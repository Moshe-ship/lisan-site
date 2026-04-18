#!/usr/bin/env python3
"""
Lisan hero visual — "Studio" cut.

Cinematic, layered, sophisticated. Replaces the space-agents concept and
the first minimalist pass. Core visual elements, back to front:

  1. Gradient mesh background (4 soft radial blobs)
  2. Vignette darkening at edges
  3. Ambient star particle layer with parallax
  4. Oversized ل watermark (10% opacity, blurred)
  5. Mac window chrome — traffic lights, title bar, status pills
  6. Content: staggered Arabic typography with RTL reveal
  7. Polar audio visualizer (64 bars in a ring)
  8. English translation caption
  9. Chromatic aberration on the primary text
 10. Film grain overlay per frame

Outputs to ~/Downloads/:
  lisan-hero.mp4          — H.264, 1440x810, 30fps, ~9s loop
  lisan-hero.gif          — palette-optimized, 15fps
  lisan-hero-poster.png   — single representative frame for og:image
"""

import math
import random
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

OUT_DIR = Path.home() / "Downloads"
FRAMES_DIR = Path("/tmp/lisan-hero-frames")
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# ---- Canvas & timing ------------------------------------------------------

W, H = 1440, 810
FPS = 30
DURATION_S = 9.0
TOTAL = int(FPS * DURATION_S)

# Palette — mirrors lisan-site/index.html :root exactly, plus richer
# midtones used for the gradient mesh that the landing page doesn't have.
BG          = (5, 5, 7)
INK         = (10, 10, 14)
ACCENT      = (125, 211, 252)
ACCENT_DIM  = (56, 189, 248)
ACCENT_DEEP = (14, 40, 60)
ACCENT_WARM = (96, 165, 250)
TEXT        = (208, 214, 226)
TEXT_DIM    = (110, 116, 128)
TEXT_DIMMER = (58, 62, 72)
SUCCESS     = (52, 199, 89)
CAUTION     = (255, 189, 46)
DANGER      = (255, 95, 87)

# Deterministic particles.
random.seed(42)

# ---- Fonts ----------------------------------------------------------------

def load_font(paths, size):
    for p in paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size)
            except OSError:
                continue
    return ImageFont.load_default()

AR = ["/System/Library/Fonts/SFArabic.ttf"]
AR_ROUND = ["/System/Library/Fonts/SFArabicRounded.ttf"]
MONO = [
    "/System/Library/Fonts/SFMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]
SANS = [
    "/System/Library/Fonts/SFNS.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]

F_WATERMARK = load_font(AR_ROUND, 900)    # massive ل behind everything
F_ARABIC_LG = load_font(AR, 68)
F_ARABIC_MD = load_font(AR, 40)
F_ARABIC_SM = load_font(AR, 22)
F_BRAND = load_font(MONO, 18)
F_MONO_MD = load_font(MONO, 15)
F_MONO_SM = load_font(MONO, 12)
F_EN_MD = load_font(SANS, 20)
F_EN_SM = load_font(SANS, 14)


# ---- Basic helpers --------------------------------------------------------

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def ease_out_expo(t):
    return 1 if t >= 1 else 1 - pow(2, -10 * t)


def clamp01(x):
    return max(0.0, min(1.0, x))


def has_arabic(s):
    return any("\u0600" <= ch <= "\u06ff" for ch in s)


def text_lang(s):
    return "ar" if has_arabic(s) else "en"


def alpha_blend_color(color, alpha):
    return (*color, max(0, min(255, int(alpha))))


# ---- Layer 1: gradient mesh background ------------------------------------

MESH_BLOBS = [
    # (cx_rel, cy_rel, radius, color, intensity)
    (0.20, 0.30, 700, ACCENT_DEEP, 0.45),
    (0.82, 0.25, 620, ACCENT_WARM, 0.28),
    (0.70, 0.80, 760, ACCENT, 0.32),
    (0.18, 0.85, 540, ACCENT_DIM, 0.22),
]

def render_mesh_bg(t):
    """Slow drift keeps the scene feeling alive without being distracting."""
    img = Image.new("RGB", (W, H), BG)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    drift = math.sin(t * math.tau * 0.04) * 14
    for (cx_rel, cy_rel, r, color, intensity) in MESH_BLOBS:
        cx = int(cx_rel * W + drift * (cx_rel - 0.5) * 2)
        cy = int(cy_rel * H + drift * (cy_rel - 0.5))
        blob = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(blob)
        # Two concentric passes for cheaper-than-per-pixel gradient look.
        steps = 28
        for s in range(steps, 0, -1):
            rr = r * s / steps
            a = int(intensity * (1 - s / steps) * 255)
            if a <= 0:
                continue
            draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                         fill=(*color, a))
        blob = blob.filter(ImageFilter.GaussianBlur(radius=70))
        overlay.alpha_composite(blob)
    base = img.convert("RGBA")
    base.alpha_composite(overlay)
    return base


# ---- Layer 2: vignette ----------------------------------------------------

def apply_vignette(img, strength=0.55):
    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    steps = 40
    max_r = int(math.hypot(W, H) * 0.7)
    for i in range(steps):
        r = int(max_r * (1 - i / steps))
        alpha = int(strength * (i / steps) * 255)
        draw.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r],
                     fill=255 - alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=120))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(ImageChops.invert(mask))
    img.alpha_composite(dark)
    return img


# ---- Layer 3: ambient particle stars --------------------------------------

STARS = []
for _ in range(55):
    STARS.append({
        "x": random.uniform(0, W),
        "y": random.uniform(0, H),
        "size": random.choice([1, 1, 1, 2, 2, 3]),
        "base_alpha": random.randint(40, 140),
        "drift": random.uniform(4, 18),
        "phase": random.uniform(0, math.tau),
        "parallax": random.uniform(0.3, 1.0),
    })

def render_stars(img, t):
    draw = ImageDraw.Draw(img)
    for s in STARS:
        # Very slow drift + twinkle.
        twinkle = 0.5 + 0.5 * math.sin(t * math.tau * 0.15 + s["phase"])
        alpha = int(s["base_alpha"] * twinkle)
        dx = math.sin(t * 0.2 + s["phase"]) * s["drift"] * s["parallax"]
        dy = math.cos(t * 0.12 + s["phase"]) * s["drift"] * 0.5
        x = (s["x"] + dx) % W
        y = (s["y"] + dy) % H
        r = s["size"]
        draw.ellipse([x - r, y - r, x + r, y + r],
                     fill=(*TEXT, alpha))
    return img


# ---- Layer 4: ل watermark -------------------------------------------------

def render_watermark(img, t):
    """The lam letter as a ghost element behind everything else."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    breath = 0.55 + 0.15 * math.sin(t * math.tau * 0.1)
    alpha = int(28 * breath)
    # Position slightly off-center so it doesn't fight the content.
    cx, cy = int(W * 0.82), int(H * 0.48)
    draw.text((cx, cy), "ل", font=F_WATERMARK,
              fill=(*ACCENT, alpha), anchor="mm",
              language="ar")
    layer = layer.filter(ImageFilter.GaussianBlur(radius=8))
    img.alpha_composite(layer)
    return img


# ---- Layer 5: Mac window chrome -------------------------------------------

def render_window_chrome(img, t_enter):
    """Traffic lights + title bar for the framed-in-a-Mac-window feel."""
    enter = ease_out_expo(clamp01(t_enter))
    if enter < 0.02:
        return img
    alpha = int(enter * 255)

    # Window rectangle inset from canvas edges.
    win_margin_x = 110
    win_margin_top = 120
    win_margin_bot = 120
    x0, y0 = win_margin_x, win_margin_top
    x1, y1 = W - win_margin_x, H - win_margin_bot

    # Subtle "glass" fill.
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=18,
                           fill=(*INK, int(220 * enter)))
    # Border.
    draw.rounded_rectangle([x0, y0, x1, y1], radius=18,
                           outline=(*TEXT_DIMMER, int(alpha * 0.6)), width=1)

    # Title bar band.
    bar_h = 40
    draw.rounded_rectangle([x0, y0, x1, y0 + bar_h], radius=18,
                           fill=(*INK, int(240 * enter)))
    # Bottom-edge hairline for the title bar.
    draw.line([x0 + 1, y0 + bar_h, x1 - 1, y0 + bar_h],
              fill=(*TEXT_DIMMER, int(alpha * 0.5)), width=1)

    # Traffic lights.
    tl_y = y0 + bar_h // 2
    for i, color in enumerate([DANGER, CAUTION, SUCCESS]):
        cx = x0 + 22 + i * 22
        draw.ellipse([cx - 7, tl_y - 7, cx + 7, tl_y + 7],
                     fill=(*color, alpha))

    # Title text centered in bar.
    draw.text(((x0 + x1) // 2, tl_y), "Lisan  ·  لسان",
              font=F_BRAND, fill=(*TEXT_DIM, alpha), anchor="mm")

    # Right-side status chips: model + language + beta.
    chip_y = tl_y
    right_edge = x1 - 18
    for text, color, width in [
        ("BETA", ACCENT_DIM, 44),
        ("AR · PRESS-TO-TALK", ACCENT, 160),
        ("SMALL · 465 MB", TEXT_DIM, 116),
    ]:
        right_edge -= width
        draw.rounded_rectangle(
            [right_edge, chip_y - 10, right_edge + width - 8, chip_y + 10],
            radius=6, outline=(*color, int(alpha * 0.9)), width=1,
        )
        draw.text((right_edge + (width - 8) / 2, chip_y),
                  text, font=F_MONO_SM, fill=(*color, alpha), anchor="mm")
        right_edge -= 6

    img.alpha_composite(layer)
    return img, (x0, y0, x1, y1, bar_h)


# ---- Layer 6: staggered Arabic typography ---------------------------------

def render_arabic_phrase(img, t_local, duration, arabic, english, win_box, reveal_start=0.15):
    """Reveal Arabic characters with a per-char focus-in (blur→sharp)."""
    x0, y0, x1, y1, bar_h = win_box
    content_cx = (x0 + x1) // 2
    content_cy = (y0 + bar_h + y1) // 2 - 30

    # Meta row above: language pill, session tag.
    draw = ImageDraw.Draw(img)
    meta_alpha = int(clamp01((t_local - 0.05) * 4) * 180)
    draw.text((content_cx, content_cy - 110),
              "·  ARABIC  ·  auto-detected  ·",
              font=F_MONO_MD, fill=(*ACCENT_DIM, meta_alpha), anchor="mm")

    # Typewriter with per-char blur fade.
    reveal_until = reveal_start + 0.55
    progress = clamp01((t_local - reveal_start) / (reveal_until - reveal_start))
    n = len(arabic)
    shown = max(0, int(ease_in_out_cubic(progress) * n))
    typed = arabic[:shown]

    # Measure typed for cursor.
    if typed:
        bbox = F_ARABIC_LG.getbbox(typed, language="ar", anchor="la")
        line_w = bbox[2] - bbox[0]
    else:
        line_w = 0

    # Draw Arabic with glow.
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.text((content_cx, content_cy), typed, font=F_ARABIC_LG,
            fill=(*TEXT, 255), anchor="mm", language="ar")
    # Glow.
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.text((content_cx, content_cy), typed, font=F_ARABIC_LG,
            fill=(*ACCENT, 100), anchor="mm", language="ar")
    glow = glow.filter(ImageFilter.GaussianBlur(radius=16))
    img.alpha_composite(glow)
    img.alpha_composite(layer)

    # Blinking cursor while typing.
    if progress < 1.0 and int(t_local * 3) % 2 == 0:
        cursor_x = content_cx - line_w / 2 - 6
        draw.rectangle([cursor_x - 3, content_cy - 32,
                        cursor_x + 2, content_cy + 26],
                       fill=(*ACCENT, 220))

    # English translation fades in below after Arabic lands.
    en_alpha = int(clamp01((t_local - reveal_until - 0.05) * 3) * 200)
    draw.text((content_cx, content_cy + 70), english,
              font=F_EN_MD, fill=(*TEXT_DIM, en_alpha), anchor="mm")

    # Small confidence/timestamp chip bottom-center.
    chip_alpha = int(clamp01((t_local - reveal_until) * 2) * 140)
    draw.text((content_cx, y1 - 30),
              f"00:0{int(t_local)}  ·  inserted locally  ·  0 bytes uploaded",
              font=F_MONO_SM, fill=(*TEXT_DIMMER, chip_alpha), anchor="mm")

    return img, (content_cx, content_cy)


# ---- Layer 7: polar audio visualizer --------------------------------------

def render_polar_viz(img, t, cx, cy, radius, intensity_phase, bars=64):
    """64 thin bars arranged in a full circle, lengths modulated by a
    synthesized spectrum. Does NOT touch real audio — purely decorative
    envelope that reads as 'voice is live right now'."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(bars):
        angle = (i / bars) * math.tau
        # Multi-sine envelope keyed to time.
        env = (
            math.sin(t * math.tau * 0.6 + i * 0.25) * 0.4 +
            math.sin(t * math.tau * 1.4 + i * 0.5) * 0.3 +
            math.sin(t * math.tau * 2.2 + i * 0.15) * 0.2
        )
        amp = abs(env) * (0.6 + 0.4 * math.sin(intensity_phase))
        length = 8 + amp * 36
        ca = math.cos(angle)
        sa = math.sin(angle)
        inner_r = radius
        outer_r = radius + length
        x0 = cx + ca * inner_r
        y0 = cy + sa * inner_r
        x1 = cx + ca * outer_r
        y1 = cy + sa * outer_r
        # Color shifts slightly with amplitude — brighter with more energy.
        c = ACCENT if amp > 0.5 else ACCENT_DIM
        alpha = int(150 + amp * 105)
        draw.line([x0, y0, x1, y1], fill=(*c, alpha), width=2)
    # Faint center ring.
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                 outline=(*ACCENT_DIM, 60), width=1)
    img.alpha_composite(layer)
    return img


# ---- Layer 9: chromatic aberration (subtle) -------------------------------

def chromatic_aberration(img, offset=2):
    """Shift red channel left, blue channel right. Very subtle — 1-2 px."""
    r, g, b, a = img.split()
    r = ImageChops.offset(r, -offset, 0)
    b = ImageChops.offset(b, offset, 0)
    return Image.merge("RGBA", (r, g, b, a))


# ---- Layer 10: film grain -------------------------------------------------

def film_grain(img, strength=10):
    """Per-frame random noise for cinematic texture. Kept low so the
    composition stays sharp."""
    noise = Image.new("L", (W, H))
    px = noise.load()
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            v = random.randint(-strength, strength) + 128
            px[x, y] = v
            if x + 1 < W: px[x + 1, y] = v
            if y + 1 < H: px[x, y + 1] = v
            if x + 1 < W and y + 1 < H: px[x + 1, y + 1] = v
    noise = noise.resize((W, H), Image.BILINEAR)
    noise_rgba = Image.merge("RGBA", (noise, noise, noise,
                                       Image.new("L", (W, H), 12)))
    img.alpha_composite(noise_rgba)
    return img


# ---- Scene schedule --------------------------------------------------------

SCENES = [
    # (name, duration_s, payload)
    ("approach", 2.0, None),
    ("phrase1",  2.8, ("اكتب للفريق إن لسان جاهز", "Tell the team Lisan is ready")),
    ("phrase2",  2.8, ("هل لغتك العربية جيدة؟", "Is your Arabic good?")),
    ("privacy",  1.4, ("صوتك لا يغادر جهازك", "Your voice never leaves your Mac")),
]


# ---- Compositor ------------------------------------------------------------

def render_frame(i):
    t = i / FPS

    # Layer 1: gradient mesh bg.
    img = render_mesh_bg(t)
    # Layer 3: stars above bg.
    img = render_stars(img, t)
    # Layer 4: watermark ل behind chrome.
    img = render_watermark(img, t)

    # Which scene and local time within it?
    cursor = 0.0
    scene_name, scene_dur, scene_payload = SCENES[-1]
    t_local = 0.0
    for name, dur, payload in SCENES:
        if t < cursor + dur:
            scene_name, scene_dur, scene_payload = name, dur, payload
            t_local = t - cursor
            break
        cursor += dur
    else:
        t_local = SCENES[-1][1]

    # Window chrome "enters" during approach scene, then stays.
    t_chrome_enter = min(1.0, t / 0.9) if scene_name == "approach" else 1.0
    result = render_window_chrome(img, t_chrome_enter)
    if isinstance(result, tuple):
        img, win_box = result
    else:
        img = result
        win_box = (110, 120, W - 110, H - 120, 40)

    # Primary content per scene.
    if scene_name == "approach":
        # Just the chrome + a "listening…" indicator coming up.
        x0, y0, x1, y1, bar_h = win_box
        draw = ImageDraw.Draw(img)
        listen_alpha = int(clamp01((t_local - 0.7) * 2.5) * 220)
        draw.text(((x0 + x1) // 2, (y0 + y1) // 2 - 30),
                  "listening…",
                  font=F_EN_MD, fill=(*TEXT_DIM, listen_alpha), anchor="mm")
        draw.text(((x0 + x1) // 2, (y0 + y1) // 2 + 6),
                  "press-to-talk",
                  font=F_MONO_SM, fill=(*TEXT_DIMMER, listen_alpha), anchor="mm")
        # Polar viz at low amplitude during approach.
        if listen_alpha > 0:
            render_polar_viz(img, t, (x0 + x1) // 2, y1 - 92, 52, t * 0.4)
    elif scene_name in ("phrase1", "phrase2"):
        arabic, english = scene_payload
        img, (cx, cy) = render_arabic_phrase(img, t_local, scene_dur,
                                             arabic, english, win_box)
        # Polar viz runs during the phrase.
        x0, y0, x1, y1, bar_h = win_box
        render_polar_viz(img, t, (x0 + x1) // 2, y1 - 92, 52,
                         math.pi * (t_local / scene_dur))
    elif scene_name == "privacy":
        x0, y0, x1, y1, bar_h = win_box
        draw = ImageDraw.Draw(img)
        ar, en = scene_payload
        fade = ease_out_expo(clamp01(t_local / 0.7))
        draw.text(((x0 + x1) // 2, (y0 + y1) // 2 - 10), ar,
                  font=F_ARABIC_MD,
                  fill=(*TEXT, int(fade * 255)), anchor="mm", language="ar")
        en_alpha = int(clamp01((t_local - 0.5) * 2) * 180)
        draw.text(((x0 + x1) // 2, (y0 + y1) // 2 + 44), en,
                  font=F_EN_MD, fill=(*TEXT_DIM, en_alpha), anchor="mm")
        # Fading viz.
        render_polar_viz(img, t, (x0 + x1) // 2, y1 - 92, 52, t)

    # Top-of-canvas header text (outside chrome) — consistent throughout.
    draw = ImageDraw.Draw(img)
    draw.text((W // 2, 50), "LISAN  ·  ARABIC-FIRST LOCAL DICTATION FOR macOS",
              font=F_MONO_MD, fill=(*TEXT_DIM, 210), anchor="mm")

    # Bottom corner marks.
    draw.text((W - 60, H - 60), "v0.3.18  ·  BETA",
              font=F_MONO_SM, fill=(*TEXT_DIMMER, 230), anchor="rm")
    draw.text((60, H - 60), "github.com/Moshe-ship/Lisan",
              font=F_MONO_SM, fill=(*TEXT_DIMMER, 210), anchor="lm")

    # Layer 2: vignette over everything up to this point.
    img = apply_vignette(img, strength=0.55)

    # Layer 9: chromatic aberration (very subtle).
    img = chromatic_aberration(img, offset=2)

    # Layer 10: film grain.
    img = film_grain(img, strength=8)

    return img


# ---- Main ------------------------------------------------------------------

def main():
    for old in FRAMES_DIR.glob("f_*.png"):
        old.unlink()

    print(f"rendering {TOTAL} frames at {W}x{H} @{FPS}fps...")
    for i in range(TOTAL):
        frame = render_frame(i)
        flat = Image.new("RGB", (W, H), BG)
        flat.paste(frame.convert("RGB"), (0, 0))
        flat.save(FRAMES_DIR / f"f_{i:04d}.png", "PNG", optimize=False)
        if i % 30 == 0 or i == TOTAL - 1:
            print(f"  {i + 1}/{TOTAL}")

    # Poster frame: pick a peak moment from phrase1 (~4s in).
    poster_idx = int(FPS * 3.6)
    src = FRAMES_DIR / f"f_{poster_idx:04d}.png"
    poster = OUT_DIR / "lisan-hero-poster.png"
    subprocess.run(["cp", str(src), str(poster)], check=True)
    print(f"poster → {poster}")

    mp4 = OUT_DIR / "lisan-hero.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "f_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "20", "-preset", "slow",
        "-movflags", "+faststart",
        str(mp4),
    ], check=True)
    print(f"mp4 → {mp4} ({mp4.stat().st_size // 1024} KB)")

    palette = Path("/tmp/lisan_palette.png")
    gif = OUT_DIR / "lisan-hero.gif"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(mp4),
        "-vf", "fps=15,scale=960:-1:flags=lanczos,palettegen=max_colors=128:stats_mode=diff",
        str(palette),
    ], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(mp4),
        "-i", str(palette),
        "-filter_complex", "fps=15,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a",
        str(gif),
    ], check=True)
    print(f"gif → {gif} ({gif.stat().st_size // 1024} KB)")
    print("\nAll three assets in ~/Downloads/")


if __name__ == "__main__":
    main()
