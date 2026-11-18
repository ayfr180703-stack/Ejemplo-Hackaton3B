# Supuestos del equipo

Cada supuesto que use el equipo (datos, alertas o proyección) se anota aquí, con quién lo propuso y por qué. El criterio "Rigor de los números" pesa 25%. Los datos oficiales del evento tienen prioridad sobre cualquier supuesto de este archivo.

## Reglas de alertas (valores iniciales, ajustables)

| # | Regla | Umbral inicial | Dónde está |
|---|-------|----------------|------------|
| 1 | Efectivo: la diferencia venta menos depósito de la semana (lunes a domingo) supera un porcentaje de la venta | 0.5% de la venta. Crítica si además supera $5,000; si no, Media | `alertas_efectivo` |
| 2 | Gasto atípico: el gasto de una categoría supera el promedio móvil de 3 meses de la misma tienda **y** la mediana de tiendas del mismo formato y región | Más de 25% sobre ambos y exceso mínimo de $3,000 | `alertas_gasto_atipico` |
| 3 | Severidad del gasto atípico | Crítica: 100% o más sobre la referencia y $10,000 o más. Alta: $10,000 o más. Media: el resto | `alertas_gasto_atipico` |
| 4 | Costo de mercancía como % de la venta contra la mediana de su región | 3 puntos o más y $5,000 de exceso. Alta desde $30,000 | `alertas_costo_mercancia` |
| 5 | Tienda nueva bajo proyección: venta diaria promedio del mes contra su primer mes por el crecimiento típico | 10% por debajo = Media; 20% = Alta | `alertas_tiendas_nuevas` |
| 6 | Prioridad: primero severidad, luego monto en riesgo | | `generar_alertas` |

Los porcentajes de las reglas 1 y 2 vienen de la propuesta del equipo. Los mínimos en pesos, los cortes de severidad y las reglas 4 y 5 son valores iniciales míos: validar con los datos reales del evento.

Si en un grupo de menos de 3 tiendas del mismo formato y región no hay con quién comparar, se compara contra la mediana de la región.

## Proyección de tienda nueva

Modelo: venta del mes = venta inicial x (1 + crecimiento)^(mes - 1), con un tope opcional; resultado = venta x margen bruto - gastos fijos; el punto de equilibrio es el primer mes con resultado positivo.

| # | Supuesto | Valor inicial | Estado |
|---|----------|---------------|--------|
| 7 | Venta inicial, crecimiento mensual, venta madura, margen bruto y gastos fijos | Se calibran con la mediana de las tiendas ya abiertas | Editables en el tablero |
| 8 | Las tiendas abren el día 1 de un mes | | Confirmar con los datos reales |
| 9 | Los gastos operativos (incluida la merma) se tratan como fijos en la proyección | | Simplificación |
| 10 | Inversión inicial por tienda | $5.5 millones de pesos | Referencia pública: estimación promedio de la empresa, no un dato de las tiendas del evento |
| 11 | Escenarios: pesimista (ventas 85%, gastos 105%), optimista (ventas 110%, gastos 98%) | | Pendiente de validar con el equipo |

## Referencias públicas de la empresa (objetivos publicados, no garantías)

Según la presentación corporativa del 3T26 de BBB Foods (tomado del documento de investigación del equipo, con corte al 18 de noviembre de 2026):

| Año de operación | Ventas objetivo por tienda | Margen de tienda (4-wall) objetivo | Rendimiento sobre la inversión |
|------------------|----------------------------|------------------------------------|--------------------------------|
| 1 | $16.9 millones | 5.6% | 17% |
| 2 | $24.2 millones | 9.1% | 40% |
| 3 | $29.7 millones | 10.2% | 55% |

Inversión promedio estimada por tienda: $5.5 millones. Periodo de recuperación (payback) objetivo: 26 meses. Margen bruto de la empresa en el 3T26: 16.7%.

Estas cifras sirven para revisar que los supuestos de la proyección sean razonables. No se usan como dato de ninguna tienda.

## Datos

| # | Supuesto | Estado |
|---|----------|--------|
| 12 | Los archivos `data/ejemplo_*.csv` son inventados (sintéticos) y solo sirven para practicar | |
| 13 | "Gasto" incluye el costo de mercancía (categoría `costo_mercancia`) | Confirmar con los datos reales |
| 14 | Categorías de gasto: costo_mercancia, renta, luz, nomina, mantenimiento, merma | Confirmar con los datos reales |
