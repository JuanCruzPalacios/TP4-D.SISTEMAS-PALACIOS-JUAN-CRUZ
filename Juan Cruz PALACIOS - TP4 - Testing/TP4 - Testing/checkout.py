from datetime import date
from decimal import ROUND_HALF_UP, Decimal


class CheckoutError(Exception):
    def __init__(self, code, mensaje):
        super().__init__(mensaje)
        self.code = code
        self.mensaje = mensaje


CATALOGO = {
    "buzo": Decimal("24999.90"),
    "remera": Decimal("11999.50"),
    "campera": Decimal("47999.99"),
}

TALLES = ["XS", "S", "M", "L", "XL", "XXL"]

CUPONES = {
    "EGRESADOS2026": {"tipo": "porcentaje", "valor": Decimal("0.15"), "vence": date(2026, 11, 30)},
    "BIENVENIDA": {"tipo": "fijo", "valor": Decimal("3000.00"), "minimo": Decimal("20000.00")},
}

ENVIOS = {
    "CABA": Decimal("2500.00"),
    "GBA": Decimal("4000.00"),
    "INTERIOR": Decimal("6500.00"),
    "RETIRO": Decimal("0.00"),
}

PRENDAS_PARA_DESCUENTO = 5
DESCUENTO_POR_CANTIDAD = Decimal("0.10")
MINIMO_ENVIO_GRATIS = Decimal("60000.00")


def redondear(monto):
    return monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validar_item(item):
    producto = item.get("producto") if isinstance(item, dict) else None
    if not isinstance(producto, str) or producto not in CATALOGO:
        raise CheckoutError("PRODUCTO_INEXISTENTE", f"Producto inexistente: {producto!r}")

    talle = item.get("talle")
    if not isinstance(talle, str) or talle.strip().upper() not in TALLES:
        raise CheckoutError("TALLE_INVALIDO", f"Talle inválido: {talle!r}")

    cantidad = item.get("cantidad")
    if type(cantidad) is not int or not 1 <= cantidad <= 10:
        raise CheckoutError("CANTIDAD_INVALIDA", "La cantidad debe ser un entero entre 1 y 10")


def calcular_subtotal(carrito):
    if not isinstance(carrito, list) or not carrito:
        raise CheckoutError("CARRITO_VACIO", "El carrito está vacío")

    subtotal = Decimal("0.00")
    for item in carrito:
        validar_item(item)
        subtotal += CATALOGO[item["producto"]] * item["cantidad"]

    return subtotal


def calcular_descuento(subtotal, cantidad_prendas, cupon=None, fecha=None):
    if fecha is None:
        fecha = date.today()

    descuento_cantidad = Decimal("0.00")
    if cantidad_prendas >= PRENDAS_PARA_DESCUENTO:
        descuento_cantidad = redondear(subtotal * DESCUENTO_POR_CANTIDAD)

    descuento_cupon = Decimal("0.00")
    codigo = cupon.strip().upper() if isinstance(cupon, str) else cupon
    if codigo:
        if codigo not in CUPONES:
            raise CheckoutError("CUPON_INVALIDO", "El cupón no existe")

        datos = CUPONES[codigo]

        if datos["tipo"] == "porcentaje":
            if fecha > datos["vence"]:
                raise CheckoutError("CUPON_VENCIDO", "El cupón está vencido")
            descuento_cupon = redondear(subtotal * datos["valor"])

        else:
            if subtotal < datos["minimo"]:
                raise CheckoutError(
                    "CUPON_MINIMO_NO_ALCANZADO",
                    f"El cupón requiere una compra mínima de ${datos['minimo']}",
                )
            descuento_cupon = datos["valor"]

    return min(max(descuento_cantidad, descuento_cupon), subtotal)


def calcular_envio(subtotal, zona):
    zona = zona.strip().upper() if isinstance(zona, str) else zona

    if zona not in ENVIOS:
        raise CheckoutError(
            "ZONA_INVALIDA",
            f"Zona inválida. Opciones: {', '.join(ENVIOS)}",
        )

    if subtotal >= MINIMO_ENVIO_GRATIS:
        return Decimal("0.00")

    return ENVIOS[zona]


def calcular_total(carrito, zona, cupon=None, fecha=None):
    subtotal = calcular_subtotal(carrito)

    prendas = 0
    for item in carrito:
        prendas = prendas + item["cantidad"]

    descuento = calcular_descuento(subtotal, prendas, cupon, fecha)
    envio = calcular_envio(subtotal - descuento, zona)
    total = subtotal - descuento + envio

    resultado = {
        "subtotal": subtotal,
        "descuento": descuento,
        "envio": envio,
        "total": total,
    }
    return resultado
