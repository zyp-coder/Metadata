# 设计日记 — auth（权限管理）

# 快照区（模块最新整体态，可覆盖刷新）

## 模块定位

REQ-019 落地：登录会话 + 用户/角色管理 + 角色×档案域字段可见/可编辑控制（白名单制）。
权限在后端序列化层强制执行（数据不下发），非前端展示级。

## 数据模型

| 模型 | 字段 | 说明 |
|------|------|------|
| Role | name(unique)/description/is_builtin | 内置管理员角色 is_builtin=True 不可删 |
| RoleFieldPermission | role FK / domain FK / visible_codes JSON[] / editable_codes JSON[] | unique(role,domain)；白名单语义：不在列表=隐藏/不可编辑；editable 必为 visible 子集（保存时约束） |
| UserProfile | user OneToOne(auth.User) / display_name / roles M2M(Role) | 多角色权限取并集；User.is_active 控制禁用 |

认证：DRF TokenAuthentication（rest_framework.authtoken，无新依赖）；前端 Authorization: Token xxx。

## 过滤单点（方向承载点，推翻时只动这里+调用处）

`apps/auth/permission.py`：
- `get_field_permission(user, domain_id) -> (visible: set|None, editable: set|None)`
  - user=None（系统级调用：开放网关复用/脚本，无请求上下文）→ (None, None) 不过滤；用户可达端点均有全局 IsAuthenticated，user 必为真实用户
  - superuser/内置管理员角色 → (None, None) 表示不过滤
  - 多角色并集；零配置/无 profile → (set(), set()) 全隐藏
- `filter_schema(schema_items, visible, editable)` → schema 投影并附 editable 标记
- `filter_record_data(data, visible)` → 记录值投影
- `filter_writable_data(data, editable)` → 写投影（静默丢弃不可编辑字段）

调用点（3 处）：ArchiveDetailSerializer/ArchiveListSerializer 的 schema 输出、ArchiveRecord list/detail 的 data 输出、ArchiveRecord update/partial_update 写入前。

## API 契约（/api/auth/ 前缀）

| 端点 | 方法 | 说明 | 鉴权 |
|------|------|------|------|
| /api/auth/login/ | POST {username,password} | → {token, user:{username,display_name,is_admin,roles[]}}；失败统一「用户名或密码错误」 | AllowAny |
| /api/auth/logout/ | POST | 删 token | Token |
| /api/auth/me/ | GET | 当前用户信息 | Token |
| /api/auth/users/ | GET/POST | 用户列表（含角色/状态/最近登录）/新建 | 仅管理员 |
| /api/auth/users/{id}/ | PATCH | 改显示名/角色/禁用（is_active） | 仅管理员 |
| /api/auth/users/{id}/reset-password/ | POST {password} | 重置密码 | 仅管理员 |
| /api/auth/roles/ | GET/POST | 角色列表（含用户数/已配置域数）/新建 | 仅管理员 |
| /api/auth/roles/{id}/ | PATCH/DELETE | 编辑/删除（有用户或内置→400 拦截） | 仅管理员 |
| /api/auth/roles/{id}/permissions/ | GET/PUT | 按域读写字段权限配置 | 仅管理员 |

全局：DEFAULT_PERMISSION_CLASSES=IsAuthenticated；豁免仅 /api/auth/login/（+admin/static）。
档案接口无签名变化——过滤在序列化层透明执行；schema 项新增 editable 布尔（前端编辑只读依据）。

## 前端

- /login 全屏卡片表单（不走 MainLayout）；router 守卫：无 token→/login
- api/index.ts：请求注入 Token；401→清 token+重定向 /login（单点）
- MainLayout 右上：当前用户 + 登出
- /settings/users：用户表格+新建/编辑 Modal 中640+重置密码 Modal 小480+禁用 popconfirm
- /settings/roles：角色表格+新建/编辑 Modal 小480+权限配置抽屉 760px（域切换+AI分组+可见/可编辑双 Checkbox+分组全选）
- 档案页零改动（schema 驱动自然收缩；editable=false 字段编辑只读）

## 初始化

init_admin 管理命令：创建内置管理员角色+admin 用户（密码环境变量 MDM_ADMIN_PASSWORD，默认 admin123456 仅开发用）。
init_test_account 管理命令：创建冒烟测试专用账号 smoke_test（密码环境变量 MDM_TEST_PASSWORD，默认 test23456），挂内置管理员角色；三个 smoke 脚本统一用它登录，测试垃圾数据不挂 admin 名下。Docker 启动链：migrate → init_admin → init_test_account → runserver。

# 变更记录区（只追加）

## 2026-08-05 初版设计（REQ-019 编码启动）

- 依据：requirements.json REQ-019、ux-review-auth.md（C1-C15 开发约束）、concept-feature-list F-201~F-203/F-209/F-210
- 决策：TokenAuthentication（DRF 内置，零新依赖）；app 目录 apps/auth、label=mdm_auth（避开 django.contrib.auth 的 auth label 冲突）；operated_by 改从 request.user.username 取（保留 request.data 兼容）
- 方向承载点登记：权限过滤逻辑收敛 apps/auth/permission.py 单文件，推翻方向=替换该文件+摘除 3 处调用（符合 rule §11.2）
