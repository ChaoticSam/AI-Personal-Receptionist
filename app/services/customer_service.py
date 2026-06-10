from app.models.customer import Customer
from app.schemas.customer_schema import CustomerResponse


def create_customer(db, business_id, name, phone, email, notes):

    # check if customer already exists
    customer = (
        db.query(Customer)
        .filter(
            Customer.name == name,
            Customer.phone == phone,
            Customer.email == email,
            Customer.business_id == business_id
        )
        .first()
    )

    if customer:
        return customer

    # create customer
    customer = Customer(
        business_id=business_id,
        phone=phone,
        name=name,
        email=email,
        notes=notes
    )

    # add customer to database
    db.add(customer)
    db.commit()
    db.refresh(customer)

    # send customer to CRM
    print(f"Customer details: id={customer.id}, business_id={customer.business_id}, phone={customer.phone}, name={customer.name}")

    return customer

def find_or_create_customer(db, business_id, phone, name=None, email=None, notes=None):
    """
    Look up a customer by phone within a business; create one if absent.
    Phone is the stable identity for inbound calls, so name/email are optional.
    """
    phone = (phone or "").strip()
    customer = (
        db.query(Customer)
        .filter(Customer.business_id == business_id, Customer.phone == phone)
        .first()
    )
    if customer:
        # Backfill a real name if we learned one and only had a placeholder.
        if name and customer.name in (None, "", "Unknown"):
            customer.name = name
            db.commit()
            db.refresh(customer)
        return customer

    customer = Customer(
        business_id=business_id,
        phone=phone,
        name=name or "Unknown",
        email=email,
        notes=notes,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    print(f"Customer created: id={customer.id}, business_id={customer.business_id}, phone={customer.phone}")
    return customer


def get_customers_by_business(db, business_id):
    customers = db.query(Customer).filter(Customer.business_id == business_id).all()
    return [CustomerResponse(id=customer.id, business_id=customer.business_id, name=customer.name, phone=customer.phone, email=customer.email, notes=customer.notes) for customer in customers]