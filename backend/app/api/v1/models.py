"""Model Registry API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.core.dependencies import DbSession, CurrentUser, require_admin
from app.db import models as m
from app.ml.inference import tabnet_inference
from app.services.audit import log_audit_event

router = APIRouter()


@router.get("")
async def list_models(db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(m.ModelVersion).order_by(m.ModelVersion.registered_at.desc()))
    models = result.scalars().all()
    return [_model_to_dict(mv) for mv in models]


@router.get("/{model_id}")
async def get_model(model_id: str, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(m.ModelVersion).where(m.ModelVersion.id == model_id))
    mv = result.scalar_one_or_none()
    if not mv:
        raise HTTPException(status_code=404, detail="Model version not found")
    return _model_to_dict(mv)


@router.post("", dependencies=[Depends(require_admin())])
async def register_model(
    name: str,
    channel: str,
    version_tag: str,
    artifact_path: Optional[str] = None,
    description: Optional[str] = None,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    mv = m.ModelVersion(
        name=name,
        channel=channel,
        version_tag=version_tag,
        artifact_path=artifact_path,
        description=description,
        registered_by_id=current_user.id,
        is_active=False,
        is_experimental=channel != "tab_net",
    )
    db.add(mv)
    await log_audit_event(db, actor_id=current_user.id, actor_email=current_user.email,
                          action="model.registered", resource_type="model_version",
                          extra={"name": name, "version_tag": version_tag})
    await db.commit()
    await db.refresh(mv)
    return _model_to_dict(mv)


@router.put("/{model_id}/activate", dependencies=[Depends(require_admin())])
async def activate_model(model_id: str, db: DbSession, current_user: CurrentUser):
    result = await db.execute(select(m.ModelVersion).where(m.ModelVersion.id == model_id))
    mv = result.scalar_one_or_none()
    if not mv:
        raise HTTPException(status_code=404, detail="Model version not found")
    # Deactivate all others in same channel
    all_result = await db.execute(
        select(m.ModelVersion).where(m.ModelVersion.channel == mv.channel)
    )
    for other in all_result.scalars().all():
        other.is_active = False
    mv.is_active = True
    # Reload model in inference engine
    if mv.artifact_path:
        tabnet_inference.reload_model(mv.artifact_path)
    await log_audit_event(db, actor_id=current_user.id, actor_email=current_user.email,
                          action="model.activated", resource_type="model_version", resource_id=model_id)
    await db.commit()
    return {"message": f"Model '{mv.name}' v{mv.version_tag} is now active."}


def _model_to_dict(mv: m.ModelVersion) -> dict:
    return {
        "id": str(mv.id),
        "name": mv.name,
        "channel": mv.channel,
        "version_tag": mv.version_tag,
        "description": mv.description,
        "artifact_path": mv.artifact_path,
        "hyperparameters": mv.hyperparameters,
        "feature_names": mv.feature_names,
        "is_active": mv.is_active,
        "is_experimental": mv.is_experimental,
        "registered_at": mv.registered_at,
        "notes": mv.notes,
    }
