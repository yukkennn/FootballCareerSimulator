"""Трансферы тренера: бюджет клуба, трансферное окно (летнее и зимнее), покупка, продажа, аренда, молодёжь, скауты.

У клуба тренера настоящий состав (game/squad.py), и сила команды = сила основы в выбранной схеме. Поэтому эффект сделки -
это изменение силы основы: новичок усиливает, только если проходит в основу на своей позиции (или рядом), продажа запасного
почти ничего не меняет. Игроки стареют и растут сами (stars.evolve; молодые - тем быстрее, чем больше играют).
Бюджет (млн €) в год - по финансовому масштабу клуба (исходная сила из базы, 70%) и уровню лиги (Реал ~250, Аякс ~40,
Селтик ~18, Кайрат ~2), плюс призовые за сезон, плюс деньги от продаж, минус зарплаты скаутов; неистраченное остаётся.
Аренда: свой игрок уходит на сезон туда, где будет играть (растёт), чужой приходит на сезон за небольшую плату.
Скауты (до трёх, со звёздами и рейтингом): сужают вилку потенциала, расширяют рынок и находят недооценённых молодых.
Сильный игрок может отказаться перейти в клуб, который не играет в еврокубках.
"""
import math
from .player import clamp
from . import stars as stars_mod
from . import squad as squad_mod
from .career import market_value

BUY_PREMIUM = 1.15           # покупка дороже рыночной стоимости
LOAN_FEE = 0.1               # аренда игрока на сезон - 10% его стоимости
MAX_SCOUTS = 3

def annual_budget(world, cid):
    """Трансферный бюджет клуба на сезон, млн €. Зависит от финансового масштаба клуба (исходная сила из базы, 70%) и лишь
    частично от нынешней силы (30%): покупки не делают клуб богаче, иначе сильный клуб покупал бы всё больше и больше."""
    d = world.d
    score = 0.7 * d.clubs[cid]["score"] + 0.3 * world.score[cid]
    ls = world.league_strength(world.league_of(cid)["country"])
    return round(max(0.05, 0.12 * math.exp(clamp(score, -30, 110) / 12.0) * (0.3 + 0.7 * ls / 100.0)), 2)

def price(ovr, age, pot):
    return round(market_value(ovr, age, pot), 2)

# ---------- скауты ----------
def scout_stars(rating):
    return 5 if rating >= 85 else 4 if rating >= 75 else 3 if rating >= 65 else 2 if rating >= 55 else 1

def scout_salary(rating):
    """Зарплата скаута за сезон, млн €: от 0.05 (рейтинг 40) до ~2 (рейтинг 95)."""
    return round(0.05 * 1.07 ** (rating - 40), 2)

def scouting(s):
    """Качество скаутинга 0..1: лучший скаут + немного за каждого следующего."""
    sc = s.get("scouts") or []
    if not sc:
        return 0.0
    best = max(x["rating"] for x in sc)
    return clamp((best - 40) / 55.0 + 0.05 * (len(sc) - 1), 0.0, 1.0)

def pot_width(s):
    """Ширина вилки потенциала: без скаутов 10, с лучшими - 2."""
    return int(round(10 - 8 * scouting(s)))

class TransferWindow:
    """Трансферное окно тренера. Состояние - career.coach["window"] (сохраняется: окно можно закрыть и вернуться)."""
    def __init__(self, career):
        self.c = career
        self.s = career.coach

    @property
    def w(self):
        return self.s.get("window")

    def formation(self):
        return self.s.get("formation", squad_mod.DEFAULT_FORMATION)

    def rating(self, players=None):
        return squad_mod.team_rating(self.c, self.formation(), players)

    # ---------- открытие ----------
    def open(self, kind):
        """kind: summer (перед сезоном) или winter (в середине сезона)."""
        c, s, world = self.c, self.s, self.c.world
        cid = s["club"]
        if s.get("window") and s["window"]["kind"] == kind and s["window"]["year"] == c.year:
            return self.w                                          # окно уже открыто (вернулись на экран)
        s.setdefault("fin", {"spent": 0.0, "income": 0.0})
        academy, returned, left = [], [], []
        if kind == "summer" and s.get("budget_year") != c.year:
            salaries = sum(x["salary"] for x in s.get("scouts") or [])
            s["budget"] = round(s.get("budget", 0.0) + annual_budget(world, cid) + s.pop("prize", 0.0) - salaries, 2)
            if salaries:
                s["fin"]["spent"] += salaries
            s["budget_year"] = c.year
            returned, left = self._end_loans()
            for p in squad_mod.squad(c):                           # за лето все восстановились
                p["fit"] = 100.0
            # академия: если в составе мало игроков или нет нужной позиции - поднимаются свои воспитанники
            ab = s.get("academy_bonus") or {}
            academy = squad_mod.academy_fill(c, ab.get("bonus", 0.0) if ab.get("left", 0) > 0 else 0.0)
            if ab.get("left", 0) > 0:
                ab["left"] -= 1
        squad_mod.apply_to_world(c)
        squad_mod.refresh_mood(c)
        s["window"] = {"kind": kind, "year": c.year, "log": [], "start_ovr": round(self.rating(), 2),
                       "academy": [{"name": p["name"], "pos": p["pos"], "ovr": p["ovr"]} for p in academy],
                       "returned": returned, "loans_ended": left,
                       "cands": self._candidates(kind), "refused": getattr(self, "refused", 0), "youth": self._youth_options(kind), "offers": self._big_offers(kind),
                       "loan_offers": self._loan_offers() if kind == "summer" else [],
                       "scout_market": self._scout_market() if kind == "summer" else []}
        return self.w

    def _end_loans(self):
        """Конец сезона аренд: свои игроки возвращаются из аренды, чужие - в свои клубы. -> (вернулись, ушли)."""
        c, s = self.c, self.s
        cid, back, gone = s["club"], [], []
        for p in stars_mod.all_players(c.stars):
            if p.get("loan_from") and p.get("loan_until", 0) <= c.year:
                info = {"name": p["name"], "pos": p["pos"], "ovr": p["ovr"]}
                if p["loan_from"] == cid:                          # наш игрок вернулся
                    back.append(info)
                elif p["club"] == cid:                             # арендованный уходит обратно
                    gone.append(info)
                # аренды прошлых клубов тренера тоже заканчиваются - игроки возвращаются в свои клубы
                p["club"], p["squad"] = p["loan_from"], p["loan_from"] == cid
                for k in ("loan_from", "loan_until", "loan_min"):
                    p.pop(k, None)
        return back, gone

    def _refuses(self, p, team):
        """Откажется ли игрок перейти: сильный игрок не хочет в клуб без еврокубков, звезда - в клуб заметно слабее своего."""
        c, s, world, rng = self.c, self.s, self.c.world, self.c.rng
        diff = p["ovr"] - team
        if not s.get("euro") and diff >= 6 and rng.random() < min(0.85, 0.4 + 0.1 * (diff - 6)):
            return True
        club = p.get("club")
        return bool(club and club in world.club_league and world.team_ovr(club) > team + 3 and rng.random() < 0.5)

    def _candidates(self, kind):
        """Рынок: в основном игроки, которые усилят основу (чаще на слабые позиции схемы), по карману.
        Известные игроки мира, которые откажутся, в список не попадают (кроме пары дорогих «мечт»); молодых талантов -
        немного: арендованные и 1-2 «жемчужины» скаутов."""
        c, s, world, rng = self.c, self.s, self.c.world, self.c.rng
        cid = s["club"]
        team = self.rating()
        q = scouting(s)
        total = (12 + round(8 * q)) if kind == "summer" else (6 + round(4 * q))     # хорошие скауты - шире рынок
        budget = max(0.05, s.get("budget", 0.0))
        cost = lambda o, a, p: price(o, a, p) * BUY_PREMIUM
        slot_val = self._slot_values()
        need = lambda pos: slot_val.get(pos, team)                  # уровень основы на этой позиции
        # известные игроки мира, которые усилят основу на своей позиции
        pool = [p for p in stars_mod.all_players(c.stars) if p["club"] != cid and p["age"] <= 33 and p["ovr"] >= need(p["pos"]) + 1
                and p["ovr"] <= team + 12 and p["club"] in world.club_league and p["club"] not in stars_mod.PROTECTED
                and not p.get("loan_from")]
        key = lambda p: -(min(8.0, p["ovr"] - need(p["pos"])) + 2 * p.get("real", False) - 0.7 * max(0, p["age"] - 29) + rng.random() * 3)
        pool.sort(key=key)
        n_known = total // 2 + 1
        fit, dream, self.refused = [], [], 0
        for p in pool:
            affordable = cost(p["ovr"], p["age"], p["pot"]) <= budget * 1.1
            if affordable and len(fit) < n_known - 2:
                if self._refuses(p, team):
                    self.refused += 1                               # отказался обсуждать - на рынке его нет
                else:
                    fit.append(p)
            elif not affordable and len(dream) < 2:
                dream.append(p)
            if len(fit) >= n_known - 2 and len(dream) >= 2:
                break
        out = [self._cand(p["ovr"], p["age"], p["pot"], p["name"], p["nat"], p["pos"], p["club"], p["id"]) for p in fit]
        for p in dream:                                             # «мечта»: дорого, и может отказаться
            cd = self._cand(p["ovr"], p["age"], p["pot"], p["name"], p["nat"], p["pos"], p["club"], p["id"])
            cd["refuse"] = self._refuses(p, team)
            out.append(cd)
        # аренда: игроки клубов посильнее, которые сразу усилят основу, - на сезон за 10% стоимости
        if kind == "summer":
            lp = [p for p in stars_mod.all_players(c.stars) if p["club"] != cid and p["club"] in world.club_league and p["age"] <= 26
                  and need(p["pos"]) + 1 <= p["ovr"] <= team + 6 and world.team_ovr(p["club"]) > team + 2 and not p.get("loan_from")
                  and p["club"] not in stars_mod.PROTECTED and p not in fit]
            rng.shuffle(lp)
            for p in lp[:2]:
                cd = self._cand(p["ovr"], p["age"], p["pot"], p["name"], p["nat"], p["pos"], p["club"], p["id"])
                cd["loan"] = True; cd["price"] = round(max(0.02, price(p["ovr"], p["age"], p["pot"]) * LOAN_FEE), 2)
                out.append(cd)
        # «жемчужина»: недооценённый молодой талант почти уровня основы - находят хорошие скауты
        if rng.random() < 0.15 + 0.5 * q:
            for _ in range(1 + (q > 0.7)):
                age = rng.randint(18, 21)
                pos = rng.choice(list(slot_val)) if slot_val else "CM"
                o = round(need(pos) - rng.uniform(0, 3), 1)
                cd = self._cand(o, age, o + 3, self._gen_name(), self._gen_nat(), pos, None, None)
                cd["pot"] = round(o + rng.uniform(7, 14), 1); cd["gem"] = True    # цена - как за обычного, потенциал - выше
                out.append(cd)
        # сгенерированные игроки, которые усилят основу: чаще на слабые позиции, возраст в основном 22-30, по карману
        weak = self._weak_positions()
        expensive = 0
        while len(out) < total:
            pos = rng.choice(weak) if weak and rng.random() < 0.75 else rng.choice(list(slot_val) or ["CM"])
            base = need(pos)
            age = rng.choices([rng.randint(19, 21), rng.randint(22, 26), rng.randint(27, 30), rng.randint(31, 33)], weights=[1, 4, 4, 1])[0]
            o = base + rng.uniform(1.5, 5.5)
            pot = o + (rng.uniform(2, 6) if age <= 21 else rng.uniform(0.5, 2.5) if age <= 24 else 0)
            while cost(o, age, pot) > budget and o > base + 1.2:      # дорого - игрок попроще, но всё ещё сильнее основы
                o -= 0.5; pot = max(o, pot - 0.5)
            if cost(o, age, pot) > budget:
                if expensive >= 2 and age < 31:                       # не по карману - опытный игрок того же уровня дешевле
                    age = rng.randint(30, 32); pot = o
                expensive += 1
            out.append(self._cand(round(o, 1), age, pot, self._gen_name(), self._gen_nat(), pos, None, None))
        return out

    def _gen_nat(self):
        return self.c.rng.choices(list(stars_mod.REGEN_NATS), weights=list(stars_mod.REGEN_NATS.values()))[0]

    def _gen_name(self, nat=None):
        nat = nat or self._gen_nat()
        return stars_mod.gen_name(self.c.rng, nat, self.c.d.countries[nat]["conf"])

    def _slot_values(self):
        """Уровень основы на каждой позиции схемы (OVR игрока на этом месте, у повторяющихся позиций - самый слабый)."""
        out = {}
        for slot, _, v in squad_mod.best_xi(squad_mod.squad(self.c), self.formation()):
            out[slot] = min(out.get(slot, 99.0), v)
        return out

    def _weak_positions(self):
        """Позиции схемы, где основа слабее всего (кандидатов на них стоит показать чаще)."""
        xi = squad_mod.best_xi(squad_mod.squad(self.c), self.formation())
        vals = sorted(((v, slot) for slot, _, v in xi), key=lambda x: x[0])
        return [slot for _, slot in vals[:4]]

    def _cand(self, o, age, pot, name, nat, pos, club, pid):
        return {"name": name, "nat": nat, "pos": pos, "age": age, "ovr": round(o, 1), "pot": round(max(pot, o), 1), "club": club, "pid": pid,
                "price": round(price(o, age, pot) * BUY_PREMIUM, 2), "done": False}

    def _youth_options(self, kind):
        if kind != "summer":
            return []
        c, world, rng = self.c, self.c.world, self.c.rng
        a = annual_budget(world, self.s["club"])
        nat = c.d.leagues[world.club_league[self.s["club"]]]["country"]
        team = self.rating()
        pos = rng.choice(list(squad_mod.TEMPLATE)[1:])
        return [{"kind": "talent", "name": stars_mod.gen_name(rng, nat, c.d.countries[nat]["conf"]), "pos": pos, "age": 17,
                 "ovr": round(team - rng.uniform(7, 11), 1), "pot": round(team + rng.uniform(2, 9), 1),
                 "price": round(max(0.05, a * rng.uniform(0.04, 0.08)), 2), "done": False},
                {"kind": "academy", "price": round(max(0.05, a * 0.12), 2), "bonus": 4.0, "seasons": 3, "done": False}]

    def _big_offers(self, kind="summer"):
        """Предложения других клубов о покупке ваших игроков: {id игрока: {клуб, сумма}}.
        Летом обычно 2-4, зимой 0-2. Интерес - к игрокам, которые усилят покупателя: клубы своего уровня и чуть слабее
        (для топ-клуба - другие топ-клубы и богатые лиги для возрастных звёзд). Чаще хотят молодых с потенциалом и
        недовольных. Сумма всегда выше обычной продажи; чем богаче покупатель, тем щедрее."""
        c, s, world, rng = self.c, self.s, self.c.world, self.c.rng
        cid = s["club"]
        players = [p for p in squad_mod.squad(c) if not (p.get("loan_from") and p["loan_from"] != cid)]
        if not players:
            return {}
        n = rng.choice([1, 2, 2, 3, 3, 4]) if kind == "summer" else rng.choice([0, 0, 1, 1, 2])
        n += sum(1 for p in players if p.get("unhappy")) > 0
        clubs = [x for x in world.club_league if not c.d.clubs[x]["reserve"] and x != cid and x not in stars_mod.PROTECTED]
        ovr_of = {x: world.team_ovr(x) for x in clubs}
        my_score = world.score[cid]
        def interest(p):
            w = 1.0 + max(0.0, p["pot"] - p["ovr"]) * 0.15 + (2.0 if p.get("unhappy") else 0.0) + (0.5 if p["age"] <= 23 else 0.0)
            return w * (0.6 if p["age"] >= 31 else 1.0)
        out, pool = {}, players[:]
        for _ in range(n * 3):                                       # несколько попыток: не для каждого найдётся покупатель
            if len(out) >= n or not pool:
                break
            p = rng.choices(pool, weights=[interest(x) for x in pool])[0]
            pool.remove(p)
            buyers = [x for x in clubs if p["ovr"] - 5 <= ovr_of[x] <= p["ovr"] + 3]
            if p["age"] >= 29:                                       # богатые лиги охотно берут опытных
                buyers += [x for x in clubs if world.d.leagues[world.club_league[x]]["country"] in ("KSA", "USA", "QAT", "UAE")
                           and ovr_of[x] >= p["ovr"] - 10 and x not in buyers]
            if not buyers:
                continue
            club = rng.choices(buyers, weights=[max(1.0, world.score[x]) ** 1.5 for x in buyers])[0]
            rich = clamp((world.score[club] - my_score) / 30.0, 0.0, 1.0)
            mult = 1.0 + rng.uniform(0.0, 0.35) + 0.25 * rich - (0.1 if p.get("unhappy") else 0.0)   # недовольного продают дешевле
            out[p["id"]] = {"club": club, "fee": round(price(p["ovr"], p["age"], p["pot"]) * max(0.95, mult), 2)}
        return out

    def _loan_offers(self):
        """Клубы послабее просят в аренду ваших молодых и запасных: [{игрок, клуб, плата}]."""
        c, s, world, rng = self.c, self.s, self.c.world, self.c.rng
        xi = {p["id"] for _, p, _ in squad_mod.current_xi(c) if p}
        cands = [p for p in squad_mod.squad(c) if p["id"] not in xi and (p["age"] <= 23 or p.get("unhappy"))]
        rng.shuffle(cands)
        out = []
        for p in cands[:3]:
            club = self._loan_destination(p)
            if club:
                out.append({"pid": p["id"], "club": club, "fee": round(price(p["ovr"], p["age"], p["pot"]) * rng.uniform(0.0, 0.06), 2),
                            "done": False})
        return out

    def _loan_destination(self, p):
        c, world, rng = self.c, self.c.world, self.c.rng
        cands = [x for x in world.club_league if not c.d.clubs[x]["reserve"] and x != self.s["club"] and x not in stars_mod.PROTECTED
                 and p["ovr"] - 4 <= world.team_ovr(x) <= p["ovr"] + 1]
        return rng.choice(cands) if cands else None

    def _scout_market(self):
        """Скауты, которых можно нанять этим летом: дешёвый, средний и сильный."""
        c, rng = self.c, self.c.rng
        out = []
        for lo, hi in ((40, 58), (58, 76), (74, 95)):
            r = round(rng.uniform(lo, hi))
            nat = rng.choices(list(stars_mod.REGEN_NATS), weights=list(stars_mod.REGEN_NATS.values()))[0]
            out.append({"name": stars_mod.gen_name(rng, nat, c.d.countries[nat]["conf"]), "rating": r, "stars": scout_stars(r),
                        "salary": scout_salary(r), "done": False})
        return out

    # ---------- оценки для экрана ----------
    def gain(self, cd):
        """На сколько изменится сила основы, если купить (или арендовать) кандидата."""
        players = squad_mod.squad(self.c)
        tmp = {"id": "_new", "pos": cd["pos"], "ovr": cd["ovr"]}
        return round(self.rating(players + [tmp]) - self.rating(players), 2)

    def loss(self, p):
        players = squad_mod.squad(self.c)
        return round(self.rating(players) - self.rating([x for x in players if x["id"] != p["id"]]), 2)

    def sale_fee(self, p):
        off = (self.w or {}).get("offers", {}).get(p["id"])
        return off["fee"] if off else round(price(p["ovr"], p["age"], p["pot"]) * 0.9, 2)

    def squad_full(self):
        return len(squad_mod.squad(self.c)) >= squad_mod.MAX_SQUAD

    # ---------- сделки ----------
    def buy(self, i):
        c, s = self.c, self.s
        win, cid = self.w, s["club"]
        cd = win["cands"][i]
        if cd["done"] or cd.get("refuse") or cd["price"] > s["budget"] + 1e-9 or self.squad_full():
            return False
        before = self.rating()
        p = stars_mod.find(c.stars, cd["pid"]) if cd["pid"] else None
        if p and p["club"] == cd["club"]:
            if cd.get("loan"):                                    # аренда на сезон
                p["loan_from"], p["loan_until"] = p["club"], c.year + 1
            p["club"] = cid                                       # реальный / известный игрок переходит к вам
        else:
            p = stars_mod.add_other(c.stars, cd["name"], cd["nat"], cd["pos"], cd["age"], cd["ovr"], cd["pot"], cid)
        # новичок приходит здоровым и свежим (старые травмы и настроение из прошлого клуба не переносятся)
        p.update(squad=True, fresh=True, inj=0, inj_kind=None, fit=100.0, unhappy=False, min=0.0)
        s["budget"] = round(s["budget"] - cd["price"], 2); s["fin"]["spent"] += cd["price"]
        cd["done"] = True
        squad_mod.apply_to_world(c)
        win["log"].append({"t": "loan_in" if cd.get("loan") else "buy", "name": cd["name"], "ovr": cd["ovr"], "fee": cd["price"],
                           "d": round(self.rating() - before, 2)})
        return True

    def sell(self, pid):
        c, s, world, rng = self.c, self.s, self.c.world, self.c.rng
        win, cid = self.w, s["club"]
        p = stars_mod.find(c.stars, pid)
        if not p or p["club"] != cid or p.get("loan_from"):         # арендованного продать нельзя
            return False
        before = self.rating()
        fee = self.sale_fee(p)
        off = win.get("offers", {}).pop(pid, None)
        if off:
            p["club"] = off["club"]
        else:
            buyers = [x for x in world.club_league if not c.d.clubs[x]["reserve"] and x != cid and x not in stars_mod.PROTECTED
                      and abs(world.team_ovr(x) - p["ovr"]) <= 4]
            p["club"] = rng.choice(buyers) if buyers else rng.choice(list(world.club_league))
        p.update(squad=False, unhappy=False, inj=0, inj_kind=None, fit=100.0)
        s["budget"] = round(s["budget"] + fee, 2); s["fin"]["income"] += fee
        squad_mod.apply_to_world(c)
        win["log"].append({"t": "sell", "name": p["name"], "ovr": p["ovr"], "fee": fee, "d": round(self.rating() - before, 2),
                           "to": p["club"]})
        return True

    def loan_out(self, pid, club=None, fee=0.0):
        """Отдать своего игрока в аренду на сезон: там он будет играть (и расти), летом вернётся."""
        c, s, world = self.c, self.s, self.c.world
        win, cid = self.w, s["club"]
        p = stars_mod.find(c.stars, pid)
        if not p or p["club"] != cid or p.get("loan_from"):
            return False
        club = club or self._loan_destination(p)
        if not club:
            return False
        before = self.rating()
        p["club"], p["loan_from"], p["loan_until"] = club, cid, c.year + 1
        p["loan_min"] = 0.85 if p["ovr"] >= world.team_ovr(club) - 1 else 0.5      # сколько будет играть в аренде
        p["unhappy"] = False
        for o in win.get("loan_offers", []):
            if o["pid"] == pid:
                o["done"] = True
        if fee:
            s["budget"] = round(s["budget"] + fee, 2); s["fin"]["income"] += fee
        squad_mod.apply_to_world(c)
        win["log"].append({"t": "loan_out", "name": p["name"], "ovr": p["ovr"], "fee": fee, "d": round(self.rating() - before, 2),
                           "to": club})
        return True

    def accept_loan_offer(self, i):
        o = self.w["loan_offers"][i]
        return not o["done"] and self.loan_out(o["pid"], o["club"], o["fee"])

    def youth(self, i):
        c, s = self.c, self.s
        win, cid = self.w, s["club"]
        y = win["youth"][i]
        if y["done"] or y["price"] > s["budget"] + 1e-9 or (y["kind"] == "talent" and self.squad_full()):
            return False
        s["budget"] = round(s["budget"] - y["price"], 2); s["fin"]["spent"] += y["price"]
        y["done"] = True
        if y["kind"] == "talent":
            p = stars_mod.add_other(c.stars, y["name"], c.d.leagues[c.world.club_league[cid]]["country"], y["pos"], 17, y["ovr"], y["pot"], cid)
            p["squad"] = True
        else:
            s["academy_bonus"] = {"bonus": y["bonus"], "left": y["seasons"]}
        win["log"].append({"t": y["kind"], "name": y.get("name"), "fee": y["price"], "d": 0.0})
        return True

    def hire_scout(self, i):
        s = self.s
        sc = self.w["scout_market"][i]
        if sc["done"] or len(s.get("scouts") or []) >= MAX_SCOUTS or sc["salary"] > s["budget"] + 1e-9:
            return False
        s.setdefault("scouts", []).append({k: sc[k] for k in ("name", "rating", "stars", "salary")})
        s["budget"] = round(s["budget"] - sc["salary"], 2); s["fin"]["spent"] += sc["salary"]   # зарплата за этот сезон
        sc["done"] = True
        self.w["log"].append({"t": "scout", "name": sc["name"], "fee": sc["salary"], "d": 0.0})
        return True

    def fire_scout(self, i):
        sc = self.s.get("scouts") or []
        if 0 <= i < len(sc):
            sc.pop(i)
            return True
        return False

    def close(self):
        """Окно закрыто: сделки переходят в запись сезона."""
        win = self.w
        if win:
            self.s.setdefault("season_moves", []).extend(win["log"])
        self.s["window"] = None
        squad_mod.apply_to_world(self.c)
