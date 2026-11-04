# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Servidor WebSocket que se hace pasar por el helper nativo de szslxd-tech.

El helper oficial (WebDriverSetup.exe / WebDriverForMac.pkg) escucha en
ws://localhost:10086 y solo existe para Windows y macOS. Esto lo reemplaza.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from websockets.asyncio.server import ServerConnection, serve

from . import protocol as p
from .backend import Backend

log = logging.getLogger("linshark")

DEFAULT_PORT = 10086
DEFAULT_HOSTS = ("127.0.0.1", "::1")

# El puente escucha en un puerto de localhost, y desde el navegador eso lo
# puede abrir CUALQUIER pagina, no solo la del fabricante (Chromium trata
# ws://localhost como origen confiable y no pide CORS). Sin este filtro,
# cualquier sitio que el usuario tenga abierto en otra pestana puede hablarle
# al mouse. El navegador pone el header Origin y el JavaScript de la pagina no
# lo puede falsificar, asi que alcanza con mirarlo.
#
# Un cliente que NO es navegador (curl, un script local) directamente no manda
# Origin. A ese no lo bloqueamos: ya corre en la maquina del usuario y tiene el
# /dev/hidraw a mano, filtrarlo no agregaria seguridad y romperia las sondas.
ORIGENES_PERMITIDOS = (
    "https://szslxd-tech.com",
    "http://szslxd-tech.com",
)


class Recorder:
    """Guarda todo el trafico a un JSONL, para analizarlo despues.

    Es la herramienta principal de la fase 0: abris la web, tocas un control,
    y queda registrado exactamente que bytes manda. Eso es lo que hay que
    saber para escribir el backend de hidraw.
    """

    def __init__(self, path: Path):
        self.path = path
        self._fh = path.open("a", encoding="utf-8")
        self._t0 = time.monotonic()

    def write(self, direction: str, text: str, note: str = "") -> None:
        entry = {
            "t": round(time.monotonic() - self._t0, 4),
            "dir": direction,          # "rx" = pagina -> puente, "tx" = puente -> pagina
            "hex": text,
            "len": len(text) // 2,
            "note": note,
        }
        self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


class Bridge:
    def __init__(self, backend: Backend, recorder: Recorder | None = None,
                 origenes=ORIGENES_PERMITIDOS):
        self.backend = backend
        self.recorder = recorder
        # origenes=None desactiva el filtro (para probar contra una copia local
        # del bundle servida desde otro dominio).
        self.origenes = tuple(origenes) if origenes else None

    def _origen_permitido(self, origen: str | None) -> bool:
        if self.origenes is None or origen is None:
            return True
        return origen in self.origenes

    async def __call__(self, conn: ServerConnection) -> None:
        origen = conn.request.headers.get("Origin") if conn.request else None
        if not self._origen_permitido(origen):
            log.warning("conexion RECHAZADA, Origin no permitido: %s", origen)
            await conn.close(1008, "origen no permitido")
            return
        log.info("pagina conectada (Origin: %s)", origen or "sin Origin")

        async def emit(text: str) -> None:
            await conn.send(text)
            note = self._describe_tx(text)
            log.info("  -> %-24s %s", text, note)
            if self.recorder:
                self.recorder.write("tx", text, note)

        # Una lectura puede tardar decenas de segundos (8 reintentos, y el NAK
        # del dongle llega recien a los 2.10 s). Si la pagina se va en el medio
        # -- y se va seguido: recargas, dos pestanas -- no tiene sentido
        # seguir pidiendole cosas al mouse para nadie. Se corre cada pedido en
        # una tarea y se hace una carrera contra el cierre de la conexion.
        cierre = asyncio.create_task(conn.wait_closed())
        pendiente: asyncio.Task | None = None
        try:
            await self.backend.start(emit)
            async for message in conn:
                if isinstance(message, bytes):
                    # La pagina siempre manda texto; si llega binario es que
                    # entendimos mal algo.
                    log.warning("  <- frame BINARIO inesperado: %s", message.hex())
                    continue
                try:
                    raw = p.decode(message)
                except ValueError:
                    # La pagina siempre manda hexadecimal; si llega otra cosa
                    # es que hay algo mal del otro lado. Se descarta la trama,
                    # pero la conexion sigue: antes esto se llevaba puesta la
                    # sesion entera con un ValueError sin capturar.
                    log.warning("  <- descarto trama no hexadecimal: %.60r", message)
                    continue
                if not raw:
                    continue
                request = p.Request(raw)
                note = request.describe()
                if request.malformado:
                    log.warning("  <- %-24s %s", message, note)
                    if self.recorder:
                        self.recorder.write("rx", message, note)
                    continue
                log.info("  <- %-24s %s", message, note)
                if self.recorder:
                    self.recorder.write("rx", message, note)
                pendiente = asyncio.create_task(self.backend.handle(request, emit))
                listas, _ = await asyncio.wait(
                    {pendiente, cierre}, return_when=asyncio.FIRST_COMPLETED)
                if pendiente not in listas:
                    log.info("  la pagina se fue; abandono %s", note)
                    break
                pendiente.result()   # propaga lo que haya fallado adentro
                pendiente = None
        finally:
            if pendiente is not None and not pendiente.done():
                pendiente.cancel()
            cierre.cancel()
            await self.backend.stop()
            log.info("pagina desconectada")

    @staticmethod
    def _describe_tx(text: str) -> str:
        raw = p.decode(text)
        if len(raw) == 2:
            return f"version del helper {raw[0]}.{raw[1]}"
        if (len(raw) == 7 and 0x80 <= raw[0] <= 0x85 and raw[1] == 0x01
                and raw[4] in (p.NOTIF_PRESENCIA, p.NOTIF_PRESENCIA_ALT)):
            model = p.MOUSE_NUM.get(raw[3], f"id {raw[3]}")
            conn = p.CONN_NAMES.get(raw[0], hex(raw[0]))
            return f"presencia: {model} via {conn}, bateria {raw[6]}%"
        if len(raw) == 6 and 0x80 <= raw[0] <= 0x85 and raw[1] == 0x01:
            tipo = p.NOTIF_NOMBRES.get(raw[3], f"tipo 0x{raw[3]:02x}")
            model = p.MOUSE_NUM.get(raw[2], f"id {raw[2]}")
            return f"notificacion de {model}: {tipo}"
        if len(raw) == 5 and raw[2] == p.CMD_ACK:
            return "ack ok" if raw[3] == 0 else "ack error (la pagina reintenta)"
        if len(raw) == 3 and raw[1] == 0:
            return f"desconexion del dispositivo {raw[2]}"
        if len(raw) >= 6 and 0x80 <= raw[0] <= 0x85:
            # [conn, deviceId, cmd, sub, ...datos]
            nombre = p.CMD_NAMES.get(raw[2], f"cmd {raw[2]}")
            return f"respuesta de {nombre} (sub={raw[3]}), {len(raw) - 4} B de datos"
        return "?"


async def run(
    backend: Backend,
    port: int = DEFAULT_PORT,
    hosts=DEFAULT_HOSTS,
    recorder: Recorder | None = None,
    origenes=ORIGENES_PERMITIDOS,
) -> None:
    bridge = Bridge(backend, recorder, origenes=origenes)
    async with serve(bridge, list(hosts), port):
        log.info("escuchando en ws://localhost:%d  (%s)", port, ", ".join(hosts))
        log.info("abri https://szslxd-tech.com/#/ en Brave y recarga la pagina")
        await asyncio.get_running_loop().create_future()
