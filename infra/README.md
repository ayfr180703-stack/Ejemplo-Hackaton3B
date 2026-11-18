# Infraestructura y despliegue

Territorio: nube y monitoreo. Pendiente de decidir y probar antes del sábado.

## Qué hay que publicar

| Pieza | Qué es | Dónde puede vivir |
|-------|--------|-------------------|
| API (`api/main.py`) | Servidor de Python (FastAPI) | Necesita un servicio con servidor: Render, Railway, Fly.io u otro. Cloudflare Pages no ejecuta Python |
| Frontend (`frontend/`) | Página web (React) | Cloudflare Pages, que publica páginas estáticas |
| Tablero de respaldo (`dashboard/`) | Streamlit | Se corre en una computadora local |

Si se quiere todo en Cloudflare: publicar el frontend en Cloudflare Pages y exponer la API con un túnel de Cloudflare (Cloudflare Tunnel) desde una computadora del equipo, o usar otro servicio para la API y apuntar el frontend hacia ella.

## Para decidir

- [ ] Dónde se publica la API y quién tiene la cuenta
- [ ] Cómo se guardan las claves (nunca en el código; usar variables de entorno)
- [ ] Qué hacer si falla la red durante la presentación

## Plan B obligatorio (congelar a las 3:45 pm del sábado)

1. Una copia que corre en local: `uvicorn api.main:app` y `streamlit run dashboard/app.py`.
2. Un video corto de la demo funcionando.
3. Los datos del evento ya cargados en esa copia local.
