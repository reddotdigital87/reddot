import hashlib
import hmac
import json
import os
from unittest import mock

os.environ.update({
    "VERIFY_TOKEN": "tok",
    "APP_SECRET": "secret",
    "IG_ACCESS_TOKEN": "x",
    "IG_USER_ID": "999",
    "DM_KEYWORDS": "link,guide",
})

import app as bot  # noqa: E402


def signed_post(client, payload):
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    return client.post("/webhook", data=body, content_type="application/json",
                       headers={"X-Hub-Signature-256": sig})


def comment(cid, text, from_id="123"):
    return {"entry": [{"changes": [{"field": "comments", "value": {
        "id": cid, "text": text, "from": {"id": from_id, "username": "riya"},
        "media": {"id": "m1"}}}]}]}


def test_verify():
    c = bot.app.test_client()
    ok = c.get("/webhook?hub.mode=subscribe&hub.verify_token=tok&hub.challenge=42")
    assert ok.status_code == 200 and ok.data == b"42"
    assert c.get("/webhook?hub.mode=subscribe&hub.verify_token=bad&hub.challenge=42").status_code == 403


def test_bad_signature_rejected():
    c = bot.app.test_client()
    r = c.post("/webhook", json=comment("c0", "link"), headers={"X-Hub-Signature-256": "sha256=bad"})
    assert r.status_code == 403


def test_keyword_sends_dm_once_and_ignores_others():
    c = bot.app.test_client()
    with mock.patch.object(bot.requests, "post") as post:
        post.return_value.ok = True
        signed_post(c, comment("c1", "LINK please!"))
        signed_post(c, comment("c1", "LINK please!"))       # webhook retry
        signed_post(c, comment("c2", "nice video"))          # no keyword
        signed_post(c, comment("c3", "link", from_id="999"))  # our own reply
    urls = [call.args[0] for call in post.call_args_list]
    assert urls == [f"{bot.GRAPH}/999/messages", f"{bot.GRAPH}/c1/replies"]
    assert post.call_args_list[0].kwargs["json"]["recipient"] == {"comment_id": "c1"}
