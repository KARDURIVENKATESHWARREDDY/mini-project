"""Model Evaluation API endpoints."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select

from app.core.dependencies import DbSession, CurrentUser, require_admin
from app.db import models as m
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_evaluation(run_id: str, model_version_id: str):
    """Background task: evaluate model on stored transactions with ground-truth labels."""
    from app.db.session import async_session_factory
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, precision_recall_curve, roc_curve, confusion_matrix,
        average_precision_score,
    )
    from app.ml.inference.tabnet_inference import predict, ensure_model_loaded

    async with async_session_factory() as db:
        run_result = await db.execute(select(m.EvaluationRun).where(m.EvaluationRun.id == run_id))
        run = run_result.scalar_one_or_none()
        if not run:
            return
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            if not ensure_model_loaded():
                raise RuntimeError("Model not loaded. Please train and register a model first.")

            # Get all transactions with known ground-truth labels
            tx_result = await db.execute(
                select(m.Transaction).where(m.Transaction.ground_truth_label.isnot(None))
            )
            txs = tx_result.scalars().all()

            if len(txs) < 10:
                raise RuntimeError(f"Insufficient labelled transactions for evaluation ({len(txs)} found, need ≥10).")

            y_true = []
            y_prob = []
            from app.core.config import settings

            for tx in txs:
                features = {
                    "Time": tx.time_seconds or 0.0,
                    "V1": tx.v1 or 0.0, "V2": tx.v2 or 0.0, "V3": tx.v3 or 0.0,
                    "V4": tx.v4 or 0.0, "V5": tx.v5 or 0.0, "V6": tx.v6 or 0.0,
                    "V7": tx.v7 or 0.0, "V8": tx.v8 or 0.0, "V9": tx.v9 or 0.0,
                    "V10": tx.v10 or 0.0, "V11": tx.v11 or 0.0, "V12": tx.v12 or 0.0,
                    "V13": tx.v13 or 0.0, "V14": tx.v14 or 0.0, "V15": tx.v15 or 0.0,
                    "V16": tx.v16 or 0.0, "V17": tx.v17 or 0.0, "V18": tx.v18 or 0.0,
                    "V19": tx.v19 or 0.0, "V20": tx.v20 or 0.0, "V21": tx.v21 or 0.0,
                    "V22": tx.v22 or 0.0, "V23": tx.v23 or 0.0, "V24": tx.v24 or 0.0,
                    "V25": tx.v25 or 0.0, "V26": tx.v26 or 0.0, "V27": tx.v27 or 0.0,
                    "V28": tx.v28 or 0.0, "Amount": tx.amount or 0.0,
                }
                try:
                    prob, _, _ = predict(features)
                    y_true.append(tx.ground_truth_label)
                    y_prob.append(prob)
                except Exception:
                    pass

            y_true_arr = np.array(y_true)
            y_prob_arr = np.array(y_prob)
            threshold = settings.FRAUD_THRESHOLD_HIGH
            y_pred = (y_prob_arr >= threshold).astype(int)

            # Compute metrics
            cm = confusion_matrix(y_true_arr, y_pred).tolist()
            tn, fp, fn, tp = confusion_matrix(y_true_arr, y_pred).ravel()
            fpr_val = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0

            precision_arr, recall_arr, pr_thresholds = precision_recall_curve(y_true_arr, y_prob_arr)
            fpr_arr, tpr_arr, roc_thresholds = roc_curve(y_true_arr, y_prob_arr)

            run.accuracy = float(accuracy_score(y_true_arr, y_pred))
            run.precision = float(precision_score(y_true_arr, y_pred, zero_division=0))
            run.recall = float(recall_score(y_true_arr, y_pred, zero_division=0))
            run.f1_score = float(f1_score(y_true_arr, y_pred, zero_division=0))
            run.macro_f1 = float(f1_score(y_true_arr, y_pred, average="macro", zero_division=0))
            run.pr_auc = float(average_precision_score(y_true_arr, y_prob_arr))
            run.roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
            run.false_positive_rate = fpr_val
            run.confusion_matrix = cm
            run.num_samples = len(y_true)
            run.num_positive = int(y_true_arr.sum())
            run.num_negative = len(y_true) - int(y_true_arr.sum())
            # Downsample curve data for storage (max 200 points)
            step = max(1, len(precision_arr) // 200)
            run.pr_curve_data = {
                "precision": precision_arr[::step].tolist(),
                "recall": recall_arr[::step].tolist(),
                "thresholds": pr_thresholds[::step].tolist() if len(pr_thresholds) > 0 else [],
            }
            step_roc = max(1, len(fpr_arr) // 200)
            run.roc_curve_data = {
                "fpr": fpr_arr[::step_roc].tolist(),
                "tpr": tpr_arr[::step_roc].tolist(),
            }
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Evaluation run %s completed. PR-AUC=%.4f", run_id, run.pr_auc)
        except Exception as e:
            logger.error("Evaluation run %s failed: %s", run_id, e)
            run.status = "failed"
            run.notes = str(e)
            await db.commit()


@router.get("/runs")
async def list_runs(db: DbSession, current_user: CurrentUser):
    result = await db.execute(
        select(m.EvaluationRun).order_by(m.EvaluationRun.created_at.desc()).limit(50)
    )
    runs = result.scalars().all()
    return [_run_to_dict(r, include_curves=False) for r in runs]


@router.post("/runs", dependencies=[Depends(require_admin())])
async def trigger_evaluation(
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
    description: Optional[str] = None,
):
    model_result = await db.execute(
        select(m.ModelVersion).where(m.ModelVersion.is_active == True).limit(1)
    )
    active_model = model_result.scalar_one_or_none()
    if not active_model:
        raise HTTPException(status_code=503, detail="No active model registered.")

    run = m.EvaluationRun(
        model_version_id=active_model.id,
        triggered_by_id=current_user.id,
        dataset_description=description or "All stored transactions with ground-truth labels",
        status="pending",
    )
    db.add(run)
    await log_audit_event(db, actor_id=current_user.id, actor_email=current_user.email,
                          action="evaluation.triggered", resource_type="evaluation_run")
    await db.commit()
    await db.refresh(run)
    background_tasks.add_task(_run_evaluation, str(run.id), str(active_model.id))
    return {"id": str(run.id), "status": "pending", "message": "Evaluation job queued."}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(m.EvaluationRun).where(m.EvaluationRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return _run_to_dict(run, include_curves=True)


def _run_to_dict(run: m.EvaluationRun, include_curves: bool = False) -> dict:
    d = {
        "id": str(run.id),
        "model_version_id": str(run.model_version_id),
        "status": run.status,
        "dataset_description": run.dataset_description,
        "num_samples": run.num_samples,
        "num_positive": run.num_positive,
        "num_negative": run.num_negative,
        "accuracy": run.accuracy,
        "precision": run.precision,
        "recall": run.recall,
        "f1_score": run.f1_score,
        "macro_f1": run.macro_f1,
        "pr_auc": run.pr_auc,
        "roc_auc": run.roc_auc,
        "false_positive_rate": run.false_positive_rate,
        "confusion_matrix": run.confusion_matrix,
        "notes": run.notes,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }
    if include_curves:
        d["pr_curve_data"] = run.pr_curve_data
        d["roc_curve_data"] = run.roc_curve_data
    return d
