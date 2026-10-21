"""Мир: лиги, кубки, континентальные турниры клубов, сборные (отбор, финальные турниры, Лига наций),
переходы между дивизионами, дрейф силы клубов и сборных.

Счёт матчей на вылет хранится словарём с точки зрения первой команды:
    {"g": [голы1, голы2], "et": дополнительное время?, "p": [пенальти1, пенальти2] | нет, "legs": [[1-й матч], [2-й матч]] | нет}
"""
import math
from .data import stars_for

def poisson(rng, lam):
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    lim, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= lim:
            return k
        k += 1

def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-max(-30, min(30, x))))

def binom(rng, n, p):
    return sum(1 for _ in range(max(0, int(n))) if rng.random() < p)

def flip(sc):
    """Тот же счёт с точки зрения соперника."""
    if not sc:
        return sc
    o = {"g": [sc["g"][1], sc["g"][0]], "et": sc.get("et", False)}
    if sc.get("p"):
        o["p"] = [sc["p"][1], sc["p"][0]]
    if sc.get("legs"):
        o["legs"] = [[b, a] for a, b in sc["legs"]]
    return o

SENS = 0.024           # насколько разница в силе клубов (шкала 0..100) влияет на ожидаемые голы
MIN_SCORE = -32.5      # нижняя граница силы клуба (OVR 35, как в recompute_stars.py): полупрофессиональные лиги слабее OVR 48
UPDOWN = {"ENG": [3, 3, 4], "ESP": [3], "GER": [3, 3], "ITA": [3], "FRA": [3]}   # сколько клубов меняются между уровнями
# Дрейф силы между сезонами: сила клуба возвращается к его «базовой» (историческому уровню) на REVERT в год, чемпион получает
# небольшой толчок CHAMP_BONUS; базовая сила очень медленно (BASE_TO_MEAN) тянется к среднему лиги - гранды остаются грандами.
REVERT, CHAMP_BONUS, BASE_TO_MEAN = 0.2, 0.4, 0.01
# «Гегемон» лиги: время от времени один из сильнейших клубов высшей лиги (деньги, состав) на 5-10 сезонов уходит в отрыв -
# его сила тянется (HEG_REVERT в год) к уровню на HEG_LEAD выше сильнейшего соперника; тот же клуб - не чаще раза в HEG_COOLDOWN лет. Шанс начала эпохи - HEG_P за сезон, если
# гегемона нет; кандидаты - 6 сильнейших клубов, чем сильнее клуб, тем вероятнее (вес exp(сила / HEG_TEMP)).
HEG_P, HEG_YEARS, HEG_LEAD, HEG_MAX, HEG_REVERT, HEG_TEMP, HEG_COOLDOWN = 0.07, (5, 10), (5.0, 9.0), 25.0, 0.35, 8.0, 10
# «Форма сезона»: случайная добавка к силе клуба на один сезон (удачный или провальный год), на рейтинг клуба не влияет
FORM_SD = 3.5
# Отрыв базовой силы лидера лиги от второго клуба больше LEAD_GAP (~2.5 OVR) тает на LEAD_FADE в год: давний гегемон (ПСЖ, Бурирам)
# остаётся фаворитом, но не навсегда. Там, где гранды рядом (Реал, Барселона, Атлетико), это не срабатывает.
LEAD_GAP, LEAD_FADE = 6.0, 0.15
NAT_SIZES = {"WC": 48, "EURO": 24, "CA": 16, "AFCON": 24, "ASIAN": 24, "GOLD": 16, "OFCNC": 8}
WC_QUOTA = {"UEFA": 16, "CAF": 9, "AFC": 8, "CONMEBOL": 6, "CONCACAF": 6, "OFC": 1}      # + 2 места через межконтинентальный плей-офф
ADVANCE = {48: 32, 24: 16, 16: 8, 8: 4}
CUP_STAGE = {2: "F", 4: "SF", 8: "QF", 16: "R16", 32: "R32", 64: "R64", 128: "R128", 256: "R256"}
KO_STAGE = {32: "R32", 16: "R16", 8: "QF", 4: "SF", 2: "F"}
# форматы отбора: групп, прямых мест из группы (остальные места разыгрываются в стыковых матчах)
QUAL_FMT = {
    ("WC", "UEFA"): (12, 1), ("WC", "CAF"): (9, 1), ("WC", "AFC"): (8, 1), ("WC", "CONMEBOL"): (1, 6),
    ("WC", "CONCACAF"): (6, 1), ("WC", "OFC"): (2, 0),
    ("EURO", "UEFA"): (10, 2), ("AFCON", "CAF"): (12, 2), ("ASIAN", "AFC"): (8, 2), ("GOLD", "CONCACAF"): (8, 2), ("OFCNC", "OFC"): (2, 4),
}
IC_FROM = {"CONMEBOL": 1, "CONCACAF": 2, "AFC": 1, "CAF": 1, "OFC": 1}   # кандидаты межконтинентального плей-офф ЧМ
HOSTS = {("WC", 2030): ["ESP", "POR", "MAR", "ARG", "URU", "PAR"], ("WC", 2034): ["KSA"], ("EURO", 2032): ["ITA", "TUR"]}
WC_HOST_ROT = ["CONCACAF", "UEFA", "AFC", "CAF", "CONMEBOL"]
NAT_ORDER = ["WC", "EURO", "CA", "AFCON", "ASIAN", "GOLD", "OFCNC"]
# путёвки в еврокубки по месту страны в рейтинге UEFA: (до какого места, {(турнир, путь): места в лиге или "cup" - обладатель кубка}).
# direct - сразу на общий этап; champ - путь чемпионов в отборе ЛЧ; league - путь представителей лиг; qual - отборочные раунды ЛЕ и ЛК
EURO_ACCESS = [
    (4, {("UCL", "direct"): [1, 2, 3, 4], ("UEL", "direct"): [5, "cup"], ("UECL", "direct"): [6]}),
    (6, {("UCL", "direct"): [1, 2, 3], ("UEL", "direct"): [4, "cup"], ("UECL", "direct"): [5]}),
    (12, {("UCL", "direct"): [1], ("UCL", "league"): [2], ("UEL", "direct"): ["cup"], ("UEL", "qual"): [3], ("UECL", "qual"): [4]}),
    (15, {("UCL", "champ"): [1], ("UEL", "qual"): [2, "cup"], ("UECL", "qual"): [3]}),
    (25, {("UCL", "champ"): [1], ("UEL", "qual"): ["cup"], ("UECL", "qual"): [2, 3]}),
    (99, {("UCL", "champ"): [1], ("UECL", "qual"): [2, "cup"]}),
]
UCL_LEAGUE_PATH = 2                # мест в ЛЧ через путь представителей лиг (остальные отборочные места - путь чемпионов)
LIB_SLOTS = {"BRA": 7, "ARG": 6, "COL": 3, "ECU": 3, "PAR": 3, "CHI": 2, "PER": 2, "URU": 2, "BOL": 2, "VEN": 2}
SUD_SLOTS = {"BRA": 6, "ARG": 6, "COL": 3, "CHI": 3, "PER": 3, "ECU": 3, "URU": 3, "PAR": 2, "BOL": 2, "VEN": 1}
# ЛЧ АФК (Элит): по реальной раскладке мест между ассоциациями (запад - Саудовская Аравия, ОАЭ, Катар; восток - Япония, Корея, Китай, Таиланд, Австралия)
ACLE_SLOTS = {"KSA": 4, "JPN": 3, "KOR": 3, "UAE": 3, "QAT": 3, "CHN": 2, "THA": 2, "AUS": 2, "IND": 1}
# Кубок чемпионов КОНКАКАФ: только клубы Мексики и MLS (лиг Центральной Америки и Карибов в базе нет)
CCC_SLOTS = {"MEX": 6, "USA": 6}
CONT_ORDER = ["UCL", "UEL", "UECL", "USC", "LIB", "SUD", "ACLE", "CCC"]
PEN_SCORES = [(5, 4), (4, 3), (4, 2), (3, 2), (5, 3), (3, 1), (6, 5), (7, 6), (4, 1), (8, 7), (2, 1)]
PEN_W = [22, 20, 12, 12, 10, 6, 8, 4, 3, 2, 1]

def edition_years(code, nxt, cycle, upto=2075):
    if code == "AFCON":
        return [2027] + list(range(2028, upto, 4))
    return list(range(nxt, upto, cycle))

class World:
    def __init__(self, data, rng, year=2026):
        self.d, self.rng, self.year = data, rng, year
        self.score = {c: v["score"] for c, v in data.clubs.items()}
        self.base = dict(self.score)
        self.club_league = {c: v["league"] for c, v in data.clubs.items()}
        self.league_clubs = {l: [] for l in data.leagues}
        for c, l in self.club_league.items():
            self.league_clubs[l].append(c)
        self.nat = dict(data.nat_strength)
        self.unl_div = self._unl_divisions()
        self.prev_uel_winner = None
        self.hegemon = {}                  # лига -> {"club", "until" (последний сезон эпохи), "boost"}
        self.heg_last = {}                 # клуб -> последний сезон его эпохи гегемона
        self._form = {}                    # форма сезона: {клуб: добавка к силе}, разыгрывается в begin_season
        self._boost = {}
        self._tactics = {}                 # тактика тренера на время розыгрыша: {клуб: (множитель своих голов, пропущенных)}

    # ---------- доступ ----------
    def eff(self, cid):
        return self.score[cid] + self._boost.get(cid, 0.0) + self._form.get(cid, 0.0)

    def team_ovr(self, cid):
        return 48.0 + 0.40 * self.score[cid]

    def nat_ovr(self, code):
        return 48.0 + self.nat[code] / 2.5

    def stars(self, cid):
        return stars_for(self.score[cid])

    def league_of(self, cid):
        return self.d.leagues[self.club_league[cid]]

    def league_games(self, lid):
        return self.d.leagues[lid]["rounds"] * (len(self.league_clubs[lid]) - 1)

    def league_strength(self, country):
        v = self.d.countries[country]["lstrength"]
        return 35.0 if v is None else v

    def league_avg_ovr(self, lid):
        ids = self.league_clubs[lid]
        return sum(self.team_ovr(c) for c in ids) / max(1, len(ids))

    # ---------- матчи ----------
    def _lam(self, a, b, neutral=False):
        d = self.eff(a) - self.eff(b)
        if neutral:
            la, lb = 1.30 * math.exp(SENS * d), 1.30 * math.exp(-SENS * d)
        else:
            la, lb = 1.45 * math.exp(SENS * d), 1.15 * math.exp(-SENS * d)
        la, lb = self._tac(a, la, lb)
        lb, la = self._tac(b, lb, la)
        return la, lb

    def _pens(self, edge):
        w, l = self.rng.choices(PEN_SCORES, weights=PEN_W)[0]
        return [w, l] if self.rng.random() < max(0.3, min(0.7, edge)) else [l, w]

    def _finish(self, sc, la, lb, edge):
        """Ничья в основное время -> дополнительное время и, если нужно, пенальти. -> победила ли первая команда."""
        x, y = sc["g"]
        if x != y:
            return x > y
        ex, ey = poisson(self.rng, la / 3), poisson(self.rng, lb / 3)
        sc["g"] = [x + ex, y + ey]; sc["et"] = True
        if sc.get("legs"):
            sc["legs"][-1] = [sc["legs"][-1][0] + ex, sc["legs"][-1][1] + ey]
        if ex != ey:
            return ex > ey
        sc["p"] = self._pens(edge)
        return sc["p"][0] > sc["p"][1]

    def _ko1(self, a, b, neutral=False):
        """Один матч на вылет (a - хозяин). -> (победитель, счёт с точки зрения a)."""
        la, lb = self._lam(a, b, neutral)
        sc = {"g": [poisson(self.rng, la), poisson(self.rng, lb)], "et": False}
        win = self._finish(sc, la, lb, 0.5 + 0.004 * (self.eff(a) - self.eff(b)))
        return (a if win else b), sc

    def _ko2(self, a, b):
        """Два матча (первый дома у a). -> (победитель, счёт с точки зрения a, с результатами матчей)."""
        la1, lb1 = self._lam(a, b)
        x1, y1 = poisson(self.rng, la1), poisson(self.rng, lb1)
        lb2, la2 = self._lam(b, a)
        x2, y2 = poisson(self.rng, la2), poisson(self.rng, lb2)
        sc = {"g": [x1 + x2, y1 + y2], "legs": [[x1, y1], [x2, y2]], "et": False}
        win = self._finish(sc, la2, lb2, 0.5 + 0.004 * (self.eff(a) - self.eff(b)))
        return (a if win else b), sc

    @staticmethod
    def _rec_ko(res, a, b, w, sc, stage, games):
        """Итог раунда на вылет; path - все раунды команды по порядку (для таблицы «путь в кубке»)."""
        for t, o, s in ((a, b, sc), (b, a, flip(sc))):
            r = res.setdefault(t, {"games": 0})
            r["games"] += games
            r.update(stage=stage if t != w else r.get("stage"), vs=o, score=s, won=(t == w))
            r.setdefault("path", []).append({"stage": stage, "vs": o, "score": s, "won": t == w})

    # ---------- сезон ----------
    def simulate_season(self, year, boost=None, tactics=None):
        return self.finish_season(self.begin_season(year, boost, tactics), boost, tactics)

    def begin_season(self, year, boost=None, tactics=None):
        """Первая половина чемпионатов (половина матчей каждой команды). -> res с таблицами середины сезона (res["half"]).
        tactics: {клуб: (множитель своих голов, множитель пропущенных)} - тактика тренера."""
        self._boost, self._tactics = boost or {}, tactics or {}
        self._form = {c: self.rng.gauss(0, FORM_SD) for c in self.score}       # удачный / провальный сезон каждого клуба
        res = {"year": year, "tables": {}, "cups": {}, "supercups": {}, "cont": {}, "nat": {}, "nat_season": {}, "lg_ovr": {},
               "half": {}, "_pending": {}}
        for lid in self.league_clubs:
            if self.league_clubs[lid]:
                st = self._league_start(lid)
                self._league_play(st, 1)
                res["_pending"][lid] = st
                res["half"][lid] = self._league_table(st, lid, final=False)
        self._boost, self._tactics = {}, {}
        return res

    def finish_season(self, res, boost=None, tactics=None):
        """Вторая половина чемпионатов (тактика и прибавка тренера могли смениться), затем кубки, еврокубки, сборные."""
        self._boost, self._tactics = boost or {}, tactics or {}
        for lid, st in res.pop("_pending").items():
            self._league_play(st, 2)
            res["tables"][lid] = self._league_table(st, lid, final=True)
            res["lg_ovr"][lid] = self.league_avg_ovr(lid)
            res.setdefault("mlog", {})[lid] = st["log"]
        for country, top in self.d.top_league.items():
            ids = [c for lid in self.league_clubs if self.d.leagues[lid]["country"] == country for c in self.league_clubs[lid]
                   if not self.d.clubs[c]["reserve"]]
            if len(ids) < 8:
                continue
            res["cups"][(country, "cup")] = self._cup(ids)
            if country == "ENG":
                res["cups"][(country, "league_cup")] = self._cup(ids)
            if self.d.cup_names(country)[2]:
                champ = res["tables"][top]["order"][0]
                cw = res["cups"][(country, "cup")]
                other = cw["winner"] if cw["winner"] != champ else cw["runner"]
                w, sc = self._ko1(champ, other, neutral=True)
                res["supercups"][country] = {"winner": w, "pair": (champ, other), "score": sc}
        self._continental(res)
        self._national(res)
        self._boost, self._tactics = {}, {}
        return res

    def club_matches(self, res, cid):
        """Матчи клуба в лиге за сезон: [[соперник, 1 дома / 0 в гостях, забито, пропущено, половина сезона], ...]."""
        lid = self.club_league.get(cid)
        return [[g if h == cid else h, int(h == cid), x if h == cid else y, y if h == cid else x, hf]
                for h, g, x, y, hf in res.get("mlog", {}).get(lid, []) if cid in (h, g)]

    def _tac(self, team, x, y):
        """Тактика команды: (её голы, голы соперника) -> с поправкой на её тактику."""
        t = self._tactics.get(team)
        return (x * t[0], y * t[1]) if t else (x, y)

    def _league_start(self, lid):
        """Календарь лиги: каждая пара встречается rounds раз; матчи поделены на две половины сезона поровну для каждой команды."""
        rng, ids = self.rng, self.league_clubs[lid]
        rounds = self.d.leagues[lid]["rounds"]
        n = len(ids)
        matches = []
        for i in range(n):
            a = ids[i]
            for j in range(i + 1, n):
                b = ids[j]
                for r in range(rounds):
                    swap = (r % 2 == 1) if rounds > 1 else (rng.random() < 0.5)
                    h, g = (b, a) if swap else (a, b)
                    if rounds % 2 == 0:
                        half = 1 if r < rounds // 2 else 2
                    elif r < rounds // 2:
                        half = 1
                    elif r > rounds // 2:
                        half = 2
                    else:                                      # средний круг при нечётном числе кругов делится пополам
                        half = 1 + (i + j) % 2
                    matches.append((h, g, half))
        z = lambda: {c: 0 for c in ids}
        return {"ids": ids, "rounds": rounds, "matches": matches, "pts": z(), "w": z(), "d": z(), "l": z(), "gf": z(), "ga": z(), "log": []}

    def _league_play(self, st, half):
        rng = self.rng
        eff = {i: self.eff(i) for i in st["ids"]}
        pts, w, dr, l, gf, ga = st["pts"], st["w"], st["d"], st["l"], st["gf"], st["ga"]
        for h, g, hf in st["matches"]:
            if hf != half:
                continue
            d = eff[h] - eff[g]
            lh, lg = 1.45 * math.exp(SENS * d), 1.15 * math.exp(-SENS * d)
            lh, lg = self._tac(h, lh, lg)
            lg, lh = self._tac(g, lg, lh)
            x, y = poisson(rng, lh), poisson(rng, lg)
            st["log"].append((h, g, x, y, hf))                    # результаты матчей - для истории сезона (club_matches)
            gf[h] += x; ga[h] += y; gf[g] += y; ga[g] += x
            if x > y:
                pts[h] += 3; w[h] += 1; l[g] += 1
            elif x < y:
                pts[g] += 3; w[g] += 1; l[h] += 1
            else:
                pts[h] += 1; pts[g] += 1; dr[h] += 1; dr[g] += 1

    def _league_table(self, st, lid, final):
        rng, ids = self.rng, st["ids"]
        pts, gf, ga = st["pts"], st["gf"], st["ga"]
        order = sorted(ids, key=lambda i: (pts[i], gf[i] - ga[i], gf[i], rng.random()), reverse=True)
        cp = (lambda m: m) if final else (lambda m: dict(m))           # таблица середины сезона - снимок
        n = len(ids)
        return {"order": order, "pts": cp(pts), "w": cp(st["w"]), "d": cp(st["d"]), "l": cp(st["l"]), "gf": cp(gf), "ga": cp(ga),
                "games": st["rounds"] * (n - 1) if final else sum(1 for m in st["matches"] if m[2] == 1 and ids[0] in m[:2])}

    def _cup(self, ids):
        """Кубок на вылет: сильнейшие клубы пропускают первый раунд, финал на нейтральном поле."""
        rng = self.rng
        teams = list(ids); rng.shuffle(teams)
        size = 1
        while size < len(teams):
            size *= 2
        nbye = size - len(teams)
        strong = set(sorted(teams, key=lambda c: -self.eff(c))[:nbye])
        rest = [c for c in teams if c not in strong]
        pairs = [(c, None) for c in strong] + [(rest[i], rest[i + 1]) for i in range(0, len(rest), 2)]
        res = {c: {"games": 0} for c in ids}
        runner, cur = None, size
        while True:
            nxt = []
            for a, b in pairs:
                if b is None:
                    nxt.append(a); continue
                w, sc = self._ko1(a, b, neutral=(cur == 2))
                self._rec_ko(res, a, b, w, sc, CUP_STAGE.get(cur, "early"), 1)
                if cur == 2:
                    runner = b if w == a else a
                nxt.append(w)
            cur //= 2
            if len(nxt) == 1:
                break
            rng.shuffle(nxt)
            pairs = [(nxt[i], nxt[i + 1]) for i in range(0, len(nxt), 2)]
        res[nxt[0]]["stage"] = "W"
        return {"winner": nxt[0], "runner": runner, "res": res}

    # ---------- континентальные турниры клубов ----------
    def _uefa_tickets(self, res):
        """Путёвки в еврокубки по месту страны в рейтинге UEFA (EURO_ACCESS).
        -> {(турнир, "direct"/"champ"/"league"/"qual"): [(посев, клуб)]}; посев - чем меньше, тем выше."""
        out = {}
        for country, top in self.d.top_league.items():
            if self.d.countries[country]["conf"] != "UEFA" or country not in self.d.uefa_rank:
                continue
            rank = self.d.uefa_rank[country]
            order = [c for c in res["tables"][top]["order"] if not self.d.clubs[c]["reserve"]]
            if not order:
                continue
            acc = next(s for s in EURO_ACCESS if rank <= s[0])[1]
            used = set()
            for (comp, path), places in acc.items():
                for pl in places:
                    if pl == "cup":
                        continue
                    if pl <= len(order) and order[pl - 1] not in used:
                        used.add(order[pl - 1])
                        out.setdefault((comp, path), []).append((rank * 100 + pl, order[pl - 1]))
            # обладатель кубка; если он уже попал в еврокубки через чемпионат, путёвка уходит следующему клубу таблицы
            cw = res["cups"].get((country, "cup"), {}).get("winner")
            for (comp, path), places in acc.items():
                if "cup" in places:
                    c = cw if cw in order and cw not in used else next((x for x in order if x not in used), None)
                    if c:
                        used.add(c)
                        out.setdefault((comp, path), []).append((rank * 100 + 50, c))
        return out

    def _qual_rounds(self, cands, target, names, pre):
        """Отборочные раунды на вылет (по два матча). cands: [(посев, клуб)], чем меньше посев, тем позже клуб вступает
        (сильные пропускают первые раунды). -> (прошедшие, [(раунд, проигравшие)])."""
        alive = [c for _, c in sorted(cands)]
        R = len(names)
        out = []
        for j, name in enumerate(names):
            E = len(alive) - target
            if E <= 0:
                break
            rl = R - j

            def fits(m):                     # успеют ли оставшиеся раунды выбить остальных
                al, e = len(alive) - m, E - m
                for _ in range(rl - 1):
                    k = min(al // 2, e)
                    al, e = al - k, e - k
                return e <= 0
            m = -(-E // rl)
            while m < min(len(alive) // 2, E) and not fits(m):
                m += 1
            m = min(m, len(alive) // 2, E)
            if m <= 0:
                break
            play = alive[len(alive) - 2 * m:]                     # слабейшие по посеву играют, остальные ждут следующего раунда
            hi, lo = play[:m], play[m:]
            self.rng.shuffle(lo)
            winners, losers = [], []
            for h, l in zip(hi, lo):
                w, sc = self._ko2(l, h)                             # первый матч дома у слабейшего по посеву
                self._rec_ko(pre, l, h, w, sc, name, 2)
                winners.append(w); losers.append(h if w == l else l)
            keep = set(alive[:len(alive) - 2 * m]) | set(winners)
            alive = [c for c in alive if c in keep]
            out.append((name, losers))
        return alive, out

    def _uefa_fields(self, res):
        """Составы ЛЧ, ЛЕ и ЛК на общий этап после отборочных раундов. Проигравший в отборе ЛЧ продолжает в ЛЕ или ЛК,
        проигравший в отборе ЛЕ - в ЛК, а проигравший в отборе ЛК выбывает из еврокубков совсем.
        -> ({турнир: состав общего этапа}, {турнир: {клуб: итог отбора}})."""
        tk = self._uefa_tickets(res)
        pre = {"UCL": {}, "UEL": {}, "UECL": {}}
        used = set()

        def take(lst):
            r = []
            for p, c in sorted(lst):
                if c not in used:
                    used.add(c); r.append((p, c))
            return r
        DROP = -1000                                              # выбывшие из турнира выше вступают в отбор позже всех
        # Лига чемпионов
        direct = take(tk.get(("UCL", "direct"), []))
        if self.prev_uel_winner and self.prev_uel_winner in self.club_league and self.prev_uel_winner not in used:
            if self.d.leagues[self.club_league[self.prev_uel_winner]]["tier"] == 1:
                direct = [(0, self.prev_uel_winner)] + direct; used.add(self.prev_uel_winner)
        lp = take(tk.get(("UCL", "league"), []))
        ch = take(tk.get(("UCL", "champ"), []))
        t_lp = min(UCL_LEAGUE_PATH, len(lp))
        t_ch = max(0, 36 - len(direct) - t_lp)
        q_lp, r_lp = self._qual_rounds(lp, t_lp, ["Q2", "Q3", "QPO"], pre["UCL"])
        q_ch, r_ch = self._qual_rounds(ch, t_ch, ["Q1", "Q2", "Q3", "QPO"], pre["UCL"])
        ucl = [c for _, c in direct] + q_lp + q_ch
        uel_direct, uel_drop, uecl_drop = [], [], []
        for rounds in (r_lp, r_ch):
            for name, losers in rounds:
                if name == "QPO":
                    uel_direct += losers
                elif name == "Q1":
                    uecl_drop += [(DROP + self.d.uefa_rank.get(self.d.clubs[c]["country"], 99), c) for c in losers]
                else:
                    uel_drop += [(DROP + (0 if name == "Q3" else 100) + self.d.uefa_rank.get(self.d.clubs[c]["country"], 99), c) for c in losers]
        # Лига Европы
        d2 = [c for _, c in take(tk.get(("UEL", "direct"), []))] + uel_direct
        q2, r2 = self._qual_rounds(take(tk.get(("UEL", "qual"), [])) + uel_drop, max(0, 36 - len(d2)), ["Q1", "Q2", "Q3", "QPO"], pre["UEL"])
        uel = d2 + q2
        uecl_direct = []
        for name, losers in r2:
            if name == "QPO":
                uecl_direct += losers
            else:
                uecl_drop += [(DROP + (0 if name == "Q3" else 100) + self.d.uefa_rank.get(self.d.clubs[c]["country"], 99), c) for c in losers]
        # Лига конференций: проигравшие в её отборе выбывают
        d3 = [c for _, c in take(tk.get(("UECL", "direct"), []))] + uecl_direct
        q3, _ = self._qual_rounds(take(tk.get(("UECL", "qual"), [])) + uecl_drop, max(0, 36 - len(d3)), ["Q1", "Q2", "Q3", "QPO"], pre["UECL"])
        uecl = d3 + q3
        return {"UCL": ucl, "UEL": uel, "UECL": uecl}, pre

    def _region_fields(self, res, slots1, slots2=None):
        f1, f2 = [], []
        for country, k in slots1.items():
            top = self.d.top_league.get(country)
            if not top or top not in res["tables"]:
                continue
            order = [c for c in res["tables"][top]["order"] if not self.d.clubs[c]["reserve"]]
            pick = order[:k]
            cw = res["cups"].get((country, "cup"), {}).get("winner")
            if cw and cw in order and cw not in pick and k > 1:
                pick[-1] = cw
            f1 += pick
            if slots2:
                f2 += [c for c in order if c not in pick][:slots2.get(country, 0)]
        return f1, f2

    def _continental(self, res):
        fields, pre = self._uefa_fields(res)
        for key in ("UCL", "UEL", "UECL"):
            r = self._cont_comp(fields[key], pre=pre[key])
            if r:
                res["cont"][key] = r
        if "UCL" in res["cont"] and "UEL" in res["cont"]:
            a, b = res["cont"]["UCL"]["winner"], res["cont"]["UEL"]["winner"]
            if a != b:
                w, sc = self._ko1(a, b, neutral=True)
                rr = {}
                self._rec_ko(rr, a, b, w, sc, "F", 1)
                rr[w]["stage"] = "W"
                res["cont"]["USC"] = {"winner": w, "res": rr, "field": [a, b]}
        lib, sud = self._region_fields(res, LIB_SLOTS, SUD_SLOTS)
        for key, field in (("LIB", lib), ("SUD", sud)):
            r = self._cont_comp(field, groups=True)
            if r:
                res["cont"][key] = r
        acl, _ = self._region_fields(res, ACLE_SLOTS)
        r = self._cont_comp(acl)
        if r:
            res["cont"]["ACLE"] = r
        ccc, _ = self._region_fields(res, CCC_SLOTS)
        r = self._cont_comp(ccc)
        if r:
            res["cont"]["CCC"] = r

    def _cont_comp(self, teams, groups=False, pre=None):
        """pre - итоги отборочных раундов: {клуб: ...}; прошедшие отбор продолжают с ними, выбывшие остаются в итогах турнира."""
        rng, n = self.rng, len(teams)
        if n < 8:
            return None
        pre = pre or {}
        res = dict(pre)
        for t in teams:
            res[t] = pre.get(t) or {"games": 0}
            res[t].pop("stage", None); res[t].pop("vs", None); res[t].pop("score", None); res[t].pop("won", None)
        lp_table = None
        if groups and n >= 16:
            ko = []
            seeded = sorted(teams, key=lambda t: -self.eff(t))
            G = n // 4
            grp = [[] for _ in range(G)]
            for i, t in enumerate(seeded):
                grp[i % G if (i // G) % 2 == 0 else G - 1 - i % G].append(t)
            firsts, seconds = [], []
            for gi, g in enumerate(grp):
                pts, gd = {t: 0 for t in g}, {t: 0 for t in g}
                for i in range(len(g)):
                    for j in range(len(g)):
                        if i == j:
                            continue
                        x, y = poisson(rng, self._lam(g[i], g[j])[0]), poisson(rng, self._lam(g[i], g[j])[1])
                        gd[g[i]] += x - y; gd[g[j]] += y - x
                        res[g[i]]["games"] += 1; res[g[j]]["games"] += 1
                        if x > y: pts[g[i]] += 3
                        elif x < y: pts[g[j]] += 3
                        else: pts[g[i]] += 1; pts[g[j]] += 1
                order = sorted(g, key=lambda t: (pts[t], gd[t], rng.random()), reverse=True)
                gtable = [[t, pts[t], gd[t]] for t in order]                  # таблица группы: клуб, очки, разница мячей
                for pos, t in enumerate(order, 1):
                    res[t].update(stage="GS", group=gi + 1, gpos=pos, gpts=pts[t], gtable=gtable)
                firsts.append(order[0]); seconds.append(order[1])
            ko = firsts + seconds          # 1-е место группы i играет со 2-м местом другой группы
        else:
            rounds = 8 if n >= 24 else 6
            pts, gd = {t: 0 for t in teams}, {t: 0 for t in teams}
            for _ in range(rounds):
                order = teams[:]; rng.shuffle(order)
                for i in range(0, len(order) - 1, 2):
                    a, b = order[i], order[i + 1]
                    la, lb = self._lam(a, b)
                    x, y = poisson(rng, la), poisson(rng, lb)
                    gd[a] += x - y; gd[b] += y - x; res[a]["games"] += 1; res[b]["games"] += 1
                    if x > y: pts[a] += 3
                    elif x < y: pts[b] += 3
                    else: pts[a] += 1; pts[b] += 1
            rank = sorted(teams, key=lambda t: (pts[t], gd[t], rng.random()), reverse=True)
            lp_table = [[t, pts[t], gd[t]] for t in rank]                     # общий этап: клуб, очки, разница мячей
            for i, t in enumerate(rank, 1):
                res[t].update(stage="LP", lp_rank=i, lp_pts=pts[t], lp_n=n)
            if n >= 24:
                direct, po = rank[:8], rank[8:24]
                winners = []
                for i in range(8):
                    a, b = po[i], po[15 - i]
                    w, sc = self._ko2(b, a)
                    self._rec_ko(res, b, a, w, sc, "PO", 2)
                    winners.append(w)
                ko = direct + winners
            elif n >= 16:
                ko = rank[:16]
            else:
                ko = rank[:8]
        first = True
        while len(ko) > 1:
            size, nxt = len(ko), []
            if first:
                pairs = [(ko[i], ko[size - 1 - i]) for i in range(size // 2)]
            else:
                rng.shuffle(ko); pairs = [(ko[i], ko[i + 1]) for i in range(0, size, 2)]
            for a, b in pairs:
                if size == 2:
                    w, sc = self._ko1(a, b, neutral=True); self._rec_ko(res, a, b, w, sc, "F", 1)
                else:
                    w, sc = self._ko2(b, a); self._rec_ko(res, b, a, w, sc, KO_STAGE[size], 2)
                nxt.append(w)
            ko, first = nxt, False
        res[ko[0]]["stage"] = "W"
        return {"winner": ko[0], "res": res, "field": teams, "lp": lp_table}

    # ---------- сборные ----------
    def _nat_lam(self, a, b, home=None):
        d = self.nat[a] - self.nat[b]
        la, lb = 1.25 * math.exp(0.016 * d), 1.25 * math.exp(-0.016 * d)
        if home == a:
            la, lb = la * 1.12, lb / 1.12
        elif home == b:
            la, lb = la / 1.12, lb * 1.12
        return la, lb

    def _nat_ko(self, a, b, neutral=True):
        la, lb = self._nat_lam(a, b, None if neutral else a)
        sc = {"g": [poisson(self.rng, la), poisson(self.rng, lb)], "et": False}
        win = self._finish(sc, la, lb, 0.5 + 0.002 * (self.nat[a] - self.nat[b]))
        return (a if win else b), sc

    def _nat_rr(self, g, double=True):
        """Круговой турнир сборных. -> список (сборная, очки, разница, забито, матчей) по местам."""
        rng = self.rng
        pts, gd, gf, gm = ({t: 0 for t in g} for _ in range(4))
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                legs = [(g[i], g[j]), (g[j], g[i])] if double else [(g[i], g[j])]
                for h, a in legs:
                    la, lb = self._nat_lam(h, a, h if double else None)
                    x, y = poisson(rng, la), poisson(rng, lb)
                    gd[h] += x - y; gd[a] += y - x; gf[h] += x; gf[a] += y; gm[h] += 1; gm[a] += 1
                    if x > y: pts[h] += 3
                    elif x < y: pts[a] += 3
                    else: pts[h] += 1; pts[a] += 1
        order = sorted(g, key=lambda t: (pts[t], gd[t], gf[t], rng.random()), reverse=True)
        return [(t, pts[t], gd[t], gf[t], gm[t]) for t in order]

    def _seed_groups(self, teams, G, noise=3.0):
        seeded = sorted(teams, key=lambda c: -(self.nat[c] + self.rng.gauss(0, noise)))
        groups = [[] for _ in range(G)]
        for i, c in enumerate(seeded):
            pot, k = divmod(i, G)
            groups[k if pot % 2 == 0 else G - 1 - k].append(c)
        return [g for g in groups if g]

    def _opp(self, me, others):
        o = [self.nat_ovr(c) for c in others if c != me]
        return round(sum(o) / len(o), 1) if o else None

    def _hosts(self, code, tyear):
        if (code, tyear) in HOSTS:
            return [h for h in HOSTS[(code, tyear)] if h in self.nat]
        if code == "WC" and tyear >= 2038:
            conf = WC_HOST_ROT[((tyear - 2038) // 4) % len(WC_HOST_ROT)]
            top = sorted((c for c in self.nat if self.d.countries[c]["conf"] == conf), key=lambda c: -self.nat[c])[:6]
            return [self.rng.choice(top)]
        return []

    def _qual_groups(self, cands, slots, G, direct, label):
        """Отборочные группы + стыковые матчи. -> (прошедшие, {сборная: инфо}, непрошедшие по убыванию)."""
        info = {}
        if slots <= 0 or not cands:
            return [], info, list(cands)
        if direct >= 1 and G * direct > slots:
            if direct == 1:
                G = slots
            else:
                direct = max(1, slots // G)
        G = max(1, min(G, len(cands)))
        qualified, rest = [], []
        for gi, g in enumerate(self._seed_groups(cands, G)):
            table = self._nat_rr(g, double=True)
            names = [t[0] for t in table]
            for pos, (c, pts, gd, gf, gm) in enumerate(table, 1):
                info[c] = {"group": gi + 1, "pos": pos, "pts": pts, "gd": gd, "n": len(g), "table": names, "res": "OUT",
                           "games": gm, "opp": self._opp(c, names)}
                if pos <= direct:
                    qualified.append(c); info[c]["res"] = "Q"
                else:
                    rest.append((pos, -pts / max(1, gm), -gd, self.rng.random(), c))
        rest = [x[-1] for x in sorted(rest)]
        po = min(slots - len(qualified), len(rest) // 2)
        losers = []
        if po > 0:
            cand, rest = rest[:2 * po], rest[2 * po:]
            for i in range(po):
                a, b = cand[i], cand[2 * po - 1 - i]
                w, sc = self._nat_ko(a, b, neutral=False)
                info[a]["po"] = {"vs": b, "score": sc, "won": w == a}
                info[b]["po"] = {"vs": a, "score": flip(sc), "won": w == b}
                for t in (a, b):
                    info[t]["games"] += 1; info[t]["res"] = "Q" if t == w else "PO"
                qualified.append(w); losers.append(b if w == a else a)
        return qualified, info, losers + rest

    def _national(self, res):
        tyear = res["year"] + 1                     # турниры проходят летом следующего календарного года
        season = {c: [] for c in self.nat}
        events = []
        for code in NAT_ORDER:
            comp = self.d.comps.get(code)
            if comp and tyear in edition_years(code, comp["next_edition_year"], comp["cycle_years"]):
                events.append(code)
        if not any(c in events for c in ("WC", "EURO")) and "UNL" in self.d.comps:
            self._unl(res, season, tyear)
        for code in events:
            field = self._qualify(code, tyear, season)
            r = self._nat_tournament(field)
            res["nat"][code] = r
            for c in field:
                rr = r["res"][c]
                season[c].append({"kind": "final", "code": code, "year": tyear, "games": rr["games"], "opp": rr.get("opp"), "info": rr})
        for c, ents in season.items():
            official = sum(e["games"] for e in ents if e["kind"] in ("qual", "unl"))
            ents.append({"kind": "friendly", "code": "FR", "year": tyear, "games": max(2, 8 - official), "opp": None, "info": {}})
        res["nat_season"] = season

    def _qualify(self, code, tyear, season):
        conf_of = lambda c: self.d.countries[c]["conf"]
        hosts = self._hosts(code, tyear)
        for h in hosts:
            season[h].append({"kind": "host", "code": code, "year": tyear, "games": 0, "opp": None, "info": {}})
        field = list(hosts)
        def add(infos):
            for c, inf in infos.items():
                season[c].append({"kind": "qual", "code": code, "year": tyear, "games": inf["games"], "opp": inf["opp"], "info": inf})
        if code == "WC":
            ic, infos_all = [], {}
            for cf, quota in WC_QUOTA.items():
                cands = [c for c in self.nat if conf_of(c) == cf and c not in hosts]
                slots = quota - sum(1 for h in hosts if conf_of(h) == cf)
                G, direct = QUAL_FMT[(code, cf)]
                q, info, left = self._qual_groups(cands, slots, G, direct, code)
                field += q; infos_all.update(info)
                ic += left[:IC_FROM.get(cf, 0)]
            if len(ic) >= 4:
                field += self._intercontinental(ic, infos_all)
            add(infos_all)
        elif code == "CA":
            field += [c for c in self.nat if conf_of(c) == "CONMEBOL"]
            guests = sorted((c for c in self.nat if conf_of(c) == "CONCACAF"), key=lambda c: -(self.nat[c] + self.rng.gauss(0, 4)))
            field += guests[:6]
            for c in guests[6:]:
                season[c].append({"kind": "notinv", "code": code, "year": tyear, "games": 0, "opp": None, "info": {}})
        else:
            cf = self.d.comps[code]["confederation"]
            cands = [c for c in self.nat if conf_of(c) == cf and c not in hosts]
            G, direct = QUAL_FMT[(code, cf)]
            q, info, _ = self._qual_groups(cands, NAT_SIZES[code] - len(hosts), G, direct, code)
            field += q
            add(info)
        return field[:NAT_SIZES[code]]

    def _intercontinental(self, cands, infos):
        """Межконтинентальный плей-офф ЧМ: 6 сборных, две сильнейшие ждут в финалах. -> 2 прошедшие."""
        cands = sorted(cands[:6], key=lambda c: -self.nat[c])
        seeds, others = cands[:2], cands[2:]
        out = []
        semis = [(others[0], others[-1])] + ([(others[1], others[2])] if len(others) >= 4 else [])
        for i, seed in enumerate(seeds):
            opp = None
            if i < len(semis):
                a, b = semis[i]
                w, sc = self._nat_ko(a, b)
                for t in (a, b):
                    infos[t]["games"] += 1
                l = b if w == a else a
                infos[l]["ic"] = {"vs": w, "score": sc if l == a else flip(sc), "won": False, "stage": "SF"}
                infos[l]["res"] = "IC"
                opp = w
            if opp is None:
                out.append(seed); continue
            w, sc = self._nat_ko(seed, opp)
            for t in (seed, opp):
                infos[t]["games"] += 1
            l = opp if w == seed else seed
            infos[w]["ic"] = {"vs": l, "score": sc if w == seed else flip(sc), "won": True, "stage": "F"}
            infos[l]["ic"] = {"vs": w, "score": sc if l == seed else flip(sc), "won": False, "stage": "F"}
            infos[w]["res"], infos[l]["res"] = "Q", "IC"
            out.append(w)
        return out

    def _nat_tournament(self, field):
        rng = self.rng
        n = len(field)
        res = {t: {"games": 0, "stage": "GS"} for t in field}
        G = max(1, n // 4)
        groups = self._seed_groups(field, G, noise=2.0)
        firsts, seconds, thirds = [], [], []
        opps = {t: [] for t in field}
        for gi, g in enumerate(groups):
            table = self._nat_rr(g, double=False)
            names = [t[0] for t in table]
            for pos, (c, pts, gd, gf, gm) in enumerate(table, 1):
                res[c].update(group=gi + 1, gpos=pos, gpts=pts, games=gm)
                opps[c] += [o for o in names if o != c]
            firsts.append(names[0]); seconds.append(names[1])
            if len(table) > 2:
                thirds.append((table[2][1], table[2][2], rng.random(), names[2]))
        need = ADVANCE.get(n, 4) - len(firsts) - len(seconds)
        ko = firsts + seconds + [t for *_, t in sorted(thirds, reverse=True)[:max(0, need)]]
        p2 = 1
        while p2 * 2 <= len(ko):
            p2 *= 2
        ko = ko[:p2]
        while len(ko) > 1:
            rng.shuffle(ko); nxt = []
            size = len(ko)
            for i in range(0, size - 1, 2):
                a, b = ko[i], ko[i + 1]
                w, sc = self._nat_ko(a, b)
                self._rec_ko(res, a, b, w, sc, KO_STAGE.get(size, "R32"), 1)
                opps[a].append(b); opps[b].append(a)
                nxt.append(w)
            ko = nxt
        res[ko[0]]["stage"] = "W"
        for t in field:
            res[t]["opp"] = self._opp(t, opps[t])
        return {"field": field, "stage": {t: res[t]["stage"] for t in field}, "winner": ko[0], "res": res}

    def _unl_divisions(self):
        """Стартовые дивизионы Лиги наций: по силе сборных (16 / 16 / 16 / остальные)."""
        uefa = sorted((c for c in self.nat if self.d.countries[c]["conf"] == "UEFA"), key=lambda c: -self.nat[c])
        return {c: "ABCD"[min(3, i // 16)] for i, c in enumerate(uefa)}

    def _unl(self, res, season, tyear):
        """Лига наций УЕФА: дивизионы A-D, группы по 4 (2 круга), финал четырёх у дивизиона A.
        Победители групп B-D поднимаются на дивизион выше, последние в группах A-C опускаются (дивизионы хранятся между розыгрышами)."""
        div = self.unl_div
        for c in self.nat:                                  # новые сборные УЕФА (если появились) - в низший дивизион
            if self.d.countries[c]["conf"] == "UEFA" and c not in div:
                div[c] = "D"
        finals = []
        infos = {}
        lasts = {}                                          # дивизион -> [(очки, разница, случайность, сборная)] последних мест
        for L in "ABCD":
            teams = sorted((c for c, l in div.items() if l == L and c in self.nat), key=lambda c: -self.nat[c])
            if len(teams) < 2:
                continue
            G = max(1, round(len(teams) / 4))
            for gi, g in enumerate(self._seed_groups(teams, G, noise=1.0)):
                table = self._nat_rr(g, double=True)
                names = [t[0] for t in table]
                for pos, (c, pts, gd, gf, gm) in enumerate(table, 1):
                    infos[c] = {"league": L, "group": gi + 1, "pos": pos, "pts": pts, "n": len(g), "table": names, "games": gm,
                                "opp": self._opp(c, names)}
                if L == "A":
                    finals.append(names[0])
                elif len(names) >= 3:
                    infos[names[0]]["move"] = {"dir": "up", "to": "ABCD"["ABCD".index(L) - 1]}
                if L != "D" and len(names) >= 3:
                    lasts.setdefault(L, []).append((table[-1][1], table[-1][2], self.rng.random(), names[-1]))
        # сколько опускается: столько же, сколько поднимается из дивизиона ниже (размеры дивизионов сохраняются)
        for L, below in (("A", "B"), ("B", "C"), ("C", "D")):
            n_up = sum(1 for inf in infos.values() if inf["league"] == below and inf.get("move", {}).get("dir") == "up")
            for *_, c in sorted(lasts.get(L, []))[:n_up]:
                infos[c]["move"] = {"dir": "down", "to": below}
        for c, inf in infos.items():
            if inf.get("move"):
                div[c] = inf["move"]["to"]
        stage = {}
        if len(finals) == 4:
            self.rng.shuffle(finals)
            fin = []
            for a, b in ((finals[0], finals[1]), (finals[2], finals[3])):
                w, sc = self._nat_ko(a, b)
                for t, o, s in ((a, b, sc), (b, a, flip(sc))):
                    infos[t]["games"] += 1
                    infos[t]["finals"] = {"stage": "SF", "vs": o, "score": s, "won": t == w}
                    stage[t] = "SF"
                fin.append(w)
            a, b = fin
            w, sc = self._nat_ko(a, b)
            for t, o, s in ((a, b, sc), (b, a, flip(sc))):
                infos[t]["games"] += 1
                infos[t]["finals"] = {"stage": "W" if t == w else "F", "vs": o, "score": s, "won": t == w}
                stage[t] = "W" if t == w else "F"
            res["nat"]["UNL"] = {"field": finals, "stage": stage, "winner": w, "res": {}}
        for c, inf in infos.items():
            season[c].append({"kind": "unl", "code": "UNL", "year": tyear, "games": inf["games"], "opp": inf["opp"], "info": inf})

    # ---------- клуб за сезон: все турниры ----------
    def club_comps(self, res, cid):
        """Турниры клуба за сезон с итогами (на уровне команды): лига, кубки, суперкубок, континентальные турниры."""
        d = self.d
        lid = self.club_league[cid]
        lg = d.leagues[lid]
        t = res["tables"][lid]
        lavg = res["lg_ovr"].get(lid) or self.league_avg_ovr(lid)
        cen, cru = d.country_name(lg["country"], "en"), d.country_name(lg["country"], "ru")
        out = [{"code": "league", "lid": lid, "name_en": f"{lg['name']} ({cen})", "name_ru": f"{lg['name']} ({cru})",
                "team_games": t["games"], "opp": lavg,
                "result": {"rank": t["order"].index(cid) + 1, "n": len(t["order"]), "pts": t["pts"][cid], "w": t["w"][cid],
                           "d": t["d"][cid], "l": t["l"][cid], "gf": t["gf"][cid], "ga": t["ga"][cid]},
                # полная таблица: клуб, В, Н, П, забито, пропущено, очки (по местам)
                "table": [[c, t["w"][c], t["d"][c], t["l"][c], t["gf"][c], t["ga"][c], t["pts"][c]] for c in t["order"]]}]
        country = lg["country"]
        cup_en, cup_ru, sc_en, sc_ru = d.cup_names(country)
        for key, en, ru in (("cup", cup_en, cup_ru), ("league_cup", "EFL Cup", "Кубок английской лиги")):
            cr = res["cups"].get((country, key))
            if cr and cid in cr["res"] and cr["res"][cid]["games"] > 0:
                out.append({"code": key, "name_en": en, "name_ru": ru, "team_games": cr["res"][cid]["games"], "opp": lavg - 2,
                            "result": cr["res"][cid]})
        sc = res["supercups"].get(country)
        if sc and cid in sc["pair"]:
            a, b = sc["pair"]
            vs = b if cid == a else a
            out.append({"code": "supercup", "name_en": sc_en, "name_ru": sc_ru, "team_games": 1, "opp": self.team_ovr(vs),
                        "result": {"stage": "W" if sc["winner"] == cid else "F", "vs": vs, "won": sc["winner"] == cid,
                                   "score": sc["score"] if cid == a else flip(sc["score"])}})
        for code in CONT_ORDER:
            e = res["cont"].get(code)
            if e and cid in e["res"]:
                f = e["field"]
                comp = d.comps[code]
                out.append({"code": code, "name_en": comp["name_en"], "name_ru": comp["name_ru"], "team_games": e["res"][cid]["games"],
                            "opp": sum(self.team_ovr(c) for c in f) / len(f), "result": e["res"][cid],
                            "table": (e.get("lp") if "lp_rank" in e["res"][cid] else None) or e["res"][cid].get("gtable")})  # общий этап или группа
        return out

    # ---------- конец сезона: переходы между дивизионами, дрейф силы ----------
    def advance(self, res):
        rng = self.rng
        changed = {}
        for country, ladder in self.d.pyramids.items():
            counts = UPDOWN.get(country, [3] * (len(ladder) - 1))
            for i in range(len(ladder) - 1):
                k = counts[i] if i < len(counts) else 3
                up_l, lo_l = ladder[i], ladder[i + 1]
                if up_l not in res["tables"] or lo_l not in res["tables"]:
                    continue
                up_tier = self.d.leagues[up_l]["tier"]
                # фарм-клубы не поднимаются в высший дивизион (а в Германии и во второй)
                def can_go_up(c):
                    if not self.d.clubs[c]["reserve"]:
                        return True
                    return up_tier > 1 and not (country == "GER" and up_tier <= 2)
                relegated = res["tables"][up_l]["order"][-k:]
                cand = [c for c in res["tables"][lo_l]["order"] if can_go_up(c)]
                if len(cand) < k:
                    continue
                promoted = cand[:k - 1]
                pool = cand[k - 1:k + 3]
                w = [math.exp(self.eff(c) / 20.0) for c in pool]
                promoted.append(rng.choices(pool, weights=w)[0])
                for c in relegated:
                    self.league_clubs[up_l].remove(c); self.league_clubs[lo_l].append(c); self.club_league[c] = lo_l; changed[c] = "relegated"
                for c in promoted:
                    self.league_clubs[lo_l].remove(c); self.league_clubs[up_l].append(c); self.club_league[c] = up_l; changed[c] = "promoted"
        self._hegemons()
        for lid, ids in self.league_clubs.items():
            if not ids:
                continue
            mean = sum(self.base[c] for c in ids) / len(ids)
            bases = sorted((self.base[c] for c in ids), reverse=True)
            second = bases[1] if len(bases) > 1 else bases[0]
            top = res["tables"][lid]["order"][0] if lid in res["tables"] else None
            h = self.hegemon.get(lid)
            for c in ids:
                s, b = self.score[c], self.base[c]
                if h and h["club"] == c:
                    s += HEG_REVERT * (b + h["boost"] - s) + rng.gauss(0, 1.8)
                else:
                    s += REVERT * (b - s) + rng.gauss(0, 1.8)
                if c == top: s += CHAMP_BONUS
                if changed.get(c) == "promoted": s += 1.0
                if changed.get(c) == "relegated": s -= 2.0
                u = rng.random()
                if u < 0.008: s += 8
                elif u > 0.992: s -= 6
                self.score[c] = max(MIN_SCORE, min(100.0, s))
                b += BASE_TO_MEAN * (mean - b)
                if b > second + LEAD_GAP:
                    b -= LEAD_FADE * (b - second - LEAD_GAP)
                self.base[c] = b
        for c in self.nat:
            self.nat[c] = max(0.0, min(100.0, self.nat[c] + 0.08 * (self.d.nat_strength[c] - self.nat[c]) + rng.gauss(0, 1.0)))
        self.prev_uel_winner = res["cont"].get("UEL", {}).get("winner")
        self.year += 1
        return changed

    def _hegemons(self):
        """Начало и конец эпох «гегемонов» в высших лигах (см. HEG_*). Сезон, который сейчас закончился, - self.year."""
        rng = self.rng
        for lid, ids in self.league_clubs.items():
            h = self.hegemon.get(lid)
            if h and (h["until"] <= self.year or self.club_league.get(h["club"]) != lid):
                del self.hegemon[lid]                                # эпоха кончилась: дальше клуб постепенно возвращается к своей силе
                self.heg_last[h["club"]] = self.year
            if lid in self.hegemon or self.d.leagues[lid]["tier"] != 1 or len(ids) < 8 or rng.random() >= HEG_P:
                continue
            ranked = sorted((c for c in ids if not self.d.clubs[c]["reserve"]), key=lambda c: -self.score[c])
            pool = [c for c in ranked[:6] if self.year - self.heg_last.get(c, -99) >= HEG_COOLDOWN]
            if not pool:
                continue
            c = rng.choices(pool, weights=[math.exp((self.score[x] - self.score[ranked[0]]) / HEG_TEMP) for x in pool])[0]
            rival = max(self.score[x] for x in ranked if x != c)
            boost = min(HEG_MAX, max(0.0, rival - self.base[c]) + rng.uniform(*HEG_LEAD))
            self.hegemon[lid] = {"club": c, "until": self.year + rng.randint(*HEG_YEARS), "boost": round(boost, 1)}

    # ---------- сохранение ----------
    def to_dict(self):
        return {"year": self.year, "score": self.score, "base": self.base, "club_league": self.club_league,
                "nat": self.nat, "prev_uel_winner": self.prev_uel_winner, "unl_div": self.unl_div, "hegemon": self.hegemon,
                "heg_last": self.heg_last}

    def load_dict(self, d, migrate=False):
        """migrate=True: сохранение старой версии (до базы FC 27) - силы клубов и сборных берутся из новой базы."""
        self.year, self.prev_uel_winner = d["year"], d.get("prev_uel_winner")
        cl = {c: l for c, l in d["club_league"].items() if c in self.d.clubs and l in self.d.leagues}
        for c, v in self.d.clubs.items():
            cl.setdefault(c, v["league"])
        self.club_league = cl
        if not migrate:
            self.score = {c: d["score"].get(c, self.d.clubs[c]["score"]) for c in self.d.clubs}
            self.base = {c: d["base"].get(c, self.d.clubs[c]["score"]) for c in self.d.clubs}
            self.nat = {c: d["nat"].get(c, self.d.nat_strength[c]) for c in self.d.nat_strength}
        self.unl_div = {c: l for c, l in (d.get("unl_div") or {}).items() if c in self.nat} or self._unl_divisions()
        self.hegemon = {l: h for l, h in (d.get("hegemon") or {}).items() if l in self.d.leagues and h.get("club") in self.d.clubs}
        self.heg_last = {c: y for c, y in (d.get("heg_last") or {}).items() if c in self.d.clubs}
        self.league_clubs = {l: [] for l in self.d.leagues}
        for c, l in self.club_league.items():
            self.league_clubs[l].append(c)
