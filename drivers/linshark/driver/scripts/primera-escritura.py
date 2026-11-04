#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""La Etapa 3 de `dev/docs/metodo.md`: la primera escritura real, entera.

No es "mandar un byte". Es el procedimiento completo, en el orden que la
etapa fija, porque cada paso existe para poder responder una pregunta si algo
sale mal:

  1. respaldo fresco, y se exige que este COMPLETO (los siete comandos)
  2. leer el valor actual del comando que se va a escribir
  3. armar la escritura de **ese mismo valor**, y mostrarla
  4. confirmar por terminal
  5. escribir, y mirar si llega el acuse 0xC1 del dongle
  6. releer todo y comparar contra el respaldo: **nada** puede haber cambiado

El truco de la etapa es el paso 3. Si el formato esta bien, el mouse lo acepta
y no cambia nada. Si esta mal, lo ignora y tampoco cambia nada. En los dos
casos el mouse queda como estaba, y lo que se aprende es si el framing sirve,
mirando el acuse. Es la unica forma de probar una escritura sin apostar el
hardware.

    driver/scripts/primera-escritura.py --comando rate
    driver/scripts/primera-escritura.py --comando rate --valor 500      # cambio real
    driver/scripts/primera-escritura.py --comando dpi
    driver/scripts/primera-escritura.py --comando dpi --nivel 1 --valor 1600
    driver/scripts/primera-escritura.py --comando luz
    driver/scripts/primera-escritura.py --comando luz --hibernacion 1    # cambio real
    driver/scripts/primera-escritura.py --comando luz --respuesta 12
    driver/scripts/primera-escritura.py --comando luz --reposo 1     # el otro reposo
    driver/scripts/primera-escritura.py --comando luz --color 0000ff
    driver/scripts/primera-escritura.py --comando botones --boton costado-adelante \\
        --funcion macro --macro-id 17
    driver/scripts/primera-escritura.py --comando macro --macro-id 17
    driver/scripts/primera-escritura.py --comando macro --macro-id 17 --modo 2

Sin un valor la escritura es idempotente, y conviene empezar siempre por ahi.
El dpi ademas necesita `--nivel`, porque el bloque trae los ocho a la vez y se
cambia uno solo.

`--comando macro` es cmd 9, y es distinto de todos los demas en tres cosas:

  * **se lee con el id del macro en el byte 5**, donde los otros llevan el
    perfil, asi que `--macro-id` es obligatorio y sin el el mouse devuelve un
    bloque vacio;
  * **va partido en dos tramas** (59 + 52), con ~1 s en el medio en que el
    mouse tiene medio bloque. Es el unico camino multi-bloque del proyecto;
  * **su escritura idempotente no es devolver el bloque leido**: el mouse
    devuelve el checksum interno con los bytes al reves, asi que el
    codificador lo rearma en big-endian.

Y cambia el **disparo** del macro, no sus eventos: grabar un macro es otra
cosa y no esta en esta herramienta. `--modo` tiene los tres valores que el
soft nativo escribio en el bus, y `--repeticiones` solo existe en el modo 0,
que es el unico con contador.

`--comando luz` es el bloque de cmd 5, que **no es solo la luz**: lleva el
tiempo de hibernacion y el de respuesta de la pantalla de parametros. Cada
campo tiene su opcion y **va uno por corrida**, porque el ciclo de la Etapa 4
es cambio chico / verificacion / vuelta atras, y dos cambios juntos rompen la
verificacion.

**El X8 Pro tiene DOS temporizadores de reposo, no uno**, y viajan en bytes
distintos del mismo bloque: `--reposo` es el corto (`Level1SleepTimer` en la
web, `Sleep Time:` en el soft nativo) y `--hibernacion` el largo (`SleepTimer`,
`Deep Sleep Time:`). Estan anidados: el largo empieza a contar cuando entra el
corto.

Los dos tienen verificacion externa, y por el mismo instrumento
(`driver/scripts/medir-hibernacion.py`, que no le escribe un byte al mouse):

  * `--hibernacion` mueve **el corte** del latido, y la unidad quedo MEDIDA
    con una palanca de 10x: `corte = 30 s + N x 60 s`, predicho 90 y
    medido [88, 92] para N=1, predicho 630 y medido [628.9, 632.9] para N=10.
  * `--reposo` mueve **el escalon** del latido, de 2.00 s a 4.00 s. El mouse
    esta en 0.5 min y el escalon cae a los ~32 s.

`--color` **no enciende nada** en el X8 Pro (medido),
`--respuesta` es el tiempo de respuesta de los botones y no tiene verificacion
por software, y los campos que no tienen opcion -brillo, modo, velocidad- es
porque comparten byte o cambian de significado segun que pantalla oficial los
escribio. Ver la nota de `ILUMINACION` en
`driver/src/linshark/estructuras.py`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from linshark import dpi as mod_dpi                      # noqa: E402
from linshark import estructuras as est                  # noqa: E402
from linshark import lugares                              # noqa: E402
from linshark import protocol as p                       # noqa: E402
from linshark.device import Device                        # noqa: E402
from linshark.hidraw import (DeviceNotFound,              # noqa: E402
                             HidrawChannel,
                             find_config_hidraw, verificar_nodo_dongle)

from linshark import nombres                              # noqa: E402
from linshark import sesion                               # noqa: E402


class _Aborta(Exception):
    """Corta la corrida desde adentro del codificador, con su codigo de salida.

    El codificador corre como callback de `sesion.aplicar()`, asi que no puede
    hacer `return` de `main()`. El mensaje ya se imprimio donde se detecto el
    problema: esto solo lleva el numero con el que hay que salir.
    """

    def __init__(self, codigo: int = 1):
        super().__init__(codigo)
        self.codigo = codigo


#: Donde van los dos respaldos de cada corrida. Es una constante de modulo y
#: no algo calculado adentro para que una corrida de prueba pueda apuntarla a
#: un directorio temporal: un test que escribe en la carpeta de verdad deja
#: basura entre los respaldos de quien usa el programa.
CARPETA_RESPALDOS = lugares.respaldos()

# Los mismos que `p.WRITABLE`, con nombre. Si alguien agrega uno aca sin que
# haya pasado la Etapa 2, el backend lo rechaza igual.
COMANDOS = {"rate": p.CMD_REPORT_RATE, "dpi": p.CMD_DPI,
            "luz": p.CMD_LIGHTING, "botones": p.CMD_BUTTONS,
            "macro": p.CMD_MACRO}

BATERIA_MINIMA = 50


# --- que se puede hacer para comprobarlo por fuera -------------------------
# Es una funcion pura y no un `if` adentro de `main()` **por un bug**: los
# interruptores del sensor entraron por `--comando dpi` y
# cayeron en la rama escrita para el nivel de dpi, que usa variables que solo
# existen si se escribio un nivel. Reventó con `UnboundLocalError` **despues**
# de haber escrito y releido, o sea que la escritura salio bien y el resumen de
# que cambio no se llego a imprimir.
#
# Aca abajo el despacho es **total**: cada combinacion tiene su rama y hay un
# `else` que no depende de ninguna variable condicional. Y al ser pura,
# `test_consejo_de_verificacion` la llama con todas las combinaciones que el
# CLI acepta y comprueba que ninguna revienta ni sale vacia, que es lo que
# habria agarrado el bug.
#
# Cada comando tiene su verificacion externa, y no son la misma. medir-polling
# mide la TASA DE REPORTE, que no cambia al mover el dpi: sugerirla ahi seria
# dar una confirmacion que no confirma nada.
#
# Para el dpi no hay un equivalente barato. Medirlo de verdad exige mover el
# mouse una distancia fisica conocida, y eso a mano no sale: se probo y dio
# entre 41 y 2545 dpi para un mouse que estaba en 1600 (ver
# dev/models/attackshark-x8pro/docs/bitacora.md). El lector independiente que si sirve es la pagina oficial,
# que es software del fabricante leyendo los mismos bytes sin pasar por nuestro
# decodificador -salvo para los cuatro interruptores, que los lee mal-.

# El byte de repeticiones de un macro **solo es un contador cuando el modo es
# 0**, asi que `parametros_de_macro()` devuelve None en los otros dos: leerlo
# como repeticiones ahi seria inventar un dato. Bien para el decodificador, y
# una trampa para el mensaje del paso 3, que imprimio
#
#     CAMBIO REAL: macro 17, modo reproducir N veces -> mantener apretado
#                  y repeticiones 1 -> None
#
# con el byte de repeticiones **sin moverse**: sigue en 1 en los dos bloques.
# Lo que se fue no es el numero, es su significado, y anunciarlo como "1 ->
# None" dice que cambio un valor que no cambio. Va aparte y es pura por el
# mismo motivo que `consejo_de_verificacion()`: asi se prueba sin un mouse
# enfrente.

def describir_cambio_de_macro(antes: dict, despues: dict, macro_id: int) -> str:
    """La linea del paso 3 para cmd 9. Devuelve texto, no imprime."""
    con_contador = despues["modo"] == est.MACRO_MODO_CON_CONTADOR
    partes = []

    def _pasos(m):
        return [(e["usageId"], e["direccion"], e["tiempo"])
                for e in m["eventos"]]

    # Los eventos van primero porque son el cambio grande: grabar un macro
    # reemplaza la lista entera, y el diff del paso 6 va a mostrar cincuenta
    # bytes moviendose. Se dice cuantos eran, cuantos son y como quedan.
    if _pasos(antes) != _pasos(despues):
        partes.append(
            f"{len(antes['eventos'])} eventos -> {len(despues['eventos'])}: "
            + est.texto_de_eventos(despues["eventos"]))
    if antes["modo"] != despues["modo"]:
        cambio = f"modo {antes['modoNombre']} -> {despues['modoNombre']}"
        # Al entrar al modo 0 el contador pasa a significar algo, asi que se
        # dice cuanto vale; no de donde viene, porque antes no era un contador.
        if con_contador:
            cambio += f", {despues['repeticiones']} repeticion(es)"
        partes.append(cambio)
    elif con_contador and antes["repeticiones"] != despues["repeticiones"]:
        partes.append(f"repeticiones {antes['repeticiones']} -> "
                      f"{despues['repeticiones']}")
    if not partes:
        return (f"IDEMPOTENTE (macro {macro_id}, el mismo disparo con el "
                "checksum rearmado)")
    return f"CAMBIO REAL: macro {macro_id}, " + " y ".join(partes)


# **Las dos barandas que dejo**, las dos avisando y ninguna
# prohibiendo: un macro de un solo evento y uno que deja algo apretado son
# justo los dos experimentos que cerraron la direccion de los eventos, asi que
# prohibirlos seria tirar el instrumento. Lo que no se hace es mandarlos sin
# decir lo que va a pasar ni como se sale.
#
# **Van antes de confirmar, no en el consejo del paso 6.** Un aviso de "esto te
# va a trabar el teclado" que llega despues de escribir no es un aviso, es una
# explicacion. Y decirlo dos veces gastaria la alarma, que en este proyecto es
# la unica red que hay.
def advertencias_de_eventos(eventos) -> list[str]:
    """Lo que hay que saber ANTES de mandar esta lista de eventos al mouse."""
    lineas: list[str] = []
    if len(eventos) < est.MACRO_EVENTOS_MIN_QUE_CORRE:
        lineas += [
            f"      OJO: un macro de {len(eventos)} evento NO SE REPRODUCE "
            "(MEDIDO, en las",
            "      dos direcciones). El mouse lo guarda y la relectura lo "
            "devuelve bien, pero al",
            "      apretar el boton no pasa nada. Con dos eventos si sale.",
        ]
    sin_cerrar = est.eventos_sin_cerrar(eventos)
    if sin_cerrar:
        quienes = ", ".join(est.nombre_de_evento(u) for u in sin_cerrar)
        lineas += [
            f"      OJO: este macro deja APRETADO lo que no cierra: {quienes}.",
            "      El firmware no suelta nada al terminar (MEDIDO), asi "
            "que eso queda",
            "      trabado en el sistema cada vez que se apriete el boton, y "
            "con una tecla trabada",
            "      el teclado deja de escribirla.",
            f"      Para despegarlo, {est.MACRO_REMEDIO_TECLA_TRABADA}.",
        ]
    return lineas


def consejo_de_verificacion(cmd: int, *, rgb=None, sensor=None, nivel=None,
                            en_la_pagina=None, efectivo=None,
                            nivel_activo=None, eventos=None, atajo=None,
                            respaldo: str = "") -> list[str]:
    """Las lineas de "y ahora como comprobas que esto hizo algo".

    Devuelve texto, no imprime: asi se puede probar sin un mouse enfrente.
    """
    sensor = sensor or {}
    volver = [f"      Para volver atras, el valor previo esta en el respaldo: "
              f"{respaldo}"] if respaldo else []

    if cmd == p.CMD_REPORT_RATE:
        return ["      Verificalo por fuera del protocolo, que no depende de "
                "creerle al mouse:",
                "        driver/scripts/medir-polling.py --segundos 15"]

    if cmd == p.CMD_LIGHTING and rgb is None:
        return ["      Verificacion externa, la unica que tiene cmd 5:",
                "        driver/scripts/medir-hibernacion.py --minutos N --nota "
                "\"que valor quedo escrito\"",
                "      Mové el mouse al arrancar, para anclar la quietud, y "
                "dejalo quieto al menos",
                "      el doble de lo que esperás que tarde."] + volver

    if cmd == p.CMD_LIGHTING:
        # **No hay verificacion por el LED, y hay que decirlo.** El plan de
        # etapas decia "reversible y visible a simple vista (el LED)" desde antes de
        # la primera escritura de luz. Se probo y **no se ve
        # nada**: el X8 Pro no enciende un LED con estos bytes. Prometer una
        # verificacion que no existe es peor que no ofrecer ninguna, porque el
        # "no vi nada" se lee como fracaso cuando la escritura salio bien.
        color = (f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}" if rgb else "el color")
        return ["      NO hay verificacion por el LED: en el X8 Pro estos "
                "bytes no encienden nada",
                "      visible (MEDIDO). Lo que tenés es la "
                "relectura de arriba.",
                "      Un lector independiente, que no pasa por nuestro "
                "decodificador:",
                "        ./linshark --backend hidraw --mode read",
                f"        y abrí la web oficial, a ver si muestra {color}."
                ] + volver

    if cmd == p.CMD_MACRO and eventos is not None:
        # Grabar tiene la misma verificacion que el disparo -apretar el boton-
        # pero lo que hay que mirar es otra cosa: que salga la secuencia, y no
        # como termina. Y el macro tambien tiene que estar asignado.
        largos = est.cuantos_largos(eventos)
        propio = [
            "      Este se verifica apretando el boton, y lo que hay que "
            "mirar es que salga la",
            "      secuencia entera y en orden. El macro tiene que estar "
            "asignado a un boton:",
            "        driver/scripts/primera-escritura.py --comando botones "
            "--boton NOMBRE \\",
            "            --funcion macro --macro-id N",
            "      Con teclas se ve en cualquier editor de texto; con "
            "clics, en la seleccion",
            "      primaria: el clic de rueda pega lo que haya seleccionado, "
            "y asi se contaron",
            "      las ocho vueltas del modo 2 -el conteo lo "
            "hizo el sistema",
            "      operativo, no nuestro decodificador-.",
            "      El orden es el que se escribe: `dir0` aprieta y `dir1` "
            "suelta, MEDIDO",
            "      con un macro de dos eventos `dir0` que dejo las "
            "dos teclas apretadas.",
        ]
        if largos:
            cuantos = (
                f"un evento pasa de {est.MACRO_TIEMPO_CORTO_MAX} ms y se arma"
                if largos == 1 else
                f"{largos} eventos pasan de {est.MACRO_TIEMPO_CORTO_MAX} ms "
                "y se arman")
            propio += [
                f"      OJO: {cuantos} con la rama de cuatro bytes,",
                "      que esta INFERIDA del bundle y ninguna captura mostro. "
                "Si el macro sale con",
                "      los tiempos raros, empezá por ahi: dev/models/attackshark-x8pro/docs/evidencia.md "
                "lo tiene anotado.",
            ]
        return propio + volver

    if cmd == p.CMD_MACRO:
        # Tambien se verifica apretando el boton, pero con un paso previo que
        # no tiene ningun otro comando: el macro tiene que estar ASIGNADO a
        # alguno. Un macro huerfano se puede escribir y releer sin que nada de
        # lo que hace se pueda comprobar.
        #
        # Y los tres modos se distinguen a simple vista, que es lo que hace
        # falta para que esto sea verificacion externa y no una relectura:
        # el 0 lo reproduce N veces y para solo, el 1 sigue hasta que se toque
        # una tecla, y el 2 corre mientras el boton este apretado.
        #
        # El 0 y el 2 quedaron MEDIDOS con el mismo macro y el
        # mismo boton -una vuelta contra ocho en bucle, unica variable el byte
        # [3]-. **El 1 no**: sigue con el 0xC1 y la relectura.
        return ["      Este se verifica apretando el boton, pero primero el "
                "macro tiene que estar",
                "      asignado a uno:",
                "        driver/scripts/primera-escritura.py --comando botones "
                "--boton NOMBRE \\",
                "            --funcion macro --macro-id N",
                "      Despues apretalo y mirá COMO termina, que es lo que "
                "distingue los tres modos:",
                "        0  lo reproduce N veces y para solo",
                "        1  sigue hasta que toques cualquier tecla",
                "        2  corre mientras lo tengas apretado, y para al "
                "soltarlo"] + volver

    if cmd == p.CMD_BUTTONS and atajo is not None:
        # El atajo se verifica apretando el boton, como cualquier remapeo,
        # pero el "hace lo nuevo" es concreto: tiene que llegar esa
        # combinacion de teclas. Y eso se puede ver sin creerle a nadie.
        return ["      Este se verifica apretando el boton: tiene que llegar "
                f"{atajo} al sistema.",
                "      Con `wev`, `xev` o `showkey` se ven las teclas que "
                "entran, y ahi se distingue",
                "      un atajo que llego de uno que el escritorio se comio "
                "(Win+D lo atiende el",
                "      gestor de ventanas, por ejemplo).",
                "      Los dos bytes del slot son la mascara de modificadores "
                "y el usage HID, y la",
                "      relectura de arriba los muestra."] + volver

    if cmd == p.CMD_BUTTONS:
        # Este SI se verifica apretando el boton, y es la verificacion mas
        # barata del proyecto despues del LOD. La rueda ya se midio girandola
        # los dos ordenes.
        return ["      Este se verifica a simple vista: apretá el boton y "
                "fijate si hace lo nuevo.",
                "      Y la relectura de arriba lo muestra en la numeracion "
                "de LECTURA, que NO es",
                "      la que se escribe: los slots 4, 5 y 6 se remapean "
                "(MEDIDO),",
                "      y por eso este comando no reescribe lo que lee sino "
                "que lo traduce."] + volver

    if cmd == p.CMD_DPI and nivel_activo is not None:
        # **Cuarta verificacion a simple vista del proyecto**, despues del LOD
        # y de los dos ordenes de la rueda. Los ocho colores de indicador
        # viajan en este mismo bloque y el LED de nivel es el unico que prende
        # en este modelo: los bytes de color de cmd 5 no encienden nada.
        return ["      Este SI se verifica a simple vista: mirá el indicador "
                "de nivel del mouse.",
                f"      Tiene que quedar en el color del nivel {nivel_activo}, "
                "que viaja en este mismo",
                "      bloque (cmd 4 trae los ocho colores, uno por nivel).",
                "      Y el puntero cambia de velocidad, que es la otra mitad: "
                "cada nivel tiene",
                "      su dpi."] + volver

    if cmd == p.CMD_DPI and sensor:
        # Los cuatro interruptores. Se los separa del nivel de dpi porque
        # comparten comando pero no verificacion, y porque la pagina oficial
        # **no sirve como lector independiente aca**: lee estos bytes mal (ver
        # la nota de `parametros_de_sensor` en estructuras.py).
        if "lod" in sensor:
            propio = ["      Este SI se verifica a simple vista, y es el unico "
                      "del proyecto:",
                      "      levantá el mouse despacio sobre el mismo apoyo y "
                      "fijate a que altura",
                      "      deja de mover el puntero. Con 2 mm tiene que "
                      "seguir mas arriba que con 1 mm."]
        else:
            propio = ["      NO hay verificacion externa barata para este "
                      "campo. Lo que tenés es el",
                      "      acuse 0xC1 y la relectura de arriba: dicen que el "
                      "mouse lo guardo, no que",
                      "      haga algo distinto."]
        return propio + [
            "      Y la pagina oficial NO sirve de lector independiente para "
            "estos cuatro:",
            "      lee el byte entero contra 1, con los campos cruzados, y ni "
            "siquiera lee",
            "      de vuelta el LOD ni el motion sync."] + volver

    if cmd == p.CMD_DPI and nivel is not None and en_la_pagina is not None:
        return ["      La relectura de arriba ya lo confirma. Si querés un "
                "lector independiente:",
                "        ./linshark --backend hidraw --mode read",
                f"        y abrí la web oficial. Va a mostrar {en_la_pagina} "
                f"en el nivel {nivel}, no {efectivo}: lee con otra formula.",
                "        OJO: la pagina, apenas se conecta, INTENTA reescribir "
                "el dpi. En modo read se bloquea."]

    # Rama de seguridad: un campo nuevo deberia traer su propio consejo, pero
    # caer aca **no puede romper el informe**. Es el bug.
    return ["      La relectura de arriba ya lo confirma. Si querés un lector "
            "independiente:",
            "        ./linshark --backend hidraw --mode read"] + volver


async def main(argv=None, *, device=None, nodo=None) -> int:
    """La corrida entera. `device` y `nodo` existen para poder probarla.

    **Sin ellos se comporta igual que siempre**: abre el nodo del dongle, lo
    verifica y lo cierra al terminar. Con ellos usa el device que le den y no
    toca ningun archivo, que es lo que deja correr la Etapa 3 completa contra
    un mouse falso en `driver/tests/salvaguardas.py`. Es la unica forma de que un
    cambio en esta coreografia -la herramienta con la que se toca el hardware-
    tenga una red que no sea el mouse de verdad.
    """
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comando", choices=sorted(COMANDOS), required=True)
    ap.add_argument("--hidraw", type=Path)
    ap.add_argument("--valor", type=int, metavar="N",
                    help="con --comando rate, la frecuencia en Hz; con dpi, el "
                         "dpi del nivel que diga --nivel. Sin esto la escritura "
                         "es idempotente, que es como hay que empezar")
    ap.add_argument("--nivel", type=int, metavar="N",
                    help="solo con --comando dpi: cual de los ocho niveles se "
                         "cambia, 1 a 8 como en la pagina oficial")
    ap.add_argument("--color", metavar="RRGGBB",
                    help="solo con --comando luz: el color en hexadecimal, "
                         "p.ej. 0000ff. OJO: en el X8 Pro estos bytes no "
                         "encienden nada (medido)")
    ap.add_argument("--hibernacion", type=int, metavar="N",
                    help=f"solo con --comando luz: tiempo de hibernacion, "
                         f"{est.HIBERNACION_MIN} a {est.HIBERNACION_MAX} "
                         "minutos, MEDIDO: el corte del latido cae en "
                         "30 + N*60 s, verificado en N=1 y N=10. Campo de "
                         "cmd 5 con verificacion externa: medir-hibernacion.py")
    ap.add_argument("--respuesta", type=int, metavar="N",
                    help=f"solo con --comando luz: tiempo de respuesta, "
                         f"{est.RESPUESTA_MIN} a {est.RESPUESTA_MAX} (la UI "
                         f"oficial muestra el doble, "
                         f"{est.RESPUESTA_UI_MIN}..{est.RESPUESTA_UI_MAX})")
    ap.add_argument("--lod", type=int, metavar="MM", choices=(1, 2),
                    help="solo con --comando dpi: altura de corte **en "
                         "milimetros**, 1 o 2, que son las dos opciones del "
                         "radio oficial. El campo viaja como 0/1; la traduccion "
                         "la hace estructuras.lod_desde_mm(). Es el unico campo "
                         "del proyecto con verificacion a simple vista: se "
                         "levanta el mouse y se cambia el ajuste sin bajarlo")
    ap.add_argument("--nivel-activo", type=int, metavar="N",
                    help="solo con --comando dpi: cual de los ocho niveles "
                         "queda EN USO. No cambia ningun valor de dpi: mueve "
                         "un byte, `Current_Dpi_level_flag`. Es el unico campo "
                         "con indicador propio -el LED de nivel cambia de "
                         "color- y el driver oficial lo escribio con seis "
                         "valores distintos")
    ap.add_argument("--ripple", type=int, metavar="0|1", choices=(0, 1),
                    help="solo con --comando dpi: control de ripple")
    ap.add_argument("--angle-snapping", type=int, metavar="0|1", choices=(0, 1),
                    help="solo con --comando dpi: correccion de angulo")
    ap.add_argument("--motion-sync", type=int, metavar="0|1", choices=(0, 1),
                    help="solo con --comando dpi: sincronizacion de movimiento")
    ap.add_argument("--boton", metavar="NOMBRE",
                    choices=sorted(est.BOTONES_POR_NOMBRE),
                    help="solo con --comando botones: que boton fisico se "
                         "remapea. Tiene que quedar un clic izquierdo en los "
                         "botones 1 a 5, y el 6 y el 7 no pueden llevarlo")
    ap.add_argument("--funcion", metavar="NOMBRE|N",
                    help="solo con --comando botones: la funcion nueva, por "
                         "nombre o por codigo. --listar-funciones las muestra")
    ap.add_argument("--listar-funciones", action="store_true",
                    help="imprime la tabla de funciones de boton y sale; no "
                         "toca el mouse")
    ap.add_argument("--atajo", metavar="CTRL+C",
                    help="solo con --comando botones --funcion 'atajo de "
                         "teclado': el atajo, con los modificadores adelante "
                         "y la tecla al final (ctrl, shift, alt, win). Los "
                         "dos bytes del slot son la mascara y el usage HID. "
                         "--listar-teclas muestra los nombres de tecla")
    ap.add_argument("--listar-teclas", action="store_true",
                    help="imprime las teclas que acepta --atajo -y los pasos "
                         "de --eventos- y sale; no toca el mouse")
    ap.add_argument("--eventos", metavar="LISTA",
                    help="solo con --comando macro: GRABA la lista de "
                         "eventos. Cada uno se escribe `tecla:direccion@ms` y "
                         "van separados por comas, por ejemplo "
                         "\"clic-izquierdo:abajo@10, clic-izquierdo:arriba@10\". "
                         f"Entran {est.MACRO_EVENTOS_MAX} eventos, y cada uno "
                         f"de mas de {est.MACRO_TIEMPO_CORTO_MAX} ms cuenta "
                         "por dos")
    ap.add_argument("--macro-id", type=int, metavar="N",
                    help="cual macro. Con --comando macro dice cual se lee y "
                         "se reescribe, y va obligatorio: cmd 9 es el unico "
                         "comando que se lee con el id en el byte 5 y no con "
                         "el perfil. Con --comando botones --funcion macro "
                         "dice cual se le asigna al boton, y tambien va "
                         "obligatorio: un slot con id 0 apunta a un macro que "
                         "no existe y el mouse acusa la escritura igual")
    ap.add_argument("--modo", type=int, metavar="0|1|2",
                    choices=tuple(est.MACRO_MODOS),
                    help="solo con --comando macro: el modo de disparo. "
                         + ", ".join(f"{k} = {v}"
                                     for k, v in est.MACRO_MODOS.items())
                         + ". Los tres estan MEDIDOS en el bus")
    ap.add_argument("--repeticiones", type=int, metavar="N",
                    help=f"solo con --comando macro --modo "
                         f"{est.MACRO_MODO_CON_CONTADOR}: cuantas veces se "
                         f"reproduce ({est.MACRO_REPETICIONES_MIN} a "
                         f"{est.MACRO_REPETICIONES_MAX}). Es el unico modo "
                         "que tiene contador; en los otros dos el byte va "
                         "forzado a 1")
    ap.add_argument("--rueda", choices=("derecha", "invertida"),
                    help="solo con --comando botones: el orden de los dos "
                         "slots de la rueda. `derecha` es el del soft nativo, "
                         "MEDIDO girandola; `invertida` es el de la pagina")
    ap.add_argument("--reposo", type=float, metavar="MIN",
                    help=f"solo con --comando luz: el OTRO temporizador de "
                         f"reposo, el corto, en minutos: {est.REPOSO_MIN} a "
                         f"{est.REPOSO_MAX} de a 0.5. No es --hibernacion: va "
                         "en otro byte. El mouse esta en 0.5 (30 s) y el "
                         "latido baja de 2 s a 4 s a los ~32 s de quietud")
    args = ap.parse_args(argv)

    if args.listar_funciones:
        for codigo, nombre in sorted(est.FUNCIONES_DE_BOTON.items()):
            print(f"  {codigo:>3}  {nombre}")
            if codigo == est.FUNCION_ATAJO:
                print("       (lleva --atajo, p.ej. --atajo ctrl+c)")
            elif codigo == est.FUNCION_MACRO:
                print("       (lleva --macro-id)")
        return 0

    if args.listar_teclas:
        # Los usages son los del bundle -`_w()` en app.js, 111 teclas-, los
        # nombres son nuestros. Se listan en orden de usage y no alfabetico
        # porque asi se ven los grupos: letras, digitos, el bloque de edicion,
        # las F, el teclado numerico.
        print("  Teclas (el numero es el usage HID):")
        for nombre, usage in sorted(est.TECLAS_HID.items(),
                                    key=lambda kv: kv[1]):
            print(f"    {usage:>3}  {nombre}")
        print("\n  Modificadores de --atajo: "
              + ", ".join(f"{n} ({b:#04x})"
                          for n, b in est.MODIFICADORES.items()))
        print("  Y solo en --eventos, ademas de las teclas: "
              + ", ".join(sorted(est.MACRO_BOTONES_POR_NOMBRE))
              + ", y los modificadores como tecla suelta (ctrl, shift, alt, "
                "win)")
        print("\n  Las dos direcciones de un paso de --eventos: "
              + ", ".join(sorted(est.MACRO_DIRECCIONES_POR_NOMBRE)))
        print(f"  ({est.MACRO_DIRECCION_MEDIDA})")
        print("\n  Los atajos que la pagina oficial ofrece hechos:")
        for nombre, texto in sorted(est.ATAJOS_DEL_BUNDLE_EN_TEXTO.items(),
                                    key=lambda kv: kv[1]):
            p1, p2 = est.ATAJOS_DEL_BUNDLE[nombre]
            print(f"    {texto:<14} {p1:#04x} {p2:#04x}  "
                  f"{nombre.removeprefix('FUN_').lower()}")
        return 0

    cmd = COMANDOS[args.comando]

    # --- botones (cmd 8) -------------------------------------------------
    # Se valida antes de tocar el mouse y con el mismo codigo que despues
    # aplica el cambio, igual que los rangos de cmd 5.
    boton_slot = funcion_cod = None
    for nombre, valor in (("--boton", args.boton), ("--funcion", args.funcion),
                          ("--rueda", args.rueda)):
        if valor is not None and cmd != p.CMD_BUTTONS:
            print(f"{nombre} es de --comando botones", file=sys.stderr)
            return 2
    for nombre, valor in (("--modo", args.modo),
                          ("--repeticiones", args.repeticiones)):
        if valor is not None and cmd != p.CMD_MACRO:
            print(f"{nombre} es de --comando macro", file=sys.stderr)
            return 2
    # `--macro-id` es el unico que sirve para dos comandos, y quiere decir lo
    # mismo en los dos: cual macro. En `botones` es el destino del slot; en
    # `macro` es el bloque que se lee y se reescribe.
    if args.eventos is not None and cmd != p.CMD_MACRO:
        print("--eventos es de --comando macro: graba la lista de pasos de un "
              "macro", file=sys.stderr)
        return 2
    if args.atajo is not None and cmd != p.CMD_BUTTONS:
        print("--atajo es de --comando botones --funcion 'atajo de teclado'",
              file=sys.stderr)
        return 2
    if args.macro_id is not None and cmd not in (p.CMD_BUTTONS, p.CMD_MACRO):
        print("--macro-id es de --comando macro o de --comando botones "
              "--funcion macro", file=sys.stderr)
        return 2

    # Las tres existen desde aca aunque no se escriba un atajo ni un macro:
    # una variable que solo existe en una rama es el bug, que
    # revento el informe DESPUES de haber escrito y releido.
    atajo_p1 = atajo_p2 = eventos_nuevos = None

    # --- macros (cmd 9) --------------------------------------------------
    # Es el unico comando que no se lee con el perfil: el byte 5 del pedido
    # lleva el id del macro (`sendMacroDataCommand(macroId)` del bundle,
    # MEDIDO). Sin id, el mouse devuelve un bloque vacio, asi
    # que no hay nada que reescribir y no hay respaldo previo de que hablar.
    if cmd == p.CMD_MACRO:
        if args.valor is not None:
            print("los macros no se cambian con --valor: van --modo y, en el "
                  f"modo {est.MACRO_MODO_CON_CONTADOR}, --repeticiones",
                  file=sys.stderr)
            return 2
        if args.macro_id is None:
            print("--comando macro necesita --macro-id: cmd 9 se lee con el "
                  "id en el byte 5, no con el perfil, y sin el devuelve un "
                  "bloque vacio. Los ids que tiene el mouse salen de "
                  "driver/scripts/respaldar.py", file=sys.stderr)
            return 2
        if args.eventos is not None and (args.modo is not None
                                         or args.repeticiones is not None):
            print("un campo por corrida: --eventos GRABA la lista de pasos y "
                  "--modo/--repeticiones cambian el disparo. Son dos cosas "
                  "distintas del mismo bloque, y si algo sale raro con las "
                  "dos juntas no se sabe cual fue", file=sys.stderr)
            return 2
        if not est.MACRO_ID_MIN <= args.macro_id <= est.MACRO_ID_MAX:
            print(f"--macro-id {args.macro_id} fuera de {est.MACRO_ID_MIN}.."
                  f"{est.MACRO_ID_MAX}", file=sys.stderr)
            return 2
        if args.eventos is not None:
            # El rango y el sitio se validan antes de tocar el mouse, con el
            # mismo codigo que los aplica.
            try:
                eventos_nuevos = est.eventos_desde_texto(args.eventos)
                est.armar_macro(args.macro_id, eventos_nuevos)
            except ValueError as exc:
                print(exc.args[0], file=sys.stderr)
                return 2
        if (args.repeticiones is not None
                and args.modo != est.MACRO_MODO_CON_CONTADOR):
            print(f"--repeticiones es del modo "
                  f"{est.MACRO_MODO_CON_CONTADOR} "
                  f"({est.MACRO_MODOS[est.MACRO_MODO_CON_CONTADOR]}), que es "
                  "el unico con contador. En los otros dos el byte va forzado "
                  "a 1", file=sys.stderr)
            return 2
        if (args.repeticiones is not None
                and not est.MACRO_REPETICIONES_MIN <= args.repeticiones
                <= est.MACRO_REPETICIONES_MAX):
            print(f"--repeticiones {args.repeticiones} fuera de "
                  f"{est.MACRO_REPETICIONES_MIN}.."
                  f"{est.MACRO_REPETICIONES_MAX}", file=sys.stderr)
            return 2
    if cmd == p.CMD_BUTTONS:
        if args.valor is not None:
            print("los botones no se cambian con --valor: van --boton y "
                  "--funcion", file=sys.stderr)
            return 2
        if (args.boton is not None) != (args.funcion is not None):
            print("--boton y --funcion van juntos: uno dice cual y el otro "
                  "que hace", file=sys.stderr)
            return 2
        if args.rueda is not None and args.boton is not None:
            print("un campo por corrida: --rueda o --boton, no los dos",
                  file=sys.stderr)
            return 2
        if args.boton is not None:
            boton_slot = est.BOTONES_POR_NOMBRE[args.boton]
            # El clic izquierdo se remapea, siempre que
            # quede uno en los botones 1 a 5: lo cuida `escribir_boton()` sobre
            # el bloque leido, que es el unico lugar donde se sabe que hay.
            texto = args.funcion.strip()
            if texto.isdigit():
                funcion_cod = int(texto)
            else:
                porn = {v.lower(): k
                        for k, v in est.FUNCIONES_DE_BOTON.items()}
                funcion_cod = porn.get(texto.lower())
            if funcion_cod not in est.FUNCIONES_DE_BOTON:
                print(f"--funcion {args.funcion!r} no esta en la tabla. "
                      "Corré --listar-funciones", file=sys.stderr)
                return 2
            # El macro es la unica funcion expuesta cuyo tercer byte lleva
            # un dato que hay que elegir, y el mouse no avisa si esta mal:
            # acusa 0xC1 y el boton queda muerto. Se valida acá, antes de
            # tocarlo, con el mismo rango que usa escribir_boton().
            if funcion_cod == est.FUNCION_MACRO:
                if args.macro_id is None:
                    print("--funcion macro necesita --macro-id: el slot es "
                          "`12 00 <id>` y sin id apunta a un macro que no "
                          "existe. Los ids que tiene el mouse salen de "
                          "driver/scripts/respaldar.py", file=sys.stderr)
                    return 2
                if not (est.MACRO_ID_MIN <= args.macro_id
                        <= est.MACRO_ID_MAX):
                    print(f"--macro-id {args.macro_id} fuera de "
                          f"{est.MACRO_ID_MIN}..{est.MACRO_ID_MAX}",
                          file=sys.stderr)
                    return 2
            elif funcion_cod == est.FUNCION_ATAJO:
                # La otra funcion con parametros, y con
                # interfaz. Sigue valiendo el agujero: sin tecla el slot queda
                # en `11 00 00` -el vacio del bundle-, el mouse lo acusa igual
                # y el boton no hace nada. Por eso --atajo es obligatorio.
                if args.atajo is None:
                    print("--funcion 'atajo de teclado' necesita --atajo, "
                          "p.ej. --atajo ctrl+c: el slot es `11 <modif> "
                          "<usage>` y sin tecla apunta a nada. Las teclas "
                          "salen de --listar-teclas", file=sys.stderr)
                    return 2
                try:
                    atajo_p1, atajo_p2 = est.atajo_desde_texto(args.atajo)
                except ValueError as exc:
                    print(exc.args[0], file=sys.stderr)
                    return 2
            elif funcion_cod in est.FUNCIONES_CON_PARAMETRO:
                # Red por si manana entra otra funcion con parametro: mejor
                # negarse que escribir un slot a medias. Las dos que hay hoy
                # -macro y atajo- estan arriba, cada una con su opcion.
                print(f"--funcion {est.FUNCIONES_DE_BOTON[funcion_cod]!r} "
                      f"necesita parametros que esta herramienta no expone "
                      f"({est.FUNCIONES_CON_PARAMETRO[funcion_cod]}). "
                      "Escribirla sin ellos deja el boton muerto y el mouse "
                      "acusa la escritura igual", file=sys.stderr)
                return 2
            elif args.atajo is not None:
                print(f"--atajo es de --funcion 'atajo de teclado'; "
                      f"{est.FUNCIONES_DE_BOTON[funcion_cod]!r} no lleva "
                      "teclas", file=sys.stderr)
                return 2
            elif args.macro_id is not None:
                print(f"--macro-id es de --funcion macro; "
                      f"{est.FUNCIONES_DE_BOTON[funcion_cod]!r} no lleva id",
                      file=sys.stderr)
                return 2

    # Un solo nombre para "esto cambia algo", porque el paso 6 compara distinto
    # segun eso y la luz no se cambia con --valor sino con --color.
    rgb = None
    if args.color is not None:
        if cmd != p.CMD_LIGHTING:
            print("--color es de la luz; para rate y dpi el valor va en "
                  "--valor", file=sys.stderr)
            return 2
        texto = args.color.lstrip("#")
        try:
            crudo = bytes.fromhex(texto)
        except ValueError:
            crudo = b""
        if len(crudo) != 3:
            print(f"--color quiere seis digitos hexadecimales (RRGGBB), no "
                  f"{args.color!r}", file=sys.stderr)
            return 2
        rgb = tuple(crudo)
    if cmd == p.CMD_LIGHTING and args.valor is not None:
        print("la luz no se cambia con --valor. Los campos de cmd 5 tienen "
              "cada uno su opcion: --color, --hibernacion, --respuesta, "
              "--reposo", file=sys.stderr)
        return 2
    for nombre, valor in (("--hibernacion", args.hibernacion),
                          ("--respuesta", args.respuesta),
                          ("--reposo", args.reposo)):
        if valor is not None and cmd != p.CMD_LIGHTING:
            print(f"{nombre} es de --comando luz", file=sys.stderr)
            return 2
    if args.nivel_activo is not None and cmd != p.CMD_DPI:
        print("--nivel-activo es de --comando dpi", file=sys.stderr)
        return 2
    if args.nivel_activo is not None and not 1 <= args.nivel_activo <= 8:
        print(f"el nivel va de 1 a 8, no {args.nivel_activo}", file=sys.stderr)
        return 2
    sensor = {"lod": (None if args.lod is None
                      else est.lod_desde_mm(args.lod)),
              "ripple": args.ripple,
              "angle_snapping": args.angle_snapping,
              "motion_sync": args.motion_sync}
    sensor = {k: v for k, v in sensor.items() if v is not None}
    for nombre in sensor:
        if cmd != p.CMD_DPI:
            print(f"--{nombre.replace('_', '-')} es de --comando dpi",
                  file=sys.stderr)
            return 2
    if sensor and args.valor is not None:
        print("los interruptores del sensor y --valor son dos campos "
              "distintos del mismo bloque: uno por corrida", file=sys.stderr)
        return 2
    if args.nivel_activo is not None and (sensor or args.valor is not None):
        print("--nivel-activo dice cual nivel se USA y --valor cuanto VALE un "
              "nivel: son dos campos distintos del mismo bloque, uno por "
              "corrida", file=sys.stderr)
        return 2
    # Un campo por corrida. El ciclo de la Etapa 4 es "cambio chico,
    # verificacion, vuelta atras": dos campos a la vez rompen la segunda parte,
    # porque si algo sale raro no se sabe cual de los dos fue.
    pedidos = [n for n, v in (("--color", rgb),
                              ("--hibernacion", args.hibernacion),
                              ("--respuesta", args.respuesta),
                              ("--nivel-activo", args.nivel_activo),
                              ("--reposo", args.reposo)) if v is not None]
    pedidos += [f"--{n.replace('_', '-')}" for n in sensor]
    if len(pedidos) > 1:
        print(f"un campo por corrida, y se pidieron {len(pedidos)}: "
              f"{', '.join(pedidos)}.\n"
              "Si algo sale raro con dos cambios juntos no se sabe cual fue.",
              file=sys.stderr)
        return 2
    # Los rangos se validan antes de tocar el mouse, con el mismo codigo que
    # los aplica: `escribir_parametros_luz()` los levanta como ValueError.
    if args.hibernacion is not None or args.respuesta is not None:
        try:
            est.escribir_parametros_luz(
                bytes(est.fin_de_campos(p.CMD_LIGHTING) + 2),
                hibernacion=args.hibernacion, respuesta=args.respuesta)
        except ValueError as exc:
            print(exc.args[0], file=sys.stderr)
            return 2
    if args.reposo is not None:
        try:
            est.escribir_reposo_ligero(
                bytes(est.fin_de_campos(p.CMD_LIGHTING) + 2),
                minutos=args.reposo)
        except ValueError as exc:
            print(exc.args[0], file=sys.stderr)
            return 2
    hay_cambio = (args.valor is not None or rgb is not None
                  or args.nivel_activo is not None
                  or args.hibernacion is not None
                  or args.respuesta is not None
                  or args.reposo is not None
                  or bool(sensor)
                  or boton_slot is not None
                  or args.rueda is not None
                  or args.modo is not None
                  or args.repeticiones is not None
                  or args.eventos is not None)

    if args.valor is not None:
        # Se valida antes de tocar el mouse: hacer esperar medio minuto de
        # respaldo para despues decir que el numero no existe es maltrato. Lo
        # unico que no se puede chequear aca es si el nivel de dpi esta
        # encendido, porque eso lo dice el mouse.
        if cmd == p.CMD_REPORT_RATE:
            if args.nivel is not None:
                print("--nivel es de dpi; el report rate no tiene niveles",
                      file=sys.stderr)
                return 2
            if args.valor not in p.RATE_INDICE:
                print(f"{args.valor} Hz no existe. Los que hay: "
                      + ", ".join(str(h) for h in sorted(p.RATE_INDICE)),
                      file=sys.stderr)
                return 2
        elif cmd == p.CMD_DPI:
            if args.nivel is None:
                print("con --comando dpi hace falta --nivel N: el bloque tiene "
                      "ocho niveles y hay que decir cual se cambia",
                      file=sys.stderr)
                return 2
            if not 1 <= args.nivel <= 8:
                print(f"el nivel va de 1 a 8, no {args.nivel}", file=sys.stderr)
                return 2
            if not est.DPI_MINIMO_UI <= args.valor <= est.DPI_MAXIMO_UI:
                print(f"{args.valor} dpi esta fuera de lo que ofrece la pagina "
                      f"oficial ({est.DPI_MINIMO_UI} a {est.DPI_MAXIMO_UI})",
                      file=sys.stderr)
                return 2

    # Un nodo que no existe, o que no es el dongle, es un error de uso: sale
    # con su mensaje y no con un traceback. Es la misma familia que H-04 de la
    # auditoria del agente A, que era sobre el CLI del puente.
    if device is not None:
        # Corrida de prueba: el device lo pone quien llama y no se toca ningun
        # nodo. La verificacion de abajo es sobre un archivo real, asi que no
        # tiene nada que verificar aca.
        path = nodo or "(device inyectado)"
    else:
        try:
            path = args.hidraw
            if path is not None:
                verificar_nodo_dongle(path)
            else:
                path = find_config_hidraw()
        except (DeviceNotFound, OSError, ValueError) as exc:
            print(f"{exc}", file=sys.stderr)
            return 1

    # Los nombres de macro viven en esta maquina y no en el mouse (ver
    # `driver/src/linshark/nombres.py`). Si el archivo no existe -lo normal- un macro
    # se sigue llamando "macro 17"; si esta roto, se avisa y se sigue.
    nombres_de_macro = nombres.NombresDeMacro()
    if nombres_de_macro.problema:
        print(f"  [!] no pude leer los nombres de macro "
              f"({nombres_de_macro.problema})", file=sys.stderr)

    canal = None
    if device is None:
        canal = HidrawChannel(path)
        canal.open()
        device = Device(canal)
        canal.start_reading(asyncio.get_running_loop(), device.alimentar)

    # **La coreografia de la Etapa 3 la corre `sesion.aplicar()`**, que es la
    # misma que va a usar la aplicacion: tasa, respaldo completo, lectura,
    # codificacion, escritura, relectura y veredicto, con la tasa devuelta en
    # el `finally`. Lo que queda aca es lo propio de una terminal -que bytes
    # pide el usuario, y como se cuenta lo que paso-, que es la regla: las
    # decisiones viven en la biblioteca.
    #
    # Antes esto era una coreografia paralela de doscientas
    # lineas. Se migro cuando la duplicacion empezo a costar: ese mismo dia el
    # permiso de tasa se escribio dos veces, una de cada lado.
    carpeta = CARPETA_RESPALDOS
    carpeta.mkdir(parents=True, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%dT%H%M%S")
    # El macro que se va a tocar entra al respaldo si o si: puede existir en el
    # mouse sin que ningun slot de cmd 8 lo apunte -entre escribirlo y
    # asignarlo a un boton- y entonces no hay de donde deducir su id. Un
    # respaldo previo que no lo trae no es una red. Al asignar el macro 17 a
    # un boton, el previo no lo tenia y el posterior si, asi que el paso 6 listo
    # "macro 17: uno de los dos no contesto (A)" adentro de la lista de
    # cambios reales, que es el unico lugar donde conviene que no haya ruido.
    extra = [args.macro_id] if args.macro_id is not None else []
    archivos: dict[str, Path] = {}

    def guardar(cual, estado):
        ruta = carpeta / f"{cual}-de-escribir-{args.comando}-{sello}.json"
        ruta.write_text(json.dumps(estado, indent=2, ensure_ascii=False))
        archivos[cual] = ruta
        if cual == "antes":
            print(f"      guardado en {ruta.relative_to(carpeta.parent)}")

    def avisar(texto):
        # Los avisos con datos vienen como `clave|texto` (ver los AVISO_* de
        # `sesion`): la clave dice que paso es y el texto se envuelve solo, en
        # vez de que el CLI adivine por el contenido.
        clave, _, detalle = texto.partition("|")
        if clave == sesion.AVISO_TASA_BAJA:
            print(f"\n[0/6] {textwrap.fill(detalle, 72, subsequent_indent='      ')}")
            return
        if clave == sesion.AVISO_TASA_VUELVE:
            print(f"\n[0/6] {detalle}")
            return
        if clave == sesion.AVISO_ESTADO_INCOHERENTE:
            # **El perfil y el bloque suelto dicen cosas distintas de lo
            # mismo.** No es el mouse: es una de las dos lecturas.
            print(f"      LA LECTURA SE CONTRADICE: {detalle}")
            return
        if clave == sesion.AVISO_BLOQUE_IMPOSIBLE:
            # **Esto corta la Etapa 3 antes del paso 4**, asi que se dice
            # fuerte: lo que sigue no es "no se pudo", es "lo que iba a
            # escribir estaba mal y no lo mande".
            print(f"\n[3/6] NO LO ESCRIBO: el bloque tiene valores que el "
                  f"mouse no puede tener ({detalle}).")
            print("      La lectura de la que sale vino mal. Volvé a "
                  "intentarlo; si insiste, respaldá y mirá el bloque.")
            return
        if texto == sesion.AVISO_RESPALDO:
            print(f"[1/6] respaldo fresco de {path}")
            print("      mové el mouse: el enlace pierde la mitad de los "
                  "pedidos con el mouse quieto")
        elif texto == sesion.AVISO_RELECTURA:
            print("\n[6/6] releyendo todo para comparar (mové el mouse)")
        elif texto == sesion.AVISO_ACUSE:
            # **No decir "el mouse aplico"**: el acuse es del dongle. MEDIDO
            #: con el mouse a 2000 Hz llego `0xC1` dos veces y
            # la tasa no se movio. Quien contesta eso es el paso 6, que relee.
            print("      el dongle acuso 0xC1: acepto la trama. Si el mouse "
                  "la aplico lo dice el paso 6")
        elif texto == sesion.AVISO_SIN_ACUSE:
            print("      SIN ACUSE. O el enlace perdio el pedido, o el mouse "
                  "ignoro la trama por formato.")
        else:
            print(f"      {texto}")

    try:
        # --- 2 y 3. el valor actual, y que bytes escribir ---------------
        # **Esto es lo unico que la biblioteca no puede hacer por nosotros**:
        # que bytes hay que escribir sale de lo que se pidio por linea de
        # comandos, y eso es propio del CLI. Todo el resto de la Etapa 3
        # -respaldo completo, tasa, escritura, relectura y veredicto- lo corre
        # `sesion.aplicar()`, que es lo que va a usar la aplicacion.
        #
        # Las variables que el paso 6 necesita se comparten con `nonlocal` en
        # vez de devolverlas: asi el cuerpo de abajo quedo **igual** al que
        # tenia la coreografia propia, que es lo que hace revisable el cambio.
        ctx_que = ctx_aviso = ""
        ctx_sin_efecto = False
        # Existen desde aca aunque no se escriba un nivel de dpi: son las dos
        # que reventaron el informe al entrar por otro camino.
        # Viven en `main` y no en `codificar` porque las lee el paso 6.
        en_la_pagina = efectivo = None

        def codificar(leido):
            nonlocal en_la_pagina, efectivo, ctx_que, ctx_aviso, ctx_sin_efecto
            if cmd == p.CMD_MACRO and est.parametros_de_macro(leido) is None:
                print(f"\n      el mouse devolvio un bloque que no cierra "
                      f"como macro. Con un id que no existe contesta un "
                      f"bloque vacio: revisa que el macro {args.macro_id} "
                      f"este cargado (driver/scripts/respaldar.py lo lista)",
                      file=sys.stderr)
                raise _Aborta(1)
            print(f"\n[2/6] leido: cmd={cmd} datos={leido.hex(' ')}")
            if cmd == p.CMD_MACRO:
                # El nombre no viene del mouse -el bloque no tiene campo de
                # nombre- sino de esta maquina. Se muestra para no escribirle
                # al macro equivocado, que es el error que un id suelto invita.
                print(f"      {nombres_de_macro.describir(args.macro_id)}")

            # --- 3. la trama ------------------------------------------------
            datos = bytearray(leido)
            aviso = ""
            if not hay_cambio and cmd == p.CMD_BUTTONS:
                # **La unica idempotente del proyecto que no es un memcpy.** Los
                # slots 4, 5 y 6 se remapean entre escritura y lectura, asi que
                # devolverle al mouse el bloque crudo le rotaria tres botones. El
                # bloque que sale de aca es distinto del leido y deja al mouse
                # igual: eso es lo que hace que la relectura del paso 6 no cambie.
                datos = bytearray(est.retraducir_botones(bytes(datos)))
                que = ("IDEMPOTENTE (el mismo estado, traducido a la numeracion "
                       "de escritura)")
            elif not hay_cambio and cmd == p.CMD_MACRO:
                # La otra idempotente que no es un memcpy. El mouse devuelve el
                # checksum interno con los bytes al reves, asi que devolverle el
                # bloque crudo le manda un bloque mal formado. El codificador lo
                # rearma y no toca ningun campo: ese es el arranque de la Etapa 3
                # de cmd 9.
                datos = bytearray(est.escribir_macro(bytes(datos)))
                que = ("IDEMPOTENTE (el mismo macro, con el checksum interno "
                       "rearmado)")
                aviso = ("      El bloque que se manda difiere del leido en DOS "
                         "bytes, y a proposito: el\n"
                         "      mouse devuelve el checksum interno invertido "
                         "(`6d 0c` al leer, `0c 6d` al\n"
                         "      escribir, MEDIDO).\n"
                         "\n"
                         "      Y va PARTIDO EN DOS TRAMAS: entre una y otra hay "
                         "~1 s en que el mouse\n"
                         "      tiene medio bloque. No desenchufes el dongle ahi.\n")
            elif not hay_cambio:
                que = "IDEMPOTENTE (el valor que ya tiene: no deberia cambiar nada)"
            elif args.nivel_activo is not None:
                # **Cual nivel esta EN USO**, que no es cuanto vale un nivel. Vive
                # en el mismo bloque que los ocho valores de dpi y que los cuatro
                # interruptores, asi que el codificador toca un byte y el checksum
                # y nada mas.
                antes_nivel = est.nivel_activo_de(bytes(datos))
                try:
                    datos = bytearray(est.escribir_nivel_activo(
                        bytes(datos), nivel=args.nivel_activo))
                except est.NivelApagado as exc:
                    print(f"\n      {exc.args[0]}", file=sys.stderr)
                    raise _Aborta(1)
                que = (f"CAMBIO REAL: nivel en uso {antes_nivel} -> "
                       f"{args.nivel_activo}")
                if antes_nivel != args.nivel_activo:
                    # **La cuarta verificacion a simple vista del proyecto.** Los
                    # ocho colores de indicador viajan en este mismo bloque, uno
                    # por nivel, y el LED de nivel es lo unico que prende en este
                    # modelo: los bytes de color de cmd 5 no encienden nada
                    # (MEDIDO).
                    # El color sale del bloque que el mouse acaba de devolver,
                    # no de una tabla nuestra: son ocho campos de este mismo cmd 4.
                    color = est.color_de_nivel(leido, args.nivel_activo)
                    pinta = ""
                    if color:
                        pinta = f" (#{color[0]}" + (f", {color[1]})" if color[1]
                                                    else ")")
                    aviso = ("      Este SI se verifica a simple vista: el "
                             "indicador de nivel del mouse\n"
                             f"      tiene que quedar en el color del nivel "
                             f"{args.nivel_activo}{pinta}.\n"
                             "      Los ocho colores viajan en este mismo bloque, "
                             "y es el unico LED que\n"
                             "      prende en este modelo.\n")
            elif sensor:
                # Los cuatro interruptores del sensor. Viven en el mismo bloque que
                # los ocho niveles de dpi, asi que el codificador toca dos bytes y
                # el checksum y **nada mas**: pisar un nivel de dpi sin querer aca
                # seria el error caro.
                antes_sen = est.parametros_de_sensor(bytes(datos))
                datos = bytearray(est.escribir_parametros_sensor(
                    bytes(datos), **sensor))
                despues_sen = est.parametros_de_sensor(bytes(datos))
                cual = next(iter(sensor))
                def _leg(v):
                    if cual == "lod":
                        return est.LOD_NOMBRES.get(v, v)
                    return "ON" if v else "OFF"
                que = (f"CAMBIO REAL: {cual.replace('_', ' ')} "
                       f"{_leg(antes_sen[cual])} -> {_leg(despues_sen[cual])}")
                if cual == "lod":
                    # Solo tiene sentido mandar a mirar el corte si de verdad se
                    # movio. Y el LOD nunca cae en el aviso de "sin verificacion
                    # externa" de abajo: es el unico campo que si la tiene.
                    if antes_sen[cual] != despues_sen[cual]:
                        aviso = ("      Este SI se verifica a simple vista, y es el "
                                 "unico del proyecto:\n"
                                 "      levantá el mouse despacio sobre el mismo "
                                 "apoyo y fijate a que altura\n"
                                 "      deja de mover el puntero. Con 2 mm tiene "
                                 "que seguir mas arriba que con 1 mm.\n")
                else:
                    aviso = ("      OJO: este campo no tiene verificacion externa "
                             "barata. El acuse 0xC1 y\n"
                             "      la relectura dicen que el mouse lo guardo, no "
                             "que haga algo distinto.\n")
            elif cmd == p.CMD_LIGHTING and rgb is None:
                # Los tres temporizadores de cmd 5. El reposo corto va por otro
                # codificador porque sale de otro lugar del bundle: vive en el byte
                # `closeTime` entero, y no en los nibbles que mueve el handler
                # `_()` del chunk del X8 Pro.
                antes_par = est.parametros_de_luz(bytes(datos))
                if args.reposo is not None:
                    datos = bytearray(est.escribir_reposo_ligero(
                        bytes(datos), minutos=args.reposo))
                    cual, clave = "reposo", "reposoMin"
                else:
                    datos = bytearray(est.escribir_parametros_luz(
                        bytes(datos), hibernacion=args.hibernacion,
                        respuesta=args.respuesta))
                    cual = ("hibernacion" if args.hibernacion is not None
                            else "respuesta")
                    clave = ("hibernateTime" if cual == "hibernacion"
                             else "responseTime")
                despues_par = est.parametros_de_luz(bytes(datos))
                que = (f"CAMBIO REAL: {cual} {antes_par[clave]} -> "
                       f"{despues_par[clave]}")
                if cual == "reposo" and antes_par[clave] != despues_par[clave]:
                    aviso = ("      Verificalo por fuera: el reposo corto es el "
                             "que mueve el ESCALON del latido\n"
                             "      (2.00 s -> 4.00 s). Con 0.5 min cae a los ~32 "
                             "s; con este valor deberia\n"
                             f"      caer a los ~{args.reposo * 60:.0f} s. "
                             "driver/scripts/medir-hibernacion.py lo ubica solo.\n")
                elif cual == "hibernacion":
                    aviso = ("      Verificalo por fuera con "
                             "driver/scripts/medir-hibernacion.py, que escucha el latido\n"
                             "      del mouse y no le escribe nada. Mové el mouse "
                             "al arrancar la corrida,\n"
                             "      para que la quietud quede anclada.\n")
            elif cmd == p.CMD_LIGHTING:
                campos = est.decodificar(cmd, bytes(datos))
                antes_rgb = (campos["redColor"], campos["greenColor"],
                             campos["blueColor"])
                datos = bytearray(est.escribir_color_luz(bytes(datos), rgb))
                que = (f"CAMBIO REAL: color #{antes_rgb[0]:02x}{antes_rgb[1]:02x}"
                       f"{antes_rgb[2]:02x} -> #{rgb[0]:02x}{rgb[1]:02x}"
                       f"{rgb[2]:02x}")
                # El checksum interno es una suma: permutar componentes -mover el
                # 0xff de verde a azul, por ejemplo- lo deja igual. No es un error,
                # pero conviene saber que ahi el checksum no distingue.
                if antes_rgb != rgb and sum(antes_rgb) == sum(rgb):
                    aviso = ("      los dos colores suman lo mismo, asi que el "
                             "checksum interno no cambia.\n"
                             "      Y no hay con que compensarlo: en este modelo "
                             "los bytes de color no\n"
                             "      encienden nada, asi que tampoco hay un LED que "
                             "mirar.\n")
            elif cmd == p.CMD_MACRO:
                # Solo el disparo. Grabar los eventos es otra cosa y no esta aca:
                # este codificador toca el byte del modo, el del contador y el
                # checksum, y nada mas.
                antes_m = est.parametros_de_macro(bytes(datos))
                if args.eventos is not None:
                    # **Grabar**, que es reemplazar la lista entera. Es el unico
                    # camino del proyecto que escribe cincuenta bytes de una: el
                    # resto toca uno o dos.
                    datos = bytearray(est.escribir_eventos_macro(
                        bytes(datos), eventos_nuevos))
                else:
                    datos = bytearray(est.escribir_macro(
                        bytes(datos), modo=args.modo,
                        repeticiones=args.repeticiones))
                despues_m = est.parametros_de_macro(bytes(datos))
                que = describir_cambio_de_macro(antes_m, despues_m, args.macro_id)
                aviso = ("      OJO: el bloque que se manda NO es el que se leyo "
                         "aunque no cambiara nada.\n"
                         "      El mouse devuelve el checksum interno con los "
                         "bytes al reves (`6d 0c` al leer,\n"
                         "      `0c 6d` al escribir, MEDIDO), asi "
                         "que el codificador lo rearma.\n"
                         "      Devolver el bloque crudo seria mandarle un bloque "
                         "mal formado.\n"
                         "\n"
                         "      Y este es el unico comando que va PARTIDO EN DOS "
                         "TRAMAS: entre una y otra\n"
                         "      hay ~1 s en que el mouse tiene medio bloque. No "
                         "desenchufes el dongle ahi.\n")
            elif cmd == p.CMD_BUTTONS:
                bots = est.botones_de(bytes(datos))
                if args.rueda is not None:
                    orden = (est.RUEDA_CORRECTA if args.rueda == "derecha"
                             else est.RUEDA_COMO_LA_WEB)
                    antes_rueda = est.orden_de_rueda(bots)
                    datos = bytearray(est.escribir_rueda(bytes(datos),
                                                         orden=orden))
                    que = (f"CAMBIO REAL: rueda {antes_rueda} -> "
                           f"{args.rueda} {orden}")
                else:
                    antes_fn = next(b["nombre"] for b in bots
                                    if b["indice"] == boton_slot)
                    try:
                        datos = bytearray(est.escribir_boton(
                            bytes(datos), slot=boton_slot, codigo=funcion_cod,
                            p1=atajo_p1 or 0,
                            p2=(atajo_p2 if atajo_p2 is not None
                                else args.macro_id or 0)))
                    except est.SinClicIzquierdo as exc:
                        print(f"\n      {exc.args[0]}", file=sys.stderr)
                        raise _Aborta(1)
                    destino = est.FUNCIONES_DE_BOTON[funcion_cod]
                    if funcion_cod == est.FUNCION_MACRO:
                        destino += f" {args.macro_id}"
                    elif funcion_cod == est.FUNCION_ATAJO:
                        # Se dice como lo vamos a escribir, no como lo tipeo el
                        # usuario: `est.texto_de_atajo()` sale de los dos bytes
                        # que de verdad van al slot.
                        destino += f" {est.texto_de_atajo(atajo_p1, atajo_p2)}"
                    que = (f"CAMBIO REAL: {args.boton} (slot leido {boton_slot}) "
                           f"{antes_fn} -> {destino}")
                aviso = ("      OJO: el bloque que se manda NO es el que se leyo "
                         "aunque no cambiara nada.\n"
                         "      Los slots 4, 5 y 6 se remapean entre escritura y "
                         "lectura (MEDIDO),\n"
                         "      asi que el codificador los traduce. "
                         "Devolver el bloque\n"
                         "      crudo rotaria tres botones.\n")
            elif cmd == p.CMD_REPORT_RATE:
                byte_previo = datos[1]
                actual = p.rate_indice(byte_previo)
                # La aritmetica vive en estructuras, que es la capa que usa la
                # aplicacion: respeta el nibble bajo -la tasa por cable,
                # INFERIDO- y rearma el complemento. Reproduce las catorce
                # escrituras de rate que hay en el bus, siete del soft y siete de
                # la web.
                datos = bytearray(est.escribir_report_rate(bytes(datos),
                                                           hz=args.valor))
                # El indice puede no estar en la tabla, y no es teorico: la
                # pagina oficial le escribio `0x01` a este mouse
                # -indice 0-, que no es ninguno de los siete observados. Decir
                # "None Hz" ahi seria peor que decir que no se sabe.
                desde = (f"{p.RATE_HZ[actual]} Hz" if actual in p.RATE_HZ
                         else f"un byte {byte_previo:#04x}, indice {actual}, que "
                              "ninguna captura mostro")
                que = f"CAMBIO REAL: {desde} -> {args.valor} Hz"
                # **El nibble bajo se respeta, y eso puede producir un byte que
                # ningun cliente oficial mando.** Si la pagina dejo el mouse en
                # `0x01` -paso- pedirle 1000 Hz da `0x41`, que no
                # esta en ninguna captura. No se prohibe: el mouse puede estar
                # justo en ese estado y ser lo que se quiere arreglar. Pero es lo
                # unico que la regla del proyecto no deja mandar a ciegas, asi que
                # se dice ANTES de confirmar.
                if not est.rate_byte_en_el_bus(datos[1]):
                    aviso += (f"      OJO: el byte que sale es {datos[1]:#04x}, y "
                              "**ninguna captura del driver oficial**\n"
                              "      lo muestra. Pasa porque el nibble bajo del "
                              f"bloque vale {datos[1] & 0x0F} y se respeta: el "
                              "soft\n"
                              "      escribe siempre 4 y la pagina iguala los dos "
                              "nibbles. Los trece vistos son\n"
                              "        " + " ".join(
                                  f"{b:#04x}" for b in sorted(
                                      est.RATE_BYTES_EN_EL_BUS)) + "\n")
            else:
                # dpi. Toda la aritmetica esta en estructuras.escribir_nivel_dpi():
                # cambia el byte bajo y el alto del nivel, el bit de la rama de
                # Pu() y el checksum interno del bloque, y nada mas.
                campos = est.decodificar(cmd, bytes(datos))
                antes_niveles = mod_dpi.niveles_lineales(
                    campos["Dpi_X_setting"], campos["Dpi_Y_setting"],
                    campos["DPI_X_Double_Flag"])
                try:
                    nuevos, efectivo = est.escribir_nivel_dpi(
                        bytes(datos), args.nivel, args.valor)
                except est.NivelApagado as exc:
                    print(f"\n      {exc.args[0]}", file=sys.stderr)
                    raise _Aborta(1)
                datos = bytearray(nuevos)
                que = (f"CAMBIO REAL: nivel {args.nivel}, "
                       f"{antes_niveles[args.nivel - 1]} -> {efectivo} dpi")
                if efectivo != args.valor:
                    aviso = (f"      pediste {args.valor} y el mouse va a guardar "
                             f"{efectivo}: `Pu()` divide entero, asi que solo "
                             f"entran multiplos de 50 (de 100 arriba de 26000).\n")
                # Y lo que importa mas: la pagina oficial NO va a mostrar ese
                # numero. Escribe con Pu() pero lee con la tabla del 3311, asi que
                # el mismo byte le da otro valor. Decirlo antes de confirmar evita
                # que despues parezca que la escritura fallo.
                nuevos_campos = est.decodificar(cmd, bytes(datos))
                en_la_pagina = mod_dpi.decodificar_niveles(
                    nuevos_campos["Dpi_X_setting"], nuevos_campos["Dpi_Y_setting"],
                    nuevos_campos["DPI_X_Double_Flag"])[args.nivel - 1]
                if en_la_pagina != efectivo:
                    aviso += (f"      OJO: la pagina oficial va a mostrar "
                              f"{en_la_pagina}, no {efectivo}. No es un error de "
                              f"esta herramienta:\n"
                              f"      la pagina escribe con Pu() y lee con la tabla "
                              f"del 3311, y para el mismo byte\n"
                              f"      las dos formulas dan distinto. Ver "
                              f"dev/models/attackshark-x8pro/docs/bitacora.md.")
            # Se pidio un cambio pero el codificador no movio un byte: el valor
            # pedido es el que el mouse ya tiene. Eso **no es un fallo**, es una
            # escritura idempotente, que es justo con lo que empieza la Etapa 3.
            # Antes el paso 6 la contaba como "NO CAMBIO NADA, y se
            # pidio un cambio" y devolvia 1, despues de haber avisado en el paso 3
            # de que iba a pasar exactamente eso: el script se contradecia solo y
            # daba una alarma falsa. Y una alarma falsa gasta a las de verdad.
            # Para cmd 8 la referencia no es el bloque leido sino su traduccion:
            # los dos difieren siempre, y compararlos crudos daria "cambio" en
            # una escritura que no cambia nada.
            # Los dos comandos cuya escritura idempotente NO es el bloque leido
            # necesitan su propia referencia: comparar contra el crudo daria
            # "cambio" en una escritura que no cambia nada.
            if cmd == p.CMD_BUTTONS:
                referencia = est.retraducir_botones(leido)
            elif cmd == p.CMD_MACRO:
                referencia = est.escribir_macro(leido)
            else:
                referencia = leido
            sin_efecto = hay_cambio and bytes(datos) == referencia
            if sin_efecto:
                que = f"IDEMPOTENTE ({que.removeprefix('CAMBIO REAL: ')})"
                aviso = ("      el valor pedido es el que el mouse ya tiene, asi "
                         "que esta escritura no\n      deberia cambiar nada, y "
                         "que no cambie nada es el resultado bueno.\n") + aviso

            ctx_que, ctx_aviso = que, aviso
            ctx_sin_efecto = sin_efecto
            return bytes(datos)

        async def confirmar(bloque, _trama):
            # **Sin prompt.** El consentimiento es el comando: nadie tipea
            # `--comando dpi --nivel 1 --valor 1600` sin querer escribir eso,
            # y en la aplicacion el click cumple el mismo papel. Lo que no se
            # saca es el registro: la trama exacta se imprime igual.
            if cmd == p.CMD_MACRO:
                hexa = "\n      ".join(
                    f"trozo {i}: {t[:t[1]].hex(' ')}"
                    for i, t in enumerate(p.build_write_blocks(bloque)))
            else:
                t = p.build_write_frame(bloque)
                hexa = t[:t[1]].hex(" ")
            print(f"\n[3/6] escritura {ctx_que}")
            if ctx_aviso:
                print(ctx_aviso)
            print(f"      {hexa}")
            if eventos_nuevos is not None:
                for linea in advertencias_de_eventos(eventos_nuevos):
                    print(linea)
            print("\n[5/6] escribiendo...")
            if cmd == p.CMD_MACRO:
                print(f"      son dos tramas con "
                      f"{p.WRITE_BLOCK_PAUSE_SOFT:.2f} s entre una y otra, "
                      "que es la pausa del soft nativo")
            return True

        # --- la tasa, arriba de 1000 Hz, no se escribe por aca -----------
        #
        # **Esta corrida no haria lo que dice.** El paso 0 baja la tasa para
        # poder respaldar y el `finally` la devuelve; si lo que se escribe ES
        # la tasa, ese `finally` restaura justo lo que se acaba de pedir, la
        # relectura no ve ninguna diferencia y el veredicto sale
        # `sin-diferencias`, o sea "salio bien". Un comando que no hace nada y
        # ademas dice que funciono es lo peor de los dos mundos.
        #
        # Estaba anotado como abierto en la nota de retomar (bitacora, "La
        # nota de retomar, archivada entera") y se cierra por la salida que esa
        # nota proponia: la tasa se escribe por el camino de un solo comando. En la aplicacion lo hace
        # `sesion.Configuracion._escribir_tasa()`; en la terminal,
        # `driver/scripts/cambiar-rate.py`, que ya existe justamente para esto.
        #
        # **Solo se rechaza cuando el mouse esta arriba de 1000 Hz**, que es
        # cuando el paso 0 tiene que bajarla. Por debajo no hay nada que
        # restaurar y la Etapa 3 hace lo correcto.
        if cmd == p.CMD_REPORT_RATE:
            hz_ahora = await sesion.tasa_actual(device)
            if hz_ahora is not None and hz_ahora > sesion.RATE_MAXIMO_PARA_LEER:
                print(f"\n      el mouse esta a {hz_ahora} Hz, y por este "
                      "camino la tasa se desharia sola:\n"
                      "      el paso 0 la baja para poder respaldar y la "
                      "devuelve al terminar, asi que\n"
                      "      restauraria justo lo que pediste -y el veredicto "
                      "diria que salio bien-.\n"
                      f"\n        driver/scripts/cambiar-rate.py --valor {args.valor}"
                      "\n\n      toca un solo comando, insiste releyendo, y "
                      "respalda el campo que cambia.", file=sys.stderr)
                return 2

        # --- la Etapa 3 entera -------------------------------------------
        resultado = await sesion.aplicar(
            device, cmd=cmd, codificar=codificar, confirmar=confirmar,
            nodo=str(path), macros_extra=extra,
            macro_id=args.macro_id if cmd == p.CMD_MACRO else None,
            # Se baja la tasa sin preguntar y se la devuelve al terminar: el
            # consentimiento es el comando. La biblioteca igual deja elegir,
            # porque la aplicacion puede querer preguntar.
            bajar_la_tasa=True,
            # **Comparar bytes no sirve para cmd 8 ni cmd 9**, donde lo
            # idempotente sale distinto de lo leido a proposito. Se evalua
            # despues de codificar, que es cuando `sin_efecto` ya se sabe.
            idempotente=lambda: (not hay_cambio) or ctx_sin_efecto,
            al_leer=lambda l: print(sesion.linea_de(l)),
            al_reintentar=lambda f, e: print(sesion.aviso_de_reintento(f, e)),
            al_cortar=lambda f, m: print(f"  {m}"),
            al_guardar=guardar, al_avisar=avisar)

        tasa_original = resultado.tasa_bajada_desde
        archivo = archivos.get("antes")
        if not resultado.ok and resultado.veredicto is None:
            # Aborto de la biblioteca: no llego a haber veredicto. El motivo
            # ya tiene su texto en `sesion.MOTIVOS`.
            print(f"\n      {sesion.MOTIVOS.get(resultado.motivo, resultado.motivo)}",
                  file=sys.stderr)
            if archivo is not None:
                print(f"      respaldo previo: {archivo.name}", file=sys.stderr)
            return 1

        # --- 6. el veredicto, contado ------------------------------------
        antes, despues = resultado.antes, resultado.despues
        veredicto = resultado.veredicto
        difs = veredicto.diferencias
        cambiados = veredicto.cambiaron
        print()

        # Sin --valor la escritura era idempotente: cualquier diferencia es un
        # problema, y ninguna es el resultado bueno. Lo mismo vale cuando se
        # pidio un valor y resulto ser el que ya estaba (`sin_efecto`). Los dos
        # casos los distingue `juzgar()` por el motivo.
        if veredicto.motivo == "sin-diferencias":
            print("      SIN DIFERENCIAS. El mouse quedo exactamente como "
                  "estaba, que es lo que tenia que pasar.")
            if resultado.aplicada:
                print("      Y acuso la escritura, asi que el framing sirve.")
            return 0
        if veredicto.motivo == "idempotente-cambio-algo":
            print("      CAMBIO algo. En una escritura idempotente esto NO "
                  "tenia que pasar:")
            for d in difs:
                print(f"        {d}")
            print(f"\n      respaldo previo: {archivo.name}")
            return 1

        # Con --valor es al reves: el exito es que haya cambiado lo que se
        # pidio, y nada mas. Antes esto devolvia 1 igual, o sea
        # que el script decia "fallo" cuando habia salido todo bien.
        # Cada comando tiene su verificacion externa, y no son la misma.
        # medir-polling mide la TASA DE REPORTE, que no cambia al mover el dpi:
        # sugerirla ahi seria dar una confirmacion que no confirma nada.
        #
        # Para el dpi no hay un equivalente barato. Medirlo de verdad exige
        # mover el mouse una distancia fisica conocida, y eso a mano no sale:
        # se probo y dio entre 41 y 2545 dpi para un mouse que
        # estaba en 1600 (ver dev/models/attackshark-x8pro/docs/bitacora.md). El lector independiente que si
        # sirve es la pagina oficial, que es software del fabricante leyendo
        # los mismos bytes sin pasar por nuestro decodificador.
        for linea in consejo_de_verificacion(
                cmd, rgb=rgb, sensor=sensor, nivel=args.nivel,
                nivel_activo=args.nivel_activo,
                eventos=eventos_nuevos,
                atajo=(est.texto_de_atajo(atajo_p1, atajo_p2)
                       if atajo_p2 is not None else None),
                en_la_pagina=en_la_pagina, efectivo=efectivo,
                respaldo=archivo.name):
            print(linea)
        print()

        nombre_cmd = p.CMD_NAMES.get(cmd, f"cmd {cmd}")
        if veredicto.motivo == "no-cambio-nada":
            print("      NO CAMBIO NADA, y se pidio un cambio. O el mouse "
                  "ignoro la trama, o la relectura trajo un estado viejo.")
            print(f"\n      respaldo previo: {archivo.name}")
            return 1
        if veredicto.motivo == "cambio-otra-cosa":
            print(f"      cambio algo, pero NO {nombre_cmd}, que es lo que se "
                  "pidio:")
            for d in difs:
                print(f"        {d}")
            print(f"\n      respaldo previo: {archivo.name}")
            return 1

        print("      CAMBIO lo que se pidio:")
        for d in difs:
            print(f"        {d}")

        # El perfil completo arranca con los tres primeros bytes del bloque de
        # report rate, asi que se mueve junto con el. MEDIDO en las dos
        # direcciones (1000 -> 500 y 500 -> 1000): los mismos dos bytes
        # en los dos comandos, y nada mas en todo el mouse. Que aparezca no es
        # sorpresa; que aparezca cualquier OTRO comando, si.
        # La resta la hace `sesion.juzgar()`, que es donde vive el criterio.
        if veredicto.inesperados:
            otros = ", ".join(p.CMD_NAMES.get(c, f"cmd {c}")
                              for c in sorted(veredicto.inesperados))
            print(f"\n      OJO: tambien cambio {otros}, que no se toco. "
                  "Revisalo contra el respaldo previo antes de seguir.")
            print(f"      respaldo previo: {archivo.name}")
            return 1

        tambien = (" y el perfil completo, que lo embebe"
                   if p.CMD_PROFILE in cambiados else "")
        print(f"\n      Y nada mas: solo {nombre_cmd}{tambien}.")
        print(f"      respaldo previo: {archivo.name}")
        return 0
    except _Aborta as corte:
        # El codificador corto la corrida: su mensaje ya se imprimio donde se
        # detecto el problema. **La tasa ya volvio**: la devuelve el `finally`
        # de `sesion.aplicar()`, que es de donde viene esta excepcion.
        return corte.codigo
    finally:
        if canal is not None:
            canal.close()


if __name__ == "__main__":
    # Un Ctrl-C aca es casi siempre "esto va a fallar igual, corto": no tiene
    # que salir por un traceback de asyncio. Lo que importa decir es que el
    # paso 5 no llego a mandar nada, porque es la pregunta que uno se hace.
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n  cortado a mano antes de escribir. El mouse no cambio.",
              file=sys.stderr)
        raise SystemExit(130)
