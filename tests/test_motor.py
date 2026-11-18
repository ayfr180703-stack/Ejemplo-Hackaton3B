"""Pruebas del motor de cálculo. Correr con:  python -m pytest -q"""
import pandas as pd
import pytest

from motor.alertas import generar_alertas
from motor.comun import validar_datos
from motor.conciliacion import (auditar_tienda, conciliacion_semanal, consolidado_mensual, kpis, verificar_cuadre)
from motor.proyeccion import ESCENARIOS, calibrar_supuestos, curva_historica, proyectar_tienda_nueva


def test_datos_validos(datos):
    assert validar_datos(*datos) == []


def test_todas_las_vistas_cuadran(datos):
    tiendas, ventas, gastos, _ = datos
    resultados = verificar_cuadre(tiendas, ventas, gastos)
    assert all(ok for ok, _ in resultados.values()), resultados


def test_kpis_de_la_red_igualan_los_datos_de_origen(datos):
    tiendas, ventas, gastos, depositos = datos
    k = kpis(tiendas, ventas, gastos, depositos)
    assert k["ventas"] == pytest.approx(ventas["venta"].sum())
    assert k["gastos"] == pytest.approx(gastos["monto"].sum())
    assert k["margen"] == pytest.approx(ventas["venta"].sum() - gastos["monto"].sum())
    assert k["diferencia_efectivo"] == pytest.approx(ventas["venta"].sum() - depositos["deposito"].sum())


def test_kpis_por_region_suman_el_total(datos):
    tiendas, ventas, gastos, depositos = datos
    total = kpis(tiendas, ventas, gastos, depositos)
    suma = sum(kpis(tiendas, ventas, gastos, depositos, region=r)["ventas"] for r in tiendas["region"].unique())
    assert suma == pytest.approx(total["ventas"])


def test_auditoria_a_mano_coincide_con_el_consolidado(datos):
    tiendas, ventas, gastos, depositos = datos
    cons = consolidado_mensual(tiendas, ventas, gastos, "tienda")
    for tienda in ["T003", "T015", "T028"]:
        fila = cons[(cons["tienda"] == tienda) & (cons["periodo"] == "2026-09-01")].iloc[0]
        a = auditar_tienda(tienda, "2026-09-01", ventas, gastos, depositos)
        assert a["ventas"] == pytest.approx(fila["ingresos"], abs=0.01)
        assert a["gastos"] == pytest.approx(fila["gastos"], abs=0.01)
        assert a["margen"] == pytest.approx(fila["margen"], abs=0.01)


def test_ejemplo_de_la_ficha_diferencia_de_efectivo():
    """Tienda 08: $420,000 en caja y $411,500 en depósitos -> faltan $8,500 (2.0%)."""
    tiendas = pd.DataFrame({"tienda": ["Tienda 08"], "region": ["Sur"], "formato": ["Estándar"],
                            "fecha_apertura": [pd.Timestamp("2025-01-01")]})
    dias = pd.date_range("2026-03-02", periods=7)  # lunes a domingo
    ventas = pd.DataFrame({"tienda": "Tienda 08", "fecha": dias, "venta": [60000.0] * 7})
    depositos = pd.DataFrame({"tienda": "Tienda 08", "fecha": dias, "deposito": [58785.7142857] * 7})
    semana = conciliacion_semanal(tiendas, ventas, depositos).iloc[0]
    assert semana["venta"] == pytest.approx(420000)
    assert semana["diferencia"] == pytest.approx(8500, abs=1)
    assert semana["diferencia_pct"] == pytest.approx(0.0202, abs=0.001)


def test_alertas_encuentran_todos_los_problemas_inyectados(datos, incidentes):
    alertas = generar_alertas(*datos)
    for i in incidentes.itertuples():
        coincide = alertas[(alertas["tipo"] == i.tipo) & (alertas["tienda"] == i.tienda)
                           & (alertas["periodo"] == i.periodo) & (alertas["categoria"] == i.categoria)]
        assert len(coincide) == 1, f"No se detectó: {i}"


def test_alertas_graves_no_tienen_falsas_alarmas(datos, incidentes):
    alertas = generar_alertas(*datos)
    graves = alertas[alertas["severidad"].isin(["Crítica", "Alta"])]
    llaves = ["tipo", "tienda", "periodo", "categoria"]
    falsas = graves.merge(incidentes[llaves], on=llaves, how="left", indicator=True).query("_merge == 'left_only'")
    assert len(falsas) <= 1, falsas[llaves + ["severidad"]]


def test_falsas_alarmas_totales_son_pocas(datos, incidentes):
    alertas = generar_alertas(*datos)
    assert len(alertas) - len(incidentes) <= 8


def test_cada_alerta_trae_motivo_y_accion(datos):
    alertas = generar_alertas(*datos)
    assert not alertas.empty
    assert (alertas["motivo"].str.len() > 20).all()
    assert (alertas["accion_sugerida"].str.len() > 20).all()
    assert alertas["prioridad"].tolist() == list(range(1, len(alertas) + 1))
    primeras = alertas["severidad"].tolist()
    assert primeras == sorted(primeras, key=["Crítica", "Alta", "Media"].index)


def test_la_accion_incluye_el_monto():
    from motor.acciones import TIPO_EFECTIVO, accion_para
    texto = accion_para(TIPO_EFECTIVO, "Tienda 08", 8500)
    assert "$8,500" in texto and "Tienda 08" in texto and "arqueos" in texto


def test_proyeccion_reproduce_el_ejemplo_de_la_propuesta():
    """Venta inicial $500,000, +10% mensual, margen bruto 20%, gastos fijos $150,000."""
    tabla, resumen = proyectar_tienda_nueva(500000, 0.10, 0.20, 150000, meses=6)
    esperado = [-50000, -40000, -29000, -16900, -3590, 11051]
    assert tabla["resultado_mensual"].round(0).tolist() == esperado
    assert resumen["mes_equilibrio"] == 6
    assert tabla["flujo_acumulado"].iloc[-1] == pytest.approx(-128439, abs=1)


def test_proyeccion_calibrada_y_escenarios(datos):
    tiendas, ventas, gastos, _ = datos
    supuestos = calibrar_supuestos(curva_historica(tiendas, ventas, gastos))
    base, resumen = proyectar_tienda_nueva(**supuestos, inversion_inicial=5_500_000, meses=48)
    assert len(base) == 48
    assert (base["resultado_mensual"] - (base["ventas"] * supuestos["margen_bruto"] - supuestos["gastos_fijos"])).abs().max() < 1e-6
    assert resumen["mes_equilibrio"] is not None
    finales = {n: proyectar_tienda_nueva(**supuestos, meses=48, **k)[0]["flujo_acumulado"].iloc[-1] for n, k in ESCENARIOS.items()}
    assert finales["Pesimista"] < finales["Base"] < finales["Optimista"]
