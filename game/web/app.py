"""Веб-приложение: состояние экранов и действия игрока. Работает в браузере (Pyodide), повторяет навигацию MainWindow.

app.js вызывает три метода:
  render()                  -> HTML текущего экрана;
  act(name, arg, form_json) -> JSON {html, toast, download, scroll} после действия (нажатие кнопки с data-act);
  partial(name, form_json)  -> JSON {html: {id: html}, set: {поле: значение}} - точечное обновление без перерисовки экрана.
"""
import json, random, time, traceback
from .. import i18n, saves
from ..i18n import tr
from ..career import Career, market_value
from ..data import GameData
from ..positions import TYPICAL_HEIGHT, HEIGHT_MIN, HEIGHT_MAX, LEFT_SIDE, RIGHT_SIDE
from ..stars import gen_name
from .. import stars as stars_mod
from ..text import (money, trophy_name, stars_text, short_trophy, lang_name, club_result, nat_comp_name, nat_result, award_name,
                    season_award_names, chronicle_text)
from ..ui import theme
from .parts import esc, btn, logo, player_card, ovr_chart, club_card, kv
from .report import season_html
from .coach import CoachScreens
from .. import story as story_mod
import html as _html, re

POS_GROUPS = [("gk", ["GK"]), ("def", ["CB", "LB", "RB"]), ("mid", ["CDM", "CM", "CAM", "LM", "RM"]), ("att", ["LW", "RW", "CF", "ST"])]

def pos_text(pos):
    return f"{pos} · {tr('pos.' + pos)}"

def youth_league_name(s):
    c = (s.get("comps") or [None])[0]
    if s["youth"] and c and c.get("code") == "youth":
        return lang_name(c)
    return ("U-18 · " if s["youth"] else "") + s["league_name"]

def club_stint_text(x, d):
    return f"{d.clubs[x['club']]['name']} ({x['y0']}–{x['y1']})" if "y0" in x else f"{d.clubs[x['club']]['name']} ({x['from'][:4]}–{x['to'][:4]})"

def end_sub(c):
    if c.coach and c.coach.get("seasons"):
        return tr("end.sub_coach", name=c.name, age=c.player_retire_age, cage=c.player.age)
    return tr("end.sub_young", name=c.name, age=c.player_retire_age)

def summary_text(c, d):
    """Итоги карьеры текстом (кнопка «Экспорт» на финальном экране), как в десктопной версии."""
    rep = c.report(); t = rep["totals"]
    gk = c.pos == "GK"
    L = [end_sub(c), tr("end.reason." + (c.retire_reason or "choice")), ""]
    L += [f"{tr('end.games')}: {t['games']}", f"{tr('end.goals')}: {t['goals']}", f"{tr('end.assists')}: {t['assists']}"]
    if gk: L.append(f"{tr('end.cs')}: {t['cs']}")
    L += [f"{tr('end.caps')}: {t['caps']}", f"{tr('end.intl_goals')}: {t['intl_goals']}", f"{tr('end.peak')}: {tr('end.peak_val', o=rep['peak_ovr'], a=rep['peak_age'])}", ""]
    L.append(tr("end.tab.comps") + ":")
    for b in rep["comps"]:
        L.append(f"  {lang_name(b):<46} {b['games']:>4} / {b['goals']:>4} / {b['cs'] if gk else b['assists']:>4}")
    L += ["", tr("end.tab.transfers") + ":"]
    for x in c.transfers:
        L.append(f"  {x['season']}  {d.clubs[x['from']]['name'] if x['from'] else '—'} -> {d.clubs[x['to']]['name']}  [{tr('type.' + x['type'])}]  {money(x['fee']) if x['fee'] > 0 else ''}")
    L += ["", tr("end.clubs") + ":", "  " + "  ->  ".join(club_stint_text(x, d) for x in rep["clubs"])]
    L += ["", tr("end.tab.honours") + ":"]
    L += [f"  ◆ {t['season']}  {trophy_name(t)}" for t in c.trophies] + [f"  ★ {a['season']}  {award_name(a['code'], a.get('rank'))}" for a in c.awards]
    if c.coach and c.coach.get("seasons"):
        sm = c.coaching().summary()
        L += ["", tr("end.tab.coach") + ":",
              f"  {tr('end.coach_seasons')}: {sm['seasons']} | {tr('end.coach_record')}: {sm['w']}-{sm['d']}-{sm['l']} ({sm['pct']}%) | "
              f"{tr('end.coach_titles')}: {sm['titles']} | {tr('end.coach_fired')}: {sm['fired']}"]
        for r in c.coach["seasons"]:
            tro = ", ".join(trophy_name(t) for t in r["trophies"])
            L.append(f"  {r['season']}  {d.clubs[r['club']]['name']:<26} {r['rank']}/{r['n']} ({tr('col.target')} {r['target']})  "
                     f"{r['w']}-{r['d']}-{r['l']}  {r['anger_before']:.0f}->{r['anger_after']:.0f}  {tro}"
                     + (f"  [{tr('verdict.' + r['verdict'])}]" if r.get("verdict") else ""))
    L += ["", tr("end.tab.seasons") + ":"]
    for s in c.seasons:
        L.append(f"  {s['season']}  {s['age']:>2}  {d.clubs[s['club']]['name']:<26} {s['rank']}/{s['n']}  {s['games']:>3}/{s['goals']:>3}/{s['cs'] if gk else s['assists']:>3}  OVR {s['ovr']}")
        for x in s.get("comps", []):
            L.append(f"        {lang_name(x):<40} {x['games']:>3}/{x['goals']:>3}/{x['cs'] if gk else x['assists']:>3}  {club_result(x, d)}")
        for e in s.get("nat_comps", []):
            if e["kind"] != "friendly" or e["games"]:
                L.append(f"        {nat_comp_name(e, d):<40} {e['games']:>3}/{e['goals']:>3}/{e['assists']:>3}  {nat_result(e, d)}")
    return "\n".join(L)

REPO_URL = "https://github.com/yukkennn/FootballCareerSimulator"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"

def copyright_html():
    """Автор и лицензия внизу стартового экрана."""
    return (f'<p class="legal">© 2026 <a href="{REPO_URL}" target="_blank" rel="noopener">yukkennn</a> · '
            f'<a href="{LICENSE_URL}" target="_blank" rel="noopener">CC BY-NC 4.0</a><br>{esc(tr("web.license_note"))}</p>')

def diary_html(text):
    """Текст дневника -> HTML: абзацы, **жирное** (даты записей), # заголовки."""
    out = []
    for block in re.split(r"\n\s*\n", text.strip()):
        b = _html.escape(block.strip())
        b = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", b)
        b = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<i>\1</i>", b)
        if b.startswith("#"):
            out.append(f"<h3>{b.lstrip('# ')}</h3>")
        elif b:
            out.append("<p>" + b.replace("\n", "<br>") + "</p>")
    return "".join(out)

def screen(title, body, footer="", left="", right=""):
    """Каркас экрана: верхняя панель, прокручиваемое содержимое, нижняя панель с кнопками."""
    top = f'<header class="topbar"><div class="tb-l">{left}</div><h1>{title}</h1><div class="tb-r">{right}</div></header>'
    foot = f'<footer class="actions">{footer}</footer>' if footer else ""
    return f'{top}<main class="content">{body}</main>{foot}'

class WebApp(CoachScreens):
    def __init__(self):
        i18n.init_lang()
        self.d = GameData()
        self.career = None
        self.view, self.ctx = "start", {}
        self.modal = None
        self.form = {"first": "", "last": "", "nat": "", "pos": "", "foot": "R", "height": 180}
        self.last_form = {}
        self._out = {}

    screen = staticmethod(screen)

    def tr(self, key):
        """Перевод для app.js (тексты настроек нейросети)."""
        return tr(key)

    def menu_btn(self):
        return btn("☰", "home", kind="ghost", extra=f'aria-label="{esc(tr("career.menu"))}"')

    # ------------------------------------------------------------------ вход из JS
    def render(self):
        html = getattr(self, "v_" + self.view)()
        # класс экрана: по нему style.css раскладывает блоки в колонки на широком экране (как в десктопной версии)
        html = html.replace('<main class="content">', f'<main class="content v-{self.view}">', 1)
        if self.modal:
            m = self.modal
            bs = "".join(btn(esc(t), a, arg, k) for t, a, arg, k in m["buttons"])
            html += (f'<div class="modal-bg"><div class="modal" role="dialog"><div class="h2">{esc(m["title"])}</div>'
                     f'<p>{esc(m["text"])}</p><div class="mbtns{" col" if m.get("column") else ""}">{bs}</div></div></div>')
        return html

    def act(self, name, arg="", form_json="{}"):
        self._out = {}
        before = (self.view, self.ctx.get("tab"), self.ctx.get("idx"))
        try:
            self._take_form(form_json)
            getattr(self, "a_" + name)(arg)
        except Exception as e:                        # ошибка не должна ломать игру: показываем её и остаёмся на экране
            traceback.print_exc()
            self._out["toast"] = f"{type(e).__name__}: {e}"
        out = dict(self._out)
        out["html"] = self.render()
        out.setdefault("scroll", "top" if before != (self.view, self.ctx.get("tab"), self.ctx.get("idx")) else "keep")
        return json.dumps(out, ensure_ascii=False)

    def partial(self, name, form_json="{}"):
        self._take_form(form_json)
        return json.dumps(getattr(self, "p_" + name)(), ensure_ascii=False)

    def _take_form(self, form_json):
        f = json.loads(form_json or "{}")
        self.last_form = f
        if self.view == "start" and f:
            for k in ("first", "last", "nat", "pos", "foot"):
                if k in f:
                    self.form[k] = f[k]
            if f.get("height"):
                self.form["height"] = int(f["height"])

    def go(self, view, **ctx):
        self.view, self.ctx, self.modal = view, ctx, None

    def save(self):
        saves.save(self.career)

    # ------------------------------------------------------------------ старт
    def v_start(self):
        d, f, lang = self.d, self.form, i18n.LANG
        langs = "".join(f'<button class="chip{" on" if lang == k else ""}" data-act="lang" data-arg="{k}">{k.upper()}</button>' for k in ("ru", "en"))
        right = f'<div class="langs">{langs}{btn("⚙", "settings", kind="ghost", extra=f'aria-label="{esc(tr("web.settings"))}"')}</div>'
        name = (f'<div class="panel a-name"><div class="muted small">{esc(tr("start.name"))}</div><div class="row">'
                f'<input name="first" value="{esc(f["first"])}" placeholder="{esc(tr("start.first"))}" autocomplete="off">'
                f'<input name="last" value="{esc(f["last"])}" placeholder="{esc(tr("start.last"))}" autocomplete="off">'
                f'<button class="btn icon" data-partial="random_name" title="{esc(tr("start.random_name_tip"))}" aria-label="{esc(tr("start.random_name"))}">🎲</button></div></div>')
        items = []
        for c in sorted(d.countries.values(), key=lambda c: c["name_ru" if lang == "ru" else "name_en"]):
            code = c["code"]
            nm = c["name_ru" if lang == "ru" else "name_en"]
            search = f"{c['name_ru']} {c['name_en']} {code}".lower()
            chk = " checked" if f["nat"] == code else ""
            items.append(f'<label class="opt" data-search="{esc(search)}"><input type="radio" name="nat" value="{code}" data-partial="phys"{chk}>'
                         f'<span>{esc(nm)}</span><span class="muted small">{code}</span><span class="gold small">{stars_text(d.nat_stars(code))}</span></label>')
        country = (f'<div class="panel a-country"><div class="h2">{esc(tr("start.country"))}</div>'
                   f'<input type="search" data-filter="#natlist" placeholder="{esc(tr("start.search"))}" autocomplete="off">'
                   f'<div class="optlist" id="natlist">{"".join(items)}</div><div class="muted small" id="sel_label">{esc(self._sel_text())}</div></div>')
        groups = []
        for gkey, plist in POS_GROUPS:
            chips = "".join(f'<label class="pos"><input type="radio" name="pos" value="{p}" data-partial="phys"{" checked" if f["pos"] == p else ""}>'
                            f'<span><b>{p}</b><small>{esc(tr("pos." + p))}</small></span></label>' for p in plist)
            groups.append(f'<div class="muted small">{esc(tr("posgrp." + gkey))}</div><div class="posrow">{chips}</div>')
        position = f'<div class="panel a-pos"><div class="h2">{esc(tr("start.position"))}</div>{"".join(groups)}</div>'
        feet = "".join(f'<label class="chip-r"><input type="radio" name="foot" value="{k}" data-partial="phys"{" checked" if f["foot"] == k else ""}>'
                       f'<span>{esc(tr("foot." + k))}</span></label>' for k in ("R", "L", "B"))
        hint, typ = self._phys()
        # нога и рост: на широком экране рядом друг с другом (как в десктопной версии), подсказка под ними
        phys = (f'<div class="panel a-phys"><div class="ph-foot"><div class="h2">{esc(tr("start.foot"))}</div><div class="row">{feet}</div></div>'
                f'<div class="ph-height"><div class="h2">{esc(tr("start.height"))}: <span id="hval">{f["height"]}</span> {esc(tr("start.cm"))}</div>'
                f'<input type="range" name="height" min="{HEIGHT_MIN}" max="{HEIGHT_MAX}" value="{f["height"]}" data-partial="phys" data-live="#hval">'
                f'<div class="muted small" id="height_typ">{esc(typ)}</div></div><div class="hint" id="phys_hint">{esc(hint)}</div></div>')
        footer = btn(esc(tr("start.load")), "show_load") + btn(esc(tr("start.next")), "start", kind="primary")
        return screen(esc(tr("start.heading")), name + country + position + phys + copyright_html(), footer, right=right)

    def _sel_text(self):
        nat = self.form["nat"]
        if not nat or nat not in self.d.countries:
            return tr("start.selected", c=tr("start.none"))
        return tr("start.selected", c=self.d.country_name(nat, i18n.LANG)) + " · " + tr("start.nat_stars", s=stars_text(self.d.nat_stars(nat)))

    def _phys(self):
        """(подсказка, обычный рост): что дают выбранные нога и рост на этой позиции (как StartPage._upd_phys)."""
        pos, f = self.form["pos"], self.form["foot"]
        if pos not in TYPICAL_HEIGHT:
            return tr("start.phys_pick_pos"), ""
        typ = TYPICAL_HEIGHT[pos]
        dh = int(self.form["height"]) - typ
        notes = [tr("phys.tall" if dh >= 4 else "phys.short" if dh <= -4 else "phys.avg")]
        if dh >= 4 and pos in ("ST", "CF", "CB", "CDM"):
            notes.append(tr("phys.headers"))
        if pos == "GK" and abs(dh) >= 4:
            notes[-1] = tr("phys.gk_tall" if dh > 0 else "phys.gk_short")
        if pos in LEFT_SIDE + RIGHT_SIDE:
            natural = (pos in LEFT_SIDE) == (f == "L")
            notes.append(tr("phys.both_wing" if f == "B" else "phys.natural" if natural else "phys.inverted"))
        elif f == "B":
            notes.append(tr("phys.both_center"))
        return " ".join(notes), tr("start.height_typ", h=typ)

    def p_phys(self):
        out = {"set": {}}
        pos = self.form["pos"]
        last = self.ctx.get("last_pos")
        if pos and pos != last:                       # пока рост не трогали, он следует за позицией (типичный рост)
            prev_typ = TYPICAL_HEIGHT.get(last, 180)
            if int(self.form["height"]) == prev_typ:
                self.form["height"] = TYPICAL_HEIGHT[pos]
                out["set"]["height"] = self.form["height"]
            self.ctx["last_pos"] = pos
        hint, typ = self._phys()
        out["html"] = {"#phys_hint": esc(hint), "#height_typ": esc(typ), "#sel_label": esc(self._sel_text()), "#hval": str(self.form["height"])}
        return out

    def p_random_name(self):
        nat = self.form["nat"] or "ENG"
        first, last = gen_name(random.Random(), nat, self.d.countries[nat]["conf"]).split(" ", 1)
        self.form["first"], self.form["last"] = first, last
        return {"set": {"first": first, "last": last}}

    def a_lang(self, lang):
        i18n.set_lang(lang)

    def a_start(self, _):
        f = self.form
        if not f["nat"]:
            self._out["toast"] = tr("web.pick_country"); return
        if not f["pos"]:
            self._out["toast"] = tr("web.pick_pos"); return
        name = " ".join(x for x in (f["first"].strip(), f["last"].strip()) if x) or tr("start.name_default")
        h = max(HEIGHT_MIN, min(HEIGHT_MAX, int(f["height"])))
        self.career = Career(self.d, name, f["nat"], f["pos"], 1, lang=i18n.LANG, foot=f["foot"], height=h)
        self.go("summary")

    def a_home(self, _):
        self.go("start")

    # ------------------------------------------------------------------ сводка и академия
    def v_summary(self):
        c, d = self.career, self.d
        rows = [(tr("summary.nation"), f"{d.country_name(c.nat, i18n.LANG)}   {stars_text(d.nat_stars(c.nat))}"),
                (tr("summary.position"), pos_text(c.pos)),
                (tr("summary.physique"), f"{tr('foot_short.' + c.player.foot)} · {c.player.height} {tr('start.cm')}"),
                (tr("summary.age"), tr("summary.age_val", n=15)), (tr("summary.start"), "2026/27")]
        body = (f'<div class="a-card">{player_card(c.player, d.country_name(c.nat, i18n.LANG))}</div><div class="a-info">{kv(rows)}'
                f'<p class="muted small">{esc(tr("summary.pot"))}</p><p class="muted small">{esc(tr("summary.rule"))}</p></div>')
        footer = btn(esc(tr("summary.reroll")), "reroll") + btn(esc(tr("summary.go")), "to_academy", kind="primary")
        return screen(esc(tr("summary.title")), body, footer, left=btn("‹", "home", kind="ghost", extra=f'aria-label="{esc(tr("summary.back"))}"'))

    def a_reroll(self, _):
        self.career.reroll()

    def a_to_academy(self, _):
        self.go("academy")

    def v_academy(self):
        c, d, w = self.career, self.d, self.career.world
        cards = []
        for cid in c.academy_ids:
            lg = w.league_of(cid)
            tag = c.academy_tag(cid)
            cards.append(club_card(d.clubs[cid], f"{lg['name']} · {d.country_name(lg['country'], i18n.LANG)}", w.stars(cid),
                                   [tr("academy.team", o=round(w.team_ovr(cid)))], esc(tr("academy.choose")), "academy", cid,
                                   tag=tr("academy." + tag), tag_home=(tag == "home")))
        body = f'<p class="muted">{esc(tr("academy.sub"))}</p>' + "".join(cards)
        return screen(esc(tr("academy.title")), body)

    def a_academy(self, cid):
        self.career.choose_academy(cid); self.save(); self.go("career")

    # ------------------------------------------------------------------ карьера
    def season_rows(self, back):
        c, d = self.career, self.d
        gk = c.pos == "GK"
        out = []
        for i in range(len(c.seasons) - 1, -1, -1):
            s = c.seasons[i]
            cl = d.clubs[s["club"]]
            tro = ", ".join(short_trophy(t["code"]) for t in s["trophies"])
            aws = ", ".join(season_award_names(s))
            stat = f"{s['games']} · {s['goals']} · {s['cs'] if gk else s['assists']}"
            intl = s["intl"]
            nat = f" · 🏳 {intl['caps']}/{intl['goals']}" if intl and intl.get("called") else ""
            badges = (f'<div class="gold small">◆ {esc(tro)}</div>' if tro else "") + (f'<div class="award small">★ {esc(aws)}</div>' if aws else "")
            out.append(f'<button class="srow" data-act="season" data-arg="{i}|{back}">{logo(cl, 36)}<div class="sr-main">'
                       f'<div><b>{esc(s["season"])}</b> <span class="muted">· {s["age"]}</span> · {esc(cl["name"])}'
                       f'{" " + esc(tr("report.loan_tag")) if s["loan"] else ""}</div>'
                       f'<div class="muted small">{esc(youth_league_name(s))} · {s["rank"]}/{s["n"]}{nat}</div>{badges}</div>'
                       f'<div class="sr-num"><div>{stat}</div><div class="muted small">OVR {s["ovr"]}→{s["ovr_end"]}</div></div></button>')
        if not out:
            return f'<p class="muted">{esc(tr("web.no_seasons"))}</p>'
        head = tr("col.games") + " · " + tr("col.goals") + " · " + tr("col.cs" if gk else "col.assists")
        return (f'<div class="muted small">{esc(tr("web.season_tap"))}</div>'
                f'<div class="srows m-only"><div class="srh muted small">{esc(head)}</div>{"".join(out)}</div>' + self.seasons_table(back))

    def seasons_table(self, back):
        """Таблица сезонов для широкого экрана - те же столбцы, что в десктопной версии; строка открывает отчёт сезона."""
        c, d = self.career, self.d
        gk = c.pos == "GK"
        cols = ["season", "age", "club", "league", "rank", "games", "goals", "cs" if gk else "assists", "ovr", "nat", "trophies_only", "awards"]
        rows = []
        for i, s in enumerate(c.seasons):
            cl = d.clubs[s["club"]]
            intl = s["intl"]
            nat = f"{intl['caps']}/{intl['goals']}" if intl and intl.get("called") else "—"
            tro = ", ".join(short_trophy(t["code"]) for t in s["trophies"])
            aws = ", ".join(season_award_names(s))
            rows.append(f'<tr class="click" data-act="season" data-arg="{i}|{back}"><td>{esc(s["season"])}</td><td>{s["age"]}</td>'
                        f'<td class="l"><span class="cl">{logo(cl, 22)}{esc(cl["name"])}{" " + esc(tr("report.loan_tag")) if s["loan"] else ""}</span></td>'
                        f'<td class="l">{esc(youth_league_name(s))}</td><td>{s["rank"]}/{s["n"]}</td><td>{s["games"]}</td><td>{s["goals"]}</td>'
                        f'<td>{s["cs"] if gk else s["assists"]}</td><td>{s["ovr"]}→{s["ovr_end"]}</td><td>{nat}</td>'
                        f'<td class="l gold">{esc(tro)}</td><td class="l award">{esc(aws)}</td></tr>')
        th = "".join(f'<th{" class=l" if k in ("club", "league", "trophies_only", "awards") else ""}>{esc(tr("col." + k))}</th>' for k in cols)
        return f'<div class="d-only twrap"><table class="tbl wide"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'

    def v_career(self):
        c, d, w = self.career, self.d, self.career.world
        pl = c.player; cl = d.clubs[c.club_id]
        youth = pl.age < 18
        lg = w.league_of(c.club_id)
        title = esc(cl["name"]) + (f" · {esc(tr('career.academy'))}" if youth else "") + (f" · © {esc(tr('career.captain'))}" if c.captain else "")
        sub = f"{lg['name']} · {d.country_name(lg['country'], i18n.LANG)}   {stars_text(w.stars(c.club_id))}   OVR {round(w.team_ovr(c.club_id))}"
        if c.parent_id:
            sub += " · " + tr("career.loan", club=d.clubs[c.parent_id]["name"])
        val = money(market_value(pl.ovr(), pl.age, pl.pot))
        head = (f'<div class="panel club-h">{logo(cl, 56)}<div><div class="h2">{title}</div><div class="muted small">{esc(sub)}</div>'
                f'<div class="gold small">{esc(tr("career.age", n=pl.age))} · {esc(tr("career.contract", n=c.contract_left))} · {esc(tr("career.value", v=val))}</div></div></div>')
        pts = [(s["age"], s["ovr"]) for s in c.seasons] + [(pl.age, pl.ovr())]
        g = sum(s["games"] for s in c.seasons); go = sum(s["goals"] for s in c.seasons); a = sum(s["assists"] for s in c.seasons)
        n_aw = sum(1 for x in c.awards if x["code"] != "ballon_top30")
        totals = f'<div class="panel muted small">{esc(tr("career.totals", g=g, a=go, s=a, t=len(c.trophies), w=n_aw))}</div>'
        body = (head.replace('class="panel club-h"', 'class="panel club-h a-head"', 1)
                + f'<div class="a-left">{player_card(pl, d.country_name(c.nat, i18n.LANG))}{ovr_chart(pts, tr("chart.title"))}</div>'
                + f'<div class="a-seasons"><div class="h2 mt m-only">{esc(tr("web.seasons"))}</div>{self.season_rows("career")}{totals}'
                + f'<p class="muted small">{esc(tr("career.autosave"))}</p></div>')
        play = tr("career.play_academy") if youth else tr(f"career.play_{c.freq if not c.parent_id else 1}")
        footer = btn(esc(tr("career.retire")), "retire", kind="danger") + btn(esc(play), "play", kind="primary", extra="data-busy")
        return screen(esc(pl.name), body, footer, left=btn("☰", "home", kind="ghost", extra=f'aria-label="{esc(tr("career.menu"))}"'))

    def a_season(self, arg):
        i, back = arg.split("|")
        self.go("season", idx=int(i), back=back, tab=self.ctx.get("tab"))

    def v_season(self):
        s = self.career.seasons[self.ctx["idx"]]
        return screen(esc(tr("report.season", s=s["season"])), self.diary_btn(self.ctx["idx"]) + season_html(self.career, self.d, s),
                      left=btn("‹", "back", self.ctx["back"], kind="ghost", extra=f'aria-label="{esc(tr("web.back"))}"'))

    # ------------------------------------------------------------------ дневник сезона (пишет нейросеть, см. game/story.py и web/llm.js)
    def diary_btn(self, idx):
        s = self.career.seasons[idx]
        if s.get("youth") and not s.get("comps"):
            return ""
        return btn(esc(tr("web.diary_btn")), "story", str(idx), "diary")

    def a_story(self, idx):
        self._story_return = (self.view, dict(self.ctx))
        self.go("story", idx=int(idx))

    def a_story_back(self, _):
        view, ctx = getattr(self, "_story_return", ("career", {}))
        self.view, self.ctx, self.modal = view, ctx, None

    def a_story_gen(self, _):
        idx = self.ctx["idx"]
        self.ctx.update(writing=True, error=None)
        self._out["llm"] = dict(story_mod.prompt(self.career, self.d, idx), idx=idx)
        self._out["scroll"] = "top"

    def a_story_save(self, payload):
        r = json.loads(payload)
        s = self.career.seasons[int(r["idx"])]
        text, memory = story_mod.split_answer(r["text"])
        s["story"] = {"text": text, "memory": memory, "provider": r.get("provider", ""), "model": r.get("model", ""), "lang": i18n.LANG}
        self.save()
        if self.view == "story":
            self.ctx.update(writing=False, error=None)
        else:
            self._out["toast"] = tr("web.diary") + " " + s["season"] + " ✓"

    def a_story_fail(self, msg):
        if self.view == "story":
            self.ctx.update(writing=False, error=tr("web.ai_need") if msg == "__need__" else msg)
        self._out["scroll"] = "keep"

    def v_story(self):
        idx = self.ctx["idx"]
        s = self.career.seasons[idx]
        st = s.get("story")
        head = (f'<div class="panel club-h">{logo(self.d.clubs[s["club"]], 48)}<div><div class="h2">{esc(self.career.name)}</div>'
                f'<div class="muted small">{esc(s["season"])} · {esc(s["club_name"])} · {esc(tr("career.age", n=s["age"]))}</div></div></div>')
        if self.ctx.get("writing"):
            body = head + f'<div class="panel center"><div class="spinner"></div><p class="muted">{esc(tr("web.diary_writing"))}</p></div>'
            return screen(esc(tr("web.diary")), body, left=btn("‹", "story_back", kind="ghost"))
        parts = [head]
        if self.ctx.get("error"):
            parts.append(f'<div class="panel err"><b>{esc(tr("web.diary_failed"))}</b><div class="small">{esc(self.ctx["error"])}</div></div>')
        if st:
            parts.append(f'<article class="diary">{diary_html(st["text"])}</article>')
            if st.get("model"):
                parts.append(f'<p class="muted small">{esc(tr("web.diary_by", p=st.get("provider", ""), m=st["model"]))}</p>')
            footer = btn(esc(tr("web.settings")), "settings") + btn(esc(tr("web.diary_rewrite")), "story_gen", kind="primary", extra="data-llm")
        else:
            parts.append(f'<div class="panel"><p>{esc(tr("web.diary_none"))}</p><p class="muted small">{esc(tr("web.diary_hint"))}</p></div>')
            footer = btn(esc(tr("web.settings")), "settings") + btn(esc(tr("web.diary_write")), "story_gen", kind="primary", extra="data-llm")
        return screen(esc(tr("web.diary")), "".join(parts), footer, left=btn("‹", "story_back", kind="ghost", extra=f'aria-label="{esc(tr("web.back"))}"'))

    # ------------------------------------------------------------------ настройки (значения хранит и заполняет app.js: ключ не попадает в Python)
    def a_settings(self, _):
        if self.view != "settings":
            self._settings_return = (self.view, dict(self.ctx))
        self.go("settings")

    def a_settings_back(self, _):
        view, ctx = getattr(self, "_settings_return", ("start", {}))
        self.view, self.ctx, self.modal = view, ctx, None

    def v_settings(self):
        opts = "".join(f'<option value="{k}">{esc(v)}</option>' for k, v in (("off", tr("web.ai_off")), ("gemini", "Google Gemini"), ("claude", "Anthropic Claude")))
        body = (f'<div class="panel" id="ai-settings"><div class="h2">{esc(tr("web.ai_title"))}</div>'
                f'<label class="sel"><span class="muted small">{esc(tr("web.ai_provider"))}</span><select id="ai-provider">{opts}</select></label>'
                f'<label class="sel"><span class="muted small">{esc(tr("web.ai_key"))}</span><input id="ai-key" type="password" autocomplete="off" spellcheck="false"></label>'
                f'<label class="sel"><span class="muted small">{esc(tr("web.ai_model"))}</span><input id="ai-model" list="ai-models" autocomplete="off" spellcheck="false">'
                f'<datalist id="ai-models"></datalist></label>'
                f'<button class="btn" data-js="ai-models">{esc(tr("web.ai_models_btn"))}</button>'
                f'<p class="muted small">{esc(tr("web.ai_key_hint"))}</p></div>')
        footer = btn(esc(tr("web.ai_save")), "", kind="primary", extra='data-js="ai-save"')
        return screen(esc(tr("web.settings")), body, footer, left=btn("‹", "settings_back", kind="ghost", extra=f'aria-label="{esc(tr("web.back"))}"'))

    def a_back(self, view):
        self.go(view, tab=self.ctx.get("tab"))

    def a_play(self, _):
        recs, reason = self.career.play_period()
        self.save()
        self.go("report", recs=recs, reason=reason)

    def v_report(self):
        c, recs, reason = self.career, self.ctx["recs"], self.ctx["reason"]
        a, b = recs[0]["season"], recs[-1]["season"]
        body = "".join(self.diary_btn(next(i for i, x in enumerate(c.seasons) if x is s)) + season_html(c, self.d, s) for s in recs)
        if len(recs) > 1:
            G = sum(s["games"] for s in recs); A = sum(s["goals"] for s in recs); S = sum(s["assists"] for s in recs); CS = sum(s["cs"] for s in recs)
            tot = tr("report.stats_gk", g=G, c=CS) if c.pos == "GK" else tr("report.stats", g=G, a=A, s=S)
            body += f'<div class="panel"><b>{esc(tr("report.total"))}:</b> {esc(tot)}</div>'
        body += f'<p class="reason">{esc(tr("reason." + reason))}</p>'
        footer = btn(esc(tr("report.continue")), "after_report", kind="primary")
        return screen(esc(tr("report.title1", a=a) if a == b else tr("report.title", a=a, b=b)), body, footer)

    def a_after_report(self, _):
        if self.career.status != "retired":
            self.go("offers")
        elif self.career.coach is None:               # карьера закончилась сама (40 лет): просто завершить или стать тренером
            self.modal = {"title": tr("retire.title"), "text": tr("retire.question"),
                          "buttons": [(tr("retire.plain"), "retire_yes", "", ""), (tr("retire.coach"), "retire_coach", "", "primary")]}
        else:
            self.go("end", tab="summary")

    # ------------------------------------------------------------------ предложения
    def v_offers(self):
        c, d, w = self.career, self.d, self.career.world
        cur = d.clubs[c.club_id]; clg = w.league_of(c.club_id); team = w.team_ovr(c.club_id)
        facts = [tr("offers.current_team", o=round(team)), tr("offers.current_role", r=tr("role." + c.role_for(c.player.ovr() - team))),
                 tr("offers.contract_left", n=c.contract_left) if c.contract_left > 0 else tr("offers.contract_over")]
        body = (f'<p class="muted">{esc(tr("reason." + c.offer_reason))}</p>'
                f'<p class="gold">{esc(tr("offers.you", o=c.player.ovr()))} · {esc(pos_text(c.pos))} · {esc(tr("career.age", n=c.player.age))}</p>'
                + club_card(cur, f"{tr('offers.current')} · {clg['name']} · {d.country_name(clg['country'], i18n.LANG)}", w.stars(c.club_id), facts,
                            esc(tr("offers.stay", club=cur["name"])) if c.can_stay else None, "accept", "stay")
                + (f'<div class="h2 mt">{esc(tr("web.new_offers"))}</div>' if c.offers else ""))
        for i, o in enumerate(c.offers):
            cl = d.clubs[o["club"]]; lg = w.league_of(o["club"])
            tag = tr("offers.kind.loan") if o["kind"] == "loan" else tr("offers.kind.first") if o["kind"] == "first" else None
            fee = tr("offers.free") if o["fee"] <= 0 and o["kind"] == "transfer" else (money(o["fee"]) if o["fee"] > 0 else "—")
            lines = [f"{tr('offers.fee')}: {fee}" if o["kind"] == "transfer" else "", tr("offers.years", n=o["years"]),
                     tr("offers.role", r=tr("role." + o["role"])), tr("offers.team", o=round(w.team_ovr(o["club"])))]
            known = stars_mod.players_at(c.stars, o["club"])[:3]
            if known:
                lines.append(tr("offers.known", n=", ".join(p["name"] for p in known)))
            body += club_card(cl, f"{lg['name']} · {d.country_name(lg['country'], i18n.LANG)}", w.stars(o["club"]), lines,
                              esc(tr("offers.choose")), "accept", str(i), tag=tag)
        footer = btn(esc(tr("offers.retire")), "retire", kind="danger")
        return screen(esc(tr("offers.title")), body, footer)

    def a_accept(self, arg):
        self.career.accept("stay" if arg == "stay" else int(arg)); self.save(); self.go("career")

    # ------------------------------------------------------------------ завершение карьеры
    def a_retire(self, _):
        self.modal = {"title": tr("retire.title"), "text": tr("retire.question_early"), "column": True,
                      "buttons": [(tr("retire.plain"), "retire_yes", "", "danger"), (tr("retire.coach"), "retire_coach", "", "primary"),
                                  (tr("retire.cancel"), "modal_close", "", "")]}

    def a_modal_close(self, _):
        self.modal = None

    def a_retire_yes(self, _):
        if self.career.status != "retired":
            self.career.retire_now()
        self.save(); self.go("end", tab="summary")

    def a_retire_coach(self, _):
        if self.career.status != "retired":
            self.career.retire_now()
        self.career.start_coaching(); self.save(); self.go("coach_offers")

    def v_end(self):
        c, d = self.career, self.d
        rep = c.report(); cc = d.clubs[rep["coach_club"]]
        tab = self.ctx.get("tab") or "summary"
        tabs = [("summary", tr("end.tab.summary")), ("seasons", tr("end.tab.seasons")), ("comps", tr("end.tab.comps")),
                ("transfers", tr("end.tab.transfers")), ("honours", tr("end.tab.honours"))]
        if any(s.get("chronicle") for s in c.seasons):
            tabs.append(("chronicle", tr("end.tab.chronicle")))
        if c.coach and c.coach.get("seasons"):
            tabs = [("coach", tr("end.tab.coach")), ("coach_seasons", tr("end.tab.coach_seasons"))] + tabs
        elif tab.startswith("coach"):
            tab = "summary"
        chips = "".join(f'<button class="chip{" on" if k == tab else ""}" data-act="tab" data-arg="{k}">{esc(t)}</button>' for k, t in tabs)
        head = (f'<div class="panel club-h">{logo(cc, 64)}<div><div class="h2">{esc(end_sub(c))}</div>'
                f'<div class="muted small">{esc(tr("end.reason." + (c.retire_reason or "choice")))}</div></div></div>')
        body = head + f'<div class="tabs">{chips}</div>' + getattr(self, "end_" + tab)(rep)
        footer = btn(esc(tr("web.export")), "export_text")
        if c.coach is None:                           # игрок завершил карьеру без тренерства: можно стать тренером и сейчас
            footer += btn(esc(tr("end.become_coach")), "retire_coach")
        footer += btn(esc(tr("end.new")), "home", kind="primary")
        return screen(esc(tr("end.title")), body, footer)

    def a_tab(self, tab):
        self.ctx["tab"] = tab

    def end_summary(self, rep):
        c, d = self.career, self.d
        t = rep["totals"]
        rows = [(tr("end.games"), t["games"]), (tr("end.goals"), t["goals"]), (tr("end.assists"), t["assists"])]
        if c.pos == "GK": rows.append((tr("end.cs"), t["cs"]))
        rows += [(tr("end.caps"), t["caps"]), (tr("end.intl_goals"), t["intl_goals"]),
                 (tr("end.peak"), tr("end.peak_val", o=rep["peak_ovr"], a=rep["peak_age"]))]
        tc = rep["trophy_cats"]
        rows.append((tr("end.trophies"), " · ".join(f"{tr('end.cat.' + k)}: {v}" for k, v in tc.items()) or tr("end.none"), theme.GOLD))
        rows.append((tr("end.awards"), " · ".join(f"{award_name(k)} ×{v}" for k, v in rep["award_counts"].items()) or tr("end.none"), theme.AWARD))
        rows.append((tr("end.clubs"), " → ".join(club_stint_text(x, d) for x in rep["clubs"]) or tr("end.none")))
        cap = {}
        for s in c.seasons:
            if s.get("captain"):
                cap[s["club"]] = cap.get(s["club"], 0) + 1
        if cap:
            rows.append((tr("end.captain"), ", ".join(f"{d.clubs[k]['name']} ({tr('end.captain_val', n=v)})" for k, v in cap.items()), theme.GOLD))
        return kv(rows)

    def end_seasons(self, rep):
        return self.season_rows("end")

    def end_comps(self, rep):
        gk = self.career.pos == "GK"
        rows = "".join(f"<tr><td>{esc(lang_name(b))}</td><td>{b['games']}</td><td>{b['goals']}</td><td>{b['cs'] if gk else b['assists']}</td></tr>"
                       for b in rep["comps_chrono"])
        return (f'<table class="tbl comps"><thead><tr><th>{esc(tr("col.comp"))}</th><th>{esc(tr("col.games"))}</th><th>{esc(tr("col.goals"))}</th>'
                f'<th>{esc(tr("col.cs" if gk else "col.assists"))}</th></tr></thead><tbody>{rows}</tbody></table>')

    def end_transfers(self, rep):
        c, d = self.career, self.d
        out, rows = [], []
        tl = c.transfers
        for i, t in enumerate(tl):
            fee = money(t["fee"]) if t["fee"] > 0 else ""
            frm = d.clubs[t["from"]]["name"] if t["from"] else "—"
            out.append(f'<div class="li"><div><b>{esc(t["season"])}</b> · {esc(tr("type." + t["type"]))}</div>'
                       f'<div>{esc(frm)} → <b>{esc(d.clubs[t["to"]]["name"])}</b></div>' + (f'<div class="gold small">{esc(fee)}</div>' if fee else "") + "</div>")
            y0 = int(t["season"][:4])
            y1 = int(tl[i + 1]["season"][:4]) if i + 1 < len(tl) else c.year
            rows.append(f'<tr><td>{esc(t["season"])}</td><td class="l">{esc(frm)}</td><td class="l"><b>{esc(d.clubs[t["to"]]["name"])}</b></td>'
                        f'<td class="l">{esc(tr("type." + t["type"]))}</td><td class="gold">{esc(fee) or "—"}</td><td>{y0}–{y1}</td></tr>')
        if not out:
            return f'<div class="panel">{esc(tr("end.none"))}</div>'
        th = "".join(f'<th{" class=l" if k in ("from", "to", "type") else ""}>{esc(tr("col." + k))}</th>' for k in ("years", "from", "to", "type", "fee", "period"))
        return (f'<div class="panel list m-only">{"".join(out)}</div>'
                f'<div class="d-only twrap"><table class="tbl wide"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')

    def end_honours(self, rep):
        c, d = self.career, self.d
        items = []
        for t in c.trophies:
            cls = "nat" if t["cat"] == "national" else "gold"
            who = d.country_name(c.nat, i18n.LANG) if t["cat"] == "national" else d.clubs[t["club"]]["name"]
            items.append((t["season"], 0, f'<div class="li"><span class="muted">{esc(t["season"])}</span> <span class="{cls}">◆ {esc(trophy_name(t))}</span>'
                                          f'<div class="muted small">{esc(who)}</div></div>'))
        for a in c.awards:
            club = d.clubs[a["club"]]["name"] if a.get("club") in d.clubs else ""
            items.append((a["season"], 1, f'<div class="li awardbg"><span class="muted">{esc(a["season"])}</span> <b class="award">★ {esc(award_name(a["code"], a.get("rank")))}</b>'
                                          f'<div class="muted small">{esc(club)}</div></div>'))
        items.sort(key=lambda x: (x[0], x[1]))
        return '<div class="panel list">' + ("".join(x[2] for x in items) or esc(tr("end.none"))) + "</div>"

    def end_chronicle(self, rep):
        out = [f'<div class="li"><span class="muted">{esc(s["season"])}</span> {esc(chronicle_text(e, self.d))}</div>'
               for s in self.career.seasons for e in s.get("chronicle", [])]
        return '<div class="panel list">' + "".join(out) + "</div>"

    def a_export_text(self, _):
        self._out["download"] = {"name": f"{self.career.name}_career.txt", "text": summary_text(self.career, self.d), "mime": "text/plain"}

    # ------------------------------------------------------------------ сохранения
    def v_load(self):
        d = self.d
        rows = []
        for it in saves.list_saves():
            when = time.strftime("%d.%m.%Y %H:%M", time.localtime(it["mtime"]))
            club = d.clubs[it["club"]]["name"] if it["club"] in d.clubs else "—"
            if it["status"] in ("retired", "coach_retired"):
                txt = tr("load.row_retired", name=it["name"], when=when)
            elif it["status"].startswith("coach"):
                txt = tr("load.row_coach", name=it["name"], age=it["age"], club=club, when=when)
            else:
                txt = tr("load.row", name=it["name"], age=it["age"], club=club, when=when)
            lg = logo(d.clubs[it["club"]], 40) if it["club"] in d.clubs else ""
            rows.append(f'<div class="ccard"><div class="cc-head">{lg}<div class="cc-main">{esc(txt)}</div></div><div class="row">'
                        + btn(esc(tr("load.delete")), "ask_delete", it["id"], "danger") + btn(esc(tr("web.export")), "export_save", it["id"])
                        + btn(esc(tr("load.open")), "open_save", it["id"], "primary") + "</div></div>")
        body = (f'<p class="muted small">{esc(tr("web.saves_hint"))}</p>'
                f'<label class="btn file">{esc(tr("web.import"))}<input type="file" accept=".json,application/json" data-import hidden></label>'
                + ("".join(rows) or f'<p class="muted">{esc(tr("load.empty"))}</p>'))
        return screen(esc(tr("load.title")), body, left=btn("‹", "home", kind="ghost", extra=f'aria-label="{esc(tr("web.back"))}"'))

    def a_show_load(self, _):
        self.go("load")

    def _save_path(self, sid):
        p = saves.saves_dir() / f"{sid}.json"
        if not p.exists():
            raise FileNotFoundError(sid)
        return p

    def a_open_save(self, sid):
        path = self._save_path(sid)
        try:
            self.career = saves.load(path, self.d)
        except (KeyError, ValueError, TypeError, IndexError) as e:
            self._out["toast"] = f"{tr('load.broken')}: {type(e).__name__}: {e}"; return
        s = self.career.status
        {"academy_pick": lambda: self.go("academy"), "playing": lambda: self.go("career"), "offers": lambda: self.go("offers"),
         "retired": lambda: self.go("end", tab="summary"), "coach_retired": lambda: self.go("end", tab="coach"),
         "coach_offers": lambda: self.go("coach_offers"), "coaching": lambda: self.go("coach")}[s]()

    def a_ask_delete(self, sid):
        self.modal = {"title": tr("load.delete"), "text": tr("web.delete_q"),
                      "buttons": [(tr("retire.cancel"), "modal_close", "", ""), (tr("load.delete"), "delete_save", sid, "danger")]}

    def a_delete_save(self, sid):
        saves.delete(self._save_path(sid)); self.modal = None

    def a_export_save(self, sid):
        path = self._save_path(sid)
        name = json.loads(path.read_text(encoding="utf-8")).get("name", "career")
        self._out["download"] = {"name": f"{name}_{sid[:8]}.json", "text": path.read_text(encoding="utf-8"), "mime": "application/json"}

    def a_import_save(self, text):
        try:
            data = json.loads(text)
            Career.from_dict(data, self.d)            # проверка: сохранение открывается
            sid = data["id"]
        except Exception:
            self._out["toast"] = tr("web.import_bad"); return
        (saves.saves_dir() / f"{sid}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        self._out["toast"] = tr("web.import_ok", name=data.get("name", ""))
