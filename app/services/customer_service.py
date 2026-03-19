from app.models.customer import Customer


def find_or_create_customer(db, business_id, phone, name, email, notes):
    customer = (
        db.query(Customer)
        .filter(
            Customer.phone == phone,
            Customer.business_id == business_id
        )
        .first()
    )

    if customer:
        return customer

    customer = Customer(
        business_id=business_id,
        phone=phone,
        name=name,
        email=email,
        notes=notes
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    # send customer to CRM
    print(f"Customer details: id={customer.id}, business_id={customer.business_id}, phone={customer.phone}, name={customer.name}")

    return customer