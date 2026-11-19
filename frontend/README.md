# Frontend (interfaz ejecutiva)

React + Vite. Hecho: tarjetas, filtros y panel de alertas. Falta: gráficas y carga de archivos en vivo.

## Cómo correrlo

```
uvicorn api.main:app --reload          # terminal 1, desde la raíz del repositorio
cd frontend && npm install && npm run dev   # terminal 2, abre http://localhost:5173
```

La dirección de la API se cambia con `VITE_API_URL` (ver `.env.example`).

## Pantalla sugerida

1. Cuatro tarjetas arriba: ventas, gastos, margen neto y diferencia de efectivo (`GET /kpis`).
2. Filtros de región, tienda y periodo en la barra superior (los mismos parámetros que acepta la API).
3. Panel de alertas por severidad (Crítica, Alta, Media) con tienda, explicación y acción (`GET /alertas`).
4. Gráficas en `frontend/components/charts/`: ingresos contra gastos (`GET /consolidado`) y curva de flujo de tienda nueva (`GET /proyecciones/{tienda}`).
5. Botón para cargar CSV en vivo (`POST /cargar-csv`, formulario con los 4 archivos).

## Reglas

- Ninguna cifra se calcula en el navegador: todo sale de la API.
- Para probar sin servidor: `uvicorn api.main:app --reload` y abrir http://127.0.0.1:8000/docs.
- Mientras esta carpeta no exista completa, el tablero de respaldo es `dashboard/app.py`.
