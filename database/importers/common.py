"""Общие функции импортёров: сопоставление названий клубов и запись сигналов."""
import difflib, re, sqlite3, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import recompute_stars  # noqa: E402

def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|afc|cf|fk|sk|sc|ac|as|ss|us|ud|cd|rcd|ca|bsc|sv|vfb|vfl|tsg|fsv|1\.)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)

def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

class ClubIndex:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.by_country = {}    # code -> {normname: set(club_id)}
        self.reload()

    def reload(self):
        self.by_country = {}
        rows = self.db.execute("SELECT club_id, country_code, name FROM clubs").fetchall()
        for cid, cc, name in rows:
            self.by_country.setdefault(cc, {}).setdefault(norm(name), set()).add(cid)
        for alias, cid, cc in self.db.execute("SELECT a.alias, a.club_id, c.country_code FROM club_aliases a JOIN clubs c USING(club_id)"):
            self.by_country.setdefault(cc, {}).setdefault(norm(alias), set()).add(cid)

    def match(self, name, country=None, cutoff=0.88):
        pools = [self.by_country.get(country, {})] if country else list(self.by_country.values())
        k = norm(name)
        hits = set()
        for p in pools:
            hits |= p.get(k, set())
        if len(hits) == 1:
            return next(iter(hits))
        if hits:
            return None                         # неоднозначно
        if country:
            keys = list(self.by_country.get(country, {}))
            close = difflib.get_close_matches(k, keys, n=2, cutoff=cutoff)
            if len(close) == 1 or (len(close) == 2 and difflib.SequenceMatcher(None, k, close[0]).ratio() - difflib.SequenceMatcher(None, k, close[1]).ratio() > 0.05):
                ids = self.by_country[country][close[0]]
                if len(ids) == 1:
                    return next(iter(ids))
        return None

def upsert_signal(db, club_id, signal, value, as_of=None):
    db.execute("INSERT OR REPLACE INTO club_signals VALUES (?,?,?,?)", (club_id, signal, float(value), as_of))

def add_club(db, name, country, league_id=None, source="import"):
    cid = f"{country.lower()}-{slug(name)}"
    if db.execute("SELECT 1 FROM clubs WHERE club_id=?", (cid,)).fetchone():
        return cid
    db.execute("INSERT INTO clubs (club_id,name,country_code,league_id,source) VALUES (?,?,?,?,?)", (cid, name, country, league_id, source))
    db.execute("INSERT OR IGNORE INTO club_aliases VALUES (?,?,?)", (name, cid, source))
    return cid

def ensure_league(db, country, name, tier, source):
    lid = f"{country.lower()}-{slug(name)}"
    db.execute("INSERT OR IGNORE INTO leagues (league_id,country_code,name,tier,n_clubs,source) VALUES (?,?,?,?,?,?)", (lid, country, name, tier, None, source))
    return lid

def finish(db):
    n = recompute_stars.run(db)
    db.commit()
    return n
