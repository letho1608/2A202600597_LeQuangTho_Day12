import json, urllib.request, os, sys

TOKEN = os.environ.get("GITHUB_TOKEN", "")
H = {"Accept": "application/vnd.github.v3+json",
     "Authorization": f"token {TOKEN}",
     "User-Agent": "Python"}
BASE = "https://api.github.com/repos/letho1608/2A202600597_LeQuangTho_Day12/actions"

url = f"{BASE}/runs?per_page=1"
req = urllib.request.Request(url, headers=H)
d = json.load(urllib.request.urlopen(req))
r = d["workflow_runs"][0]
print(f"Run #{r['run_number']} {r['name']}: {r['status']} conclusion={r['conclusion']}")

url2 = f"{BASE}/runs/{r['id']}/jobs"
req2 = urllib.request.Request(url2, headers=H)
jd = json.load(urllib.request.urlopen(req2))
for j in jd["jobs"]:
    print(f"\nJob: {j['name']} ({j['conclusion']})")
    for s in j["steps"]:
        m = "OK" if s["conclusion"] == "success" else "FAIL" if s["conclusion"] == "failure" else "SKIP"
        print(f"  [{m}] {s['name']}")
    if j["conclusion"] == "failure":
        for s in j["steps"]:
            if s["conclusion"] == "failure":
                log_url = f"{BASE}/jobs/{j['id']}/logs"
                try:
                    log_req = urllib.request.Request(log_url, headers=H)
                    resp = urllib.request.urlopen(log_req)
                    log_data = resp.read().decode("utf-8", errors="replace")
                    lines = log_data.split("\n")
                    print(f"\n  -- Logs for '{s['name']}' (last 30 lines) --")
                    for line in lines[-30:]:
                        print(f"  | {line}")
                except Exception as e:
                    print(f"\n  ! Error fetching logs: {e}")
