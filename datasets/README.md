# CARD-Net Curated Datasets

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
