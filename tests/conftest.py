import pytest

from data.generar_datos import generar
from motor.comun import cargar_datos


@pytest.fixture(scope="session")
def carpeta_datos(tmp_path_factory):
    carpeta = tmp_path_factory.mktemp("datos")
    generar(carpeta)
    return carpeta


@pytest.fixture(scope="session")
def datos(carpeta_datos):
    return cargar_datos(carpeta_datos)


@pytest.fixture(scope="session")
def incidentes(carpeta_datos):
    import pandas as pd
    return pd.read_csv(carpeta_datos / "ejemplo_incidentes.csv", parse_dates=["periodo"])
