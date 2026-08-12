---
kind: dependency_management
name: Python与Node.js双端依赖管理
category: dependency_management
scope:
    - '**'
source_files:
    - backend/requirements.txt
    - frontend/package.json
    - frontend/package-lock.json
    - backend/Dockerfile
    - backend/docker-compose.yml
---

本仓库采用前后端分离架构，依赖管理分别由 Python 的 pip 和 Node.js 的 npm 各自独立管理：

**后端（Django）**
- 使用 `backend/requirements.txt` 声明所有 Python 依赖，采用宽松上限版本约束（如 `Django>=5.0,<5.1`、`djangorestframework>=3.14,<4.0`），锁定主版本范围但允许次版本更新。
- 关键依赖包括 Django、DRF、psycopg2-binary、redis、celery、gunicorn、openpyxl 等。
- 通过 Dockerfile 中的 `pip install -r requirements.txt` 在容器构建时安装依赖，未使用虚拟环境文件或 lock 文件。
- 无 pyproject.toml、poetry.lock、Pipfile 等现代 Python 依赖管理工具配置。

**前端（Vue3）**
- 使用 `frontend/package.json` 声明依赖，分为 dependencies 和 devDependencies 两类。
- 使用 `package-lock.json`（lockfileVersion: 3）锁定精确依赖树，确保构建可重现。
- 主要依赖包括 Vue 3、Ant Design Vue、Axios、Pinia、Vite、TypeScript 等。
- 使用 npm 包管理器，未见 pnpm 或 yarn 配置文件。

**容器化部署**
- `backend/docker-compose.yml` 编排 PostgreSQL、Redis 和后端服务，依赖通过 Docker 镜像拉取。
- Dockerfile 基于 python:3.12-slim，系统级依赖通过 apt-get 安装 gcc、libpq-dev。

**约定与约束**
- Python 依赖使用 `>=X,<Y` 格式限制主版本范围，避免破坏性更新。
- 前端依赖使用语义化版本前缀（^、~），配合 package-lock.json 保证一致性。
- 未使用私有 PyPI 源或 npm registry 镜像，直接访问官方仓库。
- 无依赖安全扫描或自动更新机制。