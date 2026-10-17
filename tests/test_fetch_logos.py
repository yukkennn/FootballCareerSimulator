"""Тест загрузчика эмблем на ЛОКАЛЬНОМ тестовом сервере (настоящий TheSportsDB из песочницы недоступен)."""
import http.server, io, json, shutil, sqlite3, subprocess, sys, tempfile, threading
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent

png = io.BytesIO(); Image.new("RGBA", (200, 260), (200, 30, 30, 255)).save(png, "PNG"); PNG = png.getvalue()
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/badge.png"):
            self.send_response(200); self.send_header("Content-Type", "image/png"); self.end_headers(); self.wfile.write(PNG); return
        q = self.path.split("t=")[-1].replace("%20", " ")
        port = self.server.server_address[1]
        base = f"http://127.0.0.1:{port}/badge.png"
        teams = {"Barnsley": [{"strTeam": "Barnsley", "strCountry": "England", "strSport": "Soccer", "strBadge": base}],
                 "Kairat Almaty": [{"strTeam": "FC Kairat", "strCountry": "Kazakhstan", "strSport": "Soccer", "strTeamBadge": base + "?kairat"}],
                 "Accrington Stanley": [{"strTeam": "Accrington Stanley", "strCountry": "Germany", "strSport": "Soccer", "strBadge": base}]}  # неверная страна
        body = json.dumps({"teams": teams.get(q)}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)
srv = http.server.HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()

tmp = Path(tempfile.mkdtemp()); shutil.copytree(ROOT, tmp / "p", ignore=shutil.ignore_patterns("football.db-journal", "__pycache__", ".venv", ".logo_cache"))
db = tmp / "p/data/football.db"
TEST_CLUBS = ("eng-barnsley", "kaz-kairat-almaty", "eng-accrington-stanley")
c0 = sqlite3.connect(db)                                  # в копии базы у тестовых клубов эмблем нет (в настоящей они уже докачаны)
c0.executemany("UPDATE clubs SET logo_path=NULL WHERE club_id=?", [(x,) for x in TEST_CLUBS]); c0.commit(); c0.close()
for x in TEST_CLUBS:
    (tmp / f"p/assets/logos/{x}.png").unlink(missing_ok=True)
r = subprocess.run([sys.executable, tmp / "p/tools/fetch_logos.py", db, "--api", f"http://127.0.0.1:{srv.server_address[1]}", "--sleep", "0",
                    "--sources", "tsdb", "--cache", str(tmp / "cache")], capture_output=True, text=True)
print(r.stdout, r.stderr[-500:])
assert r.returncode == 0
c = sqlite3.connect(db)
assert c.execute("select logo_path from clubs where club_id='eng-barnsley'").fetchone()[0], "Barnsley получил эмблему (strBadge)"
assert c.execute("select logo_path from clubs where club_id='kaz-kairat-almaty'").fetchone()[0], "Kairat получил эмблему (поле strTeamBadge, «FC Kairat» вложено в «Kairat Almaty»)"
assert c.execute("select logo_path from clubs where club_id='eng-accrington-stanley'").fetchone()[0] is None, "неверная страна отвергнута"
assert Image.open(tmp / "p/assets/logos/eng-barnsley.png").height == 96
print("fetch_logos: OK")
c.close()
shutil.rmtree(tmp, ignore_errors=True)
