# web/server/api.py
import logging
from datetime import datetime
from pathlib import Path
import markdown

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse

from web.server.schemas import AnalyzeRequest, TaskInfo, TaskListResponse, TaskResponse, TaskStatus
from web.server.tasks import create_task, get_task, list_tasks, list_latest_tasks, get_event_queue, find_duplicate_task, validate_ticker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.post("/analyze", response_model=TaskResponse)
async def analyze(req: AnalyzeRequest):
    """Submit a new analysis task."""
    analysis_date = req.analysis_date or datetime.now().strftime("%Y-%m-%d")

    # 1. Validate ticker symbol
    error = validate_ticker(req.ticker)
    if error:
        return TaskResponse(
            task_id="",
            status=TaskStatus.FAILED,
            message=error,
        )

    # 2. Check for duplicate task
    existing = find_duplicate_task(req.ticker, analysis_date)
    if existing is not None:
        status_label = {
            TaskStatus.RUNNING: "正在分析中",
            TaskStatus.QUEUED: "排队中",
            TaskStatus.PENDING: "等待调度",
            TaskStatus.COMPLETED: "已完成",
        }.get(existing["status"], existing["status"])
        return TaskResponse(
            task_id=existing["task_id"],
            status=existing["status"],
            message=f"{req.ticker.upper()} · {analysis_date} {status_label}，请耐心等待",
        )

    task = create_task(req.ticker, analysis_date, req.mode.value)
    mode_label = "实时流式" if req.mode.value == "streaming" else "后台"
    return TaskResponse(
        task_id=task.task_id,
        status=task.status,
        message=f"分析任务已提交 ({mode_label})",
    )


@router.get("/task/{task_id}", response_model=TaskInfo)
async def get_task_info(task_id: str):
    """Get task status and metadata."""
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks_endpoint(limit: int = 50):
    """List recent tasks."""
    return TaskListResponse(tasks=list_tasks(limit))


@router.get("/tasks/recent")
async def recent_tasks():
    """Return latest task per ticker: 1 active + 1 completed."""
    return {"tasks": [t.model_dump() for t in list_latest_tasks()]}


@router.get("/task/{task_id}/events")
async def task_events(task_id: str):
    """SSE endpoint for real-time task events."""
    import json
    eq = get_event_queue(task_id)
    if eq is None:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        import asyncio
        task = get_task(task_id)
        if task:
            yield {
                "event": "task_status",
                "data": json.dumps(task.model_dump()),
            }

        while True:
            try:
                event = await asyncio.wait_for(eq.get(), timeout=30)
                logger.info("SSE event yielded: %s", event.get("event"))
                # Ensure data is JSON-encoded
                if "data" in event and not isinstance(event["data"], str):
                    event["data"] = json.dumps(event["data"])
                yield event
                if event["event"] in ("task_completed", "task_failed"):
                    break
            except asyncio.TimeoutError:
                # Heartbeat to keep connection alive
                yield {"event": "heartbeat", "data": json.dumps({"task_id": task_id})}

    return EventSourceResponse(event_generator())


@router.get("/task/{task_id}/report/{section:path}")
async def get_report_section(task_id: str, section: str):
    """Get a specific report file from disk."""
    from web.server.tasks import _store
    t = _store().get(task_id)
    report_path = (t or {}).get("report_path")

    if report_path:
        section_file = Path(report_path) / section
        if section_file.exists():
            content = section_file.read_text(encoding="utf-8")
            return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8")

    raise HTTPException(status_code=404, detail="Report section not found")


@router.get("/task/{task_id}/report-dir")
@router.get("/task/{task_id}/report-dir/{dir_path:path}")
async def list_report_dir(task_id: str, dir_path: str = ""):
    """List markdown files in a report directory."""
    from web.server.tasks import _store
    t = _store().get(task_id)
    report_path = (t or {}).get("report_path")

    if report_path:
        target = Path(report_path) if not dir_path else Path(report_path) / dir_path
        if target.is_dir():
            files = [f.name for f in target.glob("*.md")]
            return {"files": sorted(files), "base": str(target)}

    # Fallback: return in-memory section names if available
    sections = (t or {}).get("in_memory_sections", [])
    if sections:
        return {"files": sorted(sections), "base": "memory", "source": "memory"}

    raise HTTPException(status_code=404, detail="Directory not found")


@router.get("/task/{task_id}/report-memory/{section}")
async def get_report_section_memory(task_id: str, section: str):
    """Get a report section from in-memory state (fallback when files not on disk)."""
    from web.server.tasks import _store
    t = _store().get(task_id)
    sections = (t or {}).get("in_memory_report", {})
    content = sections.get(section)
    if content:
        return PlainTextResponse(content=content, media_type="text/markdown; charset=utf-8")
    raise HTTPException(status_code=404, detail="Report section not found")


@router.get("/task/{task_id}/report-html/{section:path}")
async def get_report_html(task_id: str, section: str):
    """Get a report file rendered as HTML (server-side rendering for mobile compatibility)."""
    from web.server.tasks import _store
    t = _store().get(task_id)
    report_path = (t or {}).get("report_path")

    if report_path:
        section_file = Path(report_path) / section
        if section_file.exists():
            md_content = section_file.read_text(encoding="utf-8")
            # Convert markdown to HTML with table extension
            html_content = markdown.markdown(
                md_content,
                extensions=['tables', 'fenced_code', 'nl2br']
            )
            return JSONResponse(content={"html": html_content})

    raise HTTPException(status_code=404, detail="Report section not found")
