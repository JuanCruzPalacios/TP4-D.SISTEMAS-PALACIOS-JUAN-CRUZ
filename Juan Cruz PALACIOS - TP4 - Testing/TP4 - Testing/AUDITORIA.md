# Parte 2 — Auditoría

## Sección 1: los tests de la IA

### Clasificación de los ocho tests

| Test | Clasificación | Por qué |
| --- | --- | --- |
| `test_subtotal` | tautológico | Compara contra `CATALOGO["buzo"] * 2`, que es la misma cuenta que hace el código: si el precio del catálogo estuviera mal o fuera `float`, el test igual pasaría. |
| `test_total_funciona` | inútil | `assert resultado is not None` pasa con cualquier diccionario, aunque todos los montos estén mal. |
| `test_total_positivo` | débil | `total > 0` acepta cualquier número positivo; no verifica el valor que pide la especificación. |
| `test_cupon_egresados` | tautológico | Espera `100000 * 0.15`, la misma cuenta en `float` del código; no prueba el redondeo, el último día de vigencia, ni que el cupón no se acumule. |
| `test_envio_caba` | útil | Verifica un valor concreto de la especificación ($ 2.500 para CABA), aunque solo prueba el camino feliz y ningún límite. |
| `test_descuento_por_cantidad` | débil | Usa 6 prendas en lugar del límite de 5, así que no detecta que el código usa `>` en lugar de `>=`. |
| `test_talle_valido` | inútil | No tiene assert: solo comprueba que no explote con un talle que ya está en mayúscula y sin espacios. |
| `test_no_explota_con_varios_productos` | inútil | El `try/except Exception: pass` hace que el test pase siempre, falle lo que falle. |

### Puntaje de mutación

```
python mutar.py --tests test_checkout_ia.py

Mutantes generados : 29
Muertos            : 17
Sobrevivientes     : 12
Puntaje de mutación: 58.6%
```

Mutantes que sobrevivieron:

```
línea  40  '<' → '<='     if not (1 <= item["cantidad"] < 10):
línea  40  10 → 11        if not (1 <= item["cantidad"] < 10):
línea  60  '>' → '>='     if cantidad_prendas > 5:
línea  72  '<' → '<='     if not fecha < datos["vence"]:
línea  76  '==' → '!='    elif datos["tipo"] == "fijo":
línea  77  '<' → '<='     if subtotal < datos["minimo"]:
línea  82  '+' → '-'      descuento += datos["valor"]
línea  96  '>=' → '>'     if subtotal >= 60000:
línea  96  60000 → 60001  if subtotal >= 60000:
línea 107  '+' → '-'      prendas = prendas + item["cantidad"]
línea 111  '+' → '-'      total = subtotal - descuento + envio
línea 111  '-' → '+'      total = subtotal - descuento + envio
```

Tres de los mutantes que sobreviven (línea 40 `<` → `<=`, línea 60 `>` → `>=` y línea 72 `<` → `<=`) son justamente la corrección de una falla real. La suite no distingue el código con el error del código arreglado.

### Por qué casi el 80% de cobertura no detecta ninguna falla

La suite cubre el 77% de las líneas (73% contando ramas), pero la cobertura solo mide qué líneas se ejecutaron, no si alguien verificó el resultado. Tres de los ocho tests no tienen un assert que pueda fallar (`is not None`, sin assert y `except: pass`), y otros dos comparan contra la misma cuenta que hace el código, así que si la cuenta está mal el test también lo está. Además, todos los tests usan datos del camino feliz, lejos de los bordes: 6 prendas en lugar de 5, ninguna cantidad de 10, ninguna fecha el 30/11, ningún subtotal cerca de $ 60.000, ningún talle en minúscula ni con espacios, ninguna zona inválida. Las fallas viven justo en esos bordes, por eso las líneas se ejecutan y ninguna falla se ve. Las ramas que no se cubren (producto inexistente, cupón vencido, `BIENVENIDA`, zona inválida) son justo las que tienen errores.

---

## Sección 2: hallazgos

### Resultado del linter

```
ruff check checkout.py

F401  `json` imported but unused                                   --> checkout.py:1
E722  Do not use bare `except`                                      --> checkout.py:50
B008  Do not perform function call `date.today` in argument defaults --> checkout.py:57
E711  Comparison to `None` should be `cond is not None`              --> checkout.py:63
B008  Do not perform function call `date.today` in argument defaults --> checkout.py:102
Found 5 errors.
```

El linter encontró por sí solo 4 de las fallas (H-01, H-11, H-12 y H-13). Todas las demás se encontraron leyendo el código contra la especificación y probándolo.

### `checkout.py`

**H-01 · Import sin usar**
- Archivo y línea: `checkout.py`, línea 1
- Categoría: code smell
- Regla: ninguna (no rompe nada, pero ensucia el módulo)
- Cómo la encontré: `ruff` (F401)
- Severidad: baja

**H-02 · Los precios del catálogo son `float`**
- Archivo y línea: `checkout.py`, líneas 12 a 16 (y 26 a 31 para los envíos)
- Categoría: numéricos
- Regla: R7 (todos los importes son `Decimal`, nunca `float`)
- Cómo la encontré: lectura del código. `calcular_subtotal` de 5 remeras devuelve `59997.5` (un `float`) en lugar de `Decimal("59997.50")`.
- Severidad: alta

**H-03 · Existe un cupón `DEBUG100` del 100%**
- Archivo y línea: `checkout.py`, línea 23
- Categoría: seguridad
- Regla: R6 (`EGRESADOS2026` y `BIENVENIDA` son los únicos dos cupones)
- Cómo la encontré: lectura del código. `calcular_total` de un buzo con `DEBUG100` da un descuento de 24.999,90 y el comprador paga solo el envío.
- Severidad: alta

**H-04 · `validar_item` modifica el ítem que recibe**
- Archivo y línea: `checkout.py`, línea 35
- Categoría: efectos laterales
- Regla: R4 (ninguna función modifica el carrito que recibe)
- Cómo la encontré: lectura del código. Después de `validar_item({"talle": "m", ...})` el ítem queda con `"talle": "M"`.
- Severidad: media

**H-05 · El talle no ignora los espacios**
- Archivo y línea: `checkout.py`, línea 35
- Categoría: strings
- Regla: R2 (`"  M "` es válido)
- Cómo la encontré: caso de `CASOS.md`. Con `" M"` se lanza `TALLE_INVALIDO`.
- Severidad: media

**H-06 · Datos de otro tipo o faltantes en el ítem lanzan otra excepción**
- Archivo y línea: `checkout.py`, líneas 35 y 40
- Categoría: tipos
- Regla: R2, R3 y sección 1 (ante datos inválidos se lanza `CheckoutError`, nunca otra excepción)
- Cómo la encontré: lectura del código. Un talle `None` lanza `AttributeError`, una cantidad `"2"` lanza `TypeError` y un ítem sin talle lanza `KeyError`.
- Severidad: media

**H-07 · La cantidad 10 se rechaza**
- Archivo y línea: `checkout.py`, línea 40
- Categoría: lógica y límites
- Regla: R3 (entre 1 y 10, ambos inclusive)
- Cómo la encontré: valor límite de `CASOS.md`. El código usa `< 10`, así que 10 da `CANTIDAD_INVALIDA`.
- Severidad: media

**H-08 · Se aceptan cantidades no enteras**
- Archivo y línea: `checkout.py`, línea 40
- Categoría: tipos
- Regla: R3 (los no enteros dan `CANTIDAD_INVALIDA`)
- Cómo la encontré: caso de `CASOS.md`. Con `2.5`, como `1 <= 2.5 < 10`, el ítem se acepta y se cobran 2,5 prendas.
- Severidad: media

**H-09 · Un producto inexistente se saltea en silencio**
- Archivo y línea: `checkout.py`, líneas 34 a 41 y 48 a 51
- Categoría: manejo de errores
- Regla: R1 (producto fuera del catálogo da `PRODUCTO_INEXISTENTE`) y sección 3 (el producto se valida antes que el talle)
- Cómo la encontré: lectura del código, a partir del `except:` que marcó el linter. `validar_item` nunca revisa el producto, y el `except: continue` saltea el ítem. Con `[zapatilla]` el total es solo el envío y nunca se lanza `PRODUCTO_INEXISTENTE`.
- Severidad: alta

**H-10 · Se usa el precio que manda el cliente**
- Archivo y línea: `checkout.py`, línea 49
- Categoría: seguridad
- Regla: R1 (el precio sale siempre del catálogo)
- Cómo la encontré: lectura del código. `calcular_subtotal([{"producto": "buzo", ..., "precio": 1}])` devuelve `1`.
- Severidad: alta

**H-11 · `except:` vacío**
- Archivo y línea: `checkout.py`, línea 50
- Categoría: code smell
- Regla: sección 1 (los errores se informan con `CheckoutError`)
- Cómo la encontré: `ruff` (E722). Atrapa cualquier error, incluso los que no tienen nada que ver con el catálogo, y es la causa de H-09.
- Severidad: baja

**H-12 · La fecha por defecto se calcula una sola vez**
- Archivo y línea: `checkout.py`, líneas 57 y 102
- Categoría: fechas
- Regla: R6 (sin `fecha`, se usa la fecha del día de la llamada)
- Cómo la encontré: `ruff` (B008). `fecha=date.today()` se evalúa cuando se importa el módulo. Si la API arranca el 30/11 y sigue corriendo, el cupón `EGRESADOS2026` se sigue aceptando los días siguientes.
- Severidad: alta

**H-13 · Comparación con `None` usando `!=`**
- Archivo y línea: `checkout.py`, línea 63
- Categoría: code smell
- Regla: ninguna por sí sola (ver H-15)
- Cómo la encontré: `ruff` (E711)
- Severidad: baja

**H-14 · El descuento por cantidad empieza en 6 prendas**
- Archivo y línea: `checkout.py`, línea 60
- Categoría: lógica y límites
- Regla: R5 (5 o más prendas)
- Cómo la encontré: valor límite de `CASOS.md`. Con 5 prendas el descuento es 0.
- Severidad: media

**H-15 · Un cupón vacío o de solo espacios da error**
- Archivo y línea: `checkout.py`, líneas 63 a 67
- Categoría: strings
- Regla: R6 (`""` o solo espacios equivalen a no usar cupón)
- Cómo la encontré: caso de `CASOS.md`. Con `""` se lanza `CUPON_INVALIDO`.
- Severidad: media

**H-16 · El cupón distingue mayúsculas**
- Archivo y línea: `checkout.py`, línea 64
- Categoría: strings
- Regla: R6 (no se distingue mayúscula de minúscula)
- Cómo la encontré: caso de `CASOS.md`. `"egresados2026"` da `CUPON_INVALIDO`.
- Severidad: media

**H-17 · Un cupón o una zona que no son texto lanzan otra excepción**
- Archivo y línea: `checkout.py`, líneas 64 y 88
- Categoría: tipos
- Regla: sección 1 (nunca otro tipo de excepción)
- Cómo la encontré: lectura del código. Un cupón `123` o una zona `None` lanzan `AttributeError`.
- Severidad: baja

**H-18 · `EGRESADOS2026` vence un día antes**
- Archivo y línea: `checkout.py`, línea 72
- Categoría: fechas
- Regla: R6 (válido hasta el 30/11/2026 inclusive)
- Cómo la encontré: valor límite de `CASOS.md`. `not fecha < vence` lanza `CUPON_VENCIDO` el mismo 30/11.
- Severidad: media

**H-19 · El cupón se suma al descuento por cantidad**
- Archivo y línea: `checkout.py`, líneas 61, 74 y 82
- Categoría: lógica y límites
- Regla: R6 (no se acumula; se aplica el mayor)
- Cómo la encontré: lectura del código (`descuento +=` en los dos lugares). Con 6 prendas y `EGRESADOS2026` sobre $ 100.000 el descuento es $ 25.000 en lugar de $ 15.000.
- Severidad: alta

**H-20 · El descuento no se limita al subtotal**
- Archivo y línea: `checkout.py`, línea 84
- Categoría: lógica y límites
- Regla: R6 (el descuento nunca puede superar el subtotal)
- Cómo la encontré: lectura del código. No hay ningún tope; con los cupones válidos no llega a pasar, pero junto con H-19 el descuento se acerca al subtotal sin control.
- Severidad: baja

**H-21 · Redondeo con `round()` sobre `float`**
- Archivo y línea: `checkout.py`, líneas 54, 84 y 117
- Categoría: numéricos
- Regla: R7 (redondeo comercial, el medio centavo sube)
- Cómo la encontré: ejemplo de la especificación. `round(11999.5 * 0.15, 2)` da `1799.92` en lugar de `1799.93`.
- Severidad: alta

**H-22 · Método que no existe en el mensaje de zona inválida**
- Archivo y línea: `checkout.py`, línea 93
- Categoría: alucinación
- Regla: R8 y sección 4 (zona inexistente da `ZONA_INVALIDA`)
- Cómo la encontré: caso de `CASOS.md`. `ENVIOS.keys().join(", ")` no existe (los `dict_keys` no tienen `join`), así que cualquier zona inválida lanza `AttributeError` en lugar de `CheckoutError`.
- Severidad: alta

**H-23 · El envío gratis se calcula sobre el subtotal sin descuento**
- Archivo y línea: `checkout.py`, línea 110
- Categoría: lógica y límites
- Regla: R8 (gratis si el subtotal **ya con el descuento** es de $ 60.000 o más)
- Cómo la encontré: caso de `CASOS.md`. Dos buzos y una remera con `EGRESADOS2026` (subtotal 61.999,30, con descuento 52.699,40) dan envío 0 en lugar de 2.500.
- Severidad: alta

**H-24 · No se valida el carrito vacío**
- Archivo y línea: `checkout.py`, líneas 102 a 118
- Categoría: manejo de errores
- Regla: R4 (carrito sin ítems da `CARRITO_VACIO`)
- Cómo la encontré: caso de `CASOS.md`. `calcular_total([], "CABA")` devuelve un pedido con total 2.500.
- Severidad: media

### `pedidos.py`

**H-25 · El pedido se guarda antes de calcular el total**
- Archivo y línea: `pedidos.py`, líneas 39 a 50
- Categoría: efectos laterales
- Regla: R10 (si `calcular_total` lanza `CheckoutError` no queda nada guardado)
- Cómo la encontré: lectura del código. Se hace el `INSERT` y el `commit` antes de llamar a `calcular_total`; si hay un error, queda un pedido con todos los montos en 0.
- Severidad: alta

**H-26 · Los montos y los ítems nunca se confirman**
- Archivo y línea: `pedidos.py`, líneas 52 a 71
- Categoría: efectos laterales
- Regla: R10 (cuando `guardar_pedido` termina, otra conexión ve el pedido completo)
- Cómo la encontré: lectura del código. Después del `UPDATE` y de los `INSERT` de ítems no hay `commit`. Otra conexión ve el pedido con montos en 0 y sin ítems, y si la conexión se cierra se pierden.
- Severidad: alta

**H-27 · Los montos se guardan como `REAL` y se pierden decimales**
- Archivo y línea: `pedidos.py`, líneas 12 a 15, 23, 55 a 58, 68 y 88 a 97
- Categoría: numéricos
- Regla: R10 (los montos de `obtener_pedido` son idénticos a los de `checkout`, sin pérdida)
- Cómo la encontré: lectura del código. Se convierte a `float` para guardar y después `Decimal(float)`: `Decimal(1799.93)` es `1799.930000000000063664...`, distinto de `Decimal("1799.93")`.
- Severidad: alta

**H-28 · `precio_unitario` usa el precio del cliente**
- Archivo y línea: `pedidos.py`, línea 64
- Categoría: seguridad
- Regla: R10 (`precio_unitario` es el del catálogo, nunca uno enviado por el cliente)
- Cómo la encontré: lectura del código (`item.get("precio", ...)`).
- Severidad: alta

**H-29 · Inyección SQL en `pedidos_de`**
- Archivo y línea: `pedidos.py`, línea 107
- Categoría: seguridad
- Regla: R10 (ningún valor del email puede alterar la consulta)
- Cómo la encontré: lectura del código: es la única consulta armada con un f-string. `pedidos_de(con, "x' OR '1'='1")` devuelve los pedidos de todos los usuarios, y un email con comilla como `o'brien@mail.com` hace fallar la consulta.
- Severidad: alta

### `api.py`

**H-30 · Los montos viajan como número JSON**
- Archivo y línea: `api.py`, línea 18
- Categoría: numéricos
- Regla: R11 (los montos viajan siempre como texto)
- Cómo la encontré: lectura del código. `json.dumps(..., default=float)` convierte los `Decimal` a número, en el `POST` y en el `GET` (incluido `precio_unitario`).
- Severidad: alta

**H-31 · Los errores de negocio devuelven 500**
- Archivo y línea: `api.py`, líneas 53 a 54 y 67 a 68
- Categoría: manejo de errores
- Regla: R11 (un `CheckoutError` da 422 con su `code`; un error nunca devuelve 500; formato `{"error": {"code", "message"}}`)
- Cómo la encontré: lectura del código. El `except Exception` responde siempre 500 con `{"error": "texto"}`, sin `code` y mostrando el mensaje interno de la excepción.
- Severidad: alta

**H-32 · La fecha llega como texto a `checkout`**
- Archivo y línea: `api.py`, línea 41
- Categoría: tipos
- Regla: R11 (la fecha viaja como `AAAA-MM-DD`; formato inválido da 400 `FECHA_INVALIDA`)
- Cómo la encontré: lectura del código. La API pasa `"2026-11-30"` sin convertirlo a `date`, y `checkout` lo compara con una fecha: `TypeError` y 500. Una fecha con otro formato tampoco da `FECHA_INVALIDA`.
- Severidad: alta

**H-33 · JSON inválido o cuerpo vacío devuelven 500**
- Archivo y línea: `api.py`, líneas 31 a 32
- Categoría: manejo de errores
- Regla: R11 (cuerpo que no es JSON válido da 400 `JSON_INVALIDO`)
- Cómo la encontré: lectura del código (`json.loads` dentro del `except Exception` general).
- Severidad: media

**H-34 · No se validan los campos obligatorios**
- Archivo y línea: `api.py`, líneas 35 a 41
- Categoría: tipos
- Regla: R11 (falta email, zona o carrito, o tienen otro tipo: 400 `DATOS_INCOMPLETOS`)
- Cómo la encontré: lectura del código. Un campo faltante da `KeyError`, un tipo incorrecto da `AttributeError` o `TypeError`, y todo termina en 500.
- Severidad: media

**H-35 · Un pedido inexistente devuelve 200**
- Archivo y línea: `api.py`, líneas 64 a 66
- Categoría: manejo de errores
- Regla: R11 (pedido que no existe da 404 `PEDIDO_INEXISTENTE`)
- Cómo la encontré: lectura del código. `obtener_pedido` devuelve `None` y la API responde `200` con `null`.
- Severidad: media

**H-36 · La conexión no se cierra si hay un error**
- Archivo y línea: `api.py`, líneas 34 a 44 y 63 a 65
- Categoría: code smell
- Regla: ninguna
- Cómo la encontré: lectura del código. Si algo falla antes de `con.close()`, la conexión queda abierta.
- Severidad: baja

### Tabla de todas las fallas, de la más grave a la menos grave

| # | Archivo | Línea | Categoría | Regla | Severidad |
| --- | --- | --- | --- | --- | --- |
| H-03 | `checkout.py` | 23 | seguridad | R6 | alta |
| H-10 | `checkout.py` | 49 | seguridad | R1 | alta |
| H-28 | `pedidos.py` | 64 | seguridad | R10 | alta |
| H-29 | `pedidos.py` | 107 | seguridad | R10 | alta |
| H-25 | `pedidos.py` | 39-50 | efectos laterales | R10 | alta |
| H-26 | `pedidos.py` | 52-71 | efectos laterales | R10 | alta |
| H-27 | `pedidos.py` | 12-15, 55-58, 88-97 | numéricos | R10 | alta |
| H-02 | `checkout.py` | 12-16 | numéricos | R7 | alta |
| H-21 | `checkout.py` | 54, 84, 117 | numéricos | R7 | alta |
| H-19 | `checkout.py` | 61, 74, 82 | lógica y límites | R6 | alta |
| H-23 | `checkout.py` | 110 | lógica y límites | R8 | alta |
| H-09 | `checkout.py` | 34-51 | manejo de errores | R1 | alta |
| H-12 | `checkout.py` | 57, 102 | fechas | R6 | alta |
| H-22 | `checkout.py` | 93 | alucinación | R8 | alta |
| H-30 | `api.py` | 18 | numéricos | R11 | alta |
| H-31 | `api.py` | 53-54, 67-68 | manejo de errores | R11 | alta |
| H-32 | `api.py` | 41 | tipos | R11 | alta |
| H-07 | `checkout.py` | 40 | lógica y límites | R3 | media |
| H-14 | `checkout.py` | 60 | lógica y límites | R5 | media |
| H-18 | `checkout.py` | 72 | fechas | R6 | media |
| H-04 | `checkout.py` | 35 | efectos laterales | R4 | media |
| H-24 | `checkout.py` | 102-118 | manejo de errores | R4 | media |
| H-05 | `checkout.py` | 35 | strings | R2 | media |
| H-15 | `checkout.py` | 63-67 | strings | R6 | media |
| H-16 | `checkout.py` | 64 | strings | R6 | media |
| H-06 | `checkout.py` | 35, 40 | tipos | R2, R3 | media |
| H-08 | `checkout.py` | 40 | tipos | R3 | media |
| H-33 | `api.py` | 31-32 | manejo de errores | R11 | media |
| H-34 | `api.py` | 35-41 | tipos | R11 | media |
| H-35 | `api.py` | 64-66 | manejo de errores | R11 | media |
| H-20 | `checkout.py` | 84 | lógica y límites | R6 | baja |
| H-17 | `checkout.py` | 64, 88 | tipos | sección 1 | baja |
| H-11 | `checkout.py` | 50 | code smell | sección 1 | baja |
| H-13 | `checkout.py` | 63 | code smell | — | baja |
| H-36 | `api.py` | 34-44, 63-65 | code smell | — | baja |
| H-01 | `checkout.py` | 1 | code smell | — | baja |
