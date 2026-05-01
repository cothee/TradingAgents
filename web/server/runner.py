# web/server/runner.py
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from cli.main import save_report_to_disk

from web.server.tasks import _queue, _store, _events, _semaphore
from web.server.schemas import TaskStatus

logger = logging.getLogger(__name__)

# Reference to the main event loop, set when runner starts
_event_loop: asyncio.AbstractEventLoop | None = None


async def start_worker():
    """Background worker that drains the task queue."""
    global _event_loop
    _event_loop = asyncio.get_running_loop()
    print(f"[Runner] Task worker started", flush=True)
    while True:
        task_id = await _queue.get()
        print(f"[Runner] Picked up task {task_id}", flush=True)
        asyncio.create_task(_run_task(task_id))


async def _run_task(task_id: str):
    """Execute a single analysis task with semaphore control."""
    async with _semaphore:
        task = _store().get(task_id)
        if task is None:
            return

        task["status"] = TaskStatus.RUNNING
        eq = _events().get(task_id)
        if eq:
            await eq.put({
                "event": "task_started",
                "data": {"ticker": task["ticker"], "date": task["analysis_date"]},
            })

        try:
            await _execute_analysis(task_id, task)
            task["status"] = TaskStatus.COMPLETED
        except Exception as e:
            logger.exception("Task %s failed", task_id)
            eq = _events().get(task_id)
            if eq:
                await eq.put({
                    "event": "task_failed",
                    "data": {"error": str(e)},
                })
            task["status"] = TaskStatus.FAILED
            task["error"] = str(e)

        task["completed_at"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def _execute_analysis(task_id: str, task: dict):
    """Run TradingAgentsGraph in a thread, emitting events periodically."""
    result = {"final_state": None, "error": None}
    cancel_event = asyncio.Event()
    task["_cancel_event"] = cancel_event

    # Config available at outer scope for report path detection
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "qwen"
    config["deep_think_llm"] = "qwen3.6-plus"
    config["quick_think_llm"] = "qwen3.6-plus"
    config["output_language"] = "Chinese"
    config["max_debate_rounds"] = 1
    config["max_risk_discuss_rounds"] = 1

    reports_dir = Path(config.get("results_dir"))
    ticker = task["ticker"].upper()
    results_dir = reports_dir / ticker / task["analysis_date"]
    report_dir = results_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Task %s: starting TradingAgentsGraph for %s on %s", task_id, task["ticker"], task["analysis_date"])

    def run_graph():
        try:
            analysts = ["market", "social", "news", "fundamentals"]
            graph = TradingAgentsGraph(analysts, config=config, debug=False)
            logger.info("Task %s: graph created, propagating state", task_id)

            init_state = graph.propagator.create_initial_state(
                task["ticker"], task["analysis_date"]
            )
            args = graph.propagator.get_graph_args()
            logger.info("Task %s: graph args = %s", task_id, args)

            chunk_count = 0
            for chunk in graph.graph.stream(init_state, **args):
                chunk_count += 1
                if cancel_event.is_set():
                    break
                _process_chunk_events(task_id, chunk)
                result["final_state"] = chunk
        except Exception as e:
            logger.exception("Task %s: graph exception", task_id)
            result["error"] = str(e)

    await asyncio.to_thread(run_graph)

    if result["error"]:
        raise RuntimeError(result["error"])

    if result["final_state"]:
        # Save reports to disk using the same function as CLI
        final_state = result["final_state"]
        logger.info("Task %s: writing reports to %s", task_id, report_dir)
        save_report_to_disk(final_state, ticker=ticker, save_path=report_dir)
        task["report_path"] = str(report_dir)
        logger.info("Task %s: report_path = %s", task_id, task["report_path"])

        # Also store in-memory sections as fallback for frontend
        section_keys = [
            "market_report", "sentiment_report", "news_report",
            "fundamentals_report", "trader_investment_plan",
            "final_trade_decision", "investment_debate_state", "risk_debate_state",
        ]
        memory_sections = {}
        section_list = []
        for key in section_keys:
            if key in final_state and final_state[key]:
                val = final_state[key]
                # For nested dicts (debate states), extract the useful text
                if isinstance(val, dict):
                    if key == "risk_debate_state":
                        memory_sections[key] = val.get("judge_decision", "")
                    elif key == "investment_debate_state":
                        memory_sections[key] = val.get("judge_decision", "")
                elif isinstance(val, str):
                    memory_sections[key] = val
                if key in memory_sections and memory_sections[key]:
                    section_list.append(f"{key}.md")
        task["in_memory_report"] = memory_sections
        task["in_memory_sections"] = section_list

        eq = _events().get(task_id)
        if eq:
            await eq.put({
                "event": "task_completed",
                "data": {
                    "ticker": task["ticker"],
                    "decision": final_state.get("final_trade_decision", "")[:200],
                    "final_trade_decision": final_state.get("final_trade_decision", ""),
                },
            })


def _emit_event(eq, event: dict):
    """Thread-safe event emission: schedule put on the main event loop."""
    if _event_loop is None:
        return
    if eq is None:
        return
    # JSON-encode the data field to ensure proper format for frontend
    if "data" in event and isinstance(event["data"], dict):
        event["data"] = json.dumps(event["data"])
    try:
        asyncio.run_coroutine_threadsafe(eq.put(event), _event_loop)
    except Exception:
        pass


# Track previous state values to detect new completions
_prev_state: Dict[str, Any] = {}


def _process_chunk_events(task_id: str, chunk: Dict[str, Any]):
    """Synchronous event emission: detect newly populated keys and emit events."""
    global _prev_state
    eq = _events().get(task_id)
    if not eq:
        return

    updates = chunk
    if not updates:
        return

    prev = _prev_state.get(task_id, {})

    agent_map = {
        "market_report": "Market Analyst",
        "sentiment_report": "Social Analyst",
        "news_report": "News Analyst",
        "fundamentals_report": "Fundamentals Analyst",
        "investment_debate_state": "Research Team",
        "trader_investment_plan": "Trader",
        "risk_debate_state": "Risk Management",
    }

    for key in agent_map.keys():
        old_val = prev.get(key)
        new_val = updates.get(key)

        is_newly_populated = False
        if isinstance(new_val, str):
            if len(new_val) > 50 and (not old_val or old_val != new_val):
                is_newly_populated = True
        elif isinstance(new_val, dict):
            if new_val and (not old_val or old_val != new_val):
                is_newly_populated = True

        if is_newly_populated:
            status = "completed"
            if key in ("risk_debate_state", "investment_debate_state"):
                if isinstance(new_val, dict) and new_val.get("judge_decision"):
                    status = "completed"
                else:
                    status = "in_progress"
            _emit_event(eq, {
                "event": "agent_progress",
                "data": {"agent": agent_map[key], "status": status},
            })

            if isinstance(new_val, str) and len(new_val) > 50:
                section_map = {
                    "market_report": "市场分析",
                    "sentiment_report": "情感分析",
                    "news_report": "新闻分析",
                    "fundamentals_report": "基本面分析",
                    "trader_investment_plan": "交易计划",
                }
                if key in section_map:
                    _emit_event(eq, {
                        "event": "report_section",
                        "data": {"section": section_map[key], "content": new_val[:500]},
                    })

    new_fd = updates.get("final_trade_decision")
    old_fd = prev.get("final_trade_decision", "")
    if new_fd and new_fd != old_fd:
        _emit_event(eq, {
            "event": "report_section",
            "data": {"section": "最终决策", "content": new_fd},
        })
        _emit_event(eq, {
            "event": "agent_progress",
            "data": {"agent": "Portfolio Manager", "status": "completed"},
        })

    _prev_state[task_id] = updates
