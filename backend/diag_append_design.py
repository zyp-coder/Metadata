# 以 UTF-8 字节追加 darc 设计日记（design-diary-modeling.md 为混合编码，头部 UTF-8）
content = """

---

## 2026-08-11 明细致子表交互改造「先注册后挂载」设计

### 需求背景

用户反馈「关系管理有建立明细子表功能，但明细子表怎么和主表建关系？没有操作空间」。根因：FieldMapping 方向反直觉（source_table=明细子表→target_table=主表，与用户直觉相反）+ 新建映射弹窗必须先选主表才能配 detail（无独立注册空间）。方向锁定见 constitution「明细致子表交互改造（2026-08-11）」决策块（7 条清单全确认 + adqa 硬回执 质[✓5] 伪[✓探针] 锁[✓5/留1/否0]）。

### 数据模型

**新模型 DetailTableConfig（子表注册，modeling/models.py）**

| 字段 | 类型 | 说明 |
|------|------|------|
| domain | FK Domain | 所属域 |
| table | FK Table | 明细子表（域内） |
| row_key_field | FK Field null | 行键列（如 ENTRY_ID） |
| display_sort_field | FK Field null | 代表行排序字段（如 EFFECTIVE_DATE） |
| display_sort_desc | Boolean default True | 排序方向 |
| conditions | JSONField default [] | 筛选条件（结构化 AND） |
| created_at / updated_at | DateTime | 时间戳 |

- Meta：unique_together=(domain, table)，一域一表仅一个注册
- 允许不选主表独立保存（注册阶段无主表概念，实现「先注册后挂载」）

**FieldMapping 扩展（modeling/models.py）**
- 新增 detail_config FK→DetailTableConfig（SET_NULL，null/blank True）：挂载关联（一子表注册可被多 FieldMapping 挂载）
- 原 detail 配置字段（row_key_field/display_sort_field/display_sort_desc/conditions）保留标记 deprecated（§8 禁止删除），新建不再直接填；同步引擎优先读 detail_config，无则回退读 fm 自身（存量兼容）

### API 契约

**DetailTableConfigViewSet（modeling/views.py）**
| 接口 | 方法/路径 | 说明 |
|------|-----------|------|
| 列表 | GET /api/field-mappings/detail-configs/?domain=X | 含表名/行键名/排序名 |
| 注册 | POST /api/field-mappings/detail-configs/ | domain/table 必填，其余可选；重复注册 400 |
| 修改 | PATCH /api/field-mappings/detail-configs/{id}/ | 改行键/排序/条件 |
| 删除 | DELETE /api/field-mappings/detail-configs/{id}/ | 有挂载 400 拒绝（防静默断链） |
| 行键检测 | POST /api/field-mappings/detail-configs/{id}/detect-row-key/ | 复用 _detect_unique_column |

**FieldMappingViewSet 扩展**
- FieldMappingSerializer 加 detail_config（id 读写 + 名称只读展示）
- 校验（create/update）：relation_type=detail 时必填 detail_config（挂载必须选已注册子表）；target_field 必须为目标表主键字段（挂载必须选关联字段）；detail_config.table 必须等于 source_table（防错挂）
- 新 action GET /api/field-mappings/detail-check/?domain=X：存量检测返回 {registered:[], unregistered:[{id, source_table, target_table, reason}], suspect:[]}——detail 映射未注册 → reason='未注册子表配置'；detail 映射的 source_table 无映射到档案主键的物理列 → reason='方向可能反了（明细表无法归属主记录）'（探针实证 id=25 即此类）

### 同步引擎改造（archive/views.py 主循环 1280-1302 detail 分支）

1. 查该表 DetailTableConfig（domain+table）
2. 有注册 → 查挂载它的 detail FieldMapping 列表（filter(detail_config=cfg, source_field active)）→ 循环 _sync_detail_rows（一子表多挂载）
3. 无注册 → 存量兼容：查 relation_type=detail 的 FieldMapping（读 fm 自身 detail 字段），存在则 warning 提示「未注册子表配置」+ 仍按旧逻辑同步（过渡期不破坏）
4. _sync_detail_rows 内部：detail_fm.row_key_field/display_sort_field/conditions 取值优先 detail_config，回退 fm 自身

### 前端改造（DomainFieldMapping.vue 单文件）

1. 「子表注册」弹窗（新入口，页顶按钮+区块）：选域内表+行键（检测按钮）/排序/条件 → 保存 DetailTableConfig（不选主表）
2. 新建映射弹窗改造：关系类型=detail 时——源表下拉=已注册子表（无注册时 Alert 引导先去注册）；目标表=主表；源字段=关联字段必选；目标字段=主表主键必选；原行键/排序/条件配置区移除（移入注册弹窗）
3. 列表 detail 行显示「挂载: 子表名」标签
4. 存量检测：onMounted 调 detail-check → 异常 Alert 提示（含 id=25 方向可疑）

### 存量迁移

- migration RunPython（幂等）：现有 detail 映射（id=23）自动创建 DetailTableConfig（复制 row_key/display_sort/conditions），FieldMapping.detail_config 指向之
- id=25 方向异常不自动改，仅检测提示（用户裁决：检测能力做好，修正由用户界面操作或后续脚本）

### 方向承载点（§11.2：推翻「先注册后挂载」需动文件清单）

1. backend/apps/modeling/models.py — DetailTableConfig 类 + FieldMapping.detail_config（新增）
2. backend/apps/modeling/views.py — DetailTableConfigViewSet + detail-check action（单点）
3. backend/apps/archive/views.py — 主循环 detail 分支 + _sync_detail_rows 取值点（单点函数段）
4. frontend/src/views/modeling/DomainFieldMapping.vue — 前端两区块（单文件）

验收标准：推翻 = 删除/替换上述单点 + 改挂载逻辑开关，不跨栈删行。

### 测试计划

- 新用例：DetailTableConfig CRUD/重复注册 400/有挂载删除 400；挂载校验（detail 必填 detail_config、target_field 必须主键、table 一致）；一子表多挂载同步两条 mapping 均产出；未注册兼容 warning；detail-check 检测 id=25 方向可疑
- 实测：detail-configs 端点 POST/GET/PATCH 真实请求；域 14 detail-check 返回 suspect 含 id=25
"""
with open(r'd:\AIproject\MetaData002\output\darc\design-diary-modeling.md', 'ab') as f:
    f.write(content.encode('utf-8'))
print('design diary appended OK')
