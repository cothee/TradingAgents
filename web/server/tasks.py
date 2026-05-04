# web/server/tasks.py
import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from web.server.schemas import TaskInfo, TaskStatus
from tradingagents.dataflows.ticker_detect import detect_market, normalize_ticker

logger = logging.getLogger(__name__)

# Concurrency limit for analysis tasks
MAX_CONCURRENT = 20
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)
_queue: asyncio.Queue = asyncio.Queue()


def _store() -> Dict[str, dict]:
    """Get the task store from the current app state (injected at runtime)."""
    from web.server.main import app
    return getattr(app.state, "task_store", {})


def _events() -> Dict[str, asyncio.Queue]:
    """Get the event queues dict."""
    from web.server.main import app
    return getattr(app.state, "event_queues", {})


# A-share valid code prefixes (format-based validation, no network required)
_A_SHARE_PREFIXES = {"600", "601", "603", "605", "688", "000", "001", "002", "300", "301"}


def _validate_a_share_format(ticker: str) -> bool:
    """Validate A-share code by prefix rules. No network call."""
    t = ticker.strip()
    if len(t) != 6 or not t.isdigit():
        return False
    return t[:3] in _A_SHARE_PREFIXES


def find_duplicate_task(ticker: str, analysis_date: str) -> Optional[dict]:
    """Check if there's an existing non-failed task for the same ticker + date."""
    ticker_normalized = normalize_ticker(ticker).strip()
    for task in _store().values():
        if normalize_ticker(task["ticker"]).strip() == ticker_normalized and task["analysis_date"] == analysis_date:
            if task["status"] not in (TaskStatus.FAILED,):
                return task
    return None


def validate_ticker(ticker: str) -> Optional[str]:
    """Validate ticker symbol. Returns error message if invalid or unsupported."""
    t = normalize_ticker(ticker)
    market = detect_market(ticker)

    if market == "a_share":
        # Format-based validation (instant, no network call)
        if not _validate_a_share_format(t):
            return f"股票代码 '{ticker}' 不存在，请检查后重试"
        return None

    # US stock validation (existing logic)
    import yfinance as yf
    try:
        info = yf.Ticker(t).info
        if not info.get("symbol"):
            return f"美股代码 '{ticker}' 不存在，请检查后重试"
        return None
    except Exception as e:
        return f"验证股票代码失败: {e}"


def create_task(ticker: str, analysis_date: str, mode: str) -> TaskInfo:
    """Create a new task record and enqueue it."""
    task_id = uuid.uuid4().hex[:12]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    task = {
        "task_id": task_id,
        "ticker": ticker.upper().strip(),
        "analysis_date": analysis_date,
        "status": TaskStatus.QUEUED,
        "created_at": now,
        "completed_at": None,
        "error": None,
        "mode": mode,
    }
    _store()[task_id] = task
    _events()[task_id] = asyncio.Queue()
    _queue.put_nowait(task_id)
    logger.info("Task %s created: %s on %s", task_id, ticker, analysis_date)
    return TaskInfo(**task)


def get_task(task_id: str) -> Optional[TaskInfo]:
    """Get task info by ID."""
    task = _store().get(task_id)
    if task is None:
        return None
    return TaskInfo(**task)


ACTIVE_STATUSES = (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RUNNING)
TERMINAL_STATUSES = (TaskStatus.COMPLETED, TaskStatus.FAILED)


def list_tasks(limit: int = 50) -> list[TaskInfo]:
    """List all tasks, newest first, limited."""
    tasks = sorted(_store().values(), key=lambda t: t["created_at"], reverse=True)
    return [TaskInfo(**t) for t in tasks[:limit]]


def list_latest_tasks() -> list[TaskInfo]:
    """For each ticker, keep at most 1 active task + 1 completed task.

    - Active (pending/queued/running): only the latest one per ticker
    - Completed/failed: only the latest one per ticker
    - Failed tasks without a report are excluded
    """
    latest_active: Dict[str, dict] = {}
    latest_terminal: Dict[str, dict] = {}

    for task in _store().values():
        ticker = task["ticker"]

        # Exclude failed tasks that have no report
        if task["status"] == TaskStatus.FAILED and not task.get("report_path"):
            continue

        if task["status"] in ACTIVE_STATUSES:
            existing = latest_active.get(ticker)
            if existing is None or task["created_at"] > existing["created_at"]:
                latest_active[ticker] = task
        elif task["status"] in TERMINAL_STATUSES:
            existing = latest_terminal.get(ticker)
            if existing is None or task["created_at"] > existing["created_at"]:
                latest_terminal[ticker] = task

    all_tasks = list(latest_active.values()) + list(latest_terminal.values())
    all_tasks.sort(key=lambda t: t["created_at"], reverse=True)
    return [TaskInfo(**t) for t in all_tasks]


def get_event_queue(task_id: str) -> Optional[asyncio.Queue]:
    """Get the SSE event queue for a task."""
    return _events().get(task_id)


def _is_valid_report(report_dir: Path) -> bool:
    """Check if a report directory has a meaningful complete_report.md."""
    complete_report = report_dir / "complete_report.md"
    if not complete_report.exists():
        return False
    content = complete_report.read_text(encoding="utf-8").strip()
    if not content:
        return False
    # Reject reports that only contain API key errors (legacy bug)
    if "API密钥" in content and len(content) < 500:
        return False
    return True


def _cleanup_empty_report(ticker_dir: Path, date_dir: Path):
    """Remove an empty/invalid report directory from disk."""
    try:
        import shutil
        shutil.rmtree(date_dir, ignore_errors=True)
        # Remove ticker dir if now empty
        if ticker_dir.exists() and not any(ticker_dir.iterdir()):
            shutil.rmtree(ticker_dir, ignore_errors=True)
        logger.info("Cleaned up empty report: %s/%s", ticker_dir.name, date_dir.name)
    except Exception as e:
        logger.warning("Failed to cleanup %s: %s", date_dir, e)


def load_history_from_disk(task_store: Dict[str, dict]):
    """Scan reports/ and reports/logs/ directories and rebuild task history."""
    project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # 1. Scan local reports/ directory (CLI format: TICKER_YYYYMMDD_HHMMSS)
    reports_dir = project_root / "reports"
    if reports_dir.exists():
        for entry in sorted(reports_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not entry.is_dir():
                continue
            if entry.name == "logs":
                continue
            parts = entry.name.rsplit("_", 2)
            if len(parts) < 3:
                continue
            ticker = parts[0]
            try:
                date_str = f"{parts[1]}-{parts[2][:2]}-{parts[2][2:4]}"
                time_str = f"{parts[2][:2]}:{parts[2][2:4]}:{parts[2][4:]}"
            except (IndexError, ValueError):
                continue
            report_path = entry / "reports" if (entry / "reports").exists() else entry
            # Skip invalid reports
            if not _is_valid_report(report_path):
                continue
            task_id = entry.name.lower().replace("_", "")
            task_store[task_id] = {
                "task_id": task_id,
                "ticker": ticker,
                "analysis_date": date_str,
                "status": TaskStatus.COMPLETED,
                "created_at": f"{date_str} {time_str}",
                "completed_at": f"{date_str} {time_str}",
                "error": None,
                "mode": "streaming",
                "report_path": str(report_path),
            }

    # 2. Scan web reports directory (reports/logs/TICKER/DATE/reports/)
    logs_dir = project_root / "reports" / "logs"
    if logs_dir.exists():
        for ticker_dir in sorted(logs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not ticker_dir.is_dir():
                continue
            for date_dir in sorted(ticker_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if not date_dir.is_dir():
                    continue
                report_dir = date_dir / "reports"
                if not report_dir.exists():
                    _cleanup_empty_report(ticker_dir, date_dir)
                    continue
                # Skip invalid reports (empty or API key errors)
                if not _is_valid_report(report_dir):
                    _cleanup_empty_report(ticker_dir, date_dir)
                    continue
                ticker = ticker_dir.name.upper()
                date_str = date_dir.name
                task_id = f"{ticker}_{date_str}".lower()
                complete_report = report_dir / "complete_report.md"
                mtime = datetime.fromtimestamp(complete_report.stat().st_mtime)
                completed_at = mtime.strftime("%Y-%m-%d %H:%M:%S")
                task_store[task_id] = {
                    "task_id": task_id,
                    "ticker": ticker,
                    "analysis_date": date_str,
                    "status": TaskStatus.COMPLETED,
                    "created_at": completed_at,
                    "completed_at": completed_at,
                    "error": None,
                    "mode": "streaming",
                    "report_path": str(report_dir),
                }

    logger.info("Loaded %d historical tasks from disk", len(task_store))
