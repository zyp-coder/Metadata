# Debug 日记 — archive 模块

> 记录 archive 模块的 Bug 根因、修复方式与已知耦合点，供后续影响分析使用。

## BUG-2026-0817-01 启动链 loaddata 条件判断误判 → 容器崩溃循环，前端全挂（假象「域管理东西全没了」）

- **现象**（第一百六十六轮）：第一百六十五轮治本上线（compose 启动链 loaddata 条件化：`if Domain.objects.exists() 则跳过，else loaddata`）后，服务器 git pull + `docker compose up -d --build backend` → backend 容器 `Restarting (1)` 循环崩溃 → 前端全部加载失败（用户以为「域管理的东西都没有了」）。日志关键行：loaddata 实际执行（走了 else 分支）→ `IntegrityError: Problem installing fixture '/app/data_dump.json': Could not load modeling.FieldMapping(pk=11): duplicate key value violates unique constraint "modeling_fieldmapping_source_table_id_source_f_da74177b_uniq"`（键 (1,1,2,33) 已存在）
- **根因（两层，第一层已确认闭环）**：
  1. **条件命令 import 路径错误（已确认）**：`INSTALLED_APPS=['apps.modeling','apps.archive','apps.auth']`（settings.py L23-25，`apps.` 前缀），但条件命令写的是 `from modeling.models import Domain` → 任何环境必然 `ModuleNotFoundError: No module named 'modeling'` → 退出码非 0 → if 误判走 else。**本机 + 容器均实测复现**（`from modeling.models` 失败 / `from apps.modeling.models` OK 1）——验证缺口：本地模拟部署验证只测了 migrate/loaddata 两条 Django 内置命令，从未实测自己写的 if 条件命令
  2. **loaddata 撞唯一约束中断启动链**：服务器数据库已有同键 FM（(1,1,2,33) 已存在，pk≠11）→ loaddata 插入 pk=11 撞唯一约束 → IntegrityError → 启动链 `&&` 中断 → gunicorn 未起 → 容器崩溃循环
- **修复**（commit 99c6c86）：compose 启动链**彻底移除 loaddata**——启动链= migrate → init_admin → collectstatic → gunicorn；data_dump.json 仅用于**首次部署手动导入**（compose 注释写明命令 `docker compose exec backend python manage.py loaddata /app/data_dump.json`）。数据库数据未丢（loaddata 撞约束前部分对象已导入，同 pk 记录被 UPDATE 成本机配置=正确方向），恢复后需核查残留
- **教训**：
  1. 启动链/脚本里**自己写的 import 语句必须实测后才可上线**——`INSTALLED_APPS` 用 `apps.` 前缀时 `from modeling.models` 必失败（本机/容器同款报错）；模拟验证只测 Django 内置命令（migrate/loaddata）测不出自定义命令的导入错误
  2. loaddata **非事务**：撞唯一约束会部分导入，恢复后必须核查数据库残留（多出的对象/被覆盖的同 pk 记录）
  3. 「页面全空」先查 `docker compose ps`（Restarting 状态）+ 启动日志，**数据未必丢**，禁止直接走恢复数据流程
  4. 生产启动链禁用自动数据操作：宁可首次部署显式手动 loaddata（写进部署脚本），也不要自动化双分支
- **验证**：YAML 解析 OK（command 展开为纯启动链）；2026-08-17 服务器恢复验证全部通过：①backend Up（不再 Restarting）②curl /api/domains/ 401（后端活）③counts=domains 1/tables 6/fields 101/fms 7/cfgs 2——loaddata 无残留（撞车于 FM pk=11 即中断，dump 的 FM 12/13 未轮到导入，7=服务器原有数量）④DB 补 3 处 OK（cfg2/cfg6 inner+conditions、FM9 inner）⑤diag_precombine 完全收敛：价目 239,504→955、分组 64→桥接 kept 116,594、交集 955、档案 total 955、影子一致 0 warning——服务器与本机完全一致

## BUG-2026-0808-02 同步收尾炸「too many SQL variables」：SQLite 999 变量上限被大列表击穿

- **现象**（第一百三十二轮）：全量同步（去 TOP 1000）实测，主体数据全部写入成功（209,123 条记录、MTL_NAME 100% 有值、PRICE 24,794 精确命中交集），但收尾时顶层报 `档案 10 数据刷新失败: too many SQL variables`，且 stats 显示全 0（records_created/updated 均 0）——与实际落库数据严重矛盾
- **根因（两层）**：
  1. **停用清扫 `exclude(id__in=matched_ids)`**：matched_ids 达 23 万+ 个 id，单条 SQL 塞 23 万参数远超 SQLite `SQLITE_LIMIT_VARIABLE_NUMBER`（999）。该代码在表循环外无 try 保护 → 异常冒泡到 `refresh_archive_data` 顶层 → 顶层 except 用**自己的初始化 stats**（`stats = viewset._sync_data_from_sources(...)` 赋值发生在函数正常返回时，异常时拿不到内部 stats）→ 打印全 0 假象，`change_batch_id: None`（变更日志批次创建在清扫之后未执行）
  2. **分段 exclude 修复方案本身错误**：改为 `for chunk: stale_qs.exclude(id__in=chunk)` 后仍炸——Django 多次 exclude 是 AND 连接（`NOT IN(500) AND NOT IN(500) AND ...`），460 个子句 × 500 变量仍是 23 万变量。**排除型大列表必须反向求差集**
- **修复**：
  1. 停用清扫改为：先拉候选 id 集（`values_list('id', flat=True)`，20 万单列无压力）与 `matched_ids` 内存求差 → `stale_ids` 按 500/批 `id__in` 分批抓身份 + 分批 update（每批独立 SQL）
  2. 变更日志 `data_map` 查询同样按 500/批 `id__in` 分段
  3. 排查确认 `bulk_create`/`bulk_update` 均有 Django 内置自动分批（`bulk_batch_size` = `max_query_params // len(fields)`），不炸，无需改
- **教训**：
  1. SQLite 下任何 `__in` 列表查询都要按 `999 // 字段数` 分批，**排除型（exclude）分批必须用「候选集-排除集差集」而非多次 exclude**
  2. `stats = func(...)` 返回式异常处理：函数内异常时外部拿不到内部状态，排查时不要被全 0 的 stats 误导，直接查库验证实际写入
  3. 大表场景（20 万+行）每处批量操作都要过变量上限审查，不能只靠既有测试（40 测试全部 mock 小数据，从未触达真实量级）
- **验证**：修复后重跑全量同步：6/6 表、errors 空、209,123 条、耗时 11 分钟、变更明细 11,677 条 updated 正常落库（batch#61）

## BUG-2026-0808-01 档案同步 0 记录：改名后 physical_name 丢失 + pk_fields 用 Field.code 而非 schema code

- **现象**：用户配置了产品主数据域（6 张外部 SQL Server 表），档案 schema 已生成（42 字段），但同步始终返回 `records_created=0`，无报错。
- **根因（三层叠加）**：
  1. **physical_name 丢失**：`rename_solo` 改名时直接覆盖 `Field.code`，原始物理列名丢失。`_build_code_to_physical` 用 `f.code`（改名后的编码）作为外部表列名查询，改名后找不到对应列。
  2. **solo 字段映射逻辑错误**：`_build_code_to_physical` 的 solo 字段循环用 `phys_code in schema_type_map` 检查，但 `schema_type_map` 的 key 是 schema code（如 `A_CREATE_ORG_ID`），而 `phys_code` 是物理列名（如 `CREATE_ORG_ID`），永远匹配不上。
  3. **pk_fields 用 Field.code 而非 schema code**：主键字段属于 StandardField（MTL_ID），Field.code 是 `MATERIAL_ID`，但 `record_data` 的 key 是 schema code `MTL_ID`，导致记录匹配时 key 取不到值，所有行被跳过。
- **修复**：
  1. Field 模型新增 `physical_name` 字段（迁移 0029），存量回填 `physical_name = F('name')`（Field.name 保留原始列名）
  2. `_build_code_to_physical` 改用 `physical_name or code or name` 作为物理列名
  3. solo 字段循环改为按 `f.code` 匹配 schema code，值用 `physical_name`
  4. `pk_fields` 构建改为用 schema code（StandardField.standard_code 或 Field.code）
  5. 数据源导入/Excel 导入创建字段时设 `physical_name=col_name`
- **影响文件**：`modeling/models.py`、`modeling/migrations/0029`、`modeling/views.py`、`modeling/excel_service.py`、`archive/views.py`
- **教训**：改名功能必须保留原始物理列名（`physical_name`），同步逻辑必须区分「概念编码」和「物理列名」两个维度。pk_fields 必须和 record_data 用同一套编码体系（schema code）。

## BUG-2026-0804-01 后端重启「不生效」：4 个 runserver 旧进程并存，请求随机路由到旧进程

- **现象**（第一百零一轮）：改 models.py ChangeType label 后 makemigrations/migrate 成功、runserver 也重启了，但 API 仍返旧文案；模型层新进程（python -c）验证新文案已生效——自相矛盾。
- **根因**：机器上并存 **4 个 runserver 进程**（旧 PID 18908/19396/29776 此前未真正退出 + 新启的 34692）。Windows 下 SO_REUSEADDR 使多进程同时绑 0.0.0.0:8000，请求被随机路由到某个旧进程（持旧代码）。`Get-NetTCPConnection` 只枚举到一个 listener 造成「已单实例」假象。
- **修复**：`Get-CimInstance Win32_Process -Filter "Name='python.exe'"` 按 CommandLine like '*runserver*' 枚举全部进程并 Stop-Process，再单实例启动——API 即返新文案。
- **经验（叠加 BUG-2026-0725-04 旧进程教训）**：后端改动「不生效」时，先用 Win32_Process 按 CommandLine 枚举**全部** runserver 进程（不能只信 Get-NetTCPConnection），确认单实例后再启动；模型层对但 API 不对 = 服务进程旧/多。

## BUG-2026-0725-04 回滚功能报错：旧 Django 进程未加载新端点

- **现象**：v17 回滚功能上线后，前端点「回滚」报错。
- **根因**：两层叠加：
  1. 主因：运行中的 Django 服务（旧 PID 23608，`--noreload` 启动）在回滚代码写入前就已启动，未加载 /change-details/{id}/rollback/ 与 /records/{id}/rollback-to-change/ 新路由 → 404 HTML 页（实测复现）。测试进程（Django test Client 新进程）冒烟单条回滚 200 ✓，证明代码本身正常。
  2. 次因（真 Bug）：历史回滚时间线**最新节点**也显示「回滚到此」按钮，点击必然 400「该时间点之后无可回滚的变更」（时间点回滚语义=撤销此后变更，最新节点无后续）。
- **修复**：
  1. 重启后端（新 PID 31544），端点实测生效；端到端冒烟：时间点回滚 200 + 留痕 change_type=rollback ✓。
  2. 前端新增 `canRollbackToPoint(index)`：时间线按 id 降序，仅当 `slice(0, index)` 中存在非 created/rollback 的变更时才显示「回滚到此」（最新节点自动隐藏）。
- **已知耦合点/经验**：
  - 后端用 `--noreload` 启动：**每次新增/修改 API 后必须手动重启**，否则新端点 404（历史已多次踩坑：第八十七/八十八轮均重启过）。排查此类「代码对但接口报错」先查进程新旧：test Client 能通但 HTTP 打不通 = 服务进程旧。
  - 详情弹窗与变更历史弹窗共用 rollbackHistory/rollbackLoading 数据源，`refreshAfterRollback` 以弹窗打开状态（historyModal/detailModal）判定刷新目标。

## BUG-2026-0728-03 档案 schema 字段口径/分组与建模脱节 + 改过记录不置顶

- **现象**（第七十轮测试报告，页面 /archive/5，3 项）：
  1. 档案界面分组（基本信息/地址信息/展厅信息）与建模字段分组（门店信息/省市区/联系信息/状态信息/经纬度/地理位置）不一致；
  2. 档案 schema 38 字段 vs 建模「档案字段」28 行——18 个 archive_category='unassigned' 字段混入档案（实证 IS_GZ_PCS、STORE_VERSION、N_AREA、D_CHECK_DATE 等）；
  3. 表格改过（未同步）的记录不置顶，靠 Meta ordering=['-updated_at'] 排序。
- **根因**（同一系统性缺陷两处表现 + 一处排序缺失）：
  1. `archive/views.py _field_released(f, sf)` 只做两层释放门控（release_to_concept + release_to_archive/is_active），**没有三分类口径**（第五十九轮已定：档案字段 = base 物理字段 + active 组合字段 + active 计算字段）；modeling 的 standard-fields action 已按此过滤，档案侧漏改——同类模式缺失。
  2. Archive.schema 是快照，仅创建/sync-schema 时刷新；建模侧改分组后档案不自动更新（快照过期），且 `_generate_schema_from_domain` 原按 table__id 排序不按分组排序。
  3. ArchiveRecordViewSet.get_queryset 无置顶逻辑。
- **修复**：
  1. `_field_released` 加三分类判定：sf 存在须 `sf.status=='active'`；solo 须 `f.archive_category=='base'`。该函数是唯一门控——schema 生成、sync_to_source 回写映射、modeling archive-preview 三个调用点自动统一。
  2. `_generate_schema_from_domain` 排序改 `F('group__sort_order').asc(nulls_last=True), F('group__id').asc(nulls_last=True), 'sort_order', 'id'`，分组顺序对齐建模、未分组排后。
  3. `ArchiveRecordViewSet.get_queryset` 加 `annotate(_sync_rank=Case(When(sync_status='synced', then=1), default=0)).order_by('_sync_rank','-updated_at')`——未同步置顶。
  4. 对档案5 重跑 sync-schema：schema 38→29 字段（27 物理 + 2 计算），分组与域8 完全一致，18 个未分配字段移除（记录 data 保留，仅不再展示/回写）。
- **已知耦合点**：
  - `_field_released` 是档案字段口径的**唯一收口点**，任何新增「字段是否进档案」判断必须走它，禁止在调用点再散写过滤条件。
  - `ArchiveRecord.sync_status` 是普通 CharField（无枚举类），取值 unsynced/synced/partial/error——代码里只能写字符串字面量。
  - Archive.schema 快照机制不变：建模侧改分组/口径后需手动 sync-schema 才生效（页面有同步模型变更按钮）。
  - ~~编辑记录后自动 status='deleted'~~【已于 2026-07-28 第七十二轮取消】：编辑后不再自动停用，改为登记 override 修正保护+lineage=manual；`sync_status='unsynced'` 仍会设置，置顶排序仍依赖此标志；sync_to_source 恢复 active 语句保留仅兼容存量 deleted 记录。
  - MDM 第6批新增耦合点：`_upsert_records_from_rows` 已是逐字段比对引擎，任何改动必须保持「差异不覆盖只入队 ArchiveFieldConflict」铁律；overrides/lineage 的读写分散在 serializers（编辑登记）/views 比对引擎（补血缘）/_apply_resolution（裁决解除）三处，数据结构变更需三处同步。
- **验证**：sync-schema 200，schema_version 2→3、字段 38→29、分组顺序=经纬度/门店信息/省市区/联系信息/状态信息/地理位置/(空)/计算字段、未分配字段残留=无；置顶排序可逆实测：将最旧记录临时置 unsynced 后 API 第一页首条即该记录（PASS），随后还原。

## BUG-2026-0805-01 同一时间同一字段被处理两次——同名未映射列写入越权（假变更风暴）

- **现象**：用户反馈变更历史中同一秒、同一条记录的同一批字段出现重复明细（截图：GFW5201705/百色市，09:23:52 两条相同「修改」）。查库实证（档案9 record#11574/GZT0001）：batch#48（2026-08-05 01:23:52 UTC）内同记录两条明细——v4→v5 把 `D_CHECK_DATE/N_AREA/STORE_VERSION` 清空为 null，v5→v6 又写回原值；全批 1522 条明细 = 761 清空 + 761 回填，**整轮刷新的"修改"全是假变更**，版本号虚增 2。
- **根因**：同名未映射列写入越权。
  1. `D_CHECK_DATE/N_AREA/STORE_VERSION` 同时存在于表19（档案信息，有值）与表20（门店信息修改，全 null），`_build_code_to_physical` 的兜底映射按 Field 遍历顺序只把这三个 code 挂给表19（先到者独占）；
  2. 但 `_upsert_records_from_rows` 行级解析有兜底 `if col_name in schema_type_map: schema_code = col_name`——**只要源行列名与 schema code 同名，无论该表是否有此字段的正式映射都写入**，表20 的三列由此偷渡；
  3. 表遍历顺序 Table.Meta ordering=['-created_at']，表20 排在表19 之前 → 表20 先用 null 抹掉已有值（假变更①）→ 表19 再写回真值（假变更②），每次刷新必现；
  4. batch#47（首轮填值）未暴露：清空写 null 时旧值本就为空，无差异不记录；自第二轮起清空→回填每轮复现。
- **同类排查**：同构兜底共 2 处——`_upsert_records_from_rows`（正式写入）与 `_preview_data_changes`（预检 dry-run，L864-867），两处同改。
- **候选方案对比**：①治本-收紧列名兜底（选定）②治标-null 不覆盖已有值（两表值都非空时仍互相覆盖，且破坏源侧合法清值语义）③配置层-组合字段+主字段（只治已配置字段，其他同名列仍漏）。
- **修复**：
  1. 两处兜底均收紧为**仅主键列**允许同名兜底（`col_name in pk_fields and col_name in schema_type_map`）——主键列是跨表记录匹配必需（辅表 STORE_NO 未注册时仍靠它匹配），其余未映射列一律跳过；
  2. 新增回归测试 `SyncFieldNameLeakTest`（mock 源行注入：辅表同名空列不得清空主表值、零变化不 bump 版本不建批次、辅表主键兜底匹配仍有效）；archive 套件 19/19 PASS；
  3. 存量清理脚本 `backend/scripts/cleanup_fake_sync_changes.py`（默认 dry-run）：检出「全清空+全回填」精确互逆配对 → 校验快照数据绕回原点且未定版 → 删假明细/假快照+版本重编号+明细版本引用改写+清空批次。实际执行：删假明细 1522 条、假快照 1522 个、重编号 761 条记录、删空批次 #48；复检残留假配对 0；record#11574 版本链归位 [1,2,3,4] 数据无损；
  4. 修复后对档案9 跑只读预检：would_create=0/would_update=0/would_deactivate=0——假变更清零且未误伤真实变更。
- **教训**：
  - "列名与 schema code 同名即写入"的隐式兜底是越权入口：**写入口径必须收敛到正式映射（code_to_physical）**，兜底只留给匹配键这类结构性必需；
  - 多表同名字段是常态源数据形态，映射"先到者独占"且无提示——后续可考虑在域配置层面对"多表同名未归并字段"给出显式告警（本次未做，待用户决策）。

## BUG-2026-0806-01：变更日志明细页菜单误高亮「档案管理」（用户反馈）

- **现象**：用户在变更日志明细页（/archive/versions?domain=11）时，左侧菜单高亮「档案管理」而非「变更日志」子项，用户困惑“明明是变更日志功能为什么跳到档案管理”。
- **RCA**：MainLayout.vue 菜单高亮靠**手动维护的白名单** allMenuKeys 做最长前缀匹配（R-013 第九十四轮建的机制）；变更日志明细页 /archive/versions 不在白名单 → 前缀匹配落到 /archive → 高亮档案管理。同类排查（全部子路由逐一核对）：/modeling/domains/:id/* 命中域管理✓、/archive/:id 与 /:id/consistency 命中档案管理✓（档案下钻合理），仅 /archive/versions 一处错漏。复发核查：与 R-013 同属菜单高亮类第二次，但根因不同（R-013 缺同步机制，本次是白名单手动维护漏登记新页面）。
- **候选方案对比**：①治标-watchEffect 加一行 /archive/versions 特判（下次新页仍会漏）②**治本（用户选定）**：白名单从 menuItems 递归自动推导（collectMenuKeys）+下钻页别名表 MENU_ALIAS_PREFIX（/archive/versions → /archive/domain-changes），新增菜单项不会再漏。
- **修复**：MainLayout.vue 单文件——collectMenuKeys 递归提取以 / 开头的叶子 key；别名表最长前缀优先转换；原 allMenuKeys 常量删除（代码删除登记：仅删手动白名单数组，能力由自动推导完整承接）。
- **修复中引入并当场拦截的二次缺陷**：watchEffect 首次同步执行回调时访问尚未声明的 menuItems（TDZ）→ 全站白屏（控制台 Cannot access 'menuItems' before initialization）；浏览器实测第一轮发现，将 watchEffect 移到 menuItems computed 声明之后解决。vue-tsc 查不出此类运行时 TDZ（闭包内引用不算提前使用），**布局/全局组件改动必须浏览器实测**。
- **验证**：vue-tsc 0 errors；Browser 子代理 5 页实测（/archive/versions 与 /archive/domain-changes 均高亮变更日志、/archive 高亮档案管理、/modeling/domains 高亮域管理、/archive/api-management 高亮 API管理），DOM 检测 ant-menu-item-selected 5/5 符合期望，控制台零应用级 error（截图工具故障未留图，结论靠 DOM class 确定性核验）。
- **教训**：①“手动白名单 + 新页面忘登记”是结构性漏洞，同类匹配表一律改为从源头（menuItems/路由表）自动推导；② watchEffect/watch 回调若访问后声明的 const，必须放在声明之后（首次同步执行会 TDZ）；③ 浏览器截图工具可能故障，验证结论可降级为 DOM 精确检测（class/属性断言）。

## BUG-2026-0813-01 服务器同步预检报「'mssql' isn't an available database backend」（用户反馈）

- **现象**（第一百五十九轮续）：用户部署到服务器后，档案同步预检报错 `EDS_K3_物料信息: 'mssql' isn't an available database backend or couldn't be imported`，4 张 SQL Server 表全部报同错，预检无法完成。
- **RCA**：三层依赖缺二——① 代码全部 SQL Server 连接经 `ENGINE_MAP['sqlserver'] = 'mssql'`（distinct_cache.py）动态建连接，OPTIONS 硬编码 `'ODBC Driver 18 for SQL Server'`（archive/views.py、modeling/views.py 等 6 处）；② 服务器 Docker 镜像（python:3.12-slim）`pip install -r requirements.txt` 只装清单内包，**requirements.txt 从未包含 mssql-django**（本机 venv 1.7.3 为手工安装，未登记清单——同一事实两处存放隐患，服务器部署踩中）；③ slim 镜像无微软 ODBC 驱动（unixodbc + msodbcsql18），即使装上 pip 包 pyodbc 也连不上 SQL Server。
- **修复**：① `backend/requirements.txt` 追加 `mssql-django>=1.7,<2.0`（对齐本机实装 1.7.3，依赖清单成为唯一主副本）；② `backend/Dockerfile` 新增微软官方源安装层（curl/gnupg2 拉取签名 → Debian 12 prod.list → `ACCEPT_EULA=Y` 装 `msodbcsql18` + `unixodbc-dev`）；③ 服务器需重新 `docker compose build backend` 后重启生效。
- **验证**：本机 mssql-django 1.7.3 已装且 `importlib.import_module('mssql.base')` 成功（后端可加载）；Dockerfile/requirements 语法层检查通过；服务器侧待用户重新 build 后实测同步。
- **教训**：① **依赖清单（requirements.txt）必须是唯一主副本**——本机手工 pip install 而不登记清单 = 分叉冻结，部署时必然踩空（rule §8 一致性底线）；② SQL Server 数据源连 Linux/Docker 需要**双依赖**（pip 包 mssql-django + 系统 ODBC 驱动），漏任一报错不同但都连不上；③ 驱动名 'ODBC Driver 18 for SQL Server' 在代码 6 处硬编码，Dockerfile 装 18 版驱动才能匹配。
