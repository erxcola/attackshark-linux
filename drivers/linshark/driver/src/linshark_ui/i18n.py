# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""La ventana en castellano, inglés y chino simplificado.

**Se traduce por el texto castellano exacto**, y eso es una baranda y no un
atajo. El castellano es el que se escribe al lado del codigo que mide, asi que
es el que esta al dia: si `modelo.py` corrige una nota -porque se midio lo que
estaba INFERIDO, por ejemplo-, la traduccion deja de coincidir y se muestra el
castellano, en vez de repetir en otro idioma lo que ya no es cierto.

**Los mensajes con partes variables son plantillas.** Una clave con `{nombre}`
adentro se compara entera contra el texto, y lo que cae en cada `{nombre}` se
traduce a su vez: asi "no se escribe: {motivo}" traduce tambien el motivo, y un
mensaje de la biblioteca se traduce sin que la biblioteca sepa que hay idiomas.
Los nombres `n` y `n_algo` solo aceptan numeros; los demas, cualquier texto.

**Lo que no se traduce nunca**: lo que escribe quien mira -nombres de macro,
pasos, atajos- y los identificadores -rutas, comandos de terminal, hex-. Por
eso los nombres de macro no pasan por `tr()` y los pasos se muestran tal cual:
`a:abajo@10` es sintaxis que el parser lee en castellano.

**Y el castellano de la pantalla puede no ser el de la biblioteca.** Una fila
con cuarta columna dice como se muestra ese texto en la ventana: los mensajes
de `sesion` los lee tambien la terminal, donde "MEDIDO a 2000 y a 8000" es la
cita que importa, y en la ventana sobra. Con la misma baranda: si la biblioteca
cambia el texto, la fila deja de coincidir y se ve el de la biblioteca.

**Lo que falta se anota.** Cada texto que `tr()` no pudo traducir queda en
`faltantes()`, y `driver/tests/interfaz.py` recorre la ventana en ingles y en chino y
se pone rojo si aparece alguno: un mensaje nuevo en castellano no puede llegar
a la pantalla sin que alguien lo note.

**Baranda de diseño**: ningun literal de este modulo coincide con las claves
del modelo (las de `campos_de()`), para preservar la regla de que la ventana no
conoce ningun campo por nombre interno.
"""

from __future__ import annotations

import logging
import re
from typing import Callable

log = logging.getLogger("linshark_ui.i18n")

IDIOMAS = {
    "es": "Español",
    "en": "English",
    "zh": "简体中文",
}

#: El idioma con el que arranca la aplicacion si no hay preferencia guardada.
IDIOMA_POR_DEFECTO = "es"

_IDIOMA_ACTUAL: str = IDIOMA_POR_DEFECTO
_LISTENERS: list[Callable[[str], None]] = []


def idioma_actual() -> str:
    """Devuelve el código del idioma activo ('es', 'en', 'zh')."""
    return _IDIOMA_ACTUAL


def fijar_idioma(idioma: str) -> None:
    """Cambia el idioma activo y avisa a los componentes registrados."""
    global _IDIOMA_ACTUAL
    if idioma not in IDIOMAS:
        raise ValueError(f"Idioma no soportado: {idioma!r}. Soportados: {list(IDIOMAS)}")
    if _IDIOMA_ACTUAL == idioma:
        return
    _IDIOMA_ACTUAL = idioma
    _CACHE.clear()
    for listener in list(_LISTENERS):
        try:
            listener(idioma)
        except Exception:                # noqa: BLE001
            # Uno que no pudo retraducirse no deja a los demas en el idioma
            # viejo, pero tampoco se calla: una pantalla a medio traducir sin
            # rastro en el log es un error que nadie va a encontrar.
            log.exception("no se pudo pasar al idioma %r: %r", idioma, listener)


def al_cambiar_idioma(listener: Callable[[str], None]) -> None:
    """Registra una función que se llamará al cambiar de idioma."""
    if listener not in _LISTENERS:
        _LISTENERS.append(listener)


def desregistrar_listener(listener: Callable[[str], None]) -> None:
    """Desregistra un listener previamente conectado."""
    if listener in _LISTENERS:
        _LISTENERS.remove(listener)


# --- el motor ----------------------------------------------------------------

_COLUMNA = {"en": 0, "zh": 1, "es": 2}
_VARIABLE = re.compile(r"\{(\w+)\}")
_NUMERO = r"-?\d+(?:\.\d+)?"
#: Tres letras seguidas: lo que no las tiene -un numero, un hex, "—"- no es un
#: texto que haga falta traducir.
_TIENE_PALABRAS = re.compile(r"[^\W\d_]{3,}")

#: Lo que no es texto aunque tenga letras: una linea que es un comando para
#: copiar en la terminal, o una ruta. Se muestra tal cual y no es un faltante.
_ES_COMANDO = re.compile(r"^(sudo |udevadm |python3 |scripts/|/dev/|/sys/)")

_CACHE: dict[str, str | None] = {}
_FALTANTES: set[str] = set()


def _patron_de(clave: str) -> re.Pattern | None:
    """La clave como expresion regular, o None si no tiene variables."""
    partes = _VARIABLE.split(clave)
    if len(partes) == 1:
        return None
    patron, vistas = "", set()
    for i, parte in enumerate(partes):
        if i % 2 == 0:
            patron += re.escape(parte)
        elif parte in vistas:
            patron += f"(?P={parte})"
        else:
            vistas.add(parte)
            forma = _NUMERO if parte == "n" or parte.startswith("n_") else ".*?"
            patron += f"(?P<{parte}>{forma})"
    return re.compile(patron, re.DOTALL)


def _armar_indices():
    """Un indice por columna: exactos, plantillas y lo ya traducido.

    La columna del castellano solo tiene las filas que cambian lo que se
    muestra: con las demas, el castellano es la clave misma.
    """
    indices = {}
    for col in (0, 1, 2):
        filas = [f for f in _TEXTOS if col != 2 or len(f) > 3]
        exactos = {f[0]: (f[1], f[2], f[3] if len(f) > 3 else f[0])
                   for f in filas}
        plantillas = []
        for f in filas:
            patron = _patron_de(f[0])
            if patron is not None:
                fijo = len(_VARIABLE.sub("", f[0]))
                plantillas.append((fijo, patron, exactos[f[0]]))
        # La mas especifica primero: "el mouse lo marca en {color} ({hexa})"
        # tiene que ganarle a "el mouse lo marca en {hexa}", que tambien
        # coincide.
        plantillas.sort(key=lambda x: -x[0])
        indices[col] = (exactos, [(pt, fl) for _, pt, fl in plantillas])
    traducidos = {x for f in _TEXTOS for x in f[1:]}
    return indices, traducidos


def _pieza(valor: str, col: int) -> str:
    """Lo que cayo en una variable: se traduce si se puede, y si no, tal cual."""
    hecho = _traducir(valor, col)
    if hecho is not None:
        return hecho
    if ", " in valor:
        partes = [_traducir(p, col) for p in valor.split(", ")]
        if any(p is not None for p in partes):
            return ", ".join(t if t is not None else p
                             for t, p in zip(partes, valor.split(", ")))
    return valor


def _traducir(texto: str, col: int) -> str | None:
    exactos, plantillas = _INDICES[col]
    fila = exactos.get(texto)
    if fila is not None:
        return fila[col]
    if "\n" in texto:
        # Linea por linea, con su sangria: el mensaje de la regla de udev trae
        # el comando en una linea aparte, y juntarlo todo lo haria ilegible.
        salida = []
        for linea in texto.split("\n"):
            cuerpo = linea.strip()
            hecho = _traducir(cuerpo, col) if cuerpo else None
            if hecho is None:
                if (col != 2 and _TIENE_PALABRAS.search(cuerpo)
                        and cuerpo not in _TRADUCIDOS
                        and not _ES_COMANDO.match(cuerpo)):
                    _FALTANTES.add(cuerpo)
                salida.append(linea)
            else:
                salida.append(linea[:len(linea) - len(linea.lstrip())] + hecho)
        return "\n".join(salida)
    normal = " ".join(texto.split())
    if normal != texto:
        fila = exactos.get(normal)
        if fila is not None:
            return fila[col]
    for patron, filas in plantillas:
        m = patron.fullmatch(normal)
        if m:
            valores = {k: _pieza(v, col) for k, v in m.groupdict().items()}
            return filas[col].format(**valores)
    return None


def tr(texto: str) -> str:
    """Traduce `texto` al idioma actualmente seleccionado.

    Si está en español ('es') o no hay traducción registrada, devuelve
    el texto original sin modificar, y en el segundo caso lo anota en
    `faltantes()`.
    """
    if not texto or not isinstance(texto, str):
        return texto
    if texto in _CACHE:
        hecho = _CACHE[texto]
    else:
        hecho = _traducir(texto, _COLUMNA[_IDIOMA_ACTUAL])
        if len(_CACHE) > 4000:
            _CACHE.clear()
        _CACHE[texto] = hecho
    if hecho is None:
        if (_IDIOMA_ACTUAL != "es"
                and _TIENE_PALABRAS.search(texto) and texto not in _TRADUCIDOS
                and not _ES_COMANDO.match(texto)):
            _FALTANTES.add(texto)
        return texto
    return hecho


def tr_si_hay(texto: str) -> str | None:
    """La traduccion, o None si no hay. **No anota faltantes.**

    Para quien tiene un plan B: una linea de diferencias de protocolo, donde
    lo que no es una frase conocida se muestra con solo el comando traducido.
    """
    if not texto:
        return texto
    return _traducir(texto, _COLUMNA[_IDIOMA_ACTUAL])


def faltantes() -> list[str]:
    """Los textos que `tr()` no supo traducir desde `olvidar_faltantes()`."""
    return sorted(_FALTANTES)


def olvidar_faltantes() -> None:
    _FALTANTES.clear()


# --- los textos ----------------------------------------------------------------
#
# Cada fila es `(castellano, inglés, chino)`: un texto no puede quedar traducido
# a un idioma y no al otro. Los que llevan `{variables}` son plantillas, y las
# columnas tienen que nombrar las mismas (lo cuida `driver/tests/interfaz.py`). Una
# cuarta columna, cuando la hay, es como se muestra en castellano en la ventana,
# y entonces el ingles y el chino traducen esa y no la clave.

_TEXTOS: tuple[tuple[str, ...], ...] = (
    # Barra superior
    ("Sin conectar",
     "Not connected",
     "未连接"),

    # --- por donde esta conectado el mouse, y en que puerto ---------------
    ("Dongle 2.4 GHz",
     "2.4 GHz dongle",
     "2.4 GHz 接收器"),
    ("Cable USB",
     "USB cable",
     "USB 线"),
    ("Conexión desconocida",
     "Unknown connection",
     "未知连接"),
    ("puerto",
     "port",
     "端口"),
    ("el dongle está en el puerto {puerto}",
     "the dongle is on port {puerto}",
     "接收器在端口 {puerto}"),
    ("el dongle está en el puerto {puerto} y el mouse está por cable en el puerto {otro}: mientras esté por cable no contesta por el dongle",
     "the dongle is on port {puerto} and the mouse is on the USB cable on port {otro}: while it is on the cable it does not answer over the dongle",
     "接收器在端口 {puerto}，鼠标通过 USB 线连接在端口 {otro}：接着线时它不会通过接收器响应"),
    ("el mouse está enchufado por el cable USB en el puerto {puerto}, y mientras esté así no habla por el dongle: no va a contestar. Sacá el cable —o cargalo de un cargador que no sea la PC— para poder configurarlo",
     "the mouse is plugged in over the USB cable on port {puerto}, and while it stays that way it does not talk over the dongle: it will not answer. Unplug the cable —or charge it from a charger that is not the PC— to be able to configure it",
     "鼠标通过 USB 线连接在端口 {puerto}，保持这样它就不会通过接收器通信：它不会响应。请拔掉线缆（或改用电脑以外的充电器）以便进行配置"),
    ("el mouse está por cable en el puerto {puerto}",
     "the mouse is on the USB cable on port {puerto}",
     "鼠标通过 USB 线连接在端口 {puerto}"),
    ("el mouse está por cable en el puerto {puerto}, pero su nodo no se puede abrir",
     "the mouse is on the USB cable on port {puerto}, but its node cannot be opened",
     "鼠标通过 USB 线连接在端口 {puerto}，但无法打开它的节点"),
    ("el mouse cambió de camino: vuelvo a abrirlo",
     "the mouse changed path: reopening it",
     "鼠标换了连接方式：重新打开"),
    ("hay un dispositivo de esta familia en el bus, pero no el canal de configuración",
     "there is a device of this family on the bus, but not the configuration channel",
     "总线上有本系列的设备，但没有配置通道"),
    ("no hay ningún mouse de esta familia en el bus USB",
     "there is no mouse of this family on the USB bus",
     "USB 总线上没有本系列的鼠标"),
    ("el dongle cambió de lugar: vuelvo a abrirlo",
     "the dongle moved: reopening it",
     "接收器换了位置：重新打开"),
    ("el mouse se fue del bus",
     "the mouse left the bus",
     "鼠标已从总线上移除"),
    # Los tres de `conexiones.elegir()`, que los muestra el cartel de arriba.
    # El castellano de pantalla (cuarta columna) dice lo mismo sin la cita de
    # la medicion, que en la terminal importa y en la ventana sobra.
    ("no hay ningun mouse de esta familia en el bus USB: ni el dongle de 2.4 GHz ni el mouse por cable. Esta puesto el dongle?",
     "there is no mouse of this family on the USB bus: neither the 2.4 GHz dongle nor the mouse over cable. Is the dongle plugged in?",
     "USB 总线上没有本系列的鼠标：既没有 2.4 GHz 接收器，也没有通过线缆连接的鼠标。接收器插好了吗？",
     "No hay ningún mouse de esta familia en el bus USB: ni el dongle de 2.4 GHz ni el mouse por cable. ¿Está puesto el dongle?"),
    ("el dongle esta en el puerto {puerto}, pero {nodo} no se puede abrir: faltan los permisos del nodo",
     "the dongle is on port {puerto}, but {nodo} cannot be opened: the node permissions are missing",
     "接收器在端口 {puerto}，但无法打开 {nodo}：缺少该节点的权限",
     "El dongle está en el puerto {puerto}, pero {nodo} no se puede abrir: faltan los permisos del nodo"),
    ("el mouse por cable esta en el puerto {puerto}, pero {nodo} no se puede abrir: faltan los permisos del nodo",
     "the mouse on the USB cable is on port {puerto}, but {nodo} cannot be opened: the node permissions are missing",
     "通过 USB 线连接的鼠标在端口 {puerto}，但无法打开 {nodo}：缺少该节点的权限",
     "El mouse por cable está en el puerto {puerto}, pero {nodo} no se puede abrir: faltan los permisos del nodo"),
    ("modelo",
     "model",
     "型号"),
    ("sin nombre",
     "unnamed",
     "无名称"),
    ("Batería: —",
     "Battery: —",
     "电量: —"),
    ("Batería:",
     "Battery:",
     "电量:"),
    ("cargando",
     "charging",
     "充电中"),
    ("estado sin medir",
     "unmeasured state",
     "未测量状态"),
    (" — sin novedades hace ",
     " — no updates for ",
     " — 无更新于 "),
    (" s",
     " s",
     " 秒"),
    ("Leer el mouse",
     "Read mouse",
     "读取鼠标"),
    # No "initial": se confunde con los de fabrica, que son los del otro boton.
    ("Volver a como estaba",
     "Revert to when opened",
     "恢复打开时的状态"),
    ("Valores seguros",
     "Safe defaults",
     "安全默认值"),
    ("Vuelve a los valores que tenía el mouse cuando se abrió esta ventana. No toca los macros.",
     "Reverts to the values the mouse had when this window was opened. Does not modify macros.",
     "恢复为此窗口打开时鼠标所具有的数值。不修改宏设置。"),
    ("Los valores de fábrica, con la tasa en {tasa} Hz para que el mouse se pueda seguir leyendo entero. No toca los macros.",
     "Factory defaults, with polling rate set to {tasa} Hz so the full profile can still be read. Does not modify macros.",
     "出厂默认值，回报率设为 {tasa} Hz 以确保可完整读取鼠标配置。不修改宏设置。"),
    ("Idioma / Language / 语言",
     "Language / Idioma / 语言",
     "语言 / Language / Idioma"),

    # Cartel de problema y udev
    ("Copiar comando",
     "Copy command",
     "复制命令"),
    ("Copiado",
     "Copied",
     "已复制"),
    ("Cerrar",
     "Close",
     "关闭"),
    ("Aplicar",
     "Apply",
     "应用"),
    ("La regla quedó instalada. Vuelve a conectar.",
     "Rule installed successfully. Reconnect the mouse.",
     "udev 规则已成功安装。请重新插拔或连接鼠标。"),
    ("El comando salió con código",
     "Command exited with code",
     "命令退出并返回代码"),
    ("Córrelo a mano",
     "Run it manually",
     "请手动运行"),

    # Cartel de tasa prestada
    ("Devolver la tasa ahora",
     "Restore rate now",
     "立即恢复回报率"),

    # Diálogo de restauración
    ("Son los valores que tenía el mouse cuando se abrió esta ventana. Los macros no se tocan.",
     "The values the mouse had when this window was opened. Macros are untouched.",
     "这是窗口打开时鼠标的数值。不修改宏设置。"),
    ("campos van a cambiar:",
     "field(s) will change:",
     "个设置项将发生更改："),
    ("No hay nada que cambiar: el mouse ya está así.",
     "Nothing to change: mouse already has these settings.",
     "无需更改：鼠标已应用这些设置。"),
    ("El mouse no contestó ",
     "The mouse did not respond to ",
     "鼠标未响应 "),
    (": esos campos ",
     ": those fields ",
     "：这些字段"),
    ("no figuran acá y <b>no se van a restaurar</b>. Lee de nuevo antes, o quedan como están.",
     "are not shown here and <b>will not be restored</b>. Re-read before proceeding, or they will stay as-is.",
     "未包含于此且<b>不会被恢复</b>。请先重新读取，否则它们将保持原样。"),
    ("Cancelar",
     "Cancel",
     "取消"),
    ("Escribir los {n}",
     "Write {n} field(s)",
     "写入全部 {n} 项"),

    # Pestañas principales y estado
    ("Parámetros",
     "Parameters",
     "参数设置"),
    ("Macros",
     "Macros",
     "宏管理"),
    ("Registro",
     "Log",
     "运行日志"),
    ("Limpiar",
     "Clear",
     "清空"),
    ("Listo",
     "Ready",
     "就绪"),
    ("Releer",
     "Re-read",
     "重新读取"),
    ("El mouse cambió solo al nivel de DPI {nivel} (alguien apretó el botón). Lo que se ve es de antes.",
     "The mouse autonomously changed to DPI level {nivel} (button pressed). Displayed values are from before.",
     "鼠标自主切换到了 DPI 档位 {nivel}（实体按键被按下）。当前界面显示的为先前数据。"),
    ("El mouse contestó entero",
     "Mouse responded completely",
     "鼠标已完整响应"),
    ("El mouse no contestó {n} comando(s): movelo y volvé a leer",
     "The mouse did not answer {n} command(s): move it and read again",
     "鼠标未响应 {n} 个命令：请移动鼠标后重新读取"),
    ("El mouse no contestó {n} comando(s) por cable: volvé a leer",
     "The mouse did not answer {n} command(s) over the cable: read again",
     "鼠标通过线缆未响应 {n} 个命令：请重新读取"),
    ("Cerrando: esperando a lo que esté andando…",
     "Closing: waiting for pending operations…",
     "正在退出：等待后台操作完成…"),
    ("    el dongle no acuso la trama",
     "    dongle did not acknowledge frame",
     "    接收器未确认数据帧"),
    ("Todavía no se leyó el mouse.",
     "Mouse has not been read yet.",
     "尚未读取鼠标配置。"),

    # Títulos de grupos (comandos)
    ("Tasa de reporte",
     "Polling Rate",
     "回报率"),
    ("Sensor y DPI",
     "Sensor and DPI",
     "传感器与 DPI"),
    ("Luz, reposo y respuesta",
     "Lighting, Sleep and Response",
     "灯效、休眠与响应时间"),
    ("Botones y rueda",
     "Buttons and Scroll Wheel",
     "按键与滚轮"),

    # Nombres de campos (modelo.py)
    ("DPI del nivel 1",
     "DPI Level 1",
     "DPI 档位 1"),
    ("DPI del nivel 2",
     "DPI Level 2",
     "DPI 档位 2"),
    ("DPI del nivel 3",
     "DPI Level 3",
     "DPI 档位 3"),
    ("DPI del nivel 4",
     "DPI Level 4",
     "DPI 档位 4"),
    ("DPI del nivel 5",
     "DPI Level 5",
     "DPI 档位 5"),
    ("DPI del nivel 6",
     "DPI Level 6",
     "DPI 档位 6"),
    ("DPI del nivel 7",
     "DPI Level 7",
     "DPI 档位 7"),
    ("DPI del nivel 8",
     "DPI Level 8",
     "DPI 档位 8"),
    ("Nivel de DPI en uso",
     "Active DPI Level",
     "当前 DPI 档位"),
    ("Altura de despegue (LOD)",
     "Lift-Off Distance (LOD)",
     "静默高度 (LOD)"),
    ("Control de ripple",
     "Ripple Control",
     "波纹控制"),
    ("Corrección de ángulo",
     "Angle Snapping",
     "直线修正"),
    ("Sincronización de movimiento",
     "Motion Sync",
     "动作同步"),
    ("Reposo corto",
     "Short Sleep",
     "浅度休眠"),
    ("Hibernación",
     "Deep Sleep",
     "深度休眠"),
    ("Tiempo de respuesta de los botones",
     "Button Response Time",
     "按键响应时间"),
    ("Color",
     "Color",
     "颜色"),

    # Opciones de controles (incluye las 54 de FUNCIONES_DE_BOTON)
    ("macro",
     "Macro",
     "宏"),
    ("Sí",
     "Yes",
     "开"),
    ("No",
     "No",
     "关"),
    ("valor actual",
     "current value",
     "当前值"),

    # Nombres de colores
    ("rojo",
     "red",
     "红色"),
    ("verde",
     "green",
     "绿色"),
    ("azul",
     "blue",
     "蓝色"),
    ("amarillo",
     "yellow",
     "黄色"),
    ("cian",
     "cyan",
     "青色"),
    ("magenta",
     "magenta",
     "品红"),
    ("naranja",
     "orange",
     "橙色"),
    ("blanco",
     "white",
     "白色"),

    # Unidades
    ("min",
     "min",
     "分钟"),
    ("ms",
     "ms",
     "ms"),
    ("mm",
     "mm",
     "mm"),
    ("Hz",
     "Hz",
     "Hz"),
    ("DPI",
     "DPI",
     "DPI"),

    # Diagrama de botones
    ("Esquema del mouse",
     "Mouse Diagram",
     "鼠标按键分布图"),
    ("Tocá un número para ir a su control",
     "Click a number to jump to its control",
     "点击数字跳转至对应按键设置"),
    ("Visto desde arriba",
     "Top view",
     "顶视图"),
    ("Visto desde abajo",
     "Bottom view",
     "底视图"),
    ("sin confirmar",
     "unconfirmed",
     "未确认"),

    # Evidencia de botones (COMO_SE_SUPO_EL_BOTON)

    # Panel de macros
    ("Selección de macro",
     "Macro Selection",
     "选择宏"),
    ("Macro:",
     "Macro:",
     "宏："),
    ("Agregar un ID:",
     "Add an ID:",
     "添加宏 ID："),
    ("Pedir este ID al leer",
     "Request this ID when reading",
     "读取时请求此 ID"),
    ("Nombre:",
     "Name:",
     "名称："),
    ("Guardar nombre",
     "Save name",
     "保存名称"),
    ("Nombre (guardado en este equipo, no en el mouse)",
     "Name (saved on this PC, not on the mouse)",
     "名称（保存在本设备，非鼠标板载）"),
    ("Disparo",
     "Trigger Mode",
     "触发模式"),
    ("Modo:",
     "Mode:",
     "模式："),
    ("Repeticiones:",
     "Repeat count:",
     "循环次数："),
    ("Pasos (hasta 50 eventos)",
     "Steps (up to 50 events)",
     "宏步骤（最多 50 个事件）"),
    ("Iniciar grabador",
     "Start recorder",
     "开始录制"),
    ("Detener grabador",
     "Stop recorder",
     "停止录制"),
    ("Grabar en el mouse",
     "Save to mouse",
     "写入鼠标"),
    ("reproducir N veces",
     "play N times",
     "循环 N 次"),
    # El nombre del fabricante es "stop on any key" y **no es lo que hace**:
    # MEDIDO que lo detiene otro boton del mouse, y que una tecla del teclado
    # no (2026-09-20). Se traduce lo medido.
    ("otro boton del mouse lo detiene",
     "another mouse button stops it",
     "按下另一个鼠标按键即可停止"),
    ("mantener apretado",
     "hold to repeat",
     "按住重复"),
    ("lo reproduce N veces y para solo",
     "plays N times and stops automatically",
     "循环 N 次并自动停止"),
    ("lo repite hasta que se apriete otro boton del mouse",
     "repeats until another mouse button is pressed",
     "重复执行直至按下另一个鼠标按键"),
    ("lo repite mientras el boton este apretado",
     "repeats while button is held down",
     "按住按键时持续重复"),
    ("El estado no incluye ningún macro. Solicita un ID arriba y vuelve a leer.",
     "State includes no macros. Request an ID above and read again.",
     "当前状态未包含任何宏。请在上方输入 ID 请求并重新读取。"),
    ("sin pasos: un macro vacio se escribe, pero no hace nada",
     "no steps: an empty macro will be written, but performs no actions",
     "无步骤：空宏可以写入，但不会执行任何操作"),
    ("El grabador está apagado. Inícialo y presiona las teclas que quieras que el macro repita",
     "Recorder is idle. Start it and press the sequence of keys you want the macro to repeat",
     "录制器已就绪。点击开始录制，并按下你希望宏重复执行的按键序列"),
    ("Grabando: presiona teclas y botones aquí adentro. Cada presionar y soltar es un evento",
     "Recording: press keys and mouse buttons here. Each press and release is recorded as an event",
     "正在录制：在此区域内按下按键。每次按下和释放均作为一个独立事件"),
    ("código",
     "code",
     "代码"),

    # Ayuda y notas de campos (modelo.py / sesion.py)

    # Notas exactas de modelo.py

    # Plantillas de lo que antes eran patrones a mano: la afirmacion va entera
    ("color de {nombre}",
     "Color of {nombre}",
     "{nombre} 的颜色"),

    # Avisos de macros (modelo.advertencias_de y el panel)
    ("Esa tecla no entra en un macro ({tecla}): el bloque guarda usages HID, y no todas las teclas tienen uno",
     "That key cannot go into a macro ({tecla}): the block stores HID usages, and not every key has one",
     "该按键无法放入宏（{tecla}）：数据块保存的是 HID usage，并非每个按键都有"),
    ("Los nombres no se pudieron leer y no se van a guardar: {problema}",
     "The names could not be read and will not be saved: {problema}",
     "无法读取名称，因此不会保存：{problema}"),
    ("Macro {n} (sin nombre propio)",
     "Macro {n} (no name of its own)",
     "宏 {n}（未命名）"),
    ("macro {n}",
     "macro {n}",
     "宏 {n}"),
    ("el esquema no sabe dónde cae {quienes}: el mouse los tiene y se configuran abajo, pero **dibujarlos sería inventar una posición**",
     "the diagram does not know where {quienes} sits: the mouse has them and they are configured below, but **drawing them would be inventing a position**",
     "示意图不知道 {quienes} 位于何处：鼠标确实有这些按键，也可以在下方设置，但**把它们画出来就是凭空编造位置**"),
    ("{n} ({nombre})",
     "{n} ({nombre})",
     "{n}（{nombre}）"),

    # Los comandos, como los nombra `protocol.CMD_NAMES`
    ("dpi", "DPI", "DPI"),
    ("iluminacion", "lighting", "灯效"),
    ("report rate", "polling rate", "回报率"),
    ("modo de despertado", "wake-up mode", "唤醒模式"),
    ("botones", "buttons", "按键"),
    ("perfil completo", "full profile", "完整配置"),
    ("version de firmware", "firmware version", "固件版本"),

    # La barra de estado mientras se lee (hardware.py)
    ("leyendo el mouse… movelo mientras tanto: así lee más rápido",
     "reading the mouse… move it meanwhile: it reads faster that way",
     "正在读取鼠标… 请同时移动鼠标：这样读取更快"),
    ("leyendo el mouse por cable…",
     "reading the mouse over the cable…",
     "正在通过线缆读取鼠标…"),
    ("leído {comando}: {n} B",
     "read {comando}: {n} B",
     "已读取 {comando}：{n} B"),
    ("{comando}: sin respuesta, lo reintento al final",
     "{comando}: no response, will retry at the end",
     "{comando}：无响应，稍后重试"),
    ("{comando}: SIN RESPUESTA",
     "{comando}: NO RESPONSE",
     "{comando}：无响应"),
    ("reintento de {n} comando(s) que no contestaron. Espero {n_s} s a que el dongle se despeje; mové el mouse.",
     "retrying {n} command(s) that did not respond. Waiting {n_s} s for the dongle to clear; move the mouse.",
     "重试 {n} 个未响应的命令。等待 {n_s} 秒让接收器恢复；请移动鼠标。"),
    ("reintento de {n} comando(s) que no contestaron, en {n_s} s.",
     "retrying {n} command(s) that did not respond, in {n_s} s.",
     "{n_s} 秒后重试 {n} 个未响应的命令。"),
    ("{n} seguidos sin respuesta",
     "{n} in a row without a response",
     "连续 {n} 个无响应"),
    ("el mouse esta a {n_hz} Hz, y arriba de {n_max} Hz los bloques largos no llegan (MEDIDO a 2000 y a 8000). No insisto: falta {nombres}. Para poder leerlo entero, bajá la tasa: driver/scripts/cambiar-rate.py --valor 1000",
     "the mouse is at {n_hz} Hz and above {n_max} Hz it cannot be read completely: {nombres} missing. Lower the polling rate to {n_max} Hz to read it all",
     "鼠标当前为 {n_hz} Hz，高于 {n_max} Hz 时无法完整读取：缺少 {nombres}。请将回报率降到 {n_max} Hz 以完整读取",
     "el mouse está a {n_hz} Hz y a más de {n_max} Hz no se puede leer entero: falta {nombres}. Bajá la tasa a {n_max} Hz para leerlo completo"),

    # Los avisos de la Etapa 3 (hardware._legible y sesion)
    ("respaldando el mouse entero antes de escribir…",
     "backing up the whole mouse before writing…",
     "写入前正在完整备份鼠标…"),
    ("releyendo para ver si el mouse aplico el cambio…",
     "re-reading to check whether the mouse applied the change…",
     "正在重新读取，确认鼠标是否应用了更改…"),
    ("releyendo lo que se escribio y el perfil completo…",
     "re-reading what was written and the full profile…",
     "正在重新读取已写入的内容和完整配置…"),
    ("el dongle acuso la trama",
     "the dongle acknowledged the frame",
     "接收器已确认数据帧"),
    ("sin acuse: se perdio el pedido o el formato no le gusto al mouse",
     "no acknowledgement: the request was lost or the mouse rejected the format",
     "无确认：请求丢失，或鼠标不接受该格式"),
    ("el mouse aceptó el report por cable",
     "the mouse accepted the report over the cable",
     "鼠标已通过线缆接受该报告"),
    ("el mouse rechazó el report por cable, aun repitiéndolo",
     "the mouse rejected the report over the cable, even after repeating it",
     "鼠标拒绝了通过线缆发送的报告，重试后依然如此"),
    ("hay que releer el mouse",
     "the mouse has to be read again",
     "需要重新读取鼠标"),
    ("hay que releer el mouse: {motivo}",
     "the mouse has to be read again: {motivo}",
     "需要重新读取鼠标：{motivo}"),
    ("cambio un bloque que no se puede escribir, asi que una de las dos "
     "lecturas vino mal y no hay nada que comparar",
     "a block that cannot be written changed, so one of the two reads came "
     "out wrong and there is nothing to compare",
     "一个无法写入的数据块发生了变化，因此两次读取中有一次出错，没有可比较的内容"),
    ("Las repeticiones solo existen en el modo «reproducir N veces». Cambiá el "
     "modo primero: escribirlas acá lo cambiaría sin avisar.",
     "Repeat counts only exist in the \u00abplay N times\u00bb mode. Change the mode "
     "first: writing them here would change it without saying so.",
     "重复次数仅存在于\u300c播放 N 次\u300d模式下。请先更改模式："
     "在此写入会在不提示的情况下更改模式。"),
    ("Quedarme en {max_hz} Hz",
     "Stay at {max_hz} Hz",
     "保持在 {max_hz} Hz"),
    ("el mouse se queda en {max_hz} Hz: ya no se le deben los {debia}",
     "the mouse stays at {max_hz} Hz: the {debia} are no longer owed",
     "鼠标保持在 {max_hz} Hz：不再需要归还 {debia}"),
    ("la lectura se contradice: {detalle}",
     "the read contradicts itself: {detalle}",
     "该次读取自相矛盾：{detalle}"),
    ("el respaldo previo se contradice a si mismo: el perfil completo y un "
     "bloque suelto traen bytes distintos de lo mismo, asi que una lectura "
     "vino mal y no sirve de red",
     "the prior backup contradicts itself: the full profile and a standalone "
     "block carry different bytes for the same thing, so one read came out "
     "wrong and it is no safety net",
     "事先备份自相矛盾：完整配置档与单独的数据块对同一内容给出了不同的字节，"
     "因此有一次读取出错，无法作为保障"),
    ("la relectura se contradice a si misma, asi que no se puede juzgar si el "
     "mouse aplico el cambio",
     "the read-back contradicts itself, so whether the mouse applied the "
     "change cannot be judged",
     "回读自相矛盾，因此无法判断鼠标是否已应用该更改"),
    ("no se escribió, el bloque tiene valores imposibles: {detalle}",
     "not written, the block holds impossible values: {detalle}",
     "未写入，该数据块含有不可能的值：{detalle}"),
    ("el bloque que se iba a escribir tiene valores fuera de rango y no se "
     "mando: sale de una lectura que vino mal, o de un codificador que la "
     "rompio",
     "the block about to be written holds out-of-range values and was not "
     "sent: it comes from a bad read, or from an encoder that broke it",
     "即将写入的数据块含有超出范围的值，因此未发送：它来自一次错误的读取，"
     "或来自破坏了该读取的编码器"),
    ("el mouse cambio de nivel de dpi solo",
     "the mouse changed DPI level on its own",
     "鼠标自行切换了 DPI 档位"),
    ("no pude releer {comando}",
     "could not re-read {comando}",
     "无法重新读取 {comando}"),
    ("una escritura termino sin poder releer el mouse",
     "a write finished without being able to re-read the mouse",
     "一次写入结束后未能重新读取鼠标"),
    ("el mouse esta a {n_hz} Hz, y arriba de {n_max} Hz el respaldo de los siete comandos no sale (MEDIDO a 2000 y a 8000). Bajo a 1000 para poder respaldar y te devuelvo los {n_hz} al terminar, pase lo que pase: va en el `finally`, asi que vuelve aunque la escritura falle",
     "the mouse is at {n_hz} Hz and cannot be backed up at that rate: lowering it to 1000 Hz to write, then returning it to {n_hz} Hz, even if the write fails",
     "鼠标当前为 {n_hz} Hz，在此回报率下无法备份：先降到 1000 Hz 进行写入，之后恢复为 {n_hz} Hz，即使写入失败也会恢复",
     "el mouse está a {n_hz} Hz y a esa velocidad no se puede respaldar: lo bajo a 1000 Hz para escribir y después lo devuelvo a {n_hz} Hz, aunque la escritura falle"),
    ("el mouse esta a {n_hz} Hz, y arriba de {n_max} Hz los bloques largos no llegan (MEDIDO a 2000 y a 8000). La bajo a {n_max} **una sola vez** mientras configuras, y te devuelvo los {n_hz} al terminar",
     "the mouse is at {n_hz} Hz and cannot be read completely at that rate: lowering it to {n_max} Hz while you configure it, then returning it to {n_hz} Hz",
     "鼠标当前为 {n_hz} Hz，在此回报率下无法完整读取：配置期间降到 {n_max} Hz，之后恢复为 {n_hz} Hz",
     "el mouse está a {n_hz} Hz y a esa velocidad no se puede leer entero: lo bajo a {n_max} Hz mientras lo configurás y después lo devuelvo a {n_hz} Hz"),
    ("uso el respaldo de {fecha} en vez de leer el mouse entero de nuevo",
     "using the backup from {fecha} instead of reading the whole mouse again",
     "使用 {fecha} 的备份，不再重新完整读取鼠标"),
    ("fecha desconocida", "unknown date", "未知日期"),
    ("tasa devuelta a {n} Hz",
     "polling rate restored to {n} Hz",
     "回报率已恢复为 {n} Hz"),
    ("OJO: la tasa quedo en {n_quedo} Hz, no en {n_hz}",
     "WARNING: the polling rate ended at {n_quedo} Hz, not {n_hz}",
     "注意：回报率停在 {n_quedo} Hz，而不是 {n_hz}"),
    ("OJO: la tasa quedo en {n_quedo} Hz, no en {n_hz}. Revisala con driver/scripts/cambiar-rate.py",
     "WARNING: the polling rate ended at {n_quedo} Hz, not {n_hz}. Check it with driver/scripts/cambiar-rate.py",
     "注意：回报率停在 {n_quedo} Hz，而不是 {n_hz}。请用 driver/scripts/cambiar-rate.py 检查"),

    # Como salio una escritura (sesion.MOTIVOS y el veredicto)
    ("el mouse quedo exactamente como estaba, que es lo que tenia que pasar",
     "the mouse stayed exactly as it was, which is what had to happen",
     "鼠标保持原样，这正是应有的结果"),
    ("cambio algo, y en una escritura idempotente eso NO tenia que pasar",
     "something changed, and in an idempotent write that should NOT have happened",
     "有内容发生了变化，而幂等写入中这本不应发生"),
    ("no cambio nada, y se pidio un cambio. O el mouse ignoro la trama, o la relectura trajo un estado viejo",
     "nothing changed, and a change was requested. Either the mouse ignored the frame, or the re-read brought back a stale state",
     "没有任何变化，但请求了更改。要么鼠标忽略了数据帧，要么重新读取得到的是旧状态"),
    ("cambio algo, pero no el comando que se pidio",
     "something changed, but not the requested command",
     "有内容发生了变化，但不是所请求的命令"),
    ("cambio lo que se pidio, pero tambien algo que no se toco",
     "the requested change happened, but so did something that was not touched",
     "请求的更改已生效，但未触及的内容也发生了变化"),
    ("cambio lo que se pidio, y nada mas",
     "the requested change happened, and nothing else",
     "请求的更改已生效，且没有其他变化"),
    ("el mouse esta arriba de 1000 Hz y el respaldo completo no sale a esa tasa",
     "the mouse is above 1000 Hz and the full backup does not complete at that rate",
     "鼠标回报率高于 1000 Hz，在此回报率下无法完成完整备份"),
    ("no se pudo bajar la tasa para poder respaldar",
     "the polling rate could not be lowered to make the backup",
     "无法降低回报率以进行备份"),
    ("el respaldo previo salio incompleto, y un respaldo incompleto no sirve como red",
     "the prior backup came out incomplete, and an incomplete backup is no safety net",
     "事先备份不完整，而不完整的备份无法作为保障"),
    ("el mouse no contesto la lectura del comando que se iba a escribir",
     "the mouse did not answer the read of the command about to be written",
     "鼠标未响应对即将写入的命令的读取"),
    ("el mouse no contesto ni la lectura de la tasa, que es la mas corta de todas: movelo y volvé a leer",
     "the mouse did not answer even the polling rate read, the shortest one of all: move it and read again",
     "鼠标连最短的回报率读取都没有响应：请移动鼠标后重新读取"),
    ("el mouse contesto la tasa con un byte que no es ninguno de los siete conocidos y no se la pudo dejar en 1000 Hz, asi que no se sabe a cuanto esta y no se lee ni se escribe. driver/scripts/cambiar-rate.py lo muestra, y con --valor lo cambia",
     "the mouse answered the polling rate with a byte that is none of the seven known ones and it could not be set to 1000 Hz, so its rate is unknown and nothing is read or written. driver/scripts/cambiar-rate.py shows it, and with --valor changes it",
     "鼠标返回的回报率字节不属于已知的七种之一，且无法将其设为 1000 Hz，因此无法得知当前回报率，不会读取也不会写入。driver/scripts/cambiar-rate.py 可以显示它，加上 --valor 可以修改它"),
    ("el mouse tenia la tasa en un byte que no es ninguno de los siete conocidos ({byte}), asi que no se sabia a cuanto estaba. La puse en {n_max} Hz para poder leerlo, y ahi queda: no hay una tasa anterior que devolver",
     "the mouse had its polling rate set to a byte that is none of the seven known ones ({byte}), so its rate was unknown. It was set to {n_max} Hz to be able to read the mouse, and it stays there: there is no previous rate to return to",
     "鼠标的回报率字节不属于已知的七种之一（{byte}），因此无法得知之前的回报率。已将其设为 {n_max} Hz 以便读取鼠标，并保持不变：没有可以恢复的原回报率",
     "el mouse tenía la tasa en un valor que no se entiende ({byte}), así que no se sabía a cuánto estaba. La puse en {n_max} Hz para poder leerlo, y ahí queda: no hay una tasa anterior que devolver"),
    ("no se confirmo la escritura",
     "the write was not confirmed",
     "写入未获确认"),
    ("por este camino el macro no se puede releer, asi que no se escribe",
     "over this path the macro cannot be read back, so it is not written",
     "通过此连接无法回读宏，因此不写入",
     "Por este camino el macro no se puede releer, así que no se escribe"),
    ("la relectura salio incompleta, asi que no se puede comparar",
     "the re-read came out incomplete, so nothing can be compared",
     "重新读取不完整，因此无法比较"),
    ("el mouse esta listo para configurarlo",
     "the mouse is ready to be configured",
     "鼠标已可进行配置"),
    ("la tasa quedo puesta, y la relectura lo confirma. Verificala por fuera del protocolo si querés: driver/scripts/medir-polling.py --segundos 10",
     "the polling rate is set, and re-reading the mouse confirms it",
     "回报率已设置，重新读取鼠标后确认生效",
     "la tasa quedó puesta, y releyendo el mouse se confirma"),
    ("el mouse no aplico la tasa aunque el dongle acusara. Probá de nuevo moviendo el mouse",
     "the mouse did not apply the polling rate even though the dongle acknowledged. Try again while moving the mouse",
     "尽管接收器已确认，鼠标仍未应用回报率。请一边移动鼠标一边重试"),
    ("esa tasa no es ninguna de las siete que el driver oficial escribe",
     "that polling rate is none of the seven the official driver writes",
     "该回报率不属于官方驱动写入的七种之一"),
    ("{motivo} (no se releyo bloque por bloque, pero el perfil completo tampoco se movio, y el perfil acompaña a todo cambio de dpi, luz, tasa y botones: MEDIDO sobre 95 pares de respaldos)",
     "{motivo}",
     "{motivo}",
     "{motivo}"),
    ("{motivo} — OJO: no se releyeron {nombres}, asi que \"y nada mas\" no se verifico para ellos",
     "{motivo} — WARNING: {nombres} were not re-read, so \"and nothing else\" was not verified for them",
     "{motivo} — 注意：未重新读取 {nombres}，因此没有为它们验证“且没有其他变化”"),
    ("{nombre}: uno de los dos no contesto ({cual})",
     "{nombre}: one of the two did not respond ({cual})",
     "{nombre}：两者之一未响应（{cual}）"),

    # El registro
    ("salio bien: {detalle}", "succeeded: {detalle}", "成功：{detalle}"),
    ("NO salio: {detalle}", "did NOT succeed: {detalle}", "未成功：{detalle}"),
    ("escribiendo {clave} = {valor}",
     "writing {clave} = {valor}",
     "正在写入 {clave} = {valor}"),
    ("escribiendo {clave} del macro {n} = {valor}",
     "writing {clave} of macro {n} = {valor}",
     "正在写入宏 {n} 的 {clave} = {valor}"),
    ("restaurando {n} campos",
     "restoring {n} fields",
     "正在恢复 {n} 个设置项"),
    ("la tasa quedo prestada: el mouse esta a {n_max} Hz y vuelve a {n_hz}",
     "polling rate borrowed: the mouse is at {n_max} Hz and goes back to {n_hz}",
     "回报率已临时借用：鼠标当前为 {n_max} Hz，之后恢复为 {n_hz}"),
    ("conectado a {nodo}", "connected to {nodo}", "已连接到 {nodo}"),
    ("(device inyectado)", "(injected device)", "（注入的设备）"),
    ("problema: {mensaje}", "problem: {mensaje}", "问题：{mensaje}"),

    # Cerrar (hardware.py)
    ("esperando a que termine lo que esta andando ({n})…",
     "waiting for running operations to finish ({n})…",
     "正在等待进行中的操作完成（{n}）…"),
    ("{n} operacion(es) no terminaron a tiempo y se cortaron. Si estabas grabando un macro, revisalo con driver/scripts/respaldar.py antes de confiar en el",
     "{n} operation(s) did not finish in time and were cut off. If you were writing a macro, check it with driver/scripts/respaldar.py before trusting it",
     "{n} 个操作未能按时完成，已被中断。如果当时正在写入宏，请先用 driver/scripts/respaldar.py 检查后再使用"),
    ("devolviendo la tasa a {n} Hz…",
     "restoring the polling rate to {n} Hz…",
     "正在将回报率恢复为 {n} Hz…"),
    ("no pude devolver la tasa al cerrar. Revisala con driver/scripts/cambiar-rate.py",
     "could not restore the polling rate on close. Check it with driver/scripts/cambiar-rate.py",
     "关闭时未能恢复回报率。请用 driver/scripts/cambiar-rate.py 检查"),
    ("el hilo de hardware no esta andando",
     "the hardware thread is not running",
     "硬件线程未运行"),
    ("no pude encolar el pedido: {error}",
     "could not queue the request: {error}",
     "无法将请求加入队列：{error}"),

    # El dongle y el modelo (hidraw.py, dispositivos.py): el cartel de problema
    ("no encontre la interfaz {interfaz} de {usb}. Esta puesto el dongle?",
     "could not find interface {interfaz} of {usb}. Is the dongle plugged in?",
     "未找到 {usb} 的接口 {interfaz}。接收器插好了吗？"),
    ("{nodo} no aparece en {sys}; no puedo verificar que sea el canal de configuracion del dongle",
     "{nodo} does not appear in {sys}; cannot verify that it is the dongle's configuration channel",
     "{nodo} 不在 {sys} 中；无法确认它是接收器的配置通道"),
    ("{nodo} es {que}, y esto solo habla con {usb} interfaz {n} (el dongle de 2.4 GHz).{extra}",
     "{nodo} is {que}, and this only talks to {usb} interface {n} (the 2.4 GHz dongle).{extra}",
     "{nodo} 是 {que}，而本程序只与 {usb} 接口 {n}（2.4 GHz 接收器）通信。{extra}"),
    ("{usb} interfaz {n}", "{usb} interface {n}", "{usb} 接口 {n}"),
    ("Ese es el X8 Pro por CABLE, que se configura con Feature Reports; este codigo no le sirve.",
     "That is the WIRED X8 Pro, which is configured with Feature Reports; this code does not work for it.",
     "那是通过线缆连接的 X8 Pro，它通过 Feature Report 配置；本程序不适用。"),
    ("sin permiso sobre {nodo}. Instala la regla de udev:",
     "no permission on {nodo}. Install the udev rule:",
     "没有 {nodo} 的访问权限。请安装 udev 规则："),
    ("que copia udev/70-attackshark-x8pro.rules y corre",
     "which copies udev/70-attackshark-x8pro.rules and runs",
     "它会复制 udev/70-attackshark-x8pro.rules 并运行"),
    ("{nodo} se abrio en solo lectura (modo listen): no se le escribe nada al mouse",
     "{nodo} was opened read-only (listen mode): nothing is written to the mouse",
     "{nodo} 以只读方式打开（监听模式）：不会向鼠标写入任何内容"),
    ("device id {n} no figura en el catalogo del bundle ({n_modelos} modelos). Puede ser un modelo mas nuevo",
     "the connected mouse (device id {n}) is not a known model: it may be a newer one",
     "已连接的鼠标（设备 ID {n}）不是已知型号：可能是较新的型号",
     "el mouse conectado (device id {n}) no es un modelo conocido: puede ser uno más nuevo"),
    ("el mouse dice ser un {nombre} (device id {n}), que el bundle conoce pero este codigo **no tiene medido**. Todo lo que hay esta verificado contra un {medido} y solo contra ese: los tamaños de bloque, los slots y la permutacion pueden ser otros. Para agregarlo hace falta la captura de su driver oficial, no adivinar offsets parecidos (ver dev/docs/metodo.md)",
     "the connected mouse is a {nombre} (device id {n}), a model this application does not support yet: it stores its settings differently from a {medido}, so writing to it is not advisable",
     "已连接的鼠标是 {nombre}（设备 ID {n}），本程序暂不支持该型号：它保存设置的方式与 {medido} 不同，因此不建议向其写入",
     "el mouse conectado es un {nombre} (device id {n}), un modelo que esta aplicación todavía no soporta: guarda sus ajustes distinto que un {medido}, así que no conviene escribirle"),

    # Lo que se escribe a mano: el parametro de un boton, un atajo, un macro
    ("{que} (ej: {ejemplo})", "{que} (e.g. {ejemplo})", "{que}（例：{ejemplo}）"),
    ("el id del macro", "the macro id", "宏 ID"),
    ("el atajo de teclado", "the keyboard shortcut", "键盘快捷键"),
    ("la funcion 'macro' necesita el id del macro: ('macro', 17)",
     "the 'macro' function needs the macro id: ('macro', 17)",
     "“宏”功能需要宏 ID：('macro', 17)"),
    ("la funcion 'atajo de teclado' necesita el atajo: ('atajo de teclado', 'ctrl+c')",
     "the 'keyboard shortcut' function needs the shortcut: ('atajo de teclado', 'ctrl+c')",
     "“键盘快捷键”功能需要快捷键：('atajo de teclado', 'ctrl+c')"),
    ("el id del macro es un numero, y {valor} no lo es",
     "the macro id is a number, and {valor} is not",
     "宏 ID 必须是数字，而 {valor} 不是"),
    ("la funcion {nombre} no lleva parametro",
     "the function {nombre} takes no parameter",
     "功能 {nombre} 不需要参数"),
    ("macro id {n} fuera de {n_min}..{n_max}, que es el rango del mouse",
     "macro id {n} outside {n_min}..{n_max}, which is the mouse's range",
     "宏 ID {n} 超出 {n_min}..{n_max}，这是鼠标支持的范围"),
    ("macro id {n} fuera de {n_min}..{n_max}",
     "macro id {n} outside {n_min}..{n_max}",
     "宏 ID {n} 超出 {n_min}..{n_max}"),
    ("tecla {tecla}: no esta en la tabla. Van por nombre -`a`..`z`, `0`..`9`, `f1`..`f24`, `enter`, `esc`, `espacio`, `tab`, `supr`, `flecha-arriba`, `num-7`...- y tambien se aceptan los del bundle (`KeyA`, `ArrowUp`). Las 111 estan en TECLAS_HID, y el CLI las lista con --listar-teclas",
     "key {tecla}: not recognized. Keys go by name: `a`..`z`, `0`..`9`, `f1`..`f24`, `enter`, `esc`, `espacio`, `tab`, `supr`, `flecha-arriba`, `num-7`…",
     "按键 {tecla}：无法识别。按键按名称书写：`a`..`z`、`0`..`9`、`f1`..`f24`、`enter`、`esc`、`espacio`、`tab`、`supr`、`flecha-arriba`、`num-7`……",
     "tecla {tecla}: no se reconoce. Las teclas van por nombre: `a`..`z`, `0`..`9`, `f1`..`f24`, `enter`, `esc`, `espacio`, `tab`, `supr`, `flecha-arriba`, `num-7`…"),
    ("usage {usage}: no es ninguna de las {n} teclas que declara el bundle. La tabla esta en TECLAS_HID",
     "usage {usage}: not a known key",
     "usage {usage}：不是已知按键",
     "usage {usage}: no es una tecla conocida"),
    ("un atajo vacio no es un atajo: el slot queda en `11 00 00` y el boton, muerto",
     "an empty shortcut is not a shortcut: the slot ends up as `11 00 00` and the button, dead",
     "空的快捷键不算快捷键：槽位会变成 `11 00 00`，按键也就失效了"),
    ("{tecla} es un modificador, y en un atajo los modificadores van en p1, no en p2. Escribilo como `ctrl+c`",
     "{tecla} is a modifier, and in a shortcut modifiers go in p1, not in p2. Write it as `ctrl+c`",
     "{tecla} 是修饰键，快捷键中的修饰键放在 p1 而不是 p2。请写成 `ctrl+c`"),
    ("modificador {modificador}: los unicos cuatro que el bundle y el soft escriben son {lista}",
     "modifier {modificador}: the ones that can be used are {lista}",
     "修饰键 {modificador}：可以使用的有 {lista}",
     "modificador {modificador}: los que se pueden usar son {lista}"),
    ("{error}. En un macro valen ademas los cinco botones del mouse ({botones}) y los modificadores como tecla suelta",
     "{error}. In a macro the five mouse buttons ({botones}) and the modifiers as standalone keys are valid too",
     "{error}。在宏中还可以使用鼠标的五个按键（{botones}），以及单独使用的修饰键"),
    ("usage {n}: es el marcador de continuacion de los tiempos largos, no una tecla. Un evento con ese usage rompe la lectura del bloque entero",
     "usage {n}: it is the continuation marker for long delays, not a key. An event with that usage breaks reading the whole block",
     "usage {n}：这是长延时的续接标记，不是按键。带有该 usage 的事件会破坏整个数据块的读取"),
    ("usage {usage}: no es ninguna tecla del bundle, ninguno de los ocho modificadores ni ninguno de los cinco botones del mouse",
     "usage {usage}: not a key, a modifier or a mouse button",
     "usage {usage}：既不是按键，也不是修饰键或鼠标按键",
     "usage {usage}: no es una tecla, un modificador ni un botón del mouse"),
    ("direccion {direccion}: las dos son {lista}",
     "direction {direccion}: the two are {lista}",
     "方向 {direccion}：只有这两种：{lista}"),
    ("direccion {direccion}: es un bit, 0 o 1",
     "direction {direccion}: it is a bit, 0 or 1",
     "方向 {direccion}：它是一个位，只能是 0 或 1"),
    ("tiempo {n} ms: entra de 0 a {n_max}, que es hasta donde llega la rama larga (las centenas van en un byte)",
     "delay {n} ms: it fits from 0 to {n_max}, which is as far as the long branch reaches (hundreds go in one byte)",
     "延时 {n} 毫秒：范围为 0 到 {n_max}，这是长分支能表示的上限（百位存放在一个字节中）"),
    ("{n} eventos ocupan {n_b} B y en el bloque entran {n_max}: son {n_cortos} eventos cortos, y cada uno de mas de {n_ms} ms cuenta por dos (hay {n_largos}). Que pasa si se manda un bloque mas largo no se midio, y averiguarlo pisando el checksum no es la forma",
     "{n} events do not fit in a macro: it holds {n_cortos} short events, and each one over {n_ms} ms takes the space of two (there are {n_largos})",
     "{n} 个事件放不进一个宏：最多容纳 {n_cortos} 个短事件，每个超过 {n_ms} 毫秒的事件占两个位置（共有 {n_largos} 个）",
     "{n} eventos no entran en un macro: caben {n_cortos} eventos cortos, y cada uno de más de {n_ms} ms ocupa como dos (hay {n_largos})"),
    ("{paso}: cada evento se escribe `tecla:direccion@ms`, por ejemplo `clic-izquierdo:abajo@10` o `a:dir1@20`",
     "{paso}: each event is written as `tecla:direccion@ms`, for example `clic-izquierdo:abajo@10` or `a:dir1@20`",
     "{paso}：每个事件写作 `tecla:direccion@ms`，例如 `clic-izquierdo:abajo@10` 或 `a:dir1@20`"),
    ("{paso}: {ms} no es un numero de milisegundos",
     "{paso}: {ms} is not a number of milliseconds",
     "{paso}：{ms} 不是毫秒数"),
    ("la lista de eventos esta vacia. Un macro sin eventos se puede escribir, pero no hace nada: si es lo que queres, decilo con un evento de 0 ms",
     "the event list is empty. A macro with no events can be written, but it does nothing: if that is what you want, say so with a 0 ms event",
     "事件列表为空。没有事件的宏可以写入，但什么也不做：如果确实需要，请用一个 0 毫秒的事件明确表示"),
    ("no escribo encima de un archivo que no pude leer ({problema}). Movelo o borralo a mano: si tiene nombres adentro, esto los perderia",
     "not writing over a file that could not be read ({problema}). Move it or delete it by hand: if it has names inside, this would lose them",
     "不会覆盖无法读取的文件（{problema}）。请手动移动或删除它：如果里面有名称，覆盖会导致丢失"),
    ("modo {n}: los unicos tres observados en el bus son {lista}",
     "mode {n}: the only three observed on the bus are {lista}",
     "模式 {n}：总线上只观察到这三种：{lista}"),
    ("repeticiones {n} fuera de {n_min}..{n_max}",
     "repetitions {n} outside {n_min}..{n_max}",
     "重复次数 {n} 超出 {n_min}..{n_max}"),

    # El valor de un boton con su parametro (estructuras.detalle_de_slot)
    ("{funcion} (p1={n_p1}, p2={n_p2})", "{funcion} (p1={n_p1}, p2={n_p2})", "{funcion}（p1={n_p1}，p2={n_p2}）"),

    # El esquema, con tres vistas
    ("Visto desde la izquierda", "Left view", "左视图"),

    # Que es cada parametro (la ayuda del `?`), y los textos de pantalla
    # que reemplazaron a los que citaban la evidencia
    ("Qué es y para qué sirve",
     "What it is and what it is for",
     "是什么、有什么用"),
    ("Cuántas veces por segundo el mouse le informa su movimiento a la computadora.\n\nMás alta da un puntero más fluido y con menos demora; más baja gasta menos batería y menos procesador.",
     "How many times per second the mouse reports its movement to the computer.\n\nHigher gives a smoother pointer with less delay; lower uses less battery and less processing.",
     "鼠标每秒向电脑报告移动的次数。\n\n越高指针越流畅、延迟越低；越低越省电，也更节省处理器资源。"),
    ("La sensibilidad de este nivel: cuántos puntos avanza el puntero por cada pulgada que movés el mouse.\n\nMás alta, el puntero recorre más distancia con menos movimiento. El botón de DPI pasa de un nivel a otro.",
     "The sensitivity of this level: how many dots the pointer moves for every inch you move the mouse.\n\nHigher means the pointer covers more distance with less movement. The DPI button switches between levels.",
     "该档位的灵敏度：鼠标每移动一英寸，指针移动多少个点。\n\n越高，移动越少指针走得越远。DPI 键可在各档位之间切换。"),
    ("El nivel de DPI que el mouse está usando ahora.\n\nEs el mismo que cambia el botón de DPI, y el LED del mouse se pone del color de ese nivel.",
     "The DPI level the mouse is using right now.\n\nIt is the same one the DPI button changes, and the mouse's LED takes that level's color.",
     "鼠标当前使用的 DPI 档位。\n\n与 DPI 键切换的是同一个设置，鼠标的指示灯会显示该档位的颜色。"),
    ("A qué altura el sensor deja de seguir el movimiento cuando levantás el mouse.\n\nMás baja evita que el puntero se corra al levantarlo para reacomodarlo; más alta sigue leyendo aunque lo separes un poco de la superficie.",
     "The height at which the sensor stops tracking when you lift the mouse.\n\nLower keeps the pointer from drifting when you lift it to reposition it; higher keeps tracking even when the mouse is slightly off the surface.",
     "抬起鼠标时传感器停止追踪的高度。\n\n越低，抬起鼠标重新摆放时指针越不容易漂移；越高，鼠标稍微离开表面时仍会继续追踪。"),
    ("Suaviza las pequeñas vibraciones que tiene la lectura del sensor, sobre todo con DPI altos.\n\nDa un puntero más estable a cambio de un poco de demora.",
     "Smooths out the small jitter in the sensor reading, especially at high DPI.\n\nGives a steadier pointer at the cost of a little delay.",
     "平滑传感器读数中的细微抖动，在高 DPI 时尤其明显。\n\n指针更稳定，但会略微增加延迟。"),
    ("Endereza los movimientos casi rectos para que salgan perfectamente horizontales o verticales.\n\nAyuda a trazar líneas rectas; en juegos suele preferirse apagada, porque cambia el movimiento real.",
     "Straightens nearly straight movements so they come out perfectly horizontal or vertical.\n\nHelps draw straight lines; in games it is usually left off, because it alters the real movement.",
     "将接近直线的移动修正为完全水平或垂直。\n\n有助于画直线；游戏中通常关闭，因为它会改变实际的移动轨迹。"),
    ("Sincroniza las lecturas del sensor con los envíos a la computadora, para que cada reporte llegue a intervalos parejos.\n\nEl movimiento resulta más uniforme, con una demora mínima.",
     "Synchronizes sensor readings with the reports sent to the computer, so each report arrives at even intervals.\n\nMovement feels more uniform, with a minimal delay.",
     "使传感器读数与发送给电脑的报告同步，让每次报告以均匀的间隔到达。\n\n移动更加均匀，延迟极小。"),
    ("Cuántos minutos sin usar el mouse pasan hasta que entra en el primer modo de ahorro de batería.",
     "How many minutes without use before the mouse enters its first battery-saving mode.",
     "鼠标闲置多少分钟后进入第一级省电模式。"),
    ("Cuántos minutos más, contados desde que entra en reposo corto, pasan hasta que el mouse se duerme del todo para ahorrar batería.\n\nMás corto hace durar más la batería.",
     "How many more minutes, counted from when short sleep begins, until the mouse fully goes to sleep to save battery.\n\nShorter makes the battery last longer.",
     "从进入浅度休眠开始，再经过多少分钟鼠标会完全休眠以节省电量。\n\n越短电池续航越长。"),
    ("Cuánto espera el mouse para confirmar que un botón se apretó o se soltó.\n\nMás bajo responde antes, pero puede registrar clics dobles que no hiciste; más alto evita esos clics fantasma.",
     "How long the mouse waits to confirm that a button was pressed or released.\n\nLower responds sooner but may register double clicks you did not make; higher prevents those ghost clicks.",
     "鼠标确认按键已按下或松开前等待的时间。\n\n越低响应越快，但可能误触发你并未进行的双击；越高可避免这类误触。"),
    ("El color de la iluminación del mouse.",
     "The color of the mouse lighting.",
     "鼠标灯光的颜色。"),
    ("El botón secundario, que normalmente abre el menú contextual.\n\nElegí qué hace al apretarlo.",
     "The secondary button, which normally opens the context menu.\n\nChoose what it does when pressed.",
     "副按键，通常用于打开右键菜单。\n\n选择按下时执行的功能。"),
    ("El clic que se hace apretando la rueda.\n\nElegí qué hace al apretarla.",
     "The click made by pressing the wheel down.\n\nChoose what it does when pressed.",
     "按下滚轮时产生的点击。\n\n选择按下时执行的功能。"),
    ("El botón del costado que queda más atrás, donde apoya el pulgar.\n\nNormalmente vuelve a la página anterior. Elegí qué hace al apretarlo.",
     "The side button nearer the back, where the thumb rests.\n\nIt normally goes back to the previous page. Choose what it does when pressed.",
     "侧面靠后、拇指所在位置的按键。\n\n通常用于返回上一页。选择按下时执行的功能。"),
    ("El botón del costado que queda más adelante.\n\nNormalmente avanza a la página siguiente. Elegí qué hace al apretarlo.",
     "The side button nearer the front.\n\nIt normally goes forward to the next page. Choose what it does when pressed.",
     "侧面靠前的按键。\n\n通常用于前进到下一页。选择按下时执行的功能。"),
    ("El botón de la base, al lado del sensor, que normalmente pasa al siguiente nivel de DPI.\n\nElegí qué hace al apretarlo.",
     "The button on the base, next to the sensor, which normally moves to the next DPI level.\n\nChoose what it does when pressed.",
     "底部传感器旁边的按键，通常用于切换到下一个 DPI 档位。\n\n选择按下时执行的功能。"),
    ("Este botón cambia el modo de conexión del mouse, y lo sigue haciendo aunque le asignes otra función:\n\nal apretarlo va a cambiar de modo y, además, va a hacer la acción que le pongas.",
     "This button switches the mouse's connection mode, and keeps doing so even if you assign it another function:\n\npressing it will switch modes and also perform the action you assign.",
     "此按键用于切换鼠标的连接模式，即使为它分配了其他功能也仍会切换：\n\n按下时会切换模式，同时执行你分配的操作。"),
    ("Muestra dónde está cada botón del mouse, con el mismo número que tiene en la lista de abajo: arriba, en el costado izquierdo y en la base.\n\nTocá un número para ir a su configuración.",
     "Shows where each mouse button is, with the same number it has in the list below: on top, on the left side and on the base.\n\nClick a number to go to its setting.",
     "显示鼠标每个按键的位置，编号与下方列表中的相同：分布在顶部、左侧和底部。\n\n点击编号即可跳转到对应设置。"),
    ("Leyendo el mouse…\nMovelo mientras tanto: así lee más rápido.",
     "Reading the mouse…\nMove it meanwhile: it reads faster that way.",
     "正在读取鼠标…\n请同时移动鼠标：这样读取更快。"),
    ("Leyendo el mouse…",
     "Reading the mouse…",
     "正在读取鼠标…"),
    ("El mouse avisa la batería cada pocos segundos. Hace un rato que no avisa —por ejemplo, si está conectado por cable—, así que este número puede estar desactualizado.",
     "The mouse reports its battery every few seconds. It has not reported for a while —for example, if it is connected by cable—, so this number may be out of date.",
     "鼠标每隔几秒报告一次电量。它已有一段时间没有报告（例如通过线缆连接时），因此这个数值可能已经过时。"),
    ("El mouse está a {max_hz} Hz mientras lo configurás: a más velocidad no se puede leer entero. Vuelve solo a {hz} Hz al cerrar la ventana o después de un rato sin cambios.",
     "The mouse is at {max_hz} Hz while you configure it: at a higher rate it cannot be read completely. It goes back to {hz} Hz by itself when you close the window or after a while without changes.",
     "配置期间鼠标回报率为 {max_hz} Hz：更高的回报率下无法完整读取。关闭窗口或一段时间没有更改后，会自动恢复为 {hz} Hz。"),
    ("Son los valores de fábrica, con la tasa en {tasa} Hz para que el mouse se pueda seguir leyendo entero. Los macros no se tocan.",
     "These are the factory defaults, with the polling rate at {tasa} Hz so the mouse can still be read completely. Macros are not touched.",
     "这是出厂默认值，回报率设为 {tasa} Hz，以便仍能完整读取鼠标。不会改动宏。"),
    ("Son {n} escrituras, una detrás de otra. Mové el mouse mientras tanto: así van más rápido.",
     "That is {n} writes, one after another. Move the mouse meanwhile: they go faster that way.",
     "将依次执行 {n} 次写入。请同时移动鼠标：这样会更快。"),
    ("Son {n} escrituras, una detrás de otra.",
     "That is {n} writes, one after another.",
     "将依次执行 {n} 次写入。"),
    ("El mouse está a {hz} Hz, y a más de {max_hz} Hz no se puede leer entero: faltan {n}. Poné la tasa en {max_hz} Hz para leerlo completo.",
     "The mouse is at {hz} Hz, and above {max_hz} Hz it cannot be read completely: {n} missing. Set the polling rate to {max_hz} Hz to read it all.",
     "鼠标当前为 {hz} Hz，高于 {max_hz} Hz 时无法完整读取：缺少 {n} 个。请将回报率设为 {max_hz} Hz 以完整读取。"),
    ("Al leer el mouse solo aparecen los macros asignados a algún botón. Para ver uno guardado sin asignar, pedilo por su ID.",
     "Reading the mouse only shows macros assigned to a button. To see a stored macro that is not assigned, request it by its ID.",
     "读取鼠标时只会显示已分配给按键的宏。若要查看已保存但未分配的宏，请按 ID 请求。"),
    ("Las repeticiones solo se usan en el modo {n} ({nombre}): en los otros dos no tienen efecto.",
     "Repetitions are only used in mode {n} ({nombre}): in the other two they have no effect.",
     "重复次数仅在模式 {n}（{nombre}）中使用：在另外两种模式下无效。"),
    ("Cada paso guarda el tiempo transcurrido desde el anterior. Para probar un macro, asignalo antes a un botón: un macro sin botón se guarda, pero nunca se ejecuta.",
     "Each step stores the time elapsed since the previous one. To try a macro, assign it to a button first: a macro without a button is saved, but never runs.",
     "每个步骤记录距上一步经过的时间。要测试宏，请先将其分配给按键：没有分配按键的宏会被保存，但永远不会执行。"),
    ("este modo todavía no se probó en el mouse",
     "this mode has not been tried on the mouse yet",
     "此模式尚未在鼠标上测试"),
    ("Este modo todavía no se probó en el mouse.",
     "This mode has not been tried on the mouse yet.",
     "此模式尚未在鼠标上测试。"),
    ("un macro de {n} evento(s) no se reproduce: el mouse lo guarda, pero al apretar el botón no pasa nada. Hacen falta al menos {n_min}",
     "a macro with {n} event(s) does not play: the mouse stores it, but pressing the button does nothing. It takes at least {n_min}",
     "只有 {n} 个事件的宏不会执行：鼠标会保存它，但按下按键时没有任何反应。至少需要 {n_min} 个事件"),
    ("deja apretado lo que no suelta ({quienes}): al terminar el macro esas teclas quedan trabadas, y apretarlas no las destraba: hay que desconectar el receptor del mouse",
     "leaves held down what it does not release ({quienes}): when the macro ends those keys stay stuck, and pressing them does not free them: the mouse's receiver has to be unplugged",
     "未释放的按键会保持按下（{quienes}）：宏结束后这些按键会卡住，再次按下也无法解除：必须拔下鼠标的接收器"),
    ("{n} evento(s) esperan más de {n_ms} ms: los tiempos largos todavía no se probaron en el mouse",
     "{n} event(s) wait longer than {n_ms} ms: long delays have not been tried on the mouse yet",
     "{n} 个事件的等待超过 {n_ms} 毫秒：长延时尚未在鼠标上测试"),
    ("el mouse no contestó esta lectura: mové el mouse y volvé a leer",
     "the mouse did not answer this read: move the mouse and read again",
     "鼠标未响应本次读取：请移动鼠标后重新读取"),
    ("el mouse no tiene un macro guardado con ese ID",
     "the mouse has no macro stored with that ID",
     "鼠标中没有保存该 ID 的宏"),

    # Los botones, sus funciones con nombres que se entienden, y la regla
    # del clic izquierdo
    ("Función bloqueada",
     "Function blocked",
     "功能已阻止"),
    ("Desactivado: el botón no hace nada",
     "Disabled: the button does nothing",
     "禁用：按键不执行任何操作"),
    ("Clic izquierdo (seleccionar)",
     "Left click (select)",
     "左键单击（选择）"),
    ("Clic derecho (menú contextual)",
     "Right click (context menu)",
     "右键单击（右键菜单）"),
    ("Clic de la rueda (clic central)",
     "Wheel click (middle click)",
     "滚轮点击（中键）"),
    ("Atrás (página anterior)",
     "Back (previous page)",
     "后退（上一页）"),
    ("Adelante (página siguiente)",
     "Forward (next page)",
     "前进（下一页）"),
    ("Doble clic con un solo toque",
     "Double click with a single press",
     "按一下即双击"),
    ("Disparo rápido (clic repetido)",
     "Rapid fire (repeated click)",
     "连发（重复点击）"),
    ("Girar la rueda hacia arriba",
     "Scroll the wheel up",
     "滚轮向上滚动"),
    ("Girar la rueda hacia abajo",
     "Scroll the wheel down",
     "滚轮向下滚动"),
    ("Desplazar hacia la izquierda",
     "Scroll left",
     "向左滚动"),
    ("Desplazar hacia la derecha",
     "Scroll right",
     "向右滚动"),
    ("Pasar al siguiente nivel de DPI",
     "Switch to the next DPI level",
     "切换到下一个 DPI 档位"),
    ("Subir el DPI un nivel",
     "Raise DPI one level",
     "DPI 提高一档"),
    ("Bajar el DPI un nivel",
     "Lower DPI one level",
     "DPI 降低一档"),
    ("Puntería rápida (cambia el DPI para apuntar)",
     "Easy aim (changes DPI for aiming)",
     "狙击键（切换 DPI 便于瞄准）"),
    ("Atajo de teclado (combinación de teclas)",
     "Keyboard shortcut (key combination)",
     "键盘快捷键（组合键）"),
    ("Ejecutar un macro",
     "Run a macro",
     "执行宏"),
    ("Abrir un programa",
     "Launch a program",
     "启动程序"),
    ("Tecla Windows / Super",
     "Windows / Super key",
     "Windows / Super 键"),
    ("Abrir el reproductor multimedia",
     "Open the media player",
     "打开媒体播放器"),
    ("Canción anterior",
     "Previous song",
     "上一曲"),
    ("Canción siguiente",
     "Next song",
     "下一曲"),
    ("Reproducir o pausar",
     "Play or pause",
     "播放或暂停"),
    ("Detener la reproducción",
     "Stop playback",
     "停止播放"),
    ("Silenciar el sonido",
     "Mute the sound",
     "静音"),
    ("Subir el volumen",
     "Volume up",
     "调高音量"),
    ("Bajar el volumen",
     "Volume down",
     "调低音量"),
    ("Abrir la calculadora",
     "Open the calculator",
     "打开计算器"),
    ("Abrir el correo electrónico",
     "Open email",
     "打开电子邮件"),
    ("Abrir los favoritos del navegador",
     "Open browser favorites",
     "打开浏览器收藏夹"),
    ("Navegador: página siguiente",
     "Browser: next page",
     "浏览器：前进"),
    ("Navegador: página anterior",
     "Browser: previous page",
     "浏览器：后退"),
    ("Navegador: detener la carga",
     "Browser: stop loading",
     "浏览器：停止加载"),
    ("Abrir Mi PC (archivos)",
     "Open My Computer (files)",
     "打开我的电脑（文件）"),
    ("Navegador: recargar la página",
     "Browser: reload the page",
     "浏览器：刷新页面"),
    ("Navegador: página de inicio",
     "Browser: home page",
     "浏览器：主页"),
    ("Navegador: buscar en la web",
     "Browser: search the web",
     "浏览器：网页搜索"),
    ("Tecla Fn (funciones especiales)",
     "Fn key (special functions)",
     "Fn 键（特殊功能）"),
    ("Pasar a la siguiente tasa de reporte",
     "Switch to the next polling rate",
     "切换到下一个回报率"),
    ("Pasar al siguiente modo de luces",
     "Switch to the next lighting mode",
     "切换到下一个灯效模式"),
    ("Mostrar el nivel de batería",
     "Show the battery level",
     "显示电量"),
    ("Prender o apagar las luces",
     "Turn the lights on or off",
     "开关灯光"),
    ("Activar el macro de clic izquierdo",
     "Start the left-click macro",
     "启动左键宏"),
    ("Detener el macro de clic izquierdo",
     "Stop the left-click macro",
     "退出左键宏"),
    ("Pasar al siguiente perfil",
     "Switch to the next profile",
     "切换到下一个配置文件"),
    ("Volver al perfil anterior",
     "Go back to the previous profile",
     "返回上一个配置文件"),
    ("Ir al perfil siguiente",
     "Go to the next profile",
     "前往下一个配置文件"),
    ("Triple clic con un solo toque",
     "Triple click with a single press",
     "按一下即三连击"),
    ("Fn + 0x09: sube en 1 el valor Y",
     "Fn + 0x09: raises the Y value by 1",
     "Fn + 0x09：Y 值加 1"),
    ("Fn + 0x0a: baja en 1 el valor Y",
     "Fn + 0x0a: lowers the Y value by 1",
     "Fn + 0x0a：Y 值减 1"),
    ("Solo cambiar el modo de conexión",
     "Only switch the connection mode",
     "仅切换连接模式"),

    # Los grupos del selector de funciones, y su buscador
    ("Clics",
     "Clicks",
     "点击"),
    ("Desplazamiento",
     "Scrolling",
     "滚动"),
    ("Música y volumen",
     "Music and volume",
     "音乐和音量"),
    ("Navegador",
     "Browser",
     "浏览器"),
    ("Abrir programas",
     "Open programs",
     "打开程序"),
    ("Teclado y macros",
     "Keyboard and macros",
     "键盘和宏"),
    ("El mouse",
     "The mouse",
     "鼠标"),
    ("Otras",
     "Other",
     "其他"),
    ("Escribí para buscar…",
     "Type to search…",
     "输入以搜索…"),
    ("Nada coincide con lo que escribiste.",
     "Nothing matches what you typed.",
     "没有与输入内容匹配的项。"),
    ("Hacé clic o empezá a escribir para buscar",
     "Click or start typing to search",
     "点击或直接输入以搜索"),
    ("Botón izquierdo (principal)",
     "Left button (main)",
     "左键（主键）"),
    ("Botón derecho (secundario)",
     "Right button (secondary)",
     "右键（副键）"),
    ("Botón de la rueda (apretarla)",
     "Wheel button (press the wheel)",
     "滚轮按键（按下滚轮）"),
    ("Botón lateral trasero (pulgar)",
     "Rear side button (thumb)",
     "侧面后键（拇指）"),
    ("Botón lateral delantero (pulgar)",
     "Front side button (thumb)",
     "侧面前键（拇指）"),
    ("Botón DPI (en la base)",
     "DPI button (on the base)",
     "DPI 键（底部）"),
    ("Botón de modo (en la base)",
     "Mode button (on the base)",
     "模式键（底部）"),
    ("Sentido de giro de la rueda",
     "Wheel scroll direction",
     "滚轮滚动方向"),
    ("Normal (el sentido de siempre)",
     "Normal (the usual direction)",
     "正常（常规方向）"),
    ("Invertido (al revés)",
     "Inverted (reversed)",
     "反向（相反方向）"),
    ("Hacia dónde se desplaza la página al girar la rueda.\n\n«Normal» es el sentido de siempre; «invertido» la mueve al revés.",
     "Which way the page scrolls when you turn the wheel.\n\n«Normal» is the usual direction; «Inverted» scrolls the other way.",
     "转动滚轮时页面滚动的方向。\n\n“正常”为常规方向；“反向”则相反。"),
    ("El botón principal, con el que se hace clic y se selecciona.\n\nSe puede reasignar, siempre que otro de los botones 1 a 5 quede con el clic izquierdo: así nunca te quedás sin un clic para usar la computadora.",
     "The main button, used to click and select.\n\nIt can be reassigned, as long as another of buttons 1 to 5 keeps the left click: that way you are never left without a click to use the computer.",
     "主按键，用于点击和选择。\n\n可以重新分配，但 1 到 5 号按键中必须有另一个保留左键功能：这样你始终有一个点击可以操作电脑。"),
    ("Atajo de teclado: {atajo}",
     "Keyboard shortcut: {atajo}",
     "键盘快捷键：{atajo}"),
    ("Ejecutar el macro {n}",
     "Run macro {n}",
     "执行宏 {n}"),
    ("Ejecutar un macro sin ID (el botón no hace nada)",
     "Run a macro without an ID (the button does nothing)",
     "执行没有 ID 的宏（按键无作用）"),
    ("Código {n} sin nombre",
     "Code {n} without a name",
     "代码 {n}（无名称）"),
    ("Intercambiar los botones izquierdo y derecho",
     "Swap the left and right buttons",
     "交换左键和右键"),
    ("Intercambiar",
     "Swap",
     "交换"),
    ("Pasa lo que hace el botón 1 al botón 2, y lo del 2 al 1, en una sola escritura.\n\nSirve para usar el mouse con la mano izquierda, y para volver a dejarlo como estaba.",
     "Moves what button 1 does to button 2, and what button 2 does to button 1, in a single write.\n\nUseful for using the mouse left-handed, and for putting it back as it was.",
     "在一次写入中，把 1 号按键的功能移到 2 号按键，并把 2 号的功能移到 1 号。\n\n适合左手使用鼠标，也可以用来恢复原状。"),
    ("el clic izquierdo solo se puede poner en los botones {n_desde} a {n_hasta}, no en el {n}",
     "the left click can only go on buttons {n_desde} to {n_hasta}, not on {n}",
     "左键功能只能放在 {n_desde} 到 {n_hasta} 号按键上，不能放在 {n} 号"),
    ("el botón {n} es el único con clic izquierdo: antes de cambiarlo, poné el clic izquierdo en otro de los botones {n_desde} a {n_hasta}",
     "button {n} is the only one with the left click: before changing it, put the left click on another of buttons {n_desde} to {n_hasta}",
     "{n} 号按键是唯一的左键：更改它之前，请先把左键功能放到 {n_desde} 到 {n_hasta} 号中的另一个按键上"),
)

_INDICES, _TRADUCIDOS = _armar_indices()
