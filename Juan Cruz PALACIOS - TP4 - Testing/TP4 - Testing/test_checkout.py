from datetime import date
from decimal import Decimal

import pytest

from checkout import (
    CheckoutError,
    calcular_descuento,
    calcular_envio,
    calcular_subtotal,
    calcular_total,
    validar_item,
)

HOY_VIGENTE = date(2026, 10, 1)


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def codigo_de_error(funcion, *args):
    with pytest.raises(CheckoutError) as error:
        funcion(*args)
    return error.value.code


def test_cantidad_cero_es_invalida():
    assert codigo_de_error(validar_item, item(cantidad=0)) == "CANTIDAD_INVALIDA"


def test_cantidad_diez_es_valida():
    carrito = [item("remera", cantidad=10)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("119995.00")


def test_cinco_prendas_tienen_diez_por_ciento_de_descuento():
    carrito = [item("remera", cantidad=5)]

    resultado = calcular_total(carrito, "CABA")

    assert resultado["descuento"] == Decimal("5999.75")


def test_egresados2026_es_valido_el_30_de_noviembre():
    ultimo_dia = date(2026, 11, 30)

    descuento = calcular_descuento(100000, 1, "EGRESADOS2026", ultimo_dia)

    assert descuento == Decimal("15000.00")


def test_zona_inexistente_es_invalida():
    assert codigo_de_error(calcular_envio, Decimal("10000.00"), "MARTE") == "ZONA_INVALIDA"


def test_carrito_vacio_es_invalido():
    assert codigo_de_error(calcular_total, [], "CABA") == "CARRITO_VACIO"
