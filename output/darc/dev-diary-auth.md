# 开发日记 — auth（权限管理）

> 快照区见 design-diary-auth.md。本文件记录编码与验证过程（只追加）。

## 2026-08-05 第一百十六轮：REQ-019 全栈编码落地

### 交付内容

**后端（apps/auth 新模块，app_label=mdm_auth）**
- models.py：Role / RoleFieldPermission（unique role×domain，save 时 clean 校验 editable⊆visible）/ UserProfile
- permission.py：**过滤单点（方向承载点）**——get_field_permission + 三投影函数（filter_schema/filter_record_data/filter_writable_data）
- serializers.py：Role/User/UserCreate/RoleFieldPermission 序列化器
- views.py：LoginView（统一 401 文案）/LogoutView/MeView/UserViewSet（无 DELETE，405）/RoleViewSet（内置与有用户角色禁删，permissions action GET/PUT 整体覆盖）
- management/commands/init_admin.py：幂等初始化内置管理员角色+admin（密码走 MDM_ADMIN_PASSWORD 环境变量，C14）
- 迁移：mdm_auth.0001_initial + authtoken.0001

**全局鉴权（config/settings.py）**
- INSTALLED_APPS += rest_framework.authtoken / apps.auth
- DEFAULT_AUTHENTICATION_CLASSES=Token+Session；DEFAULT_PERMISSION_CLASSES=IsAuthenticated（登录接口 AllowAny 豁免；v19 开放网关自带免登录配置不受影响）

**archive 三处投影接入（serializers.py）**
- ArchiveDetailSerializer.get_schema：权限投影+editable 标记
- ArchiveRecordList/DetailSerializer.get_data：隐藏字段不下发
- ArchiveRecordUpdateSerializer.update：写投影——不可编辑字段静默还原旧值（在 ownership 拦截之前）；updated_by 登录态兜底

**前端**
- Login.vue（全屏独立页 C2）/ router 守卫（无 token → /login）/ api/index.ts 401 拦截单点（C5）
- MainLayout：当前用户+登出；「权限管理」菜单组仅 is_admin 可见（后端另有 403）
- settings/UserManagement.vue（新建640 Modal/重置密码480/禁用启用/编辑改显示名与角色，无删除）
- settings/RoleManagement.vue（权限配置抽屉 760px，域选择+字段勾选表；保存按整体覆盖语义回传全部域配置）
- ArchiveDetail.vue：编辑控件 :disabled 追加 field.editable === false（两处渲染块）
- types：ArchiveSchemaItem.editable?: boolean

### 编码中发现并修复的问题（6 项）

1. **开放网关写回归**：网关复用 UpdateSerializer 时无请求上下文，user=None 被按零配置全隐藏 → PATCH 写入被静默还原（v19 测试 test_patch_archive_field_writes_manual_layer 失败暴露）。修复收敛到单点：get_field_permission 对 user=None（系统级调用）返回 (None, None) 不过滤；用户可达端点均有全局 IsAuthenticated，user 必为真实用户实例
2. **RoleManagement 保存语义冲突**：前端只提交当前域，后端 PUT 整体覆盖会误删其他域配置 → 改为加载全部域配置快照，保存时其他域原样回传+当前域替换（全清空=移除该行收回授权）
3. **权限抽屉字段来源错误**：列表接口不含 schema → 改拉档案详情（archiveApi.get）取字段集
4. **Token 无 id 属性**：测试断言改用 key
5. **非管理员菜单可见性**：权限管理菜单组按 is_admin 隐藏；loadUser 先重置 currentUser 防账号切换时菜单残留
6. **最近登录恒为空**：Token 登录不走 django login()，LoginView 手动维护 last_login

### 验证证据

**测试**：新增 apps/auth/tests.py 32 用例（登录体系 7 / 用户管理 6 / 角色管理 6 / 权限单点 6 / 档案三处投影端到端 7）；全量回归 `test apps.modeling apps.archive apps.auth` **104/104 PASS**（既有 72 条含 auth_client superuser 适配，断言零改动）

**真实请求实测**（smoke_auth.py，19/19 PASS，关键证据）：
- 未登录 /auth/me/ 与 /archives/ → 401
- admin 登录 200+token（is_admin=True）；错误密码与不存在账号统一 401「用户名或密码错误」
- 建角色 201 → 配权限 PUT 200（visible=['CUST_NO','CUST_NAME','LIAISON'] editable=['LIAISON']）→ editable⊄visible 400
- probe_user 登录 → GET 档案详情 schema 投影恰为 3 字段且 editable 标记 {CUST_NO:False, CUST_NAME:False, LIAISON:True}
- GET 记录列表 data 键仅 3 个可见字段（隐藏字段不下发）
- PATCH 伪造改 CUST_NO → 200 但值未变（GFWS201921 静默还原）；改 LIAISON → 成功写入
- 有用户角色删除 400；普通用户访问 /users/ 403；登出后 token 即失效 401
- last_login 登录后有值（admin/probe_user 实测确认）

**浏览器实测**（Browser 子代理两轮，localhost:3004）：
- 登录守卫/错误文案/登录跳转 ✅；用户管理、角色管理列表 ✅（内置角色删除置灰）
- 权限抽屉 760px，门店域 25 字段勾选表加载正常，已配置勾选回显 ✅
- probe_user 档案详情列仅 3 业务列；详情弹窗 CUST_NO/CUST_NAME disabled、LIAISON 可编辑 ✅
- probe_user 菜单无「权限管理」组；直访 /settings/users 后端 403+toast ✅
- 控制台无应用级 error ✅

### 运维要点

- 首次部署需跑 `python manage.py init_admin`（MDM_ADMIN_PASSWORD 环境变量；本机开发 admin 密码 Admin@12345）
- dev.db 中 admin 密码曾与预期不符，已用 shell 重置（浏览器实测阻塞项，已解除）
- probe_user / Probe@12345 为实测账号（挂「实测角色」，门店域 3 字段可见）

### 遗留

- 无阻塞遗留。uxqa 交付验收关待用户发令。

## 2026-08-05 第一百一十九轮：测试反馈修复——「可编辑」配置限制为档案侧维护字段

### 问题（测试报告）

/settings/roles 权限抽屉中，源系统维护字段（ownership='source'）也能被勾选「可编辑」——此类字段档案侧只读（记录更新的 ownership 拦截会拒绝人工修改），配置无效且误导。

### 修复（双层防护，用户确认方案）

1. **前端 RoleManagement.vue**：可编辑复选框对 ownership='source' 字段置灰 + tooltip「源系统维护，档案侧不可人工编辑」；表格上方灰色提示行；onDomainChange 加载历史配置时剔除可能误存的 source 字段
2. **后端 apps/auth/views.py PUT permissions**：新增 ownership 校验——按域查首个 Archive 的 schema，editable_codes 含 ownership='source' 字段 → 400「域 X：字段 Y 由源系统维护，不可配置为可编辑」（与记录更新的 ownership 拦截同口径；域无档案/schema 空时跳过校验）
3. **测试**：apps/auth/tests.py 新增 test_permissions_put_rejects_source_owned_editable（400 拦截 + 仅 archive 字段通过），共 33 用例

### 验证证据

- 定向回归：test apps.auth **33/33 PASS**；vue-tsc 0 errors
- 真实请求实测（smoke_src_owned.py，9/9 PASS）：PUT 含 CUST_NO（source）→ 400+文案；仅 LIAISON（archive）→ 200 且保存正确；临时角色已清理
- 浏览器实测（Browser 子代理）：门店域 25 字段中 24 个可编辑复选框置灰（仅 LIAISON 可勾）、tooltip 文案正确、可见列 25/25 不受影响、提示行存在，未保存任何变更

### 环境教训

- **8000 端口曾双进程同时 LISTENING**（旧 runserver 未杀干净，新进程也绑上，请求被旧进程处理导致实测假 200）——重启服务前必须 netstat 确认端口清空；smoke 脚本需幂等（清理上次中断残留的临时角色）

## 2026-08-06 admin 密码统一 + 冒烟测试专用账号

### 背景（用户反馈）

1. admin 密码多处不一致：init_admin 默认 admin23456、三个 smoke 脚本写 Admin@12345、日记曾记 admin123——用户永远猜不到当前有效密码
2. smoke 脚本用 admin 账号跑，测试垃圾数据（实测角色/probe_user）挂在系统里被用户误认为异常数据

### 变更

1. **admin 密码统一为 admin123456**：init_admin.py 默认值 + 三个 smoke 脚本 + dev.db 存量（shell set_password 重置）；实测登录 200+token 确认
2. **新增 management/commands/init_test_account.py**：幂等创建冒烟测试专用账号 smoke_test（默认密码 test23456，环境变量 MDM_TEST_PASSWORD 可覆盖），挂内置管理员角色（脚本需建角色/建用户/配权限）；与 init_admin 同模式
3. **三个 smoke 脚本改用 smoke_test/test23456**：smoke_auth.py（TEST_USER 常量）/smoke_permission_overview.py/smoke_src_owned.py；smoke_src_owned.py 顺手修正硬编码计数 /7→/9（实际 9 项检查）
4. **docker-compose.yml 启动链补两命令**：migrate → init_admin → init_test_account → runserver（原先容器重建后 admin 从不自建）
5. **存量清理（用户确认）**：ORM 删除 probe_user（含 token/profile）与「实测角色」（含域 11 权限配置）；「敏彤」角色（真实用户配置）与 admin 未动

### 验证证据

- smoke_auth.py 实测 **19/19 PASS**（smoke_test 登录 is_admin=True → 建角色/配权限/投影/写投影/删除拦截全链路）
- smoke_src_owned.py 实测 **9/9 PASS**（source 字段拦截 400+文案，临时角色自清理）
- smoke_permission_overview.py 实测 **7 passed 0 failed**（权限全景聚合正常，敏彤角色在 roles 区可见）

### 运维要点更新

- admin 密码：admin123456（本机 dev.db 已重置；生产走 MDM_ADMIN_PASSWORD 环境变量）
- smoke 测试账号：smoke_test / test23456（MDM_TEST_PASSWORD 可覆盖）
- 脚本仍会产出 probe_user/实测角色（UserViewSet 无 DELETE 端点，脚本无法 API 自清理），但全部可辨识挂在 smoke_test 名下；需清理时走 ORM


## 2026-08-06 | 第一百二十三轮：uxqa 整改 R-058 删除角色 popconfirm→Modal.confirm

### 前端（views/settings/RoleManagement.vue）

- 模板：`a-popconfirm` 包裹 → 红色 `a` 链接 @click=confirmDelete（v-if !is_builtin 保留，内置角色仍灰色禁用文字）
- 新增 `confirmDelete`：Modal.confirm（title 确认删除该角色 / content 含角色名+不可恢复+字段可见可编辑配置一并清除+后端拦截说明 / okText 确认删除 / okType danger），onOk 返回 handleDelete 复用既有删除逻辑
- import 补 Modal（原仅 message）
- 影响文案依据后端事实（apps/auth/views.py perform_destroy：内置角色不可删；角色下有用户 → 400 提示先调整；RoleFieldPermission FK CASCADE 随角色删除）
- 与全站删除防护口径对齐（R-052/R-053 同类整改已闭环先例）

### 验证

- vue-tsc -b 0 errors
- 浏览器实测 PASS：非内置角色「实测角色」点删除 → 红色危险确认弹窗出现 → 取消后角色仍在列表（全程未点确认删除）；console 0 error
