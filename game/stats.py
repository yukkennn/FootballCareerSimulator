"""Индивидуальная статистика: голы и передачи, сухие матчи, средняя оценка за сезон, очки для Золотого мяча.

Одна и та же модель считает сезон и для вашего игрока, и для звёзд мира (stars.py), поэтому награды
сравнивают всех по одним правилам: статистика + трофеи команды + класс игрока.
"""
import math
from .player import clamp
from .positions import GOAL_RATE, ASSIST_RATE, RATE_SENS
from .world import poisson

def rates(pos, ovr, team, opp, attrs=None):
    """Ожидаемые голы и передачи за матч. team - OVR своей команды, opp - средний OVR соперников."""
    m = math.exp(clamp((ovr - opp) / RATE_SENS[pos], -1.5, 1.2)) * math.exp(clamp((team - opp) / 35.0, -0.6, 0.6))
    m = min(m, 2.75)
    g, a = GOAL_RATE[pos] * m, ASSIST_RATE[pos] * m
    if attrs:
        g *= clamp(1 + (attrs[1] - ovr) / 120, 0.7, 1.4)
        a *= clamp(1 + (attrs[2] - ovr) / 150, 0.75, 1.3)
    return g, a

def _nb(rng, mu, cap):
    """Отрицательно-биномиальное число (Пуассон со случайной интенсивностью): сезоны бывают удачными и нет."""
    if mu <= 0:
        return 0
    lam = rng.gammavariate(10.0, mu / 10.0)
    return min(poisson(rng, lam), cap)

def produce(rng, pos, ovr, team, opp, games, attrs=None, mult=1.0, style=None):
    """-> (голы, передачи, ожидаемые голы, ожидаемые передачи) за games матчей.
    style - (множитель голов, множитель передач) от ведущей ноги и роста (Player.style)."""
    if games <= 0:
        return 0, 0, 0.0, 0.0
    g, a = rates(pos, ovr, team, opp, attrs)
    sg, sa = style or (1.0, 1.0)
    mu_g, mu_a = games * g * mult * sg, games * a * mult * sa
    cap = int(games * 1.6) + 1
    return _nb(rng, mu_g, cap), _nb(rng, mu_a, cap), mu_g, mu_a

def cs_rate(team, opp):
    """Доля сухих матчей команды."""
    return clamp(0.30 * math.exp((team - opp) / 10.0), 0.04, 0.62)

def clean_sheets(rng, games, team, opp):
    r = cs_rate(team, opp)
    return sum(1 for _ in range(games) if rng.random() < r), games * r

# ---------- средняя оценка за сезон (как у статистических сайтов: 6.0 слабо, 6.7 норма, 7.3+ отлично, 8+ выдающийся) ----------
BENCH = {p: GOAL_RATE[p] + 0.7 * ASSIST_RATE[p] for p in GOAL_RATE}       # «норма» для позиции
W_ATT = {"ST": 1.0, "CF": 1.0, "LW": 1.0, "RW": 1.0, "CAM": 0.9, "LM": 0.8, "RM": 0.8, "CM": 0.65, "CDM": 0.4,
         "LB": 0.4, "RB": 0.4, "CB": 0.25, "GK": 0.5}

def season_rating(pos, apps, goals, assists, cs, ovr, league_ovr, rank, n, team_ga_pg, league_ga_pg):
    if apps <= 0:
        return None
    if pos == "GK":
        att = (cs / apps) / 0.30
    else:
        att = ((goals + 0.7 * assists) / apps) / BENCH[pos]
    deff = clamp(league_ga_pg / max(0.35, team_ga_pg), 0.4, 2.2) if team_ga_pg is not None else 1.0
    w = W_ATT[pos]
    rel = w * att + (1 - w) * deff
    team = 1 - 2 * (rank - 1) / max(1, n - 1) if n else 0.0
    r = 6.0 + 0.95 * math.log(1 + 1.2 * clamp(rel, 0, 6)) + 0.15 * team + 0.01 * clamp(ovr - league_ovr, -10, 10)
    return round(clamp(r, 5.5, 9.3), 2)

# ---------- очки Золотого мяча / символических сборных ----------
# вес гола, передачи, матча, сухого матча
PTS_W = {"ST": (1.0, 0.7, 0.0, 0.0), "CF": (1.0, 0.75, 0.0, 0.0), "LW": (1.05, 0.8, 0.05, 0.0), "RW": (1.05, 0.8, 0.05, 0.0),
         "CAM": (1.1, 0.85, 0.08, 0.0), "LM": (1.15, 0.85, 0.1, 0.0), "RM": (1.15, 0.85, 0.1, 0.0), "CM": (1.3, 0.95, 0.2, 0.0),
         "CDM": (1.5, 1.0, 0.25, 0.0), "LB": (1.4, 1.0, 0.15, 0.12), "RB": (1.4, 1.0, 0.15, 0.12), "CB": (1.6, 1.0, 0.15, 0.2),
         "GK": (0.0, 0.0, 0.15, 0.6)}
CONT_PTS = {"UCL": {"W": 25, "F": 14, "SF": 8, "QF": 4, "R16": 1.5}, "UEL": {"W": 10, "F": 5, "SF": 3, "QF": 1},
            "UECL": {"W": 5, "F": 2.5, "SF": 1}, "USC": {"W": 2}, "LIB": {"W": 14, "F": 7, "SF": 4, "QF": 2},
            "SUD": {"W": 5, "F": 2.5, "SF": 1}, "ACLE": {"W": 8, "F": 4, "SF": 2}, "CCC": {"W": 6, "F": 3, "SF": 1.5}}
NAT_PTS = {"WC": {"W": 30, "F": 16, "SF": 10, "QF": 4, "R16": 1}, "EURO": {"W": 18, "F": 9, "SF": 5, "QF": 2},
           "CA": {"W": 18, "F": 9, "SF": 5, "QF": 2}, "AFCON": {"W": 10, "F": 5, "SF": 3}, "ASIAN": {"W": 10, "F": 5, "SF": 3},
           "GOLD": {"W": 5, "F": 2.5}, "OFCNC": {"W": 1}, "UNL": {"W": 4, "F": 2}}

def club_team_points(comps, ls, tier=1):
    """Очки за успехи клуба: comps - турниры клуба (world.club_comps)."""
    lf = ls / 100.0
    t = 0.0
    for c in comps:
        r, code = c["result"], c["code"]
        if code == "league":
            if r["rank"] == 1:
                t += (14 if tier == 1 else 2) * lf
            elif r["rank"] <= 4 and tier == 1:
                t += 2 * lf
        elif code == "cup":
            t += {"W": 4, "F": 1}.get(r.get("stage"), 0) * lf
        elif code == "league_cup":
            t += 1.5 * lf if r.get("stage") == "W" else 0
        elif code == "supercup":
            t += 1 * lf if r.get("stage") == "W" else 0
        elif code in CONT_PTS:
            t += CONT_PTS[code].get(r.get("stage"), 0)
    return t

def nat_points(stages):
    """stages: [(код турнира, стадия)] сборной за сезон."""
    return sum(NAT_PTS.get(code, {}).get(st, 0) for code, st in stages)

# голосование за Золотой мяч исторически любит атакующих: вратари и защитники выигрывают его крайне редко
BDO_APPEAL = {"GK": 0.7, "CB": 0.8, "LB": 0.8, "RB": 0.8, "CDM": 0.9, "CM": 0.95}

def ballon_points(pos, apps, goals, assists, cs, ls, ovr, team_pts):
    wg, wa, wp, wc = PTS_W[pos]
    ind = (goals * wg + assists * wa + apps * wp + cs * wc) * (0.25 + 0.75 * ls / 100.0)
    return round(ind + team_pts + (ovr - 80) * 1.2, 1)
