# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""De una tecla de Qt al nombre que entiende un macro.

Es traduccion de **Qt**, no de protocolo: los nombres de llegada son los de
`estructuras.TECLAS_HID`, que ya estan en castellano y ya se validan alla. Lo
unico que hay aca es el puente entre `Qt.Key_Left` y `"flecha-izquierda"`.

Las flechas se llaman `flecha-*` por el motivo que explica `TECLAS_HID`: en un
macro "arriba" y "abajo" son las dos direcciones de un evento, y dos cosas
distintas con el mismo nombre en la misma pantalla es una trampa.
"""

from __future__ import annotations

from PySide6.QtCore import Qt

from linshark import estructuras as est

#: Las que Qt nombra distinto. Las letras y los digitos salen del bucle de
#: abajo, y los modificadores entran como tecla suelta -adentro de un macro el
#: Ctrl se aprieta y se suelta como cualquier otra-.
POR_TECLA_QT = {
    Qt.Key_Escape: "esc", Qt.Key_Tab: "tab", Qt.Key_Backspace: "retroceso",
    Qt.Key_Return: "enter", Qt.Key_Enter: "num-enter",
    Qt.Key_Insert: "insert", Qt.Key_Delete: "supr", Qt.Key_Pause: "pausa",
    Qt.Key_Print: "impr-pant", Qt.Key_Home: "inicio", Qt.Key_End: "fin",
    Qt.Key_Left: "flecha-izquierda", Qt.Key_Up: "flecha-arriba",
    Qt.Key_Right: "flecha-derecha", Qt.Key_Down: "flecha-abajo",
    Qt.Key_PageUp: "re-pag", Qt.Key_PageDown: "av-pag",
    Qt.Key_CapsLock: "bloq-mayus", Qt.Key_NumLock: "bloq-num",
    Qt.Key_ScrollLock: "bloq-despl", Qt.Key_Space: "espacio",
    Qt.Key_Minus: "guion", Qt.Key_Equal: "igual",
    Qt.Key_BracketLeft: "corchete-abre", Qt.Key_BracketRight: "corchete-cierra",
    Qt.Key_Backslash: "barra-invertida", Qt.Key_Semicolon: "punto-y-coma",
    Qt.Key_Apostrophe: "comilla", Qt.Key_QuoteLeft: "tilde-grave",
    Qt.Key_Comma: "coma", Qt.Key_Period: "punto", Qt.Key_Slash: "barra",
    Qt.Key_Menu: "menu",
    Qt.Key_Control: "ctrl", Qt.Key_Shift: "shift", Qt.Key_Alt: "alt",
    Qt.Key_Meta: "win",
    **{getattr(Qt, f"Key_F{n}"): f"f{n}" for n in range(1, 25)},
    **{getattr(Qt, f"Key_{c}"): c.lower()
       for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    **{getattr(Qt, f"Key_{d}"): str(d) for d in range(10)},
}

#: **El teclado numerico son las mismas teclas de Qt con `KeypadModifier`**:
#: no existe `Qt.Key_Numpad5`, el 5 del pad llega como `Key_5`. Sin mirar el
#: modificador, el pad se grababa como la fila de arriba -otro usage HID, o sea
#: otra tecla- y el `+` y el `*`, que no estan en la tabla de arriba porque en
#: la fila principal son combinaciones con Shift, se perdian del todo.
#:
#: `TECLAS_HID` los tiene a los diecisiete, asi que lo unico que faltaba era
#: mirar el modificador.
POR_TECLA_NUMERICA = {
    **{getattr(Qt, f"Key_{d}"): f"num-{d}" for d in range(10)},
    Qt.Key_Plus: "num-mas", Qt.Key_Minus: "num-menos",
    Qt.Key_Asterisk: "num-multiplicar", Qt.Key_Slash: "num-dividir",
    Qt.Key_Enter: "num-enter", Qt.Key_Equal: "num-igual",
    # La coma es el separador decimal del pad en los teclados latinos, y el
    # punto en los ingleses: los dos son la misma tecla fisica.
    Qt.Key_Period: "num-punto", Qt.Key_Comma: "num-punto",
}

#: Los cinco botones del mouse, que en un macro son eventos como las teclas.
POR_BOTON_QT = {
    Qt.LeftButton: "clic-izquierdo",
    Qt.RightButton: "clic-derecho",
    Qt.MiddleButton: "clic-rueda",
    Qt.ForwardButton: "adelante",
    Qt.BackButton: "atras",
}


def nombre_de_tecla(tecla, modificadores=None) -> str | None:
    """El nombre del macro para esa tecla de Qt, o None si no entra.

    `modificadores` son los de `QKeyEvent.modifiers()`. Solo se mira uno,
    `KeypadModifier`, que es lo unico que distingue el 5 del pad del 5 de la
    fila de arriba: para Qt son la misma `Key_5` y para el mouse son dos
    usages distintos.

    **None no es un error de la traduccion**: hay teclas que el bloque de macro
    no puede expresar, y decirlo es mejor que mandar un usage inventado. Quien
    llame tiene que **avisarlo**, no tragarselo. Se verifica contra la
    biblioteca, no contra esta tabla.
    """
    nombre = None
    if modificadores is not None and (modificadores & Qt.KeypadModifier):
        nombre = POR_TECLA_NUMERICA.get(tecla)
    if nombre is None:
        nombre = POR_TECLA_QT.get(tecla)
    if nombre is None:
        return None
    try:
        est.usage_de_evento(nombre)
    except ValueError:                             # pragma: no cover
        return None
    return nombre


def nombre_de_boton(boton) -> str | None:
    """Lo mismo para los cinco botones del mouse."""
    return POR_BOTON_QT.get(boton)
