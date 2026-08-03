"""字段去重取值缓存工具（从 views.py 抽出的独立模块）。

被 views.py（AI查重/组合字段抽屉/刷新去重）与 computed_service.py（试算参数空间）共用，
避免 service → views 反向依赖。
"""

# db_type → Django 数据库引擎映射（与 DataSourceViewSet 共用）
ENGINE_MAP = {
    'postgresql': 'django.db.backends.postgresql',
    'mysql': 'django.db.backends.mysql',
    'sqlserver': 'mssql',
    'oracle': 'django.db.backends.oracle',
}


def json_safe(v):
    """把单元格值转为 JSON 可序列化形式（datetime/Decimal/date → str）。"""
    if v is None:
        return None
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    if isinstance(v, (int, float, bool, str)):
        return v
    return str(v)


def fetch_distinct_values(table, field_code, limit=100):
    """读取一个字段的去重取值样本（上限 limit 条）。

    本地表（无 data_source）：默认连接查询。
    外部表：复用动态连接模式（参照 _preview_external_data），按 db_type 构造 SQL。
    失败抛出异常由上层捕获。
    """
    from django.db import connection, connections

    if not (table.data_source_id and table.external_table_name):
        # 本地表
        with connection.cursor() as cursor:
            cursor.execute(
                f'SELECT DISTINCT "{field_code}" FROM "{table.code}" '
                f'WHERE "{field_code}" IS NOT NULL LIMIT %s',
                [limit],
            )
            return [json_safe(row[0]) for row in cursor.fetchall()]

    # 外部数据源表
    ds = table.data_source
    engine = ENGINE_MAP.get(ds.db_type)
    if not engine:
        raise ValueError(f'不支持的数据库类型: {ds.db_type}')
    alias = f'_distinct_{ds.id}_{table.id}'
    db_config = {
        'ENGINE': engine,
        'NAME': ds.db_name,
        'HOST': ds.host,
        'PORT': str(ds.port),
        'USER': ds.username,
        'PASSWORD': ds.password,
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'TIME_ZONE': None,
        'CONN_MAX_AGE': 0,
        'CONN_HEALTH_CHECKS': False,
        'OPTIONS': {},
    }
    if ds.db_type == 'oracle':
        db_config['OPTIONS'] = {'service_name': ds.db_name}
    elif ds.db_type == 'sqlserver':
        db_config['OPTIONS'] = {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=no',
        }
    connections.databases[alias] = db_config
    try:
        conn = connections[alias]
        conn.ensure_connection()
        ext_table = table.external_table_name
        schema = table.schema or {'postgresql': 'public', 'sqlserver': 'dbo', 'oracle': '', 'mysql': ''}.get(ds.db_type, '')
        with conn.cursor() as cursor:
            if ds.db_type == 'sqlserver':
                full_table = f'[{schema}].[{ext_table}]'
                cursor.execute(f'SELECT DISTINCT TOP {int(limit)} [{field_code}] FROM {full_table} WHERE [{field_code}] IS NOT NULL')
            elif ds.db_type == 'oracle':
                owner = schema.upper() if schema else ''
                full_table = f'"{owner}"."{ext_table}"' if owner else f'"{ext_table}"'
                cursor.execute(
                    f'SELECT * FROM (SELECT DISTINCT "{field_code}" FROM {full_table} WHERE "{field_code}" IS NOT NULL) WHERE ROWNUM <= %s',
                    [limit],
                )
            elif ds.db_type == 'mysql':
                cursor.execute(f'SELECT DISTINCT `{field_code}` FROM `{ext_table}` WHERE `{field_code}` IS NOT NULL LIMIT %s', [limit])
            else:  # postgresql
                full_table = f'"{schema}"."{ext_table}"'
                cursor.execute(f'SELECT DISTINCT "{field_code}" FROM {full_table} WHERE "{field_code}" IS NOT NULL LIMIT %s', [limit])
            return [json_safe(row[0]) for row in cursor.fetchall()]
    finally:
        connections.databases.pop(alias, None)


def ensure_distinct_cache(fields, force=False):
    """确保传入字段的去重内容缓存已填充。

    force=False：仅对 distinct_values 为 None 的字段查库（按需）。
    force=True：全部重查。
    返回 {'updated': n, 'errors': [{'field','message'}]}。
    """
    from django.utils import timezone
    updated = 0
    errors = []
    for f in fields:
        if not force and f.distinct_values is not None:
            continue
        try:
            vals = fetch_distinct_values(f.table, f.code, limit=100)
            f.distinct_values = vals
            f.distinct_synced_at = timezone.now()
            f.save(update_fields=['distinct_values', 'distinct_synced_at', 'updated_at'])
            updated += 1
        except Exception as e:
            errors.append({'field': f.id, 'message': str(e)})
    return {'updated': updated, 'errors': errors}
