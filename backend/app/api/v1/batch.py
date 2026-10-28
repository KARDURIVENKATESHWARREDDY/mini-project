"""Batch screening API endpoints."""
import asyncio
import csv
import io
import logging
import os
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import DbSession, CurrentUser, require_analyst_or_admin
from app.db import models as m
from app.schemas import batch as s
from app.ml.inference import tabnet_inference
from app.services.audit import log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
REQUIRED_COLUMNS = {"Time", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9",
                    "V10", "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18",
                    "V19", "V20", "V21", "V22", "V23", "V24", "V25", "V26", "V27",
                    "V28", "Amount"}


async def _process_batch_job(job_id: str, file_path: str, model_version_id: str):
    """Background task: read CSV, run inference, store transaction+prediction records."""
    from app.db.session import async_session_factory
    async with async_session_factory() as db:
        job_result = await db.execute(select(m.BatchJob).where(m.BatchJob.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            return
        from datetime import datetime, timezone
        job.status = m.BatchJobStatus.processing
        job.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            job.total_rows = len(rows)
            processed = 0
            rejected = 0
            skipped = 0

            # Batch in chunks of 500
            chunk_size = 500
            for i in range(0, len(rows), chunk_size):
                chunk = rows[i:i + chunk_size]
                feature_dicts = []
                valid_idx = []
                for j, row in enumerate(chunk):
                    try:
                        features = {col: float(row[col]) for col in REQUIRED_COLUMNS if col in row}
                        if len(features) < len(REQUIRED_COLUMNS):
                            rejected += 1
                            continue
                        feature_dicts.append(features)
                        valid_idx.append(i + j)
                    except (ValueError, KeyError):
                        rejected += 1

                if feature_dicts:
                    results = tabnet_inference.predict_batch(
                        feature_dicts,
                        threshold_low=settings.FRAUD_THRESHOLD_LOW,
                        threshold_high=settings.FRAUD_THRESHOLD_HIGH,
                    )
                    for k, (prob, risk, _) in enumerate(results):
                        row = rows[valid_idx[k]]
                        if prob < 0:  # Error row
                            rejected += 1
                            continue
                        tx = m.Transaction(
                            v1=float(row.get("V1", 0)), v2=float(row.get("V2", 0)),
                            v3=float(row.get("V3", 0)), v4=float(row.get("V4", 0)),
                            v5=float(row.get("V5", 0)), v6=float(row.get("V6", 0)),
                            v7=float(row.get("V7", 0)), v8=float(row.get("V8", 0)),
                            v9=float(row.get("V9", 0)), v10=float(row.get("V10", 0)),
                            v11=float(row.get("V11", 0)), v12=float(row.get("V12", 0)),
                            v13=float(row.get("V13", 0)), v14=float(row.get("V14", 0)),
                            v15=float(row.get("V15", 0)), v16=float(row.get("V16", 0)),
                            v17=float(row.get("V17", 0)), v18=float(row.get("V18", 0)),
                            v19=float(row.get("V19", 0)), v20=float(row.get("V20", 0)),
                            v21=float(row.get("V21", 0)), v22=float(row.get("V22", 0)),
                            v23=float(row.get("V23", 0)), v24=float(row.get("V24", 0)),
                            v25=float(row.get("V25", 0)), v26=float(row.get("V26", 0)),
                            v27=float(row.get("V27", 0)), v28=float(row.get("V28", 0)),
                            time_seconds=float(row.get("Time", 0)),
                            amount=float(row.get("Amount", 0)),
                            ground_truth_label=int(row["Class"]) if "Class" in row else None,
                            batch_job_id=job_id,
                            source_file=job.filename,
                        )
                        db.add(tx)
                        await db.flush()
                        pred = m.Prediction(
                            transaction_id=tx.id,
                            model_version_id=model_version_id,
                            channel=m.ModelChannel.tab_net,
                            fraud_probability=prob,
                            risk_category=risk,
                            threshold_low=settings.FRAUD_THRESHOLD_LOW,
                            threshold_high=settings.FRAUD_THRESHOLD_HIGH,
                        )
                        db.add(pred)
                        processed += 1
                await db.commit()

            job.status = m.BatchJobStatus.completed
            job.processed_rows = processed
            job.rejected_rows = rejected
            job.skipped_rows = skipped
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Batch job %s completed: %d processed, %d rejected", job_id, processed, rejected)
        except Exception as e:
            logger.error("Batch job %s failed: %s", job_id, e)
            job.status = m.BatchJobStatus.failed
            job.error_message = str(e)
            await db.commit()


@router.post("/upload", response_model=s.BatchJobStatus,
             dependencies=[Depends(require_analyst_or_admin())])
async def upload_batch(
    background_tasks: BackgroundTasks,
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are accepted.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit.")

    # Validate CSV header
    try:
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        header = set(reader.fieldnames or [])
        missing_cols = REQUIRED_COLUMNS - header
        if missing_cols:
            raise HTTPException(
                status_code=422,
                detail=f"CSV is missing required columns: {sorted(missing_cols)}",
            )
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="File is not valid UTF-8 CSV.")

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename.replace(' ', '_')}"
    file_path = str(upload_dir / safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # Load active model
    model_result = await db.execute(
        select(m.ModelVersion).where(m.ModelVersion.is_active == True).limit(1)
    )
    active_model = model_result.scalar_one_or_none()
    if not active_model:
        raise HTTPException(status_code=503, detail="No active model. Please register a model first.")

    # Create job record
    job = m.BatchJob(
        filename=file.filename,
        file_path=file_path,
        submitted_by_id=current_user.id,
        model_version_id=active_model.id,
        status=m.BatchJobStatus.queued,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await log_audit_event(db, actor_id=current_user.id, actor_email=current_user.email,
                          action="batch.uploaded", resource_type="batch_job", resource_id=job.id,
                          extra={"filename": file.filename})
    await db.commit()

    background_tasks.add_task(_process_batch_job, str(job.id), file_path, str(active_model.id))

    return s.BatchJobStatus(
        id=str(job.id),
        filename=job.filename,
        status=job.status,
        total_rows=None,
        processed_rows=0,
        rejected_rows=0,
        skipped_rows=0,
        created_at=job.created_at,
    )


@router.get("/jobs", response_model=s.PaginatedBatchJobs)
async def list_jobs(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    from sqlalchemy import func
    total = await db.scalar(select(func.count()).select_from(m.BatchJob))
    result = await db.execute(
        select(m.BatchJob).order_by(m.BatchJob.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    jobs = result.scalars().all()
    return s.PaginatedBatchJobs(
        total=total or 0, page=page, page_size=page_size,
        items=[s.BatchJobStatus(
            id=str(j.id), filename=j.filename, status=j.status,
            total_rows=j.total_rows, processed_rows=j.processed_rows,
            rejected_rows=j.rejected_rows, skipped_rows=j.skipped_rows,
            created_at=j.created_at, started_at=j.started_at,
            completed_at=j.completed_at, error_message=j.error_message,
        ) for j in jobs],
    )


@router.get("/jobs/{job_id}", response_model=s.BatchJobStatus)
async def get_job(job_id: str, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(m.BatchJob).where(m.BatchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return s.BatchJobStatus(
        id=str(job.id), filename=job.filename, status=job.status,
        total_rows=job.total_rows, processed_rows=job.processed_rows,
        rejected_rows=job.rejected_rows, skipped_rows=job.skipped_rows,
        created_at=job.created_at, started_at=job.started_at,
        completed_at=job.completed_at, error_message=job.error_message,
    )
