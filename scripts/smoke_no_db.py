from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src import data_cleaning, data_validation, feature_engineering


def main() -> None:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(rng.normal(size=(200, 28)), columns=[f"V{i}" for i in range(1, 29)])
    frame["Time"] = np.linspace(0, 172800, 200)
    frame["Amount"] = rng.lognormal(3.0, 1.0, 200)
    frame["Class"] = rng.binomial(1, 0.05, 200)
    assert data_validation.build_report(frame)["status"] in ("PASS", "WARN")
    cleaned, _ = data_cleaning.clean(frame)
    feat = feature_engineering.build_features(cleaned)
    assert {"hour_of_day", "day_index", "amount_log"} <= set(feat.columns)
    print("runbook smoke OK")


if __name__ == "__main__":
    main()