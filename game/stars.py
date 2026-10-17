"""Звёзды мира: соперники вашего игрока в борьбе за Золотой мяч, символические сборные и бутсы.

На старте (сезон 2026/27) это реальные звёзды с клубами по данным до лета 2026 года (могли смениться).
Каждый сезон звёзды играют за свои клубы и сборные по той же модели, что и ваш игрок (stats.py), стареют,
переходят в другие клубы и уходят из элиты. Реальные перспективные игроки (PROSPECTS) растут вне элиты и попадают в звёзды,
только если раскрылись; у молодых звёзд и перспективных игроков потенциал в каждой карьере свой. Известные игроки клубов
(NOTABLE, pool["others"]) живут своей жизнью и первыми занимают освободившиеся места среди звёзд; когда реальные игроки
заканчиваются - молодые таланты со сгенерированными именами.
"""
import csv
from .paths import DATA
from .player import clamp
from .positions import GROUP
from .stats import produce, clean_sheets, season_rating, club_team_points, nat_points, ballon_points
from .world import sigmoid, binom

POOL = 90
# Реальные игроки - в data/real_players.csv (tier: star - звёзды мира с первого сезона; prospect - перспективные игроки 16-22 лет;
# notable - известные игроки клубов). Возраст - в сезоне 2026/27, клубы - по данным до лета 2026 года (могли смениться).
#   star:     растут к потенциалу (pot_lo = pot_hi; у молодых в каждой карьере свой, см. young_pot), борются за Золотой мяч;
#   prospect: живут вне элиты и попадают в звёзды мира, только если дорастут до OVR 80; потенциал в каждой карьере свой
#             (от pot_lo до pot_hi, примерно каждый четвёртый не раскрывается и остаётся ниже pot_lo);
#   notable:  стареют, развиваются и переходят в другие клубы; заполняют освободившиеся места среди звёзд мира раньше
#             сгенерированных талантов; видны в составах клубов и на трансферном рынке тренера.
def _load_real():
    starters, prospects, notable = [], [], []
    with open(DATA / "real_players.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            base = (r["name"], r["nat"], r["pos"], int(r["age"]), int(r["ovr"]))
            if r["tier"] == "star":
                starters.append(base + (int(r["pot_hi"]), r["club"]))
            elif r["tier"] == "prospect":
                prospects.append(base + (int(r["pot_lo"]), int(r["pot_hi"]), r["club"]))
            else:
                notable.append(base + (int(r["pot_lo"]), int(r["pot_hi"]), r["club"]))
    return starters, prospects, notable

# STARTERS: (имя, сборная, позиция, возраст, OVR, потенциал, клуб); PROSPECTS и NOTABLE: (..., OVR, pot_lo, pot_hi, клуб)
STARTERS, PROSPECTS, NOTABLE = _load_real()
PROMOTE_OVR = 80        # перспективный игрок с таким OVR входит в звёзды мира
PROSPECT_GIVE_UP = 24   # в этом возрасте не доросший до элиты перестаёт считаться перспективным
OTHER_TO_STAR = 80      # известный игрок клуба с таким OVR (и не старше 31) может занять освободившееся место среди звёзд
OTHER_RETIRE = 37       # известные игроки уходят из футбола в этом возрасте (или раньше, если OVR упал ниже 64)
OTHERS_MIN = 300        # меньше известных игроков клубов не бывает: когда реальные уходят, приходят сгенерированные
PROTECTED = set()       # клубы, составом которых управляет тренер: мир не переводит игроков ни из них, ни в них

# ---------- генерация имён новых талантов ----------
NAMES = {
    "es": (["Alejandro", "Pablo", "Diego", "Javier", "Sergio", "Mateo", "Nicolás", "Thiago", "Martín", "Hugo", "Álvaro", "Iker", "Marcos",
             "Gonzalo", "Joaquín", "Santiago", "Emiliano", "Facundo", "Valentín", "Bruno", "Lucas", "Adrián", "Rodrigo", "Tomás"],
           ["García", "Fernández", "Rodríguez", "López", "Martínez", "Sánchez", "Pérez", "Gómez", "Romero", "Torres", "Ruiz", "Navarro",
            "Molina", "Ortega", "Castro", "Herrera", "Medina", "Vega", "Rojas", "Suárez", "Acosta", "Benítez", "Paredes", "Correa"]),
    "pt": (["João", "Pedro", "Gabriel", "Rafael", "Lucas", "Matheus", "Vitor", "Gustavo", "Thiago", "Bruno", "Diogo", "Rodrigo", "Tiago",
             "André", "Gonçalo", "Henrique", "Caio", "Davi", "Enzo", "Murilo"],
           ["Silva", "Santos", "Oliveira", "Souza", "Costa", "Pereira", "Almeida", "Ferreira", "Carvalho", "Gomes", "Ribeiro", "Martins",
            "Rocha", "Lima", "Araújo", "Mendes", "Nunes", "Moreira", "Barbosa", "Teixeira"]),
    "en": (["Jack", "Harry", "James", "Oliver", "Charlie", "George", "Mason", "Callum", "Jacob", "Ethan", "Kai", "Leo", "Alfie", "Archie",
             "Noah", "Tyler", "Reece", "Jayden", "Liam", "Connor"],
           ["Smith", "Jones", "Taylor", "Brown", "Wilson", "Walker", "Wright", "Clarke", "Hughes", "Ward", "Morgan", "Bennett", "Hill",
            "Cooper", "Mitchell", "Turner", "Robinson", "Hall", "Green", "Doherty"]),
    "fr": (["Lucas", "Hugo", "Théo", "Nathan", "Enzo", "Mathis", "Rayan", "Ilyes", "Maxime", "Antoine", "Adrien", "Moussa", "Ibrahima",
             "Yanis", "Evan", "Mathys", "Kylian", "Sacha", "Bradley", "Malo"],
           ["Martin", "Bernard", "Dubois", "Moreau", "Laurent", "Lefebvre", "Fofana", "Diallo", "Camara", "Koné", "Traoré", "Mendy",
            "Girard", "Bonnet", "Guerin", "Kamara", "Sissoko", "Mbaye", "Lacroix", "Faure"]),
    "de": (["Lukas", "Leon", "Felix", "Jonas", "Maximilian", "Paul", "Niklas", "Tim", "Jan", "Florian", "Moritz", "Finn", "Luca", "Ben",
             "Elias", "Noah"],
           ["Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Wagner", "Becker", "Hoffmann", "Koch", "Richter", "Wolf", "Neuhaus",
            "Brandt", "Schulz", "Krämer", "Lehmann"]),
    "it": (["Lorenzo", "Matteo", "Alessandro", "Andrea", "Francesco", "Federico", "Davide", "Riccardo", "Giacomo", "Nicolò", "Samuele",
             "Tommaso", "Gabriele", "Pietro"],
           ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo", "Ricci", "Marino", "Greco", "Bruno", "Gallo",
            "Conti", "De Luca", "Mancini", "Lombardi"]),
    "nl": (["Daan", "Sem", "Jesse", "Thijs", "Milan", "Lars", "Ruben", "Bram", "Luuk", "Xavi", "Jorrel", "Noa"],
           ["de Jong", "Jansen", "de Vries", "van Dijk", "Bakker", "Visser", "Smit", "Meijer", "Mulder", "Peeters", "Janssens", "Maes"]),
    "sl": (["Ivan", "Luka", "Marko", "Nikola", "Filip", "Jakub", "Dominik", "Matej", "Andrei", "Mateusz", "Petar", "Stefan", "Artem", "Kirill"],
           ["Novak", "Kovač", "Horvat", "Petrović", "Jovanović", "Nowak", "Kowalski", "Popescu", "Ionescu", "Dvořák", "Kovalenko",
            "Bondarenko", "Ivanov", "Smirnov", "Marić", "Babić"]),
    "sc": (["Erik", "Oscar", "William", "Elias", "Mathias", "Jonas", "Emil", "Kasper", "Viktor", "Magnus", "Sander", "Lucas"],
           ["Hansen", "Johansson", "Andersen", "Larsen", "Nielsen", "Karlsson", "Berg", "Lindqvist", "Eriksen", "Olsen", "Holm", "Dahl"]),
    "af": (["Victor", "Samuel", "Emmanuel", "Moses", "Ibrahim", "Sadio", "Ismaïla", "Kelechi", "Mohammed", "Yaw", "Kwame", "Ademola",
             "Cheikh", "Amadou", "Lamine", "Pape"],
           ["Osei", "Mensah", "Boateng", "Okafor", "Adeyemi", "Diop", "Sarr", "Ndiaye", "Onana", "Asante", "Eze", "Okonkwo", "Bamba",
            "Touré", "Gueye", "Cissé"]),
    "ar": (["Youssef", "Achraf", "Hakim", "Mohamed", "Riyad", "Ismael", "Amine", "Omar", "Karim", "Salem", "Bilal", "Ilias", "Saud", "Fahad"],
           ["Benali", "Bensaïd", "Haddad", "El Amrani", "Mansouri", "Brahimi", "Ounahi", "Aboukhlal", "Al-Dawsari", "Al-Shehri",
            "Al-Faraj", "Hamdi", "Ziani", "Belkacem"]),
    "tr": (["Arda", "Kerem", "Kenan", "Hakan", "Orkun", "Ferdi", "Barış", "Emre", "Cengiz", "Yusuf", "Semih", "Can"],
           ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Aydın", "Öztürk", "Arslan", "Güler", "Yıldız", "Kökçü", "Akgün"]),
    "jp": (["Takumi", "Kaoru", "Ritsu", "Daichi", "Takefusa", "Yuto", "Kota", "Hiroki", "Ao", "Sota"],
           ["Tanaka", "Suzuki", "Takahashi", "Watanabe", "Ito", "Yamamoto", "Nakamura", "Kubo", "Mitoma", "Endo"]),
    "kr": (["Min-jae", "Heung-min", "Kang-in", "Jae-sung", "Hyun-woo", "Seung-ho", "Jun-ho", "Ji-sung"],
           ["Kim", "Lee", "Park", "Choi", "Son", "Hwang", "Jung", "Yang"]),
    "cn": (["Wei", "Lei", "Hao", "Jun", "Tao", "Yang", "Chen", "Bo"], ["Wang", "Li", "Zhang", "Liu", "Chen", "Wu", "Zhao", "Huang"]),
    "ca": (["Alisher", "Bauyrzhan", "Islam", "Ramazan", "Askhat", "Dastan", "Nurlan", "Arsen", "Timur", "Daniyar", "Abbos", "Eldor"],
           ["Zhaksylykov", "Seydakhmet", "Tagybergen", "Kenzhebek", "Ismailov", "Abiken", "Orazov", "Fayzullaev", "Mamedov", "Aliyev"]),
    "gr": (["Giorgos", "Dimitris", "Konstantinos", "Christos", "Nikos", "Vangelis"],
           ["Papadopoulos", "Georgiou", "Nikolaidis", "Konstantinidis", "Pavlidis", "Tzolis"]),
}
REGION = {}
for _r, _codes in {
    "es": "ESP ARG URU COL CHI PER ECU PAR BOL VEN MEX CRC HON PAN SLV GUA CUB DOM NCA PUR",
    "pt": "POR BRA ANG MOZ CPV GNB STP", "en": "ENG SCO WAL NIR IRL USA CAN AUS NZL JAM TRI",
    "fr": "FRA HAI", "de": "GER AUT SUI LIE LUX", "it": "ITA SMR MLT", "nl": "NED BEL SUR",
    "sl": "CRO SRB SVN BIH MNE MKD POL CZE SVK UKR RUS BLR BUL ROU MDA ALB KOS HUN LVA LTU EST GEO ARM",
    "sc": "NOR SWE DEN ISL FIN FRO", "ar": "MAR ALG TUN EGY LBY KSA QAT UAE IRQ JOR SYR LBN KUW BHR OMA YEM PLE IRN",
    "tr": "TUR", "jp": "JPN", "kr": "KOR PRK", "cn": "CHN HKG TPE", "ca": "KAZ UZB KGZ TJK TKM AZE", "gr": "GRE CYP",
}.items():
    for _c in _codes.split():
        REGION[_c] = _r
CONF_REGION = {"UEFA": "sl", "CAF": "af", "AFC": "ar", "CONCACAF": "es", "CONMEBOL": "es", "OFC": "en"}
REGEN_NATS = {"FRA": 10, "ESP": 9, "ENG": 9, "BRA": 9, "GER": 7, "ARG": 7, "POR": 6, "NED": 5, "ITA": 5, "BEL": 4, "CRO": 2, "NOR": 2,
              "URU": 2, "COL": 2, "MAR": 2, "SEN": 2, "NGA": 2, "CIV": 2, "USA": 2, "JPN": 2, "TUR": 2, "DEN": 2, "SUI": 1, "AUT": 1,
              "POL": 1, "KOR": 1, "SRB": 1, "ECU": 1, "GHA": 1, "CMR": 1, "ALG": 1, "SWE": 1, "SCO": 1, "GEO": 1, "UKR": 1, "CZE": 1}
GROUP_TARGET = {"GK": 9, "DEF": 24, "MID": 28, "ATT": 29}   # состав пула звёзд по линиям (в сумме POOL)
REGEN_POS = {"GK": 2, "CB": 4, "LB": 2, "RB": 2, "CDM": 2, "CM": 4, "CAM": 3, "LM": 1, "RM": 1, "LW": 3, "RW": 3, "CF": 1, "ST": 5}

def gen_name(rng, nat, conf):
    first, last = NAMES[REGION.get(nat) or CONF_REGION.get(conf, "en")]
    return f"{rng.choice(first)} {rng.choice(last)}"

MAX_PER_CLUB = 4          # больше звёзд в одном клубе не собирается

def _elite_clubs(world, min_ovr, pool=None):
    full = set()
    if pool:
        cnt = {}
        for s in pool["list"]:
            cnt[s["club"]] = cnt.get(s["club"], 0) + 1
        full = {c for c, n in cnt.items() if n >= MAX_PER_CLUB}
    return [c for c in world.club_league if not world.d.clubs[c]["reserve"] and world.team_ovr(c) >= min_ovr and c not in full
            and c not in PROTECTED]

def young_pot(rng, pot, age):
    """Потенциал молодой звезды в этой карьере: указанный - лишь ориентир. Обычно около него, иногда выше, иногда игрок застревает."""
    if age > 23:
        return float(pot)
    u = rng.random()
    if u < 0.15:
        return round(pot - rng.uniform(3, 6), 1)          # не раскрылся
    if u > 0.90:
        return round(min(97.0, pot + rng.uniform(1, 3)), 1)
    return round(pot + rng.gauss(0, 1.2), 1)

def prospect_pot(rng, lo, hi):
    """Потенциал перспективного игрока: ~25% не раскрываются (ниже lo), большинство ближе к нижней границе, ~15% к верхней."""
    u = rng.random()
    if u < 0.25:
        return round(rng.uniform(lo - 5, lo), 1)
    if u < 0.85:
        return round(rng.triangular(lo, hi, lo + 0.3 * (hi - lo)), 1)
    return round(rng.uniform(lo + 0.6 * (hi - lo), hi), 1)

def new_pool(world, rng):
    pool = {"next": 1, "list": [], "prospects": []}
    for name, nat, pos, age, ovr, pot, club in STARTERS:
        if club not in world.club_league:
            continue
        pool["list"].append({"id": f"s{pool['next']}", "name": name, "nat": nat, "pos": pos, "age": age, "ovr": float(ovr),
                             "pot": young_pot(rng, pot, age), "club": club, "real": True})
        pool["next"] += 1
    for name, nat, pos, age, ovr, lo, hi, club in PROSPECTS:
        if club not in world.club_league:
            continue
        pool["prospects"].append({"id": f"s{pool['next']}", "name": name, "nat": nat, "pos": pos, "age": age, "ovr": float(ovr),
                                  "pot": prospect_pot(rng, lo, hi), "club": club, "real": True, "prospect": True})
        pool["next"] += 1
    pool["others"] = []
    for name, nat, pos, age, ovr, lo, hi, club in NOTABLE:
        if club not in world.club_league:
            continue
        pool["others"].append({"id": f"s{pool['next']}", "name": name, "nat": nat, "pos": pos, "age": age, "ovr": float(ovr),
                               "pot": round(rng.uniform(lo, hi), 1) if hi > lo else float(hi), "club": club, "real": True})
        pool["next"] += 1
    fill(pool, world, rng)
    return pool

def all_players(pool):
    """Все известные игроки мира: звёзды, перспективные и известные игроки клубов."""
    return pool["list"] + pool.get("prospects", []) + pool.get("others", [])

def players_at(pool, cid):
    """Известные игроки клуба (по убыванию OVR)."""
    return sorted((s for s in all_players(pool) if s["club"] == cid), key=lambda s: -s["ovr"])

def find(pool, pid):
    return next((s for s in all_players(pool) if s["id"] == pid), None)

def add_other(pool, name, nat, pos, age, ovr, pot, club, real=False):
    """Новый известный игрок (например, купленный тренером игрок с рынка): дальше живёт в мире как остальные."""
    s = {"id": f"s{pool['next']}", "name": name, "nat": nat, "pos": pos, "age": age, "ovr": float(ovr), "pot": float(pot),
         "club": club, "real": real}
    pool["next"] += 1
    pool.setdefault("others", []).append(s)
    return s

def regen(pool, world, rng):
    d = world.d
    nat = rng.choices(list(REGEN_NATS), weights=list(REGEN_NATS.values()))[0]
    have = {}
    for x in pool["list"]:
        have[GROUP[x["pos"]]] = have.get(GROUP[x["pos"]], 0) + 1
    need = {g: GROUP_TARGET[g] - have.get(g, 0) for g in GROUP_TARGET}
    short = [g for g, v in need.items() if v > 0]
    poss = [x for x in REGEN_POS if not short or GROUP[x] in short]
    pos = rng.choices(poss, weights=[REGEN_POS[x] for x in poss])[0]
    pot = clamp(rng.gauss(89.5, 2.6), 85, 97)
    ovr = max(80.0, pot - rng.uniform(4, 9))
    home = [c for c in _elite_clubs(world, 74, pool) if d.clubs[c]["country"] == nat]
    elite = _elite_clubs(world, 77, pool) or _elite_clubs(world, 70)
    club = rng.choice(home) if home and rng.random() < 0.45 else rng.choices(elite, weights=[world.score[c] ** 2 for c in elite])[0]
    s = {"id": f"s{pool['next']}", "name": gen_name(rng, nat, d.countries[nat]["conf"]), "nat": nat, "pos": pos,
         "age": rng.randint(18, 20), "ovr": round(ovr, 1), "pot": round(pot, 1), "club": club, "real": False}
    pool["next"] += 1
    return s

def fill(pool, world, rng):
    """Добор звёзд до POOL: сначала лучшие реальные известные игроки (OVR 80+, не старше 31), потом сгенерированные таланты."""
    others = pool.setdefault("others", [])
    while len(pool["list"]) < POOL:
        cand = [s for s in others if s["ovr"] >= OTHER_TO_STAR and s["age"] <= 31]
        if cand:
            best = max(cand, key=lambda s: s["ovr"])
            others.remove(best); pool["list"].append(best)
        else:
            pool["list"].append(regen(pool, world, rng))

def _evolve_others(pool, world, rng):
    """Известные игроки клубов: возраст и форма, иногда переход в клуб своего уровня, уход из футбола."""
    keep = []
    for s in pool.setdefault("others", []):
        _age_one(s, rng)
        if s["age"] >= OTHER_RETIRE or (s["ovr"] < 64 and not s.get("squad")):   # игроки состава тренера - только по возрасту
            continue
        if s["club"] not in world.club_league:
            s["club"] = rng.choice(list(world.club_league))
        team = world.team_ovr(s["club"])
        if s["club"] not in PROTECTED and not s.get("loan_from") and rng.random() < (0.12 if abs(s["ovr"] - team) > 4 else 0.06):   # не по уровню - уходит чаще
            cands = [c for c in world.club_league if not world.d.clubs[c]["reserve"] and abs(world.team_ovr(c) - s["ovr"]) <= 3
                     and c != s["club"] and c not in PROTECTED]
            if cands:
                s["club"] = rng.choice(cands)
        keep.append(s)
    pool["others"] = keep
    # реальные игроки со временем уходят: список известных игроков пополняется сгенерированными (по уровню клубов)
    while len(pool["others"]) < OTHERS_MIN:
        pool["others"].append(regen_other(pool, world, rng))

def regen_other(pool, world, rng):
    """Сгенерированный известный игрок клуба: клуб - чаще сильный, OVR около уровня клуба, возраст 18-29."""
    d = world.d
    clubs = [c for c in world.club_league if not d.clubs[c]["reserve"] and world.team_ovr(c) >= 66 and c not in PROTECTED]
    club = rng.choices(clubs, weights=[max(1.0, world.score[c]) ** 1.5 for c in clubs])[0]
    team = world.team_ovr(club)
    lc = d.leagues[world.club_league[club]]["country"]
    nat = lc if rng.random() < 0.55 else rng.choices(list(REGEN_NATS), weights=list(REGEN_NATS.values()))[0]
    age = rng.randint(18, 29)
    ovr = clamp(team + rng.gauss(0, 2.5) - (3 if age <= 20 else 0), 60, 86)
    pot = ovr + (rng.uniform(2, 8) if age <= 22 else rng.uniform(0, 2))
    pos = rng.choices(list(REGEN_POS), weights=list(REGEN_POS.values()))[0]
    s = {"id": f"s{pool['next']}", "name": gen_name(rng, nat, d.countries[nat]["conf"]), "nat": nat, "pos": pos, "age": age,
         "ovr": round(ovr, 1), "pot": round(min(pot, 92), 1), "club": club, "real": False}
    pool["next"] += 1
    return s

def league_ga_pg(res, lid):
    t = res["tables"][lid]
    return sum(t["ga"].values()) / max(1, len(t["order"]) * t["games"])

def nat_stage_list(res, nat):
    return [(code, r["stage"][nat]) for code, r in res["nat"].items() if nat in r["stage"]]

def simulate(pool, world, res, rng):
    """Сезон звёзд. -> список итогов (статистика, оценка, очки Золотого мяча)."""
    out, cache = [], {}
    for s in pool["list"]:
        cid = s["club"]
        if cid not in world.club_league:
            continue
        comps = cache.get(cid) or cache.setdefault(cid, world.club_comps(res, cid))
        team, ovr, pos = world.team_ovr(cid), s["ovr"], s["pos"]
        share = min(0.95, sigmoid((ovr - team + 4) / 3.0))
        if rng.random() < 0.25:
            share *= rng.uniform(0.5, 0.9)                        # травма
        apps = goals = assists = cs = 0
        lg = {"apps": 0, "goals": 0, "assists": 0, "cs": 0}
        tg_total = 0
        for c in comps:
            tg = c["team_games"]; tg_total += tg
            n = binom(rng, tg, share * (0.8 if c["code"] in ("cup", "league_cup") else 1.0))
            g, a, *_ = produce(rng, pos, ovr, team, c["opp"], n)
            k = clean_sheets(rng, n, team, c["opp"])[0] if GROUP[pos] in ("GK", "DEF") else 0
            apps += n; goals += g; assists += a; cs += k
            if c["code"] == "league":
                lg = {"apps": n, "goals": g, "assists": a, "cs": k}
        league = comps[0]
        lid = league["lid"]
        lcountry = world.d.leagues[lid]["country"]
        ls = world.league_strength(lcountry)
        tier = world.d.leagues[lid]["tier"]
        club_pts = club_team_points(comps, ls, tier) if apps >= 0.35 * tg_total else 0.0
        nat_ovr = world.nat_ovr(s["nat"]) if s["nat"] in world.nat else 70
        stages = [x for x in nat_stage_list(res, s["nat"]) if rng.random() < sigmoid((ovr - nat_ovr + 3) / 2.0)]
        pts = ballon_points(pos, apps, goals, assists, cs, ls, ovr, club_pts + nat_points(stages))
        r = league["result"]
        lgames = max(1, league["team_games"])
        rating = season_rating(pos, apps, goals, assists, cs, ovr, league["opp"], r["rank"], r["n"], r["ga"] / lgames, league_ga_pg(res, lid))
        out.append({"id": s["id"], "name": s["name"], "nat": s["nat"], "pos": pos, "age": s["age"], "ovr": round(ovr), "club": cid,
                    "league": lid, "apps": apps, "goals": goals, "assists": assists, "cs": cs, "lg": lg, "lg_team_games": lgames,
                    "rating": rating, "pts": pts})
    return out

def _age_one(s, rng):
    """Год жизни звезды или перспективного игрока: рост к потенциалу до 28 лет, плато, спад после 30."""
    s["age"] += 1
    a, o = s["age"], s["ovr"]
    if a <= 23:
        # игроки тренера (и его арендованные) растут по сыгранным минутам: без игры - втрое медленнее
        m = s["loan_min"] if "loan_min" in s else (s.get("min_season") if s.get("squad") else None)
        k = 1.0 if m is None else min(1.15, 0.35 + 0.9 * m)
        o += max(0.0, s["pot"] - o) * rng.uniform(0.2, 0.45) * k + rng.gauss(0, 0.5)
    elif a <= 28:
        o += max(0.0, s["pot"] - o) * rng.uniform(0.1, 0.35) + rng.gauss(0, 0.7)
    elif a <= 30:
        o += rng.gauss(-0.3, 0.8)
    else:
        o -= {31: 0.7, 32: 1.1, 33: 1.5, 34: 1.9, 35: 2.3}.get(a, 2.8) + abs(rng.gauss(0, 0.6))
    s["ovr"] = round(min(o, 97.0), 1)

def _grow_prospects(pool, world, rng):
    """Перспективные игроки: кто дорос до элиты - в звёзды мира (сильный клуб может забрать его к себе), кто не успел к 24 - уходит."""
    left = []
    for s in pool.setdefault("prospects", []):
        _age_one(s, rng)
        if s["ovr"] >= PROMOTE_OVR:
            if s["club"] not in world.club_league or (s["club"] not in PROTECTED and not s.get("loan_from") and world.team_ovr(s["club"]) < 76 and rng.random() < 0.5):
                cands = _elite_clubs(world, 78, pool)
                if cands:
                    s["club"] = rng.choices(cands, weights=[world.score[c] ** 2 for c in cands])[0]
            pool["list"].append(s)
        elif s["age"] < PROSPECT_GIVE_UP:
            left.append(s)
    pool["prospects"] = left

def evolve(pool, world, rng):
    """Конец сезона: возраст, рост/спад, уход из элиты, переходы, перспективные игроки, новые таланты."""
    _evolve_others(pool, world, rng)          # до звёзд: выпавшие из элиты в этом сезоне не стареют дважды
    keep = []
    for s in pool["list"]:
        _age_one(s, rng)
        a = s["age"]
        if a >= 38 or (a >= 33 and s["ovr"] < 81) or s["ovr"] < 79:
            if a < OTHER_RETIRE and s["ovr"] >= 64:              # ушёл из элиты, но ещё играет: доигрывает как известный игрок клуба
                pool.setdefault("others", []).append(s)
            continue
        if s["club"] not in world.club_league:
            s["club"] = rng.choice(_elite_clubs(world, 76, pool) or _elite_clubs(world, 70))
        team = world.team_ovr(s["club"])
        r = 1.0 if s["club"] in PROTECTED or s.get("loan_from") else rng.random()      # составом клуба тренера управляет тренер
        if a >= 31 and r < 0.10:
            rich = [c for c in world.club_league if world.d.leagues[world.club_league[c]]["country"] in ("KSA", "USA")
                    and world.team_ovr(c) >= 69 and c not in PROTECTED]
            if rich:
                s["club"] = rng.choice(rich)
        elif s["ovr"] >= team + 1 and r < 0.18:
            cands = [c for c in _elite_clubs(world, max(team + 1, 79), pool) if c != s["club"]]
            if cands:
                s["club"] = rng.choices(cands, weights=[world.score[c] ** 2 for c in cands])[0]
        keep.append(s)
    pool["list"] = keep
    _grow_prospects(pool, world, rng)
    fill(pool, world, rng)
