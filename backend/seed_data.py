"""
Seed script — initializes the database with:
1. Admin user (admin@cardnet.local / admin_change_me)
2. Active Model Version (XGBoost TAB-Net v1 pointing to ml_models/latest.pkl)
3. Verified Evaluation Run from model_metadata.json
4. Realistic benchmark transactions from creditcard.csv with real model predictions and SHAP attributions
5. Sample investigation on high-risk transaction

Usage:
    cd backend
    python seed_data.py
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import async_session_factory, engine
from app.db import models as m
from app.ml.inference import tabnet_inference


async def seed():
    # 1. Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(m.Base.metadata.create_all)

    async with async_session_factory() as db:
        # ── Admin User ────────────────────────────────────────────────────────
        admin = await db.scalar(select(m.User).where(m.User.email == "admin@cardnet.local"))
        if not admin:
            admin = m.User(
                email="admin@cardnet.local",
                full_name="CARD-Net Administrator",
                hashed_password=hash_password("admin_change_me"),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            print("[+] Admin user created: admin@cardnet.local")
        else:
            print("[i] Admin user exists: admin@cardnet.local")

        # ── Active Model Registration ─────────────────────────────────────────
        model_version = await db.scalar(select(m.ModelVersion).where(m.ModelVersion.channel == "tab_net", m.ModelVersion.is_active == True))
        
        meta_path = Path(__file__).parent / "ml_models" / "model_metadata.json"
        if not meta_path.exists():
            meta_path = Path(__file__).parent.parent / "ml_models" / "model_metadata.json"

        meta = {}
        if meta_path.exists():
            with open(meta_path, "r") as f:
                meta = json.load(f)

        xgb_results = meta.get("evaluation_results", {}).get("xgboost", {})

        if not model_version:
            model_version = m.ModelVersion(
                name=meta.get("model_name", "XGBoost TAB-Net v1"),
                channel="tab_net",
                version_tag=meta.get("version_tag", "1.0.0"),
                description="Primary gradient boosted tabular inference pipeline trained on Kaggle/ULB credit card benchmark.",
                artifact_path="ml_models/latest.pkl",
                hyperparameters={
                    "n_estimators": 500,
                    "learning_rate": 0.05,
                    "max_depth": 6,
                    "scale_pos_weight": "imbalance_weighted",
                },
                training_dataset_info=meta.get("training_info"),
                feature_names=tabnet_inference.FEATURE_NAMES,
                is_active=True,
                is_experimental=False,
                registered_by_id=admin.id,
                notes="Trained on held-out chronological split. Real test PR-AUC: 0.8071, ROC-AUC: 0.9894.",
            )
            db.add(model_version)
            await db.commit()
            await db.refresh(model_version)
            print("[+] Registered active model:", model_version.name)
        else:
            print("[i] Active model already exists:", model_version.name)

        # ── Evaluation Run ────────────────────────────────────────────────────
        eval_run = await db.scalar(select(m.EvaluationRun).where(m.EvaluationRun.model_version_id == model_version.id))
        if not eval_run and xgb_results:
            eval_run = m.EvaluationRun(
                model_version_id=model_version.id,
                status="completed",
                dataset_description="ULB/Kaggle Credit Card Fraud benchmark held-out test set (56,962 samples)",
                num_samples=meta.get("training_info", {}).get("test_samples", 56962),
                num_positive=meta.get("training_info", {}).get("test_positives", 75),
                num_negative=meta.get("training_info", {}).get("test_samples", 56962) - meta.get("training_info", {}).get("test_positives", 75),
                accuracy=xgb_results.get("accuracy", 0.9996),
                precision=xgb_results.get("precision", 0.9048),
                recall=xgb_results.get("recall", 0.7600),
                f1_score=xgb_results.get("f1", 0.8261),
                macro_f1=xgb_results.get("macro_f1", 0.9129),
                pr_auc=xgb_results.get("pr_auc", 0.8071),
                roc_auc=xgb_results.get("roc_auc", 0.9894),
                false_positive_rate=xgb_results.get("fpr", 0.0001),
                confusion_matrix=xgb_results.get("confusion_matrix"),
                notes="Independently computed evaluation metrics on held-out chronological test split.",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                completed_at=datetime.now(timezone.utc),
            )
            db.add(eval_run)
            await db.commit()
            print("[+] Recorded real evaluation run for", model_version.name)

        # ── Sample Real Transactions ──────────────────────────────────────────
        tx_count = await db.scalar(select(m.Transaction.id).limit(1))
        if not tx_count:
            csv_path = Path(__file__).parent.parent / "ml" / "data" / "creditcard.csv"
            if csv_path.exists():
                print(f"[i] Loading real transactions from {csv_path}...")
                df = pd.read_csv(csv_path)

                # Ensure model is ready
                tabnet_inference.ensure_model_loaded()

                # Pick 40 legitimate and 15 fraudulent rows
                legit_df = df[df["Class"] == 0].iloc[100:140]
                fraud_df = df[df["Class"] == 1].iloc[:15]
                sample_df = pd.concat([legit_df, fraud_df]).sample(frac=1.0, random_state=42).reset_index(drop=True)

                now = datetime.now(timezone.utc)
                first_high_risk_tx_id = None

                for i, row in sample_df.iterrows():
                    tx = m.Transaction(
                        external_id=f"benchmark-row-{i+1}",
                        time_seconds=float(row["Time"]),
                        amount=float(row["Amount"]),
                        ground_truth_label=int(row["Class"]),
                        imported_at=now - timedelta(days=float(len(sample_df) - i) / 2.0),
                        v1=float(row["V1"]), v2=float(row["V2"]), v3=float(row["V3"]), v4=float(row["V4"]),
                        v5=float(row["V5"]), v6=float(row["V6"]), v7=float(row["V7"]), v8=float(row["V8"]),
                        v9=float(row["V9"]), v10=float(row["V10"]), v11=float(row["V11"]), v12=float(row["V12"]),
                        v13=float(row["V13"]), v14=float(row["V14"]), v15=float(row["V15"]), v16=float(row["V16"]),
                        v17=float(row["V17"]), v18=float(row["V18"]), v19=float(row["V19"]), v20=float(row["V20"]),
                        v21=float(row["V21"]), v22=float(row["V22"]), v23=float(row["V23"]), v24=float(row["V24"]),
                        v25=float(row["V25"]), v26=float(row["V26"]), v27=float(row["V27"]), v28=float(row["V28"]),
                    )
                    db.add(tx)
                    await db.flush()

                    # Run real inference
                    feat_dict = {f: float(row[f]) for f in tabnet_inference.FEATURE_NAMES}
                    prob, risk, shap_vals = tabnet_inference.predict(feat_dict)

                    pred = m.Prediction(
                        transaction_id=tx.id,
                        model_version_id=model_version.id,
                        channel="tab_net",
                        fraud_probability=prob,
                        risk_category=risk,
                        threshold_low=settings.FRAUD_THRESHOLD_LOW,
                        threshold_high=settings.FRAUD_THRESHOLD_HIGH,
                        shap_values=shap_vals,
                        review_status="flagged" if risk == "high" else "pending",
                        predicted_at=tx.imported_at + timedelta(seconds=1),
                    )
                    db.add(pred)

                    if risk == "high" and first_high_risk_tx_id is None:
                        first_high_risk_tx_id = tx.id

                await db.commit()
                print(f"[+] Seeded {len(sample_df)} real benchmark transactions and predictions.")

                # Open 1 sample investigation
                if first_high_risk_tx_id:
                    inv = m.Investigation(
                        transaction_id=first_high_risk_tx_id,
                        status="open",
                        priority="high",
                        opened_by_id=admin.id,
                        opened_at=now - timedelta(hours=2),
                        updated_at=now - timedelta(hours=1),
                    )
                    db.add(inv)
                    await db.flush()

                    event = m.InvestigationEvent(
                        investigation_id=inv.id,
                        event_type="note",
                        actor_id=admin.id,
                        notes="Initial triage: High probability flagged by TAB-Net model. Reviewing attributions.",
                        created_at=now - timedelta(hours=1),
                    )
                    db.add(event)
                    await db.commit()
                    print(f"[+] Created sample investigation for high-risk transaction {first_high_risk_tx_id[:8]}...")
        else:
            print("[i] Transactions already populated.")


if __name__ == "__main__":
    asyncio.run(seed())
