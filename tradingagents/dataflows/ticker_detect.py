# tradingagents/dataflows/ticker_detect.py
"""Ticker format detection for multi-market support."""

# A-share suffixes that indicate exchange
_A_SHARE_SUFFIXES = {".SS", ".SZ", ".SHA", ".SHE"}


def detect_market(ticker: str) -> str:
    """Detect market from ticker symbol.

    Returns:
        'a_share' or 'us'
    """
    t = ticker.strip().upper()

    # Check suffix markers
    if any(t.endswith(s) for s in _A_SHARE_SUFFIXES):
        return "a_share"

    # Check pure 6-digit numeric (A-share)
    if len(t) == 6 and t.isdigit():
        return "a_share"

    return "us"


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker to a consistent format.

    A-share: keeps the 6-digit code as-is (e.g. '600519').
    US: uppercase (e.g. 'AAPL').
    """
    t = ticker.strip().upper()

    # If it has a known A-share suffix, keep it
    if any(t.endswith(s) for s in _A_SHARE_SUFFIXES):
        return t

    # Pure 6-digit A-share code
    if len(t) == 6 and t.isdigit():
        return t

    return t
