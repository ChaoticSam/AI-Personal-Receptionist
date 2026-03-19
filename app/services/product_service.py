from app.models.product import Product
from app.services.embedding_service import upsert_product_embedding

# Fields that affect embeddings and require a re-generation when changed
EMBEDDING_FIELDS = {"name", "description", "product_meta"}


def create_product(db, business_id, name, description=None, price=None, unit=None,
                   is_available="true", product_meta=None):
    product = Product(
        business_id=business_id,
        name=name,
        description=description,
        price=price,
        unit=unit,
        is_available=is_available,
        product_meta=product_meta,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    print(f"Product created: id={product.id}, name={product.name}, business_id={product.business_id}")

    # Auto-generate embedding after product is persisted
    upsert_product_embedding(db, product)

    return product


def get_products_by_business(db, business_id):
    return db.query(Product).filter(Product.business_id == business_id).all()


def get_product_by_id(db, product_id):
    return db.query(Product).filter(Product.id == product_id).first()


def update_product(db, product_id, **fields):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        return None

    embedding_needs_refresh = any(k in EMBEDDING_FIELDS for k in fields)

    for key, value in fields.items():
        if value is not None and hasattr(product, key):
            setattr(product, key, value)

    db.commit()
    db.refresh(product)

    # Re-generate embedding only if semantic fields changed
    if embedding_needs_refresh:
        upsert_product_embedding(db, product)

    return product
