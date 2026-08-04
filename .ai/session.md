# 会话接力 — 主文件（当前状态 + 功能索引）

> 启动只读本文件（rule §3）。历史详情按模块存于 `.ai/session-details/<模块>.md`（archive / modeling / uxqa / project / early-logs），确认需求后按「模块+功能标签/第N轮」grep 加载，禁止全量读。

## 当前会话状态

- **当前阶段：**第九十九轮 变更日志 v18.1 已落地（测试报告 2 项）：仅按时间一层折叠（批次降为明细行字段）+字段变化直看（旧值→新值+日行主要变化摘要）+撤销本日全部；顺手修复验证发现的缺陷（明细级回滚自建批无 source_batch_id 导致纯回滚日未禁用）。vue-tsc 0 errors、浏览器两轮验证通过。待办：R-024 待用户确认删除 legacy/ 目录、ArchiveApi 鉴权强化、源优先级配置(BR-018-1)、血缘历史时间线、AI建立关系后端 API
- **活跃模块**：archive


### 最近 3 轮详情（满 3 轮后最旧一轮下沉到详情文件）

- **上次操作**：2026-08-04 — 第九十九轮：测试报告 2 项修复（v18.1，推翻 v18 两层折叠）：①仅按时间一层折叠——批次行层移除，同档案同日全部批次合并为日期行，展开直出当日全部明细，批次号 #N 作为字段显示在明细行时间列；②字段变化直看——明细行旧值→新值彩色展示，新增/停用显示「记录级变更」提示，日行加载完明细后显示「主要变化」top3 摘要（如备注×1298）；③撤销本日全部（用户选定粒度）取代批次级整批撤销，串行逐批撤销汇总结果。验证中发现并修复缺陷：明细级回滚自建批无 source_batch_id 标记导致纯回滚日撤销链接未禁用，判定改「含正向变更且非整批回滚产物」；另修翻页拉全计数 bug。vue-tsc 0 errors，浏览器两轮验证（含 1439 条大日、纯回滚日禁用态复验）通过。
- **更早操作**：2026-08-03 — 第九十八轮：变更日志批次视图交互调整（用户：「把明细也放到列表里面」，AskUserQ 选定「点批次行展开子行」）。VersionManagement.vue 纯前端改造：下钻抽屉移除，批次行预挂占位子行保展开箭头可见，@expand 首次展开拉取该批明细（page_size=500）替换占位；明细子行存响应式 Map batchDetails（不可直接改 computed 返回对象）；列合并双义（版本列批次行显示明细数提示、明细行显示 vN→vM）；移除抽屉内变更类型/记录搜索筛选。验证：vue-tsc 0 errors、浏览器两级展开（日行→批次→299 条明细批）正常无 JS 错误；顺手修 3 处 AStatistic value-style 警告。
- **更早操作**：2026-08-03 — 第九十七轮：v18 回滚体系统一落地（四任务按序 ③回滚收口→④预检告警→①批次视图→②攒批保存），详见 session-details/archive.md。

## 功能索引（倒序，每轮一行；完整性/确认点自本次迁移后开始记录）

| 轮次 | 日期 | 模块 | 功能标签 | 一句话摘要 | 完整性 | 确认点 |
|------|------|------|----------|------------|--------|--------|
| 第一百轮 | 2026-08-04 | modeling、archive | 测试扩展、CI、better-harness | 测试覆盖从 12 扩展到 45（modeling 27 + archive 18），覆盖 CRUD/唯一约束/主表切换/双层存储/版本追踪/变更日志/数据服务 API；45 测试全 PASS，vue-tsc 0 errors | 闸✓记✓拓✓ | 1问 |
| 第九十九轮 | 2026-08-04 | archive | /archive/versions、变更日志、时间折叠、字段变化 | 测试报告 2 项（v18.1 推翻两层折叠）：仅按时间一层折叠（批次降为明细行 #N 字段）；字段变化直看（旧值→新值+记录级变更提示+日行主要变化 top3 摘要）；撤销本日全部取代批次级撤销；修复验证发现缺陷（明细级回滚自建批无 source_batch_id 致纯回滚日未禁用）+翻页计数 bug | 闸✓记✓拓✓ | 2问/0改向 |
| 第九十八轮 | 2026-08-03 | archive | /archive/versions、变更日志、批次视图、明细展示 | 变更日志明细内联展开：下钻抽屉改为点批次行展开明细子行（占位行保箭头可见+@expand 按需加载+响应式 Map 存子行），抽屉及其筛选移除；vue-tsc 0 errors+浏览器两级展开验证正常 | 闸✓记✓拓✓ | 1问/0改向 |
| 第九十七轮 | 2026-08-03 | archive | /archive/versions、变更日志、回滚、攒批保存、刷新预检 | v18 回滚体系统一落地：回滚统一「恢复快照」语义走 _execute_field_rollback 分层写回（修 C1 隐性 Bug）；明细加 version_before/after 映射（迁移0011，存量降级）；三粒度回滚（单条/整批撤销跳过后续编辑/版本）；VersionManagement 翻新批次视图（同日折叠+下钻+近7天汇总卡）；人工编辑攒批保存（start-manual+change_batch_id，草稿仅存浏览器+离开拦截）；刷新预检 archive_owned_impact 告警；后端 6 测试+端到端冒烟 6/6 PASS | 闸✓记✓拓✓ | 2问/0改向 |
| 第九十六轮 | 2026-08-03 | archive | /archive/versions、变更日志、回滚、设计讨论 | 变更日志×回滚架构讨论：诊断4处冲突（版本回滚不分层/单条回滚不可交换/双事实源/源侧回滚虚假承诺），提出「一条时间线(快照为骨干)+双视图+统一回滚+刷新预检源侧告警」方案，用户意向合并日志与快照、保留单条+版本回滚、源侧加检查提醒，待边界确认后走流程 | N-A | 3问/3改向 |
| 第九十五轮 | 2026-08-03 | modeling、archive | 测试报告、列合并、AI按钮、图标、布局、回滚 | 测试报告 8 项修复：TableList 字段弹窗「释放+状态」合并「模型字段」列、DomainFieldMapping 加AI建立关系按钮(后端待开发)、DomainFieldConfig 图标+编辑文字、ArchiveList 操作列加编辑、ArchiveDetail 布局占满屏+去详情弹窗回滚+历史弹窗下拉 | 闸✓记✓拓✓ | 3问/4改向 |
| 第九十四轮 | 2026-08-03 | uxqa、modeling、archive、settings | 全站、交互流程、按钮名称、交互密度 | UXQA 交互流程巡检，R-040~R-044（5项）全部闭环：字段分组树去按钮+名称点击编辑、3页操作列编辑改名称可点击、settings标题去前缀、Modal.confirm统一“确认”、15处冗余||e.message清理 | 闸✓记✓拓✓ | 2问/1改向 |
| 第九十二轮 | 2026-08-03 | uxqa、modeling、archive、settings | 全站、交付验收、危险操作确认、extractApiError | UXQA 全站14页巡检，R-032~R-036（5项）全部闭环：3处删除改Modal.confirm+影响文案、DomainList补extractApiError、ConsistencyCheck操作人默认值统一、导出按钮v-if已覆盖 | 闸✓记✓拓✓ | 1问 |
| 第九十一轮 | 2026-08-03 | project | 基础设施、Git、测试、验收标准 | better-harness 报告 3 项优化：Git 初始化(236文件)+后端12冒烟测试+前端 vue-tsc 0 errors+交付验收标准 | 闸✓记✓拓✓ | 1问 |
| 第九十轮 | 2026-07-25 | uxqa、archive、modeling、settings | 全站、交付验收、菜单、弹窗、scroll.x、死代码 | UXQA 全站17页交付验收巡检，21项整改(R-011~031)全部闭环，4批次执行 vue-tsc 0 errors | - | - |
| 第八十九轮 | 2026-07-25 | archive | /archive/versions、/archive/5、回滚、变更日志、版本 | v17 回滚前端落地+回滚报错修复（旧进程未加载端点）+v17.1 记录列表「变更历史」入口弹窗 | - | - |
| 第八十八轮 | 2026-07-30 | archive、modeling、uxqa、project | /modeling/domains/8/fields、/archive/5、同步、计算字段、版本 | 测试报告 7 项全栈整改（/modeling/domains/8/fields 3 项 + /archive/5 3 项… | - | - |
| 第八十七轮 | 2026-07-30 | archive、modeling、uxqa | /modeling/domains/8/fields、/archive/5、同步、版本、字段分组 | 测试报告 8 项全栈整改（/modeling/domains/8/fields 1 项 + /archive/5 7 项… | - | - |
| 第八十六轮 | 2026-07-30 | archive、modeling、project | /archives/、/archive、一致性、变更日志、主字段 | 一致性检查独立页全栈落地（需求「以主字段为准覆盖所有成员表」与 Hub 宪法「源表只读、永不回写」冲突，AskUserQ… | - | - |
| 第八十五轮 | 2026-07-30 | archive、modeling | /modeling、同步、一致性、主字段、数据源 | 组合字段主字段机制全栈落地（用户三条背景：①设主表后组合字段默认用主表成员作主字段（用于档案更新）②主字段=数据源头其余… | - | - |
| 第八十四轮 | 2026-07-30 | archive、modeling | /modeling/domains/8/fields、/modeling、同步、字段维护方、去重 | 测试报告 2 项修复（/modeling/domains/8/fields 属性配置 Tab；①ownership 默认… | - | - |
| 第八十三轮 | 2026-07-30 | archive、modeling | /archive/5、/modeling/domains/8/fields、同步、计算字段、版本 | 测试问题报告 10 项修复（/archive/5 九项 + /modeling/domains/8/fields 一项；… | - | - |
| 第八十二轮 | 2026-07-29 | archive | /archive_name/operation_type_display、版本、变更日志、菜单、抽屉 | 档案菜单信息架构重做（🏗️ 模块重做级，两轮 AskUserQuestion 锁定：①档案管理收敛数据向操作保留档案 C… | - | - |
| 第八十一轮 | 2026-07-29 | archive | /archive/changes、变更日志、菜单、导出 | 变更日志收尾三项（用户决策：①不做保留期清理—变更日志是保留记录永久存库②全局总览新页面+菜单③导出针对单个档案带全部明… | - | - |
| 第八十轮 | 2026-07-25 | archive | 同步、变更日志、刷新 | 数据变更日志全栈落地（用户需求：源侧系统经常自行改数据/删数据不通知，需可追溯的数据核对记录；四项确认决策：①新建批次+… | - | - |
| 第七十九轮 | 2026-07-25 | archive、modeling | 同步、计算字段、抽屉、刷新 | 主数据记录管理边界收口（两项用户决策：①禁止档案端人工新增—所有记录源头来自业务系统；②源侧删除→标记停用） | - | - |
| 第七十八轮 | 2026-07-29 | archive、modeling | 同步、计算字段、刷新 | 档案5（域8）计算字段脏配置修复，三处问题三处修复 | - | - |
| 第七十七轮 | 2026-07-29 | archive、modeling、project | 同步、计算字段、刷新 | 档案双层存储重构（方案B+定时刷新）全栈落地，7 Task 全部完成 | - | - |
| 第七十六轮 | 2026-07-29 | archive、modeling、project | /modeling/domains/8/fields、/archive/5、同步、计算字段、数据源 | 测试报告两项 | - | - |
| 第七十五轮 | 2026-07-28 | archive、modeling、uxqa、project | /archive、同步、计算字段、抽屉 | 方案B（Hub式MDM）架构整改全栈落地【重大架构转向：放弃双向同步，推翻 F-116 冲突队列/F-118 字段级回写… | - | - |
| 第七十四轮 | 2026-07-25 | archive、project | 同步 | 第七十四轮（环境配置修复，prjm 直接处理无代码变更）：为域8 正式设置主表——表8「IMP_零售_门店_基本信息填报… | - | - |
| 第七十三轮 | 2026-07-28 | archive | 同步、抽屉、血缘 | REQ-018 MDM 第7批（F-118 字段级回写 + F-119 血缘展示）darc 开发全栈落地 | - | - |
| 第七十二轮 | 2026-07-28 | archive | 同步、版本、血缘 | REQ-018 MDM 第6批 darc 开发全栈落地 | - | - |
| 第七十一轮 | 2026-07-28 | archive、modeling | /archive/5、同步、计算字段、去重、抽屉 | 测试报告两题（/archive/5） | - | - |
| 第七十轮 | 2026-07-28 | archive、modeling、uxqa | /archive/5、/modeling、同步、计算字段、字段分组 | 测试报告 3 项（/archive/5） | - | - |
| 第六十九轮 | 2026-07-28 | archive、modeling | /modeling/domains/8/fields、同步、计算字段、去重、弹窗 | 测试报告 4 项（/modeling/domains/8/fields） | - | - |
| 第六十八轮 | 2026-07-28 | archive、modeling、uxqa | 计算字段、Bug | 第六十八轮（Bug）：计算字段填 IFS(...) 表达式点保存失败 | - | - |
| 第六十七轮 | 2026-07-28 | archive、modeling | 同步、去重、弹窗、测试报告 | 测试报告 3 项 | - | - |
| 第六十六轮 | 2026-07-28 | uxqa | 弹窗 | uxqa 全流程整改枚举试算弹窗（用户反馈「这个页面就没怎么设计啊 uxqa一下」，XPath body/div[7] … | - | - |
| 第六十五轮 | 2026-07-28 | project | 测试报告 | 测试报告 5 项（FormulaEditor） | - | - |
| 第六十四轮 | 2026-07-28 | modeling | /modeling、测试报告 | 测试报告 4 项（FormulaEditor） | - | - |
| 第六十三轮 | 2026-07-27 | uxqa | 测试报告 | 测试报告 3 项（FormulaEditor 对齐+细框） | - | - |
| 第六十二轮 | 2026-07-25 | uxqa | - | 第六十二轮（UXQA 实跑验收）：用户反馈第六十一轮第 2/3/5 项不达标，浏览器实跑截图+JS 量化测量定位三个真根… | - | - |
| 第六十一轮 | 2026-07-27 | project | - | 用户反馈 FormulaEditor 五项调整 | - | - |
| 第四十九轮 | 2026-07-27 | project | 同步、测试报告 | 第四十九轮测试报告 4 项处理（第五十轮）：用户反馈 FormulaEditor 四项改进 | - | - |
| 第四十九轮 | 2026-07-27 | modeling、project | 同步、计算字段、弹窗、刷新 | FormulaEditor 侧栏加技术函数 Tab（第四十九轮）：用户反馈「技术函数编辑入口也应该在新建计算字段弹窗里，… | - | - |
| 第四十八轮 | 2026-07-27 | modeling | /modeling、菜单、弹窗 | 技术函数插件动态加载（第四十八轮）：用户反馈「技术函数实现形式不对，要写好的 .py 脚本可以在前台直接导入」 | - | - |
| 第四十七轮 | 2026-07-27 | modeling、project | /modeling/custom_functions | 技术函数方案A实施（第四十七轮）：用户确认只做方案A | - | - |
| 第四十六轮 | 2026-07-27 | modeling、project | 同步、计算字段、测试报告 | 测试报告5项处理（第四十六轮）：FormulaEditor公式编辑器 | - | - |
| 第四十五轮 | 2026-07-27 | project | 去重、测试报告 | 测试报告5项修复（第四十五轮）：FormulaEditor公式编辑器五项优化 | - | - |
| 第四十四轮 | 2026-07-27 | modeling | /modeling/domains/、同步、测试报告 | 测试报告2项修复（第四十四轮）：页面 /modeling/domains/:id/fields 属性配置Tab | - | - |
| 第四十三轮 | 2026-07-27 | project | 去重、弹窗、测试报告 | 测试报告4项修复（第四十三轮）：FormulaEditor公式编辑器四项优化 | - | - |
| 第四十二轮 | 2026-07-25 | modeling | 去重 | 公式编辑器数据预览功能（第四十二轮）：FormulaEditor新建/编辑窗口增加「数据预览」按钮+内嵌面板 | - | - |
| 第四十一轮 | 2026-07-25 | modeling | /modeling/domains/、字段分组 | 字段分组Tab 3项修复（第四十一轮）：页面 /modeling/domains/:id/fields 字段分组Tab | - | - |
| 第三十九轮 | 2026-07-25 | modeling | /modeling/domains/、测试报告 | 测试报告5项修复（第三十九轮）：页面 /modeling/domains/:id/fields 公式编辑器Formula… | - | - |
| 第三十八轮 | 2026-07-25 | modeling | 字段分组 | 字段分组Tab 4项UI修复（第三十八轮）：①左栏加宽 200px→500px；②kind_tag"基础字段"→"基础"… | - | - |
| 第三十七轮 | 2026-07-25 | archive、modeling | /modeling/domains/、测试报告 | 测试报告2项修复（第三十七轮）：页面 /modeling/domains/:id/fields 公式编辑器Formula… | - | - |
| 第三十六轮 | 2026-07-25 | modeling | - | 多层分组功能实现（darc编码，第三十六轮）：FieldGroup模型增加parent外键支持树形嵌套（最多3层） | - | - |
| 第三十五轮 | 2026-07-25 | archive、modeling | 计算字段 | 计算字段功能全栈实现（darc编码，第三十五轮）：REQ-017 计算字段配置与自动计算全功能实现 | - | - |
| 第三十四轮 | 2026-07-25 | modeling | 同步、计算字段 | 计算字段功能概念设计（reqa增量，第三十四轮）：REQ-017 计算字段配置与自动计算 | - | - |
| 第三十三轮 | 2026-07-25 | archive、modeling | /modeling/domains/、字段分组、测试报告 | 测试报告3项修复（第三十三轮）：页面 /modeling/domains/:id/fields 字段分组Tab三项修正 | - | - |
| 第三十二轮 | 2026-07-25 | archive、modeling | /modeling/domains/、标准字段 | 标准字段页重构三分类架构（第三十二轮）：页面 /modeling/domains/:id/fields 全面重写 | - | - |
| 第二十七轮 | 2026-07-24 | archive、modeling | /modeling/domains/8/fields、标准字段、去重、弹窗、刷新 | 标准字段界面工具栏重排+统一启用开关（第二十七轮）：页面 /modeling/domains/8/fields 标准字段… | - | - |
| 第二十六轮 | 2026-07-24 | archive、modeling | /modeling/domains/8/fields、/archive-preview/、标准字段 | 标准字段界面重做为上/下双栏看板（第二十六轮）：页面 /modeling/domains/8/fields 标准字段Ta… | - | - |
| 第二十五轮 | 2026-07-24 | archive、modeling | /modeling/domains/8/fields、标准字段、去重、弹窗、刷新 | 标准字段页手动新增内联化+启用开关语义改概念模型（第二十五轮）：页面 /modeling/domains/8/field… | - | - |
| 第二十四轮 | 2026-07-24 | project | - | AI配置模型改纯选择+升级DeepSeek V4（第二十四轮）：①模型字段从 a-auto-complete（可输入可选… | - | - |
| 第二十三轮 | 2026-07-24 | modeling | /modeling/domains/8/fields、标准字段、去重、抽屉 | 字段管理3项修复（第二十三轮）：页面 /modeling/domains/8/fields | - | - |
| 第二十二轮 | 2026-07-24 | project | - | AI配置页精简（第二十二轮）：用户嫌配置项太多 | - | - |
| 第二十一轮 | 2026-07-24 | modeling | 标准字段、去重、弹窗、抽屉 | 手动新增标准字段3项修复（第二十一轮）：①去重读取失败明细化—refreshManualDistinct 失败时 Mod… | - | - |
| 第二十轮 | 2026-07-24 | modeling、uxqa | /modeling/domains/8/fields、标准字段、弹窗 | 手动新增标准字段弹窗最大化+去换页器（第二十轮）：页面 /modeling/domains/8/fields 手动新增弹… | - | - |
| 第十九轮 | 2026-07-24 | modeling | /modeling | AI配置页增强（第十九轮）：①默认改DeepSeek(api_base=https://api.deepseek.com… | - | - |
| 第十八轮 | 2026-07-24 | modeling | 标准字段、去重、菜单、弹窗 | 测试报告4项修复（第十八轮）：①手动新增弹窗放大(90vw/maxWidth1280/body72vh/table46v… | - | - |
| 第十七轮 | 2026-07-23 | modeling | 标准字段、去重、刷新 | 标准字段功能再设计（第十七轮）：①AI检测三层匹配（编码/名称/数据去重内容）；②手动新增改可排序表格（编码/名称/来源… | - | - |
| 第十六轮 | 2026-07-23 | archive、modeling | 标准字段、字段分组、去重、弹窗 | 测试问题报告6项修复（第十六轮）：①主键设置后表列表不刷新→TableList.doTogglePrimaryKey 成… | - | - |
| - | 2026-07-27 | project | - | FormulaEditor 侧栏加技术函数 Tab（第四十九轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-27 | project | - | 技术函数插件动态加载（第四十八轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-27 | project | - | 技术函数方案A实施（第四十七轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-27 | project | - | 公式编辑器加宽+AI生成表达式+技术函数评估（第四十六轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-27 | project | - | 公式编辑器预览采样与侧栏级联重构（第四十五轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-27 | project | - | 属性配置Tab重构（第四十四轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-25 | project | - | 公式编辑器数据预览功能（第四十二轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-25 | modeling | - | 字段分组Tab 3项修复（第四十一轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-25 | project | - | 测试报告3项修复（第四十轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-25 | project | - | 多层分组功能实现（darc编码，第三十六轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-25 | modeling | - | 计算字段功能全栈实现（darc编码，第三十五轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-25 | modeling | - | 计算字段功能概念设计（reqa增量，第三十四轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-25 | project | - | 测试报告3项修复（第三十三轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-25 | modeling | - | 标准字段页重构三分类架构（第三十二轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-24 | modeling | - | 标准字段界面工具栏重排+统一启用开关（第二十七轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-24 | modeling | - | 标准字段界面重做：上/下双栏看板（第二十六轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-24 | modeling | - | 标准字段页手动新增内联化+启用开关语义改概念模型（第二十五轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-24 | modeling | - | 字段管理3项修复：默认Tab改标准字段+差异高亮改频次+成员单独释放（第二十三轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-24 | project | - | AI配置页精简：主区只留模型+APIKey、其余折叠、模型改可输入下拉自动带接口地址（第二十二轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-24 | modeling | - | 手动新增标准字段3项修复：失败明细化+弹窗填满+成员值排序与差异红标（第二十一轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-24 | modeling | - | 手动新增标准字段弹窗最大化+去换页器全量展示（第二十轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-24 | project | - | AI配置页增强：默认DeepSeek+厂商/模型下拉(接口地址自动)+四类prompt可配置（第十九轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-24 | project | - | 测试报告4项修复：弹窗放大+勾选顶置+去重值查看抽屉+AI分组prompt重写+AI配置页（第十八轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | modeling | - | 标准字段功能再设计：三层匹配+手动新增可排序表格（第十七轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | project | - | 测试问题报告6项修复（第十六轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | archive | - | 字段两层释放门控（物理层→概念层→档案）（第十五轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | project | - | 「待处理记录不应是975条」→ 不同步写回字段机制（第十四轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | archive | - | 「流程报错」→ 同步到数据源两阶段重构（第十三轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | project | - | 启用/停用逻辑修复（第十二轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | project | - | 测试报告 5 项问题修复（第十一轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | project | - | 测试报告 4 项问题修复（第十轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | archive、uxqa | - | R-003 整改（ArchiveList 操作列收敛）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | uxqa | - | UXQA 全界面交付验收巡检（第九轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | project | - | 测试报告 5 项问题修复（第八轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | archive | - | 数据服务API功能（档案维护拆分）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-23 | project | - | 测试报告 4 项问题修复（第七轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | project | - | 表头横滚问题修复（第六轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | project | - | 测试报告 4 项问题修复（第五轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | project | - | 测试报告 6 项问题修复（第四轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | project | - | 测试报告 6 项问题修复（第三轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | project | - | 测试报告 3 项问题修复（第二轮）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | project | - | 测试报告 5 项问题修复（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | archive、uxqa | - | UXQA 交付验收关（档案与主表架构页面）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | project | - | 主表架构实现（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | archive | - | 档案数据合并逻辑修复（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | archive | - | 档案 schema 字段完整性修复（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | archive | - | 档案模块5项测试问题修复（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | archive | - | 档案详情页增强（记录数据管理）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | uxqa | - | 全模块 API 测试 + UXQA 巡检（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | project | - | UI修复5项问题（用户测试报告）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | archive | - | 档案模块代码修复（对齐新模型结构）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-22 | archive | - | reqa 档案模块增量概念设计（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-21 | modeling | - | 用户4项需求增强（主键列/ER缩放/分页/字段去重）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-21 | project | - | 关系管理功能增强（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-21 | modeling | - | Bug 修复（进度条堆叠 + ER图中文名）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-21 | project | - | 数据源配置修复 + 测试连接（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-21 | project | - | 数据源驱动扩展（SQL Server + Oracle）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-21 | uxqa | - | UXQA 整改（R-007~R-010）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-21 | uxqa | - | UXQA 第四轮交付验收关（新增尺寸推理+交互状态巡检）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-21 | project | - | Bug 修复（用户反馈）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-21 | uxqa | - | UXQA 第三轮交付验收关（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-20 | uxqa | - | UXQA 整改（darc 执行）（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-20 | uxqa | - | UXQA 交付验收关（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-20 | project | - | prjm 项目检查（早期日志，见 early-logs.md） | - | - |
| - | 2026-07-17 | modeling | - | 第二轮增强（域管理功能增强）（早期日志，见 early-logs.md） | - | - |

## 未完成事项

### UXQA 整改项（第九十轮全站交付验收，全部已闭环）

| 编号 | 严重度 | 问题摘要 | 状态 |
|------|--------|---------|------|
| R-011~R-031 | P1×14+P2×7 | 全站 17 页巡检（21 项整改含菜单高亮/命名链/scroll.x/弹窗规范/死代码/R-024隔离等） | ✅ 全部闭环（R-024 已隔离待确认删） |

### UXQA 整改项（第三轮新发现，待闭环）

| 编号 | 严重度 | 问题摘要 | 状态 |
|------|--------|---------|------|
| R-007 | P2 | FieldMapping.vue 创建时间未用 formatDateTime | ✅ 已闭环 |
| R-008 | P3 | FieldMapping.vue 新建映射按钮未做 <2 表禁用 | ✅ 已闭环 |
| R-009 | P3 | TableList.vue 展开行与弹窗注释编辑双入口 | ✅ 已闭环 |
| R-010 | P2 | FieldClassification.vue 分组重命名未持久化 | ✅ 已闭环 |

### UXQA 整改项（第一轮全部已闭环）

| 编号 | 严重度 | 问题摘要 | 状态 |
|------|--------|---------|------|
| R-001 | P1 | 域列表创建时间格式统一 | ✅ 已闭环 |
| R-004 | P1 | 数据预览提示改进 | ✅ 已闭环 |
| R-002 | P2 | 域列表操作列增加「管理表」入口 | ✅ 已闭环 |
| R-003 | P2 | 表列表提示文字调整 | ✅ 已闭环 |
| R-005 | P2 | Excel 上传后自动预览 | ✅ 已闭环 |
| R-006 | P2 | 左栏滚动条样式 | ✅ 已闭环 |

### 其他

- auth 和 quality 模块尚未启动设计
