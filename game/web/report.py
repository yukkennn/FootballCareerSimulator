"""Отчёт о сезоне для узкого экрана: блоки идут друг под другом, таблицы компактные."""
from html import escape
from .. import i18n
from ..i18n import tr
from ..text import (trophy_name, stage, event_text, intl_line, lang_name, club_result, nat_comp_name, nat_result, group_line,
                    season_award_names, score_text, chronicle_text)
from ..ui import theme
from .parts import esc

def _club(d, cid):
    c = d.clubs.get(cid)
    return escape(c["name"]) if c else escape(str(cid))

def _table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    return f'<table class="tbl {cls}"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table>'

def _tr(cells, cls=""):
    return f'<tr class="{cls}">' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

def league_table_html(x, d, me):
    t = x.get("table")
    if not t:
        return ""
    rows = []
    for i, (cid, w, dr, l, gf, ga, pts) in enumerate(t, 1):
        cls = "me" if cid == me else ("first" if i == 1 else "")
        rows.append(_tr([i, _club(d, cid), w + dr + l, f"{w}-{dr}-{l}", f"{gf}:{ga}", f"<b>{pts}</b>"], cls))
    r = x["result"]
    cap = tr("tbl.league_caption", r=r["rank"], n=r["n"], pts=r["pts"])
    head = ["#", tr("col.club"), tr("tbl.p"), f'{tr("tbl.w")}-{tr("tbl.d")}-{tr("tbl.l")}', tr("tbl.goals"), tr("tbl.pts")]
    return (f'<details class="sub"><summary>{esc(lang_name(x))} · <span class="{"gold" if r["rank"] == 1 else "muted"}">{esc(cap)}</span></summary>'
            + _table(head, rows, "league") + "</details>")

def _stage_table_html(x, d, me):
    t, r = x.get("table"), x["result"]
    if not t:
        return ""
    lp = len(t) > 8
    rows = []
    for i, (cid, pts, gd) in enumerate(t, 1):
        zone = ("z-top" if i <= 8 else "z-po" if i <= 24 else "z-out") if lp else ("z-top" if i <= 2 else "")
        rows.append(_tr([i, _club(d, cid), f"<b>{pts}</b>", f"{gd:+d}"], "me" if cid == me else zone))
    cap = tr("tbl.lp_caption", r=r["lp_rank"], n=r["lp_n"], pts=r["lp_pts"]) if lp and "lp_rank" in r else \
          tr("tbl.group_caption", g=r.get("group", "?"), p=r.get("gpos", "?")) if "gpos" in r else ""
    legend = f'<div class="cap">{esc(tr("tbl.lp_legend"))}</div>' if lp else ""
    return _table(["#", tr("col.club"), tr("tbl.pts"), "+/−"], rows) + (f'<div class="cap">{esc(cap)}</div>' if cap else "") + legend

def cup_path_html(x, d, me):
    r = x["result"]
    path = list(r.get("path") or [])
    if not path and r.get("vs"):
        path = [{"stage": r.get("stage") if r.get("stage") != "W" else "F", "vs": r["vs"], "score": r.get("score"), "won": r.get("won", r.get("stage") == "W")}]
    body = _stage_table_html(x, d, me)
    if path:
        rows = []
        for p in path:
            if p["won"] and p["stage"] == "F":
                mark = f'<span class="gold b">◆ {esc(tr("tbl.won_final"))}</span>'
            elif p["won"]:
                mark = f'<span class="ok">{esc(tr("tbl.through"))}</span>'
            else:
                mark = f'<span class="bad">{esc(tr("tbl.out"))}</span>'
            rows.append(_tr([esc(stage(p["stage"]).capitalize()), _club(d, p["vs"]), esc(score_text(p["score"])), mark]))
        body += _table([tr("tbl.round"), tr("tbl.opponent"), tr("tbl.score"), ""], rows, "path")
    won = r.get("stage") == "W"
    res = esc(club_result(x, d))
    return (f'<details class="sub"><summary>{esc(lang_name(x))} · <span class="{"gold" if won else "muted"}">{res}</span></summary>'
            + body + "</details>")

def details_html(d, s):
    comps = s.get("comps") or []
    me = s["club"]
    lg = [league_table_html(x, d, me) for x in comps if x["code"] in ("league", "youth") and not x.get("senior")]
    cups = [cup_path_html(x, d, me) for x in comps if x["code"] not in ("league", "youth") and (x["result"].get("path") or x["result"].get("vs") or x.get("table"))]
    lg, cups = [p for p in lg if p], [p for p in cups if p]
    if not lg and not cups:
        return ""
    # на широком экране: таблица лиги слева, кубки справа (как в десктопной версии)
    return (f'<div class="blk s-full"><div class="bh">{esc(tr("web.details"))}</div>'
            f'<div class="dt"><div class="dt-l">{"".join(lg)}</div><div class="dt-r">{"".join(cups)}</div></div></div>')

def ballon_html(b, d):
    rows = []
    for i, x in enumerate(b["top"], 1):
        me = x.get("me")
        if i > 5 and not me:
            continue
        who = tr("bdo.you") if me else x["name"]
        club = d.clubs[x["club"]]["name"] if x["club"] in d.clubs else ""
        name = f'<b>{esc(who)}</b><br><span class="muted small">{esc(club)} · {esc(d.country_name(x["nat"], i18n.LANG))}</span>'
        rows.append(_tr([i, name, f'<b>{esc(x["pos"])}</b>', x["goals"], x["assists"]], "me" if me else ""))
    r = b.get("rank")
    if r == 1:
        foot = f'<div class="gold b">{esc(tr("bdo.you_won"))}</div>'
    elif r:
        foot = f"<div>{esc(tr('bdo.place', r=r))}</div>"
        if b.get("ahead"):
            foot += f'<div class="muted">{esc(tr("bdo.ahead", names=", ".join(x["name"] for x in b["ahead"])))}</div>'
    else:
        foot = f'<div class="muted">{esc(tr("bdo.not_nominated"))}</div>'
    head = ["#", tr("bdo.col_player"), tr("bdo.col_pos"), tr("col.go"), tr("col.a")]
    return f'<div class="ballon"><div class="gold b">{esc(tr("bdo.title", y=b["year"]))}</div>{_table(head, rows, "bdo")}{foot}</div>'

def season_html(c, d, s, open_details=False):
    gk = c.pos == "GK"
    h = []
    lg = f"{s['league_name']} ({d.country_name(s['league_country'], i18n.LANG)})"
    h.append(f'<div class="season-h"><div class="h2">{esc(tr("report.season", s=s["season"]))}</div>'
             f'<div class="muted small">{esc(tr("career.age", n=s["age"]))} · {esc(s["club_name"])} '
             f'{esc(tr("report.loan_tag")) if s["loan"] else ""} · {esc(lg)}</div></div>')
    if s["youth"]:
        h.append(f'<div class="muted small pad">{esc(tr("report.youth_note"))}</div>')
    # --- клуб: по турнирам
    head = [tr("col.comp"), tr("col.g"), tr("col.csh") if gk else tr("col.go")] + ([] if gk else [tr("col.a")])
    rows = []
    for x in s.get("comps", []):
        won = x["result"].get("stage") == "W" or (x["code"] in ("league", "youth") and x["result"].get("rank") == 1)
        name = esc(lang_name(x)) + (f' <span class="muted">({esc(tr("report.senior_tag"))})</span>' if x.get("senior") else "")
        res = f'<div class="res {"gold" if won else "muted"}">{esc(club_result(x, d))}</div>'
        rows.append(_tr([name + res, x["games"], x["cs"] if gk else x["goals"]] + ([] if gk else [x["assists"]])))
    rows.append(_tr([f"<b>{esc(tr('report.club_total'))}</b>", f"<b>{s['games']}</b>", f"<b>{s['cs'] if gk else s['goals']}</b>"]
                    + ([] if gk else [f"<b>{s['assists']}</b>"]), "total"))
    extra = [tr("report.ovr", a=s["ovr"], b=s["ovr_end"])]
    if s.get("rating"):
        extra.append(tr("report.rating", r=f"{s['rating']:.2f}"))
    h.append('<div class="s-cols"><div class="s-l">')          # широкий экран: клуб и сборная слева, трофеи и события справа
    h.append(f'<div class="blk">{_table(head, rows, "comps")}<div class="muted small pad">{esc(" · ".join(extra))}</div></div>')
    # --- сборная
    if s.get("nat_comps"):
        intl = s["intl"] or {}
        called = intl.get("called")
        nrows = []
        for e in s["nat_comps"]:
            if e["kind"] == "friendly" and not e["games"]:
                continue
            won = (e["kind"] == "final" and e["info"].get("stage") == "W") or (e["kind"] == "unl" and (
                (e["info"].get("finals") or {}).get("stage") == "W" or (e["info"].get("move") or {}).get("dir") == "up"))
            res = nat_result(e, d)
            gl = group_line(e, d)
            cell = esc(nat_comp_name(e, d))
            if res:
                cell += f'<div class="res {"gold" if won else "muted"}">{esc(res)}</div>'
            if gl:
                cell += f'<div class="muted small">{esc(gl)}</div>'
            nrows.append(_tr([cell, e["games"] if called else "—", "" if gk else (e["goals"] if called else "")]
                             + ([] if gk else [e["assists"] if called else ""])))
        sub = tr("report.nat_called") if called else tr("report.nat_not_called")
        body = _table(head, nrows, "comps") if nrows else ""
        if called:
            body += f'<div class="pad">{esc(intl_line(intl["caps"], intl["goals"], intl["assists"]))}</div>'
        h.append(f'<div class="blk"><div class="bh">{esc(tr("report.nat_title", c=d.country_name(c.nat, i18n.LANG)))}'
                 f' <span class="muted small">· {esc(sub)}</span></div>{body}</div>')
    # --- трофеи, награды, Золотой мяч, события
    hon = []
    for t in s["trophies"]:
        cls = "nat" if t["cat"] == "national" else "gold"
        hon.append(f'<div class="{cls}">◆ {esc(trophy_name(t))}</div>')
    if not s["trophies"]:
        hon.append(f'<div class="muted">{esc(tr("report.no_trophies"))}</div>')
    hon += [f'<div class="award">★ {esc(a)}</div>' for a in season_award_names(s)]
    h.append('</div><div class="s-r">')
    h.append(f'<div class="blk"><div class="bh">{esc(tr("report.honours"))}</div><div class="pad lines">{"".join(hon)}</div></div>')
    if s.get("ballon"):
        h.append(ballon_html(s["ballon"], d))
    ev = [f'<div class="ev">• {esc(event_text(e))}</div>' for e in s["events"]]
    ev += [f"<div>▸ {esc(chronicle_text(e, d))}</div>" for e in s.get("chronicle") or []]
    if ev:
        h.append(f'<div class="blk"><div class="bh">{esc(tr("chron.title"))}</div><div class="pad lines">{"".join(ev)}</div></div>')
    h.append("</div></div>")
    h.append(details_html(d, s))
    return '<section class="season">' + "".join(h) + "</section>"
