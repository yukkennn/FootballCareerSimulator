"""Тексты для отчётов: названия трофеев, наград, стадий, форматы денег."""
from .i18n import tr, LANG
from . import i18n

def money(m):
    if m <= 0:
        return tr("offers.free")
    v = f"{m:.2f}".rstrip("0").rstrip(".") if m < 10 else f"{m:.1f}".rstrip("0").rstrip(".")
    if i18n.LANG == "ru":
        v = v.replace(".", ",")
    return tr("money.m", v=v)

def trophy_name(t):
    return t["name_ru"] if i18n.LANG == "ru" else t["name_en"]

def stage(code):
    return tr("stage." + code)

def stars_text(x):
    return "★" * int(x) + ("½" if x - int(x) >= 0.5 else "")

def event_text(e):
    if e["t"] == "injury":
        return tr("event.injury_serious" if e["serious"] else "event.injury", w=e["weeks"])
    return tr("event." + e["t"])

_SHORT = {"league": ("Чемпион", "Champion"), "title2": ("Победа в лиге", "League win"), "cup": ("Кубок", "Cup"), "league_cup": ("Кубок лиги", "League Cup"),
          "supercup": ("Суперкубок", "Super Cup"), "UCL": ("ЛЧ", "UCL"), "UEL": ("ЛЕ", "UEL"), "UECL": ("ЛК", "UECL"), "USC": ("Суперкубок УЕФА", "UEFA Super Cup"),
          "WC": ("ЧМ", "World Cup"), "EURO": ("ЧЕ", "EURO"), "CA": ("Копа Америка", "Copa América"), "AFCON": ("Кубок Африки", "AFCON"),
          "ASIAN": ("Кубок Азии", "Asian Cup"), "GOLD": ("Золотой кубок", "Gold Cup"), "OFCNC": ("Кубок ОФК", "OFC Cup"), "youth_league": ("Мол. лига", "Youth League"),
          "LIB": ("Либертадорес", "Libertadores"), "SUD": ("Судамерикана", "Sudamericana"), "ACLE": ("ЛЧ АФК", "AFC CL"), "CCC": ("Кубок КОНКАКАФ", "CONCACAF CC"), "UNL": ("Лига наций", "Nations League")}

def award_name(code, rank=None):
    """Название личной награды; для места в топ-30 Золотого мяча - с номером места."""
    if code == "ballon_top30" and rank:
        return tr("award.ballon_place", r=rank)
    return tr("award." + code)

def season_award_names(s):
    """Названия наград сезона (запись сезона из career.seasons)."""
    rank = (s.get("ballon") or {}).get("rank")
    names = [award_name(a, rank) for a in s["awards"]]
    if rank and rank > 3 and "ballon_top30" not in s["awards"]:     # сезоны из сохранений, где место в топ-30 ещё не записывалось
        names.append(award_name("ballon_top30", rank))
    return names

def chronicle_text(e, d):
    """Строка летописи карьеры (событие из Career._chronicle)."""
    k = e["k"]
    club = lambda: d.clubs[e["club"]]["name"] if e.get("club") in d.clubs else ""
    if k in ("debut", "first_goal"):
        return tr("chron." + k, club=club(), age=e.get("age", ""))
    if k == "nat_debut":
        return tr("chron.nat_debut", age=e["age"])
    if k in ("goals_mark", "games_mark", "caps_mark", "best_goals"):
        return tr("chron." + k, n=e["n"])
    if k in ("first_trophy", "big_trophy"):
        return tr("chron." + k, name=e["name_ru"] if i18n.LANG == "ru" else e["name_en"])
    if k == "award":
        return tr("chron.award", name=award_name(e["code"]))
    if k == "injury":
        return tr("chron.injury", w=e["weeks"])
    if k in ("move", "record_move"):
        return tr("chron." + k, club=club(), fee=money(e["fee"]))
    if k in ("promoted", "relegated", "captain", "loan"):
        return tr("chron." + k, club=club())
    return tr("chron." + k)

def short_trophy(code):
    ru, en = _SHORT.get(code, (code, code))
    return ru if i18n.LANG == "ru" else en

def _plural(n, ru, en):
    if i18n.LANG == "ru":
        n10, n100 = n % 10, n % 100
        f = ru[0] if (n10 == 1 and n100 != 11) else ru[1] if (2 <= n10 <= 4 and not 12 <= n100 <= 14) else ru[2]
    else:
        f = en[0] if n == 1 else en[1]
    return f"{n} {f}"

def intl_line(caps, goals, assists):
    pre = "Сборная: " if i18n.LANG == "ru" else "National team: "
    return pre + ", ".join([_plural(caps, ("матч", "матча", "матчей"), ("app", "apps")),
                            _plural(goals, ("гол", "гола", "голов"), ("goal", "goals")),
                            _plural(assists, ("передача", "передачи", "передач"), ("assist", "assists"))])

# ---------- результаты турниров ----------
def lang_name(obj):
    return obj["name_ru"] if i18n.LANG == "ru" else obj["name_en"]

def group_letter(i):
    return chr(64 + i) if 1 <= i <= 26 else str(i)

def score_text(sc):
    if not sc:
        return ""
    t = f"{sc['g'][0]}:{sc['g'][1]}"
    if sc.get("legs"):
        t += " (" + ", ".join(f"{a}:{b}" for a, b in sc["legs"]) + ")"
    if sc.get("et"):
        t += " " + tr("score.et")
    if sc.get("p"):
        t += ", " + tr("score.pens", a=sc["p"][0], b=sc["p"][1])
    return t

def club_result(c, d):
    """Итог клуба в турнире: место в лиге, стадия вылета с соперником и счётом, победа."""
    r, code = c["result"], c["code"]
    if code in ("league", "youth"):
        t = tr("res.league", r=r["rank"], n=r["n"], pts=r["pts"])
        if "w" in r:
            t += tr("res.wdl", w=r["w"], d=r["d"], l=r["l"])
        return t
    st = r.get("stage")
    if st == "W":
        if c.get("senior") and c["games"] <= 3 and code in ("cup", "league_cup"):
            return tr("res.team_won_cup")
        return tr("res.won", vs=d.clubs[r["vs"]]["name"], score=score_text(r["score"])) if r.get("vs") else stage("W")
    if st == "LP" and "lp_rank" in r:
        return tr("res.lp_out", r=r["lp_rank"], n=r["lp_n"])
    if st == "GS" and "gpos" in r:
        return tr("res.gs_out", p=r["gpos"])
    if r.get("vs"):
        return tr("res.lost", stage=stage(st or "early").capitalize(), vs=d.clubs[r["vs"]]["name"], score=score_text(r["score"]))
    return stage(st or "early")

def nat_comp_name(e, d):
    """Название турнира сборной для таблицы: «Отбор: Чемпионат мира 2030», «Лига наций УЕФА», «Товарищеские матчи»."""
    k, code = e["kind"], e["code"]
    if k == "friendly":
        return tr("nat.friendly")
    if k == "unl":
        return tr("nat.unl")
    full = f"{lang_name(d.comps[code])} {e['year']}"
    return tr("nat.qual", comp=full) if k == "qual" else full

def nat_result(e, d):
    """Итог сборной: место в отборочной группе, стыковые матчи, стадия на турнире с соперником и счётом."""
    k, info = e["kind"], e["info"]
    nat = lambda c: d.country_name(c, i18n.LANG)
    if k == "friendly":
        return ""
    if k == "host":
        return tr("nat.host")
    if k == "notinv":
        return tr("nat.notinv")
    if k == "qual":
        t = tr("nat.qual_group", p=info["pos"], g=group_letter(info["group"]), pts=info["pts"])
        if info.get("po"):
            po = info["po"]
            t += tr("nat.po_won" if po["won"] else "nat.po_lost", vs=nat(po["vs"]), score=score_text(po["score"]))
        elif info.get("ic"):
            ic = info["ic"]
            t += tr("nat.ic_won" if ic["won"] else "nat.ic_lost", vs=nat(ic["vs"]), score=score_text(ic["score"]))
        else:
            t += tr("nat.qualified" if info["res"] == "Q" else "nat.not_qualified")
        return t
    if k == "unl":
        t = tr("nat.unl_group", L=info["league"], g=info["group"], p=info["pos"], pts=info["pts"])  # в Лиге наций группы нумеруются
        f = info.get("finals")
        if f:
            t += tr("nat.unl_fin_won", vs=nat(f["vs"]), score=score_text(f["score"])) if f["stage"] == "W" else \
                 tr("nat.unl_fin_lost", stage=stage(f["stage"]), vs=nat(f["vs"]), score=score_text(f["score"]))
        elif info["league"] == "A" and info["pos"] == 1:
            t += tr("nat.unl_no_finals")
        mv = info.get("move")
        if mv:
            t += tr("nat.unl_up" if mv["dir"] == "up" else "nat.unl_down", L=mv["to"])
        return t
    st = info.get("stage")
    if st == "W":
        return tr("res.won", vs=nat(info["vs"]), score=score_text(info["score"]))
    if st == "GS":
        return tr("nat.final_gs", p=info.get("gpos", "?"), pts=info.get("gpts", 0))
    return tr("res.lost", stage=stage(st).capitalize(), vs=nat(info["vs"]), score=score_text(info["score"]))

def group_line(e, d):
    info = e.get("info") or {}
    if e["kind"] in ("qual", "unl") and info.get("table"):
        return tr("nat.group_table", t=" · ".join(f"{i}. {d.country_name(c, i18n.LANG)}" for i, c in enumerate(info["table"], 1)))
    return ""
