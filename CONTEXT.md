RETO 7  ·  CONTROL FINANCIERO Y FLUJO DE EFECTIVO POR TIENDA
Visibilidad del gasto y del efectivo en una red que crece rápido

PROBLEMÁTICA
Con aperturas constantes, el área financiera necesita saber rápido cuánto cuesta operar cada tienda, cuándo una tienda nueva se vuelve rentable y dónde hay gastos o diferencias de efectivo 
fuera de lo normal. Cuando esta información llega tarde o en archivos separados, las desviaciones se detectan después de que afectaron el margen.
OBJETIVO DEL RETO
Desarrollar una herramienta que consolide ingresos y gastos por tienda (o región), proyecte el flujo de efectivo de tiendas nuevas y alerte sobre gastos atípicos o diferencias entre venta y depósito.
ENTREGABLES ESPERADOS
Vista consolidada de ingresos, gastos y margen por tienda o región, con filtros por periodo.
Regla o modelo de detección de gastos fuera de patrón (por ejemplo, desviación frente al histórico o a tiendas similares).
Proyección simple del flujo de efectivo de una tienda nueva durante sus primeros meses.
Lista priorizada de alertas con una acción sugerida para cada una.
STACK / LINEAMIENTOS TÉCNICOS SUGERIDOS
Python o Excel avanzado para limpiar y consolidar datos, y un tablero ligero para la visualización. Las reglas de alerta pueden ser simples y explicables; se valora más que el equipo financiero
pueda confiar en ellas que un modelo complejo.
CRITERIOS DE EVALUACIÓN
Criterio,                  Peso,      Qué se evalúa
Utilidad para finanzas      30%       Responde preguntas reales de control de gasto y efectivo, no solo muestra datos.
Calidad de las alertas      25%       Detecta desviaciones relevantes con pocas falsas alarmas y explica por qué alertó.
Rigor de los números        25%       Las cifras cuadran entre vistas y los supuestos de la proyección son razonables.
Claridad de presentación    20%       Un directivo entiende el resultado y la acción recomendada en pocos minutos.

REGLAS PARA LAS IA:
1. No inventar cifras. Todo número debe venir de los datos del repositorio o de un supuesto escrito en docs/supuestos.md.
2. Las reglas de alerta deben ser simples y explicables: cada alerta indica qué regla la disparó y con qué cifras.
3. Antes de dar un resultado por bueno, comprobar que las cifras cuadran entre vistas (ventas - gastos = margen, por tienda y por región).
4. Usar solo datos de ejemplo o los datos entregados en el evento. No subir datos reales de la empresa, claves ni credenciales.
5. La IA nunca calcula: solo redacta o filtra sobre resultados ya calculados por motor/. Si una pregunta no se puede responder con los datos, lo dice.
6. Dejar el código comentado y en español, para que cualquier integrante lo entienda y lo pueda defender.
7. Cada integrante trabaja en su carpeta y en su propia rama; los cambios entran por pull request.
8. Si algo es ambiguo, anotarlo como pregunta en docs/supuestos.md en lugar de decidir en silencio.

## CONTRATO DE DATOS

Si alguien cambia un campo, lo avisa en el chat del equipo antes de subirlo.

Archivos CSV con encabezados (en `data/`, con el prefijo `ejemplo_` en los de práctica):

| Archivo | Columnas obligatorias | Notas |
|---------|----------------------|-------|
| `tiendas.csv` | `tienda`, `region`, `fecha_apertura` | `formato` es opcional (si falta, todas son "Estándar"). Se supone que las tiendas abren el día 1 de un mes |
| `ventas.csv` | `tienda`, `fecha`, `venta` | Venta diaria del punto de venta |
| `gastos.csv` | `tienda`, `fecha`, `categoria`, `monto` | Categorías: `costo_mercancia`, `renta`, `luz`, `nomina`, `mantenimiento`, `merma` |
| `depositos.csv` | `tienda`, `fecha`, `deposito` | Depósito bancario diario |

Los archivos reales se convierten a este formato con `data/limpieza.py` (reconoce otros nombres de columna, fechas dd/mm/aaaa, montos con `$` y comas, duplicados y vacíos, y deja una bitácora de lo que corrigió).

## ENDPOINTS (api/main.py)

| Endpoint | Qué regresa |
|----------|-------------|
| `GET /kpis?region=&tienda=&desde=&hasta=` | Ventas, gastos, margen, depósitos y diferencia de efectivo |
| `GET /consolidado?nivel=tienda\|region` | Ingresos, gastos y margen por mes |
| `GET /alertas?severidad=&tipo=&region=&tienda=` | Alertas priorizadas con motivo y acción sugerida |
| `GET /proyecciones/{tienda}` | Curva de flujo, supuestos y mes de punto de equilibrio |
| `GET /cuadre` · `GET /auditoria/{tienda}?mes=` | Verificación de que las cifras cuadran y recálculo desde datos crudos |
| `POST /cargar-csv` | Carga, limpia y valida los 4 archivos en vivo |

Formato de cada alerta: `prioridad`, `tipo`, `tienda`, `region`, `periodo`, `categoria`, `valor`, `referencia`, `desviacion_pct`, `monto_en_riesgo`, `severidad` (Crítica, Alta o Media), `motivo`, `accion_sugerida`.
