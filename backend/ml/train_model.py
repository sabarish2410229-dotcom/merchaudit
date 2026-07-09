"""
Train-once model training job.

Run this whenever you want to (re)train the anomaly model — it is
intentionally NOT run automatically by the API on every request.
The API loads whatever is currently saved under models/current/
at startup and only ever does inference.

Usage:
    python backend/ml/train_model.py --n 800 --seed 42 --out models/current
"""

import argparse
import sys
from pathlib import Path

# allow running as `python backend/ml/train_model.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.generate_synthetic_data import generate_dataset
from merchaudit.anomaly_engine import AnomalyEngine


def main():
    parser = argparse.ArgumentParser(description="Train and persist the MerchAudit anomaly model.")
    parser.add_argument("--n", type=int, default=800, help="number of synthetic merchants to train on")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default="models/current", help="output directory for model artifacts")
    args = parser.parse_args()

    dataset_version = f"synthetic-n{args.n}-seed{args.seed}"
    print(f"Generating training data ({dataset_version})...")
    df = generate_dataset(n=args.n, seed=args.seed)

    print("Fitting Isolation Forest...")
    engine = AnomalyEngine()
    engine.fit(df, dataset_version=dataset_version)

    engine.save(args.out)
    print(f"Model saved to {args.out}/")
    print(f"  dataset_version : {engine.metadata['dataset_version']}")
    print(f"  trained_at      : {engine.metadata['trained_at']}")
    print(f"  n_samples       : {engine.metadata['n_training_samples']}")
    print(f"  feature_version : {engine.metadata['feature_version']}")


if __name__ == "__main__":
    main()
