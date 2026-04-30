# web/server/schemas.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RunMode(str, Enum):
    STREAMING = "streaming"
    BACKGROUND = "background"


class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., description="股票代码，如 NVDA, AAPL")
    analysis_date: Optional[str] = Field(default=None, description="分析日期 YYYY-MM-DD，不传则使用当天")
    mode: RunMode = Field(default=RunMode.STREAMING, description="运行模式")


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskInfo(BaseModel):
    task_id: str
    ticker: str
    analysis_date: str
    status: TaskStatus
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    report_path: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str


class TaskListResponse(BaseModel):
    tasks: list[TaskInfo]
