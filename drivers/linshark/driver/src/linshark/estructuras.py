# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Las estructuras de configuracion del mouse, campo por campo.

Salen del bundle de la web, que las arma con nombres propios del fabricante.
Los constructores estan en `app.js`:

    co(e)   -> payload de iluminacion, para el camino WebSocket
    Vve(e)  -> el mismo, corrido 2 posiciones, para el camino WebHID viejo
    Of(e)   -> payload de dpi

y los objetos con los valores por defecto son `gw` (luz) y `Qt` (dpi). Los
alias del bundle minificado: `co` es `ak`, `Of` es `bC`, `gw` es `G` y `Qt` es
`c4`, resueltos contra el bloque `export{...}` de `app.js`.

Los dos primeros campos de toda estructura son:

    fixed           el codigo de comando (5 = iluminacion, 4 = dpi)
    sizeTotalData   el largo del bloque; el proyecto lo venia llamando `sub`

y el largo total de la trama del dispositivo sale de `sizeTotalData + 5`,
escrito asi, literal, en la primera linea de `co()` y de `Vve()`.

Este modulo es **solo lectura**: aca se decodifica lo que manda el mouse. Los
codificadores existen para verificar contra las capturas reales (la Etapa 2 de
`dev/docs/metodo.md`: el estado leido, recodificado, tiene que dar byte a byte la
trama que mando el driver oficial).

Desde el backend **si** tiene un camino de escritura, pero no
pasa por aca: `_responder_escritura()` usa `protocol.build_write_frame()` y
antes chequea modo `full`, allowlist `--permitir-escritura`, simulacro y
bateria. Ver `dev/docs/metodo.md`.
"""

from __future__ import annotations

from . import dispositivos as _disp
from . import dpi as _dpi
# La tabla de tasas vive en `protocol`, que es donde la usan el armador de
# tramas y el backend. Tenerla dos veces seria tenerla mal una vez, asi que se
# importa; no hay circularidad, `protocol` no depende de nadie del paquete.
from . import protocol as _p


# --- lo que es de ESTE mouse no se escribe aca ------------------------------
#
# Antes los numeros del X8 Pro estaban en este archivo: 56, 59,
# 18 botones, 111, los slots de la rueda, la permutacion. `dispositivos.py` los
# listaba al lado para que se leyera de una sentada que hay que medir para
# agregar un modelo, y un test los comparaba para que no se desincronizaran.
# **Tener el mismo numero en dos lados es tenerlo mal en uno de los dos el dia
# que cambie**, asi que ahora hay uno solo: el del perfil.
#
# Este modulo le pregunta al perfil activo **en cada llamada**, no al importar:
# cambiar de perfil cambia como se decodifica y como se escribe, sin tocar una
# linea de los codificadores. `test_el_perfil_manda_de_verdad` arma un perfil
# de fantasia -otros tamaños, otros botones- y verifica que el bloque salga
# distinto; si algo volviera a tener el numero adentro, se pone rojo.
#
# Los nombres de siempre -`BOTONES_CANTIDAD`, `SLOTS_DE_RUEDA`, ...- siguen
# existiendo y valen lo mismo: los resuelve `__getattr__` contra el perfil
# activo, asi que ni el CLI ni la ventana ni los tests cambiaron de vocabulario.
# **Pero se resuelven al usarlos**: guardarse uno en una variable de modulo
# -`from .estructuras import BOTONES_CANTIDAD`- lo congela, y eso es volver al
# problema que esto resuelve. Se importa el modulo y se lee el atributo.
def _perfil():
    """El perfil del mouse al que le estamos hablando ahora mismo."""
    return _disp.activo()


#: `nombre publico -> como sale del perfil`. Es la lista completa de lo que en
#: este archivo depende del modelo: si algo no esta aca, es del protocolo y
#: vale para todos.
_POR_MODELO = {
    "ILUMINACION_SIZE": lambda perfil: perfil.bloques[_p.CMD_LIGHTING],
    "DPI_SIZE": lambda perfil: perfil.bloques[_p.CMD_DPI],
    "BOTONES_SIZE": lambda perfil: perfil.bloques[_p.CMD_BUTTONS],
    "MACRO_SIZE": lambda perfil: perfil.bloques[_p.CMD_MACRO],
    "DPI": lambda perfil: _tabla_dpi(perfil),
    "BOTONES": lambda perfil: _tabla_botones(perfil),
    "ESTRUCTURAS": lambda perfil: _tablas_de(perfil),
    "BOTONES_CANTIDAD": lambda perfil: perfil.botones,
    "BOTONES_POR_NOMBRE": lambda perfil: dict(perfil.botones_por_nombre),
    # Los tres de abajo pueden **no existir** en otro mouse, y preguntar por
    # uno que no esta no puede reventar: dan `None` -y `0` el maximo-, que es
    # un slot con el que nada compara igual. Antes eran un
    # `[...]` que tiraba `KeyError` con un perfil sin boton de modo.
    "BOTONES_POR_NOMBRE_MAX": lambda perfil: max(
        perfil.botones_por_nombre.values(), default=0),
    "SLOT_DE_MODO": lambda perfil: perfil.botones_por_nombre.get("modo"),
    "SLOT_DEL_CLIC_DE_RUEDA": lambda perfil: perfil.botones_por_nombre.get(
        "rueda"),
    "COMO_SE_SUPO_EL_BOTON": lambda perfil: dict(perfil.como_se_supo_el_boton),
    "SLOTS_PARA_CLIC_IZQUIERDO": lambda perfil: perfil.slots_para_clic_izquierdo,
    "SLOTS_DE_RUEDA": lambda perfil: perfil.slots_de_rueda,
    "SLOT_ESCRITO_DE_LEIDO": lambda perfil: dict(perfil.remapeo_de_slots),
    "SLOTS_QUE_SE_REMAPEAN": lambda perfil: tuple(
        sorted(perfil.remapeo_de_slots)),
    "DPI_MINIMO_UI": lambda perfil: perfil.dpi_minimo,
    "DPI_MAXIMO_UI": lambda perfil: perfil.dpi_maximo,
    "MACRO_ID_MIN": lambda perfil: perfil.macro_id_min,
    "MACRO_ID_MAX": lambda perfil: perfil.macro_id_max,
    "MACRO_DATOS_SIZE": lambda perfil: perfil.bloques[_p.CMD_MACRO] - 2,
    "MACRO_EVENTOS_BYTES": lambda perfil: (perfil.bloques[_p.CMD_MACRO] - 2
                                           - MACRO_EVENTOS_OFFSET - 2),
    "MACRO_EVENTOS_MAX": lambda perfil: (perfil.bloques[_p.CMD_MACRO] - 2
                                         - MACRO_EVENTOS_OFFSET - 2) // 2,
}


def __getattr__(nombre: str):
    """Las constantes que son de un modelo, resueltas contra el perfil activo.

    PEP 562. Lo que no esta en `_POR_MODELO` no existe, y da el `AttributeError`
    de siempre: esto no inventa atributos.
    """
    sacar = _POR_MODELO.get(nombre)
    if sacar is None:
        raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")
    return sacar(_perfil())


def __dir__():
    return sorted(list(globals()) + list(_POR_MODELO))


# --- iluminacion (cmd 5) ----------------------------------------------------
# Transcripcion del orden en que co() escribe los campos. Verificada contra los
# 13 bytes que devolvio el mouse: el checksum interno da 0x01af, exactamente
# los dos bytes que trae la captura, y el color queda (0, 255, 0), que es el
# verde que tenia el LED cuando se leyo.
ILUMINACION_FIXED = 5
# `ILUMINACION_SIZE` -el `gw.sizeTotalData` del bundle, 15- sale del perfil,
# como todos los largos de bloque. Ver `_POR_MODELO`.

ILUMINACION = (
    # (nombre, largo, escala)  -- escala: lo que co() hace al escribir
    ("profileId", 1, None),
    ("lightMode", 1, "<<4"),
    ("breathingSpeed", 1, None),
    ("LightBrightness", 1, None),
    ("redColor", 1, None),
    ("greenColor", 1, None),
    ("blueColor", 1, None),
    ("closeTime", 1, "*2"),
    ("direction", 1, "/2"),
)

# --- lo que estos nombres NO quieren decir ---------------------
#
# Los nombres son los del fabricante y **tres de los nueve enganan**. Sale de
# leer `parameterDef()` en `dev/research/webapp/app.js` junto con el handler que
# parsea la respuesta, y cierra con los 15 bloques distintos de cmd 5 que hay
# en `dev/models/attackshark-x8pro/docs/capturas-w/`. Importa antes de escribir: si se toma "brillo 168" al
# pie de la letra y se escribe 200, se le esta moviendo otra cosa al mouse.
#
# 1. **El bloque no es solo la luz.** `parameterDef()` termina con
#    `n.direction = e.responseTime` y `n.closeTime = e.hibernateTime`. O sea
#    que cmd 5 lleva ademas el tiempo de hibernacion y el tiempo de respuesta.
#    Escribir "iluminacion" es escribir tambien eso.
#
# 2. **`breathingSpeed` son dos campos en un byte.** Literal:
#        const a = e.closeTime, o = a & 240, i = a & 15,
#              l = n.breathingSpeed & 15;
#        n.breathingSpeed = o | l
#    nibble alto = la parte alta de closeTime, nibble bajo = la velocidad. Y el
#    handler de lectura lo desarma igual: `o.breathingSpeed & 15` para la
#    velocidad y `o.breathingSpeed & 240` para rearmar closeTime. Los tres
#    valores capturados -0x03, 0x13, 0x33- dan velocidad 3 en los tres, con la
#    parte alta de closeTime en 0, 1 y 3.
#
# 3. **`LightBrightness` tambien son dos, y depende de que pantalla escribio.**
#        n.LightBrightness = (e.closeTime & 15) << 4
#                            | (lightMode == 1 || lightMode == 5
#                               ? n.LightBrightness & 15 : 8)
#    Los 15 bloques capturados tienen el nibble bajo en 8, o sea la rama del
#    `else`: **todos salieron de la pantalla de parametros**, no de la de luz.
#    Por el otro camino (`En.LightBrightness = o.brightness`) el byte si es el
#    brillo pelado. Con lo que tenemos, "brillo 168" para el 0xa8 del respaldo
#    **no esta establecido**: el mismo byte se explica igual como
#    `(closeTime & 15) << 4 | 8`. `describir()` lo dice asi.
#
# 4. **`lightMode` vale 0x00 en las 15 capturas, y hay dos lecturas.** El
#    handler lo lee `(o.lightMode & 240) >> 4`, que es lo que hace este modulo.
#    Pero en el bundle hay dos codificadores: uno escribe `e.lightMode` pelado
#    y otro `e.lightMode << 4`, y los objetos de defaults traen `lightMode: 80`
#    (0x50), que ya viene con el modo en el nibble alto. `80 << 4` con
#    `setUint8` desborda y da 0x00. O sea que "el mouse esta en modo 0" y "la
#    app oficial se comio el campo al escribirlo dos veces corrido" producen el
#    mismo byte y **no se distinguen** con estas capturas.
#
# Lo unico de esta estructura con significado sin ambiguedad son
# `redColor` / `greenColor` / `blueColor`: los escriben pelados los seis
# codificadores del bundle y los lee pelados todo handler. Por eso el unico
# cambio real que ofrece `escribir_color_luz()` es el color.

# --- dpi (cmd 4) ------------------------------------------------------------
# Orden del objeto Qt. Verificado contra los 54 bytes que devolvio el mouse:
# los ocho campos de color coinciden byte por byte con los valores por defecto
# del bundle, `dpi_ON_OFF_flag` da 0x3f = 63 como el default, y los
# `Dpi_X_setting` con sus altos dan 1200/2400/3200/5600/8000/40000, que es lo
# que muestra la pagina oficial. (Antes este comentario citaba
# 1000/2000/2700/4750/6800/24400, que es lo que da la tabla dispersa del 3311;
# ese no es el camino de este modelo. Ver `dpi.py`.)
DPI_FIXED = 4
# `DPI_SIZE` -el `Qt.sizeTotalData` del bundle, 56- sale del perfil.


def _tabla_dpi(perfil) -> tuple:
    """La tabla de campos del cmd 4 para ese modelo.

    **Cuantos niveles hay es del modelo**, no del protocolo: los dos campos de
    `Dpi_X/Y_setting` miden un byte por nivel y hay un `indication_flag` de
    tres bytes por nivel. Con ocho da los 54 B que contesto este mouse; con
    otra cantidad, el bloque entero se corre, que es justo por lo que este
    numero no puede estar escrito aca adentro.
    """
    n = perfil.niveles_dpi
    return (
        ("profileId", 1, None),
        ("SensitivityX", 1, None),
        ("SensitivityY", 1, None),
        ("dpi_ON_OFF_flag", 1, None),
        ("DPI_X_Double_Flag", 1, None),
        ("DPI_Y_Double_Flag", 1, None),
        ("Dpi_X_setting", n, None),
        ("Dpi_Y_setting", n, None),
        ("Current_Dpi_level_flag", 1, None),
        *((f"Dpi_level_{i}_indication_flag", 3, None)
          for i in range(1, n + 1)),
        ("Dpi_indication_type", 1, None),
    )

# `Dpi_Y_setting` estuvo marcado como sin confirmar porque en la primera
# captura venia casi todo en cero. **Quedo confirmado**: trae un
# `01` en el indice 5, y es justo el byte alto que hace falta para que el nivel
# 6 de 40000 (`n = 0x18f = 399`, rama de `/100`, con el bit 5 puesto en
# `DPI_X_Double_Flag`). Si el campo empezara un byte antes o despues, ese `01`
# caeria en el nivel 5 o en el 7 y los valores no darian lo que muestra la
# pagina oficial. O sea que el offset no es una eleccion nuestra: es el unico
# que hace cerrar los seis niveles a la vez.
# --- botones (cmd 8) --------------------------------------------------------
# Transcripcion de `_fe(e)` en `dev/research/webapp/app.js`, que es el constructor
# que `protocolo.md` ya nombraba como pendiente. Literal:
#
#     function _fe(e){
#       let t=0; const n=63, a=new ArrayBuffer(n), o=new DataView(a);
#       o.setUint8(t++,8); o.setUint8(t++,59); o.setUint8(t++,1);
#       let i=0;
#       Object.values(e).forEach(l=>{ o.setUint8(t++,l[0]);
#                                     o.setUint8(t++,l[1]);
#                                     o.setUint8(t++,l[2]); });
#       for(let l=3;l<t;l++) i+=o.getUint8(l);
#       o.setUint8(t++,(i&65280)>>8); o.setUint8(t++,i&255);
#       return new Uint8Array(a);
#     }
#
# De ahi salen tres cosas y ninguna hay que inferirla: `fixed` es 8,
# `sizeTotalData` es 59 -el mismo 0x3b que ya estaba en `READ_SUB`-, y cada
# boton ocupa **tres bytes**. El checksum arranca en el byte 3 del buffer, que
# sobre `datos` -que empieza en `profileId`- es `datos[1:]`, o sea exactamente
# lo que ya calcula `checksum_interno()`.
#
# **Cuantos botones no lo dice el bundle**: `_fe` itera sobre las claves que le
# pasen. Sale del bloque real, y sale sin holgura: el mouse contesta 57 B de
# datos (59 - 2, como todo bloque) y 57 = 1 profileId + 18*3 + 2 checksum. **18
# botones exactos, sin relleno.** Con 17 o 19 no cierra.
BOTONES_FIXED = 8
# `BOTONES_SIZE` (59) y `BOTONES_CANTIDAD` (18) salen del perfil: el 59 es el
# literal de `_fe()` y los 18 salen del bloque real, y **los dos son de este
# modelo**. Un mouse con menos botones tiene un cmd 8 mas corto.


def _tabla_botones(perfil) -> tuple:
    """La tabla de campos del cmd 8 para ese modelo.

    Se generan en vez de escribirse a mano porque asi es como el bundle los
    trata: `_fe` no los nombra, son posiciones. Nombrarlos aca uno por uno
    seria inventar una semantica que el bundle no da.
    """
    return (("profileId", 1, None),) + tuple(
        (f"boton{n}", 3, None) for n in range(1, perfil.botones + 1))

# El codigo de funcion, que es el primero de los tres bytes. La tabla es `Rve`
# de `app.js` (exportada como `ag`, que es lo que importa el chunk del X8 Pro
# `indexX8Pro-D0yEPypd.js`), traducida. Ahi se indexa **por el codigo crudo**:
# el chunk hace `ae[q(codigo)]` con `q = e => parseInt(e)`, o sea identidad.
#
# **Y aca hubo una falsa alarma que conviene dejar anotada.** La otra tabla del
# bundle, `sl` -la de escritura, nombre -> tripleta-, dice
# `FUN_SCROLL_UP:[10,0,0]` y `FUN_SCROLL_DOWN:[9,0,0]`, que contra esta parece
# el cuarto caso del patron de I-W10 / I-W24: escribir con una regla y leer con
# otra. **No lo es.** El bundle trae un tercer diccionario, el de etiquetas,
# donde `FUN_SCROLL_UP` lleva `label:"ScrollDown"` y `FUN_SCROLL_DOWN` lleva
# `label:"ScrollUp"`. O sea que la etiqueta compensa: las dos tablas coinciden
# en que **9 es arriba y 10 es abajo**, y lo unico equivocado es el nombre de
# la constante del fabricante. Es un nombre mentiroso, no una lectura mala.
FUNCIONES_DE_BOTON = {
    0: "funcion bloqueada",
    1: "apagado",
    2: "clic izquierdo",
    3: "clic derecho",
    4: "clic de rueda",
    5: "atras",
    6: "adelante",
    7: "doble clic",
    8: "tecla de fuego",
    9: "rueda arriba",
    10: "rueda abajo",
    11: "inclinar a la izquierda",
    12: "inclinar a la derecha",
    13: "ciclo de dpi",
    14: "dpi +",
    15: "dpi -",
    16: "puntería asistida (dpi)",
    17: "atajo de teclado",
    18: "macro",
    19: "lanzar programa",
    20: "tecla Windows",
    21: "reproductor multimedia",
    22: "pista anterior",
    23: "pista siguiente",
    24: "reproducir / pausar",
    25: "detener",
    26: "silenciar",
    27: "volumen +",
    28: "volumen -",
    29: "calculadora",
    30: "email",
    31: "favoritos del navegador",
    32: "navegador adelante",
    33: "navegador atras",
    34: "navegador detener",
    35: "mi PC",
    36: "navegador recargar",
    37: "navegador inicio",
    38: "navegador buscar",
    39: "tecla Fn",
    40: "ciclo de report rate",
    41: "ciclo de modo LED",
    43: "mostrar bateria",
    48: "LED on/off",
    50: "macro de clic izquierdo",
    51: "salir del macro de clic izquierdo",
    52: "ciclo de perfil",
    53: "perfil anterior",
    54: "perfil siguiente",
    55: "triple clic",
    56: "Fn + 0x09 = Y mas 1",
    57: "Fn + 0x0a = Y menos 1",
    58: "macro de clic izquierdo",
}

# El 60 esta en la tabla de escritura (`sl.FUN_MODE_KEY = [60,0,0]`) y **no
# esta en `Rve`**, que llega hasta el 58. Se le pone nombre aca porque es el
# valor que el mouse trae de fabrica en el boton 7, o sea que un bloque sin
# tocar ya contiene un codigo que la tabla de nombres de la pagina no cubre.
# Que hace la pagina con eso no se probo, asi que no se afirma nada mas.
FUNCIONES_DE_BOTON[60] = "tecla de modo"

# Los tres bytes son `[codigo, p1, p2]`. Para casi todas las funciones p1 y p2
# van en cero; las que los usan, en `sl`, son las de atajo de teclado
# (`FUN_COPY:[17,1,6]`, con p1 = modificadores y p2 = usage HID), el macro
# (`[18,0,id]`) y dos casos con p2 = 3 (`FUN_EASY_AIM`, `FUN_LED_LOOP`). Eso
# esta LEIDO del bundle y **no capturado**: el mouse de la casa los tiene todos
# en cero.

# **El macro es la unica de esas funciones que el proyecto expone hoy, y su p2
# no es opcional.** `[18, 0, id]`: escribirla con p2 en cero apunta a un macro
# 0, que no existe, y deja el boton muerto -el mouse acusa `0xC1` igual, asi
# que el fallo no se ve hasta que se aprieta-. Por eso `escribir_boton()` lo
# exige y el CLI pide `--macro-id`.
FUNCION_MACRO = 18

# Las otras estan nombradas para que la validacion sea **total** y no un
# `if codigo == 18`. La segunda es el atajo de teclado, y **tiene
# interfaz**: ver `escribir_atajo()` y `atajo_desde_texto()`
# mas abajo. Los dos parametros no salen solo del bundle -este mouse los tiene
# todos en cero-, tambien del bus: `soft-todo.pcap` trae `11 08 07` y
# `11 0a 16`, que son Win+D y Win+Shift+S.
FUNCIONES_CON_PARAMETRO = {
    FUNCION_MACRO: "el id del macro va en p2",
    17: "modificadores en p1 y usage HID en p2",
}

# `MACRO_ID_MIN` y `MACRO_ID_MAX` (1 y 255) salen del perfil.

CAMPOS_SIN_CONFIRMAR: frozenset[str] = frozenset()

# --- macros (cmd 9): el bloque quedo MEDIDO -------------------
#
# Antes aca decia "cero tramas de cmd 9 en las diez capturas" y el
# layout estaba tomado de `Zve(e, t, n, a)` de `app.js` -que es el que importa
# el chunk del X8 Pro (`indexX8Pro-D0yEPypd.js`, `ah as Fe`)- y arma **131**
# bytes. La captura `dev/models/attackshark-x8pro/docs/capturas-w/soft-macro-asignado.pcap` mostro que al
# mouse le llegan **111**, en el layout de la familia `Qve`/`t1e`, que son los
# constructores de 111 bytes del mismo bundle.
#
# Ojo con la conclusion: el que escribio esos 111 bytes fue el **soft nativo de
# Windows**, que no es el bundle y no esta atado a `Zve`. Lo que queda medido
# es que **este mouse recibe 111 bytes con este layout**; que la pagina le
# mande 131 sigue LEIDO del bundle y sin capturar, y si lo hace seria el cuarto
# desacuerdo entre los dos clientes oficiales.
#
# El layout, con los cuatro bloques de la captura:
#
#     [0]        9                   fixed
#     [1]        111                 sizeTotalData (= el largo del bloque)
#     [2]        id del macro        0x11 en la captura, y el bloque de
#                                    botones lo referencia: slot = `12 00 11`
#     [3]        modo de disparo     0, 1 o 2   <- lo que cambio en el A/B
#     [4..6]     0
#     [7]        repeticiones si el modo es 0; si no, 1
#     [8]        cuantos eventos
#     [9..]      los eventos, dos bytes cada uno
#     [109,110]  checksum, sumando desde el byte 3
#
# **LOS TRES MODOS DE DISPARO, MEDIDOS.** El A/B: cuatro escrituras del soft
# nativo con el mismo macro y el mismo boton, en las que **lo unico que cambio
# fue el byte [3]**: 0 -> 1 -> 2 -> 0, con el checksum interno acompanando
# (0x0c6d, 0x0c6e, 0x0c6f, 0x0c6d). El soft ofrece tres opciones y son las
# mismas tres del chunk del X8 Pro, que hace
# `S.value ? $=0 : M.value ? $=1 : z.value && ($=2)`:
#
#     0   "numero de veces a reproducir"  (Loop)       <- el unico con numero
#     1   "cualquier tecla para detener"  (Automatic)
#     2   "presionar y mantener, soltar"  (Press)
#
# Que el 0 sea el del contador **no depende del orden en que se toco la UI**:
# los cuatro constructores del bundle hacen `n===0 ? setUint8(7,a) :
# setUint8(7,1)`, o sea que el modo 0 es el unico que usa el parametro de
# repeticiones, y es el unico de los tres que la UI acompana con un campo
# numerico (`min:1, max:255` en el chunk del X8 Pro). Los nombres largos salen
# de la pantalla de macros generica (`chunks/index-BJtO3KHt.js`), que lista los
# mismos modos en el mismo orden con `triggerValue` 1..4: `LoopPlayback`,
# `StopOnAnyKey`, `HoldToPlay`, `StopOnCurrentKey`. El X8 Pro no tiene el
# cuarto.
# **El nombre del modo 1 lo puso el fabricante y no describe lo que hace.**
# `StopOnAnyKey` / "cualquier tecla para detener" es lo que dice el bundle
# (LEIDO, arriba). Lo MEDIDO el 2026-09-20, con un macro de tres eventos
# asignado a un boton y cuatro corridas iguales:
#
#   * se dispara al apretar y **sigue despues de soltar**, indefinidamente;
#   * **una tecla del teclado NO lo detiene**: se escribe esa tecla y el macro
#     sigue saliendo entremedio;
#   * **lo detiene apretar cualquier otro boton del MOUSE**.
#
# Asi que el nombre que se muestra es el medido, no el del fabricante. El suyo
# queda arriba, donde corresponde: es evidencia de lo que dice el bundle, no de
# lo que hace el firmware.
MACRO_MODOS = {
    0: "reproducir N veces",
    1: "otro boton del mouse lo detiene",
    2: "mantener apretado",
}

# Cada evento son dos bytes `[tiempo | bit de direccion, usageId]`. En la
# captura los diez eventos son `0a f1  8a f1  0a f3  8a f3  0a f5  8a f5
# 0a f4  8a f4  0a f2  8a f2`: el bit 7 marca una direccion y la otra va sin
# bit -el soft manda `0a`, mientras los constructores del bundle mandan
# `d|1`-, y los usageId son los cinco botones del mouse.
#
# **El tiempo va en milisegundos**, y eso sale de cruzar el bus con el archivo
# del soft. Los constructores del bundle no coinciden entre si: `Zve` divide
# por 10 (decimas de segundo) y `Qve`/`e1e`/`t1e` mandan el numero tal cual. El
# `.macro` de este macro guarda **retardos de 10 ms** (`dev/models/attackshark-x8pro/docs/soft-nativo.md`,
# "+4..7 retardo en ms, dword LE") y en el bus el byte es `0x0a` = 10: pasa tal
# cual, o sea la rama de `Qve`. Si fueran decimas de segundo, 10 ms viajaria
# como 1.
#
# Y arriba de 127 ms el evento **ocupa cuatro bytes**, con la centena en un
# par extra. De `Qve` en `app.js`, que es el constructor del layout de 111
# bytes -el que le llega a este mouse-:
#
#     let d=h.time;
#     if(d>127){ let c=d/100; d=d%100;
#                _===0 ? (setUint8(r++,d|1), setUint8(r++,m))
#                      : (d|=129, setUint8(r++,d), setUint8(r++,m));
#                setUint8(r++,c); setUint8(r++,3); s++; continue }
#     ...
#     l.setUint8(8, e.length+s)
#
# O sea: el par normal lleva el **resto** de dividir por 100, y detras va un
# par `[centenas, 3]`. El `3` es el marcador, y por eso se puede reconocer al
# leer: no colisiona ni con los usage de teclado HID -que empiezan en 4- ni con
# los cinco de los botones del mouse, que estan en 241..245.
#
# Y **el byte 8 no cuenta eventos: cuenta pares de bytes** (`e.length+s`, donde
# `s` son los eventos largos). Leerlo como "cantidad de eventos" y avanzar de a
# dos bytes funciona igual, porque las dos cuentas coinciden en bytes; lo que
# no funciona es mostrar cada par como un evento, que es lo que hacia antes este
# decodificador: un macro con un solo evento de 250 ms se veria como dos, el segundo con "usage 3".
#
# **Esto es INFERIDO del bundle, no medido**: no hay ninguna captura con
# eventos de mas de 127 ms -en la unica que hay, los diez son de 10 ms- y el
# que escribio ese macro fue el soft nativo, que no es el bundle. Los eventos
# decodificados por esta rama se marcan con `largo: True` para que quien los
# muestre pueda decirlo.
MACRO_USAGE_CONTINUACION = 3

# El bit 0 es otra diferencia entre los dos clientes y **no se sabe que
# significa**: el bundle lo fuerza en tres de los cuatro casos (`d|1` con
# direccion 0, `d|129` en la rama larga) y el soft nativo no lo pone nunca -en
# la captura manda `0a` y `8a` para 10 ms-. Como el mouse devuelve lo que el
# soft escribio, el tiempo se lee tal cual; si alguna vez lo escribe la pagina,
# los tiempos impares de la rama larga pueden estar 1 ms corridos.
MACRO_BIT_DIRECCION = 0x80

# **dir0 es apretar y dir1 es soltar: MEDIDO.** Se escribio el
# macro `a:dir0@10, b:dir0@10` -los dos eventos en la misma direccion, sin
# ninguno de cierre- y al apretar el boton salio `abbbbbbbb...`: la `a` y
# despues la `b`, en el orden en que se escribieron, y la ultima repitiendo.
# Que salgan caracteres dice que dir0 aprieta; que queden apretadas dice que
# dir1 es lo unico que suelta. Ver dev/models/attackshark-x8pro/docs/bitacora.md.
#
# Antes de eso era INFERIDO de cruzar el `.macro` del soft (`1 = abajo,
# 2 = arriba`, dev/models/attackshark-x8pro/docs/soft-nativo.md) con el orden del bus, y la inferencia
# resulto correcta.
#
# Se siguen aceptando los dos juegos de nombres al escribir, porque grabar un
# macro pensando en "dir0" es pensar en bytes.
MACRO_DIRECCIONES = {0: "dir0", 1: "dir1"}
MACRO_DIRECCIONES_POR_NOMBRE = {"dir0": 0, "dir1": 1,
                                "abajo": 0, "arriba": 1}
MACRO_DIRECCION_MEDIDA = ("dir0 aprieta y dir1 suelta, MEDIDO con un macro "
                          "de dos eventos dir0 que dejo las dos "
                          "teclas apretadas")

# **El firmware no suelta nada al terminar el macro** (MEDIDO,
# la misma corrida). Lo que un macro deja apretado queda apretado, y despegarlo
# no es trivial: apretar la tecla fisica **no alcanzo** -el sistema ya la tenia
# por apretada, asi que la pulsacion real no generaba un caracter nuevo- y hubo
# que desacoplar el dongle.
#
# Por eso `eventos_sin_cerrar()` existe y el CLI avisa antes de confirmar: no
# se prohibe -un macro asi es justamente el experimento que cerro la direccion-
# pero no se manda sin decir lo que va a pasar ni como se sale.
MACRO_REMEDIO_TECLA_TRABADA = ("apretar la tecla fisica no alcanza: hay que "
                               "desacoplar el dongle (MEDIDO)")

# Los eventos de macro **no usan los codigos de `FUNCIONES_DE_BOTON`**: usan
# usage IDs de teclado HID (A=4, B=5, ...) y, para los botones del mouse, cinco
# codigos propios por encima del rango de teclado. De `app.js`:
#
#     LeftMouseButton:{usageId:241}, RightClick:{usageId:242},
#     MouseWheelClick:{usageId:243}, MouseForward:{usageId:244},
#     MouseBack:{usageId:245}
#
# **Confirmados dos veces.** Una, contra un archivo del soft nativo:
# un macro grabado a mano con los cinco botones del mouse los guarda como
# `f1 f3 f5 f4 f2`, que con esta tabla se lee izquierdo, rueda, atras,
# adelante, derecho -exactamente el orden en que se apretaron-. Y el mismo dia,
# contra el bus: ese macro es el que viaja en `soft-macro-asignado.pcap`, con
# los mismos cinco usageId, cada uno dos veces.
MACRO_USAGE_BOTONES = {
    241: "clic izquierdo",
    242: "clic derecho",
    243: "clic de rueda",
    244: "adelante",
    245: "atras",
}

MACRO_FIXED = 9
# `MACRO_SIZE` (111, MEDIDO: lo que el soft nativo le manda al mouse) sale del
# perfil, como los otros largos de bloque.
MACRO_SIZE_ZVE = 131           # lo que arma el constructor que importa la web
MACRO_SIZE_LECTURA = 111       # READ_SUB[9]; el layout de adentro NO se conoce


# El bloque de LECTURA quedo MEDIDO, y es el mismo de escritura
# salvo por **dos bytes**.
#
# `sondear.py --pedir 9 --macro-id 17` devolvio los 111 bytes con el macro
# adentro, identicos byte a byte a los que el soft nativo escribio, **menos el
# checksum interno, que vuelve con los bytes al reves**: la escritura manda
# `0c 6d` y la lectura trae `6d 0c`. La suma es la misma, 0x0c6d; lo que
# cambia es el orden.
#
# Es una rareza de cmd 9 y no del camino de lectura: cmd 4, cmd 5 y cmd 8
# devuelven su checksum interno en el mismo orden en que se escribe -por eso
# `test_etapa2_ida_y_vuelta` y `test_etapa2_botones` pasan comparando lecturas
# contra escrituras-. Comprobado sobre el respaldo.
#
# **Y es la baranda de cmd 9 para el dia que entre en `WRITABLE`**, la misma
# familia que la permutacion de slots de cmd 8: devolverle al mouse el bloque
# que se le leyo, tal cual, le manda un checksum interno invertido. Hay que
# rearmarlo en big-endian.
MACRO_CHECKSUM_ORDENES = {"big": "como se escribe", "little": "como se lee"}


def parametros_de_macro(datos: bytes) -> dict | None:
    """Decodifica un bloque de macro (cmd 9), leido o escrito.

    `datos` es lo que viene despues de `[fixed, sizeTotalData]`, o sea lo
    mismo que `Frame.data`. Devuelve None si no cierra.

    El layout es el mismo en los dos sentidos; la unica diferencia es el orden
    de los dos bytes del checksum interno, que se informa en `checksumOrden`
    (ver la nota de arriba).
    """
    if len(datos) < 9:
        return None
    pares_n = datos[6]
    crudos = datos[7:7 + 2 * pares_n]
    if len(crudos) < 2 * pares_n:
        return None
    eventos = []
    i = 0
    while i < len(crudos):
        tiempo = crudos[i] & ~MACRO_BIT_DIRECCION
        usage = crudos[i + 1]
        largo = (i + 3 < len(crudos)
                 and crudos[i + 3] == MACRO_USAGE_CONTINUACION)
        if largo:
            # El par de continuacion lleva las centenas; el par normal, el
            # resto. Ver la nota de MACRO_USAGE_CONTINUACION: es la rama del
            # bundle, y no hay captura que la muestre.
            tiempo += crudos[i + 2] * 100
        eventos.append({
            "tiempo": tiempo,
            "direccion": 1 if crudos[i] & MACRO_BIT_DIRECCION else 0,
            "usageId": usage,
            # Tambien las teclas: antes solo se nombraban los cinco botones
            # del mouse y un macro de teclado se leia "usage 4, usage 224". La tabla es la del bundle.
            "nombre": nombre_de_evento(usage),
            "largo": largo,
        })
        i += 4 if largo else 2
    modo = datos[1]
    suma = sum(datos[1:len(datos) - 2]) & 0xFFFF
    cola = bytes(datos[-2:])
    orden = None
    if cola == suma.to_bytes(2, "big"):
        orden = "big"
    elif cola == suma.to_bytes(2, "little"):
        orden = "little"
    return {
        "macroId": datos[0],
        "modo": modo,
        "modoNombre": MACRO_MODOS.get(modo, f"desconocido ({modo})"),
        # El byte de repeticiones solo es el contador cuando el modo es 0; en
        # los otros dos los constructores lo fuerzan a 1, asi que leerlo como
        # repeticiones ahi seria inventar un dato.
        "repeticiones": datos[5] if modo == 0 else None,
        "eventos": eventos,
        "checksumSuma": suma,
        "checksumOrden": orden,
        "checksum_ok": orden is not None,
    }


def _tablas_de(perfil) -> dict:
    """`cmd -> (nombre, tabla de campos, largo)` para ese modelo.

    Es `ESTRUCTURAS`, que sigue existiendo con ese nombre y se arma con el
    perfil que este activo. Las tres entradas dependen del modelo: dos por el
    largo del bloque y dos por cuantos campos tiene adentro.
    """
    return {
        ILUMINACION_FIXED: ("iluminacion", ILUMINACION,
                            perfil.bloques[_p.CMD_LIGHTING]),
        DPI_FIXED: ("dpi", _tabla_dpi(perfil), perfil.bloques[_p.CMD_DPI]),
        BOTONES_FIXED: ("botones", _tabla_botones(perfil),
                        perfil.bloques[_p.CMD_BUTTONS]),
    }


def decodificar(cmd: int, datos: bytes) -> dict | None:
    """Parte los datos de una respuesta en los campos de su estructura.

    `datos` es lo que viene despues de [cmd, sizeTotalData] en la trama, o sea
    lo mismo que `Frame.data`. Devuelve None si no conocemos la estructura.
    """
    entrada = _tablas_de(_perfil()).get(cmd)
    if entrada is None:
        return None
    _, campos, _ = entrada
    salida: dict = {}
    i = 0
    for nombre, largo, escala in campos:
        if i + largo > len(datos):
            break
        trozo = datos[i:i + largo]
        valor = trozo[0] if largo == 1 else bytes(trozo)
        if escala == "<<4":
            valor >>= 4
        elif escala == "*2":
            valor //= 2
        elif escala == "/2":
            valor *= 2
        salida[nombre] = valor
        i += largo
    # Lo que sobra son el checksum interno de la estructura y el relleno.
    if i < len(datos):
        salida["_cola"] = bytes(datos[i:])
    return salida


def offsets(cmd: int) -> dict[str, tuple[int, int]]:
    """`{campo: (offset, largo)}` de la estructura, sacado de la tabla.

    Los offsets no se escriben a mano en ningun lado: se derivan de la misma
    tabla que usa `decodificar()`, asi que no pueden quedar desfasados de ella.
    """
    entrada = _tablas_de(_perfil()).get(cmd)
    if entrada is None:
        raise KeyError(f"no conocemos la estructura del cmd {cmd}")
    _, campos, _ = entrada
    salida, i = {}, 0
    for nombre, largo, _escala in campos:
        salida[nombre] = (i, largo)
        i += largo
    return salida


def fin_de_campos(cmd: int) -> int:
    """Offset donde terminan los campos y arranca el checksum interno."""
    return sum(largo for _, largo, _ in _tablas_de(_perfil())[cmd][1])


def checksum_interno(cmd: int, datos: bytes) -> int:
    """El primer checksum, el que va adentro de la estructura.

    En `co()` es `for (l = 3; l < o; l++) i += buf[l]`, o sea la suma desde el
    byte 3 del buffer -que es `[fixed, sizeTotalData, profileId, ...]`- hasta
    donde arranca el checksum. Sobre `datos`, que empieza en `profileId`, eso
    es `datos[1:fin_de_campos]`.

    **MEDIDO** contra las capturas del driver oficial: 61 tramas
    de dpi y de iluminacion, de la web y del soft, con valores distintos, y las
    61 traen exactamente esta suma en los dos bytes siguientes. Antes esta
    funcion sumaba el bloque entero -incluido el propio checksum y el relleno-
    y no daba ese numero en ningun caso.
    """
    return sum(datos[1:fin_de_campos(cmd)]) & 0xFFFF


def checksum_interno_cierra(cmd: int, datos: bytes) -> bool | None:
    """Si el checksum que trae el bloque es el que le corresponde.

    Devuelve None para los comandos que **no tienen** checksum interno -cmd 6,
    cmd 10 y cmd 11 no estan en la tabla- y para un bloque demasiado corto para
    alojarlo: ahi no hay nada que juzgar, y un False seria una alarma inventada.

    **Es el detector de lecturas corrompidas**, y no es una precaucion teorica.
    El 2026-09-20 el canal por cable devolvio, pedido el bloque de cmd 5, el
    payload entero de cmd 6 -`01 74 8b 00 00 00 00`- relleno con ceros. El byte
    0 venia bien, asi que `Cable._frame()` lo dejo pasar; lo unico que no
    cerraba era este checksum. El bloque fue de ahi a un codificador, que le
    cambio su byte y **lo recalculo**, y salio al mouse con el checksum bueno
    sobre datos ajenos.

    Cierra en **375 de 375** bloques de cmd 4, 5 y 8 de los 125 respaldos
    versionados, y falla en el unico bloque que se sabe corrompido. O sea que
    no da falsos positivos sobre toda la evidencia que hay.
    """
    try:
        fin = fin_de_campos(cmd)
    except KeyError:
        return None
    if len(datos) < fin + 2:
        return None
    return int.from_bytes(datos[fin:fin + 2], "big") == \
        checksum_interno(cmd, datos)


def perfil_discrepa(cmd: int, perfil: bytes, bloque: bytes) -> str | None:
    """Si el perfil completo y el bloque suelto dicen cosas distintas.

    Devuelve None cuando concuerdan, cuando este modelo no declara donde
    embebe a `cmd`, o cuando alguno de los dos es mas corto que el tramo: ahi
    no hay nada que cruzar, y un "discrepan" seria una alarma inventada.

    **Es la unica red que cubre a cmd 10**, que no tiene checksum interno y es
    el **testigo de toda escritura** por el camino de la relectura acotada: si
    el perfil viene sangrado, el veredicto del paso 6 se arma sobre bytes de
    otro bloque y hoy no lo notaria nadie. Y de paso da segunda opinion sobre
    cmd 4, 5, 6 y 8, que es barata porque el perfil ya se lee igual.

    Que el perfil embebe a los demas estaba en `evidencia.md` desde el primer
    respaldo por cable; lo que faltaba era cruzarlo en vez de mirarlo.
    """
    donde = _perfil().perfil_embebe.get(cmd)
    if donde is None:
        return None
    po, bo, largo = donde
    if len(perfil) < po + largo or len(bloque) < bo + largo:
        return None
    del_perfil, del_bloque = perfil[po:po + largo], bloque[bo:bo + largo]
    if del_perfil == del_bloque:
        return None
    return (f"el perfil completo dice {del_perfil.hex(' ')} y el bloque suelto "
            f"dice {del_bloque.hex(' ')}")


def poner_checksum_interno(cmd: int, datos: bytes) -> bytes:
    """Devuelve `datos` con su checksum interno recalculado."""
    fin = fin_de_campos(cmd)
    if len(datos) < fin + 2:
        raise ValueError(
            f"el bloque mide {len(datos)} B y el checksum interno del cmd "
            f"{cmd} va en [{fin}:{fin + 2}]")
    salida = bytearray(datos)
    salida[fin:fin + 2] = checksum_interno(cmd, datos).to_bytes(2, "big")
    return bytes(salida)


# --- lo que cmd 5 lleva de verdad en el X8 Pro ------------------------------
# Los nombres del fabricante no dicen esto y la tabla de campos no puede
# expresarlo, porque dos valores de la interfaz viajan **partidos entre dos
# bytes**. Sale del escritor propio del modelo,
# `dev/research/webapp/chunks/indexX8Pro-BTVvPdTw.js`, funcion `_()`:
#
#     const o = t.parameterX8Pro.closeTime, e = o & 240, l = o & 15,
#           u = p.breathingSpeed & 15;
#     p.breathingSpeed = e | u;
#     if (p.lightMode == 1 || p.lightMode == 5) { ... }
#     else p.LightBrightness = l << 4 | 8;
#     p.direction = t.parameterX8Pro.responseTime;
#
# O sea que el tiempo de hibernacion de la pantalla de parametros se guarda
# **en el nibble alto de dos bytes distintos**: el alto de `closeTime` va al
# nibble alto de `breathingSpeed` y el bajo al nibble alto de
# `LightBrightness`. El tiempo de respuesta va entero en `direction`.
#
# **MEDIDO contra los 16 bloques distintos** que hay entre las capturas (web y
# soft) y los respaldos: los 16 reconstruyen una hibernacion en 1..60 y una
# respuesta en 2..25, sin una sola excepcion. El 2..25 no es una eleccion
# nuestra: es exactamente el rango del control, que el chunk calcula como
# `Math.floor(2 + 23 * (v - 0) / 100)`, y las capturas tocan los dos extremos.
#
# **El campo se midio** con `driver/scripts/medir-hibernacion.py`, y
# gobierna un temporizador real: con hibernacion 1 el latido espontaneo del
# mouse paro entre los 88 y los 92 s de quietud, y con hibernacion 10 no paro en
# 358 s, en dos corridas que encierran a la primera. El corte se mueve con lo
# que escribimos.
#
# Pero que sean **minutos** sigue siendo INFERIDO: 88 s no son 60 s. Los valores
# observados son 1, 10, 17, 23, 25, 49 y 60, y un maximo de 60 con minimo de 1
# tiene la forma de un temporizador de sueño; con un solo punto medido aguantan
# tanto "escalon de ~32 s + N minutos" (predice 92) como "N x 90 s" (predice
# 90). Se separan con una corrida a hibernacion 2: 150 s contra 180 s.

HIBERNACION_MIN, HIBERNACION_MAX = 1, 60      # minutos, slider SleepTimer

# El tiempo de respuesta se escribe en el byte `direction` **dividido por dos**
# (`a.setUint8(o++, e.direction / 2)` en el serializador de `app.js`). El
# control del X8 Pro es un slider de 4..50 paso 2, asi que el byte va 2..25.
#
# OJO: el proyecto justificaba este rango con `Math.floor(2 + 23*v/100)`. Esa
# formula existe en el chunk pero es de **otro** control: se le aplica a
# `Level1SleepTimer`, no a `responseTime`, y sobre su rango (0.5..30) da 2..8.
# El 2..25 sale del slider propio, que es mejor evidencia.
RESPUESTA_MIN, RESPUESTA_MAX = 2, 25          # byte; la UI muestra el doble
RESPUESTA_UI_MIN, RESPUESTA_UI_MAX = 4, 50
#: Y va **de a dos**, porque el byte viaja a la mitad (`KeyResponseTime/2`) y
#: tiene que dar entero. Ya estaba dicho en el mensaje de error de
#: `escribir_parametros_luz()` ("4..50 paso 2"); esta con nombre para que una
#: interfaz pueda mover el control de a dos en vez de ofrecer impares que el
#: codificador va a rechazar.
RESPUESTA_UI_PASO = 2

# El OTRO temporizador de reposo, el corto. Viaja en el byte `closeTime`
# **multiplicado por dos**, o sea en medios minutos: `hibernateTime = 0.5` es
# el byte 1. Los dos extremos salen del slider `Level1SleepTimer` del chunk del
# X8 Pro (`min:.5, max:30, step:.5`).
REPOSO_MIN, REPOSO_MAX = 0.5, 30.0            # minutos
#: De a medio minuto: el byte `closeTime` son medios minutos y no hay forma de
#: representar otra cosa (ver `escribir_reposo_ligero`).
REPOSO_PASO = 0.5
REPOSO_BYTE_MIN, REPOSO_BYTE_MAX = 1, 60


def parametros_de_luz(datos: bytes) -> dict | None:
    """Los dos valores de la pantalla de parametros que viajan en cmd 5.

    `datos` es lo que devolvio el mouse para el cmd 5. Devuelve None si el
    bloque es mas corto de lo que hace falta.

    Devuelve tambien `en_rango`, que es lo que permite darse cuenta de que la
    lectura esta mal: si el desempaquetado fuera equivocado, los numeros se
    irian de los rangos del control oficial. En los 16 bloques conocidos no se
    va ninguno.
    """
    pos = offsets(ILUMINACION_FIXED)
    fin = max(off + largo for off, largo in pos.values())
    if len(datos) < fin:
        return None
    bs = datos[pos["breathingSpeed"][0]]
    lb = datos[pos["LightBrightness"][0]]
    hibernacion = (bs & 0xF0) | (lb >> 4)
    respuesta = datos[pos["direction"][0]]
    # El byte `closeTime` NO es la hibernacion -esa va partida en los nibbles
    # de arriba-: es el temporizador de reposo corto, en medios minutos.
    reposo_byte = datos[pos["closeTime"][0]]
    return {
        "hibernateTime": hibernacion,
        "responseTime": respuesta,
        "responseTimeUI": respuesta * 2,
        "reposoByte": reposo_byte,
        "reposoMin": reposo_byte / 2,
        "breathingSpeed": bs & 0x0F,
        "lightMode": datos[pos["lightMode"][0]] >> 4,
        "en_rango": (HIBERNACION_MIN <= hibernacion <= HIBERNACION_MAX
                     and RESPUESTA_MIN <= respuesta <= RESPUESTA_MAX),
        "reposo_en_rango": REPOSO_BYTE_MIN <= reposo_byte <= REPOSO_BYTE_MAX,
    }


#: Los comandos cuyo bloque se puede juzgar antes de mandarlo. Hoy es uno
#: solo, y los demas **lo dicen** en vez de contestar que estan bien:
#: inventarle un rango a cmd 4 o a cmd 8 sin una captura que mueva esos campos
#: seria exactamente lo que este proyecto no hace.
CMDS_CON_RANGO = frozenset({ILUMINACION_FIXED})


def fuera_de_rango(cmd: int, datos: bytes) -> str | None:
    """Por que `datos` no puede ser un bloque sano de `cmd`. None si lo es.

    Es la misma cuenta que `parametros_de_luz()["en_rango"]`, que hasta ahora
    solo se miraba **al imprimir** un respaldo. Mirarla antes de escribir es lo
    que faltaba: los codificadores de cmd 5 tocan su campo y **copian del
    bloque que recibieron**, asi que una lectura mala se convierte en una
    escritura mala, con el checksum recalculado -o sea valida- y nada aguas
    abajo puede notarlo.

    Paso de verdad (2026-09-20, por cable): una relectura de cmd 5 volvio
    `01 74 8b 00 00 00 00 01 00 01 00` -hibernacion 128 min, respuesta 0- y
    `escribir_reposo_ligero()` la mando de vuelta tal cual, con el reposo bien
    puesto. El mouse quedo con cuatro campos que nadie pidio. Ver
    `dev/models/attackshark-x8pro/docs/bitacora.md`.

    **Juzga el bloque que se va a escribir, no el que se leyo.** Asi cubre
    tambien un codificador roto, y sobre todo **deja pasar un bloque bueno
    escrito sobre un mouse que ya quedo mal**, que es justo lo que hace falta
    para poder restaurarlo.

    Para los comandos que no estan en `CMDS_CON_RANGO` devuelve None **porque
    no tiene con que juzgar**, no porque el bloque este bien.
    """
    if cmd not in CMDS_CON_RANGO:
        return None
    par = parametros_de_luz(datos)
    if par is None:
        return (f"el bloque mide {len(datos)} B y la estructura de "
                "iluminacion necesita mas")
    malos = []
    if not (HIBERNACION_MIN <= par["hibernateTime"] <= HIBERNACION_MAX):
        malos.append(f"hibernacion {par['hibernateTime']} min, fuera de "
                     f"{HIBERNACION_MIN}..{HIBERNACION_MAX}")
    if not (RESPUESTA_MIN <= par["responseTime"] <= RESPUESTA_MAX):
        malos.append(f"respuesta {par['responseTimeUI']}, fuera de "
                     f"{RESPUESTA_UI_MIN}..{RESPUESTA_UI_MAX}")
    if not par["reposo_en_rango"]:
        malos.append(f"reposo {par['reposoMin']:g} min, fuera de "
                     f"{REPOSO_MIN:g}..{REPOSO_MAX:g}")
    return ", ".join(malos) or None


# --- tres cosas que salieron del bus --------------------------
#
# `dev/models/attackshark-x8pro/docs/SIGUIENTE-SESION.md` decia que botones y macros "no tienen capturas".
# **Para botones era falso**: hay 15 bloques de cmd 8 entre `soft-todo.pcap`,
# `web-todo.pcap`, `soft-rates-anotados.pcap` y `soft-rate-8000-a-1000.pcap`.
# Se encontraron buscando el bloque por su contenido, sin asumir el layout de
# la trama. Es la lección 1 del proyecto otra vez: la doc heredada no es
# evidencia, ni siquiera cuando dice que algo falta.
#
# 1. NINGUN CLIENTE OFICIAL LEE LOS BOTONES.
#
# Los 15 bloques van en direccion OUT (host -> mouse). Cero en IN. Y no es que
# las capturas no tengan lecturas: `web-arranque-dpi-y-rate.pcap` trae la
# respuesta del mouse para luz y para dpi cuando la pagina se conecta, y ahi no
# hay ningun bloque de botones. O sea que los dos clientes escriben este
# comando desde su propio estado guardado y **nunca lo releen**.
#
# 2. LOS DOS CLIENTES ESCRIBEN LA RUEDA AL REVES UNO DEL OTRO.
#
#     soft nativo (13 bloques)   slot 17 = 0x0a, slot 18 = 0x09
#     pagina web  ( 3 bloques)   slot 17 = 0x09, slot 18 = 0x0a
#
# Sin una sola excepcion, con los otros 16 slots iguales, y los dos son
# escrituras -asi que la comparacion es directa y no la ensucia el punto 3-.
# El bloque que la web escribe al final de su captura, cuando el usuario habia
# devuelto todo a fabrica, queda distinto del de fabrica **exactamente en esos
# dos bytes**: por el camino de la web el mouse no vuelve a como estaba.
#
# **El orden del soft nativo es el correcto. MEDIDO**: con el
# mouse en `slot 17 = 0x0a, slot 18 = 0x09` -que es lo que se lee, y lo que el
# soft escribe- el scroll anda derecho, verificado girando la rueda. Es la
# segunda verificacion a simple vista del proyecto, despues del LOD.
#
# Que los slots 17 y 18 no se remapeen entre lectura y escritura -al reves que
# los del punto 3- sale de los mismos bytes: el soft escribe `0a, 09` y el
# mouse devuelve `0a, 09`. Si se intercambiaran, se leeria `09, 0a`.
#
# **Y la otra mitad tambien quedo MEDIDA, el mismo dia**: se abrio la pagina
# oficial y se toco un boton -con eso escribe su bloque, capturado en
# `dev/models/attackshark-x8pro/docs/capturas-w/web-rueda-orden-web.pcap` con `slot 17 = 09, slot 18 = 0a`-
# y al girar la rueda **el scroll salio invertido**. O sea que estos dos bytes
# **no son inertes**: la pagina oficial rompe la rueda con solo conectarse y
# escribir. No es un desacuerdo cosmetico.
#
# El costo de esa prueba tambien quedo anotado: para volver el scroll hubo que
# darle "restaurar valores por defecto" en la pagina, que ademas le puso el
# report rate en 8000 Hz, que es donde el canal de configuracion no responde
# desde Linux. Ver dev/models/attackshark-x8pro/docs/bitacora.md.
#
# 3. LOS SLOTS 4, 5 Y 6 NO SE LEEN EN EL ORDEN EN QUE SE ESCRIBEN. [MEDIDO]
#
# El soft nativo cerro su captura 16:16 devolviendo el mouse a
# fabrica, y ese bloque lleva `0d 05 06` en los slots 4-6. El respaldo de las
# **16:51 del mismo dia**, 35 minutos despues, lee `05 06 0d`. Los tres valores
# estan, corridos un lugar:
#
#     lo escrito en 4 (0d, ciclo de dpi) se lee en 6
#     lo escrito en 5 (05, atras)        se lee en 4
#     lo escrito en 6 (06, adelante)     se lee en 5
#
# No es una rotacion global -los slots 1, 2 y 3 coinciden- sino un remapeo de
# esos tres, y encaja con que la UI oficial los liste en el orden en que el
# usuario los ve y el firmware los guarde en el suyo. Los 44 respaldos leen
# siempre `05 06 0d`, incluidos los posteriores a las capturas.
#
# **MEDIDO con un A/B directo.** En
# `dev/models/attackshark-x8pro/docs/capturas-w/soft-boton4-vuelve-adelante.pcap` el soft escribe el bloque a
# las 17:21:05 con `0d 05 06` en los slots 4-6, y `dev/models/attackshark-x8pro/respaldos/20260910-172258.json`
# lo lee a las 17:22:58 -misma sesion, una hora y cincuenta segundos despues-
# con `05 06 0d`. Los otros quince slots, identicos. La permutacion se cumple en
# los tres, sin excepcion:
#
#     escrito[4] ciclo de dpi -> leido[6] ciclo de dpi
#     escrito[5] atras        -> leido[4] atras
#     escrito[6] adelante     -> leido[5] adelante
#
# Ya no hace falta razonar sobre capturas de dias distintos.
#
# **El experimento previo, que la habia dejado a un paso.** Se remapeo con el soft nativo el
# boton fisico del costado-adelante a "reproducir / pausar" y se leyo desde
# Linux con `respaldar.py`, sin escribir un byte. Cambio **un solo slot, el 5**
# -de `06` (adelante) a `18` (reproducir / pausar)-, mas el checksum y su
# reflejo en el perfil completo.
#
# Eso cierra la cadena, porque el soft escribe "adelante" en **su** slot 6:
#
#     escrito 4 (ciclo de dpi) -> leido 6      \
#     escrito 5 (atras)        -> leido 4       > y el boton fisico confirma
#     escrito 6 (adelante)     -> leido 5      /   este par
#
# El boton del costado-adelante es real y se puede apretar: que su remapeo caiga
# en el slot 5 leido, cuando el soft lo escribe en el 6, es la observacion que
# no depende de ninguna tabla.
#
# Y esto es una baranda para cuando cmd 8 entre en WRITABLE: devolverle al
# mouse el bloque que se le leyo, tal cual, **le rota tres botones**. Esa
# relectura idempotente es con lo que empieza cada Etapa 3, asi que el
# codificador de cmd 8 tiene que traducir por `SLOT_ESCRITO_DE_LEIDO` antes de
# mandar nada.
# `SLOTS_DE_RUEDA` (17 y 18) sale del perfil: cuales son los dos slots de la
# rueda es de este modelo. Los codigos de scroll, en cambio, son del protocolo.
RUEDA_COMO_EL_SOFT = (10, 9)      # lo que el soft nativo escribe en 17 y 18
RUEDA_COMO_LA_WEB = (9, 10)       # lo que escribe la pagina

# La permutacion vive en el perfil (`remapeo_de_slots`), como `{slot leido:
# slot escrito}`: `{4: 5, 5: 6, 6: 4}` en este mouse, y en otro puede no
# existir o ser otra. Desde la usa `_bloque_de_botones()`, que es
# el unico camino a escribir cmd 8: el codificador decide explicitamente en que
# orden manda los slots en vez de heredar el de la lectura.
#
# `SLOTS_QUE_SE_REMAPEAN` -los tres slots del punto 3- son sus claves, y se
# siguen leyendo con ese nombre.

# El orden de rueda que deja el scroll derecho, medido girandola.
RUEDA_CORRECTA = RUEDA_COMO_EL_SOFT


# --- y hay TRES numeraciones para el mismo boton ----------------------------
#
# La pantalla de botones del soft nativo numera **1 clic izquierdo, 2 clic
# derecho, 3 medio, 4 adelante, 5 atras** (observado). Contra los
# dos bloques, para los mismos botones fisicos:
#
#     boton fisico    UI del soft   slot escrito   slot leido
#     clic izquierdo        1             1             1
#     clic derecho          2             2             2
#     rueda (medio)         3             3             3
#     adelante              4             6             5
#     atras                 5             5             4
#     ciclo de dpi        (aparte)        4             6
#
# O sea que **ni la UI ni el bloque escrito ni el leido coinciden**, y el unico
# que ordena los dos laterales como "atras, adelante" es el bloque escrito. El
# slot 4 escrito es el boton de dpi, que la UI no numera entre esos cinco: eso
# explica el corrimiento sin necesidad de postular nada raro.
#
# Para la aplicacion propia esto se resuelve igual que `--lod` en milimetros:
# **hacia afuera un nombre que signifique algo** -"adelante", "atras"- y hacia
# adentro el slot que el firmware use. Heredar cualquiera de las tres
# numeraciones seria elegir el error de otro.
BOTONES_UI_DEL_SOFT = {1: 1, 2: 2, 3: 3, 4: 5, 5: 4}   # numero de UI -> slot leido
BOTONES_UI_A_SLOT_ESCRITO = {1: 1, 2: 2, 3: 3, 4: 6, 5: 5}


def detalle_de_slot(codigo: int, p1: int, p2: int) -> str:
    """Como se dice un slot completo, con su parametro si lo lleva.

    "atajo de teclado" y "macro" a secas no alcanzan: los dos tienen adentro
    un dato elegido -la combinacion de teclas, el id del macro- y esconderlo
    es lo que hace que un cliente muestre "macro" para un boton que apunta a
    un macro que no existe. El nombre solo queda para las otras 52 funciones,
    donde `p1` y `p2` van en cero.
    """
    nombre = FUNCIONES_DE_BOTON.get(codigo, f"codigo {codigo} sin nombre")
    if codigo == FUNCION_ATAJO:
        return f"{nombre} {texto_de_atajo(p1, p2)}"
    if codigo == FUNCION_MACRO:
        return f"{nombre} {p2}" if p2 else f"{nombre} SIN ID (boton muerto)"
    # Un `p1`/`p2` que no sea cero en las demas funciones no se calla: puede
    # ser una de las que el bundle escribe con p2 = 3 (`FUN_EASY_AIM`,
    # `FUN_LED_LOOP`) o algo que no vimos nunca.
    if p1 or p2:
        return f"{nombre} (p1={p1}, p2={p2})"
    return nombre


def botones_de(datos: bytes) -> list[dict] | None:
    """Los 18 slots de cmd 8, cada uno con su funcion traducida.

    `datos` es lo que devolvio el mouse para el cmd 8. Devuelve None si el
    bloque es mas corto que la estructura.

    Cada slot son tres bytes `[codigo, p1, p2]`. `p1` y `p2` van en cero salvo
    en los atajos de teclado (`p1` = mascara de modificadores, `p2` = usage
    HID) y en el macro (`p2` = id). Eso **quedo capturado**, no solo leido: en
    `soft-todo.pcap` hay dos bloques con `11 08 07` y `11 0a 16`, que son
    exactamente `FUN_SHOW_DESKTOP:[17,8,7]` y `FUN_SCREEN_CAPTURE:[17,10,22]`
    de la tabla `sl` del bundle.
    """
    pos = offsets(BOTONES_FIXED)
    fin = fin_de_campos(BOTONES_FIXED)
    if len(datos) < fin:
        return None
    salida = []
    for n in range(1, _perfil().botones + 1):
        off, largo = pos[f"boton{n}"]
        trozo = datos[off:off + largo]
        salida.append({
            "indice": n,
            "codigo": trozo[0],
            "p1": trozo[1],
            "p2": trozo[2],
            "nombre": FUNCIONES_DE_BOTON.get(
                trozo[0], f"codigo {trozo[0]} sin nombre"),
            # `nombre` es la funcion; `detalle` es la funcion con su
            # parametro, que en el atajo y en el macro es la mitad del dato.
            "detalle": detalle_de_slot(trozo[0], trozo[1], trozo[2]),
            "bytes": bytes(trozo),
        })
    return salida


def orden_de_rueda(botones: list[dict]) -> str:
    """Cual de los dos clientes oficiales escribio los slots de la rueda.

    Ver la nota de `SLOTS_DE_RUEDA`: los dos los escriben al reves uno del
    otro, y cual deja la rueda derecha quedo MEDIDO girandola
    con los dos ordenes puestos.

    Sobre un bloque leido es directo: estos dos slots **no** se remapean -el
    soft escribe `0a, 09` y el mouse devuelve `0a, 09`-, al reves que los del
    punto 3 de esa nota.
    """
    par = tuple(b["codigo"] for b in botones
                if b["indice"] in _perfil().slots_de_rueda)
    if par == RUEDA_COMO_EL_SOFT:
        return "como el soft nativo (el que deja el scroll derecho)"
    if par == RUEDA_COMO_LA_WEB:
        return "como la pagina web (el que deja el scroll invertido)"
    return "en un orden que no es el de ninguno de los dos clientes"


def describir(cmd: int, datos: bytes) -> str:
    """Una linea legible, para los logs y las sondas."""
    # Cmd 9 va antes de `decodificar()` a proposito: no esta en `ESTRUCTURAS`
    # -su lista de eventos es de largo variable y la tabla de campos no puede
    # expresar eso- asi que `decodificar()` devuelve None y cortaria la
    # funcion antes de llegar aca.
    if cmd == MACRO_FIXED:
        m = parametros_de_macro(datos)
        if m is None:
            return f"bloque de {len(datos)} B, no cierra como macro"
        pasos = []
        for e in m["eventos"]:
            quien = e["nombre"] or f"usage {e['usageId']}"
            # No se dice "abajo"/"arriba" porque cual de los dos es el bit 7 no
            # esta medido: se muestra el bit tal cual.
            # El `?` marca el tiempo que salio de la rama larga del bundle,
            # que ninguna captura mostro: se muestra, y se dice que es
            # inferido, en vez de callarlo o de no leerlo.
            largo = "?" if e.get("largo") else ""
            pasos.append(f"{quien} dir{e['direccion']} {e['tiempo']}{largo} ms")
        if any(e.get("largo") for e in m["eventos"]):
            pasos.append("[los tiempos con ? salen de la rama larga del "
                         "bundle, sin captura que la confirme]")
        repes = "" if m["repeticiones"] is None else f" x{m['repeticiones']}"
        aviso = "" if m["checksum_ok"] else "  [!] CHECKSUM INTERNO MAL"
        if m["checksumOrden"] == "little":
            aviso = "  (checksum interno al reves, como lo devuelve el mouse)"
        return (f"macro {m['macroId']}, modo {m['modo']} "
                f"({m['modoNombre']}){repes}, "
                f"{len(m['eventos'])} eventos: {', '.join(pasos)}{aviso}")
    campos = decodificar(cmd, datos)
    if campos is None:
        return ""
    if cmd == DPI_FIXED:
        # **Se muestran los dos, y el orden importa.**
        #
        # La pagina oficial LEE los bytes con la tabla dispersa del 3311 -lo
        # tiene hardcodeado: `getSensorType()` mapea `X8Pro: "3311"` y
        # `parseDpiSettings()` llama a `convertBytesToDpi3311()`- y ESCRIBE con
        # `Pu()`, que es lineal. Las dos cosas a la vez, o sea que la propia
        # aplicacion del fabricante se contradice: al conectarse lee un valor
        # con una formula y lo reescribe con la otra.
        #
        # Cual de las dos corresponde al dpi que hace el sensor **no se sabe**.
        # Ver dev/models/attackshark-x8pro/docs/bitacora.md. Hasta que se mida, mostrar uno solo
        # seria elegir por el que lee: primero va el de la pagina, porque es el
        # numero que el usuario tiene delante y contra el que va a comparar.
        xs = campos.get("Dpi_X_setting", b"\0" * 8)
        ys = campos.get("Dpi_Y_setting", b"\0" * 8)
        doble = campos.get("DPI_X_Double_Flag", 0)
        como_la_pagina = [n for n in _dpi.decodificar_niveles(xs, ys, doble) if n]
        lineales = [n for n in _dpi.niveles_lineales(xs, ys, doble) if n]
        texto = (f"perfil {campos.get('profileId')}, "
                 f"nivel actual {campos.get('Current_Dpi_level_flag')}, "
                 f"dpi: {', '.join(map(str, como_la_pagina))}")
        if lineales != como_la_pagina:
            texto += ("  |  lo mismo con Pu(), que es como se escribe: "
                      + ", ".join(map(str, lineales)))
        # Los cuatro interruptores viajan en el mismo bloque y la pagina no los
        # muestra bien, asi que conviene tenerlos a la vista cada vez que se
        # lee cmd 4: son lo que se pisa sin querer al escribir un dpi.
        sen = parametros_de_sensor(datos)
        if sen is not None:
            def _si(v):
                return "ON" if v else "OFF"
            texto += (f"  |  LOD {LOD_NOMBRES.get(sen['lod'], sen['lod'])}, "
                      f"ripple {_si(sen['ripple'])}, "
                      f"angle snapping {_si(sen['angle_snapping'])}, "
                      f"motion sync {_si(sen['motion_sync'])}")
            if sen["pagina_angle_snapping"] != sen["angle_snapping"] or \
               sen["pagina_ripple"] != sen["ripple"]:
                texto += ("  [la pagina oficial mostraria "
                          f"snapping {_si(sen['pagina_angle_snapping'])}, "
                          f"ripple {_si(sen['pagina_ripple'])}: lee mal estos "
                          "bytes]")
        return texto
    if cmd == BOTONES_FIXED:
        # Se listan solo los slots asignados: los apagados son diez de los
        # dieciocho y llenan la linea sin decir nada. La rueda va aparte porque
        # es lo unico de este bloque en lo que los dos clientes oficiales no
        # coinciden.
        bots = botones_de(datos)
        if bots is None:
            return f"bloque de {len(datos)} B, mas corto que la estructura"
        asignados = [b for b in bots
                     if b["indice"] not in _perfil().slots_de_rueda
                     and b["codigo"] != 1]
        detalle = ", ".join(f"{b['indice']}:{b['detalle']}"
                            for b in asignados)
        apagados = sum(1 for b in bots if b["codigo"] == 1)
        return (f"perfil {campos.get('profileId')}, "
                f"{len(asignados)} asignados ({detalle}), "
                f"{apagados} apagados  |  rueda {orden_de_rueda(bots)}")
    if cmd == ILUMINACION_FIXED:
        # Se muestra lo que el bloque lleva **de verdad** en este modelo, no
        # los nombres del fabricante: la hibernacion y el tiempo de respuesta,
        # que es lo unico que la pantalla oficial del X8 Pro escribe aca. El
        # color va al final y con su aclaracion, porque en este mouse no
        # enciende nada (ver la nota de ILUMINACION).
        par = parametros_de_luz(datos)
        if par is None:
            return f"bloque de {len(datos)} B, mas corto que la estructura"
        aviso = "" if par["en_rango"] else "  [!] FUERA DE RANGO"
        if not par["reposo_en_rango"]:
            aviso += "  [!] REPOSO FUERA DE RANGO"
        return (f"perfil {campos.get('profileId')}, "
                f"reposo {par['reposoMin']:g} min, "
                f"hibernacion {par['hibernateTime']} min, "
                f"respuesta {par['responseTimeUI']} de {RESPUESTA_UI_MIN}.."
                f"{RESPUESTA_UI_MAX} (byte {par['responseTime']}), "
                f"modo {par['lightMode']}, velocidad {par['breathingSpeed']}, "
                f"color #{campos.get('redColor', 0):02x}"
                f"{campos.get('greenColor', 0):02x}"
                f"{campos.get('blueColor', 0):02x} (inerte en este modelo)"
                f"{aviso}")
    return ""


# --- escribir un nivel de dpi ----------------------------------------------
# Los limites son los de la UI oficial del X8 Pro: los seis sliders de
# `chunks/dpiX8Pro-CVtR2JhM.js` declaran `min:100` y `max:4e4`. El minimo de
# 100 tambien sale del formato: `Pu(50)` y `Pu(0)` dan los mismos dos bytes,
# asi que 50 dpi no se distingue de "nivel apagado".

# `DPI_MINIMO_UI` (100) y `DPI_MAXIMO_UI` (40000) salen del perfil: son los
# limites del sensor de este modelo, no del protocolo.
#: La grilla del sensor: `Pu()` divide entero, asi que el mouse solo guarda
#: **multiplos de 50** (`n = (dpi - 50) // 50` en `dpi.codificar_lineal`).
#: Arriba de 26000 la rama doble lo lleva a 100, y eso **no** esta en esta
#: constante: el valor efectivo lo devuelve `escribir_nivel_dpi()`, que es
#: quien lo sabe. Esto es el paso del control, para no ofrecer numeros que el
#: mouse no puede guardar.
DPI_PASO_UI = 50


class NivelApagado(ValueError):
    """Se pidio escribir en un nivel que el mouse tiene desactivado."""


def escribir_nivel_dpi(datos: bytes, nivel: int, valor: int) -> tuple[bytes, int]:
    """Cambia UN nivel de dpi sobre el bloque leido del mouse.

    `datos` es lo que devolvio el mouse para el cmd 4 (lo mismo que
    `Frame.data`), `nivel` va de 1 a 8 como en la UI, y `valor` es el dpi que se
    quiere. Devuelve `(bloque_nuevo, valor_efectivo)`.

    **El valor efectivo puede no ser el pedido**: `Pu()` divide entero, asi que
    el mouse solo guarda multiplos de 50 -de 100 arriba de 26000-. Se devuelve
    para poder decirlo ANTES de escribir y no descubrirlo releyendo.

    Lo que toca, y nada mas:

    - `Dpi_X_setting[nivel-1]`, el byte bajo, y `Dpi_Y_setting[nivel-1]`, el
      alto. Los dos salen de `dpi.codificar_lineal()`, que es `Pu()`.
    - El bit del nivel en `DPI_X_Double_Flag`, que es lo que dice por cual de
      las dos ramas de `Pu()` se codifico. Sin eso, un valor de mas de 26000
      se leeria a la mitad.
    - El checksum interno de la estructura.

    Lo que **respeta** tal como vino: todo el resto, incluido
    `DPI_Y_Double_Flag`. La web escribe el flag ahi y el soft en el campo X
    (ver `dev/models/attackshark-x8pro/docs/soft-nativo.md`); el mouse que tenemos lo trae en X, que es de
    donde lo lee nuestro decodificador, asi que se mueve ese y el otro se deja
    como este. Es la misma decision que con el nibble bajo del report rate: si
    no esta medido que haya que tocarlo, no se toca.
    """
    perfil = _perfil()
    if not 1 <= nivel <= perfil.niveles_dpi:
        raise ValueError(f"el nivel va de 1 a {perfil.niveles_dpi}, "
                         f"no {nivel}")
    if not perfil.dpi_minimo <= valor <= perfil.dpi_maximo:
        raise ValueError(
            f"{valor} dpi esta fuera de lo que ofrece la pagina oficial "
            f"({perfil.dpi_minimo} a {perfil.dpi_maximo})")

    off = offsets(DPI_FIXED)
    fin = fin_de_campos(DPI_FIXED)
    if len(datos) < fin + 2:
        raise ValueError(f"el bloque de dpi mide {len(datos)} B, esperaba al "
                         f"menos {fin + 2}")

    i = nivel - 1
    encendidos = datos[off["dpi_ON_OFF_flag"][0]]
    if not encendidos & (1 << i):
        raise NivelApagado(
            f"el nivel {nivel} esta apagado en el mouse (dpi_ON_OFF_flag = "
            f"{encendidos:#04x}). Encenderlo es otro cambio, y no esta medido")

    bajo, alto = _dpi.codificar_lineal(valor)
    salida = bytearray(datos)
    salida[off["Dpi_X_setting"][0] + i] = bajo
    salida[off["Dpi_Y_setting"][0] + i] = alto

    pos_flag = off["DPI_X_Double_Flag"][0]
    if valor > _dpi.DPI_LINEAL_MAXIMO:
        salida[pos_flag] |= 1 << i
    else:
        salida[pos_flag] &= ~(1 << i) & 0xFF

    efectivo = _dpi.decodificar_lineal(bajo, alto,
                                       doble=valor > _dpi.DPI_LINEAL_MAXIMO)
    return poner_checksum_interno(DPI_FIXED, bytes(salida)), efectivo


# --- el report rate (cmd 6) -------------------------------------------------
#
# El bloque son siete bytes: `01 44 bb 00 00 00 00`. El `01` es el perfil, el
# segundo es el rate y el tercero su **complemento** (`0xFF ^ byte`), que es el
# mismo idioma de valor+complemento de cmd 7 y del comando `0x0c`.
#
# **El nibble ALTO es el indice** de `RATE_HZ` (`125 * 2^(n-1)`), y el bajo se
# respeta tal como vino: es INFERIDO que sea la tasa por cable, y no es nuestro
# asunto. Los dos clientes oficiales difieren justo ahi -el soft lo deja en 4
# (`0x14`..`0x74`) y la web escribe los dos nibbles iguales (`0x11`..`0x77`)-,
# asi que respetarlo es lo unico que reproduce a los dos.
#
# Las catorce escrituras estan en el bus: las siete del soft en
# `soft-rates-anotados.pcap` y las siete de la web en `web-todo.pcap`. Esta
# funcion las reproduce todas (`test_escribir_report_rate`), que es la Etapa 2
# de **las siete tasas**: 125, 250, 500, 1000, 2000, 4000 y 8000 Hz.
#
# Lo unico que no se arregla escribiendo este byte es volver: **a 8000 Hz las
# lecturas largas fallan** y el paso 1 de la Etapa 3 exige un respaldo
# completo. Escribir a esa tasa si funciona (MEDIDO sobre el
# driver oficial), asi que es una limitacion de la herramienta, no del mouse.

def escribir_report_rate(datos: bytes, *, hz: int) -> bytes:
    """Cambia la tasa de reporte sobre el bloque leido del mouse.

    `datos` es lo que devolvio el mouse para cmd 6. Mueve dos bytes: el del
    rate y su complemento. El nibble bajo del byte de rate se respeta.
    """
    if hz not in _p.RATE_INDICE:
        raise ValueError(
            f"{hz} Hz no existe. Los que hay: "
            + ", ".join(str(x) for x in sorted(_p.RATE_INDICE)))
    if len(datos) < 3:
        raise ValueError(f"el bloque de report rate mide {len(datos)} B, "
                         "esperaba al menos 3")
    salida = bytearray(datos)
    salida[1] = (_p.RATE_INDICE[hz] << 4) | (salida[1] & 0x0F)
    salida[2] = 0xFF ^ salida[1]
    return bytes(salida)


# Los catorce bytes de rate que hay en el bus: siete del soft nativo
# (`soft-rates-anotados.pcap`, nibble bajo 4) y siete de la pagina
# (`web-todo.pcap`, los dos nibbles iguales).
#
# **Y sirven de baranda.** Como el nibble bajo se respeta, partir de un bloque
# raro produce un byte que ningun cliente oficial mando nunca: si la pagina
# dejo el mouse en `0x01` -paso- y despues se le pide 1000 Hz,
# sale `0x41`, que no esta en esta lista. El mouse probablemente lo acepte,
# pero es exactamente lo que la regla del proyecto no permite mandar a ciegas,
# asi que `escribir_report_rate()` lo dice y quien llama decide.
RATE_BYTES_EN_EL_BUS = frozenset(
    [n << 4 | 4 for n in _p.RATE_HZ] + [n << 4 | n for n in _p.RATE_HZ])


def rate_byte_en_el_bus(byte: int) -> bool:
    """Si ese byte de rate aparece en alguna captura del driver oficial."""
    return byte in RATE_BYTES_EN_EL_BUS


def report_rate_coherente(datos: bytes) -> bool:
    """Si el byte de rate y su complemento dicen lo mismo.

    Es lo que separa **un byte raro que el mouse tiene guardado** de **una
    lectura que vino mal**: el sangrado del cable trajo `01 00 83 01 01 00 00`
    -el payload de la version detras del `01` del rate-, que no cierra; el
    `01 02 fd 00 00 00 00` del 2026-10-04 si.
    """
    return len(datos) >= 3 and datos[2] == 0xFF ^ datos[1]


def arreglar_report_rate(datos: bytes, *, por_cable: bool = False) -> bytes:
    """El bloque con la tasa en 1000 Hz, para cuando el byte no se entiende.

    **Aca el nibble bajo NO se respeta**, al reves que en
    `escribir_report_rate()`. Respetarlo sobre un byte ilegible da uno que
    ningun cliente oficial mando (`0x02` -> `0x42`), y un byte asi no lo
    escribio nadie que supiera de nibbles. Sale siempre uno de
    `RATE_BYTES_EN_EL_BUS`:

      * por el dongle, `0x44`: con un bloque que termina en ceros es byte a
        byte la escritura de rate del driver oficial
        (`04 0e 00 06 09 01 44 bb 00 00 00 00 01 21`, `evidencia.md`);
      * por cable lo ilegible es el nibble bajo, y el alto -la tasa de la
        radio- se conserva si es un indice: `0x70` -> `0x74`, que es lo que
        el soft escribio por cable para 1000 Hz (`cable-soft-rate-1000.pcap`).
    """
    if len(datos) < 3:
        raise ValueError(f"el bloque de report rate mide {len(datos)} B, "
                         "esperaba al menos 3")
    mil = _p.RATE_INDICE[1000]
    alto = datos[1] >> 4
    if not (por_cable and alto in _p.RATE_HZ):
        alto = mil
    salida = bytearray(datos)
    salida[1] = alto << 4 | mil
    salida[2] = 0xFF ^ salida[1]
    return bytes(salida)


def report_rate_de(datos: bytes) -> int | None:
    """Los Hz que declara el bloque, o None si el indice no es de los siete."""
    if len(datos) < 2:
        return None
    return _p.RATE_HZ.get(_p.rate_indice(datos[1]))


# --- el report rate por CABLE ----------------------------------------------
# El mismo byte, el **otro nibble**. Por cable el soft nativo mueve el
# nibble bajo y deja el alto -la tasa inalambrica- como estaba (MEDIDO en
# `cable-soft-rate-500.pcap` y `cable-soft-rate-1000.pcap`: leyo `0x74`, escribio
# `0x73` para 500 Hz y `0x74` para 1000). `escribir_report_rate()` habria
# escrito `0x34`: la tasa inalambrica a 500 y la del cable intacta, o sea otra
# cosa que la que se pidio por el camino por el que se pidio.
#
# **Y el mouse aplica el nibble bajo como su tasa por cable**, verificado por
# fuera del protocolo (2026-09-18): con `0x73` escrito desde la ventana,
# `medir-polling.py` por cable dio 2000 us de mediana -500 Hz-.
def escribir_report_rate_por_cable(datos: bytes, *, hz: int) -> bytes:
    """Cambia la tasa **del cable** sobre el bloque leido: el nibble bajo."""
    tope = _perfil().tasa_maxima_por_cable
    if hz not in _p.RATE_INDICE or hz > tope:
        raise ValueError(
            f"{hz} Hz no es una tasa del cable. Las que hay: "
            + ", ".join(str(x) for x in sorted(_p.RATE_INDICE) if x <= tope))
    if len(datos) < 3:
        raise ValueError(f"el bloque de report rate mide {len(datos)} B, "
                         "esperaba al menos 3")
    salida = bytearray(datos)
    salida[1] = (salida[1] & 0xF0) | _p.RATE_INDICE[hz]
    salida[2] = 0xFF ^ salida[1]
    return bytes(salida)


def report_rate_por_cable_de(datos: bytes) -> int | None:
    """Los Hz del cable que declara el bloque: el nibble bajo."""
    if len(datos) < 2:
        return None
    return _p.RATE_HZ.get(datos[1] & 0x0F)


# --- el nivel de dpi activo ------------------------------------------------
#
# `Current_Dpi_level_flag` es **cual de los ocho niveles esta en uso**, y es el
# otro parametro de cmd 4 que el driver oficial escribe de verdad: en las
# capturas toma **seis valores distintos**, 1 a 6, que es toda la barrida de
# los niveles encendidos (`dpi_ON_OFF_flag = 0x3f`).
#
# Y hay **86 pares de escrituras del driver oficial que difieren solo en el
# byte 22 y el checksum interno** -algunos dentro de la misma captura, como
# `soft-todo.pcap` a t+862.96 con nivel 3 y a t+865.24 con nivel 1-. Esa es la
# forma mas fuerte de Etapa 2 que da el proyecto, la misma de
# `escribir_reposo_ligero()`: no hace falta creerle a un constructor del
# bundle, alcanza con convertir una escritura real en la otra.
#
# **Y es el unico campo del mouse con un indicador propio.** Los ocho
# `Dpi_level_N_indication_flag` del mismo bloque traen un color cada uno
# -`ff0000`, `00ff00`, `0000ff`, `ffff00`, `00ffff`, `ff00ff`, `ff4000`,
# `ffffff`- y el LED de nivel es lo unico que prende en este modelo: los bytes
# de color de cmd 5 no encienden nada (MEDIDO). Asi que cambiar
# el nivel activo **se ve**, y es la cuarta verificacion a simple vista del
# proyecto, despues del LOD y de los dos ordenes de la rueda.
#
# Lo que NO se puede escribir de este bloque, y por que: `dpi_ON_OFF_flag`
# (cuales niveles estan encendidos), los ocho colores de indicador y
# `Dpi_indication_type` son **constantes en las 53 escrituras capturadas**.
# Sin una captura que los mueva no hay Etapa 2, y la regla del proyecto es que
# al mouse no se le manda una secuencia que el driver oficial no haya mandado
# antes.

def escribir_nivel_activo(datos: bytes, *, nivel: int) -> bytes:
    """Cambia cual de los ocho niveles de dpi esta en uso.

    `datos` es lo que devolvio el mouse para cmd 4. No toca ningun valor de
    dpi: solo `Current_Dpi_level_flag` y el checksum interno, que es
    exactamente lo que mueven los pares del driver oficial.
    """
    niveles = _perfil().niveles_dpi
    if not 1 <= nivel <= niveles:
        raise ValueError(f"el nivel va de 1 a {niveles}, no {nivel}")

    off = offsets(DPI_FIXED)
    fin = fin_de_campos(DPI_FIXED)
    if len(datos) < fin + 2:
        raise ValueError(f"el bloque de dpi mide {len(datos)} B, esperaba al "
                         f"menos {fin + 2}")

    # Un nivel apagado no se puede seleccionar, y el mouse acusaria la
    # escritura igual: es el mismo agujero que tenia `--funcion macro` sin id.
    encendidos = datos[off["dpi_ON_OFF_flag"][0]]
    if not encendidos & (1 << (nivel - 1)):
        raise NivelApagado(
            f"el nivel {nivel} esta apagado en el mouse (dpi_ON_OFF_flag = "
            f"{encendidos:#04x}), asi que no se puede poner en uso. "
            "Encenderlo es otro cambio, y no esta medido")

    salida = bytearray(datos)
    salida[off["Current_Dpi_level_flag"][0]] = nivel
    return poner_checksum_interno(DPI_FIXED, bytes(salida))


# Los ocho colores del indicador de nivel, tal como vinieron en las 53
# escrituras capturadas -son constantes en todas-. La tabla es solo para
# poder **nombrar** el color al hablarle a una persona: el valor sale siempre
# del bloque del mouse, no de aca.
NOMBRES_DE_COLOR = {
    "ff0000": "rojo",
    "00ff00": "verde",
    "0000ff": "azul",
    "ffff00": "amarillo",
    "00ffff": "cian",
    "ff00ff": "magenta",
    "ff4000": "naranja",
    "ffffff": "blanco",
}


def color_de_nivel(datos: bytes, nivel: int) -> tuple[str, str | None] | None:
    """El color del indicador de un nivel de dpi, leido del propio bloque.

    Devuelve `(hex, nombre)` -el nombre es None si no es uno de los ocho
    conocidos- o None si el bloque no cierra o el nivel no existe.
    """
    if not 1 <= nivel <= _perfil().niveles_dpi:
        return None
    campos = decodificar(DPI_FIXED, datos)
    if campos is None:
        return None
    crudo = campos.get(f"Dpi_level_{nivel}_indication_flag")
    if not isinstance(crudo, (bytes, bytearray)):
        return None
    hexa = bytes(crudo).hex()
    return hexa, NOMBRES_DE_COLOR.get(hexa)


def nivel_activo_de(datos: bytes) -> int | None:
    """Cual nivel esta en uso, o None si el bloque no cierra."""
    campos = decodificar(DPI_FIXED, datos)
    return None if campos is None else campos.get("Current_Dpi_level_flag")


# --- escribir el color de la luz -------------------------------------------

def escribir_color_luz(datos: bytes, rgb: tuple[int, int, int]) -> bytes:
    """Cambia SOLO el color sobre el bloque de iluminacion leido del mouse.

    `datos` es lo que devolvio el mouse para el cmd 5 (lo mismo que
    `Frame.data`). Toca tres bytes y el checksum interno, y nada mas.

    **Por que solo el color.** El bloque de cmd 5 lleva nueve campos y tres de
    ellos comparten byte con otra cosa o cambian de significado segun que
    pantalla de la app oficial los escribio (la nota de arriba de
    `ILUMINACION` lo detalla, con las citas de `app.js`). Ofrecer "brillo" o
    "modo" seria ofrecer un numero que no sabemos donde cae. `redColor`,
    `greenColor` y `blueColor`, en cambio, los escriben pelados los seis
    codificadores del bundle y los lee pelados todo handler, y las capturas
    traen dos valores distintos ahi (`00 ff 00` y `00 00 ff`) con el resto del
    bloque igual: son bytes que el driver oficial ya movio en este modelo.

    **Y no esperes ver nada.** Se escribio, ida y vuelta, con
    acuse y relectura: los bytes cambian y **el mouse no enciende nada**. El
    X8 Pro no tiene un LED que responda a este bloque; el unico indicador que
    prende es el de nivel de dpi, y lo pinta cmd 4. Encaja con el bundle: el
    escritor propio del modelo (`chunks/indexX8Pro-BTVvPdTw.js`) usa cmd 5
    **solo como portador** de `closeTime` y `responseTime`, y nunca asigna un
    color. Eso ya estaba anotado en `dev/models/attackshark-x8pro/docs/capturas-w/web-todo.txt`, y el
    plan de la Fase 2 lo contradecia igual. Sobre
    este modelo el color parece **inerte**: se guarda, se relee y no mueve nada. No esta probado que lo sea -podria haber un LED bajo un
    `lightMode` que nunca pusimos, y `lightMode` es justo el campo que no
    sabemos escribir- pero es lo que la evidencia sostiene.
    """
    for c in rgb:
        if not 0 <= c <= 255:
            raise ValueError(f"componente de color fuera de rango: {c}")
    pos = offsets(ILUMINACION_FIXED)
    salida = bytearray(datos)
    for nombre, valor in zip(("redColor", "greenColor", "blueColor"), rgb):
        i, largo = pos[nombre]
        if i + largo > len(salida):
            raise ValueError(
                f"el bloque mide {len(salida)} B y {nombre} va en {i}")
        salida[i] = valor
    return poner_checksum_interno(ILUMINACION_FIXED, bytes(salida))


# --- escribir los parametros que viajan en cmd 5 ---------------------------

def escribir_parametros_luz(datos: bytes, *,
                            hibernacion: int | None = None,
                            respuesta: int | None = None) -> bytes:
    """Cambia hibernacion y/o tiempo de respuesta sobre el bloque leido.

    Reproduce lo que hace `_()` en `chunks/indexX8Pro-BTVvPdTw.js`, con una
    diferencia deliberada: donde el original escribe el literal `8` en el
    nibble bajo de `LightBrightness`, aca se **conserva el que trajo el mouse**.

    El `8` del original sale de la rama `else` de `lightMode != 1 && != 5`, y
    nuestro mouse cae en esa rama (`lightMode` es 0), asi que hoy da lo mismo.
    Pero conservar lo leido es lo que hace que escribir los valores actuales
    reproduzca el bloque **byte a byte**, que es la prueba de la Etapa 2 y lo
    que verifica `test_escribir_parametros_luz`. Fijar un literal seria
    escribirle al mouse una suposicion sobre un campo que no sabemos leer.

    Lo que toca, y nada mas: el nibble ALTO de `breathingSpeed`, el nibble ALTO
    de `LightBrightness`, el byte `direction`, y el checksum interno.
    """
    if hibernacion is not None and not (
            HIBERNACION_MIN <= hibernacion <= HIBERNACION_MAX):
        raise ValueError(
            f"hibernacion {hibernacion} fuera de {HIBERNACION_MIN}.."
            f"{HIBERNACION_MAX}, que es lo que se vio en las 16 tramas del "
            "driver oficial")
    if respuesta is not None and not (
            RESPUESTA_MIN <= respuesta <= RESPUESTA_MAX):
        raise ValueError(
            f"respuesta {respuesta} fuera de {RESPUESTA_MIN}..{RESPUESTA_MAX}, "
            f"que es el rango del slider del X8 Pro ({RESPUESTA_UI_MIN}.."
            f"{RESPUESTA_UI_MAX} paso 2) dividido por dos, que es como viaja")

    pos = offsets(ILUMINACION_FIXED)
    fin = max(off + largo for off, largo in pos.values())
    if len(datos) < fin:
        raise ValueError(
            f"el bloque mide {len(datos)} B y la estructura necesita {fin}")

    salida = bytearray(datos)
    if hibernacion is not None:
        i_bs = pos["breathingSpeed"][0]
        i_lb = pos["LightBrightness"][0]
        salida[i_bs] = (hibernacion & 0xF0) | (salida[i_bs] & 0x0F)
        salida[i_lb] = ((hibernacion & 0x0F) << 4) | (salida[i_lb] & 0x0F)
    if respuesta is not None:
        salida[pos["direction"][0]] = respuesta
    return poner_checksum_interno(ILUMINACION_FIXED, bytes(salida))


# --- el OTRO temporizador de reposo, el corto -------------------------------
# El X8 Pro tiene **dos** temporizadores de reposo, no uno, y viajan en bytes
# distintos del mismo bloque de cmd 5. Esto se destapo, buscando
# por que el corte del latido con `--hibernacion 1` cayo en 88..92 s y no en 60.
#
# Los dos controles, en `chunks/indexX8Pro-BTVvPdTw.js`:
#
#     Level1SleepTimer   slider min:.5  max:30 step:.5   -> el corto
#     SleepTimer         slider min:1   max:60 step:2    -> la hibernacion
#
# y el soft nativo los llama `Sleep Time:` y `Deep Sleep Time:` (ver
# `dev/models/attackshark-x8pro/docs/soft-nativo.md`, que ya los listaba).
#
# El corto vive en el byte `closeTime`, en medios minutos. La cadena entera, en
# `dev/research/webapp/app.js`:
#
#     a.setUint8(o++, e.closeTime * 2)              // serializador, off 1115592
#     this[n].hibernateTime = o.sleepTime / 2       // lectura,      off 1433656
#     sleepTime: t.length > 11 ? t[11] : 0          // y t[11] es este byte
#
# MEDIDO en el bus: toma 1, 2 y 12 en las capturas (0.5, 1 y 6 minutos), y en
# `soft-todo.pcap` el software nativo lo movio **1 -> 12 -> 1** mientras la
# hibernacion de los nibbles iba 10 -> 25 -> 10 por separado. Dos campos, dos
# controles, la misma sesion.
#
# La web **nunca lo escribe** en este modelo: su slider esta en un div con
# `display:none` y ademas `k()` lo manda a `LightBrightness`, no aca. Por eso
# las diez tramas de `web-todo.pcap` lo tienen constante en 2.
#
# Nuestro mouse lo tiene en 1, o sea **0.5 min = 30 s**, y el latido baja de
# 2.00 s a 4.00 s entre los 32.8 y los 36.8 s de quietud.
#
# Los 30 s aparecen MEDIDOS como el termino constante del corte del latido:
#
#     corte = 30 s + N x 60 s     con N = la hibernacion de los nibbles
#     N=1   predicho  90 s   medido [88.0, 92.0]
#     N=10  predicho 630 s   medido [628.9, 632.9]
#
# Pero **que ese 30 sea ESTE byte es INFERIDO**: en las cuatro corridas el byte
# valio siempre 1, asi que un preambulo fijo del firmware encaja igual de bien.
# Se zanja escribiendole 1 min y mirando el escalon: si se va a ~62 s era este
# campo; si se queda en ~33 s, no.


def escribir_reposo_ligero(datos: bytes, *, minutos: float) -> bytes:
    """Cambia el temporizador de reposo corto sobre el bloque leido.

    No es el que mueve `escribir_parametros_luz(hibernacion=...)`: ese va
    partido en los nibbles altos de `breathingSpeed` y `LightBrightness`. Este
    va entero en el byte `closeTime`, y en medios minutos.

    `minutos` es el numero del control oficial: 0.5 a 30, de a 0.5.

    Lo que toca, y nada mas: el byte `closeTime` y el checksum interno.
    """
    if not (REPOSO_MIN <= minutos <= REPOSO_MAX):
        raise ValueError(
            f"reposo {minutos} fuera de {REPOSO_MIN}..{REPOSO_MAX} minutos, "
            "que es el rango del slider Level1SleepTimer del X8 Pro")
    byte = minutos * 2
    if byte != int(byte):
        raise ValueError(
            f"reposo {minutos} no es multiplo de 0.5: el byte son medios "
            "minutos y no hay forma de representarlo")
    byte = int(byte)

    pos = offsets(ILUMINACION_FIXED)
    fin = max(off + largo for off, largo in pos.values())
    if len(datos) < fin:
        raise ValueError(
            f"el bloque mide {len(datos)} B y la estructura necesita {fin}")

    salida = bytearray(datos)
    salida[pos["closeTime"][0]] = byte
    return poner_checksum_interno(ILUMINACION_FIXED, bytes(salida))


# --- los cuatro interruptores del sensor, que viven en cmd 4 ---------------
# `SensitivityX` y `SensitivityY` **no son sensibilidad**: son cuatro campos
# empaquetados de a dos por byte. Del escritor propio del modelo,
# `chunks/indexX8Pro-BTVvPdTw.js`, funcion `S()`:
#
#     let o = t.parameterX8Pro.straightLine ? 1 : 0,
#         e = t.parameterX8Pro.ripple ? 1 : 0,
#         l = t.parameterX8Pro.motionSync ? 1 : 0,
#         u = t.parameterX8Pro.sensitivityX;
#     M.SensitivityX = u << 4 | e;
#     M.SensitivityY = o << 4 | l;
#
# Y los nombres de la interfaz salen del template del mismo archivo:
#
#     sensitivityX -> radio bajo el header `SilentHeight`, con dos opciones
#                     literales: `value:0 -> "1 MM"`, `value:1 -> "2 MM"`.
#                     Es la **altura de corte (LOD)**, no una sensibilidad.
#     straightLine -> switch `AngleSnapping`
#     ripple       -> switch `RippleControl1`
#     motionSync   -> switch `MotionSync`
#
# MEDIDO en el bus: entre las capturas hay **10 pares distintos** de
# (SensitivityX, SensitivityY), y los cuatro bits aparecen en los dos estados.
#
# **La pagina oficial lee estos bytes mal, y conviene saberlo antes de creerle
# a su pantalla.** Su parser (`app.js`) tiene dos ramas y el X8 Pro cae en la
# de abajo:
#
#     if (t === "MV6") { ...desempaqueta los nibbles... }
#     else {
#       this[n].straightLine = e.dpiSettings.sensitivityX === 1;
#       this[n].ripple       = e.dpiSettings.sensitivityY === 1;
#     }
#
# O sea que compara el **byte entero** contra 1, con los campos cruzados, y
# **nunca lee de vuelta ni el LOD ni el motion sync**. Con el bloque de fabrica
# (`01 01`) muestra "angle snapping ON" cuando el byte dice que esta OFF. Es el
# mismo tipo de error que el del dpi (I-W10) y que el nibble de rate: leer con
# una regla y escribir con otra.
#
# Por eso este modulo desempaqueta como escribe `S()`, no como lee la pagina.


# El campo va 0/1 en el bus, pero **hacia afuera se habla en milimetros**. El
# radio oficial dice `value:0 -> "1 MM"` y `value:1 -> "2 MM"`, y heredar esa
# numeracion seria el mismo error que heredar `SensitivityX` para algo que no es
# sensibilidad: el proyecto traduce los nombres del fabricante, asi que tambien
# traduce sus numeros. Adentro, el codificador sigue hablando en valores de
# campo, que es lo que viaja.
LOD_1MM, LOD_2MM = 0, 1
LOD_NOMBRES = {LOD_1MM: "1 mm", LOD_2MM: "2 mm"}
LOD_MM = {LOD_1MM: 1, LOD_2MM: 2}
LOD_DESDE_MM = {1: LOD_1MM, 2: LOD_2MM}


def lod_desde_mm(mm: int) -> int:
    """El valor de campo para una altura en milimetros.

    La conversion vive aca y no en el CLI para que haya un solo lugar donde
    milimetros y valores de campo se cruzan, y para poder probarlo.
    """
    if mm not in LOD_DESDE_MM:
        raise ValueError(
            f"LOD {mm} mm: el radio oficial solo ofrece "
            f"{' y '.join(f'{k} mm' for k in sorted(LOD_DESDE_MM))}")
    return LOD_DESDE_MM[mm]


def parametros_de_sensor(datos: bytes) -> dict | None:
    """Los cuatro interruptores del sensor, desempaquetados de cmd 4.

    Desempaqueta como los escribe el handler del X8 Pro, no como los lee la
    pagina oficial (ver la nota de arriba: la pagina los lee mal).
    """
    pos = offsets(DPI_FIXED)
    fin = max(off + largo for off, largo in pos.values())
    if len(datos) < fin:
        return None
    sx = datos[pos["SensitivityX"][0]]
    sy = datos[pos["SensitivityY"][0]]
    return {
        "lod": (sx >> 4) & 0x0F,
        "ripple": bool(sx & 0x0F),
        "angle_snapping": bool((sy >> 4) & 0x0F),
        "motion_sync": bool(sy & 0x0F),
        # Lo que la pagina oficial mostraria con estos mismos bytes, para poder
        # explicar la diferencia cuando alguien la mire en pantalla.
        "pagina_angle_snapping": sx == 1,
        "pagina_ripple": sy == 1,
    }


def escribir_parametros_sensor(datos: bytes, *,
                               lod: int | None = None,
                               ripple: bool | None = None,
                               angle_snapping: bool | None = None,
                               motion_sync: bool | None = None) -> bytes:
    """Cambia los interruptores del sensor sobre el bloque de cmd 4 leido.

    Reproduce el empaquetado de `S()`. Lo que no se nombra se conserva tal como
    vino del mouse, asi que escribir lo que ya tiene reproduce el bloque byte a
    byte.

    Lo que toca, y nada mas: `SensitivityX`, `SensitivityY` y el checksum
    interno. **No toca ningun nivel de dpi**, que viven en el mismo bloque.
    """
    if lod is not None and lod not in (LOD_1MM, LOD_2MM):
        raise ValueError(
            f"lod {lod} no es {LOD_1MM} (1 mm) ni {LOD_2MM} (2 mm), que son "
            "las dos unicas opciones del radio oficial")

    pos = offsets(DPI_FIXED)
    fin = max(off + largo for off, largo in pos.values())
    if len(datos) < fin:
        raise ValueError(
            f"el bloque mide {len(datos)} B y la estructura necesita {fin}")

    actual = parametros_de_sensor(datos)
    salida = bytearray(datos)
    nuevo_lod = actual["lod"] if lod is None else lod
    nuevo_rip = actual["ripple"] if ripple is None else bool(ripple)
    nuevo_snap = (actual["angle_snapping"] if angle_snapping is None
                  else bool(angle_snapping))
    nuevo_sync = (actual["motion_sync"] if motion_sync is None
                  else bool(motion_sync))

    salida[pos["SensitivityX"][0]] = (nuevo_lod & 0x0F) << 4 | int(nuevo_rip)
    salida[pos["SensitivityY"][0]] = int(nuevo_snap) << 4 | int(nuevo_sync)
    return poner_checksum_interno(DPI_FIXED, bytes(salida))


# --- escribir botones (cmd 8) ----------------------------------------------
#
# Este codificador existe por una sola razon y conviene tenerla a la vista:
# **el bloque que el mouse devuelve no se le puede devolver tal cual**. Los
# slots 4, 5 y 6 se remapean entre escritura y lectura (MEDIDO
# con un A/B directo, ver la nota de `SLOT_ESCRITO_DE_LEIDO`), asi que la
# relectura idempotente con la que arranca cada Etapa 3 -escribirle al mouse
# exactamente lo que se le leyo- **le rotaria tres botones**.
#
# Y el checksum interno no avisa: es una suma llana, y permutar tres slots la
# deja igual. Los dos bloques del A/B traen los dos `0x0079`. O sea que el
# unico que puede atajar esto es el codificador.
#
# Hacia afuera, nombres. Las tres numeraciones -UI del soft, slot escrito,
# slot leido- no coinciden entre si (ver `BOTONES_UI_DEL_SOFT`), y elegir
# cualquiera de las tres seria heredar el error de otro, como pasaria con el
# LOD si hablaramos en 0/1 en vez de milimetros.
#
# **Estado epistemico de los nombres**: que `costado-adelante` sea el slot
# leido 5 esta MEDIDO -se remapeo ese boton fisico con el soft y cambio ese
# slot y solo ese-.
#
# **Y los otros cuatro quedaron cerrados** (ver dev/models/attackshark-x8pro/docs/evidencia.md):
#
#   * 4 (costado-atras) y 7 (modo): se remapearon a "reproducir / pausar"
#     (codigo 24), se apretaron -la musica se puso en pausa- y se devolvieron.
#     La verificacion la hizo el reproductor del sistema, no nuestro
#     decodificador;
# * 6 (dpi): por otro camino,. Al ciclarlo, el firmware escribe
#     `Current_Dpi_level_flag` y el LED toma el color de ese nivel;
#   * 1, 2 y 3 salen del bloque de fabrica, que para el clic izquierdo, el
#     derecho y el de rueda no tiene lectura alternativa.
#
# Del slot 7 salio ademas un hecho que no es del mapeo: **ese boton cambia el
# canal de conexion siempre**, con cualquier funcion encima -al apretarlo el
# mouse se desconecto del dongle y ademas pauso la musica-. O sea que el codigo
# 60 (`FUN_MODE_KEY`) que trae de fabrica es, en la practica, "no mandes nada
# extra"; remapearlo no desactiva el cambio de modo.
#
# Ninguno se aprieta a ciegas: el CLI muestra que funcion tiene hoy el slot
# antes de pedir confirmacion.
# `BOTONES_POR_NOMBRE` -que boton fisico es cada slot- vive en el perfil
# (`botones_por_nombre`): que botones tiene el chasis es lo mas de este modelo
# que hay en este archivo. Se sigue leyendo con ese nombre.

# **Siempre queda un clic izquierdo, y en un boton donde se pueda usar.**
#
# Antes la baranda era mas bruta: el slot 1 no se remapeaba, porque un mouse
# sin clic izquierdo no se arregla desde ninguna interfaz que haya que
# clickear. Se pregunto si hacia falta, y el bundle contesto dos
# cosas (LEIDO, `dev/research/webapp/`):
#
#   * la pagina del X8 Pro **deja** remapear el boton 1: `indexX8Pro` pide
#     `ModifyLeftKeyWarning` ("Modificar el botón izquierdo puede impedir
#     clics") cuando el boton elegido es el 1, y si se acepta, escribe;
#   * otros clientes del fabricante ponen una regla mejor que la nuestra:
#     `AtLeastOneButtonMustBeLeftClick` ("至少一个按键功能为 Left Click", chunk
#     `zh-B5btDJ85.js`).
#
# La baranda pasa a ser esa, con una restriccion del proyecto: el clic
# izquierdo solo puede quedar en los botones 1 a 5. El 6 y el 7 estan en la
# **base** del mouse, y un clic que solo se puede hacer dando vuelta el mouse
# no es un clic que sirva para arreglar nada.
#
# **Lo que no esta medido**: ninguna captura muestra una escritura del slot 1
# distinta de la de fabrica. El bloque de cmd 8 si esta cerrado (Etapa 2), y el
# codigo 2 es el mismo que el slot 1 trae; lo que falta es la Etapa 3 de un
# remapeo del slot 1 contra el mouse.
FUNCION_CLIC_IZQUIERDO = 2
# En que botones puede quedar, `SLOTS_PARA_CLIC_IZQUIERDO`, sale del perfil: es
# por modelo y no global, porque depende de donde caiga cada boton en el chasis.

#: El slot del boton de modo de conexion, y el del clic de rueda. Los dos
#: tienen nombre propio porque hay codigo que necesita senalarlos sin recorrer
#: la tabla: el de modo lleva una advertencia que ningun otro lleva -ver
#: `COMO_SE_SUPO_EL_BOTON`- y el de rueda marca donde va el sentido del scroll
#: cuando los botones se muestran en orden fisico.
#: `SLOT_DE_MODO` y `SLOT_DEL_CLIC_DE_RUEDA` salen del mapa del perfil, y
#: `BOTONES_POR_NOMBRE_MAX` es el slot mas alto que es un boton fisico: los de
#: arriba son slots que el X8 Pro no usa (van apagados) y los dos de la rueda.

#: **Como se supo que cada slot es ese boton fisico.** Es evidencia, no
#: decoracion: un diagrama que pone un numero sobre un boton **afirma** que ese
#: numero es ese boton, asi que quien dibuje tiene que poder decir de donde lo
#: saco, y un slot que no este aca **no se dibuja como si estuviera medido**.
#: Todo sale de `dev/models/attackshark-x8pro/docs/evidencia.md`; los siete estan cerrados. Viven en
#: el perfil (`como_se_supo_el_boton`), porque lo que se
#: midio se midio **de este modelo**: en otro, los mismos siete slots serian
#: otros botones y esta evidencia no valdria.


def boton_confirmado(slot: int) -> bool:
    """Si se sabe -y como- que ese slot es un boton fisico determinado.

    Quien dibuje un diagrama lo usa para no afirmar de mas: un slot que da
    `False` va en gris y con un signo de pregunta, no sobre un boton.
    """
    return slot in _perfil().como_se_supo_el_boton


class SinClicIzquierdo(ValueError):
    """La escritura dejaria el mouse sin un clic izquierdo que se pueda usar."""



def con_clic_izquierdo(bots: list[dict]) -> list[int]:
    """Los botones de `SLOTS_PARA_CLIC_IZQUIERDO` que hoy hacen clic izquierdo.

    Mira los bytes y no `codigo`: los codificadores cambian `bytes` y dejan el
    resto del diccionario como se leyo.
    """
    return [b["indice"] for b in bots
            if b["indice"] in _perfil().slots_para_clic_izquierdo
            and bytes(b["bytes"])[0] == FUNCION_CLIC_IZQUIERDO]


def _cuidar_el_clic_izquierdo(antes: list[int], bots: list[dict]) -> None:
    """La baranda del clic izquierdo, sobre el bloque ya modificado.

    **Solo protege lo que hay.** Si el mouse ya llego sin clic izquierdo en los
    botones 1 a 5 -lo dejo asi otro cliente-, no se bloquea nada: impedir
    escribir no lo arregla, y la escritura que lo arregla tiene que poder
    pasar.
    """
    pueden = _perfil().slots_para_clic_izquierdo
    fisicos = max(_perfil().botones_por_nombre.values())
    for b in bots:
        if (bytes(b["bytes"])[0] == FUNCION_CLIC_IZQUIERDO
                and 1 <= b["indice"] <= fisicos
                and b["indice"] not in pueden):
            raise SinClicIzquierdo(
                f"el clic izquierdo solo se puede poner en los botones "
                f"{pueden[0]} a {pueden[-1]}, no en el {b['indice']}")
    if antes and not con_clic_izquierdo(bots):
        raise SinClicIzquierdo(
            f"el botón {antes[0]} es el único con clic izquierdo: antes de "
            "cambiarlo, poné el clic izquierdo en otro de los botones "
            f"{pueden[0]} a {pueden[-1]}")


def _bloque_de_botones(bots: list[dict]) -> bytes:
    """Arma el bloque de ESCRITURA a partir de los slots en orden de LECTURA.

    Traduce por `SLOT_ESCRITO_DE_LEIDO` y recalcula el checksum interno. Los
    slots de la rueda no se tocan: esos dos **no** se remapean, el soft escribe
    `0a, 09` y el mouse devuelve `0a, 09`.
    """
    perfil = _perfil()
    por_indice = {b["indice"]: bytes(b["bytes"]) for b in bots}
    salida = bytearray([1])            # profileId
    for escrito in range(1, perfil.botones + 1):
        # El remapeo del perfil va de leido -> escrito; aca hace falta al
        # reves, y se invierte en vez de escribir la otra tabla a mano para que
        # no puedan quedar desincronizadas.
        leido = next((k for k, v in perfil.remapeo_de_slots.items()
                      if v == escrito), escrito)
        salida += por_indice[leido]
    salida += b"\x00\x00"              # el hueco del checksum interno
    return poner_checksum_interno(BOTONES_FIXED, bytes(salida))


def retraducir_botones(datos: bytes) -> bytes:
    """El bloque de cmd 8 leido, listo para devolverselo al mouse SIN cambios.

    No es `datos`. Los slots 4, 5 y 6 se remapean entre escritura y lectura,
    asi que "devolver lo mismo" exige traducir; mandar el bloque crudo rotaria
    tres botones. Es la escritura con la que arranca la Etapa 3 de este
    comando, y la unica forma de que sea de verdad idempotente.
    """
    bots = botones_de(datos)
    if bots is None:
        raise ValueError(f"el bloque mide {len(datos)} B y no alcanza para "
                         f"{_perfil().botones} slots")
    return _bloque_de_botones(bots)


def escribir_boton(datos: bytes, *, slot: int, codigo: int,
                   p1: int = 0, p2: int = 0) -> bytes:
    """Cambia UN boton sobre el bloque de cmd 8 leido del mouse.

    `slot` va en la numeracion de **lectura**, que es la que muestran
    `respaldar.py` y `describir()`. `codigo` es una clave de
    `FUNCIONES_DE_BOTON`; `p1` y `p2` solo se usan en los atajos de teclado y
    en el macro (ver `botones_de`).

    Devuelve el bloque listo para `build_write_frame()`, ya traducido a la
    numeracion de escritura. Pedir el codigo que el slot ya tiene reproduce el
    bloque que el driver oficial mando: eso es lo que prueba
    `test_etapa2_botones`.

    **La baranda del clic izquierdo va sobre el bloque ya cambiado**: ver
    `SLOTS_PARA_CLIC_IZQUIERDO`. Es el unico lugar donde se sabe que botones
    lo tienen, y por eso cuida por igual al CLI y a la ventana.
    """
    perfil = _perfil()
    if not 1 <= slot <= perfil.botones:
        raise ValueError(f"slot {slot}: los slots van de 1 a "
                         f"{perfil.botones}")
    if slot in perfil.slots_de_rueda:
        raise ValueError(
            f"el slot {slot} es de la rueda y los dos clientes oficiales lo "
            "escriben al reves uno del otro. Se toca con escribir_rueda()")
    if codigo not in FUNCIONES_DE_BOTON:
        raise ValueError(f"codigo {codigo}: no esta en la tabla de funciones")
    if (codigo == FUNCION_MACRO
            and not perfil.macro_id_min <= p2 <= perfil.macro_id_max):
        raise ValueError(
            f"la funcion macro necesita el id del macro en p2, y llego {p2}. "
            "Un slot `12 00 00` apunta a un macro que no existe y deja el "
            "boton muerto: el mouse acusa la escritura igual, asi que no se "
            "nota hasta apretarlo")
    if codigo == FUNCION_ATAJO:
        # El mismo agujero que el del macro, para la otra funcion con
        # parametros: `11 00 00` es el slot vacio del bundle
        # (`FUN_SHORTCUT:[17,0,0]`), el mouse lo acusa igual y el boton queda
        # muerto. Los dos bytes se validan juntos porque juntos se eligen.
        mascara_de_modificadores(p1)
        if p2 not in USAGES_DE_TECLA:
            if p2 in USAGES_DE_MODIFICADOR:
                raise ValueError(
                    f"p2 = {p2} es {USAGES_DE_MODIFICADOR[p2]}, y en un atajo "
                    "los modificadores van en p1. La tecla va en p2")
            raise ValueError(
                f"el atajo de teclado necesita el usage HID de la tecla en "
                f"p2, y llego {p2}. Sin tecla el slot queda en `11 00 00`, "
                "que es el vacio: el mouse lo acusa igual y el boton no hace "
                "nada")
    bots = botones_de(datos)
    if bots is None:
        raise ValueError(f"el bloque mide {len(datos)} B y no alcanza para "
                         f"{perfil.botones} slots")
    antes = con_clic_izquierdo(bots)
    for b in bots:
        if b["indice"] == slot:
            b["bytes"] = bytes([codigo, p1, p2])
    _cuidar_el_clic_izquierdo(antes, bots)
    return _bloque_de_botones(bots)


def intercambiar_botones(datos: bytes, *, a: int, b: int) -> bytes:
    """Intercambia lo que hacen dos botones, en **una** escritura.

    Existe por el clic izquierdo: pasarlo del 1 al 2 con `escribir_boton()`
    son dos escrituras, y en el medio el mouse queda con dos clics izquierdos
    -o, en el otro orden, la baranda no deja-. Aca los dos cambian en el mismo
    bloque, que viaja en una sola trama. Los parametros viajan con la funcion:
    un atajo o un macro se mudan enteros.
    """
    perfil = _perfil()
    for slot in (a, b):
        if not 1 <= slot <= perfil.botones or slot in perfil.slots_de_rueda:
            raise ValueError(f"slot {slot}: no es un boton que se remapee")
    if a == b:
        raise ValueError("para intercambiar hacen falta dos botones distintos")
    bots = botones_de(datos)
    if bots is None:
        raise ValueError(f"el bloque mide {len(datos)} B y no alcanza para "
                         f"{perfil.botones} slots")
    antes = con_clic_izquierdo(bots)
    por_indice = {x["indice"]: x for x in bots}
    por_indice[a]["bytes"], por_indice[b]["bytes"] = (
        bytes(por_indice[b]["bytes"]), bytes(por_indice[a]["bytes"]))
    _cuidar_el_clic_izquierdo(antes, bots)
    return _bloque_de_botones(bots)


def escribir_rueda(datos: bytes, *, orden: tuple[int, int]) -> bytes:
    """Fija los dos slots de la rueda sobre el bloque de cmd 8 leido.

    Va aparte de `escribir_boton()` porque estos dos slots son el unico lugar
    del bloque donde los dos clientes oficiales se contradicen, y porque el
    orden correcto esta MEDIDO: con `RUEDA_CORRECTA` el scroll anda derecho, y
    con el otro queda invertido(girandola).
    """
    if tuple(orden) not in (RUEDA_COMO_EL_SOFT, RUEDA_COMO_LA_WEB):
        raise ValueError(
            f"orden {tuple(orden)}: los unicos dos observados en el bus son "
            f"{RUEDA_COMO_EL_SOFT} (scroll derecho) y {RUEDA_COMO_LA_WEB} "
            "(invertido)")
    perfil = _perfil()
    bots = botones_de(datos)
    if bots is None:
        raise ValueError(f"el bloque mide {len(datos)} B y no alcanza para "
                         f"{perfil.botones} slots")
    for b in bots:
        if b["indice"] in perfil.slots_de_rueda:
            i = perfil.slots_de_rueda.index(b["indice"])
            b["bytes"] = bytes([orden[i], b["p1"], b["p2"]])
    return _bloque_de_botones(bots)


# --- el teclado: usages HID, modificadores y el atajo (funcion 17) ----------
#
# La funcion 17 de un boton lleva **dos parametros dentro del slot**: `p1` es
# la mascara de modificadores y `p2` el usage HID de la tecla. Y no es solo
# algo LEIDO del bundle: esta en el bus. `soft-todo.pcap` trae dos bloques de
# cmd 8 del soft nativo con `11 08 07` y `11 0a 16`, que son exactamente
# `FUN_SHOW_DESKTOP:[17,8,7]` (Win+D) y `FUN_SCREEN_CAPTURE:[17,10,22]`
# (Win+Shift+S) de la tabla `sl` de `app.js`.
#
# **La tabla de usages es del bundle, no nuestra.** `_w()` en `app.js` declara
# 118 teclas con su `usageId` -`KeyA:{usageId:4}` ... `F24:{usageId:115}`, los
# ocho modificadores en 224..231 y los cinco botones del mouse en 241..245- y
# son los usages HID estandar de la pagina 0x07. Lo unico nuestro son los
# nombres: los del bundle son los `event.code` del navegador (`KeyA`,
# `Digit1`, `ArrowUp`), que describen un teclado del navegador y no una tecla.
# Se traducen como se tradujo el LOD a milimetros.
TECLAS_HID = {
    # letras: KeyA..KeyZ = 4..29
    **{chr(ord("a") + i): 4 + i for i in range(26)},
    # digitos: Digit1..Digit9 = 30..38 y Digit0 = 39. El cero va ultimo, como
    # en el teclado y como en la tabla del bundle.
    **{str(d): 29 + d for d in range(1, 10)}, "0": 39,
    "enter": 40, "esc": 41, "retroceso": 42, "tab": 43, "espacio": 44,
    "guion": 45, "igual": 46, "corchete-abre": 47, "corchete-cierra": 48,
    "barra-invertida": 49, "punto-y-coma": 51, "comilla": 52,
    "tilde-grave": 53, "coma": 54, "punto": 55, "barra": 56,
    "bloq-mayus": 57,
    # F1..F12 = 58..69, y F13..F24 = 104..115
    **{f"f{n}": 57 + n for n in range(1, 13)},
    **{f"f{n}": 91 + n for n in range(13, 25)},
    "impr-pant": 70, "bloq-despl": 71, "pausa": 72, "insert": 73,
    "inicio": 74, "re-pag": 75, "supr": 76, "fin": 77, "av-pag": 78,
    # Las flechas se llaman `flecha-*` y no `arriba`/`abajo` a proposito: en
    # un macro "arriba" y "abajo" son las dos direcciones de un evento, y dos
    # cosas distintas con el mismo nombre en la misma interfaz es una trampa.
    "flecha-derecha": 79, "flecha-izquierda": 80, "flecha-abajo": 81,
    "flecha-arriba": 82,
    "bloq-num": 83, "num-dividir": 84, "num-multiplicar": 85,
    "num-menos": 86, "num-mas": 87, "num-enter": 88,
    **{f"num-{d}": 88 + d for d in range(1, 10)}, "num-0": 98,
    "num-punto": 99,
    # `IntlBackslash`: la tecla extra de los teclados no-US, la de `<>` a la
    # izquierda de la Z.
    "menor-mayor": 100,
    "menu": 101, "encendido": 102, "num-igual": 103,
}

# Los nombres del bundle se aceptan igual -son los que va a tener a mano
# cualquiera que mire `app.js` o el DOM de la pagina- y unos pocos sinonimos
# de uso corriente. Es solo entrada: lo que se muestra siempre es la clave de
# `TECLAS_HID`.
ALIAS_DE_TECLA = {
    "escape": "esc", "backspace": "retroceso", "space": "espacio",
    "spacebar": "espacio", "minus": "guion", "equal": "igual",
    "bracketleft": "corchete-abre", "bracketright": "corchete-cierra",
    "backslash": "barra-invertida", "semicolon": "punto-y-coma",
    "quote": "comilla", "backquote": "tilde-grave", "comma": "coma",
    "period": "punto", "slash": "barra", "capslock": "bloq-mayus",
    "printscreen": "impr-pant", "scrolllock": "bloq-despl",
    "pause": "pausa", "home": "inicio", "pageup": "re-pag",
    "delete": "supr", "del": "supr", "end": "fin", "pagedown": "av-pag",
    "arrowright": "flecha-derecha", "arrowleft": "flecha-izquierda",
    "arrowdown": "flecha-abajo", "arrowup": "flecha-arriba",
    "numlock": "bloq-num", "numpaddivide": "num-dividir",
    "numpadmultiply": "num-multiplicar", "numpadsubtract": "num-menos",
    "numpadadd": "num-mas", "numpadenter": "num-enter",
    "numpaddecimal": "num-punto", "numpadequal": "num-igual",
    "intlbackslash": "menor-mayor", "contextmenu": "menu", "power": "encendido",
    **{f"key{chr(ord('a') + i)}": chr(ord("a") + i) for i in range(26)},
    **{f"digit{d}": str(d) for d in range(10)},
    **{f"numpad{d}": f"num-{d}" for d in range(10)},
}

# El byte de modificadores. **Sale de veinte atajos del bundle y de dos
# bloques del bus**, y coincide con el byte de modificadores de un teclado HID
# estandar: bit 0 Ctrl, bit 1 Shift, bit 2 Alt, bit 3 Win, todos izquierdos.
#
# La verificacion cruzada es la tabla `sl` de `app.js` entera: sus veinte
# entradas con codigo 17 son atajos conocidos de Windows y **las veinte
# cierran** contra `TECLAS_HID` con este mapa -`FUN_COPY:[17,1,6]` es Ctrl+C,
# `FUN_CLOSE_WINDOWS:[17,4,61]` es Alt+F4, `FUN_SCREEN_CAPTURE:[17,10,22]` es
# Win+Shift+S, que ademas esta capturado-. Eso es `ATAJOS_DEL_BUNDLE`, y
# `test_etapa2_atajo` las reproduce una por una.
MODIFICADORES = {"ctrl": 0x01, "shift": 0x02, "alt": 0x04, "win": 0x08}
ALIAS_DE_MODIFICADOR = {"control": "ctrl", "mayus": "shift",
                        "super": "win", "meta": "win", "cmd": "win",
                        "windows": "win"}

# Los cuatro bits de arriba son los modificadores **derechos** del estandar
# HID (RCtrl, RShift, RAlt, RWin). No aparecen en ninguna de las veinte
# entradas del bundle, en ningun bloque capturado, ni en el dialogo del soft
# -que ofrece Ctrl, Shift, Alt y Win, cuatro-. Asi que el codificador los
# rechaza: que el firmware los pase tal cual al host es probable, pero
# "probable" no es como se escriben bytes en este proyecto.
MODIFICADORES_NO_ATESTIGUADOS = 0xF0

# Las veinte entradas de `sl` con codigo 17, tal cual. Sirven para dos cosas:
# son la Etapa 2 del codificador -veinte combinaciones de modificadores y
# tecla armadas por el cliente oficial- y son la lista de atajos que la web
# ofrece hecha, por si la aplicacion quiere ofrecerla igual.
ATAJOS_DEL_BUNDLE = {
    "FUN_ALL": (1, 4), "FUN_COPY": (1, 6), "FUN_CUT": (1, 27),
    "FUN_FIND": (1, 9), "FUN_NEW": (1, 17), "FUN_OPEN": (1, 18),
    "FUN_PASTE": (1, 25), "FUN_PRINT": (1, 19), "FUN_REDO": (1, 28),
    "FUN_SAVE": (1, 22), "FUN_UNDO": (1, 29), "FUN_ZOOM_IN": (1, 46),
    "FUN_ZOOM_OUT": (1, 45), "FUN_BROWSER_FAVORITES": (3, 18),
    "FUN_CLOSE_WINDOWS": (4, 61), "FUN_SWAP_WINDOWS": (4, 43),
    "FUN_LOCK_PC": (8, 15), "FUN_RUN": (8, 21), "FUN_SHOW_DESKTOP": (8, 7),
    "FUN_SCREEN_CAPTURE": (10, 22),
}

# Y lo mismo en castellano, que es como se escribe un atajo a mano. El texto
# del medio es lo que `atajo_desde_texto()` recibe.
ATAJOS_DEL_BUNDLE_EN_TEXTO = {
    "FUN_ALL": "ctrl+a", "FUN_COPY": "ctrl+c", "FUN_CUT": "ctrl+x",
    "FUN_FIND": "ctrl+f", "FUN_NEW": "ctrl+n", "FUN_OPEN": "ctrl+o",
    "FUN_PASTE": "ctrl+v", "FUN_PRINT": "ctrl+p", "FUN_REDO": "ctrl+y",
    "FUN_SAVE": "ctrl+s", "FUN_UNDO": "ctrl+z", "FUN_ZOOM_IN": "ctrl+igual",
    "FUN_ZOOM_OUT": "ctrl+guion", "FUN_BROWSER_FAVORITES": "ctrl+shift+o",
    "FUN_CLOSE_WINDOWS": "alt+f4", "FUN_SWAP_WINDOWS": "alt+tab",
    "FUN_LOCK_PC": "win+l", "FUN_RUN": "win+r", "FUN_SHOW_DESKTOP": "win+d",
    "FUN_SCREEN_CAPTURE": "win+shift+s",
}

FUNCION_ATAJO = 17

#: Los usages que `TECLAS_HID` cubre, para validar un `p2` que llega en numero.
USAGES_DE_TECLA = frozenset(TECLAS_HID.values())

#: Los ocho modificadores como **tecla**, que es otra cosa que como mascara.
#: Valen adentro de un macro -un macro que hace Ctrl+C aprieta y suelta el
#: Ctrl- y no valen como la tecla de un atajo, donde el Ctrl va en `p1`.
USAGES_DE_MODIFICADOR = {
    224: "ctrl izquierdo", 225: "shift izquierdo", 226: "alt izquierdo",
    227: "win izquierdo", 228: "ctrl derecho", 229: "shift derecho",
    230: "alt derecho", 231: "win derecho",
}


def usage_de_tecla(tecla) -> int:
    """El usage HID de una tecla, por nombre o por numero.

    Acepta la clave de `TECLAS_HID`, sus alias -incluidos los nombres del
    bundle, `KeyA` o `ArrowUp`- o el usage directo. Levanta ValueError con la
    lista a mano si no esta.
    """
    if isinstance(tecla, int):
        if tecla in USAGES_DE_TECLA:
            return tecla
        raise ValueError(
            f"usage {tecla}: no es ninguna de las {len(TECLAS_HID)} teclas "
            "que declara el bundle. La tabla esta en TECLAS_HID")
    clave = str(tecla).strip().lower().replace("_", "-").replace(" ", "-")
    if clave in TECLAS_HID:
        return TECLAS_HID[clave]
    # Los alias del bundle vienen pegados (`arrowup`, `printscreen`), asi que
    # se prueban tambien sin los separadores.
    for candidata in (clave, clave.replace("-", "")):
        if candidata in ALIAS_DE_TECLA:
            return TECLAS_HID[ALIAS_DE_TECLA[candidata]]
    raise ValueError(
        f"tecla {tecla!r}: no esta en la tabla. Van por nombre -`a`..`z`, "
        "`0`..`9`, `f1`..`f24`, `enter`, `esc`, `espacio`, `tab`, `supr`, "
        "`flecha-arriba`, `num-7`...- y tambien se aceptan los del bundle "
        "(`KeyA`, `ArrowUp`). Las 111 estan en TECLAS_HID, y el CLI las lista "
        "con --listar-teclas")


def nombre_de_tecla(usage: int) -> str | None:
    """El nombre de un usage, o None si no lo conocemos."""
    for nombre, u in TECLAS_HID.items():
        if u == usage:
            return nombre
    return None


def mascara_de_modificadores(modificadores) -> int:
    """La mascara `p1` a partir de una lista de nombres, o de un numero.

    `modificadores` puede ser un entero -que se valida igual- o cualquier
    iterable de nombres: `("ctrl", "shift")`. Los cuatro derechos del estandar
    HID no se aceptan: ver `MODIFICADORES_NO_ATESTIGUADOS`.
    """
    if isinstance(modificadores, int):
        mascara = modificadores
    else:
        mascara = 0
        for m in modificadores:
            clave = str(m).strip().lower()
            clave = ALIAS_DE_MODIFICADOR.get(clave, clave)
            if clave not in MODIFICADORES:
                raise ValueError(
                    f"modificador {m!r}: los unicos cuatro que el bundle y el "
                    "soft escriben son "
                    + ", ".join(sorted(MODIFICADORES)))
            mascara |= MODIFICADORES[clave]
    if not 0 <= mascara <= 0xFF:
        raise ValueError(f"mascara {mascara}: no entra en un byte")
    if mascara & MODIFICADORES_NO_ATESTIGUADOS:
        raise ValueError(
            f"mascara {mascara:#04x}: los bits de arriba son los "
            "modificadores derechos del estandar HID, y ningun cliente "
            "oficial los escribio nunca -ni el bundle en sus veinte atajos, "
            "ni el soft, que ofrece cuatro-. Sin captura no se mandan")
    return mascara


def texto_de_modificadores(mascara: int) -> str:
    """`ctrl+shift` a partir de la mascara. Cadena vacia si no hay ninguno."""
    return "+".join(nombre for nombre, bit in MODIFICADORES.items()
                    if mascara & bit)


def atajo_desde_texto(texto: str) -> tuple[int, int]:
    """`"ctrl+shift+s"` -> `(p1, p2)`, los dos bytes del slot.

    El ultimo termino es la tecla y los de adelante los modificadores. Un
    atajo sin tecla no existe: `11 00 00` es el slot vacio que el bundle usa
    de plantilla (`FUN_SHORTCUT:[17,0,0]`), el mouse lo acusa igual y el boton
    queda muerto, que es el mismo agujero que el del macro con id 0.
    """
    partes = [t for t in str(texto).replace(" ", "").split("+") if t]
    if not partes:
        raise ValueError("un atajo vacio no es un atajo: el slot queda en "
                         "`11 00 00` y el boton, muerto")
    # Un "+" como tecla se escribe `ctrl+igual`, no `ctrl++`: la tecla que hay
    # en el teclado es `=`/`+` y el bundle la llama `Equal`.
    tecla = partes[-1]
    p2 = usage_de_tecla(tecla)
    if p2 in USAGES_DE_MODIFICADOR:
        raise ValueError(
            f"{tecla!r} es un modificador, y en un atajo los modificadores van "
            "en p1, no en p2. Escribilo como `ctrl+c`")
    return mascara_de_modificadores(partes[:-1]), p2


def texto_de_atajo(p1: int, p2: int) -> str:
    """La vuelta: los dos bytes del slot en `ctrl+shift+s`.

    Si el usage no esta en la tabla se dice el numero, que es lo que hay.
    """
    tecla = nombre_de_tecla(p2) or USAGES_DE_MODIFICADOR.get(p2) \
        or f"usage {p2}"
    mods = texto_de_modificadores(p1)
    return f"{mods}+{tecla}" if mods else tecla


def escribir_atajo(datos: bytes, *, slot: int, atajo) -> bytes:
    """Pone un atajo de teclado en un boton, sobre el bloque de cmd 8 leido.

    `atajo` es el texto -`"ctrl+c"`- o el par `(p1, p2)` ya armado. Es
    `escribir_boton()` con la funcion 17 y sus dos parametros; existe aparte
    porque esos dos bytes se eligen juntos y validarlos sueltos deja pasar el
    slot vacio.
    """
    p1, p2 = atajo_desde_texto(atajo) if isinstance(atajo, str) else atajo
    return escribir_boton(datos, slot=slot, codigo=FUNCION_ATAJO,
                          p1=p1, p2=p2)


# --- el codificador de macros (cmd 9) --------------------------------------
# Va aparte de `poner_checksum_interno()` y de `ESTRUCTURAS` a proposito: cmd 9
# no tiene tabla de campos -su bloque es cabecera mas una lista de eventos de
# largo variable-, asi que `fin_de_campos()` no sabe donde termina. Su checksum
# interno son los **dos ultimos bytes** del bloque, y suma desde el byte 3 del
# buffer completo, igual que los demas: sobre `datos`, `datos[1:-2]`.
#
# **Y hay que rearmarlo siempre, aunque no cambie ni un campo**, porque el
# mouse lo devuelve con los bytes al reves: escribe `0c 6d` y lee `6d 0c` (ver
# la nota de `MACRO_CHECKSUM_ORDENES`). Devolverle el bloque leido tal cual le
# manda un checksum invertido. Es la misma familia de trampa que la permutacion
# de slots de cmd 8, y por eso este codificador **no** es un `memcpy`.
MACRO_REPETICIONES_MIN = 1
MACRO_REPETICIONES_MAX = 255      # `min:1, max:255` del chunk del X8 Pro
MACRO_MODO_CON_CONTADOR = 0


def poner_checksum_macro(datos: bytes) -> bytes:
    """Devuelve el bloque de macro con su checksum interno en big-endian.

    Big-endian es como lo **escribe** el driver oficial, atestiguado en las
    cuatro escrituras de `dev/models/attackshark-x8pro/docs/capturas-w/soft-macro-asignado.pcap`. La lectura
    lo trae al reves; esta funcion normaliza los dos casos.
    """
    if len(datos) < 9:
        raise ValueError(f"el bloque de macro mide {len(datos)} B y la "
                         "cabecera sola necesita 9")
    salida = bytearray(datos)
    suma = sum(salida[1:-2]) & 0xFFFF
    salida[-2:] = suma.to_bytes(2, "big")
    return bytes(salida)


def escribir_macro(datos: bytes, *, modo: int | None = None,
                   repeticiones: int | None = None) -> bytes:
    """Cambia el disparo de un macro sobre el bloque leido del mouse.

    Toca **dos bytes y el checksum**, nada mas: el modo de disparo y, cuando el
    modo es el 0, el contador de repeticiones. No graba eventos ni cambia el
    id: la lista de eventos se pasa entera y decidir como se expresa eso es
    diseño de la aplicacion, no una opcion de este codificador.

    Es exactamente el A/B que el soft nativo hizo en el bus: cuatro escrituras
    del mismo macro al mismo boton en las que lo unico que cambio fue el byte
    del modo, 0 -> 1 -> 2 -> 0, con el checksum interno acompañando. Por eso la
    Etapa 2 de este codificador se verifica byte a byte
    (`test_etapa2_macro`).

    El byte de repeticiones **solo es el contador cuando el modo es 0**: los
    cuatro constructores del bundle hacen `n===0 ? setUint8(7,a) :
    setUint8(7,1)`, asi que en los otros dos modos va forzado a 1 y pedir un
    numero ahi seria pedir algo que el bloque no puede expresar.

    Llamarlo sin `modo` ni `repeticiones` reescribe el mismo macro con el
    checksum normalizado: esa es la escritura idempotente de cmd 9, y **no es
    devolver el bloque leido** -si viene de una lectura, los dos bytes del
    checksum cambian de orden-.
    """
    m = parametros_de_macro(datos)
    if m is None:
        raise ValueError(f"el bloque mide {len(datos)} B y no cierra como "
                         "macro")
    if modo is None:
        modo = m["modo"]
    if modo not in MACRO_MODOS:
        raise ValueError(
            f"modo {modo}: los unicos tres observados en el bus son "
            + ", ".join(f"{k} ({v})" for k, v in MACRO_MODOS.items()))

    if modo == MACRO_MODO_CON_CONTADOR:
        if repeticiones is None:
            # si ya venia en modo 0, se conserva su contador; si venia de otro
            # modo, el byte estaba forzado a 1 y ese 1 es el unico valor que
            # el bloque atestigua
            repeticiones = m["repeticiones"] if m["repeticiones"] else 1
        if not (MACRO_REPETICIONES_MIN <= repeticiones
                <= MACRO_REPETICIONES_MAX):
            raise ValueError(
                f"repeticiones {repeticiones} fuera de "
                f"{MACRO_REPETICIONES_MIN}..{MACRO_REPETICIONES_MAX}, que es "
                "el rango del campo numerico del chunk del X8 Pro")
    elif repeticiones is not None:
        raise ValueError(
            f"el modo {modo} ({MACRO_MODOS[modo]}) no tiene contador: el byte "
            "va forzado a 1. El unico modo que lo usa es el "
            f"{MACRO_MODO_CON_CONTADOR} ({MACRO_MODOS[MACRO_MODO_CON_CONTADOR]})")
    else:
        repeticiones = 1

    salida = bytearray(datos)
    salida[1] = modo
    salida[5] = repeticiones
    return poner_checksum_macro(bytes(salida))


# --- grabar un macro: el codificador de eventos (cmd 9) --------------------
#
# Hasta hoy cmd 9 se escribia solo por el disparo (`escribir_macro()`): la
# lista de eventos se leia y se devolvia intacta. Esto la arma.
#
# El sitio es lo primero: el bloque son 109 bytes de datos -`MACRO_SIZE` menos
# los dos de la cabecera de trama-, la cabecera de adentro ocupa 7 y el
# checksum interno 2, asi que a los eventos les quedan **100 bytes**. Cada
# evento son dos, o cuatro si el tiempo pasa de 127 ms: **50 eventos**, o 25
# si todos son largos. El byte que los cuenta entra hasta 255, pero el sitio
# no: pasarse llena el bloque y se come el checksum. Por eso el limite se
# valida contra el sitio y no contra el byte.
#
# **Lo que se escribe es la regla del soft nativo, no la del bundle**, y en un
# bit se separan. Para los eventos cortos los dos coinciden salvo en el bit 0:
# el soft manda `0a` para 10 ms y los constructores del bundle mandan `d|1`
# -ver la nota de `MACRO_BIT_DIRECCION`, donde tampoco se sabe que significa-.
# Se copia al soft porque es **el unico de los dos cuya escritura de macro
# esta capturada**, y porque su regla reproduce los diez eventos del bus byte
# a byte (`test_etapa2_eventos_de_macro`).
#
# En la rama larga eso se nota mas: `Qve` hace `d|1` / `d|=129` al partir el
# tiempo, asi que un evento de 350 ms sale de su codificador como 51 + 3
# centenas, o sea **351**. Nosotros no forzamos ese bit y 350 sale 350. Es una
# decision, no un descubrimiento: la estructura de cuatro bytes es del bundle
# (INFERIDA, ninguna captura la muestra) y el bit 0 es del soft (MEDIDO, pero
# en eventos cortos). Queda anotado en `dev/models/attackshark-x8pro/docs/evidencia.md` y el CLI lo avisa
# antes de escribir un macro con tiempos largos.
MACRO_EVENTOS_OFFSET = 7          # despues de id, modo, tres ceros, rep y n
# Los tres que salen del largo del bloque, y por eso del perfil:
# `MACRO_DATOS_SIZE` es lo que `Frame.data` trae (109 aca), `MACRO_EVENTOS_BYTES`
# lo que queda para los eventos (100) y `MACRO_EVENTOS_MAX` cuantos entran (50).
MACRO_TIEMPO_MAX = 255 * 100 + 99   # las centenas van en un byte: 25599 ms
MACRO_TIEMPO_CORTO_MAX = 127        # arriba de esto el evento ocupa cuatro

def _sitio_de_eventos() -> int:
    """Los bytes que le quedan a los eventos en el bloque de este modelo.

    Es `MACRO_EVENTOS_BYTES`: el bloque menos la cabecera de trama, menos los
    7 de la cabecera de adentro, menos los 2 del checksum.
    """
    return (_perfil().bloques[_p.CMD_MACRO] - 2 - MACRO_EVENTOS_OFFSET - 2)


#: Los cinco botones del mouse como nombre, para armar eventos. Es
#: `MACRO_USAGE_BOTONES` dado vuelta, con las claves escribibles a mano.
MACRO_BOTONES_POR_NOMBRE = {
    "clic-izquierdo": 241, "clic-derecho": 242, "clic-rueda": 243,
    "adelante": 244, "atras": 245,
}

#: Los otros nombres que se aceptan para un paso de macro: los trece del
#: bundle que no son teclas -los cinco botones del mouse y los ocho
#: modificadores, que adentro de un macro son teclas como cualquier otra- y
#: unas formas cortas. Se aceptan por lo mismo que `KeyA` y `ArrowUp`: son los
#: nombres que tiene a mano quien mire `app.js`. Solo entrada.
ALIAS_DE_EVENTO = {
    "leftmousebutton": 241, "rightclick": 242, "mousewheelclick": 243,
    "mouseforward": 244, "mouseback": 245,
    "izquierdo": 241, "derecho": 242, "rueda": 243,
    "controlleft": 224, "shiftleft": 225, "altleft": 226, "guileft": 227,
    "controlright": 228, "shiftright": 229, "altright": 230,
    "guiright": 231,
}

#: Todo lo que puede ir en el segundo byte de un evento: las teclas, los ocho
#: modificadores -adentro de un macro el Ctrl es una tecla mas, se aprieta y
#: se suelta- y los cinco botones del mouse.
USAGES_DE_EVENTO = (USAGES_DE_TECLA
                    | frozenset(USAGES_DE_MODIFICADOR)
                    | frozenset(MACRO_USAGE_BOTONES))


def usage_de_evento(que) -> int:
    """El usage de un paso de macro: una tecla, un modificador o un boton.

    Acepta nombre o numero. Es mas ancho que `usage_de_tecla()` a proposito:
    en un atajo el Ctrl va en la mascara, y adentro de un macro es un evento
    como cualquier otro.
    """
    if isinstance(que, int):
        if que in USAGES_DE_EVENTO:
            return que
        if que == MACRO_USAGE_CONTINUACION:
            raise ValueError(
                f"usage {MACRO_USAGE_CONTINUACION}: es el marcador de "
                "continuacion de los tiempos largos, no una tecla. Un evento "
                "con ese usage rompe la lectura del bloque entero")
        raise ValueError(f"usage {que}: no es ninguna tecla del bundle, "
                         "ninguno de los ocho modificadores ni ninguno de los "
                         "cinco botones del mouse")
    clave = str(que).strip().lower().replace("_", "-").replace(" ", "-")
    if clave in MACRO_BOTONES_POR_NOMBRE:
        return MACRO_BOTONES_POR_NOMBRE[clave]
    for candidata in (clave, clave.replace("-", "")):
        if candidata in ALIAS_DE_EVENTO:
            return ALIAS_DE_EVENTO[candidata]
    for usage, texto in USAGES_DE_MODIFICADOR.items():
        if clave == texto.replace(" ", "-"):
            return usage
    # `ctrl` a secas, adentro de un macro, es el izquierdo: es el que el
    # bundle llama `ControlLeft` y el que un teclado manda al apretarlo.
    if clave in MODIFICADORES:
        return {"ctrl": 224, "shift": 225, "alt": 226, "win": 227}[clave]
    try:
        return usage_de_tecla(clave)
    except ValueError as exc:
        # El mensaje de `usage_de_tecla()` habla solo de teclas, y adentro de
        # un macro hay tres familias: agregarlas evita mandar a alguien a
        # buscar `clic-rueda` en la tabla de teclas.
        raise ValueError(
            f"{exc.args[0]}. En un macro valen ademas los cinco botones del "
            "mouse (" + ", ".join(MACRO_BOTONES_POR_NOMBRE)
            + ") y los modificadores como tecla suelta") from None


def nombre_de_evento(usage: int) -> str:
    """Como se dice un usage de macro. Nunca devuelve None: el numero, si no."""
    return (MACRO_USAGE_BOTONES.get(usage)
            or USAGES_DE_MODIFICADOR.get(usage)
            or nombre_de_tecla(usage)
            or f"usage {usage}")


def normalizar_evento(ev) -> dict:
    """Un evento en su forma canonica: usageId, direccion y tiempo.

    Acepta lo que devuelve `parametros_de_macro()` -asi la ida y la vuelta
    cierran- y tambien la forma corta `("a", 0, 10)`. `direccion` es el bit 7
    del primer byte, **tal cual**: 0 aprieta y 1 suelta (MEDIDO,
    ver `MACRO_DIRECCIONES`).
    """
    if isinstance(ev, dict):
        usage, direccion, tiempo = (ev.get("usageId", ev.get("usage")),
                                    ev.get("direccion", 0),
                                    ev.get("tiempo", 0))
        if usage is None:
            usage = ev.get("tecla")
    else:
        usage, direccion, tiempo = ev
    usage = usage_de_evento(usage)
    if isinstance(direccion, str):
        clave = direccion.strip().lower()
        if clave not in MACRO_DIRECCIONES_POR_NOMBRE:
            raise ValueError(
                f"direccion {direccion!r}: las dos son "
                + " y ".join(sorted(MACRO_DIRECCIONES_POR_NOMBRE)))
        direccion = MACRO_DIRECCIONES_POR_NOMBRE[clave]
    if direccion not in (0, 1):
        raise ValueError(f"direccion {direccion}: es un bit, 0 o 1")
    tiempo = int(tiempo)
    if not 0 <= tiempo <= MACRO_TIEMPO_MAX:
        raise ValueError(
            f"tiempo {tiempo} ms: entra de 0 a {MACRO_TIEMPO_MAX}, que es "
            "hasta donde llega la rama larga (las centenas van en un byte)")
    return {"usageId": usage, "direccion": direccion, "tiempo": tiempo}


def pares_de_evento(ev) -> bytes:
    """Los dos -o cuatro- bytes de UN evento.

    Es la regla de `Qve` con el bit 0 del soft nativo: arriba de 127 ms el
    evento se parte en `[resto | direccion, usage]` + `[centenas, 3]`. Ver la
    nota de arriba, que es donde se explica por que ese bit no se fuerza.
    """
    e = normalizar_evento(ev)
    bit = MACRO_BIT_DIRECCION if e["direccion"] else 0
    if e["tiempo"] > MACRO_TIEMPO_CORTO_MAX:
        centenas, resto = divmod(e["tiempo"], 100)
        return bytes([resto | bit, e["usageId"],
                      centenas, MACRO_USAGE_CONTINUACION])
    return bytes([e["tiempo"] | bit, e["usageId"]])


def codificar_eventos(eventos) -> tuple[bytes, int]:
    """La lista de eventos en bytes, y **cuantos pares** ocupa.

    Los dos valores hacen falta: el byte 8 del bloque no cuenta eventos,
    cuenta pares de bytes (`e.length + s` en `Qve`, donde `s` son los eventos
    largos). Confundirlos es el bug que este proyecto ya tuvo una vez, del
    lado de la lectura.
    """
    sitio = _sitio_de_eventos()
    crudos = b"".join(pares_de_evento(ev) for ev in eventos)
    if len(crudos) > sitio:
        largos = sum(1 for ev in eventos if normalizar_evento(ev)["tiempo"]
                     > MACRO_TIEMPO_CORTO_MAX)
        raise ValueError(
            f"{len(eventos)} eventos ocupan {len(crudos)} B y en el bloque "
            f"entran {sitio}: son {sitio // 2} eventos "
            f"cortos, y cada uno de mas de {MACRO_TIEMPO_CORTO_MAX} ms cuenta "
            f"por dos (hay {largos}). Que pasa si se manda un bloque mas "
            "largo no se midio, y averiguarlo pisando el checksum no es la "
            "forma")
    return crudos, len(crudos) // 2


def cuantos_largos(eventos) -> int:
    """Cuantos de esos eventos caen en la rama INFERIDA del bundle.

    Lo usa quien tenga que avisar: esos eventos se arman con una regla que
    ninguna captura mostro.
    """
    return sum(1 for ev in eventos
               if normalizar_evento(ev)["tiempo"] > MACRO_TIEMPO_CORTO_MAX)


def escribir_eventos_macro(datos: bytes, eventos, *, modo: int | None = None,
                           repeticiones: int | None = None) -> bytes:
    """Cambia **la lista de eventos** de un macro, sobre el bloque leido.

    Conserva el id y, salvo que se pidan, el modo de disparo y el contador:
    los eventos y el disparo son dos cosas distintas y se cambian por separado,
    como en el soft. El resto del bloque se rellena con ceros, que es como
    viene el del bus -ochenta bytes en cero detras de los diez eventos-.

    Devolver la lista que `parametros_de_macro()` leyo reproduce el bloque
    tal cual: esa es la escritura idempotente de los eventos.
    """
    largo = _perfil().bloques[_p.CMD_MACRO] - 2
    if len(datos) < largo:
        raise ValueError(f"el bloque mide {len(datos)} B y un macro son "
                         f"{largo}")
    m = parametros_de_macro(datos)
    if m is None:
        raise ValueError(f"el bloque mide {len(datos)} B y no cierra como "
                         "macro")
    crudos, pares = codificar_eventos(eventos)
    sitio = _sitio_de_eventos()
    salida = bytearray(datos[:largo])
    salida[MACRO_EVENTOS_OFFSET - 1] = pares
    hueco = slice(MACRO_EVENTOS_OFFSET, MACRO_EVENTOS_OFFSET + sitio)
    salida[hueco] = crudos.ljust(sitio, b"\0")
    # El disparo va por el mismo camino de siempre, que es el que valida el
    # modo y el contador y rearma el checksum en big-endian.
    return escribir_macro(bytes(salida), modo=modo, repeticiones=repeticiones)


def armar_macro(macro_id: int, eventos, *, modo: int = 0,
                repeticiones: int | None = None) -> bytes:
    """Un bloque de macro entero, desde cero.

    Hace falta para grabar en un id que el mouse no tiene todavia: ahi no hay
    bloque leido del que partir -contesta 108 bytes de `0xff`- y armarlo sobre
    esa basura seria escribir basura.

    La forma es la del bloque capturado: `[id, modo, 0, 0, 0, repeticiones,
    pares, eventos..., ceros..., checksum]`. Los tres bytes en cero de
    `[2..4]` son cero en las cuatro escrituras del soft, y se dejan en cero
    por eso, no porque se sepa que son.
    """
    perfil = _perfil()
    if not perfil.macro_id_min <= macro_id <= perfil.macro_id_max:
        raise ValueError(f"macro id {macro_id} fuera de "
                         f"{perfil.macro_id_min}..{perfil.macro_id_max}")
    base = bytearray(perfil.bloques[_p.CMD_MACRO] - 2)
    base[0] = macro_id
    base[5] = 1
    return escribir_eventos_macro(bytes(base), eventos, modo=modo,
                                  repeticiones=repeticiones)


def eventos_desde_texto(texto: str) -> list[dict]:
    """`"a:abajo@10, a:arriba@10"` -> la lista de eventos de un macro.

    Cada evento se escribe `tecla:direccion@milisegundos` y van separados por
    comas. La tecla puede ser una tecla, un modificador o uno de los cinco
    botones del mouse (`clic-izquierdo`, `clic-rueda`, `adelante`, `atras`,
    `clic-derecho`).

    **El tiempo es obligatorio** aunque el soft tenga un "delay por defecto":
    lo que se escribe son bytes, y un default invisible es un byte que nadie
    eligio. `direccion` se escribe `dir0`/`dir1`, o `abajo`/`arriba`: son lo
    mismo, y el alias esta MEDIDO -dir0 aprieta, dir1
    suelta, ver `MACRO_DIRECCIONES`-.
    """
    eventos = []
    for crudo in str(texto).split(","):
        paso = crudo.strip()
        if not paso:
            continue
        if ":" not in paso or "@" not in paso:
            raise ValueError(
                f"{paso!r}: cada evento se escribe `tecla:direccion@ms`, por "
                "ejemplo `clic-izquierdo:abajo@10` o `a:dir1@20`")
        que, resto = paso.split(":", 1)
        direccion, ms = resto.rsplit("@", 1)
        try:
            tiempo = int(ms.strip().removesuffix("ms"))
        except ValueError:
            raise ValueError(f"{paso!r}: {ms!r} no es un numero de "
                             "milisegundos") from None
        eventos.append(normalizar_evento(
            (que.strip(), direccion.strip(), tiempo)))
    if not eventos:
        raise ValueError("la lista de eventos esta vacia. Un macro sin "
                         "eventos se puede escribir, pero no hace nada: si es "
                         "lo que queres, decilo con un evento de 0 ms")
    return eventos


# **Un macro de UN SOLO evento no se reproduce** (MEDIDO). Se
# probo en las dos direcciones -`a:dir0@10` y `a:dir1@10`-, con el macro
# asignado al costado-adelante y en modo 0: el mouse **guarda** el bloque -la
# relectura lo devuelve con su checksum bien- y al apretar el boton no pasa
# nada. Con dos eventos del mismo usage sale, y con dos de usages distintos
# tambien.
#
# **Por que no se reproduce, no se sabe.** Lo medido es el umbral entre uno y
# dos, no la regla: puede ser que el firmware itere de a pares, que descarte
# los macros de largo impar, o cualquier otra cosa. Anotar mas que esto seria
# inventar. Ver dev/models/attackshark-x8pro/docs/bitacora.md.
MACRO_EVENTOS_MIN_QUE_CORRE = 2


def eventos_sin_cerrar(eventos) -> list[int]:
    """Los usages que el macro deja APRETADOS al terminar, en orden.

    Existe porque **el firmware no suelta nada al final** (MEDIDO, ver
    `MACRO_REMEDIO_TECLA_TRABADA`): un macro que aprieta sin
    soltar deja la tecla trabada en el sistema, y despegarla obliga a
    desacoplar el dongle.

    `dir0` aprieta y `dir1` suelta (MEDIDO el mismo dia). Un `dir1` sobre algo
    que no estaba apretado no hace nada, asi que no resta de mas.
    """
    apretados: list[int] = []
    for ev in eventos:
        e = normalizar_evento(ev)
        usage = e["usageId"]
        if e["direccion"] == 0:
            if usage not in apretados:
                apretados.append(usage)
        elif usage in apretados:
            apretados.remove(usage)
    return apretados


def texto_de_eventos(eventos) -> str:
    """La vuelta, en el mismo formato que entra. Util para mostrar y repetir."""
    porusage = {u: n for n, u in MACRO_BOTONES_POR_NOMBRE.items()}
    partes = []
    for ev in eventos:
        e = normalizar_evento(ev)
        # Los botones se dicen con guion -`clic-izquierdo`- y no con el
        # espacio de `MACRO_USAGE_BOTONES`, para que el texto que sale se
        # pueda volver a pegar como argumento sin comillas de mas.
        quien = porusage.get(e["usageId"]) or nombre_de_evento(e["usageId"])
        partes.append(f"{quien}:{MACRO_DIRECCIONES[e['direccion']]}"
                      f"@{e['tiempo']}")
    return ", ".join(partes)
