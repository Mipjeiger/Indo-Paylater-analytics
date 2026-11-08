"""Validated API request and response schemas."""

from pydantic import BaseModel, Field


class TWP90Request(BaseModel):
    borrower_id: str = Field(min_length=1)
    features: dict[str, object]


class TWP90Response(BaseModel):
    borrower_id: str
    default_probability: float = Field(ge=0, le=1)
    model_version: str | None = None


class DTIResponse(BaseModel):
    borrower_id: str
    dti: float
    financial_distress_index: float
    model_version: str | None = None


class RootCauseResponse(BaseModel):
    borrower_id: str
    root_cause: str
    model_version: str | None = None
