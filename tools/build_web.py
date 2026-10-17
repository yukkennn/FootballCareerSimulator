"""Сборка веб-версии для телефона в папку site/ (её и выкладывают на хостинг, например GitHub Pages).

    python tools/build_web.py

site/ = web/ (страница, стили, app.js, service worker, манифест) + game.zip (код игры без десктопного интерфейса и данные)
+ assets/logos (эмблемы) + иконки. Проверить локально: python -m http.server 8000 -d site, затем http://localhost:8000
"""
import shutil, time, zipfile
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
WEB, OUT = ROOT / "web", ROOT / "site"
SKIP_DATA = {"logo_sources.csv"}                     # данные только для сборки базы, игре не нужны

def game_files():
    for p in sorted((ROOT / "game").rglob("*.py")):
        rel = p.relative_to(ROOT)
        if rel.parts[1] == "ui" and p.name not in ("__init__.py", "theme.py"):    # PySide6-экраны в браузере не нужны (theme.py - только цвета)
            continue
        yield p, rel
    for p in sorted((ROOT / "data").iterdir()):
        if p.is_file() and p.suffix in (".db", ".csv") and p.name not in SKIP_DATA:
            yield p, p.relative_to(ROOT)

def main():
    build = time.strftime("%Y%m%d%H%M%S")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for p in WEB.iterdir():
        if p.suffix in (".html", ".js", ".css", ".webmanifest"):
            (OUT / p.name).write_text(p.read_text(encoding="utf-8").replace("__BUILD__", build), encoding="utf-8")
    with zipfile.ZipFile(OUT / "game.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p, rel in game_files():
            z.write(p, rel.as_posix())
    shutil.copytree(ROOT / "assets" / "logos", OUT / "assets" / "logos")
    icon = Image.open(ROOT / "assets" / "icon.png").convert("RGBA")
    for size in (180, 192, 512):
        bg = Image.new("RGBA", (size, size), "#10141a")              # без прозрачности: на iPhone прозрачный фон иконки становится чёрным
        im = icon.resize((round(size * 0.86),) * 2, Image.LANCZOS)
        bg.alpha_composite(im, ((size - im.width) // 2,) * 2)
        bg.convert("RGB").save(OUT / f"icon-{size}.png")
    (OUT / ".nojekyll").write_text("")                                 # GitHub Pages: отдавать файлы как есть
    zs = (OUT / "game.zip").stat().st_size
    print(f"site/ собран (версия {build}), game.zip {zs / 1e6:.1f} МБ")

if __name__ == "__main__":
    main()
