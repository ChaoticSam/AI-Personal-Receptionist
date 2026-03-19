from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductResponse
from app.services.product_service import create_product, get_products_by_business, get_product_by_id, update_product

router = APIRouter()


@router.post("/products", response_model=ProductResponse)
def add_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product_meta_dict = payload.product_meta.model_dump() if payload.product_meta else None
    product = create_product(
        db,
        business_id=current_user.business_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        unit=payload.unit,
        is_available=payload.is_available or "true",
        product_meta=product_meta_dict,
    )
    return product


@router.get("/products", response_model=List[ProductResponse])
def list_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_products_by_business(db, current_user.business_id)


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/products/{product_id}", response_model=ProductResponse)
def patch_product(
    product_id: str,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fields = payload.model_dump(exclude_none=True)
    # Convert nested product_meta model to plain dict for SQLAlchemy JSONB storage
    if "product_meta" in fields and hasattr(fields["product_meta"], "model_dump"):
        fields["product_meta"] = fields["product_meta"].model_dump()
    product = update_product(db, product_id, **fields)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
