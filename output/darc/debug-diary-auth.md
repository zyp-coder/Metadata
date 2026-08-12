# Debug 日记 — auth（权限管理）

> 快照区见 design-diary-auth.md。本文件记录问题与修复（只追加）。

## BUG-2026-0805-02：权限抽屉「可编辑」可勾选源系统维护字段（测试反馈）

- **现象**：/settings/roles 权限配置抽屉中，ownership='source'（源系统维护、档案侧只读）的字段也能被勾选「可编辑」。该配置无效且误导：用户实际编辑记录时会被记录更新的 ownership 拦截拒绝，不知所以。
- **RCA**：`RoleManagement.vue` 可编辑复选框 disabled 条件仅 `!visibleCodes.has(code)`，未考虑字段 ownership；后端 `PUT /roles/{id}/permissions/` 仅校验 editable⊆visible，无 ownership 校验。同类排查（grep ownership 口径）：ArchiveDetail.vue disabled 与 smoke_auth 候选口径均已正确，仅权限抽屉一处漏口径——孤立点非模式。
- **修复方案（用户确认·双层防护）**：
  1. 前端：source 字段可编辑复选框置灰 + tooltip「源系统维护，档案侧不可人工编辑」+ 表格上方提示行 + 加载历史配置时剔除误存的 source 字段（`RoleManagement.vue`）
  2. 后端：PUT permissions 按域查首个 Archive 的 schema，editable_codes 含 source 字段 → 400（`apps/auth/views.py`，与记录更新 ownership 拦截同口径）
  3. 新增测试用例 `test_permissions_put_rejects_source_owned_editable`
- **影响范围**：仅配置入口；运行时过滤单点 permission.py 与档案三处投影不受影响。
- **验证**：test apps.auth 33/33；smoke_src_owned.py 9/9；浏览器实测 24/25 置灰正确。
- **教训**：① 凡「可编辑/可写」语义的入口都必须与 ownership 口径对齐，配置端与执行端同规则；② 实测发现假 200 时先查端口是否多进程监听（本次 8000 端口双进程，旧进程处理请求导致新校验未生效）。
