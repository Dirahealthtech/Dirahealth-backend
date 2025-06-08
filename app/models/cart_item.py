from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base
from ..models.base import TimeStampMixin

class CartItem(Base, TimeStampMixin):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    cart = relationship("Cart", back_populates="cart_items")
    product = relationship("Product")


    def __repr__(self):
        return f'<CartItem(cart_id={self.cart_id}, product_id={self.product_id}, quantity={self.quantity})>'
