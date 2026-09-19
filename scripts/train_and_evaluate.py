"""Pickled-model inference + full evaluation: reproduce every Phase 8 artefact.

Usage:
    python -m src.fraud_detection   # train & persist (see train_and_evaluate)
    python scripts/train_and_evaluate.py   # train + render evaluation
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import fraud_detection
from src import model_evaluation

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    LOGGER = logging.getLogger("finguard.pipeline")
    LOGGER.info("Training models...")
    out = fraud_detection.run()
    LOGGER.info("Rendering evaluation artefacts...")
    model_evaluation.run_report_all(out)
    LOGGER.info("Model-prediction records written to model_predictions.")


if __name__ == "__main__":
    main()