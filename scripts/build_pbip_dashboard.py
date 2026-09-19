import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "dashboard" / "FinGuard.Report" / "definition"
PAGES = REPORT / "pages"
MODEL = ROOT / "dashboard" / "FinGuard.SemanticModel" / "definition" / "tables"

VISUAL_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.12.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

MEASURES = {
    "vw_class_overview": [
        ("TxnsSum", "SUM(vw_class_overview[txns])", "#,0"),
        ("FraudTxns", "CALCULATE(SUM(vw_class_overview[txns]), vw_class_overview[class] = 1)", "#,0"),
        ("FraudRatePct", "DIVIDE([FraudTxns], [TxnsSum], 0) * 100", "0.00\"%\""),
    ],
    "vw_hourly_analysis": [
        ("HourlyTxnsSum", "SUM(vw_hourly_analysis[txns])", "#,0"),
        ("FraudRatePctAvg", "AVERAGE(vw_hourly_analysis[fraud_rate_pct])", "0.0000"),
    ],
    "vw_model_test_confusion": [
        ("PrecisionPctSum", "SUM(vw_model_test_confusion[precision_pct])", "0.00"),
        ("RecallPctSum", "SUM(vw_model_test_confusion[recall_pct])", "0.00"),
        ("F1PctSum", "SUM(vw_model_test_confusion[f1_pct])", "0.00"),
    ],
    "vw_alert_overview": [("AlertsOverviewSum", "SUM(vw_alert_overview[alerts])", "#,0")],
    "vw_alert_risk_buckets": [("AlertsBucketsSum", "SUM(vw_alert_risk_buckets[alerts])", "#,0")],
}


def nid(label: str) -> str:
    return hashlib.md5(label.encode()).hexdigest()[:20]


def col(entity: str, prop: str) -> dict:
    return {
        "field": {
            "Column": {
                "Expression": {"SourceRef": {"Entity": entity}},
                "Property": prop,
            }
        },
        "queryRef": f"{entity}.{prop}",
    }


def pair(entity: str, prop: str, native: str) -> dict:
    item = col(entity, prop)
    item["nativeQueryRef"] = native
    return item


def visual_json(name: str, vtype: str, roles: dict, pos, txt=None) -> dict:
    container = {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": pos,
        "visual": {"visualType": vtype, "drillFilterOtherVisuals": True},
    }
    if vtype == "textbox":
        container["visual"]["objects"] = {
            "textbox": [{"properties": {"text": {"expr": {"Literal": {"Value": txt}}}}}]
        }
        return container
    query = {}
    filters = []
    seen = set()
    for role, projections in roles.items():
        query[role] = {"projections": projections}
        for proj in projections:
            field = proj["field"]
            key = json.dumps(field, sort_keys=True)
            if key not in seen:
                seen.add(key)
                filters.append(
                    {
                        "name": nid(proj["queryRef"] + "f"),
                        "field": field,
                        "type": "Advanced",
                    }
                )
    container["visual"]["query"] = {"queryState": query}
    container["filterConfig"] = {"filters": filters}
    return container


def write_visual(page: str, label: str, vtype: str, roles: dict, pos, txt=None):
    name = nid(label)
    folder = PAGES / page / "visuals" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "visual.json").write_text(
        json.dumps(visual_json(name, vtype, roles, pos, txt), indent=2), encoding="utf-8"
    )
    return name


def write_page(page_id: str, display_name: str):
    folder = PAGES / page_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "page.json").write_text(
        json.dumps(
            {
                "$schema": PAGE_SCHEMA,
                "name": page_id,
                "displayName": display_name,
                "displayOption": "FitToPage",
                "height": 1080,
                "width": 1920,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def patch_measures():
    for table, measures in MEASURES.items():
        path = MODEL / f"{table}.tmdl"
        text = path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"\n\tmeasure .*?(?=\n\t(?:column|partition)\s|\Z)", "\n", text, flags=re.S)
        blocks = []
        for mname, expr, fmt in measures:
            blocks.append(
                f"\n\tmeasure {mname} = {expr}\n"
                f"\t\tlineageTag: {nid(table + mname)}\n"
                f"\t\tformatString: {fmt}"
            )
        text = re.sub(r"\n(\s*partition )", "\n" + "".join(blocks) + "\n\\1", text, count=1)
        path.write_text(text, encoding="utf-8")


def build():
    patch_measures()

    p1 = "3151622f782a408e0a6a"
    write_page(p1, "Monitoring overview")

    write_visual(
        p1, "p1-total-card", "cardVisual", {"Rows": [col("vw_class_overview", "TxnsSum")]},
        {"x": 40, "y": 40, "z": 0, "height": 150, "width": 300, "tabOrder": 0},
    )
    write_visual(
        p1, "p1-fraud-card", "cardVisual", {"Rows": [col("vw_class_overview", "FraudTxns")]},
        {"x": 380, "y": 40, "z": 1, "height": 150, "width": 300, "tabOrder": 1},
    )
    write_visual(
        p1, "p1-rate-card", "cardVisual", {"Rows": [col("vw_class_overview", "FraudRatePct")]},
        {"x": 720, "y": 40, "z": 2, "height": 150, "width": 300, "tabOrder": 2},
    )
    write_visual(
        p1, "p1-donut",
        "donutChart",
        {
            "CategoryData": [pair("vw_class_overview", "class", "class")],
            "Rows": [col("vw_class_overview", "TxnsSum")],
        },
        {"x": 40, "y": 240, "z": 3, "height": 340, "width": 520, "tabOrder": 3},
    )
    write_visual(
        p1, "p1-line",
        "lineChart",
        {
            "Category": [pair("vw_hourly_analysis", "hour_bucket", "hour_bucket")],
            "Values": [col("vw_hourly_analysis", "HourlyTxnsSum"), col("vw_hourly_analysis", "FraudRatePctAvg")],
        },
        {"x": 600, "y": 240, "z": 4, "height": 340, "width": 1270, "tabOrder": 4},
    )
    write_visual(
        p1, "p1-note", "textbox", {},
        {"x": 40, "y": 620, "z": 5, "height": 120, "width": 1840, "tabOrder": 5},
        "'Hour axis is a derived 24-hour cycle, not a clock time. Fraud rate is highest in the early-morning derived buckets.'",
    )

    p2 = nid("page-detection")
    write_page(p2, "Detection performance")
    write_visual(
        p2, "p2-bar",
        "clusteredColumnChart",
        {
            "Category": [pair("vw_model_test_confusion", "model_name", "model_name")],
            "Values": [
                col("vw_model_test_confusion", "PrecisionPctSum"),
                col("vw_model_test_confusion", "RecallPctSum"),
                col("vw_model_test_confusion", "F1PctSum"),
            ],
        },
        {"x": 40, "y": 40, "z": 0, "height": 380, "width": 880, "tabOrder": 0},
    )
    write_visual(
        p2, "p2-table",
        "tableEx",
        {
            "Values": [
                pair("vw_model_test_confusion", "model_name", "model_name"),
                pair("vw_model_test_confusion", "test_rows", "test_rows"),
                pair("vw_model_test_confusion", "tp", "tp"),
                pair("vw_model_test_confusion", "fp", "fp"),
                pair("vw_model_test_confusion", "fn", "fn"),
                pair("vw_model_test_confusion", "tn", "tn"),
                pair("vw_model_test_confusion", "precision_pct", "precision_pct"),
                pair("vw_model_test_confusion", "recall_pct", "recall_pct"),
                pair("vw_model_test_confusion", "f1_pct", "f1_pct"),
            ]
        },
        {"x": 960, "y": 40, "z": 1, "height": 380, "width": 920, "tabOrder": 1},
    )
    write_visual(
        p2, "p2-note1", "textbox", {},
        {"x": 40, "y": 450, "z": 2, "height": 110, "width": 1840, "tabOrder": 2},
        "'Random Forest is the primary detector: 93.7% precision at 77.9% recall on the held-out test, with only 5 false positives (vs 20 for logistic regression).'",
    )
    write_visual(
        p2, "p2-note2", "textbox", {},
        {"x": 40, "y": 580, "z": 3, "height": 110, "width": 1840, "tabOrder": 3},
        "'Rule baseline (Phase 7): 0.28% precision / 15.65% recall across 26,632 alerts. Isolation Forest (Phase 9, label-free): PR-AUC 0.207, ROC-AUC 0.953 — flags 39 fraud cases the Random Forest misses.'",
    )

    p3 = nid("page-alerts")
    write_page(p3, "Alert workload")
    write_visual(
        p3, "p3-sources",
        "stackedBarChart",
        {
            "Category": [pair("vw_alert_overview", "alert_source", "alert_source")],
            "Series": [pair("vw_alert_overview", "alert_type", "alert_type")],
            "Values": [col("vw_alert_overview", "AlertsOverviewSum")],
        },
        {"x": 40, "y": 40, "z": 0, "height": 360, "width": 900, "tabOrder": 0},
    )
    write_visual(
        p3, "p3-buckets",
        "stackedBarChart",
        {
            "Category": [pair("vw_alert_risk_buckets", "alert_source", "alert_source")],
            "Series": [pair("vw_alert_risk_buckets", "risk_bucket", "risk_bucket")],
            "Values": [col("vw_alert_risk_buckets", "AlertsBucketsSum")],
        },
        {"x": 980, "y": 40, "z": 1, "height": 360, "width": 900, "tabOrder": 1},
    )
    write_visual(
        p3, "p3-table",
        "tableEx",
        {
            "Values": [
                pair("vw_transaction_monitoring", "transaction_id", "transaction_id"),
                pair("vw_transaction_monitoring", "amount", "amount"),
                pair("vw_transaction_monitoring", "class", "class"),
                pair("vw_transaction_monitoring", "alert_count", "alert_count"),
                pair("vw_transaction_monitoring", "max_risk_score", "max_risk_score"),
                pair("vw_transaction_monitoring", "alert_sources", "alert_sources"),
                pair("vw_transaction_monitoring", "rf_probability_test", "rf_probability_test"),
            ]
        },
        {"x": 40, "y": 440, "z": 2, "height": 420, "width": 1840, "tabOrder": 2},
    )
    write_visual(
        p3, "p3-note", "textbox", {},
        {"x": 40, "y": 900, "z": 3, "height": 100, "width": 1840, "tabOrder": 3},
        "'Alerts are triage signals, not fraud verdicts. max_risk_score combines rules + model signals (0-1).'",
    )

    page_order = [p1, p2, p3]
    (PAGES / "pages.json").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
                "pageOrder": page_order,
                "activePageName": p1,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"built report: pages={page_order}")


if __name__ == "__main__":
    build()