# 操作详情 — modeling 模块（倒序，最新在前）
> 由 rule §3 双层留痕追加；检索方式：按「第N轮」或功能标签 grep。
## 第一百五十八轮（2026-08-13）标签：诊断、部署未生效、--noreload、dist旧构建、编辑修改不行
**任务**：用户反馈「为什么还是不行，我用编辑来修改不行」（第一百五十七轮挂载字段放宽+一对多落地后，编辑挂载仍失败）。
**读取文件**：
- `.ai/session.md`、`output/darc/dev-diary-archive.md`（用户改动已提交，无 diff）
- `backend/apps/modeling/serializers.py`（L374-395 validate 已放宽，无主键校验）
- `frontend/src/views/modeling/DomainFieldMapping.vue`（openEdit L1485-1526 回填正常；detail 分栏模板无禁选；handleSubmit 先建后删+detail PATCH 正常；dcModal 编辑模式 4 处 `dcEditingId ? field-item--disabled` 禁选为第一百四十二轮设计）
- git show 6436c2c（第一百五十六轮）：serializers validate 仍含 `if target_f and not target_f.is_primary_key: raise '明细子表关系的目标字段必须是目标表的主键字段'`
- 进程/端口/构建时间实证
**变更摘要**：无代码变更（纯诊断轮）。证据链：
1. 后端进程 35252（manage.py runserver 0.0.0.0:8000 **--noreload**）启动于 8/12 16:56:50 < serializers.py 最后修改 8/13 15:20:02 → **本地后端实际跑第一百五十六轮代码**（validate 仍强校验主键，选 GROUP_ID 保存必 400）
2. frontend/dist 全部产物构建于 8/8 17:08:50 → 156/157 轮前端改动（非主键可选、左右分栏）未进入
3. 本地端口全景：8000=Django（旧）、8080=edb Apache（无关）、无 nginx/vite/serve 服务 dist → **本地无本项目前端服务**
4. git：157 轮改动 5f4d81c+c9fd200 于 8/13 15:29 已推送 origin master；deploy/sync.sh 路径已修正（b9a4a2f，/opt/metadata）
**结论**：用户「编辑点不动/保存报主键错」= 旧代码必然现象，非功能缺失。代码本身已就绪。
**验证**：无需测试（无代码变更）；部署验证待用户执行。
**遗留**：用户确认访问服务器 + 将重新跑 deploy/sync.sh 后再试；若部署后仍不行再排查（需部署日志/报错信息）。**教训**：--noreload 后端改代码后必须手动重启、dist 必须重建，用户报「功能不行」先查运行版本再查代码。

## 第一百五十七轮（2026-08-13）标签：方向修正、挂载字段任意键、一对多归属、GROUP_ID、同步归属机制
**任务**：用户方向性纠正——「为什么和预组合表的关联字段只能是主键呢？？？我们的设计应该是任何键啊」+ 拍板方案B「B，支持挂载的字段一对多啊。。场景很现实啊。。我的是物料主数据，物料表和物料分组预组合表的关联。。肯定是用GROUPID来关联的啊」；AskUserQuestion 确认一对多方向=明细行挂到所有同值主记录（推荐项）。
**读取文件**：
- `backend/apps/archive/views.py`（_sync_detail_rows 归属机制改造）
- `backend/apps/modeling/serializers.py`（挂载字段校验放宽）
- `backend/apps/modeling/views.py`（detail-check 简化）
- `frontend/src/views/modeling/DomainFieldMapping.vue`（主表字段全可选）
- `backend/apps/archive/tests.py`（新增 DetailSyncOneToManyTest）

**变更摘要**：
- 后端 archive/views.py `_sync_detail_rows` 归属机制核心改造：
  - 归属键从「主表主键 pk_fields」改为「挂载字段 detail_fm.target_field.code」：code_to_physical+match_channels 构建 target_physical_to_schema（本表+头表物理列），无映射→warnings+return 不静默
  - existing_records 改多值索引 `{挂载字段值: [records]}`（active 优先 insert(0)）
  - 明细行 upsert 循环 `for existing in existing_list:`——同值多主记录全部挂载（一对多）
  - _record_key_for_row 从行内取挂载字段物理列值（含 __hdr__ 头表前缀回退），无值返回 None 跳过
  - 代表行折叠按挂载字段值分组（seen_keys），每组首行写所有同值主记录（key=(rep_key,)）
- 后端 modeling/serializers.py：移除 target_field is_primary_key 强校验（保留 detail 必填 detail_config/target_field）
- 后端 modeling/views.py detail-check：方向异常检测简化为仅「未配置挂载字段」suspect（同步侧警告兜底）
- 前端 DomainFieldMapping.vue（6 处）：主表字段「仅主键可选」→全部可选（移除 field-item--disabled）；删除主键警告 alert+detailTargetNoPk computed；detailRecommendedFieldId 改按已选目标字段 code 匹配（未选回退主键）；loadTargetFields detail 分支默认推荐单一主键保留；handleSubmit 文案改「请选择主表端关联字段」；selectDetailTargetField 移除主键拦截+触发重新推荐
- 新增测试 DetailSyncOneToManyTest 3 条（域 DSYNC1N：主表 MATERIAL_ID 主键+MATERIAL_GROUP 非主键 / 明细分组头 FID 主键+GROUP_ID 非主键；G1→M1,M2 一对多+代表行共享；第二轮幂等；G9 未匹配跳过）

**验证**：vue-tsc --noEmit 0 errors + py_compile 3 文件 OK + DetailSyncOneToManyTest+DetailSyncEngineTest+ArchiveRecordDetailModelTest 14/14 + 全套 105/105 PASS
**遗留**：服务器部署后需重新构建前端+重启后端生效（release.ps1 / deploy/sync.sh 一键发布）。

## 第一百五十六轮（2026-08-13）标签：测试报告1问题、预组合关系表单、左右分栏、左源右目标、匹配字段点选
**任务**：用户新测试报告1个问题：新建/编辑映射弹窗选「预组合关系」时界面没有匹配字段可选功能，且不是左源右目标设计（XPath 指向 body/div[6] 弹窗容器）。
**读取文件**：
- `frontend/src/views/modeling/DomainFieldMapping.vue`（核心修改）

**变更摘要**：
- detail 分支表单（原 a-select 下拉：主表/预组合/关联字段）改为左右分栏（与 reference 分支同构）：
  - 左侧（span=12，内 8|16）：预组合列表（点击选择，名称+编码+行键小字，header 带「管理注册」入口）+ 关联字段列表（点选，⚿ 主键标 + 推荐 tag，空态「请先选择预组合」）
  - 中间（span=1）：→ 箭头（padding-top 200px）
  - 右侧（span=11，内 8|16）：主表列表（点击选择，targetTableOptions 排除预组合明细表）+ 主表字段列表（点选但仅主键可选，非主键 field-item--disabled——挂载目标固定为主表单一主键）
- 配置摘要（含条件/挂载数）+ 主键警告 alert 保留在分栏下方
- 新增函数：selectDetailSourceField（置 sourceFieldTouched 防自动推荐覆盖）、selectDetailTargetField（非主键点击拦截）
- 复用：onDetailConfigChange（预组合点选→加载关联字段池+清主表冲突）、selectTargetTable/loadTargetFields（主表点选→自动选单一主键）、onDetailSourceFieldChange（避免死代码）
**验证**：vue-tsc --noEmit 0 errors；已 commit+push（ab4c32c）
**遗留**：无（form 结构不变，handleSubmit/openEdit/openCreate 零改动）。

## 第一百五十五轮（2026-08-13）标签：测试报告3问题、dcModal左右分栏、JOIN类型、dcList搜索、条件构建器头表字段、UXQA巡检
**任务**：用户新测试报告3个问题修复，全部在 /modeling/domains/2/mappings 页面，按4批处理。
**读取文件**：
- `frontend/src/views/modeling/DomainFieldMapping.vue`（核心修改）
- `backend/apps/modeling/models.py`（DetailTableConfig 加 join_type）
- `backend/apps/modeling/serializers.py`（字段列表加 join_type）
- `backend/apps/modeling/migrations/0034_detailtableconfig_join_type.py`（新增迁移）

**变更摘要**：
- 批1（dcModal左右分栏 + JOIN类型）：弹窗 640px→860px；顶栏关系类型 tag + JOIN type 选择器（LEFT/INNER）；主体左-中-右分栏——左侧头表列表(8col)+头表字段列表(16col)、中间↔箭头+检测按钮、右侧明细表列表(8col)+明细表字段列表(16col)；新增 selectDcHeaderTable/selectDcDetailTable；编辑模式 field-item--disabled 禁选；后端 DetailTableConfig 模型加 join_type 字段（迁移0034）+ 序列化器暴露
- 批2（dcList搜索筛选）：Alert 下方加 a-input 搜索框（dcListSearch）；a-table dataSource 改为 filteredDetailConfigs computed（按头表名/明细表名/编码过滤）
- 批3（条件构建器头表字段）：条件行加"字段来源" a-select（明细/头表）；字段列表按 fieldSource 切换 dcHeaderFields/dcSourceFields；后端存储 field_source 标记；存量兼容默认 'detail'
- 批4（UXQA全页巡检）：映射表加 :scroll="{ x: 1160 }" 防列宽溢出
**验证**：vue-tsc --noEmit 0 errors（批3/批4各验证一次）；已 commit+push（640ff5a）
**遗留**：无。

### 第一百五十四轮（2026-08-13）标签：测试报告8问题、预组合改名、表列表点选、按钮去重、ER预组合标签
**任务**：测试报告8个问题修复，全部在 /modeling/domains/2/mappings 页面，按4批处理。
**读取文件**：
- `frontend/src/views/modeling/DomainFieldMapping.vue`（核心修改，~+97/-57行）

**变更摘要**：
- 批1（#6, #2, #3）：关系类型下拉选项 "引用（字段级映射，默认）"→"普通关系"、"明细子表（整表作为子表挂载到主表）"→"预组合关系"；ER按钮 "预组合表"→"预组合" + font-weight:600；dcColumns 移除 row_key 和 挂载两列
- 批2（#5）：表选择从 a-select 下拉改为左右布局列表点选——源侧 a-col:span=12 内再分 8|16（表列表|字段列表），目标侧 span=11 内同样 8|16，中间箭头 padding-top 200px；新增 selectSourceTable/selectTargetTable 函数（直接切换+清空字段+加载）；field-item--disabled CSS
- 批3（#1, #2）：移除「明细检查」a-badge 按钮，子表注册按钮 type="primary" label="预组合"
- 批4（#8）：ER图 renderER 内建 headerTableToDetails/detailTableToHeaders 查找表，头表节点追加绿色"预组合" tag + 明细表名，明细表节点追加青色"预组合" tag + 头表名
**验证**：vue-tsc --noEmit 0 errors；已 commit+push（3a93caa）
**遗留**：无。

### 第一百四十四轮（2026-08-11）标签：关系管理列表直观性改进、预组合名、主表tag、浅蓝底
**任务**：用户反馈关系管理列表「明细表和主表、普通表的关系不直观」。现状分析（DOM 实证）：detail 行只显示明细表名（预组合信息丢失）、目标表主表地位无体现、普通关联是裸灰字。AskUserQuestion 确认方案A（表格增强）。
**修改文件**：
- `backend/apps/modeling/serializers.py`：FieldMappingSerializer 新增 `detail_config_combo = SerializerMethodField()`——预组合全名「头表名 + 明细表名」（旧注册无头表只返明细表名），get_detail_config_combo 实现；list 字段追加
- `frontend/src/views/modeling/DomainFieldMapping.vue`：a-table 加 :row-class-name="mappingRowClassName"；源表列 detail 且有 combo 时显示预组合全名+蓝色小标「明细子表（预组合）」（列宽 150→260）；目标表列主表金色「主表」tag（primaryTableId computed=domainTables 中 is_primary）；关系类型列普通关联裸灰字→灰色 tag「普通关联」；mappingRows 分组/联合分支透传 detail_config_combo；style 加 `:deep(.mapping-row-detail) > td { background: #f0f7ff !important }`
**验证**：后端 APIClient 实测 6 条映射 combo 全对（id=3 'EDS_K3_销售价目表 + EDS_K3_销售价目表明细'、id=8/9 同格式、id=4 旧范式 None、reference 无）；vue-tsc 0 errors；django check 0 issues；浏览器 DOM 实测（HMR 后重抓）：4 行 detail 浅蓝底 rgb(240,247,255)、预组合名+小标、目标表=主表 3 行金色「主表」tag、普通关联 tag——首次抓取未见 tag 为 HMR 重渲染时序，二次确认全过；截图存档超时未成（DOM 证据已足）
**数据现状核对**：映射列表 6 条（id=3/4/5/7/8/9）——用户新增 id=7（物料.MATERIAL_ID+MATERIAL_NO→物料信息主表，与 id=5 同对合并为联合字段行）、id=8（物料分组+物料分组→物料信息主表，预组合头表=明细表同名）、id=9（销售价目表+销售价目表明细→物料信息主表）；域主表已由「物料」切为「EDS_K3_物料信息主表」（用户操作）——id=3/4 目标表「物料」无主表 tag 是如实反映
**状态**：完成，收尾留痕完成（dev-diary 第一百四十四轮）
**遗留**：id=4 旧范式 detail 映射仍无预组合名（detail_config 为空，如实显示浅蓝底+原表名）；后续可考虑叠加方案C（行键/排序摘要 tooltip）待用户提出
### 第一百四十二轮（2026-08-11）标签：子表注册唯一性报错修复、预组合、列表管理入口
**任务**：用户新建子表注册选「物料分组+物料分组_L」点 OK 报「字段DOMAIN，TABLE，必须能构成唯一集合」。Bug 六步：Step1 code review（前端 handleDcSubmit payload 正确；后端 unique_together=(domain,table) 触发 DRF 默认 UniqueTogetherValidator）→ Step2 同类排查（FieldMapping 唯一性同类待办；注册管理入口缺失）→ Step3 方案对比（A 禁选+友好报错+列表管理 / B 仅后端 / C 仅前端）→ Step4 影响分析（封闭 modeling 关系管理页+serializer，无迁移）→ Step5 用户确认选方案A → Step6 修复+回归。
**修改文件**：
- `backend/apps/modeling/serializers.py`：新增 `DetailTableUniqueValidator(UniqueTogetherValidator)`（Meta.validators 追加，冲突时抛友好错误指明占用组合与 ID，编辑排除自身），import UniqueTogetherValidator
- `frontend/src/views/modeling/DomainFieldMapping.vue`：新建弹窗明细表下拉禁选+「已注册（xx组合）」标记（dcRegisteredMap computed）；「管理注册」/顶部「子表注册」按钮改为打开列表管理弹窗（复活 dcListModalVisible+dcColumns 6 列）；openDetailConfigManager 拆分为 openDetailConfigList/openDetailConfigCreate，新增 openDetailConfigEdit（回填+字段池并行加载）与 removeDetailConfig（popconfirm 挂载影响提示）；修正 detailConfigApi.delete 方法名
**验证**：后端实测 5 项全过（重复分组组合→400+友好错误指明 ID=3、重复价格组合→400、全新组合→201+204 清理、编辑自身→200、归属校验→400 未破坏）；vue-tsc 0 errors；django check 0 issues；浏览器实测 4 项（子表注册→列表弹窗 2 组合✓/新建明细表下拉 2 项已注册禁选✓/列表编辑回填+4 select 禁用✓/挂载弹窗管理注册→列表✓）
**状态**：修复完成，收尾留痕完成；debug-diary 记 BUG-2026-0811-01
**遗留**：①同类点 FieldMapping 唯一性默认模板待用户确认后修；②删除 popconfirm hover 交互未能浏览器模拟（browser-use 限制），DELETE API 已实测 204；③既有 ABadge offset="[0, 2]" 字符串 prop 警告（非本轮引入，未处理）
### 第一百二十九轮（2026-08-08）标签：/modeling/config-tables、数据源同步、MAP_ORDER多位置、自动调度
**任务**：用户场景——产品分类等配置数据已在外部数据源维护（如 SQL Server 的 METADATA.I_PRD_INFO），需通过 SQL 查询+处理后同步到配置表作为 Key-Value 使用。还要求 MAP_ORDER 支持多位置查找（同一编码不同位置段可能都是工艺/特性/连纹方式）。
**方向判定表**：数据流向 触及但已锁定（单向同步：外部数据源→配置表，不回写源表，符合 Hub 宪法）/ 存储模型 不触及（仍用 JSONField，只是数据来源变了）/ 模块边界 触及但已锁定（配置表仍在主数据域-管理表区域）/ 核心交互范式 不触及（MAP_ORDER 向后兼容，旧公式不受影响）→ 不走 §11.1。
**修改文件**：
- `backend/apps/modeling/models.py`：ConfigTable 模型扩展 3 字段（data_source FK→DataSource, sync_sql TextField, last_synced_at DateTimeField）
- `backend/apps/modeling/migrations/0028_configtable_datasource_sync.py`：迁移文件
- `backend/apps/modeling/serializers.py`：ConfigTableSerializer 加 data_source/data_source_name/sync_sql/last_synced_at 字段
- `backend/apps/modeling/views.py`：
  - DataSourceViewSet 新增 `execute_query` action（只读 SQL 执行，安全限制：仅 SELECT、超时 30s、行数上限 10000）
  - ConfigTableViewSet 新增 `sync` action（调用 _sync_config_table）
  - 新增 `_sync_config_table(table)` 可复用函数（执行 sync_sql→结果前两列写入 columns/rows）
  - 新增 `_parse_table_codes(codes, domain_id)` 辅助函数（分离配置表编码和默认值）
  - 新增 `_lookup_tables(val, table_codes, domain_id)` 辅助函数（在配置表列表中查找值）
  - `func_map_order` 扩展支持多位置模式：检测第2参数是分隔符+第3参数是逗号分隔数字时，进入多位置模式
- `backend/apps/modeling/management/commands/sync_config_tables.py`：管理命令（批量同步所有已配置数据源的配置表，支持 --domain 过滤）
- `backend/apps/archive/apps.py`：daemon 线程搭车配置表自动同步（每 ARCHIVE_AUTO_REFRESH_MINUTES 分钟执行一次）
- `backend/apps/modeling/custom_functions.py`：MAP_ORDER 函数扩展——多位置模式（"5,6,7" 依次取段查表）
- `backend/apps/modeling/tests.py`：新增 test_map_order_multi_position 测试（3 场景：首段命中/第二段命中/全不命中）
- `frontend/src/api/modeling.ts`：ConfigTable interface 加 data_source/data_source_name/sync_sql/last_synced_at 字段；configTableApi 加 sync 方法 + patch 方法；dataSourceApi 加 executeQuery 方法
- `frontend/src/views/modeling/ConfigTables.vue`：新增同步配置区（数据源下拉+SQL 编辑器+预览+同步按钮）；选中表时自动填充 syncForm；同步时先 PATCH 保存配置再执行同步
- `frontend/src/views/modeling/components/FormulaEditor.vue`：新增「配置表」Tab（a-collapse 展示表数据）
**Bug 修复**：
- TIME_ZONE 连接配置缺失：execute_query 和 sync 的 db_config 缺少 TIME_ZONE/CONN_MAX_AGE/CONN_HEALTH_CHECKS/OPTIONS，导致 SQL Server 连接报错 `'TIME_ZONE'`。修复：补全配置（参照 distinct_cache.py 的完整配置）
- PATCH 保存同步配置：前端用 PUT（要求所有必填字段）保存 data_source/sync_sql 导致 400 报错。修复：改用 PATCH（只更新指定字段）
**验证**：迁移 0028 OK✓ 新增 4 测试（10/10 ConfigTable 测试 PASS）✓ 管理命令 sync_config_tables 实测 2/2 成功✓ execute-query API 实测 200 OK✓ sync API 实测 200 OK✓
**状态**：v12 配置表同步功能已闭环，待用户实际使用验证
### 第一百二十八轮（2026-08-07）标签：/modeling/config-tables、MAP_VALUE配置表驱动、ConfigTable、产品编码解析
**任务**：用户有大量产品编码映射场景（如 D_918_5_884_BM_FH_J_3 按分隔符拆分后映射为中文名称），现有 MAP_VALUE 需在公式里写长串映射串，维护困难。用户提出做配置表驱动：提前在管理界面配好映射，公式里只写配置表编码。
**方向判定表**：数据流向 不触及（纯域内查找，不涉及跨系统同步）/ 存储模型 触及但已锁定（JSONField 轻量存储，不物理建表，用户确认）/ 模块边界 触及但已锁定（配置表放主数据域-管理表区域，用户纠正了最初“系统设置”的方案）/ 核心交互范式 不触及（MAP_VALUE 向后兼容，旧公式不受影响）→ 不走 §11.1。
**用户纠正记录**：最初设计为“系统设置里加映射管理页”，用户纠正为“配置表应放在主数据域-管理表区域内，用户自己建表自己维护”。
**修改文件**：
- `backend/apps/modeling/models.py`：新增 ConfigTable 模型（domain FK + name/code/category/columns(JSON)/rows(JSON)/status，unique_together domain+code，轻量级查找表不参与同步/ER图/字段映射）
- `backend/apps/modeling/migrations/0027_configtable.py`：迁移文件
- `backend/apps/modeling/serializers.py`：新增 ConfigTableSerializer
- `backend/apps/modeling/views.py`：新增 ConfigTableViewSet（CRUD + rows action GET/PUT）
- `backend/apps/modeling/urls.py`：注册 config-tables 路由
- `backend/apps/modeling/custom_functions.py`：MAP_VALUE 函数改造——先尝试配置表查找（通过 __domain_id__ + code），未命中则回退旧映射串（向后兼容）
- `backend/apps/modeling/computed_service.py`：_build_context_from_record 注入 __domain_id__ 供 MAP_VALUE 查表
- `backend/apps/modeling/tests.py`：新增 ConfigTableTest（6 测试用例）
- `frontend/src/api/modeling.ts`：新增 ConfigTable interface + configTableApi
- `frontend/src/views/modeling/ConfigTables.vue`：新建 321 行配置表管理页（CRUD + 数据管理弹窗）
- `frontend/src/views/modeling/TableList.vue`：添加「配置表」按钮 + goConfigTables 路由跳转
- `frontend/src/router/index.ts`：添加 /modeling/domains/:id/config-tables 路由
**验证**：迁移 0027 OK✓ 新增 6 测试（41/41 PASS）✓ 全站 114 测试 0 回归✓ vue-tsc 0 errors✓
**状态**：v12 配置表功能已闭环，待用户实际使用验证
**UX 简化（同日追加）**：用户反馈配置表页“看不懂、很多报错、要表的样式”。重写 ConfigTables.vue：去掉多层弹窗（新建弹窗+列定义弹窗+数据管理弹窗），改为 Key-Value 单页体验（新建内联表单→填表名编码→自动展开 Key/Value 两列编辑表→点击列表行切换编辑）。修复 DomainStageNav 组件支持 config-tables stage（新增第四阶“配置表”）。兼容旧表列名映射（第一列→Key，第二列→Value）。vue-tsc 0 errors✓ 41/41 PASS✓
**Bug 修复（同日追加）**：
- 服务器重启：旧 Django 进程（PID 40096）未加载新路由返回 404，taskkill 后重启
- `__domain_id__` 注入：`trial_calculate` 2 处 + `preview_expression` 2 处 evaluate() 调用未注入 __domain_id__，导致 MAP_VALUE 配置表查找失败（报错“映射项格式错误”）。修复后公式预览/试算均正常
- FormulaEditor 侧栏新增「配置表」Tab：显示当前域所有配置表（名称+编码+行数），点击展开 Key-Value 数据（最多 20 行），方便用户写公式时查看
**MAP_ORDER 新函数（同日追加）**：用户场景——产品编码段如“BM”可能是工艺/特性/连纹方式，需依次查多张配置表直到命中。新增 `MAP_ORDER(值, 表编码1, 表编码2, ..., [默认值])`：按顺序依次查配置表，返回第一个命中结果；最后一个参数如果不是已注册的表编码则视为默认值。新增 3 测试（级联首表命中/回退命中/默认值），9 新测试 44/44 PASS✓
### 第一百二十七轮（2026-08-06）标签：/modeling/tables、字段管理大抽屉、R-059、/modeling/domains、分组弹窗、R-061
**任务**：第118轮整改单 5 批计划批4——R-059 字段管理近全屏 modal → 65vw 大抽屉 + R-061 window.prompt → Modal 表单。
**方向判定表**：数据流向 不触及（纯前端容器层）/ 存储模型 不触及（零后端改动）/ 模块边界 不触及（modeling 内部）/ 核心交互范式 不触及（执行已锁定的三维选型决策）→ 不走 §11.1。
**修改文件**：
- `frontend/src/views/modeling/TableList.vue`：字段管理 a-modal（calc(100vw−80px)）→ a-drawer 65vw（destroyOnClose+bodyStyle padding）；footer=null → #footer 固定底栏「关闭」；双 Tab（字段表/数据预览）、主键标识区、fieldTableScrollY、两入口（操作列 openFieldModal+路由参数自动打开）全部不动
- `frontend/src/views/modeling/DomainFieldConfig.vue`：openCreateGroupModal/renameGroup 两处 window.prompt → 共用 groupFormModal（480px a-modal：标题随模式与父级名 computed、空名禁用确认 okButtonProps、重命名预填原名、未改动静默关闭零请求）；submitGroupForm 请求 .then 内显式 groupFormModal=false 关闭
**踩坑（重要，跨项目通用）**：antdv 4.x **声明式 a-modal 的 @ok 不消费 handler 返回值**（Modal.js handleOk 仅 emit('ok')，Promise 自动关闭/loading 仅 Modal.confirm 命令式 API 有）→ 提交关闭必须请求成功后显式置 open=false；catch 不可重抛（antdv 不接 → console unhandled rejection + Vue warn）。v1 用 @ok 返回 Promise 致「提交成功后弹窗卡死不关闭、取消/X 无效」，实测拦截后 v2 修复。
**验证**：vue-tsc -b --force 0 errors；Browser 实测 R-059 6/6 PASS（1257 视口抽屉实测精确 65vw、双 Tab、左侧表列表未被完全遮挡、关闭底栏、切表正确）+ R-061 v2 7/7 PASS（创建/取消/静默关闭/改名/超长名 400 失败保持打开无 unhandled rejection）+ console 0 error；测后清理域 11 恢复原 7 分组。
**状态**：R-059/R-061 闭环，整改进度 7/8，剩 R-060（批5）。
### 第一百一十三轮（2026-08-05）标签：/modeling/fields、属性配置、同名字段标记
**任务**：用户要求在字段属性配置处做同名字段标记与检查（「我那里是支持你改名的」）——第112轮域配置检查只能整体告知，本页补齐定位到行+就地处置能力。
**修改文件**：
- `backend/apps/modeling/views.py`：提取 `_find_dup_unmerged_field_groups(domain)` 口径单点（配置检查 P1-4 与接口共用）；新增 `GET /api/domains/{id}/dup-fields/` 端点
- `backend/apps/modeling/tests.py`：新增 dup-fields 端点实测用例（APIClient 200+结构断言）
- `frontend/src/api/modeling.ts`：domainApi.dupFields
- `frontend/src/views/modeling/DomainFieldConfig.vue`：属性配置 Tab 告警条（N 组冲突+处置指引+只看冲突开关）；冲突行「同名」角标+tooltip；基础/未分配表格 code 列同标记（field_id 精确匹配）；AttrRow 加 physical_field_ids；改名/归并后自动刷新
- `output/darc/REUSE_CATALOG.md`：回写新提取工具函数
**验证**：回归 52/52 PASS；真实请求 GET /api/domains/11/dup-fields/ → 200 返回 4 组（D_CHECK_DATE field_ids=[183,193]）；vue-tsc 0 errors；浏览器实测 4/4（告警条/角标 tooltip/只看冲突过滤/未分配角标），截图 verify_attr_1~4_*.png
**遗留**：域#11 的 4 组冲突现在可在页面上直接看到并处置（改名入口已在该页），待用户实际操作
**同日更正（用户纠正）**：用户指出配置检查只包含已维护到档案的字段（第一百零八轮决策 archive_category='base'），未分配/未分组不包含 → `_find_dup_unmerged_field_groups` 加 base 过滤；前端移除字段分类表格的同名角标（仅保留属性配置 Tab）；新增 2 用例，回归 54/54 PASS。真实域#11 复测 dup-fields 返回空（原 4 组均为未分配字段，档案范围内确无冲突），浏览器 DOM 复核告警条/角标已消失。教训：新增检查项前必须核对既有范围决策
### 第一百一十二轮（2026-08-05）标签：/modeling/domains、配置检查、同名字段归并
**任务**：BUG-2026-0805-01 遗留建议落地——域配置检查新增「多表同名未归并字段」显式告警。
**改向记录**：初案提在一致性检查 issue 体系新增第 5 种检查类型（AskUserQuestion），用户改向「应该放在域管理的配置检查里面」→ 改为 _check_domain_config 新增检查项，一致性检查体系零改动。
**修改文件**：
- `backend/apps/modeling/views.py`：_check_domain_config 8 项→9 项，新增 P1 级 multi_table_dup_field_merged：同名存在于≥2张表且未全部挂靠同一标准字段→warn；豁免主键字段（跨表匹配结构性必需）与 release_to_concept=False 字段（已排除）；message 列前 5 组同名字段及所属表
- `backend/apps/modeling/tests.py`：新增 DomainConfigDupFieldTest（5 用例）
**验证**：新增 5 用例全 PASS；modeling+archive 定向回归 51/51 PASS；真实数据实测域#11（BUG 涉事域）命中 4 组同名未归并字段 warn（含 D_CHECK_DATE/N_AREA/STORE_VERSION），域#12/#13 pass。前端 DomainList 配置检查弹窗为通用动态渲染，无需改动
**遗留**：域#11 现存 4 组同名未归并字段（REMARK/N_AREA/STORE_VERSION/D_CHECK_DATE），待用户决策归并或排除
### 第一百一十一轮（2026-08-05）标签：/modeling/domains、/archive、操作列、换行、命名精简
- 测试报告 2 项修复（跨 modeling/archive/uxqa）：①/modeling/domains 操作列链接换行：根因量化=列宽 280−padding 32=248px < 实需≈281px（4 链接 182+divider 51+size8 间隙 48），DomainList.vue a-space 补 `:size="4" + nowrap` + 列宽 280→320；同类防御：DataSourceList/DomainFieldMapping 操作列同补 nowrap。②/archive 按钮名精简（用户指定）：ArchiveList「一致性检查→检查、从数据源同步→同步」。uxqa 漏检复盘（仅复盘不补规则）：R-004 闭环声称 nowrap 已落实但从未落码 + 第109轮 B2 抽检漏 DomainList 且目测未实算 + 命名精简无检查项。验证：vue-tsc 0 errors；浏览器实测 domains 操作列 nowrap 生效 spaceWidth=257<320 无折行、archive 链接 编辑/检查/同步/删除 spaceWidth=187 无折行；截图 fix_verify_domains_action_nowrap.png / fix_verify_archive_action_short_names.png。debug-diary-modeling BUG-2026-0805-01 已登记，rectification-list 附复盘注记。**改向补记**：用户随后改向「那你加上吧」，两条补强写入 uxqa 方法论：frontend-delivery-checklist B2 硬约束（全站含操作列表格禁抽样+量化实算禁目测+闭环复检必 grep 代码证据）+ A9 操作列文案专项（≤2 字动词/对象来源不进按钮名/全站枚举逐列核对）；popup-layout-spec 命名节同步增条目。另核实修正：A9/B2/B8 检查项本就存在，真实缺口是措辞容许抽样/目测 + A9 未覆盖操作列文案，非缺项。
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

### 第一百三十三轮（2026-08-08）标签：方向锁定、子表关系、明细致子表、默认价、adqa质疑关

- 读取文件：probe 脚本执行结果（probe_price_plan/probe_ladder/probe_entry/probe_mapping_v2）、FieldMapping/StandardField/Field 模型定义、constitution.md、session.md 索引区
- 修改文件：.ai/constitution.md（追加「档案明细致子表与子表关系」架构级决策）、.ai/session.md（追加索引行）；output/probe_mapping_v2.py（创建后待删）；三个旧探针待删
- 变更摘要：task-132 延续，方向锁定闭环。①用户提出「子表关系」概念：FieldMapping 加关系类型（reference/detail），先构建子表再嵌套，替代独立 DetailGroup 配置（合并取消）；②默认价取数规则锁定：EFFECTIVE_DATE DESC + 自动补行键 DESC（同日期取行键最大，可复现）；③adqa 质疑关收口 5 条：代表行次级键（同日 3808 行无区分度）/主表 35 字段去留（全保留取代表行）/编辑联动（独立不联动）/明细量级（折叠+分页）/25-26 分组链（不标 detail 可反悔）；④实证：PRICE_PLAN 全空、FID 标主键但仅 14,883 唯一、ENTRY_ID 239,504 零重复零空、表 28 全 35 字段 release_to_archive=True、EFFECTIVE_DATE 已配 field_type=date（date_format 空待补）、28→22 单通道、27/28 无字段重名
- 方向判定表（rule §11）：命中「存储模型」（明细致子表保留行）→ 走完整 §11.1 流程（方向清单循环 4 轮 + adqa 质疑关硬回执 质[?5条] 伪[?8探针] 锁[?确认12/留活口1/否决0]），锁定结论已记 constitution
- 验证：方向锁定为文档任务无代码变更（N-A）；8 个探针全部实测执行
- 状态变更：方向锁定清单 v5 全部决策点闭环；detail 声明=FieldMapping.relation_type（待 darc 实施）；ArchiveRecordDetail 模型待建
- 遗留问题：①f4 重跑全量同步验证 GROUP_* 4 字段 + 计算字段重算（仍 PENDING）；②实施阶段：FieldMapping 扩展（relation_type/row_key/display_sort/conditions）+ ArchiveRecordDetail + 审计扩展 + API 嵌套分页；③date_format 空值需在代表行排序时按 ISO 兜底；④output/probe_*.py 四个探针待删


### 第一百三十七轮（2026-08-11）标签：方向锁定、子表交互改造、先注册后挂载、探针验证、adqa质疑关

- **读取文件**：constitution.md、session.md、DomainFieldMapping.vue（1309 行全读）、archive/views.py（主循环 1282-1286 / _query_external_table 1616+ / _sync_detail_rows 1755-1900+）、tests.py（633-649 方向实证）、models.py（FieldMapping 扩展 / Archive.domain OneToOne）
- **修改文件**：backend/diag_probe_2728.py（SQL 加 [dbo]. schema 前缀修复，验证后删除）、.ai/constitution.md（追加架构级决策块）、.ai/session.md（当前状态+索引行+最近3轮详情）
- **变更摘要**：用户反馈「关系管理有建立明细子表功能，但明细子表怎么和主表建关系？没有操作空间」→ 根因=FieldMapping 方向反直觉（source=明细子表→target=主表，与用户直觉相反）+新建映射弹窗无独立注册空间（必须先选主表才能配 detail）；方向锁定（§11.1）：①「先注册后挂载」交互范式（子表独立注册：域/表/行键/排序/条件，允许不选主表保存→主表挂载时下拉直接选）；②子表注册独立落库（DetailTableConfig 类新模型，FieldMapping 挂载 FK），一子表多挂载；③挂载必须选关联字段（明细物理列→主表主键通道）；④同步引擎 detail 查找 .first() → 多挂载循环；⑤旧入口移除+存量迁移通用化（自动检测方向异常 detail 映射并提示）；⑥独立主数据（价格列表/产品分组）确认不做（一域一档案不动），留升级活口；⑦darc 对齐 Archive 模型；探针实证：28.FID→27.ID 命中率 100%（239,504/239,504）→ 28 是 27 明细、存量 id=25（source=27→target=28）方向反了且从未产出数据（27 无映射到档案主键 MATERIAL_ID 的列），用户裁决并入交互改造统一修正；adqa 硬回执 质[✓5条] 伪[✓探针] 锁[✓确认5/留活口1/否决0]
- **状态**：方向锁定完成（constitution 已落盘），待路由 darc 实施设计编码
- **遗留**：id=25 方向修正并入交互改造；探针脚本已删除；模型选型（独立 DetailTableConfig vs FieldMapping 扩展）留 darc 设计时定；交互改造实施范围含前端两区块改造+存量迁移提示

### 第一百三十八轮（2026-08-11）标签：数据源新增、网络错误、服务重启

- **读取文件**：.ai/session.md、vite.config.ts、package.json、DomainList.vue（前轮）
- **修改文件**：无（纯运维诊断）
- **变更摘要**：用户报「新增数据源提示网络错误」+ 前轮「创建域操作失败」——根因均为后端 runserver 进程随终端关闭被终止（8000 端口无监听），前端 axios 请求全部落空 → 网络错误；另发现 init_admin 未跑（重建库后 admin 不存在，创建域 401/400）。处置：init_admin 重建 admin/admin123456；重启 runserver 8000（--noreload）+ vite dev 3000；全链路实测：登录 200 + 新增数据源 201 + 清理测试源 ✓
- **状态**：已解决，前后端服务运行中
- **遗留**：服务随终端关闭而终止的问题反复出现（历史多轮踩坑）——建议后续评估用 daemon 化/启动脚本托管，避免每次手工重启

### 第一百四十轮（2026-08-11）标签：数据源测试连接、SQL Server 18456、密码错误、编码修复

- **读取文件**：local_settings.py、views.py（_do_test_connection 96-148）、distinct_cache.py（ENGINE_MAP/OPTIONS 68-72）、DataSourceList.vue（217-238 测试连接）、mssql-django base.py（venv 源码 _build_connection_string 含 Windows MARS_Connection=yes 注入）、session-details/modeling.md（第一百三十八轮重建库事实）
- **修改文件**：.ai/session-details/modeling.md（编码修复）、.ai/telemetry/rule-hits.md（编码修复）；临时脚本 _diag_ds.py/_diag_encoding.py/_fix_encoding.py 已删
- **变更摘要**：①用户报 SQL Server 测试连接失败（28000/18456 用户 'MB_READ' 登录失败 + 无效的连接字符串属性）。根因排查三步排除：实验验证 MARS_Connection=yes（mssql-django 1.7.3 Windows 强制注入）+Encrypt=no 均为 ODBC Driver 18 有效属性（实验报 timeout 258 而非属性错）→ 连接字符串无技术问题；权威来源（StackOverflow/Azure/厂商 KB）证实「18456+Invalid connection string attribute」为已知组合噪音，主因是 SQL Server 端认证拒绝；第一百三十二轮同代码同步成功 209,123 条证明连接路径本身通。叠加第一百三十八轮重建库背景（数据源配置全丢、用户重新录入）。用户确认「我搞错密码了」→ 密码错误致 18456，与诊断一致，无需改代码。②顺带发现并修复留痕文件混合编码损坏：modeling.md（第一百三十三轮详情段 GBK 混入 UTF-8）与 rule-hits.md（尾部 GBK）均为之前写入时误用 GBK 编码（Windows 工具链默认编码），已无损统一为 UTF-8（GBK 段按段落解码合并），备份 .bak-enc 已删
- **状态**：已解决（用户改密码即可，无代码变更；编码修复完成）
- **遗留**：①测试连接报错原文对非技术用户不友好（原始 pyodbc 多段错误），可考虑后续把 18456/08001/258 等常见错误码翻译为友好提示（待用户需要时路由 darc 实施）；②数据源密码重置后需在页面重新保存验证

### 第一百四十一轮（2026-08-11）标签：方向锁定、子表交互改造第二轮、建关系直选子表、形态1

- **读取文件**：constitution.md（第一百三十七轮决策段）、DomainFieldMapping.vue（新建/编辑映射弹窗 162-233、onDetailConfigChange 1257-1267、handleSubmit 1009-1154、targetTableOptions 525-528、loadDetailConfigs 1181-1186）、session-details/modeling.md
- **修改文件**：.ai/constitution.md（追加「明细致子表交互改造第二轮『建关系直选子表』」架构级决策块）、.ai/session.md（当前状态+索引行）
- **变更摘要**：用户反馈「关系管理的明细子表没啥用啊。。你不是应该建好明细子表之后就可以用明细子表来和主表关系的么？」→ 第一百三十七轮「先注册后挂载」已实现（子表独立注册+映射下拉选配置），但新建映射弹窗把「关联子表配置」藏在表单尾部、源表/目标表下拉只含普通表，用户注册完子表后找不到建关系入口（库内现状：1 条子表注册 EDS_K3_物料分类、0 条映射）。方向锁定（§11.1）：①注册与建关系两步流程保持分开（用户明确「建子表是建子表的流程，选关系就可以选所有表和创建的子表。工作步骤是分开的」，否决合并方案）；②子表=有嵌套关系的表专用（分组/价格等，用户纠正「子表的意思是那些有嵌套关系的才需要建立的」）；③形态1：新建映射弹窗关系类型置顶，选「明细子表」后：主表下拉（普通表）→ 子表下拉（已注册子表+「管理注册」快捷入口）→ 关联字段（自动推荐可改）→ 保存自动建「子表→主表」映射并挂 detail_config（用户不管方向）；④一子表多主表保持（137 轮 .all() 循环已实现）；⑤存量未注册 detail 映射编辑=弹窗提示+可直接补选已注册配置（暂定默认可反悔），id=25 方向异常按 137 轮决策一并修正。adqa 质疑关 4 条收口：未注册引导（用户裁决「建关系时可以选普通表和子表」→两列表分置）/关联字段推荐（可改）/多主表（保持支持）/存量编辑（暂定默认）。发现并待修 bug：onDetailConfigChange 选中配置会把 source_table 覆盖为子表注册的表（用户已选主表被意外替换）；探针复用 137 轮（28.FID↔27.ID 命中率 100%）；adqa 硬回执 质[✓4条] 伪[✓复用137轮探针+实施后多挂载实测] 锁[✓确认5/暂定1(存量编辑)/否决0]
- **状态**：方向锁定完成（constitution 已落盘），待路由 darc 实施编码
- **遗留**：①实施范围=前端 DomainFieldMapping.vue 新建映射弹窗形态1重构+onDetailConfigChange bug 修复+编辑弹窗存量提示（后端大概率无改动，待 darc 影响分析确认）；②实施后实测：注册一子表挂两主表跑同步验证多挂载稳定性；③id=25 存量方向异常修正一并实施

### 第一百四十一轮（2026-08-11）标签：方向修正、预组合=头表+明细表、第三轮
- **读取文件**：constitution.md（第137/141轮决策段）、models.py（DetailTableConfig 569-598）、serializers.py（DetailTableConfigSerializer 230-247、FieldMappingSerializer.validate 275-298）、archive/views.py（主循环 detail 分支 1278-1330、_sync_detail_rows 1782-1900）、design-diary-modeling.md（137轮契约 677-752）、DomainFieldMapping.vue（dcModal 130-222、detail 表单 162-222）、库内表/注册/映射现状
- **修改文件**：.ai/constitution.md（追加「明细致子表交互改造第三轮『预组合=头表+明细表』」决策块）、.ai/session.md（当前状态+第141轮索引行改写）
- **变更摘要**：用户纠正第二轮语义理解错误：「子表=预组合=头表+明细表先组合（价格头+价格明细、分组头+分组明细），再用预组合体关联主表」。库内实证：价格组合=销售价目表 S_K3_T_SAL_PRICELIST_L(PK=ID)+价目表明细 S_K3_T_SAL_PRICELISTENTRY(FID 关联头.ID)；分组组合=物料分组 S_K3_T_BD_MATERIALGROUP(PK=FID)+分组明细 _L(FID 关联头.FID)。方向锁定 7 条：①注册=选头表+选明细表+配头↔明细关联字段（同名校验自动检测可手动）+行键/排序/条件，域+头表+明细表唯一；②挂载=主表↔预组合体（关联字段自动推荐可改，字段池=头字段+明细字段平铺）；③组合形态=平铺宽表（用户否决嵌套，一行=一条明细+头字段重复）；④存量单表注册（物料分组行键 GROUP_ID）删掉重建；⑤挂载关联自动推荐可改；⑥前端上轮改动复用（关系类型置顶/主表下拉/推荐），子表下拉→预组合下拉、注册弹窗→双表形态；⑦不做：不合并弹窗、不动引用、不删旧字段。adqa 质疑关 4 条裁决：字段重名（FID）→头字段加前缀/字段池标注来源；内存 JOIN 性能→对照 _query_external_table 全量拉取现状风险持平；分组组合宽表无物料关联字段（GROUP_ID string vs MATERIAL_GROUP number）→推荐失败可手动选；平铺行归属→pk_physical_to_schema 明细表物理列映射不变则归属不变。硬回执 质[✓4条] 伪[✓字段交集实测] 锁[✓确认7/暂定0/否决0]
- **状态**：方向修正锁定（constitution 已追加），待路由 darc 实施编码
- **遗留**：①实施范围=后端 DetailTableConfig 扩展（头表/明细表/关联字段 FK）+迁移+serializer/校验+同步引擎平铺 JOIN+前端两弹窗改造（挂载弹窗预组合下拉+注册弹窗双表形态）；②存量单表注册删除；③实施后实测：注册价格组合+分组组合→挂载物料主表→跑同步验证平铺行输出

### 第一百四十一轮实施（2026-08-11）标签：预组合实施、三缺陷修复、浏览器实测、平铺行实测
- **任务**：第三轮方向锁定后的 darc 实施：预组合（头表+明细表先组合再关联主表）全栈落地。
- **修改文件**：
  - `backend/apps/modeling/models.py`+迁移0032：DetailTableConfig 扩展 header_table FK→Table / header_link_field / detail_link_field（FK→Field），unique_together=(domain, table)
  - `backend/apps/modeling/serializers.py`：DetailTableConfigSerializer 三字段+头表名/关联字段 code；FieldMappingSerializer.validate（detail 必填 detail_config、target_field 必须目标表主键、cfg.table==source_table；不校验 source_field 归属——放行头表字段作关联键）
  - `backend/apps/modeling/views.py`：detect-header-link action（同名校验→FID 后缀匹配→头表 PK 兜底）
  - `backend/apps/archive/views.py`：_join_header_rows（头表全量拉取→hindex 内存 JOIN→`__hdr__{物理列名}` 前缀并入，失败/未命中降级纯明细行不阻断）；physical_to_schema/pk_physical_to_schema 纳入 header_table_id；_record_key_for_row __hdr__ 回退；detail_data 构建 is_hdr 剥前缀
  - `frontend/src/api/modeling.ts`+`types/index.ts`：detailConfigApi.detectHeaderLink+类型扩展
  - `frontend/src/views/modeling/DomainFieldMapping.vue`：挂载弹窗预组合形态（关系类型置顶/主表→预组合下拉「头表名+明细表名」/字段池=头字段+明细字段平铺/配置摘要/管理注册按钮）；注册弹窗双表形态（头表+明细表+关联字段三件套+检测按钮+行键/排序/条件）
  - `backend/scripts/test_precombine.py`（新建）：平铺行实测脚本
- **修复的缺陷（浏览器实测发现）**：①loadSourceFields 只加载明细表字段→并入头表字段（复测 12 字段）；②pk_physical_to_schema 只收 tbl_id==table.id→纳入 header_table_id；③_record_key_for_row 不认 __hdr__ 前缀→回退查找；④placeholder :绑定显示 [object Object]→去 :
- **验证**：django check 0 issues + vue-tsc 0 errors；浏览器实测：注册弹窗双表形态✓/挂载预组合下拉✓/关联字段推荐 MATERIAL_ID✓/手动改选 GROUP_ID✓/保存 201×2+列表 2 行✓/删除 Modal.confirm+DELETE×2✓/持久化刷新保留✓（3/6 表已配置）；平铺行实测：价格组合 239,504 行 35 明细键+6 头字段命中 3/3、分组组合 __hdr__GROUP_ID 存在归属取前缀值、pk 纳入判断 True
- **测试工具限制（非产品 bug）**：browser-use dispatchEvent 模拟事件缺 focus 链→antd Select 报 Cannot read properties of null (reading 'focus')；残留 Modal 动画 transitionend 不触发致 DOM 残留；「编辑/删除」是 a 标签非 button
- **状态**：实施完成，收尾留痕完成；constitution 追加实施补充决策块
- **编码修复（收尾发现）**：第一百四十一轮方向锁定详情条目（本文件尾部）再次以 GBK 编码写入致混合编码损坏（第一百四十轮修复后同类问题连续两轮复现）——已 GBK 无损转码 UTF-8 恢复原文，constitution 追加「留痕文件写入编码纪律」硬约束防第三次
- **遗留**：P2 建议——字段池 FID 重名（头表 PK FID + 明细表 FID）下拉显示歧义（功能无碍，显示可加「头表」标记）；子表注册弹窗选择+自动检测+保存交互未能在浏览器完全走通（模拟事件受限，弹窗形态已验+注册接口后端 201）

### 第一百四十三轮（2026-08-11）标签：FieldMapping 唯一性报错、关系重复创建、预检拦截
- **Bug**：新建字段映射（物料主表→物料信息表普通关联）报「字段 source_table, source_field, target_table, target_field 必须能构成唯一集合」——四元组与存量 id=5 重复（AskUserQuestion 确认场景=普通字段关联）；上轮已登记同类待办
- **根因**：FieldMapping unique_together 四元组 + FieldMappingSerializer 无自定义校验器（DRF 默认模板）；前端无预检；存量 3 条映射 id=3/4/5
- **方案**：用户确认方案A（后端友好报错+前端保存前预检）+本次只修字段映射（其余 7 处同类下批）
- **修改文件**：backend/apps/modeling/serializers.py（FieldMappingUniqueValidator+Meta.validators）；frontend/src/views/modeling/DomainFieldMapping.vue（checkMappingDuplicates+handleSubmit 调用）
- **验证**：后端 APIClient 6 项全过（重复 id=5→400 友好、重复 id=3 detail 挂载→400 友好、全新 201+204、编辑自身 200、编辑撞他人 400 友好）；vue-tsc 0 + django check 0；浏览器实测预检拦截（message.warning「该关系已存在：…ID=5」、弹窗保持打开未提交）
- **状态**：实施+验证完成，收尾留痕完成
- **遗留**：7 处同类 unique 约束默认模板待分批（用户选择下批）；存量 id=4 detail 映射 detail_config 为空（旧范式遗留，编辑会触发必填校验，待用户遇到再处理）
### 第一百五十二轮（2026-08-13）标签：测试报告4问题、明细检查按钮、ER图全屏、JOIN类型、左右分栏
- **背景**：测试报告4个问题，分批处理。批1=Issues 1-2；批2=Issue 3（JOIN类型配置）；批3=Issue 4（弹窗左右分栏）
- **Issue 1 明细检查按钮**：按钮点开抽屉后 API 返回全空数据，用户认为"没有作用"。修复→onMounted 自动预加载 loadDetailCheck()；新增 `hasDetailCheckIssues` computed（registered/unregistered/suspect 任一有数据才 true）；`v-if="hasDetailCheckIssues"` 控制 badge+按钮渲染，无异常时隐藏
- **Issue 2 ER图全屏**：原逻辑仅 v-show 隐藏映射列表+CSS 高度拉伸（calc(100vh-220px)），用户要真正的浏览器全屏。修复→`toggleErFullScreen` 改为 `erContainer.requestFullscreen()` + `document.exitFullscreen()`；`fullscreenchange` 事件同步 `erFullScreen.value` 状态；Fullscreen API 不可用时回退原逻辑
- **Issue 3 JOIN 类型配置**：FieldMapping 新增 `join_type`（JoinType.LEFT/INNER，迁移0033）+ 序列化器暴露 + 同步引擎四场景适配（_join_header_rows join_type='inner' 跳过无匹配头表行 / _upsert_dimension_via_mapping inner 跳过无匹配目标行 / _sync_detail_rows nested_sources inner 跳过明细行）+ 前端 JOIN 选择器（关系类型右侧并列）+ 列表 join_type 列（灰色LEFT JOIN/蓝色INNER JOIN）+ TypeScript 类型扩展
- **Issue 4 弹窗左右分栏**：弹窗宽度 640px→960px；引用表单改为 a-row 左右分栏——左侧源表 select+字段可点选列表（联合主键特殊行+field-panel CSS），中间箭头，右侧目标表 select+字段可点选列表
- **变更文件**：`backend/apps/modeling/models.py`（FieldMapping JoinType+join_type）、`backend/apps/modeling/migrations/0033_fieldmapping_join_type.py`（新）、`backend/apps/modeling/serializers.py`、`backend/apps/archive/views.py`（四场景适配）、`frontend/src/types/index.ts`（FieldMapping 接口扩展）、`frontend/src/views/modeling/DomainFieldMapping.vue`（模板+脚本+样式）
- **验证**：vue-tsc 0 errors + django check 0 issues + 102 tests 0.716s PASS
- **状态**：全部4个问题实施+验证+留痕完成