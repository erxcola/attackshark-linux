#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Las barandas del proyecto, verificadas sin tocar el hardware.

Cada test de aca corresponde a un hallazgo de auditoria (los IDs H-xx son los
de dev/models/attackshark-x8pro/docs/evidencia.md y los I-xx los de dev/models/attackshark-x8pro/docs/evidencia.md).
La idea es que si alguien las saca sin querer, esto se ponga rojo.

    $ python3 driver/tests/salvaguardas.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# **Los tests no tocan las carpetas de quien los corre**: algunos scripts piden
# la de respaldos al importarse, y una prueba no escribe en el HOME de nadie.
import os  # noqa: E402
import tempfile as _tempfile  # noqa: E402
_CASA_DE_PRUEBA = _tempfile.mkdtemp(prefix="linshark-tests-")
os.environ["XDG_CONFIG_HOME"] = f"{_CASA_DE_PRUEBA}/config"
os.environ["XDG_STATE_HOME"] = f"{_CASA_DE_PRUEBA}/state"

from websockets.asyncio.client import connect  # noqa: E402
from websockets.exceptions import ConnectionClosed  # noqa: E402

from linshark import estructuras as est  # noqa: E402
from linshark import protocol as p  # noqa: E402
from linshark import server  # noqa: E402
from linshark.backend import HidrawBackend, Mode, StubBackend  # noqa: E402
from linshark.device import Device, Frame  # noqa: E402
from linshark.hidraw import HidrawChannel  # noqa: E402

PORT = 10187  # distinto al real y al de simula_pagina.py

# Capturado del hardware (dev/models/attackshark-x8pro/docs/bitacora.md), con checksum bueno.
RESPUESTA_VERSION = bytes.fromhex("040d000b0808008301050000b5")
ESTADO_OCUPADO = bytes.fromhex("0406c30000cd")
ESTADO_ACEPTADO = bytes.fromhex("0406c00100cb")
# El acuse de escritura, tal cual sale en las 93 escrituras del driver oficial
# que hay en dev/models/attackshark-x8pro/docs/capturas-w/ (ver el comentario de ST_ESCRITURA_OK en
# device.py). El NAK sale de dev/models/attackshark-x8pro/docs/bitacora.md: cuerpo `06 c2 00`.
ESTADO_ESCRITURA_OK = bytes.fromhex("0406c10100cc")
ESTADO_NAK = bytes.fromhex("0406c20000cc")


class CanalFalso:
    """Se hace pasar por HidrawChannel y contesta un guion escrito a mano."""

    def __init__(self, guion):
        # guion: lista de listas [(retraso, bytes), ...], una por escritura.
        self.guion = list(guion)
        self.escrituras: list[bytes] = []
        self.device: Device | None = None
        self.solo_lectura = False

    def write_frame(self, frame: bytes) -> None:
        self.escrituras.append(frame)
        if not self.guion:
            return
        loop = asyncio.get_running_loop()
        for retraso, datos in self.guion.pop(0):
            loop.call_later(retraso, self.device.alimentar, datos)


# --- H-02 / I-05: un comando sin plantilla no puede tumbar nada -------------

def test_comando_sin_sub(fallos: list[str]) -> None:
    if p.CMD_WAKEUP in p.READ_SUB:
        fallos.append("CMD_WAKEUP volvio a READ_SUB sin plantilla del binario")
    try:
        p.build_read_frame(p.CMD_WAKEUP)
    except p.ComandoSinSub:
        pass
    except Exception as exc:  # noqa: BLE001
        fallos.append(f"build_read_frame levanto {type(exc).__name__}, "
                      "esperaba ComandoSinSub")
    else:
        fallos.append("build_read_frame invento una trama para CMD_WAKEUP")


async def test_leer_sin_sub_no_revienta(fallos: list[str]) -> None:
    canal = CanalFalso([])
    dev = Device(canal)
    canal.device = dev
    try:
        frame = await dev.leer(p.CMD_WAKEUP)
    except Exception as exc:  # noqa: BLE001
        fallos.append(f"device.leer(CMD_WAKEUP) levanto {type(exc).__name__}")
        return
    if frame is not None:
        fallos.append("device.leer(CMD_WAKEUP) devolvio algo")
    if canal.escrituras:
        fallos.append("device.leer(CMD_WAKEUP) igual escribio al mouse")


# --- H-05: el 0xC3 del dongle no cuesta el timeout entero ------------------

async def test_ocupado_reintenta_rapido(fallos: list[str]) -> None:
    # Primera escritura: el dongle dice "ocupado". Segunda: contesta bien.
    canal = CanalFalso([
        [(0.01, ESTADO_OCUPADO)],
        [(0.01, ESTADO_ACEPTADO), (0.05, RESPUESTA_VERSION)],
    ])
    dev = Device(canal)
    canal.device = dev
    t0 = time.monotonic()
    frame = await dev.leer(p.CMD_VERSION)
    tardanza = time.monotonic() - t0

    if frame is None:
        fallos.append("no llego la respuesta despues del 0xC3")
        return
    if not frame.checksum_ok:
        fallos.append("la respuesta de version no valida el checksum")
    # Antes esto esperaba el timeout completo (3.0 s) por cada 0xC3.
    if tardanza > 1.0:
        fallos.append(f"el 0xC3 costo {tardanza:.2f} s; se volvio a esperar "
                      "el timeout en vez de reintentar")
    if len(canal.escrituras) != 2:
        fallos.append(f"{len(canal.escrituras)} escrituras, esperaba 2")


# --- H-03 / I-08: en listen el canal no puede escribir ---------------------

def test_canal_solo_lectura(fallos: list[str]) -> None:
    canal = HidrawChannel(Path("/dev/null"), solo_lectura=True)
    canal._fd = -1  # no se llega a usar: la guarda salta antes
    try:
        canal.write_frame(b"\x04\x0c\xa0\x0b\x08")
    except PermissionError:
        pass
    except Exception as exc:  # noqa: BLE001
        fallos.append(f"write_frame en solo lectura levanto {type(exc).__name__}")
    else:
        fallos.append("un canal de solo lectura dejo escribir")


# --- H-08: el modo full no se puede pedir ----------------------------------

# --- Lo que el puente OFRECE es menos que lo que el backend acepta, y no es
# un descuido. Por el puente escribe la **pagina oficial**, no nosotros, y ya
# esta medido lo que hace al conectarse: reescribe el dpi sola (I-W12, seis
# veces) y escribe el bloque de botones con los slots de la rueda al reves, que
# **invierte el scroll**(girandola). Cmd 5 y cmd 8 pasaron la
# Etapa 2 y se escriben con `driver/scripts/primera-escritura.py`, que pide un campo
# por corrida y confirma; por el puente no se exponen.

def test_el_puente_ofrece_menos_que_writable(fallos: list[str]) -> None:
    from linshark import cli
    ofrecidos = set(cli.ESCRIBIBLES.values())
    if not ofrecidos < p.WRITABLE:
        fallos.append("cli.ESCRIBIBLES dejo de ser un subconjunto ESTRICTO de "
                      "WRITABLE: el puente no deberia ofrecer todo lo que el "
                      "backend acepta")
    for cmd, por_que in ((p.CMD_LIGHTING, "cmd 5 lleva los dos temporizadores "
                          "de reposo y tres campos sin significado univoco"),
                         (p.CMD_BUTTONS, "la pagina escribe la rueda al reves "
                          "y eso invierte el scroll")):
        if cmd in ofrecidos:
            fallos.append(f"el puente ofrece escribir cmd {cmd}: {por_que}")


# --- N-01: el error del CLI dice el techo del CLI, no el del backend -------
# `backend.py` nombra `WRITABLE - SIN_CAMINO_EN_EL_BACKEND` -rate, dpi, luz y
# botones-, que es correcto para quien usa `HidrawBackend` desde codigo propio.
# Pero el CLI acepta solo `cli.ESCRIBIBLES`, asi que ese mensaje mandaba a
# pedir dos comandos que argparse rechaza. Lo marco la auditoria del agente B (N-01)
# en dos pasadas seguidas; la primera se arreglo a medias -se resto macro y no
# el techo del CLI- y por eso volvio a salir.
def test_el_error_del_cli_ofrece_lo_que_el_cli_acepta(fallos: list[str]) -> None:
    from linshark import cli

    args = cli.build_parser().parse_args(["--backend", "hidraw",
                                          "--mode", "full"])
    try:
        cli._construir_backend(args, p.CONN_8K_B, "X8 Pro")
    except ValueError as exc:
        texto = str(exc)
    else:
        fallos.append("el CLI acepto 'full' sin --permitir-escritura")
        return

    # lo que ofrece tiene que ser exactamente lo que argparse deja pedir
    for nombre in cli.ESCRIBIBLES:
        if nombre not in texto:
            fallos.append(f"el error del CLI no ofrece {nombre!r}, que si se "
                          "puede pedir")
    for nombre, cmd in (("iluminacion", p.CMD_LIGHTING),
                        ("botones", p.CMD_BUTTONS)):
        if nombre in texto:
            fallos.append(f"el error del CLI ofrece {nombre!r}, que argparse "
                          "rechaza: manda a pedir algo imposible")

    # y no se cae en lo contrario: prometer menos de lo que hay tampoco sirve,
    # asi que tiene que decir por que los demas no salen por aca.
    if "proposito" not in texto and "propósito" not in texto:
        fallos.append("el error del CLI no dice por que los demas comandos "
                      "escribibles no salen por el puente")


def test_modo_full_no_habilita_nada_solo(fallos: list[str]) -> None:
    """`full` existe desde que la Etapa 2 quedo cumplida, pero no abre nada.

    La baranda ya no es "el modo no se puede construir": es que construirlo
    sin nombrar comandos es un error, que solo se pueden nombrar los que
    pasaron la Etapa 2, y que el default es simulacro.
    """
    # 1. full a secas no alcanza: hay que nombrar comandos.
    try:
        HidrawBackend(mode=Mode.FULL)
    except ValueError:
        pass
    else:
        fallos.append("HidrawBackend acepto 'full' sin --permitir-escritura")

    # 2. solo entran los comandos que pasaron la Etapa 2. Iluminacion salio de
    # esta lista y botones, cuando cada uno la
    #    paso. Los tres que quedan siguen afuera, y no por el mismo motivo:
    #
    # * CMD_MACRO **entro a `p.WRITABLE`**, cuando el
    #      codificador rearmo el checksum invertido, y **sigue prohibido aca
    #      igual**: el backend no sabe mandarlo. Mide 111 bytes, no entra en
    #      un report y va partido en dos tramas por `escribir_por_bloques()`,
    #      que es un metodo que este camino no usa. Lo escribe
    #      `driver/scripts/primera-escritura.py`, que habla con `Device` directo.
    #      Es el techo mas bajo del backend, y esta nombrado en
    #      `backend.SIN_CAMINO_EN_EL_BACKEND` en vez de salir por accidente de
    #      que `build_write_frame()` rechace el largo.
    #    * CMD_PROFILE y CMD_VERSION no tienen captura que los respalde.
    for prohibido in (p.CMD_MACRO, p.CMD_PROFILE, p.CMD_VERSION):
        try:
            HidrawBackend(mode=Mode.FULL, permitir_escritura=[prohibido])
        except ValueError:
            pass
        else:
            fallos.append(f"acepto escribir cmd {prohibido}, que no paso la "
                          "Etapa 2")

    # Y la razon importa: cmd 9 esta afuera porque el backend no tiene el
    # camino, no porque le falte la Etapa 2. Si un dia se confunden, el
    # mensaje va a mandar a alguien a rehacer una Etapa 2 que ya esta hecha.
    from linshark import backend as backend_mod
    if p.CMD_MACRO not in backend_mod.SIN_CAMINO_EN_EL_BACKEND:
        fallos.append("cmd 9 salio de SIN_CAMINO_EN_EL_BACKEND: el backend "
                      "sigue sin poder mandar un bloque multi-trama")
    if p.CMD_MACRO not in p.WRITABLE:
        fallos.append("cmd 9 salio de WRITABLE, donde entro con la Etapa 2 "
                      "hecha en los dos sentidos")
    try:
        HidrawBackend(mode=Mode.FULL, permitir_escritura=[p.CMD_MACRO])
    except ValueError as exc:
        if "Etapa 2" in str(exc):
            fallos.append("el backend rechaza cmd 9 diciendo que no paso la "
                          "Etapa 2, y si la paso: lo que no tiene es camino")

    # 3. pedir permisos en un modo que no escribe es un error, no algo que se
    #    ignore en silencio.
    for modo in (Mode.LISTEN, Mode.READ):
        try:
            HidrawBackend(mode=modo, permitir_escritura=[p.CMD_REPORT_RATE])
        except ValueError:
            pass
        else:
            fallos.append(f"acepto --permitir-escritura en modo {modo}")

    # 4. el modo valido arranca en simulacro y con la bateria exigida.
    b = HidrawBackend(mode=Mode.FULL, permitir_escritura=[p.CMD_REPORT_RATE])
    if not b.simulacro:
        fallos.append("el modo full no arranca en simulacro")
    if b.bateria_minima < 50:
        fallos.append(f"umbral de bateria {b.bateria_minima}%, se esperaba >= 50")
    if b.permitir_escritura != frozenset({p.CMD_REPORT_RATE}):
        fallos.append(f"permitir_escritura quedo en {b.permitir_escritura}")

    # 5. la allowlist de escritura es mas chica que la de lectura, y a
    #    proposito: que algo se pueda leer no es motivo para escribirlo.
    if not p.WRITABLE < set(p.READ_SUB):
        fallos.append("WRITABLE dejo de ser un subconjunto estricto de READ_SUB")


# --- H-09: hexadecimal invalido no corta la sesion -------------------------

async def test_basura_no_corta_la_sesion(fallos: list[str]) -> None:
    backend = StubBackend(presence_period=3600)
    bridge = server.Bridge(backend)
    async with server.serve(bridge, ["127.0.0.1"], PORT):
        async with connect(f"ws://127.0.0.1:{PORT}",
                           additional_headers={"Origin": "https://szslxd-tech.com"}) as ws:
            for _ in range(2):  # version + presencia
                await asyncio.wait_for(ws.recv(), timeout=3)

            await ws.send("no soy hexadecimal")
            await ws.send("f0")            # lectura cortada: 0xF0 con 1 byte
            # Si la conexion sobrevivio, una escritura normal sigue teniendo ack.
            await ws.send(p.encode([p.CONN_WIRELESS, 8, 12, 7, 8, 0, 0, 0, 0, 0]))
            try:
                respuesta = await asyncio.wait_for(ws.recv(), timeout=3)
            except (ConnectionClosed, asyncio.TimeoutError) as exc:
                fallos.append(f"la basura mato la sesion: {type(exc).__name__}")
                return
            raw = p.decode(respuesta)
            if not (len(raw) == 5 and raw[2] == p.CMD_ACK):
                fallos.append(f"esperaba un ack, llego {respuesta}")


# --- H-07: solo el origen del fabricante puede hablarle al puente ----------

async def _intenta_conexion(headers) -> bool:
    """True si el puente dejo hablar."""
    try:
        async with connect(f"ws://127.0.0.1:{PORT}",
                           additional_headers=headers) as ws:
            await asyncio.wait_for(ws.recv(), timeout=3)
        return True
    except (ConnectionClosed, asyncio.TimeoutError, OSError):
        return False


async def test_filtro_de_origen(fallos: list[str]) -> None:
    backend = StubBackend(presence_period=3600)
    async with server.serve(server.Bridge(backend), ["127.0.0.1"], PORT):
        if not await _intenta_conexion({"Origin": "https://szslxd-tech.com"}):
            fallos.append("rechazo el Origin del fabricante")
        if await _intenta_conexion({"Origin": "https://sitio-cualquiera.example"}):
            fallos.append("acepto un Origin ajeno: cualquier pestana abierta "
                          "podria hablarle al mouse")
        # Sin Origin no es un navegador (curl, una sonda local): se deja pasar
        # a proposito, porque ese proceso ya tiene el /dev/hidraw a mano.
        if not await _intenta_conexion({}):
            fallos.append("rechazo un cliente sin Origin")

    # Y el filtro se tiene que poder apagar a mano.
    async with server.serve(server.Bridge(backend, origenes=None),
                            ["127.0.0.1"], PORT):
        if not await _intenta_conexion({"Origin": "https://sitio-cualquiera.example"}):
            fallos.append("--sin-chequeo-de-origen no deja pasar nada")


# --- regresion del framing: la trama tiene que dar igual a la del binario --

def test_trama_igual_a_la_del_binario(fallos: list[str]) -> None:
    # Los dos volcados salen de dev/models/attackshark-x8pro/docs/bitacora.md, capturados del desensamblado
    # de WebDriver.exe y del trafico real.
    casos = [
        (0x0C, "040ca00c0a000000000000c6"),   # el bloque en 0x40e542
        (p.CMD_VERSION, "040ca00b08000000000000c3"),
    ]
    for cmd, esperado in casos:
        obtenido = p.build_read_frame(cmd).hex()
        if obtenido != esperado:
            fallos.append(f"trama de cmd 0x{cmd:02x}: {obtenido}, "
                          f"el binario dice {esperado}")

    if not p.verify_frame(RESPUESTA_VERSION):
        fallos.append("verify_frame rechaza una respuesta real del mouse")


# --- fase 2: las tramas de escritura, sin mandarlas a ningun lado ---------

def test_tramas_de_escritura(fallos: list[str]) -> None:
    # El bloque de lectura del modo de despertado que arma la pagina
    # (WakeupModeReadCommand del bundle), pasado por el camino de escritura.
    trama = p.build_write_frame(bytes([0x0C, 0x07, 0x08, 0, 0, 0, 0]))
    if trama.hex() != "040c000c0708000000000 02b".replace(" ", ""):
        fallos.append(f"trama de escritura inesperada: {trama.hex()}")
    if trama[1] != len(trama):
        fallos.append("el largo declarado no coincide con el real")
    if not p.verify_frame(trama):
        fallos.append("la trama de escritura no valida su propio checksum")

    # Un bloque incoherente no se arma: el byte N tiene que ser su largo.
    try:
        p.build_write_frame(bytes([4, 99, 0]))
    except ValueError:
        pass
    else:
        fallos.append("acepto un bloque cuyo N no coincide con su largo")

    # Un bloque que no entra en un report tiene que fallar limpio: es el
    # camino que hay que tomar con build_write_blocks(). (Aca vivia un
    # NameError que tapaba el ValueError; lo encontro la re-auditoria.)
    try:
        p.build_write_frame(bytes([0, 60] + [0] * 58))
    except ValueError:
        pass
    except Exception as exc:  # noqa: BLE001
        fallos.append(f"un bloque demasiado grande levanto {type(exc).__name__}, "
                      "esperaba ValueError")
    else:
        fallos.append("acepto un bloque que no entra en el report")

    # El camino por bloques: el binario fija largo 0x40 para el primero y
    # 0x39 para el segundo. Los dos tienen que salir solos de la formula.
    bloques = p.build_write_blocks(bytes(range(111)))
    if len(bloques) != 2:
        fallos.append(f"{len(bloques)} bloques para 111 bytes, esperaba 2")
    else:
        if bloques[0][:3].hex() != "044000":
            fallos.append(f"cabecera del bloque 0: {bloques[0][:3].hex()}, "
                          "el binario dice 044000")
        if bloques[1][:3].hex() != "043901":
            fallos.append(f"cabecera del bloque 1: {bloques[1][:3].hex()}, "
                          "el binario dice 043901")
    for i, b in enumerate(bloques):
        if b[1] != len(b) or not p.verify_frame(b):
            fallos.append(f"bloque {i}: largo o checksum mal")

    # El unico camino desde el backend hacia el mouse pasa por un metodo, y
    # ese metodo chequea el modo y la allowlist antes de armar nada. Antes aca
    # se exigia que backend.py no nombrara estas funciones; desde que las
    # escrituras existen, lo que hay que sostener es que esten encerradas.
    import inspect
    from linshark import backend

    if "build_write_blocks" in inspect.getsource(backend):
        fallos.append("build_write_blocks aparece en backend.py: el camino "
                      "multibloque no paso la Etapa 2")

    for nombre, metodo in inspect.getmembers(backend.HidrawBackend,
                                             inspect.isfunction):
        fuente = inspect.getsource(metodo)
        if "build_write_frame" not in fuente:
            continue
        if nombre != "_responder_escritura":
            fallos.append(f"{nombre}() arma tramas de escritura; el unico que "
                          "puede es _responder_escritura()")
            continue
        for guarda in ("self.mode != Mode.FULL",
                       "self.permitir_escritura",
                       "self.simulacro",
                       "self.battery_level"):
            if guarda not in fuente:
                fallos.append(f"_responder_escritura() ya no chequea {guarda}")


def test_largo_es_n_mas_cinco(fallos: list[str]) -> None:
    """La relacion L = N + 5, contra respuestas reales del mouse."""
    for nombre, hx in (("version", "040d000b0808008301050000b5"),
                       ("report rate", "040e0006090144bb000000000121")):
        f = bytes.fromhex(hx)
        if f[1] != f[4] + 5:
            fallos.append(f"{nombre}: L={f[1]} pero N+5={f[4] + 5}")
        if not p.verify_frame(f):
            fallos.append(f"{nombre}: checksum de la captura real no valida")


# --- respuestas largas: llegan en bloques y hay que juntarlas --------------

async def test_reensamblado(fallos: list[str]) -> None:
    """macro (111) y perfil completo (128) no entran en un report de 64."""
    payload = bytes([p.CMD_MACRO, 111]) + bytes(range(109))
    bloques = p.build_write_blocks(payload)
    if [(b[1], b[2]) for b in bloques] != [(64, 0), (57, 1)]:
        fallos.append(f"largos de bloque inesperados: {[(b[1], b[2]) for b in bloques]}")

    canal = CanalFalso([[(0.01 * (i + 1), b) for i, b in enumerate(bloques)]])
    dev = Device(canal)
    canal.device = dev
    frame = await dev.leer(p.CMD_MACRO)
    if frame is None:
        fallos.append("una respuesta en dos bloques no se reensamblo")
        return
    if len(frame.data) != 109:
        fallos.append(f"reensamblado con {len(frame.data)} B, esperaba 109 "
                      "(se estaba perdiendo el segundo bloque en silencio)")
    if frame.data != payload[2:]:
        fallos.append("el contenido reensamblado no coincide")


# --- una respuesta que llega tarde sigue siendo la respuesta ---------------
# Las dos de abajo son: a 8000 Hz el respaldo perdia macro y
# perfil completo, y no era que el mouse no contestara sino que contestaba
# tarde y no habia nadie escuchando. Ver dev/models/attackshark-x8pro/docs/bitacora.md.

async def test_respuesta_durante_la_pausa(fallos: list[str]) -> None:
    """La respuesta cae en plena pausa de "ocupado" y tiene que valer igual."""
    # Un solo guion: el dongle dice 0xC3 enseguida y contesta 0.2 s despues,
    # dentro de la pausa de 0.4 s. Si el pedido no la recoge ahi, no hay
    # segunda oportunidad, que es exactamente lo que pasaba con el mouse.
    canal = CanalFalso([[(0.01, ESTADO_OCUPADO), (0.2, RESPUESTA_VERSION)]])
    dev = Device(canal)
    canal.device = dev
    frame = await dev.leer(p.CMD_VERSION, timeout=0.3, reintentos=2)
    if frame is None:
        fallos.append("la respuesta llego durante la pausa de 'ocupado' y se "
                      "perdio: no quedo nadie esperandola")


async def test_gracia_con_bloque_tardio(fallos: list[str]) -> None:
    """Con medio macro en la mano, rendirse es rendirse con la respuesta en vuelo."""
    payload = bytes([p.CMD_MACRO, 111]) + bytes(range(109))
    bloque0, bloque1 = p.build_write_blocks(payload)
    # El bloque 0 llega enseguida y el 1 recien despues de agotados los
    # reintentos. Tener el bloque 0 es la prueba de que el dongle esta
    # contestando: ahi, y solo ahi, vale esperar de mas.
    canal = CanalFalso([[(0.01, bloque0), (0.8, bloque1)]])
    dev = Device(canal)
    canal.device = dev
    frame = await dev.leer(p.CMD_MACRO, timeout=0.5, reintentos=1)
    if frame is None:
        fallos.append("se abandono una respuesta a medio llegar en vez de "
                      "esperar el bloque que faltaba")
        return
    if frame.data != payload[2:]:
        fallos.append("el bloque tardio no se junto bien con el primero")


async def test_parcial_no_contamina_al_siguiente(fallos: list[str]) -> None:
    """Los restos de un pedido que quedo a medias no son datos del siguiente."""
    payload = bytes([p.CMD_MACRO, 111]) + bytes(range(109))
    bloque0, _ = p.build_write_blocks(payload)
    canal = CanalFalso([[(0.01, bloque0)],                    # macro a medias
                        [(0.01, RESPUESTA_VERSION)]])         # y ahora version
    dev = Device(canal)
    canal.device = dev
    await dev.leer(p.CMD_MACRO, timeout=0.1, reintentos=1)
    frame = await dev.leer(p.CMD_VERSION, timeout=0.5, reintentos=1)
    if frame is None:
        fallos.append("version no contesto despues de un macro a medias")
        return
    if frame.cmd != p.CMD_VERSION:
        fallos.append(f"se devolvio cmd {frame.cmd} pidiendo version: los "
                      "restos del pedido anterior se colaron")


# --- N-H04: el acuse 0xC1 que llega durante una pausa no se puede perder ---
# Hasta este parche, `Device.escribir()` dormia con `asyncio.sleep()` en las
# dos pausas del bucle (la de "ocupado" y la de reintento). Si el `0xC1` caia
# ahi, se marcaba el Event, el bucle hacia `continue` y la vuelta siguiente lo
# borraba con `clear()` antes de mirarlo.
#
# El sintoma no es solo perder tiempo: la escritura YA se aplico en el mouse.
# Se reenvia una trama que no hacia falta y, si se agotan los reintentos, se
# devuelve False habiendo escrito. Reportar como fallido algo que paso es peor
# que fallar. Por eso los dos primeros tests miran tambien **cuantas veces se
# escribio**, no solo el valor devuelto.

# El bloque de report rate a 1000 Hz, el mismo que el mouse recibio de verdad
# y que el driver oficial mando en `w2-rate.pcap` (dev/docs/metodo.md,
# Etapa 3). No se inventa un bloque para el test: `escribir()` lo pasa por
# `build_write_frame()`, que valida N contra el largo.
BLOQUE_RATE_1000 = bytes.fromhex("06090144bb00000000")


async def test_acuse_en_la_pausa_de_ocupado(fallos: list[str]) -> None:
    # 0xC3 enseguida y el 0xC1 a 0.2 s: adentro de la pausa de 0.4 s.
    canal = CanalFalso([[(0.01, ESTADO_OCUPADO), (0.2, ESTADO_ESCRITURA_OK)]])
    dev = Device(canal)
    canal.device = dev
    ok = await dev.escribir(BLOQUE_RATE_1000, timeout=0.3, reintentos=2)
    if not ok:
        fallos.append("el 0xC1 llego durante la pausa de 'ocupado' y se "
                      "perdio: la escritura se dio por fallida")
    if len(canal.escrituras) != 1:
        fallos.append(f"{len(canal.escrituras)} escrituras, esperaba 1: se "
                      "reenvio al mouse una escritura que ya estaba aplicada")


async def test_acuse_en_la_pausa_de_reintento(fallos: list[str]) -> None:
    # NAK enseguida y el 0xC1 a 0.05 s: adentro de la pausa de 0.15 s.
    canal = CanalFalso([[(0.01, ESTADO_NAK), (0.05, ESTADO_ESCRITURA_OK)]])
    dev = Device(canal)
    canal.device = dev
    ok = await dev.escribir(BLOQUE_RATE_1000, timeout=0.3, reintentos=2)
    if not ok:
        fallos.append("el 0xC1 llego durante la pausa de reintento y se "
                      "perdio: la escritura se dio por fallida")
    if len(canal.escrituras) != 1:
        fallos.append(f"{len(canal.escrituras)} escrituras, esperaba 1: se "
                      "reenvio al mouse una escritura que ya estaba aplicada")


# --- El camino multi-bloque, que es el unico del proyecto con una ventana en
# la que el mouse tiene MEDIO bloque.
#
# Cmd 9 mide 111 bytes y no entra en un report: viaja en dos tramas de 59 + 52
# con el numero de bloque donde iria el opcode. El dongle acusa `0xC0` despues
# de cada una y el `0xC1` recien despues de la segunda (MEDIDO en
# `soft-macro-asignado.pcap`, en las cuatro escrituras).
#
# Lo que este test fija es lo que se puede hacer mal: **un reintento tiene que
# reenviar la secuencia entera**. Mandarle el trozo 1 a un mouse que perdio el
# 0 le arma un bloque Frankenstein, y el checksum de trama no lo atrapa porque
# cada trozo lleva el suyo.

async def test_macro_por_bloques_al_mouse(fallos: list[str]) -> None:
    bloque = bytes.fromhex(MACRO_BLOQUE)
    tramas = p.build_write_blocks(bloque)
    if len(tramas) != 2:
        fallos.append(f"el macro tendria que partirse en 2 trozos, salio "
                      f"{len(tramas)}")
        return

    # 1. el caso bueno: las dos tramas, el 0xC1 despues de la segunda
    canal = CanalFalso([[(0.01, ESTADO_ACEPTADO)],
                        [(0.01, ESTADO_ACEPTADO), (0.02, ESTADO_ESCRITURA_OK)]])
    dev = Device(canal)
    canal.device = dev
    ok = await dev.escribir_por_bloques(bloque, timeout=0.3, reintentos=2,
                                        pausa=0.02)
    if not ok:
        fallos.append("el macro se mando entero y el 0xC1 llego, y aun asi "
                      "escribir_por_bloques() dijo que fallo")
    if canal.escrituras != tramas:
        fallos.append(f"mando {len(canal.escrituras)} tramas y no son las de "
                      "build_write_blocks()")

    # 2. el 0xC0 del primer trozo NO es el acuse: si se lo tomara por bueno,
    # el mouse se quedaria con medio bloque y nosotros diciendo que anduvo.
    canal = CanalFalso([[(0.01, ESTADO_ACEPTADO)], [(0.01, ESTADO_ACEPTADO)]])
    dev = Device(canal)
    canal.device = dev
    ok = await dev.escribir_por_bloques(bloque, timeout=0.1, reintentos=1,
                                        pausa=0.02)
    if ok:
        fallos.append("sin 0xC1 la escritura por bloques se dio por buena: el "
                      "0xC0 del trozo 0 no es un acuse")

    # 3. un reintento reenvia la secuencia ENTERA, nunca el ultimo trozo solo
    canal = CanalFalso([[(0.01, ESTADO_ACEPTADO)],
                        [(0.01, ESTADO_NAK)],
                        [(0.01, ESTADO_ACEPTADO)],
                        [(0.01, ESTADO_ACEPTADO), (0.02, ESTADO_ESCRITURA_OK)]])
    dev = Device(canal)
    canal.device = dev
    ok = await dev.escribir_por_bloques(bloque, timeout=0.3, reintentos=3,
                                        pausa=0.02)
    if not ok:
        fallos.append("el reintento del macro no llego a buen puerto")
    if canal.escrituras != tramas * 2:
        cuales = [t[2] for t in canal.escrituras]
        fallos.append(f"el reintento no reenvio la secuencia entera: los "
                      f"numeros de bloque mandados fueron {cuales}, esperaba "
                      f"{[t[2] for t in tramas * 2]}")

    # 4. y este camino es de cmd 9 y de ningun otro: los demas entran en un
    # report, y mandarlos por aca les cambiaria el opcode por un numero de
    # bloque sin que nadie lo note.
    for otro in (p.CMD_REPORT_RATE, p.CMD_DPI, p.CMD_LIGHTING, p.CMD_BUTTONS):
        canal = CanalFalso([])
        dev = Device(canal)
        canal.device = dev
        try:
            await dev.escribir_por_bloques(bytes([otro, 9]) + b"\x00" * 7)
        except ValueError:
            pass
        else:
            fallos.append(f"escribir_por_bloques acepto cmd {otro}")
        if canal.escrituras:
            fallos.append(f"escribir_por_bloques le mando algo al mouse con "
                          f"cmd {otro}")


async def test_sin_acuse_sigue_siendo_fallo(fallos: list[str]) -> None:
    """La otra mitad: sin 0xC1, `escribir()` NO puede devolver True.

    Una espera mas atenta al Event no puede volverse un "che, seguro que si".
    Sin este caso, el parche de arriba se podria pasar devolviendo True
    siempre y los dos tests anteriores no lo notarian.
    """
    canal = CanalFalso([[(0.01, ESTADO_OCUPADO)], [(0.01, ESTADO_NAK)]])
    dev = Device(canal)
    canal.device = dev
    ok = await dev.escribir(BLOQUE_RATE_1000, timeout=0.2, reintentos=2)
    if ok:
        fallos.append("escribir() dijo que si sin haber recibido el 0xC1")


# --- escribir UN nivel de dpi sin tocar el resto ---------------------------
# El codificador de escritura de dpi (`Pu()`) se valida con la misma idea que
# la Etapa 2: escribirle al bloque el valor que YA tiene tiene que reproducirlo
# byte a byte. Si un offset, el flag de la rama o el checksum interno estuvieran
# mal, el bloque saldria distinto.

DPI_DE_FABRICA = (1200, 2400, 3200, 5600, 8000, 40000)


def test_escribir_un_nivel_de_dpi(fallos: list[str]) -> None:
    from linshark import estructuras as e

    # 1. Idempotencia, nivel por nivel, sobre la captura real del mouse.
    for nivel, actual in enumerate(DPI_DE_FABRICA, start=1):
        nuevo, efectivo = e.escribir_nivel_dpi(DPI_REAL, nivel, actual)
        if efectivo != actual:
            fallos.append(f"nivel {nivel}: {actual} dpi se guardaria como "
                          f"{efectivo}")
        if nuevo != DPI_REAL:
            distintos = [i for i in range(len(DPI_REAL)) if nuevo[i] != DPI_REAL[i]]
            fallos.append(f"nivel {nivel}: reescribir {actual} dpi movio los "
                          f"bytes {distintos}; no tenia que cambiar nada")

    # 2. Un cambio real toca el byte del nivel, el checksum, y NADA mas.
    nuevo, efectivo = e.escribir_nivel_dpi(DPI_REAL, 1, 1600)
    off = e.offsets(e.DPI_FIXED)
    fin = e.fin_de_campos(e.DPI_FIXED)
    permitidos = {off["Dpi_X_setting"][0], off["Dpi_Y_setting"][0],
                  off["DPI_X_Double_Flag"][0], fin, fin + 1}
    movidos = {i for i in range(len(DPI_REAL)) if nuevo[i] != DPI_REAL[i]}
    if movidos - permitidos:
        fallos.append(f"cambiar el nivel 1 movio bytes que no debia: "
                      f"{sorted(movidos - permitidos)}")
    if efectivo != 1600:
        fallos.append(f"1600 dpi dio {efectivo}")

    # 3. La cuantizacion se avisa ANTES de escribir, no se descubre releyendo.
    _, efectivo = e.escribir_nivel_dpi(DPI_REAL, 1, 2453)
    if efectivo != 2450:
        fallos.append(f"pedir 2453 dpi tendria que avisar 2450, aviso {efectivo}")

    # 4. Bajar el nivel 6 de 40000 a algo chico tiene que APAGAR su bit de
    #    rama; si no, el mouse leeria el doble de lo que se pidio.
    nuevo, _ = e.escribir_nivel_dpi(DPI_REAL, 6, 1000)
    flag = nuevo[off["DPI_X_Double_Flag"][0]]
    if flag & (1 << 5):
        fallos.append(f"bajar el nivel 6 a 1000 dpi dejo el bit de /100 puesto "
                      f"(flag {flag:#04x})")
    campos = e.decodificar(e.DPI_FIXED, nuevo)
    leidos = mod_dpi_niveles(campos)
    if leidos[5] != 1000:
        fallos.append(f"el nivel 6 quedo en {leidos[5]}, esperaba 1000")

    # 5. Etapa 2 del codificador: reproducir un cambio que hizo el driver
    #    oficial. El par sale de `dev/models/attackshark-x8pro/docs/capturas-w/web-todo.pcap`, dos
    #    escrituras seguidas donde el operador movio el nivel 4 de 4750 a 4800
    #    desde la pagina. Nuestro codificador tiene que dar la segunda a partir
    #    de la primera, byte a byte, checksum interno incluido.
    antes = bytes.fromhex(
        "0110003f00001327355e87e70000000000000001000004ff000000ff000000"
        "ffffff0000ffffff00ffff4000ffffff020fc400000000")
    oficial = bytes.fromhex(
        "0110003f00001327355f87e70000000000000001000004ff000000ff000000"
        "ffffff0000ffffff00ffff4000ffffff020fc500000000")
    nuestro, _ = e.escribir_nivel_dpi(antes, 4, 4800)
    if nuestro != oficial:
        distintos = [i for i in range(len(oficial)) if nuestro[i] != oficial[i]]
        fallos.append(f"no reproduce el cambio 4750 -> 4800 del driver "
                      f"oficial; difiere en los bytes {distintos}")

    # 6. Lo que tiene que rechazar.
    for nivel, valor, porque in ((7, 1000, "un nivel que el mouse tiene apagado"),
                                 (1, 50, "por debajo del minimo de la UI"),
                                 (1, 40001, "por encima del maximo de la UI"),
                                 (9, 1000, "un nivel que no existe")):
        try:
            e.escribir_nivel_dpi(DPI_REAL, nivel, valor)
        except ValueError:
            pass
        else:
            fallos.append(f"acepto escribir {valor} dpi en el nivel {nivel}: "
                          f"es {porque}")


def mod_dpi_niveles(campos: dict) -> list[int]:
    from linshark import dpi as mod
    return mod.niveles_lineales(campos["Dpi_X_setting"], campos["Dpi_Y_setting"],
                                campos["DPI_X_Double_Flag"])


# --- lo que cmd 5 lleva de verdad: hibernacion y tiempo de respuesta -------
# Cinco bloques reales del driver oficial, elegidos porque **fijan los cuatro
# extremos**: la hibernacion minima y maxima, y la respuesta minima y maxima.
# Que los extremos observados caigan justo en 1..60 y en 2..25 -y que 2..25 sea
# exactamente `Math.floor(2 + 23*v/100)` del control oficial- es lo que hace
# que el desempaquetado no sea una eleccion arbitraria: con los nibbles
# cruzados, los numeros se irian del rango.
#
# (hex del bloque, hibernacion, respuesta, de donde sale)
LUZ_PARAMETROS = [
    ("010003180000ff020401200000", 1, 4, "web-todo.pcap, hibernacion minima"),
    ("010033c80000ff020402000000", 60, 4, "web-todo.pcap, hibernacion maxima"),
    ("010013180000ff0202012e0000", 17, 2, "web-todo.pcap, respuesta minima"),
    ("010013180000ff021901450000", 17, 25, "web-todo.pcap, respuesta maxima"),
    ("010003a800ff00010901b40000", 10, 9, "el estado del mouse"),
]


def test_parametros_de_luz(fallos: list[str]) -> None:
    from linshark import estructuras as e

    vistos_h, vistos_r = set(), set()
    for hexa, hiberna, resp, origen in LUZ_PARAMETROS:
        par = e.parametros_de_luz(bytes.fromhex(hexa))
        if par is None:
            fallos.append(f"{origen}: parametros_de_luz devolvio None")
            continue
        if par["hibernateTime"] != hiberna:
            fallos.append(f"{origen}: hibernacion {par['hibernateTime']}, "
                          f"esperaba {hiberna}")
        if par["responseTime"] != resp:
            fallos.append(f"{origen}: respuesta {par['responseTime']}, "
                          f"esperaba {resp}")
        if not par["en_rango"]:
            fallos.append(f"{origen}: un bloque real del driver oficial quedo "
                          "fuera de rango")
        vistos_h.add(par["hibernateTime"])
        vistos_r.add(par["responseTime"])

    # Los extremos tienen que ser los del control oficial, no unos cualquiera.
    if min(vistos_h) != e.HIBERNACION_MIN or max(vistos_h) != e.HIBERNACION_MAX:
        fallos.append(f"las hibernaciones observadas van de {min(vistos_h)} a "
                      f"{max(vistos_h)}; el control declara "
                      f"{e.HIBERNACION_MIN}..{e.HIBERNACION_MAX}")
    if min(vistos_r) != e.RESPUESTA_MIN or max(vistos_r) != e.RESPUESTA_MAX:
        fallos.append(f"las respuestas observadas van de {min(vistos_r)} a "
                      f"{max(vistos_r)}; el chunk calcula "
                      f"{e.RESPUESTA_MIN}..{e.RESPUESTA_MAX}")

    # Un bloque corto no se inventa campos.
    if e.parametros_de_luz(b"\x01\x00\x03") is not None:
        fallos.append("parametros_de_luz leyo campos de un bloque de 3 bytes")


# --- escribir la hibernacion: nuestros bytes contra los del driver oficial --
# La prueba fuerte del codificador. Las capturas traen **siete** valores de
# hibernacion distintos, y cada uno dejo un par (breathingSpeed, LightBrightness)
# concreto en el bus. Nuestro codificador, alimentado con el mismo numero, tiene
# que producir el mismo par. No es "el codificador se reproduce a si mismo": el
# numero sale del rango del control oficial y los bytes salen del bus.
#
#   hibernacion -> (breathingSpeed, LightBrightness), de web-todo.pcap y
#   soft-todo.pcap
HIBERNACION_OFICIAL = {
    1:  (0x03, 0x18),
    10: (0x03, 0xa8),
    17: (0x13, 0x18),
    23: (0x13, 0x78),
    25: (0x13, 0x98),
    49: (0x33, 0x18),
    60: (0x33, 0xc8),
}


def test_escribir_parametros_luz(fallos: list[str]) -> None:
    from linshark import estructuras as e

    pos = e.offsets(e.ILUMINACION_FIXED)
    i_bs, i_lb = pos["breathingSpeed"][0], pos["LightBrightness"][0]
    fin = e.fin_de_campos(e.ILUMINACION_FIXED)

    # 1. Idempotencia sobre CADA bloque real conocido: escribirle los valores
    #    que ya tiene lo reproduce byte a byte. Si un nibble estuviera del lado
    #    equivocado, alguno saldria distinto.
    for hexa, hiberna, resp, origen in LUZ_PARAMETROS:
        bloque = bytes.fromhex(hexa)
        igual = e.escribir_parametros_luz(bloque, hibernacion=hiberna,
                                          respuesta=resp)
        if igual != bloque:
            fallos.append(f"{origen}: reescribir sus propios valores dio otro "
                          f"bloque\n      {bloque.hex()}\n      {igual.hex()}")

    # 2. Los siete valores del driver oficial: nuestros dos bytes contra los
    #    suyos. El punto de partida es el bloque real del mouse.
    base = bytes.fromhex(LUZ_PARAMETROS[-1][0])
    for valor, (bs, lb) in sorted(HIBERNACION_OFICIAL.items()):
        salida = e.escribir_parametros_luz(base, hibernacion=valor)
        if (salida[i_bs], salida[i_lb]) != (bs, lb):
            fallos.append(
                f"hibernacion {valor}: armamos "
                f"({salida[i_bs]:#04x}, {salida[i_lb]:#04x}) y el driver "
                f"oficial mando ({bs:#04x}, {lb:#04x})")
        # y no se movio nada mas que esos dos bytes y el checksum
        movidos = {i for i in range(len(base)) if base[i] != salida[i]}
        if not movidos <= {i_bs, i_lb, fin, fin + 1}:
            fallos.append(f"hibernacion {valor}: se movieron los offsets "
                          f"{sorted(movidos - {i_bs, i_lb, fin, fin + 1})}")

    # 3. Fuera del rango del control oficial no se escribe. 0 y 61 son los dos
    #    vecinos del rango: si pasaran, el rango seria decorativo.
    for malo in (0, 61, -1, 256):
        try:
            e.escribir_parametros_luz(base, hibernacion=malo)
        except ValueError:
            pass
        else:
            fallos.append(f"acepto una hibernacion de {malo}")
    for malo in (1, 26, -1):
        try:
            e.escribir_parametros_luz(base, respuesta=malo)
        except ValueError:
            pass
        else:
            fallos.append(f"acepto un tiempo de respuesta de {malo}")

    # 4. Sin argumentos no toca nada.
    if e.escribir_parametros_luz(base) != base:
        fallos.append("escribir_parametros_luz() sin valores cambio el bloque")


# --- el OTRO temporizador de cmd 5: el reposo corto ------------------------
# El X8 Pro tiene dos temporizadores de reposo y viajan en bytes distintos del
# mismo bloque. Este es el corto (`Level1SleepTimer` en la web, `Sleep Time:`
# en el soft nativo), y va en el byte `closeTime` en **medios minutos**.
#
# La prueba mas fuerte que da el bus: `soft-todo.pcap` tiene dos escrituras del
# software nativo que difieren **solo en ese byte y el checksum**, a 74 s de
# distancia. Nuestro codificador tiene que convertir la primera en la segunda,
# byte a byte, y la segunda en la primera. Eso no es "el codificador se
# reproduce a si mismo": las dos puntas las mando el driver oficial.
REPOSO_PAR_OFICIAL = (
    "010003a800ff00010401af0000",   # soft-todo t=23.8s,  byte 7 = 1  (0.5 min)
    "010003a800ff000c0401ba0000",   # soft-todo t=97.9s,  byte 7 = 12 (6.0 min)
)

# Y los tres valores que el byte tomo en todas las capturas.
REPOSO_BYTES_VISTOS = {0.5: 1, 1.0: 2, 6.0: 12}


def test_escribir_reposo_ligero(fallos: list[str]) -> None:
    from linshark import estructuras as e

    i_ct = e.offsets(e.ILUMINACION_FIXED)["closeTime"][0]
    fin = e.fin_de_campos(e.ILUMINACION_FIXED)
    antes, despues = (bytes.fromhex(h) for h in REPOSO_PAR_OFICIAL)

    # 1. El par del driver oficial, en las dos direcciones.
    if e.escribir_reposo_ligero(antes, minutos=6.0) != despues:
        fallos.append("el par oficial: 0.5 -> 6.0 no reprodujo la trama que "
                      "mando el soft nativo")
    if e.escribir_reposo_ligero(despues, minutos=0.5) != antes:
        fallos.append("el par oficial: 6.0 -> 0.5 no reprodujo la vuelta")

    # 2. Idempotencia sobre cada bloque real conocido, y nada mas que ese byte.
    for hexa, _h, _r, origen in LUZ_PARAMETROS:
        bloque = bytes.fromhex(hexa)
        propio = e.parametros_de_luz(bloque)["reposoMin"]
        igual = e.escribir_reposo_ligero(bloque, minutos=propio)
        if igual != bloque:
            fallos.append(f"{origen}: reescribir su propio reposo dio otro "
                          f"bloque\n      {bloque.hex()}\n      {igual.hex()}")
        salida = e.escribir_reposo_ligero(bloque, minutos=6.0)
        movidos = {i for i in range(len(bloque)) if bloque[i] != salida[i]}
        if not movidos <= {i_ct, fin, fin + 1}:
            fallos.append(f"{origen}: el reposo movio los offsets "
                          f"{sorted(movidos - {i_ct, fin, fin + 1})}")

    # 3. Los tres valores vistos en el bus dan sus bytes.
    base = bytes.fromhex(LUZ_PARAMETROS[-1][0])
    for minutos, byte in sorted(REPOSO_BYTES_VISTOS.items()):
        salida = e.escribir_reposo_ligero(base, minutos=minutos)
        if salida[i_ct] != byte:
            fallos.append(f"reposo {minutos} min: armamos el byte "
                          f"{salida[i_ct]} y en el bus era {byte}")

    # 4. Fuera del rango del slider no se escribe, y medios minutos es medios
    #    minutos: 0.3 no tiene representacion y no se redondea a escondidas.
    for malo in (0, 0.25, 0.3, 30.5, 31, -1):
        try:
            e.escribir_reposo_ligero(base, minutos=malo)
        except ValueError:
            pass
        else:
            fallos.append(f"acepto un reposo de {malo}")


# --- los cuatro interruptores del sensor, en cmd 4 -------------------------
# `SensitivityX` y `SensitivityY` no son sensibilidad: llevan el LOD, el ripple,
# el angle snapping y el motion sync, de a dos por byte. La prueba fuerte, como
# con el reposo, son **transiciones reales del driver oficial**: tres pares de
# `soft-todo.pcap` que difieren solo en esos dos bytes (el checksum ni se mueve,
# porque los nibbles se intercambian y la suma se conserva).
SENSOR_TRANSICIONES = [
    # (antes, despues, que cambio) — soft-todo.pcap, el soft nativo tocando los
    # switches de a uno.
    ("0111013f0000172f3f6f51000000000000000100000001ff000000ff000000ffffff"
     "0000ffffff00ffff4000ffffff020ecd000000001026",
     "0101113f0000172f3f6f51000000000000000100000001ff000000ff000000ffffff"
     "0000ffffff00ffff4000ffffff020ecd000000001026",
     "t=81.0 -> t=93.8: LOD 2mm->1mm y angle snapping OFF->ON"),
    ("0100013f0000172f3f6f51000000000000000100000001ff000000ff000000ffffff"
     "0000ffffff00ffff4000ffffff020ebc000000001004",
     "0101003f0000172f3f6f51000000000000000100000001ff000000ff000000ffffff"
     "0000ffffff00ffff4000ffffff020ebc000000001004",
     "t=89.5 -> t=98.7: ripple OFF->ON y motion sync ON->OFF"),
]

# Los diez pares (SensitivityX, SensitivityY) que aparecen en todo el bus. Los
# cuatro bits estan en los dos estados, asi que ninguno queda sin ejercitar.
SENSOR_PARES_BUS = [
    (0x01, 0x01), (0x11, 0x01), (0x00, 0x01), (0x01, 0x11), (0x01, 0x00),
    (0x11, 0x11), (0x10, 0x01), (0x10, 0x00), (0x00, 0x00), (0x00, 0x11),
]


# --- cmd 4: el nivel de dpi que esta en uso --------------------------------
#
# Las dos escrituras del soft nativo en `soft-todo.pcap` con **2.28 s** de
# diferencia -t+862.96 y t+865.24-, con el usuario cambiando el nivel activo
# en la UI. Difieren en **dos bytes**: el 22, que es
# `Current_Dpi_level_flag`, y el 49, que es el checksum interno. Es la misma
# forma de prueba que `test_escribir_reposo_ligero`: convertir una escritura
# real del driver oficial en la otra, byte a byte y en las dos direcciones.
DPI_NIVEL_ACTIVO_3 = bytes.fromhex(
    "0101013f2000172f3f6f9f8f0000000000000001000003ff000000ff000000ffffff"
    "0000ffffff00ffff4000ffffff020fbc00000000")
DPI_NIVEL_ACTIVO_1 = bytes.fromhex(
    "0101013f2000172f3f6f9f8f0000000000000001000001ff000000ff000000ffffff"
    "0000ffffff00ffff4000ffffff020fba00000000")


def test_escribir_nivel_activo(fallos: list[str]) -> None:
    from linshark import estructuras as e

    # 1. las dos direcciones, contra el bus
    for origen, destino, nivel in ((DPI_NIVEL_ACTIVO_3, DPI_NIVEL_ACTIVO_1, 1),
                                   (DPI_NIVEL_ACTIVO_1, DPI_NIVEL_ACTIVO_3, 3)):
        nuestro = e.escribir_nivel_activo(origen, nivel=nivel)
        if nuestro != destino:
            difs = [i for i in range(len(destino)) if nuestro[i] != destino[i]]
            fallos.append(f"nivel activo -> {nivel}: no reproduce la escritura "
                          f"del soft, difiere en {difs}")

    # 2. idempotente: pedir el nivel que ya esta no mueve un byte
    if e.escribir_nivel_activo(DPI_NIVEL_ACTIVO_1, nivel=1) != DPI_NIVEL_ACTIVO_1:
        fallos.append("reescribir el nivel activo que ya esta movio bytes")

    # 3. y no toca ningun VALOR de dpi: eso es el otro codificador
    antes = e.decodificar(p.CMD_DPI, DPI_NIVEL_ACTIVO_1)
    despues = e.decodificar(p.CMD_DPI, e.escribir_nivel_activo(
        DPI_NIVEL_ACTIVO_1, nivel=6))
    # `_cola` lleva el checksum interno y tiene que moverse: lo que no puede
    # moverse es un campo con nombre.
    movidos = [k for k in antes if antes[k] != despues[k] and k != "_cola"]
    if movidos != ["Current_Dpi_level_flag"]:
        fallos.append(f"cambiar el nivel activo movio {movidos}")

    # 4. un nivel apagado no se puede poner en uso: el mouse acusaria igual.
    #    En este bloque `dpi_ON_OFF_flag` es 0x3f, o sea 1..6 encendidos.
    try:
        e.escribir_nivel_activo(DPI_NIVEL_ACTIVO_1, nivel=7)
    except e.NivelApagado:
        pass
    except Exception as exc:  # noqa: BLE001
        fallos.append(f"nivel apagado levanto {type(exc).__name__}")
    else:
        fallos.append("dejo poner en uso un nivel apagado (el 7, con "
                      "dpi_ON_OFF_flag = 0x3f)")

    # 5. y fuera de rango es un error, no un byte cualquiera
    for malo in (0, 9, -1):
        try:
            e.escribir_nivel_activo(DPI_NIVEL_ACTIVO_1, nivel=malo)
        except (ValueError, e.NivelApagado):
            pass
        else:
            fallos.append(f"acepto el nivel {malo}")


def test_escribir_parametros_sensor(fallos: list[str]) -> None:
    from linshark import estructuras as e

    pos = e.offsets(e.DPI_FIXED)
    i_sx, i_sy = pos["SensitivityX"][0], pos["SensitivityY"][0]
    fin = e.fin_de_campos(e.DPI_FIXED)

    # 1. Las transiciones del driver oficial, en las dos direcciones.
    for a_hex, b_hex, que in SENSOR_TRANSICIONES:
        a, b = bytes.fromhex(a_hex), bytes.fromhex(b_hex)
        for origen, destino in ((a, b), (b, a)):
            objetivo = e.parametros_de_sensor(destino)
            nuestro = e.escribir_parametros_sensor(
                origen, lod=objetivo["lod"], ripple=objetivo["ripple"],
                angle_snapping=objetivo["angle_snapping"],
                motion_sync=objetivo["motion_sync"])
            if nuestro != destino:
                fallos.append(f"{que}: no reprodujimos la trama del driver\n"
                              f"      {destino.hex()}\n      {nuestro.hex()}")

    # 2. Los diez pares del bus: nuestro empaquetado tiene que dar esos bytes.
    base = bytes.fromhex(SENSOR_TRANSICIONES[0][0])
    for sx, sy in SENSOR_PARES_BUS:
        campos = e.parametros_de_sensor(bytes([0, sx, sy]) + base[3:])
        salida = e.escribir_parametros_sensor(
            base, lod=campos["lod"], ripple=campos["ripple"],
            angle_snapping=campos["angle_snapping"],
            motion_sync=campos["motion_sync"])
        if (salida[i_sx], salida[i_sy]) != (sx, sy):
            fallos.append(
                f"par del bus ({sx:#04x}, {sy:#04x}): armamos "
                f"({salida[i_sx]:#04x}, {salida[i_sy]:#04x})")
        movidos = {i for i in range(len(base)) if base[i] != salida[i]}
        if not movidos <= {i_sx, i_sy, fin, fin + 1}:
            fallos.append(f"par ({sx:#04x}, {sy:#04x}): se movieron los offsets "
                          f"{sorted(movidos - {i_sx, i_sy, fin, fin + 1})}")

    # 3. Idempotencia: escribirle lo que ya tiene reproduce el bloque, y sin
    #    argumentos no toca nada. Ningun nivel de dpi se mueve nunca: viven en
    #    el mismo bloque y son lo mas caro de pisar sin querer.
    for a_hex, b_hex, que in SENSOR_TRANSICIONES:
        for bloque in (bytes.fromhex(a_hex), bytes.fromhex(b_hex)):
            propio = e.parametros_de_sensor(bloque)
            igual = e.escribir_parametros_sensor(
                bloque, lod=propio["lod"], ripple=propio["ripple"],
                angle_snapping=propio["angle_snapping"],
                motion_sync=propio["motion_sync"])
            if igual != bloque:
                fallos.append(f"{que}: reescribir sus propios valores dio otro "
                              "bloque")
            if e.escribir_parametros_sensor(bloque) != bloque:
                fallos.append(f"{que}: sin argumentos cambio el bloque")

    # 3b. Milimetros hacia afuera, valor de campo hacia adentro. Si esa
    #     traduccion se invierte, `--lod 1` escribiria 2 mm y nadie se daria
    #     cuenta hasta levantar el mouse.
    if e.lod_desde_mm(1) != e.LOD_1MM or e.lod_desde_mm(2) != e.LOD_2MM:
        fallos.append("lod_desde_mm no traduce milimetros a valor de campo")
    if e.LOD_MM[e.LOD_1MM] != 1 or e.LOD_MM[e.LOD_2MM] != 2:
        fallos.append("LOD_MM no es la inversa de LOD_DESDE_MM")
    for malo in (0, 3, -1, 1.5):
        try:
            e.lod_desde_mm(malo)
        except ValueError:
            pass
        else:
            fallos.append(f"lod_desde_mm acepto {malo} mm")

    # 4. El LOD tiene dos opciones y nada mas: el radio oficial declara 0 y 1.
    for malo in (2, 15, -1, 16):
        try:
            e.escribir_parametros_sensor(base, lod=malo)
        except ValueError:
            pass
        else:
            fallos.append(f"acepto un LOD de {malo}")

    # 5. Y la diferencia con lo que muestra la pagina oficial queda expuesta,
    #    porque es la que va a confundir a cualquiera que compare pantallas.
    #    Con el bloque de fabrica (01 01) la pagina dice "angle snapping ON" y
    #    el byte dice OFF.
    fabrica = e.parametros_de_sensor(bytes.fromhex(
        "0101013f20001f2f3f6f9f8f0000000000000001000002ff000000ff000000"
        "ffffff0000ffffff00ffff4000ffffff020fc300000000"))
    if fabrica is None:
        fallos.append("parametros_de_sensor devolvio None con el bloque real")
    elif fabrica["angle_snapping"] or not fabrica["pagina_angle_snapping"]:
        fallos.append("la discrepancia con el lector de la pagina cambio: "
                      f"{fabrica}")


# --- el consejo de verificacion no puede reventar --------------------------
# Los interruptores del sensor entraron por `--comando dpi` y
# cayeron en la rama del informe final escrita para el nivel de dpi, que usa
# variables que solo existen si se escribio un nivel. Revento con
# `UnboundLocalError` **despues** de haber escrito y releido: la escritura salio
# bien y el resumen de que cambio no se llego a imprimir.
#
# Ningun linter agarra eso -la variable si esta asignada en la funcion, es el
# camino lo que falla-, asi que la baranda es que el despacho sea **total** y
# que este test lo recorra entero. Si manana aparece un campo nuevo sin su rama,
# no revienta: cae en el `else` de seguridad, y este test lo comprueba.

def _cargar_primera_escritura():
    import importlib.util
    ruta = (Path(__file__).resolve().parent.parent / "scripts"
            / "primera-escritura.py")
    spec = importlib.util.spec_from_file_location("primera_escritura", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_consejo_de_verificacion(fallos: list[str]) -> None:
    pe = _cargar_primera_escritura()

    # Todas las combinaciones que el CLI acepta hoy, mas dos que no acepta
    # -un comando sin rama propia y un dpi sin nivel- que son justo las que
    # tienen que caer en el `else` de seguridad sin romperse.
    casos = [
        ("rate", p.CMD_REPORT_RATE, {}),
        ("luz --color", p.CMD_LIGHTING, {"rgb": (0, 255, 0)}),
        ("luz --hibernacion", p.CMD_LIGHTING, {}),
        ("luz --reposo", p.CMD_LIGHTING, {}),
        ("luz --respuesta", p.CMD_LIGHTING, {}),
        ("dpi --lod", p.CMD_DPI, {"sensor": {"lod": 1}}),
        ("dpi --ripple", p.CMD_DPI, {"sensor": {"ripple": 1}}),
        ("dpi --angle-snapping", p.CMD_DPI, {"sensor": {"angle_snapping": 1}}),
        ("dpi --motion-sync", p.CMD_DPI, {"sensor": {"motion_sync": 1}}),
        ("dpi --nivel --valor", p.CMD_DPI,
         {"nivel": 1, "en_la_pagina": 1350, "efectivo": 1600}),
        ("dpi --nivel-activo", p.CMD_DPI, {"nivel_activo": 2}),
        ("dpi sin nivel (no deberia pasar)", p.CMD_DPI, {}),
        ("macro --modo", p.CMD_MACRO, {}),
        ("macro --eventos", p.CMD_MACRO,
         {"eventos": [{"usageId": 4, "direccion": 0, "tiempo": 10}]}),
        ("macro --eventos con un tiempo largo", p.CMD_MACRO,
         {"eventos": [{"usageId": 4, "direccion": 0, "tiempo": 250}]}),
        ("botones --atajo", p.CMD_BUTTONS, {"atajo": "ctrl+c"}),
        ("un comando sin rama propia", p.CMD_PROFILE, {}),
    ]
    for nombre, cmd, kw in casos:
        try:
            lineas = pe.consejo_de_verificacion(cmd, respaldo="x.json", **kw)
        except Exception as exc:  # noqa: BLE001
            fallos.append(f"consejo_de_verificacion revento con {nombre}: "
                          f"{type(exc).__name__}: {exc}")
            continue
        if not lineas or not all(isinstance(l, str) for l in lineas):
            fallos.append(f"consejo_de_verificacion salio vacio con {nombre}")

    # El LOD es el unico campo con verificacion a simple vista: si eso deja de
    # decirse, la sugerencia perdio lo que la hacia util.
    lod = "\n".join(pe.consejo_de_verificacion(
        p.CMD_DPI, sensor={"lod": 1}, respaldo="x.json"))
    if "simple vista" not in lod or "2 mm" not in lod:
        fallos.append("el consejo del LOD ya no menciona la verificacion a "
                      "simple vista")
    # Y el nivel activo es la otra que se ve: el LED de nivel cambia de color.
    # Si el consejo no lo dice, se pierde la unica verificacion barata que
    # tiene cmd 4 ademas del LOD.
    act = "\n".join(pe.consejo_de_verificacion(
        p.CMD_DPI, nivel_activo=2, respaldo="x.json"))
    if "simple vista" not in act or "indicador" not in act:
        fallos.append("el consejo del nivel activo no manda a mirar el LED")
    # Cmd 9 se verifica apretando el boton, pero **solo si el macro esta
    # asignado a uno**. Si el consejo se olvida de ese paso, manda a alguien a
    # apretar un boton que no tiene el macro y a leer "no pasa nada" como si
    # la escritura hubiera fallado.
    mac = "\n".join(pe.consejo_de_verificacion(p.CMD_MACRO, respaldo="x.json"))
    if "--funcion macro" not in mac:
        fallos.append("el consejo de cmd 9 no dice que primero hay que "
                      "asignar el macro a un boton")

    # Grabar eventos se verifica apretando el boton, igual que el disparo,
    # pero lo que hay que mirar es otra cosa: que salga la secuencia.
    ev = "\n".join(pe.consejo_de_verificacion(
        p.CMD_MACRO, eventos=[{"usageId": 4, "direccion": 0, "tiempo": 10}],
        respaldo="x.json"))
    if "--funcion macro" not in ev:
        fallos.append("el consejo de --eventos no dice que el macro tiene que "
                      "estar asignado a un boton")
    # Y la direccion esta MEDIDA, asi que el consejo dice
    # cual es en vez de avisar que es una inferencia. Si alguien devuelve el
    # texto viejo, esto se pone rojo: seria degradar un dato medido.
    if "MEDIDO" not in ev or "dir0" not in ev:
        fallos.append("el consejo de --eventos ya no dice que dir0 aprieta, "
                      "que es lo que quedo medido")
    if "INFERIDO" in ev:
        fallos.append("el consejo de --eventos sigue diciendo que la "
                      "direccion es inferida: ya se midio")
    largo = "\n".join(pe.consejo_de_verificacion(
        p.CMD_MACRO, eventos=[{"usageId": 4, "direccion": 0, "tiempo": 250}],
        respaldo="x.json"))
    if "INFERIDA" not in largo or "cuatro" not in largo:
        fallos.append("el consejo no avisa que los tiempos largos salen de la "
                      "rama sin captura")
    # y el atajo dice que combinacion tiene que llegar, no "algo nuevo"
    at = "\n".join(pe.consejo_de_verificacion(
        p.CMD_BUTTONS, atajo="ctrl+c", respaldo="x.json"))
    if "ctrl+c" not in at:
        fallos.append(f"el consejo del atajo no dice cual es: {at!r}")

    # Y los otros tres no la tienen: prometerla seria el error de I-W15.
    otro = "\n".join(pe.consejo_de_verificacion(
        p.CMD_DPI, sensor={"ripple": 1}, respaldo="x.json"))
    if "simple vista" in otro:
        fallos.append("el consejo de --ripple promete una verificacion visual "
                      "que no existe")


# --- las dos barandas que dejo el dia que se trabo el teclado --------------
# Un macro de dos eventos `dir0` dejo la `a` y la `b` apretadas,
# y despegarlas obligo a desacoplar el dongle: apretar la tecla fisica no
# alcanzaba, porque el sistema ya la tenia por apretada. Las dos avisan y
# ninguna prohibe -eran justo el experimento que cerro la direccion- pero el
# aviso tiene que llegar ANTES de escribir, que es lo unico que lo hace util.
def test_advertencias_de_eventos(fallos: list[str]) -> None:
    from linshark import estructuras as e

    pe = _cargar_primera_escritura()

    def texto(s: str) -> str:
        return "\n".join(
            pe.advertencias_de_eventos(e.eventos_desde_texto(s)))

    # el macro que trabo el teclado
    trabador = texto("a:dir0@10, b:dir0@10")
    if "APRETADO" not in trabador:
        fallos.append("no se avisa que el macro deja teclas apretadas")
    if "a, b" not in trabador:
        fallos.append(f"el aviso no dice cuales quedan apretadas: {trabador!r}")
    if "dongle" not in trabador:
        fallos.append("el aviso no dice como se despega: apretar la tecla no "
                      "alcanza, hay que desacoplar el dongle")

    # el macro de un solo evento, que el mouse guarda y no reproduce
    corto = texto("a:dir0@10")
    if "NO SE REPRODUCE" not in corto:
        fallos.append("no se avisa que un macro de un evento no corre")

    # y los que estan bien no gastan la alarma: si esto suena siempre, deja de
    # significar algo (la leccion sobre las alarmas falsas).
    for sano in ("a:dir0@10, a:dir1@10",
                 "clic-izquierdo:dir0@10, clic-izquierdo:dir1@10",
                 # soltar algo que nunca se apreto no deja nada colgado
                 "a:dir1@10, a:dir0@10, a:dir1@10"):
        if pe.advertencias_de_eventos(e.eventos_desde_texto(sano)):
            fallos.append(f"advertencia de mas en un macro sano: {sano}")

    # el macro capturado del soft nativo, que es sano, no puede avisar
    base = ("clic-izquierdo:dir0@10, clic-izquierdo:dir1@10, "
            "clic-rueda:dir0@10, clic-rueda:dir1@10, atras:dir0@10, "
            "atras:dir1@10, adelante:dir0@10, adelante:dir1@10, "
            "clic-derecho:dir0@10, clic-derecho:dir1@10")
    if pe.advertencias_de_eventos(e.eventos_desde_texto(base)):
        fallos.append("el macro capturado del soft dispara una advertencia")


# --- cambiar el color de la luz sin tocar el resto del bloque --------------
# Misma idea que el dpi: escribirle el color que YA tiene tiene que reproducir
# el bloque byte a byte. Si un offset o el checksum interno estuvieran mal,
# saldria distinto. Y ademas se comprueba lo que NO se mueve, porque el bloque
# de cmd 5 lleva encima el tiempo de hibernacion y el de respuesta: tocarlos
# sin querer seria cambiarle al mouse algo que nadie pidio.

def test_escribir_color_luz(fallos: list[str]) -> None:
    from linshark import estructuras as e

    leido = bytes.fromhex(LUZ_LEIDO[2])
    campos = e.decodificar(e.ILUMINACION_FIXED, leido)
    actual = (campos["redColor"], campos["greenColor"], campos["blueColor"])

    # 1. idempotente: el mismo color reproduce el bloque exacto.
    igual = e.escribir_color_luz(leido, actual)
    if igual != leido:
        fallos.append(f"reescribir el color que ya tiene dio otro bloque\n"
                      f"      leido: {leido.hex()}\n"
                      f"      salio: {igual.hex()}")

    # 2. un cambio real mueve los tres bytes de color y el checksum, y NADA
    #    mas. Se elige un color que no sume lo mismo, para que el checksum
    #    tenga que moverse: si no, el punto 2b no probaria nada.
    nuevo = (0x11, 0x22, 0x33)
    cambiado = e.escribir_color_luz(leido, nuevo)
    pos = e.offsets(e.ILUMINACION_FIXED)
    fin = e.fin_de_campos(e.ILUMINACION_FIXED)
    permitidos = {pos["redColor"][0], pos["greenColor"][0],
                  pos["blueColor"][0], fin, fin + 1}
    movidos = {i for i in range(len(leido)) if leido[i] != cambiado[i]}
    if not movidos <= permitidos:
        de_mas = sorted(movidos - permitidos)
        nombres = [n for n, (o, _l) in pos.items() if o in de_mas]
        fallos.append(f"escribir_color_luz movio los offsets {de_mas} "
                      f"({', '.join(nombres) or 'cola'}), que no son el color")
    # 2b. y el checksum interno se movio de verdad.
    if not {fin, fin + 1} & movidos:
        fallos.append("el checksum interno no cambio con el color")

    # 3. el checksum interno del bloque nuevo cierra.
    esperado = int.from_bytes(cambiado[fin:fin + 2], "big")
    if e.checksum_interno(e.ILUMINACION_FIXED, cambiado) != esperado:
        fallos.append("el bloque con el color nuevo no lleva su checksum "
                      "interno bien puesto")

    # 4. y la trama sale valida para el dispositivo.
    trama = p.build_write_frame(
        bytes([e.ILUMINACION_FIXED, e.ILUMINACION_SIZE]) + cambiado)
    if not p.verify_frame(trama):
        fallos.append("la trama del color nuevo no valida su propio checksum")

    # 5. un componente fuera de rango no se recorta en silencio.
    for malo in ((256, 0, 0), (-1, 0, 0)):
        try:
            e.escribir_color_luz(leido, malo)
        except ValueError:
            pass
        else:
            fallos.append(f"escribir_color_luz acepto {malo}")


# --- el desenlace de una escritura: que cambio, y que NO -------------------
# Hasta `primera-escritura.py` devolvia 1 aunque el cambio fuera
# exactamente el que se pidio, o sea que decia "fallo" cuando habia salido todo
# bien. El codigo de salida es lo que mira quien encadene el script, asi que no
# es cosmetico. La decision se toma comparando POR COMANDO, no sobre el texto
# que arma `comparar()`.

def _cargar_respaldar():
    import importlib.util
    ruta = Path(__file__).resolve().parent.parent / "scripts" / "respaldar.py"
    spec = importlib.util.spec_from_file_location("respaldar", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _respaldo(cmds: dict) -> dict:
    return {"fecha": "", "nodo": "",
            "comandos": {str(k): (None if v is None else
                                  {"nombre": p.CMD_NAMES.get(k, f"cmd {k}"),
                                   "datos": v})
                         for k, v in cmds.items()}}


def test_diferencias_mira_los_dos_lados(fallos: list[str]) -> None:
    """Un campo que solo existe del lado nuevo tambien es una diferencia.

    `diferencias()` recorria las claves de `a`, asi que un campo que
    apareciera solo en `b` -otra version de firmware, un decodificador que
    aprendio a partir un byte- no se reportaba nunca. Lo encontro una
    auditoria externa leyendo el codigo.
    """
    from linshark import sesion

    def estado(campos, datos):
        return {"comandos": {"6": {"nombre": "report rate", "datos": datos,
                                   "campos": campos}}}

    a = estado({"profileId": 1}, "0144bb")
    b = estado({"profileId": 1, "nuevoCampo": 7}, "0154ab")
    difs = "\n".join(sesion.diferencias(a, b))
    if "nuevoCampo" not in difs:
        fallos.append(f"un campo que solo esta en el lado nuevo no se "
                      f"reporta: {difs!r}")
    # y al reves, uno que desaparece
    difs = "\n".join(sesion.diferencias(b, a))
    if "nuevoCampo" not in difs:
        fallos.append(f"un campo que desaparece no se reporta: {difs!r}")


# --- el veredicto del paso 6, que es la red de toda la Etapa 3 -------------
#
# Los seis casos, incluidos los dos que costaron un bug cada uno: una
# idempotente que no mueve un byte **es un exito**, y un cambio real tiene que
# mover lo que se pidio y nada mas -salvo el perfil completo, que embebe a los
# demas bloques y acompaña siempre-.

# --- el modelo con nombres propios -----------------------------------------
#
# La interfaz no tiene que saber que `SensitivityX` es el LOD ni que
# `LightBrightness` son cuatro bits de la hibernacion. Lo que se prueba aca es
# que la traduccion sea completa -no queden nombres del fabricante a la vista-,
# que los campos escribibles tengan rango u opciones, y que las advertencias
# medidas sigan puestas: son la razon por la que la aplicacion existe.

def _estado_de_prueba():
    BOT = ("01" + "020000030000040000050000060000" + "0d0000" + "3c0000"
           + "010000" * 9 + "0a0000" + "090000" + "0079")
    return {"comandos": {
        str(p.CMD_REPORT_RATE): {"datos": "0144bb00000000"},
        str(p.CMD_DPI): {"datos": DPI_REAL.hex()},
        str(p.CMD_LIGHTING): {"datos": LUZ_REAL.hex()},
        str(p.CMD_BUTTONS): {"datos": BOT},
    }}


def e_estructuras():
    from linshark import estructuras
    return estructuras


def test_modelo_con_nombres_propios(fallos: list[str]) -> None:
    from linshark import modelo
    from linshark import sesion

    campos = modelo.por_clave(_estado_de_prueba())
    if not campos:
        fallos.append("el modelo no saco ningun campo de un estado completo")
        return

    # 1. Ningun nombre del fabricante a la vista. Son los tres que el proyecto
    #    ya sabe que enseñan un modelo equivocado del dispositivo.
    del_fabricante = ("SensitivityX", "SensitivityY", "closeTime",
                      "LightBrightness", "breathingSpeed", "Dpi_X_setting",
                      "responseTime", "hibernateTime")
    for c in campos.values():
        texto = f"{c.clave} {c.nombre}"
        for malo in del_fabricante:
            if malo.lower() in texto.lower():
                fallos.append(f"el campo {c.clave!r} usa el nombre del "
                              f"fabricante ({malo})")

    # 2. Los campos que se pueden escribir tienen que decir QUE se puede
    #    escribir: sin rango ni opciones, una interfaz no puede ofrecerlos.
    for c in campos.values():
        if not c.escribible:
            continue
        tiene_limites = c.opciones or (c.minimo is not None
                                       and c.maximo is not None)
        if not tiene_limites and c.clave not in ("color",):
            fallos.append(f"{c.clave!r} es escribible y no dice su rango ni "
                          "sus opciones")

    # 2b. Cada campo dice que es, para quien lo va a tocar: es lo que la
    #     ventana muestra detras del `?`. Y ahi no va la evidencia -fechas,
    #     citas, lo que hace el cliente oficial-, que se queda en `nota`.
    import re
    cita = re.compile(r"20\d\d-\d\d-\d\d|MEDID|INFERID|cliente oficial|"
                      r"bundle|captura|I-W\d", re.I)
    for c in campos.values():
        if not (c.definicion or c.aviso):
            fallos.append(f"{c.clave!r} no dice que es (definicion vacia)")
        for texto in (c.definicion, c.aviso):
            if cita.search(texto):
                fallos.append(f"{c.clave!r}: la definicion cita evidencia: "
                              f"{texto[:60]!r}")

    # 3. Las advertencias medidas siguen puestas.
    esperadas = {
        "dpi_nivel_1": "3311",          # la pagina lee con otra formula
        "ripple": "I-W24",              # la pagina los lee cruzados
        "lod": "simple vista",          # la unica verificacion visual barata
        "rueda": "invertido",           # la web rompe el scroll
        "nivel_activo": "LED",          # se ve
    }
    for clave, fragmento in esperadas.items():
        c = campos.get(clave)
        if c is None:
            fallos.append(f"falta el campo {clave!r}")
        elif fragmento not in c.nota:
            fallos.append(f"{clave!r} perdio su advertencia ({fragmento!r} no "
                          f"esta en la nota)")

    # 4. Donde el cliente oficial muestra otra cosa, el modelo lo dice.
    dpi1 = campos.get("dpi_nivel_1")
    if dpi1 is None or not dpi1.difiere_del_cliente_oficial:
        fallos.append("el dpi no marca que la pagina oficial muestra otro "
                      "numero, que es el caso testigo de I-W10")

    # 5. El clic izquierdo se ofrece en los botones 1 a 5, y en el 6 y el 7
    # no: estan en la base (decidido).
    clic = e_estructuras().FUNCIONES_DE_BOTON[e_estructuras().FUNCION_CLIC_IZQUIERDO]
    for c in campos.values():
        if c.slot is None:
            continue
        if not c.escribible:
            fallos.append(f"{c.clave!r} no se ofrece para remapear")
        dentro = c.slot in e_estructuras().SLOTS_PARA_CLIC_IZQUIERDO
        if dentro != (clic in c.opciones):
            fallos.append(f"{c.clave!r} (boton {c.slot}) "
                          f"{'no ' if dentro else ''}ofrece el clic izquierdo")

    # 6. Los colores del indicador van **pegados al nivel**, no como campos
    #    propios: se leen y no se escriben -ningun cliente oficial los escribe,
    #    asi que no hay captura de la que partir- y una fila por color era una
    #    fila que solo se podia mirar. Y solo los niveles que el mouse tiene
    #    cargados: el bloque reserva ocho y el LED de los que estan en cero no
    #    se prende nunca.
    if any(c.startswith("color_nivel_") for c in campos):
        fallos.append("los colores del indicador volvieron a salir como "
                      "campos propios")
    niveles = sorted(int(k.rsplit("_", 1)[1]) for k in campos
                     if k.startswith("dpi_nivel_"))
    if not niveles:
        fallos.append("el modelo no saco ningun nivel de dpi")
    for i in niveles:
        color = campos[f"dpi_nivel_{i}"].color
        del_bloque = est.color_de_nivel(DPI_REAL, i)
        if color is None:
            fallos.append(f"dpi_nivel_{i} no trae el color de su indicador")
        elif del_bloque is None or color.hexa != f"#{del_bloque[0]}":
            fallos.append(f"dpi_nivel_{i} dice {color.hexa!r} y el bloque "
                          f"tiene {del_bloque!r}")
        elif not color.nota:
            fallos.append(f"dpi_nivel_{i}: el color perdio lo que se sabe de "
                          "el (que ningun cliente oficial lo escribe)")
    # Un nivel que no existe no aporta ni dpi ni color.
    de_mas = [i for i in range(1, 9)
              if i not in niveles and est.color_de_nivel(DPI_REAL, i)
              and any(c.color and c.color.hexa == f"#{est.color_de_nivel(DPI_REAL, i)[0]}"
                      and c.clave.startswith("dpi_nivel_") for c in campos.values())]
    if de_mas:
        fallos.append(f"salieron niveles que el mouse no tiene: {de_mas}")
    # Y el nivel en uso lleva el color que el LED tiene prendido ahora.
    activo = campos.get("nivel_activo")
    if activo is not None and activo.valor in niveles:
        if activo.color != campos[f"dpi_nivel_{activo.valor}"].color:
            fallos.append("el nivel en uso no se marca con el color de su "
                          "propio nivel, que es el que se ve encendido")

    # 6 bis. El RGB del cmd 5 no se ofrece donde no enciende nada. En el X8 Pro
    #    se escribe, se relee cambiado y el chasis no prende (MEDIDO).
    #    Escribirlo sigue siendo posible por la biblioteca: I-W16
    #    esta abierto y esto es una decision de que mostrar, no de que se puede.
    #
    #    **Y las dos direcciones se prueban de verdad**: la decision vive en
    #    `Perfil.campos_ausentes`, asi que un perfil que no lo liste tiene que
    #    devolver el control **sin tocar el modelo ni la ventana**. Antes
    #    esto miraba una constante que valia False siempre, y la
    #    otra rama no se ejecutaba nunca.
    from linshark import dispositivos
    perfil = dispositivos.activo()
    if "color" not in perfil.campos_ausentes:
        fallos.append("el perfil dejo de decir que el RGB del cmd 5 no "
                      "enciende nada en este mouse")
    if "color" in campos:
        fallos.append("el RGB del cmd 5 se ofrece y no enciende nada en este "
                      "mouse")
    from dataclasses import replace
    con_rgb = replace(perfil, campos_ausentes={})
    if "color" not in modelo.por_clave(_estado_de_prueba(), con_rgb):
        fallos.append("con un perfil cuyo RGB enciende, el control no vuelve: "
                      "el campo quedo atado a algo que no es el perfil")
    # Y la afirmacion medida no se borro con el campo: se sigue citando.
    if "no encienden nada" not in modelo.NOTA_COLOR:
        fallos.append("NOTA_COLOR perdio lo que se midio")
    try:
        sesion.preparar_mutacion("color", "#00ff00")
    except Exception as exc:                        # noqa: BLE001
        fallos.append(f"el color dejo de poder escribirse por la biblioteca: "
                      f"{type(exc).__name__}: {exc}")

    # 7. Un mouse leido a medias tiene que dar los campos que si se leyeron,
    #    no reventar: la interfaz tiene que poder mostrar algo.
    parcial = {"comandos": {str(p.CMD_REPORT_RATE): {"datos": "0144bb00000000"}}}
    solo = modelo.por_clave(parcial)
    if "tasa" not in solo or len(solo) != 1:
        fallos.append(f"con un estado parcial saco {sorted(solo)}")


def test_veredicto_del_paso_6(fallos: list[str]) -> None:
    from linshark import sesion

    def estado(**bloques):
        return {"comandos": {str(c): {"nombre": p.CMD_NAMES.get(c, str(c)),
                                      "datos": d}
                             for c, d in bloques.items()}}

    rate, perfil, luz = p.CMD_REPORT_RATE, p.CMD_PROFILE, p.CMD_LIGHTING
    igual = estado(**{str(rate): "0144bb", str(perfil): "0144bb01",
                      str(luz): "aa"})
    casos = [
        # (antes, despues, cmd, idempotente, ok esperado, motivo)
        (igual, igual, rate, True, True, "sin-diferencias"),
        (igual, estado(**{str(rate): "0154ab", str(perfil): "0154ab01",
                          str(luz): "aa"}),
         rate, True, False, "idempotente-cambio-algo"),
        (igual, igual, rate, False, False, "no-cambio-nada"),
        (igual, estado(**{str(rate): "0144bb", str(perfil): "0144bb01",
                          str(luz): "bb"}),
         rate, False, False, "cambio-otra-cosa"),
        # lo pedido + el perfil que lo embebe: correcto
        (igual, estado(**{str(rate): "0154ab", str(perfil): "0154ab01",
                          str(luz): "aa"}),
         rate, False, True, "cambio-lo-pedido"),
        # lo pedido + algo que nadie toco: NO
        (igual, estado(**{str(rate): "0154ab", str(perfil): "0154ab01",
                          str(luz): "bb"}),
         rate, False, False, "cambio-de-mas"),
    ]
    for antes, despues, cmd, idem, ok, motivo in casos:
        v = sesion.juzgar(antes, despues, cmd=cmd, idempotente=idem)
        if v.ok != ok or v.motivo != motivo:
            fallos.append(f"juzgar({motivo}): dio ok={v.ok} motivo={v.motivo!r}, "
                          f"esperaba ok={ok} motivo={motivo!r}")
        if not v.explicacion or v.explicacion == v.motivo:
            fallos.append(f"el motivo {v.motivo!r} no tiene explicacion en "
                          "castellano")

    # El caso de "cambio de mas" tiene que decir QUE cambio de mas: si no, el
    # que lo lee no sabe donde mirar.
    v = sesion.juzgar(igual, estado(**{str(rate): "0154ab",
                                       str(perfil): "0154ab01",
                                       str(luz): "bb"}),
                      cmd=rate, idempotente=False)
    if v.inesperados != frozenset({luz}):
        fallos.append(f"no nombro el comando que sobro: {v.inesperados}")


def test_que_cambio_en_una_escritura(fallos: list[str]) -> None:
    respaldar = _cargar_respaldar()
    rate, perfil, luz = p.CMD_REPORT_RATE, p.CMD_PROFILE, p.CMD_LIGHTING
    casos = (
        # El caso real, en las dos direcciones: cambia el rate y
        # con el el perfil completo, que arranca con sus tres primeros bytes.
        ({rate: "0134cb", perfil: "0134cb01", luz: "aa"},
         {rate: "0144bb", perfil: "0144bb01", luz: "aa"},
         {rate, perfil}, "rate y el perfil que lo embebe"),
        # Escritura idempotente: el resultado bueno es que no cambie nada.
        ({rate: "0134cb", luz: "aa"}, {rate: "0134cb", luz: "aa"},
         set(), "idempotente, no cambia nada"),
        # Lo que tiene que encender la alarma: se movio algo que no se toco.
        ({rate: "0134cb", luz: "aa"}, {rate: "0144bb", luz: "bb"},
         {rate, luz}, "cambio un comando que no se toco"),
        # Un comando que no contesto no se puede comparar: no es un cambio.
        ({rate: "0134cb", luz: None}, {rate: "0144bb", luz: "bb"},
         {rate}, "sin respuesta no cuenta como cambiado"),
    )
    for antes, despues, esperado, que in casos:
        obtenido = respaldar.cmds_que_cambiaron(_respaldo(antes),
                                                _respaldo(despues))
        if obtenido != esperado:
            fallos.append(f"{que}: dio {sorted(obtenido)}, esperaba "
                          f"{sorted(esperado)}")


# --- las estructuras, contra las capturas reales del mouse -----------------

# Los datos que devolvio el X8 Pro (dev/models/attackshark-x8pro/docs/bitacora.md).
LUZ_REAL = bytes.fromhex("010003a800ff00010401af0000")
DPI_REAL = bytes.fromhex("0101013f2000172f3f6f9f8f0000000000000001000001ff0000"
                         "00ff000000ffffff0000ffffff00ffff4000ffffff020fba0000"
                         "0000")


# --- cmd 8: botones ---------------------------------------------------------
# El bloque de fabrica, tal como lo devuelve el mouse. Identico en los 44
# respaldos.
BOTONES_REAL = bytes.fromhex(
    "01" "020000" "030000" "040000" "050000" "060000" "0d0000" "3c0000"
    + "010000" * 9 + "0a0000" "090000" "0079")
# Y los dos bloques que el bus muestra escribiendo, uno de cada cliente
# oficial, los dos con el mouse en fabrica: el ultimo de `soft-todo.pcap`
# (t+175s) y el ultimo de `web-todo.pcap` (t+155s).
BOTONES_ESCRIBE_EL_SOFT = bytes.fromhex(
    "01" "020000" "030000" "040000" "0d0000" "050000" "060000" "3c0000"
    + "010000" * 9 + "0a0000" "090000" "0079")
BOTONES_ESCRIBE_LA_WEB = bytes.fromhex(
    "01" "020000" "030000" "040000" "0d0000" "050000" "060000" "3c0000"
    + "010000" * 9 + "090000" "0a0000" "0079")
# Y lo que el mouse devolvio 16:18, despues de que el soft nativo
# remapeara el boton fisico del costado-adelante a "reproducir / pausar"
# (`dev/models/attackshark-x8pro/respaldos/20260910-161848.json`). Es el experimento de la inferencia 14.
BOTONES_TRAS_REMAPEO = bytes.fromhex(
    "01" "020000" "030000" "040000" "050000" "180000" "0d0000" "3c0000"
    + "010000" * 9 + "0a0000" "090000" "008b")


def test_botones(fallos: list[str]) -> None:
    """La estructura de cmd 8 y los tres hallazgos del bus."""
    from linshark import estructuras as e

    # El largo no es una eleccion: 1 profileId + 18*3 + 2 checksum = 57, que es
    # sizeTotalData - 2. Con 17 o 19 botones no cierra, y el checksum interno
    # -que se calcula desde la tabla, no a mano- no caeria donde cae.
    if e.BOTONES_CANTIDAD != 18:
        fallos.append(f"BOTONES_CANTIDAD={e.BOTONES_CANTIDAD}, esperaba 18")
    if e.fin_de_campos(e.BOTONES_FIXED) != 55:
        fallos.append(f"los campos de cmd 8 terminan en "
                      f"{e.fin_de_campos(e.BOTONES_FIXED)}, esperaba 55")
    for nombre, bloque in (("fabrica", BOTONES_REAL),
                           ("soft", BOTONES_ESCRIBE_EL_SOFT),
                           ("web", BOTONES_ESCRIBE_LA_WEB)):
        if len(bloque) != e.BOTONES_SIZE - 2:
            fallos.append(f"el bloque {nombre} mide {len(bloque)} B, "
                          f"esperaba {e.BOTONES_SIZE - 2}")
            continue
        fin = e.fin_de_campos(e.BOTONES_FIXED)
        esperado = int.from_bytes(bloque[fin:fin + 2], "big")
        if e.checksum_interno(e.BOTONES_FIXED, bloque) != esperado:
            fallos.append(
                f"el checksum interno del bloque {nombre} no reproduce el de "
                f"la captura ({e.checksum_interno(e.BOTONES_FIXED, bloque):#06x}"
                f" contra {esperado:#06x})")

    # El bundle dice sizeTotalData=59 y el binario del helper dice sub=0x3b.
    # Dos fuentes independientes, como en las otras dos estructuras.
    if p.READ_SUB.get(e.BOTONES_FIXED) != e.BOTONES_SIZE:
        fallos.append(f"cmd 8: el bundle dice sizeTotalData={e.BOTONES_SIZE} y "
                      f"la tabla del binario dice "
                      f"sub={p.READ_SUB.get(e.BOTONES_FIXED)}")

    bots = e.botones_de(BOTONES_REAL)
    if bots is None or len(bots) != 18:
        fallos.append(f"botones_de() devolvio {bots and len(bots)}, esperaba 18")
        return
    # Las siete funciones que el mouse trae asignadas, decodificadas con la
    # tabla del bundle. Si la estructura se corriera un byte, ninguna daria.
    esperadas = {1: "clic izquierdo", 2: "clic derecho", 3: "clic de rueda",
                 4: "atras", 5: "adelante", 6: "ciclo de dpi",
                 7: "tecla de modo"}
    for indice, nombre in esperadas.items():
        visto = bots[indice - 1]["nombre"]
        if visto != nombre:
            fallos.append(f"boton {indice}: {visto!r}, esperaba {nombre!r}")
    if sum(1 for b in bots if b["nombre"] == "apagado") != 9:
        fallos.append("esperaba 9 slots apagados en el bloque de fabrica")

    # El 60 esta en la tabla de escritura del bundle y NO en la de nombres, y
    # aun asi es lo que el mouse trae de fabrica en el slot 7. Si alguien
    # rearma FUNCIONES_DE_BOTON desde Rve solamente, esto se pone rojo.
    if e.FUNCIONES_DE_BOTON.get(60) is None:
        fallos.append("el codigo 60 (FUN_MODE_KEY), que el mouse trae de "
                      "fabrica, se quedo sin nombre")

    # Hallazgo 2: los dos clientes oficiales escriben la rueda al reves uno del
    # otro. Los dos bloques son escrituras, asi que la comparacion es directa.
    par_soft = tuple(BOTONES_ESCRIBE_EL_SOFT[1 + 3 * (n - 1)]
                     for n in e.SLOTS_DE_RUEDA)
    par_web = tuple(BOTONES_ESCRIBE_LA_WEB[1 + 3 * (n - 1)]
                    for n in e.SLOTS_DE_RUEDA)
    if par_soft != e.RUEDA_COMO_EL_SOFT:
        fallos.append(f"el bloque del soft escribe {par_soft} en los slots de "
                      f"la rueda, la constante dice {e.RUEDA_COMO_EL_SOFT}")
    if par_web != e.RUEDA_COMO_LA_WEB:
        fallos.append(f"el bloque de la web escribe {par_web} en los slots de "
                      f"la rueda, la constante dice {e.RUEDA_COMO_LA_WEB}")
    if par_soft == par_web:
        fallos.append("los dos clientes escriben la rueda igual: el hallazgo "
                      "medido dice que no, revisar cual bloque cambio")
    # Y los dos bloques son iguales en todo lo demas: eso es lo que hace que el
    # desacuerdo sea de esos dos bytes y no de otra cosa.
    sin_rueda = slice(0, 1 + 3 * 16)
    if BOTONES_ESCRIBE_EL_SOFT[sin_rueda] != BOTONES_ESCRIBE_LA_WEB[sin_rueda]:
        fallos.append("los bloques del soft y de la web difieren fuera de los "
                      "slots de la rueda: la comparacion ya no aisla el campo")

    # Hallazgo 3, MEDIDO con un A/B directo: la escritura del soft
    # capturada a las 17:21:05 y la lectura de las 17:22:58, misma sesion. Es la
    # prueba fuerte de la permutacion, y por eso se fija byte a byte.
    escrito_ab = BOTONES_ESCRIBE_EL_SOFT
    leido_ab = BOTONES_REAL
    for leido_slot, escrito_slot in e.SLOT_ESCRITO_DE_LEIDO.items():
        ve = escrito_ab[1 + 3 * (escrito_slot - 1)]
        vl = leido_ab[1 + 3 * (leido_slot - 1)]
        if ve != vl:
            fallos.append(
                f"el A/B no cierra: escrito[{escrito_slot}]={ve:#04x} pero "
                f"leido[{leido_slot}]={vl:#04x}")
    # Y fuera de esos tres, escritura y lectura tienen que coincidir slot a slot.
    for n in range(1, 19):
        if n in e.SLOTS_QUE_SE_REMAPEAN:
            continue
        o = 1 + 3 * (n - 1)
        if escrito_ab[o:o + 3] != leido_ab[o:o + 3]:
            fallos.append(f"el slot {n} difiere entre escritura y lectura, y no "
                          "esta entre los que se remapean")

    # Los usage de macro son OTRA tabla, y confundirlas seria caro: el codigo 2
    # es "clic izquierdo" en los botones y una tecla de teclado en un macro.
    if e.MACRO_USAGE_BOTONES.get(241) != "clic izquierdo":
        fallos.append("la tabla de usage de macro perdio el 241")
    if set(e.MACRO_USAGE_BOTONES) & set(e.FUNCIONES_DE_BOTON):
        fallos.append("los usage de macro y los codigos de boton se solapan: "
                      "son tablas distintas y no pueden compartir claves")

    # Lo que sigue abierto: lo que el soft escribe en los
    # slots 4-6 no es lo que el mouse devuelve al leerlos. El test lo fija como
    # observacion, no como verdad del protocolo: si alguien "arregla" uno de
    # los dos bloques para que coincidan, esto avisa.
    escritos = tuple(BOTONES_ESCRIBE_EL_SOFT[1 + 3 * (n - 1)]
                     for n in e.SLOTS_QUE_SE_REMAPEAN)
    leidos = tuple(BOTONES_REAL[1 + 3 * (n - 1)]
                   for n in e.SLOTS_QUE_SE_REMAPEAN)
    if escritos == leidos:
        fallos.append("los slots 4-6 leidos coinciden con los escritos: el "
                      "remapeo MEDIDO ya no se ve, revisar")
    if sorted(escritos) != sorted(leidos):
        fallos.append(f"los slots 4-6 escritos {escritos} y leidos {leidos} no "
                      "son la misma multiconjunto: no es un remapeo")

    # El experimento sobre la inferencia 14. Lo que se fija es lo
    # que se observo, no la conclusion: el remapeo de UN boton fisico movio UN
    # solo slot leido, y fue el 5. Si alguien toca la permutacion sin repetir el
    # experimento, esto no lo deja pasar en silencio.
    if len(BOTONES_TRAS_REMAPEO) == len(BOTONES_REAL):
        movidos = [n for n in range(1, 19)
                   if BOTONES_REAL[1 + 3 * (n - 1)]
                   != BOTONES_TRAS_REMAPEO[1 + 3 * (n - 1)]]
        if movidos != [5]:
            fallos.append(f"el remapeo movio los slots {movidos},"
                          " se observo que movia solo el 5")
        tras = e.botones_de(BOTONES_TRAS_REMAPEO)
        if tras is None or tras[4]["nombre"] != "reproducir / pausar":
            fallos.append("el slot 5 tras el remapeo no da 'reproducir / pausar'")
        fin = e.fin_de_campos(e.BOTONES_FIXED)
        esperado = int.from_bytes(BOTONES_TRAS_REMAPEO[fin:fin + 2], "big")
        if e.checksum_interno(e.BOTONES_FIXED, BOTONES_TRAS_REMAPEO) != esperado:
            fallos.append("el checksum del bloque tras el remapeo no cierra")
    # El boton fisico que se remapeo es el del costado-adelante, y el soft lo
    # escribe en SU slot 6: por eso la permutacion manda el 6 escrito al 5 leido.
    if e.SLOT_ESCRITO_DE_LEIDO.get(5) != 6:
        fallos.append("la permutacion ya no manda el slot 6 escrito al 5 leido, "
                      "que es el par que confirmo el boton fisico")
    if sorted(e.SLOT_ESCRITO_DE_LEIDO) != sorted(e.SLOTS_QUE_SE_REMAPEAN):
        fallos.append("la permutacion y SLOTS_QUE_SE_REMAPEAN no hablan de los "
                      "mismos slots")
    # Las tres numeraciones tienen que componer. Es una verificacion
    # independiente de la permutacion: `SLOT_ESCRITO_DE_LEIDO` se infirio de
    # comparar el bus con un respaldo, y la numeracion de la UI
    # se observo en la pantalla del soft. Componer una con la otra
    # da la tabla leida **sin ajustar nada**; con otra permutacion no cerraria.
    for ui, escrito in e.BOTONES_UI_A_SLOT_ESCRITO.items():
        leido = next((l for l, esc in e.SLOT_ESCRITO_DE_LEIDO.items()
                      if esc == escrito), escrito)
        if leido != e.BOTONES_UI_DEL_SOFT[ui]:
            fallos.append(f"boton {ui} de la UI: escrito {escrito} -> leido "
                          f"{leido}, pero la tabla dice "
                          f"{e.BOTONES_UI_DEL_SOFT[ui]}")
    # Y el boton que se remapeo fue el 4 de la UI, que cae en el slot 5 leido.
    if e.BOTONES_UI_DEL_SOFT[4] != 5:
        fallos.append("el boton 4 de la UI dejo de caer en el slot 5 leido, que "
                      "es lo que se observo al remapearlo")

    # La rueda quedo medida girandola: el orden del soft es el que anda.
    if e.RUEDA_CORRECTA != e.RUEDA_COMO_EL_SOFT:
        fallos.append("RUEDA_CORRECTA dejo de ser la del soft nativo, que es la "
                      "que se verifico girando la rueda")

    # describir() no puede reventar con un bloque corto, que es la leccion:
    # el despacho tiene que ser total.
    for corto in (b"", BOTONES_REAL[:10], BOTONES_REAL[:54]):
        try:
            e.describir(e.BOTONES_FIXED, corto)
        except Exception as exc:            # noqa: BLE001
            fallos.append(f"describir() de cmd 8 revento con {len(corto)} B: "
                          f"{exc!r}")


def test_botones_fisicos_y_orden_de_botones(fallos: list[str]) -> None:
    """Los botones salen en orden físico, y cada slot trae su evidencia."""
    from linshark import estructuras as est
    from linshark import modelo

    estado = _estado_de_prueba()
    campos = [c for c in modelo.campos_de(estado) if c.cmd == p.CMD_BUTTONS]
    claves_en_orden = [c.clave for c in campos]
    esperadas = [
        "boton_izquierdo",
        "boton_derecho",
        "rueda",
        "boton_rueda",
        "boton_costado_atras",
        "boton_costado_adelante",
        "boton_dpi",
        "boton_modo",
    ]
    if claves_en_orden != esperadas:
        fallos.append(f"orden de botones: {claves_en_orden}, esperaba {esperadas}")

    fisicos = modelo.botones_fisicos(estado)
    if len(fisicos) != 7:
        fallos.append(f"botones_fisicos() devolvió {len(fisicos)} botones, esperaba 7")
    slots_vistos = [b.slot for b in fisicos]
    if slots_vistos != list(range(1, 8)):
        fallos.append(f"slots de botones físicos: {slots_vistos}, esperaba 1..7")

    for b in fisicos:
        if not b.confirmado:
            fallos.append(f"slot {b.slot} ({b.nombre}) figura sin confirmar")
        if not b.como_se_supo:
            fallos.append(f"slot {b.slot} no dice cómo se supo")
        if not est.boton_confirmado(b.slot):
            fallos.append(f"est.boton_confirmado({b.slot}) dio False")

    modo = next((c for c in campos if c.clave == "boton_modo"), None)
    if modo is None or "cambia el canal" not in modo.nota:
        fallos.append("el botón de modo perdió la advertencia de cambio de canal")
    elif "modo" not in modo.aviso or modo.definicion:
        fallos.append("el botón de modo tiene que llevar solo su aviso: "
                      f"{modo.definicion!r} / {modo.aviso!r}")
    # el numero de cada boton viaja en el campo, y es el del esquema
    numeros = {c.clave: c.slot for c in campos if c.slot is not None}
    if numeros != {b.clave: b.slot for b in fisicos}:
        fallos.append(f"los campos numeran distinto que el esquema: {numeros}")

    izq = next((c for c in campos if c.clave == "boton_izquierdo"), None)
    if izq is None or not izq.escribible:
        fallos.append("el botón izquierdo no se ofrece para escribir")

    if modelo.botones_fisicos({}) != []:
        fallos.append("botones_fisicos() con estado vacío no devolvió []")


def test_intercambiar_y_restaurar_cuidan_el_clic_izquierdo(fallos: list[str]) -> None:
    """Las dos cosas de la ventana que escriben mas de un boton.

    Intercambiar el 1 y el 2 es **una** escritura, y restaurar un mouse con
    los clics cruzados tiene que empezar por el boton que recibe el clic
    izquierdo: al reves, la baranda frenaria la primera escritura por dejar el
    mouse sin clic.
    """
    from linshark import estructuras as est
    from linshark import modelo
    from linshark import sesion

    estado = _estado_de_prueba()
    bloque = bytes.fromhex(estado["comandos"][str(p.CMD_BUTTONS)]["datos"])
    m = sesion.preparar_mutacion(modelo.ACCION_INTERCAMBIAR_CLICS, True)
    if m.cmd != p.CMD_BUTTONS:
        fallos.append(f"intercambiar escribe el cmd {m.cmd}, no el de botones")
    if m.codificar(bloque) != est.intercambiar_botones(bloque, a=1, b=2):
        fallos.append("el despachador no intercambia los botones 1 y 2")

    # el mouse con los clics cruzados, como lo deja el boton de intercambiar
    cruzado = bytearray(bloque)
    cruzado[1], cruzado[4] = cruzado[4], cruzado[1]
    estado_cruzado = {"comandos": {**estado["comandos"], str(p.CMD_BUTTONS):
                                   {"datos": bytes(cruzado).hex()}}}
    cambios = modelo.pendientes(estado_cruzado, modelo.SEGUROS)
    botones = [c for c, _, _ in cambios if c.startswith("boton_")]
    if botones[:2] != ["boton_izquierdo", "boton_derecho"]:
        fallos.append(f"restaurar no empieza por el clic izquierdo: {botones}")
    # y aplicadas en ese orden, ninguna escritura choca con la baranda
    actual = bytes(cruzado)
    for clave, _, valor in cambios:
        if not clave.startswith("boton_"):
            continue
        escrito = sesion.preparar_mutacion(clave, valor).codificar(actual)
        # el bloque escrito vuelve a la numeracion de lectura: los slots 4, 5
        # y 6 se permutan al escribir
        leido = dict((v, k) for k, v in est.SLOT_ESCRITO_DE_LEIDO.items())
        por_escrito = [escrito[1 + 3 * i:4 + 3 * i] for i in range(est.BOTONES_CANTIDAD)]
        nuevo = bytearray(actual)
        for escrito_n in range(1, est.BOTONES_CANTIDAD + 1):
            leido_n = leido.get(escrito_n, escrito_n)
            nuevo[1 + 3 * (leido_n - 1):4 + 3 * (leido_n - 1)] = por_escrito[escrito_n - 1]
        actual = bytes(nuevo)
    if est.con_clic_izquierdo(est.botones_de(actual)) != [1]:
        fallos.append("restaurar no dejo el clic izquierdo en el boton 1: "
                      f"{est.con_clic_izquierdo(est.botones_de(actual))}")


def test_estructuras(fallos: list[str]) -> None:
    from linshark import estructuras as e

    # Los dos primeros campos de toda estructura son fixed y sizeTotalData, y
    # el sizeTotalData tiene que ser el mismo numero que el proyecto viene
    # llamando `sub` en la tabla que saco del binario. Son dos fuentes
    # independientes: el bundle JS y el desensamblado del helper.
    for cmd, size in ((e.ILUMINACION_FIXED, e.ILUMINACION_SIZE),
                      (e.DPI_FIXED, e.DPI_SIZE)):
        if p.READ_SUB.get(cmd) != size:
            fallos.append(f"cmd {cmd}: el bundle dice sizeTotalData={size} y "
                          f"la tabla del binario dice sub={p.READ_SUB.get(cmd)}")

    luz = e.decodificar(e.ILUMINACION_FIXED, LUZ_REAL)
    # El LED estaba en verde cuando se leyo.
    if (luz["redColor"], luz["greenColor"], luz["blueColor"]) != (0, 255, 0):
        fallos.append(f"color decodificado {luz['redColor']},"
                      f"{luz['greenColor']},{luz['blueColor']}, esperaba 0,255,0")
    # El checksum interno de la estructura tiene que dar los dos bytes que
    # vienen en la cola de la propia captura.
    for nombre, cmd, bloque in (("iluminacion", e.ILUMINACION_FIXED, LUZ_REAL),
                                ("dpi", e.DPI_FIXED, DPI_REAL)):
        fin = e.fin_de_campos(cmd)
        esperado = int.from_bytes(bloque[fin:fin + 2], "big")
        if e.checksum_interno(cmd, bloque) != esperado:
            fallos.append(f"el checksum interno de {nombre} no reproduce el de "
                          f"la captura ({e.checksum_interno(cmd, bloque):#06x} "
                          f"contra {esperado:#06x})")

    d = e.decodificar(e.DPI_FIXED, DPI_REAL)
    # Los ocho colores de nivel tienen que ser los defaults del bundle.
    defaults = [(255,0,0), (0,255,0), (0,0,255), (255,255,0),
                (0,255,255), (255,0,255), (255,64,0), (255,255,255)]
    for i, esperado_rgb in enumerate(defaults, start=1):
        visto = tuple(d[f"Dpi_level_{i}_indication_flag"])
        if visto != esperado_rgb:
            fallos.append(f"Dpi_level_{i}: {visto}, el bundle dice {esperado_rgb}")
    if d["dpi_ON_OFF_flag"] != 63:
        fallos.append(f"dpi_ON_OFF_flag={d['dpi_ON_OFF_flag']}, esperaba 63")

    # Y el ancla mas fuerte: los DPI decodificados son los que la propia
    # pagina notifico en pantalla.
    from linshark import dpi as mod_dpi
    # DPI_REAL es el bloque de fabrica. Con el mouse en ese estado, la pagina
    # oficial muestra en pantalla 1200/2400/3200/5600/8000/40000 (observado).
    # El nivel 6 sale por la rama de `/100` de `Pu()`, marcada por
    # el bit 5 de DPI_X_Double_Flag = 0x20: sin ese bit darian 20000.
    niveles = mod_dpi.niveles_lineales(d["Dpi_X_setting"], d["Dpi_Y_setting"],
                                       d["DPI_X_Double_Flag"])
    if niveles[:6] != [1200, 2400, 3200, 5600, 8000, 40000]:
        fallos.append(f"niveles de dpi {niveles[:6]}, esperaba "
                      "[1200, 2400, 3200, 5600, 8000, 40000]")


# --- Request: una lectura cortada no es una escritura ----------------------

def test_lectura_cortada(fallos: list[str]) -> None:
    req = p.Request([0xF0, 0x83, 0x08])
    if not req.malformado:
        fallos.append("una lectura de 3 bytes no quedo marcada como malformada")
    if req.is_read:
        fallos.append("una lectura de 3 bytes paso como lectura valida")


# --- Etapa 2 de metodo.md: el estado leido del mouse, pasado por nuestro
# codificador, tiene que dar la trama que el driver oficial le escribio a ESTE
# mouse. No es "la captura se reproduce a si misma": el punto de partida es una
# lectura real (dev/models/attackshark-x8pro/respaldos/despues-de-los-resets.json) y el punto de
# llegada es una trama real del bus (dev/models/attackshark-x8pro/docs/capturas-w/soft-todo.pcap y
# web-todo.pcap). Que coincidan es lo que autoriza a pensar en escribir.

# report rate leido del mouse: cmd 6, sizeTotalData 9, datos 0144bb00000000
RATE_LEIDO = (6, 9, "0144bb00000000")
RATE_OFICIAL = "040e0006090144bb000000000121"

# dpi leido del mouse: cmd 4, sizeTotalData 56
DPI_LEIDO = (4, 56,
             "0101013f2000172f3f6f9f8f0000000000000001000002ff000000ff0000"
             "00ffffff0000ffffff00ffff4000ffffff020fbb00000000")
DPI_OFICIAL = ("043d0004380101013f2000172f3f6f9f8f0000000000000001000002ff00"
               "0000ff000000ffffff0000ffffff00ffff4000ffffff020fbb0000000011"
               "03")

# iluminacion leida del mouse: cmd 5, sizeTotalData 15.
# `dev/docs/metodo.md` daba esto por bloqueado ("hay 18 escrituras capturadas pero
# ninguna corresponde al estado que quedo leido en el respaldo"). No es asi: el
# estado que tienen los 14 respaldos desde las 19:00 sale identico a una trama
# que el driver oficial escribio 3 veces, en soft-todo.pcap,
# soft-rates-anotados.pcap y soft-rate-8000-a-1000.pcap.
#
# Y en la forma fuerte, que ademas es un viaje de ida y vuelta completo por el
# hardware: el driver oficial escribio esos bytes desde Windows (16:16), el
# mouse los guardo, nosotros los leimos desde Linux tres horas despues (19:00)
# y al recodificarlos vuelve a salir la misma trama. El estado de partida y la
# trama de llegada se midieron en maquinas y sistemas distintos.
LUZ_LEIDO = (5, 15, "010003a800ff00010901b40000")
LUZ_OFICIAL = "041400050f010003a800ff00010901b400000296"


def test_etapa2_ida_y_vuelta(fallos: list[str]) -> None:
    for (cmd, size, datos), oficial in ((RATE_LEIDO, RATE_OFICIAL),
                                        (DPI_LEIDO, DPI_OFICIAL),
                                        (LUZ_LEIDO, LUZ_OFICIAL)):
        bloque = bytes([cmd, size]) + bytes.fromhex(datos)
        trama = p.build_write_frame(bloque)
        nuestra = trama[:trama[1]].hex()
        if nuestra != oficial:
            fallos.append(
                f"cmd {cmd}: lo que armamos desde la lectura no es la trama "
                f"del driver oficial\n      nuestra: {nuestra}\n      "
                f"oficial: {oficial}")


# --- El camino por bloques, que hasta nunca se habia visto
# correr. `build_write_blocks()` es transcripcion del trio de 0x40d612 del
# helper oficial, y no habia con que contrastarla: cero tramas de cmd 9 en las
# diez capturas. `soft-macro-asignado.pcap` trajo cuatro escrituras de macro y
# las cuatro salen identicas, las dos tramas de cada una.
#
# El bloque es el mismo en las cuatro salvo el byte del modo de disparo y su
# reflejo en los checksums, asi que alcanza con guardar uno y variar ese byte:
# eso es justo lo que prueba que ESE byte es el modo.

MACRO_BLOQUE = ("096f1100000000010a0af18af10af38af30af58af50af48af40af28af2"
                + "00" * 80 + "0c6d")
MACRO_OFICIAL = {
    0: ("044000096f1100000000010a0af18af10af38af30af58af50af48af40af28af2"
        + "00" * 30 + "0d3a",
        "0439" + "01" + "00" * 50 + "0c6d" + "00b7"),
    1: ("044000096f1101000000010a0af18af10af38af30af58af50af48af40af28af2"
        + "00" * 30 + "0d3b",
        "0439" + "01" + "00" * 50 + "0c6e" + "00b8"),
    2: ("044000096f1102000000010a0af18af10af38af30af58af50af48af40af28af2"
        + "00" * 30 + "0d3c",
        "0439" + "01" + "00" * 50 + "0c6f" + "00b9"),
}


# --- Escribir el valor que el mouse ya tiene tiene que dar el MISMO bloque,
# byte a byte. De eso depende que `primera-escritura.py` pueda distinguir una
# escritura idempotente -que es con la que arranca la Etapa 3- de una que el
# mouse ignoro: la primera no mueve un byte al codificar, la segunda si.
#
# Antes el script avisaba en el paso 3 que el paso 6 lo iba a
# contar como fallo, y despues lo contaba como fallo: se contradecia solo y
# devolvia 1 con todo bien. Una alarma falsa gasta a las de verdad.

def test_reescribir_el_mismo_valor_no_mueve_un_byte(fallos: list[str]) -> None:
    from linshark import estructuras as e
    luz = bytes.fromhex(LUZ_LEIDO[2])
    dpi = bytes.fromhex(DPI_LEIDO[2])
    par = e.parametros_de_luz(luz)
    sen = e.parametros_de_sensor(dpi)
    casos = [
        ("luz --reposo", luz,
         e.escribir_reposo_ligero(luz, minutos=par["reposoMin"])),
        ("luz --hibernacion", luz,
         e.escribir_parametros_luz(luz, hibernacion=par["hibernateTime"])),
        ("luz --respuesta", luz,
         e.escribir_parametros_luz(luz, respuesta=par["responseTime"])),
        ("luz --color", luz, e.escribir_color_luz(luz, (
            e.decodificar(5, luz)["redColor"],
            e.decodificar(5, luz)["greenColor"],
            e.decodificar(5, luz)["blueColor"]))),
    ]
    for campo in ("lod", "ripple", "angle_snapping", "motion_sync"):
        casos.append((f"dpi --{campo}", dpi,
                      e.escribir_parametros_sensor(dpi, **{campo: sen[campo]})))
    niveles = _dpi_mod().niveles_lineales(
        e.decodificar(4, dpi)["Dpi_X_setting"],
        e.decodificar(4, dpi)["Dpi_Y_setting"],
        e.decodificar(4, dpi)["DPI_X_Double_Flag"])
    casos.append(("dpi --nivel 1", dpi,
                  e.escribir_nivel_dpi(dpi, 1, niveles[0])[0]))
    casos.append(("dpi --nivel-activo", dpi,
                  e.escribir_nivel_activo(dpi, nivel=e.nivel_activo_de(dpi))))
    # cmd 9 entra por el bloque ESCRITO, no por el leido: sobre una lectura
    # este codificador mueve dos bytes a proposito -da vuelta el checksum
    # invertido-, y esa es justamente su razon de existir (test_etapa2_macro).
    macro = bytes.fromhex(MACRO_BLOQUE)[2:]
    mac = e.parametros_de_macro(macro)
    casos.append(("macro --modo", macro, e.escribir_macro(macro)))
    casos.append(("macro --repeticiones", macro,
                  e.escribir_macro(macro, modo=mac["modo"],
                                   repeticiones=mac["repeticiones"])))
    for nombre, previo, nuevo in casos:
        if bytes(nuevo) != bytes(previo):
            fallos.append(
                f"{nombre}: reescribir el valor que ya estaba movio bytes\n"
                f"      previo: {bytes(previo).hex()}\n"
                f"      nuevo:  {bytes(nuevo).hex()}")


def _dpi_mod():
    from linshark import dpi as mod
    return mod


# --- Etapa 2 de cmd 8, y en las dos variantes que hacen falta.
#
# El punto de partida es una LECTURA real de este mouse
# (dev/models/attackshark-x8pro/respaldos/20260910-172258.json, 17:22:58) y los dos puntos de llegada son
# escrituras reales del driver oficial, de dos capturas distintas del mismo
# dia. Que la lectura se convierta en las dos es lo que autoriza a escribir
# este comando.
#
# La segunda importa mas que la primera: reproducir un CAMBIO, y no solo la
# identidad, es lo que descarta que estemos copiando bytes sin entenderlos.

BOTONES_LEIDO = ("010200000300000400000500000600000d00003c000001000001000001"
                 "0000010000010000010000010000010000010000" + "0a0000090000"
                 + "0079")
# soft-boton4-vuelve-adelante.pcap, 17:21:05 — el mouse de vuelta a fabrica
BOTONES_OFICIAL = ("010200000300000400000d00000500000600003c000001000001000001"
                   "0000010000010000010000010000010000010000" + "0a0000090000"
                   + "0079")
# soft-macro-asignado.pcap — el costado-adelante puesto en macro 0x11
BOTONES_OFICIAL_MACRO = ("010200000300000400000d00000500001200113c0000010000010000"
                         "010000010000010000010000010000010000010000"
                         + "0a0000090000" + "0096")


# --- La sonda de macros es angosta, y tiene que seguir siendolo.
#
# `--macro-id` pone el id del macro en el byte 5 de la lectura de cmd 9, donde
# los demas comandos llevan el perfil. Sale de `sendMacroDataCommand(macroId)`
# del bundle y **tiene una inferencia adentro** (que el helper copie ese byte
# al frame[5]), asi que es explicita y opcional: el default no cambia.
#
# El riesgo que este test cuida no es ese, es el otro: que esta opcion se
# vuelva el `--crudo` que el proyecto saco. Un solo comando, un solo byte, un
# rango validado, y todo por `build_read_frame()`.

def test_sonda_de_macro_es_angosta(fallos: list[str]) -> None:
    normal = p.build_read_frame(p.CMD_MACRO)
    conid = p.build_read_frame(p.CMD_MACRO, macro_id=0x11)
    difs = {i for i, (a, b) in enumerate(zip(normal, conid)) if a != b}
    # el byte 5 y el checksum, y nada mas. El checksum son dos bytes pero
    # puede moverse uno solo: si la diferencia no acarrea, el alto no cambia.
    permitidos = {5, len(normal) - 2, len(normal) - 1}
    if 5 not in difs or not difs <= permitidos:
        fallos.append(f"--macro-id movio los bytes {sorted(difs)}; solo puede "
                      "mover el 5 y el checksum")
    if conid[5] != 0x11 or conid[2] != p.READ_OPCODE or conid[3] != p.CMD_MACRO:
        fallos.append("--macro-id cambio algo que no es el byte 5")
    if not p.verify_frame(conid):
        fallos.append("la trama con macro_id no cierra el checksum")
    # solo cmd 9
    for cmd in sorted(p.READ_SUB):
        if cmd == p.CMD_MACRO:
            continue
        try:
            p.build_read_frame(cmd, macro_id=1)
        except ValueError:
            pass
        else:
            fallos.append(f"build_read_frame acepto macro_id para cmd {cmd}")
    # y el rango
    for malo in (0, 256, -1):
        try:
            p.build_read_frame(p.CMD_MACRO, macro_id=malo)
        except ValueError:
            pass
        else:
            fallos.append(f"build_read_frame acepto macro_id {malo}")
    # el default no cambia: sin pedirlo, el byte 5 sigue siendo el perfil
    if normal[5] != 1:
        fallos.append("la lectura de macro dejo de mandar el perfil por "
                      "defecto; eso cambia el comportamiento de respaldar.py")


def test_etapa2_botones(fallos: list[str]) -> None:
    from linshark import estructuras as e
    leido = bytes.fromhex(BOTONES_LEIDO)
    # 1. idempotente: NO es devolver el bloque crudo, es traducirlo
    nuestro = e.retraducir_botones(leido)
    if nuestro.hex() != BOTONES_OFICIAL:
        fallos.append(
            "cmd 8 idempotente: lo que armamos desde la lectura no es la "
            f"trama del driver oficial\n      nuestra: {nuestro.hex()}\n"
            f"      oficial: {BOTONES_OFICIAL}")
    if nuestro == leido:
        fallos.append(
            "cmd 8: el bloque a escribir salio IGUAL al leido. Los slots 4, 5 "
            "y 6 se remapean: devolverlo crudo le rota tres botones al mouse")
    # 2. con cambio real: el costado-adelante (slot leido 5) puesto en macro
    conmacro = e.escribir_boton(leido, slot=5, codigo=0x12, p2=0x11)
    if conmacro.hex() != BOTONES_OFICIAL_MACRO:
        fallos.append(
            "cmd 8 con cambio: asignar el macro no da la trama del driver "
            f"oficial\n      nuestra: {conmacro.hex()}\n"
            f"      oficial: {BOTONES_OFICIAL_MACRO}")
    # 3. las barandas. **Siempre queda un clic izquierdo en los botones 1 a
    # 5** (antes el slot 1 no se remapeaba).
    try:
        e.escribir_boton(leido, slot=1, codigo=6)
    except e.SinClicIzquierdo:
        pass
    else:
        fallos.append("escribir_boton() dejo sacar el unico clic izquierdo")
    for slot in (6, 7):
        try:
            e.escribir_boton(leido, slot=slot, codigo=e.FUNCION_CLIC_IZQUIERDO)
        except e.SinClicIzquierdo:
            pass
        else:
            fallos.append(f"escribir_boton() dejo poner el clic izquierdo en "
                          f"el boton {slot}, que esta en la base")
    # con otro clic izquierdo en el 2, el 1 si se remapea
    dos_clics = bytearray(leido)
    dos_clics[1 + 3 * 1] = e.FUNCION_CLIC_IZQUIERDO     # slot leido 2
    try:
        e.escribir_boton(bytes(dos_clics), slot=1, codigo=3)
    except e.SinClicIzquierdo as exc:
        fallos.append(f"con el clic izquierdo en el 2, el 1 no se dejo "
                      f"remapear: {exc}")
    # un mouse que ya llego sin clic izquierdo no queda bloqueado: la
    # escritura que lo arregla tiene que poder pasar
    sin_clic = bytearray(leido)
    sin_clic[1] = 3                                      # slot leido 1
    for slot, codigo in ((4, 24), (2, e.FUNCION_CLIC_IZQUIERDO)):
        try:
            e.escribir_boton(bytes(sin_clic), slot=slot, codigo=codigo)
        except e.SinClicIzquierdo as exc:
            fallos.append(f"sin clic izquierdo de antes, no se dejo escribir "
                          f"el boton {slot}: {exc}")
    # intercambiar el 1 y el 2: una escritura, y solo cambian esos dos bytes
    cruzado = e.intercambiar_botones(leido, a=1, b=2)
    distintos = [i for i, (x, y) in enumerate(zip(nuestro, cruzado)) if x != y]
    if distintos != [1, 4] or cruzado[1:7] != nuestro[4:7] + nuestro[1:4]:
        fallos.append(f"intercambiar 1 y 2 cambio los bytes {distintos}, no "
                      "la funcion de esos dos botones")
    try:
        e.intercambiar_botones(leido, a=1, b=6)
    except e.SinClicIzquierdo:
        pass
    else:
        fallos.append("intercambiar dejo el clic izquierdo en el boton 6")
    for slot in e.SLOTS_DE_RUEDA:
        try:
            e.escribir_boton(leido, slot=slot, codigo=6)
        except ValueError:
            pass
        else:
            fallos.append(f"escribir_boton() dejo tocar el slot de rueda {slot}")
    try:
        e.escribir_rueda(leido, orden=(1, 2))
    except ValueError:
        pass
    else:
        fallos.append("escribir_rueda() acepto un orden que nadie escribio")
    # 4. y el orden de rueda que se pide es el que sale
    for orden in (e.RUEDA_COMO_EL_SOFT, e.RUEDA_COMO_LA_WEB):
        salida = e.botones_de(e.escribir_rueda(leido, orden=orden))
        par = tuple(b["codigo"] for b in salida
                    if b["indice"] in e.SLOTS_DE_RUEDA)
        if par != orden:
            fallos.append(f"escribir_rueda({orden}) dejo {par}")


# --- El bloque de macro LEIDO del mouse, con los bytes reales de la corrida
# (`sondear.py --pedir 9 --macro-id 17`). Es el mismo layout de
# escritura salvo el checksum interno, que vuelve con los bytes al reves.
#
# El test fija las dos cosas: que se decodifique igual que el escrito, y que la
# inversion se detecte en vez de pasar por "checksum mal". Esa distincion es la
# baranda del dia que cmd 9 entre en WRITABLE: devolverle al mouse lo que
# devolvio, tal cual, le manda un checksum invertido.

MACRO_LEIDO = ("1100000000010a" + "0af18af10af38af30af58af50af48af40af28af2"
               + "00" * 80 + "6d0c")


# --- la rama larga de los eventos de macro (INFERIDA del bundle) ----------
#
# No hay captura con eventos de mas de 127 ms: en la unica que existe los diez
# son de 10 ms. Asi que este bloque **no sale del bus**, se arma con la regla
# de `Qve` en `app.js` -el constructor del layout de 111 bytes, que es el que
# le llega a este mouse- y lo que fija el test es que el decodificador lea esa
# regla, no que el mouse la use.
#
# Vale la pena igual: sin esto, un macro con un evento de 250 ms se leia como
# **dos** eventos, el segundo con "usage 3", y eso entra al respaldo.

def _macro_con_tiempos_largos() -> bytes:
    """Un bloque de macro armado con la regla de `Qve`. No es una captura."""
    eventos = bytearray()
    # corto, como lo escribe el soft nativo: sin el bit 0 que pone el bundle
    eventos += bytes([0x0a, 241])
    # largo, direccion 1: c = 253//100 = 2, d = 53, d |= 129
    eventos += bytes([53 | 129, 242, 2, 3])
    # largo, direccion 0: c = 350//100 = 3, d = 50, d |= 1  -> 51
    eventos += bytes([50 | 1, 243, 3, 3])
    datos = bytearray(109)
    datos[0] = 17                     # macroId
    datos[1] = 0                      # modo
    datos[5] = 1                      # repeticiones
    datos[6] = 5                      # PARES de bytes: 3 eventos + 2 largos
    datos[7:7 + len(eventos)] = eventos
    suma = sum(datos[1:107]) & 0xFFFF
    datos[107:109] = suma.to_bytes(2, "big")
    return bytes(datos)


def test_macro_con_tiempos_largos(fallos: list[str]) -> None:
    from linshark import estructuras as e

    m = e.parametros_de_macro(_macro_con_tiempos_largos())
    if m is None:
        fallos.append("el bloque con tiempos largos no cierra como macro")
        return
    if not m["checksum_ok"]:
        fallos.append("el bloque de prueba quedo con el checksum mal armado")
    if len(m["eventos"]) != 3:
        fallos.append(f"la rama larga se leyo como {len(m['eventos'])} eventos, "
                      "esperaba 3 (el par [centenas, 3] es continuacion, no un "
                      "evento con usage 3)")
        return
    tiempos = [(ev["tiempo"], ev["direccion"], ev["largo"])
               for ev in m["eventos"]]
    # El 351 no es un error del decodificador: el bundle fuerza el bit 0 al
    # partir el evento (`d|1`), asi que 350 ms viaja como 51 + 3 centenas. Se
    # lee lo que dice el byte, no lo que se quiso escribir.
    esperado = [(10, 0, False), (253, 1, True), (351, 0, True)]
    if tiempos != esperado:
        fallos.append(f"tiempos largos: {tiempos} != {esperado}")
    if any(ev["usageId"] == e.MACRO_USAGE_CONTINUACION
           for ev in m["eventos"]):
        fallos.append("un par de continuacion quedo como evento")

    # Y el texto tiene que decir que esos tiempos son inferidos, no medidos.
    texto = e.describir(p.CMD_MACRO, _macro_con_tiempos_largos())
    if "?" not in texto or "sin captura" not in texto:
        fallos.append(f"describir() no marca los tiempos inferidos: {texto!r}")

    # Un macro sin eventos largos no puede cambiar por esto: el bloque real que
    # este mouse devolvio tiene que seguir leyendose igual.
    real = e.parametros_de_macro(bytes.fromhex(MACRO_LEIDO))
    if len(real["eventos"]) != 10:
        fallos.append(f"el macro real cambio de largo: "
                      f"{len(real['eventos'])} eventos")
    if any(ev["largo"] for ev in real["eventos"]):
        fallos.append("el macro real quedo con eventos marcados como largos")
    if "?" in e.describir(p.CMD_MACRO, bytes.fromhex(MACRO_LEIDO)):
        fallos.append("el macro real quedo marcado como inferido")


def test_macro_leido_del_mouse(fallos: list[str]) -> None:
    from linshark import estructuras as e
    leido = bytes.fromhex(MACRO_LEIDO)
    escrito = bytes.fromhex(MACRO_BLOQUE)[2:]
    if len(leido) != len(escrito):
        fallos.append(f"el bloque leido mide {len(leido)} B y el escrito "
                      f"{len(escrito)}")
        return
    if leido[:-2] != escrito[:-2]:
        difs = [i for i, (x, y) in enumerate(zip(leido, escrito)) if x != y]
        fallos.append(f"leido y escrito difieren fuera del checksum: {difs}")
    m = e.parametros_de_macro(leido)
    if m is None:
        fallos.append("parametros_de_macro() no decodifica el bloque leido")
        return
    if not m["checksum_ok"] or m["checksumOrden"] != "little":
        fallos.append(f"el checksum del bloque leido tendria que detectarse "
                      f"invertido; salio orden={m['checksumOrden']} "
                      f"ok={m['checksum_ok']}")
    esc = e.parametros_de_macro(escrito)
    if esc["checksumOrden"] != "big":
        fallos.append(f"el del bloque escrito tendria que ser big-endian, "
                      f"salio {esc['checksumOrden']}")
    for campo in ("macroId", "modo", "repeticiones", "eventos", "checksumSuma"):
        if m[campo] != esc[campo]:
            fallos.append(f"el campo {campo} no coincide entre el bloque "
                          f"leido y el escrito")
    # y el resto de los comandos NO tiene esta rareza: sus lecturas traen el
    # checksum interno en el mismo orden que sus escrituras, que es lo que ya
    # comprueban test_etapa2_ida_y_vuelta y test_etapa2_botones.
    otros = [(4, DPI_LEIDO[2]), (5, LUZ_LEIDO[2]), (8, BOTONES_LEIDO)]
    for cmd, datos in otros:
        d = bytes.fromhex(datos)
        fin = e.fin_de_campos(cmd)
        if d[fin:fin + 2] != e.checksum_interno(cmd, d).to_bytes(2, "big"):
            fallos.append(f"cmd {cmd}: la lectura no trae el checksum interno "
                          "en big-endian; la rareza de cmd 9 no seria solo de "
                          "cmd 9")


# --- Etapa 2 de cmd 9: del bloque que el mouse devolvio a las tramas del
# driver oficial, byte a byte y en los tres modos.
#
# El punto de partida es una LECTURA real de este mouse
# (`sondear.py --pedir 9 --macro-id 17`) y los puntos de llegada
# son las cuatro escrituras del soft nativo en `soft-macro-asignado.pcap`. Que
# la lectura se convierta en las tres es lo que autoriza a escribir cmd 9.
#
# Y fija la baranda que hace falta el dia que entre en WRITABLE: la escritura
# **idempotente** de este comando no es devolver el bloque leido. Devolverlo
# tal cual manda el checksum interno al reves; el codificador lo da vuelta, y
# el test comprueba que mueve **exactamente esos dos bytes** y ninguno mas.


# --- La funcion "macro" de un boton necesita su id, y el mouse no avisa.
#
# `escribir_boton(codigo=18)` sin p2 arma el slot `12 00 00`: la funcion macro
# apuntando a un macro 0, que no existe. El mouse **acusa `0xC1` igual** -es un
# codigo valido de la tabla- asi que el fallo no se ve hasta apretar el boton.
# Antes el CLI aceptaba `--funcion macro` y escribia exactamente
# eso, porque nunca pasaba p2.
#
# Importa ahora porque la verificacion externa de cmd 9 es **apretar el
# boton**, y para eso primero hay que poder asignarle el macro con cmd 8.
#
# Se prueban los casos que FALLAN, que es lo unico que se puede probar sin
# hardware: el caso bueno termina en el mouse y lo corre el usuario. El subproceso
# lleva un nodo inexistente a proposito, para que algo que se colara por la
# validacion muera al abrir el dispositivo y no en el mouse.

def test_boton_macro_necesita_id(fallos: list[str]) -> None:
    from linshark import estructuras as e
    leido = bytes.fromhex(BOTONES_LEIDO)

    # 1. el codificador, que es lo que la aplicacion va a usar
    for p2 in (0, 256, -1):
        try:
            e.escribir_boton(leido, slot=5, codigo=e.FUNCION_MACRO, p2=p2)
        except ValueError:
            pass
        else:
            fallos.append(f"escribir_boton acepto la funcion macro con p2={p2}")
    try:
        con = e.escribir_boton(leido, slot=5, codigo=e.FUNCION_MACRO, p2=0x11)
    except ValueError as exc:
        fallos.append(f"escribir_boton rechazo un macro id valido: {exc}")
    else:
        if con != bytes.fromhex(BOTONES_OFICIAL_MACRO):
            fallos.append("asignar el macro 0x11 al costado-adelante dejo de "
                          "dar la trama del driver oficial")

    # y la tabla de las funciones con parametro es la fuente de esa baranda:
    # si manana aparece una tercera, el CLI la rechaza sola.
    if e.FUNCION_MACRO not in e.FUNCIONES_CON_PARAMETRO:
        fallos.append("la funcion macro salio de FUNCIONES_CON_PARAMETRO")
    for codigo in e.FUNCIONES_CON_PARAMETRO:
        if codigo not in e.FUNCIONES_DE_BOTON:
            fallos.append(f"FUNCIONES_CON_PARAMETRO tiene el codigo {codigo}, "
                          "que no esta en la tabla de funciones")

    # 2. el CLI, que es por donde se corre hoy
    import subprocess
    base = [sys.executable,
            str(Path(__file__).resolve().parent.parent / "scripts"
                / "primera-escritura.py"),
            "--hidraw", "/dev/hidraw-que-no-existe"]
    malos = [
        ("--funcion macro sin --macro-id",
         ["--comando", "botones", "--boton", "costado-adelante",
          "--funcion", "macro"]),
        ("--macro-id con una funcion que no lo lleva",
         ["--comando", "botones", "--boton", "costado-adelante",
          "--funcion", "adelante", "--macro-id", "17"]),
        ("--macro-id 0",
         ["--comando", "botones", "--boton", "costado-adelante",
          "--funcion", "macro", "--macro-id", "0"]),
        ("--macro-id 256",
         ["--comando", "botones", "--boton", "costado-adelante",
          "--funcion", "macro", "--macro-id", "256"]),
        ("--macro-id fuera de --comando botones",
         ["--comando", "rate", "--macro-id", "17"]),
        # --- y el comando nuevo, cmd 9 -------------------------------------
        # El id no es opcional aca por un motivo distinto del de botones: cmd
        # 9 es el unico comando que se lee con el id en el byte 5 y no con el
        # perfil, asi que sin id el mouse devuelve un bloque vacio y no hay
        # nada que reescribir.
        ("--comando macro sin --macro-id", ["--comando", "macro"]),
        ("--comando macro con --macro-id 0",
         ["--comando", "macro", "--macro-id", "0", "--modo", "1"]),
        ("--comando macro con --valor",
         ["--comando", "macro", "--macro-id", "17", "--valor", "1000"]),
        # el contador es del modo 0 y de ningun otro
        ("--repeticiones en un modo sin contador",
         ["--comando", "macro", "--macro-id", "17", "--modo", "1",
          "--repeticiones", "3"]),
        ("--repeticiones sin --modo",
         ["--comando", "macro", "--macro-id", "17", "--repeticiones", "3"]),
        ("--repeticiones 0",
         ["--comando", "macro", "--macro-id", "17", "--modo", "0",
          "--repeticiones", "0"]),
        ("--repeticiones 256",
         ["--comando", "macro", "--macro-id", "17", "--modo", "0",
          "--repeticiones", "256"]),
        ("--modo 3, que no se observo en el bus",
         ["--comando", "macro", "--macro-id", "17", "--modo", "3"]),
        # `--nivel-activo` dice cual nivel se USA; `--valor`, cuanto VALE uno.
        # Son dos campos del mismo bloque y va uno por corrida, como los
        # cuatro interruptores.
        ("--nivel-activo fuera de --comando dpi",
         ["--comando", "rate", "--nivel-activo", "2"]),
        ("--nivel-activo 0", ["--comando", "dpi", "--nivel-activo", "0"]),
        ("--nivel-activo 9", ["--comando", "dpi", "--nivel-activo", "9"]),
        ("--nivel-activo junto con --valor",
         ["--comando", "dpi", "--nivel-activo", "2", "--nivel", "1",
          "--valor", "1600"]),
        ("--nivel-activo junto con un interruptor",
         ["--comando", "dpi", "--nivel-activo", "2", "--ripple", "1"]),
        # El atajo de teclado tiene el mismo agujero que tenia el macro:
        # necesita modificadores en p1 y un usage HID en p2, y no hay interfaz
        # para eso. Escribirlo pelado deja el slot en `11 00 00` y el mouse lo
        # acusa igual.
        ("--funcion atajo de teclado, que lleva parametros sin interfaz",
         ["--comando", "botones", "--boton", "costado-adelante",
          "--funcion", "atajo de teclado"]),
        ("--modo fuera de --comando macro",
         ["--comando", "rate", "--modo", "1"]),
        ("--repeticiones fuera de --comando macro",
         ["--comando", "rate", "--repeticiones", "3"]),
    ]
    for nombre, args in malos:
        r = subprocess.run(base + args, capture_output=True, text=True,
                           timeout=60)
        if r.returncode != 2:
            fallos.append(
                f"el CLI tendria que rechazar {nombre} con codigo 2; salio "
                f"{r.returncode}\n      {r.stderr.strip()[:200]}")


# --- El mensaje del paso 3 para cmd 9, que la primera corrida real destapo.
#
# Al pasar el macro 17 del modo 0 al 2, el CLI imprimio
#
#     CAMBIO REAL: macro 17, modo reproducir N veces -> mantener apretado
#                  y repeticiones 1 -> None
#
# con el byte de repeticiones **sin moverse**: vale 1 en los dos bloques. Lo
# que se va al salir del modo 0 es el significado del byte, no su valor, y
# `parametros_de_macro()` devuelve None justamente para no inventar un contador
# donde no lo hay. Anunciarlo como "1 -> None" convierte esa honestidad del
# decodificador en un cambio de valor que no ocurrio.
#
# Mismo patron que la alarma falsa: el que mira la salida tiene
# que poder creerle a la lista de lo que cambio.

def test_mensaje_de_cambio_de_macro(fallos: list[str]) -> None:
    from linshark import estructuras as e
    pe = _cargar_primera_escritura()
    leido = bytes.fromhex(MACRO_LEIDO)

    def par(bloque):
        return e.parametros_de_macro(bloque)

    base = par(e.escribir_macro(leido))          # modo 0, repeticiones 1

    # 1. salir del modo 0 no es un cambio de repeticiones
    a_dos = par(e.escribir_macro(leido, modo=2))
    texto = pe.describir_cambio_de_macro(base, a_dos, 17)
    if "repeticiones" in texto:
        fallos.append(f"el mensaje habla de repeticiones al salir del modo 0, "
                      f"donde el byte no se movio: {texto!r}")
    if "None" in texto:
        fallos.append(f"el mensaje del paso 3 muestra un None: {texto!r}")
    if "mantener apretado" not in texto or "CAMBIO REAL" not in texto:
        fallos.append(f"el mensaje no dice el cambio de modo: {texto!r}")

    # 2. entrar al modo 0 SI dice cuanto vale el contador, y no de donde viene
    de_vuelta = pe.describir_cambio_de_macro(a_dos, base, 17)
    if "repeticion" not in de_vuelta:
        fallos.append(f"al entrar al modo 0 el mensaje no dice el contador: "
                      f"{de_vuelta!r}")
    if "None" in de_vuelta:
        fallos.append(f"al entrar al modo 0 el mensaje muestra un None: "
                      f"{de_vuelta!r}")

    # 3. cambiar solo el contador, dentro del modo 0
    cinco = par(e.escribir_macro(leido, modo=0, repeticiones=5))
    texto = pe.describir_cambio_de_macro(base, cinco, 17)
    if "1 -> 5" not in texto:
        fallos.append(f"un cambio de contador dentro del modo 0 no se informa: "
                      f"{texto!r}")

    # 4. y el caso sin cambios es idempotente, no un "cambio real" vacio
    texto = pe.describir_cambio_de_macro(base, base, 17)
    if not texto.startswith("IDEMPOTENTE"):
        fallos.append(f"reescribir el mismo disparo no se informa como "
                      f"idempotente: {texto!r}")

    # 5. grabar eventos es el cambio grande de cmd 9 -la lista entera-, y el
    #    mensaje tiene que decir cuantos eran, cuantos son y como quedan: el
    #    diff del paso 6 va a mostrar cincuenta bytes moviendose y con
    #    "IDEMPOTENTE" arriba nadie entenderia nada.
    grabado = par(e.escribir_eventos_macro(leido, [("a", 0, 10), ("a", 1, 10)]))
    texto = pe.describir_cambio_de_macro(base, grabado, 17)
    if "CAMBIO REAL" not in texto or "10 eventos -> 2" not in texto:
        fallos.append(f"grabar eventos no se informa como cambio: {texto!r}")
    if "a:dir0@10" not in texto:
        fallos.append(f"el mensaje no dice como quedan los eventos: {texto!r}")
    # y reescribir los mismos eventos sigue siendo idempotente
    igual = par(e.escribir_eventos_macro(leido, base["eventos"]))
    if not pe.describir_cambio_de_macro(base, igual, 17).startswith(
            "IDEMPOTENTE"):
        fallos.append("reescribir los mismos eventos no se informa como "
                      "idempotente")

    # 6. el despacho es total: ninguna combinacion de los tres modos revienta
    #    ni sale vacia, que es lo que agarro aquel bug.
    todos = [par(e.escribir_macro(leido, modo=m)) for m in e.MACRO_MODOS]
    for a in todos:
        for b in todos:
            t = pe.describir_cambio_de_macro(a, b, 17)
            if not t or "None" in t:
                fallos.append(f"modo {a['modo']} -> {b['modo']}: {t!r}")


# El paso 6 tiene que releer los MISMOS macros que el paso 1, o su lista de
# cambios miente. Las dos direcciones aparecieron contra el hardware el mismo
# dia, y ninguna era un cambio en el mouse:
#
#   * al ASIGNAR el macro 17 a un boton (12:36), el previo no lo traia -ningun
#     slot lo apuntaba- y el posterior si: "no contesto (A)";
#   * al DESASIGNARLO (17:12), el previo si y el posterior no: "(B)".
#
# La primera se tapo metiendo `--macro-id` en el respaldo previo; la segunda no
# la cubre, porque esa corrida es de `--comando botones --funcion adelante` y
# no lleva `--macro-id`. La lista sale del respaldo previo, que es lo unico que
# sabe que macros habia antes de escribir.

# --- la capa que va a usar la aplicacion -----------------------------------
#
# `linshark.sesion` salio de `driver/scripts/respaldar.py`, y lo que se
# movio es justo lo que sostiene la red: leer los siete bloques, reintentar lo
# que el enlace pierda, traer los macros que los slots apuntan y comparar dos
# estados. Nada de eso se puede probar contra el mouse desde un test -el
# hardware lo corre el usuario-, asi que se prueba contra un dispositivo falso que
# contesta los bloques que este mouse devolvio de verdad.
#
# Y hay una cosa mas que fijar: **el JSON tiene que seguir siendo el mismo**.
# Hay 82 respaldos versionados y `respaldar.py --comparar` compara uno de hoy
# contra uno; si cambiaran las claves, la red de toda escritura
# se corta en silencio.

class DeviceFalso:
    """Contesta `leer()` con bloques reales. Puede fallar a pedido."""

    def __init__(self, bloques, fallan=(), macros=None):
        self.bloques = dict(bloques)
        self.macros = dict(macros or {})
        # cmds que fallan la primera vez que se los pide, para ejercitar la
        # segunda pasada sin esperar los 3 s del respiro de verdad.
        self.fallan = set(fallan)
        self.pedidos: list[tuple[int, int | None]] = []

    async def leer(self, cmd, sub=None, macro_id=None):
        self.pedidos.append((cmd, macro_id))
        if macro_id is not None:
            datos = self.macros.get(macro_id)
        elif cmd in self.fallan:
            self.fallan.discard(cmd)
            return None
        else:
            datos = self.bloques.get(cmd)
        if datos is None:
            return None
        return Frame(report_id=4, length=len(datos) + 5, opcode=p.WRITE_OPCODE,
                     cmd=cmd, sub=len(datos), data=datos, checksum_ok=True)


async def test_sesion_lee_el_estado_entero(fallos: list[str]) -> None:
    from linshark import sesion

    # El macro 17 asignado al costado-adelante, que es como estuvo el mouse
    # entre las 16:36 y las 17:12.
    botones_con_macro = bytes.fromhex(
        "01" "020000" "030000" "040000" "050000" "120011" "0d0000" "3c0000"
        + "010000" * 9 + "0a0000" "090000" "0096")
    dev = DeviceFalso(
        {p.CMD_VERSION: bytes.fromhex("0b0808008301050000"),
         p.CMD_REPORT_RATE: bytes.fromhex("0144bb"),
         p.CMD_LIGHTING: LUZ_REAL,
         p.CMD_DPI: DPI_REAL,
         p.CMD_BUTTONS: botones_con_macro,
         p.CMD_MACRO: bytes.fromhex("01" + "ff" * 108),
         p.CMD_PROFILE: bytes.fromhex("0144bb01")},
        macros={0x11: bytes.fromhex(MACRO_LEIDO)})

    estado = await sesion.leer_estado(dev, nodo="/dev/hidrawX")

    if sesion.incompletos(estado):
        fallos.append(f"faltaron comandos sin que el enlace fallara: "
                      f"{sesion.incompletos(estado)}")
    # El formato del respaldo, clave por clave.
    if set(estado) != {"fecha", "nodo", "comandos", "macros"}:
        fallos.append(f"el JSON del estado cambio de forma: {sorted(estado)}")
    entrada = estado["comandos"][str(p.CMD_DPI)]
    if set(entrada) < {"nombre", "sizeTotalData", "datos", "checksum_ok",
                       "campos", "legible"}:
        fallos.append(f"la entrada de un comando perdio claves: "
                      f"{sorted(entrada)}")
    if entrada["datos"] != DPI_REAL.hex():
        fallos.append("el bloque guardado no es el que contesto el mouse")

    # **El macro se lee con su id**, y el id sale del slot de cmd 8, no de una
    # lista escrita a mano. Es lo que arreglo el agujero del respaldo previo.
    if "17" not in estado.get("macros", {}):
        fallos.append("el estado no trajo el macro que el boton apunta")
    elif estado["macros"]["17"]["datos"] != MACRO_LEIDO:
        fallos.append("el macro guardado no es el que contesto el mouse")
    if (p.CMD_MACRO, 0x11) not in dev.pedidos:
        fallos.append(f"no se pidio el macro con su id: {dev.pedidos}")

    # El respiro entre fallos son 3 s MEDIDOS contra el dongle, y en un test
    # solo son espera: los dos casos de abajo lo unico que miran es el camino.
    respiro = sesion.RESPIRO_TRAS_FALLO
    sesion.RESPIRO_TRAS_FALLO = 0
    try:
        # Un mouse que no contesta nada no puede reventar ni inventar macros.
        vacio = await sesion.leer_estado(DeviceFalso({}), nodo="")
        if set(sesion.incompletos(vacio)) != set(sesion.A_LEER):
            fallos.append("un mouse que no contesta nada tendria que dar los "
                          f"siete incompletos: {sesion.incompletos(vacio)}")
        if vacio.get("macros"):
            fallos.append("invento macros sin bloque de botones")

        # Y la segunda pasada es la que hace falta con el mouse quieto: el
        # enlace pierde la mitad de los pedidos, asi que lo que falla una vez
        # tiene que volver a pedirse, y avisarse. El device contesta todo
        # menos el dpi, que falla **una sola vez**: asi no se dispara el corte
        # por fallos seguidos, que es otro camino.
        avisos = []
        todos = {c: bytes([1, 0x44, 0xBB]) for c in sesion.A_LEER}
        todos[p.CMD_DPI] = DPI_REAL
        dev2 = DeviceFalso(todos, fallan={p.CMD_DPI})
        estado2 = await sesion.leer_estado(
            dev2, nodo="", al_reintentar=lambda f, e: avisos.append(list(f)))
        if p.CMD_DPI in sesion.incompletos(estado2):
            fallos.append("el comando que fallo la primera vez no se reintento")
        if not avisos or p.CMD_DPI not in avisos[0]:
            fallos.append(f"no se aviso del reintento: {avisos}")

        # **El corte por fallos seguidos.** Con el canal tomado no tiene
        # sentido pedir los siete: tras CORTE_TRAS_FALLOS seguidos se
        # abandona la tanda. Antes se los peleaba a todos y eso
        # eran minutos de terminal trabada para un resultado ya sabido.
        cortes = []
        mudo = DeviceFalso({})
        await sesion.leer_estado(mudo, nodo="",
                                 al_cortar=lambda f, m: cortes.append(list(f)))
        pedidos = [c for c, _ in mudo.pedidos]
        if len(pedidos) > 2 * sesion.CORTE_TRAS_FALLOS:
            fallos.append(f"con el canal mudo pidio {len(pedidos)} comandos; "
                          f"el corte es tras {sesion.CORTE_TRAS_FALLOS} "
                          "seguidos")
        if not cortes:
            fallos.append("corto la tanda sin avisar")

        # **Y el semaforo del rate.** Si el bloque corto dice que el mouse
        # esta arriba de 1000 Hz, la segunda pasada va a fallar igual: se
        # corta y se dice como bajarlo.
        avisos_corte = []
        rapido = DeviceFalso({p.CMD_VERSION: bytes([1, 2, 3]),
                              p.CMD_REPORT_RATE: bytes.fromhex("0154ab00000000")})
        estado3 = await sesion.leer_estado(
            rapido, nodo="",
            al_cortar=lambda f, m: avisos_corte.append(m))
        if sesion.tasa_de(estado3) != 2000:
            fallos.append(f"no leyo la tasa del bloque: "
                          f"{sesion.tasa_de(estado3)}")
        texto = "\n".join(avisos_corte)
        if "2000 Hz" not in texto or "cambiar-rate.py" not in texto:
            fallos.append(f"el aviso de tasa alta no dice que hacer: {texto!r}")
    finally:
        sesion.RESPIRO_TRAS_FALLO = respiro


# --- la confirmacion tiene que poder leerse ---------------------------------
#
# Es una de las siete barandas del modo `full`, y quedo
# demostrado que no servia de nada: el mouse manda una notificacion de
# presencia cada dos segundos, asi que el `Escribir? [escribir/no]:`
# desaparecia de la pantalla antes de que nadie llegara a contestarlo. Dos
# sesiones enteras se perdieron asi, y la escritura que se queria probar nunca
# salio. Una baranda que no se puede leer no es una baranda.

def test_la_confirmacion_no_se_tapa(fallos: list[str]) -> None:
    import io
    from linshark import cli

    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.addFilter(cli._silenciador)
    log = logging.getLogger("prueba-confirmacion")
    log.handlers = [h]
    log.setLevel(logging.INFO)
    log.propagate = False

    previo = cli._SilenciarRutina.activo
    try:
        log.info("presencia antes")
        cli._SilenciarRutina.activo = True
        cli._SilenciarRutina.ocultadas = 0
        for _ in range(5):
            log.info("presencia mientras espera la respuesta")
        # Las alarmas SI pasan: si el mouse se desconecta justo ahi, eso hay
        # que verlo aunque tape la pregunta.
        log.warning("el mouse se desconecto")
        cli._SilenciarRutina.activo = False
        log.info("presencia despues")
    finally:
        cli._SilenciarRutina.activo = previo

    salida = buf.getvalue()
    if "presencia mientras espera" in salida:
        fallos.append("el log de rutina tapa la confirmacion otra vez")
    if "el mouse se desconecto" not in salida:
        fallos.append("el silenciador se comio una advertencia")
    for esperado in ("presencia antes", "presencia despues"):
        if esperado not in salida:
            fallos.append(f"silencio de mas: falto {esperado!r}")
    if cli._SilenciarRutina.ocultadas != 5:
        fallos.append(f"conto {cli._SilenciarRutina.ocultadas} lineas "
                      "ocultadas, esperaba 5")


def test_linea_de_lectura(fallos: list[str]) -> None:
    """El formato que se lee MIENTRAS corre una escritura."""
    from linshark import sesion

    entrada = {"nombre": "botones", "datos": "00" * 57, "legible": "perfil 1"}
    casos = (
        (sesion.Lectura(p.CMD_BUTTONS, "botones", entrada),
         "  botones                 57 B  perfil 1"),
        # sin decodificar no hay legible, y la linea no queda con un "None"
        (sesion.Lectura(p.CMD_VERSION, "version de firmware",
                        {"nombre": "version de firmware", "datos": "00" * 6}),
         "  version de firmware      6 B"),
        # el macro lleva su id y usa el otro ancho
        (sesion.Lectura(p.CMD_MACRO, "macro 17",
                        {"datos": "00" * 109, "legible": "macro 17, modo 0"},
                        macro_id=17),
         "  macro 17                109 B  macro 17, modo 0"),
        # y las dos formas de no contestar no dicen lo mismo
        (sesion.Lectura(p.CMD_DPI, "dpi", None, reintentable=True),
         "  dpi                    sin respuesta (lo reintento al final)"),
        (sesion.Lectura(p.CMD_DPI, "dpi", None),
         "  dpi                    SIN RESPUESTA"),
    )
    for lectura, esperado in casos:
        obtenido = sesion.linea_de(lectura)
        if obtenido != esperado:
            fallos.append(f"linea_de: {obtenido!r} != {esperado!r}")
        if "None" in obtenido:
            fallos.append(f"la linea muestra un None: {obtenido!r}")


def test_macros_del_paso_6_son_los_del_previo(fallos: list[str]) -> None:
    from linshark import sesion

    def previo(macros):
        return {"comandos": {}, "macros": macros}

    casos = (
        # El caso 17:12: se desasigna el macro y la corrida no
        # lleva --macro-id. Sin esto el posterior no lo lee y el paso 6 lista
        # una asimetria como si fuera un cambio.
        ([], previo({"17": {"datos": "11"}}), [17], "desasignar un macro"),
        # El del mediodia, ya cubierto por --macro-id, tiene que seguir estando.
        ([17], previo({}), [17], "asignar un macro que nadie apuntaba"),
        # Sin duplicados y en int, que es lo que espera _leer_macros: las
        # claves del JSON son str y sorted() de str con int revienta.
        ([17], previo({"17": {"datos": "11"}, "3": None}), [3, 17],
         "ids repetidos y uno que no contesto"),
        # Y un respaldo sin macros no agrega nada ni revienta.
        ([], previo({}), [], "sin macros"),
        ([], {"comandos": {}}, [], "un respaldo viejo, sin la seccion"),
    )
    for extra, antes, esperado, que in casos:
        obtenido = sesion.macros_a_releer(extra, antes)
        if obtenido != esperado:
            fallos.append(f"{que}: dio {obtenido}, esperaba {esperado}")
        if any(not isinstance(x, int) for x in obtenido):
            fallos.append(f"{que}: devolvio ids que no son int: {obtenido}")


def test_etapa2_macro(fallos: list[str]) -> None:
    from linshark import estructuras as e
    leido = bytes.fromhex(MACRO_LEIDO)
    escrito = bytes.fromhex(MACRO_BLOQUE)[2:]

    # 1. idempotente: normaliza el checksum y no toca nada mas
    ida = e.escribir_macro(leido)
    if ida != escrito:
        fallos.append(
            "cmd 9 idempotente: el bloque leido no se convierte en el que "
            f"escribio el driver oficial\n      nuestro: {ida.hex()}\n"
            f"      oficial: {escrito.hex()}")
    difs = [i for i, (x, y) in enumerate(zip(ida, leido)) if x != y]
    if difs != [len(leido) - 2, len(leido) - 1]:
        fallos.append(
            f"cmd 9 idempotente: tendria que mover solo los dos bytes del "
            f"checksum; movio {difs}")

    # 2. con cambio real: los tres modos de disparo, contra el bus
    bloque = bytes.fromhex(MACRO_BLOQUE)
    for modo, oficiales in MACRO_OFICIAL.items():
        datos = e.escribir_macro(leido, modo=modo)
        nuestras = tuple(x.hex() for x in
                         p.build_write_blocks(bloque[:2] + datos))
        if nuestras != oficiales:
            fallos.append(
                f"cmd 9 modo {modo}: no da las tramas del driver oficial\n"
                f"      nuestras: {list(nuestras)}\n"
                f"      oficiales: {list(oficiales)}")

    # 3. el contador es del modo 0 y de ningun otro: pedirlo en los otros dos
    # seria pedir algo que el bloque no puede expresar, porque los cuatro
    # constructores del bundle fuerzan ese byte a 1.
    for modo in (1, 2):
        try:
            e.escribir_macro(leido, modo=modo, repeticiones=3)
        except ValueError:
            pass
        else:
            fallos.append(f"cmd 9: acepto repeticiones en el modo {modo}, que "
                          "no tiene contador")
        if e.escribir_macro(leido, modo=modo)[5] != 1:
            fallos.append(f"cmd 9 modo {modo}: el byte de repeticiones tendria "
                          "que quedar forzado en 1")
    for malo in (0, 256, -1):
        try:
            e.escribir_macro(leido, modo=0, repeticiones=malo)
        except ValueError:
            pass
        else:
            fallos.append(f"cmd 9: acepto {malo} repeticiones")
    for malo in (3, 4, 255):
        try:
            e.escribir_macro(leido, modo=malo)
        except ValueError:
            pass
        else:
            fallos.append(f"cmd 9: acepto el modo {malo}, que no se observo "
                          "nunca en el bus")

    # 4. no toca los eventos ni el id: este codificador cambia el disparo, no
    # graba un macro.
    cambiado = e.escribir_macro(leido, modo=2)
    if cambiado[0] != leido[0]:
        fallos.append("cmd 9: el codificador movio el id del macro")
    if cambiado[6:-2] != leido[6:-2]:
        fallos.append("cmd 9: el codificador toco la lista de eventos")


def test_macro_por_bloques(fallos: list[str]) -> None:
    from linshark import estructuras as e
    for modo, oficiales in MACRO_OFICIAL.items():
        bloque = bytearray.fromhex(MACRO_BLOQUE)
        bloque[3] = modo
        # el checksum interno acompana al byte del modo, como en el bus
        interno = sum(bloque[3:-2]) & 0xFFFF
        bloque[-2], bloque[-1] = interno >> 8, interno & 0xFF
        nuestras = [x.hex() for x in p.build_write_blocks(bytes(bloque))]
        if tuple(nuestras) != oficiales:
            fallos.append(
                f"macro modo {modo}: las tramas por bloques no son las del "
                f"driver oficial\n      nuestras: {nuestras}\n      "
                f"oficiales: {list(oficiales)}")
        m = e.parametros_de_macro(bytes(bloque)[2:])
        if m is None or m["modo"] != modo or not m["checksum_ok"]:
            fallos.append(f"macro modo {modo}: parametros_de_macro() no lo decodifica")
        elif m["repeticiones"] != (1 if modo == 0 else None):
            fallos.append(
                f"macro modo {modo}: el byte 7 solo es el contador cuando el "
                f"modo es 0; parametros_de_macro() devolvio {m['repeticiones']}")
    # y los cinco botones del mouse, que es lo que se grabo
    m = e.parametros_de_macro(bytes.fromhex(MACRO_BLOQUE)[2:])
    nombres = [e["nombre"] for e in m["eventos"]]
    esperado = ["clic izquierdo", "clic izquierdo", "clic de rueda",
                "clic de rueda", "atras", "atras", "adelante", "adelante",
                "clic derecho", "clic derecho"]
    if nombres != esperado:
        fallos.append(f"los usageId del macro capturado se leen {nombres}")


# --- El mouse solo guarda multiplos de 50 (o de 100 arriba de 26000), porque
# Pu() divide entero. Si alguien pide 2453, lo que queda guardado es 2450, y
# eso hay que poder decirlo antes de escribir, no descubrirlo releyendo.

def test_dpi_se_cuantiza(fallos: list[str]) -> None:
    from linshark import dpi as mod_dpi
    for pedido, esperado in ((2453, 2450), (2400, 2400), (2499, 2450),
                             (1000, 1000), (100, 100)):
        bajo, alto = mod_dpi.codificar_lineal(pedido)
        real = mod_dpi.decodificar_lineal(bajo, alto)
        if real != esperado:
            fallos.append(f"pedir {pedido} dpi deberia guardar {esperado}, "
                          f"guarda {real}")
    # y arriba de 26000 la rama es de a 100, con el flag puesto
    bajo, alto = mod_dpi.codificar_lineal(40000)
    if mod_dpi.decodificar_lineal(bajo, alto, doble=True) != 40000:
        fallos.append("40000 dpi no sobrevive el ida y vuelta por la rama /100")

    # Rareza del formato del fabricante, no nuestra: Pu(50) y Pu(0) dan los
    # mismos dos bytes, asi que 50 dpi no se distingue de "nivel apagado". El
    # minimo que se puede pedir sin ambiguedad es 100. Si algun dia una UI
    # ofrece 50, hay que rechazarlo antes de escribir.
    if mod_dpi.codificar_lineal(50) != mod_dpi.codificar_lineal(0):
        fallos.append("se esperaba que 50 dpi y 0 colisionen en Pu(); ya no "
                      "colisionan, revisar el minimo que ofrece la UI")


# --- El cmd de una escritura sale de payload[0], no de payload[1] ------------
# Las cinco escrituras que la pagina oficial mando por WebSocket estan en
# dev/models/attackshark-x8pro/docs/capturas-w/w1-from-har.jsonl. Si esto se rompe, toda allowlist de
# escritura queda comparando tamanos de bloque contra codigos de comando.

ESCRITURAS_DE_LA_PAGINA = [
    # (mensaje tal como lo mando la pagina, cmd esperado, sub esperado)
    ("830804380101113f0020172f3f6f9f8f", p.CMD_DPI, 0x38),
    ("830806090133cc00000000000000000000", p.CMD_REPORT_RATE, 0x09),
]


def test_cmd_de_escritura(fallos: list[str]) -> None:
    for hexa, cmd_esperado, sub_esperado in ESCRITURAS_DE_LA_PAGINA:
        req = p.Request(list(bytes.fromhex(hexa)))
        if req.is_read:
            fallos.append(f"{hexa[:12]}: se interpreto como lectura")
            continue
        if req.cmd != cmd_esperado:
            fallos.append(f"{hexa[:12]}: cmd={req.cmd}, esperaba "
                          f"{cmd_esperado} ({p.CMD_NAMES.get(cmd_esperado)})")
        if req.sub != sub_esperado:
            fallos.append(f"{hexa[:12]}: sub={req.sub}, esperaba {sub_esperado}")


# --- El camino de escritura en vivo -----------------------------------------
# Las pruebas de arriba miran el constructor. Estas manejan el backend ya
# armado y comprueban que ninguna trama llegue al dispositivo cuando no
# corresponde. Un backend bien construido con un handle() permisivo seria
# exactamente la clase de baranda que parece puesta y no lo esta.

class _DispositivoEspia:
    """Se hace pasar por Device y anota que le pidieron."""

    def __init__(self, respuesta=None):
        self.escrituras = []
        self.por_bloques = []
        self.lecturas = []          # (cmd, macro_id)
        self.respuesta = respuesta

    async def escribir(self, bloque, **kw):
        self.escrituras.append(bytes(bloque))
        return True

    async def escribir_por_bloques(self, bloque, **kw):
        self.por_bloques.append(bytes(bloque))
        return True

    async def leer(self, cmd, sub=None, macro_id=None, **kw):
        self.lecturas.append((cmd, macro_id))
        return self.respuesta


def _escritura_de_rate():
    """La escritura de report rate tal como la manda la pagina oficial.

    Literal de `dev/models/attackshark-x8pro/docs/capturas-w/w1-from-har.jsonl`. Viene con relleno: 15
    bytes de payload para un bloque que declara 9. Usar aca la version
    recortada seria hacerse trampa, porque el recorte es justo uno de los
    pasos que el camino de escritura tiene que hacer bien.
    """
    return p.Request(list(bytes.fromhex(
        "830806090133cc00000000000000000000")))


async def _correr_handle(backend, request):
    espia = _DispositivoEspia()
    backend.device = espia
    acks = []

    async def emit(msg):
        acks.append(msg)

    await backend.handle(request, emit)
    return espia.escrituras, acks


# --- el puente espacia lo que le llega encimado ----------------------------
#
# La pagina mando **seis escrituras de report rate en tres
# segundos** -el usuario tocando el control mientras el puente esperaba la
# confirmacion, y el navegador encolandolas- y el mouse dejo de mover el
# puntero: hubo que sacarlo del modo dongle y volver. El driver oficial no
# manda nunca dos escrituras a menos de un segundo.

# --- el puente tiene que pedir EL macro que le piden ------------------------
#
# Cmd 9 se lee con el **id del macro** en el byte 5, donde los demas comandos
# llevan el perfil (MEDIDO). El backend no le pasaba el id a
# `device.leer()`, asi que cualquier macro que pidiera la pagina volvia como
# el macro 1 -o sea vacio, porque en este mouse el que existe es el 17-.
# Lo encontro una auditoria externa leyendo el codigo; ninguna corrida lo
# habria mostrado, porque la pagina nunca llego a pedir un macro.

# --- el camino de escritura lo elige el tamaño, no el comando --------------

# --- el orquestador de la Etapa 3, sin terminal y sin mouse ----------------
#
# `sesion.aplicar()` hace la coreografia de los siete pasos. Lo que se prueba
# aca es que **aborte donde tiene que abortar**: sin respaldo completo no se
# escribe, sin confirmacion no se escribe, y con el mouse a tasa alta tampoco
# -salvo que se pida bajarla, y entonces la tasa tiene que volver-.

def _macro_de_prueba() -> bytes:
    """El macro 17 con dos eventos, **como lo devuelve el mouse**.

    O sea con el checksum interno invertido, que es la forma de lectura. Se
    arma con el codificador para que no haya un hex a mano que se desactualice.
    """
    escrito = bytes(est.armar_macro(
        17, est.eventos_desde_texto("clic-izquierdo:dir0@10, "
                                    "clic-izquierdo:dir1@10")))
    return escrito[:-2] + bytes([escrito[-1], escrito[-2]])


_MACRO_COMO_LO_LEE_EL_MOUSE = _macro_de_prueba()


class _MouseFalso:
    """Un mouse de mentira con estado: acepta escrituras y las refleja."""

    def __init__(self, *, hz=1000, completo=True, mudo_tras=None):
        self.bloques = {
            p.CMD_VERSION: bytes([1, 2, 3]),
            p.CMD_REPORT_RATE: bytes.fromhex("0144bb00000000"),
            p.CMD_LIGHTING: LUZ_REAL,
            p.CMD_DPI: DPI_REAL,
            p.CMD_BUTTONS: bytes.fromhex(BOTONES_LEIDO),
            # Un macro **de verdad**, no 108 ceros: el 17 con un par de
            # eventos, tal como lo devuelve el mouse -o sea con el checksum
            # interno invertido-. Con el bloque vacio `escribir_macro()` no era
            # idempotente: normalizaba los ceros en vez de devolver lo mismo,
            # y eso se leia como si el codificador cambiara algo.
            p.CMD_MACRO: _MACRO_COMO_LO_LEE_EL_MOUSE,
            p.CMD_PROFILE: bytes([1, 0x44, 0xBB]),
        }
        self.bloques[p.CMD_REPORT_RATE] = est_rate(hz)
        self._rehacer_perfil()
        self.completo = completo
        # Se calla a partir de la lectura N: sirve para llegar al paso 2 con
        # el respaldo ya tomado, que es el unico modo de ejercerlo.
        self.mudo_tras = mudo_tras
        self.lecturas = 0
        #: Cada cmd que se le pidio, en orden. Sirve para contar **lecturas
        #: completas** sin umbrales: `CMD_VERSION` esta en `A_LEER` y no lo
        #: pide ningun otro camino -ni el paso 2, ni la relectura acotada, ni
        #: `_refrescar`-, asi que cuantas veces aparece es cuantas veces se
        #: leyo el mouse entero. Un numero exacto, no una estimacion.
        self.pedidos: list[int] = []
        self.escrituras = []

    async def leer(self, cmd, sub=None, macro_id=None, **kw):
        self.lecturas += 1
        self.pedidos.append(cmd)
        if self.mudo_tras is not None and self.lecturas > self.mudo_tras:
            return None
        if not self.completo and cmd in (p.CMD_BUTTONS, p.CMD_MACRO,
                                         p.CMD_PROFILE):
            return None
        datos = self.bloques.get(cmd)
        if datos is None:
            return None
        # `sizeTotalData` es el largo del BLOQUE -`[cmd, sub, ...datos]`-, no
        # el de los datos: para el rate son 9 con 7 bytes de datos. Lo mismo
        # que valida `build_write_frame()`.
        return Frame(report_id=4, length=len(datos) + 5, opcode=p.WRITE_OPCODE,
                     cmd=cmd, sub=len(datos) + 2, data=datos, checksum_ok=True)

    async def escribir(self, bloque, **kw):
        self.escrituras.append(bytes(bloque))
        # **Guarda lo que un mouse real guardaria, no los bytes del bus.** En
        # cmd 8 y cmd 9 el formato de escritura no es el de lectura -los slots
        # 4, 5 y 6 permutados; el checksum interno invertido-, asi que un mouse
        # que devolviera la escritura tal cual mostraria un cambio donde no lo
        # hubo. Las dos inversas estan verificadas: `retraducir_botones` es de
        # orden 3 (aplicarla dos veces mas deshace), y el checksum del macro se
        # da vuelta solo.
        datos = bytes(bloque[2:])
        if bloque[0] == p.CMD_BUTTONS:
            datos = bytes(est.retraducir_botones(
                bytes(est.retraducir_botones(datos))))
        elif bloque[0] == p.CMD_MACRO and len(datos) >= 2:
            datos = datos[:-2] + bytes([datos[-1], datos[-2]])
        self.bloques[bloque[0]] = datos
        self._rehacer_perfil()
        return True

    async def escribir_por_bloques(self, bloque, **kw):
        return await self.escribir(bloque)

    def _rehacer_perfil(self):
        """El perfil completo, embebiendo a los bloques, como el mouse real.

        **Un mouse de mentira con un perfil de relleno hace pasar pruebas sobre
        un mouse que no existe.** El perfil real embebe a rate, dpi, luz y
        botones -por eso acompaña a todo cambio, que es en lo que se apoya la
        relectura acotada- y desde que `sesion.incoherencias()` cruza las dos
        copias, un perfil que no las lleve es justamente lo que esa baranda
        tiene que rechazar.

        Se rehace **despues de cada escritura**, que es lo que hace el mouse:
        un perfil que se quedara con los bytes viejos seria otro mouse que no
        existe.
        """
        from linshark import dispositivos
        embebe = dispositivos.activo().perfil_embebe
        if not embebe:
            return
        largo = max(po + L for po, _, L in embebe.values())
        cuerpo = bytearray(self.bloques.get(p.CMD_PROFILE, b"")[:largo])
        cuerpo.extend(bytes(largo - len(cuerpo)))
        for cmd, (po, bo, L) in embebe.items():
            datos = self.bloques.get(cmd)
            if datos is not None and len(datos) >= bo + L:
                cuerpo[po:po + L] = datos[bo:bo + L]
        self.bloques[p.CMD_PROFILE] = bytes(cuerpo)


class _MouseRapido(_MouseFalso):
    """Un mouse falso que **respeta lo medido sobre las tasas altas**.

    `_MouseFalso(hz=8000)` contesta todo, y eso es justamente lo que no pasa:
    esta MEDIDO(a 2000 y a 8000 Hz) que arriba de 1000 Hz las
    lecturas cortas -version, rate, luz- llegan y **las largas no** -dpi,
    botones, macro y perfil-. Un mouse de mentira que contesta el perfil a
    8000 Hz hace pasar pruebas sobre un mouse que no existe, y las dos veces
    que este proyecto se llevo un susto fue por algo asi.

    `perdida_de_rate` simula lo otro que esta MEDIDO: que el dongle acuse
    `0xC1` y el mouse no aplique la tasa(dos veces seguidas a
    2000 Hz). Es lo que hace falta para ejercer los reintentos de
    `sesion.poner_tasa()`.
    """

    LARGOS = (p.CMD_DPI, p.CMD_BUTTONS, p.CMD_MACRO, p.CMD_PROFILE)

    def __init__(self, *, hz=8000, perdida_de_rate=0):
        super().__init__(hz=hz)
        self.perdida_de_rate = perdida_de_rate
        self.escrituras_de_rate = 0

    @property
    def hz(self):
        from linshark import estructuras as e
        return e.report_rate_de(self.bloques[p.CMD_REPORT_RATE])

    async def leer(self, cmd, sub=None, macro_id=None, **kw):
        # El contador lo lleva el padre: incrementarlo aca tambien haria que
        # `mudo_tras` -que cuenta lecturas- se disparara antes de tiempo.
        if cmd in self.LARGOS and (self.hz or 0) > 1000:
            self.lecturas += 1
            self.pedidos.append(cmd)
            return None
        return await super().leer(cmd, sub, macro_id, **kw)

    async def escribir(self, bloque, **kw):
        if bloque[0] == p.CMD_REPORT_RATE:
            self.escrituras_de_rate += 1
            if self.escrituras_de_rate <= self.perdida_de_rate:
                # el dongle acusa y el mouse no aplica: lo MEDIDO
                self.escrituras.append(bytes(bloque))
                return True
        return await super().escribir(bloque, **kw)


def est_rate(hz):
    from linshark import estructuras as e
    return e.escribir_report_rate(bytes.fromhex("0144bb00000000"), hz=hz)


# --- la herramienta con la que se toca el hardware, de punta a punta -------
# `primera-escritura.py` es el unico programa de este repo que le escribe al
# mouse de verdad, y antes no tenia forma de probarse sin uno
# enfrente: abria el nodo adentro de `main()`. Ahora `main()` acepta un device
# y un nodo, asi que la Etapa 3 entera -paso 0 incluido- corre contra
# `_MouseFalso`.
#
# Esto no reemplaza apretar el boton. Lo que cubre es lo otro: que la
# coreografia no se rompa al tocarla, que es exactamente lo que hacia caro
# migrarla.
async def test_la_herramienta_de_punta_a_punta(fallos: list[str]) -> None:
    import io
    import tempfile
    from contextlib import redirect_stderr, redirect_stdout

    pe = _cargar_primera_escritura()

    # Una corrida que revienta tiene que salir como **un fallo de este test**,
    # no como un traceback que tumba la tanda entera: si `main()` levanta una
    # excepcion, el resto de las salvaguardas no llegan a correr y la salida
    # no dice cual fue. Se descubrio probando las mutaciones:
    # dos de las cuatro se detectaban, pero reventando.
    async def correr(argv, *, hz=1000, **kw):
        mouse = _MouseFalso(hz=hz, **kw)
        with tempfile.TemporaryDirectory() as tmp:
            pe.CARPETA_RESPALDOS = Path(tmp)
            # **stderr tambien.** El CLI manda por ahi todos sus motivos de
            # aborto, asi que capturando solo stdout ninguna prueba podia
            # mirar lo que dice cuando se niega a algo: lo unico verificable
            # era el codigo de salida. Se noto al probar la
            # guarda de la tasa.
            salida = io.StringIO()
            try:
                with redirect_stdout(salida), redirect_stderr(salida):
                    codigo = await pe.main(argv, device=mouse,
                                           nodo="/dev/falso")
            except BaseException as exc:            # noqa: BLE001
                fallos.append(f"main({argv}) revento: "
                              f"{type(exc).__name__}: {exc}")
                codigo = -1
            guardados = sorted(f.name for f in Path(tmp).iterdir())
        return codigo, mouse, salida.getvalue(), guardados

    # 1. una escritura que cambia algo: sale bien, escribe una vez y deja los
    #    dos respaldos.
    codigo, mouse, texto, guardados = await correr(
        ["--comando", "rate", "--valor", "500"])
    if codigo != 0:
        fallos.append(f"la corrida de rate dio {codigo}, no 0:\n{texto}")
    if len(mouse.escrituras) != 1:
        fallos.append(f"escribio {len(mouse.escrituras)} veces, no 1")
    if len(guardados) != 2:
        fallos.append(f"dejo {len(guardados)} respaldos, no 2: {guardados}")
    if "[3/6]" not in texto or "[5/6]" not in texto or "[6/6]" not in texto:
        fallos.append(f"la corrida no conto sus pasos:\n{texto}")

    # 2. **Sin prompt.** El consentimiento es el comando; si alguien vuelve a
    #    poner un `input()`, esto cuelga o revienta en vez de pasar.
    if "[escribir/no]" in texto or "[bajar/no]" in texto:
        fallos.append("volvio a aparecer un prompt de confirmacion")

    # 2b. **La tasa, arriba de 1000 Hz, no se escribe por este camino.**
    #     El paso 0 la baja para poder respaldar y el `finally` la devuelve:
    #     si lo que se escribe ES la tasa, la corrida restaura justo lo que se
    #     pidio y el veredicto sale `sin-diferencias`, o sea "salio bien". Se
    #     cerro mandando a `cambiar-rate.py`, que toca un solo comando. Por debajo de 1000 Hz no hay nada que restaurar y el camino
    #     de siempre sirve: eso es el caso 1, que sigue arriba.
    codigo, mouse, texto, _ = await correr(
        ["--comando", "rate", "--valor", "1000"], hz=8000)
    if codigo == 0:
        fallos.append("escribio la tasa por la Etapa 3 con el mouse a 8000 Hz: "
                      "esa corrida se deshace sola y dice que salio bien")
    if mouse.escrituras:
        fallos.append("toco el mouse antes de negarse")
    if "cambiar-rate.py" not in texto:
        fallos.append(f"no dijo por donde se cambia de verdad:\n{texto}")

    # 3. A tasa alta baja sola, escribe, y **devuelve la tasa**. Es el paso 0
    #    entero, que antes solo se probaba por dentro de `sesion.aplicar()`.
    codigo, mouse, texto, _ = await correr(
        ["--comando", "dpi", "--nivel", "1", "--valor", "1600"], hz=8000)
    if codigo != 0:
        fallos.append(f"a 8000 Hz la corrida dio {codigo}:\n{texto}")
    if est_rate(8000) != mouse.bloques[p.CMD_REPORT_RATE]:
        fallos.append("no devolvio la tasa a 8000 Hz al terminar")
    if len(mouse.escrituras) != 3:
        fallos.append(f"a 8000 Hz escribio {len(mouse.escrituras)} veces, "
                      "esperaba 3 (bajar, el dpi, restaurar)")
    if "[0/6]" not in texto:
        fallos.append("bajo la tasa sin decirlo: el registro es lo unico que "
                      "queda ahora que no se pregunta")

    # 4. Un respaldo incompleto no se escribe **nunca**: es la baranda del
    #    paso 1, y la que mas caro sale perder.
    codigo, mouse, texto, guardados = await correr(
        ["--comando", "rate", "--valor", "500"], completo=False)
    if codigo == 0:
        fallos.append("siguio adelante con el respaldo incompleto")
    if mouse.escrituras:
        fallos.append("ESCRIBIO con el respaldo incompleto")

    # 5. Un valor que no existe se rechaza antes de tocar el mouse: ni una
    #    lectura, para no hacer esperar medio minuto de respaldo y despues
    #    decir que el numero no va.
    codigo, mouse, texto, _ = await correr(["--comando", "rate", "--valor", "3"])
    if codigo != 2:
        fallos.append(f"3 Hz no se rechazo con codigo 2, dio {codigo}")
    if mouse.lecturas or mouse.escrituras:
        fallos.append("toco el mouse para rechazar un valor que no existe")


# --- G-01: el despachador da los mismos bytes que el CLI -------------------
# `sesion.preparar_mutacion()` existe para que la interfaz no reimplemente el
# mapeo `(clave, valor) -> que comando y que codificador`, que antes vivia
# solo adentro de `primera-escritura.py`. Lo pidio la
# auditoria del agente A (G-01).
#
# **Este test es lo que evita que se conviertan en dos copias que divergen.**
# Corre los dos caminos contra el mismo mouse falso y compara el bloque que
# sale: si alguien toca uno y no el otro, se pone rojo. Es la misma idea que la
# caracterizacion de quince corridas que verifico la migracion del CLI, pero
# permanente.
async def test_el_despachador_y_el_cli_dan_lo_mismo(fallos: list[str]) -> None:
    import io
    import tempfile
    from contextlib import redirect_stdout

    from linshark import sesion

    pe = _cargar_primera_escritura()

    casos = [
        ("tasa", 500, ["--comando", "rate", "--valor", "500"]),
        ("lod", 2, ["--comando", "dpi", "--lod", "2"]),
        ("ripple", False, ["--comando", "dpi", "--ripple", "0"]),
        ("angle_snapping", False, ["--comando", "dpi", "--angle-snapping", "0"]),
        ("motion_sync", False, ["--comando", "dpi", "--motion-sync", "0"]),
        ("nivel_activo", 2, ["--comando", "dpi", "--nivel-activo", "2"]),
        ("dpi_nivel_1", 1600,
         ["--comando", "dpi", "--nivel", "1", "--valor", "1600"]),
        ("hibernacion", 1, ["--comando", "luz", "--hibernacion", "1"]),
        ("reposo", 1, ["--comando", "luz", "--reposo", "1"]),
        # **20 contra `--respuesta 10`, y no es un descuido.** El despachador
        # toma el numero que se ve -la unidad de `modelo.campos_de()`- y el CLI
        # toma el byte, que viaja a la mitad (`KeyResponseTime/2`) y esta
        # documentado asi en `modelo.NOTA_RESPUESTA`. Los dos tienen que
        # producir el MISMO bloque; que los argumentos difieran en un factor 2
        # es la conversion, puesta a la vista.
        ("respuesta", 20, ["--comando", "luz", "--respuesta", "10"]),
        ("color", "#ff0000", ["--comando", "luz", "--color", "ff0000"]),
        ("rueda", "invertida", ["--comando", "botones", "--rueda", "invertida"]),
        ("rueda", "derecho", ["--comando", "botones", "--rueda", "derecha"]),
        ("boton_costado_adelante", "adelante",
         ["--comando", "botones", "--boton", "costado-adelante",
          "--funcion", "adelante"]),
        ("boton_costado_adelante", ("macro", 17),
         ["--comando", "botones", "--boton", "costado-adelante",
          "--funcion", "macro", "--macro-id", "17"]),
        ("boton_costado_adelante", ("atajo de teclado", "ctrl+c"),
         ["--comando", "botones", "--boton", "costado-adelante",
          "--funcion", "atajo de teclado", "--atajo", "ctrl+c"]),
        # **Los tres de cmd 9**, que son los unicos que necesitan el id: el
        # macro no se lee con el perfil. Entraron al despachador,
        # cuando el panel de macros de la ventana los pidio; antes vivian solo
        # adentro del CLI, que es exactamente la copia que este test evita.
        ("macro_modo", 2,
         ["--comando", "macro", "--macro-id", "17", "--modo", "2"], 17),
        ("macro_repeticiones", 5,
         ["--comando", "macro", "--macro-id", "17", "--modo", "0",
          "--repeticiones", "5"], 17),
        ("macro_eventos", "a:abajo@10, a:arriba@10",
         ["--comando", "macro", "--macro-id", "17",
          "--eventos", "a:abajo@10, a:arriba@10"], 17),
    ]

    for clave, valor, argv, *resto in casos:
        macro_id = resto[0] if resto else None
        mouse = _MouseFalso()
        with tempfile.TemporaryDirectory() as tmp:
            pe.CARPETA_RESPALDOS = Path(tmp)
            try:
                with redirect_stdout(io.StringIO()):
                    await pe.main(argv, device=mouse, nodo="/dev/falso")
            except BaseException as exc:            # noqa: BLE001
                fallos.append(f"el CLI revento con {argv}: "
                              f"{type(exc).__name__}: {exc}")
                continue
        if not mouse.escrituras:
            fallos.append(f"el CLI no escribio nada con {argv}")
            continue
        del_cli = bytes(mouse.escrituras[0])[2:]

        try:
            m = sesion.preparar_mutacion(clave, valor, macro_id=macro_id)
            del_despachador = bytes(m.codificar(
                _MouseFalso().bloques[m.cmd]))
        except Exception as exc:                    # noqa: BLE001
            fallos.append(f"preparar_mutacion({clave!r}, {valor!r}) revento: "
                          f"{type(exc).__name__}: {exc}")
            continue

        if del_cli != del_despachador:
            fallos.append(
                f"{clave}={valor!r}: el despachador y el CLI no dan lo mismo\n"
                f"           cli  {del_cli.hex()}\n"
                f"           disp {del_despachador.hex()}")

    # Y los campos que NO se escriben tienen que decir por que, no reventar con
    # un KeyError: la interfaz los muestra igual, en gris.
    for clave in ("color_nivel_3",):
        try:
            sesion.preparar_mutacion(clave, "lo que sea")
        except sesion.CampoNoEscribible as exc:
            if len(str(exc)) < 40:
                fallos.append(f"{clave}: el motivo no explica nada")
        except Exception as exc:                    # noqa: BLE001
            fallos.append(f"{clave} tiro {type(exc).__name__}, no "
                          "CampoNoEscribible")
        else:
            fallos.append(f"{clave} paso como escribible")

    # una clave inventada tampoco puede pasar en silencio
    try:
        sesion.preparar_mutacion("no_existe", 1)
    except ValueError:
        pass
    except Exception as exc:                        # noqa: BLE001
        fallos.append(f"una clave inventada tiro {type(exc).__name__}")
    else:
        fallos.append("una clave inventada no protesto")


# --- G-02: los macros, modelados para la interfaz --------------------------
# `campos_de()` da parametros escalares y un macro no lo es: tiene disparo,
# pasos y un nombre que el mouse no guarda. Lo pidio la auditoria (G-02).
# --- leer y volver a escribir no puede mover nada --------------------------
# **El argumento entero del proyecto, vuelto test.** La pagina oficial "no puede
# releer su propio estado sin corromperlo": lee tres bloques y los reescribe
# cambiados. Si `modelo.campos_de()` publica un campo en una unidad y
# `preparar_mutacion()` lo toma en otra, la aplicacion hace exactamente lo
# mismo, y lo hace en silencio.
#
# Paso: hasta `respuesta` se **mostraba** como el numero del
# slider (4..50) y se **escribia** como el byte (2..25, la mitad). Escribir el
# 8 que la pantalla acababa de mostrar dejaba el mouse en 16, y la mitad de
# arriba del rango publicado ni siquiera se podia escribir. No lo veia nadie:
# el test de paridad compara el despachador contra el CLI, y el CLI tiene la
# misma convencion, asi que los dos coincidian en estar mal respecto del modelo.
#
# Esto lo mira desde el otro lado, que es el unico que importa: **el valor que
# se ve**. Para cada campo escribible, escribir lo que `campos_de()` muestra
# tiene que dar el bloque idempotente, byte a byte.
async def test_leer_y_reescribir_no_mueve_nada(fallos: list[str]) -> None:
    from linshark import modelo, sesion

    mouse = _MouseFalso()
    estado = await sesion.leer_estado(mouse, nodo="/dev/falso",
                                      macros_extra=(17,))
    campos = [c for c in modelo.campos_de(estado) if c.escribible]
    if len(campos) < 20:
        fallos.append(f"solo {len(campos)} campos escribibles: el mouse falso "
                      "no esta dando el estado entero")
    for campo in campos:
        bloque = mouse.bloques[campo.cmd]
        try:
            mutacion = sesion.preparar_mutacion(campo.clave, campo.valor)
            salida = bytes(mutacion.codificar(bloque))
        except Exception as exc:                    # noqa: BLE001
            fallos.append(
                f"{campo.clave}: escribir el valor que el modelo MUESTRA "
                f"({campo.valor!r}) revento con "
                f"{type(exc).__name__}: {exc}")
            continue
        if salida != sesion.referencia_idempotente(campo.cmd, bloque):
            fallos.append(
                f"{campo.clave}: escribir el valor que el modelo muestra "
                f"({campo.valor!r}) MUEVE el campo. Es el reproche que este "
                "proyecto le hace a la pagina oficial")

    # Y los dos extremos del rango publicado tienen que ser escribibles: un
    # rango que la pantalla ofrece y el codificador rechaza es una promesa
    # falsa.
    for campo in campos:
        if campo.minimo is None:
            continue
        for punto, cual in ((campo.minimo, "minimo"), (campo.maximo, "maximo")):
            try:
                sesion.preparar_mutacion(campo.clave, punto)
            except Exception as exc:                # noqa: BLE001
                fallos.append(
                    f"{campo.clave}: el {cual} que el modelo publica "
                    f"({punto}) no se puede escribir: {exc}")


# --- G-03 y G-05: lo que el mouse avisa solo, y el nodo sin permiso --------
def test_novedades_y_permiso(fallos: list[str]) -> None:
    from linshark import sesion
    from linshark.hidraw import COMANDO_UDEV, FaltaLaReglaDeUdev

    # G-03. Los dos formatos estan confirmados escuchando el hardware, y son
    # los que figuran en protocol.NOTIF_*.
    n = sesion.novedad_de(bytes.fromhex("08400164"))
    if n is None or n.tipo != "bateria" or n.bateria != 100:
        fallos.append(f"no decodifico la presencia con bateria: {n}")
    elif n.estado_bateria != 1:
        fallos.append(f"el byte de estado salio {n.estado_bateria}, no 1")

    n = sesion.novedad_de(bytes.fromhex("08100300"))
    if n is None or n.tipo != "nivel-dpi" or n.nivel_dpi != 3:
        fallos.append(f"no decodifico el cambio de nivel de dpi: {n}")

    # una notificacion que no conocemos se devuelve igual, marcada: tirarla
    # seria perder la unica pista de que existe
    n = sesion.novedad_de(bytes.fromhex("08ff0000"))
    if n is None or n.tipo != "desconocida" or not n.crudo:
        fallos.append("una notificacion desconocida se perdio")

    # y un reporte cortado no revienta
    if sesion.novedad_de(b"\x08\x40") is not None:
        fallos.append("un reporte cortado paso como novedad")

    # **El byte de estado de bateria ya se interpreta, y solo hasta donde se
    # midio.** Antes esta baranda exigia lo contrario -que no hubiera un
    # `cargando`, porque habria sido inventado-; se puso y
    # se saco el cargador dos veces en una corrida y las cuatro transiciones
    # salieron, con el LED morado de testigo. Lo que la baranda cuida ahora es
    # el limite: 3 y 1 estan medidos, el resto **no**, y un valor sin medir
    # tiene que dar None, no False.
    n = sesion.novedad_de(bytes.fromhex("08400364"))
    if n is None or n.cargando is not True or n.estado_bateria != 3:
        fallos.append(f"el estado 3 (cargando, MEDIDO) no se leyo: {n}")

    n = sesion.novedad_de(bytes.fromhex("08400164"))
    if n is None or n.cargando is not False:
        fallos.append(f"el estado 1 (a bateria, MEDIDO) no se leyo: {n}")

    for crudo in ("08400064", "08400264", "08400764"):
        n = sesion.novedad_de(bytes.fromhex(crudo))
        if n is None or n.cargando is not None:
            fallos.append(f"el estado {crudo[4:6]} no esta medido y "
                          f"`cargando` no dio None: {n}")

    # y el byte crudo sigue estando, que es de donde sale cualquier valor que
    # aparezca despues
    if "estado_bateria" not in sesion.Novedad.__dataclass_fields__:
        fallos.append("Novedad perdio el byte de estado crudo")

    # el listener engancha sobre el hook que ya existia
    class _Dev:
        on_estado_mouse = None

    visto = []
    dev = _Dev()
    sesion.escuchar_novedades(dev, visto.append)
    if dev.on_estado_mouse is None:
        fallos.append("escuchar_novedades no engancho nada")
    else:
        dev.on_estado_mouse(bytes.fromhex("08400150"))
        dev.on_estado_mouse(b"\x08")          # corto: no tiene que llegar
        if [v.bateria for v in visto] != [80]:
            fallos.append(f"el listener paso {visto}")

    # G-05. Sigue siendo un PermissionError -nada de lo que ya lo captura deja
    # de andar- y ademas trae el arreglo como dato, no como texto.
    exc = FaltaLaReglaDeUdev("sin permiso", path="/dev/hidraw2")
    if not isinstance(exc, PermissionError) or not isinstance(exc, OSError):
        fallos.append("FaltaLaReglaDeUdev dejo de ser un PermissionError: eso "
                      "rompe a todo lo que ya lo capturaba")
    if exc.comando != COMANDO_UDEV or "instalar-udev" not in exc.comando:
        fallos.append(f"no trae el comando de arreglo: {exc.comando!r}")
    if str(exc.path) != "/dev/hidraw2":
        fallos.append("no trae el nodo que fallo")


# --- donde esta el mouse: el bus, no el mouse ------------------------------
#
# `conexiones.buscar()` no abre ningun nodo y no le manda nada al mouse: mira
# `/sys/class/hidraw`. Eso deja probarlo **entero sin hardware**, armando un
# sysfs de mentira en un directorio temporal -con la misma forma que el de
# verdad: el nodo es un symlink a un directorio que cuelga de la interfaz USB,
# y la interfaz cuelga del dispositivo-. Asi se prueban los tres casos que no
# se pueden pedir a mano cuando el mouse esta lejos: el dongle desenchufado, el
# nodo sin permisos, y el mouse conectado **solo por cable**.
def _sysfs_falso(tmp: Path, dispositivos_usb) -> tuple[Path, Path]:
    """Arma un `/sys/class/hidraw` y un `/dev` de mentira.

    `dispositivos_usb` es una lista de `(puerto, vendor, producto, atributos,
    [(interfaz, nombre_de_nodo, permisos)])`.
    """
    clase = tmp / "class" / "hidraw"
    clase.mkdir(parents=True, exist_ok=True)
    dev = tmp / "dev"
    dev.mkdir(exist_ok=True)
    for puerto, vendor, producto, extra, interfaces in dispositivos_usb:
        usb = tmp / "devices" / puerto
        usb.mkdir(parents=True, exist_ok=True)
        (usb / "idVendor").write_text(f"{vendor:04x}\n")
        (usb / "idProduct").write_text(f"{producto:04x}\n")
        for clave, valor in extra.items():
            (usb / clave).write_text(f"{valor}\n")
        for interfaz, nombre, permisos in interfaces:
            iface = usb / f"{puerto}:1.{interfaz}"
            iface.mkdir(parents=True, exist_ok=True)
            (iface / "bInterfaceNumber").write_text(f"{interfaz:02d}\n")
            hid = iface / f"0003:{vendor:04X}:{producto:04X}.0001"
            (hid / "hidraw" / nombre).mkdir(parents=True, exist_ok=True)
            # `hidrawN/device` es un symlink al dispositivo HID, y por eso
            # `device/..` es la interfaz y `device/../..` el dispositivo USB.
            # Si esto no se arma igual que sysfs, el test no prueba nada.
            enlace = hid / "hidraw" / nombre / "device"
            if not enlace.exists():
                enlace.symlink_to(hid, target_is_directory=True)
            nodo_clase = clase / nombre
            if not nodo_clase.exists():
                nodo_clase.symlink_to(hid / "hidraw" / nombre,
                                      target_is_directory=True)
            nodo = dev / nombre
            nodo.write_bytes(b"")
            nodo.chmod(permisos)
    return clase, dev


#: Lo que el X8 Pro pone en el bus, como lo puso con el dongle y
#: el cable enchufados a la vez. Los numeros salen de ese sysfs de verdad.
_DONGLE = ("1-2", 0x1D57, 0xFA65,
           {"manufacturer": "LXDDZ", "product": "2.4G 8K HS Receiver",
            "busnum": 1, "devnum": 8, "speed": 480},
           [(0, "hidraw0", 0o600), (1, "hidraw1", 0o600),
            (2, "hidraw2", 0o666), (3, "hidraw3", 0o600)])
_CABLE = ("1-4", 0x1D57, 0x2126,
          {"manufacturer": "Beken", "product": "X8PRO Mouse",
           "busnum": 1, "devnum": 7, "speed": 12},
          [(0, "hidraw5", 0o600), (1, "hidraw6", 0o600),
           (2, "hidraw7", 0o666), (3, "hidraw8", 0o600)])


def test_donde_esta_el_mouse(fallos: list[str]) -> None:
    """El bus se lee entero, y cada caso se dice distinto.

    Antes, no encontrar el nodo daba siempre el mismo error -"no
    encontre la interfaz 2 de 1d57:fa65. Esta puesto el dongle?"-, que es falso
    cuando el dongle esta puesto y lo que pasa es otra cosa: el mouse enchufado
    por cable (otro dispositivo USB, que ademas se lleva el canal de radio) o
    el nodo sin permisos. Decir "no esta" cuando esta manda a buscar al lugar
    equivocado.
    """
    import os
    import tempfile
    from linshark import conexiones as con
    from linshark import hidraw as h

    es_root = os.geteuid() == 0

    with tempfile.TemporaryDirectory() as crudo:
        tmp = Path(crudo)

        # 1. los dos a la vez, que es como estaba
        clase, dev = _sysfs_falso(tmp / "a", [_DONGLE, _CABLE])
        vistas = con.buscar(clase, dev)
        if len(vistas) != 2:
            fallos.append(f"con el dongle y el cable vi {len(vistas)} "
                          "dispositivos, esperaba 2")
        else:
            # **El cable primero**: con el cable puesto el mouse no habla por
            # el dongle (MEDIDO), asi que el que contesta es el cable.
            cable, dongle = vistas
            if dongle.via != con.VIA_DONGLE or cable.via != con.VIA_CABLE:
                fallos.append(f"no distinguio los caminos: {dongle.via}, "
                              f"{cable.via}")
            if dongle.puerto != "1-2" or cable.puerto != "1-4":
                fallos.append(f"los puertos salieron {dongle.puerto} y "
                              f"{cable.puerto}")
            if len(dongle.nodos) != 4:
                fallos.append(f"el dongle son cuatro interfaces y agrupo "
                              f"{len(dongle.nodos)}")
            if dongle.modelo != "X8 Pro" or cable.modelo != "X8 Pro":
                fallos.append("no reconocio el modelo por el id del producto")
            # **Por cable el canal es la misma interfaz 2**, con otro
            # protocolo adentro: la conexion lo ofrece, y quien lo abre mira
            # `via` (ver el punto 5).
            if (cable.nodo_de_configuracion is None
                    or cable.nodo_de_configuracion.path != dev / "hidraw7"):
                fallos.append("por cable no ofrecio la interfaz 2 como canal")
            if not es_root and not (cable.se_puede_configurar
                                    and dongle.se_puede_configurar):
                fallos.append("con los nodos abiertos dijo que no se puede "
                              "configurar por alguno de los dos caminos")
            elegida = con.elegir(vistas)
            if elegida.via != con.VIA_CABLE:
                fallos.append(f"con los dos puestos eligio {elegida.via}, y "
                              "con el cable puesto el dongle no contesta")

        # 2. **solo el cable**: se configura por ahi
        clase, dev = _sysfs_falso(tmp / "b", [_CABLE])
        try:
            elegida = con.elegir(con.buscar(clase, dev))
        except con.NoHayCanal as exc:
            fallos.append(f"con el mouse solo por cable no hay canal: {exc}")
        else:
            if elegida.via != con.VIA_CABLE or \
                    elegida.nodo_de_configuracion.path != dev / "hidraw7":
                fallos.append("con el mouse solo por cable no eligio su "
                              "interfaz 2")

        # 3. **el dongle sin permisos**: existe, y lo que falta es la regla
        if not es_root:
            sin_regla = (_DONGLE[0], _DONGLE[1], _DONGLE[2], _DONGLE[3],
                         [(n, nombre, 0o000)
                          for n, nombre, _ in _DONGLE[4]])
            clase, dev = _sysfs_falso(tmp / "c", [sin_regla])
            vistas = con.buscar(clase, dev)
            if not vistas or not vistas[0].falta_la_regla_de_udev:
                fallos.append("con el nodo sin permisos no dijo que faltaba "
                              "la regla de udev")
            try:
                con.elegir(vistas)
            except con.NoHayCanal as exc:
                if not exc.por_permisos:
                    fallos.append("el error por permisos no se distingue de "
                                  "los otros, y tiene un arreglo de una linea")
            else:
                fallos.append("con el nodo cerrado dijo que se puede "
                              "configurar")

        # 4. **nada de esta familia**: tambien es una respuesta distinta
        clase, dev = _sysfs_falso(tmp / "d", [
            ("1-9", 0x046D, 0xC52B, {"manufacturer": "Logitech",
                                     "product": "Unifying Receiver",
                                     "busnum": 1, "devnum": 3, "speed": 12},
             [(2, "hidraw9", 0o666)])])
        if con.buscar(clase, dev):
            fallos.append("miro un dispositivo de otro fabricante")
        try:
            con.elegir(con.buscar(clase, dev))
        except con.NoHayCanal as exc:
            if "dongle" not in str(exc):
                fallos.append("sin nada en el bus el error no dice que falta "
                              "el dongle")
        else:
            fallos.append("sin nada en el bus dijo que hay canal")

        # 5. Y `find_config_hidraw()` -que es por donde entran el CLI y el
        #    puente, que hablan el framing del dongle- **no devuelve nunca el
        #    nodo del cable**: seria mandarle Output Reports del dongle a un
        #    endpoint que espera Feature Reports. Tiene que decir por que.
        clase, dev = _sysfs_falso(tmp / "e", [_DONGLE, _CABLE])
        antes = (con.SYS_HIDRAW, con.DEV)
        con.SYS_HIDRAW, con.DEV = clase, dev
        try:
            h.find_config_hidraw()
        except h.DeviceNotFound as exc:
            if "cable" not in str(exc):
                fallos.append(f"find_config_hidraw() sigue sin decir que el "
                              f"mouse esta por cable: {str(exc)[:90]}")
        except Exception as exc:                   # noqa: BLE001
            fallos.append(f"find_config_hidraw() tiro {type(exc).__name__}")
        else:
            fallos.append("find_config_hidraw() devolvio un nodo con el mouse "
                          "por cable, y el camino del dongle no le sirve")
        finally:
            con.SYS_HIDRAW, con.DEV = antes

        # 6. **Y por cable no se ofrecen tasas que el cable no puede dar.** El
        #    dispositivo del cable es Full Speed con `bInterval` de 1 ms, asi
        #    que no pasa de 1000 Hz: lo dice su descriptor, no nosotros. Un
        #    desplegable con 8000 por ese camino es un control que no hace lo
        #    que dice, que es el reproche de este proyecto al cliente oficial.
        from linshark import dispositivos as d
        from linshark import modelo
        from linshark import sesion
        from linshark.perfiles.x8pro import X8_PRO
        clase, dev = _sysfs_falso(tmp / "f", [_DONGLE, _CABLE])
        cable, dongle = con.buscar(clase, dev)
        if max(cable.tasas) != X8_PRO.tasa_maxima_por_cable:
            fallos.append(f"por cable ofrece hasta {max(cable.tasas)} Hz y el "
                          f"descriptor no da mas de "
                          f"{X8_PRO.tasa_maxima_por_cable}")
        if max(dongle.tasas) != max(X8_PRO.tasas):
            fallos.append("por el dongle dejo de ofrecer la tasa mas alta")
        estado = {"comandos": {str(p.CMD_REPORT_RATE):
                               {"datos": "0144bb00000000"}}}
        por_cable = modelo.por_clave(estado, None, d.VIA_CABLE)["tasa"]
        por_dongle = modelo.por_clave(estado, None, d.VIA_DONGLE)["tasa"]
        if max(por_cable.opciones) > X8_PRO.tasa_maxima_por_cable:
            fallos.append(f"el campo de tasa por cable ofrece "
                          f"{sorted(por_cable.opciones)}")
        if max(por_dongle.opciones) != max(X8_PRO.tasas):
            fallos.append("el campo de tasa por el dongle perdio las altas")
        # **Y el valor es el del camino**: `0x74` es 8000 por radio y 1000 por
        # cable (MEDIDO, `cable-soft-abrir`). Mostrar 8000 por cable seria
        # mostrar la tasa de un camino que no se esta usando.
        estado = {"comandos": {str(p.CMD_REPORT_RATE):
                               {"datos": "01748b00000000"}}}
        if (modelo.por_clave(estado, None, d.VIA_CABLE)["tasa"].valor != 1000
                or modelo.por_clave(estado, None,
                                    d.VIA_DONGLE)["tasa"].valor != 8000):
            fallos.append("el campo de tasa no lee el nibble de su camino")
        # **Y sin que nadie pase la via, la dice el estado.** Un estado leido
        # por cable trae `"via": "cable"`; sin esto, "Volver a como estaba"
        # anotaba 8000 -la tasa de la radio- y por cable intentaba escribirla.
        estado["via"] = d.VIA_CABLE
        if modelo.por_clave(estado)["tasa"].valor != 1000 or \
                sesion.tasa_de(estado) != 1000:
            fallos.append("un estado leido por cable no hace valer su camino "
                          "cuando no se lo pasan")


# --- el driver no depende del lado de investigacion ------------------------
# El repositorio esta partido en dos: `driver/` es el programa que
# se instala y `dev/` es como se supo lo que el programa sabe -capturas,
# respaldos, herramientas de medicion, el bundle del fabricante-. La frontera
# tiene una sola regla y es en un solo sentido: **el driver no puede necesitar
# nada de `dev/` para funcionar**, porque lo que se instala en la maquina de
# alguien es `driver/` y nada mas. Al reves si: las herramientas de `dev/`
# importan la biblioteca del driver, que es lo que se esta midiendo.
#
# Citarlo en un comentario esta bien -y es lo que hace todo este proyecto: cada
# byte con su fuente-. Lo que no puede pasar es **abrir un archivo de `dev/` en
# tiempo de ejecucion**, que es lo que esto busca: literales de ruta en codigo,
# no en prosa.
def test_el_driver_no_necesita_a_dev(fallos: list[str]) -> None:
    import ast

    driver = Path(__file__).resolve().parent.parent
    yo = Path(__file__).resolve()
    sospechosos = []
    for archivo in sorted(driver.rglob("*.py")):
        # Este archivo se saltea a si mismo: los literales que busca los tiene
        # escritos adentro, y encontrarse a si mismo no prueba nada.
        if "__pycache__" in str(archivo) or archivo.resolve() == yo:
            continue
        try:
            arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        except SyntaxError as exc:                 # pragma: no cover
            fallos.append(f"{archivo.name} no compila: {exc}")
            continue
        # Los docstrings son prosa: ahi citar `dev/docs/...` es correcto.
        docstrings = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                doc = ast.get_docstring(nodo, clean=False)
                if doc is not None:
                    docstrings.add(doc)
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Constant):
                continue
            if not isinstance(nodo.value, str) or nodo.value in docstrings:
                continue
            texto = nodo.value.strip()
            if texto.startswith("dev/") or "/dev/docs" in texto \
                    or "/dev/models" in texto or "/dev/herramientas" in texto:
                sospechosos.append(
                    f"{archivo.relative_to(driver)}:{nodo.lineno} -> {texto[:60]!r}")
    if sospechosos:
        fallos.append("el driver usa rutas de dev/ en codigo (no en prosa): "
                      + "; ".join(sospechosos[:4]))

    # Y al reves, la que **si** vale: las herramientas de dev importan la
    # biblioteca del driver, y tienen que seguir apuntando a donde esta.
    dev = driver.parent / "dev"
    if dev.exists():
        mal = []
        for archivo in sorted((dev / "herramientas").glob("*.py")):
            fuente = archivo.read_text(encoding="utf-8")
            if "sys.path.insert" in fuente and "driver" not in fuente:
                mal.append(archivo.name)
        if mal:
            fallos.append(f"estas herramientas de dev no encuentran la "
                          f"biblioteca del driver: {mal}")


# Lo que el programa anota de un mouse va a la maquina de quien lo usa
# (`linshark.lugares`), no al lado del codigo. Instalado, al lado del codigo es
# `/opt/linshark`, que es de root; en el repositorio terminaba versionado:
# **paso**, con 24 respaldos de un mouse en `driver/respaldos/`.
def test_lo_del_mouse_no_va_al_lado_del_codigo(fallos: list[str]) -> None:
    import ast
    import os

    from linshark import lugares

    import tempfile

    # 1. `XDG_STATE_HOME` manda, y sin el es `~/.local/state`. Con un HOME de
    #    mentira: una prueba no mira la carpeta de quien corre los tests.
    antes = {k: os.environ.get(k) for k in ("HOME", "XDG_STATE_HOME")}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["HOME"] = tmp
            os.environ["XDG_STATE_HOME"] = f"{tmp}/estado"
            if lugares.respaldos() != Path(tmp, "estado/linshark/respaldos"):
                fallos.append(f"XDG_STATE_HOME no manda: {lugares.respaldos()}")
            del os.environ["XDG_STATE_HOME"]
            if lugares.carpeta() != Path(tmp, ".local/state/linshark"):
                fallos.append(f"sin XDG_STATE_HOME no es ~/.local/state: "
                              f"{lugares.carpeta()}")
    finally:
        for clave, valor in antes.items():
            if valor is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor

    # 2. Nadie arma la carpeta de respaldos por su cuenta: la da `lugares`.
    driver = Path(__file__).resolve().parent.parent
    archivos = sorted((driver / "src").rglob("*.py")) \
        + sorted((driver / "scripts").glob("*.py"))
    for archivo in archivos:
        if archivo.name == "lugares.py" or "__pycache__" in archivo.parts:
            continue
        arbol = ast.parse(archivo.read_bytes())
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Constant) and nodo.value == "respaldos":
                fallos.append(f"{archivo.relative_to(driver)}:{nodo.lineno} "
                              "arma su propia carpeta de respaldos")


# Todo `.py` del repositorio tiene que compilar, y no solo lo que importan los
# tests. **Paso de verdad**: al poner la cabecera de licencia, en
# `capturas-w/_parse_har.py` quedo **delante** de un BOM que el archivo traia
# de Windows. Un BOM al principio Python lo acepta; en la linea 3 es un
# caracter invisible y el script no arrancaba, sin que ningun test lo tocara.
#
# Compila desde los **bytes**, como carga Python un archivo, y sin escribir
# ningun `.pyc`. Instalado no hay `dev/`, y entonces mira solo el driver.
def test_todo_el_codigo_compila(fallos: list[str]) -> None:
    driver = Path(__file__).resolve().parent.parent
    raices = [driver] + [d for d in [driver.parent / "dev"] if d.is_dir()]

    # El control negativo va primero: si esto compilara, la prueba de abajo
    # no probaria nada.
    roto = b"# cabecera\n\xef\xbb\xbfimport json\n"
    try:
        compile(roto, "bom-en-el-medio.py", "exec")
        fallos.append("un BOM en la linea 2 compila: esta prueba no ve el caso "
                      "que la motivo")
    except SyntaxError:
        pass

    vistos = 0
    for raiz in raices:
        for archivo in sorted(raiz.rglob("*.py")):
            if "__pycache__" in archivo.parts:
                continue
            vistos += 1
            try:
                compile(archivo.read_bytes(), str(archivo), "exec")
            except (SyntaxError, ValueError) as exc:
                fallos.append(f"{archivo.relative_to(driver.parent)} no "
                              f"compila: {exc}")
    if vistos < 20:
        fallos.append(f"solo encontre {vistos} archivos .py: esto dejo de "
                      "mirar el repositorio")


# --- el canal por cable: leido del helper, no capturado --------------------
# Los dos constructores de `protocol.py` son las hipotesis contra las que se va
# a comparar la captura del cliente oficial configurando por cable. Este test
# fija que digan lo que dice el binario, y que se nieguen a lo que el binario
# no dice.
def test_constructores_del_cable(fallos: list[str]) -> None:
    # 1. El pedido de lectura, llamador por llamador de 0x40e380:
    #    `[a0, cmd, sub, 00, perfil, 00, 00, 00]`, con version y 0x0c en 0.
    esperados = {
        p.CMD_DPI: "a004380001000000",
        p.CMD_LIGHTING: "a0050f0001000000",
        p.CMD_REPORT_RATE: "a006090001000000",
        p.CMD_BUTTONS: "a0083b0001000000",
        p.CMD_PROFILE: "a00a800001000000",
        p.CMD_VERSION: "a00b080000000000",
        0x0C: "a00c0a0000000000",
    }
    for cmd, hexa in esperados.items():
        try:
            armado = p.build_cable_read_request(cmd).hex()
        except KeyError as exc:
            fallos.append(f"no arma el pedido de lectura de cmd {cmd}: {exc}")
            continue
        if armado != hexa:
            fallos.append(f"pedido de lectura de cmd {cmd}: {armado}, y el "
                          f"helper arma {hexa}")
    # El macro lleva su id en el byte 4 (0x40fbcb pasa `[ebx+0x8]`, la misma
    # variable que el camino del dongle pone donde va el id). Sin id no hay
    # pedido, y el modo de despertado el helper no lo lee.
    if p.build_cable_read_request(p.CMD_MACRO, macro_id=17).hex() != \
            "a009830011000000":
        fallos.append("el pedido del macro 17 por cable no es "
                      "a0 09 83 00 11 00 00 00")
    for cmd in (p.CMD_MACRO, p.CMD_WAKEUP):
        try:
            p.build_cable_read_request(cmd)
        except KeyError:
            pass
        else:
            fallos.append(f"armo un pedido de lectura por cable para cmd {cmd}, "
                          "que el binario no respalda")

    # 2. El report de escritura: el bloque del dongle sin su relleno.
    dpi = bytes([p.CMD_DPI, 56]) + DPI_REAL
    luz = bytes([p.CMD_LIGHTING, 15]) + LUZ_REAL
    for bloque, largo in ((dpi, 52), (luz, 13)):
        try:
            report = p.build_cable_write_report(bloque, largo)
        except ValueError as exc:
            fallos.append(f"rechazo un bloque legitimo de cmd {bloque[0]}: {exc}")
            continue
        if report != bloque[:largo]:
            fallos.append(f"cmd {bloque[0]}: el report no es el bloque cortado "
                          f"a {largo}: {report.hex()}")
    # Y se niega a cortar datos, a tomar una trama del dongle por un bloque
    # -`04 0e 00 06 ...` seria un "dpi" de 14 bytes- y al macro, que va en trozos.
    malos = {
        "datos despues del largo": (dpi[:53] + b"\x07" + dpi[54:], 52),
        "trama del dongle": (p.build_write_frame(
            bytes([p.CMD_REPORT_RATE, 9]) + bytes.fromhex("0144bb00000000")), 52),
        "macro": (bytes([p.CMD_MACRO, 3, 17]), 64),
        "tamaño que no coincide": (bytes([p.CMD_DPI, 50]) + DPI_REAL, 52),
    }
    for que, (bloque, largo) in malos.items():
        try:
            p.build_cable_write_report(bloque, largo)
        except ValueError:
            pass
        else:
            fallos.append(f"build_cable_write_report acepto {que}")


# Lo que el soft nativo le escribio y le leyo al mouse **por cable**, tal cual
# aparece en `dev/models/attackshark-x8pro/docs/capturas-w/cable-soft-*.pcap`. Cada linea es un Feature
# Report entero, con el cmd de Report ID adelante.
CABLE_LEIDO_DPI = bytes.fromhex(               # cable-soft-abrir, GET(4)
    "04380100013f2000192f436fa18f0000000000000001000001ff000000ff000000ffffff"
    "0000ffffff00ffff4000ffffff020fc100000000")
CABLE_LEIDO_RATE = bytes.fromhex("060901748b00000000")   # abrir, GET(6)
CABLE_ESCRITO = {
    "dpi nivel 1 a 500": "04380100013f2000092f436fa18f0000000000000001000001ff"
                         "000000ff000000ffffff0000ffffff00ffff4000ffffff020fb1",
    "lod 2 mm": "04380110013f2000192f436fa18f0000000000000001000001ff000000ff"
                "000000ffffff0000ffffff00ffff4000ffffff020fd1",
    "rate 500": "060901738c00000000",
    "rate 1000": "060901748b00000000",
    "boton 6 a macro 17": "083b010200000300000400000d00000500001200113c" +
                          "000001" * 9 + "00000a0000090000" + "0096",
    "boton 6 a adelante": "083b010200000300000400000d00000500000600003c" +
                          "000001" * 9 + "00000a0000090000" + "0079",
}
# Los dos trozos del macro 17 en cada modo: el primero lleva los eventos, el
# segundo el checksum interno del bloque de 111.
CABLE_MACRO = {
    modo: ("09401100" + f"{modo:02x}" + "000000010a"
           + "0af18af10af38af30af58af50af48af40af28af2" + "00" * 34,
           "09401101" + "00" * 46 + f"0c{0x6d + modo:02x}" + "00" * 12)
    for modo in (0, 1, 2)
}


def test_etapa2_cable(fallos: list[str]) -> None:
    """La Etapa 2 del cable: nuestros codificadores contra lo que escribio el soft.

    Todo parte de algo que el mouse devolvio -por cable, o por el dongle
    cuando por cable el soft no lo leyo- y tiene que dar **byte a byte** el
    `SET_REPORT` capturado. Donde hay ida y vuelta se prueban las dos.
    """
    from linshark import estructuras as e
    from linshark import sesion

    def report(cmd, datos, largo):
        return p.build_cable_write_report(
            bytes([cmd, p.READ_SUB[cmd]]) + datos, largo)

    def comparar(que, nuestro, cual):
        oficial = bytes.fromhex(CABLE_ESCRITO[cual])
        if nuestro != oficial:
            fallos.append(f"cable, {que}: no da lo que escribio el soft\n"
                          f"      nuestro: {nuestro.hex()}\n"
                          f"      oficial: {oficial.hex()}")

    # El pedido de lectura, en los tres comandos que el soft leyo.
    for cmd, hexa in ((6, "a006090001000000"), (4, "a004380001000000"),
                      (5, "a0050f0001000000")):
        if p.build_cable_read_request(cmd).hex() != hexa:
            fallos.append(f"cable: el pedido de lectura de cmd {cmd} no es el "
                          "del bus")

    # dpi: LOD y nivel 1, ida y vuelta. La vuelta sale de lo que se escribio,
    # que mide 52: se le devuelve el relleno para que sea un bloque de 56.
    def datos_de(report_dpi):
        return report_dpi[2:56].ljust(54, b"\0")

    leido = CABLE_LEIDO_DPI[2:]
    lod2 = report(4, e.escribir_parametros_sensor(leido, lod=1), 52)
    comparar("LOD 2 mm desde la lectura", lod2, "lod 2 mm")
    vuelta = report(4, e.escribir_parametros_sensor(datos_de(lod2), lod=0), 52)
    if vuelta != CABLE_LEIDO_DPI[:52]:
        fallos.append("cable, LOD 1 mm desde lo escrito: no vuelve a la lectura")
    n1 = report(4, e.escribir_nivel_dpi(leido, 1, 500)[0], 52)
    comparar("dpi nivel 1 desde la lectura", n1, "dpi nivel 1 a 500")
    if report(4, e.escribir_nivel_dpi(datos_de(n1), 1, 1300)[0],
              52) != CABLE_LEIDO_DPI[:52]:
        fallos.append("cable, dpi nivel 1 de vuelta: no vuelve a la lectura")

    # rate: el nibble bajo. Y el codificador del dongle **no** sirve por aca:
    # moveria la tasa inalambrica.
    r500 = report(6, e.escribir_report_rate_por_cable(CABLE_LEIDO_RATE[2:],
                                                      hz=500), 9)
    comparar("rate 500 desde la lectura", r500, "rate 500")
    comparar("rate 1000 desde lo escrito",
             report(6, e.escribir_report_rate_por_cable(r500[2:], hz=1000), 9),
             "rate 1000")
    if report(6, e.escribir_report_rate(CABLE_LEIDO_RATE[2:], hz=500), 9) == \
            bytes.fromhex(CABLE_ESCRITO["rate 500"]):
        fallos.append("cable: el codificador del dongle dio el rate del cable; "
                      "si es asi, sobra escribir_report_rate_por_cable")
    if e.report_rate_por_cable_de(CABLE_LEIDO_RATE[2:]) != 1000 or \
            e.report_rate_de(CABLE_LEIDO_RATE[2:]) != 8000:
        fallos.append("cable: 0x74 tendria que ser 1000 Hz por cable y 8000 "
                      "por radio")

    # botones: por cable el soft no los leyo, asi que se parte del bloque que
    # el mouse devuelve por el dongle. Es el mismo mouse y el mismo bloque.
    for valor, cual in ((("macro", 17), "boton 6 a macro 17"),
                        ("adelante", "boton 6 a adelante")):
        m = sesion.preparar_mutacion("boton_costado_adelante", valor)
        comparar(cual, report(8, m.codificar(BOTONES_REAL), 59), cual)

    # macro: el bloque de 111 de siempre, partido en los dos trozos del cable.
    for modo, oficiales in CABLE_MACRO.items():
        bloque = bytes([9, 0x6F]) + e.escribir_macro(
            bytes.fromhex(MACRO_LEIDO), modo=modo)
        nuestros = tuple(t.hex() for t in p.build_cable_macro_reports(bloque))
        if nuestros != oficiales:
            fallos.append(f"cable, macro 17 modo {modo}: los trozos no son los "
                          f"del bus\n      nuestros: {list(nuestros)}\n"
                          f"      oficiales: {list(oficiales)}")
    try:
        p.build_cable_macro_reports(bytes([9, 0x83, 17]) + bytes(128))
    except ValueError:
        pass
    else:
        fallos.append("cable: partio en trozos un macro de 131, que no se vio "
                      "en el bus")


def test_el_cable_solo_pasa_por_su_canal(fallos: list[str]) -> None:
    """Lo que le habla al mouse por cable vive en `cable.py`, y en ningun lado mas.

    Antes este test decia "sin captura, nadie le manda nada": los
    constructores existian para compararlos con la captura. La captura se
    hizo -del soft nativo, `cable-soft-*.pcap`- y la Etapa 2 pasa, asi que
    ahora hay canal. Lo que se sigue cuidando es **que haya uno solo**: el
    ioctl de escritura de Feature Reports y los `build_cable_*` los usa
    `cable.py`, y el camino del dongle -`hidraw.py`, `device.py`, el puente-
    no los conoce. Un segundo lugar que le escriba al cable seria un camino
    sin las barandas de este.
    """
    driver = Path(__file__).resolve().parent.parent
    permitidos = {"protocol.py", "cable.py"}
    usos = []
    for archivo in sorted(driver.rglob("*.py")):
        if "__pycache__" in str(archivo) or archivo.parent.name == "tests":
            continue
        fuente = archivo.read_text(encoding="utf-8")
        if archivo.name not in permitidos and "build_cable_" in fuente:
            usos.append(f"{archivo.relative_to(driver)} usa build_cable_*")
        if archivo.name != "cable.py" and "HIDIOCSFEATURE" in fuente:
            usos.append(f"{archivo.relative_to(driver)} nombra HIDIOCSFEATURE")
    for nombre in ("hidraw.py", "device.py", "backend.py", "server.py"):
        fuente = (driver / "src" / "linshark" / nombre).read_text(
            encoding="utf-8")
        if "import cable" in fuente or "from .cable" in fuente:
            usos.append(f"{nombre}, del camino del dongle, importa el cable")
    if usos:
        fallos.append("el cable tiene otro camino ademas de cable.py: "
                      + "; ".join(usos))


# --- el canal por cable, contra un mouse de mentira ------------------------
# Un mouse que habla **Feature Reports** como el del bus: contesta un `GET`
# solo despues del pedido `0xA0` -sin el, nada: los ocho timeouts de
# `cable-primera-lectura.json`-, devuelve el bloque entero con su relleno aunque
# declare menos, guarda lo que se le escribe sobre lo que tenia, y puede
# rechazar un `SET` con STALL, como hizo 6 de 19 veces en las capturas.
_LARGOS_DEL_CABLE = {4: 52, 5: 13, 6: 9, 8: 59, 9: 64, 10: 8, 11: 8, 12: 6}


class _IoctlDeCable:
    def __init__(self):
        self.reports = {
            p.CMD_DPI: CABLE_LEIDO_DPI,
            p.CMD_LIGHTING: bytes([p.CMD_LIGHTING, 15]) + LUZ_REAL,
            p.CMD_REPORT_RATE: CABLE_LEIDO_RATE,
            p.CMD_BUTTONS: bytes([p.CMD_BUTTONS, 0x3B]) + BOTONES_REAL,
            p.CMD_PROFILE: bytes([p.CMD_PROFILE, 0x80, 1]) + bytes(125),
            p.CMD_VERSION: bytes([p.CMD_VERSION, 8, 1, 2, 3, 4, 5, 6]),
        }
        self._rehacer_perfil()
        #: Los macros por id, **como los devuelve el mouse**: con el checksum
        #: interno invertido (MEDIDO por el dongle).
        self.macros = {17: bytes(_MACRO_COMO_LO_LEE_EL_MOUSE)}
        self.macro_pedido = None
        self.cola_del_macro = bytes(20)
        self._trozos: dict[int, dict[int, bytes]] = {}
        self.pendiente = None
        self.stall = 0
        #: Cuantas veces el `GET` del bloque devuelve el del pedido anterior,
        #: como el `GET(6)` que volvio con la version el 2026-09-18.
        self.ajeno = 0
        self.ultimo = None
        self.sets: list[bytes] = []
        self.gets: list[tuple[int, int]] = []
        #: `(que, reloj)` de cada transferencia, para medir los respiros.
        self.tiempos: list[tuple[str, float]] = []

    def set_feature(self, report):
        import time
        report = bytes(report)
        self.sets.append(report)
        self.tiempos.append((f"set {report[0]:#04x}", time.monotonic()))
        if self.stall:
            self.stall -= 1
            raise OSError(32, "Broken pipe")          # EPIPE: el STALL
        if report[0] == p.CABLE_READ_REPORT_ID:
            self.pendiente = report[1]
            self.macro_pedido = report[4] if report[1] == p.CMD_MACRO else None
            return
        if report[0] == p.CMD_MACRO:
            # `[09, 40, id, trozo, 60 bytes]`: el mouse junta los trozos.
            mid, n = report[2], report[3]
            self._trozos.setdefault(mid, {})[n] = report[4:64]
            if len(self._trozos[mid]) == 2:
                cuerpo = (self._trozos[mid][0] + self._trozos[mid][1])[:108]
                datos = bytes([mid]) + cuerpo
                self.macros[mid] = datos[:-2] + bytes([datos[-1], datos[-2]])
                del self._trozos[mid]
            return
        viejo = self.reports[report[0]]
        self.reports[report[0]] = report + viejo[len(report):]
        self._rehacer_perfil()

    def _rehacer_perfil(self):
        """El perfil completo embebiendo a los bloques, como el mouse real.

        Sin esto el perfil de mentira son 125 ceros, y `sesion.incoherencias()`
        lo marca -con razon-: un estado donde el perfil y el bloque suelto
        dicen cosas distintas es justo lo que esa baranda busca. Un mouse de
        mentira que no lo respeta hace pasar pruebas sobre un mouse que no
        existe.
        """
        from linshark import dispositivos
        embebe = dispositivos.activo().perfil_embebe
        if not embebe:
            return
        perfil = bytearray(self.reports[p.CMD_PROFILE])
        for cmd, (po, bo, L) in embebe.items():
            datos = self.reports.get(cmd, b"")[2:]
            if len(datos) >= bo + L and len(perfil) >= 2 + po + L:
                perfil[2 + po:2 + po + L] = datos[bo:bo + L]
        self.reports[p.CMD_PROFILE] = bytes(perfil)

    def get_feature(self, report_id, largo):
        import time
        self.gets.append((report_id, largo))
        self.tiempos.append((f"get {report_id:#04x}", time.monotonic()))
        if report_id == p.CABLE_READ_REPORT_ID:
            listo = 1 if self.pendiente is not None else 0
            return bytes([p.CABLE_READ_REPORT_ID, listo]) + bytes(largo - 2)
        if report_id != self.pendiente:
            raise OSError(110, "Connection timed out")
        self.pendiente = None
        if self.ajeno and self.ultimo is not None:
            self.ajeno -= 1
            return self.reports[self.ultimo][:largo].ljust(largo, b"\0")
        self.ultimo = report_id
        if report_id == p.CMD_MACRO:
            datos = self.macros.get(self.macro_pedido)
            if datos is None:
                raise OSError(110, "Connection timed out")
            # Como lo devuelve el mouse por cable (MEDIDO,
            # `cable-macro-17.json`): `sizeTotalData` 0x83, el bloque de 111
            # del dongle adentro, y 20 ceros de relleno.
            return (bytes([p.CMD_MACRO, 0x83]) + datos + self.cola_del_macro
                    )[:largo].ljust(largo, b"\0")
        return self.reports[report_id][:largo].ljust(largo, b"\0")


async def test_canal_por_cable(fallos: list[str]) -> None:
    """`CableDevice` y la sesion por cable, byte a byte contra el bus.

    Todo lo que sale se compara con lo que el soft mando en
    `cable-soft-*.pcap`: el pedido `0xA0`, el largo de cada `GET`, el `SET`
    de 52 del LOD y el de 9 del rate. Y lo que **no** tiene que salir: nada
    para el macro, nada de escritura en solo lectura, y ninguna tasa prestada.
    """
    from linshark import cable as c
    from linshark import estructuras as e
    from linshark import sesion

    esperas = (c.ESPERA_TRAS_PEDIDO, c.ESPERA_TRAS_LISTO, c.PAUSA_TRAS_STALL,
               c.PAUSA_DE_LISTO, p.WRITE_BLOCK_PAUSE_SOFT,
               c.PAUSA_TRAS_ESCRITURA, c.PAUSA_ENTRE_PEDIDOS)
    c.ESPERA_TRAS_PEDIDO = c.ESPERA_TRAS_LISTO = c.PAUSA_TRAS_STALL = 0
    c.PAUSA_DE_LISTO = c.PAUSA_ENTRE_PEDIDOS = 0
    p.WRITE_BLOCK_PAUSE_SOFT = 0
    # **El respiro despues de escribir no se pone en cero**: es lo que se
    # prueba abajo. Chico, para que la prueba no tarde.
    c.PAUSA_TRAS_ESCRITURA = 0.05
    try:
        def nuevo(**kw):
            mouse = _IoctlDeCable()
            return mouse, c.CableDevice(Path("/dev/hidraw-cable"),
                                        largos=_LARGOS_DEL_CABLE, ioctl=mouse,
                                        **kw)

        # 1. leer: el pedido, el "listo" y el bloque, con los largos del bus
        mouse, dev = nuevo()
        frame = await dev.leer(p.CMD_DPI)
        if [x.hex() for x in mouse.sets] != ["a004380001000000"]:
            fallos.append(f"el pedido del dpi salio {mouse.sets}")
        if mouse.gets != [(0xA0, 8), (p.CMD_DPI, 56)]:
            fallos.append(f"los GET salieron {mouse.gets}; el soft pidio "
                          "(0xa0, 8) y (4, 56)")
        if frame is None or frame.data != CABLE_LEIDO_DPI[2:56] \
                or frame.sub != 0x38:
            fallos.append("el dpi leido por cable no es el bloque del dongle")

        # 2. el STALL: se repite **el mismo** pedido, y pasa
        mouse, dev = nuevo()
        mouse.stall = 1
        frame = await dev.leer(p.CMD_REPORT_RATE)
        if len(mouse.sets) != 2 or mouse.sets[0] != mouse.sets[1]:
            fallos.append(f"tras un STALL mando {mouse.sets}, y en el bus se "
                          "repite el mismo")
        if frame is None or frame.data != CABLE_LEIDO_RATE[2:]:
            fallos.append("tras un STALL no leyo el rate")

        # 3. escribir: el SET de 52 que mando el soft para el LOD a 2 mm
        mouse, dev = nuevo()
        bloque = bytes([p.CMD_DPI, 0x38]) + e.escribir_parametros_sensor(
            CABLE_LEIDO_DPI[2:], lod=1)
        if not await dev.escribir(bloque):
            fallos.append("no acepto la escritura del LOD")
        if mouse.sets[-1:] != [bytes.fromhex(CABLE_ESCRITO["lod 2 mm"])]:
            fallos.append(f"el LOD salio {mouse.sets[-1:]}, no el del soft")

        # 3b. **Y despues de escribir, nada sale antes del respiro.** Sin el, la
        #     primera corrida contra el mouse escribio el LOD y la relectura,
        #     a los pocos milisegundos, lo mostro sin cambiar.
        await dev.leer(p.CMD_DPI)
        escrito = next(t for q, t in mouse.tiempos if q == "set 0x04")
        siguiente = next(t for q, t in mouse.tiempos if t > escrito)
        if siguiente - escrito < c.PAUSA_TRAS_ESCRITURA * 0.9:
            fallos.append(f"despues de escribir, el pedido siguiente salio a "
                          f"los {(siguiente - escrito) * 1000:.0f} ms: el "
                          "helper espera 500 y el soft nunca menos de 200")

        # 3c. El bloque de otro comando -el buffer con el pedido anterior- no
        #     se toma: se vuelve a pedir.
        mouse, dev = nuevo()
        await dev.leer(p.CMD_VERSION)
        mouse.ajeno = 1
        frame = await dev.leer(p.CMD_REPORT_RATE)
        if frame is None or frame.cmd != p.CMD_REPORT_RATE or \
                frame.data != CABLE_LEIDO_RATE[2:]:
            fallos.append("volvio el bloque de la version al pedir el rate y "
                          "no lo volvio a pedir")

        # 3d. **El Report ID 3 por cable llega igual que por el dongle.** El
        #     descriptor del cable lo declara, y es el aviso del boton de dpi:
        #     sin escucharlo, la ventana no se enteraba.
        vistas = []
        sesion.escuchar_novedades(dev, vistas.append)
        dev.alimentar(bytes.fromhex("0308100200"))     # nivel 2, como el dongle
        dev.alimentar(bytes.fromhex("01000000"))       # movimiento: no importa
        if [(v.tipo, v.nivel_dpi) for v in vistas] != [("nivel-dpi", 2)]:
            fallos.append(f"el Report ID 3 por cable dio {vistas}")

        # 4. el macro: se pide con su id, y se escribe en los trozos del soft
        mouse, dev = nuevo()
        frame = await dev.leer(p.CMD_MACRO, macro_id=17)
        if [x.hex() for x in mouse.sets] != ["a009830011000000"] or \
                mouse.gets[-1] != (p.CMD_MACRO, 0x83):
            fallos.append(f"el macro 17 se pidio {mouse.sets} / {mouse.gets}")
        if frame is None or frame.data != _MACRO_COMO_LO_LEE_EL_MOUSE \
                or frame.sub != 0x6F:
            fallos.append("el macro 17 leido por cable -0x83 con 20 ceros- no "
                          "quedo como el bloque de 111 del dongle")
        # Si lo que sobra no es relleno, es otro bloque: no se corta.
        mouse, dev = nuevo()
        mouse.cola_del_macro = bytes(19) + b"\x01"
        if await dev.leer(p.CMD_MACRO, macro_id=17) is not None:
            fallos.append("corto un macro de cable que traia datos despues de "
                          "los 111")
        if await dev.leer(p.CMD_MACRO) is not None:
            fallos.append("pidio un macro sin id")
        for modo, oficiales in CABLE_MACRO.items():
            mouse, dev = nuevo()
            bloque = bytes([9, 0x6F]) + e.escribir_macro(
                bytes.fromhex(MACRO_LEIDO), modo=modo)
            if not await dev.escribir_por_bloques(bloque):
                fallos.append(f"no acepto el macro en modo {modo}")
            if tuple(x.hex() for x in mouse.sets) != oficiales:
                fallos.append(f"el macro en modo {modo} salio {mouse.sets}, "
                              "no los trozos del soft")
        # un trozo que no entra: se manda **la secuencia entera** de nuevo
        mouse, dev = nuevo()
        c.INTENTOS_POR_STALL, intentos = 1, c.INTENTOS_POR_STALL
        try:
            mouse.stall = 0
            original = mouse.set_feature

            def falla_el_trozo_1_una_vez(report, _hecho=[]):
                if report[0] == p.CMD_MACRO and report[3] == 1 and not _hecho:
                    _hecho.append(1)
                    mouse.sets.append(bytes(report))
                    raise OSError(32, "Broken pipe")
                return original(report)
            mouse.set_feature = falla_el_trozo_1_una_vez
            bloque = bytes([9, 0x6F]) + e.escribir_macro(
                bytes.fromhex(MACRO_LEIDO), modo=0)
            ok = await dev.escribir_por_bloques(bloque)
        finally:
            c.INTENTOS_POR_STALL = intentos
        trozos = [x[3] for x in mouse.sets if x[0] == p.CMD_MACRO]
        if not ok or trozos != [0, 1, 0, 1]:
            fallos.append(f"con el trozo 1 rechazado mando los trozos "
                          f"{trozos}: tiene que volver a empezar por el 0")

        # 5. solo lectura: pasan los pedidos y ningun report de escritura
        mouse, dev = nuevo(solo_lectura=True)
        if await dev.leer(p.CMD_LIGHTING) is None:
            fallos.append("en solo lectura no leyo")
        try:
            await dev.escribir(bloque)
        except PermissionError:
            pass
        else:
            fallos.append("en solo lectura escribio")
        if any(x[0] != p.CABLE_READ_REPORT_ID for x in mouse.sets):
            fallos.append("en solo lectura salio un report que no es pedido")

        # 6. la sesion por cable: sin tasa prestada, el rate en el nibble
        #    bajo, el LOD con su Etapa 3, y el macro rechazado sin leer nada
        mouse, dev = nuevo()
        config = sesion.Configuracion(dev)

        async def si(bloque, trama):
            return True

        prep = await config.preparar()
        if not prep.ok or config.tasa_prestada is not None:
            fallos.append(f"por cable preparar dio {prep.motivo} y presto "
                          f"{config.tasa_prestada}: la tasa del cable es 1000")
        if any(x[0] != p.CABLE_READ_REPORT_ID for x in mouse.sets):
            fallos.append("preparar() escribio algo por cable")
        if prep.antes and set(prep.antes["comandos"]) != {
                str(x) for x in c.A_LEER}:
            fallos.append(f"el respaldo por cable leyo "
                          f"{sorted(prep.antes['comandos'])}")

        r = await config.escribir(
            cmd=p.CMD_REPORT_RATE,
            codificar=sesion.preparar_mutacion("tasa", 500).codificar,
            confirmar=si)
        escritos = [x for x in mouse.sets if x[0] == p.CMD_REPORT_RATE]
        if [x.hex() for x in escritos] != [CABLE_ESCRITO["rate 500"]]:
            fallos.append(f"la tasa por cable salio {escritos}; el soft mando "
                          f"{CABLE_ESCRITO['rate 500']} (el nibble bajo)")
        if not r.ok:
            fallos.append(f"la tasa por cable termino en {r.motivo}")

        m = sesion.preparar_mutacion("lod", 2)
        r = await config.escribir(cmd=m.cmd, codificar=m.codificar,
                                  confirmar=si)
        escritos = [x for x in mouse.sets if x[0] == p.CMD_DPI]
        if escritos != [bytes.fromhex(CABLE_ESCRITO["lod 2 mm"])]:
            fallos.append(f"el LOD por cable salio {escritos}")
        if not r.ok or r.motivo != "cambio-lo-pedido":
            fallos.append(f"el LOD por cable termino en {r.motivo}")

        m = sesion.preparar_mutacion("macro_modo", 2, macro_id=17)
        r = await config.escribir(cmd=m.cmd, codificar=m.codificar,
                                  macro_id=m.macro_id, confirmar=si,
                                  macros_extra=(17,))
        if not r.ok or r.motivo != "cambio-lo-pedido":
            fallos.append(f"el macro por cable termino en {r.motivo}")
        leido = e.parametros_de_macro(mouse.macros[17])
        if leido is None or leido["modo"] != 2 or not leido["checksum_ok"]:
            fallos.append(f"el macro quedo en {leido}, y se pidio modo 2")
    finally:
        (c.ESPERA_TRAS_PEDIDO, c.ESPERA_TRAS_LISTO, c.PAUSA_TRAS_STALL,
         c.PAUSA_DE_LISTO, p.WRITE_BLOCK_PAUSE_SOFT,
         c.PAUSA_TRAS_ESCRITURA, c.PAUSA_ENTRE_PEDIDOS) = esperas


# --- el perfil declarativo no puede mentir ---------------------------------
# `dispositivos.py` es **de donde salen** los numeros del X8 Pro:
# `estructuras.py` no los tiene adentro, se los pide. Eso cambia lo que este
# test puede probar. Antes comparaba cada campo del perfil con
# la constante de la que salio, y estaba bien porque eran dos copias; ahora son
# la misma, y compararlas seria una verificacion que no puede fallar -de las
# que gastan una alarma sin proteger nada-.
#
# Asi que cada campo se compara con **la evidencia**: las capturas del mouse,
# los bloques del bus y las tablas que el bundle declara. Lo que no tiene una
# fuente independiente se dice, y se verifica lo que si se puede: que sea
# coherente con lo que el codificador acepta.
def test_el_perfil_no_miente(fallos: list[str]) -> None:
    from linshark import dispositivos as d
    from linshark import hidraw as h

    perfil = d.perfil_de(p.DEVICE_X8_PRO)

    def igual(que, del_perfil, de_verdad, fuente):
        if del_perfil != de_verdad:
            fallos.append(f"el perfil dice {que}={del_perfil!r} y {fuente} "
                          f"dice {de_verdad!r}")

    # 1. El USB: lo unico que sigue teniendo su copia aparte, en `hidraw.py`,
    #    porque ahi vive la baranda que verifica el nodo antes de abrirlo.
    igual("usb.vendor", perfil.usb.vendor, h.VENDOR_ID, "hidraw")
    igual("usb.producto_dongle", perfil.usb.producto_dongle,
          h.DONGLE_PRODUCT_ID, "hidraw")
    igual("usb.producto_cable", perfil.usb.producto_cable, h.WIRED_PRODUCT_ID,
          "hidraw")
    igual("usb.interfaz", perfil.usb.interfaz, h.CONFIG_INTERFACE, "hidraw")
    igual("usb.report_id", perfil.usb.report_id, h.REPORT_ID, "hidraw")
    igual("usb.report_size", perfil.usb.report_size, h.REPORT_SIZE, "hidraw")

    # 2. Los largos de bloque, contra **el bundle** (`READ_SUB`, que es lo que
    #    el cliente oficial pide) y contra **lo que el mouse contesto**: un
    #    bloque son `sizeTotalData - 2` bytes de datos.
    for cmd, medido in ((p.CMD_LIGHTING, LUZ_REAL), (p.CMD_DPI, DPI_REAL),
                        (p.CMD_BUTTONS, BOTONES_REAL)):
        nombre = p.CMD_NAMES.get(cmd, cmd)
        igual(f"bloques[{nombre}]", perfil.bloques[cmd], p.READ_SUB[cmd],
              "READ_SUB del bundle")
        igual(f"bloques[{nombre}]", perfil.bloques[cmd] - 2, len(medido),
              "lo que contesto el mouse")
    igual("bloques[macro]", perfil.bloques[p.CMD_MACRO], p.READ_SUB[p.CMD_MACRO],
          "READ_SUB del bundle")
    igual("escribibles", perfil.escribibles, frozenset(p.WRITABLE),
          "protocol.WRITABLE")

    # 3. Cuantos botones: sale del bloque real y **sin holgura**. 57 B de datos
    #    = 1 profileId + N*3 + 2 checksum. Con 17 o 19 no cierra.
    igual("botones", perfil.botones, (len(BOTONES_REAL) - 3) // 3,
          "el bloque de cmd 8 que contesto el mouse")
    if 1 + perfil.botones * 3 + 2 != len(BOTONES_REAL):
        fallos.append(f"con {perfil.botones} botones el bloque de cmd 8 no "
                      f"cierra contra los {len(BOTONES_REAL)} B del mouse")

    # 4. Los niveles de dpi: son los bytes de `Dpi_X_setting` del bloque que
    #    contesto el mouse, no una cuenta nuestra.
    campos_dpi = est.decodificar(p.CMD_DPI, DPI_REAL) or {}
    igual("niveles_dpi", perfil.niveles_dpi,
          len(campos_dpi.get("Dpi_X_setting", b"")),
          "el bloque de cmd 4 que contesto el mouse")

    # 5. Los slots de la rueda: son los que en el bloque de fabrica llevan los
    #    dos codigos de scroll, y **no se remapean** (el soft escribe `0a, 09`
    #    y el mouse devuelve `0a, 09`).
    de_fabrica = {b["indice"]: b["codigo"]
                  for b in est.botones_de(BOTONES_REAL)}
    scroll = tuple(sorted(n for n, c in de_fabrica.items()
                          if c in est.RUEDA_COMO_EL_SOFT))
    igual("slots_de_rueda", tuple(sorted(perfil.slots_de_rueda)), scroll,
          "los codigos de scroll del bloque de fabrica")

    # 6. La permutacion de slots, contra el A/B del bus: lo que el soft escribe
    #    en el slot N es lo que el mouse devuelve en el slot que dice el
    # perfil. Es la medicion, no una tabla nuestra.
    escrito = {b["indice"]: b["codigo"]
               for b in est.botones_de(BOTONES_ESCRIBE_EL_SOFT)}
    for leido, esc in perfil.remapeo_de_slots.items():
        if de_fabrica.get(leido) != escrito.get(esc):
            fallos.append(f"el perfil dice que lo escrito en {esc} se lee en "
                          f"{leido}, y en el bus el mouse devolvio "
                          f"{de_fabrica.get(leido)} donde el soft escribio "
                          f"{escrito.get(esc)}")
    if any(n not in perfil.remapeo_de_slots and de_fabrica.get(n) != escrito.get(n)
           for n in de_fabrica):
        fallos.append("hay slots que difieren entre lo escrito y lo leido y "
                      "el perfil no los declara remapeados")

    # 7. Que boton es cada slot. El unico con verificacion fisica directa en
    #    estos bytes es el costado-adelante: cuando el soft lo remapeo a
    #    "reproducir / pausar", el mouse devolvio **un solo slot cambiado**.
    tras = {b["indice"]: b["codigo"]
            for b in est.botones_de(BOTONES_TRAS_REMAPEO)}
    movidos = [n for n in tras if tras[n] != de_fabrica.get(n)]
    igual("botones_por_nombre['costado-adelante']",
          perfil.botones_por_nombre.get("costado-adelante"),
          movidos[0] if len(movidos) == 1 else movidos,
          "el slot que cambio al remapear ese boton fisico")
    for nombre, slot in perfil.botones_por_nombre.items():
        if not 1 <= slot <= perfil.botones:
            fallos.append(f"{nombre} apunta al slot {slot}, que este mouse no "
                          "tiene")
        if slot in perfil.slots_de_rueda:
            fallos.append(f"{nombre} apunta a un slot de la rueda, que no se "
                          "remapea")
        if slot not in perfil.como_se_supo_el_boton:
            fallos.append(f"el slot {slot} ({nombre}) se dibuja como un boton "
                          "fisico y el perfil no dice como se supo")

    # 8. Donde puede quedar el clic izquierdo. Es una decision -el 6 y el 7
    #    estan en la base- y lo que se puede verificar es que no se contradiga
    #    con el mouse: el slot que lo trae de fabrica tiene que poder tenerlo,
    #    o la baranda rechazaria el bloque de fabrica.
    con_clic = [n for n, c in de_fabrica.items()
                if c == est.FUNCION_CLIC_IZQUIERDO]
    for n in con_clic:
        if n not in perfil.slots_para_clic_izquierdo:
            fallos.append(f"el slot {n} trae el clic izquierdo de fabrica y "
                          "el perfil no lo deja tenerlo")
    for n in perfil.slots_para_clic_izquierdo:
        if n not in perfil.botones_por_nombre.values():
            fallos.append(f"el slot {n} podria llevar el clic izquierdo y no "
                          "es un boton fisico de este mouse")

    # 9. Las tasas, contra la tabla del protocolo; los ids de macro, contra el
    #    rango con el que `protocol` valida el pedido.
    igual("tasas", set(perfil.tasas), set(p.RATE_INDICE), "protocol.RATE_HZ")
    igual("macro_id_min", perfil.macro_id_min, p.MACRO_ID_MIN, "protocol")
    igual("macro_id_max", perfil.macro_id_max, p.MACRO_ID_MAX, "protocol")

    # 10. Cuantos eventos entran: es el largo del bloque menos las dos
    #     cabeceras y el checksum, partido en pares. Se recalcula desde
    #     `READ_SUB`, que es la fuente de afuera.
    sitio = p.READ_SUB[p.CMD_MACRO] - 2 - est.MACRO_EVENTOS_OFFSET - 2
    igual("macro_eventos_max", perfil.macro_eventos_max, sitio // 2,
          "el sitio que queda en el bloque de cmd 9")

    # 11. El rango de dpi **no tiene fuente independiente en el codigo**: sale
    #     del control de la pagina oficial (100 a 40000). Lo que si se puede
    #     verificar es que el codificador lo acepte entero y no mas.
    if perfil.dpi_minimo >= perfil.dpi_maximo:
        fallos.append("el rango de dpi del perfil esta al reves")
    for valor, tiene_que_entrar in ((perfil.dpi_minimo, True),
                                    (perfil.dpi_maximo, True),
                                    (perfil.dpi_maximo + 1, False)):
        try:
            est.escribir_nivel_dpi(DPI_REAL, 1, valor)
        except ValueError:
            entro = False
        else:
            entro = True
        if entro != tiene_que_entrar:
            fallos.append(f"{valor} dpi {'no ' if tiene_que_entrar else ''}"
                          f"entro, y el perfil dice {perfil.dpi_minimo}.."
                          f"{perfil.dpi_maximo}")

    # 12. Y lo que el mouse no ofrece se dice con su motivo, no con un True
    #     pelado: es lo que la ventana muestra cuando alguien pregunta por que
    #     falta un control.
    for clave, motivo in perfil.campos_ausentes.items():
        if not motivo or len(motivo) < 20:
            fallos.append(f"campos_ausentes[{clave!r}] no dice por que")

    # Y lo que el modelo nombra nunca puede pasarse de los niveles que el
    # bloque de cmd 4 trae (punto 4): el modelo solo nombra
    # los niveles que el mouse tiene cargados -seis de los ocho en este X8
    # Pro-, asi que contar `dpi_nivel_*` o `color_nivel_*` mediria la
    # configuracion y no el hardware.
    from linshark import modelo
    claves = {c.clave for c in modelo.campos_de(_estado_de_prueba())}
    for prefijo in ("dpi_nivel_", "color_nivel_"):
        de_mas = [k for k in claves if k.startswith(prefijo)
                  and int(k[len(prefijo):]) > perfil.niveles_dpi]
        if de_mas:
            fallos.append(f"el modelo nombra {sorted(de_mas)}, y este mouse "
                          f"tiene {perfil.niveles_dpi} niveles")

    # --- y el catalogo dice lo que sabe y lo que no ---------------------
    cat = d.catalogo()
    if len(cat) != len(p.MOUSE_NUM):
        fallos.append(f"el catalogo tiene {len(cat)} y el bundle "
                      f"{len(p.MOUSE_NUM)}")
    # **Saber que un modelo existe no es saber hablarle.** Si algun dia
    # PERFILES crece sin que nadie mida nada, esto lo dice.
    if set(d.PERFILES) - set(cat):
        fallos.append("hay perfiles de modelos que el catalogo no conoce")
    for device_id in d.PERFILES:
        if device_id != p.DEVICE_X8_PRO:
            fallos.append(f"apareció un perfil para el device id {device_id}: "
                          "si se midió de verdad, sacá esta línea del test; si "
                          "se copió del X8 Pro, no")

    # un modelo del catalogo sin perfil tiene que explicarse, no reventar
    for device_id, (nombre, _) in cat.items():
        if device_id in d.PERFILES:
            continue
        try:
            d.perfil_de(device_id)
        except d.ModeloDesconocido as exc:
            if nombre not in str(exc) or "captura" not in str(exc):
                fallos.append(f"el error de {nombre} no dice que falta medirlo")
        else:
            fallos.append(f"{nombre} devolvio un perfil que nadie midio")
        break        # con uno alcanza: el mensaje es el mismo

    # y uno que no existe tampoco revienta
    try:
        d.perfil_de(0xFFFF)
    except d.ModeloDesconocido:
        pass
    except Exception as exc:                       # noqa: BLE001
        fallos.append(f"un device id inventado tiro {type(exc).__name__}")
    else:
        fallos.append("un device id inventado devolvio un perfil")


# --- y el perfil manda de verdad -------------------------------------------
# El compañero del test de arriba, y el que prueba el trabajo:
# que `estructuras.py` **lea** del perfil en vez de tener los numeros adentro.
# Se hace con un mouse que no existe -otros largos, otros botones, otros
# niveles- y mirando que cambie todo lo que tiene que cambiar. Si alguien
# vuelve a escribir un 18 o un 56 en una funcion, aca se pone rojo: con este
# perfil esos numeros son 7 y 40.
def test_el_perfil_manda_de_verdad(fallos: list[str]) -> None:
    from dataclasses import replace
    from linshark import dispositivos as d
    from linshark.perfiles.x8pro import X8_PRO

    #: Un mouse de fantasia: siete botones, cuatro niveles de dpi, bloques mas
    #: cortos. **No se agrega a `PERFILES`**: no esta medido y no existe.
    otro = replace(
        X8_PRO, device_id=0, nombre="mouse de prueba", marca=None,
        bloques={p.CMD_LIGHTING: 15, p.CMD_DPI: 40, p.CMD_BUTTONS: 26,
                 p.CMD_MACRO: 61},
        botones=7, niveles_dpi=4,
        slots_para_clic_izquierdo=(1, 2),
        slots_de_rueda=(6, 7), remapeo_de_slots={},
        botones_por_nombre={"izquierdo": 1, "derecho": 2, "rueda": 3,
                            "modo": 5},
        como_se_supo_el_boton={1: "inventado", 2: "inventado", 3: "inventado",
                               5: "inventado"},
        dpi_minimo=200, dpi_maximo=12000, macro_id_max=32)

    def dice(que, valor, esperado):
        if valor != esperado:
            fallos.append(f"con otro perfil, {que} dio {valor!r} y tenia que "
                          f"dar {esperado!r}: hay un numero del X8 Pro escrito "
                          "adentro")

    de_este_mouse = (est.BOTONES_CANTIDAD, est.DPI_SIZE, est.MACRO_EVENTOS_MAX)

    with d.como(otro):
        # 1. las constantes de siempre valen lo del perfil nuevo
        dice("BOTONES_CANTIDAD", est.BOTONES_CANTIDAD, 7)
        dice("DPI_SIZE", est.DPI_SIZE, 40)
        dice("BOTONES_SIZE", est.BOTONES_SIZE, 26)
        dice("SLOTS_DE_RUEDA", est.SLOTS_DE_RUEDA, (6, 7))
        dice("SLOT_DE_MODO", est.SLOT_DE_MODO, 5)
        dice("MACRO_EVENTOS_MAX", est.MACRO_EVENTOS_MAX,
             (61 - 2 - est.MACRO_EVENTOS_OFFSET - 2) // 2)

        # 2. la tabla de campos del dpi se corre entera: cuatro niveles, y los
        #    dos campos de sensibilidad miden cuatro bytes, no ocho
        off = est.offsets(p.CMD_DPI)
        dice("Dpi_X_setting", off["Dpi_X_setting"][1], 4)
        dice("niveles en la tabla",
             sum(1 for k in off if k.startswith("Dpi_level_")), 4)
        if "Dpi_level_5_indication_flag" in off:
            fallos.append("la tabla de dpi sigue teniendo ocho niveles")
        dice("fin_de_campos(dpi)", est.fin_de_campos(p.CMD_DPI),
             sum(largo for _, largo, _ in est.DPI))

        # 3. el bloque de botones tambien: 1 + 7*3 + 2 = 24 B de datos
        dice("fin_de_campos(botones)", est.fin_de_campos(p.CMD_BUTTONS), 22)
        bloque = bytes([1]) + bytes([2, 0, 0]) * 7 + b"\x00\x00"
        bots = est.botones_de(bloque)
        dice("cuantos slots decodifica", len(bots or []), 7)
        try:
            est.escribir_boton(bloque, slot=8, codigo=2)
        except ValueError as exc:
            if "1 a 7" not in str(exc):
                fallos.append(f"el error no habla de los slots de este mouse: "
                              f"{exc}")
        else:
            fallos.append("escribio el slot 8 en un mouse de siete botones")

        # 4. y el macro se arma con el largo de ESTE bloque
        armado = est.armar_macro(1, [("a", 0, 10), ("a", 1, 10)])
        dice("largo del bloque de macro", len(armado), 61 - 2)
        try:
            est.armar_macro(33, [("a", 0, 10), ("a", 1, 10)])
        except ValueError:
            pass
        else:
            fallos.append("acepto un macro id que este mouse no tiene")

    # 5. y al salir, todo vuelve a ser del X8 Pro
    if (est.BOTONES_CANTIDAD, est.DPI_SIZE, est.MACRO_EVENTOS_MAX) != de_este_mouse:
        fallos.append("el perfil no volvio al de este mouse al cerrar el "
                      "bloque: `dispositivos.como()` dejo el estado cambiado")
    if 0 in d.PERFILES:
        fallos.append("el mouse de fantasia quedo en PERFILES, que es la lista "
                      "de los que estan medidos")

    # 6. **Leer un estado de ese mouse, sin activarlo a mano.** Es lo que
    # `modelo.campos_de(estado, perfil)` promete, y antes no
    #    hacia: los decodificadores median el bloque contra el perfil activo
    #    -el X8 Pro-, no pasaba el chequeo de largo y la funcion devolvia una
    #    **lista vacia sin decir nada**. Lo encontro una auditoria externa.
    with d.como(otro):
        bloque = est.poner_checksum_interno(
            p.CMD_BUTTONS, bytes([1]) + bytes([2, 0, 0]) * otro.botones
            + b"\x00\x00")
    ajeno = {"comandos": {str(p.CMD_BUTTONS): {"datos": bloque.hex()}}}
    from linshark import modelo
    claves = [c.clave for c in modelo.campos_de(ajeno, otro)]
    if not claves:
        fallos.append("campos_de(estado, perfil) con un mouse de otro modelo "
                      "no devolvio ningun campo: el perfil que se le pasa no "
                      "llega a los decodificadores")
    if d.activo() is not X8_PRO:
        fallos.append("campos_de() dejo puesto el perfil que le pasaron: el "
                      "hilo que habla con el mouse decodificaria con el "
                      "perfil equivocado")

    # 7. Un mouse **sin boton de modo** -o sin rueda- no puede reventar al
    #    preguntar por su slot: da None, que es un slot con el que nada compara
    #    igual. Antes `SLOT_DE_MODO` hacia `[...]` y tiraba `KeyError`.
    pelado = replace(otro, botones_por_nombre={"izquierdo": 1, "derecho": 2},
                     como_se_supo_el_boton={1: "inventado", 2: "inventado"})
    with d.como(pelado):
        try:
            if est.SLOT_DE_MODO is not None:
                fallos.append("un mouse sin boton de modo devolvio un slot de "
                              "modo")
            if est.SLOT_DEL_CLIC_DE_RUEDA is not None:
                fallos.append("un mouse sin clic de rueda devolvio un slot")
            dice("BOTONES_POR_NOMBRE_MAX", est.BOTONES_POR_NOMBRE_MAX, 2)
        except Exception as exc:                   # noqa: BLE001
            fallos.append(f"preguntar por un boton que este mouse no tiene "
                          f"revento: {type(exc).__name__}: {exc}")

    # 8. Y la advertencia del boton de modo sigue **al slot del perfil**, que
    #    es donde esta ese boton en ese mouse. Era un dict de modulo y se
    #    quedaba con el numero del X8 Pro.
    with d.como(otro):
        if sorted(modelo.notas_por_slot()) != [1, otro.botones_por_nombre["modo"]]:
            fallos.append(f"las notas por slot salieron "
                          f"{sorted(modelo.notas_por_slot())} y el boton de "
                          f"modo de ese mouse es el "
                          f"{otro.botones_por_nombre['modo']}")
    with d.como(pelado):
        if modelo.notas_por_slot().get(7):
            fallos.append("un mouse sin boton de modo trae la advertencia del "
                          "boton de modo igual")

    # 9. Y `como()` es **de este hilo**: la ventana puede mirar un estado ajeno
    #    sin cambiarle el perfil al hilo que esta hablando con el mouse.
    import threading
    visto = []
    with d.como(otro):
        hilo = threading.Thread(target=lambda: visto.append(d.activo()))
        hilo.start()
        hilo.join()
    if visto and visto[0] is not X8_PRO:
        fallos.append("`como()` le cambio el perfil a otro hilo: el que "
                      "decodifica lo que contesta el mouse leeria con el "
                      "perfil equivocado")


def test_modelo_de_macros(fallos: list[str]) -> None:
    from linshark import modelo

    def estado_con(texto, macro_id=17):
        escrito = bytes(est.armar_macro(
            macro_id, est.eventos_desde_texto(texto)))
        # como lo devuelve el mouse: el checksum interno al reves
        leido = escrito[:-2] + bytes([escrito[-1], escrito[-2]])
        return {"comandos": {},
                "macros": {str(macro_id): {"datos": leido.hex(),
                                           "checksum_ok": True}}}

    # 1. un macro sano: se lee entero y su texto se puede volver a escribir
    sano = "clic-izquierdo:dir0@10, clic-izquierdo:dir1@10"
    m = modelo.macros_de(estado_con(sano))[0]
    if m.id != 17:
        fallos.append(f"el id salio {m.id}")
    if not m.corre or m.advertencias:
        fallos.append(f"un macro sano dio advertencias: {m.advertencias}")
    if m.texto != sano:
        fallos.append(f"el texto no vuelve igual: {m.texto!r}")
    # y volver a parsearlo tiene que dar los mismos eventos: es lo que hace
    # que la interfaz pueda mostrar y reescribir sin traducir nada
    # se comparan en su forma canonica: el decodificador agrega `nombre` y
    # `largo`, que son de presentacion y no viajan al mouse.
    canonico = lambda evs: [est.normalizar_evento(x) for x in evs]
    if canonico(est.eventos_desde_texto(m.texto)) != canonico(m.eventos):
        fallos.append("el texto del macro no vuelve a parsear igual")
    if m.nombre != "macro 17" or m.nombre_propio is not None:
        fallos.append(f"sin nombre puesto deberia decir 'macro 17', dijo "
                      f"{m.nombre!r}/{m.nombre_propio!r}")

    # 2. el nombre lo pone la aplicacion, no el mouse
    class _Nombres:
        def nombre(self, mid):
            return "copiar y pegar" if mid == 17 else None

    m = modelo.macros_de(estado_con(sano), _Nombres())[0]
    if m.nombre != "copiar y pegar" or m.nombre_propio != "copiar y pegar":
        fallos.append(f"no tomo el nombre de la app: {m.nombre!r}")

    # 3. **las dos advertencias medidas tienen que salir**: un
    #    macro de un evento no corre, y uno que no cierra traba la tecla.
    m = modelo.macros_de(estado_con("a:dir0@10"))[0]
    if m.corre:
        fallos.append("un macro de un evento figura como que corre")
    junto = " ".join(m.advertencias)
    if "no se reproduce" not in junto:
        fallos.append("no avisa que un macro de un evento no corre")
    if "desconectar el receptor" not in junto:
        fallos.append("no avisa como se despega una tecla trabada")

    m = modelo.macros_de(estado_con("a:dir0@10, b:dir0@10"))[0]
    if not any("apretado" in a for a in m.advertencias):
        fallos.append("no avisa que el macro deja teclas apretadas")

    # 4. y un macro sano no las dispara: una alarma que suena siempre no dice
    # nada (la leccion)
    base = ("clic-izquierdo:dir0@10, clic-izquierdo:dir1@10, "
            "clic-rueda:dir0@10, clic-rueda:dir1@10")
    if modelo.macros_de(estado_con(base))[0].advertencias:
        fallos.append("un macro sano dispara advertencias")

    # 5. lo que el mouse no contesto se devuelve igual, dicho: esconderlo
    #    haria creer que el macro no existe
    m = modelo.macros_de({"comandos": {}, "macros": {"9": None}})[0]
    if m.id != 9 or not m.advertencias:
        fallos.append("un macro que no contesto se perdio o no se explica")

    # 6. un estado sin macros no revienta
    if modelo.macros_de({"comandos": {}}) != []:
        fallos.append("un estado sin macros no dio la lista vacia")


async def test_el_orquestador_aborta_donde_debe(fallos: list[str]) -> None:
    from linshark import sesion

    async def si(bloque, trama):
        return True

    async def no(bloque, trama):
        return False

    # 1. Respaldo incompleto -> no se escribe. Es la Etapa 0: sin red, nada.
    mouse = _MouseFalso(completo=False)
    r = await sesion.aplicar(mouse, cmd=p.CMD_REPORT_RATE,
                             codificar=lambda leido: est_rate(2000),
                             confirmar=si)
    if r.ok or r.motivo != "respaldo-incompleto":
        fallos.append(f"con el respaldo incompleto dio {r.motivo!r}")
    if mouse.escrituras:
        fallos.append("escribio sin respaldo completo")

    # 2. Sin confirmar -> no se escribe.
    mouse = _MouseFalso()
    r = await sesion.aplicar(mouse, cmd=p.CMD_REPORT_RATE,
                             codificar=lambda leido: est_rate(2000),
                             confirmar=no)
    if r.ok or r.motivo != "sin-confirmar":
        fallos.append(f"sin confirmar dio {r.motivo!r}")
    if mouse.escrituras:
        fallos.append("escribio sin confirmacion")

    # 3. A tasa alta, sin pedir bajarla -> no se escribe.
    mouse = _MouseFalso(hz=8000)
    r = await sesion.aplicar(mouse, cmd=p.CMD_DPI,
                             codificar=lambda leido: leido, confirmar=si)
    if r.ok or r.motivo != "tasa-alta":
        fallos.append(f"a 8000 Hz sin --bajar-y-restaurar dio {r.motivo!r}")
    if mouse.escrituras:
        fallos.append("escribio con el mouse a 8000 Hz sin bajarlo")

    # 3a. **La idempotencia se mide contra la referencia, no contra lo leido.**
    # En cmd 8 y cmd 9 lo idempotente sale DISTINTO de lo leido a proposito
    # -los slots permutados, el checksum invertido-, asi que comparar con
    # `leido` le daria `no-cambio-nada` a una escritura que salio perfecta. Se
    # descubrio al ir a migrar el CLI encima.
    from linshark import estructuras as e
    for cmd, referencia in (
            (p.CMD_BUTTONS, e.retraducir_botones),
            (p.CMD_MACRO, e.escribir_macro),
            (p.CMD_REPORT_RATE, lambda b: b),
            (p.CMD_DPI, lambda b: b)):
        mouse = _MouseFalso()
        leido = mouse.bloques[cmd]
        esperado = bytes(referencia(leido))
        if sesion.referencia_idempotente(cmd, leido) != esperado:
            fallos.append(f"referencia_idempotente({cmd}) no es la del "
                          "codificador de ese comando")
        # el codificador que no cambia nada tiene que dar "sin diferencias"
        r = await sesion.aplicar(mouse, cmd=cmd,
                                 codificar=lambda _b, x=esperado: x,
                                 confirmar=si)
        if not r.ok or r.motivo != "sin-diferencias":
            nombre = p.CMD_NAMES.get(cmd, cmd)
            fallos.append(f"{nombre} idempotente dio {r.motivo!r}, esperaba "
                          "'sin-diferencias'")

    # y si quien llama la sabe, **manda lo que diga** por encima de la
    # inferencia: la misma escritura que arriba salio 'sin-diferencias' tiene
    # que salir 'no-cambio-nada' si se la declara como un cambio real.
    mouse = _MouseFalso()
    quieto = bytes(e.retraducir_botones(mouse.bloques[p.CMD_BUTTONS]))
    r = await sesion.aplicar(mouse, cmd=p.CMD_BUTTONS,
                             codificar=lambda _b: quieto, confirmar=si,
                             idempotente=False)
    if r.ok or r.motivo != "no-cambio-nada":
        fallos.append(f"con idempotente=False explicito dio {r.motivo!r}: la "
                      "inferencia le gano a quien llama")

    # **Devolver el bloque leido en cmd 8 NO es idempotente**, y es la baranda
    # que costo tres botones rotados. El mouse falso lo aplica
    # como lo aplicaria uno real, asi que esto tiene que verse como un cambio.
    mouse = _MouseFalso()
    r = await sesion.aplicar(mouse, cmd=p.CMD_BUTTONS,
                             codificar=lambda leido: leido, confirmar=si,
                             idempotente=True)
    if r.ok:
        fallos.append("devolver el bloque leido en cmd 8 paso como "
                      "idempotente: eso rota los slots 4, 5 y 6")

    # 3b. Y el permiso puede venir por callback, para que quien llama pregunte
    # ANTES de que se toque nada: bajar la tasa es una escritura, y pasa antes
    # del `confirmar` de la escritura principal. Un "no" ahi no puede dejar el
    # mouse con la tasa movida.
    preguntado = []

    async def no_bajar(hz):
        preguntado.append(hz)
        return False

    mouse = _MouseFalso(hz=8000)
    r = await sesion.aplicar(mouse, cmd=p.CMD_DPI,
                             codificar=lambda leido: leido, confirmar=si,
                             bajar_la_tasa=no_bajar)
    if preguntado != [8000]:
        fallos.append(f"no se le pregunto al callback de tasa: {preguntado!r}")
    if r.ok or r.motivo != "tasa-alta":
        fallos.append(f"el 'no' del callback de tasa dio {r.motivo!r}")
    if mouse.escrituras:
        fallos.append("escribio despues de que el callback de tasa dijera que "
                      "no: bajar la tasa ya es tocar el mouse")

    # 4. A tasa alta pidiendo bajarla: escribe, y **la tasa vuelve**.
    mouse = _MouseFalso(hz=8000)
    r = await sesion.aplicar(mouse, cmd=p.CMD_DPI,
                             codificar=lambda leido: leido, confirmar=si,
                             bajar_la_tasa=True)
    if r.motivo != "sin-diferencias":
        fallos.append(f"idempotente con la tasa bajada dio {r.motivo!r}")
    if r.tasa_bajada_desde != 8000:
        fallos.append(f"no anoto desde que tasa bajo: {r.tasa_bajada_desde}")
    from linshark import estructuras as e
    quedo = e.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE])
    if quedo != 8000:
        fallos.append(f"no devolvio la tasa: quedo en {quedo} Hz, no en 8000")

    # 5. El camino feliz de un cambio real: cambia lo pedido y nada mas.
    mouse = _MouseFalso()
    r = await sesion.aplicar(mouse, cmd=p.CMD_REPORT_RATE,
                             codificar=lambda leido: est_rate(2000),
                             confirmar=si)
    if not r.ok or r.motivo != "cambio-lo-pedido":
        fallos.append(f"el camino feliz dio {r.motivo!r} (ok={r.ok})")
    if not r.aplicada:
        fallos.append("no registro el acuse")
    if e.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE]) != 2000:
        fallos.append("no aplico el cambio al mouse falso")

    # 6. El mouse se calla justo despues del respaldo: el paso 2 lo agarra.
    #    El paso 0 gasta una lectura (la tasa) antes del respaldo, asi que el
    #    corte va una despues de las que consume `leer_estado`.
    mouse = _MouseFalso()
    await sesion.leer_estado(mouse, nodo="")
    n = mouse.lecturas + 1
    mouse = _MouseFalso(mudo_tras=n)
    r = await sesion.aplicar(mouse, cmd=p.CMD_DPI,
                             codificar=lambda leido: leido, confirmar=si)
    if r.ok or r.motivo != "no-contesto":
        fallos.append(f"con el mouse mudo en el paso 2 dio {r.motivo!r}")
    if mouse.escrituras:
        fallos.append("escribio sin haber podido leer el bloque a modificar")


async def test_no_se_escribe_un_bloque_imposible(fallos: list[str]) -> None:
    """Un bloque con valores que el mouse no puede tener no sale al bus.

    **Es una regresion con los bytes de verdad.** El 2026-09-20, por cable, una
    relectura de cmd 5 devolvio `01 74 8b 00 ...` -hibernacion 128 min,
    respuesta 0- y `escribir_reposo_ligero()` la reescribio tal cual con el
    reposo bien puesto. El mouse quedo con cuatro campos que nadie pidio, y con
    el checksum recalculado, asi que **nada aguas abajo podia notarlo**: el
    paso 6 comparo contra un respaldo que ya no describia al mouse.

    Las cuatro puntas que importan:

      1. sobre una lectura podrida, `aplicar()` corta y **no escribe**;
      2. sobre una lectura sana no se inventa una alarma -una falsa gasta a las
         de verdad, que en este proyecto son la unica red-;
      3. **un bloque bueno sobre un mouse podrido si se escribe**, que es lo
         que permite restaurarlo. Si la baranda mirara la lectura en vez de la
         escritura, el mouse quedaria trabado en el estado malo;
      4. los comandos sin rango conocido devuelven None **por no tener con que
         juzgar**, y eso no puede leerse como "esta bien".
    """
    from linshark import estructuras as e
    from linshark import sesion

    async def si(bloque, trama):
        return True

    # Los dos bloques son los del incidente, tal cual salieron en el log y en
    # `dev/models/attackshark-x8pro/respaldos/cable-{antes,despues}-de-A.json`.
    PODRIDO = bytes.fromhex("01748b00000000010001000000")
    SANO = bytes.fromhex("010003c800ff00010201cd0000")

    # 0. El juicio, sobre los bytes que de verdad pasaron por el bus.
    if e.fuera_de_rango(p.CMD_LIGHTING, SANO) is not None:
        fallos.append("da por imposible el bloque sano de cmd 5")
    motivo = e.fuera_de_rango(p.CMD_LIGHTING, PODRIDO)
    if motivo is None:
        fallos.append("el bloque podrido de cmd 5 pasa como bueno")
    elif "hibernacion" not in motivo or "respuesta" not in motivo:
        fallos.append(f"el motivo no nombra los dos campos rotos: {motivo!r}")

    # Y lo que el codificador hace con el: copiarlo. Ese es el bug entero, y si
    # algun dia deja de copiar, este test perdio su objeto y hay que decirlo.
    if e.escribir_reposo_ligero(PODRIDO, minutos=0.5)[:10] != PODRIDO[:10]:
        fallos.append("escribir_reposo_ligero ya no copia el bloque que "
                      "recibe: la regresion perdio su objeto")

    # 1. Sobre una lectura podrida no se escribe nada.
    mouse = _MouseFalso()
    mouse.bloques[p.CMD_LIGHTING] = PODRIDO
    mouse._rehacer_perfil()      # el mouse real mueve el perfil con el bloque
    r = await sesion.aplicar(
        mouse, cmd=p.CMD_LIGHTING,
        codificar=lambda leido: e.escribir_reposo_ligero(leido, minutos=0.5),
        confirmar=si)
    if r.ok or r.motivo != "bloque-imposible":
        fallos.append(f"con la lectura podrida dio {r.motivo!r} (ok={r.ok})")
    if mouse.escrituras:
        fallos.append("escribio un bloque con valores que el mouse no puede "
                      "tener")

    # 2. Sobre una lectura sana, ni una alarma.
    mouse = _MouseFalso()
    mouse.bloques[p.CMD_LIGHTING] = SANO
    mouse._rehacer_perfil()
    r = await sesion.aplicar(
        mouse, cmd=p.CMD_LIGHTING,
        codificar=lambda leido: e.escribir_reposo_ligero(leido, minutos=1),
        confirmar=si)
    if r.motivo == "bloque-imposible":
        fallos.append("alarma falsa sobre un bloque sano de cmd 5")
    if not mouse.escrituras:
        fallos.append("no escribio un cambio bueno de cmd 5")

    # 3. **Restaurar tiene que poder**: mouse podrido, bloque bueno entero.
    mouse = _MouseFalso()
    mouse.bloques[p.CMD_LIGHTING] = PODRIDO
    mouse._rehacer_perfil()      # el mouse real mueve el perfil con el bloque
    r = await sesion.aplicar(mouse, cmd=p.CMD_LIGHTING,
                             codificar=lambda leido: SANO, confirmar=si)
    if r.motivo == "bloque-imposible":
        fallos.append("la baranda no deja restaurar un mouse que quedo mal: "
                      "estaria mirando la lectura en vez de la escritura")
    if not mouse.escrituras:
        fallos.append("no escribio el bloque de restauracion")
    if mouse.bloques[p.CMD_LIGHTING] != SANO:
        fallos.append("la restauracion no dejo el bloque bueno en el mouse")

    # 4. Lo que no sabe juzgar lo dice, en vez de dar el visto bueno.
    for cmd in (p.CMD_DPI, p.CMD_BUTTONS, p.CMD_MACRO, p.CMD_REPORT_RATE):
        if cmd in e.CMDS_CON_RANGO:
            fallos.append(f"cmd {cmd} dice tener rango y nadie lo escribio")
        if e.fuera_de_rango(cmd, b"\xff" * 60) is not None:
            fallos.append(f"cmd {cmd} juzga un bloque sin tener con que")


async def test_el_sangrado_de_buffer_se_detecta(fallos: list[str]) -> None:
    """Una lectura que trae el buffer de otro bloque no llega a un codificador.

    **El caso es el del 2026-09-20, con los bytes de verdad.** Pedido el bloque
    de cmd 5 por cable, el mouse devolvio el payload entero de cmd 6
    -`01 74 8b 00 00 00 00`- relleno con ceros y **con el byte 0 en 0x05**. El
    unico filtro que habia miraba el byte 0, asi que paso entero, fue a un
    codificador que le cambio su byte y le **recalculo** el checksum, y salio
    al mouse.

    Las dos mitades:

      1. `checksum_interno_cierra()` separa un bloque bueno del sangrado, y
         devuelve None -no False- donde no hay checksum que mirar;
      2. `_por_que_no_sirve()` lo rechaza, y sigue rechazando el bloque ajeno
         de siempre.
    """
    from linshark import cable
    from linshark import estructuras as e

    BUENO = bytes.fromhex("010003c800ff00010201cd0000")
    SANGRADO = bytes.fromhex("01748b00000000000000000000")   # cmd 6 + relleno
    RATE = bytes.fromhex("01748b00000000")                   # el payload real

    if e.checksum_interno_cierra(p.CMD_LIGHTING, BUENO) is not True:
        fallos.append("el checksum del bloque bueno de cmd 5 no cierra")
    if e.checksum_interno_cierra(p.CMD_LIGHTING, SANGRADO) is not False:
        fallos.append("el sangrado de cmd 6 pasa el checksum de cmd 5")
    # Los que no tienen checksum interno dicen None, que no es lo mismo que
    # False: un False ahi seria una alarma inventada sobre un bloque sano.
    for cmd in (p.CMD_REPORT_RATE, p.CMD_PROFILE, p.CMD_VERSION):
        if e.checksum_interno_cierra(cmd, RATE) is not None:
            fallos.append(f"cmd {cmd} no tiene checksum interno y se lo juzga "
                          "igual")

    def report(cmd, datos):
        return bytes([cmd, len(datos) + 2]) + datos

    casos = [
        (report(p.CMD_LIGHTING, BUENO), None, "el bloque bueno"),
        (report(p.CMD_LIGHTING, SANGRADO), "checksum", "el sangrado de cmd 6"),
        (report(p.CMD_REPORT_RATE, RATE), "volvio el bloque", "el ajeno"),
    ]
    for rep, espera, que in casos:
        dicho = cable._por_que_no_sirve(p.CMD_LIGHTING, rep)
        if espera is None and dicho is not None:
            fallos.append(f"{que} fue rechazado: {dicho!r}")
        elif espera is not None and (dicho is None or espera not in dicho):
            fallos.append(f"{que} no fue rechazado como se esperaba: {dicho!r}")

    # **El macro queda afuera a proposito**: su checksum vuelve invertido del
    # mouse y su largo es variable, asi que esta cuenta lo daria por roto.
    macro = report(p.CMD_MACRO, bytes(109))
    if cable._por_que_no_sirve(p.CMD_MACRO, macro) is not None:
        fallos.append("cmd 9 se juzga con un checksum que no es el suyo")

    # --- y el tercer filtro: reconocer el bloque ANTERIOR ------------------
    # **MEDIDO** (`medir-sangrado.py`, 6 de 6 en 240 pedidos): cuando el mouse
    # sangra devuelve el bloque del pedido anterior. Reconocerlo es lo unico
    # que cubre a cmd 6, 10 y 11, que **no tienen checksum interno** y se
    # quedaban sin red. En `A_LEER` cmd 6 va justo antes de cmd 5, que es
    # exactamente el par del incidente.
    ant = (p.CMD_REPORT_RATE, RATE)
    casos = [
        (p.CMD_LIGHTING, report(p.CMD_LIGHTING, RATE + bytes(6)), True,
         "el sangrado del incidente, relleno con ceros"),
        (p.CMD_LIGHTING, report(p.CMD_LIGHTING, BUENO), False,
         "un bloque de luz bueno"),
        (p.CMD_VERSION, report(p.CMD_VERSION, RATE[:6]), True,
         "el sangrado truncado, en un bloque sin checksum"),
        (p.CMD_VERSION, report(p.CMD_VERSION, bytes.fromhex("080083010100")),
         False, "la version de verdad"),
        (p.CMD_PROFILE, report(p.CMD_PROFILE, RATE + bytes(119)), True,
         "el sangrado en el perfil, que tampoco tiene checksum"),
    ]
    for cmd, rep, espera, que in casos:
        dicho = cable._por_que_no_sirve(cmd, rep, ant)
        if espera and dicho is None:
            fallos.append(f"no reconocio {que}")
        elif not espera and dicho is not None:
            fallos.append(f"alarma falsa sobre {que}: {dicho!r}")

    # **Releer el mismo comando devuelve lo mismo, y eso esta bien.** Pasa en
    # cada relectura del paso 6; llamarlo sangrado seria la alarma falsa mas
    # cara que este filtro podria dar.
    if cable._por_que_no_sirve(p.CMD_REPORT_RATE,
                               report(p.CMD_REPORT_RATE, RATE), ant):
        fallos.append("releer el mismo bloque se toma por sangrado")

    # Y con poco en comun no se afirma: todos los bloques arrancan con el
    # mismo profileId.
    corto = (p.CMD_VERSION, b"\x01\x74")
    if cable._por_que_no_sirve(p.CMD_LIGHTING,
                               report(p.CMD_LIGHTING, BUENO), corto):
        fallos.append("con dos bytes en comun ya dice que es el anterior")


def test_el_instalador_apunta_a_archivos_que_existen(fallos: list[str]) -> None:
    """Todo lo que `install.sh` copia tiene que estar donde dice.

    **Paso de verdad** (2026-09-20). Al mover lo del X8 Pro a su carpeta por
    modelo, la regla de udev quedo en `driver/attackshark-x8pro/udev/` -hoy
    `driver/models/attackshark-x8pro/udev/`- y el instalador tenia **dos** caminos hacia ella: el de copiar, que se actualizo,
    y el de instalarla en `/etc/udev/rules.d`, que no. La instalacion de verdad
    murio a la mitad -con el programa ya copiado, sin regla y sin lanzadores- y
    `--solo-probar` habia salido limpio, porque la linea rota estaba adentro
    del `if` de instalar en serio.

    Un ensayo que no puede fallar por un archivo que no esta da confianza
    falsa. Esto lo mira **sin correr nada**, que es lo unico que se puede hacer
    en una tanda de tests: saca los `$DRIVER/...` y `$AQUI/...` del script y
    comprueba que existan.
    """
    import re

    instalar = Path(__file__).resolve().parent.parent / "instalar"
    script = instalar / "install.sh"
    fuente = script.read_text(encoding="utf-8")

    # Las variables del script, resueltas como las resuelve el
    # (`AQUI` es la carpeta del script y `DRIVER` su madre).
    donde = {"AQUI": instalar, "DRIVER": instalar.parent}
    # `$VAR/loquesea` hasta la comilla, saltando los que llevan otra variable
    # adentro -esos se arman en tiempo de corrida y no se pueden resolver aca-.
    patron = re.compile(r'"\$(AQUI|DRIVER)(/[^"$]*)"')
    vistos = set()
    for var, resto in patron.findall(fuente):
        ruta = donde[var] / resto.lstrip("/")
        vistos.add(ruta)
        if not ruta.exists():
            fallos.append(f"install.sh copia {var}{resto} y no existe: {ruta}")

    if len(vistos) < 4:
        fallos.append(f"solo encontre {len(vistos)} rutas en install.sh: el "
                      "patron dejo de reconocerlas y esto no verifica nada")

    # Y la regla de udev, que es la que se rompio: se arma con una variable
    # adentro (`$ORIGEN_REGLA` sale de `$REGLA`), asi que se comprueba aparte.
    regla = re.search(r'ORIGEN_REGLA="([^"]+)"', fuente)
    nombre = re.search(r'REGLA="([^"$]+\.rules)"', fuente)
    if not regla or not nombre:
        fallos.append("install.sh ya no dice de donde saca la regla de udev")
    else:
        ruta = Path(regla.group(1)
                    .replace("$DRIVER", str(donde["DRIVER"]))
                    .replace("$REGLA", nombre.group(1)))
        if not ruta.exists():
            fallos.append(f"la regla de udev que instala no existe: {ruta}")

    # Y el otro camino hacia la regla: `scripts/instalar-udev.sh`, que es el
    # que corre el boton de la ventana, **en el repo y ya instalado**. La busca
    # relativa a si mismo, asi que el instalador tiene que copiar `models/` con
    # la misma forma; si la copia en otro lado, el boton muere en /opt.
    udev = (instalar.parent / "scripts" / "instalar-udev.sh").read_text(encoding="utf-8")
    origen = re.search(r'^ORIGEN=.*?\)/(\.\./[^"]+)"', udev, re.M)
    if not origen or not nombre:
        fallos.append("instalar-udev.sh ya no dice de donde saca la regla")
    else:
        relativa = origen.group(1).replace("$REGLA", nombre.group(1))
        ruta = (instalar.parent / "scripts" / relativa).resolve()
        if not ruta.exists():
            fallos.append(f"instalar-udev.sh busca la regla en {ruta} y no esta")
        if 'cp -r "$DRIVER/models" "$PREFIJO/models"' not in fuente:
            fallos.append("install.sh no copia models/ con la forma del repo: "
                          "instalado, instalar-udev.sh no encuentra la regla")


#: Los README traducidos, por carpeta: el original en castellano y sus
#: traducciones. **El castellano es el original**: se escribe al lado del
#: codigo y de las mediciones, asi que es el que esta al dia. Cada traduccion
#: lleva en su primera linea `<!-- traduce: README.md sha256:... -->`, el hash
#: del original que tradujo.
#:
#: `dev/` no se traduce, a proposito: es procedimiento y evidencia, y una
#: traduccion atrasada ahi es alguien escribiendole al mouse con una Etapa 2
#: mal entendida. Quien aporta un modelo lee el original.
TRADUCCIONES_DEL_README = ("README.en.md", "README.zh-CN.md")
_MARCA_DE_TRADUCCION = r"<!-- traduce: (\S+) sha256:([0-9a-f]{64}) -->"


def test_las_traducciones_no_quedaron_atrasadas(fallos: list[str]) -> None:
    """Cada traduccion del README dice que version del castellano tradujo.

    No juzga el sentido -eso no lo puede hacer un test-: juzga que el original
    no haya cambiado desde que se tradujo. La marca es un hash del contenido y
    no un commit, para que el castellano y su traduccion puedan cambiar en el
    mismo commit y para que ande sin `.git`.

    El README de la raiz se mira solo si esto es el repositorio entero:
    `driver/` se distribuye y se prueba solo.
    """
    import hashlib
    import re

    driver = Path(__file__).resolve().parent.parent
    carpetas = [driver]
    if (driver.parent / "dev").is_dir() and (driver.parent / "README.md").is_file():
        carpetas.append(driver.parent)

    for carpeta in carpetas:
        original = carpeta / "README.md"
        if not original.is_file():
            fallos.append(f"no esta {original}")
            continue
        texto = original.read_text(encoding="utf-8")
        hash_actual = hashlib.sha256(original.read_bytes()).hexdigest()
        donde = original.relative_to(driver.parent)
        for nombre in TRADUCCIONES_DEL_README:
            traduccion = carpeta / nombre
            cual = traduccion.relative_to(driver.parent)
            if not traduccion.is_file():
                fallos.append(f"{donde} no tiene su traduccion {nombre}")
                continue
            if f"]({nombre})" not in texto:
                fallos.append(f"{donde} no enlaza a {nombre}: nadie la encuentra")
            primera = traduccion.read_text(encoding="utf-8").partition("\n")[0]
            marca = re.fullmatch(_MARCA_DE_TRADUCCION, primera.strip())
            if not marca:
                fallos.append(f"{cual} no dice en su primera linea que version "
                              "del castellano tradujo")
                continue
            if marca.group(1) != original.name:
                fallos.append(f"{cual} dice traducir {marca.group(1)}, y su "
                              f"original es {original.name}")
            if marca.group(2) != hash_actual:
                fallos.append(f"{cual} traduce una version vieja de {donde}: "
                              "actualizar la traduccion con lo que cambio, y "
                              f"despues su marca a sha256:{hash_actual}")

    # Y el instalador lleva las traducciones junto al manual: instalado, el
    # README de /opt/linshark es lo unico que hay para leer.
    instalar = (driver / "instalar" / "install.sh").read_text(encoding="utf-8")
    if 'for leeme in "$DRIVER"/README*.md' not in instalar:
        fallos.append("install.sh no copia las traducciones del manual")


async def test_el_estado_incoherente_no_pasa(fallos: list[str]) -> None:
    """Un estado que se contradice a si mismo no sirve de red ni de veredicto.

    El perfil completo (cmd 10) **no tiene checksum interno** y es el testigo
    de toda escritura por el camino de la relectura acotada, asi que una
    lectura suya corrompida no la notaba nadie. Lo unico que lo cubre es que
    **embebe a los otros bloques**: un estado trae dos copias de esos bytes y
    tienen que coincidir.

    Aca se prueba la baranda con estados armados a mano. Que la tabla de
    offsets diga la verdad se verifica contra los respaldos, que son evidencia
    y viven del otro lado de la frontera: `dev/tests/evidencia.py`.
    """
    from linshark import dispositivos as d
    from linshark import sesion

    perfil = d.perfil_de(p.DEVICE_X8_PRO)
    if not perfil.perfil_embebe:
        fallos.append("el perfil del X8 Pro no dice donde embebe a los bloques")
        return
    if p.CMD_LIGHTING not in perfil.perfil_embebe:
        fallos.append("la tabla no cubre cmd 5, que es donde paso")
        return

    # Un perfil coherente, armado desde los bloques: se le pega cada tramo
    # donde la tabla dice que va. Asi el estado sano no depende de ningun
    # respaldo, y la tabla se usa en el sentido contrario al que se verifica.
    LUZ = bytes.fromhex("010003c800ff00010201cd0000")
    largo = max(po + L for po, _, L in perfil.perfil_embebe.values())
    cuerpo = bytearray(largo)
    po, bo, L = perfil.perfil_embebe[p.CMD_LIGHTING]
    cuerpo[po:po + L] = LUZ[bo:bo + L]

    def estado(luz):
        return {"comandos": {
            str(p.CMD_LIGHTING): {"nombre": "iluminacion", "datos": luz.hex()},
            str(p.CMD_PROFILE): {"nombre": "perfil completo",
                                 "datos": bytes(cuerpo).hex()}}}

    if sesion.incoherencias(estado(LUZ)):
        fallos.append("un estado coherente sale como incoherente: la alarma "
                      "falsa gasta a las de verdad")

    # El sangrado de cmd 6, que es lo que de verdad llego el 2026-09-20.
    SANGRADO = bytes.fromhex("01748b00000000") + bytes(6)
    malas = sesion.incoherencias(estado(SANGRADO))
    if not malas:
        fallos.append("el sangrado de cmd 6 en el bloque de luz pasa como "
                      "coherente")
    elif "iluminacion" not in malas[0]:
        fallos.append(f"la incoherencia no dice que bloque es: {malas[0]!r}")

    # Y sin perfil no se inventa nada: un estado al que le falta el testigo no
    # es incoherente, es incompleto, y de eso se ocupa `incompletos()`.
    solo_luz = {"comandos": {str(p.CMD_LIGHTING): {"nombre": "iluminacion",
                                                   "datos": SANGRADO.hex()}}}
    if sesion.incoherencias(solo_luz):
        fallos.append("sin perfil completo igual dice que algo se contradice")


async def test_varios_campos_de_un_bloque_salen_juntos(fallos) -> None:
    """`preparar_mutaciones()` agrupa por comando, y eso es lo que destraba.

    **No es una optimizacion.** Los codificadores de un campo copian el resto
    del bloque que reciben, asi que un cmd 5 con la hibernacion Y la respuesta
    fuera de rango **no se puede arreglar campo por campo**: escribir la
    hibernacion arrastra la respuesta mala y `fuera_de_rango()` lo rechaza, y
    al reves igual. La ventana se quedaba sin salida -restaurar escribia de a
    uno- y habia que ir a `restaurar-bloque.py`.

    Encadenados, los dos cambios entran en el mismo bloque y el resultado ya
    esta en rango.
    """
    from linshark import estructuras as e
    from linshark import sesion

    PODRIDO = bytes.fromhex("01748b00000000010001000000")

    # 1. De a uno, ninguno de los dos puede: cada uno arrastra al otro.
    for clave, valor in (("hibernacion", 12), ("respuesta", 4)):
        sale = bytes(sesion.preparar_mutacion(clave, valor).codificar(PODRIDO))
        if e.fuera_de_rango(p.CMD_LIGHTING, sale) is None:
            fallos.append(f"escribir {clave} solo ya arregla el bloque: el "
                          "test perdio su objeto")

    # 2. Juntos, una sola escritura y el bloque sale en rango.
    ms = sesion.preparar_mutaciones([("hibernacion", 12), ("respuesta", 4)])
    if len(ms) != 1:
        fallos.append(f"dos campos de cmd 5 salieron en {len(ms)} escrituras")
        return
    sale = bytes(ms[0].codificar(PODRIDO))
    mal = e.fuera_de_rango(p.CMD_LIGHTING, sale)
    if mal is not None:
        fallos.append(f"los dos juntos siguen fuera de rango: {mal}")
    par = e.parametros_de_luz(sale)
    if par["hibernateTime"] != 12 or par["responseTimeUI"] != 4:
        fallos.append(f"el bloque encadenado no tiene los dos valores: {par}")

    # 3. Comandos distintos no se mezclan, y **el orden se respeta**: la tasa
    #    va ultima en la rafaga (ver `modelo.pendientes`), y agrupar no puede
    #    adelantarla.
    ms = sesion.preparar_mutaciones([("hibernacion", 12), ("lod", 2),
                                     ("respuesta", 4), ("tasa", 1000)])
    if [m.cmd for m in ms] != [p.CMD_LIGHTING, p.CMD_DPI, p.CMD_REPORT_RATE]:
        fallos.append(f"agrupar reordeno los comandos: {[m.cmd for m in ms]}")

    # 4. Y un solo campo sigue siendo la mutacion de siempre, sin envolver.
    una = sesion.preparar_mutaciones([("lod", 2)])
    if len(una) != 1 or una[0].clave != "lod":
        fallos.append(f"un campo solo salio como {[m.clave for m in una]}")


async def test_el_canario_de_version(fallos: list[str]) -> None:
    """Si cambia un bloque que no se puede escribir, el veredicto lo dice.

    La version de firmware no tiene comando de escritura, asi que dos lecturas
    suyas que difieran prueban que **una lectura vino mal**. Cuando paso de
    verdad (2026-09-20) el veredicto fue `cambio-de-mas`, que manda a buscar
    que otra cosa se escribio -y no se habia escrito nada: se habia leido mal-.

    Va antes que la rama idempotente, donde "no cambio nada" es el resultado
    bueno y una lectura podrida lo daria por malo sin decir por que.
    """
    from linshark import sesion

    def estado(version, luz):
        return {"comandos": {
            str(p.CMD_VERSION): {"nombre": "version de firmware",
                                 "datos": version, "checksum_ok": True},
            str(p.CMD_LIGHTING): {"nombre": "iluminacion", "datos": luz,
                                  "checksum_ok": True}}}

    SANA = "080083010100"
    PODRIDA = "08740b010100"        # la del incidente
    LUZ_A = "010003c800ff00010201cd0000"
    LUZ_B = "010003c800ff00020201ce0000"

    # 1. Con la version movida no se juzga la escritura, se denuncia la lectura.
    v = sesion.juzgar(estado(SANA, LUZ_A), estado(PODRIDA, LUZ_B),
                      cmd=p.CMD_LIGHTING, idempotente=False)
    if v.ok or v.motivo != "lectura-corrompida":
        fallos.append(f"con la version movida el veredicto fue {v.motivo!r}")
    if p.CMD_VERSION not in v.inesperados:
        fallos.append("el veredicto no nombra el bloque que no puede cambiar")

    # 2. Y tambien en la rama idempotente, que devuelve antes que todo lo demas.
    v = sesion.juzgar(estado(SANA, LUZ_A), estado(PODRIDA, LUZ_A),
                      cmd=p.CMD_LIGHTING, idempotente=True)
    if v.motivo != "lectura-corrompida":
        fallos.append(f"idempotente con la version movida dio {v.motivo!r}")

    # 3. Sin tocar la version, los veredictos de siempre no se mueven.
    v = sesion.juzgar(estado(SANA, LUZ_A), estado(SANA, LUZ_B),
                      cmd=p.CMD_LIGHTING, idempotente=False)
    if v.motivo != "cambio-lo-pedido":
        fallos.append(f"un cambio normal ahora da {v.motivo!r}")
    v = sesion.juzgar(estado(SANA, LUZ_A), estado(SANA, LUZ_A),
                      cmd=p.CMD_LIGHTING, idempotente=True)
    if v.motivo != "sin-diferencias":
        fallos.append(f"un idempotente normal ahora da {v.motivo!r}")


async def test_la_tasa_insiste_y_no_escribe_de_gusto(fallos: list[str]) -> None:
    """`poner_tasa()` reintenta, y no manda una trama si la tasa ya esta puesta.

    Las dos mitades salen de cosas MEDIDAS:

      * el dongle acusa `0xC1` sin que el mouse aplique nada -dos veces
        seguidas, a 2000 Hz-, asi que una sola trama no alcanza y lo unico que
        decide es la relectura. Antes esto mandaba una y se
        rendia, y como el paso 0 de la Etapa 3 baja la tasa para poder
        respaldar, **una perdida de radio dejaba el campo sin poder
        escribirse**;
      * y cada trama de rate que llega reconfigura la radio: la pagina oficial
        mando seis en tres segundos y el mouse dejo de mover el puntero hasta
        que se lo saco del modo dongle. Escribir la tasa que ya esta puesta es
        pagar ese riesgo a cambio de nada.
    """
    from linshark import estructuras as e
    from linshark import sesion

    # 1. ya esta puesta: no se manda nada
    mouse = _MouseRapido(hz=1000)
    quedo = await sesion.poner_tasa(mouse, 1000)
    if quedo != 1000:
        fallos.append(f"poner_tasa a la tasa que ya estaba dio {quedo}")
    if mouse.escrituras_de_rate:
        fallos.append("reconfiguro la radio para dejar la tasa como estaba")

    # 2. se pierde la primera: la segunda entra
    mouse = _MouseRapido(hz=8000, perdida_de_rate=1)
    quedo = await sesion.poner_tasa(mouse, 1000)
    if quedo != 1000:
        fallos.append(f"con una trama perdida no llego a bajar: quedo {quedo}")
    if mouse.escrituras_de_rate != 2:
        fallos.append(f"mando {mouse.escrituras_de_rate} tramas de rate, no 2")

    # 3. no insiste de mas: con el enlace sano, UNA sola trama
    mouse = _MouseRapido(hz=8000)
    await sesion.poner_tasa(mouse, 1000)
    if mouse.escrituras_de_rate != 1:
        fallos.append(f"con el enlace sano mando {mouse.escrituras_de_rate} "
                      "tramas: cada una reconfigura la radio")

    # 4. y si no entra nunca, lo dice en vez de mentir
    mouse = _MouseRapido(hz=8000, perdida_de_rate=99)
    quedo = await sesion.poner_tasa(mouse, 1000)
    if quedo == 1000:
        fallos.append("dijo que la tasa entro y el mouse sigue en 8000")
    if e.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE]) != 8000:
        fallos.append("el mouse falso aplico una trama que se perdio")


async def test_configurar_baja_la_tasa_una_vez(fallos: list[str]) -> None:
    """La sesion baja la tasa **una vez** y lee el mouse **una vez**.

    Es el arreglo, y las dos mitades importan por motivos
    distintos:

      * **las escrituras de rate**, porque cada una reconfigura la radio y seis
        seguidas dejaron el mouse sin mover el puntero (MEDIDO).
        Tres cambios costaban seis; tienen que costar una;
      * **las lecturas completas**, porque leer el mouse entero tarda minutos y
        la ventana se bloquea mientras escribe. Tres cambios costaban seis
        lecturas completas; tienen que costar una.
    """
    from linshark import estructuras as e
    from linshark import sesion

    async def si(bloque, trama):
        return True

    mouse = _MouseRapido(hz=8000)
    config = sesion.Configuracion(mouse)
    for _ in range(3):
        r = await config.escribir(cmd=p.CMD_DPI,
                                  codificar=lambda leido: leido, confirmar=si)
        if not r.ok:
            fallos.append(f"una escritura de la rafaga dio {r.motivo!r}")
            break

    if mouse.escrituras_de_rate != 1:
        fallos.append(f"tres cambios costaron {mouse.escrituras_de_rate} "
                      "escrituras de rate: tenian que costar 1")
    completas = mouse.pedidos.count(p.CMD_VERSION)
    if completas != 1:
        fallos.append(f"tres cambios costaron {completas} lecturas completas "
                      "del mouse: tenian que costar 1")
    if config.tasa_prestada != 8000:
        fallos.append(f"no anoto que debe 8000 Hz: {config.tasa_prestada}")
    if (e.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE])
            != sesion.RATE_MAXIMO_PARA_LEER):
        fallos.append("no dejo el mouse donde se puede leer entero")

    # y soltar la devuelve, una sola vez
    quedo = await config.soltar()
    if quedo != 8000:
        fallos.append(f"soltar dejo la tasa en {quedo}, no en 8000")
    if mouse.escrituras_de_rate != 2:
        fallos.append(f"soltar gasto de mas: {mouse.escrituras_de_rate} "
                      "escrituras de rate en total")
    if await config.soltar() is not None:
        fallos.append("soltar dos veces mando otra trama de rate")

    # **Y volver a pedirla prestada no cuesta una lectura completa.** Pasa cada
    # vez que la gracia de la ventana se vence mientras alguien mira la
    # pantalla: si ahi se tirara el cache entero, el click siguiente costaria
    # los minutos que este arreglo vino a sacar. Lo unico que cambio es la
    # tasa, asi que se refrescan cmd 6 y el perfil, que la embebe.
    completas = mouse.pedidos.count(p.CMD_VERSION)
    r = await config.escribir(cmd=p.CMD_DPI, codificar=lambda leido: leido,
                              confirmar=si)
    if not r.ok:
        fallos.append(f"al retomar la tasa prestada dio {r.motivo!r}")
    if mouse.pedidos.count(p.CMD_VERSION) != completas:
        fallos.append("retomar la tasa prestada releyo el mouse entero: se "
                      "tiro el cache por el unico bloque que habia cambiado")
    await config.soltar()


async def test_volver_a_como_estaba_con_la_tasa_prestada(fallos: list[str]) -> None:
    """"Como estaba" es la tasa de su dueño, no la prestada.

    **Paso**: con el mouse abierto a 8000 Hz, la sesion baja la tasa a 1000
    para poder leerlo, y "volver a como estaba" tomaba ese 1000 por la tasa del
    mouse. Si en la sesion se ponia 4000, volver escribia **1000**. Y "valores
    seguros" no pedia nada con la tasa prestada -1000 contra 1000-, asi que al
    cerrar la ventana el mouse volvia a 8000 en vez de quedar en los seguros.

    Cinco caminos, con el mouse que respeta lo medido a tasas altas.
    """
    from linshark import modelo
    from linshark import sesion

    async def si(bloque, trama):
        return True

    async def abrir():
        mouse = _MouseRapido(hz=8000)
        config = sesion.Configuracion(mouse)
        prep = await config.preparar()
        return mouse, config, modelo.como_esta(prep.antes)

    async def poner(config, hz):
        m = sesion.preparar_mutacion("tasa", hz)
        return await config.escribir(cmd=m.cmd, codificar=m.codificar,
                                     confirmar=si)

    def volver(config, al_abrir):
        if config.estado is None:
            return "la cache quedo vacia"
        return modelo.pendientes(config.estado, al_abrir)

    # 1. Al abrir, la tasa es la del dueño, y con la prestada no hay nada que
    #    volver: se devuelve sola al cerrar.
    mouse, config, al_abrir = await abrir()
    if al_abrir.get("tasa") != 8000:
        fallos.append(f"'como estaba' tomo la prestada: {al_abrir.get('tasa')}")
    if volver(config, al_abrir):
        fallos.append(f"sin tocar nada, volver pide {volver(config, al_abrir)}")

    # 2. El caso del bug: 4000 en la sesion, y volver lleva a 8000.
    mouse, config, al_abrir = await abrir()
    r = await poner(config, 4000)
    if not r.ok:
        fallos.append(f"poner 4000 dio {r.motivo!r}")
    elif volver(config, al_abrir) != [("tasa", 4000, 8000)]:
        fallos.append(f"despues de poner 4000, volver pide "
                      f"{volver(config, al_abrir)}")
    else:
        r = await poner(config, 8000)
        if not r.ok or mouse.hz != 8000:
            fallos.append(f"volver no dejo el mouse en 8000: {r.motivo!r}, "
                          f"{mouse.hz} Hz")
        # Y la cache sigue sirviendo: el campo que sigue se escribe.
        r = await config.escribir(cmd=p.CMD_DPI, codificar=lambda d: d,
                                  confirmar=si)
        if not r.ok:
            fallos.append(f"despues de volver, el dpi dio {r.motivo!r}")

    # 3. La tasa ya se devolvio: el bloque en memoria dice 1000 y el mouse esta
    #    en 8000. Volver no reescribe nada.
    mouse, config, al_abrir = await abrir()
    await config.soltar()
    escritas = mouse.escrituras_de_rate
    if volver(config, al_abrir):
        fallos.append(f"con la tasa ya devuelta, volver pide "
                      f"{volver(config, al_abrir)}")
    if mouse.escrituras_de_rate != escritas:
        fallos.append("mirar que falta escribio una tasa")

    # 4. Quedarse con la prestada: ahora si esta en 1000, y volver lo sabe.
    mouse, config, al_abrir = await abrir()
    config.quedarse_con_la_tasa()
    if volver(config, al_abrir) != [("tasa", 1000, 8000)]:
        fallos.append(f"quedandose con 1000, volver pide "
                      f"{volver(config, al_abrir)}")

    # 5. Valores seguros con la tasa prestada: la tasa se pide, y se cumple
    #    cancelando la deuda, sin una sola trama de rate.
    mouse, config, _ = await abrir()
    tasa = [c for c in modelo.pendientes(config.estado, modelo.SEGUROS)
            if c[0] == "tasa"]
    if tasa != [("tasa", 8000, modelo.TASA_SEGURA)]:
        fallos.append(f"valores seguros no pide la tasa: {tasa}")
    escritas = mouse.escrituras_de_rate
    await poner(config, modelo.TASA_SEGURA)
    if mouse.escrituras_de_rate != escritas:
        fallos.append("para quedarse en 1000 reconfiguro la radio")
    if config.tasa_prestada is not None:
        fallos.append(f"sigue debiendo {config.tasa_prestada} Hz: al cerrar "
                      "desharia los valores seguros")


async def test_a_tasa_alta_la_ventana_puede_escribir(fallos: list[str]) -> None:
    """**El bug reportado**: con el mouse a 2000, 4000 u 8000 Hz no se podia
    cambiar ningun parametro.

    Contra un mouse falso que respeta lo medido -a esas tasas los bloques
    largos no llegan-, la sesion tiene que poder escribir igual, y devolver la
    tasa al terminar. Se prueba con las tres porque el usuario las nombro a las
    tres, y porque la frontera MEDIDA es 1000: 2000 ya falla.
    """
    from linshark import estructuras as e
    from linshark import sesion

    async def si(bloque, trama):
        return True

    for hz in (2000, 4000, 8000):
        mouse = _MouseRapido(hz=hz)
        config = sesion.Configuracion(mouse)
        r = await config.escribir(
            cmd=p.CMD_DPI,
            codificar=lambda leido: bytes(e.escribir_nivel_dpi(leido, 1, 1600)[0]),
            confirmar=si)
        if not r.ok:
            fallos.append(f"a {hz} Hz no se pudo escribir el dpi: {r.motivo!r}")
            continue
        await config.soltar()
        quedo = e.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE])
        if quedo != hz:
            fallos.append(f"a {hz} Hz la tasa quedo en {quedo} al terminar")

    # Y el control negativo: **sin la sesion** -una Etapa 3 aislada, que es lo
    # que hacia la ventana hasta- con una sola perdida de radio
    # el campo no se puede escribir. Si esto deja de fallar, la prueba de
    # arriba dejo de medir lo que dice medir.
    mouse = _MouseRapido(hz=8000, perdida_de_rate=99)
    r = await sesion.aplicar(mouse, cmd=p.CMD_DPI,
                             codificar=lambda leido: leido, confirmar=si,
                             bajar_la_tasa=True)
    if r.ok:
        fallos.append("el control negativo no fallo: con la radio perdiendo "
                      "todas las tramas de rate no se puede bajar la tasa, y "
                      "sin bajarla no hay respaldo")


async def test_la_relectura_acotada_no_afirma_de_mas(fallos: list[str]) -> None:
    """Releer poco esta bien; **decir que se releyo todo, no**.

    La relectura acotada mira el bloque escrito y el perfil completo. Con eso
    alcanza para las dos preguntas del paso 6 en el caso bueno, pero **no**
    alcanza para afirmar "y nada mas" cuando algo se movio: el perfil se movio
    tambien, porque acompaña a todo cambio, y entonces ya no distingue. Ahi el
    veredicto tiene que decir que no miro.
    """
    from linshark import estructuras as e
    from linshark import sesion

    async def si(bloque, trama):
        return True

    # 1. un cambio real: ok, pero con la advertencia y con los comandos que no
    #    se miraron nombrados
    mouse = _MouseFalso()
    config = sesion.Configuracion(mouse)
    r = await config.escribir(
        cmd=p.CMD_DPI,
        codificar=lambda leido: bytes(e.escribir_nivel_dpi(leido, 1, 1600)[0]),
        confirmar=si)
    if not r.ok or r.veredicto is None:
        fallos.append(f"el cambio real dio {r.motivo!r}")
    else:
        if not r.veredicto.no_releidos:
            fallos.append("la relectura acotada no dijo que no habia mirado "
                          "todo")
        if p.CMD_DPI in r.veredicto.no_releidos:
            fallos.append("dijo que no releyo el comando que si releyo")
        if p.CMD_PROFILE in r.veredicto.no_releidos:
            fallos.append("dijo que no releyo el perfil, que es el testigo")
        if "no se releyeron" not in r.veredicto.explicacion:
            fallos.append("la explicacion no nombra lo que no se miro: "
                          f"{r.veredicto.explicacion!r}")
        if r.despues.get(sesion.CLAVE_ACOTADA) is None:
            fallos.append("el estado no queda marcado como relectura acotada, "
                          "asi que se podria guardar como si fuera completo")

    # 2. una escritura idempotente: nada se movio, y el perfil es testigo de
    #    eso. Ahi la advertencia **no** corresponde y no tiene que aparecer.
    mouse = _MouseFalso()
    config = sesion.Configuracion(mouse)
    r = await config.escribir(cmd=p.CMD_DPI, codificar=lambda leido: leido,
                              confirmar=si)
    if r.motivo != "sin-diferencias":
        fallos.append(f"la idempotente dio {r.motivo!r}")
    elif "no se releyeron" in r.veredicto.explicacion:
        fallos.append("aviso de que no miro todo en un caso donde el perfil "
                      "alcanza como testigo: una alarma que sobra gasta a las "
                      "que importan")

    # 3. la relectura completa sigue siendo la de siempre, y no advierte nada
    mouse = _MouseFalso()
    r = await sesion.aplicar(mouse, cmd=p.CMD_DPI,
                             codificar=lambda leido: leido, confirmar=si)
    if r.veredicto is None or r.veredicto.no_releidos:
        fallos.append("la relectura completa dijo que no habia mirado algo")


async def test_una_tasa_ilegible_no_deja_al_programa_afuera(
        fallos: list[str]) -> None:
    """Un byte de tasa que no se entiende se arregla, y el mouse se lee igual.

    **Es una regresion con los bytes de verdad.** El 2026-10-04 el mouse
    devolvio `01 02 fd 00 00 00 00` para cmd 6 -nibble alto 0, que no es
    ninguno de los siete indices- al primer intento, reportando a 8000 Hz. La
    ventana dijo "el mouse no contesto la lectura del comando que se iba a
    escribir" -ni habia una escritura, ni el mouse se habia callado- y no leyo
    nada: la unica salida fue `cambiar-rate.py` a mano.
    """
    from linshark import estructuras as e
    from linshark import sesion

    raro = bytes.fromhex("0102fd00000000")
    pausa, p.WRITE_BLOCK_PAUSE_SOFT = p.WRITE_BLOCK_PAUSE_SOFT, 0
    try:
        # 1. se arregla con la trama del driver oficial, una sola, y se lee
        avisos = []
        mouse = _MouseFalso()
        mouse.bloques[p.CMD_REPORT_RATE] = raro
        config = sesion.Configuracion(mouse, al_avisar=avisos.append)
        r = await config.preparar()
        if not r.ok:
            fallos.append(f"con el byte de tasa 0x02 no leyo: {r.motivo!r}")
        tramas = [p.build_write_frame(b).hex() for b in mouse.escrituras]
        if tramas != [RATE_OFICIAL]:
            fallos.append("el arreglo no es la escritura de rate del driver "
                          f"oficial, una vez: {tramas}")
        if r.ok and sesion.tasa_de(r.antes) != 1000:
            fallos.append(f"quedo en {sesion.tasa_de(r.antes)} Hz, no en 1000")
        if r.ok and r.antes.get(sesion.CLAVE_TASA_ARREGLADA) != raro.hex():
            fallos.append("el estado no guarda el bloque que habia: es el "
                          "unico respaldo de lo que se piso")
        if config.tasa_prestada is not None or r.tasa_bajada_desde is not None:
            fallos.append("anoto una tasa para devolver, y no hay ninguna")
        if not any(a.startswith(sesion.AVISO_TASA_ARREGLADA) and "0x02" in a
                   for a in avisos):
            fallos.append(f"cambio la tasa sin decirlo: {avisos}")

        # 2. sin el permiso entero no toca nada
        mouse = _MouseFalso()
        mouse.bloques[p.CMD_REPORT_RATE] = raro
        r = await sesion.Configuracion(mouse).preparar(permiso=False)
        if r.ok or r.motivo != "tasa-ilegible" or mouse.escrituras:
            fallos.append(f"sin permiso dio {r.motivo!r} y escribio "
                          f"{len(mouse.escrituras)}")
        if mouse.pedidos != [p.CMD_REPORT_RATE]:
            fallos.append("siguio leyendo sin saber a que tasa esta el mouse: "
                          f"{mouse.pedidos}")

        # 3. una lectura que vino mal no es un byte raro: no se le escribe
        #    encima. Es el sangrado del cable, con sus bytes.
        mouse = _MouseFalso()
        mouse.bloques[p.CMD_REPORT_RATE] = bytes.fromhex("01008301010000")
        r = await sesion.Configuracion(mouse).preparar()
        if r.ok or r.motivo != "tasa-ilegible" or mouse.escrituras:
            fallos.append(f"con el bloque sangrado dio {r.motivo!r} y "
                          f"escribio {len(mouse.escrituras)}")

        # 4. y un mouse mudo es otra cosa, con otro mensaje
        mouse = _MouseFalso(mudo_tras=0)
        r = await sesion.Configuracion(mouse).preparar()
        if r.ok or r.motivo != "sin-tasa":
            fallos.append(f"con el mouse mudo dio {r.motivo!r}")
    finally:
        p.WRITE_BLOCK_PAUSE_SOFT = pausa

    # 5. el arreglo no inventa bytes: de cualquiera de los 256 sale uno que el
    #    driver oficial escribio, legible en 1000 Hz por su camino, y por cable
    #    la tasa de la radio se conserva si era un indice.
    for byte in range(256):
        bloque = bytes([1, byte, 0xFF ^ byte, 0, 0, 0, 0])
        for por_cable, leer in ((False, e.report_rate_de),
                                (True, e.report_rate_por_cable_de)):
            salida = e.arreglar_report_rate(bloque, por_cable=por_cable)
            if not e.rate_byte_en_el_bus(salida[1]):
                fallos.append(f"de {byte:#04x} sale {salida[1]:#04x}, que "
                              "ninguna captura muestra")
            if leer(salida) != 1000 or not e.report_rate_coherente(salida):
                fallos.append(f"de {byte:#04x} sale {salida.hex()}, que no "
                              "son 1000 Hz bien formados")
    if e.arreglar_report_rate(bytes.fromhex("01708f00000000"),
                              por_cable=True)[1] != 0x74:
        fallos.append("por cable piso la tasa de la radio, que se entendia")


async def test_el_camino_de_escritura_lo_elige_el_tamano(fallos) -> None:
    from linshark import sesion

    espia = _DispositivoEspia()
    # cmd 6: 9 bytes de bloque, entra en un report de 64
    corto = bytes([p.CMD_REPORT_RATE, 9]) + bytes.fromhex("0144bb00000000")
    await sesion.escribir_bloque(espia, corto)
    if espia.escrituras != [corto] or espia.por_bloques:
        fallos.append(f"un bloque que entra en un report se mando por bloques: "
                      f"{espia.escrituras}, {espia.por_bloques}")

    # cmd 9: 111 bytes, no entra
    espia = _DispositivoEspia()
    largo = bytes([p.CMD_MACRO, 111]) + bytes(109)
    await sesion.escribir_bloque(espia, largo)
    if espia.por_bloques != [largo] or espia.escrituras:
        fallos.append(f"un bloque que no entra en un report se mando de una: "
                      f"{espia.escrituras}, {espia.por_bloques}")

    # Y la frontera es la del protocolo, no un `if cmd == 9`: un bloque de
    # cualquier comando que pase de 59 bytes utiles va por bloques.
    espia = _DispositivoEspia()
    justo = bytes([p.CMD_BUTTONS, 60]) + bytes(58)
    await sesion.escribir_bloque(espia, justo)
    esperado_por_bloques = len(justo) + p.WRITE_FRAME_OVERHEAD > p.WRITE_REPORT_LEN
    fue_por_bloques = bool(espia.por_bloques)
    if fue_por_bloques != esperado_por_bloques:
        fallos.append(f"la frontera no es la del protocolo: bloque de "
                      f"{len(justo)} B fue por bloques={fue_por_bloques}")


async def test_el_puente_pide_el_macro_correcto(fallos: list[str]) -> None:
    backend = HidrawBackend(mode=Mode.READ)
    espia = _DispositivoEspia()
    backend.device = espia

    async def emit(msg):
        pass

    # La pagina pide el macro 17: `[0xF0, conn, dev, cmd, sub]`, con el id
    # en `sub` (sendMacroDataCommand(macroId) del bundle).
    await backend.handle(p.Request([0xF0, 0x83, 8, p.CMD_MACRO, 17]), emit)
    if (p.CMD_MACRO, 17) not in espia.lecturas:
        fallos.append(f"pidio {espia.lecturas}, esperaba el macro 17: sin el "
                      "id, cmd 9 devuelve siempre el macro 1")

    # Y los demas comandos NO llevan macro_id: ahi el byte 5 es el perfil.
    espia.lecturas.clear()
    await backend.handle(p.Request([0xF0, 0x83, 8, p.CMD_DPI, 0]), emit)
    if espia.lecturas != [(p.CMD_DPI, None)]:
        fallos.append(f"le paso un macro_id a un comando que no es cmd 9: "
                      f"{espia.lecturas}")


async def test_las_escrituras_no_se_encinan(fallos: list[str]) -> None:
    import time
    from linshark import backend as mod_backend

    previo = mod_backend.PAUSA_ENTRE_ESCRITURAS
    mod_backend.PAUSA_ENTRE_ESCRITURAS = 0.15      # el test no espera 1 s
    try:
        backend = HidrawBackend(mode=Mode.FULL,
                                permitir_escritura=[p.CMD_REPORT_RATE])
        backend.simulacro = False                  # ya se pidio --sin-simulacro
        backend._confirmado = True                 # y ya se confirmo antes
        espia = _DispositivoEspia()
        backend.device = espia

        async def emit(msg):
            pass

        t0 = time.monotonic()
        for _ in range(3):
            await backend.handle(_escritura_de_rate(), emit)
        tardo = time.monotonic() - t0

        if len(espia.escrituras) != 3:
            fallos.append(f"mando {len(espia.escrituras)} escrituras de 3")
        minimo = 2 * mod_backend.PAUSA_ENTRE_ESCRITURAS
        if tardo < minimo * 0.9:
            fallos.append(
                f"tres escrituras seguidas tardaron {tardo:.2f} s; con la "
                f"pausa de {mod_backend.PAUSA_ENTRE_ESCRITURAS:.2f} s entre "
                f"una y otra tendrian que tardar al menos {minimo:.2f} s. "
                "Sin espaciado, una rafaga de la pagina le cuelga el stream "
                "de movimiento al mouse")
    finally:
        mod_backend.PAUSA_ENTRE_ESCRITURAS = previo


async def test_camino_de_escritura(fallos: list[str]) -> None:
    req = _escritura_de_rate()
    if req.cmd != p.CMD_REPORT_RATE:
        fallos.append(f"la trama de prueba no es rate: cmd={req.cmd}")
        return

    # 1. listen y read no escriben, aunque les llegue una trama valida.
    for modo in (Mode.LISTEN, Mode.READ):
        b = HidrawBackend(mode=modo)
        esc, _ = await _correr_handle(b, req)
        if esc:
            fallos.append(f"modo {modo} dejo pasar una escritura")

    # 2. full en simulacro (el default) arma la trama pero no la manda.
    b = HidrawBackend(mode=Mode.FULL, permitir_escritura=[p.CMD_REPORT_RATE])
    esc, _ = await _correr_handle(b, req)
    if esc:
        fallos.append("el simulacro mando la escritura igual")

    # 3. full sin simulacro, pero pidiendo un comando que no es el permitido.
    b = HidrawBackend(mode=Mode.FULL, permitir_escritura=[p.CMD_DPI],
                      simulacro=False, confirmar=_confirmar_si)
    esc, _ = await _correr_handle(b, req)
    if esc:
        fallos.append("escribio rate teniendo permitido solo dpi")

    # 4. bateria por debajo del umbral.
    b = HidrawBackend(mode=Mode.FULL, permitir_escritura=[p.CMD_REPORT_RATE],
                      simulacro=False, battery_level=20,
                      confirmar=_confirmar_si)
    esc, _ = await _correr_handle(b, req)
    if esc:
        fallos.append("escribio con la bateria al 20%")

    # 5. sin forma de confirmar, no se escribe.
    b = HidrawBackend(mode=Mode.FULL, permitir_escritura=[p.CMD_REPORT_RATE],
                      simulacro=False, confirmar=None)
    esc, _ = await _correr_handle(b, req)
    if esc:
        fallos.append("escribio sin poder pedir confirmacion")

    # 6. si el usuario dice que no, no se escribe.
    b = HidrawBackend(mode=Mode.FULL, permitir_escritura=[p.CMD_REPORT_RATE],
                      simulacro=False, confirmar=_confirmar_no)
    esc, _ = await _correr_handle(b, req)
    if esc:
        fallos.append("escribio despues de que el usuario dijera que no")

    # 7. y con todo en su lugar, SI escribe: una baranda que nunca deja pasar
    #    nada no se distingue de una rota.
    b = HidrawBackend(mode=Mode.FULL, permitir_escritura=[p.CMD_REPORT_RATE],
                      simulacro=False, confirmar=_confirmar_si)
    esc, acks = await _correr_handle(b, req)
    if len(esc) != 1:
        fallos.append(f"con todo habilitado escribio {len(esc)} veces, "
                      "esperaba 1")
    elif esc[0][0] != p.CMD_REPORT_RATE:
        fallos.append(f"escribio el comando {esc[0][0]}, esperaba rate")


async def _confirmar_si(nombre, hexa):
    return True


async def _confirmar_no(nombre, hexa):
    return False


# --- El byte de report rate: nibble ALTO ------------------------------------
# Barrida anotada (dev/models/attackshark-x8pro/docs/capturas-w/soft-rates-anotados.txt): el
# operador puso 125, 250, 500, 1000, 2000, 4000 y 8000 en ese orden, y el soft
# escribio estos bytes. Si esto se rompe, la pagina muestra la frecuencia
# equivocada y el puente escribe la que no es.

RATES_MEDIDOS = [(0x14, 125), (0x24, 250), (0x34, 500), (0x44, 1000),
                 (0x54, 2000), (0x64, 4000), (0x74, 8000)]


# --- cmd 6: las siete tasas, contra las catorce escrituras del bus ---------
#
# `soft-rates-anotados.pcap` tiene la barrida entera del soft nativo -125, 250,
# 500, 1000, 2000, 4000 y 8000, en ese orden- y `web-todo.pcap` la de la
# pagina. Difieren en el nibble bajo: el soft lo deja en 4 y la web escribe los
# dos nibbles iguales. Nuestro codificador tiene que reproducir **las dos
# familias**, porque respeta el nibble bajo que venga en el bloque leido.
RATE_SOFT = [   # (hz, payload que escribio el soft nativo)
    (125,  "0114eb00000000"), (250,  "0124db00000000"),
    (500,  "0134cb00000000"), (1000, "0144bb00000000"),
    (2000, "0154ab00000000"), (4000, "01649b00000000"),
    (8000, "01748b00000000"),
]
RATE_WEB = [
    (125,  "0111ee00000000"), (250,  "0122dd00000000"),
    (500,  "0133cc00000000"), (1000, "0144bb00000000"),
    (2000, "0155aa00000000"), (4000, "01669900000000"),
    (8000, "01778800000000"),
]


# --- el doble empaquetado, que costo una tarde entera ----------------------
#
# `driver/scripts/cambiar-rate.py` armaba la trama para mostrarla y despues se la
# pasaba a `device.escribir()`, que vuelve a empaquetarla. El mouse recibia
# cmd 0x04 (dpi) con un tamaño imposible y lo descartaba; **el dongle acusaba
# `0xC1` igual**, asi que parecian veinte escrituras exitosas sin un byte
# cambiado. Encima la validacion vieja no lo agarraba: una trama de 14 bytes
# declara `bloque[1] = 0x0e = 14` y mide 14, coincide por casualidad.
#
# Lo agarro una revision externa mirando el codigo, no las corridas: veinte
# corridas contra el hardware dieron todas el mismo sintoma y ninguna lo
# separo de "el mouse no aplica cambios a esta tasa".

def test_no_se_empaqueta_dos_veces(fallos: list[str]) -> None:
    # Las tramas de escritura de cada comando, armadas bien una vez.
    for cmd, sub, datos in ((p.CMD_REPORT_RATE, 9, "0144bb00000000"),
                            (p.CMD_DPI, 56, DPI_REAL.hex()),
                            (p.CMD_LIGHTING, 15, LUZ_REAL.hex())):
        bloque = bytes([cmd, sub]) + bytes.fromhex(datos)
        try:
            trama = p.build_write_frame(bloque)
        except ValueError as exc:
            fallos.append(f"rechazo un bloque legitimo de cmd {cmd}: {exc}")
            continue
        # y volver a empaquetarla tiene que ser un error, no una trama nueva
        try:
            otra = p.build_write_frame(trama)
        except ValueError as exc:
            if "trama armada" not in str(exc):
                fallos.append(f"cmd {cmd}: rechaza el doble empaquetado con un "
                              f"mensaje que no lo explica: {exc}")
        else:
            fallos.append(
                f"cmd {cmd}: empaqueto la trama dos veces sin protestar. "
                f"El mouse leeria cmd {otra[3]:#04x} en vez de {cmd:#04x}")

    # Y el script que tuvo el bug: la trama que manda tiene que ser la de
    # `build_write_frame(bloque)`, no una envuelta dos veces.
    scripts = Path(__file__).resolve().parent.parent / "scripts"
    if "device.escribir(trama)" in (scripts / "cambiar-rate.py").read_text():
        fallos.append("cambiar-rate.py volvio a pasarle la trama a "
                      "device.escribir(); espera el bloque")

    # **Y el criterio del paso 6 no vuelve a la terminal.** Vivia adentro de
    # `primera-escritura.py` mezclado con sus `print`, que es el unico lugar
    # donde no le sirve a la aplicacion. Si alguien lo reimplementa ahi, la
    # biblioteca y el script pueden opinar distinto sobre si una escritura
    # salio bien, que es lo peor que puede pasar en el paso que es la red.
    cli = (scripts / "primera-escritura.py").read_text()
    for reimplementado in ("cmds_que_cambiaron(antes, despues)",
                           "cambiados - {cmd,"):
        if reimplementado in cli:
            fallos.append(f"primera-escritura.py volvio a calcular el "
                          f"veredicto por su cuenta ({reimplementado!r}); "
                          "eso es sesion.juzgar()")


def test_escribir_report_rate(fallos: list[str]) -> None:
    from linshark import estructuras as e

    # 1. La familia del SOFT, que es la que tiene este mouse (nibble bajo 4):
    #    partiendo de cada tasa, pedir cada otra da la trama que el soft
    #    escribio. 49 combinaciones.
    soft = [(hz, bytes.fromhex(h)) for hz, h in RATE_SOFT]
    for _, desde in soft:
        for hz, esperado in soft:
            obtenido = e.escribir_report_rate(desde, hz=hz)
            if obtenido != esperado:
                fallos.append(f"de {desde.hex()} a {hz} Hz dio "
                              f"{obtenido.hex()}, el bus dice {esperado.hex()}")
                break

    # 2. La familia de la WEB no se reproduce, y esta bien que no: la pagina
    #    **iguala** el nibble bajo al alto y nosotros lo **respetamos**. Con un
    #    bloque suyo, pedir otra tasa deja el nibble bajo donde estaba.
    #    Reproducir a la web exigiria pisar un campo que no entendemos.
    de_la_web = bytes.fromhex("0177880000000000"[:14])
    salida = e.escribir_report_rate(de_la_web, hz=1000)
    if salida[1] & 0x0F != 0x7:
        fallos.append(f"piso el nibble bajo de la web: {salida.hex()}")
    if e.report_rate_de(salida) != 1000:
        fallos.append(f"la relectura de {salida.hex()} no da 1000 Hz")

    # 3. Y las dos familias se leen igual, que es lo que importa del nibble
    #    alto.
    for tabla in (RATE_SOFT, RATE_WEB):
        for hz, h in tabla:
            if e.report_rate_de(bytes.fromhex(h)) != hz:
                fallos.append(f"{h} se lee {e.report_rate_de(bytes.fromhex(h))} "
                              f"Hz, esperaba {hz}")

    # 4. **La baranda del nibble bajo.** Respetarlo puede producir un byte que
    #    ningun cliente oficial mando: si la pagina dejo el mouse en `0x01`
    # -paso- y despues se le pide 1000 Hz, sale `0x41`. El
    #    codificador no lo prohibe, pero tiene que poder decirse.
    raro = e.escribir_report_rate(bytes.fromhex("0101fe00000000"), hz=1000)
    if raro[1] != 0x41:
        fallos.append(f"partiendo del 0x01 de la pagina, 1000 Hz dio "
                      f"{raro[1]:#04x}, esperaba 0x41")
    if e.rate_byte_en_el_bus(raro[1]):
        fallos.append("0x41 no esta en ninguna captura y se lo da por visto")
    for visto in (0x14, 0x44, 0x74, 0x11, 0x77):
        if not e.rate_byte_en_el_bus(visto):
            fallos.append(f"{visto:#04x} esta en el bus y se lo da por raro")
    if len(e.RATE_BYTES_EN_EL_BUS) != 13:
        fallos.append(f"los bytes de rate del bus son 13 (el 0x44 esta en las "
                      f"dos familias), no {len(e.RATE_BYTES_EN_EL_BUS)}")

    # Una tasa que no existe es un error, no un byte cualquiera:
    # la pagina oficial le escribio a este mouse un indice 0 que ninguna
    # captura habia mostrado, y no se sabe que frecuencia deja.
    for malo in (0, 100, 16000, -1):
        try:
            e.escribir_report_rate(bytes.fromhex("0144bb00000000"), hz=malo)
        except ValueError:
            pass
        else:
            fallos.append(f"acepto {malo} Hz, que no es ninguna de las siete")


def test_byte_de_report_rate(fallos: list[str]) -> None:
    from linshark.backend import _adaptar_report_rate
    for byte, hz in RATES_MEDIDOS:
        n = p.rate_indice(byte)
        if p.RATE_HZ.get(n) != hz:
            fallos.append(f"{byte:#04x}: indice {n} = {p.RATE_HZ.get(n)} Hz, "
                          f"la captura dice {hz}")
        # y el camino que ve la pagina
        salida = _adaptar_report_rate(bytes([1, byte, 0xFF ^ byte, 0, 0, 0, 0]))
        if p.RATE_HZ.get(salida[1]) != hz:
            fallos.append(f"{byte:#04x}: el adaptador le pasa a la pagina "
                          f"{p.RATE_HZ.get(salida[1])} Hz en vez de {hz}")

    # La barrida de la WEB escribe los dos nibbles iguales, asi que tiene que
    # dar lo mismo. Es la confirmacion independiente del mapeo.
    for n, hz in p.RATE_HZ.items():
        if p.rate_indice(n << 4 | n) != n:
            fallos.append(f"la forma de la web ({n << 4 | n:#04x}) no da {n}")


# --- El teclado: la tabla de usages y el atajo (funcion 17) -----------------
#
# Dos fuentes, las dos transcritas aca porque el bundle **no se versiona** -se
# guarda su hash y se lo baja con `dev/research/bajar-webapp.sh`-, asi que un test
# que lo leyera del disco pasaria o no segun quien corriera.
#
# 1. `KEYMAP_DEL_BUNDLE` es `_w()` de `app.js`, literal: los nombres son los
#    `event.code` del navegador y los numeros, los usages HID. Nuestra tabla
#    tiene que cubrir **exactamente** esos usages, ni uno mas -inventar una
#    tecla es inventar un byte- ni uno menos.
# 2. `ATAJOS_OFICIALES` son las veinte entradas con codigo 17 de la tabla `sl`
#    del mismo archivo. Cada una es un atajo conocido de Windows, asi que
#    armarlas desde su texto es la Etapa 2 del codificador: veinte
#    combinaciones de modificadores y tecla que escribio el cliente oficial.
#    Dos de ellas ademas estan **en el bus** (ver ATAJO_BUS_* mas abajo).

KEYMAP_DEL_BUNDLE = (
    "KeyA:4,KeyB:5,KeyC:6,KeyD:7,KeyE:8,KeyF:9,KeyG:10,KeyH:11,"
    "KeyI:12,KeyJ:13,KeyK:14,KeyL:15,KeyM:16,KeyN:17,KeyO:18,"
    "KeyP:19,KeyQ:20,KeyR:21,KeyS:22,KeyT:23,KeyU:24,KeyV:25,"
    "KeyW:26,KeyX:27,KeyY:28,KeyZ:29,Digit1:30,Digit2:31,Digit3:32,"
    "Digit4:33,Digit5:34,Digit6:35,Digit7:36,Digit8:37,Digit9:38,"
    "Digit0:39,Enter:40,Escape:41,Backspace:42,Tab:43,Space:44,"
    "Minus:45,Equal:46,BracketLeft:47,BracketRight:48,Backslash:49,"
    "Semicolon:51,Quote:52,Backquote:53,Comma:54,Period:55,"
    "Slash:56,CapsLock:57,F1:58,F2:59,F3:60,F4:61,F5:62,F6:63,"
    "F7:64,F8:65,F9:66,F10:67,F11:68,F12:69,PrintScreen:70,"
    "ScrollLock:71,Pause:72,Insert:73,Home:74,PageUp:75,Delete:76,"
    "End:77,PageDown:78,ArrowRight:79,ArrowLeft:80,ArrowDown:81,"
    "ArrowUp:82,NumLock:83,NumpadDivide:84,NumpadMultiply:85,"
    "NumpadSubtract:86,NumpadAdd:87,NumpadEnter:88,Numpad1:89,"
    "Numpad2:90,Numpad3:91,Numpad4:92,Numpad5:93,Numpad6:94,"
    "Numpad7:95,Numpad8:96,Numpad9:97,Numpad0:98,NumpadDecimal:99,"
    "IntlBackslash:100,ContextMenu:101,Power:102,NumpadEqual:103,"
    "F13:104,F14:105,F15:106,F16:107,F17:108,F18:109,F19:110,"
    "F20:111,F21:112,F22:113,F23:114,F24:115,ControlLeft:224,"
    "ShiftLeft:225,AltLeft:226,GUILeft:227,ControlRight:228,"
    "ShiftRight:229,AltRight:230,GUIRight:231,LeftMouseButton:241,"
    "RightClick:242,MouseWheelClick:243,MouseForward:244,MouseBack:245")

# nombre del bundle -> (p1, p2, como se escribe el atajo en castellano)
ATAJOS_OFICIALES = {
    "FUN_ALL": (1, 4, "ctrl+a"),
    "FUN_COPY": (1, 6, "ctrl+c"),
    "FUN_CUT": (1, 27, "ctrl+x"),
    "FUN_FIND": (1, 9, "ctrl+f"),
    "FUN_NEW": (1, 17, "ctrl+n"),
    "FUN_OPEN": (1, 18, "ctrl+o"),
    "FUN_PASTE": (1, 25, "ctrl+v"),
    "FUN_PRINT": (1, 19, "ctrl+p"),
    "FUN_REDO": (1, 28, "ctrl+y"),
    "FUN_SAVE": (1, 22, "ctrl+s"),
    "FUN_UNDO": (1, 29, "ctrl+z"),
    "FUN_ZOOM_IN": (1, 46, "ctrl+igual"),
    "FUN_ZOOM_OUT": (1, 45, "ctrl+guion"),
    "FUN_BROWSER_FAVORITES": (3, 18, "ctrl+shift+o"),
    "FUN_CLOSE_WINDOWS": (4, 61, "alt+f4"),
    "FUN_SWAP_WINDOWS": (4, 43, "alt+tab"),
    "FUN_LOCK_PC": (8, 15, "win+l"),
    "FUN_RUN": (8, 21, "win+r"),
    "FUN_SHOW_DESKTOP": (8, 7, "win+d"),
    "FUN_SCREEN_CAPTURE": (10, 22, "win+shift+s"),
}

# --- Y el atajo EN EL BUS. Dos bloques de cmd 8 de `soft-todo.pcap`, el soft
# nativo escribiendo atajos de verdad en dos slots distintos:
#
#   16:16:22  ... 11 08 07 ...            el slot escrito 3 pasa a Win+D
#   16:16:28  ... 11 08 07 ... 11 0a 16   y el slot escrito 5, a Win+Shift+S
#
# Son consecutivos y cambian **un solo slot** cada uno, asi que sirven de par
# antes/despues: aplicarle nuestro codificador al primero tiene que dar el
# segundo byte a byte, checksum interno incluido. El bloque previo -con
# `17 00 00`, pista siguiente, en el mismo slot- da el otro par.
ATAJO_BUS_PREVIO = ("01" "020000" "030000" "170000" "0d0000" "020000"
                    "010000" "3c0000" + "010000" * 9 + "0a0000" "090000"
                    + "0084")
ATAJO_BUS_WIN_D = ("01" "020000" "030000" "110807" "0d0000" "020000"
                   "010000" "3c0000" + "010000" * 9 + "0a0000" "090000"
                   + "008d")
ATAJO_BUS_LOS_DOS = ("01" "020000" "030000" "110807" "0d0000" "110a16"
                     "010000" "3c0000" + "010000" * 9 + "0a0000" "090000"
                     + "00bc")


def _a_numeracion_de_lectura(escrito: str) -> bytes:
    """Un bloque de ESCRITURA visto como lo devolveria el mouse.

    Los slots 4, 5 y 6 se remapean entre las dos numeraciones, asi que para
    alimentar a `escribir_boton()` -que recibe la de lectura- con un bloque
    que salio del bus hay que deshacer esa permutacion. No vive en
    `estructuras` porque la aplicacion nunca la necesita: el mouse siempre
    entrega la numeracion de lectura. Aca hace falta porque la evidencia son
    escrituras.
    """
    from linshark import estructuras as e
    datos = bytes.fromhex(escrito)
    salida = bytearray(datos)
    for leido, esc in e.SLOT_ESCRITO_DE_LEIDO.items():
        salida[1 + (leido - 1) * 3: 1 + leido * 3] = \
            datos[1 + (esc - 1) * 3: 1 + esc * 3]
    return bytes(salida)


def test_teclas_del_bundle(fallos: list[str]) -> None:
    from linshark import estructuras as e
    tabla = dict(x.split(":") for x in KEYMAP_DEL_BUNDLE.split(","))
    tabla = {n: int(u) for n, u in tabla.items()}
    del_bundle = {u for u in tabla.values() if u < 224}
    nuestros = set(e.TECLAS_HID.values())
    if nuestros != del_bundle:
        fallos.append(
            f"la tabla de teclas no es la del bundle: nos faltan "
            f"{sorted(del_bundle - nuestros)} y tenemos de mas "
            f"{sorted(nuestros - del_bundle)}")
    if len(set(e.TECLAS_HID)) != len(e.TECLAS_HID.values()):
        fallos.append("dos nombres de tecla apuntan al mismo usage")
    # Los nombres del bundle tienen que seguir entrando: son los que va a
    # tener a mano cualquiera que mire `app.js` o el DOM de la pagina.
    for nombre, usage in tabla.items():
        if usage >= 224:
            continue
        try:
            if e.usage_de_tecla(nombre) != usage:
                fallos.append(f"{nombre} no resuelve a {usage}")
        except ValueError:
            fallos.append(f"{nombre} (usage {usage}) no lo acepta nadie")
    # y la vuelta, que es lo que se muestra
    for usage in sorted(del_bundle):
        nombre = e.nombre_de_tecla(usage)
        if nombre is None or e.usage_de_tecla(nombre) != usage:
            fallos.append(f"usage {usage} no vuelve a su nombre ({nombre})")
    # Los cinco botones del mouse NO son teclas: en un atajo no van, en un
    # macro si. La separacion es la que impide escribir `11 00 f1`.
    for usage in e.MACRO_USAGE_BOTONES:
        if usage in nuestros:
            fallos.append(f"el boton {usage} entro en la tabla de teclas")
        if usage not in e.USAGES_DE_EVENTO:
            fallos.append(f"el boton {usage} no vale como evento de macro")
    # Y los trece nombres del bundle que no son teclas -los cinco botones y
    # los ocho modificadores- tienen que entrar como evento de macro: adentro
    # de un macro el Ctrl es una tecla mas, se aprieta y se suelta.
    for nombre, usage in tabla.items():
        if usage < 224:
            continue
        try:
            if e.usage_de_evento(nombre) != usage:
                fallos.append(f"{nombre} no resuelve a {usage} como evento")
        except ValueError:
            fallos.append(f"{nombre} (usage {usage}) no vale como evento de "
                          "macro, y el bundle lo declara")
        if e.nombre_de_evento(usage).startswith("usage "):
            fallos.append(f"el usage {usage} no tiene nombre propio")


def test_etapa2_atajo(fallos: list[str]) -> None:
    from linshark import estructuras as e

    # 1. las veinte entradas del bundle, armadas desde su texto
    for nombre, (p1, p2, texto) in ATAJOS_OFICIALES.items():
        try:
            nuestro = e.atajo_desde_texto(texto)
        except ValueError as exc:
            fallos.append(f"{nombre} ({texto}) no se pudo armar: {exc}")
            continue
        if nuestro != (p1, p2):
            fallos.append(f"{nombre}: {texto!r} da {nuestro}, el bundle "
                          f"escribe ({p1}, {p2})")
        if e.ATAJOS_DEL_BUNDLE.get(nombre) != (p1, p2):
            fallos.append(f"{nombre}: la tabla del modulo dice "
                          f"{e.ATAJOS_DEL_BUNDLE.get(nombre)}")
        # y el texto que mostramos tiene que volver a los mismos dos bytes
        if e.atajo_desde_texto(e.texto_de_atajo(p1, p2)) != (p1, p2):
            fallos.append(f"{nombre}: {e.texto_de_atajo(p1, p2)!r} no vuelve "
                          f"a ({p1}, {p2})")

    # 2. contra el bus: los dos bloques que el soft nativo escribio
    previo = _a_numeracion_de_lectura(ATAJO_BUS_PREVIO)
    # el slot escrito 3 es el leido 3: la rueda no se remapea
    win_d = e.escribir_atajo(previo, slot=3, atajo="win+d")
    if win_d.hex() != ATAJO_BUS_WIN_D:
        fallos.append("atajo Win+D: no da el bloque del driver oficial\n"
                      f"      nuestro: {win_d.hex()}\n"
                      f"      oficial: {ATAJO_BUS_WIN_D}")
    # y el segundo, sobre el primero: el slot escrito 5 es el leido 4
    los_dos = e.escribir_atajo(_a_numeracion_de_lectura(ATAJO_BUS_WIN_D),
                               slot=4, atajo="win+shift+s")
    if los_dos.hex() != ATAJO_BUS_LOS_DOS:
        fallos.append("atajo Win+Shift+S: no da el bloque del driver oficial\n"
                      f"      nuestro: {los_dos.hex()}\n"
                      f"      oficial: {ATAJO_BUS_LOS_DOS}")
    # el par (p1, p2) directo tiene que dar lo mismo que el texto
    if e.escribir_atajo(previo, slot=3, atajo=(8, 7)) != win_d:
        fallos.append("el atajo por (p1, p2) no da lo mismo que por texto")

    # 3. un slot leido se muestra con su atajo, no como "atajo de teclado"
    #    a secas: los dos bytes de adentro son la mitad del dato. El caso que
    #    lo pide es el macro sin id, que un cliente mostraria como "macro" y
    #    es un boton muerto.
    bots = e.botones_de(_a_numeracion_de_lectura(ATAJO_BUS_LOS_DOS))
    detalles = {b["indice"]: b["detalle"] for b in bots}
    if detalles.get(3) != "atajo de teclado win+d":
        fallos.append(f"el slot del atajo se muestra {detalles.get(3)!r}")
    if e.detalle_de_slot(e.FUNCION_MACRO, 0, 0x11) != "macro 17":
        fallos.append("el slot de macro no dice cual macro")
    if "muerto" not in e.detalle_de_slot(e.FUNCION_MACRO, 0, 0):
        fallos.append("un slot de macro sin id se muestra como si sirviera")

    # 4. las barandas
    for malo, por_que in (("", "vacio"), ("ctrl", "solo modificadores"),
                          ("ctrl+shift", "solo modificadores"),
                          ("ctrl+inexistente", "tecla que no existe"),
                          ("ctrl+clic-izquierdo", "un boton no es tecla")):
        try:
            e.atajo_desde_texto(malo)
        except ValueError:
            pass
        else:
            fallos.append(f"atajo_desde_texto({malo!r}) paso: {por_que}")
    # el slot vacio del bundle, que es el que deja el boton muerto
    try:
        e.escribir_boton(previo, slot=3, codigo=e.FUNCION_ATAJO, p1=0, p2=0)
    except ValueError:
        pass
    else:
        fallos.append("escribir_boton() dejo escribir `11 00 00`, el slot "
                      "vacio: el mouse lo acusa y el boton queda muerto")
    # los modificadores derechos no los escribio ningun cliente oficial
    for derecho in (0x10, 0x20, 0x40, 0x80, 0x11):
        try:
            e.escribir_atajo(previo, slot=3, atajo=(derecho, 6))
        except ValueError:
            pass
        else:
            fallos.append(f"el atajo acepto la mascara {derecho:#04x}, que "
                          "ningun cliente oficial escribio")
    # un modificador como tecla va en p1, no en p2
    try:
        e.escribir_atajo(previo, slot=3, atajo=(1, 224))
    except ValueError:
        pass
    else:
        fallos.append("el atajo acepto un modificador como tecla en p2")
    # y el unico clic izquierdo no se pierde tampoco por este camino. En este
    # bloque capturado el boton 4 tambien hace clic izquierdo, asi que el 1 se
    # puede cambiar; sin ese segundo clic, no.
    try:
        e.escribir_atajo(previo, slot=1, atajo="ctrl+c")
    except e.SinClicIzquierdo as exc:
        fallos.append(f"con el clic izquierdo tambien en el 4, el atajo en el "
                      f"1 no paso: {exc}")
    solo_uno = bytearray(previo)
    solo_uno[1 + 3 * 3] = 5                              # slot leido 4 -> atras
    try:
        e.escribir_atajo(bytes(solo_uno), slot=1, atajo="ctrl+c")
    except e.SinClicIzquierdo:
        pass
    else:
        fallos.append("escribir_atajo() dejo sacar el unico clic izquierdo")


# --- El codificador de eventos de macro, contra el unico macro capturado.
#
# `MACRO_BLOQUE` son los 111 bytes que el soft nativo le escribio al mouse:
# el macro 0x11, modo 0, diez eventos de 10 ms que aprietan y sueltan los
# cinco botones. Armar esa misma lista desde cero tiene que dar esos bytes,
# **checksum interno incluido**, y las dos tramas del bus tienen que salir
# identicas a las del driver oficial.
#
# Es la Etapa 2 mas barata que quedaba en el proyecto: el bloque ya estaba en
# el repo, y lo unico que faltaba era el codificador.

EVENTOS_CAPTURADOS = [
    ("clic-izquierdo", 0, 10), ("clic-izquierdo", 1, 10),
    ("clic-rueda", 0, 10), ("clic-rueda", 1, 10),
    ("atras", 0, 10), ("atras", 1, 10),
    ("adelante", 0, 10), ("adelante", 1, 10),
    ("clic-derecho", 0, 10), ("clic-derecho", 1, 10),
]


def test_etapa2_eventos_de_macro(fallos: list[str]) -> None:
    from linshark import estructuras as e
    escrito = bytes.fromhex(MACRO_BLOQUE)[2:]
    leido = bytes.fromhex(MACRO_LEIDO)

    # 1. armado desde cero: el bloque del bus, byte a byte
    nuestro = e.armar_macro(0x11, EVENTOS_CAPTURADOS, modo=0)
    if nuestro != escrito:
        fallos.append(
            "armar_macro() no reproduce el macro que el soft nativo escribio\n"
            f"      nuestro: {nuestro.hex()}\n      oficial: {escrito.hex()}")
    # y las dos tramas que van al mouse
    bloque = bytes.fromhex(MACRO_BLOQUE)
    nuestras = tuple(x.hex() for x in
                     p.build_write_blocks(bloque[:2] + nuestro))
    if nuestras != MACRO_OFICIAL[0]:
        fallos.append(f"las tramas del macro armado no son las del bus: "
                      f"{list(nuestras)}")

    # 2. idempotente: los eventos leidos, devueltos, no mueven un byte
    m = e.parametros_de_macro(leido)
    ida = e.escribir_eventos_macro(leido, m["eventos"])
    if ida != escrito:
        fallos.append(
            "reescribir los eventos leidos no da el bloque oficial\n"
            f"      nuestro: {ida.hex()}\n      oficial: {escrito.hex()}")
    # ida y vuelta: lo que se escribe se lee igual
    vuelta = e.parametros_de_macro(ida)
    if [(x["usageId"], x["direccion"], x["tiempo"]) for x in vuelta["eventos"]] \
            != [(x["usageId"], x["direccion"], x["tiempo"])
                for x in m["eventos"]]:
        fallos.append("los eventos no sobreviven la ida y vuelta")

    # 3. un macro distinto: teclas, y el disparo que no se toca
    eventos = [("ctrl", 0, 10), ("c", 0, 20), ("c", 1, 20), ("ctrl", 1, 10)]
    ctrl_c = e.escribir_eventos_macro(leido, eventos)
    m2 = e.parametros_de_macro(ctrl_c)
    if [(x["usageId"], x["direccion"], x["tiempo"]) for x in m2["eventos"]] != \
            [(224, 0, 10), (6, 0, 20), (6, 1, 20), (224, 1, 10)]:
        fallos.append(f"el macro de teclas no cierra: {m2['eventos']}")
    if ctrl_c[6] != 4:
        fallos.append(f"el contador de pares quedo en {ctrl_c[6]}, esperaba 4")
    if ctrl_c[0] != leido[0] or ctrl_c[1] != leido[1]:
        fallos.append("grabar eventos movio el id o el modo del macro")
    if not m2["checksum_ok"] or m2["checksumOrden"] != "big":
        fallos.append("el macro grabado no lleva el checksum como se escribe")
    # el hueco que dejan los eventos que ya no estan tiene que quedar en cero,
    # como en el bloque del bus: si no, sobreviven bytes del macro anterior
    if any(ctrl_c[7 + 8:-2]):
        fallos.append("quedaron bytes del macro viejo detras de los eventos")

    # 4. la rama larga: cuatro bytes, y el tiempo que se pidio
    largo = e.escribir_eventos_macro(leido, [("a", 0, 250), ("a", 1, 10)])
    m3 = e.parametros_de_macro(largo)
    if [(x["tiempo"], x["largo"]) for x in m3["eventos"]] != \
            [(250, True), (10, False)]:
        fallos.append(f"la rama larga no cierra: {m3['eventos']}")
    if largo[6] != 3:
        fallos.append(f"un evento largo y uno corto son 3 pares, no {largo[6]}")
    if e.cuantos_largos([("a", 0, 250), ("a", 1, 10)]) != 1:
        fallos.append("cuantos_largos() no cuenta la rama inferida")
    # **y el bit 0 no se fuerza**: el bundle escribiria 251 donde se pidio 250
    if largo[7] & 1:
        fallos.append("el codificador forzo el bit 0 de la rama larga, que es "
                      "lo que hace que el bundle escriba 351 donde quiso 350")

    # 5. las barandas
    for malos, por_que in (
            ([("a", 0, 10)] * (e.MACRO_EVENTOS_MAX + 1), "51 eventos cortos"),
            ([("a", 0, 200)] * 26, "26 eventos largos"),
            ([("a", 0, e.MACRO_TIEMPO_MAX + 1)], "tiempo fuera de rango"),
            ([("a", 2, 10)], "direccion que no es un bit"),
            ([(3, 0, 10)], "el usage 3, que es la continuacion"),
            ([("inexistente", 0, 10)], "una tecla que no existe")):
        try:
            e.escribir_eventos_macro(leido, malos)
        except ValueError:
            pass
        else:
            fallos.append(f"el codificador acepto {por_que}")
    # el limite exacto si tiene que entrar
    try:
        lleno = e.escribir_eventos_macro(leido, [("a", 0, 10)]
                                         * e.MACRO_EVENTOS_MAX)
    except ValueError as exc:
        fallos.append(f"{e.MACRO_EVENTOS_MAX} eventos no entraron: {exc}")
    else:
        if lleno[6] != e.MACRO_EVENTOS_MAX or len(lleno) != 109:
            fallos.append(f"el bloque lleno mide {len(lleno)} B con "
                          f"{lleno[6]} pares")
        if not e.parametros_de_macro(lleno)["checksum_ok"]:
            fallos.append("el bloque lleno se comio el checksum")
    # 6. el texto con el que se escribe un macro a mano: ida y vuelta
    texto = "clic-izquierdo:abajo@10, a:dir1@250, ctrl:arriba@0"
    evs = e.eventos_desde_texto(texto)
    if [(x["usageId"], x["direccion"], x["tiempo"]) for x in evs] != \
            [(241, 0, 10), (4, 1, 250), (224, 1, 0)]:
        fallos.append(f"el texto no se parsea: {evs}")
    if e.eventos_desde_texto(e.texto_de_eventos(evs)) != evs:
        fallos.append("los eventos no sobreviven la vuelta por texto, asi que "
                      "lo que el CLI imprime no se puede volver a pegar")
    for malo in ("", "a@10", "a:abajo", "a:abajo@diez", "a:costado@10",
                 "   ,  "):
        try:
            e.eventos_desde_texto(malo)
        except ValueError:
            pass
        else:
            fallos.append(f"eventos_desde_texto({malo!r}) paso")

    # armar_macro valida el id, que es el mismo agujero que el del slot
    for malo in (0, 256):
        try:
            e.armar_macro(malo, EVENTOS_CAPTURADOS)
        except ValueError:
            pass
        else:
            fallos.append(f"armar_macro() acepto el id {malo}")


# --- Los nombres de macro, que el mouse no guarda.
#
# Los 111 bytes no tienen campo de nombre -MEDIDO: el bloque entero esta
# decodificado- y el soft los guarda en su propio archivo, `ms_13/macro.data`.
# O sea que los nombres son cosa del cliente. Lo que este test cuida es que la
# aplicacion no se confunda de lugar: el nombre es nuestro, el macro es del
# mouse, y perder el archivo no puede romper nada.

def test_nombres_de_macro(fallos: list[str]) -> None:
    import json
    import tempfile
    from pathlib import Path

    from linshark import nombres

    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "macros.json"
        lib = nombres.NombresDeMacro(ruta)
        if lib.nombre(17) is not None:
            fallos.append("un macro sin nombre tendria que dar None")
        if lib.describir(17) != "macro 17":
            fallos.append(f"sin nombre se dice 'macro 17', no {lib.describir(17)!r}")
        lib.poner(17, "copiar y pegar")
        lib.guardar()
        if not ruta.exists():
            fallos.append("guardar() no escribio el archivo")
        otra = nombres.NombresDeMacro(ruta)
        if otra.nombre(17) != "copiar y pegar":
            fallos.append(f"el nombre no sobrevivio: {otra.nombre(17)!r}")
        if otra.describir(17) != "macro 17 (copiar y pegar)":
            fallos.append(f"describir(): {otra.describir(17)!r}")
        if otra.todos() != {17: "copiar y pegar"}:
            fallos.append(f"todos(): {otra.todos()!r}")
        # el id se valida con el mismo rango que usa el mouse
        for malo in (0, 256, -1):
            try:
                lib.poner(malo, "x")
            except ValueError:
                pass
            else:
                fallos.append(f"acepto el id {malo}")
        # y el nombre no puede ser vacio: eso es borrar, y se dice borrando
        try:
            lib.poner(17, "   ")
        except ValueError:
            pass
        else:
            fallos.append("acepto un nombre vacio en vez de pedir borrar()")
        lib.borrar(17)
        lib.guardar()
        if nombres.NombresDeMacro(ruta).nombre(17) is not None:
            fallos.append("borrar() no borro")

        # Un archivo roto no puede llevarse puesta la sesion: el nombre es una
        # comodidad y el mouse anda sin el. Se avisa y se sigue.
        ruta.write_text("{ esto no es json")
        rota = nombres.NombresDeMacro(ruta)
        if rota.nombre(17) is not None or rota.todos():
            fallos.append("un archivo roto tendria que leerse como vacio")
        if not rota.problema:
            fallos.append("un archivo roto tendria que dejar dicho que lo esta")
        # y no se pisa solo: guardar sobre un archivo que no se pudo leer
        # perderia lo que hubiera adentro sin que nadie lo vea
        try:
            rota.guardar()
        except RuntimeError:
            pass
        else:
            fallos.append("guardo encima de un archivo que no pudo leer")

        # El archivo es de la aplicacion, no del mouse: tiene que decir de que
        # dispositivo habla, para que dos mouses no se pisen los nombres.
        ruta2 = Path(tmp) / "otro.json"
        lib2 = nombres.NombresDeMacro(ruta2)
        lib2.poner(1, "ñandú")           # y en UTF-8, que es donde se rompen
        lib2.guardar()
        crudo = json.loads(ruta2.read_text(encoding="utf-8"))
        if crudo.get("macros", {}).get("1") != "ñandú":
            fallos.append(f"el archivo quedo raro: {crudo!r}")
        if crudo.get("dispositivo") != nombres.DISPOSITIVO:
            fallos.append("el archivo no dice de que dispositivo habla; dos "
                          f"mouses se pisarian los nombres: {crudo!r}")


async def main() -> int:
    pruebas_sync = [
        ("H-02  comando sin sub documentado", test_comando_sin_sub),
        ("H-03  canal de solo lectura", test_canal_solo_lectura),
        ("H-08  full no habilita nada solo", test_modo_full_no_habilita_nada_solo),
        ("N-01  el error del CLI ofrece lo que el CLI acepta",
         test_el_error_del_cli_ofrece_lo_que_el_cli_acepta),
        ("H-08  el puente ofrece menos que WRITABLE",
         test_el_puente_ofrece_menos_que_writable),
        ("      framing igual al del binario", test_trama_igual_a_la_del_binario),
        ("      lectura cortada != escritura", test_lectura_cortada),
        ("      tramas de escritura (fase 2)", test_tramas_de_escritura),
        ("      largo = N + 5 en capturas reales", test_largo_es_n_mas_cinco),
        ("      estructuras vs. capturas reales", test_estructuras),
        ("      etapa 2: lectura -> trama oficial", test_etapa2_ida_y_vuelta),
        ("      etapa 2: cmd 8, y con cambio real", test_etapa2_botones),
        ("      la sonda de macro es angosta", test_sonda_de_macro_es_angosta),
        ("      la funcion macro necesita su id", test_boton_macro_necesita_id),
        ("      cmd 9: Etapa 2 del codificador", test_etapa2_macro),
        ("      cmd 9: el mensaje del paso 3", test_mensaje_de_cambio_de_macro),
        ("      cmd 9: el paso 6 relee los mismos macros",
         test_macros_del_paso_6_son_los_del_previo),
        ("H-08  la confirmacion no se tapa sola",
         test_la_confirmacion_no_se_tapa),
        ("      el formato de la linea que se lee", test_linea_de_lectura),
        ("      cmd 9: macro por bloques", test_macro_por_bloques),
        ("      cmd 9: la rama larga de los eventos",
         test_macro_con_tiempos_largos),
        ("      cmd 9: el bloque leido del mouse",
         test_macro_leido_del_mouse),
        ("      reescribir lo mismo no mueve un byte",
         test_reescribir_el_mismo_valor_no_mueve_un_byte),
        ("      el dpi se cuantiza de a 50", test_dpi_se_cuantiza),
        ("      cmd de escritura = payload[0]", test_cmd_de_escritura),
        ("      byte de report rate", test_byte_de_report_rate),
        ("H-08  no se empaqueta la trama dos veces",
         test_no_se_empaqueta_dos_veces),
        ("      cmd 6: las siete tasas vs. el bus",
         test_escribir_report_rate),
        ("      el modelo con nombres propios",
         test_modelo_con_nombres_propios),
        ("      donde esta el mouse, y por que camino",
         test_donde_esta_el_mouse),
        ("      el driver no necesita a dev/", test_el_driver_no_necesita_a_dev),
        ("      lo del mouse no va al lado del codigo",
         test_lo_del_mouse_no_va_al_lado_del_codigo),
        ("      todo el codigo compila", test_todo_el_codigo_compila),
        ("      el instalador apunta a lo que existe",
         test_el_instalador_apunta_a_archivos_que_existen),
        ("      las traducciones del README estan al dia",
         test_las_traducciones_no_quedaron_atrasadas),
        ("      cable: los constructores dicen lo del helper",
         test_constructores_del_cable),
        ("      cable: la Etapa 2 contra lo que escribio el soft",
         test_etapa2_cable),
        ("      cable: un solo canal, el de cable.py",
         test_el_cable_solo_pasa_por_su_canal),
        ("      el perfil declarativo no miente", test_el_perfil_no_miente),
        ("      el perfil manda de verdad", test_el_perfil_manda_de_verdad),
        ("G-02  los macros, modelados para la interfaz",
         test_modelo_de_macros),
        ("G-03/05 las novedades del mouse, y el nodo sin permiso",
         test_novedades_y_permiso),
        ("      el veredicto del paso 6", test_veredicto_del_paso_6),
        ("      que cambio en una escritura", test_que_cambio_en_una_escritura),
        ("      el diff mira los dos lados",
         test_diferencias_mira_los_dos_lados),
        ("      escribir un nivel de dpi", test_escribir_un_nivel_de_dpi),
        ("      escribir el color de la luz", test_escribir_color_luz),
        ("      cmd 5: hibernacion y respuesta", test_parametros_de_luz),
        ("      escribir hibernacion vs. el oficial",
         test_escribir_parametros_luz),
        ("      escribir el reposo corto vs. el oficial",
         test_escribir_reposo_ligero),
        ("      cmd 4: el nivel de dpi en uso", test_escribir_nivel_activo),
        ("      cmd 4: los cuatro interruptores del sensor",
         test_escribir_parametros_sensor),
        ("      el consejo de verificacion no revienta",
         test_consejo_de_verificacion),
        ("      cmd 9: el aviso de teclas trabadas llega antes",
         test_advertencias_de_eventos),
        ("      cmd 8: botones, y el desacuerdo de la rueda", test_botones),
        ("      cmd 8: orden físico de botones y evidencia",
         test_botones_fisicos_y_orden_de_botones),
        ("      cmd 8: intercambiar y restaurar cuidan el clic izquierdo",
         test_intercambiar_y_restaurar_cuidan_el_clic_izquierdo),
        ("      las teclas HID son las del bundle", test_teclas_del_bundle),
        ("      cmd 8: el atajo de teclado vs. el bus", test_etapa2_atajo),
        ("      cmd 9: grabar eventos vs. el bus",
         test_etapa2_eventos_de_macro),
        ("      los nombres de macro los guarda la app",
         test_nombres_de_macro),
    ]
    pruebas_async = [
        ("      cable: el canal y la sesion, contra el bus",
         test_canal_por_cable),
        ("H-02  leer() no revienta", test_leer_sin_sub_no_revienta),
        ("H-05  0xC3 reintenta rapido", test_ocupado_reintenta_rapido),
        ("H-07  filtro de Origin", test_filtro_de_origen),
        ("H-09  basura no corta la sesion", test_basura_no_corta_la_sesion),
        ("      respuestas largas en bloques", test_reensamblado),
        ("      respuesta en la pausa de 0xC3", test_respuesta_durante_la_pausa),
        ("      gracia con un bloque tardio", test_gracia_con_bloque_tardio),
        ("      un parcial no contamina al que sigue",
         test_parcial_no_contamina_al_siguiente),
        ("      la sesion lee el estado entero",
         test_sesion_lee_el_estado_entero),
        ("H-08  el camino de escritura filtra", test_camino_de_escritura),
        ("H-08  las escrituras no se enciman",
         test_las_escrituras_no_se_encinan),
        ("      el puente pide el macro correcto",
         test_el_puente_pide_el_macro_correcto),
        ("      una tasa ilegible no deja al programa afuera",
         test_una_tasa_ilegible_no_deja_al_programa_afuera),
        ("      el camino de escritura lo elige el tamaño",
         test_el_camino_de_escritura_lo_elige_el_tamano),
        ("      la herramienta de punta a punta, sin mouse",
         test_la_herramienta_de_punta_a_punta),
        ("G-01  el despachador da lo mismo que el CLI",
         test_el_despachador_y_el_cli_dan_lo_mismo),
        ("       leer y reescribir no mueve nada",
         test_leer_y_reescribir_no_mueve_nada),
        ("      la tasa insiste y no escribe de gusto",
         test_la_tasa_insiste_y_no_escribe_de_gusto),
        ("      configurar baja la tasa una sola vez",
         test_configurar_baja_la_tasa_una_vez),
        ("      volver a como estaba, con la tasa prestada",
         test_volver_a_como_estaba_con_la_tasa_prestada),
        ("      a tasa alta la ventana puede escribir",
         test_a_tasa_alta_la_ventana_puede_escribir),
        ("      la relectura acotada no afirma de mas",
         test_la_relectura_acotada_no_afirma_de_mas),
        ("H-08  el orquestador aborta donde debe",
         test_el_orquestador_aborta_donde_debe),
        ("H-08  un bloque imposible no sale al bus",
         test_no_se_escribe_un_bloque_imposible),
        ("H-08  el sangrado de buffer se detecta",
         test_el_sangrado_de_buffer_se_detecta),
        ("H-08  un estado incoherente no pasa",
         test_el_estado_incoherente_no_pasa),
        ("      varios campos de un bloque salen juntos",
         test_varios_campos_de_un_bloque_salen_juntos),
        ("H-08  el canario de version de firmware",
         test_el_canario_de_version),
        ("N-H04 acuse en la pausa de 'ocupado'",
         test_acuse_en_la_pausa_de_ocupado),
        ("N-H04 acuse en la pausa de reintento",
         test_acuse_en_la_pausa_de_reintento),
        ("N-H04 sin acuse sigue siendo fallo",
         test_sin_acuse_sigue_siendo_fallo),
        ("      cmd 9: las dos tramas al mouse",
         test_macro_por_bloques_al_mouse),
    ]

    malos = 0
    for nombre, prueba in pruebas_sync:
        fallos: list[str] = []
        prueba(fallos)
        malos += _informar(nombre, fallos)
    for nombre, prueba in pruebas_async:
        fallos = []
        await prueba(fallos)
        malos += _informar(nombre, fallos)

    print()
    print("todo en orden" if malos == 0 else f"{malos} prueba(s) con problemas")
    return 1 if malos else 0


def _informar(nombre: str, fallos: list[str]) -> int:
    if fallos:
        print(f"FALLA  {nombre}")
        for f in fallos:
            print(f"         - {f}")
        return 1
    print(f"ok     {nombre}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
