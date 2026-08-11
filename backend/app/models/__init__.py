# app/models/__init__.py

from app.models.user import User
from app.models.listing import Listing
from app.models.offer import Offer
from app.models.order import Order
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.invoice import Invoice
from app.models.transporter import TransporterProfile
from app.models.price_history import PriceHistory
from app.models.seasonality import Seasonality

# Exportez tous les modèles pour qu'Alembic les découvre
__all__ = [
    "User",
    "Listing",
    "Offer",
    "Order",
    "Conversation",
    "Message",
    "Invoice",
    "TransporterProfile",
    "PriceHistory",
    "Seasonality"
]
