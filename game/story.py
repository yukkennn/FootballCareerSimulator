"""Дневник сезона: факты сезона из игры -> задание для нейросети (Gemini, Claude) -> текст дневника от лица игрока.

Нейросеть только пишет текст: всё, что можно проверить (счёт, место, трофеи, голы), берётся из игры и передаётся в задании.
Голы и передачи игрока раскладываются по матчам так, чтобы сумма совпадала со статистикой сезона (детерминированно:
та же карьера и тот же сезон дают ту же раскладку). Личную жизнь (семья, друзья, отношения) придумывает нейросеть, а чтобы
она не противоречила прошлым сезонам, в конце каждого дневника она пишет блок «ПАМЯТЬ», и он передаётся в следующие задания.
"""
import random, re
from . import i18n
from . import stars as stars_mod
from .text import trophy_name, award_name, club_result, lang_name, nat_comp_name, nat_result, score_text, chronicle_text, money, stage

MEMORY_RU, MEMORY_EN = "ПАМЯТЬ:", "MEMORY:"
# страны, где сезон идёт в пределах календарного года (весна-осень)
CALENDAR_YEAR = {"USA", "BRA", "ARG", "COL", "CHI", "PER", "ECU", "URU", "PAR", "BOL", "VEN", "KOR", "CHN", "KAZ", "ISL", "IRL",
                 "NOR", "SWE", "FIN", "LVA", "LTU", "EST", "FRO"}
MONTHS_RU = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def _ru():
    return i18n.LANG == "ru"

def T(ru, en):
    return ru if _ru() else en

def club_name(d, cid):
    c = d.clubs.get(cid)
    return c["name"] if c else str(cid)

def _distribute(rng, n, caps):
    """n событий по матчам с ёмкостью caps (сколько максимум в матче) - вес по ёмкости. -> [кол-во по матчам]."""
    got = [0] * len(caps)
    for _ in range(n):
        free = [i for i, c in enumerate(caps) if got[i] < c]
        if not free:
            break
        i = rng.choices(free, weights=[caps[j] - got[j] for j in free])[0]
        got[i] += 1
    return got

def _month(md, total, calendar_year):
    """Номер тура -> (месяц 1..12, сдвиг года 0/1) примерно по календарю лиги."""
    if calendar_year:                     # февраль - ноябрь
        m = 2 + int(9.99 * (md - 0.5) / max(1, total))
        return m, 0
    m = 8 + int(10 * (md - 0.5) / max(1, total))   # август - май
    return (m - 1) % 12 + 1, (1 if m > 12 else 0)

def league_matches(c, d, s, rng, coach=False):
    """Матчи лиги в порядке туров с участием игрока, его голами и передачами. -> (строки, сводка)."""
    ms = list(s.get("matches") or [])
    if not ms:
        return [], {}
    # порядок туров: внутри каждой половины сезона - случайный, но постоянный для этой карьеры и сезона
    first = [m for m in ms if m[4] == 1]; second = [m for m in ms if m[4] == 2]
    rng.shuffle(first); rng.shuffle(second)
    order = first + second
    n = len(order)
    lg = next((x for x in s.get("comps", []) if x["code"] == "league"), None)
    games = 0 if coach else min(n, lg["games"] if lg else 0)
    goals, assists = (lg["goals"], lg["assists"]) if lg else (0, 0)
    # пропуск по травме - подряд идущие туры
    out = set()
    inj = next((e for e in s.get("events", []) if e["t"] == "injury"), None)
    if inj:
        k = min(n - games, max(1, round(inj["weeks"] * n / 40)))
        if k > 0:
            start = rng.randint(0, max(0, n - k))
            out = set(range(start, start + k))
    pool = [i for i in range(n) if i not in out]
    played = set(rng.sample(pool, min(games, len(pool)))) if games else set()
    if len(played) < games:                                   # травма оказалась короче, чем пропущенных матчей
        played |= set(rng.sample(sorted(out), min(games - len(played), len(out))))
        out -= played
    idx = sorted(played)
    g = _distribute(rng, goals, [order[i][2] for i in idx])
    a = _distribute(rng, assists, [order[i][2] - g[j] for j, i in enumerate(idx)])
    mine = {i: (g[j], a[j]) for j, i in enumerate(idx)}
    cal = d.leagues[s["league"]]["country"] in CALENDAR_YEAR if s.get("league") in d.leagues else False
    lines = []
    for i, (opp, home, gf, ga, half) in enumerate(order):
        mon, dy = _month(i + 1, n, cal)
        res = T("победа", "win") if gf > ga else T("поражение", "loss") if gf < ga else T("ничья", "draw")
        where = T("дома", "home") if home else T("в гостях", "away")
        if coach:
            me = ""
        elif i in mine:
            pg, pa = mine[i]
            me = T("играл", "played") + (f", {T('голы', 'goals')}: {pg}" if pg else "") + (f", {T('передачи', 'assists')}: {pa}" if pa else "")
        elif i in out:
            me = T("пропустил (травма)", "missed (injury)")
        else:
            me = T("не играл", "did not play")
        month = (MONTHS_RU if _ru() else MONTHS_EN)[mon - 1]
        lines.append(f"{T('Тур', 'Matchday')} {i + 1} ({month}{', ' + T('след. год', 'next year') if dy else ''}), {where}: "
                     f"{club_name(d, opp)}, {gf}:{ga} ({res})" + (f" - {me}" if me else ""))
    big_win = max(order, key=lambda m: (m[2] - m[3], m[2]))
    big_loss = min(order, key=lambda m: (m[2] - m[3], -m[3]))
    summ = {"best": f"{club_name(d, big_win[0])} {big_win[2]}:{big_win[3]}", "worst": f"{club_name(d, big_loss[0])} {big_loss[2]}:{big_loss[3]}"}
    return lines, summ

def cup_lines(c, d, s, rng, coach=False):
    """Кубки и еврокубки: раунды с соперниками и счётом, голы игрока разложены по матчам."""
    out = []
    for x in s.get("comps", []):
        if x["code"] in ("league", "youth"):
            continue
        r = x["result"]
        path = list(r.get("path") or [])
        if not path and r.get("vs"):
            path = [{"stage": r.get("stage") if r.get("stage") != "W" else "F", "vs": r["vs"], "score": r.get("score"), "won": r.get("won", r.get("stage") == "W")}]
        head = f"{lang_name(x)}: {club_result(x, d)}" + ("" if coach else f". {T('Игрок', 'Player')}: {x['games']} {T('матчей', 'apps')}, {x['goals']} {T('голов', 'goals')}, {x['assists']} {T('передач', 'assists')}")
        if x.get("senior"):
            head += T(" (вызван в основную команду)", " (called up to the first team)")
        out.append(head)
        if r.get("lp_rank"):
            out.append(f"  {T('Общий этап', 'League phase')}: {r['lp_rank']}/{r['lp_n']}, {r.get('lp_pts', '?')} {T('очк.', 'pts')}")
        if r.get("gpos"):
            out.append(f"  {T('Группа', 'Group')}: {r['gpos']}-{T('е место', ' place')}")
        caps = [max(1, (p.get("score") or {}).get("g", [1, 0])[0]) for p in path]
        g = _distribute(rng, x["goals"], caps) if path and not coach else []
        for j, p in enumerate(path):
            mark = T("прошли", "through") if p["won"] else T("вылетели", "out")
            if p["won"] and p["stage"] == "F":
                mark = T("ТРОФЕЙ", "TROPHY")
            extra = f", {T('гол игрока', 'player scored')} x{g[j]}" if g and g[j] else ""
            out.append(f"  {stage(p['stage']).capitalize()}: {club_name(d, p['vs'])}, {score_text(p.get('score'))} - {mark}{extra}")
    return out

def nat_lines(c, d, s):
    intl = s.get("intl") or {}
    out = []
    if not s.get("nat_comps"):
        return out
    out.append(T("Вызывали в сборную: ", "Called up: ") + (T("да", "yes") if intl.get("called") else T("нет", "no")) +
               (f"; {intl.get('caps', 0)} {T('матчей', 'apps')}, {intl.get('goals', 0)} {T('голов', 'goals')}, {intl.get('assists', 0)} {T('передач', 'assists')}" if intl.get("called") else ""))
    for e in s["nat_comps"]:
        if e["kind"] == "friendly" and not e["games"]:
            continue
        res = nat_result(e, d)
        out.append(f"  {nat_comp_name(e, d)}{': ' + res if res else ''}" + (f" ({T('игрок', 'player')}: {e['games']} {T('матчей', 'apps')}, {e['goals']} {T('голов', 'goals')})" if intl.get("called") else ""))
    return out

def table_lines(c, d, s):
    lg = next((x for x in s.get("comps", []) if x["code"] in ("league", "youth") and x.get("table")), None)
    if not lg:
        return []
    out = []
    for i, (cid, w, dr, l, gf, ga, pts) in enumerate(lg["table"], 1):
        if i <= 4 or cid == s["club"] or i > len(lg["table"]) - 2:
            out.append(f"  {i}. {club_name(d, cid)} - {pts} {T('очк.', 'pts')} ({w}-{dr}-{l}, {gf}:{ga})" + (T("  <- мы", "  <- us") if cid == s["club"] else ""))
    return out

def facts(c, d, idx):
    """Все факты сезона текстом (на языке игры)."""
    s = c.seasons[idx]
    rng = random.Random(f"{c.id}-{s['year']}-story")
    p = c.player
    cl = d.clubs[s["club"]]
    L = []
    add = L.append
    add(f"{T('Сезон', 'Season')}: {s['season']}")
    add(f"{T('Игрок', 'Player')}: {c.name}, {s['age']} {T('лет', 'years old')}, {T('позиция', 'position')} {c.pos} ({i18n.tr('pos.' + c.pos)}), "
        f"{d.country_name(c.nat, i18n.LANG)}, {p.height} {T('см', 'cm')}, {i18n.tr('foot_short.' + p.foot)}")
    add(f"{T('Рейтинг игрока (OVR)', 'Player rating (OVR)')}: {s['ovr']} -> {s['ovr_end']}" +
        (f"; {T('средняя оценка за сезон', 'average match rating')} {s['rating']:.2f}" if s.get("rating") else ""))
    where = ", ".join(x for x in (cl.get("city"), cl.get("stadium") and f"{T('стадион', 'stadium')} {cl['stadium']}") if x)
    add(f"{T('Клуб', 'Club')}: {cl['name']}" + (f" ({where})" if where else "") + f", {s['league_name']} ({d.country_name(s['league_country'], i18n.LANG)}), "
        f"{T('звёзды клуба', 'club stars')} {s.get('club_stars', '?')}" + (T(", игрок в аренде", ", player on loan") if s.get("loan") else "") +
        (T(", игрок - капитан команды", ", player is the captain") if s.get("captain") else ""))
    if s["youth"]:
        add(T("Игрок ещё в академии: играет за молодёжную команду U-18, в основе - только если вызывают.",
              "Still in the academy: plays for the U-18 side, first team only when called up."))
    moved = [t for t in c.transfers if t["season"] == s["season"] and t["to"] == s["club"]]
    for t in moved:
        frm = club_name(d, t["from"]) if t["from"] else "-"
        add(f"{T('Переход перед сезоном', 'Pre-season move')}: {frm} -> {club_name(d, t['to'])} ({i18n.tr('type.' + t['type'])}"
            + (f", {money(t['fee'])}" if t["fee"] > 0 else "") + ")")
    mates = [m for m in stars_mod.players_at(c.stars, s["club"])][:6]
    if mates:
        add(T("Известные партнёры по команде: ", "Notable teammates: ") + ", ".join(f"{m['name']} ({m['pos']}, {m['age']})" for m in mates))
    h = (c.world.hegemon or {}).get(s.get("league")) if hasattr(c.world, "hegemon") else None
    if h and h["club"] in d.clubs:
        add(T("В лиге эпоха гегемона: ", "League hegemon era: ") + club_name(d, h["club"]))
    # --- лига
    lg = next((x for x in s.get("comps", []) if x["code"] in ("league", "youth")), None)
    if lg:
        add("")
        add(f"{T('ЛИГА', 'LEAGUE')}: {lang_name(lg)} - {club_result(lg, d)}" +
            (f"; {T('после первого круга были', 'after the first half we were')} {s['mid_rank']}-{T('ми', 'th')}" if s.get("mid_rank") else ""))
        add(f"{T('Игрок в лиге', 'Player in the league')}: {lg['games']} {T('матчей', 'apps')}, {lg['goals']} {T('голов', 'goals')}, "
            f"{lg['cs'] if c.pos == 'GK' else lg['assists']} {T('сухих матчей' if c.pos == 'GK' else 'передач', 'clean sheets' if c.pos == 'GK' else 'assists')}")
        tl = table_lines(c, d, s)
        if tl:
            add(T("Таблица (верх, мы, низ):", "Table (top, us, bottom):")); L.extend(tl)
        ml, summ = league_matches(c, d, s, rng)
        if ml:
            add(T("Все матчи лиги по турам:", "All league matches by matchday:")); L.extend("  " + x for x in ml)
            add(f"{T('Самая крупная победа', 'Biggest win')}: {summ['best']}; {T('самое тяжёлое поражение', 'heaviest defeat')}: {summ['worst']}")
    cups = cup_lines(c, d, s, rng)
    if cups:
        add(""); add(T("КУБКИ И МЕЖДУНАРОДНЫЕ ТУРНИРЫ:", "CUPS AND INTERNATIONAL COMPETITIONS:")); L.extend(cups)
    nat = nat_lines(c, d, s)
    if nat:
        add(""); add(T("СБОРНАЯ:", "NATIONAL TEAM:")); L.extend(nat)
    add("")
    add(T("ИТОГИ СЕЗОНА ИГРОКА:", "PLAYER'S SEASON TOTALS:") + f" {s['games']} {T('матчей', 'apps')}, {s['goals']} {T('голов', 'goals')}, {s['assists']} {T('передач', 'assists')}" +
        (f", {s['cs']} {T('сухих', 'clean sheets')}" if c.pos == "GK" else ""))
    if s["trophies"]:
        add(T("Трофеи: ", "Trophies: ") + "; ".join(trophy_name(t) for t in s["trophies"]))
    else:
        add(T("Трофеев нет.", "No trophies."))
    if s["awards"]:
        add(T("Личные награды: ", "Individual awards: ") + "; ".join(award_name(a, (s.get("ballon") or {}).get("rank")) for a in s["awards"]))
    b = s.get("ballon")
    if b and b.get("top"):
        top3 = ", ".join(f"{i}. {T('я', 'me') if x.get('me') else x['name']} ({club_name(d, x['club'])})" for i, x in enumerate(b["top"][:3], 1))
        add(f"{T('Золотой мяч', 'Ballon d’Or')} {b['year']}: {top3}" + (f"; {T('моё место', 'my place')}: {b['rank']}" if b.get("rank") else T("; меня не номинировали", "; I was not nominated")))
    for e in s.get("events", []):
        if e["t"] == "injury":
            add(T(f"Травма: {e['weeks']} недель" + (" (серьёзная)" if e.get("serious") else ""), f"Injury: {e['weeks']} weeks" + (" (serious)" if e.get("serious") else "")))
    for e in s.get("chronicle") or []:
        add(T("Веха: ", "Milestone: ") + chronicle_text(e, d))
    # --- что дальше
    if idx == len(c.seasons) - 1 and c.status != "retired":
        add(f"{T('Контракт: осталось лет', 'Contract years left')}: {c.contract_left}")
    return "\n".join(L)

# ---------------------------------------------------------------- сезоны по ключу: "p:3" - сезон игрока, "c:1" - сезон тренера
def keys(c):
    """Все сезоны жизни героя по порядку: сначала игрок, потом тренер."""
    out = [f"p:{i}" for i in range(len(c.seasons))]
    if c.coach:
        out += [f"c:{i}" for i in range(len(c.coach.get("seasons") or []))]
    return out

def record(c, key):
    """-> (вид "p"/"c", индекс, запись сезона)."""
    kind, i = key.split(":")
    i = int(i)
    return kind, i, (c.seasons[i] if kind == "p" else c.coach["seasons"][i])

def coach_facts(c, d, i):
    from .web.coach import deal_text, verdict_text, board_reason_text, kind_text, tactic_name, eur
    r = c.coach["seasons"][i]
    rng = random.Random(f"{c.id}-{r['year']}-coach-story")
    cl = d.clubs[r["club"]]
    L = []
    add = L.append
    add(f"{T('Сезон', 'Season')}: {r['season']}")
    add(f"{T('Герой', 'Hero')}: {c.name}, {r['age']} {T('лет', 'years old')}, "
        + T(f"главный тренер (бывший футболист, позиция {c.pos}, завершил карьеру игрока в {c.player_retire_age} лет)",
            f"head coach (a former {c.pos}, retired as a player at {c.player_retire_age})"))
    where = ", ".join(x for x in (cl.get("city"), cl.get("stadium") and f"{T('стадион', 'stadium')} {cl['stadium']}") if x)
    add(f"{T('Клуб', 'Club')}: {cl['name']}" + (f" ({where})" if where else "") + f", {r['league_name']} ({d.country_name(r['league_country'], i18n.LANG)})")
    add(f"{T('Задача руководства', 'Board target')}: {kind_text(r['kind'])} ({T('место', 'place')} {r['target']}); "
        f"{T('проект', 'project')}: {i18n.tr('coach.project.' + r['project'])}")
    tac = [tactic_name(t) for t in (r.get("tactics") or []) if t]
    if tac:
        add(T("Тактика по половинам сезона: ", "Tactics by half: ") + " -> ".join(tac))
    for m in r.get("moves", []):
        add(T("Сделка: ", "Deal: ") + deal_text(m))
    if r.get("fin"):
        f = r["fin"]
        add(f"{T('Финансы: потрачено', 'Finances: spent')} {eur(f['spent'])}, {T('получено', 'income')} {eur(f['income'])}, "
            f"{T('бюджет на конец', 'budget at the end')} {eur(f['budget'])}")
    add("")
    add(f"{T('ЛИГА', 'LEAGUE')}: {r['rank']}/{r['n']}, {r['w']}-{r['d']}-{r['l']}" +
        (f"; {T('после первого круга были', 'after the first half')}: {r['mid_rank']}" if r.get("mid_rank") else ""))
    tl = table_lines(c, d, r)
    if tl:
        add(T("Таблица (верх, мы, низ):", "Table (top, us, bottom):")); L.extend(tl)
    ml, summ = league_matches(c, d, r, rng, coach=True)
    if ml:
        add(T("Все матчи лиги по турам:", "All league matches by matchday:")); L.extend("  " + x for x in ml)
        add(f"{T('Самая крупная победа', 'Biggest win')}: {summ['best']}; {T('самое тяжёлое поражение', 'heaviest defeat')}: {summ['worst']}")
    cups = cup_lines(c, d, r, rng, coach=True)
    if cups:
        add(""); add(T("КУБКИ И МЕЖДУНАРОДНЫЕ ТУРНИРЫ:", "CUPS AND INTERNATIONAL COMPETITIONS:")); L.extend(cups)
    add("")
    add(T("Трофеи: ", "Trophies: ") + ("; ".join(trophy_name(t) for t in r["trophies"]) or T("нет", "none")))
    if r["awards"]:
        add(T("Награды тренеру: ", "Coaching awards: ") + "; ".join(award_name(a) for a in r["awards"]))
    for e in r.get("events", []):
        add(T("Событие: ", "Event: ") + i18n.tr("event." + e["t"]))
    for e in r.get("squad_events") or []:
        add(T("Состав: ", "Squad: ") + f"{e['name']} ({e['pos']}) - {i18n.tr('sqev.' + e['t'])}")
    add(f"{T('Раздражение руководства (0-100, 100 - увольнение)', 'Board anger (0-100, 100 means the sack)')}: {r['anger_before']:.0f} -> {r['anger_after']:.0f}")
    for k, v in r.get("reasons", []):
        if abs(v) >= 0.5:
            add(f"  {board_reason_text(k, r)}: {v:+.0f}")
    if r.get("verdict"):
        add(T("Итог для тренера: ", "Outcome for the coach: ") + verdict_text(r))
    bc = r.get("best_coach") or {}
    if bc.get("rank"):
        add(f"{T('Место в рейтинге лучших тренеров мира', 'Place in the world best coach ranking')}: {bc['rank']}")
    return "\n".join(L)

def career_so_far(c, d, key):
    kind, i, rec = record(c, key)
    prev = c.seasons[:i] if kind == "p" else c.seasons
    if not prev:
        return T("Это первый сезон карьеры.", "This is the first season of the career.")
    clubs = []
    for s in prev:
        n = club_name(d, s["club"])
        if not clubs or clubs[-1] != n:
            clubs.append(n)
    tro = [t for t in c.trophies if kind == "c" or t["season"] < rec["season"]]
    goals = sum(s["goals"] for s in prev)
    out = (T("Карьера игрока", "Playing career") + (T(" до этого сезона", " so far") if kind == "p" else "") + ": " + " -> ".join(clubs) +
           f"; {len(prev)} {T('сезонов', 'seasons')}, {goals} {T('голов', 'goals')}, {len(tro)} {T('трофеев', 'trophies')}" +
           (": " + ", ".join(f"{t['season']} {trophy_name(t)}" for t in tro[-6:]) if tro else ""))
    if kind == "c":
        cs = c.coach["seasons"][:i]
        if cs:
            out += "\n" + T("Тренерская карьера до этого сезона: ", "Coaching career so far: ") + "; ".join(
                f"{x['season']} {club_name(d, x['club'])} {x['rank']}/{x['n']}" for x in cs[-8:])
    return out

def memories(c, key):
    ks = keys(c)
    pos = ks.index(key)
    out = []
    for k in ks[max(0, pos - 6):pos]:
        _, _, s = record(c, k)
        st = s.get("story") or {}
        if st.get("memory"):
            out.append(f"[{s['season']}]\n{st['memory']}")
    return "\n".join(out)

def prompt(c, d, key):
    """-> {"system": ..., "user": ...} для нейросети: дневник сезона игрока ("p:i") или тренера ("c:i")."""
    kind, i, s = record(c, key)
    age = s["age"]
    mem = memories(c, key)
    data = facts(c, d, i) if kind == "p" else coach_facts(c, d, i)
    coach = kind == "c"
    if _ru():
        who = ("главного тренера футбольного клуба (бывшего футболиста) - героя футбольного симулятора" if coach else
               "профессионального футболиста - героя футбольного симулятора")
        life = ("работа с командой и штабом, тактика, разговоры с руководством, трансферы, пресс-конференции, переезды, город, дом, "
                "семья, друзья, бывшие партнёры по команде, деньги, хобби, отдых, сомнения и мечты, отношения и романтика" if coach else
                "тренировки, предсезонка, переезды, город, дом, семья, друзья, партнёры по команде, тренер, болельщики, журналисты, деньги, "
                "хобби, отдых, сомнения и мечты, отношения и романтика")
        system = (
            f"Ты пишешь личный дневник {who}. Пиши от первого лица, живо, эмоционально и подробно, как настоящий дневник: "
            "записи с датами (дата выделена жирным, например **14 августа 2026**). Это литературный текст на русском языке, без списков и таблиц.\n"
            "Правила:\n"
            "1. Все спортивные факты (счёт, соперники, место в таблице, трофеи, голы, передачи, травмы, награды, решения руководства) бери ТОЛЬКО "
            "из данных сезона и никогда им не противоречь. Детали матчей (минуты, как забили, атмосфера, погода) можно придумывать, если они не меняют фактов.\n"
            f"2. Кроме футбола, пиши о жизни: {life}. Личную жизнь можно придумывать, но она должна продолжать то, что записано "
            "в памяти о прошлых сезонах (имена, отношения, события), и развиваться со временем.\n"
            f"3. Герою сейчас {age} лет. Если ему меньше 18, романтика только невинная (симпатия, прогулки, переписка). В любом возрасте "
            "никаких откровенных сцен.\n"
            "4. Объём большой: 2500-3500 слов. Ключевые матчи (финалы, решающие туры, дерби" + ("" if coach else ", матчи с голами героя") +
            ") - подробно, проходные - коротко или упоминанием. Охвати весь сезон от начала до конца.\n"
            "5. В самом конце, после дневника, отдельной строкой напиши «ПАМЯТЬ:» и под ней 5-10 коротких строк - факты о личной жизни "
            "и окружении героя, которые важно помнить в следующих сезонах (имена близких, отношения, друзья, дом, питомцы, тренер или помощники, "
            "соперники, обещания). Этот блок читатель не увидит.")
        user = (f"Данные сезона:\n\n{data}\n\n{career_so_far(c, d, key)}\n\n"
                + (f"Память о прошлых сезонах (продолжай эти линии):\n{mem}\n\n" if mem else "Прошлых записей нет: придумай окружение героя с нуля.\n\n")
                + "Напиши дневник этого сезона.")
    else:
        who = ("a head coach (a former footballer), the hero of a football career simulator" if coach else
               "a professional footballer, the hero of a football career simulator")
        life = ("working with the squad and staff, tactics, talks with the board, transfers, press conferences, moving, the city, home, "
                "family, friends, former teammates, money, hobbies, holidays, doubts and dreams, relationships and romance" if coach else
                "training, pre-season, moving, the city, home, family, friends, teammates, the coach, fans, journalists, money, hobbies, "
                "holidays, doubts and dreams, relationships and romance")
        system = (
            f"You write the personal diary of {who}. Write in the first person, vividly, emotionally and in detail, like a real diary: "
            "dated entries (the date in bold, e.g. **14 August 2026**). This is literary prose in English, no lists or tables.\n"
            "Rules:\n"
            "1. Take every sporting fact (scores, opponents, league position, trophies, goals, assists, injuries, awards, board decisions) ONLY "
            "from the season data and never contradict it. Match details (minutes, how goals were scored, atmosphere, weather) may be invented if they do not change the facts.\n"
            f"2. Beyond football, write about life: {life}. Personal life may be invented, but it must continue what the memory of previous "
            "seasons says (names, relationships, events) and develop over time.\n"
            f"3. The hero is {age}. If under 18, romance stays innocent (a crush, walks, messages). At any age, no explicit scenes.\n"
            "4. Make it long: 2500-3500 words. Key matches (finals, decisive matchdays, derbies" + ("" if coach else ", games where the hero scored") +
            ") in detail, routine ones briefly. Cover the whole season from start to finish.\n"
            "5. At the very end, after the diary, write «MEMORY:» on its own line followed by 5-10 short lines of facts about the hero's personal "
            "life and people around him worth remembering next season (names, relationships, friends, home, pets, coach or assistants, rivals, "
            "promises). The reader will not see this block.")
        user = (f"Season data:\n\n{data}\n\n{career_so_far(c, d, key)}\n\n"
                + (f"Memory of previous seasons (continue these threads):\n{mem}\n\n" if mem else "No previous entries: create the hero's circle from scratch.\n\n")
                + "Write this season's diary.")
    return {"system": system, "user": user}

def save_answer(c, key, text, provider="", model=""):
    """Ответ нейросети -> дневник в записи сезона (текст и скрытая «память»)."""
    _, _, s = record(c, key)
    diary, memory = split_answer(text)
    s["story"] = {"text": diary, "memory": memory, "provider": provider, "model": model, "lang": i18n.LANG}
    return s["story"]

def missing(c, ks):
    """Ключи сезонов из ks, у которых ещё нет дневника (сезоны в академии без матчей пропускаются)."""
    out = []
    for k in ks:
        kind, _, s = record(c, k)
        if not s.get("story") and (kind == "c" or s.get("comps")):
            out.append(k)
    return out

def plain(text):
    """Дневник без разметки: для текстового файла."""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", text or "")
    return re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"\1", t)

def book_text(c, d):
    """Все дневники карьеры одной «книгой» (для экспорта итогов). Пустая строка, если дневников нет."""
    parts = []
    for k in keys(c):
        kind, _, s = record(c, k)
        st = s.get("story")
        if not st:
            continue
        title = f"{s['season']} · {club_name(d, s['club'])}" + (T(" · тренер", " · coach") if kind == "c" else "")
        parts.append(f"{title}\n{'-' * len(title)}\n\n{plain(st['text']).strip()}\n")
    if not parts:
        return ""
    head = T(f"ДНЕВНИК: {c.name}", f"DIARY: {c.name}")
    return f"{head}\n{'=' * len(head)}\n\n" + "\n\n".join(parts)

def split_answer(text):
    """Ответ нейросети -> (дневник, память)."""
    t = (text or "").strip()
    for mark in (MEMORY_RU, MEMORY_EN, "**" + MEMORY_RU + "**", "**" + MEMORY_EN + "**"):
        k = t.rfind(mark)
        if k >= 0:
            return t[:k].rstrip(" \n*#-"), t[k + len(mark):].strip(" \n*")
    return t, ""
