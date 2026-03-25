"""Shared helpers for ElevenLabs agent HTTP tools."""

from __future__ import annotations

import re
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.call import Call
from app.models.product import Product
from app.services.business_service import get_business_by_id, get_business_by_phone


def normalize_phone_candidates(raw: str) -> list[str]:
    """Return a small set of phone string variants to match DB `businesses.phone_number`."""
    s = (raw or "").strip()
    if not s:
        return []
    digits = re.sub(r"\D", "", s)
    out: list[str] = []
    for candidate in {s, s.replace(" ", ""), f"+{digits}" if digits else ""}:
        if candidate and candidate not in out:
            out.append(candidate)
    # US-style: +1XXXXXXXXXX vs 10-digit local
    if len(digits) == 11 and digits.startswith("1"):
        out.append("+" + digits)
        out.append("+1" + digits[1:])
    if len(digits) == 10:
        out.append("+1" + digits)
    # de-dup preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def resolve_business_by_twilio_to(db: Session, to_number: str):
    for cand in normalize_phone_candidates(to_number):
        biz = get_business_by_phone(db, cand)
        if biz:
            return biz
    return None


def parse_uuid(value: str, field: str) -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid {field}") from exc


def assert_call_belongs(
    db: Session,
    *,
    call_id: UUID,
    business_id: UUID,
    customer_id: UUID,
) -> Call:
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise LookupError("Call not found")
    if call.business_id != business_id:
        raise PermissionError("Call does not belong to this business")
    if call.customer_id != customer_id:
        raise PermissionError("Call customer mismatch")
    return call


def product_for_business(db: Session, product_id: UUID, business_id: UUID) -> Optional[Product]:
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p or p.business_id != business_id:
        return None
    return p


def required_custom_field_names(product: Product) -> list[str]:
    meta = product.product_meta or {}
    fields = meta.get("custom_fields") or []
    if isinstance(fields, list):
        return [str(x) for x in fields if x]
    return []


def custom_fields_satisfied(
    required: list[str],
    provided: Optional[dict],
) -> list[str]:
    if not required:
        return []
    provided = provided or {}
    missing: list[str] = []
    for name in required:
        v = provided.get(name)
        if v is None or (isinstance(v, str) and not v.strip()):
            missing.append(name)
    return missing
