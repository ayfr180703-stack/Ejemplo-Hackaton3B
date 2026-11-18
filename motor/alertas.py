"""Reglas de alerta simples y explicables, con severidad y acción sugerida.

Cada alerta dice qué regla la activó y con qué cifras. No hay cajas negras.

Reglas (los umbrales están como parámetros y en docs/supuestos.md):
  1. Efectivo: la diferencia venta - depósito de la semana supera 0.5% de la
     venta. Crítica si además supera $5,000; si no, media.
  2. Gasto atípico: el gasto de una categoría supera en más de 25% tanto el
     promedio móvil de 3 meses de la misma tienda como la mediana de tiendas
     del mismo formato y región. Se exigen las dos para reducir falsas alarmas.
  3. Costo de mercancía alto: como % de la venta supera por 3 puntos o más la
     mediana de su región.
  4. Tienda nueva bajo proyección: la venta del mes está 10% o más por debajo
     de su proyección (su venta del primer mes x el crecimiento típico de las
     tiendas ya abiertas). Alta si la diferencia llega a 20%.
"""
import numpy as np
import pandas as pd

from motor.acciones import TIPO_COSTO, TIPO_EFECTIVO, TIPO_GASTO, TIPO_NUEVA, accion_para
from motor.comun import CATEGORIA_COSTO, mes_de
from motor.conciliacion import conciliacion_semanal

SEVERIDADES = ["Crítica", "Alta", "Media"]
COLUMNAS_ALERTA = [
    "tipo", "tienda", "region", "periodo", "categoria", "valor", "referencia",
    "desviacion_pct", "monto_en_riesgo", "severidad", "motivo", "accion_sugerida",
]


def _dinero(x):
    return f"${x:,.0f}"


def _vacia():
    return pd.DataFrame(columns=COLUMNAS_ALERTA)


# ---------------------------------------------------------------- efectivo
def alertas_efectivo(tiendas, ventas, depositos, umbral_pct=0.005, monto_critico=5000):
    s = conciliacion_semanal(tiendas, ventas, depositos)
    s = s[(s["venta"] > 0) & (s["diferencia"].abs() > umbral_pct * s["venta"])]
    if s.empty:
        return _vacia()
    filas = []
    for r in s.itertuples():
        monto = abs(r.diferencia)
        falta = r.diferencia > 0
        filas.append({
            "tipo": TIPO_EFECTIVO, "tienda": r.tienda, "region": r.region, "periodo": r.semana,
            "categoria": "efectivo", "valor": r.diferencia, "referencia": 0.0,
            "desviacion_pct": r.diferencia / r.venta, "monto_en_riesgo": monto,
            "severidad": "Crítica" if monto > monto_critico else "Media",
            "motivo": (f"Semana del {r.semana:%Y-%m-%d}: venta {_dinero(r.venta)} y depósitos {_dinero(r.deposito)}; "
                       f"{'faltan' if falta else 'sobran'} {_dinero(monto)} ({monto / r.venta:.1%} de la venta, "
                       f"umbral {umbral_pct:.1%})."),
            "accion_sugerida": accion_para(TIPO_EFECTIVO, r.tienda, monto, falta=falta),
        })
    return pd.DataFrame(filas, columns=COLUMNAS_ALERTA)


# ------------------------------------------------------------ gasto atípico
def alertas_gasto_atipico(tiendas, gastos, ventana=3, umbral=0.25, monto_min=3000,
                          umbral_critico=1.0, monto_critico=10000, monto_alta=10000, min_pares=3):
    t = tiendas[["tienda", "region", "formato"]]
    g = gastos[gastos["categoria"] != CATEGORIA_COSTO].copy()
    g["mes"] = mes_de(g["fecha"])
    m = (g.groupby(["tienda", "categoria", "mes"], as_index=False)["monto"].sum()
           .merge(t, on="tienda", how="left")
           .sort_values(["tienda", "categoria", "mes"]))
    m["ref_prom"] = m.groupby(["tienda", "categoria"])["monto"].transform(
        lambda s: s.shift(1).rolling(ventana, min_periods=ventana).mean())
    por_formato = m.groupby(["region", "formato", "categoria", "mes"])["monto"].transform("median")
    n_formato = m.groupby(["region", "formato", "categoria", "mes"])["monto"].transform("count")
    por_region = m.groupby(["region", "categoria", "mes"])["monto"].transform("median")
    m["ref_pares"] = np.where(n_formato >= min_pares, por_formato, por_region)
    m["grupo_pares"] = np.where(n_formato >= min_pares, "mismo formato y región", "misma región")

    m["referencia"] = m[["ref_prom", "ref_pares"]].max(axis=1)
    sobre_ambas = (m["monto"] > m["ref_prom"] * (1 + umbral)) & (m["monto"] > m["ref_pares"] * (1 + umbral))
    m = m[sobre_ambas & (m["monto"] - m["referencia"] >= monto_min)].copy()
    if m.empty:
        return _vacia()

    filas = []
    for r in m.itertuples():
        riesgo = r.monto - r.referencia
        desv = r.monto / r.referencia - 1
        if desv >= umbral_critico and riesgo >= monto_critico:
            sev = "Crítica"
        elif riesgo >= monto_alta:
            sev = "Alta"
        else:
            sev = "Media"
        filas.append({
            "tipo": TIPO_GASTO, "tienda": r.tienda, "region": r.region, "periodo": r.mes,
            "categoria": r.categoria, "valor": r.monto, "referencia": r.referencia,
            "desviacion_pct": desv, "monto_en_riesgo": riesgo, "severidad": sev,
            "motivo": (f"{r.categoria} de {r.mes:%Y-%m}: {_dinero(r.monto)}. Promedio de sus últimos {ventana} meses: "
                       f"{_dinero(r.ref_prom)} (+{r.monto / r.ref_prom - 1:.0%}); mediana de tiendas de {r.grupo_pares}: "
                       f"{_dinero(r.ref_pares)} (+{r.monto / r.ref_pares - 1:.0%}). Umbral: más de {umbral:.0%} sobre ambos."),
            "accion_sugerida": accion_para(TIPO_GASTO, r.tienda, riesgo, categoria=r.categoria, periodo=r.mes),
        })
    return pd.DataFrame(filas, columns=COLUMNAS_ALERTA)


# ------------------------------------------------------ costo de mercancía
def alertas_costo_mercancia(tiendas, ventas, gastos, umbral_pts=0.03, monto_min=5000, monto_alta=30000):
    region = tiendas[["tienda", "region"]]
    v = ventas.assign(mes=mes_de(ventas["fecha"])).groupby(["tienda", "mes"], as_index=False)["venta"].sum()
    c = gastos[gastos["categoria"] == CATEGORIA_COSTO].copy()
    if c.empty:
        return _vacia()
    c["mes"] = mes_de(c["fecha"])
    c = c.groupby(["tienda", "mes"], as_index=False)["monto"].sum()
    t = v.merge(c, on=["tienda", "mes"], how="inner").merge(region, on="tienda", how="left")
    t = t[t["venta"] > 0].copy()
    t["pct"] = t["monto"] / t["venta"]
    t["ref_pct"] = t.groupby(["region", "mes"])["pct"].transform("median")
    t["exceso"] = (t["pct"] - t["ref_pct"]) * t["venta"]
    t = t[((t["pct"] - t["ref_pct"]) >= umbral_pts) & (t["exceso"] >= monto_min)]
    if t.empty:
        return _vacia()
    filas = []
    for r in t.itertuples():
        filas.append({
            "tipo": TIPO_COSTO, "tienda": r.tienda, "region": r.region, "periodo": r.mes,
            "categoria": CATEGORIA_COSTO, "valor": r.pct, "referencia": r.ref_pct,
            "desviacion_pct": r.pct - r.ref_pct, "monto_en_riesgo": r.exceso,
            "severidad": "Alta" if r.exceso >= monto_alta else "Media",
            "motivo": (f"Costo de mercancía de {r.mes:%Y-%m}: {r.pct:.1%} de la venta; la mediana de su región es "
                       f"{r.ref_pct:.1%} (+{(r.pct - r.ref_pct) * 100:.1f} puntos, umbral {umbral_pts * 100:.0f})."),
            "accion_sugerida": accion_para(TIPO_COSTO, r.tienda, r.exceso),
        })
    return pd.DataFrame(filas, columns=COLUMNAS_ALERTA)


# ------------------------------------------------------------ tiendas nuevas
def alertas_tiendas_nuevas(tiendas, ventas, gastos, umbral_media=0.10, umbral_alta=0.20, max_mes=12, min_tiendas=3):
    """Proyección de cada tienda = su venta diaria promedio del primer mes x el
    crecimiento típico de las tiendas ya abiertas. Así se compara contra su propio
    tamaño y no contra el promedio de la red. Se usa la venta diaria promedio para
    que febrero (28 días) no parezca una caída frente a enero (31 días)."""
    ap = tiendas.set_index("tienda")[["fecha_apertura", "region"]]
    v = (ventas.assign(mes=mes_de(ventas["fecha"])).groupby(["tienda", "mes"])["venta"]
         .agg(venta_dia="mean", venta="sum").reset_index())
    v = v.join(ap, on="tienda")
    v["mes_n"] = (v["mes"].dt.year - v["fecha_apertura"].dt.year) * 12 + (v["mes"].dt.month - v["fecha_apertura"].dt.month) + 1
    v = v[(v["mes_n"] >= 1) & (v["mes_n"] <= max_mes)]
    por_mes = v.groupby("mes_n")["venta_dia"].agg(["median", "count"])
    por_mes.loc[por_mes["count"] < min_tiendas, "median"] = np.nan
    factor = por_mes["median"].ffill() / por_mes["median"].iloc[0]
    primer_mes = v[v["mes_n"] == 1].set_index("tienda")["venta_dia"]
    v = v[(v["mes_n"] >= 2) & v["tienda"].isin(primer_mes.index)].copy()
    v["esperado"] = v["tienda"].map(primer_mes) * v["mes_n"].map(factor)
    v["desv"] = v["venta_dia"] / v["esperado"] - 1
    v = v[v["desv"] <= -umbral_media]
    if v.empty:
        return _vacia()
    filas = []
    for r in v.itertuples():
        dias = r.venta / r.venta_dia
        faltante = (r.esperado - r.venta_dia) * dias
        filas.append({
            "tipo": TIPO_NUEVA, "tienda": r.tienda, "region": r.region, "periodo": r.mes,
            "categoria": "ventas", "valor": r.venta, "referencia": r.esperado * dias,
            "desviacion_pct": r.desv, "monto_en_riesgo": faltante,
            "severidad": "Alta" if r.desv <= -umbral_alta else "Media",
            "motivo": (f"Mes {r.mes_n} de operación ({r.mes:%Y-%m}): vendió {_dinero(r.venta)} contra "
                       f"{_dinero(r.esperado * dias)} esperados ({r.desv:.0%}). Esperado = su venta diaria del primer mes por el "
                       f"crecimiento típico de las tiendas nuevas. Umbral: {umbral_media:.0%} por debajo."),
            "accion_sugerida": accion_para(TIPO_NUEVA, r.tienda, faltante),
        })
    return pd.DataFrame(filas, columns=COLUMNAS_ALERTA)


# ---------------------------------------------------------------- conjunto
def generar_alertas(tiendas, ventas, gastos, depositos):
    """Junta todas las alertas y las prioriza: primero severidad, luego monto en riesgo."""
    partes = [
        alertas_efectivo(tiendas, ventas, depositos),
        alertas_gasto_atipico(tiendas, gastos),
        alertas_costo_mercancia(tiendas, ventas, gastos),
        alertas_tiendas_nuevas(tiendas, ventas, gastos),
    ]
    partes = [p for p in partes if not p.empty]
    columnas = ["prioridad"] + COLUMNAS_ALERTA
    if not partes:
        return pd.DataFrame(columns=columnas)
    out = pd.concat(partes, ignore_index=True)
    out["_orden"] = out["severidad"].map({s: i for i, s in enumerate(SEVERIDADES)})
    out = out.sort_values(["_orden", "monto_en_riesgo"], ascending=[True, False]).drop(columns="_orden")
    out = out.reset_index(drop=True)
    out.insert(0, "prioridad", np.arange(1, len(out) + 1))
    return out[columnas]
