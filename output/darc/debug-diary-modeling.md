# Debug 日记 — modeling 模块

> 记录 modeling 模块的 Bug 根因、修复方式与已知耦合点，供后续影响分析使用。

## BUG-2026-0728-02 试算弹窗测试值下拉全部 No data

- **现象**：新建计算字段后打开枚举试算弹窗，参数表「测试值」下拉框全是 No data。
- **根因**：引用字段从未同步过去重值（distinct_values=None）时：
  1. `computed_service._build_param_space_from_distinct` 直接用 `['']` 占位不查库 → auto_enumerate 回填全空；
  2. `available_references` 的 sample_values 也只读缓存 → 前端 distinct_values=[]。
  而项目已有 `_ensure_distinct_cache` 按需填充机制（AI查重/组合字段抽屉/刷新去重都在用），唯独试算路径漏接——同类模式缺失。
- **修复**（治本，第六十九轮）：去重缓存工具抽独立模块 `backend/apps/modeling/distinct_cache.py`（ENGINE_MAP/json_safe/fetch_distinct_values/ensure_distinct_cache），views.py 改为 import 别名兼容旧引用；`_build_param_space_from_distinct` 对 distinct_values is None 的字段按需 `ensure_distinct_cache([field_obj])`（失败不阻断降级占位）。
- **已知耦合点**：
  - `distinct_cache.py` 不得 import views（依赖方向：views/computed_service → distinct_cache）；新增需要去重缓存的路径一律复用 `ensure_distinct_cache`，禁止再写只读缓存的降级分支。
  - 外部数据源不可达时 ensure 会记录 errors 不抛异常，试算降级为占位 `['']`——沙箱/断网环境下 No data 仍可能出现，属环境问题非代码问题。
- **验证**：APIClient 实测 trial-calculate 200；standard-fields 28 行全带 distinct_values；vue-tsc 0 errors。

## BUG-2026-0728-01 计算字段保存失败（表面像 IFS 表达式问题）

- **现象**：新建计算字段填入 IFS(...) 表达式，点「保存」只提示「保存失败」，连点多次无效。
- **根因**（两层叠加）：
  1. 数据层：`ComputedField` 有 `unique_together('domain','code')`，用户重建的编码 `store_status` 被**已废弃**（status='discarded'）的同名字段占用 → DRF 返回 400 `{"non_field_errors":["字段 domain, code 必须能构成唯一集合。"]}`。
  2. 前端层：全前端 catch 统一写 `e.response?.data?.error || '兜底文案'`，DRF 的 `non_field_errors`/字段级错误被吞，用户只见笼统「保存失败」。
- **排除项**：IFS/AND/NOT/ISBLANK/`=`/TRUE 均被 formula_engine 支持，相同表达式换新编码实测 201 创建成功（表达式无任何问题）。
- **修复**：
  1. 新建 `frontend/src/utils/apiError.ts` → `extractApiError(e)`：依次解析 error → detail → message → non_field_errors → 字段级错误；全前端 31 处 catch 统一替换（7 文件：DomainFieldConfig 15、FormulaEditor 7、TableList 13→合并复合模式、TrialCalculation 2、DomainFieldMapping 1、TechFunctions 3、ArchiveDetail 2）。
  2. 后端 `ComputedFieldViewSet` 新增 `_code_conflict_response()` 前置校验（create/update 均拦）：编码被废弃字段占用 → 「编码「xxx」已被废弃字段「yyy」占用：请到左栏「废弃字段」分类恢复它，或换一个编码」；被活跃字段占用 → 提示已存在。
- **已知耦合点**：
  - `unique_together('domain','code')` 在 models.py L423，废弃字段不释放编码——这是有意设计（废弃可恢复），前置校验必须区分 discarded/active 给不同指引。
  - 前端新增错误提取入口统一走 `@/utils/apiError`，后续新 catch 禁止再手写 `e.response?.data?.xxx` 链。
- **验证**：APIClient 实测 T1 新编码+IFS=201、T2 重复编码=400 且返回新指引文案；vue-tsc 0 errors。
