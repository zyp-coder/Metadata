from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import DataSource, Domain, Table, FieldGroup, Field, FieldOption, FieldMapping, StandardField, AIConfig, ComputedField
from . import ai_service
from .serializers import (
    DataSourceSerializer,
    DomainSerializer, DomainDetailSerializer,
    TableListSerializer, TableCreateSerializer,
    FieldGroupSerializer, FieldOptionSerializer,
    FieldListSerializer, FieldBatchSerializer,
    FieldMappingSerializer, FieldBatchUpdateSerializer,
    AiAnalyzeResultSerializer, ClassificationConfirmSerializer,
    StandardFieldSerializer,
    StandardFieldAggregateSerializer,
    AIConfigSerializer,
    ComputedFieldSerializer,
)
from .distinct_cache import (
    ENGINE_MAP,
    json_safe as _json_safe,
    fetch_distinct_values as _fetch_distinct_values,
    ensure_distinct_cache as _ensure_distinct_cache,
)



class DataSourceViewSet(viewsets.ModelViewSet):
    """数据源配置 API"""
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    search_fields = ['name', 'db_type', 'host']

    # db_type → Django 数据库引擎映射（已抽至 distinct_cache.ENGINE_MAP 共用）
    _ENGINE_MAP = ENGINE_MAP

    def _get_connection(self, ds):
        """动态创建到指定数据源的数据库连接（返回 alias 和 connection）"""
        from django.db import connections
        alias = f'_ds_{ds.id}'
        engine = self._ENGINE_MAP.get(ds.db_type)
        if not engine:
            raise ValueError(f'不支持的数据库类型: {ds.db_type}')
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
        # Oracle 默认用 SERVICE_NAME 方式连接
        if ds.db_type == 'oracle':
            db_config['OPTIONS'] = {'service_name': ds.db_name}
        elif ds.db_type == 'sqlserver':
            db_config['OPTIONS'] = {
                'driver': 'ODBC Driver 18 for SQL Server',
                'extra_params': 'Encrypt=no',
            }
        connections.databases[alias] = db_config
        conn = connections[alias]
        conn.ensure_connection()
        return alias, conn

    @action(detail=True, methods=['get'], url_path='test-connection')
    def test_connection(self, request, pk=None):
        """测试已有数据源的连接"""
        ds = self.get_object()
        return self._do_test_connection(ds)

    @action(detail=False, methods=['post'], url_path='test-connection')
    def test_connection_params(self, request):
        """测试未保存的连接参数"""
        from .models import DataSource
        ds = DataSource(
            db_type=request.data.get('db_type', 'postgresql'),
            host=request.data.get('host', ''),
            port=request.data.get('port', 5432),
            db_name=request.data.get('db_name', ''),
            username=request.data.get('username', ''),
            password=request.data.get('password', ''),
        )
        return self._do_test_connection(ds)

    def _do_test_connection(self, ds):
        """执行连接测试"""
        from django.db import connections
        alias = f'_test_{ds.db_type}_{id(ds)}'
        try:
            engine = self._ENGINE_MAP.get(ds.db_type)
            if not engine:
                return Response(
                    {'success': False, 'error': f'不支持的数据库类型: {ds.db_type}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
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
            conn = connections[alias]
            conn.ensure_connection()
            # 执行一个简单查询验证连接可用
            with conn.cursor() as cursor:
                if ds.db_type == 'postgresql':
                    cursor.execute("SELECT 1")
                elif ds.db_type == 'mysql':
                    cursor.execute("SELECT 1")
                elif ds.db_type == 'sqlserver':
                    cursor.execute("SELECT 1")
                elif ds.db_type == 'oracle':
                    cursor.execute("SELECT 1 FROM DUAL")
            return Response({'success': True, 'message': f'连接成功！{ds.db_type}://{ds.host}:{ds.port}/{ds.db_name}'})
        except Exception as e:
            return Response(
                {'success': False, 'error': f'连接失败: {str(e)}'},
                status=status.HTTP_200_OK,
            )
        finally:
            connections.databases.pop(alias, None)

    @action(detail=True, methods=['get'], url_path='schemas')
    def list_schemas(self, request, pk=None):
        """列出数据源中的 schema；支持 ?include_counts=true 返回每个 schema 的表数量"""
        from django.db import connections
        ds = self.get_object()
        include_counts = request.query_params.get('include_counts', '').lower() in ('true', '1', 'yes')
        try:
            alias, conn = self._get_connection(ds)
            schemas = []
            schema_table_counts = {}  # schema_name -> table_count
            with conn.cursor() as cursor:
                if ds.db_type == 'postgresql':
                    cursor.execute(
                        "SELECT schema_name FROM information_schema.schemata "
                        "WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_toast') "
                        "ORDER BY schema_name"
                    )
                    schemas = [row[0] for row in cursor.fetchall()]
                    if include_counts:
                        cursor.execute(
                            "SELECT n.nspname, COUNT(*) FROM pg_class c "
                            "JOIN pg_namespace n ON n.oid = c.relnamespace "
                            "WHERE c.relkind='r' AND n.nspname NOT IN ('pg_catalog','information_schema','pg_toast') "
                            "GROUP BY n.nspname"
                        )
                        schema_table_counts = {row[0]: row[1] for row in cursor.fetchall()}
                elif ds.db_type == 'mysql':
                    cursor.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA "
                                   "WHERE SCHEMA_NAME NOT IN ('mysql','information_schema','performance_schema','sys') "
                                   "ORDER BY SCHEMA_NAME")
                    schemas = [row[0] for row in cursor.fetchall()]
                    if include_counts:
                        cursor.execute(
                            "SELECT TABLE_SCHEMA, COUNT(*) FROM information_schema.TABLES "
                            "WHERE TABLE_TYPE='BASE TABLE' "
                            "GROUP BY TABLE_SCHEMA"
                        )
                        schema_table_counts = {row[0]: row[1] for row in cursor.fetchall()}
                elif ds.db_type == 'sqlserver':
                    cursor.execute(
                        "SELECT schema_name FROM information_schema.schemata "
                        "WHERE schema_name NOT IN ('guest','INFORMATION_SCHEMA','sys') "
                        "ORDER BY CASE WHEN schema_name='dbo' THEN 0 ELSE 1 END, schema_name"
                    )
                    schemas = [row[0] for row in cursor.fetchall()]
                    if include_counts:
                        cursor.execute(
                            "SELECT SCHEMA_NAME(schema_id), COUNT(*) "
                            "FROM sys.tables GROUP BY schema_id"
                        )
                        schema_table_counts = {row[0]: row[1] for row in cursor.fetchall()}
                elif ds.db_type == 'oracle':
                    cursor.execute(
                        "SELECT DISTINCT owner FROM all_tables "
                        "WHERE owner NOT IN ('SYS','SYSTEM','XDB','CTXSYS','MDSYS','ORDSYS','OUTLN','WMSYS') "
                        "ORDER BY owner"
                    )
                    schemas = [row[0] for row in cursor.fetchall()]
                    if include_counts:
                        cursor.execute(
                            "SELECT owner, COUNT(*) FROM all_tables "
                            "WHERE owner NOT IN ('SYS','SYSTEM','XDB','CTXSYS','MDSYS','ORDSYS','OUTLN','WMSYS') "
                            "GROUP BY owner"
                        )
                        schema_table_counts = {row[0]: row[1] for row in cursor.fetchall()}
            del connections.databases[alias]
            result = {'schemas': schemas}
            if include_counts:
                result['schema_table_counts'] = {
                    s: schema_table_counts.get(s, 0) for s in schemas
                }
            return Response(result)
        except Exception as e:
            return Response(
                {'error': f'连接数据源失败: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=['get'], url_path='external-tables')
    def list_external_tables(self, request, pk=None):
        """列出指定数据源中的表名，支持 ?schema=<schema_name>&has_data=true 参数"""
        from django.db import connections
        ds = self.get_object()
        schema = request.query_params.get('schema', '')
        has_data_only = request.query_params.get('has_data', '').lower() in ('true', '1', 'yes')
        # 默认 schema 按数据库类型
        if not schema:
            schema = {'postgresql': 'public', 'sqlserver': 'dbo', 'oracle': '', 'mysql': ''}.get(ds.db_type, '')
        try:
            alias, conn = self._get_connection(ds)
            tables = []
            with conn.cursor() as cursor:
                if ds.db_type == 'postgresql':
                    cursor.execute(
                        "SELECT c.relname AS table_name, "
                        "  obj_description(c.oid) AS table_comment, "
                        "  c.reltuples::bigint AS row_estimate "
                        "FROM pg_class c "
                        "JOIN pg_namespace n ON n.oid = c.relnamespace "
                        "WHERE c.relkind='r' AND n.nspname=%s "
                        "ORDER BY c.relname",
                        [schema],
                    )
                    for row in cursor.fetchall():
                        tables.append({
                            'name': row[0],
                            'comment': row[1] or '',
                            'row_count': max(row[2], 0) if row[2] else 0,
                        })
                elif ds.db_type == 'mysql':
                    cursor.execute(
                        "SELECT TABLE_NAME, TABLE_COMMENT, TABLE_ROWS "
                        "FROM information_schema.TABLES "
                        "WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE' "
                        "ORDER BY TABLE_NAME",
                        [ds.db_name],
                    )
                    for row in cursor.fetchall():
                        tables.append({
                            'name': row[0],
                            'comment': row[1] or '',
                            'row_count': row[2] or 0,
                        })
                elif ds.db_type == 'sqlserver':
                    cursor.execute(
                        "SELECT t.name AS table_name, "
                        "  ISNULL(ep.value, '') AS table_comment, "
                        "  ISNULL(p.row_cnt, 0) AS row_count "
                        "FROM sys.tables t "
                        "LEFT JOIN sys.extended_properties ep "
                        "  ON ep.major_id=t.object_id AND ep.minor_id=0 AND ep.name='MS_Description' "
                        "LEFT JOIN ( "
                        "  SELECT object_id, SUM(rows) AS row_cnt "
                        "  FROM sys.partitions WHERE index_id IN (0,1) GROUP BY object_id "
                        ") p ON p.object_id=t.object_id "
                        "WHERE SCHEMA_NAME(t.schema_id)=%s "
                        "ORDER BY t.name",
                        [schema],
                    )
                    for row in cursor.fetchall():
                        tables.append({
                            'name': row[0],
                            'comment': str(row[1]) if row[1] else '',
                            'row_count': row[2] or 0,
                        })
                elif ds.db_type == 'oracle':
                    if schema:
                        cursor.execute(
                            "SELECT t.table_name, tc.comments, t.num_rows "
                            "FROM all_tables t "
                            "LEFT JOIN all_tab_comments tc ON tc.owner=t.owner AND tc.table_name=t.table_name "
                            "WHERE t.owner=%s ORDER BY t.table_name",
                            [schema.upper()],
                        )
                    else:
                        cursor.execute(
                            "SELECT t.table_name, tc.comments, t.num_rows "
                            "FROM user_tables t "
                            "LEFT JOIN user_tab_comments tc ON tc.table_name=t.table_name "
                            "ORDER BY t.table_name"
                        )
                    for row in cursor.fetchall():
                        tables.append({
                            'name': row[0],
                            'comment': row[1] or '',
                            'row_count': row[2] or 0,
                        })
            # 过滤只显示有数据的表
            if has_data_only:
                tables = [t for t in tables if t['row_count'] > 0]
            del connections.databases[alias]
            return Response({'tables': tables, 'schema': schema})
        except Exception as e:
            return Response(
                {'error': f'连接数据源失败: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DomainViewSet(viewsets.ModelViewSet):
    """域管理 API"""
    queryset = Domain.objects.all()
    search_fields = ['name', 'code']
    filterset_fields = ['status']

    def get_serializer_class(self):
        if self.action == 'list':
            return DomainSerializer
        return DomainDetailSerializer

    @action(detail=True, methods=['get'], url_path='pk-status')
    def pk_status(self, request, pk=None):
        """检查域下所有表的主键配置状态和关系配置状态"""
        domain = self.get_object()
        tables = Table.objects.filter(domain=domain, status='active')
        result = []
        all_configured = True
        for t in tables:
            pk_fields = list(
                Field.objects.filter(table=t, is_primary_key=True)
                .order_by('sort_order', 'id')
                .values('id', 'code', 'name', 'comment', 'sort_order')
            )
            # 检查该表是否已配置关系（作为源表或目标表均可）
            has_mapping = FieldMapping.objects.filter(Q(source_table=t) | Q(target_table=t)).exists()
            is_configured = len(pk_fields) > 0 and has_mapping
            if not is_configured:
                all_configured = False
            result.append({
                'table_id': t.id,
                'table_code': t.code,
                'table_name': t.name,
                'pk_fields': pk_fields,
                'has_pk': len(pk_fields) > 0,
                'has_mapping': has_mapping,
                'is_configured': is_configured,
            })
        return Response({
            'tables': result,
            'all_configured': all_configured,
            'total': len(result),
            'configured_count': sum(1 for r in result if r['is_configured']),
        })

class TableViewSet(viewsets.ModelViewSet):
    """表管理 API"""
    queryset = Table.objects.select_related('domain').all()
    search_fields = ['name', 'code']
    filterset_fields = ['domain', 'type', 'status']

    def get_serializer_class(self):
        if self.action == 'list':
            return TableListSerializer
        return TableCreateSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        domain_id = self.request.query_params.get('domain')
        if domain_id:
            qs = qs.filter(domain_id=domain_id)
        return qs

    def perform_create(self, serializer):
        """创建表后，如果是数据源表，自动从外部数据库同步字段结构"""
        instance = serializer.save()
        if instance.data_source and instance.external_table_name:
            schema = self.request.data.get('schema', '')
            try:
                self._sync_external_table_fields(instance, schema)
            except Exception as e:
                # 字段同步失败不影响表的创建，只记录警告
                import logging
                logging.getLogger(__name__).warning(
                    f'同步外部表字段失败 {instance.external_table_name}: {e}'
                )

    def _sync_external_table_fields(self, table, schema=''):
        """从外部数据库获取表的字段结构，创建 Field 记录"""
        from django.db import connections
        from .models import Field
        ds = table.data_source
        engine = DataSourceViewSet._ENGINE_MAP.get(ds.db_type)
        if not engine:
            return
        # 默认 schema
        if not schema:
            schema = {'postgresql': 'public', 'sqlserver': 'dbo', 'oracle': '', 'mysql': ''}.get(ds.db_type, '')
        alias = f'_sync_{ds.id}_{table.id}'
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
            columns = []
            with conn.cursor() as cursor:
                ext_table = table.external_table_name
                if ds.db_type == 'postgresql':
                    cursor.execute(
                        "SELECT c.column_name, c.data_type, c.character_maximum_length, "
                        "  c.is_nullable, c.column_default, '' "
                        "FROM information_schema.columns c "
                        "WHERE c.table_schema=%s AND c.table_name=%s "
                        "ORDER BY c.ordinal_position",
                        [schema, ext_table],
                    )
                    columns = cursor.fetchall()
                elif ds.db_type == 'mysql':
                    cursor.execute(
                        "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, "
                        "  IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT "
                        "FROM information_schema.COLUMNS "
                        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s "
                        "ORDER BY ORDINAL_POSITION",
                        [ds.db_name, ext_table],
                    )
                    columns = cursor.fetchall()
                elif ds.db_type == 'sqlserver':
                    cursor.execute(
                        "SELECT c.COLUMN_NAME, c.DATA_TYPE, c.CHARACTER_MAXIMUM_LENGTH, "
                        "  c.IS_NULLABLE, c.COLUMN_DEFAULT, "
                        "  ISNULL(CAST(ep.value AS NVARCHAR(MAX)), '') "
                        "FROM INFORMATION_SCHEMA.COLUMNS c "
                        "LEFT JOIN sys.columns sc "
                        "  ON sc.object_id = OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME) "
                        "  AND sc.name = c.COLUMN_NAME "
                        "LEFT JOIN sys.extended_properties ep "
                        "  ON ep.major_id = sc.object_id AND ep.minor_id = sc.column_id "
                        "  AND ep.name = 'MS_Description' "
                        "WHERE c.TABLE_SCHEMA = %s AND c.TABLE_NAME = %s "
                        "ORDER BY c.ORDINAL_POSITION",
                        [schema, ext_table],
                    )
                    columns = cursor.fetchall()
                elif ds.db_type == 'oracle':
                    owner = schema.upper() if schema else None
                    if owner:
                        cursor.execute(
                            "SELECT c.column_name, c.data_type, c.data_length, "
                            "  c.nullable, c.data_default, cc.comments "
                            "FROM all_tab_columns c "
                            "LEFT JOIN all_col_comments cc "
                            "  ON cc.owner=c.owner AND cc.table_name=c.table_name "
                            "  AND cc.column_name=c.column_name "
                            "WHERE c.owner=%s AND c.table_name=%s "
                            "ORDER BY c.column_id",
                            [owner, ext_table.upper()],
                        )
                    else:
                        cursor.execute(
                            "SELECT c.column_name, c.data_type, c.data_length, "
                            "  c.nullable, c.data_default, cc.comments "
                            "FROM user_tab_columns c "
                            "LEFT JOIN user_col_comments cc "
                            "  ON cc.table_name=c.table_name AND cc.column_name=c.column_name "
                            "WHERE c.table_name=%s "
                            "ORDER BY c.column_id",
                            [ext_table.upper()],
                        )
                    columns = cursor.fetchall()
            # 创建 Field 记录
            type_map = self._map_db_type
            for idx, col in enumerate(columns):
                col_name = col[0]
                col_type = (col[1] or '').lower()
                col_length = col[2]
                col_nullable = col[3] if len(col) > 3 else 'YES'
                col_comment = col[5] if len(col) > 5 else ''
                field_type = type_map(col_type)
                Field.objects.create(
                    table=table,
                    name=col_name,
                    code=col_name,
                    comment=str(col_comment) if col_comment else '',
                    field_type=field_type,
                    length=col_length,
                    required=str(col_nullable).upper() == 'NO' if col_nullable else False,
                    sort_order=idx,
                )
        finally:
            connections.databases.pop(alias, None)

    @staticmethod
    def _map_db_type(db_type: str) -> str:
        """将外部数据库的类型映射为 Field.FieldType"""
        db_type = db_type.lower().strip()
        # 数字类型
        if db_type in ('int', 'integer', 'bigint', 'smallint', 'tinyint', 'mediumint',
                       'numeric', 'decimal', 'number', 'float', 'double', 'real',
                       'money', 'smallmoney', 'double precision', 'float4', 'float8',
                       'serial', 'bigserial'):
            return 'number'
        # 日期类型
        if db_type in ('date', 'datetime', 'timestamp', 'timestamptz', 'time', 'timetz',
                       'datetime2', 'smalldatetime', 'datetimeoffset', 'year'):
            return 'date'
        # 布尔类型
        if db_type in ('bit', 'boolean', 'bool'):
            return 'boolean'
        # 其余均为字符串
        return 'string'

    def update(self, request, *args, **kwargs):
        # 支持部分更新，因为 type/data_source 等字段创建后不可修改
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(TableListSerializer(instance).data)

    @action(detail=True, methods=['put'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        """切换表启用/停用。停用前拦截：若表参与字段映射则不允许停用。"""
        table = self.get_object()
        target = request.data.get('status')
        if target not in (Table.Status.ACTIVE, Table.Status.DEPRECATED):
            return Response({'error': '无效的状态值'}, status=status.HTTP_400_BAD_REQUEST)

        if target == Table.Status.DEPRECATED:
            related = FieldMapping.objects.filter(
                models.Q(source_table=table) | models.Q(target_table=table)
            ).select_related('source_table', 'source_field', 'target_table', 'target_field')
            if related.exists():
                mappings = [
                    {
                        'id': m.id,
                        'source': f'{m.source_table.name}.{m.source_field.name}',
                        'target': f'{m.target_table.name}.{m.target_field.name}',
                    }
                    for m in related
                ]
                return Response(
                    {
                        'error': '该表存在字段映射关系，请先到「关系管理」解除后再停用。',
                        'mappings': mappings,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        table.status = target
        table.save(update_fields=['status', 'updated_at'])
        return Response(TableListSerializer(table).data)

    @action(detail=True, methods=['get'], url_path='preview-data')
    def preview_data(self, request, pk=None):
        """获取表的数据预览（最多 100 行）"""
        table = self.get_object()
        limit = min(int(request.query_params.get('limit', 100)), 500)
        try:
            if table.data_source and table.external_table_name:
                return self._preview_external_data(table, limit)
            else:
                return self._preview_local_data(table, limit)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'数据预览失败: {e}')
            return Response({'error': f'数据预览失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    def _preview_local_data(self, table, limit):
        """预览本地表数据"""
        from django.db import connection
        columns = []
        rows = []
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT * FROM "{table.code}" LIMIT %s', [limit])
            columns = [desc[0] for desc in cursor.description]
            rows = [[_json_safe(v) for v in row] for row in cursor.fetchall()]
        return Response({'columns': columns, 'rows': rows})

    def _preview_external_data(self, table, limit):
        """预览外部数据源表数据"""
        from django.db import connections
        ds = table.data_source
        engine = DataSourceViewSet._ENGINE_MAP.get(ds.db_type)
        if not engine:
            return Response({'error': f'不支持的数据库类型: {ds.db_type}'}, status=status.HTTP_400_BAD_REQUEST)
        alias = f'_preview_{ds.id}_{table.id}'
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
            columns = []
            rows = []
            with conn.cursor() as cursor:
                ext_table = table.external_table_name
                # 使用表保存的 schema，或使用默认值
                schema = table.schema or {'postgresql': 'public', 'sqlserver': 'dbo', 'oracle': '', 'mysql': ''}.get(ds.db_type, '')
                # 构建查询 SQL
                if ds.db_type == 'sqlserver':
                    full_table = f'[{schema}].[{ext_table}]'
                    cursor.execute(f'SELECT TOP {limit} * FROM {full_table}')
                elif ds.db_type == 'oracle':
                    owner = schema.upper() if schema else ''
                    full_table = f'"{owner}"."{ext_table}"' if owner else f'"{ext_table}"'
                    cursor.execute(f'SELECT * FROM {full_table} WHERE ROWNUM <= %s', [limit])
                elif ds.db_type == 'mysql':
                    cursor.execute(f'SELECT * FROM `{ext_table}` LIMIT %s', [limit])
                else:  # postgresql
                    full_table = f'"{schema}"."{ext_table}"'
                    cursor.execute(f'SELECT * FROM {full_table} LIMIT %s', [limit])
                columns = [desc[0] for desc in cursor.description]
                rows = [[_json_safe(v) for v in row] for row in cursor.fetchall()]
            return Response({'columns': columns, 'rows': rows})
        finally:
            connections.databases.pop(alias, None)

    @action(detail=False, methods=['post'], url_path='preview-excel')
    def preview_excel(self, request):
        """预览单个 Excel 文件：解析列 + 样本行 + 推断字段类型。"""
        from . import excel_service
        f = request.FILES.get('file')
        if not f:
            return Response({'error': '未上传文件'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            parsed = excel_service.parse_excel(f)
            if not parsed['columns']:
                return Response({'error': 'Excel 为空或无法解析'}, status=status.HTTP_400_BAD_REQUEST)
            fields = excel_service.infer_field_types(parsed['columns'], parsed['rows'])
            # 样本行转为可 JSON 序列化的形式
            rows_serialized = []
            for r in parsed['rows']:
                rows_serialized.append([_json_safe(c) for c in r])
            return Response({
                'columns': parsed['columns'],
                'rows': rows_serialized,
                'inferred_fields': fields,
            })
        except Exception as e:
            return Response({'error': f'解析失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='import-excel')
    def import_excel(self, request):
        """批量导入 Excel 文件，为每个文件在本地建表并创建 Table/Field 记录。

        请求：multipart/form-data
          - files: 多个 Excel 文件
          - configs: JSON 字符串，格式 [{file_name, code, name_en, name_cn}, ...]
        """
        import json as _json
        from . import excel_service
        files = request.FILES.getlist('files')
        configs_str = request.data.get('configs', '[]')
        if isinstance(configs_str, list):
            configs = configs_str
        else:
            try:
                configs = _json.loads(configs_str)
            except _json.JSONDecodeError:
                return Response({'error': 'configs 格式错误，需要 JSON 数组'}, status=status.HTTP_400_BAD_REQUEST)
        domain_id = request.data.get('domain')
        if not domain_id:
            return Response({'error': '缺少 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        if not files:
            return Response({'error': '未上传任何文件'}, status=status.HTTP_400_BAD_REQUEST)

        # 按文件名匹配配置
        config_map = {c.get('file_name'): c for c in configs}
        created = []
        errors = []
        for f in files:
            cfg = config_map.get(f.name) or {}
            if not cfg.get('code'):
                errors.append({'file_name': f.name, 'error': '缺少编码配置'})
                continue
            try:
                parsed = excel_service.parse_excel(f)
                fields = excel_service.infer_field_types(parsed['columns'], parsed['rows'])
                table = excel_service.create_local_table_from_excel(
                    domain_id=domain_id,
                    file_name=f.name,
                    table_code=cfg.get('code'),
                    table_name_en=cfg.get('name_en') or cfg.get('code'),
                    table_name_cn=cfg.get('name_cn') or '',
                    fields=fields,
                )
                created.append({
                    'file_name': f.name,
                    'table_id': table.id,
                    'table_code': table.code,
                    'field_count': len(fields),
                })
            except Exception as e:
                errors.append({'file_name': f.name, 'error': str(e)})
        return Response({'created': created, 'errors': errors})

    @action(detail=True, methods=['put'], url_path='save-er-position')
    def save_er_position(self, request, pk=None):
        """保存 ER 图中该表节点的位置（x, y）"""
        table = self.get_object()
        x = request.data.get('er_node_x')
        y = request.data.get('er_node_y')
        if x is None or y is None:
            return Response({'error': '缺少 er_node_x 或 er_node_y'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            table.er_node_x = int(x)
            table.er_node_y = int(y)
            table.save(update_fields=['er_node_x', 'er_node_y', 'updated_at'])
        except (ValueError, TypeError):
            return Response({'error': '坐标值必须为整数'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'id': table.id, 'er_node_x': table.er_node_x, 'er_node_y': table.er_node_y})

    @action(detail=False, methods=['post'], url_path='batch-reset-er-position')
    def batch_reset_er_position(self, request):
        """批量清空某域下所有表的 ER 图位置（用于重置布局）"""
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '缺少 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        n = Table.objects.filter(domain_id=domain_id).exclude(er_node_x__isnull=True).update(er_node_x=None, er_node_y=None)
        return Response({'reset_count': n})

    @action(detail=True, methods=['post'], url_path='set-primary')
    def set_primary(self, request, pk=None):
        """将此表设为域的主表，同时取消同域其他表的主表标识"""
        table = self.get_object()
        table.set_as_primary()
        return Response({'id': table.id, 'is_primary': table.is_primary, 'message': '已设为主表'})


class FieldGroupViewSet(viewsets.ModelViewSet):
    """字段分组 API（支持多层嵌套，最多3层）"""
    queryset = FieldGroup.objects.all()
    serializer_class = FieldGroupSerializer
    filterset_fields = ['domain', 'parent']

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.query_params.get('tree') == '1':
            ctx['tree_mode'] = True
        return ctx

    def get_queryset(self):
        qs = super().get_queryset()
        # 树形模式只返回顶层分组（children 递归在 serializer 展开）
        if self.request.query_params.get('tree') == '1':
            qs = qs.filter(parent__isnull=True)
        return qs

    def perform_destroy(self, instance):
        """删除分组时：子分组上浮到父级，直属字段变为未分组"""
        # 子分组上浮
        instance.children.update(parent=instance.parent)
        # 直属字段变未分组
        instance.fields.update(group=None)
        instance.delete()

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """同父级内批量重排序。

        请求体: {"ordered_ids": [id1, id2, ...]} — 按目标顺序的分组ID列表
        按传入顺序依次写入 sort_order = 0,1,2,...
        """
        ordered_ids = request.data.get('ordered_ids')
        if not isinstance(ordered_ids, list) or not ordered_ids:
            return Response({'error': '必须提供 ordered_ids 数组'}, status=status.HTTP_400_BAD_REQUEST)

        groups = {g.id: g for g in FieldGroup.objects.filter(id__in=ordered_ids)}
        updated = []
        for idx, gid in enumerate(ordered_ids):
            g = groups.get(gid)
            if g and g.sort_order != idx:
                g.sort_order = idx
                updated.append(g)
        if updated:
            FieldGroup.objects.bulk_update(updated, ['sort_order'])
        return Response({'updated': len(updated)})


class FieldOptionViewSet(viewsets.ModelViewSet):
    """枚举选项 API"""
    queryset = FieldOption.objects.all()
    serializer_class = FieldOptionSerializer
    filterset_fields = ['field']


class FieldViewSet(viewsets.ModelViewSet):
    """字段定义 API"""
    queryset = Field.objects.select_related('group', 'table').prefetch_related('options').all()
    filterset_fields = ['table', 'table__domain', 'status', 'field_type', 'group']

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return FieldListSerializer
        return FieldListSerializer

    @action(detail=False, methods=['get'], url_path='field-categories')
    def field_categories(self, request):
        """返回域下各字段分类计数（左栏导航用）。

        返回：{
          'base': N,           # 基础字段（archive_category='base' 且 standard_field=null 且 status='active'）
          'composite': N,      # 组合字段（StandardField 且 status='active'）
          'computed': N,       # 计算字段（ComputedField 且 status='active'）
          'unassigned': N,     # 未分配字段（archive_category='unassigned' 且 standard_field=null 且 status='active'）
          'discarded': N,      # 废弃字段（物理+标准+计算）
        }
        """
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 基础字段：archive_category='base'，不属于任何StandardField，状态活跃
        base_count = Field.objects.filter(
            table__domain_id=domain_id, status=Field.Status.ACTIVE,
            archive_category=Field.ArchiveCategory.BASE,
            standard_field__isnull=True,
        ).count()

        # 组合字段：StandardField status='active'
        composite_count = StandardField.objects.filter(
            domain_id=domain_id, status='active'
        ).count()

        # 计算字段：ComputedField status='active'
        computed_count = ComputedField.objects.filter(
            domain_id=domain_id, status=ComputedField.Status.ACTIVE
        ).count()

        # 未分配字段：archive_category='unassigned'，不属于任何StandardField，状态活跃
        unassigned_count = Field.objects.filter(
            table__domain_id=domain_id, status=Field.Status.ACTIVE,
            archive_category=Field.ArchiveCategory.UNASSIGNED,
            standard_field__isnull=True,
        ).count()

        # 废弃字段：物理字段 deprecated + 标准字段 discarded + 计算字段 discarded
        discarded_physical = Field.objects.filter(
            table__domain_id=domain_id, status=Field.Status.DEPRECATED
        ).count()
        discarded_standard = StandardField.objects.filter(
            domain_id=domain_id, status='discarded'
        ).count()
        discarded_computed = ComputedField.objects.filter(
            domain_id=domain_id, status=ComputedField.Status.DISCARDED
        ).count()

        return Response({
            'base': base_count,
            'composite': composite_count,
            'computed': computed_count,
            'unassigned': unassigned_count,
            'discarded': discarded_physical + discarded_standard + discarded_computed,
        })

    @action(detail=False, methods=['post'], url_path='batch')
    def batch_save(self, request):
        """批量保存字段名称"""
        table_id = request.query_params.get('table')
        if not table_id:
            return Response({'error': '必须指定 table 参数'}, status=status.HTTP_400_BAD_REQUEST)
        table = get_object_or_404(Table, id=table_id)

        serializer = FieldBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        fields_data = serializer.validated_data['fields']
        created = []
        for item in fields_data:
            field, _ = Field.objects.update_or_create(
                table=table, code=item.get('code', ''),
                defaults={'name': item['name'], 'sort_order': item.get('sort_order', 0)}
            )
            created.append(FieldListSerializer(field).data)
        return Response(created, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['put'], url_path='batch-attributes')
    def batch_update_attributes(self, request):
        """批量更新字段属性（含枚举选项）"""
        serializer = FieldBatchUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = []
        for item in serializer.validated_data['fields']:
            field = get_object_or_404(Field, id=item['id'])
            for attr in ['field_type', 'length', 'required', 'default_value', 'date_format',
                         'validation_rule', 'sort_order', 'status',
                         'comment', 'semantic_note', 'is_primary_key',
                         'release_to_concept', 'release_to_archive', 'archive_category', 'ownership']:
                if attr in item:
                    setattr(field, attr, item[attr])
            # group 为 FK，必须用 group_id 赋值（整数）
            if 'group' in item:
                field.group_id = item['group']
            field.save()

            # 处理枚举选项
            if 'options' in item and isinstance(item['options'], list):
                # 清除旧选项，写入新选项
                field.options.all().delete()
                for idx, opt in enumerate(item['options']):
                    FieldOption.objects.create(
                        field=field,
                        label=opt.get('label', ''),
                        value=opt.get('value', ''),
                        sort_order=idx,
                    )

            updated.append(FieldListSerializer(field).data)
        return Response(updated)

    @action(detail=True, methods=['put'], url_path='deprecate')
    def deprecate(self, request, pk=None):
        """作废字段"""
        field = self.get_object()
        field.status = Field.Status.DEPRECATED
        field.save()
        return Response(FieldListSerializer(field).data)

    @action(detail=False, methods=['post'], url_path='ai-analyze')
    def ai_analyze(self, request):
        """AI字段分类与冗余检测"""
        table_id = request.query_params.get('table')
        if not table_id:
            return Response({'error': '必须指定 table 参数'}, status=status.HTTP_400_BAD_REQUEST)
        table = get_object_or_404(Table, id=table_id)
        fields = Field.objects.filter(table=table, status=Field.Status.ACTIVE)

        if not fields.exists():
            return Response({'error': '该表没有可分析的字段'}, status=status.HTTP_400_BAD_REQUEST)

        # 模拟AI分类结果
        field_names = [f.name for f in fields]
        n = len(field_names)
        # 简单均分为3组作为模拟结果
        third = max(1, n // 3) if n > 2 else n
        groups = []
        group_names = ['基本信息', '业务信息', '扩展信息']
        for i, gname in enumerate(group_names):
            start = i * third
            end = start + third if i < 2 else n
            chunk = fields[start:end]
            if chunk:
                groups.append({
                    'name': gname,
                    'fields': [{'id': f.id, 'name': f.name, 'code': f.code} for f in chunk],
                })

        # 模拟冗余检测
        redundant = []
        seen = {}
        for f in fields:
            base = f.name.replace(' ', '').lower()
            if base in seen:
                redundant.append({'id': f.id, 'name': f.name, 'code': f.code,
                                  'similar_to': seen[base]})
            else:
                seen[base] = f.name

        return Response({
            'groups': groups,
            'redundant_fields': redundant,
        })

    @action(detail=False, methods=['post'], url_path='ai-auto-group')
    def ai_auto_group(self, request):
        """域级字段 AI 自动分组：对域下 active 字段分组，创建/复用分组并回写。"""
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        domain = get_object_or_404(Domain, id=domain_id)
        fields = list(Field.objects.filter(
            table__domain=domain, status=Field.Status.ACTIVE
        ).select_related('table'))
        if not fields:
            return Response({'error': '该域没有可分组的字段'}, status=status.HTTP_400_BAD_REQUEST)

        result = ai_service.auto_group_fields(fields)

        groups_out = []
        for idx, g in enumerate(result):
            group_obj, _ = FieldGroup.objects.get_or_create(
                domain=domain, name=g['name'],
                defaults={'sort_order': idx},
            )
            Field.objects.filter(id__in=g['field_ids']).update(group=group_obj)
            groups_out.append({
                'group_id': group_obj.id,
                'name': group_obj.name,
                'field_ids': g['field_ids'],
            })
        return Response({'groups': groups_out})

    @action(detail=False, methods=['post'], url_path='ai-semantic')
    def ai_semantic(self, request):
        """域级字段 AI 语义识别：补全空注释 + 翻译英文注释为中文 + 写入同义/歧义标识。"""
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        domain = get_object_or_404(Domain, id=domain_id)
        fields = list(Field.objects.filter(
            table__domain=domain, status=Field.Status.ACTIVE
        ).select_related('table'))
        if not fields:
            return Response({'error': '该域没有可识别的字段'}, status=status.HTTP_400_BAD_REQUEST)

        field_map = {f.id: f for f in fields}
        result = ai_service.semantic_recognition(fields)

        # 对空注释填补，对纯英文注释翻译为中文
        import re as _re
        for fid, comment in result.get('comments', {}).items():
            f = field_map.get(fid)
            if not f or not comment:
                continue
            need_update = False
            if not f.comment:
                f.comment = comment
                need_update = True
            elif _re.search(r'[a-zA-Z]', f.comment) and not _re.search(r'[一-鿿]', f.comment):
                # 纯英文注释：用 AI 翻译结果替换
                f.comment = comment
                need_update = True
            if need_update:
                f.save(update_fields=['comment', 'updated_at'])
        # 写入语义标识
        for mark in result.get('marks', []):
            f = field_map.get(mark['id'])
            if f:
                f.semantic_note = mark['semantic_note']
                f.save(update_fields=['semantic_note', 'updated_at'])

        updated = Field.objects.filter(
            id__in=field_map.keys()
        ).select_related('group', 'table').prefetch_related('options')
        return Response(FieldListSerializer(updated, many=True).data)

    @action(detail=False, methods=['post'], url_path='detect-standards')
    def detect_standards(self, request):
        """检测跨表冗余（标准字段）建议，AI 优先 + 启发式降级。仅返回建议，不落库。"""
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        domain = get_object_or_404(Domain, id=domain_id)
        fields = list(Field.objects.filter(
            table__domain=domain, status=Field.Status.ACTIVE
        ).select_related('table'))
        if not fields:
            return Response({'error': '该域没有可检测的字段'}, status=status.HTTP_400_BAD_REQUEST)

        field_map = {f.id: f for f in fields}
        # 三层匹配第三层：确保去重内容缓存已填充，并传入 detect 供 LLM 综合判断
        _ensure_distinct_cache(fields)
        distinct_map = {f.id: f.distinct_values for f in fields if f.distinct_values}
        suggestions = ai_service.detect_duplicate_fields(fields, distinct_map=distinct_map)
        # 补充成员明细（表名/中文名）供前端展示
        groups = []
        for g in suggestions:
            members = []
            for fid in g['field_ids']:
                f = field_map.get(fid)
                if not f:
                    continue
                members.append({
                    'id': f.id, 'code': f.code, 'name': f.name, 'comment': f.comment,
                    'table': f.table_id, 'table_name': f.table.name,
                    'already_grouped': f.standard_field_id is not None,
                })
            if len(members) >= 2:
                groups.append({
                    'standard_code': g['standard_code'],
                    'standard_name': g['standard_name'],
                    'field_ids': g['field_ids'],
                    'members': members,
                })
        return Response({'groups': groups})

    @action(detail=False, methods=['post'], url_path='apply-standards')
    def apply_standards(self, request):
        """应用去重：创建/复用标准字段并回写 Field.standard_field。

        请求体：{"groups":[{"standard_code":"","standard_name":"","field_ids":[..]}]}。
        物理字段全部保留，仅记录归并关系。
        """
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        domain = get_object_or_404(Domain, id=domain_id)
        groups_in = request.data.get('groups', [])
        if not isinstance(groups_in, list) or not groups_in:
            return Response({'error': 'groups 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        result = []
        for g in groups_in:
            std_code = (g.get('standard_code') or '').strip()
            field_ids = g.get('field_ids') or []
            if not std_code or len(field_ids) < 2:
                continue
            sf, _ = StandardField.objects.update_or_create(
                domain=domain, standard_code=std_code,
                defaults={
                    'standard_name': (g.get('standard_name') or '')[:200],
                    'note': (g.get('note') or '')[:500],
                    'source': g.get('source') or StandardField.Source.AI,
                },
            )
            # 仅回写本域下的字段，防止跨域误挂
            Field.objects.filter(id__in=field_ids, table__domain=domain).update(standard_field=sf)
            sf.auto_assign_primary_field()
            result.append(sf.id)

        groups_out = StandardField.objects.filter(
            id__in=result
        ).prefetch_related('members__table')
        return Response(StandardFieldSerializer(groups_out, many=True).data)

    @action(detail=False, methods=['get'], url_path='standard-fields')
    def standard_fields(self, request):
        """返回域下的“标准字段”列表（分组 Tab 专用）。

        标准字段聚合为一行（kind='equiv'），独立物理字段各自一行（kind='solo'）。
        每行携带 physical_field_ids，拖拽分组时批量更新这些物理字段的 group。
        """
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)

        fields = Field.objects.filter(
            table__domain_id=domain_id, status=Field.Status.ACTIVE
        ).select_related('table', 'group', 'standard_field').order_by('id')

        # 标准字段 → 聚合
        sf_map = {}  # sf_id -> {ids, first_group, first_group_name}
        field_map = {}  # field_id -> Field（主字段 label 查找用）
        for f in fields:
            field_map[f.id] = f
            sf_id = f.standard_field_id
            if not sf_id:
                continue
            bucket = sf_map.setdefault(sf_id, {
                'ids': [], 'first_group': None, 'first_group_name': None, 'distinct': [],
                'tables': {}, 'is_pk': False,
            })
            bucket['ids'].append(f.id)
            # 成员所属表（去重）+ 主键标记（任一成员为主键即置位）
            if f.table_id and f.table_id not in bucket['tables']:
                bucket['tables'][f.table_id] = {'name': f.table.name, 'is_primary': f.table.is_primary}
            if f.is_primary_key:
                bucket['is_pk'] = True
            # 成员去重值并集（读缓存，不查库），供属性配置 Tab 展示
            if f.distinct_values:
                for v in f.distinct_values:
                    if v not in bucket['distinct']:
                        bucket['distinct'].append(v)
            if bucket['first_group'] is None:
                bucket['first_group'] = f.group_id
                bucket['first_group_name'] = f.group.name if f.group else ''

        sf_ids = list(sf_map.keys())
        sf_lookup = {}
        if sf_ids:
            for sf in StandardField.objects.filter(id__in=sf_ids, status='active'):
                sf_lookup[sf.id] = sf

        result = []
        equiv_field_ids = set()
        for sf_id, info in sf_map.items():
            sf = sf_lookup.get(sf_id)
            if not sf:
                continue
            # 主字段：失效成员（非 active）视为未设置
            pf = field_map.get(sf.primary_field_id) if sf.primary_field_id else None
            result.append({
                'kind': 'equiv',
                'key': f'equiv_{sf_id}',
                'sf_id': sf_id,
                'standard_code': sf.standard_code,
                'standard_name': sf.standard_name,
                'physical_field_ids': info['ids'],
                'group': info['first_group'],
                'group_name': info['first_group_name'],
                'source': sf.source,
                'member_count': len(info['ids']),
                'release_to_archive': sf.release_to_archive,
                'field_type': sf.field_type,
                'length': sf.length,
                'required': sf.required,
                'default_value': sf.default_value,
                'is_active': sf.is_active,
                'ownership': sf.ownership,
                'distinct_values': info['distinct'][:50],
                'tables': list(info['tables'].values()),
                'is_primary_key': info['is_pk'],
                'primary_field_id': pf.id if pf else None,
                'primary_field_label': (f'{pf.table.name}.{pf.code}' if pf and pf.table_id else (pf.code if pf else None)),
                'primary_field_manual': sf.primary_field_manual,
            })
            equiv_field_ids.update(info['ids'])

        # 独立物理字段（不属于任何标准字段）——只包含已归入档案的基础字段
        for f in fields:
            if f.id in equiv_field_ids:
                continue
            if f.archive_category != 'base':
                continue
            result.append({
                'kind': 'solo',
                'key': f'solo_{f.id}',
                'sf_id': None,
                'standard_code': f.code,
                'standard_name': f.comment or f.name,
                'physical_field_ids': [f.id],
                'group': f.group_id,
                'group_name': f.group.name if f.group else '',
                'source': None,
                'member_count': 1,
                'release_to_archive': f.release_to_archive,
                'field_type': f.field_type,
                'length': f.length,
                'required': f.required,
                'default_value': f.default_value,
                'is_active': None,
                'ownership': f.ownership,
                'distinct_values': (f.distinct_values or [])[:50],
                'tables': [{'name': f.table.name, 'is_primary': f.table.is_primary}] if f.table_id else [],
                'is_primary_key': f.is_primary_key,
            })

        return Response(StandardFieldAggregateSerializer(result, many=True).data)

    @action(detail=False, methods=['post'], url_path='refresh-distinct')
    def refresh_distinct(self, request):
        """刷新域下 active 字段的数据去重内容缓存（强制重查）。"""
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        fields = list(Field.objects.filter(
            table__domain_id=domain_id, status=Field.Status.ACTIVE
        ).select_related('table', 'table__data_source'))
        result = _ensure_distinct_cache(fields, force=True)
        return Response(result)

    @action(detail=True, methods=['post'], url_path='load-sample-values')
    def load_sample_values(self, request, pk=None):
        """刷新单个字段的去重值缓存并返回前10条样本值。"""
        field = self.get_object()
        vals = _fetch_distinct_values(field.table, field.code, limit=100)
        field.distinct_values = vals
        from django.utils import timezone
        field.distinct_synced_at = timezone.now()
        field.save(update_fields=['distinct_values', 'distinct_synced_at', 'updated_at'])
        return Response({'sample_values': vals[:10] if vals else []})

    @action(detail=False, methods=['get'], url_path='manual-candidates')
    def manual_candidates(self, request):
        """手动新增标准字段的候选字段列表。

        仅返回域下 active 且未配置标准字段（standard_field 为空）的字段，
        携带来源与已缓存的去重内容（不在此强制查库）。
        """
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        fields = Field.objects.filter(
            table__domain_id=domain_id, status=Field.Status.ACTIVE,
            standard_field__isnull=True,
        ).select_related('table', 'table__data_source').order_by('table_id', 'sort_order', 'id')
        items = []
        for f in fields:
            t = f.table
            source_label = t.name
            items.append({
                'id': f.id,
                'code': f.code,
                'name': f.name,
                'comment': f.comment,
                'table_name': t.name,
                'source_label': source_label,
                'distinct_values': f.distinct_values,
                'distinct_synced_at': f.distinct_synced_at.isoformat() if f.distinct_synced_at else None,
                'release_to_archive': f.release_to_archive,
                'release_to_concept': f.release_to_concept,
                'archive_category': f.archive_category,
            })
        return Response({'candidates': items})

    @action(detail=False, methods=['get'], url_path='archive-preview')
    def archive_preview(self, request):
        """只读预览：返回当前域最终释放到档案的字段及其物理表关系。

        复用 archive 模块的 _generate_schema_from_domain（两层释放门控 + 去重），
        不会触发任何写操作，仅供前端“确认到档案”弹窗展示。
        返回：{'schema': [{'code','name','type','group','table',...}]}。
        """
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        domain = get_object_or_404(Domain, id=domain_id)
        from apps.archive.views import _generate_schema_from_domain
        schema = _generate_schema_from_domain(domain)
        return Response({'schema': schema})


class StandardFieldViewSet(viewsets.ModelViewSet):
    """标准字段（概念层一等公民）API。支持列表/手动新增/解散（删除）。"""
    queryset = StandardField.objects.prefetch_related('members__table').all()
    serializer_class = StandardFieldSerializer
    filterset_fields = ['domain', 'source']

    def create(self, request, *args, **kwargs):
        """手动新增标准字段：创建 StandardField 并挂靠成员物理字段。

        请求体：{"domain":id, "standard_code":"", "standard_name":"", "member_field_ids":[..]}。
        物理字段全部保留，仅记录归并关系。
        """
        domain_id = request.data.get('domain')
        std_code = (request.data.get('standard_code') or '').strip()
        if not domain_id or not std_code:
            return Response({'error': 'domain 与 standard_code 为必填'}, status=status.HTTP_400_BAD_REQUEST)
        domain = get_object_or_404(Domain, id=domain_id)
        member_field_ids = request.data.get('member_field_ids') or []
        sf, created = StandardField.objects.update_or_create(
            domain=domain, standard_code=std_code,
            defaults={
                'standard_name': (request.data.get('standard_name') or '')[:200],
                'note': (request.data.get('note') or '')[:500],
                'source': StandardField.Source.MANUAL,
            },
        )
        if member_field_ids:
            # 仅回写本域下的字段，防止跨域误挂
            Field.objects.filter(id__in=member_field_ids, table__domain=domain).update(standard_field=sf)
        sf.refresh_from_db()
        sf.auto_assign_primary_field()
        data = StandardFieldSerializer(sf).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def perform_destroy(self, instance):
        # 解散标准字段：先把成员 standard_field 置空，再删记录（物理字段不受影响）
        instance.members.update(standard_field=None)
        instance.delete()

    @action(detail=True, methods=['post'], url_path='remove-member')
    def remove_member(self, request, pk=None):
        """从该标准字段释放单个成员物理字段（解除归并关系，物理字段本身不受影响）。

        请求体：{"field_id": id}。
        """
        sf = self.get_object()
        field_id = request.data.get('field_id')
        if not field_id:
            return Response({'error': 'field_id 为必填'}, status=status.HTTP_400_BAD_REQUEST)
        member = sf.members.filter(id=field_id).first()
        if not member:
            return Response({'error': '该字段不是此标准字段的成员'}, status=status.HTTP_400_BAD_REQUEST)
        member.standard_field = None
        member.save(update_fields=['standard_field'])
        sf.refresh_from_db()
        sf.auto_assign_primary_field()
        return Response({'ok': True, 'removed_field_id': field_id, 'remaining': sf.members.count()})

    @action(detail=True, methods=['post'], url_path='add-member')
    def add_member(self, request, pk=None):
        """将物理字段添加为该标准字段的成员。

        请求体：{"field_ids": [id, ...]}。如果字段已属于其他标准字段，会先解除原关系。
        """
        sf = self.get_object()
        field_ids = request.data.get('field_ids') or []
        if not field_ids:
            return Response({'error': 'field_ids 为必填'}, status=status.HTTP_400_BAD_REQUEST)
        updated = Field.objects.filter(id__in=field_ids, table__domain=sf.domain).update(standard_field=sf)
        sf.refresh_from_db()
        sf.auto_assign_primary_field()
        return Response({'ok': True, 'added_count': updated, 'member_count': sf.members.count()})

    @action(detail=True, methods=['post'], url_path='set-primary-field')
    def set_primary_field(self, request, pk=None):
        """设置组合字段的主字段（档案更新数据源头）。

        请求体：{"field_id": id} → 人工指定（主表变更不跟随）；
                {"field_id": null} → 清除人工标记，按主表成员自动重分配。
        """
        sf = self.get_object()
        field_id = request.data.get('field_id')
        if field_id is None:
            StandardField.objects.filter(pk=sf.pk).update(primary_field=None, primary_field_manual=False)
            sf.refresh_from_db()
            sf.auto_assign_primary_field()
            sf.refresh_from_db()
        else:
            member = sf.members.filter(id=field_id, status=Field.Status.ACTIVE).first()
            if not member:
                return Response({'error': '主字段必须是该组合字段的有效成员'}, status=status.HTTP_400_BAD_REQUEST)
            StandardField.objects.filter(pk=sf.pk).update(primary_field=member, primary_field_manual=True)
            sf.refresh_from_db()
        return Response(StandardFieldSerializer(sf).data)

    @action(detail=True, methods=['get'], url_path='members-distinct')
    def members_distinct(self, request, pk=None):
        """返回该标准字段各成员物理字段的去重取值，供人工并排核对数据是否一致。

        按需填充 distinct_values 缓存（force=False）。
        返回：{'members': [{'field_id','table_name','code','name','comment',
                          'distinct_values','synced_at','count'}]}。
        """
        sf = self.get_object()
        members = list(sf.members.select_related('table').all())
        _ensure_distinct_cache(members)
        data = []
        for f in members:
            vals = f.distinct_values or []
            data.append({
                'field_id': f.id,
                'table_name': f.table.name,
                'table_is_primary': f.table.is_primary,
                'is_primary_field': f.id == sf.primary_field_id,
                'code': f.code,
                'name': f.name,
                'comment': f.comment,
                'distinct_values': vals,
                'synced_at': f.distinct_synced_at.isoformat() if f.distinct_synced_at else None,
                'count': len(vals),
            })
        return Response({'members': data})


class AIConfigViewSet(viewsets.ModelViewSet):
    """AI 服务配置 API（系统设置，单例语义）。

    提供列表/详情/更新，以及 current（获取生效配置）和 test-connection（测试连接）。
    """
    queryset = AIConfig.objects.all()
    serializer_class = AIConfigSerializer

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='current')
    def current(self, request):
        """获取/更新当前生效的 AI 配置（不存在则自动创建默认）。"""
        obj = AIConfig.objects.order_by('-enabled', '-updated_at').first()
        if obj is None:
            obj = AIConfig.objects.create()
        if request.method in ('PUT', 'PATCH'):
            serializer = self.get_serializer(obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(obj).data)

    @action(detail=False, methods=['post'], url_path='test-connection')
    def test_connection(self, request):
        """测试 AI 连接。可传入临时配置（api_base/api_key/model/...）覆盖测试，
        不传则使用当前生效配置。"""
        cfg = None
        body = request.data or {}
        if any(body.get(k) for k in ('api_base', 'api_key', 'model')):
            base = ai_service._resolve_ai_config()
            # 传空 api_key 时沿用已存配置的密钥
            if not body.get('api_key'):
                body = {**body, 'api_key': base.get('api_key', '')}
            cfg = {
                'api_base': body.get('api_base') or base.get('api_base'),
                'api_key': body.get('api_key') or base.get('api_key'),
                'model': body.get('model') or base.get('model'),
                'temperature': body.get('temperature', base.get('temperature', 0.2)),
                'timeout': body.get('timeout') or base.get('timeout', 30),
            }
        ok, message = ai_service.test_connection(cfg=cfg)
        return Response({'ok': ok, 'message': message},
                        status=status.HTTP_200_OK if ok else status.HTTP_400_BAD_REQUEST)


class FieldMappingViewSet(viewsets.ModelViewSet):
    """字段映射 API"""
    queryset = FieldMapping.objects.select_related(
        'source_table', 'source_field', 'target_table', 'target_field'
    ).all()
    serializer_class = FieldMappingSerializer
    filterset_fields = ['source_table', 'target_table']

    def get_queryset(self):
        qs = super().get_queryset()
        table_id = self.request.query_params.get('table')
        if table_id:
            qs = qs.filter(source_table_id=table_id) | qs.filter(target_table_id=table_id)
        domain_id = self.request.query_params.get('domain')
        if domain_id:
            qs = qs.filter(
                models.Q(source_table__domain_id=domain_id) |
                models.Q(target_table__domain_id=domain_id)
            )
        return qs


class ComputedFieldViewSet(viewsets.ModelViewSet):
    """计算字段 CRUD API。"""
    queryset = ComputedField.objects.prefetch_related('depends_on', 'depends_on_computed').all()
    serializer_class = ComputedFieldSerializer
    filterset_fields = ['domain', 'status']

    def _code_conflict_response(self, domain_id, code, exclude_pk=None):
        """前置校验 domain+code 唯一性，返回友好错误（区分废弃字段占用）。"""
        if not domain_id or not code:
            return None
        qs = ComputedField.objects.filter(domain_id=domain_id, code=code)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        conflict = qs.first()
        if conflict is None:
            return None
        if conflict.status == ComputedField.Status.DISCARDED:
            return Response({'error': f'编码「{code}」已被废弃字段「{conflict.name}」占用：请到左栏「废弃字段」分类恢复它，或换一个编码'}, status=400)
        return Response({'error': f'编码「{code}」在当前域中已存在（字段「{conflict.name}」），请换一个编码'}, status=400)

    def create(self, request, *args, **kwargs):
        resp = self._code_conflict_response(request.data.get('domain'), request.data.get('code'))
        if resp is not None:
            return resp
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        domain_id = request.data.get('domain', instance.domain_id)
        code = request.data.get('code', instance.code)
        resp = self._code_conflict_response(domain_id, code, exclude_pk=instance.pk)
        if resp is not None:
            return resp
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        """创建后自动解析依赖。"""
        instance = serializer.save()
        if instance.expression:
            from .computed_service import parse_and_save_dependencies
            parse_and_save_dependencies(instance)

    def perform_update(self, serializer):
        """更新后自动重新解析依赖。"""
        instance = serializer.save()
        if instance.expression:
            from .computed_service import parse_and_save_dependencies
            parse_and_save_dependencies(instance)

    @action(detail=False, methods=['post'], url_path='validate-expression')
    def validate_expression_action(self, request):
        """纯语法验证（无需已保存的计算字段实例）。

        请求体: {"expression": "...", "domain": X}
        返回: {"valid": bool, "references": [...], "errors": [...]}
        """
        expression = request.data.get('expression', '')
        from .formula_engine import validate_expression, extract_references

        validation = validate_expression(expression)
        if not validation['valid']:
            return Response({
                'valid': False,
                'references': extract_references(expression),
                'cycle': None,
                'errors': [validation.get('error', '语法错误')],
            })

        refs = extract_references(expression)
        return Response({
            'valid': True,
            'references': refs,
            'cycle': None,
            'errors': [],
        })

    @action(detail=True, methods=['post'], url_path='validate-formula')
    def validate_formula(self, request, pk=None):
        """验证公式语法 + 解析依赖 + 检测循环依赖。

        请求体: {"expression": "..."} （可选，不传则使用当前保存的表达式）
        返回: {"valid": bool, "references": [...], "cycle": None|[...], "errors": [...]}
        """
        cf = self.get_object()
        expression = request.data.get('expression', cf.expression or '')

        from .formula_engine import validate_expression, extract_references
        from .computed_service import detect_cycle

        validation = validate_expression(expression)
        if not validation['valid']:
            return Response({
                'valid': False,
                'references': [],
                'cycle': None,
                'errors': [validation.get('error', '语法错误')],
            })

        refs = extract_references(expression)

        # 临时保存表达式以检测循环
        old_expr = cf.expression
        cf.expression = expression
        cf.save(update_fields=['expression'])

        from .computed_service import parse_and_save_dependencies
        result = parse_and_save_dependencies(cf)

        if result.get('cycle'):
            # 有循环，回滚表达式
            cf.expression = old_expr
            cf.save(update_fields=['expression'])
            from .computed_service import parse_and_save_dependencies as _re_parse
            if old_expr:
                _re_parse(cf)
            return Response({
                'valid': False,
                'references': refs,
                'cycle': result['cycle'],
                'errors': [f"检测到循环依赖: {' → '.join(result['cycle'])}"],
            })

        return Response({
            'valid': True,
            'references': refs,
            'cycle': None,
            'errors': [],
            'dag_order': result.get('dag_order', []),
        })

    @action(detail=False, methods=['post'], url_path='preview-data')
    def preview_data(self, request):
        """免实例数据预览：按引用字段去重值枚举组合并计算输出。

        请求体: {"expression": "...", "domain": X, "max_combinations": N(可选；缺省/None 则返回全部)}
        返回: {"valid", "errors", "columns", "rows", "total_possible", "truncated"}
        """
        expression = request.data.get('expression', '')
        domain_id = request.data.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        # max_combinations 缺省/None 时返回全部（不截断），前端「全部」模式走这条路径
        raw_max = request.data.get('max_combinations')
        if raw_max is None or raw_max == '':
            max_combinations = 10 ** 9  # 不截断
        else:
            max_combinations = max(int(raw_max), 1)

        from .computed_service import preview_expression
        result = preview_expression(int(domain_id), expression, max_combinations=max_combinations)
        return Response(result)

    @action(detail=False, methods=['post'], url_path='generate-formula')
    def generate_formula(self, request):
        """AI 自然语言生成计算表达式。

        请求体: {"description": "自然语言描述", "domain": X, "selected_refs": ["表.字段", ...]（可选）,
                 "current_expression": "当前表达式"（可选，传入时 AI 在其基础上按描述修改）}
        返回: {"expression": "...", "explanation": "...", "reasoning": "...", "risk": "...",
               "code": "建议字段编码", "name": "建议字段名称", "output_type": "建议输出类型"}
        """
        description = (request.data.get('description') or '').strip()
        domain_id = request.data.get('domain')
        selected_refs = request.data.get('selected_refs') or None
        current_expression = (request.data.get('current_expression') or '').strip() or None
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)
        if not description:
            return Response({'error': '请输入自然语言描述'}, status=status.HTTP_400_BAD_REQUEST)
        if selected_refs is not None and not isinstance(selected_refs, list):
            return Response({'error': 'selected_refs 必须为数组'}, status=status.HTTP_400_BAD_REQUEST)

        from .ai_service import generate_formula
        try:
            result = generate_formula(int(domain_id), description, selected_refs=selected_refs,
                                      current_expression=current_expression)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=True, methods=['post'], url_path='trial-calculate')
    def trial_calculate(self, request, pk=None):
        """枚举试算。

        请求体: {"params": {"表名.字段名": [值1,值2,...]}, "auto_enumerate": bool}
        返回: {"combinations": [...], "total_possible": N, "truncated": bool}
        """
        cf = self.get_object()
        params = request.data.get('params')
        auto_enumerate = request.data.get('auto_enumerate', False)
        max_combinations = int(request.data.get('max_combinations', 100))

        from .computed_service import trial_calculate
        result = trial_calculate(
            computed_field_id=cf.id,
            params=params,
            auto_enumerate=auto_enumerate,
            max_combinations=max_combinations,
        )
        return Response(result)

    @action(detail=False, methods=['get'], url_path='dependency-graph')
    def dependency_graph(self, request):
        """域内完整 DAG 图数据。

        参数: ?domain=X
        返回: {"nodes": [...], "edges": [...], "topo_order": [...]}
        """
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)

        from .computed_service import build_dag
        result = build_dag(int(domain_id))
        return Response(result)

    @action(detail=False, methods=['post'], url_path='batch-recalculate')
    def batch_recalculate(self, request):
        """手动触发批量重算。

        请求体: {"domain": X}
        返回: {"total": N, "success": M, "errors": [...], "records_updated": K}
        """
        domain_id = request.data.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)

        from .computed_service import batch_recalculate
        result = batch_recalculate(int(domain_id))
        return Response(result)

    @action(detail=False, methods=['get'], url_path='available-functions')
    def available_functions(self, request):
        """返回函数库清单（名称/参数/说明）。"""
        from .formula_engine import get_available_functions
        functions = get_available_functions()
        return Response({'functions': functions})

    # -------- 技术函数插件管理 --------

    @action(detail=False, methods=['post'], url_path='plugins/upload')
    def plugin_upload(self, request):
        """上传技术函数插件 .py 文件。

        请求体: multipart/form-data，字段 file（.py 文件）
        返回: {"filename": "xxx.py", "functions": ["FUNC1", ...], "source": "xxx.py"}
        安全校验失败返回 400 + 具体错误信息。
        """
        from . import plugin_loader
        f = request.FILES.get('file')
        if not f:
            return Response({'error': '请上传 .py 文件'}, status=status.HTTP_400_BAD_REQUEST)
        if not f.name.endswith('.py'):
            return Response({'error': '仅支持 .py 文件'}, status=status.HTTP_400_BAD_REQUEST)
        # 文件名规范化：只保留字母数字下划线和连字符
        safe_name = ''.join(c for c in f.name if c.isalnum() or c in '_.-').strip('_')
        if not safe_name.endswith('.py'):
            safe_name += '.py'
        try:
            content = f.read().decode('utf-8')
        except UnicodeDecodeError:
            return Response({'error': '文件必须是 UTF-8 编码的 Python 源码'}, status=status.HTTP_400_BAD_REQUEST)
        # 先 AST 校验
        errs = plugin_loader.validate_plugin_code(content)
        if errs:
            return Response({'error': '安全校验失败', 'details': errs}, status=status.HTTP_400_BAD_REQUEST)
        # 写入 tech_plugins/ 并加载
        plugin_loader._ensure_plugins_dir()
        path = plugin_loader.PLUGINS_DIR / safe_name
        path.write_text(content, encoding='utf-8')
        try:
            info = plugin_loader.load_plugin(safe_name)
        except plugin_loader.PluginError as e:
            # 回滚写入
            try:
                path.unlink()
            except OSError:
                pass
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(info)

    @action(detail=False, methods=['post'], url_path='plugins/unload')
    def plugin_unload(self, request):
        """卸载插件。请求体: {"filename": "xxx.py"}"""
        from . import plugin_loader
        filename = (request.data.get('filename') or '').strip()
        if not filename:
            return Response({'error': '必须指定 filename'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            plugin_loader.unload_plugin(filename)
        except plugin_loader.PluginError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'ok': True, 'filename': filename})

    @action(detail=False, methods=['post'], url_path='plugins/reload')
    def plugin_reload(self, request):
        """重载插件。请求体: {"filename": "xxx.py"}"""
        from . import plugin_loader
        filename = (request.data.get('filename') or '').strip()
        if not filename:
            return Response({'error': '必须指定 filename'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            info = plugin_loader.reload_plugin(filename)
        except plugin_loader.PluginError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(info)

    @action(detail=False, methods=['get'], url_path='plugins')
    def plugin_list(self, request):
        """返回所有已加载插件清单。"""
        from . import plugin_loader
        return Response({'plugins': plugin_loader.list_plugins()})

    @action(detail=False, methods=['get'], url_path='plugins/template')
    def plugin_template(self, request):
        """返回插件模板代码，供前端下载。"""
        from . import plugin_loader
        return Response({'template': plugin_loader.get_plugin_template()})

    @action(detail=False, methods=['get'], url_path='available-references')
    def available_references(self, request):
        """返回域内可引用字段列表。

        参数: ?domain=X
        返回: {"fields": [{"ref": "表名.字段名", "name": ..., "type": ...}],
               "computed_fields": [{"ref": "$computed.code", "name": ..., "expression": ...}]}
        """
        domain_id = request.query_params.get('domain')
        if not domain_id:
            return Response({'error': '必须指定 domain 参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 物理字段
        physical_fields = Field.objects.filter(
            table__domain_id=domain_id,
            status=Field.Status.ACTIVE
        ).select_related('table').order_by('table__name', 'sort_order')

        fields_out = []
        for f in physical_fields:
            # 携带缓存的去重值（前10条，供公式编辑器预览）
            sample_values = None
            if f.distinct_values:
                sample_values = f.distinct_values[:10]
            fields_out.append({
                'id': f.id,
                'ref': f"{f.table.name}.{f.code}",
                'table_name': f.table.name,
                'code': f.code,
                'name': f.name or f.comment or f.code,
                'display_name': f.comment or f.name or f.code,
                'type': f.field_type,
                'sample_values': sample_values,
            })

        # 计算字段
        computed_fields = ComputedField.objects.filter(
            domain_id=domain_id,
            status=ComputedField.Status.ACTIVE
        ).order_by('execution_order')

        computed_out = []
        for cf in computed_fields:
            computed_out.append({
                'ref': f"$computed.{cf.code}",
                'code': cf.code,
                'name': cf.name,
                'output_type': cf.output_type,
                'expression_preview': (cf.expression or '')[:50],
            })

        return Response({'fields': fields_out, 'computed_fields': computed_out})
