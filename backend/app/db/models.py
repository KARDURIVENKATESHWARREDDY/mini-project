"""
SQLAlchemy ORM models for CARD-Net.

Design principles:
- All timestamps are UTC.
- Audit events are append-only (no UPDATE/DELETE on audit_events table).
- Passwords, card numbers, and CVVs are never stored in plaintext.
- Soft-delete via `is_active` on users; hard records for transactions.
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer,
    JSON, String, Text, UniqueConstraint, Index, BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ─── Enumerations ─────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


class RiskCategory(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ReviewStatus(str, enum.Enum):
    pending = "pending"
    under_review = "under_review"
    resolved_fraud = "resolved_fraud"
    resolved_legitimate = "resolved_legitimate"
    dismissed = "dismissed"


class BatchJobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class InvestigationStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    escalated = "escalated"
    resolved = "resolved"
    closed = "closed"


class ModelChannel(str, enum.Enum):
    tab_net = "tab_net"
    seq_net = "seq_net"
    geo_net = "geo_net"
    prof_net = "prof_net"


# ─── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.viewer)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    sessions: Mapped[List["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    investigations_assigned: Mapped[List["Investigation"]] = relationship(
        back_populates="assigned_to", foreign_keys="Investigation.assigned_to_id"
    )


class Session(Base):
    """Refresh token store for JWT rotation."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=new_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    refresh_token_hash = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    is_revoked = Column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship(back_populates="sessions")


# ─── Transactions ─────────────────────────────────────────────────────────────

class Transaction(Base):
    """
    Represents a single credit card transaction from the benchmark dataset or import.
    Fields match the ULB/Kaggle creditcard.csv schema (Time, V1–V28, Amount, Class).
    No card numbers, CVVs, or personally identifying information are stored.
    """
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=new_uuid)
    # External reference (e.g., row index in original CSV)
    external_id = Column(String(128), nullable=True, index=True)
    # PCA-transformed features V1–V28
    v1 = Column(Float); v2 = Column(Float); v3 = Column(Float); v4 = Column(Float)
    v5 = Column(Float); v6 = Column(Float); v7 = Column(Float); v8 = Column(Float)
    v9 = Column(Float); v10 = Column(Float); v11 = Column(Float); v12 = Column(Float)
    v13 = Column(Float); v14 = Column(Float); v15 = Column(Float); v16 = Column(Float)
    v17 = Column(Float); v18 = Column(Float); v19 = Column(Float); v20 = Column(Float)
    v21 = Column(Float); v22 = Column(Float); v23 = Column(Float); v24 = Column(Float)
    v25 = Column(Float); v26 = Column(Float); v27 = Column(Float); v28 = Column(Float)
    time_seconds = Column(Float, nullable=True)   # Time (seconds from first transaction in dataset)
    amount = Column(Float, nullable=True)
    # Ground-truth label from dataset (0=legitimate, 1=fraud). Null if unknown.
    ground_truth_label = Column(Integer, nullable=True)
    # Metadata
    imported_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    batch_job_id = Column(String(36), ForeignKey("batch_jobs.id"), nullable=True)
    source_file = Column(String(512), nullable=True)

    predictions: Mapped[List["Prediction"]] = relationship(back_populates="transaction", cascade="all, delete-orphan")
    investigation: Mapped[Optional["Investigation"]] = relationship(back_populates="transaction", uselist=False)

    __table_args__ = (
        Index("ix_transactions_imported_at", "imported_at"),
    )


# ─── Predictions ──────────────────────────────────────────────────────────────

class Prediction(Base):
    """
    Model prediction for a single transaction.
    Stores the probability, risk category, and SHAP values if available.
    Separate from ground-truth labels.
    """
    __tablename__ = "predictions"

    id = Column(String(36), primary_key=True, default=new_uuid)
    transaction_id = Column(String(36), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    model_version_id = Column(String(36), ForeignKey("model_versions.id"), nullable=False)
    channel = Column(String(50), nullable=False, default=ModelChannel.tab_net)
    fraud_probability = Column(Float, nullable=False)
    risk_category = Column(String(20), nullable=False)  # low / medium / high
    threshold_low = Column(Float, nullable=False)
    threshold_high = Column(Float, nullable=False)
    # SHAP values stored as JSON dict {feature_name: shap_value}
    shap_values = Column(JSON, nullable=True)
    review_status = Column(String(50), nullable=False, default=ReviewStatus.pending)
    predicted_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    # Fusion composite score (populated when all required channels available)
    cfri_score = Column(Float, nullable=True)
    cfri_available = Column(Boolean, nullable=False, default=False)

    transaction: Mapped["Transaction"] = relationship(back_populates="predictions")
    model_version: Mapped["ModelVersion"] = relationship(back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_predicted_at", "predicted_at"),
        Index("ix_predictions_risk_category", "risk_category"),
    )


# ─── Model Registry ───────────────────────────────────────────────────────────

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(128), nullable=False)          # e.g. "XGBoost TAB-Net v1"
    channel = Column(String(50), nullable=False)        # tab_net / seq_net / etc.
    version_tag = Column(String(64), nullable=False)    # e.g. "1.0.0"
    description = Column(Text, nullable=True)
    artifact_path = Column(String(512), nullable=True)  # Path to serialised model
    hyperparameters = Column(JSON, nullable=True)
    training_dataset_info = Column(JSON, nullable=True)
    feature_names = Column(JSON, nullable=True)         # Ordered list of feature names
    is_active = Column(Boolean, nullable=False, default=False)
    is_experimental = Column(Boolean, nullable=False, default=False)
    registered_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    registered_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    notes = Column(Text, nullable=True)

    predictions: Mapped[List["Prediction"]] = relationship(back_populates="model_version")
    evaluation_runs: Mapped[List["EvaluationRun"]] = relationship(back_populates="model_version")

    __table_args__ = (
        UniqueConstraint("channel", "version_tag", name="uq_model_version_channel_tag"),
    )


# ─── Evaluation ───────────────────────────────────────────────────────────────

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=new_uuid)
    model_version_id = Column(String(36), ForeignKey("model_versions.id"), nullable=False)
    triggered_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    dataset_description = Column(Text, nullable=True)
    num_samples = Column(Integer, nullable=True)
    num_positive = Column(Integer, nullable=True)   # Fraud samples
    num_negative = Column(Integer, nullable=True)   # Legitimate samples
    # Core metrics
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    macro_f1 = Column(Float, nullable=True)
    pr_auc = Column(Float, nullable=True)
    roc_auc = Column(Float, nullable=True)
    false_positive_rate = Column(Float, nullable=True)
    # Confusion matrix [TN, FP, FN, TP]
    confusion_matrix = Column(JSON, nullable=True)
    # PR curve data {precision: [...], recall: [...], thresholds: [...]}
    pr_curve_data = Column(JSON, nullable=True)
    roc_curve_data = Column(JSON, nullable=True)
    threshold_comparison = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # pending/running/completed/failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    model_version: Mapped["ModelVersion"] = relationship(back_populates="evaluation_runs")


# ─── Batch Jobs ───────────────────────────────────────────────────────────────

class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id = Column(String(36), primary_key=True, default=new_uuid)
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)   # Server-side path (not exposed to client)
    submitted_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    model_version_id = Column(String(36), ForeignKey("model_versions.id"), nullable=True)
    status = Column(String(50), nullable=False, default=BatchJobStatus.queued)
    total_rows = Column(Integer, nullable=True)
    processed_rows = Column(Integer, nullable=False, default=0)
    rejected_rows = Column(Integer, nullable=False, default=0)
    skipped_rows = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="batch_job", primaryjoin="BatchJob.id == Transaction.batch_job_id",
        foreign_keys="Transaction.batch_job_id"
    )


# Fix circular reference
Transaction.batch_job = relationship("BatchJob", back_populates="transactions", foreign_keys=[Transaction.batch_job_id])


# ─── Investigations ───────────────────────────────────────────────────────────

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=new_uuid)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False, unique=True, index=True)
    opened_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    status = Column(String(50), nullable=False, default=InvestigationStatus.open)
    priority = Column(String(20), nullable=False, default="medium")  # low/medium/high/critical
    confirmed_label = Column(Integer, nullable=True)  # Analyst's verified label (0/1), separate from model
    resolution_notes = Column(Text, nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="investigation")
    opened_by: Mapped["User"] = relationship(foreign_keys=[opened_by_id])
    assigned_to: Mapped[Optional["User"]] = relationship(foreign_keys=[assigned_to_id], back_populates="investigations_assigned")
    events: Mapped[List["InvestigationEvent"]] = relationship(back_populates="investigation", cascade="all, delete-orphan", order_by="InvestigationEvent.created_at")


class InvestigationEvent(Base):
    """Immutable append-only timeline entry for an investigation."""
    __tablename__ = "investigation_events"

    id = Column(String(36), primary_key=True, default=new_uuid)
    investigation_id = Column(String(36), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # note/assign/escalate/resolve/dismiss
    notes = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)  # Extra structured data
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    investigation: Mapped["Investigation"] = relationship(back_populates="events")
    actor: Mapped["User"] = relationship(foreign_keys=[actor_id])


# ─── Audit Log ────────────────────────────────────────────────────────────────

class AuditEvent(Base):
    """
    Immutable system-wide audit log.
    Records are never updated or deleted.
    """
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=new_uuid)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)  # Null for system events
    actor_email = Column(String(255), nullable=True)     # Denormalised for immutability
    action = Column(String(128), nullable=False)          # e.g. "user.login", "prediction.created"
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(128), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    extra = Column(JSON, nullable=True)                  # Additional context
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_audit_events_created_at", "created_at"),
        Index("ix_audit_events_actor_id", "actor_id"),
        Index("ix_audit_events_action", "action"),
    )
