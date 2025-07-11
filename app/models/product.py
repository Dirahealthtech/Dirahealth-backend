from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship

from ..db.base import Base
from ..enums import ProductType, WarrantyUnit
from ..models.base import TimeStampMixin



class Product(Base, TimeStampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    product_type = Column(Enum(ProductType), nullable=False)
    sku = Column(String, nullable=False, unique=True)
    price = Column(Float, nullable=False)
    discounted_price = Column(Float, default=0)
    tax_rate = Column(Float, default=0)
    stock = Column(Integer, nullable=False, default=0)
    images = Column(JSON)  # Stores array of image objects with URL and isMain flag
    specifications = Column(JSON)  # Stores specifications as key-value pairs
    requires_prescription = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    weight = Column(Float, nullable=True)
    dimensions = Column(JSON, nullable=True)  # Stores length, width, height and unit
    tags = Column(JSON, nullable=True)  # Stores array of tag strings
    reorder_level = Column(Integer, nullable=True)
    warranty_period = Column(Integer, nullable=True)
    warranty_unit = Column(Enum(WarrantyUnit), nullable=True, default=WarrantyUnit.MONTHS)
    warranty_description = Column(Text, nullable=True)

    # Relationships
    category = relationship("Category", back_populates="products")
    inventory_transactions = relationship("InventoryTransaction", back_populates="product")
    supplier = relationship("Supplier", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    cart_items = relationship("CartItem", back_populates="product")
    flash_sales = relationship("FlashSale", secondary="flash_sale_products", back_populates="products")


    def __repr__(self):
        return f"<Product(id={self.id}, category_id={self.category_id}, supplier_id={self.supplier_id}, product_type={self.product_type})>"
