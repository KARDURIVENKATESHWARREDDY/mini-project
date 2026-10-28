"""Pydantic schemas — Batch Jobs."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class BatchJobStatus(BaseModel):
    id: str
    filename: str
    status: str
    total_rows: Optional[int] = None
    processed_rows: int = 0
    rejected_rows: int = 0
    skipped_rows: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class PaginatedBatchJobs(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[BatchJobStatus]
