// Нейросети для дневника сезона: Google Gemini (REST) и Anthropic Claude (официальный SDK, грузится с CDN при первом вызове).
// Настройки и ключи хранятся только в localStorage этого браузера и уходят только выбранному сервису.
"use strict";
const AI_KEY = "fcs.ai";
const AI_DEFAULT_MODEL = { gemini: "gemini-2.5-flash", claude: "claude-opus-5-5" };
const ANTHROPIC_SDK = "https://cdn.jsdelivr.net/npm/@anthropic-ai/sdk@0.131.0/+esm";
const GEMINI_API = "https://generativelanguage.googleapis.com/v1beta";
// модели Claude, которым можно включить серверный запасной вариант на случай отказа (см. документацию Anthropic)
const CLAUDE_FALLBACK = ["claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"];

function aiLoad() {
  try { return Object.assign({ provider: "gemini", model: {}, key: {} }, JSON.parse(localStorage.getItem(AI_KEY) || "{}")); }
  catch (e) { return { provider: "gemini", model: {}, key: {} }; }
}
function aiSave(s) {
  try { localStorage.setItem(AI_KEY, JSON.stringify(s)); return true; } catch (e) { return false; }
}
function aiCurrent() {
  const s = aiLoad(), p = s.provider;
  return { provider: p, key: (s.key || {})[p] || "", model: (s.model || {})[p] || AI_DEFAULT_MODEL[p] || "" };
}

// перегрузка сервиса (429/5xx) обычно временная: повторяем запрос с паузами 4, 10 и 20 секунд
const RETRY_STATUS = [429, 500, 502, 503, 504, 529];
const RETRY_DELAYS = [4000, 10000, 20000];
class BusyError extends Error {}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function withRetry(call, onRetry) {
  for (let i = 0; ; i++) {
    try { return await call(); }
    catch (e) {
      const busy = e instanceof BusyError || RETRY_STATUS.includes(e.status);
      if (!busy || i >= RETRY_DELAYS.length) {
        if (busy) { const be = new Error("__busy__"); be.detail = e.message; throw be; }
        throw e;
      }
      if (onRetry) onRetry(i + 1, RETRY_DELAYS.length);
      await sleep(RETRY_DELAYS[i]);
    }
  }
}

// --- Gemini
async function geminiWrite(key, model, system, user) {
  const r = await fetch(`${GEMINI_API}/models/${encodeURIComponent(model)}:generateContent`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": key },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: system }] },
      contents: [{ role: "user", parts: [{ text: user }] }],
      generationConfig: { temperature: 1.0, maxOutputTokens: 32768 },
    }),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    const msg = (data.error && data.error.message) || `HTTP ${r.status}`;
    if (RETRY_STATUS.includes(r.status)) throw new BusyError(msg);
    throw new Error(msg);
  }
  const cand = (data.candidates || [])[0];
  if (!cand) throw new Error((data.promptFeedback && "blocked: " + data.promptFeedback.blockReason) || "empty response");
  const text = ((cand.content && cand.content.parts) || []).filter((p) => !p.thought).map((p) => p.text || "").join("");
  if (!text.trim()) throw new Error("finishReason: " + (cand.finishReason || "?"));
  return text;
}
async function geminiModels(key) {
  const r = await fetch(`${GEMINI_API}/models?pageSize=1000`, { headers: { "x-goog-api-key": key } });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((data.error && data.error.message) || `HTTP ${r.status}`);
  return (data.models || []).filter((m) => (m.supportedGenerationMethods || []).includes("generateContent"))
    .map((m) => m.name.replace(/^models\//, ""))
    .filter((n) => n.startsWith("gemini") && !/(image|tts|audio|live|embedding|vision)/.test(n));
}

// --- Claude: официальный SDK @anthropic-ai/sdk в браузере (ключ пользователя, поэтому dangerouslyAllowBrowser)
let anthropicMod = null;
async function claudeClient(key) {
  if (!anthropicMod) anthropicMod = await import(ANTHROPIC_SDK);
  const Anthropic = anthropicMod.default || anthropicMod.Anthropic;
  return new Anthropic({ apiKey: key, dangerouslyAllowBrowser: true });
}
async function claudeWrite(key, model, system, user) {
  const client = await claudeClient(key);
  const params = { model, max_tokens: 32000, system, messages: [{ role: "user", content: user }] };
  let stream;
  if (CLAUDE_FALLBACK.includes(model)) {
    stream = client.beta.messages.stream({ ...params, betas: ["server-side-fallback-2026-07-01"], fallbacks: "default" });
  } else {
    stream = client.messages.stream(params);
  }
  const msg = await stream.finalMessage();
  if (msg.stop_reason === "refusal") throw new Error("refusal" + (msg.stop_details && msg.stop_details.category ? ": " + msg.stop_details.category : ""));
  const text = msg.content.filter((b) => b.type === "text").map((b) => b.text).join("");
  if (!text.trim()) throw new Error("stop_reason: " + msg.stop_reason);
  return text;
}
async function claudeModels(key) {
  const client = await claudeClient(key);
  const out = [];
  for await (const m of client.models.list()) out.push(m.id);
  return out;
}

async function aiWrite(system, user, onRetry) {
  const ai = aiCurrent();
  if (ai.provider === "off" || !ai.key) throw new Error("__need__");
  const call = () => ai.provider === "claude" ? claudeWrite(ai.key, ai.model, system, user) : geminiWrite(ai.key, ai.model, system, user);
  const text = await withRetry(call, onRetry);
  return { text, provider: ai.provider === "claude" ? "Claude" : "Gemini", model: ai.model };
}

// текст ошибки для игрока: перегрузку и отсутствие настроек - своими словами, остальное как есть
function aiErrorText(e) {
  if (e.message === "__need__") return app.tr("web.ai_need");
  if (e.message === "__busy__") return app.tr("web.ai_busy") + (e.detail ? ` (${e.detail})` : "");
  return String(e.message || e);
}
async function aiModels(provider, key) {
  return provider === "claude" ? claudeModels(key) : geminiModels(key);
}
