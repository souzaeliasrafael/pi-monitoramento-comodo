"""Criação explícita do engine e inicialização idempotente do banco."""

from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from app.config import PROJECT_ROOT, Settings, load_settings
from app.database.models import Base


def create_database_engine(
    settings: Settings | None = None, *, base_dir: Path = PROJECT_ROOT,
) -> Engine:
    """Resolve caminhos relativos na raiz do projeto, independente do diretório atual."""
    url = make_url((settings or load_settings()).database_url)
    if url.database != ":memory:":
        path = Path(url.database)
        if not path.is_absolute():
            path = base_dir / path
        path = path.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        url = url.set(database=str(path))
    return create_engine(url)


def initialize_database(engine: Engine) -> None:
    """Abre/cria o arquivo SQLite e cria as tabelas que estiverem registradas."""
    with engine.begin() as connection:
        connection.execute(text("SELECT 1"))
        Base.metadata.create_all(connection)

