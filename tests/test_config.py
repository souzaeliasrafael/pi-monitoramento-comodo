import pytest

from app.config import Settings, load_settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in Settings.__dataclass_fields__:
        monkeypatch.delenv(name.upper(), raising=False)


def test_defaults(tmp_path):
    config = load_settings(tmp_path / "missing.env")
    assert config == Settings()
    assert config.energy_price_kwh == 0.78938
    assert (config.temperature_min, config.temperature_max) == (18, 30)
    assert (config.humidity_min, config.humidity_max) == (40, 70)


def test_env_file_and_process_precedence(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("ENERGY_PRICE_KWH=1.25\nTEMPERATURE_MIN=19\n", encoding="utf-8")
    monkeypatch.setenv("ENERGY_PRICE_KWH", "1.50")
    settings = load_settings(path)
    assert settings.energy_price_kwh == 1.50
    assert settings.temperature_min == 19


@pytest.mark.parametrize("values", [
    {"simulation_interval_seconds": 0}, {"energy_price_kwh": -1},
    {"temperature_min": 31}, {"humidity_min": -1}, {"humidity_max": 101},
    {"humidity_min": 70}, {"energy_price_kwh": float("nan")},
    {"temperature_max": float("inf")}, {"database_url": "invalid"},
    {"database_url": "postgresql://localhost/db"}, {"database_url": "sqlite://"},
])
def test_invalid_settings(values):
    with pytest.raises(ValueError):
        Settings(**values)


def test_invalid_environment_number(tmp_path, monkeypatch):
    monkeypatch.setenv("ENERGY_PRICE_KWH", "abc")
    with pytest.raises(ValueError, match="ENERGY_PRICE_KWH"):
        load_settings(tmp_path / "missing.env")


def test_fractional_lighting_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("USAGE_HOURS_MIN", "8.5")
    monkeypatch.setenv("LAMP_COUNT", "2")
    config = load_settings(tmp_path / "missing.env")
    assert config.usage_hours_min == 8.5
    assert config.lamp_count == 2

