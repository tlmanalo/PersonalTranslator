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
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

app = Flask(__name__)

configuration = Configuration(access_token=os.environ["CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])
anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

TARGET_USER_ID = "U4b03989bc76d4027dae55df0f6ba536a"

SYSTEM_PROMPT = """You are a translation assistant. Detect the language of the user's text.
- If the text is in English, translate it to Thai.
- If the text is in any other language (including Thai), translate it to English.
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
    user_text = event.message.text

    try:
        translated = translate_text(user_text)
        private_msg = f"🌐 Translation:\n\n{translated}"
    except Exception:
        private_msg = "Translation error. Please try again. / เกิดข้อผิดพลาดในการแปล กรุณาลองใหม่"

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=TARGET_USER_ID,
                messages=[TextMessage(text=private_msg)],
            )
        )


def translate_text(text: str) -> str:
    # System prompt is stable across all requests — cache it to save tokens
    response = anthropic_client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": text}],
    )
    return response.content[0].text


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
