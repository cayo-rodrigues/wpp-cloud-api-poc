import os
from parser import format_order, parse_nl_order

from fastapi import FastAPI, Request, Response, status

from whatsapp_api import send_confirmation_buttons, send_text_message

app = FastAPI()

WHATSAPP_VERIFY_TOKEN = os.environ["WHATSAPP_VERIFY_TOKEN"]


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN
    ):
        return Response(
            content=params.get("hub.challenge", ""), media_type="text/plain"
        )
    return Response(status_code=status.HTTP_403_FORBIDDEN)


@app.post("/webhook")
async def receive_webhook(request: Request):
    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            profile_name = ""

            for contact in value.get("contacts", []):
                profile_name = contact.get("profile", {}).get("name")

            for message in value.get("messages", []):
                wa_id = message["from"]

                if message.get("type") == "text":
                    await handle_text_msg(message, profile_name, wa_id)
                elif message.get("type") == "interactive":
                    await handle_interactive_msg(message, wa_id)

    return Response(status_code=status.HTTP_200_OK)


async def handle_text_msg(message: dict, profile_name: str, wa_id: str):
    text = message["text"]["body"]

    parsed_order = await parse_nl_order(
        nl_input=text
        + f"\n\nWhatsApp profile name: {profile_name}\nWhatsApp number: {wa_id}"
    )
    print(f"[{wa_id}] {text!r} -> {parsed_order}")

    await send_confirmation_buttons(
        to=wa_id,
        body="Please review and confirm your order:\n\n" + format_order(parsed_order),
    )


async def handle_interactive_msg(message: dict, wa_id: str):
    button_id = message["interactive"].get("button_reply", {}).get("id")

    if button_id == "order_confirm":
        print(f"[{wa_id}] order confirmed")
        await send_text_message(
            to=wa_id,
            body="Awesome! Your order is confirmed and we're getting it ready. 🎉",
        )
    elif button_id == "order_fix":
        print(f"[{wa_id}] customer requested changes")
        await send_text_message(
            to=wa_id,
            body="No problem! Just send me the corrected details.",
        )
