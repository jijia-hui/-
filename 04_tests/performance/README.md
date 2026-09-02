# 性能对比实验

本目录用于课程要求的单体版与微服务版性能对比。`load_test.py` 是两套部署共用的压力测试脚本，使用同一套请求逻辑和参数运行，避免因工具或测试流程不同造成偏差。

## 测试场景

脚本内置三个只读业务场景：

| 场景 | 请求 |
|---|---|
| `courses` | `GET /api/courses/` |
| `assignments` | `GET /api/assignments/?course=<课程 ID>` |
| `submissions` | `GET /api/submissions/?assignment=<作业 ID>` |

`courses` 代表课程查询，`assignments` 代表作业查询，`submissions` 能覆盖微服务版的跨服务授权范围和用户名补全调用。请求均为只读，不会因为重复压测污染业务数据。

## 运行前提

1. 启动 Docker Desktop，并确认 `docker info` 成功。
2. 分别为单体版和微服务版准备同一批演示数据。两套数据建议使用全新的独立卷，并按 README 中的 `seed_data` 命令按相同顺序初始化。
3. 为每个版本准备一个可访问的学生或教师 JWT。令牌只用于本次压测，不要提交到仓库。
4. 从接口响应中确认 `course-id` 和 `assignment-id`，两套版本使用同一业务数据对应的 ID。
5. 先预热，再测量；单体版和微服务版必须使用相同的并发、时长、预热时间和重复次数。建议一次只运行一套业务栈，避免两套栈互相争抢 CPU/内存。

## 示例

PowerShell 示例（微服务网关使用 `8081`，单体前端使用 `8080`）：

```powershell
python 04_tests/performance/load_test.py `
  --base-url http://127.0.0.1:8080 `
  --token $monoToken `
  --scenario courses `
  --concurrency 10 `
  --duration 60 `
  --warmup 15 `
  --containers otp-backend,otp-mysql,otp-frontend `
  --output 04_tests/performance/raw/monolith_courses_c10_r1.json

python 04_tests/performance/load_test.py `
  --base-url http://127.0.0.1:8081 `
  --token $microToken `
  --scenario courses `
  --concurrency 10 `
  --duration 60 `
  --warmup 15 `
  --containers otp-micro-user,otp-micro-course,otp-micro-assignment,otp-micro-gateway,otp-micro-mysql,otp-micro-frontend `
  --output 04_tests/performance/raw/micro_courses_c10_r1.json
```

对每个场景、每个并发级别至少重复 3 次。建议并发级别为 `1,10,50`，但应根据机器实际承受能力调整。脚本输出 JSON 原始结果，包含测试条件、每次请求的状态汇总、平均/P95 响应时间、吞吐量、错误率以及容器 CPU/内存采样值。

## 两套编排建议

为避免 Compose 项目和端口互相覆盖，使用不同项目名：

```powershell
docker compose -p otp-monolith -f docker-compose.yml up -d --build
docker compose -p otp-micro -f docker-compose.micro.yml up -d --build
```

如果两套同时启动，微服务前端应改用 `WEB_PORT=8081`、网关改用 `GATEWAY_PORT=8001`；正式采样时建议停止另一套栈。测试边界必须在报告中写明：包括前端 Nginx/网关的端到端入口，还是只测后端入口，并在两个版本保持一致。

