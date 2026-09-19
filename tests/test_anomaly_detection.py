"""Tests for src.anomaly_detection (unsupervised scoring logic)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import MODEL_FEATURE_COLUMNS
from src.anomaly_detection import (
    flag_top_k,
    fit_anomaly_model,
    score_all,
    test_metrics as compute_test_metrics,
    threshold_sweep,
)
from tests.helpers import make_engineered_frame


def test_fit_and_score_returns_bounded_risk():
    df = make_engineered_frame(n=800, seed=20)
    model = fit_anomaly_model(df[MODEL_FEATURE_COLUMNS])
    scored = score_all(df, model)
    assert set(scored.columns) == {
        "transaction_id", "anomaly_score", "risk_score", "Class"}
    assert (scored["risk_score"] >= 0).all()
    assert (scored["risk_score"] <= 1).all()


def test_clear_outlier_gets_high_risk():
    df = make_engineered_frame(n=600, seed=21)
    df.loc[0, "V1"] = 100.0  # synthetic extremal outlier
    model = fit_anomaly_model(df[MODEL_FEATURE_COLUMNS])
    scored = score_all(df, model)
    assert scored.loc[0, "risk_score"] > scored["risk_score"].median()


def test_flag_top_k_returns_exact_size():
    scored = pd.DataFrame({
        "risk_score": np.linspace(0, 1, 500),
        "transaction_id": np.arange(500),
    })
    top = flag_top_k(scored, 0.02)
    assert len(top) == 10
    assert top["risk_score"].min() > 0.97


def test_threshold_sweep_recall_is_monotonic():
    scored = pd.DataFrame({
        "risk_score": np.random.default_rng(0).random(400),
        "Class": np.random.default_rng(1).binomial(1, 0.1, 400),
    })
    sweep = threshold_sweep(scored)
    assert sweep["fraud_captured"].is_monotonic_increasing


def test_test_metrics_are_naive_units():
    y = pd.Series([0] * 90 + [1] * 10)
    risk = np.array([0.1] * 90 + [0.9] * 10)
    scored = pd.DataFrame({"risk_score": risk,
                           "Class": y.to_numpy()})
    metrics = compute_test_metrics(scored)
    assert 0 <= metrics["pr_auc"] <= 1
    assert 0 <= metrics["roc_auc"] <= 1