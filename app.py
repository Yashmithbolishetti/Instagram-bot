import os
import json
import requests
import threading
from flask import Flask, request
from database import SessionLocal, UserTask, init_db

app = Flask(__name__)

# Load environment variables safely
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "")
MANUS_API_KEY = os.getenv("MANUS_API_KEY", "")
MANUS_PROJECT_ID = os.getenv("MANUS_PROJECT_ID", "")
PAGE_ID = os.getenv("PAGE_ID", "")
PUBLIC_URL = os.getenv("PUBLIC_URL", "")

MANUS_API_BASE_URL = "https://api.manus.ai/v2"

# Init DB
init_db()

def log(msg):
    print(str(msg))


# ===================== WEBHOOK VERIFY =====================
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


# ===================== INSTAGRAM WEBHOOK =====================
@app.route("/webhook", methods=["POST"])
def instagram_webhook():
    data = request.get_json() or {}
    log(data)

    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                message = event.get("message", {})
                sender_id = event.get("sender", {}).get("id")

                if sender_id and message.get("text"):
                    threading.Thread(
                        target=handle_message,
                        args=(sender_id, message["text"])
                    ).start()

    return "OK", 200


# ===================== HANDLE MESSAGE =====================
def handle_message(sender_id, text):
    session = SessionLocal()

    try:
        user = session.query(UserTask).filter_by(
            instagram_sender_id=sender_id
        ).first()

        headers = {
            "x-manus-api-key": MANUS_API_KEY,
            "Content-Type": "application/json"
        }

        # CREATE NEW TASK
        if not user:
            response = requests.post(
                f"{MANUS_API_BASE_URL}/task.create",
                headers=headers,
                json={
                    "project_id": MANUS_PROJECT_ID,
                    "message": {
                        "content": [{"type": "text", "text": text}]
                    }
                }
            )
            response.raise_for_status()

            task_id = response.json().get("task_id")

            new_user = UserTask(
                instagram_sender_id=sender_id,
                manus_task_id=task_id
            )
            session.add(new_user)
            session.commit()

            register_manus_webhook(task_id)

        # EXISTING USER
        else:
            requests.post(
                f"{MANUS_API_BASE_URL}/task.sendMessage",
                headers=headers,
                json={
                    "task_id": user.manus_task_id,
                    "message": {
                        "content": [{"type": "text", "text": text}]
                    }
                }
            )

    except Exception as e:
        log(f"ERROR: {e}")
        send_message(sender_id, "Something went wrong. Try again.")

    finally:
        session.close()


# ===================== MANUS WEBHOOK =====================
@app.route("/manus_webhook", methods=["POST"])
def manus_webhook():
    data = request.get_json() or {}
    log(data)

    if data.get("type") == "assistant_message":
        task_id = data.get("task_id")

        session = SessionLocal()
        user = session.query(UserTask).filter_by(
            manus_task_id=task_id
        ).first()
        session.close()

        if user:
            for content in data.get("assistant_message", {}).get("content", []):
                if content.get("type") == "text":
                    send_message(user.instagram_sender_id, content.get("text"))

    return "OK", 200


# ===================== REGISTER MANUS WEBHOOK =====================
def register_manus_webhook(task_id):
    if not PUBLIC_URL:
        return

    try:
        requests.post(
            f"{MANUS_API_BASE_URL}/webhook.create",
            headers={
                "x-manus-api-key": MANUS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "task_id": task_id,
                "event_types": ["assistant_message"],
                "url": f"{PUBLIC_URL}/manus_webhook"
            }
        )
    except Exception as e:
        log(f"Webhook error: {e}")


# ===================== SEND MESSAGE =====================
def send_message(recipient_id, text):
    try:
        requests.post(
            f"https://graph.facebook.com/v19.0/{PAGE_ID}/messages",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text}
            }
        )
    except Exception as e:
        log(f"Send error: {e}")


# ===================== RUN =====================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
