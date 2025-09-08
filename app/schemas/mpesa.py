from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any
from datetime import datetime

from ..enums import MpesaTransactionType, MpesaTransactionStatus, PaymentMethod


# STK Push (Lipa Na M-Pesa) Schemas
class MpesaSTKPushRequest(BaseModel):
    phone_number: str
    amount: float
    account_reference: Optional[str] = None
    transaction_desc: Optional[str] = "Payment for order"
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        """Validate and format Kenyan phone number"""
        # Remove any spaces or special characters
        phone = ''.join(filter(str.isdigit, v))
        
        # Handle different formats
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif phone.startswith('254'):
            phone = phone
        elif phone.startswith('+254'):
            phone = phone[1:]
        elif phone.startswith('7') or phone.startswith('1'):
            phone = '254' + phone
        else:
            raise ValueError('Invalid phone number format')
        
        if len(phone) != 12 or not phone.startswith('254'):
            raise ValueError('Phone number must be a valid Kenyan number')
        
        return phone
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Validate amount is positive and reasonable"""
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        if v > 70000:  # M-Pesa daily limit
            raise ValueError('Amount exceeds M-Pesa daily limit')
        return round(v, 2)


class MpesaSTKPushResponse(BaseModel):
    merchant_request_id: str
    checkout_request_id: str
    response_code: str
    response_description: str
    customer_message: str


class MpesaQueryRequest(BaseModel):
    checkout_request_id: str


    


# Callback Schemas
class MpesaCallbackResponse(BaseModel):
    merchant_request_id: str
    checkout_request_id: str
    result_code: int
    result_desc: str
    callback_metadata: Optional[Dict[str, Any]] = None


class MpesaCallbackItem(BaseModel):
    name: str
    value: Optional[str] = None


class MpesaCallbackMetadata(BaseModel):
    item: list[MpesaCallbackItem]


class MpesaSTKCallback(BaseModel):
    merchant_request_id: str
    checkout_request_id: str
    result_code: int
    result_desc: str
    callback_metadata: Optional[MpesaCallbackMetadata] = None


# Transaction Tracking Schemas
class MpesaTransactionResponse(BaseModel):
    id: int
    merchant_request_id: Optional[str]
    checkout_request_id: Optional[str]
    mpesa_receipt_number: Optional[str]
    phone_number: str
    amount: float
    transaction_type: MpesaTransactionType
    transaction_status: MpesaTransactionStatus
    order_id: Optional[int]
    account_reference: Optional[str]
    transaction_desc: Optional[str]
    result_code: Optional[int]
    result_desc: Optional[str]
    transaction_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MpesaTransactionCreate(BaseModel):
    phone_number: str
    amount: float
    transaction_type: MpesaTransactionType
    order_id: Optional[int] = None
    account_reference: Optional[str] = None
    transaction_desc: Optional[str] = None


class MpesaTransactionUpdate(BaseModel):
    merchant_request_id: Optional[str] = None
    checkout_request_id: Optional[str] = None
    mpesa_receipt_number: Optional[str] = None
    transaction_status: Optional[MpesaTransactionStatus] = None
    result_code: Optional[int] = None
    result_desc: Optional[str] = None
    stk_callback_response: Optional[str] = None
    transaction_date: Optional[datetime] = None


# Configuration Schemas
class MpesaConfigurationCreate(BaseModel):
    environment: str = "sandbox"
    consumer_key: str
    consumer_secret: str
    business_short_code: str
    lipa_na_mpesa_passkey: str
    callback_url: str
    business_name: str
    confirmation_url: Optional[str] = None
    validation_url: Optional[str] = None
    initiator_name: Optional[str] = None
    security_credential: Optional[str] = None


class MpesaConfigurationResponse(BaseModel):
    id: int
    environment: str
    business_short_code: str
    callback_url: str
    business_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Payment Processing Schemas
class PaymentRequest(BaseModel):
    order_id: int
    payment_method: PaymentMethod
    phone_number: Optional[str] = None  # Required for M-Pesa
    amount: Optional[float] = None  # If different from order total


class PaymentResponse(BaseModel):
    success: bool
    message: str
    payment_method: PaymentMethod
    transaction_id: Optional[str] = None
    checkout_request_id: Optional[str] = None
    amount: float
    additional_data: Optional[Dict[str, Any]] = None


# Transaction Status Check
class TransactionStatusRequest(BaseModel):
    checkout_request_id: Optional[str] = None
    transaction_id: Optional[int] = None


class TransactionStatusResponse(BaseModel):
    transaction_id: int
    status: MpesaTransactionStatus
    mpesa_receipt_number: Optional[str]
    amount: float
    phone_number: str
    transaction_date: Optional[datetime]
    result_desc: Optional[str]
