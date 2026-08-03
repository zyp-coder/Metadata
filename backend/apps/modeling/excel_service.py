"""Excel 解析与本地建表服务。

负责：
1) 解析 Excel 文件（列名 + 样本数据）
2) 推断字段类型（调用 ai_service.infer_fields_from_excel）
3) 在本地数据库执行 CREATE TABLE 并创建 Table/Field 记录
"""
import re

from django.db import connection, transaction
from .models import Domain, Table, Field
from . import ai_service


def parse_excel(file_obj):
    """解析 Excel 文件，返回 {columns, rows}。

    :param file_obj: Django 上传的 InMemoryUploadedFile 或文件路径
    :return: {'columns': [{'name': str}], 'rows': [[cell, ...], ...]}
    """
    import openpyxl

    # openpyxl 需要可 seek 的文件
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)

    wb = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)

    # 第一行作为列名
    try:
        header_row = next(rows_iter)
    except StopIteration:
        wb.close()
        return {'columns': [], 'rows': []}

    columns = []
    for i, cell in enumerate(header_row):
        name = str(cell).strip() if cell is not None else f'column_{i + 1}'
        if not name:
            name = f'column_{i + 1}'
        columns.append({'name': name})

    # 取前 10 行作为样本
    rows = []
    for i, row in enumerate(rows_iter):
        if i >= 10:
            break
        rows.append([cell for cell in row])

    wb.close()
    return {'columns': columns, 'rows': rows}


def infer_field_types(columns, rows, use_ai=True):
    """推断字段类型。优先 AI，失败降级到启发式。"""
    if use_ai:
        try:
            return ai_service.infer_fields_from_excel(columns, rows)
        except Exception:
            pass
    return ai_service._infer_fields_heuristic(columns, rows)


# 字段类型 → SQL 类型映射（本地 PostgreSQL）
_FIELD_TYPE_TO_SQL = {
    'string': 'VARCHAR({length})',
    'number': 'NUMERIC',
    'date': 'TIMESTAMP',
    'boolean': 'BOOLEAN',
    'enum': 'VARCHAR(50)',
}


def _sql_type_for(field_def):
    ft = field_def.get('field_type', 'string')
    template = _FIELD_TYPE_TO_SQL.get(ft, 'VARCHAR(200)')
    if '{length}' in template:
        length = field_def.get('length') or 200
        return template.format(length=length)
    return template


def _safe_code(code):
    """将表/字段编码清洗为合法标识符（字母/数字/下划线，字母开头）。"""
    code = re.sub(r'[^A-Za-z0-9_]', '_', str(code or '').strip())
    if not code or not re.match(r'^[A-Za-z_]', code):
        code = 't_' + code
    return code[:50]


@transaction.atomic
def create_local_table_from_excel(domain_id, file_name, table_code, table_name_en, table_name_cn, fields):
    """根据 Excel 解析结果在本地数据库建表，并创建 Table/Field 记录。

    :param domain_id: 域 id
    :param file_name: 原始 Excel 文件名（用于日志）
    :param table_code: 表编码（将作为数据库表名）
    :param table_name_en: 英文名
    :param table_name_cn: 中文名
    :param fields: [{'name', 'code', 'field_type', 'length', 'required', 'comment'}]
    :return: 创建的 Table 实例
    """
    domain = Domain.objects.get(id=domain_id)
    table_code = _safe_code(table_code)

    # 1) 执行 CREATE TABLE
    if not fields:
        raise ValueError('字段列表为空，无法建表')

    col_defs = []
    # 自增主键 id
    col_defs.append('id SERIAL PRIMARY KEY')
    for f in fields:
        col_code = _safe_code(f.get('code') or f.get('name'))
        sql_type = _sql_type_for(f)
        null_clause = '' if f.get('required') else ' NULL'
        col_defs.append(f'"{col_code}" {sql_type}{null_clause}')
    # 通用审计字段
    col_defs.append('created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
    col_defs.append('updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

    create_sql = f'CREATE TABLE IF NOT EXISTS "{table_code}" ({", ".join(col_defs)})'
    with connection.cursor() as cursor:
        cursor.execute(create_sql)

    # 2) 创建 Table 记录
    table = Table.objects.create(
        domain=domain,
        name=table_name_en or table_code,
        code=table_code,
        description=table_name_cn or '',
        type=Table.Type.LOCAL,
        data_source=None,
        external_table_name='',
        status=Table.Status.ACTIVE,
    )

    # 3) 创建 Field 记录
    for idx, f in enumerate(fields):
        col_code = _safe_code(f.get('code') or f.get('name'))
        Field.objects.create(
            table=table,
            name=f.get('name') or col_code,
            code=col_code,
            comment=f.get('comment', '')[:500],
            field_type=f.get('field_type', 'string'),
            length=f.get('length'),
            required=bool(f.get('required', False)),
            sort_order=idx,
            status=Field.Status.ACTIVE,
        )

    return table
