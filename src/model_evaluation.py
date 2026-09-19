"""Model evaluation artefacts (PR curves, threshold sweeps, confusion).

All curves use held-out test probabilities already computed by
src.fraud_detection; no threshold is tuned here. Plots are saved to
reports/model_eval/ and metrics are returned as DataFrames for logging.
"""
from __future__ import annotations

import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_curve,
)

from src.config import MODEL_EVAL_DIR

LOGGER = logging.getLogger("finguard.modeval")

MODELS = {
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
}


def confusion_rows(y, proba, threshold, model_name):
    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
    return {"model": model_name, "threshold": threshold,
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def plot_pr_curves(model_names, probas, y_test):
    fig, ax = plt.subplots(figsize=(8, 6))
    for name in model_names:
        p, r, _ = precision_recall_curve(y_test, probas[name])
        ax.plot(r, p, label=MODELS.get(name, name))
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall curves (held-out test)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = MODEL_EVAL_DIR / "pr_curves.png"
    fig.savefig(path, dpi=150)
    LOGGER.info("Saved %s", path)


def plot_threshold_sweeps(model_names, tables):
    fig, axes = plt.subplots(1, len(model_names), figsize=(13, 5),
                             sharey=False)
    if len(model_names) == 1:
        axes = [axes]
    for axis, name in zip(axes, model_names):
        t = tables[name]
        axis.plot(t["threshold"], t["precision"], label="Precision")
        axis.plot(t["threshold"], t["recall"], label="Recall")
        axis.plot(t["threshold"], t["f1"], label="F1")
        axis.set_title(MODELS.get(name, name))
        axis.set_xlabel("Threshold")
        axis.set_ylim(0, 1)
        axis.legend()
        axis.grid(alpha=0.3)
    fig.suptitle("Validation threshold sweep (F1-optimal point chosen here)")
    fig.tight_layout()
    path = MODEL_EVAL_DIR / "threshold_sweeps.png"
    fig.savefig(path, dpi=150)
    LOGGER.info("Saved %s", path)


def plot_confusion_matrices(model_names, y_test, probas, thresholds):
    fig, axes = plt.subplots(1, len(model_names), figsize=(12, 4.5))
    if len(model_names) == 1:
        axes = [axes]
    for axis, name in zip(axes, model_names):
        pred = (probas[name] >= thresholds[name]).astype(int)
        cm = confusion_matrix(y_test, pred)
        im = axis.imshow(cm, cmap="Blues")
        axis.set_title(f"{MODELS.get(name, name)} (thr={thresholds[name]:.2f})")
        axis.set_xlabel("Predicted")
        axis.set_ylabel("True")
        for i in range(2):
            for j in range(2):
                axis.text(j, i, f"{cm[i, j]:,}", ha="center", va="center")
        fig.colorbar(im, ax=axis, shrink=0.85)
    fig.tight_layout()
    path = MODEL_EVAL_DIR / "confusion_matrices.png"
    fig.savefig(path, dpi=150)
    LOGGER.info("Saved %s", path)


def export_summary(results):
    rows = [dict(v) for v in results.values()]
    df = pd.DataFrame(rows).set_index("model")
    path = MODEL_EVAL_DIR / "metrics.csv"
    df.to_csv(path)
    LOGGER.info("Saved %s", path)
    return df


def run_report_all(out):
    """Render every evaluation artefact from a fraud_detection.run() dict."""
    y_test = out["splits"][5]
    model_names = list(out["probas"].keys())
    plot_pr_curves(model_names, out["probas"], y_test)
    plot_threshold_sweeps(model_names, out["threshold_tables"])
    plot_confusion_matrices(model_names, y_test, out["probas"],
                            out["thresholds"])
    export_summary(out["results"])
    conf = pd.DataFrame([confusion_rows(y_test, out["probas"][name],
                                        out["thresholds"][name], name)
                         for name in model_names])
    conf.to_csv(MODEL_EVAL_DIR / "confusion.csv", index=False)
    LOGGER.info("\nConfusion:\n%s", conf.to_string(index=False))