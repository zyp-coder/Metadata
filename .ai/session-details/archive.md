# 模块详情：archive

### 第一百六十六轮（2026-08-17）标签：loaddata事故、容器崩溃、启动链、事故修复、方案A

**任务**：第一百六十五轮治本（compose 启动链 loaddata 条件化）上线后服务器事故——用户报「服务器更新之后域管理的东西都没有了」。

**事故链条（取证）**：docker compose ps 显示 backend `Restarting (1)` 循环崩溃；日志 = loaddata 走了 else 分支 → `IntegrityError: Could not load modeling.FieldMapping(pk=11): duplicate key (1,1,2,33) already exists` → 启动链 && 中断 → gunicorn 未起 → 前端全挂（假象）。关键判断：报错证明数据库配置**都在**（数据未丢），页面全空是后端崩溃所致。

**根因**：①条件命令 `shell -c '...sys.exit(0 if Domain.objects.exists() else 1)'` 在容器内误判走 else（具体原因未复现——本地模拟只测了导入路径，未实测 if 分支，验证缺口）；②服务器库已有同键 FM（pk≠11）→ loaddata 插入撞唯一约束。

**修复（方案A，用户确认，commit 99c6c86）**：启动链彻底移除 loaddata（migrate→init_admin→collectstatic→gunicorn）；data_dump.json 仅用于首次部署手动导入（compose 注释写明命令）；YAML 解析验证 OK。

**状态变更**：v20 决策（loaddata 条件化）被推翻 → v21（启动链零数据操作，首次部署手动灌）；constitution 决策行已标【推翻】。

**服务器恢复验证（全部通过）**：①docker compose ps backend Up（不再 Restarting）②curl /api/domains/ 401（后端活；/api/modeling/domains/ 404=路径错误不影响）③counts=domains 1/tables 6/fields 101/fms 7/cfgs 2——loaddata 无残留（撞车于 FM pk=11 即中断，dump 的 FM 12/13 未轮到导入，7=服务器原有数量）④DB 补 3 处 OK（cfg2/cfg6 inner+conditions、FM9 inner；修正版命令用 apps.modeling 前缀）⑤diag_precombine 完全收敛：价目 239,504→955、分组 64→桥接 kept 116,594、交集 955、档案 total 955、影子一致 0 warning——服务器与本机完全一致。

**根因闭环确认**：条件命令 `from modeling.models import Domain` import 路径错误（INSTALLED_APPS 用 `apps.` 前缀，settings.py L23-25）→ 任何环境必 ModuleNotFoundError → 退出码非 0 → 误判走 else（本机+容器实测复现，debug-diary BUG-2026-0817-01）。

**遗留**：界面同步收敛 955 待用户确认（用户已被告知重跑同步后反馈）

### 第一百六十五轮（2026-08-17）标签：27281根因、data_dump基线、loaddata条件化、配置分发、治本

**任务**：服务器 diag_precombine 输出对比定位 27281 vs 955 根因 + 配置分发机制治本。用户连续追问「data_dump 为什么是旧的」「应该跟我的配置做」→ 解释机制（快照=出厂设置，只在首次部署读；配置存数据库不随 git 走）+ 用户拍板治本。

**根因（证据链）**：
- 服务器 cfg2/cfg6 conditions=[]、join_type=left、updated_at=08-11（=data_dump 导出时间）；FM9 价目挂载 left、FM11 分组挂载 inner 但无条件 → kept=209,123 全量 → 主表 239,504 行匹配 27,281 行 = 用户看到的 27281
- dump 考古：FieldMapping/DetailTableConfig 记录无 join_type 字段（后续模型新增）→ loaddata 取默认 left
- 机制缺陷：启动链每次 loaddata 覆盖数据库，服务器改配置重启即还原

**方向锁定**：命中数据流向（配置分发机制）→ rule §11.1 方向理解清单 4 条 + adqa 质疑关 5 条（#4 存活：新部署用旧 dump 重踩 27281 → 整改项 R-001；#1/#5 执行时验证；#2/#3 证伪失败）→ 用户全确认。

**变更文件**：
- `deploy/docker-compose.yml`：启动链 loaddata 条件化（`if Domain.objects.exists() 跳过，else loaddata`，仅首次部署灌快照）
- `deploy/data_dump.json`：重新导出正确基线（排除 auth.user/authtoken/userprofile/archive；PYTHONUTF8=1 防 GBK 编码；91KB/133 对象）
- `.gitignore`：解除 /deploy/data_dump.json 忽略（决策变更，用户确认入库）

**验证**：模拟首次部署（临时 sqlite 库 migrate+loaddata 全量 133 对象导入 OK + cfg2/cfg6 inner+conditions 正确）；YAML 解析 OK；commit c46ed2b→push 待做。

**状态变更**：服务器配置分发从「每次启动 loaddata 覆盖」→「仅首次初始化 + 数据库为准」；配置基线从 08-11 旧版 → 08-17 正确版入库。

**遗留**：服务器待执行 git pull → up --build（看 loaddata skipped）→ DB 补 3 处（cfg2/cfg6 conditions+join_type、FM9 inner）→ diag 重跑验证 kept 955/116,594 交集 955 → 界面重跑同步收敛；用户「在哪台机器配的」未确认（不阻塞：本机 dev.db=正确主副本）

### 第一百六十四轮（2026-08-17）标签：diag_precombine、诊断命令、预组合过滤、本机vs服务器对比

**任务**：用户报服务器档案同步出 27281 条（本机 955 正确），预组合配置界面已确认（物料分组 64 条限制 + inner join），代码已 git 同步；用户要求把同步逻辑做成可打印的 debug 工具，两侧各跑一次对比。prjm 路由→AskUserQuestion 确认「做诊断命令」→ darc 执行。

**关键判断（影响分析）**：预组合配置（DetailTableConfig.conditions / FieldMapping.join_type）存数据库、不随 git 走——代码同步 ≠ 配置同步；session 第一百六十二轮留痕「服务器 data_dump 配置暂缓」是最大嫌疑。

**变更文件**：
- `backend/apps/archive/management/commands/diag_precombine.py`（新文件，只读不改数据）：`python manage.py diag_precombine --domain-id N [--archive-id M] [--no-query]`
  - 第一部分 配置全景：主表/主键/每表数据源/DetailTableConfig（conditions 原样 JSON + join_type + 头表关联 + updated_at）/detail 挂载 FieldMapping；高亮 cfg.join_type != fm.join_type 不一致（同步实际用 fm.join_type）
  - 第二部分 逐步模拟：复用 ArchiveViewSet 纯方法（无 request 实例化），逐挂载打印 条件来源→header/detail 拆分→明细行数→头表带条件行数→JOIN 后行数→src_values 大小→same_domain→桥接行数→kept→交集；逻辑与 _build_precombine_filters 逐行对齐
  - 第三部分 影子校验：真实 _build_precombine_filters 对比 warnings 与结论（防诊断逻辑漂移）
  - 第四部分 档案统计：total/active/synced
- 踩坑修复：Windows 控制台 GBK 不支持 ✓/⚠/★/→ 等符号（UnicodeEncodeError）→ 全部 ASCII 化（FAIL/WARN/OK/->）；`--no-query` 模式验证配置输出
- 修正：默认取域下第一个档案（不限 status）——本机档案 #3 是 draft 状态但 active=955 正是目标档案

**本机实跑验证（域 2 档案 #3，EXIT:0）**：
- 挂载#12 价目明细：header 条件 NAME eq 明码实价 → 头表 1 行 → inner JOIN 239,504→955 → src_values=955 → same_domain=True → kept=955
- 挂载#13 物料分组：detail 条件 FULL_PARENT_ID starts_with .101041 → 明细 64 行（用户限制生效）→ 头表 1,782 行 → JOIN 后 64 行 → same_domain=False → 桥接物料表 209,123 行 → kept=116,594
- 交集=955；影子校验一致（真实函数生成 row_filter [1,2,6]，0 warnings）；档案 active=955 完全吻合
- 关键对比证据：本机 cfg2 updated_at=2026-08-17 01:13:38、cfg6 updated_at=2026-08-13 08:54:13

**状态变更**：诊断命令已交付；服务器侧待用户跑 `docker compose exec backend python manage.py diag_precombine --domain-id 2` 对比输出定位根因（重点：cfg.conditions 是否缺失/旧、kept 大小、交集）。

**遗留**：若服务器 cfg.conditions 缺失/不同 → 需在服务器数据库修正配置（或重新导入 data_dump），并重跑同步收敛 27281→955。

### 第一百五十九轮续2（2026-08-13）标签：服务器同步、mssql后端缺失、ODBC Driver 18、Dockerfile、requirements

**任务**：用户部署服务器后档案同步预检报错 `'mssql' isn't an available database backend or couldn't be imported`（4 张 SQL Server 表同报），预检无法完成。

**诊断（事实链）**：
- 代码全部 SQL Server 连接经 `ENGINE_MAP['sqlserver']='mssql'`（distinct_cache.py L11）动态建连接，OPTIONS 硬编码 `'ODBC Driver 18 for SQL Server'`（archive/views.py + modeling/views.py 共 6 处）
- 本机 venv 有 mssql-django 1.7.3 + pyodbc 5.3.0（**手工安装**），requirements.txt 从未包含——依赖清单与实装分叉
- 服务器 Docker 镜像（python:3.12-slim）只装 requirements.txt 内包 → 无 mssql-django；且 slim 镜像无微软 ODBC 驱动 → 即使有 pip 包也连不上

**变更文件**：
- `backend/requirements.txt`：追加 `mssql-django>=1.7,<2.0`（对齐本机实装 1.7.3，清单成为唯一主副本）
- `backend/Dockerfile`：新增 ODBC 安装层（curl/gnupg2 拉微软签名 → Debian 12 prod.list → ACCEPT_EULA=Y 装 msodbcsql18 + unixodbc-dev）

**验证**：本机 mssql-django 1.7.3 已装，`importlib.import_module('mssql.base')` 成功；Dockerfile/requirements 语法层检查通过；服务器侧待用户重新 `docker compose build backend` 后实测同步。

**状态变更**：BUG-2026-0813-01 已修复（代码侧闭环），待服务器 rebuild 验证。

**教训**：依赖清单（requirements.txt）必须是唯一主副本——本机手工 pip install 不登记 = 分叉冻结，部署必然踩空；SQL Server 数据源连 Linux/Docker 需双依赖（pip 包 + 系统 ODBC 驱动）。

### 第一百五十九轮续（2026-08-13）标签：档案删除、SQLite too many SQL variables、perform_destroy、combined_updates、ArchiveChangeDetail SET_NULL

**任务**：用户反馈「档案列表点删除删除不了」。诊断为后端 DELETE /api/archives/1/ 500 OperationalError：too many SQL variables。

**根因**：SQLite 999 绑定变量上限。Django 6.0 Collector 的 `combined_updates` 优化将过多 PK 合并到单条 UPDATE 语句（`ArchiveChangeDetail.detail_group` FK SET_NULL），超限。

**第一次修复（不足）**：按 record_id 500/批分别 delete 版本/明细/记录。但 `ArchiveRecordDetail.objects.filter(record_id__in=batch).delete()` → Collector 收集 ~1250 详情 PK → combined_updates UPDATE SET NULL 超限。

**第二次修复（成功）**：先清 `ArchiveChangeDetail.detail_group` 反指 FK（200 PK/批 update detail_group=None），再按 200 PK/批 delete ArchiveRecordDetail。

**修改文件**：
- `backend/apps/archive/views.py`：perform_destroy 完全重写——ArchiveRecordVersion 按 record_id 500/批 DELETE（无反向 FK）；ArchiveRecordDetail 先清 ArchiveChangeDetail 反指 FK、再按 detail PK 200/批 DELETE；ArchiveRecord 按 PK 500/批 DELETE；instance.delete() CASCADE 兜底量小关联

**验证**：curl DELETE /api/archives/1/ → 204 No Content ✅

**状态变更**：
- `perform_destroy` 从简单分批升级为三层策略（考虑反向 FK SET_NULL 触发器）
- 教训：SQLite 下 Django 6.0 的 combined_updates 会将反向 SET_NULL 的 FK 合并为单条 UPDATE，PK 数 > 999 时必炸，必须手动清空反向 FK 再删

**回执**：闸[✓] 记[✓] 拓[✓] 测[✓（curl 实测 204）]

### 第一百五十九轮（2026-08-13）标签：普通关联筛选条件、_upsert_dimension_via_mapping、conditions透传、FieldMappingConditionsApiTest、ReferenceConditionsSyncTest

**任务**：批2③ reference 映射筛选条件接入同步引擎（配合前端弹窗条件构建器）。
**变更摘要**：`_upsert_dimension_via_mapping` L2503 `trows = self._query_external_table(target, order_by=t_order_by)` → 增加 `conds`（仅 `fm.relation_type == RelationType.REFERENCE and fm.conditions` 时传，detail 不传——明细条件在 detail_config 上、目标表行不过滤，行为不变）；`_query_external_table`/`_build_conditions_sql` 零改动（2026-08-08 已支持）。
**新增测试**：FieldMappingConditionsApiTest（PATCH null 400 锁定「不能为 null」/[] 200/列表 200 落库）+ ReferenceConditionsSyncTest（reference 带条件透传/无条件 None/detail None，mock _query_external_table）。
**验证**：新增 6/6 PASS + apps.archive 全套 60/60 PASS。
**遗留**：同步实际过滤效果待服务器部署后全量同步验证（条件字段=目标表字段编码，白名单校验在同步期执行，非法字段会进 stats.errors）。

### 第一百五十轮（2026-08-12）标签：全量同步实测、走通有数据、SQLite写锁、row_key去重

**任务**：用户要求「你能帮我测试一下先么？先走通有数据的」——实际走通同步流程，把真实数据写入系统。

**过程**：
- 写临时脚本 diag_full_sync.py 模拟前端全流程：refresh-preview 预检 → 确认 → POST sync-schema（预检发现 schema 有变化，走全量拉取+重建 schema 路径）
- 600s 测试脚本超时被杀，但**后端同步线程仍在执行**（记录持续增长 ~200 条/s，客户端断开不终止服务端线程）
- SQLite 被写锁锁死（database is locked），期间系统整体不可用；通过监控 dev.db-journal 判断写事务活跃度（autocommit 每条 save 单独事务，journal 短暂消失是事务间隙），连续 90s 无 journal 确认同步结束
- AskUserQuestion 确认：用户选择「继续等同步跑完（推荐）」

**结果（最终态）**：
- ArchiveRecord = **209,123** 条（全部 active/synced），创建窗口约 18 分钟
- ArchiveRecordDetail = **49,588** 条：mapping_id=3（价目表明细）24,794 + mapping_id=9 24,794（收尾阶段补入 8,041 条）
- 主记录字段：部分记录 11 字段（含 PRICE/TO_QTY/PRICE_UNIT_ID/PRICE_BASE/FORBID_STATUS 代表行字段），其余仅 6 主表字段
- 档案状态仍 draft、schema_version=1、schema 32 字段

**变更文件**：无产品代码变更（临时诊断脚本 diag_*.py / diag_out*.txt 已全部清理；历史遗留 diag_fix*.py / diag_append_design.py 未动）

**遗留问题（已定位未修复，待用户裁决）**：
1. **变更批次/操作日志缺失**：ChangeBatch=0、操作日志仅 1 条 create——sync_schema 收尾（变更批次落库 + SCHEMA_SYNC 日志）未执行，疑似请求线程异常中断
2. **物料分组明细 0 条**：cfg id=6 pk_physical_to_schema 为空——GROUP_ID 经 FieldMapping 中转映射不在 code_to_physical/match_channels 直接匹配通道，_sync_detail_rows 直接 return
3. **row_key 配置错误**：cfg id=2 row_key_field=MATERIAL_ID 非唯一，价目明细 239,504 行去重为 24,794 条（每物料仅保留排序后最后一条）
4. **NAME/DESCRIPTION（价目表头）0 值**：抽查 100 条 NAME 0/100，维度表中转写入未生效
5. **代表行字段覆盖不均**：仅 24,794 条有价目明细的物料含 PRICE 等字段（架构预期：代表行只更新有明细的物料）

**状态变更**：无（数据已就位，档案状态仍 draft）

**验证**：API refresh-preview 实测 36s 返回 timeout=200、tables_checked=3、errors=[]、would_create=209123；最终数据态 shell 查询 209,123 / 49,588 / 0 / 0 / 1；同步期间及结束后系统恢复正常响应

### 考古修正
- **「变更批次缺失」实为误报**：版本快照（ArchiveRecordVersion） 209,125 条 update 记录证明昨天同步收尾实际完成（ChangeBatch id=1 10:15 UTC + OpLog id=2 10:27 UTC），只是我昨天验证时收尾未执行完（延迟~50分钟，batch_recalculate 耗时）
- **「24,790 条主记录有 PRICE」实为误报**：209,125 条 update 版本快照中仅 3 条含 PRICE 字段——昨天的验证脚本查错了对象/口径
- **真正缺陷**：代表行只写 `sorted_rows[0]`（全局首行），25,993 个有价目明细的物料中仅 1 个在主表有 PRICE；与第 133 轮「默认价=每物料」锁定语义不符

### 第一百五十轮续（2026-08-13）标签：row_key修复、代表行分组修复

**任务**：用户确认先修 row_key（DTC id=2 MATERIAL_ID→ENTRY_ID）+ 考古发现代表行缺陷后，用户确认「只管系统逻辑」

**变更文件**：
- `backend/apps/archive/views.py`（L2081-2092）：_sync_detail_rows 代表行改为按物料（rec_key）分组遍历——每组取排序后首行写主表，跳过已见过的同组键；注释更新对齐第 133 轮锁定语义

**验证**：django check 0 issues；DetailSyncEngineTest 8/8 PASS；未重跑同步（用户确认「数据不用处理」）

**状态变更**：
- 遗留 row_key 配置错误 → 已修复 ✓
- 代表行只写全局首行 → 已修复 ✓（待下次同步验证）
- 变更批次缺失 → 已澄清（收尾延迟非缺失）
- 遗留：物料分组明细 0 条（cfg id=6 pk_physical_to_schema 为空）、NAME/DESCRIPTION 0 值（待用户裁决）

### 第一百四十九轮（2026-08-12）标签：续诊同步无反应、axios超时

**任务**：用户续诊「不对，你debug一下，我等了很久也没有/」——后端预组合跳过已修复（36s返回），但用户仍然等不到响应。

**诊断**：前端 axios 默认 timeout:30000ms（30s），后端 refresh-preview 耗时 36s，导致前端 30s 超时。用户看到的不是预检弹窗，而是 30s 后一闪而过的「预检失败」。这是双层问题：第1层后端预组合表跳过（已修复），第2层前端超时 < 后端耗时。

**变更文件**：
- `frontend/src/api/archive.ts`：refreshPreview 单独设 timeout:180000（180s），覆盖全局 30s 默认值
- `frontend/src/views/archive/ArchiveList.vue`：catch 块区分 timeout 错误，提示「预检超时：源数据量较大（约20万条），请耐心等待60秒左右」

**状态变更**：无

**验证**：后端实测 36s 返回 timeout=200、tables_checked=3、errors=[]、would_create=209123；vue-tsc 0 errors；django check 0 issues

**遗留问题**：37s 仍是远程 SQL Server 网络延迟 + 209K 行数据量的硬耗时，无法进一步优化

### 第一百四十八轮（2026-08-12）标签：产品档案同步预检超时、预组合表跳过、loading

**任务**：用户反馈产品档案同步"完全没反应"，怀疑预组合表导致。诊断定位：本机开发环境 archive 1（产品主数据档案）状态=draft、记录=0，点击同步调用 refresh-preview 因预组合明细子表被全量查询（239K+14K 行）而超时

**变更文件**：
- `backend/apps/archive/models.py`（M1）：ArchiveChangeDetail 扩展——`detail_group` FK（ArchiveRecordDetail，nullable，SET_NULL）+ `detail_row_key` CharField（max_length=200，行键值快照，解耦回滚）；新增 `ChangeType.DETAIL_SYNC = 'detail_sync', '明细同步'`
- `backend/apps/archive/serializers.py`（M2）：ChangeDetailSerializer 扩展 detail_group / detail_row_key 字段
- `backend/apps/archive/views.py`（M3/M4/M5）：
  - M3：`_sync_detail_rows` 末尾追加聚合 change_entries——统计 details_created/updated/deactivated，生成 DETAIL_SYNC 类型条目（field_changes 存 detail_stats 聚合字典，不逐行创建）；record_id=None、record_key='{源表名} 明细'、version_before/after=None、detail_group/detail_row_key=None/''
  - M4：`ArchiveChangeDetail.bulk_create` 补充 detail_group_id / detail_row_key 字段（从 change_entries dict 取值）
  - M5：新增 rollback_detail action（POST /archives/{id}/rollback-detail/）——接收 detail_fm_id + operated_by；构造同步上下文（_build_code_to_physical + pk_fields + match_channels）→ _query_external_table + _sync_detail_rows 全量覆盖 → 有变更则建 ArchiveChangeBatch + ArchiveChangeDetail（含 DETAIL_SYNC 聚合条目）→ 写 ArchiveOperationLog
- 迁移：archive 0016（archivechangedetail.detail_group + detail_row_key + change_type 扩展），migrate OK
- `backend/apps/archive/tests.py`：新增 3 定向测试（聚合变更条目验证 + 无变更无条目 + 模型扩展字段及 ChangeType）

**状态变更**：批1 明细变更不进 change_entries 限制解除（批2 统一加了 DETAIL_SYNC 聚合日志）。批2 范围边界：回滚=重新同步覆盖（不创建 ArchiveRecordDetailVersion 快照，不逐行回滚）；嵌套表保留行能力仍留活口（批1 边界未动）；前端（明细区变更日志展示 + 回滚按钮）留批3。

**验证**：新增 3 测试全 PASS（DETAIL_SYNC 聚合变更条目/无变更无条目/模型扩展字段及 ChangeType）；回归 archive 51/51 PASS；Django check 0 issues。批2 无新端点真实请求实测（rollback-detail 依赖域 14 配置 detail 关系，留批4 全量同步实测时一并验证）。

**遗留问题**：
- date_format 空值待批4 配置时补（同批1）
- 明细行 20 万级首次全量性能未实测（批4 全量同步时观察）
- 嵌套透传仅一级，嵌套表保留行能力留活口（方向锁定决策）

### 第一百三十四轮（2026-08-10）标签：明细致子表、子表关系、detail分支、行键检测、conditions

**任务**：明细致子表批1（后端核心）实施（task-132 方向锁定 v5 落地，用户放行「这个你先继续做吧」+ 逃生方案：行键配置处加日期配置）。方向判定表：存储模型 触及但已锁定（ArchiveRecordDetail 新存储，方向锁定已确认）/ 模块边界 触及但已锁定（FieldMapping 扩展，用户提案）/ 数据流向、核心交互范式 不触及。

**变更文件**：
- `backend/apps/modeling/models.py`（M1）：FieldMapping 扩展——RelationType(REFERENCE/DETAIL) + row_key_field + display_sort_field + display_sort_desc(默认True) + conditions(JSON 结构化筛选，AND 组合)
- `backend/apps/archive/models.py`（A1）：新增 ArchiveRecordDetail（record/mapping/row_key 三层 unique_together + source_data 整层替换 + manual_data 保留 + data 合并物化 + status 停用标记）
- `backend/apps/archive/views.py`（A7/A2/A3）：
  - `_query_external_table` 新增 conditions 参数 + `_build_conditions_sql`（字段白名单校验 + 值全参数化 + eq/ne/gt/ge/lt/le/in 六操作符 + SQL Server []/Oracle ""/MySQL `` 方言化）
  - `_sync_data_from_sources` 表循环新增 detail 分支：relation_type=DETAIL 的 FieldMapping 优先，整表作为明细致子表同步（跳过直连/中转路径），失败仅记 errors 不阻断他表
  - 新增 `_sync_detail_rows`：行键配置优先否则 `_detect_unique_column` 自动检测并回填配置；嵌套属性一级透传（target_table=本表的 reference 映射，`__nested__{schema_code}` 前缀，同值多行取排序后最后一条）；代表行排序（display_sort DESC/ASC + 行键次级键，空值垫底）复用 `_write_dimension_row` 写主表；明细 upsert（source_data 整层替换 + manual 保留，merged 有差异才 save）；批1 明细变更不进 change_entries（防假明细 BUG-2026-0805-01 教训，批2 扩展 ChangeDetail 时统一加）；明细停用清扫（安全闸门无 errors，500/批标 DELETED）
  - 新增 `_detect_unique_column`：全量行逐列统计（无空值且 COUNT(DISTINCT)==总行数），优先已标主键列，覆盖「FID 标主键但仅 14,883/239,504 唯一」反例
- `backend/apps/modeling/serializers.py`（M2）：FieldMappingSerializer 扩展 8 新字段
- `backend/apps/modeling/views.py`（M3）：FieldMappingViewSet 新增 detect-row-key action（detail=True，复用 ArchiveViewSet._query_external_table + _detect_unique_column）
- 迁移：modeling 0030（fieldmapping 5 新字段）+ archive 0015（archiverecorddetail 建表），migrate OK
- `backend/apps/archive/tests.py`：新增 8 定向测试（ArchiveRecordDetailModelTest 3 + DetailSyncEngineTest 5）

**状态变更**：方向锁定 v5 → 批1 实施完成。批1 范围边界：明细变更日志留批2（ChangeDetail detail_group/detail_row_key + 回滚）；前端 UI 留批3（关系管理配置页 + 明细区折叠分页）；域 14 实际配置 + 全量同步实测留批4（f4 待办：GROUP_* 4 字段 + 计算字段重算 + detail 配置）。

**验证**：新增 8 测试全 PASS（明细创建/代表行写主表/第二轮更新+停用清扫/无法归属跳过/行键检测三反例/conditions SQL 白名单拒绝）；回归 archive+modeling 99/99 PASS；Django check 0 issues。

**遗留问题**：
- date_format 空值待批4 配置时补（用户逃生方案：行键配置处加日期配置；display_sort 不依赖 field_type，字符串比较已够）
- 明细行 20 万级首次全量性能未实测（批4 全量同步时观察）
- 嵌套透传仅一级，嵌套表保留行能力留活口（方向锁定决策）
- 误删 modeling/views.py 两行（# 补充表名和字段名 + from .models import Field, Table）已当场恢复，dev-diary 未记（无实质变更）

### 第一百三十二轮（2026-08-08）标签：/archive/同步、全量同步、去TOP1000、BUG-2026-0808-02

**任务**：用户提出「原架构按星型模型设计，实际是多维模型，档案是宽表还是视图，要结合处理」。诊断结论：档案是 JSON 物化宽表（ArchiveRecord.data/source_data/manual_data 双层存储，读取零 join，同步时物化多维关联结果），既非物理宽表也非视图。真实根因：_query_external_table 每表 TOP 1000 截断 + 各表物理序不一致 → 截断集合分裂（表28↔表22 截断交集 0 → NAME/PRICE 全空假象；表24 与表22 截断批次分裂 → 1334 漂移）。方向判定表：本次为容量策略变更，不触及数据流向/存储模型/模块边界/交互范式四项，仍记录本判定。用户裁决：全量同步（AskUserQuestion 1问/0改向）。

**变更文件**：
- `backend/apps/archive/views.py`：
  - `_query_external_table`：去除 SQL Server TOP/Oracle ROWNUM/MySQL LIMIT 截断，改全量 SELECT + fetchmany(10000) 分批转换（docstring 记录根因）
  - `_query_local_table`：去除 LIMIT 1000
  - `_upsert_records_from_rows` / `_upsert_dimension_via_mapping`：无变化记录收集 no_change_updates 收尾 bulk_update(batch_size=2000)；变更明细瘦身条件 `if reactivated or (changed_codes and existing.id not in created_in_this_batch)`（防首次全量 20 万条重复明细）
  - 停用清扫重写：候选 id 集-差集 matched_ids → stale_ids 按 500/批 id__in 分批（修 BUG-2026-0808-02）；变更日志 data_map 查询同样 500/批分段

**验证结果**：实测全量同步 6/6 表、errors 空、209,123 条（=主表真实行数）、耗时 11 分钟（增量）；MTL_NAME/MTL_CODE 100% 有值、PRICE/UNIT_ID/TO_QTY 24,794（精确命中表28↔表22 全量交集）、NAME 5,322（价目表头 FID→明细→物料中转链）、cardinality_fold_count 12,044 告警正常；变更明细 11,677 条落库（batch#61）；archive 40 测试全 PASS

**遗留问题**：
1. GROUP_NAME/GROUP_ID/GROUP_NO/GROUP_DESC 0 值：表 25/26 字段未挂 StandardField 组合字段（建模配置缺失，非引擎 bug；FieldMapping 25.GROUP_ID→22.MATERIAL_GROUP、25.FID→26.FID 已存在，需在字段属性配置页挂组合字段）
2. 7 个计算字段重算全失败：P_COLOR 等公式引用 `EDS_K3_物料.MNEMONIC_CODE` 物理名，Field.code=MTL_MCODE，既有公式配置错误
3. 首次全量 59.4 分钟（20.9 万条逐条 save+version，一次性成本，后续可优化批量创建）

**状态变更**：同步引擎容量策略从「每表 TOP 1000 截断」改为「全量拉取」（constitution 已追加架构级决策）；无模型变更

### 第一百三十一轮（2026-08-08）标签：/archive/去重值、field-distinct-values

**任务**：新需求——查看档案各字段的去重值（从档案记录实时统计）

**变更文件**：
- `backend/apps/archive/views.py`：ArchiveViewSet 新增 `field_distinct_values` action（GET /archives/{id}/field-distinct-values/），从 ArchiveRecord.data 实时聚合每 schema 字段去重值+计数，每字段最多 200 个值按计数降序
- `frontend/src/api/archive.ts`：新增 `FieldDistinctValue` interface + `archiveApi.fieldDistinctValues(id)` 方法
- `frontend/src/views/archive/ArchiveDetail.vue`：字段导航每项右侧加「值」小按钮（点击弹窗展示该字段去重值，首次加载全量缓存后续零请求）+ 520px 弹窗
- `frontend/src/views/archive/ArchiveList.vue`：无变更（初始放错位置已撤回）

**验证结果**：新端点实测 200（产品档案 1000 条记录、42 字段，数据正确）；回归 40/40 PASS；vue-tsc 0 errors

**状态变更**：新增功能，无状态变更

### 第一百三十轮（2026-08-08）标签：BUG-2026-0808-01 档案同步 0 记录修复

**涉及模块**：modeling、archive

**变更文件**：
- `backend/apps/modeling/models.py`：Field 新增 `physical_name` 字段
- `backend/apps/modeling/migrations/0029_add_physical_name_to_field.py`：迁移 + 存量回填 physical_name=name
- `backend/apps/modeling/views.py`：数据源导入创建字段时设 physical_name=col_name
- `backend/apps/modeling/excel_service.py`：Excel 导入创建字段时设 physical_name=col_code
- `backend/apps/archive/views.py`：_build_code_to_physical 改用 physical_name + solo 字段映射按 f.code 匹配 schema code + pk_fields 改用 schema code

**变更摘要**：
- 根因三层叠加：① rename_solo 改名后 Field.code 变了，原始列名丢失；② _build_code_to_physical solo 循环用 phys_code in schema_type_map 匹配不上；③ pk_fields 用 Field.code 而非 schema code，record_data 取不到主键值
- 修复：Field 新增 physical_name 字段保留原始列名，同步改用 physical_name，pk_fields 改用 schema code
- 产品域档案同步从 0 恢复到 1000 条

**状态**：完成

### 第一百零八轮（2026-08-05）标签：紧急修复 3 项（配置检查范围 + 警告不阻断 + 同步关键 Bug）

**涉及模块**：archive

**修改文件**：
- `backend/apps/modeling/views.py`：_check_domain_config 中“字段编码与名称有区分”检查范围从所有活跃字段缩小为 `archive_category='base'` 的档案字段
- `backend/apps/archive/views.py`：①`_validate_primary_fields` 从硬拦截改为警告（_sync_data_from_sources + _preview_data_changes 两处移除 return stats，改为 stats['warnings']）；②`_upsert_records_from_rows` 修复 sync_exclude_codes 排除主键字段导致跨表数据无法匹配写入的关键 Bug（主键字段即使在排除集合中也保留用于记录匹配）；③3 处 stats 初始化加 `warnings: []`
- `frontend/src/views/archive/ArchiveDetail.vue`：showConsistencyWarning 从 Modal.confirm 改为 notification.warning（非阻断右上角通知，8 秒自动消失）；doRefreshData/doSyncSchema 增加 warnings 展示
- `frontend/src/views/archive/ArchiveList.vue`：预检弹窗增加 warnings 黄色提醒条
- `frontend/src/types/index.ts`：SyncStats 接口加 `warnings?: string[]`

**验证结果**：45 测试 PASS，vue-tsc 0 errors。实际同步验证：records_updated 从 0 恢复到 2194，GZT0001 从 15 字段恢复到 23 字段（CLOSE_REASON/D_CLOSE_DATE/CUST_NO 等全部写入）

### 第一百零七轮（2026-08-04）标签：测试报告反馈 3 项修正

**涉及模块**：archive、modeling

**修改文件**：
- `backend/apps/modeling/views.py`：StandardFieldViewSet 新增 `rename_solo` action（独立字段改名，级联更新 schema/records/consistency）
- `frontend/src/api/modeling.ts`：standardFieldApi 新增 `renameSolo` 方法
- `frontend/src/views/modeling/DomainFieldConfig.vue`：改名按钮从组合字段表移到属性配置 Tab（支持 equiv+solo 两种 kind）；组合字段表操作列移除改名
- `frontend/src/views/modeling/DomainList.vue`：配置检查按钮从操作列移入配置状态标签（可点击 tag + tooltip）；操作列宽 360→280
- `frontend/src/views/archive/ConsistencyCheck.vue`：完全重写为分组设计——4 个检查类型统计卡片（点击展开/收起）+ 展开后按日期分组 + 日期组可折叠

**验证结果**：45 测试 PASS，vue-tsc 0 errors

### 第一百零六轮（2026-08-04）标签：测试报告 3 项（域检查 + 改名 + 一致性大改）

**涉及模块**：archive、modeling

**修改文件**：
- `backend/apps/archive/models.py`：ConsistencyIssue 新增 CheckType 枚举（4 种）、check_type/check_rule_key/detail 字段；新增 ConsistencyCheckRule 模型；唯一约束加 check_type
- `backend/apps/archive/migrations/0013_consistencycheckrule_and_more.py`：新建迁移
- `backend/apps/archive/serializers.py`：ConsistencyIssueSerializer 加 check_type/check_rule_key/detail 字段；新增 ConsistencyCheckRuleSerializer
- `backend/apps/archive/views.py`：consistency_check 扩展 4 种检查类型（composite_member/archive_source_diff/orphan_source_record/schema_drift）+ 失效规则过滤；新增 ConsistencyCheckRuleViewSet（list/toggle/disable/enable）；ConsistencyIssueViewSet 加 check_type 筛选
- `backend/apps/archive/urls.py`：注册 consistency-rules 路由
- `backend/apps/modeling/views.py`：_check_domain_config 8 项检查 + DomainViewSet.check_config + perform_update P0 前置拦截 + StandardFieldViewSet.rename 级联改名
- `frontend/src/views/modeling/DomainList.vue`：配置状态列 + 启用/停用开关 + 配置检查弹窗
- `frontend/src/views/modeling/DomainFieldConfig.vue`：组合字段改名按钮 + 改名弹窗
- `frontend/src/views/archive/ConsistencyCheck.vue`：全面重写——4 种检查类型筛选/渲染 + 失效规则管理抽屉 + 规则失效弹窗
- `frontend/src/api/archive.ts`：新增 consistencyRuleApi（list/disable/enable/toggle/delete）
- `frontend/src/api/modeling.ts`：domainApi 加 patch/checkConfig；standardFieldApi 加 rename
- `frontend/src/types/index.ts`：ConsistencyIssue 加 check_type/check_type_display/check_rule_key/detail；新增 ConsistencyCheckRule/CheckType 类型

**验证结果**：45 测试 PASS，vue-tsc 0 errors

### 第一百一十轮（2026-08-05）标签：/archive/记录变更历史、同步引擎

**任务**：用户反馈变更历史面板同一秒、同一记录的同批字段出现重复"修改"明细（清空+回填配对），排查根因并修复 + 清理存量污染。

**读取/排查**：
- dev.db 实证：档案9 record#11574（GZT0001）batch#48 中两条明细 v4→5 清空三字段、v5→6 写回原值；batch#48 全批 1522 条明细 = 761 清空 + 761 回填，全部假变更
- D_CHECK_DATE/N_AREA/STORE_VERSION 同时存在于表19（有值）和表20（全 null），code_to_physical 映射只挂表19（先到者独占）；Table ordering=['-created_at'] 使表20 先于表19 处理

**根因**：`_upsert_records_from_rows` 行级兜底 `if col_name in schema_type_map` 让未映射给本表的同名空列偷渡写入 → 表20 先清空（假变更①）→ 表19 再写回（假变更②），每轮刷新必现。同类排查发现 `_preview_data_changes` 存在同构漏洞。

**修改文件**：
- `backend/apps/archive/views.py`：两处同名兜底收紧为仅主键列（保跨表记录匹配）——写入侧 _upsert_records_from_rows、预检侧 _preview_data_changes
- `backend/apps/archive/tests.py`：新增 SyncFieldNameLeakTest 回归测试（mock _query_local_table 注入辅表同名空列，断言不清空/不 bump 版本/不建批次）
- `backend/scripts/cleanup_fake_sync_changes.py`：新建存量清理脚本（默认 dry-run），已 --apply 执行

**验证结果**：archive 套件 19/19 PASS；清理删假明细 1522 + 假快照 1522 + 空批次 [48]，重编号 761 条记录；修复后对档案9 只读预检 would_create/update/deactivate 全 0；record#11574 版本链归位 [1,2,3,4]

**状态变更**：BUG-2026-0805-01 已闭环（代码修复 + 回归测试 + 存量清理），登记 debug-diary-archive / constitution / route_index

**遗留问题**：域配置层可对“多表同名未归并字段”给显式告警（待用户决策）

### 第一百一十四轮（2026-08-05）标签：/archive/api-management、REQ-005、API Key 鉴权、设计

**涉及模块**：archive（纯设计，零代码变更）

**任务**：用户要求“设计一下 API 管理的部分”。首轮 AskUserQuestion 被用户取消并提醒补读 reqa 需求文档（幻觉闸门生效：未读需求文档就出方案属猜测）；补读后定位 REQ-005「接口开放与权限配置」（F-204 API接口配置 + F-205 API密钥管理，归属 auth 模块待启动）与现状差距：无密钥/无真实端点/无文档/无限流/仅读。

**方向锁定**（两轮 AskUserQuestion 共 5 问，用户全选推荐项零改向）：①完整落地 REQ-005 API 部分；②推翻宪法 2026-07-23「真实鉴权留待 auth 模块」——本期自建 API Key 真实鉴权；③读写全设计（守 Hub 宪法永不回写源表，写落 manual_data/软停用）；④独立密钥×多 API 授权（ApiKeyGrant）；⑤调用日志落库 90 天+近 7 天统计。

**产出**：
- `output/darc/design-diary-archive.md`：v19 完整设计（方向锁定/设计原则/业务流程/数据模型 ApiKey+ApiKeyGrant+ApiCallLog+ArchiveApi 扩展/对外网关契约 /api/open/{slug}/ 读写六端点+拦截链 401→403→429/管理端密钥端点/前端双 Tab 交互/方向承载点清单/实施顺序/验收标准）
- `.ai/constitution.md`：架构级新增「API管理完整落地 REQ-005(v19)」决策；旧「API开放权限」决策移入历史区并注推翻
- `.ai/route_index.md`：archive 待办「ArchiveApi 鉴权强化」更新为已出 v19 设计待编码

**状态变更**：无（纯设计轮）；下一步待用户发令按 v19 实施顺序编码（①模型迁移→⑦daemon 清理）

**遗留问题**：无

### 第一百一十五轮（2026-08-05）标签：/archive/api-management、字段释放粒度、补登记

**涉及模块**：archive（纯文档登记，零代码变更）

**任务**：用户关注「API 配置能否配置不同字段释放给不同的 API，要增加这个」。基于代码事实核实：该能力已存在（ArchiveApi.exposed_fields 挂每个 API 独立，前端抽屉分组勾选，v19 网关读投影/写限 exposed∩archive）；AskUserQuestion 确认用户选「现状已够，补登记即可」，不引入读写分离字段清单/密钥级字段再收窄。

**修改文件**：
- `output/darc/design-diary-archive.md`：v19 设计原则区补「字段释放粒度=每 API 独立」条目（含两层释放衔接说明）
- `.ai/constitution.md`：「API管理完整落地 REQ-005(v19)」决策行尾追加字段释放粒度句

**状态变更**：无；设计待编码状态不变

### 第一百一十七轮（2026-08-05）标签：/archive/api-management、v19 编码落地、REQ-005

**涉及模块**：archive（编码轮；uxqa 设计评审关已先行下发 7 条开发约束）

**任务**：v19 REQ-005 API 管理全栈编码实施（延续第一百一十四轮设计），按实施顺序 ①模型迁移→⑦daemon 完成，本轮收尾测试+留痕。

**修改文件**：
- `backend/apps/archive/models.py`：ApiKey/ApiKeyGrant/ApiCallLog 新模型 + ArchiveApi 扩展 slug/allowed_operations/rate_limit_per_min + ChangeSource.API（迁移0014）
- `backend/apps/archive/open_api_auth.py`（新建137行，方向承载点）：鉴权链 401/授权 403/限流 429/日志/90天清理
- `backend/apps/archive/open_api_gateway.py`（新建388行，方向承载点）：网关六端点 + build_docs；PATCH 复用 ArchiveRecordUpdateSerializer（批次 change_source=api），POST 主键落 source_data+可写字段落 manual_data
- `backend/apps/archive/serializers.py`：批次解析提前+ArchiveApiSerializer 扩展（自动 slug）+密钥三序列化器
- `backend/apps/archive/views.py`：ApiKeyViewSet（CRUD/rotate/revoke/call-logs）+api_call_stats+docs action
- `backend/apps/archive/urls.py`：api-keys/api-call-stats/open 网关路由
- `backend/apps/archive/apps.py`：修复重复类定义存量 Bug（daemon 从未启动）+90天日志清理并入循环
- `backend/apps/archive/tests.py`：新增 19 条用例（OpenApiGatewayTest 13 + ApiKeyManagementTest 6）
- 前端：ApiManagement.vue 重写双 Tab+文档抽屉（680行）；新建 components/ApiKeyTab.vue（391行）；api/archive.ts + types 扩展
- 留痕：dev-diary-archive v19 实施条目、route_index 状态/文件索引/Bug 行、REUSE_CATALOG 回填 3 工具、ux-review-archive v19 评审关

**验证结果**：archive 37/37 PASS；archive+modeling 定向回归 54/54 PASS；vue-tsc 0 errors；真实请求实测 18/18 PASS（管理端 CRUD+docs/密钥明文一次/网关 401×2/投影/写拒 400×2/越权 403/日志统计/轮换/吊销），实测残留已清理、脚本已删

**状态变更**：v19 从「待编码」→「已交付」（uxqa 交付验收关通过）

**uxqa 交付验收**：四维核查全 ✅；checklist 21/21 ✅（A1-A3/A9/B1-B2/C2/C7-C9/D1/D7-D8/E4/F1/F3/G1/G4/H1/I1/J2）；发现 P2 R-054（密钥表 scroll.x=1100 偏小）→ 已修复为 1300 并闭环；浏览器实跑 0 error / 网络 3 请求全 200 / Tab 深链验证通过

### 第一百一十八轮（2026-08-05）标签：/archive/api-management、测试报告、只读、测试接口

**任务**：测试报告 3 项修复：①API 管理页改只读；②修复暴露字段 checkbox-group 跨分组清空 bug；③新增测试接口功能

**修改文件**：
- `frontend/src/views/archive/ApiManagement.vue`：
  - 移除「新建」按钮（行 27）
  - 操作列只保留「数据」「文档」「测试」（移除编辑/删除/启停用）
  - API 名称从可点击链接改为纯文本
  - 移除整个编辑抽屉模板（120 行）+ 相关函数/状态变量（250 行）
  - 修复 checkbox-group bug：改独立 checkbox + `toggleField` 函数手动管理数组
  - 新增测试接口 Modal（URL 展示/API Key 输入/发送请求/响应展示）
  - 清理未使用 import（Empty/Modal/ArchiveSchemaItem/ApiFilterCondition）

**验证结果**：vue-tsc 0 errors；回归 104/104 PASS

**状态变更**：API 管理页从「可编辑」→「只读」+ 新增测试功能

### 第一百二十轮（2026-08-05）标签：/archive、权限全景、只读审计、API 聚合

**任务**：新需求「档案管理增加权限功能菜单，一站式看档案配了什么 API/释放字段/调用系统/角色/用户/字段授权」；质问闸门 3 问锁定：入口=档案列表操作列、仅管理员、只读+跳转配置

**修改文件**：
- `backend/apps/archive/views.py`：ArchiveViewSet 新增 `permission_overview` action（83 行）：IsMdmAdmin 403；聚合机器权限（ArchiveApi+ApiKeyGrant+ApiCallLog 按密钥聚合调用统计）+人用权限（RoleFieldPermission+角色用户）；零新模型
- `backend/apps/archive/tests.py`：新增 PermissionOverviewTest 3 用例（结构全断言/非管理员 403/空档案 200）
- `backend/smoke_permission_overview.py`：新建实测脚本 7 项断言
- `frontend/src/views/archive/components/PermissionOverview.vue`：新建 203 行抽屉组件（960px 两区块+去配置跳转）
- `frontend/src/views/archive/ArchiveList.vue`：操作列「权限」链接（v-if isAdmin，getMeApi 判定）+抽屉挂载
- `frontend/src/api/archive.ts`、`frontend/src/types/index.ts`：permissionOverview API + 3 接口

**验证结果**：定向回归 40/40 PASS；vue-tsc 0 errors；实测 7/7 PASS（admin 档案 9 200+结构齐、probe_user 403）；Browser 验证 admin 抽屉两区块数据正确+probe_user 无入口+console 零报错

**环境操作**：实测前重启后端（旧进程未加载新 action）；杀进程前 netstat 确认端口状态（沿用上轮双进程教训），taskkill 需提权

**状态变更**：新增「权限全景」只读审计视图，archive 待 uxqa 验收

### 第一百二十二轮（2026-08-06）标签：/archive/versions、菜单高亮、变更日志

**背景**：用户反馈“明明是变更日志功能，为什么菜单跳到档案管理”——变更日志明细页（/archive/versions?domain=11）左侧高亮「档案管理」而非「变更日志」。方向判定表：不触及数据流向/存储模型/模块边界/核心交互范式（纯前端展示层路由联动）。

**路由**：prjm Bug 流程 → code review 定位根因 → 同类全排查+复发核查 → 方案对比 AskUserQuestion（用户选治本）→ darc 修复。

**根因**：MainLayout.vue 高亮白名单 allMenuKeys 手动维护，/archive/versions（变更日志明细页，无独立菜单项）漏登记，最长前缀匹配落入 /archive。同类排查：全部子路由仅此一错（/archive/:id 等档案下钻命中档案管理属合理）；复发核查：与 R-013 同属菜单高亮类第二次但根因不同。

**修改文件**：frontend/src/layouts/MainLayout.vue 单文件——①collectMenuKeys 递归从 menuItems 提取路径 key（替代手动白名单）②MENU_ALIAS_PREFIX 下钻页别名表（/archive/versions → /archive/domain-changes）③watchEffect 移到 menuItems computed 声明之后（TDZ 修复）

**二次缺陷拦截**：首版修复把 watchEffect 留在 menuItems 声明之前，首次同步执行 TDZ 全站白屏；Browser 实测第一轮发现，移后解决。vue-tsc 无法检出此类运行时 TDZ。

**验证**：vue-tsc 0 errors；Browser 子代理 5 页实测（变更日志×2/档案管理/域管理/API管理）DOM 检测 ant-menu-item-selected 5/5 符合期望，控制台零 error；截图工具故障未留图，结论靠 DOM class 确定性核验

**状态变更**：debug-diary-archive 新增 BUG-2026-0806-01；constitution 已知问题表+route_index Bug 表已登记；archive 待 uxqa 验收


### 第123轮（2026-08-06）标签：/archive/记录启停、/settings/roles、uxqa整改、R-055、R-058

- 读取文件：rectification-list.md 第118轮整改区段、ArchiveDetail.vue（doToggleStatus/开关绑定/既有 Modal.confirm 风格）、RoleManagement.vue、apps/auth/views.py perform_destroy、apps/auth/models.py（CASCADE 关系）、frontend/package.json
- 修改文件：ArchiveDetail.vue（doToggleStatus 包 Modal.confirm）、RoleManagement.vue（import Modal + 模板改 a 链接 + 新增 confirmDelete）
- 变更摘要：R-055 档案记录启停无确认（全站唯一无防护危险点）→ Modal.confirm 二次确认（停用=danger/启用=primary）；R-058 删除角色 popconfirm → Modal.confirm（不可逆删除防护与全站对齐）
- 方向判定表（rule §11）：数据流向不触及（纯前端交互层）/存储模型不触及（零后端改动）/模块边界不触及（archive/auth 内部）/核心交互范式=执行已锁定决策（constitution 三维选型+第118轮拍板），非新方向 → 无需 §11.1 循环
- 验证：vue-tsc -b 0 errors；Browser 子代理实测 2/2 PASS（启停弹窗出现+取消回弹+列表不刷新；删角色弹窗出现+取消角色仍在）；console 0 error
- 状态变更：rectification-list R-055/R-058 → ✅ 已闭环；整改单剩余 R-056/R-057/R-059/R-060/R-061/R-062 六项 ⏳ 待整改
- 遗留问题：剩余六项整改待后续轮次派单（R-056 记录详情转抽屉为下一候选）；archive/auth 仍待 uxqa 交付验收关

### 第120轮（2026-08-05）下沉：档案权限全景只读审计视图

档案列表操作列「权限」链接（仅管理员）→ 960px 抽屉两区块（机器权限：API/暴露字段/授权密钥/按密钥聚合调用统计；人用权限：角色×域字段白名单/用户），区块头「去配置」跳既有配置页；后端 GET /archives/{id}/permission-overview/（IsMdmAdmin 403，零新模型聚合 v19+REQ-019 数据）；新增用例 3 条 40/40 PASS + 实测 7/7 + 浏览器验证全过

### 第124轮（2026-08-06）标签：/archive/记录详情、R-056、弹窗转抽屉、uxqa整改

- 读取文件：rectification-list.md 第118轮整改区段、ArchiveDetail.vue（detailModal 全量+openDetailDrawer+schemaGridStyle）、全站 a-drawer 档位扫描（760/900/960/1000）、frontend/package.json
- 修改文件：ArchiveDetail.vue（detailModal 容器 a-modal→a-drawer 1100px；底部关闭/暂存修改按钮移入 #footer slot 固定底栏）
- 变更摘要：R-056 记录详情 1400px modal → 1100px 大抽屉（右侧滑入不遮记录列表可边看边改；暂存编辑/变更预览/分组网格全保留；状态变量名 detailModal 与 openDetailDrawer 未动，调用方零影响；沿用全站既有 a-drawer 骨架无新组件）
- 方向判定表（rule §11）：数据流向不触及（纯前端容器形态）/存储模型不触及（零后端改动）/模块边界不触及（archive 内部）/核心交互范式=执行已锁定决策（第118轮三维选型拍板+本轮用户确认 5 批计划），非新方向 → 无需 §11.1 循环
- 验证：vue-tsc -b 0 errors；Browser 子代理实测 6/6 PASS（右侧滑入 ant-drawer 宽 1100px 无 ant-modal/元信息+26 字段齐全/footer 固定底栏/暂存修改初禁用改字段后启用+1 字段变更预览/关闭后列表完好/console 0 error）
- 状态变更：rectification-list R-056 → ✅ 已闭环；整改进度 3/8，剩余 R-057/R-059/R-060/R-061/R-062 五项 ⏳
- 遗留问题：批2=R-057 变更历史抽屉收敛（ArchiveDetail+VersionManagement 两处同构弹窗收敛为单组件）；archive/auth 仍待 uxqa 交付验收关

### 第125轮（2026-08-06）标签：/archive/变更历史、R-057、组件收敛、uxqa整改

- 读取文件：rectification-list.md 第118轮整改区段、ArchiveDetail.vue（historyModal + 回滚相关十函数 + openDetailDrawer 死预载）、VersionManagement.vue（historyModal + loadHistory + openHistory/openHistoryFromRecord）、ChangeDetail 类型定义、全站 a-drawer 档位
- 修改文件：components/ChangeHistoryDrawer.vue（新建 201 行）、ArchiveDetail.vue（5 对替换）、VersionManagement.vue（5 对替换）
- 变更摘要：R-057 变更历史两处同构拷贝收敛为 ChangeHistoryDrawer 单组件（900px 抽屉 + a-timeline + 双粒度回滚 dropdown）；props open/recordId/title/enableRollback 区分 AD 带回滚 / VM 只读；加载口径统一 VM 全量分页、色映射取 AD 完整版；AD 侧附带清理 121 行死预载代码（详情内回滚面板遗留）
- 方向判定表（rule §11）：数据流向不触及（纯前端组件收敛）/存储模型不触及（零后端改动）/模块边界不触及（archive 内部）/核心交互范式=执行已锁定决策（第118轮三维选型拍板 + 清单原文「收敛为单组件复用」）→ 无需 §11.1 循环
- 验证：vue-tsc -b --force 0 errors；Browser 子代理实测 8 项全 PASS（AD 侧 900px 抽屉/时间线 12 条含版本映射/双粒度回滚 dropdown/关闭重开重载/随记录切换；VM 侧同款只读回滚按钮数=0/记录详情弹窗内转历史）；console 0 error（截图受自动化浏览器渲染帧限制未留存，DOM/Network 证据链完整）
- 状态变更：rectification-list R-057 → ✅ 已闭环；整改进度 4/8，剩余 R-059/R-060/R-061/R-062 四项 ⏳
- 遗留问题：批3 = R-062 刷新预检收敛（ArchiveList + ArchiveDetail 两处同构弹窗收敛单组件）；archive/auth 仍待 uxqa 交付验收

### 第126轮（2026-08-06）标签：/archive/刷新预检、R-062、组件收敛、uxqa整改

- 读取文件：rectification-list.md 第118轮整改区段、ArchiveList.vue 全量（刷新预检弹窗 L41-126 + doRefreshPreview/confirmRefresh）、ArchiveDetail.vue 刷新预检区段（L256-343 + refreshData/doRefreshPreview/confirmRefresh/showConsistencyWarning）、components 目录现状
- 修改文件：components/RefreshPreviewModal.vue（新建 115 行）、ArchiveList.vue（切片替换 L41-126 + import + stats 文案泛化）、ArchiveDetail.vue（切片替换 L256-343 + import）
- 变更摘要：R-062 刷新预检两处同构弹窗收敛为 RefreshPreviewModal 单组件（760px modal，props open/previewData/archiveName，emit confirm）；职责边界：组件只管展示+确认意图，执行逻辑留父组件（两处刷新对象不同）；AL stats 文案顺带泛化（补复活文案+同步/刷新动词区分，R-048/R-049 同类分叉补齐）
- 方向判定表（rule §11）：数据流向不触及（纯前端组件抽取）/存储模型不触及（零后端改动）/模块边界不触及（archive 内部）/核心交互范式=执行已锁定决策（第118轮三维选型拍板 + R-062 清单原文「收敛为单组件」）→ 无需 §11.1 循环
- 验证：vue-tsc -b --force 0 errors；Browser 子代理实测 6 项 PASS——无变化分支 toast+不弹窗；schema 变化分支（子代理主动注入建模变化 SF#27 触发：弹窗 760px 带档案名标题、取消零 POST、确认 sync-schema 200 + 列表版本 2→3）；详情页按钮 loading+同款弹窗+确认后记录表重载；DOM 单实例无残留；console 0 error；注入测试后数据复原（截图受 hidden-tab 渲染冻结未留存，DOM/Network 证据链完整）
- 状态变更：rectification-list R-062 → ✅ 已闭环；整改进度 5/8，剩余 R-059/R-060/R-061 三项 ⏳
- 遗留问题：批4 = R-059 字段管理近全屏 modal → 大抽屉 + R-061 window.prompt 改 Modal 表单；archive/auth 仍待 uxqa 交付验收

### 第一百三十六轮（2026-08-10）标签：明细致子表批3a+3b、前端、关系管理配置、明细展示、变更日志、detail_sync

**任务**：明细致子表批3a+3b（前端）实施。方向判定表：四项不触及（纯前端扩展 + 后端简单查询 action，不涉及数据流向/存储模型/模块边界/核心交互范式变更）。

**变更文件**：

**批3a（关系管理配置页）**：
- `frontend/src/types/index.ts`：FieldMapping 扩展——relation_type/row_key_field/display_sort_field/display_sort_desc/conditions
- `frontend/src/api/modeling.ts`：fieldMappingApi 新增 `update` (PATCH) + `detectRowKey` 方法
- `frontend/src/views/modeling/DomainFieldMapping.vue`：
  - 模板：映射表格加「关系类型」列（明细子表蓝标签/引用灰标签）；编辑弹窗加关系类型 select（reference/detail）+ detail 配置区（行键字段 select+检测按钮/代表行排序字段 select/排序方向 switch/筛选条件 JSON 输入）
  - Script：form 扩展 detail 字段、`detectingRowKey` ref、`openCreate/openEdit` 回填 detail 字段、`handleSubmit` 创建后 PATCH 更新 detail 配置（引用类型清除遗留配置）、`detectRowKey()` 调用后端 /detect-row-key/ 自动匹配、`onRelationTypeChange()` 切换引用时清空 detail 字段

**批3b（明细展示 + 变更日志）**：
- `backend/apps/archive/serializers.py`：新增 `ArchiveRecordDetailRowSerializer`（ArchiveRecordDetail 模型序列化器，含 mapping_name）
- `backend/apps/archive/views.py`：ArchiveRecordViewSet 新增 `@action(detail=True, methods=['get'], url_path='details')` → `GET /records/{id}/details/` 返回明细行列表
- `frontend/src/api/archive.ts`：archiveRecordApi 新增 `listDetails(id)` 方法
- `frontend/src/views/archive/ArchiveDetail.vue`：操作列新增「明细」按钮 + 900px 明细子表行 drawer（行键/数据/状态/更新时间列，数据字段以 JSON 键值对展示）+ 状态变量 + loadDetailRows 函数
- `frontend/src/views/archive/components/ChangeHistoryDrawer.vue`：时间线新增 `detail_sync` 类型聚合条目展示（新增/更新/移除行数统计）+ 普通明细行展示关联 detail_group/detail_row_key 信息；timelineColor/changeTypeColor/canRollbackDetail 均扩展 `detail_sync` 类型
- `frontend/src/types/index.ts`：FieldChange 扩展 `detail_stats?: { created: number; updated: number; deactivated: number }`

**验证**：vue-tsc 0 errors；后端序列化器导入验证通过。无新测试用例（明细展示为纯前端展示，后端 endpoint 为简单查询，已有记录列表测试覆盖）。

**遗留问题**：
- 域 14 实际配置 detail 关系 + 全量同步实测留批4
- 明细行 20 万级首次全量性能待实测（批4 全量同步时观察）

### （续上轮 2026-08-08）标签：DB诊断脚本合并

**任务**：用户反馈 3 个 DB 检查脚本（check_db_contents / check_db_storage / check_db_field_sizes）设计杂乱，合并优化。

**问题清单**：
1. 三个脚本割裂，Django setup 重复 3 次
2. 矛盾结论：check_db_contents 只看 data 字段（828 字符）结论有误，check_db_field_sizes 才发现 schema 字段（73KB）才是真凶
3. 无统计分布：100 条采样不给中位数/百分位
4. 代码 Bug：`avg_ver_per_rec = ver_cnt / ver_cnt`（自除恒为1）、`pragm_page_count` 拼写错误、MB 换算写错
5. 只列症状不开药方

**变更**：
- 删除 `scripts/check_db_contents.py`
- 删除 `scripts/check_db_storage.py`
- 删除 `scripts/check_db_field_sizes.py`
- 新建 `scripts/check_db_diagnostics.py`（三合一）
  - 字段大小分布：原生 SQL 不走 ORM deserialize，2000 行随机抽样，输出均值/中位数/P90/P95/P99/最大
  - 存储分析：优先 dbstat 虚拟表精确页统计，fallback 近似估算
  - 版本分布直方图（对数分桶），极端记录 TOP5 追溯
  - schema 非空占比检查（反映回填进度）
  - 综合诊断 + 推荐操作步骤

**验证**：import 通过。

**回执**：闸✓ 记✓ 拓✓ 测✓（无新增路径）

### 第一百六十二轮（2026-08-14）标签：预组合过滤、inner join、筛选条件、kept预扫、row_filter、桥接挂载、FULL_PARENT_ID、eq明码实价

**任务**：用户反馈「预组合表设置了筛选条件 + inner join，同步结果数据量未收敛」，贴期望 SQL（价目明细 NAME LIKE 明码实价 INNER JOIN 物料 INNER JOIN 分组 FULL_PARENT_ID LIKE '.101041%'）。

**方向锁定**：constitution 决策块 + adqa 回执行（质✓5条/伪✓/锁✓确认5暂定0否决0）；用户拍板：主记录要过滤；cfg6 PARENT_ID→FULL_PARENT_ID（用户自认配置错）；数据量口径按配置 eq；服务器 data_dump 暂缓只改本机。

**变更文件**：
- `backend/apps/archive/views.py`（7 改动点）：`_split_conditions` 新（conditions 按 field_source 拆 header/detail，header 透传 `_join_header_rows`——原 header 字段不在明细表白名单 → ValueError 整表跳过 = 筛选静默失效根因）；`_build_precombine_filters` 新（129 行，inner detail 挂载预扫 kept_keys 主键值集合，多挂载交集 → row_filter）；`_upsert_records_from_rows` 加 row_filter 行级过滤（不进 seen_keys/不 upsert/不创建，防 stale 复活死循环）；`_join_header_rows` 加 conditions 透传；`_sync_detail_rows` 异名挂载补洞 + target_code 标准字段解析 + existing_records 桥接索引
- `backend/apps/archive/tests.py`：PrecombineFilterSyncTest 7 条 + DetailSyncHeteronymMountTest 3 条（含新增 test_bridge_mount_when_key_not_in_schema）；fake_query 补 PCM_MAIN 分支
- `backend/dev.db`：cfg2 conditions 改 eq「明码实价」；cfg6 conditions 改 FULL_PARENT_ID starts_with .101041

**首跑未生效根因链（探针定位）**：① target_code 用挂载字段 code（MATERIAL_ID/MATERIAL_GROUP）非 schema code（MTL_ID）→ code_to_physical 解析 None；② 预扫 phys_cols 依赖 code_to_physical → 全空 → kept 空 → 过滤静默跳过。修复：kept 改**明细行 source_field 物理列行内取值**（src_values），主记录侧按「同域直取（tf_phys==target 表主键）or 桥接 target_field.table（{主键值→挂载键值}）」收敛为主键值集合；`_sync_detail_rows` target_code 走 standard_field.standard_code 优先；挂载键不在 schema → 桥接建 {主键值→挂载键值} 索引。

**数据事实（域 2）**：eq 新明码实价 838 物料（7 位 ID）全不在物料表（209,123 行 6 位 ID）→ 与分组交集 0；eq 明码实价 955（6 位 ID 全在 .101041 组）→ 用户确认改 eq 明码实价。

**验证**：实跑同步（12 分钟）records_updated=955、records_deactivated=208,168、details_created=117,549、tables_synced=6、errors=[]——主记录 209,123→955 精确命中用户 SQL 口径；新测试 10/10 + archive 全套 70/70 PASS。

**遗留问题**：
1. existing_records 遍历全部记录（含将停用 stale）→ 分组头明细挂到 116,594 个将停用记录上（details_created 117,549 中约 116,594 属此类）；active 记录（955）明细正常；如需只挂 active 后续单独处理
2. 服务器 data_dump.json 配置暂缓（用户裁决），服务器 cfg2/cfg6 条件发布时需同步
3. 物料分组未配置代表行排序字段（既有 warning）

**回执**：闸✓ 记✓ 拓✓ 测✓（新测试 10 条 + 实跑 955 验证）
