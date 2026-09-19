"""Tests for src.model_evaluation (plotters and metric rows)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.model_evaluation import (
    confusion_rows,
    export_summary,
    run_report_all,
)


def test_confusion_rows_counts_are_correct():
    y = pd.Series([0, 0, 1, 1])
    p = np.array([0.1, 0.9, 0.2, 0.8])
    row = confusion_rows(y, p, 0.5, "demo")
    assert row == {"model": "demo", "threshold": 0.5,
                   "tn": 1, "fp": 1, "fn": 1, "tp": 1}


def test_run_report_all_uses_output_dict_schema():
    from src.fraud_detection import evaluate as feval
    rng = np.random.default_rng(0)
    n = 200
    y_test = pd.Series(rng.binomial(1, 0.1, n))
    probas = {
        "logistic_regression": np.clip(rng.random(n) + y_test * 0.4, 0, 1),
        "random_forest": np.clip(rng.random(n) + y_test * 0.5, 0, 1),
    }
    thresholds = {"logistic_regression": 0.5, "random_forest": 0.5}
    split_val = None
    results = {
        name: feval(y_test, probas[name], thr, name)
        for name, thr in thresholds.items()}
    sample = pd.Series(np.zeros(n))
    out = {
        "splits": (sample, sample, sample, sample, sample, y_test),
        "probas": probas,
        "thresholds": thresholds,
        "results": results,
        "threshold_tables": {name: pd.DataFrame({
            "threshold": [0.5], "precision": [0.5], "recall": [0.5], "f1": [0.5]}
        ) for name in probas},
    }
    run_report_all(out)  # writes to reports/model_eval/ (temp-ish, small)
    summary = export_summary(results)
    assert list(summary.index) == ["logistic_regression", "random_forest"]