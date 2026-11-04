# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""El tema de la ventana, en un solo lugar.

**Es opcional a proposito.** Qt toma el tema del escritorio -Breeze en KDE, el
que haya en GTK- y pisarlo siempre seria decidir por el que mira. Con
`--sin-tema` la ventana se dibuja con el del sistema y todo sigue andando: lo
que se pierde es la paleta, no la informacion. Los tres colores que SI importan
-el de advertencia, el de discrepancia con el cliente oficial y el de campo no
escribible- viven ademas en propiedades de Qt (`role`), asi que se distinguen
con cualquier tema.
"""

from __future__ import annotations

#: Los colores, con nombre. Se eligieron con el contraste en mente: el texto
#: normal da 12:1 contra el fondo y el de advertencia 7:1, que es holgado para
#: AA en cuerpo chico.
COLORES = {
    "fondo": "#0c0f14",
    "fondo_panel": "#151921",
    "fondo_control": "#1e2430",
    "fondo_control_hover": "#283141",
    "borde": "#2a3344",
    "borde_hover": "#3d4960",
    "borde_foco": "#3b82f6",
    "texto": "#f1f5f9",
    "texto_tenue": "#8a99ad",
    "acento": "#3b82f6",
    "acento_hover": "#60a5fa",
    "aviso": "#f59e0b",
    "peligro": "#ef4444",
    "ok": "#10b981",
}

QSS = """
QWidget {{
    background: {fondo};
    color: {texto};
    font-size: 13px;
}}
QMainWindow::separator {{ background: {borde}; }}

QFrame#panel, QGroupBox {{
    background: {fondo_panel};
    border: 1px solid {borde};
    border-radius: 14px;
}}
QGroupBox {{
    margin-top: 24px;
    padding: 20px 16px 16px 16px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    top: 2px;
    padding: 4px 12px;
    color: {acento};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    background: {fondo_control};
    border: 1px solid {borde};
    border-radius: 8px;
}}

/* La fila que el esquema de botones manda mirar. Dura un segundo y medio y
   se apaga sola: es para encontrarla con la vista, no para dejarla marcada.
   Con `--sin-tema` esto no existe, y por eso `destacar()` ademas le da el
   foco al control, que se ve con cualquier tema. */
QFrame#fila {{
    border-radius: 8px;
    border: 1px solid transparent;
}}
QFrame#fila:hover {{
    background: rgba(255, 255, 255, 0.025);
    border-color: rgba(255, 255, 255, 0.04);
}}
QFrame#fila[destacada="true"] {{
    background: rgba(59, 130, 246, 0.16);
    border: 1px solid rgba(59, 130, 246, 0.45);
    border-radius: 8px;
}}

QFrame#grabador {{
    background: {fondo_control};
    border: 1px dashed {borde};
    border-radius: 10px;
}}
QFrame#grabador:focus {{
    border-color: {acento};
}}
QFrame#grabador[grabando="true"] {{
    background: rgba(245, 158, 11, 0.08);
    border: 1px dashed {aviso};
}}

/* El aviso de mover el mouse mientras se lee por primera vez: es lo unico
   que hay en pantalla en ese momento, asi que se lee comodo. */
QLabel#cartel_de_lectura[role="aviso"] {{
    font-size: 13px;
    padding: 14px 18px;
    border-radius: 10px;
}}

/* El numero de un boton en su fila: el mismo circulo que el esquema. */
QLabel#numero_de_boton {{
    background: {acento};
    color: #ffffff;
    border: 1px solid {borde_hover};
    border-radius: 11px;
    font-size: 11px;
    font-weight: 700;
}}

/* Sin esto las etiquetas pintan el fondo general adentro de un grupo, y
   cada nota queda como una banda mas oscura cruzando la fila. */
QLabel {{ background: transparent; }}
QLabel[role="titulo"] {{ font-size: 15px; font-weight: 700; color: {texto}; }}
QLabel[role="tenue"]  {{ color: {texto_tenue}; }}
QLabel[role="chip"]   {{
    background: {fondo_control};
    border: 1px solid {borde};
    border-radius: 6px;
    padding: 3px 10px;
    font-family: monospace;
    font-size: 11px;
    color: {texto_tenue};
}}
QLabel[role="nota"]   {{ color: {texto_tenue}; font-size: 12px; padding: 3px 0; }}
QLabel[role="aviso"]  {{
    color: {aviso};
    font-size: 11px;
    padding: 7px 12px;
    background: rgba(245, 158, 11, 0.10);
    border-left: 3px solid {aviso};
    border-radius: 6px;
    margin-top: 4px;
}}
QLabel[role="discrepancia"] {{
    color: {peligro};
    font-size: 11px;
    font-weight: 600;
    padding: 7px 12px;
    background: rgba(239, 68, 68, 0.10);
    border-left: 3px solid {peligro};
    border-radius: 6px;
    margin-top: 4px;
}}
QLabel[role="ok"]     {{ color: {ok}; font-weight: 600; }}
QLabel[role="peligro"] {{ color: {peligro}; font-weight: 600; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {fondo_control};
    border: 1px solid {borde};
    border-radius: 8px;
    padding: 6px 11px;
    color: {texto};
    selection-background-color: {acento};
    selection-color: #ffffff;
}}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
    border-color: {borde_hover};
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus {{
    border-color: {acento};
    background: {fondo_control_hover};
}}
QComboBox {{
    padding-right: 20px;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}}
QComboBox QAbstractItemView {{
    background: {fondo_panel};
    border: 1px solid {borde};
    border-radius: 8px;
    selection-background-color: {acento};
    selection-color: #ffffff;
    padding: 4px;
}}

QPushButton {{
    background: {fondo_control};
    border: 1px solid {borde};
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 500;
    font-size: 13px;
    color: {texto};
}}
QPushButton:hover {{
    background: {fondo_control_hover};
    border-color: {borde_hover};
}}
QPushButton:pressed {{ background: {borde}; }}
QPushButton:disabled {{
    color: {texto_tenue};
    border-color: {borde};
    background: {fondo_panel};
}}
QPushButton[role="primario"] {{
    background: {acento};
    color: #ffffff;
    border: 1px solid {acento};
    font-weight: 600;
    padding: 7px 18px;
}}
QPushButton[role="primario"]:hover {{
    background: {acento_hover};
    border-color: {acento_hover};
}}
QPushButton[role="primario"]:pressed {{ background: #2563eb; }}
QPushButton[role="primario"]:disabled {{
    background: {borde};
    border-color: {borde};
    color: {texto_tenue};
}}

/* El `?` de cada fila. Tiene que estar **a mano y callado**: lo que explica
   importa, pero treinta signos de pregunta gritando al costado serian el mismo
   muro de texto que vinieron a reemplazar. Se apaga hasta que se lo mira. */
QPushButton[role="ayuda"] {{
    background: transparent;
    border: 1px solid {borde};
    border-radius: 11px;
    padding: 0;
    color: {texto_tenue};
    font-weight: 700;
    font-size: 11px;
}}
QPushButton[role="ayuda"]:hover {{
    background: {fondo_control};
    border-color: {acento};
    color: {acento};
}}
QPushButton[role="ayuda"]:pressed {{ background: {fondo_control_hover}; }}

QPushButton#boton_idioma {{
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 600;
    border-radius: 8px;
    background: {fondo_control};
    border: 1px solid {borde};
    color: {texto};
}}
QPushButton#boton_idioma:hover {{
    background: {fondo_control_hover};
    border-color: {borde_hover};
}}
QPushButton#boton_idioma::menu-indicator {{
    image: none;
    width: 0px;
}}

QMenu {{
    background: {fondo_panel};
    border: 1px solid {borde};
    border-radius: 10px;
    padding: 6px;
    color: {texto};
}}
QMenu::item {{
    padding: 7px 18px;
    border-radius: 6px;
    margin: 2px 4px;
}}
QMenu::item:selected {{
    background: {acento};
    color: #ffffff;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: {fondo_control};
    border: 1px solid {borde};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {acento};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: #ffffff;
    border: 2px solid {acento};
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {acento_hover};
    border: 2px solid #ffffff;
}}
QSlider::handle:horizontal:disabled {{
    background: {borde};
    border-color: {fondo_control};
}}

QCheckBox {{
    spacing: 10px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {borde};
    border-radius: 6px;
    background: {fondo_control};
}}
QCheckBox::indicator:hover {{
    border-color: {acento};
}}
QCheckBox::indicator:checked {{
    background: {acento};
    border-color: {acento};
}}
QCheckBox:disabled {{ color: {texto_tenue}; }}

QTabWidget::pane {{
    border: none;
    background: transparent;
    padding-top: 12px;
}}
QTabBar {{
    background: {fondo_panel};
    border: 1px solid {borde};
    border-radius: 12px;
    padding: 4px;
}}
QTabBar::tab {{
    background: transparent;
    padding: 8px 24px;
    border-radius: 8px;
    color: {texto_tenue};
    font-size: 13px;
    font-weight: 500;
    margin: 2px;
}}
QTabBar::tab:hover {{
    color: {texto};
    background: {fondo_control};
}}
QTabBar::tab:selected {{
    color: #ffffff;
    background: {acento};
    font-weight: 600;
}}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px 4px 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.16);
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.30);
}}
QScrollBar::handle:vertical:pressed {{
    background: {acento};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0 4px 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.16);
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{
    background: rgba(255, 255, 255, 0.30);
}}
QScrollBar::handle:horizontal:pressed {{
    background: {acento};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

QStatusBar {{
    background: {fondo_panel};
    border-top: 1px solid {borde};
    padding: 6px 16px;
}}
QStatusBar::item {{ border: none; }}

QPlainTextEdit {{
    font-family: monospace;
    font-size: 12px;
    border-radius: 8px;
}}

QListWidget {{
    background: {fondo_control};
    border: 1px solid {borde};
    border-radius: 8px;
}}
QListWidget::item:selected {{ background: {acento}; color: {fondo}; }}

/* El selector de funciones de boton: los grupos al costado se ven como las
   pestanas de arriba, y las opciones con aire para apuntarles. */
QListWidget#categorias, QListWidget#opciones {{
    background: {fondo_control};
    padding: 4px;
    outline: none;
}}
QListWidget#categorias::item, QListWidget#opciones::item {{
    padding: 7px 10px;
    border-radius: 6px;
}}
QListWidget#categorias::item {{ color: {texto_tenue}; }}
QListWidget#categorias::item:hover, QListWidget#opciones::item:hover {{
    background: {fondo_control_hover};
    color: {texto};
}}
QListWidget#categorias::item:selected, QListWidget#opciones::item:selected {{
    background: {acento};
    color: #ffffff;
    font-weight: 600;
}}
QLabel#sin_resultados {{
    background: {fondo_control};
    border: 1px solid {borde};
    border-radius: 8px;
}}
QListWidget#opciones::item:disabled {{
    color: {acento};
    background: transparent;
    padding-top: 10px;
}}
"""


def hoja() -> str:
    """El QSS ya resuelto con la paleta."""
    return QSS.format(**COLORES)


def aplicar(app) -> None:
    """Le pone el tema a la aplicacion."""
    app.setStyleSheet(hoja())
