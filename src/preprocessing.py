#!/usr/bin/env python3
"""
Phase 3: Trajectory Preprocessing & Step-Level Dataset Generation.
Converts complete agent trajectories into step-level ML training examples
with online runtime features and future failure labels.
"""

import json
import os
import sys
import time
import pandas as pd
from sklearn.model_selection import train_test_split

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.signals.feature_extractor import extract_step_features

RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
SAFE_PATH = os.path.join(RAW_DIR, "aftraj_safe.parquet")
UNSAFE_PATH = os.path.join(RAW_DIR, "aftraj_unsafe.parquet")
SPLITS_PATH = os.path.join(RAW_DIR, "splits_test.json")


def assign_trajectory_splits(safe_df: pd.DataFrame, unsafe_df: pd.DataFrame, test_splits: dict, random_state: int = 42):
    """
    Assign each trajectory conv_id to 'train', 'val', or 'test'.
    The test split strictly uses the official benchmark splits_test.json.
    Train and validation splits are stratified by domain and safety status.
    """
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
    print("     PHASE 3: PREPROCESSING & STEP-LEVEL FEATURE EXTRACTION")
    print("=" * 70)

    # 1. Load raw data
    print("\n[1/5] Loading raw datasets...")
    safe_df = pd.read_parquet(SAFE_PATH)
    unsafe_df = pd.read_parquet(UNSAFE_PATH)
    with open(SPLITS_PATH, "r") as f:
        test_splits = json.load(f)

    print(f"      Loaded {len(safe_df)} safe and {len(unsafe_df)} unsafe trajectories.")

    # 2. Assign splits by conv_id
    print("\n[2/5] Partitioning trajectories by conv_id into Train / Val / Test...")
    split_map = assign_trajectory_splits(safe_df, unsafe_df, test_splits)

    split_counts = pd.Series(list(split_map.values())).value_counts()
    print(f"      Trajectories per split:\n{split_counts.to_string()}")

    # 3. Extract step-level features
    print("\n[3/5] Extracting step features for unfolding prefixes...")
    all_step_records = []

    # Process safe trajectories
    for _, row in safe_df.iterrows():
        conv_id = row["conv_id"]
        domain = row["domain"]
        task = str(row["task"] or "")
        turns = list(row["turns"])
        split = split_map[conv_id]

        for step_idx in range(len(turns)):
            record = extract_step_features(
                conv_id=conv_id,
                domain=domain,
                task_text=task,
                turns=turns,
                step_idx=step_idx,
                mistake_step=-1,
                mistake_agent="",
                unsafe_source="safe",
                split=split,
            )
            all_step_records.append(record)

    # Process unsafe trajectories
    for _, row in unsafe_df.iterrows():
        conv_id = row["conv_id"]
        domain = row["domain"]
        task = str(row["task"] or "")
        turns = list(row["turns"])
        split = split_map[conv_id]
        k_star = int(row["mistake_step"])
        a_star = str(row.get("mistake_agent", "") or "")
        source = str(row.get("unsafe_source", "") or "")

        for step_idx in range(len(turns)):
            record = extract_step_features(
                conv_id=conv_id,
                domain=domain,
                task_text=task,
                turns=turns,
                step_idx=step_idx,
                mistake_step=k_star,
                mistake_agent=a_star,
                unsafe_source=source,
                split=split,
            )
            all_step_records.append(record)

    full_df = pd.DataFrame(all_step_records)
    print(f"      Total steps extracted across all runs: {len(full_df):,}")

    # 4. Handle post-failure steps & create clean ML dataset
    print("\n[4/5] Separating pre-failure vs post-failure steps...")
    # Per Requirement 7: Exclude or separately handle prefixes after decisive failure
    clean_df = full_df[full_df["post_failure"] == 0].copy()
    post_failure_count = (full_df["post_failure"] == 1).sum()
    print(f"      Total steps before/at decisive failure (Clean dataset): {len(clean_df):,}")
    print(f"      Post-failure steps excluded from ML training:          {post_failure_count:,}")

    # 5. Save outputs
    print("\n[5/5] Saving processed datasets to data/processed/...")
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    clean_csv_path = os.path.join(PROCESSED_DIR, "step_features_clean.csv")
    clean_df.to_csv(clean_csv_path, index=False)
    print(f"      Saved: {clean_csv_path} ({os.path.getsize(clean_csv_path) / 1024 / 1024:.2f} MB)")

    all_csv_path = os.path.join(PROCESSED_DIR, "step_features_all.csv")
    full_df.to_csv(all_csv_path, index=False)
    print(f"      Saved: {all_csv_path} ({os.path.getsize(all_csv_path) / 1024 / 1024:.2f} MB)")

    # Also save separate split CSVs for quick ML consumption
    for s in ["train", "val", "test"]:
        s_df = clean_df[clean_df["split"] == s]
        s_path = os.path.join(PROCESSED_DIR, f"{s}_features.csv")
        s_df.to_csv(s_path, index=False)
        print(f"      Saved: {s_path} ({len(s_df):,} rows)")

    elapsed = time.time() - start_time
    print(f"\nProcessing completed successfully in {elapsed:.2f} seconds!")

    # Summary Statistics
    print("\n" + "=" * 70)
    print("                    DATASET SUMMARY & LABELS")
    print("=" * 70)
    print("\nClass Balance in Clean Dataset (will_fail):")
    print(clean_df["will_fail"].value_counts(normalize=True).rename({0: "0 (Safe)", 1: "1 (Will Fail)"}))

    print("\nDistribution across Splits:")
    print(pd.crosstab(clean_df["split"], clean_df["will_fail"], margins=True))

    print("\nDistribution across Domains:")
    print(pd.crosstab(clean_df["domain"], clean_df["will_fail"], margins=True))

    print("\nSample Columns & Datatypes:")
    print(clean_df.dtypes.to_string())
    print("=" * 70)


if __name__ == "__main__":
    process_dataset()

