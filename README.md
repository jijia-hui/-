# 在线教学与实训平台

课程教学场景的在线教学与实训平台：学生选课、查看作业、在线提交代码，教师创建课程/作业、查看提交并评分。
后端 Django + DRF，前端 React + Vite + Ant Design，数据库 MySQL 8，全部组件运行在容器中。

## 技术栈

| 组件 | 技术 | 目录 |
|---|---|---|
| 后端 | Python 3.12 / Django 6 / DRF / gunicorn | `web_backend/` |
| 前端 | Node 20 / React 18 / Vite / Ant Design | `web_frontend/` |
| 数据库 | MySQL 8.0（官方镜像） | 容器内服务 |
| 编排 | Docker Compose / Kubernetes | `docker-compose.yml` / `k8s/` |
| CI/CD | GitHub Actions | `.github/workflows/` |

## 快速启动（Docker Compose）

前置条件：安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（含 Docker Engine 与 Compose v2）。

```bash
git clone https://github.com/jijia-hui/-.git online_teaching_platform
cd online_teaching_platform

# 可选：配置邮箱与密码等（不配置也能启动，邮件会打印到后端日志）
cp .env.example .env

# 构建并启动（首次自动建库、执行迁移建表、收集静态文件）
docker compose up -d --build
```

启动完成后访问 http://localhost:8080 （端口可通过 `.env` 中的 `WEB_PORT` 修改）。
Compose 会启动 MySQL、**user-service**（注册/登录）、**backend**（课程/作业）和前端。

### 测试数据

```bash
docker compose exec backend python manage.py seed_data
```

脚本幂等（可重复执行），会创建演示账号与课程作业：

- 教师 `demo_teacher`、学生 `demo_student`，密码均为 `Demo@1234`
- 三门示例课程（CS101 程序设计基础 / OS101 操作系统 / CN101 计算机网络），每门含 2 个作业

### 常用命令

```bash
docker compose ps                # 查看服务状态
docker compose logs -f backend   # 跟踪后端日志
docker compose restart backend   # 重启单个服务
docker compose down              # 停止（数据保留在卷中）
docker compose up -d --build     # 代码变更后重新构建
docker compose exec user-service python manage.py createsuperuser   # 后台管理员（用户服务）
```

## 本地开发（不使用容器）

1. MySQL 8 运行，建库：`CREATE DATABASE online_teach CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
2. 后端：`python -m venv .venv` → 安装 `web_backend/requirements.txt` → `python web_backend/manage.py runserver`（数据库连接等配置在 `web_backend/web_backend/settings.py`，可用环境变量覆盖）
3. 前端：`cd web_frontend && npm install && npm run dev`（Vite 代理 `/api` 到 `127.0.0.1:8000`）

## 测试

| 类型 | 命令 |
|---|---|
| 单元测试（UNIT-TC01~14） | `PYTHONPATH=web_backend python web_backend/manage.py test 04_tests/unit` |
| 集成/API 测试（INT-TC01~14） | `PYTHONPATH=web_backend python web_backend/manage.py test 04_tests/integration` |
| 端到端测试（E2E-TC01~14） | `python 04_tests/e2e/run_e2e.py` |

详细说明见 `04_tests/README.md`。

## CI/CD（GitHub Actions）

推送到 `main`：CI 自动执行单元/集成/E2E 测试与前后端构建；CD 测试通过后制作**版本化镜像**（提交 SHA 或 `v*` 标签）推送 GHCR，并部署到 Kubernetes（kind）完成健康检查。任一环节失败即停止，后续部署不执行；运行日志与失败诊断均保留为构建产物。详见 `部署文档.md`。

## 目录结构

```text
online_teaching_platform/
├── docker-compose.yml        # 容器编排（mysql / backend / frontend）
├── web_backend/              # Django 后端（Dockerfile、entrypoint.sh）
├── web_frontend/             # React 前端（Dockerfile、nginx.conf）
├── k8s/                      # Kubernetes 部署清单
├── scripts/deploy_k8s.sh     # K8s 部署 + 健康检查脚本
├── .github/workflows/        # CI / CD 流水线
├── 04_tests/                 # 单元 / 集成 / 端到端测试
└── 部署文档.md               # 完整部署与 CI/CD 说明
```
