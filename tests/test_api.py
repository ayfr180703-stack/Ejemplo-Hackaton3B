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
    assert r.status_code == 422 and "fila de encabezados" in r.json()["detail"]


# ---------------------------------------------------------------- robustez (Fase 6)
def _csv(texto):
    return io.BytesIO(texto.encode("utf-8"))


def _archivos(**cambios):
    base = {
        "tiendas": "tienda,region,fecha_apertura\nT1,Norte,2026-01-01\nT2,Norte,2026-02-01\n",
        "ventas": "tienda,fecha,venta\nT1,2026-03-05,1000\nT2,2026-03-05,500\n",
        "gastos": "tienda,fecha,categoria,monto\nT1,2026-03-31,luz,200\n",
        "depositos": "tienda,fecha,deposito\nT1,2026-03-05,990\nT2,2026-03-05,500\n",
    }
    base.update(cambios)
    return {n: (f"{n}.csv", _csv(t), "text/csv") for n, t in base.items()}


def test_cabeceras_cors_y_tiempo(cliente):
    r = cliente.get("/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] in ("*", "http://localhost:5173")
    assert float(r.headers["x-tiempo-ms"]) >= 0


def test_carga_con_duplicados_fechas_malas_y_negativos_no_se_rompe(cliente):
    antes = cliente.get("/kpis").json()
    r = cliente.post("/cargar-csv", files=_archivos(
        ventas="tienda,fecha,venta\nT1,2026-03-05,1000\nT1,2026-03-05,1000\nT2,no-es-fecha,500\nT2,2026-03-06,-300\nT2,2026-03-07,abc\n"))
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["filas"]["ventas"] < 5 and cuerpo["bitacora"]["ventas"]
    assert cliente.get("/kpis").status_code == 200
    assert cliente.get("/kpis").json() != antes


def test_archivo_en_la_ranura_equivocada_da_422_y_conserva_datos(cliente):
    antes = cliente.get("/kpis").json()
    r = cliente.post("/cargar-csv", files=_archivos(ventas="tienda,fecha,categoria,monto\nT1,2026-03-05,luz,200\n"))
    assert r.status_code == 422 and "ventas.csv" in r.json()["detail"]
    assert cliente.get("/kpis").json() == antes


def test_archivo_vacio_da_422(cliente):
    r = cliente.post("/cargar-csv", files=_archivos(gastos="   \n"))
    assert r.status_code == 422 and "vacío" in r.json()["detail"]


def test_escenarios_juntos_y_ordenados(cliente):
    r = cliente.get("/proyecciones/T028/escenarios", params={"meses": 48, "inversion_inicial": 2_000_000}).json()
    assert set(r["escenarios"]) == {"Pesimista", "Base", "Optimista"}
    acum = {e: x["curva"][-1]["flujo_acumulado"] for e, x in r["escenarios"].items()}
    assert acum["Pesimista"] < acum["Base"] < acum["Optimista"]


def test_inversion_negativa_o_tienda_inexistente(cliente):
    assert cliente.get("/proyecciones/T028", params={"inversion_inicial": -5}).status_code == 422
    assert cliente.get("/proyecciones/NOEXISTE/escenarios").status_code == 404


def test_filtros_para_la_interfaz(cliente):
    f = cliente.get("/filtros").json()
    assert "Centro" in f["regiones"] and len(f["tiendas"]) == 30 and f["desde"] < f["hasta"]


def test_consolidado_total_suma_lo_filtrado(cliente):
    total = cliente.get("/consolidado", params={"nivel": "total"}).json()
    k = cliente.get("/kpis").json()
    assert sum(f["ingresos"] for f in total) == pytest.approx(k["ventas"])
    assert sum(f["gastos"] for f in total) == pytest.approx(k["gastos"])
    una = cliente.get("/consolidado", params={"nivel": "total", "tienda": "T001"}).json()
    assert 0 < sum(f["ingresos"] for f in una) < k["ventas"]


def test_la_api_sirve_la_interfaz_compilada(cliente):
    from pathlib import Path
    if not (Path(api_main.__file__).resolve().parent.parent / "frontend" / "dist").is_dir():
        pytest.skip("la interfaz no está compilada")
    r = cliente.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert cliente.get("/health").json()["ok"] is True
