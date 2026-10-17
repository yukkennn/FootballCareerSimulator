// Оболочка веб-версии: загружает Python (Pyodide) и игру, передаёт нажатия в game/web/app.py и показывает готовый HTML.
"use strict";
const HOME = "/home/pyodide";
const USER_DIR = HOME + "/.football_career_sim";   // сюда game/paths.py пишет сохранения и настройки; папка хранится в IndexedDB браузера
const APP_DIR = HOME + "/fcs";
const root = document.getElementById("app");
let py, app, FS;

function splash(text) {
  const el = document.getElementById("splash-text");
  if (el) el.textContent = text;
}

function toast(text) {
  const t = document.getElementById("toast");
  t.textContent = text; t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, 4000);
}

// дать браузеру нарисовать индикатор загрузки до долгого расчёта (запасной таймер - для вкладки в фоне, где кадры не рисуются)
const nextFrame = () => new Promise(r => { requestAnimationFrame(() => setTimeout(r, 0)); setTimeout(r, 100); });

function syncfs(populate) {
  return new Promise((res) => FS.syncfs(populate, (err) => { if (err) console.warn("syncfs", err); res(); }));
}

// значения всех полей текущего экрана: {имя: значение}
function collectForm() {
  const f = {};
  root.querySelectorAll("input[name]").forEach((el) => {
    if (el.type === "radio") { if (el.checked) f[el.name] = el.value; else if (!(el.name in f)) f[el.name] = ""; }
    else if (el.type !== "file") f[el.name] = el.value;
  });
  return f;
}

async function act(name, arg, busy) {
  const keep = window.scrollY;
  if (busy) { document.getElementById("busy").hidden = false; await nextFrame(); }
  try {
    const res = JSON.parse(app.act(name, arg || "", JSON.stringify(collectForm())));
    root.innerHTML = res.html;
    window.scrollTo(0, res.scroll === "top" ? 0 : keep);
    if (res.toast) toast(res.toast);
    if (res.download) download(res.download);
  } catch (e) {
    console.error(e); toast(String(e));
  } finally {
    document.getElementById("busy").hidden = true;
  }
  syncfs(false);
}

function partial(name) {
  const res = JSON.parse(app.partial(name, JSON.stringify(collectForm())));
  for (const [sel, html] of Object.entries(res.html || {})) {
    const el = root.querySelector(sel); if (el) el.innerHTML = html;
  }
  for (const [k, v] of Object.entries(res.set || {})) {
    const el = root.querySelector(`input[name="${k}"]`); if (el) el.value = v;
  }
}

async function download(d) {
  const file = new File([d.text], d.name, { type: d.mime });
  // на телефоне удобнее системное меню «Поделиться» (сохранить в «Файлы», отправить в мессенджер), на компьютере - обычное скачивание
  if (navigator.canShare && navigator.canShare({ files: [file] }) && matchMedia("(pointer: coarse)").matches) {
    try { await navigator.share({ files: [file], title: d.name }); return; }
    catch (e) { if (e.name === "AbortError") return; }
  }
  const a = document.createElement("a");
  a.href = URL.createObjectURL(file); a.download = d.name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 10000);
}

// --- события
root.addEventListener("click", (e) => {
  const p = e.target.closest("button[data-partial]");
  if (p) { e.preventDefault(); partial(p.dataset.partial); return; }
  const b = e.target.closest("[data-act]");
  if (b) { e.preventDefault(); act(b.dataset.act, b.dataset.arg, b.hasAttribute("data-busy")); }
});
root.addEventListener("change", (e) => {
  const el = e.target;
  if (el.matches("input[data-partial]")) partial(el.dataset.partial);
  // списки (схема, ротация, игрок на позиции) и галочки: действие с выбранным значением
  if (el.dataset.onchange) act(el.dataset.onchange, el.type === "checkbox" ? (el.checked ? "1" : "0") : el.value);
  if (el.matches("input[data-import]") && el.files[0]) {
    el.files[0].text().then((text) => act("import_save", text));
  }
});
root.addEventListener("input", (e) => {
  const el = e.target;
  if (el.dataset.live) { const t = root.querySelector(el.dataset.live); if (t) t.textContent = el.value; }
  if (el.dataset.filter) {
    const q = el.value.trim().toLowerCase();
    root.querySelectorAll(el.dataset.filter + " [data-search]").forEach((it) => { it.hidden = !!q && !it.dataset.search.includes(q); });
  }
});

// --- запуск
async function main() {
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    navigator.serviceWorker.register("sw.js").catch((e) => console.warn("sw", e));
  }
  if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
  splash("Python…");
  py = await loadPyodide({ indexURL: window.PYODIDE_URL });
  FS = py.FS;
  splash("SQLite…");
  await py.loadPackage("sqlite3");
  splash("Game…");
  const zip = await fetch("game.zip?v=" + window.BUILD).then((r) => { if (!r.ok) throw new Error("game.zip " + r.status); return r.arrayBuffer(); });
  py.unpackArchive(zip, "zip", { extractDir: APP_DIR });
  FS.mkdirTree(USER_DIR);
  FS.mount(FS.filesystems.IDBFS, {}, USER_DIR);
  await syncfs(true);
  py.runPython(`import sys; sys.path.insert(0, "${APP_DIR}")\nfrom game.web.app import WebApp\nweb_app = WebApp()`);
  app = py.globals.get("web_app");
  document.documentElement.lang = py.runPython("from game import i18n; i18n.LANG");
  root.innerHTML = app.render();
}

main().catch((e) => {
  console.error(e);
  splash("Ошибка загрузки / Load error: " + e.message);
});
