"""Create sample structured news sentiment fallback data."""

import pandas as pd


def create_sample_news_data() -> pd.DataFrame:
    rows = [
        ["AAPL", "Apple expands AI roadmap", "Apple announced a broader AI roadmap focused on productivity features.", "Reuters", "2026-06-08T10:30:00", "https://example.com/aapl-1", "Analysts viewed the announcement as supportive for medium-term demand."],
        ["AAPL", "Supply chain costs stabilize", "Recent supplier updates suggest stable component costs for next quarter.", "Bloomberg", "2026-06-07T14:15:00", "https://example.com/aapl-2", "Lower volatility in component pricing may support margins."],
        ["MSFT", "Cloud demand remains resilient", "Enterprise cloud demand stayed resilient across major verticals.", "CNBC", "2026-06-08T11:10:00", "https://example.com/msft-1", "Partner channel checks indicate stable renewal trends."],
        ["TSLA", "EV incentives under review", "Policy discussion around EV incentives introduced uncertainty.", "Financial Times", "2026-06-06T09:40:00", "https://example.com/tsla-1", "Short-term demand could fluctuate if policy changes are enacted."],
        ["NVDA", "Datacenter order momentum holds", "Datacenter customers continue prioritizing accelerated compute capacity.", "MarketWatch", "2026-06-08T08:20:00", "https://example.com/nvda-1", "Management commentary points to sustained AI infrastructure spending."],
    ]
    return pd.DataFrame(rows, columns=["symbol", "title", "description", "source", "published_at", "url", "content"])


if __name__ == "__main__":
    df = create_sample_news_data()
    df.to_csv("data/sample_news_sentiment_data.csv", index=False)
    print(f"Created sample news sentiment dataset with {len(df)} rows")
