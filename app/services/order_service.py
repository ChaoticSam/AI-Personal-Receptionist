from app.models.order import Order
from app.models.customer import Customer
from app.models.product import Product


def create_order(db, business_id, customer_id, quantity, product_id=None, call_id=None, order_notes=None):
    order = Order(
        business_id=business_id,
        customer_id=customer_id,
        product_id=product_id,
        call_id=call_id,
        quantity=quantity,
        order_notes=order_notes
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    print(f"Order created: id={order.id}, business_id={order.business_id}, customer_id={order.customer_id}")

    return order


def get_orders_by_business(db, business_id):

    rows = (
        db.query(Order, Customer, Product)
        .outerjoin(Customer, Order.customer_id == Customer.id)
        .outerjoin(Product, Order.product_id == Product.id)
        .filter(Order.business_id == business_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    results = []
    for order, customer, product in rows:
        item = {
            "id": order.id,
            "business_id": order.business_id,
            "customer_id": order.customer_id,
            "product_id": order.product_id,
            "call_id": order.call_id,
            "quantity": order.quantity,
            "status": order.status,
            "order_notes": order.order_notes,
            "deadline": order.deadline,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "customer_name": customer.name if customer else None,
            "customer_phone": customer.phone if customer else None,
            "product_name": product.name if product else None,
        }
        results.append(item)

    return results


def update_order_status(db, order_id, status):

    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        return None

    order.status = status
    db.commit()
    db.refresh(order)

    return order
