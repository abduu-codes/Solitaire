"""
generate_assets.py
Generates 52 high-resolution anti-aliased playing card PNGs + 1 luxury ornate card back PNG
using Pillow vector geometry (zero broken Unicode glyph issues across OSes).
"""
import os
import math
from PIL import Image, ImageDraw, ImageFont

SUITS = ["spades", "hearts", "clubs", "diamonds"]
RANKS = {
    1: "A", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    8: "8", 9: "9", 10: "10", 11: "J", 12: "Q", 13: "K",
}

OUT_W, OUT_H = 114, 160
SCALE = 2
W, H = OUT_W * SCALE, OUT_H * SCALE
RESAMPLE_LANCZOS = getattr(Image, "Resampling", Image).LANCZOS

RED_COLOR = (214, 34, 54, 255)
BLACK_COLOR = (22, 28, 42, 255)
CARD_BG = (250, 251, 253, 255)
CARD_BORDER = (205, 213, 224, 255)
GOLD_ACCENT = (212, 168, 72, 255)
ROYAL_BG_RED = (254, 242, 244, 255)
ROYAL_BG_BLK = (240, 244, 250, 255)


def load_font(size: int, bold: bool = True):
    candidates = [
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_heart(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float, color, upside_down=False):
    pts = []
    steps = 40
    for i in range(steps):
        t = (2 * math.pi * i) / steps
        x = 16 * (math.sin(t) ** 3)
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        if upside_down:
            y = -y
        px = cx + (x / 17.5) * size
        py = cy + (y / 17.5) * size
        pts.append((px, py))
    draw.polygon(pts, fill=color)


def draw_diamond(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float, color, upside_down=False):
    rx = size * 0.78
    ry = size * 1.04
    pts = [(cx, cy - ry), (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)]
    draw.polygon(pts, fill=color)


def draw_spade(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float, color, upside_down=False):
    body_cy = cy - size * 0.08 if not upside_down else cy + size * 0.08
    draw_heart(draw, cx, body_cy, size * 0.92, color, upside_down=not upside_down)
    sign = -1 if upside_down else 1
    stem = [
        (cx, cy + sign * size * 0.15),
        (cx - size * 0.36, cy + sign * size * 0.95),
        (cx + size * 0.36, cy + sign * size * 0.95),
    ]
    draw.polygon(stem, fill=color)


def draw_club(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float, color, upside_down=False):
    sign = -1 if upside_down else 1
    r = size * 0.42
    lobes = [
        (cx, cy - sign * size * 0.42),
        (cx - size * 0.44, cy + sign * size * 0.12),
        (cx + size * 0.44, cy + sign * size * 0.12),
    ]
    for lx, ly in lobes:
        draw.ellipse((lx - r, ly - r, lx + r, ly + r), fill=color)
    draw.ellipse((cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6), fill=color)
    stem = [
        (cx, cy + sign * size * 0.12),
        (cx - size * 0.34, cy + sign * size * 0.95),
        (cx + size * 0.34, cy + sign * size * 0.95),
    ]
    draw.polygon(stem, fill=color)


def draw_suit(draw, suit: str, cx: float, cy: float, size: float, color, upside_down=False):
    if suit == "hearts":
        draw_heart(draw, cx, cy, size, color, upside_down)
    elif suit == "diamonds":
        draw_diamond(draw, cx, cy, size, color, upside_down)
    elif suit == "spades":
        draw_spade(draw, cx, cy, size, color, upside_down)
    elif suit == "clubs":
        draw_club(draw, cx, cy, size, color, upside_down)


PIP_LAYOUTS = {
    2: [(0.5, 0.23, False), (0.5, 0.77, True)],
    3: [(0.5, 0.22, False), (0.5, 0.50, False), (0.5, 0.78, True)],
    4: [(0.34, 0.23, False), (0.66, 0.23, False), (0.34, 0.77, True), (0.66, 0.77, True)],
    5: [(0.34, 0.23, False), (0.66, 0.23, False), (0.5, 0.50, False), (0.34, 0.77, True), (0.66, 0.77, True)],
    6: [(0.34, 0.22, False), (0.66, 0.22, False), (0.34, 0.50, False), (0.66, 0.50, False), (0.34, 0.78, True), (0.66, 0.78, True)],
    7: [(0.34, 0.22, False), (0.66, 0.22, False), (0.5, 0.36, False), (0.34, 0.50, False), (0.66, 0.50, False), (0.34, 0.78, True), (0.66, 0.78, True)],
    8: [(0.34, 0.22, False), (0.66, 0.22, False), (0.5, 0.36, False), (0.34, 0.50, False), (0.66, 0.50, False), (0.5, 0.64, True), (0.34, 0.78, True), (0.66, 0.78, True)],
    9: [(0.34, 0.20, False), (0.66, 0.20, False), (0.34, 0.40, False), (0.66, 0.40, False), (0.5, 0.50, False), (0.34, 0.60, True), (0.66, 0.60, True), (0.34, 0.80, True), (0.66, 0.80, True)],
    10: [(0.34, 0.20, False), (0.66, 0.20, False), (0.5, 0.31, False), (0.34, 0.40, False), (0.66, 0.40, False), (0.34, 0.60, True), (0.66, 0.60, True), (0.5, 0.69, True), (0.34, 0.80, True), (0.66, 0.80, True)],
}


def draw_crown(draw, cx, cy, w, h, color):
    pts = [
        (cx - w * 0.5, cy + h * 0.45),
        (cx - w * 0.55, cy - h * 0.25),
        (cx - w * 0.22, cy + h * 0.08),
        (cx, cy - h * 0.5),
        (cx + w * 0.22, cy + h * 0.08),
        (cx + w * 0.55, cy - h * 0.25),
        (cx + w * 0.5, cy + h * 0.45),
    ]
    draw.polygon(pts, fill=color)
    draw.rectangle((cx - w * 0.5, cy + h * 0.45, cx + w * 0.5, cy + h * 0.62), fill=color)


def create_card_image(suit: str, rank: int) -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = RED_COLOR if suit in ("hearts", "diamonds") else BLACK_COLOR
    rank_str = RANKS[rank]

    # Rounded card base with subtle border
    draw.rounded_rectangle((2, 2, W - 3, H - 3), radius=18, fill=CARD_BG, outline=CARD_BORDER, width=3)

    font_rank = load_font(34 if rank != 10 else 30, bold=True)
    font_court = load_font(76, bold=True)

    # Top-left rank & mini suit
    bbox = draw.textbbox((0, 0), rank_str, font=font_rank)
    tw = bbox[2] - bbox[0]
    corner_x = 26
    draw.text((corner_x - tw / 2, 12), rank_str, fill=color, font=font_rank)
    draw_suit(draw, suit, corner_x, 66, 13, color, upside_down=False)

    # Bottom-right inverted corner
    corner_stamp = Image.new("RGBA", (60, 90), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(corner_stamp)
    cdraw.text((30 - tw / 2, 6), rank_str, fill=color, font=font_rank)
    draw_suit(cdraw, suit, 30, 60, 13, color, upside_down=False)
    corner_stamp = corner_stamp.rotate(180)
    img.alpha_composite(corner_stamp, (W - 56, H - 96))

    # Center Art
    if rank == 1:
        draw.ellipse((W / 2 - 54, H / 2 - 54, W / 2 + 54, H / 2 + 54), outline=GOLD_ACCENT, width=3)
        draw.ellipse((W / 2 - 46, H / 2 - 46, W / 2 + 46, H / 2 + 46), outline=CARD_BORDER, width=2)
        draw_suit(draw, suit, W / 2, H / 2, 36, color)
    elif rank in (11, 12, 13):
        frame_bg = ROYAL_BG_RED if suit in ("hearts", "diamonds") else ROYAL_BG_BLK
        fx1, fy1, fx2, fy2 = 50, 44, W - 50, H - 44
        draw.rounded_rectangle((fx1, fy1, fx2, fy2), radius=12, fill=frame_bg, outline=GOLD_ACCENT, width=3)
        draw.rounded_rectangle((fx1 + 6, fy1 + 6, fx2 - 6, fy2 - 6), radius=8, outline=color, width=1)
        draw_crown(draw, W / 2, fy1 + 36, 56, 30, GOLD_ACCENT)

        cb = draw.textbbox((0, 0), rank_str, font=font_court)
        cw, ch = cb[2] - cb[0], cb[3] - cb[1]
        draw.text((W / 2 - cw / 2, H / 2 - ch / 2 - 8), rank_str, fill=color, font=font_court)
        draw_suit(draw, suit, W / 2, fy2 - 38, 19, color)
    else:
        for xf, yf, flip in PIP_LAYOUTS[rank]:
            draw_suit(draw, suit, xf * W, yf * H, 16, color, upside_down=flip)

    return img.resize((OUT_W, OUT_H), RESAMPLE_LANCZOS)


def create_card_back() -> Image.Image:
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((2, 2, W - 3, H - 3), radius=18, fill=(245, 248, 252, 255), outline=(180, 194, 212, 255), width=3)
    draw.rounded_rectangle((14, 14, W - 15, H - 15), radius=12, fill=(13, 27, 46, 255), outline=(45, 212, 191, 255), width=3)
    draw.rounded_rectangle((22, 22, W - 23, H - 23), radius=8, outline=GOLD_ACCENT, width=2)

    lattice_color = (26, 58, 92, 255)
    for x in range(28, W - 26, 20):
        for y in range(28, H - 26, 20):
            draw.polygon([(x, y - 7), (x + 7, y), (x, y + 7), (x - 7, y)], outline=lattice_color)

    cx, cy = W / 2, H / 2
    draw.polygon([(cx, cy - 48), (cx + 36, cy), (cx, cy + 48), (cx - 36, cy)], fill=(18, 42, 68, 255), outline=GOLD_ACCENT)
    draw.polygon([(cx, cy - 34), (cx + 25, cy), (cx, cy + 34), (cx - 25, cy)], fill=(13, 27, 46, 255), outline=(45, 212, 191, 255))
    draw_diamond(draw, cx, cy, 13, GOLD_ACCENT)
    draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(45, 212, 191, 255))

    return img.resize((OUT_W, OUT_H), RESAMPLE_LANCZOS)


def generate_all_assets(output_dir: str = None):
    if output_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "assets", "cards")
    os.makedirs(output_dir, exist_ok=True)

    for suit in SUITS:
        for rank in range(1, 14):
            fname = f"{RANKS[rank].lower()}_of_{suit}.png"
            create_card_image(suit, rank).save(os.path.join(output_dir, fname), "PNG")

    create_card_back().save(os.path.join(output_dir, "back.png"), "PNG")
    return output_dir


if __name__ == "__main__":
    folder = generate_all_assets()
    print(f"Successfully generated 52 cards + card back in: {folder}")