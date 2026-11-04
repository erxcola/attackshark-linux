# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""El panel de parametros, que se dibuja solo.

Recorre `modelo.campos_de(estado)` y pone una fila por campo. **No conoce
ningun campo**: los agrupa por el comando del que salieron -que es informacion
del protocolo, no del modelo de este mouse- y el control lo elige
`controles.editor_para()` mirando las propiedades del `Campo`.

Eso es lo que hace que el panel no haya que tocarlo cuando el modelo cambie: si
manana `campos_de()` devuelve un campo nuevo, aparece; si deja de devolver uno,
desaparece. Y si el mouse contesto a medias, se dibuja lo que contesto —una
pantalla con seis campos es mas util que una vacia—.

Y una fila es **una** fila: marca, nombre, control y el `?`. Que es cada campo
y para que sirve esta detras de ese boton (`controles.ayuda_de()`). Antes lo
medido iba debajo de cada control, y con treinta campos la pantalla eran mas
advertencias que controles; la ventana no muestra lo medido, sino la
definicion.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QGroupBox, QHBoxLayout, QLabel, QScrollArea,
                               QVBoxLayout, QWidget)

from linshark import conexiones
from linshark import modelo
from linshark import protocol as p

from ..controles import FilaDeAccion, FilaDeCampo
from ..diagrama import DiagramaDeBotones
from ..i18n import tr

#: Como se llama en pantalla cada bloque del mouse. Va por **comando**, no por
#: campo: son los siete que el mouse contesta, no los veintitantos
#: parametros.
#: El que no figure sale con el nombre del protocolo, que es peor pero no
#: miente.
#: Lo que dice el panel antes de la primera lectura, y mientras se hace.
TODAVIA_NO = "Todavía no se leyó el mouse."
#: Mientras lee. Por el dongle se pide moverlo -quieto, la radio pierde la
#: mitad de los pedidos (MEDIDO)- sin explicar la radio: alcanza con decir
#: para que sirve. Por cable no hay nada que mover, asi que no se pide.
LEYENDO = "Leyendo el mouse…\nMovelo mientras tanto: así lee más rápido."
LEYENDO_POR_CABLE = "Leyendo el mouse…"

TITULOS = {
    p.CMD_DPI: "Sensor y DPI",
    p.CMD_LIGHTING: "Luz, reposo y respuesta",
    p.CMD_REPORT_RATE: "Tasa de reporte",
    p.CMD_BUTTONS: "Botones y rueda",
    p.CMD_MACRO: "Macros",
}


class PanelDeParametros(QScrollArea):
    """Todos los campos del mouse, agrupados y en vivo."""

    #: `(clave, valor)`, listo para `hardware.escribir()`.
    pidio_escribir = Signal(str, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self._filas: dict[str, FilaDeCampo] = {}
        #: Las filas de `modelo.acciones_de()`: botones que hacen algo y no son
        #: un campo, como intercambiar el clic izquierdo y el derecho.
        self._acciones: dict[str, FilaDeAccion] = {}
        self._grupos: dict[int, QGroupBox] = {}
        self._cajas: dict[int, QVBoxLayout] = {}
        #: El esquema del mouse. Se arma la primera vez que llegan botones y
        #: se mete **arriba del grupo al que pertenecen**, no en un lugar
        #: elegido a mano: si manana los botones salen de otro comando, el
        #: esquema los sigue.
        self._diagrama: DiagramaDeBotones | None = None

        self._cuerpo = QWidget()
        layout_exterior = QHBoxLayout(self._cuerpo)
        layout_exterior.setContentsMargins(20, 16, 20, 20)
        layout_exterior.setAlignment(Qt.AlignHCenter)

        self._contenedor = QWidget()
        self._contenedor.setMaximumWidth(940)
        self._caja = QVBoxLayout(self._contenedor)
        self._caja.setContentsMargins(0, 0, 0, 0)
        self._caja.setSpacing(18)
        layout_exterior.addWidget(self._contenedor)

        self._vacio = QLabel(tr(TODAVIA_NO))
        self._vacio.setObjectName("cartel_de_lectura")
        self._vacio.setProperty("role", "tenue")
        self._vacio.setWordWrap(True)
        # **Un ancho con el que se lea.** Centrado y con salto de linea, Qt le
        # daba el ancho minimo y el aviso de mover el mouse quedaba en una
        # columna de tres palabras por renglon.
        self._vacio.setMinimumWidth(460)
        self._vacio.setMaximumWidth(600)
        self._leyendo = False
        self._vacio.setAlignment(Qt.AlignCenter)
        self._caja.addWidget(self._vacio, 0, Qt.AlignHCenter)
        self._caja.addStretch(1)
        self.setWidget(self._cuerpo)

    # --- lo que llega del mouse ------------------------------------------

    def _texto_vacio(self) -> str:
        if not self._leyendo:
            return TODAVIA_NO
        if getattr(self, "_via_leyendo", None) == conexiones.VIA_CABLE:
            return LEYENDO_POR_CABLE
        return LEYENDO

    def leyendo(self, si: bool, via: str | None = None) -> None:
        """Mientras se lee por primera vez, el cartel vacio pide mover el mouse.

        Es el momento en que mas importa: la primera lectura son los siete
        comandos, y con el mouse quieto el dongle pierde la mitad de los
        pedidos. **Por cable no se pide**: no hay radio. Si la lectura no trae
        nada, el cartel vuelve a decir que no se leyo.
        """
        self._leyendo = si
        self._via_leyendo = via
        self._vacio.setText(tr(self._texto_vacio()))
        self._vacio.setProperty("role", "aviso" if si else "tenue")
        # El aviso se lee de izquierda a derecha, como los demas avisos; el
        # "todavia no se leyo", que es una linea sola, va centrado.
        self._vacio.setAlignment((Qt.AlignLeft | Qt.AlignVCenter) if si
                                 else Qt.AlignCenter)
        # **`setStyleSheet` y no `unpolish`/`polish`.** Con esos dos el color
        # cambiaba pero el relleno del aviso no se aplicaba (MEDIDO: los
        # margenes quedaban en 0 y el texto pegado al borde).
        # Una hoja propia, aunque sea un comentario, obliga a Qt a recalcular
        # la caja entera.
        self._vacio.setStyleSheet(f"/* {self._vacio.property('role')} */")

    def poner_estado(self, estado: dict, via: str | None = None) -> None:
        """Dibuja -o refresca- todas las filas desde un estado leido.

        `via` es por donde esta conectado el mouse, cuando se sabe: hay campos
        que dependen del camino y no del modelo -por cable el descriptor no da
        mas de 1000 Hz-, y un desplegable que ofrece 8000 por un camino que no
        puede darlos es un control que no hace lo que dice.
        """
        campos = modelo.campos_de(estado, via=via)
        if self._leyendo:
            self.leyendo(False)
        self._vacio.setVisible(not campos)
        vistos = set()
        for campo in campos:
            vistos.add(campo.clave)
            fila = self._filas.get(campo.clave)
            if fila is None:
                fila = FilaDeCampo(campo)
                fila.pidio_escribir.connect(self.pidio_escribir)
                self._filas[campo.clave] = fila
                self._caja_de(campo.cmd).addWidget(fila)
            fila.poner_campo(campo)
        # Un campo que dejo de venir no se queda mostrando un valor viejo: se
        # esconde. Borrarlo obligaria a rearmar el grupo entero cada vez.
        for clave, fila in self._filas.items():
            fila.setVisible(clave in vistos)
        # **`isHidden()` y no `isVisible()`.** Qt devuelve `isVisible() == False`
        # para todo widget cuya ventana todavia no se mostro, y este panel se
        # llena antes de que la ventana aparezca: preguntando por `isVisible()`
        # los grupos se escondian todos, para siempre, y la pantalla quedaba en
        # blanco con las treinta y dos filas construidas adentro.
        for cmd, grupo in self._grupos.items():
            grupo.setVisible(any(not f.isHidden() for f in self._filas.values()
                                 if f.campo.cmd == cmd))
        # **Despues de las filas, y no antes.** `_caja_de()` crea el grupo la
        # primera vez que alguien lo pide: pidiendolo antes, el grupo de los
        # botones se armaba primero y subia al tope de la pantalla.
        self._poner_diagrama(modelo.botones_fisicos(estado))
        self._poner_acciones(modelo.acciones_de(estado))

    def _poner_acciones(self, acciones) -> None:
        """Cada accion en el grupo de su comando, abajo de la fila que dice."""
        vistas = set()
        for accion in acciones:
            vistas.add(accion.clave)
            if accion.clave in self._acciones:
                continue
            fila = FilaDeAccion(accion)
            fila.pidio_escribir.connect(self.pidio_escribir)
            self._acciones[accion.clave] = fila
            caja = self._caja_de(accion.cmd)
            previa = self._filas.get(accion.despues_de)
            indice = caja.indexOf(previa) if previa is not None else -1
            if indice >= 0:
                caja.insertWidget(indice + 1, fila)
            else:
                caja.addWidget(fila)
        for clave, fila in self._acciones.items():
            fila.setVisible(clave in vistas)

    def acciones(self) -> dict[str, FilaDeAccion]:
        """Las filas de acciones por clave. Lo usan las pruebas."""
        return dict(self._acciones)

    def _poner_diagrama(self, botones) -> None:
        """El esquema, arriba de los controles de los botones.

        **Arriba y no al costado**: el esquema acompaña a las filas que
        remapea, y al costado la lista quedaria en media pantalla para todos
        los demas grupos.
        """
        if not botones:
            if self._diagrama is not None:
                self._diagrama.hide()
            return
        if self._diagrama is None:
            self._diagrama = DiagramaDeBotones()
            self._diagrama.pidio_ver.connect(self.mostrar_campo)
            self._caja_de(botones[0].cmd).insertWidget(0, self._diagrama)
        self._diagrama.poner_botones(botones)

    def mostrar_campo(self, clave: str) -> None:
        """Trae a la vista la fila de ese campo, y la hace notar.

        Lo pide el esquema cuando se toca un numero. La clave viene del
        modelo -`BotonFisico.clave`-, asi que este panel sigue sin conocer
        ninguna por nombre.
        """
        fila = self._filas.get(clave)
        if fila is None or fila.isHidden():
            return
        # El margen deja la fila separada del borde: pegada arriba de todo
        # parece cortada, y no se ve el titulo del grupo al que pertenece.
        self.ensureWidgetVisible(fila, 0, 80)
        fila.destacar()

    def _caja_de(self, cmd: int) -> QVBoxLayout:
        if cmd not in self._grupos:
            grupo = QGroupBox(tr(TITULOS.get(cmd, p.CMD_NAMES.get(cmd, str(cmd)))))
            caja = QVBoxLayout(grupo)
            caja.setContentsMargins(16, 16, 16, 16)
            caja.setSpacing(8)
            self._grupos[cmd] = grupo
            self._cajas[cmd] = caja
            # antes del stretch final, para que los grupos queden arriba
            self._caja.insertWidget(self._caja.count() - 1, grupo)
        return self._cajas[cmd]

    def actualizar_textos(self) -> None:
        """Actualiza los títulos de grupos y las filas tras un cambio de idioma."""
        self._vacio.setText(tr(self._texto_vacio()))
        for cmd, grupo in self._grupos.items():
            grupo.setTitle(tr(TITULOS.get(cmd, p.CMD_NAMES.get(cmd, str(cmd)))))
        for fila in list(self._filas.values()) + list(self._acciones.values()):
            fila.actualizar_textos()
        if self._diagrama is not None:
            self._diagrama.actualizar_textos()

    # --- estado de la pantalla -------------------------------------------

    def revertir(self) -> None:
        """Todas las filas vuelven a lo que dice el modelo. Ver `FilaDeCampo`."""
        for fila in self._filas.values():
            fila.revertir()

    def bloquear(self, si: bool) -> None:
        """Durante una escritura no se toca nada: la Etapa 3 esta corriendo."""
        for fila in list(self._filas.values()) + list(self._acciones.values()):
            fila.bloquear(si)

    def diagrama(self) -> "DiagramaDeBotones | None":
        """El esquema de botones, si el mouse trajo botones."""
        return self._diagrama

    def contenido_de(self, cmd: int) -> list:
        """Lo que hay en el grupo de ese comando, **en el orden dibujado**.

        Lo usan las pruebas: el orden de las filas es el orden fisico de los
        botones, y el esquema va arriba de todas ellas.
        """
        caja = self._cajas.get(cmd)
        if caja is None:
            return []
        return [caja.itemAt(i).widget() for i in range(caja.count())]

    def filas(self) -> dict[str, FilaDeCampo]:
        """Las filas por clave. Lo usa la ventana y lo usan las pruebas."""
        return dict(self._filas)
