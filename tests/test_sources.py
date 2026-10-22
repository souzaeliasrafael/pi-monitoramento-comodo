import pytest

from app.config import Settings
from app.data_sources.base import DataSource
from app.data_sources.factory import create_source


def test_contract():
    with pytest.raises(TypeError):
        DataSource()
    source = create_source(Settings())
    assert isinstance(source, DataSource)
    assert len(source.get_current_readings()) == 4


def test_tuya_is_explicitly_unavailable():
    source = create_source(Settings(data_source="tuya"))
    assert isinstance(source, DataSource)
    with pytest.raises(NotImplementedError, match="futura"):
        source.get_current_readings()


def test_credentials_are_not_exposed_or_used(monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError("Não deve acessar a rede.")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    settings = Settings(data_source="tuya", tuya_access_id="test-id", tuya_access_secret="test-secret")
    assert "test-secret" not in repr(settings)
    assert "test-id" not in repr(settings)
    with pytest.raises(NotImplementedError):
        create_source(settings).get_current_readings()
