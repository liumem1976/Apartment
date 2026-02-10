from pathlib import Path
import subprocess
import sys

out_dir = Path(".git-output")
out_dir.mkdir(exist_ok=True)

cmd = [sys.executable, "-m", "pytest", "tests/test_models.py", "-q"]
print("Running:", " ".join(cmd))
proc = subprocess.run(cmd, capture_output=True, text=True)
output = proc.stdout
if proc.stderr:
    output += "\n=== STDERR ===\n" + proc.stderr

(out_dir / "pytest_models_run.txt").write_text(output, encoding="utf-8")
print("Wrote .git-output/pytest_models_run.txt, exitcode", proc.returncode)
sys.exit(proc.returncode)
