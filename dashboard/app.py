"""Tablero local de respaldo del Reto 7 (Streamlit). Desde la raíz del repositorio:
    streamlit run dashboard/app.py
El tablero principal del equipo es el de /frontend; este corre sin internet y
sirve de plan B para la demo. Todas las cifras salen de motor/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from motor.alertas import generar_alertas
from motor.comun import DATA, cargar_datos, validar_datos
from motor.conciliacion import (consolidado_mensual, filtrar_periodo, gastos_por_categoria, kpis, verificar_cuadre)
from motor.proyeccion import ESCENARIOS, calibrar_supuestos, curva_historica, proyectar_tienda_nueva

st.set_page_config(page_title="Reto 7 · Control financiero por tienda", layout="wide")


@st.cache_data
def cargar(prefijo):
    return cargar_datos(DATA, prefijo)


def dinero(x):
    return f"${x:,.0f}"


st.title("Control financiero y flujo de efectivo por tienda")
st.caption("Datos de ejemplo (sintéticos) mientras no se carguen los datos reales")

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

fin_periodo = pd.Timestamp(hasta) + pd.offsets.MonthEnd(0)
sel = tiendas[tiendas["region"].isin(regiones)]
ventas_s, gastos_s, depositos_s = (d[d["tienda"].isin(sel["tienda"])] for d in (ventas, gastos, depositos))

tab1, tab2, tab3, tab4 = st.tabs(["Consolidado", "Alertas", "Proyección tienda nueva", "Cuadre y supuestos"])

with tab1:
    k = {"ventas": 0, "gastos": 0, "margen": 0, "diferencia_efectivo": 0}
    for r in regiones:
        parcial = kpis(tiendas, ventas, gastos, depositos, region=r, desde=desde, hasta=fin_periodo)
        for clave in k:
            k[clave] += parcial[clave]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ventas", dinero(k["ventas"]))
    c2.metric("Gastos", dinero(k["gastos"]))
    c3.metric("Margen", dinero(k["margen"]), f"{k['margen'] / k['ventas']:.1%}" if k["ventas"] else None)
    c4.metric("Diferencia de efectivo", dinero(k["diferencia_efectivo"]), help="Venta del punto de venta menos depósitos")

    cons = filtrar_periodo(consolidado_mensual(sel, ventas_s, gastos_s, nivel), desde, hasta)
    total = cons.groupby("periodo", as_index=False)[["ingresos", "gastos", "margen"]].sum()
    st.plotly_chart(px.bar(total.melt("periodo", value_vars=["ingresos", "gastos", "margen"]), x="periodo", y="value",
                           color="variable", barmode="group", labels={"value": "Pesos", "periodo": "Mes", "variable": ""}),
                    width="stretch")
    clave = "tienda" if nivel == "tienda" else "region"
    resumen = cons.groupby(clave, as_index=False)[["ingresos", "gastos", "margen"]].sum()
    resumen["margen_pct"] = resumen["margen"] / resumen["ingresos"]
    st.subheader(f"Margen por {'tienda' if nivel == 'tienda' else 'región'} en el periodo")
    st.dataframe(resumen.sort_values("margen"), width="stretch", hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="$%.0f") for c in ["ingresos", "gastos", "margen"]}
                 | {"margen_pct": st.column_config.NumberColumn("margen %", format="percent")})
    cat = filtrar_periodo(gastos_por_categoria(sel, gastos_s, "region"), desde, hasta).groupby("categoria", as_index=False)["monto"].sum()
    st.plotly_chart(px.pie(cat, names="categoria", values="monto", title="Gasto por categoría"), width="stretch")

with tab2:
    al = generar_alertas(sel, ventas_s, gastos_s, depositos_s)
    al = al[(al["periodo"] >= pd.Timestamp(desde)) & (al["periodo"] <= fin_periodo)]
    a1, a2, a3 = st.columns(3)
    a1.metric("Alertas en el periodo", len(al))
    a2.metric("Críticas", int((al["severidad"] == "Crítica").sum()))
    a3.metric("Monto en riesgo", dinero(al["monto_en_riesgo"].sum()))
    sev = st.multiselect("Severidad", ["Crítica", "Alta", "Media"], default=["Crítica", "Alta", "Media"])
    vista = al[al["severidad"].isin(sev)].copy()
    vista["periodo"] = vista["periodo"].dt.strftime("%Y-%m-%d")
    st.dataframe(vista[["prioridad", "severidad", "tipo", "tienda", "region", "periodo", "monto_en_riesgo", "motivo", "accion_sugerida"]],
                 width="stretch", hide_index=True,
                 column_config={"monto_en_riesgo": st.column_config.NumberColumn("monto en riesgo", format="$%.0f")})
    st.download_button("Descargar alertas (CSV)", vista.to_csv(index=False).encode("utf-8-sig"), "alertas.csv", "text/csv")

with tab3:
    st.write("Los supuestos son editables. Los valores iniciales se calibran con las tiendas ya abiertas.")
    base = calibrar_supuestos(curva_historica(tiendas, ventas, gastos))
    p1, p2, p3 = st.columns(3)
    venta_inicial = p1.number_input("Venta del primer mes", value=int(base["venta_inicial"]), step=10_000)
    crecimiento = p2.number_input("Crecimiento mensual", value=round(base["crecimiento_mensual"], 3), step=0.005, format="%.3f")
    venta_madura = p3.number_input("Venta mensual madura (tope)", value=int(base["venta_madura"]), step=50_000)
    p4, p5, p6 = st.columns(3)
    margen_bruto = p4.number_input("Margen bruto", value=round(base["margen_bruto"], 3), step=0.005, format="%.3f")
    gastos_fijos = p5.number_input("Gastos fijos al mes", value=int(base["gastos_fijos"]), step=5_000)
    inversion = p6.number_input("Inversión inicial (supuesto)", value=5_500_000, step=100_000)
    horizonte = st.select_slider("Meses a proyectar", options=[12, 24, 36, 48, 60], value=48)
    escenario = st.selectbox("Escenario para el resumen", list(ESCENARIOS), index=1)

    def corre(factores):
        return proyectar_tienda_nueva(venta_inicial, crecimiento, margen_bruto, gastos_fijos, venta_madura,
                                      meses=horizonte, inversion_inicial=inversion, **factores)
    _, res = corre(ESCENARIOS[escenario])
    m1, m2, m3 = st.columns(3)
    m1.metric("Primer mes con resultado positivo", res["mes_equilibrio"] or "No llega")
    m2.metric("Mes en que se recupera la inversión", res["mes_recuperacion"] or f"No en {horizonte} meses")
    m3.metric("Necesidad máxima de efectivo", dinero(res["necesidad_maxima_de_efectivo"]))
    todas = pd.concat([corre(f)[0].assign(escenario=n) for n, f in ESCENARIOS.items()])
    st.plotly_chart(px.line(todas, x="mes_n", y="flujo_acumulado", color="escenario",
                            labels={"mes_n": "Mes de operación", "flujo_acumulado": "Flujo acumulado (pesos)"}), width="stretch")
    st.caption("Es una estimación con supuestos editables, no un pronóstico garantizado.")
    st.dataframe(corre(ESCENARIOS[escenario])[0].round(0), width="stretch", hide_index=True)

with tab4:
    st.subheader("Validación de los datos")
    problemas = validar_datos(tiendas, ventas, gastos, depositos)
    for p in problemas:
        st.warning(p)
    if not problemas:
        st.success("Los datos pasaron las validaciones básicas.")
    st.subheader("¿Cuadran las cifras entre vistas?")
    for nombre, (ok, dif) in verificar_cuadre(tiendas, ventas, gastos).items():
        (st.success if ok else st.error)(f"{nombre}: {'cuadra' if ok else f'diferencia de {dif:,.2f}'}")
    st.subheader("Supuestos del equipo")
    ruta = Path(__file__).resolve().parent.parent / "docs" / "supuestos.md"
    st.markdown(ruta.read_text(encoding="utf-8") if ruta.exists() else "Falta docs/supuestos.md")
