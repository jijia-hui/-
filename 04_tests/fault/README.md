# 故障处理实验（T-M-05）

本目录补齐任务书要求的四件套：**自动化测试**、**故障注入脚本**（含 Compose 与 K8s）、**原始实验数据**、**实验报告**。

## 目录结构

| 文件 | 作用 |
|---|---|
| `collect_fault_unit_tests.py` | 聚合各微服务 503/降级/502 相关单元测试，输出 JSON |
| `run_experiment.py` | 在 **微服务 Compose** 环境注入故障并采集 HTTP 原始数据 |
| `generate_report.py` | 由 `raw/*.json` 生成 `故障处理实验报告.md` |
| `raw/` | 每次实验的原始 JSON（可提交 Git） |
| `故障处理实验报告.md` | 由脚本生成，答辩/对质用 |

脚本（仓库根目录）：

| 文件 | 作用 |
|---|---|
| `scripts/fault-inject-compose.sh` | **本地 Compose** 一键注入/恢复（与 P23 录屏一致） |
| `scripts/fault-inject.sh` | **K8s** F1～F6 注入/恢复（命名空间 `online-teach-micro`） |

## 环境要求

1. 在仓库根目录，使用 **main 分支微服务版**（含 `services/` 与 `docker-compose.micro.yml`）。
2. Docker Desktop 已启动。
3. Python 3.12（仅实验脚本；单元测试在各服务 venv 或全局均可）。

## 一键流程（推荐）

在仓库根目录 PowerShell：

```powershell
# 1. 启动微服务栈
docker compose -f docker-compose.micro.yml up -d --build

# 2. 初始化演示数据（首次）
docker compose -f docker-compose.micro.yml exec user-service python manage.py seed_data
docker compose -f docker-compose.micro.yml exec course-service python manage.py seed_data
docker compose -f docker-compose.micro.yml exec assignment-service python manage.py seed_data

# 3. 跑单元测试聚合（自动化测试 · 503/降级）
python 04_tests/fault/collect_fault_unit_tests.py

# 4. 跑 Compose 故障实验（原始数据）
python 04_tests/fault/run_experiment.py --base-url http://127.0.0.1:8080

# 5. 生成报告
python 04_tests/fault/generate_report.py
```

完成后应得到：

- `04_tests/fault/raw/unit_tests_*.json`
- `04_tests/fault/raw/compose_fault_*.json`
- `04_tests/fault/故障处理实验报告.md`

## 仅跑自动化测试（不启 Docker）

```powershell
python 04_tests/fault/collect_fault_unit_tests.py
```

## Compose 手动注入（与答辩录屏一致）

```powershell
bash scripts/fault-inject-compose.sh inject user-service
bash scripts/fault-inject-compose.sh recover user-service
```

## K8s 故障演练（需已部署 online-teach-micro + kubeconfig）

```powershell
# 手动触发 GitHub Actions：fault-drill workflow，或本地：
bash scripts/fault-inject.sh F4 inject
bash scripts/fault-inject.sh F4 recover
```

> F3/F5/F6 在 K8s 脚本中为扩展场景；Compose 实验以 SC01～SC04 为准（停服 + HTTP 断言），与 P23 演示一致。

## 与性能压测的区别

故障实验的「加压」指 **停服 / 注入异常**，不是 QPS 压测。若需在故障期间叠加并发请求，可使用：

```powershell
python 04_tests/fault/fault_load_spike.py --base-url http://127.0.0.1:8080 --scenario user_down
```

（可选；默认实验不依赖此脚本。）
