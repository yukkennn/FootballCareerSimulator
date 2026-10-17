#!/usr/bin/env python3
"""Импорт базы команд EA FC 27 (data/fc27_teams.csv) и расширение мира новыми лигами.

    python database/importers/import_fc27.py [data/football.db]

Что делает (можно запускать повторно, результат тот же):
  1. Сборные из файла FC 27 (строки с названиями стран) в клубы НЕ попадают: их рейтинги уже перенесены
     в data/national_strength.csv (колонка fc_ovr). «MLS All Stars» пропускается.
  2. Клубы FC 27, которые уже есть в базе, получают сигнал ea_team_ovr (явный список: data/fc27_club_map.csv).
  3. Новые лиги (data/world_leagues.csv) и клубы (data/world_clubs.csv) добавляются в базу. Клубы из FC 27
     получают их рейтинг, остальные (дозаполнение неполных лиг) - ручную оценку est_ovr.
  4. Клубам базы, которых нет в FC 27, ставится ручная оценка OVR (data/club_ovr_estimates.csv).
  5. Сила лиг новых стран (data/world_league_strength.csv), формат лиг (rounds: сколько раз встречаются
     две команды, data/league_format.csv и world_leagues.csv), запасные академии (data/academy_fallback.csv).
  6. Пересчёт звёзд (recompute_stars.py).
Женских команд в файле FC 27 нет; если появятся (Women / Féminin / Frauen в названии), они пропускаются.
"""
import csv, math, re, sqlite3, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                         # корень проекта
sys.path.insert(0, str(HERE))
from common import finish, slug, upsert_signal  # noqa: E402

DATA = ROOT / "data"
NAT_ALIAS = {"Korea Republic": "KOR", "Türkiye": "TUR", "Czech Republic": "CZE", "Republic of Ireland": "IRL",
             "Congo DR": "COD", "United States": "USA"}
WOMEN = re.compile(r"\b(women|womens|féminin|feminin|frauen|femenino|ladies|wfc)\b", re.I)
CLUB_COUNTRY_FIX = {"sui-fc-vaduz": "LIE"}     # клуб играет в чужой лиге (как валлийские клубы в Англии)

def rows(name):
    with open(DATA / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main(db_path):
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys=ON")
    cols = [r[1] for r in db.execute("PRAGMA table_info(leagues)")]
    if "rounds" not in cols:
        db.execute("ALTER TABLE leagues ADD COLUMN rounds INTEGER NOT NULL DEFAULT 2")
    countries = {r[0]: r[1] for r in db.execute("SELECT fifa_code, name_en FROM countries")}
    by_name = {v: k for k, v in countries.items()}

    fc, nations, women = {}, {}, []
    for r in rows("fc27_teams.csv"):
        n = r["team_name"].strip()
        if WOMEN.search(n):
            women.append(n); continue
        code = NAT_ALIAS.get(n) or by_name.get(n)
        if code:
            nations[code] = int(r["ovr"]); continue
        fc[n] = int(r["ovr"])

    # --- 2. клубы, которые уже есть в базе
    used, matched, skipped = set(), 0, []
    for r in rows("fc27_club_map.csv"):
        n, cid = r["fc_name"], r["club_id"]
        used.add(n)
        if not cid:
            skipped.append((n, r["note"])); continue
        if not db.execute("SELECT 1 FROM clubs WHERE club_id=?", (cid,)).fetchone():
            sys.exit(f"fc27_club_map.csv: нет клуба {cid} ({n})")
        if n not in fc:
            sys.exit(f"fc27_club_map.csv: нет команды «{n}» в fc27_teams.csv")
        upsert_signal(db, cid, "ea_team_ovr", fc[n], "FC 27")
        db.execute("DELETE FROM club_signals WHERE club_id=? AND signal='ovr_estimate'", (cid,))
        db.execute("INSERT OR IGNORE INTO club_aliases VALUES (?,?,?)", (n, cid, "fc27"))
        matched += 1
    for cid, cc in CLUB_COUNTRY_FIX.items():
        db.execute("UPDATE clubs SET country_code=? WHERE club_id=?", (cc, cid))

    # --- 3. новые лиги и клубы
    for r in rows("world_leagues.csv"):
        db.execute("INSERT OR IGNORE INTO leagues (league_id,country_code,name,tier,n_clubs,source,rounds) VALUES (?,?,?,?,?,?,?)",
                   (r["league_id"], r["country_code"], r["name"], int(r["tier"]), None, "fc27+manual", int(r["rounds"])))
        db.execute("UPDATE leagues SET rounds=?, name=?, tier=? WHERE league_id=?", (int(r["rounds"]), r["name"], int(r["tier"]), r["league_id"]))
    lcountry = dict(db.execute("SELECT league_id, country_code FROM leagues"))
    added, est_new = 0, 0
    for r in rows("world_clubs.csv"):
        country = r["club_country"] or lcountry[r["league_id"]]
        cid = f"{country.lower()}-{slug(r['name'])}"
        if not db.execute("SELECT 1 FROM clubs WHERE club_id=?", (cid,)).fetchone():
            db.execute("INSERT INTO clubs (club_id,name,country_code,league_id,is_reserve,source) VALUES (?,?,?,?,?,?)",
                       (cid, r["name"], country, r["league_id"], int(r["is_reserve"]), "fc27" if r["fc_name"] else "manual"))
            added += 1
        else:
            db.execute("UPDATE clubs SET name=?, country_code=?, league_id=?, is_reserve=? WHERE club_id=?",
                       (r["name"], country, r["league_id"], int(r["is_reserve"]), cid))
        db.execute("INSERT OR IGNORE INTO club_aliases VALUES (?,?,?)", (r["name"], cid, "world_clubs"))
        if r["fc_name"]:
            if r["fc_name"] not in fc:
                sys.exit(f"world_clubs.csv: нет команды «{r['fc_name']}» в fc27_teams.csv")
            used.add(r["fc_name"])
            upsert_signal(db, cid, "ea_team_ovr", fc[r["fc_name"]], "FC 27")
            db.execute("INSERT OR IGNORE INTO club_aliases VALUES (?,?,?)", (r["fc_name"], cid, "fc27"))
        else:
            upsert_signal(db, cid, "ovr_estimate", float(r["est_ovr"]), "manual")
            est_new += 1
    for lid, n in db.execute("SELECT league_id, COUNT(*) FROM clubs GROUP BY league_id").fetchall():
        db.execute("UPDATE leagues SET n_clubs=? WHERE league_id=?", (n, lid))
    for r in rows("league_format.csv"):
        db.execute("UPDATE leagues SET rounds=? WHERE league_id=?", (int(r["rounds"]), r["league_id"]))

    # --- 4. оценки для клубов без рейтинга FC 27
    est_old = 0
    for r in rows("club_ovr_estimates.csv"):
        has_fc = db.execute("SELECT 1 FROM club_signals WHERE club_id=? AND signal='ea_team_ovr'", (r["club_id"],)).fetchone()
        if not has_fc:
            upsert_signal(db, r["club_id"], "ovr_estimate", float(r["est_ovr"]), "manual")
            est_old += 1

    # --- 5. коэффициенты УЕФА (свежий рейтинг) и сила лиг УЕФА: 100 * sqrt(коэфф / коэфф лидера), как в build_db.py
    coeff = {r["fifa_code"]: (float(r["coefficient_5y"]), r["as_of"]) for r in rows("uefa_association_coefficients.csv")}
    top = max(v for v, _ in coeff.values())
    for code, (v, _) in coeff.items():
        db.execute("UPDATE countries SET uefa_coeff_5y=?, league_strength=? WHERE fifa_code=?", (v, round(100 * math.sqrt(v / top), 1), code))
    db.execute("INSERT OR REPLACE INTO meta VALUES ('uefa_coeff_as_of', ?)", (max(a for _, a in coeff.values()),))
    # --- сила лиг других стран, запасные академии
    for r in rows("world_league_strength.csv"):
        db.execute("UPDATE countries SET league_strength=? WHERE fifa_code=?", (float(r["league_strength"]), r["fifa_code"]))
    db.execute("UPDATE countries SET fallback_academy_country=NULL")
    for r in rows("academy_fallback.csv"):
        db.execute("UPDATE countries SET fallback_academy_country=? WHERE fifa_code=?", (r["fallback_country"], r["fifa_code"]))
    db.execute("INSERT OR REPLACE INTO meta VALUES ('fc27_import', 'teams.csv: клубы и сборные EA FC 27')")

    n = finish(db)
    left = sorted(set(fc) - used)
    no_rating = db.execute("SELECT club_id FROM clubs WHERE club_id NOT IN (SELECT club_id FROM club_signals WHERE signal IN ('ea_team_ovr','ovr_estimate'))").fetchall()
    print(f"FC 27: сборных {len(nations)}, клубов {len(fc)} | сопоставлено с базой: {matched} | новых клубов: {added} "
          f"(из них с ручной оценкой: {est_new}) | оценки для старых клубов: {est_old} | пропущено: {len(skipped)} | "
          f"женских команд: {len(women)} | пересчитано клубов: {n}")
    for s in skipped:
        print("   пропущено:", *s)
    if left:
        print("   команды FC 27 без места в базе:", left)
    if no_rating:
        print("   клубы без рейтинга:", [r[0] for r in no_rating])
    db.execute("VACUUM")
    db.close()

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "football.db"))
