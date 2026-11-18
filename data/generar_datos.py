"""Genera datos SINTÉTICOS (inventados) para practicar el Reto 7.

Uso, desde la raíz del repositorio:
    python data/generar_datos.py

Crea data/ejemplo_tiendas.csv, ejemplo_ventas.csv, ejemplo_gastos.csv,
ejemplo_depositos.csv y ejemplo_incidentes.csv (la "clave de respuestas" con
los problemas que se metieron a propósito, para comprobar que las alertas los
encuentran). No contiene datos reales de ninguna empresa.
"""
from pathlib import Path

import numpy as np
import pandas as pd

REGIONES = {"Centro": 1.00, "Norte": 0.95, "Sur-Sureste": 0.90, "Occidente": 1.05}
FORMATOS = {"Estándar": 1.00, "Compacta": 0.80}
INICIO, FIN = pd.Timestamp("2024-01-01"), pd.Timestamp("2026-10-31")
VENTA_DIARIA_BASE = 70000
COSTO_BASE = 0.82        # costo de mercancía como % de la venta
COSTO_INCIDENTE = 0.89
DIA_SEMANA = np.array([0.95, 0.93, 0.95, 0.97, 1.05, 1.12, 1.03])  # lunes a domingo


def generar(carpeta=None, prefijo="ejemplo_", semilla=7):
    rng = np.random.default_rng(semilla)
    carpeta = Path(carpeta) if carpeta else Path(__file__).resolve().parent

    # --- Catálogo: 6 tiendas maduras + 24 que abren entre 2024 y 2026 ---
    meses_apertura = pd.date_range("2024-01-01", "2026-08-01", freq="MS")
    nuevas = meses_apertura[np.linspace(0, len(meses_apertura) - 1, 24).round().astype(int)]
    aperturas = sorted([pd.Timestamp("2023-06-01")] * 6 + list(nuevas))
    nombres_region, nombres_formato = list(REGIONES), list(FORMATOS)
    tiendas = pd.DataFrame({
        "tienda": [f"T{i + 1:03d}" for i in range(len(aperturas))],
        "region": [nombres_region[i] for i in rng.permutation(len(aperturas)) % len(nombres_region)],
        "formato": rng.choice(nombres_formato, size=len(aperturas), p=[0.7, 0.3]),
        "fecha_apertura": aperturas,
    })

    # --- Ventas y depósitos diarios ---
    ventas, depositos, parametros = [], [], {}
    for t in tiendas.itertuples():
        tam = FORMATOS[t.formato]
        base = VENTA_DIARIA_BASE * REGIONES[t.region] * tam * rng.lognormal(0, 0.05)
        parametros[t.tienda] = {
            "renta": rng.uniform(38000, 46000) * tam, "nomina": rng.uniform(82000, 90000) * tam,
            "luz": rng.uniform(25000, 30000) * tam, "mantenimiento": rng.uniform(6000, 10000) * tam,
            "merma_pct": rng.uniform(0.008, 0.012), "costo_pct": COSTO_BASE + rng.normal(0, 0.003),
            "ritmo": rng.uniform(5.5, 6.5),   # qué tan rápido madura la tienda (meses)
        }
        fechas = pd.date_range(max(t.fecha_apertura, INICIO), FIN, freq="D")
        m = (fechas.year - t.fecha_apertura.year) * 12 + (fechas.month - t.fecha_apertura.month) + 1
        rampa = 1 - 0.7 * np.exp(-(m - 1) / parametros[t.tienda]["ritmo"])
        venta = base * rampa * DIA_SEMANA[fechas.dayofweek] * rng.lognormal(0, 0.06, len(fechas))
        dep = venta * (1 + rng.normal(0, 0.002, len(fechas)))
        ventas.append(pd.DataFrame({"tienda": t.tienda, "fecha": fechas, "venta": venta}))
        depositos.append(pd.DataFrame({"tienda": t.tienda, "fecha": fechas, "deposito": dep}))
    ventas = pd.concat(ventas, ignore_index=True)
    depositos = pd.concat(depositos, ignore_index=True)

    # --- Selección de tiendas para los problemas inyectados ---
    elegibles = tiendas.loc[tiendas["fecha_apertura"] <= "2025-12-01", "tienda"].to_numpy()
    e = list(rng.choice(elegibles, size=7, replace=False))
    recientes = tiendas.loc[(tiendas["fecha_apertura"] >= "2026-01-01") & (tiendas["fecha_apertura"] <= "2026-05-01"), "tienda"].to_numpy()
    nueva_floja = str(rng.choice(recientes))
    incidentes = []

    # Tienda nueva que vende 25% menos de lo normal de agosto a octubre de 2026
    filtro = (ventas["tienda"] == nueva_floja) & (ventas["fecha"] >= "2026-08-01")
    ventas.loc[filtro, "venta"] *= 0.75
    depositos.loc[(depositos["tienda"] == nueva_floja) & (depositos["fecha"] >= "2026-08-01"), "deposito"] *= 0.75
    for mes in ["2026-08-01", "2026-09-01", "2026-10-01"]:
        incidentes.append({"tipo": "Tienda nueva bajo proyección", "tienda": nueva_floja, "periodo": pd.Timestamp(mes),
                           "categoria": "ventas", "detalle": "vende 25% menos de lo normal"})

    # Faltantes de efectivo en una semana (lunes a sábado)
    for tienda, lunes, faltante in [(e[4], "2026-09-14", 0.07), (e[5], "2026-10-05", 0.05), (e[6], "2026-10-19", 0.09)]:
        lunes = pd.Timestamp(lunes)
        filtro = (depositos["tienda"] == tienda) & (depositos["fecha"] >= lunes) & (depositos["fecha"] < lunes + pd.Timedelta(days=6))
        depositos.loc[filtro, "deposito"] *= (1 - faltante)
        incidentes.append({"tipo": "Diferencia venta vs depósito", "tienda": tienda, "periodo": lunes,
                           "categoria": "efectivo", "detalle": f"faltante de {faltante:.0%} en la semana"})
    ventas["venta"] = ventas["venta"].round(2)
    depositos["deposito"] = depositos["deposito"].round(2)

    # --- Gastos mensuales por categoría (fecha = último día del mes) ---
    mensual = ventas.assign(mes=ventas["fecha"].dt.to_period("M").dt.to_timestamp()) \
                    .groupby(["tienda", "mes"], as_index=False)["venta"].sum()
    gastos = []
    for r in mensual.itertuples():
        p = parametros[r.tienda]
        fecha = r.mes + pd.offsets.MonthEnd(0)
        montos = {
            "costo_mercancia": r.venta * (p["costo_pct"] + rng.normal(0, 0.003)),
            "renta": p["renta"],
            "nomina": p["nomina"] * rng.normal(1, 0.015),
            "luz": p["luz"] * rng.normal(1, 0.04),
            "mantenimiento": p["mantenimiento"] * rng.lognormal(0, 0.12),
            "merma": r.venta * p["merma_pct"] * rng.normal(1, 0.05),
        }
        for categoria, monto in montos.items():
            gastos.append((r.tienda, fecha, categoria, round(monto, 2)))
    gastos = pd.DataFrame(gastos, columns=["tienda", "fecha", "categoria", "monto"])

    def sube_gasto(tienda, mes, categoria, factor):
        fecha = pd.Timestamp(mes) + pd.offsets.MonthEnd(0)
        filtro = (gastos["tienda"] == tienda) & (gastos["fecha"] == fecha) & (gastos["categoria"] == categoria)
        gastos.loc[filtro, "monto"] = (gastos.loc[filtro, "monto"] * factor).round(2)
        incidentes.append({"tipo": "Gasto atípico", "tienda": tienda, "periodo": pd.Timestamp(mes),
                           "categoria": categoria, "detalle": f"{categoria} x{factor}"})

    sube_gasto(e[0], "2026-08-01", "luz", 2.6)
    sube_gasto(e[1], "2026-09-01", "mantenimiento", 4.0)
    sube_gasto(e[2], "2026-10-01", "nomina", 1.45)

    for mes in ["2026-09-01", "2026-10-01"]:
        fecha = pd.Timestamp(mes) + pd.offsets.MonthEnd(0)
        filtro = (gastos["tienda"] == e[3]) & (gastos["fecha"] == fecha) & (gastos["categoria"] == "costo_mercancia")
        gastos.loc[filtro, "monto"] = (gastos.loc[filtro, "monto"] * COSTO_INCIDENTE / COSTO_BASE).round(2)
        incidentes.append({"tipo": "Costo de mercancía alto", "tienda": e[3], "periodo": pd.Timestamp(mes),
                           "categoria": "costo_mercancia", "detalle": "costo ~89% de la venta"})

    incidentes = pd.DataFrame(incidentes)
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, df in [("tiendas", tiendas), ("ventas", ventas), ("gastos", gastos),
                       ("depositos", depositos), ("incidentes", incidentes)]:
        df.to_csv(carpeta / f"{prefijo}{nombre}.csv", index=False)
    return incidentes


if __name__ == "__main__":
    inc = generar()
    print(f"Datos de ejemplo creados en data/. Problemas inyectados: {len(inc)}")
