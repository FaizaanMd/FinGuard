"""Unsupervised anomaly detection with Isolation Forest (Track A).

Design choices:
- The anomaly scorer is fit on the TRAIN split only, so the metric geography
  matches Phase 8 exactly (same held-out test partition).
- `contamination` is an explicit prior (0.2%) — using the true label rate to
  set it would leak labels into an unsupervised method, so it is never tuned
  against `Class`.
- Anomaly scores are computed for every transaction (deployment simulation:
  scoring is stateless per row), but every headline metric is measured on the
  held-out TEST split only.

Run directly:
    python -m src.anomaly_detection
"""
from __future__ import annotations

import logging

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score
from sqlalchemy import create_engine, text

from src.config import (
    ANOMALY_CONTAMINATION,
    ANOMALY_N_ESTIMATORS,
    ANOMALY_REPORTS_DIR,
    CREDITCARD_TARGET_COLUMN,
    DATABASE_URL,
    ENGINEERED_FEATURES_PATH,
    MODEL_FEATURE_COLUMNS,
    MODELS_DIR,
    PROCESSED_DATA_DIR,
    RANDOM_STATE,
)
from src.fraud_detection import split_data

LOGGER = logging.getLogger("finguard.anomaly")

SCORES_CSV_PATH = PROCESSED_DATA_DIR / "anomaly_scores.csv"
ALERTS_CSV_PATH = PROCESSED_DATA_DIR / "alerts_anomaly.csv"
EVAL_RUN_LOG = MODELS_DIR / "experiments_anomaly.csv"


def fit_anomaly_model(X_train: pd.DataFrame) -> IsolationForest:
    model = IsolationForest(
        n_estimators=ANOMALY_N_ESTIMATORS,
        contamination=ANOMALY_CONTAMINATION,
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    model.fit(X_train)
    LOGGER.info("IsolationForest fit on %s rows (preprocessing-free)",
                len(X_train))
    return model


def score_all(df: pd.DataFrame, model: IsolationForest) -> pd.DataFrame:
    X = df[MODEL_FEATURE_COLUMNS]
    scores = model.score_samples(X)
    # score_samples: higher = more normal, lower = more anomalous.
    risk = (scores.max() - scores) / (scores.max() - scores.min())
    out = pd.DataFrame({
        "transaction_id": df["transaction_id"],
        "anomaly_score": np.round(scores, 6),
        "risk_score": np.round(risk, 4),
    })
    out[CREDITCARD_TARGET_COLUMN] = df[CREDITCARD_TARGET_COLUMN].values
    return out


def flag_top_k(scored: pd.DataFrame, fraction: float) -> pd.DataFrame:
    n = int(np.ceil(fraction * len(scored)))
    return scored.nlargest(n, "risk_score").copy()


def test_metrics(scored_test: pd.DataFrame) -> dict:
    y = scored_test[CREDITCARD_TARGET_COLUMN]
    return {
        "pr_auc": float(average_precision_score(y, scored_test["risk_score"])),
        "roc_auc": float(roc_auc_score(y, scored_test["risk_score"])),
    }


def threshold_sweep(scored_test: pd.DataFrame,
                    flags: tuple[int, ...] = None) -> pd.DataFrame:
    if flags is None:
        flags = (1, 2, 5, 10, 20, 50, 100, 200)
    y = scored_test[CREDITCARD_TARGET_COLUMN].to_numpy()
    risk = scored_test["risk_score"].to_numpy()
    n = len(scored_test)
    rows = []
    for top_k in flags:
        cutoff = np.partition(risk, n - top_k)[n - top_k] if top_k < n else 0.0
        hit = risk >= cutoff
        rows.append({
            "n_flagged": int(hit.sum()),
            "fraud_captured": int((hit & (y == 1)).sum()),
            "precision_pct": round(100.0 * (hit & (y == 1)).sum() /
                                   max(hit.sum(), 1), 3),
            "recall_pct": round(100.0 * (hit & (y == 1)).sum() /
                                max(int((y == 1).sum()), 1), 3),
        })
    return pd.DataFrame(rows, index=pd.Index([f"top_{k}" for k in flags],
                                             name="operating_point"))


def persist_scored(scored: pd.DataFrame, alerts: pd.DataFrame) -> None:
    scored.to_csv(SCORES_CSV_PATH, index=False)
    alerts.to_csv(ALERTS_CSV_PATH, index=False)
    LOGGER.info("Scores -> %s | alerts -> %s", SCORES_CSV_PATH, ALERTS_CSV_PATH)


def write_alert_rows(alerts: pd.DataFrame, risk_column: str = "risk_score",
                     source: str = "isolation_forest",
                     alert_type: str = "ANOMALY") -> None:
    """Replace previous isolation-forest alerts (idempotent) and insert."""
    rows = pd.DataFrame({
        "transaction_id": alerts["transaction_id"],
        "alert_source": source,
        "alert_type": alert_type,
        "risk_score": np.round(alerts[risk_column], 4),
        "alert_status": "New",
    })
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text(
            "DELETE FROM fraud_alerts WHERE alert_source = :source"),
            {"source": source})
        rows.to_sql("fraud_alerts", conn, if_exists="append", index=False,
                    chunksize=10_000)
    LOGGER.info("Wrote %s isolation-forest alerts", len(rows))


def persist_model(model: IsolationForest) -> None:
    path = MODELS_DIR / "isolation_forest.joblib"
    joblib.dump(model, path)
    LOGGER.info("Model -> %s", path)


def log_experiment(metrics: dict, alerts: pd.DataFrame, fit_rows: int) -> None:
    row = pd.DataFrame([{
        "run_at": pd.Timestamp.now(),
        "contamination": ANOMALY_CONTAMINATION,
        "fit_rows": fit_rows,
        "test_pr_auc": metrics["pr_auc"],
        "test_roc_auc": metrics["roc_auc"],
        "test_fraud": metrics.pop("n_test_fraud"),
        **{f"recall_{k}": v for k, v in alerts["recall_pct"].items()},
    }])
    if EVAL_RUN_LOG.exists():
        row.to_csv(EVAL_RUN_LOG, mode="a", header=False, index=False)
    else:
        row.to_csv(EVAL_RUN_LOG, index=False)
    LOGGER.info("Experiment log -> %s", EVAL_RUN_LOG)


def run() -> dict:
    df = pd.read_csv(ENGINEERED_FEATURES_PATH)
    _, _, X_test, _, _, y_test = split_data(
        df[MODEL_FEATURE_COLUMNS], df[CREDITCARD_TARGET_COLUMN])

    # Fit on everything EXCLUDING the test split (same geography as Phase 8).
    train_mask = ~df.index.isin(X_test.index)
    model = fit_anomaly_model(df.loc[train_mask, MODEL_FEATURE_COLUMNS])

    train_count = int(train_mask.sum())
    scored_all = score_all(df, model)
    scored_test = scored_all[df.index.isin(X_test.index)].copy()

    metrics = test_metrics(scored_test)
    metrics["n_test_fraud"] = int(y_test.sum())
    sweep = threshold_sweep(scored_test)

    alerts = flag_top_k(scored_all, ANOMALY_CONTAMINATION)
    persist_scored(scored_all, alerts)
    persist_model(model)
    write_alert_rows(alerts)
    log_experiment(metrics, sweep, train_count)

    rows = {
        "model": model,
        "metrics": metrics,
        "sweep": sweep,
        "alerts": alerts,
        "scored": scored_all,
    }
    return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    out = run()
    LOGGER.info("Test metrics: %s",
                pd.DataFrame([out["metrics"]]).to_string(index=False))
    LOGGER.info("\nOperating points (test):\n%s",
                out["sweep"].to_string())