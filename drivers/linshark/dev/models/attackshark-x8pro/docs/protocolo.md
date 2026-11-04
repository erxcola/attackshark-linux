# Protocolo del web driver de szslxd-tech.com

**La primera mitad** de este documento (protocolo WebSocket pagina <-> helper)
salio de leer el bundle JavaScript de la web (211 chunks, copia parcial en
`dev/research/webapp/`). **La segunda mitad** (la trama que va al mouse) salio de
extraer `WebDriverSetup.exe` con `innoextract` y desensamblar `WebDriver.exe`
con `objdump`: extraccion y lectura estatica, sin decompilador ni ejecucion de
nada de Windows. Cada afirmacion dice de cual de las dos fuentes viene.

## Lo primero: la web NO usa WebHID

Es lo que cambia todo el planteo. En el bundle entero **no hay una sola
llamada a `navigator.hid` ni a `requestDevice`**. Lo que hay es:

```js
connect() {
  if (this.socket) return;
  this.socket = new WebSocket("ws://localhost:10086");
  ...
}
```

y, en la vista de bienvenida, el plan B si eso no conecta:

```js
onMounted(() => {
  store.connect();
  setTimeout(() => {
    if (!store.connected) window.location.href = "myapp://WebDriver";
  }, 3000);
});
```

seguido de botones para bajar `WebDriverSetup.exe` y `WebDriverForMac.pkg`.
**No hay build de Linux**, y por eso la web se queda para siempre en la
pantalla de "descarga el driver" por mas permisos o flags que le pongas.

La pagina es solo la interfaz. Todo el acceso al mouse lo hace un demonio
nativo local. Este proyecto es un reemplazo de ese demonio.

### Residuo: la version vieja si usaba WebHID

En `dev/research/webapp/index-Dh2X5xHc.js` sobrevive el camino anterior:

```js
async function i(s) {
  let e = r().device;
  if (!e.opened || !e) { console.error("设备未连接"); return }
  await e.sendReport(4, s);
}
```

`device` esta declarado como `device: null` en el store y **nunca se
asigna**, asi que es codigo muerto. Pero es la mejor pista que tenemos: en
`indexX8Pro-BTVvPdTw.js` los dos caminos conviven y mandan el mismo payload,
uno con el prefijo de 2 bytes por WebSocket y el otro pelado con
`sendReport(4, payload)`. De ahi sale la hipotesis central de este proyecto:

> El helper recibe `[connectionMethod, deviceId, ...payload]`, usa los dos
> primeros bytes solo para rutear, y escribe `payload` como Output Report
> ID 4 en la interfaz 2 del dongle.

**CONFIRMADA contra el hardware** (fase 1) y reforzada despues, cuando una
escritura armada asi cambio efectivamente el report rate del mouse. Ver `bitacora.md`.

## Codificacion

Frames de **texto**, contenido en hexadecimal ASCII, sin separadores ni
prefijos de largo. La pagina decodifica asi:

```js
convertToHexArray(e) {
  return e.length % 2 !== 0 && (e += "0"),
         e.match(/.{1,2}/g).map(n => parseInt(n, 16))
}
```

Mandar frames binarios no funciona.

## Pagina -> helper

Dos familias de mensajes.

### 1. Lectura: prefijo `0xF0`, 5 bytes

```
[0xF0, connectionMethod, deviceId, cmd, sub]
```

El helper la interpreta el mismo en vez de reenviarla cruda. Constructor:

```js
async sendLegacyCommand(e, t, n, a) {
  const o = new ArrayBuffer(5), i = new DataView(o);
  let l = 0;
  i.setUint8(l++, 240);                   // 0xF0
  i.setUint8(l++, e.connectionMethod);
  i.setUint8(l++, e.deviceId);
  i.setUint8(l++, t);                     // cmd
  i.setUint8(l++, n);                     // sub
  ...
}
```

`readDeviceInfoNew()` usa el mismo formato con `cmd = 10, sub = 0` para pedir
el perfil entero de una.

### 2. Escritura: largo variable

```
[connectionMethod, deviceId, ...payload]
```

Los dos bytes de prefijo los pone `convertDeviceData()`:

```js
convertDeviceData(e) {
  const t = this.deviceNo,
        n = this.mouseArr.find(l => l.deviceId === t),
        a = Array.from(e);
  a.unshift(n.connectionMethod, t);
  return hex(new Uint8Array(a));
}
```

Hay una variante `convertDeviceDataImg()` que antepone
`[connectionMethod, deviceId, 0xFF]`, para transferencia de imagenes a los
modelos con pantalla.

**Ojo con generalizar el orden de los dos primeros bytes.** En las escrituras
el `cmd` es `payload[0]` y el tamaño `payload[1]`: eso esta MEDIDO contra las
cinco escrituras del HAR y lo fija `test_cmd_de_escritura`. Antes
`Request.cmd` leia el byte equivocado y una allowlist montada ahi habria
comparado tamaños contra codigos de comando.

Lo que no cierra es **el modo de despertado**, y solo el: manda payload
`[12, 7, 8, 0, 0, 0, 0, 0]` y su respuesta llega como `[conn, dev, 7, 8, ...]`,
que admite leerse como `[cmd=12, sizeTotalData=7, ...]` o como
`[L=12, cmd=7, sizeTotalData=8, ...]`. Las dos lecturas estan abiertas -ver la
seccion del comando 7- y por eso el puente no arma ninguna trama para el.

## Helper -> pagina

| Largo   | Forma                                        | Significado |
| ------- | -------------------------------------------- | ----------- |
| 2       | `[major, minor]`                             | version del helper |
| 3       | `[x, 0x00, deviceId]`                        | el dispositivo se desconecto |
| 5       | `[conn, dev, 0x50, ok, x]`                   | ack (`ok=0` exito, `ok=1` la pagina reintenta) |
| 6 o 7   | `[conn, 0x01, ..., deviceId, 0x40, batt, %]` | presencia + bateria |
| >= 6    | `[conn, dev, cmd, sub, ...datos]`            | respuesta a una lectura |
| >= 120  | `[conn, dev, 10, 0x80, ...]`                 | perfil completo |

### Version

La pagina tiene hardcodeado `version: [3, 5]`. Si recibe otra cosa muestra el
cartel de "actualiza el driver" (molesto pero no bloqueante). Y si el major es
menor a 3, o es exactamente 3.0, activa `readFlag` y **desactiva toda la
funcionalidad de lectura**. Por eso el puente anuncia `03 05`.

### Presencia

Es el mensaje que hace que la pagina entre a la interfaz del mouse. Formato de
7 bytes:

```
[0] connectionMethod   0x80..0x85
[1] 0x01               setDevice() descarta el paquete si esto no es 1
[2] sin usar
[3] deviceId           8 = X8 Pro
[4] 0x40 o 0x41        si no, el handler de presencia lo descarta
[5] batteryStatus      1 = a bateria, 3 = cargando (MEDIDO)
[6] batteryLevel       porcentaje
```

El `batteryStatus` se midio poniendo y sacando un cargador externo, cuatro
transiciones, con el LED morado de carga como testigo independiente
(`bitacora.md`). El `2` del bundle -su constante de
"desconocido"- **nunca se lo vio**, y que manda con la bateria llena no se
midio.

En la variante de 6 bytes el `deviceId` esta en `[2]` y el marcador en `[3]`.

### `connectionMethod` y el ruteo

`setDevice()` rutea segun el primer byte:

| Valor | Handler              | Efecto |
| ----- | -------------------- | ------ |
| 0x80  | `setWiredDevice`     | cable 1 kHz |
| 0x81  | `setWirelessDevice`  | 2.4 GHz |
| 0x82  | `setWiredDevice8K`   | marca `highSpeedFlag = 1` |
| 0x83  | `setWiredDevice8K`   | idem |
| 0x84  | `setWirelessDevice`  | bluetooth, **solo si el paquete mide 6 bytes** |
| 0x85  | `setWiredDevice8K`   | idem 0x82 |

`highSpeedFlag = 1` es lo que habilita las opciones de 8 kHz en la interfaz.
El nombre `setWiredDevice8K` es enganoso: la lista de modelos que acepta
incluye al X8 Pro y nuestro dongle es inalambrico de 8 kHz.

### deviceId

`store.mouseNum` mapea **47 modelos** (contados en el bundle;
este documento decia 43). Y **no son de una sola marca**: las rutas del bundle
enrutan a tres —`/ATTACKSHARK/`, `/MAMBASNAKE/` e `/INX/`—, o sea que es
software OEM compartido. De los 47, solo 14 tienen ruta con marca explicita;
los demas caen en paginas genericas y no se les puede atribuir una. El catalogo
esta en `linshark/dispositivos.py`, y es **LEIDO**: el unico confirmado contra
hardware es el 8.

El que nos importa:

```
8 -> X8Pro
```

Con `deviceNo === 8`, `selectDevice()` hace
`router.push({ path: "/ATTACKSHARK/factoryX8Pro" })`. Esa ruta es el criterio
de exito de la fase 0.

## Codigos de comando

Salen de los handlers de respuesta del store (`n[2]` es el `cmd`):

| cmd  | sub  | Que es |
| ---- | ---- | ------ |
| 4    |      | DPI |
| 5    |      | iluminacion |
| 6    |      | report rate |
| 7    | 8    | modo de despertado |
| 8    | != 8 | botones |
| 9    |      | macros |
| 10   | 0x80 | perfil completo (respuesta >= 120 bytes) |
| 11   | 8    | version de firmware (respuesta `[4] << 8 | [5]`) |
| 0x50 |      | ack |

## Que expone la web para el X8 Pro

Estado por defecto del store:

```js
parameterX8Pro: {
  closeTime: 10,      // LOD / tiempo de apagado
  responseTime: 8,
  hibernateTime: null,
  rateRadio: 1,       // report rate
  sensitivityX: 0, sensitivityY: 0,
  straightLine: false,  // angle snapping
  ripple: true,         // ripple control
  motionSync: true,
  ...
}

dpiX8Pro: {
  dpiID: 1,
  dpiValue: { dpi1: 1200, dpi2: 2400, dpi3: 3200,
              dpi4: 5600, dpi5: 8000, dpi6: 40000,
              dpi7: 0, dpi8: 0 }
}
```

Mas iluminacion RGB, remapeo de botones y macros, en
`/ATTACKSHARK/parameterX8Pro` y `/ATTACKSHARK/dpiX8Pro`.

---

# La trama del lado del dispositivo

Esta parte **no se puede sacar del bundle JavaScript**. Salio de extraer
`WebDriverSetup.exe` con `innoextract` (extraccion pura, sin ejecutar nada de
Windows) y desensamblar el helper.

## Que trae el instalador

```
app/WebDriver.exe      4.14 MiB   el helper, MFC/MSVC, PE32 i386
app/hidapi.dll         82.5 KiB   acceso HID
app/msvcp140.dll  msvcr120.dll  ...
app/register_protocol.bat        registra el esquema myapp://
```

Que use **hidapi** ya dice bastante: el primer byte del buffer es el Report ID.
De sus imports, usa `hid_enumerate` + `hid_open_path` para elegir el
dispositivo, y despues `hid_write` / `hid_read`, mas
`hid_send_feature_report` / `hid_get_feature_report` para los modelos cuyo
canal de configuracion son Feature Reports (como el X8 Pro por cable).

## El formato, leido del desensamblado

En los 8 sitios donde llama a `hid_write` con largo 12, el buffer se arma asi
(bloque en `0x40e542`, para `connectionMethod` 0x83 y 0x85):

```asm
mov DWORD PTR [ebp-0xdc],0xca00c04   ; 04 0c a0 0c
mov BYTE  PTR [ebp-0xd8],0xa         ; 0a
mov WORD  PTR [ebp-0xd7],0x0         ; 00 00
...
movzx eax,BYTE PTR [ebp+ecx*1-0xdc]  ; suma buffer[0..9]
add   dx,ax
cmp   ecx,0xa
jl    ...
mov   BYTE PTR [ebp-0xd2],al         ; chkHi
mov   BYTE PTR [ebp-0xd1],al         ; chkLo
push  0xc                            ; largo 12
call  hid_write
```

O sea:

```
04 0c a0 CMD SUB 00 00 00 00 00 chkHi chkLo
^^ ^^ ^^
|  |  opcode:  0xa0 leer,  0x00 escribir/respuesta,  0xc0/0xc2/0xc3 estado
|  largo total de la trama, con el Report ID incluido
Report ID 4
```

**El checksum es la suma llana de todos los bytes anteriores, big-endian, e
incluye el byte del Report ID.** Ese detalle explica el `i = 4` que aparece
como semilla en `co()` y `Vve()` del JavaScript: no era una constante magica,
era el Report ID que `sendReport(4, ...)` agrega por su cuenta.

## La tabla de `sub`

Cada comando de lectura lleva un `sub` fijo. **La pagina manda siempre
`sub=0`**, asi que esto no se podia deducir del bundle: lo pone el helper de
su propia tabla.

| cmd  | sub  | Que lee |
| ---- | ---- | ------- |
| 0x04 | 0x38 | dpi |
| 0x05 | 0x0f | iluminacion |
| 0x06 | 0x09 | report rate |
| 0x08 | 0x3b | botones |
| 0x09 | 0x6f | macros |
| 0x0a | 0x80 | perfil completo |
| 0x0b | 0x08 | version de firmware |
| 0x0c | 0x0a | (sin identificar) |

**El comando 7 (modo de despertado) no esta en esta tabla, y hay un motivo
mas fuerte de lo que parecia.** El handler de la pagina es literal:

```js
if (n.length >= 10 && n[2] === 7 && n[3] === 8) {
  const o = n[1];
  this.handleLegacyWakeupModeResponse(o, n)
}
```

o sea que la **respuesta** viene con `cmd = 7` y `sizeTotalData = 8`. Pero el
**pedido** lo manda `WakeupModeReadCommand()` por el camino de ESCRITURA
(`convertDeviceData`, no `sendLegacyCommand`), con el payload
`[12, 7, 8, 0, 0, 0, 0, 0]`, y ese payload admite dos lecturas que no se
pueden separar con lo que tenemos:

- `[cmd=12, sizeTotalData=7, ...]`, siguiendo el layout de `co()` y `Of()`,
  que empiezan por `fixed`. Encajaria con el comando `0x0C` del binario.
- `[L=12, cmd=7, sizeTotalData=8, ...]`, que encajaria con el handler de
  arriba y con `L = 8 + 5 = 13`... salvo que ahi el 12 no cuadra.

Ninguna de las dos cierra del todo. **Se resuelve capturando**: basta abrir la
pantalla que lee el modo de despertado con `--backend stub --record` y mirar
que bytes manda. Hasta entonces no se arma ninguna trama para el comando 7:
el puente lo trata como no soportado, loguea y se calla. La pagina lo
lista con `sub = 8` en sus handlers, y `sendWakeupModeReadCommand()` manda
literalmente el payload `[12, 7, 8, 0, 0, 0, 0, 0]`. Pero eso viaja por el
camino de *escritura* de la pagina y va **sin checksum**: no es una de las
tramas de 12 bytes que arma el helper, y el cmd 7 no aparece entre los 8
sitios de `hid_write` con `push 0xc` del binario. Combinar los dos framings
seria inventar una trama, asi que el puente lo trata como **no soportado**:
loguea y se calla, en vez de mandar algo que nadie leyo nunca.

## El byte de perfil

El byte 5 de la trama es el **numero de perfil, 1-based**. No todos los
comandos lo llevan: version (0x0b) y 0x0c tienen un 0 literal ahi, mientras
que dpi, iluminacion, report rate, botones, macros y perfil completo lo
cargan desde un registro. En el desensamblado se ve claro:

```asm
mov al, BYTE PTR [ebp+0x8]      ; el argumento de la funcion
inc al                          ; +1  <- de aca sale que es 1-based
mov BYTE PTR [ebp-0xd3], al     ; buffer[5]
mov BYTE PTR [ebp-0xd4], 0x9    ; buffer[4] = sub
mov DWORD PTR [ebp-0xd8], 0x6a00c04   ; buffer[0..3] = 04 0c a0 06
```

Coincide con el `Tn.profileId = 1` que esta hardcodeado en el JavaScript.

Mandar 0 en esa posicion hace que el mouse **ignore el comando en silencio**:
el dongle acepta el pedido y despues avisa "sin respuesta". Es
indistinguible de una perdida del enlace, y por eso costo encontrarlo.

Se verifica sola contra la pagina: los handlers de respuesta esperan
exactamente estos valores (`cmd 11 -> sub 8`, `cmd 10 -> sub 128`).

## Respuestas

Misma trama, con `opcode = 0x00`. Ejemplo real de la version de firmware:

```
04 | 0d 00 0b 08 | 08 00 83 01 05 00 | 00 b5
     ^^ ^^ ^^ ^^                       ^^^^^
     |  |  |  sub                      suma = 181 = 0xb5
     |  |  cmd 0x0b
     |  opcode 0x00 = respuesta
     largo 13
```

El helper le saca `[largo, opcode]` y le antepone
`[connectionMethod, deviceId]`, y por eso la pagina lee el `cmd` en `n[2]` y
el `sub` en `n[3]`.

## Estados del dongle

Tramas de 6 bytes que manda el dongle, no el mouse:

| opcode | Significado |
| ------ | ----------- |
| 0xc0   | pedido aceptado y encolado hacia el mouse |
| 0xc2   | el mouse no contesto; hay que reintentar |
| 0xc3   | ocupado (llega si se mandan comandos muy pegados) |

## La trama de ESCRITURA

De los 17 sitios de `hid_write` del binario, **9 usan largo `0x41` (65 bytes)**
y son el camino de escritura. Estan en tres trios identicos (`0x40d679`,
`0x40dad9`, `0x40df39`), uno por grupo de `connectionMethod`, igual que las
lecturas. Cada trio tiene una rama general y dos de un camino por bloques.

### La rama general

Es la que importa. Empieza en `0x40d8aa` y termina en el `hid_write` de
`0x40d9c5`:

```asm
ecx = [ebp-0x800]                     ; N
mov BYTE PTR [ebp-0x210],0x4          ; buffer[0] = Report ID 4
lea eax,[ecx+0x5]
mov BYTE PTR [ebp-0x20f],al           ; buffer[1] = N + 5   <- largo total
mov BYTE PTR [ebp-0x20e],0x0          ; buffer[2] = 0x00    <- opcode escribir
push ecx ; push [ebp-0x7f0] ; push [ebp-0x20d]
call 0x591af0                         ; memcpy(&buffer[3], mensaje, N)
...                                   ; suma buffer[0 .. N+3)
mov BYTE PTR [ebp+ecx*1-0x20d],al     ; buffer[N+3] = chkHi
mov BYTE PTR [ebp+ecx*1-0x20c],al     ; buffer[N+4] = chkLo
push 0x41 ; call hid_write            ; y despues Sleep(500)
```

O sea:

```
04 L 00 | ...N bytes... | chkHi chkLo        con L = N + 5
```

**Es la misma regla que las lecturas**: el byte 1 es el largo total `L`, y el
checksum son los dos ultimos bytes de esos `L`, sumando todo lo anterior con
el Report ID incluido. Se verifico con tres largos distintos del binario
(12, 57 y 64) y contra respuestas reales del mouse.

El `0x41` que se le pasa a `hid_write` **no es el largo de la trama**: hidapi
en Windows ajusta el buffer al tamano del report. El descriptor del dongle
declara 63 bytes de datos, o sea un report de 64 (1 de Report ID + 63), y el
byte 65 sobra. **En Linux se escribe el report de 64.** Lo confirma el propio
binario, que en el bloque de un solo report pone `buffer[1] = 0x40 = 64`.

### El camino por bloques

El trio que arranca en `0x40d612` es para los payloads que no entran en un
report. Se activa comparando el primer byte del mensaje con 9 (macros):

- Los datos se parten en bloques de **`0x3b` = 59 bytes** (`imul eax,edx,0x3b`).
- El **byte 2 deja de ser el opcode y pasa a ser el numero de bloque**,
  0-based.
- El primer bloque declara largo `0x40` (64) y el ultimo `0x39` (57).
- `Sleep(200)` entre bloques y `Sleep(1000)` al final.

De los dos bloques y el largo `0x39` del segundo se deduce que el payload de
macros mide 111 bytes (59 + 52).

**Ya no es inferencia: quedo [MEDIDO].** El mouse contesta `macro` con
`sizeTotalData` 111 y 109 bytes de datos, en los ocho respaldos tomados por
hidraw, y la respuesta llega justo en dos bloques de 64 y 57 — los mismos
largos que usa el binario para escribir. `test_reensamblado` los fija como
regresion.

### El byte que llamamos `sub` es `sizeTotalData`

Al reconstruir la escritura aparecio que el `sub` de la tabla no se comporta
como un subcomando sino como el **largo del bloque** `[cmd, N, ...datos]`. Y
despues aparecio la confirmacion directa: **asi se llama en el bundle**. Los
constructores de payload de `app.js` arrancan todos igual:

```js
function co(e) {
  const t = e.sizeTotalData + 5,
        n = new ArrayBuffer(t),
        a = new DataView(n);
  let o = 0;
  a.setUint8(o++, e.fixed);          // el cmd
  a.setUint8(o++, e.sizeTotalData);  // el byte que llamabamos `sub`
  a.setUint8(o++, e.profileId);
  ...
```

`e.fixed` es el codigo de comando y `e.sizeTotalData` es el largo, y el total
de la trama es `sizeTotalData + 5`, escrito literal en la primera linea. Los
valores por defecto de los objetos que se le pasan cierran con la tabla que
habiamos sacado del **binario**, que es una fuente independiente:

| objeto | `fixed` | `sizeTotalData` | `READ_SUB` del binario |
| ------ | ------- | --------------- | ---------------------- |
| `gw` (iluminacion) | 5 | 15 | `0x0F` = 15 |
| `Qt` (dpi) | 4 | 56 | `0x38` = 56 |

Y cuadra con las cuatro lecturas que le hicimos al mouse:

| comando | `sub` = N | L = N + 5 | trama real |
| ------- | --------- | --------- | ---------- |
| version de firmware | 8 | 13 | `04 0d 00 0b 08 ...` |
| report rate | 9 | 14 | `04 0e 00 06 09 ...` |
| iluminacion | 15 | 20 | (13 bytes de datos) |
| dpi | 56 | 61 | `04 3d 00 04 38 ...` |

En el **pedido** de lectura el largo total es 12 fijo, porque el pedido no
lleva datos, y `N` le dice al mouse cuanto devolver. En la **respuesta** y en
las escrituras, `L = N + 5`. Encaja ademas con el binario, donde ese mismo
byte es el `n` del `memcpy` de `0x40cf8d` y el sumando del `buffer[1] = n + 5`.

Explica de paso por que la pagina manda siempre `sub = 0`: no conoce el tamano
de cada estructura de configuracion, lo pone el helper de su tabla.

Con el nombre `sizeTotalData` del propio bundle y el `+5` escrito ahi mismo,
esto pasa a ser **[LEIDO]**, no interpretacion. Se dejo igual el nombre `sub`
en el codigo porque es el que usan los handlers de la pagina, pero esta
aclarado en `protocol.py`.

## El canal por CABLE, leido del helper

**Todo esta seccion es [LEIDO]** de `WebDriver.exe` (sha256 `0eea3fef…`):
dice que bytes arma el helper, no que pone Windows en el bus. Lo que el bus
mostro esta al final, en "Lo que dijo la captura", y **no es el helper**: es
el soft nativo, otro programa, hablando el mismo protocolo. Los constructores
estan en `protocol.py` (`build_cable_read_request`,
`build_cable_write_report`), y los usa `driver/src/linshark/cable.py`, que es
el canal: la misma interfaz que el `Device` del dongle, con los tiempos y el
reintento del STALL que se vieron en el bus.

### Quien habla por cable: la web, a traves del helper

Estos documentos decian que "el cliente web no habla por cable", porque el
bundle no usa `sendFeatureReport` en ningun lado. **Era una inferencia por
ausencia, y estaba mal**: la pagina no le habla a ningun HID -habla con el
helper por WebSocket- y quien toca el USB es el helper, que tiene el camino del
cable entero.

- **La enumeracion** (`0x4115a8`) hace `hid_enumerate(0x1d57, 0)`, descarta los
  dos dongles (`0xfa60`, `0xfa65`) y se queda con las colecciones de **Usage
  Page 0x0B** (configuracion) y **0x0A** (notificaciones), usage 0. Es justo
  lo que declara la interfaz 2 del cable (`hardware.md`). Ese grupo es el de
  `connectionMethod` **0x80**.
- **La pagina lo acepta**: `setWiredDevice` incluye `8: "X8Pro"`, y para 128
  muestra "WiredConnection".

Hay un segundo grupo por Feature Reports, el **0x81**: un dongle de otro PID
(`0xfa60`, enumerado en `0x4098ce`) con las mismas dos Usage Pages. No es el
nuestro -el nuestro es `0xfa65` y va por Output Report- pero comparte las dos
funciones de abajo.

### Leer: un pedido por `0xA0`, y despues el bloque

`0x40e380(h, conn, cmd, sub, perfil)`, que solo corre para 0x80 y 0x81:

```
Sleep(100)
SET_FEATURE [a0, cmd, sub, 00, perfil, 00, 00, 00]   ; hasta 10 veces, hasta
Sleep(500)                                           ; que no falle
GET_FEATURE [a0, ...] (8 B); Sleep(100)              ; una vez
listo si el byte 1 == 1
```

y despues cada llamador hace `GET_FEATURE [cmd, ...]` con el largo `sub`, y
le pasa a la pagina `%02x%02x` (conn, dev) seguido del buffer tal cual
(`0x412730`). O sea que **el report es `[cmd, sizeTotalData, perfil,
campos..., checksum interno]`**: el mismo bloque que viaja adentro de la trama
del dongle, sin el `04 L 00` de afuera ni su checksum.

| cmd | llamador | `sub` | byte 4 del pedido | `GET_FEATURE` en |
| --- | --- | --- | --- | --- |
| dpi | `0x4137a6` | `0x38` | perfil + 1 | `0x4137da` |
| iluminacion | `0x413288` | `0x0f` | perfil + 1 | `0x4132bc` |
| report rate | `0x412ca6` | `0x09` | perfil + 1 | `0x412cda` |
| botones | `0x413cc6` | `0x3b` | perfil + 1 | `0x413cfa` |
| macro | `0x40fbd7` | **`0x83`** | `[ebx+8]`, **sin** el +1 | `0x40fc0e` |
| perfil completo | `0x40f61d` | `0x80` | perfil + 1 | `0x40f654` |
| version | `0x40ef33` | `0x08` | 0 | `0x40ef67` |
| 0x0c | `0x40e8e5` | `0x0a` | 0 | `0x40e919` |

Tres diferencias con el pedido del dongle: **un `00` de mas** entre el `sub` y
el perfil; el macro pide **131** (`0x83`, el `MACRO_SIZE_ZVE` de la web) y no
111; y en el macro el byte 4 no es el perfil: **es el id del macro**
(seguido el 2026-09-18). La misma funcion (`0x40f780`) tiene los dos caminos:
por el dongle (`connectionMethod` 0x83/0x85) arma `04 0c a0 09 6f` y pone
`[ebx+0x8]` en el byte 5 (`0x40f81c`), que es donde el id del macro hace que
el mouse devuelva el bloque (MEDIDO); por cable (0x80/0x81, `0x40fbcb`) pasa
**la misma variable** como el "perfil" de `0x40e380`, que va al byte 4. O sea
`a0 09 83 00 <id> 00 00 00`, y despues `GET_FEATURE(9)` de 131
(`0x40fc07`). Es lo que arma `build_cable_read_request(9, macro_id=N)`.

### Escribir: el bloque como Feature Report

En la rama 0x80 de `0x40cf10`:

```
hid_send_feature_report(h, payload, payload[1]); Sleep(500)   ; 0x40d1f4
```

con `payload` el mensaje de la pagina sin `[conn, dev]`: `[cmd,
sizeTotalData, perfil, ...]`, el mismo `bloque` que recibe
`Device.escribir()`. **El `cmd` hace de Report ID**, y no hay checksum de
afuera: solo el interno de la estructura.

El macro va aparte (`0x40cff8`), en trozos de 64 bytes:

```
[09, 40, payload[2], trozo, 60 bytes de payload[3:]]         ; Sleep(500) cada uno
```

dos trozos si `sizeTotalData` es `0x6f` (111), y si no tres, con `0x0c` en el
byte 1 del tercero (`0x40d1e1`). El cable declara el report 9 de **64 bytes**:
justo el trozo.

### Lo que cierra con lo medido, y lo que no

**Cierra [MEDIDO sobre los respaldos]**: el largo que el cable declara para
dpi, luz y botones es exactamente `[cmd, size]` + los campos + los dos bytes
del checksum interno -52, 13 y 59- y lo que queda afuera es el relleno del
dongle: **cero en los 120 bloques de dpi y los 121 de luz** de los respaldos.
Lo verifica `test_el_cable_mide_el_bloque_sin_relleno`. Rate y version miden
igual por los dos caminos.

**No cierra, y queda abierto**: el perfil completo (el cable declara 8 bytes y
el helper pide 128) y el 0x0c (6 contra 10).

### Lo que dijo la captura [MEDIDO]

Seis capturas del **soft nativo** configurando por cable
(`capturas-w/cable-soft-*.pcap`, con la nota de cada una al lado). Se
llamaron `cable-web-*` hasta que el usuario aclaro que lo que abrio en la VM
fue el soft: el `web` venia del comando que le armo el asistente. El bus lo
confirma por su cuenta: el bloque de botones que se escribio lleva la rueda en
`0a, 09`, que es el orden del soft (la pagina escribe `09, 0a`), y el byte de
rate `0x73` trae los dos nibbles distintos (la pagina los escribe iguales).

**Que sea el soft y no el helper importa**: lo que el helper arma sigue sin
verse en el cable. Lo que si queda es mas fuerte en otro sentido: los pedidos
que `build_cable_read_request()` transcribe del helper salieron **byte a
byte** de otro programa, que no comparte codigo con el. Las tres preguntas que
el binario dejaba abiertas:

1. **El largo de cada `SET_REPORT` es el que declara el mouse**: 52 el dpi, 9
   el rate, 59 los botones, 64 cada trozo de macro, que es
   `build_cable_write_report()` byte a byte. Los `GET_REPORT` piden los
   largos de la tabla del helper -56, 15, 9- y **el mouse devuelve el bloque
   entero, con el relleno**;
2. **sin el pedido `0xA0` el mouse no contesta**: pedido en frio, los ocho
   `GET` dieron timeout (`leer-por-cable.py`). Con el pedido, la secuencia es
   la del binario: `SET(a0 …)`, `GET(a0)` que vuelve `a0 01`, `GET(cmd)`. El
   pedido sale identico a `build_cable_read_request()` en rate, dpi y luz;
3. **que va en el byte 4 del pedido del macro sigue sin saberse**: el soft,
   por cable, lee solo rate, dpi y luz **al abrirse**, y no escribe nada.
   Botones, macro, perfil completo, version y 0x0c no los leyo en ninguna de
   las seis. **Capturar al soft abriendo ya esta hecho** (`cable-soft-abrir`):
   no los lee.

Y dos cosas que no se preguntaban:

- **el nibble del rate es el otro**. Por cable el soft mueve el **bajo** del
  byte de rate: leyo `0x74`, escribio `0x73` para 500 Hz y `0x74` para 1000,
  con el alto -la tasa inalambrica, 7 = 8000 Hz- quieto. Por el dongle el
  mismo soft hace lo contrario -mueve el alto y deja el bajo en 4-, asi que un
  solo cliente maneja los dos nibbles por separado segun el camino. Por eso
  hay un codificador aparte, `escribir_report_rate_por_cable()`: el del
  dongle habria escrito `0x34`;
- **el mouse a veces rechaza un `SET_REPORT` con STALL**, y el mismo `SET`
  repetido ~205 ms despues pasa: 6 de 19 pedidos, los seis aceptados al
  segundo intento. Quien reintenta -el soft, Windows o QEMU- no se sabe; lo
  que importa es que en el bus es lo que pasa, y que funciona.

**La Etapa 2 del cable esta cumplida en todo lo capturado** (`test_etapa2_cable`):
desde lo que devolvio el mouse, nuestros codificadores dan lo que escribio el
soft en el LOD, el nivel 1 del dpi, el rate, el boton del costado-adelante y
los tres modos del macro 17, ida y vuelta donde la hubo. Los botones se
parten del bloque leido **por el dongle**, porque por cable el soft no los
lee: es el mismo mouse y el mismo bloque.

## Las estructuras, campo por campo

Los mismos constructores dan el contenido. Estan transcriptos en
`driver/src/linshark/estructuras.py`, con esta verificacion contra el hardware:

### Iluminacion (`fixed = 5`, `sizeTotalData = 15`)

```
profileId  lightMode<<4  breathingSpeed  LightBrightness
redColor  greenColor  blueColor  closeTime*2  direction/2
chk1Hi chk1Lo  0x00 0x00
```

Contra los 13 bytes que devolvio el mouse (`01 00 03 a8 00 ff 00 01 04 01 af
00 00`): el color sale **(0, 255, 0)**, que es el verde que tenia el LED en ese
momento, y el checksum interno recalculado da **0x01af**, exactamente los dos
bytes que trae la captura. `co()` lo calcula como la suma de `buf[3..o)`.

### DPI (`fixed = 4`, `sizeTotalData = 56`)

```
profileId  SensitivityX  SensitivityY  dpi_ON_OFF_flag
DPI_X_Double_Flag  DPI_Y_Double_Flag
Dpi_X_setting[8]  Dpi_Y_setting[8]  Current_Dpi_level_flag
Dpi_level_1..8_indication_flag[3]  Dpi_indication_type
chk1Hi chk1Lo  relleno
```

Contra los 54 bytes reales, tres anclas independientes:

1. Los **ocho campos de color** coinciden byte por byte con los valores por
   defecto del objeto `Qt` del bundle (`ff0000`, `00ff00`, ..., `ff4000`,
   `ffffff`), y `Dpi_indication_type` da 2, tambien el default.
2. `dpi_ON_OFF_flag` da `0x3f` = 63, el default.
3. `Dpi_X_setting` cae donde tiene que caer y decodifica a seis valores
   plausibles.

   > **Anotado, y corregido dos veces el mismo dia.** Este ancla
   > decia "la mas fuerte" apoyandose en que la tabla del 3311 daba
   > 1000/2000/2700/4750/6800/24400, "exactamente lo que la propia pagina
   > notifico en pantalla". Por la mañana se creyo que eso era falso y que el
   > X8 Pro usaba solo `Pu()`; por la noche, abriendo la web con los bytes
   > delante, se vio que **la pagina LEE con la tabla y ESCRIBE con `Pu()`**,
   > las dos cosas.
   >
   > Asi que el ancla nunca estuvo del todo mal: la pagina si muestra los
   > valores de la tabla. Lo que estaba mal era llamarla "la mas fuerte", porque
   > **no separa las alternativas** — para lo unico que sirve de verdad es para
   > fijar el **offset** del campo, que es para lo que se usa aca. Cual de las
   > dos formulas corresponde al dpi real del sensor sigue sin saberse. Ver
   > `dpi.py` y `bitacora.md`.

`Dpi_Y_setting` **estuvo** sin confirmar -en la primera captura venia casi todo
en cero- y **quedo confirmado**: trae un `01` en el indice 5, que
es justo el byte alto que hace falta para que el nivel 6 de 40000. Si el campo
empezara un byte antes o despues, ese `01` caeria en el nivel 5 o en el 7 y los
valores no darian lo que muestra la pagina. `CAMPOS_SIN_CONFIRMAR` quedo vacio
desde entonces; ver la nota en `estructuras.py`.

#### Cual nivel esta EN USO: `Current_Dpi_level_flag`

Es el otro campo de cmd 4 que el driver oficial escribe de verdad, y **no es
cuanto vale un nivel sino cual esta seleccionado**. En las 53 escrituras
capturadas toma **seis valores distintos, 1 a 6**, que es toda la barrida de
los niveles encendidos.

La prueba es la mas fuerte que da el proyecto, la misma forma que el reposo
corto: **86 pares de escrituras reales que difieren solo en el byte 22 y el
checksum interno**, varios dentro de la misma captura —`soft-todo.pcap` manda
nivel 3 a t+862.96 y nivel 1 a t+865.24, con 2.28 s entre medio, que es el
usuario tocando el control—. `escribir_nivel_activo()` convierte una en la otra
byte a byte, en las dos direcciones (`test_escribir_nivel_activo`).

**Y es el unico campo del mouse que se ve encenderse.** Los ocho
`Dpi_level_N_indication_flag` del mismo bloque traen un color cada uno —rojo,
verde, azul, amarillo, cian, magenta, naranja, blanco— y el LED de nivel es lo
unico que prende en este modelo: los bytes de color de cmd 5 **no encienden
nada** (MEDIDO). Asi que cambiar el nivel activo es la **cuarta
verificacion a simple vista** del proyecto, despues del LOD y de los dos
ordenes de la rueda. `color_de_nivel()` saca el color del propio bloque, no de
una tabla nuestra.

Un nivel apagado no se puede poner en uso: el codificador levanta
`NivelApagado` antes de mandar nada. El mouse acusaria `0xC1` igual —es el
mismo agujero que tenia `--funcion macro` sin id— y el fallo se veria recien
al mirar el LED.

#### Lo que de cmd 4 NO se puede escribir, y por que

`dpi_ON_OFF_flag` (cuales de los ocho niveles estan encendidos), los **ocho
colores de indicador** y `Dpi_indication_type` son **constantes en las 53
escrituras capturadas**: `0x3f`, los ocho colores por defecto y `2`. Ningun
cliente oficial los movio nunca delante de una captura.

Sin eso no hay Etapa 2 posible, y la regla del proyecto es que al mouse no se
le manda una secuencia que el driver oficial no haya mandado antes. No es que
falte el codificador: **falta la captura**. Se consiguen apagando un nivel o
cambiando un color de indicador desde el soft nativo en la VM, con usbmon
corriendo.

Lo mismo vale para `lightMode` en cmd 5, que es constante 0 en las 23
escrituras de ese comando.

### La estructura de botones (cmd 8)

Transcripta de `_fe(e)` en `dev/research/webapp/app.js`:

```js
function _fe(e){
  let t=0; const n=63, a=new ArrayBuffer(n), o=new DataView(a);
  o.setUint8(t++,8); o.setUint8(t++,59); o.setUint8(t++,1);
  let i=0;
  Object.values(e).forEach(l=>{ o.setUint8(t++,l[0]);
                                o.setUint8(t++,l[1]);
                                o.setUint8(t++,l[2]); });
  for(let l=3;l<t;l++) i+=o.getUint8(l);
  o.setUint8(t++,(i&65280)>>8); o.setUint8(t++,i&255);
  return new Uint8Array(a);
}
```

`fixed = 8`, `sizeTotalData = 59` —el mismo `0x3b` que la tabla del binario— y
**tres bytes por boton**. El checksum arranca en el byte 3 del buffer, que sobre
`datos` es `datos[1:]`: exactamente lo que ya calculaba `checksum_interno()`.

**Cuantos botones no lo dice el bundle** (`_fe` itera sobre las claves que le
pasen), pero lo dice el bloque, y sin holgura: 57 B = 1 `profileId` + 18·3 + 2
de checksum. **Dieciocho slots exactos, sin relleno.**

El bloque de fabrica, decodificado:

| slot | bytes | funcion |
| --- | --- | --- |
| 1 | `02 00 00` | clic izquierdo |
| 2 | `03 00 00` | clic derecho |
| 3 | `04 00 00` | clic de rueda |
| 4 | `05 00 00` | atras |
| 5 | `06 00 00` | adelante |
| 6 | `0d 00 00` | ciclo de dpi |
| 7 | `3c 00 00` | tecla de modo |
| 8–16 | `01 00 00` | apagado |
| 17 | `0a 00 00` | rueda abajo |
| 18 | `09 00 00` | rueda arriba |

Los codigos salen de dos tablas del bundle: `Rve` (codigo -> nombre, 0..58) y
`sl` (nombre -> tripleta, 61 funciones). `p1` y `p2` van en cero salvo en los
atajos de teclado —`p1` = mascara de modificadores, `p2` = usage HID— y en el
macro (`p2` = id); eso **esta capturado y no solo leido**: en `soft-todo.pcap`
hay bloques con `11 08 07` y `11 0a 16`, que son `FUN_SHOW_DESKTOP:[17,8,7]` y
`FUN_SCREEN_CAPTURE:[17,10,22]` byte a byte.

**El codigo 60 (`FUN_MODE_KEY`), que el mouse trae de fabrica en el slot 7,
esta en `sl` y no esta en `Rve`.** O sea que un bloque sin tocar ya contiene un
codigo que la tabla de nombres de la pagina no cubre.

### El atajo de teclado, entero

`p1` es el byte de modificadores de un teclado HID y `p2` el usage de la tecla:

    p1   bit 0 ctrl   bit 1 shift   bit 2 alt   bit 3 win     (los izquierdos)
    p2   usage HID de la pagina 0x07:  a = 4 ... z = 29, 1 = 30 ... 0 = 39,
         enter 40, esc 41, f1 58 ... f12 69, f13 104 ... f24 115, y el resto

Las 111 teclas salen de `keyMap` en `_w()` (`app.js`), y el mapa de bits
**cierra con las veinte entradas de codigo 17 de `sl`**, que son atajos
conocidos de Windows: `FUN_COPY:[17,1,6]` = Ctrl+C, `FUN_CLOSE_WINDOWS:[17,4,61]`
= Alt+F4, `FUN_BROWSER_FAVORITES:[17,3,18]` = Ctrl+Shift+O,
`FUN_SCREEN_CAPTURE:[17,10,22]` = Win+Shift+S. Veinte coincidencias
independientes sobre cuatro bits.

Los **cuatro modificadores derechos** del estandar (`0x10`..`0x80`) no aparecen
en ninguna de las veinte, en ningun bloque capturado ni en el dialogo del soft
—que ofrece cuatro—, asi que `escribir_atajo()` los rechaza. Y `11 00 00` —el
`FUN_SHORTCUT` del bundle, sin tecla— es el mismo agujero que el macro con
id 0: el mouse acusa `0xC1` y el boton queda muerto.

### Una falsa alarma que conviene no repetir

`sl` declara `FUN_SCROLL_UP:[10,0,0]` y `FUN_SCROLL_DOWN:[9,0,0]`, y `Rve` dice
`9 = rueda arriba`, `10 = rueda abajo`. Parece el cuarto caso del patron de
I-W10 / I-W24 —escribir con una regla y leer con otra— y **no lo es**: el
bundle trae un tercer diccionario donde `FUN_SCROLL_UP` lleva
`label: "ScrollDown"` y `FUN_SCROLL_DOWN` lleva `label: "ScrollUp"`. La
etiqueta compensa, las dos tablas coinciden en que **9 es arriba y 10 es
abajo**, y lo unico equivocado es el nombre de la constante.

### Lo que si es un desacuerdo real

**Los dos clientes oficiales escriben los slots 17 y 18 al reves uno del otro**,
sobre el mismo mouse y los dos por el camino de escritura:

    soft nativo   13 bloques    slot 17 = 0x0a, slot 18 = 0x09
    pagina web     3 bloques    slot 17 = 0x09, slot 18 = 0x0a

Sin excepciones, y con los otros 16 slots iguales. El bloque con el que la web
cierra su captura —con el usuario devolviendo todo a fabrica— queda distinto
del de fabrica **exactamente en esos dos bytes**.

**Los dos lados quedaron MEDIDOS girando la rueda,.** Con el
orden del soft (`0a, 09`) el scroll anda derecho. Y con el de la web (`09,
0a`), escrito en `capturas-w/web-rueda-orden-web.pcap` con solo abrir la
pagina y tocar un boton, **el scroll queda invertido**: esos dos bytes no son
inertes y la pagina oficial rompe la rueda al conectarse. Es la tercera
verificacion a simple vista del proyecto, despues del LOD y del orden del
soft.

### Y ninguno de los dos lee este comando

Los 15 bloques de cmd 8 del bus van en direccion OUT. Cero en IN. No es que
falten lecturas en las capturas: `web-arranque-dpi-y-rate.pcap` trae la
respuesta del mouse para luz y para dpi cuando la pagina se conecta, y ahi no
hay ningun bloque de botones. Escriben desde su propio estado guardado y nunca
releen.

Eso explica que nadie del fabricante haya notado la **inferencia 14** de
`evidencia.md`: lo que el soft escribe en los slots 4-6 (`0d 05 06`) no es lo
que el mouse devuelve al leerlos (`05 06 0d`).


### Escribir botones: el codificador, y por que no puede ser un memcpy

**Cmd 8 entro a `p.WRITABLE`**, con la Etapa 2 cumplida en las
dos variantes que hacen falta. El punto de partida es una lectura real de este
mouse y los dos puntos de llegada son escrituras reales del driver oficial, de
dos capturas distintas del mismo dia:

| | de | a | resultado |
| --- | --- | --- | --- |
| idempotente | `dev/models/attackshark-x8pro/respaldos/20260910-172258.json` (17:22:58) | `soft-boton4-vuelve-adelante.pcap` (17:21:05) | identico |
| con cambio | el mismo bloque leido, costado-adelante -> macro `0x11` | `soft-macro-asignado.pcap` (18:14:50) | identico |

La segunda importa mas que la primera: reproducir un **cambio**, y no solo la
identidad, es lo que descarta que estemos copiando bytes sin entenderlos.

**Y este comando necesito un codificador de verdad.** Los slots 4, 5 y 6 se
remapean entre escritura y lectura, asi que devolverle al mouse el bloque que
se le leyo —que es con lo que empieza cada Etapa 3— **le rota tres botones**. Y
el checksum interno no lo atrapa: es una suma llana y la permutacion la deja
igual, los dos bloques del A/B traen `0x0079`. Por eso:

- `estructuras.retraducir_botones()` es la escritura idempotente. **No devuelve
  `datos`**: devuelve `datos` traducido, que es distinto y deja al mouse igual.
- `estructuras.escribir_boton()` cambia un slot, en la numeracion de **lectura**.
- `estructuras.escribir_rueda()` va aparte: es el unico lugar del bloque donde
  los dos clientes oficiales se contradicen.

**Dos barandas nuevas**, las dos con test:

- **Siempre queda un clic izquierdo en los botones 1 a 5**
  (`SLOTS_PARA_CLIC_IZQUIERDO`,; el
  valor sale de `dispositivos.Perfil.slots_para_clic_izquierdo`, porque en que
  botones se puede usar comodo un clic depende del chasis). Antes la
  baranda era que el slot 1 no se remapeaba (`SLOT_INTOCABLE`). Ahora es la
  regla que el propio fabricante pone en otros clientes
  -`AtLeastOneButtonMustBeLeftClick`-, limitada a los botones 1 a 5 porque el 6
  y el 7 estan en la base. La cuida `escribir_boton()` sobre el bloque ya
  cambiado, con `SinClicIzquierdo`, y `intercambiar_botones()` cruza dos
  botones en una sola escritura. **Etapa 3 cumplida**; Etapa 2 no
  hay, porque ninguna captura muestra al cliente oficial escribiendo el slot 1.
- **Por el puente no se expone.** `cli.ESCRIBIBLES` sigue siendo `rate` y
  `dpi`. Quien escribe por el puente es la pagina oficial, y ya esta medido que
  su bloque de botones invierte el scroll: permitirselo seria dejar que rompa
  la rueda sin que nadie toque un control. `test_el_puente_ofrece_menos_que_writable`
  lo fija.

Hacia afuera el CLI habla por **nombres**, no por numeros:

```bash
driver/scripts/primera-escritura.py --comando botones --listar-funciones
driver/scripts/primera-escritura.py --comando botones --boton costado-adelante --funcion adelante
driver/scripts/primera-escritura.py --comando botones --rueda derecha
```

Los nombres son `izquierdo`, `derecho`, `rueda`, `costado-atras`,
`costado-adelante`, `dpi` y `modo`. Que `costado-adelante` sea el slot leido 5
esta MEDIDO; el resto sale de la asignacion de fabrica. Elegir cualquiera de
las tres numeraciones —UI del soft, slot escrito, slot leido— seria heredar el
error de otro, igual que hablar en 0/1 en vez de milimetros con el LOD.

## Macros (cmd 9): el bloque que recibe el mouse, MEDIDO

Antes aca decia "cero tramas de cmd 9 en las diez capturas" y el
layout salia solo del bundle. `capturas-w/soft-macro-asignado.pcap` trajo
**cuatro escrituras** —grabar un macro y asignarlo a un boton, que es lo unico
que dispara este comando— y con eso el lado de escritura queda cerrado.

### Son 111 bytes, no 131

En `app.js` hay cuatro constructores de macro y no son el mismo formato: `Zve`
y `e1e` arman 131 bytes, `Qve` y `t1e` arman 111. El chunk del X8 Pro importa
`Zve` (`indexX8Pro-D0yEPypd.js`, `ah as Fe`), pero **al mouse le llegan 111**,
en el layout de la familia de `Qve`.

No es una contradiccion: quien escribio esos bytes fue el **soft nativo de
Windows**, que no es el bundle. Lo que queda medido es que este mouse recibe
111 bytes asi. Que la pagina le mande 131 sigue LEIDO del bundle y sin
capturar; si lo hace, es el cuarto desacuerdo entre los dos clientes oficiales.

```
[0]        9                   fixed
[1]        111                 sizeTotalData (= el largo del bloque)
[2]        id del macro        0x11, y el bloque de botones lo referencia:
                               el slot del boton dice `12 00 11`
[3]        modo de disparo     0, 1 o 2
[4..6]     0
[7]        repeticiones si el modo es 0; si no, 1
[8]        cuantos eventos
[9..]      los eventos, dos bytes cada uno
[109,110]  checksum, sumando desde el byte 3 como todas las demas
```

La diferencia con `Zve` son exactamente los veinte bytes en cero de `[8..27]`:
131 - 20 = 111, y el contador de eventos se corre del byte 28 al 8.

### El camino por bloques, visto correr por primera vez

El bloque no entra en un report de 64 bytes, asi que va partido en dos, tal
como decia el desensamblado del helper (0x40d612): trozos de 0x3b = 59 bytes,
y **el byte 2 deja de ser el opcode y pasa a ser el numero de bloque**.

```
04 40 00  09 6f 11 ...   largo 0x40, bloque 0, 59 bytes de datos + checksum
04 39 01  00 00 ...      largo 0x39, bloque 1, 52 bytes de datos + checksum
```

`protocol.build_write_blocks()` —transcripcion del desensamblado que hasta hoy
no se habia podido contrastar con nada— reproduce **las cuatro escrituras,
identicas, las dos tramas de cada una**. Cubierto por `test_macro_por_bloques`.

Y el dongle trata las dos como **una sola** escritura: acusa `0xC0` despues de
cada trama, pero el `0xC1` —el que dice que el mouse aplico— llega recien
despues de la segunda. En los cuatro casos.

Lo unico que no coincide con el desensamblado son las pausas: el `Sleep(200)`
es del helper de la web, y el soft nativo espera **1.008 s** entre los dos
trozos, que es el mismo intervalo con el que manda todas sus escrituras. Cual
es el minimo no esta medido: nadie fue mas rapido que un segundo.

### Los tres modos de disparo

El byte `[3]` fue **lo unico que cambio** entre las cuatro escrituras: 0, 1, 2
y de vuelta 0, con el checksum interno siguiendolo (`0x0c6d`, `0x0c6e`,
`0x0c6f`, `0x0c6d`). El soft nativo ofrece tres opciones y son las mismas tres
del chunk del X8 Pro, que hace `S.value ? $=0 : M.value ? $=1 : z.value && ($=2)`:

| modo | soft nativo | bundle | |
| --- | --- | --- | --- |
| 0 | "numero de veces a reproducir" (con campo numerico) | `Loop` / `LoopPlayback` | el contador va en `[7]` |
| 1 | "cualquier tecla para detener" | `Automatic` / `StopOnAnyKey` | **el nombre miente**, ver abajo |
| 2 | "presionar y mantener, soltar para detener" | `Press` / `HoldToPlay` | |

**El nombre del modo 1 no describe lo que hace** (MEDIDO, 2026-09-20, cuatro
corridas iguales con un macro de tres eventos asignado a un boton): se dispara
al apretar y **sigue despues de soltar**; **una tecla del teclado NO lo
detiene** -se escribe esa tecla y el macro sigue saliendo entremedio-; lo
detiene apretar **cualquier otro boton del mouse**. Por eso `MACRO_MODOS[1]`
dice "otro boton del mouse lo detiene" y no lo que dice el fabricante: la tabla
de arriba es evidencia de lo que dice el bundle, no de lo que hace el firmware.

Que el 0 sea el del contador no depende del orden en que se toco la UI: los
cuatro constructores hacen `n===0 ? setUint8(7,a) : setUint8(7,1)`, o sea que
el modo 0 es el unico que usa el parametro de repeticiones, y es el unico de
los tres con un campo numerico al lado (`min:1, max:255`). Los nombres largos
salen de la pantalla de macros generica (`chunks/index-BJtO3KHt.js`), que lista
los mismos modos en el mismo orden con `triggerValue` 1..4: `LoopPlayback`,
`StopOnAnyKey`, `HoldToPlay`, `StopOnCurrentKey`. El X8 Pro no tiene el cuarto.

### Los eventos

Dos bytes cada uno, `[tiempo | bit de direccion, usageId]`. Los diez de la
captura:

```
0a f1   8a f1   0a f3   8a f3   0a f5   8a f5   0a f4   8a f4   0a f2   8a f2
```

que con la tabla de usageId son los cinco botones del mouse —izquierdo, rueda,
atras, adelante, derecho— cada uno con sus dos direcciones. Es el mismo macro
que se habia leido del archivo `ms_13/macro.data` del soft, asi
que la tabla queda confirmada por segunda vez y ahora contra el bus.

**El tiempo va en milisegundos**, y sale de cruzar el bus con el archivo del
soft: el `.macro` de este macro guarda retardos de **10 ms**
(`soft-nativo.md`) y en el bus el byte es `0x0a` = 10. Pasa tal cual, que
es la rama de `Qve`; con la de `Zve` —decimas de segundo— 10 ms viajaria como
1. Lo que **no** esta probado es la rama de los tiempos largos: arriba de 127
el evento ocupa cuatro bytes y agrega `[t/100, 3]`. **Se decodifica**, con la
regla de `Qve` y marcando los tiempos como inferidos; ver
abajo.

### La rama larga: cuatro bytes por evento (INFERIDA del bundle)

`Qve` en `app.js`, que es el constructor del layout de 111 bytes —el que le
llega a este mouse—, parte los eventos de mas de 127 ms:

```js
let d=h.time;
if(d>127){ let c=d/100; d=d%100;
           _===0 ? (setUint8(r++,d|1), setUint8(r++,m))
                 : (d|=129, setUint8(r++,d), setUint8(r++,m));
           setUint8(r++,c); setUint8(r++,3); s++; continue }
...
l.setUint8(8, e.length+s)
```

Tres cosas salen de ahi:

* el par normal lleva el **resto** de dividir por 100 y detras va un par
  `[centenas, 3]`. El `3` es el marcador y se puede reconocer al leer: no
  colisiona con los usage de teclado HID —que empiezan en 4— ni con los cinco
  de los botones del mouse, que estan en 241..245;
* **el byte 8 cuenta pares de bytes, no eventos** (`e.length+s`, donde `s` son
  los largos). Avanzar de a dos bytes leyendo ese numero funciona; mostrar cada
  par como un evento, no: un macro con un solo evento de 250 ms se veia como
  dos, el segundo con "usage 3";
* y **el bit 0 lo fuerza el bundle en tres de los cuatro casos** (`d|1` con
  direccion 0, `d|129` en la rama larga) mientras el soft nativo no lo pone
  nunca. Si la pagina escribe un macro, los tiempos de la rama larga pueden
  quedar 1 ms corridos: 350 ms viaja como `51 + 3 centenas` y se lee 351.

**Nada de esto esta medido**: no hay ninguna captura con eventos de mas de
127 ms. `describir()` marca esos tiempos con `?` y lo dice.

**Lo que si queda sin medir es cual direccion es cual.** El bit 7 marca una y
la otra va sin bit; el soft manda `0a` donde los constructores del bundle
mandan `d|1`. Por eso el decodificador muestra `dir0`/`dir1` y no
"abajo"/"arriba".

### Y como se ESCRIBE la lista

`escribir_eventos_macro()` y `armar_macro()`. Tres cosas que conviene tener a
la vista, porque las tres son decisiones y no transcripciones:

* **el sitio son 100 bytes**: 109 de datos, menos 7 de cabecera y 2 de
  checksum. Eso da **50 eventos** cortos, o 25 si todos son largos. El byte que
  los cuenta entra hasta 255, asi que el limite se valida contra el sitio y no
  contra el byte: pasarse llenaria el bloque y se comeria el checksum, y que
  hace el mouse con eso **no se midio**;
* **el bit 0 no se fuerza**, ni en la rama corta ni en la larga. Se copia al
  soft nativo, que es el unico de los dos clientes cuya escritura de macro
  esta capturada; el bundle escribiria 351 donde se pidio 350;
* **el checksum se rearma siempre en big-endian**, aunque no cambie ningun
  evento, porque la lectura lo trae al reves.

La Etapa 2 esta cerrada contra el bus: los diez eventos del macro capturado
—los cinco botones, apretados y soltados, 10 ms cada uno— devuelven el bloque
de 111 bytes **identico** al que el soft nativo escribio, y las dos tramas
salen iguales a las de `soft-macro-asignado.pcap`.

### El layout de LECTURA, MEDIDO

El bloque de cmd 9 volvia siempre vacio —`01` y 108 bytes de `0xff`, checksum
valido— y la razon no era que faltara el macro: se leyo con el `0x11`
**asignado a un boton** y volvio igual.

**La lectura de macros lleva un parametro que las demas no tienen: el id.**
Sale de `sendMacroDataCommand(macroId)` (`chunks/index-Bl1gF1oR.js`, llamada
desde `cacheMacroKey`), que arma
`F0 | connectionMethod | deviceNo | 0x09 | macroId`: el quinto byte, que en
todas las otras lecturas de la pagina va en cero, aca es el id. Nosotros
poniamos ahi el **perfil**, porque cmd 9 esta en `CMDS_CON_PERFIL`, o sea que
le pediamos el macro 1 cuando el que existe es el 17.

Con el id en el byte 5 el mouse **devuelve el bloque entero**:

```
04 0c a0 09 6f 11 00 00 00 00 01 39      <- el pedido
04 40 00 09 6f 11 00 00 00 00 01 0a ...  <- la respuesta, en dos bloques
```

`sondear.py --pedir 9 --macro-id N` hace eso, y es una opcion **explicita y
angosta**: el default no cambia, solo la acepta cmd 9, el rango se valida y
todo sigue pasando por `build_read_frame()` (`test_sonda_de_macro_es_angosta`).

### El layout leido es el de escritura, menos dos bytes

Los 111 bytes que devuelve son **identicos** a los que el soft nativo escribe,
con una sola excepcion: **el checksum interno vuelve con los bytes al reves**.

```
escritura   ... 00 00 0c 6d
lectura     ... 00 00 6d 0c
```

La suma es la misma, `0x0c6d`. Lo que cambia es el orden, y es una rareza de
cmd 9: cmd 4, cmd 5 y cmd 8 devuelven su checksum interno en el mismo orden en
que se escribe —por eso `test_etapa2_ida_y_vuelta` y `test_etapa2_botones`
pasan comparando una lectura contra una escritura—.

**Es la baranda de cmd 9**, de la misma familia que la permutacion de slots de
cmd 8: devolverle al mouse el bloque que se le leyo, tal cual, le manda un
checksum invertido. Lo rearma `estructuras.poner_checksum_macro()`, en
big-endian, que es como lo escribe el driver oficial en las cuatro escrituras
capturadas.

`estructuras.parametros_de_macro()` decodifica los dos sentidos e informa cual
de los dos ordenes vio en `checksumOrden`, y `describir()` ya muestra el macro
en la salida de `respaldar.py` y de `leer-captura-usb.py`.

### Escribir macros: el codificador y el camino de dos tramas

`estructuras.escribir_macro()` cambia el **disparo** del macro —el modo y, en
el modo 0, el contador de repeticiones— y rearma el checksum. Toca dos bytes y
el checksum, y nada mas: no graba eventos ni mueve el id.

**Etapa 2, en los dos sentidos y contra el mismo mouse.** El punto de partida
es el bloque que este mouse devolvio y los puntos de llegada son
las cuatro escrituras del soft nativo en `soft-macro-asignado.pcap`:

| | resultado |
| --- | --- |
| idempotente | da byte a byte el bloque escrito por el soft, moviendo **exactamente** los dos bytes del checksum invertido |
| con cambio | los modos 0, 1 y 2 dan byte a byte las tres escrituras del soft, con sus **dos tramas** cada una |

La segunda es la que importa: reproducir un cambio, y no solo la identidad,
descarta que estemos copiando bytes sin entenderlos. Lo sostiene
`test_etapa2_macro`.

**El byte de repeticiones solo es el contador cuando el modo es 0.** Los cuatro
constructores del bundle hacen `n===0 ? setUint8(7,a) : setUint8(7,1)`, asi que
en los otros dos va forzado a 1 y pedir un numero ahi seria pedir algo que el
bloque no puede expresar: el codificador lo rechaza.

**Y el camino de escritura es el unico multi-bloque del proyecto.**
`device.escribir_por_bloques()` manda las dos tramas con la pausa del soft
nativo —**1.008 s, MEDIDA**, no el `Sleep(200)` del helper de la web— y espera
el `0xC1` despues de la ultima; el `0xC0` de la primera **no es un acuse**. Un
reintento reenvia la **secuencia entera**: mandarle el trozo 1 a un mouse que
perdio el 0 le arma un bloque Frankenstein, y el checksum de trama no lo
atrapa porque cada trozo lleva el suyo.

**El backend no tiene este camino y no lo va a tener**
(`backend.SIN_CAMINO_EN_EL_BACKEND`): el techo del puente es mas bajo que
`p.WRITABLE`. Cmd 9 se escribe con `driver/scripts/primera-escritura.py --comando
macro --macro-id N`, que habla con `Device` directo.

**Y la funcion "macro" de un boton necesita su id.** El slot es `[18, 0, id]`;
escribirla con `p2` en cero apunta a un macro 0, que no existe, y **el mouse
acusa `0xC1` igual**, asi que el fallo no se ve hasta apretar el boton. Por eso
`escribir_boton()` lo exige y el CLI pide `--macro-id` (N-W19).

**Y `respaldar.py` los respalda de verdad.** Despues de la tanda normal saca
los ids de los slots de cmd 8 —que los llevan en `p2`— y pide cada macro. Van
en una seccion `macros` aparte, para no tocar la cuenta de "7 de 7" que usa
`primera-escritura.py` como senal de salud; `comparar()` y
`cmds_que_cambiaron()` los miran igual.

## La pagina reescribe todo lo que leyo, y cambiado (MEDIDO)

`capturas-w/web-rueda-orden-web.pcap`, con el usuario tocando **un**
boton. Las cinco lecturas que la pagina hizo al conectarse **contestaron** -las
respuestas estan en el bus-, asi que lo que escribio despues no salio de sus
valores por defecto: salio de haber leido el mouse.

| bloque | el mouse contesto | la pagina escribio |
| --- | --- | --- |
| cmd 4 | `SensitivityX = 0x01`, ripple **ON** | `0x00`, ripple **OFF** |
| cmd 4 | `Double_Flag` `20 00` | `00 20`, que mueve el nivel 6 |
| cmd 5 | reposo 0.5 min, respuesta 18, verde | reposo 1 min, respuesta 8, azul |
| cmd 6 | `0x44` = 1000 Hz | `0x01`, indice 0 |
| cmd 7, cmd 8 | *nunca los leyo* | los escribio igual, con la rueda invertida |

Eso cierra **I-W24** y la **inferencia 13** de `evidencia.md`. Y no es una
discrepancia de presentacion: la pagina apago el ripple sin que nadie tocara
ese control, y su propia UI mostraria "ripple ON" **antes y despues**, porque
lee `SensitivityY === 1` en vez del bit que escribe.

El byte de rate `0x01` es nuevo: indice 0, que no esta en `RATE_HZ` ni entre
los siete observados (`0x14`..`0x74` del soft, `0x11`..`0x77` de la web). **Que
frecuencia deja no se sabe.**

**Consecuencia para el puente**: con `full` + `--permitir-escritura`, cada
bloque que se le habilite a la pagina es un bloque que va a reescribir con esto
adentro. Es el motivo por el que `cli.ESCRIBIBLES` es mas chico que
`p.WRITABLE`, y el que mas peso tiene para dejar de ser un puente.

## Que falta para poder escribir el resto

**Se escriben los cinco de `p.WRITABLE`: rate (cmd 6), dpi y los cuatro
interruptores del sensor (cmd 4), los tres temporizadores y el color (cmd 5),
botones (cmd 8) y macros (cmd 9).** Los cinco tienen la Etapa 2 y la Etapa 3
cumplidas; cmd 9 cerro, apretando el boton: con el
macro en modo 2 se repitio mientras el boton estuvo apretado y se corto al
soltarlo. Lo que queda:

1. **Grabar** un macro -la lista de eventos- sigue sin interfaz, a proposito:
   `escribir_macro()` cambia el disparo, no los eventos, y una API para
   grabarlos se diseña con la aplicacion. De los tres modos de disparo, el 0 y
   el 2 quedaron MEDIDOS apretando el boton -uno para solo tras una vuelta, el
   otro repite mientras este apretado-; el **modo 1** sigue solo con el `0xC1`
   y la relectura.
2. **Modo de despertado (cmd 7): capturado, pero no se puede releer.** Hay dos
   escrituras en el bus con los mismos bytes y `build_write_frame()` las
   reproduce, pero es un solo valor -no hay nada que decodificar- y cmd 7 no
   esta en `READ_SUB` a proposito, asi que no hay Etapa 3 posible: esa empieza
   releyendo.
3. **Confirmar `Dpi_Y_setting`**, que en la unica captura viene en cero.
4. Y la regla de siempre para cualquier comando nuevo: **nunca se le manda al
   mouse una secuencia que no haya mandado antes el driver oficial, verificada
   byte a byte.** Con el corolario que dejo esta semana: **verificar la trama
   no alcanza si el bloque leido no es el que hay que devolver.** Paso con los
   slots de cmd 8 y con el checksum de cmd 9.

`build_write_frame()` y `build_write_blocks()` arman las tramas y estan
cubiertos por `driver/tests/salvaguardas.py`, que ademas verifica que el unico camino
del backend que las usa (`_responder_escritura`) siga chequeando las cuatro
guardas: modo `full`, allowlist `--permitir-escritura`, simulacro y bateria.
