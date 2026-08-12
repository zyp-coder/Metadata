"""技术函数插件（自定义公式函数注册入口）。

当内置32个业务函数不满足需求时，技术人员在本文件中用 @register_function
装饰器注册 Python 函数，即可自动纳入以下全链路（无需改任何其他代码）：
- 表达式语法校验 / 参数个数校验（formula_engine.validate_expression）
- 求值执行（formula_engine._eval_func）
- 前端公式编辑器函数库「技术函数」分类（get_available_functions）
- AI 自然语言生成表达式的可用函数清单（ai_service.generate_formula）

注册规范：
1. 函数名全大写，Excel 风格，建议动宾结构（如 PAD_LEFT / REGEX_EXTRACT）
2. category 固定为 '技术函数'
3. description 必须写清签名与用途：'NAME(参数1, [可选参数]) — 用途说明'
4. 函数签名固定为 (args: list, ctx: dict)，args 为已求值的参数列表
5. 业务性错误抛 FormulaRuntimeError（会被 IFERROR 捕获并友好提示）

本文件由 formula_engine.py 末尾自动导入，新增函数保存后重启服务即生效。
"""
import hashlib
import re

from .formula_engine import FormulaRuntimeError, register_function


@register_function('PAD_LEFT', 2, 3, 'PAD_LEFT(文本, 长度, [填充字符]) — 左侧补齐到指定长度，默认补0', category='技术函数')
def func_pad_left(args, ctx):
    text = '' if args[0] is None else str(args[0])
    try:
        width = int(float(args[1]))
    except (ValueError, TypeError):
        raise FormulaRuntimeError(f"PAD_LEFT长度参数无效: {args[1]}")
    fill = str(args[2])[0] if len(args) > 2 and str(args[2]) else '0'
    return text.rjust(width, fill)


@register_function('REGEX_EXTRACT', 2, 3, 'REGEX_EXTRACT(文本, 正则, [组序号]) — 正则提取首个匹配，未匹配返回空', category='技术函数')
def func_regex_extract(args, ctx):
    text = '' if args[0] is None else str(args[0])
    pattern = str(args[1])
    group = int(float(args[2])) if len(args) > 2 else 0
    try:
        m = re.search(pattern, text)
    except re.error as e:
        raise FormulaRuntimeError(f"REGEX_EXTRACT正则无效: {e}")
    if not m:
        return ''
    try:
        return m.group(group) or ''
    except IndexError:
        raise FormulaRuntimeError(f"REGEX_EXTRACT组序号超出范围: {group}")


@register_function('REGEX_REPLACE', 3, 3, 'REGEX_REPLACE(文本, 正则, 替换文本) — 正则替换全部匹配', category='技术函数')
def func_regex_replace(args, ctx):
    text = '' if args[0] is None else str(args[0])
    try:
        return re.sub(str(args[1]), str(args[2]), text)
    except re.error as e:
        raise FormulaRuntimeError(f"REGEX_REPLACE正则无效: {e}")


@register_function('SPLIT_INDEX', 3, 3, 'SPLIT_INDEX(文本, 分隔符, 序号) — 按分隔符拆分后取第N段（从1开始），越界返回空', category='技术函数')
def func_split_index(args, ctx):
    text = '' if args[0] is None else str(args[0])
    sep = str(args[1])
    if not sep:
        raise FormulaRuntimeError('SPLIT_INDEX分隔符不能为空')
    try:
        idx = int(float(args[2]))
    except (ValueError, TypeError):
        raise FormulaRuntimeError(f"SPLIT_INDEX序号无效: {args[2]}")
    parts = text.split(sep)
    if 1 <= idx <= len(parts):
        return parts[idx - 1]
    return ''


@register_function('MAP_VALUE', 2, 3, 'MAP_VALUE(值, "映射串或配置表编码", [默认值]) — 按映射表转换，支持配置表引用（第二参数为配置表编码时自动查表）', category='技术函数')
def func_map_value(args, ctx):
    val = '' if args[0] is None else str(args[0])
    mapping_str = str(args[1])

    # 尝试配置表查找：第二参数匹配域内配置表编码时，自动从配置表读取映射
    domain_id = ctx.get('__domain_id__')
    if domain_id:
        from .models import ConfigTable
        ct = ConfigTable.objects.filter(domain_id=domain_id, code=mapping_str, status='active').first()
        if ct and isinstance(ct.columns, list) and len(ct.columns) >= 2 and isinstance(ct.rows, list):
            key_col = ct.columns[0]
            val_col = ct.columns[1]
            for row in ct.rows:
                if isinstance(row, dict) and str(row.get(key_col, '')) == val:
                    return str(row.get(val_col, ''))
            # 未命中，返回默认值
            return str(args[2]) if len(args) > 2 else val

    # 回退：旧版映射串逻辑（向后兼容）
    mapping = {}
    for pair in mapping_str.split(';'):
        pair = pair.strip()
        if not pair:
            continue
        if ':' not in pair:
            raise FormulaRuntimeError(f"MAP_VALUE映射项格式错误（应为 旧值:新值）: {pair}")
        k, v = pair.split(':', 1)
        mapping[k.strip()] = v.strip()
    if val in mapping:
        return mapping[val]
    return str(args[2]) if len(args) > 2 else val


@register_function('MAP_ORDER', 3, 20,
    'MAP_ORDER(值, "配置表编码1", ..., ["默认值"]) — 单值级联查多张配置表。'
    'MAP_ORDER(文本, "分隔符", "位置1,2,...", "配置表编码1", ..., ["默认值"]) — 单字段多位置：依次取各段查表。'
    'MAP_ORDER(文本1+分隔符+文本2, "分隔符", "位置1,2/位置3,4", "配置表编码1", ..., ["默认值"]) — 多字段多位置："/"分隔不同字段的位罝组',
    category='技术函数')
def func_map_order(args, ctx):
    """按顺序级联配置表查找，支持单值模式和多位置模式。

    单值模式: MAP_ORDER(值, 表编码1, 表编码2, ..., [默认值])
    多位置模式: MAP_ORDER(文本, "分隔符", "位置1,2,...", 表编码1, ..., [默认值])
      - 按分隔符拆分文本，依次取各位置段，每段查所有表，命中即返回
      - 位置组用 "/" 分隔表示多个字段："5,6,7/3,4" = 字段1取5/6/7段，字段2取3/4段
      - 文本也用 "/" 分隔多个字段，与位置组一一对应
    """
    domain_id = ctx.get('__domain_id__')
    if not domain_id:
        return ''

    from .models import ConfigTable

    # 检测多位置模式：第2参数是短字符串（分隔符）且第3参数含数字（逗号/斜杠分隔）
    # 最少 5 参数：文本 + 分隔符 + 位置 + 至少1表编码 + 默认值
    is_multi = (
        len(args) >= 5
        and len(str(args[1])) <= 3
        and re.match(r'^\d+([,/]\d+)*$', str(args[2]).strip())
    )

    if is_multi:
        # 多位置模式
        full_text = '' if args[0] is None else str(args[0])
        delimiter = str(args[1])
        positions_str = str(args[2]).strip()

        # 解析位置组："/" 分隔不同字段的位置
        position_groups = []
        for group in positions_str.split('/'):
            positions = [int(x.strip()) for x in group.split(',') if x.strip()]
            if positions:
                position_groups.append(positions)

        # 文本也用 "/" 分隔多个字段，与位置组一一对应
        # 如果没有 "/"，整个文本作为唯一字段
        if '/' in full_text and len(position_groups) > 1:
            field_texts = full_text.split('/')
        else:
            field_texts = [full_text]

        # 解析剩余参数：配置表编码 + 可选默认值
        remaining = [str(a) for a in args[3:]]
        table_codes, default_val = _parse_table_codes(remaining, domain_id)

        # 依次处理每个字段
        for i, field_text in enumerate(field_texts):
            # 取该字段对应的位置组（如果超出位置组数量，用最后一个）
            group_idx = min(i, len(position_groups) - 1)
            positions = position_groups[group_idx]
            parts = field_text.split(delimiter)
            # 依次取各段，查所有表
            for pos in positions:
                if 1 <= pos <= len(parts):
                    val = parts[pos - 1]
                    result = _lookup_tables(val, table_codes, domain_id)
                    if result is not None:
                        return result
        return default_val

    # 单值模式（原始行为）
    val = '' if args[0] is None else str(args[0])
    all_codes = [str(a) for a in args[1:]]
    table_codes, default_val = _parse_table_codes(all_codes, domain_id)

    result = _lookup_tables(val, table_codes, domain_id)
    if result is not None:
        return result
    return default_val


def _parse_table_codes(codes, domain_id):
    """从参数列表中分离配置表编码和默认值。

    最后一个参数如果不是已注册的配置表编码，则视为默认值。
    返回 (table_codes, default_val)。
    """
    from .models import ConfigTable
    codes = list(codes)
    default_val = ''
    if len(codes) >= 2:
        last = codes[-1]
        exists = ConfigTable.objects.filter(
            domain_id=domain_id, code=last, status='active'
        ).exists()
        if not exists:
            default_val = last
            codes = codes[:-1]
    return codes, default_val


def _lookup_tables(val, table_codes, domain_id):
    """在指定配置表列表中查找值，命中返回结果，全部未命中返回 None。"""
    from .models import ConfigTable
    for code in table_codes:
        ct = ConfigTable.objects.filter(
            domain_id=domain_id, code=code, status='active'
        ).first()
        if not ct or not isinstance(ct.columns, list) or len(ct.columns) < 2:
            continue
        if not isinstance(ct.rows, list):
            continue
        key_col = ct.columns[0]
        val_col = ct.columns[1]
        for row in ct.rows:
            if isinstance(row, dict) and str(row.get(key_col, '')) == val:
                return str(row.get(val_col, ''))
    return None


@register_function('HASH_MD5', 1, 2, 'HASH_MD5(文本, [长度]) — 生成MD5摘要（小写16进制），可截取前N位，常用于迁移对账', category='技术函数')
def func_hash_md5(args, ctx):
    text = '' if args[0] is None else str(args[0])
    digest = hashlib.md5(text.encode('utf-8')).hexdigest()
    if len(args) > 1:
        try:
            n = int(float(args[1]))
        except (ValueError, TypeError):
            raise FormulaRuntimeError(f"HASH_MD5长度参数无效: {args[1]}")
        if n > 0:
            return digest[:n]
    return digest
