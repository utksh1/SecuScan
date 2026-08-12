import json, subprocess, sys, time

sys.path.insert(0, "/Users/Utkarsh/Desktop/Projects/SecuScan/scripts")
from issues_data import ISSUES, build_type_labels

# Post exactly first 100
LIMIT = 100
issues = ISSUES[:LIMIT]

DONE_FILE = "/Users/Utkarsh/Desktop/Projects/SecuScan/scripts/posted_issues.txt"

def load_done():
    try:
        with open(DONE_FILE) as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

done = load_done()

def post_issue(issue, idx):
    type_labels = build_type_labels(issue)
    labels = type_labels + [issue["area"], issue["priority"], issue["level"]]
    if issue.get("gfi"):
        labels.append("good first issue")
    title = f"[#{idx+1}] {issue['title']}"
    body = issue["body"]
    cmd = ["gh", "issue", "create", "--repo", "utksh1/SecuScan",
           "--title", title, "--body", body, "--label", ",".join(labels)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FAIL #{idx+1}: {issue['title']}\n{res.stderr}", file=sys.stderr)
        return False, res.stderr
    # extract URL from output
    url = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""
    print(f"OK #{idx+1}: {url}")
    with open(DONE_FILE, "a") as f:
        f.write(f"{idx+1}\t{issue['title']}\t{url}\n")
    return True, url

count_ok = 0
for i, iss in enumerate(issues):
    if str(i+1) in done:
        print(f"skip #{i+1} (already posted)")
        count_ok += 1
        continue
    ok, _ = post_issue(iss, i)
    if ok:
        count_ok += 1
    time.sleep(0.6)  # be gentle with rate limits

print(f"\nPosted {count_ok}/{LIMIT} issues.")
