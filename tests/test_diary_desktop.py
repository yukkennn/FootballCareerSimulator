"""Дневник сезона в версии для компьютера без экрана: автодневник в фоне после сезона, окно дневников, настройки, тренерский сезон,
книга в экспорте. Нейросеть подменена заглушкой (настоящие запросы не уходят). Запуск: python tests/test_diary_desktop.py"""
import os, sys, tempfile, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
home = tempfile.mkdtemp()
os.environ["HOME"] = os.environ["USERPROFILE"] = home
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtWidgets import QApplication
from game import i18n, llm, story
from game.ui import theme
from game.data import GameData
from game.ui.main_window import MainWindow
from game.ui.diary import DiaryDialog, SettingsDialog

calls = []
def fake_write(system, user):
    time.sleep(0.05)
    calls.append(user)
    who = "тренер" if "главного тренера" in system else "игрок"
    return f"**1 августа**\nДневник ({who}).\n\nПАМЯТЬ:\n- Лейла {len(calls)}", "Gemini", "fake-model"
llm.write = fake_write

def wait(mgr, timeout=20):
    t = time.time()
    while (mgr.worker is not None or mgr.queue) and time.time() - t < timeout:
        app.processEvents(); time.sleep(0.01)
    app.processEvents()
    assert mgr.worker is None and not mgr.queue, "дневник не дописался"

app = QApplication(sys.argv)
i18n.LANG = "ru"
app.setStyleSheet(theme.STYLE)
win = MainWindow(GameData())
mgr = win.diaries

# без настроек нейросети автодневник молчит
win.on_start("Тест", "BRA", "ST", "R", 182)
win.career.choose_academy(win.career.academy_ids[0])
win.on_play(); wait(mgr)
assert not calls, "без настроек не должно быть запросов"

# настройки: Gemini с ключом, автодневник включён
llm.save_settings({"provider": "gemini", "model": {"gemini": "gemini-x"}, "key": {"gemini": "k"}, "auto": True})
assert llm.ready() and llm.current()["model"] == "gemini-x"
dlg = SettingsDialog(win); dlg._save(); assert llm.ready()

for _ in range(3):
    if win.career.status == "offers":
        win.career.accept(0)
    win.on_play(); wait(mgr)
c = win.career
written = [k for k in story.keys(c) if story.record(c, k)[2].get("story")]
assert len(written) >= 3, written
st = story.record(c, written[-1])[2]["story"]
assert st["text"].startswith("**1 августа**") and st["memory"].startswith("- Лейла") and st["model"] == "fake-model"
assert "Лейла" in calls[-1], "следующий дневник не получил память прошлого"

# окно дневников: выбор сезона, «Написать заново»
d = DiaryDialog(mgr, written[0], win); d.show(); app.processEvents()
assert "Дневник (игрок)" in d.view.toPlainText()
d.box.setCurrentIndex(0); d._write(); wait(mgr); app.processEvents()
d.close()

# тренер: дневник тренерского сезона пишется сам после итогов сезона
c.retire_now(); c.start_coaching(); c.coaching().accept(0)
c.coach["tactic"] = "balanced"
mid = c.coaching().begin_season("balanced")
win.on_coach_second_half("balanced"); wait(mgr)
ck = f"c:{len(c.coach['seasons']) - 1}"
assert story.record(c, ck)[2].get("story", {}).get("text", "").startswith("**1 августа**"), "нет дневника тренера"
assert "главного тренера" in story.prompt(c, win.d, ck)["system"]

# книга в экспорте
book = story.book_text(c, win.d)
assert book.startswith("ДНЕВНИК: Тест") and "1 августа" in book and "**" not in book
print(f"desktop diary ok: запросов {len(calls)}, дневников {sum(1 for k in story.keys(c) if story.record(c, k)[2].get('story'))}")
