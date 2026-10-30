"""
Dataset Generator Utility for CARD-Net
Generates curated benchmark dataset splits and sample batch files for:
1. Batch screening upload (Mixed, Fraud-only, Legit-only, High-volume 500)
2. Evaluation testing (Held-out chronological split)
3. High-amount anomaly cases
"""
import os
from pathlib import Path
import pandas as pd

def generate():
    root = Path(__file__).resolve().parent
    data_path = root / "ml" / "data" / "creditcard.csv"

    if not data_path.exists():
        print(f"Error: {data_path} not found.")
        return

    out_dirs = [
        root / "datasets",
        root / "frontend" / "public" / "datasets"
    ]

    for d in out_dirs:
        d.mkdir(parents=True, exist_ok=True)

    print(f"Reading benchmark dataset from {data_path}...")
    df = pd.read_csv(data_path)
    total_rows = len(df)
    fraud_count = int(df["Class"].sum())
    print(f"Total rows: {total_rows}, Confirmed frauds: {fraud_count}")

    # 1. Mixed sample (50 rows: 35 legit, 15 fraud)
    legit_35 = df[df["Class"] == 0].iloc[100:135]
    fraud_15 = df[df["Class"] == 1].iloc[:15]
    mixed_50 = pd.concat([legit_35, fraud_15]).sample(frac=1.0, random_state=42).reset_index(drop=True)

    # 2. Fraud only (25 rows) - guaranteed high risk
    fraud_25 = df[df["Class"] == 1].iloc[15:40].reset_index(drop=True)

    # 3. Legit only (50 rows) - normal transactions
    legit_50 = df[df["Class"] == 0].iloc[200:250].reset_index(drop=True)

    # 4. Large benchmark batch (500 rows: 450 legit, 50 fraud)
    legit_450 = df[df["Class"] == 0].iloc[500:950]
    fraud_50 = df[df["Class"] == 1].iloc[40:90]
    large_500 = pd.concat([legit_450, fraud_50]).sample(frac=1.0, random_state=42).reset_index(drop=True)

    # 5. High-value fraud (sorted by transaction Amount descending)
    fraud_high_val = df[df["Class"] == 1].sort_values(by="Amount", ascending=False).iloc[:25].reset_index(drop=True)

    # 6. Evaluation held-out test split (1000 samples from the 20% test split, including test frauds)
    split_idx = int(len(df) * 0.8)
    test_slice = df.iloc[split_idx:]
    test_frauds = test_slice[test_slice["Class"] == 1]
    test_legit = test_slice[test_slice["Class"] == 0]
    
    # 25 test frauds + 975 test legit (2.5% fraud rate test benchmark)
    eval_test_1000 = pd.concat([
        test_legit.sample(n=min(975, len(test_legit)), random_state=42),
        test_frauds.sample(n=min(25, len(test_frauds)), random_state=42)
    ]).sample(frac=1.0, random_state=42).reset_index(drop=True)

    datasets = {
        "sample_batch_mixed_50.csv": (mixed_50, "50 rows (35 legitimate, 15 fraudulent) - Ideal for general batch testing"),
        "sample_batch_fraud_only_25.csv": (fraud_25, "25 rows (100% fraudulent cases) - Test fraud trigger sensitivity"),
        "sample_batch_legit_only_50.csv": (legit_50, "50 rows (100% legitimate transactions) - Test false positive rate"),
        "sample_batch_large_500.csv": (large_500, "500 rows (450 legitimate, 50 fraudulent) - Stress and performance testing"),
        "sample_fraud_high_value_25.csv": (fraud_high_val, "25 rows (Highest-amount fraudulent attacks up to $2,125.87)"),
        "evaluation_test_split_1000.csv": (eval_test_1000, "1,000 rows (Held-out chronological test split with 25 frauds for Evaluation Lab)"),
    }

    manifest = []

    for filename, (dset, desc) in datasets.items():
        frauds = int(dset["Class"].sum()) if "Class" in dset.columns else 0
        legit = len(dset) - frauds
        manifest.append({
            "filename": filename,
            "rows": len(dset),
            "fraud_rows": frauds,
            "legit_rows": legit,
            "description": desc,
            "columns": list(dset.columns),
        })
        for out_dir in out_dirs:
            target_path = out_dir / filename
            dset.to_csv(target_path, index=False)
            print(f"[+] Generated: {target_path} ({len(dset)} rows, {frauds} fraud)")

    # Write manifest JSON for easy consumption by frontend and backend
    import json
    for out_dir in out_dirs:
        manifest_path = out_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"[+] Wrote manifest to {manifest_path}")

    # Generate a comprehensive Markdown documentation for datasets
    readme_path = root / "datasets" / "README.md"
    readme_content = f"""# CARD-Net Curated Datasets

This directory contains standardized benchmark datasets and sample CSV suites extracted from the Kaggle/ULB Credit Card Fraud Detection benchmark (284,807 transactions).

## Available Datasets

| Dataset | Rows | Legitimate | Fraudulent | Fraud Rate | Primary Use Case |
|---|---|---|---|---|---|
| `sample_batch_mixed_50.csv` | 50 | 35 | 15 | 30.0% | Quick testing of batch scoring pipeline & risk categorisation |
| `sample_batch_fraud_only_25.csv` | 25 | 0 | 25 | 100.0% | High-risk triage & alert testing in Investigations UI |
| `sample_batch_legit_only_50.csv` | 50 | 50 | 0 | 0.0% | False positive verification & low-risk score baseline |
| `sample_batch_large_500.csv` | 500 | 450 | 50 | 10.0% | Throughput, batch job scaling & async pipeline validation |
| `sample_fraud_high_value_25.csv` | 25 | 0 | 25 | 100.0% | High financial impact fraud investigation cases |
| `evaluation_test_split_1000.csv` | 1,000 | 998 | 2 | 0.2% | Realistic imbalance chronological held-out test split for Evaluation Lab |

## Column Specification

Every dataset conforms to the schema expected by the TAB-Net ML inference pipeline:
- `Time`: Elapsed seconds since first transaction in the dataset.
- `V1` through `V28`: Principal Component Analysis (PCA) transformed features preserving confidentiality.
- `Amount`: Transaction amount in fiat currency (USD / EUR equivalent).
- `Class`: Ground-truth label (`1` for Fraud, `0` for Legitimate). *Optional during production batch screening; required for Evaluation Lab runs.*

## Usage

### 1. In the Web UI (Batch Screening)
- Open `http://localhost:3000/batch`
- Download or select any sample CSV from the **Sample Datasets** section or drag & drop a file directly.
- Monitor real-time status and view scores on `http://localhost:3000/transactions`.

### 2. In Python / CLI
```python
import pandas as pd
df = pd.read_csv("datasets/sample_batch_mixed_50.csv")
print(df.head())
```

### 3. Re-generating or Customizing
Run:
```bash
python generate_datasets.py
```
"""
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"[+] Wrote datasets documentation to {readme_path}")

if __name__ == "__main__":
    generate()
