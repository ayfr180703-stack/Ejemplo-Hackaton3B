import pandas as pd
import pytest

from data.limpieza import limpiar_tabla


def test_limpia_columnas_fechas_y_montos():
    sucio = pd.DataFrame({
        "Sucursal": [" T001 ", "T001", "T002", "T002", "T003"],
        "Fecha": ["05/03/2026", "06/03/2026", "2026-03-05", "2026-03-05", "no sé"],
        "Importe": ["$1,200.50", "(300)", "450", "450", ""],
    })
    limpia, bitacora = limpiar_tabla(sucio, "ventas")
    assert list(limpia.columns) == ["tienda", "fecha", "venta"]
    assert limpia["tienda"].tolist() == ["T001", "T001", "T002"]
    assert limpia["fecha"].tolist() == [pd.Timestamp("2026-03-05"), pd.Timestamp("2026-03-06"), pd.Timestamp("2026-03-05")]
    assert limpia["venta"].tolist() == [1200.5, -300.0, 450.0]
    texto = " ".join(bitacora)
    assert "repetidas" in texto and "negativos" in texto


def test_fechas_con_diagonales_se_leen_dia_mes_ano():
    df = pd.DataFrame({"tienda": ["T1"], "fecha": ["03/04/2026"], "deposito": ["100"]})
    limpia, _ = limpiar_tabla(df, "depositos")
    assert limpia["fecha"].iloc[0] == pd.Timestamp("2026-04-03")


def test_categorias_con_otros_nombres_se_unifican():
    df = pd.DataFrame({"tienda": ["T1"] * 3, "fecha": ["2026-01-31"] * 3,
                       "categoria": ["Energía", "Sueldos", "Costo de mercancía"], "monto": ["1", "2", "3"]})
    limpia, _ = limpiar_tabla(df, "gastos")
    assert limpia["categoria"].tolist() == ["luz", "nomina", "costo_mercancia"]


def test_columnas_faltantes_dan_error_claro():
    with pytest.raises(ValueError, match="Faltan las columnas"):
        limpiar_tabla(pd.DataFrame({"tienda": ["T1"], "fecha": ["2026-01-01"]}), "ventas")


def test_catalogo_sin_formato_asigna_estandar():
    df = pd.DataFrame({"tienda": ["T1"], "region": ["Sur"], "fecha_apertura": ["2025-01-01"]})
    limpia, bitacora = limpiar_tabla(df, "tiendas")
    assert limpia["formato"].iloc[0] == "Estándar"
