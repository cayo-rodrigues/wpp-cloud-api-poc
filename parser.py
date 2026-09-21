from typing import Literal, Optional

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field

client = AsyncAnthropic()

SYSTEM = """
You extract structured data from unstructured text. Given raw text input:

1. Read the schema first. Note required vs optional fields, enums, and format constraints (dates, currencies, IDs). The schema is the contract — never emit a key it doesn't define.
2. Scan the input for each field. Prefer explicit values over inferred ones. If a required field is genuinely absent, use null rather than guessing.
3. Normalize as you extract: trim whitespace, coerce dates to ISO 8601, strip currency symbols into numeric + code, collapse enum synonyms to their canonical value.
4. Call the `extract` tool exactly once with the extracted fields.

When the input is ambiguous, pick the most conservative interpretation.
"""


class CouldNotParseOrderErr(BaseException): ...


class OrderItem(BaseModel):
    item_name: str
    item_quantity: Optional[int | None]


class DeliveryOrder(BaseModel):
    name: Optional[str | None]
    phone: Optional[str | None]
    address: Optional[str | None]
    payment_method: Optional[
        Literal["cash", "credit_card", "debit_card", "pix", "other", None]
    ] = Field(
        description="Canonical payment method, or 'other' if stated but not one of the known values."
    )
    payment_method_other: Optional[str] = Field(
        description="The payment method as stated by the user, verbatim, only when payment_method is 'other'. Otherwise null."
    )
    orders: list[OrderItem]


PAYMENT_METHOD_LABELS = {
    "cash": "Cash",
    "credit_card": "Credit card",
    "debit_card": "Debit card",
    "pix": "Pix",
    "other": "Other",
}

NOT_PROVIDED = "Not provided"


def format_order(order: DeliveryOrder) -> str:
    payment = (
        order.payment_method_other
        or PAYMENT_METHOD_LABELS.get(order.payment_method or "")
        or NOT_PROVIDED
    )
    lines = [
        f"Name: {order.name or NOT_PROVIDED}",
        f"Phone: {order.phone or NOT_PROVIDED}",
        f"Address: {order.address or NOT_PROVIDED}",
        f"Payment method: {payment}",
        "",
        "Items:",
    ]
    for item in order.orders:
        if item.item_quantity is not None:
            lines.append(f"- {item.item_quantity}x {item.item_name}")
        else:
            lines.append(f"- {item.item_name} (quantity not specified)")
    return "\n".join(lines)


async def parse_nl_order(nl_input: str):
    message = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        cache_control={"type": "ephemeral"},
        system=SYSTEM,
        tools=[
            {
                "name": "extract",
                "description": "Record the structured delivery order extracted from the input text.",
                "input_schema": DeliveryOrder.model_json_schema(),
            }
        ],
        tool_choice={"type": "tool", "name": "extract"},
        messages=[
            {
                "role": "user",
                "content": nl_input,
            }
        ],
    )

    for block in message.content:
        if block.type == "tool_use" and block.name == "extract":
            return DeliveryOrder.model_validate(block.input)

    raise CouldNotParseOrderErr
