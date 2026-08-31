# 在线教学与实训平台

课程教学场景的在线教学与实训平台：学生选课、查看作业、在线提交代码，教师创建课程/作业、查看提交并评分。
后端 Django + DRF，前端 React + Vite + Ant Design，数据库 MySQL 8，全部组件运行在容器中。

> **架构说明**：自 2026-08-31 起后端拆分为 **3 个业务微服务 + 1 个 Nginx API 网关**（用户服务 / 课程服务 / 作业与提交服务），
> 对外 API 与页面完全兼容；单体版保留在 `web_backend/`（Git 标签 `monolith-start`），供性能对比实验使用。
> 拆分方案见《微服务划分图.md》《数据表归属方案.md》《微服务接口清单.md》《跨服务调用说明.md》。

## 技术栈

| 组件 | 技术 | 目录 |
|---|---|---|
| 后端（微服务版，当前） | Python 3.12 / Django 6 / DRF / JWT / gunicorn ×3 服务 + Nginx 网关 | `services/` |
| 后端（单体版，性能对比基线） | Python 3.12 / Django 6 / DRF / gunicorn | `web_backend/` |
| 前端 | Node 20 / React 18 / Vite / Ant Design | `web_frontend/` |
| 数据库 | MySQL 8.0（官方镜像，微服务版三库隔离） | 容器内服务 |
| 编排 | Docker Compose / Kubernetes | `docker-compose*.yml` / `k8s/`（单体）、`k8s/micro/`（微服务） |
| CI/CD | GitHub Actions | `.github/workflows/` |

## 微服务版快速启动（Docker Compose，源码构建）

```bash
git clone https://github.com/jijia-hui/-.git online_teaching_platform
cd online_teaching_platform
docker compose -f docker-compose.micro.yml up -d --build
```

- 首次启动自动创建 MySQL 三个库（`otp_user` / `otp_course` / `otp_assignment`）、各服务自动迁移。
- 访问 http://localhost:8080；网关直连调试 http://localhost:8000（`GATEWAY_PORT` 可改）。
- 健康检查：`/api/health/`（网关）、`/api/health/{user,course,assignment}/`（逐服务，含版本号与 DB 状态）。
- 演示数据（按顺序执行三条命令）：

```bash
docker compose -f docker-compose.micro.yml exec user-service       python manage.py seed_data
docker compose -f docker-compose.micro.yml exec course-service     python manage.py seed_data
docker compose -f docker-compose.micro.yml exec assignment-service python manage.py seed_data
```

- 测试账号：教师 `demo_teacher`、学生 `demo_student`，密码均为 `Demo@1234`；三门示例课程各含 2 个作业。
- 拉取 GHCR 镜像免构建运行：`docker compose -f docker-compose.micro.prod.yml up -d`（可用 `MICRO_IMAGE_TAG` 指定版本）。
- 与单体版互不冲突（容器名 `otp-micro-*`、独立卷），两套可同时运行做性能对比。

### 微服务版测试

```bash
# 各服务单元 + API 测试（SQLite，无需数据库；96 项）
USE_SQLITE=1 python services/user_service/manage.py test tests
USE_SQLITE=1 python services/course_service/manage.py test tests
USE_SQLITE=1 python services/assignment_service/manage.py test tests

# 端到端回归（需微服务栈已启动；58 项断言覆盖 UC01~UC14 + 级联删除）
E2E_BASE_URL=http://127.0.0.1:8080 E2E_EXEC_PREFIX="docker exec -i otp-micro-user" \
python 04_tests/e2e/run_e2e_micro.py
```

### 微服务版 Kubernetes

```bash
bash scripts/deploy_micro_k8s.sh user=<tag> course=<tag> assignment=<tag> frontend=<tag>
# 例（CI 中统一以当前版本部署）：
bash scripts/deploy_micro_k8s.sh user=v1.1.0 course=v1.1.0 assignment=v1.1.0 frontend=v1.1.0
kubectl -n online-teach-micro port-forward svc/frontend 8080:80   # 本机访问
```

命名空间 `online-teach-micro`（与单体版 `online-teach` 隔离）；每服务有 `/api/live/`、`/api/ready/` 探针与版本号注入。

## 快速启动（拉取 GHCR 镜像，无需克隆源码）

CI 在每次推送到 `main` 后自动构建前后端镜像并发布到 GHCR。本地只需一个编排文件即可拉起完整项目（自动建库、执行迁移、收集静态文件），无需克隆源码、无需安装 Python/Node/MySQL。

前置条件：安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（含 Docker Engine 与 Compose v2）。

```bash
# 1. 下载编排文件（Windows PowerShell 可用：
#    Invoke-WebRequest -OutFile docker-compose.prod.yml <下方地址>）
curl -LO https://raw.githubusercontent.com/jijia-hui/-/main/docker-compose.prod.yml

# 2. 拉取镜像并启动（MySQL 初始化约需半分钟，可用 ps 等待 healthy）
docker compose -f docker-compose.prod.yml up -d

# 3.（可选）导入演示数据（脚本幂等，详见下方"测试数据"）
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_data
```

启动完成后访问 http://localhost:8080（端口可通过 `.env` 中的 `WEB_PORT` 修改，`.env` 需与编排文件放同一目录）。

> **镜像拉取报 `denied`？** GHCR 包默认私有，两种解决方式任选其一：
> 1.（推荐）在 GitHub 仓库右侧 **Packages** 中分别打开 `online-teaching-platform-backend` 和 `online-teaching-platform-frontend` → **Package settings** → **Danger Zone** → **Change visibility** → **Public**，一次设置永久生效；
> 2. 本机登录：`docker login ghcr.io -u jijia-hui`，密码使用勾选了 `read:packages` 权限的 [Personal Access Token](https://github.com/settings/tokens)。

已克隆仓库的情况下，在仓库根目录执行 `docker compose -f docker-compose.prod.yml up -d` 同样可直接拉镜像启动，跳过本地构建。

### 常用命令（拉取模式）

```bash
docker compose -f docker-compose.prod.yml ps                # 查看服务状态
docker compose -f docker-compose.prod.yml logs -f backend   # 跟踪后端日志
docker compose -f docker-compose.prod.yml down              # 停止（数据保留在卷中）
```

## 从源码构建启动（Docker Compose）

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
docker compose exec backend python manage.py createsuperuser   # 后台管理员
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

**单体版**（`ci.yml` / `cd.yml`）：推送到 `main` 后自动执行单元/集成/E2E 测试与前后端构建；CD 测试通过后制作**版本化镜像**（提交 SHA 或 `v*` 标签）推送 GHCR，并部署到 Kubernetes（kind）完成健康检查。任一环节失败即停止。

**微服务版**（`ci-micro.yml` / `cd-micro.yml`）：按**路径检测变更**，只有发生变更的微服务才会重新测试、构建镜像并推送（`ghcr.io/<owner>/otp-{user,course,assignment}-service`、`otp-gateway`，版本号 = 提交 SHA / `v*` 标签）；随后部署整套微服务到 kind 集群（`k8s/micro/`），健康检查 + **UC01~UC14 全量 E2E 回归**通过才算成功，部署日志与 E2E 报告保留为构建产物（含失败诊断：pod 状态、deployment 详情、各服务日志）。

镜像发布到 GHCR 后，任何一台装有 Docker 的机器都可通过 `docker-compose.micro.prod.yml` 一键拉取运行微服务版，见上文"微服务版快速启动"。

## 目录结构

```text
online_teaching_platform/
├── docker-compose.yml            # 单体版编排（mysql / backend / frontend，源码构建）
├── docker-compose.prod.yml       # 单体版拉取式编排（GHCR 镜像）
├── docker-compose.micro.yml      # 微服务版编排（源码构建：三服务 + 网关 + 前端）
├── docker-compose.micro.prod.yml # 微服务版拉取式编排（GHCR 镜像）
├── services/                     # 微服务版后端
│   ├── user_service/             #   用户服务（users / email_verification_codes）
│   ├── course_service/           #   课程服务（courses / enrollments）
│   ├── assignment_service/       #   作业与提交服务（assignments / submissions）
│   ├── gateway/                  #   API 网关（Nginx，编排内服务名 backend:8000）
│   └── db/init/                  #   MySQL 三库初始化脚本
├── web_backend/                  # 单体版后端（monolith-start，性能对比基线）
├── web_frontend/                 # React 前端（单体/微服务共用镜像）
├── k8s/                          # 单体版 K8s 清单；k8s/micro/ 为微服务版
├── scripts/                      # 部署脚本（deploy_k8s.sh / deploy_micro_k8s.sh）
├── .github/workflows/            # CI / CD（单体 + 微服务各一套）
├── 04_tests/                     # 单元 / 集成 / 端到端测试（含微服务版）
└── 部署文档.md                    # 完整部署与 CI/CD 说明
```
