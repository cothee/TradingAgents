"""Market heatmap data fetchers with TTL caching and popular stocks ranking."""

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Predefined stock lists ──────────────────────────────────────────────

US_STOCKS: dict[str, list[dict]] = {
    "Tech": [
        {"ticker": "AAPL", "name": "Apple"},
        {"ticker": "MSFT", "name": "Microsoft"},
        {"ticker": "NVDA", "name": "NVIDIA"},
        {"ticker": "GOOGL", "name": "Alphabet"},
        {"ticker": "META", "name": "Meta"},
        {"ticker": "AMZN", "name": "Amazon"},
        {"ticker": "TSLA", "name": "Tesla"},
        {"ticker": "AMD", "name": "AMD"},
    ],
    "Finance": [
        {"ticker": "JPM", "name": "JPMorgan"},
        {"ticker": "BAC", "name": "Bank of America"},
        {"ticker": "GS", "name": "Goldman Sachs"},
        {"ticker": "V", "name": "Visa"},
    ],
    "Healthcare": [
        {"ticker": "JNJ", "name": "Johnson & Johnson"},
        {"ticker": "UNH", "name": "UnitedHealth"},
        {"ticker": "PFE", "name": "Pfizer"},
        {"ticker": "LLY", "name": "Eli Lilly"},
    ],
    "Consumer": [
        {"ticker": "WMT", "name": "Walmart"},
        {"ticker": "KO", "name": "Coca-Cola"},
        {"ticker": "PEP", "name": "PepsiCo"},
        {"ticker": "MCD", "name": "McDonald's"},
    ],
    "Energy": [
        {"ticker": "XOM", "name": "ExxonMobil"},
        {"ticker": "CVX", "name": "Chevron"},
        {"ticker": "COP", "name": "ConocoPhillips"},
    ],
}

A_SHARE_STOCKS: dict[str, list[dict]] = {
    "消费": [
        {"ticker": "600519", "name": "贵州茅台"},
        {"ticker": "000858", "name": "五粮液"},
        {"ticker": "600809", "name": "山西汾酒"},
        {"ticker": "000568", "name": "泸州老窖"},
    ],
    "金融": [
        {"ticker": "601318", "name": "中国平安"},
        {"ticker": "600036", "name": "招商银行"},
        {"ticker": "601166", "name": "兴业银行"},
        {"ticker": "600000", "name": "浦发银行"},
    ],
    "科技": [
        {"ticker": "000063", "name": "中兴通讯"},
        {"ticker": "688981", "name": "中芯国际"},
        {"ticker": "002415", "name": "海康威视"},
        {"ticker": "002594", "name": "比亚迪"},
    ],
    "医药": [
        {"ticker": "600276", "name": "恒瑞医药"},
        {"ticker": "300760", "name": "迈瑞医疗"},
        {"ticker": "000538", "name": "云南白药"},
        {"ticker": "603259", "name": "药明康德"},
    ],
    "新能源": [
        {"ticker": "300750", "name": "宁德时代"},
        {"ticker": "601012", "name": "隆基绿能"},
        {"ticker": "600438", "name": "通威股份"},
        {"ticker": "002129", "name": "TCL中环"},
    ],
}


# ── TTL Cache ───────────────────────────────────────────────────────────

class HeatmapCache:
    """Simple TTL cache for heatmap data."""

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._data: Optional[dict] = None
        self._timestamp: float = 0

    def get(self) -> Optional[dict]:
        if self._data is not None and (time.time() - self._timestamp) < self.ttl:
            return self._data
        return None

    def set(self, data: dict[str, Any]):
        self._data = data
        self._timestamp = time.time()


heatmap_cache = HeatmapCache(ttl=300)


# ── Fetch heatmap data ──────────────────────────────────────────────────

def _fetch_a_share_data() -> dict[str, list[dict]]:
    """Fetch real-time A-share quotes via AKShare."""
    import akshare as ak

    try:
        df = ak.stock_zh_a_spot_em()
        # Build a lookup map: code -> {name, change_pct, price}
        lookup: dict[str, dict] = {}
        for _, row in df.iterrows():
            code = row.get("代码", "")
            lookup[code] = {
                "name": row.get("名称", ""),
                "change_pct": float(row["涨跌幅"]) if row["涨跌幅"] is not None else 0.0,
                "price": row.get("最新价", "-"),
            }
    except Exception as e:
        logger.warning("Failed to fetch A-share spot data: %s", e)
        lookup = {}

    result: dict[str, list[dict]] = {}
    for sector, stocks in A_SHARE_STOCKS.items():
        sector_stocks = []
        for s in stocks:
            info = lookup.get(s["ticker"], {})
            sector_stocks.append({
                "ticker": s["ticker"],
                "name": info.get("name", s["name"]),
                "change_pct": info.get("change_pct", 0.0),
                "price": info.get("price", "-"),
            })
        result[sector] = sector_stocks

    return result


def _fetch_us_data() -> dict[str, list[dict]]:
    """Fetch US stock quotes via yfinance."""
    import yfinance as yf
    import pandas as pd

    all_tickers = [s["ticker"] for stocks in US_STOCKS.values() for s in stocks]

    try:
        # Download 2 days of data to calculate daily change
        data = yf.download(all_tickers, period="2d", group_by="ticker", progress=False, auto_adjust=True)

        if isinstance(data.columns, pd.MultiIndex):
            # MultiIndex columns: (ticker, field)
            def get_close(ticker: str) -> pd.Series:
                return data[ticker]["Close"].dropna()
        else:
            # Single ticker case (shouldn't happen with multi-ticker download)
            def get_close(ticker: str) -> pd.Series:
                return data["Close"].dropna()
    except Exception as e:
        logger.warning("Failed to download US stock data: %s", e)
        return {
            sector: [{"ticker": s["ticker"], "name": s["name"], "change_pct": 0.0, "price": "-"} for s in stocks]
            for sector, stocks in US_STOCKS.items()
        }

    result: dict[str, list[dict]] = {}
    for sector, stocks in US_STOCKS.items():
        sector_stocks = []
        for s in stocks:
            t = s["ticker"]
            try:
                close = get_close(t)
                if len(close) >= 2:
                    prev = close.iloc[-2]
                    curr = close.iloc[-1]
                    pct = round((curr - prev) / prev * 100, 2) if prev else 0.0
                    price = round(curr, 2)
                elif len(close) == 1:
                    pct = 0.0
                    price = round(close.iloc[-1], 2)
                else:
                    pct = 0.0
                    price = "-"

                sector_stocks.append({
                    "ticker": t,
                    "name": s["name"],
                    "change_pct": pct,
                    "price": price,
                })
            except Exception as e:
                logger.warning("Failed to get data for %s: %s", t, e)
                sector_stocks.append({
                    "ticker": t,
                    "name": s["name"],
                    "change_pct": 0.0,
                    "price": "-",
                })
        result[sector] = sector_stocks

    return result


def fetch_heatmap_data() -> dict:
    """Fetch current day % change for all predefined stocks."""
    result = {"us": _fetch_us_data(), "a_share": _fetch_a_share_data()}
    return result


# ── Popular stocks ranking ──────────────────────────────────────────────

def get_popular_stocks_ranking(limit: int = 10) -> list[dict]:
    """Count analyses per ticker from task store and return top N."""
    from collections import Counter
    from web.server.tasks import _store

    ticker_counts: Counter = Counter()
    ticker_latest: dict[str, dict] = {}

    for task in _store().values():
        t = task["ticker"]
        ticker_counts[t] += 1
        existing = ticker_latest.get(t)
        if existing is None or task["created_at"] > existing["created_at"]:
            ticker_latest[t] = task

    ranked = []
    for ticker, count in ticker_counts.most_common(limit):
        latest = ticker_latest.get(ticker, {})
        ranked.append({
            "ticker": ticker,
            "analysis_count": count,
            "latest_status": latest.get("status", "unknown"),
            "latest_task_id": latest.get("task_id", ""),
            "latest_date": latest.get("analysis_date", ""),
        })

    return ranked
