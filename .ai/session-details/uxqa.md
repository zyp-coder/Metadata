# 操作详情 — uxqa 模块（倒序，最新在前）

> 由 rule §3 双层留痕追加；检索方式：按「第N轮」或功能标签 grep。

### 第一百零九轮（2026-08-05）标签：全站巡检、warnings展示、scroll.x、popconfirm

- **操作**：2026-08-05 — 第一百零九轮：UXQA 全站巡检（16 页面 + 2 弹窗组件），vue-tsc 0 errors + 后端 45 tests PASS。发现 6 项 P2（R-048~R-053）并全部闭环：①R-048 ArchiveDetail 预检弹窗补 warnings 展示；②R-049 confirmRefresh 路径补 warnings/一致性提醒；③R-050/R-051 DataSourceList/DomainChangeOverview 补 scroll.x；④R-052 ConsistencyCheck 失效规则删除改 Modal.confirm；⑤R-053 插件卸载改 Modal.confirm。（从 session.md 最近 3 轮下沉补登）

### 第九十五轮（2026-08-03）标签：测试报告、列合并、AI按钮、图标、布局、回滚

- **操作**：2026-08-03 — 第九十五轮：测试报告 8 项修复（5 页面：modeling tables/mappings/fields + archive 列表/详情）。AskUserQuestion 3 轮确认方向（4 次改向：T-001=字段弹窗释放+状态合并非主表列、T-003=加编辑文字、T-004=操作列加编辑+名称不可点、T-007=保留编辑只去回滚按钮）。执行：①T-001 TableList.vue 字段管理弹窗「释放到概念层」+「状态」两列合并为「模型字段」列（120px，单个开关同时控制 release_to_concept+status，新增 toggleModelField 函数）；②T-002 DomainFieldMapping.vue 工具栏加「🤖 AI建立关系」按钮（后端 API 待实现，前端占位 message.info）；③T-003 DomainFieldConfig.vue 字段分组标题栏 EditOutlined + 编辑文字；④T-004 ArchiveList.vue 操作列加回「编辑」链接+名称列改纯文本+列宽调整；⑤T-005+T-006 ArchiveDetail.vue 记录表格 scroll.y calc(100vh-300px) + 外层容器 min-height calc(100vh-180px) + flex 容器 min-height calc(100vh-280px)+align-items:stretch；⑥T-007 详情弹窗删除回滚面板+提示「如需回滚请查看变更历史」；⑦T-008 变更历史弹窗两回滚按钮合并为「回滚 ▾」下拉菜单。修改文件：TableList.vue/DomainFieldMapping.vue/DomainFieldConfig.vue/ArchiveList.vue/ArchiveDetail.vue。验证：vue-tsc 0 errors

### 第九十四轮（2026-08-03）标签：全站、交互流程、按钮名称、交互密度

- **操作**：2026-08-03 — 第九十四轮：UXQA 交互流程巡检（用户反馈「字段分组树按钮太多，应该点名称编辑」→ 全站 14 页交互模式审计）。发现 R-040~R-045（6 项），AskUserQuestion 用户确认 R-040~R-044 整改、R-045 伪需求（步骤顺序正确，关系管理是组合字段前提）。执行：①R-040 DomainFieldConfig 字段分组树交互重做——去 3 个图标按钮→名称点击触发 renameGroup + 面板头部 a-dropdown 下拉菜单（新建/重命名/删除）+ MoreOutlined 图标；②R-041 DomainList/ArchiveList/ApiManagement 名称列改 `<a>` 可点击链接 + 删操作列「编辑」按钮 + 列宽收窄（380→320/340→260/260→200）；③R-042 AIConfig/TechFunctions/DataSourceList h2 去「系统设置 — 」前缀；④R-043 TableList 3 处「确定」→「确认」（title/content/okText）；⑤R-044 TableList 11 处 + DomainFieldMapping 1 处 + ArchiveDetail 3 处冗余 `|| e.message` 清理。修改文件：DomainFieldConfig.vue/DomainList.vue/ArchiveList.vue/ApiManagement.vue/AIConfig.vue/TechFunctions.vue/DataSourceList.vue/TableList.vue/DomainFieldMapping.vue/ArchiveDetail.vue。验证：vue-tsc 0 errors + grep 确认全站 `extractApiError(...) || e.message` 清零

### 第九十三轮（2026-08-03）标签：全站、交付验收、extractApiError、popconfirm

- **操作**：2026-08-03 — 第九十三轮：UXQA 全站 14 页交付验收巡检（modeling 4 + archive 6 + settings 3 + MainLayout）。方法：源码全量读取 + 问题模式 grep + vue-tsc 0 errors。发现 R-037~R-039（3 项 P2），AskUserQuestion 用户确认「P2 全部整改」后分 3 批执行：①R-037 4 处 popconfirm→Modal.confirm+影响面文案（ApiManagement 删除/DomainFieldMapping 删除/DomainFieldConfig 删除分组+释放组合字段）；②R-038 10 文件≈25 处 catch 统一 extractApiError（新增导入 4 文件：ApiManagement/AIConfig/DataSourceList/VersionManagement/DomainChangeOverview，修复已导入但未使用的 5 文件：ArchiveDetail/ArchiveList/DomainFieldMapping，同时清理 ArchiveList 2 处冗余 `|| e.message`）；③R-039 ConsistencyCheck L307 删除 `|| 'admin'` 回退。修改文件：ApiManagement.vue/DomainFieldMapping.vue/DomainFieldConfig.vue/AIConfig.vue/DataSourceList.vue/VersionManagement.vue/DomainChangeOverview.vue/ArchiveDetail.vue/ArchiveList.vue/ConsistencyCheck.vue。验证：vue-tsc 0 errors + grep 确认活跃文件 e.message 清零（仅 legacy/ 残留）

### 第九十二轮（2026-08-03）标签：全站、交付验收、危险操作确认

- **操作**：2026-08-03 — 第九十二轮：UXQA 全站 14 页交付验收巡检（modeling 4 + archive 6 + settings 3 + MainLayout）。方法：源码量化巡检 + vue-tsc 0 errors。checklist 22 项（✅18/⚠️4）。发现 R-032~R-036（5 项 P1×1+P2×4），AskUserQuestion 用户确认「全部整改」后一次执行：①R-032 3 处删除改 Modal.confirm+级联影响文案（DomainList/TableList/DataSourceList）；②R-033 随 R-032 闭环；③R-034 DomainList 补 extractApiError（2 处 catch）；④R-035 ConsistencyCheck 操作人默认 'admin'→''（与 ArchiveDetail 统一）；⑤R-036 确认 v-if 已覆盖无需额外修改。修改文件：DomainList.vue/TableList.vue/DataSourceList.vue/ConsistencyCheck.vue。验证：vue-tsc 0 errors。整改清单 R-032~R-036 全部标记已闭环

### 第六十六轮（2026-07-28）标签：弹窗

- **更早操作**：2026-07-28 — 第六十六轮：uxqa 全流程整改枚举试算弹窗（用户反馈「这个页面就没怎么设计啊 uxqa一下」，XPath body/div[7] 定位 TrialCalculation.vue）。实跑巡检+源码双证据产出整改清单 R-005~R-010（3 P1+3 P2），AskUserQuestion 确认后全部 6 项一次整改：①R-005 标题带业务对象「枚举试算 - code (name)」，泛化同修 FormulaEditor 编辑态标题；②R-006 参数表/结果表表头用 availableReferences 建 displayNameMap 显示中文名（参数列两行：中文名主体+技术 ref 小字）；③R-007 容错三项：无参数空态提示条、0 组合警告条、两按钮均绑 :loading；④R-008 自动枚举回填空值过滤（null/空串）+删死代码 firstInputs；⑤R-009 表达式格式化展示：formatExpressionText 从 FormulaEditor 抽到新建 utils/formula.ts（95 行纯函数）供三处复用，试算弹窗用 pre 多行展示；⑥R-010 结果表加 :scroll="{x:'max-content',y:300}"+底部关闭按钮。TrialCalculation.vue 整体重写为 292 行。事故与修复：对重写后文件做小替换时 SearchReplace 异常（+247 added）将整文件内容重复追加至 537 行两个 template 块导致编译错误，用 Write 整文件覆写恢复；经验：SearchReplace 后若 line changes 远超替换内容行数必须立即查文件总行数。验证：vue-tsc 0 errors；Browser 二次复检 7/8 达标，唯一疑点（MD_STATUS 字段参数表显示原始 ref）经 API 核查定性为脏数据：该字段表达式引用 {门店表.门店名称} 而域 8 的 44 个 available-references 均为 IMP_零售_门店_xxx.CODE 格式不存在「门店表」，displayName 回退原始 ref 是预期保护行为（id=2 store_status 引用的 D_CLOSE_DATE 存在且正确映射「闭店日期」）；建议用户修复或删除测试字段 MD_STATUS。rectification-list.md R-005~R-010 全部标记已闭环

### 第六十三轮（2026-07-27）标签：测试报告

- **更早操作**：2026-07-27 — 第六十三轮：测试报告 3 项（FormulaEditor 对齐+细框）。①「计算表达式」label 行与侧栏 Tab 栏对齐：根因是 dep-list/unused-warn 在左列内部把 label 往下顶；整改：两者上移到 formula-editor-layout 双列布局之外（全宽行，仍紧贴表达式区上方，符合「依赖字段在计算表达式上方」既定规范）+ `.formula-main .formula-label` 固定 height 38px + `.formula-sidebar :deep(.ant-tabs-nav)` 同 38px/margin-bottom 4px；②textarea 与侧栏搜索框/级联对齐：textarea 高度 300→332px（=搜索框24+间距8+级联300，顶底两端平齐）；③预览表格统一细框：5 处 2px 粗线（首行底边/输出列左边×2/body 首行顶边/分组分隔）全改 1px，grep 确认 2px solid 清零。验证：vue-tsc 0 errors；浏览器实跑量化复检：label/Tab 栏 top 差 0px、textarea/搜索框 top 差 0px、textarea/级联 bottom 差 0px、表格 24 单元格无 >1px 边框，截图确认

### 第六十二轮（2026-07-25）标签：-

- **更早操作**：2026-07-25 — 第六十二轮（UXQA 实跑验收）：用户反馈第六十一轮第 2/3/5 项不达标，浏览器实跑截图+JS 量化测量定位三个真根因并整改：①表头第二行颜色—真根因是 `.preview-table th`（类+元素选择器特异性更高）一直压过 `.preview-th-sub` 单类名，之前改的颜色/border 从未生效（实测 border 仍是旧值 #e8e8e8 即证据）；修复：`.preview-th-sub/.preview-th-output/.preview-td-output/.preview-td-error` 全部改用 `.preview-table th.xxx`/`.preview-table td.xxx` 提升特异性，背景改 #fafafa 与第一行完全一致（复检实测两行均 rgb(250,250,250)）；②列宽—真根因是基础样式 `.preview-table th/td` 的 max-width:160px 仍在钳住 td 数据单元格；th/td/th-sub 的 max-width 统一改 400px（容器 overflow:auto 横向滚动兑底）；③label 与输入框分离—实测 label 列 127px 而文字仅 80px，左对齐后留白 47px，根因是固定栅格 label-col span 8；先试 antd 自动宽度（a-select 塌缩到 46px 失败），最终弃用 a-form 栅格改自定义 flex 布局：`.basic-form`（flex gap 24px）+ 三个 `.basic-field`（flex:1，label flex:none + 控件 flex:1），必填星号用 `.basic-field-req` 自行渲染；复检实测：label 间隙 8px、三控件 290/290/298px 等宽撑满。验证：vue-tsc 0 errors + 浏览器三次实跑复检（截图+getComputedStyle 量化）全部达标。经验：scoped 样式改色必须先查同属性的高特异性旧规则，否则改了也不生效
