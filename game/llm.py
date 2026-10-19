"""Нейросети для дневника сезона в версии для компьютера: Google Gemini (REST) и Anthropic Claude (официальный SDK `anthropic`).

Настройки (сервис, модель, ключи, автодневник) хранятся в settings.json папки пользователя (~/.football_career_sim), как язык игры.
В веб-версии то же самое делает web/llm.js.
"""
import json, urllib.error, urllib.request
from . import i18n

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = {"gemini": "gemini-2.5-flash", "claude": "claude-opus-5-5"}
# модели Claude, которым включается серверный запасной вариант на случай отказа
CLAUDE_FALLBACK = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}

class AIError(Exception):
    pass

# ---------------------------------------------------------------- настройки
def settings():
    s = i18n.load_settings().get("ai") or {}
    return {"provider": s.get("provider", "gemini"), "model": dict(s.get("model") or {}), "key": dict(s.get("key") or {}),
            "auto": s.get("auto", True)}

def save_settings(ai):
    s = i18n.load_settings()
    s["ai"] = ai
    i18n.SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")

def current():
    s = settings()
    p = s["provider"]
    return {"provider": p, "key": s["key"].get(p, ""), "model": s["model"].get(p) or DEFAULT_MODEL.get(p, ""), "auto": s["auto"]}

def ready():
    c = current()
    return c["provider"] in ("gemini", "claude") and bool(c["key"])

# ---------------------------------------------------------------- Gemini
def _gemini(path, key, body=None, timeout=300):
    req = urllib.request.Request(f"{GEMINI_API}/{path}", data=json.dumps(body).encode("utf-8") if body is not None else None,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key}, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8")).get("error", {}).get("message")
        except Exception:
            msg = None
        raise AIError(msg or f"HTTP {e.code}")
    except urllib.error.URLError as e:
        raise AIError(str(e.reason))

def gemini_write(key, model, system, user):
    data = _gemini(f"models/{model}:generateContent", key, {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 1.0, "maxOutputTokens": 32768}})
    cands = data.get("candidates") or []
    if not cands:
        raise AIError("blocked: " + str((data.get("promptFeedback") or {}).get("blockReason", "empty response")))
    text = "".join(p.get("text", "") for p in (cands[0].get("content") or {}).get("parts", []) if not p.get("thought"))
    if not text.strip():
        raise AIError("finishReason: " + str(cands[0].get("finishReason")))
    return text

def gemini_models(key):
    data = _gemini("models?pageSize=1000", key)
    names = [m["name"].split("/", 1)[-1] for m in data.get("models", []) if "generateContent" in (m.get("supportedGenerationMethods") or [])]
    return [n for n in names if n.startswith("gemini") and not any(x in n for x in ("image", "tts", "audio", "live", "embedding", "vision"))]

# ---------------------------------------------------------------- Claude (официальный SDK)
def _claude_client(key):
    try:
        import anthropic
    except ImportError:
        raise AIError(i18n.tr("ai.no_sdk"))
    return anthropic, anthropic.Anthropic(api_key=key)

def claude_write(key, model, system, user):
    anthropic, client = _claude_client(key)
    params = dict(model=model, max_tokens=32000, system=system, messages=[{"role": "user", "content": user}])
    try:
        if model in CLAUDE_FALLBACK:
            with client.beta.messages.stream(**params, betas=["server-side-fallback-2026-07-01"], fallbacks="default") as stream:
                msg = stream.get_final_message()
        else:
            with client.messages.stream(**params) as stream:
                msg = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise AIError("invalid x-api-key")
    except anthropic.APIStatusError as e:
        raise AIError(f"{e.status_code}: {e.message}")
    except anthropic.APIConnectionError as e:
        raise AIError(str(e))
    if msg.stop_reason == "refusal":
        cat = getattr(getattr(msg, "stop_details", None), "category", None)
        raise AIError("refusal" + (f": {cat}" if cat else ""))
    text = "".join(b.text for b in msg.content if b.type == "text")
    if not text.strip():
        raise AIError(f"stop_reason: {msg.stop_reason}")
    return text

def claude_models(key):
    anthropic, client = _claude_client(key)
    try:
        return [m.id for m in client.models.list()]
    except anthropic.APIStatusError as e:
        raise AIError(f"{e.status_code}: {e.message}")

# ---------------------------------------------------------------- общий вход
def write(system, user):
    """-> (текст, название сервиса, модель). Без настроек - AIError с текстом про настройки."""
    c = current()
    if c["provider"] not in ("gemini", "claude") or not c["key"]:
        raise AIError(i18n.tr("web.ai_need"))
    if c["provider"] == "claude":
        return claude_write(c["key"], c["model"], system, user), "Claude", c["model"]
    return gemini_write(c["key"], c["model"], system, user), "Gemini", c["model"]

def models(provider, key):
    return claude_models(key) if provider == "claude" else gemini_models(key)
