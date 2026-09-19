"""Generate the FinGuard notebooks from narrative + src helpers.

Run:
    python scripts/build_notebooks.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import nbformat  # noqa: E402

from src.config import NOTEBOOKS_DIR, EDA_REPORTS_DIR  # noqa: E402
from src.eda import make_all_plots, save_summary_csv  # noqa: E402
import src.eda  # noqa: E402


def cell(markdown: str | None = None, source: str | None = None) -> dict:
    if markdown is not None:
        return nbformat.v4.new_markdown_cell(markdown)
    return nbformat.v4.new_code_cell(source)


def build_eda_notebook() -> Path:
    nb = nbformat.v4.new_notebook()
    nb.metadata.kernelspec = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata.language_info = {
        "name": "python",
        "version": "3.12",
    }

    cells = [
        cell(markdown=(
            "# FinGuard — 01 Exploratory Data Analysis (Track A: benchmark)\n\n"
            "**Data:** Anonymized credit-card transactions from the ULB/Kaggle "
            "`creditcardfraud` benchmark (284,807 raw rows, `Time`, `V1..V28`, "
            "`Amount`, `Class`). After deduplication the working set has "
            "**283,726 rows** with 473 fraud rows.\n\n"
            "**Ground rules:** `V1..V28` are anonymous PCA components — no "
            "business meaning is invented for them. `hour_of_day` assumes a "
            "24-hour cycle whose **phase is unknown**, so only relative "
            "patterns are interpreted."
        )),
        cell(markdown="## 1. Setup and data loading"),
        cell(source=(
            "import sys\n"
            "from pathlib import Path\n"
            "PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()\n"
            "sys.path.insert(0, str(PROJECT_ROOT))\n"
            "\n"
            "%matplotlib inline\n"
            "import pandas as pd\n"
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n"
            "import seaborn as sns\n"
            "from IPython.display import Image as DispImage\n"
            "\n"
            "import src.eda as eda\n"
            "from src.config import (\n"
            "    ENGINEERED_FEATURES_PATH, EDA_REPORTS_DIR, CREDITCARD_TARGET_COLUMN,\n"
            "    CREDITCARD_AMOUNT_COLUMN, CREDITCARD_AMOUNT_LOG_COLUMN,\n"
            ")\n"
            "\n"
            "df = eda.load()\n"
            "print('shape:', df.shape)"
        )),
        cell(markdown=(
            "## 2. Class imbalance\n\n"
            "The dataset is highly imbalanced. Accuracy alone is meaningless "
            "here; later modeling phases use precision, recall, PR-AUC and "
            "alert-workload metrics."
        )),
        cell(source=(
            "imbalance = eda.imbalance_summary(df)\n"
            "display(imbalance)\n"
            "eda.plot_class_balance(df, EDA_REPORTS_DIR)\n"
            "display(DispImage((EDA_REPORTS_DIR / '01_class_balance.png').as_posix()))\n"
            "print('Fraud rate: %.4f%%' % (100.0 * df[CREDITCARD_TARGET_COLUMN].mean()))"
        )),
        cell(markdown=(
            "## 3. Transaction amount\n\n"
            "Compare amount behaviour by label. Because amounts are "
            "right-skewed (max ~25.7k), log-transformed `amount_log` is "
            "plotted. Note the **mean vs median divergence**: fraud has a "
            "*higher* mean but a *lower* median than legitimate transactions."
        )),
        cell(source=(
            "amt = eda.amount_stats(df)\n"
            "display(amt)\n"
            "eda.plot_amount_distribution(df, EDA_REPORTS_DIR)\n"
            "display(DispImage((EDA_REPORTS_DIR / '02_amount_distribution.png').as_posix()))"
        )),
        cell(markdown=(
            "## 4. Amount deciles\n\n"
            "Fraud is not a 'big-amount' problem in this dataset. The smallest-"
            "amount decile has the **highest fraud rate**, and the largest "
            "decile is only mildly elevated (a mild U-shape)."
        )),
        cell(source=(
            "eda.plot_amount_deciles(df, EDA_REPORTS_DIR)\n"
            "display(DispImage((EDA_REPORTS_DIR / '03_amount_decile_fraud_rate.png').as_posix()))"
        )),
        cell(markdown=(
            "## 5. Time cycle (derived, phase unknown)\n\n"
            "`hour_of_day = (Time % 86400) / 3600` assumes a 24h cycle over "
            "the observed ~48h window. Only the **shape** of the pattern is "
            "read: activity is lowest in the early hours of the cycle, where "
            "the fraud rate is highest relative to its own volume."
        )),
        cell(source=(
            "time_pat = eda.time_patterns(df)\n"
            "display(time_pat.round(3))\n"
            "eda.plot_time_patterns(df, EDA_REPORTS_DIR)\n"
            "display(DispImage((EDA_REPORTS_DIR / '04_time_patterns.png').as_posix()))"
        )),
        cell(markdown=(
            "## 6. Anonymous V-features\n\n"
            "Rank the PCA components by standardized mean difference "
            "(Cohen's d) between classes, inspect the top separators, and "
            "check correlations. Results show several components are strong "
            "separators, which motivates the supervised models in later phases."
        )),
        cell(source=(
            "ranking = eda.cohens_d_ranking(df, top_n=8)\n"
            "display(ranking.round(4))\n"
            "eda.plot_top_features_by_class(df, EDA_REPORTS_DIR)\n"
            "display(DispImage((EDA_REPORTS_DIR / '06_top_features_by_class.png').as_posix()))\n"
            "eda.plot_feature_heatmap(df, EDA_REPORTS_DIR)\n"
            "display(DispImage((EDA_REPORTS_DIR / '05_feature_heatmap.png').as_posix()))"
        )),
        cell(markdown=(
            "## 7. Statistical comparison\n\n"
            "Mann-Whitney U compares the class distributions without assuming "
            "normality. The difference in `amount` distributions is "
            "statistically significant, but the effect is small in practical "
            "terms — and it does **not** mean 'fraud = large amounts'."
        )),
        cell(source=(
            "tests = pd.DataFrame(eda.statistical_tests(df))\n"
            "display(tests)\n"
            "eda.save_summary_csv(df, EDA_REPORTS_DIR)"
        )),
        cell(markdown=(
            "## 8. Summary of findings\n\n"
            "1. Imbalance: 0.167% fraud — evaluation must use PR-based metrics.\n"
            "2. Amount: fraud median 9.82 vs legit 22.00; fraud mean 123.87 vs "
            "88.41. Mean/median divergence → report several statistics.\n"
            "3. Deciles: smallest-amount decile carries the top fraud rate.\n"
            "4. Cycle: early-cycle-hours show elevated relative fraud rate.\n"
            "5. Features: V14, V4, V12, V11, V10 rank highest by |Cohen's d|.\n\n"
            "### Limitations\n"
            "- Anonymized PCs: patterns cannot be mapped to real-world causes.\n"
            "- `hour_of_day` phase is unknown; absolute clock meanings are not "
            "claimed.\n"
            "- Correlations ≠ causation; findings are dataset observations.\n"
            "- Future-information hazards are avoided by fitting any scaler "
            "only on training data (modelling phase)."
        )),
    ]
    nb.cells = cells
    path = NOTEBOOKS_DIR / "01_eda.ipynb"
    nbformat.write(nb, path)
    return path


if __name__ == "__main__":
    path = build_eda_notebook()
    print(f"Wrote {path}")