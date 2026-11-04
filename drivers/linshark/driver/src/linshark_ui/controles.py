# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""La fabrica de controles: un `Campo` entra, un widget sale.

**Ningun control se elige por el nombre del campo.** Se elige por lo que el
`Campo` trae: si tiene `opciones` de dos valores booleanos es un interruptor,
si tiene otras `opciones` es un desplegable -con buscador y grupos si ademas
trae `grupos`-, si tiene `minimo` y `maximo` es un deslizador con su numerito,
y si su valor **se ve** como un color es un selector de color. Lo mismo con la marca de la fila: se pinta cuando el campo trae un
`color` -el LED que el mouse le prende, que no es su valor- y queda vacia
cuando no, sin que nadie pregunte de que campo se trata.
El dia que el modelo devuelva un campo que hoy no existe, la ventana
lo dibuja igual y sin que nadie la toque; el dia que aparezca un
`if campo.clave == "lod"`, la ventana volvio a ser de un solo mouse.

Lo que esta capa dice de cada campo es **lo que necesita quien lo toca**:

  * `campo.escribible == False` -> el control va en gris, y la definicion dice
    por que;
  * `campo.definicion` -> que es y para que sirve, detras del `?` de la fila;
  * `campo.aviso` -> lo unico que hay que saber antes de tocarlo, cuando hay
    algo, en el color de las advertencias.

Lo medido -`campo.nota`, lo que muestra el cliente oficial, las fechas- sigue
en el modelo y en `dev/docs/`, y **no sale en la ventana**: decidido,
la ayuda de una fila explica el parametro, no la evidencia.

Y una decision sobre cuando se escribe: **nunca mientras se arrastra**. Una
escritura son varios segundos de Etapa 3 -respaldo completo, escritura,
relectura-, asi que un deslizador que escribiera por cada pixel dejaria cien
corridas encoladas. Se escribe al soltar, y solo si el valor cambio.
"""

from __future__ import annotations

import html
import re
import unicodedata

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox,
                               QDoubleSpinBox, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QSizePolicy, QSlider, QSpinBox,
                               QStackedWidget, QVBoxLayout, QWidget)

from linshark import sesion
from .i18n import tr

#: Lo que se considera un color: exactamente lo que `modelo.py` produce y lo
#: que `sesion._rgb_de()` acepta. La deteccion es por la forma del valor y no
#: por el nombre del campo, que es lo que la mantiene data-driven.
ES_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def parece_color(valor) -> bool:
    return isinstance(valor, str) and bool(ES_COLOR.match(valor))


def rico(texto: str) -> str:
    """Las notas de la biblioteca, con su enfasis puesto.

    Vienen escritas para leerse en una terminal -`**asi**` lo importante y
    `` `asi` `` un identificador-, y mostrar los asteriscos crudos en una
    ventana seria dejar a medias una marca que ya esta. **No se cambia ni una
    palabra**: solo se marca lo que el texto ya marcaba.
    """
    if not texto:
        return ""
    salida = html.escape(texto)
    salida = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", salida)
    salida = re.sub(r"`([^`]+)`", r"<code>\1</code>", salida)
    # Un renglon en blanco es un parrafo aparte. En texto enriquecido Qt junta
    # los saltos de linea en un espacio, y la ayuda partida en dos parrafos
    # -que es y para que sirve moverlo- se leia de corrido.
    return "<br><br>".join(salida.split("\n\n")).replace("\n", "<br>")


def texto_de_opcion(campo, opcion) -> str:
    """Como se lee una opcion en pantalla, con la unidad si la hay.

    Si el campo trae `etiquetas`, se usa la de la opcion: el valor sigue siendo
    el que entiende el despachador, y lo que se lee es lo que eligio el modelo.
    """
    if isinstance(opcion, bool):
        return tr("Sí") if opcion else tr("No")
    etiqueta = (campo.etiquetas or {}).get(opcion)
    txt = tr(etiqueta if etiqueta is not None else str(opcion))
    unidad = tr(campo.unidad) if campo.unidad else ""
    return f"{txt} {unidad}".strip() if unidad else txt


def texto_de_valor(campo, valor) -> str:
    """Como se lee un valor del campo, sea una de sus opciones o no.

    El valor actual de un boton puede llevar su parametro -"macro 17"- y no
    estar entre las opciones; para ese el modelo trae `etiqueta_de_valor`.
    """
    if valor == campo.valor and campo.etiqueta_de_valor:
        return tr(campo.etiqueta_de_valor)
    return texto_de_opcion(campo, valor)


def paso_de(campo) -> float:
    """De a cuanto se mueve el control.

    **Primero lo que el campo declara.** `Campo.paso` no es una preferencia de
    presentacion: es lo que el mouse puede guardar -el dpi de a 50 porque
    `Pu()` divide entero, el tiempo de respuesta de a 2 porque el byte viaja a
    la mitad-. Ofrecer un numero de los otros es hacerle pedir a quien mira
    algo que el codificador va a rechazar, o que el mouse va a redondear sin
    avisar: con paso 1, arrastrar el deslizador del dpi daba 1623 y el mouse
    guardaba 1600.

    Sin `paso`, se infiere del rango: si alguno de los extremos no es entero,
    ese resto es el paso. Con los dos enteros, 1.
    """
    if getattr(campo, "paso", None) is not None:
        return campo.paso
    restos = [abs(x - int(x)) for x in (campo.minimo, campo.maximo)
              if x is not None and float(x) != int(x)]
    return min(restos) if restos else 1


def paso_comodo(campo) -> float:
    """Cuanto mueve una flecha del teclado: un multiplo del paso real.

    Con el dpi -de 100 a 40000, de a 50- moverse de a 50 obliga a arrastrar
    ochocientas veces. Se redondea el rango a un multiplo del paso, asi que el
    numero que sale sigue siendo uno que el mouse puede guardar.
    """
    paso = paso_de(campo)
    if campo.minimo is None or campo.maximo is None:
        return paso
    rango = int(campo.maximo - campo.minimo)
    comodo = 10 ** max(0, len(str(rango)) - 3)
    return max(paso, round(comodo / paso) * paso)


def decimales_de(paso: float) -> int:
    return 0 if float(paso) == int(paso) else len(f"{paso}".split(".")[1])


class DesplegableSinRueda(QComboBox):
    """Un desplegable al que la rueda del mouse **no le cambia el valor**.

    El panel es una lista larga dentro de un `QScrollArea`, y un `QComboBox`
    se come la rueda que pasa por encima: bajar la pantalla con el dedo sobre
    un desplegable le cambiaba la opcion sin que nadie lo hubiera elegido, y
    en este panel cada opcion es **una escritura al mouse**. Pasar el scroll
    por arriba del boton derecho lo remapeaba a otra funcion.

    Es el unico lugar donde eso puede pasar en silencio. Los deslizadores y
    los numeritos siguen aceptando la rueda a proposito: ahi el valor se ve
    cambiar mientras gira -es un numero que sube- y, sobre todo, no se escribe
    hasta que se suelta o el control pierde el foco.

    `ignore()` y **no** `return` a secas: un evento que no se acepta Qt se lo
    pasa al padre, asi que la rueda sigue moviendo el panel, que es lo que
    quiso quien la giro.
    """

    def wheelEvent(self, evento) -> None:            # noqa: N802 - API de Qt
        evento.ignore()


class DesplegableConBuscador(DesplegableSinRueda):
    """Se ve como un desplegable, pero al abrirlo sale `SelectorAgrupado`.

    Muestra lo que el mouse tiene, igual que los otros desplegables, y la
    lista con sus datos sigue adentro -`findData()`, `currentData()`-: lo
    unico que cambia es **que se abre**. Con cincuenta y tantas opciones la
    lista de siempre no se recorre, y escribir es mas rapido que buscar.

    **Escribir encima abre el buscador con esa letra puesta**, y las flechas
    lo abren en vez de pasar a la opcion de al lado. En un `QComboBox` comun
    la flecha abajo elige la siguiente y dispara `activated`, que aca es una
    escritura al mouse: con el foco en el desplegable, una flecha cambiaba la
    funcion de un boton sin que nadie la hubiera elegido.
    """

    #: El texto con el que se abre el buscador: vacio, o la tecla que se
    #: apreto encima del desplegable.
    pidio_abrir = Signal(str)

    ABREN = frozenset({Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown,
                       Qt.Key_Home, Qt.Key_End, Qt.Key_Space, Qt.Key_Return,
                       Qt.Key_Enter, Qt.Key_F4})

    def showPopup(self) -> None:                     # noqa: N802 - API de Qt
        self.pidio_abrir.emit("")

    def keyPressEvent(self, evento) -> None:         # noqa: N802 - API de Qt
        atajo = evento.modifiers() & (Qt.ControlModifier | Qt.AltModifier
                                      | Qt.MetaModifier)
        if not atajo and evento.key() in self.ABREN:
            evento.accept()
            self.pidio_abrir.emit("")
            return
        texto = evento.text()
        if not atajo and texto and texto.isprintable():
            evento.accept()
            self.pidio_abrir.emit(texto)
            return
        super().keyPressEvent(evento)


def sin_acentos(texto: str) -> str:
    """Como se compara lo que se busca: sin mayusculas y sin tildes.

    Quien escribe "musica" busca "Música", y "canción" tiene que encontrar
    lo mismo que "cancion". Con `NFKD` los signos anchos del chino -el `：`
    de "浏览器：刷新页面"- quedan como los comunes, que es lo que se teclea.
    """
    descompuesto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in descompuesto
                   if not unicodedata.combining(c)).casefold()


def ubicar_debajo(popup: QWidget, widget: QWidget) -> None:  # pragma: no cover
    """Pone un popup debajo de `widget`, sin salirse de la pantalla."""
    origen = widget.mapToGlobal(QPoint(0, widget.height() + 4))
    pantalla = widget.screen()
    if pantalla is not None:
        libre = pantalla.availableGeometry()
        popup.adjustSize()
        x = min(origen.x(), libre.right() - popup.width() - 8)
        y = origen.y()
        if y + popup.height() > libre.bottom():
            y = max(libre.top(),
                    origen.y() - popup.height() - widget.height() - 8)
        origen = QPoint(max(libre.left() + 8, x), y)
    popup.move(origen)
    popup.show()


# --- los editores ----------------------------------------------------------
#
# Cada uno declara **con que campos sirve** mirando solo propiedades, y
# `editor_para()` toma el primero que diga que si. El orden es el de
# `EDITORES`, y es la unica lista que hay que tocar para agregar una forma de
# control nueva.

class Editor(QWidget):
    """Lo que edita un valor. No sabe escribir: avisa que se pidio algo."""

    #: El valor nuevo, en la forma que `sesion.preparar_mutacion()` acepta.
    pidio = Signal(object)

    def __init__(self, campo, parent=None) -> None:
        super().__init__(parent)
        self.campo = campo
        caja = QHBoxLayout(self)
        caja.setContentsMargins(0, 0, 0, 0)
        caja.setSpacing(10)
        self.caja = caja
        self._armar()
        self.poner_campo(campo)

    @classmethod
    def sirve_para(cls, campo) -> bool:       # pragma: no cover - base
        return False

    def _armar(self) -> None:                 # pragma: no cover - base
        raise NotImplementedError

    def poner_campo(self, campo) -> None:
        """Refresca con un `Campo` nuevo **sin** disparar una escritura."""
        self.campo = campo
        self._mostrar(campo.valor)
        self.setEnabled(campo.escribible)

    def _mostrar(self, valor) -> None:        # pragma: no cover - base
        raise NotImplementedError

    def bloquear(self, si: bool) -> None:
        self.setEnabled(self.campo.escribible and not si)


class EditorBooleano(Editor):
    """Dos opciones y las dos son booleanas: un interruptor."""

    @classmethod
    def sirve_para(cls, campo) -> bool:
        return set(campo.opciones) == {False, True}

    def _armar(self) -> None:
        self.casilla = QCheckBox()
        self.casilla.toggled.connect(self._al_tocar)
        self.caja.addWidget(self.casilla)
        self.caja.addStretch(1)

    def _mostrar(self, valor) -> None:
        self.casilla.blockSignals(True)
        self.casilla.setChecked(bool(valor))
        self.casilla.setText(tr("Sí") if valor else tr("No"))
        self.casilla.blockSignals(False)

    def _al_tocar(self, marcado: bool) -> None:
        self.casilla.setText(tr("Sí") if marcado else tr("No"))
        if bool(self.campo.valor) != marcado:
            self.pidio.emit(marcado)

    def actualizar_textos(self) -> None:
        self.casilla.setText(tr("Sí") if self.casilla.isChecked() else tr("No"))


class EditorDeOpciones(Editor):
    """Una lista cerrada de valores: un desplegable.

    **Y el campito del parametro**, para las dos funciones de boton que llevan
    un dato adentro -el id del macro, la combinacion del atajo-. Cual de las
    opciones lo necesita no lo decide este modulo: lo contesta la biblioteca
    con `sesion.FaltaElParametro`, que trae que falta y un ejemplo. Asi el
    desplegable de botones funciona sin saber que existe un codigo 18.
    """

    @classmethod
    def sirve_para(cls, campo) -> bool:
        return bool(campo.opciones)

    def _crear_lista(self) -> QComboBox:
        return DesplegableSinRueda()

    def _armar(self) -> None:
        self.lista = self._crear_lista()
        # Sin esto el desplegable toma el foco al pasarle la rueda por encima
        # (`WheelFocus` es el default), y despues las flechas del teclado le
        # cambian el valor a un control que nadie eligio.
        self.lista.setFocusPolicy(Qt.StrongFocus)
        self.lista.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.lista.activated.connect(self._al_elegir)
        self.caja.addWidget(self.lista, 1)

        self.parametro = QLineEdit()
        self.parametro.setPlaceholderText("")
        self.parametro.setVisible(False)
        self.parametro.returnPressed.connect(self._al_poner_parametro)
        self.caja.addWidget(self.parametro)

        self.poner = QPushButton(tr("Aplicar"))
        self.poner.setVisible(False)
        self.poner.clicked.connect(self._al_poner_parametro)
        self.caja.addWidget(self.poner)

    def _mostrar(self, valor) -> None:
        self.lista.blockSignals(True)
        self.lista.clear()
        # **El valor que tiene el mouse puede no estar entre las opciones.**
        # Un boton en "macro 17" o en "atajo de teclado ctrl+c" lleva su
        # parametro pegado al nombre. Se muestra igual -esconderlo seria
        # mostrar "macro" para un boton que apunta a un macro que no existe-
        # pero no se puede reescribir tal cual, asi que va sin dato.
        if valor is not None and valor not in self.campo.opciones:
            self.lista.addItem(
                f"{texto_de_valor(self.campo, valor)}   ({tr('valor actual')})",
                None)
        for opcion in self.campo.opciones:
            self.lista.addItem(texto_de_opcion(self.campo, opcion), opcion)
        indice = self.lista.findData(valor)
        self.lista.setCurrentIndex(indice if indice >= 0 else 0)
        self.lista.blockSignals(False)
        self._esconder_parametro()

    def actualizar_textos(self) -> None:
        """Cambia los textos **sin rearmar la lista**.

        Rearmarla con el dato de la opcion elegida perdia el "valor actual": ese
        renglon no lleva dato, asi que un boton en "macro 17" pasaba a mostrar
        la primera opcion de la lista, que no es lo que el mouse tiene.
        """
        self.poner.setText(tr("Aplicar"))
        for i in range(self.lista.count()):
            opcion = self.lista.itemData(i)
            self.lista.setItemText(
                i, f"{texto_de_valor(self.campo, self.campo.valor)}   "
                   f"({tr('valor actual')})"
                if opcion is None else texto_de_opcion(self.campo, opcion))

    def _esconder_parametro(self) -> None:
        self._pendiente = None
        self.parametro.setVisible(False)
        self.parametro.clear()
        self.poner.setVisible(False)

    def elegir(self, opcion) -> None:
        """Elige una opcion por valor. Es lo que hace un click, sin mouse."""
        indice = self.lista.findData(opcion)
        if indice < 0:
            raise ValueError(f"{opcion!r} no esta entre las opciones de "
                             f"{self.campo.clave}")
        self.lista.setCurrentIndex(indice)
        self._al_elegir(indice)

    def _al_elegir(self, indice: int) -> None:
        opcion = self.lista.itemData(indice)
        if opcion is None:               # el "valor actual" que no se reescribe
            return
        if opcion == self.campo.valor:
            self._esconder_parametro()
            return
        try:
            sesion.preparar_mutacion(self.campo.clave, opcion)
        except sesion.FaltaElParametro as exc:
            # No se escribe todavia: falta un dato que solo puede dar quien
            # esta mirando. El campito aparece al lado y el Enter lo manda.
            self._pendiente = opcion
            self.parametro.setPlaceholderText(
                tr(f"{exc.que} (ej: {exc.ejemplo})"))
            self.parametro.setToolTip(tr(str(exc)))
            self.parametro.setVisible(True)
            self.parametro.setFocus()
            self.poner.setVisible(True)
            return
        except Exception:                # noqa: BLE001
            # Cualquier otro problema lo dice quien escribe, con el mensaje de
            # la biblioteca: aca solo se decide si hace falta pedir un dato.
            pass
        self._esconder_parametro()
        self.pidio.emit(opcion)

    def _al_poner_parametro(self) -> None:
        texto = self.parametro.text().strip()
        if self._pendiente is None or not texto:
            return
        opcion, self._pendiente = self._pendiente, None
        self._esconder_parametro()
        self.pidio.emit((opcion, texto))

    def bloquear(self, si: bool) -> None:
        super().bloquear(si)
        if si:
            self._esconder_parametro()


#: Lo que dicen el buscador y el desplegable que lo abre.
BUSCAR = "Escribí para buscar…"
NADA_COINCIDE = "Nada coincide con lo que escribiste."
PISTA_DEL_BUSCADOR = "Hacé clic o empezá a escribir para buscar"


class SelectorAgrupado(QFrame):
    """Las opciones de un campo con `grupos`: buscador arriba, grupos al
    costado y las opciones del grupo elegido al lado.

    **Los grupos van al costado y no como pestañas de arriba**: son nueve, y
    en una fila de pestañas no entran sin flechas para correrlas, que
    esconden justo lo que se vino a buscar. Al costado se ven todos juntos.

    **Escribir busca en todos los grupos a la vez**, sin tildes ni mayusculas
    y por palabras sueltas: "vol sub" encuentra "Subir el volumen". Se busca
    en lo que se lee en el idioma de la ventana, en el castellano, en el
    nombre que usa el CLI y, si con eso no aparece nada, en el nombre del
    grupo: "musica" trae el grupo de la musica aunque ninguna opcion diga
    "musica". Los resultados salen debajo del nombre de su grupo, y el Enter
    elige el primero.

    No escribe nada: avisa que opcion se eligio y el editor la manda por el
    mismo camino que un click en el desplegable, con su campito de parametro
    cuando la funcion lo necesita.
    """

    eligio = Signal(object)

    ANCHO = 640
    ALTO = 440

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.Popup)
        self.setObjectName("panel")
        self.setFixedSize(self.ANCHO, self.ALTO)
        self.campo = None
        self._ya_eligio = False
        #: El widget que lo abrio: un click ahi cierra el selector y no lo
        #: vuelve a abrir (ver `mousePressEvent`).
        self._abridor: QWidget | None = None

        caja = QVBoxLayout(self)
        caja.setContentsMargins(14, 14, 14, 14)
        caja.setSpacing(10)

        self.buscador = QLineEdit()
        self.buscador.setClearButtonEnabled(True)
        self.buscador.textChanged.connect(self._filtrar)
        self.buscador.installEventFilter(self)
        caja.addWidget(self.buscador)

        self.pila = QStackedWidget()
        caja.addWidget(self.pila, 1)

        # Pagina 0: los grupos y lo que hay en el elegido.
        navegar = QWidget()
        fila = QHBoxLayout(navegar)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(10)
        self.categorias = QListWidget()
        self.categorias.setObjectName("categorias")
        self.categorias.setFixedWidth(200)
        self.categorias.currentRowChanged.connect(self._mostrar_categoria)
        self.categorias.installEventFilter(self)
        fila.addWidget(self.categorias)
        self.opciones = QListWidget()
        self.opciones.setObjectName("opciones")
        self.opciones.installEventFilter(self)
        fila.addWidget(self.opciones, 1)
        self.pila.addWidget(navegar)

        # Pagina 1: lo que coincide con lo escrito, de todos los grupos.
        buscar = QWidget()
        columna = QVBoxLayout(buscar)
        columna.setContentsMargins(0, 0, 0, 0)
        self.resultados = QListWidget()
        self.resultados.setObjectName("opciones")
        self.resultados.installEventFilter(self)
        columna.addWidget(self.resultados, 1)
        self.sin_resultados = QLabel()
        # Con nombre, para que el QSS le de la misma caja que a la lista que
        # reemplaza: sin eso quedaba un hueco del color de la ventana.
        self.sin_resultados.setObjectName("sin_resultados")
        self.sin_resultados.setProperty("role", "tenue")
        self.sin_resultados.setAlignment(Qt.AlignCenter)
        self.sin_resultados.setWordWrap(True)
        columna.addWidget(self.sin_resultados, 1)
        self.pila.addWidget(buscar)

        for lista in (self.opciones, self.resultados):
            # **Las dos señales**, y `_ya_eligio` para que una sola cuente: en
            # un escritorio con "un click abre" -KDE, por ejemplo- el click
            # dispara tambien `itemActivated`, y el Enter solo dispara esa.
            lista.itemClicked.connect(self._al_tocar)
            lista.itemActivated.connect(self._al_tocar)

    # --- lo que se muestra ----------------------------------------------

    def poner(self, campo, texto: str = "") -> None:
        """Rearma el selector para ese campo, con `texto` ya escrito."""
        self.campo = campo
        self._ya_eligio = False
        self.buscador.setPlaceholderText(tr(BUSCAR))
        self.sin_resultados.setText(tr(NADA_COINCIDE))
        self.categorias.blockSignals(True)
        self.categorias.clear()
        for titulo, _ in campo.grupos:
            self.categorias.addItem(tr(titulo))
        self.categorias.blockSignals(False)
        # Se abre en el grupo de lo que el boton tiene ahora, con esa opcion
        # marcada: es lo primero que se quiere ver antes de cambiarla.
        actual = self._opcion_actual()
        fila = next((i for i, (_, opciones) in enumerate(campo.grupos)
                     if actual in opciones), 0)
        self.categorias.setCurrentRow(fila)
        self._mostrar_categoria(fila)
        self.buscador.blockSignals(True)
        self.buscador.setText(texto)
        self.buscador.blockSignals(False)
        self._filtrar(texto)
        self.buscador.setFocus(Qt.PopupFocusReason)

    def _opcion_actual(self):
        """La opcion que el campo tiene ahora, aunque traiga su parametro.

        Un boton en "macro 17" no esta entre las opciones, pero es la opcion
        "macro" con su id: se toma la mas larga de la que el valor sea
        la opcion seguida de algo. Sin eso, un boton con un macro abria el
        selector en el primer grupo.
        """
        valor = self.campo.valor
        if valor in self.campo.opciones:
            return valor
        texto = str(valor)
        candidatas = [o for o in self.campo.opciones
                      if isinstance(o, str) and texto.startswith(o + " ")]
        return max(candidatas, key=len, default=None)

    def _item(self, opcion) -> QListWidgetItem:
        item = QListWidgetItem(texto_de_opcion(self.campo, opcion))
        item.setData(Qt.UserRole, opcion)
        return item

    def _mostrar_categoria(self, fila: int) -> None:
        self.opciones.clear()
        if self.campo is None or not 0 <= fila < len(self.campo.grupos):
            return
        actual = self._opcion_actual()
        for opcion in self.campo.grupos[fila][1]:
            item = self._item(opcion)
            self.opciones.addItem(item)
            if opcion == actual:
                self.opciones.setCurrentItem(item)
                self.opciones.scrollToItem(item)

    def _pajar(self, opcion, titulo: str = "") -> str:
        """Lo que se puede escribir para encontrar esa opcion."""
        etiqueta = (self.campo.etiquetas or {}).get(opcion)
        partes = (texto_de_opcion(self.campo, opcion), etiqueta or "",
                  str(opcion), tr(titulo) if titulo else "", titulo)
        return sin_acentos(" ".join(partes))

    def _coincidencias(self, palabras) -> list:
        """`[(titulo, [opcion, ...]), ...]` con lo que coincide.

        **El nombre del grupo cuenta solo si ninguna opcion coincide por si
        misma.** Con el grupo siempre en la busqueda, "vol" traia el grupo de
        la musica entero -el titulo dice "volumen"- en vez de las dos
        opciones que suben y bajan el volumen. Asi "vol" trae esas dos, y
        "musica", que no lo dice ninguna opcion, trae el grupo.
        """
        for con_titulo in (False, True):
            salida = []
            for titulo, opciones in self.campo.grupos:
                pajar = titulo if con_titulo else ""
                del_grupo = [o for o in opciones
                             if all(p in self._pajar(o, pajar)
                                    for p in palabras)]
                if del_grupo:
                    salida.append((titulo, del_grupo))
            if salida:
                return salida
        return []

    def _filtrar(self, texto: str) -> None:
        palabras = sin_acentos(texto).split()
        if not palabras or self.campo is None:
            self.pila.setCurrentIndex(0)
            return
        self.resultados.clear()
        encontradas = 0
        for titulo, del_grupo in self._coincidencias(palabras):
            # El nombre del grupo, como un renglon que no se elige: el
            # teclado lo saltea y un click encima no hace nada.
            cabeza = QListWidgetItem(tr(titulo))
            cabeza.setFlags(Qt.NoItemFlags)
            letra = cabeza.font()
            letra.setBold(True)
            cabeza.setFont(letra)
            self.resultados.addItem(cabeza)
            for opcion in del_grupo:
                self.resultados.addItem(self._item(opcion))
                encontradas += 1
        self.resultados.setVisible(encontradas > 0)
        self.sin_resultados.setVisible(encontradas == 0)
        primera = self._primera(self.resultados)
        if primera is not None:
            self.resultados.setCurrentItem(primera)
        self.pila.setCurrentIndex(1)

    @staticmethod
    def _primera(lista: QListWidget):
        for i in range(lista.count()):
            if lista.item(i).flags() & Qt.ItemIsEnabled:
                return lista.item(i)
        return None

    def _lista_activa(self) -> QListWidget:
        return self.resultados if self.pila.currentIndex() == 1 else self.opciones

    # --- elegir ---------------------------------------------------------

    def _al_tocar(self, item) -> None:
        if (item is None or self._ya_eligio
                or not item.flags() & Qt.ItemIsEnabled):
            return
        self._ya_eligio = True
        opcion = item.data(Qt.UserRole)
        self.hide()
        self.eligio.emit(opcion)

    def buscar(self, texto: str) -> None:
        """Escribe en el buscador, como lo haria una persona."""
        self.buscador.setText(texto)

    def encontradas(self) -> list:
        """Las opciones que muestra la busqueda, en orden. Lo usan las pruebas."""
        if self.pila.currentIndex() != 1:
            return []
        return [self.resultados.item(i).data(Qt.UserRole)
                for i in range(self.resultados.count())
                if self.resultados.item(i).flags() & Qt.ItemIsEnabled]

    def elegir_con_enter(self) -> None:
        """Lo que hace el Enter en el buscador: la marcada, o la primera."""
        lista = self._lista_activa()
        item = lista.currentItem() or self._primera(lista)
        self._al_tocar(item)

    # --- el teclado -----------------------------------------------------

    def eventFilter(self, objeto, evento) -> bool:   # noqa: N802 - API de Qt
        if evento.type() != QEvent.KeyPress:
            return super().eventFilter(objeto, evento)
        tecla = evento.key()
        if objeto is self.buscador:
            if tecla in (Qt.Key_Return, Qt.Key_Enter):
                self.elegir_con_enter()
                return True
            if tecla in (Qt.Key_Down, Qt.Key_PageDown):
                lista = self._lista_activa()
                lista.setFocus(Qt.TabFocusReason)
                if lista.currentItem() is None:
                    primera = self._primera(lista)
                    if primera is not None:
                        lista.setCurrentItem(primera)
                return True
            return False
        # En las listas, las letras siguen escribiendo en el buscador: quien
        # empezo a escribir no tiene que volver a clickearlo.
        texto = evento.text()
        atajo = evento.modifiers() & (Qt.ControlModifier | Qt.AltModifier
                                      | Qt.MetaModifier)
        if (not atajo and texto and texto.isprintable() and texto != " "
                or tecla == Qt.Key_Backspace):
            self.buscador.setFocus(Qt.OtherFocusReason)
            if tecla == Qt.Key_Backspace:
                self.buscador.backspace()
            else:
                self.buscador.insert(texto)
            return True
        if objeto is self.categorias and tecla in (Qt.Key_Right, Qt.Key_Return,
                                                   Qt.Key_Enter):
            self.opciones.setFocus(Qt.TabFocusReason)
            if self.opciones.currentItem() is None and self.opciones.count():
                self.opciones.setCurrentRow(0)
            return True
        if objeto is self.opciones and tecla == Qt.Key_Left:
            self.categorias.setFocus(Qt.BacktabFocusReason)
            return True
        return super().eventFilter(objeto, evento)

    # --- abrir y cerrar -------------------------------------------------

    def abrir_debajo_de(self, widget: QWidget) -> None:  # pragma: no cover
        self._abridor = widget
        ubicar_debajo(self, widget)
        self.buscador.setFocus(Qt.PopupFocusReason)

    def mousePressEvent(self, evento) -> None:       # noqa: N802 - API de Qt
        """Un click en el desplegable que lo abrio lo cierra, y nada mas.

        Un popup recibe tambien los clicks de afuera, y Qt los **reenvia** al
        widget de abajo al cerrarse: sobre el desplegable, ese reenvio lo
        volvia a abrir, y no habia forma de cerrarlo con el mismo click que lo
        abrio. Es lo que hace el popup del `QComboBox` de Qt.
        """
        abridor = self._abridor
        sobre_el = (abridor is not None and abridor.rect().contains(
            abridor.mapFromGlobal(evento.globalPosition().toPoint())))
        self.setAttribute(Qt.WA_NoMouseReplay, sobre_el)
        super().mousePressEvent(evento)


class EditorDeOpcionesAgrupadas(EditorDeOpciones):
    """Un desplegable con demasiadas opciones para recorrerlas de a una.

    Sirve para los campos que traen `grupos` -hoy, las funciones de los
    botones-, y se ve igual que cualquier desplegable: el valor que el mouse
    tiene, en una caja. **Al abrirlo sale `SelectorAgrupado`**, y empezar a
    escribir con el foco encima lo abre con lo escrito puesto.

    Todo lo demas es de `EditorDeOpciones`: el "valor actual" que no se
    reescribe, el campito del parametro para el macro y el atajo, `elegir()`.
    """

    _selector: SelectorAgrupado | None = None

    @classmethod
    def sirve_para(cls, campo) -> bool:
        return bool(campo.opciones) and bool(getattr(campo, "grupos", ()))

    def _crear_lista(self) -> QComboBox:
        lista = DesplegableConBuscador()
        lista.setToolTip(tr(PISTA_DEL_BUSCADOR))
        lista.pidio_abrir.connect(self.abrir_selector)
        return lista

    def abrir_selector(self, texto: str = "") -> SelectorAgrupado:
        """Abre el selector debajo del desplegable, con `texto` escrito."""
        if self._selector is None:
            self._selector = SelectorAgrupado(self)
            self._selector.eligio.connect(self.elegir)
        self._selector.poner(self.campo, texto)
        self._selector.abrir_debajo_de(self.lista)
        return self._selector

    def selector(self) -> SelectorAgrupado | None:
        """El selector, si alguna vez se abrio. Lo usan las pruebas."""
        return self._selector

    def poner_campo(self, campo) -> None:
        super().poner_campo(campo)
        # Llego un estado nuevo con el selector abierto: que muestre el valor
        # nuevo y no el de cuando se abrio.
        if self._selector is not None and self._selector.isVisible():
            self._selector.poner(campo, self._selector.buscador.text())

    def actualizar_textos(self) -> None:
        super().actualizar_textos()
        self.lista.setToolTip(tr(PISTA_DEL_BUSCADOR))
        if self._selector is not None and self._selector.isVisible():
            self._selector.poner(self.campo, self._selector.buscador.text())

    def bloquear(self, si: bool) -> None:
        super().bloquear(si)
        # Empezo una escritura: nada que elegir hasta que termine.
        if si and self._selector is not None:
            self._selector.hide()


class EditorNumerico(Editor):
    """Un rango: deslizador y numerito, sincronizados.

    Se escribe al **soltar** el deslizador o al terminar de editar el numero, y
    solo si quedo distinto de lo que el mouse tiene. Arrastrar no escribe.
    """

    @classmethod
    def sirve_para(cls, campo) -> bool:
        return campo.minimo is not None and campo.maximo is not None

    def _armar(self) -> None:
        paso = paso_de(self.campo)
        self._paso = paso
        decimales = decimales_de(paso)
        self.numero = (QSpinBox() if decimales == 0 else QDoubleSpinBox())
        if decimales:
            self.numero.setDecimals(decimales)
        self.numero.setRange(self.campo.minimo, self.campo.maximo)
        self.numero.setSingleStep(paso_comodo(self.campo))
        # Sin esto el numerito acepta 1623 escrito a mano y el deslizador lo
        # muestra en 1600: dos controles de la misma fila diciendo cosas
        # distintas. `QAbstractSpinBox` alinea a `minimum + n*singleStep`, asi
        # que el paso chico va aca y el comodo -el de las flechas- arriba.
        self.numero.setStepType(QSpinBox.DefaultStepType)
        if self.campo.unidad:
            self.numero.setSuffix(f" {tr(self.campo.unidad)}")
        self.numero.setKeyboardTracking(False)
        self.numero.setMinimumWidth(95)

        self.deslizador = QSlider(Qt.Horizontal)
        self.deslizador.setRange(int(round(self.campo.minimo / paso)),
                                 int(round(self.campo.maximo / paso)))
        self.deslizador.setPageStep(
            max(1, int((self.deslizador.maximum()
                        - self.deslizador.minimum()) / 20)))

        self.deslizador.valueChanged.connect(self._al_deslizar)
        self.deslizador.sliderReleased.connect(self._al_soltar)
        self.numero.editingFinished.connect(self._al_soltar)

        self.caja.addWidget(self.deslizador, 1)
        self.caja.addWidget(self.numero)

    def _mostrar(self, valor) -> None:
        for w in (self.numero, self.deslizador):
            w.blockSignals(True)
        if valor is not None:
            self.numero.setValue(valor)
            self.deslizador.setValue(int(round(valor / self._paso)))
        for w in (self.numero, self.deslizador):
            w.blockSignals(False)

    def _al_deslizar(self, pasos: int) -> None:
        self.numero.blockSignals(True)
        self.numero.setValue(pasos * self._paso)
        self.numero.blockSignals(False)

    def valor(self):
        return self.numero.value()

    def poner_valor(self, valor) -> None:
        """Pone el numero como lo pondria una persona, y escribe si cambio."""
        self.numero.setValue(valor)
        self._al_soltar()

    def _al_soltar(self) -> None:
        valor = self.numero.value()
        self.deslizador.blockSignals(True)
        self.deslizador.setValue(int(round(valor / self._paso)))
        self.deslizador.blockSignals(False)
        if self.campo.valor is None or float(valor) != float(self.campo.valor):
            self.pidio.emit(valor)

    def actualizar_textos(self) -> None:
        if self.campo.unidad:
            self.numero.setSuffix(f" {tr(self.campo.unidad)}")


class EditorDeColor(Editor):
    """El valor se ve como `#rrggbb`: un boton con la muestra."""

    @classmethod
    def sirve_para(cls, campo) -> bool:
        return parece_color(campo.valor)

    def _armar(self) -> None:
        self.muestra = QFrame()
        self.muestra.setFixedSize(22, 22)
        self.muestra.setFrameShape(QFrame.StyledPanel)
        self.boton = QPushButton()
        self.boton.clicked.connect(self._al_pedir_color)
        self.caja.addWidget(self.muestra)
        self.caja.addWidget(self.boton)
        self.caja.addStretch(1)

    def _mostrar(self, valor) -> None:
        self.boton.setText(str(valor))
        self.muestra.setStyleSheet(
            f"background: {valor}; border: 1px solid #353b47; "
            "border-radius: 6px;")

    def _al_pedir_color(self) -> None:       # pragma: no cover - dialogo modal
        inicial = QColor(str(self.campo.valor))
        elegido = QColorDialog.getColor(inicial, self,
                                        tr(f"color de {self.campo.nombre}"))
        if elegido.isValid():
            self.elegir(elegido.name())

    def elegir(self, hexa: str) -> None:
        """Pone un color. Es lo que hace el dialogo, sin el dialogo."""
        hexa = str(hexa).lower()
        if not parece_color(hexa):
            raise ValueError(f"{hexa!r} no es un color `#rrggbb`")
        self._mostrar(hexa)
        if hexa != str(self.campo.valor).lower():
            self.pidio.emit(hexa)


class EditorDeTexto(Editor):
    """Lo que no entra en ninguno de los otros: se muestra y no se toca."""

    @classmethod
    def sirve_para(cls, campo) -> bool:
        return True

    def _armar(self) -> None:
        self.texto = QLabel()
        self.texto.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.caja.addWidget(self.texto)
        self.caja.addStretch(1)

    def _mostrar(self, valor) -> None:
        unidad = f" {tr(self.campo.unidad)}" if self.campo.unidad else ""
        self.texto.setText(f"{valor}{unidad}")

    def actualizar_textos(self) -> None:
        self._mostrar(self.campo.valor)


#: El orden importa: se toma el primero que sirva. Booleano antes que
#: desplegable -dos opciones booleanas son un interruptor, no una lista-, el
#: agrupado antes que el comun -un campo con `grupos` tiene tambien
#: `opciones`-, y texto al final, que sirve para todo.
EDITORES = (EditorBooleano, EditorDeOpcionesAgrupadas, EditorDeOpciones,
            EditorNumerico, EditorDeColor, EditorDeTexto)


def editor_para(campo, parent=None) -> Editor:
    """El control que le corresponde a ese campo, por sus propiedades."""
    for clase in EDITORES:
        if clase.sirve_para(campo):
            return clase(campo, parent)
    raise AssertionError("EditorDeTexto sirve para todo")   # pragma: no cover


# --- lo que hay que decir de un campo, y donde ------------------------------

def ayuda_de(campo) -> list[tuple[str, str]]:
    """Lo que sale detras del `?` de un campo: que es, y el aviso si lo hay.

    Devuelve pares `(role, texto)`, donde `role` es la propiedad de Qt que le
    da el color: `"nota"` la definicion, `"aviso"` lo que hay que saber antes
    de tocarlo.

    **Es una funcion y no un widget** para poder probar que se dice sin abrir
    una ventana, y porque quien la llama decide donde ponerlo.

    Antes esto juntaba todo lo medido del campo -la nota con su
    fecha, el color del LED, por que no se escribe y lo que mostraria el
    cliente oficial-. Era el registro del proyecto puesto en pantalla, y a
    quien mueve un deslizador no le dice que hace el deslizador. Ahora dice
    eso; lo medido sigue en `Campo.nota` y en `dev/models/attackshark-x8pro/docs/evidencia.md`.
    """
    partes: list[tuple[str, str]] = []
    if campo.definicion:
        partes.append(("nota", campo.definicion))
    if campo.aviso:
        partes.append(("aviso", campo.aviso))
    return partes


class PopupDeAyuda(QFrame):
    """Lo que dice `ayuda_de()`, al lado del boton que lo pidio.

    Va con `Qt.Popup`: se cierra solo al clickear afuera o con Escape, no tapa
    la ventana y no hay que acordarse de cerrarlo. No es un dialogo modal
    porque no pregunta nada -es para leer mientras se mira el control-.
    """

    ANCHO = 440

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.Popup)
        self.setObjectName("panel")
        self.setFixedWidth(self.ANCHO)
        self._caja = QVBoxLayout(self)
        self._caja.setContentsMargins(18, 16, 18, 16)
        self._caja.setSpacing(12)
        self.titulo = QLabel()
        self.titulo.setProperty("role", "titulo")
        self.titulo.setWordWrap(True)
        self._caja.addWidget(self.titulo)
        self._textos: list[QLabel] = []

    def poner(self, campo) -> None:
        """Rearma el contenido para ese campo."""
        self.poner_textos(campo.nombre, ayuda_de(campo))

    def poner_textos(self, titulo: str, partes) -> None:
        """Lo mismo, para lo que no es un campo.

        El esquema de botones tambien tiene cosas medidas que decir -de donde
        sale que cada numero es ese boton- y no es ningun `Campo`. Los `role`
        son los mismos: `"nota"`, `"aviso"`, `"discrepancia"`.
        """
        self.titulo.setText(tr(titulo))
        for viejo in self._textos:
            self._caja.removeWidget(viejo)
            viejo.deleteLater()
        self._textos = []
        for role, texto in partes:
            etiqueta = QLabel(rico(tr(texto)))
            etiqueta.setProperty("role", role)
            etiqueta.setWordWrap(True)
            etiqueta.setTextFormat(Qt.RichText)
            etiqueta.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self._caja.addWidget(etiqueta)
            self._textos.append(etiqueta)

    def textos(self) -> list[str]:
        """Lo que quedo escrito. Lo usan las pruebas."""
        return [x.text() for x in self._textos]

    def abrir_junto_a(self, widget) -> None:      # pragma: no cover - posicion
        """Se abre debajo del boton, y sin salirse de la pantalla."""
        ubicar_debajo(self, widget)


# --- la fila entera: nombre, control, y el boton que explica ----------------

class FilaDeCampo(QFrame):
    """Un campo con su marca, su nombre, su control y su `?`.

    **`QFrame` y no `QWidget`**: un `QWidget` pelado no pinta el fondo que le
    pone una hoja de estilos -hay que dibujarlo a mano en `paintEvent`- y la
    fila necesita poder pintarse cuando el esquema de botones manda mirarla.

    **La marca identifica la fila como la identifica el mouse**: el color del
    LED para un nivel de dpi, el numero del boton para un boton -el mismo que
    el esquema dibuja encima del mouse-. Lo que hace el campo va detras del `?`
    y en el tooltip de la fila, no en un parrafo debajo del control.
    """

    pidio_escribir = Signal(str, object)

    #: El ancho de la columna de los nombres. Entra el mas largo que tiene hoy
    #: el modelo ("tiempo de respuesta de los botones") sin partirse.
    ANCHO_DEL_NOMBRE = 250

    def __init__(self, campo, parent=None) -> None:
        super().__init__(parent)
        self.campo = campo
        # El QSS lo usa para poder pintar **una** fila cuando el esquema de
        # botones manda mirarla, sin alcanzar a todos los `QWidget`.
        self.setObjectName("fila")
        self.setProperty("destacada", "false")
        caja = QHBoxLayout(self)
        caja.setContentsMargins(8, 6, 8, 6)
        caja.setSpacing(14)

        #: El lugar de la marca, con ancho fijo. **Ocupa lugar siempre**,
        #: tambien vacio: sin el, el nombre de esa fila se correria a la
        #: izquierda y las filas del grupo dejarian de alinear entre si.
        self.insignia = QWidget()
        self.insignia.setFixedSize(22, 22)
        dentro = QHBoxLayout(self.insignia)
        dentro.setContentsMargins(0, 0, 0, 0)
        dentro.setSpacing(0)
        #: El color con el que el mouse identifica al campo, cuando le pone
        #: alguno (`Campo.color`).
        self.marca = QFrame()
        self.marca.setFixedSize(14, 14)
        dentro.addWidget(self.marca, 0, Qt.AlignCenter)
        #: El numero del boton (`Campo.slot`), en el mismo circulo que el
        #: esquema pone sobre el mouse: el que ve un 4 arriba encuentra un 4 aca.
        self.numero = QLabel()
        self.numero.setObjectName("numero_de_boton")
        self.numero.setFixedSize(22, 22)
        self.numero.setAlignment(Qt.AlignCenter)
        dentro.addWidget(self.numero, 0, Qt.AlignCenter)
        caja.addWidget(self.insignia)

        self.nombre = QLabel(tr(campo.nombre))
        # **Ancho fijo, no preferido.** Con el ancho natural cada control
        # arrancaba donde terminaba su nombre, asi que los interruptores de un
        # mismo grupo quedaban escalonados. Con `setWordWrap` un nombre que no
        # entre se parte en dos renglones en vez de recortarse: lo segundo
        # dejaria a medias el nombre de un campo, que es justo lo que este
        # proyecto se propuso traducir bien.
        self.nombre.setFixedWidth(self.ANCHO_DEL_NOMBRE)
        self.nombre.setWordWrap(True)
        caja.addWidget(self.nombre)

        self.editor = editor_para(campo, self)
        self.editor.pidio.connect(
            lambda valor: self.pidio_escribir.emit(self.campo.clave, valor))
        caja.addWidget(self.editor, 1)

        #: El `?`. **Conserva el lugar cuando no hay nada que decir**, para que
        #: los controles de un grupo terminen todos a la misma altura.
        self.ayuda = QPushButton("?")
        self.ayuda.setProperty("role", "ayuda")
        self.ayuda.setFixedSize(22, 22)
        self.ayuda.setFlat(True)
        politica = self.ayuda.sizePolicy()
        politica.setRetainSizeWhenHidden(True)
        self.ayuda.setSizePolicy(politica)
        self.ayuda.clicked.connect(self.mostrar_ayuda)
        caja.addWidget(self.ayuda)

        self._popup: PopupDeAyuda | None = None
        self.poner_campo(campo)

    def poner_campo(self, campo) -> None:
        """Refresca la fila: el control, la marca y lo que dice el `?`."""
        self.campo = campo
        self.nombre.setText(tr(campo.nombre))
        self.editor.poner_campo(campo)
        self._pintar_marca(campo.color)
        self.numero.setText("" if campo.slot is None else str(campo.slot))
        self.numero.setVisible(campo.slot is not None)
        self.marca.setVisible(campo.slot is None)

        partes = ayuda_de(campo)
        self.ayuda.setVisible(bool(partes))
        self.ayuda.setToolTip(tr("Qué es y para qué sirve"))
        self.setToolTip("\n\n".join(tr(texto) for _, texto in partes))
        if self._popup is not None and self._popup.isVisible():
            self._popup.poner(campo)

    def actualizar_textos(self) -> None:
        """Actualiza las etiquetas y tooltips tras un cambio de idioma."""
        self.nombre.setText(tr(self.campo.nombre))
        self.ayuda.setToolTip(tr("Qué es y para qué sirve"))
        self._pintar_marca(self.campo.color)
        partes = ayuda_de(self.campo)
        self.setToolTip("\n\n".join(tr(texto) for _, texto in partes))
        if hasattr(self.editor, "actualizar_textos"):
            self.editor.actualizar_textos()
        if self._popup is not None and self._popup.isVisible():
            self._popup.poner(self.campo)

    def mostrar_ayuda(self) -> None:
        """Abre el popup con lo que `ayuda_de()` tenga para este campo."""
        partes = ayuda_de(self.campo)
        if not partes:
            return
        if self._popup is None:
            self._popup = PopupDeAyuda(self)
        self._popup.poner(self.campo)
        self._popup.abrir_junto_a(self.ayuda)

    def popup(self) -> "PopupDeAyuda | None":
        """El popup, si alguna vez se abrio. Lo usan las pruebas."""
        return self._popup

    def _pintar_marca(self, color) -> None:
        """El puntito del color que el mouse le pone al campo, o nada.

        Sin color queda transparente y sin borde: se sigue viendo el hueco,
        que es lo que mantiene los nombres alineados, pero no dibuja una
        pastilla gris al lado de cada fila.
        """
        hexa = color.hexa if color is not None else None
        if hexa and parece_color(hexa):
            self.marca.setStyleSheet(
                f"background: {hexa}; border: 1px solid #353b47; "
                "border-radius: 7px;")
            # El nombre del color, que antes iba en la ayuda: aca es de quien
            # es, en la marca que lo muestra.
            self.marca.setToolTip(f"{tr(color.nombre)} ({hexa})"
                                  if color.nombre else hexa)
        else:
            self.marca.setStyleSheet("background: transparent; border: none;")
            self.marca.setToolTip("")

    #: Cuanto dura el resaltado, en milisegundos. Lo suficiente para
    #: encontrar la fila con la vista, no tanto como para quedar pintada.
    DURA_DESTACADA = 1600

    def destacar(self) -> None:
        """Se hace notar: alguien la esta buscando desde otro lado.

        Lo pide el esquema de botones cuando se toca un numero. El foco va al
        control **y ademas** se pinta la fila: el foco solo es demasiado
        discreto en una lista de treinta, y el color solo no existe con
        `--sin-tema`, donde la hoja de estilos no esta puesta. Con los dos,
        algo se ve siempre.
        """
        self.editor.setFocus(Qt.OtherFocusReason)
        self._pintar_destacada(True)
        QTimer.singleShot(self.DURA_DESTACADA, self,
                          lambda: self._pintar_destacada(False))

    def _pintar_destacada(self, si: bool) -> None:
        try:
            self.setProperty("destacada", "true" if si else "false")
            # Una propiedad dinamica no repinta sola: el selector de QSS ya se
            # resolvio cuando el widget se creo.
            self.style().unpolish(self)
            self.style().polish(self)
        except RuntimeError:
            pass

    def revertir(self) -> None:
        """Vuelve a mostrar lo que dice el modelo.

        Hace falta cuando una escritura **falla sin releer** -respaldo
        incompleto, el mouse que no contesta, un valor que el codificador
        rechaza-: ahi no llega un estado nuevo y el control se queda mostrando
        lo que se intento poner, que no es lo que el mouse tiene. Un
        desplegable que muestra "macro 20" para un boton que sigue en
        "adelante" es la misma mentira que este proyecto le reprocha a la
        pagina oficial, solo que nuestra.
        """
        self.poner_campo(self.campo)

    def bloquear(self, si: bool) -> None:
        self.editor.bloquear(si)


class FilaDeAccion(QFrame):
    """Una `modelo.Accion`: nombre, el boton que la hace, y su `?`.

    Tiene la misma forma que `FilaDeCampo` -el lugar de la marca, el nombre de
    ancho fijo, el control y el `?`- para que en su grupo alinee con las filas
    de al lado. No sabe que hace: al apretar pide escribir `accion.clave` con
    `accion.valor`, y la ventana lo manda por el mismo camino que un campo.
    """

    pidio_escribir = Signal(str, object)

    def __init__(self, accion, parent=None) -> None:
        super().__init__(parent)
        self.accion = accion
        self.setObjectName("fila")
        self.setProperty("destacada", "false")
        caja = QHBoxLayout(self)
        caja.setContentsMargins(8, 6, 8, 6)
        caja.setSpacing(14)
        hueco = QWidget()
        hueco.setFixedSize(22, 22)
        caja.addWidget(hueco)
        self.nombre = QLabel()
        self.nombre.setFixedWidth(FilaDeCampo.ANCHO_DEL_NOMBRE)
        self.nombre.setWordWrap(True)
        caja.addWidget(self.nombre)
        self.boton = QPushButton()
        self.boton.clicked.connect(
            lambda: self.pidio_escribir.emit(self.accion.clave,
                                             self.accion.valor))
        caja.addWidget(self.boton)
        caja.addStretch(1)
        self.ayuda = QPushButton("?")
        self.ayuda.setProperty("role", "ayuda")
        self.ayuda.setFixedSize(22, 22)
        self.ayuda.setFlat(True)
        self.ayuda.clicked.connect(self.mostrar_ayuda)
        caja.addWidget(self.ayuda)
        self._popup: PopupDeAyuda | None = None
        self.actualizar_textos()

    def actualizar_textos(self) -> None:
        self.nombre.setText(tr(self.accion.nombre))
        self.boton.setText(tr(self.accion.boton))
        self.ayuda.setToolTip(tr("Qué es y para qué sirve"))
        self.ayuda.setVisible(bool(self.accion.definicion))
        self.setToolTip(tr(self.accion.definicion))
        if self._popup is not None and self._popup.isVisible():
            self.mostrar_ayuda()

    def mostrar_ayuda(self) -> None:
        if self._popup is None:
            self._popup = PopupDeAyuda(self)
        self._popup.poner_textos(self.accion.nombre,
                                 [("nota", self.accion.definicion)])
        self._popup.abrir_junto_a(self.ayuda)

    def popup(self) -> "PopupDeAyuda | None":
        return self._popup

    def bloquear(self, si: bool) -> None:
        self.boton.setEnabled(not si)
