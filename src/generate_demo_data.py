"""Generate fully synthetic farmer survey data for an analysis demo.

These are NOT the original project's 428 questionnaire responses.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "synthetic_farm_survey.csv"
SEED = 20260923
N = 320  # intentionally different from the 428 real valid questionnaires


def make_synthetic_data(n: int = N, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.integers(24, 71, size=n)
    education = rng.integers(3, 17, size=n).astype(float)
    land = np.round(rng.lognormal(mean=2.1, sigma=0.57, size=n), 2)
    training = rng.binomial(1, 0.42, size=n)
    cost = rng.integers(1, 6, size=n).astype(float)
    region = rng.choice(["A", "B", "C"], size=n, p=[0.35, 0.35, 0.30])

    # Arbitrary simulation parameters; these are not observed effects.
    p_credit = 1 / (1 + np.exp(-(-0.60 + 0.025 * (education - 9)
                                  + 0.40 * training + 0.02 * np.log1p(land))))
    credit = rng.binomial(1, p_credit, size=n)
    p_adopt = 1 / (1 + np.exp(-(-1.55 + 0.70 * credit + 0.65 * training
                                 + 0.08 * (education - 9) + 0.16 * np.log1p(land)
                                 - 0.18 * (cost - 3))))
    adoption = rng.binomial(1, p_adopt, size=n)

    df = pd.DataFrame({
        "respondent_id": np.arange(1, n + 1),
        "age": age,
        "education_years": education,
        "land_mu": land,
        "training_attended": training,
        "perceived_cost": cost,
        "credit_access": credit,
        "adoption": adoption,
        "region_group": region,
    })
    for col in ["education_years", "perceived_cost"]:
        idx = rng.choice(df.index, size=max(1, round(n * 0.025)), replace=False)
        df.loc[idx, col] = np.nan
    return df


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    make_synthetic_data().to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"SYNTHETIC demo only: {N} records written to {OUTPUT}")


if __name__ == "__main__":
    main()
