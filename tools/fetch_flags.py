"""Флаги стран (SVG) для всех сборных базы - в assets/flags/<iso2>.svg (gb-eng.svg, de.svg ...).

    python tools/fetch_flags.py

Источник - пакет flag-icons (лицензия MIT, https://github.com/lipis/flag-icons), формат 4x3.
Уже скачанные файлы не перекачиваются.
"""
import sqlite3, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "flags"
URL = "https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/flags/4x3/{}.svg"
LICENSE = """Flags: flag-icons by Panayiotis Lipiridis and contributors, MIT License.
https://github.com/lipis/flag-icons
"""

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "LICENSE.txt").write_text(LICENSE, encoding="utf-8")
    db = sqlite3.connect(ROOT / "data" / "football.db")
    codes = sorted({r[0].lower() for r in db.execute("SELECT iso2 FROM countries")})
    missing = []
    for code in codes:
        f = OUT / f"{code}.svg"
        if f.exists():
            continue
        try:
            with urllib.request.urlopen(URL.format(code), timeout=30) as r:
                data = r.read()
            if not data.lstrip().startswith(b"<svg"):
                raise ValueError("not an svg")
            f.write_bytes(data)
        except Exception as e:                       # noqa: BLE001
            missing.append((code, str(e)))
    total = sum(p.stat().st_size for p in OUT.glob("*.svg"))
    print(f"флагов: {len(list(OUT.glob('*.svg')))}, {total / 1e6:.2f} МБ; не найдены: {missing}")

if __name__ == "__main__":
    main()
