import io

import pytest
from fastapi.testclient import TestClient

import api.main as api_main


@pytest.fixture()
def cliente(datos):
    api_main._estado["datos"] = datos
    api_main._estado["origen"] = "pruebas"
    return TestClient(api_main.app)


def test_salud(cliente):
    assert cliente.get("/health").json()["ok"] is True


def test_kpis_y_filtros(cliente):
    total = cliente.get("/kpis").json()
    centro = cliente.get("/kpis", params={"region": "Centro"}).json()
    assert 0 < centro["ventas"] < total["ventas"]
    assert total["margen"] == pytest.approx(total["ventas"] - total["gastos"])
    mes = cliente.get("/kpis", params={"desde": "2026-09-01", "hasta": "2026-09-30"}).json()
    assert 0 < mes["ventas"] < total["ventas"]


def test_alertas_filtradas_por_severidad(cliente):
    criticas = cliente.get("/alertas", params={"severidad": "Crítica"}).json()
    assert len(criticas) >= 5
    assert all(a["severidad"] == "Crítica" and a["motivo"] and a["accion_sugerida"] for a in criticas)


def test_proyeccion_de_una_tienda(cliente):
    r = cliente.get("/proyecciones/T028", params={"meses": 24, "inversion_inicial": 1_000_000}).json()
    assert r["resumen"]["mes_equilibrio"] is not None
    assert len(r["curva"]) == 24 and "venta_real" in r["curva"][0]
    assert cliente.get("/proyecciones/NOEXISTE").status_code == 404


def test_cuadre_y_auditoria(cliente):
    assert all(v["cuadra"] for v in cliente.get("/cuadre").json()["revisiones"].values())
    a = cliente.get("/auditoria/T003", params={"mes": "2026-09-01"}).json()
    assert a["ventas"] > 0 and a["margen"] == pytest.approx(a["ventas"] - a["gastos"])


def test_cargar_csv_sucio_en_vivo(cliente):
    def csv(texto):
        return io.BytesIO(texto.encode("utf-8"))
    archivos = {
        "tiendas": ("t.csv", csv("Sucursal,Zona,Fecha de apertura\nT1,Norte,01/01/2026\nT2,Norte,01/02/2026\n"), "text/csv"),
        "ventas": ("v.csv", csv("tienda,fecha,importe\nT1,05/03/2026,\"$1,000.00\"\nT1,05/03/2026,\"$1,000.00\"\nT2,05/03/2026,500\n"), "text/csv"),
        "gastos": ("g.csv", csv("tienda,fecha,concepto,importe\nT1,31/03/2026,Energía,200\n"), "text/csv"),
        "depositos": ("d.csv", csv("tienda,fecha,deposito\nT1,05/03/2026,990\nT2,05/03/2026,500\n"), "text/csv"),
    }
    r = cliente.post("/cargar-csv", files=archivos)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["filas"] == {"tiendas": 2, "ventas": 2, "gastos": 1, "depositos": 2}
    assert cliente.get("/kpis").json()["ventas"] == pytest.approx(1500)


def test_cargar_csv_con_columnas_faltantes_regresa_error_claro(cliente):
    archivos = {n: (f"{n}.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv") for n in ["tiendas", "ventas", "gastos", "depositos"]}
    r = cliente.post("/cargar-csv", files=archivos)
    assert r.status_code == 422 and "Faltan las columnas" in r.json()["detail"]
