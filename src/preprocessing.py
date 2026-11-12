#!/usr/bin/env python3
"""
Phase 3/4 Preprocessing & Dataset Generation.
Uses RuntimeSignalsEngine directly to ensure 100% feature alignment
between offline training and live real-time inference.
"""

import json
import os
import sys
import time
import pandas as pd
from sklearn.model_selection import train_test_split

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.signals.engine import RuntimeSignalsEngine, SignalVector

RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
SAFE_PATH = os.path.join(RAW_DIR, "aftraj_safe.parquet")
UNSAFE_PATH = os.path.join(RAW_DIR, "aftraj_unsafe.parquet")
SPLITS_PATH = os.path.join(RAW_DIR, "splits_test.json")


def assign_trajectory_splits(safe_df: pd.DataFrame, unsafe_df: pd.DataFrame, test_splits: dict, random_state: int = 42):
    test_safe_ids = set(test_splits["test_safe"])
    test_unsafe_ids = set(test_splits["test_unsafe"])

    meta_records = []
    for _, row in safe_df.iterrows():
        meta_records.append({
            "conv_id": row["conv_id"],
            "domain": row["domain"],
            "is_safe": 1,
            "is_test": int(row["conv_id"] in test_safe_ids)
        })
    for _, row in unsafe_df.iterrows():
        meta_records.append({
            "conv_id": row["conv_id"],
            "domain": row["domain"],
            "is_safe": 0,
            "is_test": int(row["conv_id"] in test_unsafe_ids)
        })

    meta_df = pd.DataFrame(meta_records)

    test_df = meta_df[meta_df["is_test"] == 1].copy()
    test_df["split"] = "test"

    train_val_pool = meta_df[meta_df["is_test"] == 0].copy()
    strat_key = train_val_pool["domain"] + "_" + train_val_pool["is_safe"].astype(str)

    train_df, val_df = train_test_split(
        train_val_pool,
        test_size=0.20,
        random_state=random_state,
        stratify=strat_key
    )
    train_df["split"] = "train"
    val_df["split"] = "val"

    split_map = dict(zip(
        pd.concat([train_df, val_df, test_df])["conv_id"],
        pd.concat([train_df, val_df, test_df])["split"]
    ))
    return split_map


def process_dataset():
    start_time = time.time()
    print("=" * 70)
    print("  PREPROCESSING WITH RUNTIME SIGNALS ENGINE (100% FEATURE ALIGNMENT)")
    print("=" * 70)

    safe_df = pd.read_parquet(SAFE_PATH)
    unsafe_df = pd.read_parquet(UNSAFE_PATH)
    with open(SPLITS_PATH, "r") as f:
        test_splits = json.load(f)

    split_map = assign_trajectory_splits(safe_df, unsafe_df, test_splits)
    engine = RuntimeSignalsEngine()

    all_records = []

    # Safe trajectories
    for _, row in safe_df.iterrows():
        conv_id = row["conv_id"]
        domain = row["domain"]
        task = str(row["task"] or "")
        turns = list(row["turns"])
        split = split_map[conv_id]

        signals = engine.evaluate_prefix(turns, task_prompt=task)
        for sig in signals:
            d = sig.to_dict()
            d["conv_id"] = conv_id
            d["split"] = split
            d["domain"] = domain
            d["mistake_step"] = -1
            d["mistake_agent"] = "none"
            d["is_unsafe_traj"] = 0
            d["post_failure"] = 0
            d["steps_to_failure"] = -1
            d["fail_within_3_steps"] = 0
            d["fail_within_5_steps"] = 0
            d["will_fail"] = 0
            all_records.append(d)

    # Unsafe trajectories
    for _, row in unsafe_df.iterrows():
        conv_id = row["conv_id"]
        domain = row["domain"]
        task = str(row["task"] or "")
        turns = list(row["turns"])
        split = split_map[conv_id]
        k_star = int(row["mistake_step"])
        a_star = str(row.get("mistake_agent", "") or "none")

        signals = engine.evaluate_prefix(turns, task_prompt=task)
        for sig in signals:
            step_idx = sig.step_idx
            post_failure = int(step_idx > k_star)
            steps_to_failure = k_star - step_idx
            will_fail = int(step_idx <= k_star)
            fail_within_3 = int(0 <= steps_to_failure <= 3)
            fail_within_5 = int(0 <= steps_to_failure <= 5)

            d = sig.to_dict()
            d["conv_id"] = conv_id
            d["split"] = split
            d["domain"] = domain
            d["mistake_step"] = k_star
            d["mistake_agent"] = a_star
            d["is_unsafe_traj"] = 1
            d["post_failure"] = post_failure
            d["steps_to_failure"] = steps_to_failure
            d["fail_within_3_steps"] = fail_within_3
            d["fail_within_5_steps"] = fail_within_5
            d["will_fail"] = will_fail
            all_records.append(d)

    full_df = pd.DataFrame(all_records)
    clean_df = full_df[full_df["post_failure"] == 0].copy()

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    clean_csv_path = os.path.join(PROCESSED_DIR, "step_features_clean.csv")
    clean_df.to_csv(clean_csv_path, index=False)

    all_csv_path = os.path.join(PROCESSED_DIR, "step_features_all.csv")
    full_df.to_csv(all_csv_path, index=False)

    for s in ["train", "val", "test"]:
        s_df = clean_df[clean_df["split"] == s]
        s_df.to_csv(os.path.join(PROCESSED_DIR, f"{s}_features.csv"), index=False)

    elapsed = time.time() - start_time
    print(f"Done in {elapsed:.2f}s! Clean steps: {len(clean_df):,} | Post-failure excluded: {len(full_df) - len(clean_df):,}")
    print(f"Saved: {clean_csv_path}")


if __name__ == "__main__":
    process_dataset()
