import os

import aiohttp

WHATSAPP_ACCESS_TOKEN = os.environ["WHATSAPP_ACCESS_TOKEN"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]

GRAPH_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"


async def _send(payload: dict) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            GRAPH_URL,
            headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"},
            json=payload,
        ) as response:
            response_body = await response.text()
            print(f"[whatsapp send] status={response.status} body={response_body}")
            response.raise_for_status()


async def send_text_message(to: str, body: str) -> None:
    await _send(
        {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
    )


async def send_confirmation_buttons(to: str, body: str) -> None:
    await _send(
        {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": "order_confirm", "title": "Confirm"},
                        },
                        {
                            "type": "reply",
                            "reply": {"id": "order_fix", "title": "Edit"},
                        },
                    ]
                },
            },
        }
    )
