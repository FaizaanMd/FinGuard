"""Render Phase 9 evaluation figures (IF vs RF overlap, PR/ROC curves).

Matches the exact Phase 8 test partition and reads RF test predictions from
the model_predictions table, so supervised vs unsupervised comparison is fair.

Run: python -m src.anomaly_eval_plots
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, roc_curve
from sqlalchemy import create_engine, text

from src.config import ANOMALY_REPORTS_DIR, DATABASE_URL, ENGINEERED_FEATURES_PATH
from src.fraud_detection import split_data, load_data

LOGGER = logging.getLogger("finguard.anomaly.plots")


def read_rf_test_predictions() -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        return pd.read_sql(text(
            "SELECT transaction_id, fraud_probability, predicted_label "
            "FROM model_predictions WHERE model_name = 'random_forest' "
            "AND split = 'test'"), conn)


def contingency(scored_test, rf, target_col, n_if=200):
    """Overlap of IF-flagged vs RF-flagged among test FRAUD transactions."""
    y = scored_test.set_index("transaction_id")[target_col]
    if_flagged = scored_test.nlargest(n_if, "risk_score")
    if_ids = set(if_flagged["transaction_id"])
    rf_ids = set(rf.loc[rf["predicted_label"] == 1, "transaction_id"])
    fraud_ids = set(y[y == 1].index)

    both = sorted(if_ids & rf_ids & fraud_ids)
    if_only = sorted((if_ids - rf_ids) & fraud_ids)
    rf_only = sorted((rf_ids - if_ids) & fraud_ids)
    return both, if_only, rf_only


def main() -> None:
    df, X, y = load_data()
    _, _, X_test, _, _, y_test = split_data(X, y)
    test_ids = set(df.loc[X_test.index, "transaction_id"])

    scored = pd.read_csv(Path(__file__).resolve().parent.parent /
                         "data" / "processed" / "anomaly_scores.csv")
    scored_test = scored[scored["transaction_id"].isin(test_ids)].copy()
    rf = read_rf_test_predictions()
    rf = rf[rf["transaction_id"].isin(test_ids)]

    both, if_only, rf_only = contingency(scored_test, rf, "Class")

    LOGGER.info("Among %s test fraud rows: IF-only=%d, RF-only=%d, both=%d",
                int(y_test.sum()), len(if_only), len(rf_only), len(both))

    pr_prec, pr_rec, _ = precision_recall_curve(
        y_test, scored_test["risk_score"])
    fpr, tpr, _ = roc_curve(y_test, scored_test["risk_score"])

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    axes[0].plot(pr_rec, pr_prec, label="Isolation Forest (test)")
    axes[0].axvline(0.779, color="tab:red", ls="--", lw=1,
                    label="RandomForest (test recall)")
    axes[0].set_xlabel("Recall")
    axes[0].set_ylabel("Precision")
    axes[0].set_title("PR curve — unsupervised IF vs RF operating point")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(fpr, tpr, label="Isolation Forest (test)")
    axes[1].plot([0, 1], [0, 1], ls=":", color="gray", label="Random guess")
    axes[1].set_xlabel("False positive rate")
    axes[1].set_ylabel("True positive rate")
    axes[1].set_title("ROC — Isolation Forest (label-free)")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    path = ANOMALY_REPORTS_DIR / "if_pr_roc.png"
    fig.savefig(path, dpi=150)
    LOGGER.info("Saved %s", path)

    fig2, ax = plt.subplots(figsize=(8, 5))
    leg = scored_test[scored_test["Class"] == 0]["risk_score"]
    fra = scored_test[scored_test["Class"] == 1]["risk_score"]
    ax.hist(leg, bins=60, alpha=0.5, label="Legitimate (test)", color="tab:blue")
    ax.hist(fra, bins=60, alpha=0.6, label="Fraud (test)", color="tab:red")
    ax.set_yscale("log")
    ax.set_xlabel("Anomaly risk score (0..1)")
    ax.set_ylabel("Count (log)")
    ax.set_title("Anomaly risk distribution by class (test)")
    ax.legend()
    fig2.tight_layout()
    path2 = ANOMALY_REPORTS_DIR / "if_risk_distribution.png"
    fig2.savefig(path2, dpi=150)
    LOGGER.info("Saved %s", path2)

    pd.DataFrame({
        "category": ["IF_only", "RF_only", "both"],
        "fraud_rows": [len(if_only), len(rf_only), len(both)],
    }).to_csv(ANOMALY_REPORTS_DIR / "detector_overlap.csv", index=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    main()