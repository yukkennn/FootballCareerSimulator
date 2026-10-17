"""Проверка импортёров на СИНТЕТИЧЕСКИХ файлах (реальные датасеты из песочницы недоступны)."""
import csv, os, shutil, sqlite3, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp())
db = tmp / "t.db"; shutil.copy(ROOT / "data" / "football.db", db)

# 1) Elo: точные имена, алиас, опечатка, неизвестный клуб, новый клуб из другой страны
with open(tmp / "elo.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Rank", "Club", "Country", "Level", "Elo", "From", "To"])
    w.writerow([1, "Man City", "ENG", 1, 2050, "2026-09-01", "2026-09-30"])
    w.writerow([2, "Real Madrid", "ESP", 1, 1990, "2026-09-01", "2026-09-30"])
    w.writerow([3, "Real Madrid", "ESP", 1, 1500, "2026-01-01", "2026-01-30"])   # старая запись не должна победить
    w.writerow([4, "Napoli", "ITA", 1, 1850, "2026-09-01", "2026-09-30"])
    w.writerow([5, "Kairat Almaty", "KAZ", 1, 1560, "2026-09-01", "2026-09-30"])
    w.writerow([7, "Barnsley", "ENG", 3, 1480, "2026-09-01", "2026-09-30"])
    w.writerow([6, "Nonexistent FC", "ENG", 1, 1700, "2026-09-01", "2026-09-30"])
r = subprocess.run([sys.executable, ROOT / "database/importers/import_elo_csv.py", db, tmp / "elo.csv", "--add-missing"], capture_output=True, text=True)
print(r.stdout, r.stderr)
assert r.returncode == 0, r.stderr
c = sqlite3.connect(db)
assert c.execute("select value from club_signals where club_id='esp-real-madrid' and signal='clubelo'").fetchone()[0] == 1990, "берётся самая свежая запись"
assert c.execute("select strength_quality from clubs where club_id='ita-ssc-napoli'").fetchone()[0] == "fc27", "рейтинг FC 27 важнее Elo"
assert c.execute("select strength_quality from clubs where club_id='kaz-kairat-almaty'").fetchone()[0] == "elo", "Elo важнее ручной оценки"
assert c.execute("select value from club_signals where club_id='kaz-kairat-almaty' and signal='clubelo'").fetchone()[0] == 1560, "Kairat Almaty сопоставлен с уже существующим клубом"
assert c.execute("select count(*) from clubs where country_code='KAZ'").fetchone()[0] == 16, "дубликат Кайрата не создан"
print("Elo import: OK; Man City matched:", c.execute("select club_id from club_signals where signal='clubelo' and value=2050").fetchall())

# 2) EA FC: по 14 игроков на команду, одна женская лига, одна неизвестная
with open(tmp / "ea.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Name", "Overall", "Club", "League", "Gender"])
    for club, lg, base in [("Arsenal", "Premier League", 80), ("Luton Town", "Championship", 66), ("Kairat Almaty", "Kazakhstan Premier League", 65)]:
        for i in range(14):
            w.writerow([f"P{i}", base - i // 4, club, lg, "M"])
    for i in range(14):
        w.writerow([f"W{i}", 85, "Arsenal Women", "Women Super League", "F"])
r = subprocess.run([sys.executable, ROOT / "database/importers/import_ea_fc.py", db, tmp / "ea.csv", "--add-missing"], capture_output=True, text=True)
print(r.stdout, r.stderr)
assert r.returncode == 0, r.stderr
assert c.close() is None
c = sqlite3.connect(db)
assert c.execute("select 1 from club_signals where club_id='eng-arsenal-fc' and signal='ea_team_ovr'").fetchone(), "Arsenal FC сопоставлен с Arsenal"
assert "Kazakhstan Premier League" in r.stdout, "неизвестная лига попала в отчёт"
print("EA import: OK")
c.close()                                    # иначе Windows не даст удалить временную базу
shutil.rmtree(tmp, ignore_errors=True)
