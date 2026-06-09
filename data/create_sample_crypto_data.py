"""Create sample crypto OHLCV data for offline mode."""

import pandas as pd


def create_sample_crypto_data() -> pd.DataFrame:
    rows = [
        ["Bitcoin", "2026-06-05", 104250.55, 32000000000],
        ["Bitcoin", "2026-06-06", 105120.41, 29800000000],
        ["Bitcoin", "2026-06-07", 103880.33, 30500000000],
        ["Bitcoin", "2026-06-08", 106240.12, 34100000000],
        ["Ethereum", "2026-06-05", 5230.48, 18200000000],
        ["Ethereum", "2026-06-06", 5281.12, 17100000000],
        ["Ethereum", "2026-06-07", 5174.89, 16500000000],
        ["Ethereum", "2026-06-08", 5322.03, 18900000000],
        ["Solana", "2026-06-05", 212.40, 4200000000],
        ["Solana", "2026-06-06", 216.15, 3980000000],
        ["Solana", "2026-06-07", 208.92, 3870000000],
        ["Solana", "2026-06-08", 219.03, 4420000000],
    ]
    df = pd.DataFrame(rows, columns=["symbol", "date", "close", "volume"])
    return df


if __name__ == "__main__":
    df = create_sample_crypto_data()
    df.to_csv("data/sample_crypto_data.csv", index=False)
    print(f"Created sample crypto dataset with {len(df)} rows")
