"""Тренерская карьера: после завершения игровой карьеры игрок может стать тренером клуба.

Состояние хранится в career.coach (словарь, сохраняется вместе с карьерой). Главное:
  rating    - тренерский навык (25-92): небольшая прибавка к силе команды и рост от опыта и успехов;
  rep       - репутация (0-100, в шкале силы клубов): от неё зависит уровень клубов в предложениях;
  anger     - раздражение руководства (0-100): растёт за результаты ниже задачи, падает за трофеи и успехи; на 100 - увольнение;
  tactic    - тактика (атака / баланс / оборона / прессинг): меняет голы команды и пропущенные, выбирается на каждую половину сезона;
  relations - отношения с клубами (-100..100): уволивший клуб долго не позовёт, клуб, где выиграл титул, захочет вернуть.
Сезон идёт в две половины: после первой руководство смотрит на таблицу и может уволить тренера посреди сезона,
а тренер может сменить тактику на вторую половину. Задача клуба (ожидаемое место) - по силе клуба среди соперников по лиге.
"""
import math
from .player import clamp
from . import stars as stars_mod
from .transfers import annual_budget, TransferWindow
from . import squad as squad_mod
from . import coaches as coaches_mod

COACH_RETIRE_AGE = 70
FIRE_AT = 100.0
DECAY = 0.6            # за сезон от прошлого раздражения остаётся 60% (руководство постепенно забывает обиды)
MID_WEIGHT = 0.6       # в середине сезона руководство оценивает таблицу с весом 0.6 (полсезона - ещё не приговор)
CONT = ("UCL", "UEL", "UECL", "USC", "LIB", "SUD", "ACLE", "CCC")
# снижение раздражения за итог в кубках и еврокубках (стадия -> очки)
CUP_RELIEF = {"cup": {"W": 22, "F": 8, "SF": 3}, "league_cup": {"W": 10, "F": 4}, "supercup": {"W": 4}}
CONT_RELIEF = {"UCL": {"W": 45, "F": 28, "SF": 18, "QF": 10, "R16": 4}, "UEL": {"W": 30, "F": 16, "SF": 9, "QF": 4},
               "UECL": {"W": 20, "F": 10, "SF": 5}, "USC": {"W": 4}, "LIB": {"W": 40, "F": 22, "SF": 12, "QF": 5},
               "SUD": {"W": 22, "F": 10, "SF": 5}, "ACLE": {"W": 30, "F": 15, "SF": 8},
               "CCC": {"W": 25, "F": 12, "SF": 6}}
TACTICS = ("balanced", "attack", "defense", "press")
REL_MIN_OFFER = -35    # с таким отношением клуб тренера не зовёт
REL_LOVED = 40         # бывший клуб, где тренера любят: зовёт охотнее

def season_label(year):
    return f"{year}/{str(year + 1)[2:]}"

def pressure(score, project):
    """Насколько быстро руководство раздражается: маленький клуб x0.6 ... топ-клуб x1.8; перестройка - вдвое терпеливее."""
    m = 0.6 + 1.2 * clamp((score - 20.0) / 70.0, 0.0, 1.0)
    return round(m * (0.45 if project == "rebuild" else 1.0), 2)

def tactic_mult(tactic, rating, tired=False):
    """-> (множитель голов команды, множитель пропущенных).
    Атака: больше голов в обе стороны - выгодна сильной команде. Оборона: меньше голов в обе стороны - выручает аутсайдера.
    Прессинг: лучше и в атаке, и в обороне, но только у сильного тренера (у слабого - хуже баланса); выматывает: если играть им
    обе половины сезона, во второй эффект вдвое меньше."""
    if tactic == "attack":
        return 1.15, 1.12
    if tactic == "defense":
        return 0.85, 0.79
    if tactic == "press":
        q = clamp((rating - 55.0) / 30.0, -0.6, 1.0) * (0.5 if tired else 1.0)
        return round(1 + 0.08 * q, 3), round(1 - 0.06 * q, 3)
    return 1.0, 1.0

def team_mult(tactic, rating, formation, tired=False):
    """Тактика и стиль схемы вместе: (множитель своих голов, пропущенных)."""
    t = tactic_mult(tactic, rating, tired)
    f = squad_mod.FORMATIONS.get(formation, squad_mod.FORMATIONS[squad_mod.DEFAULT_FORMATION])[1]
    return round(t[0] * f[0], 3), round(t[1] * f[1], 3)

def place_points(rank, target, n):
    """Очки раздражения за место в таблице: ниже задачи - плюс (большой провал непропорционально хуже), выше - минус."""
    x = (rank - target) / max(1, n - 1)
    return 150 * x + (250 * x * x if x > 0 else 0)

class CoachCareer:
    """Операции тренерской карьеры над объектом Career (состояние - career.coach; незавершённый сезон - career._coach_pending)."""
    def __init__(self, career):
        self.c = career
        s = career.coach
        if s is not None:                                     # сохранения прошлых версий тренерского режима
            s.setdefault("tactic", "balanced"); s.setdefault("relations", {})
            if s.get("club") and "budget" not in s:
                s.update(budget=annual_budget(career.world, s["club"]), budget_year=career.year, fin={"spent": 0.0, "income": 0.0},
                         window=None, season_moves=[], prize=0.0)
            s.setdefault("formation", squad_mod.DEFAULT_FORMATION)
            if s.get("club") and s.get("squad_club") != s["club"]:       # состав клуба появился в этой версии
                squad_mod.build(career, s["club"]); s["squad_club"] = s["club"]

    @property
    def s(self):
        return self.c.coach

    # ---------- начало ----------
    @staticmethod
    def start(career):
        """Игрок завершил карьеру и стал тренером: стартовый навык и репутация - из игровой карьеры."""
        c, rng = career, career.rng
        rep_src = c.report()
        peak = c.player.peak_ovr
        n_tro, n_aw = len(c.trophies), sum(1 for a in c.awards if a["code"] != "ballon_top30")
        caps = rep_src["totals"]["caps"]
        big = sum(1 for a in c.awards if a["code"] in ("ballon_dor", "ballon_silver", "ballon_bronze", "world_xi"))
        rating = clamp(42 + (peak - 70) * 0.5 + min(caps, 120) / 30 + min(n_tro, 20) * 0.35 + rng.gauss(0, 4), 32, 74)
        rep = clamp(12 + (peak - 62) * 1.6 + min(n_tro, 25) * 0.8 + n_aw * 1.5 + big * 4 + min(caps, 120) / 12, 5, 80)
        # клубы игровой карьеры помнят игрока: с теми, где он выигрывал трофеи, отношения лучше
        rel = {}
        for t in c.transfers:
            rel[t["to"]] = max(rel.get(t["to"], 0), 10)
        for t in c.trophies:
            if t.get("club"):
                rel[t["club"]] = min(60, rel.get(t["club"], 0) + 8)
        c.coach = {"rating": round(rating, 1), "rep": round(rep, 1), "club": None, "contract_left": 0, "project": "normal",
                   "anger": 0.0, "tactic": "balanced", "relations": rel, "seasons": [], "spells": [], "trophies": [], "awards": [],
                   "offers": [], "offer_reason": "start", "start_age": c.player.age, "start_year": c.year, "end_reason": None, "can_stay": False}
        c.status = "coach_offers"
        cc = CoachCareer(c)
        c.coach["offers"] = cc.make_offers("start")
        return cc

    # ---------- задача клуба ----------
    def expected(self, cid):
        """-> (ожидаемое место, число клубов, вид задачи). Ожидаемое место = 1 + сумма вероятностей оказаться ниже каждого соперника
        (чем ближе силы, тем ближе к 50/50): в выровненной лиге вроде MLS задача ближе к середине таблицы, явный фаворит - 1-е место."""
        w = self.c.world
        lid = w.club_league[cid]
        ids = w.league_clubs[lid]
        n = len(ids)
        me = w.score[cid]
        rank = int(round(1 + sum(1.0 / (1.0 + math.exp(-(w.score[o] - me) / 6.0)) for o in ids if o != cid)))
        rank = max(1, min(n, rank))
        tier = self.c.d.leagues[lid]["tier"]
        if tier > 1 and rank <= max(2, n // 6):
            kind = "promotion"
        elif rank == 1:
            kind = "title"
        elif rank <= max(3, n // 5):
            kind = "top"
        elif rank <= n // 2:
            kind = "top_half"
        elif rank <= n - 4:
            kind = "mid"
        else:
            kind = "survive"
        return rank, n, kind

    # ---------- отношения с клубами ----------
    def rel(self, cid):
        return self.s["relations"].get(cid, 0)

    def _rel_add(self, cid, v):
        r = self.s["relations"]
        r[cid] = round(clamp(r.get(cid, 0) + v, -100, 100), 1)

    def _rel_decay(self):
        """Отношения понемногу забываются (обида уволившего клуба держится годами)."""
        r = self.s["relations"]
        for k in list(r):
            r[k] = round(r[k] * 0.93, 1)
            if abs(r[k]) < 2:
                del r[k]

    # ---------- предложения ----------
    def make_offers(self, reason):
        c, w, rng, d = self.c, self.c.world, self.c.rng, self.c.d
        s = self.s
        target = s["rep"] - (10 if reason == "fired" else 0)
        played = {x["to"] for x in c.transfers}                     # клубы игровой карьеры
        played_countries = {d.leagues[w.club_league[x]]["country"] for x in played if x in w.club_league}
        my_conf = d.countries[c.nat]["conf"]
        cands = []
        for cid, cl in d.clubs.items():
            if cl["reserve"] or cid == s.get("club"):
                continue
            rel = self.rel(cid)
            if rel <= REL_MIN_OFFER:
                continue                                         # уволивший клуб не позовёт, пока обида не забудется
            sc = w.score[cid]
            wgt = math.exp(-((sc - target) / 13.0) ** 2)
            if rel >= REL_LOVED:
                wgt = max(wgt, math.exp(-((sc - target) / 22.0) ** 2))   # бывший клуб, где вас любят, зовёт и «не по уровню»
            lc = d.leagues[w.club_league[cid]]["country"]
            if cl["country"] == c.nat:
                wgt *= 2.5
            elif lc in played_countries:
                wgt *= 1.6
            elif d.countries[lc]["conf"] != my_conf:
                wgt *= 0.5
            wgt *= math.exp(rel / 35.0)
            cands.append((cid, wgt))
        k = rng.randint(2, 3) if reason == "fired" else rng.randint(3, 5)
        offers, pool = [], cands[:]
        while pool and len(offers) < k:
            cid = rng.choices([x[0] for x in pool], weights=[x[1] + 1e-12 for x in pool])[0]
            pool = [x for x in pool if x[0] != cid]
            offers.append(self._offer(cid))
        offers.sort(key=lambda o: -w.score[o["club"]])
        return offers

    def _offer(self, cid):
        w, rng = self.c.world, self.c.rng
        rank, n, kind = self.expected(cid)
        rebuild = rng.random() < (0.15 if w.score[cid] >= 70 else 0.3)
        years = rng.randint(4, 5) if rebuild else rng.randint(2, 3)
        return {"club": cid, "project": "rebuild" if rebuild else "normal", "years": years, "target": rank, "n": n, "kind": kind,
                "pressure": pressure(w.score[cid], "rebuild" if rebuild else "normal"), "rel": self.rel(cid)}

    def accept(self, idx):
        c, s = self.c, self.s
        if idx == "stay":
            s["contract_left"] = c.rng.randint(2, 3) if s["project"] == "normal" else c.rng.randint(3, 4)
            s["spells"][-1]["extended"] = s["spells"][-1].get("extended", 0) + 1
        else:
            o = s["offers"][idx]
            self.leave_for_offer()
            # в клубе, где тренера помнят плохо, руководство заранее настороже
            s.update(club=o["club"], contract_left=o["years"], project=o["project"], anger=round(max(0.0, -self.rel(o["club"])) * 0.5, 1))
            s["spells"].append({"club": o["club"], "from": c.year, "to": None, "seasons": 0, "project": o["project"], "end": None})
            # новый клуб - свой бюджет на этот сезон и полный состав
            s.update(budget=annual_budget(c.world, o["club"]), budget_year=c.year, fin={"spent": 0.0, "income": 0.0},
                     window=None, season_moves=[], prize=0.0, academy_bonus=None)
            squad_mod.build(c, o["club"]); s["squad_club"] = o["club"]
            s["formation"] = squad_mod.club_formation(o["club"])           # начинаем со схемы, под которую собран состав
            s["lineup_mode"], s["lineup"] = "auto", {}
            s["euro"] = self._euro_guess(o["club"])
        s["offers"], s["offer_reason"], s["can_stay"] = [], None, False
        c.status = "coaching"

    # ---------- сезон: первая половина ----------
    def _boost(self):
        return clamp((self.s["rating"] - 60.0) * 0.08, -2.0, 2.5)          # навык тренера: до ~+1 OVR команды

    def window(self):
        return TransferWindow(self.c)

    def _euro_guess(self, cid):
        """Сыграет ли клуб в еврокубках (для новичков, которые не хотят в клуб без них): топ-4 высшей лиги по силе."""
        w = self.c.world
        lid = w.club_league[cid]
        return self.c.d.leagues[lid]["tier"] == 1 and self.expected(cid)[0] <= 4

    def begin_season(self, tactic=None, formation=None):
        """Первая половина сезона. -> данные середины сезона (таблица, раздражение руководства, увольнение)."""
        c, w, d, s = self.c, self.c.world, self.c.d, self.s
        if s.get("window"):
            TransferWindow(c).close()
        if tactic:
            s["tactic"] = tactic
        if formation:
            s["formation"] = formation
        cid = s["club"]
        squad_mod.apply_to_world(c)                                         # сила клуба = сила основы в выбранной схеме
        target, n, kind = self.expected(cid)
        rival_exp = coaches_mod.expectations(c, self)
        t1 = s["tactic"]
        res = w.begin_season(c.year, {cid: self._boost()}, {cid: team_mult(t1, s["rating"], s["formation"])})
        sq_events = squad_mod.play_half(c, press=t1 == "press")            # минуты, усталость, травмы первой половины
        for p in squad_mod.squad(c):                                        # зимняя пауза: игроки немного восстановились
            p["fit"] = min(100.0, p.get("fit", 100.0) + 10.0)
        squad_mod.apply_to_world(c)
        lid = w.club_league[cid]
        ht = res["half"][lid]
        rank = ht["order"].index(cid) + 1
        p = pressure(w.score[cid], s["project"])
        mid_pts = round(place_points(rank, target, len(ht["order"])) * p * MID_WEIGHT, 1)
        anger_mid = round(clamp(s["anger"] + max(0.0, mid_pts), 0.0, 100.0), 1)   # в середине сезона руководство только копит недовольство
        mid = {"rank": rank, "n": len(ht["order"]), "target": target, "kind": kind, "tactic": t1, "anger_before": s["anger"],
               "anger": anger_mid, "points": mid_pts, "fired": anger_mid >= FIRE_AT, "lid": lid, "squad_events": sq_events,
               "table": [[x, ht["w"][x], ht["d"][x], ht["l"][x], ht["gf"][x], ht["ga"][x], ht["pts"][x]] for x in ht["order"]]}
        c._coach_pending = {"res": res, "mid": mid, "rival_exp": rival_exp}
        return mid

    # ---------- сезон: вторая половина и итоги ----------
    def finish_season(self, tactic=None, formation=None):
        c, w, rng, d, s = self.c, self.c.world, self.c.rng, self.c.d, self.s
        pend = c._coach_pending
        c._coach_pending = None
        res, mid = pend["res"], pend["mid"]
        if s.get("window"):
            TransferWindow(c).close()                                       # зимнее окно закрывается перед второй половиной
        if formation and not mid["fired"]:
            s["formation"] = formation
        squad_mod.apply_to_world(c)
        cid = s["club"]
        year = c.year
        score = w.score[cid]
        fired_mid = mid["fired"]
        t2 = tactic or s["tactic"]
        if fired_mid:                                                       # уволен посреди сезона: дальше команда без него
            res = w.finish_season(res)
        else:
            s["tactic"] = t2
            tired = mid["tactic"] == "press" and t2 == "press"
            res = w.finish_season(res, {cid: self._boost()}, {cid: team_mult(t2, s["rating"], s["formation"], tired)})
        sq_events = list(mid.get("squad_events") or [])
        if not fired_mid:
            sq_events += squad_mod.play_half(c, press=t2 == "press")
            sq_events += squad_mod.end_of_season(c)                        # недовольные без игры, молодые без минут
        comps = w.club_comps(res, cid)
        stars_mod.simulate(c.stars, w, res, rng)                            # звёзды мира играют сезон (до переходов между дивизионами)
        lid = w.club_league[cid]
        league = d.leagues[lid]
        lg = comps[0]
        rank, n_real = lg["result"]["rank"], lg["result"]["n"]
        exp_rank, kind = mid["target"], mid["kind"]
        rec = {"season": season_label(year), "year": year, "age": c.player.age, "club": cid, "club_name": d.clubs[cid]["name"],
               "league": lid, "league_name": league["name"], "league_country": league["country"], "tier": league["tier"],
               "rank": rank, "n": n_real, "target": exp_rank, "kind": kind, "project": s["project"], "comps": [], "trophies": [],
               "awards": [], "events": [], "w": lg["result"]["w"], "d": lg["result"]["d"], "l": lg["result"]["l"],
               "rating": s["rating"], "tactics": [mid["tactic"], None if fired_mid else t2], "formation": s["formation"],
               "mid": {k: mid[k] for k in ("rank", "n", "anger", "points", "fired", "table")}, "squad_events": sq_events}
        for x in comps:
            res_x = {k: v for k, v in x["result"].items() if k != "gtable"}
            rec["comps"].append({"code": x["code"], "name_en": x["name_en"], "name_ru": x["name_ru"], "games": 0, "goals": 0, "assists": 0,
                                 "cs": 0, "team_games": x["team_games"], "result": res_x, "table": x.get("table")})
        # «Лучший тренер мира»: тренеры клубов мира против тренера-игрока (до переходов между дивизионами)
        me_pts = -99.0 if fired_mid else coaches_mod.points(c, res, cid, exp_rank, s["rating"])
        top, my_rank = coaches_mod.season(c, res, pend.get("rival_exp") or {}, me_pts)
        rec["best_coach"] = {"top": top, "rank": None if fired_mid else my_rank}
        changed = w.advance(res)
        ev = changed.get(cid)
        if ev:
            rec["events"].append({"t": ev})
        p = pressure(score, s["project"])
        before = s["anger"]
        if fired_mid:
            # трофеи и награды сезона достаются уже не ему; руководство уволило его посреди сезона
            rec.update(anger_before=round(before, 1), anger_after=100.0, reasons=[("mid_fired", round(mid["points"], 1))], pressure=p)
            s["anger"] = 100.0
        else:
            self._season_trophies(rec, comps, league, cid)
            reasons = [("league", round(place_points(rank, exp_rank, n_real) * p, 1))]
            for x in comps[1:]:
                st = x["result"].get("stage")
                v = (CUP_RELIEF.get(x["code"]) or CONT_RELIEF.get(x["code"]) or {}).get(st, 0)
                if v:
                    reasons.append(("cup:" + x["code"] + ":" + st, -v))
                if x["code"] == "UCL" and score >= 75 and st in ("LP", "GS", "PO"):
                    reasons.append(("cup:" + x["code"] + ":" + st, round(8 * p, 1)))   # топ-клуб не вышел из общего этапа ЛЧ
            if rank == 1 and league["tier"] == 1:
                reasons.append(("title", -35.0))
            if ev == "relegated":
                reasons.append(("relegated", 40.0 if kind != "survive" else 18.0))
            elif ev == "promoted":
                reasons.append(("promoted", -30.0))
            # деньги: крупные траты без результата злят, продажи с прибылью радуют маленькие клубы и проекты перестройки
            fin, annual = s.get("fin") or {"spent": 0.0, "income": 0.0}, annual_budget(w, cid)
            net = fin["spent"] - fin["income"]
            if net > 0.5 * annual and rank > exp_rank:
                reasons.append(("spending", round(min(25.0, 12.0 * net / annual) * p, 1)))
            elif net < -0.3 * annual and (s["project"] == "rebuild" or p < 0.9):
                reasons.append(("profit", -round(min(10.0, 6.0 * -net / annual), 1)))
            after = clamp(before * DECAY + sum(v for _, v in reasons), 0.0, 100.0)
            s["anger"] = round(after, 1)
            rec.update(anger_before=round(before, 1), anger_after=round(after, 1), reasons=reasons, pressure=p)
            # --- навык, репутация, награда
            over = (exp_rank - rank) / max(1, n_real - 1)                      # > 0 - выше задачи
            tro = len(rec["trophies"])
            s["rating"] = round(clamp(s["rating"] + (0.4 if c.player.age < 55 else 0.0) + 2.0 * over + 0.3 * tro + rng.gauss(0, 0.6), 25, 92), 1)
            lf = w.league_strength(league["country"]) / 100.0
            s["rep"] = round(clamp(0.85 * s["rep"] + 0.15 * score + 10 * over * lf + tro * 2.5 * lf
                                   + (8 if any(t["cat"] == "euro" for t in rec["trophies"]) else 0), 0, 100), 1)
            if (rank == 1 and league["tier"] == 1) or (over >= 0.35 and rank <= max(2, n_real // 3) and n_real >= 10):
                rec["awards"].append("coach_of_season"); s["awards"].append({"season": rec["season"], "code": "coach_of_season", "club": cid})
            if my_rank == 1:
                rec["awards"].append("best_coach"); s["awards"].append({"season": rec["season"], "code": "best_coach", "club": cid})
                s["rep"] = round(min(100.0, s["rep"] + 4), 1)
            s["euro"] = league["tier"] == 1 and rank <= 4 or any(x["code"] in CONT and x["result"].get("stage") == "W" for x in comps)
        # --- деньги сезона: сделки, призовые (придут в бюджет следующим летом)
        rec["moves"] = s.pop("season_moves", []) or []
        fin = s.get("fin") or {"spent": 0.0, "income": 0.0}
        rec["fin"] = {"spent": round(fin["spent"], 2), "income": round(fin["income"], 2), "budget": round(s.get("budget", 0.0), 2)}
        if not fired_mid:
            annual = annual_budget(w, cid)
            share = 0.0
            if rank == 1:
                share += 0.3 if league["tier"] == 1 else 0.15
            share += 0.2 if ev == "promoted" else 0.0
            for x in comps[1:]:
                share += ((CUP_RELIEF.get(x["code"]) or CONT_RELIEF.get(x["code"]) or {}).get(x["result"].get("stage"), 0)) / 100.0
            s["prize"] = round(annual * share, 2)
            rec["fin"]["prize"] = s["prize"]
        s["fin"] = {"spent": 0.0, "income": 0.0}
        # --- отношения с клубом
        self._rel_decay()
        titles = sum(1 for t in rec["trophies"] if t["code"] in ("league", "title2"))
        self._rel_add(cid, 3 + 30 * titles + 8 * (len(rec["trophies"]) - titles) - (60 if s["anger"] >= FIRE_AT else 0))
        # --- конец сезона: игроки стареют и растут (составом клуба тренера мир не распоряжается)
        stars_mod.PROTECTED.clear()
        if not fired_mid:
            stars_mod.PROTECTED.add(cid)
        stars_mod.evolve(c.stars, w, rng)
        stars_mod.PROTECTED.clear()
        coaches_mod.evolve(c)
        if not fired_mid:
            squad_mod.apply_to_world(c)                                     # игроки постарели и выросли - сила клуба по новому составу
        c.player.age += 1
        c.year += 1
        s["contract_left"] = max(0, s["contract_left"] - 1)
        sp = s["spells"][-1]; sp["seasons"] += 1; sp["to"] = c.year
        if fired_mid:
            verdict = "fired_mid"
        elif s["anger"] >= FIRE_AT:
            verdict = "fired"
        elif c.player.age >= COACH_RETIRE_AGE:
            verdict = "retired"
        elif s["contract_left"] == 0:
            verdict = "contract_end"
        else:
            verdict = None
        rec["verdict"] = verdict
        s["seasons"].append(rec)
        if verdict == "retired":
            sp["end"] = "retired"; s["end_reason"] = "age"; c.status = "coach_retired"
        elif verdict:
            sp["end"] = "fired" if verdict.startswith("fired") else verdict
            if verdict == "contract_end" and s["anger"] >= 60:
                self._rel_add(cid, -15)                                       # расстались недовольными
            self.begin_offers("fired" if verdict.startswith("fired") else verdict)
        return rec

    def play_season(self, tactic=None):
        """Сезон целиком без остановки в середине (тесты, быстрые прогоны)."""
        self.begin_season(tactic)
        return self.finish_season()

    def _season_trophies(self, rec, comps, league, cid):
        d, s = self.c.d, self.s
        cn_en, cn_ru = d.country_name(league["country"], "en"), d.country_name(league["country"], "ru")
        def trophy(cat, code, en, ru):
            t = {"season": rec["season"], "cat": cat, "code": code, "name_en": en, "name_ru": ru, "club": cid}
            rec["trophies"].append(t); s["trophies"].append(t)
        if rec["rank"] == 1:
            if league["tier"] == 1:
                trophy("domestic", "league", f"League champion: {league['name']} ({cn_en})", f"Чемпион: {league['name']} ({cn_ru})")
            else:
                trophy("domestic", "title2", f"Won {league['name']} ({cn_en})", f"Победа в лиге: {league['name']} ({cn_ru})")
        for x in comps[1:]:
            if x["result"].get("stage") == "W":
                trophy("domestic" if x["code"] in ("cup", "league_cup", "supercup") else "euro", x["code"], x["name_en"], x["name_ru"])

    def begin_offers(self, reason):
        s = self.s
        if reason == "fired":
            s["rep"] = round(clamp(s["rep"] - 8, 0, 100), 1)
        s["can_stay"] = reason == "contract_end" and s["anger"] < 60
        if s["can_stay"]:
            s["spells"][-1]["end"] = None                          # продление: тот же период работы может продолжиться
        s["offer_reason"] = reason
        s["offers"] = self.make_offers(reason)
        self.c.status = "coach_offers"

    def leave_for_offer(self):
        """Тренер выбрал другой клуб, хотя мог остаться: период в старом клубе закрывается (клубу немного обидно)."""
        s = self.s
        if s["spells"] and s["spells"][-1].get("end") is None:
            s["spells"][-1]["end"] = "left"
            self._rel_add(s["spells"][-1]["club"], -5)

    def retire(self):
        s = self.s
        if s["spells"] and s["spells"][-1].get("end") is None:
            s["spells"][-1]["end"] = "retired"
        s["end_reason"] = s.get("end_reason") or "choice"
        s["offers"] = []
        self.c.status = "coach_retired"

    # ---------- итоги и рекорды ----------
    def summary(self):
        s = self.s
        seasons = s["seasons"]
        w = sum(r["w"] for r in seasons); dr = sum(r["d"] for r in seasons); l = sum(r["l"] for r in seasons)
        cats = {}
        for t in s["trophies"]:
            cats[t["cat"]] = cats.get(t["cat"], 0) + 1
        return {"seasons": len(seasons), "w": w, "d": dr, "l": l, "pct": round(100 * w / max(1, w + dr + l)),
                "titles": sum(1 for t in s["trophies"] if t["code"] == "league"), "trophy_cats": cats,
                "fired": sum(1 for sp in s["spells"] if sp.get("end") == "fired"), "clubs": len({sp["club"] for sp in s["spells"]}),
                "best": min(((r["rank"], r["season"], r["club"]) for r in seasons if r["tier"] == 1), default=None)}

    def records(self):
        """Рекорды тренера. -> словарь; пустые значения - None."""
        s = self.s
        seasons, spells = s["seasons"], s["spells"]
        by_club = {}
        for sp in spells:
            by_club[sp["club"]] = by_club.get(sp["club"], 0) + sp["seasons"]
        streak = best_streak = 0                       # сезонов подряд без увольнения
        for r in seasons:
            if (r.get("verdict") or "").startswith("fired"):
                streak = 0
            else:
                streak += 1
                best_streak = max(best_streak, streak)
        tro_by_club = {}
        for t in s["trophies"]:
            b = tro_by_club.setdefault(t["club"], {"all": 0, "titles": 0})
            b["all"] += 1; b["titles"] += t["code"] in ("league", "title2")
        played = [r for r in seasons if r["w"] + r["d"] + r["l"] >= 10]
        best_pct = max(played, key=lambda r: r["w"] / (r["w"] + r["d"] + r["l"]), default=None)
        best_ppg = max(played, key=lambda r: (3 * r["w"] + r["d"]) / (r["w"] + r["d"] + r["l"]), default=None)
        over = max(seasons, key=lambda r: r["target"] - r["rank"], default=None)
        fired_spells = [sp for sp in spells if sp.get("end") == "fired"]
        longest = max(spells, key=lambda sp: sp["seasons"], default=None)
        return {
            "longest_spell": (longest["club"], longest["seasons"]) if longest else None,
            "legends": sorted([c for c, n in by_club.items() if n >= 10], key=lambda c: -by_club[c]),
            "no_fire_streak": best_streak,
            "trophies_by_club": sorted(tro_by_club.items(), key=lambda x: (-x[1]["titles"], -x[1]["all"])),
            "best_pct": (best_pct["season"], best_pct["club"], round(100 * best_pct["w"] / (best_pct["w"] + best_pct["d"] + best_pct["l"])))
                        if best_pct else None,
            "best_ppg": (best_ppg["season"], best_ppg["club"], round((3 * best_ppg["w"] + best_ppg["d"]) / (best_ppg["w"] + best_ppg["d"] + best_ppg["l"]), 2))
                        if best_ppg else None,
            "overachieve": (over["season"], over["club"], over["target"] - over["rank"], over["rank"], over["target"])
                           if over and over["target"] > over["rank"] else None,
            "shortest_fired": min(((sp["club"], sp["seasons"]) for sp in fired_spells), key=lambda x: x[1], default=None),
        }
