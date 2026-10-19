"""Карьера игрока: сезоны, статистика по турнирам, рост, трансферы, сборная, награды, завершение карьеры."""
import math, random, uuid, time
from .player import Player, clamp
from .positions import GROUP, XI_SLOTS
from .world import World, sigmoid, poisson, binom, SENS
from .stats import produce, clean_sheets, season_rating, club_team_points, nat_points, ballon_points, BDO_APPEAL, W_ATT
from . import stars as stars_mod

START_YEAR = 2026
RETIRE_AGE = 40
SAVE_VERSION = 2
CONT_CODES = ("UCL", "UEL", "UECL", "USC", "LIB", "SUD", "ACLE", "CCC")

def season_label(year):
    return f"{year}/{str(year + 1)[2:]}"

def market_value(ovr, age, pot):
    """Рыночная стоимость, млн евро."""
    v = 0.35 * math.exp((ovr - 55) / 5.6)
    if age <= 21:
        v *= 1 + max(0.0, pot - ovr) * 0.03
    elif age >= 29:
        v *= max(0.15, 1 - 0.13 * (age - 28))
    return max(0.05, v)

def youth_level(score, age):
    """Средний OVR молодёжной команды клуба силы score в возрасте age."""
    return 38 + 0.18 * score + (age - 15) * 4.5

class Career:
    def __init__(self, data, name, nat, pos, freq=1, seed=None, lang="ru", foot="R", height=None):
        """freq - через сколько сезонов показывать предложения клубов (в новых карьерах всегда 1: после каждого сезона)."""
        self.d = data
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.rng = random.Random(self.seed)
        self.id = uuid.uuid4().hex[:10]
        self.name, self.nat, self.pos, self.freq, self.lang = name, nat, pos, freq, lang
        self.player = Player.generate(name, nat, pos, self.rng, foot=foot, height=height)
        self.world = World(data, self.rng, START_YEAR)
        self.stars = stars_mod.new_pool(self.world, self.rng)
        self.year = START_YEAR
        self.status = "academy_pick"
        self.club_id = None
        self.parent_id = None
        self.contract_left = 0
        self.seasons, self.transfers, self.trophies, self.awards = [], [], [], []
        self.academy_ids, self.offers, self.offer_reason = [], [], None
        self.seasons_in_period = 0
        self.seasons_at_club = 0
        self.last_share = 1.0
        self.serious_inj = 0
        self.retire_reason = None
        self.can_stay = True
        self.created = time.time()
        self.captain = False                 # капитан нынешнего клуба (повязка снимается при уходе)
        self.captain_seasons = 0
        self._chron_pending = []             # события летописи между сезонами (переход, капитанство) -> в следующий сезон
        self.coach = None                    # тренерская карьера после завершения игровой (game/coach.py)
        self._coach_pending = None           # сезон тренера между половинами (только в памяти, сохраняется по итогам сезона)
        self.academy_ids = self._academy_options()

    # ---------- старт ----------
    def reroll(self):
        self.player = Player.generate(self.name, self.nat, self.pos, self.rng, foot=self.player.foot, height=self.player.height)

    def _academy_options(self):
        rng, d = self.rng, self.d
        pool = d.clubs_of_country(self.nat)
        if len(pool) < 5:
            return self._academy_options_abroad(pool)
        pool = sorted(pool, key=lambda c: -self.world.score[c["id"]])
        foreign = [c for c in d.clubs.values() if not c["reserve"] and c not in pool]
        k = min(rng.randint(3, 5), len(pool))
        picks = []
        for i in range(k):
            for _ in range(20):
                if rng.random() < 0.10:
                    c = rng.choice(foreign)                         # 1/10: академия из другой страны
                else:
                    q = (i + rng.random()) / k
                    c = pool[min(len(pool) - 1, int(q * len(pool)))]
                if c["id"] not in picks:
                    picks.append(c["id"]); break
        return picks

    def _academy_options_abroad(self, home):
        """Страна без своей лиги (или почти без клубов): академии из нескольких стран, а не из одной.
        Запасная страна из базы (Япония -> Германия), соседи по конфедерации (Корея, Китай, Саудовская Аравия...)
        и иногда сильная лига из другой части света."""
        rng, d = self.rng, self.d
        me = d.countries[self.nat]
        fb = me["fallback"] or d.league_host.get(self.nat)
        by_country = {}
        for c in d.clubs.values():
            if not c["reserve"] and c["country"] != self.nat:
                by_country.setdefault(c["country"], []).append(c)
        strength = lambda k: d.countries[k]["lstrength"] or 30.0
        def take(cands, n, wfun):
            cands, out = list(cands), []
            while cands and len(out) < n:
                k = rng.choices(cands, weights=[wfun(x) for x in cands])[0]
                cands.remove(k); out.append(k)
            return out
        conf = [k for k in by_country if k != fb and d.countries[k]["conf"] == me["conf"]]
        sources = [None] if home else []                            # None - клуб своей страны
        if fb in by_country:
            sources.append(fb)
        sources += take(conf, 2 if fb in by_country else 3, lambda k: 1.0 + strength(k) / 25.0)
        rest = [k for k in by_country if k not in sources]
        sources += take(rest, 1 if rng.random() < 0.6 or len(sources) < 3 else 0, lambda k: (strength(k) / 25.0) ** 3 + 0.05)
        if fb in by_country and len(sources) < 4:
            sources.append(fb)                                      # вторая академия из основной страны
        rng.shuffle(sources)
        picks = []
        for src in sources[:rng.randint(4, 5)]:
            clubs = home if src is None else by_country[src]
            free = [c for c in clubs if c["id"] not in picks]
            if free:
                picks.append(rng.choice(free)["id"])
        return sorted(picks, key=lambda c: -self.world.score[c])

    def academy_tag(self, cid):
        """home - клуб вашей страны; nolg - в вашей стране нет лиги в базе; foreign - зарубежная академия."""
        if self.d.clubs[cid]["country"] == self.nat:
            return "home"
        return "foreign" if self.d.clubs_of_country(self.nat) else "nolg"

    def choose_academy(self, club_id):
        self.club_id = club_id
        self.contract_left = 3
        self.transfers.append({"season": season_label(self.year), "from": None, "to": club_id, "fee": 0.0, "type": "academy"})
        self.status = "playing"
        self.seasons_in_period = 0
        self.seasons_at_club = 0

    # ---------- сезон ----------
    def play_season(self):
        p, w, rng, d = self.player, self.world, self.rng, self.d
        year, age = self.year, p.age
        cid = self.club_id
        club = d.clubs[cid]
        youth = age < 18
        lid = w.club_league[cid]
        league = d.leagues[lid]
        score = w.score[cid]
        ovr, attrs = p.ovr(), p.attrs()
        team = w.team_ovr(cid)
        if youth:
            diff = ovr - youth_level(score, age)
            p_start = 0.5 + 0.5 * sigmoid((diff + 2) / 3.5)          # в молодёжной команде играют регулярно
            boost = {}
        else:
            diff = ovr - team
            p_start = sigmoid((diff + 3) / 3.2)
            if self.captain:                                  # капитану тренер доверяет больше
                p_start = min(0.97, p_start + 0.05)
            boost = {cid: clamp(diff * 0.3 * p_start, -2.0, 7.0)}
        res = w.simulate_season(year, boost)
        team_eff = team + 0.4 * boost.get(cid, 0.0)

        # --- травмы
        inj_weeks, inj_hit = 0, 0.0
        if rng.random() < (0.30 if age <= 30 else 0.40):
            inj_weeks = min(52, 1 + int(rng.expovariate(1 / 8.0)))
        if inj_weeks >= 30:
            self.serious_inj += 1
            inj_hit = rng.uniform(0.5, 2.5) if age >= 24 else rng.uniform(0, 1.2)
        avail = 1.0 - min(inj_weeks, 44) / 46.0
        share = p_start * avail

        rec = {"season": season_label(year), "year": year, "age": age, "club": cid, "club_name": club["name"], "league": lid,
               "league_name": league["name"], "league_country": league["country"], "tier": league["tier"], "youth": youth,
               "loan": self.parent_id is not None, "ovr": ovr, "share": round(share, 2), "club_stars": w.stars(cid),
               "comps": [], "trophies": [], "awards": [], "events": [], "intl": None, "nat_comps": [], "ballon": None, "rating": None,
               "captain": self.captain and not youth}
        if inj_weeks >= 4:
            rec["events"].append({"t": "injury", "weeks": inj_weeks, "serious": inj_weeks >= 30})

        def add_trophy(cat, code, name_en, name_ru):
            t = {"season": rec["season"], "cat": cat, "code": code, "name_en": name_en, "name_ru": name_ru, "club": cid}
            rec["trophies"].append(t); self.trophies.append(t)

        team_comps = w.club_comps(res, cid)
        if youth:
            mu = self._youth_season(rec, res, team_comps, share, ovr, attrs, team, score, add_trophy)
        else:
            mu = self._senior_season(rec, team_comps, share, ovr, attrs, team_eff, add_trophy)
        for k in ("games", "goals", "assists", "cs"):
            rec[k] = sum(c[k] for c in rec["comps"])
        cs_perf = (rec["cs"] - mu[2]) / max(4.0, mu[2])
        att_perf = (rec["goals"] + 0.7 * rec["assists"] - mu[0] - 0.7 * mu[1]) / max(3.0, mu[0] + 0.7 * mu[1])
        if p.pos == "GK":
            perf = cs_perf
        elif GROUP[p.pos] == "DEF":                         # защитники: сухие матчи + голевые действия (CB 75/25, LB/RB 60/40)
            w_att = W_ATT[p.pos]
            perf = w_att * att_perf + (1 - w_att) * cs_perf
        else:
            perf = att_perf
        perf = clamp(perf, -1.0, 1.5)

        # --- сборная (результаты сборной показываются всегда, даже без вызова)
        stages = self._national(res, rec, ovr, attrs, add_trophy)

        # --- звёзды мира и награды
        star_out = stars_mod.simulate(self.stars, w, res, rng)
        if not youth:
            self._awards(rec, res, team_comps, star_out, stages, ovr)

        # --- рост
        p.grow(rng, share, score / 100.0, perf, inj_hit, rec["rating"], p_start)
        p.age += 1
        rec["ovr_end"] = p.ovr()
        changed = w.advance(res)
        stars_mod.evolve(self.stars, w, rng)
        if changed.get(cid):
            rec["events"].append({"t": changed[cid]})
        self.year += 1
        self.contract_left = max(0, self.contract_left - 1)
        self.seasons_at_club += 1
        self.last_share = share
        # --- капитан: опытный (2+ сезона в клубе, 23+ лет) ключевой игрок, сыгравший хороший сезон; повязка - до ухода из клуба
        if self.captain:
            self.captain_seasons += 1
        elif (not youth and self.parent_id is None and self.seasons_at_club >= 2 and age >= 23 and share >= 0.6
              and (rec["rating"] or 0) >= 7.0 and ovr >= team - 2):
            self.captain = True
            self._chron_pending.append({"k": "captain", "club": cid})
        if not youth:                                    # результаты матчей лиги и место после первого круга - только для истории сезона
            rec["matches"] = w.club_matches(res, cid)
            half = res.get("half", {}).get(lid)
            if half and cid in half["order"]:
                rec["mid_rank"] = half["order"].index(cid) + 1
        rec["chronicle"] = self._chronicle(rec)
        self.seasons.append(rec)
        return rec

    # ---------- летопись карьеры ----------
    MILESTONES_GOALS = (50, 100, 150, 200, 250, 300, 400, 500)
    MILESTONES_GAMES = (100, 200, 300, 400, 500, 600, 700, 800)
    MILESTONES_CAPS = (25, 50, 100, 150)

    def _chronicle(self, rec):
        """Заголовки сезона из его статистики: дебюты, первые голы, юбилеи, трофеи, награды, переходы, капитанство, травмы."""
        out = list(self._chron_pending)                   # события между сезонами (переход, капитанская повязка)
        self._chron_pending = []
        prev = self.seasons
        tot = lambda key: sum(s[key] for s in prev)
        caps_prev = sum((s["intl"] or {}).get("caps", 0) for s in prev)
        ngoals_prev = sum((s["intl"] or {}).get("goals", 0) for s in prev)
        senior_games = lambda s: sum(c["games"] for c in s.get("comps", []) if c.get("senior") or not s["youth"])
        senior_goals = lambda s: sum(c["goals"] for c in s.get("comps", []) if c.get("senior") or not s["youth"])
        if senior_games(rec) > 0 and not any(senior_games(s) > 0 for s in prev):
            out.append({"k": "debut", "club": rec["club"], "age": rec["age"]})
        if senior_goals(rec) > 0 and not any(senior_goals(s) > 0 for s in prev):
            out.append({"k": "first_goal", "club": rec["club"], "age": rec["age"]})
        intl = rec["intl"] or {}
        if intl.get("caps", 0) > 0 and caps_prev == 0:
            out.append({"k": "nat_debut", "age": rec["age"]})
        if intl.get("goals", 0) > 0 and ngoals_prev == 0:
            out.append({"k": "nat_first_goal"})
        for key, marks, k in (("goals", self.MILESTONES_GOALS, "goals_mark"), ("games", self.MILESTONES_GAMES, "games_mark")):
            a, b = tot(key), tot(key) + rec[key]
            for m in marks:
                if a < m <= b:
                    out.append({"k": k, "n": m})
        for m in self.MILESTONES_CAPS:
            if caps_prev < m <= caps_prev + intl.get("caps", 0):
                out.append({"k": "caps_mark", "n": m})
        if not rec["youth"] and self.pos != "GK":
            best_before = max((s["goals"] for s in prev if not s["youth"]), default=0)
            if rec["goals"] >= 20 and rec["goals"] > best_before:
                out.append({"k": "best_goals", "n": rec["goals"]})
        if rec["trophies"] and not any(s["trophies"] for s in prev):
            out.append({"k": "first_trophy", "name_ru": rec["trophies"][0]["name_ru"], "name_en": rec["trophies"][0]["name_en"]})
        for t in rec["trophies"]:
            if t["code"] in ("UCL", "WC", "EURO", "CA", "LIB"):
                out.append({"k": "big_trophy", "name_ru": t["name_ru"], "name_en": t["name_en"]})
        for a in rec["awards"]:
            if a in ("ballon_dor", "ballon_silver", "ballon_bronze", "golden_boot", "league_poty", "world_xi", "best_young"):
                out.append({"k": "award", "code": a})
        for e in rec["events"]:
            if e["t"] == "injury" and e.get("serious"):
                out.append({"k": "injury", "weeks": e["weeks"]})
            elif e["t"] in ("promoted", "relegated"):
                out.append({"k": e["t"], "club": rec["club"]})
        return out

    def _comp_entry(self, c, n, g, a, k, senior=False):
        res = {key: v for key, v in c["result"].items() if key != "gtable"}      # таблица группы идёт отдельно, в "table"
        return {"code": c["code"], "name_en": c["name_en"], "name_ru": c["name_ru"], "games": n, "goals": g, "assists": a, "cs": k,
                "team_games": c["team_games"], "result": res, "senior": senior, "table": c.get("table")}

    def _senior_season(self, rec, team_comps, share, ovr, attrs, team, add_trophy):
        p, rng, d = self.player, self.rng, self.d
        mg = ma = mc = 0.0
        played = {}
        for c in team_comps:
            code = c["code"]
            sh = share * 0.8 if code in ("cup", "league_cup") else (min(1.0, share + 0.1) if code == "supercup" else share)
            n = binom(rng, c["team_games"], clamp(sh, 0.0, 0.97))
            g, a, mu_g, mu_a = produce(rng, p.pos, ovr, team, c["opp"], n, attrs, style=p.style())
            k, mu_k = clean_sheets(rng, n, team, c["opp"]) if GROUP[p.pos] in ("GK", "DEF") else (0, 0.0)
            mg += mu_g; ma += mu_a; mc += mu_k
            rec["comps"].append(self._comp_entry(c, n, g, a, k))
            played[code] = n
        lg = team_comps[0]
        r = lg["result"]
        rec["rank"], rec["n"] = r["rank"], r["n"]
        league = d.leagues[rec["league"]]
        cn_en, cn_ru = d.country_name(league["country"], "en"), d.country_name(league["country"], "ru")
        if r["rank"] == 1:
            if league["tier"] == 1:
                add_trophy("domestic", "league", f"League champion: {league['name']} ({cn_en})", f"Чемпион: {league['name']} ({cn_ru})")
            else:
                add_trophy("domestic", "title2", f"Won {league['name']} ({cn_en})", f"Победа в лиге: {league['name']} ({cn_ru})")
        in_squad = sum(played.values()) > 0
        for c in team_comps[1:]:
            code, st = c["code"], c["result"].get("stage")
            # суперкубок - один матч: трофей получает и игрок заявки, который в этом матче не вышел
            if st != "W" or not (played.get(code, 0) > 0 or (code in ("supercup", "USC") and in_squad)):
                continue
            if code in ("cup", "league_cup", "supercup"):
                add_trophy("domestic", code, c["name_en"], c["name_ru"])
            else:
                add_trophy("euro", code, c["name_en"], c["name_ru"])
        return mg, ma, mc

    def _youth_season(self, rec, res, team_comps, share, ovr, attrs, team, score, add_trophy):
        """Академия (15-17 лет): своя молодёжная лига; основная команда - только если вызвали на кубок или дебют в лиге."""
        p, w, rng, d = self.player, self.world, self.rng, self.d
        age, cid = p.age, self.club_id
        country = d.leagues[rec["league"]]["country"]
        others = sorted((c for c in w.club_league if c != cid and not d.clubs[c]["reserve"]
                         and d.leagues[w.club_league[c]]["country"] == country), key=lambda c: -w.score[c])[:15]
        ids = [cid] + others
        lvl = {c: w.score[c] + rng.gauss(0, 10) for c in ids}
        lvl[cid] += clamp((ovr - youth_level(score, age)) * 0.6 * share, -3, 6)
        pts, gf, ga, wn, dr, ls = ({c: 0 for c in ids} for _ in range(6))
        for i in range(len(ids)):
            for j in range(len(ids)):
                if i == j:
                    continue
                h, a = ids[i], ids[j]
                dd = lvl[h] - lvl[a]
                x, y = poisson(rng, 1.45 * math.exp(SENS * dd)), poisson(rng, 1.15 * math.exp(-SENS * dd))
                gf[h] += x; ga[h] += y; gf[a] += y; ga[a] += x
                if x > y: pts[h] += 3; wn[h] += 1; ls[a] += 1
                elif x < y: pts[a] += 3; wn[a] += 1; ls[h] += 1
                else: pts[h] += 1; pts[a] += 1; dr[h] += 1; dr[a] += 1
        order = sorted(ids, key=lambda c: (pts[c], gf[c] - ga[c], gf[c], rng.random()), reverse=True)
        n_t = len(ids)
        tg = 2 * (n_t - 1)
        rank = order.index(cid) + 1
        yref = youth_level(score, age)
        opp = sum(youth_level(w.score[c], age) for c in ids) / n_t
        n = binom(rng, tg, clamp(share, 0.0, 0.97))
        g, a, mg, ma = produce(rng, p.pos, ovr, yref, opp, n, attrs, 1.1, p.style())
        k, mc = clean_sheets(rng, n, yref, opp) if GROUP[p.pos] in ("GK", "DEF") else (0, 0.0)
        cn_en, cn_ru = d.country_name(country, "en"), d.country_name(country, "ru")
        rec["comps"].append({"code": "youth", "name_en": f"U-18 League ({cn_en})", "name_ru": f"Молодёжная лига U-18 ({cn_ru})",
                             "games": n, "goals": g, "assists": a, "cs": k, "team_games": tg, "senior": False,
                             "result": {"rank": rank, "n": n_t, "pts": pts[cid], "gf": gf[cid], "ga": ga[cid], "w": wn[cid], "d": dr[cid], "l": ls[cid]},
                             "table": [[c, wn[c], dr[c], ls[c], gf[c], ga[c], pts[c]] for c in order]})
        rec["rank"], rec["n"] = rank, n_t
        tot_ga = sum(ga.values()) / (n_t * tg)
        rec["rating"] = season_rating(p.pos, n, g, a, k, ovr, opp, rank, n_t, ga[cid] / tg, tot_ga)
        if rank == 1:
            add_trophy("youth", "youth_league", f"U-18 League champion ({cn_en})", f"Чемпион молодёжной лиги U-18 ({cn_ru})")
        # --- вызов в основную команду: кубок (с 16 лет), дебют в лиге (в 17 лет)
        lg = team_comps[0]
        cup = next((c for c in team_comps if c["code"] == "cup"), None)
        if age >= 16 and cup and rng.random() < sigmoid((ovr - (team - 12)) / 2.5) * (0.5 if age == 16 else 0.75):
            n2 = rng.randint(1, min(3, cup["team_games"]))
            g2, a2, mg2, ma2 = produce(rng, p.pos, ovr, team, cup["opp"], n2, attrs, style=p.style())
            k2 = clean_sheets(rng, n2, team, cup["opp"])[0] if GROUP[p.pos] in ("GK", "DEF") else 0
            rec["comps"].append(self._comp_entry(cup, n2, g2, a2, k2, senior=True))
            mg += mg2; ma += ma2
        if age == 17 and rng.random() < sigmoid((ovr - (team - 6)) / 2.0) * 0.6:
            n3 = rng.randint(1, min(6, lg["team_games"]))
            g3, a3, mg3, ma3 = produce(rng, p.pos, ovr, team, lg["opp"], n3, attrs, style=p.style())
            k3 = clean_sheets(rng, n3, team, lg["opp"])[0] if GROUP[p.pos] in ("GK", "DEF") else 0
            rec["comps"].append(self._comp_entry(lg, n3, g3, a3, k3, senior=True))
            mg += mg3; ma += ma3
        return mg, ma, mc

    def _national(self, res, rec, ovr, attrs, add_trophy):
        """Сборная за сезон. Итоги сборной в турнирах записываются всегда; статистика игрока - если его вызвали.
        -> список (турнир, стадия) финальных турниров, где игрок сыграл (для очков Золотого мяча)."""
        p, w, rng, d = self.player, self.world, self.rng, self.d
        nat = self.nat
        nov = w.nat_ovr(nat)
        thr = nov - 5
        pc = sigmoid((ovr - thr) / 2.0)
        if p.age < 18:
            pc = pc * 0.3 if (p.age == 17 and ovr >= thr + 6) else 0.0
        called = rng.random() < pc
        sn = sigmoid((ovr - (nov - 1)) / 3.0)
        caps = goals = assists = 0
        stages, tours = [], []
        for e in res["nat_season"].get(nat, []):
            apps = binom(rng, e["games"], clamp(0.3 + 0.65 * sn, 0.15, 0.95)) if called else 0
            g, a, *_ = produce(rng, p.pos, ovr, nov, e["opp"] or nov, apps, attrs, 0.9, p.style())
            caps += apps; goals += g; assists += a
            comp = d.comps.get(e["code"], {})
            rec["nat_comps"].append({"kind": e["kind"], "code": e["code"], "year": e["year"], "games": apps, "goals": g, "assists": a,
                                     "team_games": e["games"], "info": e["info"]})
            st = None
            if e["kind"] == "final":
                st = e["info"]["stage"]
            elif e["kind"] == "unl" and e["info"].get("finals"):
                st = e["info"]["finals"]["stage"]
            if called and st:
                if apps > 0:
                    stages.append((e["code"], st))
                if e["kind"] == "final":
                    tours.append({"code": e["code"], "stage": st, "games": apps, "goals": g, "assists": a})
                if st == "W":
                    add_trophy("national", e["code"], comp.get("name_en", e["code"]), comp.get("name_ru", e["code"]))
        rec["intl"] = {"called": called, "caps": caps, "goals": goals, "assists": assists, "tournaments": tours}
        return stages

    def _awards(self, rec, res, team_comps, star_out, stages, ovr):
        rng, p, w, d = self.rng, self.player, self.world, self.d
        lid = rec["league"]
        league = d.leagues[lid]
        ls = w.league_strength(league["country"])
        lgc = rec["comps"][0]
        lg_team = team_comps[0]
        r = lg_team["result"]
        lgames = max(1, lg_team["team_games"])
        lg_ga = stars_mod.league_ga_pg(res, lid)
        rating = season_rating(p.pos, rec["games"], rec["goals"], rec["assists"], rec["cs"], ovr, lg_team["opp"], r["rank"], r["n"],
                               r["ga"] / lgames, lg_ga)
        rec["rating"] = rating
        def award(code, **extra):
            rec["awards"].append(code); self.awards.append({"season": rec["season"], "code": code, "club": rec["club"], **extra})

        # --- награды лиги: только при регулярной игре в лиге, по оценке за сезон (статистика + место команды)
        rivals = [s for s in star_out if s["league"] == lid and s["lg"]["apps"] >= 0.5 * s["lg_team_games"]]
        group = GROUP[p.pos]
        if lgc["games"] >= 0.55 * lgames and rating:
            best_rival = max((s["rating"] for s in rivals), default=0.0)
            if rating >= max(7.75 + rng.gauss(0, 0.06), best_rival + 0.01):
                award("league_poty")
            elif rating >= 7.45 + rng.gauss(0, 0.06) and sum(1 for s in rivals if GROUP[s["pos"]] == group and s["rating"] > rating) < XI_SLOTS[group]:
                award("league_xi")
        if lgc["games"] >= 0.5 * lgames and lgc["goals"] >= 8:
            synth = rng.gauss(0.64 * lgames, 3.0)              # лучший бомбардир лиги среди остальных игроков
            if lgc["goals"] > max([synth] + [s["lg"]["goals"] for s in star_out if s["league"] == lid]):
                award("golden_boot")

        # --- мировые награды: очки = статистика (с поправкой на уровень лиги) + трофеи клуба и сборной + класс
        tg_total = sum(c["team_games"] for c in rec["comps"])
        eligible = rec["games"] >= 0.4 * max(1, tg_total)
        club_pts = club_team_points(team_comps, ls, league["tier"]) if rec["games"] >= 0.35 * max(1, tg_total) else 0.0
        pts = ballon_points(p.pos, rec["games"], rec["goals"], rec["assists"], rec["cs"], ls, ovr, club_pts + nat_points(stages))
        rec["bdo_pts"] = pts
        me = {"me": True, "name": p.name, "nat": self.nat, "club": rec["club"], "pos": p.pos, "goals": rec["goals"],
              "assists": rec["assists"], "pts": pts}
        vote = lambda x, pos: x * BDO_APPEAL.get(pos, 1.0) * (1 + rng.gauss(0, 0.04))
        field = [(vote(s["pts"], s["pos"]), dict(s)) for s in star_out]
        if eligible:
            field.append((vote(pts, p.pos), me))
        field.sort(key=lambda x: -x[0])
        ranked = [x[1] for x in field]
        rank = next((i + 1 for i, s in enumerate(ranked) if s.get("me")), None)
        slim = lambda s: {"name": s["name"], "nat": s["nat"], "club": s["club"], "pos": s["pos"], "goals": s["goals"],
                          "assists": s["assists"], "me": bool(s.get("me"))}
        rec["ballon"] = {"year": rec["year"] + 1, "rank": rank if rank and rank <= 30 else None, "top": [slim(s) for s in ranked[:10]],
                         "ahead": [slim(s) for s in ranked[:rank - 1]] if rank and rank <= 3 else []}
        if rank == 1: award("ballon_dor")
        elif rank == 2: award("ballon_silver")
        elif rank == 3: award("ballon_bronze")
        elif rank and rank <= 30: award("ballon_top30", rank=rank)      # место в голосовании среди 30 номинантов
        good = eligible and (rating or 0) >= 7.35          # мировые сборные и награды только за сильный личный сезон
        if good and pts >= 50 and sum(1 for s in star_out if GROUP[s["pos"]] == group and s["pts"] > pts) < XI_SLOTS[group]:
            award("world_xi")
        appeal = lambda x, pos: x * BDO_APPEAL.get(pos, 1.0)
        if p.age <= 21 and good and appeal(pts, p.pos) >= 40 and not any(appeal(s["pts"], s["pos"]) > appeal(pts, p.pos)
                                                                         for s in star_out if s["age"] <= 21):
            award("best_young")

    # ---------- завершение периода ----------
    def play_period(self):
        """Играет сезоны до конца периода / вынужденного события / завершения карьеры. -> (записи, причина)"""
        out, reason = [], None
        while reason is None:
            rec = self.play_season(); out.append(rec)
            self.seasons_in_period += 1
            if self._maybe_retire():
                reason = "retired"; break
            a = self.player.age
            if a < 18:
                continue
            if a == 18 and rec["youth"]:
                reason = "academy_end"
            elif self.parent_id is not None:
                reason = "loan_end"
            elif self.contract_left == 0:
                reason = "contract"
            elif rec["share"] < 0.2 and self.seasons_at_club >= 1:
                reason = "benched"
            elif self.seasons_in_period >= self.freq:
                reason = "period_end"
        if reason == "retired":
            self.status = "retired"
        else:
            if reason == "loan_end":
                self.return_from_loan()
            self._begin_offers(reason)
        return out, reason

    def _maybe_retire(self):
        """Карьера заканчивается сама только в 40 лет; раньше - кнопкой «Завершить карьеру»."""
        if self.player.age >= RETIRE_AGE:
            self.retire_reason = "age"
            return True
        return False

    def retire_now(self):
        self.retire_reason = "choice"
        self.status = "retired"
        self.offers = []

    @property
    def coach_club(self):
        """Последний клуб: игровой, а если игрок стал тренером - клуб, где он тренирует (или тренировал последним)."""
        if self.coach and self.coach.get("spells"):
            return self.coach["spells"][-1]["club"]
        return self.parent_id or self.club_id

    @property
    def player_retire_age(self):
        """Возраст завершения игровой карьеры (у тренера player.age продолжает расти)."""
        return self.coach["start_age"] if self.coach else self.player.age

    def start_coaching(self):
        from .coach import CoachCareer
        return CoachCareer.start(self)

    def coaching(self):
        from .coach import CoachCareer
        return CoachCareer(self)

    # ---------- предложения ----------
    def _contract_years(self):
        a = self.player.age
        yrs = self.rng.randint(1, 2) if a >= 33 else self.rng.choice([2, 3, 3, 4, 5])
        return min(max(yrs, self.freq), max(1, RETIRE_AGE - a))

    def role_for(self, gap):
        return "key" if gap >= 2 else "starter" if gap >= -3 else "rotation" if gap >= -8 else "bench"

    def _begin_offers(self, reason):
        self.status = "offers"
        self.offer_reason = reason
        self.offers = self._make_offers(reason)
        self.can_stay = not (self.contract_left == 0 and self.last_share < 0.4) and reason != "academy_end"

    def _make_offers(self, reason):
        p, w, rng, d = self.player, self.world, self.rng, self.d
        ovr, age = p.ovr(), p.age
        cur = self.parent_id or self.club_id
        my_conf = d.countries[self.nat]["conf"]
        cands = []
        for cid, c in d.clubs.items():
            if c["reserve"] or cid == cur:
                continue
            gap = ovr - w.team_ovr(cid)
            center = -2 if age <= 21 else (3 if age >= 31 else 1)
            wgt = math.exp(-((gap - center) / 6.0) ** 2)
            lc = d.leagues[w.club_league[cid]]["country"]
            conf = d.countries[lc]["conf"]
            if c["country"] == self.nat:
                wgt *= 2.2
            elif conf == my_conf:
                wgt *= 1.25
            elif conf != "UEFA":
                wgt *= 0.4                                  # из Европы в Южную Америку и Азию уезжают редко
            if lc in ("KSA", "USA") and age >= 29:
                wgt *= 2.5                                  # богатые лиги зовут опытных
            cands.append((cid, wgt, gap))
        k = rng.randint(2, 5) + (1 if ovr >= 85 else 0)
        if age >= 33: k = min(k, 3)
        if reason == "academy_end": k = rng.randint(3, 5)
        k = clamp(k, 1, 5)
        offers = []
        if reason == "academy_end":
            offers.append(self._offer(cur, "first", 0.0, ovr - w.team_ovr(cur)))
            k -= 1
        pool = cands[:]
        loan_wanted = 18 <= age <= 22 and (self.last_share < 0.5 or rng.random() < 0.3) and reason != "loan_end"
        picked = []
        while pool and len(picked) < k:
            ch = rng.choices(pool, weights=[x[1] + 1e-9 for x in pool])[0]
            pool.remove(ch); picked.append(ch)
        for cid, _, gap in picked:
            offers.append(self._offer(cid, "transfer", None, gap, reason))
        if loan_wanted:
            easy = sorted([x for x in cands if x[2] >= 3 and x[0] not in [o["club"] for o in offers]], key=lambda x: -x[1])[:5]
            if easy:
                cid, _, gap = rng.choice(easy)
                offers = offers[:4] + [self._offer(cid, "loan", 0.0, gap)]
        offers.sort(key=lambda o: -w.score[o["club"]])
        return offers

    def _offer(self, cid, kind, fee, gap, reason=None):
        p, w, rng = self.player, self.world, self.rng
        if fee is None:
            val = market_value(p.ovr(), p.age, p.pot + rng.uniform(-3, 3))
            ls = w.league_strength(w.league_of(cid)["country"])
            fee = val * rng.uniform(0.8, 1.25) * (0.6 + 0.5 * ls / 100)
            if p.age < 19: fee *= 0.2
            if reason == "contract" or self.contract_left == 0: fee = 0.0
            fee = round(fee, 2) if fee < 10 else round(fee, 1)
        return {"club": cid, "kind": kind, "fee": fee, "years": 1 if kind == "loan" else (3 if kind == "first" else self._contract_years()),
                "role": self.role_for(gap), "gap": round(gap, 1)}

    def accept(self, idx):
        """idx: индекс в self.offers или 'stay'."""
        s = season_label(self.year)
        if idx == "stay":
            self.contract_left = min(self.rng.randint(2, 4), max(1, RETIRE_AGE - self.player.age))
        else:
            o = self.offers[idx]
            old = self.club_id
            if o["club"] != old:
                self.captain = False                           # капитанская повязка остаётся в старом клубе
            if o["kind"] == "loan":
                self.parent_id = self.parent_id or self.club_id
                self.transfers.append({"season": s, "from": old, "to": o["club"], "fee": 0.0, "type": "loan"})
                self.club_id = o["club"]
                self._chron_pending.append({"k": "loan", "club": o["club"]})
            else:
                if self.parent_id:
                    self.parent_id = None
                if o["club"] != old:
                    best_fee = max((t["fee"] for t in self.transfers), default=0.0)
                    self.transfers.append({"season": s, "from": old, "to": o["club"], "fee": o["fee"], "type": o["kind"]})
                    self._chron_pending.append({"k": "record_move" if o["fee"] > best_fee and o["fee"] >= 1 else "move",
                                                "club": o["club"], "fee": o["fee"]})
                self.club_id = o["club"]
                self.contract_left = o["years"]
            self.seasons_at_club = 0
        self.status = "playing"
        self.seasons_in_period = 0
        self.offers = []

    def return_from_loan(self):
        """После сезона в аренде игрок возвращается в родной клуб (вызывается перед показом предложений)."""
        if self.parent_id:
            loan_club = self.club_id
            self.club_id, self.parent_id = self.parent_id, None
            self.transfers.append({"season": season_label(self.year), "from": loan_club, "to": self.club_id, "fee": 0.0, "type": "return"})
            self.seasons_at_club = 0

    # ---------- итоги ----------
    def report(self):
        tot = {"games": 0, "goals": 0, "assists": 0, "cs": 0, "caps": 0, "intl_goals": 0, "intl_assists": 0}
        stints, by_comp = [], {}                         # периоды в клубах: возвращение в клуб после перерыва - новый период
        def add_comp(key, en, ru, g, go, a, cs):
            b = by_comp.setdefault(key, {"name_en": en, "name_ru": ru, "games": 0, "goals": 0, "assists": 0, "cs": 0})
            b["games"] += g; b["goals"] += go; b["assists"] += a; b["cs"] += cs
        for r in self.seasons:
            tot["games"] += r["games"]; tot["goals"] += r["goals"]; tot["assists"] += r["assists"]; tot["cs"] += r["cs"]
            if r["intl"]:
                tot["caps"] += r["intl"]["caps"]; tot["intl_goals"] += r["intl"]["goals"]; tot["intl_assists"] += r["intl"]["assists"]
            if not r["youth"]:
                yr = r.get("year", int(r["season"][:4]))
                if not stints or stints[-1]["club"] != r["club"]:
                    stints.append({"club": r["club"], "from": r["season"], "to": r["season"], "y0": yr, "y1": yr + 1,
                                   "games": 0, "goals": 0, "assists": 0, "loan": r.get("loan", False)})
                b = stints[-1]
                b["to"] = r["season"]; b["y1"] = yr + 1
                b["games"] += r["games"]; b["goals"] += r["goals"]; b["assists"] += r["assists"]
            if "comps" in r:
                for c in r["comps"]:
                    if c["games"] > 0:
                        key = ("youth", "") if c["code"] == "youth" else (c["code"], c["name_en"])
                        add_comp(key, c["name_en"], c["name_ru"], c["games"], c["goals"], c["assists"], c["cs"])
                for c in r.get("nat_comps", []):
                    if c["games"] > 0:
                        comp = self.d.comps.get(c["code"], {})
                        key = ("nat", c["code"], c["kind"] == "qual")
                        en, ru = (comp.get("name_en", "Friendlies"), comp.get("name_ru", "Товарищеские матчи")) if c["code"] != "FR" else ("Friendlies", "Товарищеские матчи")
                        if c["kind"] == "qual":
                            en, ru = f"{en}: qualifying", f"{ru}: отбор"
                        add_comp(key, f"National team · {en}", f"Сборная · {ru}", c["games"], c["goals"], c["assists"], 0)
            else:
                add_comp(("old", ""), "Club matches (old save)", "Клубные матчи (старое сохранение)", r["games"], r["goals"], r["assists"], r["cs"])
        cats = {}
        for t in self.trophies:
            cats[t["cat"]] = cats.get(t["cat"], 0) + 1
        aw = {}
        for a in self.awards:
            aw[a["code"]] = aw.get(a["code"], 0) + 1
        peak = max(self.seasons, key=lambda r: r["ovr"]) if self.seasons else None
        comps = sorted(by_comp.values(), key=lambda b: -b["games"])
        return {"totals": tot, "trophy_cats": cats, "award_counts": aw, "peak_ovr": self.player.peak_ovr,
                "peak_age": peak["age"] if peak else None, "clubs": stints, "comps": comps, "comps_chrono": list(by_comp.values()),
                "last_age": self.player_retire_age, "coach_club": self.coach_club}

    # ---------- сохранение ----------
    def to_dict(self):
        st = self.rng.getstate()
        return {"v": SAVE_VERSION, "id": self.id, "seed": self.seed, "name": self.name, "nat": self.nat, "pos": self.pos, "freq": self.freq,
                "lang": self.lang, "player": self.player.to_dict(), "world": self.world.to_dict(), "stars": self.stars, "year": self.year,
                "status": self.status, "club_id": self.club_id, "parent_id": self.parent_id, "contract_left": self.contract_left,
                "seasons": self.seasons, "transfers": self.transfers, "trophies": self.trophies, "awards": self.awards,
                "academy_ids": self.academy_ids, "offers": self.offers, "offer_reason": self.offer_reason,
                "seasons_in_period": self.seasons_in_period, "seasons_at_club": self.seasons_at_club, "last_share": self.last_share,
                "serious_inj": self.serious_inj, "retire_reason": self.retire_reason, "can_stay": self.can_stay, "created": self.created,
                "coach": self.coach, "captain": self.captain, "captain_seasons": self.captain_seasons, "chron_pending": self._chron_pending,
                "rng": [st[0], list(st[1]), st[2]]}

    @classmethod
    def from_dict(cls, data, d):
        c = cls.__new__(cls)
        c.d = d
        for k in ("id", "seed", "name", "nat", "pos", "freq", "lang", "year", "status", "club_id", "parent_id", "contract_left", "seasons",
                  "transfers", "trophies", "awards", "academy_ids", "offers", "offer_reason", "seasons_in_period", "seasons_at_club",
                  "last_share", "serious_inj", "retire_reason", "can_stay", "created"):
            setattr(c, k, data[k])
        c.coach = data.get("coach")
        c._coach_pending = None
        c.captain, c.captain_seasons = data.get("captain", False), data.get("captain_seasons", 0)
        c._chron_pending = data.get("chron_pending", [])
        c.rng = random.Random()
        r = data["rng"]
        c.rng.setstate((r[0], tuple(r[1]), r[2]))
        c.player = Player.from_dict(data["player"])
        old = data.get("v", 1) < SAVE_VERSION
        c.world = World(d, c.rng, data["year"])
        c.world.load_dict(data["world"], migrate=old)
        if data.get("stars"):
            c.stars = data["stars"]
        else:                                           # сохранение до появления звёзд мира: создаём их и «старим» до текущего года
            c.stars = stars_mod.new_pool(c.world, c.rng)
            for _ in range(max(0, data["year"] - START_YEAR)):
                stars_mod.evolve(c.stars, c.world, c.rng)
        if c.status == "retired" and c.player.age < RETIRE_AGE and not c.retire_reason:
            c.retire_reason = "choice"
        return c
