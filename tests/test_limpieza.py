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


# ---------------------------------------------------------------- lectura de archivos
import io as _io

import pandas as _pd
import pytest as _pytest

from data.limpieza import leer_y_limpiar


def test_lee_csv_punto_y_coma_con_acentos_de_windows():
    texto = "tienda;fecha;categoria;monto\nT1;05/03/2026;Energía;1.200,50\n"
    # coma decimal europea no se asume: el monto "1.200,50" se limpia con las reglas existentes
    df, bit = leer_y_limpiar(texto.encode("latin-1"), "gastos.csv", "gastos")
    assert len(df) == 1 and df.iloc[0]["categoria"] == "luz"
    assert any("latin-1" in b and "punto y coma" in b for b in bit)


def test_lee_excel_con_encabezado_en_fila_3_y_total():
    filas = [["Reporte de ventas", None, None], [None, None, None],
             ["Sucursal", "Fecha", "Importe"],
             ["T1", "05/03/2026", "1000"], ["T2", "05/03/2026", "500"],
             ["Total", None, "1500"]]
    buf = _io.BytesIO()
    _pd.DataFrame(filas).to_excel(buf, header=False, index=False)
    df, bit = leer_y_limpiar(buf.getvalue(), "ventas.xlsx", "ventas")
    assert list(df["tienda"]) == ["T1", "T2"] and df["venta"].sum() == 1500
    assert any("fila 3" in b for b in bit) and any("totales" in b for b in bit)


def test_archivo_vacio_o_irreconocible_da_error_claro():
    with _pytest.raises(ValueError, match="vacío"):
        leer_y_limpiar(b"  \n", "x.csv", "ventas")
    with _pytest.raises(ValueError, match="encabezados"):
        leer_y_limpiar(b"a,b\n1,2\n", "x.csv", "ventas")
    with _pytest.raises(ValueError, match="xls"):
        leer_y_limpiar(b"x", "x.xls", "ventas")
