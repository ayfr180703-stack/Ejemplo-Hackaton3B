# Plan de trabajo, Reto 7: control financiero y flujo de efectivo por tienda

Está pensado para avanzarlo por partes, una persona o las cinco. Cada fase dice qué archivo tocar, qué hacer y cuándo se considera terminada. Las fases 1 a 5 corresponden a los 4 entregables de la ficha (`CONTEXT.md`) más el tablero.

## Estado de partida

| Pieza | Estado |
|-------|--------|
| Datos de ejemplo (sintéticos) y generador | Listo (`data/generar_datos.py`) |
| Consolidado de ingresos, gastos y margen | Listo, falta ajustar a los datos reales |
| Reglas de alertas con motivo y acción sugerida | Listas, falta ajustar umbrales a los datos reales |
| Proyección de tienda nueva (3 escenarios) | Lista, falta definir supuestos con el equipo |
| Tablero (Streamlit) | Listo con 4 pestañas |
| Pruebas automáticas | 6 pruebas que pasan |

Para verlo corriendo: `pip install -r requirements.txt`, luego `streamlit run dashboard/app.py`. Para correr las pruebas: `python -m pytest -q`.

## Fase 1. Datos (la base de todo)
- **Archivos:** `data/`, `src/comun.py`.
- **Qué hacer:** cuando lleguen los datos reales del reto, convertirlos a las 4 tablas de `src/comun.py` (tiendas, ventas, gastos, depósitos). Si el formato es distinto, solo se cambia la función `cargar_datos`.
- **Revisar:** correr `validar_datos` y leer cada aviso (tiendas fuera del catálogo, días sin depósito, montos negativos, duplicados).
- **Listo cuando:** la pestaña "Cuadre y supuestos" muestra los datos sin avisos, o los avisos están anotados en `docs/supuestos.md`.

## Fase 2. Vista consolidada (entregable 1)
- **Archivos:** `src/consolidacion/consolidar.py`, pestaña "Consolidado".
- **Qué hacer:** confirmar qué cuenta como "gasto" en los datos reales (¿incluye el costo de mercancía?). Ajustar las categorías si cambian los nombres.
- **Listo cuando:** ingresos, gastos y margen por tienda y por región, con filtro de periodo, y la verificación de cuadre en verde.

## Fase 3. Alertas de gasto atípico (entregable 2)
- **Archivos:** `src/alertas/alertas.py` (función `alertas_gastos`).
- **Qué hacer:** probar los umbrales con los datos reales (40% sobre el historial propio, 60% sobre las tiendas de su región, mínimo $5,000). Contar cuántas alertas salen y revisar a mano 10 de ellas.
- **Meta:** pocas falsas alarmas. Si salen demasiadas, subir el monto mínimo o los porcentajes.
- **Listo cuando:** cada alerta explica por qué salió y la mayoría de las revisadas a mano tienen sentido.

## Fase 4. Diferencias entre venta y depósito (parte del entregable 2)
- **Archivos:** `src/alertas/alertas.py` (función `alertas_efectivo`).
- **Qué hacer:** confirmar con el reto cuándo se deposita (mismo día, día siguiente) y ajustar la comparación. Hoy se compara por semana para no alertar por depósitos que se hacen al día siguiente.
- **Listo cuando:** las diferencias grandes aparecen como alertas y los desfases normales no.

## Fase 5. Proyección de flujo de efectivo de una tienda nueva (entregable 3)
- **Archivos:** `src/proyeccion/proyeccion.py`, pestaña "Proyección tienda nueva".
- **Qué hacer:** definir con el equipo la inversión inicial y los escenarios (pesimista 85% de la venta, optimista 110%). Anotarlos en `docs/supuestos.md`.
- **Listo cuando:** se muestra el mes en que el flujo mensual se vuelve positivo, el mes en que se recupera la inversión y el efectivo máximo que necesita la tienda.

## Fase 6. Lista priorizada con acción sugerida (entregable 4)
- **Archivos:** `src/alertas/alertas.py` (función `generar_alertas`), pestaña "Alertas".
- **Qué hacer:** revisar el texto de cada acción sugerida para que sea algo que una persona de finanzas pueda hacer mañana. Ajustar los cortes de severidad (alta desde $30,000, media desde $10,000).
- **Listo cuando:** la lista sale ordenada por monto en riesgo y se puede descargar en CSV.

## Fase 7. Presentación (20% de la calificación)
- **Archivos:** `docs/` (agregar `presentacion.md` con el guion).
- **Guion de 5 minutos:** (1) el problema en una frase, (2) el consolidado, (3) las 3 alertas más importantes con su acción, (4) la proyección de una tienda nueva, (5) cómo sabemos que las cifras cuadran.
- **Ensayo:** correr el tablero completo con el cable de red desconectado, para no depender de internet.
- **Listo cuando:** un directivo entiende el resultado y la acción en pocos minutos.

## Fase 8. Publicar en Cloudflare
- **Archivos:** `docs/despliegue.md`.
- **Qué hacer:** decidir si el tablero se publica en vivo o solo se muestra desde una computadora. Streamlit necesita un servidor, así que si se quiere en Cloudflare hay que cambiar el tablero a una página estática. Tener siempre la opción de correrlo local como respaldo.

## Orden recomendado si lo haces tú solo

1. Fase 1 y 2 (con datos reales, lo más importante).
2. Fase 3 y 4 (alertas).
3. Fase 6 (lista priorizada).
4. Fase 5 (proyección).
5. Fase 7 (presentación).
6. Fase 8 (publicar), solo si sobra tiempo.

## Reparto entre 5 personas (para cuando se integren)

| Persona | Fases |
|---------|-------|
| 1. Datos | 1 y 2 |
| 2. Alertas de gasto | 3 y 6 |
| 3. Efectivo y depósitos | 4 |
| 4. Proyección | 5 |
| 5. Tablero y presentación | 7 y 8 |

## Riesgos

- Los datos reales pueden traer otro formato: la Fase 1 es la que más puede retrasar todo.
- Un modelo complejo vale menos que reglas simples que finanzas pueda explicar.
- Si las cifras no cuadran entre vistas, se pierde puntos de "rigor de los números" (25%).
