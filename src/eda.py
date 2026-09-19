"""Statistical analysis and exploratory data analysis (Track A benchmark).

Produces:
- a summary of class imbalance and amount/time behaviour by class
- a Cohen's-d ranking of the anonymized V-features
- statistical tests comparing the classes
- a set of saved standalone figures (PNG) under reports/eda/
- a machine-readable statistical summary (CSV)

Interpretation rules: features V1..V28 are anonymized PCA components — no
business meaning is invented for them. `hour_of_day` assumes a 24-hour cycle;
its phase is unknown, so only relative patterns are interpretable.

Run directly:
    python -m src.eda
"""
from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from scipy import stats  # noqa: E402

from src.config import (  # noqa: E402
    CREDITCARD_AMOUNT_COLUMN,
    CREDITCARD_AMOUNT_LOG_COLUMN,
    CREDITCARD_TARGET_COLUMN,
    CREDITCARD_TIME_COLUMN,
    ENGINEERED_FEATURES_PATH,
    EDA_REPORTS_DIR,
)

LOGGER = logging.getLogger("finguard.eda")

sns.set_theme(style="whitegrid", palette="colorblind")
plt.rcParams["figure.dpi"] = 110

FRAUD_LABEL, LEGIT_LABEL = "Fraud (1)", "Legitimate (0)"


def load(frame_path: Path = ENGINEERED_FEATURES_PATH) -> pd.DataFrame:
    if not Path(frame_path).exists():
        raise FileNotFoundError(
            f"Engineered features not found at {frame_path}. "
            "Run feature engineering first."
        )
    return pd.read_csv(frame_path)


def cohens_d_ranking(df: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """Rank V-features by standardized mean difference between classes."""
    rows = []
    for col in [f"V{i}" for i in range(1, 29)]:
        fraud = df.loc[df[CREDITCARD_TARGET_COLUMN] == 1, col]
        legit = df.loc[df[CREDITCARD_TARGET_COLUMN] == 0, col]
        diff = fraud.mean() - legit.mean()
        pooled = np.sqrt((fraud.var() + legit.var()) / 2.0)
        rows.append({
            "feature": col,
            "fraud_mean": fraud.mean(),
            "legit_mean": legit.mean(),
            "cohens_d": float(diff / pooled) if pooled > 0 else np.nan,
        })
    ranking = pd.DataFrame(rows).sort_values(
        "cohens_d", key=lambda s: s.abs(), ascending=False
    )
    return ranking.head(top_n).reset_index(drop=True)


def imbalance_summary(df: pd.DataFrame) -> pd.DataFrame:
    counts = df[CREDITCARD_TARGET_COLUMN].value_counts().sort_index()
    summary = pd.DataFrame({
        "label": ["legitimate", "fraud"],
        "count": [counts.get(0, 0), counts.get(1, 0)],
    })
    summary["share_pct"] = 100.0 * summary["count"] / summary["count"].sum()
    return summary


def amount_stats(df: pd.DataFrame) -> pd.DataFrame:
    stats_list = []
    for label in (0, 1):
        values = df.loc[df[CREDITCARD_TARGET_COLUMN] == label,
                        CREDITCARD_AMOUNT_COLUMN]
        stats_list.append({
            "label": LEGIT_LABEL if label == 0 else FRAUD_LABEL,
            "n": len(values),
            "mean": values.mean(),
            "std": values.std(),
            "min": values.min(),
            "p25": values.quantile(0.25),
            "median": values.median(),
            "p75": values.quantile(0.75),
            "p95": values.quantile(0.95),
            "p99": values.quantile(0.99),
            "max": values.max(),
        })
    return pd.DataFrame(stats_list)


def time_patterns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["hour_band"] = np.floor(df["hour_of_day"] / 3) * 3
    grouped = (
        df.groupby("hour_band")[CREDITCARD_TARGET_COLUMN]
        .agg(txns="count", fraud="sum")
        .reset_index()
    )
    global_rate = df[CREDITCARD_TARGET_COLUMN].mean()
    grouped["fraud_rate_pct"] = 100.0 * grouped["fraud"] / grouped["txns"]
    grouped["lift"] = grouped["fraud_rate_pct"] / (100.0 * global_rate)
    return grouped


def statistical_tests(df: pd.DataFrame) -> list[dict]:
    results = []
    for col, disp in ((CREDITCARD_AMOUNT_COLUMN, "amount"),
                      (CREDITCARD_AMOUNT_LOG_COLUMN, "amount_log")):
        fraud = df.loc[df[CREDITCARD_TARGET_COLUMN] == 1, col]
        legit = df.loc[df[CREDITCARD_TARGET_COLUMN] == 0, col]
        u, p = stats.mannwhitneyu(fraud, legit, alternative="two-sided")
        results.append({
            "variable": disp,
            "test": "Mann-Whitney U",
            "u_statistic": float(u),
            "p_value": float(p),
            "fraud_median": float(fraud.median()),
            "legit_median": float(legit.median()),
        })
    return results


def _save(fig, outdir: Path, name: str) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / name
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_class_balance(df: pd.DataFrame, outdir: Path) -> Path:
    summary = imbalance_summary(df)
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(summary["label"], summary["count"], color=["#3c8dbc", "#dd4b39"])
    ax.set_yscale("log")
    ax.set_ylabel("Transactions (log scale)")
    ax.set_title("Class imbalance — fraud vs legitimate")
    for bar, count in zip(bars, summary["count"]):
        ax.text(bar.get_x() + bar.get_width() / 2, count, f"{count:,}",
                ha="center", va="bottom", fontsize=9)
    return _save(fig, outdir, "01_class_balance.png")


def plot_amount_distribution(df: pd.DataFrame, outdir: Path) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for label, color in ((0, "#3c8dbc"), (1, "#dd4b39")):
        subset = df[df[CREDITCARD_TARGET_COLUMN] == label][CREDITCARD_AMOUNT_LOG_COLUMN]
        axes[0].hist(subset, bins=80, alpha=0.55, density=True,
                     label=LEGIT_LABEL if label == 0 else FRAUD_LABEL,
                     color=color)
    axes[0].set_xlabel("log1p(Amount)")
    axes[0].set_ylabel("Density")
    axes[0].set_title("Amount distribution (log scale)")
    axes[0].legend()

    df.boxplot(column=CREDITCARD_AMOUNT_LOG_COLUMN, by=CREDITCARD_TARGET_COLUMN,
               ax=axes[1], patch_artist=True, widths=0.4)
    axes[1].set_xlabel("Class")
    axes[1].set_ylabel("log1p(Amount)")
    axes[1].set_title("Amount by class (box, log scale)")
    fig.suptitle("")
    return _save(fig, outdir, "02_amount_distribution.png")


def plot_amount_deciles(df: pd.DataFrame, outdir: Path) -> Path:
    tmp = df.copy()
    tmp["decile"] = pd.qcut(tmp[CREDITCARD_AMOUNT_COLUMN], 10,
                            labels=False, duplicates="drop") + 1
    rates = (
        tmp.groupby("decile")[CREDITCARD_TARGET_COLUMN]
        .agg(txns="count", fraud="sum")
        .reset_index()
    )
    rates["fraud_rate_pct"] = 100.0 * rates["fraud"] / rates["txns"]
    fig, ax1 = plt.subplots(figsize=(9, 4))
    ax1.bar(rates["decile"], rates["fraud_rate_pct"], color="#dd4b39",
            alpha=0.8, label="Fraud rate %")
    ax1.set_xlabel("Amount decile (1 = smallest)")
    ax1.set_ylabel("Fraud rate (%)")
    ax1.set_title("Fraud rate by amount decile")
    ax2 = ax1.twinx()
    ax2.plot(rates["decile"], rates["txns"], color="#3c8dbc", marker="o",
             label="Transactions")
    ax2.set_ylabel("Transactions")
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")
    return _save(fig, outdir, "03_amount_decile_fraud_rate.png")


def plot_time_patterns(df: pd.DataFrame, outdir: Path) -> Path:
    patterns = time_patterns(df)
    fig, ax1 = plt.subplots(figsize=(9, 4))
    ax1.plot(patterns["hour_band"] + 1.5, patterns["txns"],
             color="#3c8dbc", marker="o", label="Transactions")
    ax1.set_xlabel("3-hour band of derived daily cycle")
    ax1.set_ylabel("Transactions")
    ax2 = ax1.twinx()
    ax2.plot(patterns["hour_band"] + 1.5, patterns["fraud_rate_pct"],
             color="#dd4b39", marker="s", label="Fraud rate %")
    ax2.set_ylabel("Fraud rate (%)")
    ax2.axhline(100.0 * df[CREDITCARD_TARGET_COLUMN].mean(), color="grey",
                linestyle="--", linewidth=1, label="Global fraud rate")
    ax1.set_title("Transaction volume and fraud rate through the derived cycle")
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")
    return _save(fig, outdir, "04_time_patterns.png")


def plot_feature_heatmap(df: pd.DataFrame, outdir: Path, top_n: int = 8) -> Path:
    ranking = cohens_d_ranking(df, top_n=top_n)
    features = ranking["feature"].tolist() + [CREDITCARD_AMOUNT_LOG_COLUMN]
    corr = df[features].corr()
    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                vmin=-1, vmax=1, ax=ax, linewidths=0.5)
    ax.set_title(f"Correlation — top {top_n} V-features (|Cohen's d|) + amount_log")
    return _save(fig, outdir, "05_feature_heatmap.png")


def plot_top_features_by_class(df: pd.DataFrame, outdir: Path) -> Path:
    ranking = cohens_d_ranking(df, top_n=4)
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    for ax, feature in zip(axes, ranking["feature"]):
        data = df[df[CREDITCARD_TARGET_COLUMN] == 1][feature]
        legit = df[df[CREDITCARD_TARGET_COLUMN] == 0][feature]
        ax.hist(legit, bins=60, alpha=0.5, density=True, color="#3c8dbc",
                label=LEGIT_LABEL)
        ax.hist(data, bins=60, alpha=0.5, density=True, color="#dd4b39",
                label=FRAUD_LABEL)
        ax.set_title(f"{feature}  (d={ranking.loc[ranking['feature'] == feature, 'cohens_d'].iloc[0]:.2f})")
        ax.set_xlabel("Value")
    axes[0].legend()
    fig.suptitle("Distribution of the most class-separating V-features", y=1.02)
    return _save(fig, outdir, "06_top_features_by_class.png")


def make_all_plots(df: pd.DataFrame, outdir: Path) -> list[Path]:
    return [
        plot_class_balance(df, outdir),
        plot_amount_distribution(df, outdir),
        plot_amount_deciles(df, outdir),
        plot_time_patterns(df, outdir),
        plot_feature_heatmap(df, outdir),
        plot_top_features_by_class(df, outdir),
    ]


def save_summary_csv(df: pd.DataFrame, outdir: Path) -> Path:
    rankings = cohens_d_ranking(df, top_n=28)
    rankings.to_csv(outdir / "feature_ranking.csv", index=False)
    return outdir / "feature_ranking.csv"


def run(df: pd.DataFrame | None = None,
        outdir: Path = EDA_REPORTS_DIR) -> dict:
    """Execute the full EDA and return the key computed summary objects."""
    df = df if df is not None else load()

    imbalance = imbalance_summary(df)
    amt = amount_stats(df)
    ranking = cohens_d_ranking(df, top_n=8)
    tests = statistical_tests(df)

    figures = make_all_plots(df, outdir)
    ranking_csv = save_summary_csv(df, outdir)

    results = {
        "imbalance": imbalance,
        "amount_stats": amt,
        "feature_ranking": ranking,
        "statistical_tests": tests,
        "figures": figures,
        "ranking_csv": ranking_csv,
        "fraud_rate_pct": 100.0 * df[CREDITCARD_TARGET_COLUMN].mean(),
    }
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    out = run()
    LOGGER.info("Fraud rate: %.4f%%", out["fraud_rate_pct"])
    LOGGER.info("\nImbalance:\n%s", out["imbalance"].to_string(index=False))
    LOGGER.info("\nAmount stats by label:\n%s", out["amount_stats"].to_string(index=False))
    LOGGER.info("\nTop V-features by |Cohen's d|:\n%s", out["feature_ranking"].to_string(index=False))
    LOGGER.info("\nStatistical tests:\n%s",
                pd.DataFrame(out["statistical_tests"]).to_string(index=False))
    LOGGER.info("Saved figures:\n%s", "\n".join(str(f) for f in out["figures"]))