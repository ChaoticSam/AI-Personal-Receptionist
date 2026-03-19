from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.schemas.auth_schema import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import register_user, login_user
from app.db.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):

    result, error = register_user(
        db,
        name=payload.name,
        email=payload.email,
        password=payload.password,
        business_name=payload.business_name,
        phone_number=payload.phone_number,
        business_type=payload.business_type,
        role=payload.role
    )

    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    user = result["user"]
    business = result["business"]

    return TokenResponse(
        access_token=result["token"],
        user_id=user.id,
        business_id=business.id,
        name=user.name,
        email=user.email,
        role=user.role
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):

    result, error = login_user(db, email=payload.email, password=payload.password)

    if error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

    user = result["user"]

    return TokenResponse(
        access_token=result["token"],
        user_id=user.id,
        business_id=user.business_id,
        name=user.name,
        email=user.email,
        role=user.role
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
