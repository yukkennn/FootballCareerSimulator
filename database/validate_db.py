#!/usr/bin/env python3
"""Проверка целостности football.db.  python database/validate_db.py [data/football.db]"""
import os, sqlite3, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent          # корень проекта
db = sqlite3.connect(sys.argv[1] if len(sys.argv) > 1 else root / "data" / "football.db")
db.execute("PRAGMA foreign_keys=ON")
q = lambda s: db.execute(s).fetchall()
errors = []
def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond: errors.append(msg)

check(q("select count(*) from countries")[0][0] == 211, "211 стран FIFA")
check(dict(q("select confederation,count(*) from countries group by 1")) == {"AFC": 46, "CAF": 54, "CONCACAF": 35, "CONMEBOL": 10, "OFC": 11, "UEFA": 55}, "состав конфедераций 46/54/35/10/11/55")
bad_ru = [r[0] for r in q("select fifa_code, name_ru from countries") if not any("\u0400" <= ch <= "\u04ff" for ch in r[1])]
check(not bad_ru, f"у всех стран русское название на кириллице (проблемные: {bad_ru})")
check(q("select count(*) from countries where uefa_coeff_5y is not null")[0][0] == 55, "коэффициенты UEFA у 55 ассоциаций")
check(not db.execute("PRAGMA foreign_key_check").fetchall(), "нет нарушений внешних ключей")
check(not q("select 1 from clubs where stars is null"), "у всех клубов есть звёзды")
check(not q("select 1 from clubs where stars not in (0.5,1,1.5,2,2.5,3,3.5,4,4.5,5)"), "звёзды в допустимом наборе")
missing = [r[0] for r in q("select logo_path from clubs where logo_path is not null") if not (root / r[0]).exists()]
check(not missing, f"все файлы эмблем существуют ({len(missing)} пропущено)")
GUESTS = {("WAL", "ENG"), ("AND", "ESP"), ("CAN", "USA"), ("NZL", "AUS"), ("LIE", "SUI"), ("NIR", "IRL")}
bad_cc = [r for r in q("select k.club_id, k.country_code, l.country_code from clubs k join leagues l using(league_id) where l.country_code != k.country_code")
          if (r[1], r[2]) not in GUESTS]
check(not bad_cc, f"страна клуба = стране лиги (исключения: Уэльс в Англии, Андорра в Испании, Канада в MLS, Новая Зеландия в A-League, Лихтенштейн в Швейцарии, Дерри Сити в Ирландии) {bad_cc}")
uefa_no_league = [r[0] for r in q("select fifa_code from countries where confederation='UEFA' and fifa_code not in (select country_code from leagues where tier=1)")]
check(uefa_no_league == ["LIE"], f"у всех ассоциаций УЕФА есть своя высшая лига, кроме Лихтенштейна (без лиги: {uefa_no_league})")
sizes = dict(q("select league_id, count(*) from clubs group by league_id"))
want = {"eng-premier-league": 20, "eng-championship": 24, "eng-league-one": 24, "eng-league-two": 24, "esp-segunda-division": 22,
        "ger-2-bundesliga": 18, "ita-serie-b": 20, "fra-ligue-2": 18, "kaz-premier-league": 16}
check(all(sizes.get(k) == v for k, v in want.items()), "размеры лиг: " + ", ".join(f"{k}={sizes.get(k)}" for k in want))
check(sizes.get("eng-premier-league") == 20 and sum(sizes.get(k, 0) for k in want if k.startswith("eng-")) == 92, "Англия: 4 дивизиона = 92 клуба")
check(q("select count(*) from clubs k join leagues l using(league_id) where k.country_code='WAL' and l.country_code='ENG'")[0][0] == 4, "4 валлийских клуба в английской системе")
check(q("select count(*) from clubs where is_reserve=1")[0][0] == 5, "5 фарм-клубов помечены is_reserve (Сельта B, Реал Сосьедад B, Штутгарт II, Хоффенхайм II, San Marino Academy U22)")
check(q("select min(48 + 0.4 * star_score) from clubs")[0][0] >= 35, "OVR клубов не ниже 35")
no_rating = q("select club_id from clubs where club_id not in (select club_id from club_signals where signal in ('ea_team_ovr','ovr_estimate','clubelo'))")
check(not no_rating, f"у каждого клуба есть рейтинг FC 27, Elo или ручная оценка (нет у: {no_rating[:10]})")
check(q("select count(*) from club_signals where signal='ea_team_ovr'")[0][0] >= 640, "рейтинги FC 27 загружены (importers/import_fc27.py)")
check(not q("select 1 from leagues where rounds < 1 or rounds is null"), "у всех лиг задан формат (rounds >= 1)")
check(not q("select league_id from leagues l where (select count(*) from clubs c where c.league_id=l.league_id) < 8"), "в каждой лиге не меньше 8 клубов")
check(not q("select 1 from clubs where is_reserve=1 and logo_path is not null"), "у фарм-клубов нет чужих эмблем")
# запасные академии
with_clubs = {r[0] for r in q("select distinct country_code from clubs where is_reserve=0")}
no_fb = [r[0] for r in q("select fifa_code from countries") if r[0] not in with_clubs and not q(f"select 1 from countries where fifa_code='{r[0]}' and fallback_academy_country is not null")]
check(not no_fb, f"у каждой страны без клубов есть запасная академия (нет у: {no_fb})")
bad_fb = [r for r in q("select fifa_code, fallback_academy_country from countries where fallback_academy_country is not null") if r[1] not in with_clubs]
check(not bad_fb, f"запасная страна всегда имеет клубы {bad_fb}")
check(not [c for c in with_clubs if q(f"select 1 from countries where fifa_code='{c}' and fallback_academy_country is not null")], "страны с клубами не имеют запасной")
check(q("select count(*) from competitions")[0][0] == 21, "21 соревнование в каталоге")
print("\nИтого: стран %d | лиг %d | клубов %d | псевдонимов %d | размер БД %.0f КБ | эмблемы %.1f МБ" % (
    q("select count(*) from countries")[0][0], q("select count(*) from leagues")[0][0], q("select count(*) from clubs")[0][0],
    q("select count(*) from club_aliases")[0][0], os.path.getsize(sys.argv[1] if len(sys.argv) > 1 else root / "data" / "football.db") / 1024,
    sum(f.stat().st_size for f in (root / "assets/logos").glob("*.png")) / 1e6))
cov = q("select confederation, sum(n_clubs>0), count(*) from v_country_coverage group by 1")
print("Покрытие стран клубами (есть клубы / всего):", {c: f"{a}/{b}" for c, a, b in cov}, "| всего", sum(a for _, a, _ in cov), "/ 211")
sys.exit(1 if errors else 0)
