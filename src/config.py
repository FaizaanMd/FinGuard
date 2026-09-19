"""Central configuration for the FinGuard pipeline.

Paths are derived from this file's location, so scripts can run from any
working directory. Database credentials are read from a git-ignored .env file.

Modules import shared values from here instead of hard-coding paths.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
SRC_DIR = PROJECT_ROOT / "src"
SQL_DIR = PROJECT_ROOT / "sql"
MODELS_DIR = PROJECT_ROOT / "models"
TESTS_DIR = PROJECT_ROOT / "tests"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
REPORTS_DIR = PROJECT_ROOT / "reports"
EDA_REPORTS_DIR = REPORTS_DIR / "eda"

RAW_CREDITCARD_PATH = RAW_DATA_DIR / "creditcard.csv"
CLEANED_TRANSACTIONS_PATH = PROCESSED_DATA_DIR / "transactions_cleaned.csv"
ENGINEERED_FEATURES_PATH = PROCESSED_DATA_DIR / "features_engineered.csv"

# Ensure core directories exist on import.
for _dir in (
    RAW_DATA_DIR,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    MODELS_DIR,
    DASHBOARD_DIR,
    REPORTS_DIR,
    EDA_REPORTS_DIR,
):
    _dir.mkdir(parents=True, exist_ok=True)

# Load .env (no-op if absent; database-dependent features raise clear errors).
load_dotenv(PROJECT_ROOT / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "finguard"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

# Column names used by the benchmark credit-card dataset.
CREDITCARD_FEATURE_COLUMNS = [f"V{i}" for i in range(1, 29)]
CREDITCARD_TIME_COLUMN = "Time"
CREDITCARD_AMOUNT_COLUMN = "Amount"
CREDITCARD_AMOUNT_LOG_COLUMN = "amount_log"
CREDITCARD_TARGET_COLUMN = "Class"

RANDOM_STATE = 42
TEST_SIZE = 0.2

# Cleaning behaviour: dropping full-row duplicates protects random train/test
# splits from leakage. Set False to keep duplicates (then use a duplicate-aware
# split in the modeling phase instead).
DROP_DUPLICATES = True