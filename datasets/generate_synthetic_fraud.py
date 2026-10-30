"""
Synthetic Fraud Scenario Dataset Generator for CARD-Net
Generates customizable synthetic transaction datasets mimicking real-world card fraud scenarios:
1. Micro-transaction Card Testing: Rapid low-amount transactions ($0.50 - $5.00)
2. High-Velocity Bust-Out: Rapid-fire high-amount transactions ($800 - $3,000)
3. Abnormal PCA Anomaly: Statistical outlier vectors representing compromised credentials
4. Custom Mix: Specify any total rows and fraud percentage
"""
import argparse
import os
from pathlib import Path
import numpy as np
import pandas as pd

FEATURE_NAMES = [f"V{i}" for i in range(1, 29)]

def generate_synthetic_dataset(
    scenario: str = "mixed",
    total_samples: int = 100,
    fraud_ratio: float = 0.2,
    output_path: str = None,
):
    np.random.seed(42)
    n_fraud = int(total_samples * fraud_ratio)
    n_legit = total_samples - n_fraud

    # Baseline legitimate PCA distribution: standard normal with small variations
    legit_features = np.random.normal(loc=0.0, scale=1.0, size=(n_legit, 28))
    legit_time = np.sort(np.random.uniform(0, 172800, size=n_legit)) # 48 hour window
    legit_amount = np.random.exponential(scale=70.0, size=n_legit).clip(1.0, 1500.0)

    # Scenarios for fraud
    if scenario == "card_testing":
        # Low amounts, high cluster in specific PCA directions (e.g. V14, V12, V4)
        fraud_features = np.random.normal(loc=0.0, scale=1.0, size=(n_fraud, 28))
        fraud_features[:, 13] -= 5.0  # V14 negative drift
        fraud_features[:, 11] -= 4.0  # V12 negative drift
        fraud_features[:, 3] += 3.5   # V4 positive shift
        fraud_time = np.sort(np.random.uniform(10000, 20000, size=n_fraud)) # tight burst
        fraud_amount = np.random.uniform(0.50, 4.99, size=n_fraud)
    elif scenario == "bust_out":
        # High amounts, pronounced anomaly on V17, V14, V10, V4
        fraud_features = np.random.normal(loc=0.0, scale=1.2, size=(n_fraud, 28))
        fraud_features[:, 16] -= 6.0  # V17 strong negative
        fraud_features[:, 13] -= 5.5  # V14 strong negative
        fraud_features[:, 9] -= 4.5   # V10
        fraud_features[:, 3] += 4.0   # V4 strong positive
        fraud_time = np.sort(np.random.uniform(50000, 70000, size=n_fraud))
        fraud_amount = np.random.uniform(500.0, 3500.0, size=n_fraud)
    else:  # Mixed scenario
        fraud_features = np.random.normal(loc=0.0, scale=1.0, size=(n_fraud, 28))
        fraud_features[:, 16] -= 4.5  # V17
        fraud_features[:, 13] -= 4.8  # V14
        fraud_features[:, 11] -= 3.8  # V12
        fraud_features[:, 9] -= 3.2   # V10
        fraud_features[:, 3] += 3.0   # V4
        fraud_time = np.sort(np.random.uniform(0, 172800, size=n_fraud))
        fraud_amount = np.random.exponential(scale=180.0, size=n_fraud).clip(5.0, 2500.0)

    # Assemble Legit Dataframe
    df_legit = pd.DataFrame(legit_features, columns=FEATURE_NAMES)
    df_legit["Time"] = legit_time
    df_legit["Amount"] = np.round(legit_amount, 2)
    df_legit["Class"] = 0

    # Assemble Fraud Dataframe
    df_fraud = pd.DataFrame(fraud_features, columns=FEATURE_NAMES)
    df_fraud["Time"] = fraud_time
    df_fraud["Amount"] = np.round(fraud_amount, 2)
    df_fraud["Class"] = 1

    # Combine, sort chronologically and reorder columns
    full_df = pd.concat([df_legit, df_fraud]).sort_values(by="Time").reset_index(drop=True)
    cols = ["Time"] + FEATURE_NAMES + ["Amount", "Class"]
    full_df = full_df[cols]

    if output_path is None:
        out_dir = Path(__file__).resolve().parent
        output_path = out_dir / f"synthetic_{scenario}_{total_samples}.csv"
    else:
        output_path = Path(output_path)

    full_df.to_csv(output_path, index=False)
    print(f"[+] Created synthetic dataset: {output_path}")
    print(f"    Total rows: {len(full_df)} | Fraud rows: {n_fraud} ({fraud_ratio*100:.1f}%) | Legit rows: {n_legit}")
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic card fraud datasets.")
    parser.add_argument("--scenario", "-s", choices=["mixed", "card_testing", "bust_out"], default="mixed")
    parser.add_argument("--samples", "-n", type=int, default=100, help="Total sample count.")
    parser.add_argument("--fraud-ratio", "-r", type=float, default=0.2, help="Proportion of fraud samples (0.0 to 1.0).")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output CSV path.")

    args = parser.parse_args()
    generate_synthetic_dataset(args.scenario, args.samples, args.fraud_ratio, args.output)

