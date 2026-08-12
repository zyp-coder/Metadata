---
kind: error_handling
name: 前后端错误处理体系：DRF序列化校验 + 自定义异常类 + Axios拦截器
category: error_handling
scope:
    - '**'
source_files:
    - backend/config/settings.py
    - backend/apps/modeling/formula_engine.py
    - backend/apps/modeling/custom_functions.py
    - backend/apps/modeling/ai_service.py
    - backend/apps/archive/serializers.py
    - frontend/src/api/index.ts
    - frontend/src/utils/apiError.ts
---

## 1. 系统/方法概述
本仓库采用「后端 Django REST Framework（DRF）序列化校验 + 业务自定义异常类，前端 Axios 响应拦截器统一解析」的分层错误处理方案。后端通过 DRF 的 `serializers.ValidationError` 返回结构化字段级错误，公式引擎使用自研异常层次结构表达语法/引用/运行时错误；前端通过 axios 拦截器将后端错误标准化为 `Error` 对象，并提供 `extractApiError` 工具函数按优先级提取可读消息。

## 2. 关键文件与包
- 后端配置：`backend/config/settings.py` — 注册 DRF、分页、过滤器、Spectacular 文档，未定义自定义 exception_handler。
- 公式引擎异常体系：`backend/apps/modeling/formula_engine.py` — 定义 `FormulaError` 基类及 `FormulaSyntaxError`、`FormulaReferenceError`、`FormulaRuntimeError`、`CircularDependencyError` 四类异常。
- 技术函数插件：`backend/apps/modeling/custom_functions.py` — 通过 `@register_function` 装饰器注册函数，业务错误统一抛 `FormulaRuntimeError`。
- AI 服务异常：`backend/apps/modeling/ai_service.py` — 使用 `RuntimeError` 表达配置缺失、AI 返回格式异常等场景。
- 序列化校验：`backend/apps/archive/serializers.py`、`backend/apps/modeling/serializers.py` — 使用 `serializers.ValidationError` 抛出字段/非字段级校验错误。
- 前端 API 基础封装：`frontend/src/api/index.ts` — axios 实例创建 + 响应拦截器，将后端错误包装为 `Error` 并保留原始 `response`。
- 前端错误提取工具：`frontend/src/utils/apiError.ts` — `extractApiError` 按 `{error} → {detail} → {message} → non_field_errors → 字段级错误` 顺序解析。

## 3. 架构与约定
### 后端异常分层
- **公式引擎**：以 `FormulaError` 为根，细分为语法错误、字段引用错误、运行时错误、循环依赖错误，便于调用方精准捕获与展示。
- **业务逻辑**：AI 服务、Excel 导入、数据源连接等模块直接使用 `RuntimeError` / `ValueError` 表达不可恢复或参数非法的错误。
- **API 层**：通过 DRF Serializer 的 `ValidationError` 返回结构化错误（支持字段级 `field: ["msg"]` 与非字段级 `non_field_errors`），由 DRF 默认异常处理器转为 JSON 响应。
- **无全局异常中间件**：未在 settings 中配置 `DEFAULT_EXCEPTION_HANDLER`，依赖 DRF 默认行为将异常序列化为标准错误响应。

### 前端错误处理流程
1. axios 响应拦截器捕获所有 HTTP 错误，提取 `data.detail/message/error` 作为消息，构造 `Error` 对象并挂载 `response` 字段供上层读取结构化数据。
2. 组件调用 `extractApiError(e)` 从拦截器抛出的错误中提取用户可读消息，优先取顶层 `error/detail/message`，其次拼接 `non_field_errors`，最后遍历字段级错误数组生成 `key: msg` 列表。
3. 若均未命中，返回 `undefined`，由调用方提供中文兜底文案（如「请求失败」）。

### 错误传播路径
- 公式引擎异常 → 调用方（views/service）→ 可能转换为 `ValidationError` 或直接上抛 → DRF 默认处理器 → JSON 响应。
- 网络/HTTP 错误 → axios 拦截器 → 标准化 `Error` → 组件通过 `extractApiError` 提取消息 → 用户可见提示。

## 4. 约定与约束
- **公式函数错误必须抛 `FormulaRuntimeError`**：`custom_functions.py` 注释明确要求业务性错误使用该异常，以便被 `IFERROR` 函数捕获并友好提示。
- **序列化校验统一使用 `serializers.ValidationError`**：所有字段验证失败均通过该方式抛出，确保 DRF 返回标准字段级错误结构。
- **前端错误提取遵循固定优先级**：`apiError.ts` 注释明确定义了 `error → detail → message → non_field_errors → 字段级错误` 的解析顺序，不得随意更改。
- **未使用 panic/recover 或全局异常中间件**：后端未定义自定义 exception handler，前端未使用 try-catch 包裹所有调用，而是依赖拦截器集中处理。
- **错误消息语言**：后端错误消息均为中文（如「该域已有档案，一个域只能创建一个档案」），前端兜底文案也为中文（「请求失败」）。