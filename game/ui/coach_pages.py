"""Экраны тренерской карьеры: предложения клубов, клуб тренера (тактика), середина сезона, итоги сезона, рекорды."""
from html import escape
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QGridLayout, QProgressBar, QTextBrowser, QButtonGroup,
                               QRadioButton, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox, QTabWidget,
                               QCheckBox)
from .. import i18n
from ..i18n import tr
from ..text import stars_text, trophy_name, stage, short_trophy, award_name, money
from ..coach import pressure, DECAY, TACTICS, REL_LOVED
from ..transfers import annual_budget, price
from .. import squad as squad_mod
from . import theme
from .widgets import ClubCard, logo_label
from .pages import label, panel, scroll, SortTable, cell, details_html, league_table_html

def kind_text(kind):
    return tr("kind." + kind)

def patience_text(p):
    return tr("patience.low" if p >= 1.3 else "patience.mid" if p >= 0.85 else "patience.high")

def anger_color(v):
    return theme.ACCENT if v < 40 else theme.GOLD if v < 70 else theme.RED

def anger_bar(value):
    bar = QProgressBar(); bar.setRange(0, 100); bar.setValue(int(round(value))); bar.setFormat(f"{value:.0f} / 100")
    bar.setStyleSheet(f"QProgressBar {{ background: {theme.PANEL2}; border: 1px solid #334053; border-radius: 6px; text-align: center; height: 20px; }}"
                      f"QProgressBar::chunk {{ background: {anger_color(value)}; border-radius: 5px; }}")
    return bar

def tactic_name(t):
    return tr("tactic." + t) if t else "—"

class TacticPicker(QWidget):
    """Выбор тактики: четыре варианта и подсказка, что даёт выбранный (прессинг - с учётом навыка тренера)."""
    def __init__(self, current, rating, title):
        super().__init__()
        self.rating = rating
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(4)
        v.addWidget(label(title, "h2"))
        grid = QGridLayout(); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(2); self.group = QButtonGroup(self)
        for i, t in enumerate(TACTICS):                       # сеткой 2x2: помещается и в узкую панель
            rb = QRadioButton(tr("tactic." + t)); rb.setProperty("tactic", t); self.group.addButton(rb, i); grid.addWidget(rb, i // 2, i % 2)
            if t == current: rb.setChecked(True)
        grid.setColumnStretch(2, 1); v.addLayout(grid)
        self.hint = label("", "muted", True); v.addWidget(self.hint)
        self.group.buttonToggled.connect(lambda *_: self._upd()); self._upd()

    def value(self):
        b = self.group.checkedButton()
        return b.property("tactic") if b else "balanced"

    def _upd(self):
        t = self.value()
        self.hint.setText(tr("tactic.hint." + t, r=f"{self.rating:.0f}") if t == "press" else tr("tactic.hint." + t))

def rel_tag(rel):
    if rel >= REL_LOVED:
        return tr("rel.loved"), True
    if rel >= 15:
        return tr("rel.good"), True
    if rel <= -10:
        return tr("rel.bad"), False
    return None, False

# ======================================================================================= предложения
class CoachOffersPage(QWidget):
    accept = Signal(object); retire = Signal()

    def __init__(self, career, data):
        super().__init__(); self.setObjectName("page")
        c, w, s = career, career.world, career.coach
        root = QVBoxLayout(self); root.setContentsMargins(32, 24, 32, 24); root.setSpacing(10)
        root.addWidget(label(tr("coach.offers_title"), "title"))
        root.addWidget(label(tr("coach.reason." + (s.get("offer_reason") or "start")), "muted", True))
        root.addWidget(label(tr("coach.you", r=f"{s['rating']:.0f}", p=f"{s['rep']:.0f}", a=c.player.age), "gold"))
        host = QWidget(); host.setObjectName("scrollhost"); v = QVBoxLayout(host); v.setSpacing(10); v.setContentsMargins(0, 6, 0, 6)
        for i, o in enumerate(s["offers"]):
            cl = data.clubs[o["club"]]; lg = w.league_of(o["club"])
            sub = f"{lg['name']} · {data.country_name(lg['country'], i18n.LANG)}"
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
            v.addWidget(ClubCard(cl, sub, w.stars(o["club"]), lines, tr("coach.choose"), lambda _=False, i=i: self.accept.emit(i),
                                 tag="\n".join(tags) or None, tag_home=good))
        v.addStretch()
        root.addWidget(scroll(host), 1)
        row = QHBoxLayout()
        if s.get("can_stay") and s.get("club"):
            b = QPushButton(tr("coach.stay", club=data.clubs[s["club"]]["name"])); b.clicked.connect(lambda: self.accept.emit("stay")); row.addWidget(b)
        row.addStretch()
        r = QPushButton(tr("coach.retire")); r.setObjectName("danger"); r.clicked.connect(self.retire.emit); row.addWidget(r)
        root.addLayout(row)

# ======================================================================================= клуб тренера
class CoachPage(QWidget):
    play = Signal(str); menu = Signal(); retire = Signal(); diary = Signal(str)   # play: тактика на первую половину сезона

    def __init__(self, career, data):
        super().__init__(); self.setObjectName("page")
        c, d, w, s = career, data, career.world, career.coach
        cid = s["club"]; cl = d.clubs[cid]; lg = w.league_of(cid)
        root = QVBoxLayout(self); root.setContentsMargins(24, 18, 24, 18); root.setSpacing(12)
        head = panel(); hl = QHBoxLayout(head); hl.setContentsMargins(16, 10, 16, 10); hl.setSpacing(14)
        hl.addWidget(logo_label(cl, 48))
        col = QVBoxLayout(); col.setSpacing(1)
        col.addWidget(label(cl["name"], "h2"))
        col.addWidget(label(tr("coach.header_sub", league=lg["name"], country=d.country_name(lg["country"], i18n.LANG),
                               stars=stars_text(w.stars(cid)), ovr=round(w.team_ovr(cid))), "muted"))
        hl.addLayout(col, 1)
        hl.addWidget(label(f"{c.name}  ·  {tr('career.age', n=c.player.age)}", "gold"))
        root.addWidget(head)
        body = QHBoxLayout(); body.setSpacing(14); root.addLayout(body, 1)
        # --- слева: тренер, руководство, тактика, рекорды
        info = panel(); info.setFixedWidth(360); g = QGridLayout(info); g.setContentsMargins(18, 14, 18, 14); g.setVerticalSpacing(8)
        cc = c.coaching()
        rank, n, kind = cc.expected(cid)
        rows = [(tr("coach.info_rating"), f"{s['rating']:.0f}"), (tr("coach.info_rep"), f"{s['rep']:.0f}"),
                (tr("coach.budget"), eur(s.get("budget", 0.0))),
                (tr("coach.info_contract"), tr("coach.years_left", n=s["contract_left"])),
                (tr("coach.info_project"), tr("coach.project." + s["project"])),
                (tr("coach.info_target"), tr("coach.target_place", t=kind_text(kind), r=rank, n=n))]
        for i, (k, val) in enumerate(rows):
            g.addWidget(label(k, "muted"), i, 0, Qt.AlignTop); g.addWidget(label(val, None, True), i, 1)
        r0 = len(rows)
        g.addWidget(label(tr("coach.anger"), "h2"), r0, 0, 1, 2)
        g.addWidget(anger_bar(s["anger"]), r0 + 1, 0, 1, 2)
        g.addWidget(label(tr("coach.anger_hint") + " · " + tr("coach.patience", p=patience_text(pressure(w.score[cid], s["project"]))),
                          "muted", True), r0 + 2, 0, 1, 2)
        self.formation = FormationPicker(c, s.get("formation", squad_mod.DEFAULT_FORMATION))
        self.formation.changed.connect(self._formation_changed)
        g.addWidget(self.formation, r0 + 3, 0, 1, 2)
        self.rotation = RotationPicker(s.get("rotation", "none"))
        self.rotation.changed.connect(self._rotation_changed)
        g.addWidget(self.rotation, r0 + 4, 0, 1, 2)
        self.tactic = TacticPicker(s.get("tactic", "balanced"), s["rating"], tr("tactic.title"))
        g.addWidget(self.tactic, r0 + 5, 0, 1, 2)
        g.setRowStretch(r0 + 6, 1)
        body.addWidget(info)
        # --- справа: вкладки «Состав» (в начале сезона - весь состав и основа) и «Сезоны» (с рекордами)
        self.c, self.d = c, d
        self.tabs = QTabWidget()
        self.squad_host = QWidget(); self.squad_lay = QVBoxLayout(self.squad_host); self.squad_lay.setContentsMargins(8, 8, 8, 8)
        self.lineup_host = QWidget(); self.lineup_lay = QVBoxLayout(self.lineup_host); self.lineup_lay.setContentsMargins(8, 8, 8, 8)
        self._fill_squad()
        self.tabs.addTab(self.squad_host, tr("tab.squad"))
        self.tabs.addTab(self.lineup_host, tr("tab.lineup"))
        sh = QWidget(); sl = QVBoxLayout(sh); sl.setContentsMargins(8, 8, 8, 8)
        rec_html = records_compact(cc.records(), d)
        if rec_html:
            sl.addWidget(label(tr("rec.title") + ": " + rec_html.replace("\n", " · "), "muted", True))
        sl.addWidget(coach_seasons_table(c, d), 1)
        self.tabs.addTab(sh, tr("tab.seasons"))
        body.addWidget(self.tabs, 1)
        bar = QHBoxLayout()
        b = QPushButton(tr("career.menu")); b.clicked.connect(self.menu.emit); bar.addWidget(b)
        r = QPushButton(tr("coach.retire")); r.setObjectName("danger"); r.clicked.connect(self.retire.emit); bar.addWidget(r)
        dz = QPushButton(tr("ai.diaries")); dz.clicked.connect(lambda: self.diary.emit("")); bar.addWidget(dz)
        bar.addStretch(); bar.addWidget(label(tr("career.autosave"), "muted"))
        p = QPushButton(tr("coach.play_half")); p.setObjectName("primary"); p.clicked.connect(lambda: self.play.emit(self.tactic.value()))
        bar.addWidget(p)
        root.addLayout(bar)

    def _fill_squad(self):
        c = self.c
        f = c.coach.get("formation", squad_mod.DEFAULT_FORMATION)
        players = squad_mod.squad(c); lc = squad_mod.line_counts(players)
        _clear(self.squad_lay)
        self.squad_lay.addWidget(label(tr("sq.xi", o=f"{squad_mod.team_rating(c, f):.1f}") + "   ·   " +
                                       tr("sq.counts", n=len(players), g=lc["GK"], d=lc["DEF"], m=lc["MID"], a=lc["ATT"]), "muted"))
        self.squad_lay.addWidget(squad_table(c, self.d, f), 1)
        _clear(self.lineup_lay)
        self.lineup_lay.addWidget(lineup_tab(c, self._fill_squad))

    def _lineup_set(self, i, pid):
        lineup_set(self.c, i, pid); self._fill_squad()

    def _lineup_auto(self, on):
        lineup_auto(self.c, on); self._fill_squad()

    def _formation_changed(self, f):
        self.c.coach["formation"] = f
        squad_mod.apply_to_world(self.c)
        self._fill_squad()

    def _rotation_changed(self, r):
        self.c.coach["rotation"] = r
        squad_mod.apply_to_world(self.c)
        self._fill_squad()

def verdict_text(r):
    return tr("verdict." + r["verdict"]) if r.get("verdict") else ""

def coach_seasons_table(c, d):
    """Сезоны тренера: сезон, возраст, клуб, лига, место, задача, В-Н-П, тактика, трофеи, раздражение, итог."""
    rows = []
    for r in c.coach["seasons"]:
        tro = [short_trophy(t["code"]) for t in r["trophies"]] + [award_name(a) for a in r["awards"]]
        diff = r["target"] - r["rank"]
        place_col = theme.ACCENT if diff > 0 else theme.RED if diff < -1 else None
        tac = r.get("tactics") or []
        tac_txt = " → ".join(tactic_name(t) for t in tac if t) if tac else ""
        fired = (r.get("verdict") or "").startswith("fired")
        rows.append([r["season"], r["age"], d.clubs[r["club"]]["name"], r["league_name"],
                     cell(f"{r['rank']}/{r['n']}", r["rank"], place_col), cell(f"{r['target']}", r["target"]),
                     cell(f"{r['w']}-{r['d']}-{r['l']}", r["w"]), tac_txt, cell(", ".join(tro), len(tro) or None, theme.GOLD),
                     cell(f"{r['anger_before']:.0f} → {r['anger_after']:.0f}", r["anger_after"], anger_color(r["anger_after"])),
                     cell(verdict_text(r), None, theme.RED if fired else None)])
    hd = [tr("col.season"), tr("col.age"), tr("col.club"), tr("col.league"), tr("col.rank"), tr("col.target"),
          tr("tbl.w") + "-" + tr("tbl.d") + "-" + tr("tbl.l"), tr("tactic.title"), tr("col.trophies_only"), tr("col.anger"), tr("col.verdict")]
    t = SortTable(hd, rows, [64, 40, 125, 105, 54, 58, 72, 135, 100, 92], center=(0, 1, 4, 5, 6, 9))
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); t.setTextElideMode(Qt.ElideRight)
    if rows:
        t.scrollToBottom()
    return t

# ======================================================================================= середина сезона
class MidSeasonPage(QWidget):
    done = Signal(str)                                   # тактика на вторую половину
    winter = Signal(str)                                 # зимнее трансферное окно (тактика запоминается)

    def __init__(self, career, data, mid):
        super().__init__(); self.setObjectName("page")
        c, d, s = career, data, career.coach
        cid = s["club"]
        root = QVBoxLayout(self); root.setContentsMargins(32, 24, 32, 24); root.setSpacing(10)
        from ..coach import season_label
        root.addWidget(label(tr("mid.title", s=season_label(c.year)), "title"))
        top = QHBoxLayout(); top.setSpacing(16); root.addLayout(top)
        box = panel(); bl = QVBoxLayout(box); bl.setContentsMargins(16, 12, 16, 12); bl.setSpacing(6)
        diff = mid["target"] - mid["rank"]
        bl.addWidget(label(tr("mid.place", r=mid["rank"], n=mid["n"], t=kind_text(mid["kind"]), e=mid["target"]),
                           "h2", True))
        bl.addWidget(label(tr("mid.anger", a=f"{mid['anger_before']:.0f}", b=f"{mid['anger']:.0f}"), None))
        bl.addWidget(anger_bar(mid["anger"]))
        msg = tr("mid.fired") if mid["fired"] else tr("mid.warn") if mid["anger"] >= 70 else tr("mid.ok")
        m = label(msg, None, True); m.setStyleSheet(f"color: {theme.RED if mid['fired'] or mid['anger'] >= 70 else theme.ACCENT}; font-weight: 700;")
        bl.addWidget(m)
        top.addWidget(box, 1)
        self.tactic = None
        if not mid["fired"]:
            tb = panel(); tl = QVBoxLayout(tb); tl.setContentsMargins(16, 12, 16, 12)
            self.tactic = TacticPicker(s.get("tactic", "balanced"), s["rating"], tr("mid.second_half"))
            tl.addWidget(self.tactic)
            fp = FormationPicker(c, s.get("formation", squad_mod.DEFAULT_FORMATION))     # схему тоже можно сменить
            fp.changed.connect(lambda f: (s.__setitem__("formation", f), squad_mod.apply_to_world(c), self._fill_lineup())); tl.addWidget(fp)
            rp = RotationPicker(s.get("rotation", "none")); rp.changed.connect(lambda r: s.__setitem__("rotation", r)); tl.addWidget(rp)
            tl.addStretch()
            top.addWidget(tb, 1)
        mid_row = QHBoxLayout(); mid_row.setSpacing(14); root.addLayout(mid_row, 1)
        view = QTextBrowser(); view.setOpenLinks(False); mid_row.addWidget(view, 1)
        self.c = c
        self.lineup_host = QWidget(); self.lineup_lay = QVBoxLayout(self.lineup_host); self.lineup_lay.setContentsMargins(0, 0, 0, 0)
        if not mid["fired"]:                                  # основу на вторую половину можно поменять вручную
            mid_row.addWidget(self.lineup_host); self._fill_lineup()
        lg = d.leagues[mid["lid"]]
        x = {"name_ru": f"{tr('mid.table')}: {lg['name']}", "name_en": f"{tr('mid.table')}: {lg['name']}", "table": mid["table"],
             "result": {"rank": mid["rank"], "n": mid["n"], "pts": next(r[6] for r in mid["table"] if r[0] == cid)}}
        ev_html = squad_events_html(mid.get("squad_events") or [], c) if not mid["fired"] else ""
        view.setHtml(f"<body style='color:{theme.TEXT}; font-size:14px;'>{ev_html}{league_table_html(x, d, cid)}</body>")
        row = QHBoxLayout()
        if not mid["fired"]:
            wb = QPushButton(tr("tw.winter_btn")); wb.clicked.connect(lambda: self.winter.emit(self.tactic.value())); row.addWidget(wb)
        row.addStretch()
        btn = QPushButton(tr("mid.continue_fired") if mid["fired"] else tr("mid.continue")); btn.setObjectName("primary")
        btn.clicked.connect(lambda: self.done.emit(self.tactic.value() if self.tactic else ""))
        row.addWidget(btn); root.addLayout(row)

    def _fill_lineup(self):
        _clear(self.lineup_lay)
        self.lineup_lay.addWidget(lineup_panel(self.c, self._fill_lineup, hint=False))

# ======================================================================================= трансферное окно
def eur(x):
    """Деньги для бюджета: ноль - «€0 млн», а не «свободный трансфер»."""
    return money(x) if x > 0.004 else tr("money.m", v="0")

def squad_events_html(events, c):
    """События состава: травмы и дисквалификации, недовольные без игры, молодые без минут (группами)."""
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
        out.append(f"<div style='margin:3px 12px; color:{style[k]}'>• {tr('sqev.' + k)}: {escape(names)}</div>")
    return "".join(out)

def best_coach_html(r, d):
    """Таблица «Лучший тренер мира» (топ-5) и место тренера-игрока."""
    bc = r.get("best_coach")
    if not bc or not bc.get("top"):
        return ""
    h = [f"<div style='margin:10px 12px 2px 12px; font-weight:700'>{tr('bc.title')}</div>"
         f"<table cellspacing='0' cellpadding='3' style='margin:0 12px'>"]
    for i, x in enumerate(bc["top"], 1):
        col = theme.AWARD if x["me"] else theme.TEXT
        club = d.clubs[x["club"]]["name"] if x["club"] in d.clubs else ""
        h.append(f"<tr><td style='color:{theme.MUTED}'>{i}.</td><td style='color:{col}; font-weight:{700 if x['me'] else 400}'>"
                 f"{escape(x['name'])}</td><td style='color:{theme.MUTED}'>{escape(club)}</td><td align='right'>{x['pts']:.1f}</td></tr>")
    h.append("</table>")
    if bc.get("rank") and bc["rank"] > 5:
        h.append(f"<div style='margin:2px 12px; color:{theme.MUTED}'>{tr('bc.my_rank', r=bc['rank'])}</div>")
    return "".join(h)

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

def _item(text, align=Qt.AlignLeft, color=None, bold=False, tip=None, bg=None):
    it = QTableWidgetItem(str(text)); it.setTextAlignment(align | Qt.AlignVCenter)
    if color: it.setForeground(QColor(color))
    if bg: it.setBackground(QColor(bg))
    if bold:
        f = it.font(); f.setBold(True); it.setFont(f)
    if tip: it.setToolTip(tip)
    return it

def _small_button(text, enabled, on_click):
    b = QPushButton(text); b.setEnabled(enabled); b.clicked.connect(on_click)
    b.setStyleSheet("QPushButton { padding: 2px 10px; font-size: 13px; border-radius: 5px; }")
    b.setFixedHeight(26)
    return b

ROW_H = 32

def _compact_table(headers, widths):
    t = QTableWidget(0, len(headers)); t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setSelectionMode(QAbstractItemView.NoSelection)
    t.verticalHeader().setVisible(False); t.verticalHeader().setDefaultSectionSize(ROW_H)
    t.verticalHeader().setMinimumSectionSize(ROW_H)
    t.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); t.setTextElideMode(Qt.ElideRight); t.setShowGrid(False)
    h = t.horizontalHeader(); h.setStretchLastSection(False)
    for i, wd in enumerate(widths):
        if wd:
            t.setColumnWidth(i, wd)
        else:
            h.setSectionResizeMode(i, QHeaderView.Stretch)
    return t

def _fit_rows(t):
    """Небольшая таблица во всю свою высоту, без прокрутки (высота - по строкам и заголовку)."""
    t.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    t.setSizeAdjustPolicy(QAbstractItemView.AdjustToContents)
    head = t.horizontalHeader().sizeHint().height() if not t.horizontalHeader().isHidden() else 0
    t.setFixedHeight(head + t.rowCount() * ROW_H + 6)

def _cell_box(*widgets):
    """Ячейка с кнопками: по центру по вертикали, с отступами."""
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(4, 2, 4, 2); h.setSpacing(6)
    for x in widgets:
        h.addWidget(x)
    h.addStretch()
    return w

def inj_text(halves):
    """Срок травмы словами: полсезона, сезон, полтора сезона."""
    return tr("inj.len" + str(max(1, min(3, int(halves)))))

def pot_text(p, w=None):
    """Потенциал для таблиц: вилка у тех, кто ещё растёт (w - ширина по оценке скаутов), «на пике» или «угасание» (с 31 года)."""
    st, r = squad_mod.pot_state(p, w)
    return f"{r[0]}–{r[1]}" if st == "range" else tr("pot." + st)

def pot_item(p, w=None):
    st, r = squad_mod.pot_state(p, w)
    color = theme.ACCENT if st == "range" else theme.MUTED if st == "peak" else "#e59b5a"
    return _item(pot_text(p, w), Qt.AlignCenter, color=color, tip=tr("pot.scout_tip", w=w) if w is not None else None)

def pot_key(p, w=None):
    """Ключ сортировки по потенциалу: верх вилки, у остальных - нынешний OVR (угасающие ниже)."""
    st, r = squad_mod.pot_state(p, w)
    return r[1] if st == "range" else p["ovr"] - (0.5 if st == "decline" else 0)

def status_text(p, cid):
    """Состояние игрока для таблицы состава: травма / дисквалификация / просит трансфер / в аренде у нас. -> (текст, цвет)."""
    if p.get("inj"):
        return (tr("st.ban") if p.get("inj_kind") == "ban" else tr("st.injury", t=inj_text(p["inj"]))), theme.RED
    if p.get("unhappy"):
        return tr("st.unhappy"), "#e59b5a"
    if p.get("loan_from") and p["loan_from"] != cid:
        return tr("st.loan_in"), theme.MUTED
    return "", None

def fit_item(p):
    f = p.get("fit", 100.0)
    return _item(f"{f:.0f}%", Qt.AlignCenter, color=theme.ACCENT if f >= 85 else theme.GOLD if f >= 70 else theme.RED,
                 tip=tr("sq.fit_tip", v=f"{squad_mod.fatigue_pen(p):.1f}"))

def squad_table(c, d, formation, sell=None, loan=None):
    """Весь состав по линиям: позиция, игрок, возраст, OVR, потенциал, форма, рыночная стоимость, роль (основа на позиции схемы /
    ротация / резерв) или состояние (травма, дисквалификация, просит трансфер, предложение большого клуба);
    если sell - кнопка «Продать», если loan - «В аренду»."""
    from ..transfers import pot_width
    players = squad_mod.squad(c)
    cid = c.coach["club"]
    pw = pot_width(c.coach)
    xi = squad_mod.current_xi(c, formation)                     # основа, которая выходит на поле (автоматическая или ручная)
    xi_slot = {p["id"]: slot for slot, p, _ in xi if p}
    role = squad_mod.roles(c, formation)
    win = c.coach.get("window") or {}
    offers = win.get("offers", {})
    tw = c.coaching().window() if sell else None
    cols = [tr("col.pos"), tr("col.player"), tr("col.age"), tr("col.ovr"), tr("col.pot"), tr("col.fit"), tr("col.value"),
            tr("col.role")] + ([""] if sell else [])
    t = _compact_table(cols, [48, 0, 50, 46, 82, 60, 92, 300 if sell else 250] + ([196] if sell else []))
    t.horizontalHeaderItem(7).setToolTip(tr("role.hint"))
    for ln in squad_mod.LINES:
        group = [p for p in players if squad_mod.LINE[p["pos"]] == ln]
        if not group:
            continue
        r = t.rowCount(); t.insertRow(r)
        t.setItem(r, 0, _item(f"{tr('line.' + ln)} ({len(group)})", color=theme.MUTED, bold=True, bg=theme.PANEL2))
        t.setSpan(r, 0, 1, t.columnCount())
        order = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "CF", "ST"]
        for p in sorted(group, key=lambda x: (order.index(x["pos"]), -x["ovr"])):
            r = t.rowCount(); t.insertRow(r)
            starter = p["id"] in xi_slot
            col = theme.GOLD if p["id"] in offers else (theme.TEXT if starter else None)
            slot = xi_slot.get(p["id"])
            rl = role.get(p["id"], "res")
            role_txt = tr("role.xi_at", s=slot) if starter and slot != p["pos"] else tr("role." + rl)
            role_col = theme.ACCENT if starter else theme.TEXT if rl == "rot" else theme.MUTED
            stt, stc = status_text(p, cid)
            off = offers.get(p["id"])
            if off:                                            # большой клуб хочет игрока: клуб и сумма - вместо роли
                stt, stc = tr("sq.offer", club=d.clubs[off["club"]]["name"], fee=eur(off["fee"])), theme.GOLD
            name = p["name"] + ("  ★" if p.get("real") else "")
            t.setItem(r, 0, _item(p["pos"], Qt.AlignCenter, color=col, bold=starter))
            t.setItem(r, 1, _item(name, color=col, bold=starter, tip=p["name"]))
            t.setItem(r, 2, _item(p["age"], Qt.AlignCenter, color=col))
            t.setItem(r, 3, _item(f"{p['ovr']:.0f}", Qt.AlignCenter, color=col, bold=starter))
            t.setItem(r, 4, pot_item(p, pw))
            t.setItem(r, 5, fit_item(p))
            t.setItem(r, 6, _item(eur(price(p["ovr"], p["age"], p["pot"])), Qt.AlignRight, color=theme.MUTED,
                                  tip=tr("sq.value_tip")))
            t.setItem(r, 7, _item(stt or role_txt, color=stc or role_col, bold=bool(off),
                                  tip=(tr("sq.offer_tip", club=d.clubs[off["club"]]["name"], fee=eur(off["fee"])) if off else
                                       stt or tr("role.hint"))))
            if sell:
                loaned_in = bool(p.get("loan_from")) and p["loan_from"] != cid
                if loaned_in:
                    t.setCellWidget(r, 8, _cell_box(label(tr("st.loan_until"), "muted")))
                    continue
                b = _small_button(tr("tw.sell"), True, lambda _=False, pid=p["id"]: sell(pid))
                b.setToolTip(tr("tw.sell_tip", f=eur(tw.sale_fee(p)), v=f"{tw.loss(p):.1f}"))
                if off:
                    b.setStyleSheet(b.styleSheet() + f" QPushButton {{ color: {theme.GOLD}; border-color: {theme.GOLD}; }}")
                    b.setText(f"{tr('tw.sell')} {eur(off['fee'])}")
                items = [b]
                if loan:
                    lb = _small_button(tr("tw.loan_out"), True, lambda _=False, pid=p["id"]: loan(pid))
                    lb.setToolTip(tr("tw.loan_out_tip")); items.append(lb)
                t.setCellWidget(r, 8, _cell_box(*items))
    return t

def _clear(lay):
    """Убрать все виджеты из раскладки (старые таблицы исчезают сразу, без «призраков»)."""
    while lay.count():
        wdg = lay.takeAt(0).widget()
        if wdg:
            wdg.hide(); wdg.setParent(None); wdg.deleteLater()

def lineup_tab(c, on_change):
    """Вкладка «Основа»: слева выбор игроков по позициям, справа - сила основы и пояснение ролей."""
    host = QWidget(); h = QHBoxLayout(host); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(24)
    h.addWidget(lineup_panel(c, on_change, 480))
    side = QVBoxLayout(); side.setSpacing(8)
    f = c.coach.get("formation", squad_mod.DEFAULT_FORMATION)
    side.addWidget(label(tr("sq.xi", o=f"{squad_mod.team_rating(c, f):.1f}"), "h2"))
    rl = squad_mod.roles(c, f)
    side.addWidget(label(tr("role.counts", x=sum(1 for v in rl.values() if v == "xi"), r=sum(1 for v in rl.values() if v == "rot"),
                            s=sum(1 for v in rl.values() if v == "res")), None, True))
    side.addWidget(label(tr("role.hint"), "muted", True))
    side.addWidget(label(tr("rot.hint"), "muted", True))
    side.addStretch()
    h.addLayout(side, 1)
    return host

def formation_name(f):
    """'4-3-3 att' -> '4-3-3 (атакующая)'."""
    base, style = squad_mod.formation_parts(f)
    return f"{base} ({tr('fstyle.' + style)})"

def lineup_set(c, i, pid):
    squad_mod.set_lineup(c, i, pid)
    squad_mod.apply_to_world(c)

def lineup_auto(c, on):
    s = c.coach
    if on:
        s["lineup_mode"] = "auto"
    else:                                                      # вручную: начинаем с нынешней основы
        f = s.get("formation", squad_mod.DEFAULT_FORMATION)
        s.setdefault("lineup", {})[f] = [p["id"] if p else None for _, p, _ in squad_mod.current_xi(c, f)]
        s["lineup_mode"] = "manual"
    squad_mod.apply_to_world(c)

def lineup_panel(c, on_change, width=360, hint=True):
    """Основа вручную: на каждую позицию схемы - выпадающий список игроков (с OVR на этой позиции). Есть на экране клуба,
    в трансферном окне и в середине сезона. on_change() - после изменения (экран перестраивается)."""
    s = c.coach
    f = s.get("formation", squad_mod.DEFAULT_FORMATION)
    box = QWidget(); box.setFixedWidth(width); v = QVBoxLayout(box); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(4)
    v.addWidget(label(tr("lineup.title", f=formation_name(f)), "h2"))
    auto = QCheckBox(tr("lineup.auto")); auto.setChecked(s.get("lineup_mode") != "manual")
    auto.toggled.connect(lambda on: (lineup_auto(c, on), on_change())); v.addWidget(auto)
    players = squad_mod.squad(c)
    for i, (slot, p, val) in enumerate(squad_mod.current_xi(c, f)):
        r = QHBoxLayout(); r.setSpacing(6)
        sl = label(slot, None); sl.setFixedWidth(40); sl.setStyleSheet("font-weight: 700;"); r.addWidget(sl)
        cb = QComboBox(); cb.setStyleSheet("QComboBox { padding: 3px 6px; min-width: 0; }")
        opts = sorted(players, key=lambda x: (not squad_mod.available(x), -(squad_mod.eff(x) - squad_mod.penalty(x["pos"], slot))))
        for x in opts:
            eff = squad_mod.eff(x) - squad_mod.penalty(x["pos"], slot)
            txt = tr("lineup.option", name=x["name"], pos=x["pos"], ovr=f"{x['ovr']:.0f}", eff=f"{eff:.0f}")
            if not squad_mod.available(x):
                txt += "  · " + status_text(x, s["club"])[0]
            cb.addItem(txt, x["id"])
        if p:
            cb.setCurrentIndex(max(0, cb.findData(p["id"])))
        cb.activated.connect(lambda _k, i=i, cb=cb: (lineup_set(c, i, cb.currentData()), on_change()))
        r.addWidget(cb, 1); v.addLayout(r)
    if hint:
        v.addWidget(label(tr("lineup.hint"), "muted", True))
    v.addStretch()
    return box

class FormationPicker(QWidget):
    """Выбор схемы: в списке - сила основы для каждой схемы с нынешним составом."""
    changed = Signal(str)

    def __init__(self, c, current):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(8)
        h.addWidget(label(tr("formation.title"), "h2"))
        self.box = QComboBox()
        players = squad_mod.squad(c)
        for f in squad_mod.FORMATIONS:
            self.box.addItem(tr("formation.item", f=formation_name(f), o=f"{squad_mod.xi_rating(players, f):.1f}"), f)
            self.box.setItemData(self.box.count() - 1, " · ".join(squad_mod.FORMATIONS[f][0][1:]), Qt.ToolTipRole)
        self.box.setCurrentIndex(list(squad_mod.FORMATIONS).index(current) if current in squad_mod.FORMATIONS else 0)
        self.box.setToolTip(tr("formation.hint"))
        self.box.currentIndexChanged.connect(lambda: self.changed.emit(self.box.currentData()))
        h.addWidget(self.box); h.addStretch()

    def value(self):
        return self.box.currentData()

class RotationPicker(QWidget):
    """Ротация: сколько минут получают запасные (основа меньше устаёт и реже травмируется, запасные довольны и растут)."""
    changed = Signal(str)

    def __init__(self, current):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(8)
        h.addWidget(label(tr("rot.title"), "h2"))
        self.box = QComboBox()
        for k in squad_mod.ROTATION:
            self.box.addItem(tr("rot." + k), k)
        self.box.setCurrentIndex(max(0, self.box.findData(current)))
        self.box.setToolTip(tr("rot.hint"))
        self.box.currentIndexChanged.connect(lambda: self.changed.emit(self.box.currentData()))
        h.addWidget(self.box); h.addStretch()

class TransferWindowPage(QWidget):
    """Трансферное окно: рынок и молодёжь (слева), весь состав с продажами (справа), бюджет и сила основы сверху."""
    buy = Signal(int); sell = Signal(str); youth = Signal(int); done = Signal(); formation = Signal(str)
    action = Signal(str, object)          # loan_out (id игрока), loan_offer (номер), hire / fire (номер скаута)

    def __init__(self, career, data, start_ovr):
        super().__init__(); self.setObjectName("page")
        c, d, w, s = career, data, career.world, career.coach
        win, cid = s["window"], s["club"]
        tw = c.coaching().window()
        team = tw.rating()
        root = QVBoxLayout(self); root.setContentsMargins(24, 16, 24, 16); root.setSpacing(8)
        root.addWidget(label(tr("tw." + win["kind"], y=c.year if win["kind"] == "summer" else c.year + 1), "title"))
        info = panel(); il = QHBoxLayout(info); il.setContentsMargins(14, 6, 14, 6); il.setSpacing(24)
        bl = label(tr("tw.budget", b=eur(s["budget"])), "h2"); bl.setStyleSheet(f"color: {theme.GOLD};"); il.addWidget(bl)
        tl = tr("tw.team_change", a=f"{start_ovr:.1f}", b=f"{team:.1f}") if abs(team - start_ovr) > 0.05 else tr("tw.team", o=f"{team:.1f}")
        il.addWidget(label(tl, "h2"))
        rank, n, kind = c.coaching().expected(cid)
        il.addWidget(label(tr("tw.target", t=kind_text(kind), r=rank), "muted"))
        fp = FormationPicker(c, s.get("formation", squad_mod.DEFAULT_FORMATION)); fp.changed.connect(self.formation.emit); il.addWidget(fp)
        il.addStretch(); root.addWidget(info)
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
        for nt in notes:
            root.addWidget(label(nt, "muted", True))
        # --- вкладки во всю ширину: рынок, ваша команда (продажа, аренда), основа, предложения аренды, скауты
        self.c, self.d, self.win, self.tw = c, d, win, tw
        from ..transfers import pot_width, scouting
        self.pw = pot_width(s)
        self.ltabs = QTabWidget()
        mhost = QWidget(); left = QVBoxLayout(mhost); left.setContentsMargins(10, 8, 10, 8); left.setSpacing(6)
        mh = QHBoxLayout(); mh.setSpacing(12); mh.addWidget(label(tr("tw.market"), "h2"))
        mh.addWidget(label(tr("tw.scouting", q=f"{100 * scouting(s):.0f}", w=self.pw), "muted")); mh.addStretch()
        mh.addWidget(label(tr("tw.filter"), "muted"))
        self.filter = QComboBox(); self.filter.addItem(tr("filter.all"), "")
        for ln in squad_mod.LINES:
            self.filter.addItem(tr("line." + ln), ln)
        self.filter.setCurrentIndex(max(0, self.filter.findData(win.get("filter", ""))))
        self.filter.currentIndexChanged.connect(self._filter_changed); mh.addWidget(self.filter)
        left.addLayout(mh)
        widths = [0, 60, 60, 54, 100, 260, 110, 80, 150]
        self.mt = _compact_table([tr("col.player"), tr("col.pos"), tr("col.age"), tr("col.ovr"), tr("col.pot"), tr("col.club"), tr("col.price"),
                                  tr("col.effect"), ""], widths)
        self.mt.setToolTip(tr("tw.sort_hint"))
        h = self.mt.horizontalHeader(); h.setSectionsClickable(True); h.sectionClicked.connect(self._sort_clicked)
        self.gains = {i: (tw.gain(cd) if not cd["done"] else 0.0) for i, cd in enumerate(win["cands"])}
        self._fill_market()
        left.addWidget(self.mt, 1)
        if win["youth"]:
            left.addWidget(label(tr("tw.youth"), "h2"))
            yt = _compact_table([""] * 9, widths)
            full = tw.squad_full()
            for i, y in enumerate(win["youth"]):
                r = yt.rowCount(); yt.insertRow(r)
                ok = not y["done"] and y["price"] <= s["budget"] + 1e-9 and not (y["kind"] == "talent" and full)
                if y["kind"] == "talent":
                    yp = {"age": 17, "ovr": y["ovr"], "pot": y["pot"], "name": y["name"]}
                    yt.setItem(r, 0, _item(tr("tw.youth_talent", name=y["name"]), bold=True))
                    yt.setItem(r, 1, _item(y["pos"], Qt.AlignCenter)); yt.setItem(r, 2, _item(17, Qt.AlignCenter))
                    yt.setItem(r, 3, _item(f"{y['ovr']:.0f}", Qt.AlignCenter, bold=True)); yt.setItem(r, 4, pot_item(yp, self.pw))
                    yt.setItem(r, 5, _item(tr("tw.academy_src"), color=theme.MUTED))
                else:
                    yt.setItem(r, 0, _item(tr("tw.academy"), bold=True))
                    yt.setItem(r, 1, _item(tr("tw.academy_line"), color=theme.MUTED)); yt.setSpan(r, 1, 1, 5)
                yt.setItem(r, 6, _item(eur(y["price"]), Qt.AlignRight, color=theme.GOLD))
                yt.setCellWidget(r, 8, _cell_box(_small_button(tr("tw.bought") if y["done"] else tr("tw.buy"), ok,
                                                               lambda _=False, i=i: self.youth.emit(i))))
            yt.horizontalHeader().setVisible(False); _fit_rows(yt)
            left.addWidget(yt)
        self.ltabs.addTab(mhost, tr("tw.tab_market"))
        # ваша команда
        shost = QWidget(); sv = QVBoxLayout(shost); sv.setContentsMargins(10, 8, 10, 8); sv.setSpacing(6)
        players = squad_mod.squad(c); lc = squad_mod.line_counts(players)
        sv.addWidget(label(tr("sq.counts", n=len(players), g=lc["GK"], d=lc["DEF"], m=lc["MID"], a=lc["ATT"]), "muted"))
        sv.addWidget(squad_table(c, d, s.get("formation", squad_mod.DEFAULT_FORMATION), sell=self.sell.emit,
                                 loan=lambda pid: self.action.emit("loan_out", pid)), 1)
        self.ltabs.addTab(shost, tr("tw.squad") + f" ({len(players)})")
        # основа (вручную - и после сделок)
        lhost = QWidget(); lv = QVBoxLayout(lhost); lv.setContentsMargins(10, 8, 10, 8)
        lv.addWidget(lineup_tab(c, lambda: self.action.emit("refresh", None)))
        self.ltabs.addTab(lhost, tr("tab.lineup"))
        n_lo = sum(1 for o in win.get("loan_offers", []) if not o["done"])
        self.ltabs.addTab(self._loans_tab(), tr("tw.tab_loans") + (f" ({n_lo})" if n_lo else ""))
        self.ltabs.addTab(self._scouts_tab(), tr("tw.tab_scouts") + f" ({len(s.get('scouts') or [])})")
        self.ltabs.setCurrentIndex(win.get("tab", 0))
        self.ltabs.currentChanged.connect(lambda i: win.__setitem__("tab", i))
        root.addWidget(self.ltabs, 1)
        row = QHBoxLayout(); row.addWidget(label(tr("tw.hint"), "muted", True), 1)
        b = QPushButton(tr("tw.done")); b.setObjectName("primary"); b.clicked.connect(self.done.emit); row.addWidget(b)
        root.addLayout(row)

    def _loans_tab(self):
        """Аренда: предложения других клубов взять ваших игроков и ваши игроки, которые сейчас в аренде."""
        from .. import stars as stars_mod
        c, d, win = self.c, self.d, self.win
        cid = c.coach["club"]
        host = QWidget(); v = QVBoxLayout(host); v.setContentsMargins(10, 8, 10, 8); v.setSpacing(6)
        v.addWidget(label(tr("tw.loan_offers"), "h2"))
        offers = win.get("loan_offers") or []
        if offers:
            t = _compact_table([tr("col.player"), tr("col.pos"), tr("col.age"), tr("col.ovr"), tr("col.pot"), tr("col.club"), tr("col.fee"), ""],
                               [0, 60, 60, 54, 100, 280, 110, 130])
            for i, o in enumerate(offers):
                p = stars_mod.find(c.stars, o["pid"])
                if not p:
                    continue
                r = t.rowCount(); t.insertRow(r)
                t.setItem(r, 0, _item(p["name"], bold=True)); t.setItem(r, 1, _item(p["pos"], Qt.AlignCenter))
                t.setItem(r, 2, _item(p["age"], Qt.AlignCenter)); t.setItem(r, 3, _item(f"{p['ovr']:.0f}", Qt.AlignCenter))
                t.setItem(r, 4, pot_item(p, self.pw)); t.setItem(r, 5, _item(d.clubs[o["club"]]["name"], color=theme.MUTED))
                t.setItem(r, 6, _item(eur(o["fee"]), Qt.AlignRight, color=theme.GOLD))
                ok = not o["done"] and p["club"] == cid
                t.setCellWidget(r, 7, _cell_box(_small_button(tr("tw.loan_done") if o["done"] else tr("tw.loan_accept"), ok,
                                                              lambda _=False, i=i: self.action.emit("loan_offer", i))))
            _fit_rows(t)
            v.addWidget(t)
        else:
            v.addWidget(label(tr("tw.no_loan_offers"), "muted", True))
        away = [p for p in stars_mod.all_players(c.stars) if p.get("loan_from") == cid and p["club"] != cid]
        v.addWidget(label(tr("tw.on_loan"), "h2"))
        if away:
            for p in away:
                v.addWidget(label(tr("tw.on_loan_row", n=p["name"], pos=p["pos"], o=f"{p['ovr']:.0f}", club=d.clubs[p["club"]]["name"],
                                     m=round(100 * p.get("loan_min", 0.5))), None, True))
        else:
            v.addWidget(label(tr("end.none"), "muted"))
        v.addWidget(label(tr("tw.loan_hint"), "muted", True)); v.addStretch()
        return host

    def _scouts_tab(self):
        """Скауты: нанятые (уволить) и свободные этим летом (нанять). Звёзды - по рейтингу скаута."""
        from ..transfers import MAX_SCOUTS
        s, win = self.c.coach, self.win
        host = QWidget(); v = QVBoxLayout(host); v.setContentsMargins(10, 8, 10, 8); v.setSpacing(6)
        v.addWidget(label(tr("sc.mine", n=len(s.get("scouts") or []), m=MAX_SCOUTS), "h2"))
        def table(rows, btn, enabled, sig):
            t = _compact_table([tr("sc.name"), tr("sc.stars"), tr("sc.rating"), tr("sc.salary"), ""], [0, 140, 100, 150, 130])
            for i, x in enumerate(rows):
                r = t.rowCount(); t.insertRow(r)
                t.setItem(r, 0, _item(x["name"], bold=True))
                t.setItem(r, 1, _item("★" * x["stars"], Qt.AlignCenter, color=theme.GOLD))
                t.setItem(r, 2, _item(x["rating"], Qt.AlignCenter)); t.setItem(r, 3, _item(eur(x["salary"]), Qt.AlignRight, color=theme.MUTED))
                t.setCellWidget(r, 4, _cell_box(_small_button(btn(x), enabled(x), lambda _=False, i=i: self.action.emit(sig, i))))
            _fit_rows(t)
            return t
        mine = s.get("scouts") or []
        if mine:
            v.addWidget(table(mine, lambda x: tr("sc.fire"), lambda x: True, "fire"))
        else:
            v.addWidget(label(tr("sc.none"), "muted", True))
        market = win.get("scout_market") or []
        if market:
            v.addWidget(label(tr("sc.market"), "h2"))
            full = len(mine) >= MAX_SCOUTS
            v.addWidget(table(market, lambda x: tr("sc.hired") if x["done"] else tr("sc.hire"),
                              lambda x: not x["done"] and not full and x["salary"] <= s["budget"] + 1e-9, "hire"))
        elif win["kind"] == "winter":
            v.addWidget(label(tr("sc.summer_only"), "muted", True))
        v.addWidget(label(tr("sc.hint"), "muted", True)); v.addStretch()
        return host

    POS_ORDER = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LM", "RM", "LW", "RW", "CF", "ST"]

    def _market_key(self, col, i):
        cd, d = self.win["cands"][i], self.d
        return [lambda: cd["name"].lower(), lambda: self.POS_ORDER.index(cd["pos"]), lambda: cd["age"], lambda: cd["ovr"],
                lambda: pot_key(cd, self.pw), lambda: (d.clubs[cd["club"]]["name"] if cd.get("club") else "").lower(),
                lambda: cd["price"], lambda: self.gains[i]][col]()

    def _sort_clicked(self, col):
        """Щелчок по заголовку: от большего -> от меньшего -> исходный порядок (состояние в окне, переживает перестройку экрана)."""
        if col >= 8:
            return
        cur = self.win.get("sort")
        self.win["sort"] = [col, 1] if not cur or cur[0] != col else ([col, 2] if cur[1] == 1 else None)
        self._fill_market()

    def _filter_changed(self):
        self.win["filter"] = self.filter.currentData()
        self._fill_market()

    def _fill_market(self):
        c, d, s, win, mt = self.c, self.d, self.c.coach, self.win, self.mt
        full = self.tw.squad_full()
        idx = [i for i, cd in enumerate(win["cands"]) if not win.get("filter") or squad_mod.LINE[cd["pos"]] == win["filter"]]
        h = mt.horizontalHeader()
        if win.get("sort"):
            col, st = win["sort"]
            idx.sort(key=lambda i: self._market_key(col, i), reverse=(st == 1))
            h.setSortIndicatorShown(True); h.setSortIndicator(col, Qt.DescendingOrder if st == 1 else Qt.AscendingOrder)
        else:
            h.setSortIndicatorShown(False)
        mt.setRowCount(0)
        for i in idx:
            cd = win["cands"][i]
            r = mt.rowCount(); mt.insertRow(r)
            real = bool(cd.get("pid")) and bool((stars_find(c, cd["pid"]) or {}).get("real"))
            club = d.clubs[cd["club"]]["name"] if cd.get("club") else tr("tw.free_agent")
            if cd.get("loan"):
                club = tr("tw.loan_from", club=club)
            g = self.gains[i]
            ok = not cd["done"] and not cd.get("refuse") and cd["price"] <= s["budget"] + 1e-9 and not full
            colr = theme.AWARD if cd.get("pid") else theme.ACCENT if cd.get("gem") else None
            name = cd["name"] + ("  ★" if real else "") + ("  ◆" if cd.get("gem") else "")
            mt.setItem(r, 0, _item(name, color=colr, bold=bool(cd.get("pid")) or cd.get("gem", False),
                                   tip=tr("tw.gem_tip") if cd.get("gem") else None))
            mt.setItem(r, 1, _item(cd["pos"], Qt.AlignCenter)); mt.setItem(r, 2, _item(cd["age"], Qt.AlignCenter))
            mt.setItem(r, 3, _item(f"{cd['ovr']:.0f}", Qt.AlignCenter, bold=True))
            mt.setItem(r, 4, pot_item(cd, self.pw))
            mt.setItem(r, 5, _item(club, color=theme.MUTED, tip=tr("tw.loan_tip") if cd.get("loan") else None))
            mt.setItem(r, 6, _item(eur(cd["price"]), Qt.AlignRight, color=theme.GOLD))
            mt.setItem(r, 7, _item(f"+{g:.1f}" if g >= 0.05 else "—", Qt.AlignCenter, color=theme.ACCENT if g >= 0.05 else theme.MUTED,
                                   tip=tr("tw.effect_plus", v=f"{g:.1f}") if g >= 0.05 else tr("tw.effect_none")))
            if cd.get("refuse") and not cd["done"]:
                b = _small_button(tr("tw.refuse"), False, lambda: None); b.setToolTip(tr("tw.refuse_tip"))
                mt.setCellWidget(r, 8, _cell_box(b))
                continue
            buy_txt = tr("tw.loan_take") if cd.get("loan") else tr("tw.buy")
            btn = tr("tw.bought") if cd["done"] else buy_txt if ok else (tr("tw.no_money") if cd["price"] > s["budget"] else buy_txt)
            mt.setCellWidget(r, 8, _cell_box(_small_button(btn, ok, lambda _=False, i=i: self.buy.emit(i))))

def stars_find(c, pid):
    from .. import stars as stars_mod
    return stars_mod.find(c.stars, pid)

# ======================================================================================= итоги сезона
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

def coach_season_html(c, d, r):
    h = [f"<body style='color:{theme.TEXT}; font-size:14px;'>"]
    lg = f"{r['league_name']} ({d.country_name(r['league_country'], i18n.LANG)})"
    h.append(f"<div style='margin-top:6px; padding:8px 12px; background:{theme.PANEL2}; border-radius:8px;'>"
             f"<span style='font-size:17px; font-weight:700;'>{escape(r['club_name'])}</span> &nbsp; "
             f"<span style='color:{theme.MUTED}'>{escape(lg)} · {tr('career.age', n=r['age'])} · {tr('coach.project.' + r['project'])}</span></div>")
    diff = r["target"] - r["rank"]
    col = theme.ACCENT if diff > 0 else theme.RED if diff < -1 else theme.TEXT
    h.append("<table width='100%' cellspacing='0' cellpadding='0'><tr><td width='55%' valign='top'>")
    h.append(f"<div style='margin:10px 12px 4px 12px; font-size:15px; color:{col}; font-weight:700'>"
             f"{tr('creport.place', r=r['rank'], n=r['n'], t=kind_text(r['kind']), e=r['target'])}</div>")
    tac = [t for t in (r.get("tactics") or []) if t]
    if tac:
        txt = tr("creport.tactics", a=tactic_name(tac[0]), b=tactic_name(tac[1])) if len(tac) > 1 else tr("creport.tactics1", a=tactic_name(tac[0]))
        h.append(f"<div style='margin:2px 12px; color:{theme.MUTED}'>{txt}</div>")
    mid = r.get("mid")
    if mid:
        mid_txt = tr("creport.mid", r=mid["rank"], n=mid["n"], a=f"{mid['anger']:.0f}")
        h.append(f"<div style='margin:2px 12px; color:{theme.MUTED}'>{mid_txt}</div>")
    for t in r["trophies"]:
        h.append(f"<div style='margin:3px 12px; color:{theme.GOLD}'>◆ {escape(trophy_name(t))}</div>")
    for a in r["awards"]:
        h.append(f"<div style='margin:3px 12px; color:{theme.AWARD}'>★ {escape(award_name(a))}</div>")
    for e in r.get("events", []):
        h.append(f"<div style='margin:3px 12px; color:#e59b5a'>• {tr('event.' + e['t'])}</div>")
    fin = r.get("fin")
    if fin:
        h.append(f"<div style='margin:8px 12px 2px 12px; color:{theme.MUTED}'>"
                 f"{tr('creport.fin', s=eur(fin['spent']), i=eur(fin['income']), b=eur(fin['budget']), p=eur(fin.get('prize', 0.0)))}</div>")
    for m in r.get("moves", []):
        h.append(f"<div style='margin:1px 12px; color:{theme.MUTED}; font-size:13px'>• {escape(deal_text(m))}</div>")
    sq = squad_events_html(r.get("squad_events") or [], c)
    if sq:
        h.append(f"<div style='margin:8px 12px 2px 12px; font-weight:700'>{tr('sqev.title')}</div>{sq}")
    h.append(best_coach_html(r, d))
    # --- руководство
    a, b = r["anger_before"], r["anger_after"]
    h.append("</td><td width='45%' valign='top'>")
    h.append(f"<table width='100%' cellspacing='0' cellpadding='10' style='margin:8px 4px 8px 12px;' bgcolor='{theme.PANEL2}'><tr><td>"
             f"<div style='font-weight:700; margin-bottom:4px'>{tr('creport.board')}</div>"
             f"<div style='font-size:16px; color:{anger_color(b)}; font-weight:700'>{tr('creport.anger', a=f'{a:.0f}', b=f'{b:.0f}')}</div>")
    v = r.get("verdict")
    if v != "fired_mid":
        decay = round(a * DECAY - a, 1)
        if decay:
            h.append(f"<div style='color:{theme.MUTED}'>{tr('creport.decay', v=f'{decay:+.0f}')}</div>")
    for key, val in r["reasons"]:
        if abs(val) < 0.5:
            continue
        cv = theme.RED if val > 0 else theme.ACCENT
        h.append(f"<div>{escape(board_reason_text(key, r))}: <span style='color:{cv}; font-weight:700'>{val:+.0f}</span></div>")
    h.append(f"<div style='color:{theme.MUTED}; font-size:12px; margin-top:4px'>{tr('board.pressure', p=r['pressure'])}</div>")
    msg = tr("creport.fired_mid") if v == "fired_mid" else tr("creport." + v) if v else tr("creport.continue_warn" if b >= 60 else "creport.continue_ok")
    mc = theme.RED if (v or "").startswith("fired") or (not v and b >= 60) else theme.ACCENT if not v else theme.GOLD
    h.append(f"<div style='margin-top:8px; color:{mc}; font-weight:700'>{msg}</div></td></tr></table>")
    h.append("</td></tr></table>")
    h.append(details_html(c, d, r))                                  # таблица лиги и путь в кубках
    h.append("</body>")
    return "".join(h)

class CoachReportPage(QWidget):
    done = Signal(); diary = Signal(str)

    def __init__(self, career, data, rec):
        super().__init__(); self.setObjectName("page")
        root = QVBoxLayout(self); root.setContentsMargins(32, 24, 32, 24); root.setSpacing(12)
        root.addWidget(label(tr("creport.title", s=rec["season"]), "title"))
        view = QTextBrowser(); view.setOpenLinks(False); root.addWidget(view, 1)
        view.setHtml(coach_season_html(career, data, rec))
        row = QHBoxLayout()
        key = f"c:{len(career.coach['seasons']) - 1}"
        dz = QPushButton(f"{tr('web.diary_btn')} {rec['season']}"); dz.clicked.connect(lambda: self.diary.emit(key)); row.addWidget(dz)
        row.addStretch()
        btn = QPushButton(tr("report.continue")); btn.setObjectName("primary"); btn.clicked.connect(self.done.emit); row.addWidget(btn)
        root.addLayout(row)

# ======================================================================================= рекорды и итоги
def records_rows(rec, d):
    """Рекорды тренера -> [(название, значение)], только непустые."""
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
        out.append((tr("rec.trophies_by_club"), "\n".join(tr("rec.trophies_club_val", club=name(c), n=v["all"], t=v["titles"])
                                                           for c, v in rec["trophies_by_club"])))
    return out

def records_compact(rec, d):
    """Короткий список рекордов для экрана клуба (до 4 строк)."""
    rows = records_rows(rec, d)[:4]
    return "\n".join(f"{k}: {v}" for k, v in rows)

def coach_summary_widget(c, d):
    s = c.coach
    cc = c.coaching()
    sm = cc.summary()
    wdg = QWidget(); wdg.setObjectName("scrollhost")              # прозрачный фон внутри прокрутки (theme.py)
    g = QGridLayout(wdg); g.setContentsMargins(24, 20, 24, 20); g.setVerticalSpacing(10); g.setHorizontalSpacing(30)
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
            (tr("end.coach_clubs"), "  →  ".join(spells) or tr("end.none"))]
    rec = records_rows(cc.records(), d)
    i = 0
    for k, v in rows:
        g.addWidget(label(k, "muted"), i, 0, Qt.AlignTop); g.addWidget(label(str(v), "h2" if i < 3 else None, True), i, 1); i += 1
    if rec:
        g.addWidget(label(tr("rec.title"), "h2"), i, 0, 1, 2); i += 1
        for k, v in rec:
            g.addWidget(label(k, "muted"), i, 0, Qt.AlignTop)
            lv = label(v, None, True); lv.setStyleSheet(f"color: {theme.GOLD};"); g.addWidget(lv, i, 1); i += 1
    g.setRowStretch(i, 1); g.setColumnStretch(1, 1)
    return scroll(wdg)
