"""
Dataset Ingestion and Seeder for CARD-Net
Allows seeding transactions and running inference from any dataset CSV file or benchmark slice.

Usage:
    # Seed 200 benchmark transactions with real predictions and SHAP attributions:
    python seed_dataset.py --count 200

    # Seed from a specific dataset file:
    python seed_dataset.py --file ../datasets/sample_batch_mixed_50.csv

    # Clear previous transactions and seed fresh:
    python seed_dataset.py --clear --count 150
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
from sqlalchemy import select, delete
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import async_session_factory, engine
from app.db import models as m
from app.ml.inference import tabnet_inference


async def ingest_dataset(file_path: str = None, count: int = 100, clear: bool = False):
    root = Path(__file__).resolve().parent

    # 1. Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(m.Base.metadata.create_all)

    # Resolve CSV path
    if file_path:
        csv_path = Path(file_path)
        if not csv_path.is_absolute():
            csv_path = (root / csv_path).resolve()
    else:
        # Default to full benchmark creditcard.csv or sample
        csv_path = root.parent / "ml" / "data" / "creditcard.csv"
        if not csv_path.exists():
            csv_path = root.parent / "datasets" / "sample_batch_mixed_50.csv"

    if not csv_path.exists():
        print(f"[-] Dataset file not found: {csv_path}")
        return

    print(f"[i] Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path)

    async with async_session_factory() as db:
        # Ensure Admin exists
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

        # Ensure Model exists
        model_version = await db.scalar(
            select(m.ModelVersion).where(m.ModelVersion.channel == "tab_net", m.ModelVersion.is_active == True)
        )
        if not model_version:
            model_version = m.ModelVersion(
                name="XGBoost TAB-Net v1",
                channel="tab_net",
                version_tag="1.0.0",
                description="Primary gradient boosted tabular inference pipeline trained on Kaggle/ULB credit card benchmark.",
                artifact_path="ml_models/latest.pkl",
                hyperparameters={
                    "n_estimators": 500,
                    "learning_rate": 0.05,
                    "max_depth": 6,
                    "scale_pos_weight": "imbalance_weighted",
                },
                feature_names=tabnet_inference.FEATURE_NAMES,
                is_active=True,
                is_experimental=False,
                registered_by_id=admin.id,
                notes="Trained on held-out chronological split.",
            )
            db.add(model_version)
            await db.commit()
            await db.refresh(model_version)

        # Optional clear
        if clear:
            print("[i] Clearing existing transactions, predictions, investigations...")
            await db.execute(delete(m.InvestigationEvent))
            await db.execute(delete(m.Investigation))
            await db.execute(delete(m.Prediction))
            await db.execute(delete(m.Transaction))
            await db.commit()
            print("[+] Cleared.")

        # Prepare sample subset
        if "Class" in df.columns and count and count < len(df):
            # Select balanced ratio (approx 80% legit, 20% fraud or natural if available)
            fraud_available = df[df["Class"] == 1]
            legit_available = df[df["Class"] == 0]

            fraud_target = min(len(fraud_available), max(5, int(count * 0.2)))
            legit_target = min(len(legit_available), count - fraud_target)

            sample_df = pd.concat([
                legit_available.sample(n=legit_target, random_state=42),
                fraud_available.sample(n=fraud_target, random_state=42)
            ]).sample(frac=1.0, random_state=42).reset_index(drop=True)
        else:
            sample_df = df.iloc[:count] if count else df

        print(f"[i] Preparing to seed {len(sample_df)} records (frauds: {sample_df['Class'].sum() if 'Class' in sample_df else 'N/A'})...")

        # Load inference pipeline
        tabnet_inference.ensure_model_loaded()

        now = datetime.now(timezone.utc)
        high_risk_tx_ids = []

        for i, row in sample_df.iterrows():
            tx = m.Transaction(
                external_id=f"tx-seed-{int(now.timestamp())}-{i+1}",
                time_seconds=float(row.get("Time", 0)),
                amount=float(row.get("Amount", 0)),
                ground_truth_label=int(row["Class"]) if "Class" in row else None,
                imported_at=now - timedelta(days=float(len(sample_df) - i) / 10.0),
                v1=float(row.get("V1", 0)), v2=float(row.get("V2", 0)), v3=float(row.get("V3", 0)), v4=float(row.get("V4", 0)),
                v5=float(row.get("V5", 0)), v6=float(row.get("V6", 0)), v7=float(row.get("V7", 0)), v8=float(row.get("V8", 0)),
                v9=float(row.get("V9", 0)), v10=float(row.get("V10", 0)), v11=float(row.get("V11", 0)), v12=float(row.get("V12", 0)),
                v13=float(row.get("V13", 0)), v14=float(row.get("V14", 0)), v15=float(row.get("V15", 0)), v16=float(row.get("V16", 0)),
                v17=float(row.get("V17", 0)), v18=float(row.get("V18", 0)), v19=float(row.get("V19", 0)), v20=float(row.get("V20", 0)),
                v21=float(row.get("V21", 0)), v22=float(row.get("V22", 0)), v23=float(row.get("V23", 0)), v24=float(row.get("V24", 0)),
                v25=float(row.get("V25", 0)), v26=float(row.get("V26", 0)), v27=float(row.get("V27", 0)), v28=float(row.get("V28", 0)),
            )
            db.add(tx)
            await db.flush()

            feat_dict = {f: float(row[f]) for f in tabnet_inference.FEATURE_NAMES if f in row}
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

            if risk == "high":
                high_risk_tx_ids.append(tx.id)

        await db.commit()
        print(f"[+] Successfully seeded {len(sample_df)} transactions and predictions!")
        print(f"[+] Flagged high-risk transactions: {len(high_risk_tx_ids)}")

        # Create investigations for up to 3 high-risk transactions
        for tx_id in high_risk_tx_ids[:3]:
            existing_inv = await db.scalar(select(m.Investigation).where(m.Investigation.transaction_id == tx_id))
            if not existing_inv:
                inv = m.Investigation(
                    transaction_id=tx_id,
                    status="open",
                    priority="high",
                    opened_by_id=admin.id,
                    opened_at=now - timedelta(hours=1),
                    updated_at=now,
                )
                db.add(inv)
                await db.flush()
                event = m.InvestigationEvent(
                    investigation_id=inv.id,
                    event_type="note",
                    actor_id=admin.id,
                    notes="Automated alert: High fraud probability identified by TAB-Net model. Attributions logged.",
                    created_at=now,
                )
                db.add(event)
        await db.commit()
        print(f"[+] Active investigations created.")


def main():
    parser = argparse.ArgumentParser(description="Ingest benchmark or custom CSV dataset into CARD-Net database.")
    parser.add_argument("--file", "-f", type=str, default=None, help="Path to CSV dataset file.")
    parser.add_argument("--count", "-n", type=int, default=100, help="Number of records to seed (default: 100).")
    parser.add_argument("--clear", "-c", action="store_true", help="Clear existing transactions before seeding.")

    args = parser.parse_args()
    asyncio.run(ingest_dataset(file_path=args.file, count=args.count, clear=args.clear))


if __name__ == "__main__":
    main()

