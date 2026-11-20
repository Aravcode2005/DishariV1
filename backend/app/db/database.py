"""Select optional PostgreSQL only when DATABASE_URL is explicitly configured."""
from app.db.repository import MemoryRepository, Repository


def create_repository(database_url: str | None) -> Repository:
    if not database_url:
        return MemoryRepository()
    # PostgreSQL dependencies are optional and never imported for default startup.
    from app.db.postgres import PostgresRepository
    return PostgresRepository(database_url)
