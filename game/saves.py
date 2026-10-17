"""Сохранение и загрузка карьер (JSON в ~/.football_career_sim/saves)."""
import json, time
from .paths import saves_dir
from .career import Career

def save(career):
    path = saves_dir() / f"{career.id}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(career.to_dict(), ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return path

def list_saves():
    out = []
    for p in sorted(saves_dir().glob("*.json"), key=lambda p: -p.stat().st_mtime):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            coach = d.get("coach") or {}
            out.append({"path": p, "id": d["id"], "name": d["name"], "age": d["player"]["age"], "status": d["status"],
                        "club": coach.get("club") if d["status"].startswith("coach") else d.get("club_id"), "mtime": p.stat().st_mtime})
        except (OSError, ValueError, KeyError):
            continue
    return out

def load(path, data):
    return Career.from_dict(json.loads(path.read_text(encoding="utf-8")), data)

def delete(path):
    try:
        path.unlink()
    except OSError:
        pass
