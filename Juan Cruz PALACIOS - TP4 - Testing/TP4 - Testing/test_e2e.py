import json
import threading
import urllib.error
import urllib.request
from decimal import Decimal

import pytest

import api

RUTA = "/api/v1/pedidos"


@pytest.fixture
def url(tmp_path):
    servidor = api.crear_servidor(str(tmp_path / "tienda.db"), 0)
    threading.Thread(target=servidor.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}"
    servidor.shutdown()
    servidor.server_close()


def pedir(url, metodo, ruta, cuerpo=None, crudo=None):
    datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
    req = urllib.request.Request(url + ruta, data=datos, method=metodo,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def compra(**cambios):
    cuerpo = {"email": "ana@mail.com", "zona": "CABA",
              "carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1}]}
    cuerpo.update(cambios)
    return cuerpo


def montos(cuerpo, *claves):
    assert all(isinstance(cuerpo[clave], str) for clave in claves)
    return [Decimal(cuerpo[clave]) for clave in claves]


def test_una_ruta_inexistente_devuelve_404(url):
    status, cuerpo = pedir(url, "GET", "/api/v1/otra")
    assert status == 404
    assert cuerpo["error"]["code"] == "RUTA_INEXISTENTE"


def test_un_post_a_una_ruta_inexistente_devuelve_404(url):
    status, cuerpo = pedir(url, "POST", "/api/v1/otra", compra())

    assert status == 404
    assert cuerpo["error"]["code"] == "RUTA_INEXISTENTE"


def test_crear_un_pedido_devuelve_201_con_los_montos_como_texto(url):
    cuerpo_pedido = compra(carrito=[{"producto": "remera", "talle": "M", "cantidad": 1}],
                           cupon="EGRESADOS2026", fecha="2026-11-30")

    status, cuerpo = pedir(url, "POST", RUTA, cuerpo_pedido)

    assert status == 201
    assert isinstance(cuerpo["id"], int)
    assert montos(cuerpo, "subtotal", "descuento", "envio", "total") == [
        Decimal("11999.50"), Decimal("1799.93"), Decimal("2500.00"), Decimal("12699.57")]


def test_crear_un_pedido_sin_cupon_ni_fecha(url):
    status, cuerpo = pedir(url, "POST", RUTA, compra())

    assert status == 201
    assert montos(cuerpo, "subtotal", "descuento", "envio", "total") == [
        Decimal("24999.90"), Decimal("0.00"), Decimal("2500.00"), Decimal("27499.90")]


def test_leer_el_pedido_creado_devuelve_lo_mismo_que_se_guardo(url):
    cuerpo_pedido = compra(email="  Ana@Mail.com ", zona="caba",
                           carrito=[{"producto": "remera", "talle": "m", "cantidad": 2},
                                    {"producto": "buzo", "talle": "L", "cantidad": 1}],
                           cupon="egresados2026", fecha="2026-11-30")
    _, creado = pedir(url, "POST", RUTA, cuerpo_pedido)

    status, pedido = pedir(url, "GET", f"{RUTA}/{creado['id']}")

    assert status == 200
    assert pedido["id"] == creado["id"]
    assert pedido["email"] == "ana@mail.com"
    assert pedido["zona"] == "CABA"
    assert pedido["cupon"] == "EGRESADOS2026"
    assert montos(pedido, "subtotal", "descuento", "envio", "total") == montos(
        creado, "subtotal", "descuento", "envio", "total")
    assert montos(pedido, "subtotal", "descuento", "envio", "total") == [
        Decimal("48998.90"), Decimal("7349.84"), Decimal("2500.00"), Decimal("44149.06")]
    assert [(i["producto"], i["talle"], i["cantidad"]) for i in pedido["items"]] == [
        ("remera", "M", 2), ("buzo", "L", 1)]
    assert [montos(i, "precio_unitario") for i in pedido["items"]] == [
        [Decimal("11999.50")], [Decimal("24999.90")]]


def test_un_error_de_negocio_devuelve_422_con_su_code(url):
    cuerpo_pedido = compra(carrito=[{"producto": "buzo", "talle": "XXXL", "cantidad": 1}])

    status, cuerpo = pedir(url, "POST", RUTA, cuerpo_pedido)

    assert status == 422
    assert cuerpo["error"]["code"] == "TALLE_INVALIDO"
    assert isinstance(cuerpo["error"]["message"], str)


def test_un_cupon_vencido_por_la_fecha_enviada_devuelve_422(url):
    cuerpo_pedido = compra(cupon="EGRESADOS2026", fecha="2026-12-01")

    status, cuerpo = pedir(url, "POST", RUTA, cuerpo_pedido)

    assert status == 422
    assert cuerpo["error"]["code"] == "CUPON_VENCIDO"


@pytest.mark.parametrize("crudo", [b"{esto no es json", b""])
def test_un_cuerpo_que_no_es_json_devuelve_400(url, crudo):
    status, cuerpo = pedir(url, "POST", RUTA, crudo=crudo)

    assert status == 400
    assert cuerpo["error"]["code"] == "JSON_INVALIDO"
    assert isinstance(cuerpo["error"]["message"], str)


@pytest.mark.parametrize("cuerpo_pedido", [
    {"zona": "CABA", "carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1}]},
    {"email": "ana@mail.com", "carrito": [{"producto": "buzo", "talle": "M", "cantidad": 1}]},
    {"email": "ana@mail.com", "zona": "CABA"},
    compra(email=123),
    compra(zona=["CABA"]),
    compra(carrito="buzo"),
])
def test_faltan_datos_o_tienen_otro_tipo_devuelve_400(url, cuerpo_pedido):
    status, cuerpo = pedir(url, "POST", RUTA, cuerpo_pedido)

    assert status == 400
    assert cuerpo["error"]["code"] == "DATOS_INCOMPLETOS"
    assert isinstance(cuerpo["error"]["message"], str)


@pytest.mark.parametrize("fecha", ["30/11/2026", "manana"])
def test_una_fecha_con_otro_formato_devuelve_400(url, fecha):
    status, cuerpo = pedir(url, "POST", RUTA, compra(fecha=fecha))

    assert status == 400
    assert cuerpo["error"]["code"] == "FECHA_INVALIDA"
    assert isinstance(cuerpo["error"]["message"], str)


def test_un_pedido_que_no_existe_devuelve_404(url):
    status, cuerpo = pedir(url, "GET", f"{RUTA}/999")

    assert status == 404
    assert cuerpo["error"]["code"] == "PEDIDO_INEXISTENTE"
    assert isinstance(cuerpo["error"]["message"], str)
