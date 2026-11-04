# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Decodificacion de los valores de DPI del sensor 3311.

**Reimplementacion propia del comportamiento** de `convertBytesToDpi3311()` y
`findDpi3311Index()`, deducido de lo que la pagina oficial muestra para unos
bytes dados. No es una copia del codigo del fabricante: lo que se reprodujo es
la correspondencia byte -> dpi, que es un hecho del formato del dispositivo y
lo unico que hace falta para interpretar lo que el mouse contesta.

El X8 Pro usa el sensor 3311 (lo dice `getSensorType()` del bundle).

En esta tabla el DPI no es una formula lineal sobre el byte, sino un indice en
una tabla dispersa de 220 entradas.

**Esta tabla es la que la pagina usa para LEER el X8 Pro.** Esta hardcodeado en
el bundle: `getSensorType()` mapea `X8Pro: "3311"` y `parseDpiSettings()` llama
a `convertBytesToDpi3311()`. Comprobado contra la pantalla: con
los bytes `1f 2f 3f 6f 9f 8f` la pagina muestra 1350, 2000, 2700, 4750, 6800 y
24400, que es exactamente lo que da esta tabla.

**Pero para ESCRIBIR usa `Pu()`, que es lineal** (descripta mas abajo). Las
dos cosas a la vez: la aplicacion del fabricante lee con una formula y escribe
con la otra, y por eso al conectarse "convierte" los bytes del mouse sin que
nadie toque nada. Se lo vio en vivo: la pagina leyo 1350 y reescribio `Pu(1350)`
= `0x1a`.

**Cual de las dos corresponde al dpi que hace el sensor no se sabe.** A favor
de la lineal: el X8 Pro se vende como 40000 dpi y solo `Pu()` da 40000 en el
nivel 6 de fabrica; `M()` del chunk del X8 Pro pone `dpi6 = 4e4` al restaurar;
y al subir de a 50 dpi desde la UI los bytes se mueven de a uno. A favor de la
tabla: es lo que la pagina muestra. No hay forma de decidirlo sin medir el
desplazamiento real del sensor. Ver dev/models/attackshark-x8pro/docs/bitacora.md.

Historia, porque el proyecto ya se equivoco en las dos direcciones: primero se
uso la tabla, despues el commit "El X8 Pro lee el dpi con Pu()" la descarto
creyendo que la pagina mostraba los valores lineales -no los muestra-, y hoy se
sabe que las dos conviven, cada una de un lado del camino.
"""

from __future__ import annotations

# findDpi3311Index(): el valor del byte se busca aca y lo que importa es su
# POSICION, no el valor.
TABLA_3311 = (
    1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 21, 22,
    23, 24, 25, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 41, 42,
    43, 44, 45, 47, 48, 49, 50, 51, 52, 54, 55, 56, 57, 58, 59, 61, 62,
    63, 64, 65, 67, 68, 69, 70, 71, 72, 74, 75, 76, 77, 78, 79, 81, 82,
    83, 84, 85, 87, 88, 89, 90, 91, 92, 94, 95, 96, 97, 98, 99, 101,
    102, 103, 104, 105, 107, 108, 109, 110, 111, 112, 114, 115, 116,
    117, 118, 119, 121, 122, 123, 124, 125, 127, 128, 129, 130, 131,
    132, 134, 135, 136, 137, 138, 139, 141, 142, 143, 144, 145, 147,
    148, 149, 150, 151, 152, 154, 155, 156, 157, 158, 159, 161, 162,
    163, 164, 165, 167, 168, 169, 170, 171, 172, 174, 175, 176, 177,
    178, 179, 181, 182, 183, 184, 185, 187, 188, 189, 190, 191, 192,
    194, 195, 196, 197, 198, 199, 201, 202, 203, 204, 205, 207, 208,
    209, 210, 211, 212, 214, 215, 216, 217, 218, 219, 221, 222, 223,
    224, 225, 227, 228, 229, 230, 231, 232, 234, 235, 118, 119, 121,
    122, 123, 124, 125, 127, 128, 129, 130, 131, 132, 134, 135, 136,
    137, 138, 139, 141
)

# Modelos que usan el camino "triple" en vez del "double".
MODELOS_TRIPLE = frozenset({2, 14, 4, 36, 229, 234})

DPI_MAXIMO = 26000


def _indice(byte_x: int) -> int:
    try:
        return TABLA_3311.index(byte_x)
    except ValueError:
        return -1


def decodificar_3311(byte_x: int, byte_y: int, doble: bool = False,
                     triple: bool = False, device_no: int = 8) -> int:
    """Convierte el par de bytes de un nivel de DPI a su valor real."""
    if byte_x == 0 and byte_y == 0:
        return 0

    if byte_y == 0:
        i = _indice(byte_x)
        valor = i * 50 + 50 if i != -1 else 50
    elif byte_y == 1:
        i = _indice(byte_x)
        valor = i * 100 + 100 if i != -1 else 100
    else:
        valor = 10100 + ((byte_y << 8 | byte_x) - 199) * 100

    if triple and device_no in MODELOS_TRIPLE:
        if byte_x == 199:
            return 25000
        if 8000 <= valor <= 8500:
            valor = ((valor - 8000) // 100 * 100) * 3 + 24000
        else:
            valor *= 3
    elif doble:
        if byte_x == 235:
            return 20100
        valor *= 2

    return min(valor, DPI_MAXIMO)


def decodificar_niveles(xs, ys, flag_doble: int = 0, flag_triple: int = 0,
                        device_no: int = 8) -> list[int]:
    """Decodifica los 8 niveles a partir de los arrays del bloque de DPI."""
    return [
        decodificar_3311(xs[i], ys[i],
                         doble=bool(flag_doble & (1 << i)),
                         triple=bool(flag_triple & (1 << i)),
                         device_no=device_no)
        for i in range(8)
    ]


# --- el otro camino: como la web ESCRIBE los dpi ----------------------------
# Todo lo de arriba es el camino de LECTURA. Para escribir, la web no invierte
# la tabla: usa una funcion aparte -`Pu()` en `app.js`, llamada desde `Of()`-
# que es lineal. **Descripcion del comportamiento, no su codigo**: el dpi se
# convierte en un indice y el indice viaja como dos bytes, bajo y alto.
#
#     dpi 0            -> (0, 0)
#     dpi <= 26000     -> indice = parte entera de (dpi - 50) / 50
#     dpi >  26000     -> indice = parte entera de (dpi - 1) / 100
#     bajo = indice & 0xFF ; alto = (indice >> 8) & 0xFF
#
# Las dos ramas dan el mismo par de bytes para valores distintos -de ahi la
# ambiguedad que se explica mas abajo-, y el redondeo hacia abajo es lo que
# hace que la UI oficial se mueva de a 50 dpi.
#
# **Para el X8 Pro esto se usa en los dos sentidos.** La tabla dispersa de
# arriba NO es el camino de este modelo; quedo porque reproduce fielmente el
# comportamiento observado y puede aplicar a otros.
#
# Medido (`dev/models/attackshark-x8pro/docs/capturas-w/web-todo.pcap`, `soft-todo.pcap`):
#
#   * El operador subio niveles de a 50 dpi desde la UI oficial y los bytes se
#     movieron de a uno, o sea exactamente `(dpi - 50) // 50`. La tabla dispersa
#     no puede dar eso: sus saltos son irregulares.
#   * Con el mouse en fabrica (`17 2f 3f 6f 9f 8f`, alto `01` en el nivel 6,
#     `DPI_X_Double_Flag = 0x20`) la pagina oficial muestra en pantalla
#     1200 / 2400 / 3200 / 5600 / 8000 / 40000. Esta formula da esos seis; la
#     tabla da 1000 / 2000 / 2700 / 4750 / 6800, que no es lo que se ve.
#
# El nivel 6 es el que obliga a mirar las dos ramas de `Pu()`. `M()` de
# `chunks/dpiX8Pro-CVtR2JhM.js` (el "restaurar" de la pantalla de dpi) pone
# `dpi6 = 4e4`, y 40000 > 26000, asi que sale por la rama de `/100`:
# `n = (40000-1)//100 = 399`, que son justo los bytes de fabrica `8f` + alto
# `01`. Pero `n = 399` tambien sale de 20000 por la rama de `/50`, o sea que
# **los bytes solos son ambiguos**. Lo que desempata es el bit del nivel en
# `DPI_X_Double_Flag`: puesto = se codifico por `/100`.

DPI_LINEAL_MAXIMO = 26000


def codificar_lineal(dpi: int) -> tuple[int, int]:
    """dpi -> (bajo, alto), como `Pu()` de la web. Es lo que se ESCRIBE."""
    if dpi == 0:
        return 0, 0
    if dpi <= DPI_LINEAL_MAXIMO:
        n = (dpi - 50) // 50
    else:
        n = (dpi - 1) // 100
    return n & 0xFF, (n >> 8) & 0xFF


def decodificar_lineal(bajo: int, alto: int = 0, doble: bool = False) -> int:
    """La inversa de `codificar_lineal()`. Es el camino del X8 Pro.

    `Pu()` tiene dos ramas y los bytes solos no dicen cual se uso: `n = 399`
    sale de 20000 por la rama de `/50` y de 40000 por la de `/100`. `doble` es
    el bit de este nivel en `DPI_X_Double_Flag`, y es lo que desempata.

    El X8 Pro sale de fabrica con el nivel 6 en 40000, o sea con ese bit
    puesto: no es un caso raro, es el default.
    """
    n = (alto << 8) | bajo
    if n == 0:
        return 0
    return (n + 1) * (100 if doble else 50)


def niveles_lineales(xs, ys=None, flag_doble: int = 0) -> list[int]:
    """Los 8 niveles del bloque de dpi.

    `ys` son los bytes altos (el campo que `estructuras.py` llama
    `Dpi_Y_setting`) y `flag_doble` es `DPI_X_Double_Flag`. Sin `ys` los
    niveles que pasan de 12800 salen truncados, que es como venia antes.
    """
    if ys is None:
        ys = b"\0" * len(xs)
    return [
        decodificar_lineal(xs[i], ys[i], doble=bool(flag_doble & (1 << i)))
        for i in range(len(xs))
    ]
