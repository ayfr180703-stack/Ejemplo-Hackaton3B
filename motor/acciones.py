"""Catálogo de acciones sugeridas por tipo de alerta.

Cada texto incluye el monto de la alerta, para que finanzas sepa qué hacer sin
abrir otra pantalla. Si se agrega un tipo de alerta nuevo, se agrega aquí.
"""

TIPO_EFECTIVO = "Diferencia venta vs depósito"
TIPO_GASTO = "Gasto atípico"
TIPO_COSTO = "Costo de mercancía alto"
TIPO_NUEVA = "Tienda nueva bajo proyección"

_POR_CATEGORIA = {
    "luz": "Revisar el recibo y los equipos de refrigeración; comparar con tiendas del mismo formato.",
    "renta": "Verificar el contrato, los ajustes por inflación y cargos extra.",
    "nomina": "Revisar plantilla, horas extra y altas del mes.",
    "mantenimiento": "Pedir las órdenes de servicio y la cotización; confirmar si es un cargo único.",
    "merma": "Revisar conteos de inventario, caducidades y la captura de merma.",
}


def _dinero(x):
    return f"${abs(x):,.0f}"


def accion_para(tipo, tienda, monto, categoria=None, periodo=None, falta=True):
    """Texto de la acción sugerida. 'monto' es el monto en riesgo."""
    if tipo == TIPO_EFECTIVO:
        if falta:
            return (f"Faltante de {_dinero(monto)} en {tienda}: auditar cortes de caja, "
                    f"fichas de depósito y arqueos de los últimos 5 días.")
        return (f"Sobrante de {_dinero(monto)} en {tienda}: revisar depósitos duplicados, "
                f"ventas sin registrar en el punto de venta y fichas de otras tiendas.")
    if tipo == TIPO_GASTO:
        base = _POR_CATEGORIA.get(categoria, "Pedir el soporte (factura o contrato) y confirmar si es un cargo único o recurrente.")
        mes = f" de {periodo:%Y-%m}" if periodo is not None else ""
        return f"Exceso de {_dinero(monto)} en {categoria}{mes} de {tienda}: {base}"
    if tipo == TIPO_COSTO:
        return (f"Costo de mercancía {_dinero(monto)} arriba de lo normal en {tienda}: "
                f"revisar mermas, precios de compra y captura de inventario.")
    if tipo == TIPO_NUEVA:
        return (f"{tienda} vende {_dinero(monto)} menos de lo proyectado: revisar surtido y horario, "
                f"y actualizar la proyección del punto de equilibrio.")
    return f"Revisar {tienda}: {_dinero(monto)} en riesgo."
