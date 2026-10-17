"""Состав клуба тренера: игроки по позициям, схема, основной состав и сила команды.

У клуба тренера есть настоящий состав (23-25 человек): известные игроки клуба из мира (stars.all_players с этим клубом) плюс
сгенерированные игроки. Сила команды = средний OVR основы (11 игроков) в выбранной схеме с учётом игры не на своей позиции.
Её и использует симуляция (world.score клуба тренера пересчитывается из состава перед каждой половиной сезона), поэтому:
  - новичок усиливает команду, только если проходит в основу на своей позиции (или рядом);
  - продажа запасного почти ничего не меняет, продажа ключевого игрока - заметно;
  - игроки стареют и растут сами (stars.evolve), и сила клуба меняется вместе с ними.
Остальные клубы мира живут по-старому: общей силой и несколькими известными игроками.
"""
import zlib
from .player import clamp
from . import stars as stars_mod

# схемы: позиции 11 игроков основы; стиль - (множитель своих голов, пропущенных), добавляется к тактике.
# Ключ - «расстановка» или «расстановка стиль» (att - атакующая, def - оборонительная, dia - ромб, wide - через фланги);
# без стиля - сбалансированная. Старые ключи (4-3-3, 4-4-2...) не менялись: сохранения продолжают работать.
_D4 = ["GK", "LB", "CB", "CB", "RB"]
_D3 = ["GK", "CB", "CB", "CB"]
_D5 = ["GK", "LB", "CB", "CB", "CB", "RB"]
FORMATIONS = {
    "4-3-3":        (_D4 + ["CM", "CDM", "CM", "LW", "ST", "RW"], (1.04, 1.03)),
    "4-3-3 att":    (_D4 + ["CM", "CAM", "CM", "LW", "ST", "RW"], (1.08, 1.06)),
    "4-3-3 def":    (_D4 + ["CDM", "CM", "CDM", "LW", "ST", "RW"], (1.01, 0.99)),
    "4-2-3-1":      (_D4 + ["CDM", "CDM", "LW", "CAM", "RW", "ST"], (1.02, 0.99)),
    "4-2-3-1 wide": (_D4 + ["CDM", "CM", "LM", "CAM", "RM", "ST"], (1.02, 1.00)),
    "4-4-2":        (_D4 + ["LM", "CM", "CM", "RM", "ST", "ST"], (1.00, 1.00)),
    "4-4-2 def":    (_D4 + ["LM", "CDM", "CDM", "RM", "ST", "ST"], (0.97, 0.95)),
    "4-4-2 dia":    (_D4 + ["CDM", "CM", "CM", "CAM", "ST", "ST"], (1.03, 1.02)),
    "4-3-1-2":      (_D4 + ["CM", "CDM", "CM", "CAM", "ST", "ST"], (1.04, 1.03)),
    "4-1-4-1":      (_D4 + ["CDM", "LM", "CM", "CM", "RM", "ST"], (0.97, 0.96)),
    "4-5-1 att":    (_D4 + ["LM", "CM", "CAM", "CM", "RM", "ST"], (1.03, 1.02)),
    "3-5-2":        (_D3 + ["LM", "CDM", "CM", "CM", "RM", "ST", "ST"], (1.02, 1.01)),
    "3-5-2 att":    (_D3 + ["LM", "CM", "CAM", "CM", "RM", "ST", "ST"], (1.06, 1.05)),
    "3-4-1-2":      (_D3 + ["LM", "CM", "CM", "RM", "CAM", "ST", "ST"], (1.05, 1.04)),
    "3-4-3":        (_D3 + ["LM", "CM", "CM", "RM", "LW", "ST", "RW"], (1.06, 1.05)),
    "5-3-2":        (_D5 + ["CM", "CDM", "CM", "ST", "ST"], (0.95, 0.92)),
    "5-4-1":        (_D5 + ["LM", "CM", "CM", "RM", "ST"], (0.93, 0.90)),
}
DEFAULT_FORMATION = "4-3-3"

# как часто клубы играют по схеме (схема прошлого тренера - под неё собран состав клуба)
FORMATION_WEIGHTS = {"4-3-3": 10, "4-3-3 att": 4, "4-3-3 def": 4, "4-2-3-1": 10, "4-2-3-1 wide": 4, "4-4-2": 7, "4-4-2 def": 3,
                     "4-4-2 dia": 3, "4-3-1-2": 2, "4-1-4-1": 4, "4-5-1 att": 2, "3-5-2": 4, "3-5-2 att": 2, "3-4-1-2": 2,
                     "3-4-3": 4, "5-3-2": 3, "5-4-1": 2}

def club_formation(cid):
    """Схема, по которой клуб играл до прихода тренера (постоянная для клуба)."""
    keys = list(FORMATION_WEIGHTS)
    total = sum(FORMATION_WEIGHTS.values())
    x = zlib.crc32(("formation:" + cid).encode()) % total
    for k in keys:
        x -= FORMATION_WEIGHTS[k]
        if x < 0:
            return k
    return DEFAULT_FORMATION

def template_for(f, rng=None, extra=3):
    """Сколько игроков каждой позиции нужно под схему: вратарей 3, на каждую позицию основы - замена
    (одиночную позицию закрывают двое, двойную - четверо, тройную - пятеро), плюс несколько игроков других позиций."""
    slots = FORMATIONS.get(f, FORMATIONS[DEFAULT_FORMATION])[0]
    out = {"GK": 3}
    for pos in set(slots) - {"GK"}:
        n = slots.count(pos)
        out[pos] = {1: 2, 2: 4}.get(n, n + 2)
    if rng:
        others = [p for p in ACADEMY_POS if p != "GK"]
        for _ in range(extra):
            pos = rng.choices(others, weights=[ACADEMY_POS[p] * (0.5 if p in out else 1.5) for p in others])[0]
            out[pos] = out.get(pos, 0) + 1
    return out

def formation_parts(f):
    """'4-3-3 att' -> ('4-3-3', 'att'); без стиля - ('4-3-3', 'bal')."""
    base, _, style = f.partition(" ")
    return base, style or "bal"
LINE = {"GK": "GK", "CB": "DEF", "LB": "DEF", "RB": "DEF", "CDM": "MID", "CM": "MID", "CAM": "MID", "LM": "MID", "RM": "MID",
        "LW": "ATT", "RW": "ATT", "CF": "ATT", "ST": "ATT"}
LINES = ("GK", "DEF", "MID", "ATT")
# штраф к OVR за игру не на своей позиции: позиция игрока -> {позиция в схеме: штраф}; чего нет - 12 (вратарь в поле - 40)
NEAR = {
    "GK": {}, "CB": {"LB": 5, "RB": 5, "CDM": 5},
    "LB": {"RB": 4, "LM": 4, "CB": 5, "LW": 6}, "RB": {"LB": 4, "RM": 4, "CB": 5, "RW": 6},
    "CDM": {"CM": 3, "CB": 5, "CAM": 8}, "CM": {"CDM": 3, "CAM": 3, "LM": 6, "RM": 6},
    "CAM": {"CM": 3, "CF": 4, "LW": 5, "RW": 5, "ST": 7}, "LM": {"LW": 2, "RM": 4, "LB": 5, "CM": 6},
    "RM": {"RW": 2, "LM": 4, "RB": 5, "CM": 6}, "LW": {"LM": 2, "RW": 3, "CAM": 5, "CF": 6, "ST": 6},
    "RW": {"RM": 2, "LW": 3, "CAM": 5, "CF": 6, "ST": 6}, "ST": {"CF": 2, "LW": 6, "RW": 6, "CAM": 7},
    "CF": {"ST": 2, "CAM": 4, "LW": 5, "RW": 5},
}
# состав по умолчанию (сколько игроков каждой позиции держит клуб)
TEMPLATE = {"GK": 3, "CB": 4, "LB": 2, "RB": 2, "CDM": 2, "CM": 3, "CAM": 2, "LM": 1, "RM": 1, "LW": 2, "RW": 2, "ST": 2}
MIN_SQUAD = 22
MAX_SQUAD = 30             # больше игроков в заявке не бывает: чтобы купить, сначала нужно кого-то продать

# ---------- форма, травмы, ротация, настроение ----------
ROTATION = {"none": 0.0, "some": 0.15, "heavy": 0.3}   # доля минут, которую получают запасные
FIT_LOSS, FIT_LOSS_PRESS, FIT_GAIN = 25.0, 12.0, 20.0  # за половину сезона: основа теряет форму (прессинг - больше), запас набирает

def available(p):
    """Игрок может играть: не травмирован и не дисквалифицирован."""
    return not p.get("inj")

def fatigue_pen(p):
    """Штраф к OVR за усталость: с формы ниже 85 - 0.12 за каждый пункт (форма 60 -> -3)."""
    return max(0.0, 85.0 - p.get("fit", 100.0)) * 0.12

def eff(p):
    """OVR игрока в матчах: с учётом усталости и недовольства (недовольный играет на 2 слабее)."""
    return p["ovr"] - fatigue_pen(p) - (2.0 if p.get("unhappy") else 0.0)

ROT_GAP = 5.0          # запасной не слабее основы больше чем на 5 OVR - игрок ротации (сам получает минуты: кубки, замены)
ROT_MIN = 0.3          # минимум минут игрока ротации за сезон (доля); резерв играет только при ротации состава
STAR_GAP = 1.0         # запасной сильнее среднего игрока основы на 1+ считает, что должен играть

def xi_avg(c, formation=None):
    xi = [p for _, p, _ in current_xi(c, formation) if p]
    return sum(p["ovr"] for p in xi) / max(1, len(xi))

def roles(c, formation=None):
    """Роль каждого игрока: xi - основа, rot - ротация (до 5 OVR ниже среднего игрока основы), res - резерв. -> {id: роль}."""
    xi = {p["id"] for _, p, _ in current_xi(c, formation) if p}
    avg = xi_avg(c, formation)
    return {p["id"]: "xi" if p["id"] in xi else "rot" if p["ovr"] >= avg - ROT_GAP else "res" for p in squad(c)}

def wants_to_start(p, avg):
    """Игрок, который считает, что заслужил основу: заметно сильнее среднего игрока основы и не моложе 22."""
    return p["age"] >= 22 and p["ovr"] >= avg + STAR_GAP

def refresh_mood(c):
    """Недовольство снимается с тех, кто больше не претендует на основу (или уже в ней)."""
    avg = xi_avg(c)
    xi = {p["id"] for _, p, _ in current_xi(c) if p}
    for p in squad(c):
        if p.get("unhappy") and (p["id"] in xi or not wants_to_start(p, avg)):
            p["unhappy"] = False

def play_half(c, press=False):
    """Половина сезона для состава: минуты, форма, травмы и дисквалификации. -> события (для экрана середины сезона и отчёта).
    Основа играет почти всё; игроки ротации - не меньше ROT_MIN за сезон (кубки, замены); резерв - только при ротации."""
    s, rng = c.coach, c.rng
    r = ROTATION.get(s.get("rotation", "none"), 0.0)
    players = squad(c)
    role = roles(c)
    bench = [p for p in players if role[p["id"]] != "xi" and available(p)]
    bench_share = min(1.0, r * 11 / max(1, len(bench))) if r > 0 else 0.0
    events = []
    for p in players:
        p.setdefault("fit", 100.0)
        if p.get("inj"):                                     # пропускает эту половину сезона
            p["inj"] -= 1
            if p["inj"] <= 0:
                p["inj"], p["inj_kind"], p["fit"] = 0, None, 75.0
            continue
        if role[p["id"]] == "xi":
            p["min"] = p.get("min", 0.0) + 0.5 * (1 - r)
            p["fit"] = clamp(p["fit"] - (FIT_LOSS + FIT_LOSS_PRESS * press) * (1 - 1.5 * r), 30.0, 100.0)
            inj_p = 0.03 + max(0.0, 70.0 - p["fit"]) * 0.003
            knock_p = 0.12
        else:
            share = max(ROT_MIN, 1.5 * bench_share) if role[p["id"]] == "rot" else 0.6 * bench_share
            p["min"] = p.get("min", 0.0) + 0.5 * share
            p["fit"] = clamp(p["fit"] + FIT_GAIN - 25.0 * share, 30.0, 100.0)
            inj_p = 0.008 + 0.02 * share
            knock_p = 0.04
        starters = role[p["id"]] == "xi"
        if p.pop("fresh", False):                             # новичок прошёл медосмотр: первые полсезона без травм
            continue
        if rng.random() < knock_p and rng.random() >= inj_p:  # лёгкая травма: пропустил несколько матчей, но не полсезона
            p["min"] = max(0.0, p["min"] - 0.08)
            events.append({"t": "knock", "name": p["name"], "pos": p["pos"], "ovr": p["ovr"]})
            continue
        if rng.random() < inj_p:                              # серьёзная: вне игры полсезона и дольше (редко)
            halves = 1 if rng.random() < 0.75 else (2 if rng.random() < 0.8 else 3)
            p["inj"], p["inj_kind"] = halves, "injury"
            events.append({"t": "injury", "name": p["name"], "pos": p["pos"], "ovr": p["ovr"], "halves": halves})
        elif starters and rng.random() < 0.015:
            p["inj"], p["inj_kind"] = 1, "ban"
            events.append({"t": "ban", "name": p["name"], "pos": p["pos"], "ovr": p["ovr"], "halves": 1})
    return events

def end_of_season(c):
    """Итоги сезона для состава: недовольство (игрок, который сильнее среднего игрока основы, а играл мало), минуты сезона
    для роста молодых. Игроки ротации и резерва свою роль принимают. -> события."""
    avg = xi_avg(c)
    events = []
    for p in squad(c):
        m = p.get("min", 0.0)
        was = p.get("unhappy", False)
        if wants_to_start(p, avg) and m < 0.45 and not p.get("inj"):
            p["unhappy"] = True
            if not was:
                events.append({"t": "unhappy", "name": p["name"], "pos": p["pos"], "ovr": p["ovr"]})
        elif m >= 0.5:
            p["unhappy"] = False
        if p["age"] <= 21 and m < 0.2:
            events.append({"t": "no_minutes", "name": p["name"], "pos": p["pos"], "ovr": p["ovr"]})
        p["min_season"], p["min"] = round(m, 2), 0.0
    return events

def penalty(pos, slot):
    """Штраф к OVR: соседняя позиция - 2-8, та же линия - 12, другая линия - 20, вратарь в поле (и наоборот) - 40."""
    if pos == slot:
        return 0
    if pos == "GK" or slot == "GK":
        return 40
    near = NEAR.get(pos, {}).get(slot)
    if near is not None:
        return near
    return 12 if LINE[pos] == LINE[slot] else 20

def squad(c, cid=None):
    """Игроки клуба тренера (по убыванию OVR)."""
    return stars_mod.players_at(c.stars, cid or c.coach["club"])

def best_xi(players, formation):
    """Основной состав: жадная расстановка по позициям схемы (сначала вратарь и самые «узкие» позиции), затем доводка
    обменами и заменами, пока сумма OVR основы растёт. -> [(позиция в схеме, игрок или None, OVR с учётом позиции)]."""
    slots = FORMATIONS[formation][0]
    players = [p for p in players if available(p)]              # травмированные и дисквалифицированные не играют
    val = lambda p, slot: eff(p) - penalty(p["pos"], slot) if p else 40.0      # пустое место в основе - как очень слабый игрок
    order = sorted(range(11), key=lambda i: (slots[i] != "GK", sum(1 for p in players if p["pos"] == slots[i])))
    used, pick = set(), [None] * 11
    for i in order:
        cand = [p for p in players if p["id"] not in used]
        if cand:
            best = max(cand, key=lambda p: val(p, slots[i]))
            used.add(best["id"]); pick[i] = best
    for _ in range(30):                                       # доводка: обмен двух игроков основы или замена запасным
        improved = False
        for i in range(11):
            for j in range(i + 1, 11):
                if val(pick[i], slots[j]) + val(pick[j], slots[i]) > val(pick[i], slots[i]) + val(pick[j], slots[j]) + 1e-9:
                    pick[i], pick[j] = pick[j], pick[i]; improved = True
            bench = [p for p in players if p["id"] not in {x["id"] for x in pick if x}]
            if bench:
                b = max(bench, key=lambda p: val(p, slots[i]))
                if val(b, slots[i]) > val(pick[i], slots[i]) + 1e-9:
                    pick[i] = b; improved = True
        if not improved:
            break
    return [(slots[i], pick[i], round(val(pick[i], slots[i]), 1)) for i in range(11)]

def xi_rating(players, formation):
    xi = best_xi(players, formation)
    return round(sum(v for _, _, v in xi) / 11.0, 2)

def current_xi(c, formation=None):
    """Основа, которая выходит на поле: автоматическая (best_xi) или выбранная тренером вручную (s["lineup"][схема] - id по
    позициям схемы). Ушедших из клуба и пустые места в ручной основе занимают лучшие из оставшихся."""
    s = c.coach
    f = formation or s.get("formation", DEFAULT_FORMATION)
    players = squad(c)
    if s.get("lineup_mode") != "manual":
        return best_xi(players, f)
    ids = (s.get("lineup") or {}).get(f) or []
    players = [p for p in players if available(p)]
    by = {p["id"]: p for p in players}
    slots = FORMATIONS[f][0]
    pick, seen = [], set()
    for i in range(11):
        p = by.get(ids[i]) if i < len(ids) else None
        if p and p["id"] in seen:
            p = None
        pick.append(p)
        if p:
            seen.add(p["id"])
    for i in range(11):
        if pick[i] is None:
            rest = [p for p in players if p["id"] not in seen]
            if rest:
                pick[i] = max(rest, key=lambda p: eff(p) - penalty(p["pos"], slots[i])); seen.add(pick[i]["id"])
    return [(slots[i], pick[i], round(eff(pick[i]) - penalty(pick[i]["pos"], slots[i]), 1) if pick[i] else 40.0) for i in range(11)]

def set_lineup(c, slot_index, pid, formation=None):
    """Тренер ставит игрока на позицию основы. Если он уже стоит на другой позиции - игроки меняются местами."""
    s = c.coach
    f = formation or s.get("formation", DEFAULT_FORMATION)
    xi = current_xi(c, f)
    ids = [p["id"] if p else None for _, p, _ in xi]
    if pid in ids:
        j = ids.index(pid)
        ids[j], ids[slot_index] = ids[slot_index], ids[j]
    else:
        ids[slot_index] = pid
    s.setdefault("lineup", {})[f] = ids
    s["lineup_mode"] = "manual"

def team_rating(c, formation=None, players=None):
    """Сила команды тренера (OVR): по основе, которая выходит на поле. С players - по лучшей основе из этих игроков
    (оценка «если купить / продать»)."""
    f = formation or c.coach.get("formation", DEFAULT_FORMATION)
    if players is not None:
        return xi_rating(players, f)
    xi = current_xi(c, f)
    base = sum(v for _, _, v in xi) / 11.0
    r = ROTATION.get(c.coach.get("rotation", "none"), 0.0)
    if r > 0:                                                 # ротация: часть минут играет второй состав
        used = {p["id"] for _, p, _ in xi if p}
        base = (1 - r) * base + r * xi_rating([p for p in squad(c) if p["id"] not in used], f)
    return round(base, 2)

def apply_to_world(c):
    """Сила клуба в мире = сила основы."""
    cid = c.coach["club"]
    sc = clamp(2.5 * (team_rating(c) - 48.0), -32.5, 100.0)
    c.world.score[cid] = sc
    c.world.base[cid] = sc

def line_counts(players):
    out = {ln: 0 for ln in LINES}
    for p in players:
        out[LINE[p["pos"]]] += 1
    return out

def pot_range(p):
    """Возможный рейтинг игрока, который ещё растёт: (от, до) или None. У молодых вилка шире, у 24-28 - уже."""
    if p["age"] >= 29 or p["pot"] - p["ovr"] < 1.5:
        return None
    if p["age"] <= 23:
        return int(round(max(p["ovr"] + 1, p["pot"] - 4))), int(round(min(97, p["pot"] + 3)))
    return int(round(max(p["ovr"] + 1, p["pot"] - 1))), int(round(min(97, p["pot"] + 1)))

def _scout_off(p):
    """Где внутри вилки лежит настоящий потенциал (0..1) - постоянно для игрока, но игрок этого не знает."""
    return (zlib.crc32(str(p.get("id") or p.get("name") or "").encode()) % 1000) / 1000.0

def pot_state(p, width=None):
    """-> ("range", (от, до)) | ("peak", None) | ("decline", None): растёт / на пике / угасание (с 31 года рейтинг падает).
    width - ширина вилки по оценке скаутов (тренер): настоящий потенциал где-то внутри неё; у 24-28 вилка вдвое уже."""
    if p["age"] >= 31:
        return "decline", None
    if width is None:
        r = pot_range(p)
        return ("range", r) if r else ("peak", None)
    if p["age"] >= 29 or p["pot"] - p["ovr"] < 1.5:
        return "peak", None
    w = width if p["age"] <= 23 else max(1, width // 2)
    lo = max(p["ovr"] + 1, p["pot"] - _scout_off(p) * w)
    return "range", (int(round(lo)), int(round(min(97, lo + w))))

# ---------- создание состава ----------
def _gen_player(c, cid, pos, ovr, age, pot):
    rng, d = c.rng, c.d
    lc = d.leagues[c.world.club_league[cid]]["country"]
    nat = lc if rng.random() < 0.6 else rng.choices(list(stars_mod.REGEN_NATS), weights=list(stars_mod.REGEN_NATS.values()))[0]
    p = stars_mod.add_other(c.stars, stars_mod.gen_name(rng, nat, d.countries[nat]["conf"]), nat, pos, age, round(ovr, 1), round(pot, 1), cid)
    p["squad"] = True
    return p

def build(c, cid):
    """Полный состав для клуба, который возглавил тренер: известные игроки + сгенерированные по шаблону.
    Сгенерированные подгоняются так, чтобы сила основы совпала с нынешним OVR клуба."""
    rng, w = c.rng, c.world
    target = w.team_ovr(cid)
    have = squad(c, cid)
    for p in have:
        p["squad"] = True
    f = club_formation(cid)                                   # состав собран под схему прошлого тренера
    slots = FORMATIONS[f][0]
    need = template_for(f, rng)
    for p in have:
        if need.get(p["pos"], 0) > 0:
            need[p["pos"]] -= 1
    gen = []
    for pos, n in need.items():
        n_start = slots.count(pos) - sum(1 for p in have if p["pos"] == pos)   # места в основе, которые не заняли известные игроки
        for k in range(n):
            first = k < n_start
            age = rng.randint(22, 31) if first else rng.choice([rng.randint(18, 22), rng.randint(23, 33)])
            ovr = target + (rng.gauss(0, 1.8) if first else -rng.uniform(3, 8))
            pot = ovr + (rng.uniform(2, 9) if age <= 22 else rng.uniform(0, 1.5))
            gen.append(_gen_player(c, cid, pos, ovr, age, pot))
    # подгонка: основа должна давать нынешний OVR клуба (известные игроки не трогаются)
    for _ in range(3):
        diff = target - xi_rating(squad(c, cid), f)
        if abs(diff) < 0.2:
            break
        for p in gen:
            p["ovr"] = round(clamp(p["ovr"] + diff, 35, 95), 1)
            p["pot"] = round(max(p["pot"] + diff, p["ovr"]), 1)
    return squad(c, cid)

ACADEMY_POS = {"GK": 2, "CB": 4, "LB": 2, "RB": 2, "CDM": 2, "CM": 4, "CAM": 2, "LM": 2, "RM": 2, "LW": 2, "RW": 2, "CF": 1, "ST": 3}

def academy_fill(c, quality_bonus=0.0):
    """Летний выпуск академии: 1-2 воспитанника любых позиций (чаще - позиций своей схемы), а если в составе мало игроков
    или для схемы не хватает игроков на позицию - ещё и на эти места. -> список новых."""
    cid, rng = c.coach["club"], c.rng
    players = squad(c)
    team = team_rating(c)
    counts = {}
    for p in players:
        counts[p["pos"]] = counts.get(p["pos"], 0) + 1
    slots = FORMATIONS.get(c.coach.get("formation", DEFAULT_FORMATION), FORMATIONS[DEFAULT_FORMATION])[0]
    need = {pos: slots.count(pos) + (1 if pos == "GK" else 0) for pos in set(slots)}      # хотя бы по одному на место (вратарей - два)
    lacking = [pos for pos, n in need.items() if counts.get(pos, 0) < n]
    rng.shuffle(lacking)
    weights = {pos: w * (2 if pos in need else 1) for pos, w in ACADEMY_POS.items()}
    room = MAX_SQUAD - 2 - len(players)
    regular = min(max(0, room - len(lacking)), 1 + (rng.random() < 0.4 + 0.1 * quality_bonus))
    new = []
    while len(players) + len(new) < MIN_SQUAD or lacking or regular > 0:
        if lacking:
            pos = lacking.pop(0)
        else:
            pos = rng.choices(list(weights), weights=list(weights.values()))[0]
            regular -= 1
        ovr = team - rng.uniform(6, 11) + quality_bonus
        pot = ovr + rng.uniform(4, 14) + quality_bonus
        p = _gen_player(c, cid, pos, ovr, rng.randint(17, 19), pot)
        p["academy"] = True
        new.append(p)
    return new
