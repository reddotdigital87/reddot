from unittest import mock

import post_reel


def resp(payload):
    r = mock.Mock(ok=True)
    r.json.return_value = payload
    return r


def test_local_file_upload_flow(tmp_path):
    video = tmp_path / "reel.mp4"
    video.write_bytes(b"abc")
    with mock.patch.object(post_reel.requests, "post") as post, \
            mock.patch.object(post_reel.requests, "get") as get:
        post.side_effect = [resp({"id": "c1"}), resp({"success": True}), resp({"id": "m1"})]
        get.return_value = resp({"status_code": "FINISHED"})
        cid = post_reel.create_container("u1", "tok", str(video), "hi")
        post_reel.wait_until_ready(cid, "tok")
        media_id = post_reel.publish("u1", "tok", cid)

    assert media_id == "m1"
    create, upload, pub = post.call_args_list
    assert create.kwargs["data"]["upload_type"] == "resumable"
    assert create.kwargs["data"]["media_type"] == "REELS"
    assert upload.args[0] == f"{post_reel.UPLOAD}/c1"
    assert upload.kwargs["headers"]["file_size"] == "3"
    assert pub.kwargs["data"] == {"creation_id": "c1"}


def test_url_skips_upload():
    with mock.patch.object(post_reel.requests, "post") as post:
        post.return_value = resp({"id": "c2"})
        post_reel.create_container("u1", "tok", "https://x.com/v.mp4", "hi")
    assert post.call_count == 1
    assert post.call_args.kwargs["data"]["video_url"] == "https://x.com/v.mp4"
