from app.models.business import Business


def create_business(db, name, business_type, phone_number, timezone=None, address=None):

    business = Business(
        name=name,
        business_type=business_type,
        phone_number=phone_number,
        timezone=timezone,
        address=address
    )

    db.add(business)
    db.commit()
    db.refresh(business)

    print(f"Business registered: id={business.id}, name={business.name}, phone={business.phone_number}")

    return business


def get_business_by_id(db, business_id):

    return db.query(Business).filter(Business.id == business_id).first()


def get_business_by_phone(db, phone_number):

    return db.query(Business).filter(Business.phone_number == phone_number).first()


def update_business(db, business_id, **fields):
    """
    Partially update a business record.
    voice_config is merged with existing values rather than fully replaced.
    """
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        return None

    for key, value in fields.items():
        if value is None:
            continue
        if key == "voice_config" and isinstance(value, dict):
            # Create a new dict so SQLAlchemy detects the JSONB change
            business.voice_config = {**(business.voice_config or {}), **value}
        else:
            setattr(business, key, value)

    db.commit()
    db.refresh(business)
    return business
