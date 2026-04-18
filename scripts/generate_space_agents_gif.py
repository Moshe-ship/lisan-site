from __future__ import annotations

import math
import random
from pathlib import Path

import arabic_reshaper
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUT_GIF = ASSETS / "lisan-space-agents.gif"
OUT_POSTER = ASSETS / "lisan-space-agents-poster.png"

W = 1080
H = 1080
FRAMES = 48
DURATION_MS = 70

FONT_LATIN = "/System/Library/Fonts/SFNSMono.ttf"
FONT_ARABIC = "/System/Library/Fonts/SFArabic.ttf"

BG_TOP = (5, 10, 22)
BG_BOTTOM = (2, 5, 14)
CYAN = (92, 231, 255)
MINT = (88, 255, 214)
ICE = (233, 246, 255)
STEEL = (132, 165, 196)
INDIGO = (96, 122, 255)


def ar(text: str) -> str:
    return arabic_reshaper.reshape(text)


def clamp(v: float, low: float, high: float) -> float:
    return max(low, min(high, v))


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def ease(t: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * t)


def radial_glow(size: int, color: tuple[int, int, int], power: float = 1.8) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    c = size / 2
    max_dist = math.sqrt(2 * (c**2))
    for y in range(size):
        for x in range(size):
            d = math.sqrt((x - c) ** 2 + (y - c) ** 2) / max_dist
            alpha = int(255 * max(0.0, 1.0 - d) ** power)
            if alpha:
                px[x, y] = (*color, alpha)
    return img


def draw_background(frame_idx: int) -> Image.Image:
    base = Image.new("RGBA", (W, H), (*BG_TOP, 255))
    draw = ImageDraw.Draw(base)
    for y in range(H):
        t = y / (H - 1)
        color = mix(BG_TOP, BG_BOTTOM, t)
        draw.line((0, y, W, y), fill=color)

    nebula = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    nd = ImageDraw.Draw(nebula)
    drift = math.sin(frame_idx / FRAMES * math.tau) * 18
    nd.ellipse((-120 + drift, 90, 560 + drift, 760), fill=(*INDIGO, 34))
    nd.ellipse((430 - drift, -40, 1180 - drift, 560), fill=(*CYAN, 22))
    nd.ellipse((170, 470, 970, 1130), fill=(34, 101, 255, 18))
    nebula = nebula.filter(ImageFilter.GaussianBlur(96))
    base.alpha_composite(nebula)

    aurora = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ad = ImageDraw.Draw(aurora)
    for i in range(5):
        x = -240 + i * 260 + drift * (0.6 + i * 0.08)
        ad.polygon(
            [(x, -30), (x + 240, -30), (x + 520, H + 30), (x + 260, H + 30)],
            fill=(*MINT, 10 + i * 3),
        )
    aurora = aurora.filter(ImageFilter.GaussianBlur(42))
    base.alpha_composite(aurora)

    star = ImageDraw.Draw(base)
    rng = random.Random(20260418)
    for i in range(180):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, H - 1)
        twinkle = 0.45 + 0.55 * math.sin((frame_idx * 0.14) + i * 1.73)
        alpha = int(55 + 155 * max(0, twinkle))
        r = 1 if i % 5 else 2
        star.ellipse((x - r, y - r, x + r, y + r), fill=(220, 236, 255, alpha))

    for y in range(0, H, 7):
        draw.line((0, y, W, y), fill=(255, 255, 255, 5))

    return base


def node_positions() -> list[tuple[int, int]]:
    return [
        (182, 318),
        (898, 258),
        (886, 822),
        (198, 842),
    ]


def packet_point(a: tuple[int, int], b: tuple[int, int], t: float) -> tuple[float, float]:
    x = a[0] + (b[0] - a[0]) * t
    y = a[1] + (b[1] - a[1]) * t
    curve = math.sin(t * math.pi) * 42
    nx = -(b[1] - a[1])
    ny = b[0] - a[0]
    length = math.sqrt(nx * nx + ny * ny) or 1
    return x + nx / length * curve, y + ny / length * curve


def draw_agent_network(frame_idx: int, canvas: Image.Image) -> None:
    center = (540, 540)
    nodes = node_positions()
    phase = frame_idx / FRAMES
    draw = ImageDraw.Draw(canvas)
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((132, 132, 948, 948), outline=(*CYAN, 26), width=2)
    rd.ellipse((214, 214, 866, 866), outline=(*INDIGO, 20), width=2)
    rd.rounded_rectangle((312, 312, 768, 768), radius=42, outline=(*ICE, 18), width=1)
    ring = ring.filter(ImageFilter.GaussianBlur(1.2))
    canvas.alpha_composite(ring)

    link_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(link_layer)
    node_colors = [CYAN, INDIGO, MINT, CYAN]
    for i, node in enumerate(nodes):
        color = node_colors[i]
        ld.line((center[0], center[1], node[0], node[1]), fill=(*color, 58), width=3)
    for i in range(len(nodes)):
        a = nodes[i]
        b = nodes[(i + 1) % len(nodes)]
        ld.line((a[0], a[1], b[0], b[1]), fill=(*STEEL, 18), width=1)
    link_layer = link_layer.filter(ImageFilter.GaussianBlur(0.8))
    canvas.alpha_composite(link_layer)

    packet_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(packet_layer)
    for i, node in enumerate(nodes):
        color = node_colors[i]
        for offset in (0.0, 0.33, 0.66):
            t = (phase * 1.35 + offset + i * 0.08) % 1.0
            x, y = packet_point(node, center, t)
            r = 5 + 1.5 * math.sin((phase + offset) * math.tau)
            pd.ellipse((x - r, y - r, x + r, y + r), fill=(*color, 248))
            pd.ellipse((x - r * 3.2, y - r * 3.2, x + r * 3.2, y + r * 3.2), fill=(*color, 24))
    packet_layer = packet_layer.filter(ImageFilter.GaussianBlur(0.6))
    canvas.alpha_composite(packet_layer)

    for i, node in enumerate(nodes):
        base_color = node_colors[i]
        pulse = 0.75 + 0.25 * math.sin(phase * math.tau + i * 0.9)
        glow = radial_glow(170, base_color, power=2.2)
        glow.putalpha(glow.getchannel("A").point(lambda p: int(p * pulse * 0.85)))
        canvas.alpha_composite(glow, (node[0] - 85, node[1] - 85))
        draw.rounded_rectangle((node[0] - 34, node[1] - 34, node[0] + 34, node[1] + 34), radius=18, fill=(8, 16, 30, 255), outline=(*base_color, 245), width=3)
        draw.ellipse((node[0] - 10, node[1] - 10, node[0] + 10, node[1] + 10), fill=(*base_color, 255))

    core_glow = radial_glow(320, MINT, power=2.1)
    core_glow.putalpha(core_glow.getchannel("A").point(lambda p: int(p * (0.9 + 0.1 * math.sin(phase * math.tau)))))
    canvas.alpha_composite(core_glow, (center[0] - 140, center[1] - 140))
    draw.rounded_rectangle((center[0] - 90, center[1] - 90, center[0] + 90, center[1] + 90), radius=30, fill=(7, 14, 26, 255), outline=(*MINT, 255), width=4)
    draw.ellipse((center[0] - 22, center[1] - 22, center[0] + 22, center[1] + 22), fill=(*MINT, 255))


def draw_words(frame_idx: int, canvas: Image.Image) -> None:
    phase = frame_idx / FRAMES
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    font_ar = ImageFont.truetype(FONT_ARABIC, 46)
    font_lat = ImageFont.truetype(FONT_LATIN, 22)

    words = [
        (ar("صوت"), 236, 190, 0.0),
        (ar("لغة"), 856, 176, 0.2),
        (ar("عربي"), 870, 908, 0.46),
        (ar("محلي"), 204, 910, 0.62),
        (ar("وكلاء"), 540, 114, 0.82),
    ]
    for text, x, y, offset in words:
        bob = math.sin((phase + offset) * math.tau) * 12
        alpha = int(120 + 70 * max(0, math.sin((phase * 1.8 + offset) * math.tau)))
        d.text((x, y + bob), text, font=font_ar, fill=(*CYAN, alpha), anchor="mm")

    orbit_labels = [
        ("LOCAL", 180, 540, 0.1),
        ("METAL", 900, 540, 0.35),
        ("AGENTS", 540, 254, 0.58),
        ("WHISPER", 540, 830, 0.8),
    ]
    for text, x, y, offset in orbit_labels:
        alpha = int(70 + 55 * max(0, math.sin((phase + offset) * math.tau)))
        d.text((x, y), text, font=font_lat, fill=(*STEEL, alpha), anchor="mm")

    layer = layer.filter(ImageFilter.GaussianBlur(0.2))
    canvas.alpha_composite(layer)


def draw_title(frame_idx: int, canvas: Image.Image) -> None:
    phase = frame_idx / FRAMES
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    title_font = ImageFont.truetype(FONT_ARABIC, 116)
    sub_font = ImageFont.truetype(FONT_ARABIC, 34)
    latin_font = ImageFont.truetype(FONT_LATIN, 26)

    title = ar("لسان")
    subtitle = ar("إملاء عربي محلي لوكلاء الذكاء")

    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((250, 430, 830, 660), radius=30, fill=(6, 12, 22, 178), outline=(*CYAN, 72), width=2)
    card = card.filter(ImageFilter.GaussianBlur(0.8))
    overlay.alpha_composite(card)

    pulse = 0.92 + 0.08 * math.sin(phase * math.tau)
    d.text((540, 510), title, font=title_font, fill=(*ICE, int(255 * pulse)), anchor="mm")
    d.text((540, 590), subtitle, font=sub_font, fill=(*CYAN, 228), anchor="mm")
    d.text((540, 635), "ARABIC-FIRST LOCAL DICTATION", font=latin_font, fill=(*STEEL, 188), anchor="mm")
    overlay = overlay.filter(ImageFilter.GaussianBlur(0.3))
    canvas.alpha_composite(overlay)


def add_vignette(canvas: Image.Image) -> Image.Image:
    vignette = Image.new("L", (W, H), 0)
    px = vignette.load()
    cx, cy = W / 2, H / 2
    max_d = math.sqrt(cx * cx + cy * cy)
    for y in range(H):
        for x in range(W):
            d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_d
            alpha = int(clamp((d - 0.28) / 0.72, 0, 1) * 175)
            px[x, y] = alpha
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(vignette)
    return Image.alpha_composite(canvas, shadow)


def build_frame(frame_idx: int) -> Image.Image:
    frame = draw_background(frame_idx)
    draw_agent_network(frame_idx, frame)
    draw_words(frame_idx, frame)
    draw_title(frame_idx, frame)
    frame = add_vignette(frame)
    return frame.convert("P", palette=Image.ADAPTIVE, colors=255)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    frames = [build_frame(i) for i in range(FRAMES)]
    poster = frames[0].convert("RGBA")
    poster.save(OUT_POSTER)
    frames[0].save(
        OUT_GIF,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        disposal=2,
        optimize=False,
    )
    print(OUT_GIF)
    print(OUT_POSTER)


if __name__ == "__main__":
    main()
