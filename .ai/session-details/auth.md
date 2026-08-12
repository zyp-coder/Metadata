# 会话详情 — auth（权限管理）

### 第一百十六轮（2026-08-05）标签：系统管理、角色配置、字段可见可编辑、REQ-019

**背景**：用户提出「系统管理功能：配置角色，不同角色可以看到档案列表的不同字段，怎么设计」。

**路由**：prjm 质问闸门（必要性+可行性）→ 用户锁定方案A 一次性完整 auth（不走分期）+ 内置账号密码登录；命中六阶段全流程（auth 新建模块）→ reqa 执行。

**澄清锁定（AskUserQuestion 两轮）**：
- 实施路径：方案A 一次性完整 auth（登录+用户+角色+字段权限一步到位）
- 权限维度：字段可见性 + **可编辑性**（用户第二轮主动追加「除了控制可见性，还有可编辑性」）
- 配置粒度：角色×档案域（每域单独配字段集）
- 默认规则：白名单制——角色在某域未配置到的字段默认隐藏
- 生效范围：档案列表列+记录详情+编辑（变更日志与对外 API 本期不叠加，v19 对外已有 exposed 控制）
- 用户管理：完整（新建/禁用/重置密码/分配角色，内置 admin 不可删）

**关键事实查证**：
- 后端零登录零鉴权（全库 grep authentication/login/IsAuthenticated = 0），前端无登录页——字段权限的前提「知道当前是谁」缺失，必须先建登录体系
- auth 模块现状仅展示占位（ArchiveApi.auth_roles JSONField），宪法决策「实际授权待 auth 模块单独决定」
- 功能清单 F-201/F-202/F-203 早已登记但从未落地；REQ-005 场景2（角色权限）+ BR-014（档案级粒度）为需求根基；v19 API Key 是对外机器鉴权，与人用角色权限平行不冲突

**产出（纯设计零代码）**：
- requirements.json：REQ-019（5 场景 9 条验收标准 + BR-019-1~8 业务规则）
- concept-feature-list.md：F-201~F-203 描述具体化（含 F-202 原「增删改查权限分配」由字段级粒度承接），新增 F-209 登录与会话、F-210 字段权限过滤层（双份表格同步更新）
- storylines/REQ-019.md：轻量故事线（多角色旅程：管理员配置+普通用户使用）
- business-flow.md：流程六（登录与字段权限过滤 mermaid）+ 异常路径 3 行（401 重定向/伪造写入忽略/零配置空列提示）
- concept-architecture.md：auth 模块职责/边界/对外接口/依赖更新（双版本）+ 实现路径图 auth 行（P0 开发中）+ 追溯矩阵 REQ-019 行 + 覆盖检查 11/11/41 + 关键设计决策「权限模型」行更新为字段级白名单
- route_index.md：auth 模块状态「设计中」，待 uxqa 设计评审→darc 编码

**遗留/下一步**：用户确认本设计后 → uxqa 设计评审关（下发开发约束）→ darc 编码（新建 apps/auth 或扩展、Token 认证方案由 darc 在复用扫描中定，不擅自引入新依赖）。

---

### 第一百十六轮（2026-08-05 续）标签：REQ-019、编码落地、全栈

**路由**：用户确认「确认设计，进评审+编码」→ uxqa 设计评审产出 C1-C15 开发约束（ux-review-auth.md）→ 用户确认「确认，开始编码」→ darc 编码（闸门 16:28 写入）。

**读取/修改文件**：
- 后端新建：apps/auth/{models,permission,serializers,views,urls,admin,apps,tests}.py + init_admin 命令 + migrations/0001_initial.py
- 后端修改：config/settings.py（全局鉴权）、config/urls.py、apps/archive/serializers.py（三处投影+写投影+updated_by 兜底）、apps/archive/tests.py 与 apps/modeling/tests.py（auth_client() helper 适配）
- 前端新建：views/auth/Login.vue、views/settings/UserManagement.vue、views/settings/RoleManagement.vue、api/auth.ts
- 前端修改：api/index.ts（401 拦截单点）、router/index.ts（守卫+/settings 路由）、layouts/MainLayout.vue（用户区+菜单 is_admin 可见）、views/archive/ArchiveDetail.vue（editable 只读）、types/index.ts
- 文档：dev-diary-auth.md 新建、design-diary-auth.md 快照刷新（user=None 系统级豁免）、REUSE_CATALOG 回写 4 行、route_index 状态改可交付+方向承载点登记

**变更摘要**：
- 编码中发现并修复 6 项：①开放网关写回归（user=None 被零配置拦截→单点豁免，v19 测试暴露）②RoleManagement 保存语义冲突（整体覆盖需回传全部域配置）③权限抽屉字段源改拉档案详情④Token 无 id⑤非管理员菜单隐藏+loadUser 重置⑥last_login 手动维护
- dev.db admin 密码与预期不符→shell 重置（浏览器实测阻塞项）

**验证**：新增 32 用例；回归 104/104 PASS；smoke_auth.py 真实请求实测 19/19 PASS；Browser 子代理浏览器实测两轮（admin 管理页+probe_user 字段过滤）全过，控制台无应用级 error；vue-tsc 0 errors

**状态变更**：auth 模块 设计中→可交付（待 uxqa 交付验收）；probe_user/Probe@12345 实测账号留库

**遗留**：无阻塞；uxqa 交付验收关待用户发令

### 第一百一十九轮（2026-08-05）标签：/settings/roles、测试反馈、可编辑限制、ownership

**读取**：测试问题报告（1 项 /settings/roles）、RoleManagement.vue、apps/auth/views.py、apps/archive/serializers.py（ownership 拦截）、types/index.ts、auth tests.py

**修改文件**：
- frontend/src/views/settings/RoleManagement.vue：可编辑复选框对 ownership='source' 字段置灰+tooltip；表格上方提示行；onDomainChange 加载历史配置时剔除误存 source 字段
- backend/apps/auth/views.py：PUT permissions 新增 ownership 校验（按域查首个 Archive.schema，editable 含 source 字段 → 400）
- backend/apps/auth/tests.py：+1 用例 test_permissions_put_rejects_source_owned_editable（共 33）
- backend/smoke_src_owned.py：新增真实请求实测脚本（幂等清理残留临时角色）

**验证**：test apps.auth 33/33 PASS；vue-tsc 0 errors；实测 9/9（PUT 含 CUST_NO→400+文案，仅 LIAISON→200）；Browser 子代理验证门店域 24/25 置灰+tooltip+可见列不受影响

**环境事件**：实测首两轮假 200——8000 端口双进程同时 LISTENING（旧 runserver 未杀干净），netstat 定位后 taskkill 双 PID 重启解除；教训写入 dev-diary/debug-diary

**状态变更**：debug-diary-auth.md 新建（BUG-2026-0805-02）；route_index 补拓扑边 auth←archive（archive 序列化层依赖 permission.py）；constitution 追加交互级决策行

**遗留**：无阻塞；auth 仍待 uxqa 交付验收关

### 第一百二十一轮（2026-08-06）标签：admin 密码统一、冒烟测试专用账号、存量清理

**背景**：用户发现 admin 密码多处不一致永远猜不中；系统里看到 smoke 脚本留下的奇怪数据（实测角色/probe_user），要求建专用测试账号。

**路由**：prjm 读上下文→影响分析→AskUserQuestion 三决策（管理命令初始化/单独密码/清理存量）→ darc 编码。此前几轮纯问答已把 admin 密码全项目统一为 admin123456（init_admin 默认值+三 smoke 脚本+dev.db 重置+docker-compose 补 init_admin）。

**读取**：init_admin.py、permission.py（user_is_admin 口径）、smoke 三脚本、design/dev-diary-auth.md、REUSE_CATALOG.md

**修改文件**：
- 新增 backend/apps/auth/management/commands/init_test_account.py（幂等建 smoke_test，MDM_TEST_PASSWORD 环境变量默认 test23456，挂内置管理员角色，与 init_admin 同模式）
- backend/smoke_auth.py：admin→smoke_test（TEST_USER 常量）+密码 test23456
- backend/smoke_permission_overview.py、backend/smoke_src_owned.py：同切 smoke_test/test23456；后者顺手修正硬编码计数 /7→/9
- backend/docker-compose.yml：启动链补 init_test_account（migrate→init_admin→init_test_account→runserver）
- output/darc/REUSE_CATALOG.md：登记两个初始化命令（smoke 脚本禁止用 admin）

**状态变更**：dev.db 新建 smoke_test；ORM 删除 probe_user（含 token/profile）与「实测角色」（含域 11 权限配置）；「敏彤」角色（真实用户配置）与 admin 未动

**验证**：smoke_auth 19/19 PASS（smoke_test is_admin=True 全链路）；smoke_src_owned 9/9；smoke_permission_overview 7 passed 0 failed；证据写 dev-diary-auth

**遗留**：脚本仍会产出 probe_user/实测角色（UserViewSet 无 DELETE 端点，无法 API 自清理），但可辨识挂在 smoke_test 名下，需清理时走 ORM；auth 仍待 uxqa 交付验收关
