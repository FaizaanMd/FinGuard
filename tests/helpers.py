"""Shared synthetic-data helpers for FinGuard tests.

Everything is fabricated locally so no large dataset or database is required.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import CREDITCARD_FEATURE_COLUMNS


def make_synthetic_raw(n: int = 2000, seed: int = 0, dup_rows: int = 0,
                       fraud_rate: float = 0.02) -> pd.DataFrame:
    """Return a DataFrame shaped like the benchmark raw file.

    Features V1..V28 are standard normal; V14 and V4 carry a modest class
    signal so the modelling tests have something to learn.
    """
    rng = np.random.default_rng(seed)
    time = np.linspace(0.0, 2 * 86_400.0, n)
    amount = rng.lognormal(mean=3.0, sigma=1.2, size=n)
    cls = rng.binomial(1, fraud_rate, n).astype(int)
    raw = rng.normal(0.0, 1.0, size=(n, 28))
    raw[:, 13] += np.where(cls == 1, -2.5, 0.0)  # V14
    raw[:, 3] += np.where(cls == 1, 2.5, 0.0)    # V4

    frame = pd.DataFrame(raw, columns=CREDITCARD_FEATURE_COLUMNS)
    frame["Time"] = time
    frame["Amount"] = amount
    frame["Class"] = cls

    if dup_rows:
        dup = frame.iloc[[i % len(frame) for i in range(dup_rows)]]
        frame = pd.concat([frame, dup], ignore_index=True)
    return frame.sample(frac=1.0, random_state=seed).reset_index(drop=True)


def make_engineered_frame(n: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Raw-style frame cleaned, assigned ids, and engineered features added."""
    from src.data_cleaning import clean
    from src.feature_engineering import build_features

    cleaned, _ = clean(make_synthetic_raw(n=n, seed=seed))
    return build_features(cleaned)