"""Тренеры мира - соперники в борьбе за награду «Лучший тренер мира».

Реальные тренеры топ-клубов (назначения - сезон 2025/26, возраст - на 2026 год) стареют вместе с миром, иногда меняют клуб
своего уровня и уходят на пенсию в 70; на их место в топ-клубах приходят сгенерированные тренеры.
Очки сезона = успехи клуба (как в Золотом мяче: титул, кубки, еврокубки) + 20 x перевыполнение задачи + немного за навык.
Состояние - career.coach["rivals"] (сохраняется с карьерой).
"""
import math
from .player import clamp
from .stats import club_team_points
from . import stars as stars_mod

START = 2026
RETIRE = 70
TOP_CLUBS = 36          # столько сильнейших клубов мира всегда имеют «известного» тренера
# имя, страна, возраст в 2026, клуб, навык
REAL = [
    ("Pep Guardiola", "ESP", 55, "eng-manchester-city", 92), ("Luis Enrique", "ESP", 56, "fra-paris-saint-germain", 91),
    ("Mikel Arteta", "ESP", 44, "eng-arsenal-fc", 88), ("Hansi Flick", "GER", 61, "esp-fc-barcelona", 88),
    ("Xabi Alonso", "ESP", 44, "esp-real-madrid", 87), ("Arne Slot", "NED", 47, "eng-liverpool-fc", 86),
    ("Antonio Conte", "ITA", 57, "ita-ssc-napoli", 86), ("Vincent Kompany", "BEL", 40, "ger-bayern-munich", 85),
    ("Diego Simeone", "ARG", 56, "esp-atletico-de-madrid", 85), ("Unai Emery", "ESP", 54, "eng-aston-villa", 85),
    ("Simone Inzaghi", "ITA", 50, "ksa-al-hilal", 84), ("Gian Piero Gasperini", "ITA", 68, "ita-as-roma", 84),
    ("Massimiliano Allegri", "ITA", 59, "ita-ac-milan", 83), ("José Mourinho", "POR", 63, "por-sl-benfica", 82),
    ("Luciano Spalletti", "ITA", 67, "ita-juventus-fc", 82), ("Roberto De Zerbi", "ITA", 47, "fra-olympique-marseille", 82),
    ("Oliver Glasner", "AUT", 51, "eng-crystal-palace", 81), ("Eddie Howe", "ENG", 48, "eng-newcastle-united", 81),
    ("Cristian Chivu", "ROU", 45, "ita-inter-milan", 80), ("Andoni Iraola", "ESP", 43, "eng-afc-bournemouth", 80),
    ("Niko Kovač", "CRO", 54, "ger-borussia-dortmund", 80), ("Francesco Farioli", "ITA", 37, "por-fc-porto", 80),
    ("Thomas Frank", "DEN", 52, "eng-tottenham-hotspur", 79), ("Peter Bosz", "NED", 62, "ned-psv-eindhoven", 79),
    ("Okan Buruk", "TUR", 52, "tur-galatasaray", 79), ("Kasper Hjulmand", "DEN", 54, "ger-bayer-04-leverkusen", 78),
    ("Rui Borges", "POR", 44, "por-sporting-cp", 78), ("Enzo Maresca", "ITA", 46, "eng-chelsea-fc", 80),
    ("Ruben Amorim", "POR", 41, "eng-manchester-united", 79), ("Fabian Hürzeler", "GER", 33, "eng-brighton-hove-albion", 77),
]

def _skill_step(age, rng):
    """Навык тренера за год: растёт до ~50 лет, потом медленно падает."""
    return (0.5 if age < 50 else -0.3 if age >= 62 else 0.0) + rng.gauss(0, 0.8)

def _gen(c, cid, age=None):
    rng, d = c.rng, c.d
    nat = d.clubs[cid]["country"] if rng.random() < 0.5 else rng.choices(list(stars_mod.REGEN_NATS), weights=list(stars_mod.REGEN_NATS.values()))[0]
    if nat not in d.countries:
        nat = "ESP"
    sc = c.world.score[cid]
    return {"name": stars_mod.gen_name(rng, nat, d.countries[nat]["conf"]), "nat": nat, "age": age or rng.randint(38, 55),
            "skill": round(clamp(60 + 0.3 * sc + rng.gauss(0, 4), 55, 90), 1), "club": cid, "real": False}

def _top_clubs(c):
    w = c.world
    ids = [x for x in w.club_league if not c.d.clubs[x]["reserve"] and c.d.leagues[w.club_league[x]]["tier"] == 1]
    return sorted(ids, key=lambda x: -w.score[x])[:TOP_CLUBS]

def init(c):
    """Тренеры мира к началу тренерской карьеры игрока: реальные постарели на прошедшие годы и могли сменить клуб."""
    rng, w = c.rng, c.world
    years = max(0, c.year - START)
    out = []
    for name, nat, age, club, skill in REAL:
        a = age + years
        if a >= RETIRE:
            continue
        sk = skill
        for k in range(years):
            sk += _skill_step(age + k, rng)
        if club not in w.club_league or rng.random() < 1 - 0.8 ** years:       # за годы мог уйти в другой клуб
            club = None
        out.append({"name": name, "nat": nat, "age": a, "skill": round(clamp(sk, 55, 95), 1), "club": club, "real": True})
    c.coach["rivals"] = out
    _staff(c)

def _staff(c):
    """У каждого топ-клуба - свой тренер; тренеры без клуба занимают свободные места своего уровня."""
    rng = c.rng
    riv = c.coach["rivals"]
    mine = c.coach.get("club")
    taken = {r["club"] for r in riv if r["club"]}
    for r in riv:                                         # клуб тренера-игрока занят им самим
        if r["club"] == mine:
            r["club"] = None
    free = sorted([r for r in riv if not r["club"]], key=lambda r: -r["skill"])
    for cid in _top_clubs(c):
        if cid in taken or cid == mine:
            continue
        if free and rng.random() < 0.7:
            r = free.pop(0); r["club"] = cid
        else:
            riv.append(_gen(c, cid))
        taken.add(cid)

def season(c, res, exp, me_pts):
    """Итоги сезона для тренеров мира. exp - {клуб: ожидаемое место} до сезона; me_pts - очки тренера-игрока.
    -> топ-5 [{name, club, pts, me}] и место игрока."""
    w, rng, d = c.world, c.rng, c.d
    if "rivals" not in c.coach:
        init(c)
    rows = []
    for r in c.coach["rivals"]:
        cid = r["club"]
        if not cid or cid not in w.club_league:
            continue
        rows.append({"name": r["name"], "nat": r["nat"], "club": cid, "pts": round(points(c, res, cid, exp.get(cid), r["skill"]), 1), "me": False})
    rows.append({"name": c.name, "nat": c.nat, "club": c.coach["club"], "pts": round(me_pts, 1), "me": True})
    rows.sort(key=lambda x: -x["pts"])
    rank = next(i for i, x in enumerate(rows, 1) if x["me"])
    return rows[:5], rank

def points(c, res, cid, exp_rank, skill):
    w, d = c.world, c.d
    comps = w.club_comps(res, cid)
    lid = w.club_league[cid]
    league = d.leagues[lid]
    ls = w.league_strength(league["country"])
    lg = comps[0]["result"]
    over = ((exp_rank or lg["rank"]) - lg["rank"]) / max(1, lg["n"] - 1)
    return club_team_points(comps, ls, league["tier"]) + 20 * over * ls / 100.0 + (skill - 70) * 0.1

def expectations(c, cc):
    """Ожидаемые места клубов тренеров мира (до начала сезона)."""
    if "rivals" not in c.coach:
        init(c)
    return {r["club"]: cc.expected(r["club"])[0] for r in c.coach["rivals"] if r["club"] and r["club"] in c.world.club_league}

def evolve(c):
    """Конец сезона: тренеры стареют, иногда переходят в клуб сильнее (после успеха) или теряют работу, уходят на пенсию."""
    rng, w = c.rng, c.world
    keep = []
    for r in c.coach.get("rivals", []):
        r["age"] += 1
        r["skill"] = round(clamp(r["skill"] + _skill_step(r["age"], rng), 50, 96), 1)
        if r["age"] >= RETIRE or (not r["real"] and not r["club"] and rng.random() < 0.4):
            continue
        if r["club"] and rng.random() < 0.12:
            r["club"] = None                                  # уволен или ушёл
        keep.append(r)
    c.coach["rivals"] = keep
    _staff(c)
