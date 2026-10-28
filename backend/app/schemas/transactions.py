"""Pydantic schemas — Transactions."""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class TransactionFeatures(BaseModel):
    v1: Optional[float] = None; v2: Optional[float] = None; v3: Optional[float] = None
    v4: Optional[float] = None; v5: Optional[float] = None; v6: Optional[float] = None
    v7: Optional[float] = None; v8: Optional[float] = None; v9: Optional[float] = None
    v10: Optional[float] = None; v11: Optional[float] = None; v12: Optional[float] = None
    v13: Optional[float] = None; v14: Optional[float] = None; v15: Optional[float] = None
    v16: Optional[float] = None; v17: Optional[float] = None; v18: Optional[float] = None
    v19: Optional[float] = None; v20: Optional[float] = None; v21: Optional[float] = None
    v22: Optional[float] = None; v23: Optional[float] = None; v24: Optional[float] = None
    v25: Optional[float] = None; v26: Optional[float] = None; v27: Optional[float] = None
    v28: Optional[float] = None


class PredictionSummary(BaseModel):
    id: str
    model_version_id: str
    model_name: Optional[str] = None
    channel: str
    fraud_probability: float
    risk_category: str
    shap_values: Optional[Dict[str, float]] = None
    review_status: str
    predicted_at: datetime


class TransactionListItem(BaseModel):
    id: str
    external_id: Optional[str] = None
    amount: Optional[float] = None
    time_seconds: Optional[float] = None
    imported_at: datetime
    fraud_probability: Optional[float] = None
    risk_category: Optional[str] = None
    review_status: Optional[str] = None
    model_version: Optional[str] = None
    ground_truth_label: Optional[int] = None


class TransactionDetail(BaseModel):
    id: str
    external_id: Optional[str] = None
    amount: Optional[float] = None
    time_seconds: Optional[float] = None
    imported_at: datetime
    ground_truth_label: Optional[int] = None
    features: TransactionFeatures
    predictions: List[PredictionSummary] = []
    investigation_id: Optional[str] = None


class PaginatedTransactions(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[TransactionListItem]
