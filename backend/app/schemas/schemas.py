from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    dataset_id: int
    algorithms: list[Literal["logistic_regression", "random_forest"]] = ["logistic_regression", "random_forest"]


class GenerateRequest(BaseModel):
    rows: int = Field(5000, ge=500, le=50000)
    seed: int = 42
    drift: bool = False
    name: str | None = None


class RetrainRequest(BaseModel):
    trigger: Literal["manual", "drift", "scheduled"] = "manual"
    dataset_id: int | None = None


class RejectRequest(BaseModel):
    reason: str = "Rejected manually"


class SettingsUpdate(BaseModel):
    values: dict[str, float]


class PredictionInput(BaseModel):
    gender: str
    SeniorCitizen: int = Field(ge=0, le=1)
    Partner: str
    Dependents: str
    tenure: int = Field(ge=0, le=120)
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: float = Field(ge=0)
    TotalCharges: float | None = None


SAMPLE_INPUT = {
    "gender": "Female", "SeniorCitizen": 0, "Partner": "Yes", "Dependents": "No", "tenure": 5,
    "PhoneService": "Yes", "MultipleLines": "No", "InternetService": "Fiber optic", "OnlineSecurity": "No",
    "OnlineBackup": "No", "DeviceProtection": "No", "TechSupport": "No", "StreamingTV": "Yes",
    "StreamingMovies": "Yes", "Contract": "Month-to-month", "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check", "MonthlyCharges": 89.9, "TotalCharges": 430.5,
}
