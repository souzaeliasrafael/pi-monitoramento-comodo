from datetime import datetime, date

from streamlit.testing.v1 import AppTest

from app.config import Settings, PROJECT_ROOT
from app.database.connection import create_database_engine, initialize_database
from app.database.repository import Repository
from app.database.models import ForecastRecord
from app.services.equipment import add_equipment
from app.services.ingestion import generate_history
from app.presentation import number


def test_dashboard_empty_and_populated(tmp_path, monkeypatch):
    url = "sqlite:///" + (tmp_path / "dashboard.db").as_posix()
    monkeypatch.setenv("DATABASE_URL", url)
    app = AppTest.from_file(str(PROJECT_ROOT / "app/dashboard/app.py"), default_timeout=30).run()
    assert not app.exception
    assert any("Banco vazio" in item.value for item in app.info)
    engine = create_database_engine(Settings(database_url=url))
    initialize_database(engine)
    generate_history(Repository(engine), datetime(2026, 1, 1), 2)
    with engine.begin() as connection:
        for day, prediction in [(1, 0.5), (2, 0.2)]:
            connection.execute(ForecastRecord.__table__.insert().values(
                issued_at=datetime(2025, 12, 31), training_end=datetime(2025, 12, 30),
                target=datetime(2026, 1, day), prediction=prediction, spread=0.1,
                actual=0.3, evaluated_at=datetime(2026, 1, 3), origin="test"))
    add_equipment(engine, "Anterior", 1, 10, active_from=datetime(2025, 12, 31))
    add_equipment(engine, "Posterior", 1, 20, active_from=datetime(2026, 1, 2))
    app.run()
    assert not app.exception
    assert not app.error
    assert len(app.metric) == 18
    assert len(app.tabs) == 0
    assert len(app.sidebar.date_input) == 0
    assert app.sidebar.radio[0].options == ["Resumo Executivo", "Ambiente e histórico", "Energia", "Alertas", "Previsão energética", "Equipamentos"]
    assert not any("Iluminação inicial:" in item.value for item in app.caption)
    total = Repository(engine).latest("energy_meter_01")["energy_kwh"]
    first_day = Repository(engine).query(end=datetime(2026, 1, 2), device_id="energy_meter_01")[-1]["energy_kwh"]
    assert app.metric[2].value == f"{number(total)} kWh"
    app.date_input[1].set_value(date(2026, 1, 1)).run()
    assert not app.exception
    assert app.metric[2].value == f"{number(first_day)} kWh"
    assert app.metric[12].value == f"R$ {number(first_day * Settings().energy_price_kwh)}"
    assert "período" in app.metric[0].label
    app.selectbox[0].select("sensor_02").run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Energia").run()
    assert not app.exception and not app.error
    assert len(app.metric) == 0
    assert app.selectbox[0].value == "sensor_02"
    app.sidebar.radio[0].set_value("Resumo Executivo").run()
    assert app.metric[2].value == "—"
    assert app.metric[9].value == "—"
    app.selectbox[0].select("Todos").run()
    assert app.metric[2].value == f"{number(first_day)} kWh"
    app.sidebar.radio[0].set_value("Alertas").run()
    assert not app.exception and not app.error
    assert len(app.metric) == 0
    assert any(item.value == "Ocorrências" for item in app.subheader)
    app.sidebar.radio[0].set_value("Previsão energética").run()
    assert not app.exception and not app.error
    assert len(app.date_input) == 2
    assert app.date_input[1].value == date(2026, 1, 1)
    assert any(item.value == "Previsão energética" for item in app.subheader)
    assert len(app.metric) == 0
    app.sidebar.radio[0].set_value("Resumo Executivo").run()
    assert app.metric[9].value == "0,50 kWh"
    assert app.metric[15].value == "0,20 kWh/dia"
    app.date_input[1].set_value(date(2026, 1, 2)).run()
    assert app.metric[9].value == "0,70 kWh"
    assert app.metric[15].value == "0,15 kWh/dia"
    app.date_input[1].set_value(date(2026, 1, 1)).run()
    app.sidebar.radio[0].set_value("Equipamentos").run()
    assert not app.exception and not app.error
    assert len(app.metric) == 0
    assert app.date_input[1].value == date(2026, 1, 1)
    app.sidebar.radio[0].set_value("Resumo Executivo").run()
    assert app.metric[17].value == "70,00 W"
    app.date_input[1].set_value(date(2026, 1, 2)).run()
    assert app.metric[17].value == "90,00 W"
    app.sidebar.radio[0].set_value("Ambiente e histórico").run()
    assert app.date_input[1].value == date(2026, 1, 2)
    assert len(app.metric) == 0
    app.sidebar.radio[0].set_value("Resumo Executivo").run()
    assert app.metric[2].value == f"{number(total)} kWh"
    engine.dispose()
