"""Trigger the retraining workflow through the API (used by Windows Task Scheduler / cron).

  python scripts/run_retraining.py --trigger scheduled
Exit code is non-zero if the run errored, so schedulers can alert on failures.
"""
import argparse
import sys

import requests

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://localhost:8000")
p.add_argument("--trigger", choices=["manual", "drift", "scheduled"], default="scheduled")
p.add_argument("--dataset-id", type=int, default=None)
a = p.parse_args()

try:
    r = requests.post(f"{a.url}/api/retraining/run", json={"trigger": a.trigger, "dataset_id": a.dataset_id}, timeout=900)
except requests.RequestException as exc:
    sys.exit(f"Backend not reachable at {a.url}: {exc}")
if r.status_code != 200:
    sys.exit(f"Retraining request failed ({r.status_code}): {r.text}")
run = r.json()
print(f"Run #{run['id']} [{run['trigger']}] -> {run['status']}: {run['reason']}")
sys.exit(1 if run["status"] == "error" else 0)
