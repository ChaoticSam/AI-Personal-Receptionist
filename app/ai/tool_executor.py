"""
Tool Executor — bridges the AI decisions to actual service calls.

Each tool function receives the session, db (optional), and kwargs, then
returns a structured result dict that will be passed back to the AI for
response generation.
"""

import threading

from app.services.order_service import create_order, update_order_status


def _fire_notification_async(business_id: str, order_data: dict, db_factory):
    """
    Dispatch the WhatsApp notification in a background thread so it never
    blocks the real-time call response.
    """
    def _run():
        db = db_factory()
        try:
            from app.services.notification_service import notify_business
            result = notify_business(db=db, business_id=business_id, order_data=order_data)
            status = "sent" if result["success"] else f"failed ({result['error']})"
            print(f"[Notification] order={order_data.get('order_id')} → {status}")
        except Exception as e:
            print(f"[Notification] Unexpected error: {e}")
        finally:
            db.close()

    threading.Thread(target=_run, daemon=True).start()


def tool_create_order(session, db, product_id=None, quantity=1, order_notes=None, custom_fields=None) -> dict:
    """
    Persist the confirmed order to the database.
    Also saves per-product custom fields and fires a WhatsApp notification.
    """
    order = create_order(
        db,
        business_id=session.business_id,
        customer_id=session.customer_id,
        product_id=product_id,
        call_id=session.call_id,
        quantity=quantity,
        order_notes=order_notes,
    )

    # Persist custom fields if any
    if custom_fields:
        try:
            from app.models.order_customization import OrderCustomization
            for field_name, field_value in custom_fields.items():
                if field_value is not None and str(field_value).strip():
                    db.add(OrderCustomization(
                        order_id=order.id,
                        field_name=field_name,
                        field_value=str(field_value),
                    ))
            db.commit()
        except Exception as e:
            print(f"Failed to save order customizations for order={order.id}: {e}")

    session.order_draft["draft_status"] = "confirmed"
    session.order_draft["_confirmed_order_id"] = str(order.id)

    # ── Notify business owner via WhatsApp ─────────────────────────────────
    try:
        from app.db.session import SessionLocal
        from app.models.customer import Customer
        from app.models.product import Product

        customer = db.query(Customer).filter(Customer.id == session.customer_id).first()
        product = db.query(Product).filter(Product.id == product_id).first()

        order_data = {
            "order_id": str(order.id),
            "product_name": product.name if product else session.order_draft.get("product_name"),
            "quantity": quantity,
            "customer_name": customer.name if customer else None,
            "customer_phone": customer.phone_number if customer else None,
            "deadline": session.order_draft.get("deadline"),
            "custom_fields": custom_fields or {},
            "order_notes": order_notes,
        }

        _fire_notification_async(
            business_id=str(session.business_id),
            order_data=order_data,
            db_factory=SessionLocal,
        )
    except Exception as e:
        print(f"[Notification] Could not schedule notification: {e}")

    return {
        "success": True,
        "order_id": str(order.id),
        "message": "Order has been placed successfully."
    }


def tool_cancel_order(session, db, order_id: str) -> dict:
    """Cancel an existing order."""
    order = update_order_status(db, order_id=order_id, status="cancelled")
    if not order:
        return {"success": False, "message": f"Order {order_id} not found."}
    return {"success": True, "message": f"Order {order_id} has been cancelled."}


def tool_get_order_status(session, db, order_id: str) -> dict:
    """Look up order status."""
    from app.models.order import Order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return {"success": False, "message": f"Order {order_id} not found."}
    return {"success": True, "status": order.status, "message": f"Your order is currently {order.status}."}


TOOL_MAP = {
    "create_order": tool_create_order,
    "cancel_order": tool_cancel_order,
    "get_order_status": tool_get_order_status,
}


def execute_tool(tool_name: str, session, db=None, **kwargs) -> dict:
    """Dispatch to the appropriate tool function. Returns a result dict."""
    handler = TOOL_MAP.get(tool_name)
    if not handler:
        return {"success": False, "message": f"Unknown tool: {tool_name}"}
    try:
        return handler(session=session, db=db, **kwargs)
    except Exception as e:
        print(f"Tool execution error [{tool_name}]: {e}")
        return {"success": False, "message": "Something went wrong. Please try again."}
