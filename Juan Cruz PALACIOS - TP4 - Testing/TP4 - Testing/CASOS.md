# Parte 1 — Casos de caja negra

Casos derivados solo de `ESPECIFICACION.md`, sin mirar el código.

Convenciones:

- Los importes son `Decimal`. `D("24999.90")` es `Decimal("24999.90")`.
- `item(...)` es un ítem `{"producto": ..., "talle": ..., "cantidad": ...}`. Si no se aclara, es `buzo`, `M`, `1`.
- Cuando se usa el cupón `EGRESADOS2026` sin hablar de su vencimiento, la fecha es `date(2026, 10, 1)`, que está vigente.
- "Error X" significa que se lanza `CheckoutError` con `code == "X"`.

---

## R1 — Catálogo y precios

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Producto `buzo` | válida | `calcular_subtotal([item("buzo")])` | `D("24999.90")` |
| Producto `remera` | válida | `calcular_subtotal([item("remera")])` | `D("11999.50")` |
| Producto `campera` | válida | `calcular_subtotal([item("campera")])` | `D("47999.99")` |
| Ítem con precio propio | válida | `calcular_subtotal([item("buzo", precio=1)])` | `D("24999.90")` (se ignora el precio del ítem) |
| Ítem con otra clave extra | válida | `calcular_subtotal([item("buzo", color="rojo")])` | `D("24999.90")` |
| Producto que no existe | inválida | `validar_item(item("zapatilla"))` | Error `PRODUCTO_INEXISTENTE` |
| Producto en mayúscula | inválida | `validar_item(item("Buzo"))` | Error `PRODUCTO_INEXISTENTE` |
| Producto con espacios | inválida | `validar_item(item(" buzo"))` | Error `PRODUCTO_INEXISTENTE` |
| Producto vacío | inválida | `validar_item(item(""))` | Error `PRODUCTO_INEXISTENTE` |

**Valores límite:** el nombre exacto (`"buzo"`) contra el nombre con una sola diferencia (`"Buzo"`, `" buzo"`) y el string vacío.

---

## R2 — Talles

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Talle válido en mayúscula | válida | `validar_item(item(talle="M"))` | no lanza error |
| Talle más chico | válida | `validar_item(item(talle="XS"))` | no lanza error |
| Talle más grande | válida | `validar_item(item(talle="XXL"))` | no lanza error |
| Talle en minúscula | válida | `validar_item(item(talle="m"))` | no lanza error |
| Talle con espacios alrededor | válida | `validar_item(item(talle="  M "))` | no lanza error |
| Talle que no existe | inválida | `validar_item(item(talle="XXXL"))` | Error `TALLE_INVALIDO` |
| Talle vacío | inválida | `validar_item(item(talle=""))` | Error `TALLE_INVALIDO` |
| Talle de solo espacios | inválida | `validar_item(item(talle="   "))` | Error `TALLE_INVALIDO` |
| Talle que no es texto | inválida | `validar_item(item(talle=None))` | Error `TALLE_INVALIDO` |

**Valores límite:** `XS` y `XXL` (los extremos de la lista), `XXXL` (justo afuera), `""` y `"   "` (vacío y solo espacios).

---

## R3 — Cantidad

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Entero entre 1 y 10 | válida | `validar_item(item(cantidad=5))` | no lanza error |
| Mínimo permitido | válida | `validar_item(item(cantidad=1))` | no lanza error |
| Máximo permitido | válida | `validar_item(item(cantidad=10))` | no lanza error |
| Menor al mínimo | inválida | `validar_item(item(cantidad=0))` | Error `CANTIDAD_INVALIDA` |
| Negativo | inválida | `validar_item(item(cantidad=-1))` | Error `CANTIDAD_INVALIDA` |
| Mayor al máximo | inválida | `validar_item(item(cantidad=11))` | Error `CANTIDAD_INVALIDA` |
| No entero (decimal) | inválida | `validar_item(item(cantidad=2.5))` | Error `CANTIDAD_INVALIDA` |
| No entero (texto) | inválida | `validar_item(item(cantidad="2"))` | Error `CANTIDAD_INVALIDA` |
| Sin valor | inválida | `validar_item(item(cantidad=None))` | Error `CANTIDAD_INVALIDA` |

**Valores límite:** `0`, `1`, `2` en el borde inferior y `9`, `10`, `11` en el borde superior. `1` y `10` son válidos; `0` y `11` no.

---

## R4 — Carrito

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Carrito con un ítem | válida | `calcular_total([item()], "CABA")` | devuelve el total, sin error |
| Carrito con varios ítems | válida | `calcular_total([item("buzo"), item("remera")], "CABA")` | devuelve el total, sin error |
| Carrito vacío | inválida | `calcular_total([], "CABA")` | Error `CARRITO_VACIO` |
| El carrito no se modifica | válida | `carrito = [item(talle=" m ", precio=1)]`, se guarda una copia y se llama `calcular_total(carrito, "CABA")` | `carrito` queda igual a la copia (`talle` sigue `" m "` y `precio` sigue `1`) |
| El carrito no se modifica aunque haya error | inválida | `carrito = [item(talle=" m "), item(talle="XXXL")]` y `calcular_total(carrito, "CABA")` | Error `TALLE_INVALIDO` y `carrito` queda igual a la copia |
| `validar_item` no modifica el ítem | válida | `i = item(talle="m")` y `validar_item(i)` | `i["talle"]` sigue siendo `"m"` |

**Valores límite:** carrito de 0 ítems (inválido) y de 1 ítem (válido).

---

## R5 — Descuento por cantidad

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Menos de 5 prendas | válida | `calcular_descuento(D("100000.00"), 4)` | `D("0.00")` |
| Exactamente 5 prendas | válida | `calcular_descuento(D("100000.00"), 5)` | `D("10000.00")` |
| Más de 5 prendas | válida | `calcular_descuento(D("100000.00"), 6)` | `D("10000.00")` |
| 5 prendas sumando varios ítems | válida | `calcular_total([item("buzo", cantidad=2), item("remera", cantidad=3)], "CABA")` | `descuento == D("8599.83")` (10% de 85998.30) |
| 4 prendas sumando varios ítems | válida | `calcular_total([item("buzo", cantidad=2), item("remera", cantidad=2)], "CABA")` | `descuento == D("0.00")` |

**Valores límite:** `4` (sin descuento), `5` (con descuento) y `6` (con descuento).

---

## R6 — Cupones

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| `EGRESADOS2026` vigente | válida | `calcular_descuento(D("100000.00"), 1, "EGRESADOS2026", date(2026, 10, 1))` | `D("15000.00")` |
| `EGRESADOS2026` el último día | válida | `calcular_descuento(D("11999.50"), 1, "EGRESADOS2026", date(2026, 11, 30))` | `D("1799.93")` |
| `EGRESADOS2026` el día anterior al último | válida | `calcular_descuento(D("100000.00"), 1, "EGRESADOS2026", date(2026, 11, 29))` | `D("15000.00")` |
| `EGRESADOS2026` vencido | inválida | `calcular_descuento(D("100000.00"), 1, "EGRESADOS2026", date(2026, 12, 1))` | Error `CUPON_VENCIDO` |
| `BIENVENIDA` con el mínimo exacto | válida | `calcular_descuento(D("20000.00"), 1, "BIENVENIDA")` | `D("3000.00")` |
| `BIENVENIDA` por encima del mínimo | válida | `calcular_descuento(D("20000.01"), 1, "BIENVENIDA")` | `D("3000.00")` |
| `BIENVENIDA` por debajo del mínimo | inválida | `calcular_descuento(D("19999.99"), 1, "BIENVENIDA")` | Error `CUPON_MINIMO_NO_ALCANZADO` |
| Cupón en minúscula | válida | `calcular_descuento(D("100000.00"), 1, "egresados2026", date(2026, 10, 1))` | `D("15000.00")` |
| Cupón con espacios alrededor | válida | `calcular_descuento(D("20000.00"), 1, "  bienvenida ")` | `D("3000.00")` |
| Sin cupón (`None`) | válida | `calcular_descuento(D("100000.00"), 1, None)` | `D("0.00")` |
| Cupón vacío | válida | `calcular_descuento(D("100000.00"), 1, "")` | `D("0.00")`, sin error |
| Cupón de solo espacios | válida | `calcular_descuento(D("100000.00"), 1, "   ")` | `D("0.00")`, sin error |
| Cupón que no existe | inválida | `calcular_descuento(D("100000.00"), 1, "NOEXISTE")` | Error `CUPON_INVALIDO` |
| Cupón que no está en la lista de la especificación | inválida | `calcular_descuento(D("100000.00"), 1, "DEBUG100")` | Error `CUPON_INVALIDO` (solo existen dos cupones) |
| Cupón mayor que el descuento por cantidad | válida | `calcular_descuento(D("100000.00"), 5, "EGRESADOS2026", date(2026, 10, 1))` | `D("15000.00")` (se aplica el mayor, no 25%) |
| Descuento por cantidad mayor que el cupón | válida | `calcular_descuento(D("100000.00"), 5, "BIENVENIDA")` | `D("10000.00")` (10% contra $ 3.000, no se suman) |
| Cupón fijo mayor que el 10% | válida | `calcular_descuento(D("20000.00"), 5, "BIENVENIDA")` | `D("3000.00")` (10% sería $ 2.000) |
| El descuento no supera el subtotal | válida | `calcular_descuento(D("20000.00"), 1, "BIENVENIDA")` | `D("3000.00")`, que es menor o igual a `D("20000.00")` |
| Sin fecha, llamado hasta el 30/11/2026 | válida | `calcular_descuento(D("100000.00"), 1, "EGRESADOS2026")` con la fecha del día en `2026-11-30` | `D("15000.00")` |
| Sin fecha, llamado después del 30/11/2026 | inválida | `calcular_descuento(D("100000.00"), 1, "EGRESADOS2026")` con la fecha del día en `2026-12-01` | Error `CUPON_VENCIDO` (se usa la fecha de la llamada, no una fija) |

**Valores límite:**

- Fecha de `EGRESADOS2026`: `29/11/2026` y `30/11/2026` son válidos, y `01/12/2026` está vencido.
- Mínimo de `BIENVENIDA`: `19999.99` no alcanza; `20000.00` y `20000.01` alcanzan.
- Cupón vacío: `None`, `""` y `"   "`.

---

## R7 — Dinero y redondeo

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Importes como `Decimal` | válida | `calcular_total([item()], "CABA")` | los cuatro valores son `Decimal`, ninguno `float` |
| Medio centavo redondea hacia arriba (cupón) | válida | `calcular_descuento(D("11999.50"), 1, "EGRESADOS2026", date(2026, 10, 1))` | `D("1799.93")` (1799.925) |
| Medio centavo redondea hacia arriba (otro precio) | válida | `calcular_descuento(D("24999.90"), 1, "EGRESADOS2026", date(2026, 10, 1))` | `D("3749.99")` (3749.985) |
| Medio centavo en el 10% | válida | `calcular_descuento(D("100.05"), 5)` | `D("10.01")` (10.005) |
| Debajo del medio centavo | válida | `calcular_descuento(D("100.04"), 5)` | `D("10.00")` (10.004) |
| Arriba del medio centavo | válida | `calcular_descuento(D("100.06"), 5)` | `D("10.01")` (10.006) |
| Suma de precios sin error de `float` | válida | `calcular_subtotal([item("remera", cantidad=5)])` | `D("59997.50")` exacto |

**Valores límite:** la tercera cifra decimal en `4` (baja), `5` (sube) y `6` (sube).

---

## R8 — Envío

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Zona `CABA` | válida | `calcular_envio(D("10000.00"), "CABA")` | `D("2500.00")` |
| Zona `GBA` | válida | `calcular_envio(D("10000.00"), "GBA")` | `D("4000.00")` |
| Zona `INTERIOR` | válida | `calcular_envio(D("10000.00"), "INTERIOR")` | `D("6500.00")` |
| Zona `RETIRO` | válida | `calcular_envio(D("10000.00"), "RETIRO")` | `D("0.00")` |
| Zona en minúscula | válida | `calcular_envio(D("10000.00"), "gba")` | `D("4000.00")` |
| Zona con espacios alrededor | válida | `calcular_envio(D("10000.00"), "  interior ")` | `D("6500.00")` |
| Zona que no existe | inválida | `calcular_envio(D("10000.00"), "MARTE")` | Error `ZONA_INVALIDA` |
| Zona vacía | inválida | `calcular_envio(D("10000.00"), "")` | Error `ZONA_INVALIDA` |
| Base justo debajo del envío gratis | válida | `calcular_envio(D("59999.99"), "CABA")` | `D("2500.00")` |
| Base exacta del envío gratis | válida | `calcular_envio(D("60000.00"), "CABA")` | `D("0.00")` |
| Base arriba del envío gratis | válida | `calcular_envio(D("60000.01"), "INTERIOR")` | `D("0.00")` |
| Subtotal ≥ 60.000 pero con descuento queda < 60.000 | válida | `calcular_total([item("buzo", cantidad=2), item("remera")], "CABA", "EGRESADOS2026", date(2026, 10, 1))` | subtotal `61999.30`, descuento `9299.90`, `envio == D("2500.00")` |
| Subtotal ≥ 60.000 sin descuento | válida | `calcular_total([item("buzo", cantidad=2), item("remera")], "CABA")` | `envio == D("0.00")` |

**Valores límite:** `59999.99` (se paga), `60000.00` (gratis) y `60000.01` (gratis). Lo que se compara es el subtotal ya con el descuento aplicado.

---

## R9 — Total

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Sin descuento y con envío (ejemplo de la especificación) | válida | `calcular_total([item("buzo", cantidad=2)], "CABA")` | `{"subtotal": D("49999.80"), "descuento": D("0.00"), "envio": D("2500.00"), "total": D("52499.80")}` |
| Con cupón y con envío | válida | `calcular_total([item("remera")], "CABA", "EGRESADOS2026", date(2026, 11, 30))` | `{"subtotal": D("11999.50"), "descuento": D("1799.93"), "envio": D("2500.00"), "total": D("12699.57")}` |
| Con descuento por cantidad y con envío | válida | `calcular_total([item("remera", cantidad=5)], "CABA")` | `{"subtotal": D("59997.50"), "descuento": D("5999.75"), "envio": D("2500.00"), "total": D("56497.75")}` |
| Con descuento y envío que deja de ser gratis | válida | `calcular_total([item("buzo", cantidad=2), item("remera")], "CABA", "EGRESADOS2026", date(2026, 10, 1))` | `{"subtotal": D("61999.30"), "descuento": D("9299.90"), "envio": D("2500.00"), "total": D("55199.40")}` |
| Sin descuento y con envío gratis | válida | `calcular_total([item("buzo", cantidad=3)], "GBA")` | `{"subtotal": D("74999.70"), "descuento": D("0.00"), "envio": D("0.00"), "total": D("74999.70")}` |
| Retiro en el colegio | válida | `calcular_total([item("remera")], "RETIRO")` | `{"subtotal": D("11999.50"), "descuento": D("0.00"), "envio": D("0.00"), "total": D("11999.50")}` |
| Varios errores: carrito vacío y zona inválida | inválida | `calcular_total([], "MARTE")` | Error `CARRITO_VACIO` |
| Varios errores en un ítem: producto y talle | inválida | `calcular_total([item("zapatilla", talle="XXXL")], "CABA")` | Error `PRODUCTO_INEXISTENTE` |
| Varios errores en un ítem: talle y cantidad | inválida | `calcular_total([item(talle="XXXL", cantidad=0)], "CABA")` | Error `TALLE_INVALIDO` |
| Errores en dos ítems | inválida | `calcular_total([item(cantidad=0), item("zapatilla")], "CABA")` | Error `CANTIDAD_INVALIDA` (se informa el del primer ítem) |
| Ítem inválido y cupón inválido | inválida | `calcular_total([item(talle="XXXL")], "CABA", "NOEXISTE")` | Error `TALLE_INVALIDO` |
| Cupón inválido y zona inválida | inválida | `calcular_total([item()], "MARTE", "NOEXISTE")` | Error `CUPON_INVALIDO` |
| Solo zona inválida | inválida | `calcular_total([item()], "MARTE")` | Error `ZONA_INVALIDA` |

**Valores límite:** un total con descuento `0.00` y uno con envío `0.00`. Con varios errores, el orden de la sección 3: carrito, ítems (producto, talle, cantidad), cupón y zona.

---

## R10 — Persistencia (`pedidos.py`)

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Pedido válido | válida | `guardar_pedido(con, "ana@mail.com", [item("remera")], "CABA", "EGRESADOS2026", date(2026, 11, 30))` | devuelve un `int` (el id) |
| Montos idénticos a `checkout` | válida | `obtener_pedido(con, id)` del pedido anterior | `subtotal == D("11999.50")`, `descuento == D("1799.93")`, `envio == D("2500.00")`, `total == D("12699.57")`, todos `Decimal` |
| Pedido con error de `checkout` | inválida | `guardar_pedido(con, "ana@mail.com", [item(talle="XXXL")], "CABA")` | Error `TALLE_INVALIDO`, y las tablas `pedidos` e `items` quedan con 0 filas |
| Error en el último ítem | inválida | `guardar_pedido(con, "ana@mail.com", [item(), item("zapatilla")], "CABA")` | Error `PRODUCTO_INEXISTENTE`, y 0 pedidos y 0 ítems guardados |
| Error de zona | inválida | `guardar_pedido(con, "ana@mail.com", [item()], "MARTE")` | Error `ZONA_INVALIDA`, y 0 pedidos guardados |
| El pedido es definitivo | válida | guardar un pedido de 2 ítems y leerlo con **otra conexión** a la misma base | la otra conexión ve el pedido con sus montos y sus 2 ítems |
| Precio de catálogo | válida | `guardar_pedido(con, "ana@mail.com", [item("buzo", precio=1)], "CABA")` y `obtener_pedido` | `precio_unitario == D("24999.90")` y `subtotal == D("24999.90")` |
| Email normalizado | válida | `guardar_pedido(con, "  Ana@Mail.COM ", [item()], "CABA")` | `email == "ana@mail.com"` |
| Zona normalizada | válida | `guardar_pedido(con, "ana@mail.com", [item()], " caba ")` | `zona == "CABA"` |
| Talle normalizado | válida | `guardar_pedido(con, "ana@mail.com", [item(talle=" m ")], "CABA")` | `items[0]["talle"] == "M"` |
| Cupón normalizado | válida | `guardar_pedido(con, "ana@mail.com", [item()], "CABA", " egresados2026 ", date(2026, 10, 1))` | `cupon == "EGRESADOS2026"` |
| Cupón vacío | válida | `guardar_pedido(con, "ana@mail.com", [item()], "CABA", "")` | `cupon is None` |
| Sin cupón | válida | `guardar_pedido(con, "ana@mail.com", [item()], "CABA")` | `cupon is None` |
| Id que no existe | inválida | `obtener_pedido(con, 999)` | `None` |
| Pedidos de un email | válida | dos pedidos de `ana@mail.com` y uno de `beto@mail.com`, después `pedidos_de(con, "ana@mail.com")` | 2 pedidos, del más reciente al más antiguo |
| Email con mayúsculas y espacios en la búsqueda | válida | `pedidos_de(con, "  ANA@mail.com ")` | los mismos 2 pedidos de Ana |
| Email sin pedidos | válida | `pedidos_de(con, "nadie@mail.com")` | `[]` |
| Email que intenta alterar la consulta | inválida | `pedidos_de(con, "x' OR '1'='1")` | `[]`, no devuelve pedidos de otros |
| Email con comilla | válida | guardar un pedido de `o'brien@mail.com` y `pedidos_de(con, "o'brien@mail.com")` | 1 pedido, sin error |

**Valores límite:**

- Carrito con un error en el primer ítem y con un error en el último: en los dos casos no queda nada guardado.
- Base sin pedidos y con un solo pedido.
- `pedidos_de` con 0, 1 y 2 pedidos.
- Cupón `None`, `""` y con espacios.

---

## R11 — API HTTP (`api.py`)

| Partición | Tipo | Caso (entrada) | Resultado esperado |
| --- | --- | --- | --- |
| Crear pedido sin cupón ni fecha | válida | `POST /api/v1/pedidos` con `{"email": "ana@mail.com", "zona": "CABA", "carrito": [buzo M 1]}` | `201`, con `id` y los montos `"24999.90"`, `"0.00"`, `"2500.00"`, `"27499.90"` como texto |
| Crear pedido con cupón y fecha | válida | `POST` con remera M 1, `"cupon": "EGRESADOS2026"`, `"fecha": "2026-11-30"` | `201`, `{"id": ..., "subtotal": "11999.50", "descuento": "1799.93", "envio": "2500.00", "total": "12699.57"}` |
| Leer un pedido existente | válida | `POST` del caso anterior y después `GET /api/v1/pedidos/{id}` | `200` con el pedido completo de la sección 6: los montos y el `precio_unitario` como texto, iguales a los que devolvió el `POST` |
| Error de negocio | inválida | `POST` con talle `"XXXL"` | `422`, `{"error": {"code": "TALLE_INVALIDO", "message": ...}}` |
| Error de negocio por fecha | inválida | `POST` con `"cupon": "EGRESADOS2026"` y `"fecha": "2026-12-01"` | `422`, code `CUPON_VENCIDO` |
| Cuerpo que no es JSON | inválida | `POST` con el cuerpo `{esto no es json` | `400`, code `JSON_INVALIDO` |
| Cuerpo vacío | inválida | `POST` sin cuerpo | `400`, code `JSON_INVALIDO` |
| Falta un campo | inválida | `POST` sin `email` | `400`, code `DATOS_INCOMPLETOS` |
| Campo de otro tipo | inválida | `POST` con `"carrito": "buzo"` | `400`, code `DATOS_INCOMPLETOS` |
| Campo de otro tipo | inválida | `POST` con `"email": 123` | `400`, code `DATOS_INCOMPLETOS` |
| JSON que no es un objeto | inválida | `POST` con el cuerpo `[]` | `400`, code `DATOS_INCOMPLETOS` |
| Fecha en otro formato | inválida | `POST` con `"fecha": "30/11/2026"` | `400`, code `FECHA_INVALIDA` |
| Pedido que no existe | inválida | `GET /api/v1/pedidos/999` | `404`, code `PEDIDO_INEXISTENTE` |
| Ruta que no existe (GET) | inválida | `GET /api/v1/otra` | `404`, code `RUTA_INEXISTENTE` |
| Ruta que no existe (POST) | inválida | `POST /api/v1/otra` | `404`, code `RUTA_INEXISTENTE` |

En todos los casos de error, la respuesta tiene la forma `{"error": {"code": ..., "message": ...}}` y el status nunca es `500`.

**Valores límite:**

- `cupon` y `fecha` presentes y ausentes, porque son opcionales.
- La fecha en el último día del cupón (`2026-11-30`) y en el día siguiente (`2026-12-01`).
- Cuerpo vacío y cuerpo de JSON válido que no es un objeto.
