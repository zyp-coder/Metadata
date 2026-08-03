"""
计算字段服务 — 依赖解析、DAG 构建、重算调度、枚举试算。
"""

import itertools
import random
from collections import defaultdict, deque

from .models import ComputedField, Field, Domain
from .formula_engine import (
    extract_references, evaluate, validate_expression,
    FormulaError, CircularDependencyError
)


# ============================================================
# 依赖解析与 DAG
# ============================================================


def parse_and_save_dependencies(computed_field: ComputedField) -> dict:
    """解析表达式，更新 depends_on/depends_on_computed/parsed_references/execution_order。

    Returns:
        {"references": [...], "dag_order": [...], "cycle": None|[...]}
    """
    expression = computed_field.expression or ''
    refs = extract_references(expression)
    computed_field.parsed_references = refs
    computed_field.save(update_fields=['parsed_references'])

    domain = computed_field.domain

    # 解析引用 → 分为物理字段依赖和计算字段依赖
    physical_field_ids = []
    computed_field_ids = []

    # 获取域内所有计算字段的 code 映射
    domain_computed_map = {
        cf.code: cf.id
        for cf in ComputedField.objects.filter(domain=domain).exclude(id=computed_field.id)
    }

    for ref in refs:
        table_name = ref['table_name']
        field_code = ref['field_code']

        # 先看是否引用了其他计算字段（约定：表名="$computed" 或直接用计算字段 code）
        if field_code in domain_computed_map:
            # 检查是否真的是计算字段引用（表名不匹配任何物理表时）
            physical_match = Field.objects.filter(
                table__domain=domain,
                table__name=table_name,
                code=field_code,
                status=Field.Status.ACTIVE
            ).first()
            if physical_match:
                physical_field_ids.append(physical_match.id)
            else:
                computed_field_ids.append(domain_computed_map[field_code])
        else:
            # 查找物理字段
            physical_match = Field.objects.filter(
                table__domain=domain,
                table__name=table_name,
                code=field_code,
                status=Field.Status.ACTIVE
            ).first()
            if physical_match:
                physical_field_ids.append(physical_match.id)

    # 更新 M2M 关系
    computed_field.depends_on.set(physical_field_ids)
    computed_field.depends_on_computed.set(computed_field_ids)

    # 检测循环依赖
    cycle = detect_cycle(domain.id, computed_field.id)
    if cycle:
        return {"references": refs, "dag_order": [], "cycle": cycle}

    # 重算域内所有计算字段的执行顺序
    dag_order = _update_execution_orders(domain.id)

    return {"references": refs, "dag_order": dag_order, "cycle": None}


def build_dag(domain_id: int) -> dict:
    """构建域内所有计算字段的 DAG。

    Returns:
        {"nodes": [{"id":..,"code":..,"name":..}], "edges": [{"from":..,"to":..}], "topo_order": [...]}
    """
    computed_fields = list(ComputedField.objects.filter(
        domain_id=domain_id, status=ComputedField.Status.ACTIVE
    ))

    nodes = [{"id": cf.id, "code": cf.code, "name": cf.name,
              "execution_order": cf.execution_order} for cf in computed_fields]

    edges = []
    for cf in computed_fields:
        for dep_id in cf.depends_on_computed.values_list('id', flat=True):
            edges.append({"from": dep_id, "to": cf.id})

    topo_order = _topological_sort(computed_fields)

    return {"nodes": nodes, "edges": edges, "topo_order": topo_order}


def detect_cycle(domain_id: int, check_field_id: int = None) -> list | None:
    """检测域内计算字段 DAG 是否有环。

    Args:
        domain_id: 域 ID
        check_field_id: 如指定，特别检查该字段是否在环中

    Returns:
        None（无环）或环路径列表 ["A", "B", "C", "A"]
    """
    computed_fields = list(ComputedField.objects.filter(
        domain_id=domain_id, status=ComputedField.Status.ACTIVE
    ).prefetch_related('depends_on_computed'))

    # 构建邻接表
    id_to_code = {cf.id: cf.code for cf in computed_fields}
    adjacency = defaultdict(set)
    for cf in computed_fields:
        for dep in cf.depends_on_computed.all():
            adjacency[dep.id].add(cf.id)

    # DFS 检测环
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cf.id: WHITE for cf in computed_fields}
    path = []

    def dfs(node_id):
        color[node_id] = GRAY
        path.append(node_id)
        for neighbor in adjacency.get(node_id, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                # 找到环
                cycle_start = path.index(neighbor)
                cycle_ids = path[cycle_start:] + [neighbor]
                return [id_to_code.get(nid, str(nid)) for nid in cycle_ids]
            if color[neighbor] == WHITE:
                result = dfs(neighbor)
                if result:
                    return result
        path.pop()
        color[node_id] = BLACK
        return None

    for cf in computed_fields:
        if color[cf.id] == WHITE:
            result = dfs(cf.id)
            if result:
                return result

    return None


def _topological_sort(computed_fields: list) -> list[int]:
    """对计算字段做拓扑排序，返回 ID 列表（执行顺序）。"""
    if not computed_fields:
        return []

    # 构建入度表和邻接表
    in_degree = {cf.id: 0 for cf in computed_fields}
    adjacency = defaultdict(list)
    id_set = set(in_degree.keys())

    for cf in computed_fields:
        for dep_id in cf.depends_on_computed.values_list('id', flat=True):
            if dep_id in id_set:
                adjacency[dep_id].append(cf.id)
                in_degree[cf.id] += 1

    # BFS (Kahn's algorithm)
    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in adjacency[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result


def _update_execution_orders(domain_id: int) -> list[int]:
    """重算域内所有计算字段的 execution_order。"""
    computed_fields = list(ComputedField.objects.filter(
        domain_id=domain_id, status=ComputedField.Status.ACTIVE
    ).prefetch_related('depends_on_computed'))

    topo_order = _topological_sort(computed_fields)

    # 批量更新
    for order, cf_id in enumerate(topo_order):
        ComputedField.objects.filter(id=cf_id).update(execution_order=order)

    return topo_order


# ============================================================
# 重算调度
# ============================================================


def batch_recalculate(domain_id: int) -> dict:
    """按 DAG 拓扑排序批量重算域内所有计算字段的值。

    对域下所有档案记录执行重算，结果写入 ArchiveRecord.data。

    Returns:
        {"total": N, "success": M, "errors": [...], "records_updated": K}
    """
    from apps.archive.models import Archive, ArchiveRecord

    computed_fields = list(ComputedField.objects.filter(
        domain_id=domain_id, status=ComputedField.Status.ACTIVE,
        release_to_archive=True
    ).order_by('execution_order'))

    if not computed_fields:
        return {"total": 0, "success": 0, "errors": [], "records_updated": 0}

    # 获取域的档案和记录
    try:
        archive = Archive.objects.get(domain_id=domain_id)
    except Archive.DoesNotExist:
        return {"total": len(computed_fields), "success": 0,
                "errors": ["域尚未创建档案"], "records_updated": 0}

    records = list(ArchiveRecord.objects.filter(
        archive=archive, status=ArchiveRecord.Status.ACTIVE
    ))

    if not records:
        return {"total": len(computed_fields), "success": len(computed_fields),
                "errors": [], "records_updated": 0}

    # 构建字段引用上下文模板（表名→字段code的映射）
    errors = []
    records_updated = 0

    for record in records:
        context = _build_context_from_record(record.data, domain_id)
        record_changed = False

        for cf in computed_fields:
            try:
                result = evaluate(cf.expression, context)
                old_val = record.data.get(cf.code)
                if old_val != result:
                    record.data[cf.code] = result
                    # 将计算结果也加入 context，供后续计算字段引用
                    context[f"$computed.{cf.code}"] = result
                    record_changed = True
            except FormulaError as e:
                errors.append({"record_id": record.id, "field": cf.code, "error": str(e)})

        if record_changed:
            record.save(update_fields=['data', 'updated_at'])
            records_updated += 1

    return {
        "total": len(computed_fields),
        "success": len(computed_fields) - len(set(e['field'] for e in errors)),
        "errors": errors[:50],  # 限制错误数量
        "records_updated": records_updated,
    }


def recalculate_affected(domain_id: int, record_id: int, changed_fields: list[str]) -> dict:
    """根据变更字段找到受影响的计算字段并重算。

    Args:
        domain_id: 域 ID
        record_id: 记录 ID
        changed_fields: 变更的字段 code 列表

    Returns:
        {"recalculated": [code,...], "new_values": {code: value}, "errors": [...]}
    """
    from apps.archive.models import ArchiveRecord

    # 获取域内所有启用的计算字段
    computed_fields = list(ComputedField.objects.filter(
        domain_id=domain_id, status=ComputedField.Status.ACTIVE,
        release_to_archive=True
    ).order_by('execution_order').prefetch_related('depends_on'))

    if not computed_fields:
        return {"recalculated": [], "new_values": {}, "errors": []}

    # 找到受影响的计算字段（直接或间接依赖变更字段的）
    affected = _find_affected_fields(computed_fields, changed_fields)

    if not affected:
        return {"recalculated": [], "new_values": {}, "errors": []}

    # 获取记录
    try:
        record = ArchiveRecord.objects.get(id=record_id)
    except ArchiveRecord.DoesNotExist:
        return {"recalculated": [], "new_values": {}, "errors": ["记录不存在"]}

    # 按执行顺序重算受影响的字段
    context = _build_context_from_record(record.data, domain_id)
    new_values = {}
    errors = []
    recalculated = []

    for cf in affected:
        try:
            result = evaluate(cf.expression, context)
            new_values[cf.code] = result
            context[f"$computed.{cf.code}"] = result
            recalculated.append(cf.code)
        except FormulaError as e:
            errors.append({"field": cf.code, "error": str(e)})

    return {"recalculated": recalculated, "new_values": new_values, "errors": errors}


def _find_affected_fields(computed_fields: list, changed_codes: list[str]) -> list:
    """找到直接或间接依赖变更字段的计算字段，按执行顺序排列。"""
    changed_set = set(changed_codes)
    affected_ids = set()

    # 构建反向依赖图：物理字段 code → 依赖它的计算字段
    code_to_cf = {cf.code: cf for cf in computed_fields}

    # 多轮传播（计算字段可能依赖其他计算字段）
    newly_affected = set()

    # 第一轮：找直接依赖变更物理字段的计算字段
    for cf in computed_fields:
        for ref in (cf.parsed_references or []):
            if ref.get('field_code') in changed_set:
                affected_ids.add(cf.id)
                newly_affected.add(cf.code)
                break

    # 后续轮：找依赖已受影响计算字段的计算字段
    while newly_affected:
        next_round = set()
        for cf in computed_fields:
            if cf.id in affected_ids:
                continue
            for ref in (cf.parsed_references or []):
                if ref.get('field_code') in newly_affected:
                    affected_ids.add(cf.id)
                    next_round.add(cf.code)
                    break
        newly_affected = next_round

    # 按执行顺序排列
    return [cf for cf in computed_fields if cf.id in affected_ids]


# ============================================================
# 枚举试算
# ============================================================


def trial_calculate(computed_field_id: int, params: dict | None = None,
                    auto_enumerate: bool = False, max_combinations: int = 100) -> dict:
    """枚举试算。

    Args:
        computed_field_id: 计算字段 ID
        params: 手动指定参数 {"表名.字段名": [值1, 值2, ...]}
        auto_enumerate: True 则从 distinct_values 自动构建参数
        max_combinations: 最大组合数限制

    Returns:
        {"combinations": [{"inputs": {...}, "output": xxx, "error": None/str}],
         "total_possible": N, "truncated": bool}
    """
    try:
        cf = ComputedField.objects.get(id=computed_field_id)
    except ComputedField.DoesNotExist:
        return {"combinations": [], "total_possible": 0, "truncated": False,
                "error": "计算字段不存在"}

    refs = cf.parsed_references or extract_references(cf.expression)

    if not refs:
        # 无依赖字段，直接计算一次
        try:
            result = evaluate(cf.expression, {})
            return {"combinations": [{"inputs": {}, "output": result, "error": None}],
                    "total_possible": 1, "truncated": False}
        except FormulaError as e:
            return {"combinations": [{"inputs": {}, "output": None, "error": str(e)}],
                    "total_possible": 1, "truncated": False}

    # 构建参数空间
    if params:
        param_space = params
    elif auto_enumerate:
        param_space = _build_param_space_from_distinct(cf.domain_id, refs)
    else:
        return {"combinations": [], "total_possible": 0, "truncated": False,
                "error": "请提供参数或开启自动枚举"}

    # 计算笛卡尔积
    keys = list(param_space.keys())
    values_lists = [param_space[k] if isinstance(param_space[k], list) else [param_space[k]]
                    for k in keys]

    total_possible = 1
    for vl in values_lists:
        total_possible *= len(vl)

    truncated = total_possible > max_combinations
    combinations_iter = _sample_combinations(values_lists, max_combinations)

    results = []
    for combo in combinations_iter:
        context = {keys[i]: combo[i] for i in range(len(keys))}
        try:
            output = evaluate(cf.expression, context)
            results.append({"inputs": context, "output": output, "error": None})
        except FormulaError as e:
            results.append({"inputs": context, "output": None, "error": str(e)})

    return {
        "combinations": results,
        "total_possible": total_possible,
        "truncated": truncated,
    }


def _build_param_space_from_distinct(domain_id: int, refs: list[dict]) -> dict:
    """从字段的 distinct_values 构建参数空间（无缓存时按需查库填充）。"""
    from .distinct_cache import ensure_distinct_cache
    param_space = {}

    for ref in refs:
        table_name = ref['table_name']
        field_code = ref['field_code']
        ref_key = f"{table_name}.{field_code}"

        # 查找字段的 distinct_values
        field_obj = Field.objects.filter(
            table__domain_id=domain_id,
            table__name=table_name,
            code=field_code,
            status=Field.Status.ACTIVE
        ).select_related('table', 'table__data_source').first()

        # 从未同步过去重值的字段：按需查库填充缓存（失败不阻断，降级为占位）
        if field_obj and field_obj.distinct_values is None:
            ensure_distinct_cache([field_obj])

        if field_obj and field_obj.distinct_values:
            # 取前 10 个值避免组合爆炸
            param_space[ref_key] = field_obj.distinct_values[:10]
        else:
            # 无缓存值，用默认占位
            param_space[ref_key] = ['']

    return param_space


def _sample_combinations(values_lists: list[list], max_n: int) -> list[tuple]:
    """采样参数组合。

    总组合数 <= max_n 时全量返回笛卡尔积；
    否则用固定种子随机采样不重复组合，保证每列都能展现多样取值
    （避免 product 顺序截断导致前列恒定不变）。
    """
    total = 1
    for vl in values_lists:
        total *= len(vl)
    if total <= max_n:
        return list(itertools.product(*values_lists))

    seen = set()
    result = []
    # 先轮转采样：保证每列前若干个取值都出现
    max_len = max(len(vl) for vl in values_lists)
    for i in range(min(max_n, max_len)):
        combo = tuple(vl[i % len(vl)] for vl in values_lists)
        if combo not in seen:
            seen.add(combo)
            result.append(combo)
    # 再随机补足（固定种子保证结果稳定可复现）
    rng = random.Random(42)
    attempts = 0
    while len(result) < max_n and attempts < max_n * 20:
        combo = tuple(vl[rng.randrange(len(vl))] for vl in values_lists)
        if combo not in seen:
            seen.add(combo)
            result.append(combo)
        attempts += 1
    return result


def preview_expression(domain_id: int, expression: str, max_combinations: int = 50) -> dict:
    """免实例数据预览：按表达式引用字段的去重值枚举组合并逐行计算输出。

    新建/编辑窗口均可调用，无需先保存计算字段。

    Returns:
        {"valid": bool, "errors": [...], "columns": ["表.字段", ...],
         "rows": [{"inputs": {...}, "output": xxx, "error": None|str}],
         "total_possible": N, "truncated": bool}
    """
    expression = (expression or '').strip()
    if not expression:
        return {"valid": False, "errors": ["表达式为空"], "columns": [],
                "rows": [], "total_possible": 0, "truncated": False}

    validation = validate_expression(expression)
    if not validation['valid']:
        # 语法错误时仍用正则提取引用，展示输入参数去重组合（输出列留空）
        err_refs = extract_references(expression)
        err_columns, err_rows = [], []
        err_total, err_truncated = 0, False
        if err_refs:
            err_space = _build_param_space_from_distinct(domain_id, err_refs)
            err_keys = list(err_space.keys())
            err_values = [err_space[k] if isinstance(err_space[k], list) else [err_space[k]]
                          for k in err_keys]
            err_total = 1
            for vl in err_values:
                err_total *= len(vl)
            err_truncated = err_total > max_combinations
            for combo in _sample_combinations(err_values, max_combinations):
                ctx = {err_keys[i]: combo[i] for i in range(len(err_keys))}
                err_rows.append({"inputs": ctx, "output": None, "error": None})
            err_columns = err_keys
        return {"valid": False, "errors": [validation.get('error', '语法错误')],
                "columns": err_columns, "rows": err_rows,
                "total_possible": err_total, "truncated": err_truncated}

    refs = extract_references(expression)

    if not refs:
        # 无依赖字段，直接计算一次
        try:
            result = evaluate(expression, {})
            return {"valid": True, "errors": [], "columns": [],
                    "rows": [{"inputs": {}, "output": result, "error": None}],
                    "total_possible": 1, "truncated": False}
        except FormulaError as e:
            return {"valid": True, "errors": [], "columns": [],
                    "rows": [{"inputs": {}, "output": None, "error": str(e)}],
                    "total_possible": 1, "truncated": False}

    param_space = _build_param_space_from_distinct(domain_id, refs)

    keys = list(param_space.keys())
    values_lists = [param_space[k] if isinstance(param_space[k], list) else [param_space[k]]
                    for k in keys]

    total_possible = 1
    for vl in values_lists:
        total_possible *= len(vl)

    truncated = total_possible > max_combinations
    combinations_iter = _sample_combinations(values_lists, max_combinations)

    rows = []
    for combo in combinations_iter:
        context = {keys[i]: combo[i] for i in range(len(keys))}
        try:
            output = evaluate(expression, context)
            rows.append({"inputs": context, "output": output, "error": None})
        except FormulaError as e:
            rows.append({"inputs": context, "output": None, "error": str(e)})

    return {
        "valid": True,
        "errors": [],
        "columns": keys,
        "rows": rows,
        "total_possible": total_possible,
        "truncated": truncated,
    }


# ============================================================
# 辅助函数
# ============================================================


def _build_context_from_record(record_data: dict, domain_id: int) -> dict:
    """从档案记录数据构建公式执行上下文。

    将 record_data 中的 {field_code: value} 转换为 {"表名.字段名": value} 格式。
    """
    from .models import Field as FieldModel

    context = {}

    # 获取域内所有物理字段的 code → 表名映射
    fields = FieldModel.objects.filter(
        table__domain_id=domain_id,
        status=FieldModel.Status.ACTIVE
    ).select_related('table').values_list('code', 'table__name')

    code_to_table = {}
    for code, table_name in fields:
        code_to_table[code] = table_name

    # 构建 context
    for code, value in record_data.items():
        table_name = code_to_table.get(code)
        if table_name:
            context[f"{table_name}.{code}"] = value
        # 也保留纯 code 方便计算字段间引用
        context[f"$computed.{code}"] = value

    # 域内字段记录缺键时补 None：字段合法但该记录无值（如未闭店门店不在闭店表）
    # 视为空值参与计算；引用域外不存在的表/字段仍会正常抛「字段引用未找到」
    for code, table_name in code_to_table.items():
        context.setdefault(f"{table_name}.{code}", None)

    return context
