"""Ensayo: los mismos datos de ejemplo, pero "ensuciados" como podrían llegar los reales
(Excel con títulos y totales, punto y coma, acentos de Windows, montos con $ y comas,
fechas dd/mm/aaaa, nombres de columnas y categorías distintos, duplicados).
Después de limpiarlos, el motor debe dar exactamente lo mismo que con los datos limpios."""
import io

import pandas as pd
import pytest

from data.limpieza import leer_y_limpiar
from motor import conciliacion
from motor.alertas import generar_alertas
from motor.comun import completar_tiendas

NOMBRE_CATEGORIA = {"costo_mercancia": "Costo de ventas", "renta": "Alquiler", "luz": "Energía",
                    "nomina": "Sueldos", "mantenimiento": "Mantenimiento", "merma": "Merma"}


def _dinero(serie):
    return serie.map(lambda v: f"${v:,.2f}")


@pytest.fixture(scope="module")
def sucios(datos):
    tiendas, ventas, gastos, depositos = datos
    # tiendas: Excel con 2 filas de título y columnas con otros nombres
    t = tiendas[["tienda", "region", "fecha_apertura"]].copy()
    t["fecha_apertura"] = t["fecha_apertura"].dt.strftime("%d/%m/%Y")
    t.columns = ["Sucursal", "Zona", "Fecha de apertura"]
    bloque = pd.concat([pd.DataFrame([["Catálogo de tiendas", None, None], [None, None, None]]),
                        pd.DataFrame([t.columns.tolist()]), pd.DataFrame(t.values)], ignore_index=True)
    buf_t = io.BytesIO()
    bloque.to_excel(buf_t, header=False, index=False)
    # ventas: Excel con título, montos con $ y fila de total
    v = ventas.copy()
    v["fecha"] = v["fecha"].dt.strftime("%d/%m/%Y")
    v["venta"] = _dinero(v["venta"])
    v.columns = ["Sucursal", "Fecha", "Importe"]
    total = pd.DataFrame([["Total", None, f"${ventas['venta'].sum():,.2f}"]], columns=v.columns)
    bloque = pd.concat([pd.DataFrame([["Ventas diarias", None, None]]), pd.DataFrame([v.columns.tolist()]),
                        pd.DataFrame(v.values), pd.DataFrame(total.values)], ignore_index=True)
    buf_v = io.BytesIO()
    bloque.to_excel(buf_v, header=False, index=False)
    # gastos: CSV con ; y acentos de Windows, comas de miles, duplicados
    g = gastos.copy()
    g["fecha"] = g["fecha"].dt.strftime("%d/%m/%Y")
    g["categoria"] = g["categoria"].map(NOMBRE_CATEGORIA)
    g["monto"] = _dinero(g["monto"])
    g.columns = ["Tienda", "Fecha", "Concepto", "Importe"]
    g = pd.concat([g, g.head(50)])
    txt_g = g.to_csv(sep=";", index=False).encode("latin-1")
    # depósitos: CSV con tabulador
    d = depositos.copy()
    d["fecha"] = d["fecha"].dt.strftime("%Y-%m-%d")
    txt_d = d.to_csv(sep="\t", index=False).encode("utf-8")
    return {"tiendas": (buf_t.getvalue(), "tiendas.xlsx"), "ventas": (buf_v.getvalue(), "ventas.xlsx"),
            "gastos": (txt_g, "gastos.csv"), "depositos": (txt_d, "depositos.txt")}


@pytest.fixture(scope="module")
def limpios(sucios):
    out = {}
    for tipo, (contenido, nombre) in sucios.items():
        out[tipo] = leer_y_limpiar(contenido, nombre, tipo)
    return out


def test_dejan_las_mismas_filas_y_totales_que_los_datos_limpios(limpios, datos):
    tiendas, ventas, gastos, depositos = datos
    assert len(limpios["tiendas"][0]) == len(tiendas)
    assert len(limpios["ventas"][0]) == len(ventas)
    assert len(limpios["gastos"][0]) == len(gastos)
    assert limpios["ventas"][0]["venta"].sum() == pytest.approx(ventas["venta"].sum())
    assert limpios["gastos"][0]["monto"].sum() == pytest.approx(gastos["monto"].sum())
    assert limpios["depositos"][0]["deposito"].sum() == pytest.approx(depositos["deposito"].sum())


def test_la_bitacora_avisa_de_lo_que_corrigio(limpios):
    assert any("repetidas" in b for b in limpios["gastos"][1])
    assert any("totales" in b for b in limpios["ventas"][1])
    assert any("fila 2" in b or "fila 3" in b for b in limpios["ventas"][1])


def test_el_motor_da_lo_mismo_con_datos_limpios_y_sucios(limpios, datos):
    tiendas, ventas, gastos, depositos = datos
    t = completar_tiendas(limpios["tiendas"][0])
    v, g, d = limpios["ventas"][0], limpios["gastos"][0], limpios["depositos"][0]
    assert conciliacion.kpis(t, v, g, d) == pytest.approx(conciliacion.kpis(tiendas, ventas, gastos, depositos))
    a_limpias = generar_alertas(tiendas, ventas, gastos, depositos)
    a_sucias = generar_alertas(t, v, g, d)
    assert len(a_sucias) == len(a_limpias)
    assert list(a_sucias["tienda"]) == list(a_limpias["tienda"])


@pytest.mark.parametrize("semilla", [1, 3, 42])
def test_las_alertas_son_estables_con_otros_datos_aleatorios(tmp_path, semilla):
    """Los umbrales no están "afinados" a una sola semilla: con otros datos inventados
    siguen encontrando los 11 problemas y las falsas alarmas son pocas y de severidad Media."""
    from data.generar_datos import generar
    from motor.comun import cargar_datos
    generar(tmp_path, semilla=semilla)
    d = cargar_datos(tmp_path)
    inc = pd.read_csv(tmp_path / "ejemplo_incidentes.csv", parse_dates=["periodo"])
    al = generar_alertas(*d)
    al["periodo"] = pd.to_datetime(al["periodo"])
    for i in inc.itertuples():
        hay = ((al["tienda"] == i.tienda) & (al["periodo"].dt.to_period("M") == i.periodo.to_period("M"))).any()
        assert hay, f"semilla {semilla}: no se detectó {i.tipo} en {i.tienda} {i.periodo:%Y-%m}"
    assert len(al) - len(inc) <= 6
    assert not (al["severidad"] == "Crítica").sum() > 5
