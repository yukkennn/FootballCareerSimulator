#!/usr/bin/env python3
"""Высшие лиги оставшихся 28 ассоциаций УЕФА (Кипр ... Сан-Марино): составы сезона 2026/27 и оценка OVR клубов.

    python tools/uefa_small_leagues.py        (дописывает data/world_leagues.csv и data/world_clubs.csv; повторный запуск ничего не дублирует)

Составы: страницы сезонов 2026/27 (2026 для лиг «весна-осень») в английской Википедии, октябрь 2026. Для Андорры, Черногории
и Сан-Марино страниц 2026/27 нет: состав 2025/26 с известными изменениями (Андорра: вылетели UE Santa Coloma и Pas de la Casa,
пришли Casa de Portugal и Sporting d'Escaldes; Черногория: вылетел Jedinstvo, пришёл Otrant; в Сан-Марино вылета нет).
Лихтенштейн своей лиги не имеет (Вадуц играет в Швейцарии), поэтому его здесь нет.

Оценка OVR: средний уровень лиги - по 5-летнему коэффициенту УЕФА на 2027 год (рейтинг ru.uefa.com), по той же
зависимости, что у лиг, которые уже есть в базе (коэфф. 45 -> ср. OVR ~66, 25 -> ~64, 12 -> ~59 у Казахстана), а ниже
коэффициента ~10 - заметно круче вниз: в полупрофессиональных лигах (Андорра, Гибралтар, Уэльс, Сан-Марино) средний OVR 39-45.
Внутри лиги - по реальной иерархии клубов (чемпионы и еврокубковые участники последних лет выше). Опоры из EA FC 27:
АПОЭЛ 70, Омония 70, Ференцварош 70, Карабах 69, ХИК 65 - у них рейтинг FC 27, а не ручная оценка.
"""
import csv, io
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Сдвиг всей лиги после сверки с лигами, которые уже есть в базе (их OVR из FC 27): при том же коэффициенте УЕФА
# средний OVR должен быть близок (Румыния/Украина/Израиль с коэфф. ~24-25 - ср. 63.5-65.6; Сербия 18 - 62.4; Казахстан 12 - 59).
# Ниже в списках клубов - иерархия внутри лиги, этот сдвиг поднимает лигу целиком.
OFFSET = {"CYP": 2, "HUN": 2, "AZE": 2, "SVN": 2, "SVK": 2, "ISL": 4, "IRL": 3, "ARM": 4, "KOS": 4, "BIH": 3, "LVA": 4, "FIN": 3, "MDA": 2}

# страна: (league_id, название, кругов, коэфф. УЕФА 2027, [(клуб, OVR или None, название в FC 27, страна клуба, фарм-клуб)])
L = {}
def lg(cc, lid, name, rounds, coeff, clubs):
    full = [c if len(c) == 5 else (c[0], c[1], None, "", 0) for c in clubs]             # (клуб, OVR) -> полная запись
    off = OFFSET.get(cc, 0)
    L[cc] = (lid, name, rounds, coeff, [(n, None if o is None else o + off, fc, ccc, r) for n, o, fc, ccc, r in full])

lg("CYP", "cyp-first-division", "Cypriot First Division", 2, 34.693, [
    ("APOEL", None, "APOEL Nicosia FC", "", 0), ("Omonia Nicosia", None, "Omonia Nicosia FC", "", 0), ("Pafos FC", 69),
    ("AEK Larnaca", 67), ("Aris Limassol", 65), ("Apollon Limassol", 64), ("Anorthosis Famagusta", 63), ("AEL Limassol", 62),
    ("Omonia Aradippou", 59), ("Olympiakos Nicosia", 59), ("Nea Salamis Famagusta", 58), ("Krasava E.N.Y.", 58), ("Karmiotissa", 57),
    ("Omonia 29M", 57)])
lg("HUN", "hun-nb-i", "NB I", 3, 27.812, [
    ("Ferencváros", None, "Ferencvárosi TC", "", 0), ("Puskás Akadémia", 65), ("Paks", 64), ("Debrecen", 63), ("ETO Győr", 63),
    ("Újpest", 62), ("MTK Budapest", 61), ("Zalaegerszeg", 61), ("Kisvárda", 60), ("Nyíregyháza", 59), ("Vasas", 59), ("Kispest-Honvéd", 59)])
lg("AZE", "aze-premier-league", "Azerbaijan Premier League", 3, 24.187, [
    ("Qarabağ", None, "Qarabağ FK", "", 0), ("Sabah", 64), ("Zira", 63), ("Neftçi", 62), ("Turan Tovuz", 61), ("Araz-Naxçıvan", 61),
    ("Sumgayit", 59), ("Kapaz", 58), ("Qabala", 58), ("Shamakhi", 57), ("Imishli", 55), ("Shafa", 55)])
lg("SVN", "svn-prvaliga", "PrvaLiga", 4, 22.843, [
    ("Celje", 65), ("Olimpija Ljubljana", 65), ("Maribor", 64), ("Koper", 62), ("Bravo", 60), ("Mura", 60), ("Radomlje", 58),
    ("Aluminij", 58), ("Nafta 1903", 57), ("Brinje Grosuplje", 56)])
lg("SVK", "svk-nike-liga", "Niké liga", 3, 22.375, [
    ("Slovan Bratislava", 66), ("DAC Dunajská Streda", 63), ("Spartak Trnava", 63), ("Žilina", 62), ("Podbrezová", 60),
    ("Zemplín Michalovce", 59), ("Trenčín", 59), ("Ružomberok", 59), ("Košice", 59), ("Skalica", 57), ("Komárno", 57),
    ("Dukla Banská Bystrica", 57)])
lg("ISL", "isl-besta-deild", "Besta deild", 2, 17.02, [
    ("Víkingur Reykjavík", 59), ("Breiðablik", 59), ("Valur", 58), ("Stjarnan", 57), ("FH", 56), ("KR", 56), ("ÍA", 55), ("Fram", 55),
    ("KA", 55), ("ÍBV", 54), ("Keflavík", 53), ("Þór Akureyri", 53)])
lg("IRL", "irl-premier-division", "League of Ireland Premier Division", 4, 16.343, [
    ("Shamrock Rovers", 61), ("Shelbourne", 59), ("Derry City", 58, "", "NIR", 0), ("St Patrick's Athletic", 58), ("Bohemians", 57),
    ("Sligo Rovers", 55), ("Galway United", 55), ("Drogheda United", 55), ("Waterford", 55), ("Dundalk", 55)])
lg("ARM", "arm-premier-league", "Armenian Premier League", 3, 15.812, [
    ("Noah", 61), ("Ararat-Armenia", 59), ("Pyunik", 59), ("Urartu", 57), ("Alashkert", 57), ("Ararat Yerevan", 54), ("Shirak", 54),
    ("Van", 54), ("BKMA Yerevan", 53), ("Syunik", 53), ("Gandzasar Kapan", 52), ("Sardarapat", 51)])
lg("KOS", "kos-superliga", "Superliga e Kosovës", 4, 14.031, [
    ("Ballkani", 59), ("Drita", 58), ("Prishtina", 56), ("Gjilani", 55), ("Llapi", 55), ("Malisheva", 54), ("Dukagjini", 53),
    ("Feronikeli", 53), ("Drenica", 52), ("Vushtrria", 52)])
lg("BIH", "bih-premijer-liga", "Premijer liga BiH", 3, 13.968, [
    ("Zrinjski Mostar", 61), ("Borac Banja Luka", 61), ("Sarajevo", 59), ("Željezničar", 58), ("Velež Mostar", 57), ("Široki Brijeg", 56),
    ("Sloga Doboj", 54), ("Radnik Bijeljina", 54), ("Čelik Zenica", 53), ("BSK Banja Luka", 52)])
lg("LVA", "lva-virsliga", "Virslīga", 4, 13.875, [
    ("RFS", 61), ("Riga FC", 59), ("Auda", 56), ("Liepāja", 54), ("BFC Daugavpils", 53), ("FS Jelgava", 53), ("Super Nova", 52),
    ("Grobiņa", 51), ("Tukums 2000", 51), ("Ogre United", 50)])
lg("FIN", "fin-veikkausliiga", "Veikkausliiga", 2, 13.625, [
    ("HJK", None, "HJK Helsinki", "", 0), ("KuPS", 60), ("Ilves", 58), ("SJK", 58), ("Inter Turku", 57), ("VPS", 56), ("Gnistan", 55),
    ("AC Oulu", 55), ("Lahti", 54), ("IFK Mariehamn", 54), ("TPS", 54), ("Jaro", 53)])
lg("MDA", "mda-liga", "Liga Moldova", 4, 10.25, [
    ("Sheriff Tiraspol", 61), ("Petrocub Hîncești", 56), ("Milsami Orhei", 55), ("Zimbru Chișinău", 55), ("Bălți", 53),
    ("Dacia Buiucani", 51), ("Real Sireți", 50), ("Politehnica UTM", 50)])
lg("FRO", "fro-premier-league", "Faroe Islands Premier League", 3, 9.875, [
    ("KÍ", 55), ("Víkingur Gøta", 52), ("HB", 52), ("B36 Tórshavn", 51), ("NSÍ Runavík", 51), ("07 Vestur", 49), ("EB/Streymur", 48),
    ("B68 Toftir", 48), ("Skála", 47), ("AB Argir", 47)])
lg("ALB", "alb-kategoria-superiore", "Kategoria Superiore", 4, 9.0, [
    ("Egnatia", 57), ("Partizani", 56), ("Vllaznia", 56), ("Tirana", 55), ("Dinamo City", 55), ("Teuta", 54), ("Elbasani", 53),
    ("Laçi", 53), ("Skënderbeu", 53), ("Vora", 51)])
lg("MKD", "mkd-first-league", "Macedonian First League", 3, 8.967, [
    ("Shkëndija", 57), ("Vardar", 55), ("Struga", 55), ("Sileks", 53), ("Arsimi", 53), ("Shkëndija 77", 52), ("Bashkimi", 52),
    ("Tikvesh", 52), ("Bregalnica Štip", 51), ("Skopje", 50)])
lg("BLR", "blr-premier-league", "Belarusian Premier League", 2, 8.708, [
    ("Dinamo Minsk", 58), ("BATE Borisov", 56), ("Neman Grodno", 55), ("Torpedo-BelAZ", 55), ("Isloch", 54), ("Dinamo Brest", 54),
    ("Slavia Mozyr", 53), ("Gomel", 53), ("FC Minsk", 53), ("Maxline Vitebsk", 53), ("Arsenal Dzerzhinsk", 52), ("Vitebsk", 52),
    ("Naftan Novopolotsk", 51), ("Dnepr Mogilev", 51), ("Belshina Bobruisk", 51), ("Baranovichi", 50)])
lg("LTU", "ltu-toplyga", "TOPLYGA", 4, 8.125, [
    ("Žalgiris Vilnius", 57), ("Kauno Žalgiris", 56), ("Hegelmann", 55), ("Sūduva", 54), ("Panevėžys", 54), ("FA Šiauliai", 52),
    ("Banga Gargždai", 52), ("Džiugas", 51), ("TransINVEST", 50)])
lg("AND", "and-primera-divisio", "Primera Divisió", 3, 7.832, [
    ("Inter Club d'Escaldes", 50), ("FC Santa Coloma", 47), ("Atlètic Club d'Escaldes", 46), ("Rànger's", 46), ("Penya Encarnada", 44),
    ("Ordino", 43), ("Carroi", 42), ("Casa de Portugal", 42), ("Esperança d'Andorra", 41), ("Sporting Club d'Escaldes", 41)])
lg("MLT", "mlt-premier-league", "Maltese Premier League", 2, 7.625, [
    ("Ħamrun Spartans", 54), ("Hibernians", 51), ("Floriana", 50), ("Birkirkara", 50), ("Sliema Wanderers", 49), ("Valletta", 49),
    ("Gżira United", 48), ("Marsaxlokk", 47), ("Mosta", 47), ("Balzan", 46), ("Żabbar St. Patrick", 45), ("Birżebbuġa St. Peter's", 44)])
lg("GIB", "gib-football-league", "Gibraltar Football League", 2, 7.207, [
    ("Lincoln Red Imps", 50), ("St Joseph's", 46), ("Europa", 45), ("FC Magpies", 44), ("Lions Gibraltar", 43), ("Glacis United", 42),
    ("Mons Calpe", 42), ("College 1975", 41), ("Lynx", 41), ("Hound Dogs", 40), ("Europa Point", 40)])
lg("EST", "est-meistriliiga", "Meistriliiga", 4, 7.041, [
    ("Flora Tallinn", 54), ("FCI Levadia", 54), ("Paide Linnameeskond", 51), ("Nõmme Kalju", 51), ("Narva Trans", 48), ("Tammeka", 47),
    ("Harju", 47), ("Nõmme United", 47), ("Kuressaare", 46), ("Vaprus", 46)])
lg("NIR", "nir-premiership", "NIFL Premiership", 3, 6.625, [
    ("Linfield", 54), ("Larne", 53), ("Glentoran", 52), ("Cliftonville", 52), ("Coleraine", 52), ("Crusaders", 51),
    ("Dungannon Swifts", 50), ("Portadown", 49), ("Ballymena United", 49), ("Carrick Rangers", 48), ("Bangor", 47), ("Limavady United", 46)])
lg("GEO", "geo-erovnuli-liga", "Erovnuli Liga", 4, 6.5, [
    ("Dinamo Tbilisi", 56), ("Dinamo Batumi", 56), ("Iberia 1999", 55), ("Torpedo Kutaisi", 55), ("Dila Gori", 54),
    ("Samgurali Tsqaltubo", 52), ("Spaeri", 52), ("Gagra", 52), ("Rustavi", 50), ("Meshakhte", 50)])
lg("LUX", "lux-national-division", "BGL Ligue", 2, 6.25, [
    ("Differdange 03", 51), ("Progrès Niederkorn", 50), ("F91 Dudelange", 50), ("Swift Hesperange", 50), ("Racing Union", 49),
    ("UNA Strassen", 49), ("Victoria Rosport", 47), ("Jeunesse Esch", 47), ("Käerjeng 97", 46), ("Hostert", 45), ("Mondorf-les-Bains", 45),
    ("Etzella Ettelbruck", 45), ("Wiltz 71", 44), ("US Rumelange", 44), ("Atert Bissen", 43), ("Résidence Walferdange", 43)])
lg("MNE", "mne-first-league", "Montenegrin First League", 4, 5.833, [
    ("Budućnost Podgorica", 54), ("Sutjeska Nikšić", 54), ("Dečić", 52), ("Mornar Bar", 51), ("Petrovac", 50), ("Mladost Donja Gorica", 50),
    ("Arsenal Tivat", 49), ("Jezero", 48), ("Bokelj", 48), ("Otrant", 46)])
lg("WAL", "wal-cymru-premier", "Cymru Premier", 2, 4.499, [
    ("The New Saints", 54), ("Connah's Quay Nomads", 49), ("Penybont", 48), ("Caernarfon Town", 47), ("Barry Town United", 46),
    ("Haverfordwest County", 46), ("Colwyn Bay", 45), ("Cardiff Met", 44), ("Flint Town United", 44), ("Briton Ferry Llansawel", 43),
    ("Airbus UK Broughton", 43), ("Llandudno", 43), ("Ammanford", 42), ("Holywell Town", 42), ("Cambrian United", 41), ("Trefelin BGC", 41)])
lg("SMR", "smr-campionato-sammarinese", "Campionato Sammarinese", 2, 2.998, [
    ("Tre Fiori", 44), ("Virtus", 43), ("La Fiorita", 43), ("Tre Penne", 43), ("Folgore", 41), ("Domagnano", 41), ("Fiorentino", 40),
    ("Cosmos", 40), ("Juvenes/Dogana", 39), ("Libertas", 39), ("Pennarossa", 38), ("San Giovanni", 38), ("Faetano", 37),
    ("San Marino Academy U22", 37, "", "", 1), ("Cailungo", 36), ("Murata", 36)])

def upsert(name, fields, new_rows, key):
    """Строки этих лиг заменяются новыми (повторный запуск обновляет оценки, а не дублирует), остальные строки файла не трогаются."""
    path = DATA / name
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    mine = {key(r) for r in new_rows}
    keep = [lines[0]] + [l for l in lines[1:] if l.strip() and key(next(csv.DictReader(io.StringIO(lines[0] + l)))) not in mine]
    out = io.StringIO()
    csv.DictWriter(out, fieldnames=fields, lineterminator="\n").writerows(new_rows)
    path.write_text("".join(keep) + out.getvalue(), encoding="utf-8", newline="")
    return len(new_rows)

def main():
    leagues, clubs = [], []
    for cc, (lid, name, rounds, coeff, cl) in L.items():
        n = len(cl)
        leagues.append({"league_id": lid, "country_code": cc, "name": name, "tier": 1, "rounds": rounds,
                        "season_note": f"2026/27; {n} клубов, {rounds} круга ({rounds * (n - 1)} матчей); коэфф. УЕФА 2027: {coeff}"})
        for club, ovr, fc, ccc, res in cl:
            clubs.append({"league_id": lid, "name": club, "club_country": ccc, "is_reserve": res, "fc_name": fc or "",
                          "est_ovr": "" if fc else ovr})
    lids = {l["league_id"] for l in leagues}
    a = upsert("world_leagues.csv", ["league_id", "country_code", "name", "tier", "rounds", "season_note"], leagues, lambda r: r["league_id"])
    b = upsert("world_clubs.csv", ["league_id", "name", "club_country", "is_reserve", "fc_name", "est_ovr"], clubs,
               lambda r: r["league_id"] if r["league_id"] in lids else (r["league_id"], r["name"]))
    print(f"лиг записано: {a}, клубов записано: {b}")
    for cc, (lid, name, rounds, coeff, cl) in sorted(L.items(), key=lambda x: -x[1][3]):
        est = [c[1] for c in cl if c[1] is not None]
        print(f"  {cc} {name:36s} коэфф. {coeff:7.3f} | клубов {len(cl):2d} | OVR {min(est)}-{max(est)}, ср. {sum(est) / len(est):.1f}")

if __name__ == "__main__":
    main()
