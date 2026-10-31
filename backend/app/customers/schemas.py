"""Pydantic schemas for customer management and customer portal."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import EmailAddress as EmailStr


class CustomerCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=64)
    tax_id: Optional[str] = Field(default=None, max_length=64)
    billing_address: str = Field(default="", max_length=1000)
    city: Optional[str] = Field(default=None, max_length=128)
    state: Optional[str] = Field(default=None, max_length=128)
    country: Optional[str] = Field(default="US", max_length=128)
    postal_code: Optional[str] = Field(default=None, max_length=32)
    notes: Optional[str] = None
    password: Optional[str] = Field(
        default=None,
        description="Optional password if staff wants to provision a portal user account immediately",
    )


class CustomerUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    company_name: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=64)
    tax_id: Optional[str] = Field(default=None, max_length=64)
    billing_address: Optional[str] = Field(default=None, max_length=1000)
    city: Optional[str] = Field(default=None, max_length=128)
    state: Optional[str] = Field(default=None, max_length=128)
    country: Optional[str] = Field(default=None, max_length=128)
    postal_code: Optional[str] = Field(default=None, max_length=32)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    name: str
    company_name: Optional[str] = None
    email: str
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    billing_address: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    active_subscriptions_count: int = 0
    total_billed: Decimal = Decimal("0.00")
    outstanding_balance: Decimal = Decimal("0.00")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedCustomerResponse(BaseModel):
    items: List[CustomerResponse]
    total: int
    page: int
    page_size: int
