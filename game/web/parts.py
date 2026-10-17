"""Общие куски HTML: эмблема, карточка игрока, график рейтинга, карточка клуба, кнопки."""
from html import escape
from ..paths import ROOT
from ..positions import attr_names
from ..text import stars_text
from ..i18n import tr
from ..ui import theme

SKIP = {"fc", "afc", "cf", "fk", "sk", "sc", "ac", "as", "cd", "ud", "rcd", "sv", "vfl", "vfb", "ss", "us", "ca", "sd"}

def esc(v):
    return escape(str(v))

def btn(text, act, arg="", kind="", extra=""):
    """Кнопка: нажатие отправляет в Python действие act с аргументом arg (см. app.js)."""
    cls = "btn" + (f" btn-{kind}" if kind else "")
    return f'<button class="{cls}" data-act="{esc(act)}" data-arg="{esc(arg)}" {extra}>{text}</button>'

def logo(club, size=48):
    """Эмблема клуба; если картинки нет или она не загрузилась - круг с инициалами (как в десктопной версии)."""
    name = club["name"]
    hue = sum(ord(c) * (i + 3) for i, c in enumerate(name)) % 360
    words = [w for w in name.replace(".", " ").split() if w.lower() not in SKIP and not w.isdigit()] or name.split()
    ini = (words[0][0] + (words[1][0] if len(words) > 1 else "")).upper()
    img = ""
    if club.get("logo"):
        try:
            src = club["logo"].relative_to(ROOT).as_posix()
        except ValueError:
            src = ""
        if src:
            img = f'<img src="{esc(src)}" alt="" loading="lazy" onerror="this.remove()">'
    return f'<span class="logo" style="--s:{size}px;--h:{hue}">{esc(ini)}{img}</span>'

def tier_color(ovr):
    if ovr >= 90: return "#7de3ff"
    if ovr >= 75: return theme.GOLD
    if ovr >= 65: return "#c3ccd9"
    return "#cd8b4e"

def player_card(pl, sub=""):
    ovr = pl.ovr()
    rows = []
    for n, v in zip(attr_names(pl.pos), pl.attrs()):
        bc = theme.ACCENT if v >= 75 else "#e0b83a" if v >= 55 else "#d9673a"
        rows.append(f'<div class="attr"><span class="an">{esc(n)}</span><span class="bar"><i style="width:{v / 99 * 100:.0f}%;background:{bc}"></i></span>'
                    f'<b>{v}</b></div>')
    return (f'<div class="pcard" style="--tc:{tier_color(ovr)}">'
            f'<div class="pc-top"><div><div class="pc-ovr">{ovr}</div><div class="pc-pos">{esc(pl.pos)}</div></div>'
            f'<div class="pc-sub">{esc(sub)}<br><span>{pl.height} {tr("start.cm")} · {esc(tr("foot_short." + pl.foot))}</span></div></div>'
            f'<div class="pc-name">{esc(pl.name)}</div><div class="pc-attrs">{"".join(rows)}</div></div>')

def ovr_chart(pts, title):
    """График рейтинга по возрасту (SVG), лучшая точка отмечена золотом."""
    W, H = 340, 170
    l, t, r, b = 30, 14, W - 10, H - 22
    X = lambda a: l + (a - 15) / 25.0 * (r - l)
    Y = lambda o: b - (min(max(o, 25), 100) - 25) / 75.0 * (b - t)
    g = []
    for v in (30, 50, 70, 90):
        g.append(f'<line x1="{l}" y1="{Y(v):.1f}" x2="{r}" y2="{Y(v):.1f}" class="grid"/><text x="{l - 5}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    for a in (15, 20, 25, 30, 35, 40):
        g.append(f'<text x="{X(a):.1f}" y="{H - 6}" text-anchor="middle">{a}</text>')
    if pts:
        xy = [(X(a), Y(o)) for a, o in pts]
        g.append('<polyline class="line" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in xy) + '"/>')
        g += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="dot"/>' for x, y in xy]
        i = max(range(len(pts)), key=lambda k: pts[k][1])
        x, y = xy[i]
        g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="best"/><text x="{x:.1f}" y="{y - 9:.1f}" text-anchor="middle" class="bestt">{pts[i][1]}</text>')
    return (f'<div class="panel chart"><div class="muted small b">{esc(title)}</div>'
            f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}">{"".join(g)}</svg></div>')

def club_card(club, sub, stars, lines, button_text=None, act=None, arg="", tag=None, tag_home=False):
    tag_html = f'<div class="tag{" home" if tag_home else ""}">{esc(tag)}</div>' if tag else ""
    lines_html = "".join(f"<div>{esc(x)}</div>" for x in lines if x)
    button = btn(button_text, act, arg, "choose") if button_text else ""
    return (f'<div class="ccard"><div class="cc-head">{logo(club, 52)}<div class="cc-main"><div class="h2">{esc(club["name"])}</div>'
            f'<div class="muted small">{esc(sub)}</div><div class="gold">{stars_text(stars)}</div>{tag_html}</div></div>'
            f'<div class="cc-lines">{lines_html}</div>{button}</div>')

def kv(rows):
    """Таблица «название — значение» (строки: (ключ, значение[, цвет]))."""
    out = []
    for row in rows:
        k, v, color = row if len(row) == 3 else (*row, None)
        st = f' style="color:{color}"' if color else ""
        out.append(f'<div class="kv"><span class="muted">{esc(k)}</span><b{st}>{esc(v)}</b></div>')
    return '<div class="panel kvs">' + "".join(out) + "</div>"
