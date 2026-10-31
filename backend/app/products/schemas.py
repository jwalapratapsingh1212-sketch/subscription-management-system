"""Pydantic schemas for products and product variants."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductVariantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: Optional[str] = Field(default=None, max_length=64)
    attribute_name: Optional[str] = Field(default="Tier", max_length=128)
    attribute_value: Optional[str] = Field(default=None, max_length=128)
    price_extra: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    is_active: bool = True


class ProductVariantUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    sku: Optional[str] = Field(default=None, max_length=64)
    attribute_name: Optional[str] = Field(default=None, max_length=128)
    attribute_value: Optional[str] = Field(default=None, max_length=128)
    price_extra: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    is_active: Optional[bool] = None


class ProductVariantResponse(BaseModel):
    id: int
    product_id: int
    name: str
    sku: Optional[str] = None
    attribute_name: Optional[str] = None
    attribute_value: Optional[str] = None
    price_extra: Decimal
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductCreateRequest(BaseModel):
    sku: Optional[str] = Field(default=None, max_length=64)
    name: str = Field(..., min_length=2, max_length=255)
    product_type: str = Field(
        default="service", pattern="^(service|software|consumable|digital|hardware)$"
    )
    sales_price: Decimal = Field(..., ge=Decimal("0.00"))
    cost_price: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    notes: Optional[str] = None
    is_active: bool = True
    variants: List[ProductVariantCreate] = Field(default_factory=list)


class ProductUpdateRequest(BaseModel):
    sku: Optional[str] = Field(default=None, max_length=64)
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    product_type: Optional[str] = Field(
        default=None, pattern="^(service|software|consumable|digital|hardware)$"
    )
    sales_price: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    cost_price: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    sku: str
    name: str
    product_type: str
    sales_price: Decimal
    cost_price: Decimal
    notes: Optional[str] = None
    is_active: bool
    variants: List[ProductVariantResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

