"""Экраны приложения."""
import random
from html import escape
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QVBoxLayout,
                               QGridLayout, QButtonGroup, QRadioButton, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
                               QTextBrowser, QTabWidget, QAbstractItemView, QSpinBox)
from .. import i18n
from ..i18n import tr
from ..career import market_value
from ..positions import POSITIONS, OUT_ATTRS, TYPICAL_HEIGHT, HEIGHT_MIN, HEIGHT_MAX, LEFT_SIDE, RIGHT_SIDE
from ..stars import gen_name
from .. import stars as stars_mod
from ..text import (money, trophy_name, stage, stars_text, event_text, short_trophy, intl_line, lang_name, club_result, nat_comp_name,
                    nat_result, group_line, award_name, season_award_names, score_text, chronicle_text)
from . import theme
from .widgets import PlayerCard, OvrChart, ClubCard, logo_label, club_pixmap

POS_GROUPS = [("gk", ["GK"]), ("def", ["CB", "LB", "RB"]), ("mid", ["CDM", "CM", "CAM", "LM", "RM"]), ("att", ["LW", "RW", "CF", "ST"])]

def page():
    w = QWidget(); w.setObjectName("page"); return w

def label(text, name=None, wrap=False):
    l = QLabel(text)
    if name: l.setObjectName(name)
    l.setWordWrap(wrap)
    return l

def panel():
    f = QFrame(); f.setObjectName("panel"); return f

def pos_text(pos):
    return f"{pos} · {tr('pos.' + pos)}"

def scroll(host):
    """Прокручиваемая область. Прозрачный фон задаётся в общей таблице стилей (theme.py), а не здесь:
    стиль без селектора, заданный прямо на виджет, наследуют все кнопки внутри, и они теряют свой цвет."""
    sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(host)
    return sc

def youth_league_name(s):
    c = (s.get("comps") or [None])[0]
    if s["youth"] and c and c.get("code") == "youth":
        return lang_name(c)
    return ("U-18 · " if s["youth"] else "") + s["league_name"]

# ======================================================================================= старт
class StartPage(QWidget):
    proceed = Signal(str, str, str, str, int)          # имя, страна, позиция, ведущая нога, рост
    load_clicked = Signal()
    lang_changed = Signal(str)
    settings_clicked = Signal()

    def __init__(self, data):
        super().__init__(); self.setObjectName("page")
        self.d, self.nat, self.pos = data, None, None
        root = QVBoxLayout(self); root.setContentsMargins(32, 24, 32, 24); root.setSpacing(16)
        top = QHBoxLayout(); top.addWidget(label(tr("start.heading"), "title")); top.addStretch()
        top.addWidget(label(tr("start.lang"), "muted"))
        self.lang = QComboBox(); self.lang.addItem("Русский", "ru"); self.lang.addItem("English", "en")
        self.lang.setCurrentIndex(0 if i18n.LANG == "ru" else 1)
        self.lang.currentIndexChanged.connect(lambda: self.lang_changed.emit(self.lang.currentData()))
        top.addWidget(self.lang)
        self.btn_load = QPushButton(tr("start.load")); self.btn_load.clicked.connect(self.load_clicked.emit); top.addWidget(self.btn_load)
        st = QPushButton("⚙ " + tr("web.settings")); st.clicked.connect(self.settings_clicked.emit); top.addWidget(st)
        root.addLayout(top)
        body = QHBoxLayout(); body.setSpacing(20); root.addLayout(body, 1)

        left = panel(); ll = QVBoxLayout(left); ll.setContentsMargins(18, 16, 18, 16); ll.setSpacing(8)
        ll.addWidget(label(tr("start.name"), "muted"))
        nrow = QHBoxLayout(); nrow.setSpacing(8)
        self.first = QLineEdit(); self.first.setPlaceholderText(tr("start.first")); nrow.addWidget(self.first, 1)
        self.last = QLineEdit(); self.last.setPlaceholderText(tr("start.last")); nrow.addWidget(self.last, 1)
        self.btn_rand = QPushButton("🎲"); self.btn_rand.setToolTip(tr("start.random_name_tip")); self.btn_rand.clicked.connect(self._random_name)
        nrow.addWidget(self.btn_rand); ll.addLayout(nrow)
        ll.addWidget(label(tr("start.country"), "h2"))
        self.search = QLineEdit(); self.search.setPlaceholderText(tr("start.search")); self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter); ll.addWidget(self.search)
        self.list = QListWidget(); self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); ll.addWidget(self.list, 1)
        lang = i18n.LANG
        for c in sorted(data.countries.values(), key=lambda c: c["name_ru" if lang == "ru" else "name_en"]):
            it = QListWidgetItem(f"{c['name_ru' if lang == 'ru' else 'name_en']}   ·   {c['code']}   ·   {stars_text(data.nat_stars(c['code']))}")
            it.setData(Qt.UserRole, c["code"])
            it.setData(Qt.UserRole + 1, f"{c['name_ru']} {c['name_en']} {c['code']}".lower())
            it.setToolTip(tr("start.nat_stars", s=f"{stars_text(data.nat_stars(c['code']))}  (OVR {data.nat_ovr(c['code']):.0f})"))
            self.list.addItem(it)
        self.list.itemSelectionChanged.connect(self._sel)
        self.sel_label = label(tr("start.selected", c=tr("start.none")), "muted"); ll.addWidget(self.sel_label)
        left.setMinimumWidth(360); body.addWidget(left, 4)

        right = panel(); rl = QVBoxLayout(right); rl.setContentsMargins(18, 16, 18, 16); rl.setSpacing(10)
        rl.addWidget(label(tr("start.position"), "h2"))
        self.pos_group = QButtonGroup(self); self.pos_group.setExclusive(True)
        for gkey, plist in POS_GROUPS:
            rl.addWidget(label(tr("posgrp." + gkey), "muted"))
            row = QHBoxLayout(); row.setSpacing(8)
            for ps in plist:
                nm = tr("pos." + ps); nm = nm.replace(" ", "\n") if len(nm) > 15 else nm
                b = QPushButton(f"{ps}\n{nm}"); b.setCheckable(True); b.setProperty("posbtn", True)
                b.clicked.connect(lambda _=False, ps=ps: self._pick_pos(ps)); self.pos_group.addButton(b); row.addWidget(b)
            row.addStretch(); rl.addLayout(row)
        # --- ведущая нога и рост
        rl.addSpacing(6)
        phys = QHBoxLayout(); phys.setSpacing(28)
        fcol = QVBoxLayout(); fcol.setSpacing(4); fcol.addWidget(label(tr("start.foot"), "h2"))
        frow = QHBoxLayout(); self.foot_group = QButtonGroup(self)
        for i, code in enumerate(("R", "L", "B")):
            rb = QRadioButton(tr("foot." + code)); rb.setProperty("foot", code); self.foot_group.addButton(rb, i); frow.addWidget(rb)
            if code == "R": rb.setChecked(True)
        self.foot_group.buttonToggled.connect(lambda *_: self._upd_phys())
        frow.addStretch(); fcol.addLayout(frow); phys.addLayout(fcol)
        hcol = QVBoxLayout(); hcol.setSpacing(4); hcol.addWidget(label(tr("start.height"), "h2"))
        hrow = QHBoxLayout()
        self.height = QSpinBox(); self.height.setRange(HEIGHT_MIN, HEIGHT_MAX); self.height.setValue(180); self.height.setSuffix(" " + tr("start.cm"))
        self.height.setMinimumWidth(110); self.height.valueChanged.connect(self._upd_phys); hrow.addWidget(self.height)
        self.height_typ = label("", "muted"); hrow.addWidget(self.height_typ); hrow.addStretch()
        hcol.addLayout(hrow); phys.addLayout(hcol, 1)
        rl.addLayout(phys)
        self.phys_hint = label("", "muted", True); rl.addWidget(self.phys_hint)
        self._height_touched = False                 # рост, изменённый вручную, больше не подстраивается под позицию
        self.height.valueChanged.connect(lambda _: setattr(self, "_height_touched", True))
        self._upd_phys()
        rl.addStretch()
        self.btn_next = QPushButton(tr("start.next")); self.btn_next.setObjectName("primary"); self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self._go); rl.addWidget(self.btn_next, 0, Qt.AlignRight)
        body.addWidget(right, 7)

    def _filter(self, text):
        t = text.strip().lower()
        for i in range(self.list.count()):
            it = self.list.item(i); it.setHidden(bool(t) and t not in it.data(Qt.UserRole + 1))

    def _sel(self):
        its = self.list.selectedItems()
        self.nat = its[0].data(Qt.UserRole) if its else None
        if self.nat:
            self.sel_label.setText(tr("start.selected", c=self.d.country_name(self.nat, i18n.LANG)) + "   ·   " +
                                   tr("start.nat_stars", s=stars_text(self.d.nat_stars(self.nat))))
        self._upd()

    def _pick_pos(self, ps):
        self.pos = ps
        if not self._height_touched:                     # пока рост не трогали, он следует за позицией (типичный рост)
            self.height.blockSignals(True); self.height.setValue(TYPICAL_HEIGHT[ps]); self.height.blockSignals(False)
        self._upd(); self._upd_phys()

    def foot(self):
        b = self.foot_group.checkedButton()
        return b.property("foot") if b else "R"

    def _upd_phys(self, *_):
        """Подсказка: что дают выбранные нога и рост на этой позиции."""
        if not self.pos:
            self.height_typ.setText(""); self.phys_hint.setText(tr("start.phys_pick_pos")); return
        typ = TYPICAL_HEIGHT[self.pos]
        self.height_typ.setText(tr("start.height_typ", h=typ))
        dh = self.height.value() - typ
        notes = [tr("phys.tall" if dh >= 4 else "phys.short" if dh <= -4 else "phys.avg")]
        if dh >= 4 and self.pos in ("ST", "CF", "CB", "CDM"):
            notes.append(tr("phys.headers"))
        if self.pos == "GK" and abs(dh) >= 4:
            notes[-1] = tr("phys.gk_tall" if dh > 0 else "phys.gk_short")
        f = self.foot()
        if self.pos in LEFT_SIDE + RIGHT_SIDE:
            natural = (self.pos in LEFT_SIDE) == (f == "L")
            notes.append(tr("phys.both_wing" if f == "B" else "phys.natural" if natural else "phys.inverted"))
        elif f == "B":
            notes.append(tr("phys.both_center"))
        self.phys_hint.setText(" ".join(notes))

    def _upd(self):
        self.btn_next.setEnabled(bool(self.nat and self.pos))

    def _random_name(self):
        """Имя и фамилия, типичные для выбранной страны (те же списки, что у молодых звёзд мира)."""
        nat = self.nat or "ENG"
        first, last = gen_name(random.Random(), nat, self.d.countries[nat]["conf"]).split(" ", 1)
        self.first.setText(first); self.last.setText(last)

    def player_name(self):
        return " ".join(x for x in (self.first.text().strip(), self.last.text().strip()) if x) or tr("start.name_default")

    def _go(self):
        self.proceed.emit(self.player_name(), self.nat, self.pos, self.foot(), self.height.value())

# ======================================================================================= сводка
class SummaryPage(QWidget):
    start = Signal(); reroll = Signal(); back = Signal()

    def __init__(self, career, data):
        super().__init__(); self.setObjectName("page")
        c = career
        root = QVBoxLayout(self); root.setContentsMargins(32, 24, 32, 24); root.setSpacing(16)
        root.addWidget(label(tr("summary.title"), "title"))
        body = QHBoxLayout(); body.setSpacing(24); root.addLayout(body, 1)
        info = panel(); g = QGridLayout(info); g.setContentsMargins(24, 20, 24, 20); g.setVerticalSpacing(14); g.setHorizontalSpacing(28)
        rows = [(tr("summary.nation"), f"{data.country_name(c.nat, i18n.LANG)}   {stars_text(data.nat_stars(c.nat))}"),
                (tr("summary.position"), pos_text(c.pos)),
                (tr("summary.physique"), f"{tr('foot_short.' + c.player.foot)}  ·  {c.player.height} {tr('start.cm')}"),
                (tr("summary.age"), tr("summary.age_val", n=15)), (tr("summary.start"), "2026/27")]
        for i, (k, v) in enumerate(rows):
            g.addWidget(label(k, "muted"), i, 0); lv = label(v, "h2"); g.addWidget(lv, i, 1)
        g.addWidget(label(tr("summary.pot"), "muted", True), len(rows), 0, 1, 2)
        g.addWidget(label(tr("summary.rule"), "muted", True), len(rows) + 1, 0, 1, 2)
        g.setRowStretch(len(rows) + 2, 1)
        body.addWidget(info, 1)
        self.card = PlayerCard(); self.card.set_player(c.player, data.country_name(c.nat, i18n.LANG))
        body.addWidget(self.card, 0, Qt.AlignTop)
        row = QHBoxLayout()
        b = QPushButton(tr("summary.back")); b.clicked.connect(self.back.emit); row.addWidget(b); row.addStretch()
        r = QPushButton(tr("summary.reroll")); r.clicked.connect(self.reroll.emit); row.addWidget(r)
        s = QPushButton(tr("summary.go")); s.setObjectName("primary"); s.clicked.connect(self.start.emit); row.addWidget(s)
        root.addLayout(row)

# ======================================================================================= академия
class AcademyPage(QWidget):
    chosen = Signal(str)

    def __init__(self, career, data):
        super().__init__(); self.setObjectName("page")
        root = QVBoxLayout(self); root.setContentsMargins(32, 24, 32, 24); root.setSpacing(12)
        root.addWidget(label(tr("academy.title"), "title")); root.addWidget(label(tr("academy.sub"), "muted", True))
        host = QWidget(); host.setObjectName("scrollhost"); v = QVBoxLayout(host); v.setSpacing(12); v.setContentsMargins(0, 8, 0, 8)
        w = career.world
        for cid in career.academy_ids:
            cl = data.clubs[cid]
            lg = w.league_of(cid)
            sub = f"{lg['name']} · {data.country_name(lg['country'], i18n.LANG)}"
            tag = career.academy_tag(cid)
            v.addWidget(ClubCard(cl, sub, w.stars(cid), [tr("academy.team", o=round(w.team_ovr(cid)))], tr("academy.choose"),
                                 lambda _=False, cid=cid: self.chosen.emit(cid), tag=tr("academy." + tag), tag_home=(tag == "home")))
        v.addStretch()
        root.addWidget(scroll(host), 1)

# ======================================================================================= карьера
class CareerPage(QWidget):
    play = Signal(); menu = Signal(); retire = Signal(); diary = Signal(str)

    def __init__(self, career, data):
        super().__init__(); self.setObjectName("page")
        self.c, self.d = career, data
        root = QVBoxLayout(self); root.setContentsMargins(24, 18, 24, 18); root.setSpacing(12)
        self.header = panel(); self.hl = QHBoxLayout(self.header); self.hl.setContentsMargins(16, 10, 16, 10); self.hl.setSpacing(14)
        self.logo_host = QHBoxLayout(); self.hl.addLayout(self.logo_host)
        self.h_main = label("", "h2"); self.h_sub = label("", "muted")
        col = QVBoxLayout(); col.setSpacing(1); col.addWidget(self.h_main); col.addWidget(self.h_sub); self.hl.addLayout(col, 1)
        self.h_right = label("", "gold"); self.h_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter); self.hl.addWidget(self.h_right)
        root.addWidget(self.header)
        body = QHBoxLayout(); body.setSpacing(14); root.addLayout(body, 1)
        left = QVBoxLayout(); left.setSpacing(12)
        self.card = PlayerCard(); left.addWidget(self.card)
        self.chart = OvrChart(tr("chart.title")); self.chart.setFixedWidth(300); left.addWidget(self.chart, 1)
        body.addLayout(left)
        self.table = QTableWidget(); cols = ["season", "age", "club", "league", "rank", "games", "goals", "assists", "ovr", "nat", "trophies_only", "awards"]
        self.cols = cols; self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([tr("col." + ("cs" if (k == "assists" and career.pos == "GK") else k)) for k in cols])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False); self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        h = self.table.horizontalHeader(); h.setSectionResizeMode(QHeaderView.Interactive); h.setStretchLastSection(True)
        for i, w in enumerate([66, 44, 150, 112, 52, 52, 50, 50, 62, 96, 135]): self.table.setColumnWidth(i, w)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.table.setTextElideMode(Qt.ElideRight)
        body.addWidget(self.table, 1)
        bar = QHBoxLayout(); b = QPushButton(tr("career.menu")); b.clicked.connect(self.menu.emit); bar.addWidget(b)
        r = QPushButton(tr("career.retire")); r.setObjectName("danger"); r.clicked.connect(self.retire.emit); bar.addWidget(r)
        dz = QPushButton(tr("ai.diaries")); dz.clicked.connect(lambda: self.diary.emit("")); bar.addWidget(dz)
        self.table.cellDoubleClicked.connect(lambda row, _col: self.diary.emit(f"p:{row}"))
        self.totals = label("", "muted"); bar.addWidget(self.totals); bar.addStretch()
        bar.addWidget(label(tr("career.autosave"), "muted"))
        self.btn = QPushButton(); self.btn.setObjectName("primary"); self.btn.clicked.connect(self.play.emit); bar.addWidget(self.btn)
        root.addLayout(bar)
        self.refresh()

    def refresh(self):
        c, d, w = self.c, self.d, self.c.world
        pl = c.player; cl = d.clubs[c.club_id]
        while self.logo_host.count():
            it = self.logo_host.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        self.logo_host.addWidget(logo_label(cl, 48))
        youth = pl.age < 18
        lg = w.league_of(c.club_id)
        self.h_main.setText(f"{cl['name']}" + (f"  ·  {tr('career.academy')}" if youth else "") +
                            (f"  ·  © {tr('career.captain')}" if c.captain else ""))
        sub = f"{lg['name']} · {d.country_name(lg['country'], i18n.LANG)}   {stars_text(w.stars(c.club_id))}   OVR {round(w.team_ovr(c.club_id))}"
        if c.parent_id: sub += "   " + tr("career.loan", club=d.clubs[c.parent_id]["name"])
        self.h_sub.setText(sub)
        val = money(market_value(pl.ovr(), pl.age, pl.pot))
        self.h_right.setText(f"{pl.name}  ·  {tr('career.age', n=pl.age)}  ·  {tr('career.contract', n=c.contract_left)}\n{tr('career.value', v=val)}")
        self.card.set_player(pl, d.country_name(c.nat, i18n.LANG))
        pts = [(s["age"], s["ovr"]) for s in c.seasons] + [(pl.age, pl.ovr())]
        self.chart.set_points(pts, tr("chart.title"))
        self.table.setRowCount(0)
        for s in c.seasons: self._row(s)
        self.table.scrollToBottom()
        g = sum(s["games"] for s in c.seasons); go = sum(s["goals"] for s in c.seasons); a = sum(s["assists"] for s in c.seasons)
        n_aw = sum(1 for x in c.awards if x["code"] != "ballon_top30")     # место в топ-30 - не награда, а номинация
        self.totals.setText("   " + tr("career.totals", g=g, a=go, s=a, t=len(c.trophies), w=n_aw))
        if youth: self.btn.setText(tr("career.play_academy"))
        else: self.btn.setText(tr(f"career.play_{c.freq if not c.parent_id else 1}"))

    def _row(self, s):
        r = self.table.rowCount(); self.table.insertRow(r)
        cl = self.d.clubs[s["club"]]
        tro = [short_trophy(t["code"]) for t in s["trophies"]]
        aws = season_award_names(s)
        intl = s["intl"]
        nat_txt = f"{intl['caps']}/{intl['goals']}" if intl and intl["called"] else "—"
        tip = "\n".join(f"{nat_comp_name(e, self.d)}: {nat_result(e, self.d)}".rstrip(": ") for e in s.get("nat_comps", [])
                        if e["kind"] != "friendly")
        gk = self.c.pos == "GK"
        lg_name = youth_league_name(s)
        vals = [s["season"], str(s["age"]), cl["name"] + (" " + tr("report.loan_tag") if s["loan"] else ""),
                lg_name, f"{s['rank']}/{s['n']}", str(s["games"]),
                str(s["goals"]), str(s["cs"] if gk else s["assists"]), f"{s['ovr']}→{s['ovr_end']}", nat_txt, ", ".join(tro), ", ".join(aws)]
        comp_tip = "\n".join(f"{lang_name(x)}: {x['games']} / {x['goals']} / {x['cs'] if gk else x['assists']}" for x in s.get("comps", []))
        for i, v in enumerate(vals):
            it = QTableWidgetItem(v)
            if i in (1, 4, 5, 6, 7, 8, 9): it.setTextAlignment(Qt.AlignCenter)
            if i == 2: it.setIcon(QIcon(club_pixmap(cl, 22)))
            if i == 3: it.setToolTip(f"{lg_name} · {self.d.country_name(s['league_country'], i18n.LANG)}")
            if i in (5, 6, 7) and comp_tip: it.setToolTip(comp_tip)
            if i == 9 and tip: it.setToolTip(tip)
            if i == 10 and tro: it.setForeground(QColor(theme.GOLD)); it.setToolTip("\n".join(trophy_name(t) for t in s["trophies"]))
            if i == 11 and aws: it.setForeground(QColor(theme.AWARD)); it.setToolTip("\n".join(aws))
            self.table.setItem(r, i, it)
        self.table.setRowHeight(r, 30)

# ======================================================================================= отчёт периода
def _cell(v, align="center", color=None, bold=False, width=None):
    st = f"padding:4px 8px; text-align:{align};" + (f" color:{color};" if color else "") + (" font-weight:700;" if bold else "")
    return f"<td style='{st}'" + (f" width='{width}'" if width else "") + f">{v}</td>"

# одинаковые ширины столбцов у всех таблиц отчёта (клуб и сборная, все сезоны): итоги стоят ровным столбцом
REPORT_COLS = ("32%", "47%", "7%", "7%", "7%")

def _row(cells):
    """cells: [(значение, выравнивание, цвет, жирный)] -> строка таблицы отчёта с фиксированными ширинами столбцов."""
    return "<tr>" + "".join(_cell(v, a, c, b, w) for (v, a, c, b), w in zip(cells, REPORT_COLS)) + "</tr>"

def _report_table(rows, margin="6px 8px"):
    return f"<table width='100%' style='margin:{margin};' cellspacing='0'>" + "".join(rows) + "</table>"

# ---------- полные таблицы турниров в отчёте ----------
MY_ROW_BG = "#3a3218"                    # строка своей команды
def _td(v, align="center", color=None, bold=False, bg=None, width=None):
    st = f"padding:3px 6px; text-align:{align};" + (f" color:{color};" if color else "") + (" font-weight:700;" if bold else "")
    return f"<td style='{st}'" + (f" bgcolor='{bg}'" if bg else "") + (f" width='{width}'" if width else "") + f">{v}</td>"

def _caption(text, color=None):
    return f"<div style='margin:2px 10px 10px 10px; color:{color or theme.MUTED}; font-size:13px;'>{text}</div>"

def _club_name(d, cid):
    c = d.clubs.get(cid)
    return escape(c["name"]) if c else escape(str(cid))

def league_table_html(x, d, me):
    """Полная таблица лиги (или молодёжной лиги): место, клуб, И, В, Н, П, мячи, разница, очки; своя команда выделена."""
    t = x.get("table")
    if not t:
        return ""
    head = "".join(_td(v, "left" if i == 1 else "center", theme.MUTED, True) for i, v in
                   enumerate(["#", tr("col.club"), tr("tbl.p"), tr("tbl.w"), tr("tbl.d"), tr("tbl.l"), tr("tbl.goals"), "+/−", tr("tbl.pts")]))
    rows = [f"<tr>{head}</tr>"]
    for i, (cid, w, dr, l, gf, ga, pts) in enumerate(t, 1):
        mine = cid == me
        bg = MY_ROW_BG if mine else None
        col = theme.GOLD if mine else None
        rows.append("<tr>" + _td(i, color=theme.GOLD if i == 1 else col, bold=mine, bg=bg) + _td(_club_name(d, cid), "left", col, mine, bg) +
                    _td(w + dr + l, color=col, bg=bg) + _td(w, color=col, bg=bg) + _td(dr, color=col, bg=bg) + _td(l, color=col, bg=bg) +
                    _td(f"{gf}:{ga}", color=col, bg=bg) + _td(f"{gf - ga:+d}", color=col, bg=bg) + _td(pts, color=col, bold=True, bg=bg) + "</tr>")
    r = x["result"]
    cap = tr("tbl.league_caption", r=r["rank"], n=r["n"], pts=r["pts"])
    return (f"<div style='margin:10px 10px 2px 10px; font-weight:700;'>{escape(lang_name(x))}</div>"
            f"<table width='100%' cellspacing='0' style='margin:0 8px;'>{''.join(rows)}</table>" + _caption(cap, theme.GOLD if r["rank"] == 1 else None))

def _stage_table_html(x, d, me):
    """Таблица общего этапа еврокубка (36 клубов) или группы: место, клуб, очки, разница. Зоны общего этапа: 1-8 - сразу в 1/8,
    9-24 - плей-офф, ниже - вылет."""
    t, r = x.get("table"), x["result"]
    if not t:
        return ""
    lp = len(t) > 8
    head = "".join(_td(v, "left" if i == 1 else "center", theme.MUTED, True) for i, v in enumerate(["#", tr("col.club"), tr("tbl.pts"), "+/−"]))
    rows = [f"<tr>{head}</tr>"]
    for i, (cid, pts, gd) in enumerate(t, 1):
        mine = cid == me
        zone = ("#173322" if i <= 8 else "#1e2a38" if i <= 24 else None) if lp else ("#173322" if i <= 2 else None)
        bg = MY_ROW_BG if mine else zone
        col = theme.GOLD if mine else (None if (not lp or i <= 24) else theme.MUTED)
        rows.append("<tr>" + _td(i, color=col, bold=mine, bg=bg) + _td(_club_name(d, cid), "left", col, mine, bg) +
                    _td(pts, color=col, bold=True, bg=bg) + _td(f"{gd:+d}", color=col, bg=bg) + "</tr>")
    cap = tr("tbl.lp_caption", r=r["lp_rank"], n=r["lp_n"], pts=r["lp_pts"]) if lp and "lp_rank" in r else \
          tr("tbl.group_caption", g=r.get("group", "?"), p=r.get("gpos", "?")) if "gpos" in r else ""
    legend = _caption(tr("tbl.lp_legend")) if lp else ""
    return f"<table width='100%' cellspacing='0' style='margin:0 8px;'>{''.join(rows)}</table>" + (_caption(cap) if cap else "") + legend

def cup_path_html(x, d, me):
    """Путь команды в кубке или еврокубке: таблица общего этапа / группы (если была) и все раунды на вылет с соперником и счётом."""
    r = x["result"]
    path = list(r.get("path") or [])
    if not path and r.get("vs"):                                       # суперкубок: один матч без записи раундов
        path = [{"stage": r.get("stage") if r.get("stage") != "W" else "F", "vs": r["vs"], "score": r.get("score"), "won": r.get("won", r.get("stage") == "W")}]
    title = f"<div style='margin:10px 10px 2px 10px; font-weight:700;'>{escape(lang_name(x))}</div>"
    body = _stage_table_html(x, d, me)
    if path:
        head = "".join(_td(v, "left", theme.MUTED, True) for v in [tr("tbl.round"), tr("tbl.opponent"), tr("tbl.score"), ""])
        rows = [f"<tr>{head}</tr>"]
        for p in path:
            ok = p["won"]
            mark = f"<span style='color:{theme.ACCENT}'>{tr('tbl.through')}</span>" if ok else f"<span style='color:{theme.RED}'>{tr('tbl.out')}</span>"
            if ok and p["stage"] == "F":
                mark = f"<span style='color:{theme.GOLD}; font-weight:700'>◆ {tr('tbl.won_final')}</span>"
            rows.append("<tr>" + _td(escape(stage(p["stage"]).capitalize()), "left", width="26%") + _td(_club_name(d, p["vs"]), "left", width="36%") +
                        _td(escape(score_text(p["score"])), "left", width="22%") + _td(mark, "left") + "</tr>")
        body += f"<table width='100%' cellspacing='0' style='margin:2px 8px;'>{''.join(rows)}</table>"
    won = r.get("stage") == "W"
    body += _caption(escape(club_result(x, d)), theme.GOLD if won else None)
    return title + body

def details_html(c, d, s):
    """Полные таблицы сезона под сводкой: слева таблица лиги, справа путь в кубках и еврокубках."""
    comps = s.get("comps") or []
    me = s["club"]
    lg = [league_table_html(x, d, me) for x in comps if x["code"] in ("league", "youth") and not x.get("senior")]
    cups = [cup_path_html(x, d, me) for x in comps if x["code"] not in ("league", "youth") and (x["result"].get("path") or x["result"].get("vs") or x.get("table"))]
    lg, cups = [h for h in lg if h], [h for h in cups if h]
    if not lg and not cups:
        return ""
    return ("<table width='100%' cellspacing='0' cellpadding='0' style='margin-top:6px;'><tr>"
            f"<td width='55%' valign='top'>{''.join(lg)}</td><td width='45%' valign='top'>{''.join(cups)}</td></tr></table>")

class ReportPage(QWidget):
    done = Signal(); diary = Signal(str)

    def __init__(self, career, data, recs, reason):
        super().__init__(); self.setObjectName("page")
        root = QVBoxLayout(self); root.setContentsMargins(32, 24, 32, 24); root.setSpacing(12)
        a, b = recs[0]["season"], recs[-1]["season"]
        root.addWidget(label(tr("report.title1", a=a) if a == b else tr("report.title", a=a, b=b), "title"))
        view = QTextBrowser(); view.setOpenLinks(False); root.addWidget(view, 1)
        view.setHtml(self._html(career, data, recs, reason))
        row = QHBoxLayout()
        for s in recs:
            key = f"p:{next(i for i, x in enumerate(career.seasons) if x is s)}"
            if s.get("comps"):
                b = QPushButton(f"{tr('web.diary_btn')} {s['season']}"); b.clicked.connect(lambda _=False, k=key: self.diary.emit(k)); row.addWidget(b)
        row.addStretch()
        btn = QPushButton(tr("report.continue")); btn.setObjectName("primary"); btn.clicked.connect(self.done.emit); row.addWidget(btn)
        root.addLayout(row)

    @staticmethod
    def season_html(c, d, s):
        gk = c.pos == "GK"
        h = []
        lg = f"{s['league_name']} ({d.country_name(s['league_country'], i18n.LANG)})"
        h.append(f"<div style='margin-top:14px; padding:8px 12px; background:{theme.PANEL2}; border-radius:8px;'>")
        h.append(f"<span style='font-size:17px; font-weight:700;'>{tr('report.season', s=s['season'])}</span>"
                 f" &nbsp; <span style='color:{theme.MUTED}'>{tr('career.age', n=s['age'])} · {escape(s['club_name'])} "
                 f"{tr('report.loan_tag') if s['loan'] else ''} · {escape(lg)}</span></div>")
        if s["youth"]:
            h.append(f"<div style='margin:6px 12px; color:{theme.MUTED}'>{tr('report.youth_note')}</div>")
        # --- таблица по турнирам: клуб
        head = _row([(x, "left" if i < 2 else "center", theme.MUTED, True) for i, x in
                     enumerate([tr("col.comp"), tr("col.result"), tr("col.g"), tr("col.csh") if gk else tr("col.go"), "" if gk else tr("col.a")])])
        rows = [head]
        for x in s.get("comps", []):
            name = escape(lang_name(x)) + (f" <span style='color:{theme.MUTED}'>({tr('report.senior_tag')})</span>" if x.get("senior") else "")
            res = escape(club_result(x, d))
            won = x["result"].get("stage") == "W" or (x["code"] in ("league", "youth") and x["result"].get("rank") == 1)
            rows.append(_row([(name, "left", None, False), (res, "left", theme.GOLD if won else None, False), (x["games"], "center", None, False),
                              (x["cs"] if gk else x["goals"], "center", None, False), ("" if gk else x["assists"], "center", None, False)]))
        rows.append(_row([(tr("report.club_total"), "left", None, True), ("", "left", None, False), (s["games"], "center", None, True),
                          (s["cs"] if gk else s["goals"], "center", None, True), ("" if gk else s["assists"], "center", None, True)]))
        h.append("<table width='100%' cellspacing='0' cellpadding='0'><tr><td width='60%' valign='top'>")    # левая колонка: клуб и сборная
        h.append(_report_table(rows))
        extra = [tr("report.ovr", a=s["ovr"], b=s["ovr_end"])]
        if s.get("rating"):
            extra.append(tr("report.rating", r=f"{s['rating']:.2f}"))
        h.append(f"<div style='margin:2px 12px; color:{theme.MUTED}'>{' · '.join(extra)}</div>")
        # --- сборная
        if s.get("nat_comps"):
            intl = s["intl"] or {}
            h.append(f"<div style='margin:10px 12px 2px 12px; font-weight:700;'>{tr('report.nat_title', c=d.country_name(c.nat, i18n.LANG))}"
                     f" <span style='font-weight:400; color:{theme.MUTED}'>· {tr('report.nat_called') if intl.get('called') else tr('report.nat_not_called')}</span></div>")
            nrows = [head]
            for e in s["nat_comps"]:
                if e["kind"] == "friendly" and not e["games"]:
                    continue
                res = nat_result(e, d)
                won = (e["kind"] == "final" and e["info"].get("stage") == "W") or (e["kind"] == "unl" and (
                    (e["info"].get("finals") or {}).get("stage") == "W" or (e["info"].get("move") or {}).get("dir") == "up"))
                gl = group_line(e, d)
                res_html = escape(res) + (f"<br><span style='color:{theme.MUTED}; font-size:12px'>{escape(gl)}</span>" if gl else "")
                called = intl.get("called")
                nrows.append(_row([(escape(nat_comp_name(e, d)), "left", None, False), (res_html, "left", theme.GOLD if won else None, False),
                                   (e["games"] if called else "—", "center", None, False),
                                   ("" if gk else (e["goals"] if called else ""), "center", None, False),
                                   ("" if gk else (e["assists"] if called else ""), "center", None, False)]))
            if len(nrows) > 1:
                h.append(_report_table(nrows, "2px 8px"))
            if intl.get("called"):
                h.append(f"<div style='margin:2px 12px;'>{intl_line(intl['caps'], intl['goals'], intl['assists'])}</div>")
        # --- правая колонка: трофеи, награды, Золотой мяч, события
        h.append("</td><td width='40%' valign='top'>")
        h.append(f"<div style='margin:8px 12px 2px 12px; font-weight:700;'>{tr('report.honours')}</div>")
        for t in s["trophies"]:
            h.append(f"<div style='margin:3px 12px; color:{theme.NATIONAL if t['cat'] == 'national' else theme.GOLD}'>◆ {escape(trophy_name(t))}</div>")
        if not s["trophies"]:
            h.append(f"<div style='margin:3px 12px; color:{theme.MUTED}'>{tr('report.no_trophies')}</div>")
        for a in season_award_names(s):
            h.append(f"<div style='margin:3px 12px; color:{theme.AWARD}'>★ {escape(a)}</div>")
        if s.get("ballon"):
            h.append(ReportPage.ballon_html(s["ballon"], d))
        for e in s["events"]:
            h.append(f"<div style='margin:3px 12px; color:#e59b5a'>• {event_text(e)}</div>")
        if s.get("chronicle"):
            h.append(f"<div style='margin:10px 12px 2px 12px; font-weight:700;'>{tr('chron.title')}</div>")
            for e in s["chronicle"]:
                h.append(f"<div style='margin:2px 12px; color:{theme.TEXT}'>▸ {escape(chronicle_text(e, d))}</div>")
        h.append("</td></tr></table>")
        h.append(details_html(c, d, s))
        return "".join(h)

    @staticmethod
    def ballon_html(b, d):
        """Плашка Золотого мяча: победитель и тройка; ваше место; кто впереди, если вы во второй или третий."""
        def who(x):
            return tr("bdo.you") if x.get("me") else x["name"]
        sm = lambda v, a="left", c=None, bold=False: (f"<td style='padding:2px 6px; text-align:{a};" + (f" color:{c};" if c else "") +
                                                      (" font-weight:700;" if bold else "") + f"'>{v}</td>")
        head = "".join(sm(x, "left" if i < 3 else "center", theme.MUTED) for i, x in
                       enumerate(["#", tr("bdo.col_player"), tr("bdo.col_pos"), tr("col.go"), tr("col.a")]))
        rows = [f"<tr>{head}</tr>"]
        for i, x in enumerate(b["top"], 1):
            me = x.get("me")
            if i > 5 and not me:                       # топ-5 и ваша строка, если вы в первой десятке
                continue
            col = theme.GOLD if me else (theme.TEXT if i <= 3 else None)
            name = (f"<b>{escape(who(x))}</b>" if i <= 3 or me else escape(who(x))) + \
                   f"<br><span style='color:{theme.MUTED}; font-size:12px'>{escape(d.clubs[x['club']]['name'])} · {d.country_name(x['nat'], i18n.LANG)}</span>"
            rows.append("<tr>" + sm(i, "left", col, i <= 3) + sm(name, "left", col) + sm(f"<b>{x['pos']}</b><br><span style='color:{theme.MUTED}; font-size:12px'>"
                        f"{escape(tr('pos.' + x['pos']))}</span>", "left", col) + sm(x["goals"], "center", col) + sm(x["assists"], "center", col) + "</tr>")
        rows = ["<table width='100%' cellspacing='0' style='margin:2px 0 6px 0;'>" + "".join(rows) + "</table>"]
        r = b.get("rank")
        if r == 1:
            foot = f"<div style='color:{theme.GOLD}; font-weight:700'>{tr('bdo.you_won')}</div>"
        elif r:
            foot = f"<div>{tr('bdo.place', r=r)}</div>"
            if b.get("ahead"):
                foot += f"<div style='color:{theme.MUTED}'>{tr('bdo.ahead', names=', '.join(escape(x['name']) for x in b['ahead']))}</div>"
        else:
            foot = f"<div style='color:{theme.MUTED}'>{tr('bdo.not_nominated')}</div>"
        return (f"<table width='100%' cellspacing='0' cellpadding='10' style='margin:8px 4px 8px 12px;' bgcolor='#2a2516' border='1' "
                f"bordercolor='#6b5a24'><tr><td><div style='color:{theme.GOLD}; font-weight:700; margin-bottom:4px'>"
                f"{tr('bdo.title', y=b['year'])}</div>" + "".join(rows) + foot + "</td></tr></table>")

    def _html(self, c, d, recs, reason):
        G, A, Ast, CS = 0, 0, 0, 0
        h = [f"<body style='color:{theme.TEXT}; font-size:14px;'>"]
        for s in recs:
            G += s["games"]; A += s["goals"]; Ast += s["assists"]; CS += s["cs"]
            h.append(self.season_html(c, d, s))
        if len(recs) > 1:
            tot = tr("report.stats_gk", g=G, c=CS) if c.pos == "GK" else tr("report.stats", g=G, a=A, s=Ast)
            h.append(f"<div style='margin-top:18px; padding:10px 12px; background:{theme.PANEL2}; border-radius:8px;'><b>{tr('report.total')}:</b> {tot}</div>")
        h.append(f"<p style='margin-top:12px; color:{theme.ACCENT}; font-size:15px;'>{tr('reason.' + reason)}</p></body>")
        return "".join(h)

# ======================================================================================= предложения
class OffersPage(QWidget):
    accept = Signal(object); retire = Signal()

    def __init__(self, career, data):
        super().__init__(); self.setObjectName("page")
        c, w = career, career.world
        root = QVBoxLayout(self); root.setContentsMargins(32, 24, 32, 24); root.setSpacing(10)
        root.addWidget(label(tr("offers.title"), "title"))
        root.addWidget(label(tr("reason." + c.offer_reason), "muted", True))
        root.addWidget(label(tr("offers.you", o=c.player.ovr()) + f"   ·   {pos_text(c.pos)}   ·   {tr('career.age', n=c.player.age)}", "gold"))
        # --- текущий клуб: с чем сравнивать предложения
        cur = data.clubs[c.club_id]; clg = w.league_of(c.club_id); team = w.team_ovr(c.club_id)
        box = panel(); bl = QHBoxLayout(box); bl.setContentsMargins(14, 8, 14, 8); bl.setSpacing(12)
        bl.addWidget(logo_label(cur, 40))
        col = QVBoxLayout(); col.setSpacing(1)
        col.addWidget(label(f"{tr('offers.current')}:  {cur['name']}", "h2"))
        col.addWidget(label(f"{clg['name']} · {data.country_name(clg['country'], i18n.LANG)}   {stars_text(w.stars(c.club_id))}", "muted"))
        bl.addLayout(col, 1)
        facts = [tr("offers.current_team", o=round(team)), tr("offers.current_role", r=tr("role." + c.role_for(c.player.ovr() - team))),
                 tr("offers.contract_left", n=c.contract_left) if c.contract_left > 0 else tr("offers.contract_over")]
        fl = label("\n".join(facts)); fl.setAlignment(Qt.AlignRight | Qt.AlignVCenter); bl.addWidget(fl)
        root.addWidget(box)
        host = QWidget(); host.setObjectName("scrollhost"); v = QVBoxLayout(host); v.setSpacing(10); v.setContentsMargins(0, 6, 0, 6)
        for i, o in enumerate(c.offers):
            cl = data.clubs[o["club"]]; lg = w.league_of(o["club"])
            sub = f"{lg['name']} · {data.country_name(lg['country'], i18n.LANG)}"
            tag = tr("offers.kind.loan") if o["kind"] == "loan" else tr("offers.kind.first") if o["kind"] == "first" else None
            fee = tr("offers.free") if o["fee"] <= 0 and o["kind"] == "transfer" else (money(o["fee"]) if o["fee"] > 0 else "—")
            lines = [f"{tr('offers.fee')}: {fee}" if o["kind"] == "transfer" else "", tr("offers.years", n=o["years"]),
                     tr("offers.role", r=tr("role." + o["role"])), tr("offers.team", o=round(w.team_ovr(o["club"])))]
            known = stars_mod.players_at(c.stars, o["club"])[:3]           # звёзды и известные игроки, с которыми предстоит играть
            if known:
                lines.append(tr("offers.known", n=", ".join(p["name"] for p in known)))
            v.addWidget(ClubCard(cl, sub, w.stars(o["club"]), [x for x in lines if x], tr("offers.choose"), lambda _=False, i=i: self.accept.emit(i), tag=tag))
        v.addStretch()
        root.addWidget(scroll(host), 1)
        row = QHBoxLayout()
        if c.can_stay:
            cur = data.clubs[c.club_id]["name"]
            b = QPushButton(tr("offers.stay", club=cur)); b.clicked.connect(lambda: self.accept.emit("stay")); row.addWidget(b)
        row.addStretch()
        r = QPushButton(tr("offers.retire")); r.setObjectName("danger"); r.clicked.connect(self.retire.emit); row.addWidget(r)
        root.addLayout(row)

# ======================================================================================= финал
def cell(text, key=None, color=None, bg=None, bold=False, tip=None):
    """Ячейка SortTable: текст, ключ сортировки (если отличается от текста), цвет текста и фона, подсказка."""
    return {"text": str(text), "key": key, "color": color, "bg": bg, "bold": bold, "tip": tip}

def _auto_key(text):
    """Ключ сортировки по тексту: число в начале («12», «5/20», «2026/27», «7.45») или сам текст; «—» и пусто - без ключа."""
    t = text.strip()
    if t in ("", "—", "-"):
        return None
    num = ""
    for ch in t:
        if ch.isdigit() or (ch in ".," and num) or (ch == "-" and not num):
            num += ch
        else:
            break
    try:
        return (0, float(num.replace(",", ".")))
    except ValueError:
        return (1, t.lower())

class SortTable(QTableWidget):
    """Таблица итогов: щелчок по заголовку столбца - от большего, ещё раз - от меньшего, третий раз - исходный порядок."""
    def __init__(self, headers, rows, widths=None, center=()):
        super().__init__(0, len(headers))
        self.setHorizontalHeaderLabels(headers); self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True); self.verticalHeader().setVisible(False); self.setSelectionBehavior(QAbstractItemView.SelectRows)
        h = self.horizontalHeader(); h.setStretchLastSection(True); h.setSectionsClickable(True); h.setSortIndicatorShown(False)
        h.sectionClicked.connect(self._clicked)
        for i, wd in enumerate(widths or []): self.setColumnWidth(i, wd)
        self.center = set(center)
        self.rows = [[c if isinstance(c, dict) else cell(c) for c in r] for r in rows]
        self.sort_col, self.state = None, 0          # state: 0 - исходный порядок, 1 - от большего, 2 - от меньшего
        self._fill()

    def _key(self, c):
        return c["key"] if c["key"] is not None and isinstance(c["key"], tuple) else (
            (0, float(c["key"])) if isinstance(c["key"], (int, float)) else _auto_key(c["text"]))

    def _clicked(self, col):
        if col != self.sort_col:
            self.sort_col, self.state = col, 1
        else:
            self.state = (self.state + 1) % 3
            if self.state == 0:
                self.sort_col = None
        self._fill()

    def _fill(self):
        rows = self.rows
        h = self.horizontalHeader()
        if self.sort_col is not None:
            col, desc = self.sort_col, self.state == 1
            known = [r for r in rows if self._key(r[col]) is not None]
            unknown = [r for r in rows if self._key(r[col]) is None]          # «—» всегда внизу
            rows = sorted(known, key=lambda r: self._key(r[col]), reverse=desc) + unknown
            h.setSortIndicatorShown(True); h.setSortIndicator(col, Qt.DescendingOrder if desc else Qt.AscendingOrder)
        else:
            h.setSortIndicatorShown(False)
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for i, c in enumerate(row):
                it = QTableWidgetItem(c["text"])
                if i in self.center: it.setTextAlignment(Qt.AlignCenter)
                if c["color"]: it.setForeground(QColor(c["color"]))
                if c["bg"]: it.setBackground(QColor(c["bg"]))
                if c["bold"]:
                    f = it.font(); f.setBold(True); it.setFont(f)
                if c["tip"]: it.setToolTip(c["tip"])
                self.setItem(r, i, it)

class EndPage(QWidget):
    new_career = Signal(); export = Signal(); quit_game = Signal(); become_coach = Signal(); diary = Signal(str)

    def __init__(self, career, data):
        super().__init__(); self.setObjectName("page")
        c, d = career, data
        rep = c.report(); cc = d.clubs[rep["coach_club"]]
        root = QVBoxLayout(self); root.setContentsMargins(32, 24, 32, 24); root.setSpacing(10)
        head = QHBoxLayout(); head.addWidget(logo_label(cc, 72))
        col = QVBoxLayout(); col.addWidget(label(tr("end.title"), "title"))
        col.addWidget(label(end_sub(c, d), "h2", True))
        col.addWidget(label(tr("end.reason." + (c.retire_reason or "choice")), "muted")); head.addLayout(col, 1); root.addLayout(head)
        tabs = QTabWidget(); root.addWidget(tabs, 1)
        tabs.addTab(self._summary(c, d, rep), tr("end.tab.summary"))
        tabs.addTab(self._seasons(c, d), tr("end.tab.seasons"))
        tabs.addTab(self._comps(c, rep), tr("end.tab.comps"))
        tabs.addTab(self._transfers(c, d), tr("end.tab.transfers"))
        tabs.addTab(self._honours(c, d), tr("end.tab.honours"))
        chron = [[s["season"], chronicle_text(e, d)] for s in c.seasons for e in s.get("chronicle", [])]
        if chron:
            tabs.addTab(SortTable([tr("col.season"), tr("chron.title")], chron, [90]), tr("end.tab.chronicle"))
        if c.coach and c.coach.get("seasons"):
            from .coach_pages import coach_summary_widget, coach_seasons_table
            tabs.addTab(coach_summary_widget(c, d), tr("end.tab.coach"))
            tabs.addTab(coach_seasons_table(c, d), tr("end.tab.coach_seasons"))
            tabs.setCurrentIndex(tabs.count() - 2)
        row = QHBoxLayout()
        b = QPushButton(tr("end.export")); b.clicked.connect(self.export.emit); row.addWidget(b)
        dz = QPushButton(tr("ai.diaries")); dz.clicked.connect(lambda: self.diary.emit("")); row.addWidget(dz); row.addStretch()
        if c.coach is None:                                    # игрок завершил карьеру без тренерства: можно стать тренером и сейчас
            bc = QPushButton(tr("end.become_coach")); bc.clicked.connect(self.become_coach.emit); row.addWidget(bc)
        n = QPushButton(tr("end.new")); n.setObjectName("primary"); n.clicked.connect(self.new_career.emit); row.addWidget(n)
        q = QPushButton(tr("end.quit")); q.clicked.connect(self.quit_game.emit); row.addWidget(q)
        root.addLayout(row)

    def _summary(self, c, d, rep):
        t = rep["totals"]; w = QWidget(); g = QGridLayout(w); g.setContentsMargins(24, 20, 24, 20); g.setVerticalSpacing(10); g.setHorizontalSpacing(30)
        rows = [(tr("end.games"), t["games"]), (tr("end.goals"), t["goals"]), (tr("end.assists"), t["assists"])]
        if c.pos == "GK": rows.append((tr("end.cs"), t["cs"]))
        rows += [(tr("end.caps"), t["caps"]), (tr("end.intl_goals"), t["intl_goals"]),
                 (tr("end.peak"), tr("end.peak_val", o=rep["peak_ovr"], a=rep["peak_age"]))]
        tc = rep["trophy_cats"]
        rows.append((tr("end.trophies"), " · ".join(f"{tr('end.cat.' + k)}: {v}" for k, v in tc.items()) or tr("end.none"), theme.GOLD))
        rows.append((tr("end.awards"), " · ".join(f"{award_name(k)} ×{v}" for k, v in rep["award_counts"].items()) or tr("end.none"), theme.AWARD))
        rows.append((tr("end.clubs"), "  →  ".join(club_stint_text(x, d) for x in rep["clubs"]) or tr("end.none"), None))
        cap = {}
        for s in c.seasons:
            if s.get("captain"):
                cap[s["club"]] = cap.get(s["club"], 0) + 1
        if cap:
            rows.append((tr("end.captain"), ", ".join(f"{d.clubs[k]['name']} ({tr('end.captain_val', n=v)})" for k, v in cap.items()), theme.GOLD))
        for i, row in enumerate(rows):
            k, v, color = row if len(row) == 3 else (*row, None)
            g.addWidget(label(k, "muted"), i, 0, Qt.AlignTop); lv = label(str(v), "h2" if i < 3 else None, True); g.addWidget(lv, i, 1)
            if color: lv.setStyleSheet(f"color: {color};")
        g.setRowStretch(len(rows), 1); g.setColumnStretch(1, 1)
        return w

    def _seasons(self, c, d):
        gk = c.pos == "GK"
        rows = []
        for s in c.seasons:
            tro = [short_trophy(t["code"]) for t in s["trophies"]]
            aws = season_award_names(s)
            rows.append([s["season"], s["age"], d.clubs[s["club"]]["name"], youth_league_name(s), cell(f"{s['rank']}/{s['n']}", s["rank"]), s["games"],
                         s["goals"], s["cs"] if gk else s["assists"], s["ovr"], f"{s['rating']:.2f}" if s.get("rating") else "—",
                         cell(", ".join(tro), len(tro) or None, theme.GOLD, tip="\n".join(trophy_name(t) for t in s["trophies"]) or None),
                         cell(", ".join(aws), len(aws) or None, theme.AWARD, tip="\n".join(aws) or None)])
        hd = [tr("col.season"), tr("col.age"), tr("col.club"), tr("col.league"), tr("col.rank"), tr("col.games"), tr("col.goals"),
              tr("col.cs" if gk else "col.assists"), tr("col.ovr"), tr("col.rating"), tr("col.trophies_only"), tr("col.awards")]
        return SortTable(hd, rows, [70, 50, 170, 160, 60, 60, 60, 60, 50, 60, 170], center=(1, 4, 5, 6, 7, 8, 9))

    def _comps(self, c, rep):
        gk = c.pos == "GK"
        rows = [(lang_name(b), b["games"], b["goals"], b["cs"] if gk else b["assists"]) for b in rep["comps_chrono"]]
        hd = [tr("col.comp"), tr("col.games"), tr("col.goals"), tr("col.cs" if gk else "col.assists")]
        return SortTable(hd, rows, [420, 90, 90, 90], center=(1, 2, 3))

    def _transfers(self, c, d):
        rows = []
        tl = c.transfers
        for i, t in enumerate(tl):
            y0 = int(t["season"][:4])
            y1 = int(tl[i + 1]["season"][:4]) if i + 1 < len(tl) else c.year
            rows.append([t["season"], d.clubs[t["from"]]["name"] if t["from"] else "—", d.clubs[t["to"]]["name"], tr("type." + t["type"]),
                         cell(money(t["fee"]) if t["fee"] > 0 else "—", t["fee"] if t["fee"] > 0 else None), cell(f"{y0}–{y1}", y1 - y0)])
        return SortTable([tr("col.years"), tr("col.from"), tr("col.to"), tr("col.type"), tr("col.fee"), tr("col.period")], rows,
                         [90, 220, 220, 190, 130], center=(0, 4, 5))

    def _honours(self, c, d):
        """Трофеи (золотые - клубные, оранжевые - сборной) и личные награды (голубые, на голубом фоне со звёздочкой) в одной таблице."""
        items = []
        for t in c.trophies:
            kind = {"national": "hon.national", "youth": "hon.youth"}.get(t["cat"], "hon.club")
            color = theme.NATIONAL if t["cat"] == "national" else theme.GOLD
            who = d.country_name(c.nat, i18n.LANG) if t["cat"] == "national" else d.clubs[t["club"]]["name"]
            items.append((t["season"], 0, [t["season"], cell(tr(kind), color=color), cell("◆ " + trophy_name(t), color=color), who]))
        for a in c.awards:
            nm = "★ " + award_name(a["code"], a.get("rank"))
            items.append((a["season"], 1, [cell(a["season"], bg=theme.AWARD_BG), cell(tr("hon.award"), color=theme.AWARD, bg=theme.AWARD_BG, bold=True),
                                           cell(nm, color=theme.AWARD, bg=theme.AWARD_BG, bold=True),
                                           cell(d.clubs[a["club"]]["name"] if a.get("club") in d.clubs else "", bg=theme.AWARD_BG)]))
        for t in (c.coach or {}).get("trophies", []):          # трофеи тренерской карьеры - тем же золотом, но с подписью «тренер»
            items.append((t["season"], 2, [t["season"], cell(tr("hon.coach"), color=theme.GOLD, bold=True), cell("◆ " + trophy_name(t), color=theme.GOLD),
                                           d.clubs[t["club"]]["name"]]))
        for a in (c.coach or {}).get("awards", []):
            items.append((a["season"], 3, [cell(a["season"], bg=theme.AWARD_BG), cell(tr("hon.coach_award"), color=theme.AWARD, bg=theme.AWARD_BG, bold=True),
                                           cell("★ " + award_name(a["code"]), color=theme.AWARD, bg=theme.AWARD_BG, bold=True),
                                           cell(d.clubs[a["club"]]["name"], bg=theme.AWARD_BG)]))
        items.sort(key=lambda x: (x[0], x[1]))
        rows = [x[2] for x in items] or [[tr("end.none"), "", "", ""]]
        return SortTable([tr("col.season"), tr("col.kind"), tr("col.honour"), tr("col.club")], rows, [90, 190, 460], center=(0,))

def club_stint_text(x, d):
    """«Клуб (2021–2024)»: период в клубе; возвращение в тот же клуб - отдельный период со своими годами."""
    return f"{d.clubs[x['club']]['name']} ({x['y0']}–{x['y1']})" if "y0" in x else f"{d.clubs[x['club']]['name']} ({x['from'][:4]}–{x['to'][:4]})"

def end_sub(c, d):
    """«Имя завершил карьеру в N лет»; если был тренером - и возраст завершения тренерской карьеры."""
    if c.coach and c.coach.get("seasons"):
        return tr("end.sub_coach", name=c.name, age=c.player_retire_age, cage=c.player.age)
    return tr("end.sub_young", name=c.name, age=c.player_retire_age)
