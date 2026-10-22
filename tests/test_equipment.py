from datetime import datetime

import pytest
from streamlit.testing.v1 import AppTest

from app.config import Settings
from app.database.connection import create_database_engine, initialize_database
from app.data_sources.factory import create_source
from app.services.equipment import add_equipment, list_equipment, equipment_load


def test_new_equipment_changes_live_source_without_retroactive_energy(tmp_path):
    settings = Settings(database_url="sqlite:///" + (tmp_path / "equipment.db").as_posix())
    engine = create_database_engine(settings)
    initialize_database(engine)
    source = create_source(settings, engine=engine)
    initial = datetime(2026, 10, 2, 7)
    activation = datetime(2026, 10, 2, 10, 30)
    end = datetime(2026, 10, 3)
    baseline = create_source(settings)
    source.get_current_readings(initial)
    baseline.get_current_readings(initial)
    add_equipment(engine, "Luminária", 2, 15, active_from=activation)
    before = source.get_current_readings(datetime(2026, 10, 2, 10))[-1]
    reference = baseline.get_current_readings(datetime(2026, 10, 2, 10))[-1]
    assert before == reference
    observed = source.get_current_readings(end)[-1]
    reference = baseline.get_current_readings(end)[-1]
    catalog = list_equipment(engine)
    _, extra = equipment_load(catalog,initial,end)
    assert extra > 0
    assert observed.energy_kwh-reference.energy_kwh == pytest.approx(extra)
    assert equipment_load(catalog,initial,activation)[1] == 0
    for args in [("Luminária",1,15),("",1,15),("Inválido",1,float("nan"))]:
        with pytest.raises(ValueError):
            add_equipment(engine,*args)
    assert len(list_equipment(engine))==1
    # Old persisted schedules cannot affect the new dynamic profile.
    for row in catalog:
        row.update(start_hour=22,duration_hours=3)
    assert equipment_load(catalog,initial,end)[1] == pytest.approx(extra)
    engine.dispose()


def equipment_app(url):
    from app.config import Settings
    from app.database.connection import create_database_engine, initialize_database
    from app.dashboard.equipment import render_equipment
    settings = Settings(database_url=url)
    engine = create_database_engine(settings)
    initialize_database(engine)
    render_equipment(engine, settings)
    engine.dispose()


def test_equipment_form_persists_and_rejects_duplicate(tmp_path):
    url = "sqlite:///" + (tmp_path / "form.db").as_posix()
    app = AppTest.from_function(equipment_app, args=(url,), default_timeout=30).run()
    assert not app.exception
    assert len(app.time_input) == 0
    app.text_input[0].set_value("Luminária de mesa")
    app.number_input[0].set_value(2)
    app.button[0].click().run()
    assert not app.exception
    assert app.success
    assert app.metric[0].value == "90,00 W"
    again = AppTest.from_function(equipment_app, args=(url,), default_timeout=30).run()
    assert again.metric[0].value == "90,00 W"
    again.text_input[0].set_value("Luminária de mesa")
    again.button[0].click().run()
    assert "Já existe" in again.error[0].value
