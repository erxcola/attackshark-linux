# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Protocolo de la web szslxd-tech.com <-> helper nativo (ws://localhost:10086).

Todo lo de este modulo salio de leer el bundle JavaScript de la web
(ver ../../docs/protocolo.md). Los mensajes viajan como frames de TEXTO
con el contenido en hexadecimal ASCII, sin separadores.

    pagina -> helper    "8100000a00"   ->  [0x81, 0x00, 0x00, 0x0a, 0x00]
    helper -> pagina    "0305"         ->  [3, 5]

La pagina decodifica con:

    convertToHexArray(e) {
        return e.length % 2 !== 0 && (e += "0"),
               e.match(/.{1,2}/g).map(n => parseInt(n, 16))
    }
"""

from __future__ import annotations

# --- version del helper -----------------------------------------------------
# La pagina guarda version:[3,5] y muestra el cartel "actualiza el driver"
# si lo que recibe no coincide exactamente. Ademas, si major < 3 (o 3.0)
# desactiva TODA la funcionalidad de lectura (readFlag = true).
HELPER_VERSION = (3, 5)

# --- metodos de conexion (primer byte de los paquetes de presencia) ---------
# store.setDevice() rutea segun este byte:
#   128 -> setWiredDevice        (cable, 1 kHz)
#   129 -> setWirelessDevice     (2.4 GHz)
#   130 -> setWiredDevice8K      (8 kHz, marca highSpeedFlag = 1)
#   131 -> setWiredDevice8K
#   132 -> setWirelessDevice     (bluetooth; solo si el paquete mide 6 bytes)
#   133 -> setWiredDevice8K
CONN_WIRED = 0x80
CONN_WIRELESS = 0x81
CONN_8K_A = 0x82
CONN_8K_B = 0x83
CONN_BLUETOOTH = 0x84
CONN_8K_C = 0x85

CONN_NAMES = {
    CONN_WIRED: "cable 1 kHz",
    CONN_WIRELESS: "2.4 GHz",
    CONN_8K_A: "8 kHz (0x82)",
    CONN_8K_B: "8 kHz (0x83)",
    CONN_BLUETOOTH: "bluetooth",
    CONN_8K_C: "8 kHz (0x85)",
}

# Los que hacen que la pagina marque highSpeedFlag = 1 y habilite 8 kHz.
CONN_HIGH_SPEED = (CONN_8K_A, CONN_8K_B, CONN_8K_C)

# --- identificadores de modelo (store.mouseNum) -----------------------------
DEVICE_X8_PRO = 8

MOUSE_NUM = {
    1: "X3Pro", 2: "X8SE", 4: "G3", 5: "F3", 6: "X8Plus", 7: "X11SE",
    8: "X8Pro", 12: "F7Pro", 13: "F7", 14: "G3Pro", 16: "R1", 20: "MV6",
    36: "V6", 43: "M800Mini", 44: "M2", 48: "M900Pro", 61: "M900Mini",
    65: "IN6", 66: "In9", 67: "G15", 73: "F1", 77: "X3", 78: "X3Max",
    85: "X11", 97: "G64", 98: "V2Ultra", 101: "V2MC", 108: "G25",
    109: "DVSE4", 119: "G11", 133: "X6", 135: "M740", 144: "IN9Ultra",
    146: "IN6SE", 147: "IN10", 153: "INX", 154: "MC031", 158: "V2MAX",
    177: "X1", 188: "M3", 190: "X11Pro", 195: "Vanguard", 201: "G9PRO",
    203: "V2", 204: "V2Ultra3955", 229: "V3Pro", 234: "V3",
}

# --- estado de bateria (store.mouseArr[].batteryStatus) ---------------------
# Es el byte [2] del reporte de presencia, al lado del porcentaje.
#
# Los dos valores que manda este mouse estan **MEDIDOS** con
# `driver/scripts/sondear.py --escuchar`, poniendo y sacando el cargador dos veces en
# una sola corrida (ver `dev/models/attackshark-x8pro/docs/bitacora.md`). Las cuatro transiciones siguieron
# al cargador, con el enlace vivo de los dos lados, y el LED morado de carga
# las confirmo por fuera del protocolo.
#
# El 2 sale del bundle -es su constante de "desconocido"- y **nunca se lo vio
# en el hardware**; por eso `sesion.Novedad.cargando` da None con ese valor en
# vez de False.
BATTERY_DISCHARGING = 1   # MEDIDO: sin cargador
BATTERY_UNKNOWN = 2       # del bundle; jamas observado
BATTERY_CHARGING = 3      # MEDIDO: cargando

# --- marcadores dentro de los paquetes --------------------------------------
# El Report ID 3 no es solo presencia: es un canal de notificaciones con un
# byte de tipo en la posicion 1. Confirmado escuchando el hardware:
#
#     08 40 01 64   -> presencia: [deviceId, 0x40, estadoBateria, nivelBateria]
#     08 10 03 00   -> cambio de DPI: [deviceId, 0x10, nivel, 0]
#
# El helper reenvia estas notificaciones anteponiendo [connectionMethod, 0x01],
# y de ahi salen los 6 bytes que espera la pagina: el tipo cae en n[3], que es
# justo donde el store decide si es presencia (0x40/0x41) o cambio de DPI
# (0x10, con el nivel en n[4], 1-based).
NOTIF_PRESENCIA = 0x40
NOTIF_PRESENCIA_ALT = 0x41
NOTIF_DPI = 0x10

NOTIF_NOMBRES = {
    NOTIF_PRESENCIA: "presencia + bateria",
    NOTIF_PRESENCIA_ALT: "presencia + bateria",
    NOTIF_DPI: "cambio de nivel de DPI",
}

PRESENCE_MARK = NOTIF_PRESENCIA

# Prefijo de los comandos de LECTURA, que el helper interpreta el mismo
# en vez de reenviarlos crudos al mouse:
#     [0xF0, connectionMethod, deviceId, cmd, sub]
READ_PREFIX = 0xF0

# Codigos de comando vistos en las respuestas (byte 2 de helper -> pagina):
CMD_DPI = 4
CMD_LIGHTING = 5
CMD_REPORT_RATE = 6
CMD_WAKEUP = 7           # con sub == 8
CMD_BUTTONS = 8          # con sub != 8
CMD_MACRO = 9
CMD_PROFILE = 10         # lectura entera; respuesta >= 120 bytes con sub 0x80
CMD_VERSION = 11         # con sub == 8
CMD_ACK = 0x50           # respuesta de 5 bytes: [conn, dev, 0x50, ok, x]

CMD_NAMES = {
    CMD_DPI: "dpi",
    CMD_LIGHTING: "iluminacion",
    CMD_REPORT_RATE: "report rate",
    CMD_WAKEUP: "modo de despertado",
    CMD_BUTTONS: "botones",
    CMD_MACRO: "macro",
    CMD_PROFILE: "perfil completo",
    CMD_VERSION: "version de firmware",
    CMD_ACK: "ack",
}


# --- codec ------------------------------------------------------------------

def decode(text: str) -> list[int]:
    """Igual que convertToHexArray() de la pagina."""
    if len(text) % 2 != 0:
        text += "0"
    return [int(text[i:i + 2], 16) for i in range(0, len(text), 2)]


def encode(data) -> str:
    """Bytes -> string hex en minusculas, que es lo que la pagina espera."""
    return "".join(f"{b & 0xFF:02x}" for b in data)


# --- constructores de mensajes helper -> pagina -----------------------------

def version_message(version=HELPER_VERSION) -> str:
    """Mensaje de 2 bytes con la version del helper."""
    return encode(version)


def presence_message(
    connection_method: int,
    device_id: int,
    battery_status: int = BATTERY_UNKNOWN,
    battery_level: int = 100,
) -> str:
    """Paquete de presencia de 7 bytes.

    Que el helper anteponga [connectionMethod, 0x01] ya no es una suposicion:
    esta literal en sus cadenas de formato, una por metodo de conexion
    (VA 0x60ac0c, usada en 0x410a89):

        "8001%02x%02x%02x%02x%02x"    "8101%02x%02x%02x%02x%02x"
        "8201%02x%02x%02x%02x%02x"    "8301%02x%02x%02x%02x%02x"
        "8501%02x%02x%02x%02x%02x"    "8401%02x%02x%02x%02x"

    Cinco bytes formateados detras del prefijo dan los 7 del paquete. La del
    bluetooth (0x84) tiene **cuatro**, o sea 6 bytes, que es exactamente la
    variante corta que la pagina solo acepta para ese metodo.

    Layout que exige la pagina:
        [0] connectionMethod, 0x80..0x85
        [1] 0x01              (setDevice() ignora el paquete si no es 1)
        [2] sin usar
        [3] deviceId
        [4] 0x40 o 0x41       (si no, el handler descarta el paquete)
        [5] batteryStatus
        [6] batteryLevel
    """
    return encode([
        connection_method,
        0x01,
        0x00,
        device_id,
        PRESENCE_MARK,
        battery_status,
        battery_level,
    ])


def notification_message(connection_method: int, payload) -> str:
    """Reenvia una notificacion del Report ID 3 tal como lo hace el helper.

    Le antepone [connectionMethod, 0x01] al payload que manda el mouse: 4
    bytes para presencia, 3 para cambio de dpi (MEDIDO, `evidencia.md`). El
    0x01 es obligatorio: setDevice() descarta el paquete si n[1] no es 1.
    """
    return encode(bytes([connection_method, 0x01]) + bytes(payload))


def unplug_message(connection_method: int, device_id: int) -> str:
    """Paquete de 3 bytes que le dice a la pagina que el mouse se desconecto.

    La pagina chequea: n.length === 3 && n[1] === 0, y saca n[2] de mouseArr.
    O sea que solo le importan los dos ultimos bytes, pero el helper oficial
    pone el connectionMethod en el primero. Se ve en sus cadenas de formato,
    una por metodo de conexion (VA 0x60aa7c y vecinas, usadas en 0x40c06c):

        "8000%02x"  "8100%02x"  "8200%02x"
        "8300%02x"  "8400%02x"  "8500%02x"

    y el argumento que se formatea sale de [esi+0x418], el campo de deviceId
    del objeto de dispositivo.
    """
    return encode([connection_method, 0x00, device_id])


def ack_message(connection_method: int, device_id: int, ok: bool = True) -> str:
    """Ack de 5 bytes: cierra el overlay de 'guardando' de la pagina.

    n.length === 5 && n[2] === 0x50 && n[3] === 0  -> exito
    n.length === 5 && n[2] === 0x50 && n[3] === 1  -> la pagina reintenta
    """
    return encode([connection_method, device_id, CMD_ACK, 0 if ok else 1, 0])


# --- parser de mensajes pagina -> helper ------------------------------------

class Request:
    """Un mensaje que la pagina le manda al helper.

    Hay dos familias:

    1. Lectura, 5 bytes con prefijo 0xF0:
           [0xF0, connectionMethod, deviceId, cmd, sub]
       El helper la interpreta y contesta con los datos del mouse.

    2. Escritura, largo variable:
           [connectionMethod, deviceId, ...payload]
       El payload sale tal cual como Output Report ID 4 al mouse.
       (convertDeviceData() de la pagina es justamente lo que antepone
       esos dos bytes; el camino WebHID viejo mandaba el payload pelado
       con sendReport(4, payload).)
    """

    __slots__ = ("raw", "is_read", "malformado", "connection_method",
                 "device_id", "cmd", "sub", "payload")

    def __init__(self, raw: list[int]):
        self.raw = raw
        self.is_read = len(raw) >= 5 and raw[0] == READ_PREFIX
        # Una trama que arranca con 0xF0 y no llega a 5 bytes es una lectura
        # cortada, no una escritura. Sin esto caia en la rama de escritura y
        # se interpretaba el 0xF0 como connectionMethod.
        self.malformado = len(raw) < 5 and bool(raw) and raw[0] == READ_PREFIX
        if self.is_read:
            self.connection_method = raw[1]
            self.device_id = raw[2]
            self.cmd = raw[3]
            self.sub = raw[4]
            self.payload = []
        else:
            self.connection_method = raw[0] if raw else None
            self.device_id = raw[1] if len(raw) > 1 else None
            self.payload = raw[2:]
            # En las escrituras el payload arranca con [cmd, sizeTotalData].
            #
            # MEDIDO contra las cinco escrituras que la pagina oficial mando
            # por WebSocket (`dev/models/attackshark-x8pro/docs/capturas-w/w1-from-har.jsonl`, Etapa W):
            #
            #     83 08 | 04 38 | 01 01 11 3f 00 20 17 2f …   cmd 4  (dpi)
            #     83 08 | 06 09 | 01 33 cc …                   cmd 6  (rate)
            #
            # o sea `payload[0]` es el comando y `payload[1]` el tamano del
            # bloque, que es lo que este proyecto viene llamando `sub`. Antes
            # aca se leia `payload[1]` como comando, con una nota que decia
            # "sin confirmar contra hardware": daba 0x38 o 0x09, que son
            # tamanos. Cualquier allowlist montada sobre ese byte comparaba
            # tamanos contra codigos de comando.
            self.cmd = self.payload[0] if self.payload else None
            self.sub = self.payload[1] if len(self.payload) > 1 else None

    def describe(self) -> str:
        if self.malformado:
            return f"MALFORMADO: lectura cortada de {len(self.raw)} bytes"
        model = MOUSE_NUM.get(self.device_id, f"desconocido({self.device_id})")
        conn = CONN_NAMES.get(self.connection_method, hex(self.connection_method or 0))
        name = CMD_NAMES.get(self.cmd, f"cmd {self.cmd}")
        kind = "LEER " if self.is_read else "ESCRIBIR"
        extra = "" if self.is_read else f" payload={len(self.payload)}B"
        return f"{kind} {name} (sub={self.sub}) | {model} via {conn}{extra}"

    def __repr__(self) -> str:
        return f"<Request {encode(self.raw)}>"


# --- trama del lado del dispositivo -----------------------------------------
# Esto salio de desensamblar WebDriver.exe (el helper oficial de Windows), en
# los sitios donde llama a hid_write() con largo 12. Ver dev/models/attackshark-x8pro/docs/bitacora.md.
#
#     04 0c a0 CMD SUB 00 00 00 00 00 chkHi chkLo
#     ^^ ^^ ^^
#     |  |  opcode: 0xa0 leer, 0x00 escribir
#     |  largo total de la trama
#     Report ID 4
#
# El checksum es la suma llana de todos los bytes anteriores, big-endian, e
# **incluye el byte del Report ID**. De ahi sale el `i = 4` que aparece como
# semilla en los serializadores del JavaScript: no era una constante magica,
# era el Report ID, que sendReport(4, ...) agrega por su cuenta.

DEVICE_REPORT_ID = 4
READ_OPCODE = 0xA0
WRITE_OPCODE = 0x00
READ_FRAME_LEN = 12

# Cada comando de lectura lleva un `sub` fijo que el helper saca de su propia
# tabla. La pagina manda siempre sub=0, asi que esto NO se puede deducir del
# bundle: salio del binario. Se verifica contra los handlers de respuesta de
# la pagina, que esperan justo estos valores (cmd 11 -> sub 8, cmd 10 -> 128).
#
# **El nombre `sub` quedo de la primera lectura y es enganoso.** Ese byte no
# parece un subcomando sino el **largo del bloque** `[cmd, N, ...datos]`. En el
# PEDIDO de lectura el largo total es 12 fijo (el pedido no lleva datos) y N le
# dice al mouse cuanto tiene que devolver; en la RESPUESTA, y en las
# escrituras, el largo sale de ahi: `L = N + 5` (3 de cabecera + N + 2 de
# checksum). Cuadra en los cuatro comandos que se leyeron del mouse, con
# valores bien distintos:
#
#     comando       N     L = N+5   respuesta real
#     version       8     13        04 0d 00 0b 08 ...
#     report rate   9     14        04 0e 00 06 09 ...
#     iluminacion   15    20
#     dpi           56    61        04 3d 00 04 38 ...
#
# Y encaja con el binario, donde el mismo byte es el `n` del memcpy de
# 0x40cf8d y el sumando del `buffer[1] = n + 5` de 0x40d8bf. Explica ademas por
# que la pagina manda siempre 0: no conoce el tamano de cada estructura, lo
# pone el helper de su tabla.
#
# Que la aritmetica cierre 4 de 4 con valores tan dispares hace muy dificil que
# sea casualidad, pero **no se vio al binario calcular ese byte**: la lectura
# "es un largo" es interpretacion. Por eso no se cambio ningun nombre ni se
# genera el valor: la tabla se mantiene tal como salio del desensamblado.
# Comandos cuyo formato de ESCRITURA paso la Etapa 2 de `dev/docs/metodo.md`: el
# estado leido del mouse, pasado por `build_write_frame()`, reproduce byte a
# byte una trama que el driver oficial le mando a este mismo mouse.
#
#     cmd 6:  04 0e 00 06 09 01 44 bb 00 00 00 00 01 21
#     cmd 4:  04 3d 00 04 38 01 01 01 3f 20 00 17 2f 3f 6f 9f 8f … 11 03
#
# Deliberadamente **separada de READ_SUB**: se puede leer mucho mas de lo que
# se puede escribir, y que un comando sea legible no es motivo para dejar
# escribirlo. Agregar algo aca exige repetir la Etapa 2 para ese comando.
# El byte de report rate empaqueta dos nibbles. El ALTO es el indice de
# frecuencia: 125 * 2^(n-1). MEDIDO con una barrida anotada
# (`dev/models/attackshark-x8pro/docs/capturas-w/soft-rates-anotados.txt`), siete de siete:
#
#     0x14 -> 125    0x24 -> 250    0x34 -> 500    0x44 -> 1000
#     0x54 -> 2000   0x64 -> 4000   0x74 -> 8000
#
# Confirmado por separado con la barrida de la web en `web-todo.pcap`, que
# escribe los dos nibbles iguales (0x11 … 0x77).
#
# El nibble bajo **es el que mueve el soft nativo por cable** (MEDIDO en
# `cable-soft-rate-500.pcap` y `cable-soft-rate-1000.pcap`): leyo `0x74`, para
# 500 Hz escribio `0x73` y para 1000 `0x74`, sin tocar el alto. **Y el mouse
# lo aplica como la tasa del cable** (MEDIDO, 2026-09-18): escrito `0x73` desde
# la ventana por cable, `medir-polling.py` enchufado dio 2000 us de mediana,
# 500 Hz. Por el dongle, la web lo pisa con el mismo valor que el alto.
RATE_HZ = {n: 125 * 2 ** (n - 1) for n in range(1, 8)}
RATE_INDICE = {hz: n for n, hz in RATE_HZ.items()}


def rate_indice(byte_rate: int) -> int:
    """El indice de frecuencia que trae el byte de report rate del mouse."""
    return byte_rate >> 4


# CMD_LIGHTING entro, con la misma prueba que los otros dos:
#
#     cmd 5:  04 14 00 05 0f 01 00 03 a8 00 ff 00 01 09 01 b4 00 00 02 96
#
# y en la forma mas fuerte que dio el proyecto hasta ahora, porque el estado de
# partida y la trama de llegada se midieron en maquinas distintas y con tres
# horas de por medio: el driver oficial escribio esos bytes desde Windows
# (`dev/models/attackshark-x8pro/docs/capturas-w/soft-todo.pcap`, 16:16), el mouse los guardo, los leimos
# desde Linux a las 19:00, y recodificar la lectura devuelve la misma trama.
# Aparece igual en soft-rates-anotados.pcap y soft-rate-8000-a-1000.pcap.
# Cubierto por `test_etapa2_ida_y_vuelta`.
#
# **Que este aca no habilita a escribir cualquier campo del bloque.** El bloque
# de cmd 5 lleva nueve campos, tres de ellos con dos cosas en un byte o con el
# significado cambiado segun que pantalla oficial lo escribio (ver la nota de
# `ILUMINACION` en estructuras.py). Lo unico con significado sin ambiguedad es
# el color, y es el unico cambio real que ofrece la herramienta.
# CMD_BUTTONS entro, con la prueba en su forma fuerte y en dos
# variantes, no una:
#
#     cmd 8 idempotente: el bloque que el mouse devolvio a las 17:22:58
#                        (dev/models/attackshark-x8pro/respaldos/20260910-172258.json), pasado por
#                        escribir_boton(), da byte a byte el bloque que el soft
#                        nativo escribio a las 17:21:05
#                        (dev/models/attackshark-x8pro/docs/capturas-w/soft-boton4-vuelve-adelante.pcap)
#
#     cmd 8 con cambio:  el mismo bloque leido, con el costado-adelante puesto
#                        en macro, da byte a byte el que el soft escribio en
#                        dev/models/attackshark-x8pro/docs/capturas-w/soft-macro-asignado.pcap
#
# La segunda es la que importa: reproducir un CAMBIO, y no solo la identidad,
# es lo que descarta que estemos copiando bytes sin entenderlos.
#
# **Y este comando necesito un codificador de verdad, no un memcpy.** Los slots
# 4, 5 y 6 se remapean entre escritura y lectura (MEDIDO, ver
# `estructuras.SLOT_ESCRITO_DE_LEIDO`), asi que devolverle al mouse el bloque
# que se le leyo -que es con lo que empieza cada Etapa 3- le rota tres botones.
# El checksum interno no lo atrapa: es una suma llana y la permutacion la deja
# igual. Por eso el unico camino a este comando es `escribir_boton()` /
# `escribir_rueda()`, y por eso **no se expone por el puente** (ver
# `cli.ESCRIBIBLES`).
# CMD_MACRO entro, y es el unico que llega con la Etapa 2 hecha
# en los DOS sentidos y contra el mismo mouse:
#
#     cmd 9 idempotente: el bloque que el mouse devolvio
#                        (`sondear.py --pedir 9 --macro-id 17`),
#                        pasado por `escribir_macro()`, da byte a byte el que
#                        el soft nativo escribio en
#                        `dev/models/attackshark-x8pro/docs/capturas-w/soft-macro-asignado.pcap`
#
#     cmd 9 con cambio:  el mismo bloque leido, con el modo de disparo puesto
#                        en 0, 1 y 2, da byte a byte las tres escrituras que el
#                        soft hizo en esa captura, con sus dos tramas cada una
#
# Cubierto por `test_etapa2_macro`.
#
# **Y este tambien necesito un codificador de verdad**, por la misma familia de
# razon que cmd 8: el mouse devuelve el checksum interno con los bytes al reves
# (`0c 6d` al escribir, `6d 0c` al leer), asi que devolverle el bloque que dio
# -que es con lo que empieza cada Etapa 3- le manda un bloque mal formado.
#
# **Dos cosas mas que no valen para ningun otro comando.** Es el unico que va
# por `escribir_por_bloques()`, con una ventana entre los dos trozos en la que
# el mouse tiene medio bloque; y es el unico que se lee con el **id del macro**
# en el byte 5, donde los demas llevan el perfil. Tampoco se expone por el
# puente (ver `cli.ESCRIBIBLES`).
WRITABLE = frozenset({CMD_REPORT_RATE, CMD_DPI, CMD_LIGHTING, CMD_BUTTONS,
                      CMD_MACRO})

# Los unicos dos opcodes que la pagina puede pedir. Cualquier otro valor en esa
# posicion es una trama que no sabemos leer, y no se le manda al mouse.
OPCODES_VALIDOS = frozenset({READ_OPCODE, WRITE_OPCODE})

READ_SUB = {
    CMD_DPI: 0x38,
    CMD_LIGHTING: 0x0F,
    CMD_REPORT_RATE: 0x09,
    CMD_BUTTONS: 0x3B,
    CMD_MACRO: 0x6F,
    CMD_PROFILE: 0x80,
    CMD_VERSION: 0x08,
    0x0C: 0x0A,
}

# CMD_WAKEUP (7) NO esta en la tabla a proposito. La pagina lo lista con
# sub=8 en sus handlers de respuesta, y `sendWakeupModeReadCommand()` manda
# literalmente el payload [12, 7, 8, 0, 0, 0, 0, 0]. Pero ese payload viaja
# por el camino de ESCRITURA de la pagina y va sin checksum: no es una de las
# tramas de 12 bytes que arma el helper, y cmd 7 no aparece entre los 8 sitios
# de hid_write con `push 0xc` del binario. Darlo por bueno seria mezclar dos
# framings distintos, o sea inventar una trama. Queda como no soportado hasta
# tener la plantilla real, y el puente lo trata como tal (log y silencio) en
# vez de reventar.


class ComandoSinSub(KeyError):
    """El comando pedido no tiene un `sub` documentado.

    Subclase de KeyError para no romper a quien ya lo capturaba asi. Se
    levanta en vez de adivinar el `sub`: mandar una trama con un sub
    inventado es exactamente el fuzzing sobre el endpoint vendor que el
    proyecto no hace.
    """


def checksum(data) -> tuple[int, int]:
    """Suma llana de los bytes, devuelta como (alto, bajo) big-endian."""
    total = sum(data) & 0xFFFF
    return (total >> 8) & 0xFF, total & 0xFF


# Comandos cuya trama lleva numero de perfil en el byte 5. En el binario se
# ve como `mov al,[ebp+8]; inc al`, o sea que el perfil viaja **1-based**: el
# helper recibe un indice desde 0 y le suma uno. Coincide con el
# `Tn.profileId = 1` que esta hardcodeado en el JavaScript.
#
# Los que NO lo llevan (version, 0x0c) tienen un 0 literal en esa posicion.
CMDS_CON_PERFIL = frozenset({CMD_DPI, CMD_LIGHTING, CMD_REPORT_RATE,
                             CMD_BUTTONS, CMD_MACRO, CMD_PROFILE})


# El byte 5 de una lectura de MACRO: el id, no el perfil. [LEIDO, no capturado]
#
# El bloque de cmd 9 vuelve vacio -`01` y 108 bytes de `0xff`, checksum
# valido-, y se descarto la explicacion facil: se leyo con el
# macro `0x11` **asignado a un boton** (el bloque de cmd 8 del mismo respaldo
# trae `12 00 11`) y volvio igual.
#
# La que queda sale del bundle. `sendMacroDataCommand(macroId)`
# (`chunks/index-Bl1gF1oR.js`, llamada desde `cacheMacroKey`) arma el mensaje
#
#     F0 | connectionMethod | deviceNo | 0x09 | macroId
#
# y ese quinto byte, que en **todas** las otras lecturas de la pagina va en
# cero, aca es el id del macro. Nosotros poniamos ahi el perfil, porque cmd 9
# esta en `CMDS_CON_PERFIL`: le pedimos el macro 1 y el que existe es el 17.
#
# **Que el helper copie ese byte al `frame[5]` es INFERIDO**, y hay un
# argumento en contra: para dpi, luz y rate la pagina manda 0 en esa posicion
# y en el bus aparece `01`, o sea que el helper pone el perfil de su tabla. Si
# eso vale tambien para cmd 9, el id tendria que viajar en otro lado.
#
# Por eso `macro_id` es **explicito y opcional**: el default no cambia, nadie
# lo manda sin pedirlo, y solo lo acepta cmd 9. La alternativa -cambiar el
# default- seria dar por buena una inferencia en el camino que le escribe al
# endpoint vendor. Se cierra con una captura de un cliente oficial leyendo un
# macro; hasta entonces esto es una sonda, no la plantilla.
MACRO_ID_MIN = 1
MACRO_ID_MAX = 255


def build_read_frame(cmd: int, sub: int | None = None,
                     profile: int = 1,
                     length: int = READ_FRAME_LEN,
                     macro_id: int | None = None) -> bytes:
    """Arma una trama de lectura completa, con Report ID y checksum.

    `macro_id` solo se acepta para `CMD_MACRO` y reemplaza al perfil en el
    byte 5. Ver la nota de arriba: es una sonda con una inferencia adentro,
    no la plantilla del helper.
    """
    if sub is None:
        sub = READ_SUB.get(cmd)
        if sub is None:
            raise ComandoSinSub(
                f"no se conoce el sub del comando 0x{cmd:02x} "
                f"({CMD_NAMES.get(cmd, 'sin nombre')}); no se inventa"
            )
    if macro_id is not None:
        if cmd != CMD_MACRO:
            raise ValueError(
                f"macro_id es solo para cmd {CMD_MACRO} (macro); se pidio "
                f"para cmd {cmd}. En los demas comandos el byte 5 es el "
                "perfil y eso si esta capturado")
        if not MACRO_ID_MIN <= macro_id <= MACRO_ID_MAX:
            raise ValueError(
                f"macro_id {macro_id} fuera de {MACRO_ID_MIN}..{MACRO_ID_MAX}")
    frame = bytearray(length)
    frame[0] = DEVICE_REPORT_ID
    frame[1] = length
    frame[2] = READ_OPCODE
    frame[3] = cmd
    frame[4] = sub
    if macro_id is not None:
        frame[5] = macro_id
    elif cmd in CMDS_CON_PERFIL:
        frame[5] = profile
    hi, lo = checksum(frame[:length - 2])
    frame[length - 2] = hi
    frame[length - 1] = lo
    return bytes(frame)


# --- trama de ESCRITURA -----------------------------------------------------
# De los 17 sitios de hid_write del binario, 9 usan largo 0x41 (65 bytes) y son
# el camino de escritura. La rama general esta en 0x40d8aa y termina en el
# hid_write de 0x40d9c5. Traducida:
#
#     ecx = N                             ; largo del payload que mando la pagina
#     buffer[0] = 0x04                    ; mov BYTE PTR [ebp-0x210],0x4
#     buffer[1] = N + 5                   ; lea eax,[ecx+0x5]
#     buffer[2] = 0x00                    ; mov BYTE PTR [ebp-0x20e],0x0
#     memcpy(&buffer[3], mensaje, N)      ; call 0x591af0
#     suma buffer[0 .. N+3)               ; esi = ecx+3
#     buffer[N+3] = chkHi                 ; mov [ebp+ecx-0x20d],al
#     buffer[N+4] = chkLo                 ; mov [ebp+ecx-0x20c],al
#     hid_write(dev, buffer, 0x41); Sleep(500)
#
# O sea **la misma regla que las lecturas**: el byte 1 es el largo total L, el
# checksum son los dos ultimos bytes de esos L y cubre todo lo anterior,
# incluido el Report ID. Con L = N+5 = 3 de cabecera + N de datos + 2 de
# checksum, todo cierra.
#
# El largo 0x41 que se le pasa a hid_write NO es el de la trama: hidapi en
# Windows ajusta el buffer al tamano del report. El descriptor del dongle
# declara 63 bytes de datos, asi que el report son 64 (1 de Report ID + 63) y
# el byte 65 sobra. En Linux se escribe el report de 64.
WRITE_FRAME_OVERHEAD = 5   # [reportId, largo, opcode] + [chkHi, chkLo]
WRITE_REPORT_LEN = 64      # 1 de Report ID + los 63 que declara el descriptor


def build_write_frame(bloque) -> bytes:
    """Arma una trama de escritura alrededor de un bloque `[cmd, N, ...datos]`.

    `bloque` es lo que el helper copia del mensaje de la pagina: arranca en el
    `cmd` y mide N bytes, donde N es su propio segundo byte (ver la nota sobre
    el campo de largo, mas arriba). El helper lo copia con
    `memcpy(&buffer[3], mensaje+2, mensaje[3])` en 0x40cf8d, y de ahi sale
    tambien el `buffer[1] = N + 5` de 0x40d8bf.

    OJO: esto arma la trama y nada mas. **No decide si se puede mandar.**
    Desde si hay un camino al mouse -`Mode.FULL` en el backend,
    y `driver/scripts/primera-escritura.py` para la Etapa 3- pero quien decide son las
    barandas del backend: allowlist `WRITABLE`, `--permitir-escritura` nombrando
    cada comando, simulacro por defecto, bateria >= 50% y confirmacion por
    terminal en la primera escritura de cada sesion. Ver dev/models/attackshark-x8pro/docs/protocolo.md y
    dev/docs/metodo.md.
    """
    bloque = bytes(bloque)
    # **Doble empaquetado: pasarle una trama ya armada en vez del bloque.**
    # Costó una tarde entera. `driver/scripts/cambiar-rate.py` armaba la
    # trama para mostrarla y despues se la pasaba a `device.escribir()`, que
    # vuelve a llamar aca; el resultado era
    #
    #     04 13 00 04 0e 00 06 09 01 44 bb 00 00 00 00 01 21 01 5a
    #           ^^ ^^ el mouse leia cmd 0x04 (dpi), sizeTotalData 14
    #
    # o sea un bloque de dpi con un tamaño imposible, que el firmware descarta
    # en silencio. Y el **dongle acusaba `0xC1` igual**, porque la trama es
    # sintacticamente valida: veinte escrituras "exitosas" sin un solo byte
    # cambiado, y tres hipotesis inventadas para explicarlo.
    #
    # La comprobacion de abajo no lo agarra: una trama de 14 bytes declara
    # `bloque[1] = 0x0e = 14` y mide 14, asi que coincide por casualidad.
    if (len(bloque) >= 5 and bloque[0] == DEVICE_REPORT_ID
            and bloque[2] == WRITE_OPCODE and bloque[3] in CMD_NAMES):
        raise ValueError(
            f"esto ya es una trama armada ({bloque[:5].hex(' ')}...), no un "
            f"bloque. `build_write_frame()` y `device.escribir()` esperan "
            f"[cmd, sizeTotalData, ...datos]: el Report ID, el largo, el "
            f"opcode y el checksum los pone esta funcion. Empaquetarla dos "
            f"veces le manda al mouse cmd {bloque[3]:#04x} con un tamaño que "
            "no le corresponde, y el dongle lo acusa igual"
        )
    if len(bloque) > 1 and bloque[1] != len(bloque):
        raise ValueError(
            f"el bloque dice N={bloque[1]} pero mide {len(bloque)} bytes. "
            "En todas las tramas observadas ese byte es el largo del propio "
            "bloque; si de verdad hay que mandarlo distinto, revisar primero "
            "dev/models/attackshark-x8pro/docs/protocolo.md"
        )
    length = len(bloque) + WRITE_FRAME_OVERHEAD
    if length > WRITE_REPORT_LEN:
        raise ValueError(
            f"bloque de {len(bloque)} B: la trama daria {length} B y el "
            f"report son {WRITE_REPORT_LEN}. Los comandos que no entran van "
            "por bloques (ver build_write_blocks)"
        )
    frame = bytearray([DEVICE_REPORT_ID, length, WRITE_OPCODE]) + bloque
    hi, lo = checksum(frame)
    frame.append(hi)
    frame.append(lo)
    return bytes(frame)


# El otro camino, para los comandos que no entran en un report: el trio de
# 0x40d612 (macros, cmd 9) parte los datos en bloques de 0x3b = 59 bytes y
# manda dos, con Sleep(200) entre uno y otro y Sleep(1000) al final. Ahi el
# byte 2 deja de ser el opcode y pasa a ser el **numero de bloque** (0-based:
# se ve en `imul eax,edx,0x3b`, que lo usa para indexar el origen), y el largo
# del ultimo bloque baja a 0x39 = 57.
#
# **MEDIDO contra el bus.** Esto venia del desensamblado y nunca
# se habia visto correr: no habia una sola trama de cmd 9 en las diez capturas.
# `dev/models/attackshark-x8pro/docs/capturas-w/soft-macro-asignado.pcap` trae cuatro, y las cuatro salen
# **identicas** de `build_write_blocks()` -las dos tramas de cada una, con sus
# dos checksums-. El bloque logico mide 111 bytes, se parte en 59 + 52, y los
# largos son los que dice el desensamblado: 0x40 la primera y 0x39 la segunda.
#
# Y el dongle lo trata como **una** escritura: acusa `0xC0` despues de cada
# trama pero el `0xC1` -el que dice que el mouse aplico- llega recien despues
# de la segunda. Se ve en los cuatro casos de esa captura.
#
# Lo que NO coincide son las pausas. `WRITE_BLOCK_PAUSE = 0.2` sale del
# `Sleep(200)` del helper, pero el soft nativo espera **1.008 s** entre los dos
# trozos, que es el mismo intervalo con el que manda todas sus escrituras. O
# sea que los 200 ms son del helper de la web, no de este camino, y no hay
# medida de cual es el minimo: nadie fue mas rapido que un segundo.
WRITE_BLOCK_DATA = 0x3B    # 59 bytes de datos por bloque
WRITE_BLOCK_PAUSE = 0.2    # push 0xc8 ; call Sleep
WRITE_BLOCK_FINAL_PAUSE = 1.0   # push 0x3e8 ; call Sleep

# Y la que usa el proyecto para mandar macros, que **no** es la del helper: es
# la del soft nativo, MEDIDA en `soft-macro-asignado.pcap` entre los dos trozos
# de las cuatro escrituras. La regla es no mandarle al mouse una secuencia que
# un driver oficial no le haya mandado antes, y la unica que se vio correr en
# este camino es esta. Ir mas rapido que 0.2 s no esta medido y aca no se
# averigua: entre trozo y trozo el mouse tiene medio bloque.
WRITE_BLOCK_PAUSE_SOFT = 1.008


def build_write_blocks(datos) -> list[bytes]:
    """Parte un payload largo en las tramas por bloques del camino de macros.

    Transcripcion del trio que arranca en 0x40d612. Mismo aviso que arriba:
    esto arma tramas, no las manda.
    """
    datos = bytes(datos)
    bloques = []
    for indice in range(0, max(len(datos), 1), WRITE_BLOCK_DATA):
        trozo = datos[indice:indice + WRITE_BLOCK_DATA]
        length = len(trozo) + WRITE_FRAME_OVERHEAD
        frame = bytearray([DEVICE_REPORT_ID, length,
                           indice // WRITE_BLOCK_DATA]) + trozo
        hi, lo = checksum(frame)
        frame.append(hi)
        frame.append(lo)
        bloques.append(bytes(frame))
    return bloques


def verify_frame(frame) -> bool:
    """True si el checksum de una trama recibida cuadra."""
    if len(frame) < 3:
        return False
    hi, lo = checksum(frame[:-2])
    return frame[-2] == hi and frame[-1] == lo


# --- el canal por CABLE -----------------------------------------------------
# Por cable el mouse es otro dispositivo USB (`1d57:2126`) y su canal de
# configuracion son Feature Reports en la Usage Page 0x0B, no el Output Report
# 4 del dongle. **Salio LEIDO del helper** (`WebDriver.exe`, sha256
# `0eea3fef…`) y **quedo MEDIDO en el bus con otro programa**: seis capturas
# del soft nativo configurando por cable (`dev/models/attackshark-x8pro/docs/capturas-w/cable-soft-*.pcap`),
# con la Etapa 2 cumplida en lo que capturaron -ver mas abajo, y
# `test_etapa2_cable`-. Lo que el helper pone en el cable sigue sin verse.
# Quien los usa es `cable.CableDevice`, el unico que le habla al cable
# (`test_el_cable_solo_pasa_por_su_canal`). La Etapa 3 por cable la corre el
# usuario desde la ventana, como siempre.
#
# El helper trata al cable del X8 Pro como `connectionMethod` 0x80: la
# enumeracion de 0x4115a8 junta todo lo de 1d57 que no sea un dongle (fa60,
# fa65) y tenga una coleccion en la Usage Page 0x0B (configuracion) o 0x0A
# (notificaciones), que es justo lo que declara la interfaz 2 del cable. Y la
# pagina lo acepta por ahi: `setWiredDevice` incluye `8: "X8Pro"`.
#
# LEER, en 0x40e380 y sus ocho llamadores:
#
#     SET_FEATURE  [a0, cmd, sub, 00, perfil, 00, 00, 00]  ; hasta 10 veces
#     Sleep(500)                                            ; hasta que no falle
#     GET_FEATURE  [a0, ...] (8 B)   -> byte 1 == 1: listo  ; tras Sleep(100)
#     GET_FEATURE  [cmd, ...] (sub B)                       ; el bloque
#
# y lo que vuelve se le pasa a la pagina como `%02x%02x` (conn, dev) seguido del
# buffer tal cual (0x412730): o sea que el report es `[cmd, sizeTotalData,
# perfil, campos..., checksum interno]`, **el mismo bloque que viaja adentro de
# la trama del dongle**, sin el `04 L 00` de afuera ni su checksum. Los `sub`
# son los de `READ_SUB` salvo el macro, que por cable pide 0x83 (131).
#
# ESCRIBIR, en la rama 0x80 de 0x40cf10:
#
#     hid_send_feature_report(h, payload, payload[1]); Sleep(500)   ; 0x40d1f4
#
# con `payload` el mensaje de la pagina sin `[conn, dev]`: el mismo `bloque`
# que recibe `Device.escribir()`. El `cmd` hace de Report ID. El macro va
# aparte, en trozos de 64: `[09, 40, payload[2], trozo, 60 bytes]`.
#
# **Lo que dijo la captura** (MEDIDO, `cable-soft-*.pcap`):
#
# * cada `SET_REPORT` lleva **el largo que el mouse declara** -52 el dpi, 9 el
#   rate, 59 los botones, 64 cada trozo de macro-: es
#   `build_cable_write_report()` tal cual. Y lo que queda afuera
#   es el relleno del dongle, cero en los 120 bloques de dpi y 121 de luz de
#   los respaldos (`dev/tests/evidencia.py`);
# * cada `GET_REPORT` pide el largo del helper -56, 15, 9- y el mouse
#   **devuelve el bloque entero, con el relleno**, aunque declare menos;
# * el pedido `0xA0` es el de `build_cable_read_request()`, byte a byte, para
#   dpi, luz y rate, y el `GET(0xA0)` vuelve `a0 01`: listo. Sin el pedido, el
#   mouse no contesta el `GET` (`dev/models/attackshark-x8pro/respaldos/cable-primera-lectura.json`);
# * **el mouse a veces rechaza un `SET_REPORT` con STALL**, y el mismo `SET`
#   repetido entre 201 y 209 ms despues pasa: 6 de 19 pedidos, los seis
#   reintentados identicos y los seis aceptados. Cuatro fueron la primera
#   escritura de una captura -no en todas- y dos, pedidos de lectura justo
#   despues de otra lectura. Quien reintenta -el soft, Windows o QEMU- no se
#   sabe; lo medido es que repetirlo es lo que pasa en el bus y que funciona.
#
# Lo que el soft **no** leyo por cable, y por eso sigue solo LEIDO del helper:
# botones, macro, perfil completo, version y 0x0c. Al abrirse, el soft lee
# solo rate, dpi y luz. Version, botones y perfil completo ya se leyeron por
# cable con estos pedidos (MEDIDO, `dev/models/attackshark-x8pro/respaldos/cable-primer-respaldo.json`).
CABLE_READ_REPORT_ID = 0xA0
CABLE_READ_REQUEST_LEN = 8
CABLE_READ_READY = 0x01          # byte 1 del GET_FEATURE(0xA0) cuando esta listo

# Los `sub` del pedido de lectura por cable, llamador por llamador. Son los del
# dongle salvo el macro, que por cable pide 0x83 (131) y lleva su id en el
# byte 4 (ver `build_cable_read_request`).
CABLE_READ_SUB = {
    CMD_DPI: 0x38,           # 0x4137a0
    CMD_LIGHTING: 0x0F,      # 0x413282
    CMD_REPORT_RATE: 0x09,   # 0x412ca0
    CMD_BUTTONS: 0x3B,       # 0x413cc0
    CMD_MACRO: 0x83,         # 0x40fbce
    CMD_PROFILE: 0x80,       # 0x40f614
    CMD_VERSION: 0x08,       # 0x40ef2d
    0x0C: 0x0A,              # 0x40e8df
}


def build_cable_read_request(cmd: int, profile: int = 1,
                             macro_id: int | None = None) -> bytes:
    """El `SET_FEATURE(0xA0)` con el que el helper pide un bloque por cable.

    Transcripcion de 0x40e380: `[a0, cmd, sub, 00, perfil, 00, 00, 00]`. Es el
    mismo pedido que la trama de lectura del dongle, con otro envoltorio y **un
    cero de mas entre el sub y el perfil**. El perfil va 1-based, como en el
    dongle (`inc eax` en cada llamador), y version y 0x0c llevan un 0 literal.

    **El macro lleva su id en el byte 4**, donde los demas llevan el perfil
    (LEIDO, 2026-09-18). El llamador de 0x40fbcb pasa `[ebx+0x8]` sin el `+1`,
    y la misma funcion, por el camino del dongle (0x40f81c), pone esa misma
    variable en el byte 5 de la trama `04 0c a0 09 6f ..` -donde va el
    perfil-, que es exactamente donde el id del macro hace que el mouse
    devuelva el bloque (MEDIDO por el dongle). O sea: el mismo id, en el mismo
    lugar relativo, por los dos caminos.
    """
    if cmd == CMD_MACRO:
        if macro_id is None:
            raise ComandoSinSub(
                "el macro se pide con su id, no con el perfil: sin macro_id no "
                "hay pedido")
        if not MACRO_ID_MIN <= macro_id <= MACRO_ID_MAX:
            raise ValueError(
                f"macro_id {macro_id} fuera de {MACRO_ID_MIN}..{MACRO_ID_MAX}")
        return bytes([CABLE_READ_REPORT_ID, CMD_MACRO, CABLE_READ_SUB[CMD_MACRO],
                      0, macro_id, 0, 0, 0])
    if macro_id is not None:
        raise ValueError(f"macro_id es solo para cmd {CMD_MACRO} (macro)")
    sub = CABLE_READ_SUB.get(cmd)
    if sub is None:
        raise ComandoSinSub(
            f"el helper no lee el comando 0x{cmd:02x} "
            f"({CMD_NAMES.get(cmd, 'sin nombre')}) por cable; no se inventa")
    pedido = bytearray(CABLE_READ_REQUEST_LEN)
    pedido[0] = CABLE_READ_REPORT_ID
    pedido[1] = cmd
    pedido[2] = sub
    if cmd in CMDS_CON_PERFIL:
        pedido[4] = profile
    return bytes(pedido)


def build_cable_write_report(bloque, largo: int) -> bytes:
    """El `SET_FEATURE` de una escritura por cable, **segun la hipotesis**.

    `bloque` es `[cmd, sizeTotalData, ...datos]`, lo mismo que recibe
    `Device.escribir()`, y `largo` el del report con su id, como lo declara el
    mouse en su descriptor. Devuelve el bloque cortado a ese largo, o
    completado con ceros si es mas corto: lo que el helper le pasa a hidapi,
    recortado a lo que el mouse dice recibir.

    **Se niega a cortar algo que no sea relleno**: si los bytes que quedan
    afuera no son todos cero, el bloque no entra en el report y cortarlo seria
    mandar otro bloque. El macro tampoco va por aca: por cable viaja en trozos.
    """
    bloque = bytes(bloque)
    if not bloque:
        raise ValueError("bloque vacio")
    # La misma trampa que en `build_write_frame()`, y aca peor: una trama del
    # dongle empieza con 0x04, que por cable es el Report ID del dpi, y su
    # byte 1 es su propio largo. `04 0e 00 06 09 ...` -una escritura de rate-
    # pasaria como un bloque de dpi de 14 bytes.
    if (len(bloque) >= 5 and bloque[0] == DEVICE_REPORT_ID
            and bloque[2] == WRITE_OPCODE and bloque[3] in CMD_NAMES):
        raise ValueError(
            f"esto es una trama del dongle ({bloque[:5].hex(' ')}...), no un "
            "bloque: por cable no lleva ni el Report ID 4, ni el largo, ni el "
            "opcode, ni el checksum de afuera")
    if bloque[0] == CMD_MACRO:
        raise ValueError(
            "el macro por cable va en trozos de 64 (0x40d005), no en un report")
    if len(bloque) < 2 or bloque[1] != len(bloque):
        raise ValueError(
            f"el byte de tamaño dice {bloque[1] if len(bloque) > 1 else None} "
            f"y el bloque mide {len(bloque)}")
    afuera = bloque[largo:]
    if any(afuera):
        raise ValueError(
            f"el report {bloque[0]} mide {largo} y el bloque trae datos despues: "
            f"{afuera.hex()}. Eso no es relleno, y cortarlo cambiaria el bloque")
    return bloque[:largo] + bytes(max(0, largo - len(bloque)))


# El macro por cable, en trozos de 64: `[09, 40, id, trozo, 60 bytes]`. LEIDO
# en 0x40d005 -dos trozos si `sizeTotalData` es 0x6f- y MEDIDO en
# `cable-soft-macros.pcap`: los trozos rearmados son, byte a byte, el bloque de
# 111 que ya se escribe por el dongle, y detras viajan 12 ceros de relleno.
CABLE_MACRO_REPORT_LEN = 0x40
CABLE_MACRO_DATOS_POR_TROZO = 60


def build_cable_macro_reports(bloque) -> list[bytes]:
    """Los dos `SET_FEATURE(9)` con los que viaja un macro por cable.

    `bloque` es el de `escribir_por_bloques()`: `[09, 6f, id, ...108 bytes]`.
    Del byte 3 en adelante se parte en trozos de 60, cada uno con la cabecera
    `[09, 40, id, trozo]`, y el ultimo se completa con ceros.

    Solo el bloque de 111 (0x6f), que es el del X8 Pro: con otro tamaño el
    helper manda tres trozos y el tercero con otra cabecera (0x40d1e1), y eso
    no se vio en el bus.
    """
    bloque = bytes(bloque)
    if len(bloque) < 3 or bloque[0] != CMD_MACRO:
        raise ValueError("no es un bloque de macro: [09, 6f, id, ...]")
    if bloque[1] != 0x6F or len(bloque) != 0x6F:
        raise ValueError(
            f"el macro por cable esta medido con el bloque de 111 (0x6f); este "
            f"dice {bloque[1]} y mide {len(bloque)}")
    datos = bloque[3:]
    trozos = []
    for i in range(0, len(datos), CABLE_MACRO_DATOS_POR_TROZO):
        trozo = datos[i:i + CABLE_MACRO_DATOS_POR_TROZO]
        trozo += bytes(CABLE_MACRO_DATOS_POR_TROZO - len(trozo))
        trozos.append(bytes([CMD_MACRO, CABLE_MACRO_REPORT_LEN, bloque[2],
                             i // CABLE_MACRO_DATOS_POR_TROZO]) + trozo)
    return trozos
