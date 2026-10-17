"""Иконка игры: футбольный мяч на зелёном круге. Создаёт assets/icon.ico (для .exe и окна) и assets/icon.png.
Запуск: python tools/make_icon.py   (нужен Pillow: pip install pillow)"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
S = 512                                    # рисуем крупно, потом уменьшаем - края гладкие

def polygon(cx, cy, r, n=5, rot=-90):
    return [(cx + r * math.cos(math.radians(rot + 360 * k / n)), cy + r * math.sin(math.radians(rot + 360 * k / n))) for k in range(n)]

def draw():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, S - 8, S - 8), fill=(31, 158, 92, 255))                     # зелёный фон (цвет кнопок игры)
    c, R = S / 2, S * 0.36
    d.ellipse((c - R, c - R, c + R, c + R), fill=(250, 250, 250, 255), outline=(20, 24, 30, 255), width=10)
    # центральный пятиугольник и пять «лучей» к краю мяча
    pr = R * 0.36
    center = polygon(c, c, pr)
    d.polygon(center, fill=(20, 24, 30, 255))
    for k, (x, y) in enumerate(center):
        a = math.radians(-90 + 72 * k)
        ex, ey = c + R * 0.78 * math.cos(a), c + R * 0.78 * math.sin(a)
        d.line((x, y, ex, ey), fill=(20, 24, 30, 255), width=12)
        # кусочки соседних пятиугольников у края мяча
        d.polygon(polygon(c + R * 0.98 * math.cos(a), c + R * 0.98 * math.sin(a), pr * 0.75, rot=-90 + 72 * k + 36),
                  fill=(20, 24, 30, 255))
    # подрезаем всё, что вылезло за мяч, оставляя зелёный круг
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((c - R, c - R, c + R, c + R), fill=255)
    ball = Image.composite(img, Image.new("RGBA", (S, S), (0, 0, 0, 0)), mask)
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(base).ellipse((8, 8, S - 8, S - 8), fill=(31, 158, 92, 255))
    base.alpha_composite(ball)
    ImageDraw.Draw(base).ellipse((c - R, c - R, c + R, c + R), outline=(20, 24, 30, 255), width=10)
    return base

if __name__ == "__main__":
    img = draw()
    out = ROOT / "assets"
    img.resize((256, 256), Image.LANCZOS).save(out / "icon.png")
    img.save(out / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("assets/icon.ico, assets/icon.png")
