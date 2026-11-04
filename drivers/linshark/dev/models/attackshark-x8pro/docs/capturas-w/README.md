# Capturas del driver oficial

Todas son tramas MEDIDAS del bus USB. **Proceden de dos máquinas distintas y, como
se descubrió después, de dos dispositivos distintos**; la tabla que los separa
está en [`../evidencia.md`](../evidencia.md), sección 5. Al utilizar una captura
hay que comprobar a qué lote pertenece: **el *framing* es válido en ambos; los
valores, solo en el lote 2.**

## Trazas del puente (WebSocket, no USB)

| Archivo | Contenido |
| :--- | :--- |
| `web-rate-2000-a-1000.jsonl` | **La plataforma oficial reduciendo la tasa a través del puente.** Tres sesiones concatenadas —cada una comienza con `0305`—; la tercera es la que funcionó: ocho escrituras de tasa con valores diversos en 40 s, y el dispositivo quedó a 1000 Hz (medido con `medir-polling.py`). Es la única evidencia de un cambio de tasa **desde por encima de 1000 Hz** realizado desde Linux. Ver `../bitacora.md` |

Es tráfico del WebSocket entre plataforma y puente, no del bus USB: sirve para
determinar qué solicitó la plataforma y en qué orden, no para contrastar tramas.

## Lote 1 — AUT01, equipo físico con Windows

Capturado con USBPcap desde el propio Windows. El análisis de la época quedó en
[`reporteW.md`](reporteW.md) y [`reporteWsoft.md`](reporteWsoft.md), que se
conservan **como artefactos del lote y no se actualizan**: lo vigente está en
[`../protocolo.md`](../protocolo.md) y [`../evidencia.md`](../evidencia.md).

**La captura original del navegador (`w1.har`) y el zip del lote no se
publican.** El HAR, guardado «with content», traía también el bundle, el CSS y
las imágenes del sitio del fabricante, y de ese material el proyecto guarda
huellas, no archivos. Lo que se usa de él son las 85 tramas del WebSocket, que
están en `w1-from-har.jsonl`. Los informes del lote lo siguen nombrando porque
no se actualizan.

| Archivo | Contenido |
| :--- | :--- |
| `w1-from-har.jsonl` | WebSocket del servicio auxiliar (WebDriver), 85 tramas |
| `w2-rate.pcap` / `w2-dpi.pcap` | USB Interrupt OUT, plataforma web |
| `w2soft-rate.pcap` / `w2soft-dpi.pcap` | USB Interrupt OUT, software nativo |
| `*-outs.txt` / `W*-RESULTADO*.txt` | Extracciones con tshark y resúmenes |
| `reporteW.md` / `reporteWsoft.md` | Los informes de la Etapa W, tal como se emitieron. No se actualizan |

Origen: `<descargas>\` (AUT01).

**Este dispositivo no es el del proyecto.** Su bloque de versión es
`08 00 83 01 05 00`; el del proyecto, `08 00 83 01 01 00`. Sirve para el
*framing* —confirmado por separado contra el dispositivo propio—, pero un valor
de este lote no representa el estado del dispositivo del proyecto.

## Lote 2 — VM de Windows, dongle por *passthrough*

Capturado desde el **anfitrión Linux con usbmon**, con Windows dentro de la VM y
el dongle asignado por USB. Procedimiento en
[`../captura-kvm.md`](../captura-kvm.md). Como el dongle es el mismo que utiliza
Linux, **este lote observa el dispositivo del proyecto**.

| Archivo | Contenido |
| :--- | :--- |
| `web-arranque-dpi-y-rate.pcap` | Web: arranque, más cuatro escrituras |
| `web-tanda-parametros.pcap` | Web: corrección de ángulo, sincronización de movimiento y control de fluctuación |
| `web-todo.pcap` | Web: tanda completa, incluida la restauración de fábrica |
| `soft-todo.pcap` | Software nativo: 46 escrituras, 46 idénticas al constructor |
| `soft-rates-anotados.pcap` | Software nativo: las siete tasas de sondeo, una por una |
| `soft-rate-8000-a-1000.pcap` | Software nativo: 8000 → 1000 Hz, cinco OUT a partir de un único control |
| `*.txt` | La nota de cada captura: qué se accionó, con qué valor y en qué máquina |

Cada `.pcap` lleva su `.txt` adjunto. Sin esa nota, una captura consultada un mes
después resulta ininterpretable; y cuando la nota se pierde, manda el contenido:
ver `soft-rate-8000-a-1000.txt`, donde el valor se reconstruyó a partir de los
datos.

## Cómo leerlas

```bash
dev/herramientas/leer-captura-usb.py dev/models/attackshark-x8pro/docs/capturas-w/soft-todo.pcap
```

Por cada Interrupt OUT muestra la trama, valida el checksum, la interpreta y la
compara contra lo que compondría `build_write_frame()`. `IDENTICO` es el criterio
de la Etapa 2 de [`dev/docs/metodo.md`](../../../../docs/metodo.md).
