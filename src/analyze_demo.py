"""Survey data QA, descriptive analysis and illustrative logistic regression.

Only generated synthetic data is accepted as input; no causal conclusions.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic_farm_survey.csv"
OUT = ROOT / "outputs"
REQUIRED = [
    "respondent_id", "age", "education_years", "land_mu",
    "training_attended", "perceived_cost", "credit_access",
    "adoption", "region_group",
]
FEATURES = [
    "credit_access", "training_attended", "education_years",
    "land_mu", "perceived_cost", "age",
]


def validate(df: pd.DataFrame) -> dict:
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if df["respondent_id"].isna().any() or df["respondent_id"].duplicated().any():
        raise ValueError("Respondent IDs must be complete and unique")
    for field, lower, upper in [
        ("age", 18, 80), ("education_years", 0, 20),
        ("land_mu", 0.01, 1e5), ("perceived_cost", 1, 5),
    ]:
        values = pd.to_numeric(df[field], errors="coerce")
        if (values.isna() & df[field].notna()).any() or (
            ~values.dropna().between(lower, upper)
        ).any():
            raise ValueError(f"Invalid values: {field}")
    for field in ("training_attended", "credit_access", "adoption"):
        if df[field].isna().any() or not df[field].isin([0, 1]).all():
            raise ValueError(f"Invalid binary field: {field}")
    if df["region_group"].isna().any() or not df["region_group"].isin(["A", "B", "C"]).all():
        raise ValueError("Invalid region_group")
    return {
        "n": int(len(df)),
        "missing_cells": {field: int(df[field].isna().sum()) for field in REQUIRED},
        "duplicate_ids": int(df["respondent_id"].duplicated().sum()),
    }


def analyze(df: pd.DataFrame, out: Path = OUT) -> dict:
    audit = validate(df)
    out.mkdir(parents=True, exist_ok=True)
    (out / "demo_quality_audit.json").write_text(
        json.dumps(audit, indent=2), encoding="utf-8"
    )
    pd.DataFrame({
        "field": REQUIRED,
        "missing_n": [audit["missing_cells"][c] for c in REQUIRED],
        "missing_pct": [
            round(100 * audit["missing_cells"][c] / len(df), 2)
            for c in REQUIRED
        ],
    }).to_csv(out / "demo_missingness.csv", index=False)

    clean = df.copy()
    for field in ("education_years", "perceived_cost"):
        if clean[field].isna().all():
            raise ValueError(f"Entire column missing: {field}")
        clean[field] = clean[field].fillna(clean[field].median())

    groups = clean.groupby("credit_access")["adoption"].agg(["size", "mean"])
    groups.columns = ["n", "adoption_rate"]
    groups.to_csv(out / "demo_group_comparison.csv")

    X = sm.add_constant(clean[FEATURES], has_constant="add")
    model = sm.Logit(clean["adoption"], X).fit(disp=False)
    pd.DataFrame({
        "term": model.params.index,
        "log_odds_coefficient": model.params.values,
        "odds_ratio": np.exp(model.params.values),
        "p_value_demo_only": model.pvalues.values,
    }).to_csv(out / "demo_model_coefficients.csv", index=False)

    complete = df.dropna(subset=FEATURES + ["adoption"])
    X_complete = sm.add_constant(complete[FEATURES], has_constant="add")
    complete_case_model = sm.Logit(complete["adoption"], X_complete).fit(disp=False)

    fig, ax = plt.subplots(figsize=(7.8, 4.5))
    bars = ax.bar(["No credit access", "Credit access"], groups["adoption_rate"] * 100)
    for bar, rate in zip(bars, groups["adoption_rate"]):
        ax.annotate(
            f"{rate * 100:.1f}%",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            ha="center", va="bottom", xytext=(0, 4), textcoords="offset points",
        )
    ax.set_ylim(0, 100)
    ax.set_ylabel("Simulated adoption rate (%)")
    ax.set_title("SYNTHETIC DATA ONLY | Illustrative group comparison")
    fig.tight_layout()
    fig.savefig(out / "demo_adoption_by_credit.png", dpi=180)
    plt.close(fig)

    summary = (
        "# 模拟数据分析输出（不代表原项目研究结论）\n\n"
        "**SYNTHETIC DATA ONLY — original questionnaires not included.**\n\n"
        f"- 模拟样本量：{audit['n']}（非原项目 428 份有效问卷）\n"
        f"- 模拟信贷可得组采纳率：{groups.loc[1, 'adoption_rate'] * 100:.1f}%\n"
        f"- 模拟信贷不可得组采纳率：{groups.loc[0, 'adoption_rate'] * 100:.1f}%\n"
        f"- 完整样本演示：{len(complete)} 条\n"
        f"- 简化 Logit 的信贷变量系数：{model.params['credit_access']:.3f}\n"
        f"- 完整样本敏感性分析的对应系数：{complete_case_model.params['credit_access']:.3f}\n\n"
        "全部数值基于模拟数据，仅展示分析方法，不代表原研究结果。"
        "普通 Logit 不等同于原研究 ESP 模型，也不能识别因果影响。\n"
    )
    (out / "demo_summary.md").write_text(summary, encoding="utf-8")
    print(f"SYNTHETIC demo analyzed: {audit['n']} records")
    return {"audit": audit, "groups": groups, "model": model}


if __name__ == "__main__":
    if not DATA.exists():
        raise FileNotFoundError("Run python src/generate_demo_data.py first")
    analyze(pd.read_csv(DATA))
