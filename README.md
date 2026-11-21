# Ejemplo-Hackaton3B

Problema financiero, con la finalidad de practicar la colaboración entre 5 miembros del equipo para sacar una solución.

Reto: **Reto 7, control financiero y flujo de efectivo por tienda** (ficha y contrato de datos en [CONTEXT.md](CONTEXT.md)). El plan paso a paso está en [docs/PLAN.md](docs/PLAN.md).

## Estructura (un territorio por rol)

| Carpeta | Contenido |
|---------|-----------|
| `data/` | Contrato de datos, `limpieza.py` (convierte CSV sucios al formato del equipo), datos sintéticos de ejemplo y su generador |
| `motor/conciliacion.py` | Consolidado de ingresos, gastos y margen; conciliación de venta contra depósito; cuadre y auditoría |
| `motor/alertas.py` | Reglas de alerta explicables, con severidad (Crítica, Alta, Media) |
| `motor/acciones.py` | Catálogo de acciones sugeridas por tipo de alerta, con el monto en el texto |
| `motor/proyeccion.py` | Proyección de flujo de efectivo y punto de equilibrio de una tienda nueva |
| `api/` | API en FastAPI que expone el motor (`/kpis`, `/alertas`, `/proyecciones/{tienda}`, `/cargar-csv`) |
| `frontend/` | Interfaz web en React + Vite (tarjetas, filtros, gráficas, alertas, escenarios y carga de archivos); ver `frontend/README.md` |
| `dashboard/` | Tablero local de respaldo en Streamlit, para la demo si falla la red |
| `infra/` | Despliegue en la nube (ver `infra/README.md`) |
| `tests/` | Pruebas automáticas (46) |
| `docs/` | Plan, supuestos y guion de la presentación |

## Cómo correrlo

```bash
python -m venv .venv
source .venv/bin/activate      # En Windows: .venv\Scripts\activate
pip install -r requirements.txt

python data/generar_datos.py   # opcional: vuelve a crear los datos de ejemplo
python -m pytest -q            # pruebas
uvicorn api.main:app --reload  # API (y la interfaz compilada en "/"), con documentación en http://127.0.0.1:8000/docs
streamlit run dashboard/app.py # tablero local de respaldo
```

## Forma de trabajo

1. Nadie sube directo a la rama `main`. Cada persona trabaja en su carpeta y en su propia rama (por ejemplo `alertas/nombre`).
2. Los cambios entran por pull request (solicitud para integrar cambios), y al menos otra persona lo revisa antes de integrarlo.
3. Commits chicos y con mensaje claro, en español.
4. Cada supuesto de negocio se anota en `docs/supuestos.md`.
5. Si se cambia una columna del contrato de datos, se avisa al equipo antes de subirlo.
6. No se suben datos reales de la empresa ni claves. Solo datos de ejemplo o los entregados en el evento.
7. Antes de integrar, se corre `python -m pytest -q` y se revisa que las cifras cuadren entre vistas.


## Demo con un solo link (interfaz + API)

La interfaz compilada vive en `frontend/dist` y la API la sirve sola. Desde la raíz del repositorio:

```
python -m uvicorn api.main:app
```

Abre http://127.0.0.1:8000. Para compartirlo en internet sin cuenta, en otra terminal:

```
cloudflared tunnel --url http://localhost:8000
```

(`cloudflared` se instala con `winget install Cloudflare.cloudflared`). El link `https://....trycloudflare.com` que imprime es la demo pública; funciona mientras la computadora y las dos terminales sigan abiertas. Si se cambia el código de `frontend/src`, hay que recompilar: `cd frontend && npm run build`.
