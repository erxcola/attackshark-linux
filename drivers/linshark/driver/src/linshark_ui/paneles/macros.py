# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""El panel de macros: los que hay, lo que hacen, y el que se esta armando.

Un macro no es un campo escalar -tiene disparo, pasos y un nombre que el mouse
no guarda- asi que no sale de `campos_de()` sino de `modelo.macros_de()`. De
ahi vienen tambien **las advertencias**, que son lo mas importante de esta
pantalla: se muestran ANTES de grabar, no despues, porque despues ya es tarde.

Las tres que estan medidas, y por que importan aca:

  * **un macro de un solo evento no se reproduce** (MEDIDO): el
    mouse lo guarda, la relectura lo devuelve bien, y al apretar el boton no
    pasa nada. Grabarlo sin avisar es regalar una tarde de depuracion;
  * **el firmware no suelta nada al terminar**, y una tecla trabada no se
    despega apretandola: hay que desacoplar el dongle. Un macro que aprieta sin
    soltar deja el teclado tomado;
  * **el modo 1 se detiene con otro boton del MOUSE, no con una tecla**
    (MEDIDO): el nombre del fabricante -`StopOnAnyKey`- dice lo contrario. Los
    tres modos estan verificados apretando el boton.

Y una que no es medicion sino aritmetica: un macro tiene que estar **asignado a
un boton** para poder probarlo. El panel lo dice, porque un macro huerfano se
escribe y se relee perfecto sin que nada lo ejecute nunca.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QElapsedTimer, Signal
from PySide6.QtWidgets import (QFrame, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                               QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from linshark import estructuras as est
from linshark import modelo
from linshark.nombres import NombresDeMacro

from .. import teclado
from ..controles import DesplegableSinRueda
from ..i18n import tr


#: Las notas fijas del panel. Lo medido que hay detras queda aca y no en la
#: pantalla: el mouse no tiene un indice de macros que se pueda pedir -la
#: lectura trae los que algun boton apunta-; el contador solo existe en el modo
#: con contador -en los otros dos el byte va forzado a 1-; que hace el firmware
#: con el tiempo de cada evento -si espera antes o despues- no esta medido; y un
#: macro sin boton se escribe y se relee perfecto sin que nada lo ejecute.
EXPLICA_MACROS = ("Al leer el mouse solo aparecen los macros asignados a algún "
                  "botón. Para ver uno guardado sin asignar, pedilo por su ID.")
NOTA_REPETICIONES = (
    f"Las repeticiones solo se usan en el modo {est.MACRO_MODO_CON_CONTADOR} "
    f"({est.MACRO_MODOS[est.MACRO_MODO_CON_CONTADOR]}): en los otros dos no "
    "tienen efecto.")
NOTA_PASOS = ("Cada paso guarda el tiempo transcurrido desde el anterior. Para "
              "probar un macro, asignalo antes a un botón: un macro sin botón "
              "se guarda, pero nunca se ejecuta.")


def _como_se_llama(macro_id: int, propio: str | None) -> str:
    """El renglon del desplegable de macros.

    **El nombre que puso quien mira no se traduce nunca**: un macro llamado
    "atras" tiene que seguir diciendo "atras" en ingles. Solo se traduce el
    que pone la aplicacion cuando no hay ninguno.
    """
    return f"{macro_id} — {propio or tr(f'macro {macro_id}')}"


class GrabadorDeEventos(QFrame):
    """Graba apretando teclas y botones de verdad.

    Es de la aplicacion y no del protocolo: el codificador de eventos ya
    estaba: lo que faltaba era de donde sacar la lista.

    **El tiempo que se anota es el que paso desde el evento anterior.** Que
    hace el firmware exactamente con ese byte -si espera antes o despues- no
    esta medido, asi que el panel lo dice en vez de suponerlo. El primero va
    en 0: no hay nada antes de lo cual esperar.
    """

    agrego = Signal(str)
    cambio_estado = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("grabador")
        self.setProperty("grabando", "false")
        self.setFocusPolicy(Qt.StrongFocus)
        self._grabando = False
        #: La ultima tecla que se rechazo, para poder probarlo y para que el
        #: cartel vuelva a lo normal cuando entre una buena.
        self.rechazo = ""
        self._reloj = QElapsedTimer()
        caja = QVBoxLayout(self)
        caja.setContentsMargins(16, 14, 16, 14)
        self.cartel = QLabel()
        self.cartel.setAlignment(Qt.AlignCenter)
        self.cartel.setWordWrap(True)
        caja.addWidget(self.cartel)
        self._decir()

    def _decir(self, rechazo: str = "") -> None:
        if rechazo:
            texto, papel = tr(rechazo), "peligro"
        elif self._grabando:
            texto = tr("Grabando: presiona teclas y botones aquí adentro. Cada "
                       "presionar y soltar es un evento")
            papel = "aviso"
        else:
            texto = tr("El grabador está apagado. Inícialo y presiona las teclas "
                       "que quieras que el macro repita")
            papel = "tenue"
        self.cartel.setText(texto)
        self.cartel.setProperty("role", papel)
        self.cartel.style().unpolish(self.cartel)
        self.cartel.style().polish(self.cartel)

    def _rechazar(self, evento) -> None:
        """Una tecla que el bloque de macro no puede expresar. **Se dice.**

        Tragarsela es lo peor de los dos mundos: el que graba ve que no pasa
        nada y no sabe si fue el foco, el grabador o la tecla. El bloque guarda
        usages HID y hay teclas que no tienen uno.
        """
        self.rechazo = evento.text().strip() or f"{tr('código')} {evento.key()}"
        self._decir(f"Esa tecla no entra en un macro ({self.rechazo}): el "
                    "bloque guarda usages HID, y no todas las teclas tienen uno")

    def grabando(self) -> bool:
        return self._grabando

    def arrancar(self) -> None:
        self._grabando = True
        self.setProperty("grabando", "true")
        self.style().unpolish(self)
        self.style().polish(self)
        self._reloj.invalidate()
        self.setFocus()
        self._decir()
        self.cambio_estado.emit(True)

    def parar(self) -> None:
        self._grabando = False
        self.setProperty("grabando", "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self._decir()
        self.cambio_estado.emit(False)

    def anotar(self, nombre: str, direccion: str) -> None:
        """Anota un evento ya traducido. Es por donde entran las pruebas."""
        if not self._grabando:
            return
        if self._reloj.isValid():
            ms = min(int(self._reloj.elapsed()), est.MACRO_TIEMPO_MAX)
        else:
            ms = 0
        self._reloj.restart()
        if self.rechazo:
            self.rechazo = ""
            self._decir()
        self.agrego.emit(f"{nombre}:{direccion}@{ms}")

    # --- lo que Qt manda --------------------------------------------------

    def keyPressEvent(self, evento) -> None:
        if not self._grabando or evento.isAutoRepeat():
            return super().keyPressEvent(evento)
        # `modifiers()` va porque el teclado numerico son las MISMAS teclas de
        # Qt con `KeypadModifier`: sin esto el 5 del pad se grababa como el 5
        # de la fila de arriba, que es otro usage HID.
        nombre = teclado.nombre_de_tecla(evento.key(), evento.modifiers())
        if nombre is None:
            self._rechazar(evento)
            return super().keyPressEvent(evento)
        self.anotar(nombre, "abajo")
        evento.accept()

    def keyReleaseEvent(self, evento) -> None:
        if not self._grabando or evento.isAutoRepeat():
            return super().keyReleaseEvent(evento)
        nombre = teclado.nombre_de_tecla(evento.key(), evento.modifiers())
        if nombre is None:
            self._rechazar(evento)
            return super().keyReleaseEvent(evento)
        self.anotar(nombre, "arriba")
        evento.accept()

    def mousePressEvent(self, evento) -> None:
        nombre = teclado.nombre_de_boton(evento.button())
        if not self._grabando or nombre is None:
            return super().mousePressEvent(evento)
        self.anotar(nombre, "abajo")
        evento.accept()

    def mouseReleaseEvent(self, evento) -> None:
        nombre = teclado.nombre_de_boton(evento.button())
        if not self._grabando or nombre is None:
            return super().mouseReleaseEvent(evento)
        self.anotar(nombre, "arriba")
        evento.accept()


class PanelDeMacros(QScrollArea):
    """Los macros del mouse, con su disparo, sus pasos y sus advertencias."""

    #: `(clave, valor, macro_id)`. Las claves son las de
    #: `sesion.CLAVES_DE_MACRO`: cmd 9 se escribe con el id, no con el perfil.
    pidio_escribir = Signal(str, object, int)
    #: Los ids que hay que pedirle al mouse en la proxima lectura.
    pidio_releer = Signal(object)

    def __init__(self, nombres: NombresDeMacro | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.nombres = nombres if nombres is not None else NombresDeMacro()
        self._macros: dict[int, modelo.Macro] = {}
        self._extra: set[int] = set()
        self._armando = False
        #: De cual macro son los pasos que estan en el cuadro de texto. Sin
        #: esto, cambiar de macro en el desplegable dejaba los pasos del
        #: anterior a la vista, y "grabar en el mouse" los escribia en el
        #: nuevo: se perdia el macro de destino sin que nada lo dijera.
        self._pasos_de: int | None = None

        cuerpo = QWidget()
        layout_exterior = QHBoxLayout(cuerpo)
        layout_exterior.setContentsMargins(20, 16, 20, 20)
        layout_exterior.setAlignment(Qt.AlignHCenter)

        contenedor = QWidget()
        contenedor.setMaximumWidth(940)
        caja = QVBoxLayout(contenedor)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(18)
        layout_exterior.addWidget(contenedor)

        self.grupo_cual = self._grupo_de_cual()
        self.grupo_disparo = self._grupo_de_disparo()
        self.grupo_pasos = self._grupo_de_pasos()
        caja.addWidget(self.grupo_cual)
        caja.addWidget(self.grupo_disparo)
        caja.addWidget(self.grupo_pasos)
        caja.addStretch(1)
        self.setWidget(cuerpo)
        self._refrescar()

    # --- las tres cajas ---------------------------------------------------

    def _grupo_de_cual(self) -> QGroupBox:
        grupo = QGroupBox(tr("Selección de macro"))
        caja = QVBoxLayout(grupo)
        caja.setContentsMargins(16, 16, 16, 16)
        caja.setSpacing(12)

        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.cual = DesplegableSinRueda()
        self.cual.currentIndexChanged.connect(lambda _: self._refrescar())
        self.lbl_macro = QLabel(tr("Macro:"))
        fila.addWidget(self.lbl_macro)
        fila.addWidget(self.cual, 1)
        caja.addLayout(fila)

        fila2 = QHBoxLayout()
        fila2.setSpacing(10)
        self.id_extra = QSpinBox()
        self.id_extra.setRange(est.MACRO_ID_MIN, est.MACRO_ID_MAX)
        self.id_extra.setValue(est.MACRO_ID_MIN)
        self.pedir = QPushButton(tr("Pedir este ID al leer"))
        self.pedir.clicked.connect(self._al_pedir_id)
        self.lbl_extra = QLabel(tr("Agregar un ID:"))
        fila2.addWidget(self.lbl_extra)
        fila2.addWidget(self.id_extra)
        fila2.addWidget(self.pedir)
        fila2.addStretch(1)
        caja.addLayout(fila2)

        self.explica_macros = QLabel(tr(EXPLICA_MACROS))
        self.explica_macros.setProperty("role", "nota")
        self.explica_macros.setWordWrap(True)
        caja.addWidget(self.explica_macros)

        fila3 = QHBoxLayout()
        fila3.setSpacing(10)
        self.nombre = QLineEdit()
        self.nombre.setPlaceholderText(tr("Nombre (guardado en este equipo, no en el mouse)"))
        self.guardar_nombre = QPushButton(tr("Guardar nombre"))
        self.guardar_nombre.clicked.connect(self._al_guardar_nombre)
        self.lbl_nombre = QLabel(tr("Nombre:"))
        fila3.addWidget(self.lbl_nombre)
        fila3.addWidget(self.nombre, 1)
        fila3.addWidget(self.guardar_nombre)
        caja.addLayout(fila3)

        self.aviso_nombres = QLabel()
        self.aviso_nombres.setProperty("role", "aviso")
        self.aviso_nombres.setWordWrap(True)
        self.aviso_nombres.setVisible(False)
        caja.addWidget(self.aviso_nombres)
        return grupo

    def _grupo_de_disparo(self) -> QGroupBox:
        grupo = QGroupBox(tr("Disparo"))
        caja = QVBoxLayout(grupo)
        caja.setContentsMargins(16, 16, 16, 16)
        caja.setSpacing(12)

        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.modo = DesplegableSinRueda()
        for codigo, nombre in sorted(est.MACRO_MODOS.items()):
            self.modo.addItem(f"{tr(nombre)} — {tr(modelo.QUE_HACE_EL_MODO[codigo])}",
                              codigo)
        self.modo.activated.connect(self._al_elegir_modo)
        self.lbl_modo = QLabel(tr("Modo:"))
        fila.addWidget(self.lbl_modo)
        fila.addWidget(self.modo, 1)
        caja.addLayout(fila)

        self.aviso_modo = QLabel()
        self.aviso_modo.setProperty("role", "aviso")
        self.aviso_modo.setWordWrap(True)
        caja.addWidget(self.aviso_modo)

        fila2 = QHBoxLayout()
        fila2.setSpacing(10)
        self.repeticiones = QSpinBox()
        self.repeticiones.setRange(est.MACRO_REPETICIONES_MIN,
                                   est.MACRO_REPETICIONES_MAX)
        self.aplicar_rep = QPushButton(tr("Aplicar"))
        self.aplicar_rep.clicked.connect(self._al_poner_repeticiones)
        self.lbl_repeticiones = QLabel(tr("Repeticiones:"))
        fila2.addWidget(self.lbl_repeticiones)
        fila2.addWidget(self.repeticiones)
        fila2.addWidget(self.aplicar_rep)
        fila2.addStretch(1)
        caja.addLayout(fila2)

        self.nota_rep = QLabel(tr(NOTA_REPETICIONES))
        self.nota_rep.setProperty("role", "nota")
        self.nota_rep.setWordWrap(True)
        caja.addWidget(self.nota_rep)
        return grupo

    def _grupo_de_pasos(self) -> QGroupBox:
        grupo = QGroupBox(tr("Pasos (hasta 50 eventos)"))
        caja = QVBoxLayout(grupo)
        caja.setContentsMargins(16, 16, 16, 16)
        caja.setSpacing(12)

        self.eventos = QPlainTextEdit()
        self.eventos.setPlaceholderText("a:abajo@10, a:arriba@10")
        self.eventos.setFixedHeight(90)
        self.eventos.textChanged.connect(self._al_cambiar_pasos)
        caja.addWidget(self.eventos)

        self.grabador = GrabadorDeEventos()
        self.grabador.agrego.connect(self._al_grabar_evento)
        caja.addWidget(self.grabador)

        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.prender = QPushButton(tr("Iniciar grabador"))
        self.prender.setCheckable(True)
        self.prender.toggled.connect(self._al_prender)
        self.limpiar = QPushButton(tr("Limpiar"))
        self.limpiar.clicked.connect(self.eventos.clear)
        self.grabar = QPushButton(tr("Grabar en el mouse"))
        self.grabar.setProperty("role", "primario")
        self.grabar.clicked.connect(self._al_grabar)
        fila.addWidget(self.prender)
        fila.addWidget(self.limpiar)
        fila.addStretch(1)
        fila.addWidget(self.grabar)
        caja.addLayout(fila)

        self.avisos = QLabel()
        self.avisos.setProperty("role", "aviso")
        self.avisos.setWordWrap(True)
        caja.addWidget(self.avisos)

        self.nota_pasos = QLabel(tr(NOTA_PASOS))
        self.nota_pasos.setProperty("role", "nota")
        self.nota_pasos.setWordWrap(True)
        caja.addWidget(self.nota_pasos)
        return grupo

    # --- lo que llega del mouse ------------------------------------------

    def poner_estado(self, estado: dict) -> None:
        macros = modelo.macros_de(estado, self.nombres)
        self._macros = {m.id: m for m in macros}
        elegido = self.macro_id()
        self._armando = True
        self.cual.clear()
        for m in macros:
            self.cual.addItem(_como_se_llama(m.id, m.nombre_propio), m.id)
        indice = self.cual.findData(elegido)
        self.cual.setCurrentIndex(indice if indice >= 0 else 0)
        self._armando = False
        self._refrescar(desde_el_mouse=True)

    def macro_id(self) -> int | None:
        dato = self.cual.currentData()
        return int(dato) if dato is not None else None

    def elegir(self, macro_id: int) -> None:
        """Elige un macro por id. Es lo que hace un click, sin mouse."""
        indice = self.cual.findData(macro_id)
        if indice < 0:
            raise ValueError(f"el estado no trae el macro {macro_id}")
        self.cual.setCurrentIndex(indice)

    def macro(self) -> modelo.Macro | None:
        mid = self.macro_id()
        return self._macros.get(mid) if mid is not None else None

    def _refrescar(self, desde_el_mouse: bool = False) -> None:
        if self._armando:
            return
        m = self.macro()
        hay = m is not None
        for w in (self.modo, self.repeticiones, self.aplicar_rep,
                  self.eventos, self.grabar, self.prender, self.limpiar,
                  self.nombre, self.guardar_nombre):
            w.setEnabled(hay)
        if not hay:
            self.avisos.setText(tr("El estado no incluye ningún macro. Solicita un ID "
                                   "arriba y vuelve a leer."))
            return

        self.nombre.setText(m.nombre_propio or "")
        self.nombre.setPlaceholderText(tr(f"Macro {m.id} (sin nombre propio)"))
        if self.nombres.problema:
            self.aviso_nombres.setText(tr(
                f"Los nombres no se pudieron leer y no se van a guardar: "
                f"{self.nombres.problema}"))
            self.aviso_nombres.setVisible(True)

        indice = self.modo.findData(m.modo)
        if indice >= 0:
            self.modo.setCurrentIndex(indice)
        self._al_elegir_modo(self.modo.currentIndex(), escribir=False)
        # En los modos 1 y 2 no hay contador (`Macro.repeticiones` es None):
        # el control queda en el minimo, y deshabilitado por el modo.
        self.repeticiones.setValue(max(m.repeticiones or 0,
                                       est.MACRO_REPETICIONES_MIN))

        # Los pasos se recargan cuando el estado es nuevo **o cuando se cambio
        # de macro**: lo que esta escrito siempre tiene que ser de este macro.
        if desde_el_mouse or self._pasos_de != m.id:
            self.eventos.blockSignals(True)
            self.eventos.setPlainText(m.texto)
            self.eventos.blockSignals(False)
            self._pasos_de = m.id
        self._al_cambiar_pasos()

    # --- lo que pide el que mira ------------------------------------------

    def _al_pedir_id(self) -> None:
        self._extra.add(int(self.id_extra.value()))
        self.pidio_releer.emit(tuple(sorted(self._extra)))

    def macros_extra(self) -> tuple:
        return tuple(sorted(self._extra))

    def _al_guardar_nombre(self) -> None:
        mid = self.macro_id()
        if mid is None:
            return
        texto = self.nombre.text().strip()
        try:
            if texto:
                self.nombres.poner(mid, texto)
            else:
                self.nombres.borrar(mid)
            self.nombres.guardar()
        except Exception as exc:                   # noqa: BLE001
            self.aviso_nombres.setText(tr(str(exc)))
            self.aviso_nombres.setVisible(True)
            return
        indice = self.cual.findData(mid)
        if indice >= 0:
            self.cual.setItemText(indice, _como_se_llama(mid, texto or None))

    def _al_elegir_modo(self, indice: int, escribir: bool = True) -> None:
        modo = self.modo.itemData(indice)
        if modo is None:
            return
        con_contador = modo == est.MACRO_MODO_CON_CONTADOR
        self.repeticiones.setEnabled(con_contador and self.eventos.isEnabled())
        self.aplicar_rep.setEnabled(con_contador and self.eventos.isEnabled())
        # Hoy `MODO_SIN_MEDIR` es None -los tres del X8 Pro estan medidos
        # apretando el boton- y el aviso no sale nunca. El camino queda para el
        # modelo que traiga el cuarto modo que el bundle lista.
        sin_medir = (modelo.MODO_SIN_MEDIR is not None
                     and modo == modelo.MODO_SIN_MEDIR)
        self.aviso_modo.setText(
            tr(modelo.AVISO_MODO_SIN_MEDIR[:1].upper()
               + modelo.AVISO_MODO_SIN_MEDIR[1:] + ".")
            if sin_medir else "")
        self.aviso_modo.setVisible(sin_medir)
        m = self.macro()
        if escribir and m is not None and modo != m.modo:
            self.pidio_escribir.emit("macro_modo", modo, m.id)

    def _al_poner_repeticiones(self) -> None:
        m = self.macro()
        if m is None:
            return
        # **Escribir el contador implica el modo 0**, porque ese byte solo es
        # un contador ahi (`sesion.preparar_mutacion`). Sobre un macro que esta
        # en otro modo, este boton lo cambiaria **sin decirlo**, que es el
        # reproche que este proyecto le hace al cliente oficial.
        #
        # Paso de verdad (2026-09-20): el macro 17 se puso en modo 2 y un
        # `macro_repeticiones` posterior lo devolvio a 0, deshaciendo la vuelta
        # sin que nada lo avisara. El control ya se deshabilita en los otros
        # modos; esto lo hace imposible aunque se habilite por cualquier
        # camino, que es lo que hace falta cuando el estado que lo habilita
        # puede venir de una relectura.
        if m.modo != est.MACRO_MODO_CON_CONTADOR:
            self.avisos.setText(tr(
                "Las repeticiones solo existen en el modo «reproducir N "
                "veces». Cambiá el modo primero: escribirlas acá lo cambiaría "
                "sin avisar."))
            return
        self.pidio_escribir.emit("macro_repeticiones",
                                 int(self.repeticiones.value()), m.id)

    def _al_prender(self, prendido: bool) -> None:
        self.prender.setText(tr("Detener grabador") if prendido
                             else tr("Iniciar grabador"))
        (self.grabador.arrancar if prendido else self.grabador.parar)()

    def _al_grabar_evento(self, paso: str) -> None:
        texto = self.eventos.toPlainText().strip()
        self.eventos.setPlainText(f"{texto}, {paso}" if texto else paso)

    def texto_de_pasos(self) -> str:
        return self.eventos.toPlainText().strip()

    def avisos_de_los_pasos(self) -> list[str]:
        """Lo que hay que decir de lo que esta escrito **ahora**.

        Se recalcula sobre el texto que se esta editando y no sobre el macro
        leido: avisar de la lista vieja mientras se arma otra no sirve de nada.
        """
        texto = self.texto_de_pasos()
        if not texto:
            return ["sin pasos: un macro vacio se escribe, pero no hace nada"]
        try:
            eventos = est.eventos_desde_texto(texto)
        except ValueError as exc:
            return [str(exc)]
        try:
            est.armar_macro(self.macro_id() or est.MACRO_ID_MIN, eventos)
        except ValueError as exc:
            return [str(exc)]
        return list(modelo.advertencias_de(eventos))

    def _al_cambiar_pasos(self) -> None:
        avisos = self.avisos_de_los_pasos()
        m = self.macro()
        if m is not None and m.texto == self.texto_de_pasos():
            # Las del macro que esta en el mouse incluyen la del modo, que no
            # depende de los pasos: mientras no se toque nada, se muestran esas.
            avisos = list(m.advertencias) or avisos
        self.avisos.setText("\n".join(f"• {tr(a)}" for a in avisos))
        self.avisos.setVisible(bool(avisos))

    def _al_grabar(self) -> None:
        m = self.macro()
        texto = self.texto_de_pasos()
        if m is None or not texto or self._pasos_de != m.id:
            return
        self.pidio_escribir.emit("macro_eventos", texto, m.id)

    # --- estado de la pantalla -------------------------------------------

    def revertir(self) -> None:
        """Vuelve a mostrar el macro que el mouse tiene, no el que se armo."""
        self._refrescar(desde_el_mouse=True)

    def actualizar_textos(self) -> None:
        """Actualiza todas las etiquetas tras un cambio de idioma."""
        self.grupo_cual.setTitle(tr("Selección de macro"))
        self.lbl_macro.setText(tr("Macro:"))
        self.lbl_extra.setText(tr("Agregar un ID:"))
        self.pedir.setText(tr("Pedir este ID al leer"))
        self.lbl_nombre.setText(tr("Nombre:"))
        self.nombre.setPlaceholderText(tr("Nombre (guardado en este equipo, no en el mouse)"))
        self.guardar_nombre.setText(tr("Guardar nombre"))
        self.explica_macros.setText(tr(EXPLICA_MACROS))

        self.grupo_disparo.setTitle(tr("Disparo"))
        self.lbl_modo.setText(tr("Modo:"))
        for i in range(self.modo.count()):
            cod = self.modo.itemData(i)
            nom = est.MACRO_MODOS.get(cod, "")
            qh = modelo.QUE_HACE_EL_MODO.get(cod, "")
            self.modo.setItemText(i, f"{tr(nom)} — {tr(qh)}")
        self.lbl_repeticiones.setText(tr("Repeticiones:"))
        self.aplicar_rep.setText(tr("Aplicar"))
        self.nota_rep.setText(tr(NOTA_REPETICIONES))

        self.grupo_pasos.setTitle(tr("Pasos (hasta 50 eventos)"))
        self.prender.setText(tr("Detener grabador") if self.prender.isChecked()
                             else tr("Iniciar grabador"))
        self.limpiar.setText(tr("Limpiar"))
        self.grabar.setText(tr("Grabar en el mouse"))
        self.nota_pasos.setText(tr(NOTA_PASOS))
        self.grabador._decir()
        self._al_elegir_modo(self.modo.currentIndex(), escribir=False)
        m = self.macro()
        if m is not None:
            self.nombre.setPlaceholderText(tr(f"Macro {m.id} (sin nombre propio)"))
        self._al_cambiar_pasos()

    def bloquear(self, si: bool) -> None:
        for w in (self.modo, self.repeticiones, self.aplicar_rep, self.grabar,
                  self.pedir, self.guardar_nombre, self.prender):
            w.setEnabled(not si and self.macro() is not None)
        self.pedir.setEnabled(not si)
        if si and self.prender.isChecked():
            self.prender.setChecked(False)
