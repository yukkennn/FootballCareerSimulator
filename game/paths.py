"""Пути приложения (работает и из исходников, и из PyInstaller-сборки)."""
import sys
from pathlib import Path

def _root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent

ROOT = _root()
DATA = ROOT / "data"
DB_PATH = DATA / "football.db"
LOGOS = ROOT / "assets" / "logos"

def user_dir() -> Path:
    p = Path.home() / ".football_career_sim"
    p.mkdir(parents=True, exist_ok=True)
    return p

def saves_dir() -> Path:
    p = user_dir() / "saves"
    p.mkdir(parents=True, exist_ok=True)
    return p

SETTINGS_FILE = user_dir() / "settings.json"
