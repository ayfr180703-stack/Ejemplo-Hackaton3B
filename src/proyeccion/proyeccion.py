"""Entregable 3: proyección simple del flujo de efectivo de una tienda nueva.

Método (explicable): se toma lo que pasó en los primeros 12 meses de las
tiendas ya abiertas (mediana por mes de operación) y se aplica a una tienda
nueva, con factores para armar escenarios.
"""
import numpy as np
import pandas as pd

from src.comun import CATEGORIA_COSTO, mes_de


def curva_historica(tiendas, ventas, gastos, max_mes=12, min_tiendas=3):
    """Mediana de venta, % de costo de mercancía y gasto operativo por mes de
    operación (1 = mes de apertura). Supone que las tiendas abren el día 1."""
    apertura = tiendas.set_index("tienda")["fecha_apertura"]
    v = (ventas.assign(mes=mes_de(ventas["fecha"])).groupby(["tienda", "mes"], as_index=False)["venta"].sum())
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


def proyectar(curva, inversion_inicial=500_000, factor_ventas=1.0, factor_gastos=1.0, horizonte=24):
    """Flujo mensual y acumulado de una tienda nueva.

    Después del mes 12 se supone que la tienda se mantiene como en el mes 12.
    inversion_inicial es un SUPUESTO (anotarlo en docs/supuestos.md)."""
    curva = curva[["mes_n", "ventas", "costo_pct", "opex"]].reset_index(drop=True)
    if horizonte > len(curva):
        extra = pd.DataFrame([curva.iloc[-1]] * (horizonte - len(curva))).reset_index(drop=True)
        extra["mes_n"] = np.arange(len(curva) + 1, horizonte + 1)
        curva = pd.concat([curva, extra], ignore_index=True)
    p = curva[["mes_n"]].copy()
    p["ventas"] = curva["ventas"] * factor_ventas
    p["costo_mercancia"] = p["ventas"] * curva["costo_pct"]
    p["gastos_operativos"] = curva["opex"] * factor_gastos
    p["flujo_mensual"] = p["ventas"] - p["costo_mercancia"] - p["gastos_operativos"]
    p["flujo_acumulado"] = p["flujo_mensual"].cumsum() - inversion_inicial

    positivos = p.loc[p["flujo_mensual"] > 0, "mes_n"]
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
