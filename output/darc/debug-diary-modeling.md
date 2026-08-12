# Debug 日记 — modeling 模块

> 记录 modeling 模块的 Bug 根因、修复方式与已知耦合点，供后续影响分析使用。

## BUG-2026-0811-02 关系创建报「字段 source_table, source_field, target_table, target_field 必须能构成唯一集合」
- **现象**：新建字段映射（物料主表与物料信息表普通关联）点 OK 报 DRF 默认唯一性模板错误，用户不知被哪条已存在关系占用
- **根因**：FieldMapping `unique_together=(source_table, source_field, target_table, target_field)`（models.py L563），FieldMappingSerializer 无自定义校验器 → DRF UniqueTogetherValidator 默认模板；前端无预检；存量 3 条映射（id=3 销售价目表明细→物料 detail / id=4 物料分组→物料 detail / id=5 物料→物料信息 reference），用户建的四元组与 id=5 重复（AskUserQuestion 确认场景=普通字段关联）
- **同类排查**：modeling 模块 8 处 unique 约束仅 DetailTableConfig（BUG-2026-0811-01 已修）与 FieldMapping（本次）有自定义校验器；其余 7 处（Table/Field/StandardField/ComputedField/ConfigTable 编码、FieldOption 枚举值、Domain 编码、DataSource 名称）仍为默认模板——用户确认分批处理
- **修复**：FieldMappingUniqueValidator(UniqueTogetherValidator) 子类化（与 DetailTableUniqueValidator 同模式）：捕获默认 ValidationError → 查 dup（编辑排除自身）→ 重抛友好错误（占用关系 表名.字段名 → 表名.字段名 + ID + 关系类型 + 指引）；前端 handleSubmit 加 checkMappingDuplicates 预检（composite 展开逐对、排除编辑自身、命中 message.warning 拦截不发请求）
- **影响范围**：FieldMappingSerializer（普通关联+detail 挂载两入口）；编辑模式排除自身不误伤；无数据迁移；注意：存量 id=4 detail 映射 detail_config 为空（旧范式遗留），编辑它会触发「必须挂载到已注册的子表配置」校验——与本次无关，待用户遇到再处理
- **验证**：后端 APIClient 6 项全过（重复 id=5→400 友好、重复 id=3 detail 挂载→400 友好、全新 201+204 清理、编辑自身 200、编辑撞他人 400 友好）+ vue-tsc 0 + django check 0 + 浏览器实测预检拦截（message.warning 指明 ID=5、弹窗保持打开未提交）
- **教训**：DRF 默认唯一性模板对用户不可读（不指明占用方）是系统性缺陷，同类约束应统一子类化模式分批处理

## BUG-2026-0811-01 子表注册保存报「字段 domain, table 必须能构成唯一集合」

- **现象**：用户新建子表注册（预组合），选头表+明细表后点 OK 报错「字段DOMAIN，TABLE，必须能构成唯一集合」（DRF UniqueTogetherValidator 默认中文模板）。
- **根因（两层）**：
  1. **直接原因**：同一域内一张明细表只能注册一次（`unique_together=(domain, table)`，table=明细表），用户选的明细表已被现有注册占用——域「产品」已有价格组合（明细=销售价目表明细）与分组组合（明细=物料分组_L），用户想重新注册分组组合即撞唯一约束。
  2. **体验缺陷**：注册弹窗明细表下拉无「已注册」标记/禁选，用户无从得知哪些明细表已被占用；后端报错是 DRF 默认模板，不指明被哪个组合占用；「管理注册」入口只有新建弹窗，无已注册列表/编辑入口（`dcListModalVisible` 死变量，列表管理当初做了未完成）。
- **方案对比（用户确认方案A）**：A=前端禁选+后端友好报错+列表管理入口（治本）；B=仅后端友好报错（用户仍要踩错才明白）；C=仅前端禁选（绕过 API 时提示仍不友好）。
- **修复**：
  1. 后端 `serializers.py`：新增 `DetailTableUniqueValidator(UniqueTogetherValidator)` 覆盖默认唯一性校验器（放在 `Meta.validators` 中**追加**于默认校验器之前，冲突时先抛友好错误、默认模板不再触发），报错指明「明细表『xx』已注册为组合『头+明细』（ID=N）；一个明细表只能注册一次，如需修改请在「管理注册」中编辑」。
  2. 前端 `DomainFieldMapping.vue`：①新建弹窗明细表下拉：已注册的显示「已注册（xx组合）」标记并禁选（`dcRegisteredMap` computed）；②「管理注册」/顶部「子表注册」按钮均改为打开列表管理弹窗（复活 `dcListModalVisible`，表格列：预组合/关联字段/行键/排序/挂载数/操作）；③列表支持编辑（`openDetailConfigEdit` 回填表单+加载字段池，头表/明细表/关联字段禁改）与删除（`removeDetailConfig`，popconfirm 提示挂载影响——`detail_config` FK 为 SET_NULL，删除后映射变未挂载，不级联删映射）。
- **同类点（记录待办）**：`FieldMapping` 的 `unique_together=(source_table, source_field, target_table, target_field)` 同样使用 DRF 默认错误模板（重复挂载时用户同样看不懂），本次未一并处理（超出用户确认的方案A范围），待用户确认后同类修复。
- **验证**：后端实测 5 项全过（重复注册分组组合→400+友好错误指明 ID=3；重复价格组合→400；全新组合→201 后 204 清理；编辑自身→200 不误伤；关联字段归属校验→400 未破坏）；vue-tsc 0 errors；浏览器实测 4 项（顶部子表注册→列表弹窗✓；新建弹窗明细表下拉已注册标记+禁选✓；列表编辑→回填+字段池+4 个 select 禁用✓；挂载弹窗管理注册→列表弹窗✓）。删除 popconfirm 为 antd 标准 hover 交互，模拟事件无法触发（browser-use 限制），其调用的 DELETE API 已后端实测 204。
- **教训**：DRF `Meta.validators` 是**追加**到默认校验器（含 ModelSerializer 自动生成的 UniqueTogetherValidator）且对象级校验器签名是 `__call__(attrs, serializer)`——自定义唯一性错误应子类化 `UniqueTogetherValidator` 覆盖 `__call__`，不能写裸函数（签名不符直接 TypeError）也不能指望覆盖（追加语义，需保证自定义先抛错才拦得住默认模板）。

## BUG-2026-0804-02 档案同步统计虚高 + 组合字段非主字段被错误更新

- **现象**：用户新建档案后，版本管理页显示「近7天修改记录: 3187」，但实际只有 974 条记录。
- **根因（两层叠加）**：
  1. **统计口径问题**：同步多个表时，第 1 个表创建 974 条记录，后续 6 个表同步到这些「刚创建」的记录时都计入「修改」→ 3187。
  2. **组合字段处理缺失**：组合字段的非主字段成员也被写入档案数据，导致大量不必要的「修改」记录。
- **修复**：
  1. 新增 `created_in_this_batch` 集合，跟踪本轮同步刚创建的记录 ID，后续表同步到这些记录时不计入「修改」。
  2. 新增 `_build_sync_exclude_codes()` 函数，构建组合字段非主字段成员的排除集合。
  3. `_upsert_records_from_rows()` 接收 `sync_exclude_codes` 参数，遇到排除集合中的字段时跳过不写入。
- **已知耦合点**：
  - 组合字段的主字段（`primary_field_id`）仍正常同步，只有非主字段成员被排除。
  - 一致性检查（`_run_consistency_check`）不受影响，仍会采集非主字段成员值用于比对。
- **验证**：修复后同步统计从 3187 降至 974（与实际记录数一致）；18 个 archive 测试全 PASS。

## BUG-2026-0804-01 API 端点 POST 方法不被允许

- **现象**：前端调用 `/api/field-mappings/infer-mappings/` 返回 "方法 POST 不被允许"。
- **根因**：后端代码已更新但服务器未重启，旧进程没有新路由。
- **修复**：重启 Django 开发服务器 `python manage.py runserver`。
- **已知耦合点**：
  - 新增 `@action` 端点后必须重启服务器（StatReloader 不会自动加载新路由）。
  - 单元测试通过不代表 API 端点可用——必须实际 HTTP 调用验证。
- **验证**：`requests.post('http://127.0.0.1:8000/api/field-mappings/infer-mappings/', json={'domain': 8})` 返回 200。
- **教训**：编码收尾的「编译/测试通过」不能只跑单元测试，新增 API 端点必须实际 HTTP 调用验证。

## BUG-2026-0728-02 试算弹窗测试值下拉全部 No data

- **现象**：新建计算字段后打开枚举试算弹窗，参数表「测试值」下拉框全是 No data。
- **根因**：引用字段从未同步过去重值（distinct_values=None）时：
  1. `computed_service._build_param_space_from_distinct` 直接用 `['']` 占位不查库 → auto_enumerate 回填全空；
  2. `available_references` 的 sample_values 也只读缓存 → 前端 distinct_values=[]。
  而项目已有 `_ensure_distinct_cache` 按需填充机制（AI查重/组合字段抽屉/刷新去重都在用），唯独试算路径漏接——同类模式缺失。
- **修复**（治本，第六十九轮）：去重缓存工具抽独立模块 `backend/apps/modeling/distinct_cache.py`（ENGINE_MAP/json_safe/fetch_distinct_values/ensure_distinct_cache），views.py 改为 import 别名兼容旧引用；`_build_param_space_from_distinct` 对 distinct_values is None 的字段按需 `ensure_distinct_cache([field_obj])`（失败不阻断降级占位）。
- **已知耦合点**：
  - `distinct_cache.py` 不得 import views（依赖方向：views/computed_service → distinct_cache）；新增需要去重缓存的路径一律复用 `ensure_distinct_cache`，禁止再写只读缓存的降级分支。
  - 外部数据源不可达时 ensure 会记录 errors 不抛异常，试算降级为占位 `['']`——沙箱/断网环境下 No data 仍可能出现，属环境问题非代码问题。
- **验证**：APIClient 实测 trial-calculate 200；standard-fields 28 行全带 distinct_values；vue-tsc 0 errors。

## BUG-2026-0728-01 计算字段保存失败（表面像 IFS 表达式问题）

- **现象**：新建计算字段填入 IFS(...) 表达式，点「保存」只提示「保存失败」，连点多次无效。
- **根因**（两层叠加）：
  1. 数据层：`ComputedField` 有 `unique_together('domain','code')`，用户重建的编码 `store_status` 被**已废弃**（status='discarded'）的同名字段占用 → DRF 返回 400 `{"non_field_errors":["字段 domain, code 必须能构成唯一集合。"]}`。
  2. 前端层：全前端 catch 统一写 `e.response?.data?.error || '兜底文案'`，DRF 的 `non_field_errors`/字段级错误被吞，用户只见笼统「保存失败」。
- **排除项**：IFS/AND/NOT/ISBLANK/`=`/TRUE 均被 formula_engine 支持，相同表达式换新编码实测 201 创建成功（表达式无任何问题）。
- **修复**：
  1. 新建 `frontend/src/utils/apiError.ts` → `extractApiError(e)`：依次解析 error → detail → message → non_field_errors → 字段级错误；全前端 31 处 catch 统一替换（7 文件：DomainFieldConfig 15、FormulaEditor 7、TableList 13→合并复合模式、TrialCalculation 2、DomainFieldMapping 1、TechFunctions 3、ArchiveDetail 2）。
  2. 后端 `ComputedFieldViewSet` 新增 `_code_conflict_response()` 前置校验（create/update 均拦）：编码被废弃字段占用 → 「编码「xxx」已被废弃字段「yyy」占用：请到左栏「废弃字段」分类恢复它，或换一个编码」；被活跃字段占用 → 提示已存在。
- **已知耦合点**：
  - `unique_together('domain','code')` 在 models.py L423，废弃字段不释放编码——这是有意设计（废弃可恢复），前置校验必须区分 discarded/active 给不同指引。
  - 前端新增错误提取入口统一走 `@/utils/apiError`，后续新 catch 禁止再手写 `e.response?.data?.xxx` 链。
- **验证**：APIClient 实测 T1 新编码+IFS=201、T2 重复编码=400 且返回新指引文案；vue-tsc 0 errors。

## BUG-2026-0805-01 DomainList 操作列链接换行（用户反馈「还是换行了」）

- **现象**：/modeling/domains 表格操作列「管理表/关系管理/字段管理」链接内部文字折行，行高被撑高。
- **根因**（量化）：操作列宽 280px − 单元格左右 padding 32px = 可用 248px；内容实需：4 链接文字 182px + 3 个 vertical divider ≈51px + a-space 默认 size8 的 6 个间隙 48px ≈ 281px > 248px → 链接内文字被压折行。历史脉络：R-004 曾定案「fixed:right+nowrap」但后续闭环时 nowrap 未真正落码（DomainList 的 a-space 一直裸写），第 109 轮 uxqa B2 抽检只覆盖 ArchiveList/VersionManagement/ApiManagement 漏了 DomainList，且目测「宽度充裕」未实算 → 漏检。
- **修复**（第一百一十轮，统一全站操作列范式 = ArchiveList/ArchiveDetail 既有写法）：
  1. DomainList.vue：a-space 补 `:size="4" style="white-space: nowrap"`，操作列宽 280→320（可用 288 ≥ 实需 257）。
  2. 同类防御（Step2 全排查）：DataSourceList.vue（160px 列/实需≈74px）、DomainFieldMapping.vue（120px 列/实需≈72px）操作列同样补 `:size="4" + nowrap`——当前不折行，防未来加按钮复现。
  3. 附带（同报告第 2 项，archive 模块）：ArchiveList 操作列「一致性检查→检查、从数据源同步→同步」（用户指定精简）。
- **uxqa 漏检复盘**（用户确认仅复盘不补规则）：① 闭环验收与代码实情脱节——R-004 标「平铺已落实」但 nowrap 从未落码；② B2 操作列检查抽样不全（漏 DomainList）且未量化实算；③ 命名精简无检查项覆盖（R-042 只管页面标题前缀）。
- **验证**：浏览器实测 /modeling/domains 操作列 spaceWidth=257<320、white-space=nowrap、7 个 space-item 同一 top 无折行；/archive 链接为 编辑/检查/同步/删除、spaceWidth=187 无折行；vue-tsc 0 errors；截图 fix_verify_domains_action_nowrap.png / fix_verify_archive_action_short_names.png。
- **教训**：操作列 a-space 一律 `:size="4" style="white-space: nowrap"` 起步；uxqa 闭环项必须 grep 代码证据而非凭上一轮结论。
- **改向补记（同轮稍后）**：用户改向「那你加上吧」，两条补强已写入 uxqa 方法论（frontend-delivery-checklist B2 硬约束：禁抽样/禁目测/闭环复检必 grep 代码证据；A9 增操作列文案专项：≤2 字动词、对象来源不进按钮名、全站枚举逐列核对；popup-layout-spec 命名节同步增条目）。另核实修正：复盘表中「命名精简无检查项」表述不准——A9 本就存在，真实缺口是未覆盖操作列文案且未要求逐列核对。
