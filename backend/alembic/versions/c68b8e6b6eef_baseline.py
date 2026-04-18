"""baseline

Revision ID: c68b8e6b6eef
Revises:
Create Date: 2026-04-18 18:10:26.234173

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c68b8e6b6eef"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("login", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column(
            "avatar", sa.String(30), nullable=False, server_default="nebula"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "lobby_statuses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
    )

    op.create_table(
        "games",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "config_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_table(
        "lobbies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "game_id", sa.Integer, sa.ForeignKey("games.id"), nullable=False
        ),
        sa.Column(
            "status_id",
            sa.Integer,
            sa.ForeignKey("lobby_statuses.id"),
            nullable=False,
        ),
        sa.Column(
            "created_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "max_players", sa.Integer, nullable=False, server_default="10"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "lobby_participants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "lobby_id",
            sa.Integer,
            sa.ForeignKey("lobbies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("lobby_id", "user_id"),
    )

    op.execute(
        """
        INSERT INTO lobby_statuses (code, name) VALUES
            ('waiting',     'Ожидание'),
            ('in_progress', 'Идёт игра'),
            ('finished',    'Завершено')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
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
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("lobby_participants")
    op.drop_table("lobbies")
    op.drop_table("games")
    op.drop_table("lobby_statuses")
    op.drop_table("users")
