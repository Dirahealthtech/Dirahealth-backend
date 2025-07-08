from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship

from ..db.base import Base
from .base import TimeStampMixin


class FlashSale(Base, TimeStampMixin):
    """
    Represents a flash sale event in the system.
    
    Attributes:
        id (int): Primary key identifier for the flash sale.
        title (str): Title or name of the flash sale.
        start_time (datetime): The starting datetime of the flash sale.
        end_time (datetime): The ending datetime of the flash sale.
        discount_percentage (float): Discount percentage applied during the flash sale.
        products (List[Product]): List of products associated with this flash sale.

    """

    __tablename__ = "flash_sales"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    discount_percentage = Column(Float, nullable=False)

    # relationship
    products = relationship("Product", secondary="flash_sale_products", back_populates="flash_sales")


    def __repr__(self):
        return (
            f'<FlashSale(id={self.id}, title={self.title}, start_time={self.start_time},'
            f' end_time={self.end_time}, discount_percentage={self.discount_percentage})>'
        )


# Association table for many-to-many relationship between FlashSale and Product
flash_sale_products = Table(
    "flash_sale_products",
    Base.metadata,
    Column("flash_sale_id", ForeignKey("flash_sales.id"), primary_key=True),
    Column("product_id", ForeignKey("products.id"), primary_key=True),
)
