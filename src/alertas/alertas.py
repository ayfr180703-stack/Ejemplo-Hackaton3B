"""Entregable 2 y 4: detección de gastos fuera de patrón, diferencias entre
venta y depósito, y lista priorizada de alertas con acción sugerida.

Todas las reglas son simples y explicables: cada alerta dice qué regla la
disparó y contra qué se comparó. Los umbrales se pueden ajustar.
"""
import numpy as np
import pandas as pd

from src.comun import CATEGORIA_COSTO, mes_de

COLUMNAS_ALERTA = [
    "tipo", "tienda", "region", "periodo", "categoria", "valor", "referencia",
    "desviacion_pct", "monto_en_riesgo", "motivo", "accion_sugerida",
]


def _dinero(x):
    return f"${x:,.0f}"


def alertas_gastos(tiendas, gastos, meses_hist=6, umbral_hist=1.40,
                   umbral_pares=1.60, monto_min=5000):
    """Regla A: el gasto del mes supera 40% la mediana de los últimos 6 meses
    de la misma tienda y categoría.
    Regla B: supera 60% la mediana de las tiendas de su región ese mes.
    Se alerta si se cumple A o B y el exceso es mayor al monto mínimo."""
    region = tiendas[["tienda", "region"]]
    g = gastos[gastos["categoria"] != CATEGORIA_COSTO].copy()
    g["mes"] = mes_de(g["fecha"])
    m = (g.groupby(["tienda", "categoria", "mes"], as_index=False)["monto"].sum()
           .merge(region, on="tienda", how="left")
           .sort_values(["tienda", "categoria", "mes"]))
    m["ref_hist"] = m.groupby(["tienda", "categoria"])["monto"].transform(
        lambda s: s.shift(1).rolling(meses_hist, min_periods=3).median())
    m["ref_pares"] = m.groupby(["region", "categoria", "mes"])["monto"].transform("median")

    regla_a = (m["monto"] >= m["ref_hist"] * umbral_hist) & (m["monto"] - m["ref_hist"] >= monto_min)
    regla_b = (m["monto"] >= m["ref_pares"] * umbral_pares) & (m["monto"] - m["ref_pares"] >= monto_min)
    m = m[regla_a | regla_b].copy()
    if m.empty:
        return pd.DataFrame(columns=COLUMNAS_ALERTA)

    filas = []
    for r in m.itertuples():
        partes = []
        if pd.notna(r.ref_hist) and r.monto >= r.ref_hist * umbral_hist and r.monto - r.ref_hist >= monto_min:
            partes.append(f"su mediana de los últimos {meses_hist} meses es {_dinero(r.ref_hist)} "
                          f"(+{r.monto / r.ref_hist - 1:.0%})")
        if r.monto >= r.ref_pares * umbral_pares and r.monto - r.ref_pares >= monto_min:
            partes.append(f"la mediana de su región es {_dinero(r.ref_pares)} "
                          f"(+{r.monto / r.ref_pares - 1:.0%})")
        referencia = r.ref_hist if (pd.notna(r.ref_hist) and r.monto >= r.ref_hist * umbral_hist
                                    and r.monto - r.ref_hist >= monto_min) else r.ref_pares
        filas.append({
            "tipo": "Gasto atípico", "tienda": r.tienda, "region": r.region, "periodo": r.mes,
            "categoria": r.categoria, "valor": r.monto, "referencia": referencia,
            "desviacion_pct": r.monto / referencia - 1,
            "monto_en_riesgo": r.monto - referencia,
            "motivo": f"{r.categoria} de {r.mes:%Y-%m} fue {_dinero(r.monto)}; " + " y ".join(partes) + ".",
            "accion_sugerida": (f"Pedir a la tienda el soporte (factura o contrato) de {r.categoria} "
                                f"de {r.mes:%Y-%m} y confirmar si es un cargo único o recurrente."),
        })
    return pd.DataFrame(filas, columns=COLUMNAS_ALERTA)


def alertas_costo_mercancia(tiendas, ventas, gastos, umbral_pts=0.03, monto_min=5000):
    """El costo de mercancía como % de la venta supera por 3 puntos o más la
    mediana de su región ese mes (posible merma, error de captura o robo)."""
    region = tiendas[["tienda", "region"]]
    v = (ventas.assign(mes=mes_de(ventas["fecha"])).groupby(["tienda", "mes"], as_index=False)["venta"].sum())
    c = gastos[gastos["categoria"] == CATEGORIA_COSTO].copy()
    c["mes"] = mes_de(c["fecha"])
    c = c.groupby(["tienda", "mes"], as_index=False)["monto"].sum()
    t = v.merge(c, on=["tienda", "mes"], how="inner").merge(region, on="tienda", how="left")
    t = t[t["venta"] > 0].copy()
    t["pct"] = t["monto"] / t["venta"]
    t["ref_pct"] = t.groupby(["region", "mes"])["pct"].transform("median")
    t["exceso"] = (t["pct"] - t["ref_pct"]) * t["venta"]
    t = t[((t["pct"] - t["ref_pct"]) >= umbral_pts) & (t["exceso"] >= monto_min)]
    if t.empty:
        return pd.DataFrame(columns=COLUMNAS_ALERTA)

    filas = []
    for r in t.itertuples():
        filas.append({
            "tipo": "Costo de mercancía alto", "tienda": r.tienda, "region": r.region, "periodo": r.mes,
            "categoria": CATEGORIA_COSTO, "valor": r.pct, "referencia": r.ref_pct,
            "desviacion_pct": r.pct - r.ref_pct, "monto_en_riesgo": r.exceso,
            "motivo": (f"El costo de mercancía de {r.mes:%Y-%m} fue {r.pct:.1%} de la venta; "
                       f"la mediana de su región es {r.ref_pct:.1%} (+{(r.pct - r.ref_pct) * 100:.1f} puntos)."),
            "accion_sugerida": "Revisar mermas, precios de compra y captura de inventario de la tienda.",
        })
    return pd.DataFrame(filas, columns=COLUMNAS_ALERTA)


def alertas_efectivo(tiendas, ventas, depositos, umbral_pct=0.015, monto_min=3000):
    """Por semana (lunes a domingo): venta menos depósito mayor a 1.5% de la
    venta y a $3,000. Se compara por semana para no alertar por depósitos que
    se hacen al día siguiente."""
    region = tiendas[["tienda", "region"]]
    d = ventas.merge(depositos, on=["tienda", "fecha"], how="outer").fillna({"venta": 0.0, "deposito": 0.0})
    d["semana"] = d["fecha"].dt.to_period("W-SUN").dt.start_time
    s = d.groupby(["tienda", "semana"], as_index=False)[["venta", "deposito"]].sum()
    s["diferencia"] = s["venta"] - s["deposito"]
    s = s[(s["venta"] > 0)].merge(region, on="tienda", how="left")
    s = s[(s["diferencia"].abs() >= umbral_pct * s["venta"]) & (s["diferencia"].abs() >= monto_min)]
    if s.empty:
        return pd.DataFrame(columns=COLUMNAS_ALERTA)

    filas = []
    for r in s.itertuples():
        falta = r.diferencia > 0
        filas.append({
            "tipo": "Diferencia venta vs depósito", "tienda": r.tienda, "region": r.region,
            "periodo": r.semana, "categoria": "efectivo", "valor": r.diferencia, "referencia": 0.0,
            "desviacion_pct": r.diferencia / r.venta, "monto_en_riesgo": abs(r.diferencia),
            "motivo": (f"Semana del {r.semana:%Y-%m-%d}: venta {_dinero(r.venta)}, depósitos {_dinero(r.deposito)}; "
                       f"{'faltan' if falta else 'sobran'} {_dinero(abs(r.diferencia))} "
                       f"({abs(r.diferencia) / r.venta:.1%} de la venta)."),
            "accion_sugerida": ("Conciliar el arqueo y las fichas de depósito de la semana con el gerente de tienda."
                                if falta else
                                "Revisar si hay depósitos duplicados o ventas sin registrar en el punto de venta."),
        })
    return pd.DataFrame(filas, columns=COLUMNAS_ALERTA)


def generar_alertas(tiendas, ventas, gastos, depositos, umbral_alta=30000, umbral_media=10000, **parametros):
    """Junta todas las alertas y las prioriza por monto en riesgo."""
    partes = [
        alertas_gastos(tiendas, gastos, **{k: v for k, v in parametros.items()
                                           if k in {"meses_hist", "umbral_hist", "umbral_pares", "monto_min"}}),
        alertas_costo_mercancia(tiendas, ventas, gastos),
        alertas_efectivo(tiendas, ventas, depositos),
    ]
    partes = [p for p in partes if not p.empty]
    if not partes:
        return pd.DataFrame(columns=["prioridad", "severidad"] + COLUMNAS_ALERTA)
    out = pd.concat(partes, ignore_index=True)
    out["severidad"] = np.select(
        [out["monto_en_riesgo"] >= umbral_alta, out["monto_en_riesgo"] >= umbral_media],
        ["Alta", "Media"], default="Baja")
    out = out.sort_values("monto_en_riesgo", ascending=False).reset_index(drop=True)
    out.insert(0, "prioridad", np.arange(1, len(out) + 1))
    return out[["prioridad", "severidad"] + COLUMNAS_ALERTA]
