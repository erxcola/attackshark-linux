# El hardware, visto desde Linux

Volcado en un VivoBook con CachyOS (kernel 7.1.8), con el dispositivo conectado
por cable y el dongle presente al mismo tiempo.

## Los dos dispositivos USB

El X8 Pro se presenta como dos dispositivos distintos según el camino de
conexión. No comparten identificadores ni descriptores.

| | Dongle 2.4 GHz | Cable |
| :--- | :--- | :--- |
| ID USB | `1d57:fa65` | `1d57:2126` |
| Nombre USB | `2.4G 8K HS Receiver` | `X8PRO Mouse` |
| Nombre HID | `LXDDZ 2.4G 8K HS Receiver` | `Beken X8PRO Mouse` |
| `bcdUSB` | 2.00, High Speed 480 Mbps | 1.10, Full Speed |
| `bInterval` del EP de mouse | 1 microtrama = **125 µs** | 1 ms |
| Tasa máxima real | **8000 Hz** | **1000 Hz** |

Conclusión práctica: **los 8 kHz solo se obtienen por el dongle.** Por cable el
descriptor no admite más de 1000 Hz; no es una limitación de Linux.

Y una advertencia que costó una noche: **esos 8 kHz tienen un precio.** A esa
tasa el canal de configuración —la interfaz 2, descrita más abajo— compite con
ocho veces más tráfico de movimiento por el mismo enlace de radio, y el dongle
comienza a responder `0xC3` (ocupado). Medido con tres corridas de
`driver/scripts/respaldar.py`: 3, 5 y 3 de los siete comandos. No se corrige con
reintentos. Peor aún: una lectura que insiste contra el dongle ocupado puede
dejar el dispositivo **sin responder durante unos segundos**, porque sus reportes
de movimiento salen por ese mismo dongle. Ver `bitacora.md`.

**Pero lo que falla es una parte, no el conjunto**, y la diferencia se midió
después. Este párrafo afirmaba «no se puede ni leer ni configurar desde Linux»,
que resultó ser más de lo que estaba medido:

| A 8 kHz | Resultado |
| :--- | :--- |
| lecturas **cortas** (versión, tasa, iluminación) | **funcionan** — 3 de 3 corridas |
| lecturas **largas** (DPI, botones, macro, perfil) | fallan: el respaldo completo no llega a obtenerse |
| **escrituras** | **funcionan** — el driver oficial redujo la tasa con el dispositivo a 7825 Hz y recibió `0xC0` más `0xC1` (`capturas-w/soft-rate-8000-a-1000.pcap`) |

La frontera está **MEDIDA y es 1000 Hz**: a 2000 Hz el respaldo completo ya no se
obtiene. De modo que configurar a 8 kHz sí es posible, reduciendo la tasa un
instante y restituyéndola: `driver/scripts/primera-escritura.py` lo hace por sí
solo —reduce a 1000, toma el respaldo completo que el paso 1 exige, escribe,
relee y restituye la tasa en el `finally`— y `driver/scripts/cambiar-rate.py`
modifica la tasa en ambas direcciones sin necesitar ese respaldo. Ver
`SIGUIENTE-SESION.md`, «8 kHz en Linux».

`1d57` figura en la base de datos de identificadores USB como «Xenta»; el
fabricante real es Guangzhou Junxingcheng Electronic Technology, según el campo
`CompanyName` del instalador oficial. «Beken» y «LXDDZ» son el SoC y el ODM.

**El modelo de sensor no está verificado.** La documentación comercial del
producto anuncia un PAW3395 (INFERIDO: procede del material de marketing, no de
una lectura del silicio ni de un registro del firmware). Lo único LEÍDO al
respecto es que el *bundle* del fabricante trata el DPI de este modelo con la
tabla del **3311**: `getSensorType()` mapea `X8Pro: "3311"` y `parseDpiSettings()`
invoca `convertBytesToDpi3311()`. Las dos afirmaciones pueden coexistir —una es
el sensor físico y la otra la tabla que la plataforma aplica—, pero ninguna
autoriza a deducir cuál es el DPI real del sensor, que sigue sin conocerse.

## Interfaces HID

Ambos dispositivos exponen 4 interfaces. La relevante es la **interfaz 2**, que
es por donde se configura. Las otras tres son teclado, mouse y multimedia.

Los números de `/dev/hidrawN` que aparecen a continuación son los de **esa
sesión**: cambian cada vez que se conecta o desconecta algo. El código nunca los
emplea de forma fija, los localiza recorriendo sysfs (`find_config_hidraw()`).

### Dongle (`1d57:fa65`), interfaz 2 → `/dev/hidraw5`

Dos *endpoints* de 64 bytes (IN `0x83`, OUT `0x03`). El descriptor declara tres
colecciones de nivel superior; la tercera es el canal de configuración:

```
0x06 0x01 0xFF   Usage Page (vendor 0xFF01)
0x09 0x02        Usage (0x02)
0xA1 0x01        Collection (Application)
0x85 0x04          Report ID (4)
0x75 0x08          Report Size (8)
0x95 0x3F          Report Count (63)
0x15 0x00 0x26 0xFF 0x00   Logical Min/Max 0..255
0x09 0x09          Usage (0x09)
0x81 0x02          Input  (Data,Var,Abs)   <- respuestas del dispositivo
0x85 0x04          Report ID (4)
0x09 0x3C          Usage (0x3C)
0x75 0x08 0x95 0x3F
0x91 0x02          Output (Data,Var,Abs)   <- comandos al dispositivo
0xC0             End Collection
```

Es decir: **Report ID 4, 63 bytes de datos, en ambos sentidos.**

El **Report ID 3** (colección vendor 0xFF00, 4 bytes de entrada), que es el canal
de notificaciones, está MEDIDO **por captura de tráfico**, no por volcado de su
parte del descriptor: se lo observó llegar escuchando el nodo mientras se
accionaba el botón de DPI (`driver/scripts/sondear.py --escuchar 20`). El largo y
el significado de sus bytes proceden de ahí.

Los reportes de movimiento **no** circulan por aquí: van por las interfaces 0 y
1. Por este nodo solo llegan el Report ID 3 cada pocos segundos y las respuestas
de configuración. Por eso los problemas a 8 kHz no son del lado del anfitrión
—el lector no se satura— sino del enlace de radio.

### El mismo canal, visto desde Windows

`capturas-w/` contiene ese canal capturado con el driver oficial, que sirve de
referencia para contrastar byte a byte
(`dev/herramientas/leer-captura-usb.py`). Dos hechos que se observan ahí y no se
deducen del descriptor:

- El driver oficial emite las tramas por el **Interrupt OUT** `0x03`, en reportes
  de 64 bytes, igual que el puente.
- **Al accionar un solo control reescribe el perfil completo:** en
  `capturas-w/soft-rate-8000-a-1000.pcap` se observan cinco OUT consecutivos, a un
  segundo de intervalo (`0x0c`, DPI, iluminación, tasa de sondeo y botones). El
  puente no replica ese comportamiento: emite únicamente el comando permitido.

### Cable (`1d57:2126`), interfaz 2 → `/dev/hidraw7`

Aquí el canal de configuración es **distinto**: emplea Usage Page 0x0B con una
pila de *Feature Reports* de identificadores `0x03` a `0x2E` y largos variables,
en lugar de un único Output Report. El código del puente que dialoga con el
dongle **no sirve tal cual para el modo cable**.

**El descriptor, analizado** (LEÍDO de sysfs, con el dispositivo conectado; los
bytes figuran en `dev/tests/evidencia.py` como `DESCRIPTOR_DEL_CABLE`). Son
**25 Feature Reports**, y sus identificadores son los mismos números que los
comandos del dongle. El largo de la tabla es el que declara el descriptor; al
solicitarlo por `HIDIOCGFEATURE` hay que sumarle 1 byte, el del propio
identificador, que es como se compara contra el `sizeTotalData` del otro camino:

| cmd | Qué es por el dongle | Dongle (`sizeTotalData`) | Cable (`largo + id`) | ¿Coincide? |
| :--- | :--- | :--- | :--- | :--- |
| 4 | DPI | 56 | 52 | **no** |
| 5 | iluminación | 15 | 13 | **no** |
| 6 | tasa de sondeo | 9 | 9 | sí |
| 7 | modo de despertado | 8 (LEÍDO) | 8 | sí |
| 8 | botones | 59 | 59 | sí |
| 9 | macro | 111 | 64 | **no** |
| 10 | perfil completo | 128 | 8 | **no** |
| 11 | versión de firmware | 8 | 8 | sí |
| 12 | (sin nombre) | 10 | 6 | **no** |

Y existen **quince identificadores que el dongle no utiliza**: `0x10`, `0xA0` y
`0x22`..`0x2E` —este documento decía «once»; son 2 + 13, y el `0x23` aparece dos
veces—. Tres de ellos miden 132 (`0x22`, `0x23`, `0x28`) y uno 131, que es
exactamente `MACRO_SIZE_ZVE`, el bloque de macro de 131 bytes que compone el
constructor de la **web** y que el software nativo no emite por el dongle; hay
además otros de 109 y 103.

Con el descriptor por sí solo se establecían dos cosas: que **el canal por cable
existe y es consultable** —los identificadores y los largos los declara el propio
dispositivo— y que **el diseño interno no podía inferirse** de los tamaños.

**El diseño interno se obtuvo después del servicio auxiliar oficial** (LEÍDO,
`protocolo.md`, «El canal por CABLE»): el servicio enumera este dispositivo por
sus dos Usage Pages, 0x0B y 0x0A, como `connectionMethod` 0x80, y le escribe **el
mismo bloque que por el dongle** —`[cmd, sizeTotalData, perfil, campos...,
checksum interno]`— como Feature Report, con el `cmd` en el Report ID. Y los
largos que declara el dispositivo concuerdan: para DPI, iluminación y botones son
el bloque **sin el relleno final**, que en los respaldos es siempre cero
(`evidencia.md`, inferencia 19). El perfil completo y el `0x0c` siguen sin
explicación.

**Y la captura lo confirmó** (MEDIDO, `capturas-w/cable-soft-*.pcap`): cada
`SET_REPORT` del software nativo lleva el largo que declara este descriptor —52
el DPI—, y la Etapa 2 se cumple byte a byte. Una asimetría que conviene conocer:
en los `GET_REPORT` el cliente solicita el largo del dongle —56— y **el
dispositivo devuelve el bloque íntegro, con el relleno**, aunque su descriptor
declare 52. Y sin la petición previa por el reporte `0xA0`, el dispositivo no
responde ningún `GET`.

**Por cable el techo de tasa es 1000 Hz**, y no por una decisión del proyecto: el
dispositivo es Full Speed con `bInterval` de 1 ms, y el modelo ofrece únicamente
las tasas que el camino puede sostener
(`dispositivos.Perfil.tasa_maxima_por_cable`).

Por eso conviene trabajar siempre con el dongle y el cable desconectado.

Y no es solo prudencia, está **MEDIDO**: con el dispositivo conectado por cable
al equipo **no llega un solo latido por el dongle** —32 s sin un único Report ID
3, entre dos tramos que latían cada 2,00 s—, y en ese intervalo el dispositivo
estaba cargando, de modo que no es que se apagara: dejó de comunicarse por radio.
El dongle permanece en el bus y nada lo advierte; simplemente no llega nada más.
Un cargador externo, en cambio, alimenta sin apropiarse del canal, y es lo que
permitió medir el byte de carga.

## Cómo se determina el camino de conexión

`driver/scripts/donde-esta-el-mouse.py` lo informa, y **no toca el dispositivo**:
todo procede de `/sys/class/hidraw` y de los atributos del dispositivo USB. La
interfaz gráfica utiliza lo mismo para el indicador de la barra superior y para
advertir cuando el cable se apropia del canal
(`driver/src/linshark/conexiones.py`).

Con el dongle y el cable conectados simultáneamente:

```
X8 Pro por el dongle de 2.4 GHz, puerto 1-2 (bus 001 dispositivo 008)
    1d57:fa65 · LXDDZ 2.4G 8K HS Receiver · 480 Mbps
    interfaz 2: /dev/hidraw2 [lectura y escritura]  <- canal de configuración
X8 Pro por el cable USB, puerto 1-4 (bus 001 dispositivo 007)
    1d57:2126 · Beken X8PRO Mouse · 12 Mbps
```

El origen de cada dato, todo de sysfs: `idVendor`/`idProduct` determinan **cuál
de los dos caminos es**; el nombre del directorio del dispositivo (`1-2`, `1-4`,
o `1-4.3` si hay un concentrador) indica **el puerto**; `busnum`/`devnum` son lo
que muestra `lsusb`; y `speed` confirma la diferencia relevante: 480 Mbps por el
dongle y 12 por cable.

**El dispositivo no informa por qué camino está comunicándose.** El Report ID 3
transporta `[deviceId, 0x40, estadoBateria, nivel]` y nada más. El cliente oficial
dispone de un campo `connectionMethod` (128 cable, 129 inalámbrico, 130-131 cable
8K, 132 bluetooth) y **lo establece su servicio auxiliar**, que lo conoce por el
dispositivo USB del que ha leído: en el paquete de 6 o 7 bytes que el servicio
entrega a la plataforma, el `connectionMethod` va delante y los cuatro bytes del
dispositivo detrás (LEÍDO del *bundle*). Es decir que preguntárselo al dispositivo
no es una opción, tampoco para el fabricante: **el camino lo determina el bus**.

## Diagnóstico del lado de Linux

Sin anomalías que corregir:

- `hid-generic` toma las 8 interfaces sin un solo error en `dmesg`.
- `usbhid.mousepoll = 0`, de modo que el kernel no limita el sondeo.
- `power/control = on` en ambos dispositivos: no interviene la suspensión
  automática.
- Hyprland ya tiene `accel_profile = "flat"` y `sensitivity = 0.0`.

La única carencia real: **`/dev/hidraw*` son `root:root 0600`**, de modo que
ningún proceso del usuario puede comunicarse con el dispositivo. Lo resuelve
`udev/70-attackshark-x8pro.rules`, que concede acceso únicamente a la interfaz 2
y deja las de teclado y mouse sin modificar.
