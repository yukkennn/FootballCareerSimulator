"""Загрузка статических данных (football.db + CSV) в память."""
import csv, sqlite3
from .paths import ROOT, DB_PATH, DATA, LOGOS

# звёзды как в EA FC: по OVR команды (те же пороги, что в recompute_stars.py)
STAR_OVR = [(82, 5.0), (79, 4.5), (76, 4.0), (73, 3.5), (70, 3.0), (67, 2.5), (64, 2.0), (61, 1.5), (57, 1.0)]
THRESHOLDS = [(2.5 * (o - 48), s) for o, s in STAR_OVR]     # в шкале силы клуба 0..100 (OVR = 48 + 0.4 * сила)

def stars_for(score):
    for t, s in THRESHOLDS:
        if score >= t:
            return s
    return 0.5

def stars_for_ovr(ovr, minimum=0.5):
    for t, s in STAR_OVR:
        if ovr >= t:
            return s
    return minimum

class GameData:
    def __init__(self, db_path=DB_PATH):
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        self.countries = {r["code"]: dict(r) for r in db.execute(
            "SELECT fifa_code AS code, iso2, name_en, name_ru, confederation AS conf, uefa_coeff_5y AS coeff, "
            "league_strength AS lstrength, fallback_academy_country AS fallback FROM countries")}
        has_rounds = any(r[1] == "rounds" for r in db.execute("PRAGMA table_info(leagues)"))
        q = "SELECT league_id, country_code, name, tier" + (", rounds" if has_rounds else "") + " FROM leagues"
        self.leagues = {r["league_id"]: {"id": r["league_id"], "country": r["country_code"], "name": r["name"], "tier": r["tier"],
                                         "rounds": (r["rounds"] if has_rounds else 2) or 2}
                        for r in db.execute(q)}
        self.clubs = {}
        for r in db.execute("SELECT club_id, name, country_code, league_id, star_score, is_reserve, logo_path, city, stadium, founded FROM clubs"):
            self.clubs[r["club_id"]] = {"id": r["club_id"], "name": r["name"], "country": r["country_code"], "league": r["league_id"],
                                        "score": float(r["star_score"]), "reserve": bool(r["is_reserve"]),
                                        "logo": (ROOT / r["logo_path"]) if r["logo_path"] else None,
                                        "city": r["city"], "stadium": r["stadium"], "founded": r["founded"]}
        self.comps = {r["code"]: dict(r) for r in db.execute("SELECT code, name_en, name_ru, kind, confederation, tier, cycle_years, next_edition_year FROM competitions")}
        db.close()
        self.nat_strength, self.nat_fc = {}, {}
        for r in csv.DictReader(open(DATA / "national_strength.csv", encoding="utf-8")):
            self.nat_strength[r["fifa_code"]] = float(r["strength"])
            self.nat_fc[r["fifa_code"]] = r.get("note", "").startswith("FC 27")
        self.cups = {r["country"]: r for r in csv.DictReader(open(DATA / "domestic_cups.csv", encoding="utf-8"))}
        ranked = sorted((c for c in self.countries.values() if c["coeff"] is not None and c["conf"] == "UEFA"), key=lambda c: -c["coeff"])
        self.uefa_rank = {c["code"]: i + 1 for i, c in enumerate(ranked)}
        by_country = {}
        for l in self.leagues.values():
            by_country.setdefault(l["country"], []).append(l)
        self.top_league = {c: min(ls, key=lambda l: l["tier"])["id"] for c, ls in by_country.items()}
        self.pyramids = {c: [l["id"] for l in sorted(ls, key=lambda l: l["tier"])] for c, ls in by_country.items() if len(ls) > 1}
        self.countries_with_clubs = sorted({c["country"] for c in self.clubs.values() if not c["reserve"]})
        # страна, в лиге которой играют клубы другой страны (Уэльс -> Англия, Канада -> США, Новая Зеландия -> Австралия ...)
        self.league_host = {}
        for c in self.clubs.values():
            lc = self.leagues[c["league"]]["country"] if c["league"] in self.leagues else c["country"]
            if lc != c["country"]:
                self.league_host.setdefault(c["country"], lc)

    def country_name(self, code, lang="ru"):
        c = self.countries[code]
        return c["name_ru"] if lang == "ru" else c["name_en"]

    def clubs_of_country(self, code):
        return [c for c in self.clubs.values() if c["country"] == code and not c["reserve"]]

    def has_league(self, code):
        """Есть ли в базе лига этой страны (или её клубы играют в соседней лиге, как Уэльс)."""
        return code in self.top_league or code in self.league_host

    def nat_ovr(self, code, strength=None):
        s = self.nat_strength[code] if strength is None else strength
        return 48.0 + s / 2.5

    def nat_stars(self, code):
        return stars_for_ovr(self.nat_ovr(code), minimum=1.0)

    def cup_names(self, country):
        """-> (кубок_en, кубок_ru, суперкубок_en | None, суперкубок_ru | None)."""
        ck = self.cups.get(country)
        en, ru = self.country_name(country, "en"), self.country_name(country, "ru")
        if ck:
            return ck["cup_en"], ck["cup_ru"], (ck["supercup_en"] or None), (ck["supercup_ru"] or None)
        return f"{en} Cup", f"Кубок страны ({ru})", f"{en} Super Cup", f"Суперкубок ({ru})"
