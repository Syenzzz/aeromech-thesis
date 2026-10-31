# -*- coding: utf-8 -*-
"""生成 aeromech-thesis 技能新头像（512x512，平台规范：JPG/PNG，≤500KB）。

三个新方案（与 icons/ 下旧的飞机剪影方案区分开）：
    avatar-a-green-badge  深绿渐变 + 白色「航」+ 论文行   —— 中文标识 + 论文语义
    avatar-b-green-light  浅绿底 + 深绿「航」+ 细边框     —— 延续现有头像调性，更精致
    avatar-c-navy-seal    深蓝渐变 + 环形「航」+ 机翼弧   —— 徽章感，最沉稳

设计约束：
    - 只在 40~64px 下仍能辨认的强剪影，不要细节；
    - 单字 + 一处强调色，配色不超过 3 色；
    - 超采样 4 倍绘制再缩到 512，保证边缘锐利。
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 512
SS = 4
W = SIZE * SS
OUT = Path(__file__).resolve().parent / "icons"

FONT_HEI = "C:/Windows/Fonts/simhei.ttf"
FONT_YAHEI = "C:/Windows/Fonts/msyhbd.ttc"

WHITE = (255, 255, 255)
GOLD = (242, 193, 78)
MINT = (111, 227, 168)

# 深绿
GREEN_TOP = (10, 74, 50)
GREEN_BOTTOM = (23, 122, 79)
# 浅绿
LIGHT_TOP = (241, 250, 245)
LIGHT_BOTTOM = (203, 233, 213)
# 深蓝
NAVY_TOP = (11, 37, 69)
NAVY_BOTTOM = (23, 57, 95)


def rr_mask(size: int, radius: float) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def vgrad(size: int, top: tuple, bottom: tuple, gamma: float = 0.9) -> Image.Image:
    """竖直渐变，gamma<1 让上半段变化更缓，避免上缘发闷。"""
    img = Image.new("RGB", (size, size), top)
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = (y / (size - 1)) ** gamma
        d.line([(0, y), (size, y)], fill=tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


def glyph(text: str, font_path: str, box: float, center=(0.5, 0.5), canvas: int = W) -> Image.Image:
    """按「墨迹外框」居中排版单字，返回与原画布同样大的透明图层。"""
    font = ImageFont.truetype(font_path, int(box))
    layer = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    x0, y0, x1, y1 = font.getbbox(text)
    cx = center[0] * canvas - (x0 + x1) / 2
    cy = center[1] * canvas - (y0 + y1) / 2
    ImageDraw.Draw(layer).text((cx, cy), text, font=font, fill=WHITE)
    return layer


def recolor(layer: Image.Image, color: tuple) -> Image.Image:
    """把白色字形图层整体染色，保留 alpha。"""
    out = Image.new("RGBA", layer.size, color + (0,))
    out.putalpha(layer.getchannel("A"))
    return out


def compose(bg: Image.Image, *layers: Image.Image) -> Image.Image:
    base = bg.convert("RGBA")
    for l in layers:
        base = Image.alpha_composite(base, l)
    return base


def bar(d: ImageDraw.ImageDraw, cx: float, y: float, half_w: float, h: float, color: tuple) -> None:
    d.rounded_rectangle([cx - half_w, y, cx + half_w, y + h], radius=h / 2, fill=color)


def wing_swoosh(cx: float, cy: float, half_w: float, thickness: float, color: tuple) -> Image.Image:
    """两段对称后掠线，构成机翼感，用作强调笔。"""
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    lift = half_w * 0.30
    d.line(
        [(cx - half_w, cy + lift), (cx, cy - lift * 0.55)],
        fill=color, width=round(thickness), joint="curve",
    )
    d.line(
        [(cx, cy - lift * 0.55), (cx + half_w, cy + lift)],
        fill=color, width=round(thickness), joint="curve",
    )
    r = thickness / 2
    for p in [(cx - half_w, cy + lift), (cx, cy - lift * 0.55), (cx + half_w, cy + lift)]:
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color)
    return layer


def a_green_badge() -> Image.Image:
    """深绿渐变 + 白色「航」，底部一道金色机翼弧收尾。"""
    bg = vgrad(W, GREEN_TOP, GREEN_BOTTOM, gamma=0.95)
    text = glyph("航", FONT_HEI, W * 0.575, center=(0.5, 0.445))
    swoosh = wing_swoosh(W / 2, W * 0.792, W * 0.178, W * 0.033, GOLD + (255,))
    return compose(bg, text, swoosh)


def b_green_light() -> Image.Image:
    """浅绿底 + 深绿「航」+ 内描边，最贴近现在这版但更讲究。"""
    bg = vgrad(W, LIGHT_TOP, LIGHT_BOTTOM, gamma=1.1)
    text = recolor(glyph("航", FONT_HEI, W * 0.580, center=(0.5, 0.500)), GREEN_BOTTOM)
    frame = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    inset = W * 0.082
    d.rounded_rectangle(
        [inset, inset, W - inset, W - inset],
        radius=W * 0.105, outline=GREEN_BOTTOM + (72,), width=round(W * 0.010),
    )
    return compose(bg, text, frame)


def c_navy_seal() -> Image.Image:
    """深蓝 + 细环切一段金色弧 + 白色「航」，徽章气质。"""
    bg = vgrad(W, NAVY_TOP, NAVY_BOTTOM, gamma=0.9)
    ring = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    c = W / 2
    r = W * 0.392
    w = round(W * 0.021)
    box = [c - r, c - r, c + r, c + r]
    d.ellipse(box, outline=(255, 255, 255, 205), width=w)
    # 右上留缺口，用金色补一段，形成「刻度环」的暗示
    d.arc(box, start=-70, end=20, fill=GOLD + (255,), width=w)
    text = glyph("航", FONT_HEI, W * 0.380, center=(0.5, 0.508))
    return compose(bg, ring, text)


def save(img: Image.Image, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    # 先按超采样尺寸切圆角再缩放，边缘才干净
    masked = img.convert("RGBA")
    masked.putalpha(rr_mask(W, W * 0.225))
    final = masked.resize((SIZE, SIZE), Image.LANCZOS)
    png = OUT / f"{name}.png"
    final.save(png, "PNG", optimize=True)
    print(f"  {png.name}  {png.stat().st_size / 1024:.1f} KB  {final.size[0]}x{final.size[1]}")
    return png


def main() -> None:
    print("生成新头像 512x512：")
    items = [
        ("avatar-a-green-badge", a_green_badge()),
        ("avatar-b-green-light", b_green_light()),
        ("avatar-c-navy-seal", c_navy_seal()),
    ]
    for name, img in items:
        save(img, name)

    # 对比预览：上排 180，下排 64 / 44 真实尺寸，浅底深底各一版
    pad, cell = 26, 210
    prev = Image.new("RGB", (pad * 2 + cell * 3, 420), (247, 248, 250))
    for i, (name, _) in enumerate(items):
        x = pad + i * cell
        im = Image.open(OUT / f"{name}.png")
        big = im.resize((170, 170), Image.LANCZOS)
        prev.paste(big, (x + 12, 26), big)
        for j, s in enumerate((64, 44)):
            sm = im.resize((s, s), Image.LANCZOS)
            prev.paste(sm, (x + 16 + j * (s + 18), 220), sm)
        # 深色底再看一眼 44px，验证深底上的对比
        dark = Image.new("RGB", (150, 76), (32, 36, 44))
        sm = im.resize((44, 44), Image.LANCZOS)
        dark.paste(sm, (12, 16), sm)
        prev.paste(dark, (x + 12, 306))
    prev.save(OUT / "_avatar_preview.png")
    print("  预览 -> _avatar_preview.png（下排 64/44px，最后一排为深色底 44px）")


if __name__ == "__main__":
    main()
