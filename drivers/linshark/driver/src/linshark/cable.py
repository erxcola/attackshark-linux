# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""El canal de configuracion por CABLE, con la misma cara que `Device`.

Por cable el mouse es otro dispositivo USB (`1d57:2126`) y no hay dongle en el
medio: el canal son **Feature Reports** por el endpoint de control, y el
report es **el mismo bloque** que viaja adentro de la trama del dongle -`[cmd,
sizeTotalData, perfil, campos..., checksum interno]`-, sin el `04 L 00` de
afuera ni su checksum. Todo sale de `dev/models/attackshark-x8pro/docs/protocolo.md`, "El canal por
CABLE": LEIDO del helper de la web y MEDIDO en las seis capturas del soft
nativo (`dev/models/attackshark-x8pro/docs/capturas-w/cable-soft-*.pcap`).

`CableDevice` tiene los mismos metodos que `Device` -`leer`, `escribir`,
`escribir_por_bloques`- para que la sesion y la ventana no se enteren del
camino. Lo que cambia por dentro:

  * **leer** es un pedido `SET_FEATURE(0xA0)`, esperar a que el `GET(0xA0)`
    diga listo, y el `GET_FEATURE` del bloque. Sin el pedido el mouse no
    contesta (MEDIDO: ocho timeouts en `dev/models/attackshark-x8pro/respaldos/cable-primera-lectura.json`);
  * **escribir** es un `SET_FEATURE` del bloque cortado al largo que el mouse
    declara en su descriptor (52 el dpi, 9 el rate, 59 los botones);
  * **no hay acuse `0xC1`**: no hay dongle que lo mande. Lo que hay es que el
    mouse acepte la transferencia o la rechace con STALL. Que la haya
    **aplicado** lo dice la relectura, como siempre -tampoco el `0xC1` lo decia-;
  * **el STALL se reintenta con el mismo report** ~205 ms despues, que es lo
    que se vio en el bus: 6 de 19 pedidos rechazados, los seis aceptados al
    segundo intento;
  * **el macro se pide con su id** en el byte 4 del pedido, donde los demas
    llevan el perfil (LEIDO: la misma variable que el helper pone donde el
    dongle lleva el id, que ahi esta MEDIDO), y se escribe en dos trozos de
    64, como el soft (MEDIDO en `cable-soft-macros.pcap`).

Los pedidos de lectura de botones, perfil completo y version **no se vieron en
el bus** -el soft, al abrirse, lee solo rate, dpi y luz-: estan LEIDOS del
helper, como permite la regla de `AGENTS.md`. Uno que el mouse no conteste no
rompe nada: no hay respuesta, y el respaldo queda incompleto.
"""

from __future__ import annotations

import asyncio
import collections
import errno
import fcntl
import logging
import os
import time
from pathlib import Path

from . import dispositivos
from . import estructuras
from . import protocol as p
from .device import Frame

log = logging.getLogger("linshark.cable")

SYS_HIDRAW = Path("/sys/class/hidraw")

# --- los ioctl de Feature Reports de hidraw ---------------------------------
# `HIDIOCSFEATURE(len)` y `HIDIOCGFEATURE(len)` de `linux/hidraw.h`: los dos
# con direccion lectura+escritura (el buffer va y vuelve), tipo 'H', numeros
# 0x06 y 0x07. El largo va adentro del numero del ioctl, y el kernel lo pone tal
# cual como `wLength` de la transferencia de control: por eso el largo de cada
# report importa y sale del descriptor, no de nosotros.
_IOC_WRITE, _IOC_READ = 1, 2


def _ioc_feature(numero: int, largo: int) -> int:
    return (((_IOC_READ | _IOC_WRITE) << 30) | (largo << 16)
            | (ord("H") << 8) | numero)


def HIDIOCSFEATURE(largo: int) -> int:     # noqa: N802 - el nombre del kernel
    return _ioc_feature(0x06, largo)


def HIDIOCGFEATURE(largo: int) -> int:     # noqa: N802
    return _ioc_feature(0x07, largo)


# --- los tiempos, del bus ---------------------------------------------------
# Lo que hizo el soft en `cable-soft-abrir.pcap`: el `GET(0xA0)` ~320 ms
# despues del pedido, y el `GET` del bloque ~110 ms despues de eso. El helper
# espera 500 y 100 (LEIDO); se usa lo medido.
ESPERA_TRAS_PEDIDO = 0.32
ESPERA_TRAS_LISTO = 0.11
#: Si el `GET(0xA0)` todavia no dice listo, se vuelve a mirar. El soft no lo
#: necesito nunca en las seis capturas; el helper lo mira una sola vez.
REINTENTOS_DE_LISTO = 10
PAUSA_DE_LISTO = 0.1

#: El reintento de un `SET` rechazado con STALL: **el mismo report**, ~205 ms
#: despues (MEDIDO: entre 201 y 209 ms, los seis aceptados al segundo). Se
#: dan algunos mas por las dudas; el helper insiste hasta 10 con el pedido.
PAUSA_TRAS_STALL = 0.205
INTENTOS_POR_STALL = 5

#: **El respiro despues de escribir, antes de mandar cualquier otra cosa.**
#: El helper hace `Sleep(500)` despues de cada escritura (0x40d1f4, LEIDO), y
#: el soft nunca manda nada antes de ~200 ms de haber escrito -en las seis
#: capturas, las escrituras seguidas van a 202..208 ms- ni relee despues de
#: escribir. Sin este respiro, la primera corrida contra el mouse
#: (2026-09-18) escribio el LOD y la respuesta, el mouse los acepto, y la
#: relectura -que salia a los pocos milisegundos- los mostro sin cambiar; la
#: tasa, que se relee 1 s despues (`sesion.poner_tasa`), si entro (MEDIDO con
#: `medir-polling.py`). La lectura razonable es que un pedido que llega
#: enseguida pisa la escritura antes de que el mouse la aplique: el mouse
#: parece tener **un solo buffer** para todos los reports -un `GET(6)` le
#: devolvio el bloque de la version- y es INFERIDO, no medido.
PAUSA_TRAS_ESCRITURA = 0.5
#: Y entre una lectura y el pedido siguiente, lo que dejo el soft: 112..175 ms.
PAUSA_ENTRE_PEDIDOS = 0.12
#: Si el `GET` devuelve algo que no es el bloque pedido -el buffer todavia
#: tenia otra cosa-, se vuelve a pedir el bloque entero, hasta esta cantidad de
#: veces.
PEDIDOS_POR_BLOQUE_AJENO = 3

#: Cuantos bytes tienen que coincidir -**despues del `profileId`**- para decir
#: que un bloque es el anterior (`_es_el_bloque_anterior`). Con menos no se
#: afirma. Con cuatro no hay un solo falso positivo en los 147 respaldos sanos,
#: y se detectan los tres que se sabe corrompidos.
MINIMO_PARA_RECONOCER = 4


def _es_el_bloque_anterior(cmd: int, report: bytes, anterior) -> bool:
    """Si lo que volvio es el payload del bloque que el mouse sirvio antes.

    **MEDIDO** con `medir-sangrado.py`: de los seis sangrados de una corrida de
    240 pedidos, los seis eran el bloque del pedido **anterior**, y ninguno
    otra cosa. El mouse sirve lo ultimo que tenia cuando todavia no armo lo
    nuevo.

    Sirve donde no llega nada mas. El filtro del byte 0 agarra el caso en que
    viene tambien el id ajeno, y el checksum interno agarra el caso silencioso
    **en cmd 4, 5 y 8**; cmd 6, 10 y 11 no tienen checksum y se quedaban sin
    red. Esto no necesita ninguno de los dos: compara contra lo que el propio
    canal sirvio recien.

    La forma es la del incidente del 2026-09-20: pedido cmd 5 volvio el payload
    de cmd 6 -que en `A_LEER` es **el anterior**- relleno con ceros hasta el
    largo de cmd 5.

    Sobre los 146 respaldos versionados, y comparando **todos** los pares de
    bloques distintos -mas estricto que mirar solo el anterior-, el unico caso
    en que un bloque parece "otro mas ceros" es justamente la lectura
    corrompida. Cero falsos positivos sobre toda la evidencia que hay.
    """
    if anterior is None:
        return False
    cmd_anterior, datos_anterior = anterior
    # Releer el mismo bloque devuelve lo mismo **con razon**: pasa en cada
    # relectura del paso 6, y llamarlo sangrado seria la alarma falsa mas cara
    # posible.
    if cmd_anterior == cmd or not datos_anterior:
        return False
    tamaño = report[1] if len(report) > 1 else 0
    datos = report[2:tamaño]
    # **Truncado o relleno, segun cuanto se pida.** Sale del mismo mecanismo: el
    # buffer tiene el bloque anterior y un `GET` de N bytes devuelve N bytes de
    # ese buffer. Si el bloque pedido es mas corto que el que quedo, llega
    # cortado; si es mas largo, llega con ceros detras, que es la forma del
    # incidente (cmd 5 pide 13 y cmd 6 dejo 7).
    # **Se compara desde el byte 1, salteando el `profileId`.** El sangrado
    # **conserva el byte 0 del bloque pedido** y trae el resto del anterior
    # (MEDIDO, 2026-09-20: pedido cmd 6 volvio `01 00 83 01 01 00 00`, que es
    # el `01` del rate con el payload de la version detras). Comparando desde
    # el 0 ese caso se escapa entero, porque el rate empieza con `01` y la
    # version con `08`. Y no afloja nada: el byte 0 de casi todos los bloques
    # es el mismo `profileId`, asi que nunca aporto a distinguir.
    cuerpo, del_anterior = datos[1:], datos_anterior[1:]
    comun = min(len(cuerpo), len(del_anterior))
    # Con menos de cuatro bytes en comun no se afirma nada: seria la alarma
    # falsa que este proyecto no se puede permitir.
    if comun < MINIMO_PARA_RECONOCER:
        return False
    return (cuerpo[:comun] == del_anterior[:comun]
            and not any(cuerpo[comun:]))


def _por_que_no_sirve(cmd: int, report: bytes, anterior=None) -> str | None:
    """Por que este report no puede pasar por el bloque de `cmd`. None si puede.

    **El mouse tiene un solo buffer para todos los reports** (MEDIDO: un
    `GET(6)` devolvio la version), asi que un `GET` puede traer lo que quedo
    del pedido anterior. Hay dos formas de darse cuenta, y hacen falta las dos:

      * el byte 0 trae otro comando. Es la que ya estaba, y **no alcanza**;
      * el checksum interno no cierra. El 2026-09-20, pedido cmd 5, volvio el
        payload entero de cmd 6 -`01 74 8b 00 00 00 00`- relleno con ceros,
        **con el byte 0 en 0x05**. Paso el primer filtro entero. De ahi fue a
        un codificador, que le cambio su byte, le recalculo el checksum y se lo
        mando al mouse: el cmd 5 quedo con hibernacion 128 min y respuesta 0.

    Cmd 6, 10 y 11 no tienen checksum interno, asi que para esos solo vale el
    primer filtro y `checksum_interno_cierra()` devuelve None. Cmd 9 tampoco
    entra: su checksum vuelve invertido del mouse y su largo es variable (ver
    `_frame`), asi que juzgarlo con esta cuenta seria una alarma inventada.
    """
    if not report:
        return "no volvio nada"
    if report[0] != cmd:
        return f"volvio el bloque de {report[0]:#04x}"
    if _es_el_bloque_anterior(cmd, report, anterior):
        nombre = p.CMD_NAMES.get(anterior[0], anterior[0])
        return f"volvio el payload del bloque anterior ({nombre})"
    if cmd == p.CMD_MACRO:
        return None
    tamaño = report[1] if len(report) > 1 else 0
    if estructuras.checksum_interno_cierra(cmd, report[2:tamaño]) is False:
        return "el checksum interno no cierra: es el buffer de otro bloque"
    return None

#: Cuantas veces se manda la secuencia entera del macro si un trozo no entra.
SECUENCIAS_DE_MACRO = 3

#: El byte 1 del `GET(0xA0)` cuando el bloque esta listo.
LISTO = p.CABLE_READ_READY

#: Lo que se lee por cable para un respaldo: lo de `sesion.A_LEER` **sin el
#: pedido del macro con el perfil**, que por el dongle devuelve un bloque
#: vacio y por cable no tiene pedido: el macro se pide con su id, aparte
#: (`sesion._leer_macros`). Rate, dpi y luz tienen su pedido visto en el bus;
#: version, botones y perfil completo, LEIDO del helper y contestado por el
#: mouse.
A_LEER = [
    p.CMD_VERSION,
    p.CMD_REPORT_RATE,
    p.CMD_LIGHTING,
    p.CMD_DPI,
    p.CMD_BUTTONS,
    p.CMD_PROFILE,
]


class CableNoDisponible(OSError):
    """El canal por cable no se puede usar para lo que se pidio."""


def reports_del_descriptor(crudo: bytes) -> dict[int, int]:
    """`{report_id: bytes_de_datos}` de los Feature Reports declarados.

    Recorre los items del descriptor HID. Los bytes son los de **datos**, sin
    el Report ID: en el cable van con el id adelante, asi que el `wLength` es
    uno mas (52 para el dpi, que declara 51).
    """
    i = 0
    rid = cuenta = tamaño = None
    salida: dict[int, int] = {}
    while i < len(crudo):
        cabeza = crudo[i]
        if cabeza == 0xFE:                 # item largo: no aparece en HID comun
            largo = crudo[i + 1] if i + 1 < len(crudo) else 0
            i += 3 + largo
            continue
        largo = (0, 1, 2, 4)[cabeza & 3]
        tipo = (cabeza >> 2) & 3
        etiqueta = cabeza >> 4
        valor = int.from_bytes(crudo[i + 1:i + 1 + largo], "little")
        i += 1 + largo
        if tipo == 1 and etiqueta == 8:            # Report ID
            rid = valor
        elif tipo == 1 and etiqueta == 9:          # Report Count
            cuenta = valor
        elif tipo == 1 and etiqueta == 7:          # Report Size
            tamaño = valor
        elif tipo == 0 and etiqueta == 11:         # Main: Feature
            if rid is not None and cuenta and tamaño:
                salida.setdefault(rid, cuenta * tamaño // 8)
    return salida


def largos_del_nodo(path: Path, raiz: Path | None = None) -> dict[int, int]:
    """`{cmd: largo en el cable}` del nodo, con el Report ID incluido."""
    raiz = Path(raiz) if raiz is not None else SYS_HIDRAW
    crudo = (raiz / Path(path).name / "device" / "report_descriptor").read_bytes()
    return {rid: datos + 1 for rid, datos in reports_del_descriptor(crudo).items()}


class _Ioctl:
    """Los dos ioctl sobre un descriptor abierto. Las pruebas lo reemplazan."""

    def __init__(self, fd: int):
        self.fd = fd

    def set_feature(self, report: bytes) -> None:
        buf = bytearray(report)
        fcntl.ioctl(self.fd, HIDIOCSFEATURE(len(buf)), buf, True)

    def get_feature(self, report_id: int, largo: int) -> bytes:
        buf = bytearray(largo)
        buf[0] = report_id
        leidos = fcntl.ioctl(self.fd, HIDIOCGFEATURE(len(buf)), buf, True)
        return bytes(buf[:leidos]) if leidos > 0 else b""


class CableDevice:
    """Pedidos y escrituras por Feature Reports, con la interfaz de `Device`.

    `solo_lectura` deja pasar los pedidos `0xA0` -sin ellos no se lee nada- y
    **rechaza cualquier report de escritura**. No lo sostiene el kernel como el
    `O_RDONLY` del dongle, porque por cable leer tambien es un `SET_FEATURE`:
    lo sostiene este objeto, y un test lo verifica.
    """

    via = dispositivos.VIA_CABLE
    #: El respaldo por cable (ver `A_LEER`).
    a_leer = tuple(A_LEER)
    #: El macro se lee con su id: `build_cable_read_request(9, macro_id=N)`.
    lee_macros = True

    def __init__(self, path: Path, *, largos: dict[int, int] | None = None,
                 solo_lectura: bool = False, ioctl: _Ioctl | None = None):
        self.path = Path(path)
        self.solo_lectura = solo_lectura
        self._largos = largos
        self._ioctl = ioctl
        self._fd: int | None = None
        self._candado = asyncio.Lock()
        #: Desde cuando se le puede volver a mandar algo al mouse (reloj
        #: monotono). Lo corre cada transferencia; ver `PAUSA_TRAS_ESCRITURA`.
        self._libre_desde = 0.0
        # Los mismos ganchos que `Device`, para que `sesion.escuchar_novedades`
        # no tenga que preguntar. Ver `alimentar()`.
        self.on_estado_mouse = None
        self.on_frame = None
        self.on_desconexion = None
        self._loop = None
        #: Cuantos bloques leidos se rechazaron, por motivo. Un `leer()` que
        #: reintenta y sale bien suma aca y **no** se nota en el resultado, asi
        #: que sin esto la frecuencia del sangrado es invisible: es lo que mide
        #: `dev/herramientas/medir-sangrado.py`. No es un contador de errores
        #: -el pedido se rehace y casi siempre anda-, es la tasa de un
        #: fenomeno del firmware.
        self.rechazos: collections.Counter[str] = collections.Counter()
        #: `(cmd, datos)` del ultimo bloque que el canal sirvio. Lo usa
        #: `_es_el_bloque_anterior()`: MEDIDO que cuando el mouse sangra
        #: devuelve **este**, asi que reconocerlo es reconocer el sangrado sin
        #: depender de un checksum que la mitad de los bloques no tiene.
        self._ultimo_servido: tuple[int, bytes] | None = None

    # --- abrir y cerrar ---------------------------------------------------

    def open(self) -> None:
        if self._ioctl is not None:
            return
        try:
            # `O_NONBLOCK` es para escuchar (`start_reading`); los ioctl de
            # Feature Reports no lo miran: son transferencias de control.
            self._fd = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)
        except PermissionError as exc:
            from .hidraw import FaltaLaReglaDeUdev
            raise FaltaLaReglaDeUdev(
                f"sin permiso sobre {self.path}, el mouse por cable. La regla "
                "de udev cubre el dongle y el cable",
                path=self.path) from exc
        self._ioctl = _Ioctl(self._fd)
        if self._largos is None:
            self._largos = largos_del_nodo(self.path)
        log.info("abierto %s, por cable (%s)", self.path,
                 "solo lectura" if self.solo_lectura else "lectura/escritura")

    def close(self) -> None:
        if self._fd is not None:
            if self._loop is not None:
                try:
                    self._loop.remove_reader(self._fd)
                except (RuntimeError, ValueError):
                    pass
            os.close(self._fd)
            self._fd = None
        self._ioctl = None
        self._loop = None

    # --- escuchar: el Report ID 3, como por el dongle ---------------------
    #
    # **El descriptor del cable declara un Input Report 3 de 4 bytes**, en la
    # Usage Page 0x0A -notificaciones- de esta misma interfaz 2 (LEIDO del
    # descriptor de `1d57:2126`, 2026-09-18). Es el mismo numero y el mismo
    # largo que el aviso del dongle -`[deviceId, tipo, ...]`: bateria, y el
    # cambio de nivel de dpi cuando se aprieta el boton-, y hasta el
    # 2026-09-18 por cable no lo escuchaba nadie: la ventana no se enteraba
    # del boton de dpi. **Que el mouse lo mande por cable no esta medido**:
    # escuchar no le escribe nada, y si no llega, no pasa nada.

    def start_reading(self, loop) -> None:
        """Escucha lo que el mouse manda solo. No le manda nada."""
        if self._fd is None:
            return
        self._loop = loop
        loop.add_reader(self._fd, self._drenar)

    def _drenar(self) -> None:
        while self._fd is not None:
            try:
                datos = os.read(self._fd, 256)
            except BlockingIOError:
                return
            except OSError as exc:
                if exc.errno in (errno.ENODEV, errno.EIO):
                    log.warning("el mouse por cable se fue: %s", exc)
                    self.close()
                    if self.on_desconexion is not None:
                        self.on_desconexion()
                    return
                raise
            if not datos:
                return
            self.alimentar(datos)

    def alimentar(self, datos: bytes) -> None:
        """Un Input Report de la interfaz 2: solo el 3 le importa a alguien."""
        from .hidraw import REPORT_ID_ESTADO
        if datos and datos[0] == REPORT_ID_ESTADO and self.on_estado_mouse:
            self.on_estado_mouse(bytes(datos[1:5]))

    @property
    def largos(self) -> dict[int, int]:
        return dict(self._largos or {})

    # --- lo que se muestra antes de escribir ------------------------------

    def trama_de(self, bloque: bytes) -> bytes:
        """Lo que saldria por el cable para ese bloque, sin mandarlo.

        El macro son sus dos trozos de 64, uno detras del otro.
        """
        if bloque and bloque[0] == p.CMD_MACRO:
            return b"".join(p.build_cable_macro_reports(bytes(bloque)))
        return p.build_cable_write_report(bloque, self._largo(bloque[0]))

    def _largo(self, cmd: int) -> int:
        largo = (self._largos or {}).get(cmd)
        if largo is None:
            raise CableNoDisponible(
                f"el mouse no declara el report {cmd} por cable; no se inventa "
                "un largo")
        return largo

    # --- el nivel de abajo: un SET con su reintento -----------------------

    async def _esperar_turno(self) -> None:
        """No le manda nada al mouse antes de que termine el respiro."""
        falta = self._libre_desde - time.monotonic()
        if falta > 0:
            await asyncio.sleep(falta)

    def _respirar(self, segundos: float) -> None:
        self._libre_desde = max(self._libre_desde,
                                time.monotonic() + segundos)

    async def _set(self, report: bytes, *, que: str) -> bool:
        """Un `SET_FEATURE`, repitiendo **el mismo** si vuelve con STALL."""
        await self._esperar_turno()
        for intento in range(1, INTENTOS_POR_STALL + 1):
            try:
                await asyncio.to_thread(self._ioctl.set_feature, report)
                return True
            except OSError as exc:
                if exc.errno != errno.EPIPE:
                    raise
                log.debug("%s: STALL (%d/%d), repito el mismo report en "
                          "%.0f ms", que, intento, INTENTOS_POR_STALL,
                          PAUSA_TRAS_STALL * 1000)
                await asyncio.sleep(PAUSA_TRAS_STALL)
        log.warning("%s: el mouse rechazo el report %d veces seguidas", que,
                    INTENTOS_POR_STALL)
        return False

    async def _get(self, report_id: int, largo: int) -> bytes | None:
        try:
            return await asyncio.to_thread(self._ioctl.get_feature, report_id,
                                           largo)
        except OSError as exc:
            log.warning("GET del report %#04x: %s", report_id, exc.strerror)
            return None

    # --- leer -------------------------------------------------------------

    async def leer(self, cmd: int, sub: int | None = None, profile: int = 1,
                   timeout: float | None = None, reintentos: int | None = None,
                   macro_id: int | None = None) -> Frame | None:
        """El bloque de un comando, como lo devolveria `Device.leer()`.

        `timeout` y `reintentos` se aceptan para tener la misma firma y no se
        usan: por cable no hay enlace de radio que pierda pedidos.
        """
        nombre = p.CMD_NAMES.get(cmd, f"cmd {cmd}")
        if self._ioctl is None:
            raise CableNoDisponible("el canal por cable no esta abierto")
        try:
            pedido = p.build_cable_read_request(cmd, profile,
                                                macro_id=macro_id)
        except p.ComandoSinSub as exc:
            log.warning("%s: por cable no se lee, %s", nombre, exc.args[0])
            return None
        largo = p.CABLE_READ_SUB[cmd]

        async with self._candado:
            for vez in range(1, PEDIDOS_POR_BLOQUE_AJENO + 1):
                report = await self._pedir_bloque(pedido, cmd, largo, nombre)
                if report is None:
                    break
                malo = _por_que_no_sirve(cmd, report, self._ultimo_servido)
                if malo is None:
                    break
                # **Con el comando que se pidio adelante.** Sin eso solo se
                # sabe que volvio, y la pregunta que importa es de que pedido
                # es lo que volvio: si siempre fuera el bloque **anterior**,
                # el fenomeno estaria explicado y el arreglo seria dirigido.
                # Con el motivo solo no se puede ni plantear.
                self.rechazos[f"pidiendo {nombre}: {malo}"] += 1
                # El buffer del mouse todavia tenia otra cosa: el "listo" era
                # del pedido anterior. Se pide de nuevo, con el respiro del
                # soft.
                log.info("%s: %s, lo pido de nuevo (%d/%d)", nombre, malo,
                         vez, PEDIDOS_POR_BLOQUE_AJENO)
            else:
                # **Se acabaron los intentos y el bloque sigue sin servir.** No
                # se devuelve: un bloque asi va derecho a un codificador, que
                # le cambia su byte, le recalcula el checksum y se lo manda al
                # mouse. Fue exactamente lo que paso el 2026-09-20.
                log.warning("%s: %s despues de %d pedidos. No lo devuelvo: "
                            "escribir sobre esto le mete al mouse datos de "
                            "otro bloque", nombre,
                            _por_que_no_sirve(cmd, report,
                                              self._ultimo_servido),
                            PEDIDOS_POR_BLOQUE_AJENO)
                return None

        frame = self._frame(cmd, report, nombre)
        # **Lo que se sirvio, para poder reconocerlo si vuelve.** Es lo unico
        # que detecta el sangrado silencioso en cmd 6, 10 y 11, que no tienen
        # checksum interno. Se guarda lo que salio bien: un bloque rechazado no
        # se sirvio, asi que el mouse no lo tiene como "lo ultimo".
        if frame is not None:
            self._ultimo_servido = (cmd, bytes(frame.data))
        return frame

    async def _pedir_bloque(self, pedido: bytes, cmd: int, largo: int,
                            nombre: str) -> bytes | None:
        """Una vuelta entera: el pedido, el "listo" y el `GET` del bloque."""
        if not await self._set(pedido, que=f"pedido de {nombre}"):
            return None
        await asyncio.sleep(ESPERA_TRAS_PEDIDO)
        for _ in range(REINTENTOS_DE_LISTO):
            estado = await self._get(p.CABLE_READ_REPORT_ID,
                                     p.CABLE_READ_REQUEST_LEN)
            if estado is not None and len(estado) > 1 and estado[1] == LISTO:
                break
            await asyncio.sleep(PAUSA_DE_LISTO)
        else:
            log.warning("%s: el mouse no dijo listo", nombre)
            self._respirar(PAUSA_ENTRE_PEDIDOS)
            return None
        await asyncio.sleep(ESPERA_TRAS_LISTO)
        report = await self._get(cmd, largo)
        self._respirar(PAUSA_ENTRE_PEDIDOS)
        return report

    @staticmethod
    def _frame(cmd: int, report: bytes | None, nombre: str) -> Frame | None:
        """El report leido, en la forma de `Frame` que espera la sesion.

        `data` arranca en el byte 2, despues de `[cmd, sizeTotalData]`, igual
        que en el dongle. **Se exige el bloque entero**: el mouse devuelve el
        relleno aunque declare menos (MEDIDO), asi que uno corto es uno que no
        llego, y decodificarlo seria leer campos que no estan.
        """
        if not report or len(report) < 2:
            log.warning("%s: el mouse no devolvio nada", nombre)
            return None
        if report[0] != cmd:
            log.warning("%s: volvio el report %#04x", nombre, report[0])
            return None
        tamaño = report[1]
        if tamaño < 2 or len(report) < tamaño:
            log.warning("%s: el bloque dice %d B y llegaron %d", nombre,
                        tamaño, len(report))
            return None
        # **El macro por cable viene con 20 ceros de mas.** El mouse contesta
        # `sizeTotalData` 0x83 -lo que pide el helper- y adentro esta el bloque
        # de 111 del dongle, con su checksum interno en su lugar, y despues
        # relleno (MEDIDO, `dev/models/attackshark-x8pro/respaldos/cable-macro-17.json`). Se presenta
        # como el del dongle, que es el que saben decodificar y escribir los
        # demas; **solo si lo que sobra es cero**: si trae datos, es otro
        # bloque, y cortarlo seria inventar uno.
        propio = p.READ_SUB.get(cmd)
        if propio is not None and 2 < propio < tamaño:
            if any(report[propio:tamaño]):
                log.warning("%s: el bloque dice %d B y el del dongle mide %d, "
                            "y lo que sobra no es relleno: %s", nombre, tamaño,
                            propio, report[propio:tamaño].hex())
                return None
            tamaño = propio
        # `checksum_ok` es el de afuera en el dongle, y por cable no hay
        # afuera: la transferencia de control ya trae su CRC. El checksum
        # interno de la estructura lo mira quien decodifica, como siempre.
        return Frame(report_id=cmd, length=len(report), opcode=p.WRITE_OPCODE,
                     cmd=cmd, sub=tamaño, data=bytes(report[2:tamaño]),
                     checksum_ok=True, raw=bytes(report))

    # --- escribir ---------------------------------------------------------

    async def escribir(self, bloque: bytes, *, timeout: float | None = None,
                       reintentos: int | None = None) -> bool:
        """Manda un bloque como Feature Report. True si el mouse lo acepto.

        **Aceptar no es aplicar**: es que la transferencia no volvio con
        STALL. Igual que con el `0xC1` del dongle, lo que dice que el mouse
        aplico el cambio es la relectura.
        """
        if self.solo_lectura:
            raise PermissionError(
                f"{self.path} se abrio en solo lectura: por cable pasan los "
                "pedidos de lectura, y ningun report de escritura")
        if self._ioctl is None:
            raise CableNoDisponible("el canal por cable no esta abierto")
        bloque = bytes(bloque)
        report = self.trama_de(bloque)
        nombre = p.CMD_NAMES.get(bloque[0], f"cmd {bloque[0]}")
        async with self._candado:
            ok = await self._set(report, que=nombre)
            # Aceptado o no, lo proximo espera: ver `PAUSA_TRAS_ESCRITURA`.
            self._respirar(PAUSA_TRAS_ESCRITURA)
        if ok:
            log.info("%s: el mouse acepto el report por cable", nombre)
        return ok

    async def escribir_por_bloques(self, bloque: bytes, **_) -> bool:
        """El macro por cable: el bloque de 111 en dos `SET_FEATURE(9)` de 64.

        Los trozos son `build_cable_macro_reports()`, byte a byte los del soft
        en `cable-soft-macros.pcap`, y el bloque adentro es el mismo que se
        escribe y se verifica por el dongle. Entre trozo y trozo, el respiro de
        despues de escribir (el helper hace `Sleep(500)` en cada uno).

        **Si un trozo no entra, se vuelve a mandar la secuencia entera**, como
        por el dongle: entre los dos trozos el mouse tiene medio macro, y el
        trozo 0 es el que lo reposiciona. Lo que dice si quedo bien es la
        relectura, como siempre.
        """
        if self.solo_lectura:
            raise PermissionError(
                f"{self.path} se abrio en solo lectura: por cable pasan los "
                "pedidos de lectura, y ningun report de escritura")
        if self._ioctl is None:
            raise CableNoDisponible("el canal por cable no esta abierto")
        trozos = p.build_cable_macro_reports(bytes(bloque))
        async with self._candado:
            for vuelta in range(1, SECUENCIAS_DE_MACRO + 1):
                entero = True
                for i, trozo in enumerate(trozos):
                    ok = await self._set(trozo, que=f"macro, trozo {i}")
                    self._respirar(PAUSA_TRAS_ESCRITURA)
                    if not ok:
                        entero = False
                        break
                if entero:
                    log.info("macro: el mouse acepto los %d trozos por cable",
                             len(trozos))
                    return True
                log.warning("macro: un trozo no entro; mando la secuencia "
                            "entera de nuevo (%d/%d)", vuelta,
                            SECUENCIAS_DE_MACRO)
        return False


def abrir(conexion, *, solo_lectura: bool = False) -> CableDevice:
    """Abre el canal de configuracion de una conexion por cable."""
    if conexion.via != dispositivos.VIA_CABLE:
        raise CableNoDisponible(f"{conexion.describir()} no es el cable")
    nodo = conexion.nodo_de_configuracion
    if nodo is None:
        raise CableNoDisponible(
            f"{conexion.describir()}: no encuentro su interfaz de configuracion")
    device = CableDevice(nodo.path, solo_lectura=solo_lectura)
    device.open()
    return device
