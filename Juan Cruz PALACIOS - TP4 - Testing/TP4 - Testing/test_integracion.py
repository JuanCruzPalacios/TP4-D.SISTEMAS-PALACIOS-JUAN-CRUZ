from datetime import date
from decimal import Decimal

import pytest

import pedidos
from checkout import CheckoutError

HOY_VIGENTE = date(2026, 10, 1)


@pytest.fixture
def ruta(tmp_path):
    return str(tmp_path / "tienda.db")


@pytest.fixture
def con(ruta):
    conexion = pedidos.conectar(ruta)
    pedidos.crear_esquema(conexion)
    yield conexion
    conexion.close()


def item(producto="buzo", talle="M", cantidad=1, **extra):
    return {"producto": producto, "talle": talle, "cantidad": cantidad, **extra}


def contar(ruta, tabla):
    assert tabla in ("pedidos", "items")
    otra = pedidos.conectar(ruta)
    try:
        return otra.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    finally:
        otra.close()


def test_un_id_inexistente_devuelve_none(con):
    assert pedidos.obtener_pedido(con, 999) is None


def test_si_checkout_falla_no_se_guarda_ni_el_pedido_ni_los_items(con, ruta):
    carrito = [item(), item(talle="XXXL")]

    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")

    assert error.value.code == "TALLE_INVALIDO"
    assert contar(ruta, "pedidos") == 0
    assert contar(ruta, "items") == 0


def test_otra_conexion_ve_el_pedido_completo(con, ruta):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item("buzo"), item("remera", talle="L")], "CABA")
    otra = pedidos.conectar(ruta)

    pedido = pedidos.obtener_pedido(otra, pedido_id)
    otra.close()

    assert pedido["total"] == Decimal("39499.40")
    assert [i["producto"] for i in pedido["items"]] == ["buzo", "remera"]


def test_los_montos_se_leen_como_decimal_sin_perdida(con):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item("buzo", cantidad=2), item("remera")],
                                       "CABA", "EGRESADOS2026", HOY_VIGENTE)

    pedido = pedidos.obtener_pedido(con, pedido_id)

    montos = [pedido["subtotal"], pedido["descuento"], pedido["envio"], pedido["total"]]
    assert all(isinstance(monto, Decimal) for monto in montos)
    assert montos == [Decimal("61999.30"), Decimal("9299.90"), Decimal("2500.00"), Decimal("55199.40")]


def test_un_email_malicioso_no_altera_la_consulta(con):
    pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA")
    pedidos.guardar_pedido(con, "beto@mail.com", [item()], "CABA")

    resultado = pedidos.pedidos_de(con, "x' OR '1'='1")

    assert resultado == []
