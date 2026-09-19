"""Run FinGuard SQL analytics files against the database and print results.

Usage:
    python scripts/run_sql_analytics.py           # runs both analytics files
    python scripts/run_sql_analytics.py <file>... # specific files

Comment lines are stripped before splitting on ';', so queries can include
explanatory comments.
"""
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SQL_DIR  # noqa: E402

DEFAULT_FILES = [
    SQL_DIR / "exploratory_queries.sql",
    SQL_DIR / "business_queries.sql",
]


def run_sql_file(engine, sql_file: Path) -> None:
    raw = sql_file.read_text(encoding="utf-8-sig")
    commentless = "\n".join(
        line for line in raw.splitlines()
        if not line.lstrip().startswith("--")
    )
    statements = [s.strip() for s in commentless.split(";") if s.strip()]
    print(f"\n{'=' * 70}\nFILE: {sql_file.name} ({len(statements)} statements)\n{'=' * 70}")
    for i, stmt in enumerate(statements, start=1):
        print(f"\n--- Q{i}")
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(stmt), conn)
            with pd.option_context(
                "display.max_columns", 20,
                "display.width", 200,
                "display.max_rows", 30,
            ):
                print(df.to_string(index=False))
        except Exception as exc:
            print("ERROR:", exc)


if __name__ == "__main__":
    from src.config import DATABASE_URL

    engine = create_engine(DATABASE_URL)
    files = [Path(f) for f in sys.argv[1:]] if len(sys.argv) > 1 else DEFAULT_FILES
    for chosen in files:
        run_sql_file(engine, chosen)
    print("\nDone.")