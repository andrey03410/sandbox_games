import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://gameuser:gamepass@localhost:5433/gamedb",
)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_TTL_HOURS = 24 * 7
