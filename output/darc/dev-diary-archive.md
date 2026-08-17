# 开发日记 — archive 模块

> 记录 archive 模块编码实现的关键数据流与实现要点，供后续影响分析使用。

## 2026-08-17 — 启动链 loaddata 事故修复：彻底移除自动灌（第一百六十六轮）

### 变更背景
第一百六十五轮治本（loaddata 条件化）上线后事故：服务器 git pull + up --build → backend 容器 Restarting 循环崩溃，前端全挂（假象「域管理的东西都没有了」）。日志：loaddata 走了 else 分支 → FieldMapping(pk=11) 撞唯一约束 (1,1,2,33) 已存在 → IntegrityError → 启动链中断 → gunicorn 未起。详见 debug-diary BUG-2026-0817-01。

### 变更（commit 99c6c86）
- `deploy/docker-compose.yml`：启动链移除 if/loaddata 双分支，恢复纯启动链 `migrate → init_admin → collectstatic → gunicorn`；注释写明 data_dump.json 仅用于首次部署手动导入（`docker compose exec backend python manage.py loaddata /app/data_dump.json`）

### 验证
- YAML 解析 OK（command 展开为纯启动链）
- 2026-08-17 服务器恢复验证全部通过：①docker compose ps backend Up（不再 Restarting）②curl /api/domains/ 401（后端活）③counts=domains 1/tables 6/fields 101/fms 7/cfgs 2——loaddata 无残留（撞车于 FM pk=11 即中断，dump 的 FM 12/13 未轮到导入，7=服务器原有数量）④DB 补 3 处 OK（cfg2/cfg6 inner+conditions、FM9 inner）⑤diag_precombine 完全收敛：价目 239,504→955、分组 64→桥接 kept 116,594、交集 955、档案 total 955、影子一致 0 warning——服务器与本机完全一致（此前 kept 209,123→27281 错误）

### 遗留
- 条件命令误判根因已确认闭环：条件命令 `from modeling.models import Domain` import 路径错误（INSTALLED_APPS 用 `apps.` 前缀）→ 任何环境必 ModuleNotFoundError → 退出码非 0 → 误判走 else（本机+容器实测复现，见 debug-diary BUG-2026-0817-01）
- loaddata 残留核查完成：无残留
- **服务器关系对齐修复完成**（用户反馈「关系管理多了很多条/语义不一样」）：FM 对齐本机 3 条——保留 FM5/FM11，FM3 改 inner，删 FM4/FM7/FM8/FM9；diag 重跑：价目 955、分组 116,594、交集 955、影子一致 0 warning，过滤结果与修复前一致；界面刷新后关系页 3 条
- 界面同步收敛 955 待用户确认

## 2026-08-17 — 服务器 27281 根因定位 + 配置分发机制治本（第一百六十五轮）

### 变更背景
用户跑服务器 diag_precombine 输出证实根因：服务器 cfg2/cfg6 conditions=[]、join_type=left、updated_at=08-11（data_dump 导出时间）；FM9（价目挂载）left；FM11（分组挂载）inner 但无条件。本机 cfg2 08-17 / cfg6 08-13 的正确配置从未进入服务器 PostgreSQL。

### 根因链（诊断证据 + dump 考古）
- **配置存数据库不随 git 走**：用户在本机界面配的 64 条限制+inner join 只写进 dev.db，服务器 PostgreSQL 从未收到（updated_at=08-11 铁证）
- **data_dump.json 是 08-11 部署基线且结构性过时**：dump 中 FieldMapping/DetailTableConfig 记录**无 join_type 字段**（该字段是后续模型新增）→ loaddata 导入时取默认值 left → 服务器全部 left；且 conditions 全空
- **27281 的数学来源**：服务器唯一 inner 挂载 FM11 无条件 → 明细 1782 行全量 → 桥接物料表 209,123 → kept=209,123 全量 → 应用到主表 239,504 行 → 匹配 27,281 行 → 全部入档
- **机制性缺陷**：docker-compose 启动链每次启动都 loaddata → 即使服务器 DB 改对，重启即被旧 dump 覆盖

### 方向锁定（rule §11.1，命中数据流向）
- 用户拍板治本；adqa 质疑关 5 条（#4 存活：未来新部署用旧 dump 会重踩 27281 → 转整改项 R-001；#1/#5 执行时验证；#2/#3 证伪失败）

### 实施（3 项）
1. **deploy/docker-compose.yml 启动链 loaddata 条件化**：`if Domain.objects.exists() 则跳过，else loaddata`——仅首次部署（空库）灌配置快照，之后重启不再覆盖数据库；配置以数据库为准
2. **data_dump.json 重新导出为正确基线**：从本机 dev.db 导出（排除 auth.user/authtoken/mdm_auth.userprofile/archive 等敏感+业务数据；`PYTHONUTF8=1` 强制 UTF-8 防 Windows GBK）；**解除 .gitignore 入库**（决策变更，用户确认）——以后 git pull 自动同步基线
3. **服务器 DB 补 3 处**（用户执行）：cfg2.conditions=[NAME eq 明码实价 header]+join_type=inner、cfg6.conditions=[FULL_PARENT_ID starts_with .101041 detail]+join_type=inner、FM9.join_type=inner（FM11 已 inner）

### 验证
- 新 dump 模拟首次部署全流程：临时 sqlite 库 migrate OK + loaddata OK（domain 1/table 6/field 101/fieldgroup 7/FM 3/cfg 2/configtable 6/datasource 1/computedfield 3/standardfield 1/aiconfig 1/role 1 全量导入）+ 导入后 cfg2/cfg6 join_type=inner + conditions 正确
- YAML 解析 OK（command 展开 if/fi 结构正确）
- 服务器待执行：git pull → up --build（看 loaddata skipped 日志）→ DB 补 3 处 → diag 重跑（kept 955/116,594 交集 955）→ 同步收敛

### 遗留
- 服务器侧验证结果待用户反馈；dump 入库后旧 dump 历史仍在 git 历史（含 08-11 的 auth.user 哈希，属历史遗留，不阻断）

## 2026-08-17 — 新增 diag_precombine 诊断命令（第一百六十四轮）

### 变更背景
用户报服务器档案同步出 27281 条（本机 955 正确），代码已 git 同步，怀疑服务器数据库配置（cfg.conditions 存 PostgreSQL，不随 git 走）与本地不一致。用户要求把同步逻辑做成可打印的 debug 工具，本机/服务器各跑一次对比。

### 关键实现（backend/apps/archive/management/commands/diag_precombine.py，新文件，只读不改数据）
- `python manage.py diag_precombine --domain-id N [--archive-id M] [--no-query]`
- **第一部分 配置全景**：主表/主键 + 每表数据源 + DetailTableConfig（conditions/join_type/头表关联/updated_at 原样 JSON）+ 全部 detail 挂载 FieldMapping（join_type/conditions/源目标字段）；高亮 `cfg.join_type != fm.join_type` 不一致告警（同步实际用 fm.join_type，前端配置界面存 cfg.join_type）
- **第二部分 逐步模拟**：复用 ArchiveViewSet 纯方法（无 request 实例化），对每个 inner 挂载逐步打印：条件来源→header/detail 拆分→明细行数→头表带条件行数→JOIN 后行数→src_values 大小→same_domain 判定→桥接行数→kept 大小→交集；逻辑与 `_build_precombine_filters` 逐行对齐
- **第三部分 影子校验**：调用真实 `_build_precombine_filters` 对比结论与 warnings（防诊断逻辑漂移；不一致时以真实函数为准）
- **第四部分 档案统计**：total/active/synced 直接对比口径
- 踩坑：Windows 控制台 GBK 不支持 ✓/⚠/★/→ 等 Unicode 符号 → 全部 ASCII 化（FAIL/WARN/OK/->）保证本机与服务器容器都能跑

### 本机实跑验证（域 2，档案 #3）
- 挂载#12 价目明细：header 条件 NAME eq 明码实价 → 头表 1 行 → inner JOIN 239,504→955 → src_values=955 → same_domain=True → kept=955
- 挂载#13 物料分组：detail 条件 FULL_PARENT_ID starts_with .101041 → 明细 64 行（用户数据限制生效）→ 头表 1,782 行 → JOIN 后 64 行 → same_domain=False → 桥接物料表 209,123 行 → kept=116,594
- 交集=955；影子校验一致（真实函数生成 row_filter，0 warnings）；档案 active=955 完全吻合
- 关键证据：本机 cfg2 updated_at=2026-08-17 01:13:38（价目）、cfg6 updated_at=2026-08-13 08:54:13（分组）——服务器对比时若 cfg.conditions 缺失/不同/updated_at 更旧 → 即为 27281 vs 955 根因

### 验证
- py_compile 通过 + Django check 0 issues + 命令实跑 2 次（--no-query 与全量）EXIT:0
- 未改任何既有逻辑（新增独立只读命令），无回归风险

### 遗留
- 服务器侧待用户跑 `docker compose exec backend python manage.py diag_precombine --domain-id 2` 对比两侧输出（重点：cfg.conditions、cfg.updated_at、kept 大小）

## 2026-08-14 — 预组合过滤主记录引擎改造（第一百六十二轮）

### 变更背景
用户反馈「预组合表设置了筛选条件 + inner join，同步结果数据量未收敛」；期望 SQL：价目明细（NAME 明码实价）INNER JOIN 物料 INNER JOIN 分组（FULL_PARENT_ID starts_with .101041）。已按用户 SQL 口径验证：最终主记录应 = 955 条（eq「明码实价」表头 955 明细）。

### 关键实现（archive/views.py，7 个改动点）
- **`_split_conditions`（新）**：conditions 按 field_source 拆 header_conds/detail_conds；header 条件透传 `_join_header_rows` 头表查询（原实现 header 字段不在明细表白名单 → ValueError 整表跳过 = 筛选条件静默失效根因）
- **`_build_precombine_filters`（新，129 行）**：同步前对每个 inner detail 挂载预扫 kept_keys（主键值集合），多挂载交集后生成 row_filter 供主表/直连表 upsert 行级过滤（防 stale 复活死循环：过滤必须发生在 upsert 阶段）；kept 全部空/交集空 → warning + 跳过过滤（防误全量停用）
- **`_upsert_records_from_rows`**：加 row_filter 参数，L2455-2457 行级过滤（不进 seen_keys/不 upsert/不创建）
- **`_join_header_rows`**：加 conditions 参数透传头表查询
- **`_sync_detail_rows` 异名挂载补洞**：挂载字段物理列不在本表/头表（分组头 FID→物料 MATERIAL_GROUP 在第三张表）→ source_field 物理列作行内取值通道

### 实跑暴露根因与修复（第二轮）
实跑域 2（209,123 主记录）过滤未生效（两个挂载 kept 全空）→ 探针定位：
1. **target_code 错位**：挂载字段 code（MATERIAL_ID/MATERIAL_GROUP）非 schema code（主表主键 schema code=MTL_ID）；`code_to_physical['MATERIAL_ID']=None` → 预扫/挂载全失配
2. **预扫 kept 取值错误**：原实现按 target_code 查 code_to_physical 取 phys_cols → 全空；改为**明细行 source_field 物理列行内取值**（src_values），主记录侧按「同域直取 or 桥接」收敛为主键值集合：
   - 同域（tf_phys == target 表主键物理列，如价目 MATERIAL_ID↔物料主键）→ kept=src_values 直接主键比较
   - 异键（如分组头 FID→物料 MATERIAL_GROUP）→ 桥接查询 target_field.table（物料表）：{主键值→挂载键值}，主记录行按主键查桥接后比较
3. **挂载归属桥接**：`_sync_detail_rows` target_code 优先标准字段解析（MATERIAL_ID→MTL_ID）；挂载键不在档案 schema（主记录 data 无该键）→ 桥接 target_field 所在表 {主键值→挂载键值} 索引 existing_records

### 配置修正（本机 dev.db，用户确认）
- cfg6（分组）：conditions PARENT_ID → **FULL_PARENT_ID**（用户界面确认「A.我的配置错了」）
- cfg2（价目）：NAME eq '新明码实价' → **eq '明码实价'**（实测：eq「新明码实价」的 838 个物料为 7 位 ID，全部不在物料表 209,123 行（6 位 ID）→ 与分组交集 0；eq「明码实价」955 条明细（6 位 ID）全在 .101041 组 → 结果 955，对齐用户 SQL 口径）

### 新增测试（tests.py）
- `PrecombineFilterSyncTest`（7 条）：split 条件拆分 / header 条件透传 / kept 交集过滤 / 全空跳过 / 单挂载空跳过 / upsert 行级过滤 / stale 防复活
- `DetailSyncHeteronymMountTest`（3 条）：异名挂载 source 取值 / 未匹配跳过 / **桥接挂载（挂载键不在 schema）**

### 实跑验证（域 2，二次实跑）
records_updated=**955**（209,123→955 active），records_deactivated=**208,168**，details_created=**117,549**（分组头+价目明细挂载生效），tables_synced=6，errors=[]；唯一 warning：物料分组未配置代表行排序字段（既有配置提示）

### 遗留问题
- 明细行归属索引（existing_records）遍历全部记录（含将停用的 stale）→ 分组头明细挂到 116,594 个将停用记录上（details_created=117,549 中约 116,594 属此类）；active 记录（955）明细正常。不影响用户诉求（主记录收敛），停用记录不展示；如需只挂 active 可后续单独处理
- 服务器 data_dump.json 配置暂缓（用户裁决 Q4「暂缓 dump，只改本机」），服务器上 cfg2/cfg6 条件需发布时同步

## 2026-08-13 — 普通关联筛选条件接入同步引擎（第一百五十九轮）

### 变更背景
批2③：reference 映射支持筛选条件（前端弹窗条件构建器 → FieldMapping.conditions），同步时过滤目标表行。

### 关键实现（_upsert_dimension_via_mapping）
- **L2503 接入点**：`trows = self._query_external_table(target, order_by=t_order_by)` → 增加 conditions 透传：仅 `fm.relation_type == RelationType.REFERENCE and fm.conditions` 时传 conditions；detail 不传（明细条件在 detail_config 上、目标表行不过滤，行为不变）
- `_query_external_table`/`_build_conditions_sql` 零改动（2026-08-08 已支持 conditions，白名单+参数化防注入）

### 新增测试（backend/apps/archive/tests.py）
- `FieldMappingConditionsApiTest`（域 COND_TEST）：PATCH conditions=null → 400「不能为 null」（锁定模型契约，前端修复后不再发送）；conditions=[] → 200；conditions 列表 → 200 落库
- `ReferenceConditionsSyncTest`（域 REFC，mock _query_external_table）：reference 带条件 → 透传 conditions；reference 无条件 → None；detail → None（行为不变）

### 验证
新增 6/6 PASS + apps.archive 全套 60/60 PASS

## 2026-08-13 — 同步引擎挂载归属改造：按挂载字段一对多（第一百五十七轮）

### 变更背景
用户拍板方案B：同步按挂载字段（detail_fm.target_field）归属主记录，支持一对多（物料表↔物料分组预组合用 GROUP_ID 关联，一组合多物料）。替代原按主表主键归属。

### 关键实现（_sync_detail_rows）
- **归属键**：target_code=detail_fm.target_field.code；`target_physical_to_schema` 由 code_to_physical+match_channels 构建（tbl_id==table.id 或 header_table_id——头表物理列可作归属键，第一百四十一轮平铺 `__hdr__` 机制复用）；无映射→stats['warnings'] 追加+return（不静默）
- **existing_records 多值索引**：`{str(挂载字段值): [records]}`，active 优先 insert(0)；原按 pk_fields tuple 单值索引
- **一对多挂载**：明细行 upsert 包进 `for existing in existing_list:` 循环——同挂载字段值的所有主记录各挂一份
- **_record_key_for_row**：行内取挂载字段物理列值（先本表列再 `__hdr__` 前缀回退），无值返回 None→continue（不创建）
- **代表行折叠**：按挂载字段值分组（seen_keys），每组排序首行写**所有**同值主记录（共享代表行数据），key 传 (rep_key,) tuple
- pk_fields 参数保留（L2021 排除列判断仍用，归属用途移除）

### 新增测试（backend/apps/archive/tests.py DetailSyncOneToManyTest，域 DSYNC1N）
- 主表物料信息：MATERIAL_ID 主键 + MATERIAL_GROUP 非主键；明细分组头：FID 主键 + GROUP_ID 非主键；挂载 source_field=GROUP_ID → target_field=MATERIAL_GROUP
- 用例1：G1→M1,M2 + G2→M3，details_created=3，代表行 GROUP_NAME 写入 M1/M2（共享）；用例2：第二轮幂等（details_created=0/details_updated=0/count=3）；用例3：G9 未匹配→0 条

### 验证
DetailSyncOneToManyTest 3/3 + DetailSyncEngineTest+ArchiveRecordDetailModelTest 11/11 定向回归 + 全套 105/105 PASS

## 2026-08-10 — 明细致子表批3a+3b（前端）：关系管理配置页 + 明细展示 + 变更日志展示

### 批3a（关系管理配置页前端）
#### 修改文件
- **frontend/src/types/index.ts**：FieldMapping 扩展（relation_type/row_key_field/display_sort_field/display_sort_desc/conditions）+ ChangeDetail 扩展（detail_sync/detail_group/detail_row_key）
- **frontend/src/api/modeling.ts**：fieldMappingApi 新增 `update` (PATCH) + `detectRowKey` 方法
- **frontend/src/views/modeling/DomainFieldMapping.vue**：
  - 映射表格加「关系类型」列（明细子表蓝标签/引用灰标签）
  - 编辑弹窗加关系类型 select（reference/detail）+ detail 配置区（行键字段 select+检测按钮/代表行排序字段 select/排序方向 switch/筛选条件 JSON 输入）
  - Script：form 扩展 detail 字段、`detectingRowKey` ref、`openCreate/openEdit` 回填 detail 字段、`handleSubmit` 创建后 PATCH 更新 detail 配置（引用类型清除遗留配置）、`detectRowKey()` 调用后端 /detect-row-key/ 自动匹配、`onRelationTypeChange()` 切换引用时清空 detail 字段

### 批3b（明细展示 + 变更日志展示）
#### 后端
- **archive/serializers.py**：新增 `ArchiveRecordDetailRowSerializer`（ArchiveRecordDetail 模型序列化器，含 mapping_name）
- **archive/views.py**：ArchiveRecordViewSet 新增 `@action(detail=True, methods=['get'], url_path='details')` → `GET /records/{id}/details/` 返回明细行列表

#### 前端
- **frontend/src/api/archive.ts**：archiveRecordApi 新增 `listDetails(id)` 方法
- **frontend/src/views/archive/ArchiveDetail.vue**：
  - 操作列新增「明细」按钮，打开明细子表行抽屉
  - 抽屉展示明细行键/数据/状态/更新时间，数据字段以 JSON 键值对形式展示
- **frontend/src/views/archive/components/ChangeHistoryDrawer.vue**：
  - 时间线支持 `detail_sync` 类型聚合条目展示（新增/更新/移除行数统计）
  - 普通明细行展示关联明细行键信息
  - timelineColor/changeTypeColor/canRollbackDetail 均扩展 `detail_sync` 类型

### 验证结果
- vue-tsc 0 errors；后端序列化器导入验证通过
- 无新测试用例（明细展示为纯前端展示，后端 endpoint 为简单查询，已有记录列表测试覆盖）

## 2026-08-10 — 明细致子表批2（审计扩展）：ChangeDetail 扩展 + 明细聚合变更日志 + 回滚 action

### 背景
- 批1 明细变更不进 change_entries（防假明细 BUG-2026-0805-01 教训），批2 统一扩展 ChangeDetail 模型加明细支持
- 用户确认方案 A：聚合级变更日志（不逐行）+ 回滚=重新同步覆盖（复用 _sync_detail_rows）

### 代码改动
1. **archive/models.py（M1）**：ArchiveChangeDetail 扩展——`detail_group` FK（ArchiveRecordDetail，nullable，on_delete=SET_NULL）+ `detail_row_key` CharField（行键值快照，解耦回滚）；新增 `ChangeType.DETAIL_SYNC = 'detail_sync', '明细同步'`
2. **archive/serializers.py（M2）**：ChangeDetailSerializer 扩展 `detail_group` / `detail_row_key` 字段
3. **archive/views.py（M3）**：`_sync_detail_rows` 末尾追加聚合 change_entries——统计 `details_created/updated/deactivated`，生成 `DETAIL_SYNC` 类型条目（field_changes 存 `detail_stats` 聚合字典，不逐行创建）；`record_id=None`、`record_key='{源表名} 明细'`、`version_before/after=None`、`detail_group/detail_row_key=None/''`
4. **archive/views.py（M4）**：`ArchiveChangeDetail.bulk_create` 补充 `detail_group_id` / `detail_row_key` 字段（从 change_entries dict 取值）
5. **archive/views.py（M5）**：新增 `rollback_detail` action（`POST /archives/{id}/rollback-detail/`）——接收 `detail_fm_id` + `operated_by`；构造同步上下文（`_build_code_to_physical` + pk_fields + match_channels）→ 调用 `_query_external_table` + `_sync_detail_rows` 全量覆盖 → 有变更则建 `ArchiveChangeBatch` + `ArchiveChangeDetail`（含 DETAIL_SYNC 聚合条目）→ 写 `ArchiveOperationLog`
6. **迁移**：archive 0016（archivechangedetail.detail_group + detail_row_key + change_type 扩展）

### 批2 范围边界
- 明细变更不进 change_entries 的限制已解除（批2 统一加了 DETAIL_SYNC 聚合日志）
- 回滚=重新同步覆盖（不创建 ArchiveRecordDetailVersion 快照，不逐行回滚）
- 嵌套表保留行能力仍留活口（批1 边界未动）
- 前端（明细区变更日志展示 + 回滚按钮）留批3

### 验证
- 新增 3 条定向测试全 PASS（DETAIL_SYNC 聚合变更条目验证 + 无变更无条目 + 模型扩展字段及 ChangeType）
- 回归 archive 51/51 PASS；Django check 0 issues
- 批2 无新端点真实请求实测（rollback-detail 依赖域 14 配置 detail 关系，留批4 全量同步实测时一并验证）

## 2026-08-10 — 明细致子表批1（后端核心）：子表关系 + 明细行存储 + 同步引擎 detail 分支

### 背景（方向锁定摘要）
- 用户需求升级：档案需保留 1:n 明细（价目明细表 28 共 239,504 行、单物料最多 3,808 行），原确定性折叠取首条不满足
- 用户提案「子表关系」：FieldMapping 增加 relation_type（reference/detail），替代原独立 DetailGroup 配置（已取消）
- 关键决策：默认价取数=生效日期最新 + 同日期取行键最大（可复现）；嵌套属性透传一级（27.NAME/DESCRIPTION 并进 28 行）；主表 35 字段全保留取代表行；编辑独立不联动；折叠+分页；批1 明细变更不进 change_entries（防假明细 BUG-2026-0805-01 教训，批2 扩展 ChangeDetail 时统一加）
- 实证：FID 标主键但仅 14,883/239,504 唯一（标主键≠行唯一）；ENTRY_ID 239,504 零重复零空；EFFECTIVE_DATE field_type='date' 系统自动推断（非手动配置，date_format 空）

### 代码改动
1. **modeling/models.py（M1）**：FieldMapping 扩展——`RelationType(REFERENCE/DETAIL)` + `row_key_field`（明细行键列 FK）+ `display_sort_field`（代表行排序字段 FK）+ `display_sort_desc`（默认 True 降序）+ `conditions`（结构化筛选条件 JSON，AND 组合）
2. **archive/models.py（A1）**：新增 `ArchiveRecordDetail` 模型——record FK + mapping FK + row_key（行键值）+ source_data/manual_data/data/lineage/overrides 双层存储同 ArchiveRecord + status（active/deleted）；`unique_together(record, mapping, row_key)`
3. **archive/views.py（A7）**：`_query_external_table` 支持 `conditions` 参数（方言化 WHERE）；新增 `_build_conditions_sql`——字段白名单校验（仅本表 active 字段 physical_name/code）+ 值全部 %s 参数化（禁拼接注入）+ eq/ne/gt/ge/lt/le/in 六操作符
4. **archive/views.py（A2/A3）**：`_sync_data_from_sources` 表循环新增 detail 分支（`relation_type=DETAIL` 的 FieldMapping 优先，整表作为明细致子表同步，跳过直连/中转路径）；新增 `_sync_detail_rows`——行键自动检测回填（`_detect_unique_column`：全量行逐列统计无空值且 COUNT(DISTINCT)==总行数，优先已标主键列）/嵌套属性一级透传（`__nested__{schema_code}` 前缀并入明细行，同值多行取排序后最后一条）/代表行写主表（display_sort DESC/ASC + 行键次级键，空值垫底，复用 `_write_dimension_row` 公共写入）/明细 upsert（source_data 整层替换 + manual_data 保留，merged 有差异才 save）/明细停用清扫（源侧消失行标 DELETED，安全闸门无 errors）；新增 `_detect_unique_column`
5. **modeling/serializers.py（M2）**：FieldMappingSerializer 扩展 relation_type/relation_type_label/row_key_field(_name)/display_sort_field(_name)/display_sort_desc/conditions
6. **modeling/views.py（M3）**：FieldMappingViewSet 新增 `detect-row-key` action（detail=True）——复用 `ArchiveViewSet._query_external_table + _detect_unique_column` 全量拉取自动检测行键列，供关系管理配置页调用
7. **迁移**：modeling 0030（fieldmapping 5 新字段）+ archive 0015（archiverecorddetail 建表）

### 批1 范围边界（方向锁定）
- 明细变更不进 change_entries（批2 扩展 ChangeDetail detail_group/detail_row_key 时统一加明细变更日志 + 回滚）
- 嵌套表本身保留行能力留活口（当前仅属性透传一级）
- 前端（关系管理 UI + 明细区折叠分页）留批3

### 验证
- 新增 8 条定向测试全 PASS（ArchiveRecordDetail 模型 3 + DetailSyncEngine 5：明细创建/代表行写主表/第二轮更新+停用清扫/无法归属跳过/行键检测/conditions SQL）
- 回归 archive+modeling 99/99 PASS；Django check 0 issues
- 新端点 detect-row-key 真实请求实测 1 次：POST /api/field-mappings/23/detect-row-key/ → 200，candidate=ENTRY_ID、total_rows=239,504、column_count=35（与方向锁定实证完全一致）；GET FM 序列化含 relation_type 新字段
- 遗留：date_format 空值待批4 配置时补（用户逃生方案：行键配置处加日期配置）；域 14 实际配置 detail 关系留批4

## 2026-08-10 — 分组字段链路修复：多级 FieldMapping 中转 + 公式口径修正（设计先行）

### 背景（诊断事实）
- 全量同步实测遗留：GROUP_NAME/GROUP_ID/GROUP_NO/GROUP_DESC 四字段 0 值、7 个计算字段重算失败
- 诊断（真实数据验证）：
  1. **表 25.GROUP_ID 列存 GUID 常量**：1,782 行仅 1 个非空值（`d82dac3f-...`），真实分组标识是 **FID 列**（101040 等）；表 22.MATERIAL_GROUP 非空 1,457 个值，与 25.FID 交集 1,457 且**表 22 全部 209,123 行 MATERIAL_GROUP 100% 命中 25.FID**（0 未命中）→ 现有 FieldMapping `25.GROUP_ID→22.MATERIAL_GROUP` 用错列，正确关联是 `25.FID↔22.MATERIAL_GROUP`
  2. **表 26（分组多语言）无 source 映射**：只有 `25.FID→26.FID`（source=25），表 26 处理时 `FieldMapping.filter(source_table=26)` 为空 → 整表跳过 → GROUP_NAME/GROUP_DESC 永远 0；正确链路 26.FID→25.FID→22.MATERIAL_GROUP 是**两级等值链**，引擎原仅支持一级中转
  3. **计算引擎 context 口径**：`computed_service._build_context_from_record` 键为 `表名.Field.code`（如 `EDS_K3_物料.MTL_MCODE`），公式却写物理名 `MNEMONIC_CODE` → 引用未找到 → 7 个 active 计算字段全失败

### 设计决策（用户裁决：改引擎支持多级，治本）
- **引擎**：`_upsert_dimension_via_mapping` 增加多级中转支持——fms 为空时沿 FieldMapping 无向等值图 BFS 找「可映射档案主键的表」路径（深度上限 5、防环）；逐级行透传（每级取上一行对应列值查下级索引）；终表主键列构建记录 key；写入复用一级「折叠写入」公共逻辑（抽 `_write_dimension_row` 公共方法，一级/多级共用，防复制分叉）
- **配置**：FieldMapping 22 修正 `25.GROUP_ID→25.FID`（目标 22.MATERIAL_GROUP 不变）；新建组合字段 GROUP_ID（主字段=25.FID，防 solo 通道把 GUID 常量写入 schema GROUP_ID）；GROUP_NO/GROUP_NAME/GROUP_DESC 走 solo 通道（Field.code 匹配 schema code）
- **计算字段**：10 个公式 `{EDS_K3_物料.MNEMONIC_CODE}` → `{EDS_K3_物料.MTL_MCODE}`（7 active + 3 discarded 全改，discarded 不执行但防将来启用再踩坑）
- **代价**：重跑同步 20.9 万条一次性补 4 个分组字段 + 计算字段首次重算成功（一次性变更明细+版本+1，与首次全量同类）
- 方向判定表：本次为引擎能力扩展 + 配置修正，不触及数据流向/存储模型/模块边界/核心交互范式四项

## 2026-08-08 — 同步引擎维度模型改造（续）：全量同步（去 TOP 1000）

### 背景
- 维度模型改造（匹配通道+折叠+中转）落地实测发现活跃记录 1000→1334 漂移
- 诊断（COUNT 实测）：主表/物料信息各 209,123 行、价目表明细 239,504、价目表头 14,883、物料分组各 1,782——**TOP 1000 硬限制使每表只取前 1000 行，各表物理序不同 → 截断集合分裂**：表 28↔表 22 截断交集为 0（NAME/PRICE 全空假象，全量交集实际 24,794）、表 24 与表 22 截断批次分裂（111xxx 与 112xxx 两批同时活跃 → 1334 漂移）

### 代码改动（backend/apps/archive/views.py）
1. **`_query_external_table` 去截断**：SQL Server `SELECT TOP 1000`/Oracle `ROWNUM <= 1000`/MySQL `LIMIT 1000` 全移除 → 全量 `SELECT *`；fetchmany(10000) 分批转换防 pyodbc C 层一次性物化（全量行仍驻留 Python 内存供折叠）；`_query_local_table` 同去 LIMIT 1000
2. **无变化记录批量落库**：`_upsert_records_from_rows`/`_upsert_dimension_via_mapping` 的「无差异」分支从逐条 `save(update_fields=...)` 改为收集 `no_change_updates` 收尾 `bulk_update(batch_size=2000)`（Django 按 SQLite `bulk_batch_size`=124 自动再分批，不炸变量上限）——防全量模式下每轮 20 万次逐条 UPDATE
3. **变更明细瘦身**：本轮刚创建记录（`created_in_this_batch`）被后续表合并时不重复记 UPDATED 明细（与 records_updated 统计口径一致，防首次全量 20 万条重复明细爆炸）；`_upsert_dimension_via_mapping` 同口径
4. **SQLite 大列表分批（BUG-2026-0808-02）**：停用清扫改为「候选 id 集与 matched_ids 内存求差 → stale_ids 按 500/批 id__in 分批抓身份+update」；变更日志 data_map 查询同分批

### 实测结果（产品档案 id=10）
- 全量同步：6/6 表、`records_created: 0`（增量重跑）、`records_updated: 11,677`、`errors: []`、耗时 662 秒 ≈ 11 分钟
- 活跃记录 **209,123**（此前 1334，漂移归零，与源表行数一致）
- 字段覆盖率：MTL_NAME/MTL_CODE 100%、MTL_SPEC 209,050/209,123、**PRICE/UNIT_ID/TO_QTY 24,794**（= 表 28↔表 22 全量交集，精确命中）、NAME 5,322（价目表头经 FID→明细→物料中转链）、GROUP_NAME 0（见遗留）
- cardinality_fold_count: 12,044（表 28 明细 1:n 折叠告警正常）
- 变更明细 11,677 条 updated（batch#61）
- 首次从零全量（1334→209,123）实测 59.4 分钟：主成本 = 20.9 万条逐条 `save()`+`ArchiveRecordVersion.create()`（表 22 创建 + 表 24 首写），一次性成本；后续增量 11 分钟

### 遗留问题
- **GROUP_NAME/GROUP_ID/GROUP_NO/GROUP_DESC 0 值**：表 25/26（物料分组）字段未挂任何 StandardField 组合字段 → `code_to_physical` 无映射 → 中转后 record_data 空跳过。建模配置缺失，非引擎 bug；需在字段属性配置页把表 25/26 字段挂到组合字段（配合 FieldMapping 25.GROUP_ID→22.MATERIAL_GROUP、25.FID→26.FID 已存在）
- **7 个计算字段重算全失败**（P_COLOR 等）：公式引用 `EDS_K3_物料.MNEMONIC_CODE` 物理名，但 `Field.code=MTL_MCODE` → computed_service 按 code 解析找不到。既有公式配置错误，需到计算字段配置页改引用
- 首次全量 59 分钟性能：后续可优化为批量创建（bulk_create + 版本快照批量），新档案全量初始化时再评估

## 2026-08-08 — 档案字段去重值统计（field-distinct-values）

### 新增端点
- `GET /archives/{id}/field-distinct-values/`：从档案记录实时聚合每个 schema 字段的去重值及计数
- 返回 `{ fields: [{ code, name, group, type, distinct_count, values: [{ value, count }] }], total_records }`
- 每字段最多返回 200 个去重值（按计数降序）
- 仅统计活跃记录（status=active），空值/null 不计入

### 前端
- ArchiveDetail 字段导航列表每项右侧加「值」小按钮，点击弹窗展示该字段去重值（首次加载全量缓存，后续点击零请求）
- archiveApi.fieldDistinctValues(id) 调用新端点

### 验证
- 新端点实测：产品档案 1000 条记录、42 字段，状态码 200，数据正确
- 回归 40/40 PASS，vue-tsc 0 errors

## 2026-08-05 — v19 REQ-005 API 管理（API Key 真实鉴权 + 对外网关 + 密钥管理 + 调用日志）

### 数据模型（migration 0014）
- ArchiveApi 扩展：`slug`（unique，对外路径标识）/`allowed_operations`（JSON，空=只读）/`rate_limit_per_min`（0=不限）
- **ApiKey**：name/key_prefix（mdm_xxxx****）/key_hash（SHA-256 unique，明文不落库）/status(active|revoked)/expires_at/total_calls/last_used_at
- **ApiKeyGrant**：api_key↔api 多对多授权 + 每授权操作裁剪；UniqueConstraint(api_key, api)
- **ApiCallLog**：api/key 均 SET_NULL + key_name 快照；索引 (-created_at)/(api,-created_at)/(api_key,-created_at)
- ChangeSource 新增 `API='api'`

### 关键数据流
1. 网关拦截链（open_api_auth.authenticate → check_grant → check_rate_limit）：401（缺/无效/吊销/过期）→ 404（slug）→ 403（停用/无授权/操作越权）→ 429（密钥维度滑动窗口）→ 业务 → log_call 异步落日志
2. 写路径：PATCH 复用 ArchiveRecordUpdateSerializer（批次解析提前，change_source 支持 API，action_text 区分「外部接口写入（密钥：xx）」）；POST 新增主键落 source_data 底层 + 可写字段落 manual_data + 物化合并 + v1 版本快照；DELETE=软停用
3. 文档：build_docs(api_obj) 公共函数，对外 `/api/open/{slug}/docs/`（需密钥）与管理端 `/archive-apis/{id}/docs/`（免鉴权预览）共用

### 方向承载点（方向推翻时只动这两个文件 + urls 开关）
- `apps/archive/open_api_auth.py`（137 行）：鉴权/限流/日志单点
- `apps/archive/open_api_gateway.py`（388 行）：网关读写六端点 + docs

### 实现要点/坑
- 密钥明文仅创建/轮换响应返回一次；hash_api_key + hmac.compare_digest 恒定时间比对
- 限流为进程内滑动窗口（dict+锁），重启清零；多实例部署需换 Redis（技术债已登记）
- **修复存量 Bug（apps.py）**：文件尾部重复的空 ArchiveConfig 类覆盖了带 ready() daemon 的完整类，导致自动刷新线程从未启动 → 删除重复类，并把 90 天日志清理并入现有 daemon 循环
- 管理端序列化器 create/update 自动补 slug（从 path 末段派生+去重）与默认 ['read']

### 验证（rule §5 第3问）
- 新用例 19 条（OpenApiGatewayTest 13 + ApiKeyManagementTest 6），archive 模块 37/37 PASS；archive+modeling 定向回归 54/54 PASS；vue-tsc 0 errors
- 真实请求实测 18/18 PASS（live_test_v19.py，跑完已删）：管理端 CRUD+docs、密钥创建明文一次、网关 401×2/列表投影/docs/写拒 400×2/越权 403、call-logs/stats、轮换（旧 401 新 200）、吊销后 401；实测残留数据已清理
- 实测中发现并确认：未授权 create 的密钥 POST → 403（操作越权拦截链正确生效）

## 2026-08-04 — v18.2 变更日志体验 3 项（术语文案 / 记录详情弹窗 / 变更历史弹窗）

用户三项反馈：①「复活/停用是啥意思」（第七十九轮定的机制：源侧删除→停用，源侧重新出现→复活）；②单条记录的变化历史看不到；③「进入档案」没必要，直接弹窗看记录详情（套用档案页详情弹窗）。决策（AskUserQ）：详情弹窗只读版；历史用时间线弹窗；术语改标签文案。

- **后端**（models.py + 迁移0012 仅 choices 元数据）：`ArchiveChangeDetail.ChangeType` label 改「停用（源侧已删）」「复活（源侧恢复）」——`change_type_display` 全局统一生效（序列化器 source='get_change_type_display' 动态取，无覆盖点；Excel 导出表头是硬编码不受影响）。注意 ArchiveApi.status 的 disabled 停用是另一枚举，未动。
- **VersionManagement.vue**：
  - 明细行操作列「进入档案」移除 → 「详情｜历史｜回滚」（record 为 null 时仅显示回滚）。
  - **只读记录详情弹窗**（openRecordModal）：`archiveRecordApi.get(record)` + `archiveApi.get(archive)` 并发，布局套用 ArchiveDetail 详情弹窗：状态/版本/创建/更新描述区 + 业务数据字段列表（按 schema 平铺，档案维护字段带橙标签）；字段只读（编辑仍去档案页），弹窗内可转历史弹窗。
  - **变更历史时间线弹窗**（loadHistory）：`changeLogApi.listDetails({ record })` 翻页拉全（后端默认 -id 序=时间倒序），UI 套用档案页历史弹窗：类型/来源标签+时间+操作人+vN→vM+字段旧值→新值；只读无回滚入口（回滚在列表明细行操作）；a-timeline 仅认预设色（timelineColor：新增绿/修改蓝/回滚红/其余灰）。
  - 变更类型列宽 100→140（文案变长）。
- **环境陷阱**：改 label 后 API 仍返旧文案——根因是 4 个 runserver 进程并存（旧进程未死，Windows SO_REUSEADDR 同绑 8000 请求随机路由），详见 debug-diary BUG-2026-0804-01。
- 验证：vue-tsc 0 errors；API 实测新文案+记录详情接口；浏览器四检查点全过（操作列/术语文案/只读详情弹窗/历史时间线 20+ 条，无 JS 错误）；小瑕疵已修：详情弹窗内转历史时标题缺记录名。

## 2026-08-04 — v18.1 变更日志仅按时间一层折叠（测试报告 2 项，推翻 v18 两层折叠交互）

测试报告：①两层折叠（日行→批次行→明细）太深，用户要「只要一个时间折叠，批次作为字段」；②列表看不到字段从什么变成什么。事实核查：字段变化数据链路完整（修改/复活明细 field_changes 带 old/new；新增/停用按设计只记记录级 views.py L1220 注释）——问题②根因是明细藏在两层折叠里。

- **VersionManagement.vue**（纯前端，后端零改动）：
  - 行类型收敛为两种：`DayRow`（同档案同日全部批次合并）/ `DetailRow`（明细，批次号 #N 作为字段显示在时间列）；批次行层移除。
  - 展开日行逐批拉取当日全部明细（`loadDayDetails` 串行+翻页拉全，单批超 500 自动翻页——首版用累计数对比单批 count 有 bug，改单批 fetched 计数）；明细存响应式 Map `dayDetails: Record<dayKey, DetailRow[]>`。
  - 日行「主要变化」摘要（`daySummary`：统计当日 field_changes 字段频次 top3，如「备注×1298，门店名称×158」）。
  - **撤销本日全部**（用户选定粒度）：日行操作列，`rollbackableBatches` 筛出当日可撤销批串行调 `rollbackBatch`，汇总成功/跳过/失败；回滚产生的批次与无正向变更批次不参与。
  - **验证发现的缺陷（已修）**：首版可撤销判定用 `!stats.source_batch_id`，但明细级回滚自建批（_execute_field_rollback L1892 只有 records_rolled_back）不带该标记，纯回滚日未禁用 → 判定改为「含正向变更（created/updated/deactivated/reactivated）且非整批回滚产物」。全库 grep 确认无同类点。
  - 新增/停用明细的字段变化列显示「（记录级变更，无字段级变化）」（取代旧版“-”，回应问题②）。
  - 移除项：批次行层、批次来源列（changeSourceColor）、批次级「整批撤销」入口（改日级）。
- 验证：vue-tsc 0 错误；浏览器实跑：仅日期行无批次行、展开直出明细（含 1439 条大日翻页拉全）、旧值→新值彩色展示、主要变化摘要、纯回滚日撤销禁用/含正向日可点（复验通过）、无 JS 错误。截图工具会话级故障未产出图（DOM 快照完整验证）。

## 2026-08-03 — 批次视图明细内联展开（取代下钻抽屉，局部调整 v18 关键数据流 7）

用户反馈：明细不要藏在下钻抽屉里，直接放进列表。方案（用户选定）：点批次行展开明细子行，抽屉移除。

- **VersionManagement.vue**（纯前端，后端零改动，复用 `changeLogApi.listDetails({batch})`）：
  - 行类型三分支：`DayGroupRow`（同日折叠）/ `BatchViewRow`（批次）/ `DetailRow`（明细子行），模板按 `row.isDayGroup / row.isBatchRow / row.isDetailRow` 分流（注意 v-else-if 链顺序）。
  - 批次行预挂占位子行（`ph-{id}`）保证展开箭头可见；`@expand` 首次展开时拉取该批明细（page_size=500）替换占位；加载中/无明细/加载失败均占位行展示文案。
  - **响应式关键**：明细子行存独立响应式 Map `batchDetails: Record<batchId, DetailRow[]>`，computed `batchRows` 读它拼树——不可直接改 computed 返回的普通对象属性（不触发重渲染）。
  - 刷新时机：筛选查询/整批撤销/单条回滚后均清空 `expandedKeys` + `batchDetails` 重载批次（回滚会生成新批次）。
  - 列合并双义：记录/所属档案、来源/类型、变更概况/字段变化、版本（批次行显示「N 条明细，点左侧箭头展开」，明细行显示 vN→vM）。
  - 移除项：下钻抽屉及其筛选（变更类型/记录搜索）——明细搜索能力下线，后续有需要再加回。
- 验证：vue-tsc 0 错误；浏览器实跑验证两级展开（日行→批次→明细）、299 条明细批加载正常、无 JS 错误；顺手修 3 处 AStatistic value-style 字符串警告→对象。

## 2026-08-03 — v18 回滚体系统一（回滚收口 + 预检告警 + 批次视图 + 攒批保存）

### 数据模型（migration 0011）

- `ArchiveChangeDetail` 新增 `version_before` / `version_after`（可空 IntegerField）：明细→版本快照映射，回滚统一「恢复快照」语义的支撑。存量 5773 条明细为 NULL（不回填，回滚降级旧字段级逻辑）。

### 关键数据流

1. **五处版本映射写入点**（views.py + serializers.py）：停用清扫（两者相等，无版本变动）/ upsert 更新分支（ver_before 在复活判断前捕获）/ upsert 新建分支（None→1）/ bulk_create / `_execute_field_rollback`（bump 前捕获）/ `ArchiveRecordUpdateSerializer.update`（ver_before 在 `instance.version += 1` 前捕获）。
2. **三回滚端点收口**（均走 `_execute_field_rollback` 按 ownership 分层写回，修复旧版只写合并层的隐性 Bug C1）：
   - `POST /records/{id}/rollback/`：快照全字段作目标值，响应体保持 ArchiveRecordDetailSerializer 不变；
   - `POST /records/{id}/rollback-to-change/`：按明细 version_after 取快照恢复；存量明细（无映射）400 提示用版本回滚；
   - `POST /change-details/{id}/rollback/`：新语义=恢复 version_before 快照（本条之后的变更一并撤销）；快照缺失/存量降级字段级 old 值恢复。
3. **`_execute_field_rollback(record, target_fields, operated_by, action_text, change_batch=None)`**：共用执行器；change_batch 传入时留痕明细挂入共享批次（整批撤销共用），否则自建批次；明细写版本映射；返回 {rolled_back_fields, batch_id, new_version}。
4. **整批撤销 `POST /change-batches/{id}/rollback/`**（应对源侧批量刷错）：逐明细恢复 version_before 快照；record 已删→skipped_deleted、无映射→skipped_legacy、该批之后又被改过（.exclude(created/reviewed/ignored)）→skipped_edited 列出 {record_key, record_label}；回滚留痕共用一个新 manual 批次，stats 记 source_batch_id。
5. **刷新预检告警**（`_preview_data_changes`）：`archive_owned_impact = {records, fields:[{code,name,records}]}`——试算中变化的字段若 ownership≠source（无人工覆盖层时值取自源层）则计入；仅提醒不阻断。前端 ArchiveDetail/ArchiveList 预检弹窗橙色告警卡。
6. **攒批保存**：`POST /change-batches/start-manual/`（开 manual 批次）→ 前端待存队列（草稿仅存浏览器）→ 页头「保存」逐条 `PUT /records/{id}/` 带 `change_batch_id`（serializer 可选参数，指定批次需属同档案且 manual，stats 累加）；保存即批次封口。前端离开拦截（onBeforeRouteLeave 列出待存内容：保存并离开/放弃二次确认/留下）+ beforeunload 拦截。
7. **批次视图页**（VersionManagement.vue 翻新）：首页看事件（批次表：概况标签+明细数+「整批撤销」）；同档案同日多批次前端折叠为日行（childrenColumnName='batches'，数据层不合并）；下钻抽屉看明细（类型筛选+记录搜索+单条回滚）；近 7 天汇总卡（批次数/新增/修改/回滚恢复）。

### 实现要点/坑

- 整批撤销的「后续编辑」判定用 `ArchiveChangeDetail.id__gt` + 排除 created/reviewed/ignored（审核标记不算数据变更）。
- 现状数据（门店主数据档案 974 条）全为源维护字段，人工可改的只有状态切换；端到端冒烟用停用→恢复闭环验证（批次 #29，6/6 PASS，不留脏数据）。
- 前端回滚文案按版本映射有无分流：有映射→「恢复到本条变更前（后续变更一并撤销）」；存量→「逐字段恢复」。
- 批次表拉取 page_size=500 后前端同日折叠 + 客户端分页（批次量级小，当前 29 个）。

## 2026-07-30 — 一致性检查独立页（ConsistencyIssue 落库 + batch-review）

### 关键数据流

1. **consistency_check action**（ArchiveViewSet，views.py，refresh_preview 之后）：schema_type_map/field_name_map ← archive.schema → _build_code_to_physical（组合字段已设主字段只映射主字段成员）→ _build_code_checks → 逐表 _query_local/_query_external + _collect_check_values（按主键采集）→ _collect_full_mismatches（全量，_norm(v)='' if None else str(v)）→ upsert ConsistencyIssue（bulk_create + bulk_update['primary_value','member_value','record','last_checked_at','status']）。pk_fields 与同步引擎同口径（主表主键→兕底第一个主键），无主键 400。record_map：ArchiveRecord data 主键快照 '/'.join → id 关联 record FK。
2. **自动 resolved 闸门**：仅当 stats['errors'] 为空时，existing 不在 seen 且 ≠RESOLVED → 置 RESOLVED；有拉取错误时不自动关闭（防源库瞬时故障误关）。
3. **batch_review**（ConsistencyIssueViewSet，_match_condition 之前）：act≠reopen 且 status==RESOLVED → skip；status==目标 → skip；reopen 清空 review_note/reviewed_by/reviewed_at；by_archive 分组每档案一个 ArchiveChangeBatch(change_source=CONSISTENCY)，明细 type_map={reviewed→REVIEWED, ignored→IGNORED, reopen→UPDATED}。
4. **前端 ConsistencyCheck.vue**：四状态计数用 4 个 page_size=1 并发取 count；字段筛选项从 page_size=200 去重；批量操作后 Promise.all([loadIssues, loadStats]) 双刷新；router 路由 ':id/consistency' 必须注册在 ':id' 之前。

### 实现要点/坑

- ChangeBatch/ChangeDetail 的 change_source 前端联合类型需同步加 'consistency'，否则 vue-tsc 不报错但 tag 三色映射失效（旧代码是二元 ternary，已改 changeSourceColor 函数，两处：明细表 cd + 批次表 cb）。
- ConsistencyIssue.record 用 SET_NULL：记录删除后差异保留（record_key 快照仍可追溯）。
- 冒烟实测：档案5 首检 69 处差异（GZT0914 等 33 条记录），批次14 reviewed/批次15 reopen；端到端 7/7 PASS。

## 2026-07-28 — REQ-018 MDM 第7批（F-118 字段级回写 / F-119 血缘展示）

### F-118 后端（仅改 sync_to_source，views.py）

1. **selections 解析**（函数开头）：`[{record: id, fields: [物理列名]}]` → `sel_map = {record_id: set(fields) | None}`；fields 缺省/空=None=整行（insert 场景）；`selections` 缺失时 sel_map=None，行为与旧版完全一致。注意：勾选用**物理列名**（与 change_plan.changed_fields.field 同口径）。
2. **勾选过滤**（changed_cols 计算后）：未选记录→skipped_by_selection；update 且有 fields→changed_cols/record_diff 取交集，交集空→skipped、真子集→is_partial=True。
3. **动作判定**：skipped 分支在 insert/update 之前（action='skipped'，sql_preview=''）；dry_run 与执行分支均 continue 不写库，计入 records_skipped。
4. **状态分流**：回读校验成功（含无主键路径）后 `is_partial ? partial_ids : synced_ids`；末尾 partial_ids 批量 `update(sync_status='partial')`（不碰 status），synced_ids 照旧 active+synced；nochange 不受 selections 影响照旧计入 synced_ids。
5. stats 新增 `records_partial`/`records_skipped`，_finalize_sync_log summary 同步。

### F-118/F-119 前端（ArchiveDetail.vue + types + api）

- **勾选状态**：`fieldSel: Record<recordId, string[]>`（update 逐字段）+ `insertSel: Record<recordId, boolean>`（insert 整行）；`runSyncPreview` 成功后 `initSelections()` 默认全选；Step2 工具栏全选/清空+计数。
- **双预览分离**：`syncPreview`=全量预览（Step1/Step2 数据源，回退不污染）；`syncSelPreview`=按选预览（goToSqlStep 携 selections 重跑 dry_run，Step3 sqlList 唯一来源）。执行 `confirmSyncExecute` 传同一 `buildSelections()`；完成提示加部分回写/跳过条数。
- **血缘展示**：详情抽屉两处（分组 groupedSchemaBlocks/平铺 archive.schema）字段值旁 `lineage[code]` 命中时 a-tag（lineageColor: manual橙/sync蓝/resolve紫）+ a-tooltip（lineageTooltip：源表/更新时间/保护人）；记录表格 data.* bodyCell 对 `rec.overrides?.[column.fieldCode]` 命中前置🔒+tooltip。
- types：`SyncSelection{record, fields?}`、SyncChangeItem.action 加 'skipped'、SyncStats 加 records_partial?/records_skipped?；api：`syncToSource(id, operatedBy?, dryRun, selections?)`。

### 验证与环境要点

- manage.py check 0 issues；vue-tsc 0 errors；Django test Client 闭环实测 16 PASS/0 FAIL（勾选过滤/sql过滤/无交集skipped/部分执行partial/补选synced+active/无selections兼容）。
- ⚠️ 域8 七张表 is_primary 全 False → sync-to-source 平时 400（环境配置非代码缺陷）；实测时临时设表8主表后还原。
- ⚠️ 释放门控 `_field_released` 导致部分字段（如 REMARK）不在 code_to_physical 映射中→不参与比对/回写，勾选它们无效属预期。
- 本批未做：源优先级配置（BR-018-1 完整体）、血缘历史时间线。

## 2026-07-28 — REQ-018 MDM 第6批（F-114 比对引擎 / F-115 修正保护 / F-116 冲突审查队列 / F-117 建议裁决）

### 数据模型（migration 0003）

- `ArchiveRecord.overrides` JSONField：`{field_code: {protected_by, protected_at, original_value}}`——original_value 只在**首次**登记时写入，后续编辑仅刷新 protected_by/at。
- `ArchiveRecord.lineage` JSONField：`{field_code: {source: manual|sync|resolve, source_table, updated_at}}`。
- `ArchiveFieldConflict`：Status(pending/resolved_accept/resolved_keep/voided)、SuggestedAction(accept_source/keep_archive)、archive/record FK、field_code、archive_value/source_value（JSONField 双值快照）、source_table、is_protected、resolved_by/resolved_at；索引 `(record, field_code, status)` + `(archive, status)`。

### 关键数据流

1. **人工编辑**（`ArchiveRecordUpdateSerializer.update`）：
   changed_fields 计算 → 逐字段登记 override + lineage=manual → `save(update_fields=['overrides','lineage'])`。
   **不再自动 status=deleted**（第七十二轮推翻 2026-07-23 决策）；sync_status='unsynced' 保留（置顶排序依赖）。

2. **同步比对**（`_upsert_records_from_rows`，views.py）：
   对已存在记录逐字段处理 `record_data`：
   - 值一致（`==` 或 str 相等）→ 跳过；若该字段无血缘则首次补建 `lineage[code]={source:'sync',...}`（BR-018-6），仅血缘变化时 `save(update_fields=['lineage'])`；
   - 档案没有的新字段 → 收进 new_fields 直接写入 + lineage=sync；有新字段才 version+1+版本快照，且**仅当本次无冲突**时置 sync_status='synced'；
   - 值差异 → **一律不覆盖**，收进 conflict_items 批量入队：先把同 (record, field_code) 的旧 pending `update(status=voided)`（只留最新），再 `bulk_create`；`code in overrides` 则 is_protected=True + 建议 keep_archive，否则 accept_source；
   - `stats['conflicts_created']` 累计（sync_schema 与 _sync_data_from_sources 两处初始 dict 均含该键）。
   新记录创建时带全量 lineage=sync。

3. **裁决**（`ArchiveFieldConflictViewSet._apply_resolution`，transaction.atomic）：
   - accept_source：record.data[field]=source_value + version+1 + 版本快照（change_summary 含 `conflict_resolution:'accept_source'`）+ `overrides.pop(field)` + lineage=resolve；
   - keep_archive：不存在 override 则登记（original_value=source_value 语境下的档案原值）；
   - 均写 ArchiveOperationLog(UPDATE) + conflict 置终态（resolved_by/at）；非 pending 重复裁决返回 400。
   - `resolve`（单条，body: decision/operated_by）与 `batch_resolve`（body: ids/action/operated_by，返回 {resolved, skipped}）。

### API

- `GET /api/field-conflicts/?archive=&record=&status=&field_code=`（ReadOnlyModelViewSet，get_queryset 手动过滤）
- `POST /api/field-conflicts/{id}/resolve/`
- `POST /api/field-conflicts/batch-resolve/`

### 前端（ArchiveDetail.vue）

- 「冲突审查」按钮（header，a-badge 包 pendingConflictCount）→ activeTab='conflicts' v-show 分区（沿用去 Tab 化模式）。
- 状态筛选默认 'pending'；row-selection 仅 pending 筛选态启用；批量/单条裁决均 a-popconfirm；accept_source 后 loadRecords() 刷新记录表。
- doSyncSchema 完成提示含 conflicts_created；>0 时 Modal.warning 引导去冲突审查 Tab。
- types：FieldOverride/FieldLineage/ArchiveFieldConflict/SyncStats.conflicts_created；api：conflictApi(list/resolve/batchResolve)。

### 验证与已知现象

- manage.py check 0 issues；vue-tsc 0 errors；Django test Client 闭环实测全 PASS（编辑保持 active/override 登记/受保护不覆盖/入队 protected+keep_archive/双路径裁决/重复裁决400/快照含裁决摘要/列表筛选）。
- **机制切换首拉现象**：档案5 首次逐字段比对暴露 451 条存量真实差异冲突（历史无条件覆盖时代遗留 + 编辑过的字段），属预期，需人工在冲突审查 Tab 消化。
- 本批未做：F-118 字段级回写（sync-to-source 重做为字段级勾选）、F-119 血缘展示（前端 lineage 可视化）。

## 2026-08-05 — 第一百二十轮：档案权限全景（只读审计聚合视图，仅管理员）

### 后端（views.py ArchiveViewSet.permission_overview，83 行）

- 入口：`GET /api/archives/{id}/permission-overview/`（detail action）；IsMdmAdmin 不通过 → 403「仅管理员可查看权限全景」（从 apps.auth.views 函数内延迟导入，避免循环）。
- 返回结构：`{archive:{id,name,domain_id}, field_names:{code→name，取自 archive.schema}, apis:[...], roles:[...]}`。
- 机器权限聚合：ArchiveApi.filter(archive).order_by('id').prefetch_related('key_grants__api_key')；每个 API 输出 id/name/slug/status/allowed_operations/exposed_fields + grants（key_name/key_status/allowed_operations）+ call_stats（total/last_at/by_key：遍历 ApiCallLog.filter(api_id).iterator() 按 key_name 快照聚合 count/last_at/ips≤5 个）。
- 人用权限聚合：RoleFieldPermission.filter(domain_id=archive.domain_id) + role.user_profiles 输出 role_id/role_name/is_builtin/visible_codes/editable_codes/users（username/display_name/is_active）。
- 零新模型：全复用 v19（ArchiveApi/ApiKey/ApiKeyGrant/ApiCallLog）+ REQ-019（Role/RoleFieldPermission）数据结构。

### 前端

- `components/PermissionOverview.vue`（新建 203 行）：props {open, archiveId, archiveName}，watch open 拉数据；960px 抽屉两区块——机器权限表（接口名称/对外路径/状态/允许操作/暴露字段 tags tooltip=code/授权密钥/调用情况，scroll.x=910）+人用权限表（角色/可见字段/可编辑字段 green tags/用户，禁用用户灰色标注）；区块头「去配置 →」分别跳 /archive/api-management 与 /settings/roles；空态 a-empty；OP_LABELS 与 ApiManagement/ApiKeyTab 一致（查询/新增/修改/删除）。
- `ArchiveList.vue`：操作列「同步」与「删除」之间插「权限」链接（v-if isAdmin）；onMounted 末尾 getMeApi() 判 isAdmin（失败按非管理员）；操作列宽 320px 不溢出。
- `api/archive.ts` archiveApi.permissionOverview(id)；`types/index.ts` PermissionOverview/PermissionOverviewApi/PermissionOverviewRole 三接口。

### 验证

- 定向回归 test apps.archive **40/40 PASS**（含新增 PermissionOverviewTest 3 用例：结构全断言/非管理员 403/空档案 200）。
- vue-tsc 0 errors。
- 真实请求实测 smoke_permission_overview.py **7/7 PASS**：admin 档案 9（配 2 个 API）200+顶层键/api 项键/call_stats 结构/roles 结构齐全；probe_user 403。注意：实测前重启后端（旧进程未加载新 action），杀进程前先 netstat 确认端口状态（沿用上轮双进程教训）。
- Browser 子代理验证：admin 操作列有「权限」，抽屉两区块数据正确（门店档案 2 个 API/23 暴露字段/2 密钥/3 次调用 + 2 角色），「去配置」链接指向正确；probe_user 操作列无「权限」链接且直连 API 403；console 零报错。

## 2026-08-06 | 第一百二十三轮：uxqa 整改 R-055 档案记录启停补二次确认

### 前端（views/archive/ArchiveDetail.vue）

- `doToggleStatus` 外包 `Modal.confirm`：停用 → title「确认停用这条记录」/okText 确认停用/okType danger；启用 → title「确认启用这条记录」/okType primary；cancelText 统一「取消」
- 开关为受控绑定（`:checked="rec.status==='active'"`），取消确认后状态自动回弹，无需手动回滚（浏览器实测验证：取消后列表不刷新、开关回原位）
- 复用同文件既有 4 处 Modal.confirm 骨架（复制式复用，与回滚确认同风格）

### 验证

- vue-tsc -b 0 errors
- 浏览器实测 PASS：点开关 →「确认停用这条记录」弹窗出现 → 取消后开关回到启用态、974 条记录列表不变；console 0 error

## 2026-08-06 | 第一百二十四轮：uxqa 整改 R-056 记录详情 1400 modal → 1100 大抽屉

### 前端（views/archive/ArchiveDetail.vue）

- `detailModal` 容器 a-modal → a-drawer：width 1400px → 1100px；bodyStyle 从 maxHeight 70vh 滚动改为 padding 16/24（抽屉 body 天然全高滚动，无需限高）
- 底部「关闭/暂存修改」按钮从 body 尾部移入 `#footer` slot 固定底栏（暂存禁用逻辑不变：editChanges.length === 0）
- 暂存编辑/变更预览/分组网格（groupedSchemaColumns/schemaGridStyle）全保留；状态变量 detailModal 与 openDetailDrawer/handleSaveDrawer 未改名，调用方零影响
- 复用扫描：全站已有 a-drawer 骨架（ConsistencyCheck 50vw / PermissionOverview 960 / ApiKeyTab 900+1000 / RoleManagement 760 / ApiManagement 900+1000），本次 1100 为新增最大档，无新组件

### 验证

- vue-tsc -b 0 errors
- Browser 子代理实测 6/6 PASS：右侧滑入（DOM ant-drawer-open 无 ant-modal，宽 1100px）/元信息+26 字段（7 可编辑）/footer 固定底栏/暂存修改初禁用→改「联系人」后启用+「共修改了 1 个字段」预览/关闭后 974 条记录列表完好/console 0 error

## 2026-08-06 | 第一百二十五轮：uxqa 整改 R-057 变更历史弹窗收敛为 ChangeHistoryDrawer 单组件

### 新组件（views/archive/components/ChangeHistoryDrawer.vue，201 行）

- 两处同构拷贝收敛为单组件：ArchiveDetail（带回滚）+ VersionManagement（只读）→ props `open/recordId/title/enableRollback` + emits `update:open/rolled-back`（防 R-048/R-049 式分叉演化）
- 容器：a-drawer 900px（沿用全站既有档位）+ a-timeline 时间线 + 双粒度回滚 dropdown（回滚此条/回滚到此），回滚区由 enableRollback 控制显隐
- 收敛口径裁决：①数据加载取 VM 全量分页（AD 原仅单页 50 条 → 统一 `changeLogApi.listDetails({ page_size: 200, ordering: '-id' })` 循环全量）②版本映射（v前 → v后）与记录级变更提示保留（VM 侧更全）③timeline 色映射取 AD 完整版（含 rollback 橙）④回滚成功后组件自行重载时间线 + emit('rolled-back') 由父组件刷列表

### ArchiveDetail.vue（5 对替换）

- historyModal 45 行 a-modal → ChangeHistoryDrawer 挂载（enableRollback + @rolled-back，标题仍取 schema 前 3 字段拼接）
- 死预载清理：openDetailDrawer 内删除 rollbackPanelKey/rollbackHistory 复位 + loadRollbackHistory 调用（详情内回滚面板早已删除的遗留死代码，每次开详情省一次浪费 API 请求）
- 状态变量 7 个（rollbackPanelKey/rollbackLoading/rollbackHistory/rollbackingId/historyModal/historyRecord/historyModalTitle）收敛为 3 个（historyOpen/historyRecordId/historyTitle）
- 十个函数 121 行删除 → 新 openHistoryModal + onHistoryRolledBack（回滚后刷详情抽屉上下文 + 记录列表）；import 删 ChangeDetail 类型（本文件不再使用）

### VersionManagement.vue（5 对替换）

- historyModal 36 行 a-modal → ChangeHistoryDrawer 挂载（只读，不传 enableRollback，标题沿用 historyLabel）
- 状态区删 historyModal/historyLoading/historyList/historySourceColor/timelineColor → historyOpen + historyLabel 两变量；openHistory/openHistoryFromRecord 改为仅 set recordId + open（加载由组件 watch 承接）
- loadHistory 函数 21 行删除；ChangeDetail 类型保留（列表明细行回滚 canRollbackDetail/handleRollbackDetail 仍在用，签名与 AD 侧不同不合并）；recordModal 记录详情弹窗不动（R-060 批5 处理）

### 验证

- vue-tsc -b --force 0 errors；残留引用核查双文件零命中（historyModal/rollbackHistory/loadHistory 等）
- Browser 子代理实测 8 项全 PASS：场景 A（档案详情）900px 抽屉 + 时间线 12 条含版本映射 + 双粒度回滚 dropdown + 关闭重开重新加载 + 随记录切换；场景 B（变更日志页）同款抽屉只读（回滚按钮数 = 0）+ 记录详情弹窗内「变更历史」可转同一抽屉；console 0 error（截图受自动化浏览器 visibilityState=hidden 渲染帧限制未能留存，DOM/Network 证据链完整）

## 2026-08-06 | 第一百二十六轮：uxqa 整改 R-062 刷新预检弹窗收敛为 RefreshPreviewModal 单组件

### 新组件（views/archive/components/RefreshPreviewModal.vue，115 行）

- 两处同构拷贝收敛为单组件：ArchiveList（操作列「同步」入口）+ ArchiveDetail（「立即刷新」入口）→ props `open/previewData/archiveName` + emits `update:open/confirm`（组件名呼应 R-016 当初建议名；防 R-016/R-048 式再次分叉）
- 组件职责边界：只展示预检结果（schema 变化 + 数据试算 + 波及告警 + warnings/errors）并发出确认意图；确认后的执行逻辑（syncSchema/refreshData + stats 汇报 + 刷新页面）留父组件——两处刷新对象不同（列表刷列表、详情刷档案+记录）
- 标题组件内 computed：带档案名 `刷新预检 — {name}`，无名兜底「刷新预检：检测到以下变化」

### ArchiveList.vue（切片替换 L41-126 + 2 对）

- 86 行 a-modal → RefreshPreviewModal 挂载（v-model:open + :previewData + :archiveName + @confirm）
- stats 汇报文案泛化（R-048/R-049 同类分叉补齐）：confirmRefresh 补 `records_reactivated` 复活文案 + tables_synced 动词按 schema 是否变化区分「同步/刷新」（取 AD 完整口径）

### ArchiveDetail.vue（切片替换 L256-343 + 1 对）

- 88 行 a-modal → RefreshPreviewModal 挂载；previewLoading（立即刷新按钮 loading）保留不动

### 验证

- vue-tsc -b --force 0 errors；残留引用核查：两文件刷新预检 a-modal 全删，挂载点唯一，previewModal/previewData 状态引用完整
- Browser 子代理实测 6 项 PASS：场景 A 无变化分支（toast「数据已是最新」+ 弹窗不出现）+ schema 变化分支（子代理主动注入建模变化 SF#27 维护方触发：760px modal、标题带档案名、schema alert+字段变更明细、「取消」零 POST、「确认更新」POST sync-schema 200 + 列表 Schema 版本 2→3）；场景 B 详情页（按钮 loading + 同款弹窗 + 确认后记录表重新加载）；DOM 单实例无残留容器（modalCount=1）；console 0 error；注入测试后数据已复原（维护方还原 source）。截图受自动化浏览器 hidden-tab 渲染冻结未能留存，DOM/Network 证据链完整

---

## 2026-08-11 明细致子表交互改造「先注册后挂载」编码

### 改动清单

1. **新模型 DetailTableConfig**（modeling/models.py 569-587）：子表注册独立落库，字段 domain/table/row_key_field/display_sort_field/display_sort_desc/conditions/mapping_count；FieldMapping 加 detail_config FK（SET_NULL，related_name='mappings'），旧 inline detail 字段 deprecated 兼容存量
2. **迁移 0031**：创建 DetailTableConfig 表 + FieldMapping.detail_config 列；RunPython 存量自动注册幂等收敛（id=23 28→22 自动创建 DetailTableConfig 并挂载；id=25 27→28 方向异常同样注册但由 detail-check 提示）
3. **DetailTableConfigSerializer** + **DetailTableConfigViewSet**（ModelViewSet + detect-row-key action）：CRUD + 行键检测
4. **detail-check action**（POST /field-mappings/detail-check/）：返回 registered/unregistered/suspect 三类，suspect 检测方向可疑的 detail 映射（source_table 无映射到档案主键的列）
5. **同步引擎多挂载改造**（archive/views.py 主循环 1280-1302 + _sync_detail_rows 内部取值）：主循环从 `.first()` 改为 `.all()` 循环 _sync_detail_rows；_sync_detail_rows 行键/排序/条件取值优先读 detail_config（回退 fm 内联字段兼容存量）
6. **前端 DomainFieldMapping.vue 改造**（主改造文件）：① Header 加「明细检查」徽章按钮 +「子表注册」按钮 ②新建 detail-config 管理弹窗（选择表/行键/检测按钮/排序/条件，独立保存不依赖主表）③新建映射弹窗 detail 区改为「关联子表配置」下拉选 + 配置摘要展示（禁用内联编辑）④ detail-check 结果抽屉⑤ handleSubmit 改存 detail_config_id ⑥编辑弹窗回显 detail_config_id ⑦自动匹配源表
7. **API 层**（api/modeling.ts + types/index.ts）：detailConfigApi(list/create/update/delete/detectRowKey) + detailCheck + FieldMapping detail_config/detail_config_id/detail_config_name + DetailTableConfig 接口

### 遗留
- 无新增路径（全是改动现有端点），未加新测试用例
- 存量 id=25 方向异常由 detail-check 提示 + 用户手动修正（用户已裁决并入交互改造统一修正）

---

## 2026-08-12 全量同步实测（用户要求「先走通有数据的」）

### 测试方式
- 临时脚本 diag_full_sync.py 模拟前端全流程：refresh-preview 预检 → 确认 → POST sync-schema（预检发现 schema 有变化，走全量拉取+重建 schema 路径）
- 600s 测试脚本超时被杀，但**后端同步线程仍在执行**（客户端断开不终止服务端线程）；期间 SQLite 被写锁锁死（database is locked），系统整体不可用
- 通过监控 dev.db-journal 文件判断写事务活跃度（autocommit 每条 save 单独事务，journal 短暂消失是事务间隙）；连续 90s 无 journal 确认同步结束

### 结果（最终态，2026-08-12 验证）
- ArchiveRecord = **209,123** 条（全部 active/synced），创建窗口约 18 分钟
- ArchiveRecordDetail = **49,588** 条：mapping_id=3（价目表明细）24,794 + mapping_id=9 24,794（收尾阶段补入 8,041 条）
- 主记录字段：部分记录 11 字段（含 PRICE/TO_QTY/PRICE_UNIT_ID/PRICE_BASE/FORBID_STATUS 代表行字段），其余仅 6 主表字段
- 档案状态仍 draft、schema_version=1、schema 32 字段

### 关键教训（测试环境行为，非产品代码缺陷）
1. **客户端断开不终止服务端同步线程**：测试脚本被杀后同步继续跑完，是「点击后等很久」体验的另一层原因——全量同步本身 18 分钟+ 且期间 SQLite 单写者锁导致 API 全部排队
2. 前端 axios 30s 超时 < 后端 36s 预检耗时（第 149 轮已修 refreshPreview 180s）

### 遗留问题（已定位未修复，待用户裁决）
1. **变更批次/操作日志缺失**：ChangeBatch=0、操作日志仅 1 条 create——sync_schema 收尾（变更批次落库 + SCHEMA_SYNC 日志）未执行，疑似请求线程异常中断
2. **物料分组明细 0 条**：cfg id=6 pk_physical_to_schema 为空——GROUP_ID 经 FieldMapping 中转映射不在 code_to_physical/match_channels 直接匹配通道，_sync_detail_rows 直接 return
3. **row_key 配置错误**：cfg id=2 row_key_field=MATERIAL_ID 非唯一，价目明细 239,504 行去重为 24,794 条（每物料仅保留排序后最后一条）
4. **NAME/DESCRIPTION（价目表头）0 值**：抽查 100 条 NAME 0/100，维度表中转写入未生效
5. **代表行字段覆盖不均**：仅 24,794 条有价目明细的物料含 PRICE 等字段，其余仅 6 主表字段（架构预期：代表行只更新有明细的物料）

### 验证证据
- API refresh-preview 实测：36s 返回 timeout=200、tables_checked=3、errors=[]、would_create=209123
- 最终数据态 shell 查询：209,123 / 49,588 / 0 / 0 / 1
- 临时诊断文件 diag_*.py、diag_out*.txt 已全部清理

---

## 2026-08-13 代表行写主表分组修复（对齐第133轮锁定语义）

### 背景
- 第 133 轮方向锁定语义：「默认价 = 每物料 EFFECTIVE_DATE 最新 + 行键最大」
- 批1 实现错误：_sync_detail_rows 代表行只写 sorted_rows[0]（全局排序首行）→ 25,993 个有价目明细的物料中仅 1 个在主表有 PRICE
- 版本快照实证：209,125 条 update 版本中仅 3 条含 PRICE 字段

### 改动
- `backend/apps/archive/views.py`（L2081-2092）：代表行改为按物料（rec_key）分组遍历——每组取排序后首次出现的行（= 首行），跳过已见过的同组键
- 新行为：每 mapping/每次同步对 N 个有明细的物料各写 1 条代表行

### 验证
- django check 0 issues
- archive DetailSyncEngineTest 8/8 PASS（0.043s）
- 代码逻辑分析：多物料时 seen_keys 去重生效

### 遗留
- 本修正是逻辑修复，未重跑同步刷新数据（用户确认「数据不用处理，只管系统逻辑」）
- 下次全量同步时代表行将正确按物料分组写入
