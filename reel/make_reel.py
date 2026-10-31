"""Render a 1080x1920 Instagram reel from reel_config.json.

Usage:
    python3 reel/make_reel.py [config.json] [output.mp4]

Frames are drawn with Pillow and piped straight into ffmpeg, so the only
requirements are Pillow and an ffmpeg binary on PATH.
"""

import json
import math
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
HERE = Path(__file__).resolve().parent

FONT_CANDIDATES = {
    "black": [
        "/usr/share/fonts/opentype/inter/Inter-Black.otf",
        "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "bold": [
        "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "medium": [
        "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}


@lru_cache(maxsize=None)
def load_font(weight, size):
    for path in FONT_CANDIDATES[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def make_background(top, bottom, accent):
    bg = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(bg)
    for y in range(H):
        k = y / (H - 1)
        draw.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bottom)))
    # soft accent glow
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse([W * 0.15, H * 0.30, W * 0.85, H * 0.70], fill=60)
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    bg.paste(Image.new("RGB", (W, H), accent), (0, 0), glow)
    return bg


def text_width(draw, text, font):
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def fit_font(draw, text, weight, size, max_w):
    font = load_font(weight, size)
    while text_width(draw, text, font) > max_w and size > 40:
        size -= 4
        font = load_font(weight, size)
    return font


def draw_centered(layer, text, y, font, fill, alpha):
    draw = ImageDraw.Draw(layer)
    x = (W - text_width(draw, text, font)) / 2
    draw.text((x, y), text, font=font, fill=fill + (int(255 * alpha),))


def render_scene(frame, scene, t, cfg, colors):
    """Draw one scene onto `frame` at local time t (seconds)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    dur = scene["duration"]
    fade_out = 1 - ease_out((t - (dur - 0.25)) / 0.25) if t > dur - 0.25 else 1.0

    kicker_font = load_font("bold", 44)
    k = ease_out(t / 0.35)
    kicker = scene.get("kicker", "")
    if kicker:
        kw = text_width(draw, kicker, kicker_font) + 60
        kx, ky = (W - kw) / 2, 560 - 30 * (1 - k)
        draw.rounded_rectangle([kx, ky, kx + kw, ky + 84], radius=42,
                               fill=colors["accent"] + (int(255 * k * fade_out),))
        draw_centered(layer, kicker, ky + 16, kicker_font, colors["text"], k * fade_out)

    font = min((fit_font(draw, line, "black", 120, W - 140) for line in scene["lines"]),
               key=lambda f: f.size)
    y = 760
    for i, line in enumerate(scene["lines"]):
        p = ease_out((t - 0.25 - i * 0.22) / 0.4)
        draw_centered(layer, line, y + 60 * (1 - p), font, colors["text"], p * fade_out)
        y += 150

    if scene.get("cta"):
        keyword = cfg["keyword"]
        p = ease_out((t - 0.5) / 0.4)
        pulse = 1 + 0.05 * math.sin(t * 2 * math.pi * 1.6) if p >= 1 else 0.6 + 0.4 * p
        box_w, box_h = int(640 * pulse), int(220 * pulse)
        bx, by = (W - box_w) / 2, 980 - box_h / 2 + 120
        draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=36,
                               fill=colors["accent"] + (int(255 * p * fade_out),))
        kf = fit_font(draw, f"“{keyword}”", "black", int(130 * pulse), box_w - 60)
        _, top, _, bottom = draw.textbbox((0, 0), keyword, font=kf)
        draw_centered(layer, f"“{keyword}”", by + (box_h - (bottom - top)) / 2 - top,
                      kf, colors["text"], p * fade_out)
        sub = ease_out((t - 1.0) / 0.4)
        draw_centered(layer, "aur link seedha aapke DM mein",
                      by + box_h + 60, load_font("medium", 52), colors["muted"], sub * fade_out)

    frame.alpha_composite(layer)


def render_chrome(frame, cfg, colors, t, total):
    draw = ImageDraw.Draw(frame)
    draw.text((70, 150), cfg["brand"], font=load_font("black", 56), fill=colors["accent"] + (255,))
    draw.ellipse([70 + text_width(draw, cfg["brand"], load_font("black", 56)) + 14, 172,
                  70 + text_width(draw, cfg["brand"], load_font("black", 56)) + 34, 192],
                 fill=colors["accent"] + (255,))
    handle_font = load_font("medium", 40)
    draw.text(((W - text_width(draw, cfg["handle"], handle_font)) / 2, H - 330),
              cfg["handle"], font=handle_font, fill=colors["muted"] + (255,))
    # progress bar
    draw.rounded_rectangle([70, 110, W - 70, 118], radius=4, fill=(255, 255, 255, 50))
    draw.rounded_rectangle([70, 110, 70 + (W - 140) * (t / total), 118], radius=4,
                           fill=colors["accent"] + (255,))


def main():
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "reel_config.json"
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "output" / "reel.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    colors = {k: hex_rgb(v) for k, v in cfg["colors"].items()}
    fps = cfg.get("fps", 30)
    scenes = cfg["scenes"]
    total = sum(s["duration"] for s in scenes)
    background = make_background(colors["bg_top"], colors["bg_bottom"], colors["accent"]).convert("RGBA")

    ffmpeg = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart",
        str(out_path),
    ], stdin=subprocess.PIPE)

    n_frames = int(round(total * fps))
    for f in range(n_frames):
        t = f / fps
        start = 0.0
        for scene in scenes:
            if t < start + scene["duration"] or scene is scenes[-1]:
                break
            start += scene["duration"]
        frame = background.copy()
        render_scene(frame, scene, t - start, cfg, colors)
        render_chrome(frame, cfg, colors, t, total)
        ffmpeg.stdin.write(frame.convert("RGB").tobytes())

    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"Saved {out_path} ({total:.1f}s, {n_frames} frames)")


if __name__ == "__main__":
    main()
