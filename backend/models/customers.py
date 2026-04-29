from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from db.database import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(120), unique=True, index=True)
    address = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())