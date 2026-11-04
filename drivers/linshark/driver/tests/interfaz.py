#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Las barandas de la interfaz, verificadas sin hardware y sin ventana.

Vive aparte de `salvaguardas.py` a proposito: aquella no depende de Qt, y no
tiene por que. Esta si, asi que se corre sola.

    $ python3 driver/tests/interfaz.py
"""

from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

# **Sin pantalla.** Desde que hay widgets hace falta una `QApplication`, y con
# esta plataforma Qt la construye sin servidor grafico: la tanda corre igual
# por ssh y en un tty. Se respeta lo que haya puesto quien la corre, para poder
# mirar la ventana de verdad cuando haga falta.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# **Los tests no tocan las carpetas de quien los corre**: algunos scripts piden
# la de respaldos al importarse, y una prueba no escribe en el HOME de nadie.
import tempfile as _tempfile  # noqa: E402
_CASA_DE_PRUEBA = _tempfile.mkdtemp(prefix="linshark-tests-")
os.environ["XDG_CONFIG_HOME"] = f"{_CASA_DE_PRUEBA}/config"
os.environ["XDG_STATE_HOME"] = f"{_CASA_DE_PRUEBA}/state"

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from linshark import protocol as p  # noqa: E402
from linshark import sesion  # noqa: E402
from linshark_ui.hardware import Hardware, _legible  # noqa: E402
from salvaguardas import _MouseFalso  # noqa: E402


def se_ve(widget) -> bool:
    """Si el widget no se escondio a proposito.

    **No es `isVisible()`.** Qt lo devuelve falso mientras la ventana de arriba
    no se mostro, y aca no se muestra ninguna: lo que se prueba es la decision
    del panel -mostrar esta advertencia, esconder esta otra-, no si hay un
    servidor grafico.
    """
    return not widget.isHidden()


def _correr_hasta(app, condicion, segundos=15) -> bool:
    """Procesa eventos de Qt hasta que `condicion()` sea cierta.

    **Cuando se acaba el tiempo lo dice por stderr**, aunque quien llame ignore
    el resultado. La mayoria de los llamados no lo miran -esperan algo que
    despues comprueban de otra forma-, asi que una espera vencida se convertia
    en un fallo mas abajo, con un mensaje que hablaba de otra cosa. Esta
    tanda fallo dos veces de forma intermitente y no quedo
    registro de cual espera se habia vencido; con esto, la proxima vez se sabe.
    """
    fin = [False]
    QTimer.singleShot(int(segundos * 1000), lambda: fin.__setitem__(0, True))
    while not condicion() and not fin[0]:
        app.processEvents()
    if not condicion():
        import traceback
        quien = traceback.extract_stack()[-2]
        print(f"         (espera vencida tras {segundos}s en "
              f"{quien.name}:{quien.lineno})", file=sys.stderr)
        return False
    return True


def test_el_hilo_no_toca_la_ventana(fallos, app):
    """Todo lo que vuelve del mouse llega por señales, en el hilo de la UI."""
    import threading
    hw = Hardware(device=_MouseFalso())
    hilo_de_la_ui = threading.get_ident()
    visto = {"estado": None, "hilo": None}

    def al_estado(e):
        visto["estado"] = e
        visto["hilo"] = threading.get_ident()

    hw.estado.connect(al_estado)
    hw.conectar()
    hw.leer_estado()
    if not _correr_hasta(app, lambda: visto["estado"] is not None):
        fallos.append("no llego el estado del mouse")
    elif visto["hilo"] != hilo_de_la_ui:
        fallos.append("la señal llego en otro hilo: los widgets solo se tocan "
                      "desde el de la ventana")
    elif not visto["estado"].get("comandos"):
        fallos.append("el estado llego vacio")
    hw.cerrar()


def test_una_escritura_pasa_por_la_etapa_3(fallos, app):
    """Escribir desde la ventana no afloja nada: es `sesion.aplicar()`."""
    mouse = _MouseFalso()
    hw = Hardware(device=mouse)
    visto = {"res": None, "avisos": []}
    hw.escritura_lista.connect(lambda r: visto.__setitem__("res", r))
    hw.progreso.connect(visto["avisos"].append)
    hw.conectar()
    hw.escribir("tasa", 500)
    if not _correr_hasta(app, lambda: visto["res"] is not None):
        fallos.append("la escritura no termino")
        hw.cerrar()
        return
    r = visto["res"]
    if not r.ok:
        fallos.append(f"la escritura dio {r.motivo!r}")
    if len(mouse.escrituras) != 1:
        fallos.append(f"mando {len(mouse.escrituras)} escrituras, no 1")
    # el respaldo completo se sigue exigiendo: es el paso 1 de la Etapa 3
    junto = " ".join(visto["avisos"])
    if "respaldando" not in junto:
        fallos.append("no aviso que estaba respaldando: el paso 1 tiene que "
                      "verse en la barra de estado")
    hw.cerrar()


def test_un_respaldo_incompleto_no_escribe(fallos, app):
    """La baranda del paso 1 vale igual desde la ventana.

    **Los 25 s no sobran.** Con tres comandos caidos el respaldo tarda 15,0 s
    MEDIDOS -dos pasadas, con el respiro de 3 s entre comando y comando- y esta
    prueba esperaba 8: la espera se vencia en **todas** las corridas, `res`
    quedaba en None y el `if` de abajo no llegaba a correr nunca. Pasaba por la
    otra comprobacion, que es la de "no escribio", asi que el verde era cierto
    pero a medias. Lo destapo el aviso de espera vencida de `_correr_hasta`.
    """
    mouse = _MouseFalso(completo=False)
    hw = Hardware(device=mouse)
    visto = {"res": None}
    hw.escritura_lista.connect(lambda r: visto.__setitem__("res", r))
    hw.conectar()
    hw.escribir("tasa", 500)
    llego = _correr_hasta(app, lambda: visto["res"] is not None, segundos=25)
    if mouse.escrituras:
        fallos.append("ESCRIBIO con el respaldo incompleto")
    if not llego:
        fallos.append("la escritura no termino: sin el resultado no se puede "
                      "comprobar que se haya negado por el motivo correcto")
    elif visto["res"].ok:
        fallos.append("dio por buena una escritura sin respaldo")
    elif visto["res"].motivo != "respaldo-incompleto":
        fallos.append(f"se nego por {visto['res'].motivo!r}, no por el "
                      "respaldo incompleto")
    hw.cerrar()


def test_los_problemas_traen_su_arreglo(fallos, app):
    """G-05: la ventana tiene que poder ofrecer el comando, no un texto."""
    from linshark.hidraw import COMANDO_UDEV, FaltaLaReglaDeUdev

    hw = Hardware()
    visto = {}
    hw.problema.connect(lambda m, c: visto.update(mensaje=m, comando=c))
    hw.conectar()

    async def revienta():
        raise FaltaLaReglaDeUdev("sin permiso sobre /dev/hidraw2",
                                 path="/dev/hidraw2")

    hw._pedir(revienta())
    if not _correr_hasta(app, lambda: "comando" in visto, segundos=8):
        fallos.append("no llego el problema")
    elif visto["comando"] != COMANDO_UDEV:
        fallos.append(f"el problema no trajo el arreglo: {visto!r}")
    hw.cerrar()


def test_un_error_no_mata_el_hilo(fallos, app):
    """Si una corrida revienta, la siguiente tiene que andar igual."""
    hw = Hardware(device=_MouseFalso())
    visto = {"problemas": 0, "estado": None}
    hw.problema.connect(lambda m, c: visto.__setitem__("problemas",
                                                       visto["problemas"] + 1))
    hw.estado.connect(lambda e: visto.__setitem__("estado", e))
    hw.conectar()

    async def revienta():
        raise RuntimeError("a proposito")

    # el traceback de este error es esperado: se calla para que no parezca un
    # problema de la corrida
    import logging
    logging.getLogger("linshark_ui.hardware").setLevel(logging.CRITICAL)
    hw._pedir(revienta())
    _correr_hasta(app, lambda: visto["problemas"] > 0, segundos=8)
    hw.leer_estado()
    if not _correr_hasta(app, lambda: visto["estado"] is not None):
        fallos.append("despues de un error el hilo dejo de responder")
    hw.cerrar()


def test_cerrar_espera_a_lo_que_esta_en_vuelo(fallos, app):
    """Cortar una escritura a la mitad puede dejar medio bloque en el mouse.

    El camino multi-trama de cmd 9 manda dos tramas con 1.008 s en el medio.
    Si cerrar la ventana matara la tarea, el mouse se quedaria con medio macro
    —el mismo riesgo que el CLI anuncia como "no desenchufes el dongle ahi"—.
    """
    import asyncio

    hw = Hardware(device=_MouseFalso())
    hw.conectar()
    estado = {"arranco": False, "termino": False}

    async def lenta():
        estado["arranco"] = True
        await asyncio.sleep(1.0)
        estado["termino"] = True

    hw._pedir(lenta())
    if not _correr_hasta(app, lambda: estado["arranco"], segundos=5):
        fallos.append("la tarea no arranco")
        hw.cerrar()
        return
    hw.cerrar()                       # esto tiene que esperarla, no matarla
    if not estado["termino"]:
        fallos.append("cerrar corto una operacion en vuelo: con una escritura "
                      "de macro eso deja medio bloque en el mouse")


def test_cerrar_no_espera_para_siempre(fallos, app):
    """Pero tampoco cuelga la ventana: se corta, y se dice."""
    import asyncio
    import logging

    hw = Hardware(device=_MouseFalso())
    hw.conectar()
    avisos = []
    hw.problema.connect(lambda m, c: avisos.append(m))
    arranco = {"si": False}

    async def eterna():
        arranco["si"] = True
        await asyncio.sleep(3600)

    logging.getLogger("linshark_ui.hardware").setLevel(logging.CRITICAL)
    hw._pedir(eterna())
    _correr_hasta(app, lambda: arranco["si"], segundos=5)
    hw.cerrar(espera=0.5)
    # `cerrar()` bloquea el hilo de la ventana mientras espera, asi que la
    # señal queda encolada: hay que dejar que Qt la entregue.
    _correr_hasta(app, lambda: bool(avisos), segundos=5)
    if not any("no terminaron a tiempo" in a for a in avisos):
        fallos.append("corto una operacion sin decirlo: el que mira tiene que "
                      f"enterarse de que algo quedo a medias ({avisos})")


def test_las_novedades_llegan(fallos, app):
    """G-03: bateria y cambio de nivel de dpi, que el mouse avisa solo."""
    mouse = _MouseFalso()
    hw = Hardware(device=mouse)
    visto = []
    hw.novedad.connect(visto.append)
    hw.conectar()
    hw.leer_estado()
    _correr_hasta(app, lambda: mouse.lecturas > 0, segundos=8)
    # el mouse falso no late solo: se simula el reporte que llegaria
    mouse.on_estado_mouse(bytes.fromhex("08400150"))
    if not _correr_hasta(app, lambda: bool(visto), segundos=5):
        fallos.append("no llego la novedad de bateria")
    elif visto[0].bateria != 80:
        fallos.append(f"la bateria llego mal: {visto[0]}")
    hw.cerrar()


def test_un_mouse_que_no_es_el_medido_se_avisa(fallos, app):
    """Todo lo medido es de un X8 Pro. Otro modelo tiene que decirse.

    Antes el codigo le hablaba a cualquier mouse que contestara
    asumiendo que era este: los tamaños de bloque, los dieciocho slots y la
    permutacion de los slots 4, 5 y 6 estan medidos contra uno solo. El device
    id llega en el Report ID 3, que es la primera oportunidad de notarlo.
    """
    import logging

    from linshark import protocol as prot

    logging.getLogger("linshark_ui.hardware").setLevel(logging.CRITICAL)

    # 1. el que si conocemos no molesta a nadie
    hw = Hardware(device=_MouseFalso())
    visto = {"modelo": None, "problemas": []}
    hw.modelo_detectado.connect(
        lambda i, n: visto.__setitem__("modelo", (i, n)))
    hw.problema.connect(lambda m, c: visto["problemas"].append(m))
    hw.conectar()
    hw.leer_estado()
    _correr_hasta(app, lambda: hw._device is not None, segundos=8)
    hw._al_haber_novedad(sesion.novedad_de(
        bytes([prot.DEVICE_X8_PRO, 0x40, 1, 100])))
    _correr_hasta(app, lambda: visto["modelo"] is not None, segundos=5)
    if visto["modelo"] != (prot.DEVICE_X8_PRO, "X8 Pro"):
        fallos.append(f"no reconocio al X8 Pro: {visto['modelo']}")
    if visto["problemas"]:
        fallos.append(f"protesto por el mouse medido: {visto['problemas']}")
    # **Y le habla con ese perfil.** Detectar el modelo y no activarlo dejaba
    # la deteccion a medias: hoy no se nota porque solo hay un perfil medido y
    # ya era el activo, y el dia que haya dos se notaria decodificando con los
    # offsets del mouse equivocado. Lo marco una auditoria externa.
    from linshark import dispositivos
    from linshark.perfiles.x8pro import X8_PRO
    if dispositivos.activo() is not X8_PRO:
        fallos.append("reconocio al X8 Pro y no le puso su perfil: "
                      f"quedo {dispositivos.activo().nombre}")
    hw.cerrar()

    # 2. **uno del catalogo que nadie midio tiene que avisar**, con el nombre
    hw = Hardware(device=_MouseFalso())
    visto = {"modelo": None, "problemas": []}
    hw.modelo_detectado.connect(
        lambda i, n: visto.__setitem__("modelo", (i, n)))
    hw.problema.connect(lambda m, c: visto["problemas"].append(m))
    hw.conectar()
    hw.leer_estado()
    _correr_hasta(app, lambda: hw._device is not None, segundos=8)
    hw._al_haber_novedad(sesion.novedad_de(bytes([133, 0x40, 1, 100])))  # X6
    _correr_hasta(app, lambda: bool(visto["problemas"]), segundos=5)
    if not visto["problemas"]:
        fallos.append("un modelo que nadie midio no aviso nada: le estariamos "
                      "escribiendo offsets de otro mouse")
    elif "X6" not in visto["problemas"][0]:
        fallos.append(f"el aviso no dice que modelo es: {visto['problemas'][0][:80]}")
    if visto["modelo"] != (133, "X6"):
        fallos.append(f"no informo el modelo detectado: {visto['modelo']}")
    # Y **no le pone ningun perfil**: de ese mouse no hay nada medido, y
    # activar el del X8 Pro seria justo lo que el aviso dice que no se haga.
    if dispositivos.activo() is not X8_PRO:
        fallos.append("con un modelo sin medir cambio el perfil activo a "
                      f"{dispositivos.activo().nombre}")
    hw.cerrar()


def test_los_avisos_se_dicen_en_castellano(fallos, app):
    """Las claves de `sesion` se traducen; nada de strings sueltos.

    **Se recorren todas las constantes `AVISO_*`, no una lista escrita a mano.**
    Antes la lista era a mano, y al agregar tres avisos nuevos
    -el respaldo traido, la relectura acotada y el cache viejo- el test siguio
    verde sin mirarlos: una clave cruda como `relectura-acotada` habria salido
    tal cual a la barra de estado y nadie se habria enterado.
    """
    for espera, clave in (("respald", sesion.AVISO_RESPALDO),
                          ("reley", sesion.AVISO_RELECTURA),
                          ("acus", sesion.AVISO_ACUSE),
                          ("sin acuse", sesion.AVISO_SIN_ACUSE)):
        if espera not in _legible(clave).lower():
            fallos.append(f"el aviso {clave!r} no se tradujo: {_legible(clave)!r}")

    # y **ninguna** clave puede salir cruda, ni sola ni con texto detras
    for nombre in dir(sesion):
        if not nombre.startswith("AVISO_"):
            continue
        clave = getattr(sesion, nombre)
        if _legible(clave) == clave:
            fallos.append(f"{nombre} sale crudo a la pantalla: {clave!r}")
        con_texto = _legible(f"{clave}|el mouse esta a 8000 Hz")
        if "|" in con_texto:
            fallos.append(f"{nombre} con texto detras no se partio: "
                          f"{con_texto!r}")


# --- la ventana, que antes no existia -----------------------
#
# Lo que sigue prueba widgets, asi que necesita `QApplication` y una plataforma
# sin pantalla (`offscreen`, arriba). Nada de esto abre una ventana ni toca un
# mouse: el estado sale de `_MouseFalso` como el resto del archivo.


def _estado_falso(macros_extra=(17,)) -> dict:
    """El estado entero del mouse de mentira, leido de una."""
    import asyncio
    return asyncio.run(sesion.leer_estado(_MouseFalso(), nodo="/dev/falso",
                                          macros_extra=macros_extra))


def _nombres_de_prueba():
    """Nombres de macro en un archivo temporal, nunca en el HOME de nadie."""
    import tempfile
    from linshark.nombres import NombresDeMacro
    return NombresDeMacro(Path(tempfile.mkdtemp()) / "macros.json")


def test_la_pantalla_se_arma_sola(fallos, app):
    """Un control por campo, elegido por las propiedades del `Campo`."""
    from linshark import modelo
    from linshark_ui import controles
    from linshark_ui.paneles.parametros import PanelDeParametros

    estado = _estado_falso()
    panel = PanelDeParametros()
    panel.poner_estado(estado)
    campos = modelo.campos_de(estado)
    if len(panel.filas()) != len(campos):
        fallos.append(f"dibujo {len(panel.filas())} filas para "
                      f"{len(campos)} campos")

    # Y cada uno cayo en el control que le corresponde **por su forma**, no
    # por su nombre: opciones -> desplegable, rango -> deslizador, dos
    # booleanos -> interruptor, `#rrggbb` -> color.
    esperado = {
        "tasa": controles.EditorDeOpciones,
        "dpi_nivel_1": controles.EditorNumerico,
        "reposo": controles.EditorNumerico,
        "ripple": controles.EditorBooleano,
        "boton_dpi": controles.EditorDeOpciones,
        "rueda": controles.EditorDeOpciones,
    }
    for clave, clase in esperado.items():
        fila = panel.filas().get(clave)
        if fila is None:
            fallos.append(f"falta la fila de {clave}")
        elif not isinstance(fila.editor, clase):
            fallos.append(f"{clave} salio {type(fila.editor).__name__}, "
                          f"esperaba {clase.__name__}")

    # **El selector de color sigue en la fabrica aunque este mouse no lo use.**
    # Desde el X8 Pro no ofrece ningun campo `#rrggbb`: el RGB
    # del cmd 5 no enciende nada aca -por eso "color" figura en
    # `Perfil.campos_ausentes`- y los colores
    # del indicador van de marca en la fila del nivel. Otro modelo puede tener
    # RGB de verdad, y entonces la eleccion por forma tiene que seguir dando el
    # control correcto, sin que nadie toque la ventana.
    de_otro_mouse = modelo.Campo("rgb", "luz del chasis", "#00ff00",
                                 p.CMD_LIGHTING, escribible=True)
    if not isinstance(controles.editor_para(de_otro_mouse),
                      controles.EditorDeColor):
        fallos.append("un campo que se ve como color no cae en el selector "
                      "de color")

    # El deslizador del reposo tiene que moverse de a medio minuto: el byte
    # son medios minutos y el paso sale del propio rango (0.5..30).
    fila = panel.filas()["reposo"]
    if controles.paso_de(fila.campo) != 0.5:
        fallos.append(f"el paso del reposo salio {controles.paso_de(fila.campo)}")

    # Leer dos veces no duplica nada: refresca.
    panel.poner_estado(estado)
    if len(panel.filas()) != len(campos):
        fallos.append("releer duplico filas")

    # **Y todo eso tiene que quedar a la vista.** Este chequeo entro despues de
    # que la pantalla saliera en blanco con las treinta y dos filas armadas
    # adentro: el panel decidia que grupos mostrar preguntando `isVisible()` a
    # las filas, que es falso mientras la ventana no se mostro, asi que los
    # escondia todos. Construir no es mostrar, y la diferencia no se veia.
    escondidas = [c for c, fila in panel.filas().items() if not se_ve(fila)]
    if escondidas:
        fallos.append(f"estas filas quedaron escondidas: {escondidas}")
    from PySide6.QtWidgets import QGroupBox
    ocultos = [g.title() for g in panel.findChildren(QGroupBox)
               if not se_ve(g)]
    if ocultos:
        fallos.append(f"estos grupos quedaron escondidos: {ocultos}")
    if not panel.findChildren(QGroupBox):
        fallos.append("no agrupo los campos por comando")


def test_cada_nivel_de_dpi_se_ve_de_su_color(fallos, app):
    """La fila lleva la marca del LED, y solo los niveles que existen.

    Son las dos mitades de lo mismo: el color del indicador es informacion
    **del nivel**, no una fila aparte al final de la lista, y un nivel que el
    mouse no tiene cargado no tiene indicador que mostrar. El X8 Pro trae ocho
    slots y usa seis; antes la pantalla mostraba ocho filas de
    "color del indicador", dos de ellas de un LED que no se prende nunca.

    **Nada de esto lo sabe la ventana**: pinta `campo.color` si viene y deja
    el hueco vacio si no.
    """
    from linshark import modelo
    from linshark_ui import controles
    from linshark_ui.paneles.parametros import PanelDeParametros

    estado = _estado_falso()
    panel = PanelDeParametros()
    panel.poner_estado(estado)
    filas = panel.filas()
    campos = modelo.por_clave(estado)

    niveles = {int(k.rsplit("_", 1)[1]) for k in filas
               if k.startswith("dpi_nivel_")}
    if not niveles:
        fallos.append("no dibujo ningun nivel de dpi")
    # Ninguna fila suelta de color: el dato va pegado al nivel.
    sueltas = [k for k in filas if k.startswith("color_nivel_")]
    if sueltas:
        fallos.append(f"quedaron filas de color sueltas: {sorted(sueltas)}")

    for i in sorted(niveles):
        fila = filas[f"dpi_nivel_{i}"]
        color = campos[f"dpi_nivel_{i}"].color
        if color is None:
            fallos.append(f"el nivel {i} no trae su color")
            continue
        if color.hexa.lower() not in fila.marca.styleSheet().lower():
            fallos.append(f"el nivel {i} no se marca con su color "
                          f"({color.hexa}): {fila.marca.styleSheet()!r}")
        if not se_ve(fila.marca):
            fallos.append(f"la marca del nivel {i} quedo escondida")
        # y la marca dice que color es: no lo dice la
        # ayuda, que explica el parametro
        if color.nombre and color.nombre not in fila.marca.toolTip():
            fallos.append(f"la marca del nivel {i} no nombra el color "
                          f"({color.nombre!r}): {fila.marca.toolTip()!r}")

    # Un campo sin color propio no dibuja una pastilla al lado del nombre,
    # pero sigue ocupando el hueco: si no, su nombre no alinea con los otros.
    sin_color = next(f for f in filas.values() if f.campo.color is None)
    if "transparent" not in sin_color.marca.styleSheet():
        fallos.append(f"{sin_color.campo.clave} pinto una marca sin tener "
                      f"color: {sin_color.marca.styleSheet()!r}")
    if not se_ve(sin_color.marca):
        fallos.append("la marca vacia se escondio: los nombres se corren")

    # Y el nivel en uso lleva el color que el LED tiene prendido ahora.
    activo = campos["nivel_activo"]
    esperado = campos[f"dpi_nivel_{activo.valor}"].color
    if activo.color != esperado:
        fallos.append("el nivel en uso no lleva el color que tiene prendido")


def test_el_rgb_que_no_enciende_nada_no_se_ofrece(fallos, app):
    """El color del cmd 5 no esta, y **no porque la ventana lo esconda**.

    En el X8 Pro esos bytes se escriben, el mouse acusa `0xC1` y la relectura
    los devuelve cambiados, y el chasis no prende nada (MEDIDO,
    `dev/models/attackshark-x8pro/docs/evidencia.md`). Un control que mueve bytes y no cambia nada es el
    reproche que este proyecto le hace al cliente oficial, asi que el modelo no
    lo ofrece: "color" figura en `dispositivos.Perfil.campos_ausentes`, con el
    motivo medido al lado.

    Lo que **no** cambia: seguir pudiendo escribirlo. I-W16 sigue abierto
    -todo lo observado fue con `lightMode: 0`- y el dia que se cierre al reves
    el control tiene que volver sacando esa clave del perfil, sin tocar la
    ventana.
    """
    from linshark import dispositivos
    from linshark import modelo
    from linshark import sesion
    from linshark_ui import controles
    from linshark_ui.paneles.parametros import PanelDeParametros

    if "color" not in dispositivos.activo().campos_ausentes:
        fallos.append("el perfil dejo de decir que el RGB del cmd 5 no "
                      "enciende nada en este mouse, y no se midio que si")

    panel = PanelDeParametros()
    panel.poner_estado(_estado_falso())
    de_color = [c for c, f in panel.filas().items()
                if controles.parece_color(f.campo.valor)]
    if de_color:
        fallos.append(f"quedaron campos de color en pantalla: {de_color}")

    # La capacidad sigue: el CLI y `preparar_mutacion` no se tocaron.
    try:
        sesion.preparar_mutacion("color", "#00ff00")
    except Exception as exc:                       # noqa: BLE001
        fallos.append(f"escribir el color dejo de andar por la biblioteca: "
                      f"{type(exc).__name__}: {exc}")


def test_la_rueda_no_cambia_un_desplegable(fallos, app):
    """Scrollear el panel no puede remapear un boton sin que nadie lo elija.

    El panel es una lista larga dentro de un `QScrollArea` y un `QComboBox` se
    come la rueda que le pasa por encima. Aca cada opcion de un desplegable es
    **una escritura al mouse**: bajar la pantalla con el puntero sobre el boton
    derecho lo dejaba en otra funcion.

    Los deslizadores y los numeritos siguen aceptandola a proposito: ahi el
    valor se ve cambiar mientras gira y no se escribe hasta soltar.
    """
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication
    from linshark_ui.paneles.parametros import PanelDeParametros

    panel = PanelDeParametros()
    panel.poner_estado(_estado_falso())
    pedidos = []
    panel.pidio_escribir.connect(lambda c, v: pedidos.append((c, v)))

    def rueda(widget, pasos=-1):
        ev = QWheelEvent(QPointF(5, 5), widget.mapToGlobal(QPointF(5, 5)),
                         QPoint(0, pasos * 120), QPoint(0, pasos * 120),
                         Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        QApplication.sendEvent(widget, ev)
        return ev

    # --- un desplegable: ni cambia, ni acepta el evento ------------------
    fila = panel.filas()["boton_derecho"]
    antes = fila.editor.lista.currentIndex()
    ev = rueda(fila.editor.lista)
    if fila.editor.lista.currentIndex() != antes:
        fallos.append("la rueda le cambio la opcion a un desplegable")
    if ev.isAccepted():
        fallos.append("el desplegable se quedo con la rueda: el panel no "
                      "puede scrollear por encima de un desplegable")
    if pedidos:
        fallos.append(f"la rueda pidio una escritura: {pedidos}")

    # y el desplegable no roba el foco al pasarle la rueda por arriba
    if panel.filas()["tasa"].editor.lista.focusPolicy() == Qt.WheelFocus:
        fallos.append("el desplegable toma el foco con la rueda, y despues "
                      "las flechas le cambian el valor")

    # --- una barra y un numerito: la rueda sigue andando -----------------
    numerico = panel.filas()["dpi_nivel_1"].editor
    antes = numerico.numero.value()
    rueda(numerico.deslizador, pasos=1)
    rueda(numerico.numero, pasos=1)
    if numerico.numero.value() == antes and numerico.deslizador.value() == 0:
        fallos.append("la rueda dejo de mover el deslizador y el numerito, "
                      "que es donde se pidio que siguiera andando")


def test_el_esquema_de_botones(fallos, app):
    """El diagrama de botones se muestra sobre el grupo de botones y resalta filas."""
    from linshark_ui.diagrama import DiagramaDeBotones
    from linshark_ui.paneles.parametros import PanelDeParametros

    estado = _estado_falso()
    panel = PanelDeParametros()
    panel.poner_estado(estado)

    diag = panel.diagrama()
    if diag is None:
        fallos.append("el panel no construyó el diagrama de botones")
        return
    if not se_ve(diag):
        fallos.append("el diagrama de botones quedó oculto")

    # El esquema va arriba del grupo de botones
    items = panel.contenido_de(p.CMD_BUTTONS)
    if not items or items[0] is not diag:
        fallos.append("el diagrama no es el primer widget del grupo de botones")

    # Tiene dos vistas (_Dibujo)
    # Tres vistas, una por cara: cada boton en la cara donde esta, y ninguno
    # dibujado dos veces.
    dibujos = diag.dibujos()
    esperado = ((1, 2, 3), (4, 5), (6, 7))
    if tuple(d.slots() for d in dibujos) != esperado:
        fallos.append(f"las vistas dibujan {[d.slots() for d in dibujos]}, "
                      f"esperaba {list(esperado)}")
    # `6 [] 7`: el dpi y el modo a los dos lados del sensor y a su altura
    abajo = next((d for d in dibujos if 6 in d.slots()), None)
    if abajo is not None:
        (x6, y6), (x7, y7) = (abajo.vista.posiciones[6],
                              abajo.vista.posiciones[7])
        if not (y6 == y7 and x6 < abajo.vista.ancho / 2 < x7):
            fallos.append(f"el 6 y el 7 no quedaron a los costados del sensor: "
                          f"{(x6, y6)} y {(x7, y7)}")
    # cada numero se puede tocar donde se ve
    for d in dibujos:
        d.resize(d.size())
        for slot in d.slots():
            punto = d.punto_de(slot)
            if d.slot_en(punto) != slot:
                fallos.append(f"el numero {slot} se dibuja en {punto} pero "
                              f"ahi el click cae en {d.slot_en(punto)}")

    # Plegar y desplegar
    diag.plegar.setChecked(False)
    if se_ve(diag.cuerpo):
        fallos.append("el cuerpo del diagrama sigue visible tras plegarlo")
    if "▸" not in diag.plegar.text():
        fallos.append(f"el botón de plegar no cambió a flecha cerrada: {diag.plegar.text()!r}")
    diag.plegar.setChecked(True)
    if not se_ve(diag.cuerpo):
        fallos.append("el cuerpo del diagrama no se mostró tras desplegarlo")

    # Tocar un número resalta la fila
    fila_atras = panel.filas()["boton_costado_atras"]
    diag._al_tocar(4)
    if fila_atras.property("destacada") != "true":
        fallos.append("al tocar el slot 4 no se destacó la fila de botón atrás")

    # Ayuda del diagrama
    diag.mostrar_ayuda()
    popup = diag.popup()
    if popup is None or not se_ve(popup):
        fallos.append("la ayuda del diagrama no se abrió")


def test_restaurar_escribe_solo_lo_que_hace_falta(fallos, app):
    """Los dos botones, y la baranda que los hace baratos.

    **Un campo que ya esta en su valor no se reescribe.** Cada escritura son
    varios segundos de Etapa 3 sobre un enlace que pierde la mitad de los
    pedidos con el mouse quieto: mandar veintipico para no mover nada seria
    gastar el enlace y el tiempo de quien mira.
    """
    from linshark import modelo
    from linshark_ui.ventana import DialogoDeRestauracion

    estado = _estado_falso()

    # 1. Contra su propio estado no hay nada que escribir.
    propio = {c.clave: c.valor for c in modelo.campos_de(estado)
              if c.escribible}
    if modelo.pendientes(estado, propio):
        fallos.append(f"restaurar al estado actual escribiria "
                      f"{modelo.pendientes(estado, propio)}")

    # El mouse falso arranca **justo** en los valores seguros, asi que para
    # probar una restauracion de verdad hace falta un destino que difiera. Se
    # arma moviendo cada interruptor a su otra opcion y la tasa a otra de las
    # que el propio campo declara: ni un valor inventado.
    destino = dict(propio)
    for campo in modelo.campos_de(estado):
        if campo.escribible and set(campo.opciones) == {False, True}:
            destino[campo.clave] = not campo.valor
    destino["tasa"] = next(hz for hz in sorted(p.RATE_INDICE)
                           if hz != propio["tasa"])

    # 2. Lo que devuelve tiene que ser escribible **de verdad**, campo por
    #    campo, por la misma puerta que usa el CLI.
    cambios = modelo.pendientes(estado, destino)
    if len(cambios) < 2:
        fallos.append(f"el destino de prueba no mueve casi nada ({cambios}): "
                      "este test no probaria el orden")
    for clave, _, a in cambios:
        try:
            sesion.preparar_mutacion(clave, a)
        except Exception as exc:                   # noqa: BLE001
            fallos.append(f"restaurar pediria {clave}={a!r}, que la "
                          f"biblioteca rechaza: {type(exc).__name__}: {exc}")

    # 3. **La tasa va ultima.** Cambiarla en el medio deja la rafaga escribiendo
    #    a una tasa distinta de la que la sesion presto, y arriba de 1000 Hz las
    #    que siguen no pueden releer.
    claves = [c for c, _, _ in cambios]
    if "tasa" in claves and claves[-1] != "tasa":
        fallos.append(f"la tasa no quedo ultima: {claves}")

    # 4. Ningun macro se toca, con ninguno de los dos botones.
    de_macro = [c for c in set(modelo.DE_FABRICA) | set(modelo.SEGUROS)
                if c in sesion.CLAVES_DE_MACRO]
    if de_macro:
        fallos.append(f"la tabla de restauracion toca macros: {de_macro}")

    # 5. Sin nada que cambiar, el dialogo no ofrece escribir.
    vacio = DialogoDeRestauracion([], "x", "")
    if hasattr(vacio, "aplicar"):
        fallos.append("con cero cambios igual ofrece aplicar")
    # y con cambios, dice cuantos y cuales
    dialogo = DialogoDeRestauracion(cambios, "x", "")
    if not hasattr(dialogo, "aplicar"):
        fallos.append("con cambios no ofrece aplicar")
    else:
        texto = dialogo.lista.toPlainText()
        for clave, de, a in cambios:
            if clave not in texto or str(a) not in texto:
                fallos.append(f"el dialogo no dice que va a mover {clave}")
                break


def test_la_ventana_no_conoce_ningun_campo(fallos, app):
    """La baranda de fondo: **nada de `if clave == "lod"`**.

    Es lo unico que vuelve mono-mouse a la ventana. Se verifica sobre el
    **arbol** del codigo y no sobre su texto, por dos motivos: un comentario o
    un docstring que explique la regla no puede hacerla fallar -este archivo
    mismo la nombra-, y `"color"` adentro de una hoja de estilo no es el campo
    `color`.

    Dos cosas se prohiben: que una clave de `campos_de()` aparezca como
    literal, y que se compare `clave` contra literales. `clave in vistos`
    -contra una variable- sigue valiendo: eso no sabe de ningun campo.
    """
    import ast

    from linshark import modelo

    claves = {c.clave for c in modelo.campos_de(_estado_falso())}
    fuentes = sorted((RAIZ / "src" / "linshark_ui").rglob("*.py"))
    if not fuentes:
        fallos.append("no encontre el codigo de la ventana")

    def es_literal(nodo) -> bool:
        if isinstance(nodo, ast.Constant):
            return True
        return (isinstance(nodo, (ast.Tuple, ast.List, ast.Set))
                and all(isinstance(x, ast.Constant) for x in nodo.elts))

    for fuente in fuentes:
        arbol = ast.parse(fuente.read_text(encoding="utf-8"))
        # los docstrings y las cadenas sueltas quedan afuera: son prosa
        prosa = {id(n.value) for n in ast.walk(arbol)
                 if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                 and isinstance(n.value.value, str)}
        for nodo in ast.walk(arbol):
            if (isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)
                    and nodo.value in claves and id(nodo) not in prosa):
                fallos.append(
                    f"{fuente.name}:{nodo.lineno} nombra el campo "
                    f"{nodo.value!r}: la ventana dejo de ser data-driven")
            if isinstance(nodo, ast.Compare):
                izq = nodo.left
                nombre = (izq.attr if isinstance(izq, ast.Attribute)
                          else izq.id if isinstance(izq, ast.Name) else "")
                if nombre == "clave" and any(es_literal(c)
                                             for c in nodo.comparators):
                    fallos.append(
                        f"{fuente.name}:{nodo.lineno} compara `clave` contra "
                        "un literal: eso es un campo conocido por nombre")


def test_mover_un_control_pide_esa_escritura(fallos, app):
    """Tocar un widget manda `(clave, valor)`, y nada mas."""
    from linshark_ui.paneles.parametros import PanelDeParametros

    panel = PanelDeParametros()
    panel.poner_estado(_estado_falso())
    pedidos = []
    panel.pidio_escribir.connect(lambda c, v: pedidos.append((c, v)))
    filas = panel.filas()

    filas["tasa"].editor.elegir(500)
    filas["ripple"].editor.casilla.setChecked(False)
    filas["dpi_nivel_1"].editor.poner_valor(1600)
    filas["lod"].editor.elegir(2)
    filas["rueda"].editor.elegir("invertido")

    espera = [("tasa", 500), ("ripple", False), ("dpi_nivel_1", 1600),
              ("lod", 2), ("rueda", "invertido")]
    if pedidos != espera:
        fallos.append(f"pidio {pedidos}, esperaba {espera}")

    # **Poner el valor que ya esta no escribe.** Una escritura son varios
    # segundos de Etapa 3: gastarlos en una idempotente que nadie pidio es
    # gastar el enlace y el tiempo de quien mira.
    pedidos.clear()
    filas["dpi_nivel_1"].editor.poner_valor(filas["dpi_nivel_1"].campo.valor)
    filas["ripple"].editor.casilla.setChecked(bool(filas["ripple"].campo.valor))
    if pedidos:
        fallos.append(f"escribio el valor que ya tenia: {pedidos}")


def test_una_funcion_con_parametro_pide_el_parametro(fallos, app):
    """"macro" a secas no alcanza: el slot lleva el id adentro.

    Y quien dice que falta es la biblioteca (`sesion.FaltaElParametro`), no la
    ventana: asi el desplegable de botones anda sin saber que existe un codigo
    18.
    """
    from linshark_ui.paneles.parametros import PanelDeParametros

    panel = PanelDeParametros()
    panel.poner_estado(_estado_falso())
    pedidos = []
    panel.pidio_escribir.connect(lambda c, v: pedidos.append((c, v)))
    editor = panel.filas()["boton_costado_adelante"].editor

    editor.elegir("macro")
    if pedidos:
        fallos.append(f"escribio un macro sin id: {pedidos}")
    if not se_ve(editor.parametro):
        fallos.append("no pidio el id del macro")
    elif "id del macro" not in editor.parametro.placeholderText():
        fallos.append(f"el campito no dice que pide: "
                      f"{editor.parametro.placeholderText()!r}")
    editor.parametro.setText("17")
    editor._al_poner_parametro()
    if pedidos != [("boton_costado_adelante", ("macro", "17"))]:
        fallos.append(f"con el id puesto pidio {pedidos}")
    # y lo que salga de ahi tiene que ser escribible de verdad
    try:
        sesion.preparar_mutacion(*pedidos[0])
    except Exception as exc:                       # noqa: BLE001
        fallos.append(f"lo que armo no se puede escribir: {exc}")

    # Una funcion sin parametro se manda derecho.
    pedidos.clear()
    editor.elegir("atras")
    if pedidos != [("boton_costado_adelante", "atras")]:
        fallos.append(f"una funcion simple pidio {pedidos}")


def test_las_funciones_se_buscan_y_se_agrupan(fallos, app):
    """Las funciones de un boton se eligen escribiendo o por grupo.

    Son mas de cincuenta, y en una lista sola "subir el volumen" era
    recorrerla entera. Lo que se prueba: que los grupos salen del modelo y no
    pierden ninguna opcion, que buscar no distingue tildes ni mayusculas, que
    el Enter elige y la eleccion va por el mismo camino que un click -con el
    campito del parametro para el macro-, y que el teclado sobre el
    desplegable abre el buscador **en vez de escribir la opcion de al lado**.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from linshark import estructuras as est
    from linshark import modelo
    from linshark_ui import controles, i18n
    from linshark_ui.paneles.parametros import PanelDeParametros

    # --- el modelo: cada opcion en un grupo, y en uno solo -----------------
    estado = _estado_falso()
    for campo in modelo.campos_de(estado):
        if campo.slot is None:
            if campo.grupos:
                fallos.append(f"{campo.clave} trae grupos y no es un boton")
            continue
        repartidas = [o for _, opciones in campo.grupos for o in opciones]
        if sorted(repartidas) != sorted(campo.opciones):
            faltan = set(campo.opciones) - set(repartidas)
            fallos.append(f"{campo.clave}: los grupos no cubren las opciones "
                          f"(faltan {sorted(faltan)[:5]}, "
                          f"repetidas {len(repartidas) - len(set(repartidas))})")
        if any(not opciones for _, opciones in campo.grupos):
            fallos.append(f"{campo.clave} tiene un grupo vacio")
    # una funcion que nadie agrupo no se pierde: cae en el ultimo grupo
    grupos = dict(modelo.grupos_de_funciones(["apagado", "una que no existe"]))
    if "una que no existe" not in grupos.get(modelo.GRUPO_DE_LO_DEMAS, ()):
        fallos.append(f"una funcion sin grupo se perdio: {grupos}")

    panel = PanelDeParametros()
    panel.poner_estado(estado)
    pedidos = []
    panel.pidio_escribir.connect(lambda c, v: pedidos.append((c, v)))
    filas = panel.filas()
    for clave in ("tasa", "rueda"):
        if isinstance(filas[clave].editor, controles.EditorDeOpcionesAgrupadas):
            fallos.append(f"{clave} no tiene grupos y salio con buscador")
    fila = filas["boton_costado_adelante"]
    editor = fila.editor
    if not isinstance(editor, controles.EditorDeOpcionesAgrupadas):
        fallos.append(f"un boton salio {type(editor).__name__}, sin buscador")
        return

    # --- se abre en el grupo de lo que el boton tiene ----------------------
    selector = editor.abrir_selector()
    titulos = [selector.categorias.item(i).text()
               for i in range(selector.categorias.count())]
    if titulos != [t for t, _ in fila.campo.grupos]:
        fallos.append(f"los grupos del costado son {titulos}")
    actual = selector.opciones.currentItem()
    if actual is None or actual.data(Qt.UserRole) != fila.campo.valor:
        fallos.append("no abrio marcando lo que el boton tiene: "
                      f"{actual and actual.data(Qt.UserRole)!r}")
    # un boton con su parametro -"macro 17"- abre en el grupo del macro
    con_macro = dataclasses.replace(fila.campo, valor="macro 17")
    selector.poner(con_macro)
    grupo = fila.campo.grupos[selector.categorias.currentRow()]
    if "macro" not in grupo[1]:
        fallos.append(f"un boton en 'macro 17' abrio en {grupo[0]!r}")
    selector.poner(fila.campo)

    # --- buscar ----------------------------------------------------------
    selector.buscar("vol")
    encontradas = selector.encontradas()
    if not {"volumen +", "volumen -"} <= set(encontradas):
        fallos.append(f"'vol' no encontro el volumen: {encontradas}")
    if "silenciar" in encontradas:
        fallos.append("'vol' trajo el grupo entero de la musica, no lo que "
                      "dice volumen")
    selector.buscar("MÚSICA")
    musica = next(o for t, o in fila.campo.grupos if "volumen +" in o)
    if selector.encontradas() != list(musica):
        fallos.append(f"'MÚSICA' no trajo su grupo: {selector.encontradas()}")
    selector.buscar("cancion")
    sin_tilde = selector.encontradas()
    selector.buscar("canción")
    if not sin_tilde or selector.encontradas() != sin_tilde:
        fallos.append("buscar con y sin tilde no encuentra lo mismo")
    selector.buscar("zzzz no existe")
    if selector.encontradas() or not se_ve(selector.sin_resultados):
        fallos.append("una busqueda sin resultados no lo dice")
    if pedidos:
        fallos.append(f"buscar pidio una escritura: {pedidos}")

    # --- elegir: el Enter, el click, y el macro con su parametro -----------
    selector.buscar("subir vol")
    selector.elegir_con_enter()
    if pedidos != [("boton_costado_adelante", "volumen +")]:
        fallos.append(f"el Enter pidio {pedidos}")
    if selector.isVisible():
        fallos.append("el selector quedo abierto despues de elegir")
    pedidos.clear()
    selector = editor.abrir_selector("atras")
    item = selector.resultados.item(1)
    # el click y el activado juntos, como en un escritorio de "un click abre"
    selector.resultados.itemClicked.emit(item)
    selector.resultados.itemActivated.emit(item)
    if len(pedidos) != 1:
        fallos.append(f"un click pidio {len(pedidos)} escrituras: {pedidos}")
    pedidos.clear()
    selector = editor.abrir_selector("macro")
    selector.elegir_con_enter()
    if pedidos:
        fallos.append(f"el macro se escribio sin id: {pedidos}")
    if not se_ve(editor.parametro):
        fallos.append("elegir el macro en el buscador no pidio el id")

    # --- el teclado sobre el desplegable abre el buscador ------------------
    otra = filas["boton_derecho"].editor
    antes = otra.lista.currentIndex()
    for tecla in (Qt.Key_Down, Qt.Key_Up, Qt.Key_End):
        QTest.keyClick(otra.lista, tecla)
    if otra.lista.currentIndex() != antes or pedidos:
        fallos.append("una flecha sobre el desplegable cambio la funcion: "
                      f"{pedidos}")
    QTest.keyClick(otra.lista, Qt.Key_V)
    if otra.selector() is None or otra.selector().buscador.text() != "v":
        fallos.append("escribir sobre el desplegable no abrio el buscador "
                      "con la letra puesta")

    # --- en otro idioma se busca en lo que se lee ------------------------
    try:
        i18n.fijar_idioma("en")
        selector = editor.abrir_selector("volume up")
        if selector.encontradas() != ["volumen +"]:
            fallos.append(f"en ingles 'volume up' trajo "
                          f"{selector.encontradas()}")
        if selector.buscador.placeholderText() == controles.BUSCAR:
            fallos.append("el buscador quedo en castellano")
    finally:
        i18n.fijar_idioma("es")
    if otra.selector() is not None:
        otra.selector().hide()
    editor.selector().hide()


def test_el_clic_izquierdo_no_se_pierde_desde_la_ventana(fallos, app):
    """El boton 1 se remapea, el 6 y el 7 no ofrecen el clic, y el que se va
    a quedar sin clic lo frena la biblioteca con un mensaje que se entiende.

    Antes el boton 1 iba en gris. Se pidio la regla del
    fabricante -al menos un boton con clic izquierdo- limitada a los botones 1
    a 5, porque el 6 y el 7 estan en la base.
    """
    from linshark import estructuras as est
    from linshark import sesion as ses
    from linshark_ui.paneles.parametros import PanelDeParametros

    panel = PanelDeParametros()
    estado = _estado_falso()
    panel.poner_estado(estado)
    filas = panel.filas()
    pedidos = []
    panel.pidio_escribir.connect(lambda c, v: pedidos.append((c, v)))

    clic = est.FUNCIONES_DE_BOTON[est.FUNCION_CLIC_IZQUIERDO]
    for clave, fila in filas.items():
        if fila.campo.slot is None:
            continue
        datos = [fila.editor.lista.itemData(i)
                 for i in range(fila.editor.lista.count())]
        if not fila.editor.isEnabled():
            fallos.append(f"{clave} quedo en gris")
        if (clic in datos) != (fila.campo.slot in est.SLOTS_PARA_CLIC_IZQUIERDO):
            fallos.append(f"{clave} (boton {fila.campo.slot}) "
                          f"{'ofrece' if clic in datos else 'no ofrece'} el "
                          "clic izquierdo")

    # Elegir otra funcion para el unico clic izquierdo pide escribir -la
    # ventana no decide- y la biblioteca lo frena sobre el bloque del mouse.
    filas["boton_izquierdo"].editor.elegir("clic derecho")
    if pedidos != [("boton_izquierdo", "clic derecho")]:
        fallos.append(f"elegir en el boton 1 pidio {pedidos}")
    bloque = bytes.fromhex(estado["comandos"][str(p.CMD_BUTTONS)]["datos"])
    m = ses.preparar_mutacion("boton_izquierdo", "clic derecho")
    try:
        m.codificar(bloque)
    except est.SinClicIzquierdo as exc:
        if "único con clic izquierdo" not in str(exc):
            fallos.append(f"el motivo no dice que hacer: {exc}")
    else:
        fallos.append("dejo sacar el unico clic izquierdo")


def test_los_botones_se_leen_claro(fallos, app):
    """Nombres largos en las opciones, la misma opcion por debajo, y la fila de
    intercambiar entre el boton derecho y el sentido de la rueda."""
    from linshark_ui.paneles.parametros import PanelDeParametros

    panel = PanelDeParametros()
    panel.poner_estado(_estado_falso())
    pedidos = []
    panel.pidio_escribir.connect(lambda c, v: pedidos.append((c, v)))
    fila = panel.filas()["boton_costado_atras"]
    lista = fila.editor.lista
    textos = {lista.itemData(i): lista.itemText(i) for i in range(lista.count())}
    if textos.get("atras") != "Atrás (página anterior)":
        fallos.append(f"la opcion 'atras' se lee {textos.get('atras')!r}")
    if len(set(textos.values())) != len(textos):
        fallos.append("hay dos opciones que se leen igual")
    if lista.currentData() != "atras":
        fallos.append(f"el valor de la fila es {lista.currentData()!r}")

    acciones = panel.acciones()
    if "intercambiar_clics" not in acciones:
        fallos.append(f"no esta la fila de intercambiar: {list(acciones)}")
        return
    accion = acciones["intercambiar_clics"]
    caja = panel._cajas[p.CMD_BUTTONS]
    if caja.indexOf(accion) != caja.indexOf(panel.filas()["boton_derecho"]) + 1:
        fallos.append("la fila de intercambiar no quedo abajo del boton derecho")
    accion.boton.click()
    if pedidos != [("intercambiar_clics", True)]:
        fallos.append(f"intercambiar pidio {pedidos}")


def test_la_ayuda_dice_que_es_cada_parametro(fallos, app):
    """Detras de cada `?`: que es y para que sirve, y nada mas.

    Antes el `?` juntaba lo medido del campo -la nota, por que no se
    escribe, lo que muestra el cliente oficial-. Se pidio al reves: la ayuda explica el parametro, y la evidencia se queda en
    el modelo y en `dev/docs/`. Esto cuida las dos mitades.
    """
    import re
    from linshark_ui import controles
    from linshark_ui.paneles.parametros import PanelDeParametros

    panel = PanelDeParametros()
    panel.poner_estado(_estado_falso())
    evidencia = re.compile(r"20\d\d-\d\d-\d\d|MEDID|INFERID|cliente oficial|"
                           r"pagina oficial|bundle|captura|I-W\d|Etapa \d|"
                           r"cmd \d", re.I)
    for clave, fila in panel.filas().items():
        partes = controles.ayuda_de(fila.campo)
        if not partes:
            fallos.append(f"{clave}: el `?` no explica nada")
            continue
        for role, texto in partes:
            if role not in ("nota", "aviso"):
                fallos.append(f"{clave}: la ayuda trae un {role!r}")
            if evidencia.search(texto):
                fallos.append(f"{clave}: la ayuda cita evidencia: {texto[:70]!r}")
            if texto not in fila.toolTip():
                fallos.append(f"{clave}: el tooltip no dice lo mismo que el `?`")
        if fila.campo.nota and any(fila.campo.nota in t for _, t in partes):
            fallos.append(f"{clave}: la nota medida volvio a la pantalla")

    # El boton de modo: solo el aviso de que sigue cambiando de modo.
    modo = controles.ayuda_de(panel.filas()["boton_modo"].campo)
    if [r for r, _ in modo] != ["aviso"] or "modo" not in modo[0][1]:
        fallos.append(f"el boton de modo no dice solo su aviso: {modo}")

    # Y el esquema: una definicion, sin la evidencia de cada numero.
    diag = panel.diagrama()
    diag.mostrar_ayuda()
    textos = diag.popup().textos()
    if len(textos) != 1 or evidencia.search(textos[0]):
        fallos.append(f"el `?` del esquema no es una definicion: {textos}")
    for dibujo in diag.dibujos():
        if evidencia.search(dibujo.toolTip()):
            fallos.append(f"el tooltip de un numero cita evidencia: "
                          f"{dibujo.toolTip()[:80]!r}")


def test_cada_boton_lleva_su_numero(fallos, app):
    """El mismo numero que el esquema dibuja sobre el mouse, al lado del nombre.

    Solo en las filas que son un boton: el sentido del scroll no es ninguno, y
    un nivel de dpi lleva su color en ese lugar.
    """
    from linshark_ui.paneles.parametros import PanelDeParametros

    panel = PanelDeParametros()
    panel.poner_estado(_estado_falso())
    filas = panel.filas()
    numerados = {c: f.numero.text() for c, f in filas.items() if se_ve(f.numero)}
    fisicos = {b.clave: str(b.slot) for b in modelo_botones()}
    if numerados != fisicos:
        fallos.append(f"los numeros de las filas {numerados} no son los del "
                      f"esquema {fisicos}")
    for clave, fila in filas.items():
        if clave in fisicos and se_ve(fila.marca):
            fallos.append(f"{clave}: dibuja la marca de color y el numero")
        if clave not in fisicos and not se_ve(fila.marca):
            fallos.append(f"{clave}: sin numero, la marca tiene que ocupar su lugar")
    # todas del mismo ancho, para que los nombres sigan alineados
    anchos = {f.insignia.width() for f in filas.values()}
    if len(anchos) != 1:
        fallos.append(f"la columna de la marca cambia de ancho: {anchos}")


def modelo_botones():
    from linshark import modelo
    return modelo.botones_fisicos(_estado_falso())


def test_leer_pide_mover_el_mouse(fallos, app):
    """Mientras se lee por primera vez, el cartel vacio pide mover el mouse.

    Y si la lectura no trae nada, deja de pedirlo: un aviso de "leyendo" que
    queda puesto despues de que la lectura fallo miente.
    """
    from linshark import conexiones as con
    from linshark_ui.ventana import Ventana

    # **El bus se fija**: la ventana lo mira al arrancar, y el cartel depende
    # del camino. Con el mouse de la maquina enchufado por cable, esta prueba
    # veia el texto del cable y fallaba por algo que no es suyo.
    real = con.buscar
    con.buscar = lambda *a, **k: [_conexion_falsa(con.VIA_DONGLE, "1-2",
                                                  0xFA65)]
    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())
    vacio = ventana.parametros._vacio
    antes = vacio.text()
    try:
        # sin el hilo andando la lectura falla en el acto, y el aviso se va
        ventana.leer()
        if vacio.text() != antes:
            fallos.append("una lectura que fallo dejo puesto el aviso de mover "
                          f"el mouse: {vacio.text()!r}")

        hw.conectar()
        ventana.leer()
        # la señal del hilo llega despues: hasta que se procesen eventos, se lee
        if "movelo" not in vacio.text().lower() or vacio.property("role") != "aviso":
            fallos.append(f"al leer no pidio mover el mouse: {vacio.text()!r}")
        _correr_hasta(app, lambda: bool(ventana.parametros.filas()))
        if se_ve(vacio):
            fallos.append("con el mouse leido el cartel sigue a la vista")

        # **Por cable no se pide**: no hay radio que pierda pedidos.
        ventana.parametros.leyendo(True, con.VIA_CABLE)
        if "movelo" in vacio.text().lower():
            fallos.append(f"por cable pidio mover el mouse: {vacio.text()!r}")
        ventana.parametros.leyendo(False)
    finally:
        con.buscar = real
        ventana.close()
        hw.cerrar()


def test_las_advertencias_del_macro_se_ven_antes_de_grabar(fallos, app):
    """Las dos que importan, **antes** de apretar grabar."""
    from linshark_ui.paneles.macros import PanelDeMacros

    panel = PanelDeMacros(_nombres_de_prueba())
    panel.poner_estado(_estado_falso())
    if panel.macro_id() != 17:
        fallos.append(f"no eligio el macro 17: {panel.macro_id()}")

    panel.eventos.setPlainText("a:abajo@10")
    avisos = " ".join(panel.avisos_de_los_pasos())
    if "no se reproduce" not in avisos:
        fallos.append(f"no aviso que un macro de un evento no corre: {avisos}")
    if "desconectar el receptor" not in avisos:
        fallos.append(f"no aviso de la tecla trabada: {avisos}")
    if not se_ve(panel.avisos) or "no se reproduce" not in panel.avisos.text():
        fallos.append("las advertencias no llegaron a la pantalla")

    panel.eventos.setPlainText("a:abajo@10, a:arriba@10")
    if panel.avisos_de_los_pasos():
        fallos.append(f"aviso de un macro sano: {panel.avisos_de_los_pasos()}")

    # Un texto que no cierra se dice donde se esta escribiendo, no al grabar.
    panel.eventos.setPlainText("esto no es un evento")
    if not any("tecla:direccion@ms" in a for a in panel.avisos_de_los_pasos()):
        fallos.append(f"un paso mal escrito no se explico: "
                      f"{panel.avisos_de_los_pasos()}")


def test_el_modo_sin_medir_se_dice(fallos, app):
    """Cambiar el modo lo pide, y un modo sin medir lo avisaria.

    **Hoy no hay ninguno sin medir**: los tres del X8 Pro estan verificados
    apretando el boton, y el 1 -el que faltaba- se cerro el 2026-09-20. Por eso
    `modelo.MODO_SIN_MEDIR` es None y el aviso **no tiene que salir**.

    El camino se prueba igual, con el aviso forzado, porque vuelve a hacer
    falta en cuanto aparezca un modelo con el cuarto modo que el bundle lista
    (`StopOnCurrentKey`) y el X8 Pro no tiene.
    """
    from linshark import estructuras as est
    from linshark import modelo
    from linshark_ui.paneles.macros import PanelDeMacros

    panel = PanelDeMacros(_nombres_de_prueba())
    panel.poner_estado(_estado_falso())
    pedidos = []
    panel.pidio_escribir.connect(
        lambda c, v, m: pedidos.append((c, v, m)))

    otro = next(m for m in est.MACRO_MODOS if m != est.MACRO_MODO_CON_CONTADOR)
    indice = panel.modo.findData(otro)
    panel.modo.setCurrentIndex(indice)
    panel._al_elegir_modo(indice)
    if pedidos != [("macro_modo", otro, 17)]:
        fallos.append(f"el cambio de modo pidio {pedidos}")
    if modelo.MODO_SIN_MEDIR is None and se_ve(panel.aviso_modo):
        fallos.append("aviso 'sin medir' sobre un modo que esta medido")

    # Y el camino del aviso, con uno forzado: tiene que poder volver a salir.
    viejo = modelo.MODO_SIN_MEDIR
    modelo.MODO_SIN_MEDIR = otro
    try:
        panel._al_elegir_modo(indice, escribir=False)
        if not se_ve(panel.aviso_modo):
            fallos.append("con un modo sin medir el aviso no sale")
    finally:
        modelo.MODO_SIN_MEDIR = viejo
    panel._al_elegir_modo(indice, escribir=False)

    # El contador es solo del modo 0: en los otros el byte va forzado a 1.
    if panel.repeticiones.isEnabled():
        fallos.append("dejo pedir repeticiones en un modo que no las tiene")
    indice0 = panel.modo.findData(est_modo_con_contador())
    panel.modo.setCurrentIndex(indice0)
    panel._al_elegir_modo(indice0)
    if not panel.repeticiones.isEnabled():
        fallos.append("el modo con contador no habilito las repeticiones")


def est_modo_con_contador() -> int:
    from linshark import estructuras as est
    return est.MACRO_MODO_CON_CONTADOR


def test_el_grabador_arma_pasos_que_la_biblioteca_acepta(fallos, app):
    """Grabar en vivo tiene que producir lo mismo que se escribe a mano."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    from linshark import estructuras as est
    from linshark_ui.paneles.macros import PanelDeMacros

    panel = PanelDeMacros(_nombres_de_prueba())
    panel.poner_estado(_estado_falso())
    panel.eventos.clear()
    panel.prender.setChecked(True)
    if not panel.grabador.grabando():
        fallos.append("el grabador no arranco")

    # Una tecla de verdad, por el mismo camino que Qt usa con un teclado.
    panel.grabador.keyPressEvent(
        QKeyEvent(QKeyEvent.KeyPress, Qt.Key_A, Qt.NoModifier))
    panel.grabador.keyReleaseEvent(
        QKeyEvent(QKeyEvent.KeyRelease, Qt.Key_A, Qt.NoModifier))
    panel.grabador.anotar("clic-rueda", "abajo")
    panel.grabador.anotar("clic-rueda", "arriba")

    texto = panel.texto_de_pasos()
    try:
        eventos = est.eventos_desde_texto(texto)
    except ValueError as exc:
        fallos.append(f"lo que grabo no se puede escribir ({texto!r}): {exc}")
        return
    if len(eventos) != 4:
        fallos.append(f"grabo {len(eventos)} eventos, esperaba 4: {texto!r}")
    nombres = [est.nombre_de_evento(e["usageId"]) for e in eventos]
    if nombres[:2] != ["a", "a"]:
        fallos.append(f"la tecla no se tradujo: {nombres}")
    # dir0 aprieta y dir1 suelta (MEDIDO)
    if [e["direccion"] for e in eventos] != [0, 1, 0, 1]:
        fallos.append(f"las direcciones salieron {[e['direccion'] for e in eventos]}")
    if est.eventos_sin_cerrar(eventos):
        fallos.append("un macro grabado apretando y soltando quedo sin cerrar")

    panel.prender.setChecked(False)
    if panel.grabador.grabando():
        fallos.append("el grabador no se apago")


def test_grabar_un_macro_pasa_por_la_biblioteca(fallos, app):
    """La ventana no arma bloques: pide, y `preparar_mutacion` traduce."""
    from linshark_ui.paneles.macros import PanelDeMacros

    panel = PanelDeMacros(_nombres_de_prueba())
    panel.poner_estado(_estado_falso())
    pedidos = []
    panel.pidio_escribir.connect(lambda c, v, m: pedidos.append((c, v, m)))
    panel.eventos.setPlainText("a:abajo@10, a:arriba@10")
    panel._al_grabar()
    if pedidos != [("macro_eventos", "a:abajo@10, a:arriba@10", 17)]:
        fallos.append(f"grabar pidio {pedidos}")
        return
    clave, valor, mid = pedidos[0]
    try:
        m = sesion.preparar_mutacion(clave, valor, macro_id=mid)
    except Exception as exc:                       # noqa: BLE001
        fallos.append(f"lo que pidio no se puede escribir: {exc}")
        return
    if m.macro_id != 17 or m.cmd != p.CMD_MACRO:
        fallos.append(f"la mutacion salio mal: cmd={m.cmd} id={m.macro_id}")


def test_la_ventana_escribe_y_se_bloquea_mientras(fallos, app):
    """De punta a punta: un click, la Etapa 3 entera, y la pantalla quieta."""
    from linshark_ui.ventana import Ventana

    mouse = _MouseFalso()
    hw = Hardware(device=mouse)
    ventana = Ventana(hw, _nombres_de_prueba())
    hw.conectar()
    hw.leer_estado()
    if not _correr_hasta(app, lambda: bool(ventana.parametros.filas())):
        fallos.append("la ventana no llego a dibujar el estado")
        hw.cerrar()
        return

    listo = []
    hw.escritura_lista.connect(listo.append)
    ventana.parametros.filas()["tasa"].editor.elegir(500)
    # el bloqueo es sincronico: pasa antes de que el hilo conteste nada
    if ventana.parametros.filas()["tasa"].editor.isEnabled():
        fallos.append("la pantalla siguio aceptando cambios mientras escribia")
    if not _correr_hasta(app, lambda: bool(listo)):
        fallos.append("la escritura no termino")
    elif not listo[0].ok:
        fallos.append(f"la escritura dio {listo[0].motivo!r}")
    if len(mouse.escrituras) != 1:
        fallos.append(f"mando {len(mouse.escrituras)} escrituras, no 1")
    # **`ocupado(False)` sale DESPUES del resultado**, porque vive en el
    # `finally` de la escritura: comprobar el desbloqueo apenas llega
    # `escritura_lista` es una carrera, y empezo a perderse.
    # Es la misma espera que `test_dos_escrituras_no_se_encinan` ya hacia.
    _correr_hasta(app,
                  lambda: ventana.parametros.filas()["tasa"].editor.isEnabled())
    if not ventana.parametros.filas()["tasa"].editor.isEnabled():
        fallos.append("la pantalla quedo bloqueada despues de escribir")
    if not any("salio bien" in l for l in ventana.lineas_del_registro()):
        fallos.append("el registro no anoto como salio: es lo unico que queda "
                      f"ahora que no se pregunta ({ventana.lineas_del_registro()})")
    hw.cerrar()


def test_la_ventana_ofrece_el_arreglo_de_udev(fallos, app):
    """G-05 en pantalla: un boton, no un parrafo para copiar a mano."""
    from linshark.hidraw import COMANDO_UDEV
    from linshark_ui.ventana import Ventana

    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())
    ventana.al_haber_problema("sin permiso sobre /dev/hidraw2", COMANDO_UDEV)
    if not se_ve(ventana.problema):
        fallos.append("el cartel no aparecio")
    if not se_ve(ventana.problema.copiar):
        fallos.append("no ofrecio el comando")
    ventana.problema._al_copiar()
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.clipboard().text() != COMANDO_UDEV:
        fallos.append("el boton de copiar no copio el comando")
    # El de aplicar necesita el script por ruta absoluta. Buscaba en
    # `driver/driver/scripts/` y no aparecia nunca, sin que nada lo notara.
    script = ventana.problema._script()
    if not script.endswith("/scripts/instalar-udev.sh"):
        fallos.append(f"no encuentra el script de udev para aplicarlo: {script!r}")
    # y un problema sin arreglo no ofrece un boton que no hace nada
    ventana.al_haber_problema("el enlace perdio el pedido", "")
    if se_ve(ventana.problema.copiar):
        fallos.append("ofrecio copiar un comando que no existe")


def test_la_bateria_dice_cuando_dejo_de_llegar(fallos, app):
    """Con el cable a la PC el mouse se calla, y el dongle no se entera.

    MEDIDO: 32 s de silencio entre dos tramos que latian cada
    2,00 s. Una pantalla que muestre el ultimo porcentaje sin decir de cuando
    es estaria afirmando algo que no sabe.
    """
    from datetime import datetime, timedelta

    from linshark_ui.ventana import SILENCIO_SOSPECHOSO, Ventana

    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())
    ventana.al_haber_novedad(sesion.novedad_de(bytes.fromhex("08400150")))
    if "80%" not in ventana.conexion.bateria.text():
        fallos.append(f"la bateria no llego: {ventana.conexion.bateria.text()!r}")
    if "cargando" in ventana.conexion.bateria.text():
        fallos.append("dijo que estaba cargando con el byte de a bateria")

    ventana.al_haber_novedad(sesion.novedad_de(bytes.fromhex("08400350")))
    if "cargando" not in ventana.conexion.bateria.text():
        fallos.append("no vio el byte de cargando (MEDIDO)")

    # un byte que nadie midio no se traduce a "a bateria"
    ventana.al_haber_novedad(sesion.novedad_de(bytes.fromhex("08400250")))
    if "sin medir" not in ventana.conexion.bateria.text():
        fallos.append(f"invento el estado de un byte sin medir: "
                      f"{ventana.conexion.bateria.text()!r}")

    ventana.conexion._ultima = datetime.now() - timedelta(
        seconds=SILENCIO_SOSPECHOSO + 5)
    ventana.conexion._pintar_bateria()
    if "sin novedades" not in ventana.conexion.bateria.text():
        fallos.append(f"no dijo que el numero era viejo: "
                      f"{ventana.conexion.bateria.text()!r}")


def test_el_dpi_que_cambia_solo_no_se_muestra_al_reves(fallos, app):
    """El mouse cambia el nivel con su boton, y la pantalla no lo inventa.

    Reflejarlo a mano seria afirmar que el resto del bloque no cambio, que no
    se sabe. Se avisa y se ofrece releer, que es la unica forma honesta.
    """
    from linshark_ui.ventana import Ventana

    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())
    ventana.parametros.poner_estado(_estado_falso())
    antes = ventana.parametros.filas()["nivel_activo"].campo.valor
    ventana.al_haber_novedad(sesion.novedad_de(bytes.fromhex("08100300")))
    if not se_ve(ventana.desactualizado):
        fallos.append("no aviso que el mouse habia cambiado solo")
    elif "3" not in ventana.desactualizado_texto.text():
        fallos.append(f"no dijo a que nivel: "
                      f"{ventana.desactualizado_texto.text()!r}")
    despues = ventana.parametros.filas()["nivel_activo"].campo.valor
    if despues != antes:
        fallos.append("pinto un valor que no leyo del mouse")


def test_cerrar_la_ventana_baja_el_hilo(fallos, app):
    """Y espera a lo que este en vuelo, que es lo que hace `cerrar()`."""
    from linshark_ui.ventana import Ventana

    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())
    hw.conectar()
    hw.leer_estado()
    _correr_hasta(app, lambda: bool(ventana.parametros.filas()))
    ventana.close()
    if hw._hilo is not None:
        fallos.append("el hilo de hardware quedo andando despues de cerrar")



def test_dos_escrituras_no_se_encinan(fallos, app):
    """Una Etapa 3 por vez, y la pantalla bloqueada hasta que no quede ninguna.

    Dos corridas encimadas se pisan de tres maneras: dos respaldos completos
    compitiendo por el enlace, dos lecturas del paso 2 que pueden ver el bloque
    a medio cambiar, y el paso 0 devolviendo la tasa mientras la otra la
    necesita baja.
    """
    import asyncio

    hw = Hardware(device=_MouseFalso())
    orden, estados, listas = [], [], []
    hw.ocupado.connect(estados.append)
    hw.escritura_lista.connect(listas.append)

    original = sesion.aplicar

    async def lenta(device, **kw):
        orden.append("entra")
        await asyncio.sleep(0.3)
        orden.append("sale")
        return sesion.Resultado(True, "cambio-lo-pedido")

    # **No se usa la tasa como campo de muestra**, y es a proposito: la tasa
    # no pasa por `sesion.aplicar()` sino por el camino de
    # un solo comando (ver `sesion.Configuracion._escribir_tasa`), asi que con
    # ella este parche no interceptaria nada y la prueba pasaria sin ejercer lo
    # que dice ejercer. `lod` es un campo cualquiera, que es lo que hace falta.
    sesion.aplicar = lenta
    try:
        hw.conectar()
        hw.escribir("lod", 2)
        # **Se espera a que la primera este adentro antes de pedir la
        # segunda.** Sin esto el orden dependia de como el loop reparta las
        # tareas: si la primera llegaba a terminar sola, `ocupado` emitia
        # `True, False, True, False` -que es correcto, son dos escrituras
        # separadas- y la comparacion contra `[True, False]` fallaba cada
        # tanto sin que hubiera nada roto. Una alarma que suena sin motivo
        # gasta a las que importan.
        if not _correr_hasta(app, lambda: orden == ["entra"], segundos=5):
            fallos.append(f"la primera escritura no arranco: {orden}")
        hw.escribir("lod", 1)
        if not _correr_hasta(app, lambda: len(listas) == 2, segundos=10):
            fallos.append(f"terminaron {len(listas)} de 2 escrituras")
        # el `False` se emite en el `finally` de la escritura, o sea despues
        # del resultado: hay que dejar que Qt entregue esa señal tambien
        _correr_hasta(app, lambda: len(estados) == 2, segundos=5)
    finally:
        sesion.aplicar = original
        hw.cerrar()

    if orden != ["entra", "sale", "entra", "sale"]:
        fallos.append(f"las dos escrituras se encimaron: {orden}")
    if estados != [True, False]:
        fallos.append(f"la pantalla se desbloqueo en el medio: {estados}")


def test_un_problema_ajeno_no_desbloquea_la_pantalla(fallos, app):
    """El aviso de un modelo desconocido llega de una novedad, en cualquier
    momento. Si desbloqueara, se podria pedir otra escritura arriba de una."""
    from linshark_ui.ventana import Ventana

    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())
    ventana.parametros.poner_estado(_estado_falso())
    ventana._bloquear(True)
    ventana.al_haber_problema("un mouse que nadie midio", "")
    if ventana.parametros.filas()["tasa"].editor.isEnabled():
        fallos.append("un problema ajeno desbloqueo la pantalla en el medio "
                      "de una escritura")
    ventana._bloquear(False)
    if not ventana.parametros.filas()["tasa"].editor.isEnabled():
        fallos.append("no volvio a desbloquearse")


def test_cambiar_de_macro_cambia_los_pasos(fallos, app):
    """Los pasos que se ven son **de este macro**, no del anterior.

    Sin esto, elegir otro macro dejaba a la vista la lista del que estaba
    antes, y "grabar en el mouse" la escribia en el nuevo: se perdia un macro
    sin que nada lo dijera.
    """
    from linshark_ui.paneles.macros import PanelDeMacros

    panel = PanelDeMacros(_nombres_de_prueba())
    # dos macros: el 17 con dos eventos y el 20, que el mouse falso devuelve
    # con el mismo bloque -alcanza para que sean dos entradas distintas-
    estado = _estado_falso(macros_extra=(17, 20))
    panel.poner_estado(estado)
    if len(panel._macros) < 2:
        fallos.append(f"el estado trajo {len(panel._macros)} macro(s), "
                      "necesito dos para probar esto")
        return

    panel.elegir(17)
    panel.eventos.setPlainText("z:abajo@10, z:arriba@10")
    pedidos = []
    panel.pidio_escribir.connect(lambda c, v, m: pedidos.append((c, v, m)))
    panel.elegir(20)
    if panel.texto_de_pasos() == "z:abajo@10, z:arriba@10":
        fallos.append("los pasos del macro anterior quedaron a la vista")
    panel._al_grabar()
    if pedidos and pedidos[0][1] == "z:abajo@10, z:arriba@10":
        fallos.append(f"iba a escribir los pasos del otro macro: {pedidos}")


# --- los cuatro que encontro la auditoria -------------------


def test_un_pedido_que_no_entra_no_deja_la_pantalla_muerta(fallos, app):
    """Si el hilo de hardware no esta, la ventana tiene que volver en si.

    `Ventana.escribir()` bloquea la pantalla **antes** de pedir -para que un
    segundo click no entre en el medio- y la desbloquea con `ocupado`, que se
    emite adentro de la corrutina. Si la corrutina no arranca nunca, nadie la
    desbloquea: la ventana queda muerta y encima Python deja la corrutina
    colgada con un `RuntimeWarning` que no mira nadie.
    """
    import warnings

    from linshark_ui.ventana import Ventana

    # 1. sin `conectar()`: no hay hilo, `_loop` es None
    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())
    ventana.parametros.poner_estado(_estado_falso())
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        ventana.parametros.filas()["tasa"].editor.elegir(500)
        app.processEvents()
    colgadas = [str(a.message) for a in avisos
                if "never awaited" in str(a.message)]
    if colgadas:
        fallos.append(f"dejo una corrutina colgada: {colgadas}")
    if not ventana.parametros.filas()["tasa"].editor.isEnabled():
        fallos.append("la pantalla quedo bloqueada para siempre")
    if ventana.problema.isHidden():
        fallos.append("no dijo que el pedido no habia entrado")

    # 2. **despues de `cerrar()` el loop no es None: esta CERRADO.** Ahi
    #    `run_coroutine_threadsafe` tira `RuntimeError` por el medio de un slot
    #    de Qt, que es peor que el caso de arriba.
    hw2 = Hardware(device=_MouseFalso())
    hw2.conectar()
    hw2.cerrar()
    ventana2 = Ventana(hw2, _nombres_de_prueba())
    ventana2.parametros.poner_estado(_estado_falso())
    with warnings.catch_warnings(record=True) as avisos2:
        warnings.simplefilter("always")
        try:
            ventana2.parametros.filas()["tasa"].editor.elegir(500)
            app.processEvents()
        except Exception as exc:                       # noqa: BLE001
            fallos.append(f"escribir tras cerrar revento: "
                          f"{type(exc).__name__}: {exc}")
    colgadas2 = [str(a.message) for a in avisos2
                 if "never awaited" in str(a.message)]
    if colgadas2:
        fallos.append(f"tras cerrar dejo una corrutina colgada: {colgadas2}")
    if not ventana2.parametros.filas()["tasa"].editor.isEnabled():
        fallos.append("tras cerrar, la pantalla quedo bloqueada")


def test_una_escritura_fallida_no_deja_el_valor_pedido_en_pantalla(fallos, app):
    """Lo que se ve tiene que ser lo que el mouse tiene.

    Una escritura que falla **antes** de la relectura -respaldo incompleto, el
    mouse que no contesta- no trae estado nuevo. Sin esto, el desplegable se
    quedaba mostrando la opcion elegida y quien mira se iba convencido de que
    el cambio entro. Es la misma mentira que este proyecto le reprocha a la
    pagina oficial, solo que nuestra.
    """
    from linshark_ui.ventana import Ventana

    mouse = _MouseFalso()
    hw = Hardware(device=mouse)
    ventana = Ventana(hw, _nombres_de_prueba())
    hw.conectar()
    hw.leer_estado()
    if not _correr_hasta(app, lambda: bool(ventana.parametros.filas())):
        fallos.append("no llego el estado")
        hw.cerrar()
        return

    fila = ventana.parametros.filas()["lod"]
    antes = fila.campo.valor
    # El mouse se calla en el **paso 2**, la lectura del bloque que se va a
    # modificar, asi que la Etapa 3 aborta con `no-contesto` y no hay
    # relectura, que es lo que esta prueba necesita.
    #
    # La cuenta cambio, cuando el respaldo paso a cachearse: la
    # escritura ya no relee los siete comandos, asi que consume **dos**
    # lecturas antes del paso 2 -la tasa que mira `Configuracion.preparar()` y
    # la que mira el paso 0 de `aplicar()`- y la tercera es la del bloque.
    # `_MouseFalso` no reintenta ni pierde pedidos, asi que el numero es exacto
    # y no una estimacion.
    mouse.mudo_tras = mouse.lecturas + 2
    listas = []
    hw.escritura_lista.connect(listas.append)
    fila.editor.elegir(2)
    _correr_hasta(app, lambda: bool(listas), segundos=20)
    _correr_hasta(app, lambda: fila.editor.isEnabled(), segundos=10)

    if not listas:
        fallos.append("la escritura no termino")
    elif listas[0].ok:
        fallos.append("dio por buena una escritura que no llego a escribir")
    elif listas[0].despues is not None:
        fallos.append("esta prueba necesita un fallo SIN relectura; "
                      f"salio {listas[0].motivo!r}, que si la trae")
    if mouse.escrituras:
        fallos.append("ESCRIBIO sin haber podido leer el bloque")
    quedo = fila.editor.lista.currentData()
    if quedo != antes:
        fallos.append(f"la pantalla quedo mostrando {quedo}, que es lo que se "
                      f"pidio, y el mouse tiene {antes}")
    hw.cerrar()


def test_el_respaldo_no_se_vuelve_a_leer_en_cada_escritura(fallos, app):
    """La segunda escritura no relee el mouse entero. **Es el arreglo entero.**

    Leer el mouse tarda minutos, y antes cada campo escrito eran
    **dos** lecturas completas -el respaldo del paso 1 y la relectura del paso
    6-. Con eso, mover un deslizador dejaba la ventana congelada, que es lo que
    el usuario reporto como "se cuelga".

    Lo que se cuenta aca son lecturas al mouse, que es la unidad en la que se
    paga: no el reloj, que en una prueba contra `_MouseFalso` no mide nada.
    """
    mouse = _MouseFalso()
    hw = Hardware(device=mouse)
    listas = []
    hw.escritura_lista.connect(listas.append)
    hw.conectar()
    hw.leer_estado()
    if not _correr_hasta(app, lambda: mouse.lecturas > 0, segundos=20):
        fallos.append("no llego a leer el estado")
        hw.cerrar()
        return

    hw.escribir("lod", 2)
    if not _correr_hasta(app, lambda: len(listas) == 1, segundos=30):
        fallos.append("la primera escritura no termino")
        hw.cerrar()
        return
    completas = mouse.pedidos.count(p.CMD_VERSION)
    hw.escribir("lod", 1)
    if not _correr_hasta(app, lambda: len(listas) == 2, segundos=30):
        fallos.append("la segunda escritura no termino")
        hw.cerrar()
        return

    if not all(r.ok for r in listas):
        fallos.append(f"alguna escritura fallo: {[r.motivo for r in listas]}")
    # **El detector es exacto, no un umbral**: `CMD_VERSION` esta en `A_LEER` y
    # no lo pide ningun otro camino, asi que si aparece una vez mas es que se
    # leyo el mouse entero otra vez.
    if mouse.pedidos.count(p.CMD_VERSION) != completas:
        fallos.append("la segunda escritura releyo el mouse entero: son "
                      "minutos de ventana congelada por cada campo")
    hw.cerrar()


def test_el_deslizador_no_ofrece_lo_que_el_mouse_no_guarda(fallos, app):
    """Cada posicion del deslizador tiene que ser escribible **tal cual**.

    Con paso 1 el deslizador del dpi tenia 39.900 posiciones sobre 900 px: cada
    pixel eran ~45 dpi y salia 1623, que el mouse guarda como 1600. El numero
    que se muestra y el que queda no eran el mismo, y el unico aviso era el
    salto despues de releer.
    """
    from linshark import estructuras as est
    from linshark_ui import controles
    from linshark_ui.paneles.parametros import PanelDeParametros

    panel = PanelDeParametros()
    panel.poner_estado(_estado_falso())
    mouse = _MouseFalso()
    for clave, fila in panel.filas().items():
        editor = fila.editor
        if not isinstance(editor, controles.EditorNumerico):
            continue
        if not fila.campo.escribible:
            continue
        d = editor.deslizador
        for pos in (d.minimum(), (d.minimum() + d.maximum()) // 2, d.maximum()):
            d.setValue(pos)
            pedido = editor.numero.value()
            try:
                mutacion = sesion.preparar_mutacion(clave, pedido)
                salida = bytes(mutacion.codificar(mouse.bloques[fila.campo.cmd]))
            except Exception as exc:               # noqa: BLE001
                fallos.append(f"{clave}: el deslizador ofrece {pedido}, que no "
                              f"se puede escribir: {exc}")
                continue
            # y lo que el mouse guarda tiene que ser lo que decia la pantalla
            if fila.campo.cmd == p.CMD_DPI:
                nivel = int(clave.removeprefix("dpi_nivel_"))
                _, efectivo = est.escribir_nivel_dpi(
                    mouse.bloques[fila.campo.cmd], nivel, pedido)
                if efectivo != pedido:
                    fallos.append(
                        f"{clave}: el deslizador muestra {pedido} y el mouse "
                        f"guarda {efectivo}")
        if fila.campo.cmd == p.CMD_DPI:
            if controles.paso_de(fila.campo) != 50:
                fallos.append(
                    f"{clave}: paso_de dio {controles.paso_de(fila.campo)}, esperaba 50")
            d.setValue(d.minimum())
            val_min = editor.numero.value()
            d.setValue(d.minimum() + 1)
            val_sig = editor.numero.value()
            if val_sig - val_min != 50:
                fallos.append(
                    f"{clave}: mover el deslizador 1 paso vario {val_sig - val_min}, no 50")


def test_el_teclado_numerico_se_graba_como_el_numerico(fallos, app):
    """El 5 del pad no es el 5 de la fila de arriba: es otro usage HID.

    Qt no tiene `Key_Numpad5`: manda la misma `Key_5` con `KeypadModifier`.
    Sin mirarlo, el pad entero se grababa como la fila principal, y el `+` y
    el `*` -que en la fila principal son combinaciones con Shift- se perdian.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    from linshark import estructuras as est
    from linshark_ui.paneles.macros import PanelDeMacros

    panel = PanelDeMacros(_nombres_de_prueba())
    panel.poner_estado(_estado_falso())
    panel.eventos.clear()
    panel.prender.setChecked(True)

    for tecla in (Qt.Key_5, Qt.Key_Plus):
        panel.grabador.keyPressEvent(
            QKeyEvent(QKeyEvent.KeyPress, tecla, Qt.KeypadModifier))
        panel.grabador.keyReleaseEvent(
            QKeyEvent(QKeyEvent.KeyRelease, tecla, Qt.KeypadModifier))

    texto = panel.texto_de_pasos()
    try:
        eventos = est.eventos_desde_texto(texto)
    except ValueError as exc:
        fallos.append(f"lo que grabo el pad no se puede escribir "
                      f"({texto!r}): {exc}")
        return
    nombres = [est.nombre_de_evento(e["usageId"]) for e in eventos]
    if nombres != ["num-5", "num-5", "num-mas", "num-mas"]:
        fallos.append(f"el pad se grabo como {nombres}")

    # y el 5 de la fila de arriba sigue siendo el 5
    panel.eventos.clear()
    panel.grabador.keyPressEvent(
        QKeyEvent(QKeyEvent.KeyPress, Qt.Key_5, Qt.NoModifier))
    if est.nombre_de_evento(
            est.eventos_desde_texto(panel.texto_de_pasos())[0]["usageId"]) != "5":
        fallos.append("la fila de arriba se grabo como el pad")

    # Todas las teclas del keypad tienen que ser reconocidas por nombre_de_tecla
    from linshark_ui import teclado
    for d in range(10):
        k = getattr(Qt, f"Key_{d}")
        n = teclado.nombre_de_tecla(k, Qt.KeypadModifier)
        if n != f"num-{d}":
            fallos.append(f"teclado numerico {d} dio {n!r}, esperaba 'num-{d}'")
    for k, esperado in [(Qt.Key_Plus, "num-mas"),
                        (Qt.Key_Minus, "num-menos"),
                        (Qt.Key_Asterisk, "num-multiplicar"),
                        (Qt.Key_Slash, "num-dividir"),
                        (Qt.Key_Enter, "num-enter"),
                        (Qt.Key_Period, "num-punto"),
                        (Qt.Key_Comma, "num-punto")]:
        n = teclado.nombre_de_tecla(k, Qt.KeypadModifier)
        if n != esperado:
            fallos.append(f"tecla de pad {k} dio {n!r}, esperaba {esperado!r}")


def test_una_tecla_que_no_entra_se_dice(fallos, app):
    """Tragarsela es lo peor: no pasa nada y nadie sabe por que."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeyEvent

    from linshark_ui.paneles.macros import PanelDeMacros

    panel = PanelDeMacros(_nombres_de_prueba())
    panel.poner_estado(_estado_falso())
    panel.eventos.clear()
    panel.prender.setChecked(True)

    # `Key_Multi_key` no tiene usage HID y no esta en ninguna de las dos tablas
    panel.grabador.keyPressEvent(
        QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Multi_key, Qt.NoModifier))
    if panel.texto_de_pasos():
        fallos.append("grabo una tecla que el bloque no puede expresar")
    if not panel.grabador.rechazo:
        fallos.append("se trago la tecla sin decir nada")
    elif "no entra en un macro" not in panel.grabador.cartel.text():
        fallos.append(f"el cartel no lo explica: "
                      f"{panel.grabador.cartel.text()!r}")

    # y en cuanto entra una buena, el cartel vuelve a lo normal
    panel.grabador.anotar("a", "abajo")
    if panel.grabador.rechazo:
        fallos.append("el cartel de rechazo se quedo pegado")


def test_una_escritura_que_revienta_antes_tambien_restaura(fallos, app):
    """El camino que no pasa por `escritura_lista`, y que por eso se escapa.

    Una escritura puede morir **antes** de `sesion.aplicar()`: alcanza con un
    id de macro que no sea un numero. Ahi `preparar_mutacion()` tira
    `ValueError`, sale por `_envolver` como `problema`, y `escritura_lista`
    **no se emite nunca**.

    Importa porque invita a restaurar la pantalla desde
    `al_terminar_escritura()`, que es donde esta el resultado: ahi el control
    se queda mostrando "macro" para un boton que sigue en "adelante", que es
    justo el bug que esto tenia que arreglar. Lo que corre siempre es
    `ocupado(False)`, que va en un `finally`.
    """
    from linshark_ui.ventana import Ventana

    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())
    problemas, resultados = [], []
    hw.problema.connect(lambda m, c: problemas.append(m))
    hw.escritura_lista.connect(resultados.append)
    hw.conectar()
    hw.leer_estado()
    if not _correr_hasta(app, lambda: bool(ventana.parametros.filas())):
        fallos.append("no llego el estado")
        hw.cerrar()
        return

    fila = ventana.parametros.filas()["boton_costado_adelante"]
    antes = fila.campo.valor
    editor = fila.editor
    editor.elegir("macro")
    editor.parametro.setText("no soy un numero")
    editor._al_poner_parametro()
    _correr_hasta(app, lambda: bool(problemas), segundos=8)
    _correr_hasta(app, lambda: editor.isEnabled(), segundos=8)

    if resultados:
        fallos.append("esta prueba necesita el camino que NO emite "
                      f"escritura_lista; emitio {resultados}")
    if not problemas:
        fallos.append("no dijo nada de un id de macro que no es un numero")
    if not editor.isEnabled():
        fallos.append("la pantalla quedo bloqueada")
    quedo = editor.lista.currentData()
    if quedo != antes:
        fallos.append(f"el control quedo mostrando {quedo!r} y el mouse tiene "
                      f"{antes!r}: es el mismo bug, por el otro camino")
    hw.cerrar()


def test_una_lectura_incompleta_dice_el_motivo_que_corresponde(fallos, app):
    """Las dos causas piden cosas distintas, y una excluye a la otra.

    Con el mouse quieto el enlace pierde pedidos y la respuesta es moverlo.
    Arriba de 1000 Hz los bloques largos **no llegan nunca** (MEDIDO a 2000 y a
    8000) y moverlo no cambia nada: hay que bajar la tasa. Quien usa el mouse
    por radio a 8000 Hz es lo primero que ve al abrir la ventana.
    """
    from linshark_ui.ventana import Ventana

    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())

    # 1. entero, a 1000 Hz
    entero = _estado_falso()
    if "entero" not in ventana.diagnostico_de(entero):
        fallos.append(f"con todo leido dijo: {ventana.diagnostico_de(entero)!r}")

    # 2. incompleto **a 1000 Hz**: ahi si, mover el mouse
    import copy
    quieto = copy.deepcopy(entero)
    quieto["comandos"][str(p.CMD_BUTTONS)] = None
    texto = ventana.diagnostico_de(quieto)
    if "movelo" not in texto:
        fallos.append(f"a 1000 Hz no mando a mover el mouse: {texto!r}")

    # 3. incompleto **a 8000 Hz**: mover el mouse no arregla nada
    import asyncio
    rapido = asyncio.run(sesion.leer_estado(_MouseFalso(hz=8000),
                                            nodo="/dev/falso"))
    rapido["comandos"][str(p.CMD_BUTTONS)] = None
    texto = ventana.diagnostico_de(rapido)
    if "8000" not in texto:
        fallos.append(f"no dijo a que tasa esta el mouse: {texto!r}")
    if "movelo" in texto:
        fallos.append("mando a mover el mouse, que a 8000 Hz no arregla nada: "
                      f"{texto!r}")
    if "tasa" not in texto:
        fallos.append(f"no dijo que hay que bajar la tasa: {texto!r}")

    # y eso pide una decision, asi que sale del renglon de estado
    ventana.al_llegar_estado(rapido)
    if ventana.problema.isHidden():
        fallos.append("la tasa alta quedo solo en la barra de estado")

    # 4. incompleto **por cable**: el byte de rate dice 8000 en el nibble de
    #    la radio, y por cable no manda ese. Ni "bajá la tasa" -por cable no
    #    pasa de 1000- ni "movelo" -no hay radio que pierda pedidos-.
    por_cable = copy.deepcopy(quieto)
    por_cable["via"] = "cable"
    por_cable["comandos"][str(p.CMD_REPORT_RATE)]["datos"] = "01748b00000000"
    texto = ventana.diagnostico_de(por_cable)
    if "Hz" in texto or "movelo" in texto or "leer" not in texto:
        fallos.append(f"por cable el diagnostico dice {texto!r}")
    ventana.problema.hide()
    ventana.al_llegar_estado(por_cable)
    if not ventana.problema.isHidden():
        fallos.append("por cable mostro el cartel de la tasa alta, que es la "
                      "tasa de la radio")


def test_escribir_la_tasa_arriba_de_1000_entra_y_se_queda(fallos, app):
    """Con el mouse a 8000 Hz, pedir 1000 desde la ventana **lo deja en 1000**.

    Antes esto hacia lo contrario, y era el bug que la nota de retomar tenia
    anotado como abierto (bitacora, "La nota de retomar, archivada entera"):
    el paso 0 de la Etapa 3 bajaba la tasa para poder respaldar y su `finally`
    la devolvia, asi que si lo que se escribia **era** la tasa, ese `finally`
    restauraba justo lo que el usuario acababa de cambiar. La relectura no
    veia ninguna diferencia, el veredicto salia `sin-diferencias` y la
    ventana decia que habia salido bien. Un control que no hace nada y
    ademas dice que funciono.

    Se arreglo por la salida que ese documento proponia: la tasa se escribe por
    el camino de un solo comando, igual que `driver/scripts/cambiar-rate.py`, y la
    tasa prestada que la sesion tuviera anotada se cancela **antes** de tocar
    nada (ver `sesion.Configuracion._escribir_tasa`).
    """
    from linshark import estructuras as est
    from linshark_ui.ventana import Ventana

    mouse = _MouseFalso(hz=8000)
    hw = Hardware(device=mouse)
    Ventana(hw, _nombres_de_prueba())
    listas = []
    hw.escritura_lista.connect(listas.append)
    hw.conectar()
    hw.escribir("tasa", 1000)
    if not _correr_hasta(app, lambda: bool(listas), segundos=40):
        fallos.append("la escritura no termino")
        hw.cerrar()
        return

    if not listas[0].ok:
        fallos.append(f"la escritura de la tasa dio {listas[0].motivo!r}")
    quedo = est.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE])
    if quedo != 1000:
        fallos.append(f"se pidio 1000 Hz y el mouse quedo en {quedo}: la "
                      "Etapa 3 volvio a pisar lo que se pidio")

    # Y lo que sigue: cerrar la ventana NO puede devolverlo a 8000, porque los
    # 8000 ya no se deben -el usuario los cambio a proposito-.
    hw.cerrar()
    quedo = est.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE])
    if quedo != 1000:
        fallos.append(f"al cerrar, la tasa volvio a {quedo} Hz: se restauro "
                      "una deuda que el usuario habia cancelado")


def _conexion_falsa(via, puerto, producto, *, usable=True):
    """Una `Conexion` armada a mano, para no depender del bus de la maquina."""
    from pathlib import Path
    from linshark import conexiones as con
    from linshark.perfiles.x8pro import X8_PRO

    nodos = tuple(con.Nodo(Path(f"/dev/hidraw{n}"), n,
                           legible=(n == 2 and usable),
                           escribible=(n == 2 and usable))
                  for n in range(4))
    return con.Conexion(
        via=via, vendor=0x1D57, producto=producto, fabricante="LXDDZ",
        nombre_usb="2.4G 8K HS Receiver", bus=1, dispositivo=8, puerto=puerto,
        ruta=Path(f"/sys/devices/{puerto}"), velocidad=480, nodos=nodos,
        perfil=X8_PRO)


def test_la_ventana_dice_donde_esta_el_mouse(fallos, app):
    """Por donde esta el mouse, en que puerto, y que hacer cuando cambia.

    Se pidio con el mouse cargando por cable y el dongle
    puesto: la ventana decia "conectado a /dev/hidraw2" -que es un detalle de
    Linux- y no decia ni por donde estaba hablando el mouse ni donde estaba
    enchufado, y si el dongle se movia de puerto no se enteraba hasta que
    alguien la cerraba y la abria.

    **Mirar el bus no toca el mouse**: son lecturas de sysfs. Por eso el
    vigilante puede correr cada pocos segundos, y por eso este test puede
    probarlo entero sin hardware.
    """
    from linshark import conexiones as con
    from linshark_ui.i18n import tr
    from linshark_ui.ventana import Ventana

    mouse = _MouseFalso()
    hw = Hardware(device=mouse)
    ventana = Ventana(hw, _nombres_de_prueba())

    bus = {"vistas": []}
    real = con.buscar
    con.buscar = lambda *a, **k: bus["vistas"]
    try:
        # 1. Solo el cable: el mouse **esta**, y la ventana lo dice con su
        #    puerto. Decir "no encuentro el mouse" seria mandar a buscar al
        #    lugar equivocado.
        bus["vistas"] = [_conexion_falsa(con.VIA_CABLE, "1-4", 0x2126,
                                         usable=False)]
        ventana._firma_del_bus = None
        ventana.mirar_el_bus()
        chip = ventana.conexion.via.text()
        if "1-4" not in chip or tr("Cable USB") not in chip:
            fallos.append(f"con el mouse por cable el chip dice {chip!r}")
        if ventana.conexion.via.isHidden() and ventana.conexion.isVisible():
            fallos.append("el chip de por-donde no se muestra")

        # 2. Aparece el dongle: se anota y **se abre solo**. Antes habia que
        #    cerrar la ventana y volver a abrirla.
        pedidos = []
        hw.abrir = lambda: pedidos.append("abrir")
        bus["vistas"] = [_conexion_falsa(con.VIA_DONGLE, "1-2", 0xFA65),
                         _conexion_falsa(con.VIA_CABLE, "1-4", 0x2126,
                                         usable=False)]
        ventana.mirar_el_bus()
        if not pedidos:
            fallos.append("aparecio el dongle y la ventana no intento abrirlo")
        chip = ventana.conexion.via.text()
        if "1-2" not in chip or tr("Dongle 2.4 GHz") not in chip:
            fallos.append(f"con el dongle puesto el chip dice {chip!r}")
        registro = ventana.registro.toPlainText()
        if "1-2" not in registro:
            fallos.append("el cambio del bus no quedo anotado en el registro")

        # 3. El dongle se va: el chip se limpia y se dice.
        bus["vistas"] = []
        ventana.mirar_el_bus()
        if ventana.conexion.via.text():
            fallos.append("se fue todo del bus y el chip sigue diciendo algo")

        # 4. Y el nodo abierto que desaparece lo avisa el canal, no el
        # vigilante: hasta `on_desconexion` no lo escuchaba
        #    nadie y la ventana mostraba un nodo que ya no existia.
        ventana.al_conectar("/dev/hidraw2")
        ventana.al_desconectar("/dev/hidraw2")
        if ventana.conexion.nodo.text():
            fallos.append("el mouse se fue del bus y el nodo sigue en pantalla")
        if "/dev/hidraw2" not in ventana.registro.toPlainText():
            fallos.append("la desconexion no quedo anotada")

        # 5. **El cable, abrible, con el dongle abierto**: es el camino que
        #    contesta -con el cable puesto el dongle se calla (MEDIDO)-, asi
        #    que el chip dice cable, no aparece el cartel de "no contesta", y
        #    la ventana se cambia de camino sin que la cierren. `buscar()` da
        #    el cable primero, y asi se lo arma aca.
        carteles, reaperturas = [], []
        mostrar_real = ventana.problema.mostrar
        ventana.problema.mostrar = lambda *a: carteles.append(a)
        hw.reconectar = lambda: reaperturas.append("reconectar")
        ventana.al_conectar("/dev/hidraw2")
        cable = _conexion_falsa(con.VIA_CABLE, "1-4", 0x2126)
        cable = dataclasses.replace(cable, nodos=tuple(
            con.Nodo(Path(f"/dev/hidraw{n}"), n - 5, legible=(n == 7),
                     escribible=(n == 7)) for n in range(5, 9)))
        bus["vistas"] = [cable, _conexion_falsa(con.VIA_DONGLE, "1-2",
                                                0xFA65)]
        ventana.mirar_el_bus()
        ventana.problema.mostrar = mostrar_real
        chip = ventana.conexion.via.text()
        if tr("Cable USB") not in chip or "1-4" not in chip:
            fallos.append(f"con el cable abrible el chip dice {chip!r}")
        if carteles:
            fallos.append("con el cable abrible avisa que por el dongle no "
                          "contesta, y no se va a usar el dongle")
        if not reaperturas:
            fallos.append("se enchufo el cable con el dongle abierto y la "
                          "ventana siguio hablandole al dongle, que se calla")
    finally:
        con.buscar = real
        hw.cerrar()


def test_la_ventana_abre_el_cable(fallos, app):
    """Con el mouse por cable, la ventana abre el canal del cable y lo usa.

    El bus y el nodo son de mentira -`conexiones.elegir` y `cable.abrir`
    reemplazados-, y el mouse es el de Feature Reports de `salvaguardas`: lo
    que se prueba es el cableado de `Hardware._abrir()`, que por cable no pasa
    por `HidrawChannel` ni espera el Report ID 3 para saber que modelo es.
    """
    from pathlib import Path
    from linshark import cable as c
    from linshark import conexiones as con
    from salvaguardas import _IoctlDeCable, _LARGOS_DEL_CABLE

    mouse = _IoctlDeCable()
    conexion = _conexion_falsa(con.VIA_CABLE, "1-4", 0x2126)
    reales = (con.elegir, c.abrir, c.ESPERA_TRAS_PEDIDO, c.ESPERA_TRAS_LISTO,
              p.WRITE_BLOCK_PAUSE_SOFT)
    con.elegir = lambda *a, **k: conexion
    c.abrir = lambda cx, **k: c.CableDevice(
        Path("/dev/hidraw7"), largos=_LARGOS_DEL_CABLE, ioctl=mouse)
    c.ESPERA_TRAS_PEDIDO = c.ESPERA_TRAS_LISTO = 0
    p.WRITE_BLOCK_PAUSE_SOFT = 0
    hw = Hardware()
    visto = {"estado": None, "modelo": None, "res": None}
    hw.estado.connect(lambda e: visto.__setitem__("estado", e))
    hw.modelo_detectado.connect(
        lambda i, n: visto.__setitem__("modelo", n))
    hw.escritura_lista.connect(lambda r: visto.__setitem__("res", r))
    try:
        hw.conectar()
        hw.leer_estado()
        if not _correr_hasta(app, lambda: visto["estado"] is not None):
            fallos.append("por cable no llego el estado")
            return
        if visto["estado"].get("via") != con.VIA_CABLE or \
                str(p.CMD_MACRO) in visto["estado"]["comandos"]:
            fallos.append("el estado por cable no dice su camino, o trae el "
                          "pedido del macro con el perfil, que por cable no "
                          "existe: el macro se pide con su id, aparte")
        if visto["modelo"] != "X8 Pro":
            fallos.append(f"por cable no dijo que modelo es: {visto['modelo']}")
        # El boton de dpi por cable: el Report ID 3 tiene que llegar a la
        # ventana sin Releer. Se lo inyecta en el hilo de hardware, que es
        # donde lo entrega el canal.
        niveles = []
        hw.novedad.connect(lambda n: niveles.append(n.nivel_dpi))
        # El boton, como lo hace el firmware: el nivel cambia en el mouse y
        # despues avisa. **Por cable se relee solo**: tiene que llegar un
        # estado con el nivel 2 sin que nadie pida Releer.
        from linshark import modelo
        mut = sesion.preparar_mutacion("nivel_activo", 2)
        viejo = mouse.reports[p.CMD_DPI]
        mouse.reports[p.CMD_DPI] = (viejo[:2] + mut.codificar(viejo[2:56])
                                    + viejo[56:])
        visto["estado"] = None
        hw._loop.call_soon_threadsafe(hw._device.alimentar,
                                      bytes.fromhex("0308100200"))
        if not _correr_hasta(app, lambda: 2 in niveles, segundos=5):
            fallos.append("por cable, el aviso del boton de dpi no llego a la "
                          "ventana")
        if not _correr_hasta(app, lambda: visto["estado"] is not None and
                             modelo.por_clave(visto["estado"])[
                                 "nivel_activo"].valor == 2, segundos=10):
            fallos.append("por cable, tras el aviso del boton no se releyo el "
                          "dpi: la ventana sigue mostrando el nivel viejo")
        hw.escribir("tasa", 500)
        if not _correr_hasta(app, lambda: visto["res"] is not None):
            fallos.append("la tasa por cable no termino")
        elif not visto["res"].ok or "060901738c00000000" not in [
                x.hex() for x in mouse.sets]:
            fallos.append(f"la tasa por cable dio {visto['res'].motivo} y "
                          "no mando el report del soft")
    finally:
        (con.elegir, c.abrir, c.ESPERA_TRAS_PEDIDO, c.ESPERA_TRAS_LISTO,
         p.WRITE_BLOCK_PAUSE_SOFT) = reales
        hw.cerrar()


def test_el_aviso_del_nivel_se_va_con_el_nivel_nuevo(fallos, app):
    """El "lo que se ve es de antes" se va cuando llega el nivel avisado.

    Por cable el dpi se relee solo apenas avisa el boton; el aviso tiene que
    irse con ese estado, y **no** con uno que todavia traiga el nivel viejo.
    """
    import copy
    from linshark_ui.ventana import Ventana

    hw = Hardware(device=_MouseFalso())
    ventana = Ventana(hw, _nombres_de_prueba())
    try:
        viejo = _estado_falso()
        ventana.al_llegar_estado(viejo)
        ventana.al_haber_novedad(sesion.novedad_de(bytes([8, 0x10, 2, 0])))
        if ventana.desactualizado.isHidden():
            fallos.append("el aviso del boton de dpi no aparecio")
        ventana.al_llegar_estado(copy.deepcopy(viejo))
        if ventana.desactualizado.isHidden():
            fallos.append("un estado con el nivel viejo tapo el aviso")
        nuevo = copy.deepcopy(viejo)
        dpi = bytes.fromhex(nuevo["comandos"][str(p.CMD_DPI)]["datos"])
        nuevo["comandos"][str(p.CMD_DPI)]["datos"] = sesion.preparar_mutacion(
            "nivel_activo", 2).codificar(dpi).hex()
        ventana.al_llegar_estado(nuevo)
        if not ventana.desactualizado.isHidden():
            fallos.append("llego el nivel avisado y el aviso sigue puesto")
    finally:
        ventana.close()
        hw.cerrar()


def test_un_macro_sin_contador_se_muestra(fallos, app):
    """Un macro en modo 1 o 2 no tiene repeticiones, y el panel no se cae.

    El decodificador devuelve `repeticiones=None` fuera del modo 0, a
    proposito: ahi el byte no es un contador. El panel hacia `max(None, 1)`
    y reventaba; aparecio la primera vez que se leyo un macro en modo 2 (por
    cable, el 17 que habia dejado el soft).
    """
    import copy
    from linshark import estructuras as est
    from linshark_ui.paneles.macros import PanelDeMacros
    from salvaguardas import MACRO_LEIDO

    estado = copy.deepcopy(_estado_falso())
    escrito = est.escribir_macro(bytes.fromhex(MACRO_LEIDO), modo=2)
    leido = escrito[:-2] + bytes([escrito[-1], escrito[-2]])
    estado["macros"]["17"]["datos"] = leido.hex()
    panel = PanelDeMacros(_nombres_de_prueba())
    try:
        panel.poner_estado(estado)
    except Exception as exc:                       # noqa: BLE001
        fallos.append(f"con un macro en modo 2 el panel revento: {exc!r}")
        return
    if panel.modo.currentData() != 2:
        fallos.append(f"el panel muestra el modo {panel.modo.currentData()}")


def test_las_repeticiones_no_cambian_el_modo_a_escondidas(fallos, app):
    """El "Aplicar" de repeticiones no puede mover el modo sin decirlo.

    Escribir el contador **implica el modo 0**, porque ese byte solo es un
    contador ahi (`sesion.preparar_mutacion`, y el CLI pide `--modo 0
    --repeticiones N`). Sobre un macro en otro modo, ese boton lo cambiaria en
    silencio: un control que hace mas de lo que dice es el reproche que este
    proyecto le hace al cliente oficial.

    **Paso de verdad** (2026-09-20, por cable): el macro 17 se puso en modo 2 y
    un `macro_repeticiones` posterior lo devolvio a 0, deshaciendo la vuelta
    sin que nada lo avisara. Se vio recien en el diff del respaldo.

    El control ya se deshabilita fuera del modo 0; esto lo hace imposible
    **aunque se habilite por cualquier camino**, que es lo que hace falta
    cuando quien lo habilita es una relectura que puede venir vieja.
    """
    import copy
    from linshark import estructuras as est
    from linshark_ui.paneles.macros import PanelDeMacros
    from salvaguardas import MACRO_LEIDO

    def panel_con_modo(modo):
        estado = copy.deepcopy(_estado_falso())
        escrito = est.escribir_macro(bytes.fromhex(MACRO_LEIDO), modo=modo)
        estado["macros"]["17"]["datos"] = (
            escrito[:-2] + bytes([escrito[-1], escrito[-2]])).hex()
        panel = PanelDeMacros(_nombres_de_prueba())
        panel.poner_estado(estado)
        pedidos = []
        panel.pidio_escribir.connect(
            lambda c, v, i: pedidos.append((c, v, i)))
        return panel, pedidos

    # 1. En modo 2 (mantener apretado) no se escribe, y se dice por que.
    panel, pedidos = panel_con_modo(2)
    panel._al_poner_repeticiones()
    if pedidos:
        fallos.append(f"en modo 2 el boton escribio {pedidos!r}: eso cambia el "
                      "modo a 0 sin decirlo")
    if "modo" not in panel.avisos.text().lower():
        fallos.append(f"no explico por que no escribio: {panel.avisos.text()!r}")

    # 2. En modo 1 tampoco: el byte tampoco es un contador ahi.
    panel, pedidos = panel_con_modo(1)
    panel._al_poner_repeticiones()
    if pedidos:
        fallos.append(f"en modo 1 el boton escribio {pedidos!r}")

    # 3. Y en modo 0, que es donde el contador existe, sigue escribiendo.
    panel, pedidos = panel_con_modo(est.MACRO_MODO_CON_CONTADOR)
    panel._al_poner_repeticiones()
    if not pedidos or pedidos[0][0] != "macro_repeticiones":
        fallos.append(f"en modo 0 dejo de escribir las repeticiones: {pedidos!r}")


def test_la_tasa_prestada_se_ve_y_se_devuelve(fallos, app):
    """La ventana **dice** que el mouse esta a 1000 Hz prestado, y lo devuelve.

    Es la unica cosa que esta aplicacion cambia sin que se lo pidan, y se hace
    porque arriba de 1000 Hz los bloques largos no llegan (MEDIDO a 2000 y a
    8000). Lo que no se puede hacer es no decirlo: un mouse que quedo a un
    octavo de su tasa sin que su dueño se entere es la clase de sorpresa que
    este proyecto le reprocha a los dos clientes oficiales.
    """
    from linshark import estructuras as est
    from linshark_ui.ventana import Ventana

    mouse = _MouseFalso(hz=8000)
    hw = Hardware(device=mouse)
    ventana = Ventana(hw, _nombres_de_prueba())
    hw.conectar()
    hw.leer_estado()
    if not _correr_hasta(app, lambda: not ventana.tasa.isHidden(), segundos=40):
        fallos.append("la ventana no dijo que la tasa estaba prestada")
        hw.cerrar()
        return
    if "8000" not in ventana.tasa.texto.text():
        fallos.append(f"no dijo a cuanto vuelve: {ventana.tasa.texto.text()!r}")
    if est.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE]) != 1000:
        fallos.append("no bajo la tasa, asi que no pudo leer el mouse entero")

    # el boton la devuelve, y el cartel se va
    ventana.devolver_tasa()
    if not _correr_hasta(
            app,
            lambda: est.report_rate_de(
                mouse.bloques[p.CMD_REPORT_RATE]) == 8000, segundos=20):
        fallos.append("el boton no devolvio la tasa")
    if not _correr_hasta(app, lambda: ventana.tasa.isHidden(), segundos=5):
        fallos.append("el cartel siguio diciendo que la tasa estaba prestada")
    hw.cerrar()


def test_quedarse_con_la_tasa_prestada(fallos, app):
    """El otro camino del cartel: no me la devuelvas, me quedo en 1000.

    Lo pidio el usuario (2026-09-20). El cartel ofrecia **una sola** salida
    -devolver los 8000-, asi que quien se sienta a configurar y quiere quedarse
    en 1000 tenia que dejar que se los devolvieran y bajarlos de nuevo con
    `cambiar-rate.py`: dos reconfiguraciones de radio para terminar donde ya
    estaba.

    Las tres cosas que tiene que cumplir:

      1. **no le escribe nada al mouse**: ya esta a 1000, y mandar una trama
         para poner la tasa que ya esta reconfigura la radio de gusto;
      2. se apaga la deuda **y el reloj de gracia**, que si no la devolveria
         solo a los 90 s y desharia lo que se acaba de elegir;
      3. el cartel se va, porque ya no hay nada que avisar.
    """
    from linshark import estructuras as est
    from linshark_ui.ventana import Ventana

    mouse = _MouseFalso(hz=8000)
    hw = Hardware(device=mouse)
    ventana = Ventana(hw, _nombres_de_prueba())
    hw.conectar()
    hw.leer_estado()
    if not _correr_hasta(app, lambda: not ventana.tasa.isHidden(), segundos=40):
        fallos.append("la ventana no dijo que la tasa estaba prestada")
        hw.cerrar()
        return

    escrituras_antes = len(mouse.escrituras)
    ventana.tasa.quedarse.click()

    if not _correr_hasta(app, lambda: ventana.tasa.isHidden(), segundos=5):
        fallos.append("el cartel siguio diciendo que la tasa estaba prestada")
    if est.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE]) != 1000:
        fallos.append("la tasa dejo de estar en 1000, que es la que se eligio")
    if len(mouse.escrituras) != escrituras_antes:
        fallos.append(f"le escribio al mouse para dejarlo donde ya estaba: "
                      f"{mouse.escrituras[escrituras_antes:]!r}")
    if ventana._gracia.isActive():
        fallos.append("el reloj de gracia sigue andando: iba a devolver la "
                      "tasa sola y deshacer lo que se acaba de elegir")
    # 4. **Y la ventana se entera** de que el 1000 dejo de ser prestado: si
    #    no, "volver a como estaba" creeria que el mouse sigue en 8000.
    from linshark import modelo
    if sesion.CLAVE_TASA_BAJADA in ventana._estado:
        fallos.append("la ventana sigue creyendo que la tasa es prestada")
    faltan = modelo.pendientes(ventana._estado, ventana.conexion._de_al_abrir)
    if ("tasa", 1000, 8000) not in faltan:
        fallos.append(f"despues de quedarse en 1000, volver pide {faltan}")

    # Y cerrar la ventana **ya no la devuelve**, porque no se debe nada. Se le
    # da tiempo a que lo hiciera mal, y se mira despues: `_correr_hasta` no
    # sirve para esto -avisa por stderr cuando la condicion no se cumple, que
    # aca es justo lo que tiene que pasar-.
    hw.cerrar()
    fin = [False]
    QTimer.singleShot(1000, lambda: fin.__setitem__(0, True))
    while not fin[0]:
        app.processEvents()
    if est.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE]) != 1000:
        fallos.append("al cerrar devolvio una tasa que ya no debia")


def test_cerrar_la_ventana_devuelve_la_tasa(fallos, app):
    """Cerrar sin devolver la tasa seria dejarle al usuario un mouse cambiado."""
    from linshark import estructuras as est
    from linshark_ui.ventana import Ventana

    mouse = _MouseFalso(hz=8000)
    hw = Hardware(device=mouse)
    Ventana(hw, _nombres_de_prueba())
    hw.conectar()
    hw.leer_estado()
    if not _correr_hasta(
            app,
            lambda: est.report_rate_de(
                mouse.bloques[p.CMD_REPORT_RATE]) == 1000, segundos=40):
        fallos.append("no llego a bajar la tasa")
        hw.cerrar()
        return
    hw.cerrar()
    quedo = est.report_rate_de(mouse.bloques[p.CMD_REPORT_RATE])
    if quedo != 8000:
        fallos.append(f"cerrar dejo el mouse en {quedo} Hz, no en los 8000 "
                      "que tenia")


def test_la_primera_lectura_queda_en_la_maquina(fallos, app):
    """La primera lectura de cada apertura queda en disco, como un respaldo.

    Se reemplaza en cada apertura y no dentro de una: lo que se lee despues de
    una escritura ya no es "como estaba". Y sin ruta no se escribe nada, que es
    lo que deja a los demas tests fuera del HOME de quien los corre.
    """
    import copy
    import json
    import tempfile
    from linshark import lugares
    from linshark_ui.ventana import Ventana

    # La carpeta todavia no existe: la primera vez se crea.
    ruta = Path(tempfile.mkdtemp()) / "linshark" / "al-abrir.json"
    primero = _estado_falso()
    ventana = Ventana(Hardware(device=_MouseFalso()), _nombres_de_prueba(),
                      al_abrir=ruta)

    # 1. La primera lectura queda entera, con el formato de un respaldo.
    ventana.al_llegar_estado(primero)
    if not ruta.exists():
        fallos.append("la primera lectura no quedo en disco")
        return
    if json.loads(ruta.read_text(encoding="utf-8")) != json.loads(json.dumps(primero)):
        fallos.append("lo que quedo en disco no es el estado leido")

    # 2. Una lectura posterior, en la misma apertura, no la pisa.
    despues = copy.deepcopy(primero)
    despues["fecha"] = "despues de escribir"
    ventana.al_llegar_estado(despues)
    if json.loads(ruta.read_text(encoding="utf-8"))["fecha"] != primero["fecha"]:
        fallos.append("una relectura piso la lectura de al abrir")

    # 3. Otra apertura, si: es la que se reemplaza.
    otra = Ventana(Hardware(device=_MouseFalso()), _nombres_de_prueba(),
                   al_abrir=ruta)
    otra.al_llegar_estado(despues)
    if json.loads(ruta.read_text(encoding="utf-8"))["fecha"] != despues["fecha"]:
        fallos.append("otra apertura no reemplazo la lectura de al abrir")

    # 4. Sin ruta no se escribe nada.
    escritos = []
    original = lugares.guardar_estado
    lugares.guardar_estado = lambda estado, r: escritos.append(r)
    try:
        Ventana(Hardware(device=_MouseFalso()),
                _nombres_de_prueba()).al_llegar_estado(primero)
    finally:
        lugares.guardar_estado = original
    if escritos:
        fallos.append(f"una ventana sin ruta escribio en {escritos}")

    # 5. Si no se puede escribir, se configura igual: la carpeta es un archivo.
    trabada = Path(tempfile.mkdtemp()) / "un-archivo"
    trabada.write_text("", encoding="utf-8")
    muda = Ventana(Hardware(device=_MouseFalso()), _nombres_de_prueba(),
                   al_abrir=trabada / "al-abrir.json")
    try:
        muda.al_llegar_estado(primero)
    except Exception as exc:                       # noqa: BLE001
        fallos.append(f"no poder guardar tiro la ventana: {exc!r}")
    if not muda.conexion.como_estaba.isEnabled():
        fallos.append("sin poder guardar, 'volver a como estaba' no se habilito")

    # 6. Sin tasa prestada no se anota ninguna; con ella, a cuanto estaba. Por
    #    el camino entero -leer un mouse a 8000 Hz-, porque depende de que
    #    `Hardware` avise la tasa **antes** de emitir el estado.
    if "tasa_bajada_desde" in json.loads(ruta.read_text(encoding="utf-8")):
        fallos.append("sin tasa prestada, anoto una tasa_bajada_desde")
    rapida = Path(tempfile.mkdtemp()) / "al-abrir.json"
    mouse = _MouseFalso(hz=8000)
    hw = Hardware(device=mouse)
    ventana = Ventana(hw, _nombres_de_prueba(), al_abrir=rapida)
    hw.conectar()
    hw.leer_estado()
    try:
        if not _correr_hasta(app, rapida.exists, segundos=40):
            fallos.append("leyendo a 8000 Hz, la lectura no quedo en disco")
            return
        guardado = json.loads(rapida.read_text(encoding="utf-8"))
        if sesion.tasa_de(guardado) != 1000:
            fallos.append(f"el bloque de rate no es el leido: "
                          f"{sesion.tasa_de(guardado)} Hz")
        if guardado.get("tasa_bajada_desde") != 8000:
            fallos.append(f"no anoto a cuanto estaba la tasa: "
                          f"{guardado.get('tasa_bajada_desde')!r}")
    finally:
        ventana._gracia.stop()
        hw.cerrar()


def test_cambio_de_idioma(fallos, app):
    """El botón de idioma conmuta entre español, inglés y chino mandarín."""
    from linshark_ui import i18n
    from linshark_ui.ventana import Ventana

    # Aseguramos estado inicial en español
    i18n.fijar_idioma("es")

    mouse = _MouseFalso()
    hw = Hardware(device=mouse)
    ventana = Ventana(hw, _nombres_de_prueba())
    ventana.al_llegar_estado(_estado_falso())

    try:
        # 1. En español por defecto
        if ventana.conexion.boton_idioma.text() != "🌐 ES":
            fallos.append(f"el botón de idioma decía {ventana.conexion.boton_idioma.text()!r}, esperaba '🌐 ES'")
        if ventana.pestañas.tabText(0) != "Parámetros":
            fallos.append(f"pestaña 0 decía {ventana.pestañas.tabText(0)!r}, esperaba 'Parámetros'")
        if ventana.conexion.leer.text() != "Leer el mouse":
            fallos.append(f"botón leer decía {ventana.conexion.leer.text()!r}, esperaba 'Leer el mouse'")

        # 2. Cambiamos a inglés
        i18n.fijar_idioma("en")
        if ventana.conexion.boton_idioma.text() != "🌐 EN":
            fallos.append(f"en inglés el botón de idioma decía {ventana.conexion.boton_idioma.text()!r}")
        if ventana.pestañas.tabText(0) != "Parameters":
            fallos.append(f"en inglés pestaña 0 decía {ventana.pestañas.tabText(0)!r}")
        if ventana.pestañas.tabText(1) != "Macros":
            fallos.append(f"en inglés pestaña 1 decía {ventana.pestañas.tabText(1)!r}")
        if ventana.pestañas.tabText(2) != "Log":
            fallos.append(f"en inglés pestaña 2 decía {ventana.pestañas.tabText(2)!r}")
        if ventana.conexion.leer.text() != "Read mouse":
            fallos.append(f"en inglés botón leer decía {ventana.conexion.leer.text()!r}")
        if ventana.conexion.como_estaba.text() != "Revert to when opened":
            fallos.append(f"en inglés como_estaba decía {ventana.conexion.como_estaba.text()!r}")
        if ventana.conexion.seguros.text() != "Safe defaults":
            fallos.append(f"en inglés seguros decía {ventana.conexion.seguros.text()!r}")

        grupos = {cmd: g.title() for cmd, g in ventana.parametros._grupos.items()}
        if grupos.get(p.CMD_REPORT_RATE) != "Polling Rate":
            fallos.append(f"en inglés tasa decía {grupos.get(p.CMD_REPORT_RATE)!r}")
        if grupos.get(p.CMD_BUTTONS) != "Buttons and Scroll Wheel":
            fallos.append(f"en inglés botones decía {grupos.get(p.CMD_BUTTONS)!r}")

        # 3. Cambiamos a chino mandarín
        i18n.fijar_idioma("zh")
        if ventana.conexion.boton_idioma.text() != "🌐 中文":
            fallos.append(f"en chino el botón de idioma decía {ventana.conexion.boton_idioma.text()!r}")
        if ventana.pestañas.tabText(0) != "参数设置":
            fallos.append(f"en chino pestaña 0 decía {ventana.pestañas.tabText(0)!r}")
        if ventana.pestañas.tabText(1) != "宏管理":
            fallos.append(f"en chino pestaña 1 decía {ventana.pestañas.tabText(1)!r}")
        if ventana.pestañas.tabText(2) != "运行日志":
            fallos.append(f"en chino pestaña 2 decía {ventana.pestañas.tabText(2)!r}")
        if ventana.conexion.leer.text() != "读取鼠标":
            fallos.append(f"en chino botón leer decía {ventana.conexion.leer.text()!r}")
        if ventana.conexion.como_estaba.text() != "恢复打开时的状态":
            fallos.append(f"en chino como_estaba decía {ventana.conexion.como_estaba.text()!r}")
        if ventana.conexion.seguros.text() != "安全默认值":
            fallos.append(f"en chino seguros decía {ventana.conexion.seguros.text()!r}")

        grupos_zh = {cmd: g.title() for cmd, g in ventana.parametros._grupos.items()}
        if grupos_zh.get(p.CMD_REPORT_RATE) != "回报率":
            fallos.append(f"en chino tasa decía {grupos_zh.get(p.CMD_REPORT_RATE)!r}")
        if grupos_zh.get(p.CMD_BUTTONS) != "按键与滚轮":
            fallos.append(f"en chino botones decía {grupos_zh.get(p.CMD_BUTTONS)!r}")

        # 4. Volver a español
        i18n.fijar_idioma("es")
        if ventana.conexion.boton_idioma.text() != "🌐 ES":
            fallos.append(f"al volver a español botón decía {ventana.conexion.boton_idioma.text()!r}")
        if ventana.pestañas.tabText(0) != "Parámetros":
            fallos.append(f"al volver a español pestaña 0 decía {ventana.pestañas.tabText(0)!r}")
        if ventana.conexion.leer.text() != "Leer el mouse":
            fallos.append(f"al volver a español leer decía {ventana.conexion.leer.text()!r}")

    finally:
        i18n.fijar_idioma("es")
        ventana.close()
        hw.cerrar()


def test_las_plantillas_de_traduccion_cierran(fallos, app):
    """Cada fila dice lo mismo en los tres idiomas, variables incluidas.

    Una variable que falta en la traduccion revienta el `.format()`; una que
    sobra queda escrita con llaves. Y una clave sin nada fijo coincidiria con
    cualquier texto.
    """
    import re
    from linshark_ui import i18n
    variable = re.compile(r"\{(\w+)\}")
    vistas = set()
    for fila in i18n._TEXTOS:
        if len(fila) not in (3, 4):
            fallos.append(f"una fila tiene {len(fila)} columnas: {fila[0][:60]!r}")
            continue
        es, en, zh = fila[:3]
        if es in vistas:
            fallos.append(f"clave repetida: {es[:60]!r}")
        vistas.add(es)
        nombres = set(variable.findall(es))
        if len(fila) == 4:
            # lo que se muestra puede usar menos variables que la clave, pero
            # no otras: las que no esten en la clave no tienen valor
            if not set(variable.findall(fila[3])) <= nombres:
                fallos.append(f"la pantalla nombra variables que la clave no "
                              f"tiene: {fila[3][:60]!r}")
            nombres = set(variable.findall(fila[3]))
        for idioma, texto in (("en", en), ("zh", zh)):
            if set(variable.findall(texto)) != nombres:
                fallos.append(f"{idioma} no nombra las variables de "
                              f"{es[:60]!r}: {texto[:60]!r}")
        if nombres and not variable.sub("", es).strip():
            fallos.append(f"plantilla sin texto fijo: {es!r}")
        # Un `&` suelto en un boton o en un grupo es un atajo de teclado para
        # Qt: no se dibuja, y "Sensor & DPI" se leia "Sensor  DPI".
        for texto in fila:
            if re.search(r"(?<!&)&(?!&)", texto):
                fallos.append(f"un & que Qt se come: {texto[:60]!r}")


def _textos_de(raiz) -> set[str]:
    """Todo lo que se lee en pantalla: etiquetas, botones, listas, tooltips."""
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import (QAbstractButton, QComboBox, QGroupBox,
                                   QLabel, QLineEdit, QListWidget,
                                   QPlainTextEdit, QTabWidget, QWidget)
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    salida = set()
    for w in [raiz] + raiz.findChildren(QWidget):
        if isinstance(w, QLabel):
            salida.add(w.text())
        if isinstance(w, QAbstractButton):
            salida.add(w.text())
        if isinstance(w, QGroupBox):
            salida.add(w.title())
        if isinstance(w, QComboBox):
            salida |= {w.itemText(i) for i in range(w.count())}
        if isinstance(w, QTabWidget):
            salida |= {w.tabText(i) for i in range(w.count())}
        if isinstance(w, QListWidget):
            salida |= {w.item(i).text() for i in range(w.count())}
        if isinstance(w, (QLineEdit, QPlainTextEdit)):
            salida.add(w.placeholderText())
        if isinstance(w, QPlainTextEdit) and w.isReadOnly():
            salida |= set(w.toPlainText().splitlines())
        salida.add(w.toolTip())
        salida.add(w.windowTitle())
    return {s for s in salida if s}


def _recorrer_la_ventana(app, idioma: str) -> set[str]:
    """Una sesion entera en `idioma`, sin mouse: lo que se lee y lo que se avisa.

    Pasa por lo que llega del hilo de hardware de verdad -una lectura y una
    escritura con `_MouseFalso`- y por los mensajes que ese mouse no sabe
    provocar: la regla de udev, un modelo desconocido, cada motivo de
    `sesion.MOTIVOS`, los errores de lo que se escribe a mano.
    """
    import tempfile
    from linshark import dispositivos, estructuras as est
    from linshark.hidraw import FaltaLaReglaDeUdev, HidrawChannel
    from linshark_ui import i18n
    from linshark_ui.ventana import Ventana

    i18n.fijar_idioma(idioma)
    # Despues de cambiar y no antes: al cambiar se retraducen tambien las
    # ventanas que dejaron las pruebas anteriores, con sus mensajes de mentira.
    i18n.olvidar_faltantes()
    mouse = _MouseFalso()
    hw = Hardware(device=mouse)
    ventana = Ventana(hw, _nombres_de_prueba())
    textos = set()
    try:
        hw.conectar()
        hw.leer_estado(macros_extra=(17,))
        _correr_hasta(app, lambda: bool(ventana.parametros.filas()))
        listo = []
        hw.escritura_lista.connect(listo.append)
        # La tasa va por su propio camino (`Configuracion._escribir_tasa`) y
        # un boton por la Etapa 3 entera: con las dos pasan todos los avisos.
        for clave, valor in (("tasa", 500), ("boton_costado_adelante", "atras")):
            listo.clear()
            ventana.parametros.filas()[clave].editor.elegir(valor)
            _correr_hasta(app, lambda: bool(listo))
            _correr_hasta(app, lambda: ventana.parametros.filas()[clave]
                          .editor.isEnabled())

        # la regla de udev, con el mensaje que arma `HidrawChannel`
        cerrado = Path(tempfile.mkdtemp()) / "hidraw-sin-permiso"
        cerrado.write_bytes(b"")
        cerrado.chmod(0)
        try:
            HidrawChannel(cerrado).open()
        except FaltaLaReglaDeUdev as exc:
            ventana.al_haber_problema(str(exc), exc.comando)
        except PermissionError:
            pass                                   # corriendo como root
        for device_id in (99999, next(i for i in dispositivos.catalogo()
                                      if i not in dispositivos.PERFILES)):
            try:
                dispositivos.perfil_de(device_id)
            except dispositivos.ModeloDesconocido as exc:
                ventana.al_haber_problema(str(exc), "")
        textos |= _textos_de(ventana)

        # como puede salir una escritura, uno por uno
        for motivo in sesion.MOTIVOS:
            ventana.al_terminar_escritura(sesion.Resultado(False, motivo))
        for cambiaron in (frozenset(), frozenset({p.CMD_DPI})):
            v = sesion.Veredicto(True, "cambio-lo-pedido",
                                 ["dpi: uno de los dos no contesto (A)",
                                  "dpi.Current_Dpi_level_flag: 1 -> 2"],
                                 cambiaron, frozenset(),
                                 frozenset({p.CMD_LIGHTING, p.CMD_BUTTONS}))
            ventana.al_terminar_escritura(sesion.Resultado(
                True, "cambio-lo-pedido", veredicto=v, aplicada=False))
        for linea in (sesion.aviso_de_tasa_alta(8000, [p.CMD_DPI, p.CMD_BUTTONS]),
                      sesion.aviso_de_tasa_arreglada(0x02),
                      sesion.aviso_de_reintento([p.CMD_DPI], 3.0)):
            ventana.al_progresar(" ".join(linea.split()))
        ventana.al_cambiar_la_tasa_prestada(8000)
        ventana.al_haber_novedad(sesion.novedad_de(bytes([8, 0x10, 3, 0])))

        # la regla del clic izquierdo, con los dos mensajes que puede dar
        bloque = bytes.fromhex(
            ventana._estado["comandos"][str(p.CMD_BUTTONS)]["datos"])
        for slot, codigo in ((1, 3), (6, est.FUNCION_CLIC_IZQUIERDO)):
            try:
                est.escribir_boton(bloque, slot=slot, codigo=codigo)
            except est.SinClicIzquierdo as exc:
                ventana.al_haber_problema(str(exc), "")
                textos |= _textos_de(ventana.problema)
        listo.clear()
        ventana.parametros.acciones()["intercambiar_clics"].boton.click()
        _correr_hasta(app, lambda: bool(listo))

        # lo que se escribe a mano: un parametro que falta, pasos que no son
        fila = ventana.parametros.filas()["boton_costado_adelante"]
        fila.editor.elegir("macro")
        # el buscador de funciones: cada grupo, una busqueda y la que no
        # encuentra nada
        selector = fila.editor.abrir_selector()
        for i in range(selector.categorias.count()):
            selector.categorias.setCurrentRow(i)
            textos |= _textos_de(selector)
        for buscado in ("vol", "musica", "zzzz"):
            selector.buscar(buscado)
            textos |= _textos_de(selector)
        textos |= _textos_de(fila)
        selector.hide()
        for pasos in ("a:abajo@20000", "esto no es un paso", "xyz:abajo@10",
                      "a:abajo@10, a:arriba@10"):
            ventana.macros.eventos.setPlainText(pasos)
            textos |= _textos_de(ventana.macros)
        for atajo in ("", "ctrl", "ctrl+tecla-que-no-existe", "hyper+c"):
            try:
                est.atajo_desde_texto(atajo)
            except ValueError as exc:
                ventana.al_haber_problema(str(exc), "")
                textos |= _textos_de(ventana.problema)

        # los popups de ayuda y el dialogo de restaurar
        for f in ventana.parametros.filas().values():
            f.mostrar_ayuda()
        ventana.parametros.diagrama().mostrar_ayuda()
        from linshark import modelo
        ventana.dialogo_de_restauracion(
            modelo.pendientes(ventana._estado, modelo.SEGUROS), True)
        # los popups y el dialogo son hijos de la ventana: salen con ella
        textos |= _textos_de(ventana)
    finally:
        ventana.close()
        hw.cerrar()
        i18n.fijar_idioma("es")
        # Borrada de verdad: una ventana cerrada sigue viva, y la corrida del
        # idioma siguiente la encontraria entre sus widgets.
        from PySide6.QtCore import QCoreApplication, QEvent
        ventana.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    return textos


def test_no_queda_nada_sin_traducir(fallos, app):
    """En ingles y en chino no aparece ni un texto en castellano.

    Dos redes, porque cada una ve lo que la otra no: **lo que `tr()` no supo
    traducir** -un mensaje nuevo de la biblioteca que no esta en el
    diccionario- y **lo que no paso por `tr()`** -un texto que se muestra sin
    traducir-, que se encuentra comparando la pantalla en castellano con la
    pantalla en el otro idioma.
    """
    import re
    from linshark_ui import i18n
    # Lo que es igual en todos los idiomas y esta bien que lo sea: nombres
    # propios, identificadores, lo que escribe quien mira y sintaxis que el
    # parser lee en castellano.
    iguales = re.compile(
        r"^(LinShark|X8 Pro|Attack Shark X8 Pro|Macros?:?|LED on/off|DPI|LOD|"
        r"a:abajo@10, a:arriba@10|esto no es un paso|xyz:abajo@10|"
        r"a:abajo@20000|#[0-9a-f]{6}|🌐 \w+|Español|English|简体中文|"
        r"\d+ — macro \d+|/.*|\s*(sudo |udevadm ).*|"
        # la marca de un color: el nombre pasa por `tr()`, y si faltara su
        # traduccion lo diria la otra red; "magenta" es igual en ingles
        r"\S+ \(#[0-9a-f]{6}\))$")
    castellano = _recorrer_la_ventana(app, "es")
    for idioma in ("en", "zh"):
        otro = _recorrer_la_ventana(app, idioma)
        sin_traducir = {t for t in otro & castellano
                        if re.search(r"[^\W\d_]{3,}", t) and not iguales.match(t)}
        faltan = [t for t in i18n.faltantes() if not iguales.match(t)]
        i18n.olvidar_faltantes()
        for t in sorted(sin_traducir | set(faltan))[:15]:
            fallos.append(f"{idioma}: sin traducir: {t[:110]!r}")


def test_el_idioma_se_guarda(fallos, app):
    """El idioma elegido sobrevive a cerrar la aplicacion, y nada mas.

    Con las reglas de los nombres de macro: sin archivo arranca en castellano,
    un archivo ilegible no se pisa y un idioma desconocido no revienta.
    """
    import json
    import tempfile
    from linshark_ui import i18n, preferencias

    carpeta = Path(tempfile.mkdtemp())
    ruta = carpeta / "interfaz.json"
    prefs = preferencias.Preferencias(ruta)
    if prefs.idioma != "es":
        fallos.append(f"sin archivo arranco en {prefs.idioma!r}, no en 'es'")
    try:
        preferencias.usar(prefs)
        i18n.fijar_idioma("zh")
        if preferencias.Preferencias(ruta).idioma != "zh":
            fallos.append("cambiar el idioma no quedo guardado")
        i18n.fijar_idioma("es")
        preferencias.Preferencias(ruta).recordar_idioma("en")
        i18n.desregistrar_listener(prefs.recordar_idioma)
        i18n.fijar_idioma("es")
        nuevas = preferencias.Preferencias(ruta)
        preferencias.usar(nuevas)
        if i18n.idioma_actual() != "en":
            fallos.append("al arrancar no se puso el idioma guardado: "
                          f"{i18n.idioma_actual()!r}")
    finally:
        for p_ in (prefs, locals().get("nuevas")):
            if p_ is not None:
                i18n.desregistrar_listener(p_.recordar_idioma)
        i18n.fijar_idioma("es")

    raro = carpeta / "raro.json"
    raro.write_text(json.dumps({"idioma": "klingon"}), encoding="utf-8")
    if preferencias.Preferencias(raro).idioma != "es":
        fallos.append("un idioma desconocido no se ignoro")

    roto = carpeta / "roto.json"
    roto.write_text("{esto no es json", encoding="utf-8")
    p_roto = preferencias.Preferencias(roto)
    p_roto.recordar_idioma("en")
    if roto.read_text(encoding="utf-8") != "{esto no es json":
        fallos.append("se escribio encima de un archivo que no se pudo leer")


def main() -> int:
    app = QApplication.instance() or QApplication([])
    pruebas = [
        ("el hilo no toca la ventana", test_el_hilo_no_toca_la_ventana),
        ("una escritura pasa por la Etapa 3", test_una_escritura_pasa_por_la_etapa_3),
        ("un respaldo incompleto no escribe", test_un_respaldo_incompleto_no_escribe),
        ("los problemas traen su arreglo", test_los_problemas_traen_su_arreglo),
        ("un error no mata el hilo", test_un_error_no_mata_el_hilo),
        ("cerrar espera a lo que esta en vuelo",
         test_cerrar_espera_a_lo_que_esta_en_vuelo),
        ("cerrar no espera para siempre, y lo dice",
         test_cerrar_no_espera_para_siempre),
        ("las novedades llegan", test_las_novedades_llegan),
        ("un mouse que no es el medido se avisa",
         test_un_mouse_que_no_es_el_medido_se_avisa),
        ("los avisos se dicen en castellano", test_los_avisos_se_dicen_en_castellano),
        ("la pantalla se arma sola", test_la_pantalla_se_arma_sola),
        ("cada nivel de dpi se ve de su color",
         test_cada_nivel_de_dpi_se_ve_de_su_color),
        ("el rgb que no enciende nada no se ofrece",
         test_el_rgb_que_no_enciende_nada_no_se_ofrece),
        ("la rueda no cambia un desplegable",
         test_la_rueda_no_cambia_un_desplegable),
        ("el esquema de botones acompaña a las filas",
         test_el_esquema_de_botones),
        ("restaurar escribe solo lo que hace falta",
         test_restaurar_escribe_solo_lo_que_hace_falta),
        ("la ventana no conoce ningun campo",
         test_la_ventana_no_conoce_ningun_campo),
        ("mover un control pide esa escritura",
         test_mover_un_control_pide_esa_escritura),
        ("una funcion con parametro pide el parametro",
         test_una_funcion_con_parametro_pide_el_parametro),
        ("las funciones se buscan y se agrupan",
         test_las_funciones_se_buscan_y_se_agrupan),
        ("el clic izquierdo no se pierde desde la ventana",
         test_el_clic_izquierdo_no_se_pierde_desde_la_ventana),
        ("los botones se leen claro", test_los_botones_se_leen_claro),
        ("la ayuda dice que es cada parametro",
         test_la_ayuda_dice_que_es_cada_parametro),
        ("cada boton lleva su numero", test_cada_boton_lleva_su_numero),
        ("leer pide mover el mouse", test_leer_pide_mover_el_mouse),
        ("las advertencias del macro se ven antes de grabar",
         test_las_advertencias_del_macro_se_ven_antes_de_grabar),
        ("el modo sin medir se dice", test_el_modo_sin_medir_se_dice),
        ("el grabador arma pasos que la biblioteca acepta",
         test_el_grabador_arma_pasos_que_la_biblioteca_acepta),
        ("grabar un macro pasa por la biblioteca",
         test_grabar_un_macro_pasa_por_la_biblioteca),
        ("la ventana escribe y se bloquea mientras",
         test_la_ventana_escribe_y_se_bloquea_mientras),
        ("la ventana ofrece el arreglo de udev",
         test_la_ventana_ofrece_el_arreglo_de_udev),
        ("la bateria dice cuando dejo de llegar",
         test_la_bateria_dice_cuando_dejo_de_llegar),
        ("el dpi que cambia solo no se muestra al reves",
         test_el_dpi_que_cambia_solo_no_se_muestra_al_reves),
        ("cerrar la ventana baja el hilo",
         test_cerrar_la_ventana_baja_el_hilo),
        ("dos escrituras no se encinan", test_dos_escrituras_no_se_encinan),
        ("un problema ajeno no desbloquea la pantalla",
         test_un_problema_ajeno_no_desbloquea_la_pantalla),
        ("cambiar de macro cambia los pasos",
         test_cambiar_de_macro_cambia_los_pasos),
        ("un pedido que no entra no deja la pantalla muerta",
         test_un_pedido_que_no_entra_no_deja_la_pantalla_muerta),
        ("una escritura fallida no deja el valor pedido en pantalla",
         test_una_escritura_fallida_no_deja_el_valor_pedido_en_pantalla),
        ("el deslizador no ofrece lo que el mouse no guarda",
         test_el_deslizador_no_ofrece_lo_que_el_mouse_no_guarda),
        ("el teclado numerico se graba como el numerico",
         test_el_teclado_numerico_se_graba_como_el_numerico),
        ("una tecla que no entra se dice",
         test_una_tecla_que_no_entra_se_dice),
        ("una escritura que revienta antes tambien restaura",
         test_una_escritura_que_revienta_antes_tambien_restaura),
        ("una lectura incompleta dice el motivo que corresponde",
         test_una_lectura_incompleta_dice_el_motivo_que_corresponde),
        ("escribir la tasa arriba de 1000 entra y se queda",
         test_escribir_la_tasa_arriba_de_1000_entra_y_se_queda),
        ("la ventana dice donde esta el mouse",
         test_la_ventana_dice_donde_esta_el_mouse),
        ("la ventana abre el cable",
         test_la_ventana_abre_el_cable),
        ("el aviso del nivel se va con el nivel nuevo",
         test_el_aviso_del_nivel_se_va_con_el_nivel_nuevo),
        ("un macro sin contador se muestra",
         test_un_macro_sin_contador_se_muestra),
        ("las repeticiones no cambian el modo a escondidas",
         test_las_repeticiones_no_cambian_el_modo_a_escondidas),
        ("la tasa prestada se ve y se devuelve",
         test_la_tasa_prestada_se_ve_y_se_devuelve),
        ("quedarse con la tasa prestada",
         test_quedarse_con_la_tasa_prestada),
        ("cerrar la ventana devuelve la tasa",
         test_cerrar_la_ventana_devuelve_la_tasa),
        ("el respaldo no se relee en cada escritura",
         test_el_respaldo_no_se_vuelve_a_leer_en_cada_escritura),
        ("la primera lectura queda en la maquina",
         test_la_primera_lectura_queda_en_la_maquina),
        ("el cambio de idioma actualiza la interfaz",
         test_cambio_de_idioma),
        ("las plantillas de traduccion cierran",
         test_las_plantillas_de_traduccion_cierran),
        ("no queda nada sin traducir", test_no_queda_nada_sin_traducir),
        ("el idioma se guarda", test_el_idioma_se_guarda),
    ]
    malos = 0
    for nombre, prueba in pruebas:
        fallos: list[str] = []
        try:
            prueba(fallos, app)
        except Exception as exc:                   # noqa: BLE001
            fallos.append(f"revento: {type(exc).__name__}: {exc}")
        if fallos:
            malos += 1
            print(f"FALLA  {nombre}")
            for f in fallos:
                print(f"         - {f}")
        else:
            print(f"ok     {nombre}")
    print()
    print("todo en orden" if malos == 0 else f"{malos} prueba(s) con problemas")
    return 1 if malos else 0


if __name__ == "__main__":
    raise SystemExit(main())
