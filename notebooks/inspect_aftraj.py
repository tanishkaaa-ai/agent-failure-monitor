#!/usr/bin/env python3
"""
AFTraj-2K Dataset Inspection Script
Reads the raw parquet files and inspects schema, turns, annotations, and statistics.
"""

import json
import os
import pandas as pd

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
SAFE_PATH = os.path.join(RAW_DIR, "aftraj_safe.parquet")
UNSAFE_PATH = os.path.join(RAW_DIR, "aftraj_unsafe.parquet")
SPLITS_PATH = os.path.join(RAW_DIR, "splits_test.json")


def inspect():
    print("=" * 70)
    print("           AFTRAJ-2K DATASET INSPECTION & SUMMARY")
    print("=" * 70)

    # 1. Load files
    safe = pd.read_parquet(SAFE_PATH)
    unsafe = pd.read_parquet(UNSAFE_PATH)
    with open(SPLITS_PATH, "r") as f:
        splits = json.load(f)

    # 2. Overall counts
    print(f"\n1. RECORD COUNTS:")
    print(f"   - Safe Trajectories:   {len(safe):>5}")
    print(f"   - Unsafe Trajectories: {len(unsafe):>5}")
    print(f"   - Total Trajectories:  {len(safe) + len(unsafe):>5}")
    print(f"   - Held-out Test Safe:  {len(splits['test_safe']):>5}")
    print(f"   - Held-out Test Unsafe:{len(splits['test_unsafe']):>5}")

    # 3. Schema comparison
    print(f"\n2. SCHEMA:")
    print(f"   - Shared Fields: {sorted(list(set(safe.columns) & set(unsafe.columns)))}")
    diff = list(set(unsafe.columns) - set(safe.columns))
    print(f"   - Unsafe-Only Failure Fields: {sorted(diff)}")

    # 4. Domain distribution
    print(f"\n3. DOMAIN BREAKDOWN:")
    breakdown = pd.DataFrame({
        "Safe": safe["domain"].value_counts(),
        "Unsafe": unsafe["domain"].value_counts()
    }).fillna(0).astype(int)
    breakdown["Total"] = breakdown["Safe"] + breakdown["Unsafe"]
    print(breakdown.to_string())

    # 5. Failure breakdown
    print(f"\n4. FAILURE MECHANISMS IN UNSAFE SET:")
    print(unsafe["unsafe_source"].value_counts().to_string())
    print(f"\nMistake Step (k*) Statistics:")
    print(f"   - Mean step:   {unsafe['mistake_step'].mean():.2f}")
    print(f"   - Median step: {unsafe['mistake_step'].median():.2f}")
    print(f"   - Min / Max:   {int(unsafe['mistake_step'].min())} / {int(unsafe['mistake_step'].max())}")

    # 6. Sample turn inspection
    sample = unsafe.iloc[0]
    print(f"\n5. SAMPLE TRAJECTORY DETAILS:")
    print(f"   - conv_id:        {sample['conv_id']}")
    print(f"   - domain:         {sample['domain']}")
    print(f"   - num_turns:      {sample['num_turns']}")
    print(f"   - mistake_step:   {sample['mistake_step']}")
    print(f"   - mistake_agent:  {sample['mistake_agent']}")
    print(f"   - mistake_reason: {sample['mistake_reason']}")
    print(f"   - task (snippet): {sample['task'][:120]}...")

    turns = sample["turns"]
    print(f"\n   Turn-level Structure ({len(turns)} turns total):")
    print(f"   - Turn schema keys: {list(turns[0].keys())}")
    
    k_star = int(sample["mistake_step"])
    print(f"\n   Pre-Mistake Turn (Step {k_star - 1}):")
    print(f"     Role:    {turns[k_star - 1]['role']}")
    print(f"     Content: {turns[k_star - 1]['content'][:120]}...")

    print(f"\n   Decisive Error Turn (Step {k_star}):")
    print(f"     Role:    {turns[k_star]['role']}")
    print(f"     Action:  {turns[k_star]['action'][:120]}...")
    print(f"     Content: {turns[k_star]['content'][:120]}...")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    inspect()

