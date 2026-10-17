"""Игрок: генерация, характеристики в стиле FIFA, рост и спад."""
import math
from .positions import WEIGHTS, PROFILE, TYPICAL_HEIGHT, attr_names, height_offsets, style_mult

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _g(a, center=16.0, width=2.0):
    return 1.0 / (1.0 + math.exp(-(a - center) / width))

def f_norm(age, center=16.0, width=2.0):
    """Доля пути к потолку, пройденная к возрасту (0 в 15 лет, 1 в 28).
    center - возраст, когда игрок раскрывается быстрее всего: 16-17 у вундеркиндов, 22-24 у «поздних»."""
    lo, hi = _g(15, center, width), _g(28, center, width)
    return clamp((_g(age, center, width) - lo) / (hi - lo), 0.0, 1.0)

def sample_bloom(rng):
    """Когда игрок раскрывается: (центр, ширина) кривой роста. Не зависит ни от потенциала, ни от стартового рейтинга."""
    u = rng.random()
    if u < 0.30:
        return rng.uniform(16.0, 17.5), rng.uniform(1.6, 2.2)       # ранний талант
    if u < 0.70:
        return rng.uniform(17.5, 20.0), rng.uniform(1.8, 2.4)       # обычный путь
    if u < 0.92:
        return rng.uniform(20.0, 22.5), rng.uniform(2.0, 2.6)       # раскрывается к 23-25
    return rng.uniform(22.5, 24.5), rng.uniform(2.0, 2.6)           # поздний расцвет, 25-28

DECLINE = {29: 0.0, 30: 0.15, 31: 0.45, 32: 0.8, 33: 1.1, 34: 1.5, 35: 1.9, 36: 2.3, 37: 2.7, 38: 3.1, 39: 3.5, 40: 3.9}

def sample_pot(rng):
    u = rng.random()
    if u < 0.004:
        return rng.uniform(96, 99)
    if u < 0.030:
        return rng.uniform(89, 96)
    if u < 0.120:
        return rng.uniform(83, 89)
    if u < 0.600:
        return clamp(rng.gauss(77, 3.0), 68, 83)
    return clamp(rng.gauss(72, 3.5), 60, 79)

class Player:
    def __init__(self, name, nat, pos, age, core, c0, pot, offsets, pot_bonus=0.0, peak_ovr=0, bloom=(16.0, 2.0), foot="R", height=None):
        self.name, self.nat, self.pos, self.age = name, nat, pos, age
        self.core, self.c0, self.pot, self.offsets = core, c0, pot, list(offsets)
        self.pot_bonus = pot_bonus
        self.bloom = tuple(bloom)
        self.foot = foot                                     # R - правая, L - левая, B - обе
        self.height = height or TYPICAL_HEIGHT[pos]          # см
        self.peak_ovr = peak_ovr or self.ovr()

    def style(self):
        """(множитель голов, множитель передач) от ведущей ноги и роста."""
        return style_mult(self.pos, self.foot, self.height)

    # ---------- создание ----------
    @classmethod
    def generate(cls, name, nat, pos, rng, age=15, foot="R", height=None):
        height = height or TYPICAL_HEIGHT[pos]
        pot = sample_pot(rng)
        c0 = clamp(rng.gauss(42.0, 3.2), 34, 51)             # стартовый уровень не связан с потенциалом
        bloom = sample_bloom(rng)
        w = WEIGHTS[pos]
        hoff = height_offsets(pos, height)                   # рост меняет профиль, а не общий рейтинг (сдвиг нормируется ниже)
        offs = [PROFILE[pos][i] + hoff[i] + rng.gauss(0, 3.5) for i in range(6)]
        key = max(range(6), key=lambda i: w[i])
        offs[key] += rng.uniform(1, 5)                      # «фирменная» сильная сторона
        shift = sum(w[i] * offs[i] for i in range(6))
        offs = [o - shift for o in offs]                    # OVR == ядру при нулевых возрастных поправках
        return cls(name, nat, pos, age, c0, c0, round(pot, 1), offs, bloom=bloom, foot=foot, height=height)

    # ---------- характеристики ----------
    def age_mod(self, i):
        a = self.age
        gk = self.pos == "GK"
        m = 0.0
        if a < 18 and not gk and i == 5:
            m -= (18 - a) * 3.0
        if a < 18 and i == (4 if gk else 0):
            m -= (18 - a) * 0.6
        if i == (4 if gk else 0):
            m -= max(0, a - 28) * 1.4
        if not gk and i == 5:
            m -= max(0, a - 31) * 1.0
        if not gk and i == 3:
            m -= max(0, a - 31) * 0.6
        if gk and i == 3:
            m -= max(0, a - 33) * 0.8
        return m

    def attrs(self):
        return [int(round(clamp(self.core + self.offsets[i] + self.age_mod(i), 25, 99))) for i in range(6)]

    def ovr_float(self):
        w = WEIGHTS[self.pos]
        return sum(w[i] * clamp(self.core + self.offsets[i] + self.age_mod(i), 25, 99) for i in range(6))

    def ovr(self):
        return int(round(clamp(self.ovr_float(), 20, 99)))

    def attr_dict(self):
        return dict(zip(attr_names(self.pos), self.attrs()))

    # ---------- рост и спад за прошедший сезон ----------
    @property
    def peak(self):
        return min(99.0, self.pot + self.pot_bonus)

    def target(self, age):
        return self.c0 + (self.peak - self.c0) * f_norm(age, *self.bloom)

    def ovr_at(self, age):
        """OVR с текущим ядром, но в другом возрасте (возрастные поправки к скорости, физике)."""
        a = self.age
        self.age = age
        try:
            return self.ovr_float()
        finally:
            self.age = a

    def grow(self, rng, share, quality, perf, injury_hit=0.0, rating=None, selection=None):
        """Вызывается в конце сезона (игроку self.age лет). Возраст не меняет.
        perf - результативность относительно ожидаемой (0 = как ожидалось), rating - средняя оценка за сезон,
        selection - доля игрового времени без учёта травм (сколько тренер готов был давать играть)."""
        a = self.age
        nxt = a + 1
        before = self.ovr_float()
        # раскрыться можно в любом возрасте до 30: сильные сезоны при регулярной игре поднимают потолок
        if perf > 0.2 and share > 0.5 and a <= 29:
            self.pot_bonus = min(9.0, self.pot_bonus + (1.0 if a >= 20 else 0.8) * perf)
        elif perf < -0.4 and share > 0.5:
            self.pot_bonus = max(-3.0, self.pot_bonus - 0.4)
        # сезоны на скамейке в 18-25 лет тормозят развитие: потолок снижается (до -0.8 за сезон, всего до -4).
        # Травма скамейкой не считается; вернуть потерянное можно сильными сезонами (бонус выше).
        sel = share if selection is None else selection
        if 18 <= a <= 25 and sel < 0.25:
            self.pot_bonus = max(min(self.pot_bonus, -4.0), self.pot_bonus - 0.8 * (0.25 - sel) / 0.25)
        if nxt <= 30:
            plan = self.target(nxt) - self.target(a)
            mult = (0.70 + 0.45 * share) * (0.95 + 0.12 * quality)
            delta = plan * mult + 0.30 * (self.target(a) - self.core) + rng.gauss(0, 0.9)
            if a < 30:
                delta += (0.7 if a < 27 else 0.4) * max(0.0, perf)
        else:
            delta = -DECLINE.get(nxt, 4.0) + rng.gauss(0, 0.5)
            if share > 0.6 and perf > 0.3:
                delta += 0.4                                   # возрастной игрок в форме стареет медленнее
        self.core = clamp(self.core + delta, 20, 99)
        # хороший сезон (статистика выше ожидаемой или высокая оценка) не роняет рейтинг: максимум держится,
        # а после 31 года спад заметно мягче
        good = share >= 0.45 and (perf >= 0.15 or (rating or 0) >= 7.2)
        if good:
            after = self.ovr_at(nxt)
            allowed = 0.0 if nxt <= 31 else DECLINE.get(nxt, 4.0) * clamp(0.85 - 0.4 * max(perf, 0.0), 0.35, 0.85)
            if after < before - allowed:
                self.core = clamp(self.core + (before - allowed - after), 20, 99)
        self.core = clamp(self.core - injury_hit, 20, 99)
        self.peak_ovr = max(self.peak_ovr, self.ovr())
        return delta

    # ---------- сериализация ----------
    def to_dict(self):
        return {"name": self.name, "nat": self.nat, "pos": self.pos, "age": self.age, "core": self.core, "c0": self.c0,
                "pot": self.pot, "offsets": self.offsets, "pot_bonus": self.pot_bonus, "peak_ovr": self.peak_ovr, "bloom": list(self.bloom),
                "foot": self.foot, "height": self.height}

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["nat"], d["pos"], d["age"], d["core"], d["c0"], d["pot"], d["offsets"], d["pot_bonus"], d["peak_ovr"],
                   d.get("bloom", (16.0, 2.0)), d.get("foot", "R"), d.get("height"))
