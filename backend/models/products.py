from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime
from sqlalchemy.sql import func
from db.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    category = Column(String(50), index=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, default=0)
    description = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())