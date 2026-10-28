"""Pydantic schemas — Predictions."""
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FeatureVector(BaseModel):
    """30-feature vector for TAB-Net: Time, V1-V28, Amount."""
    Time: float = Field(..., description="Seconds elapsed from the first transaction in the dataset")
    V1: float; V2: float; V3: float; V4: float; V5: float
    V6: float; V7: float; V8: float; V9: float; V10: float
    V11: float; V12: float; V13: float; V14: float; V15: float
    V16: float; V17: float; V18: float; V19: float; V20: float
    V21: float; V22: float; V23: float; V24: float; V25: float
    V26: float; V27: float; V28: float
    Amount: float = Field(..., ge=0, description="Transaction amount in dataset currency units")


class SinglePredictionRequest(BaseModel):
    features: FeatureVector
    transaction_id: Optional[str] = None  # Link to stored transaction if available


class PredictionResult(BaseModel):
    prediction_id: Optional[str] = None
    transaction_id: Optional[str] = None
    fraud_probability: float
    risk_category: str
    model_name: str
    model_version: str
    channel: str
    threshold_low: float
    threshold_high: float
    thresholds_validated: bool = False
    shap_values: Optional[Dict[str, float]] = None
    predicted_at: datetime
    warnings: List[str] = []
