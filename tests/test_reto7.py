"""Pruebas del Reto 7. Correr con:  python -m pytest -q"""
import pandas as pd
import pytest

from data.generar_datos import generar
from src.alertas.alertas import generar_alertas
from src.comun import cargar_datos, validar_datos
from src.consolidacion.consolidar import consolidado_mensual, verificar_cuadre
from src.proyeccion.proyeccion import ESCENARIOS, curva_historica, proyectar


@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("datos")
    incidentes = generar(carpeta)
    return cargar_datos(carpeta), incidentes


def test_datos_validos(datos):
    (tiendas, ventas, gastos, depositos), _ = datos
    assert validar_datos(tiendas, ventas, gastos, depositos) == []


def test_consolidado_cuadra_con_origen(datos):
    (tiendas, ventas, gastos, _), _ = datos
    for nivel in ["tienda", "region"]:
        consolidado = consolidado_mensual(tiendas, ventas, gastos, nivel)
        assert all(ok for ok, _ in verificar_cuadre(ventas, gastos, consolidado).values())


def test_tienda_y_region_dan_el_mismo_total(datos):
    (tiendas, ventas, gastos, _), _ = datos
    por_tienda = consolidado_mensual(tiendas, ventas, gastos, "tienda")["margen"].sum()
    por_region = consolidado_mensual(tiendas, ventas, gastos, "region")["margen"].sum()
    assert por_tienda == pytest.approx(por_region)


def test_alertas_encuentran_todos_los_problemas_inyectados(datos):
    (tiendas, ventas, gastos, depositos), incidentes = datos
    alertas = generar_alertas(tiendas, ventas, gastos, depositos)
    for i in incidentes.itertuples():
        coincide = alertas[(alertas["tipo"] == i.tipo) & (alertas["tienda"] == i.tienda)
                           & (alertas["periodo"] == i.periodo) & (alertas["categoria"] == i.categoria)]
        assert len(coincide) == 1, f"No se detectó: {i}"


def test_alertas_importantes_no_tienen_falsas_alarmas(datos):
    (tiendas, ventas, gastos, depositos), incidentes = datos
    alertas = generar_alertas(tiendas, ventas, gastos, depositos)
    importantes = alertas[alertas["severidad"].isin(["Alta", "Media"])]
    assert len(importantes) == len(incidentes)


def test_proyeccion_es_coherente(datos):
    (tiendas, ventas, gastos, _), _ = datos
    curva = curva_historica(tiendas, ventas, gastos)
    base, resumen = proyectar(curva)
    assert len(base) == 24
    assert (base["flujo_mensual"] - (base["ventas"] - base["costo_mercancia"] - base["gastos_operativos"])).abs().max() < 1e-6
    assert resumen["mes_equilibrio"] is not None
    pesimista, _ = proyectar(curva, **ESCENARIOS["Pesimista"])
    optimista, _ = proyectar(curva, **ESCENARIOS["Optimista"])
    assert pesimista["flujo_acumulado"].iloc[-1] < base["flujo_acumulado"].iloc[-1] < optimista["flujo_acumulado"].iloc[-1]
