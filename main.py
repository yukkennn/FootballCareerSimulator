#!/usr/bin/env python3
"""Симулятор футбольной карьеры: точка входа (и для запуска из исходников, и для FootballCareerSim.exe)."""
import sys
import traceback
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from game import i18n
from game.paths import DB_PATH, ROOT, user_dir
from game.ui import theme

LOG = user_dir() / "error.log"

def _excepthook(kind, value, tb):
    """Ошибка не должна молча закрывать игру (у .exe нет консоли): пишем её в файл и показываем окно."""
    text = "".join(traceback.format_exception(kind, value, tb))
    try:
        LOG.write_text(text, encoding="utf-8")
    except OSError:
        pass
    sys.__stderr__ and sys.__stderr__.write(text)
    if QApplication.instance():
        QMessageBox.critical(None, "Football Career Sim", f"{value}\n\n{LOG}")

def main():
    sys.excepthook = _excepthook
    if sys.platform == "win32":                     # своя иконка на панели задач, а не иконка Python
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FootballCareerSim")
        except Exception:
            pass
    app = QApplication(sys.argv)
    icon = ROOT / "assets" / "icon.ico"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    i18n.init_lang()
    app.setStyleSheet(theme.STYLE)
    if not DB_PATH.exists():
        QMessageBox.critical(None, "Error", f"{i18n.tr('err.db')}:\n{DB_PATH}")
        return 1
    from game.data import GameData
    from game.ui.main_window import MainWindow
    win = MainWindow(GameData())
    win.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
