"""Rule-based detection engine (Track A benchmark).

Rules are deliberately restricted to what this dataset can support — there are
no customer, merchant, device, or location identifiers, so velocity/geography
rules cannot be meaningfully built here (Track B synthetic data covers those).

Rules rendered by the engine:

- `rule_high_value`: amount above the **data-derived** 99th percentile.
- `rule_high_value_rapid`: arrives within <= 1 second of the previous
  transaction AND is above the 90th percentile of amounts. The time-gap is an
  identity-free proxy for rapid activity — a bare gap rule fires on ~91% of
  this dense dataset, so it must be paired with amount, never used alone.
- `rule_night_high_value`: amount above the data-derived 95th percentile
  during the early hours of the derived daily cycle (calibrated from EDA,
  where relative fraud rate was highest).

A rule trigger is **a risk indicator, not a fraud verdict**. Combined risk per
transaction uses a probabilistic OR over triggered rule weights.

Run directly:
    python -m src.rule_engine
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from src.config import (
    CREDITCARD_AMOUNT_COLUMN,
    CREDITCARD_TARGET_COLUMN,
    CREDITCARD_TIME_COLUMN,
    DATABASE_URL,
    ENGINEERED_FEATURES_PATH,
    PROCESSED_DATA_DIR,
)

LOGGER = logging.getLogger("finguard.rules")

ALERTS_CSV_PATH = PROCESSED_DATA_DIR / "alerts_rules.csv"
RISK_CSV_PATH = PROCESSED_DATA_DIR / "transaction_risk.csv"

NIGHT_HOUR_LIMIT = 6.0
RAPID_GAP_SECONDS = 1.0
RAPID_GAP_MIN_AMOUNT_PCT = 0.90
HIGH_VALUE_PCT = 0.99
NIGHT_VALUE_PCT = 0.95


@dataclass
class Rule:
    name: str
    alert_type: str
    description: str
    risk_indicator: str
    weight: float
    mask: pd.Series


def build_rules(df: pd.DataFrame) -> list[Rule]:
    """Construct the configured rules with data-derived thresholds."""
    amount = df[CREDITCARD_AMOUNT_COLUMN]
    high_p99 = amount.quantile(HIGH_VALUE_PCT)
    night_p95 = amount.quantile(NIGHT_VALUE_PCT)

    time = df[CREDITCARD_TIME_COLUMN].to_numpy()
    gap_sec = pd.Series(np.full(len(df), np.nan), index=df.index)
    order = np.argsort(time, kind="stable")
    sorted_gap = np.diff(time[order])
    gap_sec.iloc[order[1:]] = sorted_gap

    rapid_p90 = amount.quantile(RAPID_GAP_MIN_AMOUNT_PCT)

    rules = [
        Rule(
            name="rule_high_value",
            alert_type="HIGH_VALUE",
            description=(
                f"Amount above the data-derived {int(HIGH_VALUE_PCT * 100)}th "
                f"percentile ({high_p99:,.2f})"
            ),
            risk_indicator="Medium",
            weight=0.70,
            mask=amount > high_p99,
        ),
        Rule(
            name="rule_high_value_rapid",
            alert_type="HIGH_VALUE_RAPID",
            description=(
                f"At most {RAPID_GAP_SECONDS:g} second since the previous "
                "transaction AND amount above the "
                f"{int(RAPID_GAP_MIN_AMOUNT_PCT * 100)}th percentile "
                f"({rapid_p90:,.2f}); a bare gap rule fires on ~91% of this "
                "dataset, so it is paired with amount"
            ),
            risk_indicator="High",
            weight=0.85,
            mask=(gap_sec <= RAPID_GAP_SECONDS) & (amount > rapid_p90),
        ),
        Rule(
            name="rule_night_high_value",
            alert_type="NIGHT_HIGH_VALUE",
            description=(
                f"Amount above the {int(NIGHT_VALUE_PCT * 100)}th percentile "
                f"({night_p95:,.2f}) during the first {NIGHT_HOUR_LIMIT:g} "
                "hours of the derived cycle"
            ),
            risk_indicator="Medium",
            weight=0.55,
            mask=(amount > night_p95) & (df["hour_of_day"] < NIGHT_HOUR_LIMIT),
        ),
    ]
    return rules


def score_transactions(df: pd.DataFrame, rules: list[Rule]) -> pd.DataFrame:
    """Combine triggered rules into per-transaction risk indicators."""
    out = df[["transaction_id"]].copy()
    out["rules_triggered"] = ""
    combined = np.zeros(len(df))
    for rule in rules:
        mask = rule.mask.to_numpy()
        out.loc[mask, "rules_triggered"] += rule.name + ";"
        weights = np.where(mask, rule.weight, 0.0)
        combined = 1.0 - (1.0 - combined) * (1.0 - weights)
    out["rules_triggered"] = out["rules_triggered"].str.rstrip(";")
    out["n_rules"] = out["rules_triggered"].str.split(";").str[0].ne("").astype(int)
    out["risk_score"] = combined.round(4)
    return out


def generate_alerts(df: pd.DataFrame, rules: list[Rule]) -> pd.DataFrame:
    """Long-format alert rows matching the fraud_alerts schema."""
    rows = []
    for rule in rules:
        flagged = df.loc[rule.mask]
        for _, txn in flagged.iterrows():
            rows.append({
                "transaction_id": int(txn["transaction_id"]),
                "alert_source": rule.name,
                "alert_type": rule.alert_type,
                "risk_score": rule.weight,
                "alert_status": "New",
            })
    return pd.DataFrame(rows)


def evaluate(df: pd.DataFrame, alerts: pd.DataFrame) -> pd.DataFrame:
    """Per-rule and combined-rule precision/recall vs the labelled classes."""
    total_fraud = int((df[CREDITCARD_TARGET_COLUMN] == 1).sum())
    rows = []

    for rule_name in alerts["alert_source"].sort_values().unique():
        flagged_ids = set(alerts.loc[alerts["alert_source"] == rule_name,
                                     "transaction_id"])
        flagged = df[df["transaction_id"].isin(flagged_ids)]
        alerts_n = len(flagged)
        fraud_n = int((flagged[CREDITCARD_TARGET_COLUMN] == 1).sum())
        rows.append({
            "rule": rule_name,
            "alerts": alerts_n,
            "fraud_alerts": fraud_n,
            "precision_pct": 100.0 * fraud_n / alerts_n if alerts_n else 0.0,
            "recall_pct": 100.0 * fraud_n / total_fraud if total_fraud else 0.0,
            "alert_rate_pct": 100.0 * alerts_n / len(df),
        })

    any_flagged_ids = set(alerts["transaction_id"])
    any_flagged = df[df["transaction_id"].isin(any_flagged_ids)]
    rows.append({
        "rule": "ANY_RULE",
        "alerts": len(any_flagged),
        "fraud_alerts": int((any_flagged[CREDITCARD_TARGET_COLUMN] == 1).sum()),
        "precision_pct": 100.0 * (any_flagged[CREDITCARD_TARGET_COLUMN] == 1).sum()
        / len(any_flagged) if len(any_flagged) else 0.0,
        "recall_pct": 100.0 * (any_flagged[CREDITCARD_TARGET_COLUMN] == 1).sum()
        / total_fraud if total_fraud else 0.0,
        "alert_rate_pct": 100.0 * len(any_flagged) / len(df),
    })
    return pd.DataFrame(rows).round(3)


def write_alerts_db(alerts: pd.DataFrame) -> None:
    """Insert alerts into fraud_alerts (idempotent: truncates first)."""
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fraud_alerts RESTART IDENTITY CASCADE"))
        alerts.to_sql("fraud_alerts", conn, if_exists="append", index=False,
                      method="multi", chunksize=50_000)
    LOGGER.info("Wrote %s alerts to fraud_alerts", len(alerts))


def run(frame: pd.DataFrame | None = None) -> dict:
    df = frame if frame is not None else pd.read_csv(ENGINEERED_FEATURES_PATH)
    df = df.copy()

    rules = build_rules(df)
    alerts = generate_alerts(df, rules)
    risk = score_transactions(df, rules)
    metrics = evaluate(df, alerts)

    RISK_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    alerts.to_csv(ALERTS_CSV_PATH, index=False)
    risk.to_csv(RISK_CSV_PATH, index=False)
    LOGGER.info("Alerts saved to %s", ALERTS_CSV_PATH)
    LOGGER.info("Transaction risk saved to %s", RISK_CSV_PATH)

    return {"rules": rules, "alerts": alerts, "risk": risk, "metrics": metrics}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    out = run()
    LOGGER.info("Rules:\n%s", pd.DataFrame([
        {"rule": r.name, "type": r.alert_type, "indicator": r.risk_indicator,
         "weight": r.weight} for r in out["rules"]
    ]).to_string(index=False))
    LOGGER.info("\nEvaluation:\n%s", out["metrics"].to_string(index=False))
    LOGGER.info("\nRisk-score distribution:\n%s", out["risk"]["risk_score"]
                .describe().round(4).to_string())
    write_alerts_db(out["alerts"])