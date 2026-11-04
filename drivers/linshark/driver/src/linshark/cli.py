# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from . import protocol as p
from . import server
from .backend import HidrawBackend, Mode, StubBackend
from .hidraw import DeviceNotFound

# main() lo vuelve a pedir despues de basicConfig; es el mismo objeto.
log = logging.getLogger("linshark")

# Los comandos que se pueden nombrar en --permitir-escritura. `p.WRITABLE` es
# la lista real y `backend.py` la exige; esto es un subconjunto **a proposito**,
# y la diferencia importa.
#
# `p.WRITABLE` tiene tambien `CMD_LIGHTING` (cmd 5), y el
# proyecto ya lo escribio -color, hibernacion y reposo corto-. Pero **por el
# puente no se expone**, y no es un olvido:
#
#   * Lo que cruza el puente lo maneja la **pagina oficial**, no nosotros. Con
#     `full` + `--permitir-escritura dpi` ya esta MEDIDO que abrir la pagina le
#     reescribe el dpi al mouse **solo por conectarse**, sin que nadie toque un
#     control (I-W12, visto seis veces).
#   * Cmd 5 no es "la luz": lleva los **dos** temporizadores de reposo y el
#     tiempo de respuesta de los botones, y tres de sus nueve campos no tienen
#     significado univoco (I-W14). Dejar que la pagina lo reescriba al conectar
#     seria pisar en silencio lo que costo dos dias medir.
#
# Cmd 5 se escribe con `driver/scripts/primera-escritura.py`, que pide un campo por
# corrida, arma la trama a la vista, la simula por defecto y pide confirmacion.
# O sea: no es que el puente sepa menos, es que el puente no elige que escribir.
#
# **Cmd 8 (botones) entro a `p.WRITABLE` y tampoco se expone
# aca**, por el mismo motivo y con una razon medida encima: el bloque de
# botones que la pagina escribe al conectarse trae los slots de la rueda al
# reves, y eso **invierte el scroll**(girandola). O sea que
# permitirle a la pagina escribir cmd 8 por el puente seria dejar que rompa la
# rueda sin que nadie toque un control. Y ademas un mouse que se queda sin
# clic izquierdo no se puede arreglar desde ninguna interfaz; la baranda que lo
# impide vive en `estructuras.escribir_boton()`, que el puente no usa.
ESCRIBIBLES = {
    "rate": p.CMD_REPORT_RATE,
    "dpi": p.CMD_DPI,
}

CONN_CHOICES = {
    "cable": p.CONN_WIRED,
    "2.4g": p.CONN_WIRELESS,
    "8k": p.CONN_8K_B,
    "8k-82": p.CONN_8K_A,
    "8k-85": p.CONN_8K_C,
    "bt": p.CONN_BLUETOOTH,
}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="linshark",
        description="Se hace pasar por el helper nativo de szslxd-tech.com "
                    "para que su web driver funcione en Linux.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
modos del backend hidraw:
  listen   abre el mouse en SOLO LECTURA y escucha. No le escribe nada,
           y el descriptor no lo permitiria aunque el codigo lo intentara.
           (por defecto)
  read     lo abre lectura/escritura y traduce las lecturas que pide la
           pagina, con las plantillas de 12 bytes sacadas del helper oficial.

  full     ademas deja pasar escrituras, pero SOLO de los comandos que se
           nombren con --permitir-escritura, y por defecto en simulacro:
           arma la trama, la muestra y no la manda. Con --sin-simulacro
           manda de verdad, pidiendo confirmacion la primera vez.

'--mode full' a secas es un error, no un permiso amplio. Solo se pueden
nombrar comandos cuyo formato de escritura reprodujo byte a byte una trama
del driver oficial (Etapa 2 de dev/docs/metodo.md): hoy rate y dpi.

Se sube de modo a proposito. Mandarle bytes inventados al endpoint vendor de
un mouse es la forma de dejarlo ladrillo.
""",
    )
    ap.add_argument("--port", type=int, default=server.DEFAULT_PORT,
                    help="puerto WebSocket (por defecto %(default)s)")
    ap.add_argument("--backend", choices=("stub", "hidraw"), default="stub",
                    help="'stub' simula el mouse sin tocar el hardware; "
                         "'hidraw' habla con el mouse de verdad")
    ap.add_argument("--mode", choices=Mode.ALL, default=Mode.LISTEN,
                    help="solo para --backend hidraw (por defecto %(default)s)")
    ap.add_argument("--hidraw", type=Path, metavar="/dev/hidrawN",
                    help="forzar el nodo; por defecto se busca en sysfs. Se "
                         "verifica que sea la interfaz 2 del dongle")
    ap.add_argument("--conn", choices=sorted(CONN_CHOICES), default="8k",
                    help="metodo de conexion que le declaramos a la pagina; "
                         "los '8k' hacen que habilite las opciones de 8 kHz")
    ap.add_argument("--device", type=int, default=p.DEVICE_X8_PRO,
                    help="id de modelo (8 = X8 Pro)")
    ap.add_argument("--battery", type=int, default=100)
    ap.add_argument("--record", type=Path, metavar="ARCHIVO.jsonl",
                    help="graba todo el trafico para analizarlo despues")
    ap.add_argument("--permitir-origen", action="append", metavar="URL", default=[],
                    help="acepta conexiones de este Origin ademas de los de "
                         "szslxd-tech.com. Repetible")
    ap.add_argument("--sin-chequeo-de-origen", action="store_true",
                    help="acepta cualquier Origin. Con esto, cualquier pagina "
                         "abierta en el navegador puede hablarle al mouse")
    ap.add_argument("--permitir-escritura", action="append", default=[],
                    metavar="CMD", choices=sorted(ESCRIBIBLES),
                    help="habilita escribir ESE comando, y solo ese. Repetible. "
                         "Necesita --mode full. Sin esto, 'full' no escribe "
                         "nada. Hoy: " + ", ".join(sorted(ESCRIBIBLES)))
    ap.add_argument("--sin-simulacro", action="store_true",
                    help="manda las escrituras de verdad. Por defecto el modo "
                         "full arma la trama, la muestra y NO la manda. "
                         "Pide confirmacion la primera vez de cada sesion")
    ap.add_argument("--bateria-minima", type=int, default=None, metavar="PCT",
                    help="no escribe si el mouse reporta menos que esto "
                         "(por defecto 50)")
    ap.add_argument("-v", "--verbose", action="store_true")
    return ap


def _construir_backend(args, conn, model):
    if args.backend == "stub":
        log.info("backend=stub  simulando %s via %s", model, p.CONN_NAMES[conn])
        return StubBackend(connection_method=conn, device_id=args.device,
                           battery_level=args.battery)

    log.info("backend=hidraw  %s via %s", model, p.CONN_NAMES[conn])
    # **El techo del CLI es mas bajo que el del backend, y el mensaje tiene que
    # decir el del CLI.** `backend.py` nombra `WRITABLE - SIN_CAMINO_EN_EL_BACKEND`
    # -rate, dpi, luz y botones-, que es correcto para quien usa `HidrawBackend`
    # desde codigo propio. Pero por aca `--permitir-escritura` solo acepta
    # `ESCRIBIBLES`, asi que ese mensaje mandaba a pedir dos comandos que
    # argparse rechaza dos lineas despues. Lo marco la auditoria del agente B (N-01)
    # en dos pasadas seguidas.
    #
    # La baranda real sigue siendo la del backend: esto solo llega antes y con
    # el nombre correcto, igual que la validacion temprana de valores en
    # `primera-escritura.py`.
    if args.mode == Mode.FULL and not args.permitir_escritura:
        raise ValueError(
            "el modo 'full' no habilita nada por si solo: hay que nombrar cada "
            "comando con --permitir-escritura. Por el puente se puede pedir "
            + ", ".join(f"{n} ({ESCRIBIBLES[n]})" for n in sorted(ESCRIBIBLES))
            + ". Los demas comandos escribibles no salen por aca a proposito "
              "(ver dev/docs/metodo.md): por el puente quien escribe es la pagina "
              "oficial, que reescribe lo que lee")
    permitidos = [ESCRIBIBLES[n] for n in args.permitir_escritura]
    extra = {}
    if args.bateria_minima is not None:
        extra["bateria_minima"] = args.bateria_minima
    backend = HidrawBackend(connection_method=conn, device_id=args.device,
                            mode=args.mode, path=args.hidraw,
                            battery_level=args.battery,
                            permitir_escritura=permitidos,
                            simulacro=not args.sin_simulacro,
                            confirmar=_confirmar_en_consola,
                            **extra)
    if permitidos:
        nombres = ", ".join(sorted(args.permitir_escritura))
        if args.sin_simulacro:
            log.warning("ESCRITURA HABILITADA de verdad para: %s", nombres)
        else:
            log.info("simulacro de escritura para: %s "
                     "(no se manda nada; --sin-simulacro para mandar)", nombres)
    return backend


class _SilenciarRutina(logging.Filter):
    """Tapa el log de rutina mientras hay una pregunta esperando respuesta.

    **Sin esto la confirmacion es inutil, y quedo demostrado**:
    el mouse manda una notificacion de presencia cada dos segundos, asi que el
    `Escribir? [escribir/no]:` desaparecia de la pantalla antes de que nadie
    pudiera leerlo. Dos sesiones enteras se perdieron por eso, y la escritura
    que se queria probar nunca salio.

    Las advertencias y los errores **si** pasan: si el mouse se desconecta
    justo ahi, eso hay que verlo aunque tape la pregunta.
    """

    activo = False
    ocultadas = 0

    def filter(self, record: logging.LogRecord) -> bool:
        if not _SilenciarRutina.activo or record.levelno >= logging.WARNING:
            return True
        _SilenciarRutina.ocultadas += 1
        return False


_silenciador = _SilenciarRutina()


async def _confirmar_en_consola(nombre: str, hexa: str) -> bool:
    """Pregunta una vez por sesion, antes de la primera escritura real.

    Corre en un hilo porque `input()` bloquea, y el loop de asyncio tiene que
    seguir atendiendo al mouse mientras tanto. Si no hay terminal, no hay
    confirmacion posible y la respuesta es que no: es preferible que una
    sesion sin tty no escriba a que escriba sin que nadie haya mirado.
    """
    if not sys.stdin.isatty():
        log.error("hace falta confirmar la primera escritura y no hay "
                  "terminal. No se escribe.")
        return False
    print()
    print("  " + "=" * 66)
    print("  Primera escritura REAL de esta sesion.")
    print(f"  comando: {nombre}")
    print(f"  trama:   {hexa}")
    print("  " + "=" * 66)
    print()
    _SilenciarRutina.activo = True
    _SilenciarRutina.ocultadas = 0
    try:
        rta = await asyncio.to_thread(input, "  Escribir? [escribir/no]: ")
    except (EOFError, KeyboardInterrupt):
        return False
    finally:
        _SilenciarRutina.activo = False
        if _SilenciarRutina.ocultadas:
            print(f"  ({_SilenciarRutina.ocultadas} lineas de rutina "
                  "ocultadas mientras esperaba)")
    return rta.strip().lower() == "escribir"


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("linshark")
    for h in logging.getLogger().handlers:
        h.addFilter(_silenciador)

    conn = CONN_CHOICES[args.conn]
    model = p.MOUSE_NUM.get(args.device, f"id {args.device}")

    # Las guardas de HidrawBackend levantan ValueError con un mensaje pensado
    # para leerse. Sin este try salia como traceback, que es justo cuando menos
    # se lee: el que se equivoco con --permitir-escritura tiene que ver la
    # explicacion, no la pila.
    try:
        backend = _construir_backend(args, conn, model)
    except ValueError as exc:
        log.error("%s", exc)
        return 2

    if args.sin_chequeo_de_origen:
        origenes = None
        log.warning("filtro de Origin DESACTIVADO: cualquier pagina abierta en "
                    "el navegador puede hablarle al mouse")
    else:
        origenes = server.ORIGENES_PERMITIDOS + tuple(args.permitir_origen)

    recorder = server.Recorder(args.record) if args.record else None
    try:
        asyncio.run(server.run(backend, port=args.port, recorder=recorder,
                               origenes=origenes))
    except KeyboardInterrupt:
        return 0
    # `OSError` cubre la desconexion fisica del dongle a mitad de camino
    # (ENODEV, EIO): sin el, sacar el dongle imprime un traceback en vez del
    # mensaje. `PermissionError` es subclase suya, asi que alcanza con el.
    except (DeviceNotFound, OSError, ValueError) as exc:
        log.error("%s", exc)
        return 1
    finally:
        if recorder:
            recorder.close()
    return 0
