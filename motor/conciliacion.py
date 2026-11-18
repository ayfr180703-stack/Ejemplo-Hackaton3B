"""Consolidación de ingresos, gastos y margen, y conciliación de efectivo
(venta del punto de venta contra depósito bancario).

Todas son funciones puras: reciben tablas y regresan tablas. Ninguna cifra del
tablero debe salir de otro lugar que no sea este módulo.
"""
import numpy as np
import pandas as pd

from motor.comun import mes_de


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


def conciliacion_diaria(ventas, depositos):
    """Venta - depósito por tienda y día, con la diferencia acumulada."""
    d = ventas.merge(depositos, on=["tienda", "fecha"], how="outer")
    d[["venta", "deposito"]] = d[["venta", "deposito"]].fillna(0.0)
    d = d.sort_values(["tienda", "fecha"]).reset_index(drop=True)
    d["diferencia"] = d["venta"] - d["deposito"]
    d["diferencia_acumulada"] = d.groupby("tienda")["diferencia"].cumsum()
    return d


def conciliacion_semanal(tiendas, ventas, depositos):
    """Venta - depósito por tienda y semana (lunes a domingo).

    Se concilia por semana para no alertar por depósitos que se hacen al día
    siguiente."""
    d = conciliacion_diaria(ventas, depositos)
    d["semana"] = d["fecha"].dt.to_period("W-SUN").dt.start_time
    s = d.groupby(["tienda", "semana"], as_index=False)[["venta", "deposito", "diferencia"]].sum()
    s = s.merge(tiendas[["tienda", "region"]], on="tienda", how="left")
    s["diferencia_pct"] = np.where(s["venta"] > 0, s["diferencia"] / s["venta"], np.nan)
    return s


def kpis(tiendas, ventas, gastos, depositos, region=None, tienda=None, desde=None, hasta=None):
    """Las cuatro tarjetas del tablero: ventas, gastos, margen y diferencia de efectivo."""
    sel = tiendas
    if region:
        sel = sel[sel["region"] == region]
    if tienda:
        sel = sel[sel["tienda"] == tienda]
    claves = set(sel["tienda"])

    def recorta(df, col="fecha"):
        df = df[df["tienda"].isin(claves)]
        if desde is not None:
            df = df[df[col] >= pd.Timestamp(desde)]
        if hasta is not None:
            df = df[df[col] <= pd.Timestamp(hasta)]
        return df

    v, g, d = recorta(ventas), recorta(gastos), recorta(depositos)
    total_v, total_g, total_d = float(v["venta"].sum()), float(g["monto"].sum()), float(d["deposito"].sum())
    return {
        "ventas": total_v,
        "gastos": total_g,
        "margen": total_v - total_g,
        "margen_pct": (total_v - total_g) / total_v if total_v else None,
        "depositos": total_d,
        "diferencia_efectivo": total_v - total_d,
        "diferencia_efectivo_pct": (total_v - total_d) / total_v if total_v else None,
        "tiendas": len(claves),
    }


def verificar_cuadre(tiendas, ventas, gastos, tolerancia=0.01):
    """Comprueba que todas las vistas dan el mismo total que los datos de origen.

    Regresa {revisión: (cuadra, diferencia)}."""
    por_tienda = consolidado_mensual(tiendas, ventas, gastos, "tienda")
    por_region = consolidado_mensual(tiendas, ventas, gastos, "region")
    revisiones = {
        "Ingresos por tienda = ventas de origen": por_tienda["ingresos"].sum() - ventas["venta"].sum(),
        "Gastos por tienda = gastos de origen": por_tienda["gastos"].sum() - gastos["monto"].sum(),
        "Ingresos por región = ingresos por tienda": por_region["ingresos"].sum() - por_tienda["ingresos"].sum(),
        "Gastos por región = gastos por tienda": por_region["gastos"].sum() - por_tienda["gastos"].sum(),
        "Margen = ingresos - gastos": por_tienda["margen"].sum() - (por_tienda["ingresos"].sum() - por_tienda["gastos"].sum()),
    }
    return {nombre: (abs(float(dif)) <= tolerancia, float(dif)) for nombre, dif in revisiones.items()}


def auditar_tienda(tienda, mes, ventas, gastos, depositos):
    """Recalcula desde los datos crudos las cifras de una tienda y un mes.

    Sirve para la auditoría a mano antes de la demo: estas cifras deben
    coincidir al centavo con lo que muestra el tablero."""
    mes = pd.Timestamp(mes)
    fin = mes + pd.offsets.MonthEnd(0)
    v = ventas[(ventas["tienda"] == tienda) & (ventas["fecha"] >= mes) & (ventas["fecha"] <= fin)]
    g = gastos[(gastos["tienda"] == tienda) & (gastos["fecha"] >= mes) & (gastos["fecha"] <= fin)]
    d = depositos[(depositos["tienda"] == tienda) & (depositos["fecha"] >= mes) & (depositos["fecha"] <= fin)]
    ventas_mes, gastos_mes, depositos_mes = float(v["venta"].sum()), float(g["monto"].sum()), float(d["deposito"].sum())
    return {
        "tienda": tienda, "mes": mes.strftime("%Y-%m"),
        "ventas": ventas_mes, "gastos": gastos_mes, "margen": ventas_mes - gastos_mes,
        "depositos": depositos_mes, "diferencia_efectivo": ventas_mes - depositos_mes,
    }
