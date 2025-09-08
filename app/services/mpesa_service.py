import base64
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import asyncio
import httpx

from ..models.mpesa_transaction import MpesaTransaction, MpesaConfiguration, MpesaCallback
from ..models.order import Order
from ..schemas.mpesa import (
    MpesaSTKPushRequest,
    MpesaSTKPushResponse,
    MpesaTransactionCreate,
    MpesaTransactionUpdate,
    MpesaTransactionResponse,
    MpesaCallbackResponse,
    TransactionStatusResponse
)
from ..enums import MpesaTransactionType, MpesaTransactionStatus
from ..core.config import Settings


class MpesaConfig:
    """Configuration class for M-Pesa settings"""
    def __init__(self):
        self.environment = os.getenv("MPESA_ENVIRONMENT", "sandbox")
        self.consumer_key = os.getenv("MPESA_CONSUMER_KEY")
        self.consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")
        self.business_short_code = os.getenv("MPESA_BUSINESS_SHORT_CODE")
        self.lipa_na_mpesa_passkey = os.getenv("MPESA_PASSKEY")
        self.callback_url = os.getenv("MPESA_CALLBACK_URL")
        self.business_name = os.getenv("MPESA_BUSINESS_NAME", "Dira Healthcare")
        
        # Validate required fields
        required_fields = [
            self.consumer_key, self.consumer_secret, self.business_short_code,
            self.lipa_na_mpesa_passkey, self.callback_url
        ]
        
        if not all(required_fields):
            missing_fields = []
            if not self.consumer_key:
                missing_fields.append("MPESA_CONSUMER_KEY")
            if not self.consumer_secret:
                missing_fields.append("MPESA_CONSUMER_SECRET")
            if not self.business_short_code:
                missing_fields.append("MPESA_BUSINESS_SHORT_CODE")
            if not self.lipa_na_mpesa_passkey:
                missing_fields.append("MPESA_PASSKEY")
            if not self.callback_url:
                missing_fields.append("MPESA_CALLBACK_URL")
                
            raise ValueError(f"Missing required M-Pesa environment variables: {', '.join(missing_fields)}")


class MpesaService:
    def __init__(self):
        self.sandbox_base_url = "https://sandbox.safaricom.co.ke"
        self.production_base_url = "https://api.safaricom.co.ke"
        self._config = None
    
    @property
    def config(self):
        """Lazy load configuration"""
        if self._config is None:
            self._config = MpesaConfig()
        return self._config
    
    async def get_access_token(self) -> str:
        """Generate OAuth access token for M-Pesa API"""
        base_url = self.sandbox_base_url if self.config.environment == "sandbox" else self.production_base_url
        
        # Create credentials
        credentials = f"{self.config.consumer_key}:{self.config.consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
        
        url = f"{base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                
            if response.status_code == 200:
                token_data = response.json()
                return token_data["access_token"]
            else:
                raise Exception(f"Failed to get access token: {response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Network error getting access token: {str(e)}")
    
    async def generate_password(self) -> tuple[str, str]:
        """Generate timestamp and password for STK Push"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Password = Base64(BusinessShortCode + Passkey + Timestamp)
        password_string = f"{self.config.business_short_code}{self.config.lipa_na_mpesa_passkey}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        
        return timestamp, password
    
    def validate_phone_number(self, phone: str) -> str:
        """Ensure phone number is in correct format (254XXXXXXXXX)"""
        import re
        
        # Remove any spaces, dashes, or plus signs
        clean_phone = re.sub(r'[\s\-\+]', '', phone)
        
        # Convert 07XX to 2547XX format
        if clean_phone.startswith('07'):
            clean_phone = '254' + clean_phone[1:]
        elif clean_phone.startswith('7'):
            clean_phone = '254' + clean_phone
        elif not clean_phone.startswith('254'):
            raise ValueError("Invalid phone number format. Use format: 254XXXXXXXXX")
        
        # Validate length (should be 12 digits: 254XXXXXXXXX)
        if len(clean_phone) != 12:
            raise ValueError("Invalid phone number length. Should be 12 digits: 254XXXXXXXXX")
            
        return clean_phone
    
    async def initiate_stk_push(
        self, 
        request: MpesaSTKPushRequest, 
        db: AsyncSession,
        order_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Initiate STK Push (Lipa Na M-Pesa Online)"""
        
        try:
            # Validate phone number
            validated_phone = self.validate_phone_number(request.phone_number)
            
            # Get access token
            access_token = await self.get_access_token()
            
            # Generate timestamp and password
            timestamp, password = await self.generate_password()
            
            # Prepare API request
            base_url = self.sandbox_base_url if self.config.environment == "sandbox" else self.production_base_url
            url = f"{base_url}/mpesa/stkpush/v1/processrequest"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "BusinessShortCode": self.config.business_short_code,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(request.amount),  # M-Pesa expects integer
                "PartyA": validated_phone,
                "PartyB": self.config.business_short_code,
                "PhoneNumber": validated_phone,
                "CallBackURL": self.config.callback_url,
                "AccountReference": request.account_reference or f"ORDER_{order_id}" if order_id else "PAYMENT",
                "TransactionDesc": request.transaction_desc
            }
            
            # Create transaction record first
            transaction_data = MpesaTransactionCreate(
                phone_number=validated_phone,
                amount=request.amount,
                transaction_type=MpesaTransactionType.C2B,
                order_id=order_id,
                account_reference=request.account_reference,
                transaction_desc=request.transaction_desc
            )
            
            transaction = await self.create_transaction(transaction_data, db)
            
            # Make API request
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ResponseCode") == "0":
                # Update transaction with M-Pesa response
                update_data = MpesaTransactionUpdate(
                    merchant_request_id=response_data.get("MerchantRequestID"),
                    checkout_request_id=response_data.get("CheckoutRequestID"),
                    transaction_status=MpesaTransactionStatus.PENDING
                )
                
                await self.update_transaction(transaction.id, update_data, db)
                
                return {
                    "success": True,
                    "message": "STK Push initiated successfully",
                    "transaction_id": transaction.id,
                    "checkout_request_id": response_data.get("CheckoutRequestID"),
                    "merchant_request_id": response_data.get("MerchantRequestID"),
                    "customer_message": response_data.get("CustomerMessage", "Please enter your M-Pesa PIN to complete the payment")
                }
            else:
                # Update transaction as failed
                update_data = MpesaTransactionUpdate(
                    transaction_status=MpesaTransactionStatus.FAILED,
                    result_desc=response_data.get("ResponseDescription", "STK Push failed")
                )
                
                await self.update_transaction(transaction.id, update_data, db)
                
                return {
                    "success": False,
                    "message": response_data.get("ResponseDescription", "STK Push failed"),
                    "transaction_id": transaction.id,
                    "error_code": response_data.get("ResponseCode")
                }
                
        except ValueError as e:
            # Handle validation errors (like phone number format)
            return {
                "success": False,
                "message": str(e),
                "error_code": "VALIDATION_ERROR"
            }
        except Exception as e:
            # Handle other errors
            return {
                "success": False,
                "message": f"Failed to initiate STK Push: {str(e)}",
                "error_code": "SYSTEM_ERROR"
            }
    
    async def query_transaction_status(
        self, 
        checkout_request_id: str, 
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Query the status of an STK Push transaction"""
        
        try:
            access_token = await self.get_access_token()
            timestamp, password = await self.generate_password()
            
            base_url = self.sandbox_base_url if self.config.environment == "sandbox" else self.production_base_url
            url = f"{base_url}/mpesa/stkpushquery/v1/query"
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "BusinessShortCode": self.config.business_short_code,
                "Password": password,
                "Timestamp": timestamp,
                "CheckoutRequestID": checkout_request_id
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)
            
            response_data = response.json()
            
            # Update local transaction record
            transaction = await self.get_transaction_by_checkout_id(checkout_request_id, db)
            if transaction:
                if response_data.get("ResultCode") == "0":
                    status = MpesaTransactionStatus.SUCCESS
                elif response_data.get("ResultCode") == "1032":
                    status = MpesaTransactionStatus.CANCELLED
                elif response_data.get("ResultCode") == "1037":
                    status = MpesaTransactionStatus.TIMEOUT
                else:
                    status = MpesaTransactionStatus.FAILED
                
                update_data = MpesaTransactionUpdate(
                    transaction_status=status,
                    result_code=response_data.get("ResultCode"),
                    result_desc=response_data.get("ResultDesc")
                )
                
                await self.update_transaction(transaction.id, update_data, db)
            
            return {
                "success": response.status_code == 200,
                "status": response_data.get("ResultDesc"),
                "result_code": response_data.get("ResultCode"),
                "transaction": transaction
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to query transaction status: {str(e)}",
                "error_code": "SYSTEM_ERROR"
            }
    
    async def process_callback(
        self, 
        callback_data: Dict[str, Any], 
        db: AsyncSession
    ) -> bool:
        """Process M-Pesa STK Push callback"""
        
        callback_record = None
        
        try:
            # Extract callback information
            stk_callback = callback_data.get("Body", {}).get("stkCallback", {})
            
            merchant_request_id = stk_callback.get("MerchantRequestID")
            checkout_request_id = stk_callback.get("CheckoutRequestID")
            result_code = stk_callback.get("ResultCode")
            result_desc = stk_callback.get("ResultDesc")
            
            # Store raw callback for debugging
            callback_record = MpesaCallback(
                merchant_request_id=merchant_request_id,
                checkout_request_id=checkout_request_id,
                callback_data=json.dumps(callback_data),
                result_code=result_code,
                result_desc=result_desc
            )
            
            db.add(callback_record)
            
            # Find the transaction
            transaction = await self.get_transaction_by_checkout_id(checkout_request_id, db)
            
            if not transaction:
                callback_record.processing_error = "Transaction not found"
                await db.commit()
                return False
            
            # Process based on result code
            if result_code == 0:  # Success
                # Extract transaction details from callback metadata
                callback_metadata = stk_callback.get("CallbackMetadata", {})
                items = callback_metadata.get("Item", [])
                
                mpesa_receipt_number = None
                transaction_date = None
                phone_number = None
                amount = None
                
                for item in items:
                    name = item.get("Name")
                    value = item.get("Value")
                    
                    if name == "MpesaReceiptNumber":
                        mpesa_receipt_number = value
                    elif name == "TransactionDate":
                        if value:
                            transaction_date = datetime.strptime(str(value), "%Y%m%d%H%M%S")
                    elif name == "PhoneNumber":
                        phone_number = value
                    elif name == "Amount":
                        amount = float(value) if value else None
                
                # Update transaction
                update_data = MpesaTransactionUpdate(
                    transaction_status=MpesaTransactionStatus.SUCCESS,
                    mpesa_receipt_number=mpesa_receipt_number,
                    result_code=result_code,
                    result_desc=result_desc,
                    transaction_date=transaction_date,
                    stk_callback_response=json.dumps(callback_data)
                )
                
                await self.update_transaction(transaction.id, update_data, db)
                
                # Update order status if applicable
                if transaction.order_id:
                    await self._update_order_payment_status(transaction.order_id, True, db)
                
            else:  # Failed transaction
                update_data = MpesaTransactionUpdate(
                    transaction_status=MpesaTransactionStatus.FAILED,
                    result_code=result_code,
                    result_desc=result_desc,
                    stk_callback_response=json.dumps(callback_data)
                )
                
                await self.update_transaction(transaction.id, update_data, db)
                
                # Update order status if applicable
                if transaction.order_id:
                    await self._update_order_payment_status(transaction.order_id, False, db)
            
            callback_record.processed = True
            await db.commit()
            return True
            
        except Exception as e:
            if callback_record:
                callback_record.processing_error = str(e)
                await db.commit()
            return False
    
    async def create_transaction(
        self, 
        transaction_data: MpesaTransactionCreate, 
        db: AsyncSession
    ) -> MpesaTransaction:
        """Create a new M-Pesa transaction record"""
        
        transaction = MpesaTransaction(
            phone_number=transaction_data.phone_number,
            amount=transaction_data.amount,
            transaction_type=transaction_data.transaction_type.value,
            order_id=transaction_data.order_id,
            account_reference=transaction_data.account_reference,
            transaction_desc=transaction_data.transaction_desc,
            transaction_status=MpesaTransactionStatus.PENDING.value
        )
        
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)
        
        return transaction
    
    async def update_transaction(
        self, 
        transaction_id: int, 
        update_data: MpesaTransactionUpdate, 
        db: AsyncSession
    ) -> Optional[MpesaTransaction]:
        """Update an existing M-Pesa transaction"""
        
        query = select(MpesaTransaction).where(MpesaTransaction.id == transaction_id)
        result = await db.execute(query)
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return None
        
        # Update fields
        for field, value in update_data.model_dump(exclude_unset=True).items():
            if hasattr(transaction, field) and value is not None:
                setattr(transaction, field, value)
        
        await db.commit()
        await db.refresh(transaction)
        
        return transaction
    
    async def get_transaction_by_checkout_id(
        self, 
        checkout_request_id: str, 
        db: AsyncSession
    ) -> Optional[MpesaTransaction]:
        """Get transaction by checkout request ID"""
        
        query = select(MpesaTransaction).where(
            MpesaTransaction.checkout_request_id == checkout_request_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_transaction_by_id(
        self, 
        transaction_id: int, 
        db: AsyncSession
    ) -> Optional[MpesaTransaction]:
        """Get transaction by ID"""
        
        query = select(MpesaTransaction).where(MpesaTransaction.id == transaction_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_order_transactions(
        self, 
        order_id: int, 
        db: AsyncSession
    ) -> list[MpesaTransaction]:
        """Get all M-Pesa transactions for an order"""
        
        query = select(MpesaTransaction).where(MpesaTransaction.order_id == order_id)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def _update_order_payment_status(
        self, 
        order_id: int, 
        paid: bool, 
        db: AsyncSession
    ):
        """Update order payment status based on M-Pesa transaction"""
        
        query = select(Order).where(Order.id == order_id)
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        
        if order:
            if paid:
                # Update order status to confirmed/paid
                from ..enums import OrderStatus
                order.status = OrderStatus.CONFIRMED
            # Additional order status logic can be added here
            
            await db.commit()


# Create service instance
mpesa_service = MpesaService()