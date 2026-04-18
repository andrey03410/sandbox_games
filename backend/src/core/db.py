from sqlalchemy import create_engine

from src.core.settings import settings

engine = create_engine(settings.database_url)
