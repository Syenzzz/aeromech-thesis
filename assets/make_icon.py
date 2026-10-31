# -*- coding: utf-8 -*-
"""生成 aeromech-thesis 技能头像（512x512，平台规范：JPG/PNG，≤500KB）。

三个方案：
    a_gear_plane   齿轮环 + 飞机      —— 机械 + 航空，最直白
    b_plane_doc    飞机 + 文稿行      —— 航空 + 论文，带巧思
    c_ring_plane   细环 + 飞机        —— 极简现代
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512
SS = 4                      # 超采样倍数
W = SIZE * SS
OUT = Path(__file__).resolve().parent / "icons"

NAVY_TOP = (11, 37, 69)
NAVY_BOTTOM = (23, 57, 95)
WHITE = (255, 255, 255)
ACCENT = (110, 198, 255)    # 浅青，做点缀


def rr_mask(size: int, radius: float) -> Image.Image:
    """圆角方形遮罩。"""
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def gradient_bg(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), NAVY_TOP)
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / (size - 1)
        # 轻微非线性，上深下浅更耐看
        t = t ** 0.85
        c = tuple(round(NAVY_TOP[i] + (NAVY_BOTTOM[i] - NAVY_TOP[i]) * t) for i in range(3))
        d.line([(0, y), (size, y)], fill=c)
    return img


def polar(cx: float, cy: float, r: float, a: float) -> tuple[float, float]:
    return (cx + r * math.cos(a), cy + r * math.sin(a))


def gear_polygon(cx, cy, r_out, r_in, teeth, tooth_ratio=0.30, root_ratio=0.26, phase=0.0):
    """梯形齿：齿顶窄、齿根宽。tooth_ratio 是齿顶宽（占一个齿距的比例），
    root_ratio 是齿根侧边起点，必须小于 tooth_ratio/2 的两倍关系才成梯形。"""
    pts = []
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a = phase + i * step
        half = step * tooth_ratio / 2
        pts.append(polar(cx, cy, r_out, a - half))
        pts.append(polar(cx, cy, r_out, a + half))
        # 齿根：从齿两侧向外斜出去，形成梯形齿
        pts.append(polar(cx, cy, r_in, a + step * root_ratio))
        pts.append(polar(cx, cy, r_in, a + step * (1 - root_ratio)))
    return pts


# 飞机俯视轮廓（右半边，机头朝上，归一化坐标）
# 机身加粗、翼尖后掠带小翼感、平尾放大——保证 64px 下仍可辨认
PLANE_HALF = [
    (0.000, -1.000),
    (0.055, -0.930),
    (0.098, -0.760),
    (0.112, -0.300),
    (0.790, -0.130),
    (0.815, 0.010),
    (0.780, 0.060),
    (0.120, 0.120),
    (0.120, 0.430),
    (0.345, 0.640),
    (0.345, 0.745),
    (0.100, 0.715),
    (0.078, 0.880),
    (0.000, 0.930),
]


def plane_polygon(cx, cy, scale, rotation_deg=0.0):
    right = [(x * scale, y * scale) for x, y in PLANE_HALF]
    full = right + [(-x, y) for x, y in reversed(right[:-1])]
    rad = math.radians(rotation_deg)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    out = []
    for x, y in full:
        rx, ry = x * cos_r - y * sin_r, x * sin_r + y * cos_r
        out.append((cx + rx, cy + ry))
    return out


def with_alpha(img: Image.Image, mask_l: Image.Image) -> Image.Image:
    out = img.convert("RGBA")
    out.putalpha(mask_l)
    return out


def draw_a_gear_plane() -> Image.Image:
    """齿轮环 + 白色飞机。厚环体 + 10 齿，保证小尺寸下不糊成噪点。"""
    bg = gradient_bg(W)
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = W / 2

    r_tip = W * 0.420
    r_root = W * 0.372
    r_hole = W * 0.312

    gear = gear_polygon(c, c, r_tip, r_root, teeth=10, tooth_ratio=0.30, root_ratio=0.255)
    d.polygon(gear, fill=WHITE)

    # 挖空齿轮内部，形成厚环
    hole = Image.new("L", (W, W), 255)
    ImageDraw.Draw(hole).ellipse(
        [c - r_hole, c - r_hole, c + r_hole, c + r_hole], fill=0
    )
    layer.putalpha(Image.composite(layer.getchannel("A"), Image.new("L", (W, W), 0), hole))

    plane = plane_polygon(c, c + W * 0.006, W * 0.262)
    d.polygon(plane, fill=WHITE)

    return with_alpha(Image.alpha_composite(bg.convert("RGBA"), layer), rr_mask(W, W * 0.225))


def draw_b_plane_doc() -> Image.Image:
    """飞机 + 下方文稿行，飞机像从文字上起飞。"""
    bg = gradient_bg(W)
    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = W / 2

    plane = plane_polygon(c, W * 0.368, W * 0.262)
    d.polygon(plane, fill=WHITE)

    # 文稿行：前三行等宽，最后一行缩短收尾，模拟段落
    rows = [
        (0.238, 0.672, 0.038, WHITE),
        (0.238, 0.744, 0.038, WHITE),
        (0.238, 0.816, 0.038, WHITE),
    ]
    for half, y, h, color in rows:
        d.rounded_rectangle(
            [c - half * W, y * W, c + half * W, y * W + h * W],
            radius=h * W / 2,
            fill=color,
        )
    # 末行用强调色，短一半，做视觉落点
    d.rounded_rectangle(
        [c - 0.238 * W, 0.888 * W, c - 0.238 * W + 0.300 * W, 0.888 * W + 0.038 * W],
        radius=0.019 * W,
        fill=ACCENT,
    )
    return with_alpha(Image.alpha_composite(bg.convert("RGBA"), layer), rr_mask(W, W * 0.225))


def draw_c_ring_plane() -> Image.Image:
    """细圆环 + 飞机，极简，小尺寸最清晰。"""
    bg = Image.new("RGB", (W, W), (15, 42, 76))
    d0 = ImageDraw.Draw(bg)
    # 径向渐变近似：由外向内逐层提亮
    for i in range(180, 0, -1):
        t = i / 180
        r = t * W * 0.80
        shade = (
            round(9 + (54 - 9) * (1 - t)),
            round(32 + (99 - 32) * (1 - t)),
            round(62 + (145 - 62) * (1 - t)),
        )
        d0.ellipse([W / 2 - r, W / 2 - r, W / 2 + r, W / 2 + r], fill=shade)

    layer = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c = W / 2

    ring_r = W * 0.400
    ring_w = W * 0.031
    d.ellipse(
        [c - ring_r, c - ring_r, c + ring_r, c + ring_r],
        outline=WHITE,
        width=round(ring_w),
    )
    d.arc(
        [c - ring_r, c - ring_r, c + ring_r, c + ring_r],
        start=-58,
        end=22,
        fill=ACCENT,
        width=round(ring_w),
    )

    plane = plane_polygon(c, c + W * 0.006, W * 0.260)
    d.polygon(plane, fill=WHITE)

    return with_alpha(Image.alpha_composite(bg.convert("RGBA"), layer), rr_mask(W, W * 0.225))


def save(img: Image.Image, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    final = img.resize((SIZE, SIZE), Image.LANCZOS)
    png = OUT / f"{name}.png"
    final.save(png, "PNG", optimize=True)
    print(f"  {png.name}  {png.stat().st_size / 1024:.1f} KB")


def main() -> None:
    print("生成技能头像 512x512：")
    names = ["icon-a-gear-plane", "icon-b-plane-doc", "icon-c-ring-plane"]
    save(draw_a_gear_plane(), names[0])
    save(draw_b_plane_doc(), names[1])
    save(draw_c_ring_plane(), names[2])

    # 对比预览：上排 512 缩到 180，下排真实 64px / 44px
    pad, cell = 24, 200
    prev = Image.new("RGBA", (pad * 2 + cell * 3, 330), (247, 248, 250, 255))
    for i, n in enumerate(names):
        x = pad + i * cell
        im = Image.open(OUT / f"{n}.png")
        prev.paste(im.resize((180, 180), Image.LANCZOS), (x + 10, 20), im.resize((180, 180), Image.LANCZOS))
        for j, s in enumerate((64, 44)):
            sm = im.resize((s, s), Image.LANCZOS)
            prev.paste(sm, (x + 20 + j * (s + 16), 230), sm)
    prev.save(OUT / "_preview.png")
    print("  对比预览 -> _preview.png（下排为 64px / 44px 真实尺寸）")


if __name__ == "__main__":
    main()
