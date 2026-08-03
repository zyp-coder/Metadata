# 项目宪法 — 主数据管理系统（MetaData002）

## 项目概述

主数据管理系统是模型驱动+AI增强的新一代平台，包含三大核心模块：
- **主数据建模引擎**（modeling）：可视化建域→建表→建关系→配字段，产出可执行主数据模型
- **档案生成与页面配置**（archive）：基于模型自动生成档案视图、页面布局、接口与权限配置
- **AI驱动的质量规则引擎**：可视化规则配置、自然语言语义转规则、AI批量生成规则

## 技术栈

- 后端：Python 3.13 + Django 6.0.7 + DRF + PostgreSQL
- 前端：Vue 3 + TypeScript + Ant Design Vue 4.x + Vite
- ER图：@antv/x6 v2.19.2（Shape.HTML.register 注册自定义 HTML 形状）
- Excel解析：openpyxl
- AI服务：OpenAI 兼容接口 + 启发式降级（默认 DeepSeek V4 Flash，api_base=https://api.deepseek.com）

## 当前状态

### 建模引擎（modeling）— 域管理三阶段

| 阶段 | 功能 | 页面 | 状态 |
|------|------|------|------|
| 第一阶段 | 管理表（创建/停用/Excel导入/数据源表选择） | TableList | ✅ 已完成 |
| 第二阶段 | 关系管理（ER图+字段映射+位置持久化+重置布局） | DomainFieldMapping | ✅ 已完成 |
| 第三阶段 | 字段管理（三分类架构：基础/组合/计算+未分配+废弃） | DomainFieldConfig | ✅ 已完成 |

### 档案模块（archive）— 数据同步 + 记录管理 ✅

### 系统设置 — 数据源配置 ✅

## 技能体系

| 技能 | 职责 | 调用时机 |
|------|------|----------|
| prjm | AI项目管家：任务路由、状态控制、影响分析、Bug升级 | **每次任务第一步必须调用** |
| darc | 产品架构师：设计/开发/Debug 三类日记 | 设计决策、编码实现、Bug修复 |
| reqa | 需求分析：将需求转化为概念设计文档 | 新需求/概念设计 |
| uxqa | 产品体验质量官：设计评审关 + 交付验收关 | 设计完成待编码 / 编码完成待交付 |

## 已知问题

| 问题 | 状态 | 日期 |
|------|------|------|
| Django 6.0.7 需要 ATOMIC_REQUESTS 配置 | ✅ 已修复 | 2026-07-17 |
| Django 6.0+ 动态数据库连接必需包含 ATOMIC_REQUESTS/TIME_ZONE/CONN_MAX_AGE/CONN_HEALTH_CHECKS | ✅ 已修复 | 2026-07-21 |
| config/settings.py 末尾自动导入 local_settings.py（开发环境 SQLite3） | ✅ 已修复 | 2026-07-21 |
| axios 响应拦截器 reject(new Error) 丢弃 err.response，前端 catch 拿不到结构化错误体（sync_stats）只见通用「Request failed with status code 4xx」 | ✅ 已修复（保留 error.response + 补 data.error 兜底） | 2026-07-23 |
| @antv/x6 v2 中 shape:'rect' 不支持 html 属性 | ✅ 已修复（改用 Shape.HTML.register） | 2026-07-13 |

## 数据源驱动支持

| 数据库类型 | db_type 值 | Django 引擎 | 默认端口 | Python 驱动包 |
|------------|-----------|------------|---------|-------------|
| PostgreSQL | `postgresql` | `django.db.backends.postgresql` | 5432 | psycopg2-binary |
| MySQL | `mysql` | `django.db.backends.mysql` | 3306 | mysqlclient |
| SQL Server | `sqlserver` | `mssql` | 1433 | mssql-django + pyodbc |
| Oracle | `oracle` | `django.db.backends.oracle` | 1521 | oracledb |

## 关键决策记录（三层分层，rule §11 / prjm 启动只读架构级）

> 分层阅读：启动必读「架构级决策」；「交互级决策」按模块/页面按需检索；「历史区」为被推翻决策存档（推翻原因见现行决策行内【推翻…】标注）。追加规则不变：只追加不修改；决策被推翻时，将原决策行**移入历史区**并在新决策行标注【推翻 日期 决策名】。

### 架构级决策（数据流向/存储模型/模块边界/数据治理 — 启动必读）

| 决策 | 内容 | 日期 |
|------|------|------|
| Excel解析策略 | 优先 AI（LLM）+ 降级启发式 | 2026-07-17 |
| 本地建表方式 | 直接执行 CREATE TABLE SQL | 2026-07-17 |
| 列表分页策略 | 管理类列表（pagination=false）前端拉全量；自定义 StandardPagination 启用 page_size_query_param（max=100000） | 2026-07-21 |
| 字段去重方案 | 不删物理字段，新增 FieldEquivalenceGroup 等价组记录跨表重复关系；code 归一化+AI 检测；等价组作为 modeling→quality 契约供后续一致性校验消费 | 2026-07-21 |
| 档案同步数据拉取 | sync-schema 同时拉取数据源实际数据（每表最多 1000 行）；schema 生成用 _generate_schema_from_domain() 包含所有物理字段去重（StandardField 信息优先）；记录匹配用主表主键动态匹配，多表数据合并而非覆盖 | 2026-07-22 |
| 主表架构 | 每个域有一个主表（is_primary=True），档案数据以主表主键为基准合并其他表数据；主表优先处理；前端表列表支持设置主表 | 2026-07-22 |
| 禁止档案端人工新增记录 | 主数据记录统一由业务系统同步产生：ArchiveRecordViewSet.create 直接 403，前端删「新增记录」入口（推翻第七十七轮 CreateSerializer 双层拆分能力，代码保留但不可达） | 2026-07-25 |
| 源侧删除→标记停用 | 刷新时未匹配到源行的 active+synced/partial 记录置 status='deleted'+sync_status='stale'（只标不删）；安全闸门：任一表同步出错/无主键时跳过清扫；stale 记录源端重现自动复活，手工停用（非 stale）保持停用只更新数据；无主键值源行不进档案 | 2026-07-25 |
| 数据变更日志（数据核对） | 源侧同步与档案侧编辑统一落 ArchiveChangeBatch（批次，change_source=sync/manual，零变更不建批次）+ ArchiveChangeDetail（明细，change_type=created/updated/deactivated/reactivated，field_changes 字段级旧值→新值，record_key 主键快照）；无人工核对确认环节—直接以源为准更新+日志留痕一处查看；判定：复活优先于修改、新增不展开字段值、停用 field_changes=[] | 2026-07-25 |
| 数据服务API归属 | API 配置在档案层（数据层）而非主数据域（定义层）；因为API对外开放的是数据（ArchiveRecord），数据实体在档案里 | 2026-07-23 |
| 档案维护导航拆分 | 拆为档案管理（/archive CRUD）+ 档案列表（/archive/browse 只读三级下钻：域→档案→API→字段+数据）+ 操作日志 | 2026-07-23 |
| API开放权限 | 定义为角色/部门授权；本期只做数据结构存储+展示，不做真实鉴权（留待 auth 模块启动后联动） | 2026-07-23 |
| axios 拦截器保留响应 | config：api/index.ts 响应错误拦截器 reject 的 Error 必须挂载原始 err.response（(error as any).response = err.response）并把 data.error 纳入 msg 兜底；否则调用方 catch 拿不到结构化错误体（如 sync_stats），只能看到「Request failed with status code 4xx」 | 2026-07-23 |
| 标准字段页重构三分类架构 | 【推翻 2026-07-24 上/下双栏看板+三Tab架构】页面全面重写为三分类架构：左栏200px字段分类导航(档案字段→基础/组合/计算、未分配、废弃) + 右栏字段表格五视图切换；基础字段=单表直接上档案(Field.archive_category='base')；组合字段=StandardField(status='active')；计算字段=新增ComputedField模型(骨架)；未分配=archive_category='unassigned'；废弃=跨类型聚合(Field.deprecated+StandardField.discarded+ComputedField.discarded)；删除AI检测功能；数据迁移策略：现有数据全部归入未分配字段 | 2026-07-25 |
| 计算字段功能设计 | Excel公式风格配置+依赖自动解析(DAG)+枚举试算验证+物化存储+自动重算(同步后批量+编辑实时)；引用范围仅同域字段({表名.字段名}语法)；计算结果参与档案消费可同步到物理表 | 2026-07-25 |
| 字段分组/属性配置Tab只管理档案字段 | 字段分组和属性配置Tab只展示已归入档案的字段（基础+组合），未分配和废弃字段不进入后续流程（分组/属性配置/档案），只在字段分类阶段管理；后端standard-fields action过滤solo字段只返回archive_category='base'，equiv只返回StandardField.status='active' | 2026-07-25 |
| 多层分组树形结构 | FieldGroup支持parent外键自引用，最多3层嵌套；字段可挂在任意层级分组；删除父分组时子分组上浮(parent=祖父)+直属字段变未分组；档案二级表头保持用字段直属分组名；前端树形展示(expand/collapse)，右栏点击父分组展示汇总字段 | 2026-07-25 |
| 档案 schema 嵌套分组渲染(方案B) | 【推翻 2026-07-25 档案二级表头仅用直属分组名】schema 每字段携带 group_path 根→叶路径数组（后端 _generate_schema_from_domain 按 FieldGroup 树 DFS 遍历生成 group_order/group_paths，字段按 (DFS序,sort_order,id) 排序，未分组排最后，计算字段 group_path=['计算字段']）；前端 ArchiveDetail 四处渲染统一走 schemaGroupTree（按 group_path 建树）→groupedSchemaBlocks（DFS 展平块）：详情/编辑/新增抽屉嵌套标题（level1 蓝色15px粗左边框/level2 灰14px/level3 浅灰13px，缩进(level-1)*16px），记录表格 buildGroupColumns 递归构建多级表头，API 配置抽屉层级缩进 | 2026-07-28 |
| REQ-018 MDM 存活机制(概念设计) | 扩展 archive 模块（不新建模块）；Golden Record + Survivorship 三级存活规则（人工修正>源优先级>最新时间戳）字段级粒度，但规则仅生成「建议裁决」——**全部字段差异一律入冲突审查队列人工确认，不做规则自动覆盖**；人工编辑档案字段即自动登记修正保护 override（修正人/时间/原值）；现有 sync-to-source 记录级两阶段流程必须重做为字段级更新（预检差异→勾选字段→执行）；字段级血缘（来源：源表/人工/裁决）；⚠️ _upsert_records_from_rows 无条件覆盖档案是当前根因，待 REQ-018 落地重做 | 2026-07-28 |
| 取消编辑自动停用 | 【推翻 2026-07-23 档案记录编辑自动停用】编辑档案记录数据变更后**不再**自动 status=deleted——改为登记 override 修正保护+lineage=manual（BR-018-3，MDM 机制下人工修正是受保护的正常态而非待同步的异常态）；sync_status='unsynced' 仍保留（置顶排序继续有效）；sync_to_source 成功后恢复 active 语句保留（兼容存量 deleted 记录） | 2026-07-28 |
| 方案B Hub式MDM(重大架构转向) | 【推翻 2026-07-23 sync_to_source 五阶段/两阶段 dry_run、2026-07-28 MDM 第6批冲突队列(F-116)与第7批字段级回写(F-118)】放弃双向同步，转 Hub 式单向数据流：源表→档案（黄金记录）→ArchiveApi 数据服务输出，永不回写。字段所有权 ownership 在建模字段属性配置（StandardField/Field.ownership，计算字段固定 archive）：ownership='source' 以源为准——档案侧只读（后端400+前端 disabled）、拉取直接覆盖+lineage=sync；ownership='archive' 以我为准——可编辑、拉取永不覆盖（首拉空值除外）。回写链路（sync_to_source/_classify_sync_error/_finalize_sync_log+前端三步向导）与冲突队列（ArchiveFieldConflict 全栈，迁移0004删表）彻底删除，SyncLog 仅留历史查看；stats 改 fields_overwritten/fields_protected；存量 schema 无 ownership 按 archive 兜底，已建档案需执行一次 sync_schema 刷新；overrides/lineage 保留仅作血缘展示 | 2026-07-28 |
| 档案双层存储(演进自方案B) | 【推翻 2026-07-28 拉取引擎 ownership 逐字段比对分流】ArchiveRecord 拆双层：source_data 源同步底层（每次刷新**整层替换零比对**，迁移0005按 lineage 拆存量）+ manual_data 人工覆盖层（仅 ownership='archive' 字段允许有键）；data=写时合并物化结果（_merge_record_data 纯函数：computed 保留现值、source 字段底层直通并清 manual 遗留键、archive 字段 manual 优先否则回落底层，schema 外遗留键并入；lineage 同步重建 manual/sync）——列表查询/搜索/排序/ArchiveApi 继续读 data 不依赖源库在线。编辑链路：archive 字段 diff 写入 manual_data，新值==底层源值时删键回落+解除 override 保护；source 字段 400 拦截不变。刷新链路：refresh-data 端点/refresh_archives 命令/apps.py daemon 定时线程（ARCHIVE_AUTO_REFRESH_MINUTES 默认60，0禁用，RUN_MAIN 防双启）三入口共用 refresh_archive_data（拉数+batch_recalculate+SYNC 日志，不 bump schema_version）；结构变更仍走 sync-schema。stats 简化删 fields_overwritten/fields_protected | 2026-07-29 |
| 变更日志收尾(v9) | ①保留期清理**不做**——变更日志是保留记录，永久存数据库，不设清理策略（用户明确决策）；②全局变更总览页 /archive/changes（ChangeLog.vue，MainLayout「档案维护」菜单「变更日志」入口）：档案下拉默认全部+来源/类型/记录标识筛选+明细/批次双视图+批次下钻，后端零改造仅 ChangeDetailSerializer 补 archive_name；③导出 Excel 针对**单个档案全量**（非按筛选条件）：GET /api/change-details/export/?archive=N，openpyxl 双 Sheet（批次汇总+变更明细），明细上限 5 万行超出取最新+末行提示，文件名 filename*=UTF-8'' 中文编码；前端首个 blob 下载先例 changeLogApi.exportExcel(responseType:'blob')+通用 downloadBlob() 解析 Content-Disposition，ArchiveDetail 变更分区与全局页两处入口 | 2026-07-29 |
| 档案刷新预检工作流(v11) | 【推翻 2026-07-29 双按钮「同步模型结构」+「立即刷新数据」】ArchiveDetail 页头合并为单个「立即刷新」按钮+预检工作流：GET /api/archives/{id}/refresh-preview/（dry-run 零写入）对比 schema 变化（按 code 对比 added/removed/changed，changed 逐属性 name/type/ownership/group_path，ownership 空值兜底 archive）+ 数据试算（_preview_data_changes：拉源行→SimpleNamespace 模拟 _merge_record_data→would_create/would_update/would_deactivate+changes_sample≤20条）；前端预检弹窗展示明细→确认后分流：schema 有变走 sync-schema（含拉数+变更日志），无变走 refresh-data；均无变化提示「数据已是最新」不弹窗。定时调度 refresh_archive_data 路径直通不预检（自动更新+变更日志）。该预检同时打通「建模改分组/字段→档案感知」链路（schema 快照过期可见并引导同步）；_build_code_to_physical 从 _sync_data_from_sources 抽出共用 | 2026-07-30 |
| 档案菜单信息架构重做(v10) | 【局部推翻 2026-07-29 v9 全局变更总览页】「档案维护」菜单四收敛三：①档案管理(ArchiveList)收敛数据向操作保留档案 CRUD+版本历史/变更日志深链，删「API接口」深链；②API管理(ApiManagement.vue /archive/api-management)替代档案列表：平铺 API 表格+所属档案下拉抽屉（编辑态 disabled，切档案重拉 schema+分组勾选）+查看数据抽屉承接 ArchiveBrowse 只读能力，ArchiveDetail API Tab 同步删除(-286行，groupedSchemaBlocks 保留供详情/编辑抽屉复用)；③版本管理(VersionManagement.vue /archive/versions)替代操作日志：全局版本平铺表格+定版/取消定版/回滚/对比，后端 GlobalVersionSerializer+RecordVersionViewSet(/api/record-versions/ 过滤 archive/record/operation_type/is_pinned/operated_by + pin/unpin action，重复操作400)；④变更日志删全局页 ChangeLog.vue+菜单+路由，只留档案管理表格行 ?tab=changes 入口，单档案导出 Excel 保留在 ArchiveDetail 变更分区；ArchiveBrowse/OperationLog/ChangeLog 三页与 operationLogApi 删除（后端 /api/operation-logs/ 端点保留） | 2026-07-29 |
| 字段维护方更名+默认source+存量全刷 | 【推翻 2026-07-28 方案B 中 ownership 默认 archive 与「以源为准/以我为准」术语】ownership 全链路更名「字段维护方：源系统维护(source)/档案维护(archive)」（列名「维护方」、档案橙标「档案维护」、拦截报错「由源系统维护不可编辑」、refresh-preview diff 值中文映射）；默认值 'archive'→'source' 且存量 Field/StandardField 全刷为 source（迁移 0025 AlterField×2+RunPython，用户确认接受旧配置被覆盖）；属性配置表加只读主表/主键标识：standard-fields 聚合行新增 tables[{name,is_primary}]（equiv=成员表去重）+is_primary_key（equiv=任一成员主键即true），前端「所属表」列（金色「主表」tag）+字段编码前金色钥匙标，设置入口仍在管理表页 | 2026-07-30 |
| 组合字段主字段机制 | 主字段=档案更新唯一数据源头（根治原 _upsert 按表循环后写覆盖、组合字段「最后处理的表」胜出的缺陷）；StandardField.primary_field(FK Field SET_NULL)+primary_field_manual，三决策：①一致性规则=刷新时逐记录比对成员值与主字段值，产出报告（stats.consistency_check：checked_fields/mismatch_count/mismatch_records/samples≤20）前端 Modal.warning 告警但**不阻断**落档；②兑底=**无主表成员时留空强制人工设置**（用户明确选非推荐项，不自动兑底第一个成员），未设置时 _validate_primary_fields 在 _sync_data_from_sources/_preview_data_changes 开头拦截（stats.errors+primary_field_missing）；③主表变更=仅自动分配的跟随新主表（primary_field_manual=False），人工指定不动；主字段只能走 set-primary-field 专用端点（序列化器 read_only），成员变更 4 入口（apply_standards/create/add_member/remove_member）+set_as_primary 均挂 auto_assign_primary_field() 钩子；_build_code_to_physical 已设主字段时仅映射主字段成员（primary_locked 防兑底追加），其余成员仅进一致性检查 | 2026-07-30 |
| 一致性检查独立页(v12)·零回写 | 需求「以主字段为准统一覆盖所有成员表」与 Hub式MDM 宪法「源表只读、永不回写」冲突，用户选**完全不回写**——「修复」降级为差异清单管理+批量标记审核状态，宪法保持不变；ConsistencyIssue 差异清单落库（archive/迁移0007：状态 open→reviewed/ignored/resolved，唯一键 archive+record_key+field_code+member_source upsert——新差异 open、仍存在更新值、resolved 重现自动 reopen、已消失且 stats.errors 为空时自动 resolved 安全闸门）；batch-review 批量审核写变更日志批次（ChangeSource 加 consistency、ChangeType 加 reviewed/ignored，明细 field_changes=[{field,name,old:成员值,new:主字段值}] 快照，reopen 用 UPDATED+清空审核三字段；reviewed/ignored 对 resolved 记录 skip）；入口=档案管理列表「一致性检查」链接 + ArchiveDetail 刷新告警 Modal.confirm「前往一致性检查」引导 → 独立页 /archive/:id/consistency（前端路由须注册在 :id 通配之前） | 2026-07-30 |
| change_summary 全补齐(v13) | 统一结构 {action:动作说明文本, changed_fields:[{field,old,new}], ...扩展键}，8 处后端补齐：人工创建（CreateSerializer 全字段初值）/源同步创建/删除（perform_destroy 状态变化+快照字段数）/回滚（rollback×2）/定版/取消定版（pin_version、pin/unpin）/源刷新（refresh SYNC 日志）/编辑（UpdateSerializer：summary_changes 含状态变化，action 文本区分「档案侧人工编辑/启用记录/停用记录/保存记录(无字段变化)」——状态切换不再显「-」）；前端 ArchiveDetail+VersionManagement 版本渲染优先显示 action 行再列 changed_fields | 2026-07-30 |
| 变更日志记录信息落库快照(v14) | ArchiveChangeDetail 加 record_label CharField(500)（迁移0008）=变更时点组合字段值快照（' / ' 拼接），取值口径 _composite_label_codes：域内 status='active'+is_active+release_to_archive 的 StandardField.standard_code；写入点两处=编辑链路 UpdateSerializer+同步链路 _sync_data_from_sources 批次落库（data_map 按 record_id 批量取当前 data）；选择落库而非实时计算因快照语义（记录后续变更/删除不影响历史日志可读性）；存量回填脚本 backfill_change_record_label.py（5773条）；前端 record_label||record_key 回落显示 | 2026-07-30 |
| 变更与版本合并页(v14) | 【局部推翻 2026-07-29 v10 三菜单中独立「版本管理」定位】评估结论：底层两套模型职责不可替代（版本=快照/回滚/定版，日志=批次/审计/导出/防删存证），重复仅在展示层→合并为「变更与版本」单页（/archive/versions 路径不变）：右上 radio 双视图——主视图=全局变更日志（change-details API 全局过滤+记录信息列+「进入档案」跳转），次级视图=版本记录（定版/回滚/对比，记录列改 record_label）；菜单/路由标题「版本管理」→「变更与版本」；档案内 ArchiveDetail 变更日志分区保留（单档案视角+导出） | 2026-07-30 |
| 版本功能前端零入口(v16) | 【推翻 v15 「ArchiveDetail 页面信息架构收缩为记录+字段导航+版本历史」、v14「变更与版本合并页」中版本视图、v13「版本历史仅保留对比」】用户确认审计日志可完成回滚（field_changes 逆向回放即可），版本快照仅为工程便利缓存——前端彻底删除版本入口：全局页只留变更日志视图（删 radio/versionColumns/loadRecordVersions），ArchiveDetail 删 versionColumns/versions/viewVersions/loadVersions/tab=versions 全链路；后端 RecordVersionViewSet 保留供将来扩展 | 2026-07-31 |
| 一致性检查历史记录(v16) | ConsistencyIssueHistory 独立表（FK→ConsistencyIssue+checked_at+primary_value+member_value），每次检查 append 历史快照保留差异值变化轨迹；前端展开行展示时间线，列重排强调「发现时间→成员表.字段→差异对比」 | 2026-07-31 |
| 变更日志回滚功能(v17) | 基于 ArchiveChangeDetail.field_changes 逆向回放实现数据回滚；**粒度**：单条明细回滚（一条 ChangeDetail 的 field_changes 逆向写回）+ 按时间点回滚（某记录在指定时刻之后的全部变更逆序回放）；**同步变更处理**：允许回滚 change_source=sync 的变更，但弹窗警告「此变更来自源系统，回滚后下次刷新可能再次覆盖」，**不加 override 保护**（下次刷新可覆盖回去）；**留痕**：回滚操作本身落一条 ChangeDetail（change_type='rollback', change_source='manual'，field_changes 记录本次逆向写入的字段和值）；**UI 入口**：全局变更日志表（VersionManagement）每行「回滚」按钮（单条回滚） + 记录详情弹窗内「历史回滚」区域（时间线选点回滚） | 2026-07-31 |

### 交互级决策（页面/控件/展示 — 按需检索）

| 决策 | 内容 | 日期 |
|------|------|------|
| 表字段管理交互 | 采用弹窗方案（非展开行） | 2026-07-17 |
| ER图位置 | 持久化到后端（er_node_x/er_node_y） | 2026-07-17 |
| ER图展示方式 | 移除缩放工具栏，新增全屏切换按钮（隐藏映射列表+ER图占满区域） | 2026-07-22 |
| 创建时间格式 | 统一 yyyy-MM-dd HH:mm:ss（24小时制） | 2026-07-17 |
| 新建表交互 | 取消创建方式选项；本地表=Excel导入；数据源表=选数据库表 | 2026-07-17 |
| 档案记录表格中国式表头 | 动态列按字段分组构建嵌套 children，分组名作父列跨字段展示 | 2026-07-22 |
| 档案版本记录优化 | 同步更新记录时，比较 merged_data == existing.data，无变化则跳过版本创建 | 2026-07-22 |
| 档案记录表格不锁顶 | 移除 scroll.x，表格正常滚动而非固定表头（字段多时固定表头占用太多空间） | 2026-07-22 |
| 档案记录移除ID列 | ID是数据库自增主键，对业务无意义，不展示在表格和抽屉中 | 2026-07-22 |
| 编辑变更预览 | 编辑抽屉保存前展示变更摘要表格（字段/原值红色/新值绿色），无变更时禁用保存按钮 | 2026-07-22 |
| 档案表格不使用冻格列 | 不使用 fixed: 'right'，但保留 scroll.x 让表格在容器内横滚（避免页面整体滚动） | 2026-07-22 |
| 档案记录启用/停用 | 状态列移入操作列，用启用/停用切换代替删除按钮 | 2026-07-22 |
| 档案表格列锁定 | #列 fixed:left，操作列 fixed:right，sync_status 合并到操作列 | 2026-07-23 |
| 档案详情页去 Tab 化 | 详情页移除可见 a-tabs 栏，改为 v-show 分区（activeTab 由 route.query.tab 初始化）；版本历史/API接口入口迁移到档案管理列表操作列深链（?tab=versions / ?tab=apis），分区内提供「← 返回档案记录」 | 2026-07-23 |
| 档案列表操作列平铺不用下拉 | 【推翻 2026-07-23 R-003 下拉方案】ArchiveList 操作列必须平铺展示全部按钮（管理记录/API接口/版本历史/从数据源同步/删除），不得收进下拉菜单；空间不足时用 fixed:right+nowrap 固定操作列+压缩数据列（ellipsis）而非隐藏按钮 | 2026-07-23 |
| 档案记录操作列顺序 | 同步标签 → 启用/停用 → 详情 → 编辑 → 版本（启用/停用紧跟同步状态标签） | 2026-07-23 |
| 版本差异弹窗整体滚动 | diff 弹窗 a-modal 用 bodyStyle maxHeight:70vh + overflowY:auto 让弹窗内容整体滚动，内部表格不设 scroll.y（无冻结表头），确保字段完整可见 | 2026-07-23 |
| 编辑模式无元信息表+单滚动条 | 编辑模式不展示顶部状态元信息 a-descriptions（状态/同步/版本/创建人等）；内层不得嵌套 max-height+overflow-y 滚动容器，统一由抽屉 body 单滚动（避免双滚动条） | 2026-07-23 |
| 版本变更内容内联展示 | 版本表「变更内容」列逐行渲染「字段(蓝)：旧值(红) → 新值(绿)」，无需点开对比即可看全变更；编辑保存后自动 loadRecords()+loadVersions()刷新（无需手动刷新） | 2026-07-23 |
| MDM 血缘展示(F-119 落地) | 详情抽屉字段值旁来源小标签（人工=橙/同步=蓝/裁决=紫）+tooltip（源表/更新时间/保护人），分组与平铺两渲染分支均覆盖；记录表格受保护字段（overrides 命中）单元格前置🔒锁标+tooltip；数据全部复用第6批 overrides/lineage JSONField，本批不做血缘历史时间线 | 2026-07-28 |
| 档案记录/抽屉 UI 收敛(v11) | ①记录表操作列删 sync_status 标签，「停用/启用」文字链改 a-switch 开关；②版本表「操作时间」及详情抽屉创建/更新时间统一 formatDateTime；③源刷新版本快照 change_summary 在 source_refreshed 外补 changed_fields[{field,old,new}]——版本表「变更内容」列能渲染新旧值；④详情抽屉只删同步蓝标保留人工橙标（lineage source==='sync' 不显示，用户明确不选全删）；⑤编辑抽屉所有权标注反转：以源为准不标注，archive 所有权字段（非 computed）标橙色「以我为准」；⑥详情/编辑抽屉 width 700→1100px，按 level1 根分组分列 CSS grid 最多3列（groupedSchemaColumns+schemaGridStyle），新增记录抽屉保持单列 | 2026-07-30 |
| 计算字段纳入字段分组 | ComputedField 加 group FK（→FieldGroup，SET_NULL，迁移0024）；序列化器加 group（可写）/group_name；_generate_schema_from_domain 重写为 entries+sort_key 统一排序——物理字段 (DFS组序,0,sort_order,id)、有分组计算字段 (DFS组序,1,execution_order,id) 随真实分组组内排物理后、未分组计算字段兜底「计算字段」虚拟组排尾；DomainFieldConfig 字段分组 Tab 并入计算字段行（kind='computed' 橙「计算」标，key=computed-{id}），换组/拖拽分流 computedFieldApi.patch({group})，物理字段仍走 batchUpdateAttributes | 2026-07-30 |
| 档案详情弹窗化+分组标题蓝色(v13) | 【推翻 2026-07-22「档案记录编辑交互」抽屉决策】详情/编辑统一改大弹窗 a-modal（width 1100px、footer null、bodyStyle maxHeight:70vh 单滚动条约束保持）；recordModal 死代码抽屉及 openRecordDetail/switchToEditMode/openEditRecord/handleSaveRecord/doDeleteRecord/getFieldSpan 六个无引用函数删除；字段分组标题**全级别蓝色系**（level1/2 #1890ff、level3 #40a9ff，用户澄清「和字段分组有关的标题用蓝色」，非值文本改色） | 2026-07-30 |
| 档案记录筛选+字段导航+变更定位(v13) | ①记录表加筛选工具栏：数据内容搜索（后端 ArchiveRecordViewSet 删 search_fields，get_queryset 手动处理 search 参数：annotate(Cast('data',TextField())) icontains，避开 SearchFilter 冲突；SQLite JSON 全文匹配）+同步状态/记录状态下拉（filterset_fields 自动过滤）+查询/重置；②左侧字段导航面板（190px，groupedSchemaBlocks 蓝色分组标题+字段列表，点击按列序 idx*DATA_COLUMN_WIDTH 横滚定位+col-flash 2.6s 淡橙高亮，customHeaderCell/customCell 挂类）；③变更明细行点击/「查看记录」列→archiveRecordApi.get 打开该记录详情弹窗+高亮本次变更字段（labelStyle/contentStyle #fff7e6；record SET_NULL 为 null 时提示「该记录已被物理删除，无法定位」） | 2026-07-30 |
| 组合字段表主表/主字段独立列 | DomainFieldConfig 组合字段成员表「操作」列前插「主表」列（只读：主表成员金tag/其余灰「—」，不可点击）+「主字段」列（当前主字段金tag+tooltip，其余成员「设为主字段」链接→standardFieldApi.setPrimaryField 专用端点），替代原内联在成员编码/来源表列中的 tag 标注 | 2026-07-30 |
| 设为主字段改图标按钮(v14) | 【迭代上条「设为主字段」蓝色文字链接】组合字段表非主字段行改灰色 KeyOutlined 图标按钮（a-button type=text + tooltip「设为主字段」），列宽 110→70；表格高频重复操作用图标不用长文字链接，避免整列蓝色长字视觉噪声 | 2026-07-30 |
| 档案详情即编辑(v14) | 【推翻 2026-07-23「档案记录查询/编辑分离」与「记录详情查看模式纯只读」】删「编辑」入口与双模式切换（drawerEditMode/openEditDrawer/switchToViewMode 全删），详情弹窗单模式：元信息 descriptions+业务数据直接可编辑控件（源系统维护字段 disabled）+变更预览+底部关闭/保存（无变更禁用保存）；打开即初始化编辑数据（openDetailDrawer/openChangeRecord 两入口） | 2026-07-30 |
| ArchiveDetail变更分区整体删除(v15) | 【推翻 v14「档案内 ArchiveDetail 变更日志分区保留」+ v10「导出 Excel 保留在 ArchiveDetail 变更分区」】ArchiveDetail 页面删除整个 changes 分区（模板+脚本+imports 约220行）；导出 Excel 能力迁移至全局「变更与版本」页（VersionManagement.vue，绑定 archive 下拉后出现导出按钮）；页面信息架构收缩为：记录表格+字段导航+版本历史 | 2026-07-31 |
| 版本对比功能删除(v15) | 【推翻 2026-07-23「版本历史仅保留对比」+ v14 版本对比基准改造】数据已全部展示在变更内容列，对比弹窗无额外信息价值——删除 viewVersionDiff/diffColumns/diffModal/diffData/VersionCompare 全栈代码；ArchiveDetail 版本表+VersionManagement 版本视图均移除「对比」操作列 | 2026-07-31 |
| 记录详情弹窗1400px(v15) | 【迭代 v13 1100px 弹窗宽度】记录详情弹窗 a-modal width 1100→1400px，适配多列字段编辑布局可读性 | 2026-07-31 |
| 域概览独立路由页(v15) | 「变更与版本」入口前新增域概览页（/archive/domain-changes，DomainChangeOverview.vue），展示各域变更统计（档案数/近7天变更/最近变更时间）；点击域卡片跳转 /archive/versions?domain=X&domain_name=Y 自动过滤；MainLayout 菜单指向域概览页，VersionManagement 支持 route.query.domain 参数自动过滤；后端新增 /api/domain-change-stats/ 聚合端点 | 2026-07-31 |
| 同步预检工作流统一(v16) | ArchiveList 「从数据源同步」按钮从直接 syncSchema 改为和 ArchiveDetail 相同的预检工作流（refreshPreview→弹窗确认→syncSchema/refreshData），解决“点击无反应”反馈（实际是无变化时无 UI 反馈） | 2026-07-31 |

### 历史区（已被推翻，仅存档）

| 决策 | 内容 | 日期 |
|------|------|------|
| 档案记录编辑交互 | 编辑按钮打开抽屉编辑模式（查看/编辑双模式切换），而非直接打开弹窗；ID点击打开详情抽屉查看模式 | 2026-07-22 |
| 档案抽屉编辑视觉统一 | 编辑模式与查看模式使用相同的 a-descriptions + h4分组视觉风格，而非 a-form 布局 | 2026-07-22 |
| 新增记录用抽屉+卡片 | 新增记录从弹窗改为抽屉，字段分组用 a-card 展示而非 a-divider | 2026-07-22 |
| 新增记录抽屉与编辑抽屉视觉统一 | 新增记录抽屉使用 a-descriptions + h4分组风格，与编辑抽屉一致 | 2026-07-22 |
| 同步到数据源 | 后端 sync-to-source API 将档案记录推送到主表数据源（INSERT/UPDATE） | 2026-07-22 |
| 档案记录编辑自动停用 | 数据变更后自动设 status=deleted，直到同步回数据源后恢复（「同步后恢复」环节已在 sync_to_source 实现：推送全部记录+成功回读校验后 filter(id__in=synced_ids).update(status=ACTIVE, sync_status='synced')） | 2026-07-23 |
| 同步死锁修复(启用/停用) | 【修复】sync_to_source 原仅推送 status=ACTIVE 记录，导致编辑后自动 deleted 的记录被排除→永不推送也永不恢复，用户误以为「启用/停用反了/默认没启用」。改为推送全部记录，成功推送并回读校验通过的记录末尾恢复 active+synced（用户选 B：保留编辑自动停用+补上同步后恢复），新增 stats.records_restored | 2026-07-23 |
| 版本历史仅保留对比 | 移除数据版本的回滚与定版功能（价值低），版本表仅保留「对比」操作；变更字段列加宽(500)、操作人列收窄(90) | 2026-07-23 |
| 同步操作前置校验+二次确认 | 从数据源同步（Schema 空拦截）与同步到数据源（0 记录拦截）均先前置校验，再用 Modal.confirm 二次确认；同步结果含错误时用 Modal.warning 汇总展示 | 2026-07-23 |
| 档案记录查询/编辑分离 | 「详情」打开只读抽屉（openDetailDrawer，drawerEditMode=false）；「编辑」直接进编辑态；编辑保存后关闭抽屉（detailDrawer=false）退出，而非退到查看态 | 2026-07-23 |
| 记录详情查看模式纯只读 | 详情抽屉查看模式（v-if !drawerEditMode）不带任何操作按钮（移除底部「查看版本」「编辑记录」）；版本历史经由记录表操作列「版本」链接进入 | 2026-07-23 |
| 同步到数据源分阶段大任务 | sync_to_source 分五阶段：①连接检查(ensure_connection) ②写权限探测(UPDATE {table} SET col=col WHERE 1=0，不改数据但需写权限) ③差异比对(SELECT 所有待写列现有行逐字段对比，非仅本次改动字段) ④推送(UPDATE/INSERT) ⑤回读校验(重 SELECT 比对确认一致)；结构化 stats(phase/checks/diffs/records_verified/records_diff/分类 errors)；任何阶段失败则提前终止并返回 400+sync_stats | 2026-07-23 |
| 同步错误分类+日志 | _classify_sync_error 按 msg 关键词分类 permission/connection/constraint/data_type/verify/config/runtime；_finalize_sync_log 写 ArchiveSyncLog(status pending→success/partial/failed, details 含 phase/checks/summary/error_by_type/errors[:50]/diffs[:50]/finished_at)；无错→synced，有推送但有错→partial | 2026-07-23 |
| 同步到数据源两阶段(dry_run) | sync_to_source 增 `dry_run` 参数：dry_run=true 预览（连接检查+写权限探测+逐字段差异比对，产出 change_plan[{record,action,changed_fields,sql_preview}]，绝不写库并提前返回，不落 ArchiveSyncLog）；dry_run=false 才执行。前端保留单个「同步到数据源」按钮，点击弹 a-steps 三步向导（①变更确认 ②数据差异校验 ③变更语句确认），先 dry_run 预览、用户确认后才 dry_run=false 执行 | 2026-07-23 |
| 同步只更新差异字段(禁整行UPDATE) | 【数据安全铁律】Phase3 推送时 UPDATE 只 SET record_diff 中真正有差异的字段（changed_cols），绝不整行 UPDATE 全部列——否则会覆盖数据源中不在本次变更范围内的字段；Phase4 回读也只校验 changed_cols | 2026-07-23 |
| 同步错误明细化 | 连接/写权限校验失败时错误消息必须附：数据源信息(类型://host:port/db)、目标完整表名、探测 SQL 语句、数据库原始报错、涉及账号名及所需权限提示（便于运维直接定位） | 2026-07-23 |
| 标准字段界面上/下双栏看板 | 标准字段Tab重做为上=已确认标准字段/下=未确认候选的双栏看板；下→上确认(create StandardField)、上→下释放(dissolve)；两表首列“进档案”checkbox直接复用两层释放门控release_to_archive(equiv走standardFieldApi.patch、solo走fieldApi.batchUpdateAttributes)，不新增独立字段/迁移；下表拖动换位仅前端临时排序(splice manualCandidates)不落库；“确认到档案”按钮只读预览(新增 /fields/archive-preview 复用 archive._generate_schema_from_domain，列出最终字段与物理表，不触发任何写操作) | 2026-07-24 |
| 标准字段界面工具栏重排+统一启用开关 | 【推翻 2026-07-24 首列“进档案”checkbox】上下表公用控件（一个模糊搜索框+刷新数据去重按钮）上移顶部工具栏，一个模糊搜索同时过滤上表(filteredStandardFieldModels)与下表(manualFilteredCandidates)；标准编码/名称是“确认”专属临时表单，收进 manualCreateVisible 弹窗(openManualCreateModal 触发)；上下表统一去除首列“进档案”checkbox，改为右侧“启用”a-switch 列（列名统一“启用”），上表switch驱动 is_active、下表switch驱动 release_to_archive——从用户视角上下表逻辑一致(该字段是否启用/进档案)，二元开关用Switch不用checkbox | 2026-07-24 |
| 标准字段界面8项交互微调 | 【推翻 2026-07-24 “释放选中回下面”按钮+row-selection】上表去除row-selection与释放按钮；dedup Tab时隐藏左栏字段分组(仅group/attr Tab需要)；工具栏AI检测按钮移到搜索/刷新之后(搜索框拉宽480px)；“确认到档案”按钮改type=primary右对齐工具栏右侧；archive-preview弹窗加高(width 900+scroll calc)并“分组”列改“去重内容”列(后端 _generate_schema_from_domain 加 distinct_values 返回)；下表恢复已选字段自动顶置(manualFilteredCandidates selected-first)+拖拽换位后清选避免顶置排序与拖动顺序冲突 | 2026-07-24 |
| 标准字段界面5项交互微调 | 【推翻 2026-07-24 上表列定义(标准编码/标准中文名/成员字段/操作/启用)】上下表列对齐：上表列改为字段编码/字段名称/来源/数据去重内容/查看/是否确认到档案（来源显示首表名+“…共N项”；去重内容显示首成员表.编码+提示点查看；查看→抽屉并排展示成员去重值）；解散按钮从表格操作列移到查看抽屉(≤2成员popconfirm直接询问/>2成员Modal.confirm)；统计显示“已确认到档案：N/M”(N=is_active启用数)；上下表列名“启用”→“是否确认到档案”+switch children改“是/否”；“确认到上面”按钮+弹窗标题改“确认到标准字段” | 2026-07-24 |
| 标准字段界面列宽对齐+数据去重内容+批量取消 | 【推翻上轮统计用is_active】“已确认到档案”统计改为按release_to_archive===true计数(is_active是概念模型门控非档案门控)；上表“数据去重内容”列改为tag展示第一个成员字段的distinct_values(后端StandardFieldSerializer加first_member_distinct_values字段)；上下表列宽统一对齐(字段编码140/字段名称140/来源160/是否确认到档案100)；上表加row-selection+工具栏“批量取消确认到档案”按钮(Modal.confirm确认后逐个patch release_to_archive=false) | 2026-07-24 |
| 标准字段界面6项微调 | 【推翻上轮来源列显示+统计范围+批量取消范围】上表来源列只显示“共N项”去掉表名；后端 manual_candidates source_label 改为中文表名(t.name)而非数据源/英文表名；来源列宽 160→320；批量取消同时作用上下表选中项(上表standardFieldApi.patch+下表fieldApi.batchUpdateAttributes)；统计“已确认到档案”改为上下表合计(上表release_to_archive===true+下表release_to_archive!==false)；下表顶置类型安全修复(keys.map(Number)) | 2026-07-24 |
| MDM 第6批数据模型 | ArchiveRecord 加 overrides/lineage 两个 JSONField(default=dict)（overrides={field_code:{protected_by,protected_at,original_value}}、lineage={field_code:{source: manual/sync/resolve, source_table, updated_at}}）+ 独立模型 ArchiveFieldConflict（Status: pending/resolved_accept/resolved_keep/voided；SuggestedAction: accept_source/keep_archive；索引 (record,field_code,status)+(archive,status)）；一次迁移 0003 | 2026-07-28 |
| MDM 比对引擎(第6批落地) | _upsert_records_from_rows 从无条件覆盖重写为逐字段比对：值一致跳过（无血缘首次补建 sync 血缘 BR-018-6）、档案没有的新字段直接写入+lineage=sync、**任何差异一律不覆盖入队 ArchiveFieldConflict**（同 (record,field_code) 旧 pending 置 voided 只留最新）、受 override 保护标 is_protected+建议 keep_archive 否则 accept_source；新字段写入才 version+1+快照且仅无冲突时置 synced；stats 加 conflicts_created；裁决闭环：accept_source→更新字段+version+1+快照(change_summary.conflict_resolution)+解除override+lineage=resolve，keep_archive→登记/维持override，重复裁决400；机制切换首拉会暴露存量真实差异（档案5实测451条），属预期 | 2026-07-28 |
| MDM 字段级回写(第7批落地) | sync_to_source 加 selections 参数 [{record,fields:[物理列名]}]（fields 缺省=整行用于 INSERT，selections=None 完全向后兼容）；勾选粒度：更新记录差异字段逐个勾选(默认全选)、新增记录整行勾选(INSERT不可拆列)；未选记录/勾选无交集→action='skipped'不回写保持原状态；部分回写（勾选为差异真子集）→sync_status='partial' 不碰 status，全量回写→synced+恢复 active；stats 加 records_partial/records_skipped；前端向导 Step2→Step3 携带 selections 重跑 dry_run 生成按选 SQL（独立 syncSelPreview 不污染全量预览） | 2026-07-28 |
| 版本对比基准=选中vs最新(v14) | 【推翻原 v-1 vs v 相邻对比】版本「对比」统一改「选中版本(v1) ↔ 当前最新(v2)」：ArchiveDetail 用 selectedRecord.version、VersionManagement 用 GlobalVersionSerializer 新增 record_version（SerializerMethodField，记录已删返回 null）；守卫：null=已删提示无法对比、version≥最新提示无需对比；diff 弹窗文案「v{n}（选中） ↔ v{m}（最新）」 | 2026-07-30 |
