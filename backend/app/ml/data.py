"""Dataset utilities: schema, cleaning, feature engineering, synthetic generator, IBM download."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "Churn"
ID_COL = "customerID"
CATEGORICAL_RAW = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines", "InternetService",
    "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod",
]
NUMERIC_RAW = ["SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"]
FEATURE_COLUMNS = CATEGORICAL_RAW + NUMERIC_RAW
ADDONS = ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"]

# Engineered columns (created inside the sklearn pipeline, so training and serving share the code)
NUMERIC_MODEL = NUMERIC_RAW + ["avg_monthly_spend", "n_addons"]
CATEGORICAL_MODEL = CATEGORICAL_RAW + ["tenure_group"]

TELCO_URLS = [
    "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv",
]


def missing_columns(df: pd.DataFrame, require_target: bool = True) -> list[str]:
    needed = FEATURE_COLUMNS + ([TARGET] if require_target else [])
    return [c for c in needed if c not in df.columns]


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Row-level cleaning that uses no statistics from the data (so it cannot leak)."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype("string").str.strip().astype("object")
    if ID_COL in df.columns:
        df = df.drop_duplicates(subset=[ID_COL])
    if TARGET in df.columns:
        df[TARGET] = df[TARGET].map(
            lambda v: 1 if str(v).strip().lower() in {"yes", "1", "true"} else (0 if str(v).strip().lower() in {"no", "0", "false"} else np.nan)
        )
        df = df.dropna(subset=[TARGET])
        df[TARGET] = df[TARGET].astype(int)
    return df.reset_index(drop=True)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Raw telco rows -> model features. Pure function: no fitting, no leakage."""
    out = df[FEATURE_COLUMNS].copy()
    for col in NUMERIC_RAW:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["SeniorCitizen"] = out["SeniorCitizen"].fillna(0)
    # new customers (tenure 0) have a blank TotalCharges in the IBM data: nothing billed yet
    out.loc[out["TotalCharges"].isna() & (out["tenure"] == 0), "TotalCharges"] = 0.0
    out["avg_monthly_spend"] = np.where(
        out["tenure"] > 0, out["TotalCharges"] / out["tenure"].clip(lower=1), out["MonthlyCharges"]
    )
    out["n_addons"] = (out[ADDONS] == "Yes").sum(axis=1)
    out["tenure_group"] = pd.cut(
        out["tenure"], [-1, 12, 24, 48, 72, 1e9], labels=["0-12", "13-24", "25-48", "49-72", "72+"]
    ).astype(object).where(out["tenure"].notna(), "Unknown").astype(str)
    for col in CATEGORICAL_RAW:
        out[col] = out[col].fillna("Unknown").astype(str)
    return out[NUMERIC_MODEL + CATEGORICAL_MODEL]


def generate_synthetic(n: int = 5000, seed: int = 42, drift: bool = False, with_target: bool = True) -> pd.DataFrame:
    """Synthetic data with the IBM Telco schema. drift=True shifts the distributions (for demos/tests)."""
    rng = np.random.default_rng(seed)
    p_contract = [0.75, 0.15, 0.10] if drift else [0.55, 0.21, 0.24]
    contract = rng.choice(["Month-to-month", "One year", "Two year"], n, p=p_contract)
    scale = 9 if drift else 18
    tenure = rng.gamma(2.0, scale, n).astype(int) + (contract != "Month-to-month") * rng.integers(0, 12, n)
    tenure = np.clip(tenure, 0, 72)
    tenure[rng.random(n) < 0.01] = 0  # brand-new customers, like the real data
    p_net = [0.2, 0.6, 0.2] if drift else [0.34, 0.44, 0.22]
    internet = rng.choice(["DSL", "Fiber optic", "No"], n, p=p_net)
    phone = rng.choice(["Yes", "No"], n, p=[0.9, 0.1])
    multi = np.where(phone == "No", "No phone service", rng.choice(["Yes", "No"], n))

    def addon(p):
        return np.where(internet == "No", "No internet service", rng.choice(["Yes", "No"], n, p=[p, 1 - p]))

    sec, bak, dev, tech, tv, mov = addon(0.3), addon(0.35), addon(0.35), addon(0.3), addon(0.4), addon(0.4)
    base = np.select([internet == "DSL", internet == "Fiber optic"], [45, 80], 20) + (15 if drift else 0)
    n_add = sum((x == "Yes").astype(int) for x in (sec, bak, dev, tech, tv, mov))
    monthly = np.round(base + n_add * 5 + rng.normal(0, 4, n), 2).clip(18.25, 120)
    total = np.round(monthly * tenure * rng.uniform(0.95, 1.05, n), 2).astype(object)
    total[tenure == 0] = " "  # IBM data has blank TotalCharges for brand-new customers
    pay = rng.choice(
        ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"], n,
        p=[0.45, 0.2, 0.17, 0.18] if drift else [0.34, 0.23, 0.22, 0.21],
    )
    df = pd.DataFrame({
        ID_COL: [f"SYN-{seed}-{i:05d}" for i in range(n)],
        "gender": rng.choice(["Male", "Female"], n),
        "SeniorCitizen": rng.choice([0, 1], n, p=[0.84, 0.16]),
        "Partner": rng.choice(["Yes", "No"], n),
        "Dependents": rng.choice(["Yes", "No"], n, p=[0.3, 0.7]),
        "tenure": tenure, "PhoneService": phone, "MultipleLines": multi, "InternetService": internet,
        "OnlineSecurity": sec, "OnlineBackup": bak, "DeviceProtection": dev, "TechSupport": tech,
        "StreamingTV": tv, "StreamingMovies": mov, "Contract": contract,
        "PaperlessBilling": rng.choice(["Yes", "No"], n, p=[0.6, 0.4]), "PaymentMethod": pay,
        "MonthlyCharges": monthly, "TotalCharges": total,
    })
    if with_target:
        logit = (-1.25 + 1.3 * (contract == "Month-to-month") - 1.0 * (contract == "Two year")
                 - 0.035 * tenure + 0.7 * (internet == "Fiber optic") + 0.012 * (monthly - 65)
                 + 0.45 * (pay == "Electronic check") - 0.5 * (tech == "Yes") - 0.4 * (sec == "Yes")
                 + 0.3 * (df["SeniorCitizen"].to_numpy() == 1) + rng.normal(0, 0.6, n))
        df[TARGET] = np.where(rng.random(n) < 1 / (1 + np.exp(-logit)), "Yes", "No")
    return df


def download_telco(dest: Path, timeout: int = 20) -> pd.DataFrame:
    """Try to download the real IBM Telco CSV. Raises RuntimeError if it is not reachable."""
    import requests

    last = None
    for url in TELCO_URLS:
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            if missing_columns(df):
                raise ValueError("downloaded file does not look like the Telco dataset")
            df.to_csv(dest, index=False)
            return df
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"Could not download the IBM Telco dataset ({last}). Use upload or the synthetic generator.")
