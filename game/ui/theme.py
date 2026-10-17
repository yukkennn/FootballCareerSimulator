BG, PANEL, PANEL2, TEXT, MUTED, ACCENT, GOLD, RED = "#10141a", "#1a212b", "#232c39", "#e8ecf1", "#8d98a8", "#2ecc71", "#f5c542", "#e55353"
AWARD, AWARD_BG = "#7de3ff", "#15303b"          # личные награды: голубой (трофеи команды - золотые)
NATIONAL = "#ffa25c"                            # трофеи сборной

STYLE = f"""
* {{ font-family: "Segoe UI", "Noto Sans", "DejaVu Sans", Arial, sans-serif; font-size: 14px; color: {TEXT}; }}
QMainWindow, QWidget#page, QDialog {{ background: {BG}; }}
QLabel#title {{ font-size: 28px; font-weight: 700; }}
QLabel#h2 {{ font-size: 18px; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#gold {{ color: {GOLD}; font-weight: 600; }}
QFrame#panel, QFrame#card {{ background: {PANEL}; border: 1px solid #2a3442; border-radius: 12px; }}
QFrame#card:hover {{ border: 1px solid {ACCENT}; }}
QPushButton {{ background: {PANEL2}; border: 1px solid #334053; border-radius: 8px; padding: 8px 16px; }}
QPushButton:hover {{ background: #2c3747; border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #5d6878; background: #1b222c; border-color: #263140; }}
QPushButton#primary {{ background: {ACCENT}; color: #08120c; border: none; font-weight: 700; padding: 10px 22px; }}
QPushButton#primary:hover {{ background: #4be08a; }}
QPushButton#primary:disabled {{ background: #27452f; color: #6c8f78; }}
QPushButton#choose {{ background: {ACCENT}; color: #08120c; border: 2px solid #7af0aa; border-radius: 10px; font-weight: 800;
                      font-size: 16px; padding: 10px 24px; }}
QPushButton#choose:hover {{ background: #5cf09a; border-color: #ffffff; }}
QPushButton#choose:pressed {{ background: #27a85c; }}
QPushButton#danger {{ background: #3a2226; border-color: #6b3037; }}
QPushButton#danger:hover {{ background: #4a2a2f; border-color: {RED}; }}
QPushButton[posbtn="true"] {{ min-width: 120px; min-height: 62px; padding: 4px 6px; font-size: 13px; }}
QPushButton[posbtn="true"]:checked {{ background: {ACCENT}; color: #08120c; border-color: {ACCENT}; font-weight: 700; }}
QLineEdit {{ background: {PANEL2}; border: 1px solid #334053; border-radius: 8px; padding: 8px 10px; }}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QSpinBox {{ background: {PANEL2}; border: 1px solid #334053; border-radius: 8px; padding: 6px 10px; color: {TEXT}; }}
QSpinBox:focus {{ border-color: {ACCENT}; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; background: #2c3747; border: none; }}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ background: #3a465a; }}
QListWidget {{ background: {PANEL}; border: 1px solid #2a3442; border-radius: 10px; padding: 4px; outline: 0; }}
QListWidget::item {{ padding: 7px 10px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {ACCENT}; color: #08120c; }}
QListWidget::item:hover:!selected {{ background: {PANEL2}; }}
QComboBox {{ background: {PANEL2}; border: 1px solid #334053; border-radius: 8px; padding: 6px 10px; min-width: 110px; }}
QComboBox QAbstractItemView {{ background: {PANEL}; selection-background-color: {ACCENT}; selection-color: #08120c; }}
QRadioButton {{ spacing: 8px; padding: 4px; }}
QRadioButton::indicator {{ width: 14px; height: 14px; border-radius: 9px; border: 2px solid #5a6b83; background: {PANEL2}; }}
QRadioButton::indicator:checked {{ background: {ACCENT}; border: 2px solid {ACCENT}; }}
QWidget#scrollhost {{ background: transparent; }}
QScrollArea > QWidget#qt_scrollarea_viewport {{ background: transparent; }}
QListWidget {{ outline: 0; }}
QTableWidget {{ background: {PANEL}; alternate-background-color: #1e2631; gridline-color: #2a3442; border: 1px solid #2a3442; border-radius: 10px; }}
QHeaderView::section {{ background: {PANEL2}; color: {MUTED}; padding: 6px; border: none; border-bottom: 1px solid #334053; font-weight: 600; }}
QTableWidget::item:selected {{ background: #2c3747; color: {TEXT}; }}
QTextBrowser {{ background: {PANEL}; border: 1px solid #2a3442; border-radius: 10px; padding: 10px; }}
QTabWidget::pane {{ border: 1px solid #2a3442; border-radius: 10px; background: {PANEL}; top: -1px; }}
QTabBar::tab {{ background: {PANEL2}; padding: 9px 18px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px; color: {MUTED}; }}
QTabBar::tab:selected {{ background: {PANEL}; color: {TEXT}; font-weight: 600; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 12px; }}
QScrollBar::handle:vertical {{ background: #3a465a; border-radius: 6px; min-height: 30px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; }}
QScrollBar::handle:horizontal {{ background: #3a465a; border-radius: 6px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""
