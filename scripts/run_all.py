"""Reproduce the entire FinGuard Track A pipeline in one command.

Stages run in dependency order; each reports PASS/FAIL with elapsed time so a
single invocation produces an auditable runbook. Database stages fail fast
with a clear message if PostgreSQL/.env is not configured.

Usage:
    python scripts/run_all.py
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from src.config import (  # noqa: E402
    CLEANED_TRANSACTIONS_PATH,
    DATABASE_URL,
    ENGINEERED_FEATURES_PATH,
    RAW_CREDITCARD_PATH,
)

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger("finguard.runbook")


def stage(name: str, fn, needs_db: bool, failures: list) -> None:
    if needs_db and not DATABASE_URL:
        print(f"  [SKIP] {name:<40} no DATABASE_URL configured")
        return
    t0 = time.perf_counter()
    try:
        fn()
        status = "PASS"
    except Exception as exc:  # noqa: BLE001 - report and continue
        status = f"FAIL:{type(exc).__name__}"
        failures.append(name)
        LOGGER.error("Stage '%s' failed", name, exc_info=exc)
    print(f"  [{status:>12}] {name:<40} {time.perf_counter() - t0:6.1f}s")


def run() -> int:
    from src import anomaly_detection, anomaly_eval_plots, data_cleaning
    from src import data_validation, dashboard_export, db
    from src import feature_engineering, fraud_detection
    from src import model_evaluation, rule_engine
    from sqlalchemy import create_engine

    def s_validation():
        if not RAW_CREDITCARD_PATH.exists():
            raise FileNotFoundError(
                f"Raw data not found at {RAW_CREDITCARD_PATH}. "
                "See data/README.md")
        data_validation.print_report(data_validation.build_report(
            pd.read_csv(RAW_CREDITCARD_PATH)))

    def s_cleaning():
        raw = pd.read_csv(RAW_CREDITCARD_PATH)
        cleaned, _ = data_cleaning.clean(raw)
        data_cleaning.save(cleaned)

    def s_features():
        cleaned = pd.read_csv(CLEANED_TRANSACTIONS_PATH)
        features = feature_engineering.build_features(cleaned)
        feature_engineering.save(features)

    def s_db():
        engine = db.get_engine()
        db.apply_schema(engine)
        expected = pd.read_csv(ENGINEERED_FEATURES_PATH).shape[0]
        db.load_transactions(engine)
        db.verify_load(engine, expected)

    def s_rules():
        out = rule_engine.run()
        rule_engine.write_alerts_db(out["alerts"])

    def s_models():
        out = fraud_detection.run()
        model_evaluation.run_report_all(out)

    def s_anomaly():
        anomaly_detection.run()
        anomaly_eval_plots.main()

    def s_dashboard():
        engine = create_engine(DATABASE_URL)
        dashboard_export.apply_dashboard_views(engine)
        dashboard_export.export_views(engine)

    failures: list[str] = []
    print("\n=== FinGuard Track A runbook ===\n")
    stage("1 validation", s_validation, False, failures)
    stage("2 cleaning", s_cleaning, False, failures)
    stage("3 feature engineering", s_features, False, failures)
    stage("4 postgres load & verify", s_db, True, failures)
    stage("5 rule engine + alerts", s_rules, True, failures)
    stage("6 supervised models", s_models, True, failures)
    stage("7 anomaly detection", s_anomaly, True, failures)
    stage("8 dashboard exports", s_dashboard, True, failures)

    print("\n=== Summary ===")
    print(f"  stages run: 8   failed: {len(failures)}")
    if failures:
        print(f"  failed stages: {', '.join(failures)}")
        return 1
    print("  Track A pipeline reproduced successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())