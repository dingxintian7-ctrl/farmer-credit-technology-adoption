import sys
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from generate_demo_data import make_synthetic_data
from analyze_demo import analyze, validate


def test_reproducible_generation():
    a = make_synthetic_data(n=50, seed=17)
    b = make_synthetic_data(n=50, seed=17)
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == 50


def test_duplicate_ids_rejected():
    df = make_synthetic_data(n=30)
    df.loc[1, "respondent_id"] = df.loc[0, "respondent_id"]
    with pytest.raises(ValueError, match="Respondent IDs"):
        validate(df)


def test_out_of_range_rejected():
    df = make_synthetic_data(n=30)
    df.loc[0, "age"] = 101
    with pytest.raises(ValueError, match="age"):
        validate(df)


def test_pipeline_creates_artifacts(tmp_path):
    df = make_synthetic_data(n=300)
    result = analyze(df, tmp_path)
    assert result["audit"]["n"] == 300
    for name in [
        "demo_quality_audit.json", "demo_missingness.csv",
        "demo_group_comparison.csv", "demo_model_coefficients.csv",
        "demo_adoption_by_credit.png", "demo_summary.md",
    ]:
        assert (tmp_path / name).is_file()
