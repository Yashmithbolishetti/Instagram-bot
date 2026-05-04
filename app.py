import os
import requests
import threading
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN", "")
PAGE_ID = os.getenv("PAGE_ID", "")

def log(msg):
    print(str(msg))


# ================= VERIFY WEBHOOK =================
@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403


# ================= RECEIVE MESSAGES =================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json() or {}
    log(data)

    if data.get("object") == "instagram":
        for entry in data.get("entry", []):
            for event in entry.get("messaging", []):
                sender_id = event.get("sender", {}).get("id")
                message = event.get("message", {}).get("text")

                if sender_id and message:
                    threading.Thread(
                        target=handle_message,
                        args=(sender_id, message)
                    ).start()

    return "OK", 200


# ================= CHAT LOGIC =================
def handle_message(sender_id, message):
    msg = message.lower()

    # 1. FIRST MESSAGE FLOW
    if msg in ["hi", "hello", "hey"]:
        reply = "Hey 👋\nThanks for checking my page\nI’m documenting an 83-day comeback journey 🚀\nIf you're trying to improve something, type JOIN"

    # 2. JOIN FLOW
    elif "join" in msg:
        reply = "Respect 🤝\nWhat are you trying to fix right now?"

    # 3. STUDY / JEE RELATED
    elif "study" in msg or "jee" in msg:
        reply = "I was at 11 percentile once\nSlowly improved to 69\nStill working on it\nWhat’s your biggest struggle in studying?"

    # 4. DISCIPLINE / LIFE
    elif "discipline" in msg or "lazy" in msg:
        reply = "Same here earlier\nStarted fixing small habits daily\nNot perfect yet\nWhat’s one habit you want to fix?"

    # 5. DRY RESPONSE
    elif len(msg) < 5:
        reply = "Got you 😄\nAre you more into study, fitness or money goals?"

    # 6. NEGATIVE USERS
    elif "tired" in msg or "demotivated" in msg:
        reply = "I get that\nI was stuck too\nStarted small, didn’t rush\nWhat’s one thing you can improve this week?"

    # DEFAULT
    else:
        reply = "I get what you’re saying\nI’m also figuring things out daily\nWhat are you focusing on right now?"

    send_message(sender_id, reply)


# ================= SEND MESSAGE =================
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
        log(e)


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
