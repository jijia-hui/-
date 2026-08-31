# 自动化测试说明（04_tests）

三类测试与任务书对应：

| 层级 | 目录 | 覆盖范围 | 运行方式 |
|---|---|---|---|
| 单元测试 | `04_tests/unit/` | 关键类、方法、业务规则与异常分支（模型 / 序列化器 / 权限类 / `Assignment.is_expired`），UNIT-TC01~14 | `python web_backend/manage.py test 04_tests/unit` |
| 集成/API 测试 | `04_tests/integration/` | 对外接口与数据库访问，按用例覆盖主成功 / 备选 / 异常流程，INT-TC01~14（每用例一个文件） | `python web_backend/manage.py test 04_tests/integration` |
| 端到端测试 | `04_tests/e2e/` | 从接口入口走完每个业务场景的完整流程，E2E-TC01~14 | `python 04_tests/e2e/run_e2e.py` |
| 冒烟测试（第 1 天产物） | `04_tests/smoke/` | 全流程 API 冒烟（32 项断言，逐用例） | 先启动后端再运行 `day1_smoke_api.py` |

## 微服务版测试（第二阶段新增）

每个微服务自带单元 + API 测试（跨服务调用全部 mock，SQLite 运行，无需数据库/依赖服务），
测试目录随服务走，可单独运行（任务书要求"每个服务能单独构建、测试和部署"）：

| 服务 | 测试目录 | 数量 | 运行方式（仓库根目录） |
|---|---|---|---|
| user-service | `services/user_service/tests/` | 32 | `USE_SQLITE=1 python services/user_service/manage.py test tests` |
| course-service | `services/course_service/tests/` | 27 | `USE_SQLITE=1 python services/course_service/manage.py test tests` |
| assignment-service | `services/assignment_service/tests/` | 37 | `USE_SQLITE=1 python services/assignment_service/manage.py test tests` |

覆盖内容（按用例编号的映射见 `02_docs/追溯表.md` 第 6 节）：

- **user-service**：注册/验证码（UC01）、JWT 登录与过期（UC02）、me（UC13）、内部用户接口契约、删除用户级联清理的成败路径（502 fail-closed）。
- **course-service**：课程 CRUD/选课退课（UC03~UC06）、教师名补全的正常与降级（用户服务不可用 → null）、内部课程接口、用户 purge 级联。
- **assignment-service**：作业 CRUD 与课程归属校验（UC07/UC08）、提交/评分（UC09~UC12）含选课校验 503 fail-closed、教师范围圈定、学生用户名补全降级、课程/用户 purge 级联、`is_expired` 业务规则。

### 微服务端到端回归（经 API 网关）

`04_tests/e2e/run_e2e_micro.py` 覆盖 UC01~UC14 全部用例 + 用户/课程删除的跨服务级联清理（58 项断言），
必须指向**已在运行**的微服务栈（Compose 或 Kubernetes）：

```bash
# Compose 栈（本地）
E2E_BASE_URL=http://127.0.0.1:8080 \
E2E_EXEC_PREFIX="docker exec -i otp-micro-user" \
python 04_tests/e2e/run_e2e_micro.py

# Kubernetes 栈（CD 流水线中的用法）
E2E_BASE_URL=http://127.0.0.1:8080 \
E2E_EXEC_PREFIX="kubectl -n online-teach-micro exec deploy/user-service --" \
python 04_tests/e2e/run_e2e_micro.py
```

说明：验证码与临时管理员通过 `E2E_EXEC_PREFIX` 在 user-service 容器内注入（与单体版走 `manage.py shell` 的做法一致，避免 E2E 触发真实 SMTP）；E2E-TC14 管理后台只检查 user-service 暴露的 Django Admin（课程/作业数据归各服务，无集中后台）。报告写入 `04_tests/reports/e2e_micro_report_<时间戳>.md`。

## 环境要求

- Python 3.12 + venv（`D:\online_teaching_platform\.venv` 或自行创建），依赖见 `web_backend` 运行环境
- MySQL 8 运行中（`web_backend/web_backend/settings.py` 的 DATABASES 配置）
- Django 测试会自动创建/销毁测试数据库，不影响开发数据

## 运行方式

在仓库根目录执行（模块名不能以数字开头，故用目录路径作为 Django 测试标签）：

```bash
# 单元测试
PYTHONPATH=web_backend python web_backend/manage.py test 04_tests/unit

# 集成/API 测试
PYTHONPATH=web_backend python web_backend/manage.py test 04_tests/integration

# 两者一起
PYTHONPATH=web_backend python web_backend/manage.py test 04_tests/unit 04_tests/integration

# 端到端测试（自动复用 8000 端口；不可达时自动启动后端到 8765，跑完关闭）
python 04_tests/e2e/run_e2e.py

# 指定后端地址（服务已在别处启动时）
E2E_BASE_URL=http://127.0.0.1:8000 python 04_tests/e2e/run_e2e.py
```

> Windows 的 cmd/PowerShell 用 `set PYTHONPATH=web_backend` 代替 `PYTHONPATH=...` 前缀写法。

## 测试结果

- 单元 + 集成：Django 测试运行器汇总（`Ran N tests ... OK`），失败时退出码非 0（CI 可据此停止流水线）。
- 端到端：控制台逐项 PASS/FAIL + 自动写入 `04_tests/reports/e2e_report_<时间戳>.md`，失败时退出码 1。
- 汇总报告：`04_tests/reports/测试报告.md`（总数 / 通过 / 失败 / 失败原因 / 运行环境）。

## 追溯

各用例 ↔ 测试编号（UNIT-TC / INT-TC / E2E-TC）的对应关系见 `02_docs/追溯表.md`。
