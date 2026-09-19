"""Tests for src.config."""
from __future__ import annotations

from src.config import (
    ANOMALY_CONTAMINATION,
    CREDITCARD_FEATURE_COLUMNS,
    DATABASE_URL,
    MODEL_FEATURE_COLUMNS,
    PROJECT_ROOT,
)


def test_feature_vector_has_expected_shape():
    assert len(CREDITCARD_FEATURE_COLUMNS) == 28
    assert CREDITCARD_FEATURE_COLUMNS == [f"V{i}" for i in range(1, 29)]


def test_model_feature_columns_are_29_vplus_3():
    assert len(MODEL_FEATURE_COLUMNS) == 31
    assert MODEL_FEATURE_COLUMNS[:28] == CREDITCARD_FEATURE_COLUMNS
    assert MODEL_FEATURE_COLUMNS[28:] == ["amount_log", "hour_of_day", "day_index"]


def test_database_url_points_at_finguard_database():
    assert DATABASE_URL.startswith("postgresql+psycopg2://")


def test_anomaly_contamination_is_a_small_prior():
    assert 0.0 < ANOMALY_CONTAMINATION < 0.01


def test_core_directories_exist():
    from src.config import (
        DATA_DIR, MODELS_DIR, REPORTS_DIR, SQL_DIR, DASHBOARD_DIR,
    )
    for path in (DATA_DIR, MODELS_DIR, REPORTS_DIR, SQL_DIR, DASHBOARD_DIR):
        assert path.exists(), path


def test_project_root_is_a_directory():
    assert PROJECT_ROOT.is_dir()