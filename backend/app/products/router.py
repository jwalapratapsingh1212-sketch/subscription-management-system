"""HTTP endpoints for product catalog and variant management."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user, require_staff_or_admin
from app.models import User
from app.products.schemas import (
    ProductCreateRequest,
    ProductResponse,
    ProductUpdateRequest,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
)
from app.products.service import (
    create_product,
    create_variant,
    get_product,
    list_products,
    update_product,
    update_variant,
)

router = APIRouter(prefix="/products", tags=["Products & Variants"])


@router.get("", response_model=List[ProductResponse])
def get_products_list(
    search: Optional[str] = Query(default=None),
    product_type: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List products and their variants."""
    return list_products(db, search=search, product_type=product_type, is_active=is_active)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def post_product(
    payload: ProductCreateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Create a product and optional initial variants (Staff or Admin)."""
    return create_product(db, payload, staff_user)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product_detail(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a product by ID."""
    return get_product(db, product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
def patch_product(
    product_id: int,
    payload: ProductUpdateRequest,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Update product fields or active/inactive status (Staff or Admin)."""
    return update_product(db, product_id, payload, staff_user)


@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_product_variant(
    product_id: int,
    payload: ProductVariantCreate,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Add a pricing variant to an existing product (Staff or Admin)."""
    return create_variant(db, product_id, payload, staff_user)


@router.patch(
    "/{product_id}/variants/{variant_id}",
    response_model=ProductVariantResponse,
)
def patch_product_variant(
    product_id: int,
    variant_id: int,
    payload: ProductVariantUpdate,
    staff_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db),
):
    """Update an existing product variant (Staff or Admin)."""
    return update_variant(db, product_id, variant_id, payload, staff_user)

