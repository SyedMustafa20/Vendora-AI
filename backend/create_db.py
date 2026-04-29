from db.database import Base, engine

# Import every model so SQLAlchemy registers it on Base.metadata before create_all.
from models.users import User  # noqa: F401
from models.conversation import Conversation  # noqa: F401
from models.message import Message  # noqa: F401
from models.admins import Admin  # noqa: F401
from models.customers import Customer  # noqa: F401
from models.products import Product  # noqa: F401
from models.orders import Order  # noqa: F401
from models.order_items import OrderItem  # noqa: F401
from models.agent import AgentConfig  # noqa: F401


Base.metadata.create_all(bind=engine)

print("Tables created successfully!")
