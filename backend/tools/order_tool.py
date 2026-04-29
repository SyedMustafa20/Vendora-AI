import re
from models.orders import Order
from models.order_items import OrderItem
from models.products import Product
from models.users import User


def extract_order_code(message: str):
    match = re.search(r"ORD\d+", message.upper())
    return match.group(0) if match else None


def execute_order_lookup(db, message: str, user):
    order_code = extract_order_code(message)

    if not order_code:
        return {
            "type": "order",
            "found": False,
            "message": "Please provide a valid order ID (e.g. ORD123)."
        }

    order = db.query(Order).filter(Order.order_code == order_code).first()

    if not order:
        return {
            "type": "order",
            "found": False,
            "message": f"No order found for {order_code}"
        }

    customer = db.query(User).filter(User.id == order.user_id).first()

    items = (
        db.query(OrderItem, Product)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(OrderItem.order_id == order.id)
        .all()
    )

    item_list = [
        {
            "product_name": product.name,
            "quantity": oi.quantity,
            "price": float(oi.price),
            "subtotal": float(oi.quantity * oi.price),
        }
        for oi, product in items
    ]

    return {
        "type": "order",
        "found": True,
        "order": {
            "order_code": order.order_code,
            "status": order.status,
            "total": float(order.total_amount),
            "created_at": str(order.created_at),
        },
        "customer": {
            "id": customer.id,
            "phone": customer.phone,
        },
        "items": item_list
    }