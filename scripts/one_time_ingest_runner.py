import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PYTHON = str(ROOT / ".venv" / "Scripts" / "python.exe")
SUMMARY_PATH = ROOT / "data" / "backups" / "one_time_ingest_summary.json"

os.environ["DATABASE_BACKEND"] = "postgresql"


def make_snippet(body: str) -> str:
    return (
        "import sys, os, json; "
        "from pathlib import Path; "
        "sys.path.insert(0, str(Path.cwd())); "
        "os.environ['DATABASE_BACKEND']='postgresql'; "
        + body
    )


STEPS = [
    (
        "fred_incremental",
        make_snippet(
            "from modules.ingestion import get_incremental_fetcher; "
            "from modules.data_series_config import get_all_fred_series; "
            "f=get_incremental_fetcher(); m=get_all_fred_series(); "
            "df=f.fetch_fred_batch_incremental(m); "
            "print(json.dumps({'series_attempted': len(m), 'series_with_new_rows': int(df.shape[1]) if hasattr(df,'shape') else 0, 'rows': int(df.shape[0]) if hasattr(df,'shape') else 0}))"
        ),
        600,
    ),
    (
        "yfinance_incremental",
        make_snippet(
            "from modules.ingestion import get_incremental_fetcher; "
            "from modules.data_series_config import get_all_yfinance_tickers; "
            "f=get_incremental_fetcher(); m=get_all_yfinance_tickers(); out=f.fetch_yfinance_batch_incremental(m); "
            "rows=sum(len(v) for v in out.values()); "
            "print(json.dumps({'tickers_attempted': len(m), 'tickers_with_new_rows': len(out), 'rows': int(rows)}))"
        ),
        600,
    ),
    (
        "bls_refresh",
        make_snippet("from modules.bls_data import refresh_bls_data; print(refresh_bls_data())"),
        300,
    ),
    (
        "census_refresh",
        make_snippet("from modules.census_data import refresh_census_data; print(refresh_census_data())"),
        300,
    ),
    (
        "eia_refresh",
        make_snippet("from modules.eia_data import refresh_eia_data; print(refresh_eia_data())"),
        300,
    ),
    (
        "imf_refresh",
        make_snippet("from modules.imf_data import refresh_imf_data; print(refresh_imf_data())"),
        300,
    ),
    (
        "oecd_refresh",
        make_snippet("from modules.oecd_data import refresh_oecd_data; print(refresh_oecd_data())"),
        300,
    ),
    (
        "worldbank_refresh",
        make_snippet("from modules.worldbank_data import refresh_worldbank_data; print(refresh_worldbank_data())"),
        300,
    ),
    (
        "cboe_vix_refresh",
        make_snippet("from modules.cboe_vix_data import refresh_cboe_vix_data; import json; print(json.dumps(refresh_cboe_vix_data(), default=str))"),
        300,
    ),
    (
        "ici_etf_refresh",
        make_snippet("from modules.ici_etf_data import refresh_ici_etf_data; import json; print(json.dumps(refresh_ici_etf_data(), default=str))"),
        300,
    ),
    (
        "sec_bulk_refresh",
        make_snippet(
            "from modules.database import get_monitored_tickers; "
            "from modules.sec_data_loader import refresh_sec_bulk_data; "
            "import json; t=get_monitored_tickers(); print(json.dumps(refresh_sec_bulk_data(tickers=t, force=True), default=str))"
        ),
        600,
    ),
    (
        "data_freshness",
        make_snippet(
            "from modules.database.queries import get_data_freshness; "
            "import json; print(json.dumps(get_data_freshness().to_dict(orient='records'), default=str))"
        ),
        120,
    ),
]


def parse_output(text: str):
    text = (text or "").strip()
    if not text:
        return None
    last_line = text.splitlines()[-1].strip()
    try:
        return json.loads(last_line)
    except Exception:
        try:
            return int(last_line)
        except Exception:
            return last_line


def main() -> int:
    results = {}

    for name, snippet, timeout_s in STEPS:
        try:
            proc = subprocess.run(
                [PYTHON, "-c", snippet],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env={**os.environ, "DATABASE_BACKEND": "postgresql"},
            )
            if proc.returncode == 0:
                results[name] = {
                    "status": "ok",
                    "result": parse_output(proc.stdout),
                }
            else:
                results[name] = {
                    "status": "error",
                    "returncode": proc.returncode,
                    "stderr": (proc.stderr or "")[-2000:],
                    "stdout": (proc.stdout or "")[-1000:],
                }
        except subprocess.TimeoutExpired:
            results[name] = {
                "status": "timeout",
                "timeout_seconds": timeout_s,
            }

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"wrote {SUMMARY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
