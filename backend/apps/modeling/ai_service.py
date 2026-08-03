"""AI 服务层。

统一封装字段智能能力：自动分组、语义识别（注释补全 + 同义/歧义标识）。
通过 settings 中的 AI_API_KEY 判断是否接入真实大模型：
- 已配置密钥：调用 OpenAI 兼容的 chat/completions 接口，要求返回 JSON。
- 未配置或调用失败：回退到基于字段名/编码的启发式模拟，保证功能可用不报错。
"""
import json
import re

from django.conf import settings

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


def _resolve_ai_config():
    """解析 AI 配置：优先读数据库 AIConfig（enabled=True），回退到 settings 环境变量。

    返回 dict：api_base / api_key / model / temperature / timeout。
    """
    cfg = {
        'api_base': getattr(settings, 'AI_API_BASE', ''),
        'api_key': getattr(settings, 'AI_API_KEY', ''),
        'model': getattr(settings, 'AI_MODEL', 'gpt-4o-mini'),
        'temperature': 0.2,
        'timeout': getattr(settings, 'AI_TIMEOUT', 30),
    }
    try:
        from .models import AIConfig
        obj = AIConfig.objects.filter(enabled=True).first()
        if obj:
            if obj.api_base:
                cfg['api_base'] = obj.api_base
            if obj.api_key:
                cfg['api_key'] = obj.api_key
            if obj.model:
                cfg['model'] = obj.model
            if obj.temperature is not None:
                cfg['temperature'] = obj.temperature
            if obj.timeout:
                cfg['timeout'] = obj.timeout
    except Exception:
        # 数据库未就绪（如迁移前）时静默回退到环境变量配置
        pass
    return cfg


def _has_llm():
    """是否具备真实大模型调用条件（DB 配置或环境变量任一提供了 API Key）。"""
    return bool(_resolve_ai_config().get('api_key')) and requests is not None


def _chat(messages, cfg=None):
    """调用 OpenAI 兼容接口，返回助手文本内容。失败抛异常由上层降级处理。"""
    cfg = cfg or _resolve_ai_config()
    base = (cfg.get('api_base') or '').rstrip('/')
    url = f'{base}/chat/completions'
    headers = {
        'Authorization': f"Bearer {cfg.get('api_key', '')}",
        'Content-Type': 'application/json',
    }
    payload = {
        'model': cfg.get('model') or 'gpt-4o-mini',
        'messages': messages,
        'temperature': cfg.get('temperature', 0.2),
        'response_format': {'type': 'json_object'},
    }
    resp = requests.post(url, headers=headers, json=payload,
                         timeout=cfg.get('timeout', 30))
    resp.raise_for_status()
    data = resp.json()
    return data['choices'][0]['message']['content']


def test_connection(cfg=None):
    """测试 AI 连接：发送最小请求验证配置是否可用，返回 (ok: bool, message: str)。"""
    cfg = cfg or _resolve_ai_config()
    if not cfg.get('api_key'):
        return False, '未配置 API Key'
    if requests is None:
        return False, '服务器缺少 requests 依赖库'
    try:
        content = _chat([{'role': 'user', 'content': '仅返回 JSON：{"ok":true}'}], cfg=cfg)
        return True, f'连接成功，模型：{cfg.get("model")}，返回：{str(content)[:120]}'
    except Exception as e:
        return False, str(e)


def _parse_json(text):
    """从模型返回文本中解析 JSON，容忍代码块包裹。"""
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
        text = re.sub(r'\n?```$', '', text).strip()
    return json.loads(text)


# ============ 可配置提示词（内置默认，仅指令部分；字段数据 JSON 由各 _llm 函数自动追加）============

DEFAULT_PROMPT_AUTO_GROUP = (
    '你是主数据建模专家。请按“业务主题/业务对象”对以下字段进行分组，'
    '让同一业务概念（如：客户信息、订单信息、商品信息、财务信息、联系方式、审计追踪等）的字段归入同一组，'
    '分组名用简洁的中文业务主题词。'
    '判断依据是字段的业务含义（结合中文名 comment、编码 code、英文名 name 综合理解），而非其存储类型。'
    '严禁按数据类型（字符串/数字/日期/布尔）或长度等技术属性分组。'
    '仅返回 JSON，格式：{"groups":[{"name":"业务主题名","field_ids":[1,2]}]}。'
)

DEFAULT_PROMPT_SEMANTIC = (
    '你是主数据治理专家。任务：'
    '1) 对 comment 为空的字段，根据名称和编码生成简洁中文注释；'
    '2) 对 comment 是英文的字段，将其翻译为简洁准确的中文注释；'
    '3) 找出同义词、语义相近或容易产生歧义的字段，给出说明。'
    '仅返回 JSON，格式：'
    '{"comments":{"字段id":"中文注释"},"marks":[{"id":字段id,"semantic_note":"说明"}]}。'
)

DEFAULT_PROMPT_DEDUP = (
    '你是主数据治理专家。任务：找出跨表的冗余（等价）字段——即实际表达同一业务含义、应保持数据一致的字段。'
    '请从三个维度综合判断：'
    '1) 字段编码归一化后相似（如 create_time 与 CreateTime）；'
    '2) 中文名称（comment）归一化后相似（如“客户名称”与“客户_名称”）；'
    '3) 数据去重内容（distinct_values）高度重合/一致（取值集合相同或大部分相同）。'
    '三者中任一强信号即可归为同组，由你综合判断。'
    '只把来自不同表、确实等价的字段归为一组，成员少于2个的不要返回。'
    '仅返回 JSON，格式：'
    '{"groups":[{"standard_code":"标准编码","standard_name":"标准中文名","field_ids":[1,2]}]}。'
)

DEFAULT_PROMPT_INFER = (
    '你是主数据建模专家。根据 Excel 列名和样本数据推断每个字段的主数据属性。\n'
    '返回 JSON，格式：{"fields":[{"name":"英文字段名（驼峰/下划线）",'
    '"field_type":"string|number|date|boolean|enum",'
    '"length":整数或null,"required":true/false,"comment":"中文注释"}]}。\n'
    '规则：1) name 必须是英文标识符；2) field_type 根据样本推断；3) 字符串长度取样本最大长度向上取整到 16/32/50/64/100/128/200/255/500；'
    '4) 样本中无空值则 required=true。'
)

PROMPT_META = [
    {'key': 'prompt_auto_group', 'label': '字段分组', 'default': DEFAULT_PROMPT_AUTO_GROUP},
    {'key': 'prompt_semantic', 'label': '语义识别', 'default': DEFAULT_PROMPT_SEMANTIC},
    {'key': 'prompt_dedup', 'label': '跨表去重检测', 'default': DEFAULT_PROMPT_DEDUP},
    {'key': 'prompt_infer', 'label': 'Excel字段推断', 'default': DEFAULT_PROMPT_INFER},
]


def _resolve_prompt(key, default):
    """解析可配置提示词：优先读数据库 AIConfig（enabled=True）的对应字段，为空则用内置默认。"""
    try:
        from .models import AIConfig
        obj = AIConfig.objects.filter(enabled=True).first()
        if obj:
            val = (getattr(obj, key, '') or '').strip()
            if val:
                return val
    except Exception:
        pass
    return default


def prompt_defaults():
    """返回各可配置提示词的内置默认值（供前端展示/恢复默认）。"""
    return {m['key']: m['default'] for m in PROMPT_META}


# ============ 字段自动分组 ============

def auto_group_fields(fields):
    """对字段进行智能分组。

    :param fields: 可迭代的 Field 对象
    :return: [{'name': 分组名, 'field_ids': [id,...]}]
    """
    field_list = list(fields)
    if not field_list:
        return []

    if _has_llm():
        try:
            return _auto_group_llm(field_list)
        except Exception:
            pass
    return _auto_group_heuristic(field_list)


def _auto_group_llm(field_list):
    items = [{'id': f.id, 'name': f.name, 'code': f.code,
              'comment': f.comment} for f in field_list]
    prompt = _resolve_prompt('prompt_auto_group', DEFAULT_PROMPT_AUTO_GROUP) + \
        f'\n字段列表：{json.dumps(items, ensure_ascii=False)}'
    content = _chat([{'role': 'user', 'content': prompt}])
    parsed = _parse_json(content)
    valid_ids = {f.id for f in field_list}
    groups = []
    for g in parsed.get('groups', []):
        ids = [i for i in g.get('field_ids', []) if i in valid_ids]
        if ids and g.get('name'):
            groups.append({'name': str(g['name']), 'field_ids': ids})
    return groups or _auto_group_heuristic(field_list)


def _auto_group_heuristic(field_list):
    """启发式分组：按业务主题关键词归类（结合编码/英文名/中文名），而非数据类型。"""
    keyword_groups = [
        ('客户信息', ['customer', 'client', 'cust', 'member', 'buyer', 'consumer', '客户', '会员', '开户']),
        ('商品信息', ['product', 'goods', 'item', 'sku', 'spu', 'material', 'ware', '商品', '产品', '物料', '货']),
        ('订单信息', ['order', 'trade', 'deal', 'purchase', 'sale', 'contract', '订单', '交易', '合同', '采购', '销售']),
        ('组织信息', ['org', 'dept', 'department', 'company', 'branch', 'team', 'staff', 'employee', '部门', '公司', '组织', '员工', '机构']),
        ('联系方式', ['phone', 'mobile', 'email', 'address', 'contact', 'tel', 'zip', 'region', 'city', 'province', '电话', '手机', '邮箱', '地址', '联系', '城市', '省'] ),
        ('财务信息', ['amount', 'price', 'money', 'cost', 'fee', 'balance', 'tax', 'pay', 'invoice', 'account', '金额', '价格', '费用', '税', '余额', '发票', '账']),
        ('状态标识', ['status', 'state', 'flag', 'enabled', 'active', 'valid', 'type', 'category', 'level', 'grade', '状态', '标志', '类型', '类别', '等级']),
        ('审计追踪', ['create', 'update', 'modify', 'delete', 'operator', 'creator', 'time', 'date', 'version', '创建', '修改', '更新', '时间', '日期', '操作人', '版本']),
        ('基础标识', ['id', 'code', 'no', 'name', 'title', 'key', 'uuid', '编号', '编码', '名称', '标题']),
    ]
    buckets = {name: [] for name, _ in keyword_groups}
    others = []
    for f in field_list:
        text = f'{f.code} {f.name} {f.comment or ""}'.lower()
        matched = None
        for name, kws in keyword_groups:
            if any(kw in text for kw in kws):
                matched = name
                break
        if matched:
            buckets[matched].append(f.id)
        else:
            others.append(f.id)
    groups = [{'name': name, 'field_ids': ids}
              for name, ids in buckets.items() if ids]
    if others:
        groups.append({'name': '其他信息', 'field_ids': others})
    return groups


# ============ 语义识别（注释补全 + 同义/歧义标识） ============

def semantic_recognition(fields):
    """语义识别。

    :param fields: 可迭代的 Field 对象
    :return: {'comments': {id: comment}, 'marks': [{'id': id, 'semantic_note': note}]}
    """
    field_list = list(fields)
    if not field_list:
        return {'comments': {}, 'marks': []}

    if _has_llm():
        try:
            return _semantic_llm(field_list)
        except Exception:
            pass
    return _semantic_heuristic(field_list)


def _semantic_llm(field_list):
    items = [{'id': f.id, 'name': f.name, 'code': f.code,
              'comment': f.comment, 'table': f.table.name} for f in field_list]
    prompt = _resolve_prompt('prompt_semantic', DEFAULT_PROMPT_SEMANTIC) + \
        f'\n字段列表：{json.dumps(items, ensure_ascii=False)}'
    content = _chat([{'role': 'user', 'content': prompt}])
    parsed = _parse_json(content)
    valid_ids = {f.id for f in field_list}
    comments = {}
    for k, v in (parsed.get('comments') or {}).items():
        try:
            fid = int(k)
        except (ValueError, TypeError):
            continue
        if fid in valid_ids and v:
            comments[fid] = str(v)[:500]
    marks = []
    for m in parsed.get('marks', []):
        fid = m.get('id')
        if fid in valid_ids and m.get('semantic_note'):
            marks.append({'id': fid, 'semantic_note': str(m['semantic_note'])[:500]})
    return {'comments': comments, 'marks': marks}


def _semantic_heuristic(field_list):
    """启发式：为空注释补默认说明；英文注释保留（无翻译能力时）；按规范化名称检测同义/歧义。"""
    comments = {}
    for f in field_list:
        if not f.comment:
            comments[f.id] = f.name
        elif re.search(r'[a-zA-Z]', f.comment) and not re.search(r'[一-鿿]', f.comment):
            # 纯英文注释：启发式无法翻译，留给 LLM 模式处理，这里仅标记为待翻译
            comments[f.id] = f.comment  # 保留原值，避免误改

    # 按规范化名称聚类，找出重名/近义字段
    seen = {}
    groups = {}
    for f in field_list:
        base = re.sub(r'[\s_\-]', '', f.name).lower()
        if base in seen:
            groups.setdefault(base, [seen[base]]).append(f)
        else:
            seen[base] = f
    marks = []
    for base, members in groups.items():
        names = '、'.join(f'{m.table.name}.{m.name}' for m in members)
        for m in members:
            marks.append({
                'id': m.id,
                'semantic_note': f'疑似同义/歧义字段，与 {names} 语义相近，请确认',
            })
    return {'comments': comments, 'marks': marks}


# ============ 跨表字段去重（等价组检测） ============

def _normalize_code(code):
    """字段编码归一化：去下划线/空格/连字符 + 转小写。create_time / CreateTime / create-time → createtime。"""
    return re.sub(r'[\s_\-]', '', str(code or '')).lower()


def _normalize_name(name):
    """字段名称（中文 comment）归一化：去空白/下划线/连字符/常见标点 + 转小写。

    “客户名称”/“客户  名称”/“客户_名称” → 客户名称。"""
    return re.sub(r'[\s_\-（）()\[\]：:，,。.、/]', '', str(name or '')).lower()


def detect_duplicate_fields(fields, distinct_map=None):
    """检测跨表冗余（等价）字段，返回建议的等价组（不落库，仅建议）。

    :param fields: 可迭代的 Field 对象（需 select_related('table')）
    :param distinct_map: {field_id: [去重值,...]}，第三层匹配依据（可选）
    :return: [{'standard_code': str, 'standard_name': str, 'field_ids': [id,...]}]
             仅返回跨 2+ 张表、成员 >=2 的组（真正的冗余）。
    """
    field_list = list(fields)
    if not field_list:
        return []

    distinct_map = distinct_map or {}
    if _has_llm():
        try:
            return _detect_duplicates_llm(field_list, distinct_map)
        except Exception:
            pass
    return _detect_duplicates_heuristic(field_list, distinct_map)


def _detect_duplicates_heuristic(field_list, distinct_map=None):
    """启发式：按编码归一化或名称（comment）归一化分桶，编码或名称任一命中即归入同一组；
    额外：去重值集合（非空）完全相同也归入同一组。且跨 2+ 张表则构成一个等价组。"""
    distinct_map = distinct_map or {}
    n = len(field_list)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    code_key_map = {}
    name_key_map = {}
    content_key_map = {}
    for idx, f in enumerate(field_list):
        ck = _normalize_code(f.code)
        if ck:
            if ck in code_key_map:
                union(idx, code_key_map[ck])
            else:
                code_key_map[ck] = idx
        nk = _normalize_name(f.comment)
        if nk:
            if nk in name_key_map:
                union(idx, name_key_map[nk])
            else:
                name_key_map[nk] = idx
        # 第三层：去重值集合完全相同（排序后构成可 hash 的 key）
        vals = distinct_map.get(f.id)
        if vals:
            contkey = tuple(sorted(str(v) for v in vals))
            if contkey:
                if contkey in content_key_map:
                    union(idx, content_key_map[contkey])
                else:
                    content_key_map[contkey] = idx

    comps = {}
    for idx in range(n):
        comps.setdefault(find(idx), []).append(field_list[idx])

    groups = []
    for members in comps.values():
        table_ids = {m.table_id for m in members}
        if len(members) < 2 or len(table_ids) < 2:
            continue
        # 标准中文名：取第一个非空 comment
        std_name = next((m.comment for m in members if m.comment), '')
        groups.append({
            'standard_code': members[0].code,
            'standard_name': std_name,
            'field_ids': [m.id for m in members],
        })
    return groups


def _detect_duplicates_llm(field_list, distinct_map=None):
    distinct_map = distinct_map or {}
    items = [{'id': f.id, 'name': f.name, 'code': f.code,
              'comment': f.comment, 'field_type': f.field_type,
              'table': f.table.name,
              'distinct_values': distinct_map.get(f.id)} for f in field_list]
    prompt = _resolve_prompt('prompt_dedup', DEFAULT_PROMPT_DEDUP) + \
        f'\n字段列表：{json.dumps(items, ensure_ascii=False)}'
    content = _chat([{'role': 'user', 'content': prompt}])
    parsed = _parse_json(content)
    valid = {f.id: f for f in field_list}
    groups = []
    for g in parsed.get('groups', []):
        ids = [i for i in g.get('field_ids', []) if i in valid]
        table_ids = {valid[i].table_id for i in ids}
        if len(ids) < 2 or len(table_ids) < 2:
            continue
        groups.append({
            'standard_code': str(g.get('standard_code') or valid[ids[0]].code),
            'standard_name': str(g.get('standard_name') or ''),
            'field_ids': ids,
        })
    return groups or _detect_duplicates_heuristic(field_list, distinct_map)


# ============ Excel 字段推断 ============

def infer_fields_from_excel(columns, rows):
    """根据 Excel 列名和样本行推断字段定义。

    :param columns: [{'name': str, 'sample_values': [...]}]
    :param rows: [[cell, ...], ...] 前 N 行样本
    :return: [{'name': str, 'code': str, 'field_type': str, 'length': int|None,
               'required': bool, 'comment': str}]
    """
    if not columns:
        return []

    if _has_llm():
        try:
            return _infer_fields_llm(columns, rows)
        except Exception:
            pass
    return _infer_fields_heuristic(columns, rows)


def _infer_fields_llm(columns, rows):
    sample = []
    for i, col in enumerate(columns):
        col_samples = [str(r[i]) if i < len(r) and r[i] is not None else '' for r in rows[:5]]
        sample.append({'name': col['name'], 'samples': col_samples})
    prompt = _resolve_prompt('prompt_infer', DEFAULT_PROMPT_INFER) + \
        f'\n列数据：{json.dumps(sample, ensure_ascii=False)}'
    content = _chat([{'role': 'user', 'content': prompt}])
    parsed = _parse_json(content)
    result = []
    for f in parsed.get('fields', []):
        name = f.get('name')
        if not name:
            continue
        result.append({
            'name': str(name),
            'code': re.sub(r'[^A-Za-z0-9_]', '_', str(name)).lower()[:50],
            'field_type': f.get('field_type') or 'string',
            'length': f.get('length'),
            'required': bool(f.get('required', False)),
            'comment': str(f.get('comment', ''))[:500],
        })
    return result or _infer_fields_heuristic(columns, rows)


def _infer_fields_heuristic(columns, rows):
    """启发式推断：根据样本值类型判断字段类型。"""
    import datetime
    common_lengths = [16, 32, 50, 64, 100, 128, 200, 255, 500, 1000]

    def _ceil_length(n):
        for l in common_lengths:
            if n <= l:
                return l
        return common_lengths[-1]

    def _infer_column(col_name, col_idx):
        values = [r[col_idx] if col_idx < len(r) else None for r in rows]
        non_empty = [v for v in values if v is not None and str(v).strip() != '']
        required = len(non_empty) == len(values) and len(values) > 0

        if not non_empty:
            return {
                'name': col_name, 'code': re.sub(r'[^A-Za-z0-9_]', '_', col_name).lower()[:50],
                'field_type': 'string', 'length': _ceil_length(max([len(str(col_name)), 32])),
                'required': required, 'comment': col_name,
            }

        # 布尔判断
        bool_values = {str(v).strip().lower() for v in non_empty}
        if bool_values.issubset({'true', 'false', '0', '1', 'yes', 'no', 'y', 'n'}):
            return {
                'name': col_name, 'code': re.sub(r'[^A-Za-z0-9_]', '_', col_name).lower()[:50],
                'field_type': 'boolean', 'length': None,
                'required': required, 'comment': col_name,
            }

        # 日期判断
        date_patterns = [r'^\d{4}-\d{2}-\d{2}$', r'^\d{4}/\d{2}/\d{2}$',
                         r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}']
        is_date = all(
            isinstance(v, (datetime.date, datetime.datetime)) or
            any(re.match(p, str(v).strip()) for p in date_patterns)
            for v in non_empty
        )
        if is_date:
            return {
                'name': col_name, 'code': re.sub(r'[^A-Za-z0-9_]', '_', col_name).lower()[:50],
                'field_type': 'date', 'length': None,
                'required': required, 'comment': col_name,
            }

        # 数字判断
        is_number = True
        for v in non_empty:
            try:
                float(str(v).replace(',', ''))
            except (ValueError, TypeError):
                is_number = False
                break
        if is_number:
            return {
                'name': col_name, 'code': re.sub(r'[^A-Za-z0-9_]', '_', col_name).lower()[:50],
                'field_type': 'number', 'length': None,
                'required': required, 'comment': col_name,
            }

        # 默认字符串
        max_len = max(len(str(v)) for v in non_empty)
        return {
            'name': col_name, 'code': re.sub(r'[^A-Za-z0-9_]', '_', col_name).lower()[:50],
            'field_type': 'string', 'length': _ceil_length(max_len),
            'required': required, 'comment': col_name,
        }

    return [_infer_column(c['name'], i) for i, c in enumerate(columns)]


# ============================================================
# AI 自然语言生成计算表达式
# ============================================================

def generate_formula(domain_id: int, description: str, selected_refs: list[str] | None = None,
                     current_expression: str | None = None) -> dict:
    """自然语言生成公式表达式。

    携带域内可引用字段清单（含中文名 + 类型 + 样本值）+ 内置函数签名调用 LLM，
    返回 {"expression", "explanation", "reasoning", "risk", "code", "name", "output_type"}。
    生成后自动验证，失败则携带错误信息重试一次，确保返回的表达式语法正确。
    无 LLM 配置时报错（不降级）。

    工作流：先判断有什么字段 → 拿这些字段的样本值 → 基于字段语义+数据特征写公式。

    Args:
        domain_id: 域 ID
        description: 自然语言描述
        selected_refs: 用户选中的引用字段列表 ["表名.字段code", ...]。
                       传入时 prompt 仅携带这些字段作为可用字段（缩小 AI 选择范围，提升准确率）；
                       不传则使用域内全部活跃字段。
        current_expression: 当前已有的表达式。传入时 AI 将描述视为对该表达式的修改要求，
                            在其基础上修改生成；不传则按描述全新生成。
    """
    if not _has_llm():
        raise RuntimeError('AI 服务未配置，请先在「系统设置-AI配置」中填写 API Key')

    from .models import Field, ComputedField
    from .formula_engine import get_available_functions, validate_expression

    def _sample_str(distinct_values, limit: int | None = None) -> str:
        """从 distinct_values 取样本值，返回 'v1、v2、v3' 形式字符串。

        Args:
            distinct_values: JSON 字符串或列表
            limit: 取前 N 个样本；None 表示取全部（distinct_values 缓存上限 100 条，
                   与下游数据预览/试算最高用量一致）
        """
        if not distinct_values:
            return ''
        try:
            vals = json.loads(distinct_values) if isinstance(distinct_values, str) else distinct_values
            if not isinstance(vals, list) or not vals:
                return ''
            selected = vals if limit is None else vals[:limit]
            parts = []
            for v in selected:
                if v is None:
                    parts.append('(空)')
                elif isinstance(v, str) and v == '':
                    parts.append('(空字符串)')
                else:
                    parts.append(str(v))
            return '、'.join(parts)
        except (json.JSONDecodeError, TypeError):
            return ''

    def _field_line(f, distinct_values_override=None) -> str:
        """构建单条字段描述行：{表名.字段code} — 中文名（类型:X，样本：v1、v2、v3）。

        Args:
            f: Field 实例
            distinct_values_override: 覆盖 f.distinct_values 的样本值（用于缓存为空时
                                     临时从数据源采样的场景，不写回数据库）
        """
        base = f"{{{f.table.name}.{f.code}}} — {f.name or f.comment or f.code}（类型:{f.field_type}"
        sample = _sample_str(distinct_values_override if distinct_values_override is not None else f.distinct_values)
        if sample:
            return f"{base}，样本：{sample}）"
        return f"{base}）"

    def _get_distinct_values(field) -> list | None:
        """获取字段的 distinct_values（缓存优先，缓存为空时临时从数据源采样 10 条）。

        不写回数据库，仅作为 AI 生成时的临时样本。
        查询失败返回 None（让 _field_line 走「无样本」分支）。
        """
        if field.distinct_values:
            # 已有缓存（非空列表/非 None）直接返回
            try:
                vals = json.loads(field.distinct_values) if isinstance(field.distinct_values, str) else field.distinct_values
                if isinstance(vals, list) and vals:
                    return vals
            except (json.JSONDecodeError, TypeError):
                pass
        # 缓存为空：临时从数据源采样 10 条（不写回数据库）
        try:
            from .views import _fetch_distinct_values
            return _fetch_distinct_values(field.table, field.code, limit=10)
        except Exception:
            # 数据源不可达/表不存在/字段不存在 → 放弃采样
            return None

    # 构建可用字段清单：如果传入 selected_refs 则只携带这些字段，否则使用域内全部活跃字段
    if selected_refs:
        # 按 selected_refs 精确筛选（保留用户指定顺序）
        ref_set = set(selected_refs)
        fields = Field.objects.filter(
            table__domain_id=domain_id, status=Field.Status.ACTIVE
        ).select_related('table')
        field_lines = []
        for f in fields:
            ref = f"{f.table.name}.{f.code}"
            if ref in ref_set:
                dv = _get_distinct_values(f)
                field_lines.append(_field_line(f, distinct_values_override=dv))
        computed = ComputedField.objects.filter(
            domain_id=domain_id, status=ComputedField.Status.ACTIVE
        )
        for cf in computed:
            ref = f"$computed.{cf.code}"
            if ref in ref_set:
                field_lines.append(f"{{{ref}}} — {cf.name}（计算字段）")
        if not field_lines:
            raise RuntimeError('所选引用字段均不存在或已停用，请重新选择')
    else:
        fields = Field.objects.filter(
            table__domain_id=domain_id, status=Field.Status.ACTIVE
        ).select_related('table').order_by('table__name', 'sort_order')
        field_lines = []
        for f in fields:
            dv = _get_distinct_values(f)
            field_lines.append(_field_line(f, distinct_values_override=dv))
        computed = ComputedField.objects.filter(
            domain_id=domain_id, status=ComputedField.Status.ACTIVE
        ).order_by('execution_order')
        field_lines += [f"{{$computed.{cf.code}}} — {cf.name}（计算字段）" for cf in computed]
        if not field_lines:
            raise RuntimeError('该域暂无可引用字段，无法生成表达式')

    func_lines = [f"{fn['name']}: {fn['description']}" for fn in get_available_functions()]

    def _build_system(error_hint: str = '') -> str:
        hint_block = ''
        if error_hint:
            hint_block = f'\n重要纠正（上次生成错误，这次必须规避）：{error_hint}\n'
        modify_block = ''
        if current_expression:
            modify_block = (
                '\n当前已有表达式（用户的描述是对它的修改要求，请在其基础上修改，保留与修改要求无关的部分）：\n'
                + current_expression + '\n'
            )
        return (
            '你是主数据平台的公式生成助手。根据用户的自然语言描述，生成一条 Excel 风格计算表达式，并给出该计算字段的建议编码/名称/输出类型。\n'
            '工作流：\n'
            '1. 先通读「可用字段」清单，理解每个字段的中文名、类型、样本值（样本值是该字段真实数据的去重抽样）；\n'
            '2. 根据样本值判断数据特征：是否含空值、类型是否一致、是否存在异常值/特殊格式；\n'
            '3. 结合需求挑选合适字段，推导表达式；若给出了「当前已有表达式」，则在其基础上按描述修改，不要推倒重写无关部分；\n'
            '4. 自检：字段引用是否存在（必须用花括号完整引用）、函数名与参数个数是否匹配、数据风险是否已处理。\n'
            '硬性规则：\n'
            '- 只能使用下面「可用字段」清单中的字段引用（含花括号完整引用，如 {表1.字段A}），严禁自造字段；\n'
            '- 只能使用下面「可用函数」清单中的函数，严禁自造函数，函数参数个数必须匹配；\n'
            '- 字符串字面量用双引号；运算符支持 + - * / = <> < > <= >= & ；\n'
            '- code 为蛇形小写英文编码（如 total_score），name 为简短中文名称，output_type 只能是 text/number/date/boolean 之一；\n'
            '- 输出 JSON：{"reasoning": "完整思考过程：先分析需求→列出候选字段→查看样本值判断数据特征→推导表达式→自检函数名与参数个数→自检字段引用是否存在→评估数据风险", "expression": "表达式", "explanation": "一句话中文总结", "risk": "数据风险提醒（可选）：如字段存在空值/类型不一致/建议加错误处理等；无风险则为空字符串", "code": "建议字段编码", "name": "建议字段名称", "output_type": "建议输出类型"}，不要输出其他内容。\n'
            + hint_block + modify_block + '\n'
            '可用字段：\n' + '\n'.join(field_lines) + '\n\n'
            '可用函数：\n' + '\n'.join(func_lines)
        )

    def _call_llm(system: str) -> dict:
        content = _chat([
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': description},
        ])
        try:
            return json.loads(content)
        except (ValueError, TypeError):
            raise RuntimeError('AI 返回格式异常，请重试或换一种描述')

    # 首次生成
    data = _call_llm(_build_system())
    expression = (data.get('expression') or '').strip()
    if not expression:
        raise RuntimeError('AI 未能生成表达式，请补充描述细节后重试')

    # 生成后自动验证；失败则携带错误信息重试一次
    validation = validate_expression(expression)
    if not validation.get('valid'):
        err_msg = validation.get('error') or '；'.join(validation.get('errors', [])) or '语法错误'
        data = _call_llm(_build_system(error_hint=f'上次生成的表达式 {expression} 验证失败：{err_msg}。请重新生成正确的表达式。'))
        expression = (data.get('expression') or '').strip()
        if not expression:
            raise RuntimeError('AI 重试后仍未能生成有效表达式，请换一种描述')

    return {
        'expression': expression,
        'explanation': (data.get('explanation') or '').strip(),
        'reasoning': (data.get('reasoning') or '').strip(),
        'risk': (data.get('risk') or '').strip(),
        'code': (data.get('code') or '').strip(),
        'name': (data.get('name') or '').strip(),
        'output_type': (data.get('output_type') or '').strip(),
    }
