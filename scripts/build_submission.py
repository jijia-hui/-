#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把仓库最新材料同步整理到 D:\\submission（哈希对比，只增改不误删）。"""
import hashlib
import os
import shutil
import sys

REPO = r"D:\online_teaching_platform"
SUB = r"D:\submission"

EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "venv",
                "dist", "build", ".wpp_backup"}
EXCLUDE_FILES = {".gitkeep"}


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def sync_file(src, dst, report):
    if os.path.basename(src) in EXCLUDE_FILES:
        return
    if os.path.exists(dst) and sha(src) == sha(dst):
        report["same"] += 1
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    tag = "UPDATE" if os.path.exists(dst) else "COPY"
    report["copied"].append((tag, os.path.relpath(src, REPO), os.path.relpath(dst, SUB)))


def sync_tree(src, dst, report, exclude_sub=None):
    exclude_sub = exclude_sub or set()
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS
                   and os.path.relpath(os.path.join(root, d), src) not in exclude_sub]
        for f in sorted(files):
            if f in EXCLUDE_FILES:
                continue
            if f.endswith((".pyc", ".pyo")):
                continue
            s = os.path.join(root, f)
            sync_file(s, os.path.join(dst, os.path.relpath(s, src)), report)


def main():
    report = {"copied": [], "same": 0}

    # 1. 根 README
    sync_file(os.path.join(REPO, "README.md"), os.path.join(SUB, "README.md"), report)

    # 2. 02_docs 全量同步
    sync_tree(os.path.join(REPO, "02_docs"), os.path.join(SUB, "02_docs"), report)

    # 3. 03_devops：compose/env/k8s/脚本/流水线/根级文档
    dev = os.path.join(SUB, "03_devops")
    for f in ["docker-compose.yml", "docker-compose.prod.yml",
              "docker-compose.micro.yml", "docker-compose.micro.prod.yml",
              ".env.example", "部署文档.md", "微服务自动构建部署验收报告.md"]:
        sync_file(os.path.join(REPO, f), os.path.join(dev, f), report)
    sync_tree(os.path.join(REPO, "k8s"), os.path.join(dev, "k8s"), report)
    for f in ["deploy_k8s.sh", "deploy_micro_k8s.sh", "fault-inject.sh"]:
        sync_file(os.path.join(REPO, "scripts", f), os.path.join(dev, "scripts", f), report)
    sync_tree(os.path.join(REPO, ".github", "workflows"), os.path.join(dev, "workflows"), report)

    # 4. 04_tests：测试代码与报告
    sync_tree(os.path.join(REPO, "04_tests"), os.path.join(SUB, "04_tests"), report)

    # 5. HPA 实验（任务书第5项：压力脚本+原始结果+3轮数据和分析 → 04_tests）
    hpa_sub = os.path.join(SUB, "04_tests", "HPA自动扩缩容实验")
    sync_file(os.path.join(REPO, "05_management", "HPA自动扩缩容实验", "HPA自动扩缩容实验报告.md"),
              os.path.join(hpa_sub, "HPA自动扩缩容实验报告.md"), report)
    # raw 只取 round1~3（round4/roundN 是失败运行的残留，不入交付）
    for r in ["round1", "round2", "round3"]:
        sync_tree(os.path.join(REPO, "05_management", "HPA自动扩缩容实验", "raw", r),
                  os.path.join(hpa_sub, "raw", r), report)
    # 只随交付包放复现实验必需的三个脚本；hpa_analyze/hpa_summarize 属分析工具，留在仓库
    for f in ["hpa_loadtest.py", "hpa_metrics_sampler.py", "hpa_experiment.sh"]:
        sync_file(os.path.join(REPO, "scripts", f), os.path.join(hpa_sub, "scripts", f), report)

    # 6. 流水线记录（任务书第4项：流水线原始报告 → 04_tests）
    sync_tree(os.path.join(REPO, "05_management", "流水线记录"),
              os.path.join(SUB, "04_tests", "流水线记录"), report)

    # 7. 05_management：管理材料
    mg = os.path.join(SUB, "05_management")
    for f in ["中期检查汇报.md", "看板.md", "看板任务清单.md", "统计页面.html"]:
        sync_file(os.path.join(REPO, "05_management", f), os.path.join(mg, f), report)

    # 8. 06_defense：报告与讲稿（PPT/视频已在 submission，不覆盖）
    df = os.path.join(SUB, "06_defense")
    for f in ["技术总结报告.md", "答辩讲稿-部署失败排查.md"]:
        sync_file(os.path.join(REPO, "06_defense", f), os.path.join(df, f), report)

    # 9. 01_source：源码快照（排除缓存/构建产物）
    for d in ["services", "web_backend", "web_frontend"]:
        sync_tree(os.path.join(REPO, d), os.path.join(SUB, "01_source", d), report)

    # 10. 清理 submission 里的 WPS 自动备份垃圾
    wpp = os.path.join(df, ".wpp_backup")
    removed = []
    if os.path.isdir(wpp):
        shutil.rmtree(wpp)
        removed.append(os.path.relpath(wpp, SUB))

    print("=== 同步完成 ===")
    print("内容一致跳过: %d 个文件" % report["same"])
    print("复制/更新: %d 个文件" % len(report["copied"]))
    for tag, s, d in report["copied"]:
        print("  [%s] %s -> %s" % (tag, s, d))
    print("删除目录: %s" % (removed or "无"))


if __name__ == "__main__":
    main()
