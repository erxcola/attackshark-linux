# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""El estado del mouse con nombres propios, rangos y advertencias.

Es la capa que separa a la interfaz de los bytes **y de los nombres del
fabricante**, que son tres cosas distintas y las tres importan:

  * `SensitivityX` **no es sensibilidad**: es la altura de despegue (LOD) y el
    control de ripple, empaquetados en un byte;
  * `closeTime` **no es la hibernacion**: es el reposo corto, el otro
    temporizador;
  * `LightBrightness` **no es el brillo**: son cuatro bits del tiempo de
    hibernacion mas un `8` de relleno.

Heredar esos nombres seria enseñarle a la interfaz un modelo equivocado del
dispositivo. El proyecto ya tradujo `SensitivityX` a "LOD" y `closeTime` a
"reposo"; esto termina el trabajo y le agrega lo que una interfaz necesita y
hoy no esta en ningun lado: **el rango de cada campo, sus opciones, si se puede
escribir, y la advertencia medida cuando la hay**.

Lo que NO hace: leer el mouse, escribirle, ni decidir si algo se puede
escribir. Recibe un estado ya leido -el de `sesion.leer_estado()`- y devuelve
campos. Las advertencias que trae son **medidas**, no decorativas: cada una
cita el dia en que se midio.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from . import dispositivos as disp
from . import dpi as _dpi
from . import estructuras as est
from . import protocol as p
from .sesion import CLAVE_TASA_BAJADA

log = logging.getLogger("linshark.modelo")


@dataclass(frozen=True)
class ColorDeCampo:
    """El color con el que **el mouse** marca un campo, y lo que se sabe de el.

    No es el valor del campo ni se escribe: es el LED que se prende. Hoy el
    unico de este mouse es el indicador de nivel de dpi -MEDIDO
    mirando el mouse: nivel 2 verde, nivel 5 turquesa, nivel 1 rojo, los tres
    como decia el bloque (`dev/models/attackshark-x8pro/docs/evidencia.md`)-.

    Viene pegado al campo y no como una fila aparte a proposito: el color del
    indicador es **informacion del nivel**, y una fila propia por color sumaba
    ocho renglones que decian lo que la fila del nivel ya podia mostrar.
    """

    #: `#rrggbb`, siempre. Es lo que se pinta.
    hexa: str
    #: "rojo", cuando es uno de los ocho conocidos; vacio cuando no.
    nombre: str = ""
    #: Lo que hay que saber de ese color, si hay algo. Medido, como todas.
    nota: str = ""


@dataclass(frozen=True)
class Campo:
    """Un parametro del mouse, listo para mostrar y para escribir.

    `clave` es el identificador estable -el que usaria una interfaz para
    referirse al campo- y `nombre` es como se dice en castellano. Los dos son
    nuestros: ninguno viene del fabricante.
    """

    clave: str
    nombre: str
    valor: Any
    cmd: int
    unidad: str = ""
    opciones: tuple = ()
    minimo: float | None = None
    maximo: float | None = None
    #: De a cuanto se mueve el campo, cuando no es de a uno. **No es una
    #: preferencia de presentacion**: es lo que el mouse puede guardar. El dpi
    #: va de a 50 porque `Pu()` divide entero, el reposo de a medio minuto
    #: porque el byte son medios minutos, y el tiempo de respuesta de a dos
    #: porque el byte viaja a la mitad. Un control que ofrezca un numero de
    #: los otros le hace pedir a quien mira algo que el codificador va a
    #: rechazar, o que el mouse va a redondear sin avisar.
    paso: float | None = None
    escribible: bool = False
    #: Lo medido sobre el campo, con su fecha y su fuente. **Es el registro del
    #: proyecto, no texto de pantalla**: la ventana muestra `definicion`.
    nota: str = ""
    #: Lo que mostraria el cliente oficial cuando **no coincide** con el valor
    #: real. No es una curiosidad: es la razon por la que existe este proyecto.
    en_el_cliente_oficial: Any = None
    #: El color con el que el mouse marca este campo, cuando le pone alguno.
    #: Ver `ColorDeCampo`. La interfaz dibuja la marca sin preguntar de que
    #: campo se trata, asi que un campo nuevo que traiga color la tiene sin
    #: tocar la ventana.
    color: ColorDeCampo | None = None
    #: Que es y para que sirve, dicho para quien lo va a tocar: es lo que sale
    #: detras del `?` de la ventana. Sin fechas, sin citas y sin lo que hace el
    #: cliente oficial -eso vive en `nota` y en `dev/docs/`-, decidido el
    #: la ayuda de una fila explica el parametro, no la evidencia.
    definicion: str = ""
    #: Lo unico que hay que saber **antes** de tocarlo, cuando hay algo. Va al
    #: lado de la definicion, en el color de las advertencias.
    aviso: str = ""
    #: El numero del boton fisico, para los campos que son un boton. Es el que
    #: el esquema dibuja sobre el mouse, y la ventana lo pone al lado del nombre.
    slot: int | None = None
    #: Como se lee cada opcion en pantalla, cuando no alcanza con la opcion
    #: misma. **Las opciones no cambian**: siguen siendo lo que acepta
    #: `sesion.preparar_mutacion()` y el `--funcion` del CLI ("atras"); esto
    #: es solo lo que se muestra ("Atrás (página anterior)").
    etiquetas: dict | None = None
    #: Como se lee el valor actual cuando **no** es una de las opciones: un
    #: boton en "macro 17" o en "atajo de teclado ctrl+c" lleva su parametro
    #: pegado, y ahi no hay etiqueta que buscar.
    etiqueta_de_valor: str = ""
    #: Las opciones repartidas en grupos, cuando son tantas que una lista
    #: sola no se recorre: `((titulo, (opcion, ...)), ...)`, en el orden en
    #: que se muestran. **Cada opcion esta en un grupo y en uno solo**, y las
    #: opciones siguen siendo `opciones`: esto dice como se presentan, no que
    #: se puede elegir.
    grupos: tuple = ()

    @property
    def difiere_del_cliente_oficial(self) -> bool:
        return (self.en_el_cliente_oficial is not None
                and self.en_el_cliente_oficial != self.valor)


# --- las advertencias, todas medidas ---------------------------------------

NOTA_DPI = ("la pagina oficial muestra otro numero para estos mismos bytes: "
            "escribe con Pu() y lee con la tabla del 3311. Cual de las dos es "
            "el dpi real del sensor no se sabe (I-W11)")
NOTA_COLOR = ("en el X8 Pro estos bytes no encienden nada: se guardan y se "
              "releen, y no mueven nada (MEDIDO). El unico LED "
              "que prende es el de nivel de dpi, y lo pinta cmd 4")

# Que el RGB del cmd 5 no se ofrezca **es una decision por modelo**, y vive
# donde corresponde: `dispositivos.Perfil.campos_ausentes`, con el motivo
# medido al lado. Antes era `LUZ_RGB_VISIBLE`, una constante
# de este archivo, y este archivo es de todos los mouses. `NOTA_COLOR` queda
# porque la afirmacion sigue siendo cierta y se cita donde hace falta.
NOTA_RESPUESTA = ("el byte viaja a la mitad de este numero "
                  "(`KeyResponseTime/2`), y por eso va de a 2. **La "
                  "aplicacion toma el numero que se ve**; `--respuesta` del "
                  "CLI toma el byte, o sea la mitad de esto. Que la unidad "
                  "sean milisegundos esta INFERIDO del nombre del control, no "
                  "medido")
NOTA_SENSOR = ("la pagina oficial lee estos cuatro bytes mal -compara el byte "
               "entero contra 1, con los campos cruzados- asi que su pantalla "
               "no refleja el estado real (I-W24, MEDIDO)")
NOTA_LOD = ("va en milimetros aunque el campo viaje como 0/1. Es el unico "
            "parametro con verificacion a simple vista: se levanta el mouse")
NOTA_NIVEL_ACTIVO = ("se ve: el LED de nivel toma el color de ese nivel, que "
                     "viaja en este mismo bloque (MEDIDO)")
NOTA_RUEDA = ("la pagina oficial escribe los dos slots al reves que el soft, y "
              "con ese orden **el scroll queda invertido** (MEDIDO)")
NOTA_TASA = ("arriba de 1000 Hz el mouse no se puede leer entero, asi que para "
             "configurar cualquier otra cosa hay que bajarla primero")


# --- que es cada parametro, para la ayuda de la ventana ----------------------
#
# **Definiciones, no evidencia.** Lo que sale detras del `?` explica que hace el
# parametro y para que sirve moverlo. Lo medido, con sus fechas, sigue en las
# `NOTA_*` de arriba y en `dev/models/attackshark-x8pro/docs/evidencia.md`.

DEFINICION_TASA = (
    "Cuántas veces por segundo el mouse le informa su movimiento a la "
    "computadora.\n\nMás alta da un puntero más fluido y con menos demora; más "
    "baja gasta menos batería y menos procesador.")
DEFINICION_DPI = (
    "La sensibilidad de este nivel: cuántos puntos avanza el puntero por cada "
    "pulgada que movés el mouse.\n\nMás alta, el puntero recorre más distancia "
    "con menos movimiento. El botón de DPI pasa de un nivel a otro.")
DEFINICION_NIVEL_ACTIVO = (
    "El nivel de DPI que el mouse está usando ahora.\n\nEs el mismo que cambia el "
    "botón de DPI, y el LED del mouse se pone del color de ese nivel.")
DEFINICION_LOD = (
    "A qué altura el sensor deja de seguir el movimiento cuando levantás el "
    "mouse.\n\nMás baja evita que el puntero se corra al levantarlo para "
    "reacomodarlo; más alta sigue leyendo aunque lo separes un poco de la "
    "superficie.")
DEFINICION_RIPPLE = (
    "Suaviza las pequeñas vibraciones que tiene la lectura del sensor, sobre "
    "todo con DPI altos.\n\nDa un puntero más estable a cambio de un poco de "
    "demora.")
DEFINICION_ANGLE_SNAPPING = (
    "Endereza los movimientos casi rectos para que salgan perfectamente "
    "horizontales o verticales.\n\nAyuda a trazar líneas rectas; en juegos suele "
    "preferirse apagada, porque cambia el movimiento real.")
DEFINICION_MOTION_SYNC = (
    "Sincroniza las lecturas del sensor con los envíos a la computadora, para "
    "que cada reporte llegue a intervalos parejos.\n\nEl movimiento resulta más "
    "uniforme, con una demora mínima.")
DEFINICION_REPOSO = (
    "Cuántos minutos sin usar el mouse pasan hasta que entra en el primer modo "
    "de ahorro de batería.")
DEFINICION_HIBERNACION = (
    "Cuántos minutos más, contados desde que entra en reposo corto, pasan "
    "hasta que el mouse se duerme del todo para ahorrar batería.\n\nMás corto "
    "hace durar más la batería.")
DEFINICION_RESPUESTA = (
    "Cuánto espera el mouse para confirmar que un botón se apretó o se soltó.\n\n"
    "Más bajo responde antes, pero puede registrar clics dobles que no "
    "hiciste; más alto evita esos clics fantasma.")
DEFINICION_COLOR = "El color de la iluminación del mouse."
DEFINICION_RUEDA = (
    "Hacia dónde se desplaza la página al girar la rueda.\n\n«Normal» es el "
    "sentido de siempre; «invertido» la mueve al revés.")

#: Por numero de slot y no por nombre, como `NOTAS_POR_SLOT`: son hechos del
#: boton fisico.
DEFINICIONES_POR_SLOT = {
    1: ("El botón principal, con el que se hace clic y se selecciona.\n\nSe puede "
        "reasignar, siempre que otro de los botones 1 a 5 quede con el clic "
        "izquierdo: así nunca te quedás sin un clic para usar la computadora."),
    2: ("El botón secundario, que normalmente abre el menú contextual.\n\nElegí "
        "qué hace al apretarlo."),
    3: "El clic que se hace apretando la rueda.\n\nElegí qué hace al apretarla.",
    4: ("El botón del costado que queda más atrás, donde apoya el pulgar.\n\n"
        "Normalmente vuelve a la página anterior. Elegí qué hace al "
        "apretarlo."),
    5: ("El botón del costado que queda más adelante.\n\nNormalmente avanza a la "
        "página siguiente. Elegí qué hace al apretarlo."),
    6: ("El botón de la base, al lado del sensor, que normalmente pasa al "
        "siguiente nivel de DPI.\n\nElegí qué hace al apretarlo."),
}

#: El boton de modo no lleva definicion sino **esto solo**, que es lo unico que
#: hay que saber antes de reasignarlo (MEDIDO, ver
#: `NOTA_BOTON_MODO`).
AVISO_BOTON_MODO = (
    "Este botón cambia el modo de conexión del mouse, y lo sigue haciendo "
    "aunque le asignes otra función:\n\nal apretarlo va a cambiar de modo y, "
    "además, va a hacer la acción que le pongas.")


def _bloque(estado: dict, cmd: int) -> bytes | None:
    entrada = estado.get("comandos", {}).get(str(cmd))
    if entrada is None:
        return None
    return bytes.fromhex(entrada["datos"])


def _campos_de_rate(datos: bytes, perfil, via=None) -> list[Campo]:
    # **Por cable la tasa es el otro nibble** (MEDIDO en `cable-soft-rate-*`):
    # el alto sigue diciendo la de la radio, que por cable no es la que manda.
    hz = (est.report_rate_por_cable_de(datos) if via == disp.VIA_CABLE
          else est.report_rate_de(datos))
    # **Las tasas dependen del camino.** Por cable el dispositivo es Full Speed
    # con `bInterval` de 1 ms, asi que no da mas de 1000 Hz: ofrecer 8000 ahi
    # seria un control que no puede hacer lo que dice, que es el reproche que
    # este proyecto le hace al cliente oficial. Lo dice el descriptor, no
    # nosotros (`dev/models/attackshark-x8pro/docs/hardware.md`).
    opciones = tuple(sorted(perfil.tasas))
    if via == disp.VIA_CABLE:
        opciones = tuple(hz for hz in opciones
                         if hz <= perfil.tasa_maxima_por_cable)
    return [Campo("tasa", "Tasa de reporte", hz, p.CMD_REPORT_RATE,
                  unidad="Hz", opciones=opciones,
                  escribible=True, nota=NOTA_TASA,
                  definicion=DEFINICION_TASA)]


def _campos_de_dpi(datos: bytes, perfil, via=None) -> list[Campo]:
    campos = est.decodificar(p.CMD_DPI, datos)
    if campos is None:
        return []
    xs, ys = campos["Dpi_X_setting"], campos["Dpi_Y_setting"]
    doble = campos["DPI_X_Double_Flag"]
    lineales = _dpi.niveles_lineales(xs, ys, doble)
    de_la_pagina = _dpi.decodificar_niveles(xs, ys, doble)
    encendidos = campos["dpi_ON_OFF_flag"]
    sensor = est.parametros_de_sensor(datos) or {}

    salida: list[Campo] = []
    #: Los niveles que el mouse **tiene cargados**, no los slots que el bloque
    #: reserva: el X8 Pro trae ocho y usa seis, y los otros dos estan en cero.
    #: Un nivel que no existe no tiene dpi que mostrar ni color de indicador
    #: que ofrecer -su LED no se prende nunca-, asi que no sale ninguno de los
    #: dos. La lista sale del propio bloque leido: si otro mouse trae ocho,
    #: salen ocho.
    existentes = [i for i, valor in enumerate(lineales, start=1) if valor]

    def _color(nivel) -> ColorDeCampo | None:
        """El indicador de ese nivel, listo para pegarle al campo.

        **No sale como campo propio.** Los colores del indicador se leen y no
        se escriben -son constantes en las 53 escrituras capturadas, asi que
        no hay Etapa 2 posible- y una fila por color era una fila
        que solo se podia mirar. Va de marca en la fila del nivel, que es de
        quien es el dato, y lo que se sabe de el viaja en la ayuda.
        """
        if nivel not in existentes:
            return None
        color = est.color_de_nivel(datos, nivel)
        if color is None:
            return None
        hexa, nombre_color = color
        return ColorDeCampo(
            f"#{hexa}", nombre_color or "",
            nota="ningun cliente oficial escribe estos bytes, asi que no hay "
                 "captura de la que partir")

    for i in existentes:
        salida.append(Campo(
            f"dpi_nivel_{i}", f"DPI del nivel {i}", lineales[i - 1], p.CMD_DPI,
            unidad="DPI", minimo=perfil.dpi_minimo, maximo=perfil.dpi_maximo,
            paso=est.DPI_PASO_UI,
            escribible=bool(encendidos & (1 << (i - 1))), nota=NOTA_DPI,
            definicion=DEFINICION_DPI,
            en_el_cliente_oficial=(de_la_pagina[i - 1]
                                   if i - 1 < len(de_la_pagina) else None),
            color=_color(i)))

    activo = campos.get("Current_Dpi_level_flag")
    prendidos = tuple(i for i in range(1, len(lineales) + 1)
                      if encendidos & (1 << (i - 1)))
    salida.append(Campo("nivel_activo", "Nivel de DPI en uso", activo,
                        p.CMD_DPI, opciones=prendidos, escribible=True,
                        nota=NOTA_NIVEL_ACTIVO, color=_color(activo),
                        definicion=DEFINICION_NIVEL_ACTIVO))

    salida.append(Campo("lod", "Altura de despegue (LOD)",
                        est.LOD_MM.get(sensor.get("lod")), p.CMD_DPI,
                        unidad="mm", opciones=tuple(est.LOD_MM.values()),
                        escribible=True, nota=NOTA_LOD,
                        definicion=DEFINICION_LOD))
    for clave, nombre, definicion in (
            ("ripple", "Control de ripple", DEFINICION_RIPPLE),
            ("angle_snapping", "Corrección de ángulo",
             DEFINICION_ANGLE_SNAPPING),
            ("motion_sync", "Sincronización de movimiento",
             DEFINICION_MOTION_SYNC)):
        salida.append(Campo(clave, nombre, sensor.get(clave), p.CMD_DPI,
                            opciones=(False, True), escribible=True,
                            nota=NOTA_SENSOR, definicion=definicion,
                            en_el_cliente_oficial=sensor.get(
                                f"pagina_{clave}")))

    return salida


def _campos_de_luz(datos: bytes, perfil, via=None) -> list[Campo]:
    par = est.parametros_de_luz(datos)
    campos = est.decodificar(p.CMD_LIGHTING, datos)
    if par is None or campos is None:
        return []
    salida = [
        Campo("reposo", "Reposo corto", par["reposoMin"], p.CMD_LIGHTING,
              unidad="min", minimo=est.REPOSO_MIN, maximo=est.REPOSO_MAX,
              paso=est.REPOSO_PASO, escribible=True,
              nota="el primer escalon de ahorro; el latido pasa de 2 a 4 s",
              definicion=DEFINICION_REPOSO),
        Campo("hibernacion", "Hibernación", par["hibernateTime"],
              p.CMD_LIGHTING, unidad="min", minimo=est.HIBERNACION_MIN,
              maximo=est.HIBERNACION_MAX, escribible=True,
              nota="empieza a contar cuando entra el reposo corto: el corte "
                   "cae en reposo + N x 60 s (MEDIDO)",
              definicion=DEFINICION_HIBERNACION),
        # **El valor que se expone es el que ve una persona**, no el byte. El
        # byte viaja a la mitad (`KeyResponseTime/2`), y exponerlo crudo seria
        # heredar la unidad del fabricante -el mismo error que llamarle
        # "brillo" a medio tiempo de hibernacion-. Aca coincide con lo que
        # muestra el cliente oficial, asi que no hay nada que contrastar.
        Campo("respuesta", "Tiempo de respuesta de los botones",
              par["responseTimeUI"], p.CMD_LIGHTING,
              unidad="ms",
              minimo=est.RESPUESTA_UI_MIN, maximo=est.RESPUESTA_UI_MAX,
              paso=est.RESPUESTA_UI_PASO, escribible=True,
              nota=NOTA_RESPUESTA, definicion=DEFINICION_RESPUESTA),
    ]
    # El RGB solo se ofrece donde enciende algo. En el X8 Pro no enciende nada
    # -por eso "color" esta en `campos_ausentes`- y un control que mueve bytes
    # sin cambiar nada es el reproche que este proyecto le hace al cliente
    # oficial. Otro modelo con RGB de verdad no lo tiene en la lista, y el
    # control aparece **sin tocar la ventana**.
    if "color" not in perfil.campos_ausentes:
        rgb = (campos["redColor"], campos["greenColor"], campos["blueColor"])
        salida.append(Campo("color", "Color", "#%02x%02x%02x" % rgb,
                            p.CMD_LIGHTING, escribible=True, nota=NOTA_COLOR,
                            definicion=DEFINICION_COLOR))
    return salida


#: Lo que hay que saber del boton de modo **antes** de ponerle una funcion, y
#: es de lo medido (`dev/models/attackshark-x8pro/docs/evidencia.md`): el cambio de canal no
#: es la funcion del slot, es del firmware, y sigue pasando con cualquier cosa
#: encima. Con "reproducir / pausar" es una molestia; con un macro largo o un
#: atajo destructivo es otra cosa.
NOTA_BOTON_MODO = (
    "este boton cambia el canal de conexion **siempre**, con cualquier funcion "
    "encima: remapearlo no desactiva el cambio de modo. Lo que se le ponga aca "
    "se va a disparar ademas **cada vez que alguien cambie de canal** "
    "(MEDIDO: al apretarlo, el mouse se desconecto del dongle y la "
    "musica se pauso, las dos cosas juntas). Por eso el codigo 60 que trae de "
    "fabrica es, en la practica, \"no mandes nada extra\"")

#: La advertencia que lleva cada slot, cuando lleva alguna. Por numero de slot
#: y no por nombre: son hechos del boton fisico, no de como lo llamamos.
#:
#: **Es una funcion y no un diccionario de modulo**: cual
#: es el slot del boton de modo sale del perfil, y un dict armado al importar
#: se quedaria con el numero del mouse que estuviera activo en ese momento.
NOTA_SLOT_1 = ("se remapea con la baranda del clic izquierdo: tiene que "
               "quedar uno en los botones 1 a 5. **Etapa 3 cumplida**, con "
               "el boton fisico de testigo. "
               "Etapa 2 no hay: ninguna captura muestra al cliente oficial "
               "escribiendo este slot")


def notas_por_slot(perfil=None) -> dict:
    """`slot -> advertencia`, para el mouse que esta enfrente."""
    perfil = perfil or disp.activo()
    salida = {1: NOTA_SLOT_1}
    modo = perfil.botones_por_nombre.get("modo")
    if modo is not None:
        salida[modo] = NOTA_BOTON_MODO
    return salida

#: Como se llama cada boton en pantalla, por numero de slot. Mas largo que la
#: clave a proposito: "costado-atras" es un identificador, y quien mira tiene
#: que poder ubicar el boton sin haber leido el codigo.
NOMBRES_DE_BOTON = {
    1: "Botón izquierdo (principal)",
    2: "Botón derecho (secundario)",
    3: "Botón de la rueda (apretarla)",
    4: "Botón lateral trasero (pulgar)",
    5: "Botón lateral delantero (pulgar)",
    6: "Botón DPI (en la base)",
    7: "Botón de modo (en la base)",
}

#: Como se lee cada funcion de boton en los desplegables, por **codigo**.
#: `estructuras.FUNCIONES_DE_BOTON` es la tabla del protocolo y sus nombres son
#: los que acepta el CLI; esto es lo que ve quien elige. Los nombres salen de
#: las etiquetas del propio fabricante -`sl` y los archivos de idioma del
#: bundle (`es-*.js`, `en-*.js`, `zh-*.js`)- con lo que hace cada una dicho
#: entre parentesis cuando la etiqueta sola no alcanza. Donde el bundle no dice
#: que hace (56, 57, los dos macros de clic izquierdo) se dice lo que dice el
#: bundle y nada mas.
NOMBRES_DE_FUNCION = {
    0: "Función bloqueada",
    1: "Desactivado: el botón no hace nada",
    2: "Clic izquierdo (seleccionar)",
    3: "Clic derecho (menú contextual)",
    4: "Clic de la rueda (clic central)",
    5: "Atrás (página anterior)",
    6: "Adelante (página siguiente)",
    7: "Doble clic con un solo toque",
    8: "Disparo rápido (clic repetido)",
    9: "Girar la rueda hacia arriba",
    10: "Girar la rueda hacia abajo",
    11: "Desplazar hacia la izquierda",
    12: "Desplazar hacia la derecha",
    13: "Pasar al siguiente nivel de DPI",
    14: "Subir el DPI un nivel",
    15: "Bajar el DPI un nivel",
    16: "Puntería rápida (cambia el DPI para apuntar)",
    17: "Atajo de teclado (combinación de teclas)",
    18: "Ejecutar un macro",
    19: "Abrir un programa",
    20: "Tecla Windows / Super",
    21: "Abrir el reproductor multimedia",
    22: "Canción anterior",
    23: "Canción siguiente",
    24: "Reproducir o pausar",
    25: "Detener la reproducción",
    26: "Silenciar el sonido",
    27: "Subir el volumen",
    28: "Bajar el volumen",
    29: "Abrir la calculadora",
    30: "Abrir el correo electrónico",
    31: "Abrir los favoritos del navegador",
    32: "Navegador: página siguiente",
    33: "Navegador: página anterior",
    34: "Navegador: detener la carga",
    35: "Abrir Mi PC (archivos)",
    36: "Navegador: recargar la página",
    37: "Navegador: página de inicio",
    38: "Navegador: buscar en la web",
    39: "Tecla Fn (funciones especiales)",
    40: "Pasar a la siguiente tasa de reporte",
    41: "Pasar al siguiente modo de luces",
    43: "Mostrar el nivel de batería",
    48: "Prender o apagar las luces",
    50: "Activar el macro de clic izquierdo",
    51: "Detener el macro de clic izquierdo",
    52: "Pasar al siguiente perfil",
    53: "Volver al perfil anterior",
    54: "Ir al perfil siguiente",
    55: "Triple clic con un solo toque",
    56: "Fn + 0x09: sube en 1 el valor Y",
    57: "Fn + 0x0a: baja en 1 el valor Y",
    58: "Activar el macro de clic izquierdo",
    # De fabrica en el boton de modo. Remapearlo no le saca el cambio de modo
    # (MEDIDO), asi que en la practica es "nada extra".
    60: "Solo cambiar el modo de conexión",
}


#: Como se reparten las funciones de boton en el selector, por **codigo**.
#: Son mas de cincuenta opciones: en una lista sola, encontrar "subir el
#: volumen" era recorrerla entera. **No es del protocolo ni del fabricante**: el bundle no
#: agrupa nada, esto lo decidimos nosotros para quien elige, juntando lo que
#: hace cosas parecidas. El orden es el de las pestañas, y adentro de cada una
#: el orden es el del codigo, que ya pone juntas las que van juntas (clic
#: izquierdo, derecho, rueda, atras, adelante).
#:
#: Un codigo que no este aca **no se pierde**: cae en `GRUPO_DE_LO_DEMAS`, asi
#: que una funcion que se agregue a `FUNCIONES_DE_BOTON` aparece aunque nadie
#: se acuerde de esta tabla.
GRUPO_DE_LO_DEMAS = "Otras"
GRUPOS_DE_FUNCION = (
    ("Clics", (2, 3, 4, 5, 6, 7, 55, 8)),
    ("Desplazamiento", (9, 10, 11, 12)),
    ("DPI", (13, 14, 15, 16)),
    ("Música y volumen", (21, 22, 23, 24, 25, 26, 27, 28)),
    ("Navegador", (31, 32, 33, 34, 36, 37, 38)),
    ("Abrir programas", (19, 29, 30, 35)),
    ("Teclado y macros", (17, 18, 20, 39, 50, 58, 51)),
    ("El mouse", (40, 41, 43, 48, 52, 53, 54, 60)),
    (GRUPO_DE_LO_DEMAS, (1, 0, 56, 57)),
)


def grupos_de_funciones(opciones) -> tuple:
    """Las opciones de un boton repartidas en `GRUPOS_DE_FUNCION`.

    Recibe los **nombres** del despachador -lo que va en `Campo.opciones`- y
    devuelve `((titulo, (nombre, ...)), ...)` sin grupos vacios: el 6 y el 7
    no ofrecen el clic izquierdo, y un grupo que quedara sin nada seria una
    pestaña vacia. Los nombres repetidos de la tabla (50 y 58) van una vez.
    """
    grupo_de = {c: titulo for titulo, codigos in GRUPOS_DE_FUNCION
                for c in codigos}
    orden = {c: i for _, codigos in GRUPOS_DE_FUNCION
             for i, c in enumerate(codigos)}
    por_grupo: dict[str, list] = {}
    for opcion in opciones:
        codigos = [c for c, n in est.FUNCIONES_DE_BOTON.items() if n == opcion]
        codigo = min(codigos, key=lambda c: (orden.get(c, len(orden)), c),
                     default=None)
        titulo = grupo_de.get(codigo, GRUPO_DE_LO_DEMAS)
        por_grupo.setdefault(titulo, []).append(
            (orden.get(codigo, len(orden)), codigo if codigo is not None else 0,
             opcion))
    titulos = [t for t, _ in GRUPOS_DE_FUNCION]
    return tuple((t, tuple(o for *_, o in sorted(por_grupo[t])))
                 for t in titulos if t in por_grupo)


def etiqueta_de_funcion(nombre: str) -> str:
    """Como se lee una funcion de boton en pantalla, a partir de su nombre."""
    codigo = next((c for c, n in est.FUNCIONES_DE_BOTON.items() if n == nombre),
                  None)
    return NOMBRES_DE_FUNCION.get(codigo, nombre)


def etiqueta_de_slot(b: dict) -> str:
    """El valor de un boton **con su parametro**, como se lee en pantalla."""
    codigo, p1, p2 = b["codigo"], b.get("p1", 0), b.get("p2", 0)
    if codigo not in est.FUNCIONES_DE_BOTON:
        return f"Código {codigo} sin nombre"
    if codigo == est.FUNCION_ATAJO:
        return f"Atajo de teclado: {est.texto_de_atajo(p1, p2)}"
    if codigo == est.FUNCION_MACRO:
        return (f"Ejecutar el macro {p2}" if p2
                else "Ejecutar un macro sin ID (el botón no hace nada)")
    largo = NOMBRES_DE_FUNCION.get(codigo, est.FUNCIONES_DE_BOTON[codigo])
    return f"{largo} (p1={p1}, p2={p2})" if (p1 or p2) else largo


def _campo_de_boton(nombre_fisico: str, slot: int, b: dict) -> Campo:
    # Los nombres repetidos de la tabla (50 y 58) son una sola opcion: el
    # despachador busca por nombre y los dos caen en el primero.
    opciones = sorted(set(est.FUNCIONES_DE_BOTON.values()))
    if slot not in est.SLOTS_PARA_CLIC_IZQUIERDO:
        # El 6 y el 7 estan en la base: ahi el clic izquierdo no se ofrece.
        opciones.remove(est.FUNCIONES_DE_BOTON[est.FUNCION_CLIC_IZQUIERDO])
    valor = b.get("detalle") or b["codigo"]
    return Campo(
        clave_de_boton(nombre_fisico),
        NOMBRES_DE_BOTON.get(slot, f"Botón {nombre_fisico}"),
        # `detalle` y no `nombre`: el atajo de teclado y el macro llevan
        # su parametro adentro del slot -la combinacion de teclas, el id-
        # y un boton que dice "macro" sin decir cual es medio dato.
        valor, p.CMD_BUTTONS, opciones=tuple(opciones),
        etiquetas={o: etiqueta_de_funcion(o) for o in opciones},
        etiqueta_de_valor=(etiqueta_de_slot(b) if valor not in opciones
                           else ""),
        grupos=grupos_de_funciones(opciones),
        escribible=True,
        nota=notas_por_slot().get(slot, ""),
        definicion=DEFINICIONES_POR_SLOT.get(slot, ""),
        aviso=AVISO_BOTON_MODO if slot == est.SLOT_DE_MODO else "",
        slot=slot)


def clave_de_boton(nombre_fisico: str) -> str:
    """La clave del campo de ese boton fisico. Un solo lugar la arma."""
    return f"boton_{nombre_fisico.replace('-', '_')}"


def _campo_de_rueda(botones: list[dict]) -> Campo:
    # `orden_de_rueda()` recibe los botones ya decodificados, no el bloque, y
    # devuelve texto: aca interesa el dato, asi que se miran los dos slots.
    par = tuple(b["codigo"] for b in botones
                if b["indice"] in est.SLOTS_DE_RUEDA)
    return Campo("rueda", "Sentido de giro de la rueda",
                 "derecho" if par == est.RUEDA_CORRECTA else "invertido",
                 p.CMD_BUTTONS, opciones=("derecho", "invertido"),
                 etiquetas={"derecho": "Normal (el sentido de siempre)",
                            "invertido": "Invertido (al revés)"},
                 escribible=True, nota=NOTA_RUEDA,
                 definicion=DEFINICION_RUEDA)


def _campos_de_botones(datos: bytes, perfil, via=None) -> list[Campo]:
    """Los botones **en el orden en que estan en el mouse**, no alfabetico.

    El orden es el fisico, decidido: clic izquierdo, clic
    derecho, sentido del scroll, clic de rueda, atras, adelante, dpi y modo.
    Es casi el orden de slot -que es el que el firmware usa- con el **sentido
    del scroll metido justo antes del clic de rueda**: las dos cosas son la
    rueda, y el sentido se mira primero. Por eso el orden no puede salir del
    numero de slot solo: el sentido no es un slot remapeable, son los dos que
    `SLOTS_DE_RUEDA` nombra y que nadie puede reasignar.

    Alfabetico -que es lo que habia hasta- no es el orden de
    nadie: pone el boton de dpi entre el derecho y el izquierdo.
    """
    botones = est.botones_de(datos)
    if botones is None:
        return []
    salida = []
    por_slot = {b["indice"]: b for b in botones}
    for nombre_fisico, slot in sorted(est.BOTONES_POR_NOMBRE.items(),
                                      key=lambda kv: kv[1]):
        if slot == est.SLOT_DEL_CLIC_DE_RUEDA:
            salida.append(_campo_de_rueda(botones))
        # `botones_de()` numera los slots en `indice`, 1-based y en la
        # numeracion de LECTURA -que no es la de escritura: los slots 4, 5 y 6
        # se remapean-. `BOTONES_POR_NOMBRE` ya esta en la de lectura.
        b = por_slot.get(slot)
        if b is None:
            continue
        salida.append(_campo_de_boton(nombre_fisico, slot, b))
    return salida


LECTORES: dict[int, Callable[..., list[Campo]]] = {
    p.CMD_REPORT_RATE: _campos_de_rate,
    p.CMD_DPI: _campos_de_dpi,
    p.CMD_LIGHTING: _campos_de_luz,
    p.CMD_BUTTONS: _campos_de_botones,
}


# --- el estado de fabrica --------------------------------------------------
#
# **De donde sale cada numero, porque ninguno se invento.**
#
# El dpi sale del cliente oficial: `M()` del chunk `dpiX8Pro-CVtR2JhM.js` -el
# boton "restaurar" de su pantalla de dpi, y el chunk es el del X8 Pro- pone
# `dpi1=1200, dpi2=2400, dpi3=3200, dpi4=5600, dpi5=8e3, dpi6=4e4, dpi7=0,
# dpi8=0`. Es la fuente pedida: los valores que trae el driver oficial.
#
# El resto sale de `dev/models/attackshark-x8pro/respaldos/linea-base-antes-de-escribir.json`, que es este
# mouse leido **antes de que el proyecto le escribiera nada** -`dev/models/attackshark-x8pro/docs/bitacora.md`
# lo llama "de fabrica" al fijar el `0x34` del report rate-. Las dos fuentes se
# confirman entre si en los seis niveles de dpi, byte por byte, y son
# independientes: una es el bundle del fabricante y la otra el hardware.
#
# `test_la_tabla_de_fabrica_sale_del_respaldo` compara esta tabla contra ese
# respaldo campo por campo, asi que no puede quedar diciendo otra cosa que la
# evidencia.
#
# **Tres cosas que esta tabla NO afirma:**
#
#   * que sea el estado de fabrica de todo X8 Pro. Es el de esta unidad, mas el
#     "restaurar" del cliente oficial. Alcanza para un boton que ofrece volver
#     a un punto conocido; no alcanza para escribir "de fabrica" en un doc de
#     protocolo;
#   * nada sobre los campos que no figuran. Los ocho colores de indicador,
#     `dpi_ON_OFF_flag`, `Dpi_indication_type` y `lightMode` son constantes en
#     las 76 escrituras capturadas: no hay Etapa 2 y escribirlos seria inventar
#     bytes. No se tocan;
#   * nada sobre los macros. Un macro es trabajo de quien lo grabo y "por
#     defecto" para una lista de eventos no significa nada medido, asi que
#     ningun boton de esta aplicacion los pisa.
#
# El nivel activo va en 1, que es lo que tenia el mouse virgen. `M()` ademas
# pone `dpiID = 2` en su propio estado, que no coincide; ante dos fuentes que
# no cierran gana **lo que se le leyo al mouse**, y la diferencia queda anotada
# aca en vez de callarse.
DE_FABRICA: dict[str, Any] = {
    # cmd 6 — la tasa. `0x34`, o sea 500 Hz (dev/models/attackshark-x8pro/docs/bitacora.md).
    "tasa": 500,
    # cmd 4 — dpi y sensor.
    "dpi_nivel_1": 1200,
    "dpi_nivel_2": 2400,
    "dpi_nivel_3": 3200,
    "dpi_nivel_4": 5600,
    "dpi_nivel_5": 8000,
    "dpi_nivel_6": 40000,
    "nivel_activo": 1,
    "lod": 1,
    "ripple": True,
    "angle_snapping": False,
    "motion_sync": True,
    # cmd 5 — reposo, hibernacion y respuesta.
    "reposo": 0.5,
    "hibernacion": 10,
    "respuesta": 8,
    # cmd 8 — los botones y el sentido de la rueda. El izquierdo entra desde
    # que se puede remapear: restaurar tiene que devolverlo.
    "boton_izquierdo": "clic izquierdo",
    "boton_costado_adelante": "adelante",
    "boton_costado_atras": "atras",
    "boton_derecho": "clic derecho",
    "boton_dpi": "ciclo de dpi",
    "boton_modo": "tecla de modo",
    "boton_rueda": "clic de rueda",
    "rueda": "derecho",
}

#: La tasa a la que vuelve el boton de valores seguros, **y no es la de
#: fabrica**. De fabrica son 500 Hz; esto pone 1000.
#:
#: 1000 Hz es el techo en el que el mouse todavia se puede **leer entero**
#: (MEDIDO a 2000 y a 8000: los bloques largos no llegan). Un boton que promete
#: dejar el mouse en un lugar seguro no puede dejarlo donde la proxima lectura
#: falla, y el "restaurar valores por defecto" del cliente oficial hace
#: exactamente eso: sube la tasa a 8000 Hz, lo que dejo el
#: respaldo en 3 de 7 y costo la sesion (`dev/models/attackshark-x8pro/docs/bitacora.md`).
TASA_SEGURA = 1000

#: Lo que escribe el boton de valores seguros: el estado de fabrica con la
#: tasa en un lugar desde el que se puede seguir trabajando. Es la unica
#: diferencia, y esta arriba el motivo.
SEGUROS: dict[str, Any] = {**DE_FABRICA, "tasa": TASA_SEGURA}


def como_esta(estado: dict) -> dict[str, Any]:
    """Los valores que se pueden escribir, como los tiene **su dueño**.

    Es lo que `campos_de()` muestra, salvo la tasa prestada. Con el mouse
    leido a 1000 Hz porque la sesion la bajo para poder leerlo entero, el
    bloque de rate dice 1000 y el mouse es de la tasa a la que se devuelve,
    que el estado trae en `sesion.CLAVE_TASA_BAJADA`. Para mostrar vale lo
    leido; para restaurar, la de su dueño: si no, "volver a como estaba"
    tomaba el 1000 prestado por la tasa que el mouse tenia al abrir.
    """
    dueno = estado.get(CLAVE_TASA_BAJADA)
    return {c.clave: (dueno if dueno is not None and c.cmd == p.CMD_REPORT_RATE
                      else c.valor)
            for c in campos_de(estado) if c.escribible}


def pendientes(estado: dict, deseado: dict) -> list[tuple[str, Any, Any]]:
    """Que habria que escribir para llevar `estado` a `deseado`.

    Devuelve `(clave, de, a)` por cada campo **que hoy se puede escribir y que
    esta en otro valor**, en el orden de `campos_de()`. Un campo que el mouse
    no contesto no figura: no se le escribe a ciegas un bloque que no se pudo
    leer, que es el paso 1 de la Etapa 3.

    Es una funcion del modelo y no de la ventana para que el CLI pueda pedir lo
    mismo, y para poder probar **que se escribiria** sin abrir nada.

    **La tasa va ultima, siempre.** Cambiarla en medio de una rafaga la deja en
    un valor distinto del que la sesion de configuracion presto y va a
    devolver, y arriba de 1000 Hz las escrituras que siguen se quedan sin
    poder releer -que es el paso 1 de la Etapa 3-. Se ordena por el **comando**
    y no por el nombre del campo: es informacion del protocolo.

    **Y se compara contra `como_esta()`**, no contra lo leido: con la tasa
    prestada, el mouse "esta" en la de su dueño. Pedirle 1000 ahi no es un
    no-cambio, es quedarse con la prestada, y la sesion lo hace sin escribir
    (`Configuracion._escribir_tasa`).
    """
    hoy = como_esta(estado)
    salida = []
    clic = est.FUNCIONES_DE_BOTON[est.FUNCION_CLIC_IZQUIERDO]
    # **Primero los botones que reciben el clic izquierdo.** Cada escritura
    # pasa por la baranda de `estructuras`, que no deja sacar el ultimo: si
    # el izquierdo y el derecho estan intercambiados, devolver primero el
    # derecho le sacaria el clic al unico que lo tiene y se negaria.
    for campo in sorted(campos_de(estado),
                        key=lambda c: (c.cmd == p.CMD_REPORT_RATE,
                                       deseado.get(c.clave) != clic)):
        if campo.clave not in deseado or not campo.escribible:
            continue
        quiero = deseado[campo.clave]
        if hoy[campo.clave] != quiero:
            salida.append((campo.clave, hoy[campo.clave], quiero))
    return salida


def campos_de(estado: dict, perfil=None, via=None) -> list[Campo]:
    """Todos los campos que el estado permite reconstruir, con nombre propio.

    Un comando que no contesto no aporta campos, y no rompe: la interfaz
    tiene que poder mostrar un mouse leido a medias.

    `perfil` es el del mouse (`dispositivos.Perfil`); por defecto, el activo.
    De el salen los rangos y **que campos se ofrecen**: un control que en este
    chasis no cambiaria nada no sale, y el motivo esta en `campos_ausentes`.

    `via` es por donde esta conectado (`conexiones.VIA_*`), cuando se sabe: hay
    cosas que dependen del camino y no del modelo, como la tasa maxima -por
    cable el descriptor no da mas de 1000 Hz-. **Si no se dice, lo dice el
    estado**: uno leido por cable trae `"via": "cable"`. Sin eso, cada lugar
    que olvidaba pasarla veia por cable la tasa de la radio -8000 Hz- y
    "Volver a como estaba" intentaba escribirla.
    """
    if via is None:
        via = estado.get("via")
    perfil = perfil or disp.activo()
    salida: list[Campo] = []
    # **Todo el cuerpo corre con ese perfil puesto**, no solo los lectores: los
    # decodificadores de `estructuras` miden los bloques contra el perfil
    # activo, asi que con el del X8 Pro puesto un bloque de otro mouse no pasa
    # el chequeo de largo y la funcion devolvia **una lista vacia, sin decir
    # nada**. El bloque es por hilo (ver `dispositivos.como`), asi que mirar un
    # estado ajeno desde la ventana no le cambia el perfil al hilo que esta
    # hablando con el mouse de enfrente.
    with disp.como(perfil):
        for cmd, lector in LECTORES.items():
            datos = _bloque(estado, cmd)
            if datos is None:
                continue
            try:
                salida.extend(lector(datos, perfil, via))
            except Exception as exc:       # noqa: BLE001
                # Un bloque raro no puede llevarse puesta la lectura de los
                # otros: el que mira la pantalla prefiere ver seis campos que
                # ninguno.
                #
                # **Pero se avisa.** Escribiendo este modulo, un `KeyError` por
                # una clave mal escrita hizo desaparecer todos los botones sin
                # una linea de error, y lo encontro el test y no la corrida. Un
                # `except` que no deja rastro es una trampa para el que venga.
                log.warning("no pude leer los campos de %s: %s",
                            p.CMD_NAMES.get(cmd, cmd), exc)
    return salida


@dataclass(frozen=True)
class BotonFisico:
    """Un boton del mouse **como cosa fisica**, con su evidencia al lado.

    Es lo que necesita un diagrama y no trae `campos_de()`: el numero de slot
    -que es lo que un dibujo pone sobre el boton- y **como se supo** que ese
    slot es ese boton. Un diagrama que pone un numero sobre un boton afirma que
    ese numero es ese boton; si la afirmacion no esta medida, `confirmado` da
    `False` y quien dibuje tiene que decirlo en vez de disimularlo.

    `clave` es la del campo de `campos_de()`, asi que una ventana puede ir del
    numero del dibujo a la fila del control sin conocer ningun nombre.
    """

    slot: int
    clave: str
    nombre: str
    #: Que funcion tiene hoy, como la acepta el despachador ("adelante").
    funcion: Any
    #: La misma, como se lee en pantalla ("Adelante (página siguiente)").
    funcion_legible: str
    #: De donde sale que ese slot es ese boton. Ver
    #: `estructuras.COMO_SE_SUPO_EL_BOTON`.
    como_se_supo: str
    confirmado: bool
    cmd: int = p.CMD_BUTTONS


def botones_fisicos(estado: dict) -> list[BotonFisico]:
    """Los botones remapeables del mouse, en orden de slot, con su evidencia.

    Solo los que el mouse contesto: si cmd 8 no llego, no hay botones que
    dibujar. El sentido del scroll **no** esta aca, y no es un olvido: son los
    slots 17 y 18, que no se remapean y no son un boton.
    """
    datos = _bloque(estado, p.CMD_BUTTONS)
    if datos is None:
        return []
    botones = est.botones_de(datos)
    if botones is None:
        return []
    por_slot = {b["indice"]: b for b in botones}
    salida = []
    for nombre_fisico, slot in sorted(est.BOTONES_POR_NOMBRE.items(),
                                      key=lambda kv: kv[1]):
        b = por_slot.get(slot)
        if b is None:
            continue
        campo = _campo_de_boton(nombre_fisico, slot, b)
        salida.append(BotonFisico(
            slot=slot, clave=campo.clave, nombre=campo.nombre,
            funcion=campo.valor,
            funcion_legible=(campo.etiqueta_de_valor
                             or (campo.etiquetas or {}).get(campo.valor,
                                                            str(campo.valor))),
            como_se_supo=est.COMO_SE_SUPO_EL_BOTON.get(slot, ""),
            confirmado=est.boton_confirmado(slot)))
    return salida


@dataclass(frozen=True)
class Accion:
    """Algo que se le hace al mouse con un boton, y que no es un valor.

    Es como un `Campo` sin valor: la ventana la dibuja en el grupo de `cmd`,
    abajo de la fila `despues_de`, y al apretarla pide escribir `clave` con
    `valor`, que `sesion.preparar_mutacion()` sabe traducir. **La ventana no
    conoce ninguna por nombre**, igual que con los campos.
    """

    clave: str
    nombre: str
    boton: str
    cmd: int
    definicion: str = ""
    despues_de: str = ""
    valor: Any = True


#: Intercambiar el clic izquierdo y el derecho (los botones 1 y 2) en una sola
#: escritura. Lo pidio el usuario, junto con la baranda que deja
#: remapear el boton 1: con dos escrituras sueltas el orden importa, y con una
#: no.
ACCION_INTERCAMBIAR_CLICS = "intercambiar_clics"


def acciones_de(estado: dict) -> list[Accion]:
    """Las acciones que el estado permite: hoy, solo con los botones leidos."""
    datos = _bloque(estado, p.CMD_BUTTONS)
    if datos is None or est.botones_de(datos) is None:
        return []
    return [Accion(
        ACCION_INTERCAMBIAR_CLICS,
        "Intercambiar los botones izquierdo y derecho",
        "Intercambiar", p.CMD_BUTTONS,
        definicion=("Pasa lo que hace el botón 1 al botón 2, y lo del 2 al 1, "
                    "en una sola escritura.\n\nSirve para usar el mouse con la "
                    "mano izquierda, y para volver a dejarlo como estaba."),
        despues_de=clave_de_boton("derecho"))]


def por_clave(estado: dict, perfil=None, via=None) -> dict[str, Campo]:
    """Lo mismo, indexado por la clave estable de cada campo."""
    return {c.clave: c for c in campos_de(estado, perfil, via)}


# --- los macros, que no son campos escalares -------------------------------
#
# `campos_de()` devuelve parametros sueltos, y un macro no lo es: tiene un
# disparo, una lista de pasos y un nombre que el mouse **no guarda**. Lo pidio
# la auditoria del agente A como G-02, y hace falta para que la pantalla de macros
# no tenga que abrir `estado["macros"]` y decodificar a mano.

#: Lo que el firmware hace con cada modo, dicho para quien mira la pantalla.
#: Los tres salen del soft nativo y **dos estan MEDIDOS apretando el boton**
#: (el 0 y el 2); el 1 sigue con el acuse y la relectura.
QUE_HACE_EL_MODO = {
    0: "lo reproduce N veces y para solo",
    1: "lo repite hasta que se apriete otro boton del mouse",
    2: "lo repite mientras el boton este apretado",
}
#: **Los tres modos estan medidos**, apretando el boton. El 1 era el que
#: faltaba y se cerro el 2026-09-20: se dispara al apretar, sigue despues de
#: soltar, una tecla del teclado **no** lo detiene -se escribe esa tecla y el
#: macro sigue- y lo detiene cualquier otro boton del mouse. Cuatro corridas,
#: las cuatro iguales.
#:
#: Queda la constante, en None, porque el aviso de "modo sin medir" es la clase
#: de cosa que vuelve a hacer falta en cuanto aparezca un modelo con el cuarto
#: modo que el bundle lista (`StopOnCurrentKey`) y el X8 Pro no tiene.
MODO_SIN_MEDIR = None
AVISO_MODO_SIN_MEDIR = "este modo todavía no se probó en el mouse"


@dataclass(frozen=True)
class Macro:
    """Un macro del mouse, listo para mostrar y para editar.

    `nombre` no viene del mouse: el bloque de 111 bytes no tiene campo de
    nombre y lo guarda la aplicacion (`linshark.nombres`). Si no hay ninguno
    guardado, es `"macro N"`.
    """

    id: int
    #: Siempre mostrable: el que le puso el usuario, o `"macro N"`.
    nombre: str
    #: El que le puso el usuario, o `None`. La interfaz lo necesita para saber
    #: si mostrar el nombre en gris -es el default- o como algo que se edito.
    nombre_propio: str | None
    modo: int
    modo_nombre: str
    que_hace: str
    #: None en los modos 1 y 2: ahi el byte no es un contador
    #: (`estructuras.parametros_de_macro`), y mostrarlo como tal seria
    #: inventar un dato.
    repeticiones: int | None
    eventos: tuple
    #: Los mismos eventos en el formato que acepta `estructuras.eventos_desde_texto`,
    #: asi que lo que se muestra se puede volver a escribir sin traducir nada.
    texto: str
    #: Lo que hay que decirle a quien lo va a usar **antes** de que apriete el
    #: boton. Salen de cosas medidas, no de estilo.
    advertencias: tuple = ()
    checksum_ok: bool = True

    @property
    def cantidad_de_eventos(self) -> int:
        return len(self.eventos)

    @property
    def corre(self) -> bool:
        """Si el firmware lo va a reproducir. Con un solo evento, no."""
        return len(self.eventos) >= est.MACRO_EVENTOS_MIN_QUE_CORRE


def advertencias_de(eventos) -> tuple:
    """Lo que hay que decir de una lista de eventos **antes** de grabarla.

    Es publica porque la interfaz la necesita sobre la lista que se esta
    editando, que todavia no es ningun `Macro`: avisar despues de escribir
    llega tarde para las dos cosas medidas -que un macro de un
    evento no corre, y que dejar algo sin cerrar traba la tecla-.
    """
    # **Los textos son de pantalla, y la evidencia queda aca.** Que un macro de
    # un evento no corre y que el firmware no suelta nada al terminar esta
    # MEDIDO (en las dos direcciones: el mouse lo guarda, la
    # relectura lo devuelve bien, y al apretar el boton no pasa nada). Que
    # una tecla trabada no se despega apretandola, tambien: hubo que desacoplar
    # el dongle. La rama de cuatro bytes de los tiempos largos esta INFERIDA
    # del bundle: ninguna captura la mostro.
    avisos = []
    if len(eventos) < est.MACRO_EVENTOS_MIN_QUE_CORRE:
        avisos.append(
            f"un macro de {len(eventos)} evento(s) no se reproduce: el mouse "
            "lo guarda, pero al apretar el botón no pasa nada. Hacen falta al "
            f"menos {est.MACRO_EVENTOS_MIN_QUE_CORRE}")
    sin_cerrar = est.eventos_sin_cerrar(eventos)
    if sin_cerrar:
        quienes = ", ".join(est.nombre_de_evento(u) for u in sin_cerrar)
        avisos.append(
            f"deja apretado lo que no suelta ({quienes}): al terminar el "
            "macro esas teclas quedan trabadas, y apretarlas no las destraba: "
            "hay que desconectar el receptor del mouse")
    largos = est.cuantos_largos(eventos)
    if largos:
        avisos.append(
            f"{largos} evento(s) esperan más de {est.MACRO_TIEMPO_CORTO_MAX} "
            "ms: los tiempos largos todavía no se probaron en el mouse")
    return tuple(avisos)


def macros_de(estado: dict, nombres=None) -> list[Macro]:
    """Los macros que trae un estado, con su nombre local y sus advertencias.

    `nombres` es un `linshark.nombres.NombresDeMacro` o cualquier objeto con
    `.nombre(id)`; sin el, cada macro se llama `"macro N"`.

    **Solo devuelve los que el estado trae.** `sesion.leer_estado()` lee los
    que algun slot de cmd 8 apunta, mas los de `macros_extra`: un macro cargado
    y sin asignar no aparece si nadie lo nombra, porque el mouse no tiene un
    indice de macros que se pueda pedir.
    """
    salida = []
    for sid, entrada in sorted((estado.get("macros") or {}).items(),
                               key=lambda kv: int(kv[0])):
        mid = int(sid)
        propio = nombres.nombre(mid) if nombres is not None else None
        como_se_llama = propio or f"macro {mid}"
        if entrada is None:
            # El mouse no contesto esa lectura. Se devuelve igual, con la
            # advertencia: esconderlo haria creer que el macro no existe.
            salida.append(Macro(
                id=mid, nombre=como_se_llama, nombre_propio=propio, modo=-1, modo_nombre="?",
                que_hace="", repeticiones=0, eventos=(), texto="",
                advertencias=("el mouse no contestó esta lectura: mové el "
                              "mouse y volvé a leer",),
                checksum_ok=False))
            continue
        try:
            par = est.parametros_de_macro(bytes.fromhex(entrada["datos"]))
        except Exception as exc:       # noqa: BLE001
            log.warning("no pude leer el macro %s: %s", mid, exc)
            par = None
        if par is None:
            salida.append(Macro(
                id=mid, nombre=como_se_llama, nombre_propio=propio, modo=-1, modo_nombre="?",
                que_hace="", repeticiones=0, eventos=(), texto="",
                # Con un id que no existe el mouse contesta un bloque vacio,
                # que no cierra como macro.
                advertencias=("el mouse no tiene un macro guardado con ese "
                              "ID",),
                checksum_ok=False))
            continue
        eventos = tuple(par["eventos"])
        modo = par["modo"]
        avisos = list(advertencias_de(eventos))
        if MODO_SIN_MEDIR is not None and modo == MODO_SIN_MEDIR:
            # Hoy no hay ninguno: los tres del X8 Pro se verificaron apretando
            # el boton. Queda el camino para el modelo que traiga el cuarto.
            avisos.append(AVISO_MODO_SIN_MEDIR)
        salida.append(Macro(
            id=mid,
            nombre=como_se_llama,
            nombre_propio=propio,
            modo=modo,
            modo_nombre=par["modoNombre"],
            que_hace=QUE_HACE_EL_MODO.get(modo, ""),
            repeticiones=par["repeticiones"],
            eventos=eventos,
            texto=est.texto_de_eventos(eventos) if eventos else "",
            advertencias=tuple(avisos),
            checksum_ok=bool(entrada.get("checksum_ok", True))))
    return salida
