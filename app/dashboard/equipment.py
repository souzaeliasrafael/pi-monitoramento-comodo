"""Cadastro persistente de equipamentos do cômodo."""

import pandas as pd
import streamlit as st

from app.presentation import number, localized_table
from app.services.equipment import add_equipment, list_equipment


def render_equipment(engine, settings, *, end=None, show_metrics=True):
    summary = st.container()
    st.subheader("Equipamentos do circuito", help="O disjuntor inteligente acompanha a potência total do circuito. O cadastro identifica as cargas; as leituras determinam o consumo. Os equipamentos entram em uso de forma dinâmica após o cadastro, preservando o histórico anterior.")
    st.caption(f"Já incluídas: {settings.lamp_count} lâmpadas LED de {number(settings.lamp_power_w)} W. Os cadastros abaixo são adicionais.")
    with st.form("equipment_form", clear_on_submit=False):
        name = st.text_input("Nome do equipamento", max_chars=100, placeholder="Ex.: luminária da mesa")
        left, right = st.columns(2)
        quantity = left.number_input("Quantidade", min_value=1, max_value=1000, value=1, step=1)
        power_text = right.text_input("Potência de cada unidade (W)", value="15,00", help="Informe a potência em watts, por exemplo 15,00 ou 100,50.")
        submitted = st.form_submit_button("Adicionar equipamento")
    if submitted:
        try:
            try:
                power = float(power_text.replace(".", "").replace(",", ".") if "," in power_text else power_text)
            except ValueError:
                raise ValueError("Informe uma potência numérica, por exemplo 15,00.") from None
            add_equipment(engine, name, quantity, power)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("Equipamento cadastrado. Será incluído no uso dinâmico do circuito nas próximas leituras.")
    equipment = list_equipment(engine)
    if end is not None:
        equipment = [row for row in equipment if row["active_from"] < end]
        st.caption("Equipamentos disponíveis até a data final, incluindo os cadastrados anteriormente e ainda ativos.")
    total = settings.lamp_count * settings.lamp_power_w + sum(row["quantity"] * row["power_w"] for row in equipment)
    if show_metrics:
        summary.metric("Potência total se todos estiverem ligados", f"{number(total)} W")
    rows = [{"Equipamento": "Lâmpadas LED já incluídas", "Quantidade": settings.lamp_count,
             "Potência por unidade (W)": settings.lamp_power_w, "Perfil": "Uso dinâmico", "Incluído em": "Histórico inicial"}]
    rows.extend({"Equipamento": row["name"], "Quantidade": row["quantity"], "Potência por unidade (W)": row["power_w"],
                 "Perfil": "Uso dinâmico", "Incluído em": row["active_from"].strftime("%d/%m/%Y %H:%M")}
                for row in equipment)
    st.table(localized_table(pd.DataFrame(rows)))
    st.caption("Os equipamentos entram nas próximas leituras do coletor; as previsões se ajustam conforme os novos dias completos ficam disponíveis.")
