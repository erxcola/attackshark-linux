# Captura desde KVM/QEMU — guía operativa

Procedimiento de la sesión de captura: Windows dentro de una VM con el dongle
asignado por USB, y **la captura realizada desde el anfitrión Linux con
usbmon**. Así no es necesario instalar USBPcap dentro de la VM, y los archivos
quedan directamente donde se analizan.

Se capturan las dos aplicaciones: el **WebDriver** (el servicio auxiliar del
navegador) y el **software nativo** (`ATTACK SHARK X8 SOFT.exe`). No son el
mismo programa y consta que pueden escribir valores distintos, de modo que se
etiquetan por separado.

---

## Comprobaciones previas

- [ ] **Únicamente el dongle conectado.** Por cable el dispositivo emplea
      *Feature Reports*, que son otro protocolo; una captura del cable no sirve
      como referencia y llevaría a escribir en el dongle un *framing* que no le
      corresponde. Para capturar **el cable** existe otra sesión, con su propia
      lista: sección 6.
- [ ] Batería del dispositivo cargada.
- [ ] **Reducir la tasa de sondeo si está en 8000 Hz.** Por dos motivos: a esa
      tasa el tráfico de movimiento engrosa considerablemente el archivo, y el
      respaldo que conviene tomar antes y después **no puede completarse** (ver
      `bitacora.md`).
- [ ] Anotar la versión de firmware que muestra la propia plataforma. Una captura
      de la que se desconoce el firmware no sirve como referencia.
- [ ] **Anotar de qué unidad procede**, no solo de qué máquina. En una ocasión se
      descubrió que la Etapa W se había capturado en otro equipo y con **otro
      dispositivo**, y eso no constaba en ninguna parte: se dedujo mucho después
      por un byte del bloque de versión. Con el dongle asignado a la VM el
      dispositivo es el mismo que ve Linux, de modo que basta con declararlo; con
      un equipo aparte, hay que anotar cuál es y adjuntar su bloque de versión.
- [ ] Cerrar `linshark` si estuviera en ejecución: dos procesos dialogando con el
      mismo `/dev/hidraw` se interfieren.

---

## 1. Preparar la captura en el anfitrión

Una sola vez:

```bash
sudo dev/herramientas/preparar-captura-vm.sh
```

Instala `tcpdump` si falta, monta `debugfs`, carga `usbmon` y lo deja cargándose
al arranque.

**No instala una regla de udev que abra `/dev/usbmon*` a un grupo**, y es
deliberado: eso entregaría a ese grupo el tráfico USB completo de la máquina,
teclado incluido. Las capturas se ejecutan con `sudo`, una por sesión.

El equivalente manual:

```bash
sudo modprobe usbmon
ls /sys/kernel/debug/usb/usbmon/     # debe existir

lsusb | grep 1d57                    # anotar el número de bus
#   Bus 001 Device 002: ID 1d57:fa65 ...   -> bus 1 -> usbmon1
```

El bus determina la interfaz: para `Bus 001`, es `usbmon1`. Si `tcpdump` no
enumera `usbmon1`, falta el `modprobe` o `debugfs` no está montado
(`sudo mount -t debugfs none /sys/kernel/debug`).

---

## 2. Asignar el dongle a la VM

Con libvirt, lo más simple es un XML de dispositivo:

```xml
<hostdev mode='subsystem' type='usb' managed='yes'>
  <source>
    <vendor id='0x1d57'/>
    <product id='0xfa65'/>
  </source>
</hostdev>
```

```bash
virsh -c qemu:///system attach-device <vm> dongle.xml --config
```

Con QEMU directamente: `-device usb-host,vendorid=0x1d57,productid=0xfa65`.

**Conviene emplear `--config`**: así forma parte de la definición y se adjunta
automáticamente en cada arranque. `managed='yes'` hace que libvirt retire el
controlador al anfitrión al arrancar y se lo devuelva al apagar, de modo que el
dongle vuelve por sí solo. Se identifica por vendedor y producto, no por puerto,
de modo que sobrevive a un cambio de conector.

Mientras la VM está en ejecución, **Linux se queda sin el dispositivo**: el
dongle pertenece a la VM. De ahí que la sesión se maneje con el panel táctil.

Para retirarlo de la definición:

```bash
virsh -c qemu:///system detach-device <vm> dongle.xml --config
```

**El *passthrough* no impide que el anfitrión observe el tráfico**: usbmon
captura a nivel del kernel del anfitrión, por donde el tráfico pasa igualmente.
Por eso el método funciona.

---

## 3. Qué capturar, y en qué orden

Una captura **por acción**, y breve. Resulta muy preferible a una captura larga
con todo mezclado: si el archivo contiene un único Interrupt OUT, no hay duda
sobre a qué corresponde.

Nombrar `web-<qué>.pcap` y `soft-<qué>.pcap` para no mezclar ambas aplicaciones.

| Prioridad | Acción | Justificación |
| :--- | :--- | :--- |
| 1 | **Iluminación**: cambiar color, brillo, modo | Es el único comando cuya estructura está transcrita por completo y que aún no se ha observado escribir. Cierra el primer bloque nuevo |
| 2 | **Distancia de despegue / tiempo de apagado / responseTime** | Comparten estructura con la iluminación (`co()`), de modo que una captura valida ambas |
| 3 | **Modo de despertado** | Resuelve la ambigüedad pendiente: si la petición va con cmd 7 o con `0x0C` |
| 4 | **Corrección de ángulo / control de fluctuación / sincronización de movimiento** | Residen en el bloque de DPI (`SensitivityX/Y`); sirve para confirmar esos dos campos |
| 5 | **DPI: modificar un único nivel** | El *framing* ya se conoce, pero un cambio de **un** valor confirma qué campo se desplaza |
| 6 | **Botones**: reasignar uno que no sea el izquierdo | Estructura nueva, la más arriesgada de escribir; conviene tenerla medida |
| 7 | **Macros** | El único camino multibloque; confirma los largos 64 y 57 también en escritura real |

Para cada una, una corrida:

```bash
sudo dev/herramientas/capturar-vm.sh web luz-rojo      # y después: soft luz-rojo
```

Inicia la captura en el bus del dongle y, al interrumpirla con Ctrl-C, pregunta
qué valor se estableció y con qué firmware, escribe el `.txt` adjunto y ejecuta
el análisis. Antes de comenzar comprueba los dos puntos verificables de la lista
previa: que no haya un dispositivo conectado por cable y que no haya un
`linshark` en ejecución.

Manualmente: iniciar `tcpdump`, accionar **un** control, esperar dos segundos,
interrumpir, y anotar en un `.txt` adjunto qué valor se estableció.

### Un caso que vale doble

Si es posible, capturar **la misma acción con el mismo valor** en el software
nativo y en la web. Si ambas tramas resultan idénticas, queda demostrado que el
*framing* no depende de la aplicación. Si difieren, constituye un hallazgo
relevante y hay que decidir a cuál se asemeja el proyecto.

---

## 4. Analizar, en el anfitrión

```bash
dev/herramientas/leer-captura-usb.py /tmp/web-luz.pcap
```

Por cada Interrupt OUT muestra la trama, valida el checksum, la interpreta y
—lo esencial— **la compara contra lo que compondría `build_write_frame()`**.

El resultado que se busca es:

```
    build_write_frame(bloque) -> IDENTICO
```

Ese es el criterio de la Etapa 2 de `metodo.md`. Si indica `DIFIERE`, hay que
comprender por qué **antes** de habilitar la escritura de ese comando.

---

## 5. Conservar la evidencia

Los `.pcap` van a `capturas-w/`, junto con un `.txt` que indique qué se accionó y
con qué valor. Sin esa nota, una captura consultada un mes después resulta
ininterpretable.

---

## 6. Capturar el canal por cable

Es otro protocolo y otra sesión. Lo que hace el servicio auxiliar por ese camino
está **LEÍDO** de su binario (`protocolo.md`, «El canal por CABLE»): una petición
por el reporte `0xA0`, el bloque mediante un `GET_REPORT(Feature)`, y las
escrituras como `SET_REPORT(Feature)` con el `cmd` en el Report ID. **Lo que la
captura debe aportar** es aquello que el binario no declara: qué largo establece
Windows en cada `SET_REPORT`, qué bloques devuelve el dispositivo, y qué contiene
el byte 4 de la petición del macro. Que el dispositivo **no** responde a un `GET`
solicitado en frío, sin el `0xA0`, ya está MEDIDO (`evidencia.md`): por eso los
bloques proceden de aquí y no de `leer-por-cable.py`.

**Quien dialoga por cable es la web**, a través de su servicio auxiliar: la
plataforma admite al X8 Pro por la ruta de cable (`setWiredDevice`) y el servicio
lo enumera como `connectionMethod` 0x80. Se captura con `web`; del software
nativo se desconoce si dialoga por cable.

Comprobaciones previas:

- [ ] **El dispositivo conectado por cable, y el cable asignado a la VM.** El
      dongle puede permanecer: con el cable conectado el dispositivo no se
      comunica por radio (MEDIDO), y el paquete de presencia que observa la
      plataforma es el latido del dispositivo con el `connectionMethod` delante
      (LEÍDO, de las cadenas de formato del servicio auxiliar), de modo que un
      dongle silencioso no debería aparecer (INFERIDO). Si aparece, retirarlo. Su
      tráfico circula por Interrupt y el lector lo separa.
- [ ] **El estado de partida, documentado.** Con el cable conectado no puede
      tomarse el respaldo por el dongle, y por cable no puede leerse en frío:
      sirve el último respaldo por el dongle, tomado inmediatamente antes.
- [ ] **La tasa en 1000 Hz, establecida antes de conectar el cable**
      (`driver/scripts/cambiar-rate.py --valor 1000`, por el dongle). Por radio el
      mouse puede estar en 8000, por cable no se superan los 1000 (`hardware.md`), y la ruta de
      cable de la plataforma no marca `highSpeedFlag`: qué muestra y qué reescribe
      con un dispositivo almacenado a 8000 no está medido, y no conviene que la
      captura lo averigüe de paso.

Asignar el cable a la VM. **En `JSJUANPC1W` ya está configurado**, junto al
dongle:

```xml
<hostdev mode='subsystem' type='usb' managed='yes'>
  <source startupPolicy='optional'>
    <vendor id='0x1d57'/>
    <product id='0x2126'/>
  </source>
</hostdev>
```

```bash
virsh -c qemu:///system attach-device <vm> cable.xml --config
```

El `startupPolicy='optional'` permite que la VM **arranque igualmente sin el
cable conectado**: sin él, libvirt se niega a arrancarla si no encuentra el
dispositivo. La entrada del dongle carece de esa política, de modo que hoy esa VM
no arranca sin el dongle presente.

Mientras la VM está en ejecución, Linux se queda sin el dispositivo igual que con
el dongle, y este continúa cargándose.

Una captura por acción, en este orden:

| Orden | Etiqueta | Acción | Qué determina |
| :--- | :--- | :--- | :--- |
| 1 | `abrir` | abrir la plataforma y esperar a que cargue, sin accionar nada | la petición `0xA0` y los `GET` de cada bloque: si `build_cable_read_request` produce IDENTICO, y con qué largo vuelve cada reporte |
| 2 | `rate-500` | tasa de sondeo a 500 Hz | la primera escritura: el largo del `SET_REPORT`, y qué bytes cambia respecto de la lectura |
| 3 | `rate-1000` | y de vuelta a 1000 Hz | el par que convierte una escritura real en otra (Etapa 2, forma 2) |
| 4 | `lod-2` | distancia de despegue a 2 mm | el reporte de **DPI**, que mide 52 por cable y 56 por el dongle: si Windows emite 52, 56 o 132 |
| 5 | `lod-1` | y de vuelta a 1 mm | su par |
| 6 | `macros` | abrir la pantalla de macros, sin grabar nada | la petición del macro: qué contiene su byte 4 |

```bash
sudo dev/herramientas/capturar-vm.sh --cable web abrir
sudo dev/herramientas/capturar-vm.sh --cable web rate-500
...
```

Las capturas se generan como `cable-web-<qué>.pcap` y el análisis se ejecuta solo.
En la sección **«Feature Reports (el canal del cable)»** hay que observar:

- `build_cable_read_request(N) -> IDENTICO` en cada petición de lectura;
- el **largo** de cada `SET_REPORT` de escritura —`-> 52 B`, `-> 56 B` o
  `-> 132 B` para el DPI—, que es la primera pregunta;
- `checksum interno: ok` en todo lo leído y lo escrito;
- y la línea `cambia respecto de la lectura en los bytes ...`: deben ser el campo
  accionado y los dos del checksum interno. Cualquier otro byte es la plataforma
  sobrescribiendo algo, comportamiento ya observado por el dongle
  (`protocolo.md`, «La página reescribe todo lo que leyó»).

**Al terminar:** retirar el cable de la VM, **revisar la configuración** —la web
reescribe lo que lee— y restituirla con el dongle y la aplicación, que es el
camino medido.

### Lo capturado, y lo pendiente

Las seis acciones de la tabla están hechas y la Etapa 2 se cumple en todo lo que
muestran (`protocolo.md`, «Lo que dijo la captura»). **Pero no proceden de la
web: proceden del software nativo** (`capturas-w/cable-soft-*.pcap`). Los
comandos indicados arriba dicen `web` y el usuario abrió el software nativo; las
capturas resultaron `cable-web-*` y así se interpretaron hasta que él lo aclaró.
**La etiqueta la establece el comando, no lo que se abre**: al capturar, conviene
anotar en la nota qué cliente se abrió realmente.

Lo que dejaron establecido: **el software nativo, por cable, lee solo tasa, DPI e
iluminación al abrirse**, y no escribe nada. Las peticiones de lectura de
botones, macro, perfil completo y versión no aparecen en ninguna. La única
captura que aún podría mostrarlas es **la web** abriendo por cable —su servicio
auxiliar declara las ocho, LEÍDO—, con el peaje habitual: la web reescribe lo que
lee. El usuario optó por no pagarlo y emplear las peticiones LEÍDAS del servicio
auxiliar (`SIGUIENTE-SESION.md`).

---

## Riesgos del método

Reducidos, pero conviene tenerlos presentes:

- **Quien escribe es el driver oficial**, no este proyecto. El riesgo de
  inutilizar el dispositivo no difiere del que supone usarlo normalmente en
  Windows.
- Un **bloqueo de la VM en mitad de una escritura** deja el comando a medias. Es
  el mismo riesgo que un cierre abrupto en Windows nativo, y por eso conviene
  realizar las capturas de una en una y no encadenar diez.
- El dongle a 8 kHz genera **mucho** tráfico de movimiento. No es peligroso, pero
  engrosa el archivo: conviene mover el dispositivo lo menos posible durante la
  captura, y filtrar después.

---

## Al finalizar

Basta con apagar la VM: con `managed='yes'` libvirt devuelve el dongle al
anfitrión al apagarse. Conviene ejecutar `driver/scripts/respaldar.py`
**después** de la sesión: el driver oficial probablemente haya dejado la
configuración modificada, y el respaldo debe reflejar el estado real con el que
se va a trabajar.
