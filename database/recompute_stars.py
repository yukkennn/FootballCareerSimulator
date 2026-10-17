#!/usr/bin/env python3
"""Пересчёт звёзд клубов (0.5..5.0) из сигналов в таблице club_signals.

Внутренняя сила клуба star_score (0..100) связана с рейтингом команды в стиле EA FC так:
    star_score = 2.5 * (OVR - 48)        (OVR 88 -> 100, OVR 70 -> 55, OVR 52 -> 10)
Игра считает OVR команды обратно: 48 + 0.4 * star_score. Для OVR ниже 48 star_score отрицательный (до -32.5 при OVR 35).

Приоритет источников (чем выше, тем надёжнее):
  1. ea_team_ovr   -> рейтинг команды из базы EA FC 27 (data/fc27_teams.csv)
  2. clubelo       -> Elo клуба (если загружен importers/import_elo_csv.py): реальные данные важнее ручной оценки
  3. ovr_estimate  -> ручная оценка OVR для клубов, которых нет в FC 27 (data/club_ovr_estimates.csv, data/world_clubs.csv)
  4. uefa_club_coeff / manual_stars / top_flight_seasons -> слабые сигналы поверх силы лиги (старая схема)

Звёзды как в EA FC (по OVR команды): 5★ от 82, 4.5★ от 79, 4★ от 76, 3.5★ от 73, 3★ от 70, 2.5★ от 67,
2★ от 64, 1.5★ от 61, 1★ от 57, ниже 0.5★.

Запуск отдельно:  python database/recompute_stars.py data/football.db
"""
import math, sqlite3, sys

ELO_RANGE = (1100.0, 2050.0)     # ClubElo: слабый клуб .. топ-клуб
EA_RANGE = (48.0, 88.0)          # OVR команды EA FC -> star_score 0..100 (линейно)
UEFA_CLUB_MAX = 130.0            # верхняя граница 5-летнего клубного коэффициента
DEFAULT_LEAGUE_STRENGTH = 35.0   # для стран без оценки лиги
STAR_OVR = [(82, 5.0), (79, 4.5), (76, 4.0), (73, 3.5), (70, 3.0), (67, 2.5), (64, 2.0), (61, 1.5), (57, 1.0)]
THRESHOLDS = [(round(2.5 * (o - 48), 1), s) for o, s in STAR_OVR]   # те же пороги в шкале star_score

def scale(v, lo, hi):
    return max(0.0, min(100.0, (v - lo) / (hi - lo) * 100.0))

MIN_OVR = 35.0                   # OVR слабее 48 тоже различается (полупрофессиональные лиги: Сан-Марино, Гибралтар, Андорра)
MIN_SCORE = 2.5 * (MIN_OVR - 48) # -32.5: star_score может быть отрицательным

def scale_ovr(ovr):
    """OVR команды -> star_score по той же прямой, что EA_RANGE, но без обрезки снизу на OVR 48 (до MIN_OVR)."""
    return max(MIN_SCORE, min(100.0, (ovr - EA_RANGE[0]) / (EA_RANGE[1] - EA_RANGE[0]) * 100.0))

def to_stars(score):
    for t, s in THRESHOLDS:
        if score >= t:
            return s
    return 0.5

STAR_TO_SCORE = {5.0: 94, 4.5: 87, 4.0: 80, 3.5: 72, 3.0: 64, 2.5: 56, 2.0: 48, 1.5: 40, 1.0: 32, 0.5: 20}
TENURE_ADJ = {1: -8, 2: -5, 3: -2, 4: 0, 5: 2, 6: 4}   # сезонов в высшем дивизионе из последних 6

TIER_PENALTY = {1: 0, 2: 12, 3: 20, 4: 26}     # нижние дивизионы слабее при прочих равных
NO_TOP_FLIGHT_PENALTY = 4                       # клуб без единого сезона в элите за 6 лет (только для tier >= 2)

def compute(league_strength, sig, tier=1):
    """-> (score, quality). sig: dict signal -> value."""
    if "ea_team_ovr" in sig:
        return scale_ovr(sig["ea_team_ovr"]), "fc27"
    if "clubelo" in sig:
        return scale(sig["clubelo"], *ELO_RANGE), "elo"
    if "ovr_estimate" in sig:
        return scale_ovr(sig["ovr_estimate"]), "estimate"
    ls = DEFAULT_LEAGUE_STRENGTH if league_strength is None else league_strength
    if "uefa_club_coeff" in sig:
        u = 100.0 * math.sqrt(min(sig["uefa_club_coeff"], UEFA_CLUB_MAX) / UEFA_CLUB_MAX)
        return 0.75 * u + 0.25 * ls, "club_signals"
    if "manual_stars" in sig:
        return float(STAR_TO_SCORE[float(sig["manual_stars"])]), "manual_seed"
    base = 15.0 + 0.55 * ls - TIER_PENALTY.get(tier, 26)
    if "top_flight_seasons" in sig:
        return max(0.0, min(100.0, base + TENURE_ADJ.get(int(sig["top_flight_seasons"]), 0))), "club_signals"
    if tier >= 2:
        return max(0.0, base - NO_TOP_FLIGHT_PENALTY), "league_only"
    return base, "league_only"

def run(db):
    ls = dict(db.execute("SELECT fifa_code, league_strength FROM countries"))
    sigs = {}
    for cid, name, v in db.execute("SELECT club_id, signal, value FROM club_signals"):
        sigs.setdefault(cid, {})[name] = v
    n = 0
    rows = db.execute("SELECT c.club_id, COALESCE(l.country_code, c.country_code), COALESCE(l.tier, 1) FROM clubs c LEFT JOIN leagues l USING(league_id)").fetchall()
    for cid, lcode, tier in rows:
        score, q = compute(ls.get(lcode), sigs.get(cid, {}), tier)
        db.execute("UPDATE clubs SET star_score=?, stars=?, strength_quality=? WHERE club_id=?",
                   (round(score, 1), to_stars(score), q, cid))
        n += 1
    return n

if __name__ == "__main__":
    con = sqlite3.connect(sys.argv[1])
    print("clubs updated:", run(con)); con.commit()
