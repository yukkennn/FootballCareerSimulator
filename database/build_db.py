#!/usr/bin/env python3
"""Сборка football.db.

Использование:
    python database/build_db.py --logos-repo PATH/football-logos --openfootball PATH/clubs [--out data/football.db]

Источники (репозитории клонируются командой git clone --depth 1):
    https://github.com/luukhopman/football-logos   (эмблемы + составы высших лиг 25 стран, 2021-22 .. 2026-27)
    https://github.com/openfootball/clubs          (CC0: названия, псевдонимы, город, стадион, год основания)
Остальное лежит в data/: страны FIFA, коэффициенты UEFA (Wikipedia, 17.09.2026), каталог турниров.
"""
import argparse, csv, math, os, re, sqlite3, sys, unicodedata
from pathlib import Path
import difflib
from babel import Locale
from PIL import Image

HERE = Path(__file__).resolve().parent          # database/
ROOT = HERE.parent                                # корень проекта: data/, assets/
SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26", "2026-27"]
CURRENT = "2026-27"

PREFIX_TO_CODE = {
    "Austria": "AUT", "Belgium": "BEL", "Bulgaria": "BUL", "Croatia": "CRO", "Czech Republic": "CZE",
    "Denmark": "DEN", "England": "ENG", "France": "FRA", "Germany": "GER", "Greece": "GRE", "Israel": "ISR",
    "Italy": "ITA", "Netherlands": "NED", "Norway": "NOR", "Poland": "POL", "Portugal": "POR", "Romania": "ROU",
    "Russia": "RUS", "Scotland": "SCO", "Serbia": "SRB", "Spain": "ESP", "Sweden": "SWE", "Switzerland": "SUI",
    "Türkiye": "TUR", "Ukraine": "UKR",
}
# папка openfootball -> код FIFA (только страны, которые есть в базе эмблем)
OF_DIR_TO_CODE = {
    "austria": "AUT", "belgium": "BEL", "bulgaria": "BUL", "croatia": "CRO", "czech-republic": "CZE",
    "denmark": "DEN", "england": "ENG", "france": "FRA", "germany": "GER", "greece": "GRE", "israel": "ISR",
    "italy": "ITA", "netherlands": "NED", "norway": "NOR", "poland": "POL", "portugal": "POR", "romania": "ROU",
    "russia": "RUS", "scotland": "SCO", "serbia": "SRB", "spain": "ESP", "sweden": "SWE", "switzerland": "SUI",
    "turkey": "TUR", "ukraine": "UKR", "wales": "WAL", "andorra": "AND",
}
RU_OVERRIDES = {
    "ENG": "Англия", "SCO": "Шотландия", "WAL": "Уэльс", "NIR": "Северная Ирландия", "TPE": "Китайский Тайбэй",
    "COD": "ДР Конго", "CGO": "Конго", "TAH": "Таити", "PLE": "Палестина", "HKG": "Гонконг", "MAC": "Макао",
    "MYA": "Мьянма", "KOS": "Косово", "CPV": "Кабо-Верде", "VIR": "Американские Виргинские острова",
    "VGB": "Британские Виргинские острова", "IRL": "Ирландия", "USA": "США", "KOR": "Южная Корея", "RSA": "ЮАР", "CZE": "Чехия", "TUR": "Турция",
}
CONF_NAMES = {
    "UEFA": ("Union of European Football Associations", "УЕФА (Европа)"),
    "CAF": ("Confederation of African Football", "КАФ (Африка)"),
    "AFC": ("Asian Football Confederation", "АФК (Азия)"),
    "CONMEBOL": ("South American Football Confederation", "КОНМЕБОЛ (Южная Америка)"),
    "CONCACAF": ("Confederation of North, Central America and Caribbean Association Football", "КОНКАКАФ (Северная и Центральная Америка)"),
    "OFC": ("Oceania Football Confederation", "ОФК (Океания)"),
}

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|afc|cf|fk|sk|sc|ac|as|ss|us|ud|cd|rcd|ca|bsc|sv|vfb|vfl|tsg|fsv|1\.)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)

def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def parse_openfootball(root: Path):
    """-> {code: [ {name, founded, stadium, city, names:set(norm)} ]}"""
    out = {}
    for d, code in OF_DIR_TO_CODE.items():
        base = root / "europe" / d
        if d == "israel":
            base = root / "middle-east" / d
        if not base.exists():
            continue
        entries = []
        for f in sorted(base.glob("*.clubs.txt")):
            cur = None
            for raw in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.rstrip()
                if not line.strip() or line.lstrip().startswith(("#", "=")):
                    continue
                if line.lstrip().startswith("|"):
                    if cur is not None:
                        for a in line.split("#")[0].split("|")[1:]:
                            a = a.strip()
                            if a:
                                cur["aliases"].append(a)
                    continue
                if line.startswith((" ", "\t")):
                    continue
                body = line.split("##")[0]
                parts = [p.strip() for p in body.split(",")]
                name = parts[0]
                founded = next((int(p) for p in parts[1:] if re.fullmatch(r"\d{4}", p)), None)
                stadium, city = None, None
                m = re.search(r"@\s*([^,]+),\s*([^,(#]+)", body)
                if m:
                    stadium, city = m.group(1).strip(), m.group(2).split("›")[0].strip()
                cur = {"name": name, "founded": founded, "stadium": stadium, "city": city, "aliases": []}
                entries.append(cur)
        out[code] = entries
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logos-repo", required=True)
    ap.add_argument("--openfootball", required=True)
    ap.add_argument("--out", default=str(ROOT / "data" / "football.db"))
    a = ap.parse_args()
    logos_repo, of_root, out = Path(a.logos_repo), Path(a.openfootball), Path(a.out)

    if out.exists():
        out.unlink()
    db = sqlite3.connect(out)
    db.executescript((HERE / "schema.sql").read_text(encoding="utf-8"))
    db.execute("PRAGMA foreign_keys=ON")

    # --- конфедерации, страны
    for code, (en, ru) in CONF_NAMES.items():
        db.execute("INSERT INTO confederations VALUES (?,?,?)", (code, en, ru))
    ru = Locale("ru")
    coeff = {r["fifa_code"]: float(r["coefficient_5y"]) for r in csv.DictReader(open(ROOT / "data/uefa_association_coefficients.csv", encoding="utf-8"))}
    top = max(coeff.values())
    for r in csv.DictReader(open(ROOT / "data/fifa_members.csv", encoding="utf-8")):
        c = r["fifa_code"]
        name_ru = RU_OVERRIDES.get(c) or re.sub(r"\s*\(.*?\)", "", ru.territories.get(r["iso2"], r["name_en"]))
        ls = round(100 * math.sqrt(coeff[c] / top), 1) if c in coeff else None
        db.execute("INSERT INTO countries VALUES (?,?,?,?,?,?,?,?)",
                   (c, r["iso2"], r["name_en"], name_ru, r["confederation"], coeff.get(c), ls, None))

    # --- соревнования
    for r in csv.DictReader(open(ROOT / "data/competitions.csv", encoding="utf-8")):
        db.execute("INSERT INTO competitions VALUES (?,?,?,?,?,?,?,?,?)",
                   (r["code"], r["name_en"], r["name_ru"], r["kind"], r["confederation"] or None,
                    int(r["tier"]), int(r["cycle_years"]), int(r["next_edition_year"]), r["note"] or None))

    # --- лиги и клубы текущего сезона
    of = parse_openfootball(of_root)
    of_primary = {c: {} for c in of}
    of_alias = {c: {} for c in of}
    for c, entries in of.items():
        for e in entries:
            of_primary[c].setdefault(norm(e["name"]), e)
            for n in e["aliases"]:
                of_alias[c].setdefault(norm(n), []).append(e)
    used_entries = set()

    def lookup(code, name):
        """Точное совпадение основного названия; иначе однозначный псевдоним. Один справочник-клуб = один клуб."""
        k = norm(name)
        e = of_primary.get(code, {}).get(k)
        if e is None:
            cands = {id(x): x for x in of_alias.get(code, {}).get(k, [])}
            if len(cands) == 1 and k not in of_primary.get(code, {}):
                e = next(iter(cands.values()))
        if e is None or id(e) in used_entries:
            return None
        used_entries.add(id(e))
        return e

    cur_dir = logos_repo / "logos"
    logo_out = ROOT / "assets" / "logos"
    logo_out.mkdir(parents=True, exist_ok=True)
    for f in logo_out.glob("*.png"):
        f.unlink()
    club_by_key = {}   # (code, norm name) -> club_id
    all_logo_names = {}   # code -> {norm(stem): Path}; свежие сезоны имеют приоритет
    matched = 0
    for league_dir in sorted(p for p in cur_dir.iterdir() if p.is_dir()):
        prefix, league_name = [x.strip() for x in league_dir.name.split(" - ", 1)]
        code = PREFIX_TO_CODE[prefix]
        lid = f"{code.lower()}-{slug(league_name)}"
        files = sorted(league_dir.glob("*.png"))
        db.execute("INSERT INTO leagues (league_id,country_code,name,tier,n_clubs,source) VALUES (?,?,?,?,?,?)", (lid, code, league_name, 1, len(files), "luukhopman/football-logos 2026-27"))
        for f in files:
            name = f.stem
            cid = f"{code.lower()}-{slug(name)}"
            ent = lookup(code, name)
            if ent:
                matched += 1
            img = Image.open(f).convert("RGBA")
            h = 96
            img = img.resize((max(1, round(img.width * h / img.height)), h), Image.LANCZOS)
            img.save(logo_out / f"{cid}.png", optimize=True)
            db.execute("INSERT INTO clubs (club_id,name,country_code,league_id,city,stadium,founded,logo_path,source) VALUES (?,?,?,?,?,?,?,?,?)",
                       (cid, name, code, lid, ent and ent["city"], ent and ent["stadium"], ent and ent["founded"],
                        f"assets/logos/{cid}.png", "luukhopman/football-logos"))
            all_logo_names.setdefault(code, {}).setdefault(norm(name), f)
            club_by_key[(code, norm(name))] = cid
            db.execute("INSERT OR IGNORE INTO club_aliases VALUES (?,?,?)", (name, cid, "logos"))
            if ent:
                for al in [ent["name"]] + ent["aliases"]:
                    db.execute("INSERT OR IGNORE INTO club_aliases VALUES (?,?,?)", (al, cid, "openfootball"))

    # --- эмблемы из всех сезонов (свежие первыми): нужны клубам, которые сейчас играют ниже высшего дивизиона
    for s_ in [CURRENT] + SEASONS[:-1][::-1]:
        base = cur_dir if s_ == CURRENT else logos_repo / "history" / s_
        if not base.exists():
            continue
        for league_dir in sorted(base.iterdir()):
            if league_dir.is_dir() and " - " in league_dir.name:
                lc = PREFIX_TO_CODE.get(league_dir.name.split(" - ")[0].strip())
                if lc:
                    for f in league_dir.glob("*.png"):
                        all_logo_names.setdefault(lc, {}).setdefault(norm(f.stem), f)

    # --- дополнительные лиги и клубы: 2-4 дивизионы топ-5 стран (Англия до 4-го) и Казахстан
    xleagues = {r["league_id"]: r for r in csv.DictReader(open(ROOT / "data/extra_leagues.csv", encoding="utf-8"))}
    xclubs = list(csv.DictReader(open(ROOT / "data/extra_clubs.csv", encoding="utf-8")))
    per_league = {}
    for r in xclubs:
        per_league[r["league_id"]] = per_league.get(r["league_id"], 0) + 1
    for lid, r in xleagues.items():
        db.execute("INSERT INTO leagues (league_id,country_code,name,tier,n_clubs,source) VALUES (?,?,?,?,?,?)",
                   (lid, r["country_code"], r["name"], int(r["tier"]), per_league[lid], "Wikipedia/сайты лиг и клубов, сверено 2026-10-01"))
    n_new = n_logo = 0
    for r in xclubs:
        lcode = xleagues[r["league_id"]]["country_code"]
        ccode = r["club_country"] or lcode
        name = r["name"]
        cid = f"{ccode.lower()}-{slug(name)}"
        if db.execute("SELECT 1 FROM clubs WHERE club_id=?", (cid,)).fetchone():
            print("  ! дубликат клуба:", cid, file=sys.stderr)
            continue
        ent = lookup(lcode, name) or (lookup(ccode, name) if ccode != lcode else None)
        pool = all_logo_names.get(lcode, {})
        tries = [norm(name)] + ([norm(ent["name"])] + [norm(x) for x in ent["aliases"]] if ent else [])
        src = next((pool[k] for k in tries if k in pool), None)
        if src is None and pool:
            close = difflib.get_close_matches(norm(name), list(pool), n=1, cutoff=0.9)
            src = pool[close[0]] if close else None
        if r["is_reserve"] == "1":
            src = None          # у фарм-клубов своей эмблемы в источнике нет; эмблему основной команды не подставляем
        logo_path = None
        if src is not None:
            img = Image.open(src).convert("RGBA")
            img = img.resize((max(1, round(img.width * 96 / img.height)), 96), Image.LANCZOS)
            img.save(logo_out / f"{cid}.png", optimize=True)
            logo_path = f"assets/logos/{cid}.png"; n_logo += 1
            if os.environ.get("DEBUG_LOGOS"):
                print(f"    логотип: {name!r} <- {src.parent.name} / {src.name}")
        db.execute("INSERT INTO clubs (club_id,name,country_code,league_id,city,stadium,founded,is_reserve,logo_path,source) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (cid, name, ccode, r["league_id"], ent and ent["city"], ent and ent["stadium"], ent and ent["founded"],
                    int(r["is_reserve"]), logo_path, "wikipedia+openfootball"))
        db.execute("INSERT OR IGNORE INTO club_aliases VALUES (?,?,?)", (name, cid, "list"))
        if ent:
            for al in [ent["name"]] + ent["aliases"]:
                db.execute("INSERT OR IGNORE INTO club_aliases VALUES (?,?,?)", (al, cid, "openfootball"))
        club_by_key[(lcode, norm(name))] = cid
        n_new += 1
    print(f"  доп. лиги: {len(xleagues)} | клубов добавлено: {n_new} | с эмблемой: {n_logo}")

    # --- история высшего дивизиона по сезонам (из эмблем); точное название приоритетнее псевдонима
    by_name, by_alias = {}, {}
    for cid, lcode, nm in db.execute("SELECT c.club_id, l.country_code, c.name FROM clubs c JOIN leagues l USING(league_id)"):
        by_name.setdefault((lcode, norm(nm)), set()).add(cid)
    for cid, lcode, al in db.execute("SELECT a.club_id, l.country_code, a.alias FROM club_aliases a JOIN clubs c USING(club_id) JOIN leagues l USING(league_id)"):
        by_alias.setdefault((lcode, norm(al)), set()).add(cid)

    def resolve(code, stem):
        k = (code, norm(stem))
        if len(by_name.get(k, ())) == 1:
            return next(iter(by_name[k]))
        if not by_name.get(k) and len(by_alias.get(k, ())) == 1:
            return next(iter(by_alias[k]))
        return None

    def add_season(season, base):
        for league_dir in base.iterdir():
            if not league_dir.is_dir() or " - " not in league_dir.name:
                continue
            code = PREFIX_TO_CODE.get(league_dir.name.split(" - ")[0].strip())
            if not code:
                continue
            for f in league_dir.glob("*.png"):
                cid = resolve(code, f.stem)
                if cid:
                    db.execute("INSERT OR IGNORE INTO club_top_flight_history VALUES (?,?)", (cid, season))
    for s in SEASONS[:-1]:
        add_season(s, logos_repo / "history" / s)
    add_season(CURRENT, cur_dir)
    for cid, n in db.execute("SELECT club_id, COUNT(*) FROM club_top_flight_history GROUP BY club_id").fetchall():
        db.execute("INSERT INTO club_signals VALUES (?,?,?,?)", (cid, "top_flight_seasons", n, CURRENT))

    # --- запасные академии для стран без клубов
    for r in csv.DictReader(open(ROOT / "data/academy_fallback.csv", encoding="utf-8")):
        db.execute("UPDATE countries SET fallback_academy_country=? WHERE fifa_code=?", (r["fallback_country"], r["fifa_code"]))

    # --- коэффициенты UEFA топ-25 клубов
    for r in csv.DictReader(open(ROOT / "data/uefa_club_coefficients.csv", encoding="utf-8")):
        code = r["fifa_code"]
        rows = db.execute("SELECT club_id FROM club_aliases WHERE alias=? COLLATE NOCASE AND club_id LIKE ?", (r["club_name"], code.lower() + "-%")).fetchall()
        cid = rows[0][0] if rows else club_by_key.get((code, norm(r["club_name"])))
        if cid:
            db.execute("INSERT INTO club_signals VALUES (?,?,?,?)", (cid, "uefa_club_coeff", float(r["coefficient_5y"]), r["as_of"]))
        else:
            print("  ! нет сопоставления для UEFA-клуба:", r["club_name"], file=sys.stderr)

    for r in csv.DictReader(open(ROOT / "data/manual_star_seed.csv", encoding="utf-8")):
        if db.execute("SELECT 1 FROM clubs WHERE club_id=?", (r["club_id"],)).fetchone():
            db.execute("INSERT OR REPLACE INTO club_signals VALUES (?,?,?,?)", (r["club_id"], "manual_stars", float(r["stars"]), CURRENT))
        else:
            print("  ! manual seed: нет клуба", r["club_id"], file=sys.stderr)

    meta = {"schema_version": "2", "built_for_season": CURRENT, "countries": "211 FIFA members",
            "uefa_coeff_as_of": "2026-09-17", "openfootball_matched_clubs": str(matched)}
    db.executemany("INSERT INTO meta VALUES (?,?)", meta.items())
    db.commit()

    sys.path.insert(0, str(HERE))
    import recompute_stars
    recompute_stars.run(db)
    db.commit(); db.execute("VACUUM"); db.close()
    # рейтинги EA FC 27, новые лиги (MLS, Бразилия, Аргентина, Саудовская Аравия ...), оценки клубов без рейтинга FC
    sys.path.insert(0, str(HERE / "importers"))
    import import_fc27
    import_fc27.main(str(out))
    print(f"OK -> {out} ({out.stat().st_size/1024:.0f} KB)")

if __name__ == "__main__":
    main()
