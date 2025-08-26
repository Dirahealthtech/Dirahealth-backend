from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base import Base
from .base import TimeStampMixin


class MpesaTransaction(Base, TimeStampMixin):
    __tablename__ = "mpesa_transactions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Transaction identifiers
    merchant_request_id = Column(String(50), nullable=True, index=True)
    checkout_request_id = Column(String(50), nullable=True, index=True)
    mpesa_receipt_number = Column(String(20), nullable=True, index=True, unique=True)
    
    # Transaction details
    phone_number = Column(String(15), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(20), nullable=False)  # MpesaTransactionType
    transaction_status = Column(String(20), default="pending")  # MpesaTransactionStatus
    
    # Order relationship
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    # STK Push details
    stk_callback_response = Column(Text, nullable=True)  # JSON response from callback
    result_code = Column(Integer, nullable=True)
    result_desc = Column(String(255), nullable=True)
    
    # Additional transaction metadata
    account_reference = Column(String(50), nullable=True)  # Order number or reference
    transaction_desc = Column(String(255), nullable=True)
    
    # Timestamps from M-Pesa
    transaction_date = Column(DateTime, nullable=True)
    
    # API response tracking
    api_request_id = Column(String(50), nullable=True)
    api_response = Column(Text, nullable=True)  # Full API response for debugging
    
    # Relationships
    order = relationship("Order", back_populates="mpesa_transactions")


class MpesaConfiguration(Base, TimeStampMixin):
    __tablename__ = "mpesa_configurations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Environment settings
    environment = Column(String(20), default="sandbox")  # sandbox or production
    
    # API Credentials
    consumer_key = Column(String(255), nullable=False)
    consumer_secret = Column(String(255), nullable=False)
    business_short_code = Column(String(10), nullable=False)
    lipa_na_mpesa_passkey = Column(Text, nullable=False)
    
    # Callback URLs
    callback_url = Column(String(255), nullable=False)
    confirmation_url = Column(String(255), nullable=True)
    validation_url = Column(String(255), nullable=True)
    
    # Business details
    business_name = Column(String(100), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Security
    initiator_name = Column(String(50), nullable=True)  # For B2C transactions
    security_credential = Column(Text, nullable=True)   # Encrypted initiator password


class MpesaCallback(Base, TimeStampMixin):
    __tablename__ = "mpesa_callbacks"

    id = Column(Integer, primary_key=True, index=True)
    
    # Reference to the original transaction
    merchant_request_id = Column(String(50), nullable=True, index=True)
    checkout_request_id = Column(String(50), nullable=True, index=True)
    
    # Callback data
    callback_data = Column(Text, nullable=False)  # Raw JSON callback data
    result_code = Column(Integer, nullable=True)
    result_desc = Column(String(255), nullable=True)
    
    # Processing status
    processed = Column(Boolean, default=False)
    processing_error = Column(Text, nullable=True)
    
    # Transaction details from callback
    mpesa_receipt_number = Column(String(20), nullable=True)
    transaction_date = Column(DateTime, nullable=True)
    phone_number = Column(String(15), nullable=True)
    amount = Column(Float, nullable=True)
