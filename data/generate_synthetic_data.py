"""
Generates synthetic merchant application + transaction-behavior data for
MerchAudit development, testing, and demoing the Streamlit dashboard.

Produces a mix of:
  - normal merchants (revenue and transaction behavior line up)
  - business-rule violators (chargeback spikes, restricted countries, bad tax IDs)
  - anomalous-but-rule-passing merchants (transaction laundering pattern:
    declared revenue is low, actual processing behavior spikes/diverges)

Run:
    python data/generate_synthetic_data.py --n 500 --out data/merchants.csv
"""

import argparse
import random
import string

import numpy as np
import pandas as pd

RNG_SEED = 42
NORMAL_COUNTRIES = ["US", "IN", "GB", "CA", "AU", "DE", "FR", "SG"]
RESTRICTED_COUNTRIES = ["IR", "KP", "SY", "CU", "RU", "BY", "MM", "VE"]
BUSINESS_TYPES = [
    "online bookstore", "coffee shop", "software SaaS", "clothing boutique",
    "consulting firm", "fitness studio", "electronics reseller", "bakery",
]


def _random_tax_id(valid: bool, length: int = 9) -> str:
    digits = [random.randint(0, 9) for _ in range(length)]
    if not valid:
        # force checksum to be a multiple of 10 -> invalid per our demo rule
        remainder = sum(digits) % 10
        digits[-1] = (digits[-1] - remainder) % 10
    else:
        while sum(digits) % 10 == 0:
            digits[-1] = random.randint(0, 9)
    return "".join(str(d) for d in digits)


def generate_merchant(merchant_id: int, profile: str) -> dict:
    declared_revenue = round(np.random.uniform(1000, 20000), 2)

    if profile == "normal":
        country = random.choice(NORMAL_COUNTRIES)
        chargeback_rate = round(np.random.uniform(0.0, 0.8), 3)
        avg_txn = round(declared_revenue / np.random.uniform(20, 60), 2)
        max_txn = round(avg_txn * np.random.uniform(2, 5), 2)
        txn_count = int(np.random.uniform(20, 80))
        pct_intl = round(np.random.uniform(0, 15), 2)
        pct_night = round(np.random.uniform(0, 10), 2)
        burst_ratio = round(np.random.uniform(0.1, 0.6), 3)
        tax_id = _random_tax_id(valid=True)

    elif profile == "rule_violator":
        country = random.choice(RESTRICTED_COUNTRIES + NORMAL_COUNTRIES)
        chargeback_rate = round(np.random.uniform(1.2, 5.0), 3)
        avg_txn = round(declared_revenue / np.random.uniform(20, 60), 2)
        max_txn = round(avg_txn * np.random.uniform(2, 6), 2)
        txn_count = int(np.random.uniform(20, 90))
        pct_intl = round(np.random.uniform(0, 30), 2)
        pct_night = round(np.random.uniform(0, 20), 2)
        burst_ratio = round(np.random.uniform(0.1, 0.8), 3)
        tax_id = _random_tax_id(valid=random.random() > 0.5)

    else:  # transaction_launderer: passes Layer 1, but structurally anomalous
        country = random.choice(NORMAL_COUNTRIES)
        chargeback_rate = round(np.random.uniform(0.0, 0.9), 3)  # stays under radar
        avg_txn = round(declared_revenue / np.random.uniform(20, 60), 2)
        max_txn = round(np.random.uniform(20000, 60000), 2)       # huge burst
        txn_count = int(np.random.uniform(150, 400))               # sudden volume
        pct_intl = round(np.random.uniform(60, 95), 2)              # mostly international
        pct_night = round(np.random.uniform(40, 80), 2)             # odd hours
        burst_ratio = round(max_txn / max(declared_revenue, 1), 3)
        tax_id = _random_tax_id(valid=True)

    return {
        "merchant_id": f"M{merchant_id:05d}",
        "business_name_type": random.choice(BUSINESS_TYPES),
        "country_code": country,
        "tax_id": tax_id,
        "declared_monthly_revenue": declared_revenue,
        "actual_avg_transaction_amount": avg_txn,
        "actual_max_transaction_amount": max_txn,
        "transaction_count_30d": txn_count,
        "pct_international_transactions": pct_intl,
        "pct_night_transactions": pct_night,
        "revenue_burst_ratio": burst_ratio,
        "chargeback_rate_pct": chargeback_rate,
        "profile_label": profile,  # ground truth for dev/testing only, not used by the model
    }


def generate_dataset(n: int, seed: int = RNG_SEED) -> pd.DataFrame:
    random.seed(seed)
    np.random.seed(seed)

    # Realistic mix: mostly normal, some rule violators, a few sneaky launderers
    n_normal = int(n * 0.80)
    n_violator = int(n * 0.13)
    n_launderer = n - n_normal - n_violator

    rows = []
    mid = 1
    for _ in range(n_normal):
        rows.append(generate_merchant(mid, "normal")); mid += 1
    for _ in range(n_violator):
        rows.append(generate_merchant(mid, "rule_violator")); mid += 1
    for _ in range(n_launderer):
        rows.append(generate_merchant(mid, "transaction_launderer")); mid += 1

    df = pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic MerchAudit merchant data.")
    parser.add_argument("--n", type=int, default=500, help="number of merchants to generate")
    parser.add_argument("--out", type=str, default="data/merchants.csv", help="output CSV path")
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    args = parser.parse_args()

    df = generate_dataset(args.n, seed=args.seed)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} synthetic merchant records to {args.out}")
    print(df["profile_label"].value_counts())
