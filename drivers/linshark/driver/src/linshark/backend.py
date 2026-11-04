# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Backends: lo que hay del otro lado del puente, despues del WebSocket."""

from __future__ import annotations

import abc
import asyncio
import logging
from collections.abc import Awaitable, Callable

from . import estructuras
from . import protocol as p
from .device import Device
from .hidraw import HidrawChannel, find_config_hidraw, verificar_nodo_dongle

log = logging.getLogger("linshark.backend")

# Comandos que estan en `p.WRITABLE` -o sea: su formato de escritura paso la
# Etapa 2- pero que este backend no sabe mandar, porque van por el camino
# multi-bloque. Hoy es uno solo.
SIN_CAMINO_EN_EL_BACKEND = frozenset({p.CMD_MACRO})

# **Pausa minima entre dos escrituras seguidas al mouse.**
#
# La pagina oficial mando, una vez, **seis escrituras de report rate en
# tres segundos** -1000, 500, 8000, 4000, 2000, 1000- porque el usuario estuvo
# tocando el control mientras el puente esperaba la confirmacion, y el
# navegador las encolo todas. El mouse dejo de mover el puntero y hubo que
# sacarlo del modo dongle y volver.
#
# Reconfigurar la radio seis veces en tres segundos no es algo que el driver
# oficial haga nunca: en sus capturas **nunca manda dos escrituras a menos de
# un segundo** (1.008 s de pausa, la misma que usa para los bloques de macro).
# Asi que el puente espacia lo que le llegue encimado, en vez de reenviarselo
# al mouse tal cual.
PAUSA_ENTRE_ESCRITURAS = p.WRITE_BLOCK_PAUSE_SOFT


Emit = Callable[[str], Awaitable[None]]
"""Funcion para empujarle un mensaje (string hex) a la pagina."""


class Backend(abc.ABC):
    """Interfaz que consume el servidor WebSocket."""

    @abc.abstractmethod
    async def start(self, emit: Emit) -> None:
        """Se llama cuando la pagina abre la conexion."""

    @abc.abstractmethod
    async def handle(self, request: p.Request, emit: Emit) -> None:
        """Se llama por cada mensaje que manda la pagina."""

    async def stop(self) -> None:
        """Se llama cuando la pagina cierra la conexion."""


class StubBackend(Backend):
    """Fase 0: simula un mouse sin tocar el hardware.

    Sirve para dos cosas:

    1. Validar que Brave/Chrome deja abrir ws://localhost:10086 desde una
       pagina HTTPS, y que la web acepta nuestro handshake y nos rutea a
       /ATTACKSHARK/factoryX8Pro.
    2. Grabar exactamente que bytes manda la pagina por cada accion de la
       interfaz, que es lo que necesitamos para escribir el backend real.

    No abre ningun /dev/hidraw. Riesgo cero para el mouse.
    """

    def __init__(
        self,
        connection_method: int = p.CONN_WIRELESS,
        device_id: int = p.DEVICE_X8_PRO,
        battery_level: int = 100,
        ack_writes: bool = True,
        presence_period: float = 2.0,
    ):
        self.connection_method = connection_method
        self.device_id = device_id
        self.battery_level = battery_level
        self.ack_writes = ack_writes
        self.presence_period = presence_period
        self._heartbeat: asyncio.Task | None = None

    async def start(self, emit: Emit) -> None:
        # La pagina espera primero la version; si no coincide con [3,5]
        # muestra el cartel de "actualiza el driver", y si es < 3.0 desactiva
        # toda la funcionalidad de lectura.
        await emit(p.version_message())
        await emit(self._presence())
        self._heartbeat = asyncio.create_task(self._keep_alive(emit))

    async def _keep_alive(self, emit: Emit) -> None:
        """El helper real repite la presencia; la pagina la trata como idempotente.

        Sin esto, si la pagina se recarga o pierde el mouseArr, no se recupera.
        """
        try:
            while True:
                await asyncio.sleep(self.presence_period)
                await emit(self._presence())
        except asyncio.CancelledError:
            pass

    def _presence(self) -> str:
        return p.presence_message(
            self.connection_method,
            self.device_id,
            battery_status=p.BATTERY_UNKNOWN,
            battery_level=self.battery_level,
        )

    async def handle(self, request: p.Request, emit: Emit) -> None:
        if request.is_read:
            # Todavia no tenemos datos reales que devolver. La pagina tiene un
            # timeout propio que cierra el overlay de carga, asi que callarse
            # es seguro.
            return
        if self.ack_writes:
            # Ack FALSO: no hay hardware ni nada persistido. Esta puesto para
            # que la pagina cierre su overlay de "guardando" y se pueda seguir
            # navegando la interfaz, pero no confirma ningun cambio real.
            log.info("  (stub) ack FALSO de escritura, no se guardo nada")
            await emit(p.ack_message(self.connection_method, self.device_id))

    async def stop(self) -> None:
        if self._heartbeat is not None:
            self._heartbeat.cancel()
            self._heartbeat = None


def _adaptar_report_rate(data: bytes) -> bytes:
    """El mouse devuelve el report rate empaquetado; la pagina lo quiere pelado.

    Al ESCRIBIR, la pagina arma el byte como `rateRadio<<4 | rateRadio`
    (se ve en indexX8Pro: `o = parameterX8Pro.rateRadio<<4 | rateRadio`).
    Al LEER, en cambio, `handleLegacyReportRateResponse` toma n[5] y lo mete
    crudo en `rateRadio`, o sea que espera el indice pelado.

    Esa conversion la hacia el helper. Sin ella la pagina recibe 0x44 = 68,
    que no es un indice valido, y no muestra ninguna frecuencia.

    **El indice es el nibble ALTO.** Antes aca se enmascaraba con `0x0F`, o sea
    que se tomaba el bajo. Andaba de casualidad: la pagina escribe los dos
    nibbles iguales, y el mouse estuvo en 0x44 todo el tiempo que se probo. Con
    cualquier otro estado devolvia 1000 Hz siempre, incluido el de FABRICA
    (0x34 = 500 Hz).

    MEDIDO con una barrida anotada de las siete frecuencias:
    `dev/models/attackshark-x8pro/docs/capturas-w/soft-rates-anotados.txt`. El soft mueve solo el nibble
    alto y deja el bajo en 4, asi que esa captura los separa; la de la web no
    podia, porque escribe los dos iguales.
    """
    if len(data) < 2:
        return data
    salida = bytearray(data)
    salida[1] = p.rate_indice(salida[1])
    return bytes(salida)


# Adaptadores de respuesta: el helper oficial no reenvia los datos crudos del
# mouse, hace algunas conversiones. Cada entrada esta justificada contra el
# handler de la pagina que consume ese comando.
ADAPTADORES = {
    p.CMD_REPORT_RATE: _adaptar_report_rate,
}


# Umbral de bateria por debajo del cual no se escribe. Lo pide la Etapa 3 de
# `dev/docs/metodo.md`: una interrupcion a mitad de una escritura es el escenario
# que no queremos, y el mouse se apaga solo cuando se queda sin carga.
BATERIA_MINIMA = 50


class Mode:
    """Cuanto se le permite a la pagina llegar hasta el mouse."""

    LISTEN = "listen"  # abre el hidraw y solo escucha. No escribe nunca.
    READ = "read"      # ademas traduce las lecturas (0xF0) de la pagina.
    FULL = "full"      # ademas deja pasar escrituras, con las barandas de abajo.

    # FULL se puede elegir, cuando la Etapa 2 de
    # `dev/docs/metodo.md` quedo cumplida para report rate y dpi: el estado leido
    # del mouse, pasado por nuestro codificador, reproduce byte a byte tramas
    # que el driver oficial le mando a este mismo mouse.
    #
    # **Elegir FULL no habilita ninguna escritura por si solo.** Hay que
    # nombrar cada comando con --permitir-escritura, y solo se aceptan los de
    # `p.WRITABLE`. Ademas el modo arranca en simulacro. Ver las barandas en
    # HidrawBackend.__init__.
    ALL = (LISTEN, READ, FULL)
    TODOS_LOS_NOMBRES = (LISTEN, READ, FULL)


class HidrawBackend(Backend):
    """Backend real: habla con el mouse a traves de /dev/hidraw.

    El modo por defecto es LISTEN, que abre el dispositivo pero **no le
    escribe un solo byte**. Se sube de modo a proposito, no por descuido:
    mandarle bytes inventados al endpoint vendor de un mouse es la forma de
    caer sin querer en un comando de bootloader.
    """

    def __init__(
        self,
        connection_method: int = p.CONN_8K_B,
        device_id: int = p.DEVICE_X8_PRO,
        mode: str = Mode.LISTEN,
        path=None,
        battery_level: int = 100,
        presence_period: float = 2.0,
        permitir_escritura=(),
        simulacro: bool = True,
        bateria_minima: int = BATERIA_MINIMA,
        confirmar=None,
    ):
        if mode not in Mode.ALL:
            raise ValueError(f"modo desconocido: {mode}")

        permitidos = frozenset(permitir_escritura)

        # Abrir el modo no abre la escritura. Un `--mode full` a secas es un
        # error, no un permiso amplio: si alguien lo puso sin nombrar comandos,
        # lo mas probable es que crea que habilita todo.
        if mode == Mode.FULL and not permitidos:
            raise ValueError(
                "el modo 'full' no habilita nada por si solo: hay que nombrar "
                "cada comando con --permitir-escritura. Hoy se puede pedir "
                # Sin `SIN_CAMINO_EN_EL_BACKEND`: ofrecer macro aca seria
                # mandar a pedir algo que el propio backend rechaza dos
                # lineas mas abajo.
                + ", ".join(f"{p.CMD_NAMES.get(c, c)} ({c})"
                            for c in sorted(p.WRITABLE
                                            - SIN_CAMINO_EN_EL_BACKEND))
            )
        if permitidos and mode != Mode.FULL:
            raise ValueError(
                f"--permitir-escritura no tiene sentido en modo '{mode}': "
                "ese modo no escribe. Usa --mode full."
            )
        # **Y el backend tiene un techo mas bajo que `p.WRITABLE`.** Cmd 9
        # (macros) paso la Etapa 2 y entro a `WRITABLE`, pero
        # **este camino no sabe mandarlo**: mide 111 bytes, no entra en un
        # report y viaja partido en dos tramas por `escribir_por_bloques()`,
        # que el backend no usa. Lo escribe `driver/scripts/primera-escritura.py`,
        # que habla con `Device` directamente, de a un campo por corrida y con
        # confirmacion por terminal.
        #
        # Que el armador de tramas lo rechazaria igual por largo no alcanza:
        # esa seria una baranda por accidente, y ademas dejaria pasar un macro
        # corto. Se nombra aca, que es donde se decide.
        sin_camino = permitidos & SIN_CAMINO_EN_EL_BACKEND
        if sin_camino:
            nombres = ", ".join(f"{p.CMD_NAMES.get(c, c)} ({c})"
                                for c in sorted(sin_camino))
            raise ValueError(
                f"no se puede escribir {nombres} por este camino: el bloque no "
                "entra en un report y va partido en varias tramas, que es algo "
                "que el backend no hace. Se escribe con "
                "driver/scripts/primera-escritura.py"
            )
        # La allowlist es un techo duro, no un default. Un comando entra aca
        # recien cuando se repitio la Etapa 2 para el.
        fuera = permitidos - p.WRITABLE
        if fuera:
            nombres = ", ".join(f"{p.CMD_NAMES.get(c, c)} ({c})"
                                for c in sorted(fuera))
            raise ValueError(
                f"no se puede escribir {nombres}: su formato de escritura no "
                "paso la Etapa 2 de dev/docs/metodo.md. Escribibles hoy: "
                + ", ".join(f"{p.CMD_NAMES.get(c, c)} ({c})"
                            for c in sorted(p.WRITABLE))
            )
        self.connection_method = connection_method
        self.device_id = device_id
        self.mode = mode
        self.path = path
        self.battery_level = battery_level
        self.battery_status = p.BATTERY_UNKNOWN
        self.presence_period = presence_period
        self.permitir_escritura = permitidos
        self.simulacro = simulacro
        self.bateria_minima = bateria_minima
        # Cuando salio la ultima escritura al mouse, para no encimarle la
        # siguiente (ver PAUSA_ENTRE_ESCRITURAS).
        self._ultima_escritura = 0.0
        self._confirmar = confirmar
        self._confirmado = False
        self.channel: HidrawChannel | None = None
        self.device: Device | None = None
        self._heartbeat: asyncio.Task | None = None
        self._emit: Emit | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._visto = False
        self._conectado = False
        # asyncio no guarda referencia fuerte a las tareas sueltas: sin este
        # set el recolector puede llevarselas a mitad de camino.
        self._tareas: set[asyncio.Task] = set()

    # --- ciclo de vida ------------------------------------------------------

    async def start(self, emit: Emit) -> None:
        # La pagina puede reconectar antes de que se cierre la conexion
        # anterior (recargas rapidas, dos pestanas). Sin esto cada conexion
        # abria otro /dev/hidraw sin cerrar el previo, quedaban varios
        # lectores registrados en el loop y cada report del mouse se
        # procesaba una vez por canal colgado.
        if self.channel is not None:
            log.warning("ya habia una sesion abierta; cierro la anterior")
            await self.stop()

        self._emit = emit
        self._loop = asyncio.get_running_loop()
        self._visto = False

        if self.path is not None:
            # Nodo forzado con --hidraw: hay que confirmar que sea el del
            # dongle. El de la interfaz 2 del mouse por cable existe, se abre
            # sin quejarse, y habla otro protocolo.
            verificar_nodo_dongle(self.path)
            path = self.path
        else:
            path = find_config_hidraw()

        self.channel = HidrawChannel(path, solo_lectura=(self.mode == Mode.LISTEN))
        self.channel.on_desconexion = self._on_desconexion
        self.channel.open()
        self._conectado = True
        self.device = Device(self.channel)
        self.device.on_estado_mouse = self._on_estado_mouse
        self.channel.start_reading(self._loop, self.device.alimentar)

        log.info("modo %s sobre %s", self.mode.upper(), path)
        if self.mode == Mode.LISTEN:
            log.info("LISTEN: abierto en solo lectura, no se le puede escribir")

        await emit(p.version_message())
        await emit(self._presence())
        self._heartbeat = asyncio.create_task(self._keep_alive(emit))

    async def stop(self) -> None:
        if self._heartbeat is not None:
            self._heartbeat.cancel()
            self._heartbeat = None
        if self.channel is not None:
            self.channel.on_desconexion = None
            self.channel.close()
            self.channel = None
        self.device = None
        self._conectado = False
        for tarea in list(self._tareas):
            tarea.cancel()
        self._tareas.clear()

    async def _keep_alive(self, emit: Emit) -> None:
        try:
            while True:
                await asyncio.sleep(self.presence_period)
                if not self._conectado:
                    return
                await emit(self._presence())
        except asyncio.CancelledError:
            pass

    def _presence(self) -> str:
        return p.presence_message(
            self.connection_method, self.device_id,
            battery_status=self.battery_status,
            battery_level=self.battery_level,
        )

    # --- mouse -> pagina ----------------------------------------------------

    def _on_estado_mouse(self, datos: bytes) -> None:
        """Report ID 3: canal de notificaciones del mouse.

        El byte 1 es el tipo: 0x40/0x41 presencia con bateria, 0x10 cambio de
        nivel de DPI. Se reenvia tal cual, anteponiendo [conn, 0x01], que es
        lo que hace el helper. La notificacion de dpi son 3 bytes, no 4
        (MEDIDO, `evidencia.md`); exigir 4 siempre hacia que las
        notificaciones de DPI se perdieran.
        """
        if len(datos) < 3:
            return
        device_id, tipo = datos[0], datos[1]
        if device_id in p.MOUSE_NUM:
            self.device_id = device_id

        if tipo in (p.NOTIF_PRESENCIA, p.NOTIF_PRESENCIA_ALT):
            if len(datos) < 4:
                return
            self.battery_status, self.battery_level = datos[2], datos[3]
            if not self._visto:
                self._visto = True
                log.info("mouse detectado: %s, bateria %d%%",
                         p.MOUSE_NUM.get(device_id, device_id), datos[3])
        elif tipo == p.NOTIF_DPI:
            log.info("  el mouse cambio al nivel de DPI %d", datos[2])
        else:
            log.info("  notificacion desconocida tipo 0x%02x: %s",
                     tipo, bytes(datos).hex(" "))

        self._emitir_suelto(p.notification_message(self.connection_method, datos))

    def _emitir_suelto(self, mensaje: str) -> None:
        """Manda un mensaje a la pagina desde un callback sincronico.

        Con referencia guardada y las excepciones tragadas: estos avisos salen
        de un callback del event loop, y si la pagina se desconecto justo en el
        medio la tarea moria con ConnectionClosed sin nadie que la mirara,
        dejando el 'Task exception was never retrieved' de asyncio.
        """
        if self._emit is None or self._loop is None:
            return
        tarea = self._loop.create_task(self._emit(mensaje))
        self._tareas.add(tarea)

        def _terminada(t: asyncio.Task) -> None:
            self._tareas.discard(t)
            if t.cancelled():
                return
            exc = t.exception()
            if exc is not None:
                log.debug("no pude avisarle a la pagina: %s", exc)

        tarea.add_done_callback(_terminada)

    def _on_desconexion(self) -> None:
        """El dongle desaparecio del bus.

        Hay que decirselo a la pagina: el paquete de 3 bytes [0, 0, deviceId]
        es el que hace que saque el mouse de su mouseArr. Sin esto el puente
        seguia mandando presencia y la pagina mostraba un mouse conectado con
        bateria al 100% que ya no estaba enchufado.
        """
        if not self._conectado:
            return
        self._conectado = False
        log.warning("el mouse se desconecto; se lo aviso a la pagina")
        if self._heartbeat is not None:
            self._heartbeat.cancel()
            self._heartbeat = None
        self._emitir_suelto(
            p.unplug_message(self.connection_method, self.device_id))

    # --- pagina -> mouse ----------------------------------------------------

    async def handle(self, request: p.Request, emit: Emit) -> None:
        if self.device is None:
            return

        if request.is_read:
            if self.mode == Mode.LISTEN:
                log.info("  (LISTEN) no mando la lectura cmd=%s", request.cmd)
                return
            await self._responder_lectura(request, emit)
            return

        await self._responder_escritura(request, emit)

    async def _responder_escritura(self, request: p.Request, emit: Emit) -> None:
        """El unico camino por el que un byte de la pagina puede llegar al mouse.

        Son seis chequeos y ninguno es redundante. El orden importa: primero lo
        que no depende del contenido (modo, permiso), despues la forma de la
        trama, y al final la bateria y la confirmacion, que son las dos cosas
        que pueden cambiar entre una escritura y la siguiente.
        """
        nombre = p.CMD_NAMES.get(request.cmd, f"cmd {request.cmd}")

        def rechazar(motivo: str):
            log.warning("  BLOQUEADO (%s): %s de %d B  %s", motivo, nombre,
                        len(request.payload), p.encode(request.payload))
            return emit(p.ack_message(self.connection_method, self.device_id,
                                      ok=False))

        # 1. El modo. En listen y read no se escribe, y punto.
        if self.mode != Mode.FULL:
            await rechazar(f"modo {self.mode}")
            return

        # 2. El comando tiene que haber sido nombrado a mano en la linea de
        #    comandos. Que este en WRITABLE no alcanza: hay que pedirlo.
        if request.cmd not in self.permitir_escritura:
            await rechazar(f"{nombre} no esta en --permitir-escritura")
            return

        # 3. La trama tiene que ser una que sepamos armar. `build_write_frame`
        #    pone el opcode 0x00 por su cuenta, asi que aca lo que se valida es
        #    que el bloque de la pagina sea coherente antes de tocarlo.
        # La pagina manda el payload con relleno: para el report rate manda 15
        # bytes cuando el bloque declara 9 (MEDIDO, `w1-from-har.jsonl`:
        # `83 08 | 06 09 01 33 cc` + diez ceros). El helper oficial recorta,
        # porque la trama que sale al bus tiene largo N+5 exacto:
        #
        #     04 0e 00 | 06 09 01 44 bb 00 00 00 00 | 01 21
        #                ^^^^^ nueve bytes, que es el N declarado
        #
        # Sin recortar, `build_write_frame()` rechaza todo lo que manda la
        # pagina por incoherencia de largo.
        payload = bytes(request.payload)
        if len(payload) < 2:
            await rechazar("payload de menos de 2 bytes")
            return
        declarado = payload[1]
        if declarado < 2 or declarado > len(payload):
            await rechazar(f"el bloque declara {declarado} bytes y llegaron "
                           f"{len(payload)}")
            return
        bloque = payload[:declarado]
        try:
            trama = p.build_write_frame(bloque)
        except Exception as exc:
            await rechazar(f"no se puede armar la trama: {exc}")
            return
        if trama[2] not in p.OPCODES_VALIDOS:
            await rechazar(f"opcode {trama[2]:#04x} fuera de la lista")
            return

        # 4. Bateria. Una interrupcion a mitad de una escritura es el escenario
        #    que la Etapa 3 quiere evitar.
        if self.battery_level < self.bateria_minima:
            await rechazar(f"bateria {self.battery_level}% < "
                           f"{self.bateria_minima}%")
            return

        hexa = trama[:trama[1]].hex(" ")

        # 5. Simulacro: arma, loguea y no manda. Es el default del modo full.
        if self.simulacro:
            log.warning("  SIMULACRO: %s NO se mando. La trama seria:", nombre)
            log.warning("    %s", hexa)
            await emit(p.ack_message(self.connection_method, self.device_id,
                                     ok=False))
            return

        # 6. Confirmacion interactiva, una sola vez por sesion, mostrando la
        #    trama. Sin una forma de preguntar, no se escribe.
        if not self._confirmado:
            if self._confirmar is None:
                await rechazar("no hay forma de pedir confirmacion")
                return
            ok = await self._confirmar(nombre, hexa)
            if not ok:
                await rechazar("el usuario no confirmo")
                return
            self._confirmado = True

        # Espaciar lo que venga encimado. La pagina puede tener varias
        # escrituras encoladas -pasa si el usuario mueve un slider, o si
        # estuvieron esperando la confirmacion- y mandarselas seguidas al
        # mouse le cuelga el stream de movimiento.
        ahora = asyncio.get_running_loop().time()
        espera = PAUSA_ENTRE_ESCRITURAS - (ahora - self._ultima_escritura)
        if espera > 0:
            log.info("  espaciando %.2f s: el driver oficial nunca manda dos "
                     "escrituras mas pegadas", espera)
            await asyncio.sleep(espera)

        log.warning("  ESCRIBIENDO %s: %s", nombre, hexa)
        self._ultima_escritura = asyncio.get_running_loop().time()
        aplicada = await self.device.escribir(bloque)
        log.warning("  %s: %s", nombre,
                    "aplicada (0xC1)" if aplicada else "SIN ACUSE")
        await emit(p.ack_message(self.connection_method, self.device_id,
                                 ok=aplicada))

    async def _responder_lectura(self, request: p.Request, emit: Emit) -> None:
        nombre = p.CMD_NAMES.get(request.cmd, f"cmd {request.cmd}")
        if request.cmd not in p.READ_SUB:
            # Pasa con CMD_WAKEUP (7), que la pagina pide pero no esta en la
            # tabla del binario. Se calla y sigue: la pagina tiene su propio
            # timeout para el overlay de carga. Antes esto era un KeyError sin
            # capturar que se llevaba puesta la conexion WebSocket entera.
            log.warning("  %s: no lo se pedir (no hay sub documentado), lo ignoro",
                        nombre)
            return
        # La pagina manda siempre sub=0; el sub real lo pone build_read_frame()
        # con la tabla que sacamos del binario del helper oficial.
        #
        # **Menos para cmd 9, que se lee con el ID DEL MACRO en el byte 5.**
        # Es la rareza que quedo MEDIDA: los demas comandos
        # llevan ahi el perfil, y el macro lleva su id. Sin pasarlo, cualquier
        # macro que pida la pagina vuelve como el macro 1 -o sea vacio, si no
        # existe-. La pagina lo manda en `sub`
        # (`sendMacroDataCommand(macroId)` del bundle).
        macro_id = request.sub if request.cmd == p.CMD_MACRO else None
        frame = await self.device.leer(request.cmd, macro_id=macro_id)
        if frame is None:
            log.warning("  %s: el mouse no contesto", nombre)
            return

        datos = frame.data
        adaptador = ADAPTADORES.get(frame.cmd)
        if adaptador is not None:
            crudo = datos
            datos = adaptador(datos)
            if datos != crudo:
                log.debug("  %s: adaptado %s -> %s", nombre,
                          crudo[:8].hex(), datos[:8].hex())

        # La pagina espera [connectionMethod, deviceId, cmd, sub, ...datos]:
        # lee el cmd en n[2] y el sub en n[3].
        mensaje = p.encode(
            bytes([self.connection_method, self.device_id, frame.cmd, frame.sub])
            + datos
        )
        legible = estructuras.describir(frame.cmd, frame.data)
        log.info("  %s: %d B de datos%s", nombre, len(datos),
                 f"  ({legible})" if legible else "")
        await emit(mensaje)
