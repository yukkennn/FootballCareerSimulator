"""Главное окно: навигация между экранами, автосохранение."""
import time
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QStackedWidget, QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton,
                               QLabel, QFileDialog, QMessageBox, QApplication)
from PySide6.QtCore import Qt
from .. import i18n, saves
from ..i18n import tr
from ..career import Career
from ..text import money, trophy_name, lang_name, club_result, nat_comp_name, nat_result, award_name
from . import pages, coach_pages
from .diary import DiaryManager, DiaryDialog, SettingsDialog
from .. import story

def summary_text(c, d):
    rep = c.report(); t = rep["totals"]
    gk = c.pos == "GK"
    L = [pages.end_sub(c, d), tr("end.reason." + (c.retire_reason or "choice")), ""]
    L += [f"{tr('end.games')}: {t['games']}", f"{tr('end.goals')}: {t['goals']}", f"{tr('end.assists')}: {t['assists']}"]
    if gk: L.append(f"{tr('end.cs')}: {t['cs']}")
    L += [f"{tr('end.caps')}: {t['caps']}", f"{tr('end.intl_goals')}: {t['intl_goals']}", f"{tr('end.peak')}: {tr('end.peak_val', o=rep['peak_ovr'], a=rep['peak_age'])}", ""]
    L.append(tr("end.tab.comps") + ":")
    for b in rep["comps"]:
        L.append(f"  {lang_name(b):<46} {b['games']:>4} / {b['goals']:>4} / {b['cs'] if gk else b['assists']:>4}")
    L += ["", tr("end.tab.transfers") + ":"]
    for x in c.transfers:
        L.append(f"  {x['season']}  {d.clubs[x['from']]['name'] if x['from'] else '—'} -> {d.clubs[x['to']]['name']}  [{tr('type.' + x['type'])}]  {money(x['fee']) if x['fee'] > 0 else ''}")
    L += ["", tr("end.clubs") + ":", "  " + "  ->  ".join(pages.club_stint_text(x, d) for x in rep["clubs"])]
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

class LoadDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent); self.d = data; self.chosen = None
        self.setWindowTitle(tr("load.title")); self.resize(640, 420)
        v = QVBoxLayout(self); self.list = QListWidget(); v.addWidget(self.list)
        self.items = saves.list_saves()
        if not self.items:
            v.insertWidget(0, QLabel(tr("load.empty")))
        for it in self.items:
            when = time.strftime("%d.%m.%Y %H:%M", time.localtime(it["mtime"]))
            club = data.clubs[it["club"]]["name"] if it["club"] in data.clubs else "—"
            if it["status"] in ("retired", "coach_retired"):
                txt = tr("load.row_retired", name=it["name"], when=when)
            elif it["status"].startswith("coach"):
                txt = tr("load.row_coach", name=it["name"], age=it["age"], club=club, when=when)
            else:
                txt = tr("load.row", name=it["name"], age=it["age"], club=club, when=when)
            self.list.addItem(QListWidgetItem(txt))
        self.list.itemDoubleClicked.connect(lambda _: self._open())
        row = QHBoxLayout()
        d = QPushButton(tr("load.delete")); d.clicked.connect(self._delete); row.addWidget(d); row.addStretch()
        c = QPushButton(tr("load.cancel")); c.clicked.connect(self.reject); row.addWidget(c)
        o = QPushButton(tr("load.open")); o.setObjectName("primary"); o.clicked.connect(self._open); row.addWidget(o)
        v.addLayout(row)

    def _open(self):
        r = self.list.currentRow()
        if r >= 0:
            self.chosen = self.items[r]["path"]; self.accept()

    def _delete(self):
        r = self.list.currentRow()
        if r >= 0:
            saves.delete(self.items[r]["path"]); self.list.takeItem(r); self.items.pop(r)

class MainWindow(QMainWindow):
    def __init__(self, data):
        super().__init__()
        self.d, self.career = data, None
        self.diaries = DiaryManager(self)                     # дневники сезонов: нейросеть пишет в фоне (game/ui/diary.py)
        self.stack = QStackedWidget(); self.setCentralWidget(self.stack)
        self.setWindowTitle(tr("app.title")); self.resize(1360, 820); self.setMinimumSize(1200, 740)
        self.show_start()

    def open_diary(self, key=""):
        if self.career is None:
            return
        self.diaries.attach(self.career, self.d)
        DiaryDialog(self.diaries, key or None, self).exec()

    def open_settings(self):
        SettingsDialog(self).exec()

    def _set(self, w):
        while self.stack.count():
            old = self.stack.widget(0); self.stack.removeWidget(old); old.deleteLater()
        self.stack.addWidget(w); self.stack.setCurrentWidget(w)
        self.page = w

    # --- экраны
    def show_start(self):
        p = pages.StartPage(self.d)
        p.proceed.connect(self.on_start); p.load_clicked.connect(self.on_load); p.lang_changed.connect(self.on_lang)
        p.settings_clicked.connect(self.open_settings)
        self._set(p)

    def on_lang(self, lang):
        i18n.set_lang(lang); self.setWindowTitle(tr("app.title")); self.show_start()

    def on_start(self, name, nat, pos, foot, height):
        self.career = Career(self.d, name, nat, pos, 1, lang=i18n.LANG, foot=foot, height=height)    # предложения клубов после каждого сезона
        self.show_summary()

    def show_summary(self):
        p = pages.SummaryPage(self.career, self.d)
        p.reroll.connect(lambda: (self.career.reroll(), self.show_summary())); p.back.connect(self.show_start); p.start.connect(self.show_academy)
        self._set(p)

    def show_academy(self):
        p = pages.AcademyPage(self.career, self.d); p.chosen.connect(self.on_academy); self._set(p)

    def on_academy(self, cid):
        self.career.choose_academy(cid); saves.save(self.career); self.show_career()

    def show_career(self):
        p = pages.CareerPage(self.career, self.d); p.play.connect(self.on_play); p.menu.connect(self.show_start); p.diary.connect(self.open_diary)
        p.retire.connect(self.ask_retire); self._set(p)

    def on_play(self):
        recs, reason = self.career.play_period()
        saves.save(self.career)
        self.show_report(recs, reason)
        n = len(self.career.seasons)                             # автодневник: нейросеть пишет новые сезоны в фоне
        self.diaries.attach(self.career, self.d)
        self.diaries.request(story.missing(self.career, [f"p:{i}" for i in range(n - len(recs), n)]), auto=True)

    def show_report(self, recs, reason):
        p = pages.ReportPage(self.career, self.d, recs, reason); p.done.connect(self.after_report); p.diary.connect(self.open_diary); self._set(p)

    def after_report(self):
        if self.career.status != "retired":
            self.show_offers()
        elif self.career.coach is None:              # карьера закончилась сама (40 лет): выбор - просто завершить или стать тренером
            self.choose_after_retire(early=False)
        else:
            self.show_end()

    def show_offers(self):
        p = pages.OffersPage(self.career, self.d); p.accept.connect(self.on_accept); p.retire.connect(self.ask_retire); self._set(p)

    def on_accept(self, idx):
        self.career.accept(idx); saves.save(self.career); self.show_career()

    def ask_retire(self):
        self.choose_after_retire(early=True)

    def choose_after_retire(self, early):
        """Завершение карьеры игрока: «Завершить карьеру» / «Завершить и стать тренером» (и «Отмена», если завершаем досрочно)."""
        q = QMessageBox(QMessageBox.Question, tr("retire.title"), tr("retire.question_early" if early else "retire.question"), parent=self)
        plain = q.addButton(tr("retire.plain"), QMessageBox.AcceptRole)
        coach = q.addButton(tr("retire.coach"), QMessageBox.AcceptRole)
        if early:
            q.addButton(tr("retire.cancel"), QMessageBox.RejectRole)
        q.exec()
        clicked = q.clickedButton()
        if clicked is coach:
            self.on_retire(coach=True)
        elif clicked is plain or not early:            # окно закрыли крестиком после 40 лет - просто итоги карьеры
            self.on_retire(coach=False)

    def on_retire(self, coach=False):
        if self.career.status != "retired":
            self.career.retire_now()
        if coach:
            self.career.start_coaching(); saves.save(self.career); self.show_coach_offers()
        else:
            saves.save(self.career); self.show_end()

    def show_end(self):
        p = pages.EndPage(self.career, self.d)
        p.new_career.connect(self.show_start); p.quit_game.connect(self.close); p.export.connect(self.on_export)
        p.become_coach.connect(lambda: self.on_retire(coach=True)); p.diary.connect(self.open_diary); self._set(p)

    # --- тренерская карьера
    def show_coach_offers(self):
        p = coach_pages.CoachOffersPage(self.career, self.d); p.accept.connect(self.on_coach_accept); p.retire.connect(self.ask_coach_retire)
        self._set(p)

    def on_coach_accept(self, idx):
        self.career.coaching().accept(idx); saves.save(self.career); self.show_coach()

    def show_coach(self):
        p = coach_pages.CoachPage(self.career, self.d); p.play.connect(self.on_coach_play); p.menu.connect(self.show_start); p.diary.connect(self.open_diary)
        p.retire.connect(self.ask_coach_retire); self._set(p)

    def on_coach_play(self, tactic="balanced"):
        """Перед сезоном - летнее трансферное окно, затем первая половина сезона."""
        self.career.coach["tactic"] = tactic
        self.show_transfer("summer", self._coach_first_half)

    def show_transfer(self, kind, back):
        """Трансферное окно; после каждой сделки экран перестраивается, «Готово» -> back()."""
        tw = self.career.coaching().window()
        tw.open(kind)
        def refresh():
            p = coach_pages.TransferWindowPage(self.career, self.d, self.career.coach["window"]["start_ovr"])
            p.buy.connect(lambda i: (tw.buy(i), refresh())); p.sell.connect(lambda pid: (tw.sell(pid), refresh()))
            p.youth.connect(lambda i: (tw.youth(i), refresh())); p.done.connect(back)
            p.formation.connect(lambda f: (self.career.coach.__setitem__("formation", f), refresh()))
            ops = {"loan_out": tw.loan_out, "loan_offer": tw.accept_loan_offer, "hire": tw.hire_scout, "fire": tw.fire_scout,
                   "refresh": lambda _x: None}                     # основа изменена вручную - экран перестраивается
            p.action.connect(lambda k, x: (ops[k](x), refresh()))
            self._set(p)
        refresh()

    def _coach_first_half(self):
        mid = self.career.coaching().begin_season(self.career.coach["tactic"])
        self._show_mid(mid)

    def _show_mid(self, mid=None):
        mid = mid or self.career._coach_pending["mid"]
        p = coach_pages.MidSeasonPage(self.career, self.d, mid); p.done.connect(self.on_coach_second_half)
        p.winter.connect(self._winter_window); self._set(p)

    def _winter_window(self, tactic):
        self.career.coach["tactic"] = tactic
        self.show_transfer("winter", self._show_mid)

    def on_coach_second_half(self, tactic=""):
        rec = self.career.coaching().finish_season(tactic or None)
        saves.save(self.career)
        p = coach_pages.CoachReportPage(self.career, self.d, rec); p.done.connect(self.after_coach_report); p.diary.connect(self.open_diary); self._set(p)
        self.diaries.attach(self.career, self.d)
        self.diaries.request(story.missing(self.career, [f"c:{len(self.career.coach['seasons']) - 1}"]), auto=True)

    def after_coach_report(self):
        st = self.career.status
        {"coaching": self.show_coach, "coach_offers": self.show_coach_offers, "coach_retired": self.show_end}[st]()

    def ask_coach_retire(self):
        q = QMessageBox(QMessageBox.Question, tr("app.title"), tr("coach.retire_q"), parent=self)
        yes = q.addButton(tr("yes"), QMessageBox.AcceptRole); q.addButton(tr("no"), QMessageBox.RejectRole)
        q.exec()
        if q.clickedButton() is yes:
            self.on_coach_retire()

    def on_coach_retire(self):
        self.career.coaching().retire(); saves.save(self.career); self.show_end()

    def on_export(self):
        name = f"{self.career.name}_career.txt"
        path, _ = QFileDialog.getSaveFileName(self, tr("end.export"), str(Path.home() / name), "Text (*.txt)")
        if path:
            book = story.book_text(self.career, self.d)                 # дневники сезонов - «книгой» после итогов
            Path(path).write_text(summary_text(self.career, self.d) + ("\n\n\n" + book if book else ""), encoding="utf-8")
            QMessageBox.information(self, tr("app.title"), tr("end.exported", p=path))

    def on_load(self):
        dlg = LoadDialog(self.d, self)
        if dlg.exec() and dlg.chosen:
            self.open_save(dlg.chosen)

    def open_save(self, path):
        try:
            self.career = saves.load(path, self.d)
        except (KeyError, ValueError, TypeError, IndexError) as e:
            QMessageBox.warning(self, tr("app.title"), f"{tr('load.broken')}\n{path}\n{type(e).__name__}: {e}")
            return
        s = self.career.status
        {"academy_pick": self.show_academy, "playing": self.show_career, "offers": self.show_offers, "retired": self.show_end,
         "coach_offers": self.show_coach_offers, "coaching": self.show_coach, "coach_retired": self.show_end}[s]()
