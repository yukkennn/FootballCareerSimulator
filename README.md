**English** · [Русский](#симулятор-футбольной-карьеры)

# Football Career Simulator

**Play in your browser (desktop or phone):** https://yukkennn.github.io/FootballCareerSimulator/

© 2026 yukkennn · License [CC BY-NC 4.0](LICENSE): you may copy and modify it only with attribution and only for non-commercial purposes
(see [License](#license) for details).

A desktop application (Python + PySide6 + SQLite): you choose a nationality, position, preferred foot and height,
go through an academy from age 15, play senior football from 18 and keep playing until 40 (or retire earlier yourself).
After every season you can pick a new club. Once your playing career is over, you can become a coach: choose a club,
meet the board's target and keep the board's anger below 100 (otherwise you get sacked).

## Phone version (web app)
The same game in the browser: the Python code runs through Pyodide, and the interface was rewritten for small screens (`game/web/`, `web/`).
On a wide screen (computer) the site shows a desktop layout similar to the .exe; on a phone it shows a compact one.
Both the playing career and the coaching career are available (transfer window, squad, starting XI, scouts, loans).
1. Build: `python tools/build_web.py` (requires Pillow); the result goes to the `site/` folder.
2. Test on a computer: `python -m http.server 8765 -d site`, then open http://localhost:8765.
3. On a phone: open https://yukkennn.github.io/FootballCareerSimulator/ and choose "Add to Home Screen" (Android: the ⋮ menu; iPhone: "Share").
   The site is rebuilt and deployed automatically on every push to `main` (`.github/workflows/pages.yml`).
Saves are stored in the browser. The "Export" button on the load screen saves a copy to a file, and "Import" brings it back.
Headless test: `python tests/test_web_flow.py`.

**Playing offline.** Open the site once with an internet connection and wait 10-20 seconds on the start screen: the game and Python (about 10 MB)
are saved in the browser. After that the game starts from the home-screen icon without internet. Club crests are saved as you see them:
offline, a crest you have never seen is drawn as a circle with initials. Updates arrive by themselves the next time you open the site online.

## Running the .exe (Windows)
Double-click the **Football Career Sim** shortcut in the project folder (or `dist\FootballCareerSim\FootballCareerSim.exe`).
Python is not required: the whole `dist\FootballCareerSim` folder can be copied to another computer or into an archive.

If the game has been changed or there is no `dist` folder, rebuild the exe: double-click **build_exe.bat** (1-3 minutes; the first build
needs Python and an internet connection). Saves and settings are stored separately in `%USERPROFILE%\.football_career_sim\`, so
rebuilding does not touch them. If the game crashes, the error text is written to `error.log` in the same folder.

## Running from source
1. Install Python 3.10 or newer from https://www.python.org/downloads/ (tick **Add Python to PATH**).
2. Double-click **run.bat**. On the first run it installs PySide6 by itself (needs internet, about 1-2 minutes).

macOS / Linux: `./run.sh`.

## How to play
1. Choose a nationality (search across 211 FIFA countries; each national team shows its strength as 1 to 5 stars), a position and how often you can choose a transfer (every 1, 2 or 3 years).
2. Look at your starting attributes (you can "Reroll" them) and pick an academy from 3-5 options. The academy is usually from your country,
   with a 1-in-10 chance of a foreign one; if your country has no league in the database, this is stated plainly: "a team from another league".
3. Press "Play". After each period you get a report for every competition separately: league, cup, super cup, Champions League, Europa League,
   Conference League, Libertadores and so on (games, goals, assists, outcome, and the opponent and score when you were knocked out), the national team
   (qualifying, play-offs, final tournament, Nations League), trophies, awards and a Ballon d'Or panel with the winner and the top three. Then 1-5 club offers with transfer fees.
4. In the academy (ages 15-17) you play in the U-18 youth league; first-team results are shown only if you were called up for a cup or given a debut.
5. The career ends by itself at 40. The "Retire" button is on the career screen and on the offers screen, and you can press it at any time.
6. The game saves itself after every period (folder `~/.football_career_sim/saves`); load a save with the button on the start screen.
   Saves from the previous version still open: club strengths are taken from the new database.

The language (Russian / English) can be switched on the start screen.

**Season diary (web and desktop).** An AI writes the hero's diary for every season, as a player and as a coach: matches, trophies,
everyday life, family, friends and romance. Every sporting fact (scores, places, goals, trophies, board decisions) comes from the game, and
the AI only turns it into prose; personal life carries over from season to season. With "Write the diary automatically" on, the diary is written
in the background right after each season; otherwise use the "📖 Season diary" button (desktop: "📖 Diaries", or double-click a season).
"Export" on the career summary adds all diaries as one book after the statistics. Choose the service (Google Gemini or Anthropic Claude), the model
and the API key under ⚙ Settings on the start screen. The key is stored only in your browser (desktop: in the settings file in the
`.football_career_sim` folder) and sent only to the chosen service. A free Gemini key: aistudio.google.com -> Get API key.
Code: `game/story.py` (facts and the prompt), `web/llm.js` and `game/llm.py` (API calls), `game/ui/diary.py` (desktop windows).

**Leagues live their own life.** Every club has good and bad seasons, and now and then one of the strongest clubs in a league starts an era
of dominance for 5-10 seasons (money and squad), then gradually returns to its usual level. Historical giants stay giants: in Spain the title
almost always goes to Real Madrid, Barcelona or Atlético, but which of them wins changes. Settings are at the top of `game/world.py` (REVERT, HEG_*, FORM_SD, LEAD_*).

**European qualifying.** As in real life, not everyone goes straight into the league phase. The top clubs of the strongest leagues qualify directly,
champions of smaller leagues go through the Champions League qualifying "champions path" (Q1, Q2, Q3, play-off round), runners-up of mid-ranked
leagues through the "league path". A club knocked out of Champions League qualifying continues in the Europa League or Conference League qualifying,
one knocked out of Europa League qualifying drops to the Conference League, and a club that loses in Conference League qualifying is out of Europe
for the season. Access list: `EURO_ACCESS` in `game/world.py`.

## Awards
The Ballon d'Or, the World Team of the Year and the best young player are contested between your player and 60 world stars
(real ones at the start: Mbappé, Haaland, Yamal and others; later they age and new talents appear). Goals and assists
(adjusted for league level), club and national-team trophies and the player's class all count. A high rating without stats and trophies no longer wins an award.
The league Team of the Season, Player of the Season and the Golden Boot depend on the average season rating and league goals.

## What's inside
- `main.py`, `game/`: the application (`world.py` leagues, cups, continental competitions, national teams; `career.py` the career; `stats.py` goals and ratings;
  `stars.py` world stars; `player.py` development and decline; `ui/` desktop screens; `web/` web screens).
- `data/football.db`, `assets/logos/`: club database and crests (1214 clubs, 83 leagues, 211 countries; team ratings from EA FC 27, smaller UEFA leagues rated by hand from the UEFA coefficient).
- `database/`, `tools/`, `data/`, `docs/DATA_SOURCES.md`: building the database, importing FC 27, Elo and EA FC ratings, downloading missing crests.
- `tests/`: `balance.py` (mass career runs), `test_ui_flow.py` (headless desktop interface), `test_web_flow.py` (headless web interface),
  `test_diary_desktop.py` (desktop season diary with a stub instead of the AI), importer tests.

## Known limitations
- **Clubs exist for 78 countries**: all 55 UEFA members, 10 CONMEBOL countries (Argentina, Brazil, Colombia, Chile, Peru, Ecuador, Uruguay, Paraguay, Bolivia,
  Venezuela), Mexico, MLS (USA plus 3 Canadian clubs), Japan, Saudi Arabia, South Korea, China, the UAE, Qatar, Thailand, India and Australia (plus 2 New Zealand clubs).
  75 countries have their own league; clubs from Canada, New Zealand and Liechtenstein play in their neighbours' leagues, and a few Welsh and Andorran
  clubs (Cardiff, Swansea, Wrexham, Newport, FC Andorra) play in the English and Spanish leagues. For the other 133 countries the academy is taken
  from a fallback country (`data/academy_fallback.csv`).
- **Many clubs are rated by hand**: EA FC 27 has only some of them. Colombia, Chile, Peru, Ecuador, Uruguay, Paraguay, Bolivia and Venezuela have
  only 4-7 FC 27 clubs each, so well-known clubs with hand-made ratings were added; those leagues are shorter than the real ones (8-12 clubs), but extra rounds
  give a realistic number of games (32-44). 6 of the 20 Brazilian clubs were added by hand. 24 small UEFA leagues (Albania, Armenia, the Baltics, Ireland,
  Wales and others) are rated entirely by hand from the UEFA coefficient, and Hungary, Cyprus, Azerbaijan and Finland have only 1-2 FC 27 clubs each.
  The actual 2027 line-up of these leagues may differ.
- **Mexico, Japan, the UAE, Qatar and Thailand** (added in October 2026): line-ups for 2026/27 from the English Wikipedia (for Qatar there is no
  2026/27 page yet, so the line-up was derived from 2025/26 with promotion and relegation). EA FC 27 has only Al Ain (71) and Buriram (68);
  the other clubs are rated by hand against the leagues already in the game (`tools/asia_mexico_leagues.py`). Mexico's cup is called Copa MX in the game,
  although the real Copa MX has not been held since 2020.
- **No clubs from Africa** and from many other countries (Central America, Iran, Egypt and others). The CONCACAF Champions Cup is played only by
  Mexican and MLS clubs. The AFC Champions League Two, the African and Oceanian club competitions and the Club World Cup are listed in the database
  but are not played in the game.
- **8 clubs have no crest**: reserve and youth teams (Real Sociedad B, VfB Stuttgart II and others), United Tigers, Juvenes/Dogana and Khor Fakkan. A circle with initials is drawn instead.
  To download missing crests: `python tools/fetch_logos.py data/football.db`.
- **Star players' clubs at the start** (574 real players in `data/real_players.csv`) are based on data up to summer 2026 and have not been re-checked: some may have moved.
- **Testing**: the web version is checked automatically by `tests/test_web_flow.py` before every deployment (a full playing and coaching career, Russian and English)
  and was checked by hand in the browser at phone and desktop widths. Before deployment the JavaScript syntax is checked too.
  Offline mode was checked in Microsoft Edge (first visit online, then the network cut off and the game reopened) and confirmed on a real phone: without internet the game opens.
  The desktop app (.exe) has only an automated headless test (`tests/test_ui_flow.py`): if something looks wrong or crashes, send a screenshot or the error text.
- Matches are not simulated minute by minute: season results come from a probabilistic model.

## License
© 2026 yukkennn. The code, interface and game logic are distributed under the
**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** license; full text in [LICENSE](LICENSE),
summary: https://creativecommons.org/licenses/by-nc/4.0/

- **You may** copy, share and modify the project, including making your own version.
- **You must** credit the author (yukkennn), link to this repository and the license, and indicate what you changed.
- **You may not** use the project for commercial purposes: selling it, charging for access, or earning money from ads.

**Third-party data is not covered by this license.** Club and player ratings (EA SPORTS FC), club crests, the names of
clubs and competitions and the names of real footballers belong to their respective owners and are used in a non-commercial fan game.
More about the sources: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).

---

[English](#football-career-simulator) · **Русский**

# Симулятор футбольной карьеры

**Играть в браузере (и на телефоне):** https://yukkennn.github.io/FootballCareerSimulator/

© 2026 yukkennn · Лицензия [CC BY-NC 4.0](LICENSE): можно копировать и изменять только с указанием автора и только не для заработка
(подробнее в разделе [Лицензия](#лицензия)).

Десктопное приложение (Python + PySide6 + SQLite): вы выбираете страну, позицию, ведущую ногу и рост,
проходите академию с 15 лет, взрослый футбол с 18 и играете до 40 лет (или завершаете карьеру раньше сами).
После каждого сезона можно выбрать новый клуб. Завершив карьеру игрока, можно стать тренером: выбрать клуб,
выполнять задачу руководства и не доводить его раздражение до 100 (иначе уволят).

## Версия для телефона (веб-приложение)
Та же игра в браузере: код Python работает через Pyodide, интерфейс написан заново под узкий экран (`game/web/`, `web/`).
На широком экране (компьютер) сайт показывает раскладку как в exe, на телефоне - компактную.
Есть и карьера игрока, и тренерская карьера (трансферное окно, состав, основа, скауты, аренды).
1. Сборка: `python tools/build_web.py` (нужен Pillow), результат в папке `site/`.
2. Проверка на компьютере: `python -m http.server 8765 -d site`, затем открыть http://localhost:8765.
3. На телефоне: открыть https://yukkennn.github.io/FootballCareerSimulator/ и выбрать «Добавить на главный экран» (Android: меню ⋮; iPhone: «Поделиться»).
   Сайт пересобирается и выкладывается сам при каждом push в `main` (`.github/workflows/pages.yml`).
Сохранения хранятся в браузере. Кнопка «Экспорт» на экране загрузки сохраняет копию в файл, «Импорт» возвращает её.
Тест без браузера: `python tests/test_web_flow.py`.

**Игра без интернета.** Один раз откройте сайт с интернетом и подождите 10-20 секунд на стартовом экране: игра и Python (около 10 МБ)
сохранятся в браузере. После этого игра запускается с иконки на главном экране без интернета. Эмблемы клубов сохраняются по мере просмотра:
без интернета ещё не виденная эмблема рисуется кругом с инициалами. Обновления приходят сами при следующем открытии сайта с интернетом.

## Запуск через .exe (Windows)
Дважды щёлкните ярлык **Football Career Sim** в папке проекта (или `dist\FootballCareerSim\FootballCareerSim.exe`).
Python для этого не нужен: папку `dist\FootballCareerSim` целиком можно скопировать на другой компьютер или в архив.

Если игру изменили или папки `dist` нет, пересоберите exe: дважды щёлкните **build_exe.bat** (1-3 минуты; при первой сборке
нужен Python и интернет). Сохранения и настройки лежат отдельно, в `%USERPROFILE%\.football_career_sim\`, поэтому
пересборка их не трогает. Если игра упадёт, текст ошибки будет в `error.log` в той же папке.

## Запуск из исходников
1. Установите Python 3.10 или новее с https://www.python.org/downloads/ (поставьте галочку **Add Python to PATH**).
2. Дважды щёлкните **run.bat**. При первом запуске он сам установит PySide6 (нужен интернет, ~1-2 минуты).

macOS / Linux: `./run.sh`.

## Как играть
1. Выберите национальность (поиск по 211 странам FIFA, у каждой сборной видна её сила в звёздах от 1 до 5), позицию и частоту выбора перехода (1, 2 или 3 года).
2. Посмотрите стартовые характеристики (можно «Перегенерировать»), выберите академию из 3-5 вариантов. Академия обычно из вашей страны,
   с шансом 1/10 зарубежная; если в вашей стране нет лиги в базе, это честно подписано: «команда из другого чемпионата».
3. Нажимайте «Сыграть». После каждого периода отчёт по каждому турниру отдельно: лига, кубок, суперкубок, Лига чемпионов, Лига Европы,
   Лига конференций, Либертадорес и т.д. (матчи, голы, передачи, итог, а при вылете соперник и счёт), сборная (отбор, стыки, финальный турнир,
   Лига наций), трофеи, награды и плашка Золотого мяча с победителем и тройкой лучших. Затем 1-5 предложений клубов с ценой.
4. В академии (15-17 лет) вы играете в молодёжной лиге U-18; результаты основной команды показываются, только если вас вызвали на кубок или дали дебютировать.
5. Карьера заканчивается сама в 40 лет. Кнопка «Завершить карьеру» есть на экране карьеры и на экране предложений, нажать её можно в любой момент.
6. Игра сохраняется сама после каждого периода (папка `~/.football_career_sim/saves`), загрузка кнопкой на стартовом экране.
   Сохранения прошлой версии открываются: силы клубов в них берутся из новой базы.

Язык (русский / английский) переключается на стартовом экране.

**Дневник сезона (сайт и версия для компьютера).** Нейросеть пишет дневник героя за каждый сезон - и игрока, и тренера: матчи, трофеи,
повседневная жизнь, семья, друзья, романтика. Все спортивные факты (счёт, места, голы, трофеи, решения руководства) берутся из игры, нейросеть
только превращает их в текст; личная жизнь продолжается из сезона в сезон. С галочкой «Писать дневник сам после каждого сезона» дневник пишется
в фоне сразу после сезона, иначе - кнопкой «📖 Дневник сезона» (в версии для компьютера - «📖 Дневники» или двойной щелчок по сезону).
«Экспорт» в итогах карьеры добавляет после статистики все дневники одной книгой. Сервис (Google Gemini или Anthropic Claude), модель и API-ключ
выбираются в ⚙ Настройках на стартовом экране. Ключ хранится только в вашем браузере (в версии для компьютера - в файле настроек в папке
`.football_career_sim`) и отправляется только выбранному сервису. Бесплатный ключ Gemini: aistudio.google.com -> Get API key.
Код: `game/story.py` (факты и задание), `web/llm.js` и `game/llm.py` (запросы к нейросетям), `game/ui/diary.py` (окна версии для компьютера).

**Лиги живут своей жизнью.** У каждого клуба бывают удачные и провальные сезоны, а время от времени один из сильнейших клубов лиги начинает
эпоху гегемонии на 5-10 сезонов (деньги и состав), после чего постепенно возвращается к своему обычному уровню. Гранды остаются грандами: в Испании
титул почти всегда берут Реал, Барселона или Атлетико, но кто из них - меняется. Настройки - в начале `game/world.py` (REVERT, HEG_*, FORM_SD, LEAD_*).

**Отбор в еврокубки.** Как в жизни, на общий этап сразу попадают не все. Лучшие клубы сильнейших лиг проходят напрямую, чемпионы небольших лиг
играют квалификацию Лиги чемпионов по «пути чемпионов» (1-й, 2-й, 3-й раунды и плей-офф), серебряные призёры лиг среднего уровня - по «пути
представителей лиг». Вылетевший из отбора Лиги чемпионов продолжает в квалификации Лиги Европы или Лиги конференций, вылетевший из отбора
Лиги Европы - в Лиге конференций, а проигравший в отборе Лиги конференций выбывает из еврокубков до следующего сезона. Распределение путёвок -
`EURO_ACCESS` в `game/world.py`.

## Награды
Золотой мяч, символическая сборная мира и лучший молодой игрок разыгрываются между вашим игроком и 60 звёздами мира
(на старте реальные: Мбаппе, Холанн, Ямаль и др.; потом они стареют, и появляются новые таланты). Учитываются голы и передачи
(с поправкой на уровень лиги), трофеи клуба и сборной и класс игрока. Высокий рейтинг без статистики и трофеев награду больше не даёт.
Символическая сборная лиги, игрок сезона и Золотая бутса зависят от средней оценки за сезон и голов в лиге.

## Что внутри
- `main.py`, `game/`: приложение (`world.py` лиги, кубки, континентальные турниры, сборные; `career.py` карьера; `stats.py` голы и оценки;
  `stars.py` звёзды мира; `player.py` рост и спад; `ui/` экраны для компьютера; `web/` экраны сайта).
- `data/football.db`, `assets/logos/`: база клубов и эмблемы (1214 клубов, 83 лиги, 211 стран; рейтинги команд из EA FC 27, у небольших лиг УЕФА ручная оценка по коэффициенту УЕФА).
- `database/`, `tools/`, `data/`, `docs/DATA_SOURCES.md`: сборка базы, импорт FC 27, Elo, рейтингов EA FC, докачка эмблем.
- `tests/`: `balance.py` (массовый прогон карьер), `test_ui_flow.py` (десктопный интерфейс без экрана), `test_web_flow.py` (веб-интерфейс без браузера),
  `test_diary_desktop.py` (дневник сезона в версии для компьютера, нейросеть заменена заглушкой), тесты импортёров.

## Честно об ограничениях
- **Клубы есть у 78 стран**: все 55 стран УЕФА, 10 стран КОНМЕБОЛ (Аргентина, Бразилия, Колумбия, Чили, Перу, Эквадор, Уругвай, Парагвай, Боливия,
  Венесуэла), Мексика, MLS (США и 3 клуба Канады), Япония, Саудовская Аравия, Южная Корея, Китай, ОАЭ, Катар, Таиланд, Индия и Австралия (с 2 клубами Новой Зеландии).
  Своя лига есть у 75 стран: клубы Канады, Новой Зеландии и Лихтенштейна играют в лигах соседей, а несколько клубов Уэльса и Андорры
  (Кардифф, Суонси, Рексем, Ньюпорт, «Андорра») - в английских и испанской лигах. Для остальных 133 стран академия берётся из запасной страны
  (`data/academy_fallback.csv`).
- **Многие клубы оценены вручную**: в EA FC 27 есть только часть из них. Из Колумбии, Чили, Перу, Эквадора, Уругвая, Парагвая, Боливии и Венесуэлы в FC 27
  только по 4-7 клубов, поэтому к ним добавлены известные клубы с ручной оценкой; лиги там короче настоящих (8-12 клубов), но за счёт лишних кругов
  число матчей близко к реальному (32-44). В Бразилии 6 клубов из 20 добавлены вручную. 24 небольшие лиги УЕФА (Албания, Армения, Прибалтика, Ирландия,
  Уэльс и другие) целиком оценены вручную по коэффициенту УЕФА, а в Венгрии, на Кипре, в Азербайджане и Финляндии из FC 27 только по 1-2 клуба.
  Составы этих лиг на сезон 2027 могли отличаться.
- **Мексика, Япония, ОАЭ, Катар и Таиланд** (добавлены в октябре 2026): составы на 2026/27 из английской Википедии (для Катара страницы 2026/27 ещё нет:
  состав выведен из 2025/26 с учётом вылета и повышения). Из EA FC 27 есть только Аль-Айн (71) и Бурирам (68), остальные клубы оценены вручную
  по лигам, которые уже есть в игре (`tools/asia_mexico_leagues.py`). Кубок Мексики в игре называется Copa MX, хотя настоящий Copa MX не проводится с 2020 года.
- **Нет клубов Африки** и многих других стран (Центральная Америка, Иран, Египет и другие). Кубок чемпионов КОНКАКАФ разыгрывают только клубы
  Мексики и MLS. Лига чемпионов АФК 2, клубные турниры Африки и Океании и клубный чемпионат мира есть в справочнике турниров, но в игре не разыгрываются.
- **Эмблем нет у 8 клубов**: резервные и молодёжные команды (Real Sociedad B, VfB Stuttgart II и др.), United Tigers, Juvenes/Dogana и Khor Fakkan. Вместо них рисуется круг с инициалами.
  Докачать: `python tools/fetch_logos.py data/football.db`.
- **Клубы звёзд на старте** (574 реальных игрока в `data/real_players.csv`) взяты по данным до лета 2026 года и с тех пор не перепроверялись: кто-то мог перейти в другой клуб.
- **Проверка**: веб-версию перед каждой публикацией автоматически проверяет `tests/test_web_flow.py` (полная карьера игрока и тренера, русский и английский);
  кроме того, она проверена вручную в браузере на ширине телефона и компьютера. Перед публикацией проверяется и синтаксис JavaScript.
  Работа без интернета проверена в Microsoft Edge (первый заход с интернетом, затем сеть отключена и игра открыта заново) и подтверждена на настоящем телефоне: без интернета игра открывается.
  У десктопного приложения (.exe) есть только автоматический тест без экрана (`tests/test_ui_flow.py`): если что-то выглядит криво или падает, пришлите скриншот или текст ошибки.
- Матчи не симулируются по минутам: результаты сезона считаются вероятностной моделью.

## Лицензия
© 2026 yukkennn. Код, интерфейс и игровая логика распространяются по лицензии
**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**, полный текст в файле [LICENSE](LICENSE),
кратко: https://creativecommons.org/licenses/by-nc/4.0/deed.ru

- **Можно** копировать, распространять и изменять проект, в том числе делать свою версию.
- **Обязательно** указывать автора (yukkennn), давать ссылку на этот репозиторий и лицензию и отмечать, что вы изменили.
- **Нельзя** использовать проект в коммерческих целях: продавать, брать плату за доступ, зарабатывать на рекламе.

**Чужие данные под эту лицензию не попадают.** Рейтинги клубов и игроков (EA SPORTS FC), эмблемы клубов, названия
клубов, турниров и имена реальных футболистов принадлежат их правообладателям и используются в некоммерческой фанатской игре.
Подробнее об источниках: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).
