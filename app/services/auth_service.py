from app.models.user import User
from app.models.business import Business
from app.core.security import hash_password, verify_password, create_access_token


def register_user(db, name, email, password, business_name, phone_number, business_type=None, role="owner"):

    email = email.strip().lower() 
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None, "Email already registered"

    business = Business(
        name=business_name,
        business_type=business_type,
        phone_number=phone_number
    )
    db.add(business)
    db.flush()

    user = User(
        business_id=business.id,
        name=name,
        email=email,
        hashed_password=hash_password(password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(business)

    print(f"User registered: id={user.id}, email={user.email}, role={user.role}, business={business.name}")

    token = create_access_token({
        "sub": str(user.id),
        "business_id": str(business.id),
        "role": user.role
    })

    return {"user": user, "business": business, "token": token}, None


def login_user(db, email, password):

    email = email.strip().lower() 
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.hashed_password):
        return None, "Invalid email or password"

    token = create_access_token({
        "sub": str(user.id),
        "business_id": str(user.business_id),
        "role": user.role
    })

    print(f"User logged in: id={user.id}, email={user.email}")

    return {"user": user, "token": token}, None


def get_user_by_id(db, user_id):
    return db.query(User).filter(User.id == user_id).first()
