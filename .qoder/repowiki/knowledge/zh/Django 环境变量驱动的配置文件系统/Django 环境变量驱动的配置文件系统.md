---
kind: configuration_system
name: Django 环境变量驱动的配置文件系统
category: configuration_system
scope:
    - '**'
source_files:
    - backend/config/settings.py
    - backend/local_settings.py
    - backend/docker-compose.yml
    - backend/manage.py
    - backend/config/wsgi.py
    - backend/config/pagination.py
    - backend/config/urls.py
---

本项目的配置系统基于 Django 框架，采用**环境变量优先 + 本地覆盖文件**的双层加载机制，所有运行时配置均通过 `os.environ.get()` 从环境变量读取，并提供合理的默认值。

## 核心架构

- **主配置文件**：`backend/config/settings.py` 集中定义所有 Django 及业务配置项
- **开发环境覆盖**：`backend/local_settings.py` 通过 `from local_settings import *` 动态导入，仅在存在时生效
- **入口设置**：`manage.py`、`wsgi.py` 通过 `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')` 统一指定配置模块

## 配置分层与来源

### 1. 环境变量（生产/部署首选）
项目使用以下关键环境变量：
- **应用安全**：`DJANGO_SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS`
- **数据库**：`DB_NAME`、`DB_USER`、`DB_PASSWORD`、`DB_HOST`、`DB_PORT`（默认 PostgreSQL）
- **缓存**：`REDIS_HOST`、`REDIS_PORT`（默认 Redis）
- **AI 服务**：`AI_API_BASE`、`AI_API_KEY`、`AI_MODEL`、`AI_TIMEOUT`
- **业务开关**：`ARCHIVE_AUTO_REFRESH_MINUTES`（档案自动刷新间隔）

### 2. Docker Compose 注入
`backend/docker-compose.yml` 为后端服务显式注入数据库、Redis 连接参数，实现容器化环境的配置管理。

### 3. 本地开发覆盖
`local_settings.py` 提供开发友好的默认值：SQLite3 数据库、内存缓存、CORS 跨域支持，无需额外环境变量即可运行。

## 配置组织约定

- **单一事实源**：所有配置集中在 `settings.py`，避免分散在多个文件中
- **类型转换**：数值型配置通过 `int()` 转换，布尔型通过 `bool(int())` 处理
- **列表配置**：`ALLOWED_HOSTS` 通过逗号分割字符串解析
- **模块化扩展**：DRF 分页、API Schema、中间件等通过独立模块（如 `pagination.py`）组织
- **条件加载**：通过 try/except ImportError 实现可选配置文件的优雅降级

## 约束与规则

- 生产环境必须设置 `DJANGO_SECRET_KEY`，否则使用开发默认值（不安全）
- 数据库连接必须提供完整的 DB_* 环境变量，否则回退到本地 SQLite
- AI 服务配置为空时自动回退到启发式模拟模式
- 分页大小上限限制为 100000，防止恶意请求耗尽资源