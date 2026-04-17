CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    login         VARCHAR(50)  NOT NULL UNIQUE,
    password_hash VARCHAR(200) NOT NULL,
    avatar        VARCHAR(30)  NOT NULL DEFAULT 'nebula',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

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
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    game_id     INTEGER      NOT NULL REFERENCES games(id),
    status_id   INTEGER      NOT NULL REFERENCES lobby_statuses(id),
    created_by  INTEGER      NOT NULL REFERENCES users(id),
    config      JSONB        NOT NULL DEFAULT '{}'::jsonb,
    max_players INTEGER      NOT NULL DEFAULT 10,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lobby_participants (
    id        SERIAL PRIMARY KEY,
    lobby_id  INTEGER     NOT NULL REFERENCES lobbies(id) ON DELETE CASCADE,
    user_id   INTEGER     NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    role      VARCHAR(20) NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (lobby_id, user_id)
);

INSERT INTO lobby_statuses (code, name) VALUES
    ('waiting',     'Ожидание'),
    ('in_progress', 'Идёт игра'),
    ('finished',    'Завершено')
ON CONFLICT (code) DO NOTHING;

INSERT INTO games (code, name, config_schema) VALUES
    ('tic_tac_toe', 'Крестики-нолики',
     '{
        "min_players": 2,
        "max_players": 2,
        "fields": [
            {"name": "field_width",  "type": "int", "label": "Ширина поля",      "default": 3, "min": 3, "max": 20},
            {"name": "field_height", "type": "int", "label": "Высота поля",      "default": 3, "min": 3, "max": 20},
            {"name": "win_line",     "type": "int", "label": "Линия для победы", "default": 3, "min": 3, "max": 20}
        ]
     }'::jsonb)
ON CONFLICT (code) DO NOTHING;
