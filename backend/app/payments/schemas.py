from pydantic import BaseModel, Field


class MockPaymentWebhook(BaseModel):
    payment_reference: str = Field(min_length=1)
    status: str = Field(default="paid")
    provider: str = Field(default="mock")


class PaymentWebhookResponse(BaseModel):
    status: str
    order_id: str | None = None
    payment_reference: str | None = None
