"""Pydantic schemas for subscription plans and lifecycle behavior flags."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanCreateRequest(BaseModel):
    code: Optional[str] = Field(default=None, max_length=64)
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    billing_interval: str = Field(
        default="monthly", pattern="^(daily|weekly|monthly|yearly)$"
    )
    minimum_quantity: int = Field(default=1, ge=1)
    available_from: Optional[date] = None
    available_until: Optional[date] = None
    trial_period_days: int = Field(default=0, ge=0)
    default_payment_term_days: int = Field(default=14, ge=0)
    auto_close: bool = False
    early_close_allowed: bool = True
    pause_allowed: bool = True
    resume_allowed: bool = True
    renewal_allowed: bool = True
    is_active: bool = True


class PlanUpdateRequest(BaseModel):
    code: Optional[str] = Field(default=None, max_length=64)
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    billing_interval: Optional[str] = Field(
        default=None, pattern="^(daily|weekly|monthly|yearly)$"
    )
    minimum_quantity: Optional[int] = Field(default=None, ge=1)
    available_from: Optional[date] = None
    available_until: Optional[date] = None
    trial_period_days: Optional[int] = Field(default=None, ge=0)
    default_payment_term_days: Optional[int] = Field(default=None, ge=0)
    auto_close: Optional[bool] = None
    early_close_allowed: Optional[bool] = None
    pause_allowed: Optional[bool] = None
    resume_allowed: Optional[bool] = None
    renewal_allowed: Optional[bool] = None
    is_active: Optional[bool] = None


class PlanResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    billing_interval: str
    minimum_quantity: int
    available_from: Optional[date] = None
    available_until: Optional[date] = None
    trial_period_days: int
    default_payment_term_days: int
    auto_close: bool
    early_close_allowed: bool
    pause_allowed: bool
    resume_allowed: bool
    renewal_allowed: bool
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

