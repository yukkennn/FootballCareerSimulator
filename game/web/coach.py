"""Тренерская карьера для узкого экрана: предложения, клуб (схема, ротация, тактика, состав, основа), трансферное окно,
середина сезона, итоги сезона, тренерские вкладки итогов. Логика та же, что в game/ui/coach_pages.py."""
from .. import i18n
from ..i18n import tr
from ..text import stars_text, trophy_name, stage, short_trophy, award_name, money
from ..coach import pressure, DECAY, TACTICS, REL_LOVED, season_label
from ..transfers import annual_budget, price, pot_width, scouting, MAX_SCOUTS
from .. import squad as squad_mod
from .. import stars as stars_mod
from ..ui import theme
from .parts import esc, btn, logo, club_card, kv
from .report import league_table_html, details_html

POS_ORDER = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "CF", "ST"]
# сортировка рынка: (ключ, номер столбца как в десктопной версии, по убыванию)
SORTS = [("ovr", 3, True), ("pot", 4, True), ("effect", 7, True), ("price", 6, False), ("age", 2, False)]

# ---------------------------------------------------------------------- тексты (как в coach_pages.py)
def kind_text(kind):
    return tr("kind." + kind)

def patience_text(p):
    return tr("patience.low" if p >= 1.3 else "patience.mid" if p >= 0.85 else "patience.high")

def anger_color(v):
    return theme.ACCENT if v < 40 else theme.GOLD if v < 70 else theme.RED

def tactic_name(t):
    return tr("tactic." + t) if t else "—"

def rel_tag(rel):
    if rel >= REL_LOVED:
        return tr("rel.loved"), True
    if rel >= 15:
        return tr("rel.good"), True
    if rel <= -10:
        return tr("rel.bad"), False
    return None, False

def eur(x):
    return money(x) if x > 0.004 else tr("money.m", v="0")

def inj_text(halves):
    return tr("inj.len" + str(max(1, min(3, int(halves)))))

def pot_text(p, w=None):
    st, r = squad_mod.pot_state(p, w)
    return f"{r[0]}–{r[1]}" if st == "range" else tr("pot." + st)

def pot_html(p, w=None):
    st, _ = squad_mod.pot_state(p, w)
    cls = "ok" if st == "range" else "muted" if st == "peak" else "ev"
    return f'<span class="{cls}">{esc(pot_text(p, w))}</span>'

def pot_key(p, w=None):
    st, r = squad_mod.pot_state(p, w)
    return r[1] if st == "range" else p["ovr"] - (0.5 if st == "decline" else 0)

def status_text(p, cid):
    if p.get("inj"):
        return (tr("st.ban") if p.get("inj_kind") == "ban" else tr("st.injury", t=inj_text(p["inj"]))), theme.RED
    if p.get("unhappy"):
        return tr("st.unhappy"), "#e59b5a"
    if p.get("loan_from") and p["loan_from"] != cid:
        return tr("st.loan_in"), theme.MUTED
    return "", None

def formation_name(f):
    base, style = squad_mod.formation_parts(f)
    return f"{base} ({tr('fstyle.' + style)})"

def verdict_text(r):
    return tr("verdict." + r["verdict"]) if r.get("verdict") else ""

def deal_text(m):
    f = money(m["fee"])
    if m["t"] == "buy":
        return tr("deal.buy", n=m["name"], o=f"{m['ovr']:.0f}", f=f)
    if m["t"] == "loan_in":
        return tr("deal.loan_in", n=m["name"], o=f"{m['ovr']:.0f}", f=f)
    if m["t"] == "loan_out":
        return tr("deal.loan_out", n=m["name"], o=f"{m['ovr']:.0f}", f=f if m["fee"] > 0 else tr("deal.no_fee"))
    if m["t"] == "scout":
        return tr("deal.scout", n=m["name"], f=f)
    if m["t"] == "sell":
        return tr("deal.sell", n=m["name"], o=f"{m['ovr']:.0f}", f=f) if m.get("name") else tr("deal.sell_generic", f=f)
    if m["t"] == "talent":
        return tr("deal.talent", n=m["name"], f=f)
    return tr("deal.academy", f=f)

def board_reason_text(key, r):
    if key == "league":
        if r["rank"] > r["target"]:
            return tr("board.league_worse", r=r["rank"], e=r["target"])
        if r["rank"] < r["target"]:
            return tr("board.league_better", r=r["rank"], e=r["target"])
        return tr("board.league_ok", r=r["rank"])
    if key in ("title", "relegated", "promoted", "mid_fired", "spending", "profit"):
        return tr("board." + key)
    if key.startswith("cup:"):
        _, code, st = key.split(":")
        return tr("board.cup", c=short_trophy(code), s=stage(st))
    return key

def records_rows(rec, d):
    name = lambda cid: d.clubs[cid]["name"]
    out = []
    if rec["longest_spell"] and rec["longest_spell"][1] > 0:
        out.append((tr("rec.longest_spell"), tr("rec.seasons_n", club=name(rec["longest_spell"][0]), n=rec["longest_spell"][1])))
    if rec["legends"]:
        out.append((tr("rec.legend"), ", ".join(name(c) for c in rec["legends"])))
    if rec["no_fire_streak"]:
        out.append((tr("rec.no_fire"), str(rec["no_fire_streak"])))
    if rec["best_pct"]:
        out.append((tr("rec.best_pct"), tr("rec.season_val", season=rec["best_pct"][0], club=name(rec["best_pct"][1]), v=f"{rec['best_pct'][2]}%")))
    if rec["best_ppg"]:
        out.append((tr("rec.best_ppg"), tr("rec.season_val", season=rec["best_ppg"][0], club=name(rec["best_ppg"][1]), v=f"{rec['best_ppg'][2]:.2f}")))
    if rec["overachieve"]:
        s_, cid, dd, rk, tg = rec["overachieve"]
        out.append((tr("rec.overachieve"), tr("rec.overachieve_val", season=s_, club=name(cid), r=rk, t=tg, d=dd)))
    if rec["shortest_fired"]:
        out.append((tr("rec.shortest"), tr("rec.seasons_n", club=name(rec["shortest_fired"][0]), n=rec["shortest_fired"][1])))
    if rec["trophies_by_club"]:
        out.append((tr("rec.trophies_by_club"), "; ".join(tr("rec.trophies_club_val", club=name(c), n=v["all"], t=v["titles"])
                                                          for c, v in rec["trophies_by_club"])))
    return out

# ---------------------------------------------------------------------- куски HTML
def meter(value):
    v = max(0.0, min(100.0, value))
    return f'<div class="meter"><i style="width:{v:.0f}%;background:{anger_color(value)}"></i><span>{value:.0f} / 100</span></div>'

def chips(act, items, current):
    return '<div class="tabs">' + "".join(f'<button class="chip{" on" if k == current else ""}" data-act="{act}" data-arg="{esc(k)}">{esc(t)}</button>'
                                         for k, t in items) + "</div>"

def select(onchange, options, current, label=None):
    opts = "".join(f'<option value="{esc(v)}"{" selected" if v == current else ""}>{esc(t)}</option>' for v, t in options)
    lab = f'<span class="muted small">{esc(label)}</span>' if label else ""
    return f'<label class="sel">{lab}<select data-onchange="{onchange}">{opts}</select></label>'

def squad_events_html(events):
    groups = {}
    for e in events:
        groups.setdefault(e["t"], []).append(e)
    out = []
    style = {"injury": theme.RED, "ban": theme.RED, "knock": "#e59b5a", "unhappy": "#e59b5a", "no_minutes": theme.MUTED}
    for k in ("injury", "ban", "knock", "unhappy", "no_minutes"):
        es = groups.get(k)
        if not es:
            continue
        if k == "injury":
            names = ", ".join(f"{e['name']} ({e['pos']}, {tr('inj.out', t=inj_text(e['halves']))})" for e in es)
        else:
            names = ", ".join(f"{e['name']} ({e['pos']}, {e['ovr']:.0f})" for e in es)
        out.append(f'<div style="color:{style[k]}">• {esc(tr("sqev." + k))}: {esc(names)}</div>')
    return "".join(out)

def best_coach_html(r, d):
    bc = r.get("best_coach")
    if not bc or not bc.get("top"):
        return ""
    rows = []
    for i, x in enumerate(bc["top"], 1):
        club = d.clubs[x["club"]]["name"] if x["club"] in d.clubs else ""
        rows.append(f'<tr class="{"me" if x["me"] else ""}"><td>{i}</td><td>{esc(x["name"])}<div class="muted small">{esc(club)}</div></td>'
                    f'<td>{x["pts"]:.1f}</td></tr>')
    extra = f'<div class="cap">{esc(tr("bc.my_rank", r=bc["rank"]))}</div>' if bc.get("rank") and bc["rank"] > 5 else ""
    return (f'<div class="blk"><div class="bh">{esc(tr("bc.title"))}</div><table class="tbl bdo"><tbody>{"".join(rows)}</tbody></table>{extra}</div>')

def coach_season_html(c, d, r):
    h = []
    lg = f"{r['league_name']} ({d.country_name(r['league_country'], i18n.LANG)})"
    h.append(f'<div class="season-h"><div class="h2">{esc(r["club_name"])}</div><div class="muted small">{esc(lg)} · '
             f'{esc(tr("career.age", n=r["age"]))} · {esc(tr("coach.project." + r["project"]))}</div></div>')
    diff = r["target"] - r["rank"]
    col = theme.ACCENT if diff > 0 else theme.RED if diff < -1 else theme.TEXT
    lines = [f'<div class="b" style="color:{col};font-size:16px">{esc(tr("creport.place", r=r["rank"], n=r["n"], t=kind_text(r["kind"]), e=r["target"]))}</div>']
    tac = [t for t in (r.get("tactics") or []) if t]
    if tac:
        txt = tr("creport.tactics", a=tactic_name(tac[0]), b=tactic_name(tac[1])) if len(tac) > 1 else tr("creport.tactics1", a=tactic_name(tac[0]))
        lines.append(f'<div class="muted">{esc(txt)}</div>')
    mid = r.get("mid")
    if mid:
        lines.append(f'<div class="muted">{esc(tr("creport.mid", r=mid["rank"], n=mid["n"], a=f"{mid['anger']:.0f}"))}</div>')
    lines += [f'<div class="gold">◆ {esc(trophy_name(t))}</div>' for t in r["trophies"]]
    lines += [f'<div class="award">★ {esc(award_name(a))}</div>' for a in r["awards"]]
    lines += [f'<div class="ev">• {esc(tr("event." + e["t"]))}</div>' for e in r.get("events", [])]
    h.append('<div class="s-cols"><div class="s-l">')            # широкий экран: итоги слева, руководство справа
    h.append(f'<div class="blk"><div class="pad lines">{"".join(lines)}</div></div>')
    # --- руководство
    a, b = r["anger_before"], r["anger_after"]
    v = r.get("verdict")
    bl = [f'<div class="b">{esc(tr("creport.board"))}</div>',
          f'<div class="b" style="font-size:16px;color:{anger_color(b)}">{esc(tr("creport.anger", a=f"{a:.0f}", b=f"{b:.0f}"))}</div>', meter(b)]
    if v != "fired_mid":
        decay = round(a * DECAY - a, 1)
        if decay:
            bl.append(f'<div class="muted">{esc(tr("creport.decay", v=f"{decay:+.0f}"))}</div>')
    for key, val in r["reasons"]:
        if abs(val) < 0.5:
            continue
        cv = theme.RED if val > 0 else theme.ACCENT
        bl.append(f'<div class="kv"><span>{esc(board_reason_text(key, r))}</span><b style="color:{cv}">{val:+.0f}</b></div>')
    bl.append(f'<div class="muted small">{esc(tr("board.pressure", p=r["pressure"]))}</div>')
    msg = tr("creport.fired_mid") if v == "fired_mid" else tr("creport." + v) if v else tr("creport.continue_warn" if b >= 60 else "creport.continue_ok")
    mc = theme.RED if (v or "").startswith("fired") or (not v and b >= 60) else theme.ACCENT if not v else theme.GOLD
    bl.append(f'<div class="b" style="color:{mc}">{esc(msg)}</div>')
    board = f'<div class="panel">{"".join(bl)}</div>'
    fin = r.get("fin")
    money_lines = []
    if fin:
        money_lines.append(f'<div class="muted">{esc(tr("creport.fin", s=eur(fin["spent"]), i=eur(fin["income"]), b=eur(fin["budget"]), p=eur(fin.get("prize", 0.0))))}</div>')
    money_lines += [f'<div class="muted small">• {esc(deal_text(m))}</div>' for m in r.get("moves", [])]
    if money_lines:
        h.append(f'<div class="blk"><div class="pad lines">{"".join(money_lines)}</div></div>')
    sq = squad_events_html(r.get("squad_events") or [])
    if sq:
        h.append(f'<div class="blk"><div class="bh">{esc(tr("sqev.title"))}</div><div class="pad lines">{sq}</div></div>')
    h.append(best_coach_html(r, d))
    h.append(f'</div><div class="s-r">{board}</div></div>')
    h.append(details_html(d, r))
    return '<section class="season">' + "".join(h) + "</section>"

# ---------------------------------------------------------------------- экраны (примесь к WebApp)
class CoachScreens:
    # --- общее: состав, основа, сезоны тренера
    def squad_html(self, sell=False):
        c, d = self.career, self.d
        s = c.coach
        f = s.get("formation", squad_mod.DEFAULT_FORMATION)
        players = squad_mod.squad(c)
        cid = s["club"]
        pw = pot_width(s)
        xi_slot = {p["id"]: slot for slot, p, _ in squad_mod.current_xi(c, f) if p}
        role = squad_mod.roles(c, f)
        offers = (s.get("window") or {}).get("offers", {})
        tw = c.coaching().window() if sell else None
        lc = squad_mod.line_counts(players)
        out = [f'<div class="muted small">{esc(tr("sq.xi", o=f"{squad_mod.team_rating(c, f):.1f}"))} · '
               f'{esc(tr("sq.counts", n=len(players), g=lc["GK"], d=lc["DEF"], m=lc["MID"], a=lc["ATT"]))}</div>']
        trows = []                                     # та же информация таблицей для широкого экрана (как в десктопной версии)
        for ln in squad_mod.LINES:
            group = [p for p in players if squad_mod.LINE[p["pos"]] == ln]
            if not group:
                continue
            rows = []
            for p in sorted(group, key=lambda x: (POS_ORDER.index(x["pos"]), -x["ovr"])):
                starter = p["id"] in xi_slot
                slot = xi_slot.get(p["id"])
                rl = role.get(p["id"], "res")
                role_txt = tr("role.xi_at", s=slot) if starter and slot != p["pos"] else tr("role." + rl)
                role_col = theme.ACCENT if starter else theme.TEXT if rl == "rot" else theme.MUTED
                stt, stc = status_text(p, cid)
                off = offers.get(p["id"])
                if off:
                    stt, stc = tr("sq.offer", club=d.clubs[off["club"]]["name"], fee=eur(off["fee"])), theme.GOLD
                fit = p.get("fit", 100.0)
                fit_col = theme.ACCENT if fit >= 85 else theme.GOLD if fit >= 70 else theme.RED
                name = esc(p["name"]) + (" ★" if p.get("real") else "")
                buttons = ""
                if sell:
                    if p.get("loan_from") and p["loan_from"] != cid:
                        buttons = f'<div class="muted small">{esc(tr("st.loan_until"))}</div>'
                    else:
                        st = tr("tw.sell") + (f" {eur(off['fee'])}" if off else f" · {eur(tw.sale_fee(p))}")
                        buttons = ('<div class="row">' + btn(esc(st), "tw_sell", p["id"], "sm" + (" gold" if off else ""))
                                   + btn(esc(tr("tw.loan_out")), "tw_loan_out", p["id"], "sm") + "</div>")
                rows.append(f'<div class="pl{" xi" if starter else ""}"><b class="ppos">{esc(p["pos"])}</b><div class="pl-m">'
                            f'<div class="{"b" if starter else ""}">{name}</div>'
                            f'<div class="muted small">{p["age"]} · {esc(tr("col.pot"))} {pot_html(p, pw)} · '
                            f'<span style="color:{fit_col}">{fit:.0f}%</span> · {esc(eur(price(p["ovr"], p["age"], p["pot"])))}</div>'
                            f'<div class="small" style="color:{stc or role_col}">{esc(stt or role_txt)}</div>{buttons}</div>'
                            f'<b class="povr">{p["ovr"]:.0f}</b></div>')
                trows.append(f'<tr class="{"xi" if starter else ""}"><td>{esc(p["pos"])}</td><td class="l{" b" if starter else ""}">{name}</td>'
                             f'<td>{p["age"]}</td><td class="b">{p["ovr"]:.0f}</td><td>{pot_html(p, pw)}</td>'
                             f'<td style="color:{fit_col}">{fit:.0f}%</td><td class="muted">{esc(eur(price(p["ovr"], p["age"], p["pot"])))}</td>'
                             f'<td class="l" style="color:{stc or role_col}">{esc(stt or role_txt)}</td>'
                             + (f'<td class="l">{buttons}</td>' if sell else "") + "</tr>")
            out.append(f'<div class="blk m-only"><div class="bh">{esc(tr("line." + ln))} ({len(group)})</div>{"".join(rows)}</div>')
            span = 9 if sell else 8
            trows.insert(len(trows) - len(group), f'<tr class="grp"><td colspan="{span}" class="l">{esc(tr("line." + ln))} ({len(group)})</td></tr>')
        heads = ["pos", "player", "age", "ovr", "pot", "fit", "value", "role"]
        th = "".join(f'<th{" class=l" if k in ("player", "role") else ""}>{esc(tr("col." + k))}</th>' for k in heads) + ("<th></th>" if sell else "")
        out.append(f'<div class="d-only twrap"><table class="tbl wide squad"><thead><tr>{th}</tr></thead><tbody>{"".join(trows)}</tbody></table></div>')
        return "".join(out)

    def lineup_html(self):
        c = self.career
        s = c.coach
        f = s.get("formation", squad_mod.DEFAULT_FORMATION)
        players = squad_mod.squad(c)
        manual = s.get("lineup_mode") == "manual"
        rows = []
        for i, (slot, p, _val) in enumerate(squad_mod.current_xi(c, f)):
            opts = sorted(players, key=lambda x: (not squad_mod.available(x), -(squad_mod.eff(x) - squad_mod.penalty(x["pos"], slot))))
            o = []
            for x in opts:
                e = squad_mod.eff(x) - squad_mod.penalty(x["pos"], slot)
                txt = tr("lineup.option", name=x["name"], pos=x["pos"], ovr=f"{x['ovr']:.0f}", eff=f"{e:.0f}")
                if not squad_mod.available(x):
                    txt += " · " + status_text(x, s["club"])[0]
                sel = " selected" if p and p["id"] == x["id"] else ""
                o.append(f'<option value="{i}|{esc(x["id"])}"{sel}>{esc(txt)}</option>')
            rows.append(f'<div class="slot"><b>{esc(slot)}</b><select data-onchange="lineup_set">{"".join(o)}</select></div>')
        rl = squad_mod.roles(c, f)
        cnt = tr("role.counts", x=sum(1 for v in rl.values() if v == "xi"), r=sum(1 for v in rl.values() if v == "rot"),
                 s=sum(1 for v in rl.values() if v == "res"))
        return (f'<div class="panel"><div class="h2">{esc(tr("lineup.title", f=formation_name(f)))}</div>'
                f'<label class="check"><input type="checkbox" data-onchange="lineup_auto"{"" if manual else " checked"}> {esc(tr("lineup.auto"))}</label>'
                f'{"".join(rows)}<div class="b">{esc(tr("sq.xi", o=f"{squad_mod.team_rating(c, f):.1f}"))}</div><div class="small">{esc(cnt)}</div>'
                f'<div class="muted small">{esc(tr("lineup.hint"))}</div><div class="muted small">{esc(tr("role.hint"))}</div>'
                f'<div class="muted small">{esc(tr("rot.hint"))}</div></div>')

    def coach_seasons_html(self):
        c, d = self.career, self.d
        out = []
        for r in reversed(c.coach.get("seasons") or []):
            tro = [short_trophy(t["code"]) for t in r["trophies"]] + [award_name(a) for a in r["awards"]]
            diff = r["target"] - r["rank"]
            pc = "ok" if diff > 0 else "bad" if diff < -1 else ""
            tac = " → ".join(tactic_name(t) for t in (r.get("tactics") or []) if t)
            vt = verdict_text(r)
            fired = (r.get("verdict") or "").startswith("fired")
            out.append(f'<div class="srow">{logo(d.clubs[r["club"]], 36)}<div class="sr-main">'
                       f'<div><b>{esc(r["season"])}</b> <span class="muted">· {r["age"]}</span> · {esc(d.clubs[r["club"]]["name"])}</div>'
                       f'<div class="muted small">{esc(r["league_name"])} · <span class="{pc}">{r["rank"]}/{r["n"]}</span> '
                       f'({esc(tr("col.target"))} {r["target"]}) · {r["w"]}-{r["d"]}-{r["l"]}</div>'
                       + (f'<div class="muted small">{esc(tac)}</div>' if tac else "")
                       + (f'<div class="gold small">◆ {esc(", ".join(tro))}</div>' if tro else "")
                       + (f'<div class="small {"bad" if fired else "muted"}">{esc(vt)}</div>' if vt else "")
                       + f'</div><div class="sr-num"><div class="small" style="color:{anger_color(r["anger_after"])}">'
                       f'{r["anger_before"]:.0f} → {r["anger_after"]:.0f}</div></div></div>')
        if not out:
            return f'<p class="muted">{esc(tr("end.none"))}</p>'
        return '<div class="srows">' + "".join(out) + "</div>"

    def records_html(self, limit=None):
        rows = records_rows(self.career.coaching().records(), self.d)
        if limit:
            rows = rows[:limit]
        if not rows:
            return ""
        return f'<div class="h2 mt">{esc(tr("rec.title"))}</div>' + kv([(k, v, theme.GOLD) for k, v in rows])

    def tactic_html(self, title, current):
        s = self.career.coach
        radios = "".join(f'<label class="chip-r"><input type="radio" name="tactic" value="{t}" data-partial="tactic"{" checked" if t == current else ""}>'
                         f'<span>{esc(tr("tactic." + t))}</span></label>' for t in TACTICS)
        return (f'<div class="h2">{esc(title)}</div><div class="row">{radios}</div>'
                f'<div class="muted small" id="tactic_hint">{esc(self._tactic_hint(current))}</div>')

    def _tactic_hint(self, t):
        return tr("tactic.hint." + t, r=f"{self.career.coach['rating']:.0f}") if t == "press" else tr("tactic.hint." + t)

    def p_tactic(self):
        t = self.last_form.get("tactic") or "balanced"
        self.ctx["tactic"] = t
        return {"html": {"#tactic_hint": esc(self._tactic_hint(t))}}

    def formation_select(self, act):
        c = self.career
        players = squad_mod.squad(c)
        opts = [(f, tr("formation.item", f=formation_name(f), o=f"{squad_mod.xi_rating(players, f):.1f}")) for f in squad_mod.FORMATIONS]
        return select(act, opts, c.coach.get("formation", squad_mod.DEFAULT_FORMATION), tr("formation.title"))

    def rotation_select(self, act):
        return select(act, [(k, tr("rot." + k)) for k in squad_mod.ROTATION], self.career.coach.get("rotation", "none"), tr("rot.title"))

    # --- предложения тренеру
    def v_coach_offers(self):
        c, d, w, s = self.career, self.d, self.career.world, self.career.coach
        body = (f'<p class="muted">{esc(tr("coach.reason." + (s.get("offer_reason") or "start")))}</p>'
                f'<p class="gold">{esc(tr("coach.you", r=f"{s['rating']:.0f}", p=f"{s['rep']:.0f}", a=c.player.age))}</p>')
        for i, o in enumerate(s["offers"]):
            lg = w.league_of(o["club"])
            lines = [tr("coach.target", t=kind_text(o["kind"])), tr("coach.patience", p=patience_text(o["pressure"])),
                     tr("coach.years", n=o["years"]), tr("coach.team", o=round(w.team_ovr(o["club"]))),
                     tr("coach.offer_budget", b=eur(annual_budget(w, o["club"]))),
                     tr("coach.club_formation", f=formation_name(squad_mod.club_formation(o["club"])))]
            tags, good = [], True
            if o["project"] == "rebuild":
                tags.append(tr("coach.rebuild_tag"))
            rt, rgood = rel_tag(o.get("rel", 0))
            if rt:
                tags.append(rt); good = good and rgood
            body += club_card(d.clubs[o["club"]], f"{lg['name']} · {d.country_name(lg['country'], i18n.LANG)}", w.stars(o["club"]), lines,
                              esc(tr("coach.choose")), "coach_accept", str(i), tag=" · ".join(tags) or None, tag_home=good)
        footer = btn(esc(tr("coach.retire")), "coach_retire", kind="danger")
        if s.get("can_stay") and s.get("club"):
            footer += btn(esc(tr("coach.stay", club=d.clubs[s["club"]]["name"])), "coach_accept", "stay", "primary")
        return self.screen(esc(tr("coach.offers_title")), body, footer, left=self.menu_btn())

    def a_coach_accept(self, arg):
        self.career.coaching().accept("stay" if arg == "stay" else int(arg)); self.save(); self.go("coach")

    def a_coach_retire(self, _):
        self.modal = {"title": tr("app.title"), "text": tr("coach.retire_q"),
                      "buttons": [(tr("no"), "modal_close", "", ""), (tr("yes"), "coach_retire_yes", "", "danger")]}

    def a_coach_retire_yes(self, _):
        self.career.coaching().retire(); self.save(); self.go("end", tab="coach")

    # --- клуб тренера
    def v_coach(self):
        c, d, w, s = self.career, self.d, self.career.world, self.career.coach
        cid = s["club"]; cl = d.clubs[cid]; lg = w.league_of(cid)
        cc = c.coaching()
        rank, n, kind = cc.expected(cid)
        head = (f'<div class="panel club-h">{logo(cl, 56)}<div><div class="h2">{esc(cl["name"])}</div>'
                f'<div class="muted small">{esc(tr("coach.header_sub", league=lg["name"], country=d.country_name(lg["country"], i18n.LANG), stars=stars_text(w.stars(cid)), ovr=round(w.team_ovr(cid))))}</div>'
                f'<div class="gold small">{esc(c.name)} · {esc(tr("career.age", n=c.player.age))}</div></div></div>')
        info = kv([(tr("coach.info_rating"), f"{s['rating']:.0f}"), (tr("coach.info_rep"), f"{s['rep']:.0f}"),
                   (tr("coach.budget"), eur(s.get("budget", 0.0))), (tr("coach.info_contract"), tr("coach.years_left", n=s["contract_left"])),
                   (tr("coach.info_project"), tr("coach.project." + s["project"])),
                   (tr("coach.info_target"), tr("coach.target_place", t=kind_text(kind), r=rank, n=n))])
        anger = (f'<div class="panel"><div class="h2">{esc(tr("coach.anger"))}</div>{meter(s["anger"])}'
                 f'<div class="muted small">{esc(tr("coach.anger_hint"))} · {esc(tr("coach.patience", p=patience_text(pressure(w.score[cid], s["project"]))))}</div></div>')
        tactic = self.ctx.get("tactic") or s.get("tactic", "balanced")
        setup = (f'<div class="panel">{self.formation_select("c_formation")}{self.rotation_select("c_rotation")}'
                 f'{self.tactic_html(tr("tactic.title"), tactic)}</div>')
        tab = self.ctx.get("tab") or "squad"
        tabs = chips("ctab", [("squad", tr("tab.squad")), ("lineup", tr("tab.lineup")), ("seasons", tr("tab.seasons"))], tab)
        if tab == "squad":
            content = self.squad_html()
        elif tab == "lineup":
            content = self.lineup_html()
        else:
            content = self.coach_seasons_html() + self.records_html(4)
        body = (head.replace('class="panel club-h"', 'class="panel club-h a-head"', 1) + f'<div class="a-left">{info}{anger}{setup}</div>'
                + f'<div class="a-right">{tabs}{content}<p class="muted small">{esc(tr("career.autosave"))}</p></div>')
        footer = btn(esc(tr("coach.retire")), "coach_retire", kind="danger") + btn(esc(tr("coach.play_half")), "coach_play", kind="primary")
        return self.screen(esc(cl["name"]), body, footer, left=self.menu_btn())

    def a_ctab(self, tab):
        self.ctx["tab"] = tab

    def a_c_formation(self, f):
        self.career.coach["formation"] = f
        squad_mod.apply_to_world(self.career)

    def a_c_rotation(self, r):
        self.career.coach["rotation"] = r
        squad_mod.apply_to_world(self.career)

    def a_lineup_set(self, arg):
        i, pid = arg.split("|", 1)
        squad_mod.set_lineup(self.career, int(i), pid)
        squad_mod.apply_to_world(self.career)

    def a_lineup_auto(self, on):
        s = self.career.coach
        if on == "1":
            s["lineup_mode"] = "auto"
        else:                                          # вручную: начинаем с нынешней основы
            f = s.get("formation", squad_mod.DEFAULT_FORMATION)
            s.setdefault("lineup", {})[f] = [p["id"] if p else None for _, p, _ in squad_mod.current_xi(self.career, f)]
            s["lineup_mode"] = "manual"
        squad_mod.apply_to_world(self.career)

    def _tactic_from_form(self):
        return self.last_form.get("tactic") or self.ctx.get("tactic") or self.career.coach.get("tactic", "balanced")

    def a_coach_play(self, _):
        """Перед сезоном - летнее трансферное окно, затем первая половина сезона."""
        self.career.coach["tactic"] = self._tactic_from_form()
        self.career.coaching().window().open("summer")
        self.go("transfer", then="first_half")

    # --- трансферное окно
    def v_transfer(self):
        c, d, s = self.career, self.d, self.career.coach
        win, cid = s["window"], s["club"]
        tw = c.coaching().window()
        team, start = tw.rating(), win["start_ovr"]
        rank, n, kind = c.coaching().expected(cid)
        tl = tr("tw.team_change", a=f"{start:.1f}", b=f"{team:.1f}") if abs(team - start) > 0.05 else tr("tw.team", o=f"{team:.1f}")
        head = (f'<div class="panel"><div class="h2 gold">{esc(tr("tw.budget", b=eur(s["budget"])))}</div><div class="b">{esc(tl)}</div>'
                f'<div class="muted small">{esc(tr("tw.target", t=kind_text(kind), r=rank))}</div>{self.formation_select("tw_formation")}</div>')
        notes = []
        if win.get("academy"):
            notes.append(tr("tw.academy_new", n=", ".join(f"{a['name']} ({a['pos']}, {a['ovr']:.0f})" for a in win["academy"])))
        if win.get("refused"):
            notes.append(tr("tw.refused_n", n=win["refused"]))
        if win.get("returned"):
            notes.append(tr("tw.returned", n=", ".join(f"{a['name']} ({a['pos']}, {a['ovr']:.0f})" for a in win["returned"])))
        if win.get("loans_ended"):
            notes.append(tr("tw.loans_ended", n=", ".join(f"{a['name']} ({a['pos']}, {a['ovr']:.0f})" for a in win["loans_ended"])))
        if tw.squad_full():
            notes.append(tr("tw.full", n=squad_mod.MAX_SQUAD))
        if win["log"]:
            notes.append(tr("tw.deals") + ": " + "; ".join(deal_text(m) + (f" ({m['d']:+.1f})" if m.get("d") else "") for m in win["log"]))
        notes_html = "".join(f'<p class="muted small">{esc(x)}</p>' for x in notes)
        tab = win.get("wtab") or "market"
        n_lo = sum(1 for o in win.get("loan_offers", []) if not o["done"])
        players = squad_mod.squad(c)
        tabs = chips("tw_tab", [("market", tr("tw.tab_market")), ("squad", tr("tw.squad") + f" ({len(players)})"), ("lineup", tr("tab.lineup")),
                                ("loans", tr("tw.tab_loans") + (f" ({n_lo})" if n_lo else "")),
                                ("scouts", tr("tw.tab_scouts") + f" ({len(s.get('scouts') or [])})")], tab)
        content = {"market": self.market_html, "squad": lambda: self.squad_html(sell=True), "lineup": self.lineup_html,
                   "loans": self.loans_html, "scouts": self.scouts_html}[tab]()
        body = head + notes_html + tabs + content + f'<p class="muted small">{esc(tr("tw.hint"))}</p>'
        title = tr("tw." + win["kind"], y=c.year if win["kind"] == "summer" else c.year + 1)
        return self.screen(esc(title), body, btn(esc(tr("tw.done")), "tw_done", kind="primary", extra="data-busy"))

    def market_html(self):
        c, d, s = self.career, self.d, self.career.coach
        win = s["window"]
        tw = c.coaching().window()
        pw = pot_width(s)
        full = tw.squad_full()
        filt = win.get("filter", "")
        idx = [i for i, cd in enumerate(win["cands"]) if not filt or squad_mod.LINE[cd["pos"]] == filt]
        gains = {i: (tw.gain(cd) if not cd["done"] else 0.0) for i, cd in enumerate(win["cands"])}
        sort = win.get("sort")
        if sort:
            col, st = sort
            keys = {0: lambda cd, i: cd["name"].lower(), 1: lambda cd, i: POS_ORDER.index(cd["pos"]), 2: lambda cd, i: cd["age"],
                    3: lambda cd, i: cd["ovr"], 4: lambda cd, i: pot_key(cd, pw), 6: lambda cd, i: cd["price"], 7: lambda cd, i: gains[i]}
            if col in keys:
                idx.sort(key=lambda i: keys[col](win["cands"][i], i), reverse=(st == 1))
        cur_sort = next((k for k, col, _ in SORTS if sort and sort[0] == col), "")
        filters = chips("tw_filter", [("", tr("filter.all"))] + [(ln, tr("line." + ln)) for ln in squad_mod.LINES], filt)
        sort_sel = select("tw_sort", [("", tr("web.sort_default"))] + [(k, tr("web.sort_" + k)) for k, _, _ in SORTS], cur_sort, tr("web.sort"))
        out = [f'<div class="muted small">{esc(tr("tw.scouting", q=f"{100 * scouting(s):.0f}", w=pw))}</div>',
               f'<div class="mk-tools">{filters}{sort_sel}</div>']
        cards, trows = [], []
        for i in idx:
            cd = win["cands"][i]
            real = bool(cd.get("pid")) and bool((stars_mod.find(c.stars, cd["pid"]) or {}).get("real"))
            club = d.clubs[cd["club"]]["name"] if cd.get("club") else tr("tw.free_agent")
            if cd.get("loan"):
                club = tr("tw.loan_from", club=club)
            g = gains[i]
            ok = not cd["done"] and not cd.get("refuse") and cd["price"] <= s["budget"] + 1e-9 and not full
            ncls = "award b" if cd.get("pid") else "ok b" if cd.get("gem") else "b"
            name = esc(cd["name"]) + (" ★" if real else "") + (" ◆" if cd.get("gem") else "")
            eff = f'<span class="ok">+{g:.1f}</span>' if g >= 0.05 else '<span class="muted">—</span>'
            if cd.get("refuse") and not cd["done"]:
                b = f'<div class="muted small">{esc(tr("tw.refuse"))}: {esc(tr("tw.refuse_tip"))}</div>'
            else:
                buy_txt = tr("tw.loan_take") if cd.get("loan") else tr("tw.buy")
                txt = tr("tw.bought") if cd["done"] else buy_txt if ok else (tr("tw.no_money") if cd["price"] > s["budget"] else buy_txt)
                b = btn(esc(txt), "tw_buy", str(i), "sm" + (" btn-primary" if ok else ""), "" if ok else "disabled")
            cards.append(f'<div class="pl"><b class="ppos">{esc(cd["pos"])}</b><div class="pl-m"><div class="{ncls}">{name}</div>'
                         f'<div class="muted small">{cd["age"]} · {esc(tr("col.pot"))} {pot_html(cd, pw)} · {esc(club)}</div>'
                         f'<div class="small"><span class="gold">{esc(eur(cd["price"]))}</span> · {esc(tr("col.effect"))} {eff}</div>{b}</div>'
                         f'<b class="povr">{cd["ovr"]:.0f}</b></div>')
            trows.append(f'<tr><td class="l {ncls}">{name}</td><td>{esc(cd["pos"])}</td><td>{cd["age"]}</td><td class="b">{cd["ovr"]:.0f}</td>'
                         f'<td>{pot_html(cd, pw)}</td><td class="l muted">{esc(club)}</td><td class="gold">{esc(eur(cd["price"]))}</td>'
                         f'<td>{eff}</td><td class="l">{b}</td></tr>')
        th = "".join(f'<th{" class=l" if k in ("player", "club") else ""}>{esc(tr("col." + k))}</th>'
                     for k in ("player", "pos", "age", "ovr", "pot", "club", "price", "effect")) + "<th></th>"
        out.append(f'<div class="m-only mk-cards">{"".join(cards)}</div>'
                   f'<div class="d-only twrap"><table class="tbl wide"><thead><tr>{th}</tr></thead><tbody>{"".join(trows)}</tbody></table></div>')
        if win["youth"]:
            out.append(f'<div class="h2 mt">{esc(tr("tw.youth"))}</div>')
            for i, y in enumerate(win["youth"]):
                ok = not y["done"] and y["price"] <= s["budget"] + 1e-9 and not (y["kind"] == "talent" and full)
                if y["kind"] == "talent":
                    yp = {"age": 17, "ovr": y["ovr"], "pot": y["pot"], "name": y["name"]}
                    info = (f'<div class="b">{esc(tr("tw.youth_talent", name=y["name"]))}</div>'
                            f'<div class="muted small">{esc(y["pos"])} · 17 · OVR {y["ovr"]:.0f} · {esc(tr("col.pot"))} {pot_html(yp, pw)}</div>')
                else:
                    info = f'<div class="b">{esc(tr("tw.academy"))}</div><div class="muted small">{esc(tr("tw.academy_line"))}</div>'
                txt = tr("tw.bought") if y["done"] else tr("tw.buy")
                out.append(f'<div class="pl"><div class="pl-m">{info}<div class="gold small">{esc(eur(y["price"]))}</div>'
                           + btn(esc(txt), "tw_youth", str(i), "sm" + (" btn-primary" if ok else ""), "" if ok else "disabled") + "</div></div>")
        return '<div class="blk mk">' + "".join(out) + "</div>"

    def loans_html(self):
        c, d = self.career, self.d
        win, cid = c.coach["window"], c.coach["club"]
        pw = pot_width(c.coach)
        out = [f'<div class="h2">{esc(tr("tw.loan_offers"))}</div>']
        offers = win.get("loan_offers") or []
        rows = []
        for i, o in enumerate(offers):
            p = stars_mod.find(c.stars, o["pid"])
            if not p:
                continue
            ok = not o["done"] and p["club"] == cid
            txt = tr("tw.loan_done") if o["done"] else tr("tw.loan_accept")
            rows.append(f'<div class="pl"><b class="ppos">{esc(p["pos"])}</b><div class="pl-m"><div class="b">{esc(p["name"])}</div>'
                        f'<div class="muted small">{p["age"]} · {esc(tr("col.pot"))} {pot_html(p, pw)} · {esc(d.clubs[o["club"]]["name"])}</div>'
                        f'<div class="gold small">{esc(eur(o["fee"]))}</div>'
                        + btn(esc(txt), "tw_loan_offer", str(i), "sm" + (" btn-primary" if ok else ""), "" if ok else "disabled")
                        + f'</div><b class="povr">{p["ovr"]:.0f}</b></div>')
        out.append('<div class="blk">' + "".join(rows) + "</div>" if rows else f'<p class="muted small">{esc(tr("tw.no_loan_offers"))}</p>')
        away = [p for p in stars_mod.all_players(c.stars) if p.get("loan_from") == cid and p["club"] != cid]
        out.append(f'<div class="h2 mt">{esc(tr("tw.on_loan"))}</div>')
        if away:
            out += [f'<p class="small">{esc(tr("tw.on_loan_row", n=p["name"], pos=p["pos"], o=f"{p['ovr']:.0f}", club=d.clubs[p["club"]]["name"], m=round(100 * p.get("loan_min", 0.5))))}</p>'
                    for p in away]
        else:
            out.append(f'<p class="muted">{esc(tr("end.none"))}</p>')
        out.append(f'<p class="muted small">{esc(tr("tw.loan_hint"))}</p>')
        return "".join(out)

    def scouts_html(self):
        s = self.career.coach
        win = s["window"]
        mine = s.get("scouts") or []
        def rows(items, label, enabled, act):
            out = []
            for i, x in enumerate(items):
                ok = enabled(x)
                out.append(f'<div class="pl"><div class="pl-m"><div class="b">{esc(x["name"])} <span class="gold">{"★" * x["stars"]}</span></div>'
                           f'<div class="muted small">{esc(tr("sc.rating"))} {x["rating"]} · {esc(tr("sc.salary"))} {esc(eur(x["salary"]))}</div>'
                           + btn(esc(label(x)), act, str(i), "sm", "" if ok else "disabled") + "</div></div>")
            return '<div class="blk">' + "".join(out) + "</div>"
        out = [f'<div class="h2">{esc(tr("sc.mine", n=len(mine), m=MAX_SCOUTS))}</div>']
        out.append(rows(mine, lambda x: tr("sc.fire"), lambda x: True, "tw_fire") if mine else f'<p class="muted small">{esc(tr("sc.none"))}</p>')
        market = win.get("scout_market") or []
        if market:
            full = len(mine) >= MAX_SCOUTS
            out.append(f'<div class="h2 mt">{esc(tr("sc.market"))}</div>')
            out.append(rows(market, lambda x: tr("sc.hired") if x["done"] else tr("sc.hire"),
                            lambda x: not x["done"] and not full and x["salary"] <= s["budget"] + 1e-9, "tw_hire"))
        elif win["kind"] == "winter":
            out.append(f'<p class="muted small">{esc(tr("sc.summer_only"))}</p>')
        out.append(f'<p class="muted small">{esc(tr("sc.hint"))}</p>')
        return "".join(out)

    def _tw(self):
        return self.career.coaching().window()

    def a_tw_tab(self, tab):
        self.career.coach["window"]["wtab"] = tab

    def a_tw_filter(self, ln):
        self.career.coach["window"]["filter"] = ln

    def a_tw_sort(self, key):
        sort = next(((col, 1 if desc else 2) for k, col, desc in SORTS if k == key), None)
        self.career.coach["window"]["sort"] = list(sort) if sort else None

    def a_tw_formation(self, f):
        self.career.coach["formation"] = f

    def a_tw_buy(self, i):
        self._tw().buy(int(i))

    def a_tw_youth(self, i):
        self._tw().youth(int(i))

    def a_tw_sell(self, pid):
        self._tw().sell(pid)

    def a_tw_loan_out(self, pid):
        self._tw().loan_out(pid)

    def a_tw_loan_offer(self, i):
        self._tw().accept_loan_offer(int(i))

    def a_tw_hire(self, i):
        self._tw().hire_scout(int(i))

    def a_tw_fire(self, i):
        self._tw().fire_scout(int(i))

    def a_tw_done(self, _):
        if self.ctx.get("then") == "first_half":
            mid = self.career.coaching().begin_season(self.career.coach["tactic"])
            self.go("mid", mid=mid)
        else:                                          # зимнее окно: обратно в середину сезона
            self.go("mid", mid=self.career._coach_pending["mid"])

    # --- середина сезона
    def v_mid(self):
        c, d, s = self.career, self.d, self.career.coach
        mid = self.ctx["mid"]
        cid = s["club"]
        msg = tr("mid.fired") if mid["fired"] else tr("mid.warn") if mid["anger"] >= 70 else tr("mid.ok")
        mc = theme.RED if mid["fired"] or mid["anger"] >= 70 else theme.ACCENT
        # широкий экран (как в десктопной версии): сверху итог половины | тактика, снизу события и таблица | основа
        top = (f'<div class="panel"><div class="h2">{esc(tr("mid.place", r=mid["rank"], n=mid["n"], t=kind_text(mid["kind"]), e=mid["target"]))}</div>'
               f'<div>{esc(tr("mid.anger", a=f"{mid['anger_before']:.0f}", b=f"{mid['anger']:.0f}"))}</div>{meter(mid["anger"])}'
               f'<div class="b" style="color:{mc}">{esc(msg)}</div></div>')
        left, right = "", ""
        if not mid["fired"]:
            tactic = self.ctx.get("tactic") or s.get("tactic", "balanced")
            top += (f'<div class="panel">{self.tactic_html(tr("mid.second_half"), tactic)}{self.formation_select("m_formation")}'
                    f'{self.rotation_select("m_rotation")}</div>')
            ev = squad_events_html(mid.get("squad_events") or [])
            if ev:
                left += f'<div class="blk"><div class="bh">{esc(tr("sqev.title"))}</div><div class="pad lines">{ev}</div></div>'
            right = f'<details class="panel dopen"><summary class="b">{esc(tr("tab.lineup"))}</summary>{self.lineup_html()}</details>'
        lg = d.leagues[mid["lid"]]
        x = {"name_ru": f"{tr('mid.table')}: {lg['name']}", "name_en": f"{tr('mid.table')}: {lg['name']}", "table": mid["table"],
             "result": {"rank": mid["rank"], "n": mid["n"], "pts": next(r[6] for r in mid["table"] if r[0] == cid)}}
        left += '<div class="blk">' + league_table_html(x, d, cid).replace("<details", "<details open", 1) + "</div>"
        body = f'<div class="m-top">{top}</div><div class="m-bot"><div class="s-l">{left}</div><div class="s-r">{right}</div></div>'
        footer = ""
        if not mid["fired"]:
            footer += btn(esc(tr("tw.winter_btn")), "mid_winter")
        footer += btn(esc(tr("mid.continue_fired") if mid["fired"] else tr("mid.continue")), "mid_done", kind="primary", extra="data-busy")
        return self.screen(esc(tr("mid.title", s=season_label(c.year))), body, footer)

    def a_m_formation(self, f):
        self.career.coach["formation"] = f
        squad_mod.apply_to_world(self.career)

    def a_m_rotation(self, r):
        self.career.coach["rotation"] = r

    def a_mid_winter(self, _):
        self.career.coach["tactic"] = self._tactic_from_form()
        self.career.coaching().window().open("winter")
        self.go("transfer", then="mid")

    def a_mid_done(self, _):
        tactic = "" if self.ctx["mid"]["fired"] else self._tactic_from_form()
        rec = self.career.coaching().finish_season(tactic or None)
        self.save()
        self.go("creport", rec=rec)

    # --- итоги сезона тренера
    def v_creport(self):
        rec = self.ctx["rec"]
        return self.screen(esc(tr("creport.title", s=rec["season"])), coach_season_html(self.career, self.d, rec),
                           btn(esc(tr("report.continue")), "creport_done", kind="primary"))

    def a_creport_done(self, _):
        st = self.career.status
        if st == "coaching":
            self.go("coach")
        elif st == "coach_offers":
            self.go("coach_offers")
        else:
            self.go("end", tab="coach")

    # --- вкладки итогов карьеры
    def end_coach(self, rep):
        c, d = self.career, self.d
        s = c.coach
        sm = c.coaching().summary()
        best = sm["best"]
        spells = []
        for sp in s["spells"]:
            end = tr("spell." + (sp.get("end") or "now"))
            spells.append(f"{d.clubs[sp['club']]['name']} ({sp['from']}–{sp['to'] or sp['from']}, {end})")
        rows = [(tr("end.coach_seasons"), sm["seasons"]), (tr("end.coach_record"), f"{sm['w']}-{sm['d']}-{sm['l']} ({sm['pct']}%)"),
                (tr("end.coach_titles"), sm["titles"]),
                (tr("end.coach_trophies"), " · ".join(f"{tr('end.cat.' + k)}: {v}" for k, v in sm["trophy_cats"].items()) or tr("end.none")),
                (tr("end.coach_best"), f"{best[0]} ({best[1]}, {d.clubs[best[2]]['name']})" if best else "—"),
                (tr("end.coach_fired"), sm["fired"]), (tr("end.coach_rating"), f"{s['rating']:.0f}"),
                (tr("end.coach_clubs"), " → ".join(spells) or tr("end.none"))]
        return kv(rows) + self.records_html()

    def end_coach_seasons(self, rep):
        return self.coach_seasons_html()
