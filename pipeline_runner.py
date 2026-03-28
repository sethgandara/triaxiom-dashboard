# pipeline_runner.py - Orchestrates all fetchers
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

DATA = Path("data")
DATA.mkdir(exist_ok=True)
LOG = DATA / "pipeline_log.json"

SCRIPTS = [
    ("etf_proxies",  "data/fetchers/etf_proxies.py",   DATA / "etf_daily.csv"),
    ("btop50",       "data/fetchers/btop50.py",         DATA / "btop50_monthly.csv"),
    ("barclay_cta",  "data/fetchers/barclay_cta.py",    DATA / "barclay_cta_current.csv"),
    ("sg_cta",       "data/fetchers/sg_cta.py",         DATA / "sg_cta_spot.csv"),
]

records = []
print("=" * 60)
print(f"Triaxiom Benchmark Pipeline - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 60)

for source, script, out_path in SCRIPTS:
    print(f"Running {source}...")
    try:
        result = subprocess.run(
            [sys.executable, script],
            capture_output=True, text=True, timeout=120,
        )
        status = "ok" if result.returncode == 0 else "error"
        rows = int(pd.read_csv(out_path).shape[0]) if out_path.exists() else 0
        records.append({
            "source": source, "status": status,
            "rows_fetched": rows,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "output": result.stdout.strip()[-800:],
            "error": result.stderr.strip()[-400:] if result.returncode != 0 else "",
        })
        icon = "OK" if status == "ok" else "ERR"
        print(f"  {icon} {source}: {status} ({rows} rows)")
        if result.stdout:
            for line in result.stdout.strip().split("\n")[:5]:
                print(f"    {line}")
        if result.returncode != 0 and result.stderr:
            print(f"    ERROR: {result.stderr.strip()[:300]}")
    except Exception as e:
        records.append({
            "source": source, "status": "error", "rows_fetched": 0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        })
        print(f"  ERR {source}: {e}")

LOG.write_text(json.dumps(records, indent=2))
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for r in records:
    icon = "OK " if r["status"] == "ok" else "ERR"
    print(f"{icon} {r['source']:15s} {r['status']:8s} {r['rows_fetched']:5d} rows")

zero = [r["source"] for r in records if r["rows_fetched"] == 0]
if zero:
    print(f"WARNING: 0 rows from: {zero}")
else:
    print("All sources populated.")
