"""Proyección simple del flujo de efectivo de una tienda nueva.

Modelo (explicable y con supuestos editables):
    venta del mes m   = venta_inicial x (1 + crecimiento) ^ (m - 1)   (con tope opcional)
    resultado del mes = venta x margen_bruto - gastos_fijos
    flujo acumulado   = suma de resultados - inversión inicial
El punto de equilibrio mensual es el primer mes con resultado positivo.

Es una estimación con supuestos, no un pronóstico garantizado.
"""
import numpy as np
import pandas as pd

from motor.comun import CATEGORIA_COSTO, mes_de


def curva_historica(tiendas, ventas, gastos, max_mes=12, min_tiendas=3):
    """Mediana de venta, % de costo de mercancía y gasto operativo por mes de
    operación (1 = mes de apertura) de las tiendas ya abiertas.

    Supone que las tiendas abren el día 1 de un mes."""
    apertura = tiendas.set_index("tienda")["fecha_apertura"]
    v = ventas.assign(mes=mes_de(ventas["fecha"])).groupby(["tienda", "mes"], as_index=False)["venta"].sum()
    g = gastos.assign(mes=mes_de(gastos["fecha"]))
    costo = (g[g["categoria"] == CATEGORIA_COSTO].groupby(["tienda", "mes"], as_index=False)["monto"].sum()
             .rename(columns={"monto": "costo"}))
    opex = (g[g["categoria"] != CATEGORIA_COSTO].groupby(["tienda", "mes"], as_index=False)["monto"].sum()
            .rename(columns={"monto": "opex"}))
    t = v.merge(costo, on=["tienda", "mes"], how="left").merge(opex, on=["tienda", "mes"], how="left")
    t = t.fillna({"costo": 0.0, "opex": 0.0})
    ap = t["tienda"].map(apertura)
    t["mes_n"] = (t["mes"].dt.year - ap.dt.year) * 12 + (t["mes"].dt.month - ap.dt.month) + 1
    t = t[(t["mes_n"] >= 1) & (t["mes_n"] <= max_mes) & (t["venta"] > 0)].copy()
    t["costo_pct"] = t["costo"] / t["venta"]

    curva = t.groupby("mes_n").agg(
        ventas=("venta", "median"), costo_pct=("costo_pct", "median"),
        opex=("opex", "median"), n_tiendas=("tienda", "nunique"))
    curva = curva.reindex(range(1, max_mes + 1))
    pocas = curva["n_tiendas"].fillna(0) < min_tiendas
    curva.loc[pocas, ["ventas", "costo_pct", "opex"]] = np.nan
    curva[["ventas", "costo_pct", "opex"]] = curva[["ventas", "costo_pct", "opex"]].ffill()
    return curva.reset_index()


def calibrar_supuestos(curva):
    """Propone supuestos iniciales a partir de las tiendas ya abiertas.

    El equipo puede cambiarlos; los valores finales van en docs/supuestos.md."""
    ventas = curva["ventas"].to_numpy()
    meses_crecimiento = min(5, len(ventas) - 1)
    crecimiento = (ventas[meses_crecimiento] / ventas[0]) ** (1 / meses_crecimiento) - 1
    return {
        "venta_inicial": float(ventas[0]),
        "crecimiento_mensual": float(crecimiento),
        "venta_madura": float(ventas[-1]),
        "margen_bruto": float(1 - curva["costo_pct"].mean()),
        "gastos_fijos": float(curva["opex"].mean()),
    }


def proyectar_tienda_nueva(venta_inicial, crecimiento_mensual, margen_bruto, gastos_fijos,
                           venta_madura=None, meses=36, inversion_inicial=0.0,
                           factor_ventas=1.0, factor_gastos=1.0):
    """Flujo mensual y acumulado de una tienda nueva. Regresa (tabla, resumen)."""
    m = np.arange(1, meses + 1)
    ventas = venta_inicial * (1 + crecimiento_mensual) ** (m - 1)
    if venta_madura is not None:
        ventas = np.minimum(ventas, venta_madura)
    ventas = ventas * factor_ventas
    fijos = np.full(meses, gastos_fijos * factor_gastos, dtype=float)

    p = pd.DataFrame({"mes_n": m, "ventas": ventas})
    p["margen_bruto_pesos"] = p["ventas"] * margen_bruto
    p["gastos_fijos"] = fijos
    p["resultado_mensual"] = p["margen_bruto_pesos"] - p["gastos_fijos"]
    p["flujo_acumulado"] = p["resultado_mensual"].cumsum() - inversion_inicial

    positivos = p.loc[p["resultado_mensual"] > 0, "mes_n"]
    recuperada = p.loc[p["flujo_acumulado"] >= 0, "mes_n"]
    resumen = {
        "mes_equilibrio": int(positivos.iloc[0]) if len(positivos) else None,
        "mes_recuperacion": int(recuperada.iloc[0]) if len(recuperada) else None,
        "necesidad_maxima_de_efectivo": float(-min(p["flujo_acumulado"].min(), 0)),
        "flujo_acumulado_final": float(p["flujo_acumulado"].iloc[-1]),
    }
    return p, resumen


ESCENARIOS = {
    "Pesimista": {"factor_ventas": 0.85, "factor_gastos": 1.05},
    "Base": {"factor_ventas": 1.00, "factor_gastos": 1.00},
    "Optimista": {"factor_ventas": 1.10, "factor_gastos": 0.98},
}
