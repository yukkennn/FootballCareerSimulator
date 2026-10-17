"""Массовый прогон карьер без интерфейса: проверка на ошибки и баланс. python tests/balance.py [N]"""
import sys, random, collections, statistics, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from game.data import GameData
from game.career import Career, RETIRE_AGE
from game.positions import POSITIONS

def auto_pick(c):
    """Простая стратегия игрока: уходит в самый сильный клуб, где попадает в основу; иначе остаётся, если играет."""
    sc = lambda i: c.world.score[c.offers[i]["club"]]
    ok = [i for i, o in enumerate(c.offers) if o["gap"] >= -3 and o["kind"] != "loan"]
    best = max(ok, key=sc) if ok else None
    if (c.can_stay and c.offer_reason != "academy_end" and c.player.ovr() >= c.world.team_ovr(c.club_id) - 2
            and (best is None or sc(best) <= c.world.score[c.club_id] + 4)):
        return "stay"
    pool = ok or list(range(len(c.offers)))
    return max(pool, key=sc)

def run(n=300, seed0=1000):
    d = GameData()
    nats = d.countries_with_clubs + ["BRA", "NGA", "JPN", "USA", "ARG", "MAR", "KAZ"]
    stats = collections.defaultdict(list)
    t0 = time.time()
    errs = 0
    for k in range(n):
        rng = random.Random(seed0 + k)
        pos = rng.choice(POSITIONS)
        c = Career(d, "T", rng.choice(nats), pos, rng.choice([1, 2, 3]), seed=seed0 + k)
        c.choose_academy(rng.choice(c.academy_ids))
        guard = 0
        while c.status != "retired" and guard < 60:
            guard += 1
            c.play_period()
            if c.status == "offers":
                c.accept(auto_pick(c))
        if c.status != "retired":
            errs += 1; continue
        r = c.report()
        stats["peak"].append(r["peak_ovr"]); stats["end_age"].append(c.player.age)
        stats["goals_" + ("ST" if pos in ("ST", "CF") else "other")].append(r["totals"]["goals"])
        stats["games"].append(r["totals"]["games"]); stats["trophies"].append(len(c.trophies))
        stats["ballon"].append(r["award_counts"].get("ballon_dor", 0))
        stats["clubs"].append(len(r["clubs"])); stats["caps"].append(r["totals"]["caps"])
        stats["wc"].append(sum(1 for t in c.trophies if t["code"] == "WC"))
        stats["age18"].append(next((s["ovr"] for s in c.seasons if s["age"] == 18), 0))
        stats["age15"].append(c.seasons[0]["ovr"])
        stats["age25"].append(next((s["ovr"] for s in c.seasons if s["age"] == 25), 0))
        stats["reason"].append(c.retire_reason)
        for s in c.seasons:
            if s["youth"] or s["games"] < 25:
                continue
            band = "90+" if s["ovr"] >= 90 else "85-89" if s["ovr"] >= 85 else "80-84" if s["ovr"] >= 80 else None
            if band and pos in ("ST", "CF"):
                stats["st_gpg_" + band].append(s["goals"] / s["games"])
                stats["st_goals_" + band].append(s["goals"])
            if band and pos in ("LW", "RW", "CAM"):
                stats["att_goals_" + band].append(s["goals"]); stats["att_ast_" + band].append(s["assists"])
            for a in s["awards"]:
                stats["aw_" + a].append((s["ovr"], s["goals"] + s["assists"], len(s["trophies"]), s.get("rating")))
            if s["ovr"] >= 90:
                stats["s90"].append(1 if "ballon_dor" in s["awards"] else 0)
    n_ok = len(stats["peak"])
    pk = stats["peak"]
    print(f"карьер: {n}, завершено: {n_ok}, зависло: {errs}, время {time.time()-t0:.1f}с")
    print(f"возраст завершения: мин {min(stats['end_age'])}, средний {statistics.mean(stats['end_age']):.1f}, макс {max(stats['end_age'])} (должен быть {RETIRE_AGE})")
    print(f"OVR в 15 лет: ср {statistics.mean(stats['age15']):.0f} (мин {min(stats['age15'])}, макс {max(stats['age15'])}) | в 18: ср {statistics.mean(stats['age18']):.0f} | в 25: ср {statistics.mean(x for x in stats['age25'] if x):.0f}")
    print(f"пик OVR: средний {statistics.mean(pk):.1f}, медиана {statistics.median(pk)}; >=85: {sum(p>=85 for p in pk)/n_ok:.1%}, >=90: {sum(p>=90 for p in pk)/n_ok:.1%}, >=95: {sum(p>=95 for p in pk)/n_ok:.1%}, 99: {sum(p>=99 for p in pk)/n_ok:.1%}")
    print(f"матчей за карьеру: ср {statistics.mean(stats['games']):.0f}; клубов: ср {statistics.mean(stats['clubs']):.1f}; трофеев: ср {statistics.mean(stats['trophies']):.1f}; матчей за сборную: ср {statistics.mean(stats['caps']):.0f}")
    print(f"голы нападающих (ST/CF) за карьеру: ср {statistics.mean(stats['goals_ST']):.0f}, макс {max(stats['goals_ST'])} | остальные: ср {statistics.mean(stats['goals_other']):.0f}, макс {max(stats['goals_other'])}")
    for band in ("80-84", "85-89", "90+"):
        g = stats.get("st_goals_" + band)
        if g:
            print(f"   ST/CF с OVR {band}: голов за сезон ср {statistics.mean(g):.1f} (за матч {statistics.mean(stats['st_gpg_' + band]):.2f}), сезонов {len(g)}")
        g = stats.get("att_goals_" + band)
        if g:
            print(f"   LW/RW/CAM с OVR {band}: голов {statistics.mean(g):.1f}, передач {statistics.mean(stats['att_ast_' + band]):.1f}, сезонов {len(g)}")
    print(f"Золотой мяч получили: {sum(b>0 for b in stats['ballon'])/n_ok:.1%} игроков; сезонов с OVR 90+: {len(stats['s90'])}, из них с Золотым мячом: {sum(stats['s90'])}")
    for a in ("ballon_dor", "world_xi", "league_poty", "league_xi", "golden_boot", "best_young"):
        v = stats.get("aw_" + a, [])
        if v:
            print(f"   {a}: {len(v)} раз; в среднем OVR {statistics.mean(x[0] for x in v):.0f}, Г+П {statistics.mean(x[1] for x in v):.0f}, "
                  f"трофеев за сезон {statistics.mean(x[2] for x in v):.1f}, оценка {statistics.mean(x[3] for x in v if x[3]):.2f}; "
                  f"худший Г+П {min(x[1] for x in v)}")
    print(f"чемпионат мира выиграли: {sum(w>0 for w in stats['wc'])/n_ok:.1%}")
    print("причины завершения:", dict(collections.Counter(stats["reason"])))
    return stats

if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 300)
