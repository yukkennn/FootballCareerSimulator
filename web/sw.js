// Service worker: игра работает без интернета.
// При первом заходе сразу сохраняются оболочка, game.zip и Python (Pyodide с CDN): страница начинает загружать Python раньше,
// чем service worker успевает включиться, поэтому ждать «первого обращения» нельзя - иначе без сети игра не откроется.
// Эмблемы клубов сохраняются при первом показе (без сети вместо ещё не виденных эмблем рисуются инициалы).
const VERSION = "__BUILD__";
const CACHE = "fcs-" + VERSION;                          // файлы игры: новая версия - новый кэш
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/";
const PY_CACHE = "pyodide-v0.27.7";                      // Python не меняется между версиями игры - качается один раз
const SHELL = ["./", "index.html", "style.css?v=" + VERSION, "app.js?v=" + VERSION, "llm.js?v=" + VERSION, "game.zip?v=" + VERSION, "manifest.webmanifest",
               "icon-192.png", "icon-512.png", "icon-180.png"];
const PY_FILES = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json",
                  "sqlite3-1.0.0-cp312-cp312-pyodide_2024_0_wasm32.whl"].map((f) => PYODIDE + f);

async function cachePython() {
  const c = await caches.open(PY_CACHE);
  await Promise.all(PY_FILES.map(async (url) => {
    if (!(await c.match(url))) await c.add(new Request(url, { mode: "cors" }));
  }));
}

self.addEventListener("install", (e) => {
  e.waitUntil(Promise.all([caches.open(CACHE).then((c) => c.addAll(SHELL)), cachePython()]).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  // старые версии игры удаляем; Python и эмблемы лежат в отдельных кэшах и переживают обновления
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith("fcs-") && k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (req.mode === "navigate") {                       // страница: сначала сеть (чтобы получить новую версию), без сети - из кэша
    e.respondWith(fetch(req).then((r) => { const copy = r.clone(); caches.open(CACHE).then((c) => c.put("index.html", copy)); return r; })
      .catch(() => caches.match("index.html", { cacheName: CACHE })));
    return;
  }
  const runtime = url.hostname === "cdn.jsdelivr.net" || url.pathname.includes("/assets/logos/");
  e.respondWith(caches.match(req, { ignoreVary: true }).then((hit) => hit || fetch(req).then((r) => {
    if (runtime && (r.ok || r.type === "opaque")) { const copy = r.clone(); caches.open("runtime").then((c) => c.put(req, copy)); }
    return r;
  })));
});
