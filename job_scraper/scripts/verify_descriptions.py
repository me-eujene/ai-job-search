"""
Print description coverage per source from the last scraper run.
Usage: uv run python job_scraper/scripts/verify_descriptions.py
"""
import json, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

with open("job_scraper/last_run.json", encoding="utf-8") as f:
    data = json.load(f)

by_source = defaultdict(lambda: {"total": 0, "ok": 0})
for j in data["jobs"]:
    src = j.get("source", "unknown")
    by_source[src]["total"] += 1
    if j.get("description_ok"):
        by_source[src]["ok"] += 1

print(f"Run: {data.get('run_id', 'unknown')}")
print(f"{'Source':<20} {'Total':>6} {'With desc':>10} {'Coverage':>10}")
print("-" * 50)
for src, counts in sorted(by_source.items()):
    pct = counts["ok"] / counts["total"] * 100 if counts["total"] else 0
    print(f"{src:<20} {counts['total']:>6} {counts['ok']:>10} {pct:>9.0f}%")
total_jobs = sum(c["total"] for c in by_source.values())
total_ok = sum(c["ok"] for c in by_source.values())
overall = total_ok / total_jobs * 100 if total_jobs else 0
print("-" * 50)
print(f"{'TOTAL':<20} {total_jobs:>6} {total_ok:>10} {overall:>9.0f}%")
