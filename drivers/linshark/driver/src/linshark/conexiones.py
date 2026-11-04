# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Donde esta el mouse: por que camino, en que puerto, y con que permisos.

Antes el codigo tenia una sola pregunta -"cual es el
/dev/hidrawN de la interfaz 2 del dongle"- y una sola respuesta cuando no
estaba: *"no encontre la interfaz 2 de 1d57:fa65. Esta puesto el dongle?"*.
Eso es falso la mitad de las veces: el dongle puede estar puesto y el mouse
estar **enchufado por cable**, que es otro dispositivo USB (`1d57:2126`), o el
nodo puede existir y no tener permisos. Decir "no esta" cuando lo que pasa es
otra cosa manda a buscar al lugar equivocado.

Este modulo mira **el bus entero** y dice lo que hay. Tres cosas que conviene
tener claras:

  * **no abre ningun nodo y no le escribe nada al mouse.** Todo sale de
    `/sys/class/hidraw` y de los atributos que el kernel ya tiene leidos, asi
    que se puede correr mientras hay una medicion andando sin ensuciarla;
  * **el camino no lo dice el mouse, lo dice el bus.** El paquete de presencia
    del Report ID 3 trae `[deviceId, 0x40, bateria...]` y **no** trae el modo
    de conexion: en el cliente oficial ese campo (`connectionMethod`, 128
    cable / 129 inalambrico / 130-131 cable 8K / 132 bluetooth) lo agrega su
    helper, que lo sabe por el dispositivo USB del que leyo, no por lo que el
    mouse le manda (LEIDO del bundle);
  * **los ids son del perfil**, no de este archivo: `Perfil.usb` dice cual es
    el producto del dongle y cual el del cable para cada modelo medido.

Por cable el canal de configuracion es **otro** -Feature Reports, ver
`dev/models/attackshark-x8pro/docs/hardware.md`- y lo habla `cable.CableDevice`. La interfaz es la misma
numero 2, asi que **quien abre el nodo tiene que mirar `via`**: mandarle el
framing del dongle al nodo del cable es escribir bytes que nadie leyo nunca en
un endpoint vendor (`hidraw.find_config_hidraw` se niega a devolverlo).

**Y si estan los dos, manda el cable**: con el cable puesto el mouse deja de
hablar por el dongle (MEDIDO), asi que el nodo del dongle abre y no contesta
nadie. `buscar()` pone el cable primero, y `elegir()` lo elige.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import dispositivos

#: Donde el kernel publica los nodos hidraw, y donde viven los nodos. Los dos
#: se pueden cambiar para las pruebas, que arman un sysfs de mentira en un
#: directorio temporal -con eso se prueban los casos que no se pueden pedir a
#: mano: el dongle desenchufado, el nodo sin permisos, el mouse solo por
#: cable-.
SYS_HIDRAW = Path("/sys/class/hidraw")
DEV = Path("/dev")

#: Por que camino esta hablando el mouse. Los nombres viven en `dispositivos`,
#: porque hay codigo que decide por la via sin mirar el bus.
VIA_DONGLE = dispositivos.VIA_DONGLE
VIA_CABLE = dispositivos.VIA_CABLE
VIA_DESCONOCIDA = dispositivos.VIA_DESCONOCIDA

VIA_LEGIBLE = {
    VIA_DONGLE: "por el dongle de 2.4 GHz",
    VIA_CABLE: "por el cable USB",
    VIA_DESCONOCIDA: "por un dispositivo que no reconozco",
}


def _leer(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def _entero(path: Path, base: int = 10) -> int | None:
    crudo = _leer(path)
    try:
        return int(crudo, base)
    except ValueError:
        return None


@dataclass(frozen=True)
class Nodo:
    """Un `/dev/hidrawN` de un dispositivo, con lo que se puede hacer con el."""

    path: Path
    interfaz: int
    #: Si el usuario que corre esto puede leerlo y escribirlo. Con la regla de
    #: udev puesta da `(True, True)`; sin ella, `(False, False)` y el nodo
    #: existe igual -que es justo el caso que antes se confundia con "no esta
    #: el dongle"-.
    legible: bool
    escribible: bool

    @property
    def sin_permiso(self) -> bool:
        return not (self.legible and self.escribible)


@dataclass(frozen=True)
class Conexion:
    """Un dispositivo del bus que es un mouse de esta familia.

    Es **un dispositivo USB**, no un nodo: el dongle publica cuatro interfaces
    y solo una es el canal de configuracion.
    """

    via: str
    vendor: int
    producto: int
    #: Lo que declara el propio dispositivo, sin adornar.
    fabricante: str
    nombre_usb: str
    #: Donde esta enchufado. `puerto` es como lo nombra el kernel -"1-2", o
    #: "1-4.3" si hay un hub en el medio-, y es lo que hay que mirar para saber
    #: si algo cambio de lugar.
    bus: int | None
    dispositivo: int | None
    puerto: str
    ruta: Path
    #: 480 con el dongle (High Speed) y 12 por cable (Full Speed), que es la
    #: razon por la que los 8 kHz solo salen por el dongle.
    velocidad: int | None
    nodos: tuple[Nodo, ...]
    #: El perfil del modelo, si es uno que tenemos medido.
    perfil: object | None = None

    @property
    def modelo(self) -> str:
        return getattr(self.perfil, "nombre", "") or "desconocido"

    def nodo(self, interfaz: int) -> Nodo | None:
        for n in self.nodos:
            if n.interfaz == interfaz:
                return n
        return None

    @property
    def nodo_de_configuracion(self) -> Nodo | None:
        """El nodo del canal de comandos, si este camino tiene uno usable.

        **Por los dos caminos es la interfaz 2, y adentro hay protocolos
        distintos**: Output Report 4 por el dongle, Feature Reports por cable.
        El nodo no alcanza para hablarle: hace falta `via`.
        """
        if self.via not in (VIA_DONGLE, VIA_CABLE) or self.perfil is None:
            return None
        return self.nodo(self.perfil.usb.interfaz)

    @property
    def se_puede_configurar(self) -> bool:
        nodo = self.nodo_de_configuracion
        return nodo is not None and not nodo.sin_permiso

    @property
    def falta_la_regla_de_udev(self) -> bool:
        nodo = self.nodo_de_configuracion
        return nodo is not None and nodo.sin_permiso

    @property
    def tasas(self) -> tuple[int, ...]:
        """Las tasas que se pueden pedir **por este camino**.

        Por el dongle son las del perfil; por cable el descriptor no da mas de
        1000 Hz -Full Speed, `bInterval` de 1 ms- y ofrecer 8000 ahi seria
        ofrecer un control que no puede hacer lo que dice.
        """
        if self.perfil is None:
            return ()
        if self.via == VIA_CABLE:
            techo = self.perfil.tasa_maxima_por_cable
            return tuple(hz for hz in self.perfil.tasas if hz <= techo)
        return tuple(self.perfil.tasas)

    def describir(self) -> str:
        """Una linea: que es, por donde, y donde esta enchufado."""
        donde = f"puerto {self.puerto}" if self.puerto else "puerto desconocido"
        if self.bus is not None and self.dispositivo is not None:
            donde += f" (bus {self.bus:03d} dispositivo {self.dispositivo:03d})"
        return (f"{self.modelo} {VIA_LEGIBLE.get(self.via, self.via)}, "
                f"{donde}")


def _perfiles_por_producto() -> dict[tuple[int, int], tuple[object, str]]:
    """`(vendor, producto) -> (perfil, via)`, de los modelos medidos."""
    tabla: dict[tuple[int, int], tuple[object, str]] = {}
    for perfil in dispositivos.PERFILES.values():
        usb = perfil.usb
        tabla[(usb.vendor, usb.producto_dongle)] = (perfil, VIA_DONGLE)
        if usb.producto_cable is not None:
            tabla[(usb.vendor, usb.producto_cable)] = (perfil, VIA_CABLE)
    return tabla


def _vendors_conocidos() -> set[int]:
    return {perfil.usb.vendor for perfil in dispositivos.PERFILES.values()}


def buscar(raiz: Path | None = None, dev: Path | None = None) -> list[Conexion]:
    """Los mouses de esta familia que hay ahora mismo en el bus.

    Recorre los nodos hidraw y los agrupa por dispositivo USB, que es lo que a
    una persona le importa: un dongle son cuatro nodos y **un** dispositivo.
    Lo que no es de un vendor conocido no se mira.
    """
    raiz = Path(raiz) if raiz is not None else SYS_HIDRAW
    dev = Path(dev) if dev is not None else DEV
    por_producto = _perfiles_por_producto()
    vendors = _vendors_conocidos()
    encontradas: dict[Path, dict] = {}

    for entrada in sorted(raiz.glob("hidraw*")):
        interfaz_usb = entrada / "device" / ".."
        dispositivo_usb = interfaz_usb / ".."
        vendor = _entero(dispositivo_usb / "idVendor", 16)
        producto = _entero(dispositivo_usb / "idProduct", 16)
        if vendor is None or producto is None or vendor not in vendors:
            continue
        interfaz = _entero(interfaz_usb / "bInterfaceNumber")
        if interfaz is None:
            continue
        # La clave es el dispositivo USB, resuelto: dos nodos del mismo dongle
        # tienen que caer en la misma conexion.
        try:
            clave = dispositivo_usb.resolve()
        except OSError:                              # pragma: no cover
            continue
        nodo_dev = dev / entrada.name
        datos = encontradas.setdefault(clave, {"nodos": []})
        datos["nodos"].append(Nodo(
            nodo_dev, interfaz,
            legible=os.access(nodo_dev, os.R_OK),
            escribible=os.access(nodo_dev, os.W_OK)))
        if "vendor" in datos:
            continue
        perfil, via = por_producto.get((vendor, producto), (None,
                                                            VIA_DESCONOCIDA))
        datos.update(
            vendor=vendor, producto=producto, perfil=perfil, via=via,
            fabricante=_leer(dispositivo_usb / "manufacturer"),
            nombre_usb=_leer(dispositivo_usb / "product"),
            bus=_entero(dispositivo_usb / "busnum"),
            dispositivo=_entero(dispositivo_usb / "devnum"),
            puerto=clave.name,
            velocidad=_entero(dispositivo_usb / "speed"))

    salida = []
    for clave, datos in encontradas.items():
        if "vendor" not in datos:                    # pragma: no cover
            continue
        salida.append(Conexion(
            via=datos["via"], vendor=datos["vendor"], producto=datos["producto"],
            fabricante=datos["fabricante"], nombre_usb=datos["nombre_usb"],
            bus=datos["bus"], dispositivo=datos["dispositivo"],
            puerto=datos["puerto"], ruta=clave, velocidad=datos["velocidad"],
            nodos=tuple(sorted(datos["nodos"], key=lambda n: n.interfaz)),
            perfil=datos["perfil"]))
    # **El cable primero.** Con el cable puesto el mouse no habla por el dongle
    # (MEDIDO), asi que si estan los dos, el que contesta es el cable.
    orden = {VIA_CABLE: 0, VIA_DONGLE: 1}
    salida.sort(key=lambda c: (orden.get(c.via, 2), c.puerto))
    return salida


class NoHayCanal(Exception):
    """No hay ningun camino por el que se pueda configurar el mouse.

    Trae **lo que si se vio** en `conexiones`, para que quien lo muestre no
    tenga que volver a buscar ni que parsear el texto.
    """

    def __init__(self, mensaje: str, *, conexiones: list[Conexion] | None = None,
                 por_permisos: bool = False):
        super().__init__(mensaje)
        self.conexiones = conexiones or []
        #: `True` cuando el dongle esta y lo unico que falta es la regla de
        #: udev. Lo mira la ventana para ofrecer el boton en vez de un texto.
        self.por_permisos = por_permisos


def elegir(conexiones: list[Conexion] | None = None) -> Conexion:
    """La conexion por la que se puede configurar, o un error que explica.

    **Si estan el cable y el dongle, elige el cable**, que es el que contesta
    (ver `buscar()`). El error **dice lo que hay**: si el mouse esta pero sin
    permisos, lo dice y trae el comando de la regla de udev; y si no hay nada de
    esta familia en el bus, eso tambien es una respuesta distinta.
    """
    conexiones = buscar() if conexiones is None else conexiones
    for conexion in conexiones:
        if conexion.se_puede_configurar:
            return conexion

    sin_permiso = [c for c in conexiones if c.falta_la_regla_de_udev]
    if sin_permiso:
        # El mensaje se arma con una variable por dato -el puerto y el nodo- y
        # no con `describir()` adentro: asi la ventana lo puede traducir con
        # una plantilla, en vez de tener que rearmar el texto.
        quien = ("el dongle" if sin_permiso[0].via == VIA_DONGLE
                 else "el mouse por cable")
        raise NoHayCanal(
            f"{quien} esta en el puerto {sin_permiso[0].puerto}, pero "
            f"{sin_permiso[0].nodo_de_configuracion.path} no se puede abrir: "
            "faltan los permisos del nodo",
            conexiones=conexiones, por_permisos=True)

    raise NoHayCanal(
        "no hay ningun mouse de esta familia en el bus USB: ni el dongle de "
        "2.4 GHz ni el mouse por cable. Esta puesto el dongle?",
        conexiones=conexiones)


def describir(conexiones: list[Conexion] | None = None) -> str:
    """Todo lo que hay, en texto, para el CLI y para un informe."""
    conexiones = buscar() if conexiones is None else conexiones
    if not conexiones:
        return "No hay ningun mouse de esta familia en el bus USB."
    lineas = []
    for c in conexiones:
        lineas.append(c.describir())
        detalle = [f"{c.vendor:04x}:{c.producto:04x}"]
        if c.fabricante or c.nombre_usb:
            detalle.append(f"{c.fabricante} {c.nombre_usb}".strip())
        if c.velocidad:
            detalle.append(f"{c.velocidad} Mbps")
        lineas.append("    " + " · ".join(detalle))
        for nodo in c.nodos:
            # **El diagnostico de udev va solo en el canal de configuracion.**
            # Las otras interfaces son las del mouse y el teclado; que esten
            # cerradas es lo normal y no hace falta ninguna regla para ellas.
            # Decir "falta la regla" en las cuatro seria una alarma falsa por
            # cada nodo que no usamos.
            es_el_canal = nodo is c.nodo_de_configuracion
            if not nodo.sin_permiso:
                permisos = "lectura y escritura"
            elif es_el_canal:
                permisos = "SIN PERMISO: falta la regla de udev"
            else:
                permisos = "sin permiso (no hace falta: no lo usamos)"
            marca = "  <- canal de configuracion" if es_el_canal else ""
            lineas.append(f"    interfaz {nodo.interfaz}: {nodo.path} "
                          f"[{permisos}]{marca}")
    return "\n".join(lineas)
