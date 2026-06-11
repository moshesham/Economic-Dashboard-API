"""Load options metrics and Greeks analytics into local database.

Usage:
  python scripts/load_options_data.py --tickers AAPL,MSFT,NVDA --max-expirations 4
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.features.options_metrics import OptionsMetricsCalculator
from modules.database import get_db_connection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load options metrics and Greeks into DB")
    parser.add_argument(
        "--tickers",
        type=str,
        default="AAPL,MSFT,NVDA",
        help="Comma-separated tickers (default: AAPL,MSFT,NVDA)",
    )
    parser.add_argument(
        "--max-expirations",
        type=int,
        default=3,
        help="Maximum expirations per ticker to fetch (default: 3)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]

    calc = OptionsMetricsCalculator()
    results = calc.batch_calculate(tickers=tickers, max_expirations=args.max_expirations)

    populated = {ticker: len(df) for ticker, df in results.items() if df is not None and not df.empty}

    print("Tickers requested:", tickers)
    print("Tickers stored:", populated)

    db = get_db_connection()
    options_counts = db.query(
        """
        SELECT ticker, COUNT(*) AS cnt, MAX(date) AS latest_date
        FROM options_data
        WHERE ticker IN ({})
        GROUP BY ticker
        ORDER BY ticker
        """.format(
            ", ".join(["?" for _ in tickers])
        ),
        tuple(tickers),
    )

    greeks_counts = db.query(
        """
        SELECT ticker, COUNT(*) AS cnt, MAX(date) AS latest_date
        FROM options_greeks_analytics
        WHERE ticker IN ({})
        GROUP BY ticker
        ORDER BY ticker
        """.format(
            ", ".join(["?" for _ in tickers])
        ),
        tuple(tickers),
    )

    print("options_data summary:")
    print(options_counts.to_string(index=False) if not options_counts.empty else "(no rows)")

    print("options_greeks_analytics summary:")
    print(greeks_counts.to_string(index=False) if not greeks_counts.empty else "(no rows)")


if __name__ == "__main__":
    main()
