#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2026 Juan Serafini
"""Cambia SOLO la tasa de reporte, sin exigir el respaldo de los siete bloques.

Existe por un problema medido: **arriba de 1000 Hz el respaldo completo no
sale**, y el paso 1 de `primera-escritura.py` lo exige antes de escribir nada.
Con el mouse a 2000 Hz o más eso deja la tasa sin camino de vuelta desde Linux
—hay que ir a la VM con el driver oficial, que de paso pisa el dpi—.

    driver/scripts/cambiar-rate.py --valor 1000     # el caso que desatasca
    driver/scripts/cambiar-rate.py --valor 8000
    driver/scripts/cambiar-rate.py                  # solo mira, no escribe

**Por qué se puede hacer sin el respaldo completo, y por qué es angosto.**

  * la lectura de cmd 6 son 7 bytes y **funciona a cualquier tasa** (tres
    corridas a 8 kHz, y la de 2 kHz);
  * la escritura de cmd 6 también: el driver oficial bajó la tasa con el mouse
    a 7825 Hz (`soft-rate-8000-a-1000.pcap`) y en su barrida la cambió **desde
    2000 Hz** (`soft-rates-anotados.pcap`), con la trama byte a byte igual a la
    que arma esto;
  * así que el campo que se toca **sí tiene respaldo**: se lee justo antes, se
    guarda en `~/.local/state/linshark/respaldos/` y se imprime. Lo que no se puede tomar es el de los
    otros seis bloques, que es exactamente lo que este comando viene a
    arreglar.

**El acuse no alcanza**: el `0xC1` dice que el **dongle** aceptó la trama, no
que el mouse la haya aplicado. Una vez acusó veinte tramas que el
firmware descartaba —iban empaquetadas dos veces, ver la baranda de
`protocol.build_write_frame()`— sin protestar una sola vez. Lo único que
contesta esa pregunta es la relectura, y por eso esto relee al final.

`--intentos` manda la trama varias veces con la pausa del driver oficial
(1.01 s) antes de verificar. Con el bug arreglado **una sola vez debería
alcanzar**; los reintentos quedan porque el enlace pierde pedidos de verdad.

Lo que **no** afloja: sigue siendo un solo comando (cmd 6), solo los siete
valores que el driver oficial escribió, confirmación por terminal antes de
mandar, verificación del nodo, y relectura. Para cualquier otro campo se usa
`primera-escritura.py`, que toma el respaldo completo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from linshark import estructuras as est             # noqa: E402
from linshark import lugares                        # noqa: E402
from linshark import protocol as p                  # noqa: E402
from linshark.device import Device                  # noqa: E402
from linshark.hidraw import (DeviceNotFound,        # noqa: E402
                             HidrawChannel,
                             find_config_hidraw, verificar_nodo_dongle)


def describir(datos: bytes) -> str:
    hz = est.report_rate_de(datos)
    if hz is None:
        return (f"byte {datos[1]:#04x}, que no es ninguno de los siete "
                "observados")
    return f"{hz} Hz (byte {datos[1]:#04x})"


async def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--valor", type=int, metavar="HZ",
                    help="la tasa nueva. Sin esto solo lee y muestra")
    ap.add_argument("--hidraw", type=Path,
                    help="por defecto se busca en sysfs")
    ap.add_argument("--intentos", type=int, default=4, metavar="N",
                    help="cuantas veces mandar la trama si el mouse no la "
                         "aplica, con la pausa del driver oficial entre una y "
                         "otra (por defecto 4). El dongle acusa 0xC1 aunque el "
                         "mouse no aplique nada, asi que lo que decide es la "
                         "relectura")
    args = ap.parse_args()

    if args.valor is not None and args.valor not in p.RATE_INDICE:
        print(f"{args.valor} Hz no existe. Los que hay: "
              + ", ".join(str(h) for h in sorted(p.RATE_INDICE)),
              file=sys.stderr)
        return 2

    # Un nodo que no existe, o que no es el dongle, es un error de uso: sale
    # con su mensaje y no con un traceback. Es la misma familia que H-04 de la
    # auditoria del agente A, que era sobre el CLI del puente.
    try:
        path = args.hidraw
        if path is not None:
            verificar_nodo_dongle(path)
        else:
            path = find_config_hidraw()
    except (DeviceNotFound, OSError, ValueError) as exc:
        print(f"{exc}", file=sys.stderr)
        return 1

    canal = HidrawChannel(path)
    canal.open()
    device = Device(canal)
    canal.start_reading(asyncio.get_running_loop(), device.alimentar)

    try:
        print(f"[1/4] leyendo la tasa actual de {path} (mové el mouse)")
        frame = await device.leer(p.CMD_REPORT_RATE)
        if frame is None:
            print("\n      el mouse no contestó ni el bloque corto de rate. "
                  "Eso no es la tasa:\n"
                  "      revisá que el dongle esté conectado y que el mouse "
                  "esté despierto.", file=sys.stderr)
            return 1
        leido = bytes(frame.data)
        print(f"      ahora: {describir(leido)}")

        # El respaldo del campo que se toca, que es el que esta funcion puede
        # garantizar. Se guarda aunque no se escriba nada.
        carpeta = lugares.respaldos()
        carpeta.mkdir(parents=True, exist_ok=True)
        sello = datetime.now().strftime("%Y%m%dT%H%M%S")
        archivo = carpeta / f"rate-{sello}.json"
        archivo.write_text(json.dumps({
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "nodo": str(path),
            "comandos": {str(p.CMD_REPORT_RATE): {
                "nombre": "report rate",
                "sizeTotalData": frame.sub,
                "datos": leido.hex(),
                "checksum_ok": frame.checksum_ok,
            }},
            "nota": "solo cmd 6: lo tomo driver/scripts/cambiar-rate.py",
        }, indent=2, ensure_ascii=False))
        print(f"      guardado en {archivo.relative_to(carpeta.parent)}")

        if args.valor is None:
            print("\n      sin --valor no se escribe nada.")
            return 0

        bloque = est.escribir_report_rate(leido, hz=args.valor)
        if bloque == leido:
            print(f"\n[2/4] ya está en {args.valor} Hz: no hay nada que "
                  "escribir.")
            return 0

        # **`device.escribir()` espera el BLOQUE, no la trama.** El Report ID,
        # el largo, el opcode y el checksum se los pone el, llamando a
        # `build_write_frame()`. Pasarle la trama ya armada fue el bug del
        # doble empaquetado: ver la baranda en `protocol.build_write_frame()`.
        bloque_con_cmd = bytes([p.CMD_REPORT_RATE, frame.sub]) + bloque
        trama = p.build_write_frame(bloque_con_cmd)   # solo para mostrarla
        print(f"\n[2/4] cambio: {describir(leido)} -> {describir(bloque)}")
        print(f"      {trama.hex(' ')}")
        if not est.rate_byte_en_el_bus(bloque[1]):
            print(f"\n      OJO: el byte que sale es {bloque[1]:#04x}, y "
                  "ninguna captura del driver oficial\n"
                  "      lo muestra. Pasa porque el nibble bajo del bloque "
                  f"vale {bloque[1] & 0x0F} y se respeta.")

        if not sys.stdin.isatty():
            print("\n      hace falta una terminal para confirmar",
                  file=sys.stderr)
            return 1
        if input("[3/4] escribir esto al mouse? [escribir/no]: ") != "escribir":
            print("      no se escribió nada.")
            return 0

        # **El acuse no alcanza, y esto quedo MEDIDO**: con el
        # mouse a 2000 Hz el dongle contesto `0xC1` dos veces seguidas y la
        # tasa no se movio ni una. Lo unico que decide es la relectura.
        #
        # Y el driver oficial no manda la trama una sola vez: manda una por
        # segundo (1.01 s MEDIDO, la misma cadencia que usa para los macros).
        # En su barrida cambio la tasa **desde 2000 Hz** sin problema, con la
        # trama byte a byte identica a esta, asi que lo que falta de nuestro
        # lado no es el contenido: es la insistencia.
        #
        # **Y conviene NO mover el mouse mientras escribe.** Mover es la regla
        # para leer -el enlace pierde la mitad de los pedidos con el mouse
        # quieto a 1000 Hz- pero arriba de esa tasa el trafico de movimiento es
        # justo lo que tapa el canal, y el mouse no manda nada cuando esta
        # quieto (MEDIDO).
        # **El driver oficial NO lee nunca**: 62 escrituras en sus tres
        # capturas de rate, cero lecturas (MEDIDO). Manda sus
        # tramas seguidas, una por segundo, y verifica contra su propia base
        # de datos. Nosotros intercalabamos una lectura entre intento e
        # intento, que es justo lo que el canal disputado no aguanta: cada
        # respuesta larga deja al dongle ocupado.
        #
        # Asi que la tanda va sin leer nada en el medio, igual que el soft, y
        # la verificacion queda para el final.
        # **Una trama, y recien si no entro se reintenta.** Cada escritura de
        # rate que llega de verdad reconfigura la radio del mouse, asi que
        # mandar varias seguidas no es insistir: es cambiarle la tasa varias
        # veces. La pagina oficial mando una vez seis en tres segundos
        # -por clics encolados- y el mouse dejo de mover el puntero hasta que
        # se lo saco del modo dongle.
        #
        # El bucle existe porque el enlace pierde pedidos de verdad (95% de
        # exito con el mouse en movimiento, 50% quieto), no porque haga falta
        # repetir lo que ya se aplico. Por eso relee entre intento e intento y
        # corta apenas entra.
        n = max(1, args.intentos)
        print(f"\n[4/4] escribiendo y verificando (hasta {n} intentos, "
              "releyendo entre uno y otro).\n"
              "      Cada trama que entra reconfigura la radio: no se manda "
              "una de mas.")
        quedo = None
        for intento in range(1, n + 1):
            acuse = "0xC1" if await device.escribir(bloque_con_cmd) else "sin acuse"
            await asyncio.sleep(p.WRITE_BLOCK_PAUSE_SOFT)
            despues = await device.leer(p.CMD_REPORT_RATE)
            if despues is None:
                print(f"      intento {intento}/{n}: {acuse}, y la relectura "
                      "no contestó")
                continue
            quedo = bytes(despues.data)
            print(f"      intento {intento}/{n}: {acuse}, quedó en "
                  f"{describir(quedo)}")
            if quedo == bloque:
                break
        if quedo is None:
            print("\n      no se pudo releer. Corré este mismo comando sin "
                  "--valor para ver cómo quedó.", file=sys.stderr)
            return 1
        if quedo != bloque:
            print(f"\n      El mouse NO aplicó el cambio en {n} intentos, "
                  "aunque el dongle acusara.\n"
                  "      Verificalo por un camino que no usa el canal de "
                  "configuración:\n"
                  "        driver/scripts/medir-polling.py --segundos 10\n"
                  "      Si ahí también sigue en la tasa vieja, comparó "
                  "la trama de arriba con\n"
                  "      la que mandó la corrida que SÍ funcionó: una vez "
                  "el problema fue\n"
                  "      justamente ese -la trama iba empaquetada dos veces-, "
                  "y cuatro horas de\n"
                  "      hipótesis sobre la radio no lo encontraron.\n"
                  f"      El valor previo está en {archivo.name}",
                  file=sys.stderr)
            return 1
        print("\n      Verificalo por fuera del protocolo, que no depende de "
              "creerle al mouse:\n"
              "        driver/scripts/medir-polling.py --segundos 10")
        if args.valor > 1000:
            print("\n      Y tené presente que **arriba de 1000 Hz el "
                  "respaldo completo no sale**\n"
                  "      (medido a 2000 y a 8000): para configurar cualquier "
                  "otra cosa hay que\n"
                  "      volver a 1000 con este mismo comando.")
        return 0
    except KeyboardInterrupt:
        print("\n      cortado a mano. No se escribió nada nuevo.",
              file=sys.stderr)
        return 130
    finally:
        canal.close()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(130)
