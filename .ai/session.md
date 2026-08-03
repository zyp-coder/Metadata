# 会话接力 — 主文件（当前状态 + 功能索引）

> 启动只读本文件（rule §3）。历史详情按模块存于 `.ai/session-details/<模块>.md`（archive / modeling / uxqa / project / early-logs），确认需求后按「模块+功能标签/第N轮」grep 加载，禁止全量读。

## 当前会话状态

- **当前阶段：**第九十一轮 better-harness 基础设施优化完成（Git 初始化 + 测试套件 + 交付验收标准）；待办：R-024 待用户确认删除 legacy/ 目录、ArchiveApi 鉴权强化、源优先级配置(BR-018-1)、血缘历史时间线
- **活跃模块**：uxqa、archive、modeling


### 最近 3 轮详情（满 3 轮后最旧一轮下沉到详情文件）

- **上次操作**：2026-07-25 — 第九十轮：UXQA 全站 17 页交付验收巡检。整改清单 R-011~R-031（21 项，P1×14+P2×7），用户确认“P1+P2 全部”，按 4 批次执行：批A(全局+archive R-011~016)→批B(modeling R-017~023)→批C(R-024隔离+settings)→批D(P2泛化+死代码)，每批 vue-tsc 0 errors。关键整改：MainLayout watchEffect 菜单高亮同步路由；命名链「变更日志」统一；ArchiveDetail 递归 scroll.x + formatDateTime + extractApiError；DomainFieldConfig 左栏 500→270px + a-empty 插槽修复 + confirmReleaseMember；DomainFieldMapping ER图高度动态+事件修正+先建后删；FormulaEditor 补「保存并试算」按钮；旧向导四页移 legacy/ 摘路由；TechFunctions/AIConfig 弹窗规范化；scroll.x 8 处统一；死代码清理 6 文件≈200 行。vue-tsc 最终 0 errors。整改清单全部销号。
- **更早操作**：2026-07-30 — 第八十八轮：测试报告 7 项全栈整改（/modeling/domains/8/fields 3 项 + /archive/5 3 项 + /archive/versions 1 项；AskUserQuestion 四决策：①蓝色长字=**改图标按钮**②问题4=**详情即编辑**（推翻查看/编辑分离）③记录信息取值=**落库快照**④问题7=**合并为一页**（推翻第八十二轮三菜单中的独立版本管理定位））。问题1：DomainFieldConfig 组合字段表「设为主字段」蓝色长链接改灰色 KeyOutlined 图标按钮+tooltip，列宽 110→70。问题2：loadAttrTabData 计算字段行 group 硬编码 null→c.group ?? null（属性配置与字段分组 Tab 分组口径一致）。问题3：删属性配置「主字段」列（列定义+模板分支+openMembersDistinctFromAttr，删前 grep 零引用）。问题4：ArchiveDetail 详情弹窗单模式化——删「编辑」入口/drawerEditMode/openEditDrawer/switchToViewMode，弹窗=元信息 descriptions+业务数据直接可编辑控件（source 字段 disabled）+变更预览+关闭/保存（无变更禁用），openDetailDrawer/openChangeRecord 打开即初始化编辑数据。问题5：ArchiveChangeDetail 加 record_label CharField(500)（迁移0008），serializers 新增 _composite_label_codes（域内 active+release_to_archive SF 的 standard_code 列表）+_build_record_label（值拼接 ' / ' 截500）两 helper，写入点两处=编辑链路 UpdateSerializer+同步链路 _sync_data_from_sources 批次落库（data_map 按 record_id 批量取 data），存量回填脚本 backfill_change_record_label.py 跑完 5773 条；ChangeDetailSerializer/GlobalVersionSerializer 加 record_label，GlobalVersionSerializer 另加 record_version（记录当前最新版本号，记录已删返回 null）；前端变更明细表加「记录信息」列（record_label||record_key 回落+tooltip）。问题6：版本对比基准改「选中版本(v1) ↔ 当前最新(v2)」——ArchiveDetail.viewVersionDiff 用 selectedRecord.version、VersionManagement.viewDiff 用 ver.record_version（null=已删/≥最新守卫），diff 弹窗文案「v{n}（选中） ↔ v{m}（最新）」。问题7：VersionManagement.vue 整页重构为「变更与版本」（评估结论：底层两套模型职责不可替代——版本=快照/回滚/定版、日志=批次/审计/导出，重复仅在展示层）——右上 radio 双视图：主视图=全局变更日志（change-details API 全局过滤 archive/change_source/change_type/record_key+记录信息列+「进入档案」跳转），次级视图=版本记录（原表格+记录列改记录信息列 record_label）；MainLayout 菜单/router meta.title「版本管理」→「变更与版本」。验证：vue-tsc 0 errors、后端重启（旧 PID 15876→新进程）后 API 实测（change-details 5773 条含 record_label/archive_name✓record-versions 11683 条含 record_version/record_label✓）、Browser 端到端 9/9 PASS（图标按钮/无主字段列/分组一致/操作列无编辑/详情即编辑弹窗/记录信息列/合并页双视图/菜单改名），验证截图已清理。constitution 登记 4 条决策（含 2 条推翻），design-diary-archive v14、design-diary-modeling v11 已登记
- **更早操作**：2026-07-30 — 第八十七轮：测试报告 8 项全栈整改（/modeling/domains/8/fields 1 项 + /archive/5 7 项；AskUserQuestion 四决策：①抽屉vs弹窗=**改大弹窗**推翻 2026-07-22 抽屉决策②蓝色字含义=用户 Other 澄清「和字段分组有关的标题用蓝色」非值文本③变更定位=仅打开详情弹窗④日志补全=全部补齐）。问题1：DomainFieldConfig 组合字段表操作列前插「主表」（只读金tag/灰—）+「主字段」（金tag/「设为主字段」链接→setPrimaryFromComposite 走 set-primary-field 端点）两列，移除原内联 tag。问题2/3/4：ArchiveDetail 详情/编辑 a-drawer→a-modal（1100px/footer null/70vh 内滚），detailDrawer 改名 detailModal，groupTitleStyle 全级别蓝色系（level1/2 #1890ff、level3 #40a9ff），删 recordModal 死代码抽屉及 6 个无引用函数（-163行，删前 grep 确认零调用点）。问题5：后端 8 处 change_summary 补齐统一 {action,changed_fields} 结构（views.py：sync CREATE 全字段初值/perform_destroy 状态变化+快照字段数/rollback×2/pin_version/pin/unpin/refresh SYNC；serializers.py：CreateSerializer 加 action+全字段初值、UpdateSerializer 重构 summary_changes 含状态变化+action 区分「档案侧人工编辑/启用记录/停用记录/保存记录(无字段变化)」——状态切换不再显「-」）；前端 ArchiveDetail+VersionManagement 版本渲染加 action 行。问题6：记录表筛选工具栏（数据内容搜索+同步/记录状态下拉+查询/重置；后端 ArchiveRecordViewSet 删 search_fields、get_queryset 手动处理 search：annotate(Cast('data',TextField())) icontains）。问题7：左侧字段导航面板（190px，groupedSchemaBlocks 渲染蓝色分组标题+字段列表，scrollToFieldColumn 按列序 idx*DATA_COLUMN_WIDTH 横滚定位+col-flash 2.6s 淡橙高亮，customHeaderCell/customCell 挂类）。问题8：变更明细行点击/「查看记录」列→openChangeRecord（record SET_NULL 为 null 提示「已被物理删除无法定位」；否则 archiveRecordApi.get 打开详情弹窗+highlightChangedCodes 高亮变更字段 #fff7e6，openDetailDrawer/openEditDrawer 重置）。验证：vue-tsc 0 errors、后端重启（旧 PID 30160→新 15876 监听唯一）后 API 200（search+status 组合；注意路由是 /api/records/ 非 /api/archive/records/）、Browser 端到端 7/7 PASS（搜索 974→6 条过滤/重置恢复、弹窗化、蓝标题、字段导航定位、版本 action 文本、变更点击定位）。constitution 登记 4 条 v13 决策（含推翻抽屉），design-diary-archive v13 已登记

## 功能索引（倒序，每轮一行；完整性/确认点自本次迁移后开始记录）

| 轮次 | 日期 | 模块 | 功能标签 | 一句话摘要 | 完整性 | 确认点 |
|------|------|------|----------|------------|--------|--------|
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
