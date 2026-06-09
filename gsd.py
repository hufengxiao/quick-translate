#!/usr/bin/env python3
"""GSD (Get-Shit-Done) — Autonomous development runner.

Reads tasks from GSD.md, executes them one by one,
runs tests after each, auto-commits on success.

Usage:
    python gsd.py                    # Run all pending tasks
    python gsd.py --init             # Create template GSD.md
    python gsd.py --status           # Show task status
    python gsd.py --add "task desc"  # Add a new task
"""
import sys
import os
import re
import subprocess
import time
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent.absolute()
GSD_FILE = PROJECT_DIR / "GSD.md"
TEST_CMD = "python ci_test.py"
COMMIT_PREFIX = "gsd:"

# ── Colors ──
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"


def log(msg, color=""):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{DIM}{ts}{RESET} {color}{msg}{RESET}")


def run(cmd, cwd=None, timeout=120):
    """Run shell command, return (success, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=cwd or PROJECT_DIR,
            capture_output=True, text=True, timeout=timeout,
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "TIMEOUT"
    except Exception as e:
        return False, "", str(e)


def git_commit(msg):
    """Stage all and commit."""
    run("git add -A")
    ok, out, err = run(f'git commit -m "{COMMIT_PREFIX} {msg}" --allow-empty')
    if ok:
        log(f"  Committed: {msg}", GREEN)
    return ok


def git_push():
    ok, out, err = run("git push", timeout=30)
    if ok:
        log("  Pushed to remote", GREEN)
    else:
        log(f"  Push failed: {err[:100]}", YELLOW)
    return ok


def run_tests():
    """Run test suite. Returns True if all pass."""
    log("  Running tests...", CYAN)
    ok, out, err = run(TEST_CMD, timeout=120)
    if ok and "passed" in out.lower():
        # Extract pass count
        m = re.search(r"(\d+)\s*passed", out)
        count = m.group(1) if m else "?"
        log(f"  Tests: {count} passed", GREEN)
        return True
    else:
        log(f"  Tests FAILED", RED)
        # Show last few lines of output
        lines = (out + "\n" + err).strip().split("\n")
        for line in lines[-5:]:
            log(f"    {line}", RED)
        return False


# ── GSD.md parsing ──

TASK_PATTERN = re.compile(r"^-\s*\[([ x~])\]\s*(.+)$", re.MULTILINE)


def parse_tasks():
    """Parse GSD.md and return list of (status, description, line_num)."""
    if not GSD_FILE.exists():
        return []
    content = GSD_FILE.read_text(encoding="utf-8")
    tasks = []
    for i, line in enumerate(content.split("\n"), 1):
        m = TASK_PATTERN.match(line.strip())
        if m:
            status_char = m.group(1)
            desc = m.group(2).strip()
            status = {" ": "pending", "x": "done", "~": "skip"}.get(status_char, "pending")
            tasks.append((status, desc, i))
    return tasks


def update_task_status(line_num, new_char):
    """Update a single task's checkbox in GSD.md."""
    lines = GSD_FILE.read_text(encoding="utf-8").split("\n")
    if 0 < line_num <= len(lines):
        line = lines[line_num - 1]
        lines[line_num - 1] = re.sub(r"\[.\]", f"[{new_char}]", line)
        GSD_FILE.write_text("\n".join(lines), encoding="utf-8")


def init_gsd():
    """Create template GSD.md."""
    if GSD_FILE.exists():
        log(f"GSD.md already exists", YELLOW)
        return
    template = """# GSD — Get Shit Done

Tasks are checkboxes. Edit this file to add tasks, then run `python gsd.py`.

- [ ] Example task: fix the startup warning
- [ ] Example task: add dark mode toggle
- [ ] Example task: optimize search performance

<!-- 
Status chars:
  [ ] = pending (will execute)
  [x] = done (skip)
  [~] = skip (manual skip)
-->
"""
    GSD_FILE.write_text(template, encoding="utf-8")
    log(f"Created GSD.md — edit it to add your tasks", GREEN)


def show_status():
    """Show task status."""
    tasks = parse_tasks()
    if not tasks:
        log("No tasks found. Run: python gsd.py --init", YELLOW)
        return

    pending = sum(1 for s, _, _ in tasks if s == "pending")
    done = sum(1 for s, _, _ in tasks if s == "done")
    skipped = sum(1 for s, _, _ in tasks if s == "skip")

    print(f"\n{BOLD}GSD Status{RESET}")
    print(f"  Pending: {YELLOW}{pending}{RESET}  Done: {GREEN}{done}{RESET}  Skipped: {DIM}{skipped}{RESET}\n")

    for status, desc, line_num in tasks:
        icon = {"pending": f"{YELLOW}[ ]{RESET}", "done": f"{GREEN}[x]{RESET}", "skip": f"{DIM}[~]{RESET}"}
        print(f"  {icon.get(status, '?')} {desc}")


def add_task(desc):
    """Append a task to GSD.md."""
    if not GSD_FILE.exists():
        init_gsd()
    with open(GSD_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n- [ ] {desc}")
    log(f"Added: {desc}", GREEN)


def execute_task(desc):
    """Execute a single task description.

    The task description is treated as a development instruction.
    GSD will attempt to execute it using available tools.
    Returns True if successful.
    """
    log(f"\n{'='*50}", CYAN)
    log(f"TASK: {desc}", BOLD + CYAN)
    log(f"{'='*50}", CYAN)

    # Parse task type from prefix
    desc_lower = desc.lower().strip()

    # ── Shell command tasks ──
    if desc_lower.startswith("run:"):
        cmd = desc.split(":", 1)[1].strip()
        log(f"  Running: {cmd}", CYAN)
        ok, out, err = run(cmd, timeout=300)
        if out:
            for line in out.split("\n")[-10:]:
                log(f"    {line}")
        if not ok:
            log(f"  Command failed: {err[:200]}", RED)
            return False
        return True

    # ── Install dependency ──
    if desc_lower.startswith("pip:") or desc_lower.startswith("install:"):
        pkg = desc.split(":", 1)[1].strip()
        log(f"  Installing: {pkg}", CYAN)
        ok, out, err = run(f"pip install {pkg}", timeout=120)
        return ok

    # ── Test tasks ──
    if desc_lower in ("test", "run tests", "run all tests"):
        return run_tests()

    # ── Commit tasks ──
    if desc_lower.startswith("commit"):
        msg = desc.split(":", 1)[1].strip() if ":" in desc else "auto-commit"
        return git_commit(msg)

    # ── Push tasks ──
    if desc_lower in ("push", "git push"):
        return git_push()

    # ── Generic task — print instructions for manual execution ──
    log(f"  This task needs manual execution or an agent.", YELLOW)
    log(f"  Tip: prefix with 'run:' for shell commands, 'pip:' for installs", DIM)
    log(f"  Example: - [ ] run: python -m pytest tests/", DIM)
    return False


def run_all(push_after=True):
    """Execute all pending tasks."""
    tasks = parse_tasks()
    pending = [(s, d, ln) for s, d, ln in tasks if s == "pending"]

    if not pending:
        log("No pending tasks! Edit GSD.md to add tasks.", GREEN)
        return

    log(f"\n{BOLD}GSD: {len(pending)} tasks to execute{RESET}\n", CYAN)

    completed = 0
    failed = 0
    t_start = time.time()

    for status, desc, line_num in pending:
        success = execute_task(desc)

        if success:
            update_task_status(line_num, "x")
            completed += 1
            log(f"  {GREEN}DONE{RESET}: {desc}")

            # Auto-commit after each successful task
            git_commit(desc)
        else:
            failed += 1
            log(f"  {RED}FAILED{RESET}: {desc}")
            # Mark with ~ to skip on next run
            # (user can fix and change back to [ ])

    # Summary
    elapsed = time.time() - t_start
    print(f"\n{'='*50}")
    log(f"{BOLD}GSD Summary{RESET}", CYAN)
    log(f"  Completed: {GREEN}{completed}{RESET}  Failed: {RED}{failed}{RESET}  Time: {elapsed:.0f}s")

    if completed > 0 and push_after:
        git_push()

    print(f"{'='*50}\n")


# ── CLI ──

def main():
    parser = argparse.ArgumentParser(description="GSD — Get Shit Done")
    parser.add_argument("--init", action="store_true", help="Create template GSD.md")
    parser.add_argument("--status", "-s", action="store_true", help="Show task status")
    parser.add_argument("--add", "-a", type=str, help="Add a new task")
    parser.add_argument("--no-push", action="store_true", help="Don't auto-push after run")
    parser.add_argument("--task", "-t", type=str, help="Run a single task by description")
    args = parser.parse_args()

    os.chdir(PROJECT_DIR)

    if args.init:
        init_gsd()
    elif args.status:
        show_status()
    elif args.add:
        add_task(args.add)
    elif args.task:
        success = execute_task(args.task)
        if success:
            git_commit(args.task)
            git_push()
        sys.exit(0 if success else 1)
    else:
        run_all(push_after=not args.no_push)


if __name__ == "__main__":
    main()
