# 会话接力 — 主文件（当前状态 + 功能索引）
> 启动只读本文件（rule §3）。历史详情按模块存于 `.ai/session-details/<模块>.md`（archive / modeling / uxqa / project / early-logs），确认需求后按「模块+功能标签/第N轮」grep 加载，禁止全量读。
## 当前会话状态
- **当前阶段**：第一百五十七轮（已完成）——方向修正：挂载字段放宽为任意键 + 同步按挂载字段一对多归属，105/105 测试 PASS
- **活跃模块**：modeling、archive、frontend
### 最近 3 轮详情（满 3 轮后最旧一轮下沉到详情文件）
- **本次操作**：2026-08-13 — 第一百五十七轮：用户方向性纠正「为什么和预组合表的关联字段只能是主键？应该是任何键」+ 拍板方案B（同步按挂载字段归属）+ GROUP_ID 一对多场景——后端 _sync_detail_rows 归属机制改造（挂载字段 target_field 构建归属键+existing_records 多值索引+明细行循环全部同值主记录+代表行按挂载值分组共享）+ serializers 移除主键校验 + detail-check 简化 + 前端主表字段全可选（6 处）；新测试 DetailSyncOneToManyTest 3 条；105/105 PASS；constitution 已追加方向修正决策
- **上次操作**：2026-08-13 — 第一百五十六轮：测试报告1问题（新建映射弹窗预组合关系表单无匹配字段点选、非左源右目标设计）——detail 分支 a-select 下拉（主表/预组合/关联字段）改为左右分栏：左侧预组合列表（点选+管理注册入口+行键小字）+关联字段列表（点选+推荐tag）、中间箭头、右侧主表列表（点选）+主表字段列表（点选仅主键可选，非主键disabled）；新增 selectDetailSourceField/selectDetailTargetField；配置摘要/主键警告保留；form 结构不变。验证：vue-tsc --noEmit 0 errors；已commit+push（ab4c32c）
- **更早操作**：2026-08-13 — 第一百五十二轮：测试报告4问题，分批处理。批2+3（Issues 3-4）：③后端 FieldMapping 模型加 join_type（JoinType.LEFT/INNER，迁移0033）+ 序列化器暴露 + 同步引擎四场景适配（_join_header_rows 参数 join_type、_upsert_dimension_via_mapping `inner` 跳过无匹配、_sync_detail_rows nested_sources `inner` 跳过明细行）+ 前端 JOIN 类型选择器（关系类型右侧并列）+ 前端列表 join_type 列 + TypeScript 类型扩展 + ④弹窗宽度 640→960px + 引用表单左右分栏（源表+字段可点选列表 | 箭头 | 目标表+字段可点选列表）+ field-panel/field-item 样式。验证：vue-tsc 0 errors + django check 0 + 102 tests 0.716s PASS
## 功能索引（倒序，每轮一行；完整性/确认点自本次迁移后开始记录）
| 轮次 | 日期 | 模块 | 功能标签 | 一句话摘要 | 完整性 | 确认点 |
|------|------|------|----------|------------|--------|--------|
| 第一百五十七轮 | 2026-08-13 | modeling、archive、frontend | /modeling/domains/2/mappings、挂载字段、一对多、GROUP_ID、同步归属、方向修正 | 方向修正（用户拍板B）：挂载字段放宽为任意键（不限定主键）+ 同步按挂载字段值归属一对多（_sync_detail_rows 归属键改造+existing_records 多值索引+明细行循环全部同值主记录+代表行按挂载值分组共享）；serializers 移除主键校验+detail-check 简化+前端主表字段全可选；新测试 DetailSyncOneToManyTest 3 条；全套 105/105 PASS；constitution 已追加决策 | 闸✓记✓拓✓测✓ | 2问/0改向 |
| 第一百五十六轮 | 2026-08-13 | modeling、frontend | /modeling/domains/2/mappings、测试报告、预组合关系表单、左右分栏、左源右目标 | 测试报告1问题：新建映射弹窗预组合关系（detail）表单由 a-select 下拉改为左右分栏——预组合列表+关联字段点选 | 箭头 | 主表列表+主表字段（仅主键可选），配置摘要保留；vue-tsc 0 errors；已commit+push（ab4c32c） | 闸✓记✓拓✓测✓ | 0问/0改向 |
| 第一百五十三轮 | 2026-08-13 | project、deploy | release.ps1、sync.sh、一键发布、服务器同步、/opt/metadata | 新增本地一键发布脚本 scripts/release.ps1（build 前端→git add/commit/push，失败中止不提交）+ 服务器同步脚本 deploy/sync.sh（git pull→npm run build→重建 backend 自动 migrate→nginx reload）；服务器 /opt/metadata/deploy 有 Node/npm；双脚本语法验证通过（PS Parser + bash -n） | 闸✓记✓拓✓测✓（无新增路径） | 1问/0改向 |
| 第一百五十二轮 | 2026-08-13 | modeling、frontend、archive | /modeling/domains/2/mappings、测试报告、JOIN类型、左右分栏、FieldMapping join_type、同步引擎 | 测试报告4问题分批处理，批1（Issues 1-2）：明细检查按钮/ER图全屏；批2+3（Issues 3-4）：FieldMapping join_type+同步引擎适配+前端JOIN选择器+列表列+弹窗左右分栏960px；vue-tsc 0+django check 0+102 tests PASS | 闸✓记✓拓✓测✓ | 0问/0改向 |
| 第一百五十一轮 | 2026-08-13 | modeling、frontend、archive | /modeling/domains/2/mappings、ER图预组合、表配置进度、排序字段、条件构建器 | UXQA测试报告问题1-5修复：①ER图预组合绿虚线②pk_status 后端预组合感知③ER图「预组合表」高亮④移除排序字段⑤JSON条件→结构化条件构建器（字段/操作符/值行列表，后端加contains/starts_with）；102 tests PASS；问题6保持现状 | 闸✓记✓拓✓测✓ | 2问/0改向 |
| 第一百五十轮 | 2026-08-12~13 | archive | 全量同步实测、row_key修复、代表行分组修复 | 用户要求「先走通有数据的」实测 + row_key MATERIAL_ID→ENTRY_ID 修复（明细 238K→476K 全保留） + 版本快照考古发现代表行只写全局首行 Bug → 修复为按物料分组写（对齐第133轮锁定）；遗留：物料分组明细0条、NAME0值 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百四十九轮 | 2026-08-12 | archive、frontend | /archive 同步预检、前端axios超时 | Bug续诊：后端预组合跳过已修复（36s），但前端axios timeout:30000 < 36s 导致用户等不到响应；修复：refreshPreview单独设180s超时 + 超时提示文案 | 闸✓记✓拓✓测⚠️（无新增路径） | 0问/0改向 |
| 第一百四十八轮 | 2026-08-12 | archive、frontend | /archive 同步预检、预组合表跳过、loading状态 | Bug：产品档案同步"完全没反应" — _preview_data_changes 未跳过预组合明细子表（239K+14K 行被全量查询），且 ArchiveList 同步按钮无 loading 反馈；修复后 tables_checked=3（原6）、37s 稳定；ArchiveList syncingId 补「同步中...」状态 | 闸✓记✓拓✓测✓ | 0问/0改向 |
| 第一百四十六轮 | 2026-08-11~12 | project、deploy | Docker Compose 内网部署、Nginx、Gunicorn、数据迁移 | 局域网开放失败（对方 ping 不通=VLAN 隔离），用户决定部署到内网 Linux 服务器。前置确认：Linux 服务器 + 内网 IP 访问 + 迁移现有数据。实施：frontend/nginx.conf（前端静态+API 反向代理+SPA fallback）+ deploy/docker-compose.yml（nginx+backend gemicorn+postgres15+redis7，启动链 migrate→loaddata→init_admin→collectstatic→gunicorn）+ deploy/.env（DEBUG=0 模板）+ backend/Dockerfile 补 CMD gunicorn + 导出 data_dump.json（138 条全业务数据）+ .gitignore 加 data_dump.json。验证：138 条记录覆盖全模型 | 闸✓记✓拓✓测✓ | 2问/0改向 |
| 第一百四十五轮 | 2026-08-11 | project、auth、frontend | 局域网开放、0.0.0.0监听、测试账号、防火墙放行 | 局域网开放测试：现状=前后端只监听 localhost+ALLOWED_HOSTS 默认 *；vite.config.ts server.host:true + 手工后台起 runserver 0.0.0.0:8000 --noreload（不动 dev.ps1，测试完 stop+start 恢复）+建 tester（qQLdeaCIu1）/manager（i5IdOs5taN）两管理员账号（UserProfile 无自动创建需手工补挂角色）+防火墙 netsh 需管理员权限未加成（命令已给用户）；实测：netstat 0.0.0.0 监听 ✓+两网卡 IP curl 200/401；遗留：防火墙待用户提权放行、测试完恢复本机监听 | 闸✓记✓拓✓测✓ | 2问/0改向 |
| 第一百四十三轮 | 2026-08-11 | modeling | FieldMapping 唯一性报错、关系重复创建、预检拦截、FieldMappingUniqueValidator | Bug 六步修复：用户建「物料主表和明细表的关系」（普通关联 物料.MATERIAL_ID→物料信息.MATERIAL_ID）报「字段 source_table... 必须能构成唯一集合」；根因=四元组 unique_together 与存量 id=5 重复+DRF 默认模板+前端无预检；方案A 实施——后端 FieldMappingUniqueValidator（友好错误指明占用关系+ID+类型，编辑排除自身）+前端 checkMappingDuplicates 预检（composite 展开逐对、命中 message.warning 拦截不发请求）；后端实测 6 项全过+vue-tsc 0+django check 0+浏览器实测预检拦截；遗留 7 处同类默认模板待分批 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百四十二轮 | 2026-08-11 | modeling | 子表注册唯一性报错、预组合、列表管理入口、DetailTableUniqueValidator | Bug 六步修复：用户新建子表注册选已占用明细表报「字段 domain, table 必须能构成唯一集合」；根因=unique_together=(domain,table)+前端无已注册提示+注册管理无列表/编辑入口；方案A 实施——后端 DetailTableUniqueValidator（友好错误指明占用组合+ID，编辑排除自身）+前端明细表下拉禁选标记（dcRegisteredMap）+「管理注册」/「子表注册」统一开列表管理弹窗（编辑回填/删除 popconfirm 挂载提示）；后端实测 5 项全过+vue-tsc 0+django check 0+浏览器实测 4 项；遗留同类点 FieldMapping 唯一性待确认 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百四十一轮 | 2026-08-11 | modeling、archive | 预组合、头表+明细表、平铺宽表、detect-header-link、_join_header_rows、多挂载 | 明细致子表交互改造第三轮实施：预组合全栈落地（DetailTableConfig 三字段扩展+迁移0032+detect-header-link+_join_header_rows 平铺 __hdr__ 前缀+归属链路三处配套+挂载/注册弹窗双表形态）；浏览器实测发现并修复 3 缺陷+1 UI（字段池缺头表字段/pk_physical_to_schema 只收明细表/_record_key_for_row 不认 __hdr__/placeholder [object Object]）；实测 201×2+删除×2+持久化+平铺行实测（价格组合 239,504 行命中 3/3、分组 __hdr__GROUP_ID）；django check 0+vue-tsc 0；遗留 P2 FID 重名显示 | 闸✓记✓拓✓测✓ | 3问/0改向 |
| 第一百四十轮 | 2026-08-11 | modeling | 数据源测试连接、SQL Server 18456、密码错误、编码修复 | SQL Server 测试连接失败诊断：根因=MB_READ 密码错误（18456 认证被拒），「无效的连接字符串属性」经实验+权威来源证实为伴随噪音非根因；顺带修复 modeling.md/rule-hits.md 混合编码损坏（GBK 段无损转 UTF-8） | N-A | 1问/0改向 |
| （续上轮） | 2026-08-08 | archive | 分析脚本合并 | 3个杂乱的DB检查脚本（check_db_contents/check_db_storage/check_db_field_sizes）合并为单个 check_db_diagnostics.py，统一统计口径（均值/中位数/P90/P95/P99/最大），修复代码bug（自除/拼写/换算），新增版本分布直方图+dbstat精确页分析+综合诊断与推荐方案 | 闸✓记✓拓✓测✓ | 0问/0改向 |
| 第一百三十九轮 | 2026-08-11 | project | scripts/dev.ps1、一键启动、后台运行、幂等 | 新增 scripts/dev.ps1（start/stop/status）：后台拉起前后端不随终端退出+日志 output/logs/+PID 落盘+端口占用幂等跳过+stop 兑底杀子进程；踩坑修复 $pid 只读变量/$Port: PSDrive 解析/npm父子进程链；实测生命周期全通过+登录 200 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百三十八轮 | 2026-08-11 | modeling、project | /modeling/data-sources、网络错误、服务重启 | 新增数据源提示网络错误诊断：根因=后端 runserver 随终端关闭终止（8000 无监听）+重建库后 admin 未初始化；处置=init_admin 重建账号+重启前后端+全链路实测（登录 200/新增数据源 201/清理） | N-A | 0问 |
| 第一百三十七轮 | 2026-08-11 | modeling、archive | 方向锁定、子表交互改造、先注册后挂载、探针验证、adqa质疑关、详情表注册、多挂载同步 | 明细致子表交互改造「先注册后挂载」完整实施：方向锁定（§11.1 全流程）+ 编码——DetailTableConfig 模型+迁移+ViewSet+同步引擎多挂载+前端改造（子表注册弹窗/映射下拉选/detail-check）+ API 层扩展；vue-tsc 0 errors + django 0 issues | 闸✓记✓拓✓测⚠️（无新增路径） | 4问/0改向 |
| 第一百三十六轮 | 2026-08-10 | modeling、archive | 明细致子表批3a+3b、前端、关系管理配置、明细展示、变更日志 | 明细致子表批3a+3b（前端）：批3a 关系管理配置页——FieldMapping 前端扩展（relation_type 列/编辑弹窗 detail 配置区/detectRowKey/handleSubmit PATCH 更新 detail 配置）+批3b 明细展示+变更日志——后端 ArchiveRecordDetailRowSerializer + GET /records/{id}/details/ + 前端 ArchiveDetail 明细抽屉 + ChangeHistoryDrawer detail_sync 展示；vue-tsc 0 errors + 后端验证通过 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百三十五轮 | 2026-08-10 | archive | 明细致子表批2、审计扩展、ChangeDetail扩展、DETAIL_SYNC、聚合变更日志、回滚 | 明细致子表批2（审计扩展）：ArchiveChangeDetail 扩展 detail_group/detail_row_key + ChangeType.DETAIL_SYNC（迁移0016）+ ChangeDetailSerializer 扩展 + _sync_detail_rows 追加聚合 change_entries（统计级不逐行）+ bulk_create 补充 detail_group/detail_row_key + rollback-detail action（POST /archives/{id}/rollback-detail/，复用 _sync_detail_rows 全量覆盖）；3 条新测试全 PASS + 回归 51/51 PASS；批1 明细不进 change_entries 限制解除 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百三十四轮 | 2026-08-10 | modeling、archive | 明细致子表、子表关系、detail分支、行键检测、conditions | 明细致子表批1（后端核心）实施：FieldMapping 扩展 relation_type/row_key_field/display_sort_field/display_sort_desc/conditions（迁移0030）+ ArchiveRecordDetail 明细行模型（迁移0015）+ 同步引擎 detail 分支（_sync_detail_rows：行键自动检测回填/嵌套属性一级透传/代表行写主表/明细upsert/明细停用清扫，批1明细变更不进change_entries）+ _build_conditions_sql 结构化条件（白名单+参数化）+ FieldMappingSerializer 扩展 + detect-row-key action；新增 8 定向测试全 PASS + 回归 99/99 PASS + check 0 issues | 闸✓记✓拓✓测✓ | 0问/0改向 |
| 第一百三十三轮 | 2026-08-08 | modeling、archive | 方向锁定、子表关系、明细致子表、默认价、adqa质疑关 | 档案明细致子表方向锁定完成（§11.1 全流程）：用户提出「子表关系」概念（FieldMapping 加 relation_type=detail，先建子表再嵌套）替代独立 DetailGroup 配置；默认价取数规则锁定（EFFECTIVE_DATE DESC+自动补行键 DESC）；adqa 质疑关收口 5 条全裁决（代表行次级键/主表35字段保留/编辑独立不联动/折叠+分页/25-26不标detail）；源库4探针+配置4探针实证（PRICE_PLAN全空/FID非行唯一/ENTRY_ID唯一/35字段全release/EFFECTIVE_DATE已配date类型）；锁定结论已记 constitution | N-A | 6问/1改向 |
| 第一百三十二轮 | 2026-08-08 | archive | /archive/同步、全量同步、去TOP1000、BUG-2026-0808-02、SQLite分批 | 同步引擎维度模型适配收尾：档案=JSON 物化宽表（非物理宽表非视图）；去 TOP 1000 全量同步（fetchmany 分批+无变化 bulk_update+明细瘦身）+BUG-2026-0808-02 SQLite 999 变量上限修复（差集+500/批）；实测 6/6 表 209,123 条 11 分钟 PRICE 24,794 精确命中交集+变更明细 11,677；40 测试全 PASS；遗留 GROUP_NAME 配置缺失+7 计算字段公式错误 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百三十一轮 | 2026-08-08 | archive | /archive/去重值、field-distinct-values | 档案字段去重值统计：后端新端点 field-distinct-values（实时聚合）+ ArchiveDetail 字段导航「值」按钮+弹窗；40 测试全 PASS + vue-tsc 0 errors | 闸✓记✓拓✓测✓ | 1问/1改向 |
| 第一百三十轮 | 2026-08-08 | modeling、archive | /archive/同步、physical_name、改名映射、BUG-2026-0808-01 | BUG修复：Field 新增 physical_name 字段保留原始列名（迁移0029）+ _build_code_to_physical 用 physical_name 同步 + pk_fields 改用 schema code；产品域档案同步从 0 恢复到 1000 条；91 测试全 PASS | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百二十九轮 | 2026-08-08 | modeling | /modeling/config-tables、数据源同步、MAP_ORDER多位置、自动调度 | 配置表数据源同步全栈：模型扩展（data_source/sync_sql/last_synced_at）+ execute-query 只读 SQL 预览 + sync action + _sync_config_table 复用函数 + 前端同步配置 UI + MAP_ORDER 多位置模式（"5,6,7" 依次取段查表）+ 管理命令 sync_config_tables + daemon 自动调度；Bug修复（TIME_ZONE 连接配置+PATCH 保存）；4 新测试 10/10 PASS | 闸✓记✓拓✓测✓ | 2问/0改向 |
| 第一百二十八轮 | 2026-08-07 | modeling | /modeling/config-tables、MAP_VALUE配置表驱动、MAP_ORDER级联查找、ConfigTable | 配置表驱动全栈：ConfigTable 模型（迁移0027）+ MAP_VALUE 配置表查表 + MAP_ORDER 级联查多表新函数 + ConfigTables.vue Key-Value 单页体验 + FormulaEditor 侧栏「配置表」Tab + Bug修复（4处__domain_id__注入+DomainStageNav+服务器重启）；9 新测试 44/44 PASS + vue-tsc 0 errors | 闸✓记✓拓✓测✓ | 6问/1改向 |
| 第一百二十七轮 | 2026-08-06 | modeling、uxqa | /modeling/tables、字段管理大抽屉、R-059、/modeling/domains、分组弹窗、R-061 | 第118轮整改单 5 批计划批4：R-059 字段管理近全屏 modal→65vw 大抽屉（双 Tab+主键标识区+预览表全保留，footer 固定关闭底栏，两入口不动）+R-061 window.prompt→480px Modal 表单（空名禁用确认、重命名预填未改动零请求）；踩坑：antdv 4.x 声明式 a-modal @ok 不消费返回值，v2 改请求 .then 内显式关闭+catch 不重抛；方向判定表四项不触及/执行已锁定决策；vue-tsc -b --force 0 errors+Browser 实测 R-059 6/6+R-061 v2 7/7 全 PASS+console 0 error；剩 R-060 一项待整改 | 闸✓记✓拓✓测✓ | 0问/0改向 |
| 第一百二十六轮 | 2026-08-06 | archive、uxqa | /archive/刷新预检、R-062、组件收敛 | 第118轮整改单 5 批计划批3：R-062 刷新预检两处同构弹窗收敛为 RefreshPreviewModal 单组件（760px modal，组件管展示+确认意图，执行逻辑留父组件；AL stats 文案顺带泛化补复活文案+同步/刷新区分，防 R-016/R-048 式再分叉）；方向判定表四项不触及/执行已锁定决策；vue-tsc -b --force 0 errors+Browser 实测 6 项 PASS（含注入建模变化触发 schema 弹窗验证）+console 0 error；剩余 R-059/R-060/R-061 三项待整改 | 闸✓记✓拓✓测✓ | 0问/0改向 |
| 第一百二十五轮 | 2026-08-06 | archive、uxqa | /archive/变更历史、R-057、组件收敛 | 第118轮整改单 5 批计划批2：R-057 变更历史两处同构弹窗收敛为 ChangeHistoryDrawer 单组件（900px 抽屉+时间线+双粒度回滚 dropdown，AD 带回滚/VM 只读；AD 附带清理 121 行死预载；加载口径统一 VM 全量分页）；方向判定表四项不触及/执行已锁定决策；vue-tsc -b --force 0 errors+Browser 实测 8 项全 PASS+console 0 error；剩余 R-059~R-062 四项待整改 | 闸✓记✓拓✓测✓ | 0问/0改向 |
| 第一百二十四轮 | 2026-08-06 | archive、uxqa | /archive/记录详情、R-056、弹窗转抽屉 | 第118轮整改单 5 批计划批1：R-056 记录详情 1400 modal→1100 大抽屉（footer 固定底栏，暂存修改/变更预览/分组网格全保留，沿用全站 a-drawer 骨架）；方向判定表四项不触及/执行已锁定决策；vue-tsc -b 0 errors+Browser 实测 6/6 PASS+console 0 error；剩余 R-057/R-059~R-062 五项待整改 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百二十三轮 | 2026-08-06 | archive、auth、uxqa | /archive/记录启停、/settings/roles、uxqa整改 | uxqa 第118轮整改单落地 2 项：R-055 记录启停无确认→Modal.confirm 二次确认（停用=danger，开关受控绑定取消自动回弹）+R-058 删角色 popconfirm→Modal.confirm（与全站删除防护对齐，文案依据后端 perform_destroy 事实）；方向判定表四项不触及/执行已锁定决策；vue-tsc -b 0 errors+Browser 实测 2/2 PASS+console 0 error；剩余 R-056~R-062 六项待整改 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百二十二轮 | 2026-08-06 | frontend、archive | /archive/versions、菜单高亮、变更日志 | Bug：变更日志明细页菜单误高亮档案管理；根因 MainLayout 高亮白名单手动维护漏登记 /archive/versions（同类排查全部子路由仅此一错）；用户选治本：白名单从 menuItems 递归自动推导+下钻页别名表；修复中引入 TDZ 白屏被浏览器实测当场拦截（watchEffect 移后）；vue-tsc 0 errors+5 页 DOM 实测全对 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百二十一轮 | 2026-08-06 | auth | admin 密码统一、冒烟测试账号、存量清理 | 用户反馈密码多处不一致+系统里有测试垃圾数据；admin 密码全项目统一 admin123456（init_admin 默认值+三 smoke 脚本+dev.db 重置）；新增 init_test_account 命令建冒烟专用 smoke_test（test23456 挂管理员角色），三脚本切换；存量清理 probe_user/实测角色（敏彤角色未动）；docker-compose 启动链补 init_admin+init_test_account；smoke_auth 19/19+smoke_src_owned 9/9+permission_overview 7 passed | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百二十轮 | 2026-08-05 | archive | /archive、权限全景、只读审计、API 聚合 | 新需求「一站式看档案的 API/暴露字段/调用系统/角色/用户/字段授权」；质问闸门 3 问锁定：入口=档案列表操作列（不新建菜单页）、仅管理员、只读+跳转配置；后端 permission_overview action（IsMdmAdmin 403，零新模型聚合 v19+REQ-019 数据，调用按密钥维度聚合）；前端 PermissionOverview.vue 960px 抽屉两区块+去配置跳转；新增用例 3 条 40/40 PASS+实测 7/7+浏览器验证全过 | 闸✓记✓拓✓测✓ | 3问/0改向 |
| 第一百一十九轮 | 2026-08-05 | auth | /settings/roles、测试反馈、可编辑限制、ownership | 测试报告 1 项：角色权限「可编辑」仅档案侧维护字段可配（ownership='archive'）——前端 source 字段复选框置灰+tooltip+提示行+加载剔除误存项；后端 PUT permissions 校验 editable_codes 含 source 字段返 400（与记录更新 ownership 拦截同口径）；新增用例 1 条 33/33 PASS+实测 smoke_src_owned 9/9+浏览器验证 24/25 置灰正确；过程中发现并清理 8000 端口双进程监听（旧进程致实测假 200） | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百一十八轮 | 2026-08-05 | archive | /archive/api-management、测试报告、测试接口、UI 精简 | 测试报告 9 项：①修复测试接口认证头（Authorization→X-API-Key）；②恢复新建接口功能；③操作范围只保留查询（新增/修改/删除禁用灰色）；④移除角色/部门授权字段（遗留配置）；⑤对外标识改系统自动生成；⑥修复文档可写列（只有 API 开放写操作时才显示）；⑦修复暴露字段 checkbox-group bug；⑧新增测试接口 Modal；⑨移除授权列；vue-tsc 0 errors+回归 104/104 PASS | 闸✓记✓拓✓测✓ | 2问/0改向 |
| 第一百一十七轮 | 2026-08-05 | archive | /archive/api-management、v19 编码落地、REQ-005、API Key 鉴权 | v19 API 管理全栈落地+uxqa 交付验收通过：迁移0014+鉴权单点+网关六端点+密钥管理+docs+前端双 Tab；新用例 19 条（37/37）+定向回归 54/54+真实请求实测 18/18 PASS；checklist 21/21 ✅，P2 R-054 已闭环，浏览器实跑 0 error | 闸✓记✓拓✓测✓ | 2问/0改向 |
| 第一百十六轮 | 2026-08-05 | auth | 系统管理、角色配置、字段可见可编辑、REQ-019 | 用户提「角色配置：不同角色看档案列表不同字段」；质问闸门锁定方案A 一次性完整 auth+内置账号密码登录；澄清锁定角色×档案域粒度/白名单制/列表+详情+编辑生效（用户追加可编辑性）/完整用户管理；产出 REQ-019（5场景+8规则）+F-209/F-210+故事线+流程六+概念架构更新；续：uxqa 评审 C1-C15→darc 全栈编码（apps/auth 新模块+全局鉴权+archive 三处投影+前端登录/管理页/权限抽屉），编码中修复 6 项（含开放网关写回归）；新用例 32 条 104/104+实测 19/19+浏览器两轮全过，待 uxqa 验收 | 闸✓记✓拓✓测✓ | 5问/0改向 |
| 第一百一十五轮 | 2026-08-05 | archive | /archive/api-management、字段释放粒度、补登记 | 用户关注「不同 API 释放不同字段」：核实该能力已存在（exposed_fields 每 API 独立+前端分组勾选+网关读写投影），用户确认现状已够；补登记 v19 设计原则+宪法决策行，不引入读写分离字段清单/密钥级再收窄 | N-A | 1问/0改向 |
| 第一百一十四轮 | 2026-08-05 | archive | /archive/api-management、REQ-005、API Key 鉴权、设计 | API 管理完整设计（v19）：用户提醒补读 reqa 定位 REQ-005（F-204/F-205）；锁定 5 项方向（本期自建 API Key 真实鉴权推翻旧决策/读写全设计守 Hub 宪法/独立密钥×多 API 授权/调用日志 90 天）；产出数据模型+网关六端点+拦截链 401→403→429+双 Tab 交互；纯设计零代码 | N-A | 2问/0改向 |
| 第一百一十三轮 | 2026-08-05 | modeling | /modeling/fields、属性配置、同名字段标记 | 字段属性配置页同名未归并字段标记+检查：后端口径单点化（_find_dup_unmerged_field_groups）+dup-fields 接口；前端告警条+同名角标+tooltip 处置指引+只看冲突过滤，基础/未分配表格同标记；回归 52/52+真实请求实测+浏览器 4/4；同日用户纠正：口径收敛为仅档案字段（base 过滤+分类表角标移除，54/54） | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百一十二轮 | 2026-08-05 | modeling | /modeling/domains、配置检查、同名字段归并 | BUG-2026-0805-01 遗留建议落地：_check_domain_config 新增第 9 项 P1 级「多表同名未归并字段」告警（豁免主键/未释放字段）；新增 5 用例+回归 51/51 PASS；真实域#11 实测命中 4 组 warn | 闸✓记✓拓✓测✓ | 2问/1改向 |
| 第一百一十一轮 | 2026-08-05 | modeling、archive、uxqa | /modeling/domains、/archive、操作列、换行、命名精简 | 测试报告 2 项：①DomainList 操作列换行根治（a-space 补 size4+nowrap、列宽 280→320，同类防御 DataSourceList/DomainFieldMapping）②ArchiveList 按钮名精简（检查/同步）；uxqa 漏检复盘+两条方法论补强落盘（B2 硬约束+A9 操作列文案专项，用户改向确认）；浏览器实测两页无折行 | 闸✓记✓拓✓测✓ | 3问/1改向 |
| 第一百一十轮 | 2026-08-05 | archive | /archive/记录变更历史、同步引擎 | Bug：同一时间同字段被处理两次——同名未映射列写入越权（他表同名空列偷渡清空→归属表写回，batch#48 全批1522条假明细）；兜底收紧为仅主键列（写入+预检两处）+回归测试+存量清理脚本删假明细1522/假快照1522/空批次#48，预检复验零变更 | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百零九轮 | 2026-08-05 | uxqa | 全站巡检、warnings展示、scroll.x、popconfirm | UXQA 全站 16 页巡检，发现 6 项 P2（R-048~R-053）并全部闭环：预检弹窗 warnings 补全、confirmRefresh 路径补 warnings/一致性提醒、2 表补 scroll.x、失效规则删除改 Modal.confirm、插件卸载改 Modal.confirm | 闸✓记✓拓✓测✓ | 1问/0改向 |
| 第一百零八轮 | 2026-08-05 | archive | /archive/consistency、同步引擎 | 紧急修复 3 项：①配置检查范围缩小为档案字段；②主字段检查+一致性检查改警告不阻断；③修复 sync_exclude_codes 排除主键致跨表数据无法写入的关键 Bug | 闸✓记✓拓✓测✓ | 3问/2改向 |
| 第一百零七轮 | 2026-08-04 | archive、modeling | /archive/consistency、/modeling/domains、/modeling/fields | 测试报告反馈 3 项修正：①改名移到属性配置 Tab 支持所有字段（rename_solo）；②配置检查按钮移入配置状态标签；③一致性检查按类型+日期分组展示 | 闸✓记✓拓✓测✓ | 3问/3改向 |
| 第一百零六轮 | 2026-08-04 | archive、modeling | /archive/consistency、/modeling/domains、/modeling/fields | 测试报告 3 项：①域启用配置完整性检查（8项 P0/P1/P2）+配置状态列+启用前置拦截；②组合字段改名+级联更新；③一致性检查大改（4 种检查类型+规则失效机制） | 闸✓记✓拓✓测✓ | 3问/0改向 |
| 系统简介 | 2026-08-04 | project | 系统简介、整体架构 | 基于 constitution/session/route_index 撰写系统整体简介（三大模块+技术架构+数据源+特色+状态），纯文档输出 | N-A | 0问 |
| 第一百零三轮 | 2026-08-04 | archive | /archive/versions、同步统计、组合字段 | 档案同步统计修复：①同一批次内多表同步时刚创建的记录不计入「修改」（created_in_this_batch）；②组合字段非主字段成员不写入档案（_build_sync_exclude_codes）。统计从 3187 降至 974 | 闸✓记✓拓✓ | 1问/0改向 |
| 第一百零二轮 | 2026-08-04 | modeling | /modeling/tables、/modeling/mappings、AI建立关系、引导提示 | 管理表引导提示（顶部 Alert+表格内空状态引导）+ AI建立关系全栈实现（后端 infer_mappings 启发式+LLM双层推断+前端弹窗勾选确认+批量创建） | 闸✓记✓拓✓ | 1问/0改向 |
| 第一百零一轮 | 2026-08-04 | archive | /archive/versions、变更日志、术语、记录详情弹窗、变更历史弹窗 | v18.2 体验 3 项：术语改文案（停用（源侧已删）/复活（源侧恢复），迁移0012）；明细行「进入档案」移除改只读详情弹窗+历史时间线弹窗（套用档案页同款 UI）；排查 4 个 runserver 旧进程并存致重启不生效（BUG-2026-0804-01） | 闸✓记✓拓✓ | 3问/0改向 |
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
- quality 模块尚未启动设计；auth 编码完成待 uxqa 交付验收
