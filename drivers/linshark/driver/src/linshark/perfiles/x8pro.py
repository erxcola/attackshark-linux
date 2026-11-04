# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""El perfil del Attack Shark X8 Pro: el unico modelo medido.

Todo lo que hay en `estructuras.py` y en `protocol.py` esta medido contra este
mouse y **solo contra este**: los tamaños de bloque, los dieciocho slots de
boton, los ocho niveles de dpi, la permutacion de los slots 4, 5 y 6. Ver el
docstring de `dispositivos.py` para el mecanismo que lee este perfil.
"""

from __future__ import annotations

from .. import protocol as p
from ..dispositivos import Perfil, Usb

X8_PRO = Perfil(
    device_id=p.DEVICE_X8_PRO,
    nombre="X8 Pro",
    marca="ATTACKSHARK",
    usb=Usb(vendor=0x1D57, producto_dongle=0xFA65, producto_cable=0x2126,
            interfaz=2, report_id=4, report_size=63, tiene_serial=False),
    # El largo que el mouse declara para cada bloque, con la cita de donde
    # salio cada numero. Los cuatro coinciden con `READ_SUB` del bundle, que
    # es lo que `test_el_perfil_no_miente` compara.
    bloques={
        p.CMD_LIGHTING: 15,     # gw.sizeTotalData
        p.CMD_DPI: 56,          # Qt.sizeTotalData
        p.CMD_BUTTONS: 59,      # el 59 literal de _fe()
        p.CMD_MACRO: 111,       # MEDIDO: lo que el soft nativo le manda
    },
    escribibles=frozenset(p.WRITABLE),
    # **Cuantos botones no lo dice el bundle**: `_fe` itera sobre las claves
    # que le pasen. Sale del bloque real y sin holgura: el mouse contesta 57 B
    # de datos y 57 = 1 profileId + 18*3 + 2 checksum. Con 17 o 19 no cierra.
    botones=18,
    # El 6 y el 7 estan en la **base** del mouse: un clic que solo se puede
    # hacer dando vuelta el mouse no arregla nada. Decidido.
    slots_para_clic_izquierdo=(1, 2, 3, 4, 5),
    slots_de_rueda=(17, 18),
    remapeo_de_slots={4: 5, 5: 6, 6: 4},
    botones_por_nombre={
        "izquierdo": 1,
        "derecho": 2,
        "rueda": 3,
        "costado-atras": 4,
        "costado-adelante": 5,
        "dpi": 6,
        "modo": 7,
    },
    # Todo esto sale de `dev/models/attackshark-x8pro/docs/evidencia.md`; los siete estan cerrados.
    como_se_supo_el_boton={
        1: "sale del bloque de fabrica, que para el clic izquierdo no tiene "
           "otra lectura razonable. Se remapea, siempre "
           "que quede un clic izquierdo en `SLOTS_PARA_CLIC_IZQUIERDO`",
        2: "sale del bloque de fabrica, que para el clic derecho no tiene "
           "otra lectura razonable",
        3: "sale del bloque de fabrica, que para el clic de rueda no tiene "
           "otra lectura razonable",
        4: "MEDIDO: se lo remapeo a \"reproducir / pausar\" "
           "(codigo 24), se lo apreto -la musica se pauso- y se lo devolvio a "
           "\"atras\". El que conto fue el reproductor del sistema, no "
           "nuestro decodificador",
        5: "MEDIDO: se remapeo ese boton fisico con el soft oficial y cambio "
           "ese slot y solo ese",
        6: "MEDIDO, y por el camino mas independiente que tiene "
           "el proyecto: al ciclarlo, el firmware escribe "
           "`Current_Dpi_level_flag` -el mismo byte que escribimos nosotros, "
           "y solo ese- y el LED toma el color de ese nivel",
        7: "MEDIDO: se lo remapeo a \"reproducir / pausar\" "
           "(codigo 24) y se apreto el boton para pasar el mouse a modo USB. "
           "Pasaron las dos cosas juntas: la musica se pauso y el mouse se "
           "desconecto del dongle",
    },
    niveles_dpi=8,
    dpi_minimo=100,
    dpi_maximo=40000,
    tasas=(125, 250, 500, 1000, 2000, 4000, 8000),
    macro_eventos_max=50,
    macro_id_min=1,
    macro_id_max=255,
    # **El RGB del cmd 5 no se ofrece en este mouse.** Se escribe, el mouse
    # acusa `0xC1`, la relectura lo devuelve cambiado y el chasis no prende
    # nada (MEDIDO; `dev/models/attackshark-x8pro/docs/evidencia.md`, donde ademas figura
    # como error del proyecto haber prometido que era "visible a simple vista"
    # sin mirar el hardware, I-W15).
    #
    # **No cierra I-W16**: que los bytes sean inertes NO esta probado, todo lo
    # observado fue con `lightMode: 0`, que es el campo ambiguo de I-W14. Por
    # eso `sesion.preparar_mutacion("color", ...)` y el `--color` del CLI
    # siguen andando: esto saca el control, no la capacidad. Otro modelo puede
    # tener RGB de verdad, y ahi el control vuelve sacando esta linea.
    campos_ausentes={
        "color": "en el X8 Pro estos bytes no encienden nada: se escriben, se "
                 "releen cambiados y el chasis no prende (MEDIDO)",
    },

    # Donde el perfil completo embebe a cada bloque: `(en el perfil, en el
    # bloque, largo)`. Sale de comparar los **126 respaldos versionados** que
    # tienen los cinco bloques; `test_el_perfil_embebe_donde_dice` lo rehace
    # contra esos mismos respaldos en cada tanda, asi que no puede quedar
    # diciendo otra cosa que la evidencia.
    #
    # El tramo de cada bloque empieza en 1 y no en 0 porque el byte 0 es el
    # `profileId`, que el perfil lleva una sola vez, adelante. El de botones es
    # la excepcion: ahi el 0 ya es el primer slot.
    #
    # **Del rate van dos bytes y no siete**: el resto del bloque de cmd 6 son
    # ceros, y casar ceros no prueba nada -la primera version de esta tabla
    # tenia ahi un tramo de cuatro ceros que coincidia siempre y no verificaba
    # nada-.
    perfil_embebe={
        6: (1, 1, 2),        # el byte de tasa y su checksum
        4: (3, 1, 47),       # los ocho niveles y los interruptores del sensor
        5: (53, 1, 8),       # hibernacion, reposo, respuesta y el RGB
        8: (62, 0, 55),      # los 18 slots y la rueda
    },
)
