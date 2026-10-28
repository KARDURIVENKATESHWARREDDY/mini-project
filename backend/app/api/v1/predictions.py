"""Prediction API endpoints — single transaction scoring."""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import DbSession, CurrentUser, require_analyst_or_admin
from app.db import models as m
from app.schemas import predictions as s
from app.ml.inference import tabnet_inference
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/single", response_model=s.PredictionResult,
             dependencies=[Depends(require_analyst_or_admin())])
async def predict_single(
    request: Request,
    body: s.SinglePredictionRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Score a single transaction feature vector.

    ⚠️ This is a research prototype. Predictions should be treated as
    decision-support information, not authoritative fraud determinations.
    """
    # Load active model version
    model_result = await db.execute(
        select(m.ModelVersion).where(m.ModelVersion.is_active == True).limit(1)
    )
    active_model = model_result.scalar_one_or_none()
    if not active_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No active model is registered. "
                "Please train and register a model using the Model Registry."
            ),
        )
    # Validate that model file is loadable
    if not tabnet_inference.is_model_loaded():
        loaded = tabnet_inference.ensure_model_loaded()
        if not loaded:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Model artifact not found on disk. "
                    "Please run 'python ml/train_tabnet.py' and restart the server."
                ),
            )
    features = body.features.model_dump()
    try:
        fraud_prob, risk_cat, shap_vals = tabnet_inference.predict(
            features=features,
            threshold_low=settings.FRAUD_THRESHOLD_LOW,
            threshold_high=settings.FRAUD_THRESHOLD_HIGH,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Persist prediction if transaction_id is provided
    prediction = None
    if body.transaction_id:
        tx_result = await db.execute(
            select(m.Transaction).where(m.Transaction.id == body.transaction_id)
        )
        tx = tx_result.scalar_one_or_none()
        if tx:
            prediction = m.Prediction(
                transaction_id=body.transaction_id,
                model_version_id=active_model.id,
                channel=m.ModelChannel.tab_net,
                fraud_probability=fraud_prob,
                risk_category=risk_cat,
                threshold_low=settings.FRAUD_THRESHOLD_LOW,
                threshold_high=settings.FRAUD_THRESHOLD_HIGH,
                shap_values=shap_vals,
                review_status=m.ReviewStatus.pending,
            )
            db.add(prediction)
            await db.commit()
            await db.refresh(prediction)

    await log_audit_event(
        db,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="prediction.created",
        resource_type="prediction",
        resource_id=str(prediction.id) if prediction else None,
        extra={"risk_category": risk_cat, "channel": "tab_net"},
    )
    await db.commit()

    return s.PredictionResult(
        prediction_id=str(prediction.id) if prediction else None,
        transaction_id=body.transaction_id,
        fraud_probability=fraud_prob,
        risk_category=risk_cat,
        model_name=active_model.name,
        model_version=active_model.version_tag,
        channel=active_model.channel,
        threshold_low=settings.FRAUD_THRESHOLD_LOW,
        threshold_high=settings.FRAUD_THRESHOLD_HIGH,
        thresholds_validated=False,  # Explicitly unvalidated
        shap_values=shap_vals,
        predicted_at=datetime.now(timezone.utc),
        warnings=[
            "Thresholds (low=0.3, high=0.7) are configurable defaults and have not been validated on production data.",
            "This is a research prototype. Do not use predictions to automatically block transactions.",
        ],
    )


@router.get("/{prediction_id}", response_model=s.PredictionResult)
async def get_prediction(prediction_id: str, db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(m.Prediction, m.ModelVersion)
        .join(m.ModelVersion, m.Prediction.model_version_id == m.ModelVersion.id)
        .where(m.Prediction.id == prediction_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Prediction not found")
    pred, mv = row
    return s.PredictionResult(
        prediction_id=str(pred.id),
        transaction_id=str(pred.transaction_id),
        fraud_probability=pred.fraud_probability,
        risk_category=pred.risk_category,
        model_name=mv.name,
        model_version=mv.version_tag,
        channel=pred.channel,
        threshold_low=pred.threshold_low,
        threshold_high=pred.threshold_high,
        thresholds_validated=False,
        shap_values=pred.shap_values,
        predicted_at=pred.predicted_at,
        warnings=["This is a research prototype. Predictions are decision-support information only."],
    )
