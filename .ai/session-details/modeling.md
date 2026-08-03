# 操作详情 — modeling 模块（倒序，最新在前）

> 由 rule §3 双层留痕追加；检索方式：按「第N轮」或功能标签 grep。

### 第八十五轮（2026-07-30）标签：/modeling、同步、一致性、主字段、数据源

- **更早操作**：2026-07-30 — 第八十五轮：组合字段主字段机制全栈落地（用户三条背景：①设主表后组合字段默认用主表成员作主字段（用于档案更新）②主字段=数据源头其余成员仅作检查③组合字段必须设一个主字段；AskUserQuestion 三决策：一致性=刷新时检测+告警不阻断、兑底=**无主表成员时留空强制人工设置（非推荐项，用户明确选择）**、主表变更=仅自动分配的跟随人工指定不动）。根治旧缺陷：原 _upsert 按表循环 {**旧,**新} 后写覆盖→组合字段实际「最后处理的表」胜出而非主表。后端：modeling/models.py StandardField 加 primary_field(FK Field SET_NULL)/primary_field_manual+auto_assign_primary_field()（active成员仍有效不动→主表成员兑底→置空清manual；用 filter(pk).update 绕 save 钩子），Table.set_as_primary 加自动分配跟随循环，迁移0026（AddField×2+RunPython 存量取主表成员无则留空）；modeling/views.py 4 处成员变更钩子（apply_standards/create/add_member/remove_member）+set-primary-field action（field_id=id→manual=True，null→清标记重分配；非有效成员400）+members_distinct/standard_fields 聚合输出 table_is_primary/is_primary_field/primary_field_id/label(表名.编码)/manual；serializers 两处同步（primary_field 只读只能走专用端点）。archive/views.py：_validate_primary_fields 模块函数（域内活跃且有成员的 SF 必须有效主字段），_sync_data_from_sources/_preview_data_changes 开头拦截（stats.errors+primary_field_missing）；_build_code_to_physical 重写：已设主字段仅映射主字段成员（primary_locked 防兑底追加）；新增 _build_code_checks/_collect_check_values/_run_consistency_check 三方法（每表拉取后按主键采集、字符串归一比对，产出 checked_fields/mismatch_count/mismatch_records/samples≤20 挂 stats.consistency_check）。前端：api/modeling.ts 类型+setPrimaryField；DomainFieldConfig.vue 组合字段表金色「主字段/主表」Tag+成员抽屉主字段卡片金边框+「设为主字段」链接（setPrimaryMember）+属性配置 Tab「主字段」列（label+自动/手动小标，未设置红标可点开抽屉）；ArchiveDetail.vue showConsistencyWarning（Modal.warning 展示不一致样本，doRefreshData/doSyncSchema 各调一次）。验证：migrate 0026 OK（存量 STORE_NO/STORE_NAME 自动分到主表成员 68/69）、check 0 issues、vue-tsc 0 errors、API 实测（非法成员400✓人工指定manual=True✓null恢复自动✓置空后 refresh-preview 拦截文案✓refresh-data 一致性检查真实生效：2字段/33记录/69处不一致含样本✓）、Browser 端到端 6 步全 PASS 无控制台错误（测试残留已恢复自动态）。constitution 登记主字段三决策，design-diary-modeling v9 已登记

### 第八十三轮（2026-07-30）标签：/archive/5、/modeling/domains/8/fields、同步、计算字段、版本

- **更早操作**：2026-07-30 — 第八十三轮：测试问题报告 10 项修复（/archive/5 九项 + /modeling/domains/8/fields 一项；AskUserQuestion 四问锁定：①刷新工作流=预检弹窗②标签范围=**只删同步标保留人工橙标**（未选推荐的全删）③抽屉分列=1100px 三列④计算字段分组=全链路改造）。后端 archive/views.py：①问题4 _upsert 更新分支版本快照 change_summary 补 changed_fields[{field,old,new}]（版本表变更内容列可渲染新旧值）；②问题1+7 新增 refresh_preview action（GET refresh-preview，dry-run 零写入：schema diff 按 code 对比 added/removed/changed 逐属性 name/type/ownership/group_path + _preview_data_changes 试算：拉源行→SimpleNamespace 模拟 _merge_record_data→would_create/update/deactivate+changes_sample≤20），_build_code_to_physical 从 _sync_data_from_sources 抽出共用；③问题10 _generate_schema_from_domain 重写 entries+sort_key 统一排序（物理 (组序,0,sort_order,id)、有分组计算字段 (组序,1,execution_order,id)、未分组兜底「计算字段」虚拟组）。modeling：ComputedField 加 group FK（迁移0024）+序列化器 group/group_name。前端 ArchiveDetail.vue 五批：时间格式化（版本表 operated_at+抽屉创建/更新时间 formatDateTime）、操作列删 sync 标签+停用改 a-switch、详情抽屉只删同步蓝标（lineage source!=='sync' 才显）+编辑抽屉所有权标注反转（ownership!=='source'&&source!=='computed' 标橙「以我为准」）、抽屉 700→1100px+groupedSchemaColumns 按 level1 根分组分列+schemaGridStyle grid 最多3列（新增记录抽屉保持单列）、页头合并「立即刷新」+预检弹窗（doRefreshPreview→confirmRefresh 分流 doSyncSchema/doRefreshData，无变化 message 提示不弹窗）；api/archive.ts 加 refreshPreview。DomainFieldConfig.vue：loadGroupTabData 三并发并入计算字段行（kind='computed' key=computed-{id} 橙「计算」标），changeFieldGroup/onDropToGroup 分流 computedFieldApi.patch({group})；api/modeling.ts 类型同步。验证：check 0 issues、migrate 0024 OK、vue-tsc 0 errors、refresh-preview 实测 200（检出 5 字段分组/名称变更、数据无变化——正是问题7 场景）、Browser 端到端 8/8 PASS 无控制台错误。⚠经验：重启后端时旧进程（127.0.0.1:8000）与新进程（0.0.0.0:8000）并存致 localhost 请求达旧进程出现 404 假象——Windows 下两进程可同端口不同地址共存，重启后必须 Get-NetTCPConnection 核对监听唯一。constitution 登记 3 条决策（v11 两条+计算字段分组），design-diary-archive v11 已登记

### 第七十一轮（2026-07-28）标签：/archive/5、同步、计算字段、去重、抽屉

- **更早操作**：2026-07-28 — 第七十一轮：测试报告两题（/archive/5）。问题1+2（分组层级顺序与建模不一致）用户选方案B真嵌套层级渲染：后端 _generate_schema_from_domain 按 FieldGroup 树 DFS 遍历建 group_order/group_paths（children_map+_walk 递归），字段 Python 侧 sorted 按 (DFS序，未分组10**9排尾,sort_order,id)，schema 三分支（sf/普通/计算）均加 group_path（计算字段=['计算字段']）；前端 types 加 group_path?: string[]，ArchiveDetail 四处渲染全改：schemaGroupTree（按 group_path 建树，nodeMap 按 path.join(' / ') 去重保插入序）→groupedSchemaBlocks（DFS 展平块：父标题在前子紧随），详情/编辑/新增抽屉嵌套标题（groupTitleStyle 三级视觉：蓝15px粗左边框/灰14px/浅灰13px，缩进(level-1)*16px），记录表格 buildGroupColumns 递归多级表头，API 配置抽屉层级缩进（无字段纯父分组只显标题）。验证：vue-tsc 0 errors；档案5 重跑 sync-schema 200，29 字段顺序实测=期望 DFS 序（门店信息→门店信息/联系信息→门店信息/状态信息→地理位置→地理位置/经纬度→地理位置/省市区→(未分组)→计算字段），group_path 无缺失。问题3（sync-schema 无条件覆盖用户修正，根因 _upsert_records_from_rows）用户选直接做完整 MDM 机制→reqa 增量模式产出 REQ-018：四项澄清决策（扩展 archive 模块/三级存活规则字段级/**全部冲突人工审查不自动裁决**/手动回写但 sync-to-source 两阶段重做为字段级）；产出：requirements.json 追加 REQ-018（4场景+BR-018-1~6）、storylines/REQ-018.md（7步旅程）、concept-feature-list F-114~F-119（同步比对引擎/修正保护登记/冲突审查队列/存活规则建议/字段级回写/字段级血缘）、business-flow 流程四 MDM 泳道图、concept-architecture 四处更新（实现路径 archive-mdm 开发顺序6/7/8、追溯 10/10）。本轮未改同步代码，constitution 已登记两条决策

### 第六十九轮（2026-07-28）标签：/modeling/domains/8/fields、同步、计算字段、去重、弹窗

- **更早操作**：2026-07-28 — 第六十九轮：测试报告 4 项（/modeling/domains/8/fields）。Browser 实跑+源码双证据定位：①「依赖图」按钮（字段分类 Tab→计算字段工具栏）经确认彻底删除（按钮+showDependencyGraph 函数，dependencyGraph API 定义保留），批量重算按钮保留；②试算弹窗测试值下拉 No data：根因是引用字段 distinct_values=None 时 _build_param_space_from_distinct 直接 [''] 占位不查库（同类模式缺失：_ensure_distinct_cache 已在 AI查重/抽屉/刷新三处使用唯独试算漏接）；经确认治本：去重缓存工具（ENGINE_MAP/json_safe/fetch_distinct_values/ensure_distinct_cache）从 views.py 抽到新模块 distinct_cache.py，views 改 import 别名兼容，computed_service 按需 ensure（失败降级占位）；③属性配置 Tab 新增「数据去重内容」列（默认值与成员数之间，tag前3+tooltip全量，与字段分类 Tab 同款）：后端 standard-fields 聊 equiv=成员并集/solo=自身缓存限50条，serializer+前端类型+AttrRow 同步；④删除属性表 th9/th10「释放到档案」「启用」两列（列+bodyCell 模板，saveAttrField 仍传存量值后端字段保留）。事故与修复：首次替换误删「批量重算」按钮立即发现并恢复。验证：vue-tsc 0 errors；APIClient 实测 standard-fields 200/28行全带 distinct_values（27非空）、trial-calculate 200 不炸（MD_STATUS 引用不存在表属脏数据正常降级）。debug-diary 登记 BUG-2026-0728-02

### 第六十八轮（2026-07-28）标签：计算字段、Bug

- **更早操作**：2026-07-28 — 第六十八轮（Bug）：计算字段填 IFS(...) 表达式点保存失败。事实核查：IFS/AND/NOT/ISBLANK/=/TRUE 均被 formula_engine 支持，APIClient 实测同表达式换新编码 201 成功；真根因双层：①编码 store_status 被已废弃同名字段占用触发 unique_together('domain','code') → DRF 返回 non_field_errors；②全前端 catch 只读 e.response?.data?.error 吞掉 DRF 校验错误只显笼统「保存失败」。经 AskUserQuestion 选定：治本全局错误解析工具 + 后端明确提示指引恢复。整改：①新建 frontend/src/utils/apiError.ts extractApiError(e)（error→detail→message→non_field_errors→字段级错误链式解析），全前端 31 处 catch 替换（7 文件：DomainFieldConfig 15/FormulaEditor 7/TableList 13/TrialCalculation 2/DomainFieldMapping 1/TechFunctions 3/ArchiveDetail 2）；②后端 ComputedFieldViewSet 新增 _code_conflict_response 前置校验（create/update 均拦）：废弃占用→「编码已被废弃字段「xx」占用：请到左栏废弃字段分类恢复它，或换一个编码」，活跃占用→提示已存在。验证：vue-tsc 0 errors；APIClient 复测 T1（IFS+新编码）201、T2（重复编码）400 且返回新指引文案。新建 output/darc/debug-diary-modeling.md 登记 BUG-2026-0728-01

### 第六十七轮（2026-07-28）标签：同步、去重、弹窗、测试报告

- **更早操作**：2026-07-28 — 第六十七轮：测试报告 3 项。①试算窗口默认列出数据预览：TrialCalculation.vue watch(open) 构建参数行后自动调用 autoEnumerate()，打开弹窗即展示试算结果并回填测试值；测试值保持 tags 模式（下拉+可手输，经 AskUserQuestion 确认），下拉选项改为字段去重样本 ∪ 枚举回填值（autoEnumerate 内将枚举值并入 row.distinct_values，保证选项始终有值）；②删除「自动枚举」按钮（默认自动执行后失去存在意义），同步改掉 0 组合警告文案与 runCalculation 提示中对该按钮的引用；③停用/删除语义：事实核查确认「停用」实为 status='discarded'，字段进左栏「废弃字段」分类可恢复、公式保留并非物理删除，但按钮叫「停用」且从列表消失造成"被删除"误解；经 AskUserQuestion 用户选「维持现状仅改文案」：DomainFieldConfig.vue 按钮改「废弃」、popconfirm 改「废弃后字段移入左栏废弃字段分类，公式保留、可随时恢复」、成功提示改「已废弃，可在左栏废弃字段分类中恢复」。泛化检查：全库其余 17 处「停用」均为真实启/停切换语义（表/字段/档案记录/API/AI 配置）无同类待修点。验证：vue-tsc 0 errors；Browser 实跑：废弃文案/气泡✓、无自动枚举按钮✓、打开即自动出试算结果✓；测试值回填/下拉选项在 MD_STATUS 上为空属预期（该字段为上轮已定性脏数据，引用不存在的门店表无可枚举取值；store_status 已不在活跃列表无干净字段可正向验证），再次建议用户修复或删除 MD_STATUS

### 第六十四轮（2026-07-28）标签：/modeling、测试报告

- **更早操作**：2026-07-28 — 第六十四轮：测试报告 4 项（FormulaEditor）。①删除「数据预览」按钮：onExpressionChange 已有 800ms 防抖自动预览，工具栏按钮冗余，仅保留格式化/验证公式（handlePreviewData 函数保留供自动预览/全部切换调用）；②格式化重写为代码编辑器风格：占位符保护→压扁单行→函数名大写→补括号→权重前缀和（占位符按还原后真实长度计）判断括号内容>40字符则换行展开（每参数独立一行、两空格缩进、闭括号回退独立成行）；③AI 区块与基础信息行换位（经 AskUserQuestion 确认）：AI 生成区置顶，并连带生成字段编码/名称/输出类型（后端 prompt 输出 JSON 新增 code/name/output_type，前端仅回填空白项不覆盖用户已填、编辑态编码不动）；④AI 改写联动：表达式非空时随请求传 current_expression，prompt 要求在其基础上按描述修改不推倒无关部分；为空则全新生成。改动：FormulaEditor.vue（模板换位/删按钮/格式化重写/handleAiGenerate 传参+回填）、api/modeling.ts（generateFormula 加 currentExpression、GenerateFormulaResult 加 code/name/output_type）、views.py generate_formula（接收 current_expression）、ai_service.py generate_formula（新参数+modify_block+返回三新字段）。验证：vue-tsc 0 errors、py_compile OK；浏览器实跑：AI 区块 top 152 < basic-form top 236、工具栏仅[格式化,验证公式]、长表达式格式化后多行缩进正确，截图确认

### 第四十九轮（2026-07-27）标签：同步、计算字段、弹窗、刷新

- **更早操作**：2026-07-27 — FormulaEditor 侧栏加技术函数 Tab（第四十九轮）：用户反馈「技术函数编辑入口也应该在新建计算字段弹窗里，切换一下」。FormulaEditor.vue 侧栏 sideTab 新增第三个 Tab「技术函数」（与「字段引用」「函数库」并列）：顶部工具栏（下载模板/刷新）+ a-upload 上传按钮（accept='.py'）+ 安全提示 + 已加载插件列表（每项 filename+函数tag+重载/卸载按钮，卸载带 popconfirm）。新增状态 plugins/pluginsLoading/pluginUploading/pluginReloadingMap/pluginUnloadingMap；新增函数 loadPlugins/handlePluginUpload/handlePluginReload/handlePluginUnload/handleDownloadTemplate（模板用 Blob 下载为 tech_function_template.py）；上传/重载/卸载成功后自动刷新插件列表+同步刷新函数库（functions.value 重新拉取 availableFunctions，确保「函数库」Tab 即时出现新函数）。watch(open) 初始化时调用 loadPlugins()。新增 CSS：tech-plugins-toolbar/plugin-list/plugin-item/plugin-header/plugin-filename/plugin-fns/plugin-actions。验证：vue-tsc 0 errors。独立管理页 /settings/tech-functions 保留作为补充入口

### 第四十八轮（2026-07-27）标签：/modeling、菜单、弹窗

- **更早操作**：2026-07-27 — 技术函数插件动态加载（第四十八轮）：用户反馈「技术函数实现形式不对，要写好的 .py 脚本可以在前台直接导入」。方案B（前端上传）实施：①后端新建 `plugin_loader.py`（tech_plugins/ 目录管理 + AST 安全校验：白名单导入 re/hashlib/math/datetime/apps.modeling.formula_engine，禁止 os/sys/subprocess/open/eval/exec/getattr 等危险操作 + load/unload/reload/list/load_all/get_template 7个核心函数）；②`apps.py` 加 `ready()` 启动时扫描 tech_plugins/ 加载全部 .py（失败记录日志不阻断启动）；③`views.py` ComputedFieldViewSet 新增 5 个 action：plugins/upload（multipart 上传+AST校验+写入+加载，失败回滚写入）/plugins/unload/plugins/reload/plugins/list/plugins/template；④前端新建 `views/settings/TechFunctions.vue` 独立管理页（a-upload-dragger 拖拽上传 + 已加载插件列表含函数 tag + 重载/卸载按钮 + 模板弹窗含复制按钮）；⑤router 加 `/settings/tech-functions` 路由 + MainLayout 系统设置菜单加「技术函数」入口；⑥`api/modeling.ts` 新增 PluginInfo/PluginFunctionInfo 接口 + computedFieldApi.pluginList/pluginUpload/pluginUnload/pluginReload/pluginTemplate。验证：vue-tsc 0 errors；Django check 0 issues；冒烟10步全通过（list空→template 787字节→合法.py上传成功注册SMOKE_TEST→available-functions含新函数→非法.py含import os被拒「行2：禁止导入 'os'」→reload成功→unload成功→list恢复空）；启动加载验证：放 startup_check.py 到 tech_plugins/ 重启后端，plugins/ 返回含 STARTUP_CHECK 函数，证明 apps.py ready() 扫描加载生效

### 第四十七轮（2026-07-27）标签：/modeling/custom_functions

- **更早操作**：2026-07-27 — 技术函数方案A实施（第四十七轮）：用户确认只做方案A。新建 backend/apps/modeling/custom_functions.py 技术函数插件（文件头含注册规范文档：全大写命名/category固定'技术函数'/description写清签名/业务错误抛FormulaRuntimeError），首批6函数：PAD_LEFT(补齐)/REGEX_EXTRACT(正则提取)/REGEX_REPLACE(正则替换)/SPLIT_INDEX(拆分取段)/MAP_VALUE(映射转换)/HASH_MD5(摘要对账)；formula_engine.py末尾 `from . import custom_functions` 接入（所有消费方ai_service/views/computed_service都import formula_engine，注册表必然完整）；前端零改动（级联函数库按category动态分组自动出现「技术函数」分类，AI prompt自动携带）。验证：Django check 0 issues；冒烟38函数（6技术函数）、9用例求值全OK（含IFERROR捕获正则错误、参数个数校验）。route_index.md已登记custom_functions.py新模块+formula_engine职责修正（32函数/真实函数名evaluate・validate_expression）

### 第四十六轮（2026-07-27）标签：同步、计算字段、测试报告

- **更早操作**：2026-07-27 — 测试报告5项处理（第四十六轮）：FormulaEditor公式编辑器。①预览面板常驻+空态引导（外层div无条件渲染，内容包template v-if=previewResult，else空态文案；header meta改v-if=previewResult&&valid）；②窗口1280→1480px+侧栏400→560px（量化：原二级栏400-12-140-8≈240px不够长code+中文名，加宽后≈400px）；③字段引用列表中文名前置为主体（ref-name #262626在前、ref-code灰色monospace 11px在后，均ellipsis）；④AI自然语言生成表达式全栈新增：后端ai_service.generate_formula（复用_chat强制json_object，prompt携带域内活跃字段清单{表名.code}—中文名（类型）+计算字段{$computed.code}+32函数签名，无LLM配置报错不降级）+ComputedFieldViewSet generate-formula action（detail=False，POST description+domain）；前端computedFieldApi.generateFormula+GenerateFormulaResult类型+FormulaEditor表达式框上方内嵌AI输入行（aiDescription/aiGenerating/aiExplanation，生成后自动验证+预览，explanation绿色提示条）；textarea 330→300px与侧栏总高对齐。⑤技术函数新需求：本轮仅产出评估报告（A自定义Python函数插件/B SQL片段直通/C外部预计算结果迁移映射三方案对比），推荐A+C组合，待用户确认后下轮路由reqa做REQ-018概念设计。验证：vue-tsc 0 errors，Django check 0 issues，has_llm True，generate-formula action注册成功。route_index.md已同步更新3处

### 第四十四轮（2026-07-27）标签：/modeling/domains/、同步、测试报告

- **更早操作**：2026-07-27 — 测试报告2项修复（第四十四轮）：页面 /modeling/domains/:id/fields 属性配置Tab。①只显示2个字段—根因 loadAttrTabData 只调 standardFieldApi.list（仅组合字段），改为 Promise.all(fieldGroupApi.tree + fieldApi.standardFields聚合 + computedFieldApi.list) 统一 AttrRow 行结构（equiv组合/solo基础/computed计算）；后端 standard-fields action equiv行携带 sf_id+field_type/length/required/default_value/is_active、solo行携带同名属性（sf_id/is_active=None），StandardFieldAggregateSerializer+前端类型同步扩展；保存分流：equiv→standardFieldApi.patch(sf_id)、solo→fieldApi.batchUpdateAttributes、computed→computedFieldApi.patch（仅release_to_archive，其余列只读显示—，类型列显示输出类型tag）；②左栏加只读分组筛选导航（split-layout，全部字段/未分组/分组树，复用 flatGroupTree/getDescendantGroupIds，无拖拽无增删），新增 attrActiveGroupId+getAttrGroupCount，表格加类型列+排序。验证：vue-tsc 0 errors，Django check 0 issues，冒烟测试域8返回28行含属性字段

### 第四十二轮（2026-07-25）标签：去重

- **更早操作**：2026-07-25 — 公式编辑器数据预览功能（第四十二轮）：FormulaEditor新建/编辑窗口增加「数据预览」按钮+内嵌面板。后端computed_service新增preview_expression免实例预览函数（验证语法→提取引用→复用_build_param_space_from_distinct构建去重参数空间→笛卡尔积逐行计算）+ ComputedFieldViewSet新增preview-data action（detail=False，无需先保存）；前端computedFieldApi.previewData+PreviewDataResult类型；FormulaEditor表达式下方内嵌预览表格（列=各输入参数字段去重值+输出结果列，sticky表头+截断提示+错误行红色，表达式变更自动清空）。验证：vue-tsc 0 errors, Django check 0 issues, manage.py shell冒烟测试通过

### 第四十一轮（2026-07-25）标签：/modeling/domains/、字段分组

- **更早操作**：2026-07-25 — 字段分组Tab 3项修复（第四十一轮）：页面 /modeling/domains/:id/fields 字段分组Tab。①「下级分组」列移到列表最后+宽度140→100+加排序（subGroupDisplay辅助函数支持sorter）；②本级字段/无分组显示灰色"--"，仅子分组字段显示分组名；③左栏分组节点支持拖拽排序（后端FieldGroupViewSet新增reorder action批量写sort_order + 前端_dragGroupId区分字段拖拽/分组节点拖拽 + findSiblingList同父级校验 + 位置感知插入）。验证：vue-tsc 0 errors, Django check 0 issues

### 第三十九轮（2026-07-25）标签：/modeling/domains/、测试报告

- **更早操作**：2026-07-25 — 测试报告5项修复（第三十九轮）：页面 /modeling/domains/:id/fields 公式编辑器FormulaEditor五项交互体验升级。①新建模式真正验证公式（后端新增validate-expression action无需保存实例+前端新建模式调用真验证接口）；②字段引用按表分组折叠展示（collapsible tree替代flat list）；③函数插入带示例模板（从description解析签名如IF(条件,真值,[假值])插入公式）；④字段值预览与插入（available-references携带sample_values前10条+选中字段展示样本值+点击值直接插入字面量）；⑤修复validate_formula KeyError bug（validation['errors']→[validation.get('error')]）。验证：vue-tsc 0 errors, Django check 0 issues

### 第三十八轮（2026-07-25）标签：字段分组

- **更早操作**：2026-07-25 — 字段分组Tab 4项UI修复（第三十八轮）：①左栏加宽 200px→500px；②kind_tag"基础字段"→"基础"；③分组列改为"下级分组"只读文本移到最前（删除下拉编辑，保留拖拽分组）；④点击父分组时非本级字段背景色区分(#f6f8fa)。验证：vue-tsc EXIT=0

### 第三十六轮（2026-07-25）标签：-

- **更早操作**：2026-07-25 — 多层分组功能实现（darc编码，第三十六轮）：FieldGroup模型增加parent外键支持树形嵌套（最多3层）。验证：vue-tsc EXIT=0, Django check 0 issues, migrate 0022 OK

### 第三十五轮（2026-07-25）标签：计算字段

- **更早操作**：2026-07-25 — 计算字段功能全栈实现（darc编码，第三十五轮）：REQ-017 计算字段配置与自动计算全功能实现。10个子任务全部完成：①ComputedField模型扩展(depends_on/depends_on_computed/parsed_references/execution_order/output_type)、②公式引擎(formula_engine.py:递归下降Lexer+Parser+Evaluator+28内置函数)、③计算服务(computed_service.py:DAG拓扑+循环检测+批量/实时重算)、④后端API(ComputedFieldViewSet+6actions:validate/trial/graph/batch/functions/references)、⑤档案集成(schema含计算字段+sync后批量重算+编辑实时重算)、⑥前端API层(6接口+6方法)、⑦FormulaEditor.vue(公式编辑器)、⑧TrialCalculation.vue(枚举试算)、⑨DomainFieldConfig增强(工具栏+列增强+modal集成)、⑩集成验证(Django check 0 issues + vue-tsc 0 errors)

### 第三十四轮（2026-07-25）标签：同步、计算字段

- **更早操作**：2026-07-25 — 计算字段功能概念设计（reqa增量，第三十四轮）：REQ-017 计算字段配置与自动计算。产出：requirements.json新增REQ-017（4场景6业务规则）、storylines/REQ-017.md（7步用户旅程）、business-flow.md新增流程五（配置阶段+执行阶段）、concept-feature-list.md新增F-011~F-017（7个功能项）、concept-architecture.md追溯矩阵更新、constitution.md新增决策记录。设计决策：Excel公式风格函数引擎+DAG依赖图+枚举试算+物化存储+双触发（同步后批量+编辑实时）

### 第三十三轮（2026-07-25）标签：/modeling/domains/、字段分组、测试报告

- **更早操作**：2026-07-25 — 测试报告3项修复（第三十三轮）：页面 /modeling/domains/:id/fields 字段分组Tab三项修正。①删除「释放到档案」列（字段分组Tab不再展示该列）；②字段分组Tab只展示档案字段（后端standard-fields action过滤solo字段只保留archive_category='base'，及只包含status='active'的StandardField）；③术语修正：类型列「独立」→「基础字段」。问题4（多层分组）留作后续设计。验证：vue-tsc EXIT=0, Django check 0 issues

### 第三十二轮（2026-07-25）标签：/modeling/domains/、标准字段

- **更早操作**：2026-07-25 — 标准字段页重构三分类架构（第三十二轮）：页面 /modeling/domains/:id/fields 全面重写。①后端模型扩展：Field.archive_category(基础/未分配/计算) + StandardField.status(active/discarded) + 新增 ComputedField 模型(骨架) + migration 0020；②前端页面完全重写：左栏200px字段分类导航(档案字段→基础/组合/计算、未分配、废弃) + 右栏字段表格(五视图切换)；③删除AI检测功能(runDetectStandards/dedupSuggestions/applyDedup)；④前端 API 层新增 ComputedFieldModel + FieldCategoryCounts + computedFieldApi；⑤后端新增 field-categories action + ComputedFieldViewSet + batch-attributes支持archive_category。验证：vue-tsc EXIT=0, Django check 0 issues

### 第二十七轮（2026-07-24）标签：/modeling/domains/8/fields、标准字段、去重、弹窗、刷新

- **更早操作**：2026-07-24 — 标准字段界面工具栏重排+统一启用开关（第二十七轮）：页面 /modeling/domains/8/fields 标准字段Tab，测试3个交互微调（针对上轮双栏看板）。经AskUserQuestion确认：①上下表公用控件（一个模糊搜索框+刷新数据去重按钮）上移顶部工具栏，一个模糊搜索同时过滤上表(filteredStandardFieldModels)+下表(manualFilteredCandidates)；②标准编码/名称收进 manualCreateVisible 弹窗(openManualCreateModal 触发)；③上下表去除首列“进档案”checkbox，统一改为右侧“启用”a-switch列（列名统一），上表switch驱动 is_active、下表switch驱动 release_to_archive（用户视角上下表逻辑一致）；删除 toggleConfirmedReleaseArchive。纯前端改动，后端不动。验证：vue-tsc EXIT=0

### 第二十六轮（2026-07-24）标签：/modeling/domains/8/fields、/archive-preview/、标准字段

- **更早操作**：2026-07-24 — 标准字段界面重做为上/下双栏看板（第二十六轮）：页面 /modeling/domains/8/fields 标准字段Tab。用户要求「整个重新编排」，经AskUserQuestion确认方案B双栏看板+复用release_to_archive门控+下表前端临时拖排(不落库)+确认到档案只读预览Modal。①上区=已确认标准字段(row-selection+“释放选中回下面”)；②下区=未确认候选(拖拽行换位)；下→上确认。新增后端 GET /fields/archive-preview/ 只读action。验证：vue-tsc EXIT=0、Django check 0 issues

### 第二十五轮（2026-07-24）标签：/modeling/domains/8/fields、标准字段、去重、弹窗、刷新

- **更早操作**：2026-07-24 — 标准字段页手动新增内联化+启用开关语义改概念模型（第二十五轮）：页面 /modeling/domains/8/fields 标准字段Tab。①手动新增从 a-modal 弹窗改为内联常驻区块，置于「已确认的标准字段」表格下方（删除「手动新增标准字段」按钮，新增区带标准编码/名称输入+搜索+刷新去重+「新增（已选N）」提交按钮+候选多选表，表格 scroll.y 由 calc(100vh-300px) 改固定 360）；候选改 onMounted 时 loadManualCandidates() 预加载，提交成功后 resetManualForm()+重载候选；移除 manualModalVisible ref、openManualModal 改 resetManualForm。②is_active 启用/停用开关语义由「不进档案」改为「不纳入概念模型」（经查后端 is_active 仅在 archive/views.py _field_released 作档案释放门控，无独立概念模型消费者；用户选复用+改语义，前端文案改 toggleStandardFieldActive message+加 a-tooltip 说明启用=纳入概念模型并向下游档案释放，后端不动）。验证：vue-tsc 零错误

### 第二十三轮（2026-07-24）标签：/modeling/domains/8/fields、标准字段、去重、抽屉

- **更早操作**：2026-07-24 — 字段管理3项修复（第二十三轮）：页面 /modeling/domains/8/fields。①从域管理进入默认Tab应为标准字段—mainTab 默认 'group'→'dedup'；②成员去重值"全部都是红"—旧 isDiffValue 用「所有成员交集」判断（非每个成员都有即红，叠加100条截断导致几乎全红），改为基于值频次 memberValueFrequency（单成员内去重后统计出现成员数），isDiffValue=仅出现在1个成员→红（独有值/不一致）、≥2成员共有→不红；抽屉加图例说明；③单独释放某表成员—抽屉每个成员卡片加「释放」(a-popconfirm)，后端 StandardFieldViewSet 新增 remove-member action(POST field_id→member.standard_field=None)，前端 standardFieldApi.removeMember + distinctStandardFieldId 跟踪当前SF。验证：vue-tsc 零错误、Django check 0 issues

### 第二十一轮（2026-07-24）标签：标准字段、去重、弹窗、抽屉

- **更早操作**：2026-07-24 — 手动新增标准字段3项修复（第二十一轮）：①去重读取失败明细化—refreshManualDistinct 失败时 Modal.warning 列出失败字段编码+错误原因，弹窗单元格区分 null(未读取/失败黄色)与 []([]无数据灰色)；②弹窗高度填满—body maxHeight 82vh→calc(100vh-140px)、表格 scroll.y 62vh→calc(100vh-300px)；③成员去重值抽屉排序+差异红标—sortedMemberValues(数字感知localeCompare)、commonDistinctSet(各成员交集)、isDiffValue(未被所有成员共享的值 :color=red)。验证：vue-tsc 零错误

### 第二十轮（2026-07-24）标签：/modeling/domains/8/fields、标准字段、弹窗

- **更早操作**：2026-07-24 — 手动新增标准字段弹窗最大化+去换页器（第二十轮）：页面 /modeling/domains/8/fields 手动新增弹窗 uxqa 反馈窗口不够大+不要换页器。①弹窗 width 90vw→**96vw**、移除 maxWidth:1280px 限制(大屏真正铺满)、top 32→16px、body maxHeight 72vh→82vh；②表格 pagination 改 **false**(全量展示)、scroll.y 46vh→62vh。尺寸推理：top16+头部55+footer53+body82vh≈89.7vh<100vh安全。验证：vue-tsc 零错误

### 第十九轮（2026-07-24）标签：/modeling

- **更早操作**：2026-07-24 — AI配置页增强（第十九轮）：①默认改DeepSeek(api_base=https://api.deepseek.com/v1、model=deepseek-chat)；②AIConfig加provider+4类可配置prompt字段(prompt_auto_group/semantic/dedup/infer，迁移0018)；③ai_service加DEFAULT_PROMPT_*常量+PROMPT_META+_resolve_prompt(DB优先内置默认降级)+prompt_defaults()，4个_llm函数(_auto_group/_semantic/_detect_duplicates/_infer_fields)改用_resolve_prompt+运行时f-string追加字段JSON；④AIConfigSerializer加provider+4prompt字段+prompt_defaults(method field)；⑤前端AIConfig.vue加PROVIDERS预设(deepseek/openai/qwen/zhipu/moonshot/custom)厂商select+模型select(非custom)/input(custom)+api_base自动填充disabled+prompt配置区(a-collapse4面板+恢复默认)；⑥api/modeling.ts AIConfigModel接口扩展。验证：check通过、migrate 0018 OK、vue-tsc 零错误

### 第十八轮（2026-07-24）标签：标准字段、去重、菜单、弹窗

- **更早操作**：2026-07-24 — 测试报告4项修复（第十八轮）：①手动新增弹窗放大(90vw/maxWidth1280/body72vh/table46vh/pageSize15)；②手动候选勾选项顶置(manualFilteredCandidates 稳定排序)；③已确认标准字段加「查看」→抽屉并排展示各成员去重值(StandardFieldViewSet.members-distinct 复用_ensure_distinct_cache)；④a AI分组prompt重写(强调按业务主题分组、严禁按数据类型)+启发式桶业务化(9主题中英文关键词)，④b 新增 AIConfig 单例模型(迁移0017)+AIConfigViewSet(current/test-connection)+ai_service._resolve_ai_config优先读DB回退env+test_connection+前端 settings/AIConfig.vue配置页(菜单改父级带children)。验证：check 通过、migrate 0017 OK、vue-tsc 零错误

### 第十七轮（2026-07-23）标签：标准字段、去重、刷新

- **更早操作**：2026-07-23 — 标准字段功能再设计（第十七轮）：①AI检测三层匹配（编码/名称/数据去重内容）；②手动新增改可排序表格（编码/名称/来源/去重内容）+刷新按钮；③排除已配置字段。Field 加 distinct_values/distinct_synced_at 缓存（迁移0016）；views 加 _fetch_distinct_values（本地+外部四库 DISTINCT）/_ensure_distinct_cache/refresh-distinct/manual-candidates；ai_service 三维度综合判断。验证：check 通过、migrate 0016 OK、vue-tsc 零错误

### 第十六轮（2026-07-23）标签：标准字段、字段分组、去重、弹窗

- **更早操作**：2026-07-23 — 测试问题报告6项修复（第十六轮）：①主键设置后表列表不刷新→TableList.doTogglePrimaryKey 成功后重算 primary_keys 回写 tables；②应用去重后分组/属性Tab不刷新→applyDedup 补 loadStandardFields+loadStandardFieldsForAttr，group Tab 加去重引导 alert；③已确认标准字段表移除来源列、操作改启用/停用→StandardField 加 is_active（迁移0015）、_field_released 停用即不释放、前端 a-switch；④字段分组加「释放到档案」列（复用门控，equiv PATCH/solo batch）；⑤分组重命名400→fieldGroupApi.update 改 PATCH；⑥AI检测增名称(comment)归一化匹配（union 编码或名称）、后端 StandardFieldViewSet.create + standardFieldApi.create、前端手动新增标准字段弹窗（搜索浏览相似项）。验证：check 通过、migrate 0015 OK、vue-tsc 零错误
