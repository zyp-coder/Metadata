# 早期操作日志归档（2026-07-17 ~ 2026-07-23，轮次编号之前的日期表格）

> 原样搬运自 session.md 操作日志区，历史零删减。

## 操作日志

### 2026-07-27 FormulaEditor 侧栏加技术函数 Tab（第四十九轮）

> 用户反馈「技术函数的编辑入口也应该在新建计算字段里面，切换一下行不行？」。在 FormulaEditor 弹窗侧栏加第三个 Tab「技术函数」，与「字段引用」「函数库」并列。

1. **FormulaEditor.vue 模板**：函数库 Tab 后新增 `<a-tab-pane key="tech_plugins" tab="技术函数">`，内含：
   - 顶部工具栏（下载模板 / 刷新按钮）
   - a-upload 上传按钮（accept='.py'，block 主按钮，loading 态）
   - 安全提示文案（AST 校验 + 同名覆盖说明）
   - 已加载插件列表（plugin-item 卡片：filename + 函数 tag 含 description tooltip + 重载/卸载按钮，卸载带 popconfirm）
2. **FormulaEditor.vue script**：
   - 新增状态：plugins/pluginsLoading/pluginUploading/pluginReloadingMap/pluginUnloadingMap
   - 新增函数：loadPlugins/handlePluginUpload/handlePluginReload/handlePluginUnload/handleDownloadTemplate（Blob 下载为 tech_function_template.py）
   - 上传/重载/卸载成功后自动刷新插件列表 + **同步刷新函数库**（重新拉取 availableFunctions 回写 functions.value，确保切回「函数库」Tab 即时看到新函数）
   - watch(open) 初始化时调用 loadPlugins()
3. **FormulaEditor.vue CSS**：新增 .tech-plugins-toolbar/.tech-plugins-hint/.plugin-list/.plugin-item/.plugin-header/.plugin-filename/.plugin-fns/.plugin-actions
4. **验证**：vue-tsc 0 errors
5. **双入口共存**：FormulaEditor 弹窗 Tab（主入口，写公式时随手切换）+ /settings/tech-functions 独立管理页（补充入口，集中管理）

### 2026-07-27 技术函数插件动态加载（第四十八轮）

> 用户反馈「技术函数实现形式不对，要写好的 .py 脚本可以在前台直接导入」。AskUserQuestion 确认方案B（前端上传 .py + AST安全校验 + 动态加载）+ 独立管理页（设置菜单下）+ 内置6函数保留为内置插件（允许用户上传同名覆盖）。

1. **后端 `plugin_loader.py`**（新建，288行）：
   - 插件目录：`backend/tech_plugins/`
   - AST 安全校验 `validate_plugin_code(source) -> list[str]`：白名单导入（re/hashlib/math/datetime/time/collections/itertools/functools/apps.modeling.formula_engine）；禁止 os/sys/subprocess/socket/shutil/builtins/importlib/ctypes/threading/multiprocessing/signal/io/pathlib/tempfile/glob/pickle/sqlite3/http/urllib/requests 等；禁止顶层 if/for/while/try/with/ClassDef；禁止 eval/exec/compile/__import__/open/getattr/setattr 等危险内建；禁止 __import__/__builtins__/__file__ 等私有属性
   - 动态加载 `load_plugin(filename)`：importlib.util.spec_from_file_location + exec_module，加载前快照 FUNCTION_REGISTRY，加载后对比新增函数打 source 标记；同名插件先卸载旧版再加载新版（覆盖语义）
   - 卸载 `unload_plugin`/重载 `reload_plugin`/列表 `list_plugins`/启动扫描 `load_all_plugins`/模板 `get_plugin_template`
2. **后端 `apps.py`**：ModelingConfig 加 `ready()` 启动时调用 `plugin_loader.load_all_plugins()`，失败记日志不阻断
3. **后端 `views.py`**：ComputedFieldViewSet 新增 5 个 action：
   - `plugins/upload`（POST multipart，文件名规范化只保留字母数字下划线点连字符，先 AST 校验再写入再 load_plugin，加载失败回滚写入）
   - `plugins/unload`（POST filename）
   - `plugins/reload`（POST filename）
   - `plugins/list`（GET）
   - `plugins/template`（GET 返回模板代码）
4. **前端 `views/settings/TechFunctions.vue`**（新建，233行）：
   - 顶部说明 alert（安全策略提示）
   - a-upload-dragger 拖拽上传（accept='.py'，失败显示 details 多行错误）
   - 已加载插件列表（a-list，每项显示 filename + 函数 tag 含 category + 重载/卸载按钮，卸载带 popconfirm）
   - 模板弹窗（代码 pre 展示 + 一键复制按钮）
5. **前端路由/菜单**：router 加 `/settings/tech-functions` 路由 + MainLayout 系统设置菜单加「技术函数」入口
6. **前端 `api/modeling.ts`**：新增 PluginInfo/PluginFunctionInfo 接口 + computedFieldApi.pluginList/pluginUpload/pluginUnload/pluginReload/pluginTemplate
7. **验证**：
   - vue-tsc 0 errors
   - Django check 0 issues
   - 冒烟10步全通过：list空→template 787字节→合法.py上传成功注册SMOKE_TEST→available-functions含新函数→非法.py含import os被拒「行2：禁止导入 'os'」→reload成功→unload成功→list恢复空
   - 启动加载验证：放 startup_check.py 到 tech_plugins/ 重启后端，plugins/ 返回含 STARTUP_CHECK 函数，证明 apps.py ready() 扫描加载生效
8. **拓扑维护**：route_index.md 更新 views.py（新增5个plugins/* action）+ custom_functions.py（标注与用户上传插件共存）+ 新增 plugin_loader.py 条目

### 2026-07-27 技术函数方案A实施（第四十七轮）

> 用户确认「实施方案A就可以了」（不做方案C）。prjm路由→影响分析（拓扑核验：FUNCTION_REGISTRY消费方全部动态读注册表，前端/AI prompt零改动）→编码。

1. **新建** `backend/apps/modeling/custom_functions.py`：技术函数插件入口，文件头内嵌注册规范（全大写Excel风格命名/category='技术函数'/description含签名/函数签名(args,ctx)/业务错抛FormulaRuntimeError）。首批6函数：PAD_LEFT（左补齐默认补0）、REGEX_EXTRACT（正则提取首匹配，支持组序号）、REGEX_REPLACE（正则全替换）、SPLIT_INDEX（拆分取第N段，1开始越界返空）、MAP_VALUE（"旧1:新1;旧2:新2"映射表转换带默认值）、HASH_MD5（摘要可截前N位，迁移对账用）。
2. **接入点**：`formula_engine.py` 末尾 `from . import custom_functions  # noqa`（不依赖Django生命周期，任何导入引擎的地方注册表都完整）。
3. **零改动波及面验证**：get_available_functions()动态读注册表→前端FormulaEditor级联函数库自动出现「技术函数」分类；ai_service.generate_formula的prompt自动携带新函数签名；validate/_eval_func自动支持。
4. **验证**：Django check 0 issues；冒烟脚本（跑完已删）：total 38函数、6技术函数、9求值用例全OK（含IFERROR捕获非法正则、PAD_LEFT缺参校验报错）。
5. **修正发现**：route_index.md原登记formula_engine为「28内置函数+validate_formula/evaluate_formula」与代码不符，已修正为32函数+真实函数名（evaluate/validate_expression/get_available_functions）并新增custom_functions.py条目。
6. **遗留**：方案C（source_type=external外部预计算结果迁移映射）用户未选择，不实施；如后续需要再路由reqa。

### 2026-07-27 公式编辑器加宽+AI生成表达式+技术函数评估（第四十六轮）

> 测试报告5项：①数据预览栏目自动显示 ②窗口加宽后列表还是太窄 ③字段列表显示中文 ④AI输入表达式功能模块 ⑤技术函数功能（✨新需求，要评估）。AskUserQuestion确认：预览常驻+空态引导 / 窗口1480+侧栏560 / 表达式框上方内嵌AI输入行 / 问题5本轮只出评估报告。

1. **预览面板常驻**：`FormulaEditor.vue` preview-panel外层去掉v-if改常驻，内容包`<template v-if="previewResult">`，空态显示引导文案「输入计算表达式后自动展示数据预览」。
2. **窗口/侧栏加宽**：modal width 1280→1480px、formula-sidebar 400→560px；量化推理：二级栏可用宽 560-12(padding)-140(一级栏)-8(gap)≈400px，可容纳长code+中文名单行。
3. **字段中文优先**：ref-item内ref-name（中文名，#262626）移至首位为主体，ref-code（灰色monospace 11px）居后为辅助，双双ellipsis防溢出。
4. **AI生成表达式（全栈新增）**：
   - 后端 `ai_service.generate_formula(domain_id, description)`：_has_llm()前置校验（未配置直接RuntimeError不降级）；prompt含域内活跃字段（Field按table+sort_order，`{表名.code} — 中文名（类型）`）+活跃计算字段（`{$computed.code}`）+get_available_functions() 32函数签名；_chat强制json_object返回`{expression, explanation}`，解析失败/空表达式抛业务错误。
   - 后端 `views.py ComputedFieldViewSet` 新增 `generate-formula` action（detail=False POST，校验domain/description，异常统一400返回error）。
   - 前端 `api/modeling.ts`：GenerateFormulaResult接口+computedFieldApi.generateFormula。
   - 前端 `FormulaEditor.vue`：表达式label与textarea间插入ai-generate-row（a-input描述+AI生成按钮，pressEnter触发），成功后回填expression+显示explanation绿条+自动handleValidate+handlePreviewData；watch(open)重置AI状态；textarea 330→300px（补偿新增AI行高度，与侧栏总高对齐）。
5. **技术函数评估（问题5，未编码）**：三方案对比（A=FUNCTION_REGISTRY装饰器机制上扩展后端注册自定义Python函数插件，天然兼容formula_engine校验/求值/get_available_functions链路；B=SQL片段直通，绕过表达式引擎风险高；C=外部预计算结果字段迁移映射，适配「技术后端已处理好只做迁移」场景）。推荐A+C组合，结论待用户确认后下轮路由reqa做REQ-018。
6. **验证**：vue-tsc 0 errors；Django check 0 issues；shell冒烟has_llm=True、generate-formula action注册OK。
7. **拓扑维护**：route_index.md更新3处（ComputedFieldViewSet actions+ai_service.py职责+FormulaEditor.vue职责）。

### 2026-07-27 公式编辑器预览采样与侧栏级联重构（第四十五轮）

> 测试报告5项：①预览只有一个参数在变 ②先选字段再选函数 ③列表不能单行展示 ④两级分两个表 ⑤表达式框与侧栏同高。方案经确认：随机多样采样+级联双栏。

| 模块 | 变更 | 状态 |
|------|------|------|
| backend/computed_service.py | 新增_sample_combinations（轮转+seed42随机补足去重）；preview_expression正常/错误两路径+trial_calculate共三处islice替换（同类待修点一并修） | ✅ |
| FormulaEditor.vue 模板 | 字段引用Tab前置；两Tab改cascade双栏（左一级140px+右二级单行）；字段项改code+name不带表名前缀 | ✅ |
| FormulaEditor.vue script | sideTab默认'fields'；selectedRefTable/selectedFuncCategory+currentRefFields/currentCategoryFns+watch自动选第一组；删expanded*/toggle*折叠逻辑 | ✅ |
| FormulaEditor.vue CSS | textarea height 330px；cascade系列样式（height 300px）；func-item/ref-item改单行flex+ellipsis；删group-header折叠样式 | ✅ |
| 验证 | vue-tsc 0 errors + Django check 0 issues + 冒烟（采样50行3列各10唯一值；域8真实预览前两列各10值；错误路径返回输入列） | ✅ |

关键点：
- 真根因：itertools.product顺序截断→前50行仅末列变化，用户视觉上“只有一个参数”；非引用提取bug
- FX_NO字段去重值本身只有1个，属数据现状非缺陷
- _sample_combinations固定种子保证结果稳定可复现；总组合≤max时仍全量笛卡尔积
- 侧栏总高≈tabs38+search40+cascade300≈378，左列label26+textarea330≈356，视觉对齐

### 2026-07-27 属性配置Tab重构（第四十四轮）

> 测试报告2项：①属性Tab只显示2个字段（应展示全部进档案字段）；②左侧加字段分组列表。方案经确认：含计算字段只读展示 + 左栏只读筛选导航。

| 模块 | 变更 | 状态 |
|------|------|------|
| backend/views.py standard_fields | equiv行+sf_id/field_type/length/required/default_value/is_active；solo行+同名属性（sf_id/is_active=None） | ✅ |
| backend/serializers.py | StandardFieldAggregateSerializer 追加6个可选字段 | ✅ |
| frontend/api/modeling.ts | StandardFieldAggregate 接口扩展同名可选字段 | ✅ |
| DomainFieldConfig.vue 属性Tab | 数据源改聚合接口+计算字段；AttrRow统一行结构；保存按kind分流；左栏分组筛选（split-layout） | ✅ |

关键点：
- 根因：旧 loadAttrTabData 只调 standardFieldApi.list（仅 StandardField 组合字段，域8恰好2个），漏基础solo字段与计算字段
- 计算字段行只读：类型列显示输出类型tag，长度/必填/默认值/成员数/启用显示—，仅 release_to_archive 可切换
- is_active 仅 equiv 行有开关（Field/ComputedField 模型无此字段）
- 左栏复用 flatGroupTree/getDescendantGroupIds/expandedGroupIds，新增 attrActiveGroupId 独立于分组Tab的 activeGroupId；计算字段无分组（group=null，归入未分组）
- 验证：vue-tsc 0 errors；Django check 0 issues；冒烟测试域8返回28行含新属性字段

### 2026-07-25 公式编辑器数据预览功能（第四十二轮）

> FormulaEditor 新建/编辑计算字段窗口增加免保存数据预览：输入参数字段去重值枚举组合 + 输出结果逐行展示。

| 模块 | 变更 | 状态 |
|------|------|------|
| 后端服务 | computed_service.preview_expression：验证语法→提取引用→复用_build_param_space_from_distinct去重参数空间→笛卡尔积逐行计算（默认上限50条） | ✅ |
| 后端视图 | ComputedFieldViewSet新增preview-data action（detail=False，POST expression+domain，无需已保存实例） | ✅ |
| 前端API | computedFieldApi.previewData + PreviewDataRow/PreviewDataResult类型 | ✅ |
| 前端UI | 「数据预览」按钮（验证公式旁）+表达式下方内嵌预览表格（输入参数列+输出结果列，sticky表头，max-height 220可滚动，截断/空态/错误行提示，表达式变更自动清空，可收起） | ✅ |
| 验证 | vue-tsc 0 errors + Django check 0 issues + manage.py shell冒烟测试（合法/非法表达式均正确返回） | ✅ |

**完整性**：route_index.md ✅（无新模块依赖，FormulaEditor→computed-fields API 既有链路内新增action）

### 2026-07-25 字段分组Tab 3项修复（第四十一轮）

> 页面 /modeling/domains/:id/fields 字段分组Tab：下级分组列优化（移尾+缩宽+排序+同级显示--）+ 左栏分组拖拽排序。

| 模块 | 变更 | 状态 |
|------|------|------|
| 后端视图 | FieldGroupViewSet新增reorder action（POST /field-groups/reorder/ 接收ordered_ids，bulk_update sort_order） | ✅ |
| 前端API | fieldGroupApi.reorder(orderedIds) | ✅ |
| 前端列定义 | groupColumns：sub_group列移到最后、宽度140→100、加sorter（按显示文本localeCompare） | ✅ |
| 前端显示 | subGroupDisplay：本级字段/无分组显示灰色"--"，仅子分组字段显示分组名 | ✅ |
| 前端拖拽 | 左栏分组节点draggable，_dragGroupId区分分组拖拽与字段移组，findSiblingList限同父级，位置感知插入（从上往下拖放到目标之后） | ✅ |
| 验证 | vue-tsc 0 errors + Django check 0 issues | ✅ |

**完整性**：route_index.md ✅（无新依赖关系，模块内功能增强）

### 2026-07-25 测试报告3项修复（第四十轮）

> 页面 /modeling/domains/:id/fields 公式编辑器FormulaEditor三项修复：公式报错体验+字段值显示+验算入口。

| 模块 | 变更 | 状态 |
|------|------|------|
| 后端公式引擎 | tokenizer支持单引号字符串分界符(与双引号等效) | ✅ |
| 后端公式引擎 | validate_expression增加_validate_func_args遍历AST校验函数参数数量(min/max+IFS奇偶校验) | ✅ |
| 后端视图 | available_references返回字段id供前端定向刷新样本值 | ✅ |
| 后端视图 | FieldViewSet新增 load-sample-values detail action(单字段刷新distinct并返回前10条) | ✅ |
| 前端API | AvailableReference接口加id + fieldApi.loadSampleValues方法 | ✅ |
| 前端UI | 验证错误显示改醒目样式(加粗+边框+→⚠️图标+大字号) | ✅ |
| 前端UI | 选中字段始终显示预览面板(无值时"暂无样本值"+加载按钮调用load-sample-values) | ✅ |
| 前端UI | FormulaEditor弹窗底部增加"保存并试算"按钮(emit save-and-trial→父组件打开TrialCalculation) | ✅ |
| 验证 | vue-tsc 0 errors + Django check 0 issues + 单元测试全通过 | ✅ |

**完整性**：route_index.md ✅（无新依赖关系，仅内部功能增强）

### 2026-07-25 多层分组功能实现（darc编码，第三十六轮）

> FieldGroup模型加parent外键实现多层嵌套（最多3层）。前后端同步改造，左栏从平铺列表改为树形交互。

| 模块 | 变更 | 状态 |
|------|------|------|
| 后端模型 | FieldGroup.parent(FK self,SET_NULL,nullable) + level属性(计算) + get_descendants方法(递归) | ✅ |
| 后端迁移 | 0022_add_parent_to_fieldgroup | ✅ |
| 后端序列化器 | parent字段 + children(tree_mode下递归) + level + validate(深度≤ 3 + 禁止循环) | ✅ |
| 后端视图 | tree=1参数只返回顶层 + perform_destroy(子组上浮+字段变未分组) + filterset加parent | ✅ |
| 前端类型 | FieldGroup加parent/level/children | ✅ |
| 前端API | fieldGroupApi.tree(domainId) | ✅ |
| 前端左栏 | 树形节点(展开/收起三角符+缩进) + 新建子分组按钮(≤ 2层时显示) + 拖放目标支持树节点 | ✅ |
| 前端右栏 | 点击父分组显示自身+所有后代分组的字段汇总 | ✅ |
| 前端下拉 | group_select下拉选项按层级缩进显示(全展平不受展开状态影响) | ✅ |
| 验证 | vue-tsc 0 errors + Django check 0 issues + migrate 0022 OK | ✅ |

**完整性**：route_index.md ✅（模块状态无变，无新依赖关系）

### 2026-07-25 计算字段功能全栈实现（darc编码，第三十五轮）

> REQ-017 计算字段配置与自动计算 — 从详细设计到全功能实现，跨两个会话完成。10个子任务全部完成。

| 任务 | 实现 | 影响文件 | 状态 |
|------|------|---------|------|
| T1 模型扩展 | ComputedField 新增 depends_on/depends_on_computed(M2M)/parsed_references(JSON)/execution_order/output_type | models.py | ✅ |
| T2 公式引擎 | formula_engine.py: Lexer+Parser+Evaluator+28内置函数+字段引用解析 | formula_engine.py(新) | ✅ |
| T3 计算服务 | computed_service.py: DAG拓扑排序(Kahn)+循环检测(DFS三色)+批量/实时重算 | computed_service.py(新) | ✅ |
| T4 后端API | ComputedFieldViewSet +6 actions(validate_formula/trial_calculate/dependency_graph/batch_recalculate/available_functions/available_references) + perform_create/update自动解析依赖 | views.py, serializers.py | ✅ |
| T5 档案集成 | schema含计算字段(release_to_archive+active) + sync后 batch_recalculate + 编辑保存时 recalculate_affected | archive/views.py, archive/serializers.py | ✅ |
| T6 前端API层 | +6接口(FormulaValidationResult/TrialCalculateResult/DependencyGraphResult等) + computedFieldApi +6方法 | api/modeling.ts | ✅ |
| T7 FormulaEditor | 公式编辑器modal(268行): code/name/output_type表单 + textarea实时验证 + 函数面板 + 字段引用选择器 | FormulaEditor.vue(新) | ✅ |
| T8 TrialCalculation | 枚举试算modal(246行): 参数表格 + 自动枚举/手动参数 + 结果表格 | TrialCalculation.vue(新) | ✅ |
| T9 DomainFieldConfig增强 | 工具栏(新建/依赖图/批量重算) + 表格列增强(公式摘要/输出类型/执行顺序/操作) + modal集成 | DomainFieldConfig.vue | ✅ |
| T10 集成验证 | Django check 0 issues + vue-tsc 0 errors | - | ✅ |

### 2026-07-25 计算字段功能概念设计（reqa增量，第三十四轮）

> REQ-017 计算字段配置与自动计算 — 从用户提供的门店SQL（10条MERGE INTO）分析复杂度，经多轮交互确定Excel公式风格+DAG+枚举试算方案，完成增量概念设计。

| 需求 | 实现 | 产出文件 | 状态 |
|------|------|---------|------|
| 需求定义 | REQ-017（4场景：新建配置/枚举试算/同步后重算/编辑实时重算；6条业务规则BR-017-1~6） | requirements.json | ✅ |
| 用户旅程 | 7步故事线（创建→编辑公式→依赖解析→试算→保存→同步重算→编辑重算） | storylines/REQ-017.md | ✅ |
| 业务流程 | 流程五：计算字段配置与执行（配置阶段Mermaid+执行阶段Mermaid+6条异常路径） | business-flow.md | ✅ |
| 功能清单 | F-011~F-017 共7项（新建/公式编辑器/依赖解析/枚举试算/同步重算/编辑重算/管理），全P0 | concept-feature-list.md | ✅ |
| 追溯矩阵 | REQ-017→F-011~F-017→流程五，覆盖检查17/17需求 | concept-architecture.md | ✅ |
| 关键决策 | constitution.md 新增「计算字段功能设计」决策记录 | constitution.md | ✅ |

**关键设计决策：**
- 公式语法：Excel函数命名（IF/CONCAT/SWITCH/IFS/IFERROR/VLOOKUP/MAXIFS等）
- 字段引用：`{表名.字段名}` 语法，仅同域内基础字段和组合字段
- 依赖管理：自动解析DAG + 循环依赖检测 + 拓扑排序确定执行顺序
- 验证机制：枚举试算（参数从字段distinct_values填充+笛卡尔积自动枚举）
- 存储策略：物化存储（计算结果落库参与档案消费，可同步到物理表）
- 触发时机：双触发（数据源同步后批量重算 + 记录编辑保存时实时重算）
- 复杂逻辑：拆解为多个计算字段，通过计算字段间依赖+DAG顺序执行

### 2026-07-25 测试报告3项修复（第三十三轮）

> 页面 /modeling/domains/:id/fields 字段分组Tab三项修正（测试问题1/2/3，问题4多层分组留后续）。

| 需求 | 实现 | 影响文件 | 状态 |
|------|------|---------|------|
| 问题1 删除「释放到档案」列 | groupColumns删除release列定义、模板删除release bodyCell、删除toggleGroupRelease函数 | DomainFieldConfig.vue | ✅ |
| 问题2 分组Tab只展示档案字段 | 后端 standard-fields action：solo字段过滤只保留archive_category='base'；StandardField只包含status='active' | views.py | ✅ |
| 问题3 术语修正 | 类型列tag「独立」→「基础字段」 | DomainFieldConfig.vue | ✅ |
| 问题4 多层分组 | 留作后续设计（需增加FieldGroup.parent外键+前端树形交互） | - | ⏳ |
| 验证 | vue-tsc EXIT=0, Django check 0 issues | - | ✅ |

### 2026-07-25 标准字段页重构三分类架构（第三十二轮）

> 页面 /modeling/domains/:id/fields 全面重写。用户要求：左栏字段分类导航（档案字段→基础/组合/计算、未分配、废弃）+ 右栏字段表格，删除AI检测功能。

| 需求 | 实现 | 影响文件 | 状态 |
|------|------|---------|------|
| 后端模型扩展 | Field.archive_category(unassigned/base/calculated) + StandardField.status(active/discarded) + ComputedField新模型(骨架) + migration 0020 | models.py, migrations/ | ✅ |
| 后端视图扩展 | field-categories action(各分类计数) + ComputedFieldViewSet(CRUD) + batch-attributes支持archive_category + manual-candidates返回archive_category | views.py, urls.py | ✅ |
| 后端序列化器 | ComputedFieldSerializer + StandardFieldSerializer加status + FieldListSerializer加archive_category | serializers.py | ✅ |
| 前端API层 | ComputedFieldModel + FieldCategoryCounts + computedFieldApi + fieldApi.fieldCategories + StandardFieldModel.status | api/modeling.ts | ✅ |
| 前端页面重写 | 2095行→713行：左栏200px分类导航(带计数badge) + 右栏五视图切换(base/composite/computed/unassigned/discarded) | DomainFieldConfig.vue | ✅ |
| 删除AI检测 | 移除 runDetectStandards/dedupSuggestions/checkedSuggestionKeys/applyDedup 及相关UI | DomainFieldConfig.vue | ✅ |
| 验证 | vue-tsc EXIT=0, Django check 0 issues, migration 0020 applied | - | ✅ |

### 2026-07-24 标准字段界面工具栏重排+统一启用开关（第二十七轮）

> 页面 /modeling/domains/8/fields 标准字段Tab，测试报告3个交互微调（针对上轮双栏看板）。先出研究式分析报告，再AskUserQuestion确认：①一个模糊搜索+刷新上移、编码/名称收进弹窗 ②搜索同时过滤上下表 ③下表也去checkbox改启用开关（“B，上下表逻辑一样，字段名也统一”）。

| 需求 | 实现 | 影响文件 | 状态 |
|------|------|---------|------|
| 问题1+3 公用控件顶置 | 一个模糊搜索框(manualFieldSearch)+刷新数据去重按钮上移顶部工具栏(a-space wrap)；删除下区原 manualForm 输入行+搜索/刷新行 | DomainFieldConfig.vue | ✅ |
| 问题1 搜索同时过滤上表 | 新增 filteredStandardFieldModels computed 按 manualFieldSearch 过滤上表(standard_code/name/members)；上表 :dataSource 改 filteredStandardFieldModels | DomainFieldConfig.vue | ✅ |
| 问题1 编码/名称收进弹窗 | 新增 manualCreateVisible 弹窗(标准编码required+中文名)；下区按钮“确认到上面”→openManualCreateModal(校验已选后开弹窗)→submitManualStandardField 成功后关弹窗 | DomainFieldConfig.vue | ✅ |
| 问题2 上表checkbox与switch冲突 | 上表删除 to_archive checkbox 列；新增 enable 列(is_active switch，从actions列移出)；toggleStandardFieldActive 保留驱动 is_active | DomainFieldConfig.vue | ✅ |
| 决策B 下表统一 | 下表删除 to_archive checkbox，改 enable switch(release_to_archive 驱动)；上下表列名统一“启用”；删除 toggleConfirmedReleaseArchive 函数 | DomainFieldConfig.vue | ✅ |
| 列定义 | standardFieldModelColumns+manualColumns 删 to_archive 列、末尾加 {key:'enable',width:90,align:center}；actions width 200→140 | DomainFieldConfig.vue | ✅ |
| 后端 | 无需改动（纯前端交互微调，is_active/release_to_archive 后端门控不变） | - | ✅ |
| 验证 | vue-tsc EXIT=0 | - | ✅ |

### 2026-07-24 标准字段界面重做：上/下双栏看板（第二十六轮）

> 页面 /modeling/domains/8/fields 标准字段Tab，测试报告“整个重新编排”(模块重做)5子诉求。先出研究式分析报告，再AskUserQuestion确认方向：方案B双栏看板+复用release_to_archive门控+拖排仅前端不落库+确认到档案只读预览。

| 需求 | 实现 | 影响文件 | 状态 |
|------|------|---------|------|
| ①上=已确认/下=未确认 | dedup视图重构为①已确认标准字段区+②未确认候选区两个dedup-section（垂直上/下） | DomainFieldConfig.vue | ✅ |
| ②下→上确认/上→下释放 | 下→上：submitManualStandardField(按钮改“确认到上面”)；上→下：上表加confirmedRowSelection+“释放选中回下面”按钮→releaseSelectedToBottom(逐个dissolve→成员变回候选) | DomainFieldConfig.vue | ✅ |
| ③上下都可勾选进档案 | 两表首列新增“进档案”a-checkbox（复用两层门控release_to_archive）；上表equiv→standardFieldApi.patch(release_to_archive)；下表solo→fieldApi.batchUpdateAttributes(release_to_archive)；toggleConfirmedReleaseArchive/toggleCandidateReleaseArchive | DomainFieldConfig.vue | ✅ |
| ④下表拖动换位 | 下表加custom-row=candidateRowProps(draggable+dragstart/over/drop/end)，onCandidateDrop对manualCandidates数组splice重排（仅前端临时，不落库）；移除manualFilteredCandidates原“已选顶置”自动排序(与拖拽冲突，覆盖第二十一轮问题2) | DomainFieldConfig.vue | ✅ |
| ⑤确认到档案按钮 | 工具栏加“确认到档案”按钮→openArchivePreview→a-modal展示最终字段(标准编码/名称/类型/分组/物理表)；后端新增GET /fields/archive-preview/?domain=只读action复用archive._generate_schema_from_domain(schema项含table) | views.py / modeling.ts / DomainFieldConfig.vue | ✅ |
| 后端辅助 | manual_candidates返回加release_to_archive/release_to_concept（供下表勾选回显） | views.py | ✅ |
| 前端类型 | 新增ArchiveSchemaItem接口+ManualFieldCandidate加release_to_archive?/release_to_concept?；fieldApi.archivePreview | modeling.ts | ✅ |
| 无需改动 | models.py(sort_order/release_to_archive/is_active均已存在)、archive/views.py门控逻辑 | - | ✅ |
| 验证 | vue-tsc EXIT=0；Django check 0 issues | - | ✅ |

### 2026-07-24 标准字段页手动新增内联化+启用开关语义改概念模型（第二十五轮）

> 页面 /modeling/domains/8/fields 标准字段Tab。用户诉求：①把「手动新增标准字段」弹窗内容放到「已确认的标准字段」下方；②增加启用/停用决定是否到概念模型。经 AskUserQuestion 确认：Part A 删按钮直接内联；Part B 复用现有 is_active 开关改语义（不进档案→不纳入概念模型）。

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| Part A 内联化 | 删除 dedup-toolbar「手动新增标准字段」按钮；a-modal 整体拆除，内容改为 dedup-section 内联区块置于「已确认的标准字段」表格下方（常驻显示）；新增区含 标准编码/名称输入+搜索+刷新去重按钮+「新增（已选N）」primary 提交按钮+候选多选表；表格 scroll.y 由 calc(100vh-300px) 改固定 360（内联区不再占满视口） | DomainFieldConfig.vue | ✅ |
| Part A 数据加载 | 候选由 openManualModal 触发改为 onMounted(loadData+loadManualCandidates) 预加载；openManualModal 改 resetManualForm（仅重置表单不含 fieldSearch/visible）；submitManualStandardField 成功后 resetManualForm()+补 loadManualCandidates() 刷新候选（已配置字段即时移出）；移除 manualModalVisible ref | DomainFieldConfig.vue | ✅ |
| Part B 语义改造 | 查证：is_active 仅在 archive/views.py _field_released 作档案释放门控（is_active=False→不释放），无独立概念模型消费者。用户选复用+改语义：toggleStandardFieldActive message 由「不进档案」改「不纳入概念模型」；is_active 开关外包 a-tooltip「启用=纳入概念模型并向下游档案释放；停用=不纳入概念模型」；后端 is_active 行为/help_text 不动（避免多余迁移） | DomainFieldConfig.vue | ✅ |
| 验证 | vue-tsc 零错误 | - | ✅ |

### 2026-07-24 字段管理3项修复：默认Tab改标准字段+差异高亮改频次+成员单独释放（第二十三轮）

> 页面 /modeling/domains/8/fields 三问题。①从域管理进入首屏应是标准字段而非字段分组；②去重查看全部标红（根因：交集判断+100条截断），应仅“基于值”的不一致才红；③需可单独释放某表字段与标准字段的关系。

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 问题1 默认Tab | mainTab 初始值 'group'→'dedup'（标准字段）；onMounted 已无关Tab全量加载数据，改默认安全 | DomainFieldConfig.vue | ✅ |
| 问题2 差异高亮改频次 | 删 commonDistinctSet(交集)；新 memberValueFrequency computed（各值在多少个成员出现，单成员内去重）；isDiffValue=成员数>1 且 freq≤1→红（仅单成员独有的值）；抽屉顶部加红色含义图例 | DomainFieldConfig.vue | ✅ |
| 问题3 单独释放 | 抽屉成员卡片标题行加「释放」(a-popconfirm danger)；removeMemberFromStandard 调 removeMember 后本地过滤+刷新标准字段表/聚合；distinctStandardFieldId 记录当前SF | DomainFieldConfig.vue | ✅ |
| 问题3 后端 | StandardFieldViewSet 新增 remove-member action(detail POST {field_id})：校验字段属于该SF→member.standard_field=None save；返回 {ok,removed_field_id,remaining} | views.py | ✅ |
| 问题3 前端API | standardFieldApi.removeMember(id,fieldId) POST /standard-fields/{id}/remove-member/ | api/modeling.ts | ✅ |
| 验证 | vue-tsc 零错误；manage.py check 0 issues | - | ✅ |
| 遗留提醒 | 问题2 若仅两2个成员且高基数(>100)，频次法与交集等价仍可能全红（100条截断）；如需彻底解决需提高 _fetch_distinct_values 的 limit 或改采样策略 | - | ⏳ |

### 2026-07-24 AI配置页精简：主区只留模型+APIKey、其余折叠、模型改可输入下拉自动带接口地址（第二十二轮）

> 用户反馈 AI 配置页字段太多太复杂，只想要「模型选择 + API Key」，且提到当前 DeepSeek 模型（DS-V4flash）过时。经 AskUserQuestion 确认方向后精简。

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 主区精简 | 表单主区只保留 模型（a-auto-complete）+ API Key 两项；配置名称/启用/服务厂商/接口地址/采样温度/超时 全部移入 a-collapse「高级设置」面板（activeAdvancedKeys 默认 []收起） | AIConfig.vue | ✅ |
| 模型单下拉可输入 | 由「厂商select+模型select(非custom)/input(custom)」改为单个 a-auto-complete：modelSelectOptions（跨厂商扁平 {value,label:厂商·模型}）+ filterModelOption（value/label 双匹配）；@change=onModelChange 命中 MODEL_INDEX（模型名→厂商+api_base）则自动带出，未命中(自定义名如DS-V4flash)保持当前接口地址不变 | AIConfig.vue | ✅ |
| 保留能力 | 提示词配置区（a-collapse 4面板）保持折叠不变；高级设置内厂商 onProviderChange 仍自动填 api_base+重置模型；isCustom 仍控制接口地址可编辑；payload 提交字段不变（后端无需改动） | AIConfig.vue | ✅ |
| 模型列表说明 | DeepSeek 预设 API id 保持 deepseek-chat/deepseek-reasoner（真实API标识，DS-V4flash 为产品名）；因改可输入下拉，用户可直接输入任意当前模型名，无需改预设 | - | ✅ |
| 验证 | vue-tsc 零错误 | - | ✅ |

### 2026-07-24 手动新增标准字段3项修复：失败明细化+弹窗填满+成员值排序与差异红标（第二十一轮）

> 页面 /modeling/domains/8/fields 三问题。①刷新后仍有字段未读到数据—根因：refresh_distinct 返回 errors[] 但前端只显示计数，且弹窗单元格把 null(失败)与 [](无数据)混为“未读取”；②弹窗不够高—固定 vh 留白；③抽屉去重值未排序且差异未高亮。

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 问题1 失败明细化 | refreshManualDistinct 改为收集 errors[]，有失败时 Modal.warning 列出每个失败字段编码(codeMap 映射回退#id)+后端错误原因(红字)；弹窗 distinct 单元格区分 Array&&length===0→“无数据(取值全为空)”灰色 / 否则→“未读取/读取失败”黄色；导入 Modal+h | DomainFieldConfig.vue | ✅ |
| 问题2 弹窗填满 | body-style maxHeight 82vh→calc(100vh-140px)（top16+头55+footer53≈140）；表格 scroll.y 62vh→calc(100vh-300px)（减表内表单/搜索/提示/表头≈160） | DomainFieldConfig.vue | ✅ |
| 问题3 排序+差异红标 | sortedMemberValues(m)：distinct_values 转String 后 localeCompare(numeric)；commonDistinctSet computed：各成员取值集合的交集（≤1成员返回null不高亮）；isDiffValue(v)：不在交集→差异值；抽屉 a-tag :color=isDiffValue?red:undefined | DomainFieldConfig.vue | ✅ |
| 验证 | vue-tsc 零错误（修正 commonDistinctSet 的 Set<never> 推断→显式 sets.map + 索引循环） | - | ✅ |

### 2026-07-24 手动新增标准字段弹窗最大化+去换页器全量展示（第二十轮）

> 页面 /modeling/domains/8/fields。用户反馈（引 uxqa）：手动新增标准字段弹窗应为最大窗口（上轮 90vw/maxWidth1280 仍不够大）；不要底部换页器，要全部展示。根因：maxWidth:1280px 封顶导致大屏不能铺满；表格 pagination pageSize:15 分页。

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 弹窗最大化 | width 90vw→96vw；移除 :style 中 maxWidth:'1280px'（大屏不再被封顶）；top 32px→16px；body-style maxHeight 72vh→82vh | DomainFieldConfig.vue | ✅ |
| 去换页器全量 | 表格 :pagination 由 {pageSize:15,showSizeChanger} 改为 false；scroll.y 46vh→62vh（适应全量行区内滚动） | DomainFieldConfig.vue | ✅ |
| 尺寸推理 | top16px+头部~55px+footer~53px+body82vh ≈ 89.7vh < 100vh，无溢出 | - | ✅ |
| 验证 | vue-tsc 零错误 | - | ✅ |

### 2026-07-24 AI配置页增强：默认DeepSeek+厂商/模型下拉(接口地址自动)+四类prompt可配置（第十九轮）

> 用户诉求：①AI配置默认用DeepSeek；②把各种要配置的提示词都放进配置页可在线编辑；③能选尽量选——模型直接下拉选、接口地址不用手写(选厂商/模型后自动填充)。设计：DB只存prompt指令部分，字段数据JSON由各_llm函数运行时f-string追加；厂商预设映射放前端，选定自动带出api_base+可选模型。

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| Task1 模型扩展 | AIConfig 加 provider(默认'deepseek')+prompt_auto_group/semantic/dedup/infer 4个TextField；api_base默认改 https://api.deepseek.com/v1、model默认改 deepseek-chat | models.py, migrations/0018 | ✅ |
| Task2 prompt可配置化 | ai_service 加 DEFAULT_PROMPT_*(4常量,原内联指令)+PROMPT_META+_resolve_prompt(key,default)(DB enabled对应字段优先,空则内置默认)+prompt_defaults()；4个_llm函数改用 _resolve_prompt(...)+f'\n字段列表/列数据：{json}' | ai_service.py | ✅ |
| Task3 serializer | AIConfigSerializer fields 加 provider+4prompt字段+prompt_defaults(SerializerMethodField→ai_service.prompt_defaults()供前端恢复默认) | serializers.py | ✅ |
| Task4 前端配置页 | AIConfig.vue：PROVIDERS预设(deepseek/openai/qwen/zhipu/moonshot/custom各含api_base+models)；厂商a-select onProviderChange自动填api_base+模型不匹配切首个；模型 a-select(非custom show-search)/a-input(custom)；api_base disabled(非custom)+inferProvider反查；prompts独立reactive避TS动态索引；prompt配置区 a-collapse遍历PROMPT_FIELDS(textarea v-model prompts[key],placeholder=默认+恢复默认按钮) | AIConfig.vue | ✅ |
| Task5 前端接口 | AIConfigModel 加 provider/prompt_auto_group/semantic/dedup/infer/prompt_defaults(Record<string,string>) | api/modeling.ts | ✅ |
| 验证 | manage.py check 通过；makemigrations+migrate 0018 OK；vue-tsc 零错误 | - | ✅ |

### 2026-07-24 测试报告4项修复：弹窗放大+勾选顶置+去重值查看抽屉+AI分组prompt重写+AI配置页（第十八轮）

> 页面 /modeling/domains/8/fields 四问题。用户确认方向：④b 完整配置页+在线编辑+测试连接（新增AIConfig模型）；④a 重写prompt强调按业务主题分组+改进启发式；③ 抽屉并排展示各成员去重值。根因诊断：AI分组「很傻」是因 API_KEY 空降级到启发式且旧桶按技术关键词分组。

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 问题1 弹窗放大 | 手动新增 a-modal width 960→90vw、maxWidth1280、body-style maxHeight72vh、table scroll y 46vh、pageSize 10→15 | DomainFieldConfig.vue | ✅ |
| 问题2 勾选顶置 | manualFilteredCandidates 加稳定排序：已勾选(manualSelectedFieldIds)项排前，便于核对确认 | DomainFieldConfig.vue | ✅ |
| 问题3 后端接口 | StandardFieldViewSet 加 members-distinct action(detail GET)：复用 _ensure_distinct_cache 返回各成员 {field_id,table_name,code,name,comment,distinct_values,synced_at,count} | views.py | ✅ |
| 问题3 前端抽屉 | 已确认标准字段表操作列加「查看」按钮→a-drawer(70vw)并排展示各成员卡片(表名.编码+去重值 a-tag)；standardFieldApi.membersDistinct + StandardFieldMemberDistinct 接口 | DomainFieldConfig.vue, api/modeling.ts | ✅ |
| 问题4a prompt重写 | _auto_group_llm prompt 强调按业务主题(客户/商品/订单等)分组、严禁按数据类型；_auto_group_heuristic 桶改为9业务主题(客户/商品/订单/组织/联系方式/财务/状态/审计/基础标识)中英文关键词、text 加 comment | ai_service.py | ✅ |
| 问题4b 后端 | AIConfig 单例模型(name/api_base/api_key/model/temperature/timeout/enabled，迁移0017)；AIConfigSerializer(api_key write_only+has_api_key，空值不改)；AIConfigViewSet(current GET/PUT + test-connection POST)；urls 注册 ai-config；ai_service 加 _resolve_ai_config(优先DB enabled回退env)/_chat(cfg参数)/test_connection/_has_llm改用DB | models.py,serializers.py,views.py,urls.py,ai_service.py | ✅ |
| 问题4b 前端 | settings/AIConfig.vue(表单+测试连接+保存)；aiConfigApi(current/update/testConnection)+AIConfigModel接口；router 加 /settings/ai；MainLayout 系统设置改父级带children(数据源配置+AI配置) | AIConfig.vue,api/modeling.ts,router/index.ts,MainLayout.vue | ✅ |
| 验证 | manage.py check 通过；makemigrations+migrate 0017 OK；vue-tsc 零错误 | - | ✅ |

### 2026-07-23 标准字段功能再设计：三层匹配+手动新增可排序表格（第十七轮）

> 用户三诉求：①AI检测三层匹配（编码/名称/**数据去重内容**）；②手动新增界面改可排序表格便于识别成套字段；③排除已配置标准字段的字段。决策：去重内容取全量去重值（100条安全上限），第三层直接把去重值喂 LLM（不做 Jaccard）。

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| Task1 去重缓存字段 | Field 加 distinct_values(JSONField,默认None)+distinct_synced_at(DateTime)，上限100条 | models.py, migrations/0016 | ✅ |
| Task2 去重值读取 helper | 模块级 _fetch_distinct_values(table,field_code,limit=100)：本地表默认连接 SELECT DISTINCT；外部表动态连接按 db_type（sqlserver TOP/oracle ROWNUM/mysql·postgresql LIMIT），值经 _json_safe，异常返回 None | views.py | ✅ |
| Task3 刷新+共享缓存 | _ensure_distinct_cache(fields,force)：force=False 仅查 None 缓存（detect 按需）、force=True 全重查；refresh-distinct action(POST ?domain=) 遍历 active 字段 force 刷新返回 {updated,errors} | views.py | ✅ |
| Task4 AI三层匹配 | detect_duplicate_fields(distinct_map)；_detect_duplicates_heuristic 加去重值集合完全相同则 union（排序后 hash key）；_detect_duplicates_llm items 加 distinct_values、prompt 改编码/名称/去重内容三维度综合判断；detect_standards 先 _ensure_distinct_cache 再构造 distinct_map | ai_service.py, views.py | ✅ |
| Task5 手动新增候选 | manual-candidates action(GET ?domain=)：standard_field__isnull=True 排除已配置；每项 {id,code,name,comment,table_name,source_label,distinct_values,distinct_synced_at}，source_label 外部=数据源名/表名·本地=表名 | views.py | ✅ |
| Task6 前端 API | fieldApi 加 refreshDistinct/manualCandidates + ManualFieldCandidate 接口 | api/modeling.ts | ✅ |
| Task7 手动新增表格 | a-modal 由 checkbox-group 改 a-table（row-selection 多选成员，列 编码/名称/来源/去重内容 均带 sorter，distinct 列 a-tag+tooltip，前8项+计数）+搜索框+刷新去重内容按钮；openManualModal async 载后端候选 | DomainFieldConfig.vue | ✅ |
| 验证 | manage.py check 通过；makemigrations+migrate 0016 OK；vue-tsc 零错误（修 row-key 隐式 any 改 row-key="id"） | - | ✅ |

### 2026-07-23 测试问题报告6项修复（第十六轮）

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 问题1 主键不刷新 | TableList.doTogglePrimaryKey 成功后调 syncPrimaryKeysToTableList：从 fieldModalFields 重算主键列表({id,code,name,comment} 按 sort_order/id 排序)回写 tables.value 对应行的 primary_keys，列表即时更新无需刷新 | TableList.vue | ✅ |
| 问题2 去重后不刷新+引导 | applyDedup 成功后补 loadStandardFields()+loadStandardFieldsForAttr()（原只 loadStandardFieldModels）；group Tab 顶部加 a-alert 引导先去标准字段Tab完成检测/去重 | DomainFieldConfig.vue | ✅ |
| 问题3 标准字段表精简+启停 | 移除「来源」列；「操作」列解散→a-switch 启用/停用（保留解散）。StandardField 加 is_active(default True) 迁移0015；StandardFieldSerializer 加 is_active；_field_released equiv 分支 is_active=False 即不释放（与 release_to_archive 取交）；toggleStandardFieldActive 调 patch 后刷新聚合 | models.py, migrations/0015, serializers.py, archive/views.py, api/modeling.ts, DomainFieldConfig.vue | ✅ |
| 问题4 分组加释放到档案 | standardFieldColumns 加 release_to_archive 列 + a-checkbox；toggleGroupReleaseToArchive（equiv 走 standardFieldApi.patch 按 key 取 id、solo 走 fieldApi.batchUpdateAttributes physical_field_ids） | DomainFieldConfig.vue | ✅ |
| 问题5 分组重命名400 | 根因 FieldGroupSerializer.domain 非 read_only，PUT 全量校验触发 domain 必填。fieldGroupApi.update 改 api.patch（部分更新）修复所有分组重命名 | api/modeling.ts | ✅ |
| 问题6 AI名称匹配+手动新增 | ai_service 加 _normalize_name（去空白/标点+小写）；_detect_duplicates_heuristic 改并查集按「编码或名称任一命中」union 跨2+表成组；LLM prompt 补名称匹配说明。StandardFieldViewSet.create（接收 member_field_ids 挂靠成员，source=manual，update_or_create 防重）；standardFieldApi.create；DomainFieldConfig.vue dedup Tab 加「手动新增标准字段」按钮+弹窗（编码/名称+搜索浏览相似字段勾选成员） | ai_service.py, views.py, api/modeling.ts, DomainFieldConfig.vue | ✅ |
| 用户澄清 | 问题6数据一致性用「看表字段去重」判断即可，不做真实数据源抽样查询 | - | ✅ |
| 验证 | manage.py check 通过；makemigrations+migrate 0015_standardfield_is_active OK；vue-tsc 零错误 | - | ✅ |

### 2026-07-23 字段两层释放门控（物理层→概念层→档案）（第十五轮）

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 方向 | 经 AskUserQuestion 确认 3 项决策：①取代上一轮不同步写回（is_sync_excluded）改为两层释放门控 ②未释放字段完全不出现（不进 schema、不拉取、记录无该列） ③概念层每个概念行（equiv+solo）都可设「释放到档案」 | - | ✅ |
| 释放规则 | 字段进档案 ⇺ release_to_concept==True 且（有 SF：sf.release_to_archive；无 SF/solo：f.release_to_archive） | - | ✅ |
| 后端-模型 | Field 新增 release_to_concept/release_to_archive（default=True）并移除 is_sync_excluded；StandardField 新增 release_to_archive；迁移 0014_field_release_gates（AddField x3 + RunPython 把原 is_sync_excluded=True 行设为双 False + RemoveField is_sync_excluded） | modeling/models.py, migrations/0014 | ✅ |
| 后端-schema/同步 | 新增共享 helper _field_released(f,sf)；_generate_schema_from_domain 按释放规则过滤后再按输出 code dedup；sync_to_source 用同一规则构 code_to_physical（移除上一轮 excluded_columns 逻辑），旧记录残留未释放列也不会被映射/比对/回写 | archive/views.py | ✅ |
| 后端-serializer/view | FieldListSerializer 换为 release_to_concept/release_to_archive；StandardFieldSerializer 加 release_to_archive（支持 PATCH）；StandardFieldAggregateSerializer + standard_fields builder 每行带 release_to_archive（equiv 取 SF、solo 取物理）；batch_update_attributes 白名单换字段 | modeling/serializers.py, views.py | ✅ |
| 前端-物理层 | types Field 去 is_sync_excluded 加 release_to_concept?/release_to_archive?；TableList.vue 字段管理列「不同步写回」→「释放到概念层」，toggleSyncExcluded→toggleReleaseToConcept | TableList.vue, types/index.ts | ✅ |
| 前端-概念层 | api/modeling.ts StandardFieldModel/Aggregate 加 release_to_archive + standardFieldApi.patch；DomainFieldConfig.vue 属性 Tab 新增「释放到档案」列+复选框+toggleReleaseToArchive（equiv PATCH standard-fields、solo batch-attributes） | api/modeling.ts, DomainFieldConfig.vue | ✅ |
| 验证 | manage.py check 通过；migrate 0014 OK（dev 库 5 条 D_ETL_TIME 转为 release_to_concept=False & release_to_archive=False）；vue-tsc 零错误；grep 全项目无 is_sync_excluded/toggleSyncExcluded/excluded_columns 残留（迁移文件除外）；_generate_schema_from_domain 输出 38 字段（原 39）has_D_ETL_TIME=False；sync_to_source code_to_physical 主表 16 列 has_D_ETL_TIME=False | - | ✅ |
| 转换说明 | 现有档案的 archive.schema 与记录仍含旧字段（D_ETL_TIME），需重跑「同步模型(sync-schema)」再生才彻底剔除；转换期间 sync_to_source 门控已保证不误回写 | - | ✅ |

### 2026-07-23 「待处理记录不应是975条」→ 不同步写回字段机制（第十四轮）

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 根因 | 同步向导第一步「待处理记录」= records_total(全档案975)，语义错误；且 946 条「更新」几乎全部仅因 `D_ETL_TIME`（ETL 加载时间戳，源端 ETL 自动维护）差异被误判为更新 | - | ✅ |
| 方向 | 经 AskUserQuestion 用户选「字段管理加不同步写回开关」（选项A）：Field 模型加 is_sync_excluded，字段管理页勾选，比对+写回均跳过被勾选列，已知 ETL 列默认预勾选 | - | ✅ |
| 后端-模型 | modeling Field 加 `is_sync_excluded` BooleanField（default=False）；迁移 0013_field_is_sync_excluded 含 RunPython 预勾选 ETL 列（code icontains ETL_TIME/ETL_DATE/LOAD_TIME 或 iexact D_ETL_TIME）；dev 库预勾选 5 条 D_ETL_TIME | modeling/models.py, migrations/0013 | ✅ |
| 后端-serializer/view | FieldListSerializer fields 加 'is_sync_excluded'；batch_update_attributes attr 白名单加 'is_sync_excluded'（复用现有批量属性更新通道） | modeling/serializers.py, views.py | ✅ |
| 后端-同步排除 | sync_to_source：遍历 all_fields 时收集 is_sync_excluded 物理列→excluded_columns；构建 row_data 时 `if phys_col in excluded_columns and phys_col not in pk_columns: continue`（主键列始终保留用于 WHERE 定位）。排除列自然从 diff/insert/update/verify 全链路移除 | archive/views.py | ✅ |
| 前端-字段管理 | TableList.vue 字段弹窗新增「不同步写回」列（a-checkbox）+ toggleSyncExcluded（调 batchUpdateAttributes）；types Field 加 is_sync_excluded?:boolean；openFieldModal 用 ...f spread 自动带入 | TableList.vue, types/index.ts | ✅ |
| 前端-向导 | ArchiveDetail.vue 第一步「待处理记录」改为「待变更记录」显示 changeCount(insert+update)+副文案「共 N 条记录」（复用已有 changeCount computed） | ArchiveDetail.vue | ✅ |
| 验证 | manage.py check 通过；migrate 0013 OK（预勾选 5 条 D_ETL_TIME）；vue-tsc 零错误；浏览器实跑 /archive/1 dry_run：records_total=975，insert=29，update 946→506，nochange 0→440，**update_etl_only=0**（不再有仅因 ETL 列差异的误判更新），样本更新字段为真实用户编辑 STORE_ADD/LIAISON/STORE_NAME。待变更记录显示 535 条 | - | ✅ |

### 2026-07-23 「流程报错」→ 同步到数据源两阶段重构（第十三轮）

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 澄清 | 报告仅「`流程` 提示报错」无 XPath/日志；页面无「流程」元素。经 AskUserQuestion 确认实指「同步到数据源」流程；用户两诉求：①权限被拒报错要明细 ②同步前先比对数据、输出将执行的变更清单，确认后才执行 | - | ✅ |
| 数据安全隐患 | 【用户关键警告】原 Phase3 是整行 UPDATE（SET 全部列），会覆盖数据源中不在本次变更范围内的字段 | views.py | ✅ |
| 后端-两阶段 | sync_to_source 增 `dry_run` 参数：dry_run=true 只做连接检查+写权限探测+逐字段差异比对，产出 change_plan，绝不写库并提前返回；dry_run=false 才执行。预览不落 ArchiveSyncLog（sync_log=None+_finalize None 守卫） | views.py | ✅ |
| 后端-部分更新 | 主循环重写：只收集有差异字段 record_diff，changed_cols=差异字段名；action 判定 insert/update/nochange + 生成 sql_preview；Phase3 UPDATE 只 SET changed_cols（修复整行 UPDATE 隐患）；Phase4 回读只校验 changed_cols；stats 新增 dry_run/records_nochange/change_plan | views.py | ✅ |
| 后端-错误明细 | 连接/权限失败消息附数据源信息/目标表/探测 SQL/原始 DB 报错/账号提示 | views.py | ✅ |
| 前端-三步向导 | ArchiveDetail.vue：保留单个「同步到数据源」按钮，点击弹出 a-steps 三步向导（①变更确认：连接/写权限检查+变更概览+错误 alert ②数据差异校验：a-table 字段级 旧→新 ③变更语句确认：pre 展示 sqlList）；syncToSource→runSyncPreview(dry_run=true)→confirmSyncExecute(dry_run=false) | ArchiveDetail.vue | ✅ |
| 前端-类型/API | types 新增 SyncChangeItem + SyncStats 扩展 dry_run/records_nochange/change_plan；archive.ts syncToSource 增 dryRun 参数 | types/index.ts, api/archive.ts | ✅ |
| 前端-拦截器 Bug | 【实跑发现】api/index.ts 响应拦截器 reject(new Error(msg)) 丢弃 err.response，且 msg 未取 data.error → 前端 catch 拿不到 sync_stats，弹窗只显示「Request failed with status code 400」。改为保留 error.response 并补 data.error 兜底 | api/index.ts | ✅ |
| 验证 | manage.py check 通过；vue-tsc 零错误；浏览器实跑 /archive/1 点「同步到数据源」→ 弹出三步向导，变更确认步显示 连接检查✓通过 / 写权限检查✗失败 + 完整明细报错（目标表[METADATA].[I_OPT_LS_STO_01_20251114]+探测SQL+SQL Server「拒绝了对对象...的UPDATE权限」+账号[MD_READ]提示），「下一步」按钮预检失败时禁用。❗dev 账号 MD_READ 只读，happy-path（差异表+SQL预览）需可写数据源才能端到端触发 | - | ✅ |

### 2026-07-23 启用/停用逻辑修复（第十二轮）

| 项 | 内容 | 影响文件 | 状态 |
|------|------|---------|------|
| 根因 | 编辑记录会自动置 status=deleted（停用）；但 sync_to_source 只选 status=ACTIVE 记录推送（views.py 原 L311），编辑过的 deleted 记录被排除→永远不被推送也永不恢复，卡在绿色「启用」按钮（用户感受：默认没启用/反了） | - | ✅ |
| 方向 | 用户选 B：保留编辑自动停用，但同步成功后自动把 deleted 恢复为 active（补上原设计缺失的“同步后恢复”环节） | - | ✅ |
| 修复 | sync_to_source：①推送集由 `status=ACTIVE` 改为全部记录 `filter(archive=archive)`；②新增 synced_ids 收集成功推送且回读校验通过的记录；③末尾 `filter(id__in=synced_ids).update(status=ACTIVE, sync_status='synced')` 恢复；删除原按 active 批量置 synced/partial 的逻辑；新增 stats.records_restored | views.py | ✅ |
| 前端 | 同步成功汇总新增「恢复启用 N 条」；SyncStats 新增 records_restored?:number | ArchiveDetail.vue, types/index.ts | ✅ |
| 验证 | manage.py check 通过；vue-tsc 零错误；sync 端点重跑仍返回结构化 400（无崩溃）。❗dev 环境数据源拒绝 UPDATE 权限，同步停在 check_permission 阶段，恢复逻辑需可写数据源才能端到端触发；5890/5891 系前轮测试编辑产物，在 dev 下会保持停用直到同步成功（或手动启用） | - | ✅ |

### 2026-07-23 测试报告 5 项问题修复（第十一轮）

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | 查看页面不需要底部两个按钮 | 记录详情抽屉查看模式（v-if !drawerEditMode）删除底部「查看版本」「编辑记录」按钮，详情页纯只读 | ArchiveDetail.vue | ✅ |
| #2 | 编辑页面顶部状态表格不要 | 编辑模式（v-else）删除顶部状态 a-descriptions（状态/同步状态/当前版本/创建人/修改人/创建/更新时间），直接进业务字段表单 | ArchiveDetail.vue | ✅ |
| #3 | 不要双滚动条 | 编辑模式内层容器去掉 max-height:calc(100vh-400px)+overflow-y:auto，仅保留 padding-right:8px，整体单抽屉滚动 | ArchiveDetail.vue | ✅ |
| #4 | 变更字段要刷新才显示+应含内容 | 版本「变更内容」列（changed_fields）改逐行渲染「字段(蓝)：旧值(红) → 新值(绿)」，宽 500→420；handleSaveDrawer 保存后 loadRecords()+若在看该记录版本则 loadVersions() 自动刷新 | ArchiveDetail.vue | ✅ |
| #5 | 同步数据源大任务：权限/一致性/更新成功检查+结果输出+错误分类+日志 | sync_to_source 重写为分阶段：Phase1 连接检查(ensure_connection)→Phase1b 写权限探测(UPDATE WHERE 1=0)→Phase2 差异比对(SELECT全列逐字段对比,非仅改动字段)→Phase3 推送(UPDATE/INSERT)→Phase4 回读校验(重SELECT比对)；结构化 stats(phase/checks/diffs/records_verified/records_diff/分类errors)；新增 _classify_sync_error(permission/connection/constraint/data_type/verify/runtime)+_finalize_sync_log(写 ArchiveSyncLog details)；前端 doSyncToSource 适配结构化展示 | views.py, ArchiveDetail.vue, types/index.ts, ArchiveList.vue | ✅ |
| 需求追加 | #5 第2步差异比对需比对整行全列（因非目标字段也可能有差异） | Phase2 SELECT 所有待写列现有行，逐字段 str 比对，累加 records_diff+diffs | views.py | ✅ |
| 验证 | vue-tsc 零错误；manage.py check 通过；浏览器实跑逐项确认：#1 查看无按钮（截图 detail-view-readonly.png）、#2/#3 编辑无元信息表+单滚动条（edit-mode-no-metatable.png）、#4「变更内容」列展示字段:旧→新（version-changed-content.png）、#5 同步返回结构化 400（phase=check_permission,connection=ok/write_permission=failed,errors[type=permission] 真实 SQL Server UPDATE 权限拒绝） | - | ✅ |

### 2026-07-23 测试报告 4 项问题修复（第十轮）

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | /archive 操作列不要下拉，要平铺全部按钮 | 推翻 R-003：操作列由「管理记录+更多▾」下拉改回平铺 5 链接（管理记录/API接口/版本历史/从数据源同步/删除），列 fixed:right+nowrap width 380，其他列压缩+ellipsis，scroll.x=1080，删除 onMoreAction/DownOutlined | ArchiveList.vue | ✅ |
| #2 | /archive/1 未同步与启用按钮放一起，启用跟在未同步后 | 记录表操作列重排：同步标签 → 启用/停用 → 详情 → 编辑 → 版本；a-space nowrap，列宽 280→340 | ArchiveDetail.vue | ✅ |
| #3 | 版本差异对比弹窗表格冻格、鼠标下拉不动、字段少 | diff 弹窗 a-modal 加 bodyStyle maxHeight:70vh + overflowY:auto，内容整体滚动、无冻结表头，字段完整可见 | ArchiveDetail.vue | ✅ |
| #4 | 编辑保存后退到详情、记录详情形同虚设、查询编辑应分离 | handleSaveDrawer 保存后关闭抽屉（detailDrawer=false）退出；新增 openDetailDrawer 只读入口 + 操作列「详情」按钮，查询/编辑彻底分离 | ArchiveDetail.vue | ✅ |
| 验证 | vue-tsc 零错误；浏览器实跑确认 4 项全部生效（平铺按钮/顺序/弹窗滚动/详情只读） | - | ✅ |

### 2026-07-23 R-003 整改（ArchiveList 操作列收敛）

| 项 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| R-003 | 操作列由 6 个平铺链接收敛为「管理记录 + 更多▾」（a-dropdown），列宽 500→180，删除改 Modal.confirm 二次确认 | ArchiveList.vue | ✅ |
| 验证 | vue-tsc 零错误；实跑浏览器确认按钮不再竖排、下拉菜单 4 项正常 | - | ✅ |
| 残留 | R-004（DomainList 操作列同类拥挤，P2）待整改 | - | ⏳ |

### 2026-07-23 UXQA 全界面交付验收巡检（第九轮）

| 环节 | 操作 | 结果 |
|------|------|------|
| 源码评定 | 13 页全量结构+尺寸推理（modeling 8 + archive 4 + settings 1） | ✅ |
| 实跑巡检 | browser-use 导航 :3000，archive 重点页 2c 交互状态实跑 | ✅ |
| #1 验证 | Tab 深链 `?tab=versions`/`?tab=apis` 跳转 + 返回按钮 | ✅ 通过 |
| #2 验证 | API 抽屉 900px、3列暴露字段布局 | ✅ 优秀 |
| R-003 | 【新增 P1】ArchiveList 操作列 500px/总宽~1620px 溢出，6按钮竖排换行（#1 深链入口副作用） | ⏳ 待整改 |
| R-004 | 【新增 P2】DomainList 操作列 5 按钮同类拥挤风险 | ⏳ 待整改 |
| 产出 | 刷新 ux-review-archive.md + rectification-list.md（R-003/R-004） | ✅ |

### 2026-07-23 测试报告 5 项问题修复（第八轮）

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | 版本历史/API接口两个 Tab 入口应移到档案管理列表 | 详情页 a-tabs 改为 v-show div（activeTab 由 route.query.tab 初始化，加“← 返回档案记录”）；档案管理列表操作列新增「API接口」「版本历史」深链入口（?tab=apis / ?tab=versions） | ArchiveDetail.vue, ArchiveList.vue | ✅ |
| #2 | API配置抽屉暴露字段区太窄 | 抽屉 width 760→900；暴露字段区 max-height 240→600 | ArchiveDetail.vue | ✅ |
| #3 | 版本回滚+定版无用 | 移除版本表「定版」列、操作列「回滚/定版」、doRollback/doPin 函数 | ArchiveDetail.vue | ✅ |
| #4 | 变更字段应长、操作人应短 | 变更字段 200→500，操作人设 90，操作 160→80 | ArchiveDetail.vue | ✅ |
| #5 | 两个同步按钮加校验+处理机制 | syncSchema（Schema 空拦截）/syncToSource（0 记录拦截）改为 Modal.confirm 二次确认 + 错误汇总弹窗 | ArchiveDetail.vue | ✅ |
| - | vue-tsc 零错误 | - | ✅ |

### 2026-07-23 数据服务API功能（档案维护拆分）

| 编号 | 任务 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| T1 | 后端数据模型 | 新增 ArchiveApi 模型（exposed_fields/filter_conditions/auth_roles/status）+ 迁移 0002_archiveapi | models.py | ✅ |
| T2 | 后端序列化器+视图 | ArchiveApiSerializer + ArchiveApiViewSet（CRUD + data action 按筛选返回启用数据）+ 路由 + admin；ArchiveListSerializer 增加 api_count | serializers.py, views.py, urls.py, admin.py | ✅ |
| T3 | 前端类型+API | 新增 ArchiveApi/ApiFilterCondition/ArchiveApiData 类型 + archiveApiApi 封装 + Archive.api_count | types/index.ts, api/archive.ts | ✅ |
| T4 | 导航+路由拆分 | 档案维护 → 档案管理(/archive)+档案列表(/archive/browse)+操作日志；browse 路由置于 :id 前 | MainLayout.vue, router/index.ts, ArchiveList.vue | ✅ |
| T5 | 档案详情API配置 | 新增“API接口”Tab（列表+新建/编辑抽屉：选字段/筛选/角色部门授权/启停） | ArchiveDetail.vue | ✅ |
| T6 | 档案列表只读浏览 | 新建 ArchiveBrowse.vue：域分类→档案下拉→API列表→抽屉看字段+数据+权限+筛选 | ArchiveBrowse.vue（新建） | ✅ |
| T7 | 验证 | makemigrations+migrate+check 通过；vue-tsc 零错误 | - | ✅ |

### 2026-07-23 测试报告 4 项问题修复（第七轮）

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #2 | 列锁定+同步状态移入操作列 | #列 fixed:left，操作列 fixed:right，sync_status 合并到操作列 | ArchiveDetail.vue | ✅ |
| #3 | 编辑后自动停用 | 更新 serializer，数据变更后自动设 status=deleted | serializers.py | ✅ |
| #4 | 版本历史显示变更字段 | 版本表增加“变更字段”列，展示 change_summary | ArchiveDetail.vue | ✅ |
| #5 | 同步到数据源报错 | 修复 full_table 变量作用域，移到循环外定义 | views.py | ✅ |
| - | vue-tsc + manage.py check 零错误 | - | ✅ |
### 2026-07-22 表头横滚问题修复（第六轮）

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | 横向滚动时表头跟着滚动走 | 加回 scroll.x（不加 fixed），让表格在容器内横滚 | ArchiveDetail.vue | ✅ |
| - | vue-tsc 零错误 | - | ✅ |
### 2026-07-22 测试报告 4 项问题修复（第五轮）

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | 同步状态冻格导致页面漂移 | 移除 sync_status 和 action 列的 fixed: 'right' | ArchiveDetail.vue | ✅ |
| #2 | 新增记录抽屉样式不统一 | 改为 a-descriptions + h4分组风格，与编辑抽屉一致 | ArchiveDetail.vue | ✅ |
| #3 | 缺少同步到数据源功能 | 后端新增 sync-to-source API，前端增加按钮 | views.py + archive.ts + ArchiveDetail.vue | ✅ |
| #4 | 状态列重复，移入操作列 | 移除独立状态列，操作列改为启用/停用切换 | ArchiveDetail.vue + serializers.py | ✅ |
| - | vue-tsc + manage.py check 零错误 | - | ✅ |
### 2026-07-22 测试报告 6 项问题修复（第四轮）

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | 表格锁顶，滚动无效 | 移除 scroll.x，表格改为正常滚动 | ArchiveDetail.vue | ✅ |
| #2 | 编辑保存前应显示变更预览 | 新增 editChanges computed 比较原值/新值，保存前展示变更摘要表格 | ArchiveDetail.vue | ✅ |
| #3 | ID列无用 | 移除 ID 列、ID 点击事件、抽屉中 ID 行 | ArchiveDetail.vue | ✅ |
| #4 | 二级表头不明显 | CSS 给分组父列头加背景色 #e6f7ff + 蓝色下边框 | ArchiveDetail.vue | ✅ |
| #5 | 同步状态应冻格在右侧 | sync_status 列加 fixed: 'right' | ArchiveDetail.vue | ✅ |
| #6 | 新增记录弹窗太丑 | 弹窗改为抽屉 + a-card 分组展示字段 | ArchiveDetail.vue | ✅ |
| - | vue-tsc 零错误 | - | ✅ |

### 2026-07-22 测试报告 6 项问题修复（第三轮）

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | 编辑抽屉和ID抽屉视觉风格不一致 | 编辑模式改用 a-descriptions + h4分组，与查看模式统一视觉风格 | ArchiveDetail.vue | ✅ |
| #2 | 表头要中国式分组（二级表头） | dynamicColumns 按 groupedSchema 构建嵌套 children，分组名作父列跨字段 | ArchiveDetail.vue | ✅ |
| #3 | 版本历史应只记录有数据变化的版本 | _upsert_records_from_rows 更新前比较 merged_data == existing.data，无变化跳过 | archive/views.py | ✅ |
| #4 | 档案名称列太宽 | name 列设 width: 400 | ArchiveList.vue | ✅ |
| #5 | Schema版本列表头换行 | 列宽 100→120 | ArchiveList.vue | ✅ |
| #6 | 档案名称超链接去掉 | 移除 <a> 标签，改纯文本 | ArchiveList.vue | ✅ |
| - | vue-tsc 零错误 + manage.py check 通过 | - | ✅ |

### 2026-07-22 测试报告 3 项问题修复（第二轮）

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | ArchiveList 操作列按钮换行，前面格子太空 | 操作列 width 240→500 | ArchiveList.vue | ✅ |
| #2 | 39个字段只显示15个 | 移除 DATA_COLUMN_MAX=15 限制，displaySchemaFields 返回全部 schema | ArchiveDetail.vue | ✅ |
| #3 | 编辑按钮要参考ID展示效果，带上编辑字段功能 | 编辑按钮改为打开抽屉编辑模式（drawerEditMode），抽屉内支持查看/编辑双模式切换，编辑模式按分组展示可编辑字段 | ArchiveDetail.vue | ✅ |
| - | vue-tsc 零错误 | - | ✅ |

### 2026-07-22 测试报告 5 项问题修复

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | ArchiveList 创建时间显示 ISO 格式 | 导入 formatDateTime，添加 customRender；列宽 170→180 | ArchiveList.vue | ✅ |
| #2 | ArchiveDetail 动态列仅展示 10/39 字段 | DATA_COLUMN_MAX 10→15，DATA_COLUMN_WIDTH 140→160 | ArchiveDetail.vue | ✅ |
| #3 | 记录弹窗太小（720px） | width 改为 calc(100vw-120px)，max-height 改为 calc(100vh-200px) | ArchiveDetail.vue | ✅ |
| #4 | 日期字段显示格式不对 | formatCellValue 增加 date/datetime 格式化；openEditRecord 转换日期值为 picker 可识别格式 | ArchiveDetail.vue | ✅ |
| #5 | “同步模型”按钮文案歧义 | 改为“从数据源同步” | ArchiveList.vue, ArchiveDetail.vue | ✅ |
| - | vue-tsc 零错误 | - | ✅ |

### 2026-07-22 UXQA 交付验收关（档案与主表架构页面）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | UXQA 三类巡检：结构(2a)+尺寸推理(2b)+交互状态(2c未实跑) | output/uxqa/ux-review-archive.md | ✅ |
| R-001 | 主键列 160px ellipsis 截断关键信息 | TableList.vue primary_keys 列 | ✅ P2 已闭环 |
| R-002 | 动态列仅展示 6/29 字段，信息密度偏低 | ArchiveDetail.vue dynamicColumns | ✅ P2 已闭环 |

### 2026-07-22 主表架构实现

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| Task 1 | Table 模型添加 is_primary 字段；Domain 添加 get_primary_table() 方法；Table 添加 set_as_primary() 方法 | modeling/models.py, 0012_table_is_primary.py | ✅ |
| Task 2 | TableViewSet 添加 set_primary action；Serializer 添加 is_primary 字段 | modeling/views.py, serializers.py | ✅ |
| Task 3 | TableList.vue 添加“主表”列和“设为主表”操作按钮；API 添加 setPrimary 方法；Type 添加 is_primary | TableList.vue, modeling.ts, types/index.ts | ✅ |
| Task 4 | _sync_data_from_sources 重构：获取主表主键 → 主表优先处理 → 动态主键匹配 | archive/views.py | ✅ |
| Task 5 | 设置门店域主表为 I_OPT_LS_STO_01_20251114 | 数据迁移 | ✅ |
| Task 6 | 验证：975 条唯一记录，29 字段，主键匹配正确 | - | ✅ |

### 2026-07-22 档案数据合并逻辑修复

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | 记录数据被覆盖而非合并：每张表的数据替换前一张表的，导致记录只有 17 个字段 | 修复 _upsert_records_from_rows：用 STORE_NO 建索引快速匹配，用 `{**existing.data, **record_data}` 合并数据 | archive/views.py | ✅ |
| #1 | 匹配效率低：O(n²) 遍历所有记录 | 改为用 STORE_NO 字典索引 O(1) 匹配 | archive/views.py | ✅ |
| - | 验证：975 条唯一记录，每条 29 个字段，100% 包含多表数据 | - | ✅ |

### 2026-07-22 档案 schema 字段完整性修复

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | 同步后字段不对：schema 只有 9 个 StandardField，缺少大量物理字段 | 新增 _generate_schema_from_domain() helper，遍历所有 active 物理字段去重生成 schema，StandardField 信息优先 | archive/views.py | ✅ |
| #1 | 数据拉取字段映射不完整 | _sync_data_from_sources 增加物理字段直接映射逻辑，非 StandardField 字段也能正确映射 | archive/views.py | ✅ |
| - | 验证：schema 从 9 字段 → 39 字段，包含地址/省份/城市/联系人等全部字段 | - | ✅ |
| - | vue-tsc 零错误 + manage.py check 通过 | - | ✅ |

### 2026-07-22 档案模块5项测试问题修复

| 编号 | 问题 | 操作 | 影响文件 | 状态 |
|------|------|------|---------|------|
| #1 | 同步模型后没有数据 | 后端 sync-schema 增加数据拉取：连接数据源表查询实际数据，创建/更新 ArchiveRecord | archive/views.py | ✅ |
| #1 | 同步反馈不清晰 | 前端同步按钮显示同步统计（表数/新增记录/更新记录） | ArchiveDetail.vue, ArchiveList.vue | ✅ |
| #2 | 操作日志按钮位置不当 | 移除 ArchiveList 页头“操作日志”按钮 | ArchiveList.vue | ✅ |
| #3 | 新建档案重复报错 | 后端 ArchiveCreateSerializer 增加 validate_domain 校验；前端可选域过滤已有档案的域 | archive/serializers.py, ArchiveList.vue | ✅ |
| #4 | 筛选控件无用 | 移除 ArchiveList 筛选卡片（域选择/状态/查询按钮） | ArchiveList.vue | ✅ |
| #5 | 版本列显示但不可见 | 已在上一轮重构中解决：版本信息在详情抽屉中展示，操作列有“版本”入口 | ArchiveDetail.vue | ✅ |
| - | vue-tsc 零错误 + manage.py check 通过 | - | - | ✅ |

### 2026-07-22 档案详情页增强（记录数据管理）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | 记录列表动态列：根据 schema 前6个字段生成数据列，直接展示业务数据 | ArchiveDetail.vue | ✅ |
| - | 记录详情抽屉：点击记录 ID 打开抽屉，按分组展示所有字段值 | ArchiveDetail.vue | ✅ |
| - | 智能表单弹窗：根据字段类型渲染组件（input/number/date/switch/textarea），按分组展示 | ArchiveDetail.vue | ✅ |
| - | 版本对比差异中字段名显示中文名 | ArchiveDetail.vue | ✅ |
| - | vue-tsc 零错误 | - | ✅ |

### 2026-07-22 全模块 API 测试 + UXQA 巡检

| 测试项 | 端点/页面 | 状态 |
|--------|----------|------|
| Archive API (16端点) | archives/records/versions/compare/rollback/pin/operation-logs/sync-logs | ✅ 全部通过 |
| Modeling API (关键端点) | domains/tables/fields/field-groups/standard-fields | ✅ 全部通过 |
| 前端 TypeScript 编译 | vue-tsc --noEmit | ✅ 零错误 |
| UXQA 档案列表页 | /archive | ✅ 结构正常 |
| UXQA 档案详情页 | /archive/:id | ✅ 结构正常 |
| UXQA 域管理页 | /modeling/domains | ✅ 结构正常 |
| UXQA 数据源管理页 | /settings/data-sources | ✅ 结构正常 |

**修复项：**
- urls.py 残留旧代码导致 archives 路由丢失 → 已清理
- ArchiveCreateSerializer 响应缺少 schema/schema_version → 已补全
- ArchiveRecordCreateSerializer 响应缺少 version/sync_status → 已补全
- ArchiveRecordUpdateSerializer 响应缺少 version 等只读字段 → 已补全

### 2026-07-22 UI修复5项问题（用户测试报告）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| Issue#1 | DomainList列宽调整（名称220→260, 编码180→200, 操作320→380） | DomainList.vue | ✅ |
| Issue#2 | TableList操作列加宽(160→200)+按钮间距(a-space size=16) | TableList.vue | ✅ |
| Issue#3 | 字段管理弹窗列宽调整（编码160→180, 英文名160→200） | TableList.vue | ✅ |
| Issue#4 | ER图全屏切换按钮（移除缩放工具栏，新增切换按钮，全屏时隐藏映射列表） | DomainFieldMapping.vue | ✅ |
| Issue#5 | 标准字段物理表tooltip换行+编号显示 | DomainFieldConfig.vue | ✅ |
| - | vue-tsc 零错误 | - | ✅ |

### 2026-07-22 档案模块代码修复（对齐新模型结构）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | serializers.py 完全重写（Archive/Record/Version/SyncLog/OpLog） | archive/serializers.py | ✅ |
| - | views.py 完全重写（ArchiveViewSet + RecordViewSet + SyncLog + OpLog + pin） | archive/views.py | ✅ |
| - | urls.py 增加 archives/sync-logs 路由 | archive/urls.py | ✅ |
| - | admin.py 恢复注册 5 个新模型 | archive/admin.py | ✅ |
| - | 前端 types/index.ts 增加 Archive/ArchiveSchemaItem/SyncLog 类型 | types/index.ts | ✅ |
| - | 前端 api/archive.ts 拆分为 archiveApi + archiveRecordApi + syncLogApi | api/archive.ts | ✅ |
| - | ArchiveList.vue 重写（展示档案列表而非记录） | ArchiveList.vue | ✅ |
| - | ArchiveDetail.vue 重写（档案详情+记录管理+版本历史） | ArchiveDetail.vue | ✅ |
| - | OperationLog.vue 修复（domain→archive） | OperationLog.vue | ✅ |
| - | migration 执行成功 + manage.py check 通过 | - | ✅ |
| - | vue-tsc 零错误 | - | ✅ |

### 2026-07-22 reqa 档案模块增量概念设计

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | 需求澄清：3个需求（REQ-013/014/015） | requirements.json | ✅ |
| - | 故事线：3条故事线 | storylines/REQ-013/014/015.md | ✅ |
| - | 业务流程：3个流程图 | business-flow.md | ✅ |
| - | 功能清单：archive 重写（F-101~F-112） | concept-feature-list.md | ✅ |
| - | 概念架构+追溯矩阵 | concept-architecture.md | ✅ |
| - | 路由索引更新 | route_index.md | ✅ |

### 2026-07-21 用户4项需求增强（主键列/ER缩放/分页/字段去重）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| 需求3 | 自定义分页 StandardPagination（page_size_query_param+max_page_size=100000） | config/pagination.py, config/settings.py | ✅ |
| 需求3 | 前端管理类列表默认拉全量（withFullPage 注入 page_size） | api/modeling.ts | ✅ |
| 需求1 | 表列表增加"主键"列（serializer get_primary_keys + 前端 gold tag） | serializers.py, TableList.vue | ✅ |
| 需求2 | ER图缩放工具栏（放大/缩小/适应/1:1/复位 + scale事件同步百分比） | DomainFieldMapping.vue | ✅ |
| 需求4 | 新增 FieldEquivalenceGroup 等价组模型 + Field.equivalence_group 外键 | models.py, migration 0009 | ✅ |
| 需求4 | AI去重检测（code归一化启发式 + LLM优先） | ai_service.py | ✅ |
| 需求4 | detect-duplicates/apply-equivalence action + FieldEquivalenceGroupViewSet | views.py, urls.py, serializers.py | ✅ |
| 需求4 | 字段管理新增"字段去重"Tab（检测建议勾选+应用+等价组解散） | DomainFieldConfig.vue, api/modeling.ts | ✅ |
| 需求4 | 分组Tab改造：等价组折叠成一行“标准字段”（⚓标识+成员tag+拖拽联动） | serializers.py, views.py, DomainFieldConfig.vue | ✅ |
| - | vue-tsc 零错误 + migration 0009 已执行 | - | ✅ |

### 2026-07-21 关系管理功能增强

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | 恢复 n/m 表已配置进度标识 | DomainFieldMapping.vue | ✅ |
| - | 映射列表主键字段黄色标识（⚿图标+黄色文字） | DomainFieldMapping.vue | ✅ |
| - | 目标字段支持联合主键虚拟选项 | DomainFieldMapping.vue | ✅ |
| - | 目标表下拉排除源表 | DomainFieldMapping.vue | ✅ |
| - | ER图联合主键显示为虚拟字段（边去重+组合标签） | DomainFieldMapping.vue | ✅ |
| - | ER图字段中文名优先展示（两行布局） | DomainFieldMapping.vue | ✅ |
| - | 关系管理列表改回一行=一条映射关系（不再按表对合并） | DomainFieldMapping.vue | ✅ |
| - | vue-tsc 编译零错误 | - | ✅ |

### 2026-07-21 Bug 修复（进度条堆叠 + ER图中文名）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| Bug1 | 修复进度条与按钮堆叠：a-space 添加 :size="16"，进度条宽度减到 180px | DomainFieldMapping.vue | ✅ |
| Bug2 | ER图字段中文名不显示：节点宽度从 280px 加到 320px | DomainFieldMapping.vue | ✅ |
| - | prjm/uxqa 责任分析：uxqa 未实跑漏检视觉问题，prjm 未做尺寸推理点对点盲修 | - | ✅ |

### 2026-07-21 数据源配置修复 + 测试连接

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| Bug2 | 修复数据源数据丢失：config/settings.py 末尾自动导入 local_settings.py | config/settings.py | ✅ |
| Bug1 | 新增测试连接功能：后端 test-connection API（已有/新建均支持） | views.py | ✅ |
| Bug1 | 新增测试连接功能：前端弹窗底部增加「测试连接」按钮 + 结果提示 | DataSourceList.vue, api/modeling.ts | ✅ |
| - | 动态数据库连接补全 Django 6.0+ 必需配置项（ATOMIC_REQUESTS/TIME_ZONE/CONN_MAX_AGE/CONN_HEALTH_CHECKS） | views.py | ✅ |
| - | SQL Server 连接增加 OPTIONS driver 配置 | views.py | ✅ |

### 2026-07-21 数据源驱动扩展（SQL Server + Oracle）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | models.py DBType 增加 SQLSERVER/ORACLE | models.py | ✅ |
| - | views.py 连接引擎映射 + schema/表查询适配 4 种数据库 | views.py | ✅ |
| - | migration 0006 扩展 db_type choices | 0006_alter_datasource_db_type.py | ✅ 待执行 |
| - | 前端 types + DataSourceList 下拉+端口自动切换 | types/index.ts, DataSourceList.vue | ✅ |
| - | 安装 mssql-django + oracledb | venv | ✅ |

### 2026-07-21 UXQA 整改（R-007~R-010）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| R-007 | FieldMapping.vue 创建时间加 formatDateTime | FieldMapping.vue | ✅ |
| R-008 | FieldMapping.vue 新建映射按钮 <2 表禁用 | FieldMapping.vue | ✅ |
| R-009 | TableList.vue 展开行改为只读展示（移除注释编辑+保存按钮） | TableList.vue | ✅ |
| R-010 | FieldClassification.vue 重命名后加提示 | FieldClassification.vue | ✅ |

### 2026-07-21 UXQA 第四轮交付验收关（新增尺寸推理+交互状态巡检）

| 时间 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | UXQA 三类巡检全覆盖：结构(2a)+尺寸推理(2b)+交互状态(2c) | output/uxqa/ux-review-modeling.md | ✅ |
| - | 新发现 R-010（FieldClassification 分组重命名未持久化） | output/uxqa/rectification-list.md | 🔴 待闭环 |
| - | 2c 交互状态测试：ER 图位置持久化验证通过 | - | ✅ |
| - | 2b 尺寸推理：所有页面/弹窗/表格尺寸合理 | - | ✅ |

### 2026-07-21 Bug 修复（用户反馈）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| Bug1 | 域列表操作列增加「关系管理」「字段管理」按钮 | DomainList.vue | ✅ |
| Bug2 | 字段管理页面最小高度改为 viewport 自适应 | DomainFieldConfig.vue | ✅ |
| Bug3 | ER图位置持久化：moved+debounce → dragend + beforeUnmount 兗底 | DomainFieldMapping.vue | ✅ |

### 2026-07-21 UXQA 第三轮交付验收关

| 时间 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | UXQA 实跑巡检（4 主页面 + 2 弹窗 Tab） | output/uxqa/ux-review-modeling.md | ✅ |
| - | 新发现 3 项（R-007 P2, R-008 P3, R-009 P3） | output/uxqa/rectification-list.md | 🔴 待闭环 |

### 2026-07-20 UXQA 整改（darc 执行）

| 编号 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| R-001 | DomainList.vue 创建时间格式统一 | DomainList.vue | ✅ |
| R-002 | DomainList.vue 操作列增加「管理表」入口 | DomainList.vue | ✅ |
| R-003 | TableList.vue 调整提示文字 | TableList.vue | ✅ |
| R-004 | TableList.vue 数据预览提示改进 | TableList.vue | ✅ |
| R-005 | TableList.vue Excel上传后自动预览 | TableList.vue | ✅ |
| R-006 | DomainFieldConfig.vue 左栏滚动条样式 | DomainFieldConfig.vue | ✅ |

### 2026-07-20 UXQA 交付验收关

| 时间 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | UXQA 实跑巡检（4 页面） | output/uxqa/ux-review-modeling.md | ✅ |
| - | 生成整改清单（6 项：2×P1 + 4×P2） | output/uxqa/rectification-list.md | ✅ |

### 2026-07-20 prjm 项目检查

| 时间 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | prjm 初始化 .ai/ 目录 | .ai/constitution.md, session.md, route_index.md | ✅ |
| - | 创建 prjm rule 铁律 | .qoder/rules/prjm.md | ✅ |
| - | 项目状态检查 + 文档同步 | .ai/*, design-diary-modeling.md | ✅ |

### 2026-07-17 第二轮增强（域管理功能增强）

| 时间 | 操作 | 影响文件 | 状态 |
|------|------|---------|------|
| - | T1 后端 Table 模型扩展（er_node_x/y） | models.py, serializers.py, migration 0005 | ✅ |
| - | T2 后端 Excel 解析 + 本地建表 | excel_service.py, ai_service.py, views.py | ✅ |
| - | T3 后端数据源 schema 浏览 | views.py (list_schemas) | ✅ |
| - | T4 前端类型与 API 扩展 | types/index.ts, api/modeling.ts | ✅ |
| - | T5a 字段查看弹窗 | TableList.vue | ✅ |
| - | T5b 新建表对话框重构 | TableList.vue | ✅ |
| - | T5c/T7 创建时间格式统一 | utils/date.ts, TableList.vue, DomainFieldMapping.vue | ✅ |
| - | T6 ER图位置持久化前端 | DomainFieldMapping.vue | ✅ |
| - | T8 验证（migration + vue-tsc） | - | ✅ |
| - | BUG修复 ATOMIC_REQUESTS 500 | config/settings.py, local_settings.py | ✅ |
| - | 字段管理弹窗调整（去长度/必填/保存，加数据预览） | TableList.vue | ✅ |
| - | Excel文件列表改表格形式 | TableList.vue | ✅ |
