PRAGMA foreign_keys = ON;

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE confederations (
  code TEXT PRIMARY KEY,            -- UEFA, CAF, AFC, CONMEBOL, CONCACAF, OFC
  name_en TEXT NOT NULL, name_ru TEXT NOT NULL
);

-- 211 членов FIFA (Англия/Шотландия/Уэльс/Сев. Ирландия отдельно)
CREATE TABLE countries (
  fifa_code TEXT PRIMARY KEY,       -- ENG, KAZ, ...
  iso2 TEXT NOT NULL,               -- для флагов (GB-ENG и т.п.)
  name_en TEXT NOT NULL,
  name_ru TEXT NOT NULL,
  confederation TEXT NOT NULL REFERENCES confederations(code),
  uefa_coeff_5y REAL,               -- только UEFA, пополняется из data/
  league_strength REAL,             -- 0..100, см. build_db.py
  fallback_academy_country TEXT REFERENCES countries(fifa_code)  -- если в стране нет клубов
);

CREATE TABLE leagues (
  league_id TEXT PRIMARY KEY,       -- eng-premier-league
  country_code TEXT NOT NULL REFERENCES countries(fifa_code),
  name TEXT NOT NULL,
  tier INTEGER NOT NULL DEFAULT 1,  -- 1 = высший дивизион
  n_clubs INTEGER,
  source TEXT NOT NULL,             -- откуда взята запись
  rounds INTEGER NOT NULL DEFAULT 2 -- сколько раз встречаются две команды (MLS и Аргентина: 1)
);

CREATE TABLE clubs (
  club_id TEXT PRIMARY KEY,         -- eng-arsenal-fc
  name TEXT NOT NULL,
  country_code TEXT NOT NULL REFERENCES countries(fifa_code),
  league_id TEXT REFERENCES leagues(league_id),
  city TEXT, stadium TEXT, founded INTEGER,
  is_reserve INTEGER NOT NULL DEFAULT 0,  -- фарм-клуб (B-команда): в предложениях трансфера не участвует
  logo_path TEXT,                   -- относительный путь в assets/logos
  stars REAL,                       -- 0.5..5.0, считает recompute_stars.py
  star_score REAL,                  -- 0..100
  strength_quality TEXT,            -- 'elo' | 'club_signals' | 'manual_seed' | 'league_only'
  source TEXT NOT NULL
);
CREATE INDEX idx_clubs_country ON clubs(country_code);
CREATE INDEX idx_clubs_league ON clubs(league_id);

CREATE TABLE club_aliases (
  alias TEXT NOT NULL,
  club_id TEXT NOT NULL REFERENCES clubs(club_id),
  source TEXT NOT NULL,
  PRIMARY KEY (alias, club_id)
);
CREATE INDEX idx_alias ON club_aliases(alias COLLATE NOCASE);

-- Сырые сигналы силы из разных источников; звёзды пересчитываются из них
CREATE TABLE club_signals (
  club_id TEXT NOT NULL REFERENCES clubs(club_id),
  signal TEXT NOT NULL,             -- ea_team_ovr (FC 27) | clubelo | ovr_estimate | uefa_club_coeff | manual_stars | top_flight_seasons
  value REAL NOT NULL,
  as_of TEXT,
  PRIMARY KEY (club_id, signal)
);

-- Сезоны, когда клуб был в высшем дивизионе (из истории эмблем по сезонам)
CREATE TABLE club_top_flight_history (
  club_id TEXT NOT NULL REFERENCES clubs(club_id),
  season TEXT NOT NULL,             -- 2024-25
  PRIMARY KEY (club_id, season)
);

CREATE TABLE competitions (
  code TEXT PRIMARY KEY,
  name_en TEXT NOT NULL, name_ru TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('club','national')),
  confederation TEXT REFERENCES confederations(code),
  tier INTEGER NOT NULL,
  cycle_years INTEGER NOT NULL,
  next_edition_year INTEGER NOT NULL,
  note TEXT
);

-- Задел под будущее: зарплаты пока не используются (решение: без зарплат)
-- Журнал карьеры (пишет движок сезонов, этап 2)
CREATE TABLE career_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  save_id INTEGER NOT NULL,
  season TEXT NOT NULL,
  age INTEGER NOT NULL,
  event_type TEXT NOT NULL,         -- season | transfer | loan | trophy | award | injury | retire
  club_id TEXT REFERENCES clubs(club_id),
  payload_json TEXT NOT NULL
);

CREATE VIEW v_country_coverage AS
SELECT c.fifa_code, c.name_en, c.confederation,
       (SELECT COUNT(*) FROM clubs k WHERE k.country_code = c.fifa_code) AS n_clubs
FROM countries c;
