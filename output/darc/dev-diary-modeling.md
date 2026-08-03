# 开发日记 - 主数据建模引擎（modeling）

> 记录 modeling 模块开发过程中的关键实现决策和技术细节。

---

## 2026-07-25 计算字段功能全栈实现（REQ-017，第三十五轮）

### 变更背景

实现 REQ-017「计算字段配置与自动计算」完整功能，包含10个子任务：模型扩展、公式引擎、计算服务、后端API、档案集成、前端API+组件+视图增强。

### 关键实现决策

#### 公式引擎架构（递归下降解析器）

自定义词法分析器(Lexer) + 递归下降语法分析器(Parser) + AST求值器(Evaluator)：
- **Lexer**：分词 NUMBER/STRING/FIELD_REF/FUNC_NAME/OP/COMMA/LPAREN/RPAREN/EOF
- **Parser**：expression → comparison → additive → multiplicative → unary → primary，优先级正确
- **字段引用**：`{表名.字段名}` 语法，正则 `\{([^.}]+)\.([^}]+)\}`
- **内置函数**：IF/CONCAT/LEFT/RIGHT/LEN/UPPER/LOWER/TRIM/ROUND/ABS/MAX/MIN/SUM/AVG/COUNT/NOW/TODAY/YEAR/MONTH/DAY/IFERROR/SWITCH/IFS/VLOOKUP/SUMIFS/COUNTIFS/MAXIFS/MINIFS

```python
# formula_engine.py 核心结构
class Lexer:   # 分词器
class Parser:  # 递归下降 AST 构建
class Evaluator:  # AST 求值 + 字段上下文注入
def parse_references(expression):  # 从表达式提取所有 {表.字段} 引用
def validate_formula(expression, available_fields):  # 语法+引用合法性校验
def evaluate_formula(expression, field_values):  # 完整执行
```

#### DAG 依赖管理

- **拓扑排序**：Kahn's algorithm 确定 execution_order
- **循环检测**：DFS 三色染色法（白/灰/黑），灰→灰即循环
- **依赖解析**：保存时自动解析 parsed_references → 挂靠 depends_on(M2M→Field) + depends_on_computed(M2M→self)

```python
# computed_service.py
def resolve_dependencies(domain_id):  # 全域拓扑排序+执行顺序写入
def detect_cycle(domain_id, new_cf_id, new_depends_on_computed_ids):  # 含假设节点的循环检测
def batch_recalculate(domain_id):  # 按拓扑序全量重算所有 active 档案记录
def recalculate_affected(domain_id, record_id, changed_field_codes):  # 单记录受影响字段实时重算
```

#### 双触发重算策略

1. **sync-schema 后批量**：`archive/views.py` 数据拉取完成后调 `batch_recalculate(domain.id)`
2. **记录编辑实时**：`archive/serializers.py` ArchiveRecordUpdateSerializer.update() 中调 `recalculate_affected()`，失败不阻塞保存

#### 枚举试算（笛卡尔积）

后端 `trial_calculate` action：
- 从 `field.distinct_values` 自动填充参数候选
- 生成笛卡尔积（上限1000组合）
- 逐组求值返回 `{params, result, error}` 列表

#### 前端组件架构

- **FormulaEditor.vue**（268行）：公式编辑器 modal，含 code/name/output_type 表单 + formula textarea 实时验证 + 函数面板 + 字段引用选择器 + 光标插入
- **TrialCalculation.vue**（246行）：枚举试算 modal，含参数表格 + 自动枚举/手动参数 + 结果表格
- **DomainFieldConfig.vue 增强**：计算字段视图增加工具栏（新建/依赖图/批量重算） + 表格列增强（公式摘要/输出类型/执行顺序/操作按钮）

### 模型变更

```python
# ComputedField 新增字段（migration 0020 已含骨架，本轮扩展）
class ComputedField(models.Model):
    depends_on = models.ManyToManyField('Field', blank=True)  # 物理字段依赖
    depends_on_computed = models.ManyToManyField('self', symmetrical=False, blank=True)  # 计算字段间依赖
    parsed_references = models.JSONField(default=list)  # [{table, field}]
    execution_order = models.IntegerField(default=0)  # 拓扑序
    output_type = models.CharField(max_length=20, default='text')  # text/number/date/boolean
```

### 新增文件

| 文件 | 职责 |
|------|------|
| `backend/apps/modeling/formula_engine.py` | 公式解析+求值引擎（Lexer/Parser/Evaluator） |
| `backend/apps/modeling/computed_service.py` | 依赖解析/循环检测/批量重算/实时重算 |
| `frontend/src/views/modeling/components/FormulaEditor.vue` | 公式编辑器组件 |
| `frontend/src/views/modeling/components/TrialCalculation.vue` | 枚举试算组件 |

### 影响范围

| 文件 | 变更类型 |
|------|----------|
| `backend/apps/modeling/models.py` | Edit: ComputedField 扩展 5 个字段 |
| `backend/apps/modeling/views.py` | Edit: ComputedFieldViewSet +6 actions |
| `backend/apps/modeling/serializers.py` | Edit: ComputedFieldSerializer 扩展 |
| `backend/apps/archive/views.py` | Edit: schema含计算字段 + sync后重算 |
| `backend/apps/archive/serializers.py` | Edit: 记录保存时触发实时重算 |
| `frontend/src/api/modeling.ts` | Edit: +6接口+6方法 |
| `frontend/src/views/modeling/DomainFieldConfig.vue` | Edit: 计算字段视图增强 |

### 验证

- **Django check**：0 issues
- **vue-tsc**：0 errors（修复1个 TS7053 隐式 any 类型错误）
- **Migration**：0020 已含 ComputedField 骨架，扩展字段通过 M2M 和 JSONField 无需新迁移

---

## 2026-07-21 关系管理功能增强

### 变更背景

用户提出 6 项关系管理功能增强需求 + 1 项列表数据模型修正：

1. 恢复 n/m 表已配置进度标识
2. 映射列表主键字段黄色标识
3. 目标字段也支持联合主键虚拟选项
4. 目标表下拉排除源表
5. ER图联合主键显示为虚拟字段
6. ER图字段中文名优先展示（两行布局）
7. **列表改回一行=一条映射关系**（不再按表对合并）

### 关键实现决策

#### 列表数据模型修正

**问题**：之前按 `(source_table, target_table)` 分组，导致同一对表的多条映射被合并为一行。

**修正**：`mappingRows` computed 直接 `mappings.value.map()` 每条映射一行，附带 `is_source_pk` / `is_target_pk` 标记。

```typescript
const mappingRows = computed(() => {
  const pkFieldIdsByTable: Record<number, Set<number>> = {}
  if (pkStatusData.value) {
    for (const t of pkStatusData.value.tables) {
      pkFieldIdsByTable[t.table_id] = new Set(t.pk_fields.map((f: any) => f.id))
    }
  }
  return mappings.value.map((m) => ({
    ...m,
    is_source_pk: pkFieldIdsByTable[m.source_table]?.has(m.source_field) ?? false,
    is_target_pk: pkFieldIdsByTable[m.target_table]?.has(m.target_field) ?? false,
  }))
})
```

#### ER图联合主键虚拟字段

当表有 2+ PK 字段时，创建虚拟字段 `{ id: 'composite_pk', is_composite: true, _pkFieldIds: [...] }`，替换 individual PK 字段显示。边去重用 `drawnCompositeEdges` Set，同一对表只画一条边。

#### X6 v2 锚点比例值

`top` 锚点的 `dx/dy` 是比例值(0-1)，不是像素值。通过阅读源码 `node_modules/@antv/x6/lib/registry/node-anchor/bbox.js` 确认：`NumberExt.normalizePercentage(options.dx, bbox.width)` 中数值型参数直接乘以 bbox 宽/高。

```typescript
anchor: { name: 'top', args: { dx: 0.5, dy: sourceFieldY / sourceNodeHeight } }
```

#### 两行字段显示

ER 图字段行从单行改为两行布局：
- `.er-f__name-cn`（12px，中文名）
- `.er-f__name-en`（10px 灰色等宽，英文名）

### 影响范围

- **文件**：`frontend/src/views/modeling/DomainFieldMapping.vue`（纯前端，无后端变更）
- **波及模块**：无（改动完全封闭在单文件内）
- **编译验证**：vue-tsc 零错误
