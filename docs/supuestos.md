# Supuestos del equipo

Cada supuesto que use el equipo (datos, alertas o proyección) se anota aquí, con quién lo propuso y por qué. El criterio "Rigor de los números" pesa 25%.

## Reglas de alertas (valores iniciales, se pueden ajustar)

| # | Regla | Umbral inicial | Dónde está en el código |
|---|-------|----------------|-------------------------|
| 1 | Gasto del mes contra el historial propio: se alerta si supera 40% la mediana de los últimos 6 meses de la misma tienda y categoría | 40% y mínimo $5,000 | `alertas_gastos` |
| 2 | Gasto del mes contra las tiendas de su región: se alerta si supera 60% la mediana | 60% y mínimo $5,000 | `alertas_gastos` |
| 3 | Costo de mercancía: se alerta si como % de la venta supera 3 puntos la mediana de su región | 3 puntos y mínimo $5,000 | `alertas_costo_mercancia` |
| 4 | Venta contra depósito: se alerta por semana si la diferencia supera 1.5% de la venta y $3,000 | 1.5% y $3,000 | `alertas_efectivo` |
| 5 | Severidad: alta desde $30,000 en riesgo, media desde $10,000 | | `generar_alertas` |

## Proyección de tienda nueva

| # | Supuesto | Propuesto por | Justificación |
|---|----------|---------------|---------------|
| 6 | La tienda abre el día 1 de un mes | | Evita meses de apertura incompletos |
| 7 | Se usa la mediana de las primeras 12 meses de las tiendas ya abiertas | | Resiste valores extremos |
| 8 | Después del mes 12 la tienda se mantiene igual que en el mes 12 | | Simplicidad |
| 9 | Inversión inicial de $500,000 | | **Pendiente de definir: es un valor de ejemplo** |
| 10 | Escenarios: pesimista (ventas 85%, gastos 105%), optimista (ventas 110%, gastos 98%) | | **Pendiente de validar con el equipo** |

## Datos

| # | Supuesto | Propuesto por | Justificación |
|---|----------|---------------|---------------|
| 11 | Los datos de `data/ejemplo_*.csv` son inventados (sintéticos) | | Se usan solo para practicar |
| 12 | "Gasto" incluye el costo de mercancía | | **Confirmar con los datos reales** |
