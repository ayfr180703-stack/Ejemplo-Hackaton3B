"""API del Reto 7 (FastAPI). Correr desde la raíz del repositorio:
    uvicorn api.main:app --reload
La documentación interactiva queda en http://127.0.0.1:8000/docs

Ninguna cifra sale de otro lugar que no sea el motor de cálculo (carpeta motor/).
"""
import json
import os
from pathlib import Path
import time
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from data.limpieza import leer_y_limpiar
from motor import conciliacion
from motor.alertas import generar_alertas
from motor.comun import cargar_datos, completar_tiendas, validar_datos
from motor.proyeccion import ESCENARIOS, calibrar_supuestos, curva_historica, proyectar_tienda_nueva

app = FastAPI(title="Reto 7 · Control financiero por tienda", version="0.1.0")
_estado = {"datos": None, "origen": None}

# CORS: permite que la interfaz web (otro dominio/puerto) consulte la API.
# En producción se limita con la variable CORS_ORIGENES="https://mi-app.pages.dev,http://localhost:5173".
_origenes = [o.strip() for o in os.getenv("CORS_ORIGENES", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_origenes, allow_methods=["*"], allow_headers=["*"],
                   expose_headers=["X-Tiempo-ms"])


@app.middleware("http")
async def medir_tiempo(request: Request, call_next):
    """Agrega el encabezado X-Tiempo-ms a cada respuesta (para vigilar que la demo sea ágil)."""
    inicio = time.perf_counter()
    respuesta = await call_next(request)
    respuesta.headers["X-Tiempo-ms"] = f"{(time.perf_counter() - inicio) * 1000:.0f}"
    return respuesta


def _datos():
    if _estado["datos"] is None:
        _estado["datos"] = cargar_datos()
        _estado["origen"] = "data/ejemplo_*.csv (datos sintéticos)"
    return _estado["datos"]


def _registros(df):
    return json.loads(df.to_json(orient="records", date_format="iso", force_ascii=False))


@app.get("/health")
def salud():
    tiendas, ventas, *_ = _datos()
    return {"ok": True, "origen": _estado["origen"], "tiendas": len(tiendas), "dias_con_venta": int(ventas["fecha"].nunique())}


@app.get("/filtros")
def filtros():
    """Opciones para los filtros de la interfaz: regiones, tiendas y rango de fechas con datos."""
    tiendas, ventas, *_ = _datos()
    return {"regiones": sorted(tiendas["region"].unique().tolist()), "tiendas": sorted(tiendas["tienda"].unique().tolist()),
            "desde": ventas["fecha"].min().strftime("%Y-%m-%d"), "hasta": ventas["fecha"].max().strftime("%Y-%m-%d")}


@app.get("/kpis")
def kpis(region: Optional[str] = None, tienda: Optional[str] = None,
         desde: Optional[str] = Query(None, description="AAAA-MM-DD"), hasta: Optional[str] = Query(None, description="AAAA-MM-DD")):
    """Ventas, gastos, margen y diferencia de efectivo, con filtros."""
    tiendas, ventas, gastos, depositos = _datos()
    return conciliacion.kpis(tiendas, ventas, gastos, depositos, region, tienda, desde, hasta)


@app.get("/consolidado")
def consolidado(nivel: str = Query("tienda", pattern="^(tienda|region|total)$"), region: Optional[str] = None,
                tienda: Optional[str] = None, desde: Optional[str] = None, hasta: Optional[str] = None):
    """Ingresos, gastos y margen por mes y por tienda, región o total (suma de lo filtrado)."""
    tiendas, ventas, gastos, _ = _datos()
    if nivel == "total":
        cons = conciliacion.consolidado_mensual(tiendas, ventas, gastos, "tienda")
        if region:
            cons = cons[cons["region"] == region]
        if tienda:
            cons = cons[cons["tienda"] == tienda]
        cons = conciliacion.filtrar_periodo(cons, desde, hasta)
        cons = cons.groupby("periodo", as_index=False)[["ingresos", "gastos", "margen"]].sum()
        cons["margen_pct"] = (cons["margen"] / cons["ingresos"]).where(cons["ingresos"] != 0, 0.0)
        return _registros(cons)
    cons = conciliacion.consolidado_mensual(tiendas, ventas, gastos, nivel)
    if region:
        cons = cons[cons["region"] == region]
    if tienda and nivel == "tienda":
        cons = cons[cons["tienda"] == tienda]
    return _registros(conciliacion.filtrar_periodo(cons, desde, hasta))


@app.get("/alertas")
def alertas(region: Optional[str] = None, tienda: Optional[str] = None, severidad: Optional[str] = None,
            tipo: Optional[str] = None, desde: Optional[str] = None, hasta: Optional[str] = None):
    """Alertas priorizadas, cada una con su explicación y su acción sugerida."""
    tiendas, ventas, gastos, depositos = _datos()
    al = generar_alertas(tiendas, ventas, gastos, depositos)
    for columna, valor in [("region", region), ("tienda", tienda), ("severidad", severidad), ("tipo", tipo)]:
        if valor:
            al = al[al[columna] == valor]
    al = conciliacion.filtrar_periodo(al, desde, hasta, columna="periodo")
    return _registros(al)


def _proyectar(tienda, meses, inversion_inicial, escenario, **cambios):
    tiendas, ventas, gastos, _ = _datos()
    if tienda not in set(tiendas["tienda"]):
        raise HTTPException(404, f"No existe la tienda {tienda}")
    if escenario not in ESCENARIOS:
        raise HTTPException(422, f"Escenario inválido. Opciones: {list(ESCENARIOS)}")
    supuestos = calibrar_supuestos(curva_historica(tiendas, ventas, gastos))
    for nombre, valor in cambios.items():
        if valor is not None:
            supuestos[nombre] = valor
    tabla, resumen = proyectar_tienda_nueva(**supuestos, meses=meses, inversion_inicial=inversion_inicial, **ESCENARIOS[escenario])
    apertura = tiendas.set_index("tienda").loc[tienda, "fecha_apertura"]
    real = ventas[ventas["tienda"] == tienda].copy()
    real["mes_n"] = (real["fecha"].dt.year - apertura.year) * 12 + (real["fecha"].dt.month - apertura.month) + 1
    real = real[real["mes_n"] >= 1].groupby("mes_n", as_index=False)["venta"].sum().rename(columns={"venta": "venta_real"})
    tabla = tabla.merge(real, on="mes_n", how="left")
    return {"tienda": tienda, "escenario": escenario, "supuestos": supuestos, "resumen": resumen, "curva": _registros(tabla)}


@app.get("/proyecciones/{tienda}")
def proyeccion(tienda: str, meses: int = Query(36, ge=6, le=120), inversion_inicial: float = Query(0.0, ge=0),
               escenario: str = "Base", venta_inicial: Optional[float] = None, crecimiento_mensual: Optional[float] = None,
               margen_bruto: Optional[float] = None, gastos_fijos: Optional[float] = None, venta_madura: Optional[float] = None):
    """Curva de flujo y mes de punto de equilibrio. Los supuestos se pueden editar
    por parámetro; si no se mandan, se calibran con las tiendas ya abiertas.
    Para una tienda existente se agrega su venta real por mes de operación."""
    return _proyectar(tienda, meses, inversion_inicial, escenario, venta_inicial=venta_inicial,
                      crecimiento_mensual=crecimiento_mensual, margen_bruto=margen_bruto,
                      gastos_fijos=gastos_fijos, venta_madura=venta_madura)


@app.get("/proyecciones/{tienda}/escenarios")
def proyeccion_escenarios(tienda: str, meses: int = Query(36, ge=6, le=120), inversion_inicial: float = Query(5_500_000.0, ge=0)):
    """Los tres escenarios juntos (Pesimista, Base, Optimista) para compararlos en una gráfica.
    Por defecto la inversión es de $5.5 millones (cifra pública de referencia); es editable."""
    return {"tienda": tienda, "inversion_inicial": inversion_inicial,
            "escenarios": {e: _proyectar(tienda, meses, inversion_inicial, e) for e in ESCENARIOS}}


@app.get("/cuadre")
def cuadre():
    """¿Cuadran las cifras entre vistas? Para la auditoría antes de la demo."""
    tiendas, ventas, gastos, depositos = _datos()
    return {
        "revisiones": {k: {"cuadra": ok, "diferencia": dif} for k, (ok, dif) in conciliacion.verificar_cuadre(tiendas, ventas, gastos).items()},
        "problemas_de_datos": validar_datos(tiendas, ventas, gastos, depositos),
    }


@app.get("/auditoria/{tienda}")
def auditoria(tienda: str, mes: str = Query(..., description="AAAA-MM-01")):
    """Cifras de una tienda y un mes recalculadas desde los datos crudos."""
    _, ventas, gastos, depositos = _datos()
    return conciliacion.auditar_tienda(tienda, mes, ventas, gastos, depositos)


@app.post("/cargar-csv")
async def cargar_csv(tiendas: UploadFile = File(...), ventas: UploadFile = File(...),
                     gastos: UploadFile = File(...), depositos: UploadFile = File(...)):
    """Carga, limpia y valida los 4 archivos (CSV o Excel .xlsx); si todo bien, reemplaza los datos en uso."""
    limpias, bitacora = {}, {}
    for nombre, archivo in [("tiendas", tiendas), ("ventas", ventas), ("gastos", gastos), ("depositos", depositos)]:
        contenido = await archivo.read()
        try:
            limpias[nombre], bitacora[nombre] = leer_y_limpiar(contenido, archivo.filename or f"{nombre}.csv", nombre)
        except ValueError as error:
            raise HTTPException(422, f"{archivo.filename}: {error}") from error
    try:
        tiendas_df = completar_tiendas(limpias["tiendas"])
        problemas = validar_datos(tiendas_df, limpias["ventas"], limpias["gastos"], limpias["depositos"])
        # Prueba de humo: el motor debe poder calcular con estos datos antes de reemplazar los vigentes.
        conciliacion.kpis(tiendas_df, limpias["ventas"], limpias["gastos"], limpias["depositos"])
        generar_alertas(tiendas_df, limpias["ventas"], limpias["gastos"], limpias["depositos"])
    except Exception as error:  # noqa: BLE001
        raise HTTPException(422, f"Los archivos se leyeron pero no se pudieron calcular (se conservan los datos anteriores): {error}") from error
    _estado["datos"] = (tiendas_df, limpias["ventas"], limpias["gastos"], limpias["depositos"])
    _estado["origen"] = "carga manual (POST /cargar-csv)"
    return {"ok": True, "filas": {k: len(v) for k, v in limpias.items()}, "bitacora": bitacora, "problemas": problemas}


# Si la interfaz ya está compilada (frontend/dist), la API la sirve en "/": con un solo link
# (por ejemplo, un túnel de Cloudflare) quedan publicadas la interfaz y los datos.
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="interfaz")
