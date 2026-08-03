# 操作详情 — uxqa 模块（倒序，最新在前）

> 由 rule §3 双层留痕追加；检索方式：按「第N轮」或功能标签 grep。

### 第六十六轮（2026-07-28）标签：弹窗

- **更早操作**：2026-07-28 — 第六十六轮：uxqa 全流程整改枚举试算弹窗（用户反馈「这个页面就没怎么设计啊 uxqa一下」，XPath body/div[7] 定位 TrialCalculation.vue）。实跑巡检+源码双证据产出整改清单 R-005~R-010（3 P1+3 P2），AskUserQuestion 确认后全部 6 项一次整改：①R-005 标题带业务对象「枚举试算 - code (name)」，泛化同修 FormulaEditor 编辑态标题；②R-006 参数表/结果表表头用 availableReferences 建 displayNameMap 显示中文名（参数列两行：中文名主体+技术 ref 小字）；③R-007 容错三项：无参数空态提示条、0 组合警告条、两按钮均绑 :loading；④R-008 自动枚举回填空值过滤（null/空串）+删死代码 firstInputs；⑤R-009 表达式格式化展示：formatExpressionText 从 FormulaEditor 抽到新建 utils/formula.ts（95 行纯函数）供三处复用，试算弹窗用 pre 多行展示；⑥R-010 结果表加 :scroll="{x:'max-content',y:300}"+底部关闭按钮。TrialCalculation.vue 整体重写为 292 行。事故与修复：对重写后文件做小替换时 SearchReplace 异常（+247 added）将整文件内容重复追加至 537 行两个 template 块导致编译错误，用 Write 整文件覆写恢复；经验：SearchReplace 后若 line changes 远超替换内容行数必须立即查文件总行数。验证：vue-tsc 0 errors；Browser 二次复检 7/8 达标，唯一疑点（MD_STATUS 字段参数表显示原始 ref）经 API 核查定性为脏数据：该字段表达式引用 {门店表.门店名称} 而域 8 的 44 个 available-references 均为 IMP_零售_门店_xxx.CODE 格式不存在「门店表」，displayName 回退原始 ref 是预期保护行为（id=2 store_status 引用的 D_CLOSE_DATE 存在且正确映射「闭店日期」）；建议用户修复或删除测试字段 MD_STATUS。rectification-list.md R-005~R-010 全部标记已闭环

### 第六十三轮（2026-07-27）标签：测试报告

- **更早操作**：2026-07-27 — 第六十三轮：测试报告 3 项（FormulaEditor 对齐+细框）。①「计算表达式」label 行与侧栏 Tab 栏对齐：根因是 dep-list/unused-warn 在左列内部把 label 往下顶；整改：两者上移到 formula-editor-layout 双列布局之外（全宽行，仍紧贴表达式区上方，符合「依赖字段在计算表达式上方」既定规范）+ `.formula-main .formula-label` 固定 height 38px + `.formula-sidebar :deep(.ant-tabs-nav)` 同 38px/margin-bottom 4px；②textarea 与侧栏搜索框/级联对齐：textarea 高度 300→332px（=搜索框24+间距8+级联300，顶底两端平齐）；③预览表格统一细框：5 处 2px 粗线（首行底边/输出列左边×2/body 首行顶边/分组分隔）全改 1px，grep 确认 2px solid 清零。验证：vue-tsc 0 errors；浏览器实跑量化复检：label/Tab 栏 top 差 0px、textarea/搜索框 top 差 0px、textarea/级联 bottom 差 0px、表格 24 单元格无 >1px 边框，截图确认

### 第六十二轮（2026-07-25）标签：-

- **更早操作**：2026-07-25 — 第六十二轮（UXQA 实跑验收）：用户反馈第六十一轮第 2/3/5 项不达标，浏览器实跑截图+JS 量化测量定位三个真根因并整改：①表头第二行颜色—真根因是 `.preview-table th`（类+元素选择器特异性更高）一直压过 `.preview-th-sub` 单类名，之前改的颜色/border 从未生效（实测 border 仍是旧值 #e8e8e8 即证据）；修复：`.preview-th-sub/.preview-th-output/.preview-td-output/.preview-td-error` 全部改用 `.preview-table th.xxx`/`.preview-table td.xxx` 提升特异性，背景改 #fafafa 与第一行完全一致（复检实测两行均 rgb(250,250,250)）；②列宽—真根因是基础样式 `.preview-table th/td` 的 max-width:160px 仍在钳住 td 数据单元格；th/td/th-sub 的 max-width 统一改 400px（容器 overflow:auto 横向滚动兑底）；③label 与输入框分离—实测 label 列 127px 而文字仅 80px，左对齐后留白 47px，根因是固定栅格 label-col span 8；先试 antd 自动宽度（a-select 塌缩到 46px 失败），最终弃用 a-form 栅格改自定义 flex 布局：`.basic-form`（flex gap 24px）+ 三个 `.basic-field`（flex:1，label flex:none + 控件 flex:1），必填星号用 `.basic-field-req` 自行渲染；复检实测：label 间隙 8px、三控件 290/290/298px 等宽撑满。验证：vue-tsc 0 errors + 浏览器三次实跑复检（截图+getComputedStyle 量化）全部达标。经验：scoped 样式改色必须先查同属性的高特异性旧规则，否则改了也不生效
