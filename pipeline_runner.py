# pipeline_runner.py - Orchestrates all fetchers
import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
DATA = Path("data")
DATA.mkdir(exist_ok=True)
LOG = DATA / "pipeline_log.json"
SCRIPTS = [
    ("etf_proxies",  "data/fetchers/etf_proxies.py",  DATA / "etf_daily.csv"),
    ("btop50",       "data/fetchers/btop50.py",       DATA / "btop50_monthly.csv"),
    ("barclay_cta",  "data/fetchers/barclay_cta.py",  DATA / "barclay_cta_current.csv"),
    ("sg_cta",       "data/fetchers/sg_cta.py",       DATA / "sg_cta_spot.csv"),
]
records = []
print("=" * 60)
for source, script, out_path in SCRIPTS:
    try:
        result = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=120)
        status = "ok" if result.returncode == 0 else "error"
        rows = int(pd.read_csv(out_path).shape[0]) if out_path.exists() else 0
        records.append({"source": source, "status": status, "rows_fetched": rows, "last_updated": datetime.now(timezone.utc).isoformat(), "output": result.stdout.strip()[-800:], "error": result.stderr.strip()[-400:] if result.returncode != 0 else ""})
        print(f"{'✅" if status=='ok' else '❌"} {source}")
    except Exception as e:
        records.append({"source": source, "status": "error", "rows_fetched": 0, "last_updated": datetime.now(timezone.utc).isoformat(), "error": str(e)})
LOG.write_text(json.dumps(records, indent=2))
print(f"Done. Log: {LOG}")
