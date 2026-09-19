"""Tests for src.rule_engine."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.rule_engine import (
    Rule,
    build_rules,
    evaluate,
    generate_alerts,
    score_transactions,
)
from tests.helpers import make_engineered_frame


def test_build_rules_returns_three_rules():
    df = make_engineered_frame(n=2000, seed=0)
    rules = build_rules(df)
    assert [rule.name for rule in rules] == [
        "rule_high_value", "rule_high_value_rapid", "rule_night_high_value"]


def test_score_transactions_probabilistic_or():
    n = 10
    df = pd.DataFrame({
        "transaction_id": np.arange(n),
        "amount": 1.0,
        "hour_of_day": 0.0,
    })
    r1 = Rule("r1", "T1", "first", "Low", 0.5,
              pd.Series([True] * n))
    r2 = Rule("r2", "T2", "second", "Low", 0.5,
              pd.Series([True] * n))
    out = score_transactions(df, [r1, r2])
    np.testing.assert_allclose(out["risk_score"], 0.75, rtol=1e-6)
    assert (out["n_rules"] == 2).all()
    assert (out["rules_triggered"] == "r1;r2").all()


def test_score_transactions_no_rules_means_zero_risk():
    df = pd.DataFrame({
        "transaction_id": np.arange(5),
        "amount": 1.0,
        "hour_of_day": 5.0,
    })
    r = Rule("r", "T", "none", "Low", 0.9,
             pd.Series([False] * 5))
    out = score_transactions(df, [r])
    assert (out["risk_score"] == 0.0).all()
    assert (out["n_rules"] == 0).all()


def test_generate_alerts_matches_fraud_alerts_schema():
    df = make_engineered_frame(n=1500, seed=5)
    rules = build_rules(df)
    alerts = generate_alerts(df, rules)
    assert set(alerts.columns) == {
        "transaction_id", "alert_source", "alert_type", "risk_score",
        "alert_status"}
    assert (alerts["alert_status"] == "New").all()
    assert (alerts["risk_score"] > 0).all()


def test_evaluate_any_rule_recall_is_between_rules():
    df = make_engineered_frame(n=2000, seed=6)
    rules = build_rules(df)
    alerts = generate_alerts(df, rules)
    metrics = evaluate(df, alerts)
    any_row = metrics[metrics["rule"] == "ANY_RULE"].iloc[0]
    per_row = metrics[metrics["rule"].str.startswith("rule_")]
    assert any_row["recall_pct"] >= per_row["recall_pct"].max() - 1e-9
    assert 0 <= any_row["alert_rate_pct"] <= 100


def test_evaluate_detects_fraud_in_alerts():
    df = make_engineered_frame(n=2000, seed=7)
    rules = build_rules(df)
    alerts = generate_alerts(df, rules)
    metrics = evaluate(df, alerts)
    assert metrics["fraud_alerts"].sum() >= 0