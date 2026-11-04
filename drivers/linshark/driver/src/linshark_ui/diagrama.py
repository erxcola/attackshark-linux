# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""El esquema del mouse: cada numero de slot puesto donde cae el boton.

**El dibujo es nuestro, y no se copia el del fabricante.** Se investigo si
servia el del cliente oficial y no: en los 216 archivos del bundle no hay
**ningun SVG de mouse** -los unicos son una fuente de iconos y el logo de Vue-,
el material grafico son PNG propietarios que este proyecto no versiona (ver
`dev/research/README.md`: "de cada cosa se guarda la huella, no el material"), las
coordenadas de los botones viven en un `.css` scoped que nunca se bajo, y
`buttonTableDataX8Pro` tiene **cinco** entradas -izquierdo, derecho, rueda,
adelante, atras-: el diagrama oficial no tendria donde poner el boton de dpi ni
el de modo, que son dos de los siete que esta aplicacion ofrece.

**Lo unico que este modulo aporta es geometria.** Los numeros, los nombres y
la evidencia salen de `modelo.botones_fisicos()`, que a su vez los saca de
`estructuras.BOTONES_POR_NOMBRE`: un mouse con otros slots dibuja los suyos, y
ninguna clave de campo aparece escrita aca.

**Y un numero sobre un boton es una afirmacion.** Que el slot 4 sea el boton
del costado-atras esta MEDIDO -se lo remapeo a "reproducir / pausar", se lo
apreto y la musica se pauso-; los siete estan cerrados, y como se supo cada
uno esta en `estructuras.COMO_SE_SUPO_EL_BOTON`. El que no
este confirmado se dibuja en gris y con un signo de pregunta, que es lo
contrario de amplificar una inferencia a hecho. **La pantalla no cuenta la
evidencia**: el tooltip de un numero dice que boton es y que hace hoy.

**Tres vistas, y no es decoracion**: los botones estan en tres caras. El 1, el
2 y el 3 se ven desde arriba; el 4 y el 5 estan en el costado izquierdo, donde
va el pulgar; y el de dpi y el de modo estan en la **base** (mirado a ojo), a
los dos lados del sensor y a su altura: en la vista desde abajo, el 6 a la
izquierda y el 7 a la derecha (lo fijo el usuario mirando el mouse).
Dibujar un boton en una cara donde no esta seria inventar una posicion.

**La forma sale de una foto del X8 Pro, medida y no calcada** (la paso el
usuario, y no se versiona, por la misma regla que el bundle). De la foto se
tomaron el medio ancho de la vista de arriba fila por fila -promediando los
dos lados, asi que el contorno es simetrico- y los dos bordes de la vista de
costado, con el casco interpolado donde asoma la rueda; los puntos se
remuestrearon a intervalos iguales y se unieron con curvas suaves. Tambien de
la foto: donde caen la rueda, el LED de nivel delante de ella, el corte de los
dos botones principales y los dos botones del costado. **Lo que la foto no
muestra es la base**: la posicion del sensor y de los patines es ilustrativa,
y lo unico medido ahi es donde estan el 6 y el 7 respecto del sensor.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QByteArray, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from . import estilo
from .controles import PopupDeAyuda, rico
from .i18n import tr

#: El radio del circulito con el numero, en unidades del dibujo. Es tambien el
#: radio con el que se acierta un click: lo que se ve es lo que se toca.
RADIO = 17.0

#: El tamaño del numero, en unidades del dibujo.
LETRA = 20

#: El contorno visto desde arriba, en un `viewBox` de 220x425: el mouse mide
#: 205x406 px en la foto, con la punta arriba. Es tambien el de la base, porque
#: es simetrico: mirado desde abajo solo se invierten izquierda y derecha.
SILUETA = (
    "M110 9 C121 9 132 11 142 14 C153 17 163 21 173 26 "
    "C182 32 191 39 197 47 C203 56 206 68 208 78 "
    "C210 89 209 100 209 111 C209 122 209 133 209 144 "
    "C209 155 208 166 208 177 C207 188 207 199 207 210 "
    "C206 221 207 232 207 242 C208 253 210 264 211 275 "
    "C211 286 212 297 211 308 C211 319 210 330 206 340 "
    "C203 351 199 361 193 370 C187 379 179 388 171 394 "
    "C163 401 152 406 142 410 C132 414 121 416 110 416 "
    "C99 416 88 414 78 410 C68 406 57 401 49 394 C41 388 33 379 27 370 "
    "C21 361 17 351 14 340 C10 330 9 319 9 308 C8 297 9 286 9 275 "
    "C10 264 12 253 13 242 C13 232 14 221 13 210 C13 199 13 188 12 177 "
    "C12 166 11 155 11 144 C11 133 11 122 11 111 C11 100 10 89 12 78 "
    "C14 68 17 56 23 47 C29 39 38 32 47 26 C57 21 67 17 78 14 "
    "C88 11 99 9 110 9 Z")

#: El costado izquierdo, en un `viewBox` de 150x425: la base es el borde de la
#: izquierda, el lomo el de la derecha y la punta queda arriba, como en la foto
#: (133x404 px).
PERFIL = (
    "M58 11 C65 12 69 25 73 32 C78 40 83 47 87 55 C91 63 95 71 99 78 "
    "C104 86 108 94 112 102 C116 110 120 118 124 126 "
    "C127 134 130 142 132 151 C135 159 137 168 138 177 "
    "C140 185 141 194 142 203 C142 212 142 221 142 229 "
    "C142 238 141 247 140 256 C139 265 138 273 136 282 "
    "C134 291 132 299 129 308 C126 316 123 324 119 332 "
    "C116 340 112 348 107 356 C102 363 97 370 91 377 "
    "C85 384 79 390 72 395 C65 401 57 407 50 409 C42 412 34 412 28 409 "
    "C22 406 16 398 13 390 C10 383 11 373 10 364 C10 355 10 346 10 337 "
    "C10 329 10 320 10 311 C10 302 10 293 10 284 C11 276 11 267 11 258 "
    "C11 249 12 240 12 231 C12 222 12 214 12 205 C12 196 12 187 12 178 "
    "C12 169 12 161 12 152 C12 143 12 134 11 125 C11 116 10 108 10 99 "
    "C10 90 9 81 10 72 C11 63 12 54 16 47 C20 39 27 33 34 27 "
    "C41 21 52 10 58 11 Z")


@dataclass(frozen=True)
class Vista:
    """Un dibujo del mouse y donde cae cada slot **en ese dibujo**.

    `dibujo` es el SVG sin los numeros: los pone `_Dibujo`, que es el que sabe
    cuales hay que poner y cuales estan confirmados.
    """

    titulo: str
    ancho: float
    alto: float
    dibujo: str
    posiciones: dict[int, tuple[float, float]]


_ARRIBA = f"""
  <path d="{SILUETA}" fill="{{relleno}}" stroke="currentColor"
        stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M22 58 Q16 110 17 160" fill="none" stroke="currentColor"
        stroke-width="1.5" opacity="0.5"/>
  <path d="M198 58 Q204 110 203 160" fill="none" stroke="currentColor"
        stroke-width="1.5" opacity="0.5"/>
  <path d="M17 160 Q110 196 203 160" fill="none" stroke="currentColor"
        stroke-width="1.6" opacity="0.6"/>
  <path d="M110 118 L110 178" fill="none" stroke="currentColor"
        stroke-width="1.5" opacity="0.6"/>
  <rect x="95" y="14" width="30" height="106" rx="14" fill="{{tenue}}"
        stroke="currentColor" stroke-width="1.4" opacity="0.9"/>
  <rect x="104" y="28" width="12" height="5" rx="2.5" fill="{{acento}}"/>
  <rect x="99" y="54" width="22" height="60" rx="9" fill="{{relleno}}"
        stroke="currentColor" stroke-width="1.6"/>
  <path d="M101 66 H119 M101 76 H119 M101 86 H119 M101 96 H119 M101 106 H119"
        stroke="currentColor" stroke-width="1" opacity="0.35"/>
  <path d="M10.5 140 L10 186 M10 194 L10.5 240" stroke="currentColor"
        stroke-width="4" stroke-linecap="round" opacity="0.55"/>
"""

_COSTADO = f"""
  <rect x="90" y="56" width="26" height="62" rx="13" fill="{{tenue}}"
        stroke="currentColor" stroke-width="1.6"/>
  <path d="{PERFIL}" fill="{{relleno}}" stroke="currentColor"
        stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M58 30 C72 70 86 128 100 156 S128 182 140 190" fill="none"
        stroke="currentColor" stroke-width="1.5" opacity="0.55"/>
  <rect x="-9" y="-27" width="18" height="54" rx="9" fill="{{tenue}}"
        stroke="currentColor" stroke-width="1.6"
        transform="translate(73.5 157.5) rotate(-8)"/>
  <rect x="-9" y="-29" width="18" height="58" rx="9" fill="{{tenue}}"
        stroke="currentColor" stroke-width="1.6"
        transform="translate(81.5 223) rotate(-8)"/>
"""

_ABAJO = f"""
  <path d="{SILUETA}" fill="{{relleno}}" stroke="currentColor"
        stroke-width="2.5" stroke-linejoin="round"/>
  <rect x="55" y="40" width="110" height="14" rx="7" fill="{{tenue}}"
        stroke="currentColor" stroke-width="1.2" opacity="0.8"/>
  <rect x="50" y="366" width="120" height="14" rx="7" fill="{{tenue}}"
        stroke="currentColor" stroke-width="1.2" opacity="0.8"/>
  <circle cx="110" cy="164" r="22" fill="{{tenue}}" stroke="currentColor"
          stroke-width="1.6"/>
  <circle cx="110" cy="164" r="8" fill="currentColor" opacity="0.7"/>
"""

#: Las tres vistas, con la posicion de cada slot **en unidades del dibujo**.
#:
#: Los de arriba y los del costado caen sobre los botones de la foto. El 6 y el
#: 7 van **a los costados del sensor y a su misma altura**, el 6 a la izquierda
#: y el 7 a la derecha -`6 [] 7`, como se lo dibujo mirando el mouse-.
VISTAS = (
    Vista("Visto desde arriba", 220, 425, _ARRIBA,
          {1: (60, 105), 2: (160, 105), 3: (110, 84)}),
    Vista("Visto desde la izquierda", 150, 425, _COSTADO,
          {5: (73.5, 157.5), 4: (81.5, 223)}),
    Vista("Visto desde abajo", 220, 425, _ABAJO,
          {6: (60, 164), 7: (160, 164)}),
)

#: Lo que sale detras del `?` del esquema: que es y para que sirve, como en
#: el `?` de cada fila. Lo medido -de donde sale cada numero, de donde sale la
#: forma- esta en el docstring de este modulo y en `dev/docs/`.
AYUDA = (
    ("nota", "Muestra dónde está cada botón del mouse, con el mismo número "
             "que tiene en la lista de abajo: arriba, en el costado izquierdo "
             "y en la base.\n\nTocá un número para ir a su configuración."),
)


def colores_de(widget) -> dict[str, str]:
    """Los colores del dibujo: los del tema propio, o los del escritorio.

    Con `--sin-tema` la aplicacion no pone hoja de estilos y Qt dibuja con la
    paleta del escritorio; el esquema tiene que seguir a la que haya, porque un
    trazo oscuro sobre un fondo oscuro no es un dibujo. El trazo y los numeros
    van por `currentColor` -que `QSvgRenderer` si resuelve, si el `<svg>` trae
    un atributo `color`-, asi que alcanza con decirlo una vez.
    """
    app = QApplication.instance()
    if getattr(app, "styleSheet", lambda: "")():
        c = estilo.COLORES
        return {"trazo": c["texto_tenue"], "relleno": c["fondo_control"],
                "tenue": c["fondo_control_hover"], "acento": c["acento"],
                "sobre_acento": "#ffffff", "apagado": c["borde_hover"]}
    pal = widget.palette()
    texto = pal.color(QPalette.WindowText)
    return {"trazo": texto.name(),
            "relleno": pal.color(QPalette.Base).name(),
            "tenue": pal.color(QPalette.AlternateBase).name(),
            "acento": pal.color(QPalette.Highlight).name(),
            "sobre_acento": pal.color(QPalette.HighlightedText).name(),
            "apagado": pal.color(QPalette.Mid).name()}


class _Dibujo(QWidget):
    """Una vista del mouse, con sus numeros, y que sabe cual se toco."""

    tocaron = Signal(int)

    #: Cuanto mide el dibujo en pantalla. Alto fijo y ancho por proporcion:
    #: mas grande no se lee mejor y se come la lista de controles, que es lo
    #: que el esquema viene a acompañar.
    ALTO = 280

    def __init__(self, vista: Vista, parent=None) -> None:
        super().__init__(parent)
        self.vista = vista
        self._botones: dict[int, object] = {}
        ancho = int(self.ALTO * vista.ancho / vista.alto)
        self.setFixedSize(ancho, self.ALTO)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    # --- lo que hay que dibujar -------------------------------------------

    def poner_botones(self, botones: dict) -> None:
        """`{slot: BotonFisico}`. Solo se dibujan los que esta vista ubica."""
        self._botones = {s: b for s, b in botones.items()
                         if s in self.vista.posiciones}
        self._actualizar_tooltip()
        self.update()

    def _actualizar_tooltip(self) -> None:
        # Que boton es cada numero y que hace hoy. Como se supo que el numero
        # es ese boton es evidencia, y no va en pantalla.
        partes = []
        for slot, bot in sorted(self._botones.items()):
            duda = "" if bot.confirmado else f" ({tr('sin confirmar')})"
            partes.append(f"{slot} · {tr(bot.nombre)}{duda}: "
                          f"{tr(bot.funcion_legible)}")
        self.setToolTip("\n".join(partes))

    def actualizar_textos(self) -> None:
        self._actualizar_tooltip()

    def slots(self) -> tuple:
        """Los que esta vista esta dibujando. Lo usan las pruebas."""
        return tuple(sorted(self._botones))

    def svg(self) -> str:
        """El dibujo entero, numeros incluidos. Es texto: se puede mirar."""
        c = colores_de(self)
        cuerpo = [self.vista.dibujo.format(**c)]
        for slot, bot in sorted(self._botones.items()):
            x, y = self.vista.posiciones[slot]
            # **El gris y el `?` son la baranda del dibujo.** Un slot que no se
            # pudo confirmar no puede salir igual que uno medido: eso seria el
            # diagrama afirmando lo que el proyecto no sabe.
            relleno = c["acento"] if bot.confirmado else c["apagado"]
            texto = c["sobre_acento"] if bot.confirmado else c["trazo"]
            etiqueta = str(slot) if bot.confirmado else f"{slot}?"
            cuerpo.append(
                f'<circle cx="{x}" cy="{y}" r="{RADIO}" fill="{relleno}" '
                f'stroke="currentColor" stroke-width="1.5"/>'
                # `QSvgRenderer` ignora `dominant-baseline`: el numero se baja
                # a mano un tercio de su altura, que es donde queda centrado.
                f'<text x="{x}" y="{y + LETRA * 0.36:g}" fill="{texto}" '
                f'font-size="{LETRA}" font-weight="700" text-anchor="middle" '
                f'font-family="sans-serif">{etiqueta}</text>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 {self.vista.ancho:g} {self.vista.alto:g}" '
                f'color="{c["trazo"]}">{"".join(cuerpo)}</svg>')

    # --- de unidades del dibujo a pixeles y al reves -----------------------

    def _marco(self) -> QRectF:
        """Donde cae el dibujo adentro del widget, con su proporcion."""
        escala = min(self.width() / self.vista.ancho,
                     self.height() / self.vista.alto)
        ancho, alto = self.vista.ancho * escala, self.vista.alto * escala
        return QRectF((self.width() - ancho) / 2, (self.height() - alto) / 2,
                      ancho, alto)

    def punto_de(self, slot: int) -> QPoint | None:
        """Donde cae, en pixeles, el numero de ese slot."""
        if slot not in self.vista.posiciones:
            return None
        x, y = self.vista.posiciones[slot]
        marco = self._marco()
        escala = marco.width() / self.vista.ancho
        return QPoint(int(marco.x() + x * escala),
                      int(marco.y() + y * escala))

    def slot_en(self, punto) -> int | None:
        """Que numero se toco, si se toco alguno. Lo que se ve es lo que se toca."""
        marco = self._marco()
        escala = marco.width() / self.vista.ancho
        if not escala:
            return None
        p = QPointF((punto.x() - marco.x()) / escala,
                    (punto.y() - marco.y()) / escala)
        for slot in self._botones:
            x, y = self.vista.posiciones[slot]
            if (p.x() - x) ** 2 + (p.y() - y) ** 2 <= RADIO ** 2:
                return slot
        return None

    # --- Qt ---------------------------------------------------------------

    def paintEvent(self, evento) -> None:           # noqa: N802 - API de Qt
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        QSvgRenderer(QByteArray(self.svg().encode("utf-8"))).render(
            pintor, self._marco())
        pintor.end()

    def mousePressEvent(self, evento) -> None:      # noqa: N802 - API de Qt
        slot = self.slot_en(evento.position().toPoint())
        if slot is not None:
            self.tocaron.emit(slot)
        else:
            super().mousePressEvent(evento)


class DiagramaDeBotones(QWidget):
    """El esquema entero: la cabecera que lo pliega y las dos vistas.

    Emite `pidio_ver(clave)` con la clave del campo de ese boton, asi que quien
    lo use va del numero del dibujo a la fila del control **sin conocer ningun
    nombre de campo**.
    """

    pidio_ver = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        caja = QVBoxLayout(self)
        caja.setContentsMargins(8, 6, 8, 14)
        caja.setSpacing(12)

        cabecera = QHBoxLayout()
        cabecera.setSpacing(10)
        self.plegar = QPushButton()
        self.plegar.setCheckable(True)
        self.plegar.setChecked(True)
        self.plegar.toggled.connect(self._al_plegar)
        cabecera.addWidget(self.plegar)
        self.pista = QLabel(tr("Tocá un número para ir a su control"))
        self.pista.setProperty("role", "tenue")
        cabecera.addWidget(self.pista)
        cabecera.addStretch(1)
        self.ayuda = QPushButton("?")
        self.ayuda.setProperty("role", "ayuda")
        self.ayuda.setFixedSize(22, 22)
        self.ayuda.setFlat(True)
        self.ayuda.setToolTip(tr("Qué es y para qué sirve"))
        self.ayuda.clicked.connect(self.mostrar_ayuda)
        cabecera.addWidget(self.ayuda)
        caja.addLayout(cabecera)

        self.cuerpo = QWidget()
        cuerpo = QHBoxLayout(self.cuerpo)
        cuerpo.setContentsMargins(0, 4, 0, 8)
        cuerpo.setSpacing(32)
        cuerpo.addStretch(1)
        self._dibujos = []
        self._titulos_vistas = []
        for vista in VISTAS:
            columna = QVBoxLayout()
            columna.setSpacing(8)
            dibujo = _Dibujo(vista, self)
            dibujo.tocaron.connect(self._al_tocar)
            columna.addWidget(dibujo, 0, Qt.AlignHCenter)
            titulo = QLabel(tr(vista.titulo))
            titulo.setProperty("role", "tenue")
            titulo.setAlignment(Qt.AlignHCenter)
            columna.addWidget(titulo)
            cuerpo.addLayout(columna)
            self._dibujos.append(dibujo)
            self._titulos_vistas.append((titulo, vista.titulo))
        cuerpo.addStretch(1)
        caja.addWidget(self.cuerpo)

        #: Los slots que el modelo trae y **ningun dibujo ubica**. No se
        #: esconden: que no sepamos donde cae un boton no lo borra del mouse.
        self.sin_ubicar = QLabel()
        self.sin_ubicar.setProperty("role", "aviso")
        self.sin_ubicar.setWordWrap(True)
        self.sin_ubicar.hide()
        caja.addWidget(self.sin_ubicar)

        self._claves: dict[int, str] = {}
        self._huerfanos: list = []
        self._popup: PopupDeAyuda | None = None
        self._al_plegar(True)

    # --- lo que llega del modelo ------------------------------------------

    def poner_botones(self, botones) -> None:
        """`modelo.botones_fisicos(estado)`, tal cual viene."""
        por_slot = {b.slot: b for b in botones}
        self._claves = {b.slot: b.clave for b in botones}
        for dibujo in self._dibujos:
            dibujo.poner_botones(por_slot)
        ubicados = {s for d in self._dibujos for s in d.slots()}
        self._huerfanos = [b for b in botones if b.slot not in ubicados]
        self._actualizar_sin_ubicar()
        self.setVisible(bool(botones))

    def _actualizar_sin_ubicar(self) -> None:
        if self._huerfanos:
            quienes = ", ".join(f"{b.slot} ({tr(b.nombre)})" for b in self._huerfanos)
            self.sin_ubicar.setText(rico(tr(
                f"el esquema no sabe dónde cae {quienes}: el mouse los tiene y "
                "se configuran abajo, pero **dibujarlos sería inventar una "
                "posición**")))
        self.sin_ubicar.setVisible(bool(self._huerfanos))

    def dibujos(self) -> tuple:
        """Las vistas. Lo usan las pruebas."""
        return tuple(self._dibujos)

    # --- la pantalla -------------------------------------------------------

    def _al_tocar(self, slot: int) -> None:
        clave = self._claves.get(slot)
        if clave:
            self.pidio_ver.emit(clave)

    def _al_plegar(self, abierto: bool) -> None:
        self.cuerpo.setVisible(abierto)
        self.pista.setVisible(abierto)
        self.plegar.setText(f"▾  {tr('Esquema del mouse')}" if abierto
                            else f"▸  {tr('Esquema del mouse')}")

    def mostrar_ayuda(self) -> None:
        if self._popup is None:
            self._popup = PopupDeAyuda(self)
        # Sin traducir: `poner_textos()` traduce, y dos veces no es dos veces
        # mejor -un texto ya traducido que vuelve a pasar se anota faltante-.
        self._popup.poner_textos("Esquema del mouse", AYUDA)
        self._popup.abrir_junto_a(self.ayuda)

    def actualizar_textos(self) -> None:
        """Actualiza los textos tras un cambio de idioma."""
        self.pista.setText(tr("Tocá un número para ir a su control"))
        self.ayuda.setToolTip(tr("Qué es y para qué sirve"))
        self._al_plegar(self.plegar.isChecked())
        for lbl, orig in self._titulos_vistas:
            lbl.setText(tr(orig))
        for dibujo in self._dibujos:
            dibujo.actualizar_textos()
        self._actualizar_sin_ubicar()
        if self._popup is not None and self._popup.isVisible():
            self._popup.poner_textos("Esquema del mouse", AYUDA)

    def popup(self) -> "PopupDeAyuda | None":
        """El popup, si alguna vez se abrio. Lo usan las pruebas."""
        return self._popup
