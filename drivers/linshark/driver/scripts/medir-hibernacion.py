#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Detecta cuando el mouse se duerme, sin mirarlo y sin escribirle nada.

El problema que resuelve: el X8 Pro **no hace nada visible** al hibernar. No
apaga un LED ni se desconecta del sistema, asi que "se durmio" no se puede
observar. Esta herramienta es la unica verificacion externa que consiguio el
bloque de cmd 5, y la consiguio.

La senal que usa: el mouse manda **solo, sin que nadie se lo pida, un reporte
de estado** por el nodo de configuracion (Report ID 3, con el nivel de bateria;
ver `hidraw.py`). Ese latido es trafico de radio. Si el mouse entra en reposo
profundo, tiene que parar o espaciarse.

Y es un metronomo con **dos cadencias** (MEDIDO, tres corridas):
2.00 s con el mouse recien usado, y 4.00 s a partir de ~32 s de quietud, que es
un primer escalon de ahorro anterior a la hibernacion. Las dos con ±0.01 s de
jitter, asi que una parada no se confunde con un hueco del enlace.

**Lo que esta herramienta mide es cuando para el latido.** Que eso fuera el
temporizador de hibernacion era la hipotesis, y quedo MEDIDO, con
la unidad incluida:

    corte = T_reposo_corto + N x 60 s        (N = --hibernacion, en minutos)

    N=1   predicho  90 s   medido [88.0, 92.0]
    N=10  predicho 630 s   medido [628.9, 632.9]

Dos puntos con una palanca de 10x, los dos adentro. Descarta el modelo paralelo
(predecia 600 y a los 600 el mouse seguia latiendo) y el N x 90 (predecia 900).

El termino constante son los 30 s del **otro** temporizador, el corto, que en
la medicion estaba en 0.5 min. Ese es tambien el que mueve el escalon de 2.00 s a
4.00 s. Ver `escribir_reposo_ligero()` en `estructuras.py`.

Abre el nodo **en solo lectura** (`O_RDONLY`, sostenido por el kernel) y no le
manda un solo byte al mouse. Se puede correr sin ningun permiso de escritura.

    driver/scripts/medir-hibernacion.py --minutos 5

Mientras corre **no hay que tocar el mouse**: cualquier movimiento o clic
reinicia el temporizador de reposo del propio mouse. La herramienta vigila el
nodo de eventos para darse cuenta y avisa, en vez de dar por buena una medicion
arruinada.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import evdev  # noqa: E402

from linshark.hidraw import (  # noqa: E402
    REPORT_ID_ESTADO, DONGLE_PRODUCT_ID, HidrawChannel, VENDOR_ID,
    WIRED_PRODUCT_ID, find_config_hidraw, verificar_nodo_dongle)

# MEDIDO con tres corridas: el latido tiene DOS cadencias, y las
# dos son metronomos. 2.00 s con el mouse recien usado (43 huecos, 1.99..2.26) y
# 4.00 s a partir de ~32 s de quietud (179 huecos, 4.00..4.01). Ninguna es un
# umbral de decision -el corte se calcula contra la mediana de la propia
# corrida- sino el respaldo para cuando hay pocos latidos para sacar una.
#
# El piso del umbral sale de la LENTA: una corrida de hibernacion transcurre
# casi entera en ese estado, y usar la rapida lo dejaria a la mitad.
LATIDO_EN_USO = 2.0
LATIDO_EN_REPOSO = 4.0

# El punto medio entre las dos cadencias, para partir los huecos en los dos
# grupos. Es una division de conveniencia, no un umbral fisico: si apareciera un
# tercer estado los huecos caerian mezclados, y la herramienta lo dice en vez de
# forzarlos a dos.
CORTE_ESCALON = 3.0


def buscar_evdev() -> evdev.InputDevice | None:
    """El nodo de eventos del mouse, para saber si alguien lo toco.

    Es el mismo que usa `medir-polling.py`. El movimiento **no pasa por el nodo
    de configuracion**, asi que sin esto la herramienta no tendria forma de
    darse cuenta de que la medicion se arruino.
    """
    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
        except OSError:
            continue
        if dev.info.vendor != VENDOR_ID or \
           dev.info.product not in (DONGLE_PRODUCT_ID, WIRED_PRODUCT_ID):
            dev.close()
            continue
        caps = dev.capabilities()
        if evdev.ecodes.EV_REL in caps and \
           evdev.ecodes.REL_X in caps[evdev.ecodes.EV_REL]:
            return dev
        dev.close()
    return None


class Medicion:
    def __init__(self):
        self.t0 = time.monotonic()
        self.latidos: list[float] = []      # t de cada Report ID 3
        self.otros: list[tuple[float, int]] = []
        self.actividad: list[float] = []    # t de cada movimiento/clic
        # El payload ENTERO, no solo la bateria: el reporte es
        # [3, deviceId, marca, estadoBateria, nivelBateria] y cualquiera de
        # esos bytes podria ser el que marca el reposo. Si el latido no para
        # pero uno de ellos cambia, el detector es ese cambio.
        self.payloads: list[tuple[float, bytes]] = []
        self.ultimo_aviso = 0.0
        self.aviso_escalon = False

    @property
    def t(self) -> float:
        return time.monotonic() - self.t0

    def alimentar_hidraw(self, data: bytes) -> None:
        t = self.t
        if data and data[0] == REPORT_ID_ESTADO:
            self.latidos.append(t)
            self.payloads.append((t, bytes(data[:5])))
            hueco = (t - self.latidos[-2]) if len(self.latidos) > 1 else 0.0
            # El escalon 2 s -> 4 s es normal y pasa una vez por corrida: se
            # avisa una vez. Antes se avisaba en CADA latido lento, o sea
            # ochenta lineas por corrida diciendo lo mismo, y el aviso que
            # importa -un hueco mas largo que la cadencia lenta- quedaba
            # enterrado entre ellas.
            if hueco > CORTE_ESCALON and not self.aviso_escalon:
                self.aviso_escalon = True
                print(f"  [{t:7.1f}s] el latido paso a {hueco:.1f}s: primer "
                      f"escalon de ahorro (MEDIDO: ~32s de quietud)")
            elif hueco > LATIDO_EN_REPOSO * 2:
                print(f"  [{t:7.1f}s] latido despues de {hueco:.1f}s de "
                      f"silencio")
        elif data:
            self.otros.append((t, data[0]))

    def alimentar_evdev(self, dev: evdev.InputDevice) -> None:
        try:
            for _ev in dev.read():
                pass
        except (BlockingIOError, OSError):
            return
        t = self.t
        # Un aviso cada 15 s como mucho: usar el mouse un minuto genera miles
        # de eventos, y una linea por rafaga llena la pantalla con lo mismo.
        if t - self.ultimo_aviso > 15.0:
            print(f"  [{t:7.1f}s] SE ESTA USANDO EL MOUSE: el temporizador de "
                  f"reposo vuelve a cero.")
            print("             Esta corrida no va a medir nada hasta que lo "
                  "dejes quieto.")
            self.ultimo_aviso = t
        self.actividad.append(t)


def ventana_quieta(m: Medicion, total: float) -> tuple[float, float]:
    """El tramo mas largo sin que nadie tocara el mouse.

    No alcanza con mirar desde la ultima actividad hasta el final: si el mouse
    se uso al final de una corrida larga, ahi no queda nada, pero el tramo
    quieto del medio puede ser justo el que tiene la respuesta. El temporizador
    del mouse se reinicia con cada movimiento, asi que cada tramo entre dos
    actividades es un experimento independiente y vale el mas largo.
    """
    bordes = [0.0] + m.actividad + [total]
    mejor = (0.0, 0.0)
    for a, b in zip(bordes, bordes[1:]):
        if b - a > mejor[1] - mejor[0]:
            mejor = (a, b)
    return mejor


def _payloads(m: Medicion) -> None:
    """Los contenidos distintos del latido, y cuando aparecio cada uno.

    Esto es lo que convierte un "el latido no paro" en un resultado util en vez
    de un callejon: si algun byte del reporte cambia al entrar en reposo, el
    detector es ese cambio y no la ausencia del latido.
    """
    if not m.payloads:
        return
    vistos: dict[bytes, list[float]] = {}
    for t, pl in m.payloads:
        vistos.setdefault(pl, []).append(t)
    print(f"\n  payloads distintos del latido: {len(vistos)}")
    for pl, ts in sorted(vistos.items(), key=lambda kv: kv[1][0]):
        print(f"    {pl.hex(' ')}  x{len(ts):<4} de {ts[0]:.0f}s a {ts[-1]:.0f}s")
    if len(vistos) > 1:
        print("    OJO: el contenido del latido CAMBIO durante la corrida.")
        print("    Si el cambio cae donde se esperaba el reposo, ese es el "
              "detector que faltaba.")
    ultimo = m.payloads[-1][1]
    if len(ultimo) >= 5:
        print(f"  bateria al final: {ultimo[4]}% (hace falta >= 50 para "
              "escribir)")


def _cadencias(huecos: list[float], latidos: list[float], ini: float,
               mediana: float) -> float | None:
    """Parte los huecos en los dos estados del latido y ubica el escalon.

    El mouse baja de 2.00 s a 4.00 s a los ~32 s de quietud (MEDIDO).
    Informar una sola mediana mezcla los dos y no dice nada de
    ninguno: en una corrida larga la mediana da 4.00 y el estado rapido
    desaparece del informe. Devuelve el t del escalon dentro del tramo quieto,
    o None si no hubo escalon o si los dos grupos vinieron mezclados.
    """
    rapidos = [g for g in huecos if g <= CORTE_ESCALON]
    lentos = [g for g in huecos if g > CORTE_ESCALON]
    print(f"  cadencia mediana del tramo: {mediana:.2f}s")
    for nombre, grupo, ref in (("recien usado", rapidos, LATIDO_EN_USO),
                               ("en reposo   ", lentos, LATIDO_EN_REPOSO)):
        if grupo:
            g = sorted(grupo)
            print(f"    {nombre}: {len(g):3d} huecos, mediana "
                  f"{g[len(g) // 2]:.2f}s, rango {min(g):.2f}..{max(g):.2f}s "
                  f"(MEDIDO: {ref:.2f}s)")
    if not (rapidos and lentos):
        return None
    i = next(k for k, g in enumerate(huecos) if g > CORTE_ESCALON)
    if any(g <= CORTE_ESCALON for g in huecos[i:]):
        print("    OJO: los dos grupos vienen MEZCLADOS, no uno despues del "
              "otro.")
        print("    El modelo de dos estados no alcanza para esta corrida; "
              "mirar los huecos.")
        return None
    escalon = latidos[i] - ini
    print(f"    el escalon esta a los {escalon:.0f}s de quietud "
          f"(MEDIDO: ~32s)")
    return escalon


def informar(m: Medicion, minutos: float) -> dict:
    total = m.t
    print()
    print("=" * 70)
    ini, fin_v = ventana_quieta(m, total)
    largo = fin_v - ini
    print(f"corrida de {total:.0f}s. Tramo quieto mas largo: {largo:.0f}s "
          f"(de {ini:.0f}s a {fin_v:.0f}s)")
    if m.actividad:
        print(f"  se uso el mouse {len(m.actividad)} veces; cada vez el "
              "temporizador del mouse vuelve a cero,")
        print("  asi que solo vale el tramo de arriba.")
        print(f"  el ultimo toque fue en {max(m.actividad):.1f}s, asi que la "
              "quietud esta anclada:")
        print("  los tiempos de abajo son quietud real.")
    else:
        # Sin un toque adentro de la corrida no se sabe cuando empezo la
        # quietud: el mouse pudo llevar rato quieto antes de arrancar. Los
        # tiempos siguen siendo utiles -son un piso- pero no se pueden comparar
        # contra los de una corrida anclada como si fueran la misma medida.
        print("  no se toco el mouse en toda la corrida, asi que el tramo "
              "arranca en el inicio")
        print("  de la corrida y no en el ultimo toque: los tiempos de abajo "
              "son un PISO de la")
        print("  quietud real, no la quietud real. Para anclarla, mover el "
              "mouse al arrancar.")
    if largo < 90:
        print(f"\n  ese tramo es corto para probar una hibernacion. Hace falta "
              f"dejarlo quieto")
        print("  bastante mas que el valor que se quiere comprobar.")

    _payloads(m)

    latidos = [t for t in m.latidos if ini <= t <= fin_v]
    print(f"\nlatidos (Report ID 3) en el tramo quieto: {len(latidos)}")
    if len(latidos) < 3:
        print("  muy pocos para decir nada. O el tramo quieto es corto, o el "
              "mouse ya estaba")
        print("  dormido, o el dongle no esta.")
        return _resumen(m, total, None, None, largo, None)

    huecos = [b - a for a, b in zip(latidos, latidos[1:])]
    huecos_ord = sorted(huecos)
    mediana = huecos_ord[len(huecos_ord) // 2]
    escalon = _cadencias(huecos, latidos, ini, mediana)
    print(f"  hueco maximo:     {max(huecos):.1f}s")

    # El corte: cuanto silencio quedo entre el ultimo latido del tramo y el
    # final del tramo. Se compara contra la cadencia de la propia corrida, no
    # contra una constante: si el enlace estuviera lento, la mediana lo refleja.
    # El piso es la cadencia LENTA, que es el estado en el que transcurre casi
    # toda una corrida de hibernacion.
    silencio = fin_v - latidos[-1]
    lentos = [g for g in huecos if g > CORTE_ESCALON]
    cadencia_previa = max(lentos) if lentos else mediana
    umbral = max(mediana, LATIDO_EN_REPOSO) * 5
    paro_en = None
    if silencio > umbral:
        paro_en = latidos[-1] - ini
        # El ultimo latido no es el instante en que paro: el corte cae en algun
        # punto del hueco que venia despues. Con 4 s de cadencia eso son 4 s de
        # incertidumbre, y decir "88s" a secas los esconde.
        print(f"\n  EL LATIDO PARO. Ultimo latido a los {paro_en:.0f}s de "
              f"quietud;")
        print(f"  con la cadencia de {cadencia_previa:.1f}s que traia, el corte "
              f"cae entre {paro_en:.0f}s y {paro_en + cadencia_previa:.0f}s "
              f"({paro_en / 60:.1f} min).")
        print(f"  Despues, {silencio:.0f}s de silencio.")
        print("\n  Eso es lo que la herramienta MIDE. Que sea la hibernacion "
              "es la hipotesis, y")
        print("  se confirma repitiendo con otro valor: el corte tiene que "
              "moverse con el.")
    else:
        print(f"\n  El latido NO paro: llego hasta el final del tramo "
              f"({silencio:.0f}s de silencio,")
        print(f"  menos que el umbral de {umbral:.0f}s).")
        print(f"  O el mouse no se durmio en {largo / 60:.1f} min de quietud, "
              "o el latido sigue")
        print("  durante el reposo. Si algun payload de arriba cambio, ese es "
              "el detector;")
        print("  si no, hay que ir al plan B (usbmon). Ver la bitacora, "
              "\"Un instrumento para lo que no se ve\".")

    if m.otros:
        ids = sorted({rid for _t, rid in m.otros})
        print(f"\n  otros reportes en el nodo: IDs {ids}")
    return _resumen(m, total, mediana, paro_en, largo, escalon,
                    cadencia_previa if paro_en is not None else None)


def _resumen(m: Medicion, total: float, mediana, paro_en,
             tramo_quieto: float, escalon, cadencia_previa=None) -> dict:
    # `latido_paro_a_los_s` es el ULTIMO LATIDO, no el instante del corte: el
    # corte cae en el hueco siguiente. `corte_entre_s` lo dice completo, que es
    # la unica forma honesta de compararlo despues contra un valor escrito.
    corte = ([round(paro_en, 1), round(paro_en + (cadencia_previa or 0), 1)]
             if paro_en is not None else None)
    return {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "duracion_s": round(total, 1),
        "latidos": len(m.latidos),
        "cadencia_mediana_s": round(mediana, 2) if mediana else None,
        "escalon_a_los_s": round(escalon, 1) if escalon is not None else None,
        "tramo_quieto_s": round(tramo_quieto, 1),
        "veces_que_se_toco": len(m.actividad),
        "latido_paro_a_los_s": round(paro_en, 1) if paro_en else None,
        "corte_entre_s": corte,
        "payloads": sorted({pl.hex() for _t, pl in m.payloads}),
        "bateria": (m.payloads[-1][1][4]
                    if m.payloads and len(m.payloads[-1][1]) >= 5 else None),
    }


async def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--minutos", type=float, default=5.0,
                    help="cuanto escuchar (por defecto %(default)s). Conviene "
                         "al menos el doble del tiempo de hibernacion que se "
                         "quiere comprobar")
    ap.add_argument("--hidraw", type=Path)
    ap.add_argument("--nota", default="",
                    help="que hibernacion tenia el mouse en esta corrida, para "
                         "que el archivo sirva despues")
    ap.add_argument("--sin-guardar", action="store_true")
    args = ap.parse_args()

    path = args.hidraw
    if path is not None:
        verificar_nodo_dongle(path)
    else:
        path = find_config_hidraw()

    # O_RDONLY: la garantia la sostiene el kernel, no un `if`.
    canal = HidrawChannel(path, solo_lectura=True)
    canal.open()
    m = Medicion()
    loop = asyncio.get_running_loop()
    canal.start_reading(loop, m.alimentar_hidraw)

    ev = buscar_evdev()
    if ev is not None:
        loop.add_reader(ev.fd, m.alimentar_evdev, ev)
        vigilancia = f"y vigilando {ev.path} por si se toca"
    else:
        vigilancia = ("SIN vigilancia de movimiento: no encontre el nodo de "
                      "eventos, asi que\n      no me voy a dar cuenta si "
                      "alguien lo toca")

    print(f"escuchando {path} en solo lectura {vigilancia}")
    cuanto = (f"{args.minutos:.0f} minutos" if args.minutos >= 1
              else f"{args.minutos * 60:.0f} segundos")
    print(f"NO TOQUES EL MOUSE durante {cuanto}. Ctrl-C corta y resume igual.\n")

    try:
        fin = time.monotonic() + args.minutos * 60
        while time.monotonic() < fin:
            await asyncio.sleep(15)
            t = m.t
            ultimo = m.latidos[-1] if m.latidos else None
            silencio = (t - ultimo) if ultimo is not None else t
            print(f"  [{t:7.1f}s] {len(m.latidos)} latidos, "
                  f"{silencio:.0f}s desde el ultimo")
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n  cortado a mano")
    finally:
        if ev is not None:
            loop.remove_reader(ev.fd)
            ev.close()
        canal.close()

    resumen = informar(m, args.minutos)
    if not args.sin_guardar:
        carpeta = Path(__file__).resolve().parent.parent / "mediciones"
        carpeta.mkdir(exist_ok=True)
        sello = datetime.now().strftime("%Y%m%dT%H%M%S")
        destino = carpeta / f"hibernacion-{sello}.json"
        resumen["nota"] = args.nota
        resumen["latidos_t"] = [round(t, 2) for t in m.latidos]
        resumen["actividad_t"] = [round(t, 2) for t in m.actividad]
        destino.write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
        print(f"\nguardado en {destino.relative_to(carpeta.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
