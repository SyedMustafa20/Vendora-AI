from models.products import Product


# STEP 1: fuzzy search (for suggestions)
def search_products(db, message: str):
    keywords = message.lower()

    products = db.query(Product).filter(
        Product.name.ilike(f"%{keywords}%")
        | Product.category.ilike(f"%{keywords}%")
    ).limit(5).all()

    if not products:
        return {
            "type": "product",
            "stage": "search",
            "found": False,
            "message": "No products found",
            "suggestions": []
        }

    return {
        "type": "product",
        "stage": "search",
        "found": True,
        "suggestions": [
            {
                "product_id": p.id,
                "name": p.name,
                "price": float(p.price),
                "category": p.category
            }
            for p in products
        ]
    }


# STEP 2: exact product fetch
def get_product_by_name(db, product_name: str):
    product = db.query(Product).filter(
        Product.name.ilike(product_name)
    ).first()

    if not product:
        return {
            "type": "product",
            "stage": "detail",
            "found": False,
            "message": "Product not found. Please select from suggestions."
        }

    return {
        "type": "product",
        "stage": "detail",
        "found": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "description": product.description,
            "stock": product.stock,
            "category": product.category
        }
    }