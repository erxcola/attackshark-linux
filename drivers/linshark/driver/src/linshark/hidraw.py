# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Acceso al canal de configuracion del mouse via /dev/hidraw."""

from __future__ import annotations

import asyncio
import errno
import logging
import os
from pathlib import Path

# Quien mira el bus entero -y sabe decir si lo que hay es el cable, o el dongle
# sin permisos, o nada- es `conexiones`. Aca queda el canal. No hay
# circularidad: `conexiones` no importa este modulo.
from . import conexiones as _conexiones

log = logging.getLogger("linshark.hidraw")

VENDOR_ID = 0x1D57
DONGLE_PRODUCT_ID = 0xFA65   # "2.4G 8K HS Receiver"
WIRED_PRODUCT_ID = 0x2126    # "X8PRO Mouse", cable
CONFIG_INTERFACE = 2         # la interfaz con la coleccion vendor 0xFF01

# Del descriptor HID del dongle, coleccion vendor 0xFF01:
# Report ID 4, 63 bytes de datos, IN y OUT. Es el canal de comandos.
REPORT_ID = 4
REPORT_SIZE = 63

# Coleccion vendor 0xFF00: Report ID 3, 4 bytes de entrada. El mouse lo manda
# solo, sin que nadie se lo pida, con [deviceId, marca 0x40, estadoBateria,
# nivelBateria]; es la materia prima del paquete de presencia que espera la
# pagina.
#
# **El latido tiene DOS cadencias, y las dos son metronomos.** MEDIDO con
# `driver/scripts/medir-hibernacion.py`, tres corridas:
#
#   * **2.00 s** con el mouse recien usado (43 huecos, rango 1.99..2.26)
#   * **4.00 s** a partir de ~32 s de quietud (179 huecos, rango 4.00..4.01)
#
# El salto entre las dos es un primer escalon de ahorro, anterior a la
# hibernacion. Vale la pena como leccion: este comentario decia "~4 s", la
# primera corrida (con el mouse EN USO) lo "corrigio" a 2.00 s, y las corridas
# con el mouse quieto mostraron que **las dos eran ciertas, de estados
# distintos**. Ninguna estaba completa, y la correccion tapo la mitad.
#
# Esa regularidad de metronomo es lo que lo vuelve util como instrumento: es el
# unico latido espontaneo que el mouse emite, asi que cuando para se nota, y
# escucharlo no le escribe nada. Y para de verdad -no se espacia: para-:
# MEDIDO a los 88 s de quietud con `--hibernacion 1`, y sin parar en 358 s con
# `--hibernacion 10`, en dos corridas que encierran a la primera.
REPORT_ID_ESTADO = 3
REPORT_ESTADO_SIZE = 4

SYS_HIDRAW = Path("/sys/class/hidraw")


class DeviceNotFound(Exception):
    pass


#: El comando que instala la regla de udev. Vive aca, y no dentro del mensaje,
#: para que una interfaz pueda ofrecerlo como un boton sin parsear texto.
COMANDO_UDEV = "sudo driver/scripts/instalar-udev.sh"


class FaltaLaReglaDeUdev(PermissionError):
    """No hay permiso sobre el nodo, y casi siempre es la regla de udev.

    **Sigue siendo un `PermissionError`**, asi que nada de lo que ya lo captura
    deja de funcionar. Es un tipo propio para que una interfaz pueda
    distinguirlo del resto de los errores de permisos y ofrecer el arreglo
    -en `comando`- en vez de mostrar un texto crudo. Lo pidio la auditoria del
    agente A como G-05.
    """

    def __init__(self, mensaje: str, *, path=None,
                 comando: str = COMANDO_UDEV):
        super().__init__(mensaje)
        self.path = path
        self.comando = comando


def _read(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def find_config_hidraw(
    vendor: int = VENDOR_ID,
    product: int = DONGLE_PRODUCT_ID,
    interface: int = CONFIG_INTERFACE,
) -> Path:
    """Encuentra el /dev/hidrawN de la interfaz de configuracion.

    Se busca recorriendo sysfs y no por numero fijo, porque la numeracion de
    hidraw cambia cada vez que se enchufa o desenchufa algo.

    **Cuando no lo encuentra, dice que fue lo que si vio.** Antes el error
    era siempre el mismo -"no encontre la interfaz 2 de
    1d57:fa65. Esta puesto el dongle?"- y mandaba a buscar al lugar
    equivocado en los dos casos mas comunes: el mouse enchufado **por cable**
    (que es otro dispositivo USB, y ademas se lleva el canal de radio) y el
    nodo ahi pero sin permisos. Eso ahora lo resuelve `conexiones.elegir()`,
    que mira el bus entero; con permisos faltantes levanta
    `FaltaLaReglaDeUdev`, que ya trae el comando del arreglo.
    """
    if (vendor, product, interface) == (VENDOR_ID, DONGLE_PRODUCT_ID,
                                        CONFIG_INTERFACE):
        try:
            conexion = _conexiones.elegir()
        except _conexiones.NoHayCanal as exc:
            if exc.por_permisos:
                sin_permiso = next(c for c in exc.conexiones
                                   if c.falta_la_regla_de_udev)
                raise FaltaLaReglaDeUdev(
                    f"{exc}. {COMANDO_UDEV} lo arregla",
                    path=sin_permiso.nodo_de_configuracion.path) from None
            raise DeviceNotFound(str(exc)) from None
        # **Este camino habla el framing del dongle**, y por cable la interfaz
        # 2 es otro protocolo. Devolver el nodo del cable aca seria mandarle
        # Output Reports del dongle a un endpoint que espera Feature Reports.
        if conexion.via != _conexiones.VIA_DONGLE:
            raise DeviceNotFound(
                f"{conexion.describir()}: esto habla solo por el dongle, y "
                "con el cable puesto el mouse no contesta por el dongle. Por "
                "cable se configura desde la ventana (driver/linshark-gui) y se "
                "respalda con driver/scripts/respaldar.py")
        return conexion.nodo_de_configuracion.path

    # El camino viejo, para cuando alguien pide otra cosa que el canal del
    # dongle: sigue existiendo porque `conexiones` solo sabe de los productos
    # que los perfiles declaran.
    candidates = []
    for entry in sorted(SYS_HIDRAW.glob("hidraw*")):
        usb_iface = entry / "device" / ".."          # interfaz USB
        if _read(usb_iface / "bInterfaceNumber") != f"{interface:02d}":
            continue
        usb_dev = usb_iface / ".."                    # dispositivo USB
        if int(_read(usb_dev / "idVendor") or "0", 16) != vendor:
            continue
        if int(_read(usb_dev / "idProduct") or "0", 16) != product:
            continue
        candidates.append(Path("/dev") / entry.name)

    if not candidates:
        raise DeviceNotFound(
            f"no encontre la interfaz {interface} de {vendor:04x}:{product:04x}. "
            "Esta puesto el dongle?"
        )
    if len(candidates) > 1:
        log.warning("varios candidatos (%s), uso el primero",
                    ", ".join(str(c) for c in candidates))
    return candidates[0]


def describir_nodo(path: Path) -> tuple[int, int, int] | None:
    """(vendor, product, interfaz) de un /dev/hidrawN, leidos de sysfs."""
    entry = SYS_HIDRAW / Path(path).name
    if not entry.exists():
        return None
    usb_iface = entry / "device" / ".."
    usb_dev = usb_iface / ".."
    iface = _read(usb_iface / "bInterfaceNumber")
    vendor = _read(usb_dev / "idVendor")
    product = _read(usb_dev / "idProduct")
    if not (iface and vendor and product):
        return None
    return int(vendor, 16), int(product, 16), int(iface, 10)


def verificar_nodo_dongle(path: Path) -> None:
    """Confirma que el nodo forzado a mano es el canal del dongle.

    Existe por --hidraw. Sin este chequeo se puede apuntar el puente a
    cualquier /dev/hidraw del sistema, y en particular al de la interfaz 2 del
    X8 Pro **por cable** (1d57:2126), donde el canal de configuracion NO es
    este: son Feature Reports de largo variable, no un Output Report ID 4.
    Mandarle ahi el framing del dongle es escribir bytes que nadie leyo nunca
    en un endpoint vendor, que es justo lo que el proyecto no hace.
    """
    info = describir_nodo(path)
    if info is None:
        raise DeviceNotFound(
            f"{path} no aparece en {SYS_HIDRAW}; no puedo verificar que sea el "
            "canal de configuracion del dongle"
        )
    vendor, product, iface = info
    if (vendor, product, iface) != (VENDOR_ID, DONGLE_PRODUCT_ID, CONFIG_INTERFACE):
        que = (f"{vendor:04x}:{product:04x} interfaz {iface}")
        extra = ""
        if (vendor, product) == (VENDOR_ID, WIRED_PRODUCT_ID):
            extra = (" Ese es el X8 Pro por CABLE, que se configura con Feature "
                     "Reports; este codigo no le sirve.")
        raise DeviceNotFound(
            f"{path} es {que}, y esto solo habla con "
            f"{VENDOR_ID:04x}:{DONGLE_PRODUCT_ID:04x} interfaz {CONFIG_INTERFACE} "
            f"(el dongle de 2.4 GHz).{extra}"
        )


class HidrawChannel:
    """Envoltorio asincronico sobre un /dev/hidraw."""

    def __init__(self, path: Path, solo_lectura: bool = False):
        self.path = path
        # En modo LISTEN el descriptor se abre O_RDONLY. No es redundante con
        # el chequeo de modo del backend: es la misma garantia pero sostenida
        # por el kernel, asi que ni un bug ni un camino de codigo olvidado
        # pueden mandarle un byte al mouse.
        self.solo_lectura = solo_lectura
        self._fd: int | None = None
        self._on_report = None
        self.on_desconexion = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def open(self) -> None:
        flags = (os.O_RDONLY if self.solo_lectura else os.O_RDWR) | os.O_NONBLOCK
        try:
            self._fd = os.open(self.path, flags)
        except PermissionError as exc:
            raise FaltaLaReglaDeUdev(
                f"sin permiso sobre {self.path}. Instala la regla de udev:\n"
                f"  {COMANDO_UDEV}\n"
                "que copia udev/70-attackshark-x8pro.rules y corre\n"
                "  udevadm control --reload-rules\n"
                "  udevadm trigger --action=add --subsystem-match=hidraw",
                path=self.path) from exc
        log.info("abierto %s (%s)", self.path,
                 "solo lectura" if self.solo_lectura else "lectura/escritura")

    def start_reading(self, loop: asyncio.AbstractEventLoop, on_report) -> None:
        assert self._fd is not None
        self._on_report = on_report
        self._loop = loop
        loop.add_reader(self._fd, self._drain)

    def _drain(self) -> None:
        assert self._fd is not None
        while True:
            try:
                data = os.read(self._fd, 256)
            except BlockingIOError:
                return
            except OSError as exc:
                if exc.errno in (errno.ENODEV, errno.EIO):
                    log.warning("el dispositivo desaparecio: %s", exc)
                    self.close()
                    # Sin avisar hacia arriba, el puente seguia mandandole a la
                    # pagina paquetes de presencia de un mouse que ya no esta.
                    if self.on_desconexion is not None:
                        self.on_desconexion()
                    return
                raise
            if not data:
                return
            if self._on_report is not None:
                self._on_report(data)

    def write_report(self, payload: bytes, report_id: int = REPORT_ID,
                     size: int = REPORT_SIZE) -> None:
        """Escribe un Output Report. El primer byte es el Report ID."""
        assert self._fd is not None, "el canal no esta abierto"
        self._exigir_escritura()
        if len(payload) > size:
            raise ValueError(f"payload de {len(payload)} B, el maximo es {size}")
        frame = bytes([report_id]) + payload.ljust(size, b"\x00")
        os.write(self._fd, frame)

    def write_frame(self, frame: bytes) -> None:
        """Escribe la trama tal cual, sin rellenar.

        El helper oficial manda exactamente 12 bytes en los comandos de
        lectura (se ve en el `push 0xc` antes de cada hid_write), no un
        report entero relleno de ceros.
        """
        assert self._fd is not None, "el canal no esta abierto"
        self._exigir_escritura()
        os.write(self._fd, frame)

    def _exigir_escritura(self) -> None:
        if self.solo_lectura:
            raise PermissionError(
                f"{self.path} se abrio en solo lectura (modo listen): "
                "no se le escribe nada al mouse"
            )

    def close(self) -> None:
        if self._fd is None:
            return
        if self._loop is not None:
            try:
                self._loop.remove_reader(self._fd)
            except ValueError:
                pass
        os.close(self._fd)
        self._fd = None
        self._loop = None
