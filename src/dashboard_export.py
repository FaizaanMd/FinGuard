"""Export dashboard-ready datasets for Power BI.

Applies sql/dashboard_views.sql (idempotent) and dumps each view to
data/dashboard_export/ as CSV so Power BI can either connect live to
PostgreSQL or import the files.

Run: python -m src.dashboard_export
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from src.config import DATABASE_URL, PROJECT_ROOT, SQL_DIR

LOGGER = logging.getLogger("finguard.dashboard")

DASHBOARD_EXPORT_DIR = PROJECT_ROOT / "data" / "dashboard_export"

VIEWS = [
    "vw_transaction_monitoring",
    "vw_alert_overview",
    "vw_class_overview",
    "vw_hourly_analysis",
    "vw_amount_buckets",
    "vw_model_test_confusion",
    "vw_alert_risk_buckets",
]


def apply_dashboard_views(engine) -> None:
    source = (SQL_DIR / "dashboard_views.sql").read_text(encoding="utf-8")
    commentless = "\n".join(
        line for line in source.splitlines()
        if not line.lstrip().startswith("--")
    )
    statements = [s.strip() for s in commentless.split(";") if s.strip()]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    LOGGER.info("Dashboard views applied from %s", SQL_DIR / "dashboard_views.sql")


def export_views(engine) -> list[tuple[str, int]]:
    DASHBOARD_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    made = []
    with engine.connect() as conn:
        for view in VIEWS:
            frame = pd.read_sql(text(f"SELECT * FROM {view}"), conn)
            path = DASHBOARD_EXPORT_DIR / f"{view}.csv"
            frame.to_csv(path, index=False)
            made.append((view, len(frame)))
            LOGGER.info("%-32s %8d rows -> %s", view, len(frame), path.name)
    return made


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    engine = create_engine(DATABASE_URL)
    apply_dashboard_views(engine)
    total = export_views(engine)
    LOGGER.info("Exported %d views to %s",
                len(total), DASHBOARD_EXPORT_DIR)