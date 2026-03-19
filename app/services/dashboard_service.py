from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.call import Call
from app.models.order import Order
from app.models.product import Product
from app.models.customer import Customer


DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _time_ago(dt: datetime) -> str:
    diff = datetime.utcnow() - dt
    minutes = int(diff.total_seconds() / 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hr ago"
    return f"{diff.days} days ago"


def get_dashboard_stats(db, business_id):

    total_calls    = db.query(func.count(Call.id)).filter(Call.business_id == business_id).scalar() or 0
    total_orders   = db.query(func.count(Order.id)).filter(Order.business_id == business_id).scalar() or 0
    total_products = db.query(func.count(Product.id)).filter(Product.business_id == business_id).scalar() or 0
    total_customers = db.query(func.count(Customer.id)).filter(Customer.business_id == business_id).scalar() or 0

    week_start = datetime.utcnow() - timedelta(days=6)

    # Calls grouped by day of week
    call_rows = (
        db.query(
            func.to_char(Call.created_at, 'Dy').label("day"),
            func.count(Call.id).label("count")
        )
        .filter(Call.business_id == business_id, Call.created_at >= week_start)
        .group_by(func.to_char(Call.created_at, 'Dy'))
        .all()
    )
    call_map = {r.day[:3]: r.count for r in call_rows}
    calls_this_week = [{"day": d, "count": call_map.get(d, 0)} for d in DAYS]

    # Orders grouped by day of week
    order_rows = (
        db.query(
            func.to_char(Order.created_at, 'Dy').label("day"),
            func.count(Order.id).label("count")
        )
        .filter(Order.business_id == business_id, Order.created_at >= week_start)
        .group_by(func.to_char(Order.created_at, 'Dy'))
        .all()
    )
    order_map = {r.day[:3]: r.count for r in order_rows}
    orders_this_week = [{"day": d, "count": order_map.get(d, 0)} for d in DAYS]

    # Recent calls (last 5)
    recent = (
        db.query(Call)
        .filter(Call.business_id == business_id)
        .order_by(Call.created_at.desc())
        .limit(5)
        .all()
    )
    recent_calls = [
        {
            "id": str(c.id),
            "phone": c.caller_phone,
            "time": _time_ago(c.created_at),
            "status": c.status,
        }
        for c in recent
    ]

    return {
        "total_calls": total_calls,
        "total_orders": total_orders,
        "total_products": total_products,
        "total_customers": total_customers,
        "calls_this_week": calls_this_week,
        "orders_this_week": orders_this_week,
        "recent_calls": recent_calls,
    }
