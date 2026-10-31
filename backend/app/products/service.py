"""Business logic for products and product variants."""
import secrets
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.audit import log_audit_event
from app.models import Product, ProductVariant, User
from app.products.schemas import (
    ProductCreateRequest,
    ProductUpdateRequest,
    ProductVariantCreate,
    ProductVariantUpdate,
)


def list_products(
    db: Session,
    search: Optional[str] = None,
    product_type: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> List[Product]:
    query = db.query(Product)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Product.name.ilike(term), Product.sku.ilike(term)))
    if product_type:
        query = query.filter(Product.product_type == product_type)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    return query.order_by(Product.id.desc()).all()


def create_product(db: Session, payload: ProductCreateRequest, actor: User) -> Product:
    sku = (payload.sku or f"PRD-{secrets.token_hex(3).upper()}").strip().upper()
    existing = db.query(Product).filter(Product.sku == sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product with SKU '{sku}' already exists.",
        )

    product = Product(
        sku=sku,
        name=payload.name.strip(),
        product_type=payload.product_type,
        sales_price=payload.sales_price,
        cost_price=payload.cost_price,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    db.add(product)
    db.flush()

    for var_in in payload.variants:
        variant = ProductVariant(
            product_id=product.id,
            name=var_in.name.strip(),
            sku=var_in.sku,
            attribute_name=var_in.attribute_name,
            attribute_value=var_in.attribute_value,
            price_extra=var_in.price_extra,
            is_active=var_in.is_active,
        )
        db.add(variant)

    log_audit_event(
        db,
        action="product.create",
        entity_type="product",
        entity_id=product.id,
        actor=actor,
        metadata={"sku": product.sku, "name": product.name, "sales_price": str(product.sales_price)},
    )
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


def update_product(
    db: Session, product_id: int, payload: ProductUpdateRequest, actor: User
) -> Product:
    product = get_product(db, product_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "sku" in update_data and update_data["sku"]:
        new_sku = update_data["sku"].strip().upper()
        conflict = (
            db.query(Product)
            .filter(Product.sku == new_sku, Product.id != product_id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another product already uses SKU '{new_sku}'.",
            )
        update_data["sku"] = new_sku

    for field, value in update_data.items():
        setattr(product, field, value)

    log_audit_event(
        db,
        action="product.update",
        entity_type="product",
        entity_id=product.id,
        actor=actor,
        metadata=update_data,
    )
    db.commit()
    db.refresh(product)
    return product


def create_variant(
    db: Session, product_id: int, payload: ProductVariantCreate, actor: User
) -> ProductVariant:
    product = get_product(db, product_id)
    variant = ProductVariant(
        product_id=product.id,
        name=payload.name.strip(),
        sku=payload.sku,
        attribute_name=payload.attribute_name,
        attribute_value=payload.attribute_value,
        price_extra=payload.price_extra,
        is_active=payload.is_active,
    )
    db.add(variant)
    db.flush()
    log_audit_event(
        db,
        action="product.create_variant",
        entity_type="product_variant",
        entity_id=variant.id,
        actor=actor,
        metadata={"product_id": product.id, "name": variant.name, "price_extra": str(variant.price_extra)},
    )
    db.commit()
    db.refresh(variant)
    return variant


def update_variant(
    db: Session, product_id: int, variant_id: int, payload: ProductVariantUpdate, actor: User
) -> ProductVariant:
    variant = (
        db.query(ProductVariant)
        .filter(ProductVariant.id == variant_id, ProductVariant.product_id == product_id)
        .first()
    )
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found.")
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(variant, field, value)
    log_audit_event(
        db,
        action="product.update_variant",
        entity_type="product_variant",
        entity_id=variant.id,
        actor=actor,
        metadata=update_data,
    )
    db.commit()
    db.refresh(variant)
    return variant

