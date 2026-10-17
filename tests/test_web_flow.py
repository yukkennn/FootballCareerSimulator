"""Прогон веб-интерфейса без браузера: все экраны режима игрока, сохранения, экспорт и импорт.
Запуск: python tests/test_web_flow.py (домашняя папка подменяется на временную, настоящие сохранения не трогаются)."""
import json, os, sys, tempfile
from pathlib import Path

home = tempfile.mkdtemp()
os.environ["HOME"] = os.environ["USERPROFILE"] = home
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game.web.app import WebApp

def act(app, name, arg="", form=None):
    out = json.loads(app.act(name, arg, json.dumps(form or {})))
    assert "Error" not in (out.get("toast") or ""), out.get("toast")
    return out

def run(lang):
    app = WebApp()
    act(app, "lang", lang)
    assert "natlist" in app.render()
    out = act(app, "start")
    assert out.get("toast"), "без страны старт не должен проходить"
    form = {"first": "Иван", "last": "Тестов", "nat": "BRA", "pos": "LW", "foot": "R", "height": "180"}
    app._take_form(json.dumps(form))
    p = json.loads(app.partial("phys", json.dumps(form)))
    assert p["set"].get("height"), p
    json.loads(app.partial("random_name", json.dumps(form)))
    act(app, "start", "", form)
    assert app.view == "summary"
    act(app, "reroll"); act(app, "to_academy")
    act(app, "academy", app.career.academy_ids[0])
    n = 0
    while app.career.status != "retired" and n < 40:
        act(app, "play")
        assert app.view == "report"
        act(app, "after_report")
        if app.view == "offers":
            act(app, "accept", "0" if app.career.offers else "stay")
        n += 1
        if n == 3:
            act(app, "season", "0|career"); assert app.view == "season"; act(app, "back", "career")
    if app.career.status != "retired":
        act(app, "retire"); act(app, "retire_yes")
    elif app.modal:                                   # 40 лет: окно «завершить / стать тренером»
        assert "retire_coach" in app.render()
        act(app, "retire_yes")
    assert app.view == "end", app.view
    for tab in ("summary", "seasons", "comps", "transfers", "honours", "chronicle"):
        act(app, "tab", tab)
    assert act(app, "export_text")["download"]["text"]
    act(app, "show_load")
    sid = app.career.id
    exp = act(app, "export_save", sid)["download"]["text"]
    act(app, "ask_delete", sid); act(app, "delete_save", sid)
    out = act(app, "import_save", exp); assert sid in out["html"], "импорт не появился в списке"
    act(app, "open_save", sid); assert app.view == "end"
    bad = json.loads(app.act("import_save", "{не json", "{}")); assert bad["toast"]
    print(lang, "ok:", len(app.career.seasons), "сезонов,", n, "периодов")

def run_coach(lang, seasons=6):
    """Тренерская карьера: досрочное завершение -> тренер, все вкладки, сделки в окнах, середина сезона, итоги, загрузка."""
    app = WebApp()
    act(app, "lang", lang)
    form = {"first": "", "last": "", "nat": "ESP", "pos": "CM", "foot": "B", "height": "178"}
    app._take_form(json.dumps(form)); act(app, "start", "", form)
    act(app, "to_academy"); act(app, "academy", app.career.academy_ids[0])
    for _ in range(4):
        act(app, "play"); act(app, "after_report")
        act(app, "accept", "stay" if app.career.can_stay else "0")
    act(app, "retire"); assert "retire_coach" in app.render()
    act(app, "retire_coach"); assert app.view == "coach_offers", app.view
    act(app, "coach_accept", "0"); assert app.view == "coach"
    for tab in ("squad", "lineup", "seasons"):
        act(app, "ctab", tab)
    act(app, "c_formation", "4-4-2"); act(app, "c_rotation", "some")
    act(app, "lineup_auto", "0")
    pid = app.career.coach["lineup"]["4-4-2"][1]
    act(app, "lineup_set", f"0|{pid}")
    act(app, "lineup_auto", "1")
    json.loads(app.partial("tactic", json.dumps({"tactic": "press"})))
    for k in range(seasons):
        if app.view == "coach_offers":
            act(app, "coach_accept", "stay" if app.career.coach.get("can_stay") else "0")
        assert app.view == "coach", app.view
        act(app, "coach_play", "", {"tactic": "attack"})
        assert app.view == "transfer", app.view
        win = app.career.coach["window"]
        for tab in ("market", "squad", "lineup", "loans", "scouts"):
            act(app, "tw_tab", tab)
        act(app, "tw_tab", "market")
        for ln in ("DEF", ""):
            act(app, "tw_filter", ln)
        for key in ("ovr", "pot", "effect", "price", "age", ""):
            act(app, "tw_sort", key)
        cheap = [i for i, cd in enumerate(win["cands"]) if not cd["done"] and not cd.get("refuse") and cd["price"] <= app.career.coach["budget"]]
        if cheap and k % 2 == 0:
            act(app, "tw_buy", str(cheap[0]))
        if k == 1:
            from game import squad as squad_mod
            weakest = min(squad_mod.squad(app.career), key=lambda p: p["ovr"])
            act(app, "tw_sell", weakest["id"])
        if win.get("scout_market") and not (app.career.coach.get("scouts")):
            act(app, "tw_hire", "0")
        act(app, "tw_formation", "4-3-3")
        act(app, "tw_done")
        assert app.view == "mid", app.view
        if not app.ctx["mid"]["fired"]:
            act(app, "m_formation", "4-2-3-1"); act(app, "m_rotation", "none")
            act(app, "mid_winter", "", {"tactic": "defense"}); assert app.view == "transfer"
            act(app, "tw_done"); assert app.view == "mid"
        act(app, "mid_done", "", {"tactic": "balanced"})
        assert app.view == "creport", app.view
        act(app, "creport_done")
        if app.view == "end":
            break
    sid = app.career.id
    if app.view != "end":
        act(app, "show_load"); act(app, "open_save", sid); assert app.view in ("coach", "coach_offers"), app.view
        act(app, "coach_retire"); act(app, "coach_retire_yes")
    assert app.view == "end"
    for tab in ("coach", "coach_seasons", "summary"):
        act(app, "tab", tab)
    assert tr_has(act(app, "export_text")["download"]["text"])
    print(lang, "coach ok:", len(app.career.coach["seasons"]), "сезонов тренером")

def tr_has(text):
    return bool(text) and ("Тренер" in text or "Coach" in text or "coach" in text)

for lang in ("ru", "en"):
    run(lang)
    run_coach(lang)
