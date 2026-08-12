---
kind: logging_system
name: 日志系统 — 基于 Python 标准库 logging 的分散式记录
category: logging_system
scope:
    - '**'
source_files:
    - backend/config/settings.py
    - backend/local_settings.py
    - backend/apps/modeling/plugin_loader.py
    - backend/apps/archive/views.py
    - backend/apps/archive/apps.py
---

## 1. 使用的系统与框架
本项目后端未引入第三方日志框架（如 loguru、structlog、django-logging-json），而是直接使用 Python 标准库 `logging`。所有日志通过 `logging.getLogger(__name__)` 获取模块级 logger 实例，按模块命名空间输出。

## 2. 核心文件与位置
- `backend/apps/modeling/plugin_loader.py`：集中定义模块级 `logger = logging.getLogger(__name__)`，用于插件加载/卸载/重载等关键路径的 info/warning 记录。
- `backend/apps/archive/views.py`：在同步失败、计算字段重算失败等异常分支中内联使用 `import logging; logging.getLogger(__name__).error(...)` / `.warning(...)`。
- `backend/apps/archive/apps.py`：后台自动刷新线程中使用 `logging.getLogger(__name__)` 记录循环执行结果与异常。
- `backend/config/settings.py`：**未配置任何 LOGGING 字典**，Django 默认使用控制台输出。
- `backend/local_settings.py`：仅覆盖数据库与缓存，不涉及日志配置。

## 3. 架构与约定
- **无统一 logger 封装**：每个需要日志的模块自行 `import logging` 并调用 `logging.getLogger(__name__)`，没有共享的 logger 工厂或基类。
- **无结构化日志**：日志消息以 f-string 拼接为主（如 `f'同步数据失败: {e}'`、`f'档案 {archive.id}({archive.name}) 自动刷新完成: {stats}'`），未使用 JSON 或固定字段结构。
- **无日志级别策略文档**：代码中混用 `info`、`warning`、`error`、`exception`，未见统一的级别规范说明。
- **无日志轮转/文件输出**：未配置 `FileHandler`、`RotatingFileHandler`，生产环境依赖 Django/WSGI 容器的 stdout/stderr 收集。
- **无请求链路追踪**：未在中间件或 DRF 层面注入 request_id、trace_id 等上下文字段。

## 4. 观察到的约定与约束
- 模块级 logger 命名：统一通过 `logging.getLogger(__name__)` 获取，保证 logger 名称与模块路径一致。
- 异常处理中的日志：在 `try/except` 块中对捕获的异常使用 `.error()` 或 `.warning()` 记录，错误信息包含异常对象字符串化结果。
- 启动时加载流程：`plugin_loader.load_all_plugins()` 在启动扫描失败时使用 `logger.warning` 记录，不中断服务启动。
- 后台线程日志：`apps.archive.apps.py` 的自动刷新线程使用独立 logger，区分于主线程日志。

## 5. 缺失项（当前状态）
- 未配置 `LOGGING` 字典，无法控制日志级别、格式、输出目标。
- 未集成 Sentry、ELK、Prometheus 等外部日志/监控平台。
- 前端（Vue3）未发现专用日志工具，调试主要依赖浏览器控制台。

总体而言，本项目的日志系统是**基于 Python 标准库 logging 的轻量实现**，满足基本的问题定位需求，但缺乏结构化、集中化与可观测性能力。