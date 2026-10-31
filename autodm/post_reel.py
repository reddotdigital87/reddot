"""Publish a reel to Instagram via the official Content Publishing API.

Usage:
    python3 post_reel.py <video.mp4 | https://public/video.mp4> "caption text"

Uses the same IG_ACCESS_TOKEN / IG_USER_ID as app.py. The token needs the
instagram_business_content_publish permission. A local file is sent with
Instagram's resumable upload; a URL must be publicly reachable.
"""

import os
import sys
import time
from pathlib import Path

import requests

API_VERSION = "v21.0"
GRAPH = f"https://graph.instagram.com/{API_VERSION}"
UPLOAD = f"https://rupload.facebook.com/ig-api-upload/{API_VERSION}"


def check(resp):
    if not resp.ok:
        sys.exit(f"Instagram API error {resp.status_code}: {resp.text}")
    return resp.json()


def create_container(user_id, token, video, caption):
    params = {"media_type": "REELS", "caption": caption, "share_to_feed": "true"}
    if video.startswith(("http://", "https://")):
        params["video_url"] = video
    else:
        params["upload_type"] = "resumable"
    headers = {"Authorization": f"Bearer {token}"}
    container_id = check(requests.post(f"{GRAPH}/{user_id}/media", data=params,
                                       headers=headers, timeout=30))["id"]

    if params.get("upload_type") == "resumable":
        data = Path(video).read_bytes()
        check(requests.post(f"{UPLOAD}/{container_id}", data=data, timeout=300, headers={
            "Authorization": f"OAuth {token}",
            "offset": "0",
            "file_size": str(len(data)),
        }))
    return container_id


def wait_until_ready(container_id, token, timeout=600, interval=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = check(requests.get(f"{GRAPH}/{container_id}", params={"fields": "status_code,status"},
                                    headers={"Authorization": f"Bearer {token}"}, timeout=30))
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram could not process the video: {status}")
        print(f"Processing... ({code})")
        time.sleep(interval)
    sys.exit("Timed out waiting for Instagram to process the video")


def publish(user_id, token, container_id):
    return check(requests.post(f"{GRAPH}/{user_id}/media_publish", data={"creation_id": container_id},
                               headers={"Authorization": f"Bearer {token}"}, timeout=30))["id"]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    video, caption = sys.argv[1], sys.argv[2]
    token, user_id = os.environ.get("IG_ACCESS_TOKEN"), os.environ.get("IG_USER_ID")
    if not token or not user_id:
        sys.exit("Set IG_ACCESS_TOKEN and IG_USER_ID first (see .env.example)")

    container_id = create_container(user_id, token, video, caption)
    print(f"Uploaded, container {container_id}")
    wait_until_ready(container_id, token)
    media_id = publish(user_id, token, container_id)
    print(f"Published! Media ID: {media_id}")
    print(f"Auto-DM sirf is reel par chalana ho to .env mein MEDIA_IDS={media_id} set karein.")


if __name__ == "__main__":
    main()
