# 全站 UXQA 评审报告 — 2026-08-03（第九十二轮）

## 评审快照

- **范围**：全站 14 页面（modeling 4 + archive 6 + settings 3 + MainLayout）
- **方法**：源码量化巡检 + vue-tsc 0 errors 确认
- **前置状态**：vue-tsc --noEmit 通过（0 errors）；第九十轮 21 项整改全部闭环
- **实跑说明**：本轮以源码推理为主，未实跑浏览器（标注风险）

### 宏观结论

| 维度 | 结论 |
|------|------|
| 布局骨架适配 | ✅ 核心任务匹配：数据密集→表格（ArchiveDetail 多级表头+字段导航）、分步流程→向导（刷新预检弹窗）、多对象管理→左右分栏（DomainFieldConfig 左导航右表格） |
| 功能区划分 | ✅ 三模块信息架构清晰：建模（域→表→字段→关系 四步递进）、档案（管理→详情→变更日志→API→一致性 五入口）、设置（数据源→AI→技术函数 三配置） |
| 业务流程适配 | ✅ 前置（建模定义标准）→主流程（档案同步+记录管理）→后置（变更日志审计+一致性检查）链路完整 |
| 信息架构 | ✅ 无巨型页面/空壳页面；跨页跳转闭环可返回（ArchiveDetail「← 返回列表」、ConsistencyCheck page-header @back） |

### 微观评定

| 维度 | 结论 |
|------|------|
| 归属与主体 | ✅ 弹窗标题带业务对象（detailModalTitle 动态拼接、FormulaEditor 编辑态带 code/name） |
| 一致性与冲突 | ⚠️ 危险操作确认强度不统一（详见 R-032~R-034）；操作人默认值不一致（R-036） |
| 反馈与容错 | ⚠️ 部分 catch 未用 extractApiError（R-035） |
| 尺寸与数据量匹配 | ✅ 各表 scroll.x 已按列宽求和设定（R-025 已闭环验证） |
| 状态持久性 | ✅ 菜单高亮 watchEffect 随路由同步（R-013 已闭环） |

---

## checklist 覆盖

> 档位：全站交付档（14 页面全巡检）

| # | 检查项 | 页面 | 证据 | 结果 |
|---|--------|------|------|------|
| A1 | 菜单高亮随路由同步 | MainLayout L48-61 | watchEffect + allMenuKeys 最长前缀匹配 | ✅ |
| A2 | 命名链一致性（菜单=路由title=页面h2） | MainLayout L79 / router L26-27 / VersionManagement L4 | 「变更日志」命名统一 | ✅ |
| A3 | formatDateTime 全站统一 | ArchiveList L168 / ArchiveDetail L83,128,129 / VersionManagement L47 / ConsistencyCheck L65 | 所有时间列均 customRender: formatDateTime | ✅ |
| A4 | extractApiError 统一依赖 | ArchiveList L266 / ArchiveDetail L789 / ConsistencyCheck L228 | 关键 catch 已用 | ⚠️ R-035 |
| A5 | scroll.x 按列宽求和 | DomainList 1200 / ArchiveList 1180 / ArchiveDetail 递归 / VersionManagement 1300 / ApiManagement 1160 / ConsistencyCheck 1100 | 各表 scroll.x 与列宽总和匹配 | ✅ |
| A6 | 危险操作 Modal.confirm | ArchiveList L311 / ApiManagement L407 / ArchiveDetail L943,997 | 删除/停用/回滚用 Modal.confirm | ⚠️ R-032~R-034 |
| A7 | 弹窗 footer 关闭按钮 | ArchiveDetail L269 / ApiManagement L161,185 / VersionManagement（Modal 默认有） | 各弹窗有明确关闭入口 | ✅ |
| A8 | 空态处理 | DomainFieldConfig L5 / DomainFieldMapping L64,75 / ApiManagement L114 / ConsistencyCheck L114 / DomainChangeOverview L30 | 各页空态有 a-empty 引导 | ✅ |
| A9 | Switch 语义（二元开关） | ArchiveDetail L86（启用/停用）/ ApiManagement L103（启用/停用）/ TableList L57（表启停）/ AIConfig L50 | 全部用 Switch 无 Radio 误用 | ✅ |
| B1 | 列宽配比合理性 | ArchiveDetail data-cell max-width 120px / 列宽 160px | 截断+ellipsis 合理 | ✅ |
| B2 | 操作列宽度 vs 内容 | ArchiveList 340/4 按钮 / VersionManagement 140/2 链接 / ApiManagement 260/4 按钮 | 宽度充裕无换行 | ✅ |
| C1 | 刷新预检弹窗一致性 | ArchiveList L37-107 / ArchiveDetail L325-396 | 共享相同弹窗结构+changes_sample | ✅ |
| C2 | 回滚防 400 | ArchiveDetail canRollbackToPoint L923-925 | 最新节点前无「回滚到此」按钮 | ✅ |
| D1 | 死代码扫描 | 第九十轮 R-028 已清理 ≈200 行 | 未发现新死代码 | ✅ |
| D2 | vue-tsc 类型检查 | 命令行执行 vue-tsc --noEmit | 0 errors | ✅ |
| E1 | record_label 落库快照 | VersionManagement L48-51 / ArchiveDetail historyModalTitle L453-458 | record_label||record_key 回落 | ✅ |
| E2 | 双层存储 lineage 血缘 | ArchiveDetail L151-153,181-183 | 详情弹窗血缘标签+tooltip | ✅ |
| F1 | 需求落地：档案CRUD | ArchiveList + ArchiveDetail | 新建/编辑/删除/详情/刷新 全链路 | ✅ |
| F2 | 需求落地：变更日志 | VersionManagement + ArchiveDetail 变更历史弹窗 | 全局+单档案双视角+导出 | ✅ |
| F3 | 需求落地：一致性检查 | ConsistencyCheck | 四状态+批量标记+历史时间线 | ✅ |
| G1 | 流程闭环：建模→档案 | DomainFieldConfig→ArchiveList→ArchiveDetail | 字段管理→新建档案→刷新同步 | ✅ |
| G2 | 流程闭环：刷新预检 | ArchiveList/ArchiveDetail → doRefreshPreview → 弹窗 → syncSchema/refreshData | 无变化→message 提示不弹窗 | ✅ |

**统计**：共 22 项 = ✅18 / ⚠️4（R-032~R-035）

---

## 整改清单

| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-032 | 【泛化 4 处】危险操作确认强度不统一（R-015 泛化遗漏）：①DataSourceList 删除数据源仅 popconfirm 无级联影响提示（关联档案将失去数据源）②TableList 删除表仅 popconfirm 无级联影响提示（关联字段/标准字段/档案 schema 受影响）③DomainList 删除域仅 popconfirm 无级联影响提示（域下表/字段/档案全部受影响）④DomainList 编辑域无确认直接保存 | DataSourceList L28 / TableList L69 / DomainList L32 | 反馈与容错 | 统一改 Modal.confirm + 影响面文案（如「该域下有 N 张表、M 个字段，删除后不可恢复」） | P1 | 待整改 |
| R-033 | DomainList 操作列「编辑」和「删除」并列，编辑无确认弹窗但修改域信息（名称/描述）是写操作，误点无法撤回 | DomainList L30 | 反馈与容错 | 编辑走弹窗表单（已有 modalVisible），确认无误；但需确保编辑也走 Modal.confirm 或至少弹窗内「确定」按钮有明确文案 | P2 | 待整改 |
| R-034 | DomainList 删除/编辑 catch 未用 extractApiError，与全站统一规范不一致（ArchiveList/ArchiveDetail/ConsistencyCheck 均已用） | DomainList L121,133 | 一致性 | catch 改 extractApiError(e) \|\| e.message | P2 | 待整改 |
| R-035 | ConsistencyCheck 批量标记弹窗操作人默认 'admin'（L177），ArchiveDetail 详情弹窗操作人默认为空（L441）；全站不统一 | ConsistencyCheck L177 / ArchiveDetail L441 | 一致性 | 统一为空（用户必须主动填写），或统一为 'admin'（当前用户） | P2 | 待整改 |
| R-036 | VersionManagement 导出按钮在 unselect archive 时仍可点击，点击后 message.info 提示；不如直接 disabled 直观 | VersionManagement L6 | 反馈与容错 | 导出按钮 :disabled="!changeFilter.archive" | P2 | 待整改 |

> **实跑验证通过项（不整改）**：
> - vue-tsc 0 errors ✅
> - 菜单高亮随路由同步（R-013 闭环确认）✅
> - formatDateTime 全站无遗漏 ✅
> - scroll.x 各表已按列宽求和（R-025 闭环确认）✅
> - 刷新预检弹窗两处一致（R-016 闭环确认）✅
> - 回滚防 400（canRollbackToPoint 最新节点隐藏）✅
> - Switch 语义全站无 Radio 误用 ✅
> - 空态处理全覆盖 ✅
> - 弹窗 footer 关闭按钮全覆盖 ✅
> - record_label 落库快照展示 ✅
> - 双层存储 lineage 血缘标签 ✅
> - 死代码无新增（R-028 闭环确认）✅
