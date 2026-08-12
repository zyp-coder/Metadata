# 整改清单
## 第一百一十八轮 全站弹窗/抽屉三维选型巡检（2026-08-05）
> 范围：全站 87 个容器（modal 29 / drawer 10 / popconfirm 10 / 命令式 38）按 popup-layout-spec 三维选型（风险优先>频率优先>类型×内容量）逐页判定。方法：子代理全量扫描源码（内容规模逐个数出）+ 主线程三维裁决 + 用户拍板全部派单。常驻抽屉：全站无强制场景（API 管理页为未来候选，暂不动，留活口）。发现 4 项 P1 + 4 项 P2。
| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-055 | 记录启停开关无任何确认：停用/启用记录属覆盖类危险操作，全站唯一无防护危险点 | ArchiveDetail.vue doToggleStatus（L1163 附近） | 反馈与容错（风险优先） | 补 Modal.confirm 二次确认，停用文案与刷新预检同口径（波及：源侧已删记录停用/值覆盖）。第123轮已整改：Modal.confirm 二次确认（停用=danger，开关受控绑定取消回弹），浏览器实测 PASS | P1 | ✅ 已闭环 |
| R-056 | 记录详情 1400px modal：高频入口+重表单（元信息+全 schema 字段+变更预览表），整屏遮挡无法参照记录列表逐条浏览 | ArchiveDetail.vue detailModal | 尺寸与层叠（频率优先） | modal → 大抽屉（约 1100px，与项目既有抽屉档一致），保留暂存修改/变更预览能力。第124轮已整改：a-drawer 1100px 右侧滑入+关闭/暂存修改移入 footer 固定底栏，暂存编辑/变更预览/分组网格全保留，浏览器实测 6/6 PASS | P1 | ✅ 已闭环 |
| R-057 | 变更历史 860px modal 两份同构拷贝：timeline 长内容竖向滚动更适合抽屉；ArchiveDetail 与 VersionManagement 各一份 | ArchiveDetail.vue historyModal / VersionManagement.vue 同构弹窗 | 尺寸与层叠+一致性（泛化铁律） | 两处同改抽屉，并收敛为单组件复用（防两份各自演化，同 R-048/R-049 分叉教训）。第125轮已整改：新建 ChangeHistoryDrawer.vue 单组件（900px 抽屉+时间线+双粒度回滚 dropdown，enableRollback 区分 AD 带回滚/VM 只读），两处同构弹窗删除（AD 附带清理 121 行死预载），浏览器实测 8 项全 PASS | P1 | ✅ 已闭环 |
| R-058 | 删除角色用 popconfirm 气泡：不可逆删除防护降级，全站其他删除（域/表/档案/映射）均为 Modal.confirm | RoleManagement.vue 操作列删除 | 反馈与容错（风险优先+一致性） | popconfirm → Modal.confirm，与全站删除防护对齐。第123轮已整改：confirmDelete + Modal.confirm（danger），浏览器实测 PASS | P1 | ✅ 已闭环 |
| R-059 | 表列表「字段管理」近全屏 modal（calc(100vw−80px)，源码注释原话"近全屏，最大化展示空间"）：高频+重+无法参照表列表；用户已拍板改大抽屉 | TableList.vue fieldModal（L89-93，入口 L82 操作列+路由参数 openFieldModal 自动打开） | 尺寸与层叠（频率优先） | modal → 大抽屉（60-70vw）：双 Tab（字段表/数据预览）保留，预览表列多时配 scroll.x；两个入口逻辑同步改。第127轮已整改：a-drawer 65vw（1257 视口实测精确 65vw）+关闭固定底栏，双 Tab/主键标识区/预览表全保留，两入口不动（openFieldModal 函数与路由参数零改动）；浏览器实测 6/6 PASS | P2 | ✅ 已闭环 |
| R-060 | 版本管理记录详情 900px modal：全字段只读重展示 | VersionManagement.vue 记录详情弹窗 | 尺寸与层叠 | modal → 抽屉（与 R-056 同档位风格） | P2 | ⏳ 待整改 |
| R-061 | 新建/重命名分组用浏览器原生 window.prompt()：无法校验、体验粗糙、与全站容器风格断裂 | DomainFieldConfig.vue L853-865 | 一致性与冲突 | 改小弹窗表单（Modal 480，名称必填校验）。第127轮已整改：新建/重命名共用 480px a-modal 表单（标题随模式+父级名动态；空名禁用确认；重命名预填原名、未改动静默关闭零请求）；踩坑：antdv 4.x 声明式 a-modal @ok 不消费返回值（handleOk 仅 emit，Promise 自动关闭仅 Modal.confirm 有）→ v2 在请求 .then 内显式置 open=false、catch 不重抛防 console unhandled rejection；回归实测 v2 7/7 PASS（含超长名 400 失败保持打开），测后清理恢复域 11 原 7 分组 | P2 | ✅ 已闭环 |
| R-062 | 刷新预检弹窗两份拷贝（ArchiveList 与 ArchiveDetail 几乎同构）：同一事实两处存放，已出过 warnings 缺失分叉（R-048/R-049） | ArchiveList.vue / ArchiveDetail.vue 刷新预检 | 一致性（防分叉） | 收敛为单组件（schema 变化+数据试算+波及告警+warnings 区），两处引用。第126轮已整改：新建 RefreshPreviewModal.vue 单组件（760px modal，组件管展示+确认意图，执行逻辑留父组件），两处同构弹窗删除（86+88 行），AL stats 文案顺带泛化（复活文案+同步/刷新区分），浏览器实测 6 项 PASS（含注入建模变化触发 schema 弹窗验证） | P2 | ✅ 已闭环 |
> 保留的例外（有意不改，依据已记录）：公式编辑器 1680 modal / 新建表 1152 modal（横向工作台布局，抽屉竖向流不适用，再长大升独立页）；密钥明文 520 modal（一次性敏感信息强制打断便于复制，特性非缺陷）；试算 800 modal（结果表横向列多）；API 管理页全部抽屉选型为三维规范样板。
## 第一百一十七轮 v19 API 管理交付验收（2026-08-05）
> 范围：v19 REQ-005 API 管理（API 管理页双 Tab+密钥抽屉+文档抽屉+日志抽屉）。发现 1 项 P2。
| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-054 | 密钥表 scroll.x=1100 < 列宽和 1230，溢出 130px | ApiKeyTab.vue 密钥表 | 微观-尺寸数据量匹配 | scroll.x 改为 1300 | P2 | ✅ 已闭环 |
---
## 第一百零九轮 全站巡检 6 项（2026-08-04）
> 范围：全站 16 页面源码巡检 + vue-tsc 0 errors + 后端 45 tests PASS。发现 6 项 P2 待整改。
| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-048 | ArchiveDetail 刷新预检弹窗缺少 warnings 展示区（ArchiveList L118-120 有，ArchiveDetail 没有） | ArchiveDetail.vue L372-375 | 一致性与冲突 | 补 warnings alert，与 ArchiveList 一致 | P2 | ✅ 已闭环 |
| R-049 | confirmRefresh 路径不显示 warnings 和一致性提醒（ArchiveList + ArchiveDetail 两处） | ArchiveList.vue confirmRefresh / ArchiveDetail.vue confirmRefresh | 反馈与容错 | 补 warnings 展示 + showConsistencyWarning 调用 | P2 | ✅ 已闭环 |
| R-050 | DataSourceList 表格缺少 scroll.x | DataSourceList.vue L8 | 尺寸与数据量匹配 | 补 :scroll="{ x: 800 }" | P2 | ✅ 已闭环 |
| R-051 | DomainChangeOverview 表格缺少 scroll.x | DomainChangeOverview.vue L7 | 尺寸与数据量匹配 | 补 :scroll="{ x: 750 }" | P2 | ✅ 已闭环 |
| R-052 | ConsistencyCheck 失效规则删除操作使用 popconfirm | ConsistencyCheck.vue L168 | 反馈与容错 | 删除改 Modal.confirm | P2 | ✅ 已闭环 |
| R-053 | 插件卸载 popconfirm 泛化（TechFunctions + FormulaEditor 2 处） | TechFunctions L75 / FormulaEditor L266 | 一致性与冲突 | 改 Modal.confirm | P2 | ✅ 已闭环 |
---
## 第九十五轮 测试报告 8 项修复（2026-08-03）
> 范围：测试报告 8 项问题（5 页面：modeling tables/mappings/fields + archive 列表/详情）。方法：源码调查 + AskUserQuestion 2 轮确认方向。
| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| T-001 | 「释放到概念层」和「状态」两列信息冲突，用户建议合并为一列「模型字段」 | TableList.vue 字段管理弹窗 | 信息架构 | 合并两列为「模型字段」列（单个开关同时控制释放+启停） | P1 | ✅ 已闭环 |
| T-002 | 关系管理页缺少「AI建立关系」按钮 | DomainFieldMapping.vue L21 | 功能完整性 | 工具栏加「🤖 AI建立关系」按钮（后端 API 待实现，前端占位） | P2 | ✅ 已闭环 |
| T-003 | 字段分组标题栏三点下拉图标太隐形 | DomainFieldConfig.vue L215 | 可见性 | MoreOutlined → EditOutlined（笔记本编辑图标） | P2 | ✅ 已闭环 |
| T-004 | 档案列表操作列缺少「编辑」入口 | ArchiveList.vue L23-30 | 交互一致性 | 操作列加回「编辑」链接，名称列改纯文本（撤回 R-041 名称点击） | P1 | ✅ 已闭环 |
| T-005 | 档案详情记录列表未占满屏幕高度 | ArchiveDetail.vue L70 | 布局 | 表格 scroll.y 改 calc(100vh - 300px) + 字段导航高度 calc(100vh - 260px) | P2 | ✅ 已闭环 |
| T-006 | 档案详情另一列表也未占满屏幕 | ArchiveDetail.vue L48 | 布局 | 随 T-005 一并修复（字段导航+记录表同时自适应） | P2 | ✅ 已闭环 |
| T-007 | 详情弹窗内的回滚时间线不应有回滚按钮 | ArchiveDetail.vue L205-239 | 交互合理性 | 删除详情弹窗内「历史回滚」折叠面板，提示文案加「如需回滚请查看变更历史」 | P1 | ✅ 已闭环 |
| T-008 | 变更历史弹窗一条数据放两个回滚按钮太丑 | ArchiveDetail.vue L273-282 | 视觉简洁 | 两按钮合并为「回滚 ▾」下拉菜单（回滚此条/回滚到此） | P2 | ✅ 已闭环 |
---
## 第九十四轮 交互流程与按钮名称巡检（2026-08-03）
> 范围：全站交互流程合理性 + 按钮名称简洁性 + 流程命名统一性。方法：用户反馈驱动（字段分组树按钮太多）→ 全站 14 页交互模式审计。AskUserQuestion 确认 R-040~R-044 整改、R-045 伪需求。
| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-040 | 字段分组树交互按钮过多：每个树节点挂 ➕✏️🗑️ 三个图标按钮，视觉噪音大、操作密度高。应改为「点名称编辑 + 工具栏下拉菜单管理」模式 | DomainFieldConfig 字段分组 Tab | 交互密度 | 去 3 个图标按钮→名称点击触发重命名 + 面板头部 a-dropdown 下拉菜单（新建/重命名/删除） | P1 | ✅ 已闭环 |
| R-041 | 操作列「编辑」按钮冗余：名称列纯文本不可点击，用户必须找操作列「编辑」按钮才能进入编辑。应改为名称可点击 | DomainList/ArchiveList/ApiManagement | 交互一致性 | 名称列改 `<a>` 可点击链接进入编辑/详情；操作列删「编辑」按钮+列宽收窄 | P1 | ✅ 已闭环 |
| R-042 | settings 页面 h2 标题带「系统设置 — 」前缀，与侧栏菜单名重复（侧栏已显示「系统设置」） | AIConfig/TechFunctions/DataSourceList | 命名简洁 | 去掉「系统设置 — 」前缀，h2 直接显示页面名 | P2 | ✅ 已闭环 |
| R-043 | Modal.confirm 文案不统一：部分用「确定」部分用「确认」，全站应统一为「确认」 | TableList（3 处）+ 已随 R-032 修 3 文件 | 一致性 | TableList「确定」→「确认」（title/content/okText） | P2 | ✅ 已闭环 |
| R-044 | catch 块冗余 `\|\| e.message`：extractApiError 已能完整解析错误，后续 `\|\| e.message` 是冗余回退。TableList 11 处 + DomainFieldMapping 1 处 + ArchiveDetail 3 处 | 3 文件 15 处 | 代码一致性 | 删除所有 `\|\| e.message` 冗余回退 | P2 | ✅ 已闭环 |
| R-045 | 【伪需求】步骤条顺序调整（用户后澄清：关系管理是组合字段的前提，当前顺序正确） | DomainStageNav | — | 不改 | — | ❌ 伪需求 |
---
## 第九十三轮 全站 14 页交付验收巡检（2026-08-03）
> 范围：全站 14 页面（modeling 4 + archive 6 + settings 3 + MainLayout）。方法：源码量化巡检 + vue-tsc 0 errors。未实跑浏览器。
> 本轮为第九十二轮后再次全站巡检，重点核查 R-032（危险操作 Modal.confirm 泛化）和 extractApiError 一致性执行情况。
| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-037 | 【泛化 4 处】popconfirm 泛化遗漏（R-032 未覆盖）：①ApiManagement L57 删除 API 仍用 popconfirm ②DomainFieldMapping L57 删除映射仍用 popconfirm ③DomainFieldConfig L244 删除分组用 popconfirm ④DomainFieldConfig L129 释放组合字段用 popconfirm。均应改 Modal.confirm + 影响面文案 | ApiManagement / DomainFieldMapping / DomainFieldConfig | 反馈与容错 | 改 Modal.confirm + 级联影响文案 | P2 | ✅ 已闭环 |
| R-038 | 【泛化 10 文件 ≈25 处 catch】extractApiError 一致性未全站覆盖：4 文件未导入（ApiManagement 6处/AIConfig 3处/DataSourceList 3处/VersionManagement 3处+DomainChangeOverview 1处）+ 5 文件已导入但部分 catch 仍用 e.message（ArchiveDetail 2处/ArchiveList 2处/DomainFieldMapping 2处/ConsistencyCheck 已用extractApiError但L307操作人回退'admin'） | 10 文件 | 一致性 | 统一导入 extractApiError + 替换所有 e.message 为 extractApiError(e) \|\| '兖底文案' | P2 | ✅ 已闭环 |
| R-039 | ConsistencyCheck L307 操作人回退 'admin'：reviewOperator.value 为空时回退到硬编码 'admin'，部分抵消 R-035 修复效果（R-035 已将默认值改为空，但此处回退使空值失效） | ConsistencyCheck L307 | 一致性 | 删除 `\|\| 'admin'` 回退，空值直接传空串或 null | P2 | ✅ 已闭环 |
---
## 第九十二轮 全站 14 页交付验收巡检（2026-08-03）
> 范围：全站 14 页面（modeling 4 + archive 6 + settings 3 + MainLayout）。方法：源码量化巡检 + vue-tsc 0 errors。未实跑浏览器。
| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-032 | 【泛化 3 处】危险操作确认强度不统一（R-015 泛化遗漏）：①DataSourceList 删除数据源仅 popconfirm ②TableList 删除表仅 popconfirm ③DomainList 删除域仅 popconfirm。已全部改 Modal.confirm + 级联影响文案 | DataSourceList / TableList / DomainList | 反馈与容错 | — | P1 | ✅ 已闭环 |
| R-033 | DomainList 删除已改 Modal.confirm（随 R-032 一并修复） | DomainList L30 | 反馈与容错 | — | P2 | ✅ 已闭环（随 R-032） |
| R-034 | DomainList 删除/编辑 catch 已补 extractApiError | DomainList L121,133 | 一致性 | — | P2 | ✅ 已闭环 |
| R-035 | ConsistencyCheck 操作人默认值已改为空（与 ArchiveDetail 统一） | ConsistencyCheck L177 | 一致性 | — | P2 | ✅ 已闭环 |
| R-036 | VersionManagement 导出按钮已有 v-if 守护（未选档案时不渲染），无需额外 disabled | VersionManagement L6 | 反馈与容错 | — | P2 | ✅ 已闭环（v-if 已覆盖） |
---
## 第九十轮 全站 17 页交付验收巡检（2026-07-25）
> 范围：modeling 8 页 + archive 6 页 + settings 3 页 + MainLayout + 4 弹窗组件。方法：源码量化推理（两路 subagent）+ 浏览器实跑两轮（含复核）。容器基准：1920 屏、侧栏 220px、内容区可用 ≈1620px。
> 实跑已确认项：v17.1 变更历史弹窗正常（标题带业务对象✓最新节点隐藏「回滚到此」✓）；记录表 No data 为时序误报不复现；settings 三页控制台 0 error。
| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-011 | 记录表「更新时间」列直出原始 ISO 串（实跑实测 `2026-07-31T15:05:22.658631+08:00`）32 字符溢出 170px 列宽，与全站 formatDateTime 不一致（全站唯一漏网点） | ArchiveDetail.vue L624 updated_at 列 | 一致性/字段呈现 | 加 customRender: formatDateTime | P1 | ✅ 已闭环 |
| R-012 | 记录表 scroll.x 在分组表头下严重低估：dynamicColumnsTotalWidth 只累加顶层列（分组列无 width 按 100 计），10 字段 2 分组实需 2160px 只算出 760px；实跑当前数据下对位正常，但分组/字段增多后 fixed 列对位风险高 | ArchiveDetail.vue L630-632, L574-597 | 尺寸量化 | 递归累加叶子列宽 | P1 | ✅ 已闭环 |
| R-013 | 菜单选中态不随路由同步：selectedKeys 仅点击时更新，刷新/程序化导航（管理记录→/archive/:id、域概览→/archive/versions）后菜单零高亮（实跑两页均复现） | MainLayout.vue L44, L94-96 | 反馈与容错 | watch(route.path) 映射最近菜单 key | P1 | ✅ 已闭环 |
| R-014 | 「变更与版本」命名链断裂：菜单文案≠两路由同名 meta.title≠页面 h2（变更日志/域概览）≠组件名 VersionManagement，且页内无任何版本内容；面包屑两页完全同名无法区分层级 | MainLayout L62、router L30-31、DomainChangeOverview L4、VersionManagement L4 | 信息架构/一致性 | 统一改「变更日志」，versions 页 title 加「— 明细」；组件更名 ChangeLogList | P1 | ✅ 已闭环 |
| R-015 | 【泛化】危险操作确认强度不统一：①API 停用无任何确认（调用方立即失败）②数据源删除仅 popconfirm 无引用影响提示③回滚 okType 三处 danger/primary 混用（VersionManagement L168、ArchiveDetail L945 vs L999）④TableList 删表无级联影响提示 | ApiManagement L53、DataSourceList L28、VersionManagement、ArchiveDetail、TableList L68 | 反馈与容错 | 停用/删除改 Modal.confirm+影响面文案；回滚统一 danger | P1 | ✅ 已闭环 |
| R-016 | 刷新预检弹窗两处重复实现且已分叉：ArchiveList 版缺 changes_sample 字段 diff 样本表，同一动作两入口信息量不对等；预检标题不带档案名 | ArchiveList L38-83 vs ArchiveDetail L366-389 | 一致性 | 抽共享组件 RefreshPreviewModal，标题带档案名 | P1 | ✅ 已闭环 |
| R-017 | 【泛化2处】a-empty 使用不存在的 #extra 插槽，空态操作按钮不渲染（实跑 FAIL 确认：分类页无「开始AI分析」按钮）；另异常路由空态与后端错误文案叠加展示样式混乱 | DomainFieldConfig L5-9、FieldClassification L11-17 | 反馈/空态 | 改默认插槽；异常路由给独立错误态 | P1 | ✅ 已闭环 |
| R-018 | 字段管理页左右配比失衡三问题同源：左栏固定 500px（分类项自然宽≈120px 留白≈350px），右栏仅剩 ≈1072px；属性表列宽合计 1130px 溢出且无 scroll.x；组合字段表弹性列「数据去重内容」仅得 ≈32px（自然宽≥180px） | DomainFieldConfig L1473、L1024-1036、L580-590 | 容器vs数据量 | 左栏 500→260-280px + 两表补 scroll.x | P1 | ✅ 已闭环 |
| R-019 | FormulaEditor「保存并试算」链路死链：handleSaveAndTrial 26 行从未挂按钮（实跑确认 footer 仅 取消/保存），父页 @save-and-trial 监听空转 | FormulaEditor L903-928、DomainFieldConfig L452 | 死代码/功能 | 补按钮或删函数+监听 | P1 | ✅ 已闭环 |
| R-020 | ER 图两疑点：①全屏后画布仍固定 height:600（容器 calc(100vh-220)，1080 屏底部 ≈260px 空白）②node.on('node:dragend') 非 X6 标准事件，拖拽保存可能从不触发（仅靠 onBeforeUnmount 兆底）；实跑因画布非标准 DOM 未能验证，标注待实跑 | DomainFieldMapping L371、L515-517 | 尺寸/质量 | height 取 clientHeight；改 graph.on('node:moved') | P1 | ✅ 已闭环 |
| R-021 | 编辑映射=先删旧再建新，创建失败时旧映射已删且无回滚，数据丢失风险 | DomainFieldMapping L669-740 | 容错 | 先建后删或后端事务化 | P1 | ✅ 已闭环 |
| R-022 | AI 分类「保存分类方案」仅循环建分组，未将任何字段绑定到分组（空壳保存）；循环逐个 await 无失败回滚 | FieldClassification L175-194 | 质量 | 补字段归属提交；若页面下线（见 R-024）则随之废弃 | P1 | ✅ 已闭环（随 R-024 隔离） |
| R-023 | 「释放成员」popconfirm 文案与后果不符：成员 ≤2 时实际删除整个组合字段，文案仍为「确认释放该成员？」 | DomainFieldConfig L411-413、L1345-1356 | 危险操作 | ≤2 成员时 Modal.confirm 明示「将删除整个组合字段」 | P1 | ✅ 已闭环 |
| R-024 | 旧向导四页孤儿化：FieldConfig/FieldClassification/FieldProperties/FieldMapping 全库无入口仍挂路由，与 DomainFieldConfig 功能重复、交互两套标准（产品决策项） | router L17-20 | 死代码/信息架构 | 确认后下线路由+删页面，或恢复入口 | P1 | ✅ 已隔离（移 legacy/ 摘路由，待用户确认后删） |
| R-025 | 【泛化8处】scroll.x 缺失/失配：缺失—DomainList(1200)、TableList(1478)、ApiManagement(1160)、VersionManagement(1300)、DomainFieldConfig 两表；低估—ArchiveList(1080<1180)；虚高—ConsistencyCheck(1300>≈1100) | 6 页 8 表 | 尺寸量化 | 按列宽求和设值（建议抽工具函数） | P2 | ✅ 已闭环 |
| R-026 | 【泛化】列宽配比失衡：ArchiveDetail 操作列 340 vs 实需 ≈178（fixed 列越宽遮挡越多）、data-cell max-width 120 vs 列宽 160 提前截断且无 tooltip；TableList 操作列 200 vs 100、弹窗注释列 ≈1070px 留白；DataSourceList 操作列 160 vs 89 | 3 页 | 列宽配比 | 按自然宽收窄；max-width 改 140+补 tooltip | P2 | ✅ 已闭环 |
| R-027 | 【泛化3处】footer=null 无底部关闭按钮：变更历史弹窗（与同页详情弹窗自绘关闭不一致）、ApiManagement 查看数据抽屉、TechFunctions 模板弹窗、TableList 字段管理弹窗；另：变更历史 860px 落档位空隙建议收敛 800 | 4 处 | 弹窗规范 | 补 footer 关闭按钮 | P2 | ✅ 已闭环 |
| R-028 | 【泛化 ≈200行】死代码：DomainList openEdit；TableList router/saveComment；DomainFieldConfig 6 批量函数+allFlatGroups；DomainFieldMapping 缩放工具套件；FormulaEditor ok-text；ArchiveDetail typeColor/getFieldLabel/buildErrText | 6 文件 | 死代码 | 删除（删前 grep 零引用） | P2 | ✅ 已闭环 |
| R-029 | 【泛化】弹窗标题不带业务对象：DomainList 编辑域、FieldClassification 重命名分组、ArchiveList 刷新预检（已并入 R-016） | 2 页 | 归属与主体 | 标题补「- 编码 (名称)」 | P2 | ✅ 已闭环 |
| R-030 | 【泛化】反馈容错杂项：静默吞错 catch{}×8（DomainFieldConfig×6 等）；表格 loading 缺绑定（DomainFieldConfig 5 表/FieldConfig/FieldProperties）；TechFunctions 多行错误 message 不换行；AIConfig 保存无必填校验；ConsistencyCheck 搜索清空不重查/lastCheck 不持久；DomainChangeOverview 双重空态；DataSourceList 密码留空无提示/切类型覆盖端口；VersionManagement 禁用回滚无 tooltip | 8 页 | 反馈与容错 | 逐项小修（合并一次整改） | P2 | ✅ 已闭环 |
| R-031 | 【泛化】一致性杂项：操作人默认值 admin/管理员混用；原生 prompt() vs a-modal（分组新建/重命名）；数字列未右对齐（4 页）；大弹窗固定 px 不用 calc 档位（新建表 1152/FormulaEditor 1680/详情 1400，窄屏贴边）；DataSourceList 页标题与菜单不一致；FieldMapping 弹窗 520 vs 同功能 640；DomainStageNav 完成态数字未隐藏（选择器失效）；FieldProperties 枚举列 300px 内嵌编辑器 | 9 页 | 一致性 | 逐项小修（合并一次整改） | P2 | ✅ 已闭环 |
> **实跑验证通过项（不整改）**：v17.1 变更历史弹窗全链路✓；回滚最新节点防 400 隐藏✓；VersionManagement 操作列 140px 量化够用（实需 ≈117px）✓；控件语义全站 Switch 无 Radio 误用✓；tag 色板跨页一致✓；表格字段取舍无「数据库视图」✓；settings 三页 0 控制台错误✓。
> **旧清单遗留**：R-004（DomainList 操作列）本轮复核为部分完成（平铺已落实、fixed:right+scroll.x 未落实），已并入 R-025 统一收口，R-004 标记关闭。
---
## 历史清单（第六十六轮及之前）
| 编号 | 问题 | 页面/元素 | 评定维度 | 建议 | 严重度 | 状态 |
|------|------|----------|---------|------|--------|------|
| R-001 | 主键列 160px + ellipsis 截断关键信息。联合主键（如 STORE_NO + BUSINESS_DATE）无法完整展示，用户需 hover tooltip 才能看全，降低信息获取效率 | TableList.vue — `primary_keys` 列 | 宏观-业务流程适配 | 列宽增至 200px | P2 | ✅ 已闭环 |
| R-002 | 档案记录表格动态列仅展示前 6 个 schema 字段（共 29 个），大部分业务数据（如 T2/T5 表字段）在列表视图中不可见，用户需点击详情才能查看 | ArchiveDetail.vue — `dynamicColumns` | 微观-尺寸与数据量匹配 | DATA_COLUMN_MAX 从 6 增至 10（总宽增至 ~2040px，配合 scroll.x 可接受） | P2 | ✅ 已闭环 |
| R-003 | **【已推翻→重新整改】** 操作列 6 个链接按钮竖排换行。初次采用下拉方案（管理记录+更多▾），但用户测试反馈明确不要下拉、要平铺全部按钮 | ArchiveList.vue — 操作列 | 微观-尺寸与数据量匹配 | 最终方案（第十轮）：操作列改回平铺 5 链接，fixed:right+nowrap width 380，其他列压缩+ellipsis，scroll.x=1080 | P1 | ✅ 已闭环（平铺终稿） |
| R-004 | DomainList 操作列 5 个按钮（380px）、多页面操作列按钮偏多，存在与 R-003 同类的压缩/拥挤风险 | DomainList.vue — 操作列 | 微观-尺寸与数据量匹配 | 【方案修正】不再收下拉（用户偏好平铺），改用 fixed:right+nowrap 固定操作列+压缩数据列 | P2 | ✅ 已关闭（平铺已落实；fixed/scroll.x 并入 R-025） |
| R-005 | 弹窗标题仅「枚举试算」，未标识业务对象（规范要求 `对象类型 - 编码 (名称)`）。【泛化】FormulaEditor 编辑态标题「编辑计算字段公式」同样不带对象 | TrialCalculation.vue L4；FormulaEditor.vue L4 | 微观-归属与主体 | 标题改 `枚举试算 - {code} ({name})`；FormulaEditor 编辑态同格式 | P1 | ✅ 已闭环 |
| R-006 | 参数表「参数字段」列与结果表表头直接显示技术 ref（实跑：表头 `IMP_零售_门店_闭店信息填报.D_CLOSE_DATE` 占 328px），无中文名；与 FormulaEditor 已定稿的「字段显示中文名」规范不一致。组件已拉 availableReferences 建 fieldMap（L137）却未使用（死代码即证据） | TrialCalculation.vue 参数表 paramColumns + 结果表 resultColumns | 微观-一致性与冲突 | 用 fieldMap 的 display_name 渲染「中文名（技术 ref 副标/小字）」 | P1 | ✅ 已闭环（注：复检时 MD_STATUS 字段仍显示原始 ref，经 API 核查属脏数据——该字段表达式引用了域内不存在的「门店表」，displayName 回退到原始 ref 是预期保护行为，代码正确） |
| R-007 | 容错/空态缺失：①试算返回 0 行时结果区不渲染、无任何提示（静默）；②无参数字段时参数表空白无引导；③自动枚举按钮无 loading 反馈（:loading 仅绑执行试算） | TrialCalculation.vue L45-77 | 微观-反馈与容错 | 0 行时显示 a-empty/提示条；参数空态提示；两按钮均绑 loading | P1 | ✅ 已闭环 |
| R-008 | 自动枚举后「测试值」select 未回填（实跑：tag 数 0），回填逻辑 L170-176 存疑；另有死代码 firstInputs（L171） | TrialCalculation.vue autoEnumerate | 微观-反馈与容错 | 排查 inputs key 与 row.ref 匹配；空值过滤 null/空串；清死代码 | P2 | ✅ 已闭环 |
| R-009 | header 表达式单行原始文本，未复用 FormulaEditor 已定稿的代码编辑器风格格式化；长表达式可读性差 | TrialCalculation.vue L16 trial-expression | 微观-一致性与冲突 | 复用 formatExpressionText（抽到 utils/formula.ts）+ pre 多行展示 | P2 | ✅ 已闭环 |
| R-010 | 结果表缺横向滚动保护：列宽 120×N+150，参数 ≥5 时超出 752px 可用宽（量化：5×120+150=750 临界，6 参数即溢出）；另 footer=null 仅右上 X 可关 | TrialCalculation.vue L60-67 | 微观-尺寸与数据量匹配 | 加 :scroll="{ x: 'max-content', y: 300 }"；底部加「关闭」按钮 | P2 | ✅ 已闭环 |
> **严重度说明**：R-003（P1）初次下拉方案已被用户推翻，改为平铺终稿（fixed:right+nowrap）并实跑验证闭环；R-004 方案同步修正为平铺固定列（不再收下拉），待整改。R-001/R-002 已闭环。R-005~R-010 为第六十六轮「枚举试算弹窗 uxqa」新增（用户反馈「这个页面就没怎么设计啊」，实跑+源码双证据），用户确认全部 6 项一次整改，TrialCalculation.vue 整体重写（292 行）+ 新建 utils/formula.ts 共享格式化函数，vue-tsc 0 errors + Browser 二次复检 7/8 达标（唯一疑点经 API 核查为脏数据非代码缺陷），全部闭环。
>
> **泛化检查（铁律6，第六十六轮补充）**：
> - R-005 标题不带业务对象 → 同类：FormulaEditor 编辑态（已并入 R-005）；「合并为组合字段」弹窗无特定单对象、distinct 抽屉标题动态已带对象，不在此列
> - R-006 技术 ref 无中文名 → 同类两处（参数表列 + 结果表表头）已合并一项；FormulaEditor 侧栏已修同类（display_name）可直接复用后端字段
>
> **泛化检查（铁律6）**：
> - R-001：仅 TableList 有主键列，无同类对象
> - R-002：仅 ArchiveDetail 有动态列，无同类对象
> - R-003：操作列按钮过多导致压缩换行 → 同类对象为 DomainList（R-004），需一并收敛
>
> **本轮实跑验证通过项（不整改）**：
> - #1 Tab 深链 `?tab=versions` / `?tab=apis` 跳转正常，「← 返回档案记录」按钮就位 ✅
> - #2 API 配置抽屉加宽至 900px，暴露字段区 3 列布局、分组清晰、无拥挤 ✅
> - 版本历史 Tab 显示引导提示（per-record 架构限制，符合预期）✅
---
## 漏检复盘（2026-08-05，第一百一十轮，用户测试报告暴露）
> 背景：用户报告 /modeling/domains 操作列「还是换行了」+ /archive 按钮名过长，两项此前 uxqa 均未检出。用户确认仅复盘、不补规则。已修，见 debug-diary-modeling BUG-2026-0805-01。
| # | 漏检点 | 根因 |
|---|--------|------|
| 1 | DomainList 操作列换行 | R-004 闭环声称「fixed:right+nowrap 已落实」但 nowrap 从未落码（闭环验收与代码实情脱节）；第 109 轮全站巡检 B2 操作列抽检只覆盖 ArchiveList/VersionManagement/ApiManagement，漏 DomainList，且目测「宽度充裕」未量化实算（实需 281px > 可用 248px） |
| 2 | /archive 按钮名过长（一致性检查/从数据源同步） | A9 命名精简检查项存在但未覆盖操作列文案（只提「按钮 2-4 字」无操作列专项，且未要求全站枚举操作列逐列核对） |
> 教训（记录备查）：闭环项必须 grep 代码证据确认落地，不得凭上一轮结论；B2 列宽检查应覆盖全部列表页并量化实算。
> **改向补记（同轮稍后，用户改向「那你加上吧」）**：两条补强已写入 uxqa 方法论——① frontend-delivery-checklist B2 增硬约束：全站所有含操作列表格禁抽样 + 必须量化实算（禁目测）+ 闭环复检必须 grep 代码证据；② A9 增「操作列按钮/链接文案专项」：≤2 字动词、对象来源不进按钮名、全站枚举逐列核对；popup-layout-spec 命名节同步增「操作列链接/按钮（最严）」条目。另核实：A9/B2/B8 检查项本就存在，真实缺口是措辞容许抽样/目测 + A9 未覆盖操作列文案，非缺项。
