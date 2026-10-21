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


def test_el_pedido_guardado_tiene_los_montos_que_calculo_checkout(con):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item("remera")], "CABA",
                                       "EGRESADOS2026", date(2026, 11, 30))

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido == {
        "id": pedido_id,
        "email": "ana@mail.com",
        "zona": "CABA",
        "cupon": "EGRESADOS2026",
        "subtotal": Decimal("11999.50"),
        "descuento": Decimal("1799.93"),
        "envio": Decimal("2500.00"),
        "total": Decimal("12699.57"),
        "items": [
            {"producto": "remera", "talle": "M", "cantidad": 1,
             "precio_unitario": Decimal("11999.50")},
        ],
    }


def test_los_montos_se_leen_como_decimal_sin_perdida(con):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item("buzo", cantidad=2), item("remera")],
                                       "CABA", "EGRESADOS2026", HOY_VIGENTE)

    pedido = pedidos.obtener_pedido(con, pedido_id)

    montos = [pedido["subtotal"], pedido["descuento"], pedido["envio"], pedido["total"]]
    assert all(isinstance(monto, Decimal) for monto in montos)
    assert montos == [Decimal("61999.30"), Decimal("9299.90"), Decimal("2500.00"), Decimal("55199.40")]


def test_si_checkout_falla_no_se_guarda_ni_el_pedido_ni_los_items(con, ruta):
    carrito = [item(talle="XXXL")]

    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")

    assert error.value.code == "TALLE_INVALIDO"
    assert contar(ruta, "pedidos") == 0
    assert contar(ruta, "items") == 0


def test_si_falla_el_ultimo_item_no_se_guarda_ningun_item(con, ruta):
    carrito = [item(), item("zapatilla")]

    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", carrito, "CABA")

    assert error.value.code == "PRODUCTO_INEXISTENTE"
    assert contar(ruta, "pedidos") == 0
    assert contar(ruta, "items") == 0


def test_si_la_zona_es_invalida_no_se_guarda_el_pedido(con, ruta):
    with pytest.raises(CheckoutError) as error:
        pedidos.guardar_pedido(con, "ana@mail.com", [item()], "MARTE")

    assert error.value.code == "ZONA_INVALIDA"
    assert contar(ruta, "pedidos") == 0


def test_otra_conexion_ve_el_pedido_completo(con, ruta):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item("buzo"), item("remera", talle="L")], "CABA")
    otra = pedidos.conectar(ruta)

    pedido = pedidos.obtener_pedido(otra, pedido_id)
    otra.close()

    assert pedido["total"] == Decimal("39499.40")
    assert [i["producto"] for i in pedido["items"]] == ["buzo", "remera"]


def test_otra_conexion_cuenta_todos_los_items(con, ruta):
    pedidos.guardar_pedido(con, "ana@mail.com", [item("buzo"), item("remera"), item("campera")], "CABA")

    cantidad_items = contar(ruta, "items")

    assert cantidad_items == 3


def test_el_precio_unitario_sale_del_catalogo(con):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item("buzo", precio=1)], "CABA")

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["items"][0]["precio_unitario"] == Decimal("24999.90")
    assert pedido["subtotal"] == Decimal("24999.90")


def test_los_datos_se_guardan_normalizados(con):
    pedido_id = pedidos.guardar_pedido(con, "  Ana@Mail.COM ", [item(talle=" m ")], " caba ",
                                       " egresados2026 ", HOY_VIGENTE)

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["email"] == "ana@mail.com"
    assert pedido["zona"] == "CABA"
    assert pedido["cupon"] == "EGRESADOS2026"
    assert pedido["items"][0]["talle"] == "M"


@pytest.mark.parametrize("cupon", [None, "", "   "])
def test_un_cupon_vacio_se_guarda_como_none(con, cupon):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA", cupon)

    pedido = pedidos.obtener_pedido(con, pedido_id)

    assert pedido["cupon"] is None


def test_pedidos_de_devuelve_del_mas_reciente_al_mas_antiguo(con):
    primero = pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA")
    pedidos.guardar_pedido(con, "beto@mail.com", [item()], "CABA")
    segundo = pedidos.guardar_pedido(con, "ana@mail.com", [item("remera")], "GBA")

    resultado = pedidos.pedidos_de(con, "ana@mail.com")

    assert [p["id"] for p in resultado] == [segundo, primero]


def test_pedidos_de_no_distingue_mayusculas_ni_espacios(con):
    pedido_id = pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA")

    resultado = pedidos.pedidos_de(con, "  ANA@mail.com ")

    assert [p["id"] for p in resultado] == [pedido_id]


def test_pedidos_de_un_email_sin_pedidos_devuelve_lista_vacia(con):
    pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA")

    resultado = pedidos.pedidos_de(con, "nadie@mail.com")

    assert resultado == []


def test_un_email_malicioso_no_altera_la_consulta(con):
    pedidos.guardar_pedido(con, "ana@mail.com", [item()], "CABA")
    pedidos.guardar_pedido(con, "beto@mail.com", [item()], "CABA")

    resultado = pedidos.pedidos_de(con, "x' OR '1'='1")

    assert resultado == []


def test_un_email_con_comilla_se_busca_sin_error(con):
    pedido_id = pedidos.guardar_pedido(con, "o'brien@mail.com", [item()], "CABA")

    resultado = pedidos.pedidos_de(con, "o'brien@mail.com")

    assert [p["id"] for p in resultado] == [pedido_id]
