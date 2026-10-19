"""Дневник сезона в версии для компьютера: окно дневников всех сезонов, настройки нейросети и фоновое написание (QThread).

Факты сезона и задание для нейросети - game/story.py, запросы к Gemini и Claude - game/llm.py (то же, что на сайте).
"""
import html, re
from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QTextBrowser, QLabel, QLineEdit, QCheckBox,
                               QMessageBox, QApplication, QFormLayout)
from .. import story, llm, saves
from ..i18n import tr
from . import theme

def diary_html(text):
    """Текст дневника -> HTML для QTextBrowser: абзацы, **даты** жирным."""
    out = []
    for block in re.split(r"\n\s*\n", (text or "").strip()):
        b = html.escape(block.strip())
        b = re.sub(r"\*\*(.+?)\*\*", r"<b style='color:#6b3a12'>\1</b>", b)
        b = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<i>\1</i>", b)
        if b.startswith("#"):
            out.append(f"<h3 style='color:#6b3a12'>{b.lstrip('# ')}</h3>")
        elif b:
            out.append("<p style='margin:0 0 12px 0'>" + b.replace("\n", "<br>") + "</p>")
    return ("<body style='background:#f4ecd8; color:#2b2418; font-family:Georgia,\"Times New Roman\",serif; font-size:17px; line-height:160%;'>"
            + "".join(out) + "</body>")

class _Worker(QThread):
    """Один запрос к нейросети вне основного потока (окно не зависает)."""
    finished_ok = Signal(str, str, str, str)          # key, text, provider, model
    failed = Signal(str, str)                          # key, error

    def __init__(self, key, job):
        super().__init__()
        self.key, self.job = key, job

    def run(self):
        try:
            text, provider, model = llm.write(self.job["system"], self.job["user"])
            self.finished_ok.emit(self.key, text, provider, model)
        except Exception as e:
            self.failed.emit(self.key, str(e))

class DiaryManager(QObject):
    """Очередь дневников одной карьеры: «Написать» в окне и автодневник после сезона. Ответ сохраняется в сезон и в сохранение."""
    changed = Signal(str)                              # ключ сезона, у которого поменялось состояние
    error = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.career, self.data = None, None
        self.queue, self.writing, self.worker = [], set(), None

    def attach(self, career, data):
        if career is not self.career:
            self.queue = []
        self.career, self.data = career, data

    def request(self, keys, auto=False):
        """Поставить сезоны в очередь (auto - только если нейросеть настроена и автодневник включён)."""
        if self.career is None or (auto and not (llm.ready() and llm.current()["auto"])):
            return
        for k in keys:
            if k not in self.queue and k not in self.writing:
                self.queue.append(k)
        self._next()

    def _next(self):
        if self.worker is not None or not self.queue or self.career is None:
            return
        key = self.queue.pop(0)
        job = story.prompt(self.career, self.data, key)
        self.writing.add(key)
        self.worker = _Worker(key, job)
        self.worker.career = self.career
        self.worker.finished_ok.connect(self._ok)
        self.worker.failed.connect(self._fail)
        self.worker.start()
        self.changed.emit(key)

    def _done(self):
        w, self.worker = self.worker, None
        if w is not None:
            w.wait()
        return w

    def _ok(self, key, text, provider, model):
        w = self._done()
        self.writing.discard(key)
        if w is not None and w.career is self.career:              # за это время могли открыть другую карьеру
            story.save_answer(self.career, key, text, provider, model)
            saves.save(self.career)
        self.changed.emit(key)
        self._next()

    def _fail(self, key, err):
        self._done()
        self.writing.discard(key)
        self.queue = []
        self.changed.emit(key)
        self.error.emit(key, err)

class DiaryDialog(QDialog):
    """Дневники всех сезонов карьеры (игрок и тренер): выбор сезона, текст, «Написать» / «Написать заново», настройки."""
    def __init__(self, manager, start_key=None, parent=None):
        super().__init__(parent)
        self.m, c, d = manager, manager.career, manager.data
        self.setWindowTitle(tr("web.diary")); self.resize(900, 760)
        v = QVBoxLayout(self)
        top = QHBoxLayout(); top.addWidget(QLabel(tr("ai.season")))
        self.box = QComboBox()
        for k in story.keys(c):
            kind, _, s = story.record(c, k)
            label = f"{s['season']} · {s['club_name']}" + (f" · {tr('ai.coach_tag')}" if kind == "c" else "")
            self.box.addItem(label, k)
        top.addWidget(self.box, 1); v.addLayout(top)
        self.status = QLabel(); self.status.setObjectName("muted"); self.status.setWordWrap(True); v.addWidget(self.status)
        self.view = QTextBrowser(); self.view.setOpenLinks(False); v.addWidget(self.view, 1)
        row = QHBoxLayout()
        s = QPushButton(tr("web.settings")); s.clicked.connect(self._settings); row.addWidget(s); row.addStretch()
        self.write = QPushButton(); self.write.setObjectName("primary"); self.write.clicked.connect(self._write); row.addWidget(self.write)
        close = QPushButton(tr("ai.close")); close.clicked.connect(self.accept); row.addWidget(close)
        v.addLayout(row)
        self.error = ""
        keys = story.keys(c)
        k = start_key if start_key in keys else (keys[-1] if keys else None)
        if k is not None:
            self.box.setCurrentIndex(keys.index(k))
        self.box.currentIndexChanged.connect(lambda _: self._show(clear_error=True))
        self.m.changed.connect(self._changed)
        self.m.error.connect(self._error)
        self._show()

    def key(self):
        return self.box.currentData()

    def _changed(self, key):
        if key == self.key():
            self._show()

    def _error(self, key, err):
        if key == self.key():
            self.error = err; self._show()

    def _show(self, clear_error=False):
        if clear_error:
            self.error = ""
        key = self.key()
        if key is None:
            return
        _, _, s = story.record(self.m.career, key)
        st = s.get("story")
        if key in self.m.writing or key in self.m.queue:
            self.view.setHtml(diary_html(tr("web.diary_writing")))
            self.status.setText(""); self.write.setEnabled(False); self.write.setText(tr("web.diary_write"))
            return
        self.write.setEnabled(True)
        if st:
            self.view.setHtml(diary_html(st["text"]))
            self.write.setText(tr("web.diary_rewrite"))
            info = tr("web.diary_by", p=st.get("provider", ""), m=st.get("model", "")) if st.get("model") else ""
        else:
            self.view.setHtml(diary_html(tr("web.diary_none") + "\n\n" + tr("web.diary_hint")))
            self.write.setText(tr("web.diary_write"))
            info = ""
        self.status.setText((f"<span style='color:{theme.RED}'>{html.escape(tr('web.diary_failed'))}: {html.escape(self.error)}</span>"
                             if self.error else html.escape(info)))

    def _write(self):
        if not llm.ready():
            self._settings()
            if not llm.ready():
                return
        self.error = ""
        self.m.request([self.key()])
        self._show()

    def _settings(self):
        SettingsDialog(self).exec()

class SettingsDialog(QDialog):
    """Настройки нейросети: сервис, ключ, модель, автодневник (сохраняются в settings.json)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("web.ai_title")); self.resize(560, 300)
        self.ai = llm.settings()
        v = QVBoxLayout(self)
        f = QFormLayout(); v.addLayout(f)
        self.prov = QComboBox()
        for k, name in (("off", tr("web.ai_off")), ("gemini", "Google Gemini"), ("claude", "Anthropic Claude")):
            self.prov.addItem(name, k)
        self.prov.setCurrentIndex(max(0, self.prov.findData(self.ai["provider"])))
        f.addRow(tr("web.ai_provider"), self.prov)
        self.keyed = QLineEdit(); self.keyed.setEchoMode(QLineEdit.Password); f.addRow(tr("web.ai_key"), self.keyed)
        self.model = QComboBox(); self.model.setEditable(True); f.addRow(tr("web.ai_model"), self.model)
        lm = QPushButton(tr("web.ai_models_btn")); lm.clicked.connect(self._load_models); f.addRow("", lm)
        self.auto = QCheckBox(tr("web.ai_auto")); self.auto.setChecked(self.ai.get("auto", True)); f.addRow("", self.auto)
        hint = QLabel(tr("ai.key_hint"))
        hint.setWordWrap(True); hint.setObjectName("muted"); v.addWidget(hint)
        row = QHBoxLayout(); row.addStretch()
        save = QPushButton(tr("web.ai_save")); save.setObjectName("primary"); save.clicked.connect(self._save); row.addWidget(save)
        cancel = QPushButton(tr("retire.cancel")); cancel.clicked.connect(self.reject); row.addWidget(cancel)
        v.addLayout(row)
        self._shown = self.prov.currentData()
        self._fill()
        self.prov.currentIndexChanged.connect(self._switch)

    def _take(self):
        p = self._shown
        if p in ("gemini", "claude"):
            self.ai["key"][p] = self.keyed.text().strip()
            self.ai["model"][p] = self.model.currentText().strip()

    def _fill(self):
        p = self.prov.currentData()
        off = p not in ("gemini", "claude")
        self.keyed.setEnabled(not off); self.model.setEnabled(not off)
        self.keyed.setText(self.ai["key"].get(p, "") if not off else "")
        self.model.clear()
        if not off:
            self.model.setEditText(self.ai["model"].get(p) or llm.DEFAULT_MODEL[p])

    def _switch(self):
        self._take(); self._shown = self.prov.currentData(); self._fill()

    def _load_models(self):
        p, key = self.prov.currentData(), self.keyed.text().strip()
        if p not in ("gemini", "claude") or not key:
            QMessageBox.information(self, tr("web.ai_title"), tr("web.ai_need")); return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            names = llm.models(p, key)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, tr("web.ai_title"), str(e)); return
        QApplication.restoreOverrideCursor()
        cur = self.model.currentText()
        self.model.clear(); self.model.addItems(names); self.model.setEditText(cur or (names[0] if names else ""))
        QMessageBox.information(self, tr("web.ai_title"), tr("ai.models_loaded", n=len(names)))

    def _save(self):
        self._take()
        self.ai["provider"] = self.prov.currentData()
        self.ai["auto"] = self.auto.isChecked()
        llm.save_settings(self.ai)
        self.accept()
