"""
Tests for Phase 3 Data Preprocessing & Step Feature Extraction.
"""

import os
import pandas as pd
import pytest

PROCESSED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")
CLEAN_CSV = os.path.join(PROCESSED_DIR, "step_features_clean.csv")
ALL_CSV = os.path.join(PROCESSED_DIR, "step_features_all.csv")


def test_files_exist():
    assert os.path.exists(CLEAN_CSV), "step_features_clean.csv must exist"
    assert os.path.exists(ALL_CSV), "step_features_all.csv must exist"


def test_no_conv_id_leakage_between_splits():
    df = pd.read_csv(CLEAN_CSV)
    train_ids = set(df[df["split"] == "train"]["conv_id"].unique())
    val_ids = set(df[df["split"] == "val"]["conv_id"].unique())
    test_ids = set(df[df["split"] == "test"]["conv_id"].unique())

    assert len(train_ids.intersection(val_ids)) == 0, "Train and Val splits share conv_ids!"
    assert len(train_ids.intersection(test_ids)) == 0, "Train and Test splits share conv_ids!"
    assert len(val_ids.intersection(test_ids)) == 0, "Val and Test splits share conv_ids!"


def test_no_post_failure_in_clean_dataset():
    df = pd.read_csv(CLEAN_CSV)
    # In clean dataset, no step should be strictly after mistake_step for unsafe runs
    unsafe_steps = df[df["is_unsafe_traj"] == 1]
    assert (unsafe_steps["step_idx"] > unsafe_steps["mistake_step"]).sum() == 0, (
        "Clean dataset must not contain steps after mistake_step"
    )
    assert (df["post_failure"] == 1).sum() == 0, "Clean dataset should have post_failure == 0"


def test_safe_trajectories_labeling():
    df = pd.read_csv(CLEAN_CSV)
    safe_steps = df[df["is_unsafe_traj"] == 0]
    assert (safe_steps["will_fail"] == 1).sum() == 0, "Safe steps must have will_fail == 0"
    assert (safe_steps["fail_within_3_steps"] == 1).sum() == 0, "Safe steps must have fail_within_3_steps == 0"
    assert (safe_steps["mistake_step"] != -1).sum() == 0, "Safe steps must have mistake_step == -1"


def test_bounded_features():
    df = pd.read_csv(CLEAN_CSV)
    bounded_cols = [
        "tool_failure_rate",
        "content_jaccard_prev",
        "thought_jaccard_prev",
        "stagnation_score_3",
        "lexical_diversity_3",
        "task_token_overlap",
        "cum_task_token_overlap",
    ]
    for col in bounded_cols:
        assert (df[col] < -0.001).sum() == 0, f"{col} has values < 0"
        assert (df[col] > 1.001).sum() == 0, f"{col} has values > 1"

