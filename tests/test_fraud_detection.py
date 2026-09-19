"""Tests for src.fraud_detection (training pipeline, no database)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from src.fraud_detection import (
    evaluate,
    make_pipeline,
    split_data,
    train_models,
    tune_threshold,
)
from tests.helpers import make_synthetic_raw, make_engineered_frame


def _learnable_frame(n=2000, seed=10):
    df = make_engineered_frame(n=n, seed=seed)
    X = df[[f"V{i}" for i in range(1, 29)]]
    return X, df["Class"]


def test_split_proportions_follow_config():
    X, y = _learnable_frame()
    X_tr, X_val, X_te, y_tr, y_val, y_te = split_data(X, y)
    total = len(X)
    assert abs(len(X_tr) / total - 0.6) < 1e-9
    assert abs(len(X_val) / total - 0.2) < 1e-9
    assert abs(len(X_te) / total - 0.2) < 1e-9


def test_split_is_stratified():
    X, y = _learnable_frame()
    _, _, _, y_tr, _, y_te = split_data(X, y)
    assert abs(y_tr.mean() - y.mean()) < 0.02
    assert abs(y_te.mean() - y.mean()) < 0.02


def test_pipeline_scaler_is_fit_on_training_data_only():
    X, y = _learnable_frame()
    X_tr, X_val, X_te, y_tr, _, _ = split_data(X, y)
    pipe = make_pipeline(_fast_model())
    pipe.fit(X_tr, y_tr)
    np.testing.assert_allclose(
        pipe.named_steps["scaler"].mean_,
        X_tr.mean(axis=0).to_numpy())
    np.testing.assert_allclose(
        pipe.named_steps["scaler"].scale_,
        X_tr.std(axis=0, ddof=0).to_numpy())


def _fast_model():
    from sklearn.ensemble import RandomForestClassifier
    return RandomForestClassifier(
        n_estimators=10, max_depth=4, random_state=0)


def test_models_train_and_score_in_unit_range():
    X, y = _learnable_frame()
    X_tr, _, X_te, y_tr, _, _ = split_data(X, y)
    models = train_models(X_tr, y_tr)
    assert set(models) == {"logistic_regression", "random_forest"}
    for pipe in models.values():
        proba = pipe.predict_proba(X_te)[:, 1]
        assert ((proba >= 0) & (proba <= 1)).all()


def test_tune_threshold_improves_f1_over_default():
    rng = np.random.default_rng(0)
    y = np.array([0] * 900 + [1] * 100)
    p = np.clip(rng.beta(a=1.0, b=3.0, size=len(y)) + y * 0.6, 0, 1)
    best, table = tune_threshold(pd.Series(y), p)
    assert table["f1"].max() <= 1.0
    best_f1 = f1_score(y, (p >= best).astype(int))
    assert best_f1 >= f1_score(y, (p >= 0.5).astype(int)) - 1e-9


def test_evaluate_counts_are_exact():
    y = pd.Series([0, 0, 1, 1, 1])
    p = np.array([0.1, 0.9, 0.2, 0.8, 0.95])
    m = evaluate(y, p, 0.5, "demo")
    assert m["tp"] == 2 and m["fp"] == 1 and m["fn"] == 1 and m["tn"] == 1
    assert m["n_alerts"] == 3 and m["fraud_captured"] == 2


def test_features_influence_probabilities():
    df = make_engineered_frame(n=3000, seed=11)
    X = df[[f"V{i}" for i in range(1, 29)]]
    y = df["Class"]
    X_tr, _, X_te, y_tr, _, y_te = split_data(X, y)
    pipe = make_pipeline(_fast_model())
    pipe.fit(X_tr, y_tr)
    probs = pipe.predict_proba(X_te)[:, 1]
    assert probs[y_te == 1].mean() > probs[y_te == 0].mean()


def test_endpoint_smoke_rule_pipeline_on_synthetic():
    df = make_synthetic_raw(n=1200, seed=12)
    from src.data_cleaning import clean
    from src.feature_engineering import build_features
    from src.rule_engine import run
    cleaned, _ = clean(df)
    features = build_features(cleaned)
    out = run(frame=features)
    assert out["metrics"]["rule"].tolist()[-1] == "ANY_RULE"
    assert out["metrics"]["alert_rate_pct"].max() < 100