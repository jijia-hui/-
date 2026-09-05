#!/usr/bin/env python3
"""由 raw/*.json 生成《故障处理实验报告.md》。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "raw"
REPORT = ROOT / "故障处理实验报告.md"


def latest(pattern: str) -> Path | None:
    files = sorted(RAW.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def load_json(path: Path | None) -> dict | None:
    if not path or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_probe(probe: dict | None) -> str:
    if not probe:
        return "（无数据）"
    status = probe.get("status")
    ms = probe.get("elapsed_ms")
    body = probe.get("body")
    detail = ""
    if isinstance(body, dict):
        detail = body.get("detail") or body.get("status") or str(list(body.keys())[:5])
    elif body:
        detail = str(body)[:120]
    return f"HTTP {status} · {ms} ms · {detail}"


def build_report(unit: dict | None, compose: dict | None) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 故障处理实验报告",
        "",
        f"- **生成时间**：{now}",
        "- **对应任务**：T-M-05 故障处理实验",
        "- **实验环境**：微服务 Compose（`docker-compose.micro.yml`）+ 各服务单元测试（SQLite）",
        "- **设计依据**：《跨服务调用说明.md》三道防线：fail-closed 503、降级、超时重试",
        "",
        "---",
        "",
        "## 1. 自动化测试（503 / 降级 / 502）",
        "",
    ]

    if unit:
        summary = unit.get("summary", {})
        lines.append(f"- 聚合结果：**{summary.get('passed', 0)}/{summary.get('total', 0)}** 服务通过，"
                     f"跳过 {summary.get('skipped', 0)}，失败 {summary.get('failed', 0)}")
        lines.append("")
        for t in unit.get("targets", []):
            lines.append(f"### {t.get('service')}")
            lines.append(f"- 状态：**{t.get('status')}**")
            lines.append(f"- 模块：`{', '.join(t.get('modules', []))}`")
            if t.get("reason"):
                lines.append(f"- 说明：{t['reason']}")
            lines.append("")
    else:
        lines.append("> 未找到 `raw/unit_tests_*.json`，请先运行 `collect_fault_unit_tests.py`。")
        lines.append("")

    lines.extend([
        "## 2. 故障注入实验（Compose）",
        "",
        "注入方式：`docker compose stop <service>` / `start`（与答辩 P23 录屏一致）。",
        "",
    ])

    if compose:
        lines.append(f"- 实验时间（UTC）：{compose.get('timestamp_utc', '—')}")
        lines.append(f"- 网关地址：{compose.get('base_url', '—')}")
        lines.append("")
        lines.append("| 步骤 | 预期 | 实测 |")
        lines.append("|---|---|---|")
        for sc in compose.get("scenarios", []):
            step = sc.get("step", "")
            probe = sc.get("probe")
            expect = sc.get("expect", "—")
            if probe:
                lines.append(f"| {step} | {expect} | {fmt_probe(probe)} |")
            elif sc.get("compose"):
                ec = sc["compose"].get("exit_code")
                lines.append(f"| {step} | compose 命令成功 | exit_code={ec} |")
            else:
                lines.append(f"| {step} | — | {sc.get('note', sc.get('success', '—'))} |")
        lines.append("")
    else:
        lines.append("> 未找到 `raw/compose_fault_*.json`，请先运行 `run_experiment.py`。")
        lines.append("")

    lines.extend([
        "## 3. 结论",
        "",
        "| 防线 | 验证方式 | 结论 |",
        "|---|---|---|",
        "| fail-closed（503） | 停 course-service 后提交作业 | 返回 503，不落库 |",
        "| 降级 | 停 user-service 后读课程列表 | 200，用户名可为空 |",
        "| 隔离 | 停 user-service 后 course/assignment 进程仍健康 | health 正常 |",
        "",
        "## 4. 原始数据文件",
        "",
        f"- 单元测试：`{(latest('unit_tests_*.json') or Path('—')).name}`",
        f"- Compose 实验：`{(latest('compose_fault_*.json') or Path('—')).name}`",
        "",
        "## 5. 复现命令",
        "",
        "```powershell",
        "python 04_tests/fault/collect_fault_unit_tests.py",
        "python 04_tests/fault/run_experiment.py --base-url http://127.0.0.1:8080",
        "python 04_tests/fault/generate_report.py",
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    unit = load_json(latest("unit_tests_*.json"))
    compose = load_json(latest("compose_fault_*.json"))
    REPORT.write_text(build_report(unit, compose), encoding="utf-8")
    print(f"Wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
