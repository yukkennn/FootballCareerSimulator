"""Прогон интерфейса без экрана: полная карьера через экраны + скриншоты в /tmp/shots (если задана переменная SHOTS=1)."""
import os, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from game import i18n
from game.ui import theme
from game.data import GameData
from game.ui.main_window import MainWindow, summary_text
from game.ui import pages, coach_pages
from game import saves, paths

def run(lang="ru", shots=False):
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.STYLE)
    i18n.LANG = lang
    out = Path("/tmp/shots") / lang
    if shots: out.mkdir(parents=True, exist_ok=True)
    d = GameData(); w = MainWindow(d); w.resize(1360, 820); w.show()
    def snap(name):
        app.processEvents()
        if shots: w.grab().save(str(out / f"{name}.png"))
    st = w.page; assert isinstance(st, pages.StartPage)
    snap("1_start")
    st.search.setText("kaz" if lang == "en" else "каз")
    visible = [i for i in range(st.list.count()) if not st.list.item(i).isHidden()]
    assert visible, "поиск ничего не нашёл"
    st.list.setCurrentRow(visible[0]); st.pos_group.buttons()[-1].click()
    assert st.btn_next.isEnabled(); snap("1b_start_filled")
    st._random_name(); assert len(st.player_name().split()) >= 2, st.player_name()
    st.first.setText("Алишер" if lang == "ru" else "Alisher"); st.last.setText("Ахметов" if lang == "ru" else "Akhmetov"); st.btn_next.click()
    assert isinstance(w.page, pages.SummaryPage); snap("2_summary")
    assert w.career.name == ("Алишер Ахметов" if lang == "ru" else "Alisher Akhmetov")
    w.page.reroll.emit(); assert isinstance(w.page, pages.SummaryPage)
    w.page.start.emit(); assert isinstance(w.page, pages.AcademyPage); snap("3_academy")
    w.on_academy(w.career.academy_ids[0]); assert isinstance(w.page, pages.CareerPage); snap("4_career_start")
    n = 0
    early = lang == "en"                 # en: завершаем карьеру сами в 33 года; ru: играем до автоматического конца в 40 и становимся тренером
    # окно выбора «завершить / стать тренером» модальное: в тесте выбор делается сразу
    w.choose_after_retire = lambda early=False, coach=not early: w.on_retire(coach=coach)
    while w.career.status not in ("retired", "coach_offers") and n < 60:
        n += 1
        w.on_play()
        assert isinstance(w.page, pages.ReportPage)
        if n in (1, 3, 5): snap(f"5_report_{n}")
        w.after_report()
        if w.career.status == "offers":
            assert isinstance(w.page, pages.OffersPage)
            if n in (3, 4): snap(f"6_offers_{n}")
            if early and w.career.player.age >= 33:
                w.on_retire()
            else:
                w.page.accept.emit(0)
            if w.career.status != "retired":
                assert isinstance(w.page, pages.CareerPage)
                if n in (4, 8): snap(f"7_career_{n}")
    assert w.career.player.age >= 33 if early else w.career.player.age == 40, w.career.player.age
    if not early:
        # --- тренерская карьера: предложения -> клуб -> 8 сезонов -> завершение
        assert w.career.status == "coach_offers" and isinstance(w.page, coach_pages.CoachOffersPage); snap("9_coach_offers")
        w.page.accept.emit(0); assert isinstance(w.page, coach_pages.CoachPage); snap("9b_coach_club")
        # ручная основа: вторым вратарём заменяем первого
        from game import squad as squad_mod
        gks = [p for p in squad_mod.squad(w.career) if p["pos"] == "GK"]
        w.page._lineup_auto(False); assert w.career.coach["lineup_mode"] == "manual"
        w.page._lineup_set(0, gks[-1]["id"])
        assert squad_mod.current_xi(w.career)[0][1]["id"] == gks[-1]["id"]
        snap("9b_coach_lineup")
        w.page._lineup_auto(True); assert w.career.coach["lineup_mode"] == "auto"
        w.page._rotation_changed("some"); assert w.career.coach["rotation"] == "some"
        for k in range(8):
            w.page.play.emit("attack" if k % 2 else "press")                      # тактика на первую половину
            assert isinstance(w.page, coach_pages.TransferWindowPage)               # летнее трансферное окно
            win = w.career.coach["window"]; b0 = w.career.coach["budget"]
            if k == 0:                                                             # сортировка и фильтр рынка
                mt = w.page.mt
                ovr = lambda: [int(mt.item(r, 3).text()) for r in range(mt.rowCount())]
                w.page._sort_clicked(3); assert ovr() == sorted(ovr(), reverse=True)
                w.page._sort_clicked(3); assert ovr() == sorted(ovr())
                w.page._sort_clicked(3); assert win.get("sort") is None
                w.page.filter.setCurrentIndex(2)                                   # только защитники
                assert all(squad_mod.LINE[mt.item(r, 1).text()] == "DEF" for r in range(mt.rowCount()))
                w.page.filter.setCurrentIndex(0)
                assert len(win["cands"]) >= 12
                # скаут: нанимаем самого дешёвого, вилка потенциала сужается
                from game import transfers as tr_mod
                w0 = tr_mod.pot_width(w.career.coach)
                w.page.action.emit("hire", 0)
                assert len(w.career.coach["scouts"]) == 1 and tr_mod.pot_width(w.career.coach) <= w0
                w.page.ltabs.setCurrentIndex(4); snap("9a_transfer_scouts")
                w.page.action.emit("fire", 0); assert not w.career.coach["scouts"]
                w.page.action.emit("hire", 2 if w.career.coach["budget"] > 3 else 0)
                assert w.page.ltabs.currentIndex() == 4                          # вкладка помнится после перестройки экрана
                w.page.ltabs.setCurrentIndex(0)
                win = w.career.coach["window"]; b0 = w.career.coach["budget"]
            if k == 1:                                                             # аренда: отдаём молодого запасного
                xi = {p["id"] for _, p, _ in squad_mod.current_xi(w.career) if p}
                young = [p for p in squad_mod.squad(w.career) if p["id"] not in xi and not p.get("loan_from")]
                if young:
                    pid = min(young, key=lambda p: p["age"])["id"]
                    w.page.action.emit("loan_out", pid)
                    from game import stars as stars_mod
                    pl = stars_mod.find(w.career.stars, pid)
                    assert pl["loan_from"] == w.career.coach["club"] and pl["club"] != w.career.coach["club"]
                w.page.ltabs.setCurrentIndex(3); snap("9a_transfer_loans")
                w.page.ltabs.setCurrentIndex(1); snap("9a_transfer_squad")
                # ручная основа после сделок, прямо в трансферном окне
                gks = [p for p in squad_mod.squad(w.career) if p["pos"] == "GK" and squad_mod.available(p)]
                coach_pages.lineup_auto(w.career, False); coach_pages.lineup_set(w.career, 0, gks[-1]["id"])
                w.page.action.emit("refresh", None)
                assert squad_mod.current_xi(w.career)[0][1]["id"] == gks[-1]["id"]
                w.page.ltabs.setCurrentIndex(2); snap("9a_transfer_lineup")
                coach_pages.lineup_auto(w.career, True); w.page.action.emit("refresh", None)
                w.page.ltabs.setCurrentIndex(0)
                win = w.career.coach["window"]; b0 = w.career.coach["budget"]
            if len(squad_mod.squad(w.career)) >= squad_mod.MAX_SQUAD:              # заявка полна: сначала продаём
                w.page.sell.emit(min(squad_mod.squad(w.career), key=lambda p: p["ovr"])["id"])
                win = w.career.coach["window"]; b0 = w.career.coach["budget"]
            cheap = [i for i, cd in enumerate(win["cands"]) if cd["price"] <= b0 and not cd.get("refuse") and not cd["done"]]
            if cheap:
                w.page.buy.emit(cheap[0]); assert w.career.coach["budget"] < b0 and w.career.coach["window"]["cands"][cheap[0]]["done"]
            if k == 1:                                                             # продажа самого слабого игрока состава
                from game import squad as squad_mod
                weakest = min(squad_mod.squad(w.career), key=lambda p: p["ovr"])
                w.page.sell.emit(weakest["id"])
                assert weakest["club"] != w.career.coach["club"]
                w.page.formation.emit("4-4-2"); assert w.career.coach["formation"] == "4-4-2"
            if k in (0, 1): snap(f"9a_transfer_{k}")
            w.page.done.emit()
            assert isinstance(w.page, coach_pages.MidSeasonPage)
            if k == 2 and w.page.tactic:                                           # зимнее окно и возврат
                w.page.winter.emit("defense"); assert isinstance(w.page, coach_pages.TransferWindowPage); snap("9a_transfer_winter")
                w.page.done.emit(); assert isinstance(w.page, coach_pages.MidSeasonPage)
            if k in (0, 3): snap(f"9b_coach_mid_{k}")
            w.page.done.emit(w.page.tactic.value() if w.page.tactic else "")       # вторая половина (или уволен посреди сезона)
            assert isinstance(w.page, coach_pages.CoachReportPage)
            if k in (0, 3): snap(f"9c_coach_report_{k}")
            w.after_coach_report()
            if w.career.status == "coach_offers":
                assert isinstance(w.page, coach_pages.CoachOffersPage); snap("9d_coach_offers_again")
                w.page.accept.emit("stay" if w.career.coach["can_stay"] else 0)
            assert isinstance(w.page, coach_pages.CoachPage)
        snap("9e_coach_club_later")
        assert len(w.career.coach["seasons"]) == 8
        w.on_coach_retire()
    assert w.career.status in ("retired", "coach_retired") and isinstance(w.page, pages.EndPage)
    snap("8_end")
    tabs = w.page.findChild(pages.QTabWidget)
    tabs.setCurrentIndex(2); snap("8b_end_comps")
    # сортировка: от большего -> от меньшего -> исходный порядок
    tabs.setCurrentIndex(1); t = tabs.currentWidget()
    col = 5                                              # матчи
    first = lambda: [t.item(r, 0).text() for r in range(t.rowCount())]
    games = lambda: [int(t.item(r, col).text()) for r in range(t.rowCount())]
    orig = first()
    t.horizontalHeader().sectionClicked.emit(col); assert games() == sorted(games(), reverse=True)
    t.horizontalHeader().sectionClicked.emit(col); assert games() == sorted(games())
    t.horizontalHeader().sectionClicked.emit(col); assert first() == orig
    snap("8c_end_seasons")
    tabs.setCurrentIndex(4); snap("8d_end_honours")
    tabs.setCurrentIndex(3); snap("8e_end_transfers")
    if not early:
        assert tabs.count() == 8, tabs.count()                      # + «Летопись», «Тренерская карьера», «Сезоны тренера»
        tabs.setCurrentIndex(5); snap("8h_end_chronicle")
        tabs.setCurrentIndex(6); snap("8f_end_coach"); tabs.setCurrentIndex(7); snap("8g_end_coach_seasons")
    txt = summary_text(w.career, d); assert len(txt) > 200
    # сохранение и загрузка
    paths_ = [s["path"] for s in saves.list_saves() if s["id"] == w.career.id]; assert paths_, "сохранение не найдено"
    w.open_save(paths_[0]); assert isinstance(w.page, pages.EndPage)
    for s in paths_: saves.delete(s)
    print(f"[{lang}] карьера: {len(w.career.seasons)} сезонов, возраст {w.career.player.age}, трофеев {len(w.career.trophies)} — UI OK")

if __name__ == "__main__":
    # изолируем сохранения во временную папку
    tmp = tempfile.mkdtemp(); paths.user_dir = lambda: Path(tmp)
    import game.paths as gp; gp.saves_dir = lambda: (Path(tmp) / "saves").mkdir(exist_ok=True) or Path(tmp) / "saves"
    saves.saves_dir = gp.saves_dir
    shots = os.environ.get("SHOTS") == "1"
    for lang in ("ru", "en"):
        run(lang, shots)
