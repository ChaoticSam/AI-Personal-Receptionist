from app.models.business import Business
from app.schemas.business_schema import AgentUiConfig, BusinessResponse
from app.services.elevenlabs_platform import merge_and_sync_agent_from_business


def business_to_response(business: Business) -> BusinessResponse:
    vc = business.voice_config or {}
    return BusinessResponse(
        id=business.id,
        name=business.name,
        business_type=business.business_type,
        phone_number=business.phone_number,
        whatsapp_number=business.whatsapp_number,
        timezone=business.timezone,
        address=business.address,
        elevenlabs_agent_id=business.elevenlabs_agent_id,
        convai_llm_model=business.convai_llm_model,
        convai_voice_id=business.convai_voice_id,
        agent_ui=AgentUiConfig(
            first_message=vc.get("first_message"),
            language=vc.get("language") or "en",
        ),
        created_at=business.created_at,
        updated_at=business.updated_at,
    )


def create_business(db, name, business_type, phone_number, timezone=None, address=None):

    business = Business(
        name=name,
        business_type=business_type,
        phone_number=phone_number,
        timezone=timezone,
        address=address,
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


def _blank_to_none(v):
    if v is None:
        return None
    if isinstance(v, str) and not v.strip():
        return None
    return v


def update_business(db, business_id, **fields):
    """
    Partial update. Only keys present in `fields` are applied (caller should use model_dump(exclude_unset=True)).
    Merges agent_ui into voice_config for first_message + language.
    Syncs ConvAI to ElevenLabs when elevenlabs_agent_id is set after update.
    """
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        return None

    agent_ui = fields.pop("agent_ui", None)

    str_cols = ("elevenlabs_agent_id", "convai_llm_model", "convai_voice_id")
    for key, value in fields.items():
        if key in str_cols:
            setattr(business, key, _blank_to_none(value))
        elif value is not None:
            setattr(business, key, value)

    if agent_ui is not None:
        if isinstance(agent_ui, dict):
            ui = {k: v for k, v in agent_ui.items() if v is not None}
        else:
            ui = agent_ui.model_dump(exclude_none=True)
        business.voice_config = {**(business.voice_config or {}), **ui}

    db.commit()
    db.refresh(business)

    if (business.elevenlabs_agent_id or "").strip():
        ok, err = merge_and_sync_agent_from_business(business)
        if not ok:
            print(f"[Business] ElevenLabs agent sync warning: {err}")

    return business
