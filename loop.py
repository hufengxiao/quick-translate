#!/usr/bin/env python3
"""Loop Engineering Runner — 自动发现任务 → 执行 → 验证 → 提交 → 继续

核心循环:
  1. 读 .planning/ROADMAP.md 找到下一个未完成任务
  2. 读 .planning/phases/N/PLAN.md 获取任务详情
  3. 执行任务（由 AI 代理完成）
  4. 运行 ci_test.py 验证
  5. 提交 + 推送
  6. 更新 ROADMAP.md 标记完成
  7. 回到步骤 1

用法:
  python loop.py                  # 运行一轮循环
  python loop.py --dry-run        # 只显示下一个任务，不执行
  python loop.py --status         # 显示当前进度
"""
import re
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT = Path(__file__).parent
ROADMAP = PROJECT / ".planning" / "ROADMAP.md"
STATE = PROJECT / ".planning" / "STATE.md"
PHASES = PROJECT / ".planning" / "phases"

GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"


def log(msg, color=""):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{DIM}{ts}{RESET} {color}{msg}{RESET}")


def read_file(path):
    return Path(path).read_text(encoding="utf-8")


def write_file(path, content):
    Path(path).write_text(content, encoding="utf-8")


def run_cmd(cmd, timeout=120):
    r = subprocess.run(cmd, shell=True, cwd=PROJECT, capture_output=True, text=True, timeout=timeout)
    return r.returncode == 0, r.stdout.strip(), r.stderr.strip()


# ── 解析 ROADMAP ──

def parse_roadmap():
    """解析 ROADMAP.md，返回所有阶段信息"""
    content = read_file(ROADMAP)
    phases = []
    current = None
    for line in content.split("\n"):
        # 匹配阶段标题: ### Phase N: Name ✅ 或 ### Phase N: Name
        m = re.match(r"###\s+Phase\s+(\d+):\s+(.+?)(?:\s+✅)?$", line)
        if m:
            if current:
                phases.append(current)
            num = int(m.group(1))
            name = m.group(2).strip()
            done = "✅" in line
            current = {"num": num, "name": name, "done": done, "tasks": [], "status": "DONE" if done else "PLANNED"}
            continue
        # 匹配状态行: **Status:** DONE / IN PROGRESS / PLANNED
        if current and "**Status:**" in line:
            s = line.split("**Status:**")[1].strip()
            current["status"] = s
        # 匹配任务: - [x] 或 - [ ]
        if current and re.match(r"\s*-\s*\[([ x])\]\s+", line):
            m2 = re.match(r"\s*-\s*\[([ x])\]\s+(.+)", line)
            if m2:
                done = m2.group(1) == "x"
                task = m2.group(2).strip()
                current["tasks"].append({"done": done, "text": task})
    if current:
        phases.append(current)
    return phases


def find_next_task(phases):
    """找到下一个未完成的任务"""
    for phase in phases:
        if phase["done"]:
            continue
        for task in phase["tasks"]:
            if not task["done"]:
                return phase, task
    return None, None


def mark_task_done(phase_num, task_text):
    """在 ROADMAP.md 中标记任务为完成"""
    content = read_file(ROADMAP)
    # 找到对应的任务行并把 [ ] 改为 [x]
    lines = content.split("\n")
    in_phase = False
    for i, line in enumerate(lines):
        if f"Phase {phase_num}:" in line:
            in_phase = True
        if in_phase and task_text in line and "[ ]" in line:
            lines[i] = line.replace("[ ]", "[x]", 1)
            break
    write_file(ROADMAP, "\n".join(lines))


def mark_phase_done(phase_num):
    """标记整个阶段为完成"""
    content = read_file(ROADMAP)
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if f"Phase {phase_num}:" in line and "✅" not in line:
            lines[i] = line.rstrip() + " ✅"
        if f"**Status:**" in line and f"Phase {phase_num}:" in "\n".join(lines[max(0,i-5):i]):
            lines[i] = "**Status:** DONE"
    write_file(ROADMAP, "\n".join(lines))


# ── 显示状态 ──

def show_status():
    phases = parse_roadmap()
    print(f"\n{BOLD}Quick Translate — 项目进度{RESET}\n")
    for p in phases:
        icon = f"{GREEN}✅{RESET}" if p["done"] else f"{YELLOW}⏳{RESET}"
        done_count = sum(1 for t in p["tasks"] if t["done"])
        total = len(p["tasks"])
        print(f"  {icon} Phase {p['num']}: {p['name']}  ({done_count}/{total})")
        for t in p["tasks"]:
            ti = f"{GREEN}[x]{RESET}" if t["done"] else f"{YELLOW}[ ]{RESET}"
            print(f"      {ti} {t['text']}")
    print()


# ── 主循环 ──

def run_loop(dry_run=False):
    """执行一轮 Loop Engineering 循环"""
    phases = parse_roadmap()
    phase, task = find_next_task(phases)

    if not task:
        log(f"{GREEN}所有任务完成！{RESET}")
        return True

    log(f"Phase {phase['num']}: {phase['name']}", CYAN)
    log(f"下一个任务: {task['text']}", BOLD)

    if dry_run:
        log("(dry-run 模式，不执行)", YELLOW)
        return False

    # 这里是 Loop Engineering 的核心：
    # 任务描述会作为 prompt 传递给 AI 代理
    # AI 代理读取代码、执行修改、运行测试
    # 验证通过后标记完成

    task_prompt = f"""你是一个自动开发循环中的执行代理。

项目: quick-translate (C:\\Users\\hufen\\projects\\quick-translate)
当前阶段: Phase {phase['num']} — {phase['name']}

任务: {task['text']}

要求:
1. 读取相关代码文件，理解当前实现
2. 实现任务描述的功能
3. 运行 python ci_test.py 验证所有测试通过
4. 提交代码: git add -A && git commit -m "loop: {task['text']}"
5. 推送: git push
6. 简要说明你做了什么

注意:
- 不要破坏现有功能
- 测试必须全部通过才能提交
- 如果任务需要修改多个文件，确保一致性"""

    # 写入任务 prompt 文件
    prompt_path = PROJECT / ".planning" / "current-task.md"
    write_file(prompt_path, task_prompt)

    log(f"任务 prompt 已写入: {prompt_path}", GREEN)
    log(f"AI 代理可以读取此文件来执行任务", DIM)

    return False


# ── CLI ──

def main():
    os.chdir(PROJECT)

    if "--status" in sys.argv or "-s" in sys.argv:
        show_status()
    elif "--dry-run" in sys.argv or "-d" in sys.argv:
        run_loop(dry_run=True)
    else:
        done = run_loop(dry_run=False)
        if not done:
            show_status()


if __name__ == "__main__":
    main()
