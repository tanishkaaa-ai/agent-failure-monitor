"""
Unit Tests for Phase 10 Testing and Evaluation Pipeline.
Validates generation of metrics CSVs and publication figures.
"""

import os
import pandas as pd
import pytest

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
METRICS_CSV = os.path.join(RESULTS_DIR, "metrics_comparison.csv")
TRAJ_CSV = os.path.join(RESULTS_DIR, "trajectory_evaluation.csv")
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")


def test_evaluation_csv_artifacts_exist():
    assert os.path.exists(METRICS_CSV), "metrics_comparison.csv must exist"
    assert os.path.exists(TRAJ_CSV), "trajectory_evaluation.csv must exist"

    df_metrics = pd.read_csv(METRICS_CSV)
    assert len(df_metrics) == 4, "Must evaluate all 4 configurations"
    assert "ROC-AUC" in df_metrics.columns
    assert "F1-Score" in df_metrics.columns


def test_trajectory_lead_times():
    df_traj = pd.read_csv(TRAJ_CSV)
    assert len(df_traj) == 4
    for _, row in df_traj.iterrows():
        assert row["Mean_Lead_Time_Steps"] >= 0.0
        assert 0.0 <= row["Detection_Rate"] <= 1.0


def test_figures_exist():
    expected_figures = [
        "metrics_comparison.png",
        "confusion_matrices.png",
        "lead_time_distribution.png",
        "roc_curve.png",
    ]
    for fig_name in expected_figures:
        fig_path = os.path.join(FIGURES_DIR, fig_name)
        assert os.path.exists(fig_path), f"Figure {fig_name} must exist"
        assert os.path.getsize(fig_path) > 1000, f"Figure {fig_name} must not be empty"

