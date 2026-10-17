#!/usr/bin/env python3
"""Лиги Мексики, Японии, ОАЭ, Катара и Таиланда: составы сезона 2026/27 и оценка OVR клубов.

    python tools/asia_mexico_leagues.py        (дописывает data/world_leagues.csv и data/world_clubs.csv; повторный запуск ничего не дублирует)
    python database/importers/import_fc27.py data/football.db      (переносит в базу)

Составы (английская Википедия, октябрь 2026):
  Liga MX - «2026–27 Liga MX season»: 18 клубов, Атланте вернулся вместо Масатлана (выкупил его место).
  J1 League - «2026–27 J1 League»: первый сезон «осень-весна», 20 клубов; вылетели Йокогама, Сёнан, Альбирекс,
      поднялись Мито, Нагасаки, ДЖЕФ Тиба.
  UAE Pro League - «2026–27 UAE Pro League»: 14 клубов; вылетели Аль-Батаех и Дибба, поднялись Хатта и Юнайтед.
  Qatar Stars League - страницы 2026/27 нет: состав 2025/26 без вылетевшего Умм-Салаля и с чемпионом второй лиги Лусаилом.
  Thai League 1 - «2026–27 Thai League 1»: 16 клубов; вылетели Муангтонг, Накхонратчасима, Канчанабури,
      поднялись Расисалай, Сисакет Юнайтед, Паттани.

Оценка OVR (шкала EA FC, OVR команды): опоры из FC 27 - Аль-Айн 71 и Бурирам 68 (у них рейтинг FC 27, а не ручная оценка).
Средний уровень лиги сверен с лигами, которые уже есть в базе: Саудовская Аравия ср. 69.4, MLS 69.2, Корея 66.2, Китай 63.4.
  Мексика ~70.7 (чуть выше MLS: в Кубке лиг и Кубке чемпионов КОНКАКАФ мексиканские клубы обычно сильнее),
  Япония ~66.5 (чуть выше Кореи: японские клубы последних лет доходят до финалов ЛЧ АФК),
  ОАЭ ~64.6 и Катар ~64.4 (между Китаем и Кореей; лидеры - Аль-Айн, Аль-Садд - на уровне середины Саудовской лиги),
  Таиланд ~59 (Бурирам 68 заметно сильнее остальных).
Внутри лиги - по таблицам прошлого сезона и титулам последних лет.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("uefa_small_leagues", HERE / "uefa_small_leagues.py")
_usl = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_usl)
upsert = _usl.upsert                              # та же запись в CSV: строки этих лиг заменяются, остальные не трогаются

# страна: (league_id, название, кругов, заметка, [(клуб, OVR или None, название в FC 27)])
L = {
    "MEX": ("mex-liga-mx", "Liga MX", 2, "2026/27 (Апертура 2026 + Клаусура 2027)", [
        ("América", 76), ("Monterrey", 76), ("Tigres UANL", 76), ("Cruz Azul", 75), ("Toluca", 75), ("Guadalajara", 74),
        ("Pumas UNAM", 72), ("Pachuca", 72), ("León", 71), ("Atlas", 70), ("Tijuana", 69), ("Querétaro", 68), ("Santos Laguna", 68),
        ("Necaxa", 67), ("Atlético San Luis", 67), ("Juárez", 66), ("Puebla", 66), ("Atlante", 65)]),
    "JPN": ("jpn-j1-league", "J1 League", 2, "2026/27 (первый сезон «осень-весна»)", [
        ("Vissel Kobe", 70), ("Kashima Antlers", 70), ("Sanfrecce Hiroshima", 69), ("Kashiwa Reysol", 68), ("Machida Zelvia", 68),
        ("Urawa Red Diamonds", 68), ("Kawasaki Frontale", 68), ("Gamba Osaka", 67), ("Cerezo Osaka", 67), ("FC Tokyo", 67),
        ("Kyoto Sanga", 66), ("Yokohama F. Marinos", 66), ("Nagoya Grampus", 66), ("Avispa Fukuoka", 65), ("Fagiano Okayama", 65),
        ("Shimizu S-Pulse", 65), ("Tokyo Verdy", 64), ("V-Varen Nagasaki", 64), ("Mito HollyHock", 63), ("JEF United Chiba", 63)]),
    "UAE": ("uae-pro-league", "UAE Pro League", 2, "2026/27", [
        ("Al Ain", None, "Al Ain FC (UAE)"), ("Shabab Al Ahli", 70), ("Al Wasl", 68), ("Al Jazira", 67), ("Al Wahda", 67),
        ("Al-Nasr", 66), ("Sharjah", 66), ("Ajman", 63), ("Baniyas", 63), ("Khor Fakkan", 62), ("Kalba", 62), ("Al Dhafra", 61),
        ("United FC", 61), ("Hatta", 60)]),
    "QAT": ("qat-stars-league", "Qatar Stars League", 2, "2026/27 (состав выведен из сезона 2025/26: вылетел Умм-Салаль, поднялся Лусаил)", [
        ("Al Sadd", 70), ("Al Duhail", 68), ("Al-Rayyan", 68), ("Al-Gharafa", 67), ("Al-Shamal", 66), ("Al-Arabi", 65), ("Qatar SC", 64),
        ("Al-Wakrah", 64), ("Al Ahli Doha", 63), ("Al-Sailiya", 62), ("Al Shahaniya", 61), ("Lusail SC", 61)]),
    "THA": ("tha-thai-league-1", "Thai League 1", 2, "2026/27", [
        ("Buriram United", None, "Buriram United"), ("Port FC", 63), ("Ratchaburi", 62), ("BG Pathum United", 62), ("Bangkok United", 62),
        ("PT Prachuap", 59), ("Chiangrai United", 59), ("Chonburi", 58), ("Rayong", 58), ("Ayutthaya United", 57), ("Uthai Thani", 57),
        ("Lamphun Warriors", 56), ("Sukhothai", 56), ("Pattani", 55), ("Rasisalai United", 55), ("Sisaket United", 55)]),
}

# сила лиги (шкала world_league_strength.csv: Бразилия 78, Аргентина 66, MLS 60, Саудовская Аравия 55, Корея 50, Китай 40)
STRENGTH = {"MEX": (62, "по мировым рейтингам лиг: чуть выше MLS"), "JPN": (52, "чуть выше Кореи"),
            "UAE": (44, "между Кореей и Китаем"), "QAT": (44, "между Кореей и Китаем"), "THA": (32, "между Индией и Китаем")}

def main():
    leagues, clubs = [], []
    for cc, (lid, name, rounds, note, cl) in L.items():
        n = len(cl)
        leagues.append({"league_id": lid, "country_code": cc, "name": name, "tier": 1, "rounds": rounds,
                        "season_note": f"{note}; {n} клубов, {rounds} круга ({rounds * (n - 1)} матчей)"})
        for c in cl:
            club, ovr, fc = (c + (None,))[:3] if len(c) == 2 else c
            clubs.append({"league_id": lid, "name": club, "club_country": "", "is_reserve": 0, "fc_name": fc or "",
                          "est_ovr": "" if fc else ovr})
    lids = {l["league_id"] for l in leagues}
    a = upsert("world_leagues.csv", ["league_id", "country_code", "name", "tier", "rounds", "season_note"], leagues, lambda r: r["league_id"])
    b = upsert("world_clubs.csv", ["league_id", "name", "club_country", "is_reserve", "fc_name", "est_ovr"], clubs,
               lambda r: r["league_id"] if r["league_id"] in lids else (r["league_id"], r["name"]))
    c = upsert("world_league_strength.csv", ["fifa_code", "league_strength", "note"],
               [{"fifa_code": k, "league_strength": v, "note": t} for k, (v, t) in STRENGTH.items()], lambda r: r["fifa_code"])
    print(f"лиг записано: {a}, клубов записано: {b}, сила лиг: {c}")
    for cc, (lid, name, rounds, note, cl) in L.items():
        est = [x[1] for x in cl if x[1] is not None]
        print(f"  {cc} {name:20s} клубов {len(cl):2d} | ручные OVR {min(est)}-{max(est)}, ср. {sum(est) / len(est):.1f}")

if __name__ == "__main__":
    main()
