"""Feature engineering for the benchmark transactions dataset.

Only features that are *defensible* for the anonymized ULB benchmark are
created. New fields are derived under the following explicit assumptions:

- `Time` is relative seconds from the first observed transaction and the
  observed span (~48 hours) is treated as a single two-day window. The
  `hour_of_day` feature therefore assumes a 24-hour daily cycle; because the
  starting instant is unknown, the phase of the cycle is an offset and the
  *shape* of the pattern is what we interpret, never an absolute clock time.
- `Amount` is right-skewed (a small fraction of very large values), so a
  log1p transformation is added for models that assume better-behaved feature
  distributions. The raw amount is retained.

Scaling of `Amount`/derived numeric features is deliberately *not* applied here
(still supports models needing it): scalers must be fit on the training split
inside the modeling pipeline to avoid leakage.

Run directly:
    python -m src.feature_engineering
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import (
    CLEANED_TRANSACTIONS_PATH,
    CREDITCARD_AMOUNT_COLUMN,
    CREDITCARD_TARGET_COLUMN,
    CREDITCARD_TIME_COLUMN,
    ENGINEERED_FEATURES_PATH,
)

LOGGER = logging.getLogger("finguard.features")

SECONDS_PER_DAY = 86_400

DERIVED_FEATURES = [
    "hour_of_day",
    "day_index",
    "amount_log",
]


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive hour-of-cycle and day-index features from relative Time seconds."""
    time = frame[CREDITCARD_TIME_COLUMN].to_numpy()
    frame["hour_of_day"] = (time % SECONDS_PER_DAY) / 3_600.0
    frame["day_index"] = np.floor(time / SECONDS_PER_DAY).astype(int)
    return frame


def add_amount_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Derive a log1p transformed amount."""
    frame["amount_log"] = np.log1p(frame[CREDITCARD_AMOUNT_COLUMN].to_numpy())
    return frame


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply all supported engineered features and return a new frame."""
    out = frame.copy()
    out = add_time_features(out)
    out = add_amount_features(out)
    return out


def save(frame: pd.DataFrame, path: Path = ENGINEERED_FEATURES_PATH) -> Path:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return Path(path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if not CLEANED_TRANSACTIONS_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found at {CLEANED_TRANSACTIONS_PATH}. "
            "Run 'python -m src.data_cleaning' first."
        )

    cleaned = pd.read_csv(CLEANED_TRANSACTIONS_PATH)
    LOGGER.info("Loaded cleaned dataset (%s rows)", len(cleaned))

    features = build_features(cleaned)
    LOGGER.info("Derived features added: %s", ", ".join(DERIVED_FEATURES))

    out = save(features)
    LOGGER.info("Saved engineered features (%s rows, %s columns) to %s",
                len(features), len(features.columns), out)

    fraud = features[CREDITCARD_TARGET_COLUMN] == 1
    preview = features.loc[fraud, DERIVED_FEATURES].describe().loc[
        ["mean", "std", "min", "max"]
    ]
    LOGGER.info("Derived-feature summary for fraud rows:\n%s", preview.to_string())
    LOGGER.info(
        "Day coverage: %s", sorted(features["day_index"].unique().tolist())
    )