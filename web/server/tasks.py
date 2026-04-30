# web/server/tasks.py
import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from web.server.schemas import TaskInfo, TaskStatus

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


def find_duplicate_task(ticker: str, analysis_date: str) -> Optional[dict]:
    """Check if there's an existing non-failed task for the same ticker + date."""
    ticker_upper = ticker.upper().strip()
    for task in _store().values():
        if task["ticker"].upper().strip() == ticker_upper and task["analysis_date"] == analysis_date:
            if task["status"] not in (TaskStatus.FAILED,):
                return task
    return None


def validate_ticker(ticker: str) -> Optional[str]:
    """Validate ticker symbol. Returns error message if invalid or unsupported."""
    import yfinance as yf
    t = ticker.upper().strip()

    # Detect A-share tickers (6-digit codes or .SS/.SZ suffix)
    is_a_share = (
        t.endswith(".SS") or t.endswith(".SZ") or
        t.endswith(".SHA") or t.endswith(".SHE") or
        (len(t) == 6 and t.isdigit())
    )
    if is_a_share:
        return "暂不支持 A 股分析，目前仅支持美股"

    # Validate US stock via yfinance
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
    """
    latest_active: Dict[str, dict] = {}
    latest_terminal: Dict[str, dict] = {}

    for task in _store().values():
        ticker = task["ticker"]
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


def load_history_from_disk(task_store: Dict[str, dict]):
    """Scan reports/ and reports/logs/ directories and rebuild task history."""
    project_root = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    # 1. Scan local reports/ directory (CLI format: TICKER_YYYYMMDD_HHMMSS)
    reports_dir = project_root / "reports"
    if reports_dir.exists():
        for entry in sorted(reports_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not entry.is_dir():
                continue
            # Skip the logs/ subdirectory — handled separately
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
                "report_path": str(entry / "reports") if (entry / "reports").exists() else str(entry),
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
                    continue
                ticker = ticker_dir.name.upper()
                date_str = date_dir.name  # e.g. 2026-04-30
                task_id = f"{ticker}_{date_str}".lower()
                # Determine completed_at from complete_report.md mtime (most reliable)
                complete_report = report_dir / "complete_report.md"
                if complete_report.exists():
                    mtime = datetime.fromtimestamp(complete_report.stat().st_mtime)
                    completed_at = mtime.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    completed_at = f"{date_str} 00:00:00"
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
