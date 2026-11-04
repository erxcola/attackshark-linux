# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Que asume el codigo sobre **este** mouse, declarado en un solo lugar.

Todo lo que hay en `estructuras.py` y en `protocol.py` esta medido contra un
Attack Shark X8 Pro y **solo contra ese**: los tamaños de bloque, los dieciocho
slots de boton, los ocho niveles de dpi, la permutacion de los slots 4, 5 y 6.
Mientras haya un solo modelo eso no molesta; en cuanto haya dos, cada una de
esas constantes es una pregunta.

Desde este modulo **manda**: `estructuras.py` no tiene los
numeros adentro, los lee de aca (`activo()`), y `modelo.py` decide con
`campos_ausentes` que controles ofrece. Antes solo los juntaba en un lugar y
`test_el_perfil_no_miente` los comparaba contra las constantes; ahora que son
la misma cosa, ese test compara el perfil contra **la evidencia** -las
capturas y el bundle-, que es lo unico que puede desmentirlo, y
`test_el_perfil_manda_de_verdad` cambia el perfil y mira que cambie lo que
`estructuras` produce.

**Dos cosas distintas, y conviene no mezclarlas:**

  * el **catalogo** dice que modelos existen. Sale de `store.mouseNum` del
    bundle oficial, o sea esta **LEIDO**: son 47 entradas y solo una -la 8-
    esta confirmada contra hardware;
  * el **perfil** dice como se le habla a uno. Hoy hay uno, el del X8 Pro, y
    esta **MEDIDO**.

Saber que un modelo existe no es saber hablarle. La regla del proyecto sigue
en pie: para agregar uno hace falta la captura de su driver oficial, no
adivinar offsets parecidos.

**El mecanismo vive aca, y los datos de cada modelo en `perfiles/`.** Este
modulo define `Usb`, `Perfil`, el registro `PERFILES` y `activo()`/`usar()`/
`como()`, y no sabe nada de ningun mouse en particular. El unico perfil que
hay hoy, `X8_PRO`, esta en `perfiles/x8pro.py`: agregar un modelo es agregar
un archivo ahi, no tocar este.
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field

from . import protocol as p

#: **Por que camino habla el mouse.** Son dos dispositivos USB distintos, con
#: ids distintos y con canales de configuracion distintos, asi que la via no es
#: un detalle de presentacion: cambia lo que se puede hacer y hasta que tasa
#: llega. Viven aca -y no en `conexiones`, que es quien mira el bus- porque hay
#: codigo que decide por la via sin saber nada del bus: `modelo.campos_de()`
#: ofrece menos tasas por cable, y eso es del mouse, no de sysfs.
VIA_DONGLE = "dongle"
VIA_CABLE = "cable"
VIA_DESCONOCIDA = "desconocida"


# --- el catalogo: que modelos dice el fabricante que existen ---------------
#
# **El bundle no es de una sola marca.** Sus rutas enrutan a tres -
# `/ATTACKSHARK/...`, `/MAMBASNAKE/...` y `/INX/...`- asi que estos 47 modelos
# son de varias marcas que comparten el mismo software OEM. De los 47, solo 14
# tienen una ruta con marca explicita; los demas caen en paginas genericas y
# **no se les puede atribuir marca con lo que hay**.
#
# Todo esto es LEIDO del bundle. Ninguno de los otros 46 se probo nunca.
MARCAS_DEL_BUNDLE = ("ATTACKSHARK", "MAMBASNAKE", "INX")

#: Los que el bundle atribuye a una marca por su ruta. El resto queda en None,
#: que quiere decir "no se sabe", no "generico".
MARCA_POR_DEVICE_ID = {
    1: "ATTACKSHARK", 2: "ATTACKSHARK", 4: "ATTACKSHARK", 6: "ATTACKSHARK",
    7: "ATTACKSHARK", 8: "ATTACKSHARK", 14: "ATTACKSHARK", 36: "ATTACKSHARK",
    44: "MAMBASNAKE", 177: "ATTACKSHARK", 188: "MAMBASNAKE",
    190: "ATTACKSHARK", 229: "ATTACKSHARK", 234: "ATTACKSHARK",
}


def catalogo() -> dict[int, tuple[str, str | None]]:
    """`device_id -> (nombre, marca o None)`, los 47 que conoce el bundle."""
    return {num: (nombre, MARCA_POR_DEVICE_ID.get(num))
            for num, nombre in p.MOUSE_NUM.items()}


# --- el perfil: como se le habla a un modelo -------------------------------

@dataclass(frozen=True)
class Usb:
    """Como se lo encuentra en el bus."""

    vendor: int
    producto_dongle: int
    #: El mismo mouse por cable declara otro producto **y se configura de otra
    #: forma**: Feature Reports de largo variable, no un Output Report. Solo lo
    #: abre `cable.py`; `verificar_nodo_dongle()` lo rechaza a proposito, asi
    #: que el CLI y el puente siguen hablando solo por el dongle. `None` en un
    #: modelo cuyo cable no se midio: `conexiones.py` no lo reconoce como camino.
    producto_cable: int | None
    interfaz: int
    report_id: int
    report_size: int
    #: Vacio en el X8 Pro: lo leimos de sysfs y no trae ninguno, asi que **no
    #: sirve para distinguir dos dongles iguales**.
    tiene_serial: bool = False


@dataclass(frozen=True)
class Perfil:
    """Lo que hay que saber de un modelo para configurarlo.

    Cada campo es algo que en otro mouse **puede ser distinto**. Si alguno
    resulta igual en todos, mejor: se habra medido dos veces.
    """

    device_id: int
    nombre: str
    marca: str | None
    usb: Usb

    #: `cmd -> sizeTotalData`, el largo que el mouse declara para cada bloque.
    #: Es lo primero que cambia entre modelos: un mouse con menos botones tiene
    #: un cmd 8 mas corto. **`estructuras.py` lee estos numeros de aca**, asi
    #: que cambiar uno cambia como se decodifica y como se escribe.
    bloques: dict[int, int]
    #: Los que pasaron la Etapa 2 **para este modelo**.
    escribibles: frozenset[int]

    botones: int
    #: Los botones que pueden llevar el clic izquierdo, y entre los que siempre
    #: tiene que quedar uno. La baranda es por modelo y no global: que botones
    #: se pueden usar comodo depende del chasis.
    slots_para_clic_izquierdo: tuple[int, ...]
    #: Los dos slots de la rueda, en la numeracion de lectura.
    slots_de_rueda: tuple[int, int]
    #: La permutacion entre lectura y escritura. **MEDIDA** para el X8 Pro;
    #: en otro modelo puede no existir, o ser otra.
    remapeo_de_slots: dict[int, int]

    #: `nombre fisico -> slot leido`. Que botones tiene el chasis y donde cae
    #: cada uno: dos modelos con el mismo protocolo pueden tener otros botones
    #: y otro orden. Los nombres son los que ve quien usa el CLI y la ventana.
    botones_por_nombre: dict[str, int]
    #: **Como se supo que cada slot es ese boton fisico**, por slot. Es
    #: evidencia y no decoracion: un diagrama que pone un numero sobre un boton
    #: **afirma** que ese numero es ese boton, y un slot que no figure aca
    #: `estructuras.boton_confirmado()` lo da por no medido. Por eso viaja con
    #: el perfil: lo que se midio se midio **de este modelo**.
    como_se_supo_el_boton: dict[int, str]

    niveles_dpi: int
    dpi_minimo: int
    dpi_maximo: int
    #: Las tasas que este modelo acepta **por el dongle**, que es por donde
    #: sale la mas alta.
    tasas: tuple[int, ...]
    macro_eventos_max: int
    macro_id_min: int
    macro_id_max: int

    #: El techo de tasa **por cable**, que no es el del dongle: el dispositivo
    #: del cable es Full Speed con `bInterval` de 1 ms (`dev/models/attackshark-x8pro/docs/hardware.md`,
    #: descriptor leido), asi que fisicamente no da mas de
    #: 1000 Hz. No es una decision nuestra ni una limitacion de Linux: lo dice
    #: el descriptor del propio mouse.
    tasa_maxima_por_cable: int = 1000

    #: Las claves de `modelo.py` que este mouse **no ofrece**, y el motivo de
    #: cada una. La interfaz se construye desde los campos, asi que sacar una
    #: clave de aca hace aparecer el control **sin tocar la ventana**.
    #:
    #: No es "campos que el protocolo no tiene": es que en **este** chasis el
    #: control no cambiaria nada, y un control que mueve bytes sin cambiar nada
    #: es el reproche que este proyecto le hace al cliente oficial. La
    #: capacidad de escribir el campo no se toca: `sesion.preparar_mutacion()`
    #: y el CLI siguen andando.
    campos_ausentes: dict[str, str] = field(default_factory=dict)

    #: **Donde el perfil completo (cmd 10) embebe a cada bloque**, como
    #: `cmd -> (offset en el perfil, offset en el bloque, largo)`.
    #:
    #: Que el perfil los embeba ya estaba en `evidencia.md`; lo que faltaba era
    #: poder **cruzarlo**. Sirve para eso: cmd 10 no tiene checksum interno y es
    #: el testigo de toda escritura por el camino de la relectura acotada, asi
    #: que sin esto una lectura suya corrompida no la nota nadie. Con esto, el
    #: perfil y el bloque se contradicen y se sabe.
    #:
    #: Los offsets son **de este modelo** -dependen de los largos de bloque, que
    #: ya son del perfil- y salen de comparar los 126 respaldos versionados que
    #: tienen los cinco bloques: cada tramo coincide en los 126, y toma entre 3
    #: y 14 valores distintos, asi que la coincidencia no es de bytes fijos. El
    #: unico que discrepa en alguno es el respaldo de la lectura corrompida del
    #: 2026-09-20, que es justo lo que esto tiene que agarrar.
    perfil_embebe: dict[int, tuple[int, int, int]] = field(default_factory=dict)


#: Los modelos a los que este codigo sabe hablarle. Lo pueblan los modulos de
#: `perfiles/` (hoy, uno solo) llamando a `registrar()`. Que el catalogo tenga
#: 47 no significa que los otros 46 anden: significa que existen.
PERFILES: dict[int, Perfil] = {}


def registrar(perfil: Perfil, *, predeterminado: bool = False) -> None:
    """Suma un perfil al registro. No lo llama el codigo que usa el mouse.

    Lo llama `linshark/__init__.py`, una vez por modulo de `perfiles/`, al
    arrancar el paquete. Va ahi y no aca abajo porque cada modulo de
    `perfiles/` importa `Perfil` y `Usb` **desde este archivo**: si este
    archivo importara a su vez a `perfiles/` para poblarse solo, el ciclo no
    cierra. El import de un paquete corre su `__init__.py` antes que
    cualquier submodulo, asi que para cuando algo usa `activo()` esto ya
    paso.
    """
    global _GLOBAL
    PERFILES[perfil.device_id] = perfil
    if predeterminado:
        _GLOBAL = perfil


class ModeloDesconocido(Exception):
    """Hay un mouse, pero no sabemos como se le habla."""


def perfil_de(device_id: int) -> Perfil:
    """El perfil de ese modelo, o un error que dice que se sabe de el."""
    perfil = PERFILES.get(device_id)
    if perfil is not None:
        return perfil
    nombre, marca = catalogo().get(device_id, (None, None))
    if nombre is None:
        raise ModeloDesconocido(
            f"device id {device_id} no figura en el catalogo del bundle "
            f"({len(p.MOUSE_NUM)} modelos). Puede ser un modelo mas nuevo")
    de_quien = f" de {marca}" if marca else ""
    # Mismo texto que cuando `X8_PRO` estaba a mano en este modulo: con un
    # solo perfil medido, nombrarlo asi es exacto. El dia que haya dos, esta
    # frase es parte de lo que hay que generalizar -no antes, que seria
    # texto nuevo sin nada que lo use todavia-.
    medido = next(iter(PERFILES.values()))
    raise ModeloDesconocido(
        f"el mouse dice ser un {nombre}{de_quien} (device id {device_id}), que "
        f"el bundle conoce pero este codigo **no tiene medido**. Todo lo que "
        f"hay esta verificado contra un {medido.nombre} y solo contra ese: los "
        "tamaños de bloque, los slots y la permutacion pueden ser otros. Para "
        "agregarlo hace falta la captura de su driver oficial, no adivinar "
        "offsets parecidos (ver dev/docs/metodo.md)")


# --- el perfil que esta en uso ---------------------------------------------
#
# Hay **uno** medido, asi que hoy esto devuelve casi siempre el mismo. Existe
# para que el resto del codigo no vuelva a tener los numeros del X8 Pro
# escritos adentro: `estructuras.py` le pregunta a `activo()` en cada llamada,
# asi que cambiar el perfil cambia como se decodifica y como se escribe, sin
# tocar una linea de los codificadores.
#
# **Son dos cosas distintas, y por eso hay dos funciones:**
#
#   * `usar()` elige el modelo **para todo el programa**. Lo llama `Hardware`
#     cuando el mouse dice que modelo es y `perfil_de()` devuelve un perfil, o
#     sea **solo con un modelo medido**: un device id que no tenemos medido
#     levanta `ModeloDesconocido` y no cambia nada;
#   * `como()` lo cambia **solo en el hilo que lo llama** y mientras dure el
#     bloque. Es para leer un estado guardado de otro mouse -o para una
#     prueba- sin que el hilo de hardware, que esta decodificando lo que
#     contesta el mouse de enfrente, decodifique con el perfil equivocado.
#
# Que `como()` sea por hilo no es un detalle: la aplicacion tiene un hilo de
# hardware y el de la ventana, y `modelo.campos_de(estado, perfil)` abre uno de
# estos bloques. Con una variable global compartida, mirar un estado ajeno
# desde la ventana le cambiaria el perfil al hilo que habla con el mouse.
#
# Arranca en `None` y no con el perfil de un modelo puesto a mano: lo pone
# `registrar(..., predeterminado=True)` desde `linshark/__init__.py`, antes de
# que nada mas del paquete se pueda usar.
_GLOBAL: Perfil | None = None
_DE_ESTE_HILO = threading.local()


def activo() -> Perfil:
    """El perfil con el que se esta hablando ahora mismo, en este hilo."""
    return getattr(_DE_ESTE_HILO, "perfil", None) or _GLOBAL


def usar(perfil: Perfil) -> None:
    """Pasa a hablarle a ese modelo, en todo el programa.

    Cambia como se decodifica **todo**, asi que se llama con un perfil que
    salio de `perfil_de()` -o sea, uno medido-, no con uno armado a mano.
    """
    global _GLOBAL
    if not isinstance(perfil, Perfil):
        raise TypeError(f"esto no es un Perfil: {perfil!r}")
    _GLOBAL = perfil


@contextmanager
def como(perfil: Perfil):
    """El perfil, en **este hilo** y mientras dure el bloque.

    Lo usa `modelo.campos_de(estado, perfil)` para leer un estado con el perfil
    del mouse del que salio, y lo usan las pruebas: una que quiera ver si el
    codigo lee de verdad del perfil arma uno de fantasia -con otros tamaños y
    otros botones- y mira que el bloque cambie. Si algo tuviera el numero del
    X8 Pro adentro, no cambiaria.
    """
    if not isinstance(perfil, Perfil):
        raise TypeError(f"esto no es un Perfil: {perfil!r}")
    anterior = getattr(_DE_ESTE_HILO, "perfil", None)
    _DE_ESTE_HILO.perfil = perfil
    try:
        yield perfil
    finally:
        _DE_ESTE_HILO.perfil = anterior
