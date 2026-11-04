# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""La ventana: lo que se ve, y nada de lo que se decide.

Cablea seis señales de `Hardware` a seis lugares de la pantalla y manda dos
cosas para el otro lado -leer y escribir-. No arma bloques, no abre nodos y no
sabe que campos existen: eso ya esta resuelto abajo.

Tres decisiones que se ven poco y pesan:

  * **el consentimiento es el click.** No hay dialogo de "seguro?" antes de
    escribir: el que aprieta ya dijo que si, y un segundo prompt seria una
    tecla mas sobre una decision tomada. Lo que se conserva es el **registro**,
    que es la pestaña de abajo;
  * **mientras escribe, no se toca nada.** Una escritura son varios segundos de
    Etapa 3 y el mouse queda con el respaldo a medio tomar: aceptar otro cambio
    encima seria encolar corridas sobre un estado que esta cambiando;
  * **la bateria dice cuando dejo de llegar.** Con el mouse enchufado por cable
    a la PC no llega un solo latido (MEDIDO: 32 s de silencio),
    y el dongle sigue en el bus: sin la hora, la pantalla mostraria para
    siempre el ultimo porcentaje como si fuera de ahora.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QMenu,
                               QPlainTextEdit, QPushButton, QStatusBar,
                               QTabWidget, QVBoxLayout, QWidget)

from linshark import conexiones
from linshark import lugares
from linshark import modelo
from linshark import protocol as p
from linshark import sesion

from . import i18n
from .i18n import tr
from .controles import texto_de_valor
from .hardware import Hardware
from .paneles.macros import PanelDeMacros
from .paneles.parametros import PanelDeParametros

log = logging.getLogger("linshark_ui.ventana")

#: La carpeta del driver -`driver/` en el repo, `/opt/linshark` instalado-,
#: para poder ofrecer el script de udev por ruta absoluta: el comando de la
#: excepcion es relativo -se corre desde la raiz del repo- y un boton no tiene
#: por que heredar el directorio de trabajo de quien lanzo la ventana.
RAIZ = Path(__file__).resolve().parent.parent.parent

#: A los cuantos segundos sin novedades la bateria deja de ser "de ahora". El
#: latido va cada 2-4 s con el mouse suelto (MEDIDO), asi que quince es holgado
#: y no parpadea.
SILENCIO_SOSPECHOSO = 15


class CartelDeProblema(QFrame):
    """Un problema, y **el arreglo cuando lo hay**.

    La regla de udev es hoy el unico problema del proyecto que tiene un arreglo
    de una linea, y `FaltaLaReglaDeUdev` lo trae como dato (`.comando`) para
    que esto pueda ofrecerlo sin parsear el texto del error (G-05).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.setVisible(False)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(16, 12, 16, 12)
        caja.setSpacing(10)
        self.texto = QLabel()
        self.texto.setWordWrap(True)
        self.texto.setProperty("role", "peligro")
        self.texto.setTextInteractionFlags(Qt.TextSelectableByMouse)
        caja.addWidget(self.texto)

        fila = QHBoxLayout()
        fila.setSpacing(10)
        self.copiar = QPushButton(tr("Copiar comando"))
        self.copiar.clicked.connect(self._al_copiar)
        self.aplicar = QPushButton()
        self.aplicar.setProperty("role", "primario")
        self.aplicar.clicked.connect(self._al_aplicar)
        self.cerrar = QPushButton(tr("Cerrar"))
        self.cerrar.clicked.connect(lambda: self.setVisible(False))
        fila.addWidget(self.copiar)
        fila.addWidget(self.aplicar)
        fila.addStretch(1)
        fila.addWidget(self.cerrar)
        caja.addLayout(fila)

        self._comando = ""
        self._mensaje = ""
        self._proceso: QProcess | None = None

    def mostrar(self, mensaje: str, comando: str) -> None:
        """`mensaje` llega en castellano, como lo dice la biblioteca.

        Se guarda asi y se traduce al mostrarlo: guardado ya traducido, un
        cambio de idioma lo dejaria en el anterior.
        """
        self._comando = comando
        self._mensaje = mensaje
        self.texto.setText(tr(mensaje))
        self.copiar.setVisible(bool(comando))
        self.copiar.setToolTip(comando)
        script = self._script()
        self.aplicar.setVisible(bool(script) and bool(shutil.which("pkexec")))
        if script:
            # El boton dice **exactamente** lo que va a correr: el click es el
            # consentimiento, y pkexec ademas pide la clave mostrando el
            # comando. Un dialogo de "seguro?" en el medio no agregaria nada.
            self.aplicar.setText(f"{tr('Aplicar')}: pkexec {script}")
        self.setVisible(True)

    def _script(self) -> str:
        """La ruta absoluta del script del comando, si el comando es uno."""
        if not self._comando:
            return ""
        ruta = Path(self._comando.split()[-1])
        # El comando nombra `driver/scripts/...` y RAIZ ya es `driver/`: sin
        # sacarle ese primer tramo buscaba `driver/driver/scripts/...`, no lo
        # encontraba nunca, y el boton de aplicar no aparecia.
        if ruta.parts[:1] == ("driver",):
            ruta = Path(*ruta.parts[1:])
        candidato = RAIZ / ruta
        return str(candidato) if candidato.is_file() else ""

    def _al_copiar(self) -> None:
        QGuiApplication.clipboard().setText(self._comando)
        self.copiar.setText(tr("Copiado"))
        QTimer.singleShot(1500, self,
                          lambda: self.copiar.setText(tr("Copiar comando")))

    def _al_aplicar(self) -> None:                # pragma: no cover - pide clave
        script = self._script()
        if not script or self._proceso is not None:
            return
        self._proceso = QProcess(self)
        self._proceso.finished.connect(self._al_terminar)
        self.aplicar.setEnabled(False)
        self._proceso.start("pkexec", [script])

    def _al_terminar(self, codigo: int, _estado) -> None:   # pragma: no cover
        self.aplicar.setEnabled(True)
        self._proceso = None
        self.texto.setText(
            tr("La regla quedó instalada. Vuelve a conectar.") if codigo == 0 else
            f"{tr('El comando salió con código')} {codigo}. {tr('Córrelo a mano')}: "
            f"{self._comando}")

    def actualizar_textos(self) -> None:
        self.copiar.setText(tr("Copiar comando"))
        self.cerrar.setText(tr("Cerrar"))
        if self._mensaje:
            self.texto.setText(tr(self._mensaje))
        script = self._script()
        if script:
            self.aplicar.setText(f"{tr('Aplicar')}: pkexec {script}")


class CartelDeTasaPrestada(QFrame):
    """El mouse esta a 1000 Hz porque se lo pedimos prestado, y eso se dice.

    **Es la unica parte de esta aplicacion que cambia algo que el usuario no
    pidio.** Se hace porque arriba de 1000 Hz los bloques largos no llegan
    (MEDIDO a 2000 y a 8000) y sin ellos no hay respaldo, o sea no hay red; y
    se devuelve al terminar. Lo que no se puede hacer es **no decirlo**: un
    mouse que quedo a un octavo de su tasa sin que su dueño se entere es
    exactamente la clase de sorpresa que este proyecto le reprocha a los dos
    clientes oficiales.
    """

    pidio_devolver = Signal()
    #: "No me la devuelvas: me quedo a 1000." Lo pidio el usuario
    #: (2026-09-20): configurar a 1000 y quedarse ahi era imposible sin dejar
    #: que la sesion devolviera los 8000 y bajarlos de nuevo a mano, que
    #: reconfigura la radio dos veces para terminar donde ya se estaba.
    pidio_quedarse = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.setVisible(False)
        self._hz = 0
        fila = QHBoxLayout(self)
        fila.setContentsMargins(16, 12, 16, 12)
        fila.setSpacing(14)
        self.texto = QLabel()
        self.texto.setProperty("role", "aviso")
        self.texto.setWordWrap(True)
        self.devolver = QPushButton(tr("Devolver la tasa ahora"))
        self.devolver.setProperty("role", "primario")
        self.devolver.clicked.connect(self.pidio_devolver)
        # **El segundo camino, que antes no existia.** El cartel ofrecia una
        # sola salida -devolver los 8000- y quien queria quedarse en 1000 tenia
        # que dejar que se los devolvieran y bajarlos de nuevo con
        # `cambiar-rate.py`: dos reconfiguraciones de radio para terminar donde
        # ya estaba. No es primario a proposito: lo que la sesion promete es
        # devolverla, y eso tiene que seguir siendo lo que salta a la vista.
        self.quedarse = QPushButton(tr("Quedarme en {max_hz} Hz").format(
            max_hz=sesion.RATE_MAXIMO_PARA_LEER))
        self.quedarse.clicked.connect(self.pidio_quedarse)
        fila.addWidget(self.texto, 1)
        fila.addWidget(self.quedarse)
        fila.addWidget(self.devolver)

    def poner(self, hz: int) -> None:
        """`hz` es a cuanto hay que devolverla. Cero esconde el cartel."""
        self._hz = hz
        self.setVisible(bool(hz))
        if hz:
            # Arriba de 1000 Hz no se puede leer entero: MEDIDO a 2000 y a 8000.
            plantilla = tr(
                "El mouse está a {max_hz} Hz mientras lo configurás: a más "
                "velocidad no se puede leer entero. Vuelve solo a {hz} Hz al "
                "cerrar la ventana o después de un rato sin cambios.")
            self.texto.setText(plantilla.format(max_hz=sesion.RATE_MAXIMO_PARA_LEER, hz=hz))

    def actualizar_textos(self) -> None:
        self.devolver.setText(tr("Devolver la tasa ahora"))
        self.quedarse.setText(tr("Quedarme en {max_hz} Hz").format(
            max_hz=sesion.RATE_MAXIMO_PARA_LEER))
        if self._hz:
            self.poner(self._hz)


def _renglon_de_cambio(clave: str, de, a, campo) -> str:
    """`nombre: de  ->  a`, en el idioma de la pantalla si se sabe el campo."""
    if campo is None:
        return f"{clave}: {de}  ->  {a}"
    return (f"{tr(campo.nombre)}: {texto_de_valor(campo, de)}  ->  "
            f"{texto_de_valor(campo, a)}")


class DialogoDeRestauracion(QDialog):
    """Que campos van a cambiar, de que a que, antes de tocar el mouse.

    **No es un "seguro?".** El consentimiento ya lo dio el click, como en
    cualquier otro control de esta ventana. Lo que este dialogo agrega es
    informacion que el boton no puede llevar: un click aca son **varias**
    escrituras, cada una con su Etapa 3, y cuales son depende de como este el
    mouse en este momento. Un boton que dice "valores seguros" no alcanza para
    saber que va a mover el dpi del nivel 3 y el sentido de la rueda.

    Y cuando no hay nada que cambiar lo dice y no ofrece aplicar: escribir
    veintipico de campos con los valores que ya tienen seria gastar la Etapa 3
    -y el enlace de 2.4 GHz- para no mover nada.
    """

    def __init__(self, cambios, titulo: str, aclaracion: str, faltan=(),
                 parent=None, campos=None, via: str | None = None):
        """`titulo` y `aclaracion` llegan ya traducidos.

        `campos` es `modelo.por_clave(estado)`: con el, la lista dice el nombre
        de cada campo y sus valores como se ven en la pantalla, en vez de la
        clave interna. Sin el, dice la clave, que sigue siendo exacta.
        """
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(480)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(20, 18, 20, 18)
        caja.setSpacing(14)

        encabezado_txt = (
            f"{len(cambios)} {tr('campos van a cambiar:')}" if cambios
            else tr("No hay nada que cambiar: el mouse ya está así."))
        encabezado = QLabel(encabezado_txt)
        encabezado.setProperty("role", "titulo")
        encabezado.setWordWrap(True)
        caja.addWidget(encabezado)

        if aclaracion:
            nota = QLabel(aclaracion)
            nota.setProperty("role", "nota")
            nota.setWordWrap(True)
            caja.addWidget(nota)

        if faltan:
            incompleto = QLabel(
                tr("El mouse no contestó ") + ", ".join(faltan) + tr(": esos campos ") +
                tr("no figuran acá y <b>no se van a restaurar</b>. Lee de nuevo antes, o quedan como están."))
            incompleto.setProperty("role", "discrepancia")
            incompleto.setWordWrap(True)
            incompleto.setTextFormat(Qt.RichText)
            caja.addWidget(incompleto)

        if cambios:
            self.lista = QPlainTextEdit()
            self.lista.setReadOnly(True)
            self.lista.setPlainText("\n".join(
                _renglon_de_cambio(clave, de, a, (campos or {}).get(clave))
                for clave, de, a in cambios))
            self.lista.setMinimumHeight(140)
            caja.addWidget(self.lista, 1)

            # Cada una con su Etapa 3; quieto, el dongle pierde la mitad de
            # los pedidos (MEDIDO). Por cable no hay nada que mover.
            if via == conexiones.VIA_CABLE:
                aviso_txt = tr("Son {n} escrituras, una detrás de otra."
                               ).format(n=len(cambios))
            else:
                aviso_txt = tr(
                    "Son {n} escrituras, una detrás de otra. Mové el mouse "
                    "mientras tanto: así van más rápido.").format(
                        n=len(cambios))
            aviso = QLabel(aviso_txt)
            aviso.setProperty("role", "aviso")
            aviso.setWordWrap(True)
            caja.addWidget(aviso)

        fila = QHBoxLayout()
        fila.setSpacing(10)
        fila.addStretch(1)
        cancelar = QPushButton(tr("Cancelar") if cambios else tr("Cerrar"))
        cancelar.clicked.connect(self.reject)
        fila.addWidget(cancelar)
        if cambios:
            self.aplicar = QPushButton(tr("Escribir los {n}").format(n=len(cambios)))
            self.aplicar.setProperty("role", "primario")
            self.aplicar.clicked.connect(self.accept)
            fila.addWidget(self.aplicar)
        caja.addLayout(fila)


def _etiqueta_de_idioma() -> str:
    codigo = i18n.idioma_actual()
    return "🌐 " + {"zh": "中文"}.get(codigo, codigo.upper())


def _texto_de_via(via: str, puerto: str) -> str:
    """"Dongle 2.4 GHz · puerto 1-2", en el idioma de la pantalla.

    El puerto entra en el texto y no al lado porque es **una sola cosa**: por
    donde habla el mouse y donde esta enchufado eso. El nodo va aparte, en su
    propio chip, porque es un detalle de Linux -y cambia de numero solo-.
    """
    if not via:
        return ""
    donde = f" · {tr('puerto')} {puerto}" if puerto else ""
    return {
        conexiones.VIA_DONGLE: tr("Dongle 2.4 GHz"),
        conexiones.VIA_CABLE: tr("Cable USB"),
    }.get(via, tr("Conexión desconocida")) + donde


class BarraDeConexion(QFrame):
    """Arriba de todo: donde esta el mouse, que modelo es, como esta la pila."""

    pidio_leer = Signal()
    #: El diccionario de valores al que hay que volver. La barra no sabe cual
    #: es cual: los dos botones mandan lo suyo y la ventana hace el resto.
    #: `(valores, son_de_fabrica)`. El bool no es decoracion: decide que dice
    #: el dialogo, y comparar el diccionario por identidad para averiguarlo
    #: seria atar la ventana a que la barra mande ese objeto y no una copia.
    pidio_restaurar = Signal(object, bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        caja = QHBoxLayout(self)
        caja.setContentsMargins(18, 12, 18, 12)
        caja.setSpacing(16)

        self.modelo = QLabel(tr("Sin conectar"))
        self.modelo.setProperty("role", "titulo")
        #: **Por donde esta hablando el mouse, y en que puerto.** El nodo
        #: (`/dev/hidrawN`) no dice nada de eso y ademas cambia de numero cada
        #: vez que se enchufa algo; el puerto es lo que se mira para saber si
        #: el dongle se movio de lugar.
        self.via = QLabel()
        self.via.setProperty("role", "chip")
        self.via.setVisible(False)
        self.nodo = QLabel()
        self.nodo.setProperty("role", "chip")
        self.bateria = QLabel(tr("Batería: —"))
        self.leer = QPushButton(tr("Leer el mouse"))
        self.leer.setProperty("role", "primario")
        self.leer.clicked.connect(self.pidio_leer)

        #: **Los dos quedan apagados hasta que haya algo leido.** Restaurar es
        #: llevar el mouse de donde esta a donde se quiere, y sin haberlo leido
        #: no se sabe de donde sale: escribir los veintipico de campos a ciegas
        #: seria saltarse el paso 1 de la Etapa 3.
        self.como_estaba = QPushButton(tr("Volver a como estaba"))
        self.como_estaba.setEnabled(False)
        self.como_estaba.setToolTip(tr(
            "Vuelve a los valores que tenía el mouse cuando se abrió esta "
            "ventana. No toca los macros."))
        self.como_estaba.clicked.connect(
            lambda: self.pidio_restaurar.emit(self._de_al_abrir, False))

        self.seguros = QPushButton(tr("Valores seguros"))
        self.seguros.setEnabled(False)
        self.seguros.setToolTip(tr(
            "Los valores de fábrica, con la tasa en {tasa} Hz para que el "
            "mouse se pueda seguir leyendo entero. No toca los macros.").format(
                tasa=modelo.TASA_SEGURA))
        self.seguros.clicked.connect(
            lambda: self.pidio_restaurar.emit(modelo.SEGUROS, True))

        self.boton_idioma = QPushButton(_etiqueta_de_idioma())
        self.boton_idioma.setObjectName("boton_idioma")
        self.boton_idioma.setCursor(Qt.PointingHandCursor)
        self.boton_idioma.setToolTip(tr("Idioma / Language / 语言"))
        menu_idioma = QMenu(self.boton_idioma)
        menu_idioma.addAction("Español", lambda: self._elegir_idioma("es"))
        menu_idioma.addAction("English", lambda: self._elegir_idioma("en"))
        menu_idioma.addAction("简体中文", lambda: self._elegir_idioma("zh"))
        self.boton_idioma.setMenu(menu_idioma)

        caja.addWidget(self.modelo)
        caja.addWidget(self.via)
        caja.addWidget(self.nodo)
        caja.addStretch(1)
        caja.addWidget(self.bateria)
        caja.addWidget(self.como_estaba)
        caja.addWidget(self.seguros)
        caja.addWidget(self.leer)
        caja.addWidget(self.boton_idioma)

        #: Los valores de la **primera** lectura de esta sesion de la ventana.
        #: Se llena una sola vez: si se llenara en cada lectura, el boton
        #: volveria a "lo de recien" y no a "lo de al abrir", que es lo que
        #: dice que hace.
        self._de_al_abrir: dict = {}
        self._nodo_actual = ""
        self._via_actual = ("", "")
        self._device_id_actual: int | None = None
        self._nombre_actual: str | None = None

        self._ultima = None
        self._porcentaje = None
        self._cargando = None
        self._reloj = QTimer(self)
        self._reloj.timeout.connect(self._pintar_bateria)
        self._reloj.start(1000)

    def _elegir_idioma(self, codigo: str) -> None:
        i18n.fijar_idioma(codigo)

    def hay_algo_de_al_abrir(self) -> bool:
        """Si ya se leyo el mouse alguna vez en esta sesion de la ventana."""
        return bool(self._de_al_abrir)

    def anotar_lo_de_al_abrir(self, estado: dict) -> None:
        """Guarda los valores de la primera lectura, y habilita los botones.

        Solo los campos **escribibles**: los otros no se pueden restaurar y
        ofrecerlos seria prometer algo que la biblioteca va a rechazar. Los
        macros no entran porque `campos_de()` no los devuelve. La tasa es la
        de su dueño, no la prestada (`modelo.como_esta`).
        """
        valores = modelo.como_esta(estado)
        if valores and not self._de_al_abrir:
            self._de_al_abrir = valores
        self.como_estaba.setEnabled(bool(self._de_al_abrir))
        self.seguros.setEnabled(bool(valores))

    def poner_modelo(self, device_id: int, nombre: str) -> None:
        self._device_id_actual = device_id
        self._nombre_actual = nombre
        self.modelo.setText(nombre or f"{tr('modelo')} {device_id} ({tr('sin nombre')})")
        self.modelo.setProperty("role", "titulo" if nombre else "peligro")
        self.modelo.style().unpolish(self.modelo)
        self.modelo.style().polish(self.modelo)

    def poner_via(self, via: str, puerto: str = "") -> None:
        """El chip de "por donde y en que puerto".

        Guarda los **datos** y no el texto: el idioma se puede cambiar en
        cualquier momento, y un chip con el texto ya armado quedaria en el
        idioma anterior.
        """
        self._via_actual = (via, puerto)
        self.via.setText(_texto_de_via(via, puerto))
        self.via.setVisible(bool(via))

    def poner_nodo(self, nodo: str) -> None:
        # Una ruta pasa tal cual; lo que no es ruta -el "(device inyectado)"
        # de las pruebas- se traduce como cualquier texto.
        self._nodo_actual = nodo
        self.nodo.setText(tr(nodo))
        self.nodo.setVisible(bool(nodo))

    def poner_bateria(self, porcentaje: int, cargando) -> None:
        self._porcentaje = porcentaje
        self._cargando = cargando
        self._ultima = datetime.now()
        self._pintar_bateria()

    def _pintar_bateria(self) -> None:
        if self._porcentaje is None:
            self.bateria.setText(tr("Batería: —"))
            return
        # `cargando` es None para todo byte que no se midio, y eso se dice: el
        # `2` del bundle nunca aparecio y afirmar "a bateria" ahi seria
        # inventar. Ver `sesion.Novedad.cargando`.
        marca = {True: f" ({tr('cargando')})", False: ""}.get(
            self._cargando, f" ({tr('estado sin medir')})")
        callado = (datetime.now() - self._ultima).total_seconds()
        if callado > SILENCIO_SOSPECHOSO:
            self.bateria.setText(
                f"{tr('Batería:')} {self._porcentaje}%{marca}{tr(' — sin novedades hace ')}"
                f"{int(callado)}{tr(' s')}")
            # Con el cable a la PC el mouse no manda ni un latido y el dongle
            # sigue en el bus (MEDIDO): de ahi el "por ejemplo".
            self.bateria.setToolTip(tr(
                "El mouse avisa la batería cada pocos segundos. Hace un rato "
                "que no avisa —por ejemplo, si está conectado por cable—, así "
                "que este número puede estar desactualizado."))
            self.bateria.setProperty("role", "tenue")
        else:
            self.bateria.setText(f"{tr('Batería:')} {self._porcentaje}%{marca}")
            self.bateria.setToolTip("")
            self.bateria.setProperty("role", "")
        self.bateria.style().unpolish(self.bateria)
        self.bateria.style().polish(self.bateria)

    def actualizar_textos(self) -> None:
        self.poner_via(*self._via_actual)
        self.boton_idioma.setText(_etiqueta_de_idioma())
        self.boton_idioma.setToolTip(tr("Idioma / Language / 语言"))
        self.leer.setText(tr("Leer el mouse"))
        self.como_estaba.setText(tr("Volver a como estaba"))
        self.como_estaba.setToolTip(tr(
            "Vuelve a los valores que tenía el mouse cuando se abrió esta "
            "ventana. No toca los macros."))
        self.seguros.setText(tr("Valores seguros"))
        self.seguros.setToolTip(tr(
            "Los valores de fábrica, con la tasa en {tasa} Hz para que el "
            "mouse se pueda seguir leyendo entero. No toca los macros.").format(
                tasa=modelo.TASA_SEGURA))
        if self._nodo_actual:
            self.nodo.setText(tr(self._nodo_actual))
        if self._nombre_actual is not None:
            self.poner_modelo(self._device_id_actual or 0, self._nombre_actual)
        else:
            self.modelo.setText(tr("Sin conectar"))
        self._pintar_bateria()


def _diferencia(linea: str) -> str:
    """Una linea de `sesion.diferencias()`, con el comando traducido.

    Son datos de protocolo -`dpi.Current_Dpi_level_flag: 1 -> 2`, bloques en
    hex- y lo unico en castellano es el nombre del comando del principio. Los
    campos llevan el nombre del fabricante y se dejan como estan, igual que
    en `dev/models/attackshark-x8pro/docs/protocolo.md`.
    """
    hecho = i18n.tr_si_hay(linea)
    if hecho is not None:
        return hecho
    for nombre in sorted(p.CMD_NAMES.values(), key=len, reverse=True):
        for corte in (".", ": "):
            if linea.startswith(nombre + corte):
                return tr(nombre) + linea[len(nombre):]
    return linea


class Ventana(QMainWindow):
    """La ventana principal."""

    def __init__(self, hardware: Hardware, nombres=None, al_abrir=None,
                 parent=None) -> None:
        super().__init__(parent)
        self.hw = hardware
        #: Donde queda la primera lectura de esta apertura
        #: (`lugares.al_abrir()`). Sin ruta no se guarda nada: los tests no
        #: escriben en el HOME de nadie.
        self._ruta_al_abrir = Path(al_abrir) if al_abrir is not None else None
        self.setWindowTitle("LinShark")
        self.setMinimumSize(640, 520)
        self.resize(980, 800)
        #: Si llego un estado nuevo desde que empezo la escritura. Una que
        #: falla **antes** de la relectura no trae ninguno -respaldo
        #: incompleto, el mouse que no contesta, un valor que el codificador
        #: rechaza- y ahi la pantalla se queda mostrando lo que se pidio.
        self._hubo_estado = False
        #: El ultimo estado leido. Lo necesita `restaurar()` para saber de
        #: donde sale cada campo: sin eso no hay diff que mostrar ni forma de
        #: escribir solo lo que hace falta.
        self._estado: dict = {}

        cuerpo = QWidget()
        caja = QVBoxLayout(cuerpo)
        caja.setContentsMargins(18, 16, 18, 14)
        caja.setSpacing(14)

        self.conexion = BarraDeConexion()
        self.conexion.pidio_leer.connect(self.leer)
        self.conexion.pidio_restaurar.connect(self.restaurar)
        caja.addWidget(self.conexion)

        self.problema = CartelDeProblema()
        caja.addWidget(self.problema)

        self.tasa = CartelDeTasaPrestada()
        self.tasa.pidio_devolver.connect(self.devolver_tasa)
        self.tasa.pidio_quedarse.connect(self.quedarse_con_la_tasa)
        caja.addWidget(self.tasa)

        self.desactualizado = QFrame()
        self.desactualizado.setObjectName("panel")
        self.desactualizado.setVisible(False)
        fila = QHBoxLayout(self.desactualizado)
        fila.setContentsMargins(16, 12, 16, 12)
        fila.setSpacing(14)
        self.desactualizado_texto = QLabel()
        self.desactualizado_texto.setProperty("role", "aviso")
        self.desactualizado_texto.setWordWrap(True)
        self.releer = QPushButton(tr("Releer"))
        self.releer.clicked.connect(self.leer)
        fila.addWidget(self.desactualizado_texto, 1)
        fila.addWidget(self.releer)
        caja.addWidget(self.desactualizado)

        self.parametros = PanelDeParametros()
        self.parametros.pidio_escribir.connect(self.escribir)
        self.macros = PanelDeMacros(nombres)
        self.macros.pidio_escribir.connect(self.escribir_macro)
        self.macros.pidio_releer.connect(lambda _: self.leer())
        self.registro = QPlainTextEdit()
        self.registro.setReadOnly(True)

        self.pestañas = QTabWidget()
        self.pestañas.addTab(self.parametros, tr("Parámetros"))
        self.pestañas.addTab(self.macros, tr("Macros"))
        self.pestañas.addTab(self.registro, tr("Registro"))
        caja.addWidget(self.pestañas, 1)
        self.setCentralWidget(cuerpo)

        barra = QStatusBar()
        barra.setContentsMargins(16, 2, 16, 2)
        self.progreso = QLabel(tr("Listo"))
        self.progreso.setProperty("role", "tenue")
        barra.addWidget(self.progreso, 1)
        self.setStatusBar(barra)

        i18n.al_cambiar_idioma(self._al_cambiar_idioma)

        hardware.progreso.connect(self.al_progresar)
        hardware.problema.connect(self.al_haber_problema)
        hardware.estado.connect(self.al_llegar_estado)
        hardware.novedad.connect(self.al_haber_novedad)
        hardware.escritura_lista.connect(self.al_terminar_escritura)
        hardware.conectado.connect(self.al_conectar)
        hardware.modelo_detectado.connect(self.conexion.poner_modelo)
        # El bloqueo lo dice el hardware: es el unico que sabe cuando la
        # Etapa 3 arranco y cuando no queda ninguna corriendo.
        hardware.ocupado.connect(self._bloquear)
        hardware.tasa_prestada.connect(self.al_cambiar_la_tasa_prestada)
        hardware.tasa_elegida.connect(self.al_elegir_la_tasa)

        #: **La tasa prestada no se queda prestada para siempre.** Si nadie
        #: toca nada durante la gracia, se devuelve sola: es del usuario, no
        #: nuestra. Sin esto, abrir la ventana, leer el mouse y olvidarse lo
        #: dejaria a 1000 Hz hasta que alguien se diera cuenta.
        self._gracia = QTimer(self)
        self._gracia.setSingleShot(True)
        self._gracia.timeout.connect(self.devolver_tasa)

        hardware.desconectado.connect(self.al_desconectar)

        #: **Lo que hay en el bus, mirado cada tanto.** Enchufar el dongle en
        #: otro puerto, o sacarlo, o enchufar el mouse por cable, cambia lo que
        #: la ventana puede hacer, y antes no se enteraba: habia
        #: que cerrarla y abrirla. Mirar el bus son unas lecturas de sysfs, **no
        #: toca el mouse ni abre ningun nodo**, asi que se puede hacer seguido
        #: sin ensuciar ninguna medicion ni gastar el enlace.
        self._nodo_conectado = ""
        #: Por donde esta conectado, cuando se sabe. Lo usa el panel: hay
        #: campos que dependen del camino -la tasa maxima por cable- y no del
        #: modelo.
        self._via = ""
        self._firma_del_bus: tuple | None = None
        self._bus = QTimer(self)
        self._bus.timeout.connect(self.mirar_el_bus)
        self._bus.start(self.LATIDO_DEL_BUS)
        self.mirar_el_bus()

    #: Cada cuanto se mira el bus USB, en ms.
    LATIDO_DEL_BUS = 3000

    def mirar_el_bus(self) -> None:
        """Mira que hay enchufado y, si cambio, lo dice y reacciona.

        Tres cosas, en este orden: se pinta lo que hay -por donde y en que
        puerto-, se anota el cambio en el registro, y **recien despues** se
        decide si hay algo que hacer. Lo que se hace es lo minimo: abrir el
        nodo si aparecio un camino y no estabamos conectados, o reabrirlo si el
        que teniamos ya no esta en el bus (el dongle cambiado de puerto).
        """
        try:
            vistas = conexiones.buscar()
        except OSError as exc:                     # pragma: no cover
            log.warning("no pude mirar el bus: %s", exc)
            return
        firma = tuple((c.via, c.puerto, c.producto, c.se_puede_configurar)
                      for c in vistas)
        if firma == self._firma_del_bus:
            return
        primera = self._firma_del_bus is None
        self._firma_del_bus = firma

        usable = next((c for c in vistas if c.se_puede_configurar), None)
        por_cable = next((c for c in vistas
                          if c.via == conexiones.VIA_CABLE), None)
        mostrar = usable or por_cable or (vistas[0] if vistas else None)
        if mostrar is not None:
            self._via = mostrar.via
            self.conexion.poner_via(mostrar.via, mostrar.puerto)
        else:
            self._via = ""
            self.conexion.poner_via("")

        if not primera:
            self.anotar(self._linea_del_bus(vistas, usable, por_cable))

        # **El caso que importa cuando estan los dos**: con el cable puesto el
        # mouse deja de hablar por el dongle (MEDIDO, 32 s sin un
        # solo latido). Si el cable se puede abrir, `buscar()` lo pone primero
        # y es el que se usa; si no -sin permisos-, lo usable es el dongle, que
        # abre igual y no contesta nadie, y sin decirlo eso parece un problema
        # del programa.
        if (usable is not None and usable.via == conexiones.VIA_DONGLE
                and por_cable is not None):
            # **En castellano, sin traducir**: el cartel guarda el mensaje y lo
            # traduce al pintarlo, asi puede repintarse cuando se cambia de
            # idioma. Pasarselo ya traducido lo deja clavado en el idioma que
            # hubiera cuando aparecio.
            self.problema.mostrar(
                "el mouse está enchufado por el cable USB en el puerto "
                f"{por_cable.puerto}, y mientras esté así no habla por el "
                "dongle: no va a contestar. Sacá el cable —o cargalo de un "
                "cargador que no sea la PC— para poder configurarlo", "")

        if usable is not None:
            # **Solo un nodo de verdad se compara contra el bus.** Con un
            # device inyectado -las pruebas- el "nodo" no es una ruta y nunca
            # va a estar en el bus: tomarlo por un dongle que se movio cerraria
            # el device de la prueba y abriria el nodo real.
            nodo_real = self._nodo_conectado.startswith("/dev/")
            if nodo_real and self._nodo_conectado not in [
                    str(n.path) for c in vistas for n in c.nodos]:
                # El nodo que teniamos abierto ya no esta: el dongle se movio
                # de puerto y el descriptor viejo apunta a la nada.
                self.anotar(tr("el dongle cambió de lugar: vuelvo a abrirlo"))
                self._nodo_conectado = ""
                self.hw.reconectar()
            elif (nodo_real and usable.nodo_de_configuracion is not None
                  and self._nodo_conectado
                  != str(usable.nodo_de_configuracion.path)):
                # El nodo sigue en el bus pero ya no es el que contesta: se
                # enchufo el cable con el dongle abierto, o se lo saco. Se
                # cambia de camino sin cerrar la ventana.
                self.anotar(tr("el mouse cambió de camino: vuelvo a abrirlo"))
                self._nodo_conectado = ""
                self.hw.reconectar()
            elif not self._nodo_conectado and not primera:
                # Aparecio un camino y no habia ninguno abierto: se abre. La
                # primera pasada no lo hace, porque de eso se encarga quien
                # arranca la ventana.
                self.hw.abrir()

    def _linea_del_bus(self, vistas, usable, por_cable) -> str:
        """Que decir en el registro cuando el bus cambio."""
        if (usable is not None and usable.via == conexiones.VIA_DONGLE
                and por_cable is not None):
            return tr(f"el dongle está en el puerto {usable.puerto} y el mouse "
                      f"está por cable en el puerto {por_cable.puerto}: "
                      "mientras esté por cable no contesta por el dongle")
        if usable is not None and usable.via == conexiones.VIA_CABLE:
            return tr(f"el mouse está por cable en el puerto {usable.puerto}")
        if usable is not None:
            return tr(f"el dongle está en el puerto {usable.puerto}")
        if por_cable is not None:
            return tr(f"el mouse está por cable en el puerto "
                      f"{por_cable.puerto}, pero su nodo no se puede abrir")
        if vistas:
            return tr("hay un dispositivo de esta familia en el bus, pero no "
                      "el canal de configuración")
        return tr("no hay ningún mouse de esta familia en el bus USB")

    def al_desconectar(self, nodo: str) -> None:
        """El nodo se fue del bus: el canal lo vio antes que el vigilante."""
        self._nodo_conectado = ""
        self.conexion.poner_nodo("")
        self.conexion.poner_via("")
        self.anotar(tr("el mouse se fue del bus") + f" ({nodo})")

    def _al_cambiar_idioma(self, idioma: str) -> None:
        self.conexion.actualizar_textos()
        self.problema.actualizar_textos()
        self.tasa.actualizar_textos()
        self.releer.setText(tr("Releer"))
        self.pestañas.setTabText(0, tr("Parámetros"))
        self.pestañas.setTabText(1, tr("Macros"))
        self.pestañas.setTabText(2, tr("Registro"))
        self.parametros.actualizar_textos()
        self.macros.actualizar_textos()
        if self._estado:
            self.progreso.setText(self.diagnostico_de(self._estado))
        elif self.progreso.text() in ("Listo", "Ready", "就绪"):
            self.progreso.setText(tr("Listo"))
        if getattr(self, "_nivel_dpi_desactualizado", None) is not None and self.desactualizado.isVisible():
            self.desactualizado_texto.setText(tr(
                "El mouse cambió solo al nivel de DPI {nivel} "
                "(alguien apretó el botón). Lo que se ve es de antes."
            ).format(nivel=self._nivel_dpi_desactualizado))

    # --- lo que se le pide al mouse --------------------------------------

    def leer(self) -> None:
        self._posponer_la_devolucion()
        self._nivel_dpi_desactualizado = None
        self.desactualizado.setVisible(False)
        if not self._estado:
            self.parametros.leyendo(True, self._via)
        self.hw.leer_estado(macros_extra=self.macros.macros_extra())

    def escribir(self, clave: str, valor) -> None:
        # Se bloquea aca **y** con `ocupado`: el pedido viaja al otro hilo, y
        # entre el click y el `True` que vuelve hay lugar para un segundo
        # click. Desbloquear, en cambio, lo decide solo el hardware.
        self._posponer_la_devolucion()
        self._bloquear(True)
        self.anotar(tr(f"escribiendo {clave} = {valor!r}"))
        self.hw.escribir(clave, valor,
                         macros_extra=self.macros.macros_extra())

    def escribir_macro(self, clave: str, valor, macro_id: int) -> None:
        self._posponer_la_devolucion()
        self._bloquear(True)
        self.anotar(tr(f"escribiendo {clave} del macro {macro_id} = {valor!r}"))
        self.hw.escribir(clave, valor, macro_id=macro_id,
                         macros_extra=self.macros.macros_extra())

    def restaurar(self, deseado: dict, de_fabrica: bool) -> None:
        """Lleva el mouse a un juego de valores, campo por campo.

        **No hay un comando de "restaurar" en este protocolo**, y si lo hubiera
        no se usaria: el del cliente oficial sube la tasa a 8000 Hz, y eso
        una vez dejo el respaldo en 3 de 7. Lo que hace este boton son
        las escrituras que ya sabemos hacer, cada una con su Etapa 3 completa,
        y **solo las que hacen falta**: un campo que ya esta en su valor no se
        reescribe.

        Las encola `Hardware`, que tiene un candado y un contador: la pantalla
        queda bloqueada hasta que termine la ultima y la tasa se presta **una
        sola vez** para toda la rafaga.
        """
        if not self._estado:
            return
        cambios = modelo.pendientes(self._estado, deseado)
        dialogo = self.dialogo_de_restauracion(cambios, de_fabrica)
        if dialogo.exec() != QDialog.Accepted:
            return
        self.anotar(tr(f"restaurando {len(cambios)} campos"))
        # **Agrupados por comando, no uno por uno.** Los campos del mismo
        # bloque salen en una sola escritura, y eso no es solo ahorrar vueltas
        # de Etapa 3: si el bloque quedo con dos campos fuera de rango,
        # escribirlos de a uno arrastra siempre al otro y la baranda los
        # rechaza a los dos. Juntos, el bloque que sale ya esta en rango.
        self._posponer_la_devolucion()
        self._bloquear(True)
        self.hw.escribir_varios([(clave, a) for clave, _, a in cambios],
                                macros_extra=self.macros.macros_extra())

    def dialogo_de_restauracion(self, cambios, de_fabrica: bool):
        """El dialogo que `restaurar()` muestra, armado y sin abrir.

        Aparte para poder mirarlo sin un `exec()` que espera un click.
        """
        return DialogoDeRestauracion(
            cambios,
            tr("Valores seguros") if de_fabrica else tr("Volver a como estaba"),
            # El dpi de fabrica sale del "restaurar" del cliente oficial; ver
            # `modelo.DE_FABRICA`.
            (tr("Son los valores de fábrica, con la tasa en {tasa} Hz para "
                "que el mouse se pueda seguir leyendo entero. Los macros no se "
                "tocan.").format(tasa=modelo.TASA_SEGURA) if de_fabrica else
             tr("Son los valores que tenía el mouse cuando se abrió esta "
                "ventana. Los macros no se tocan.")),
            # **Lo que no se leyo se nombra, no se calla.** Un bloque que el
            # mouse no contesto no tiene campos, asi que no aparece en el diff
            # y quedaria restaurado "a medias" sin que nadie lo supiera.
            faltan=[tr(p.CMD_NAMES.get(c, str(c)))
                    for c in sesion.incompletos(self._estado)],
            parent=self, campos=modelo.por_clave(self._estado),
            via=self._estado.get("via") or self._via)

    def devolver_tasa(self) -> None:
        """Le devuelve al mouse la tasa que tenia. Se puede llamar de mas."""
        self._gracia.stop()
        self.hw.soltar_tasa()

    def quedarse_con_la_tasa(self) -> None:
        """Cancela la deuda: el mouse se queda en la tasa que tiene puesta.

        **No le escribe nada**: ya esta a esa tasa. Lo que se apaga es la
        promesa de devolverla —y el reloj de gracia que la devolvia sola—, asi
        que a partir de aca la tasa puesta es la que el usuario eligio.
        """
        self._gracia.stop()
        self.hw.quedarse_con_la_tasa()

    def al_elegir_la_tasa(self, debia: int) -> None:
        self.anotar(tr(f"el mouse se queda en "
                       f"{sesion.RATE_MAXIMO_PARA_LEER} Hz: ya no se le "
                       f"deben los {debia}"))

    def al_cambiar_la_tasa_prestada(self, hz: int) -> None:
        self.tasa.poner(hz)
        if hz:
            self.anotar(tr(f"la tasa quedo prestada: el mouse esta a "
                           f"{sesion.RATE_MAXIMO_PARA_LEER} Hz y vuelve a {hz}"))
            self._gracia.start(int(sesion.GRACIA_ANTES_DE_SOLTAR * 1000))
        else:
            self._gracia.stop()

    def _posponer_la_devolucion(self) -> None:
        """Mientras se este configurando, la tasa sigue prestada."""
        if self._gracia.isActive():
            self._gracia.start(int(sesion.GRACIA_ANTES_DE_SOLTAR * 1000))

    def _bloquear(self, si: bool) -> None:
        if si:
            self._hubo_estado = False
        elif not self._hubo_estado:
            # Termino sin traer estado: lo que se ve tiene que volver a ser lo
            # que el mouse dice. Si trajo estado, `al_llegar_estado` ya lo
            # pinto y revertir seria pisar lo bueno con lo viejo.
            self.parametros.revertir()
            self.macros.revertir()
        self.parametros.bloquear(si)
        self.macros.bloquear(si)
        self.conexion.leer.setEnabled(not si)
        # Los de restaurar tambien: encolan una rafaga entera y apretarlos con
        # otra corriendo encolaria dos tandas sobre un estado que esta
        # cambiando, que es lo mismo que la pantalla bloqueada viene a evitar.
        self.conexion.como_estaba.setEnabled(
            not si and self.conexion.hay_algo_de_al_abrir())
        self.conexion.seguros.setEnabled(not si and bool(self._estado))

    # --- lo que llega del mouse ------------------------------------------

    def al_progresar(self, linea: str) -> None:
        # `Hardware` habla en castellano, como la biblioteca: el idioma es
        # cosa de la pantalla, y se resuelve en la pantalla.
        self.progreso.setText(tr(linea))

    def al_conectar(self, nodo: str) -> None:
        self._nodo_conectado = nodo
        self.conexion.poner_nodo(nodo)
        self.anotar(tr(f"conectado a {nodo}"))
        # Al conectar se repinta el chip: el nodo solo no dice por donde esta
        # hablando el mouse ni donde esta enchufado.
        self._firma_del_bus = None
        self.mirar_el_bus()

    def al_llegar_estado(self, estado: dict) -> None:
        self._hubo_estado = True
        self._estado = estado
        # **El aviso de "lo que se ve es de antes" se va cuando lo que llega
        # ya trae el nivel nuevo**: por cable, el dpi se relee solo apenas
        # avisa el boton (`Hardware._releer_el_dpi`). Se compara el nivel, no
        # cualquier estado: uno que llegue de antes no lo tapa.
        nivel = getattr(self, "_nivel_dpi_desactualizado", None)
        if nivel is not None and sesion.nivel_dpi_de(estado) == nivel:
            self._nivel_dpi_desactualizado = None
            self.desactualizado.setVisible(False)
        primera = not self.conexion.hay_algo_de_al_abrir()
        self.conexion.anotar_lo_de_al_abrir(estado)
        if primera and self.conexion.hay_algo_de_al_abrir():
            self._guardar_lo_de_al_abrir(estado)
        self.parametros.poner_estado(estado, self._via)
        self.macros.poner_estado(estado)
        self.progreso.setText(self.diagnostico_de(estado))
        hz = sesion.tasa_de(estado)
        if (sesion.incompletos(estado) and hz is not None
                and hz > sesion.RATE_MAXIMO_PARA_LEER):
            # Necesita una decision, no solo un renglon: el que mira tiene que
            # bajar la tasa para poder leer el mouse entero.
            self.problema.mostrar(self.diagnostico_de(estado), "")

    def _guardar_lo_de_al_abrir(self, estado: dict) -> None:
        """Deja la primera lectura en la maquina, con el formato de un respaldo.

        Es lo mismo que "volver a como estaba" tiene en memoria, pero entero:
        sobrevive a cerrar la ventana y sirve para `respaldar.py --comparar` y
        `restaurar-bloque.py`. Se reemplaza en cada apertura. Que no se pueda
        escribir no es motivo para dejar de configurar el mouse: se dice en el
        log y se sigue.
        """
        if self._ruta_al_abrir is None:
            return
        # Con la tasa prestada, el bloque de rate dice 1000 y el estado ya
        # trae a cuanto estaba (`sesion.CLAVE_TASA_BAJADA`): se guarda tal cual.
        try:
            lugares.guardar_estado(estado, self._ruta_al_abrir)
        except OSError as exc:
            log.warning("no pude guardar la lectura de al abrir en %s: %s",
                        self._ruta_al_abrir, exc)
            return
        log.info("la lectura de al abrir quedo en %s", self._ruta_al_abrir)

    @staticmethod
    def diagnostico_de(estado: dict) -> str:
        """Por que la lectura salio como salio, con el consejo que aplica.

        **Las dos causas piden cosas distintas.** Con el mouse quieto el enlace
        pierde pedidos y la respuesta es moverlo; arriba de 1000 Hz los bloques
        largos no llegan nunca (MEDIDO a 2000 y a 8000) y moverlo no cambia
        nada. Decir lo segundo cuando pasa lo primero es mandar a alguien a
        hacer algo que no sirve, y este proyecto ya sabe lo que cuesta eso.
        """
        faltan = sesion.incompletos(estado)
        if not faltan:
            return tr("El mouse contestó entero")
        hz = sesion.tasa_de(estado)
        if hz is not None and hz > sesion.RATE_MAXIMO_PARA_LEER:
            # Los bloques largos no llegan arriba de 1000 Hz: MEDIDO a 2000 y
            # a 8000. Desde la terminal: driver/scripts/cambiar-rate.py --valor 1000.
            return tr(
                "El mouse está a {hz} Hz, y a más de {max_hz} Hz no se puede "
                "leer entero: faltan {n}. Poné la tasa en {max_hz} Hz para "
                "leerlo completo."
            ).format(hz=hz, max_hz=sesion.RATE_MAXIMO_PARA_LEER, n=len(faltan))
        if estado.get("via") == conexiones.VIA_CABLE:
            # Por cable no hay radio que pierda pedidos: moverlo no ayuda.
            return tr("El mouse no contestó {n} comando(s) por cable: volvé "
                      "a leer").format(n=len(faltan))
        return tr("El mouse no contestó {n} comando(s): movelo y volvé a "
                  "leer").format(n=len(faltan))

    def al_haber_novedad(self, novedad) -> None:
        if novedad.bateria is not None:
            self.conexion.poner_bateria(novedad.bateria, novedad.cargando)
        if novedad.nivel_dpi is not None:
            self._nivel_dpi_desactualizado = novedad.nivel_dpi
            # **No se toca la pantalla por dentro.** El nivel cambio en el
            # mouse, no lo cambiamos nosotros, y el resto del bloque de dpi
            # pudo cambiar tambien: la unica forma honesta de reflejarlo es
            # releer. Mientras tanto se avisa, en vez de mostrar un valor
            # viejo sin que nadie se entere.
            self.desactualizado_texto.setText(tr(
                "El mouse cambió solo al nivel de DPI {nivel} "
                "(alguien apretó el botón). Lo que se ve es de antes."
            ).format(nivel=novedad.nivel_dpi))
            self.desactualizado.setVisible(True)

    def al_haber_problema(self, mensaje: str, comando: str) -> None:
        if not self._estado:
            # La lectura no trajo nada: el cartel deja de pedir que se mueva.
            self.parametros.leyendo(False)
        self.problema.mostrar(mensaje, comando)
        self.anotar(tr(f"problema: {mensaje}"))

    def al_terminar_escritura(self, resultado) -> None:
        detalle = tr(resultado.explicacion)
        self.anotar(tr(("salio bien: " if resultado.ok else "NO salio: ")
                       + resultado.explicacion))
        if resultado.veredicto is not None:
            for d in resultado.veredicto.diferencias:
                self.anotar(f"    {_diferencia(d)}")
        if not resultado.aplicada:
            self.anotar(tr("    el dongle no acuso la trama"))
        self.progreso.setText(detalle)
        # Una escritura que termina empuja la gracia hacia adelante: una
        # lectura completa puede tardar mas que la gracia entera, y sin esto
        # el reloj se vencia en el medio y devolvia la tasa apenas soltaba el
        # candado, con el usuario todavia configurando.
        self._posponer_la_devolucion()
        # **Restaurar la pantalla no se hace aca.** Es tentador -el resultado
        # dice que fallo, justo aca esta el dato- y estuvo escrito asi un rato,
        # en paralelo con lo de `_bloquear()`. No alcanza: una escritura que
        # revienta ANTES de `sesion.aplicar()` -un id de macro que no es un
        # numero, por ejemplo- no emite `escritura_lista` nunca, asi que este
        # camino no corre y el control queda mostrando lo que no es. La que
        # corre siempre es `ocupado(False)`, que va en un `finally`.

    # --- el registro ------------------------------------------------------

    def anotar(self, linea: str) -> None:
        """Una linea al registro, **ya en el idioma de la pantalla**.

        No traduce: lo hace quien llama, que sabe que parte es texto y que
        parte es un dato -una trama, un valor escrito- que no se toca.
        """
        self.registro.appendPlainText(
            f"{datetime.now():%H:%M:%S}  {linea}")

    def lineas_del_registro(self) -> list[str]:
        return self.registro.toPlainText().splitlines()

    # --- cerrar -----------------------------------------------------------

    def closeEvent(self, evento) -> None:
        """Cerrar espera a lo que este en vuelo: cortar deja medio bloque.

        Lo hace `Hardware.cerrar()`, que si no llega a tiempo corta **y lo
        dice**. Aca solo se avisa que se esta esperando, para que la ventana
        que tarda un segundo en irse no parezca colgada.
        """
        i18n.desregistrar_listener(self._al_cambiar_idioma)
        self.progreso.setText(tr("Cerrando: esperando a lo que esté andando…"))
        self.hw.cerrar()
        super().closeEvent(evento)
