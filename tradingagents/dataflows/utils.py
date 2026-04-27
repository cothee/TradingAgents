import os
import json
import pandas as pd
from datetime import date, timedelta, datetime
from typing import Annotated, Optional
import pytz

SavePathType = Annotated[str, "File path to save data. If None, data is not saved."]

# Ticker suffix → market timezone mapping
_MARKET_TIMEZONES = {
    # US markets (NYSE, NASDAQ)
    "": "America/New_York",
    # Hong Kong
    ".HK": "Asia/Hong_Kong",
    ".H": "Asia/Hong_Kong",
    # Tokyo
    ".T": "Asia/Tokyo",
    ".JP": "Asia/Tokyo",
    # Shanghai / Shenzhen
    ".SS": "Asia/Shanghai",
    ".SZ": "Asia/Shanghai",
    # London
    ".L": "Europe/London",
    ".IL": "Europe/London",
    # Toronto
    ".TO": "America/Toronto",
    ".V": "America/Toronto",
    # Frankfurt
    ".F": "Europe/Berlin",
    ".DE": "Europe/Berlin",
    # Sydney
    ".AX": "Australia/Sydney",
    # Korea
    ".KS": "Asia/Seoul",
    ".KQ": "Asia/Seoul",
    # Taiwan
    ".TW": "Asia/Taipei",
    # Singapore
    ".SI": "Asia/Singapore",
    # Paris
    ".PA": "Europe/Paris",
}


def convert_to_market_date(
    input_date: str,
    ticker: str,
    input_tz: str = "Asia/Shanghai",
) -> str:
    """Convert a user-entered date from their local timezone to the market's local date.

    Args:
        input_date: Date string in YYYY-MM-DD format, interpreted as the user's local date
        ticker: Ticker symbol (e.g. "AAPL", "0700.HK")
        input_tz: User's local timezone (default: Asia/Shanghai for Beijing time)

    Returns:
        Date string in YYYY-MM-DD format in the market's timezone.
        If the ticker's market cannot be determined, returns the input date unchanged.
    """
    try:
        # Determine market timezone from ticker
        ticker_upper = ticker.upper()
        market_tz_name = None
        for suffix, tz_name in _MARKET_TIMEZONES.items():
            if suffix and ticker_upper.endswith(suffix):
                market_tz_name = tz_name
                break
        if market_tz_name is None:
            market_tz_name = _MARKET_TIMEZONES[""]  # Default: US Eastern

        input_tz_obj = pytz.timezone(input_tz)
        market_tz_obj = pytz.timezone(market_tz_name)

        # Parse the input date as midnight in the user's timezone
        input_dt = datetime.strptime(input_date, "%Y-%m-%d")
        input_local = input_tz_obj.localize(input_dt)

        # Convert to market timezone
        market_local = input_local.astimezone(market_tz_obj)

        return market_local.strftime("%Y-%m-%d")
    except Exception:
        return input_date  # Fallback: return input unchanged

def save_output(data: pd.DataFrame, tag: str, save_path: SavePathType = None) -> None:
    if save_path:
        data.to_csv(save_path, encoding="utf-8")
        print(f"{tag} saved to {save_path}")


def get_current_date():
    return date.today().strftime("%Y-%m-%d")


def decorate_all_methods(decorator):
    def class_decorator(cls):
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value):
                setattr(cls, attr_name, decorator(attr_value))
        return cls

    return class_decorator


def get_next_weekday(date):

    if not isinstance(date, datetime):
        date = datetime.strptime(date, "%Y-%m-%d")

    if date.weekday() >= 5:
        days_to_add = 7 - date.weekday()
        next_weekday = date + timedelta(days=days_to_add)
        return next_weekday
    else:
        return date
