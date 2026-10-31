"""Instagram comment -> auto DM bot (official Instagram API with Instagram Login).

When someone comments one of DM_KEYWORDS on your post/reel, the bot:
  1. sends them a private DM (Instagram "private reply" to the comment), and
  2. optionally replies publicly to the comment ("Check your DM!").

Configure via environment variables (see .env.example). Run locally with
`python3 app.py` or in production with `gunicorn app:app`.
"""

import hashlib
import hmac
import logging
import os
from collections import OrderedDict

import requests
from flask import Flask, abort, request

GRAPH = "https://graph.instagram.com/v21.0"

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "")
APP_SECRET = os.environ.get("APP_SECRET", "")
ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "")
KEYWORDS = [k.strip().lower() for k in os.environ.get("DM_KEYWORDS", "link").split(",") if k.strip()]
DM_MESSAGE = os.environ.get("DM_MESSAGE", "Hi {username}! Ye raha aapka link: https://example.com")
PUBLIC_REPLY = os.environ.get("PUBLIC_REPLY", "Check your DM {username} \U0001F4E9")
# Comma-separated media IDs to watch; empty means every post/reel.
MEDIA_IDS = {m.strip() for m in os.environ.get("MEDIA_IDS", "").split(",") if m.strip()}

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = app.logger

# Instagram retries webhooks, so remember recent comment IDs to avoid double DMs.
_seen = OrderedDict()


def already_handled(comment_id):
    if comment_id in _seen:
        return True
    _seen[comment_id] = True
    if len(_seen) > 5000:
        _seen.popitem(last=False)
    return False


def signature_ok(raw_body, header):
    if not APP_SECRET:
        log.warning("APP_SECRET not set; skipping signature check")
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


def matches_keyword(text):
    words = text.lower().replace("“", " ").replace("”", " ").split()
    cleaned = {w.strip(".,!?\"'#@") for w in words}
    return any(k in cleaned for k in KEYWORDS)


def send_private_reply(comment_id, text):
    resp = requests.post(
        f"{GRAPH}/{IG_USER_ID}/messages",
        json={"recipient": {"comment_id": comment_id}, "message": {"text": text}},
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        timeout=10,
    )
    if not resp.ok:
        log.error("DM failed for comment %s: %s", comment_id, resp.text)
    return resp.ok


def send_public_reply(comment_id, text):
    resp = requests.post(
        f"{GRAPH}/{comment_id}/replies",
        data={"message": text},
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        timeout=10,
    )
    if not resp.ok:
        log.error("Public reply failed for comment %s: %s", comment_id, resp.text)
    return resp.ok


def handle_comment(value):
    comment_id = value.get("id")
    text = value.get("text", "")
    sender = value.get("from", {})
    media_id = value.get("media", {}).get("id")
    username = sender.get("username", "")

    if not comment_id or sender.get("id") == IG_USER_ID:
        return  # ignore our own replies, otherwise we'd loop
    if MEDIA_IDS and media_id not in MEDIA_IDS:
        return
    if not matches_keyword(text):
        return
    if already_handled(comment_id):
        return

    log.info("Keyword comment from @%s on %s: %r", username, media_id, text)
    if send_private_reply(comment_id, DM_MESSAGE.format(username=username)) and PUBLIC_REPLY:
        send_public_reply(comment_id, PUBLIC_REPLY.format(username=f"@{username}" if username else ""))


@app.get("/webhook")
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge", ""), 200
    abort(403)


@app.post("/webhook")
def receive():
    if not signature_ok(request.get_data(), request.headers.get("X-Hub-Signature-256")):
        abort(403)
    payload = request.get_json(silent=True) or {}
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                handle_comment(change.get("value", {}))
    return "EVENT_RECEIVED", 200


@app.get("/")
def health():
    return {"ok": True, "keywords": KEYWORDS}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
