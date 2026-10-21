import copy
from datetime import date
from decimal import Decimal

import pytest

import checkout
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


def fijar_hoy(monkeypatch, dia):
    class FechaFija(date):
        @classmethod
        def today(cls):
            return dia

    monkeypatch.setattr(checkout, "date", FechaFija)


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

    descuento = calcular_descuento(Decimal("100000.00"), 1, "EGRESADOS2026", ultimo_dia)

    assert descuento == Decimal("15000.00")


def test_zona_inexistente_es_invalida():
    assert codigo_de_error(calcular_envio, Decimal("10000.00"), "MARTE") == "ZONA_INVALIDA"


def test_carrito_vacio_es_invalido():
    assert codigo_de_error(calcular_total, [], "CABA") == "CARRITO_VACIO"


def test_se_ignora_el_precio_que_trae_el_item():
    carrito = [item("remera", precio=1)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("11999.50")


@pytest.mark.parametrize("producto, precio", [
    ("buzo", Decimal("24999.90")),
    ("remera", Decimal("11999.50")),
    ("campera", Decimal("47999.99")),
])
def test_el_precio_de_cada_producto_sale_del_catalogo(producto, precio):
    carrito = [item(producto)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == precio


@pytest.mark.parametrize("producto", ["zapatilla", "Buzo", " buzo", "", None])
def test_producto_fuera_del_catalogo_es_inexistente(producto):
    assert codigo_de_error(validar_item, item(producto)) == "PRODUCTO_INEXISTENTE"


@pytest.mark.parametrize("talle", ["XS", "XXL", "m", "  M "])
def test_talle_valido_sin_importar_mayusculas_ni_espacios(talle):
    carrito = [item("remera", talle=talle)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("11999.50")


@pytest.mark.parametrize("talle", ["XXXL", "", "   ", None])
def test_talle_fuera_de_la_lista_es_invalido(talle):
    assert codigo_de_error(validar_item, item(talle=talle)) == "TALLE_INVALIDO"


def test_cantidad_uno_es_valida():
    carrito = [item("remera", cantidad=1)]

    subtotal = calcular_subtotal(carrito)

    assert subtotal == Decimal("11999.50")


@pytest.mark.parametrize("cantidad", [11, -1, 2.5, "2", None])
def test_cantidad_fuera_de_rango_o_no_entera_es_invalida(cantidad):
    assert codigo_de_error(validar_item, item(cantidad=cantidad)) == "CANTIDAD_INVALIDA"


def test_calcular_total_no_modifica_el_carrito():
    carrito = [item("remera", talle="m", precio=1)]
    copia = copy.deepcopy(carrito)

    calcular_total(carrito, "CABA")

    assert carrito == copia


def test_cuatro_prendas_no_tienen_descuento():
    descuento = calcular_descuento(Decimal("100000.00"), 4)

    assert descuento == Decimal("0.00")


def test_las_prendas_de_todos_los_items_se_suman_para_el_descuento():
    carrito = [item("buzo", cantidad=2), item("remera", cantidad=3)]

    resultado = calcular_total(carrito, "CABA")

    assert resultado["descuento"] == Decimal("8599.83")


def test_egresados2026_vencido_el_1_de_diciembre():
    dia_siguiente = date(2026, 12, 1)

    codigo = codigo_de_error(calcular_descuento, Decimal("100000.00"), 1, "EGRESADOS2026", dia_siguiente)

    assert codigo == "CUPON_VENCIDO"


def test_bienvenida_con_el_minimo_exacto_descuenta_3000():
    descuento = calcular_descuento(Decimal("20000.00"), 1, "BIENVENIDA")

    assert descuento == Decimal("3000.00")


def test_bienvenida_debajo_del_minimo_no_se_aplica():
    codigo = codigo_de_error(calcular_descuento, Decimal("19999.99"), 1, "BIENVENIDA")

    assert codigo == "CUPON_MINIMO_NO_ALCANZADO"


@pytest.mark.parametrize("cupon", ["egresados2026", "  EGRESADOS2026 "])
def test_cupon_sin_importar_mayusculas_ni_espacios(cupon):
    descuento = calcular_descuento(Decimal("100000.00"), 1, cupon, HOY_VIGENTE)

    assert descuento == Decimal("15000.00")


@pytest.mark.parametrize("cupon", [None, "", "   "])
def test_cupon_vacio_equivale_a_no_usar_cupon(cupon):
    descuento = calcular_descuento(Decimal("100000.00"), 1, cupon, HOY_VIGENTE)

    assert descuento == Decimal("0.00")


@pytest.mark.parametrize("cupon", ["NOEXISTE", "DEBUG100"])
def test_cupon_que_no_existe_es_invalido(cupon):
    codigo = codigo_de_error(calcular_descuento, Decimal("100000.00"), 1, cupon, HOY_VIGENTE)

    assert codigo == "CUPON_INVALIDO"


def test_cupon_y_descuento_por_cantidad_no_se_acumulan():
    descuento = calcular_descuento(Decimal("100000.00"), 5, "EGRESADOS2026", HOY_VIGENTE)

    assert descuento == Decimal("15000.00")


def test_se_aplica_el_descuento_por_cantidad_si_es_mayor_que_el_cupon():
    descuento = calcular_descuento(Decimal("100000.00"), 5, "BIENVENIDA")

    assert descuento == Decimal("10000.00")


def test_se_aplica_el_cupon_fijo_si_es_mayor_que_el_descuento_por_cantidad():
    descuento = calcular_descuento(Decimal("20000.00"), 5, "BIENVENIDA")

    assert descuento == Decimal("3000.00")


def test_sin_fecha_el_cupon_vale_si_hoy_es_el_ultimo_dia(monkeypatch):
    fijar_hoy(monkeypatch, date(2026, 11, 30))

    descuento = calcular_descuento(Decimal("100000.00"), 1, "EGRESADOS2026")

    assert descuento == Decimal("15000.00")


def test_sin_fecha_el_cupon_vence_si_hoy_es_despues_del_ultimo_dia(monkeypatch):
    fijar_hoy(monkeypatch, date(2026, 12, 1))

    codigo = codigo_de_error(calcular_descuento, Decimal("100000.00"), 1, "EGRESADOS2026")

    assert codigo == "CUPON_VENCIDO"


def test_los_importes_del_total_son_decimal():
    carrito = [item()]

    resultado = calcular_total(carrito, "CABA")

    assert all(isinstance(valor, Decimal) for valor in resultado.values())


def test_el_descuento_porcentual_redondea_el_medio_centavo_hacia_arriba():
    descuento = calcular_descuento(Decimal("11999.50"), 1, "EGRESADOS2026", HOY_VIGENTE)

    assert descuento == Decimal("1799.93")


@pytest.mark.parametrize("subtotal, esperado", [
    (Decimal("100.04"), Decimal("10.00")),
    (Decimal("100.05"), Decimal("10.01")),
    (Decimal("100.06"), Decimal("10.01")),
])
def test_el_descuento_por_cantidad_redondea_al_centavo(subtotal, esperado):
    descuento = calcular_descuento(subtotal, 5)

    assert descuento == esperado


@pytest.mark.parametrize("zona, costo", [
    ("CABA", Decimal("2500.00")),
    ("GBA", Decimal("4000.00")),
    ("INTERIOR", Decimal("6500.00")),
    ("RETIRO", Decimal("0.00")),
    ("gba", Decimal("4000.00")),
    ("  interior ", Decimal("6500.00")),
])
def test_costo_de_envio_segun_la_zona(zona, costo):
    envio = calcular_envio(Decimal("10000.00"), zona)

    assert envio == costo


@pytest.mark.parametrize("zona", ["", None])
def test_zona_vacia_o_que_no_es_texto_es_invalida(zona):
    assert codigo_de_error(calcular_envio, Decimal("10000.00"), zona) == "ZONA_INVALIDA"


@pytest.mark.parametrize("base, costo", [
    (Decimal("59999.99"), Decimal("2500.00")),
    (Decimal("60000.00"), Decimal("0.00")),
    (Decimal("60000.01"), Decimal("0.00")),
])
def test_envio_gratis_desde_60000(base, costo):
    envio = calcular_envio(base, "CABA")

    assert envio == costo


def test_el_envio_gratis_se_calcula_con_el_descuento_aplicado():
    carrito = [item("buzo", cantidad=2), item("remera")]

    resultado = calcular_total(carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE)

    assert resultado["envio"] == Decimal("2500.00")


def test_total_del_ejemplo_de_la_especificacion():
    carrito = [item("buzo", cantidad=2)]

    resultado = calcular_total(carrito, "CABA")

    assert resultado == {
        "subtotal": Decimal("49999.80"),
        "descuento": Decimal("0.00"),
        "envio": Decimal("2500.00"),
        "total": Decimal("52499.80"),
    }


def test_total_con_cupon_el_ultimo_dia():
    carrito = [item("remera")]

    resultado = calcular_total(carrito, "CABA", "EGRESADOS2026", date(2026, 11, 30))

    assert resultado == {
        "subtotal": Decimal("11999.50"),
        "descuento": Decimal("1799.93"),
        "envio": Decimal("2500.00"),
        "total": Decimal("12699.57"),
    }


def test_total_con_descuento_que_hace_pagar_el_envio():
    carrito = [item("buzo", cantidad=2), item("remera")]

    resultado = calcular_total(carrito, "CABA", "EGRESADOS2026", HOY_VIGENTE)

    assert resultado == {
        "subtotal": Decimal("61999.30"),
        "descuento": Decimal("9299.90"),
        "envio": Decimal("2500.00"),
        "total": Decimal("55199.40"),
    }


def test_total_con_envio_gratis():
    carrito = [item("buzo", cantidad=3)]

    resultado = calcular_total(carrito, "GBA")

    assert resultado == {
        "subtotal": Decimal("74999.70"),
        "descuento": Decimal("0.00"),
        "envio": Decimal("0.00"),
        "total": Decimal("74999.70"),
    }


@pytest.mark.parametrize("carrito, zona, cupon, esperado", [
    ([], "MARTE", None, "CARRITO_VACIO"),
    ([item("zapatilla", talle="XXXL")], "CABA", None, "PRODUCTO_INEXISTENTE"),
    ([item(talle="XXXL", cantidad=0)], "CABA", None, "TALLE_INVALIDO"),
    ([item(cantidad=0), item("zapatilla")], "CABA", None, "CANTIDAD_INVALIDA"),
    ([item(talle="XXXL")], "CABA", "NOEXISTE", "TALLE_INVALIDO"),
    ([item()], "MARTE", "NOEXISTE", "CUPON_INVALIDO"),
])
def test_con_varios_errores_se_informa_el_primero_segun_el_orden(carrito, zona, cupon, esperado):
    assert codigo_de_error(calcular_total, carrito, zona, cupon) == esperado
