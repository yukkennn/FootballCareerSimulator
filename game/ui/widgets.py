"""Самодельные виджеты: карточка игрока, график рейтинга, карточки клубов, эмблемы."""
from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QPolygonF
from PySide6.QtWidgets import QWidget, QFrame, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QSizePolicy
from ..positions import attr_names
from ..text import stars_text
from ..i18n import tr
from . import theme

_cache = {}
SKIP = {"fc", "afc", "cf", "fk", "sk", "sc", "ac", "as", "cd", "ud", "rcd", "sv", "vfl", "vfb", "ss", "us", "ca", "sd"}

def club_pixmap(club, size=56):
    key = (club["id"], size)
    if key in _cache:
        return _cache[key]
    pm = None
    if club.get("logo") and club["logo"].exists():
        src = QPixmap(str(club["logo"]))
        if not src.isNull():
            pm = src.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    if pm is None:
        pm = QPixmap(size, size); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        h = sum(ord(c) * (i + 3) for i, c in enumerate(club["name"])) % 360
        p.setBrush(QColor.fromHsv(h, 140, 150)); p.setPen(QPen(QColor(255, 255, 255, 70), 2))
        p.drawEllipse(2, 2, size - 4, size - 4)
        words = [w for w in club["name"].replace(".", " ").split() if w.lower() not in SKIP and not w.isdigit()] or club["name"].split()
        ini = (words[0][0] + (words[1][0] if len(words) > 1 else "")).upper()
        f = QFont(); f.setBold(True); f.setPixelSize(int(size * 0.36)); p.setFont(f); p.setPen(QColor("white"))
        p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, ini); p.end()
    _cache[key] = pm
    return pm

def logo_label(club, size=56):
    l = QLabel(); l.setPixmap(club_pixmap(club, size)); l.setFixedSize(size, size); l.setAlignment(Qt.AlignCenter)
    l.setStyleSheet("background: transparent; border: none;")
    return l

def tier_color(ovr):
    if ovr >= 90: return QColor("#7de3ff")
    if ovr >= 75: return QColor(theme.GOLD)
    if ovr >= 65: return QColor("#c3ccd9")
    return QColor("#cd8b4e")

class PlayerCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = None; self.sub = ""
        self.setFixedSize(300, 340)

    def set_player(self, player, sub=""):
        self.player, self.sub = player, sub; self.update()

    def paintEvent(self, _):
        if not self.player:
            return
        p, pl = QPainter(self), self.player
        p.setRenderHint(QPainter.Antialiasing)
        col = tier_color(pl.ovr())
        r = QRectF(2, 2, self.width() - 4, self.height() - 4)
        g = QLinearGradient(r.topLeft(), r.bottomRight()); g.setColorAt(0, QColor("#2d3748")); g.setColorAt(1, QColor("#161b24"))
        p.setBrush(QBrush(g)); p.setPen(QPen(col, 2.5)); p.drawRoundedRect(r, 18, 18)
        f = QFont(); f.setPixelSize(54); f.setBold(True); p.setFont(f); p.setPen(col)
        p.drawText(QRectF(20, 14, 120, 62), Qt.AlignLeft | Qt.AlignVCenter, str(pl.ovr()))
        f.setPixelSize(20); p.setFont(f); p.setPen(QColor(theme.TEXT))
        p.drawText(QRectF(20, 76, 120, 26), Qt.AlignLeft | Qt.AlignVCenter, pl.pos)
        f.setPixelSize(15); f.setBold(False); p.setFont(f); p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(150, 22, 130, 26), Qt.AlignRight | Qt.AlignVCenter, self.sub)
        f.setPixelSize(13); p.setFont(f)
        p.drawText(QRectF(110, 78, 170, 22), Qt.AlignRight | Qt.AlignVCenter,
                   f"{pl.height} {tr('start.cm')} · {tr('foot_short.' + pl.foot)}")
        f.setPixelSize(20); f.setBold(True); p.setFont(f); p.setPen(QColor(theme.TEXT))
        p.drawText(QRectF(14, 112, self.width() - 28, 28), Qt.AlignCenter, pl.name)
        p.setPen(QPen(QColor(255, 255, 255, 40), 1)); p.drawLine(20, 148, self.width() - 20, 148)
        names, vals = attr_names(pl.pos), pl.attrs()
        f.setPixelSize(15); f.setBold(True); p.setFont(f)
        for i, (n, v) in enumerate(zip(names, vals)):
            y = 160 + i * 28
            p.setPen(QColor(theme.MUTED)); p.drawText(QRectF(24, y, 50, 22), Qt.AlignLeft | Qt.AlignVCenter, n)
            p.setPen(Qt.NoPen); p.setBrush(QColor(255, 255, 255, 24)); p.drawRoundedRect(QRectF(80, y + 6, 150, 10), 5, 5)
            bc = QColor(theme.ACCENT) if v >= 75 else QColor("#e0b83a") if v >= 55 else QColor("#d9673a")
            p.setBrush(bc); p.drawRoundedRect(QRectF(80, y + 6, 150 * v / 99.0, 10), 5, 5)
            p.setPen(QColor(theme.TEXT)); p.drawText(QRectF(236, y, 40, 22), Qt.AlignRight | Qt.AlignVCenter, str(v))

class OvrChart(QWidget):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.pts, self.title = [], title
        self.setMinimumSize(300, 170)

    def set_points(self, pts, title=None):
        self.pts = pts
        if title is not None: self.title = title
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setBrush(QColor(theme.PANEL)); p.setPen(QPen(QColor("#2a3442"), 1)); p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), 12, 12)
        f = QFont(); f.setPixelSize(13); f.setBold(True); p.setFont(f); p.setPen(QColor(theme.MUTED))
        p.drawText(QRectF(14, 8, w - 28, 20), Qt.AlignLeft, self.title)
        l, t, r, b = 38, 36, w - 16, h - 26
        f.setBold(False); f.setPixelSize(11); p.setFont(f)
        for v in (30, 50, 70, 90):
            y = b - (v - 25) / 75.0 * (b - t)
            p.setPen(QPen(QColor(255, 255, 255, 22), 1)); p.drawLine(int(l), int(y), int(r), int(y))
            p.setPen(QColor(theme.MUTED)); p.drawText(QRectF(2, y - 8, l - 6, 16), Qt.AlignRight | Qt.AlignVCenter, str(v))
        for a in (15, 20, 25, 30, 35, 40):
            x = l + (a - 15) / 25.0 * (r - l)
            p.setPen(QColor(theme.MUTED)); p.drawText(QRectF(x - 14, b + 4, 28, 14), Qt.AlignCenter, str(a))
        if len(self.pts) < 1:
            return
        poly = QPolygonF([QPointF(l + (a - 15) / 25.0 * (r - l), b - (min(max(o, 25), 100) - 25) / 75.0 * (b - t)) for a, o in self.pts])
        p.setPen(QPen(QColor(theme.ACCENT), 2.5)); p.setBrush(Qt.NoBrush); p.drawPolyline(poly)
        p.setPen(Qt.NoPen); p.setBrush(QColor(theme.ACCENT))
        for pt in poly: p.drawEllipse(pt, 3, 3)
        mx = max(self.pts, key=lambda x: x[1]); i = self.pts.index(mx)
        p.setBrush(QColor(theme.GOLD)); p.drawEllipse(poly[i], 5, 5)
        p.setPen(QColor(theme.GOLD)); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(poly[i].x() - 20, poly[i].y() - 22, 40, 16), Qt.AlignCenter, str(mx[1]))

class ClubCard(QFrame):
    """Карточка клуба: эмблема, название, лига, звёзды, дополнительные строки и кнопка."""
    def __init__(self, club, subtitle, stars, lines, button_text, on_click, tag=None, parent=None, tag_home=False):
        super().__init__(parent)
        self.setObjectName("card")
        lay = QHBoxLayout(self); lay.setContentsMargins(16, 12, 16, 12); lay.setSpacing(16)
        lay.addWidget(logo_label(club, 64))
        mid = QVBoxLayout(); mid.setSpacing(2)
        name = QLabel(club["name"]); name.setObjectName("h2"); name.setStyleSheet("border:none;background:transparent;")
        sub = QLabel(subtitle); sub.setObjectName("muted"); sub.setStyleSheet("border:none;background:transparent;")
        st = QLabel(stars_text(stars)); st.setObjectName("gold"); st.setStyleSheet("border:none;background:transparent;font-size:16px;")
        mid.addWidget(name); mid.addWidget(sub); mid.addWidget(st)
        if tag:
            t = QLabel(tag); t.setWordWrap(True)
            t.setStyleSheet(f"color:{theme.ACCENT if tag_home else theme.GOLD};border:none;background:transparent;font-size:12px;"); mid.addWidget(t)
        lay.addLayout(mid, 1)
        right = QVBoxLayout(); right.setSpacing(3)
        for ln in lines:
            l = QLabel(ln); l.setAlignment(Qt.AlignRight); l.setStyleSheet("border:none;background:transparent;"); right.addWidget(l)
        lay.addLayout(right)
        btn = QPushButton(button_text); btn.setObjectName("choose"); btn.setMinimumWidth(150); btn.setMinimumHeight(44)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(on_click); lay.addWidget(btn, 0, Qt.AlignVCenter)
        self.button = btn
