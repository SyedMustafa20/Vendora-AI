from sqlalchemy import Column, Integer, String, DateTime, Boolean, VARCHAR
from datetime import datetime
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # phone is nullable so admins (registered with username/password) can be
    # created before they fill in profile data from the dashboard.
    phone = Column(String, unique=True, index=True, nullable=True)
    user_type = Column(VARCHAR(10), default="client")  # 'client' | 'agent' | 'admin'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
