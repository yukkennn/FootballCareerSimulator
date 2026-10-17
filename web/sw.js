// Service worker: игра работает без интернета. Оболочка и game.zip кэшируются при установке, Python (Pyodide с CDN) и эмблемы - при первом обращении.
const VERSION = "__BUILD__";
const CACHE = "fcs-" + VERSION;
const SHELL = ["./", "index.html", "style.css?v=" + VERSION, "app.js?v=" + VERSION, "game.zip?v=" + VERSION, "manifest.webmanifest",
               "icon-192.png", "icon-512.png", "icon-180.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  // старые версии игры удаляем; Python и эмблемы лежат в отдельном кэше и переживают обновления
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
  e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((r) => {
    if (runtime && (r.ok || r.type === "opaque")) {     // pyodide.js подключён тегом <script>: ответ «непрозрачный», но его тоже храним const copy = r.clone(); caches.open("runtime").then((c) => c.put(req, copy)); }
    return r;
  })));
});
