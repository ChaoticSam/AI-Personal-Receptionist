from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Add it to a .env file in the project root, for example:\n"
        "  DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@localhost:5432/DATABASE_NAME\n"
        "Then start PostgreSQL (or use your host’s connection string) and run the app again."
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # test connection before use; reconnects if DB restarted
    pool_recycle=1800,    # recycle connections every 30 min to avoid server-side timeouts
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()