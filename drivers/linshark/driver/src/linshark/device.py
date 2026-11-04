# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Capa de dispositivo: tramas, correlacion pedido/respuesta y reintentos.

Encima de HidrawChannel, que solo mueve bytes. Aca vive lo que aprendimos
sobre como se comporta el enlace de 2.4 GHz.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from . import protocol as p
from .hidraw import REPORT_ID_ESTADO, HidrawChannel

log = logging.getLogger("linshark.device")

# --- opcodes de estado que manda el dongle ----------------------------------
# El dongle contesta al toque con uno de estos, y recien despues (si el mouse
# atendio) llega la respuesta de verdad.
ST_ACEPTADO = 0xC0       # pedido encolado hacia el mouse
ST_ESCRITURA_OK = 0xC1   # el dongle acepto la escritura. NO es que el
                         # mouse la haya aplicado: acuso
                         # veinte tramas mal armadas -un bloque de dpi de
                         # 14 bytes, que el firmware descarta- sin
                         # protestar una sola vez. Le alcanza con que la
                         # trama cierre: Report ID, largo y checksum. Lo
                         # unico que dice que el mouse aplico algo es la
                         # relectura.
ST_OCUPADO = 0xC3        # llega si se mandan comandos muy pegados
ST_SIN_RESPUESTA = 0xC2  # el mouse no contesto: hay que reintentar

# 0xC1 es MEDIDO. En `dev/models/attackshark-x8pro/docs/capturas-w/` hay 93 escrituras del
# driver oficial y 5 lecturas; las 93 escrituras reciben `04 06 c1 01 00 cc`
# unos 25 ms despues, y ninguna de las 5 lecturas lo recibe. O sea:
#
#     lectura   -> 0xC0 (aceptado) y despues la respuesta con los datos
#     escritura -> 0xC0 (aceptado) y despues 0xC1 (aplicada)
#
# Es la senal en la que se apoya la Etapa 3 de `dev/docs/metodo.md`: permite saber
# si el mouse acepto una escritura sin tener que releer y comparar.

ESTADOS = {
    ST_ACEPTADO: "aceptado",
    ST_ESCRITURA_OK: "escritura aplicada",
    ST_OCUPADO: "ocupado",
    ST_SIN_RESPUESTA: "sin respuesta del mouse",
}

# Medidos contra el hardware: la respuesta buena llega a ~0.74 s y el NAK del
# dongle a ~2.10 s, los dos muy consistentes.
#
# El enlace pierde pedidos segun el mouse este activo o quieto: 95% de exito
# moviendose, 50% quieto (ver dev/models/attackshark-x8pro/docs/bitacora.md). Por eso hacen falta varios
# reintentos: con 50% por intento, 8 intentos dan 99.6%.
#
# OJO con el timeout: tiene que ser MAS LARGO que los 2.10 s del NAK. El NAK
# no es algo que convenga evitar esperar, es la senal de que el dongle se
# libero. Reintentar antes de que llegue le cae encima con el pedido anterior
# todavia en vuelo, contesta 0xC3 "ocupado", y de ahi no sale mas.
# El timeout queda solo como red de seguridad: lo normal es que la carrera la
# gane la respuesta (0.74 s) o el NAK (2.10 s).
TIMEOUT = 3.0
REINTENTOS = 8

# Si el dongle contesta 0xC3 "ocupado" es porque todavia tiene en vuelo el
# pedido anterior, que va a terminar en respuesta (~0.74 s) o en NAK (~2.10 s).
# No hay que esperar el timeout completo: alcanza con una pausa corta y volver
# a mandar. Tampoco conviene gastar el presupuesto de reintentos del enlace en
# esto, que es un problema distinto (nosotros mandamos muy pegado, no es la
# radio), asi que los "ocupado" llevan su propio tope.
#
# El presupuesto tiene que superar el peor caso MEDIDO de arriba: si el dongle
# puede tardar 2.10 s en liberarse (el NAK), rendirse antes es rendirse sin
# haberle dado la chance. Antes esto era 0.3 s x 4 = 1.2 s, o
# sea la mitad de lo que hace falta, y no se noto nunca porque a 1000 Hz el
# dongle se libera rapido. A 8000 Hz no: el canal de configuracion compite
# con ocho veces mas trafico de movimiento, el presupuesto se agota, y como
# cada reintento le cae encima con el pedido anterior todavia en vuelo, el
# dongle queda trabado y **el mouse deja de moverse** hasta que se recupera
# solo. Ver dev/models/attackshark-x8pro/docs/bitacora.md.
#
# La espera crece al doble cada vez en vez de ser fija, por el mismo motivo:
# insistir al mismo ritmo contra algo que esta ocupado lo mantiene ocupado.
PAUSA_OCUPADO = 0.4
REINTENTOS_OCUPADO = 4
PAUSA_OCUPADO_MAXIMA = 3.0


@dataclass
class Frame:
    """Una trama del dispositivo ya parseada."""

    report_id: int
    length: int
    opcode: int
    cmd: int | None
    sub: int | None
    data: bytes
    checksum_ok: bool
    raw: bytes = field(repr=False, default=b"")

    @property
    def es_estado(self) -> bool:
        return self.opcode in ESTADOS

    @property
    def es_respuesta(self) -> bool:
        return self.opcode == p.WRITE_OPCODE and self.cmd is not None

    def describe(self) -> str:
        if self.es_estado:
            return f"estado: {ESTADOS[self.opcode]}"
        nombre = p.CMD_NAMES.get(self.cmd, f"cmd {self.cmd}")
        return f"respuesta de {nombre} (sub={self.sub}), {len(self.data)} B de datos"


def parse_frame(report: bytes) -> Frame | None:
    """Parsea un Input Report del canal de configuracion.

    Formato, ya confirmado contra el hardware y contra WebDriver.exe:

        [reportId][largo][opcode][...][chkHi][chkLo]

    donde el checksum es la suma llana de todo lo anterior, con el reportId
    incluido. Cuando el opcode es 0x00 la trama trae cmd y sub; cuando es
    0xC0/0xC2/0xC3 es un estado con un solo byte de dato.
    """
    if len(report) < 6:
        return None
    report_id, length, opcode = report[0], report[1], report[2]
    if length < 6 or length > len(report):
        return None
    cuerpo = report[:length]
    hi, lo = p.checksum(cuerpo[:-2])
    ok = cuerpo[-2] == hi and cuerpo[-1] == lo

    if opcode in ESTADOS:
        return Frame(report_id, length, opcode, None, None,
                     cuerpo[3:-2], ok, cuerpo)
    if opcode != p.WRITE_OPCODE:
        # Bloque de continuacion de una respuesta larga: el byte 2 es el
        # numero de bloque, y no hay cmd ni sub. Se deja pasar sin
        # interpretarlos; los junta Device._reensamblar().
        return Frame(report_id, length, opcode, None, None,
                     cuerpo[3:-2], ok, cuerpo)
    return Frame(report_id, length, opcode, cuerpo[3], cuerpo[4],
                 cuerpo[5:-2], ok, cuerpo)


class Device:
    """Pedidos con correlacion y reintentos sobre el canal HID."""

    def __init__(self, canal: HidrawChannel):
        self.canal = canal
        self._esperando: dict[int, asyncio.Future] = {}
        self._nak = asyncio.Event()
        self._ocupado = asyncio.Event()
        self._escritura_ok = asyncio.Event()
        # Respuesta larga a medio armar (ver _bloque_siguiente).
        self._parcial: dict | None = None
        self.on_estado_mouse = None   # callback para el Report ID 3
        self.on_frame = None          # callback para todo lo demas

    # --- entrada ------------------------------------------------------------

    def alimentar(self, data: bytes) -> None:
        """Se llama por cada Input Report que llega."""
        if data and data[0] == REPORT_ID_ESTADO:
            if self.on_estado_mouse:
                # [deviceId, marca, estadoBateria, nivelBateria]
                self.on_estado_mouse(data[1:5])
            return

        frame = parse_frame(data)
        if frame is None:
            return
        if not frame.checksum_ok:
            log.warning("checksum invalido: %s", data[:16].hex())
            return

        if frame.opcode == ST_SIN_RESPUESTA:
            self._nak.set()
            return
        if frame.opcode == ST_ESCRITURA_OK:
            self._escritura_ok.set()
            return
        if frame.opcode == ST_OCUPADO:
            # Sin esto la espera se comia el timeout completo (3 s) aunque el
            # dongle ya hubiera dicho que no acepto el pedido.
            self._ocupado.set()
            return
        if frame.es_estado:
            return

        completo = self._reensamblar(frame)
        if completo is None:
            return

        fut = self._esperando.pop(completo.cmd, None)
        if fut is not None and not fut.done():
            fut.set_result(completo)
        elif self.on_frame:
            self.on_frame(completo)

    # --- respuestas que no entran en un report ------------------------------
    # El canal mueve reports de 64 bytes, asi que una respuesta cuyo
    # `sizeTotalData` pase de 59 no entra en uno solo: llega **en bloques**,
    # con los mismos largos que usa el binario para escribir macros (64 el
    # primero, 57 el ultimo) y el numero de bloque en el byte 2, en el lugar
    # donde el bloque 0 tiene el opcode.
    #
    # Se descubrio leyendo `macro` (sizeTotalData 111) y `perfil completo`
    # (128): los dos devolvian 57 bytes de datos y el resto se perdia en
    # silencio, porque el bloque 1 no es ni un estado ni una respuesta y caia
    # en ninguna rama. Ver dev/models/attackshark-x8pro/docs/bitacora.md.

    def _reensamblar(self, frame: Frame) -> Frame | None:
        """Devuelve el frame completo, o None si todavia faltan bloques."""
        esperados = frame.sub - 2 if frame.sub is not None else 0

        if frame.opcode == p.WRITE_OPCODE:
            # Bloque 0: trae cmd y sizeTotalData.
            if len(frame.data) >= esperados:
                return frame            # entraba en un solo report
            self._parcial = {
                "cmd": frame.cmd,
                "sub": frame.sub,
                "datos": bytearray(frame.data),
                "raw": bytearray(frame.raw),
            }
            log.debug("respuesta larga de %s: %d de %d bytes, espero mas bloques",
                      p.CMD_NAMES.get(frame.cmd, frame.cmd),
                      len(frame.data), esperados)
            return None

        # Bloques siguientes: el byte 2 es el numero de bloque y **no hay
        # cmd ni sub**, los datos arrancan en el 3.
        if self._parcial is None:
            return None
        trozo = frame.raw[3:-2]
        self._parcial["datos"].extend(trozo)
        self._parcial["raw"].extend(frame.raw)
        faltan = self._parcial["sub"] - 2 - len(self._parcial["datos"])
        if faltan > 0:
            return None

        armado = Frame(
            report_id=p.DEVICE_REPORT_ID,
            length=len(self._parcial["raw"]),
            opcode=p.WRITE_OPCODE,
            cmd=self._parcial["cmd"],
            sub=self._parcial["sub"],
            data=bytes(self._parcial["datos"]),
            checksum_ok=True,          # cada bloque valido el suyo al entrar
            raw=bytes(self._parcial["raw"]),
        )
        log.debug("respuesta de %s completa: %d bytes en varios bloques",
                  p.CMD_NAMES.get(armado.cmd, armado.cmd), len(armado.data))
        self._parcial = None
        return armado

    # --- salida -------------------------------------------------------------

    async def leer(self, cmd: int, sub: int | None = None,
                   profile: int = 1,
                   timeout: float = TIMEOUT,
                   reintentos: int = REINTENTOS,
                   macro_id: int | None = None) -> Frame | None:
        """Pide un valor al mouse, reintentando si el dongle da NAK.

        El enlace de 2.4 GHz pierde alrededor de la mitad de los pedidos
        cuando el mouse esta ocioso: el dongle acepta el comando y despues
        avisa "sin respuesta". Reintentar alcanza.
        """
        nombre = p.CMD_NAMES.get(cmd, f"cmd {cmd}")
        try:
            trama = p.build_read_frame(cmd, sub, profile, macro_id=macro_id)
        except p.ComandoSinSub as exc:
            # No es un error del enlace ni algo que se arregle reintentando: no
            # tenemos la plantilla de ese comando. Antes esto salia como
            # KeyError sin capturar y se llevaba puesta la conexion entera.
            log.warning("%s: no soportado, %s", nombre, exc.args[0])
            return None

        # El futuro vive TODA la llamada, no un intento. Antes se lo
        # registraba y se lo borraba en cada vuelta, asi que durante las
        # pausas --de 0.4 a 3.0 s en la rama de "ocupado"-- no quedaba nadie
        # esperando: una respuesta que llegara justo ahi no la recibia el
        # pedido que la habia pedido, se iba por `on_frame` y el intento moria
        # por timeout con la respuesta ya en casa. Se nota sobre todo en macro
        # y perfil completo, que vienen en varios bloques y tardan mas.
        # Ver dev/models/attackshark-x8pro/docs/bitacora.md.
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._esperando[cmd] = fut
        # Restos de una respuesta larga que quedo a medias en el pedido
        # anterior: no son de este, y anexarlos daria un frame Frankenstein.
        self._parcial = None

        intento = 0
        ocupados = 0
        try:
            while intento < reintentos:
                intento += 1
                self._nak.clear()
                self._ocupado.clear()
                self.canal.write_frame(trama)

                # Carrera entre la respuesta y los dos avisos del dongle: gana
                # el que llegue primero. Sin esto se esperaria el timeout
                # completo aunque el dongle ya haya avisado que el mouse no
                # atendio (0xC2) o que ni siquiera acepto el pedido (0xC3).
                espera_nak = asyncio.create_task(self._nak.wait())
                espera_ocupado = asyncio.create_task(self._ocupado.wait())
                try:
                    await asyncio.wait(
                        {fut, espera_nak, espera_ocupado},
                        timeout=timeout,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                finally:
                    espera_nak.cancel()
                    espera_ocupado.cancel()

                if fut.done():
                    return fut.result()

                if self._ocupado.is_set() and not self._nak.is_set():
                    # El dongle estaba con el pedido anterior en vuelo. Es
                    # culpa nuestra por mandar muy pegado, no del enlace, asi
                    # que no consume el presupuesto de reintentos de radio.
                    ocupados += 1
                    intento -= 1
                    if ocupados > REINTENTOS_OCUPADO:
                        # **No se nombra una tasa aca.** Antes este
                        # mensaje decia "si el mouse esta a
                        # 8000 Hz", y el dia que el respaldo fallo de verdad
                        # el mouse estaba a **2000**: la frontera esta mucho
                        # mas abajo de lo que decia el aviso, y el aviso
                        # mandaba a buscar el problema donde no estaba.
                        log.warning(
                            "%s: el dongle sigue ocupado despues de %d intentos. "
                            "Arriba de 1000 Hz el canal de configuracion compite "
                            "con el trafico de movimiento y los bloques largos no "
                            "llegan: bajar la tasa (driver/scripts/cambiar-rate.py "
                            "--valor 1000) o dejar el mouse quieto y reintentar.",
                            nombre, ocupados)
                        break
                    pausa = min(PAUSA_OCUPADO * 2 ** (ocupados - 1),
                                PAUSA_OCUPADO_MAXIMA)
                    log.debug("%s: dongle ocupado, espero %.2f s (%d/%d)",
                              nombre, pausa, ocupados, REINTENTOS_OCUPADO)
                    await self._dormir_salvo_respuesta(fut, pausa)
                    if fut.done():
                        return fut.result()
                    continue

                motivo = "NAK del dongle" if self._nak.is_set() else "timeout"
                log.debug("%s: %s, reintento %d/%d", nombre, motivo, intento,
                          reintentos)
                await self._dormir_salvo_respuesta(fut, 0.15)
                if fut.done():
                    return fut.result()
            else:
                log.warning("%s: sin respuesta despues de %d intentos",
                            nombre, reintentos)

            # Una respuesta larga a medio llegar es evidencia de que el dongle
            # SI esta contestando, y rendirse ahi es rendirse con la respuesta
            # en el aire. Se le da un timeout mas, pero **solo** con esa
            # evidencia: sin ella, esperar de mas es demorar el fracaso.
            if self._parcial is not None:
                traidos = len(self._parcial["datos"])
                total = self._parcial["sub"] - 2
                log.warning("%s: llegaron %d de %d bytes; el dongle contesto y "
                            "se perdio el resto. Espero %.1f s mas.",
                            nombre, traidos, total, timeout)
                await self._dormir_salvo_respuesta(fut, timeout)
                if fut.done():
                    return fut.result()
            return None
        finally:
            self._esperando.pop(cmd, None)

    @staticmethod
    async def _dormir_salvo_respuesta(fut: asyncio.Future,
                                      segundos: float) -> None:
        """Duerme, salvo que llegue la respuesta que estamos esperando.

        Un `sleep` pelado en medio de los reintentos es tiempo durante el cual
        la respuesta puede llegar sin que nadie la mire hasta que se cumpla la
        pausa entera. El `shield` es para que el timeout cancele la espera, no
        el futuro.
        """
        try:
            await asyncio.wait_for(asyncio.shield(fut), timeout=segundos)
        except asyncio.TimeoutError:
            pass

    @staticmethod
    async def _dormir_salvo_evento(evento: asyncio.Event,
                                   segundos: float) -> None:
        """Lo mismo que `_dormir_salvo_respuesta`, pero para un Event.

        `escribir()` no espera un futuro con la respuesta adentro: espera el
        acuse `0xC1`, que es un Event. Un `sleep` pelado ahi tiene el mismo
        problema --y uno peor, ver abajo-- que el que se arreglo en `leer()`.

        No hace falta `shield`: cancelar al que espera no borra el Event, el
        estado queda puesto y lo lee el que llama.
        """
        try:
            await asyncio.wait_for(evento.wait(), timeout=segundos)
        except asyncio.TimeoutError:
            pass

    async def escribir(self, bloque: bytes, *,
                       timeout: float = TIMEOUT,
                       reintentos: int = REINTENTOS) -> bool:
        """Le manda un bloque de configuracion al mouse y espera el acuse.

        `bloque` empieza en el byte de comando: `[cmd, sizeTotalData, ...datos]`.
        La trama la arma `build_write_frame()`, que le pone el Report ID, el
        largo, el opcode 0x00 y el checksum.

        Devuelve True solo si llego el `0xC1` del dongle (ver ST_ESCRITURA_OK).
        No reintenta a ciegas: el mismo mecanismo de `leer()` distingue entre
        "el dongle estaba ocupado" (culpa nuestra, no gasta reintentos) y "el
        enlace perdio el pedido" (sí los gasta).

        **Este metodo no decide si algo se puede escribir.** La allowlist, el
        modo y el simulacro se chequean en el backend, antes de llegar aca.

        Las pausas de este bucle **no son `sleep`**, y el motivo es peor que en
        `leer()`. Ahi, perder una respuesta durante la pausa cuesta un pedido
        de mas: se relee y listo. Aca, perder el `0xC1` durante la pausa
        significa que la escritura **ya se aplico en el mouse** y nosotros no
        nos enteramos, con dos consecuencias:

        1. Se reenvia una escritura que ya surtio efecto. Con rate y dpi eso es
           idempotente, pero la regla del proyecto es no mandarle al mouse una
           trama que no haga falta.
        2. Si se agotan los reintentos se devuelve False habiendo escrito, o
           sea que reportamos como fallado algo que paso. Es justo la clase de
           afirmacion que el proyecto no se permite (ver dev/docs/metodo.md, "un
           error de formato se ve igual que un problema de enlace").

        El acuse llega ~25 ms despues de la escritura y la pausa por "ocupado"
        arranca en 400 ms y crece hasta 3 s: la ventana para perderlo es la
        pausa entera. Con `_dormir_salvo_evento()` la pausa se corta apenas
        llega el `0xC1` y se devuelve True ahi mismo.
        """
        cmd = bloque[0] if bloque else None
        nombre = p.CMD_NAMES.get(cmd, f"cmd {cmd}")
        return await self._escribir_tramas(
            [p.build_write_frame(bloque)], nombre=nombre, timeout=timeout,
            reintentos=reintentos)

    async def escribir_por_bloques(
            self, bloque: bytes, *,
            timeout: float = TIMEOUT,
            reintentos: int = REINTENTOS,
            pausa: float = p.WRITE_BLOCK_PAUSE_SOFT) -> bool:
        """El otro camino de escritura: el bloque no entra en un report.

        Solo lo usa cmd 9 (macros), que mide 111 bytes y viaja partido en dos
        tramas de 59 + 52 con el numero de bloque donde iria el opcode. El
        dongle acusa `0xC0` despues de cada trama y el `0xC1` -el que dice que
        el mouse aplico- **recien despues de la ultima**, asi que la espera es
        la misma de `escribir()` pero corre una sola vez, al final.

        **Un reintento reenvia la secuencia ENTERA, nunca el ultimo trozo
        suelto.** Entre las dos tramas hay una ventana en la que el mouse tiene
        medio bloque, y el trozo 0 es lo que lo reposiciona: mandarle el trozo
        1 a un mouse que perdio el 0 seria armarle un bloque Frankenstein.

        La pausa por defecto es la del **soft nativo**, MEDIDA en
        `soft-macro-asignado.pcap`. `WRITE_BLOCK_PAUSE` (0.2 s) sale del
        `Sleep(200)` del helper de la web, que es otro camino; nadie fue mas
        rapido que un segundo en el bus, asi que no hay medida del minimo y
        este no es lugar para averiguarlo.
        """
        cmd = bloque[0] if bloque else None
        if cmd != p.CMD_MACRO:
            raise ValueError(
                f"el camino por bloques es de cmd {p.CMD_MACRO} (macros) y "
                f"llego cmd {cmd}. Los demas comandos entran en un report y "
                "van por escribir()")
        nombre = p.CMD_NAMES.get(cmd, f"cmd {cmd}")
        return await self._escribir_tramas(
            p.build_write_blocks(bloque), nombre=nombre, timeout=timeout,
            reintentos=reintentos, pausa=pausa)

    async def _escribir_tramas(self, tramas: list[bytes], *, nombre: str,
                               timeout: float, reintentos: int,
                               pausa: float = 0.0) -> bool:
        """Manda una o varias tramas y espera un unico acuse, con reintentos.

        Con una sola trama es el camino de siempre. Con varias -macros- las
        manda en orden con `pausa` entre una y otra y espera el `0xC1` despues
        de la ultima; si el dongle se queja en el medio, corta el intento y la
        vuelta siguiente reenvia desde el primer trozo.
        """
        intento = 0
        ocupados = 0
        while intento < reintentos:
            intento += 1
            self._nak.clear()
            self._ocupado.clear()
            self._escritura_ok.clear()

            cortado = False
            for i, trama in enumerate(tramas):
                self.canal.write_frame(trama)
                if i + 1 == len(tramas):
                    break
                await asyncio.sleep(pausa)
                if self._nak.is_set() or self._ocupado.is_set():
                    log.debug("%s: el dongle se quejo entre el trozo %d y el "
                              "%d; se reenvia la secuencia entera", nombre,
                              i, i + 1)
                    cortado = True
                    break
            if cortado:
                if self._ocupado.is_set() and not self._nak.is_set():
                    ocupados += 1
                    intento -= 1
                    if ocupados > REINTENTOS_OCUPADO:
                        log.warning("%s: el dongle sigue ocupado despues de "
                                    "%d intentos", nombre, ocupados)
                        return False
                    await asyncio.sleep(
                        min(PAUSA_OCUPADO * 2 ** (ocupados - 1),
                            PAUSA_OCUPADO_MAXIMA))
                else:
                    # NAK en el medio de la secuencia. La misma pausa que da
                    # el camino de una sola trama antes de reintentar: el
                    # dongle acaba de quejarse y reenviarle las dos tramas en
                    # el mismo instante es pedirle otro NAK.
                    await asyncio.sleep(0.15)
                continue

            espera_ok = asyncio.create_task(self._escritura_ok.wait())
            espera_nak = asyncio.create_task(self._nak.wait())
            espera_ocupado = asyncio.create_task(self._ocupado.wait())
            try:
                await asyncio.wait(
                    {espera_ok, espera_nak, espera_ocupado},
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                for tarea in (espera_ok, espera_nak, espera_ocupado):
                    tarea.cancel()

            if self._escritura_ok.is_set():
                log.info("%s: escritura aplicada (0xC1)", nombre)
                return True

            if self._ocupado.is_set() and not self._nak.is_set():
                ocupados += 1
                intento -= 1
                if ocupados > REINTENTOS_OCUPADO:
                    log.warning("%s: el dongle sigue ocupado despues de %d "
                                "intentos", nombre, ocupados)
                    return False
                pausa = min(PAUSA_OCUPADO * 2 ** (ocupados - 1),
                            PAUSA_OCUPADO_MAXIMA)
                await self._dormir_salvo_evento(self._escritura_ok, pausa)
                if self._escritura_ok.is_set():
                    log.info("%s: escritura aplicada (0xC1), llego durante la "
                             "pausa de 'ocupado'", nombre)
                    return True
                continue

            motivo = "NAK del dongle" if self._nak.is_set() else "timeout"
            log.debug("%s: %s, reintento %d/%d", nombre, motivo, intento,
                      reintentos)
            await self._dormir_salvo_evento(self._escritura_ok, 0.15)
            if self._escritura_ok.is_set():
                log.info("%s: escritura aplicada (0xC1), llego despues del %s",
                         nombre, motivo)
                return True

        log.warning("%s: sin acuse de escritura despues de %d intentos",
                    nombre, reintentos)
        return False
