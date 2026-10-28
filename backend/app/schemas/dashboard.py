"""Pydantic schemas — Dashboard."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ActiveModelInfo(BaseModel):
    id: str
    name: str
    version_tag: str
    channel: str


class LatestMetrics(BaseModel):
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    pr_auc: Optional[float] = None
    roc_auc: Optional[float] = None


class DashboardSummary(BaseModel):
    total_transactions: int
    high_risk_count: int
    confirmed_fraud_count: int
    pending_review_count: int
    open_investigations: int
    active_model: Optional[ActiveModelInfo] = None
    latest_metrics: Optional[LatestMetrics] = None


class TimeSeriesPoint(BaseModel):
    date: str
    value: int


class RiskDistribution(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0


class RecentAlert(BaseModel):
    prediction_id: str
    transaction_id: str
    fraud_probability: float
    risk_category: str
    amount: Optional[float] = None
    predicted_at: datetime
    review_status: str


class ModelHealthStatus(BaseModel):
    tab_net_available: bool
    seq_net_available: bool
    geo_net_available: bool
    prof_net_available: bool
    fusion_available: bool
    active_model_name: Optional[str] = None
    active_model_version: Optional[str] = None
    notes: Optional[str] = None
