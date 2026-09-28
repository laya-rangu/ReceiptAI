from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Cents = Annotated[int, Field(strict=True, ge=0, le=100_000_000)]
Category = Literal["Groceries", "Food & drink", "Shopping", "Transport", "Health", "Other"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ItemInput(StrictModel):
    raw_name: str = Field(min_length=1, max_length=300)
    normalized_name: str = Field(min_length=1, max_length=300)
    quantity: Decimal = Field(gt=0, le=10000, decimal_places=3)
    line_total_cents: Cents
    category: Category = "Other"


class ReceiptDraft(StrictModel):
    merchant_name: str = Field(min_length=1, max_length=200)
    purchased_at: date
    currency: Literal["USD"] = "USD"
    items: list[ItemInput] = Field(min_length=1, max_length=200)
    subtotal_cents: Cents
    discount_cents: Cents = 0
    tax_cents: Cents = 0
    fees_cents: Cents = 0
    total_cents: Cents
    tax_included: bool = False
    category: Category = "Other"
    notes: str = Field(default="", max_length=2000)


class LoginInput(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_format(cls, value):
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Enter a valid email address")
        return value.lower()


class RegisterInput(LoginInput):
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=10, max_length=128)


class BasketItem(StrictModel):
    product_id: str
    quantity: int = Field(strict=True, ge=1, le=100)


class SaleInput(StrictModel):
    items: list[BasketItem] = Field(min_length=1, max_length=50)


class ClaimInput(StrictModel):
    token: str = Field(min_length=20, max_length=200)


class ConfirmInput(StrictModel):
    acknowledge_duplicate: bool = False


class ChatInput(StrictModel):
    message: str = Field(min_length=1, max_length=1000)
