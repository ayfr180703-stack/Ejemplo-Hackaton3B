"""Tablero del Reto 7. Correr desde la raíz del repositorio:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.alertas.alertas import generar_alertas
from src.comun import DATA, cargar_datos, validar_datos
from src.consolidacion.consolidar import (consolidado_mensual, filtrar_periodo,
                                          gastos_por_categoria, verificar_cuadre)
from src.proyeccion.proyeccion import ESCENARIOS, curva_historica, proyectar

st.set_page_config(page_title="Reto 7 · Control financiero por tienda", layout="wide")


@st.cache_data
def cargar(prefijo):
    tiendas, ventas, gastos, depositos = cargar_datos(DATA, prefijo)
    return tiendas, ventas, gastos, depositos


def dinero(x):
    return f"${x:,.0f}"


st.title("Control financiero y flujo de efectivo por tienda")
st.caption("Reto 7 · Datos de ejemplo (sintéticos) mientras no se cargue información real")

with st.sidebar:
    st.header("Filtros")
    prefijo = st.text_input("Prefijo de los archivos en data/", value="ejemplo_")
    try:
        tiendas, ventas, gastos, depositos = cargar(prefijo)
    except Exception as error:  # noqa: BLE001
        st.error(f"No se pudieron cargar los datos: {error}")
        st.stop()
    meses = sorted(consolidado_mensual(tiendas, ventas, gastos, "region")["periodo"].unique())
    desde, hasta = st.select_slider("Periodo", options=meses, value=(meses[max(0, len(meses) - 6)], meses[-1]),
                                    format_func=lambda m: pd.Timestamp(m).strftime("%Y-%m"))
    regiones = st.multiselect("Región", sorted(tiendas["region"].unique()), default=sorted(tiendas["region"].unique()))
    nivel = st.radio("Ver por", ["tienda", "region"], format_func=lambda x: "Tienda" if x == "tienda" else "Región")

tiendas_sel = tiendas[tiendas["region"].isin(regiones)]
ventas_sel = ventas[ventas["tienda"].isin(tiendas_sel["tienda"])]
gastos_sel = gastos[gastos["tienda"].isin(tiendas_sel["tienda"])]
depositos_sel = depositos[depositos["tienda"].isin(tiendas_sel["tienda"])]

tab1, tab2, tab3, tab4 = st.tabs(["Consolidado", "Alertas", "Proyección tienda nueva", "Cuadre y supuestos"])

# ---------------- Consolidado ----------------
with tab1:
    cons = filtrar_periodo(consolidado_mensual(tiendas_sel, ventas_sel, gastos_sel, nivel), desde, hasta)
    ing, gas = cons["ingresos"].sum(), cons["gastos"].sum()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ingresos", dinero(ing))
    c2.metric("Gastos", dinero(gas))
    c3.metric("Margen", dinero(ing - gas))
    c4.metric("Margen %", f"{(ing - gas) / ing:.1%}" if ing else "—")

    total = cons.groupby("periodo", as_index=False)[["ingresos", "gastos", "margen"]].sum()
    st.plotly_chart(px.bar(total.melt("periodo", value_vars=["ingresos", "gastos", "margen"]),
                           x="periodo", y="value", color="variable", barmode="group",
                           labels={"value": "Pesos", "periodo": "Mes", "variable": ""}),
                    width="stretch")

    clave = "tienda" if nivel == "tienda" else "region"
    resumen = cons.groupby(clave, as_index=False)[["ingresos", "gastos", "margen"]].sum()
    resumen["margen_pct"] = resumen["margen"] / resumen["ingresos"]
    st.subheader(f"Margen por {'tienda' if nivel == 'tienda' else 'región'} en el periodo")
    st.dataframe(resumen.sort_values("margen"), width="stretch", hide_index=True,
                 column_config={"ingresos": st.column_config.NumberColumn(format="$%.0f"),
                                "gastos": st.column_config.NumberColumn(format="$%.0f"),
                                "margen": st.column_config.NumberColumn(format="$%.0f"),
                                "margen_pct": st.column_config.NumberColumn("margen %", format="percent")})
    cat = filtrar_periodo(gastos_por_categoria(tiendas_sel, gastos_sel, "region"), desde, hasta)
    cat = cat.groupby("categoria", as_index=False)["monto"].sum()
    st.plotly_chart(px.pie(cat, names="categoria", values="monto", title="Gasto por categoría"),
                    width="stretch")

# ---------------- Alertas ----------------
with tab2:
    alertas = generar_alertas(tiendas_sel, ventas_sel, gastos_sel, depositos_sel)
    alertas = alertas[(alertas["periodo"] >= pd.Timestamp(desde)) & (alertas["periodo"] <= pd.Timestamp(hasta) + pd.offsets.MonthEnd(0))]
    a1, a2, a3 = st.columns(3)
    a1.metric("Alertas en el periodo", len(alertas))
    a2.metric("Severidad alta", int((alertas["severidad"] == "Alta").sum()))
    a3.metric("Monto en riesgo", dinero(alertas["monto_en_riesgo"].sum()))
    sev = st.multiselect("Severidad", ["Alta", "Media", "Baja"], default=["Alta", "Media", "Baja"])
    tipos = st.multiselect("Tipo", sorted(alertas["tipo"].unique()), default=sorted(alertas["tipo"].unique()))
    vista = alertas[alertas["severidad"].isin(sev) & alertas["tipo"].isin(tipos)].copy()
    vista["periodo"] = vista["periodo"].dt.strftime("%Y-%m-%d")
    st.dataframe(vista[["prioridad", "severidad", "tipo", "tienda", "region", "periodo", "monto_en_riesgo",
                        "motivo", "accion_sugerida"]], width="stretch", hide_index=True,
                 column_config={"monto_en_riesgo": st.column_config.NumberColumn("monto en riesgo", format="$%.0f")})
    st.download_button("Descargar alertas (CSV)", vista.to_csv(index=False).encode("utf-8-sig"), "alertas.csv", "text/csv")
    st.caption("Reglas: ver docs/supuestos.md. Cada alerta explica por qué se disparó.")

# ---------------- Proyección ----------------
with tab3:
    st.write("Se aplica la mediana de los primeros 12 meses de las tiendas ya abiertas a una tienda nueva.")
    p1, p2 = st.columns(2)
    inversion = p1.number_input("Inversión inicial (supuesto)", min_value=0, value=500_000, step=50_000)
    escenario = p2.selectbox("Escenario", list(ESCENARIOS), index=1)
    curva = curva_historica(tiendas, ventas, gastos)
    proy, res = proyectar(curva, inversion_inicial=inversion, **ESCENARIOS[escenario])
    m1, m2, m3 = st.columns(3)
    m1.metric("Mes en que el flujo mensual es positivo", res["mes_equilibrio"] or "No llega")
    m2.metric("Mes en que se recupera la inversión", res["mes_recuperacion"] or "No en 24 meses")
    m3.metric("Necesidad máxima de efectivo", dinero(res["necesidad_maxima_de_efectivo"]))
    todas = pd.concat([proyectar(curva, inversion_inicial=inversion, **k)[0].assign(escenario=n)
                       for n, k in ESCENARIOS.items()])
    st.plotly_chart(px.line(todas, x="mes_n", y="flujo_acumulado", color="escenario",
                            labels={"mes_n": "Mes de operación", "flujo_acumulado": "Flujo acumulado (pesos)"}),
                    width="stretch")
    st.dataframe(proy.round(0), width="stretch", hide_index=True)

# ---------------- Cuadre ----------------
with tab4:
    st.subheader("Validación de los datos")
    problemas = validar_datos(tiendas, ventas, gastos, depositos)
    if problemas:
        for p in problemas:
            st.warning(p)
    else:
        st.success("Los datos pasaron las validaciones básicas.")
    st.subheader("¿Cuadran las cifras entre vistas?")
    completo = consolidado_mensual(tiendas, ventas, gastos, nivel)
    for nombre, (ok, dif) in verificar_cuadre(ventas, gastos, completo).items():
        (st.success if ok else st.error)(f"{nombre}: {'cuadra' if ok else f'diferencia de {dif:,.2f}'}")
    st.subheader("Supuestos del equipo")
    ruta = Path(__file__).resolve().parent.parent / "docs" / "supuestos.md"
    st.markdown(ruta.read_text(encoding="utf-8") if ruta.exists() else "Falta docs/supuestos.md")
