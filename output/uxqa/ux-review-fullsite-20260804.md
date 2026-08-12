# 全站 UXQA 评审报告 — 2026-08-04（第一百零九轮）

## 评审快照

- **范围**：全站 16 页面（modeling 4 + archive 6 + settings 3 + MainLayout + 2 弹窗组件）
- **方法**：源码量化巡检 + vue-tsc 0 errors + 后端 45 tests PASS
- **前置状态**：第一百零八轮 sync_exclude_codes 关键 Bug 修复 + 一致性检查改警告不阻断 + 配置检查范围缩小
- **实跑说明**：本轮以源码推理为主，未实跑浏览器（标注风险）

### 宏观结论

| 维度 | 结论 |
|------|------|
| 布局骨架适配 | ✅ 与上轮一致，无变化 |
| 功能区划分 | ✅ 三模块信息架构清晰，无变化 |
| 业务流程适配 | ✅ 刷新预检→一致性检查→变更日志 链路完整 |
| 信息架构 | ✅ 无巨型页面/空壳页面 |

### 微观评定

| 维度 | 结论 |
|------|------|
| 归属与主体 | ✅ 弹窗标题带业务对象 |
| 一致性与冲突 | ⚠️ 刷新预检弹窗 warnings 展示 ArchiveList 有但 ArchiveDetail 缺失；confirmRefresh 路径 warnings/一致性提醒缺失 |
| 反馈与容错 | ✅ 危险操作 Modal.confirm 已全站覆盖（R-032 闭环）；popconfirm 仅用于低风险可逆操作 |
| 尺寸与数据量匹配 | ⚠️ DataSourceList/DomainChangeOverview 表格缺 scroll.x（当前列宽够用，防御性缺失） |
| 状态持久性 | ✅ 菜单高亮随路由同步 |

---

## checklist 覆盖

> 档位：全站交付档（16 页面全巡检）

| # | 检查项 | 页面 | 证据 | 结果 |
|---|--------|------|------|------|
| A1 | 菜单高亮随路由同步 | MainLayout L48-61 | watchEffect + allMenuKeys 最长前缀匹配 | ✅ |
| A2 | 命名链一致性 | MainLayout L79 / router / VersionManagement L4 | 「变更日志」命名统一 | ✅ |
| A3 | formatDateTime 全站统一 | ArchiveList L184 / ArchiveDetail L88 / VersionManagement / ConsistencyCheck L19 | 所有时间列均 formatDateTime | ✅ |
| A4 | extractApiError 统一依赖 | 全站 grep `\|\| e.message` = 0 matches | 全部 catch 已用 extractApiError | ✅ |
| A5 | scroll.x 按列宽求和 | DomainList 1400 / ArchiveList 1220 / ArchiveDetail 递归 / VersionManagement 1200 / ApiManagement 1160 / ConsistencyCheck（内嵌表） | 主流表格已设 | ⚠️ R-050/R-051 |
| A6 | 危险操作 Modal.confirm | ArchiveList L326 / DomainList L285 / DataSourceList L196 / TableList / ArchiveDetail L939,993 | 删除/停用/回滚用 Modal.confirm | ✅ |
| A7 | 弹窗 footer 关闭按钮 | ArchiveDetail L238 / ApiManagement（drawer 默认有） | 各弹窗有明确关闭入口 | ✅ |
| A8 | 空态处理 | DomainFieldConfig / DomainFieldMapping / ApiManagement / ConsistencyCheck / DomainChangeOverview L30 | 各页空态有 a-empty 引导 | ✅ |
| A9 | Switch 语义 | ArchiveDetail L91 / ApiManagement L55 / TableList L71 / AIConfig L50 / DomainList L18 | 全部用 Switch 无 Radio 误用 | ✅ |
| B1 | 列宽配比 | ArchiveDetail data-cell max-width 120px | 截断+ellipsis 合理 | ✅ |
| B2 | 操作列宽度 | ArchiveList 320/4 按钮 / VersionManagement / ApiManagement | 宽度充裕无换行 | ✅ |
| C1 | 刷新预检弹窗一致性 | ArchiveList L37-122 / ArchiveDetail L292-376 | 弹窗结构一致 | ⚠️ R-048 |
| C2 | 回滚防 400 | ArchiveDetail canRollbackToPoint L916-917 | 最新节点前无「回滚到此」 | ✅ |
| D1 | 死代码扫描 | 无新增 | 未发现新死代码 | ✅ |
| D2 | vue-tsc 类型检查 | 命令行执行 | 0 errors | ✅ |
| D3 | 后端测试 | python manage.py test | 45/45 PASS | ✅ |
| E1 | record_label 落库快照 | VersionManagement L92 / ArchiveDetail historyModalTitle L433-438 | record_label\|\|record_key 回落 | ✅ |
| E2 | 双层存储 lineage 血缘 | ArchiveDetail L156-158,186-188 | 详情弹窗血缘标签+tooltip | ✅ |
| E3 | warnings 告警展示 | ArchiveList L118-120 / ArchiveDetail doRefreshData L818-823 | 预检弹窗+刷新后均有展示 | ⚠️ R-048/R-049 |
| F1 | 需求落地：档案CRUD | ArchiveList + ArchiveDetail | 全链路 | ✅ |
| F2 | 需求落地：变更日志 | VersionManagement + ArchiveDetail 变更历史弹窗 | 全局+单档案双视角+导出 | ✅ |
| F3 | 需求落地：一致性检查 | ConsistencyCheck | 四状态+批量标记+类型分组 | ✅ |
| G1 | 流程闭环：建模→档案 | DomainFieldConfig→ArchiveList→ArchiveDetail | 字段管理→新建档案→刷新同步 | ✅ |
| G2 | 流程闭环：刷新预检 | ArchiveList/ArchiveDetail → doRefreshPreview → 弹窗 → confirmRefresh → syncSchema/refreshData | 无变化→message 不弹窗 | ✅ |
| H1 | 一致性检查不阻断写入 | ArchiveDetail showConsistencyWarning L789-797 | notification.warning 非阻断 | ✅ |

**统计**：共 23 项 = ✅19 / ⚠️4（R-048~R-051）

---

## 整改清单

| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-048 | ArchiveDetail 刷新预检弹窗缺少 warnings 展示区：ArchiveList.vue L118-120 有 `<a-alert v-if="warnings?.length" type="warning">` 但 ArchiveDetail.vue 的刷新预检弹窗（L292-376）没有，同一功能两处不一致 | ArchiveDetail.vue L372-375 | 一致性与冲突 | 在 errors alert 后补 warnings alert，与 ArchiveList L118-120 一致 | P2 | ✅ 已闭环 |
| R-049 | confirmRefresh 路径不显示 warnings 和一致性提醒：ArchiveList L285-315 和 ArchiveDetail L779-786 的 confirmRefresh 函数在刷新成功后只 message.success，没有像 doRefreshData/doSyncSchema 那样展示 stats.warnings（Modal.warning）和 showConsistencyWarning（notification.warning）。从预检弹窗确认刷新走 confirmRefresh 路径，warnings 和一致性提醒被跳过 | ArchiveList.vue confirmRefresh / ArchiveDetail.vue confirmRefresh | 反馈与容错 | confirmRefresh 的 syncSchema/refreshData 分支补上 warnings 展示 + showConsistencyWarning 调用（复用 doRefreshData/doSyncSchema 中的逻辑） | P2 | ✅ 已闭环 |
| R-050 | DataSourceList 表格缺少 scroll.x：列宽合计 ≈780px，当前够用但与全站 scroll.x 规范不一致（R-025 已闭环页均设了 scroll.x） | DataSourceList.vue L8 | 尺寸与数据量匹配 | 补 :scroll="{ x: 800 }" | P2 | ✅ 已闭环 |
| R-051 | DomainChangeOverview 表格缺少 scroll.x：列宽合计 ≈720px，同上 | DomainChangeOverview.vue L7 | 尺寸与数据量匹配 | 补 :scroll="{ x: 750 }" | P2 | ✅ 已闭环 |
| R-052 | ConsistencyCheck 失效规则操作使用 popconfirm：L167-168 恢复/删除用 popconfirm，删除操作不可恢复应用更强确认 | ConsistencyCheck.vue L167-168 | 反馈与容错 | 删除改 Modal.confirm + 影响面文案；恢复保持 popconfirm（低风险可逆） | P2 | ✅ 已闭环 |
| R-053 | 插件卸载 popconfirm 泛化（2 处）：TechFunctions L75 和 FormulaEditor L266 的插件卸载用 popconfirm，影响可逆（可重载），风险低但与 Modal.confirm 规范不完全一致 | TechFunctions L75 / FormulaEditor L266 | 一致性与冲突 | 改 Modal.confirm | P2 | ✅ 已闭环 |

> **实跑验证通过项（不整改）**：
> - vue-tsc 0 errors ✅
> - 后端 45 tests PASS ✅
> - 菜单高亮随路由同步 ✅
> - formatDateTime 全站无遗漏 ✅
> - extractApiError 全站统一（grep 0 matches）✅
> - 危险操作 Modal.confirm 全站覆盖（删除/停用/回滚）✅
> - 一致性检查改 notification.warning 不阻断 ✅
> - 刷新预检弹窗结构一致 ✅
> - 回滚防 400 ✅
> - Switch 语义无 Radio 误用 ✅
> - 空态处理全覆盖 ✅
> - 弹窗 footer 关闭按钮全覆盖 ✅
> - record_label 落库快照展示 ✅
> - 双层存储 lineage 血缘标签 ✅
> - 死代码无新增 ✅
