CREATE TABLE IF NOT EXISTS lobby_statuses (
    id   SERIAL PRIMARY KEY,
    code VARCHAR(30)  NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS games (
    id            SERIAL PRIMARY KEY,
    code          VARCHAR(50)  NOT NULL UNIQUE,
    name          VARCHAR(100) NOT NULL,
    config_schema JSONB        NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS lobbies (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    game_id       INTEGER      NOT NULL REFERENCES games(id),
    status_id     INTEGER      NOT NULL REFERENCES lobby_statuses(id),
    config        JSONB        NOT NULL DEFAULT '{}'::jsonb,
    players_count INTEGER      NOT NULL DEFAULT 0,
    max_players   INTEGER      NOT NULL DEFAULT 10
);

INSERT INTO lobby_statuses (code, name) VALUES
    ('waiting',     'Ожидание'),
    ('in_progress', 'Идёт игра'),
    ('finished',    'Завершено')
ON CONFLICT (code) DO NOTHING;

INSERT INTO games (code, name, config_schema) VALUES
    ('tic_tac_toe', 'Крестики-нолики',
     '{
        "fields": [
            {"name": "field_width",  "type": "int", "label": "Ширина поля",      "default": 3, "min": 3, "max": 20},
            {"name": "field_height", "type": "int", "label": "Высота поля",      "default": 3, "min": 3, "max": 20},
            {"name": "win_line",     "type": "int", "label": "Линия для победы", "default": 3, "min": 3, "max": 20}
        ]
     }'::jsonb)
ON CONFLICT (code) DO NOTHING;
