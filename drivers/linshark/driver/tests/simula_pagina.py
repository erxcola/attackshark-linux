#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Simula al cliente real: reimplementa la logica del store de la web.

Esto NO es un mock complaciente. Cada chequeo de abajo es una transcripcion
del JavaScript minificado de szslxd-tech.com (dev/research/webapp/app.js), asi
que si el puente pasa este test, la pagina de verdad deberia aceptarlo.

    $ python3 driver/tests/simula_pagina.py
"""

from __future__ import annotations

import asyncio
import sys
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

from linshark import protocol as p  # noqa: E402
from linshark import server  # noqa: E402
from linshark.backend import StubBackend  # noqa: E402

PORT = 10186  # puerto distinto al real, para no chocar con un puente andando


class StoreSimulado:
    """Transcripcion del pinia store de la pagina, solo lo que importa aca."""

    def __init__(self):
        self.version = [3, 5]
        self.mouseArr: list[dict] = []
        self.deviceNo = None
        self.deviceFlag = False
        self.highSpeedFlag = 0
        self.readFlag = False
        self.versionTipShow = False
        self.route = None

    # --- fiel a: this.socket.onmessage ---
    def onmessage(self, data: str) -> None:
        n = p.decode(data)

        # if (n.length == 2) -> version del helper
        if len(n) == 2:
            major, minor = n[0], n[1]
            if major < 3 or (major == 3 and minor == 0):
                self.readFlag = True
            if self.version != n:
                self.versionTipShow = True
            return

        # presencia: (n.length===7||n.length===6) && n[0]>=128 && n[0]<=133
        if len(n) in (6, 7) and 128 <= n[0] <= 133:
            # if (n[4]!==64 && n[4]!==65 && n.length===7 ||
            #     n[3]!==64 && n[3]!==65 && n.length===6) return
            if (n[4] not in (64, 65) and len(n) == 7) or \
               (n[3] not in (64, 65) and len(n) == 6):
                return
            if len(n) == 7:
                dev, batt_status, batt_level = n[3], n[5], n[6]
            else:
                dev, batt_status, batt_level = n[2], n[4], n[5]
            if dev not in p.MOUSE_NUM:
                return
            found = next((m for m in self.mouseArr if m["deviceId"] == dev), None)
            if found:
                found["connectionMethod"] = n[0]
                found["batteryStatus"] = batt_status
                found["batteryLevel"] = batt_level
            else:
                self.mouseArr.append({
                    "deviceId": dev, "connectionMethod": n[0],
                    "batteryStatus": batt_status, "batteryLevel": batt_level,
                })
            self.setDevice(n)
            return

        # ack: n.length===5 && n[2]===80 && n[3]===0
        if len(n) == 5 and n[2] == 80:
            self.last_ack_ok = (n[3] == 0)
            return

    # --- fiel a: setDevice(e) ---
    def setDevice(self, e: list[int]) -> None:
        t, conn, a = len(e), e[0], e[1]
        o = e[3] if t == 7 else e[2]
        if a != 1:
            return
        if conn == 128:
            self._set(o, wired_8k=False)
        elif conn == 129:
            self._set(o, wired_8k=False)
        elif conn in (130, 131):
            self._set(o, wired_8k=True)
        elif conn == 132 and t == 6:
            self._set(o, wired_8k=False)
        elif conn == 133:
            self._set(o, wired_8k=True)

    def _set(self, dev: int, wired_8k: bool) -> None:
        if dev not in p.MOUSE_NUM or self.deviceFlag:
            return
        self.deviceNo = dev
        self.deviceFlag = True
        if wired_8k:
            self.highSpeedFlag = 1
        self.selectDevice()

    # --- fiel a: selectDevice() para deviceNo === 8 ---
    def selectDevice(self) -> None:
        rutas = {6: "/ATTACKSHARK/factoryX8Plus",
                 8: "/ATTACKSHARK/factoryX8Pro",
                 2: "/ATTACKSHARK/factoryX8SE"}
        self.route = rutas.get(self.deviceNo, f"/desconocida({self.deviceNo})")


async def escenario(conn_name: str, conn_value: int, espera_8k: bool) -> list[str]:
    fallos = []
    backend = StubBackend(connection_method=conn_value, device_id=p.DEVICE_X8_PRO,
                          presence_period=3600)
    bridge = server.Bridge(backend)
    async with server.serve(bridge, ["127.0.0.1"], PORT):
        async with connect(f"ws://127.0.0.1:{PORT}") as ws:
            store = StoreSimulado()
            for _ in range(2):  # version + presencia
                store.onmessage(await asyncio.wait_for(ws.recv(), timeout=3))

            if store.versionTipShow:
                fallos.append("la pagina pediria actualizar el driver")
            if store.readFlag:
                fallos.append("la pagina desactivaria las lecturas")
            if not store.deviceFlag:
                fallos.append("no reconocio ningun dispositivo")
            if store.deviceNo != p.DEVICE_X8_PRO:
                fallos.append(f"deviceNo={store.deviceNo}, esperaba 8")
            if store.route != "/ATTACKSHARK/factoryX8Pro":
                fallos.append(f"ruteo a {store.route}")
            if store.highSpeedFlag != (1 if espera_8k else 0):
                fallos.append(f"highSpeedFlag={store.highSpeedFlag}, "
                              f"esperaba {1 if espera_8k else 0}")
            if not store.mouseArr or store.mouseArr[0]["batteryLevel"] != 100:
                fallos.append(f"mouseArr mal poblado: {store.mouseArr}")

            # una escritura tiene que volver con ack ok
            store.last_ack_ok = None
            await ws.send(p.encode([conn_value, 8, 12, 7, 8, 0, 0, 0, 0, 0]))
            store.onmessage(await asyncio.wait_for(ws.recv(), timeout=3))
            if store.last_ack_ok is not True:
                fallos.append(f"ack de escritura: {store.last_ack_ok}")

    return fallos


async def main() -> int:
    casos = [
        ("2.4 GHz", p.CONN_WIRELESS, False),
        ("8 kHz (0x83)", p.CONN_8K_B, True),
        ("8 kHz (0x85)", p.CONN_8K_C, True),
        ("cable", p.CONN_WIRED, False),
    ]
    malos = 0
    for nombre, valor, espera_8k in casos:
        fallos = await escenario(nombre, valor, espera_8k)
        if fallos:
            malos += 1
            print(f"FALLA  {nombre}")
            for f in fallos:
                print(f"         - {f}")
        else:
            print(f"ok     {nombre}  -> /ATTACKSHARK/factoryX8Pro"
                  f"{'  (8 kHz habilitado)' if espera_8k else ''}")
    print()
    print("todo en orden" if malos == 0 else f"{malos} escenario(s) con problemas")
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
