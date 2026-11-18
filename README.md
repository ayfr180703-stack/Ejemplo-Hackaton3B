# Ejemplo-Hackaton3B

Problema financiero, con la finalidad de practicar la colaboración entre 5 miembros del equipo para sacar una solución.

Reto: **Reto 7, control financiero y flujo de efectivo por tienda** (ver [CONTEXT.md](CONTEXT.md)).

## Estructura

| Carpeta | Contenido | Entregable de la ficha |
|---------|-----------|------------------------|
| `data/` | Datos de ejemplo o sintéticos (ingresos, gastos, depósitos por tienda) | Base para todo |
| `src/consolidacion/` | Limpieza y vista de ingresos, gastos y margen por tienda o región, con filtro por periodo | Vista consolidada |
| `src/alertas/` | Reglas de gastos fuera de patrón y de diferencias entre venta y depósito | Detección y lista priorizada de alertas |
| `src/proyeccion/` | Flujo de efectivo de una tienda nueva en sus primeros meses | Proyección simple |
| `dashboard/` | Tablero para la presentación | Claridad de presentación |
| `docs/` | Supuestos, plan de despliegue y guion de la presentación | Rigor de los números |

## Reparto sugerido (ajustar entre todos)

| Área | Responsable |
|------|-------------|
| Datos y consolidación | |
| Alertas | |
| Proyección de flujo de efectivo | |
| Tablero | |
| Presentación y supuestos | |

## Forma de trabajo

1. Nadie sube directo a la rama `main`. Cada persona trabaja en su propia rama, con nombre `area/nombre` (por ejemplo `alertas/brandon`).
2. Los cambios entran por pull request (solicitud para integrar cambios), y al menos otra persona lo revisa antes de integrarlo.
3. Commits chicos y con mensaje claro, en español.
4. Cada supuesto de negocio se anota en `docs/supuestos.md`.
5. No se suben datos reales de la empresa ni claves. Solo datos de ejemplo.
6. Antes de integrar, se revisa que las cifras cuadren entre vistas (ingresos, gastos y margen).

## Cómo correrlo

```bash
python -m venv .venv
source .venv/bin/activate      # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
