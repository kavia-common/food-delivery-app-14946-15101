from datetime import datetime, timezone
import uuid
from typing import Dict, Optional, Literal

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field

# FastAPI app with metadata matching project requirements and OpenAPI docs
app = FastAPI(
    title="Payment Service API",
    description="Handles payment intents, confirmation callbacks, refunds, and status.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Payments", "description": "Operations related to payment intents and status"},
    ],
)


# In-memory storage for payment intents (MVP only).
# Key: payment intent id, Value: PaymentIntent record
PAYMENT_STORE: Dict[str, Dict] = {}


class PaymentMethod(str):
    """Supported payment methods."""
    CARD = "card"
    WALLET = "wallet"
    UPI = "upi"
    COD = "cod"


class PaymentStatus(str):
    """Payment status enum mirroring the OpenAPI spec."""
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# PUBLIC_INTERFACE
class CreatePaymentIntentRequest(BaseModel):
    """Request model for creating a payment intent."""
    orderId: str = Field(..., description="Associated order ID")
    method: Literal["card", "wallet", "upi", "cod"] = Field(
        ..., description="Payment method to be used"
    )
    amount: Optional[float] = Field( # Not in spec required, but useful for MVP
        None, description="Optional order amount for the intent"
    )
    currency: Optional[str] = Field(
        "INR", description="Optional currency code, defaults to INR"
    )


# PUBLIC_INTERFACE
class PaymentIntent(BaseModel):
    """PaymentIntent response model aligned with the OpenAPI schema."""
    id: str = Field(..., description="Payment intent ID")
    orderId: str = Field(..., description="Associated order ID")
    amount: float = Field(..., description="Order amount")
    currency: str = Field(..., description="Currency code")
    status: Literal[
        "requires_payment_method",
        "requires_confirmation",
        "processing",
        "succeeded",
        "failed",
        "cancelled",
        "refunded",
    ] = Field(..., description="Current payment status")
    provider: Optional[str] = Field(None, description="Mock provider name")
    clientSecret: Optional[str] = Field(None, description="Client secret for client-side SDKs")
    createdAt: datetime = Field(..., description="Creation timestamp")
    updatedAt: datetime = Field(..., description="Last update timestamp")


# PUBLIC_INTERFACE
class WebhookEvent(BaseModel):
    """Model for simulated payment gateway webhook."""
    type: Literal[
        "payment_intent.succeeded",
        "payment_intent.failed",
        "payment_intent.processing",
        "payment_intent.canceled",
        "payment_intent.refunded",
    ] = Field(..., description="Type of the webhook event")
    paymentId: str = Field(..., description="Target payment ID")
    orderId: Optional[str] = Field(None, description="Associated order ID (optional mirror)")
    metadata: Optional[dict] = Field(None, description="Additional details if any")


def _now() -> datetime:
    """Utility to get current UTC datetime."""
    return datetime.now(timezone.utc)


def _default_amount() -> float:
    """Default mock amount for intents when not provided."""
    return 100.0


# PUBLIC_INTERFACE
@app.post(
    "/payments/intent",
    response_model=PaymentIntent,
    status_code=201,
    tags=["Payments"],
    summary="Create payment intent for an order",
)
def create_payment_intent(payload: CreatePaymentIntentRequest):
    """
    Create a payment intent for an order.
    - Body: orderId (str), method (card|wallet|upi|cod), amount (optional), currency (optional)
    - Returns: PaymentIntent with a mock clientSecret for client-side confirmation.
    """
    intent_id = str(uuid.uuid4())
    created_at = _now()
    amount = payload.amount if payload.amount is not None else _default_amount()
    currency = payload.currency or "INR"

    # For this MVP, we use a simple mock provider and client_secret
    provider = "mockpay"
    client_secret = f"pi_{intent_id}_secret_{uuid.uuid4().hex[:16]}"

    record = {
        "id": intent_id,
        "orderId": payload.orderId,
        "amount": float(amount),
        "currency": currency,
        "status": PaymentStatus.REQUIRES_CONFIRMATION,
        "provider": provider,
        "clientSecret": client_secret,
        "createdAt": created_at,
        "updatedAt": created_at,
    }

    PAYMENT_STORE[intent_id] = record
    return PaymentIntent(**record)


# PUBLIC_INTERFACE
@app.get(
    "/payments/{paymentId}",
    response_model=PaymentIntent,
    tags=["Payments"],
    summary="Get payment status",
)
def get_payment(paymentId: str):
    """
    Retrieve a payment intent by ID.
    - Path: paymentId (str)
    - Returns: PaymentIntent
    - 404 if not found
    """
    record = PAYMENT_STORE.get(paymentId)
    if not record:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentIntent(**record)


# PUBLIC_INTERFACE
@app.post(
    "/payments/webhook",
    tags=["Payments"],
    summary="Simulate payment gateway webhook",
)
def payment_webhook(event: WebhookEvent):
    """
    Simulate a payment gateway webhook event to update payment status.
    - Body: type (event type), paymentId (target payment intent), optional orderId/metadata
    - Returns: Updated PaymentIntent
    Notes:
      - In production, this route would verify signatures and security headers.
      - Here it simply maps the event type to a new status for the stored intent.
    """
    record = PAYMENT_STORE.get(event.paymentId)
    if not record:
        raise HTTPException(status_code=404, detail="Payment not found")

    status_map = {
        "payment_intent.succeeded": PaymentStatus.SUCCEEDED,
        "payment_intent.failed": PaymentStatus.FAILED,
        "payment_intent.processing": PaymentStatus.PROCESSING,
        "payment_intent.canceled": PaymentStatus.CANCELLED,
        "payment_intent.refunded": PaymentStatus.REFUNDED,
    }

    new_status = status_map.get(event.type)
    if not new_status:
        raise HTTPException(status_code=400, detail="Unsupported event type")

    record["status"] = new_status
    record["updatedAt"] = _now()
    # Potential place to notify OrderService of payment status change.
    # For MVP, we just update the in-memory store.

    PAYMENT_STORE[event.paymentId] = record
    return PaymentIntent(**record)


@app.get("/", include_in_schema=False)
def health():
    """Simple health endpoint for container readiness checks."""
    return {"status": "ok", "service": "PaymentService"}
