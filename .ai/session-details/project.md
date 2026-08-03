# 操作详情 — project 模块（倒序，最新在前）

> 由 rule §3 双层留痕追加；检索方式：按「第N轮」或功能标签 grep。

### 第九十一轮（2026-08-03）标签：基础设施优化

**来源**：better-harness 分析报告（`.qoder/better-harness/2026-08-03/111845-metadata002/findings.json`）

**变更文件**：
- 新建 `.gitignore`（49 行，覆盖 Python/Node/Django/IDE/OS 临时文件）
- 新建 `backend/apps/modeling/tests.py`（56 行，3 个测试类 6 个用例）
- 新建 `backend/apps/archive/tests.py`（62 行，3 个测试类 6 个用例）
- 新建 `output/delivery-checklist.md`（36 行，9 项验收检查）

**变更摘要**：
- Git 初始化：`git init` + 初始提交（236 文件，34150 行）
- 后端测试：12 个冒烟测试全部通过（模型导入/URL 解析/CRUD/403 拦截）
- 前端类型检查：`vue-tsc --noEmit` 0 errors
- 交付验收标准：3 类 9 项检查（自动化 P0 + 功能 P0 + 质量 P1）

**状态**：完成

### 第六十五轮（2026-07-28）标签：测试报告

- **更早操作**：2026-07-28 — 第六十五轮：测试报告 5 项（FormulaEditor）。①AI 区块与基础信息行间隔：`.ai-generate-block` margin-bottom 8→20px；②AI 生成携带全部引用：handleAiGenerate 改用 refUnion = selectedRefsForAi ∪ validationResult.references（已依赖）∪ unusedReferences（未引用），确保未在表达式中使用的字段也传给 AI 重新生成时考虑；③AI 生成完自动格式化：抽出纯函数 formatExpressionText(raw)（手动格式化与 AI 生成后复用），handleAiGenerate 设置表达式时直接过格式化；④未引用字段合并进依赖行：删除独立 unused-warn 警告条（模板+CSS 全删），dep-list 改为蓝 tag（已引用）+橙 tag（未引用，title 提示）同行展示，v-if 改为两者任一非空；⑤侧栏加宽：`.formula-sidebar` 580→720px、`.cascade-l1` 200→300px（表达式列不需过宽，空间让给字段引用，长表名不再截断）。验证：vue-tsc 0 errors、grep unused-warn 清零；浏览器实跑量化：间隔实测 20px、侧栏 720px、一级栏 300px、.unused-warn 查询为 null（截图工具超时未出图，尺寸均经 getBoundingClientRect 实测）

### 第六十一轮（2026-07-27）标签：-

- **更早操作**：2026-07-27 — 第六十一轮：用户反馈 FormulaEditor 五项调整。①删除「保存并试算」按钮：footer 内 `<a-space>` 包两个按钮改单按钮 `<a-button>保存</a-button>`（与数据预览功能重复，保留 handleSaveAndTrial 函数但不再被模板调用）；②表头第二行颜色再浅一点：`.preview-th-sub` 背景从 #fafafa 改 #f5f5f5（更浅灰，与第一行 #fafafa 有细微区分）；③表格列宽再宽一点：`.preview-th-sub` 的 max-width 从 200px 改 280px（可容 14 中文字符，长字段名不再被截断）；④表达式「格式化」按钮：在「验证公式」按钮左侧新增 `<a-button size="small" type="link">格式化</a-button>` + 新增 `handleFormatExpression` 函数（纯前端实现：抽离字段引用 {...} 和字符串字面量 "..." 用占位符保护 → 函数名大写化（`/\b([A-Za-z_][A-Za-z0-9_]*)\s*\(/g` 匹配标识符后跟 '('）→ 逗号后补空格（统一为 ', '）→ 栈匹配补全缺失右括号 → 还原占位符）；⑤输入框和 label 紧凑化：`:deep(.ant-form-item-label)` 加 `padding-right: 4px`（Ant Design Vue 默认 12px，减小后 label 文字与输入框紧贴）。验证：vue-tsc 0 errors

### 第四十九轮（2026-07-27）标签：同步、测试报告

- **更早操作**：2026-07-27 — 第四十九轮测试报告 4 项处理（第五十轮）：用户反馈 FormulaEditor 四项改进。①AI 生成区移到「计算表达式」label 上方+放大：a-input 改 a-textarea auto-size 2~4 行、按钮改默认 size、新增 ai-generate-block 容器（渐变背景+标题+提示文案）+ aiExplanation 改黄色提示条（icon+text 分离）+ 新增 aiReasoning 折叠展示（a-collapse，后端 generate_formula prompt 加 reasoning 字段要求 LLM 输出完整思考过程，前端 aiReasoning+aiReasoningActiveKey 状态，生成后默认展开）；②窗口 1480→1680px + 侧栏 560→580px + 级联一级栏 140→200px（量化：域 8 最长表名 `IMP_零售_门店_成品交付改造意愿` 18 字符，200px 可容 14 中文字符，超长 ellipsis+title 提示）；③字段引用显示中文名：后端 views.py available_references 新增 display_name 字段（comment or name or code 中文名优先），前端 AvailableReference 类型加 display_name、ref-name 改显示 `ref.display_name || ref.name`、搜索过滤同步支持 display_name；④数据预览改中国式多级表头：前端新增 PreviewColumnItem/PreviewGroup 接口 + refDisplayNameMap computed（ref→中文名查找表）+ previewGroups computed（按表名分组列）+ previewColumnList computed（展平列）；模板改两行表头（第一行分组 colspan+输出结果独立分组，第二行字段中文名子表头）+ tbody 用 previewColumnList 遍历 + preview-td-group-start 分组分隔线。CSS 新增：ai-generate-block/header/row/explanation/reasoning-collapse、preview-tr-group/th-group/th-sub/td-group-start。验证：vue-tsc 0 errors；后端冒烟：available-references 返回 display_name 字段（STORE_NO→门店编码、STORE_NAME→门店名称）、generate-formula 返回 reasoning 字段（完整思考过程）

### 第四十五轮（2026-07-27）标签：去重、测试报告

- **更早操作**：2026-07-27 — 测试报告5项修复（第四十五轮）：FormulaEditor公式编辑器五项优化。①数据预览“只有一个参数在变”真根因：itertools.product顺序截断导致前50行首列恒定（内层循环先变）；后端computed_service新增_sample_combinations确定性随机采样（总组合≤max全量笛卡尔积，否则轮转采样保证每列多样+seed42随机补足去重），同类待修点一并修复：preview_expression正常/语法错误两路径+trial_calculate共三处islice全换；②字段引用Tab前置且默认选中（sideTab默认'fields'，先选字段再选函数工作流）；③④两个Tab改两级级联双栏（左栏cascade-l1 140px选表/函数分类带count徽标+active高亮，右栏cascade-l2单行展示：字段只显示code+name不带长表名前缀、函数name+desc单行ellipsis；删expandedRefGroups/expandedFuncGroups/toggle*折叠逻辑，新增selectedRefTable/selectedFuncCategory+currentRefFields/currentCategoryFns+watch自动选中第一组）；⑤表达式框与侧栏同高（formula-textarea height 330px，cascade height 300px）。验证：vue-tsc 0 errors，Django check 0 issues，冒烟测试通过（域8真实3字段预览50行前两列各10个唯一值，FX_NO数据本身仅1值；语法错误路径正常返回输入列）

### 第四十三轮（2026-07-27）标签：去重、弹窗、测试报告

- **更早操作**：2026-07-27 — 测试报告4项修复（第四十三轮）：FormulaEditor公式编辑器四项优化。①函数库分类分组（后端register_function加category参数+32个函数标注逻辑/字符串/数字/判空/日期五类+get_available_functions返回category；前端groupedFunctions按分类折叠分组展示，默认全展开）；②数据预览默认展示+置底（面板从fommula-main左列移到formula-editor-layout之后窗口底部全宽；打开弹窗有表达式时自动预览+表达式变更800ms防抖后自动预览；后端preview_expression语法错误时仍用extract_references正则提取引用返回输入参数去重组合（输出列隐藏））；③移除字段引用Tab样本值面板（与数据预览功能重复，删ref-values-panel/selectedRef/loadFieldSampleValues/insertLiteralValue，字段改单击直接插入引用）；④窗口加宽960→1280px+字段引用侧栏280→400px+ref-code/ref-name加nowrap省略号（量化：长表名引用约290px，原侧栏可用仅~240px必换行）。验证：vue-tsc 0 errors，Django check 0 issues，冒烟测试通过（五类32函数全分类+语法错误预览返回输入列）

### 第二十四轮（2026-07-24）标签：-

- **更早操作**：2026-07-24 — AI配置模型改纯选择+升级DeepSeek V4（第二十四轮）：①模型字段从 a-auto-complete（可输入可选择）改为 a-select show-search（纯选择可搜索）；②DeepSeek 模型列表从旧版 deepseek-chat/deepseek-reasoner 升级为 deepseek-v4-flash/deepseek-v4-pro（旧模型 2026-07-24 停用）；③默认模型改为 deepseek-v4-flash；④DeepSeek API 地址从 https://api.deepseek.com/v1 改为 https://api.deepseek.com（官方最新）。验证：vue-tsc 零错误

### 第二十二轮（2026-07-24）标签：-

- **更早操作**：2026-07-24 — AI配置页精简（第二十二轮）：用户嫌配置项太多。经 AskUserQuestion 确认①主区只留「模型+API Key」，服务厂商/接口地址/采样温度/超时/名称/启用全部折叠进 a-collapse「高级设置」（默认收起）；②模型由「厂商select+模型select/input」改为单个 a-auto-complete（可选可输入），选中预设模型经 MODEL_INDEX 自动带出厂商+接口地址，直接手输新模型名（如 DS-V4flash）则保持当前接口地址不变。提示词配置区保持折叠不变。DeepSeek 预设模型 API id 保持 deepseek-chat/deepseek-reasoner（用户可自行输入新名）。验证：vue-tsc 零错误
