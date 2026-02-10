import json
import sys
import time
import urllib.request

OWNER = "liumem1976"
REPO = "Apartment"
BRANCH = "fix/pr-a-model-alignment-auto"
POLL_INTERVAL = 15

URL = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs?branch={BRANCH}&per_page=5"


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "ci-poller"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def find_latest_run(data):
    if not data.get("workflow_runs"):
        return None
    # take the first run
    return data["workflow_runs"][0]


def main():
    print("Polling GitHub Actions for branch", BRANCH)
    while True:
        try:
            data = fetch()
        except Exception as e:
            print("Fetch error:", e)
            time.sleep(POLL_INTERVAL)
            continue

        run = find_latest_run(data)
        if not run:
            print("No workflow runs found yet. Sleeping...")
            time.sleep(POLL_INTERVAL)
            continue

        status = run.get("status")
        conclusion = run.get("conclusion")
        html_url = run.get("html_url")
        print(
            f"Run id={run.get('id')} status={status} conclusion={conclusion} url={html_url}"
        )

        if status == "completed":
            if conclusion == "success":
                print("CI succeeded")
                sys.exit(0)
            else:
                print("CI completed with conclusion:", conclusion)
                sys.exit(2)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
