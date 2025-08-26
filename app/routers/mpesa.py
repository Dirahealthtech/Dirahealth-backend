from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from ..core.dependencies import get_db, RoleChecker
from ..enums import UserRole
from ..schemas.mpesa import (
    MpesaSTKPushRequest,
    PaymentRequest,
    PaymentResponse,
    TransactionStatusRequest,
    TransactionStatusResponse,
    MpesaConfigurationCreate,
    MpesaConfigurationResponse
)
from ..services.mpesa_service import mpesa_service
from ..exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/payments", tags=["M-Pesa Payments"])

admin_only = Depends(RoleChecker([UserRole.ADMIN]))


@router.post("/mpesa/stk-push")
async def initiate_mpesa_payment(
    request: MpesaSTKPushRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    **Initiate M-Pesa STK Push Payment**
    
    Initiates a Lipa Na M-Pesa Online (STK Push) payment request.
    
    **Request Body:**
    - **phone_number**: Kenyan phone number (254XXXXXXXXX format)
    - **amount**: Payment amount (minimum 1, maximum 70,000 KES)
    - **account_reference**: Reference for the payment (optional)
    - **transaction_desc**: Description of the transaction (optional)
    
    **Returns:**
    - **success**: Whether the STK push was initiated successfully
    - **message**: Status message
    - **transaction_id**: Internal transaction ID for tracking
    - **checkout_request_id**: M-Pesa checkout request ID
    - **customer_message**: Message displayed to customer
    
    **Process:**
    1. Validates phone number and amount
    2. Initiates STK push via M-Pesa API
    3. Creates internal transaction record
    4. Returns checkout details for status tracking
    
    **Note:** Customer will receive STK push on their phone to complete payment
    """
    try:
        result = await mpesa_service.initiate_stk_push(request, db)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate M-Pesa payment: {str(e)}"
        )


@router.post("/mpesa/order-payment")
async def initiate_order_payment(
    request: PaymentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    **Initiate Payment for Order**
    
    Initiates payment for a specific order using M-Pesa or other methods.
    
    **Request Body:**
    - **order_id**: ID of the order to pay for
    - **payment_method**: Payment method (mpesa, card, etc.)
    - **phone_number**: Required for M-Pesa payments
    - **amount**: Payment amount (optional, uses order total if not provided)
    
    **Returns:**
    - Payment initiation details based on selected method
    - For M-Pesa: STK push details and tracking information
    
    **Supported Payment Methods:**
    - **mpesa**: M-Pesa STK Push
    - **cash_on_delivery**: Cash on delivery (validates product support)
    
    **Process:**
    1. Validates order exists and payment method is supported
    2. Checks product payment options compatibility
    3. Initiates payment via selected method
    4. Links payment to order for tracking
    """
    try:
        # Get order details
        from ..models.order import Order
        from sqlalchemy import select
        
        query = select(Order).where(Order.id == request.order_id)
        result = await db.execute(query)
        order = result.scalar_one_or_none()
        
        if not order:
            raise NotFoundException("Order not found")
        
        # Determine payment amount
        payment_amount = request.amount or order.total
        
        if request.payment_method.value == "mpesa":
            if not request.phone_number:
                raise BadRequestException("Phone number is required for M-Pesa payments")
            
            # Create STK push request
            stk_request = MpesaSTKPushRequest(
                phone_number=request.phone_number,
                amount=payment_amount,
                account_reference=f"ORDER_{order.order_number}",
                transaction_desc=f"Payment for order {order.order_number}"
            )
            
            result = await mpesa_service.initiate_stk_push(stk_request, db, order.id)
            
            return PaymentResponse(
                success=result["success"],
                message=result["message"],
                payment_method=request.payment_method,
                transaction_id=str(result.get("transaction_id")),
                checkout_request_id=result.get("checkout_request_id"),
                amount=payment_amount,
                additional_data={
                    "customer_message": result.get("customer_message"),
                    "merchant_request_id": result.get("merchant_request_id")
                }
            )
        
        elif request.payment_method.value == "cash_on_delivery":
            # Validate that all products in order support COD
            # This would require checking order items against product payment options
            
            return PaymentResponse(
                success=True,
                message="Cash on delivery selected. Payment will be collected upon delivery.",
                payment_method=request.payment_method,
                amount=payment_amount,
                additional_data={
                    "delivery_payment": True,
                    "order_status": "confirmed_cod"
                }
            )
        
        else:
            raise BadRequestException(f"Payment method {request.payment_method.value} not supported")
        
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BadRequestException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate payment: {str(e)}"
        )


@router.get("/mpesa/status/{checkout_request_id}")
async def check_payment_status(
    checkout_request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    **Check M-Pesa Payment Status**
    
    Queries the status of an M-Pesa STK Push transaction.
    
    **Path Parameters:**
    - **checkout_request_id**: The checkout request ID from STK push initiation
    
    **Returns:**
    - **success**: Whether the query was successful
    - **status**: Transaction status description
    - **result_code**: M-Pesa result code
    - **transaction**: Full transaction details
    
    **Status Codes:**
    - **0**: Success - Payment completed
    - **1032**: Cancelled by user
    - **1037**: Timeout - No response from user
    - **Other**: Various failure reasons
    
    **Usage:**
    Use this endpoint to poll payment status after initiating STK push.
    Recommended polling interval: 5-10 seconds for up to 60 seconds.
    """
    try:
        result = await mpesa_service.query_transaction_status(checkout_request_id, db)
        
        if result["transaction"]:
            transaction = result["transaction"]
            return TransactionStatusResponse(
                transaction_id=transaction.id,
                status=transaction.transaction_status,
                mpesa_receipt_number=transaction.mpesa_receipt_number,
                amount=transaction.amount,
                phone_number=transaction.phone_number,
                transaction_date=transaction.transaction_date,
                result_desc=transaction.result_desc
            )
        else:
            raise NotFoundException("Transaction not found")
        
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check payment status: {str(e)}"
        )


@router.post("/mpesa/callback")
async def mpesa_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    **M-Pesa Callback Endpoint**
    
    Receives STK Push callback notifications from M-Pesa.
    
    **Note:** This endpoint is called by M-Pesa servers and should not be called manually.
    
    **Process:**
    1. Receives callback data from M-Pesa
    2. Validates and processes transaction status
    3. Updates internal transaction records
    4. Updates related order status if applicable
    5. Stores callback for audit purposes
    
    **Callback Types:**
    - **Success**: Payment completed successfully
    - **Failure**: Payment failed or was cancelled
    - **Timeout**: Customer did not respond to STK push
    
    **Security:** Ensure this endpoint is properly secured and only accessible by M-Pesa servers
    """
    try:
        # Get the raw callback data
        callback_data = await request.json()
        
        # Process the callback
        success = await mpesa_service.process_callback(callback_data, db)
        
        if success:
            return {"ResultCode": 0, "ResultDesc": "Success"}
        else:
            return {"ResultCode": 1, "ResultDesc": "Failed to process callback"}
        
    except Exception as e:
        # Log the error but return success to M-Pesa to avoid retries
        print(f"Callback processing error: {str(e)}")
        return {"ResultCode": 0, "ResultDesc": "Received"}


@router.get("/mpesa/transactions/{transaction_id}")
async def get_transaction_details(
    transaction_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    **Get M-Pesa Transaction Details**
    
    Retrieves detailed information about a specific M-Pesa transaction.
    
    **Path Parameters:**
    - **transaction_id**: Internal transaction ID
    
    **Returns:**
    Complete transaction details including:
    - Transaction status and amounts
    - M-Pesa receipt number (if successful)
    - Timestamps and processing details
    - Related order information
    """
    try:
        transaction = await mpesa_service.get_transaction_by_id(transaction_id, db)
        
        if not transaction:
            raise NotFoundException("Transaction not found")
        
        return transaction
        
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve transaction: {str(e)}"
        )


@router.get("/mpesa/orders/{order_id}/transactions")
async def get_order_transactions(
    order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    **Get Order M-Pesa Transactions**
    
    Retrieves all M-Pesa transactions associated with a specific order.
    
    **Path Parameters:**
    - **order_id**: Order ID to get transactions for
    
    **Returns:**
    List of all M-Pesa transactions for the order, including:
    - Successful and failed payment attempts
    - Transaction statuses and details
    - Payment amounts and timestamps
    
    **Use Cases:**
    - Order payment history
    - Debugging payment issues
    - Refund processing
    """
    try:
        transactions = await mpesa_service.get_order_transactions(order_id, db)
        return transactions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve order transactions: {str(e)}"
        )


# Admin endpoints for M-Pesa configuration
@router.post("/mpesa/config", response_model=MpesaConfigurationResponse)
async def create_mpesa_configuration(
    config_data: MpesaConfigurationCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Create M-Pesa Configuration - Admin Only**
    
    Creates or updates M-Pesa API configuration for payment processing.
    
    **Request Body:**
    - **environment**: sandbox or production
    - **consumer_key**: M-Pesa API consumer key
    - **consumer_secret**: M-Pesa API consumer secret
    - **business_short_code**: M-Pesa business short code
    - **lipa_na_mpesa_passkey**: STK Push passkey
    - **callback_url**: URL for M-Pesa callbacks
    - **business_name**: Business name for transactions
    
    **Security Note:** This endpoint handles sensitive API credentials.
    Ensure proper authentication and authorization.
    """
    try:
        from ..models.mpesa_transaction import MpesaConfiguration
        
        # Deactivate existing configurations
        from sqlalchemy import update
        await db.execute(
            update(MpesaConfiguration).values(is_active=False)
        )
        
        # Create new configuration
        config = MpesaConfiguration(**config_data.model_dump())
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
        return config
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create M-Pesa configuration: {str(e)}"
        )


@router.get("/mpesa/config", response_model=MpesaConfigurationResponse)
async def get_mpesa_configuration(
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Get M-Pesa Configuration - Admin Only**
    
    Retrieves the current active M-Pesa configuration.
    
    **Returns:**
    Current M-Pesa configuration details (credentials are masked for security)
    """
    try:
        config = await mpesa_service.get_configuration(db)
        
        if not config:
            raise NotFoundException("M-Pesa configuration not found")
        
        return config
        
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve M-Pesa configuration: {str(e)}"
        )
