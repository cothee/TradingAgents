import os
from datetime import datetime

_TRADINGAGENTS_HOME = os.path.join(os.path.expanduser("~"), ".tradingagents")

# Auto-detect user's local timezone as an IANA timezone name.
# Python's datetime gives ambiguous abbreviations like "CST" (could be China,
# US Central, or Cuba), so we resolve by UTC offset against known timezones.
def _detect_iana_timezone():
    now = datetime.now()
    local = now.astimezone()
    utc_offset = local.utcoffset().total_seconds()
    tz_abbrev = local.tzname()

    # If the name is already a valid IANA timezone (contains "/"), use it
    if "/" in tz_abbrev:
        return tz_abbrev

    # Fallback: find an IANA timezone with matching UTC offset.
    # Prefer the most common city for each offset.
    import pytz
    common_cities = [
        "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Taipei", "Asia/Singapore",
        "Asia/Tokyo", "Asia/Seoul", "Asia/Kolkata", "Asia/Dubai",
        "Asia/Bangkok", "Asia/Jakarta", "Asia/Manila", "Asia/Kuala_Lumpur",
        "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Moscow",
        "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
        "America/Sao_Paulo", "America/Toronto", "America/Mexico_City",
        "Australia/Sydney", "Pacific/Auckland",
        "Africa/Cairo", "Africa/Johannesburg", "Africa/Lagos",
        "UTC",
    ]
    for name in common_cities:
        tz = pytz.timezone(name)
        try:
            if tz.utcoffset(now).total_seconds() == utc_offset:
                return name
        except Exception:
            pass
    return "UTC"

_USER_TIMEZONE = _detect_iana_timezone()

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", os.path.join(_TRADINGAGENTS_HOME, "logs")),
    "data_cache_dir": os.getenv("TRADINGAGENTS_CACHE_DIR", os.path.join(_TRADINGAGENTS_HOME, "cache")),
    "memory_log_path": os.getenv("TRADINGAGENTS_MEMORY_LOG_PATH", os.path.join(_TRADINGAGENTS_HOME, "memory", "trading_memory.md")),
    # Optional cap on the number of resolved memory log entries. When set,
    # the oldest resolved entries are pruned once this limit is exceeded.
    # Pending entries are never pruned. None disables rotation entirely.
    "memory_log_max_entries": None,
    # LLM settings
    "llm_provider": "qwen",
    "deep_think_llm": "qwen3.6-plus",
    "quick_think_llm": "qwen3.6-plus",
    # When None, each provider's client falls back to its own default endpoint
    # (api.openai.com for OpenAI, generativelanguage.googleapis.com for Gemini, ...).
    # The CLI overrides this per provider when the user picks one. Keeping a
    # provider-specific URL here would leak (e.g. OpenAI's /v1 was previously
    # being forwarded to Gemini, producing malformed request URLs).
    "backend_url": None,
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Checkpoint/resume: when True, LangGraph saves state after each node
    # so a crashed run can resume from the last successful step.
    "checkpoint_enabled": False,
    # Output language for analyst reports and final decision
    # Internal agent debate stays in English for reasoning quality
    "output_language": "English",
    # User's local timezone: auto-detected from system clock, used to convert
    # the entered date to the market's local date (e.g. Beijing 2026-04-28
    # 10:00 → US Eastern 2026-04-27 22:00 for AAPL)
    "user_timezone": _USER_TIMEZONE,
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
}
