#!/usr/bin/env python3
"""Докачка недостающих эмблем клубов: TheSportsDB (бесплатный ключ 123), затем Викиданные (свойство «логотип», файлы Викисклада).

    python tools/fetch_logos.py data/football.db [--max N] [--sleep 2.2] [--api URL] [--sources tsdb,wikidata] [--dry-run]

Как ищется клуб:
  1. TheSportsDB, поиск по названию клуба и по его альтернативным названиям из базы (club_aliases). Результат подходит, только если
     страна команды на сайте совпадает со страной клуба или страной его лиги (Дерри Сити - Северная Ирландия, лига Ирландии)
     и названия похожи (после отбрасывания FC, FK, SC и т.п.).
  2. Викиданные: поиск элемента по названию, нужен футбольный клуб (P31) из той же страны (P17, сверка по коду ISO) с логотипом (P154).
     Картинка берётся с Викисклада в PNG.
Один и тот же клуб с сайта (или одна и та же картинка) достаётся только одному клубу базы - тому, у кого совпадение лучше:
так «Omonia Nicosia» не получит эмблему «Omonia 29M», а «Arsenal Tivat» - эмблему лондонского «Арсенала».

Эмблема приводится к высоте 96 px и сохраняется в assets/logos/<club_id>.png. Ответы сайтов кешируются (tools/.logo_cache),
повторный запуск пропускает клубы, у которых эмблема уже есть. Что откуда взято - в data/logo_sources.csv.
Эмблемы - товарные знаки клубов; в проекте они используются как есть (личный проект).
"""
import argparse, csv, difflib, hashlib, io, json, re, sqlite3, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, PngImagePlugin
PngImagePlugin.MAX_TEXT_CHUNK = 64 * 1024 * 1024        # у некоторых эмблем в PNG огромные текстовые блоки (метаданные редакторов)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "database" / "importers"))
from common import norm

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "football-career-sim/1.0 (personal project; club logo fetcher)"}
# как страны называются на TheSportsDB, если не так, как name_en в базе
TSDB_ALIASES = {"USA": {"united states", "usa"}, "IRL": {"ireland", "republic of ireland"}, "KOR": {"south korea", "korea republic", "korea"},
                "CZE": {"czech republic", "czechia"}, "TUR": {"turkey", "türkiye", "turkiye"}, "BIH": {"bosnia-herzegovina", "bosnia and herzegovina"},
                "MKD": {"north macedonia", "macedonia", "fyr macedonia"}, "CHN": {"china", "china pr"}, "KSA": {"saudi arabia"},
                "NED": {"netherlands", "holland"}, "CIV": {"ivory coast", "côte d'ivoire"}, "RUS": {"russia"}, "MDA": {"moldova"},
                "FRO": {"faroe islands"}, "NIR": {"northern ireland"}, "KOS": {"kosovo"}, "ENG": {"england"}, "WAL": {"wales"},
                "SCO": {"scotland"}, "AUS": {"australia"}, "NZL": {"new zealand"}, "CAN": {"canada"}, "GEO": {"georgia"}}
# молодёжные, резервные и женские команды: их эмблему основной команде не берём (слова, которых нет в названии клуба базы)
JUNK = {"women", "womens", "ladies", "femenino", "feminino", "feminin", "feminines", "frauen", "reserves", "reserve", "youth", "academy",
        "akademija", "u17", "u18", "u19", "u20", "u21", "u23", "ii", "iii", "b", "c", "2", "w"}
# найденное оказалось другим клубом с похожим названием (проверено вручную по data/logo_sources.csv)
EXCLUDE = {("arg-central-cordoba", "Central Córdoba de Rosario")}
# клубы, которые автоматический поиск не находит (короткие или неоднозначные названия): статья английской Википедии задана явно
MANUAL_WIKI = {
    "aze-neftci": "Neftçi PFK", "aze-qabala": "Gabala FC", "chi-colo-colo": "Colo-Colo", "chi-o-higgins": "O'Higgins F.C.",
    "fro-hb": "Havnar Bóltfelag", "fro-ki": "KÍ Klaksvík", "gib-st-joseph-s": "St Joseph's F.C.",
    "irl-st-patrick-s-athletic": "St Patrick's Athletic F.C.", "isl-fh": "Fimleikafélag Hafnarfjarðar",
    "kaz-irtysh": "ru:Иртыш (футбольный клуб, Павлодар)", "kaz-kaspiy": "ru:Каспий (футбольный клуб, Актау)",   # в английской статье эмблемы нет
    "ksa-abha-club": "Abha Club", "lva-auda": "lv:FK Auda", "mlt-birzebbuga-st-peter-s": "Birżebbuġa St. Peter's F.C.",
    "par-nacional-asuncion": "Club Nacional", "per-adt-tarma": "Asociación Deportiva Tarma", "smr-juvenes-dogana": "S.S. Juvenes/Dogana",
    "svn-nafta-1903": "NK Nafta 1903", "wal-cardiff-met": "Cardiff Metropolitan University F.C.", "wal-the-new-saints": "The New Saints F.C.",
    "usa-minnesota-united-fc": "Minnesota United FC",
}
FOOTBALL_CLUB_QIDS ={"Q476028", "Q103229495", "Q847017", "Q15944511", "Q17270000", "Q21290861", "Q1478437"}   # футбольный клуб и близкие типы

class Fetcher:
    def __init__(self, cache_dir, sleep):
        self.cache, self.sleep = Path(cache_dir), sleep
        self.cache.mkdir(parents=True, exist_ok=True)

    def json(self, url, polite=None):
        key = self.cache / (hashlib.sha1(url.encode()).hexdigest() + ".json")
        if key.exists():
            return json.loads(key.read_text(encoding="utf-8"))
        last = None
        for i in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                    data = json.load(r)
                key.write_text(json.dumps(data), encoding="utf-8")
                time.sleep(self.sleep if polite is None else polite)
                return data
            except urllib.error.HTTPError as e:                 # 429: ждём столько, сколько просит сервер
                last = e
                wait = e.headers.get("Retry-After") if e.code == 429 else None
                time.sleep(min(120, int(wait)) if wait and wait.isdigit() else 15 * (i + 1))
            except Exception as e:                              # сеть
                last = e
                time.sleep(5 * (i + 1))
        print("   ошибка запроса:", url[:120], last, file=sys.stderr)
        return None

def similarity(db_name, site_name):
    """Похожесть названий 0..1. Название из базы целиком внутри названия на сайте («Kairat» / «Kairat Almaty») - 0.9;
    название с сайта внутри нашего («Zalgiris» / «Zalgiris Vilnius») - 0.86, если оно не слишком короткое."""
    a, b = norm(db_name), norm(site_name)
    if not a or not b:
        return 0.0
    r = difflib.SequenceMatcher(None, a, b).ratio()
    if len(a) >= 4 and a in b:
        r = max(r, 0.9 + 0.01 * r)                  # + доля похожести: при равенстве выигрывает более близкое название
    elif len(b) >= 6 and b in a:
        r = max(r, 0.86 + 0.01 * r)
    return r

def words(s):
    return set(re.sub(r"[^\w]+", " ", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).split())

def is_junk(db_name, site_name):
    """Команда сайта - молодёжная, резервная или женская версия клуба (Kapaz II, Partizani B, Minnesota United FC 2, ... Women)."""
    return bool((words(site_name) - words(db_name)) & JUNK) or re.search(r"-\s*2\b", site_name or "") is not None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db"); ap.add_argument("--max", type=int, default=100_000)
    ap.add_argument("--sleep", type=float, default=2.2, help="пауза между запросами к TheSportsDB (бесплатный ключ ~30 в минуту)")
    ap.add_argument("--api", default="https://www.thesportsdb.com/api/v1/json/123")
    ap.add_argument("--sources", default="tsdb,wikidata")
    ap.add_argument("--cache", default=str(ROOT / "tools/.logo_cache"))
    ap.add_argument("--min-score", type=float, default=0.85)
    ap.add_argument("--dry-run", action="store_true", help="только найти и записать отчёт, без скачивания")
    a = ap.parse_args()
    sources = set(a.sources.split(","))
    db = sqlite3.connect(a.db)
    countries = {c: (n or "", (iso or "").upper()) for c, n, iso in db.execute("SELECT fifa_code, name_en, iso2 FROM countries")}
    todo = db.execute("""SELECT c.club_id, c.name, c.country_code, COALESCE(l.country_code, c.country_code) FROM clubs c
                         LEFT JOIN leagues l USING(league_id) WHERE c.logo_path IS NULL AND c.is_reserve=0 ORDER BY c.club_id LIMIT ?""",
                      (a.max,)).fetchall()
    aliases = {}
    for alias, cid in db.execute("SELECT alias, club_id FROM club_aliases"):
        aliases.setdefault(cid, []).append(alias)
    f = Fetcher(a.cache, a.sleep)

    def tsdb_names(code):
        return {countries[code][0].lower()} | TSDB_ALIASES.get(code, set())

    cands = {}                                   # club_id -> [(score, ключ команды на сайте, url картинки, название на сайте, источник)]
    # --- 1. TheSportsDB
    if "tsdb" in sources:
        for k, (cid, name, cc, lc) in enumerate(todo, 1):
            ok = tsdb_names(cc) | tsdb_names(lc)
            queries = [name] + [x for x in aliases.get(cid, []) if norm(x) != norm(name)][:2]
            for q in queries:
                data = f.json(f"{a.api}/searchteams.php?t={urllib.parse.quote(q)}")
                for t in (data or {}).get("teams") or []:
                    if (t.get("strSport") or "Soccer").lower() != "soccer" or (t.get("strCountry") or "").lower() not in ok:
                        continue
                    url = t.get("strBadge") or t.get("strTeamBadge")
                    if not url or is_junk(name, t.get("strTeam")) or (cid, t.get("strTeam")) in EXCLUDE:
                        continue
                    s = max(similarity(n, t.get(fld) or "") for n in (name, q) for fld in ("strTeam", "strTeamShort", "strAlternate"))
                    if s >= a.min_score:
                        cands.setdefault(cid, []).append((s, "tsdb:" + str(t.get("idTeam") or t.get("strTeam")), url, t.get("strTeam"), "TheSportsDB"))
                if cands.get(cid) and max(x[0] for x in cands[cid]) >= 0.95:
                    break
            if k % 50 == 0:
                print(f"   TheSportsDB: {k}/{len(todo)}, найдено {len(cands)}", flush=True)

    # --- 2. Викиданные (для тех, кого не нашёл TheSportsDB)
    if "wikidata" in sources:
        iso_of_qid = {}
        rest = [x for x in todo if x[0] not in cands]
        for k, (cid, name, cc, lc) in enumerate(rest, 1):
            want = {countries[cc][1], countries[lc][1]} - {""}
            if cc in ("ENG", "WAL", "SCO", "NIR"):
                want.add("GB")
            # кандидаты: поиск в Викиданных по названию, затем полнотекстовый поиск статьи в английской Википедии
            # («HB football club Faroe Islands») - для коротких и неоднозначных названий
            ids, relaxed = [], set()
            for q in (name, f"{name} FC"):
                s = f.json("https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=en&type=item&limit=7&search="
                           + urllib.parse.quote(q), polite=1.5)
                ids += [x["id"] for x in (s or {}).get("search", []) if x["id"] not in ids]
            sr = f.json("https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srlimit=3&srsearch="
                        + urllib.parse.quote(f"{name} football club {countries[cc][0]}"), polite=1.5) or {}
            titles = [x["title"] for x in (sr.get("query") or {}).get("search", [])]
            if titles:
                pp = f.json("https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageprops&ppprop=wikibase_item&redirects=1&titles="
                            + urllib.parse.quote("|".join(titles)), polite=1.5) or {}
                for pg in ((pp.get("query") or {}).get("pages") or {}).values():
                    q = (pg.get("pageprops") or {}).get("wikibase_item")
                    if q and q not in ids:
                        ids.append(q); relaxed.add(q)       # найдено по стране и «football club»: название может отличаться сильнее
            if not ids:
                continue
            e = {"entities": {}}
            for i in range(0, len(ids), 40):
                part = f.json("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=claims|labels|aliases|sitelinks"
                              "&sitefilter=enwiki&languages=en&ids=" + "|".join(ids[i:i + 40]), polite=1.5) or {}
                e["entities"].update(part.get("entities") or {})
            for qid in ids:
                ent = (e.get("entities") or {}).get(qid) or {}
                cl = ent.get("claims") or {}
                val = lambda p: [x["mainsnak"].get("datavalue", {}).get("value") for x in cl.get(p, []) if x.get("mainsnak")]
                p31 = {v.get("id") for v in val("P31") if isinstance(v, dict)}
                logos = [v for v in val("P154") if isinstance(v, str) and "wordmark" not in v.lower()]   # надпись-логотип - не эмблема
                enwiki = ((ent.get("sitelinks") or {}).get("enwiki") or {}).get("title")
                if not (logos or enwiki) or not (p31 & FOOTBALL_CLUB_QIDS):
                    continue
                isos = set()
                for c in [v.get("id") for v in val("P17") if isinstance(v, dict)]:
                    if c not in iso_of_qid:
                        ce = f.json(f"https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=claims&ids={c}", polite=1.5) or {}
                        cc_cl = ((ce.get("entities") or {}).get(c) or {}).get("claims") or {}
                        iso_of_qid[c] = {x["mainsnak"].get("datavalue", {}).get("value") for x in cc_cl.get("P297", [])} - {None}
                    isos |= iso_of_qid[c]
                if not (isos & want):
                    continue
                labels = [(ent.get("labels") or {}).get("en", {}).get("value", "")] + [x["value"] for x in (ent.get("aliases") or {}).get("en", [])]
                if is_junk(name, labels[0]) or (cid, labels[0]) in EXCLUDE:
                    continue
                sc = max(similarity(name, lb) for lb in labels if lb) if any(labels) else 0
                if qid in relaxed and sc < a.min_score and sc >= 0.6:
                    sc = a.min_score                        # тип и страна совпали, статья найдена по названию + стране
                if sc < a.min_score:
                    continue
                if logos:                                            # логотип в Викиданных: свободный файл Викисклада
                    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(logos[0].replace(" ", "_")) + "?width=300"
                    cands.setdefault(cid, []).append((sc - 0.01, "wd:" + qid, url, labels[0], "Wikidata/Commons"))
                    continue
                # иначе - картинка из карточки статьи английской Википедии (эмблемы там обычно несвободные файлы: pilicense=any)
                p = f.json("https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages&piprop=thumbnail|name"
                           "&pithumbsize=300&pilicense=any&redirects=1&titles=" + urllib.parse.quote(enwiki), polite=1.5) or {}
                for pg in ((p.get("query") or {}).get("pages") or {}).values():
                    img, th = (pg.get("pageimage") or ""), (pg.get("thumbnail") or {}).get("source")
                    # в карточке клуба бывает и фото стадиона: берём только файлы, похожие на эмблему
                    if th and any(w in img.lower() for w in ("logo", "crest", "badge", "emblem", "escudo", "grb", "herb", "wappen", "fc", "fk", "club")):
                        cands.setdefault(cid, []).append((sc - 0.02, "wd:" + qid, th, labels[0], "Wikipedia"))
            if k % 50 == 0:
                print(f"   Викиданные: {k}/{len(rest)}, всего найдено {len(cands)}", flush=True)

    # --- 2б. явно заданные статьи Википедии (MANUAL_WIKI): важнее автоматических находок
    if "wikidata" in sources:
        for cid, name, cc, lc in todo:
            title = MANUAL_WIKI.get(cid)
            if not title:
                continue
            lang, _, rest_title = title.partition(":") if title[2:3] == ":" else ("en", "", title)    # "ru:Статья" - другая Википедия
            title = rest_title
            p = f.json(f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages&piprop=thumbnail|name"
                       "&pithumbsize=300&pilicense=any&redirects=1&titles=" + urllib.parse.quote(title), polite=1.5) or {}
            for pg in ((p.get("query") or {}).get("pages") or {}).values():
                th = (pg.get("thumbnail") or {}).get("source")
                if th:
                    cands.setdefault(cid, []).append((1.01, "wp:" + title, th, title, "Wikipedia (статья задана вручную)"))

    # --- 3. одна команда сайта (и одна картинка) - одному клубу базы, лучшее совпадение первым
    pairs = sorted(((s, cid, key, url, nm, src) for cid, lst in cands.items() for s, key, url, nm, src in lst), key=lambda x: -x[0])
    taken_cid, taken_key, taken_url, chosen = set(), set(), set(), []
    for s, cid, key, url, nm, src in pairs:
        if cid in taken_cid or key in taken_key or url in taken_url:
            continue
        taken_cid.add(cid); taken_key.add(key); taken_url.add(url); chosen.append((cid, s, url, nm, src))

    # --- 4. скачивание
    (ROOT / "assets/logos").mkdir(parents=True, exist_ok=True)
    names = {cid: (name, cc) for cid, name, cc, _ in todo}
    report, got = [], 0
    for cid, s, url, nm, src in chosen:
        report.append({"club_id": cid, "club": names[cid][0], "country": names[cid][1], "source": src, "matched_name": nm,
                       "score": round(s, 3), "url": url})
        if a.dry_run:
            continue
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                img = Image.open(io.BytesIO(r.read())).convert("RGBA")
            bbox = img.getbbox()                                 # обрезка прозрачных полей
            if bbox:
                img = img.crop(bbox)
            img = img.resize((max(1, round(img.width * 96 / img.height)), 96), Image.LANCZOS)
            img.save(ROOT / f"assets/logos/{cid}.png", optimize=True)
            db.execute("UPDATE clubs SET logo_path=? WHERE club_id=?", (f"assets/logos/{cid}.png", cid)); db.commit()
            got += 1
            time.sleep(0.3)
        except Exception as e:
            print("   не удалось скачать", names[cid][0], url[:100], e, file=sys.stderr)
            report[-1]["source"] += " (ошибка скачивания)"
    if report:
        path = ROOT / "data/logo_sources.csv"
        old = list(csv.DictReader(open(path, encoding="utf-8"))) if path.exists() else []
        done = {r["club_id"] for r in report}
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["club_id", "club", "country", "source", "matched_name", "score", "url"], lineterminator="\n")
            w.writeheader(); w.writerows([r for r in old if r["club_id"] not in done] + report)
    miss = len(todo) - len(chosen)
    print(f"обработано: {len(todo)} | найдено: {len(chosen)} | скачано: {got} | не найдено: {miss}")
    by_src = {}
    for r in report:
        by_src[r["source"]] = by_src.get(r["source"], 0) + 1
    print("   по источникам:", by_src)

if __name__ == "__main__":
    main()
