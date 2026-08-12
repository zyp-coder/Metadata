---
kind: build_system
name: 构建与制品管理（Django + Vue3 + Docker）
category: build_system
scope:
    - '**'
source_files:
    - backend/Dockerfile
    - backend/docker-compose.yml
    - backend/requirements.txt
    - frontend/package.json
    - frontend/vite.config.ts
    - scripts/check-all.ps1
---

本项目采用前后端分离架构，后端基于 Django + DRF，前端基于 Vue3 + Vite，通过 Docker Compose 编排开发环境，PowerShell 脚本统一执行质量检查。

**后端构建与依赖**
- Python 依赖通过 `backend/requirements.txt` 声明，使用 pip 安装；运行时依赖包括 Django、DRF、psycopg2-binary、redis、celery、gunicorn 等。
- 后端容器镜像基于 `python:3.12-slim`，在 `backend/Dockerfile` 中安装系统依赖（gcc、libpq-dev），再安装 Python 依赖并复制源码。
- 开发服务器通过 `manage.py runserver` 启动，生产部署使用 gunicorn（由 requirements.txt 引入）。

**前端构建与依赖**
- 前端使用 `frontend/package.json` 管理依赖，构建工具为 Vite 5，TypeScript 通过 vue-tsc 进行类型检查。
- 构建脚本：`dev` 启动开发服务器（端口 3000），`build` 先执行 `vue-tsc -b` 类型检查再 `vite build` 生成静态资源，`preview` 预览构建产物。
- Vite 配置在 `frontend/vite.config.ts` 中，配置了 `@` 路径别名指向 `src`，并通过代理将 `/api` 请求转发到后端 `http://localhost:8000`。

**容器化与编排**
- `backend/docker-compose.yml` 定义三个服务：PostgreSQL 15（端口 5432）、Redis 7（端口 6379）、后端应用（端口 8000）。
- 后端服务启动时自动执行 `python manage.py migrate` 然后运行 `runserver`，通过环境变量注入数据库和 Redis 连接信息。
- 所有服务均配置 healthcheck，后端服务依赖 db 和 redis 健康后再启动。

**质量检查与测试**
- `scripts/check-all.ps1` 是统一的 Windows PowerShell 检查脚本，依次执行：后端 Django check、后端测试（apps.modeling 和 apps.archive）、前端 TypeScript 检查（vue-tsc --noEmit）、前端构建检查（vite build --mode production）。
- 脚本统计 pass/fail/skip 数量并以不同颜色输出结果，失败时返回非零退出码。
- 后端测试通过 Django 的 `manage.py test` 运行，前端类型检查通过 `npx vue-tsc --noEmit` 执行。

**约定与约束**
- 后端使用 venv 虚拟环境（`backend/venv`），PowerShell 脚本直接调用 `backend\venv\Scripts\python.exe`。
- 前端开发服务器默认端口 3000，后端默认端口 8000，通过 Vite 代理实现跨域开发。
- 数据库凭据在 docker-compose 中以明文形式硬编码（POSTGRES_PASSWORD=metadata123），仅适用于开发环境。
- 项目未包含 Makefile、CI/CD 配置文件（如 .github/workflows、Jenkinsfile 等），也未发现独立的构建脚本（.sh），构建流程主要依赖各子项目的原生工具链和 PowerShell 聚合脚本。