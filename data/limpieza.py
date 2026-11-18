"""Limpieza y estandarización de los CSV que lleguen (por ejemplo, los del evento).

Convierte archivos "sucios" al contrato de datos de motor/comun.py:
  - nombres de columnas (sin acentos, minúsculas, con alias comunes)
  - fechas en cualquier formato razonable (05/03/2026, 2026-03-05, 5-mar-2026...)
  - montos con signo de pesos, comas o paréntesis
  - nulos, duplicados y espacios de más

Cada función regresa (tabla_limpia, bitacora). La bitácora es una lista de
textos que dice qué se corrigió y qué se descartó: nada se arregla en silencio.
"""
import re
import unicodedata

import pandas as pd

from motor.comun import COLUMNAS, FECHAS, FORMATO_POR_DEFECTO

ALIAS_COLUMNAS = {
    "tienda": ["tienda", "sucursal", "id_tienda", "clave_tienda", "store", "nombre_tienda", "unidad", "numero_tienda"],
    "region": ["region", "zona", "regional"],
    "formato": ["formato", "tipo_tienda", "tipo"],
    "fecha_apertura": ["fecha_apertura", "apertura", "fecha_de_apertura"],
    "fecha": ["fecha", "dia", "fecha_operacion", "fecha_venta", "fecha_deposito", "fecha_gasto"],
    "venta": ["venta", "ventas", "venta_pos", "venta_total", "monto_venta", "importe_venta", "importe"],
    "deposito": ["deposito", "depositos", "monto_deposito", "importe_deposito", "deposito_banco", "importe"],
    "categoria": ["categoria", "concepto", "rubro", "tipo_gasto"],
    "monto": ["monto", "importe", "gasto", "total", "importe_gasto"],
}
ALIAS_CATEGORIAS = {
    "energia": "luz", "electricidad": "luz", "energia_electrica": "luz", "cfe": "luz",
    "sueldos": "nomina", "salarios": "nomina", "alquiler": "renta", "arrendamiento": "renta",
    "costo_de_mercancia": "costo_mercancia", "costo_de_ventas": "costo_mercancia", "cmv": "costo_mercancia",
}


def _sin_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", str(texto)) if unicodedata.category(c) != "Mn")


def _nombre_columna(nombre):
    n = _sin_acentos(nombre).strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", n).strip("_")


def _normalizar_columnas(df, tipo, bitacora):
    esperadas = COLUMNAS[tipo] + (["formato"] if tipo == "tiendas" else [])
    df = df.copy()
    df.columns = [_nombre_columna(c) for c in df.columns]
    renombres = {}
    for esperada in esperadas:
        if esperada in df.columns:
            continue
        for alias in ALIAS_COLUMNAS[esperada]:
            if alias in df.columns and alias not in renombres and alias not in esperadas:
                renombres[alias] = esperada
                break
    if renombres:
        bitacora.append(f"Columnas renombradas: {renombres}")
        df = df.rename(columns=renombres)
    faltan = [c for c in COLUMNAS[tipo] if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan las columnas {faltan} en el archivo de {tipo}. Columnas encontradas: {list(df.columns)}")
    return df


def _a_fecha(serie):
    """Fechas con año primero (2026-03-05) se leen tal cual; las demás se leen
    como día/mes/año (05/03/2026), que es el orden usual en México."""
    texto = serie.astype("string").str.strip()
    resultado = pd.Series(pd.NaT, index=texto.index, dtype="datetime64[ns]")
    iso = texto.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", na=False)
    if iso.any():
        resultado[iso] = pd.to_datetime(texto[iso], format="mixed", dayfirst=False, errors="coerce")
    if (~iso).any():
        resultado[~iso] = pd.to_datetime(texto[~iso], format="mixed", dayfirst=True, errors="coerce")
    return resultado


def _a_numero(serie):
    texto = serie.astype("string").str.strip()
    negativo = texto.str.match(r"^\(.*\)$", na=False)
    limpio = texto.str.replace(r"[\$,\s()]", "", regex=True)
    numero = pd.to_numeric(limpio, errors="coerce")
    return numero.where(~negativo, -numero)


def limpiar_tabla(df, tipo):
    """Limpia una tabla de tipo 'tiendas', 'ventas', 'gastos' o 'depositos'."""
    bitacora = []
    n_inicial = len(df)
    df = _normalizar_columnas(df, tipo, bitacora)
    columnas = COLUMNAS[tipo] + (["formato"] if tipo == "tiendas" and "formato" in df.columns else [])
    df = df[columnas].copy()

    for col in ("tienda", "region", "formato", "categoria"):
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    if "categoria" in df.columns:
        cat = df["categoria"].map(lambda x: re.sub(r"[^a-z0-9]+", "_", _sin_acentos(x).lower()).strip("_") if pd.notna(x) else x)
        df["categoria"] = cat.replace(ALIAS_CATEGORIAS)

    for col in FECHAS[tipo]:
        antes = df[col].notna().sum()
        df[col] = _a_fecha(df[col])
        perdidas = int(antes - df[col].notna().sum())
        if perdidas:
            bitacora.append(f"{perdidas} fecha(s) en '{col}' no se pudieron leer y quedaron vacías.")
    for col in ("venta", "deposito", "monto"):
        if col in df.columns:
            antes = df[col].notna().sum()
            df[col] = _a_numero(df[col])
            perdidas = int(antes - df[col].notna().sum())
            if perdidas:
                bitacora.append(f"{perdidas} valor(es) en '{col}' no eran números y quedaron vacíos.")

    nulos = df[COLUMNAS[tipo]].isna().any(axis=1)
    if nulos.any():
        bitacora.append(f"Se descartaron {int(nulos.sum())} fila(s) con datos vacíos en columnas obligatorias.")
        df = df[~nulos]
    exactos = df.duplicated()
    if exactos.any():
        bitacora.append(f"Se descartaron {int(exactos.sum())} fila(s) exactamente repetidas.")
        df = df[~exactos]

    claves = {"tiendas": ["tienda"], "ventas": ["tienda", "fecha"], "depositos": ["tienda", "fecha"], "gastos": ["tienda", "fecha", "categoria"]}[tipo]
    repetidas = df.duplicated(claves, keep=False)
    if tipo != "gastos" and repetidas.any():
        bitacora.append(f"ATENCIÓN: {int(repetidas.sum())} fila(s) comparten {claves} con valores distintos; revisar a mano (no se corrigieron).")
    if tipo == "tiendas" and "formato" not in df.columns:
        df["formato"] = FORMATO_POR_DEFECTO
        bitacora.append(f"El catálogo no trae 'formato'; se asignó '{FORMATO_POR_DEFECTO}' a todas las tiendas.")
    negativos = [c for c in ("venta", "deposito", "monto") if c in df.columns and (df[c] < 0).any()]
    for c in negativos:
        bitacora.append(f"ATENCIÓN: hay montos negativos en '{c}' (¿devoluciones, notas de crédito o errores?).")
    bitacora.append(f"{tipo}: {n_inicial} fila(s) de entrada, {len(df)} de salida.")
    return df.reset_index(drop=True), bitacora
