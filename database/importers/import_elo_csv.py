#!/usr/bin/env python3
"""Импорт Elo клубов из CSV (ClubElo / датасет Kaggle с Elo-срезами) в club_signals.

    python database/importers/import_elo_csv.py data/football.db Elo.csv [--add-missing --min-elo 1500]

Колонки определяются автоматически (club/name, elo, date/from, country). Если у вашего файла другие
имена - укажите --club-col / --elo-col / --date-col / --country-col.
Берётся самая свежая запись для каждого клуба. Коды стран ClubElo в большинстве случаев совпадают с
кодами FIFA (ENG, GER, ESP ...); незнакомые коды пропускаются и попадают в отчёт.

ВАЖНО: API clubelo.com/YYYY-MM-DD на 30.09.2026 не работал (HTTP 502), поэтому источник - файл, который
вы скачали сами (Kaggle и т.п.). Проверьте условия использования источника.
"""
import argparse, csv, sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ClubIndex, add_club, finish, upsert_signal

CLUB = ["club", "name", "team", "club_name", "club name in english"]
ELO = ["elo", "rating", "elo_rating"]
DATE = ["to", "date", "snapshot", "date of the snapshot", "from"]
COUNTRY = ["country", "country_code", "club country three-letter code", "nation"]

def pick(header, wanted, candidates):
    low = {h.lower().strip(): h for h in header}
    if wanted:
        return low.get(wanted.lower()) or wanted
    for c in candidates:
        if c in low:
            return low[c]
    for h in low:
        if any(c in h for c in candidates):
            return low[h]
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db"); ap.add_argument("csv")
    ap.add_argument("--club-col"); ap.add_argument("--elo-col"); ap.add_argument("--date-col"); ap.add_argument("--country-col")
    ap.add_argument("--add-missing", action="store_true", help="создавать клубы, которых нет в базе (без лиги и эмблемы)")
    ap.add_argument("--min-elo", type=float, default=1500, help="порог Elo для --add-missing")
    a = ap.parse_args()

    db = sqlite3.connect(a.db); db.execute("PRAGMA foreign_keys=ON")
    countries = {r[0] for r in db.execute("SELECT fifa_code FROM countries")}
    idx = ClubIndex(db)
    with open(a.csv, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        cc, ec, dc, kc = (pick(rd.fieldnames, a.club_col, CLUB), pick(rd.fieldnames, a.elo_col, ELO),
                          pick(rd.fieldnames, a.date_col, DATE), pick(rd.fieldnames, a.country_col, COUNTRY))
        if not cc or not ec:
            sys.exit(f"Не найдены колонки клуба/Elo. Заголовок: {rd.fieldnames}")
        latest = {}
        for r in rd:
            try:
                elo = float(r[ec])
            except (ValueError, TypeError):
                continue
            key = (r[cc], (r.get(kc) or "").strip().upper() if kc else "")
            d = r.get(dc, "") if dc else ""
            if key not in latest or d >= latest[key][0]:
                latest[key] = (d, elo)
    matched = added = unknown_country = unmatched = 0
    for (name, country), (d, elo) in latest.items():
        country = country if country in countries else None
        if kc and (country is None):
            unknown_country += 1
        cid = idx.match(name, country)
        if cid is None and a.add_missing and country and elo >= a.min_elo:
            cid = add_club(db, name, country, None, "clubelo-csv"); added += 1
            idx.reload()
        if cid is None:
            unmatched += 1
            continue
        upsert_signal(db, cid, "clubelo", elo, d[:10] or None); matched += 1
    n = finish(db)
    print(f"строк (клуб, страна): {len(latest)} | сопоставлено: {matched} | добавлено: {added} | "
          f"не найдено: {unmatched} | неизвестный код страны: {unknown_country} | пересчитано клубов: {n}")

if __name__ == "__main__":
    main()
