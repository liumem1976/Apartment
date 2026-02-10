import io
import os
import sys
import urllib.request
import zipfile

OWNER = "liumem1976"
REPO = "Apartment"


def fetch(run_id: str):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs/{run_id}/logs"
    out_dir = os.path.join(".git-output", f"ci_logs_{run_id}")
    os.makedirs(out_dir, exist_ok=True)
    try:
        # prefer an explicitly provided read token to avoid 403 when downloading logs
        token = os.environ.get("CI_READ_TOKEN") or os.environ.get("GITHUB_TOKEN")
        headers = {"User-Agent": "ci-log-fetcher"}
        if token:
            headers["Authorization"] = f"token {token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
    except Exception as e:
        print("Failed to download logs:", e)
        return 2

    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        z.extractall(out_dir)
    except Exception as e:
        print("Failed to extract zip:", e)
        return 3

    print("Logs extracted to", out_dir)

    keywords = ["ERROR", "Traceback", "FAILED", "failed", "AssertionError"]
    matches = []
    for root, _, files in os.walk(out_dir):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue
            for i, line in enumerate(lines):
                for kw in keywords:
                    if kw in line:
                        context = "".join(lines[max(0, i - 3) : min(len(lines), i + 3)])
                        matches.append((path, i + 1, kw, line.strip(), context))
    if not matches:
        print("No keyword matches found in logs.")
        return 0

    print("Found log matches:")
    for path, lineno, kw, line, ctx in matches[:10]:
        print("---")
        print(f"File: {path} Line: {lineno} Keyword: {kw}")
        print(line)
        print("Context:")
        print(ctx)

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: fetch_ci_logs.py <run_id>")
        sys.exit(1)
    run_id = sys.argv[1]
    sys.exit(fetch(run_id))
