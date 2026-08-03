# 开发日记 — archive 模块

> 记录 archive 模块编码实现的关键数据流与实现要点，供后续影响分析使用。

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
