"""Supervised fraud-detection models (Track A benchmark).

Leakage-safe workflow:
    1. Stratified split into train / validation / test (60 / 20 / 20).
    2. All preprocessing (StandardScaler) is fit on the TRAIN split only,
       inside a Pipeline, so it is learned per-protocol.
    3. The decision threshold is tuned on the VALIDATION split only.
    4. Every reported metric comes from the held-out TEST split, using the
       validation-tuned threshold.

Run directly:
    python -m src.fraud_detection
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine, text

from src.config import (
    CREDITCARD_TARGET_COLUMN,
    DATABASE_URL,
    ENGINEERED_FEATURES_PATH,
    EXPERIMENTS_LOG,
    MODEL_FEATURE_COLUMNS,
    MODELS_DIR,
    RANDOM_STATE,
    TRAIN_FRACTION,
    VALIDATION_FRACTION,
)

LOGGER = logging.getLogger("finguard.models")

MODEL_NAMES = {
    "logistic_regression": LogisticRegression(
        class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE
    ),
    "random_forest": RandomForestClassifier(
        n_estimators=150,
        class_weight="balanced",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    ),
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    df = pd.read_csv(ENGINEERED_FEATURES_PATH)
    X = df[MODEL_FEATURE_COLUMNS]
    y = df[CREDITCARD_TARGET_COLUMN]
    return df, X, y


def split_data(
    X: pd.DataFrame, y: pd.Series
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame,
           pd.Series, pd.Series, pd.Series]:
    test_fraction = 1.0 - TRAIN_FRACTION - VALIDATION_FRACTION
    rest_fraction = VALIDATION_FRACTION + test_fraction
    X_tr, X_rest, y_tr, y_rest = train_test_split(
        X, y, test_size=rest_fraction,
        stratify=y, random_state=RANDOM_STATE)
    within_rest_test = test_fraction / rest_fraction
    X_val, X_te, y_val, y_te = train_test_split(
        X_rest, y_rest, test_size=within_rest_test,
        stratify=y_rest, random_state=RANDOM_STATE)
    return X_tr, X_val, X_te, y_tr, y_val, y_te


def make_pipeline(model) -> Pipeline:
    return Pipeline([("scaler", StandardScaler()), ("model", model)])


def train_models(
    X_train: pd.DataFrame, y_train: pd.Series
) -> dict[str, Pipeline]:
    pipelines = {}
    for name, estimator in MODEL_NAMES.items():
        LOGGER.info("Training %s", name)
        t0 = time.perf_counter()
        pipe = make_pipeline(estimator)
        pipe.fit(X_train, y_train)
        LOGGER.info("%s trained in %.1fs", name, time.perf_counter() - t0)
        pipelines[name] = pipe
    return pipelines


def tune_threshold(
    y_val: pd.Series, p_val: np.ndarray, objective: str = "f1"
) -> tuple[float, pd.DataFrame]:
    thresholds = np.linspace(0.001, 0.9999, 600)
    rows = []
    for thr in thresholds:
        pred = (p_val >= thr).astype(int)
        rows.append({
            "threshold": thr,
            "precision": precision_score(y_val, pred, zero_division=0),
            "recall": recall_score(y_val, pred, zero_division=0),
            "f1": f1_score(y_val, pred, zero_division=0),
        })
    df = pd.DataFrame(rows)
    best_idx = int(df[objective].idxmax())
    return float(df.loc[best_idx, "threshold"]), df


def evaluate(
    y_test: pd.Series, p_test: np.ndarray, threshold: float, model_name: str
) -> dict:
    pred = (p_test >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    return {
        "model": model_name,
        "threshold": float(threshold),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "f1": float(f1_score(y_test, pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y_test, p_test)),
        "roc_auc": float(roc_auc_score(y_test, p_test)),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "n_alerts": int(pred.sum()),
        "fraud_captured": int(tp),
        "fraud_missed": int(fn),
    }


def persist_models(pipelines: dict[str, Pipeline]) -> list[Path]:
    paths = []
    for name, pipe in pipelines.items():
        path = MODELS_DIR / f"{name}.joblib"
        joblib.dump(pipe, path)
        paths.append(path)
        LOGGER.info("Saved model %s -> %s", name, path)
    return paths


def persist_predictions(
    test_transaction_ids: np.ndarray,
    probas: dict[str, np.ndarray],
    thresholds: dict[str, float],
) -> None:
    frames = []
    for name, proba in probas.items():
        label = (proba >= thresholds[name]).astype(int)
        frames.append(pd.DataFrame({
            "transaction_id": np.asarray(test_transaction_ids),
            "model_name": name,
            "fraud_probability": np.round(proba, 8),
            "predicted_label": label,
            "split": "test",
        }))
    all_rows = pd.concat(frames, ignore_index=True)
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE TABLE model_predictions RESTART IDENTITY CASCADE"))
        all_rows.to_sql("model_predictions", conn, if_exists="append",
                        index=False, chunksize=10_000)
    LOGGER.info("Wrote %s model predictions (split=%s)",
                len(all_rows), "test")


def log_experiments(
    results: dict[str, dict], threshold_tables: dict[str, pd.DataFrame]
) -> None:
    rows = []
    for name, metrics in results.items():
        val_df = threshold_tables[name]
        best_idx = int(val_df["f1"].idxmax())
        rows.append({
            "experiment_at": pd.Timestamp.now(),
            "model": name,
            "best_val_threshold": metrics["threshold"],
            "val_pr_auc_max": float(val_df["precision"].max()),
            "val_recall_at_best_f1": float(
                val_df.loc[best_idx, "recall"]),
            "test_precision": metrics["precision"],
            "test_recall": metrics["recall"],
            "test_f1": metrics["f1"],
            "test_pr_auc": metrics["pr_auc"],
            "test_roc_auc": metrics["roc_auc"],
            "test_n_alerts": metrics["n_alerts"],
            "test_fraud_captured": metrics["fraud_captured"],
            "test_fraud_missed": metrics["fraud_missed"],
        })
    out = pd.DataFrame(rows)
    if EXPERIMENTS_LOG.exists():
        out.to_csv(EXPERIMENTS_LOG, mode="a", header=False, index=False)
    else:
        out.to_csv(EXPERIMENTS_LOG, index=False)
    LOGGER.info("Experiment log -> %s", EXPERIMENTS_LOG)


def run() -> dict:
    df, X, y = load_data()
    LOGGER.info("Dataset: %s rows, %s features, fraud rate %.4f%%",
                len(df), X.shape[1], 100.0 * y.mean())

    X_tr, X_val, X_te, y_tr, y_val, y_te = split_data(X, y)
    LOGGER.info("Splits: train=%d val=%d test=%d (fraud: %d/%d/%d)",
                len(X_tr), len(X_val), len(X_te),
                int(y_tr.sum()), int(y_val.sum()), int(y_te.sum()))

    pipelines = train_models(X_tr, y_tr)
    persist_models(pipelines)

    probas = {name: pipe.predict_proba(X_te)[:, 1]
              for name, pipe in pipelines.items()}
    thresholds = {}
    threshold_tables = {}
    for name, p_val in pipelines.items():
        thr, table = tune_threshold(y_val, pipelines[name].predict_proba(X_val)[:, 1])
        thresholds[name] = thr
        threshold_tables[name] = table
        LOGGER.info("%s validation F1-optimal threshold: %.3f", name, thr)

    results = {name: evaluate(y_te, probas[name], thresholds[name], name)
               for name in pipelines}
    for name, m in results.items():
        LOGGER.info(
            "%s -> pr_auc=%.4f roc_auc=%.4f at thr=%.3f: "
            "prec=%.4f rec=%.4f f1=%.4f alerts=%d fraud_captured=%d",
            name, m["pr_auc"], m["roc_auc"], m["threshold"],
            m["precision"], m["recall"], m["f1"],
            m["n_alerts"], m["fraud_captured"])

    persist_predictions(df.loc[y_te.index, "transaction_id"].to_numpy(),
                        probas, thresholds)
    log_experiments(results, threshold_tables)

    return {
        "pipelines": pipelines,
        "probas": probas,
        "thresholds": thresholds,
        "threshold_tables": threshold_tables,
        "results": results,
        "splits": (X_tr, X_val, X_te, y_tr, y_val, y_te),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    run()