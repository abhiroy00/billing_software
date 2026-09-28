import pytest

from database import connection
from database.base import Base
from services import auth_service


@pytest.fixture()
def db_session(tmp_path):
    db_path = tmp_path / "test.db"
    connection.init_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(connection.get_engine())
    with connection.get_session() as session:
        yield session


@pytest.fixture(autouse=True)
def _reset_current_session():
    auth_service.current_session.clear()
    yield
    auth_service.current_session.clear()
