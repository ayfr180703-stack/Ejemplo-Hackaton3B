# Plan de trabajo, Reto 7: control financiero y flujo de efectivo por tienda

Sigue el plan de roles del equipo (5 integrantes, un territorio por persona). Si una sola persona tiene que hacer varios roles, el orden recomendado está más abajo.

Los datos y criterios oficiales se entregan el sábado 21 de noviembre a las 9:00 am. Si difieren de lo que hay aquí, **prevalece lo que indique el organizador**.

## Qué ya está hecho (con datos de ejemplo)

| Pieza | Rol | Estado |
|-------|-----|--------|
| Contrato de datos y endpoints | Líder técnico | Listo en `CONTEXT.md` |
| Limpieza de CSV sucios (`data/limpieza.py`) | Líder técnico | Lista, con 5 pruebas |
| Consolidado, conciliación, cuadre y auditoría (`motor/conciliacion.py`) | Conciliación | Listo, con pruebas |
| Alertas: efectivo, gasto atípico, costo de mercancía y tienda nueva (`motor/alertas.py`) | Alertas y QA | Listas. Detectan los 11 problemas inyectados con 4 falsas alarmas, todas de severidad media |
| Proyección y punto de equilibrio (`motor/proyeccion.py`) | Alertas y QA | Lista. Reproduce el ejemplo de la propuesta (mes 6, acumulado -$128,439) |
| Catálogo de acciones (`motor/acciones.py`) | Nube, gráficas y acciones | Listo |
| API (`api/main.py`) | Alertas y QA | Lista, con pruebas |
| Tablero local de respaldo (`dashboard/app.py`) | Frontend | Listo |
| Interfaz web (`frontend/`) | Frontend | **Pendiente** |
| Despliegue en la nube (`infra/`) | Nube | **Pendiente** |
| Capa de inteligencia artificial (`/ai`) | Líder técnico | **Pendiente**, se deja para el final |

Para correrlo: `pip install -r requirements.txt`, luego `python -m pytest -q`, `uvicorn api.main:app --reload` o `streamlit run dashboard/app.py`.

## Pendientes por rol

### Líder técnico: datos, nube e inteligencia artificial (`/data`, `/ai`, `CONTEXT.md`)
- [ ] Con los CSV del evento: correr `limpiar_tabla` en cada archivo y leer la bitácora (qué se corrigió y qué se descartó).
- [ ] Si las columnas o categorías de los archivos reales son distintas, agregar los alias en `data/limpieza.py` y actualizar `CONTEXT.md`.
- [ ] Capa de IA (al final): resumen ejecutivo en 3 viñetas y buscador. La IA solo recibe tablas ya calculadas y nunca calcula. Endpoints: `GET /api/ai/resumen-ejecutivo` y `POST /api/ai/preguntar`.

### Conciliación y rigor contable (`motor/conciliacion.py`)
- [ ] Confirmar qué cuenta como "gasto" en los datos reales (¿incluye costo de mercancía?).
- [ ] Confirmar cuándo se deposita (mismo día, día siguiente) y si conviene conciliar por semana (hoy se hace así).
- [ ] Auditar 3 tiendas al azar a mano contra los CSV originales: `GET /auditoria/{tienda}?mes=` debe coincidir al centavo con lo que muestra el tablero.

### Alertas, proyección, API y pruebas (`motor/alertas.py`, `motor/proyeccion.py`, `api/`, `tests/`)
- [ ] Probar los umbrales con los datos reales (ver `docs/supuestos.md`): contar alertas, revisar 10 a mano y anotar cuántas son falsas alarmas.
- [ ] Ajustar los supuestos de la proyección con el equipo (inversión, escenarios).
- [ ] Probar la carga en vivo con archivos rotos: duplicados, fechas mal escritas, columnas faltantes y montos negativos.

### Interfaz (`/frontend`)
- [ ] Construir la pantalla descrita en `frontend/README.md` conectada a la API.
- [ ] Mientras tanto, el tablero de respaldo ya muestra las cuatro tarjetas, las alertas y la proyección.

### Nube, gráficas y acciones (`/infra`, `motor/acciones.py`, `/frontend/components/charts/`)
- [ ] Decidir dónde se publica la API (ver `infra/README.md`) y probar el despliegue antes del sábado.
- [ ] Gráficas: ingresos contra gastos por tienda y región, y curva de flujo acumulado marcando el mes de punto de equilibrio.
- [ ] Revisar el texto de cada acción en `motor/acciones.py`: que sea algo que una persona de finanzas pueda hacer mañana.
- [ ] Plan B: copia que corre en local y video corto de la demo.

## Plan de práctica: miércoles 18 y jueves 19 de noviembre

Todo el reto se practica con datos inventados antes del sábado; ese día solo se revisan los CSV reales contra lo que ya funciona.

Decisiones tomadas: interfaz en **React + Vite**; publicación en **Cloudflare**; la IA se decide después (probablemente DeepSeek).

| Bloque | Cuándo | Qué | Estado |
|--------|--------|-----|--------|
| 1 | Mié, tarde | API robusta: CORS, medición de tiempos, pruebas con archivos dañados | Hecho |
| 2 | Mié, tarde | Ensayo con datos sucios "reales" simulados: ajustar umbrales y contar falsas alarmas | Hecho |
| 3 | Mié, tarde | Revisar textos de acciones; endpoint de escenarios (pesimista, base, optimista) con inversión editable | Hecho |
| 4 | Mié, noche | Interfaz parte 1: proyecto React + Vite, tarjetas y filtro por región | Hecho |
| 5 | Jue, mañana | Interfaz parte 2: gráficas, flujo acumulado con punto de equilibrio, alertas con acción, carga en vivo | Hecho |
| 6 | Jue, mediodía | Despliegue en Cloudflare (o plan B: copia local y video) | Hecho: la API sirve la interfaz y se publica con un túnel de Cloudflare (ver README) |
| 7 | Jue, tarde | Auditoría de 3 tiendas al centavo y cuadre entre vistas | Pendiente |
| 8 | Jue, tarde | Capa de IA (resumen y buscador), solo si hay tiempo | Pendiente |
| 9 | Jue, cierre | Congelar versión y ensayar la demo de 3 minutos | Pendiente |

**Si falta tiempo:** una sola regla de gasto atípico (promedio de 3 meses), la IA solo como resumen ejecutivo, y conservar el cuadre al centavo, la conciliación y la acción sugerida, que cubren la mayor parte de la rúbrica.

## Día del evento (sábado 21 de noviembre)

Con la práctica hecha, este día se usa para meter los CSV oficiales, ajustar alias y umbrales, y ensayar.

| Horario | Qué se hace |
|---------|-------------|
| 9:00 - 9:30 | Lectura del reto, reglas y criterios. Anotar dudas. Confirmar que el entorno de nube responde |
| 9:30 - 10:00 | Inspeccionar los CSV oficiales, limpiar, estandarizar columnas y actualizar `CONTEXT.md` |
| 10:00 - 1:30 | Desarrollo en paralelo (cada quien en su carpeta y su rama) |
| 1:30 - 2:00 | Comida y corte de alcance: qué funciona y qué falta. Aplicar el plan "si falta tiempo" |
| 2:00 - 3:45 | Integración, despliegue y pruebas con datos atípicos |
| 3:45 - 4:30 | Auditar 3 tiendas al centavo contra los CSV crudos. Congelar la demo |
| 4:30 - 5:00 | Ensayo del recorrido de 3 minutos: problema, demo, impacto en números y siguientes pasos |
| 5:00 | Presentación |

## Guion de la demo

1. Abrir el tablero: cuatro tarjetas (ventas, gastos, margen neto, diferencia de efectivo).
2. Filtrar una región y abrir la alerta crítica con su explicación y su acción.
3. Abrir la curva de flujo de una tienda nueva y señalar el mes de punto de equilibrio.
4. Mostrar que las cifras cuadran (`GET /cuadre` o la pestaña "Cuadre").
5. Cargar un CSV nuevo en vivo y ver cómo se recalcula todo.

## Riesgos

- Los datos reales pueden traer otro formato: es lo que más puede retrasar todo. Por eso `limpieza.py` y el contrato de datos van primero.
- Un modelo complejo vale menos que reglas simples que finanzas pueda explicar.
- Si las cifras no cuadran entre vistas, se pierden puntos de "rigor de los números" (25%).
- Si falla la red durante la presentación: copia local y video de respaldo.
- Las pruebas de este repositorio usan datos inventados: **que pasen no garantiza que las reglas funcionen bien con los datos reales**.
