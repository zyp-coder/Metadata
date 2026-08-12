"""字段权限过滤单点（方向承载点，见 design-diary-auth.md）。

REQ-019：角色×档案域字段可见/可编辑白名单。
- get_field_permission 返回 (visible, editable)：None 表示不过滤（管理员），集合表示白名单
- filter_schema / filter_record_data / filter_writable_data 为三个投影函数
推翻该方向 = 替换本文件 + 摘除 archive 序列化层 3 处调用。
"""


def user_is_admin(user):
    """superuser 或持有内置管理员角色 → 全量权限。"""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'profile', None)
    if profile is None:
        return False
    return profile.roles.filter(is_builtin=True).exists()


def get_field_permission(user, domain_id):
    """返回 (visible_codes: set|None, editable_codes: set|None)。

    - user=None：系统级调用（开放网关复用/脚本，无请求上下文）→ (None, None) 不过滤；
      用户可达端点均有全局 IsAuthenticated，user 必为真实用户实例
    - 管理员（superuser/内置角色）→ (None, None)，调用方不过滤
    - 普通用户：多角色配置取并集（BR-019-5）；某域零配置 → 空集（全隐藏，白名单语义）
    - 无 profile 的已登录用户按零配置处理（全隐藏）
    """
    if user is None:
        return None, None
    if user_is_admin(user):
        return None, None
    profile = getattr(user, 'profile', None)
    if profile is None:
        return set(), set()
    perms = profile.roles.values_list(
        'field_permissions__domain_id',
        'field_permissions__visible_codes',
        'field_permissions__editable_codes',
    ).filter(field_permissions__domain_id=domain_id)
    visible, editable = set(), set()
    for _domain_id, v_codes, e_codes in perms:
        visible.update(v_codes or [])
        editable.update(e_codes or [])
    return visible, editable


def filter_schema(schema_items, visible, editable):
    """schema 投影：仅保留可见字段，并为每项附 editable 标记（前端编辑只读依据）。"""
    if visible is None:
        return [{**item, 'editable': True} for item in (schema_items or [])]
    editable = editable or set()
    result = []
    for item in schema_items or []:
        code = item.get('code')
        if code in visible:
            result.append({**item, 'editable': code in editable})
    return result


def filter_record_data(data, visible):
    """记录值投影：隐藏字段数据不下发（BR-019-6）。"""
    if visible is None:
        return data
    return {k: v for k, v in (data or {}).items() if k in visible}


def filter_writable_data(data, editable):
    """写投影：不可编辑字段静默丢弃（不报错，BR-019-6）。"""
    if editable is None:
        return data
    return {k: v for k, v in (data or {}).items() if k in editable}
