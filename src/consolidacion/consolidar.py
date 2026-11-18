"""Entregable 1: vista consolidada de ingresos, gastos y margen."""
import numpy as np
import pandas as pd

from src.comun import mes_de


def consolidado_mensual(tiendas, ventas, gastos, nivel="tienda"):
    """Ingresos, gastos y margen por mes. nivel = 'tienda' o 'region'."""
    region = tiendas[["tienda", "region"]]
    v = ventas.assign(periodo=mes_de(ventas["fecha"])).merge(region, on="tienda", how="left")
    g = gastos.assign(periodo=mes_de(gastos["fecha"])).merge(region, on="tienda", how="left")
    v["region"] = v["region"].fillna("Sin región")
    g["region"] = g["region"].fillna("Sin región")

    claves = ["periodo", "tienda", "region"] if nivel == "tienda" else ["periodo", "region"]
    ingresos = v.groupby(claves, as_index=False)["venta"].sum().rename(columns={"venta": "ingresos"})
    egresos = g.groupby(claves, as_index=False)["monto"].sum().rename(columns={"monto": "gastos"})

    out = ingresos.merge(egresos, on=claves, how="outer")
    out[["ingresos", "gastos"]] = out[["ingresos", "gastos"]].fillna(0.0)
    out["margen"] = out["ingresos"] - out["gastos"]
    out["margen_pct"] = np.where(out["ingresos"] > 0, out["margen"] / out["ingresos"], np.nan)
    return out.sort_values(claves).reset_index(drop=True)


def gastos_por_categoria(tiendas, gastos, nivel="tienda"):
    """Gasto mensual separado por categoría."""
    region = tiendas[["tienda", "region"]]
    g = gastos.assign(periodo=mes_de(gastos["fecha"])).merge(region, on="tienda", how="left")
    claves = ["periodo", "tienda", "region", "categoria"] if nivel == "tienda" else ["periodo", "region", "categoria"]
    return g.groupby(claves, as_index=False)["monto"].sum()


def filtrar_periodo(df, desde=None, hasta=None, columna="periodo"):
    """Filtra por rango de periodos (inclusivo)."""
    if desde is not None:
        df = df[df[columna] >= pd.Timestamp(desde)]
    if hasta is not None:
        df = df[df[columna] <= pd.Timestamp(hasta)]
    return df


def verificar_cuadre(ventas, gastos, consolidado, tolerancia=0.01):
    """Comprueba que el consolidado cuadra con los datos de origen.

    Regresa un diccionario {revisión: (cuadra, diferencia)}.
    """
    dif_ing = float(consolidado["ingresos"].sum() - ventas["venta"].sum())
    dif_gas = float(consolidado["gastos"].sum() - gastos["monto"].sum())
    dif_mar = float(
        consolidado["margen"].sum()
        - (consolidado["ingresos"].sum() - consolidado["gastos"].sum())
    )
    return {
        "Ingresos del consolidado = ventas de origen": (abs(dif_ing) <= tolerancia, dif_ing),
        "Gastos del consolidado = gastos de origen": (abs(dif_gas) <= tolerancia, dif_gas),
        "Margen = ingresos - gastos": (abs(dif_mar) <= tolerancia, dif_mar),
    }
