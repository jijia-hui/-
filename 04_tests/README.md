# 自动化测试说明（04_tests）

三类测试与任务书对应：

| 层级 | 目录 | 覆盖范围 | 运行方式 |
|---|---|---|---|
| 单元测试 | `04_tests/unit/` | 关键类、方法、业务规则与异常分支（模型 / 序列化器 / 权限类 / `Assignment.is_expired`），UNIT-TC01~14 | `python web_backend/manage.py test 04_tests/unit` |
| 集成/API 测试 | `04_tests/integration/` | 对外接口与数据库访问，按用例覆盖主成功 / 备选 / 异常流程，INT-TC01~14（每用例一个文件） | `python web_backend/manage.py test 04_tests/integration` |
| 端到端测试 | `04_tests/e2e/` | 从接口入口走完每个业务场景的完整流程，E2E-TC01~14 | `python 04_tests/e2e/run_e2e.py` |
| 冒烟测试（第 1 天产物） | `04_tests/smoke/` | 全流程 API 冒烟（32 项断言，逐用例） | 先启动后端再运行 `day1_smoke_api.py` |

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
