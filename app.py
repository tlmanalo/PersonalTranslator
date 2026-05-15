import os
import anthropic
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

configuration = Configuration(access_token=os.environ["CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])
anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

YOUR_USER_ID = "U4b03989bc76d4027dae55df0f6ba536a"

SYSTEM_PROMPT_TO_ENGLISH = """You are a translation assistant. Translate the user's text to English.
Reply with ONLY the translated text. Do not include explanations, labels, or any other text."""

SYSTEM_PROMPT_TO_THAI = """You are a translation assistant. Translate the user's text to Thai.
Reply with ONLY the translated text. Do not include explanations, labels, or any other text."""


@app.route("/health", methods=["GET"])
def health():
    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    source = event.source
    user_text = event.message.text

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        if source.type == "group":
            # Ignore messages sent by yourself in groups
            if source.user_id == YOUR_USER_ID:
                return

            # Translate others' messages to English and push privately
            display_name = "Unknown User"
            try:
                profile = line_bot_api.get_group_member_profile(source.group_id, source.user_id)
                display_name = profile.display_name
            except Exception:
                pass

            try:
                translated = translate_text(user_text, SYSTEM_PROMPT_TO_ENGLISH)
                private_msg = f"👤 {display_name}\n🌐 Translation:\n\n{translated}"
            except Exception:
                private_msg = f"👤 {display_name}\nTranslation error. Please try again."

            line_bot_api.push_message(
                PushMessageRequest(
                    to=YOUR_USER_ID,
                    messages=[TextMessage(text=private_msg)],
                )
            )

        elif source.type == "user" and source.user_id == YOUR_USER_ID:
            # Translate your private messages to Thai and reply in chat
            try:
                translated = translate_text(user_text, SYSTEM_PROMPT_TO_THAI)
                reply_msg = f"🇹🇭 Thai:\n\n{translated}"
            except Exception:
                reply_msg = "Translation error. / เกิดข้อผิดพลาดในการแปล"

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_msg)],
                )
            )


def translate_text(text: str, system_prompt: str) -> str:
    response = anthropic_client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": text}],
    )
    return response.content[0].text


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
