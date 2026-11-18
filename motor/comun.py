"""Utilidades comunes del motor: rutas, esquema de datos, carga y validación.

Esquema (archivos CSV con encabezados, en la carpeta data/). Es el contrato de
datos del equipo; si cambia, hay que avisar y actualizar CONTEXT.md.

  <prefijo>tiendas.csv    -> tienda, region, fecha_apertura   (+ formato, opcional)
  <prefijo>ventas.csv     -> tienda, fecha, venta             (punto de venta, diario)
  <prefijo>gastos.csv     -> tienda, fecha, categoria, monto
  <prefijo>depositos.csv  -> tienda, fecha, deposito          (banco, diario)

Si los datos reales llegan con otro formato, se transforman en data/limpieza.py
y el resto del proyecto no cambia.
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"

COLUMNAS = {
    "tiendas": ["tienda", "region", "fecha_apertura"],
    "ventas": ["tienda", "fecha", "venta"],
    "gastos": ["tienda", "fecha", "categoria", "monto"],
    "depositos": ["tienda", "fecha", "deposito"],
}
FECHAS = {
    "tiendas": ["fecha_apertura"],
    "ventas": ["fecha"],
    "gastos": ["fecha"],
    "depositos": ["fecha"],
}
FORMATO_POR_DEFECTO = "Estándar"
CATEGORIA_COSTO = "costo_mercancia"


def mes_de(serie_fechas):
    """Primer día del mes de cada fecha."""
    return serie_fechas.dt.to_period("M").dt.to_timestamp()


def completar_tiendas(tiendas):
    """Agrega la columna 'formato' si el catálogo no la trae."""
    tiendas = tiendas.copy()
    if "formato" not in tiendas.columns:
        tiendas["formato"] = FORMATO_POR_DEFECTO
    tiendas["formato"] = tiendas["formato"].fillna(FORMATO_POR_DEFECTO)
    return tiendas[["tienda", "region", "formato", "fecha_apertura"]]


def cargar_datos(carpeta=None, prefijo="ejemplo_"):
    """Carga las 4 tablas y regresa (tiendas, ventas, gastos, depositos)."""
    carpeta = Path(carpeta) if carpeta else DATA
    tablas = {}
    for nombre, columnas in COLUMNAS.items():
        ruta = carpeta / f"{prefijo}{nombre}.csv"
        df = pd.read_csv(ruta, parse_dates=FECHAS[nombre])
        faltan = [c for c in columnas if c not in df.columns]
        if faltan:
            raise ValueError(f"{ruta.name}: faltan las columnas {faltan}")
        tablas[nombre] = df[columnas + (["formato"] if nombre == "tiendas" and "formato" in df.columns else [])]
    return completar_tiendas(tablas["tiendas"]), tablas["ventas"], tablas["gastos"], tablas["depositos"]


def validar_datos(tiendas, ventas, gastos, depositos):
    """Revisa calidad básica. Regresa una lista de problemas (vacía = todo bien)."""
    problemas = []
    if tiendas["tienda"].duplicated().any():
        problemas.append("Hay tiendas duplicadas en el catálogo.")
    catalogo = set(tiendas["tienda"])
    for nombre, df in [("ventas", ventas), ("gastos", gastos), ("depósitos", depositos)]:
        fuera = set(df["tienda"]) - catalogo
        if fuera:
            problemas.append(f"{nombre}: {len(fuera)} tienda(s) no están en el catálogo.")
        if df.isna().any().any():
            problemas.append(f"{nombre}: hay valores vacíos.")
    if ventas.duplicated(["tienda", "fecha"]).any():
        problemas.append("ventas: hay más de un registro por tienda y día.")
    if depositos.duplicated(["tienda", "fecha"]).any():
        problemas.append("depósitos: hay más de un registro por tienda y día.")
    if (ventas["venta"] < 0).any():
        problemas.append("ventas: hay montos negativos.")
    if (gastos["monto"] < 0).any():
        problemas.append("gastos: hay montos negativos (¿devoluciones o notas de crédito?).")
    sin_deposito = len(
        ventas.merge(depositos, on=["tienda", "fecha"], how="left").query("deposito.isna()")
    )
    if sin_deposito:
        problemas.append(f"{sin_deposito} día(s) con venta y sin depósito registrado.")
    return problemas
