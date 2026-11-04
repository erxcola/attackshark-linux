# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Leer y comparar el estado entero del mouse, sin imprimir ni hablar HTTP.

Es la capa que usa la **aplicacion**: una capa de sesion que no sea el
WebSocket (bitacora, "La primera capa de la aplicacion, sacada de un script").
`server.py` existe para hablarle a la pagina oficial y arrastra todo lo que eso
implica -el filtro de `Origin`, el formato de mensajes de szslxd-tech.com-; la
aplicacion no necesita nada de eso: le habla a `device.py` directo.

Antes esto vivia adentro de `driver/scripts/respaldar.py`, y
`driver/scripts/primera-escritura.py` lo usaba **importando otro script**. Funcionaba,
pero deja la logica en la herramienta en vez de en la biblioteca, que es
exactamente lo que la aplicacion no puede heredar.

Que hay aca, en el orden de la Etapa 3:

  * **leer el estado entero** (`leer_estado`), con los reintentos que el enlace
    obliga y el bloque de rate de semaforo;
  * **la tasa** (`tasa_actual`, `poner_tasa`): arriba de 1000 Hz el respaldo
    completo no sale, asi que configurar empieza por bajar;
  * **escribir un bloque** (`escribir_bloque`), eligiendo una trama o varias
    segun el tamaño;
  * **y juzgar como salio** (`juzgar`), que es el criterio del paso 6 y la red
    de toda la Etapa 3.

Lo que **no** hace, a proposito:

  * **no imprime.** Leer el mouse tarda minutos y quien lo corre necesita ver
    avanzar la lista, asi que avisa por callbacks y el formato lo elige quien
    llama: la terminal en `respaldar.py`, una vista en la aplicacion.
  * **no decide si algo se puede escribir.** La allowlist, el simulacro, la
    confirmacion por terminal y el respaldo previo obligatorio son barandas de
    quien llama: `driver/scripts/primera-escritura.py` y la aplicacion.
    Esta capa sabe **como** se hace, no **si** corresponde.

El formato del estado es **el mismo JSON que los respaldos versionados**, y
tiene que seguir siendolo: `respaldar.py --comparar` compara un respaldo de
hoy contra uno, y esa comparacion es la red de toda escritura.
"""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable

from . import dispositivos
from . import estructuras
from . import protocol as p

# Todo lo que sabemos pedir, en orden. El perfil completo va ultimo porque es
# el mas largo y el que mas veces hay que reintentar.
A_LEER = [
    p.CMD_VERSION,
    p.CMD_REPORT_RATE,
    p.CMD_LIGHTING,
    p.CMD_DPI,
    p.CMD_BUTTONS,
    p.CMD_MACRO,
    p.CMD_PROFILE,
]

# Cuando un comando se rinde, el dongle suele seguir con ese pedido en vuelo:
# encimarle el siguiente lo mantiene ocupado, y el fallo se contagia hacia
# abajo en la lista. El peor caso MEDIDO para que se libere es 2.10 s (ver
# device.py), asi que se le da ese respiro antes de seguir.
RESPIRO_TRAS_FALLO = 3.0

# Y al final se reintenta lo que falto, una vez. No es aflojar nada: el estado
# sigue estando incompleto si algo no contesta, y quien exige los siete
# comandos es primera-escritura.py. Es solo darle al enlace la segunda chance
# que el 50% de perdida con el mouse quieto hace obligatoria.
PASADAS = 2

# **Cuantos fallos seguidos hacen falta para abandonar la tanda.** Arriba de
# 1000 Hz el canal de configuracion no da los bloques largos, y antes el
# respaldo se los peleaba igual: cinco "ocupado" con backoff por
# comando, mas el respiro de 3 s entre uno y otro, por dos pasadas. Con tres
# comandos caidos eso es un minuto largo de terminal trabada para un resultado
# que ya se sabe.
#
# A 1000 Hz un fallo es intermitente -95% de exito con el mouse en
# movimiento-, asi que tres seguidos no es mala suerte: es el canal tomado.
CORTE_TRAS_FALLOS = 3

# Y arriba de esta tasa, el respaldo completo **no sale** (MEDIDO a 2000 y a
# 8000 Hz). El bloque de rate son 7 bytes y contesta siempre, asi que se lo usa
# como semaforo: si el mouse esta rapido, no se insiste con una segunda pasada
# que va a fallar igual.
RATE_MAXIMO_PARA_LEER = 1000

# El codigo de la funcion "macro" de un boton vive en estructuras, que es donde
# esta la tabla; tenerlo dos veces es tenerlo mal una vez.
FUNCION_MACRO = estructuras.FUNCION_MACRO


@dataclass(frozen=True)
class Lectura:
    """Un comando que contesto -o que no-, para que quien llama lo muestre.

    `entrada` es None cuando no hubo respuesta, y `reintentable` dice si
    todavia queda una pasada: no es lo mismo "sin respuesta, lo reintento al
    final" que "SIN RESPUESTA" y se acabo.
    """

    cmd: int
    nombre: str
    entrada: dict | None
    reintentable: bool = False
    macro_id: int | None = None


AlLeer = Callable[[Lectura], None]
AlReintentar = Callable[[list[int], float], None]
AlCortar = Callable[[list[int], str], None]


def _entrada(cmd: int, frame) -> dict:
    """Un comando leido, en el formato del respaldo."""
    entrada = {
        "nombre": p.CMD_NAMES.get(cmd, f"cmd {cmd}"),
        "sizeTotalData": frame.sub,
        "datos": frame.data.hex(),
        "checksum_ok": frame.checksum_ok,
    }
    campos = estructuras.decodificar(cmd, frame.data)
    if campos is not None:
        entrada["campos"] = {
            k: (v.hex() if isinstance(v, bytes) else v)
            for k, v in campos.items()
        }
        entrada["legible"] = estructuras.describir(cmd, frame.data)
    return entrada


async def _leer_tanda(cmds, device, estado, *, ultima: bool,
                      al_leer: AlLeer | None,
                      al_cortar: AlCortar | None = None) -> list[int]:
    """Lee una tanda de comandos. Devuelve los que no contestaron.

    Abandona la tanda tras `CORTE_TRAS_FALLOS` fallos seguidos: a esa altura
    el canal esta tomado y seguir pidiendo solo gasta minutos de terminal.
    """
    faltan = []
    seguidos = 0
    for i, cmd in enumerate(cmds):
        nombre = p.CMD_NAMES.get(cmd, f"cmd {cmd}")
        frame = await device.leer(cmd)
        if frame is None:
            if al_leer:
                al_leer(Lectura(cmd, nombre, None, reintentable=not ultima))
            faltan.append(cmd)
            seguidos += 1
            if seguidos >= CORTE_TRAS_FALLOS and i + 1 < len(cmds):
                restantes = list(cmds[i + 1:])
                faltan += restantes
                if al_cortar:
                    al_cortar(restantes, f"{seguidos} seguidos sin respuesta")
                break
            if i + 1 < len(cmds):
                await asyncio.sleep(RESPIRO_TRAS_FALLO)
            continue
        seguidos = 0
        entrada = _entrada(cmd, frame)
        estado["comandos"][str(cmd)] = entrada
        if al_leer:
            al_leer(Lectura(cmd, nombre, entrada))
    return faltan


# --- los macros no se leen con el perfil, se leen con el id ----------------
#
# El pedido de cmd 9 de `A_LEER` lleva el perfil en el byte 5, como todos los
# demas, y por eso siempre devuelve el bloque vacio: `01` y 108 bytes de
# `0xff`. MEDIDO: con el id del macro en ese byte el mouse
# devuelve el bloque entero.
#
# Un estado que no trae los macros no es una red: si se escribe cmd 9 y sale
# mal, no hay a donde volver. Asi que despues de la tanda normal se leen
# tambien, y los ids salen de donde el mouse mismo los dice: los slots de cmd 8
# con funcion "macro" los llevan en `p2`.
#
# Va **aparte de `comandos`** para no tocar la cuenta de "7 de 7", que es la
# señal de salud que usa `primera-escritura.py`. Un macro que no contesta no
# invalida el estado de los siete bloques; que falte se ve igual, en su propia
# linea.
async def _leer_macros(device, estado, *, extra=(),
                       al_leer: AlLeer | None) -> None:
    ids = set(extra)
    bloque = estado["comandos"].get(str(p.CMD_BUTTONS))
    if bloque is not None:
        bots = estructuras.botones_de(bytes.fromhex(bloque["datos"]))
        if bots is not None:
            ids |= {b["p2"] for b in bots if b["codigo"] == FUNCION_MACRO}
    ids = sorted(ids)
    if not ids:
        return
    estado["macros"] = {}
    for mid in ids:
        nombre = f"macro {mid}"
        frame = await device.leer(p.CMD_MACRO, macro_id=mid)
        if frame is None:
            estado["macros"][str(mid)] = None
            if al_leer:
                al_leer(Lectura(p.CMD_MACRO, nombre, None, macro_id=mid))
            continue
        entrada = {
            "datos": frame.data.hex(),
            "checksum_ok": frame.checksum_ok,
            "legible": estructuras.describir(p.CMD_MACRO, frame.data),
        }
        estado["macros"][str(mid)] = entrada
        if al_leer:
            al_leer(Lectura(p.CMD_MACRO, nombre, entrada, macro_id=mid))


# --- el camino: dongle o cable ---------------------------------------------
#
# La sesion no sabe por donde habla, y casi nunca le hace falta: el cable tiene
# los mismos `leer` y `escribir` que el dongle (`cable.CableDevice`). Las tres
# cosas que si cambian las dice el device, y se preguntan aca y en ningun otro
# lado:
#
#   * **que se lee para un respaldo** (`a_leer`): por cable no va el pedido
#     del macro con el perfil -por el dongle devuelve un bloque vacio-; el
#     macro se pide con su id, aparte;
#   * **si el macro se lee** (`lee_macros`): por los dos caminos si. Un camino
#     que no pudiera leerlo no lo escribiria: lo que no se relee no se
#     escribe;
#   * **cual es la tasa**: el mismo byte, **otro nibble**. Por el dongle la
#     tasa es el alto; por cable, el bajo (MEDIDO en `cable-soft-rate-*.pcap`).
#     Mirar el alto por cable daria 8000 Hz, y la sesion "bajaria la tasa"
#     escribiendo la de la radio.

def via_de(device) -> str:
    """Por donde habla el device. Sin decirlo, es el dongle de siempre."""
    return getattr(device, "via", dispositivos.VIA_DONGLE)


def a_leer_de(device) -> list[int]:
    """Los comandos del respaldo por ese camino."""
    return list(getattr(device, "a_leer", A_LEER))


def lee_macros(device) -> bool:
    return bool(getattr(device, "lee_macros", True))


def _tasa_del_camino(device):
    """`(leer_hz, escribir)` del nibble de la tasa que corresponde."""
    if via_de(device) == dispositivos.VIA_CABLE:
        return (estructuras.report_rate_por_cable_de,
                estructuras.escribir_report_rate_por_cable)
    return estructuras.report_rate_de, estructuras.escribir_report_rate


def tasa_de(estado: dict, via: str | None = None) -> int | None:
    """Los Hz que declara el bloque de rate del estado, si lo trajo.

    El nibble es el del camino: el que se pase, o el que dice el estado.
    """
    if via is None:
        via = estado.get("via")
    bloque = estado["comandos"].get(str(p.CMD_REPORT_RATE))
    if bloque is None:
        return None
    datos = bytes.fromhex(bloque["datos"])
    if via == dispositivos.VIA_CABLE:
        return estructuras.report_rate_por_cable_de(datos)
    return estructuras.report_rate_de(datos)


def aviso_de_tasa_arreglada(byte: int) -> str:
    """Lo que se dice cuando la tasa no se entendia y se la dejo en 1000 Hz.

    **Dice que queda ahi**: a diferencia de la tasa prestada, esta no vuelve,
    porque no hay una anterior que devolver.
    """
    return (f"el mouse tenia la tasa en un byte que no es ninguno de los siete "
            f"conocidos ({byte:#04x}), asi que no se sabia a cuanto estaba. La "
            f"puse en {RATE_MAXIMO_PARA_LEER} Hz para poder leerlo, y ahi "
            "queda: no hay una tasa anterior que devolver")


def aviso_de_tasa_alta(hz: int, faltan: list[int]) -> str:
    """Lo que se dice cuando el mouse esta demasiado rapido para leerlo."""
    nombres = ", ".join(p.CMD_NAMES.get(c, f"cmd {c}") for c in faltan)
    return (f"\n  el mouse esta a {hz} Hz, y arriba de {RATE_MAXIMO_PARA_LEER} "
            "Hz los bloques largos no llegan\n"
            f"  (MEDIDO a 2000 y a 8000). No insisto: falta {nombres}.\n"
            "  Para poder leerlo entero, bajá la tasa:\n"
            "    driver/scripts/cambiar-rate.py --valor 1000")


async def leer_estado(device, *, nodo: str = "", pasadas: int = PASADAS,
                      macros_extra=(), al_leer: AlLeer | None = None,
                      al_reintentar: AlReintentar | None = None,
                      al_cortar: AlCortar | None = None) -> dict:
    """El estado entero: los siete bloques mas los macros que el mouse apunta.

    `macros_extra` son ids que se leen **ademas** de los que salen de los slots
    de cmd 8. Hace falta porque un macro puede existir en el mouse sin que
    ningun boton lo apunte -entre escribirlo y asignarlo a un boton- y en
    ese caso no hay de donde deducir su id: un estado previo a escribirlo
    tiene que traerlo igual, o no es una red.
    """
    a_leer = a_leer_de(device)
    estado = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "nodo": nodo,
        # En el orden de A_LEER y no en el que vayan contestando, para que dos
        # estados se puedan mirar en paralelo aunque uno haya necesitado
        # segunda pasada.
        "comandos": {str(cmd): None for cmd in a_leer},
    }
    if via_de(device) != dispositivos.VIA_DONGLE:
        # El estado dice por donde se leyo: por cable la tasa es otro nibble
        # (`tasa_de`, `modelo.campos_de`) y no trae el pedido del macro con el
        # perfil, que `--comparar` contra uno del dongle tomaria por faltante.
        estado["via"] = via_de(device)
    faltan = list(a_leer)
    for pasada in range(1, pasadas + 1):
        if pasada > 1:
            if al_reintentar:
                al_reintentar(list(faltan), RESPIRO_TRAS_FALLO)
            await asyncio.sleep(RESPIRO_TRAS_FALLO)
        faltan = await _leer_tanda(faltan, device, estado,
                                   ultima=(pasada == pasadas), al_leer=al_leer,
                                   al_cortar=al_cortar)
        if not faltan:
            break
        # **El bloque de rate es el semaforo.** Son 7 bytes y contesta a
        # cualquier tasa, asi que si dice que el mouse esta rapido ya se sabe
        # como termina la segunda pasada: igual. Se corta y se dice que hacer,
        # en vez de pelearla un minuto.
        hz = tasa_de(estado, via_de(device))
        if hz is not None and hz > RATE_MAXIMO_PARA_LEER:
            if al_cortar:
                al_cortar(list(faltan), aviso_de_tasa_alta(hz, faltan))
            break
    if lee_macros(device):
        await _leer_macros(device, estado, extra=macros_extra, al_leer=al_leer)
    return estado


# El formato de la linea que se ve mientras el mouse contesta. Vive aca -y no
# en los scripts- porque `respaldar.py` y `primera-escritura.py` la imprimen
# identica, y una salida que se lee mientras corre una escritura no puede
# depender de cual de los dos la escribio. Es formato, no impresion: devuelve
# texto y quien llama decide que hacer con el.
def linea_de(lectura: Lectura) -> str:
    """Una linea por comando leido, como la muestra la terminal."""
    # El macro lleva su id pegado al nombre y por eso pide otro ancho; el
    # resto entra en la columna de siempre.
    if lectura.macro_id is not None:
        etiqueta = f"macro {lectura.macro_id:<17}"
    else:
        etiqueta = f"{lectura.nombre:22}"
    if lectura.entrada is None:
        marca = ("sin respuesta (lo reintento al final)"
                 if lectura.reintentable else "SIN RESPUESTA")
        return f"  {etiqueta} {marca}"
    legible = lectura.entrada.get("legible")
    largo = len(lectura.entrada["datos"]) // 2
    return f"  {etiqueta} {largo:3d} B{'  ' + legible if legible else ''}"


def aviso_de_reintento(faltan: list[int], espera: float,
                       via: str | None = None) -> str:
    """Lo que se dice antes de la segunda pasada. Por el dongle, moverlo."""
    if via == dispositivos.VIA_CABLE:
        return (f"\n  reintento de {len(faltan)} comando(s) que no "
                f"contestaron, en {espera:.0f} s.")
    return (f"\n  reintento de {len(faltan)} comando(s) que no contestaron. "
            f"Espero {espera:.0f} s a que el dongle se despeje; mové el mouse.")


def incompletos(estado: dict) -> list[int]:
    """Los comandos que no contestaron. Vacio = los siete estan."""
    return [int(k) for k, v in estado["comandos"].items() if v is None]


def incoherencias(estado: dict) -> list[str]:
    """Donde un estado se contradice a si mismo. Vacio = todo concuerda.

    El perfil completo embebe a rate, dpi, luz y botones, asi que un estado
    trae **dos copias** de esos bytes y tienen que coincidir. Cuando no
    coinciden, una de las dos lecturas vino mal.

    **Es lo unico que cubre a cmd 10**, que no tiene checksum interno y sin
    embargo es el testigo de toda escritura por el camino de la relectura
    acotada: si el perfil viene sangrado, el veredicto se arma sobre bytes de
    otro bloque.

    Se mira sobre un estado ya leido -no cuesta una sola lectura de mas- y se
    exige en los mismos dos puntos que `incompletos()`: el respaldo previo y la
    relectura del paso 6.
    """
    datos = {}
    for k, v in estado["comandos"].items():
        if isinstance(v, dict) and v.get("datos"):
            datos[int(k)] = bytes.fromhex(v["datos"])
    perfil = datos.get(p.CMD_PROFILE)
    if perfil is None:
        return []
    malas = []
    for cmd, bloque in sorted(datos.items()):
        if cmd == p.CMD_PROFILE:
            continue
        dice = estructuras.perfil_discrepa(cmd, perfil, bloque)
        if dice is not None:
            malas.append(f"{p.CMD_NAMES.get(cmd, cmd)}: {dice}")
    return malas


# --- comparar dos estados --------------------------------------------------
#
# El paso 6 de la Etapa 3 es esto: releer todo y mirar que se movio **solo** lo
# que se pidio. Es la red, asi que lo que se imprima aca tiene que poder
# creerse: una linea de mas gasta una alarma, y este proyecto no tiene otras.

def cmds_que_cambiaron(a: dict, b: dict) -> set[int]:
    """Los comandos cuyos bytes difieren entre dos estados.

    `diferencias()` devuelve texto para mostrar; esto devuelve los comandos,
    que es lo que hace falta para decidir si una escritura salio bien. Un
    comando que no contesto en alguno de los dos no cuenta como cambiado: no
    se sabe.
    """
    cambiados = set()
    for k, ea in a["comandos"].items():
        eb = b["comandos"].get(k)
        if ea is None or eb is None:
            continue
        if ea["datos"] != eb["datos"]:
            cambiados.add(int(k))
    # Un macro que cambia es un cambio en cmd 9, aunque viva en otra seccion.
    for k in set(a.get("macros", {})) | set(b.get("macros", {})):
        ea, eb = a.get("macros", {}).get(k), b.get("macros", {}).get(k)
        if ea is None or eb is None:
            continue
        if ea["datos"] != eb["datos"]:
            cambiados.add(p.CMD_MACRO)
    return cambiados


def diferencias(a: dict, b: dict) -> list[str]:
    """Diferencias entre dos estados, campo por campo."""
    difs = []
    claves = sorted(set(a["comandos"]) | set(b["comandos"]), key=int)
    for k in claves:
        ea, eb = a["comandos"].get(k), b["comandos"].get(k)
        nombre = (ea or eb or {}).get("nombre", f"cmd {k}") if (ea or eb) else f"cmd {k}"
        if ea is None or eb is None:
            if ea != eb:
                difs.append(f"{nombre}: uno de los dos no contesto "
                            f"({'A' if ea is None else 'B'})")
            continue
        if ea["datos"] == eb["datos"]:
            continue
        ca, cb = ea.get("campos", {}), eb.get("campos", {})
        if ca and cb:
            # **La union, no solo las claves de `a`.** Un campo que aparezca
            # unicamente del lado nuevo -otra version de firmware, un
            # decodificador que aprendio a partir un byte- no se veria nunca
            # si se recorre un solo diccionario.
            for campo in sorted(set(ca) | set(cb)):
                if ca.get(campo) != cb.get(campo):
                    difs.append(f"{nombre}.{campo}: {ca.get(campo)!r} -> "
                                f"{cb.get(campo)!r}")
        else:
            difs.append(f"{nombre}: {ea['datos']} -> {eb['datos']}")
    for k in sorted(set(a.get("macros", {})) | set(b.get("macros", {})), key=int):
        ma, mb = a.get("macros", {}).get(k), b.get("macros", {}).get(k)
        if ma is None or mb is None:
            if ma != mb:
                difs.append(f"macro {k}: uno de los dos no contesto "
                            f"({'A' if ma is None else 'B'})")
            continue
        if ma["datos"] != mb["datos"]:
            difs.append(f"macro {k}: {ma['datos']} -> {mb['datos']}")
    return difs


# --- el camino de escritura -------------------------------------------------

def trama_de(device, bloque: bytes) -> bytes:
    """Lo que sale por el cable para ese bloque, para mostrarlo y anotarlo.

    Por el dongle son una o dos tramas de Output Report; por cable, el Feature
    Report que arma el propio device con el largo de su descriptor.
    """
    propia = getattr(device, "trama_de", None)
    if propia is not None:
        return propia(bloque)
    if len(bloque) + p.WRITE_FRAME_OVERHEAD > p.WRITE_REPORT_LEN:
        return b"".join(p.build_write_blocks(bloque))
    return p.build_write_frame(bloque)


async def escribir_bloque(device, bloque: bytes) -> bool:
    """Le manda un bloque al mouse eligiendo el camino que corresponde.

    `bloque` es `[cmd, sizeTotalData, ...datos]`, lo mismo que espera
    `device.escribir()`. **No hay que pasarle una trama armada**: eso lo
    rechaza `protocol.build_write_frame()`, y por buenos
    motivos.

    El criterio no es "si es cmd 9" sino si el bloque entra en un report: hoy
    da lo mismo porque el unico que no entra es el macro, pero la regla es del
    tamaño, no del comando.
    """
    if len(bloque) + p.WRITE_FRAME_OVERHEAD > p.WRITE_REPORT_LEN:
        return await device.escribir_por_bloques(bloque)
    return await device.escribir(bloque)


# --- el paso 0: la tasa tiene que dejar leer -------------------------------
#
# Arriba de 1000 Hz el respaldo de los siete comandos no se completa (MEDIDO a
# 2000 y a 8000 Hz), y sin respaldo no hay Etapa 3. Para colmo el codificador
# de dpi parte del bloque leido, que es uno de los que se caen: a esa tasa no
# se puede ni **armar** la escritura.
#
# Bajar la tasa no afloja ninguna baranda: el respaldo completo se sigue
# exigiendo, solo que se lo toma donde sale, y lo unico que se escribe antes de
# tenerlo es el campo que se leyo un segundo antes.

async def tasa_actual(device) -> int | None:
    """Los Hz que declara el mouse, leyendo el bloque corto de cmd 6.

    Son 7 bytes y contesta a cualquier tasa, que es lo que lo hace util como
    semaforo.
    """
    frame = await device.leer(p.CMD_REPORT_RATE)
    if frame is None:
        return None
    leer_hz, _ = _tasa_del_camino(device)
    return leer_hz(bytes(frame.data))


#: Cuantas veces se manda la trama de rate antes de rendirse, **releyendo
#: entre una y otra**. Es exactamente lo que hace
#: `driver/scripts/cambiar-rate.py`, que es el unico camino MEDIDO que
#: funciona: las cuatro tasas en las dos direcciones, cada una en el primer
#: intento.
#:
#: Antes esto mandaba **una** trama y se rendia. Como el enlace
#: pierde pedidos de verdad -95% de exito con el mouse en movimiento, 50%
#: quieto- una sola perdida se convertia en `no-pude-bajar-la-tasa`, y como el
#: paso 0 de la Etapa 3 baja la tasa para poder respaldar, eso dejaba el campo
#: **sin poder escribirse** con el mouse arriba de 1000 Hz.
INTENTOS_DE_TASA = 4


async def poner_tasa(device, hz: int, *,
                     intentos: int = INTENTOS_DE_TASA) -> int | None:
    """Cambia la tasa y devuelve la que quedo, releyendo. None si no se pudo.

    **Si ya esta en `hz`, no manda nada.** Cada escritura de rate que llega
    reconfigura la radio del mouse: la pagina oficial mando seis
    en tres segundos -por clics encolados- y el mouse dejo de mover el puntero
    hasta que se lo saco del modo dongle. Escribir la tasa que ya esta puesta
    es pagar ese riesgo a cambio de nada.

    **Y si no esta, insiste releyendo entre intento e intento.** No es mandar
    varias seguidas: se corta apenas la relectura dice que entro, asi que con
    el enlace sano el mouse recibe **una** trama. El bucle existe porque el
    enlace pierde pedidos, no porque haya que repetir lo que ya se aplico.

    El acuse del dongle no decide, y por eso no se mira: contesto
    `0xC1` dos veces seguidas con el mouse a 2000 Hz sin que la tasa se moviera
    ni una. Lo unico que contesta la pregunta es la relectura.
    """
    frame = await device.leer(p.CMD_REPORT_RATE)
    if frame is None:
        return None
    leer_hz, escribir = _tasa_del_camino(device)
    leido = bytes(frame.data)
    bloque = bytes(escribir(leido, hz=hz))
    if bloque == leido:
        return leer_hz(leido)
    quedo = None
    for _ in range(max(1, intentos)):
        await device.escribir(bytes([p.CMD_REPORT_RATE, frame.sub]) + bloque)
        await asyncio.sleep(p.WRITE_BLOCK_PAUSE_SOFT)
        despues = await device.leer(p.CMD_REPORT_RATE)
        if despues is None:
            continue
        quedo = bytes(despues.data)
        if quedo == bloque:
            return leer_hz(quedo)
    return leer_hz(quedo) if quedo is not None else None


# --- el veredicto del paso 6 ------------------------------------------------
#
# Releer y comparar es la red de toda la Etapa 3, y el criterio tiene mas
# matices de los que parece. Vivia adentro de `primera-escritura.py`, mezclado
# con sus `print`, que es el unico lugar donde no le sirve a la aplicacion.
#
# Las dos reglas de fondo, que costaron sendos bugs:
#
#   * **una escritura idempotente que no mueve un byte es un EXITO**, no un
#     fallo. Antes el CLI anunciaba la alarma falsa y despues la emitia
#     igual, con salida 1;
#   * y un cambio real tiene que mover **lo que se pidio y nada mas**, salvo el
#     perfil completo, que embebe a los demas bloques y por eso acompaña.

@dataclass(frozen=True)
class Veredicto:
    """Como salio una escritura, mirando el estado de antes contra el de después."""

    ok: bool
    motivo: str                     # clave estable, para que el que muestra decida
    diferencias: list[str]
    cambiaron: frozenset[int]
    inesperados: frozenset[int]
    #: Los comandos que la relectura del paso 6 **no miro**. Vacio con la
    #: relectura completa, que es la de siempre. Existe porque un veredicto que
    #: dice "y nada mas" sin haber mirado seria justo lo que este proyecto le
    #: reprocha a la pagina oficial: afirmar sobre bytes que no leyo.
    no_releidos: frozenset[int] = frozenset()

    @property
    def explicacion(self) -> str:
        base = MOTIVOS.get(self.motivo, self.motivo)
        return base + self.advertencia_de_alcance

    @property
    def advertencia_de_alcance(self) -> str:
        """Lo que hay que decir cuando la relectura no miro todo.

        **No aparece cuando no hizo falta.** Si no se movio nada, el perfil
        completo -que si se releyo- alcanza como testigo: acompaña a todo
        cambio de dpi, luz, rate y botones (MEDIDO sobre los 139 respaldos
        versionados: 95 pares con alguna diferencia, 0 en los que el perfil no
        acompañara y 0 en los que se moviera solo). Si se movio algo, el perfil
        se movio tambien y ya no distingue nada: ahi la advertencia es real.
        """
        if not self.no_releidos:
            return ""
        if not self.cambiaron:
            return (" (no se releyo bloque por bloque, pero el perfil completo "
                    "tampoco se movio, y el perfil acompaña a todo cambio de "
                    "dpi, luz, tasa y botones: MEDIDO sobre 95 pares de "
                    "respaldos)")
        nombres = ", ".join(p.CMD_NAMES.get(c, f"cmd {c}")
                            for c in sorted(self.no_releidos))
        return (f" — OJO: no se releyeron {nombres}, asi que \"y nada mas\" no "
                "se verifico para ellos")


MOTIVOS = {
    "sin-diferencias":
        "el mouse quedo exactamente como estaba, que es lo que tenia que pasar",
    "idempotente-cambio-algo":
        "cambio algo, y en una escritura idempotente eso NO tenia que pasar",
    "no-cambio-nada":
        "no cambio nada, y se pidio un cambio. O el mouse ignoro la trama, o "
        "la relectura trajo un estado viejo",
    "cambio-otra-cosa":
        "cambio algo, pero no el comando que se pidio",
    "cambio-de-mas":
        "cambio lo que se pidio, pero tambien algo que no se toco",
    "cambio-lo-pedido":
        "cambio lo que se pidio, y nada mas",
    "lectura-corrompida":
        "cambio un bloque que no se puede escribir, asi que una de las dos "
        "lecturas vino mal y no hay nada que comparar",
}

#: Los bloques que **no pueden cambiar** entre dos lecturas del mismo mouse.
#: La version de firmware no se escribe: no hay comando que la toque, ni en el
#: bundle ni en el helper. Si dos lecturas suyas difieren, lo que fallo es una
#: lectura.
#:
#: Sirve de canario porque **no tiene checksum interno** -cmd 11 no esta en la
#: tabla de estructuras- asi que `checksum_interno_cierra()` no lo cubre y esta
#: es la unica forma de darse cuenta. MEDIDO: `080083010100` en 124 de los 125
#: respaldos versionados, y el unico que difiere es el de la sesion en la que
#: el canal por cable devolvio el buffer de otro bloque (2026-09-20).
CMDS_INMUTABLES = frozenset({p.CMD_VERSION})


def juzgar(antes: dict, despues: dict, *, cmd: int, idempotente: bool,
           no_releidos: frozenset[int] = frozenset()) -> Veredicto:
    """El criterio del paso 6 de la Etapa 3. No lee el mouse: solo compara.

    `idempotente` es True cuando se escribio el valor que el mouse ya tenia
    -sea porque no se pidio ninguno, sea porque el pedido resulto ser el que ya
    estaba-. Ahi el resultado bueno es que **no** cambie nada.

    `no_releidos` son los comandos que la relectura no miro (ver
    `RELECTURA_LO_ESCRITO`). **No cambia ningun veredicto**: viaja para que
    quien muestre pueda decir sobre que se afirma y sobre que no.
    """
    difs = diferencias(antes, despues)
    cambiaron = frozenset(cmds_que_cambiaron(antes, despues))

    # **El canario, y va antes que todo lo demas.** Si cambio un bloque que no
    # se puede escribir, una de las dos lecturas vino mal, y entonces comparar
    # no dice si la escritura entro: el veredicto seria sobre bytes inventados.
    # Va delante incluso de la rama idempotente, porque ahi el resultado bueno
    # es "no cambio nada" y una lectura podrida lo daria por malo sin decir por
    # que.
    corrompidos = cambiaron & CMDS_INMUTABLES
    if corrompidos:
        return Veredicto(False, "lectura-corrompida", difs, cambiaron,
                         frozenset(corrompidos), no_releidos)

    if idempotente:
        return Veredicto(ok=not difs,
                         motivo="sin-diferencias" if not difs
                                else "idempotente-cambio-algo",
                         diferencias=difs, cambiaron=cambiaron,
                         inesperados=frozenset(), no_releidos=no_releidos)

    if not cambiaron:
        return Veredicto(False, "no-cambio-nada", difs, cambiaron, frozenset(),
                         no_releidos)
    if cmd not in cambiaron:
        return Veredicto(False, "cambio-otra-cosa", difs, cambiaron,
                         frozenset(cambiaron), no_releidos)

    # El perfil completo embebe a los demas bloques, asi que cambia siempre que
    # cambie alguno: acompaña, no sobra.
    inesperados = frozenset(cambiaron - {cmd, p.CMD_PROFILE})
    if inesperados:
        return Veredicto(False, "cambio-de-mas", difs, cambiaron, inesperados,
                         no_releidos)
    return Veredicto(True, "cambio-lo-pedido", difs, cambiaron, frozenset(),
                     no_releidos)


# --- el paso 6 barato: releer lo escrito, con el perfil de testigo ---------
#
# La relectura completa son los siete comandos mas los macros, y **leer el
# mouse tarda minutos**. Eso esta bien para una corrida de terminal donde se
# escribe un campo por vez y se mira la salida; para una ventana en la que
# alguien mueve un deslizador es lo que la deja congelada.
#
# La salida barata se apoya en algo que ya estaba medido y que este proyecto
# usaba solo de costado: **el perfil completo (cmd 10) acompaña a todo cambio
# de los otros bloques**. Estaba en `evidencia.md` para dos comandos -rate y
# botones-; se lo verifico sobre los
# **139 respaldos versionados**, que son mediciones contra el hardware ya
# hechas y guardadas:
#
#     pares consecutivos con alguna diferencia ......... 95
#     cambio solo dpi        -> el perfil acompaño ..... 28 de 28
#     cambio solo luz        -> el perfil acompaño ..... 19 de 19
#     cambio solo rate       -> el perfil acompaño ....... 2 de 2
#     cambio solo botones    -> el perfil acompaño ..... 17 de 17
#     el perfil se movio solo (falso positivo) .......... 0
#     cambio algo sin que el perfil se moviera .......... 0
#
# Asi que releer **el bloque escrito y el perfil** contesta las dos preguntas
# del paso 6 con dos lecturas en vez de nueve:
#
#   * cambio lo que se pidio? -> lo dice el bloque escrito;
#   * se movio algo mas? -> si el perfil no se movio, no se movio nada de dpi,
#     luz, rate ni botones. Si se movio, era de esperar -acabamos de cambiar
#     algo- y entonces **ya no distingue**, y eso se dice: `Veredicto.
#     no_releidos` lleva los comandos que no se miraron y la explicacion los
#     nombra.
#
# **Lo que esto NO cubre, y hay que decirlo**: los macros. Viven en
# `estado["macros"]`, se leen con su id y ningun par de respaldos los movio sin
# mover tambien otra cosa, asi que no hay medicion que diga que el perfil los
# refleje. El macro que se escribe si se relee; los otros no se miran.
#
# Por eso `RELECTURA_TODO` sigue siendo el default y es lo que usa el CLI: la
# relectura acotada es para la ventana, que es quien paga los minutos.

#: La relectura de siempre: los siete comandos y los macros. Es la unica que
#: puede afirmar "cambio lo pedido **y nada mas**" sobre el mouse entero.
RELECTURA_TODO = "todo"
#: La barata: el bloque escrito y el perfil completo, que hace de testigo.
RELECTURA_LO_ESCRITO = "lo-escrito"

#: La clave con la que un estado dice **que no se releyo entero**. Un JSON de
#: respaldo sin esta clave afirma que sus siete bloques se leyeron del mouse
#: en esa corrida; uno con ella dice cuales vienen copiados del estado anterior.
#: Sin esto, guardar una relectura acotada en `dev/models/attackshark-x8pro/respaldos/` seria fechar como de
#: ahora bytes que se leyeron hace diez minutos.
CLAVE_ACOTADA = "relectura_acotada"

#: La clave con la que un estado dice que **su bloque de rate es el prestado**:
#: se leyo con la tasa bajada para poder leer el mouse entero, dice 1000, y el
#: mouse es de la tasa que trae esta clave. La pone `Configuracion` al bajar la
#: tasa y **la deja al devolverla** -el bloque en memoria sigue diciendo 1000 y
#: el mouse volvio a la suya-; la saca cuando su dueño elige una tasa,
#: escribiendola o quedandose con la prestada. `modelo.como_esta()` la usa para
#: que "volver a como estaba" no confunda la tasa prestada con la del dueño.
CLAVE_TASA_BAJADA = "tasa_bajada_desde"

#: La clave con la que un estado dice que **su tasa la puso la sesion porque la
#: que habia no se entendia**: lleva el bloque de rate tal como vino, en hex.
#: Es el respaldo del unico campo que se escribe sin haber podido leer el mouse
#: entero, y viaja con el estado para que quede en `al-abrir.json`.
CLAVE_TASA_ARREGLADA = "tasa_arreglada_desde"


async def releer_lo_escrito(device, *, cmd: int, antes: dict,
                            macro_id: int | None = None, nodo: str = "",
                            al_leer: AlLeer | None = None
                            ) -> tuple[dict, frozenset[int]]:
    """El estado posterior mirando solo el bloque escrito y el perfil.

    Devuelve `(despues, no_releidos)`. Lo que no se releyo viene **copiado de
    `antes`**, y el estado queda marcado con `CLAVE_ACOTADA` para que nadie lo
    confunda con una lectura completa.
    """
    despues = copy.deepcopy(antes)
    despues["fecha"] = datetime.now().isoformat(timespec="seconds")
    despues["nodo"] = nodo or antes.get("nodo", "")

    # El macro no se pide con el perfil sino con su id, y vive en otra seccion:
    # por eso el pedido lleva el `macro_id` y no alcanza con el cmd.
    pedidos = [(cmd, macro_id)]
    if cmd != p.CMD_PROFILE:
        pedidos.append((p.CMD_PROFILE, None))

    leidos = set()
    for c, mid in pedidos:
        nombre = (f"macro {mid}" if mid is not None
                  else p.CMD_NAMES.get(c, f"cmd {c}"))
        frame = await device.leer(c, macro_id=mid)
        if frame is None:
            if mid is not None:
                despues.setdefault("macros", {})[str(mid)] = None
            else:
                despues["comandos"][str(c)] = None
            if al_leer:
                al_leer(Lectura(c, nombre, None, macro_id=mid))
            continue
        if mid is not None:
            entrada = {
                "datos": frame.data.hex(),
                "checksum_ok": frame.checksum_ok,
                "legible": estructuras.describir(p.CMD_MACRO, frame.data),
            }
            despues.setdefault("macros", {})[str(mid)] = entrada
        else:
            entrada = _entrada(c, frame)
            despues["comandos"][str(c)] = entrada
            leidos.add(c)
        if al_leer:
            al_leer(Lectura(c, nombre, entrada, macro_id=mid))

    no_releidos = frozenset(int(k) for k in antes["comandos"]) - leidos
    despues[CLAVE_ACOTADA] = {
        "comandos": sorted(no_releidos),
        "macros": sorted(int(k) for k in antes.get("macros", {})
                         if macro_id is None or int(k) != macro_id),
    }
    return despues, no_releidos


# --- el procedimiento entero de la Etapa 3 ---------------------------------
#
# Los pasos, en orden, y cada uno con su motivo de existir:
#
#   0. la tasa tiene que dejar leer -arriba de 1000 Hz el respaldo no sale-;
#   1. respaldo **completo**, o no se escribe: sin el no hay a donde volver;
#   2. leer el bloque del comando, que es de donde parte el codificador;
#   3. codificar el cambio (lo hace quien llama: depende del campo);
#   4. confirmar, mostrando la trama que va a salir;
#   5. escribir y mirar el acuse -que es del dongle, no del mouse-;
#   6. releer TODO y juzgar: no solo el campo que se toco, los siete comandos.
#
# Esta funcion hace la coreografia y **ninguna de las decisiones de politica**:
# quien llama decide si el comando se puede escribir, como se codifica el
# campo, como se pregunta y que se hace con el resultado. Por eso `confirmar` y
# `codificar` son callbacks y no `if`s aca adentro.

@dataclass(frozen=True)
class Resultado:
    """Como termino un intento de escritura, con todo lo que hay que mostrar."""

    ok: bool
    motivo: str
    veredicto: Veredicto | None = None
    antes: dict | None = None
    despues: dict | None = None
    aplicada: bool = False          # el 0xC1 del dongle, o por cable, que
                                    # el mouse acepto el report
    bloque: bytes | None = None     # lo que se mando, para poder mostrarlo
    tasa_bajada_desde: int | None = None

    @property
    def explicacion(self) -> str:
        if self.veredicto is not None and self.motivo == self.veredicto.motivo:
            return self.veredicto.explicacion
        return MOTIVOS.get(self.motivo, self.motivo)


MOTIVOS.update({
    "tasa-alta": "el mouse esta arriba de 1000 Hz y el respaldo completo no "
                 "sale a esa tasa",
    "no-pude-bajar-la-tasa": "no se pudo bajar la tasa para poder respaldar",
    "respaldo-incompleto": "el respaldo previo salio incompleto, y un respaldo "
                           "incompleto no sirve como red",
    "no-contesto": "el mouse no contesto la lectura del comando que se iba a "
                   "escribir",
    "sin-tasa": "el mouse no contesto ni la lectura de la tasa, que es la mas "
                "corta de todas: movelo y volvé a leer",
    "tasa-ilegible": "el mouse contesto la tasa con un byte que no es ninguno "
                     "de los siete conocidos y no se la pudo dejar en 1000 "
                     "Hz, asi que no se sabe a cuanto esta y no se lee ni se "
                     "escribe. driver/scripts/cambiar-rate.py lo muestra, y "
                     "con --valor lo cambia",
    "sin-confirmar": "no se confirmo la escritura",
    "relectura-incompleta": "la relectura salio incompleta, asi que no se "
                            "puede comparar",
    "macro-sin-relectura": "por este camino el macro no se puede releer, asi "
                           "que no se escribe",
    "bloque-imposible": "el bloque que se iba a escribir tiene valores fuera "
                        "de rango y no se mando: sale de una lectura que vino "
                        "mal, o de un codificador que la rompio",
    "respaldo-incoherente": "el respaldo previo se contradice a si mismo: el "
                            "perfil completo y un bloque suelto traen bytes "
                            "distintos de lo mismo, asi que una lectura vino "
                            "mal y no sirve de red",
    "relectura-incoherente": "la relectura se contradice a si misma, asi que "
                             "no se puede juzgar si el mouse aplico el cambio",
})

# **Los dos comandos donde una escritura idempotente NO devuelve el bloque
# leido.** Para el resto -rate, luz, dpi- escribir lo mismo produce los mismos
# bytes. Para estos dos no, y por motivos medidos:
#
#   * cmd 8: los slots 4, 5 y 6 se permutan entre lectura y escritura
#     (MEDIDO), asi que `retraducir_botones()` devuelve un bloque distinto
#     del leido y deja al mouse igual;
#   * cmd 9: el mouse devuelve el checksum interno invertido -`6d 0c` al leer,
#     `0c 6d` al escribir- (MEDIDO).
CMDS_QUE_NO_VUELVEN_IGUAL = frozenset({p.CMD_BUTTONS, p.CMD_MACRO})


def referencia_idempotente(cmd: int, leido: bytes) -> bytes:
    """Lo que un codificador devuelve **cuando no cambia nada**.

    Es con esto -y no con el bloque leido- que hay que comparar para saber si
    una escritura pide un cambio real. Comparar contra `leido` da lo contrario
    de la verdad en cmd 8 y cmd 9 (ver `CMDS_QUE_NO_VUELVEN_IGUAL`): ahi lo
    idempotente sale distinto a proposito, y `juzgar()` terminaba dando
    `no-cambio-nada` a una escritura que salio perfecta.

    Lo encontro la migracion de `primera-escritura.py`. El primer
    arreglo fue negarse a adivinar; este es el bueno, porque adivina bien.
    """
    if cmd == p.CMD_BUTTONS:
        return bytes(estructuras.retraducir_botones(leido))
    if cmd == p.CMD_MACRO:
        return bytes(estructuras.escribir_macro(leido))
    return bytes(leido)

#: Lo que `aplicar()` manda por `al_avisar` justo antes de tomar el respaldo
#: completo. Existe para que quien llama pueda numerar ese paso sin adivinar
#: cuando empieza: el CLI lo imprime como `[1/6]`.
AVISO_RESPALDO = "respaldo"
#: Lo mismo para la relectura del paso 6, que es la que dice si el mouse
#: aplico algo. El CLI la numera `[6/6]`.
AVISO_RELECTURA = "relectura"
#: Y el acuse del dongle, avisado en el momento en que llega -entre la
#: escritura y la relectura-. Sin esto quien llama solo puede contarlo cuando
#: `aplicar()` termina, o sea despues del paso 6, que es tarde: la pregunta
#: "acuso?" se hace en el paso 5.
AVISO_ACUSE = "acuse"
AVISO_SIN_ACUSE = "sin-acuse"
#: Por cable no hay dongle ni `0xC1`: lo que hay es que el mouse acepte el
#: report o lo rechace con STALL (despues de repetirlo, ver `cable.py`).
AVISO_CABLE_ACEPTO = "cable-acepto"
AVISO_CABLE_RECHAZO = "cable-rechazo"
#: Los dos de la tasa llevan texto detras, porque incluyen los Hz. Van como
#: `clave|texto` para que quien llama pueda numerar y envolver el mensaje sin
#: adivinar por el contenido, y para que el que no lo parsea vea igual algo
#: legible. Se separan con `split("|", 1)`.
AVISO_TASA_BAJA = "tasa-baja"
AVISO_TASA_VUELVE = "tasa-vuelve"
#: La tasa que habia no se entendia y se la dejo en 1000 Hz. Lleva detras el
#: byte que vino (ver `aviso_de_tasa_arreglada`).
AVISO_TASA_ARREGLADA = "tasa-arreglada"
#: El respaldo no se tomo porque quien llama trajo uno. Va aparte de
#: `AVISO_RESPALDO` a proposito: son dos cosas distintas y el que mira tiene
#: derecho a saber cual paso. Lleva detras la fecha del respaldo que se uso.
AVISO_RESPALDO_TRAIDO = "respaldo-traido"
#: La relectura del paso 6 miro solo el bloque escrito y el perfil.
AVISO_RELECTURA_ACOTADA = "relectura-acotada"
#: El estado cacheado dejo de ser confiable y hay que releer el mouse. Lleva
#: detras el motivo cuando lo hay.
AVISO_CACHE_VIEJO = "cache-viejo"
#: El bloque codificado tiene valores que el mouse no puede tener, asi que no
#: se mando (ver `estructuras.fuera_de_rango`). Lleva detras que campo se fue
#: de rango: sin eso, "no lo escribi" no dice donde mirar.
AVISO_BLOQUE_IMPOSIBLE = "bloque-imposible"
#: Un estado leido se contradice: el perfil completo y un bloque suelto traen
#: bytes distintos de lo mismo (ver `incoherencias`). Lleva detras cual y que
#: dice cada uno. Va uno por discrepancia, no uno resumido: cual bloque se
#: contradice es lo que dice donde mirar.
AVISO_ESTADO_INCOHERENTE = "estado-incoherente"

Codificar = Callable[[bytes], bytes]
Confirmar = Callable[[bytes, bytes], Awaitable[bool]]
#: `bajar_la_tasa` acepta un `bool` -el si o el no dados de antemano- o una
#: corrutina que recibe los Hz actuales y contesta. La segunda forma existe
#: para que **quien llama pueda preguntar antes de que se toque nada**: bajar
#: la tasa es una escritura al mouse, y ocurre antes del `confirmar` de la
#: escritura principal. Si se bajara primero y se preguntara despues, un "no"
#: dejaria al mouse tocado por una corrida que el usuario aborto.
PermisoDeTasa = bool | Callable[[int], Awaitable[bool]]


async def aplicar(device, *, cmd: int, codificar: Codificar,
                  confirmar: Confirmar, nodo: str = "",
                  macro_id: int | None = None, macros_extra=(),
                  bajar_la_tasa: PermisoDeTasa = False,
                  idempotente: bool | Callable[[], bool] | None = None,
                  respaldo: dict | None = None,
                  relectura: str = RELECTURA_TODO,
                  al_leer: AlLeer | None = None,
                  al_reintentar: AlReintentar | None = None,
                  al_cortar: AlCortar | None = None,
                  al_guardar: Callable[[str, dict], None] | None = None,
                  al_avisar: Callable[[str], None] | None = None) -> Resultado:
    """Corre la Etapa 3 entera para un comando. Devuelve como salio.

    `codificar` recibe el bloque que devolvio el mouse y devuelve el que hay
    que escribir -sin `[cmd, sub]`, que los pone esta funcion-. Si devuelve lo
    mismo que recibio, la escritura es **idempotente** y el resultado bueno
    pasa a ser que no cambie nada.

    `confirmar` recibe `(bloque, trama)` y decide. Sin confirmacion no se
    escribe: es una baranda de quien llama, y aca se la respeta.

    **`respaldo` es un estado ya leido que se usa en lugar de tomar uno.** No
    afloja el paso 1: el respaldo completo se sigue exigiendo -si el que traen
    esta incompleto, no se escribe nada- y lo unico que cambia es **quien** lo
    leyo. Existe porque leer el mouse entero tarda minutos y la Etapa 3 lo hacia
    **dos veces por campo**: con eso, mover un deslizador en la ventana la
    dejaba congelada varios minutos, que es el problema que esto viene a
    arreglar. Quien lo trae se hace cargo de que sea de este mouse y de que no
    haya quedado viejo (ver `Configuracion`).

    `relectura` elige el alcance del paso 6: `RELECTURA_TODO` (el default, y lo
    que usa el CLI) o `RELECTURA_LO_ESCRITO`, que mira el bloque escrito y el
    perfil completo. Lo que no se mira viaja en `Veredicto.no_releidos` y la
    explicacion lo nombra: un veredicto no puede afirmar sobre bytes que no
    leyo.
    """
    def avisar(texto: str) -> None:
        if al_avisar:
            al_avisar(texto)

    # **Por un camino que no lee el macro, el macro no se escribe**: el paso 6
    # es releer. Se corta antes de tocar nada, con un motivo propio: el
    # "no contesto" que saldria del paso 2 mandaria a buscar un problema de
    # enlace que no hay. Hoy los dos caminos lo leen; queda por el que venga.
    if cmd == p.CMD_MACRO and not lee_macros(device):
        return Resultado(False, "macro-sin-relectura")
    # **Y por cable se relee todo.** La relectura barata se apoya en que el
    # perfil completo acompaña a todo cambio, y eso esta medido por el dongle.
    # Por cable no hace falta la apuesta: no hay radio que pierda pedidos, y
    # releer los seis bloques tarda segundos, no minutos.
    if via_de(device) == dispositivos.VIA_CABLE:
        relectura = RELECTURA_TODO

    # --- 0. la tasa ---
    tasa_original = None
    hz = await tasa_actual(device)
    if hz is not None and hz > RATE_MAXIMO_PARA_LEER:
        permitido = (await bajar_la_tasa(hz) if callable(bajar_la_tasa)
                     else bool(bajar_la_tasa))
        if not permitido:
            return Resultado(False, "tasa-alta")
        # **El aviso dice las tres cosas que hacen falta para no asustarse**:
        # que se va a tocar la tasa, por que, y que vuelve al terminar. Sin la
        # tercera, "bajo a 1000" se lee como que el mouse queda ahi.
        avisar(f"{AVISO_TASA_BAJA}|el mouse esta a {hz} Hz, y arriba de "
               f"{RATE_MAXIMO_PARA_LEER} Hz el respaldo de los siete comandos "
               f"no sale (MEDIDO a 2000 y a 8000). Bajo a 1000 para poder "
               f"respaldar y te devuelvo los {hz} al terminar, pase lo que "
               f"pase: va en el `finally`, asi que vuelve aunque la escritura "
               f"falle")
        if await poner_tasa(device, 1000) != 1000:
            return Resultado(False, "no-pude-bajar-la-tasa")
        tasa_original = hz

    try:
        # --- 1. respaldo completo, o no se escribe ---
        # **El respaldo sigue siendo obligatorio**; lo que puede cambiar es
        # quien lo leyo. Un respaldo traido que este incompleto se rechaza
        # igual, tres lineas mas abajo, por el mismo `incompletos()`.
        if respaldo is not None:
            antes = respaldo
            avisar(f"{AVISO_RESPALDO_TRAIDO}|uso el respaldo de "
                   f"{antes.get('fecha', 'fecha desconocida')} en vez de leer "
                   "el mouse entero de nuevo")
        else:
            avisar(AVISO_RESPALDO)
            antes = await leer_estado(device, nodo=nodo,
                                      macros_extra=macros_extra,
                                      al_leer=al_leer,
                                      al_reintentar=al_reintentar,
                                      al_cortar=al_cortar)
        if al_guardar:
            al_guardar("antes", antes)
        if incompletos(antes):
            return Resultado(False, "respaldo-incompleto", antes=antes,
                             tasa_bajada_desde=tasa_original)
        # **Un respaldo que se contradice no sirve de red**, por el mismo
        # motivo que uno incompleto: el codificador parte de estos bytes y el
        # paso 6 compara contra ellos. Si el perfil y el bloque suelto dicen
        # cosas distintas, una de las dos lecturas vino mal y no se sabe cual.
        malas = incoherencias(antes)
        if malas:
            for linea in malas:
                avisar(f"{AVISO_ESTADO_INCOHERENTE}|{linea}")
            return Resultado(False, "respaldo-incoherente", antes=antes,
                             tasa_bajada_desde=tasa_original)

        # --- 2. el valor actual, que es de donde parte el codificador ---
        frame = await device.leer(cmd, macro_id=macro_id)
        if frame is None:
            return Resultado(False, "no-contesto", antes=antes,
                             tasa_bajada_desde=tasa_original)
        leido = bytes(frame.data)

        # --- 3. codificar (la politica es de quien llama) ---
        datos = bytes(codificar(leido))
        # **Comparar bytes no sirve para cmd 8 ni cmd 9** (ver
        # `CMDS_QUE_NO_VUELVEN_IGUAL`): ahi lo idempotente sale distinto de lo
        # leido a proposito, y quien llama es el unico que sabe si pidio un
        # cambio. Para el resto se infiere, que es lo que hacia siempre.
        # **La idempotencia se infiere contra la referencia, no contra lo
        # leido** (ver `referencia_idempotente`). Quien llama puede decirla
        # igual -un bool, o un callable que se evalua recien aca, que es
        # cuando se sabe- pero no hace falta.
        quiza = idempotente() if callable(idempotente) else idempotente
        es_idempotente = (datos == referencia_idempotente(cmd, leido)
                          if quiza is None else bool(quiza))
        bloque = bytes([cmd, frame.sub]) + datos

        # --- 3b. un bloque imposible no se manda ---
        # **La baranda mira lo que SE VA A ESCRIBIR, no lo que se leyo.** Los
        # codificadores copian del bloque que reciben, asi que una lectura mala
        # sale de aca como una escritura mala -con el checksum recalculado, o
        # sea valida- y el paso 6 la compara contra un respaldo que ya no
        # describe al mouse. Mirar la salida cubre ademas al codificador, y
        # **deja pasar un bloque bueno escrito sobre un mouse que quedo mal**,
        # que es lo que hace falta para poder restaurarlo.
        #
        # Va antes del paso 4 a proposito: no tiene sentido pedir que confirmen
        # algo que no se va a mandar.
        imposible = estructuras.fuera_de_rango(cmd, datos)
        if imposible is not None:
            avisar(f"{AVISO_BLOQUE_IMPOSIBLE}|{imposible}")
            return Resultado(False, "bloque-imposible", antes=antes,
                             bloque=bloque, tasa_bajada_desde=tasa_original)

        # --- 4. confirmar ---
        if not await confirmar(bloque, trama_de(device, bloque)):
            return Resultado(False, "sin-confirmar", antes=antes, bloque=bloque,
                             tasa_bajada_desde=tasa_original)

        # --- 5. escribir ---
        aplicada = await escribir_bloque(device, bloque)
        if via_de(device) == dispositivos.VIA_CABLE:
            avisar(AVISO_CABLE_ACEPTO if aplicada else AVISO_CABLE_RECHAZO)
        else:
            avisar(AVISO_ACUSE if aplicada else AVISO_SIN_ACUSE)

        # --- 6. releer y juzgar ---
        no_releidos = frozenset()
        if relectura == RELECTURA_LO_ESCRITO:
            avisar(AVISO_RELECTURA_ACOTADA)
            despues, no_releidos = await releer_lo_escrito(
                device, cmd=cmd, antes=antes, macro_id=macro_id, nodo=nodo,
                al_leer=al_leer)
        else:
            avisar(AVISO_RELECTURA)
            despues = await leer_estado(
                device, nodo=nodo,
                macros_extra=macros_a_releer(macros_extra, antes),
                al_leer=al_leer, al_reintentar=al_reintentar,
                al_cortar=al_cortar)
        if al_guardar:
            al_guardar("despues", despues)
        if incompletos(despues):
            return Resultado(False, "relectura-incompleta", antes=antes,
                             despues=despues, aplicada=aplicada, bloque=bloque,
                             tasa_bajada_desde=tasa_original)
        # Y lo mismo del otro lado: juzgar contra una relectura que se
        # contradice es afirmar sobre bytes que no son del mouse. **La
        # escritura ya salio**, asi que esto no la evita; lo que evita es dar
        # un veredicto -bueno o malo- que no se puede sostener.
        malas = incoherencias(despues)
        if malas:
            for linea in malas:
                avisar(f"{AVISO_ESTADO_INCOHERENTE}|{linea}")
            return Resultado(False, "relectura-incoherente", antes=antes,
                             despues=despues, aplicada=aplicada, bloque=bloque,
                             tasa_bajada_desde=tasa_original)

        veredicto = juzgar(antes, despues, cmd=cmd, idempotente=es_idempotente,
                           no_releidos=no_releidos)
        return Resultado(veredicto.ok, veredicto.motivo, veredicto=veredicto,
                         antes=antes, despues=despues, aplicada=aplicada,
                         bloque=bloque, tasa_bajada_desde=tasa_original)
    finally:
        # **La tasa vuelve pase lo que pase.** Dejarla abajo seria cambiarle al
        # mouse algo que nadie pidio, y encima en silencio.
        if tasa_original is not None:
            quedo = await poner_tasa(device, tasa_original)
            avisar(f"{AVISO_TASA_VUELVE}|tasa devuelta a {quedo} Hz"
                   if quedo == tasa_original
                   else f"{AVISO_TASA_VUELVE}|OJO: la tasa quedo en {quedo} "
                        f"Hz, no en {tasa_original}")


# **Los dos estados de una escritura se leen con la MISMA lista de macros.**
# Los ids salen de los slots de cmd 8, asi que asignar un macro hace que
# aparezca solo en el estado posterior, y desasignarlo, solo en el previo. Las
# dos cosas pasaron contra el hardware -12:36 y 17:12- y las dos
# salieron impresas como `macro 17: uno de los dos no contesto (A|B)` adentro
# de la lista de cambios reales, que es el unico lugar donde conviene que no
# haya ruido.
#
# La lista sale del estado previo, que es lo unico que sabe que macros habia
# antes de escribir. Con eso "uno de los dos no contesto" vuelve a significar
# una sola cosa: que el enlace perdio el pedido.
def macros_a_releer(extra, antes: dict) -> list[int]:
    """Los ids que tiene que leer el estado posterior. Devuelve, no lee."""
    return sorted({*extra, *(int(k) for k in antes.get("macros", {}))})


# --- configurar el mouse sin releerlo entero cada vez ----------------------
#
# **El problema que esto arregla, medido.** Con el mouse a 2000,
# 4000 u 8000 Hz la ventana no podia cambiar un parametro, y mientras lo
# intentaba quedaba congelada. Son tres fallas distintas encimadas, y las tres
# salen de que cada escritura era una Etapa 3 entera y aislada:
#
#   1. **una perdida de radio bastaba para que el campo no se pudiera
#      escribir.** El paso 0 baja la tasa con `poner_tasa()`, que mandaba UNA
#      trama y se rendia; con 50% de perdida con el mouse quieto, eso salia
#      `no-pude-bajar-la-tasa` la mitad de las veces. Arreglado en
#      `poner_tasa()`, que ahora insiste como `driver/scripts/cambiar-rate.py`;
#   2. **dos escrituras de rate por campo.** El paso 0 baja y el `finally`
#      devuelve, asi que tres cambios eran seis reconfiguraciones de la radio.
#      Y esta MEDIDO lo que eso hace: la pagina oficial mando seis tramas de rate en tres segundos -por clics encolados- y **el mouse
#      dejo de mover el puntero** hasta que se lo saco del modo dongle. O sea
#      que la ventana tenia un camino directo a dejar el mouse inutilizable;
#   3. **dos lecturas completas por campo**, y leer el mouse entero tarda
#      minutos. Eso es el "se cuelga": la ventana se bloquea a proposito
#      mientras escribe, y esperaba dos respaldos completos por deslizador
#      movido.
#
# `Configuracion` es la respuesta a los puntos 2 y 3: **la tasa se baja una vez
# por rafaga y el estado se lee una vez**, y de ahi en mas cada escritura
# arranca con el respaldo que ya esta y relee solo lo que escribio.
#
# **Que NO afloja**, que es lo que importa en este proyecto:
#
#   * el respaldo completo sigue siendo obligatorio antes de escribir. Si la
#     lectura sale incompleta, no se cachea nada y no se escribe;
#   * la relectura y el veredicto siguen ahi, y el veredicto **dice que no
#     miro** cuando no miro todo (`Veredicto.no_releidos`);
#   * la tasa vuelve. Al soltar la sesion, y en el `finally` de quien la tenga.
#
# **Lo que si cambia, y hay que saberlo**: el respaldo que sirve de red puede
# ser de hace minutos y no de hace segundos. Es una red igual -es el estado que
# el mouse tenia- salvo que algo lo haya movido por afuera. Los dos caminos por
# los que eso pasa estan cubiertos: el firmware, que escribe
# `Current_Dpi_level_flag` cuando alguien cicla el dpi con el boton y lo avisa
# por el Report ID 3 (`invalidar()`), y otro cliente oficial, que no puede
# correr al mismo tiempo que este porque el nodo es exclusivo.

#: Despues de cuanto silencio conviene devolver la tasa. No es una regla del
#: protocolo: es que la tasa prestada es del usuario, y si la ventana se queda
#: abierta sin que nadie toque nada, el mouse tiene que volver a como estaba.
#: Quien decide cuando llamar a `soltar()` es la interfaz; esto es el numero
#: que usa.
#:
#: **Tres minutos y no uno** porque el costo de que se venza no es cero: hay
#: que devolver la tasa y volver a pedirla prestada, y cada trama de rate
#: reconfigura la radio. Con el cache refrescado en vez de tirado (ver
#: `preparar()`) eso son dos tramas y dos lecturas cortas, no una lectura
#: completa, pero sigue sin convenir que pase cada vez que alguien se queda
#: mirando la pantalla.
GRACIA_ANTES_DE_SOLTAR = 180.0

MOTIVOS.update({
    "listo": "el mouse esta listo para configurarlo",
    "tasa-puesta": "la tasa quedo puesta, y la relectura lo confirma. "
                   "Verificala por fuera del protocolo si querés: "
                   "driver/scripts/medir-polling.py --segundos 10",
    "no-entro-la-tasa": "el mouse no aplico la tasa aunque el dongle acusara. "
                        "Probá de nuevo moviendo el mouse",
    "tasa-desconocida": "esa tasa no es ninguna de las siete que el driver "
                        "oficial escribe",
})


class Configuracion:
    """El mouse abierto para configurarlo: la tasa baja una vez, se lee una vez.

    Es la capa que usa la **ventana**. El CLI no la necesita: escribe un campo
    por corrida y despues se va, asi que para el una Etapa 3 aislada es
    exactamente lo correcto.

    No imprime y no decide politicas, igual que el resto de este modulo: avisa
    por los mismos callbacks que `aplicar()` y con las mismas claves.
    """

    def __init__(self, device, *, nodo: str = "",
                 al_leer: AlLeer | None = None,
                 al_reintentar: AlReintentar | None = None,
                 al_cortar: AlCortar | None = None,
                 al_avisar: Callable[[str], None] | None = None) -> None:
        self._device = device
        self._nodo = nodo
        self._al_leer = al_leer
        self._al_reintentar = al_reintentar
        self._al_cortar = al_cortar
        self._al_avisar = al_avisar
        #: De que tasa se bajo, o None si no se toco. Mientras no sea None, la
        #: tasa del mouse **es prestada** y hay que devolverla.
        self._tasa_original: int | None = None
        #: El bloque de rate que habia antes de `_arreglar_la_tasa()`, en hex.
        self._tasa_arreglada_desde: str | None = None
        #: El respaldo vivo. None significa "no se sabe como esta el mouse", y
        #: la proxima escritura vuelve a leerlo entero.
        self._estado: dict | None = None
        self._macros_extra: tuple[int, ...] = ()

    # --- lo que se puede preguntar ---------------------------------------

    @property
    def estado(self) -> dict | None:
        """El ultimo estado completo conocido. None si hay que releer."""
        return self._estado

    @property
    def tasa_prestada(self) -> int | None:
        """A que tasa hay que devolver el mouse, o None si no se le debe nada."""
        return self._tasa_original

    def quedarse_con_la_tasa(self) -> int | None:
        """Deja de deber la tasa: la que esta puesta pasa a ser la elegida.

        Devuelve la que se dejo de deber, o None si no se debia nada.

        **No le escribe nada al mouse**, y por eso existe: el mouse ya esta a
        `RATE_MAXIMO_PARA_LEER` -lo bajo `preparar()`- asi que "quedarse con
        estos 1000" es cancelar la deuda, no una escritura. Mandar una trama
        para poner la tasa que ya esta seria reconfigurar la radio de gusto,
        que es lo que `poner_tasa()` evita a proposito.

        Lo pidio el usuario (2026-09-20): quien se sienta a configurar a 1000
        Hz muchas veces quiere quedarse ahi, y la unica salida que habia era
        dejar que la sesion devolviera los 8000 y despues bajarlos de nuevo con
        `cambiar-rate.py`, que **si** reconfigura la radio dos veces.

        Es del usuario y de nadie mas: esta clase presta la tasa sin preguntar
        -y lo dice-, pero **quedarsela no se decide solo**.
        """
        debia, self._tasa_original = self._tasa_original, None
        self._marcar_la_tasa(None)
        return debia

    def _marcar_la_tasa(self, hz: int | None) -> None:
        """Anota en el estado cacheado de que tasa se bajo su bloque de rate.

        None la saca: el bloque de rate es la tasa de su dueño. Ver
        `CLAVE_TASA_BAJADA`.
        """
        if self._estado is None:
            return
        if hz is None:
            self._estado.pop(CLAVE_TASA_BAJADA, None)
        else:
            self._estado[CLAVE_TASA_BAJADA] = hz

    def invalidar(self, motivo: str = "") -> None:
        """Marca el estado cacheado como no confiable. **No toca la tasa.**

        Lo llama quien se entera de que el mouse cambio por afuera: hoy, el
        cambio de nivel de dpi que el firmware hace solo cuando alguien aprieta
        el boton y avisa por el Report ID 3. Ese es el unico camino medido por
        el que el mouse se mueve sin que lo movamos nosotros.
        """
        if self._estado is not None and self._al_avisar:
            self._al_avisar(f"{AVISO_CACHE_VIEJO}|{motivo}" if motivo
                            else AVISO_CACHE_VIEJO)
        self._estado = None

    # --- abrir ------------------------------------------------------------

    async def preparar(self, *, macros_extra=(),
                       permiso: PermisoDeTasa = True,
                       forzar_lectura: bool = False) -> Resultado:
        """Deja el mouse en condiciones de que se le escriba. Se puede repetir.

        Baja la tasa **si hace falta y solo la primera vez**, y lee el estado
        entero **si no lo tiene**. Las dos cosas son idempotentes: llamarla
        antes de cada escritura no cuesta nada cuando ya esta todo listo.
        """
        def avisar(texto: str) -> None:
            if self._al_avisar:
                self._al_avisar(texto)

        # **No contestar y contestar algo ilegible son dos problemas
        # distintos**, y `tasa_actual()` devuelve None por los dos. Antes salian
        # juntos como `no-contesto`, que ademas habla de una escritura que aca
        # no hay: mandaba a buscar un problema de enlace con el mouse
        # contestando al primer intento. MEDIDO el 2026-10-04: el bloque era
        # `01 02 fd 00 00 00 00` -nibble alto 0, que no es ningun indice- con
        # el mouse reportando a 8000 Hz (`medir-polling.py`).
        frame = await self._device.leer(p.CMD_REPORT_RATE)
        if frame is None:
            return Resultado(False, "sin-tasa")
        leer_hz, _ = _tasa_del_camino(self._device)
        hz = leer_hz(bytes(frame.data))
        if hz is None:
            # Sin saber la tasa no se sabe si el mouse se puede leer entero:
            # se la deja en una que si, o no se sigue.
            hz = await self._arreglar_la_tasa(frame, permiso, avisar)
            if hz is None:
                return Resultado(False, "tasa-ilegible")

        if hz > RATE_MAXIMO_PARA_LEER and self._tasa_original is None:
            permitido = (await permiso(hz) if callable(permiso)
                         else bool(permiso))
            if not permitido:
                return Resultado(False, "tasa-alta")
            avisar(f"{AVISO_TASA_BAJA}|el mouse esta a {hz} Hz, y arriba de "
                   f"{RATE_MAXIMO_PARA_LEER} Hz los bloques largos no llegan "
                   f"(MEDIDO a 2000 y a 8000). La bajo a "
                   f"{RATE_MAXIMO_PARA_LEER} **una sola vez** mientras "
                   f"configuras, y te devuelvo los {hz} al terminar")
            quedo = await poner_tasa(self._device, RATE_MAXIMO_PARA_LEER)
            if quedo != RATE_MAXIMO_PARA_LEER:
                return Resultado(False, "no-pude-bajar-la-tasa")
            self._tasa_original = hz
            # **La tasa es parte del estado, pero es lo UNICO que cambio.**
            # Tirar el cache entero aca costaria una lectura completa -o sea
            # minutos- cada vez que la tasa se devuelve y se vuelve a pedir
            # prestada, que es justo lo que pasa cuando la gracia se vence
            # mientras alguien mira la pantalla. Se refrescan los dos bloques
            # que se movieron: el de rate y el perfil, que lo embebe.
            if self._estado is not None:
                await self._refrescar(p.CMD_REPORT_RATE)
                await self._refrescar(p.CMD_PROFILE)

        extra = tuple(sorted({*self._macros_extra, *macros_extra}))
        if self._estado is None or forzar_lectura or extra != self._macros_extra:
            avisar(AVISO_RESPALDO)
            estado = await leer_estado(
                self._device, nodo=self._nodo, macros_extra=extra,
                al_leer=self._al_leer, al_reintentar=self._al_reintentar,
                al_cortar=self._al_cortar)
            if self._tasa_original is not None:
                estado[CLAVE_TASA_BAJADA] = self._tasa_original
            if self._tasa_arreglada_desde is not None:
                estado[CLAVE_TASA_ARREGLADA] = self._tasa_arreglada_desde
            if incompletos(estado):
                # **No se cachea un respaldo incompleto.** Seria peor que no
                # tener ninguno: la proxima escritura lo usaria de red creyendo
                # que esta entera.
                return Resultado(False, "respaldo-incompleto", antes=estado,
                                 tasa_bajada_desde=self._tasa_original)
            self._estado = estado
            self._macros_extra = extra

        if self._tasa_original is not None:
            self._marcar_la_tasa(self._tasa_original)
        return Resultado(True, "listo", antes=self._estado,
                         tasa_bajada_desde=self._tasa_original)

    async def _arreglar_la_tasa(self, frame, permiso: PermisoDeTasa,
                                avisar) -> int | None:
        """Deja en 1000 Hz una tasa que no se entiende. None si no se pudo.

        **Un mouse con un byte raro no puede dejar al programa afuera**: sin
        esto la ventana no leia nada y la unica salida era la terminal. Paso
        el 2026-10-04 con `01 02 fd 00 00 00 00` -el mouse reportando a 8000
        Hz-, y de ahi se salio a mano con `cambiar-rate.py`.

        Es el camino de un solo comando de `poner_tasa()` -escribir, releer,
        insistir- con otro bloque: el de `estructuras.arreglar_report_rate()`,
        que sale siempre de los bytes que el driver oficial escribio. Lo que
        **no** arregla:

          * una lectura que vino mal (el complemento no cierra): eso no es lo
            que el mouse tiene guardado, y escribir encima seria el incidente
            del sangrado otra vez;
          * nada, si quien llama no dio el permiso entero. Un `permiso` que
            pregunta por los Hz no tiene aca Hz por los que preguntar.

        **La tasa queda en 1000 y no vuelve**: no hay una anterior que
        devolver, asi que `_tasa_original` no se toca. Se dice por
        `AVISO_TASA_ARREGLADA` y el bloque que habia viaja en el estado
        (`CLAVE_TASA_ARREGLADA`).
        """
        leido = bytes(frame.data)
        if permiso is not True or not estructuras.report_rate_coherente(leido):
            return None
        por_cable = via_de(self._device) == dispositivos.VIA_CABLE
        bloque = estructuras.arreglar_report_rate(leido, por_cable=por_cable)
        for _ in range(INTENTOS_DE_TASA):
            await self._device.escribir(
                bytes([p.CMD_REPORT_RATE, frame.sub]) + bloque)
            await asyncio.sleep(p.WRITE_BLOCK_PAUSE_SOFT)
            despues = await self._device.leer(p.CMD_REPORT_RATE)
            if despues is not None and bytes(despues.data) == bloque:
                break
        else:
            return None
        self._tasa_arreglada_desde = leido.hex()
        # Lo que hubiera cacheado se leyo con la tasa de antes en el bloque.
        self._estado = None
        avisar(f"{AVISO_TASA_ARREGLADA}|{aviso_de_tasa_arreglada(leido[1])}")
        leer_hz, _ = _tasa_del_camino(self._device)
        return leer_hz(bloque)

    # --- escribir ---------------------------------------------------------

    async def escribir(self, *, cmd: int, codificar: Codificar,
                       confirmar: Confirmar, macro_id: int | None = None,
                       macros_extra=(),
                       idempotente: bool | Callable[[], bool] | None = None,
                       permiso: PermisoDeTasa = True,
                       relectura: str = RELECTURA_LO_ESCRITO,
                       al_guardar=None) -> Resultado:
        """Escribe un campo apoyandose en lo que la sesion ya sabe.

        Es `aplicar()` con el respaldo puesto y sin tocar la tasa: la sesion ya
        la tiene baja. Todo lo demas -codificar, confirmar, escribir, releer y
        juzgar- es el mismo camino, con el mismo test que lo compara contra el
        CLI.
        """
        # **La tasa no pasa por la Etapa 3**, y no es un atajo: ver
        # `_escribir_tasa`. Va antes de `preparar()` porque no necesita ni el
        # respaldo completo ni la tasa baja.
        if cmd == p.CMD_REPORT_RATE:
            return await self._escribir_tasa(codificar=codificar,
                                             confirmar=confirmar)
        # Antes de `preparar()`, que leeria el mouse entero para nada.
        if cmd == p.CMD_MACRO and not lee_macros(self._device):
            return Resultado(False, "macro-sin-relectura")

        prep = await self.preparar(macros_extra=macros_extra, permiso=permiso)
        if not prep.ok:
            return prep

        resultado = await aplicar(
            self._device, cmd=cmd, codificar=codificar, confirmar=confirmar,
            nodo=self._nodo, macro_id=macro_id,
            macros_extra=self._macros_extra,
            # **La tasa no se toca aca.** Ya la bajo `preparar()`, y es suya
            # hasta `soltar()`: si `aplicar()` la bajara, su `finally` la
            # devolveria despues de cada campo, que es justo lo que dejaba seis
            # reconfiguraciones de radio para tres cambios.
            bajar_la_tasa=False,
            idempotente=idempotente,
            respaldo=self._estado,
            relectura=relectura,
            al_leer=self._al_leer, al_reintentar=self._al_reintentar,
            al_cortar=self._al_cortar, al_avisar=self._al_avisar,
            al_guardar=al_guardar)
        self._anotar(resultado)
        return resultado

    async def _escribir_tasa(self, *, codificar: Codificar,
                            confirmar: Confirmar) -> Resultado:
        """La tasa se escribe como `driver/scripts/cambiar-rate.py`, no como el resto.

        **Y no es aflojar una baranda: es que la Etapa 3 no puede verificar
        este campo.** El paso 1 exige el respaldo completo de los siete
        comandos y el paso 6 una relectura; las dos necesitan el mouse a
        1000 Hz o menos, que es justo lo que este comando cambia. Pedirle a la
        Etapa 3 que escriba 4000 Hz es pedirle que verifique el cambio con una
        herramienta que el cambio acaba de romper: la relectura del perfil no
        llega a esa tasa y el veredicto sale `relectura-incompleta` aunque la
        escritura haya entrado perfecta.

        Peor todavia con una sesion abierta: el paso 0 baja la tasa y el
        `finally` la devuelve, asi que **escribir la tasa por ese camino se
        deshacia solo** y encima daba "salio bien" (estaba anotado como
        abierto en la nota de retomar; bitacora, "La nota de retomar, archivada
        entera"). Aca se cierra por la salida que esa misma nota proponia:
        que la tasa se escriba siempre por el camino de un solo comando.

        Lo que **si** se conserva, y aca mas que en `cambiar-rate.py`:

          * **el respaldo completo sigue siendo obligatorio.** La herramienta
            de terminal se lo salta porque a 8000 Hz no se puede tomar; aca ya
            no es el caso, porque `preparar()` dejo el mouse a 1000 antes de
            llegar a esta linea. La baranda del paso 1 vale igual;
          * la confirmacion;
          * y la verificacion por **relectura**, nunca por el acuse del dongle.
        """
        prep = await self.preparar()
        if not prep.ok:
            return prep

        frame = await self._device.leer(p.CMD_REPORT_RATE)
        if frame is None:
            return Resultado(False, "no-contesto")
        leido = bytes(frame.data)
        datos = bytes(codificar(leido))
        hz = estructuras.report_rate_de(datos)
        if hz is None:
            return Resultado(False, "tasa-desconocida", bloque=datos)
        # **La mutacion dice cuantos Hz; el camino dice que nibble.** Quien
        # codifica no sabe por donde se escribe, y por cable el nibble alto es
        # la tasa de la radio: se rearma sobre el bajo, desde lo leido.
        _, escribir = _tasa_del_camino(self._device)
        try:
            datos = bytes(escribir(leido, hz=hz))
        except ValueError:
            return Resultado(False, "tasa-desconocida", bloque=datos)
        bloque = bytes([p.CMD_REPORT_RATE, frame.sub]) + datos
        if not await confirmar(bloque, trama_de(self._device, bloque)):
            return Resultado(False, "sin-confirmar", bloque=bloque)

        # **La deuda se cancela ANTES de escribir, y es lo que arregla el bug
        # que `dev/models/attackshark-x8pro/docs/SIGUIENTE-SESION.md` tenia anotado como abierto.** La tasa
        # que el usuario acaba de elegir reemplaza a la que habia: si quedara
        # anotada, `soltar()` restauraria despues los 8000 Hz de los que
        # `preparar()` bajo y el cambio se desharia solo, con el veredicto
        # diciendo que salio bien. Va antes del `datos == leido` porque el caso
        # "estaba a 8000, pedi 1000" llega justo ahi: `preparar()` ya lo dejo
        # en 1000, asi que no hay nada que escribir **y sin embargo hay algo
        # que cambiar**, que es a donde se vuelve.
        tasa_que_se_debia = self._tasa_original
        self._tasa_original = None

        if datos == leido:
            # Su dueño eligio la tasa que ya estaba puesta: el bloque de rate
            # deja de ser prestado.
            self._marcar_la_tasa(None)
            return Resultado(True, "sin-diferencias", aplicada=True,
                             bloque=bloque, despues=self._estado,
                             tasa_bajada_desde=tasa_que_se_debia)

        quedo = await poner_tasa(self._device, hz)
        if quedo != hz:
            # No entro: se vuelve a deber lo de antes, porque el mouse sigue
            # donde estaba y esa tasa sigue sin ser la que su dueño quiere.
            self._tasa_original = tasa_que_se_debia
            return Resultado(False, "no-entro-la-tasa", bloque=bloque,
                             despues=self._estado)

        if hz > RATE_MAXIMO_PARA_LEER:
            # **Arriba de 1000 el perfil no se relee** (MEDIDO), y
            # `_refrescar()` tiraria el cache entero: la ventana se quedaba con
            # un estado viejo que no sabia de la tasa nueva. `poner_tasa()` ya
            # la verifico releyendola. El bloque en memoria es el leido con la
            # tasa baja y el mouse esta en otra, que es lo mismo que despues de
            # `soltar()`: se marca. La proxima escritura pasa por `preparar()`,
            # que baja la tasa y refresca el rate y el perfil antes de usarlo.
            self._marcar_la_tasa(hz)
        else:
            await self._refrescar(p.CMD_REPORT_RATE)
            self._marcar_la_tasa(None)
        return Resultado(True, "tasa-puesta", aplicada=True, bloque=bloque,
                         despues=self._estado)

    async def refrescar(self, *cmds: int) -> dict | None:
        """Relee esos bloques, los deja en el estado cacheado y lo devuelve.

        Para lo que el mouse cambia solo y avisa: el nivel de dpi, con el
        boton. Devuelve None si no habia estado, o si algun bloque no contesto
        y el cache se invalido.
        """
        for cmd in cmds:
            await self._refrescar(cmd)
        return self._estado

    async def _refrescar(self, cmd: int) -> None:
        """Vuelve a leer un bloque -y el perfil, que lo embebe- y los cachea.

        Si alguno no contesta, el cache se invalida entero: mejor releer el
        mouse que seguir mostrando un bloque que ya no se sabe si es el de
        ahora.

        **El perfil va con el, porque el mouse lo mueve con el.** El perfil
        completo acompaña a todo cambio de rate, dpi, luz y botones (MEDIDO
        sobre los respaldos versionados), asi que refrescar el bloque solo deja
        el cache diciendo dos cosas distintas de los mismos bytes: el rate
        nuevo y, adentro del perfil, el viejo. Lo destapo `incoherencias()`
        sobre el camino de la tasa, que era el unico que no relee el perfil
        -`aplicar()` ya lo hace, por `RELECTURA_LO_ESCRITO`-.
        """
        if self._estado is None:
            return
        cmds = [cmd]
        if cmd in dispositivos.activo().perfil_embebe:
            cmds.append(p.CMD_PROFILE)
        for cual in cmds:
            frame = await self._device.leer(cual)
            if frame is None:
                self.invalidar(f"no pude releer {p.CMD_NAMES.get(cual, cual)}")
                return
            self._estado["comandos"][str(cual)] = _entrada(cual, frame)

    def _anotar(self, resultado: Resultado) -> None:
        """Deja el cache en lo que se sepa despues de una escritura."""
        if resultado.despues is not None:
            self._estado = resultado.despues
            # Una relectura completa trae un estado nuevo, sin la marca.
            if self._tasa_original is not None:
                self._marcar_la_tasa(self._tasa_original)
            return
        # Se armo un bloque y no se llego a releer: pudo haber entrado. El
        # unico caso en que se sabe que no se escribio es el "no" de
        # `confirmar`, que corta antes de mandar nada.
        if resultado.bloque is not None and resultado.motivo != "sin-confirmar":
            self.invalidar("una escritura termino sin poder releer el mouse")

    # --- cerrar -----------------------------------------------------------

    async def soltar(self) -> int | None:
        """Devuelve la tasa prestada. Se puede llamar dos veces.

        Devuelve los Hz en que quedo, o None si no habia nada que devolver.
        """
        if self._tasa_original is None:
            return None
        hz = self._tasa_original
        # Se olvida **antes** de escribir: si esto falla o lo cancelan, no
        # puede quedar un segundo intento creyendo que todavia debe algo y
        # mandando otra trama de rate encima.
        self._tasa_original = None
        quedo = await poner_tasa(self._device, hz)
        # **La marca queda**: el bloque de rate en memoria sigue diciendo 1000
        # y el mouse volvio a la suya. Si no volvio, es de donde haya quedado.
        self._marcar_la_tasa(quedo if quedo is not None else hz)
        if self._al_avisar:
            self._al_avisar(
                f"{AVISO_TASA_VUELVE}|tasa devuelta a {quedo} Hz"
                if quedo == hz else
                f"{AVISO_TASA_VUELVE}|OJO: la tasa quedo en {quedo} Hz, no en "
                f"{hz}. Revisala con driver/scripts/cambiar-rate.py")
        return quedo


# --- el despachador de mutaciones -----------------------------------------
#
# **Que bytes escribir para poner un campo en un valor.** Antes
# ese mapeo vivia adentro de `codificar()` en `driver/scripts/primera-escritura.py`,
# atado a los argumentos de una linea de comandos: la interfaz habria tenido
# que reescribirlo entero. Lo marco la auditoria del agente A como G-01, y es la
# misma duplicacion que se cerro entre el CLI y la biblioteca, un nivel
# mas arriba —solo que esta vez se hace **antes** de que existan dos copias.
#
# Las claves son las de `modelo.campos_de()`, que son las que una interfaz ya
# usa para mostrar. Lo que se devuelve es lo que `aplicar()` necesita.

class CampoNoEscribible(Exception):
    """El campo existe pero no se escribe, y se dice por que."""


class FaltaElParametro(ValueError):
    """La opcion existe, pero lleva un dato adentro y ese dato no vino.

    Son exactamente las dos de `estructuras.FUNCIONES_CON_PARAMETRO`: el macro
    -que lleva el id en p2- y el atajo de teclado -modificadores en p1, usage
    en p2-. Las otras 51 funciones de boton se escriben con el nombre solo.

    **Existe para que una interfaz pueda pedir el dato sin parsear el
    mensaje.** Sigue siendo un `ValueError`, asi que a quien ya lo atrapa -el
    CLI- no le cambia nada; lo que agrega es `que` y `ejemplo`, que es lo que
    hace falta para dibujar el campito al lado del desplegable.
    """

    def __init__(self, mensaje: str, *, funcion: str, que: str,
                 ejemplo: str) -> None:
        super().__init__(mensaje)
        #: La funcion que se eligio, como la nombra `FUNCIONES_DE_BOTON`.
        self.funcion = funcion
        #: Que falta, dicho en castellano: "el id del macro".
        self.que = que
        #: Uno valido, para mostrar de ejemplo.
        self.ejemplo = ejemplo


@dataclass(frozen=True)
class Mutacion:
    """Como poner un campo en un valor: que comando, y con que codificador."""

    clave: str
    cmd: int
    codificar: Codificar
    #: Solo para cmd 9, que se lee y se escribe con el id del macro en el byte
    #: 5 y no con el perfil.
    macro_id: int | None = None


def preparar_mutaciones(cambios, *, macro_id: int | None = None
                        ) -> list[Mutacion]:
    """Varias `(clave, valor)` en **una mutacion por comando**.

    Los codificadores de un campo reciben el bloque y devuelven el bloque con
    su byte cambiado, asi que encadenarlos da un bloque con todos los cambios y
    **una sola escritura**. El orden de `cambios` se respeta -importa para la
    tasa, que va ultima (ver `modelo.pendientes`)- y se agrupa por comando sin
    reordenar: dos campos del mismo bloque salen juntos aunque tengan otros en
    el medio.

    **No es solo ahorrar escrituras: es lo unico que saca al mouse de un bloque
    malo.** Cada codificador copia el resto del bloque que recibe, asi que si
    cmd 5 quedo con la hibernacion y la respuesta fuera de rango, escribir un
    campo por vez arrastra el otro y `fuera_de_rango()` lo rechaza -con razon-:
    ninguna escritura de un campo suelto puede arreglarlo. Encadenadas, las dos
    entran en el mismo bloque y el resultado ya esta en rango. Sin esto la
    ventana no tiene salida y hay que ir a `restaurar-bloque.py`.

    Los macros van aparte: uno por `(cmd 9, id)`, porque cada id es otro bloque.
    """
    grupos: dict[tuple[int, int | None], list[Mutacion]] = {}
    for clave, valor in cambios:
        m = preparar_mutacion(clave, valor, macro_id=macro_id)
        grupos.setdefault((m.cmd, m.macro_id), []).append(m)

    salida = []
    for (cmd, mid), ms in grupos.items():
        if len(ms) == 1:
            salida.append(ms[0])
            continue

        def encadenar(datos, ms=ms):
            for m in ms:
                datos = bytes(m.codificar(datos))
            return datos

        salida.append(Mutacion(", ".join(m.clave for m in ms), cmd,
                               encadenar, macro_id=mid))
    return salida


# El boton izquierdo estuvo aca antes. Ahora se escribe, y la
# baranda es otra y vive en `estructuras`: tiene que quedar un clic izquierdo
# en los botones 1 a 5 (`SLOTS_PARA_CLIC_IZQUIERDO`).
# Por que no se escribe cada campo que no se escribe. **Cuantos niveles de dpi
# hay es del modelo**, asi que la lista se arma con el perfil activo y no con un
# ocho escrito aca: con menos niveles sobrarian claves, y con mas faltaria una
# -y un campo sin motivo llegaria al codificador como si fuera escribible-.
# Antes era el dict `NO_ESCRIBIBLES`, armado al importar.
def no_escribibles() -> dict[str, str]:
    """`clave -> por que no se escribe`, para el mouse que esta enfrente."""
    motivo = (
        "los colores de indicador son constantes en las 76 escrituras "
        "capturadas: ningun cliente oficial los movio nunca, asi que no hay "
        "Etapa 2 y escribirlos seria inventar bytes (ver dev/models/attackshark-x8pro/docs/evidencia.md)")
    return {f"color_nivel_{n}": motivo
            for n in range(1, dispositivos.activo().niveles_dpi + 1)}


def _rgb_de(valor) -> tuple[int, int, int]:
    """`"#00ff00"`, `"00ff00"` o `(0, 255, 0)` -> la terna."""
    if isinstance(valor, (tuple, list)):
        if len(valor) != 3:
            raise ValueError(f"un color son tres componentes, no {len(valor)}")
        return tuple(int(x) for x in valor)
    texto = str(valor).strip().lstrip("#")
    if len(texto) != 6:
        raise ValueError(f"{valor!r} no es un color: se escribe `rrggbb`")
    return tuple(int(texto[i:i + 2], 16) for i in (0, 2, 4))


def _accion_de_boton(valor) -> tuple[int, int, int]:
    """El valor de un `boton_*` -> `(codigo, p1, p2)`.

    Acepta el nombre de la funcion a secas (`"adelante"`) y, para las dos que
    llevan parametro, un par: `("macro", 17)` o `("atajo de teclado", "ctrl+c")`.
    El nombre del atajo se resuelve con el mismo codificador que reproduce los
    dos bloques del bus, asi que la interfaz no necesita saber de usages HID.
    """
    parametro = None
    if isinstance(valor, (tuple, list)):
        if len(valor) != 2:
            raise ValueError("una accion de boton es un nombre, o un par "
                             "(nombre, parametro)")
        valor, parametro = valor
    nombre = str(valor).strip().lower()
    codigo = next((c for c, n in estructuras.FUNCIONES_DE_BOTON.items()
                   if n.lower() == nombre), None)
    if codigo is None:
        raise ValueError(
            f"{valor!r} no es una funcion de boton. Hay "
            f"{len(estructuras.FUNCIONES_DE_BOTON)}; se listan con "
            "estructuras.FUNCIONES_DE_BOTON")
    if codigo == estructuras.FUNCION_MACRO:
        if parametro is None:
            raise FaltaElParametro(
                "la funcion 'macro' necesita el id del macro: ('macro', 17)",
                funcion=nombre, que="el id del macro", ejemplo="17")
        try:
            macro_id = int(parametro)
        except (TypeError, ValueError):
            # Sin esto salia el mensaje de Python -"invalid literal for
            # int()"-, que no dice que se estaba pidiendo un id de macro.
            raise ValueError(f"el id del macro es un numero, y {parametro!r} "
                             "no lo es") from None
        return codigo, 0, macro_id
    if codigo == estructuras.FUNCION_ATAJO:
        if parametro is None:
            raise FaltaElParametro(
                "la funcion 'atajo de teclado' necesita el atajo: "
                "('atajo de teclado', 'ctrl+c')",
                funcion=nombre, que="el atajo de teclado", ejemplo="ctrl+c")
        p1, p2 = estructuras.atajo_desde_texto(str(parametro))
        return codigo, p1, p2
    if parametro is not None:
        raise ValueError(f"la funcion {nombre!r} no lleva parametro")
    return codigo, 0, 0


#: Lo que se le puede cambiar a un macro, con el mismo corte que el CLI: el
#: **disparo** (modo y contador) por un lado y la **lista de eventos** por el
#: otro. Son dos cosas distintas del mismo bloque y se escriben por separado
#: —si algo sale raro con las dos juntas no se sabe cual fue—, que es la misma
#: regla que `primera-escritura.py` hace cumplir con un `return 2`.
CLAVES_DE_MACRO = ("macro_modo", "macro_repeticiones", "macro_eventos")


def _mutacion_de_macro(clave: str, valor, macro_id: int | None) -> Mutacion:
    """Las tres de cmd 9, que necesitan el id y por eso van aparte.

    El id no es un detalle: cmd 9 se lee con el id del macro en el byte 5 y no
    con el perfil (MEDIDO), asi que sin el el mouse devuelve un
    bloque vacio y no hay nada que reescribir. Es la misma exigencia que el CLI
    hace con `--macro-id`.
    """
    e = estructuras
    if macro_id is None:
        raise ValueError(
            f"{clave} necesita el id del macro: cmd 9 se lee con el id en el "
            "byte 5, no con el perfil, y sin el el mouse devuelve un bloque "
            "vacio. Los ids que tiene el mouse salen de driver/scripts/respaldar.py")
    if not e.MACRO_ID_MIN <= macro_id <= e.MACRO_ID_MAX:
        raise ValueError(f"macro id {macro_id} fuera de {e.MACRO_ID_MIN}.."
                         f"{e.MACRO_ID_MAX}, que es el rango del mouse")

    if clave == "macro_eventos":
        eventos = (e.eventos_desde_texto(valor) if isinstance(valor, str)
                   else [e.normalizar_evento(ev) for ev in valor])
        # El rango y el **sitio** se validan aca, antes de tocar el mouse:
        # `armar_macro()` hace el mismo trabajo que el codificador y protesta
        # por los dos. Hacer esperar medio minuto de respaldo para despues
        # decir que la lista no entra es la clase de error que el CLI ya evita.
        e.armar_macro(macro_id, eventos)
        return Mutacion(clave, p.CMD_MACRO,
                        lambda d: e.escribir_eventos_macro(d, eventos),
                        macro_id=macro_id)

    if clave == "macro_modo":
        modo = int(valor)
        if modo not in e.MACRO_MODOS:
            raise ValueError(
                f"modo {modo}: los unicos tres observados en el bus son "
                + ", ".join(f"{k} ({v})" for k, v in e.MACRO_MODOS.items()))
        return Mutacion(clave, p.CMD_MACRO,
                        lambda d: e.escribir_macro(d, modo=modo),
                        macro_id=macro_id)

    # `macro_repeticiones`. El byte **solo es un contador en el modo 0**: en
    # los otros dos va forzado a 1, asi que pedir un numero ahi seria pedir
    # algo que el bloque no puede expresar. Escribirlo implica el modo 0, que
    # es lo mismo que el CLI exige pidiendo `--modo 0 --repeticiones N`.
    n = int(valor)
    if not e.MACRO_REPETICIONES_MIN <= n <= e.MACRO_REPETICIONES_MAX:
        raise ValueError(f"repeticiones {n} fuera de "
                         f"{e.MACRO_REPETICIONES_MIN}.."
                         f"{e.MACRO_REPETICIONES_MAX}")
    return Mutacion(clave, p.CMD_MACRO,
                    lambda d: e.escribir_macro(
                        d, modo=e.MACRO_MODO_CON_CONTADOR, repeticiones=n),
                    macro_id=macro_id)


def preparar_mutacion(clave: str, valor, *, macro_id: int | None = None) -> Mutacion:
    """Que hay que escribirle al mouse para poner `clave` en `valor`.

    `clave` es la de `modelo.campos_de()`. Lo que vuelve se le pasa a
    `aplicar()` tal cual:

        m = sesion.preparar_mutacion("lod", 2)
        r = await sesion.aplicar(device, cmd=m.cmd, codificar=m.codificar, ...)

    Las tres claves de `CLAVES_DE_MACRO` son las unicas que **no** salen de
    `campos_de()`: un macro no es un campo escalar y va aparte, con su id
    (`preparar_mutacion("macro_modo", 2, macro_id=17)`). La `Mutacion` que
    vuelve lleva el `macro_id` adentro, que es lo que `aplicar()` necesita
    para leer cmd 9 -el unico comando que no se lee con el perfil-.

    **No toca el mouse y no decide politicas**: no pide confirmacion, no mira
    la tasa y no sabe si el valor es el que ya esta. Eso lo hace `aplicar()`,
    que ademas infiere la idempotencia sola (ver `referencia_idempotente`).
    """
    e = estructuras
    sin_escritura = no_escribibles()
    if clave in sin_escritura:
        raise CampoNoEscribible(f"{clave}: {sin_escritura[clave]}")

    def mut(cmd, fn, **kw):
        return Mutacion(clave, cmd, fn, macro_id=kw.get("macro_id"))

    if clave in CLAVES_DE_MACRO:
        return _mutacion_de_macro(clave, valor, macro_id)

    if clave == "tasa":
        hz = int(valor)
        return mut(p.CMD_REPORT_RATE,
                   lambda d: e.escribir_report_rate(d, hz=hz))

    if clave.startswith("dpi_nivel_"):
        nivel, dpi = int(clave.removeprefix("dpi_nivel_")), int(valor)
        # `escribir_nivel_dpi` devuelve `(bloque, dpi efectivo)`: el mouse
        # cuantiza, asi que lo que se pide no siempre es lo que queda.
        return mut(p.CMD_DPI, lambda d: e.escribir_nivel_dpi(d, nivel, dpi)[0])

    if clave == "nivel_activo":
        nivel = int(valor)
        return mut(p.CMD_DPI, lambda d: e.escribir_nivel_activo(d, nivel=nivel))

    if clave in ("lod", "ripple", "angle_snapping", "motion_sync"):
        # Los cuatro viven en los mismos dos bytes de cmd 4 y se escriben con
        # el mismo codificador, uno por vez.
        #
        # **El LOD entra en milimetros**, que es como lo muestra `modelo.py` y
        # como lo piensa quien lo usa; el codificador quiere el codigo crudo
        # (0 = 1 mm, 1 = 2 mm). Traducirlo es justo lo que la interfaz no tiene
        # que reimplementar.
        v = e.lod_desde_mm(valor) if clave == "lod" else bool(valor)
        return mut(p.CMD_DPI, lambda d: e.escribir_parametros_sensor(
            d, **{clave: v}))

    if clave == "reposo":
        minutos = float(valor)
        return mut(p.CMD_LIGHTING,
                   lambda d: e.escribir_reposo_ligero(d, minutos=minutos))

    if clave == "hibernacion":
        minutos = int(valor)
        return mut(p.CMD_LIGHTING, lambda d: e.escribir_parametros_luz(
            d, hibernacion=minutos))

    if clave == "respuesta":
        # **Entra el numero que se ve, no el byte.** El byte viaja a la mitad
        # (`KeyResponseTime/2`), y antes esto tomaba el byte
        # -igual que `--respuesta` del CLI, que lo documenta-. Con eso,
        # escribir el valor que `modelo.campos_de()` acababa de mostrar lo
        # DUPLICABA: 8 leido, 8 escrito, 16 releido. Leer y volver a escribir
        # movia el campo, que es exactamente lo que este proyecto le reprocha
        # a la pagina oficial, y ademas la mitad del rango publicado (26..50)
        # reventaba contra el rango del byte.
        #
        # El criterio es el mismo que el del LOD, que entra en milimetros: la
        # unidad de este despachador es la de `modelo.py`, que es la que ve una
        # persona. El CLI sigue tomando el byte y `test_el_despachador_y_el_cli
        # _dan_lo_mismo` compara 20 contra `--respuesta 10`, con la conversion
        # a la vista.
        ui = float(valor)
        if ui != int(ui) or int(ui) % e.RESPUESTA_UI_PASO:
            raise ValueError(
                f"respuesta {valor}: va de a {e.RESPUESTA_UI_PASO} "
                f"({e.RESPUESTA_UI_MIN}..{e.RESPUESTA_UI_MAX}), porque el byte "
                "es la mitad y tiene que dar entero")
        if not e.RESPUESTA_UI_MIN <= ui <= e.RESPUESTA_UI_MAX:
            raise ValueError(
                f"respuesta {valor} fuera de {e.RESPUESTA_UI_MIN}.."
                f"{e.RESPUESTA_UI_MAX}, que es el rango del slider del X8 Pro")
        byte = int(ui) // 2
        return mut(p.CMD_LIGHTING, lambda d: e.escribir_parametros_luz(
            d, respuesta=byte))

    if clave == "color":
        rgb = _rgb_de(valor)
        return mut(p.CMD_LIGHTING, lambda d: e.escribir_color_luz(d, rgb))

    if clave == "rueda":
        # "derecho" es como lo escribe el soft nativo; la pagina lo deja al
        # reves y por eso el campo existe (ver modelo.NOTA_RUEDA).
        orden = (e.RUEDA_CORRECTA if str(valor).strip().lower().startswith("d")
                 else e.RUEDA_COMO_LA_WEB)
        return mut(p.CMD_BUTTONS, lambda d: e.escribir_rueda(d, orden=orden))

    if clave == "intercambiar_clics":
        # `modelo.ACCION_INTERCAMBIAR_CLICS`: los botones 1 y 2, en un bloque.
        # El valor no importa -es un boton que se aprieta-, y la baranda del
        # clic izquierdo la cuida `intercambiar_botones()` como a cualquier otra
        # escritura de cmd 8.
        return mut(p.CMD_BUTTONS,
                   lambda d: e.intercambiar_botones(d, a=1, b=2))

    if clave.startswith("boton_"):
        fisico = clave.removeprefix("boton_").replace("_", "-")
        slot = e.BOTONES_POR_NOMBRE.get(fisico)
        if slot is None:
            raise ValueError(f"{clave}: no hay un boton {fisico!r}. Hay "
                             + ", ".join(sorted(e.BOTONES_POR_NOMBRE)))
        codigo, p1, p2 = _accion_de_boton(valor)
        return mut(p.CMD_BUTTONS, lambda d: e.escribir_boton(
            d, slot=slot, codigo=codigo, p1=p1, p2=p2))

    raise ValueError(f"{clave!r} no es un campo escribible del modelo. Los que "
                     "hay salen de modelo.campos_de(), con escribible=True")


# --- lo que el mouse avisa solo -------------------------------------------
#
# **La bateria no se pide: llega.** No viaja en el Report ID 4 -el canal de
# comandos- sino en reportes espontaneos del Report ID 3, cada 2-4 s. Por eso
# `leer_estado()` no la trae y nunca la va a traer: no hay nada que preguntar.
#
# Antes esto solo lo miraba `backend.py`, o sea el puente, asi
# que una aplicacion propia no tenia de donde sacar el indicador de bateria.
# Lo marco la auditoria del agente A como G-03.
#
# **Y con el mouse enchufado por cable a la PC no llega ni un latido** (MEDIDO
#: 32 s de silencio, entre dos tramos que latian cada 2,00 s).
# Una interfaz que muestre bateria tiene que distinguir "no llegan novedades"
# de "la bateria sigue siendo la de hace un rato": el dongle sigue en el bus y
# el puente no ve ninguna desconexion, simplemente el mouse dejo de hablar por
# radio. Del cargador, en cambio, llegan igual, y por eso se pudo medir la
# carga.

@dataclass(frozen=True)
class Novedad:
    """Algo que el mouse avisa sin que nadie se lo pida (Report ID 3)."""

    #: `"bateria"`, `"nivel-dpi"` o `"desconocida"`.
    tipo: str
    crudo: bytes
    device_id: int = 0
    #: Porcentaje, solo en `"bateria"`.
    bateria: int | None = None
    #: El byte de estado que acompaña al nivel, crudo. Se sigue exponiendo
    #: asi -aunque ahora tenga lectura- porque el `2` del bundle nunca
    #: aparecio y no hay con que descartar otros valores.
    estado_bateria: int | None = None
    #: Si el mouse esta cargando. **MEDIDO**: el byte vale 3 con
    #: el cargador puesto y 1 sin el, en cuatro transiciones seguidas, con el
    #: LED morado confirmandolo por fuera del protocolo (ver
    #: `p.BATTERY_CHARGING`). Es None para cualquier otro valor -incluido el
    #: `2` "desconocido" del bundle-: no medimos que significan, y decir False
    #: ahi seria afirmar algo que nadie vio.
    cargando: bool | None = None
    #: Nivel de dpi al que el mouse acaba de cambiar, 1-based. Solo en
    #: `"nivel-dpi"`, y es el aviso que dio la verificacion mas independiente
    #: del proyecto: el firmware escribiendo un campo y nosotros leyendolo.
    nivel_dpi: int | None = None


def novedad_de(datos: bytes) -> Novedad | None:
    """Decodifica un reporte espontaneo. `None` si es demasiado corto.

    Los dos formatos estan confirmados escuchando el hardware (ver
    `protocol.NOTIF_*`):

        08 40 01 64   presencia: [deviceId, tipo, estadoBateria, nivel]
        08 10 03      cambio de dpi: [deviceId, tipo, nivel]

    La notificacion de dpi son 3 bytes, no 4 (MEDIDO, `evidencia.md`): el `00`
    final que se penso ver antes era del reenvio de 6 bytes del bundle, nunca
    del Input Report crudo.

    El estadoBateria vale 1 a bateria y 3 cargando (MEDIDO, `p.BATTERY_*`).
    """
    if len(datos) < 3:
        return None
    device_id, tipo = datos[0], datos[1]
    if tipo in (p.NOTIF_PRESENCIA, p.NOTIF_PRESENCIA_ALT):
        if len(datos) < 4:
            return None
        estado = datos[2]
        cargando = {p.BATTERY_CHARGING: True,
                    p.BATTERY_DISCHARGING: False}.get(estado)
        return Novedad("bateria", bytes(datos), device_id,
                       bateria=datos[3], estado_bateria=estado,
                       cargando=cargando)
    if tipo == p.NOTIF_DPI:
        return Novedad("nivel-dpi", bytes(datos), device_id,
                       nivel_dpi=datos[2])
    return Novedad("desconocida", bytes(datos), device_id)


def nivel_dpi_de(estado: dict) -> int | None:
    """El nivel de dpi en uso segun el estado, 1-based como el de `Novedad`.

    Para saber si un estado ya trae el cambio que el mouse aviso: se compara
    contra `Novedad.nivel_dpi`. None si el estado no trae el bloque de dpi.
    """
    bloque = estado.get("comandos", {}).get(str(p.CMD_DPI))
    if bloque is None:
        return None
    campos = estructuras.decodificar(p.CMD_DPI, bytes.fromhex(bloque["datos"]))
    return None if campos is None else campos.get("Current_Dpi_level_flag")


def escuchar_novedades(device, al_haber: Callable[[Novedad], None]) -> None:
    """Llama a `al_haber(novedad)` cada vez que el mouse avise algo.

    Es lo que le falta a una interfaz para tener el indicador de bateria vivo.
    No pide nada ni escribe nada: solo mira lo que ya esta llegando.

    **Sirve tambien para enterarse de lo que el usuario hace con el mouse**:
    si cicla el dpi con su boton, llega una novedad `"nivel-dpi"`. Una interfaz
    que muestre el nivel activo deberia escucharla, porque si no queda
    mostrando un valor viejo sin que nadie se entere.
    """
    def _reenviar(datos: bytes) -> None:
        novedad = novedad_de(datos)
        if novedad is not None:
            al_haber(novedad)

    device.on_estado_mouse = _reenviar
