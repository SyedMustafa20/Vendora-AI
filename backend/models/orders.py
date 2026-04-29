from sqlalchemy import Column, Integer, String, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_code = Column(String(20), unique=True, index=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

    status = Column(String(30), default="pending")  
    total_amount = Column(Numeric(10, 2), default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    customer = relationship("Customer", backref="orders")
    items = relationship("OrderItem", back_populates="order")