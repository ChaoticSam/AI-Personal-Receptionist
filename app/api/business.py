from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.business_schema import BusinessCreate, BusinessUpdate, BusinessResponse
from app.services.business_service import (
    business_to_response,
    create_business,
    get_business_by_id,
    update_business,
)

router = APIRouter()


@router.post("/business/register", response_model=BusinessResponse)
def register_business(payload: BusinessCreate, db: Session = Depends(get_db)):

    business = create_business(
        db,
        name=payload.name,
        business_type=payload.business_type,
        phone_number=payload.phone_number,
        timezone=payload.timezone,
        address=payload.address,
    )

    return business_to_response(business)


@router.get("/business/{business_id}", response_model=BusinessResponse)
def get_business(business_id: str, db: Session = Depends(get_db)):

    business = get_business_by_id(db, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    return business_to_response(business)


@router.patch("/business/{business_id}", response_model=BusinessResponse)
def patch_business(
    business_id: str,
    payload: BusinessUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if str(current_user.business_id) != business_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this business")

    data = payload.model_dump(exclude_unset=True)
    business = update_business(db, business_id, **data)

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    return business_to_response(business)
