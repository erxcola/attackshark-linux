# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""El puente entre `linshark` (asyncio) y Qt (su propio reactor).

**Por que un hilo y no `qasync`.** `linshark` es asyncio de punta a punta y sus
esperas no son cortas: el respaldo completo de los siete comandos tarda varios
segundos, y el camino multi-trama de cmd 9 duerme 1.008 s entre bloques. Una
llamada sincrona desde el hilo de la ventana la congela, y el compositor la
marca como "no responde".

Las dos salidas que la auditoria (G-04) propuso son `qasync` -unificar los dos
reactores- o un hilo de trabajo. Se eligio el hilo:

  * **no agrega una dependencia** para algo que la biblioteca estandar hace;
  * **aisla de verdad**: el hilo de la ventana nunca toca el dispositivo, asi
    que ninguna espera del protocolo puede trabarla, ni siquiera por error;
  * y el loop propio va bien con `loop.add_reader()` sobre el fd de hidraw,
    que es como `HidrawChannel` escucha al mouse.

**Las señales de Qt cruzan hilos solas**: emitirlas desde el hilo de hardware
las encola en el de la ventana, que es exactamente lo que hace falta. Nada de
este modulo toca widgets.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from linshark import cable
from linshark import conexiones
from linshark import dispositivos
from linshark import protocol as p
from linshark import sesion
from linshark.device import Device
from linshark.hidraw import (DeviceNotFound, FaltaLaReglaDeUdev, HidrawChannel,
                             verificar_nodo_dongle)

log = logging.getLogger("linshark_ui.hardware")


class Hardware(QObject):
    """El mouse, visto desde el hilo de la ventana.

    Todo lo que devuelve sale por señales, nunca por retorno: quien llama pide
    y sigue. `conectar()` arranca el hilo; `cerrar()` lo baja.
    """

    #: El estado entero, ya leido (`sesion.leer_estado`).
    estado = Signal(dict)
    #: Una linea de progreso, lista para una barra de estado.
    progreso = Signal(str)
    #: Algo que el mouse aviso solo: bateria, cambio de nivel de dpi.
    novedad = Signal(object)
    #: `sesion.Resultado` de una escritura.
    escritura_lista = Signal(object)
    #: Algo salio mal. El segundo argumento es el comando de arreglo cuando lo
    #: hay -hoy, la regla de udev-, para que la ventana ofrezca un boton en vez
    #: de un texto.
    problema = Signal(str, str)
    #: El nodo quedo abierto y el mouse contesta.
    conectado = Signal(str)
    #: **El nodo desaparecio del bus.** Lo dice el propio canal cuando el
    #: kernel contesta `ENODEV`/`EIO`: desenchufar el dongle -o moverlo de
    #: puerto- deja el descriptor muerto. Antes el canal avisaba y
    #: **nadie lo escuchaba**: la ventana seguia mostrando "conectado a
    #: /dev/hidraw2" sobre un nodo que ya no existia.
    desconectado = Signal(str)
    #: El mouse dijo que modelo es. El segundo argumento es su nombre, o
    #: vacio si no figura ni en el catalogo del bundle.
    modelo_detectado = Signal(int, str)
    #: A que tasa hay que devolver el mouse mientras dure la configuracion, o
    #: `0` cuando no se le debe nada. **La ventana lo tiene que mostrar**: la
    #: tasa esta prestada, no cambiada, y quien mira tiene derecho a saber que
    #: su mouse esta a 1000 Hz en este momento y por que.
    tasa_prestada = Signal(int)
    #: Los Hz que se dejaron de deber al quedarse con la tasa puesta.
    tasa_elegida = Signal(int)
    #: `True` cuando arranca una escritura y `False` cuando no queda ninguna.
    #: **Lo dice el hardware, no lo adivina la ventana.** Antes la ventana
    #: bloqueaba al llamar a `escribir()` y desbloqueaba con `escritura_lista`
    #: o con `problema`, y ese `problema` podia ser de otra cosa -el aviso de
    #: un modelo desconocido llega de una novedad, en cualquier momento-, asi
    #: que la pantalla se desbloqueaba en el medio de una Etapa 3.
    ocupado = Signal(bool)

    def __init__(self, nodo: Path | None = None, parent=None, *, device=None):
        """`device` existe para poder probar esto sin un mouse enfrente.

        Con el, `abrir()` no toca ningun nodo y usa lo que le den —la misma
        puerta que `driver/scripts/primera-escritura.py` tiene, y
        por el mismo motivo: sin ella, la unica forma de ejercer este codigo
        seria el mouse de verdad.
        """
        super().__init__(parent)
        self._nodo_pedido = nodo
        self._device_de_prueba = device
        self._loop: asyncio.AbstractEventLoop | None = None
        self._hilo: threading.Thread | None = None
        self._canal = None
        self._device = None
        self._listo = threading.Event()
        #: **Una escritura por vez.** Dos Etapa 3 encimadas se pisan de tres
        #: maneras: dos respaldos completos compitiendo por el enlace, dos
        #: lecturas del paso 2 que pueden ver el bloque a medio cambiar, y el
        #: paso 0 restaurando la tasa mientras la otra la necesita baja.
        self._candado = asyncio.Lock()
        self._escrituras = 0
        #: El device id que el mouse dijo ser, cuando lo dijo. Llega en las
        #: novedades del Report ID 3, no se puede pedir.
        self._device_id: int | None = None
        #: **La sesion de configuracion**, que es lo que hace que la ventana
        #: pueda escribirle a un mouse que esta a 8000 Hz sin colgarse: baja la
        #: tasa una vez y lee el estado una vez, en vez de las dos lecturas
        #: completas y las dos escrituras de rate **por campo** que hacia cada
        #: `sesion.aplicar()` aislado. Ver `sesion.Configuracion`.
        self._config: sesion.Configuracion | None = None

    # --- el hilo ---------------------------------------------------------

    def conectar(self) -> None:
        """Arranca el hilo de hardware y abre el nodo. Vuelve enseguida."""
        if self._hilo is not None:
            return
        self._hilo = threading.Thread(target=self._correr, name="linshark-hw",
                                      daemon=True)
        self._hilo.start()
        self._listo.wait(timeout=5)

    def _correr(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._listo.set()
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    #: Cuanto se espera, al cerrar, a que termine lo que este en vuelo.
    #: **No es prolijidad**: el camino multi-trama de cmd 9 manda dos tramas
    #: con 1.008 s en el medio, y cortar ahi deja al mouse con medio bloque de
    #: macro —es el mismo riesgo que el CLI anuncia como "no desenchufes el
    #: dongle ahi"—. Cerrar la ventana no puede ser peor que eso.
    ESPERA_AL_CERRAR = 15.0

    def cerrar(self, espera: float | None = None) -> None:
        """Cierra el nodo y baja el hilo. Se puede llamar dos veces.

        **Espera a que termine lo que este escribiendo**, no lo mata.

        La segunda vez el loop ya no es None sino **cerrado** -`_correr()` lo
        cierra en su `finally` y `self._loop` sigue apuntando ahi-, y pedirle
        algo revienta con `RuntimeError`: cerrar la ventana y despues el
        hardware lo hacia. Por eso se miran las dos cosas.
        """
        if self._loop is None or self._loop.is_closed():
            return
        fut = asyncio.run_coroutine_threadsafe(
            self._cerrar(self.ESPERA_AL_CERRAR if espera is None else espera),
            self._loop)
        try:
            fut.result(timeout=(espera or self.ESPERA_AL_CERRAR) + 5)
        except Exception:                          # noqa: BLE001
            log.warning("no pude cerrar limpio el hilo de hardware")
        self._loop.call_soon_threadsafe(self._loop.stop)
        if self._hilo is not None:
            self._hilo.join(timeout=5)
        self._hilo = None

    async def _cerrar(self, espera: float) -> None:
        # Primero lo que este en vuelo, y recien despues el nodo. Al reves
        # seria cerrarle el descriptor a una escritura a medio mandar.
        pendientes = [t for t in asyncio.all_tasks(asyncio.get_running_loop())
                      if t is not asyncio.current_task() and not t.done()]
        if pendientes:
            self.progreso.emit(
                f"esperando a que termine lo que esta andando "
                f"({len(pendientes)})…")
            listas, faltan = await asyncio.wait(pendientes, timeout=espera)
            if faltan:
                # Se dice y se cancela: dejar el hilo colgado seria peor, pero
                # el que mira tiene que saber que algo quedo a medias.
                log.warning("%d tarea(s) no terminaron en %.0f s; las corto",
                            len(faltan), espera)
                self.problema.emit(
                    f"{len(faltan)} operacion(es) no terminaron a tiempo y se "
                    "cortaron. Si estabas grabando un macro, revisalo con "
                    "driver/scripts/respaldar.py antes de confiar en el", "")
                for t in faltan:
                    t.cancel()
        # **La tasa se devuelve antes de cerrar el nodo.** Es lo ultimo que
        # el mouse espera de nosotros: quedo a 1000 Hz porque se la pedimos
        # prestada para poder leerlo, y cerrar la ventana sin devolverla seria
        # cambiarle al usuario algo que no pidio, en silencio y para siempre.
        if self._config is not None and self._config.tasa_prestada is not None:
            self.progreso.emit(
                f"devolviendo la tasa a {self._config.tasa_prestada} Hz…")
            try:
                await self._config.soltar()
            except Exception as exc:               # noqa: BLE001
                log.warning("no pude devolver la tasa: %s", exc)
                self.problema.emit(
                    "no pude devolver la tasa al cerrar. Revisala con "
                    "driver/scripts/cambiar-rate.py", "")
        self._config = None
        if self._canal is not None:
            self._canal.close()
        self._canal = None
        self._device = None

    def _al_haber_novedad(self, novedad) -> None:
        """Reenvia la novedad y, la primera vez, mira **que modelo es**.

        **Antes el codigo le hablaba a cualquier mouse que
        contestara**, asumiendo que era un X8 Pro. Todo lo que hay esta medido
        contra ese y solo contra ese -los tamaños de bloque, los dieciocho
        slots, la permutacion de los slots 4, 5 y 6-, asi que escribirle a otro
        modelo con estos offsets es mandarle bytes que nadie verifico. El
        device id llega solo en el Report ID 3: es la primera oportunidad que
        hay de notarlo.
        """
        # **El unico camino medido por el que el mouse se mueve solo.** Al
        # ciclar el dpi con su boton, el firmware escribe
        # `Current_Dpi_level_flag` y lo avisa por el Report ID 3: el estado
        # cacheado deja de describir al mouse y no puede seguir sirviendo de
        # red. La ventana ya avisaba que lo que se ve es de antes; esto hace
        # que ademas **no se escriba sobre un respaldo viejo**.
        if novedad.nivel_dpi is not None and self._config is not None:
            if sesion.via_de(self._device) == conexiones.VIA_CABLE:
                # **Por cable se relee, en vez de pedir que relean.** La
                # unica forma honesta de mostrar el cambio es releer, y por
                # cable el bloque de dpi y el perfil que lo embebe tardan un
                # segundo: no hay radio. Si no contestan, el cache se
                # invalida igual que por el dongle.
                self._pedir(self._releer_el_dpi())
            else:
                self._config.invalidar("el mouse cambio de nivel de dpi solo")
        self.novedad.emit(novedad)
        if novedad.device_id and self._device_id is None:
            self._device_id = novedad.device_id
            try:
                perfil = dispositivos.perfil_de(novedad.device_id)
            except dispositivos.ModeloDesconocido as exc:
                nombre, _ = dispositivos.catalogo().get(
                    novedad.device_id, ("", None))
                self.modelo_detectado.emit(novedad.device_id, nombre)
                self.problema.emit(str(exc), "")
                return
            # **Y se le habla con ese perfil.** `perfil_de()` solo devuelve
            # modelos medidos -cualquier otro levanta `ModeloDesconocido` y se
            # fue por el `except` de arriba-, asi que activar el que devolvio
            # no es creerle al device id: es usar lo que hay medido de el.
            # Hoy es el X8 Pro y ya estaba puesto; el dia que haya un segundo
            # perfil, esta linea es la que hace que se decodifique con el suyo.
            dispositivos.usar(perfil)
            self.modelo_detectado.emit(perfil.device_id, perfil.nombre)

    async def _releer_el_dpi(self) -> None:
        if self._config is None or self._config.estado is None:
            return
        async with self._candado:
            estado = await self._config.refrescar(p.CMD_DPI, p.CMD_PROFILE)
        if estado is not None:
            self.estado.emit(estado)

    def _nodo(self) -> str:
        return str(self._canal.path) if self._canal is not None else ""

    def _pedir(self, corrutina) -> bool:
        """Manda trabajo al hilo de hardware, sin esperarlo. Dice si entro.

        **Si no entra, la corrutina se cierra y se avisa que no entro.** Los
        dos importan:

          * una corrutina creada y nunca esperada queda colgada, y lo unico que
            Python dice es un `RuntimeWarning` que nadie mira;
          * y quien la pidio se queda esperando una señal que no va a llegar.
            `escribir()` bloquea la pantalla **antes** de pedir -para que un
            segundo click no entre en el medio- y la desbloquea con `ocupado`,
            que se emite adentro de la corrutina: si la corrutina no arranca
            nunca, la ventana queda muerta para siempre.

        El loop tambien puede estar **cerrado** y no en None: `cerrar()` baja el
        hilo y el loop se cierra en su `finally`, pero `self._loop` sigue
        apuntando ahi. Ahi `run_coroutine_threadsafe` tira `RuntimeError`, que
        sin este `try` sale por el medio de un slot de Qt.
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            corrutina.close()
            self.problema.emit("el hilo de hardware no esta andando", "")
            return False
        envoltorio = self._envolver(corrutina)
        try:
            asyncio.run_coroutine_threadsafe(envoltorio, loop)
        except RuntimeError as exc:
            # se cerro entre el chequeo y el encolado
            envoltorio.close()
            corrutina.close()
            self.problema.emit(f"no pude encolar el pedido: {exc}", "")
            return False
        return True

    # **`_pedir` no emite `ocupado`, y es a proposito.** Por aca pasan tambien
    # `abrir()` y `leer_estado()`, que no son escrituras: decir "no hay ninguna
    # escritura andando" porque fallo una lectura es afirmar algo sobre otra
    # cosa. Quien bloqueo la pantalla es `escribir()`, y es el que la suelta
    # -mirando el contador, por si hubiera otra escritura de verdad-.

    async def _envolver(self, corrutina) -> None:
        """Ningun error del protocolo puede matar el hilo en silencio."""
        try:
            await corrutina
        except FaltaLaReglaDeUdev as exc:
            # El unico problema que tiene un arreglo de una linea, asi que
            # viaja con el comando y la ventana puede ofrecerlo (G-05).
            self.problema.emit(str(exc), exc.comando)
        except (DeviceNotFound, OSError, ValueError) as exc:
            self.problema.emit(str(exc), "")
        except Exception as exc:                   # noqa: BLE001
            log.exception("error inesperado en el hilo de hardware")
            self.problema.emit(f"{type(exc).__name__}: {exc}", "")

    # --- lo que se le puede pedir ----------------------------------------

    def abrir(self) -> None:
        """Abre el nodo del dongle y engancha las novedades."""
        self._pedir(self._abrir())

    async def _abrir(self) -> None:
        if self._device is not None:
            return
        if self._device_de_prueba is not None:
            self._device = self._device_de_prueba
            self._armar_sesion()
            sesion.escuchar_novedades(self._device, self._al_haber_novedad)
            self.conectado.emit("(device inyectado)")
            return
        nodo = self._nodo_pedido
        if nodo is not None:
            verificar_nodo_dongle(nodo)
        else:
            # **Por donde, lo decide el bus**: si el mouse esta por cable, el
            # dongle no contesta (MEDIDO), y `elegir()` da el cable.
            try:
                conexion = conexiones.elegir()
            except conexiones.NoHayCanal as exc:
                if exc.por_permisos:
                    sin_permiso = next(c for c in exc.conexiones
                                       if c.falta_la_regla_de_udev)
                    raise FaltaLaReglaDeUdev(
                        str(exc),
                        path=sin_permiso.nodo_de_configuracion.path) from None
                raise DeviceNotFound(str(exc)) from None
            if conexion.via == conexiones.VIA_CABLE:
                await self._abrir_por_cable(conexion)
                return
            nodo = conexion.nodo_de_configuracion.path
        canal = HidrawChannel(nodo)
        canal.open()
        canal.on_desconexion = lambda: self._al_desconectarse(str(nodo))
        device = Device(canal)
        canal.start_reading(asyncio.get_running_loop(), device.alimentar)
        # Lo que el mouse avisa solo: bateria cada 2-4 s, y el cambio de nivel
        # de dpi cuando el usuario aprieta el boton. Sin esto la ventana queda
        # mostrando un nivel viejo (G-03).
        sesion.escuchar_novedades(device, self._al_haber_novedad)
        self._canal, self._device = canal, device
        self._armar_sesion()
        self.conectado.emit(str(nodo))

    async def _abrir_por_cable(self, conexion) -> None:
        """El mismo `_abrir()`, por el cable: otro device, la misma sesion.

        El modelo lo dice el propio dispositivo USB, que es de un modelo
        medido o `conexiones` no le habria dado perfil: no hace falta esperar
        al Report ID 3. Ese se escucha igual -el descriptor del cable lo
        declara-, por el aviso del boton de dpi y la bateria.
        """
        device = cable.abrir(conexion)
        device.on_desconexion = lambda: self._al_desconectarse(str(device.path))
        device.start_reading(asyncio.get_running_loop())
        # El Report ID 3 por cable, si llega: el cambio de nivel de dpi con el
        # boton y la bateria, igual que por el dongle (ver `cable.py`).
        sesion.escuchar_novedades(device, self._al_haber_novedad)
        self._canal, self._device = device, device
        if conexion.perfil is not None:
            dispositivos.usar(conexion.perfil)
            # **El modelo ya lo dijo el USB**, y queda anotado: si el Report ID
            # 3 llega por cable con otro byte de id -no esta medido que traiga
            # el mismo-, no se lo toma por un modelo desconocido.
            self._device_id = conexion.perfil.device_id
            self.modelo_detectado.emit(conexion.perfil.device_id,
                                       conexion.perfil.nombre)
        self._armar_sesion()
        self.conectado.emit(str(device.path))

    def _al_desconectarse(self, nodo: str) -> None:
        """El nodo se fue del bus. Se limpia y se avisa; no se reabre solo.

        Reabrir por nuestra cuenta seria adivinar: el dongle puede haber
        cambiado de puerto, o puede no estar. Quien decide es la ventana, que
        mira el bus y **ve** si aparecio otra vez (`conexiones.buscar()`).
        """
        self._canal = None
        self._device = None
        self._config = None
        self._device_id = None
        self.desconectado.emit(nodo)

    def reconectar(self) -> None:
        """Cierra lo que haya y vuelve a abrir el nodo que corresponda ahora.

        Es lo que hace falta cuando el dongle cambio de puerto: el descriptor
        viejo apunta a un nodo que ya no existe, y el nuevo puede tener otro
        numero. **No baja el hilo**: `cerrar()` es para cerrar la aplicacion.
        """
        self._pedir(self._reconectar())

    async def _reconectar(self) -> None:
        if self._canal is not None:
            try:
                self._canal.close()
            except Exception:                      # noqa: BLE001
                log.warning("no pude cerrar el canal viejo", exc_info=True)
        self._canal = None
        self._device = None
        self._config = None
        self._device_id = None
        await self._abrir()

    def _armar_sesion(self) -> None:
        """La sesion de configuracion, con los avisos ya enchufados."""
        self._config = sesion.Configuracion(
            self._device, nodo=self._nodo(),
            al_leer=lambda l: self.progreso.emit(_linea_de_lectura(l)),
            al_reintentar=lambda faltan, espera: self.progreso.emit(
                sesion.aviso_de_reintento(
                    faltan, espera, via=sesion.via_de(self._device)).strip()),
            al_cortar=lambda faltan, motivo: self.progreso.emit(
                " ".join(motivo.split())),
            al_avisar=lambda t: self.progreso.emit(_legible(t)))

    def leer_estado(self, macros_extra=()) -> None:
        """Lee el mouse entero. Tarda varios segundos: por eso esto existe."""
        self._pedir(self._leer_estado(tuple(macros_extra)))

    async def _leer_estado(self, macros_extra) -> None:
        """Lee el mouse entero, **bajando la tasa si hace falta**.

        Antes esto llamaba a `sesion.leer_estado()` pelado, asi
        que con el mouse a 2000 Hz o mas la lectura salia siempre incompleta:
        los bloques largos no llegan a esa tasa (MEDIDO a 2000 y a 8000) y lo
        unico que la ventana podia hacer era mostrar el cartel diciendolo. La
        sesion lo resuelve donde corresponde -bajando la tasa una vez, y
        devolviendola despues- y de paso deja el estado cacheado, que es lo que
        hace que la primera escritura no tenga que releer nada.
        """
        if self._device is None:
            await self._abrir()
        if sesion.via_de(self._device) == conexiones.VIA_CABLE:
            self.progreso.emit("leyendo el mouse por cable…")
        else:
            self.progreso.emit("leyendo el mouse… movelo mientras tanto: así "
                               "lee más rápido")
        # **Bajo el candado**, como las escrituras: una lectura presta la tasa
        # y la anota en el estado, y "quedarse" o "devolverla" en el medio
        # dejaban un estado sin `CLAVE_TASA_BAJADA` que la ventana tomaba por
        # la lectura de al abrir, con el 1000 prestado como tasa del dueño.
        async with self._candado:
            prep = await self._config.preparar(macros_extra=macros_extra,
                                               forzar_lectura=True)
        self._avisar_tasa()
        if prep.antes is not None:
            # **Se emite tambien el estado incompleto.** Una pantalla con seis
            # campos es mas util que una vacia, y `Ventana.diagnostico_de()`
            # ya sabe decir por que falta el resto.
            self.estado.emit(prep.antes)
        if not prep.ok and prep.antes is None:
            self.problema.emit(prep.explicacion, "")

    def escribir(self, clave: str, valor, *, macro_id: int | None = None,
                 macros_extra=()) -> None:
        """Pone un campo en un valor, con la Etapa 3 entera detras.

        `macro_id` es para las tres claves de `sesion.CLAVES_DE_MACRO`, que son
        las unicas que no salen de `campos_de()`: cmd 9 se lee con el id del
        macro y no con el perfil, asi que sin el no hay bloque del que partir.
        """
        if not self._pedir(self._escribir(clave, valor, tuple(macros_extra),
                                          macro_id)):
            # La pantalla ya se bloqueo (ver `Ventana.escribir`) y `ocupado`
            # vive adentro de la corrutina que no arranco: si no se dice aca,
            # no lo dice nadie. El chequeo del contador es por si hubiera otra
            # escritura de verdad andando, que entonces sigue mandando ella.
            if self._escrituras == 0:
                self.ocupado.emit(False)

    async def _escribir(self, clave, valor, macros_extra, macro_id=None) -> None:
        self._escrituras += 1
        if self._escrituras == 1:
            self.ocupado.emit(True)
        try:
            async with self._candado:
                await self._escribir_una(clave, valor, macros_extra, macro_id)
        finally:
            # En el `finally`, como la tasa: si la escritura revienta, la
            # pantalla tiene que volver igual. Un contador y no un bool porque
            # la segunda escritura espera al candado, y avisar "libre" cuando
            # termina la primera dejaria tocar la pantalla con una corriendo.
            self._escrituras -= 1
            if self._escrituras == 0:
                self.ocupado.emit(False)

    def escribir_varios(self, cambios, *, macros_extra=()) -> None:
        """Una rafaga de `(clave, valor)`, **agrupada por comando**.

        Los campos del mismo bloque salen en una sola escritura
        (`sesion.preparar_mutaciones`). Aparte de ahorrar vueltas de Etapa 3,
        es lo unico que saca al mouse de un bloque que quedo con dos campos
        fuera de rango: uno por vez, cada escritura arrastra al otro y la
        baranda la rechaza.
        """
        for m in sesion.preparar_mutaciones(list(cambios)):
            if not self._pedir(self._escribir_mutacion(m, tuple(macros_extra))):
                if self._escrituras == 0:
                    self.ocupado.emit(False)

    async def _escribir_mutacion(self, m, macros_extra) -> None:
        self._escrituras += 1
        if self._escrituras == 1:
            self.ocupado.emit(True)
        try:
            async with self._candado:
                await self._correr_mutacion(m, macros_extra)
        finally:
            self._escrituras -= 1
            if self._escrituras == 0:
                self.ocupado.emit(False)

    async def _escribir_una(self, clave, valor, macros_extra,
                            macro_id=None) -> None:
        # El mapeo `(clave, valor) -> que escribir` vive en la biblioteca, no
        # aca: es el mismo que usa el CLI, y un test compara los dos (G-01).
        await self._correr_mutacion(
            sesion.preparar_mutacion(clave, valor, macro_id=macro_id),
            macros_extra)

    async def _correr_mutacion(self, m, macros_extra) -> None:
        if self._device is None:
            await self._abrir()
        clave = m.clave
        extra = tuple(macros_extra)
        if m.macro_id is not None:
            extra = extra + (m.macro_id,)

        async def confirmar(bloque, trama):
            # **El consentimiento es el click.** Quien llamo a `escribir()` ya
            # dijo que si; un segundo prompt seria una tecla mas sobre una
            # decision tomada. Lo que no se pierde es el registro: la trama va
            # al log igual que el CLI la imprime.
            log.info("escribiendo %s: %s", clave, bytes(trama).hex(" "))
            return True

        # **Todo pasa por la sesion, que es la que tiene la tasa y el
        # respaldo.** No es una segunda copia de la Etapa 3: `Configuracion.
        # escribir()` llama a `sesion.aplicar()`, el mismo camino que corre el
        # CLI y que `test_el_despachador_y_el_cli_dan_lo_mismo` compara.
        resultado = await self._config.escribir(
            cmd=m.cmd, codificar=m.codificar, confirmar=confirmar,
            macro_id=m.macro_id, macros_extra=extra)
        self._avisar_tasa()
        self.escritura_lista.emit(resultado)
        if resultado.despues is not None:
            self.estado.emit(resultado.despues)

    # --- la tasa prestada -------------------------------------------------

    def _avisar_tasa(self) -> None:
        """Dice cuanto se le debe al mouse. Cero es "nada"."""
        prestada = self._config.tasa_prestada if self._config else None
        self.tasa_prestada.emit(prestada or 0)

    def soltar_tasa(self) -> None:
        """Devuelve la tasa prestada, si hay alguna. Vuelve enseguida."""
        self._pedir(self._soltar_tasa())

    def quedarse_con_la_tasa(self) -> None:
        """Deja de deber la tasa: la puesta pasa a ser la elegida.

        No toca el mouse -ya esta a esa tasa-, pero **va por el hilo del
        hardware y bajo el candado**. Antes cambiaba la sesion desde el hilo de
        la ventana, y si caia en medio de una lectura, la lectura salia sin
        `CLAVE_TASA_BAJADA`: la ventana la anotaba como la de al abrir y
        "volver a como estaba" perdia la tasa del dueño. La prueba
        "quedarse con la tasa prestada" fallaba asi una de cada dos veces.
        Cuanto se debia llega por `tasa_elegida`.
        """
        self._pedir(self._quedarse_con_la_tasa())

    async def _quedarse_con_la_tasa(self) -> None:
        if self._config is None:
            return
        async with self._candado:
            debia = self._config.quedarse_con_la_tasa()
        # El estado antes que la tasa: cuando el cartel se va, la ventana ya
        # sabe que su bloque de rate dejo de ser prestado.
        if debia is not None and self._config.estado is not None:
            self.estado.emit(self._config.estado)
        self._avisar_tasa()
        if debia is not None:
            self.tasa_elegida.emit(debia)

    async def _soltar_tasa(self) -> None:
        if self._config is None or self._config.tasa_prestada is None:
            return
        async with self._candado:
            await self._config.soltar()
        self._avisar_tasa()


def _linea_de_lectura(lectura) -> str:
    """Lo que dice la barra de estado mientras el mouse contesta.

    **No es `sesion.linea_de()`**, que es la linea de la terminal: esa lleva el
    bloque decodificado -`perfil 1, nivel actual 1, dpi: ...`-, que en la
    ventana dura lo que tarda en llegar el comando siguiente y ya se ve entero
    en los controles. Esta dice que llego y cuanto, con una forma fija que la
    pantalla puede traducir.
    """
    nombre = (f"macro {lectura.macro_id}" if lectura.macro_id is not None
              else lectura.nombre)
    if lectura.entrada is None:
        return (f"{nombre}: sin respuesta, lo reintento al final"
                if lectura.reintentable else f"{nombre}: SIN RESPUESTA")
    return f"leído {nombre}: {len(lectura.entrada['datos']) // 2} B"


def _legible(aviso: str) -> str:
    """Los avisos de `sesion.aplicar()`, dichos para una barra de estado.

    Vienen con clave estable a proposito -`AVISO_RESPALDO`, `AVISO_ACUSE`, y
    los de la tasa como `clave|texto`- justamente para que quien los muestra no
    tenga que leer strings sueltos.
    """
    clave, _, detalle = aviso.partition("|")
    if clave == sesion.AVISO_TASA_BAJA:
        return detalle
    if clave == sesion.AVISO_TASA_VUELVE:
        return detalle
    if clave == sesion.AVISO_TASA_ARREGLADA:
        return detalle
    if clave == sesion.AVISO_RESPALDO_TRAIDO:
        return detalle
    if clave == sesion.AVISO_CACHE_VIEJO:
        return (f"hay que releer el mouse: {detalle}" if detalle
                else "hay que releer el mouse")
    if clave == sesion.AVISO_BLOQUE_IMPOSIBLE:
        return f"no se escribió, el bloque tiene valores imposibles: {detalle}"
    if clave == sesion.AVISO_ESTADO_INCOHERENTE:
        return f"la lectura se contradice: {detalle}"
    # **La busqueda va por `clave`, no por `aviso`.** Los que no llevan texto
    # detras son iguales de las dos formas, pero si alguien agrega uno que si
    # lo lleve y se olvida de la rama de arriba, buscar por `aviso` lo deja
    # salir crudo a la barra de estado -`relectura-acotada|...`-. Lo cuida
    # `test_los_avisos_se_dicen_en_castellano`, que recorre **todas** las
    # constantes `AVISO_*` en vez de una lista escrita a mano.
    return {
        sesion.AVISO_RESPALDO: "respaldando el mouse entero antes de escribir…",
        sesion.AVISO_RELECTURA: "releyendo para ver si el mouse aplico el cambio…",
        sesion.AVISO_RELECTURA_ACOTADA: "releyendo lo que se escribio y el "
                                        "perfil completo…",
        sesion.AVISO_ACUSE: "el dongle acuso la trama",
        sesion.AVISO_SIN_ACUSE: "sin acuse: se perdio el pedido o el formato no "
                                "le gusto al mouse",
        sesion.AVISO_CABLE_ACEPTO: "el mouse aceptó el report por cable",
        sesion.AVISO_CABLE_RECHAZO: "el mouse rechazó el report por cable, "
                                    "aun repitiéndolo",
    }.get(clave, aviso)
