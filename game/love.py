"""Личная жизнь героя для дневника сезона: игра заранее «планирует» романтическую линию каждой карьеры, а нейросеть только
пишет её по этому плану. Иначе нейросеть почти всегда даёт герою девушку в первом же сезоне. Пара в итоге есть у каждого,
различается только возраст, когда он её встречает, и путь к ней.

План строится из id карьеры (детерминированно: та же карьера - тот же план, переписанный дневник его не меняет):
у кого-то первая любовь в 17, у кого-то в 30; бывают невзаимная симпатия, короткий роман, тяжёлые отношения, расставания,
свадьба, дети, развод, долгое одиночество. У каждой девушки свой характер (типаж); имена придумывает нейросеть.
"""
import random
from . import i18n

def T(ru, en):
    return ru if i18n.LANG == "ru" else en

# типажи девушек: (русский, английский)
TYPES = [
    ("добрая, спокойная и домашняя: заботливая, верит в него, не любит шумные компании",
     "kind, calm and homely: caring, believes in him, dislikes loud crowds"),
    ("готка: чёрная одежда, мрачный юмор, любит старый рок и кладбищенские прогулки, к футболу равнодушна",
     "a goth: black clothes, dark humour, loves old rock and walks in old cemeteries, indifferent to football"),
    ("резкая и грубоватая: говорит в лицо, что думает, вспыльчивая, но честная",
     "sharp and blunt: says what she thinks to his face, quick-tempered but honest"),
    ("амбициозная карьеристка: юрист или менеджер, вечно занята, ценит независимость",
     "an ambitious career woman: a lawyer or manager, always busy, values independence"),
    ("творческая натура: художница или музыкант, живёт настроением, непредсказуемая",
     "an artist type: a painter or musician, lives by her moods, unpredictable"),
    ("спортсменка: сама тренируется (лёгкая атлетика, теннис или волейбол), соревновательная",
     "an athlete herself (track, tennis or volleyball), competitive"),
    ("тусовщица и светская львица: обожает вечеринки, соцсети и внимание",
     "a party girl and socialite: loves parties, social media and attention"),
    ("тихая и застенчивая книжница: работает в библиотеке или учится, краснеет от комплиментов",
     "a quiet, shy bookworm: works in a library or studies, blushes at compliments"),
    ("весёлая хохотушка-оптимистка: шутит без остановки, со всеми дружит",
     "a cheerful optimist: jokes non-stop, friends with everyone"),
    ("холодная и загадочная: мало говорит о себе, держит дистанцию",
     "cold and mysterious: says little about herself, keeps her distance"),
    ("медсестра или врач: практичная, видела всякое, не впечатляется славой",
     "a nurse or doctor: practical, has seen it all, unimpressed by fame"),
    ("бунтарка с татуировками: мотоцикл, протесты, презирает богатых футболистов",
     "a tattooed rebel: motorbike, protests, despises rich footballers"),
    ("подруга детства из родного города: знает его ещё до футбола",
     "a childhood friend from his home town who knew him before football"),
    ("ревнивая и требовательная: хочет всё его время, устраивает сцены",
     "jealous and demanding: wants all his time, makes scenes"),
    ("иностранка: другая страна, другой язык, всё время что-то теряется в переводе",
     "a foreigner: another country, another language, things keep getting lost in translation"),
    ("журналистка: познакомились на интервью, любопытная и колкая",
     "a journalist: they met at an interview, curious and sharp-tongued"),
]
BREAKUP = [
    ("она устала от его вечных разъездов и сборов", "she got tired of his constant travelling and training camps"),
    ("его переход в другой клуб и переезд: отношения на расстоянии не выдержали", "his transfer and move: the long-distance relationship did not last"),
    ("ревность и ссоры из-за фанаток и журналистов", "jealousy and rows over female fans and journalists"),
    ("они хотели от жизни совсем разного", "they wanted completely different things from life"),
    ("она встретила другого", "she met someone else"),
    ("он с головой ушёл в футбол и перестал её замечать", "he buried himself in football and stopped noticing her"),
    ("её семья была против", "her family was against it"),
    ("всё просто тихо угасло", "it all just quietly faded"),
    ("тяжёлая травма и его плохое настроение разрушили отношения", "a bad injury and his dark moods wrecked the relationship"),
]

def _first_love_age(rng):
    """Возраст первых серьёзных отношений: у всех по-разному, от юности до тридцати с лишним."""
    return rng.choices([rng.randint(17, 18), rng.randint(19, 22), rng.randint(23, 26), rng.randint(27, 31), rng.randint(32, 38)],
                       weights=[12, 28, 28, 20, 12])[0]

def plan(career_id):
    """Главы личной жизни: [{kind, start, end, type, outcome, reason, married, kids, divorce}] по возрасту героя (15..75)."""
    rng = random.Random(f"{career_id}-love")
    ch = []
    if rng.random() < 0.45:                                       # невзаимная симпатия в юности
        a = rng.randint(15, 18)
        ch.append({"kind": "crush", "start": a, "end": a, "type": rng.randrange(len(TYPES))})
    age = _first_love_age(rng)
    used = set()
    settle = rng.randint(27, 36)                                  # к этому возрасту герой встречает «ту самую» (у всех по-разному)
    divorced = False
    while True:
        t = rng.choice([i for i in range(len(TYPES)) if i not in used] or list(range(len(TYPES))))
        used.add(t)
        r = 1.0 if age >= settle else rng.random()               # пора: дальше только серьёзные отношения
        if r < 0.2:                                               # короткий роман на один сезон
            ch.append({"kind": "fling", "start": age, "end": age, "type": t, "reason": rng.randrange(len(BREAKUP))})
            age += 1 + rng.randint(0, 3)
            continue
        if r < 0.35:                                              # тяжёлые отношения, которые плохо кончаются
            n = rng.randint(1, 3)
            ch.append({"kind": "toxic", "start": age, "end": age + n - 1, "type": 13 if 13 not in used else t,
                       "reason": rng.randrange(len(BREAKUP))})
            age += n + rng.randint(1, 4)
            continue
        n = rng.randint(2, 7)                                     # серьёзные отношения
        c = {"kind": "serious", "start": age, "end": age + n - 1, "type": t}
        if age >= settle or (age + n - 1 >= 22 and rng.random() < 0.45):  # свадьба, дети, иногда развод
            c["married"] = max(age + rng.randint(1, 3), 22)
            c["end"] = 99
            if rng.random() < 0.65:
                c["kids"] = c["married"] + rng.randint(1, 4)
            if not divorced and rng.random() < 0.2:              # развод бывает не больше одного раза
                divorced = True
                c["divorce"] = c["married"] + rng.randint(3, 12)
                c["end"] = c["divorce"]
                c["reason"] = rng.randrange(len(BREAKUP))
            ch.append(c)
            if "divorce" not in c:
                break
            age = c["divorce"] + 1 + rng.randint(1, 5)
            continue
        c["reason"] = rng.randrange(len(BREAKUP))
        ch.append(c)
        age += n + rng.randint(0, 5)
    return ch

def season_line(career_id, age, partner_names=None):
    """Указание нейросети на сезон: что происходит в личной жизни героя в этом возрасте."""
    chs = plan(career_id)
    cur = next((c for c in chs if c["start"] <= age <= c["end"]), None)
    prev = [c for c in chs if c["end"] < age]
    last = prev[-1] if prev else None
    ty = lambda c: TYPES[c["type"]][0 if i18n.LANG == "ru" else 1]
    br = lambda c: BREAKUP[c.get("reason", 0)][0 if i18n.LANG == "ru" else 1]
    if cur is None:
        if last and age - last["end"] <= 1 and last["kind"] != "crush":
            return T("Герой одинок: недавно расстался и ещё переживает. Новых отношений в этом сезоне НЕ начинай (можно случайное свидание без продолжения).",
                     "The hero is single: he broke up recently and is still getting over it. Do NOT start a new relationship this season (a one-off date is fine).")
        if not any(c["kind"] != "crush" for c in prev):
            return T("Герой одинок, серьёзных отношений у него ещё не было. Девушку в этом сезоне НЕ заводи: футбол, друзья, семья, "
                     "можно мысли о любви, неловкий флирт или зависть к влюблённым товарищам - но без отношений.",
                     "The hero is single and has never had a serious relationship yet. Do NOT give him a girlfriend this season: football, friends, family, "
                     "maybe thoughts of love, awkward flirting or envy of teammates in love - but no relationship.")
        return T("Герой одинок в этом сезоне. Новых отношений НЕ начинай: можно одиночество, свидания без продолжения, мысли о прошлом.",
                 "The hero is single this season. Do NOT start a new relationship: loneliness, dates that go nowhere, thoughts about the past are fine.")
    k = cur["kind"]
    if k == "crush":
        return T(f"В этом сезоне герой тайно влюбляется, но взаимности нет: она не отвечает или встречается с другим. Её характер: {ty(cur)}. "
                 "Придумай ей имя. Отношений НЕ будет - это история о неразделённой симпатии.",
                 f"This season the hero secretly falls for a girl, but it is not mutual: she ignores him or dates someone else. Her character: {ty(cur)}. "
                 "Invent her name. There will be NO relationship - this is a story of unrequited feelings.")
    if k == "fling":
        return T(f"В этом сезоне у героя короткий роман, который в этом же сезоне и заканчивается. Её характер: {ty(cur)}. Придумай ей имя. "
                 f"Почему расстались: {br(cur)}.",
                 f"This season the hero has a short affair that ends within the same season. Her character: {ty(cur)}. Invent her name. "
                 f"Why it ended: {br(cur)}.")
    start = cur["start"] == age
    if k == "toxic":
        if start:
            s = T(f"В этом сезоне герой начинает отношения, которые окажутся тяжёлыми. Её характер: {ty(cur)}. Придумай ей имя и историю знакомства.",
                  f"This season the hero starts a relationship that will turn out to be hard. Her character: {ty(cur)}. Invent her name and how they met.")
        else:
            s = T(f"Тяжёлые отношения с той же девушкой продолжаются (её характер: {ty(cur)}): ссоры, примирения, ему всё труднее.",
                  f"The hard relationship with the same girl goes on (her character: {ty(cur)}): rows, make-ups, it gets harder for him.")
        if cur["end"] == age:
            s += T(f" В этом сезоне они болезненно расстаются. Причина: {br(cur)}.", f" This season they break up painfully. Reason: {br(cur)}.")
        return s
    # серьёзные отношения
    if start:
        s = T(f"В этом сезоне герой знакомится с девушкой, с которой начнутся серьёзные отношения. Её характер: {ty(cur)}. "
              "Придумай ей имя и живую историю знакомства.",
              f"This season the hero meets a girl and a serious relationship begins. Her character: {ty(cur)}. Invent her name and a vivid story of how they met.")
    else:
        stage = T("встречаются", "dating")
        if cur.get("married") and age > cur["married"]:
            stage = T("женаты", "married")
            if cur.get("kids") and age > cur["kids"]:
                stage = T("женаты, у них есть ребёнок (или дети)", "married, they have a child (or children)")
        elif age - cur["start"] >= 2:
            stage = T("давно вместе, живут вместе", "together for a while, living together")
        s = T(f"Отношения с той же девушкой продолжаются (её характер: {ty(cur)}). Сейчас они {stage}.",
              f"The relationship with the same woman continues (her character: {ty(cur)}). Right now they are {stage}.")
    if cur.get("married") == age:
        s += T(" В этом сезоне он делает предложение, и они женятся.", " This season he proposes and they get married.")
    if cur.get("kids") == age:
        s += T(" В этом сезоне у них рождается ребёнок.", " This season their child is born.")
    if cur.get("divorce") == age:
        s += T(f" В этом сезоне они разводятся. Причина: {br(cur)}.", f" This season they divorce. Reason: {br(cur)}.")
    elif cur["end"] == age and not cur.get("married"):
        s += T(f" В этом сезоне они расстаются. Причина: {br(cur)}.", f" This season they break up. Reason: {br(cur)}.")
    return s
