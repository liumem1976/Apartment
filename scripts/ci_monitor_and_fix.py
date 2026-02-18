#!/usr/bin/env python3
"""
Lightweight CI log monitor + targeted fixer.

Checks the newest `gh_run_*.log` in the repo root and applies safe, idempotent
fixes for known CI failures:
- If an Alembic 'no such table' / index creation ordering issue is detected
  and `.github/workflows/ci.yml` contains an `alembic stamp` line, remove it
  and push a branch with the change.
- If a Pydantic/`FieldInfo` runtime traceback is found, save the traceback
  to `ci-tracebacks/` and push a branch containing the file for review.

This script is intentionally conservative: for changes that may affect
dependencies or larger behaviour it only collects evidence and creates a
branch with the artifacts rather than performing major automatic upgrades.
"""

import datetime
import glob
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, check=True, capture=False):
    if capture:
        return subprocess.run(
            cmd,
            shell=True,
            cwd=ROOT,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    else:
        return subprocess.run(cmd, shell=True, cwd=ROOT, check=check)


def find_latest_log():
    logs = sorted(
        glob.glob(str(ROOT / "gh_run_*.log")), key=os.path.getmtime, reverse=True
    )
    return Path(logs[0]) if logs else None


def git_branch_and_push(branch_name, paths, message):
    try:
        run("git fetch --all")
        run(f"git checkout -b {branch_name}")
    except Exception:
        # branch may already exist locally
        run(f"git checkout {branch_name}", check=False)
    run("git add " + " ".join(str(p) for p in paths))
    run(f'git commit -m "{message}"')
    run(f"git push -u origin {branch_name}")


def fix_alembic_stamp(workflow_path: Path):
    text = workflow_path.read_text(encoding="utf8")
    if "alembic stamp" not in text:
        print("no alembic stamp line found in workflow; nothing to do")
        return False
    new_lines = []
    changed = False
    for line in text.splitlines():
        if "alembic stamp" in line:
            changed = True
            continue
        new_lines.append(line)
    if changed:
        workflow_path.write_text("\n".join(new_lines) + "\n", encoding="utf8")
        print(f"removed alembic stamp lines from {workflow_path}")
    return changed


def main():
    latest = find_latest_log()
    if not latest:
        print("no gh_run_*.log files found")
        sys.exit(0)

    log = latest.read_text(encoding="utf8")
    print(f"analysing {latest.name}")

    # 1) Alembic ordering/index issue
    if "CREATE UNIQUE INDEX uq_meter_unit_kind_slot" in log or (
        "no such table" in log and "meter" in log
    ):
        wf = ROOT / ".github" / "workflows" / "ci.yml"
        if wf.exists():
            changed = fix_alembic_stamp(wf)
            if changed:
                branch = f"ci/auto-fix-alembic-stamp-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                git_branch_and_push(
                    branch,
                    [wf],
                    "ci: remove alembic stamp to ensure migrations run in order",
                )
                print(f"created and pushed branch {branch} with workflow fix")
                return

    # 2) FieldInfo runtime error evidence collection
    if "FieldInfo" in log and "in_" in log:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        out_dir = ROOT / "ci-tracebacks"
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / f"fieldinfo_traceback_{ts}.log"
        # extract a chunk around the first occurrence
        idx = log.find("FieldInfo")
        start = max(0, idx - 2000)
        end = min(len(log), idx + 20000)
        snippet = log[start:end]
        out_file.write_text(snippet, encoding="utf8")
        branch = f"ci/traceback-fieldinfo-{ts}"
        git_branch_and_push(
            branch, [out_file], "ci: add FieldInfo traceback for debugging"
        )
        print(f"Saved traceback to {out_file} and pushed branch {branch}")
        return

    # 3) Lint/format auto-fix suggestions: run local formatters and push if they change files
    if "Run ruff" in log or "Run black" in log or "Run isort" in log:
        print("running local formatters (ruff, isort, black) to apply fixes")
        changed = False
        try:
            run("python -m ruff format .", check=False)
            run("isort .", check=False)
            run("black .", check=False)
            # check git status
            res = run("git status --porcelain", capture=True)
            if res.stdout.strip():
                changed = True
                branch = f"ci/auto-format-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                git_branch_and_push(
                    branch, ["."], "chore: apply auto-formatters (ruff/isort/black)"
                )
                print(f"Applied formatters and pushed branch {branch}")
        except Exception as exc:
            print("formatter run failed:", exc)
        if changed:
            return

    print("no known auto-fix applied for this log")


if __name__ == "__main__":
    main()
