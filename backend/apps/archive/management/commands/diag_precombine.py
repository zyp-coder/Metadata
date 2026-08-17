"""预组合过滤诊断命令：python manage.py diag_precombine --domain-id N [--archive-id M] [--no-query]

只读诊断（不修改任何数据），用于对比本机与服务器两侧的预组合过滤配置与计算差异
（典型场景：本机档案 955 条正确、服务器 27281 条错误；代码已 git 同步，但预组合
配置存在数据库、不随 git 走——服务器 data_dump 导入的可能是旧配置）。

输出四部分：
1. 配置全景：域/主表/主键 + 每表数据源 + DetailTableConfig.conditions/join_type 原样
   JSON + 全部 detail 挂载 FieldMapping（join_type/conditions/源目标字段/头表关联）
2. 逐步模拟过滤：每个 inner 挂载的 明细行数 -> 头表带条件行数 -> src_values 大小
   -> same_domain 判定 -> kept 大小 -> 各挂载交集 -> 最终 row_filter 是否生成
   （计算逻辑与 views._build_precombine_filters 逐行对齐）
3. 影子校验：调用同步引擎真实 _build_precombine_filters，对比其 warnings 与结论
   （防诊断逻辑与真实逻辑漂移；结论不一致时以真实函数为准）
4. 档案记录统计：total/active/synced（本机 955 vs 服务器 27281 的直接对比口径）

--no-query 时只打本地配置，不连外部库（外部库连不通时先看配置是否缺失）。
"""
import json

from django.core.management.base import BaseCommand

from apps.archive.models import Archive, ArchiveRecord
from apps.archive.views import ArchiveViewSet
from apps.modeling.models import Domain, Table, Field, DetailTableConfig, FieldMapping


class Command(BaseCommand):
    help = '诊断预组合过滤：配置全景 + 逐步模拟 inner 挂载过滤计算（只读）'

    def add_arguments(self, parser):
        parser.add_argument('--domain-id', type=int, required=True, help='域 ID（必填）')
        parser.add_argument('--archive-id', type=int, default=None, help='档案 ID（默认取域下第一个 active 档案）')
        parser.add_argument('--no-query', action='store_true', help='跳过外部库查询，只打印本地配置')

    def handle(self, *args, **options):
        domain_id = options['domain_id']
        archive_id = options.get('archive_id')
        no_query = options.get('no_query')
        try:
            domain = Domain.objects.get(id=domain_id)
        except Domain.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'域 #{domain_id} 不存在'))
            return

        archives = Archive.objects.filter(domain=domain).order_by('id')
        if archive_id:
            archives = archives.filter(id=archive_id)
        archive = archives.first()
        if not archive:
            self.stderr.write(self.style.ERROR(f'域 #{domain_id} 下没有可用档案'))
            return

        # 复用同步引擎（ArchiveViewSet 纯方法不依赖 request，可无参实例化）
        v = ArchiveViewSet()

        out = []
        out.append('=' * 74)
        out.append('第一部分：预组合配置全景（本地数据库，不连外部库）')
        out.append('=' * 74)
        out.append(f'域 #{domain.id} {domain.name} (code={domain.code})')
        out.append(f'档案 #{archive.id} {archive.name} (status={archive.status})')

        primary_table = domain.get_primary_table()
        if primary_table:
            out.append(f'主表: #{primary_table.id} {primary_table.name} (code={primary_table.code})')

        # 主键字段（与 _sync_data_from_sources 同规则：standard_code 优先）
        pk_fields = []
        if primary_table:
            for f in Field.objects.filter(table=primary_table, is_primary_key=True, status=Field.Status.ACTIVE):
                sf = f.standard_field
                pk_fields.append(sf.standard_code if sf else f.code)
        if not pk_fields:
            first_pk = Field.objects.filter(
                table__domain=domain, is_primary_key=True, status=Field.Status.ACTIVE).first()
            if first_pk:
                sf = first_pk.standard_field
                pk_fields = [sf.standard_code if sf else first_pk.code]
        out.append(f'主键字段(code): {pk_fields}')

        all_tables = Table.objects.filter(domain=domain, status=Table.Status.ACTIVE)
        tables = ([primary_table] if primary_table else []) + \
            [t for t in all_tables if t.id != (primary_table.id if primary_table else -1)]

        for table in tables:
            ds = table.data_source
            cfg = DetailTableConfig.objects.filter(domain=domain, table=table).first()
            out.append('-' * 74)
            tag = '主表' if primary_table and table.id == primary_table.id else '子表/维表'
            out.append(f'表 #{table.id} {table.name} (code={table.code}) [{tag}]')
            if not ds:
                out.append('  数据源: 无（本地表，不走外部查询）')
            else:
                out.append(f'  数据源: #{ds.id} {ds.name} db_type={ds.db_type} host={ds.host} db={ds.db_name} 外部表={table.external_table_name}')
            if cfg:
                out.append(f'  DetailTableConfig #{cfg.id}:')
                out.append(f'    cfg.join_type   = {cfg.join_type}   ← 配置界面上保存的 JOIN 类型')
                out.append(f'    cfg.conditions  = {json.dumps(cfg.conditions, ensure_ascii=False)}')
                ht = cfg.header_table
                hf = cfg.header_link_field
                df = cfg.detail_link_field
                out.append(f'    头表: {ht.name if ht else None} (#{cfg.header_table_id})')
                out.append(f'    header_link_field: {hf.code if hf else None} (phys={hf.physical_name if hf else None})')
                out.append(f'    detail_link_field: {df.code if df else None} (phys={df.physical_name if df else None})')
                rk = cfg.row_key_field
                so = cfg.display_sort_field
                out.append(f'    row_key_field: {rk.code if rk else None} | display_sort_field: {so.code if so else None}'
                           f' | desc={cfg.display_sort_desc}')
                out.append(f'    updated_at = {cfg.updated_at:%Y-%m-%d %H:%M:%S}   ← 配置最后修改时间（两侧对比新旧关键证据）')
            else:
                out.append('  DetailTableConfig: 未注册（无该表的子表配置）')
            # detail 挂载
            if cfg:
                fms = list(FieldMapping.objects.filter(
                    detail_config=cfg, source_field__status='active',
                ).select_related('source_field', 'target_field', 'row_key_field', 'display_sort_field', 'detail_config'))
            else:
                fms = list(FieldMapping.objects.filter(
                    source_table=table, relation_type=FieldMapping.RelationType.DETAIL,
                    source_field__status='active',
                ).select_related('source_field', 'target_field', 'row_key_field', 'display_sort_field', 'detail_config'))
            if not fms:
                out.append('  挂载: 无 detail 挂载')
            for fm in fms:
                star = 'INNER' if fm.join_type == 'inner' else 'left '
                tf = fm.target_field
                out.append(f'  {star} FM #{fm.id} join_type={fm.join_type} relation={fm.relation_type}  <- INNER=参与主记录过滤')
                out.append(f'      source_field: {fm.source_field.code} (phys={fm.source_field.physical_name}, 表#{fm.source_table_id})')
                out.append(f'      target_field: {tf.code if tf else None} (phys={tf.physical_name if tf else None},'
                           f' 表{tf.table.name if tf and tf.table else None}#{tf.table_id})')
                out.append(f'      fm.conditions = {json.dumps(fm.conditions, ensure_ascii=False)}')
                rk = fm.row_key_field
                so = fm.display_sort_field
                out.append(f'      row_key={rk.code if rk else None} display_sort={so.code if so else None}'
                           f' desc={fm.display_sort_desc}')
                cond_src = 'cfg.conditions' if cfg and cfg.conditions else ('fm.conditions' if fm.conditions else '无')
                out.append(f'      同步生效条件来源: {cond_src}')
                if cfg and cfg.join_type != fm.join_type:
                    out.append(f'      WARN: cfg.join_type({cfg.join_type}) != fm.join_type({fm.join_type})，'
                               f'同步实际用 fm.join_type')

        if no_query:
            out.append('=' * 74)
            out.append('[--no-query] 已跳过外部库查询与过滤模拟（第二部分起不输出）')
            out.append('=' * 74)
            self.stdout.write('\n'.join(out))
            return

        # ================= 第二部分：逐步模拟 =================
        out.append('')
        out.append('=' * 74)
        out.append('第二部分：逐步模拟预组合过滤（逻辑与 views._build_precombine_filters 对齐）')
        out.append('=' * 74)
        kept_sets = []
        inner_total = 0
        sim_warnings = 0

        def _warn(msg):
            nonlocal sim_warnings
            sim_warnings += 1
            out.append(f'  WARN {msg}')

        for table in tables:
            if not table.data_source:
                continue
            cfg = DetailTableConfig.objects.filter(domain=domain, table=table).first()
            if cfg:
                fms = list(FieldMapping.objects.filter(
                    detail_config=cfg, source_field__status='active',
                ).select_related('source_field', 'target_field', 'detail_config'))
            else:
                fms = list(FieldMapping.objects.filter(
                    source_table=table, relation_type=FieldMapping.RelationType.DETAIL,
                    source_field__status='active',
                ).select_related('source_field', 'target_field', 'detail_config'))
            for fm in fms:
                if fm.join_type != 'inner':
                    continue  # 仅 inner 挂载参与主记录过滤（left 不收敛数据）
                inner_total += 1
                target_code = fm.target_field.code if fm.target_field else None
                out.append('-' * 74)
                out.append(f'  [inner 挂载 #{fm.id}] 表 #{table.id} {table.name or table.code} -> {target_code}')
                conds = None
                cond_src = '无'
                if cfg and cfg.conditions:
                    conds = cfg.conditions
                    cond_src = 'cfg.conditions'
                elif fm.conditions:
                    conds = fm.conditions
                    cond_src = 'fm.conditions'
                out.append(f'  条件来源: {cond_src}')
                header_conds, detail_conds = v._split_conditions(conds)
                out.append(f'  header 条件: {json.dumps(header_conds, ensure_ascii=False)}')
                out.append(f'  detail 条件: {json.dumps(detail_conds, ensure_ascii=False)}')
                try:
                    rows = v._query_external_table(table, order_by=None, conditions=detail_conds)
                except Exception as e:
                    out.append(f'  FAIL 明细表查询异常: {type(e).__name__}: {e}')
                    _warn(f'{table.name or table.code} 查询失败，该挂载不参与主记录过滤')
                    continue
                if rows is None:
                    out.append(f'  FAIL 明细表查询失败（返回 None），该挂载不参与过滤')
                    _warn(f'{table.name or table.code} 查询失败，该挂载不参与主记录过滤')
                    continue
                out.append(f'  明细表查询行数(detail条件后): {len(rows)}')
                if cfg and cfg.header_table_id and cfg.header_link_field_id and cfg.detail_link_field_id:
                    header_table = cfg.header_table
                    h_pk = Field.objects.filter(
                        table=header_table, is_primary_key=True, status=Field.Status.ACTIVE).first()
                    h_order = (h_pk.physical_name or h_pk.code) if h_pk else None
                    try:
                        header_rows = v._query_external_table(
                            header_table, order_by=h_order, conditions=header_conds)
                    except Exception as e:
                        out.append(f'  FAIL 头表查询异常: {type(e).__name__}: {e}（降级纯明细，头字段缺失）')
                        header_rows = None
                    if header_rows is None:
                        out.append(f'  头表查询失败/异常 -> _join_header_rows 降级纯明细')
                    else:
                        out.append(f'  头表带条件行数: {len(header_rows)}')
                    before = len(rows)
                    rows = v._join_header_rows(table, cfg, rows, fm.join_type,
                                               conditions=header_conds, header_rows=header_rows)
                    out.append(f'  头表 JOIN 后行数(join_type={fm.join_type}): {before} -> {len(rows)}'
                               f'（inner 时被过滤 {before - len(rows)} 行）')
                src_phys = fm.source_field.physical_name or fm.source_field.code
                if not src_phys:
                    _warn(f'{table.name or table.code} 挂载未配置源字段，该挂载不参与主记录过滤')
                    continue
                src_values = set()
                for row in rows:
                    rv = row.get(src_phys)
                    if rv is None:
                        rv = row.get(f'__hdr__{src_phys}')
                    if rv is not None:
                        src_values.add(str(rv))
                out.append(f'  挂载源字段 {src_phys}: src_values 大小 = {len(src_values)}'
                           f'（明细行中该列去重后的挂载键值数）')
                if not src_values:
                    _warn(f'{table.name or table.code} 挂载 {target_code} 条件未命中任何明细行，该挂载不参与过滤')
                    continue
                tf = fm.target_field
                tf_phys = tf.physical_name or tf.code
                tf_table = tf.table
                same_domain = False
                if tf_table and tf_table.data_source:
                    tf_pk = Field.objects.filter(
                        table=tf_table, is_primary_key=True, status=Field.Status.ACTIVE).first()
                    if tf_pk and (tf_pk.physical_name or tf_pk.code) == tf_phys:
                        same_domain = True
                out.append(f'  same_domain: {same_domain}'
                           f'（target 字段 {tf_phys} {"==" if same_domain else "!="} 表{tf_table.name if tf_table else "?"}主键'
                           f' -> {"同域直取" if same_domain else "桥接"}）')
                if same_domain:
                    kept = src_values
                    out.append(f'  同域直取: kept 大小 = {len(kept)}')
                else:
                    kept = set()
                    if tf_table and tf_table.data_source:
                        tf_pk = Field.objects.filter(
                            table=tf_table, is_primary_key=True, status=Field.Status.ACTIVE).first()
                        if tf_pk:
                            tf_pk_phys = tf_pk.physical_name or tf_pk.code
                            try:
                                brow = v._query_external_table(tf_table, order_by=None)
                            except Exception as e:
                                out.append(f'  FAIL 桥接表查询异常: {type(e).__name__}: {e}')
                                brow = None
                            if brow is not None:
                                out.append(f'  桥接表 {tf_table.name} 全量行数: {len(brow)}')
                                for r in brow:
                                    pv = r.get(tf_pk_phys)
                                    tv = r.get(tf_phys)
                                    if pv is None or tv is None:
                                        continue
                                    if str(tv) in src_values:
                                        kept.add(str(pv))
                                out.append(f'  桥接后 kept 大小 = {len(kept)}')
                            else:
                                out.append(f'  FAIL 桥接表查询失败，该挂载不参与过滤')
                        else:
                            out.append(f'  FAIL target 表无主键字段，桥接不可行，该挂载不参与过滤')
                    else:
                        out.append(f'  FAIL target 表无数据源，桥接不可行，该挂载不参与过滤')
                if kept:
                    kept_sets.append(kept)
                    out.append(f'  OK 该挂载参与过滤')
                else:
                    _warn(f'{table.name or table.code} 挂载 {target_code} 条件未命中任何主记录，该挂载不参与过滤')

        out.append('=' * 74)
        if not kept_sets:
            out.append(f'模拟结论: {inner_total} 个 inner 挂载全部未命中 -> 跳过主记录过滤（全量入档）')
            sim_inter = None
        else:
            sim_inter = set.intersection(*kept_sets)
            out.append(f'参与过滤挂载数: {len(kept_sets)}/{inner_total}')
            out.append(f'各挂载 kept 大小: {[len(k) for k in kept_sets]}')
            out.append(f'交集 kept 大小 = {len(sim_inter)}')
            if not sim_inter:
                out.append('模拟结论: 交集为空 -> 跳过主记录过滤（全量入档）')
            else:
                out.append('模拟结论: row_filter 生成 -> 主表/直连表仅保留主键值在 kept 中的行')

        # ================= 第三部分：影子校验 =================
        out.append('')
        out.append('=' * 74)
        out.append('第三部分：影子校验（调用同步引擎真实 _build_precombine_filters）')
        out.append('=' * 74)
        schema_type_map = {i['code']: i['type'] for i in (archive.schema or []) if i.get('code')}
        code_to_physical = v._build_code_to_physical(domain, schema_type_map)
        match_channels = v._build_match_channels(domain, pk_fields)
        stats_shadow = {'warnings': []}
        try:
            real_filters = v._build_precombine_filters(
                domain, tables, pk_fields, code_to_physical, match_channels, stats_shadow)
            out.append(f'真实函数 warnings（{len(stats_shadow["warnings"])} 条）:')
            for w in stats_shadow['warnings']:
                out.append(f'  WARN {w}')
            out.append(f'真实函数生成 row_filter 的表: {sorted(real_filters.keys())}')
            real_generated = bool(real_filters)
            sim_generated = bool(sim_inter)
            if real_generated == sim_generated:
                out.append(f'影子校验: 一致（真实函数{"生成" if real_generated else "跳过"}过滤'
                           f' <-> 模拟{"生成" if sim_generated else "跳过"}）')
            else:
                out.append(f'影子校验: FAIL 不一致！真实函数{"生成" if real_generated else "跳过"}'
                           f' 但模拟{"生成" if sim_generated else "跳过"}——'
                           f'请以真实函数为准，检查模拟逻辑或输入装配差异')
        except Exception as e:
            out.append(f'FAIL 真实函数执行异常: {type(e).__name__}: {e}（模拟结论仍可参考）')
        out.append(f'模拟 warning 数: {sim_warnings} | 真实 warning 数: {len(stats_shadow["warnings"])}')

        # ================= 第四部分：档案统计 =================
        out.append('')
        out.append('=' * 74)
        out.append('第四部分：档案记录统计（本机 vs 服务器直接对比口径）')
        out.append('=' * 74)
        total = ArchiveRecord.objects.filter(archive=archive).count()
        active = ArchiveRecord.objects.filter(archive=archive, status=ArchiveRecord.Status.ACTIVE).count()
        synced = ArchiveRecord.objects.filter(
            archive=archive, status=ArchiveRecord.Status.ACTIVE,
            sync_status__in=['synced', 'partial']).count()
        out.append(f'档案 #{archive.id} {archive.name}: total={total} active={active} synced/partial={synced}')
        if sim_inter is not None:
            out.append(f'若过滤生效，主表仅保留 {len(sim_inter)} 个主键值对应的行'
                       f'（最终 active 记录数应~此数量级，可对比上面的 active 数）')
        out.append('')
        out.append('排查提示: 两侧对比重点看 1) cfg.conditions 是否一致 2) cfg.updated_at 新旧 '
                   '3) fm.join_type/cfg.join_type 是否 inner 4) 各挂载 kept 大小与交集。')
        self.stdout.write('\n'.join(out))
