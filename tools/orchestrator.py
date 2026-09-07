#!/usr/bin/env python3
"""Minimal Orchestrator CLI skeleton for V1.

This is intentionally small: it records tasks to `.orchestrator/tasks.jsonl`,
can run pytest, and prints simulated PR operations. It is a starting point.
"""
import argparse
import json
import os
import subprocess
import uuid
from datetime import datetime
from tools.orchestrator_core import Orchestrator

ROOT = os.path.dirname(os.path.dirname(__file__))
TASK_LOG = os.path.join(ROOT, ".orchestrator", "tasks.jsonl")

def ensure_dirs():
    d = os.path.dirname(TASK_LOG)
    os.makedirs(d, exist_ok=True)

def create_task(title, spec_file=None):
    ensure_dirs()
    task_id = str(uuid.uuid4())
    entry = {
        "task_id": task_id,
        "title": title,
        "spec_file": spec_file,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "transitions": [
            {"state": "proposed", "actor": "orchestrator", "at": datetime.utcnow().isoformat() + "Z"}
        ]
    }
    with open(TASK_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(task_id)
    return task_id

def run_checks(task_id):
    print(f"Running pytest for task {task_id}...")
    try:
        r = subprocess.run(["pytest", "-q"], cwd=ROOT, check=False, capture_output=True, text=True)
        reports_dir = os.path.join(ROOT, "reports", task_id)
        os.makedirs(reports_dir, exist_ok=True)
        with open(os.path.join(reports_dir, "pytest.txt"), "w", encoding="utf-8") as f:
            f.write(r.stdout + "\n" + r.stderr)
        print("Tests finished. Output written to reports/" + task_id)
        return r.returncode
    except FileNotFoundError:
        print("pytest not found in PATH. Skipping tests.")
        return 2

def apply_patch_simulated(task_id, diff_file):
    # This is a placeholder: real implementation would create a branch and push.
    branch = f"agent/{task_id}/patch"
    print(f"(simulated) Created branch {branch} from current HEAD and applied {diff_file}")
    pr_url = f"https://example.com/repo/pull/{task_id[:8]}"
    print(f"(simulated) Opened PR: {pr_url}")
    return branch, pr_url

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    c1 = sub.add_parser("create_task")
    c1.add_argument("--title", required=True)
    c1.add_argument("--spec-file")
    c1.add_argument("--description", default="")
    c1.add_argument("--created-by", default="system")

    c2 = sub.add_parser("run_checks")
    c2.add_argument("--task-id", required=True)

    c3 = sub.add_parser("apply_patch")
    c3.add_argument("--task-id", required=True)
    c3.add_argument("--diff-file", required=True)

    c4 = sub.add_parser("list_tasks")

    c5 = sub.add_parser("show_task")
    c5.add_argument("--task-id", required=True)

    c6 = sub.add_parser("transition_task")
    c6.add_argument("--task-id", required=True)
    c6.add_argument("--to", required=True)
    c6.add_argument("--actor", required=True)

    args = p.parse_args()
    if args.cmd == "create_task":
        orch = Orchestrator()
        task = orch.create_task(args.title, description=args.description, created_by=args.created_by)
        print(task.get("task_id"))
    elif args.cmd == "run_checks":
        run_checks(args.task_id)
    elif args.cmd == "apply_patch":
        apply_patch_simulated(args.task_id, args.diff_file)
    elif args.cmd == "list_tasks":
        orch = Orchestrator()
        tasks = orch.store.list_tasks()
        for t in tasks:
            print(t.get("task_id"), t.get("title"), t.get("status"))
    elif args.cmd == "show_task":
        orch = Orchestrator()
        t = orch.store.read_task(args.task_id)
        if t:
            print(json.dumps(t, indent=2))
        else:
            print("not found")
    elif args.cmd == "transition_task":
        orch = Orchestrator()
        res = orch.transition_task(args.task_id, args.to, args.actor)
        print(json.dumps(res, indent=2))
    else:
        p.print_help()

if __name__ == "__main__":
    main()
