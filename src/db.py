"""Load the processed benchmark dataset into PostgreSQL and verify.

Responsibilities:
- apply the schema in sql/schema.sql (idempotent)
- bulk-load the engineered transactions alongside optional predictions/alerts
- verify the loaded row counts against the source CSV

The loader TRUNCATEs the transactions table before loading so re-runs are
idempotent (it is a local, portfolio-scale tool, not a production sync).

Run directly:
    python -m src.db
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from src.config import (
    CLEANED_TRANSACTIONS_PATH,
    DATABASE_URL,
    ENGINEERED_FEATURES_PATH,
    SQL_DIR,
)

LOGGER = logging.getLogger("finguard.db")


def get_engine():
    return create_engine(DATABASE_URL)


def apply_schema(engine) -> None:
    """Execute every statement in sql/schema.sql against the database."""
    schema_file = Path(SQL_DIR) / "schema.sql"
    sql_text = schema_file.read_text(encoding="utf-8")
    commentless = "\n".join(
        line for line in sql_text.splitlines()
        if not line.lstrip().startswith("--")
    )
    statements = [
        s.strip() for s in commentless.split(";") if s.strip()
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    LOGGER.info("Schema applied from %s", schema_file)


def load_transactions(engine, source: Path = ENGINEERED_FEATURES_PATH) -> int:
    """Read the engineered features and bulk-load into transactions."""
    frame = pd.read_csv(source)

    column_map = {
        "Time": "transaction_time",
        "Amount": "amount",
        "Class": "class",
    }
    renamed = frame.rename(columns=column_map)
    renamed["transaction_id"] = renamed["transaction_id"].astype("int64")
    renamed.columns = [c.lower() for c in renamed.columns]

    rows = len(renamed)
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE transactions, model_predictions, fraud_alerts "
                "RESTART IDENTITY CASCADE"
            )
        )
        renamed.to_sql(
            "transactions",
            conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=50_000,
        )
    LOGGER.info("Loaded %s transaction rows", rows)
    return rows


def verify_load(engine, expected_rows: int) -> None:
    """Compare SQL counts with the expected count."""
    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM transactions")
        ).scalar_one()
        fraud = conn.execute(
            text("SELECT COUNT(*) FROM transactions WHERE class = 1")
        ).scalar_one()
        min_amount = conn.execute(
            text("SELECT MIN(amount) FROM transactions")
        ).scalar_one()
        max_amount = conn.execute(
            text("SELECT MAX(amount) FROM transactions")
        ).scalar_one()
    LOGGER.info(
        "VERIFY total=%s (expected %s) fraud=%s amount=[%s, %s]",
        total, expected_rows, fraud, min_amount, max_amount,
    )
    if total != expected_rows:
        raise SystemExit(
            f"Row-count mismatch: DB has {total}, expected {expected_rows}"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if not ENGINEERED_FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Engineered features not found at {ENGINEERED_FEATURES_PATH}. "
            "Run data cleaning + feature engineering first."
        )

    engine = get_engine()
    apply_schema(engine)
    n = load_transactions(engine)
    verify_load(engine, n)
    LOGGER.info("Done.")