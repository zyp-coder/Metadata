# Debug 日记 — archive 模块

> 记录 archive 模块的 Bug 根因、修复方式与已知耦合点，供后续影响分析使用。

## BUG-2026-0725-04 回滚功能报错：旧 Django 进程未加载新端点

- **现象**：v17 回滚功能上线后，前端点「回滚」报错。
- **根因**：两层叠加：
  1. 主因：运行中的 Django 服务（旧 PID 23608，`--noreload` 启动）在回滚代码写入前就已启动，未加载 /change-details/{id}/rollback/ 与 /records/{id}/rollback-to-change/ 新路由 → 404 HTML 页（实测复现）。测试进程（Django test Client 新进程）冒烟单条回滚 200 ✓，证明代码本身正常。
  2. 次因（真 Bug）：历史回滚时间线**最新节点**也显示「回滚到此」按钮，点击必然 400「该时间点之后无可回滚的变更」（时间点回滚语义=撤销此后变更，最新节点无后续）。
- **修复**：
  1. 重启后端（新 PID 31544），端点实测生效；端到端冒烟：时间点回滚 200 + 留痕 change_type=rollback ✓。
  2. 前端新增 `canRollbackToPoint(index)`：时间线按 id 降序，仅当 `slice(0, index)` 中存在非 created/rollback 的变更时才显示「回滚到此」（最新节点自动隐藏）。
- **已知耦合点/经验**：
  - 后端用 `--noreload` 启动：**每次新增/修改 API 后必须手动重启**，否则新端点 404（历史已多次踩坑：第八十七/八十八轮均重启过）。排查此类「代码对但接口报错」先查进程新旧：test Client 能通但 HTTP 打不通 = 服务进程旧。
  - 详情弹窗与变更历史弹窗共用 rollbackHistory/rollbackLoading 数据源，`refreshAfterRollback` 以弹窗打开状态（historyModal/detailModal）判定刷新目标。

## BUG-2026-0728-03 档案 schema 字段口径/分组与建模脱节 + 改过记录不置顶

- **现象**（第七十轮测试报告，页面 /archive/5，3 项）：
  1. 档案界面分组（基本信息/地址信息/展厅信息）与建模字段分组（门店信息/省市区/联系信息/状态信息/经纬度/地理位置）不一致；
  2. 档案 schema 38 字段 vs 建模「档案字段」28 行——18 个 archive_category='unassigned' 字段混入档案（实证 IS_GZ_PCS、STORE_VERSION、N_AREA、D_CHECK_DATE 等）；
  3. 表格改过（未同步）的记录不置顶，靠 Meta ordering=['-updated_at'] 排序。
- **根因**（同一系统性缺陷两处表现 + 一处排序缺失）：
  1. `archive/views.py _field_released(f, sf)` 只做两层释放门控（release_to_concept + release_to_archive/is_active），**没有三分类口径**（第五十九轮已定：档案字段 = base 物理字段 + active 组合字段 + active 计算字段）；modeling 的 standard-fields action 已按此过滤，档案侧漏改——同类模式缺失。
  2. Archive.schema 是快照，仅创建/sync-schema 时刷新；建模侧改分组后档案不自动更新（快照过期），且 `_generate_schema_from_domain` 原按 table__id 排序不按分组排序。
  3. ArchiveRecordViewSet.get_queryset 无置顶逻辑。
- **修复**：
  1. `_field_released` 加三分类判定：sf 存在须 `sf.status=='active'`；solo 须 `f.archive_category=='base'`。该函数是唯一门控——schema 生成、sync_to_source 回写映射、modeling archive-preview 三个调用点自动统一。
  2. `_generate_schema_from_domain` 排序改 `F('group__sort_order').asc(nulls_last=True), F('group__id').asc(nulls_last=True), 'sort_order', 'id'`，分组顺序对齐建模、未分组排后。
  3. `ArchiveRecordViewSet.get_queryset` 加 `annotate(_sync_rank=Case(When(sync_status='synced', then=1), default=0)).order_by('_sync_rank','-updated_at')`——未同步置顶。
  4. 对档案5 重跑 sync-schema：schema 38→29 字段（27 物理 + 2 计算），分组与域8 完全一致，18 个未分配字段移除（记录 data 保留，仅不再展示/回写）。
- **已知耦合点**：
  - `_field_released` 是档案字段口径的**唯一收口点**，任何新增「字段是否进档案」判断必须走它，禁止在调用点再散写过滤条件。
  - `ArchiveRecord.sync_status` 是普通 CharField（无枚举类），取值 unsynced/synced/partial/error——代码里只能写字符串字面量。
  - Archive.schema 快照机制不变：建模侧改分组/口径后需手动 sync-schema 才生效（页面有同步模型变更按钮）。
  - ~~编辑记录后自动 status='deleted'~~【已于 2026-07-28 第七十二轮取消】：编辑后不再自动停用，改为登记 override 修正保护+lineage=manual；`sync_status='unsynced'` 仍会设置，置顶排序仍依赖此标志；sync_to_source 恢复 active 语句保留仅兼容存量 deleted 记录。
  - MDM 第6批新增耦合点：`_upsert_records_from_rows` 已是逐字段比对引擎，任何改动必须保持「差异不覆盖只入队 ArchiveFieldConflict」铁律；overrides/lineage 的读写分散在 serializers（编辑登记）/views 比对引擎（补血缘）/_apply_resolution（裁决解除）三处，数据结构变更需三处同步。
- **验证**：sync-schema 200，schema_version 2→3、字段 38→29、分组顺序=经纬度/门店信息/省市区/联系信息/状态信息/地理位置/(空)/计算字段、未分配字段残留=无；置顶排序可逆实测：将最旧记录临时置 unsynced 后 API 第一页首条即该记录（PASS），随后还原。
