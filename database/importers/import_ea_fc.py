#!/usr/bin/env python3
"""Импорт рейтингов команд из датасета игроков EA FC (Kaggle и т.п.) в club_signals + добавление клубов.

    python database/importers/import_ea_fc.py data/football.db players.csv [--league-map my_leagues.csv] [--add-missing]

Из файла игроков берутся колонки: клуб, лига, общий рейтинг (OVR), при наличии - пол (женские лиги пропускаются).
Рейтинг команды = среднее 14 лучших игроков (минимум 11 игроков в клубе).
Лига -> страна берётся из встроенной таблицы ниже, её можно дополнить файлом --league-map
(колонки: league_name,country_code,tier). Неопознанные лиги печатаются в отчёте - добавьте их в файл.

Важно: EA лицензирует не все лиги (нет, например, чемпионата Казахстана), поэтому для части стран
этот источник не даст ничего - нужен ClubElo или другой источник.
"""
import argparse, csv, sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ClubIndex, add_club, ensure_league, finish, norm, upsert_signal

BUILTIN = {  # нормализованное название лиги EA -> (код страны FIFA, уровень)
    "premierleague": ("ENG", 1), "efl championship": ("ENG", 2), "championship": ("ENG", 2), "efl league one": ("ENG", 3),
    "league one": ("ENG", 3), "efl league two": ("ENG", 4), "league two": ("ENG", 4),
    "ligue 1": ("FRA", 1), "ligue 1 uber eats": ("FRA", 1), "ligue 1 mcdonalds": ("FRA", 1), "ligue 2": ("FRA", 2), "ligue 2 bkt": ("FRA", 2),
    "bundesliga": ("GER", 1), "bundesliga 2": ("GER", 2), "2 bundesliga": ("GER", 2), "3 liga": ("GER", 3),
    "serie a": ("ITA", 1), "serie a enilive": ("ITA", 1), "serie a timtm": ("ITA", 1), "serie b": ("ITA", 2),
    "laliga ea sports": ("ESP", 1), "la liga": ("ESP", 1), "laliga": ("ESP", 1), "laliga hypermotion": ("ESP", 2), "la liga 2": ("ESP", 2),
    "eredivisie": ("NED", 1), "liga portugal": ("POR", 1), "liga portugal betclic": ("POR", 1),
    "major league soccer": ("USA", 1), "mls": ("USA", 1), "saudi pro league": ("KSA", 1), "roshn saudi league": ("KSA", 1),
    "a league men": ("AUS", 1), "a league": ("AUS", 1), "k league 1": ("KOR", 1), "super lig": ("TUR", 1), "trendyol super lig": ("TUR", 1),
    "scottish premiership": ("SCO", 1), "cinch premiership": ("SCO", 1), "jupiler pro league": ("BEL", 1), "belgian pro league": ("BEL", 1),
    "eliteserien": ("NOR", 1), "allsvenskan": ("SWE", 1), "admiral bundesliga": ("AUT", 1), "austrian bundesliga": ("AUT", 1),
    "raiffeisen super league": ("SUI", 1), "ekstraklasa": ("POL", 1), "pko bp ekstraklasa": ("POL", 1),
    "league of ireland premier division": ("IRL", 1), "liga profesional": ("ARG", 1), "liga profesional de futbol": ("ARG", 1),
    "liga betplay": ("COL", 1), "liga betplay dimayor": ("COL", 1), "liga mx": ("MEX", 1), "ukrainian premier league": ("UKR", 1),
    "3f superliga": ("DEN", 1), "danish superliga": ("DEN", 1), "fortuna liga": ("CZE", 1), "chance liga": ("CZE", 1),
}

def find(header, cands):
    low = {h.lower().strip(): h for h in header}
    for c in cands:
        if c in low:
            return low[c]
    for h in low:
        if any(c in h for c in cands):
            return low[h]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db"); ap.add_argument("csv")
    ap.add_argument("--league-map"); ap.add_argument("--add-missing", action="store_true")
    ap.add_argument("--top-n", type=int, default=14)
    a = ap.parse_args()
    lm = dict(BUILTIN)
    if a.league_map:
        for r in csv.DictReader(open(a.league_map, encoding="utf-8-sig")):
            lm[norm(r["league_name"])] = (r["country_code"].upper(), int(r.get("tier") or 1))
    lm = {norm(k): v for k, v in lm.items()}

    db = sqlite3.connect(a.db); db.execute("PRAGMA foreign_keys=ON")
    countries = {r[0] for r in db.execute("SELECT fifa_code FROM countries")}
    idx = ClubIndex(db)
    with open(a.csv, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        cc = find(rd.fieldnames, ["club_name", "team", "club"]); lc = find(rd.fieldnames, ["league_name", "league"])
        oc = find(rd.fieldnames, ["overall", "ovr"]); gc = find(rd.fieldnames, ["gender", "sex"])
        if not (cc and lc and oc):
            sys.exit(f"Не найдены колонки клуб/лига/overall. Заголовок: {rd.fieldnames}")
        teams = {}
        for r in rd:
            if gc and str(r.get(gc, "")).strip().lower() in ("f", "female", "women", "w"):
                continue
            try:
                teams.setdefault((r[cc].strip(), r[lc].strip()), []).append(int(float(r[oc])))
            except (ValueError, TypeError, AttributeError):
                continue
    unknown_leagues, matched, added, small, unmatched = {}, 0, 0, 0, 0
    for (club, league), ovrs in teams.items():
        key = norm(league)
        if key not in lm:
            unknown_leagues[league] = unknown_leagues.get(league, 0) + 1
            continue
        country, tier = lm[key]
        if country not in countries:
            unknown_leagues[league] = unknown_leagues.get(league, 0) + 1
            continue
        if len(ovrs) < 11:
            small += 1
            continue
        team_ovr = sum(sorted(ovrs, reverse=True)[:a.top_n]) / min(a.top_n, len(ovrs))
        cid = idx.match(club, country)
        if cid is None and a.add_missing:
            lid = ensure_league(db, country, league, tier, "ea-fc-csv")
            cid = add_club(db, club, country, lid, "ea-fc-csv"); added += 1
            idx.reload()
        if cid is None:
            unmatched += 1
            continue
        upsert_signal(db, cid, "ea_team_ovr", round(team_ovr, 2), None); matched += 1
    n = finish(db)
    print(f"команд: {len(teams)} | сопоставлено: {matched} | добавлено: {added} | не найдено в базе: {unmatched} | "
          f"мало игроков: {small} | пересчитано клубов: {n}")
    if unknown_leagues:
        print("Неопознанные лиги (добавьте в --league-map):")
        for k, v in sorted(unknown_leagues.items(), key=lambda x: -x[1])[:25]:
            print(f"   {k}  ({v} команд)")

if __name__ == "__main__":
    main()
