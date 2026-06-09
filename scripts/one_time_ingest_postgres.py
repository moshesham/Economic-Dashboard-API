import os
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DATABASE_BACKEND"] = "postgresql"
logging.getLogger().setLevel(logging.ERROR)

results = {}


def run_step(name, fn):
    try:
        value = fn()
        results[name] = {"status": "ok", "result": value}
    except Exception as exc:
        results[name] = {"status": "error", "error": str(exc)}


from modules.ingestion import get_incremental_fetcher
from modules.data_series_config import get_all_fred_series, get_all_yfinance_tickers
from modules.bls_data import refresh_bls_data
from modules.census_data import refresh_census_data
from modules.eia_data import refresh_eia_data
from modules.imf_data import refresh_imf_data
from modules.oecd_data import refresh_oecd_data
from modules.worldbank_data import refresh_worldbank_data
from modules.cboe_vix_data import refresh_cboe_vix_data
from modules.ici_etf_data import refresh_ici_etf_data
from modules.sec_data_loader import refresh_sec_bulk_data
from modules.database import get_monitored_tickers
from modules.database.queries import get_data_freshness

fetcher = get_incremental_fetcher()
fred_map = get_all_fred_series()
yf_map = get_all_yfinance_tickers()


def run_fred():
    df = fetcher.fetch_fred_batch_incremental(fred_map)
    return {
        "series_attempted": len(fred_map),
        "series_with_new_rows": int(df.shape[1]) if hasattr(df, "shape") else 0,
        "rows": int(df.shape[0]) if hasattr(df, "shape") else 0,
    }


def run_yf():
    out = fetcher.fetch_yfinance_batch_incremental(yf_map)
    rows = sum(len(df) for df in out.values())
    return {
        "tickers_attempted": len(yf_map),
        "tickers_with_new_rows": len(out),
        "rows": int(rows),
    }


run_step("fred_incremental", run_fred)
run_step("yfinance_incremental", run_yf)
run_step("bls_refresh", lambda: refresh_bls_data())
run_step("census_refresh", lambda: refresh_census_data())
run_step("eia_refresh", lambda: refresh_eia_data())
run_step("imf_refresh", lambda: refresh_imf_data())
run_step("oecd_refresh", lambda: refresh_oecd_data())
run_step("worldbank_refresh", lambda: refresh_worldbank_data())
run_step("cboe_vix_refresh", lambda: refresh_cboe_vix_data())
run_step("ici_etf_refresh", lambda: refresh_ici_etf_data())
tracked = get_monitored_tickers()
run_step("sec_bulk_refresh", lambda: refresh_sec_bulk_data(tickers=tracked, force=True))
run_step("data_freshness", lambda: get_data_freshness().to_dict(orient="records"))

out = Path("data/backups/one_time_ingest_summary.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(results, default=str, indent=2), encoding="utf-8")
print(f"wrote {out}")
