# web/server/main.py
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

# Module-level app reference for lazy access from tasks.py and api.py
app: FastAPI | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load existing reports as task history. Shutdown: cancel pending tasks."""
    import asyncio
    from web.server.heatmap import fetch_heatmap_data, heatmap_cache
    from web.server.tasks import load_history_from_disk
    from web.server.runner import start_worker

    # Pre-warm heatmap cache in background (don't block startup)
    async def prewarm_cache():
        try:
            data = await asyncio.to_thread(fetch_heatmap_data)
            heatmap_cache.set(data)
            logger.info("Heatmap cache pre-warmed")
        except Exception as e:
            logger.warning("Failed to pre-warm heatmap cache: %s", e)

    app.state.task_store = {}
    app.state.event_queues = {}
    load_history_from_disk(app.state.task_store)
    logger.info("Web server started, loaded %d tasks from disk", len(app.state.task_store))

    # Start background task worker
    worker_task = asyncio.create_task(start_worker())
    # Pre-warm heatmap cache without blocking startup
    asyncio.create_task(prewarm_cache())
    yield

    # Cleanup: cancel running tasks
    worker_task.cancel()
    for tid, task in app.state.task_store.items():
        if hasattr(task, "_cancel_event"):
            task["_cancel_event"].set()
    logger.info("Web server stopped")


def create_app(dev_mode: bool = False) -> FastAPI:
    global app
    app = FastAPI(title="TradingAgents Web", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if dev_mode else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API router
    from web.server.api import router as api_router
    app.include_router(api_router)

    # Serve built frontend static files in production
    if not dev_mode:
        static_dir = Path(__file__).parent.parent / "client" / "dist"
        if static_dir.exists():
            app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app
