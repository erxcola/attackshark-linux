# Bitacora

Lo que se probo contra el hardware, con resultados. Incluye lo que **no**
funciono, que es la mitad util.

**Las entradas no se editan despues de escritas**, ni siquiera cuando lo que
dicen resulta incompleto: cuando una medicion se corrige, la correccion va en
una entrada nueva que cita a la vieja. Por eso hay afirmaciones aca que
despues cambiaron —y por eso se puede ver como cambiaron—. El estado vigente
esta en [`protocolo.md`](protocolo.md) y [`evidencia.md`](evidencia.md).

La unica reescritura que hubo fue una pasada de limpieza que le saco a todo el
archivo **las fechas y los datos personales**, sin tocar ninguna medicion ni
ninguna conclusion. El orden de las entradas es el orden en que pasaron las
cosas, y es lo unico cronologico que queda.

Algunas entradas mencionan `docs/fase2.md`, `AUDITORIA.md`,
`INFORME-AUDITORIA-VIVO.md` o los reportes de la Etapa W. Esos documentos se
retiraron: el metodo quedo en [`metodo.md`](../../../docs/metodo.md), la clasificacion de la
evidencia en [`evidencia.md`](evidencia.md), y los reportes de la Etapa W
junto a sus capturas, en `capturas-w/`.

## Indice

- [Fase 0: el transporte funciona](#fase-0-el-transporte-funciona)
- [udev: dos trampas](#udev-dos-trampas)
- [Fase 1: el canal esta vivo en los dos sentidos](#fase-1-el-canal-esta-vivo-en-los-dos-sentidos)
- [El binario del helper resuelve el framing](#el-binario-del-helper-resuelve-el-framing)
- [El enlace 2.4 GHz pierde pedidos](#el-enlace-24-ghz-pierde-pedidos)
- [El byte de perfil, y por que costo encontrarlo](#el-byte-de-perfil-y-por-que-costo-encontrarlo)
- [Fase 1 completa, punta a punta](#fase-1-completa-punta-a-punta)
- [Punto de partida para la fase 2 (escrituras)](#punto-de-partida-para-la-fase-2-escrituras)
- [El Report ID 3 es un canal de notificaciones](#el-report-id-3-es-un-canal-de-notificaciones)
- [Fuga de canales al reconectar](#fuga-de-canales-al-reconectar)
- [Los DPI, validados contra una fuente independiente](#los-dpi-validados-contra-una-fuente-independiente)
- [La tasa de reporte real](#la-tasa-de-reporte-real)
- [Cierre de los hallazgos de las dos auditorias](#cierre-de-los-hallazgos-de-las-dos-auditorias)
- [Fase 2: el formato de escritura, resuelto](#fase-2-el-formato-de-escritura-resuelto)
- [El `sub` tenia nombre, y las estructuras aparecieron enteras](#el-sub-tenia-nombre-y-las-estructuras-aparecieron-enteras)
- [Etapa W: las capturas de Windows, revisadas](#etapa-w-las-capturas-de-windows-revisadas)
- [Los artefactos de la Etapa W, verificados de primera mano](#los-artefactos-de-la-etapa-w-verificados-de-primera-mano)
- [Las respuestas largas venian truncadas y nadie se habia dado cuenta](#las-respuestas-largas-venian-truncadas-y-nadie-se-habia-dado-cuenta)
- [La primera escritura desde Linux](#la-primera-escritura-desde-linux)
- [El byte de report rate, medido](#el-byte-de-report-rate-medido)
- [A 8000 Hz el canal de configuracion se cae, y el mouse con el](#a-8000-hz-el-canal-de-configuracion-se-cae-y-el-mouse-con-el)
- [La respuesta llegaba y no había nadie esperándola](#la-respuesta-llegaba-y-no-habia-nadie-esperandola)
- [El mouse cambió de frecuencia porque Linux se lo pidió](#el-mouse-cambio-de-frecuencia-porque-linux-se-lo-pidio)
- [Repaso de documentación, y un byte que no cuadra](#repaso-de-documentacion-y-un-byte-que-no-cuadra)
- [La vuelta, y el ciclo cerrado](#la-vuelta-y-el-ciclo-cerrado)
- [El camino de escritura de dpi, y dos cosas que no esperaba](#el-camino-de-escritura-de-dpi-y-dos-cosas-que-no-esperaba)
- [El mouse cambió de DPI porque Linux se lo pidió](#el-mouse-cambio-de-dpi-porque-linux-se-lo-pidio)
- [Medir el DPI con una regla no funciona](#medir-el-dpi-con-una-regla-no-funciona)
- [La página lee con una fórmula y escribe con otra](#la-pagina-lee-con-una-formula-y-escribe-con-otra)
- [Un acuse que se perdía en la pausa, y una iluminación que no estaba bloqueada](#un-acuse-que-se-perdia-en-la-pausa-y-una-iluminacion-que-no-estaba-bloqueada)
- [El mouse aceptó el color, y no pasó nada](#el-mouse-acepto-el-color-y-no-paso-nada)
- ["LOD / parámetros" no es un comando: son tres](#lod-parametros-no-es-un-comando-son-tres)
- [Un instrumento para lo que no se ve](#un-instrumento-para-lo-que-no-se-ve)
- [El mouse se durmió cuando se lo pedimos, y de paso apareció un estado que no sabíamos que existía](#el-mouse-se-durmio-cuando-se-lo-pedimos-y-de-paso-aparecio-un-estado-que-no-sabiamos-que-existia)
- [El X8 Pro tiene dos temporizadores de reposo, y el que faltaba explica los 88 segundos](#el-x8-pro-tiene-dos-temporizadores-de-reposo-y-el-que-faltaba-explica-los-88-segundos)
- [El corte cayó a los 630 segundos, que era la predicción](#el-corte-cayo-a-los-630-segundos-que-era-la-prediccion)
- [El reposo corto mueve el escalón, y los timers están anidados](#el-reposo-corto-mueve-el-escalon-y-los-timers-estan-anidados)
- [La página oficial lee mal los interruptores del sensor](#la-pagina-oficial-lee-mal-los-interruptores-del-sensor)
- [El LOD escrito, y un bug que reventó después de escribir](#el-lod-escrito-y-un-bug-que-revento-despues-de-escribir)
- [El LOD se verificó a simple vista, y el arreglo del informe aguantó](#el-lod-se-verifico-a-simple-vista-y-el-arreglo-del-informe-aguanto)
- [Los botones estaban capturados desde el principio](#los-botones-estaban-capturados-desde-el-principio)
- [El botón físico confirmó el remapeo, y la rueda quedó medida](#el-boton-fisico-confirmo-el-remapeo-y-la-rueda-quedo-medida)
- [El A/B cierra la inferencia 14, y aparecen los archivos del soft](#el-ab-cierra-la-inferencia-14-y-aparecen-los-archivos-del-soft)
- [Macros decodificado, la rueda cerrada, y el mouse a 8 kHz](#macros-decodificado-la-rueda-cerrada-y-el-mouse-a-8-khz)
- [El mouse volvió, y el script se contradecía solo](#el-mouse-volvio-y-el-script-se-contradecia-solo)
- [Cmd 8 entra a WRITABLE, y el macro nunca se perdió](#cmd-8-entra-a-writable-y-el-macro-nunca-se-perdio)
- [La Etapa 3 de cmd 4 y de cmd 8, y por qué cmd 9 vuelve vacío](#la-etapa-3-de-cmd-4-y-de-cmd-8-y-por-que-cmd-9-vuelve-vacio)
- [El último bloque del modelo de datos: cmd 9 se lee con el id](#el-ultimo-bloque-del-modelo-de-datos-cmd-9-se-lee-con-el-id)
- [La primera escritura de macros, y el camino de dos tramas contra el hardware](#la-primera-escritura-de-macros-y-el-camino-de-dos-tramas-contra-el-hardware)
- [El botón apretado cerró cmd 9, y el chat sirvió de contador](#el-boton-apretado-cerro-cmd-9-y-el-chat-sirvio-de-contador)
- [La primera capa de la aplicación, sacada de un script](#la-primera-capa-de-la-aplicacion-sacada-de-un-script)
- [Un macro de 250 ms se leía como dos eventos](#un-macro-de-250-ms-se-leia-como-dos-eventos)
- [El último parámetro que faltaba, y los que no se pueden escribir](#el-ultimo-parametro-que-faltaba-y-los-que-no-se-pueden-escribir)
- [La documentación pasada a limpio](#la-documentacion-pasada-a-limpio)
- [El LED obedeció, y el propio mouse confirmó el campo](#el-led-obedecio-y-el-propio-mouse-confirmo-el-campo)
- [Los colores de nivel sí se pueden cambiar, y el soft nativo tiene el diálogo](#los-colores-de-nivel-si-se-pueden-cambiar-y-el-soft-nativo-tiene-el-dialogo)
- [El selector de color no está en la UI, y por qué la lectura del binario no alcanzaba](#el-selector-de-color-no-esta-en-la-ui-y-por-que-la-lectura-del-binario-no-alcanzaba)
- [A 8 kHz se puede ESCRIBIR: lo que faltaba estaba en una captura vieja](#a-8-khz-se-puede-escribir-lo-que-faltaba-estaba-en-una-captura-vieja)
- [Las siete tasas, y un byte que nadie escribió nunca](#las-siete-tasas-y-un-byte-que-nadie-escribio-nunca)
- [Por qué falla el respaldo a 8 kHz, y qué se puede hacer](#por-que-falla-el-respaldo-a-8-khz-y-que-se-puede-hacer)
- [La frontera está en 1000 Hz, no en 8000](#la-frontera-esta-en-1000-hz-no-en-8000)
- [El `0xC1` no dice que el mouse aplicó nada](#el-0xc1-no-dice-que-el-mouse-aplico-nada)
- [Dieciséis acuses y ni un cambio: no es la insistencia](#dieciseis-acuses-y-ni-un-cambio-no-es-la-insistencia)
- [Cuatro hipótesis menos, y una baranda que no se podía leer](#cuatro-hipotesis-menos-y-una-baranda-que-no-se-podia-leer)
- [La página lo bajó por nuestro propio puente](#la-pagina-lo-bajo-por-nuestro-propio-puente)
- [Era un bug nuestro: la trama iba empaquetada dos veces](#era-un-bug-nuestro-la-trama-iba-empaquetada-dos-veces)
- [Las cuatro tasas, medidas, y las dos auditorías contestadas](#las-cuatro-tasas-medidas-y-las-dos-auditorias-contestadas)
- [Configurar a 8 kHz: bajar, hacer y volver](#configurar-a-8-khz-bajar-hacer-y-volver)
- [Configurar a 8 kHz, medido, y la paridad con el soft](#configurar-a-8-khz-medido-y-la-paridad-con-el-soft)
- [La mitad de escritura de la capa de sesión](#la-mitad-de-escritura-de-la-capa-de-sesion)
- [El orquestador: la Etapa 3 entera, sin terminal](#el-orquestador-la-etapa-3-entera-sin-terminal)
- [El estado con nombres propios](#el-estado-con-nombres-propios)
- [El atajo de teclado y los eventos de macro: la paridad, en código](#el-atajo-de-teclado-y-los-eventos-de-macro-la-paridad-en-codigo)
- [La Etapa 3 de los dos codificadores, y el día que se trabó el teclado](#la-etapa-3-de-los-dos-codificadores-y-el-dia-que-se-trabo-el-teclado)
- [La tasa deja de depender de que uno se acuerde](#la-tasa-deja-de-depender-de-que-uno-se-acuerde)
- [La deuda técnica, cerrada, y el bug que la estaba escondiendo](#la-deuda-tecnica-cerrada-y-el-bug-que-la-estaba-escondiendo)
- [Las auditorías, revisadas antes de la interfaz](#las-auditorias-revisadas-antes-de-la-interfaz)
- [Lo que le faltaba a la biblioteca para la interfaz](#lo-que-le-faltaba-a-la-biblioteca-para-la-interfaz)
- [El perfil declarativo, y de quién son los 47 modelos](#el-perfil-declarativo-y-de-quien-son-los-47-modelos)
- [El byte de estado de batería: 3 es cargando, y por cable a la PC el mouse se calla](#el-byte-de-estado-de-bateria-3-es-cargando-y-por-cable-a-la-pc-el-mouse-se-calla)
- [Con el mouse rápido no se podía configurar nada, y la ventana se colgaba](#con-el-mouse-rapido-no-se-podia-configurar-nada-y-la-ventana-se-colgaba)
- [Cómo comprobar si el firmware acepta cambiar los colores de DPI](#como-comprobar-si-el-firmware-acepta-cambiar-los-colores-de-dpi)
- [El esquema de botones y el cambio de idioma, sin tocar el mouse](#el-esquema-de-botones-y-el-cambio-de-idioma-sin-tocar-el-mouse)
- [La ventana entera en tres idiomas, el idioma que se recuerda, y el esquema con la forma del X8 Pro](#la-ventana-entera-en-tres-idiomas-el-idioma-que-se-recuerda-y-el-esquema-con-la-forma-del-x8-pro)
- [La ayuda dice qué es cada parámetro, y la pantalla deja de citar evidencia](#la-ayuda-dice-que-es-cada-parametro-y-la-pantalla-deja-de-citar-evidencia)
- [El clic izquierdo se reasigna, con la regla del fabricante, y los botones se leen claro](#el-clic-izquierdo-se-reasigna-con-la-regla-del-fabricante-y-los-botones-se-leen-claro)
- [Las tres corridas contra el mouse, y el modelo deja de ser de un solo mouse](#las-tres-corridas-contra-el-mouse-y-el-modelo-deja-de-ser-de-un-solo-mouse)
- [Una auditoría externa encontró cuatro cosas del trabajo de la mañana](#una-auditoria-externa-encontro-cuatro-cosas-del-trabajo-de-la-manana)
- [Dónde está el mouse: el bus se mira entero, y el cable se nombra](#donde-esta-el-mouse-el-bus-se-mira-entero-y-el-cable-se-nombra)
- [El modo cable: lo que el mouse declara, y lo que todavía no se sabe](#el-modo-cable-lo-que-el-mouse-declara-y-lo-que-todavia-no-se-sabe)
- [El repositorio se parte en dos: el programa y cómo se supo](#el-repositorio-se-parte-en-dos-el-programa-y-como-se-supo)
- [El cable, leído del helper: la web sí configura por cable](#el-cable-leido-del-helper-la-web-si-configura-por-cable)
- [Las capturas del cable: la Etapa 2 pasa, y el rate es el otro nibble](#las-capturas-del-cable-la-etapa-2-pasa-y-el-rate-es-el-otro-nibble)
- [El canal por cable: la misma cara que el dongle, otro protocolo adentro](#el-canal-por-cable-la-misma-cara-que-el-dongle-otro-protocolo-adentro)
- [Una relectura podrida se reescribió sola, y el cmd 5 quedó roto](#una-relectura-podrida-se-reescribio-sola-y-el-cmd-5-quedo-roto)
- [Cada modelo, dentro de `models/`, y dos auditorías más](#cada-modelo-dentro-de-models-y-dos-auditorias-mas)
- [La nota de retomar, archivada entera](#la-nota-de-retomar-archivada-entera)
- [El proyecto pasa a llamarse LinShark](#el-proyecto-pasa-a-llamarse-linshark)
- ["Quedarse con la tasa" le ganaba a la lectura](#quedarse-con-la-tasa-le-ganaba-a-la-lectura)
- [Un byte de tasa que no se entiende dejaba a la ventana afuera](#un-byte-de-tasa-que-no-se-entiende-dejaba-a-la-ventana-afuera)

---
## Fase 0: el transporte funciona

Brave abre `ws://localhost:10086` desde la pagina HTTPS sin ninguna
ceremonia: no hace falta TLS, ni flags, ni tocar contenido mixto. Chromium
trata `localhost` como origen confiable.

La web nos acepto como helper valido con solo dos mensajes (`0305` y el
paquete de presencia), salio de la pantalla de "descarga el driver", entro a
`/ATTACKSHARK/factoryX8Pro` y arranco a pedir datos:

```
f0 83 08 0b 00   LEER version de firmware
f0 83 08 06 00   LEER report rate
f0 83 08 05 00   LEER iluminacion
f0 83 08 04 00   LEER dpi
```

Queda confirmado en vivo el formato `[0xF0, connectionMethod, deviceId, cmd, sub]`.

El "cargando" que queda colgado es el overlay esperando esas cuatro
respuestas, que el stub no sabe dar. Esperado.

## udev: dos trampas

La regla obvia no funciona. Ver los comentarios en
`udev/70-attackshark-x8pro.rules`. Resumen:

1. En una misma regla, todos los `ATTRS{}` tienen que matchear en el **mismo**
   dispositivo padre. `bInterfaceNumber` esta en la interfaz USB y
   `idVendor`/`idProduct` en el dispositivo USB: no se combinan.
2. `KERNELS=="*:1.2"` como reemplazo tampoco matchea.
3. Un archivo `99-` llega tarde para `uaccess`: el tag lo consume
   `73-seat-late.rules`. Hay que ordenar antes.

Lo que si funciona es matchear por `ENV{}`, porque el builtin `usb_id` deja
`ID_VENDOR_ID`, `ID_MODEL_ID` e `ID_USB_INTERFACE_NUM` sobre el propio
dispositivo hidraw, y corre en `60-persistent-hidraw.rules`.

Ojo tambien: despues de instalar la regla hace falta
`udevadm trigger --action=add`. Con la accion `change` por defecto los
permisos del nodo vivo no se reaplican.

Resultado: `/dev/hidraw5` queda `crw-rw----+ root input` con ACL para el
usuario, y las otras tres interfaces siguen `root:root 0600`.

## Fase 1: el canal esta vivo en los dos sentidos

### El mouse habla solo

Cada ~4 segundos manda por **Report ID 3** (coleccion vendor 0xFF00, 4 bytes):

```
08 40 01 64
^^ ^^ ^^ ^^
|  |  |  nivel de bateria = 0x64 = 100
|  |  estado de bateria
|  la marca 0x40 que la pagina exige en el paquete de presencia
deviceId 0x08 = X8Pro
```

Es la materia prima del paquete de presencia. El helper le antepone
`[connectionMethod, 0x01]` y le queda la variante de 6 bytes que espera la
pagina:

```
[conn, 0x01, 0x08, 0x40, 0x01, 0x64]
```

O sea que `deviceId`, la marca y la bateria son **datos reales del hardware**;
lo unico que el helper inventa es el `connectionMethod` y el `0x01`.

### El mouse contesta, pero rechaza todo lo que le mandamos

Escribiendo por Report ID 4, el mouse responde siempre lo mismo:

```
06 c0 00 00 ca
```

Framings probados, todos con el mismo resultado:

| Payload enviado                        | De donde salio                        | Respuesta |
| -------------------------------------- | ------------------------------------- | --------- |
| `0c 0b 00`                             | reconstruido de `sendLegacyCommand`   | `06 c0 00 00 ca` |
| `0c 07 08 00 00 00 00 00`              | textual de `sendWakeupModeReadCommand`| `06 c0 00 00 ca` |
| `0a 00 0c 07 08 00 00 00 00 00`        | lo anterior con el prefijo `[len, 0]` de `Vve` | `06 c0 00 00 ca` |
| `00 00 00 00 00 00 00 00`              | todo ceros, control inerte            | `06 c0 00 00 ca` |

Que el payload inerte devuelva exactamente lo mismo prueba que **es un
rechazo generico**, no una respuesta.

### Pero el rechazo nos regala el checksum

El paquete de rechazo cumple la regla de la segunda suma de `co()`/`Vve()`,
la que arranca con `i = 4`:

```
06 c0 00 | 00 ca

0x06 + 0xc0 + 0x00 = 0xC6
0xC6 + 4            = 0xCA        <- los ultimos 2 bytes, big-endian
```

Asi que el formato de trama del dispositivo lleva un trailer de 2 bytes con
`4 + suma(bytes anteriores)`, big-endian. Nuestros envios van sin el, y por
eso los rechaza.

En `co()` ademas hay un **primer** checksum sobre el subrango de datos, dos
bytes en cero, y recien despues el checksum total:

```
[cmd, size, profileId, ...datos..., chk1Hi, chk1Lo, 0x00, 0x00, chk2Hi, chk2Lo]
                                    \_ suma de [3..o) _/          \_ 4+suma[0..o) _/
```

`Vve()` es lo mismo corrido 2 posiciones, con `[totalLen, 0x00]` al frente y
el primer checksum sobre `[5..o)`.

### Donde quedamos

Sabemos: el canal, los report IDs, el formato de presencia, el algoritmo de
checksum y la forma general de la trama. Falta la transformacion exacta que
hace el helper entre lo que manda la pagina y lo que va al cable, sobre todo
para los comandos de **lectura**, que en la pagina viajan sin checksum.

Seguir adivinando framings es fuzzing sobre el endpoint vendor de un mouse, y
eso no se hace. La fuente de verdad es el binario del helper.

## El binario del helper resuelve el framing

`innoextract` (el que trae Lutris en
`~/.local/share/lutris/runtime/innoextract-1.9-linux`, no hizo falta instalar
nada) saco el payload de `WebDriverSetup.exe` sin ejecutar nada de Windows.

`WebDriver.exe` es un MFC/MSVC PE32 i386 que usa `hidapi.dll`. Desensamblando
con `objdump` y ubicando los sitios de llamada a `hid_write` via la IAT que
saco `pefile`, aparecieron **dos tamanos de escritura**: `0x41` (65 bytes) y
`0x0c` (12 bytes). Los de 12 son los comandos de lectura, y de ahi salio el
formato completo. Detalle en `protocolo.md`.

Lo que hacia imposible adivinarlo:

1. El paquete es de **12 bytes**, no un report entero relleno.
2. Lleva un **checksum** al final que **incluye el byte del Report ID**.
3. Cada comando tiene un **`sub` fijo que la pagina nunca manda** (siempre
   manda 0) y que el helper pone de una tabla interna.

Nuestro constructor `build_read_frame()` reproduce el paquete del binario
byte por byte, checksum incluido:

```
del binario:  04 0c a0 0c 0a 00 00 00 00 00 00 c6
del codigo:   04 0c a0 0c 0a 00 00 00 00 00 00 c6
```

Y el mouse contesta:

```
-> 04 0c a0 0b 08 00 00 00 00 00 00 c3      (leer version de firmware)
<- 04 0d 00 0b 08 08 00 83 01 05 00 00 b5   (respuesta, checksum ok)
```

> **Ojo con esta traza (anotado).** El bloque de version dice
> `...01 05 00`, y los ocho respaldos tomados por hidraw dicen `...01 01 00`.
> Ver la entrada sobre el byte de version: el dato que vale
> es el de los respaldos.

## El enlace 2.4 GHz pierde pedidos

Los tiempos son deterministas:

- respuesta buena: **~0.74 s**
- NAK del dongle (`06 c2 00`): **~2.10 s**

La tasa de exito depende de si el mouse se esta moviendo. Medido con
`medir-enlace.py`, que lee el nodo de eventos del propio mouse y clasifica
cada pedido:

| Estado del mouse | Respondieron |
| ---------------- | ------------ |
| moviendose       | **58/61 = 95%** |
| quieto           | **5/10 = 50%**  |

(Una primera corrida dio 13/23 = 57% pero sin una sola muestra en
movimiento, asi que no probaba nada. La segunda, con movimiento en la primera
mitad, es la que cierra la correlacion.)

Es el ciclo de trabajo de la radio: con el mouse quieto despierta menos
seguido y se pierde la mitad de los pedidos.

Consecuencias de diseno:

* **Hay que reintentar.** Con 50% por intento en el peor caso, 8 reintentos
  dan 99.6%.
* Conviene reintentar **apenas llega el NAK** a los 2.10 s, en vez de esperar
  un timeout largo, porque el exito siempre llega a los 0.74 s. Se hace
  corriendo una carrera entre la respuesta y el NAK.
* No hay que interpretar un solo NAK como "el mouse no soporta este comando".

## El byte de perfil, y por que costo encontrarlo

Con el framing ya correcto, `version` e `iluminacion` respondian pero
`report rate` y `dpi` fallaban **siempre**, las 8 veces. Eso no es el enlace.

La pista estaba en la extraccion de los templates: en esos comandos el byte 5
se cargaba **desde un registro** en vez de ser una constante. Volviendo al
desensamblado:

```asm
mov al, BYTE PTR [ebp+0x8]      ; argumento de la funcion
inc al                          ; +1
mov BYTE PTR [ebp-0xd3], al     ; buffer[5]
```

Es el **numero de perfil, 1-based**. Nosotros mandabamos 0.

Lo desagradable del sintoma: con perfil 0 el mouse **ignora el comando en
silencio**. El dongle acepta el pedido igual y despues manda su NAK a los
2.10 s, que es exactamente lo mismo que se ve cuando se pierde el paquete por
radio. Un error de formato disfrazado de problema de enlace.

## Fase 1 completa, punta a punta

Con el puente en `--mode read` contra el mouse real, la pagina pide y recibe:

```
<- f083080b00     LEER version      -> 83080b08 080083010500
<- f083080600     LEER report rate  -> 83080609 0144bb00000000
<- f083080500     LEER iluminacion  -> 8308050f 010003a800ff00010401af0000
<- f083080400     LEER dpi          -> 83080438 0101013f2000172f3f6f9f8f...
```

Todo con checksum validado. El `report rate` vuelve como `01 44 bb`: perfil 1,
valor 0x44 (que es `rateRadio<<4 | rateRadio`, o sea indice 4) y su
complemento 0xBB, el mismo patron `~valor` que usa `xt()` en el JavaScript.

Ademas la respuesta de version trae `08 00 83 01 05 00`, donde el tercer byte
es **0x83**, el mismo valor que venimos declarando como `connectionMethod`.

> **Ojo con el quinto byte (anotado).** Aca figura `05` y los
> ocho respaldos por hidraw dicen `01`. Lo que se discute abajo es el `0x83`,
> que no cambia; el `05` quedo marcado como sospechoso. Ver la entrada sobre
> el byte de version.

**Ojo con esa coincidencia, que casi nos come.** Primero se escribio aca que
"el connectionMethod lo dice el propio hardware". No es asi, y el razonamiento
era circular: el `0x83` del prefijo lo pusimos nosotros al armar el mensaje
para la pagina, y el `0x83` del payload de version es un campo del firmware
que no sabemos que significa. Que coincidan es lo unico MEDIDO. Que ese byte
*sea* el connectionMethod sigue siendo **[INFERIDO]** — es el punto 1 de
`AUDITORIA.md`, y ahi se queda hasta que aparezca el codigo del helper que lo
elige. Es exactamente el mismo patron de falsa confirmacion que el de los DPI
como `(valor+1)*50`, mas abajo.

## Punto de partida para la fase 2 (escrituras)

Los otros 9 sitios de `hid_write` usan largo **0x41 (65 bytes)** y son el
camino de escritura. Misma familia de trama: el checksum se calcula sobre los
bytes 0..61 (vectorizado con SSE y despues un lazo escalar, `cmp ecx,0x3e`) y
se guarda en las posiciones **62 y 63**.

Cuidado con el largo: hidapi en Windows ajusta el buffer al tamano del report,
asi que 65 bytes ahi terminan siendo un report de 64 (1 de Report ID + 63 de
datos, que es lo que declara el descriptor del dongle). En Linux hay que
escribir 64, no 65.

## El Report ID 3 es un canal de notificaciones

Sintoma: la pagina mostraba siempre el nivel de DPI 1 (rojo) aunque el LED
del mouse estuviera en verde, incluso despues de refrescar.

Son **dos cosas distintas**:

1. El `currentDpiLevel` que devuelve el comando de lectura (cmd 0x04, byte
   t[26]) es la configuracion **guardada del perfil**, no el nivel activo.
   Comprobado: leyendo con el LED en verde devuelve exactamente los mismos
   bytes, con el nivel en 1.
2. El nivel en vivo viaja por el Report ID 3, y lo estabamos descartando.

Escuchando el hardware mientras se apretaba el boton de DPI:

```
08 40 01 64    presencia + bateria
08 10 03       cambio de DPI, nivel 3
08 10 02       cambio de DPI, nivel 2
```

O sea que el Report ID 3 **no es solo presencia**: es un canal de
notificaciones con un byte de tipo en la posicion 1.

| tipo | Contenido |
| ---- | --------- |
| 0x40 / 0x41 | `[deviceId, tipo, estadoBateria, nivelBateria]` |
| 0x10        | `[deviceId, tipo, nivelDpi, 0]` — nivel 1-based |

El helper reenvia estas notificaciones anteponiendo `[connectionMethod, 0x01]`,
y quedan los 6 bytes que espera la pagina, con el tipo cayendo justo en `n[3]`,
que es donde el store decide si es presencia o cambio de DPI.

Nuestro bug: forzabamos `0x40` siempre al armar el paquete, asi que las
notificaciones de DPI llegaban disfrazadas de bateria y se descartaban.
Arreglado reenviando el payload tal cual.

## Fuga de canales al reconectar

En el log aparecia cada notificacion **dos veces**. No era el mouse: la
pagina reconecta seguido (recargas, dos pestanas) y `start()` abria otro
`/dev/hidraw` sin cerrar el anterior, dejando varios lectores registrados en
el event loop.

```
16:58:30  pagina conectada + abierto /dev/hidraw5
16:58:40  pagina conectada + abierto /dev/hidraw5   <- sin desconexion en el medio
16:58:42  pagina desconectada
16:58:45  pagina desconectada
```

Arreglado: `start()` cierra la sesion anterior si quedaba uno abierto.

## Los DPI, validados contra una fuente independiente

Primero decodifique los bytes de DPI como `(valor+1)*50`, y me convenci de
que estaba bien porque daba 1200/2400/3200/5600/8000, parecido a los valores
por defecto del store. **Estaba mal.**

La pagina, al cambiar de nivel, manda una notificacion de escritorio. En el
historial de Caelestia (`~/.local/state/caelestia/notifs.json`):

```
Dpi切换至 2000
Dpi切换至 2700
Dpi切换至 4750
Dpi切换至 6800
```

El algoritmo real (`convertBytesToDpi3311`) no es una formula lineal: el byte
es un **indice en una tabla dispersa de 220 entradas**, con un multiplicador
para los niveles marcados como "double". Transcripto en `driver/src/asbridge/dpi.py`.
Con los bytes que leimos del mouse da:

```
1000, 2000, 2700, 4750, 6800, 24400
```

Los cuatro del medio coinciden exactamente con lo que notifico la pagina.

## La tasa de reporte real

Medida con `driver/scripts/medir-polling.py`, que cronometra los `SYN_REPORT` que
llegan al kernel, sin depender del driver ni de la web:

```
12222 muestras, intervalo mediano 1000 us
   875 us   14.3%
  1000 us   68.8%
  1125 us   13.4%
```

1000 Hz reales, con jitter simetrico. Concuerda con lo que leemos por el
canal de configuracion (`rateRadio = 4`) y con lo que muestra la pagina.

El dongle **puede** 8000 Hz (su descriptor declara `bInterval=1` a High
Speed), pero eso es la capacidad del enlace: el mouse viene configurado en
1000 y se sube desde el driver. Tabla de la vista del X8 Pro:

| rateRadio | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
| --------- | - | - | - | - | - | - | - |
| Hz | 125 | 250 | 500 | 1000 | 2000 | 4000 | 8000 |

## Cierre de los hallazgos de las dos auditorias

Al proyecto se le hicieron dos revisiones independientes
(`docs/INFORME-AUDITORIA-VIVO.md` y `auditoría-A.md`) que coincidieron
casi punto por punto. Lo que se arreglo, y por que:

**El bug mas vergonzoso** era el nuestro: `driver/scripts/instalar-udev.sh` corria
`udevadm trigger` sin `--action=add`, que es exactamente la trampa que este
mismo archivo documenta mas arriba y que el README y el AGENTS.md repiten. El
script terminaba diciendo "reglas recargadas" y dejaba al usuario sin permisos
hasta que desenchufaba el dongle.

**Un crash real**: `CMD_WAKEUP` (7) no esta en `READ_SUB`, asi que si la pagina
pedia esa lectura `build_read_frame()` levantaba `KeyError`, nadie lo capturaba
y se caia la conexion WebSocket entera. Ahora hay una excepcion propia
(`ComandoSinSub`) y el puente lo trata como no soportado: loguea y sigue. Se
decidio **no** inventarle la entrada en la tabla: la pagina lo lista con sub 8
y `sendWakeupModeReadCommand()` manda `[12, 7, 8, 0, 0, 0, 0, 0]`, pero eso va
por el camino de escritura y sin checksum, y el cmd 7 no aparece entre los 8
sitios de `hid_write` de 12 bytes del binario. Mezclar los dos framings seria
inventar una trama.

**Barandas que no estaban donde deciamos.** El modo `listen` abria el nodo
`O_RDWR`: la promesa de "no le escribe nada" dependia de un `if`. Ahora se abre
`O_RDONLY` y la sostiene el kernel. Las sondas tenian un `--crudo` que aceptaba
hexadecimal libre y un `--leer CMD SUB` con SUB arbitrario, que salteaban
`build_read_frame()` y con eso la unica garantia del proyecto: se sacaron. El
modo `full` estaba en la CLI aunque rechace todo, y `--hidraw` aceptaba
cualquier nodo, incluido el de la interfaz 2 del mouse **por cable**, que se
abre sin quejarse y habla Feature Reports.

**El puente escuchaba a cualquiera.** Chromium trata `ws://localhost` como
origen confiable y no pide CORS, asi que cualquier pagina abierta en otra
pestana podia hablarle al mouse. Ahora se mira el header `Origin`, que el
JavaScript de una pagina no puede falsificar. Los clientes que no son
navegadores no mandan `Origin` y se dejan pasar a proposito: ya corren en la
maquina del usuario.

Todo esto quedo cubierto por `driver/tests/salvaguardas.py`, que corre sin hardware.

### El 0xC3 costaba 3 segundos

Cuando el dongle contesta `06 c3` ("ocupado", llega si se mandan comandos muy
pegados) el codigo no hacia nada con eso y la espera se comia el timeout
entero, aunque el dongle ya hubiera avisado que ni siquiera acepto el pedido.
Ahora el `0xC3` entra en la misma carrera que la respuesta y el NAK. Se ve en
vivo, en tres lecturas seguidas:

```
<<< 04 06 c3 00 00 cd      ocupado
<<< 04 06 c0 01 00 cb      aceptado   (reintento a los 0.3 s)
<<< 04 0e 00 06 09 01 44 bb ...  respuesta
```

Los "ocupado" llevan su propio tope de reintentos y **no** consumen el
presupuesto de los 8 del enlace: son problemas distintos, uno es que mandamos
muy pegado y el otro es la radio.

### Las cadenas de formato del helper cierran el INFERIDO #2

Buscando strings en `WebDriver.exe` (`strings -a -t x | grep '%02x'`, sha
`0eea3fef…`) aparece toda la familia de mensajes que el helper le manda a la
pagina, escrita literal:

```
8001%02x%02x%02x%02x%02x    8101%02x%02x%02x%02x%02x    (presencia, 7 bytes)
8201%02x%02x%02x%02x%02x    8301%02x%02x%02x%02x%02x
8501%02x%02x%02x%02x%02x    8401%02x%02x%02x%02x        (bluetooth, 6 bytes)

8000%02x  8100%02x  8200%02x  8300%02x  8400%02x  8500%02x   (desconexion)

84%02x0B08%02x%02x          84%02x0C0A%02x%02x%02x%02x       (respuestas)
```

La primera familia (VA `0x60ac0c`, usada en `0x410a89`) confirma que el helper
antepone `[connectionMethod, 0x01]`: era el **INFERIDO #2** y pasa a LEIDO. De
yapa, la variante de bluetooth tiene un `%02x` menos, que explica sola por que
la pagina solo acepta el paquete de 6 bytes cuando el metodo es `0x84`.

La segunda (VA `0x60aa7c`, usada en `0x40c06c` con el campo `[esi+0x418]` del
dispositivo) dice que el paquete de desconexion es
`[connectionMethod, 0x00, deviceId]`. Nosotros mandabamos `0x00` en el primer
byte; la pagina no lo mira, pero se corrigio para no separarse del helper sin
motivo.

La tercera (VA `0x60ac8c`) muestra el rearme `[conn, deviceId, cmd, sub, datos]`
con los sub de la tabla (`0B -> 08`, `0C -> 0A`). Es el camino de bluetooth, no
el del dongle, asi que el **INFERIDO #3** no se cierra, pero queda mucho mejor
respaldado.

Hay un cuarto grupo, `%02x%02x<CMD>F0`, con una cadena por cada uno de los ocho
comandos de lectura (VA `0x60ab94` y vecinas, usadas en `0x40e755`, `0x40ed98`,
`0x412b0c`). Se formatean con dos argumentos y **no se sabe que son**. No se les
asigno ningun significado: queda anotado como pista para la fase 2.

## Fase 2: el formato de escritura, resuelto

Los 9 sitios de `hid_write` con largo `0x41` resultaron ser tres trios
identicos, uno por grupo de `connectionMethod`. La rama general (`0x40d8aa`,
`hid_write` en `0x40d9c5`) arma:

```
04 L 00 | ...N bytes... | chkHi chkLo        con L = N + 5
```

**Misma familia que las lecturas.** El byte 1 es el largo total, el checksum
son los dos ultimos bytes de esos `L` y suma todo lo anterior con el Report ID
incluido. Se verifico con tres largos distintos que aparecen en el binario:
12, 57 y 64. Detalle en `protocolo.md`.

Lo que costaba entender era el `0x41` que se le pasa a `hid_write`: **no es el
largo de la trama**. hidapi en Windows ajusta al tamano del report, que aca es
64. Lo confirma el propio binario, que para el bloque de un report pone
`buffer[1] = 0x40 = 64`. En Linux se escribe 64.

El camino por bloques (macros) usa trozos de 59 bytes, con el numero de bloque
en el byte 2 en lugar del opcode, `Sleep(200)` entre bloques y `Sleep(1000)` al
final. El segundo bloque declara largo `0x39` = 57, y de ahi sale que el
payload de macros mide 111 bytes.

Se implementaron `build_write_frame()` y `build_write_blocks()`. **No hay
ningun camino que las use**: el modo `full` sigue cerrado y hay un test que
falla a proposito si aparecen mencionadas en `backend.py`.

### De yapa: el `sub` no es un subcomando, es un largo

Reconstruyendo la escritura aparecio que el byte que llamabamos `sub` se
comporta como el largo del bloque `[cmd, N, ...datos]`, con `L = N + 5` en las
respuestas. Contra las cuatro lecturas que le hicimos al mouse:

```
comando       sub = N    L = N+5    respuesta real
version         8          13       04 0d 00 0b 08 ...
report rate     9          14       04 0e 00 06 09 ...
iluminacion    15          20
dpi            56          61       04 3d 00 04 38 ...
```

Cuatro de cuatro, con valores bien distintos. Explica ademas por que la pagina
manda siempre `sub = 0`: no sabe el tamano de cada estructura, lo pone el
helper de su tabla.

Ojo igual: **no se vio al binario calcular ese byte**. La aritmetica cierra,
pero que "sea" un largo es interpretacion. No se renombro nada ni se genera el
valor; `READ_SUB` sigue siendo la tabla tal cual salio del desensamblado. Si
en algun momento aparece un comando donde la cuenta no de, esta anotado aca de
donde salio la idea.

### Donde quedamos

Falta el **contenido** de las escrituras, no el formato: hay que capturar con
`--record` que payload manda la pagina por cada control, que se hace con el
backend `stub` y sin que nada llegue al mouse.

## El `sub` tenia nombre, y las estructuras aparecieron enteras

Buscando los constructores de escritura en el bundle (los que le pasan el
payload a `convertDeviceData`) aparecio esto, que cierra de una el hallazgo
anterior:

```js
function co(e) {
  const t = e.sizeTotalData + 5, ...
  a.setUint8(o++, e.fixed);          // el cmd
  a.setUint8(o++, e.sizeTotalData);  // el que llamabamos `sub`
```

El fabricante lo llama **`sizeTotalData`** y el `+5` esta escrito ahi mismo.
Deja de ser interpretacion nuestra: pasa a LEIDO.

Y los objetos con los valores por defecto confirman la tabla que habiamos
sacado del binario, desde una fuente completamente independiente:

```
gw = {fixed: 5, sizeTotalData: 15, profileId: 1, lightMode: 80, ...}   -> READ_SUB[5] = 0x0F = 15
Qt = {fixed: 4, sizeTotalData: 56, profileId: 1, SensitivityX: 0, ...}  -> READ_SUB[4] = 0x38 = 56
```

De paso quedan las dos estructuras enteras, campo por campo y con los nombres
del fabricante. Transcriptas en `driver/src/asbridge/estructuras.py` y verificadas
contra lo que ya le habiamos leido al mouse:

- **Iluminacion**: el color decodificado da (0, 255, 0), el verde que tenia el
  LED cuando se leyo, y el checksum interno recalculado da `0x01af`, que son
  exactamente los dos bytes que trae la captura.
- **DPI**: los ocho campos de color coinciden byte por byte con los defaults
  del bundle, `dpi_ON_OFF_flag` da 63 (tambien el default), y sobre todo los
  `Dpi_X_setting` pasados por `dpi.py` dan **1000, 2000, 2700, 4750, 6800,
  24400**, que es lo que la propia pagina habia notificado en pantalla.

Tres anclas independientes sobre la misma captura. El unico campo que queda
sin confirmar es `Dpi_Y_setting`, que en esa lectura viene casi todo en cero.

`dpi.py` estaba escrito desde la fase 1 pero **no lo llamaba nadie**: ahora
`estructuras.py` lo usa, y las lecturas de la sonda y del puente salen
interpretadas.

Nada de esto habilita escrituras: son transcripciones para leer. El modo
`full` sigue cerrado.

## Etapa W: las capturas de Windows, revisadas

Llegaron `docs/reporteW.md` (WebDriver oficial) y `docs/reporteWsoft.md` (soft
nativo). Lo que se pudo verificar contra el codigo, se verifico.

### Lo que cierran

**`build_write_frame()` reproduce la trama real, byte a byte.** La captura USB
del cambio de report rate hecho por el driver oficial:

```
capturado (w2-rate.pcap)   04 0e 00 06 09 01 44 bb 00 00 00 00 01 21
asbridge                   04 0e 00 06 09 01 44 bb 00 00 00 00 01 21
capturado (w2soft-rate)    04 0e 00 06 09 01 34 cb 00 00 00 00 01 21
asbridge                   04 0e 00 06 09 01 34 cb 00 00 00 00 01 21
```

Dos capturas independientes (la web y el soft nativo, que son dos programas
distintos) y las dos salen identicas a lo que arma nuestro constructor. El
formato de escritura pasa de LEIDO a **MEDIDO**.

Detalle lindo: el checksum del report rate es **siempre** `01 21`, porque el
valor y su complemento suman 0xFF y el resto de la trama es fijo.

**El bloque de dpi del soft es el mismo que leemos nosotros.** La captura del
soft empieza `01 01 01 3f 20 00 17 2f 3f 6f 9f 8f`, que es exactamente lo que
devuelve `driver/scripts/sondear.py --pedir 4` en esta maquina. La estructura que
sacamos del bundle queda confirmada contra el driver oficial.

**INFERIDO #1 y #3 cerrados.** La presencia real del helper es
`83 01 03 08 40 01 64` (anuncia `0x83`) y la respuesta de version es
`83 08 0b 08 08 00 83 01 05 00 00 b5`.

### Dos lecturas equivocadas de los reportes

1. **`0e 00` no es un `uint16` little-endian.** Es `[largo][opcode]`. Da lo
   mismo en las escrituras de un solo bloque **por casualidad**, porque el
   opcode de escritura es `0x00`. Se cae en los otros dos casos que ya
   teniamos medidos: la lectura de version es `04 0c a0 ...`, que como uint16
   LE seria 40972; y el segundo bloque de macros es `04 39 01`, que seria 313
   en vez de largo 57 y bloque 1.
2. **`01 44 bb` no es "valor + checksum".** Es `profileId=1`, `valor=0x44` y
   `complemento=0xbb`. El checksum de la trama son los dos ultimos bytes,
   `01 21`.

### Cuatro cosas que los reportes no notaron

1. **El helper recorta el payload.** El mensaje WebSocket del rate es
   `83 08 06 09 01 33 cc` + **ocho bytes de relleno en cero**, o sea 15 bytes
   de payload, pero la trama que sale al mouse usa solo los **9** primeros,
   que es lo que dice el `sizeTotalData` del byte 1. Confirma el
   `memcpy(&buffer[3], mensaje+2, mensaje[3])` que habiamos leido del
   desensamblado.
2. **El helper le pasa a la pagina el checksum de la trama; nosotros no.** La
   respuesta oficial es `[conn, dev]` + la trama **desde el byte 3 hasta el
   final**, checksum incluido. La nuestra corta antes y queda 2 bytes mas
   corta. La pagina tiene handlers que exigen `n.length >= 10`, y nuestra
   respuesta de version mide exactamente 10: **estamos justo en el limite**.
   Conviene alinearse con el helper.
3. **El byte 2 del paquete de presencia es `0x03`**, no `0x00` como mandamos
   nosotros. La pagina no lo mira, pero es un dato medido.
4. **Los dpi que escribio la web usan bytes que nuestra tabla no mapea.** De
   `13 27 35 5e 87 f3`, los valores `0x35` (53) y `0xf3` (243) **no estan en
   `TABLA_3311`**, y `_indice()` devuelve -1. O la tabla esta incompleta, o
   ese offset no es el que creemos para esa captura. **Hay que resolverlo
   antes de escribir dpi**: si no sabemos decodificar esos bytes, tampoco
   sabemos generarlos.

## Los artefactos de la Etapa W, verificados de primera mano

Llegaron los `.pcap` y el `.har` a `capturas-w/`. Se parsearon **sin
confiar en la transcripcion de los reportes**: no hay tshark en esta maquina,
asi que se leyo el formato USBPcap (linktype 249) directamente. Las cuatro
capturas tienen **un solo Interrupt OUT con datos**, todas al `dev=2`,
`endpoint 0x03`, reports de 64 bytes. Coinciden con lo que decian los reportes.

Y lo que importa: **`build_write_frame()` reproduce las cuatro tramas byte a
byte, checksum incluido**, incluidas las de dpi completas de 61 bytes, que en
los reportes venian solo como prefijo:

```
w2-rate.pcap      04 0e 00 06 09 01 44 bb 00 00 00 00 01 21                 IDENTICO
w2soft-rate.pcap  04 0e 00 06 09 01 34 cb 00 00 00 00 01 21                 IDENTICO
w2-dpi.pcap       04 3d 00 04 38 01 01 11 3f 00 00 13 27 35 5e 87 f3 ...    IDENTICO
w2soft-dpi.pcap   04 3d 00 04 38 01 01 01 3f 20 00 17 2f 3f 6f 9f 8f ...    IDENTICO
```

Ademas el bloque de dpi que escribe el soft oficial es **identico byte a byte**
al que leemos por hidraw en esta maquina. El circulo cierra: bundle ->
desensamblado -> captura del driver oficial -> lectura nuestra.

### El hallazgo incomodo: la web escribe con una formula y lee con otra

Los bytes de dpi que escribio la web (`13 27 35 5e 87 f3`) **no estan en
`TABLA_3311`**. No es un error de transcripcion: la tabla del repo coincide
exactamente con la del bundle (220 entradas, maximo 235), y esos valores
tampoco estan ahi.

La explicacion aparecio en `Of()`, que no usa la tabla para escribir sino una
funcion aparte:

```js
function Pu(e, t) {
  if (e === 0) return [0, 0];
  let n, a = 0, o = 0;
  return e <= 26e3
    ? (n = Math.floor((e - 50) / 50), n > 255 ? (a = n >> 8 & 255, o = n & 255) : (a = 0, o = n & 255))
    : (n = Math.floor((e - 1) / 100), a = n >> 8 & 255, o = n & 255),
    [o, a];
}
```

Es **lineal**: `byte = dpi/50 - 1`, o sea `dpi = (byte + 1) * 50`. Y reproduce
exactamente los seis bytes capturados:

```
1000 -> 0x13   2000 -> 0x27   2700 -> 0x35
4750 -> 0x5e   6800 -> 0x87  12200 -> 0xf3
```

**Es la misma formula que en su momento descartamos por equivocada.** No estaba
equivocada: estabamos mirando el lado que no era. La web **escribe** con esta
formula lineal y **lee** con la tabla dispersa de `convertBytesToDpi3311`. Las
dos no son inversas una de la otra: los bytes que tenia el mouse (`17 2f 3f
6f 9f 8f`) dan 1000/2000/2700/4750/6800 por la tabla, y la web, para esos
mismos valores, escribe `13 27 35 5e 87 f3`.

O sea que **guardar desde la web cambia los bytes del mouse aunque el usuario
no toque ningun valor**. Es una asimetria del driver oficial, no nuestra.

Consecuencia practica para la fase 2: para escribir dpi hay que usar `Pu()`,
que es lo que usa la web. Reproducimos al driver oficial, con su asimetria
incluida; no nos toca arreglarla. Pero **no se puede derivar el byte de
escritura invirtiendo la tabla de lectura**, que era el camino que parecia
natural.

## Las respuestas largas venian truncadas y nadie se habia dado cuenta

Escribiendo `driver/scripts/respaldar.py` aparecio que `macro` y `perfil completo`
devolvian **los dos exactamente 57 bytes**, siendo estructuras de tamaños bien
distintos. 57 es sospechosamente igual a `64 - 5 - 2`, o sea un report entero.

El canal mueve reports de 64 bytes, asi que una respuesta con
`sizeTotalData` mayor a 59 **no entra en uno solo**: llega en bloques, con el
numero de bloque en el byte 2, justo donde el bloque 0 tiene el opcode. El
bloque 1 no era ni un estado ni una respuesta, no caia en ninguna rama de
`alimentar()` y **se descartaba en silencio**.

Lo lindo es que los largos son los mismos que ya conociamos del camino de
**escritura** de macros, que habiamos sacado del binario:

```
escritura (del binario)   bloque 0: largo 64    bloque 1: largo 57
lectura   (del hardware)  bloque 0: largo 64    bloque 1: largo 57
```

Con `sizeTotalData = 111` para las macros: el bloque 0 lleva `[cmd, N]` mas 57
bytes de datos, y el bloque 1 los 52 que faltan. 57 + 52 = 109 = 111 - 2.

Y confirma de rebote algo que estaba **inferido**: la aritmetica del binario
nos habia hecho deducir que el payload de macros medía 111 bytes, y ahora el
mouse lo dice el mismo en el campo `sizeTotalData`. Igual el perfil completo,
que declara 128 y devuelve 126 bytes de datos.

Arreglado en `Device._reensamblar()`. Con eso el respaldo pasa de:

```
macro                   57 B        perfil completo     57 B     (truncados)
```

a:

```
macro                  109 B        perfil completo    126 B     (completos)
```

Y el perfil completo resulto ser lo que promete: trae los bloques concatenados,
arrancando por el report rate (`01 34 cb`), despues el de dpi y despues el de
iluminacion. Con una sola lectura se tiene todo.

**Dato de paso:** el report rate del mouse ahora es `01 34 cb` y antes de las
capturas de Windows era `01 44 bb`. Lo cambio el soft nativo durante la sesion
de captura. Era esperable, pero conviene tenerlo anotado: **el estado del mouse
cambio**, y el respaldo de linea de base se tomo despues.

---

## La primera escritura desde Linux

Etapa 3 de `docs/fase2.md`, con `driver/scripts/primera-escritura.py`. El mouse por
dongle, bateria 94% (reportada por el propio mouse, no estimada), nada mas
hablandole.

Se le escribio el **report rate que ya tenia**:

```
leido:    cmd=6 datos=01 44 bb 00 00 00 00
escrito:  04 0e 00 06 09 01 44 bb 00 00 00 00 01 21
```

Esa trama es la misma que el driver oficial le mando a este mismo mouse
(coincide con tres tramas de `web-todo.pcap` y `soft-todo.pcap`). No es una
trama nuestra que se parece: es la de ellos, reconstruida desde una lectura.

**Resultado: el dongle acuso `0xC1` y el respaldo posterior salio identico al
previo**, los siete comandos, byte a byte (los dos JSON solo difieren en la
marca de tiempo).

Las dos mitades hacen falta y prueban cosas distintas:

* El **acuse** dice que el mouse acepto la trama. Sin eso no sabriamos si el
  framing sirve, porque un formato invalido no da error: el mouse simplemente
  no hace nada.
* La **comparacion completa** dice que no se toco nada mas. Se comparan los
  siete comandos, no solo el que se escribio, justamente porque el riesgo no
  es equivocarse en el campo que uno mira.

Si el formato hubiera estado mal, el mouse habria ignorado la trama y la
comparacion habria salido igual de limpia. Por eso el criterio es el acuse
**y** la comparacion, no una de las dos.

### Lo que esto cierra y lo que no

Cierra que **se le puede escribir al mouse desde Linux con nuestro codigo**, y
que las siete barandas no estorban el camino legitimo (una baranda que no deja
pasar nada no se distingue de una rota).

No cierra el cambio real. Escribir el valor que ya estaba no demuestra que el
mouse *aplique* un valor distinto, solo que acepta la trama. El paso siguiente
es 1000 -> 500 Hz, verificable por fuera del protocolo con
`driver/scripts/medir-polling.py`.

### Lo que bloquea ese paso

**No sabemos que nibble del byte de rate corresponde al dongle.** Los datos que
hay:

| byte | de donde |
| ---- | -------- |
| `0x34` | de fabrica (`linea-base-antes-de-escribir.json`) |
| `0x11` | escrito por la web durante la tanda |
| `0x44` | escrito por la web y por el soft; es el actual |

Tres valores, y de ninguno se anoto que Hz mostraba la pantalla en ese momento.
Con eso no alcanza para mapear: `0x44` podria ser 1000 Hz o 8000 Hz.

Para resolverlo hace falta una tanda corta y **anotada**: abrir el driver, leer
que Hz muestra, cambiar a un valor conocido, capturar, repetir tres o cuatro
veces. Es la misma leccion de la primera captura de esta serie: la trama sin la
nota de que se toco vale la mitad.


---

## El byte de report rate, medido

Barrida anotada con el soft nativo (`capturas-w/soft-rates-anotados.txt`).
Se partio de 1000 Hz y se puso 125, 250, 500, 1000, 2000, 4000, 8000 en ese
orden. Siete escrituras, siete valores:

| byte | nibble alto | Hz |
| ---- | ----------- | -- |
| 0x14 | 1 |  125 |
| 0x24 | 2 |  250 |
| 0x34 | 3 |  500 |
| 0x44 | 4 | 1000 |
| 0x54 | 5 | 2000 |
| 0x64 | 6 | 4000 |
| 0x74 | 7 | 8000 |

**El nibble alto es el indice: `125 * 2^(n-1)`.** El bajo se quedo en 4 en las
siete. `web-todo.pcap` tiene la misma barrida hecha desde la web, que escribe
los dos nibbles iguales (`0x11` … `0x77`): coinciden en el alto.

### El bug que destapo

`_adaptar_report_rate()` tomaba el nibble **bajo** (`n & 0x0F`). Andaba de
casualidad, por dos motivos que se taparon entre si: la web escribe los dos
nibbles iguales, y el mouse estuvo en `0x44` durante todas las pruebas. Con
cualquier otro estado le decia a la pagina **1000 Hz siempre**, incluido el de
fabrica (`0x34`, que resulta ser 500 Hz).

Es el mismo patron que el decodificador de dpi: una hipotesis validada contra
un unico dato donde las dos alternativas coincidian.

### Lo que queda INFERIDO

El nibble bajo. La lectura razonable es que sea la tasa por cable — el soft lo
deja en 4 y la web lo pisa con el mismo valor que el inalambrico — pero para
medirlo hay que capturar por cable, y el cable habla Feature Reports. Hasta
entonces el puente lo **respeta**: al escribir cambia solo el nibble alto.

### Y una nota de metodo

La captura se pidio como `web` y era del soft. Se noto sola: manda el comando
`0x0c`, que la web nunca manda. Vale como recordatorio de que la etiqueta se
puede equivocar y los datos no: conviene chequear la etiqueta contra el
contenido antes de sacar conclusiones.

---

## A 8000 Hz el canal de configuracion se cae, y el mouse con el

**Lo que no funciono**, que es la mitad util.

Despues de la barrida de report rate el mouse quedo en **8000 Hz** (`0x74`, la
ultima escritura del soft). Al correr `primera-escritura.py --comando rate
--valor 500`, el respaldo del paso 1 leyo tres comandos y despues:

```
dpi: el dongle sigue ocupado despues de 5 intentos
botones: el dongle sigue ocupado despues de 5 intentos
macro: el dongle sigue ocupado despues de 5 intentos
perfil completo: el dongle sigue ocupado despues de 5 intentos
```

y **el mouse dejo de moverse** durante un rato. Se recupero solo.

### Que paso

No fue la escritura: el script aborto en el paso 1 por respaldo incompleto y
nunca llego a escribir. Fue el camino de **lectura**.

A 8000 Hz el dongle mueve ocho veces mas trafico de movimiento, y el canal de
configuracion compite con eso. El dongle empieza a contestar `0xC3` ocupado, y
ahi aparece un defecto que estaba desde siempre y no se habia notado:

| | |
| --- | --- |
| presupuesto de espera | `PAUSA_OCUPADO` 0.3 s x `REINTENTOS_OCUPADO` 4 = **1.2 s** |
| peor caso medido para que el dongle se libere | **2.10 s** (el NAK) |

O sea que se rendia antes de darle la chance de liberarse. Y peor: cada
reintento le caia encima con el pedido anterior todavia en vuelo, que es
exactamente lo que el comentario de `device.py` advertia que lo deja trabado
("de ahi no sale mas"). El mouse dejo de andar porque sus reports de movimiento
salen por ese mismo dongle trabado.

A 1000 Hz nunca se vio porque el dongle se libera rapido y el presupuesto
alcanzaba de sobra.

### Que se cambio

`PAUSA_OCUPADO` pasa a 0.4 s y la espera **crece al doble** cada vez, con tope
de 3 s: 0.4 + 0.8 + 1.6 + 3.0 = 5.8 s de presupuesto, comodo por encima de los
2.10 s. Insistir al mismo ritmo contra algo que esta ocupado lo mantiene
ocupado; esperar cada vez mas es lo unico que corta el ciclo.

El mensaje de rendicion ahora nombra la causa probable, en vez de dejarla para
que la deduzca el que lo lea a las once de la noche.

### Lo que queda abierto

**No esta medido que esto alcance a 8000 Hz.** El cambio es correcto en su
razonamiento —el presupuesto ahora supera el peor caso conocido— pero la unica
prueba real es volver a intentar el respaldo con el mouse a 8 kHz. Si igual
falla, la conclusion seria que a 8000 Hz el canal de configuracion no es
utilizable y hay que bajar la tasa antes de configurar, que es una limitacion
del hardware y no algo que se arregle con reintentos.

### Nota de seguridad

Esto pone un limite real: **una lectura puede dejar el mouse sin responder por
unos segundos.** No hay riesgo para el firmware, pero si el usuario esta
usando la maquina, se le muere el puntero. Cualquier cosa que lea configuracion
en segundo plano tiene que tenerlo en cuenta.

---

## La respuesta llegaba y no había nadie esperándola

La prueba que pedía la entrada anterior, corrida contra el hardware.

### Lo medido

Con el mouse en 8000 Hz (`medir-polling.py`: 8004 Hz de mediana, 91.2% de los
intervalos en 125 us) y ya con el backoff exponencial de 5.8 s:

| comando | sub | datos | bloques | A: 1.2 s | B: 5.8 s | C: 5.8 s + respiro |
| ------- | --- | ----- | ------- | -------- | -------- | ------------------ |
| versión de firmware | 8 | 6 B | 1 | ok | ok | ok |
| report rate | 9 | 7 B | 1 | ok | ok | ok |
| iluminación | 15 | 13 B | 1 | ok | ok | ok |
| dpi | 56 | 54 B | 1 | **falla** | ok | **falla** |
| botones | 59 | 57 B | 1 | **falla** | ok | **falla** |
| macro | 111 | 109 B | **2** | **falla** | **falla** | **falla** |
| perfil completo | 128 | 126 B | **3** | **falla** | **falla** | **falla** |

Las tres con el mouse a 8000 Hz. A es la del backoff corto; B, la de la
entrada anterior; C es con el backoff largo **más** el respiro entre fallos y
la segunda pasada, o sea con todo puesto: 3 de 7, peor que B.

**Corrección, y vale anotarla como método.** Mirando solo A y B escribí que la
frontera era nítida y estaba en el límite del bloque: pasaba todo lo que entra
en un report de 64 y fallaba lo que no. C lo desmiente — dpi y botones son de
un bloque y también fallaron. Era el mismo error que ya está catalogado dos
veces en este archivo (el dpi, el nibble del rate): **una hipótesis linda
validada contra una sola corrida**. Lo que hay no es una frontera sino una
probabilidad que empeora con lo que tarde la respuesta; los multi-bloque son
los primeros en caer porque necesitan más de una ventana libre en el aire,
pero nadie está a salvo.

Lo que sí queda firme de las tres: **a 8000 Hz el respaldo no se completa
nunca.** Tres corridas, tres incompletas, y la mejor dejó afuera los dos
comandos más largos.

### El agujero, que no era del enlace

Los dos que fallan mueren con `0xC3` ocupado, y ahí estaba el defecto de
verdad. En `leer()`, el futuro donde se deja la respuesta se registraba y se
borraba **dentro de cada intento**:

```
self._esperando[cmd] = fut      # se registra
...
finally:
    self._esperando.pop(cmd)    # se borra ANTES de la pausa
await asyncio.sleep(pausa)      # 0.4 a 3.0 s sin nadie esperando
continue                        # recién acá se vuelve a registrar
```

Durante la pausa de "ocupado" —que después del arreglo anterior puede ser de
hasta 3 s— **no quedaba nadie esperando la respuesta**. Si llegaba justo ahí,
`alimentar()` no encontraba a quién dársela, se iba por `on_frame` (que en el
respaldo es `None`) y el intento moría por timeout con la respuesta ya en
casa. Lo mismo tras rendirse: un bloque que llegara un segundo tarde se tiraba.

Cuanto más tarda una respuesta, más probable es que caiga en uno de esos
huecos. Por eso pegaba justo en macro y perfil completo: son los que vienen en
varios bloques y necesitan más de una ventana libre en el aire.

Vale la pena decirlo claro porque es la trampa n.º 1 del proyecto otra vez, en
otro disfraz: **esto se ve idéntico a "el enlace perdió el pedido"**, y no lo
era. El pedido volvía; lo tirábamos nosotros.

### Qué se cambió

Nada de esto le manda un byte nuevo al mouse: son las mismas tramas de
lectura de siempre. Todo el cambio es de este lado.

- El futuro vive **toda la llamada** a `leer()`, no un intento. Las pausas
  dejaron de ser huecos.
- Las pausas se despiertan si la respuesta llega antes
  (`_dormir_salvo_respuesta`), en vez de dormir el tiempo completo.
- **Gracia con evidencia**: si al agotarse los reintentos hay una respuesta
  larga a medio armar, se espera un timeout más. Solo con esa evidencia:
  tener el bloque 0 en la mano es la prueba de que el dongle está
  contestando. Sin ella, esperar de más es demorar el fracaso.
- `_parcial` se limpia al empezar cada pedido, para que los restos de uno que
  quedó a medias no se anexen al siguiente.
- El mensaje de rendición ahora distingue "no contestó" de "contestó N de M
  bytes y se perdió el resto", que son dos problemas distintos.
- `respaldar.py`: tras un comando que se rinde, **3 s de respiro** antes del
  siguiente (el dongle puede seguir con ese pedido en vuelo, y encimarle otro
  lo mantiene ocupado), y una **segunda pasada** al final sobre lo que faltó.
  La segunda pasada no afloja nada: el respaldo sigue estando incompleto si
  algo no contesta, y quien exige los siete es `primera-escritura.py`.

Tres regresiones nuevas en `driver/tests/salvaguardas.py`. Dos de ellas fallan con el
código anterior (se comprobó con el `device.py` viejo): la respuesta que llega
durante la pausa del `0xC3`, y el bloque tardío. La tercera —que un parcial no
contamine al pedido siguiente— pasa también con el código viejo: es una guarda
del invariante, no un bug que se haya observado.

### Lo que quedó medido, y era la pregunta abierta

**A 8000 Hz el canal de configuración no es utilizable.** La entrada anterior
dejó eso planteado como la conclusión a la que había que llegar si los
reintentos no alcanzaban, y la corrida C lo confirma con todas las mejoras
puestas. No es algo que se arregle esperando más: es una limitación del
enlace. **Hay que bajar la tasa antes de configurar.**

Lo que sigue sin saberse es si los arreglos de esta entrada mejoran algo a
tasas normales. A 1000 Hz el respaldo ya salía 7/7 antes, así que no hay dónde
verlo; el valor de estos cambios es que el modo de fallo que arreglan —tirar
una respuesta que sí llegó— era real y estaba en el camino de lectura de
siempre. Que a 8 kHz no alcance no lo vuelve incorrecto, solo insuficiente.

### El círculo, y por dónde se sale

Bajar el rate desde Linux exige un respaldo completo (Etapa 3), el respaldo
completo exige que el canal de configuración funcione, y el canal de
configuración es justamente lo que se cae a 8000 Hz. Es circular y no se sale
por adentro.

La salida no es aflojar la exigencia del respaldo. Es bajar la tasa por el
otro camino —el soft oficial en la VM de Windows, que ya tiene el dongle
pasado por USB— y volver a Linux con el mouse a 1000 Hz. Es exactamente el
papel de "red de seguridad" que `docs/fase2.md` le asigna a Windows: no
reemplaza al proyecto, lo destraba.

**Consecuencia operativa, para no volver a caer:** dejar el mouse a 8000 Hz
inhabilita la configuración desde Linux, incluida la lectura. Si se sube la
tasa para probar, hay que bajarla antes de terminar.

---

## El mouse cambió de frecuencia porque Linux se lo pidió

La Etapa 3 completa, con cambio real y verificado por fuera del protocolo.

### El camino

El mouse estaba en 8000 Hz, que es donde el canal de configuración no
responde (entrada anterior). Se bajó a 1000 Hz con el soft oficial en la VM de
Windows —Windows como red de seguridad, exactamente el papel que le
asigna `docs/fase2.md`— y con eso el respaldo volvió a salir **7 de 7 a la
primera**. De ahí en adelante, todo en Linux.

### La escritura

```
[2/6] leido: cmd=6 datos=01 44 bb 00 00 00 00
[3/6] escritura CAMBIO REAL: 1000 Hz -> 500 Hz
      04 0e 00 06 09 01 34 cb 00 00 00 00 01 21
[5/6] el dongle acuso 0xC1: el mouse aplico la escritura
```

`0x44` → `0x34`: el nibble alto pasa de 4 a 3, y `125 * 2^(3-1)` = 500. El
nibble bajo se dejó en 4, como hace el soft. El `0xcb` que lo sigue es el
`0xFF ^ 0x34` del propio payload.

### Lo que cambió en el mouse: dos bytes

El paso 6 releyó los siete comandos y comparó contra el respaldo previo:

| comando | byte 1 | byte 2 |
| ------- | ------ | ------ |
| report rate | `0x44` → `0x34` | `0xbb` → `0xcb` |
| perfil completo | `0x44` → `0x34` | `0xbb` → `0xcb` |

**Nada más se movió**, en ningún comando. Y los dos que se movieron lo
hicieron con los mismos valores en los mismos índices, porque el perfil
completo empieza con los tres primeros bytes del bloque de report rate
(`01 44 bb`, verificado byte a byte en el respaldo). No es una lectura
independiente: los embebe.

### La verificación que no depende de creerle al mouse

`medir-polling.py`, que lee `/dev/input/event5` y no habla el protocolo:

```
antes:    intervalo mediano  999 us -> 1001 Hz   (72.0% en 1000 us)
despues:  intervalo mediano 1999 us ->  500 Hz   (53.9% en 2000 us)
```

Es la primera vez que el proyecto cambia el comportamiento del hardware desde
Linux y lo confirma por un camino que no es el mismo que dio la orden.

### Lo que esto deja MEDIDO

- **El nibble alto es el índice**, ahora comprobado escribiéndolo y midiendo el
  efecto, no solo leyéndolo de una captura. La barrida anotada mapeó los siete
  valores; esto cierra el círculo del otro lado.
- **Respetar el nibble bajo funciona.** Se lo dejó en 4 y no rompió nada. Lo
  que *significa* sigue INFERIDO (la lectura razonable es que sea la tasa por
  cable, y medirlo exige capturar por cable, que habla Feature Reports).
- El framing de escritura sirve para un cambio real, no solo para el
  idempotente más temprano.

### De la captura del soft, de paso

`soft-rate-8000-a-1000.pcap`, tocando **un solo control**: el soft manda cinco
escrituras seguidas, a un segundo de intervalo —`0x0c`, dpi, iluminación,
report rate, botones— y las cinco dieron **IDÉNTICO** contra
`build_write_frame()`. Reescribe todo el perfil aunque se haya tocado una cosa.

Y otra vez la nota de método: la nota de la captura dice "qué valor exacto
pusiste? nose", pero la trama dice `0x44` y `medir-polling.py` midió 1001 Hz
después. **La etiqueta se puede perder; los datos no.** Es el mismo aprendizaje
que dejó la captura mal rotulada de la barrida.

---

## Repaso de documentación, y un byte que no cuadra

Pasada sobre toda la documentación después de la Etapa 3, para bajar lo que
había quedado desactualizado. Casi todo era mecánico —el modo `full` figuraba
como cerrado en cuatro lugares del README, en `AUDITORIA.md` y en el docstring
de `build_write_frame()`— pero salieron dos cosas que no lo eran.

### `dpi.py` seguía afirmando lo que su propio commit desmintió

El commit "El X8 Pro lee el dpi con Pu(), no con la tabla dispersa del 3311"
corrigió el código y los comentarios de la parte de `Pu()`, pero el **docstring
del módulo** siguió diciendo que el DPI "no es una fórmula lineal sobre el byte:
es un índice en una tabla dispersa". Y `AUDITORIA.md` seguía listando como
MEDIDO los valores viejos —1000/2000/2700/4750/6800/24400— que son justo los
que ese commit demostró equivocados para este modelo.

O sea: la afirmación corregida sobrevivió en los dos lugares donde la va a leer
alguien que audita, que son los que más importan. Corregidos los dos.

### El byte de versión: `01` en Linux, `05` en la Etapa W

Revisando los respaldos apareció esto:

| fuente | bloque de versión (cmd 11) | checksum |
| ------ | -------------------------- | -------- |
| los **ocho** respaldos por hidraw y 08 | `08 00 83 01 01 00` | `b1` |
| el HAR y las capturas de la Etapa W | `08 00 83 01 05 00` | `b5` |

El checksum acompaña en las dos, así que son dos tramas reales y no una mal
transcripta. **No sabemos qué campo es ese byte.** La anotación de
`capturas-w/web-arranque-dpi-y-rate.txt` ya lo había notado y propuso la
explicación razonable —que la Etapa W se capturó contra otra unidad o con otro
firmware— pero eso se quedó dentro del archivo de la captura y nunca llegó ni a
`AUDITORIA.md` ni acá.

Importa por dos motivos:

- Las conclusiones de la Etapa W valen como **framing** —eso está confirmado
  contra este mouse byte a byte— pero no necesariamente como **valores** de
  esta unidad.
- Las dos trazas de esta bitácora que muestran `05` como lectura
  de Linux (en "Fase 1 completa, punta a punta" y más arriba) **no concuerdan
  con ningún respaldo**. O se copiaron del material de la Etapa W, o el valor
  cambió y nadie lo vio. Quedan marcadas como sospechosas; el dato que vale es
  el de los respaldos, que son ocho y coinciden.

### Y la explicación, que la puso el usuario

**Son dos mouses.** Las medidas no salieron todas de la misma máquina: la
Etapa W se capturó en **AUT01**, una PC física con Windows, y el resto en una
**VM de Windows** con el dongle pasado por USB. Con eso la
evidencia parte limpio en dos:

| Origen | Bloque de versión | chk |
| ------ | ----------------- | --- |
| AUT01 — `w1.har`, `w2-*.pcap`, `w2soft-*.pcap` | `08 00 83 01 05 00` | `b5` |
| VM de Windows — `web-*.pcap`, `soft-*.pcap` | `08 00 83 01 01 00` | `b1` |
| Los ocho respaldos por hidraw, desde Linux | `08 00 83 01 01 00` | `b1` |

Lo que lo cierra es el passthrough: **la VM usa el mismo dongle físico que
Linux**, así que mira necesariamente el mismo mouse — y coincide. AUT01 tenía
el suyo.

Lo bueno es que la división cae del lado correcto: **AUT01 aportó forma, la VM
aportó valores.** Los cierres de I-01 y I-03 son sobre el framing, y el framing
está confirmado aparte contra este mouse. Y la Etapa 2, que es la que autoriza
a escribir, se validó contra `soft-todo.pcap` y `web-todo.pcap` —los dos de la
VM— partiendo de un respaldo real. Nada que dependa de un valor de AUT01 quedó
sosteniendo una escritura.

Lo que sigue abierto es **qué campo es ese byte**.

### Un regalo que estaba escondido en el mismo lugar

Revisando `reporteWsoft.md` apareció esto: la trama con la que ayer bajamos el
rate a 500 Hz,

```
04 0e 00 06 09 01 34 cb 00 00 00 00 01 21
```

**ya estaba capturada del driver oficial** en
`capturas-w/w2soft-rate-outs.txt`, byte a byte idéntica. O sea
que la primera escritura real del proyecto no fue una trama deducida del mapeo
de nibbles y armada por nosotros: es una que el soft oficial ya había puesto en
el bus. Es la regla del proyecto cumplida en su forma más fuerte, y no lo
sabíamos cuando la mandamos.

### Y lo que hizo falta para no volver a tropezar

`capturas-w/README.md` listaba **solo** el lote de AUT01: los seis `.pcap` de la
VM no figuraban, y las dos procedencias no se distinguían. Esa omisión es lo
que dejó pasar el asunto durante un día entero de trabajo. Reescrito con los
dos lotes separados y con la advertencia de cuál sirve para qué. `captura-kvm.md`
suma a su checklist anotar **de qué unidad** es la captura, no solo de qué
máquina.

Queda como I-W6 (explicado, con la pregunta del campo abierta) y I-W7 en el
informe vivo.

---

## La vuelta, y el ciclo cerrado

500 Hz -> 1000 Hz, que era el último checkbox de la Etapa 3.

Antes de correrlo se calculó qué trama tenía que salir, para tener un control
byte a byte que no dependiera de mirar el resultado y darlo por bueno. Salió
esta:

```
04 0e 00 06 09 01 44 bb 00 00 00 00 01 21
```

**Que es exactamente la que el driver oficial mandó en `w2-rate.pcap`**, y la
que el test guarda como `RATE_OFICIAL`. O sea que las dos escrituras reales del
proyecto —la ida y la vuelta— resultaron ser tramas que el driver oficial ya
había puesto en el bus: la de 500 Hz está en `w2soft-rate-outs.txt` y la de
1000 Hz en `w2-rate.pcap`. La regla del proyecto se cumplió sin que hubiera que
forzarla.

### El resultado

Cuatro bytes en todo el mouse, contando la ida y la vuelta:

| comando | antes | después |
| ------- | ----- | ------- |
| report rate | `01 34 cb` | `01 44 bb` |
| perfil completo | `01 34 cb …` | `01 44 bb …` |

Los otros cinco comandos, idénticos. Y la verificación que vale, la que no
pasa por el protocolo: `medir-polling.py` dio **1001 Hz**, mediana 999 us, con
el 73.8% de los intervalos en 1000 us — el mismo perfil que antes de bajar.

### Dos cosas que aparecieron de paso

**El mouse venía de fábrica a 500 Hz, no a 1000.** El respaldo
(`linea-base-antes-de-escribir.json`) tiene `0x34`. El checkbox de `fase2.md`
decía "volver a 1000 Hz" dando por sentado que ese era el punto de partida;
1000 Hz es donde estuvo la mayor parte del trabajo, pero el estado original era
500. Si algún día se quiere dejar como vino, es `--valor 500`.

**La baranda de "sin terminal no se escribe" actuó por primera vez en serio.**
El primer intento se corrió a través del `!` del asistente, que ejecuta sin
tty: el script llegó hasta el paso 3, mostró la trama, y cortó en el 4 sin
escribir. No estaba previsto ese caso concreto y funcionó igual, que es lo que
uno quiere de una baranda.

### Y un defecto del propio script

Terminaba con código de salida **1** aunque el cambio fuera exactamente el que
se pidió: con `--valor`, cualquier diferencia contaba como fallo. Quien encadene
el script leía "falló" cuando había salido todo bien.

Ahora el desenlace se decide **por comando** y no sobre el texto que arma
`comparar()`, con `respaldar.cmds_que_cambiaron()`:

| qué pasó | sale |
| -------- | ---- |
| cambió el comando pedido, y el perfil completo que lo embebe | **0** |
| no cambió nada, habiendo pedido un cambio | 1 |
| cambió algo pero no el comando pedido | 1 |
| cambió además algún otro comando | 1, y lo nombra |
| escritura idempotente sin diferencias | 0 |
| escritura idempotente con diferencias | 1 |

El perfil completo está en la lista de lo esperado porque **está medido** que se
mueve con el rate: los mismos dos bytes, en las dos direcciones. Cualquier otro
comando sigue siendo alarma. `test_que_cambio_en_una_escritura` fija los cuatro
casos.

---

## El camino de escritura de dpi, y dos cosas que no esperaba

Sesión sin el usuario y sin tocar el mouse: todo lo de acá es código y análisis de
capturas que ya estaban.

### El checksum interno, que estaba mal calculado y nadie lo usaba

`estructuras.checksum_interno()` sumaba el bloque entero —incluido el propio
checksum y el relleno— y no daba el número que traen las capturas en ningún
caso. El docstring decía que contra la iluminación daba `0x01af`, y para eso
había que llamarla con el recorte ya hecho, que es lo que hacía el único test
que la usaba.

La regla real, leída de `co()` (`for (l = 3; l < o; l++) i += buf[l]`) y ahora
**medida**: es la suma de `datos[1:fin_de_campos]`, o sea sin el `profileId` y
sin la cola. Verificada contra **61 tramas** de dpi e iluminación de las
capturas del driver oficial, de la web y del soft, con valores distintos: las
61 traen exactamente esa suma. Cero excepciones.

Importa porque **para escribir hay que recalcularlo**. Un bloque de dpi con el
checksum viejo es una trama que el mouse nunca vio.

### `Dpi_Y_setting` deja de estar sin confirmar

Estaba marcado en `CAMPOS_SIN_CONFIRMAR` porque "en la única captura viene casi
todo en cero". No está todo en cero: trae un `01` en el índice 5, y es
exactamente el byte alto que hace falta para que el nivel 6 dé 40000
(`n = 0x18f = 399`, rama de `/100`, con el bit 5 puesto en `DPI_X_Double_Flag`).

Si el campo empezara un byte antes o después, ese `01` caería en el nivel 5 o
en el 7, y los seis valores no darían lo que muestra la página oficial. El
offset no es una elección nuestra: es el único que hace cerrar los seis niveles
a la vez. `CAMPOS_SIN_CONFIRMAR` queda vacío.

### `escribir_nivel_dpi()`

Cambia **un** nivel sobre el bloque leído del mouse: el byte bajo y el alto del
nivel, el bit de la rama de `Pu()` y el checksum interno. Nada más — ni el
nivel seleccionado, ni `DPI_Y_Double_Flag`, que se respetan como vengan, con el
mismo criterio que el nibble bajo del report rate.

La prueba fuerte es la de la Etapa 2, en dos formas:

1. **Idempotencia, seis de seis.** Reescribirle a cada nivel el valor que ya
   tiene reproduce el bloque byte a byte, checksum incluido. Incluye el nivel 6
   con sus 40000, que es el que usa la otra rama de `Pu()`.
2. **Reproducir un cambio del driver oficial.** En `web-todo.pcap` el operador
   movió el nivel 4 de 4750 a 4800 desde la página; nuestro codificador produce
   la segunda trama a partir de la primera, idéntica.

### Y las dos cosas que no esperaba

Barrí las capturas buscando pares de escrituras de dpi que difirieran en un
solo nivel, para ver cuántos reproducíamos. **Cinco de trece idénticos**, y las
diferencias son casi siempre los mismos dos bytes.

**1. El driver oficial mueve también el nivel seleccionado.** El byte que
difiere es `Current_Dpi_level_flag` (y el checksum, que lo sigue): al tocar el
slider del nivel N, la aplicación además deja el mouse *en* ese nivel. Nosotros
no, y creo que está bien: cambiar el valor de un nivel y cambiar en qué nivel
está el mouse son dos cosas distintas, y la segunda se nota al instante en la
mano. Los cinco casos idénticos son aquellos en que el nivel seleccionado ya
coincidía. **Consecuencia: para dpi no hay igualdad byte a byte con el oficial
salvo en ese caso**, y conviene saberlo antes de invocar la regla del proyecto.

**2. Hay dos codificaciones para el mismo dpi, y el oficial usa las dos.**
Pasando el nivel 1 de 1000 a 2000, la web dejó el byte en `0x13` y **encendió
el bit de la rama**: `(19+1) * 100 = 2000`. `Pu(2000)` da `0x27` con el bit
apagado: `(39+1) * 50 = 2000`. Las dos se leen como 2000 y las dos son
coherentes; nosotros escribimos la de `Pu()`, que es la transcripción literal
del bundle.

**Lo que no está medido es si al mouse le da igual.** Si el firmware usa ese
flag para su propio cálculo y no solo como etiqueta, dos codificaciones que la
UI muestra iguales podrían no mover el sensor igual. No hay forma de decidirlo
desde las capturas. Por eso la primera escritura real de dpi tiene que ser la
**idempotente**, que está probada byte a byte, y un cambio de verdad conviene
hacerlo con un valor por debajo de 26000, donde `Pu()` no tiene alternativa.

---

## El mouse cambió de DPI porque Linux se lo pidió

La Etapa 3 para el segundo comando, en las dos formas y en el mismo orden que
con el report rate.

**Idempotente primero.** Acusó `0xC1` y el respaldo posterior salió idéntico al
previo, los siete comandos. El framing de dpi sirve.

**Y después el cambio real**, nivel 1 de 1200 a 1600 dpi:

```
04 3d 00 04 38 01 01 01 3f 20 00 1f 2f 3f 6f 9f 8f … 02 0f c3 00 00 00 00 11 13
```

El mouse quedó en `1600, 2400, 3200, 5600, 8000, 40000`, y el diff es
exactamente el que se había calculado antes de mandarlo:

| | antes | después |
| --- | --- | --- |
| `Dpi_X_setting` | `17 2f 3f 6f 9f 8f 00 00` | `1f 2f 3f …` |
| `_cola` (checksum interno) | `0f bb` | `0f c3` |

`0x17` = 23 → `0x1f` = 31, y el checksum subió exactamente 8, que es la misma
diferencia. **El recálculo del checksum interno quedó verificado contra el
hardware**, no solo contra las capturas: si hubiera estado mal, el mouse habría
ignorado la trama o guardado otra cosa.

Y el perfil completo se movió con los mismos dos cambios, como con el rate.

### Lo que faltaba y no me había dado cuenta

El paso 6 sugería `medir-polling.py` para verificar por fuera del protocolo.
**Para dpi eso no verifica nada**: mide la tasa de reporte, que no cambia al
mover el dpi. Es peor que no sugerir nada, porque da una confirmación que no
confirma.

Ahora cada comando sugiere la suya. Para dpi escribí un `medir-dpi.py` que
contaba los counts mientras se movía el mouse una distancia declarada y los
dividía por las pulgadas, dando por sentado que mover 20 cm a mano iba a ser
lo bastante repetible.

> **No lo fue, y el script se borró el mismo día. Ver abajo.**

**Ojo con una cosa al medir**: hay que poner el mouse *en* el nivel que se
cambió, con el botón de DPI. Este mouse estaba en el nivel 2 y el cambio fue al
1; medir sin cambiar de nivel habría dado 2400 y parecería que la escritura no
funcionó.

Eso, de paso, explica por qué el driver oficial mueve `Current_Dpi_level_flag`
al nivel que se toca: para que el usuario vea el efecto en la mano al instante.
Nosotros no lo hacemos —son dos cambios distintos— y el precio es este paso
manual.


---

## Medir el DPI con una regla no funciona

`medir-dpi.py` duró unas horas. Estas son las mediciones que dio, todas del
mismo mouse, recién puesto en 1600 dpi:

```
41  ·  1006  ·  537  ·  2545  ·  171  ·  111      dpi
```

El código contaba bien los counts. Lo que no se cumple es la premisa: **mover
el mouse exactamente 20 cm a mano, tres veces seguidas, no es repetible**, y el
corte automático por "un segundo de quietud" partía los trazos por la mitad, de
manera que una pasada contaba medio recorrido y la siguiente empezaba a mitad
de camino.

### Por qué se borra en vez de arreglarse

Porque **dio una falsa alarma sobre una escritura que había salido perfecta**:
dijo "revisá si la escritura quedó donde tenía que quedar" cuando el mouse
había acusado `0xC1`, releía 1600 y el diff eran dos bytes con el checksum
coherente. Una baranda que grita cuando no pasa nada gasta la credibilidad de
las que sí sirven, y este proyecto tiene varias que dependen de que uno les
crea.

Se podría arreglar midiendo **relaciones** en vez de valores absolutos —el
mismo recorrido físico entre dos topes, en dos niveles distintos, y comparar
los counts— pero eso sigue siendo manual, sigue dependiendo del pulso, y no
hace falta.

### Lo que sí verifica un cambio de dpi

**Tres caminos independientes, y los tres ya estaban:**

1. El dongle acusa `0xC1`: la trama fue aceptada.
2. La relectura completa muestra el valor nuevo, y el diff está acotado a los
   bytes que se tocaron.
3. **El checksum interno.** Este es el que más pesa y es el que no habíamos
   sabido apreciar: lo calculamos nosotros, va adentro del bloque, y si
   estuviera mal el mouse habría rechazado la trama o guardado otra cosa. Que
   el byte suba 8 y el checksum suba 8 no es una coincidencia que se pueda
   fabricar.

Y si se quiere un lector que no sea el nuestro, está la **página oficial**:
`./asbridge --backend hidraw --mode read` y abrir la web. Es software del
fabricante interpretando los mismos bytes sin pasar por nuestro decodificador,
que es exactamente lo que se le pedía a la medición con regla, y sale gratis.

### La lección, que es de método

El report rate tiene una verificación externa barata y precisa **porque el
kernel ya cronometra los reportes**: no hay que medir nada, solo leer. Di por
sentado que cada comando iba a tener una equivalente y me puse a fabricarla. No
todas la tienen, y fabricar una mala es peor que reconocer que no hay.

---

## La página lee con una fórmula y escribe con otra

El usuario abrió la web para verificar el cambio de dpi y **la página mostró 1350 en
el nivel 1**, no los 1600 que habíamos escrito. Y 2000 en el nivel 2, donde
nosotros mostrábamos 2400.

No era un error de la escritura. Es un hallazgo, y de los grandes.

### Lo que hace la página oficial

| | fórmula | de dónde sale |
| --- | --- | --- |
| **Leer** | tabla dispersa del 3311 | `getSensorType()` mapea `X8Pro: "3311"`, y `parseDpiSettings()` llama a `convertBytesToDpi3311()`. Está **hardcodeado**, no es una detección que falle |
| **Escribir** | `Pu()`, lineal | los seis usos de `Pu(` en `app.js`, y las capturas del bus |

O sea que **la aplicación del fabricante se contradice consigo misma**. Y no es
una teoría: se lo vio en vivo en el log del puente. Apenas se conectó, la
página leyó los bytes del mouse, los interpretó con la tabla y **los reescribió
con `Pu()`**:

```
mouse:  1f 2f 3f 6f 9f 8f   ->  tabla: 1350, 2000, 2700, 4750, 6800, 24400
pagina: 1a 27 35 5e 87 e7   <-  Pu() de esos mismos seis valores
```

`Pu(1350) = 0x1a`, `Pu(2000) = 0x27`, `Pu(2700) = 0x35`… los seis cierran. La
página convierte el estado del mouse de una codificación a la otra **sin que
nadie toque un control**, solo por abrirla.

**El modo `read` bloqueó las seis escrituras** y el mouse no se movió. Se ve en
el log: `BLOQUEADO (modo read): dpi de 60 B`, seis veces, y la página
reintentando.

### Lo que esto corrige

El commit "El X8 Pro lee el dpi con Pu(), no con la tabla dispersa del 3311"
tenía razón en la mitad de **escritura** y estaba equivocado en la de
**lectura**. Su evidencia era "con el mouse en fábrica la página muestra
1200/2400/3200/5600/8000/40000". No los muestra: muestra los de la tabla. Esa
observación nunca se había hecho mirando la pantalla con los bytes delante.

Es la tercera vez que el dpi engaña, y las tres veces por lo mismo: una
hipótesis contrastada contra datos que no separaban las alternativas.

### Lo que sigue sin saberse, y ahora importa

**Cuál de las dos fórmulas corresponde al dpi que hace el sensor.**

A favor de la lineal (`Pu()`): el X8 Pro se vende como 40000 dpi, y solo `Pu()`
da 40000 en el nivel 6 de fábrica; `M()` del chunk del X8 Pro pone
`dpi6 = 4e4` al restaurar; y al subir de a 50 dpi desde la UI los bytes se
mueven de a uno, que es exactamente `(dpi-50)/50`.

A favor de la tabla: es lo que la página muestra en pantalla.

No se puede decidir desde el bundle ni desde las capturas: hay que medir el
desplazamiento real del sensor. Y acá sí valdría la pena hacerlo, aunque la
medición sea tosca —a diferencia del intento de esta mañana, que buscaba
confirmar algo ya confirmado—: entre las dos hipótesis hay un 18% en el nivel 1
y un **64% en el nivel 6** (40000 contra 24400). Una medición con una regla y un
error del 20% alcanza para separarlas.

### Lo que se cambió mientras tanto

- `describir()` muestra **los dos** valores, y primero el de la página, que es
  el número que el usuario tiene delante. La etiqueta anterior decía
  `tabla 3311 (otro modelo daria)`, que era falsa y es justamente la que hizo
  que esto pasara meses sin verse: no es otro modelo, es **este**.
- `primera-escritura.py` avisa, **antes de confirmar**, qué va a mostrar la
  página: pedir 2000 dpi escribe un byte que la página lee como 1700.
- El docstring de `dpi.py` explica las dos mitades y por qué el proyecto se
  equivocó primero en una dirección y después en la otra.

### Una advertencia que sale de esto

**Con el modo `full` y `--permitir-escritura dpi`, abrir la página oficial le
reescribe el dpi al mouse.** No hace falta tocar nada: lo hace al conectarse.
La confirmación de la primera escritura es lo único que se interpone, y después
de aceptarla una vez, las siguientes pasan solas. En `read` no puede pasar.

---

## Un acuse que se perdía en la pausa, y una iluminación que no estaba bloqueada

Dos cosas sin relación entre sí, las dos sin escribirle un byte al mouse.

### El `0xC1` que se perdía (N-H04)

`Device.escribir()` dormía con `asyncio.sleep()` en las dos pausas de su bucle:
la del backoff por `0xC3` (de 0.4 a 3.0 s) y la de reintento (0.15 s). Si el
acuse llegaba ahí, `_escritura_ok.set()` se marcaba, el bucle hacía `continue`
y la vuelta siguiente lo borraba con `clear()` **antes de mirarlo**.

`leer()` ya tenía esto arreglado desde esta mañana (`_dormir_salvo_respuesta`),
pero el arreglo no había cruzado a `escribir()`.

**Y en la escritura el daño es peor.** Perder una respuesta en `leer()` cuesta
un pedido de más. Perder el acuse en `escribir()` significa que la escritura
**ya se aplicó en el mouse** y no nos enteramos: se reenvía una trama que no
hacía falta y, si se agotan los reintentos, se devuelve `False` habiendo
escrito. O sea que el script hubiera dicho "SIN ACUSE. O el enlace perdió el
pedido, o el mouse ignoró la trama por formato" para una escritura que salió
bien. Justo la clase de afirmación que este proyecto no se permite.

La ventana no era teórica: el acuse llega a ~25 ms y la pausa por "ocupado"
arranca en 400 ms. Cualquier `0xC3` seguido del acuse normal caía adentro.

Arreglado con `_dormir_salvo_evento()`, el equivalente de
`_dormir_salvo_respuesta()` para un `Event` (sin `shield`: cancelar al que
espera no borra el Event).

Los tres tests de regresión miran **cuántas veces se escribió**, no solo el
valor devuelto, porque el reenvío es la mitad del problema. Sin el parche:

    FALLA  N-H04 acuse en la pausa de 'ocupado'
             - el 0xC1 llego durante la pausa ... se dio por fallida
             - 3 escrituras, esperaba 1: se reenvio al mouse una escritura
               que ya estaba aplicada

Tres veces la misma trama al mouse por un acuse que ya había llegado. El
tercer test es el negativo: sin `0xC1`, `escribir()` tiene que seguir dando
`False`. Sin ese caso el parche se podía pasar devolviendo `True` siempre.

### La iluminación no estaba bloqueada

`docs/fase2.md` decía que había "18 escrituras capturadas pero **ninguna
corresponde al estado que quedó leído en el respaldo**". Es falso.

El estado que tienen los 14 respaldos desde las 19:00,
`01 00 03 a8 00 ff 00 01 09 01 b4 00 00`, recodificado da exactamente

    04 14 00 05 0f 01 00 03 a8 00 ff 00 01 09 01 b4 00 00 02 96

que el driver oficial escribió **3 veces**, en tres capturas distintas:
`soft-todo.pcap`, `soft-rates-anotados.pcap` y `soft-rate-8000-a-1000.pcap`.
El estado anterior (`…01 04 01 af 00 00`, el de la línea de base) también
tiene su trama, 2 veces.

Y es el caso **más fuerte** de Etapa 2 que dio el proyecto, porque las dos
puntas se midieron en máquinas distintas con tres horas de por medio: el driver
oficial escribió esos bytes desde Windows a las 16:16, el mouse los guardó, los
leímos desde Linux a las 19:00, y recodificar la lectura devuelve la misma
trama. Para rate y dpi las dos puntas salieron de la misma sesión.

La nota se escribió a las 19:47, con las tres capturas ya en el repo (16:21,
17:58, 19:12). **No faltó evidencia: no se hizo el cruce.** Es la misma forma
que las tres veces que el dpi engañó — una afirmación que nunca se contrastó
contra los datos que la podían separar— pero al revés: acá lo no verificado
bloqueó un comando en vez de habilitarlo.

### Lo que sí apareció al mirar el bloque de cerca

Y es más interesante que el desbloqueo. `parameterDef()` en `app.js`, cruzado
con los 15 bloques distintos de cmd 5 de las capturas:

- **El bloque no es "la luz".** Termina con `n.direction = e.responseTime` y
  `n.closeTime = e.hibernateTime`: lleva encima el tiempo de hibernación y el
  de respuesta.
- **`breathingSpeed` son dos campos en un byte**: `n.breathingSpeed = (closeTime
  & 240) | (breathingSpeed & 15)`. Los tres valores capturados —`0x03`, `0x13`,
  `0x33`— dan velocidad 3 en los tres, con la parte alta de `closeTime` en 0, 1
  y 3.
- **`LightBrightness` también**, y cambia de significado según qué pantalla
  escribió: la de parámetros mete `(closeTime & 15) << 4 | 8`, la de luz mete el
  brillo pelado. Los 15 bloques tienen el nibble bajo en 8, o sea la rama del
  `else`: **todos salieron de la pantalla de parámetros**. Así que el "brillo
  168" que este proyecto venía mostrando para el `0xa8` **no está establecido**:
  el mismo byte se explica igual como `(closeTime & 15) << 4 | 8`.
- **`lightMode` vale `0x00` en las 15 capturas.** Hay dos codificadores en el
  bundle, uno escribe el campo pelado y otro `<< 4`, y los defaults traen
  `lightMode: 80` (`0x50`), que **ya viene con el modo en el nibble alto**.
  `80 << 4` con `setUint8` desborda y da `0x00`. "El mouse está en modo 0" y "la
  app oficial se comió el campo al desplazarlo dos veces" producen el mismo
  byte y no se distinguen con estas capturas.

Lo único del bloque con significado sin ambigüedad es el **color**: pelado en
los seis codificadores del bundle, pelado en todo handler, y con dos valores
distintos atestiguados en las capturas (`00 ff 00` y `00 00 ff`).

De ahí que `--comando luz` acepte `--color RRGGBB` y nada más, y que `--valor`
ahí sea un error. No es prudencia genérica: es que no sabemos dónde cae un
"brillo 200" en ese byte.

`describir()` dejó de afirmar el brillo y ahora muestra el byte con sus dos
lecturas. Es más feo de leer y es lo que sabemos.

### Una nota para cuando se escriba

El checksum interno es una suma, así que **permutar componentes de color no lo
mueve**: pasar de verde (`00 ff 00`) a azul (`00 00 ff`) da el mismo checksum
interno *y* el mismo checksum de trama. No es un error —la aritmética está
bien— pero ahí el checksum no distingue nada y la verificación es el LED.
`primera-escritura.py` lo avisa antes de confirmar.

Y el bloque de luz está embebido en el perfil completo (cmd 10) en el offset
53, con el checksum interno al revés (`b4 01` contra `01 b4` en el bloque
suelto). O sea que un cambio de color mueve cmd 5 y cmd 10, igual que el rate.

---

## El mouse aceptó el color, y no pasó nada

Tres corridas de `primera-escritura.py --comando luz`, en el orden de la Etapa 3.

| # | Qué | Acuse | Relectura |
| - | --- | ----- | --------- |
| 23:52:58 | idempotente | `0xC1` | sin diferencias en los siete comandos |
| 23:53:23 | verde → azul (`--color 0000ff`) | `0xC1` | `greenColor 255→0`, `blueColor 0→255`, en cmd 5 y en el perfil |
| 23:53:47 | la vuelta a verde | `0xC1` | idéntico al respaldo previo a las dos |

Cero cambio neto: `respaldar.py --comparar antes-…235323 despues-…235347` da
**sin diferencias**. El camino de escritura de cmd 5 funciona.

Y las dos cosas que la herramienta anticipó antes de confirmar salieron como
decía: verde y azul suman lo mismo, así que **ni el checksum interno ni el de
trama se movieron**; y el bloque de luz está embebido en el perfil completo, así
que cmd 5 y cmd 10 se mueven juntos, igual que con el rate.

### Y ahora la parte que importa: no se ve nada

**El LED no cambió.** Y no es que la escritura fallara —el mouse acusó, guardó y
devolvió los bytes nuevos— sino que **el X8 Pro no tiene un LED que responda a
este bloque**. El único indicador que enciende es el de nivel de dpi, al cambiar
de nivel o al enchufar el USB, y ese lo pinta `Dpi_level_N_indication_flag` del
bloque de cmd 4. En modo dongle está apagado el resto del tiempo.

O sea que **la razón por la que este comando iba segundo en el orden de riesgo
no existía**. `fase2.md` decía "reversible y **visible a simple vista** (el
LED)" desde antes de la primera escritura del proyecto, y hoy, unas horas antes
de esta corrida, yo repetí esa frase y la amplifiqué: puse en la herramienta que
el LED era "la verificación más fuerte de todo el proyecto". Nunca se había
comprobado que el mouse tuviera esa luz.

Es la misma forma que el bloqueo de la iluminación de esta mañana —una
afirmación heredada que nadie cruzó contra la realidad— y sale dos veces el
mismo día sobre el mismo comando: una para bloquearlo de más, otra para
prometerle una verificación que no tiene.

**Prometer una verificación que no existe es peor que no ofrecer ninguna**,
porque el "no vi nada" se lee como fracaso justo cuando la escritura salió bien.
Corregido en `primera-escritura.py`, `fase2.md` y `AGENTS.md`.

### Por qué probablemente esos bytes son inertes

Evidencia LEÍDA, del escritor propio del modelo
(`dev/research/webapp/chunks/indexX8Pro-BTVvPdTw.js`):

```js
const o = t.parameterX8Pro.closeTime, e = o & 240, l = o & 15,
      u = p.breathingSpeed & 15;
p.breathingSpeed = e | u;
if (p.lightMode == 1 || p.lightMode == 5) { … } else p.LightBrightness = l<<4|8;
p.direction = t.parameterX8Pro.responseTime;
```

La página del X8 Pro usa el bloque de cmd 5 **solo como portador** de
`closeTime` y `responseTime`. Lee `lightMode` para elegir una rama y **nunca
asigna un color**. Encaja con los 15 bloques capturados: los 15 con el nibble
bajo de `LightBrightness` en 8 y `lightMode` en `0x00`.

Y encaja con lo de esta noche: los bytes de color se guardan, se releen y no
mueven nada. **No está probado que sean inertes** —podría haber un LED bajo un
`lightMode` que nunca pusimos— pero es lo que la evidencia sostiene. Y no se
puede zanjar sin escribir `lightMode`, que es justo el campo que no sabemos
escribir: vale `0x00` en las 15 capturas y "modo 0" no se distingue de "la app
oficial desbordó el campo". Queda abierto, y es la clase de pregunta que **no**
se responde probando.

### Dónde queda la escritura de luz, entonces

Escrita y reversible, pero **sin verificación externa**. El orden real de fuerza
de lo que el proyecto escribió:

1. **rate** — `medir-polling.py` cronometra el kernel: no depende de creerle al
   mouse ni a nuestro decodificador.
2. **dpi** — la página oficial muestra un número: software del fabricante
   leyendo los mismos bytes sin pasar por nuestro código.
3. **luz** — solo el `0xC1` y la relectura. Nada externo.

La luz quedó tercera, no segunda. El orden de la Etapa 4 estaba mal por la razón
equivocada: no porque el comando sea riesgoso —no lo es— sino porque lo que lo
hacía atractivo era falso.

---

## "LOD / parámetros" no es un comando: son tres

Siguiendo el hilo de la noche anterior —que cmd 5 lleva `closeTime` y
`responseTime`— resultó que la fila "LOD / parámetros" que `fase2.md` daba por
bloqueada por "no se capturó" **está capturada**. El
problema era otro: no existe un comando de parámetros.

La pantalla de parámetros del X8 Pro tiene tres handlers, y cada uno escribe un
bloque distinto (`chunks/indexX8Pro-BTVvPdTw.js`):

| Control | Handler | Va a |
| ------- | ------- | ---- |
| report rate | `$()` | **cmd 6**, byte `n<<4 \| n` |
| angle snapping, ripple, motion sync, sensitivityX | `S()` | **cmd 4** |
| hibernación, tiempo de respuesta | `_()` | **cmd 5** |

Los tres ya están en `p.WRITABLE`. Lo que falta no es permiso ni captura: es el
codificador de cada campo.

### Dos empaquetados que la tabla de campos no puede expresar

```js
// S(): tres interruptores y un valor, en dos bytes del bloque de DPI
M.SensitivityX = sensitivityX << 4 | ripple;
M.SensitivityY = straightLine  << 4 | motionSync;
```

O sea que `SensitivityX` y `SensitivityY` de la estructura de DPI **no son
sensibilidad**: son cuatro cosas en dos bytes. En el mouse valen `01` y `01`,
que se lee como sensitivityX 0 / ripple 1 / straightLine 0 / motionSync 1.

```js
// _(): el tiempo de hibernación, partido entre DOS bytes del bloque de luz
const o = closeTime, e = o & 240, l = o & 15;
p.breathingSpeed  = e | (p.breathingSpeed & 15);   // nibble alto
p.LightBrightness = l << 4 | 8;                    // nibble alto
p.direction = responseTime;                        // entero
```

Eso explica por fin el `0xa8` que veníamos mostrando como "brillo 168": es el
nibble bajo del tiempo de hibernación (`a`) más el `8` de la rama `else`. Y el
`0x03` del `breathingSpeed` es el nibble alto (`0`) más la velocidad (`3`).
Juntos: hibernación `0x0a` = **10**.

### La verificación, y por qué no es arbitraria

Reconstruí los dos valores en **los 16 bloques distintos** que hay entre las
capturas (web y soft) y los respaldos. Los 16 dan hibernación en 1..60 y
respuesta en 2..25, **sin una sola excepción**:

    hibernaciones : 1, 10, 17, 23, 25, 49, 60
    respuestas    : 2, 4, 9, 12, 16, 25

El 2..25 no lo elegimos: es exactamente `Math.floor(2 + 23*v/100)`, el cálculo
del control en el chunk, y las capturas tocan los dos extremos. El 1..60 tiene
la forma de un temporizador de sueño en minutos, con el máximo justo en 60.

Que sean **minutos es INFERIDO**, no medido. Pero a diferencia del LED de
anoche, **esta medición sí existe**: se deja el mouse quieto y se cronometra.

Con los nibbles cruzados los números se van del rango (195 donde debería haber
60), y eso es lo que verifica `test_parametros_de_luz`: no compara contra una
tabla que escribimos nosotros, compara contra el rango del control oficial.

### Y una corrección de anoche

Presenté "el X8 Pro no tiene UI de luces, el bloque es un portador" como
hallazgo de la sesión. **Ya estaba en el repo**: `capturas-w/web-todo.txt`
lo dice con la misma cita del chunk.

Lo cual empeora el diagnóstico en vez de mejorarlo: `fase2.md` decía "visible a
simple vista (el LED)" mientras una nota de captura del mismo día, en el mismo
repositorio, decía que el modelo no tiene luces. No faltó una inferencia; faltó
leer lo que ya estaba escrito. Es la tercera vez en dos días que el problema es
el mismo, y las tres veces sobre este comando.

### El codificador de hibernación, y por qué se puede confiar en él

Escrito el mismo día: `escribir_parametros_luz()`, con `--hibernacion` y
`--respuesta` en `primera-escritura.py`. Un campo por corrida, porque el ciclo
de la Etapa 4 es cambio chico / verificación / vuelta atrás y dos cambios juntos
rompen la segunda parte.

La prueba es la más fuerte que dio el proyecto para un codificador de campo. Las
capturas traen **siete** valores de hibernación distintos, y cada uno dejó un par
`(breathingSpeed, LightBrightness)` concreto en el bus:

    1 -> 03 18   10 -> 03 a8   17 -> 13 18   23 -> 13 78
    25 -> 13 98   49 -> 33 18   60 -> 33 c8

Alimentado con el mismo número, partiendo del bloque real del mouse, nuestro
codificador produce **el mismo par en los siete**. No es "el codificador se
reproduce a sí mismo": el número sale del rango del control oficial y los bytes
salen del bus.

Y una diferencia deliberada con el original: donde `_()` escribe el literal `8`
en el nibble bajo de `LightBrightness` —la rama `else` de
`lightMode != 1 && != 5`—, nosotros **conservamos el que trajo el mouse**. Hoy
da lo mismo (`lightMode` es 0, así que cae en esa rama), pero conservar lo leído
es lo que hace que escribir los valores actuales reproduzca el bloque byte a
byte. Fijar el literal sería escribirle al mouse una suposición sobre un campo
que no sabemos leer.

Lo que queda es la Etapa 3, y por primera vez en cmd 5 **con una verificación
externa de verdad**: poner la hibernación en 1, dejar el mouse quieto y
cronometrar. A los 10 que tiene ahora habría que esperar diez veces más.

---

## Un instrumento para lo que no se ve

El usuario probó a escribir la hibernación y se topó con lo mismo que con el color:
**el mouse no hace nada visible al hibernar**. No apaga un LED, no se
desconecta, no cambia a la vista. "Se durmió" no se puede observar.

Es la segunda vez en dos días que un campo que sabemos escribir se queda sin
verificación externa por la misma razón. Su pedido: algo que no dependa de
mirar, "quizás una medición que lo tome desde el dongle o USB".

### La señal que ya estaba

`hidraw.py` la documentaba desde siempre, en un comentario de tres líneas: el
mouse manda **solo, sin que nadie se lo pida**, un Report ID 3 con la batería.
Es tráfico de radio espontáneo. Si el mouse entra en reposo profundo, tiene que
parar o espaciarse.

O sea que el instrumento no había que inventarlo: había que darse cuenta de que
ya existía. (Cuarta vez en dos días que lo que hacía falta ya estaba escrito en
el repo.)

### Y es un metrónomo

MEDIDO con la primera corrida de `driver/scripts/medir-hibernacion.py`: **2.00 s**, con
22 huecos seguidos todos entre 1.99 y 2.01.

    huecos: 2.0 2.0 2.01 2.0 2.0 2.0 2.0 2.01 2.0 2.0 2.0 2.0 2.01
            2.0 2.0 2.0 1.99 2.01 2.0 2.0 2.0 2.0

El comentario de `hidraw.py` decía "~4 s". Corregido en los dos lados, con la
condición anotada: la medición se hizo con el mouse **en uso**. Si la cadencia
cambia en reposo, eso es justamente lo que estamos buscando.

Esa regularidad es lo que lo vuelve un instrumento y no una corazonada: con
±0.01 s de jitter, una parada no se confunde con un hueco del enlace de 2.4 GHz
—que es un enlace que pierde la mitad de los pedidos con el mouse quieto, así
que la distinción no era gratis—.

### Lo que la herramienta mide, y lo que no

Mide **cuándo para el latido**. Que eso sea la hibernación es la hipótesis, y
la salida del programa lo dice con esas palabras. Se confirma con dos corridas
a valores que difieren 10x: si el corte se mueve de ~600 s a ~60 s con el valor
que escribimos, queda medido. Un solo corte no probaría nada.

Tres decisiones que importan:

- **`O_RDONLY`.** El instrumento no le escribe un byte al mouse, y la garantía
  la sostiene el kernel. Se puede correr sin ningún permiso de escritura.
- **Vigila el nodo de eventos.** El movimiento no pasa por el nodo de
  configuración, así que sin eso no habría forma de darse cuenta de que alguien
  tocó el mouse y reinició su temporizador. Analiza **el tramo quieto más
  largo**, no el final: si el mouse se usa al cerrar una corrida larga, el
  tramo del medio sigue valiendo.
- **Guarda los cuatro bytes del latido, no solo la batería.** Si el latido no
  para pero algún byte cambia al dormirse, **el detector es ese cambio**. Es lo
  que convierte un "no paró" en un resultado en vez de un callejón. Despierto
  el payload es constante: `03 08 40 01 59`.

### La restricción práctica

El mouse es el puntero de la máquina. Mientras se use no se mide nada, y hace
falta dejarlo quieto varias veces el tiempo de hibernación. Se resuelve con un
segundo puntero o dejándolo corriendo al irse; con la hibernación en 1 alcanzan
5 minutos.

El protocolo completo, con el orden de los pasos —la línea de base **antes** de
escribir nada, para no confundir "falló la escritura" con "la señal no sirve"—
y el plan B (usbmon local, sin VM), quedó en `SIGUIENTE-SESION.md`.

---

## El mouse se durmió cuando se lo pedimos, y de paso apareció un estado que no sabíamos que existía

Etapa 3 para el tiempo de hibernación, con el protocolo de
`SIGUIENTE-SESION.md` seguido en orden: línea de base **antes** de escribir
nada, después el cambio, después la vuelta. Tres corridas de
`medir-hibernacion.py`, dos escrituras de cmd 5.

### El resultado

| Corrida | Escrito | Quietud | Último latido | Resultado |
| --- | --- | --- | --- | --- |
| 16:01 | hibernación 10 | 360 s | 358.2 s | **no paró** |
| 16:10 | hibernación 1 | 299 s | 89.1 s | **paró**, y después 211 s de silencio |
| 17:31 | hibernación 10 | 360 s | 358.9 s | **no paró** |

Las tres escrituras acusaron `0xC1` y la relectura mostró el valor pedido; la
idempotente previa no dejó una sola diferencia en los siete comandos.

Lo que hace fuerte a esto no es el corte: es el **encierro**. La corrida que
paró está entre dos que no pararon, una antes y otra después. No es deriva, no
es la batería —86% en las tres—, no es una casualidad de una tarde. El único
cambio entre medio fueron los dos bytes que escribimos.

Y la corrida que paró está bien anclada: los 478 eventos de actividad caen
**todos entre 0.31 s y 1.13 s**, o sea el arranque, y ninguno después. La
quietud empieza en 1.13 s, así que el último latido a 89.1 s son 88.0 s de
quietud real.

**El campo controla un temporizador de verdad, y se mide desde afuera.** No es
el mouse devolviéndonos los bytes que le mandamos: es su radio callándose. Es
la primera verificación externa que consigue el bloque de cmd 5, que hasta hoy
tenía dos campos escribibles y ninguna forma de comprobar ninguno —el color no
enciende nada, y la hibernación no se ve—.

### Pero no son 60 segundos

88 s no son 60 s, y con un solo punto aguantan varios modelos:

| Modelo | hib 1 | hib 2 | hib 10 |
| --- | --- | --- | --- |
| escalón de ~32 s + N·60 s | 92 | **150** | 630 |
| N·90 s | 90 | **180** | 900 |
| N·60 s pelado | 60 ✗ | 120 | 600 |

El tercero ya está en problemas: predice 60 y medimos 88. Los otros dos son
indistinguibles hoy, y los dos son compatibles con "no paró en 358 s" a
hibernación 10, así que las dos corridas de 6 minutos **no discriminan nada**
sobre la unidad: solo dicen que el corte se movió.

Una corrida de 4 minutos con `--hibernacion 2` los separa: 150 contra 180 s son
treinta segundos sobre una granularidad de 4 s. **"Minutos" sigue INFERIDO**, y
ahora hay un número concreto que no le cierra.

### El estado que no sabíamos que existía

Mirando los huecos apareció otra cosa: **el latido tiene dos cadencias**, no
una.

- **2.00 s** con el mouse recién usado — 43 huecos, rango 1.99..2.26
- **4.00 s** a partir de ~32 s de quietud — 179 huecos, rango 4.00..4.01

El salto está a los 26.1 s, 31.9 s y 30.9 s del arranque de cada corrida. Solo
la del medio está anclada a un toque real, y ahí son **31.9 s**; en las otras
dos el mouse ya venía quieto desde antes de arrancar, así que sus números son
un piso. Es un primer escalón de ahorro, anterior a la hibernación.

### Y una corrección de anoche que hay que hacerse cargo

`hidraw.py` decía **"~4 s"** desde siempre. Anoche la primera corrida del
instrumento midió 2.00 s y lo corrigió, en el código y en tres documentos, con
la frase "decía ~4 s y estaba mal".

**El "~4 s" era cierto.** Describía el mouse quieto, que es el estado en el que
transcurre casi entera cualquier medición de hibernación. La corrida de anoche
se hizo con el mouse en uso —5142 eventos de actividad en 45 s— y midió el otro
estado. Las dos eran ciertas; ninguna estaba completa, y la corrección tapó la
mitad que más falta hacía.

Anoche esto quedó anotado como condición ("la medición se hizo con el mouse EN
USO; si la cadencia cambia en reposo, eso es justamente lo que la herramienta
está buscando") y aun así el titular fue "estaba mal". La condición estaba bien
puesta y el titular la contradecía. Corregido en `hidraw.py` con los dos
estados y de dónde sale cada uno.

### Lo que se arregló del instrumento

Cuatro cosas, todas destapadas por los datos de hoy:

1. **Avisaba en cada latido lento.** Con la cadencia de 4 s eso son ~80 líneas
   por corrida diciendo lo mismo, y el aviso que importa —un hueco más largo
   que la cadencia lenta— quedaba enterrado. Ahora anuncia el escalón una vez y
   después solo los huecos de más de 8 s.
2. **Informaba una sola mediana.** En una corrida larga da 4.00 y el estado
   rápido desaparece del informe. Ahora parte los huecos en los dos grupos, da
   mediana y rango de cada uno, ubica el escalón, y **avisa si los dos vienen
   mezclados** en vez de forzarlos a dos estados.
3. **El umbral de parada tenía piso de 2.00 s.** `max(mediana*5, 2.00*5)`: en
   la corrida que paró la mediana fue 2.25 y el umbral habría sido 11 s, o sea
   menos de tres latidos lentos. Dio 20 s de casualidad, porque el otro término
   ganó. Ahora el piso es la cadencia **lenta**, que es el estado en el que
   transcurre la medición.
4. **Decía "paró a los 88 s" a secas.** El último latido no es el corte: el
   corte cae en el hueco siguiente, y con 4 s de cadencia eso son 4 s de
   incertidumbre. Ahora informa el intervalo —`entre 88s y 92s`— y lo guarda
   así en el JSON (`corte_entre_s`). Es la única forma honesta de comparar el
   número contra un valor escrito.

Y una quinta que no era un bug sino una omisión: **si no se toca el mouse en
toda la corrida, el tramo quieto arranca en el inicio de la corrida y no en el
último toque**, así que los tiempos son un piso de la quietud real. Pasó en dos
de las tres corridas de hoy. Ahora lo dice, y dice cómo anclarla: mover el
mouse al arrancar.

Los tres archivos de `mediciones/` se volvieron a pasar por el análisis nuevo y
reproducen los tres resultados, con el escalón y el intervalo del corte
agregados.

### Un cabo suelto que puede valer

`--respuesta` ya existe, con codificador verificado contra el bus, y el mouse
está en `responseTime = 9` (rango 2..25). El escalón de 2 s → 4 s cae a los
~32 s. Si ese escalón es lo que `responseTime` gobierna, **cmd 5 gana un
segundo campo con verificación externa**, y se prueba en dos minutos:
`--respuesta 2` debería adelantarlo de forma visible. Si no se mueve,
aprendimos que no es eso, que también es una medición.

---

## El X8 Pro tiene dos temporizadores de reposo, y el que faltaba explica los 88 segundos

El usuario preguntó por la hibernación profunda y dijo que esos campos tenían que
estar capturados, porque los había movido en la VM. Tenía razón en las dos
cosas, y la segunda destapa la primera.

### La pantalla de parámetros tiene tres sliders, no dos

De `dev/research/webapp/chunks/indexX8Pro-BTVvPdTw.js`:

| Control | Rango UI | Dónde viaja | Handler |
| --- | --- | --- | --- |
| `KeyResponseTime` | 4..50, paso 2 | byte 8 (`direction`), = valor/2 | `_()` |
| `Level1SleepTimer` | **0.5..30, paso 0.5** | — (ver abajo) | `k()` |
| `SleepTimer` | 1..60, paso 2 | nibbles altos de `breathingSpeed` + `LightBrightness` | `_()` |

Las etiquetas i18n confirman que son dos niveles: *"Level 1 Sleep Timer"* /
*"一级休眠时间"* y *"SleepTimer"* / *"休眠时间"*.

Y el proyecto ya tenía la otra mitad escrita:
`soft-nativo.md` lista, del `EN.xml` del software nativo, **`Sleep Time:`
y `Deep Sleep Time:`** bajo `Power Management`. Dos controles, con esos
nombres, en el otro programa. Es la quinta vez en tres días que lo que hacía
falta ya estaba en el repo.

### El byte que faltaba

El serializador de `app.js` (offset 1115592) dice literalmente:

```js
a.setUint8(o++, e.closeTime * 2), a.setUint8(o++, e.direction / 2)
```

y la lectura cierra el círculo (offset 1433656): `hibernateTime = sleepTime/2`,
con `sleepTime = t[11]`, que es el byte 7 del bloque. O sea que **el byte 7 son
medios minutos**: 1 → 0.5 min, 2 → 1 min, 12 → 6 min. Por eso `autoConfig`
tiene `hibernateTime: 0.5`, un valor que en el byte es 1.

Ese byte el proyecto lo mostraba como `closeTime` crudo y no le daba
significado. Es el temporizador de reposo corto.

### Y sí, estaba capturado

Extraje las 20 tramas de cmd 5 de las cinco capturas. El byte 7 toma **tres
valores**: 1, 2 y 12. En `soft-todo.pcap` el software nativo lo movió
**1 → 12 → 1** (t=97.9 s y t=173.0 s) mientras la hibernación de los nibbles iba
**10 → 25 → 10 por separado** (t=100.1 s). Dos sliders distintos, la misma
sesión, los dos escritos por el soft.

La web nunca lo movió: escribe 2 constante en sus diez tramas. Tiene
explicación exacta —y es una que se comprueba, no se supone—: el div del
`Level1SleepTimer` en el chunk del X8 Pro es
`I={class:"slider-demo-block",style:{display:"none"}}`. **Está oculto**, y
además `k()` lo manda a `LightBrightness`, no al byte 7.

### Los dos números del día caen en su lugar

El codificador **no toca el byte 7**, así que en las tres corridas de la mañana
el reposo corto estuvo fijo en 1 = 0.5 min = 30 s. Y:

- el escalón del latido de 2.00 s → 4.00 s cayó a los **26 / 32 / 31 s** →
  es el reposo corto, no un misterio del firmware
- el corte con `SleepTimer = 1` cayó entre **88 y 92 s** = **30 + 60**

Los temporizadores están **anidados**: el largo empieza a contar cuando entra el
corto. Los 88 s que no cerraban con 60 eran 30 + 60. La unidad es minutos.

Esto convierte el escalón, que hasta hoy era una curiosidad, en la **segunda
señal medible** de cmd 5.

### El codificador, y la prueba que da el bus

`escribir_reposo_ligero()` toca el byte 7 y el checksum, nada más. La
verificación es la más fuerte que dio el proyecto para un campo de cmd 5: las
dos escrituras del soft en `soft-todo.pcap` difieren **solo en ese byte y el
checksum**, a 74 s de distancia:

    t=23.8s   01 00 03 a8 00 ff 00 01 04 01 af 00 00
    t=97.9s   01 00 03 a8 00 ff 00 0c 04 01 ba 00 00

Nuestro codificador convierte la primera en la segunda byte a byte, checksum
incluido, y la segunda en la primera. Las dos puntas las mandó el driver
oficial. Etapa 2 cumplida para el campo. En `test_escribir_reposo_ligero`, con
la idempotencia sobre los cinco bloques conocidos y el rechazo de los valores
que no son múltiplos de 0.5.

### Tres correcciones que salen de leer el chunk entero

1. **`describir()` mostraba "respuesta 9" donde la página oficial muestra 18.**
   El byte es `KeyResponseTime/2`. Mismo tipo de error que
   `_adaptar_report_rate()` tomando el nibble equivocado.
2. **La justificación del rango 2..25 estaba mal.** El proyecto lo derivó de
   `Math.floor(2+23*v/100)`; esa fórmula existe en el chunk pero se le aplica a
   **`Level1SleepTimer`**, no a `responseTime`, y sobre su rango (0.5..30) da
   2..8. El 2..25 sale del slider propio del X8 Pro, 4..50 paso 2, dividido por
   dos. El rango estaba bien; el motivo, no.
3. **`sensitivityX` es el LOD.** El radio bound a ese campo, bajo el header
   `SilentHeight`, tiene `value:0 → "1 MM"` y `value:1 → "2 MM"`. Los tres
   switches de al lado son `straightLine → AngleSnapping`, `ripple →
   RippleControl1`, `motionSync → MotionSync`. El respaldo de fábrica
   (`SensitivityX=1`, `SensitivityY=1`) se lee entonces como LOD 1 mm, ripple
   ON, angle snapping OFF, motion sync ON. Es lo que le faltaba al codificador
   de cmd 4.

### Sobre `docs/PLAN_SUGERENCIAS.md`

Lo revisé entero contra el bundle y el código. Lo que verifiqué:

- **Cierto**: el `display:none` del `Level1SleepTimer` (literal en el chunk); la
  máquina de estados anidada y la fórmula 30 s + N·60 s; `sensitivityX` = LOD
  con 1 MM / 2 MM; el `0x10` del Report ID 3 (ya estaba en `protocol.py` como
  `NOTIF_DPI`, junto con `0x40` y `0x41`); que `CMD_WAKEUP` no debe volver a
  `READ_SUB` (lo guarda `salvaguardas.py`).
- **Falso**: que el reposo de nivel 1 esté *"fijo en firmware"*. Está oculto en
  la UI **de la web**; el software nativo lo movió tres veces en el bus y
  nosotros ya lo escribimos.
- **A medias**: `responseTime` como debounce en ms. El nombre del control y su
  rango lo hacen razonable, pero es INFERIDO del label, no medido, y el rango
  que da el documento (2..25 ms) es el del byte: la UI muestra 4..50.

---

## El corte cayó a los 630 segundos, que era la predicción

La corrida de 16 minutos con el mouse como estaba (reposo corto 0.5 min,
hibernación 10). **Corte en [628.9, 632.9] s de quietud.**

| Modelo | Predicción | Resultado |
| --- | --- | --- |
| anidado + minutos: `T_corto + N·60` | **630 s** | **DENTRO** |
| paralelo: `N·60` | 600 s | fuera |
| `N·90` | 900 s | fuera |

Con N=1 el corte fue [88, 92] y la predicción 90; con N=10, [628.9, 632.9] y la
predicción 630. **Dos puntos, una palanca de 10×, los dos aciertan.** La unidad
del temporizador profundo **son minutos, MEDIDO**.

El paralelo queda descartado sin ambigüedad: a los 600 s el mouse seguía
latiendo y siguió 29 s más. El N·90 también: paró a los 630 y no volvió.

La corrida está bien anclada: 246 eventos de actividad, **todos entre 0.48 y
1.3 s**, ninguno después. Y el payload fue uno solo (`03 08 40 01 56`) en los
167 latidos.

### Lo que no se ve, y por qué importa

Después del corte hubo **330 s de silencio** sin un solo latido y sin ningún
payload nuevo. Por el nodo de configuración no se ve **nada** más: si el
firmware tiene un tercer estado por debajo, hidraw no lo entrega. Eso deja el
plan B (usbmon sobre el bus entero) como la única forma de buscarlo, y ahora
con una ventana conocida: hay que capturar más allá de los 630 s.

### El detalle que no cierra del todo

El escalón cayó entre **32.8 y 36.8 s** de quietud, y el byte 7 dice 0.5 min =
30 s. Son 3 a 7 segundos de retardo sin explicación. Y la predicción del corte
funciona mejor con 30 que con 33 (633 se sale del intervalo medido por una
décima), así que el temporizador profundo parece arrancar en el **30 nominal**
mientras el cambio de cadencia del latido llega con unos segundos de retraso.

No es un problema del modelo —el término constante está medido en los dos
puntos— pero **que ese 30 sea el byte 7 sigue siendo INFERIDO**. Lo zanja la
corrida con `--reposo 1`: si el escalón se va a ~62 s, era el byte 7; si se
queda en ~33 s, el 30 es un preámbulo fijo del firmware y el byte 7 es otra
cosa.

---

## El reposo corto mueve el escalón, y los timers están anidados

Las dos corridas que faltaban. Un campo por corrida, las dos ancladas.

### 1. `--reposo 1` (byte 7: 1 → 2), hibernación en 10

El escalón del latido pasó de **32.75 s a 63.55 s de quietud**. El byte se
duplicó y el escalón se duplicó. No hubo corte, que es lo que correspondía: con
la hibernación en 10 caía a los 660 s, fuera de la corrida de 240 s.

**MEDIDO: el byte 7 gobierna el escalón de 2.00 s → 4.00 s.** Se acabó la
inferencia: no es un preámbulo fijo del firmware, es el campo que escribimos.

### 2. `--hibernacion 1` con el reposo ya en 1

| Modelo | Predicción | Medido: **[119.8, 123.8]** |
| --- | --- | --- |
| anidado (`T_reposo + N·60`) | **120 s** | **DENTRO** |
| preámbulo fijo (`30 + N·60`) | 90 s | fuera |

**MEDIDO: los dos temporizadores están anidados**, y el término constante de la
fórmula es el reposo corto, no una constante del firmware. El modelo queda
cerrado en sus dos parámetros:

    corte = T_reposo_corto + N x 60 s

con los dos términos verificados moviéndolos por separado. La inferencia 10 de
`AUDITORIA.md` queda cerrada.

### El retardo del escalón, que sigue ahí y ahora se puede acotar

El escalón llega unos segundos después del valor nominal, en las dos corridas:

| Reposo | Nominal | Salto observado en | Retardo |
| --- | --- | --- | --- |
| 0.5 min | 30 s | (32.75, 36.75) | 2.75 a 6.75 s |
| 1.0 min | 60 s | (63.55, 67.55) | 3.55 a 7.55 s |
| 1.0 min | 60 s | (63.83, 67.83) | 3.83 a 7.83 s |

Las tres ventanas se solapan en **3.83 a 6.75 s**, o sea un retardo constante y
no proporcional. Y el corte cae en la suma **nominal**, no en la observada: con
reposo 1 y hibernación 1 dio [119.8, 123.8] y no [123.5, 127.5]. O sea que el
temporizador profundo arranca cuando vence el nivel corto de verdad, y lo que
llega tarde es el cambio de cadencia del latido, no el estado.

---

## La página oficial lee mal los interruptores del sensor

Buscando cómo escribir cmd 4 apareció que **la página lee esos bytes con una
regla distinta de la que usa para escribirlos**. Es el tercer caso del mismo
patrón, después del dpi (I-W10) y del nibble de rate.

### Lo que escribe

`S()`, en el chunk propio del modelo:

    M.SensitivityX = sensitivityX << 4 | ripple
    M.SensitivityY = straightLine  << 4 | motionSync

### Lo que lee

`app.js` tiene dos ramas, y el X8 Pro cae en la de abajo:

```js
if (t === "MV6") { ...desempaqueta los nibbles... }
else {
  this[n].straightLine = e.dpiSettings.sensitivityX === 1;
  this[n].ripple       = e.dpiSettings.sensitivityY === 1;
}
```

Compara el **byte entero contra 1**, con los campos **cruzados**, y **nunca lee
de vuelta ni el LOD ni el motion sync**. Con el bloque de fábrica (`01 01`) la
página muestra "angle snapping ON" cuando el byte dice que está OFF.

### Que los cuatro campos son lo que decimos, medido en el bus

Los nombres salen del template del mismo chunk: el radio bound a
`sensitivityX`, bajo el header `SilentHeight`, tiene dos opciones literales
`value:0 → "1 MM"` y `value:1 → "2 MM"`. Los switches vecinos son
`straightLine → AngleSnapping`, `ripple → RippleControl1`, `motionSync →
MotionSync`.

Y en el bus hay **10 pares distintos** de (SensitivityX, SensitivityY), con los
cuatro bits en los dos estados. Entre ellos, **tres transiciones que difieren
solo en esos dos bytes** —el checksum ni se mueve, porque los nibbles se
intercambian y la suma se conserva—:

    t=81.0 -> t=93.8   0x11,0x01 -> 0x01,0x11   LOD 2mm->1mm, snapping OFF->ON
    t=89.5 -> t=98.7   0x00,0x01 -> 0x01,0x00   ripple OFF->ON, sync ON->OFF

`escribir_parametros_sensor()` las reproduce byte a byte en las dos
direcciones, y produce los diez pares del bus (`test_escribir_parametros_sensor`).

### Lo que esto significa para la aplicación de Linux

Es el mejor argumento hasta ahora para no ser un puente y ser una aplicación:
**la página oficial no puede mostrar el estado real de este mouse.** No es que
nos falte información; es que su lector está mal para este modelo. Un cliente
propio lee los cuatro campos bien porque desempaqueta como el firmware los
recibe.

`describir()` ahora muestra los cuatro, y cuando difieren de lo que mostraría la
página lo dice al lado, porque es la diferencia que va a confundir a cualquiera
que compare las dos pantallas.

### Y un riesgo operativo que hay que anotar

Los cuatro bits viajan en **todas** las escrituras de cmd 4, incluidas las trece
del barrido de dpi de a 50 en `web-todo.pcap`. Como la página los lee mal y
`sensitivityX` ni siquiera se lee de vuelta, **una escritura de dpi hecha por la
página puede devolver un estado distinto del que había**. Con `full` +
`--permitir-escritura dpi` eso pasa por nuestro puente. Es la misma familia que
I-W12, con un mecanismo concreto: está LEIDO del bundle, y se confirma con una
captura de la página conectándose con el LOD en 2 mm.

**El LOD es, además, el único campo del proyecto con verificación externa a
simple vista**: se levanta el mouse despacio y se mira a qué altura deja de
mover el puntero. Es más barata y más directa que todo lo que se verificó hasta
ahora.

---

## El LOD escrito, y un bug que reventó después de escribir

Primera escritura de cmd 4 del proyecto: LOD 1 mm → 2 mm y la vuelta, con la
idempotente antes. Las tres con `0xC1` y relectura.

### Lo que cambió, reconstruido de los respaldos

    cmd 4:  offsets [1, 49]   0x01 -> 0x11   SensitivityX y el checksum
    cmd 10: offsets [3, 51]   el reflejo en el perfil completo

**Los ocho niveles de dpi quedaron intactos en las dos corridas.** Era lo que
más importaba: viven en el mismo bloque y son lo caro de pisar sin querer.

### El bug, y por qué hubo que reconstruirlo

El resumen de arriba **el script no lo llegó a imprimir**. Los interruptores
entraron por `--comando dpi` y cayeron en la rama del informe final escrita para
el nivel de dpi, que usa `en_la_pagina`, `args.nivel` y `efectivo` — variables
que solo existen si se escribió un nivel. `UnboundLocalError`.

Conviene ser preciso con el daño: **reventó después de escribir y después de
releer**. Las escrituras salieron bien y el mouse quedó restaurado. Lo que se
perdió fue justamente la parte que confirma que no se pisó nada más, y hubo que
sacarla de los respaldos a mano.

Es la segunda vez que un camino de este script muerde (la primera fue N-H04, el
acuse perdido en las pausas), y las dos veces el síntoma apareció **después** de
que el mouse ya había hecho lo que se le pidió.

### Por qué no alcanzaba con agregar una rama

Porque el mismo error vuelve con el próximo campo. Tres cambios:

1. **El despacho es total**: cada combinación tiene su rama y hay un `else` de
   seguridad que no depende de ninguna variable condicional.
2. **`en_la_pagina` y `efectivo` se inicializan** antes del despacho.
3. **El consejo salió de `main()` y es una función pura**,
   `consejo_de_verificacion()`, que devuelve texto en vez de imprimirlo. Eso es
   lo que la vuelve probable sin un mouse enfrente.

`test_consejo_de_verificacion` la llama con las doce combinaciones que el CLI
acepta, más un `--comando dpi` sin nivel y un comando sin rama propia, que son
los que tienen que caer en el `else` sin romperse. Y comprueba que el consejo
del LOD siga mencionando la verificación a simple vista y que el de los otros
tres **no la prometa**, que sería repetir I-W15.

Verificado desactivando la rama del sensor: el test se pone rojo.

### Y una nota de método

**Ningún linter agarra esta familia de bug**: la variable sí está asignada en la
función, es el camino lo que falla. Un barrido de AST sobre los seis archivos
con lógica de despacho no encontró otros casos —los dos candidatos que salieron,
`que` y `cambiados`, son falsos positivos—, pero eso no es una garantía: la
única garantía es que el despacho sea total y que un test lo recorra entero.

---

## El LOD se verificó a simple vista, y el arreglo del informe aguantó

### El LOD

Ciclo completo: 1 mm → 2 mm → 1 mm, las dos escrituras con `0xC1` y relectura, y
el resumen confirmando que **solo se movieron `SensitivityX` y el checksum**
(más el reflejo en el perfil completo). Los ocho niveles de dpi, intactos.

**MEDIDO**, y con un método mejor que la escalera de tarjetas que se había
propuesto: con el LOD en 2 mm se levantó el mouse hasta ~2 mm y seguía
rastreando; **sin bajarlo**, se bajó el ajuste a 1 mm y dejó de moverse.

Por qué es mejor: **la altura quedó fija por construcción**. La escalera
intentaba controlar la altura entre dos pruebas separadas, y ese es justo el
punto donde una medición a mano se ensucia. Acá el mouse nunca bajó, así que el
ajuste fue la única variable y el efecto no puede venir de otro lado.

Es la primera verificación a simple vista del proyecto, y saca al LOD del grupo
de campos que solo tienen el acuse y la relectura.

**Lo que queda fuera**: los ~2 mm son a ojo, no con galga. Está medido el
**efecto del campo**, no el valor absoluto del corte de cada ajuste. Es la
diferencia entre "el campo cambia la altura de corte" —que sí— y "el ajuste alto
vale exactamente 2 mm" —que no se midió—. El protocolo de la escalera quedó
guardado en `SIGUIENTE-SESION.md` por si algún día hace falta el número.

### Y el arreglo del informe final, confirmado contra el hardware

Las mismas dos corridas que ayer reventaron con `UnboundLocalError` esta vez
salieron enteras, con el bloque de "CAMBIO lo que se pidió" que la vez anterior
hubo que reconstruir de los respaldos a mano. El despacho total funciona en el
camino real, no solo en el test.

### Estado al cierre

    reposo 0.5 min, hibernacion 10 min, LOD 1 mm, dpi nivel 1, 1000 Hz

O sea como estaba antes de la sesión. Último respaldo bueno:
`dev/models/attackshark-x8pro/respaldos/despues-de-escribir-dpi-20260910T001625.json`.

### Y `--lod` pasa a hablar en milímetros

`--lod 1` significaba **2 mm**, porque tomaba el valor del campo tal como lo
numera el radio oficial (`value:0 → "1 MM"`). Es una trampa que iba a morder a
alguien, y va en contra de algo que el proyecto ya hacía: traduce `SensitivityX`
a "LOD" y `closeTime` a "reposo" en vez de heredar los nombres del fabricante.
Heredar su numeración era el mismo error con otra cara.

Ahora `--lod 1` es 1 mm y `--lod 2` es 2 mm. **Por debajo no cambió nada**: el
campo sigue viajando como 0/1 y el codificador sigue hablando en valores de
campo, que es lo que el firmware recibe. La traducción vive en un solo lugar,
`estructuras.lod_desde_mm()`, con su test —incluida la comprobación de que
`LOD_MM` sea la inversa exacta, porque si esa traducción se invierte `--lod 1`
escribiría 2 mm y nadie se daría cuenta hasta levantar el mouse—.

Es el criterio general para la aplicación de Linux: **hacia afuera, unidades y
nombres que signifiquen algo; hacia adentro, lo que el firmware recibe.**

---

## Los botones estaban capturados desde el principio

Sesión sin tocar el mouse: se trabajó sobre el bundle y sobre las capturas ya
grabadas. Queda como directriz del proyecto que los comandos que tocan el
hardware los corre el usuario, no el asistente —está en `AGENTS.md`—.

### La premisa que estaba mal

`SIGUIENTE-SESION.md` decía que botones y macros "no tienen capturas", y
eso era lo que bloqueaba el modelo de datos de la aplicación. **Para botones era
falso.** Hay **15 bloques de cmd 8** en el bus, repartidos en cuatro capturas:
`soft-todo.pcap` (10), `web-todo.pcap` (3), `soft-rates-anotados.pcap` (1) y
`soft-rate-8000-a-1000.pcap` (1).

No aparecían antes porque se los buscaba por comando en un layout de trama
supuesto. Aparecen buscando **el bloque por su contenido**, que no supone nada:
los nueve slots apagados seguidos (`01 00 00` ×9) no salen en ninguna otra cosa.

Es la lección 1 otra vez, con una vuelta de tuerca: la documentación heredada no
es evidencia **ni siquiera cuando dice que algo falta**. Una afirmación negativa
también se hereda sin verificar.

Para macros, en cambio, la doc tenía razón: cero tramas de cmd 9 en las diez
capturas. Las 22 que aparecían con un filtro flojo eran reportes de movimiento
de 7 bytes por el endpoint `0x82` donde el byte 3 vale 9 por casualidad.

### La estructura

`_fe(e)` en `app.js`, que `protocolo.md` ya nombraba como pendiente. `fixed=8`,
`sizeTotalData=59`, tres bytes por botón, checksum desde el byte 3 del buffer
—o sea `datos[1:]`, que es lo que ya calculaba `checksum_interno()`—.

El bundle **no dice cuántos botones son**: `_fe` itera sobre las claves que le
pasen. Lo dice el bloque, y sin holgura: 57 B = 1 + 18·3 + 2. **Dieciocho.** Con
17 o 19 no cierra y el checksum no caería donde cae, en los 44 respaldos y en
los 15 bloques del bus.

Las siete funciones asignadas de fábrica decodifican a algo que tiene sentido
—clic izquierdo, derecho, rueda, atrás, adelante, ciclo de dpi, tecla de modo—,
que es el ancla de que el offset es el correcto.

### Una falsa alarma, y por qué vale anotarla

`sl` (la tabla de escritura del bundle) declara `FUN_SCROLL_UP:[10,0,0]` y
`FUN_SCROLL_DOWN:[9,0,0]`; `Rve` (la de nombres) dice `9 = arriba`,
`10 = abajo`. Cruzadas. Parecía el **cuarto** caso del patrón de I-W10 e I-W24
—la página escribe con una regla y lee con otra— y se estuvo a punto de
anotarlo así.

No lo es. El bundle trae un tercer diccionario donde `FUN_SCROLL_UP` lleva
`label:"ScrollDown"` y `FUN_SCROLL_DOWN` lleva `label:"ScrollUp"`: la etiqueta
compensa el nombre. Las dos tablas coinciden. Lo único equivocado es el nombre
de la constante del fabricante.

La diferencia entre "hallazgo" y "falsa alarma" fueron dos greps más.

### Lo que sí es un desacuerdo real

**Los dos clientes oficiales escriben los slots 17 y 18 al revés uno del otro:**

    soft nativo   13 bloques    slot 17 = 0x0a, slot 18 = 0x09
    página web     3 bloques    slot 17 = 0x09, slot 18 = 0x0a

Sin una sola excepción, con los otros 16 slots iguales, y los dos son
escrituras: la comparación no la ensucia nada. El bloque con el que la web
cierra su captura —con el usuario devolviendo todo a fábrica— queda distinto del
de fábrica **exactamente en esos dos bytes**. Por el camino de la web el mouse
no vuelve a como estaba.

Cuál de los dos deja la rueda derecha **no se sabe**, igual que con las dos
fórmulas de dpi. Pero a diferencia del dpi, esto **se ve girando la rueda**:
sería la segunda verificación a simple vista del proyecto, después del LOD.

### Ninguno de los dos lee este comando

Los 15 bloques van en dirección OUT. Cero en IN. Y no es que falten lecturas en
las capturas: `web-arranque-dpi-y-rate.pcap` trae la respuesta del mouse para
luz y para dpi cuando la página se conecta, y ahí no hay ningún bloque de
botones. Los dos clientes escriben desde su propio estado guardado y **nunca
releen**.

Hubo un rodeo acá que conviene anotar: la primera lectura de `soft-todo.pcap` y
`web-todo.pcap` mostró cero respuestas de cualquier comando, y se estuvo a punto
de concluir "no leen botones" desde ahí. Era una conclusión sin sustento: esas
dos capturas **no tienen lecturas de nada**, son 46 escrituras y 46 acuses. La
conclusión válida necesitaba la captura de arranque, que sí tiene lecturas y
donde tampoco aparecen los botones.

### Y de ahí sale la inferencia 14, que es una baranda

El soft nativo cerró su captura 16:16 devolviendo el mouse a
fábrica, y ese bloque lleva `0d 05 06` en los slots 4-6. **El respaldo de las
16:51 del mismo día lee `05 06 0d`.** Los tres valores están, corridos un lugar:

    lo escrito en 4 (ciclo de dpi) se lee en 6
    lo escrito en 5 (atrás)        se lee en 4
    lo escrito en 6 (adelante)     se lee en 5

No es una rotación global —los slots 1, 2 y 3 coinciden—. Los 44 respaldos de
esos días leen siempre lo mismo, incluidos los posteriores a la captura.

**Está INFERIDO, no medido**: es una escritura capturada contra una lectura
posterior, no un A/B, y encaja igual de bien con que la UI liste los botones en
el orden en que el usuario los ve y el firmware los guarde en el suyo.

Importa antes de que cmd 8 entre en `WRITABLE`: si el remapeo existe,
devolverle al mouse el bloque que se le leyó, tal cual, **le rota tres
botones**. Es la primera vez que el proyecto encuentra un motivo para no tratar
una relectura como idempotente, que es justamente con lo que empieza cada
Etapa 3.

### Lo que quedó en el código

`estructuras.py`: `BOTONES`, `FUNCIONES_DE_BOTON` (61 códigos), `botones_de()`,
`orden_de_rueda()` y la rama de `describir()`. `driver/tests/salvaguardas.py`:
`test_botones`, que fija el largo, el checksum contra los tres bloques reales,
las siete funciones de fábrica, el desacuerdo de la rueda y el remapeo inferido.

Verificado poniéndolo rojo a propósito con cinco mutaciones: un botón de menos,
el código 60 sacado de la tabla, la rueda de la web igualada a la del soft, los
slots remapeados apuntando a 1-3, y el bloque de fábrica corrido un byte. Las
cinco se detectan.

---

## El botón físico confirmó el remapeo, y la rueda quedó medida

Dos experimentos del usuario, los dos sin que el proyecto le escriba un byte al
mouse: el remapeo lo hizo el soft nativo y la lectura fue `respaldar.py`.

### El remapeo de un botón que se puede apretar

Se remapeó **el botón del costado-adelante** a "reproducir / pausar" con el soft
nativo, y se leyó desde Linux. Contra el respaldo anterior cambió **un solo
slot, el 5** —de `06` (adelante) a `18` (reproducir / pausar)—, más el checksum
y su reflejo en el perfil completo. Los otros diecisiete, intactos.

Eso cierra la cadena de la inferencia 14, porque el soft escribe "adelante" en
**su** slot 6:

    escrito 4 (ciclo de dpi) -> leído 6
    escrito 5 (atrás)        -> leído 4
    escrito 6 (adelante)     -> leído 5   <- confirmado con el botón físico

El valor del experimento es que **el botón del costado-adelante es real y se
puede apretar**: que su remapeo caiga en el slot 5 leído, cuando el soft lo
escribe en el 6, es una observación que no depende de ninguna tabla del bundle
ni de cómo el fabricante numere nada.

**Sigue sin ser un A/B directo**, y conviene decirlo: falta la trama de
escritura de esta sesión, que no se capturó. Lo que hay es la escritura
anterior más esta lectura. Pero la alternativa —que no haya remapeo— exige que
el soft creyera que el costado-adelante es su slot 5, que es donde él mismo
escribe `05` = atrás. Para cerrarla del todo: repetir el remapeo con usbmon
corriendo.

### La rueda, medida girándola

Con el mouse en `slot 17 = 0x0a, slot 18 = 0x09` —que es lo que se lee, y lo que
el soft escribe— **el scroll anda derecho**. Verificado a simple vista. Es la
segunda verificación visual del proyecto, después del LOD.

Y esos dos slots **no se remapean**, al revés que los del punto anterior: el
soft escribe `0a, 09` y el mouse devuelve `0a, 09`. Si se intercambiaran, se
leería `09, 0a`. O sea que acá lectura y escritura sí coinciden.

**Queda abierta la otra mitad**: que el orden de la web invierta el scroll de
verdad. Podrían ser inertes, y entonces el desacuerdo entre los dos clientes
sería cosmético. Se cierra abriendo la página oficial, tocando un botón —con eso
escribe su bloque— y girando la rueda. Con la advertencia de I-W12.

### Y un efecto colateral que hay que anotar

Abrir el soft nativo **para remapear un botón** le revirtió el dpi: el nivel 1
volvió de **1600** —escrito desde Linux— a **1200**, el de
fábrica. El `Current_Dpi_level_flag` también pasó de 1 a 2.

Ya estaba documentado que el soft reescribe el perfil entero aunque se toque un
solo control. Lo nuevo es la consecuencia medida: **se perdió un valor que
habíamos escrito nosotros**, sin que nadie tocara el dpi. Es I-W12 —la página
reescribiendo el dpi al conectarse— con el otro cliente del fabricante.

Para la aplicación propia es el mismo argumento de siempre, y ahora con los dos
clientes: cualquiera de los dos que se abra pisa el estado.

---

## El A/B cierra la inferencia 14, y aparecen los archivos del soft

### La inferencia 14 pasa a MEDIDA

`capturas-w/soft-boton4-vuelve-adelante.pcap` tiene la escritura del soft a
las **17:21:05** con `0d 05 06` en los slots 4-6, y
`dev/models/attackshark-x8pro/respaldos/20260910-172258.json` la lectura a las **17:22:58**, con `05 06 0d`.
Misma sesión, una hora y cincuenta segundos de diferencia, los otros quince
slots idénticos:

    escrito[4] ciclo de dpi -> leído[6] ciclo de dpi
    escrito[5] atrás        -> leído[4] atrás
    escrito[6] adelante     -> leído[5] adelante

Ya no hay que razonar sobre capturas de días distintos. Y de paso el botón
volvió a "adelante", que era lo que se quería hacer.

La captura confirma además lo ya sabido: el soft reescribe **el perfil entero**
—cmd 0x0c, dpi, iluminación, report rate y botones, cinco tramas en cinco
segundos— y las cinco las reproduce `build_write_frame()` idénticas.

**Y volvió a pisar el dpi**: escribió `17 2f 3f 6f 9f 8f`, o sea el nivel 1 en
1200 otra vez.

### El macro no llegó al mouse, y eso también es un dato

El bloque de cmd 9 sigue vacío —108 B de `0xff`— en los dos respaldos de hoy. El
macro se grabó y quedó **en el disco del soft**, no en el mouse: para que viaje
hay que **asignarlo a un botón**, que es lo que dispara el bloque de cmd 9. Con
el macro solo grabado no se escribe nada.

Encaja con el chunk del X8 Pro: la rama `x.value === "macro"` primero pone el
botón en función 18 con el id del macro en `p2`, y recién después llama a `Fe()`
—`Zve`— para mandar el bloque.

### Los archivos del soft, como tercera fuente

`.macro` quedó decodificado entero (ver `soft-nativo.md`): nombre en
UTF-16LE, cantidad de eventos, y eventos de 16 bytes con usage id, dirección y
retardo. El macro de prueba tiene 10 eventos de 10 ms.

**Y sirvió para confirmar los usage id de los botones dentro de un macro**, que
son **otra tabla** distinta de la de funciones de botón: 241..245 para
izquierdo, derecho, rueda, adelante y atrás. El macro grabado a mano quedó
`f1 f3 f5 f4 f2`, que se lee izquierdo, rueda, atrás, adelante, derecho —el
orden en que se apretaron—. El bundle lo declara igual, así que son dos fuentes
independientes.

Que sean tablas distintas importa: el código 2 es "clic izquierdo" entre las
funciones de botón y una tecla de teclado dentro de un macro. Hay un test que
comprueba que no se solapen.

`pro.data` aportó una **tercera** validación de la tabla de funciones —guarda
registros de 10 bytes `[indice, codigo, ...]` con los mismos códigos—, pero
**no describe el mouse**: el del directorio que el soft tocó durante la prueba
trae 17 registros con ciclo de perfil y tilt de rueda, que este modelo no tiene.
No es una permutación, son contenidos distintos. Queda anotado como algo que
**no** hay que usar como fuente de estado.

---

## Macros decodificado, la rueda cerrada, y el mouse a 8 kHz

Tres pruebas de las que quedaban pendientes en `SIGUIENTE-SESION.md`, en
el orden en que estaban planteadas. Las tres las corrió el usuario; desde Linux no se
escribió un byte.

### 1. El A/B del botón 4 salió, y ya está anotado

`capturas-w/soft-boton4-vuelve-adelante.pcap`, más
`dev/models/attackshark-x8pro/respaldos/20260910-172258.json` una hora y cincuenta segundos después. Cierra
la inferencia 14 con las dos mitades en la misma sesión.

### 2. Macros (cmd 9): de cero tramas a cuatro, y el formato cerrado

`capturas-w/soft-macro-asignado.pcap`. Lo que destraba el comando es
**asignar** el macro a un botón, no grabarlo —grabarlo solo escribe
`ms_13/macro.data` en el disco de Windows—.

**Son 111 bytes y no 131.** El chunk del X8 Pro importa `Zve`, que arma 131,
pero al mouse le llegan 111, que es el layout de la familia de `Qve`. No es
contradicción: quien escribió fue el soft nativo, que no es el bundle. La
diferencia son exactamente los veinte bytes en cero de `[8..27]` de `Zve`.

**El camino por bloques se vio correr por primera vez.** `build_write_blocks()`
era transcripción del desensamblado del helper (0x40d612) y nunca había habido
con qué contrastarla. Reproduce **las cuatro escrituras idénticas, las dos
tramas de cada una**, con sus dos checksums. Los largos son los que decía el
desensamblado —0x40 el primer trozo, 0x39 el segundo— y el byte 2 es el número
de bloque, no el opcode.

Y el dongle trata las dos tramas como **una sola** escritura: `0xC0` después de
cada una, pero el `0xC1` recién después de la segunda. En los cuatro casos.

**Los tres modos de disparo, medidos.** El byte `[3]` fue lo único que cambió
entre las cuatro escrituras: 0 → 1 → 2 → 0, con el checksum interno siguiéndolo
(`0x0c6d`, `0x0c6e`, `0x0c6f`, `0x0c6d`). El usuario vio tres opciones en el soft y
son las mismas tres del chunk del X8 Pro:

| modo | el soft nativo | el bundle |
| --- | --- | --- |
| 0 | "número de veces a reproducir", con campo numérico | `Loop` / `LoopPlayback` |
| 1 | "cualquier tecla para detener" | `Automatic` / `StopOnAnyKey` |
| 2 | "presionar y mantener, soltar para detener" | `Press` / `HoldToPlay` |

**Que el 0 sea el del contador no depende del orden en que se tocó la UI**, y
eso importa porque la nota de la captura volvió a decir "qué valor exacto
pusiste? nose". Los cuatro constructores del bundle hacen
`n===0 ? setUint8(7,a) : setUint8(7,1)`: el modo 0 es el único que usa el
parámetro de repeticiones, y es el único de los tres que la UI acompaña con un
número. La captura sola prueba que ese byte es el selector y que su rango es
0..2; el bundle dice cuál es cuál.

**El tiempo de los eventos va en milisegundos**, cruzando el bus con el archivo
del soft: el `.macro` guarda retardos de 10 ms y en el bus el byte es `0x0a`.
Con la fórmula de `Zve` —décimas de segundo— 10 ms habría viajado como 1.

Y los usage id de los cinco botones quedaron confirmados **por segunda vez**,
ahora contra el bus: `f1 f3 f5 f4 f2`, los mismos del archivo.

**Lo que sigue faltando es el layout de LECTURA.** El mouse devuelve 111 bytes
pero empiezan distinto —`01` y 108 de `0xff`, un `profileId` donde la escritura
lleva el id del macro—. Que sean la misma estructura es plausible y **no está
medido**, así que cmd 9 sigue fuera de `ESTRUCTURAS` y el decodificador nuevo
se llama `macro_escrito()`, con el nombre diciendo de qué lado es.

Se cierra con un `respaldar.py` con un macro cargado. No se llegó a hacer, por
lo que sigue.

### 3. La rueda de la web SÍ invierte el scroll, y salió cara

`capturas-w/web-rueda-orden-web.pcap`: se abrió la página oficial, se tocó
un botón, y con eso escribió su bloque con `slot 17 = 09, slot 18 = 0a`. **Al
girar la rueda, el scroll salió invertido.** Esos dos bytes no son inertes: la
página oficial rompe la rueda con solo conectarse y guardar. Tercera
verificación a simple vista del proyecto, después del LOD y del orden del soft.

**Y el precio de la prueba fue el mouse.** Para volver el scroll se le dio
"restaurar valores por defecto" en la página, y eso le puso el report rate en
**8000 Hz**, que es exactamente donde el canal de configuración no responde
desde Linux (entrada). El `respaldar.py` posterior sacó 3 de 7 y
hubo que cortarlo.

O sea que se volvió a caer en el círculo que esa entrada ya había descrito, y
por un camino que no estaba anotado: **el "restaurar valores por defecto" de la
página también sube la tasa**. La salida es la misma de siempre —bajarla con el
soft oficial en la VM— y de paso el soft reescribe el bloque de botones con
`0a, 09`, que es lo que deja la rueda derecha.

Vale como corolario de la lección de método: la prueba estaba bien diseñada y
la advertencia de I-W12 estaba anotada, pero **el modo de volver atrás no**. Si
una prueba deja el mouse en un estado que hay que revertir, el paso de vuelta
va escrito antes de correrla.

---

## El mouse volvió, y el script se contradecía solo

### La salida de los 8 kHz funcionó, y de paso quedó un A/B limpio

`medir-polling.py` midió **7696 Hz de mediana**, con el 54.8% de los intervalos
en 125 us: el mouse estaba en 8000 Hz, confirmado por fuera del protocolo.

Se bajó con el **"restablecer" del soft nativo en la VM**, que deja el report
rate en **1000 Hz** (`0x44`). Y el respaldo siguiente salió **7 de 7 a la
primera**, contra los 3 de 7 de media hora antes con el mismo código y el mismo
mouse. Es la tercera vez que se ve, y ahora con las dos mitades pegadas: **a
8 kHz el canal de configuración no responde; a 1000 Hz sale entero**.

Lo que el "restablecer" del soft deja, además del rate: la rueda en `0a, 09`
—el scroll derecho—, la iluminación con reposo 0.5 y hibernación 10, y **el
tiempo de respuesta en el byte 4** (UI 8) en vez del 9 que teníamos. El dpi del
nivel 1 vuelve a 1200 y el nivel activo pasa a 1.

### La restauración, y qué quedó

Cuatro escrituras desde Linux, una por corrida. El estado final contra
`dev/models/attackshark-x8pro/respaldos/20260910-172258.json`, que era el último bueno, difiere en **tres
bytes y todos queridos**:

```
dpi.Dpi_X_setting: '172f3f6f9f8f0000' -> '1f2f3f6f9f8f0000'   nivel 1: 1200 -> 1600
dpi.Current_Dpi_level_flag: 2 -> 1                            lo movió el soft
dpi._cola: '0fbb00000000' -> '0fc200000000'                   el checksum interno
```

Todo lo demás idéntico: rate `0x44`, respuesta 18, reposo 0.5, hibernación 10,
LOD 1 mm, ripple ON, botones y rueda.

### El bloque de macro volvió vacío, así que cmd 9 sigue abierto

`comandos.9.datos` sigue siendo `01` y 108 bytes de `0xff`. O el "restablecer"
del soft borró el macro, o desasignarlo del botón alcanzó para que el mouse lo
soltara. **El layout de LECTURA de cmd 9 sigue sin medirse**, y para cerrarlo
hay que volver a asignar un macro con el soft y leer sin tocar nada más.

### Y el script daba una alarma falsa que él mismo anunciaba

Tres de las cuatro escrituras eran idempotentes —el valor pedido era el que el
mouse ya tenía— y las tres terminaron en:

```
NO CAMBIO NADA, y se pidio un cambio. O el mouse ignoro la trama, o la
relectura trajo un estado viejo.
```

con salida 1. Y el mismo script había avisado en el paso 3: *"es el valor que
ya tiene: el paso 6 lo va a contar como que no cambio nada"*. O sea que
**predecía el diagnóstico y después lo emitía igual como si fuera una anomalía**.

No es cosmético. La escritura idempotente es con lo que **empieza** cada Etapa
3, y ahí "no cambió nada" es el resultado **bueno**, no el malo. Un script que
grita cuando todo salió bien enseña a ignorar el grito, que es justamente lo
que no se puede permitir un proyecto cuya única red son las barandas.

**El arreglo**: `primera-escritura.py` compara el bloque codificado contra el
que leyó. Si el codificador no movió un byte, la escritura *es* idempotente —lo
diga el nombre de la opción o no— y el paso 6 usa el mismo criterio que ya
usaba para las idempotentes explícitas: sin diferencias es éxito.

Y hay un test que sostiene la premisa: `test_reescribir_el_mismo_valor_no_mueve_un_byte`
comprueba, para los nueve codificadores, que reescribir el valor que el bloque
ya tiene devuelve el bloque **byte a byte igual**. Si alguno dejara de ser
idempotente, la detección de arriba se volvería mentira y el test se pone rojo.

De paso cayó una promesa vieja: el aviso de los colores que suman igual decía
*"la verificación buena acá es el LED, no el checksum"*, en un mouse donde ya
está anotado que **los bytes de color no encienden nada**. Es la lección 2 otra
vez, y esta vez en el código.

---

## Cmd 8 entra a WRITABLE, y el macro nunca se perdió

### Por qué el bloque de macro vuelve vacío: la respuesta está en la captura

La pregunta era si el macro del botón 4 "se tomó". **Se tomó**, y el bus lo
prueba tres veces: a las 18:14:50 el soft escribió el bloque de botones con el
slot 6 en `12 00 11` —función macro, id 0x11— y un segundo después el bloque de
cmd 9 con ese macro adentro; el dongle acusó `0xC1` las dos veces.

Lo que pasó es lo otro: **en la misma captura, a las 18:15:38, el último bloque
de botones devuelve ese slot a `06` (adelante)**. Es la última trama del
archivo. Cuando se leyó desde Linux —a las 18:55, después del "restablecer"—
hacía cuarenta minutos que ningún botón apuntaba al macro.

Y entre esas dos cosas no hubo ninguna lectura: los respaldos saltan de las
17:22:58 a las 18:55:41. **Nunca se leyó cmd 9 con un macro asignado**, así que
no se sabe si el bloque vuelve vacío porque el "restablecer" lo borró o porque
el mouse solo lo devuelve mientras haya un botón apuntándole. Las dos
explicaciones siguen abiertas y la próxima corrida las separa: asignar el macro
y leer **sin desasignarlo**.

Lo que sí queda descartado es que haga falta **apretar** el botón. El canal de
configuración contesta lo que tiene guardado; apretar el botón reproduciría el
macro, no lo haría legible.

### Cmd 8 entra a WRITABLE, con la Etapa 2 en dos variantes

El punto de partida es una lectura real de este mouse
(`dev/models/attackshark-x8pro/respaldos/20260910-172258.json`, 17:22:58) y los dos puntos de llegada son
escrituras reales del driver oficial, de dos capturas distintas:

```
idempotente   -> soft-boton4-vuelve-adelante.pcap  17:21:05   IDENTICO
con cambio    -> soft-macro-asignado.pcap          18:14:50   IDENTICO
```

**La segunda importa más que la primera.** Reproducir la identidad puede salir
bien copiando bytes sin entenderlos; reproducir un **cambio** —el
costado-adelante puesto en macro `0x11`, que cae en un slot distinto del que se
leyó— no.

### La escritura idempotente de cmd 8 no es devolver lo que se leyó

Es el único comando del proyecto donde la Etapa 3 no puede empezar con un
`memcpy`. Los slots 4, 5 y 6 se remapean, así que el bloque a escribir **es
distinto del leído y deja al mouse igual**. Eso vive en
`estructuras.retraducir_botones()`, y hay un test que comprueba las dos cosas a
la vez: que reproduzca la trama oficial **y** que no sea igual al bloque leído.

El checksum interno no habría avisado nunca: es una suma llana y la permutación
la deja igual —los dos bloques del A/B traen `0x0079`—.

### Dos barandas nuevas

**El clic izquierdo no se remapea.** Un mouse sin clic izquierdo no se arregla
desde ninguna interfaz, ni la oficial ni la nuestra, porque para arreglarlo hay
que poder hacer clic. Estaba escrito como advertencia en
`SIGUIENTE-SESION.md` desde hacía días; ahora es un `ValueError` en el
codificador y un `return 2` en el CLI, antes de tocar el mouse.

**Por el puente no se expone.** `cli.ESCRIBIBLES` sigue siendo `rate` y `dpi`.
Quien escribe por ahí es la página oficial, y ya está medido que su bloque de
botones invierte el scroll: permitírselo sería dejar que rompa la rueda sin que
nadie toque un control. Es la misma decisión que se tomó con `luz` (I-W23), y
ahora tiene test propio —`test_el_puente_ofrece_menos_que_writable`—, que exige
que lo ofrecido sea un subconjunto **estricto** de `WRITABLE`.

### Y macros sigue afuera de WRITABLE aunque pasó la Etapa 2

Vale la pena dejarlo escrito porque es contraintuitivo: cmd 9 reproduce sus
cuatro escrituras idénticas contra el bus, y aun así no entra. **La Etapa 3
arranca escribiéndole al mouse el valor que ya tiene, y para eso hay que poder
leerlo.** El layout de lectura de cmd 9 no se conoce. Un comando que no se
puede releer no se puede escribir con red.

### La captura de la rueda tenía adentro I-W24, y bastante más

Al revisarla de nuevo apareció lo que no se había mirado: **las lecturas de la
página sí contestaron**. Los cinco pedidos que hizo al conectarse tienen su
respuesta en el bus. O sea que lo que escribió después no salió de sus valores
por defecto: salió de haber leído el mouse y haberlo reescrito **cambiado**.

Con el usuario tocando **un** botón, la página leyó tres bloques, escribió cinco, y
los tres que leyó los escribió distintos:

| bloque | el mouse contestó | la página escribió |
| --- | --- | --- |
| cmd 4 (dpi) | `SensitivityX = 0x01`, ripple **ON** | `0x00`, ripple **OFF** |
| cmd 4 (dpi) | `Double_Flag` `20 00` | `00 20` (mueve el nivel 6) |
| cmd 5 (luz) | reposo 0.5 min, respuesta 18, verde | reposo 1 min, respuesta 8, azul |
| cmd 6 (rate) | `0x44` = 1000 Hz | `0x01`, índice 0 |

Y cmd 7 y cmd 8 los escribió **sin haberlos leído nunca** —el de botones con la
rueda invertida—.

**Eso cierra I-W24 y la inferencia 13.** No era una discrepancia de
presentación: la página apagó el ripple sin que nadie tocara ese control. Y su
propia UI mostraría "ripple ON" **antes y después**, porque lee
`SensitivityY === 1` en vez del bit que escribe. El usuario no tiene forma de
enterarse.

**El byte de rate `0x01` es nuevo**: índice 0, que no está en `RATE_HZ` ni
entre los siete valores observados (`0x14`..`0x74` del soft, `0x11`..`0x77` de
la web). Qué frecuencia deja **no se sabe**: poco después el mouse midió
8000 Hz, pero entre medio hubo un "restaurar valores por defecto" y con lo que
hay los dos eventos no se pueden separar. Queda anotado, y el CLI dejó de
decir "None Hz" cuando el byte trae un índice que la tabla no tiene.

Es, hasta hoy, el argumento más fuerte del proyecto para la aplicación propia:
**el cliente oficial no puede releer su propio estado sin corromperlo**, y no
en un campo sino en cuatro, en una sola conexión.

---

## La Etapa 3 de cmd 4 y de cmd 8, y por qué cmd 9 vuelve vacío

Ocho escrituras desde Linux, todas con `0xC1` y relectura, y ninguna sorpresa.

### Los cuatro interruptores del sensor: Etapa 3 cumplida para cmd 4

Seis escrituras, un campo por corrida, ida y vuelta:

```
--ripple 0          SensitivityX  1 -> 0
--angle-snapping 1  SensitivityY  1 -> 17   (0x11)
--motion-sync 0     SensitivityY 17 -> 16   (0x10)
--ripple 1          SensitivityX  0 -> 1
--angle-snapping 0  SensitivityY 16 -> 0
--motion-sync 1     SensitivityY  0 -> 1
```

**Lo que hay que mirar no es que cambiaran, sino que no se cruzaran.** Cada
corrida movió exactamente un campo y dejó el otro del mismo byte donde estaba:
`--angle-snapping 1` sobre `SensitivityY = 1` dio `17` y no `16`, o sea que el
motion sync sobrevivió al cambio del nibble alto; y `--angle-snapping 0` sobre
`16` dio `0` y no `1`. Eso es justo lo que la página oficial no hace: empaqueta
`lod<<4|ripple` y lee comparando el byte entero contra 1, con los campos
cruzados.

Sigue sin haber verificación externa barata para estos tres, y el CLI lo dice
en cada corrida. Lo que quedó demostrado es el camino, no el efecto.

### Y el arreglo de la falsa alarma pasó su primera prueba real

La última corrida, `--ripple 1` sobre un mouse que ya lo tenía en 1:

```
[3/6] escritura IDEMPOTENTE (ripple ON -> ON)
      el valor pedido es el que el mouse ya tiene, ...
      SIN DIFERENCIAS. El mouse quedo exactamente como estaba, que es lo que tenia que pasar.
```

Antes del arreglo eso mismo terminaba en `NO CAMBIO NADA, y se pidio un cambio`
con salida 1.

### La primera escritura de botones desde Linux, y el remapeo validado

```
--comando botones --boton costado-adelante --funcion adelante
```

El mouse tenía `12 00 11` (macro) en el slot **leído** 5. Se le escribió
`06 00 00` en el slot **escrito** 6 —el codificador traduce— y la relectura lo
devolvió en el **leído 5**, con los otros diecisiete slots intactos:

```
botones.boton5: '120011' -> '060000'
botones._cola:  '0096'   -> '0079'
```

**Esa es la validación contra el hardware de `SLOT_ESCRITO_DE_LEIDO`.** Si la
permutación estuviera mal, el cambio habría caído en otro slot y se habrían
movido tres botones. Cayó donde tenía que caer y no se movió nada más. Etapa 3
cumplida para cmd 8, y el botón responde.

### Cmd 9: el macro asignado no alcanza, y la razón está en el bundle

El respaldo de las 21:14 se tomó **con el macro `0x11` asignado a un botón**
—el bloque de cmd 8 lo muestra, `12 00 11` en el slot leído 5— y el bloque de
macro volvió igual de vacío: `01` y 108 bytes de `0xff`, checksum válido.

Eso **descarta** una de las dos explicaciones que habían quedado abiertas: no
es que el mouse solo lo devuelva mientras un botón le apunte.

Y buscando la otra apareció algo que no estaba en la documentación: **la
lectura de macros lleva un parámetro que las demás no tienen**.
`sendMacroDataCommand(macroId)` en `chunks/index-Bl1gF1oR.js`, llamada desde
`cacheMacroKey`, arma `F0 | connectionMethod | deviceNo | 0x09 | macroId` —y
ese quinto byte, que en todas las otras lecturas de la página va en cero, acá
es el **id del macro**—.

Nosotros mandamos `04 0c a0 09 6f **01** 00 00 00 00 01 29`: un `01` que es el
**perfil**, porque cmd 9 está en `CMDS_CON_PERFIL`. O sea que le estaríamos
pidiendo el macro 1, y el que existe es el 17.

**Es una hipótesis leída del bundle, no medida**, y tiene un eslabón inferido:
que el helper copie ese quinto byte al `frame[5]`. En contra juega que para
dpi, luz y rate la página manda 0 ahí y en el bus aparece `01` —el helper pone
el perfil de su tabla—, así que para cmd 9 haría falta un caso especial. **No
se cambia la trama hasta tener la captura**: mandar un parámetro distinto en
una posición cuyo significado se infiere es lo que el proyecto no hace.

Se cierra capturando a un cliente oficial **leyendo** un macro. La página lo
hace sola en cuanto se entera de uno asignado.

### La sonda del byte 5, y una corrida que el asistente no debió hacer

Se agregó `sondear.py --pedir 9 --macro-id N`, que pone el id del macro en el
byte 5 de la lectura de cmd 9 —donde los demás comandos llevan el perfil—,
siguiendo `sendMacroDataCommand(macroId)` del bundle. Es **explícita y
opcional**: el default no cambia, solo la acepta cmd 9, el rango se valida y
todo sigue pasando por `build_read_frame()`. Hay un test
(`test_sonda_de_macro_es_angosta`) que la mantiene angosta, porque el riesgo
real no es la inferencia sino que esto se convierta en el `--crudo` que el
proyecto sacó.

**Y acá hay que anotar un error de método, no de código.** Probando las
validaciones, el asistente corrió `--pedir 9 --macro-id 17` contra el mouse.
Eso rompe la regla de `AGENTS.md`: los comandos que tocan el hardware los
corre el usuario, y la regla nombra a `sondear.py` y dice "lecturas" con todas las
letras. Fue una lectura —no se escribió un byte— pero eso no la hace
permitida: el motivo de la regla es que quien está usando el mouse sepa que
hay una corrida en curso.

Lo que devolvió —**repetido y confirmado por el usuario**, ver la
entrada siguiente—:

```
04 40 00 09 6f 11 00 00 00 00 01 0a 0a f1 8a f1 ...
```

Si se confirma, es la respuesta a la última pregunta del modelo de datos:
**el layout de lectura de cmd 9 es el mismo que el de escritura** —`fixed=9`,
`sizeTotalData=111`, id `0x11`, modo 0, repeticiones 1, diez eventos que
arrancan en `0a f1 8a f1`— y también viene por el camino de bloques. Con eso
`macro_escrito()` deja de necesitar el "escrito" en el nombre.

Y quedaría una consecuencia práctica para `respaldar.py`: hoy pide cmd 9 con
el perfil y por eso siempre trae el bloque vacío. Con el id, podría sacar los
ids de los slots de cmd 8 —que los llevan en `p2`— y pedir cada macro.

---

## El último bloque del modelo de datos: cmd 9 se lee con el id

La sonda salió, corrida por quien corresponde:

```
driver/scripts/sondear.py --pedir 9 --macro-id 17

macro  datos: 11 00 00 00 00 01 0a 0a f1 8a f1 0a f3 8a f3 0a f5 8a f5
              0a f4 8a f4 0a f2 8a f2 00 ... 00 6d 0c   (checksum ok)
```

La hipótesis leída del bundle era la correcta: **la lectura de macros lleva el
id del macro en el byte 5, donde los demás comandos llevan el perfil.** Con el
perfil ahí le estábamos pidiendo el macro 1, y el que existe es el 17.

Eso cierra la última pregunta del modelo de datos. Los siete comandos que el
mouse contesta están decodificados.

### El layout leído es el de escritura, menos dos bytes

Los 111 bytes son idénticos a los que el soft nativo escribe, con una sola
excepción: **el checksum interno vuelve con los bytes al revés.**

```
escritura   ... 00 00 0c 6d
lectura     ... 00 00 6d 0c
```

La suma es la misma, `0x0c6d`. Y es una rareza de cmd 9, no del camino de
lectura: cmd 4, cmd 5 y cmd 8 devuelven su checksum interno en el mismo orden
en que se escribe —eso es justamente lo que hace posible que
`test_etapa2_ida_y_vuelta` y `test_etapa2_botones` comparen una lectura contra
una escritura y den idéntico—.

**Es la tercera baranda de la misma familia**, y vale ponerlas juntas porque
el patrón ya no es anecdótico:

| comando | lo que el mouse devuelve **no** se le puede devolver tal cual |
| --- | --- |
| cmd 8 | los slots 4, 5 y 6 vienen permutados: rotaría tres botones |
| cmd 9 | el checksum interno viene invertido |
| cmd 4 (la página) | lee los interruptores cruzados y reescribe mal |

Las tres se descubrieron midiendo, ninguna estaba documentada, y las tres
rompen la suposición más natural del mundo —que leer y escribir son la misma
estructura—. Para la aplicación propia esto deja de ser una curiosidad: es la
razón por la que el codificador y el decodificador tienen que ser funciones
distintas y no un `memcpy` con nombre.

### Lo que se hizo con eso

- `estructuras.parametros_de_macro()` reemplaza a `macro_escrito()`: sirve para
  los dos sentidos e informa cuál de los dos órdenes de checksum vio, en
  `checksumOrden`. El nombre viejo decía "escrito" porque el de lectura no se
  conocía; ya no hace falta la aclaración.
- `describir()` muestra el macro, así que aparece en `respaldar.py` y en
  `leer-captura-usb.py`.
- **`respaldar.py` respalda los macros de verdad.** Después de la tanda normal
  saca los ids de los slots de cmd 8 —que los llevan en `p2`— y pide cada uno.
  Van en una sección `macros` aparte, para no tocar la cuenta de "7 de 7" que
  `primera-escritura.py` usa como señal de salud; `comparar()` y
  `cmds_que_cambiaron()` los miran igual.

Eso último importa más de lo que parece: hasta hoy el respaldo previo a cada
escritura **no contenía los macros**. Si mañana se escribe cmd 9 y sale mal, no
había a dónde volver. La red tenía un agujero del tamaño de un comando.

### Y el dpi ya estaba

La corrida de `--comando dpi --nivel 1 --valor 1600` salió **IDEMPOTENTE**: el
nivel ya estaba en 1600 desde las 21:48 del día anterior
(`dev/models/attackshark-x8pro/respaldos/despues-de-escribir-dpi-20260910T214802.json`, `17` → `1f`). Lo
que se había leído como pendiente era un respaldo anterior a esa escritura.

---

## La primera escritura de macros, y el camino de dos tramas contra el hardware

Tres corridas de `primera-escritura.py`, en el orden de la Etapa 3. Salieron
las tres, y lo más fuerte del día no es que salieran: es **qué salió al bus**.

### Las tres tramas son las del driver oficial, byte a byte

Se compararon los hex que imprimió el CLI contra las constantes que
`driver/tests/salvaguardas.py` levantó de las capturas del soft nativo:

| corrida | trama emitida | contra |
| --- | --- | --- |
| `--comando macro --macro-id 17` | los dos trozos | `MACRO_OFICIAL[0]` de `soft-macro-asignado.pcap` — **idénticos** |
| `--comando botones --funcion macro --macro-id 17` | el bloque de cmd 8 | `BOTONES_OFICIAL_MACRO`, la misma captura — **idéntico** |
| `--comando macro --macro-id 17 --modo 2` | los dos trozos | `MACRO_OFICIAL[2]` — **idénticos** |

O sea que la regla del proyecto —nunca mandarle al mouse una secuencia que el
driver oficial no le haya mandado antes— se cumplió en el sentido más literal
posible: no una trama *equivalente*, la **misma** trama.

### Lo que quedó MEDIDO

**El camino multi-bloque funciona.** Es la primera vez que el proyecto manda un
bloque partido en dos tramas. El dongle acusó `0xC1` **después de la segunda**,
en las dos corridas de cmd 9, que es exactamente el modelo que salía de
`soft-macro-asignado.pcap`. Si hubiera acusado después de la primera, el modelo
estaba mal.

**La escritura idempotente de cmd 9 no mueve un byte.** Los siete bloques y el
macro salieron idénticos: `SIN DIFERENCIAS`. Y el bloque que se mandó **no era
el que se leyó**: difería en los dos bytes del checksum, `6d 0c` leído → `0c 6d`
escrito. Es la baranda de cmd 9, y ahora está probada contra el hardware y no
solo contra la captura.

**El modo de disparo se escribe.** `modo 0 → 2`, la relectura lo confirma, y el
diff del paso 6 tiene **una sola línea**: el bloque del macro, con el byte `[3]`
en 2 y el checksum acompañando (`0c6d` → `0c6f`). Nada más se movió.

**Y la permutación de slots de cmd 8 se revalidó.** Se escribió `12 00 11` en el
slot **escrito 6** y el mouse lo devolvió en el **leído 5**, sin mover ninguno
de los otros diecisiete. Segunda confirmación contra el hardware de
`SLOT_ESCRITO_DE_LEIDO`.

### Lo que NO quedó medido, y es la mitad que falta

Que el mouse **guardó** el modo 2 está medido. Que el modo 2 **haga** "mantener
apretado" no: eso se ve apretando el botón, y no se apretó. Hasta que se
aprete, cmd 9 tiene lo mismo que tienen el color y los tres interruptores del
sensor —el `0xC1` y la relectura—, que es justo lo que el proyecto no cuenta
como verificación externa.

**La Etapa 3 de cmd 9 queda a un paso**, y el paso es gratis: el macro ya está
asignado al costado-adelante.

### Dos defectos que solo se veían corriéndolo

Los dos son de presentación, y los dos son de la misma familia que la alarma
falsa: el que mira la salida tiene que poder creerle.

**1. `repeticiones 1 -> None`.** Al pasar del modo 0 al 2, el paso 3 anunció un
cambio de repeticiones **con el byte sin moverse**: vale 1 en los dos bloques.
`parametros_de_macro()` devuelve None fuera del modo 0 justamente para no
inventar un contador donde el byte no lo es —eso está bien—, pero el mensaje
convertía esa honestidad en un valor que cambió. Lo que se va al salir del modo
0 es el significado, no el número.

Ahora el mensaje sale de `describir_cambio_de_macro()`, que es **pura** —igual
que `consejo_de_verificacion()`, y por el mismo motivo: así se prueba sin un
mouse enfrente— y `test_mensaje_de_cambio_de_macro` recorre las nueve
combinaciones de modo.

**2. `macro 17: uno de los dos no contesto (A)`**, listado **adentro** de la
lista de cambios reales, en la corrida de botones. No era un cambio en el
mouse: el respaldo previo no traía el macro porque ningún slot lo apuntaba
todavía, y el posterior sí. Ruido en el único lugar donde conviene que no haya.

El respaldo previo ahora incluye el macro nombrado en `--macro-id` **en los dos
comandos**, no solo en `--comando macro`.

### Nota de uso

`\` seguido de un espacio no corta la línea en fish: la primera corrida de
botones murió con `unrecognized arguments`. Sin la barra anduvo.

## El botón apretado cerró cmd 9, y el chat sirvió de contador

Faltaba un paso y era gratis: apretar el botón. Se apretó, y el macro hizo lo
que el byte `[3]` decía que iba a hacer.

### Lo que quedó MEDIDO: el modo 2 es "mantener apretado"

Con el macro 17 en modo 2 y asignado al costado-adelante, **manteniendo el
botón apretado el macro se repitió una y otra vez, y al soltarlo se cortó**.
Eso es la verificación externa que le faltaba a cmd 9: no es el mouse
repitiéndonos bytes, es el mouse haciendo algo que se ve desde afuera del
protocolo.

**Y se pudo contar las repeticiones, sin instrumento.** El macro son diez
eventos —los cinco botones del mouse, press y release—, y uno de ellos es el
**clic de rueda**, que en X11 pega la selección primaria. O sea que cada vuelta
del macro deja una copia del texto seleccionado en el cuadro donde esté el
foco. Con el botón mantenido apretado salieron **ocho copias seguidas** del
mismo comando, y al soltar se cortó.

No estaba buscado, pero es un contador de vueltas honesto: lo escribe el
sistema operativo, no nuestro decodificador.

**Con esto la Etapa 3 de cmd 9 queda cumplida**, y los siete comandos del
modelo de datos están cerrados en los dos sentidos.

### Lo que NO quedó medido, y conviene decirlo

**Cuánto duró.** La estimación a ojo fue "~70 ms, muy aprox", y con el modelo
en la mano no puede ser: diez eventos de 10 ms son ~100 ms por vuelta, así que
ocho vueltas son ~0.8 s. No hace falta que cierre —el dato duro son las ocho
repeticiones y el corte al soltar, no el cronómetro— pero una estimación a ojo
no es una medición, y anotarla como si lo fuera sería justo el error que este
proyecto viene evitando. Si algún día importa el período del macro, se mide con
los timestamps de los eventos, no a ojo.

### Y el modo 0 también quedó MEDIDO, con un A/B de una sola variable

Con el macro ya en modo 0 y todavía asignado al mismo botón, **manteniéndolo
apretado salió una sola copia y paró**, donde minutos antes en modo 2 repetía
en bucle mientras estuviera apretado. Misma acción física, mismo macro, mismo
botón: la única variable fue el byte `[3]`.

    modo 2, botón mantenido apretado    ocho copias, se corta al soltar
    modo 0 x1, botón mantenido apretado UNA copia, para sola

**La condición no depende de acordarse de nada**: la prueba cae
necesariamente en la ventana entre las dos corridas de la vuelta atrás
(17:11:43 y 17:12:02), porque es la única en que el macro estuvo asignado al
botón **y** en modo 0 — después de la segunda el slot es `06 00 00` y el botón
no dispara nada. Que se haya pegado texto ubica el experimento solo.

Con eso los **tres** modos de disparo tienen su verificación: el 0 y el 2
apretando el botón, y el 1 —"cualquier tecla lo detiene"— sigue solo con el
`0xC1` y la relectura, que es lo que el proyecto no cuenta como externa.

### La vuelta atrás, las dos corridas

```
17:11:43  --comando macro --macro-id 17 --modo 0    0xC1, una sola línea de diff
17:12:02  --comando botones --boton costado-adelante --funcion adelante
                                                    0xC1, boton5 120011 -> 060000
```

El mouse quedó como estaba antes de la prueba: macro 17 en modo 0 x1, el
costado-adelante en "adelante", y ningún otro slot movido. El paso de vuelta
estaba escrito **antes** de correr la prueba, que es la lección 6 de la lista.

### Y el defecto (B), que es el (A) de la mañana dado vuelta

La corrida de botones listó, adentro de los cambios reales:

    macro 17: uno de los dos no contesto (B)

No era el enlace. `respaldar.py` saca los ids de macro de los slots de cmd 8,
así que **al desasignar el macro el respaldo posterior ya no lo trae**: el
previo lo tenía y el posterior no, y eso se imprimió como si el mouse hubiera
cambiado algo. Es exactamente el defecto del mediodía —el `(A)`, cuando el
macro todavía no lo apuntaba nadie— pero del otro lado.

El arreglo del mediodía no lo cubría: metía `--macro-id` en el respaldo previo,
y esta corrida no lleva `--macro-id` (es `--funcion adelante`). El arreglo bueno
es que **los dos respaldos se lean con la misma lista de macros**, y la lista
sale del previo, que es lo único que sabe qué había antes de escribir:

```python
despues = await respaldar.tomar_respaldo(
    canal, device, macros_extra=macros_a_releer(extra, antes))
```

`macros_a_releer()` es pura y la prueba `test_macros_del_paso_6_son_los_del_previo`
con los dos casos reales del día, en las dos direcciones. Con eso "uno de los
dos no contestó" vuelve a significar una sola cosa: que el enlace perdió el
pedido.

Es la tercera vez en dos días que el paso 6 —que es la red— mete ruido en la
lista de cambios reales. Las tres veces el bug era de presentación y ninguna
tocaba el mouse; y las tres veces se vio corriéndolo, no leyéndolo.

## La primera capa de la aplicación, sacada de un script

Con cmd 9 cerrado, el modelo de datos está completo y lo que sigue es la
aplicación. Su primer paso, según `SIGUIENTE-SESION.md`, es **una capa de
sesión que no sea el WebSocket**: `server.py` existe para hablarle a la página
oficial y arrastra todo lo que eso implica —el filtro de `Origin`, el formato
de mensajes de szslxd-tech.com—, y la aplicación no necesita nada de eso.

### Lo que se movió, y por qué estaba mal donde estaba

Leer el estado entero del mouse —los siete bloques, los reintentos que el
enlace obliga, los macros que los slots de cmd 8 apuntan— vivía adentro de
`driver/scripts/respaldar.py`. Y `driver/scripts/primera-escritura.py`, que es la herramienta
más delicada del proyecto, lo usaba **importando el otro script por ruta**:

```python
_spec = importlib.util.spec_from_file_location(
    "respaldar", Path(__file__).resolve().parent / "respaldar.py")
```

Funcionaba. Pero deja la lógica en la herramienta en vez de en la biblioteca, y
eso es exactamente lo que la aplicación no puede heredar: para leer el estado
habría que importar un script de línea de comandos.

Ahora está en `driver/src/asbridge/sesion.py`: `leer_estado()`, `incompletos()`,
`diferencias()`, `cmds_que_cambiaron()` y `macros_a_releer()`. `respaldar.py`
pasó de 294 a 145 líneas y quedó siendo lo que tiene que ser —la terminal:
elige el nodo, imprime y guarda el JSON—, y `primera-escritura.py` ya no
importa otro script.

### Dos cosas que la capa NO hace, a propósito

**No imprime.** Leer el mouse tarda minutos y quien lo corre necesita ver
avanzar la lista, así que `leer_estado()` avisa por callbacks y el formato lo
elige quien llama. El formato de la línea sí vive en la biblioteca
(`linea_de()`), porque las dos herramientas la imprimen idéntica y una salida
que se lee **mientras** corre una escritura no puede depender de cuál de los
dos la escribió. `test_linea_de_lectura` la fija, incluidas las dos formas de
no contestar, que no dicen lo mismo: "sin respuesta (lo reintento al final)" no
es "SIN RESPUESTA".

**No escribe.** Los pedidos de lectura son transferencias OUT —sin escribir no
hay nada que leer, que es N-W18— pero ninguna escritura de configuración sale
de ahí. Eso sigue detrás de las barandas de `primera-escritura.py`.

### Cómo se prueba algo que solo el hardware contesta

No se puede correr esto contra el mouse desde un test, así que
`test_sesion_lee_el_estado_entero` usa un `DeviceFalso` que contesta **bloques
que este mouse devolvió de verdad**, con el macro 17 asignado al
costado-adelante —el estado en que estuvo entre las 16:36 y las 17:12—. Fija
tres cosas: que el macro se pida **con su id sacado del slot**, que un mouse
que no contesta nada no reviente ni invente macros, y que lo que falla una vez
se vuelva a pedir y se avise.

Y una cuarta, que es la que más importa: **el JSON no cambió de forma**. Hay 82
respaldos versionados y `respaldar.py --comparar` compara uno de hoy contra el
primero de todos; si cambiaran las claves, la red de toda escritura se cortaría
en silencio. El test lo fija clave por clave, y además se comparó a mano contra
los respaldos de anoche: mismo resultado, misma salida.

### Lo que le falta a la capa

Escribir. Hoy `primera-escritura.py` tiene el procedimiento entero —respaldo,
codificar, confirmar, escribir, releer, comparar— y la aplicación va a querer
los mismos seis pasos sin una terminal. Eso es lo siguiente, y se hace con
cuidado: es el único código del proyecto que le manda bytes al mouse.

## Un macro de 250 ms se leía como dos eventos

Con el modelo de datos cerrado quedaba una rama sin leer, y no era teórica: si
alguien graba un macro con un retardo de más de 127 ms, **el decodificador lo
mostraba mal**, y eso entra al respaldo.

`Qve` en `app.js` —el constructor del layout de 111 bytes, que es el que le
llega a este mouse— parte esos eventos en cuatro bytes:

```js
if(d>127){ let c=d/100; d=d%100;
           _===0 ? (setUint8(r++,d|1), setUint8(r++,m))
                 : (d|=129, setUint8(r++,d), setUint8(r++,m));
           setUint8(r++,c); setUint8(r++,3); s++; continue }
...
l.setUint8(8, e.length+s)
```

Tres cosas salieron de leerlo entero:

**El `3` es un marcador y se puede reconocer.** No colisiona con los usage de
teclado HID —que empiezan en 4— ni con los cinco de los botones del mouse
(241..245). Por eso el decodificador puede mirar el par siguiente y decidir si
es un evento nuevo o la continuación del anterior.

**El byte 8 no cuenta eventos: cuenta pares de bytes** (`e.length+s`, donde `s`
son los largos). Avanzar de a dos bytes leyendo ese número funciona —los bytes
son los mismos—; lo que no funciona es mostrar cada par como un evento. Ese era
el bug: un macro con un solo evento de 250 ms salía como dos, el segundo con
"usage 3".

**Y el bit 0 es otro desacuerdo entre los dos clientes.** El bundle lo fuerza
en tres de los cuatro casos (`d|1` con dirección 0, `d|129` en la rama larga) y
el soft nativo no lo pone nunca: en la captura manda `0a` y `8a` para 10 ms. La
consecuencia es medible en el papel: 350 ms escritos por la página viajan como
`51 + 3 centenas` y se leen 351.

### Está INFERIDO, y el código lo dice

**No hay ninguna captura con eventos de más de 127 ms** —en la única que
existe, los diez son de 10 ms, y quien la escribió fue el soft nativo, que no
es el bundle—. Así que los eventos que salen de esta rama se marcan con
`largo: True`, `describir()` les pone un `?` y agrega que salen del bundle sin
captura que lo confirme. Es la inferencia 15 de `AUDITORIA.md`.

El test arma el bloque **con la regla de `Qve`**, no con una captura, y lo dice
en el nombre de la función: lo que fija es que el decodificador lea esa regla,
no que el mouse la use. Incluye el caso del 1 ms corrido —espera 351 donde el
autor quiso 350— porque ese desvío es del bundle, no nuestro, y esconderlo
sería inventar precisión.

Y fija lo otro que importaba: **el macro real de este mouse se sigue leyendo
igual**, diez eventos, ninguno marcado como largo.

Se cierra el día que alguien grabe un macro con un retardo largo desde el soft
nativo y lo capture. Cuesta una captura y está anotado.

## El último parámetro que faltaba, y los que no se pueden escribir

Antes de empezar la aplicación había que saber si quedaba algún comando de
parámetros sin cerrar. La pregunta no se contesta leyendo el código: se
contesta mirando **qué movió alguna vez el driver oficial**, porque un campo
que ningún cliente escribió delante de una captura no tiene Etapa 2 posible.

Así que se recorrieron las 53 escrituras de cmd 4 y las 23 de cmd 5 que hay en
`capturas-w/`, campo por campo, contando cuántos valores distintos tomó
cada uno.

### El resultado: faltaba uno solo

| campo | valores distintos en el bus | estado |
| --- | --- | --- |
| `Current_Dpi_level_flag` | **6** (1 a 6) | **faltaba, y se cerró hoy** |
| `Dpi_X_setting` / `Dpi_Y_setting` | 15 / 4 | ya tenía `escribir_nivel_dpi()` |
| `SensitivityX` / `SensitivityY` | 4 / 3 | ya tenían `escribir_parametros_sensor()` |
| `DPI_X_Double_Flag` / `DPI_Y_Double_Flag` | 3 / 2 | los mueve el codificador de dpi |
| `dpi_ON_OFF_flag` | **1** (`0x3f`) | sin evidencia |
| los 8 colores de indicador | **1** cada uno | sin evidencia |
| `Dpi_indication_type` | **1** (`2`) | sin evidencia |
| `lightMode` (cmd 5) | **1** (`0`) | sin evidencia |

Y una sorpresa que no lo era: los "cinco valores de `LightBrightness`" y los
"tres de `breathingSpeed`" **no son brillo ni velocidad**. Son los nibbles del
tiempo de hibernación, que ya tiene codificador; y los seis
valores de `direction` son el tiempo de respuesta dividido por dos. O sea que
cmd 5 no tenía nada pendiente: lo que parecía tres campos sin escribir era el
mismo dato leído con los nombres del fabricante.

### `Current_Dpi_level_flag`: cuál nivel está en uso

No es cuánto vale un nivel —eso es `--nivel N --valor N`— sino **cuál está
seleccionado**. La prueba salió con la forma más fuerte que da el proyecto:
**86 pares de escrituras reales del driver oficial que difieren solo en el byte
22 y el checksum interno**. Varios son de la misma captura y con segundos de
diferencia: `soft-todo.pcap` manda nivel 3 a t+862.96 y nivel 1 a t+865.24, que
es el usuario tocando el control en la UI.

`escribir_nivel_activo()` convierte una en la otra byte a byte, en las dos
direcciones. No hace falta creerle a ningún constructor del bundle.

### Y trae la cuarta verificación a simple vista

Los ocho `Dpi_level_N_indication_flag` del mismo bloque traen un color cada uno
—rojo, verde, azul, amarillo, cian, magenta, naranja, blanco— y **el LED de
nivel es lo único que prende en este mouse**: los bytes de color de cmd 5 no
encienden nada, medido. Así que cambiar el nivel activo se ve, y
se ve de dos maneras: el color del indicador y la velocidad del puntero.

Es la cuarta del proyecto, después del LOD y de los dos órdenes de la rueda.
`color_de_nivel()` saca el color **del propio bloque** que devolvió el mouse,
no de una tabla nuestra: la tabla solo traduce el hex a un nombre para poder
decirlo en castellano.

Falta la Etapa 3, que la corre el usuario:

```bash
driver/scripts/primera-escritura.py --comando dpi --nivel-activo 2   # el LED a verde
driver/scripts/primera-escritura.py --comando dpi --nivel-activo 1   # y la vuelta
```

### Lo que no se puede escribir, dicho como corresponde

`dpi_ON_OFF_flag`, los ocho colores de indicador, `Dpi_indication_type` y
`lightMode` **no tienen codificador porque no tienen captura**, no porque falte
trabajo de código. Escribirlos sería inventar bytes, que es justo lo que este
proyecto no hace. Se consiguen apagando un nivel o cambiando un color de
indicador desde el soft nativo en la VM, con usbmon corriendo; están anotados
como lo que son.

**Con esto los comandos de cambio de parámetros quedan cerrados hasta donde
llega la evidencia**, y lo que sigue es la aplicación.

## La documentación pasada a limpio

Con los comandos de parámetros cerrados, la documentación había crecido por
capas: catorce archivos, dos de ellos informes de auditoría de septiembre con
hallazgos ya cerrados, tres reportes de una etapa que terminó hace días, y un
`AGENTS.md` de 461 líneas que repetía lo que ya decían `protocolo.md` y esta
bitácora.

### Lo que se fue

| Archivo | Por qué |
| --- | --- |
| `docs/INFORME-AUDITORIA-VIVO.md` | Los hallazgos que seguían vivos pasaron a `evidencia.md`; el resto estaba cerrado |
| `auditoría-A.md` | Auditoría externa, ya procesada |
| `docs/fase2.md` | El plan de etapas, **cumplido**. Lo que sigue vivo de él es el método |
| `docs/PLAN_SUGERENCIAS.md` | Análisis, absorbido por la bitácora |
| `docs/reporteW.md` y `docs/reporteWsoft.md` | Las copias originales viven junto a sus capturas, en `capturas-w/` |

Git conserva todo. Y las copias originales de los dos reportes se quedaron
donde están las capturas que describen, con una nota que dice que no se
actualizan.

### Lo que quedó

```
AGENTS.md                 las reglas y el estado, para quien retome
dev/SIGUIENTE-SESION.md  cómo quedó el mouse y qué sigue
dev/metodo.md            cómo se le escribe a este mouse sin romperlo
dev/evidencia.md         qué se sabe, cómo se sabe, y qué está solo inferido
dev/protocolo.md         el protocolo, con las citas de dónde salió
dev/bitacora.md          lo que se probó contra el hardware, y lo que falló
dev/hardware.md          descriptores USB/HID
dev/captura-kvm.md       cómo capturar al driver oficial desde la VM
dev/soft-nativo.md       inventario de opciones del soft de Windows
```

**`AUDITORIA.md` pasó a `evidencia.md`** y se le cambió el nombre por una
razón: no era un informe de auditoría, era el estado epistémico del proyecto
—qué está MEDIDO, qué LEÍDO y qué INFERIDO— y llamarlo "auditoría" lo confundía
con los informes que sí lo eran. Se le actualizó el encabezado, se le agregaron
las dos filas de MEDIDO del día y cinco errores nuevos a la sección 3, que es
la más útil para alguien que llega de afuera.

**`metodo.md` es nuevo** y destila lo que quedaba vivo de `fase2.md`: la
regla de fondo, las cuatro etapas, qué cuenta como verificación, las siete
barandas del modo `full`, qué no se hace nunca y las señales de alarma. Sin los
checkboxes, que son registro y ya están acá.

**`AGENTS.md` pasó de 461 a 149 líneas.** Antes de podar cada afirmación se
verificó que estuviera en `protocolo.md`, `evidencia.md` o esta bitácora; lo
único que queda ahí es lo que hace falta para retomar: el objetivo, el orden de
lectura, las reglas, las dos trampas, el estado y los comandos.

### Y la bitácora tiene índice

53 entradas, agrupadas por fecha. Con una nota al principio que dice lo que
hasta hoy era costumbre y no estaba escrito: **las entradas no se editan
después de escritas**. Cuando una medición se corrige, la corrección va en una
entrada nueva que cita a la vieja —por eso hay afirmaciones acá que después
cambiaron, y por eso se puede ver cómo cambiaron—. Las menciones a los
documentos retirados se dejaron tal cual: una bitácora que se reescribe no
sirve de nada.

## El LED obedeció, y el propio mouse confirmó el campo

Dos corridas de `--comando dpi --nivel-activo`, y entre medio una cosa que no
estaba en el guion y resultó valer más que las dos.

### Lo que se pidió

```
19:02:01  nivel en uso 1 -> 2    0xC1, y el indicador pasó a VERDE
19:02:35  nivel en uso 5 -> 1    0xC1, y el indicador volvió a ROJO
```

El diff de las dos es de un campo: `Current_Dpi_level_flag`, su checksum
interno y el perfil completo, que lo embebe. Ningún nivel de dpi se movió,
ningún interruptor del sensor se cruzó.

**Y los colores son los que el bloque dice.** El nivel 2 trae `00ff00` y el LED
se puso verde; el nivel 1 trae `ff0000` y volvió a rojo. Hasta hoy la tabla de
los ocho `Dpi_level_N_indication_flag` estaba **LEÍDA** —los valores coincidían
con los defaults del bundle— y ahora está **MEDIDA** en tres de los ocho
puntos. El tercero es el que sigue.

### Lo que no estaba en el guion, y es lo mejor del día

Entre las dos corridas el usuario **cicló el dpi con el botón del mouse** hasta
dejarlo en turquesa, para ver si el indicador respondía. Eso convirtió la
prueba en otra cosa.

El respaldo previo a la segunda corrida leyó **nivel actual 5**. Y el nivel 5
del bloque es `00ffff`, cian. O sea: el color que se vio y el número que
nosotros leímos coinciden, **y ninguno de los dos pasó por software de
terceros**.

Comparando el respaldo posterior a la primera corrida contra el previo a la
segunda —o sea, lo que hizo el mouse **solo**, sin ningún cliente conectado—:

```
dpi.Current_Dpi_level_flag: 2 -> 5
dpi._cola: '0fc300000000' -> '0fc600000000'
```

**El firmware usa el mismo byte que nosotros escribimos, y solo ese.** Es la
primera vez en el proyecto que un campo se verifica por este camino: no
escribiéndolo y releyéndolo —que es creerle al mouse que guardó algo— sino
dejando que **el mouse lo escriba por su cuenta** y leyéndolo nosotros. El
firmware es acá un lector y escritor independiente de todo nuestro código y del
de szslxd-tech.

Con eso `Current_Dpi_level_flag` queda verificado en las **dos direcciones**:

| Dirección | Qué se hizo | Qué lo confirma |
| --- | --- | --- |
| escritura | `--nivel-activo 2`, y después 1 | el LED tomó el color del nivel pedido |
| lectura | se cicló con el botón hasta turquesa | leímos 5, y el nivel 5 del bloque es cian |

### Y de yapa, dos confirmaciones laterales

**El botón de ciclo de dpi hace lo que la tabla dice.** El slot leído 6 tiene
la función `0d`, que en la tabla de 61 funciones del bundle es "ciclo de dpi".
Apretarlo movió el nivel: la tabla se confirma en un punto más, contra el
hardware.

**Y la Etapa 3 de cmd 4 se amplía.** Ya estaba cumplida para los cuatro
interruptores del sensor y para los valores de dpi; ahora también para el
nivel en uso, que es el único campo de ese bloque con indicador propio.

**Con esto los comandos de cambio de parámetros quedan cerrados**: los cinco de
`p.WRITABLE`, con todos sus campos escribibles verificados contra el hardware.
Lo que falta —`dpi_ON_OFF_flag`, los cinco colores restantes,
`Dpi_indication_type`, `lightMode`— no tiene captura, y el modo 1 del macro no
se apretó. Lo que sigue es la aplicación.

### El mouse quedó como estaba

Nivel 1 en uso, indicador rojo, y ningún otro campo movido en las dos corridas.

## Los colores de nivel sí se pueden cambiar, y el soft nativo tiene el diálogo

Pregunta del usuario: ¿se puede personalizar el color de cada nivel de dpi? La
respuesta corta es **sí, y falta una captura**. La larga tiene tres partes, y
ninguna necesitó tocar el mouse.

### El campo admite cualquier color

Son ocho campos de 3 bytes en el bloque de cmd 4, uno por nivel
(`Dpi_level_1..8_indication_flag`). No es una paleta cerrada: cada nivel acepta
un RGB arbitrario de 24 bits. Y que el LED los usa quedó MEDIDO esta misma
tarde en tres puntos.

### La página web no puede, y ahora se sabe por qué

En `app.js` hay **tres serializadores que aceptan un array de ocho colores** y
los vuelcan al bloque:

```js
if (n && n.length >= 8) for (let c = 0; c < 8; c++) {
    const b = n[c];
    c===0 ? Wt.Dpi_level_1_indication_flag = [b.r, b.g, b.b] : ...
}
```

Pero **ninguna llamada le pasa el array**: las cuatro invocaciones que existen
(`If(n,1)`, `If(n,2)`, `Pfe(n,2)`, `Lfe(n,2)`) van con dos argumentos, así que
la rama nunca corre. Es código muerto. Y el chunk del X8 Pro —4994 bytes— no
menciona la palabra "color" ni una vez.

Eso explica por qué los ocho campos son constantes en las 53 escrituras
capturadas: **no es que nadie los haya tocado, es que por la web no se pueden
tocar.**

### El soft nativo sí, y es para este modelo

`app/res/DpiColorDialog.xml`, del instalador de Windows, es un selector de
color completo: una `ColorPalette` continua, campos **R / G / B numéricos** de
tres dígitos —o sea color arbitrario, no una lista— y dieciséis presets
llamados `mouse_dpi_color_1..16`. El nombre no deja lugar a dudas sobre qué
pinta.

Falta saber si ese diálogo le aparece al X8 Pro, y eso salió del binario:

1. Las cadenas UTF-16 del diálogo están en `0xee240` y siguientes
   (`DpiColorDialog.xml`, `DpiColorWnd`, `ColorPallet`, `r_edit`, `g_edit`,
   `b_edit`, `mouse_dpi_color_%d`).
2. Los dos métodos virtuales que las devuelven están en `0x40c888` y
   `0x40c8a0`, y la **vtable de `CDpiColorWnd`** en `0x4ef7d4`.
3. Esa vtable se referencia desde **36 lugares de `.text`, en 18 pares
   regulares**. Hay 18 modelos.
4. Por RTTI se ubicaron los constructores de las páginas:
   `CMS_12_Page` en `0x435444`, **`CMS_13_Page` en `0x440164`** y
   `CMS_14_Page` en `0x44b444`.
5. El par `0x44249f` / `0x442a96` cae **dentro del rango de la página 13**, y
   el del 12 (`0x4376df`/`0x437cd6`) y el del 14 (`0x44d70f`/`0x44dd06`) caen
   cada uno dentro del suyo. Un par por clase, en orden.

**El X8 Pro es el modelo 13**: el soft guardó el macro de este mouse en
`ms_13/macro.data` (bitácora). Así que la página que instancia
el selector de color es la de nuestro mouse.

El código alrededor de `0x442400` desarma un dword en tres bytes con `movzx` y
los guarda en la estructura del dispositivo, que es exactamente lo que haría al
aplicar un RGB elegido.

### Qué falta, y es barato

Una captura del soft cambiando un color, y con eso el campo queda escribible
como cualquier otro:

```bash
sudo dev/herramientas/capturar-vm.sh soft dpi-color-nivel1-rojo-a-violeta
```

El codificador son tres bytes y el checksum. Y la verificación es de las
buenas: **se mira el LED**.

Dos advertencias. La primera: **abrir el soft nativo pisa el dpi** (I-W12: el
nivel 1 volvió de 1600 a 1200), así que hay que revisar y volver
después. La segunda es epistémica: la captura además resuelve una hipótesis que
hoy no está descartada —que el firmware tenga la tabla de colores fija y los
bytes del bloque sean solo un reflejo—. Si el soft cambia un color y el LED
obedece, se cae sola.

### Dónde está el control, para el que vaya a capturar

No se lo encontró a simple vista, y tiene sentido: el diálogo no es una
pantalla, es un popup de 250x200 que se abre desde la propia página del modelo.
Lo que hay que buscar es el **cuadrito de color de cada nivel de dpi** en la
lista de niveles —el `color_show_control` del diálogo sugiere que el control de
origen también es un cuadrito de color—, no una opción de menú.

## El selector de color no está en la UI, y por qué la lectura del binario no alcanzaba

Se fue a buscar el selector de color de dpi al soft nativo y **no está**: las
opciones que el soft le habilita a este mouse no lo incluyen. La entrada de
anoche decía que la página del X8 Pro instancia `CDpiColorWnd`; eso sigue
siendo cierto como lectura del binario, y **no alcanza**.

### Qué probaba y qué no

Lo que se midió en el binario es que `CMS_13_Page` —la clase de la página del
modelo 13— **contiene código que construye el diálogo**. Lo que se infirió, sin
decirlo, es que ese código es alcanzable desde la interfaz. No es lo mismo, y
la diferencia es justo la que el proyecto ya se comió tres veces con el dpi: se
leyó código y se lo tomó por comportamiento.

El indicio que estaba a la vista y no se usó: las dieciocho clases de página
tienen **el mismo tamaño y la misma estructura** —los pares de instanciación
están espaciados de forma regular, con deltas idénticos (`0x5f7`, `0x52f`)—.
Eso huele a dieciocho copias de la misma clase, y en dieciocho copias el código
está aunque el control no se cree. Que exista el constructor no dice que exista
el botón que lo llama.

### Lo que sigue en pie

- El campo existe, admite un RGB arbitrario por nivel, y **el LED lo usa**:
  eso está MEDIDO(tres colores en tres niveles).
- La **página web no puede** escribirlo: su serializador acepta los ocho
  colores y ninguna llamada se los pasa. Eso también sigue en pie, y es lectura
  de código verificable.
- El soft nativo **tiene** el diálogo compilado, con paleta y R/G/B.

### Lo que cambia

Que hoy **no hay ningún cliente oficial que lo escriba**, y por lo tanto no hay
captura posible. Sin captura no hay Etapa 2, y sin Etapa 2 no se le manda al
mouse. El campo queda donde estaba: identificado, con significado medido, y sin
camino de escritura.

Quedan dos hilos, ninguno urgente:

1. **Si `ms_13` es de verdad el X8 Pro.** Sale de que el soft guardó el macro
   de este mouse en `ms_13/macro.data`, que es fuerte pero
   indirecto. Si el modelo fuera otro, la lectura del binario apuntó a la clase
   equivocada.
2. **Si el control existe pero está oculto para este firmware.** El soft podría
   crear el cuadrito de color solo cuando el dispositivo declara la capacidad.
   Se vería desensamblando qué condiciona la creación del control, que es más
   trabajo que valor por ahora.

### Y un dato del hardware que no estaba anotado

El LED de nivel de dpi **no está encendido de forma permanente**: se prende al
cambiar de nivel —con el botón o por escritura nuestra— y se apaga solo. El
otro momento en que prende es **cargando con el cable, en morado**, que es un
estado que no sale de ningún campo de cmd 4: es del firmware.

Eso explica por qué la verificación funcionó tan bien: escribir
`Current_Dpi_level_flag` dispara el mismo parpadeo que el botón.

## A 8 kHz se puede ESCRIBIR: lo que faltaba estaba en una captura vieja

El usuario quiere poder usar el mouse a 8000 Hz en Linux. Antes de tocar el hardware
había una captura sin exprimir: `soft-rate-8000-a-1000.pcap`, el driver oficial
bajando la tasa **con el mouse a 8 kHz**. Se la midió entera, y contesta la
pregunta.

### Lo medido en el bus

**La tasa, antes y después de la escritura**, calculada sobre los huecos entre
reportes de movimiento en una ventana de 6 s a cada lado:

```
antes   7825 Hz        (huecos de ~128 us)
despues 1000 Hz        (huecos de 1000 us, clavados)
```

O sea que la captura muestra el cambio **en vivo**, y el mouse estaba de verdad
a 8 kHz cuando el driver oficial le escribió.

**Y la escritura pasó**: `0xC0` y después `0xC1`, los dos acuses, con el mouse a
esa tasa. Lo mismo en las otras cuatro escrituras de la misma captura.

**El driver oficial no lee nada para hacerlo.** Son cinco escrituras, ninguna
lectura, una por segundo (1.01 s entre trama y trama, la misma pausa que usa
para los macros): cmd `0x0c`, dpi, iluminación, report rate y botones. Escribe
su estado completo desde su base de datos local, sin preguntarle nada al mouse.

### Por qué importa

Lo que está MEDIDO es que **a 8 kHz el respaldo no se
completa nunca** —tres corridas, tres incompletas—, y de ahí salió la frase "a
8000 Hz no se puede configurar el mouse desde Linux, ni siquiera leerlo". La
segunda mitad es cierta. La primera es más fuerte de lo que la evidencia
sostiene: **lo que falla son las lecturas largas, no las escrituras**.

Y encaja con la tabla: a 8 kHz pasaron siempre los tres comandos
cortos —versión, report rate, iluminación— y fallaron los largos. Una lectura
trae el bloque entero por radio desde el mouse, que es la dirección cargada por
el tráfico de movimiento; una escritura va en la otra dirección y solo vuelve
un acuse de seis bytes.

### El mouse calla cuando está quieto, y eso cambia una instrucción

En los 34 s de esa captura hay **34 silencios de más de 50 ms que suman 19.9 s**:
el 58% del tiempo el mouse no manda nada. Cuando manda, manda a su tasa
nominal. O sea que **el tráfico de movimiento existe solo mientras el mouse se
mueve**.

Eso pone en duda una instrucción que el proyecto repite en todas sus
herramientas: *"mové el mouse: el enlace pierde la mitad de los pedidos con el
mouse quieto"*. Es cierta a 1000 Hz —está medida— pero a 8 kHz mover el mouse
es justamente lo que satura el aire. **Nunca se probó leer a 8 kHz con el mouse
completamente quieto**, y las tres corridas se hicieron con la instrucción de
moverlo.

Es un experimento barato y con las dos respuestas útiles.

### Lo que queda pendiente de hacer

1. **Un camino de vuelta desde 8 kHz.** Hoy subir la tasa desde Linux es una
   trampa: `primera-escritura.py` exige en su paso 1 un respaldo **completo**,
   y a 8 kHz eso no sale nunca, así que para bajar hay que ir a la VM. La
   escritura en sí funcionaría —esta captura lo muestra—; lo que bloquea es la
   baranda, y con razón: la baranda no sabe que este caso es distinto.
2. **Probar la lectura a 8 kHz con el mouse quieto**, contra la corrida de
   referencia con el mouse en movimiento.
3. Y recién con eso, decidir si se toca la instrucción de "mové el mouse", que
   hoy vale para todo por igual.

## Las siete tasas, y un byte que nadie escribió nunca

El requisito para la aplicación es que ofrezca las mismas tasas que el soft
oficial: 125, 250, 500, 1000, 2000, 4000 y 8000 Hz. El CLI ya las escribía
todas, pero la aritmética vivía **suelta dentro de `primera-escritura.py`** —el
único lugar donde no sirve para la aplicación—, así que se movió a
`estructuras.escribir_report_rate()`, que es la capa que la app va a usar.

### Etapa 2 de las siete, contra catorce escrituras del bus

Las siete del soft están en `soft-rates-anotados.pcap` y las siete de la página
en `web-todo.pcap`:

```
soft   0x14  0x24  0x34  0x44  0x54  0x64  0x74      (nibble bajo siempre 4)
web    0x11  0x22  0x33  0x44  0x55  0x66  0x77      (los dos nibbles iguales)
```

`test_escribir_report_rate` recorre las **49 combinaciones** de la familia del
soft —partiendo de cada tasa, pedir cada otra— y las reproduce byte a byte,
incluido el complemento del tercer byte (`0xFF ^ rate`).

### Y apareció una baranda que no estaba

Nuestro codificador **respeta el nibble bajo** que venga en el bloque, porque
es INFERIDO que sea la tasa por cable y no es nuestro asunto. Eso reproduce al
soft, pero tiene una consecuencia que nadie había mirado: **si el nibble bajo
no es 4, el byte que sale no lo mandó nunca ningún cliente oficial.**

Y no es un caso teórico. La página oficial le escribió `0x01` a
este mouse —índice 0, que ninguna captura había mostrado—, dejando el nibble
bajo en 1. Con el mouse en ese estado, pedirle 1000 Hz produce `0x41`, que no
está entre los trece bytes que existen en el bus.

No se prohíbe, y el motivo importa: el mouse puede estar justo en ese estado y
ser lo que se quiere arreglar. Lo que se hace es **decirlo antes de confirmar**,
que es lo que la regla del proyecto pide cuando una trama no tiene respaldo en
una captura. `estructuras.RATE_BYTES_EN_EL_BUS` tiene los trece —el `0x44` está
en las dos familias— y `rate_byte_en_el_bus()` contesta la pregunta.

### Lo que sigue sin resolverse

Subir a 8 kHz desde Linux funciona hoy. **Bajar, no**: el paso 1 de la Etapa 3
exige un respaldo completo de los siete comandos y a esa tasa nunca sale. La
escritura en sí pasa —el driver oficial lo hizo con el mouse a 7825 Hz— así que
es una limitación de la herramienta. Queda pendiente de decisión, con el diseño
en `SIGUIENTE-SESION.md`.

## Por qué falla el respaldo a 8 kHz, y qué se puede hacer

Cuatro preguntas del usuario: por qué no se puede el respaldo completo a 8 kHz, qué
opciones hay, si existe un comando especial para esa tasa, y si el respaldo
funciona a 4k o 2k. Tres se contestan con lo que ya hay grabado.

### El tiempo de respuesta NO depende del tamaño del bloque

Medido sobre las diez lecturas que hay en el bus —las únicas dos capturas con
lecturas son de la web, a 500 y 1000 Hz—:

```
version de firmware    8 B    18.87 ms      report rate    9 B     8.37 ms
version de firmware    8 B    22.38 ms      iluminacion   15 B    16.38 ms
dpi                   56 B    15.84 ms      dpi           56 B    13.67 ms
```

Ocho bytes tardan **más** que cincuenta y seis. Todas caen entre 8 y 22 ms, sin
relación con el tamaño. Eso **descarta la explicación de ancho de banda**: si
el problema fuera mover los bytes, un bloque siete veces más grande tardaría
siete veces más.

Lo que domina es la **latencia de acceso al medio**: el mouse tiene que
conseguir su turno para contestar, y una vez que lo tiene, mandar 8 o 56 bytes
cuesta casi lo mismo.

### Con eso, el modelo de la falla se arma solo

El dongle contesta `0xC3` **ocupado**, que es lo que dice cuando ya tiene un
pedido en vuelo. Y el peor caso medido para que se libere es 2.10 s. Entonces:

1. a 8 kHz el medio está más disputado, así que la respuesta tarda más;
2. el pedido anterior sigue en vuelo cuando sale el siguiente;
3. el dongle contesta `0xC3`, y el fallo **se contagia hacia abajo en la
   lista**, que es exactamente lo que muestran las tres corridas —y por eso
   el respaldo empeora cuanto más comandos tiene, no
   cuanto más largos son—.

La frontera "pasan los cortos, fallan los largos" era una coincidencia de la
primera corrida. La entrada ya la había corregido: *"lo que hay
no es una frontera sino una probabilidad que empeora con lo que tarde la
respuesta"*. El tiempo medido ahora explica por qué.

### ¿Hay un comando especial para 8 kHz?

**No, y el driver oficial lo resuelve de otra manera: no lee.** Está medido en
`soft-rate-8000-a-1000.pcap`: con el mouse a 7825 Hz manda cinco escrituras,
cero lecturas, una por segundo, y escribe su estado completo desde su base de
datos local. No necesita leer porque se acuerda de lo que puso.

No hay ningún opcode ni `sizeTotalData` distinto para tasas altas en ninguna
captura ni en el bundle.

### ¿Funciona a 4k o a 2k?

**No se sabe, y no hay forma de saberlo con lo grabado**: las únicas lecturas
del driver oficial que existen son a 500 y 1000 Hz. A 1000 funciona (44
respaldos) y a 8000 no (tres corridas); **la zona de 2000 y 4000 nunca se
probó**, ni por nosotros ni por el driver oficial.

Es el experimento que falta, es barato y es escalonado y seguro: a 2000 y 4000,
si el respaldo sale completo, bajar la tasa es trivial porque el paso 1 de la
Etapa 3 tiene lo que pide. El único escalón con riesgo es el 8000.

### Las opciones, en orden de lo que cuestan

1. **Bajar la tasa para configurar y restaurarla al terminar.** Leer el rate
   funciona a 8 kHz (es corto) y escribirlo también (medido sobre el driver
   oficial), así que el ciclo *leer rate → bajar a 1000 → respaldo completo →
   configurar → restaurar* no afloja ninguna baranda: el respaldo completo se
   sigue exigiendo, y lo único que se escribe antes de tenerlo es el campo que
   sí se leyó. Es lo que haría cualquier herramienta sensata, y resuelve el
   problema entero.
2. **Leer con el mouse quieto.** Está medido que el mouse **no manda nada
   cuando está quieto**, así que a 8 kHz el medio estaría libre. Nadie lo
   probó: las tres corridas se hicieron con la instrucción de mover el mouse,
   que es correcta a 1000 Hz y puede ser contraproducente acá.
3. **No leer, como el soft.** La aplicación puede mantener su propio estado y
   escribir sin releer. Es lo que hace el fabricante, y es también la razón por
   la que su cliente corrompe lo que no conoce: si nunca lee, nunca se entera
   de lo que otro cambió.
4. **Por cable.** Es otro canal —Feature Reports, sin radio de por medio— así
   que el problema no existiría. Pero el código no lo soporta y no hay ninguna
   captura: es trabajo nuevo, no una opción de hoy.
5. **Más reintentos.** Ya se probó y no alcanza: la corrida con backoff de
   5.8 s más respiro entre fallos dio 3 de 7, peor que la de 5.8 s sola.

## La frontera está en 1000 Hz, no en 8000

El experimento escalonado se corrió y contestó en el primer escalón, que no era
el esperado: **a 2000 Hz el respaldo completo ya no sale.**

```
--comando rate --valor 2000     0xC1, el mouse quedó a 2000 Hz
                                (medir-polling: 500 us de mediana, 75.4%)
el respaldo POSTERIOR:          botones, macro y perfil completo SIN RESPUESTA
driver/scripts/respaldar.py            dpi, botones, macro sin respuesta -> cortado a mano
```

Así que la zona utilizable para configurar es **hasta 1000 Hz**, y el aviso que
el proyecto venía dando —"si el mouse está a 8000 Hz…"— mandaba a buscar el
problema cuatro veces más arriba de donde está. Ese texto ya se corrigió: no
nombra ninguna tasa que no se haya medido.

### Y la trampa se cerró sobre el mouse

Con el mouse a 2000 Hz, `primera-escritura.py --comando rate --valor 1000`
**tampoco puede bajarlo**: su paso 1 exige el respaldo completo, que a esa tasa
no sale. Es exactamente la trampa que la entrada de anoche describía en
condicional, y esta vez pasó de verdad: el mouse quedó arriba, sin camino de
vuelta desde Linux, y con la única salida en la VM.

### Lo que se hizo

**`driver/scripts/cambiar-rate.py`**, el camino angosto que ya estaba diseñado. Lee
cmd 6, lo guarda, muestra la trama, pide confirmación por terminal, escribe y
relee. No toma el respaldo de los siete bloques —que es justamente lo que no se
puede a esa tasa— y el campo que toca **sí** queda respaldado: se lee un
segundo antes y se guarda en `dev/models/attackshark-x8pro/respaldos/`.

La trama que produce para 2000 Hz es `04 0e 00 06 09 01 54 ab 00 00 00 00 01
21`, byte a byte la que el CLI mandó hoy, y la de 1000 Hz es la que el driver
oficial mandó en cinco capturas distintas.

**Y las herramientas dejaron de colgarse.** Antes, con tres bloques caídos, un
respaldo se peleaba cinco "ocupado" con backoff por comando más el respiro de
3 s entre uno y otro, por dos pasadas: más de un minuto de terminal trabada
para un resultado ya sabido. Ahora:

* `sesion.CORTE_TRAS_FALLOS = 3` abandona la tanda tras tres fallos seguidos
  —a 1000 Hz un fallo es intermitente, así que tres seguidos no es mala suerte,
  es el canal tomado—;
* **el bloque de rate es el semáforo**: son 7 bytes y contesta a cualquier
  tasa, así que si dice que el mouse está arriba de 1000 Hz no se hace la
  segunda pasada y se dice cómo bajarlo;
* y un Ctrl-C sale con una línea en vez de treinta de traceback de asyncio,
  diciendo lo único que importa saber: si llegó a escribir algo.

### De paso: el soft nativo pisó tres campos, no uno

Comparando el respaldo de ayer 19:02 con el de hoy 13:40 —sin ninguna escritura
nuestra en el medio, y con la visita de ayer al soft nativo para buscar el
selector de color—:

```
dpi.SensitivityY:      1 -> 17      angle snapping OFF -> ON
dpi.Dpi_X_setting:  1f.. -> 17..    nivel 1: 1600 -> 1200 dpi (Pu)
iluminacion.direction: 18 -> 8      tiempo de respuesta 18 -> 8
```

I-W12 decía que abrir el soft nativo pisa el dpi. **Pisa tres cosas**: el dpi,
el angle snapping y el tiempo de respuesta. El reposo y el color quedaron como
estaban, así que no es un "restablecer": es que su UI escribe su propio estado
en esos tres campos al abrirse, como la web con los suyos.

Vale como confirmación de por qué la aplicación propia no debe reescribir al
conectarse, y como recordatorio de que cualquier visita a un cliente oficial se
paga revisando después.

## El `0xC1` no dice que el mouse aplicó nada

`cambiar-rate.py` se corrió dos veces contra el mouse a 2000 Hz para bajarlo a
1000. Las dos veces el dongle contestó `0xC1`. Las dos veces el mouse **siguió
a 2000**, confirmado por la relectura y por `medir-polling.py` (500 us de
mediana, 77% de los intervalos).

### Lo que esto corrige

El proyecto trataba `0xC1` como "el mouse aplicó la escritura" —así estaba
escrito en `device.py`, y así lo decía el paso 5 del CLI—.
Es falso: **el acuse es del dongle**, y dice que aceptó la trama. Que el mouse
la haya aplicado lo contesta la relectura, y nada más.

No invalida ninguna escritura anterior: todas se verificaron releyendo, que es
el paso 6 de la Etapa 3. Pero sí invalida el mensaje, y el mensaje es lo que
uno lee a las tres de la tarde con el mouse trabado.

### Por qué el driver oficial sí puede, y nosotros no podíamos

Midiendo la barrida del soft (`soft-rates-anotados.pcap`) segundo a segundo,
con la tasa calculada sobre los huecos entre reportes de movimiento:

| escritura | tasa antes | tasa después |
| --- | --- | --- |
| `0x34` = 500 | 1000 | 500 |
| `0x44` = 1000 | 500 | 1000 |
| `0x54` = 2000 | 1000 | 2000 |
| `0x64` = 4000 | **2000** | **3998** |

O sea que **el mouse sí acepta un cambio de tasa estando a 2000 Hz**, y la
trama del soft es byte a byte la que arma `escribir_report_rate()`. Lo que
faltaba de nuestro lado no era el contenido.

Dos diferencias con lo que hacíamos:

1. **El soft manda una trama por segundo**, no una sola vez. Es la misma
   cadencia de 1.008 s que usa para los macros, y en la captura de la bajada
   desde 7825 Hz manda cinco tramas seguidas así.
2. **Y nadie está moviendo el mouse mientras escribe.** Nuestra instrucción de
   siempre —"mové el mouse"— está medida a 1000 Hz, donde el enlace pierde la
   mitad de los pedidos con el mouse quieto. Arriba de esa tasa el tráfico de
   movimiento es justo lo que tapa el canal, y el mouse **no manda nada cuando
   está quieto** (medido esta misma tarde). Las dos corridas fallidas se
   hicieron moviendo el mouse, porque eso es lo que el script pedía.

### Lo que se hizo

`cambiar-rate.py --intentos N` (4 por defecto): manda la trama, espera 1.008 s,
relee, y repite hasta que la relectura confirme. Y el paso 4 ahora dice **"no
muevas el mouse"** en vez de lo contrario.

Es la primera vez que el proyecto escribe con una cadencia de reintento tomada
del driver oficial en vez de una nuestra, y la primera vez que una instrucción
física cambia según la tasa.

**Lo que todavía no está medido** es cuál de las dos diferencias es la que
importa —la insistencia o la quietud—. La próxima corrida lo dice: si sale en
el primer intento con el mouse quieto, era la quietud.

## Dieciséis acuses y ni un cambio: no es la insistencia

Tres corridas más de `cambiar-rate.py` contra el mouse a 2000 Hz —4, 4 y 8
tramas—, todas con el mouse quieto. **Dieciséis `0xC1` y la tasa sin moverse.**

Eso descarta las dos hipótesis de la entrada anterior: no era la insistencia, y
no era mover el mouse. Lo que queda es que el mouse, a 2000 Hz, **no aplica un
cambio de tasa que le manda nuestro canal**, aunque el dongle acepte la trama.

### La diferencia que faltaba mirar

El driver oficial **no lee nunca**. Contado sobre sus tres capturas de rate:

```
soft-rates-anotados.pcap     11 escrituras,  0 lecturas
soft-rate-8000-a-1000.pcap    5 escrituras,  0 lecturas
soft-todo.pcap               46 escrituras,  0 lecturas
```

Sesenta y dos escrituras, cero lecturas. Mantiene su estado en su base de datos
local y nunca le pregunta nada al mouse. Nosotros, en cambio, intercalábamos
una lectura entre intento e intento —para verificar—, y una lectura es
exactamente lo que el canal disputado no aguanta: la respuesta viaja en la
dirección cargada y deja al dongle ocupado.

Así que la tanda pasó a ser como la suya: N tramas seguidas, una cada 1.008 s,
**sin leer nada en el medio**, y la verificación al final.

### Y si eso tampoco alcanza, lo que queda

1. **El comando `0x0c`.** El soft lo manda como **primera trama** de cada
   sesión, antes de dpi, iluminación, rate y botones:
   `04 0f 00 0c 0a 01 fe 01 fe 00 00 00 00 02 27` — dos pares valor+complemento,
   los dos en 1. Es el único opcode que el proyecto tiene **prohibido mandar**
   por no saber qué hace, y la prohibición sigue en pie: es decisión del usuario,
   no del asistente.

   Lo que juega a favor: son bytes literales de una captura de este mismo
   modelo, que el driver oficial manda al abrir su ventana. Lo que juega en
   contra: no sabemos qué hace, y esa es justo la razón por la que la regla
   existe.

2. **El cable.** Es otro canal —Feature Reports, sin radio— así que el problema
   no existiría. No hay código ni capturas: es trabajo nuevo.

3. **El driver oficial en la VM**, que es la salida conocida y cuesta el peaje
   de siempre: pisa el dpi, el angle snapping y el tiempo de respuesta.

### Lo que esto agrega al modelo

Hasta hoy el proyecto decía que a tasas altas "fallan las lecturas largas y las
escrituras pasan". La primera mitad sigue en pie. La segunda hay que
corregirla: **la escritura viaja y el dongle la acepta, pero el mouse no la
aplica**. Que el driver oficial sí lo logre desde 2000 Hz —medido en su
barrida— dice que es posible; lo que no sabemos es qué le falta a nuestra
secuencia.

## Cuatro hipótesis menos, y una baranda que no se podía leer

Tanda larga contra el hardware con el mouse trabado a 2000 Hz. Ninguna corrida
lo bajó, pero cuatro hipótesis quedaron descartadas y apareció un defecto
nuestro que arruinó el experimento que más prometía.

### El dongle NO contesta por el mouse

La duda era si las lecturas cortas las contestaba el dongle de una copia
propia, lo que habría invalidado todas nuestras relecturas. Se probó de la
única forma que la separa: **con el mouse apagado**.

```
driver/scripts/cambiar-rate.py          -> report rate: sin respuesta despues de 8 intentos
```

No contesta. El canal llega al mouse de verdad, y la hipótesis del caché queda
descartada.

### La re-enumeración del USB tampoco es

Se desenchufó el dongle, se volvió a enchufar, y se escribió de inmediato,
antes de mover el mouse. **Cuatro tramas, cuatro acuses, sigue a 2000 Hz.** Así
que el estado que le falta a nuestra secuencia no se arma al enumerar.

### Y la baranda que no se podía leer

El experimento bueno —dejar que la página oficial escriba el rate por nuestro
puente— se corrió dos veces y **las dos se perdieron por un defecto nuestro**:

```
16:09:47  <- ESCRIBIR report rate  0x66 = 4000 Hz
          Escribir? [escribir/no]: 16:09:48  -> presencia...
                                   16:09:50  -> presencia...
```

El mouse manda una notificación de presencia **cada dos segundos**, así que el
`Escribir? [escribir/no]:` desaparecía de la pantalla antes de que nadie
llegara a contestarlo. La confirmación interactiva es una de las siete
barandas del modo `full`, y durante meses **no se pudo leer**: nadie la había
ejercido con el mouse mandando notificaciones.

Arreglado con un filtro de logging que tapa el log de rutina mientras hay una
pregunta esperando —y **deja pasar las advertencias**, porque si el mouse se
desconecta justo ahí eso hay que verlo—. Al terminar dice cuántas líneas
ocultó. `test_la_confirmacion_no_se_tapa` lo fija.

### Lo que sí se aprendió de las dos sesiones

**La página manda exactamente nuestra trama.** Cuando se le pidió 1000 Hz armó
`04 0e 00 06 09 01 44 bb 00 00 00 00 01 21`, byte a byte la nuestra. Cuando se
le pidió 4000, `0x66` — la familia de la web, con los dos nibbles iguales.

**El canal de notificaciones funciona a 2000 Hz.** Seis cambios de nivel de dpi
hechos con el botón del mouse llegaron todos, en orden, en menos de dos
segundos.

**Y los bloques largos son probabilísticos, no imposibles.** En la primera
sesión el dpi no contestó; en la segunda **sí** —54 bytes, a los 9 segundos de
pedirlo—. Eso confirma lo que la entrada ya decía y matiza el
corte temprano de esta tarde: a 2000 Hz un respaldo completo podría salir con
suficiente paciencia, solo que tarda.

### Y algo que hay que anotar aunque no sea nuestro

**La página oficial colgó el mouse.** Al entrar a su pantalla de parámetros con
el mouse a 2000 Hz, el mouse dejó de responder por completo y hubo que sacarlo
del modo dongle con el selector físico y volver a ponerlo. No es un fallo del
puente: el puente solo le pasó las lecturas que ella pidió.

## La página lo bajó por nuestro propio puente

El mouse quedó en **1000 Hz**, medido con `medir-polling.py` (1000 us de
mediana, 61% de los intervalos). Lo bajó la página oficial de szslxd-tech,
hablando por `asbridge --mode full --permitir-escritura rate`: nuestro puente,
nuestro nodo hidraw, nuestro `device.escribir()`.

Eso deja el problema acotado a un punto: **no es el canal, no es el nodo, no es
el código de escritura y no es la trama.** Todo eso es compartido, y por ese
camino el cambio entró.

### Lo que la página mandó, y nosotros no

Ocho escrituras de rate en cuarenta segundos, con **valores distintos**:

```
t+19.2  1000 Hz (0x44)     t+35.9  2000 Hz (0x55)
t+34.4   500 Hz (0x33)     t+36.3  1000 Hz (0x44)
t+35.1  8000 Hz (0x77)     t+46.2  2000 Hz (0x55)
t+35.8  4000 Hz (0x66)     t+50.6  1000 Hz (0x44)
```

Nosotros mandábamos **la misma trama** cuatro u ocho veces seguidas. Las
diferencias candidatas, sin poder separarlas todavía:

1. **valores variados en vez de repetir uno** —si el firmware descarta un
   pedido igual al anterior, nuestras repeticiones idénticas se caían solas—;
2. **pasar por otras tasas** antes de llegar a la buscada;
3. **el ciclo de cuelgue y reconexión**: durante la sesión el mouse dejó de
   mover el puntero y hubo que sacarlo del modo dongle y volver. Puede que el
   cambio se guarde siempre y solo se haga efectivo al renegociar el enlace.

### Y el "cuelgue" no es lo que parecía

En las tres sesiones grabadas, **el mouse no dejó de mandar señales ni una
vez**: sus notificaciones de presencia llegaron cada dos segundos de principio
a fin, incluso durante las ocho escrituras seguidas.

Así que lo que se cuelga no es el enlace con el dongle sino **el stream de
movimiento**: el canal de configuración sigue vivo mientras el puntero no
responde. Por eso hace falta sacar el mouse del modo dongle y volver, que es lo
que fuerza a renegociar. Y si la hipótesis 3 es la buena, **el cuelgue no es el
fallo: es la señal de que el cambio entró**.

### Lo que queda para la próxima vez que haga falta bajar de tasa

El camino que funciona, hoy, es el puente con la página oficial:

```bash
./asbridge --backend hidraw --mode full --permitir-escritura rate \
    --sin-simulacro --conn 8k --record traza.jsonl
```

`--permitir-escritura rate` deja pasar **solo** el report rate, así que los
intentos de la página de reescribir dpi, luz y botones los bloquea la
allowlist: se evita el peaje de I-W24.

Y el experimento que separa las tres hipótesis, cuando el mouse vuelva a quedar
arriba: mandar con `cambiar-rate.py` una tanda de **valores variados** en vez
de repetir uno. Si entra, era la hipótesis 1 o 2 y se puede automatizar; si no
entra hasta reconectar, era la 3 y lo que hay que documentar es el paso físico.

## Era un bug nuestro: la trama iba empaquetada dos veces

Una revisión externa del código encontró en diez minutos lo que veinte corridas
contra el hardware no habían separado. **`driver/scripts/cambiar-rate.py` le pasaba a
`device.escribir()` la trama ya armada, y esa función vuelve a armarla.**

```python
trama = p.build_write_frame(bytes([p.CMD_REPORT_RATE, frame.sub]) + bloque)
...
if await device.escribir(trama):        # <- espera el BLOQUE, no la trama
```

Lo que salía al bus:

```
correcto   04 0e 00 06 09 01 44 bb 00 00 00 00 01 21
lo nuestro 04 13 00 04 0e 00 06 09 01 44 bb 00 00 00 00 01 21 01 5a
                    ^^ ^^  el mouse leia cmd 0x04 (dpi), sizeTotalData 14
```

Un bloque de dpi de catorce bytes no existe —son 56— así que el firmware lo
descartaba. **Y el dongle acusaba `0xC1` igual**, porque la trama es
sintácticamente válida: Report ID correcto, largo coherente, checksum bueno.

### Por qué la validación no lo agarró

`build_write_frame()` comprueba que `bloque[1]` sea el largo del bloque. Una
trama de 14 bytes declara `bloque[1] = 0x0e = 14` y mide 14: **coincide por
casualidad numérica**. La baranda que existía pasaba de largo justo en el caso
que importaba.

### Lo que esto invalida de las entradas de hoy

Las tres entradas anteriores explicaron el síntoma con hipótesis sobre el
hardware, y **todas se apoyaban en este bug**:

- *"no es la insistencia"* — las veinte tramas iban mal armadas;
- *"no es mover el mouse"* — idem, la condición física no tenía nada que ver;
- *"el mouse no aplica un cambio de tasa que le manda nuestro canal"* — nunca
  le mandamos un cambio de tasa: le mandábamos un bloque de dpi roto;
- *"la página lo logró y nosotros no"* — la página no hizo nada especial: su
  escritura pasaba por `backend.py`, que **sí** le da el bloque a
  `device.escribir()`. Los valores variados, la cadencia y el cuelgue eran
  ruido.

Lo que **sí** sigue en pie, porque no dependía del bug:

- **a 2000 Hz el respaldo completo no sale** (las lecturas son otro camino);
- **el `0xC1` es del dongle, no del mouse**: esto quedó mejor probado que
  antes, porque ahora se sabe que acusó veinte tramas que el firmware
  descartó;
- el mouse **calla cuando está quieto**, y el driver oficial **no lee nunca**;
- y el soft nativo **pisa tres campos** al abrirse.

### Lo que se arregló

1. **El bug**: `cambiar-rate.py` le pasa el bloque, como hacen `backend.py` y
   `primera-escritura.py`.
2. **La baranda**, en `build_write_frame()`: un bloque que empieza con el
   Report ID, lleva el opcode de escritura en el byte 2 y un comando conocido
   en el 3 **es una trama**, y se rechaza con un mensaje que explica el error.
   `test_no_se_empaqueta_dos_veces` lo fija para los tres comandos, y además
   comprueba que el script no vuelva a pasar la trama.
3. **El espaciado en el puente**: la página mandó seis escrituras en tres
   segundos y el mouse dejó de mover el puntero. El driver oficial nunca manda
   dos a menos de un segundo, así que el backend espacia lo que le llegue
   encimado (`PAUSA_ENTRE_ESCRITURAS`), con test.

### La lección, que es vieja y volvió a morder

**Un error de formato se ve igual que un problema de enlace.** Está escrito en
`metodo.md` como la primera trampa del proyecto, y aun así se pasaron cuatro
horas buscando explicaciones en la radio, en el firmware y en un comando sin
identificar, mientras el bug estaba en una línea de Python.

Lo que faltó fue barato: **contrastar la trama que sale con la que salió cuando
funcionó**. `primera-escritura.py` había subido la tasa a 2000 Hz sin
problemas ese mismo día; comparar sus bytes con los de `cambiar-rate.py` habría
mostrado el doble encabezado en el primer minuto.

### Y un efecto secundario del arreglo, que había que atender

Con el bug vivo, mandar cuatro tramas seguidas era inofensivo: ninguna llegaba.
**Arreglado, cada una reconfigura la radio del mouse** —y seis seguidas fue
exactamente lo que le colgó el puntero a la página—. Así que `cambiar-rate.py`
volvió al patrón sensato: **una trama, releer, y reintentar solo si no entró**.

El bucle sigue existiendo porque el enlace pierde pedidos de verdad (95% de
éxito con el mouse en movimiento, 50% quieto), no porque haya que repetir lo
que ya se aplicó.

## Las cuatro tasas, medidas, y las dos auditorías contestadas

### Las cuatro tasas funcionan desde Linux

Con el doble empaquetado arreglado, la barrida entera salió **en el primer
intento cada vez**, y verificada por fuera del protocolo:

| escrito | `medir-polling.py` |
| --- | --- |
| 2000 Hz | 500 us de mediana, 68.5% de los intervalos |
| 4000 Hz | 275 us, con el 46.7% en 250 us |
| 8000 Hz | **126 us, con el 68.9% en 125 us** (7944 Hz) |
| 1000 Hz | la vuelta, también en el primer intento |

Así que **la tasa se cambia en las dos direcciones desde Linux**, incluida la
que hasta ayer obligaba a ir a la VM. El mouse no se colgó en ninguna.

Lo que no cambia es la otra mitad: arriba de 1000 Hz el respaldo completo no
sale, así que para configurar cualquier otra cosa hay que bajar primero. Eso
sigue medido y sigue documentado.

### Y se contestaron las dos auditorías

`auditoría-A.md` (once hallazgos) y `auditoría-B.md` (cinco abiertos),
las dos. El detalle está en
[`respuesta-auditorias.md`](respuesta-auditorias.md); el resumen:

**Ocho arreglados**, y uno de ellos era funcional de verdad: el puente **no le
pasaba el id del macro** a `device.leer()`, así que cualquier macro que pidiera
la página volvía como el macro 1 —vacío, en este mouse—. Ninguna corrida lo
habría mostrado, porque la página nunca llegó a pedir un macro; lo encontró una
lectura del código.

Los otros: el diff que miraba un solo lado, el mensaje de `full` que ofrecía un
comando que el propio backend rechaza, el `except` que no cubría la desconexión
física, dos descriptores de evdev sin cerrar, un `pacman` asumido, dos
inconsistencias en `protocolo.md` y `respaldar.py --macro-id`.

**Uno no es defecto, por tercera vez**: `respaldar.py` abre `O_RDWR` porque un
pedido de lectura es una transferencia **OUT**. Ya lo habían marcado dos
veces; ahora la explicación está en la línea donde se abre el canal, para
que la cuarta no haga falta.

**Dos quedan aceptados sin hacer** —el `profileId` fijo y la pausa
interrumpible de cmd 9— por la misma razón en los dos casos: tocar código
verificado contra el bus sin una captura que lo pida.

### Lo que ninguna de las dos vio

Que `build_write_frame()` no se defendía de recibir una trama ya armada. Su
validación comparaba `bloque[1]` contra el largo, y una trama de 14 bytes
declara `0x0e` = 14 y mide 14: coincide por casualidad. Esa baranda existe
desde hoy, y es la que habría ahorrado las cuatro horas de ayer.

## Configurar a 8 kHz: bajar, hacer y volver

Pregunta del usuario: para cambiar el dpi con el mouse a 8 kHz, ¿conviene intentar
respaldar a esa tasa o descartar el respaldo? **Ninguna de las dos.**

### Por qué no respaldar a 8 kHz

Está medido que el respaldo de los siete comandos **no sale** arriba de
1000 Hz —cuatro corridas, a 2000 y a 8000—. Y hay una razón más de fondo: para
escribir el dpi hay que **leer el bloque de dpi primero**, porque el
codificador parte de lo que devolvió el mouse. Ese bloque son 54 bytes, o sea
justo de los que se caen a tasas altas.

Así que a 8 kHz no es solo que la red esté rota: es que ni siquiera se puede
armar la escritura.

### Por qué no descartar el respaldo

Porque es la Etapa 0, y sin él no hay a dónde volver. Y porque el problema no
es el respaldo: es la tasa.

### Lo que se hizo: el paso 0

`primera-escritura.py --bajar-y-restaurar`. Antes del paso 1 lee el bloque de
rate —7 bytes, contesta a cualquier tasa— y si el mouse está arriba de 1000 Hz:

1. baja a 1000 y lo verifica releyendo;
2. corre la Etapa 3 entera, con su respaldo completo de los siete comandos;
3. y **devuelve la tasa original en el `finally`**, así vale también si la
   escritura falló o si se cortó a mano.

**No afloja ninguna baranda**: el respaldo completo se sigue exigiendo, solo
que se lo toma a una tasa donde sale. Y lo único que se escribe antes de
tenerlo es el campo que se leyó un segundo antes —el rate—, que es exactamente
lo que hace `cambiar-rate.py` y por el mismo motivo.

Sin la opción, el paso 0 aborta con el mensaje que dice las dos salidas, en vez
de dejar que el paso 1 falle siete veces.

### De paso

Los dos scripts salían con un traceback de veinte líneas cuando `--hidraw`
apuntaba a un nodo que no existe. Ahora sale el mensaje, que es lo que hay que
leer. Es la misma familia que H-04 de la auditoría del agente A, que era sobre el
CLI del puente.

## Configurar a 8 kHz, medido, y la paridad con el soft

### El paso 0 funciona contra el hardware

```
driver/scripts/cambiar-rate.py --valor 8000
driver/scripts/primera-escritura.py --comando dpi --nivel 1 --valor 1600 --bajar-y-restaurar
```

Bajó a 1000 Hz, tomó el respaldo completo de los siete comandos, escribió el
nivel 1 de dpi (1200 → 1600), el diff mostró **solo dpi y el perfil completo
que lo embebe**, y devolvió la tasa: `quedo en 8000 Hz`. Verificado por fuera
con `medir-polling.py`: 126 us de mediana, 61.3% de los intervalos en 125 us.

Y el usuario confirmó lo otro que hacía falta saber: **el botón de dpi del mouse
funciona a 8 kHz**, así que la parte que usa el usuario no depende del canal de
configuración.

Con esto la respuesta a "¿se puede configurar a 8 kHz?" es **sí, bajando un
segundo y volviendo**, y sin aflojar ninguna baranda.

### Y se contestó la pregunta de paridad

¿Se pueden mapear los botones y configurar macros con las mismas opciones que
el programa de Windows? Se contestó cruzando `app/res/lan/EN.xml` del
instalador —su inventario completo de textos de interfaz— con nuestras tablas.
El detalle está en [`paridad-con-el-soft.md`](paridad-con-el-soft.md); en
corto:

**Botones: sí, menos uno.** Las 54 funciones de la tabla cubren todas las
familias que ofrece el soft —clics, doble clic, fire, dpi, multimedia,
navegador, apagado, macro— y varias que él no muestra. **Falta solo el atajo de
teclado** (código 17), que lleva modificadores en `p1` y un usage HID en `p2`:
el CLI lo rechaza a propósito en vez de escribir un slot que el mouse acusa y
que no hace nada. No hay nada que investigar —los usages son estándar—, falta
la interfaz.

**Macros: el disparo sí, la grabación no.** Los tres modos son exactamente los
tres del soft (`Loop Times`, `Any Key Press To Stop`, `Press And Hold`), y dos
están medidos apretando el botón. La lista de eventos **se lee** —usage,
dirección y tiempo en ms, incluida la rama larga— pero no se escribe: falta el
codificador, no la información.

Dos datos que salieron de paso:

* **entran 50 eventos por macro** (100 bytes de sitio, 2 por evento; 25 si
  todos pasan de 127 ms), y el contador de pares es un byte, así que el límite
  lo pone el espacio y no el contador;
* **el nombre del macro no viaja al mouse**: no hay campo en los 111 bytes, el
  soft lo guarda en su propio archivo. La aplicación va a tener que guardarlos
  ella.

### Limpieza

`src/` tenía dos trazas del puente (`traza-fase0`,
`traza-fase1`) que nunca debieron vivir en el directorio del paquete: pasaron a
`capturas-w/` con nombres que dicen qué son. Y `cambiar-rate.py` dejaba un
respaldo por consulta aunque no fuera a escribir nada —dieciséis copias del
mismo byte hoy—: ahora solo guarda cuando va a escribir.

## La mitad de escritura de la capa de sesión

Lo primero del plan de la aplicación. Hasta hoy `sesion.py` sabía leer el
estado y compararlo; el resto de la Etapa 3 vivía dentro de
`driver/scripts/primera-escritura.py`, mezclado con sus `print`, que es el único lugar
donde no le sirve a la aplicación.

Se movieron cuatro cosas, cada una con su test:

**`juzgar()` — el criterio del paso 6**, que es la red de toda la Etapa 3 y
tiene más matices de los que parece. Devuelve un `Veredicto` con un motivo
estable, y `test_veredicto_del_paso_6` recorre los seis casos, incluidos los
dos que costaron un bug cada uno: una escritura idempotente que no mueve un
byte **es un éxito**, y un cambio real tiene que mover lo que se pidió **y nada
más**, salvo el perfil completo, que embebe a los otros bloques y acompaña
siempre.

**`escribir_bloque()` — el camino lo elige el tamaño, no el comando.** El CLI
tenía un `if cmd == p.CMD_MACRO` para mandar por bloques; el criterio real es
si el bloque entra en un report de 64. Hoy da lo mismo porque el único que no
entra es el macro, pero la regla es del protocolo y ahora está escrita como tal.

**`tasa_actual()` y `poner_tasa()` — el paso 0.** Leer el bloque de rate son 7
bytes y contesta a cualquier tasa: es el semáforo que dice si se va a poder
respaldar. `poner_tasa()` manda **una sola trama** y relee, porque cada
escritura de rate que llega reconfigura la radio.

Y `primera-escritura.py` quedó con lo que le toca a una terminal: cómo se
cuenta. Un test nuevo fija que el criterio **no vuelva** a reimplementarse ahí:
si la biblioteca y el script opinaran distinto sobre si una escritura salió
bien, sería el peor lugar donde tener dos opiniones.

### Lo que falta para que la aplicación pueda escribir sin la terminal

El procedimiento completo —respaldo previo obligatorio, confirmación, escritura,
relectura y veredicto— sigue orquestado en el CLI. Mover **eso** es el próximo
paso, y es el que hay que hacer con más cuidado: ahí viven las barandas, no
solo la mecánica.

## El orquestador: la Etapa 3 entera, sin terminal

`sesion.aplicar()` hace la coreografía de los siete pasos y devuelve un
`Resultado`. Es lo que la aplicación va a llamar cuando quiera escribir algo.

```
0. la tasa tiene que dejar leer     -> aborta, o la baja si se lo piden
1. respaldo COMPLETO                -> sin él no se escribe
2. leer el bloque del comando       -> de ahí parte el codificador
3. codificar                        -> lo hace quien llama
4. confirmar mostrando la trama     -> sin confirmación no se escribe
5. escribir, y mirar el acuse
6. releer TODO y juzgar
7. (finally) devolver la tasa
```

**Hace la coreografía y ninguna de las decisiones de política.** Quien llama
decide si el comando se puede escribir, cómo se codifica el campo, cómo se
pregunta y qué se muestra: por eso `codificar` y `confirmar` son callbacks y no
`if`s adentro. La capa sabe **cómo** se hace, no **si** corresponde.

### Lo que fija el test, y por qué ese

`test_el_orquestador_aborta_donde_debe` prueba los seis casos **sin hardware**,
con un mouse falso que tiene estado y aplica lo que se le escribe:

1. respaldo incompleto → no escribe (es la Etapa 0: sin red, nada);
2. sin confirmar → no escribe;
3. a 8000 Hz sin pedir bajar → no escribe;
4. a 8000 Hz pidiendo bajar → escribe **y la tasa vuelve a 8000**;
5. el camino feliz → cambia lo pedido, nada más, y registra el acuse;
6. el mouse mudo justo después del respaldo → lo agarra el paso 2, y no
   escribe sin haber podido leer lo que iba a modificar.

Los tres primeros son barandas, no funcionalidad: lo que se prueba es que
**no** haga algo.

### Dos cosas que aparecieron escribiendo el test

**`sizeTotalData` es el largo del bloque, no el de los datos.** El mouse falso
lo devolvía mal —7 donde van 9 para el rate— y `build_write_frame()` lo
rechazó con su mensaje, que es exactamente para lo que está.

**El paso 0 gasta una lectura antes del respaldo**, así que el caso 6 tuvo que
contar las lecturas de `leer_estado()` y sumarle una. Es el tipo de detalle que
solo aparece ejercitando el camino entero.

### Lo que queda: el CLI sigue con su propia coreografía

`driver/scripts/primera-escritura.py` ya usa **todas las decisiones** de la biblioteca
—el veredicto, el camino de escritura, el manejo de la tasa— pero mantiene su
propio orden de pasos, con sus `print` entre uno y otro. O sea que hay dos
coreografías y una sola fuente para cada decisión.

Migrarlo a `aplicar()` es posible —los callbacks están para eso— pero es
reescribir doscientas líneas de la herramienta con la que se toca el hardware,
y hoy no hay nada roto que lo justifique. Queda anotado como deuda con su
motivo, y con la regla que la mantiene sana: **las decisiones viven en la
biblioteca; lo que el CLI puede tener propio es cómo se cuentan**.

## El estado con nombres propios

El punto 2 del plan de la aplicación: `driver/src/asbridge/modelo.py`. Devuelve **32
campos** con clave estable, nombre en castellano, valor, unidad, rango u
opciones, si se puede escribir y la advertencia medida cuando la hay.

```
tasa                 1000 Hz   W  opciones: 125…8000
dpi_nivel_1         1200 dpi   W  100..40000     [la página muestra 1000]
nivel_activo               1   W  opciones: 1..6
lod                     1 mm   W  opciones: 1, 2
ripple                  True   W                 [la página muestra True igual,
angle_snapping         False   W                  pero porque lee mal]
reposo               0.5 min   W  0.5..30
hibernacion           10 min   W  1..60
respuesta                  8   W  4..50
color                #00ff00   W                 [no enciende nada]
boton_izquierdo clic izquierdo    (no se remapea)
rueda                derecho   W  derecho / invertido
```

### Por qué no alcanzaba con lo que había

`decodificar()` devuelve los nombres del fabricante, y tres de ellos **enseñan
un modelo equivocado del dispositivo**: `SensitivityX` no es sensibilidad —es
el LOD y el ripple en un byte—, `closeTime` no es la hibernación —es el otro
temporizador— y `LightBrightness` no es el brillo —son cuatro bits del tiempo
de hibernación más un `8` de relleno—. Una interfaz construida sobre esos
nombres le miente al usuario con la etiqueta antes de mostrarle un valor.

Y faltaba lo que una interfaz necesita y no estaba en ningún lado: **el rango
de cada campo, sus opciones y si se puede escribir**.

### Dos decisiones que valen la pena

**El tiempo de respuesta se expone como lo ve una persona** (8), no como viaja
el byte (4). Exponer el byte crudo sería heredar la unidad del fabricante, el
mismo error que llamarle "brillo" a medio tiempo de hibernación. Queda anotado
que el CLI toma la mitad, y que **la unidad en milisegundos está INFERIDA** del
nombre del control, no medida.

**Las advertencias viajan con el campo**, no en la documentación: que la página
muestra otro dpi, que el color no enciende nada, que los cuatro interruptores
del sensor la página los lee cruzados, que el orden de rueda de la web deja el
scroll invertido. Son medidas y cada una cita su fecha. El test las verifica:
si alguien las borra, se pone rojo.

### Y un `except` que se tragó un bug

El lector de botones buscaba `b["slot"]` donde la clave es `b["indice"]`, y el
`except Exception: continue` que protege a los otros bloques **hizo desaparecer
los siete botones sin una línea de error**. Lo encontró el test, no la corrida.

Ahora ese `except` loguea qué comando no pudo leer y por qué. Un `except` que
no deja rastro es una trampa para el que venga — que en este caso fui yo,
media hora después.

## El atajo de teclado y los eventos de macro: la paridad, en código

El punto 3 del plan de la aplicación, que eran las dos cosas que le faltaban
para igualar al soft de Windows. Ninguna necesitaba hardware ni capturas
nuevas: la evidencia estaba en el repo y lo que faltaba era
el codificador.

### El atajo de teclado (función 17)

```bash
driver/scripts/primera-escritura.py --comando botones --boton costado-adelante \
    --funcion "atajo de teclado" --atajo ctrl+c
driver/scripts/primera-escritura.py --comando botones --listar-teclas
```

**La Etapa 2 salió contra dos fuentes a la vez.** `soft-todo.pcap` —la tanda
del soft nativo— tiene dos escrituras consecutivas de cmd 8 que
cambian **un solo slot** cada una:

```
16:16:22   ... 17 00 00 ...              pista siguiente
16:16:28   ... 11 08 07 ...              Win+D            <- el slot escrito 3
16:16:32   ... 11 08 07 ... 11 0a 16     Win+Shift+S      <- y el escrito 5
```

Así que sirven de par antes/después: aplicarle el codificador al bloque
anterior da el siguiente **byte a byte**, checksum interno incluido. Es el
mismo criterio con el que se aceptaron las escrituras de dpi, luz y botones.

Y la segunda fuente es el bundle: la tabla `sl` de `app.js` tiene **veinte**
entradas con el código 17, todas atajos conocidos de Windows, y las veinte
cierran con `ctrl=1, shift=2, alt=4, win=8` más la tabla de usages HID. Veinte
coincidencias independientes sobre cuatro bits:

```
FUN_COPY:[17,1,6]              ctrl+c
FUN_CLOSE_WINDOWS:[17,4,61]    alt+f4
FUN_BROWSER_FAVORITES:[17,3,18] ctrl+shift+o
FUN_SCREEN_CAPTURE:[17,10,22]  win+shift+s     (y además capturado)
```

La tabla de teclas también es del bundle —`_w()` declara 111 teclas con su
usage—, y el test la fija contra una transcripción literal: nuestra tabla cubre
**exactamente** esos usages, ni uno más. Inventar una tecla es inventar un
byte. Lo único nuestro son los nombres, porque los del bundle son los
`event.code` del navegador (`KeyA`, `ArrowUp`): se traducen como se tradujo el
LOD a milímetros, y los originales se siguen aceptando al escribir.

**Dos cosas se dejaron afuera a propósito.** Los cuatro modificadores derechos
del estándar HID (`0x10`..`0x80`) no aparecen en ninguna de las veinte
entradas, en ningún bloque capturado, ni en el diálogo del soft, que ofrece
cuatro: se rechazan con ese motivo escrito en el mensaje. Y el slot vacío
`11 00 00` —el `FUN_SHORTCUT` del bundle— es el mismo agujero que el macro con
id 0: el mouse lo acusa con `0xC1` y el botón queda muerto, así que `--atajo`
es obligatorio.

### Grabar un macro (cmd 9)

```bash
driver/scripts/primera-escritura.py --comando macro --macro-id 17 \
    --eventos "clic-izquierdo:abajo@10, clic-izquierdo:arriba@10"
```

**La Etapa 2 más barata que le quedaba al proyecto.** El bloque de 111 bytes
que el soft nativo le escribió al mouse está en el repo; darle al
codificador esos mismos diez eventos —los cinco botones, apretados y soltados,
10 ms cada uno— devuelve el bloque **idéntico**, checksum interno incluido, y
las dos tramas que van al dongle salen iguales a las cuatro escrituras de
`soft-macro-asignado.pcap`. Y al revés: devolverle los eventos que
`parametros_de_macro()` leyó reproduce el bloque tal cual, que es la escritura
idempotente de los eventos.

**El límite se valida contra el sitio, no contra el byte.** Entran 100 bytes de
eventos, o sea 50 cortos —25 si todos pasan de 127 ms, que ocupan cuatro—,
mientras el contador de pares entra hasta 255. Pasarse llenaría el bloque y se
comería el checksum, así que el codificador se niega y lo dice: qué hace el
mouse con un bloque más largo no se midió, y averiguarlo pisando su propio
checksum no es la forma.

### La decisión que hubo que tomar: un bit que los dos clientes escriben distinto

Para los eventos cortos, el soft manda el tiempo tal cual (`0a` = 10 ms) y los
constructores del bundle hacen `d|1`. Para los largos, `Qve` parte el tiempo y
**también** fuerza ese bit (`d|1` / `d|=129`). Nadie sabe qué significa.

El codificador usa **la estructura del bundle y el bit del soft**: cuatro bytes
con `[centenas, 3]` detrás, sin forzar el bit 0. La consecuencia es concreta y
a favor: pedir 350 ms escribe 350, mientras el codificador del bundle
escribiría 351. No es un hallazgo, es una elección entre dos clientes que no
coinciden, y se eligió el que tiene su escritura de macro capturada. Queda
anotada en `evidencia.md` dentro de la inferencia 15, y el CLI la avisa antes
de confirmar cuando algún evento cae en esa rama.

### Y una inferencia que ahora se puede cerrar apretando un botón

Cuál de los dos bits de dirección es *apretar* **no está medido**, y el
proyecto lo muestra como `dir0`/`dir1` desde que lo decodifica. Ahora que se
puede escribir, la medición cuesta un minuto: un macro de un solo evento `dir0`
sobre una tecla, asignado a un botón. Si al apretarlo la tecla queda
repitiendo, `dir0` es abajo. Es la clase de verificación que el proyecto
aprendió a buscar con el botón de ciclo de dpi: dejar que el
hardware conteste.

Mientras tanto `abajo`/`arriba` se aceptan como alias —grabar un macro pensando
en "dir0" es pensar en bytes— y el consejo de verificación dice que si la
secuencia sale al revés, eso es lo primero que hay que mirar.

### Los nombres de macro, que son nuestros

`driver/src/asbridge/nombres.py` y `driver/scripts/nombres-de-macro.py`. El bloque de un
macro no tiene campo de nombre —está decodificado entero— y el soft guarda los
suyos en `ms_13/macro.data`: los nombres son cosa del cliente. Se guardan en
`~/.config/asbridge/macros.json` y `primera-escritura.py --comando macro` los
muestra, para no escribirle al macro equivocado.

Dos barandas, no adornos: un archivo ilegible se lee como vacío **y se dice**
—sin nombres la aplicación anda igual—, y en ese caso `guardar()` se niega,
porque escribir encima borraría lo que hubiera adentro sin que nadie lo vea.

### Lo que además quedó mejor

Un macro de teclado se leía `usage 4, usage 224`: el decodificador solo
nombraba los cinco botones del mouse. Ahora usa la tabla completa y dice
`c dir0 20 ms, ctrl izquierdo dir1 10 ms`.

Y un slot con atajo se mostraba "atajo de teclado" a secas, igual que un slot
de macro mostraba "macro" sin decir cuál. Los dos llevan su parámetro adentro y
esconderlo es medio dato: `detalle_de_slot()` los muestra como `atajo de
teclado win+d` y `macro 17`, y un macro con id 0 —el botón muerto— como `macro
SIN ID (boton muerto)`.

### Qué queda

**La Etapa 3 de los dos, que la corre el usuario**, y las dos se verifican apretando
el botón: que llegue la combinación al sistema (`wev` o `xev` lo muestran), y
que salga la secuencia del macro en orden. Después de eso, el punto 4: la
interfaz. Grabar apretando teclas en vivo es parte de eso, no del protocolo:
el codificador ya está.

Las 62 pruebas de `driver/tests/salvaguardas.py` pasan —eran 58— y las cuatro nuevas
se probaron rompiéndolas a propósito —ocho mutaciones, ocho detectadas— porque
un test que pasa a la primera no prueba que mire.

## La Etapa 3 de los dos codificadores, y el día que se trabó el teclado

Faltaba apretar el botón. Se apretó, y salieron **seis** cosas medidas: las dos
Etapa 3 que estaban pendientes, dos hallazgos que nadie buscaba, y un
experimento del propio proyecto que resultó estar mal diseñado.

### Lo primero: la tasa, y una contradicción que se cerró leyendo archivos

`AGENTS.md` decía que el estado base era 1000 Hz y `SIGUIENTE-SESION.md` decía
que el mouse había quedado en 8000. Se resolvió **sin tocar el
mouse**, cruzando tres cosas: `dev/models/attackshark-x8pro/respaldos/rate-20260913T170606.json` (8000 Hz),
el respaldo completo quince segundos posterior (1000 Hz) y la entrada de
`bitacora.md` del cierre 4, que dice `quedo en 8000 Hz`. Esa cronología es la
firma exacta de una corrida con `--bajar-y-restaurar`. La lectura del hardware
lo confirmó: 8000 Hz.

**Y el usuario decidió que 8000 Hz es el estado base**, así que todas las corridas
del día llevaron `--bajar-y-restaurar`.

> Con una trampa anotada de paso: el respaldo `despues-de-escribir-*` de una
> corrida con `--bajar-y-restaurar` registra **1000 Hz**, porque se toma antes
> del `finally` que devuelve la tasa. El mouse queda en 8000 y el JSON dice
> otra cosa. Es justo el archivo que uno mira para saber cómo quedó el mouse.

### El experimento que el proyecto proponía no servía

`evidencia.md` decía, desde antes, cómo cerrar la dirección de los
eventos: *"un macro de un solo evento `dir0` sobre una tecla, asignado a un
botón. Si al apretarlo la tecla queda repitiendo, el 0 es abajo."*

Se corrió. **No pasó nada.** Se corrió con `dir1`. **Tampoco.**

El experimento apilaba sin saberlo una segunda variable que ninguna captura
había tocado: **una tecla de teclado dentro de un macro**. Los diez eventos de
la única captura de macro son los cinco botones del mouse (241..245); el usage
4 de la `a` salía solo del bundle. Con dos variables sin medir a la vez, "no
pasa nada" no distingue nada.

Es la lección 7 del proyecto llegando por la puerta de atrás: *antes de
escribir un codificador, mirar si el driver oficial movió ese campo alguna
vez*. Acá el campo se había movido —pero solo dentro del rango de botones, y
nadie había mirado **cuál** rango.

### Separadas de a una, las dos salen

| Macro escrito | Al apretar el botón |
| --- | --- |
| `a:dir0@10` | nada |
| `a:dir1@10` | nada |
| `clic-rueda:dir0@10, clic-rueda:dir1@10` | **pega la selección primaria, una vez por apretada** |
| `a:dir0@10, a:dir1@10` | **una `a`**, en el editor y en la terminal |
| `a:dir0@10, b:dir0@10` | **`abbbbbbbb…`** |

De ahí salen tres cosas:

**1. El codificador de eventos de macro funciona: Etapa 3 cumplida.** El
primer macro que el mouse ejecutó armado por nosotros es uno que ninguna
captura contiene. La verificación es externa: el pegado de selección primaria
lo hace X11 al recibir el clic de rueda, no nuestro decodificador. Y con la
tecla, el usuario comprobó que el portapapeles tenía otra cosa —o sea que la `a` era
una tecla y no un pegado—.

**2. `dir0` aprieta y `dir1` suelta.** Lo dice la última fila: salen las dos
letras, en el orden en que se escribieron, y quedan apretadas. La inferencia
16 resultó correcta y queda cerrada.

**3. Un macro de un solo evento no se reproduce.** El mouse lo **guarda** —la
relectura lo devuelve con su checksum bien— y al apretar el botón no hace
nada. Con dos eventos sale. **Por qué, no se sabe**: lo medido es el umbral
entre uno y dos, no la regla. Anotarlo como "el firmware itera de a pares"
sería inventar.

### El atajo de teclado: Etapa 3 cumplida

Con el slot `11 01 06` —`ctrl+c`, la primera combinación escrita que **no**
está en ninguna captura; las dos del bus son `11 08 07` y `11 0a 16`— el botón
del costado copia en un editor **y** manda SIGINT en una terminal. Las dos
cosas a la vez descartan que sea un pegado o que lo interprete una sola
aplicación.

### Y el día se pagó con el teclado trabado

El macro `a:dir0@10, b:dir0@10` dejó la `a` y la `b` apretadas. **El firmware
no suelta nada al terminar el macro.**

Lo caro no fue eso, fue el remedio. El proyecto tenía escrito, **desde esa
misma mañana** —commit `d0d3f5e`, junto con los codificadores—: *"si una `a`
queda pegada, se despega apretando la tecla en el teclado"*. **Es falso**, y
duró unas horas. Con la tecla trabada el sistema ya la tiene por
apretada, así que la pulsación real no genera un carácter nuevo: la `a` deja
de escribirse, y el propio remedio deja de estar disponible. Hubo que
**desacoplar el dongle** —y escribir sin la letra `a` para pedir ayuda, que es
el síntoma más claro que va a dar este bug—.

De ahí salieron las dos barandas del día, y las dos **avisan sin prohibir**:
los dos macros que las disparan son exactamente los experimentos que cerraron
la dirección, así que prohibirlos sería tirar el instrumento.

* `estructuras.eventos_sin_cerrar()` dice qué usages quedan apretados;
* `MACRO_EVENTOS_MIN_QUE_CORRE = 2` marca el macro que no se va a reproducir;
* y `primera-escritura.advertencias_de_eventos()` las imprime en el **paso 3,
  antes del prompt de confirmación**. Un aviso de "esto te va a trabar el
  teclado" que llega en el consejo del paso 6 no es un aviso, es una
  explicación. Y decirlo dos veces gastaría la alarma, que en este proyecto es
  la única red que hay.

El aviso dice el remedio real, no el que no funciona.

### Qué quedó en el mouse

El estado base, verificado **desde los respaldos** sin volver a leer el
hardware: macro 17 en modo 0 x1 con sus diez eventos, y el costado-adelante en
`adelante`. Los macros viven en `estado["macros"]`, no en `estado["comandos"]`.

Las 63 pruebas de `driver/tests/salvaguardas.py` pasan —eran 62—. El test viejo del
consejo de verificación exigía que dijera `INFERIDO` sobre la dirección: ahora
exige lo contrario, que diga `MEDIDO` y cuál es. Si alguien devuelve el texto
viejo, se pone rojo: sería degradar un dato medido.

### La lección, que es nueva

**Un experimento anotado en los docs es una hipótesis, no un procedimiento.**
El de la dirección estuvo tres días escrito como "se cierra barato" y no
cerraba nada, porque su autor —nosotros— no había notado que usaba una tecla
donde todas las capturas usaban botones. Cuando un experimento diseñado no
contesta, la primera sospecha no es el hardware: es que mide dos cosas.

## La tasa deja de depender de que uno se acuerde

Propuesta del usuario, sobre la sugerencia que había quedado anotada: *"podemos
poner un aviso o mensaje que si la tasa es mayor a 1 kHz el software la baja
para aplicar los cambios. Si el usuario es informado entonces no se hace nada
sin permiso"*.

Es la salida correcta, y resuelve la tensión que tenía anotada la sugerencia
—comodidad contra "no tocar lo que no se pidió"—: el consentimiento informado
no afloja la baranda, la mueve de un flag que hay que recordar a una pregunta
que se contesta.

**Con un detalle de orden sin el cual no se cumple.** El paso 0 corre **antes**
del prompt del paso 4. Si la tasa se bajara primero y recién después se
preguntara "¿escribir?", un "no" dejaría al mouse tocado por una corrida que el
usuario abortó. Que la tasa vuelva en el `finally` no cambia el punto: se le
movió un campo a alguien que dijo que no. Así que la pregunta va **antes de
bajar**.

Queda así:

```
[0/6] el mouse esta a 8000 Hz, y arriba de 1000 Hz el respaldo de los
      siete comandos no sale
      (MEDIDO a 2000 y a 8000), y el paso 1 lo exige. Para seguir hay que
      bajar la tasa a 1000 Hz y devolverte los 8000 al terminar -va en el
      `finally`, asi que vuelve aunque la escritura falle-. No afloja
      ninguna baranda: el respaldo completo se sigue tomando, solo que a
      1000 Hz.

[0/6] bajar a 1000 Hz y devolver 8000 al terminar? [bajar/no]:
```

`--bajar-y-restaurar` deja de ser el único camino y pasa a ser **el "sí" dado
de antemano**: sirve para no contestar dos veces y para una corrida sin
terminal, donde ahora se exige explícitamente.

### Y la política vive donde corresponde

`sesion.aplicar(bajar_la_tasa=...)` acepta un `bool` **o una corrutina** que
recibe los Hz y contesta. Es la misma forma que ya tenía `confirmar`, y por el
mismo motivo: la decisión de que **haga falta** bajar es de la biblioteca —sale
de `RATE_MAXIMO_PARA_LEER`, que está medido— y la de **preguntar** es de quien
llama. La regla sigue valiendo: las decisiones viven en la
biblioteca; lo propio del CLI es cómo se cuentan.

`test_el_orquestador_aborta_donde_debe` gana un caso: que el callback se
consulte con los Hz reales, y que un "no" **no deje ninguna escritura hecha**.
Siguen siendo 63 pruebas —el caso entra en un test que ya existía—.

## La deuda técnica, cerrada, y el bug que la estaba escondiendo

`primera-escritura.py` usaba todas las **decisiones** de la biblioteca pero
mantenía su propia coreografía de la Etapa 3. La deuda estaba anotada desde
antes, con el argumento de que no había nada roto que justificara tocar
doscientas líneas de la herramienta con la que se escribe al hardware.

Ese argumento se venció ese mismo día: el permiso de tasa se escribió **dos
veces**, una de cada lado.

### Primero la red, después la cirugía

La razón por la que migrarla era caro no era el tamaño: era que **no había
forma de probarla sin un mouse enfrente**. `main()` abría el nodo adentro.

Ahora acepta `device` y `nodo`, así que la Etapa 3 entera —paso 0 incluido—
corre contra `_MouseFalso`. Eso da `test_la_herramienta_de_punta_a_punta`, con
cinco casos: una escritura que anda, que no haya vuelto ningún prompt, el paso
0 completo a 8000 Hz, un respaldo incompleto que **no** escribe, y un valor
inválido rechazado sin tocar el mouse.

Se probó rompiéndolo a propósito: **cinco mutaciones, cinco detectadas**. Dos
de ellas, al principio, se detectaban *reventando* en vez de fallando —lo que
tumbaba la tanda entera y tapaba cuál había sido—, así que `correr()` captura
la excepción y la reporta como un fallo más.

Y por encima, una caracterización de **quince** corridas —todos los comandos y
sus variantes— guardando código de salida, escrituras al mouse y salida de
terminal, para comparar antes y después.

### El bug que la migración destapó

`sesion.aplicar()` infería si una escritura era idempotente comparando
`datos == leido`. **Para cmd 8 y cmd 9 eso da lo contrario de la verdad**: ahí
lo idempotente sale distinto de lo leído a propósito —los slots retraducidos,
el checksum reinvertido—, que es la baranda de "lo leído no se devuelve tal
cual" que el proyecto viene documentando.

O sea que `aplicar()` le habría dado `no-cambio-nada` —veredicto malo— a una
escritura idempotente de botones o de macro que salió perfecta:

```
idempotente=True   ok=True   motivo='sin-diferencias'     <- lo correcto
idempotente=False  ok=False  motivo='no-cambio-nada'
```

El CLI no caía porque calcula la idempotencia de **lo que el usuario pidió**,
no comparando bytes. Nadie lo había visto porque los seis casos de
`test_el_orquestador_aborta_donde_debe` no incluían una escritura idempotente
de esos dos comandos.

Se arregló, y sin dejar el default peligroso puesto: `aplicar()` ahora acepta
`idempotente` explícito y **se niega a adivinar** en los dos comandos donde
adivinar miente. No decirlo ahí es un `ValueError`, no un default silencioso.
Acepta además un callable, porque quien llama suele saberlo recién después de
codificar.

**Esto es lo que valía la deuda.** No era mover código: era que la biblioteca
—la que va a usar la aplicación— tenía un veredicto equivocado en dos de los
cinco comandos escribibles, y la única forma de encontrarlo era intentar que
reemplazara al CLI.

### Cómo quedó

`aplicar()` corre la Etapa 3 entera y el CLI conserva lo suyo: qué bytes pide
el usuario (`codificar`) y cómo se cuenta lo que pasó. Para que la biblioteca
no tenga que saber de terminales, manda avisos con clave estable
—`AVISO_RESPALDO`, `AVISO_RELECTURA`, `AVISO_ACUSE`, `AVISO_SIN_ACUSE`, y los
dos de la tasa como `clave|texto`— y el CLI los numera y los envuelve.

El resultado, contra la caracterización: **15 de 15 con las mismas escrituras
al mouse y el mismo código de salida**. La única salida que cambió es la del
paso 0, y cambió a mejor: ahora dice que la tasa vuelve al terminar, que era lo
que faltaba para que "bajo a 1000" no se leyera como que el mouse queda ahí.

Se fueron además el prompt de confirmación —el consentimiento es el comando, y
en la aplicación va a ser el click—, el flag `--bajar-y-restaurar` que ya no
tenía nada que dar por respondido, y `_leer_todo()`, que quedó sin usar.

### La lección

**Una deuda técnica puede estar escondiendo un bug, y el bug puede estar del
otro lado.** Acá lo que estaba mal no era el código duplicado del CLI: era la
biblioteca a la que había que migrarlo. Mientras nadie intentara reemplazar
uno por el otro, los dos parecían andar.

## Las auditorías, revisadas antes de la interfaz

Segunda pasada de las dos auditorías, esta vez sobre el HEAD `1628e1f`. Las dos
coinciden en el fondo: **no hay bloqueantes y el backend está listo**. Lo que
dejaron son tres arreglos y un plan.

### Los tres arreglos

**El `hardware.md` decía más de lo que estaba medido** (agente B, G-8k). El
párrafo sobre los 8 kHz afirmaba que a esa tasa "el mouse no se puede ni leer
ni configurar desde Linux". Era cierto, cuando se escribió, y
dejó de serlo el 13 sin que nadie volviera a tocarlo. Hoy la distinción está
medida y es de tres niveles: las lecturas **cortas** funcionan, las **largas**
no, y las **escrituras** también funcionan —el driver oficial bajó el rate con
el mouse a 7825 Hz—. Es el error que este proyecto más viene evitando, cometido
por omisión: una afirmación que se quedó vieja.

**El error del modo `full` mandaba a pedir lo imposible** (agente B, N-01). El
mensaje de `backend.py` ofrece `WRITABLE - SIN_CAMINO_EN_EL_BACKEND` —rate,
dpi, luz y botones—, que es correcto para quien usa `HidrawBackend` desde
código propio. Pero el CLI acepta solo `cli.ESCRIBIBLES` (rate y dpi), así que
un usuario que leyera ese error y pidiera `luz` se comía un "invalid choice" de
argparse dos líneas después.

Es la **segunda vez** que el agente B lo marca: la primera se arregló a medias —se
restó `macro` y no el techo del CLI— y por eso volvió. Ahora el CLI valida
antes, nombra su propio techo y dice por qué los demás no salen por el puente.
El mensaje del backend no se tocó: para su público es correcto.

**Y G-06 ya estaba arreglado** cuando se revisó: el texto residual que el agente A
cita en `SIGUIENTE-SESION.md` salió del repo el mismo día, y la pasada quedó
entre medio.

### Una trampa de trazabilidad que conviene anotar

**Los IDs del agente B se renumeran en cada pasada.** El archivo se sobrescribe
entero, y `N-03` era "el techo del CLI no es el de la API" el 12 y es "el
nibble bajo del byte de rate" el 14. `respuesta-auditorias.md` ahora fecha cada
cita por eso. Los `H-xx` y los `G-0x` del agente A sí son estables.

### Y el plan de la interfaz, que es lo que las dos vinieron a dejar

El agente A lo dice como recomendaciones y es lo mejor del informe: hay **cuatro
cosas que la interfaz tendría que reimplementar** si no se hacen antes en la
biblioteca. Las cuatro se verificaron contra el código:

* **el despachador de mutaciones** (G-01): traducir `(clave, valor)` a "qué
  comando y qué codificador" vive hoy adentro de `codificar()` en
  `primera-escritura.py`. Es la misma duplicación que se cerró hoy entre el CLI
  y la biblioteca, un nivel más arriba — y esta vez conviene hacerlo **antes**
  de que existan dos copias;
* **el modelo de macros** (G-02): `campos_de()` no mira `estado["macros"]`;
* **la batería** (G-03): vive en `backend.py`, no en `sesion`, y no se pide
  —llega sola en el Report ID 3 cada 2-4 s—;
* **el `PermissionError` del nodo** (G-05): en una terminal se lee, en una
  ventana hay que atraparlo.

Están en `SIGUIENTE-SESION.md` como el punto de partida, con lo que verifiqué
de cada uno.

### La lección

**Una auditoría que repite un hallazgo está diciendo que el arreglo anterior
quedó a medias.** N-01 se dio por cerrado el 12 restando `macro`, que era la
mitad visible del problema; la otra mitad —que el CLI ofrece menos que el
backend— estaba escrita en `metodo.md` desde antes, y aun así el mensaje seguía
nombrando los cuatro. La segunda marca no es ruido: es información.

## Lo que le faltaba a la biblioteca para la interfaz

Las cuatro cosas que la auditoría marcó como "lo que la interfaz tendría que
reimplementar". Ninguna era un defecto; todas eran trabajo que alguien iba a
hacer dos veces si no se hacía una.

### El despachador de mutaciones (G-01), y por qué el test importa más que él

`modelo.py` dice qué campos hay y cuáles se escriben. Lo que no había era cómo
se pasa de `("lod", 2)` a "qué comando tocar y con qué codificador": eso vivía
adentro de `codificar()` en `primera-escritura.py`, atado a los argumentos de
una línea de comandos.

Ahora es `sesion.preparar_mutacion(clave, valor)`, con las claves de
`modelo.campos_de()` —las mismas que la interfaz ya usa para mostrar—. Y hace
las traducciones que si no cada cliente reinventa: el **LOD entra en
milímetros** y el codificador quiere el código crudo; el color se escribe
`"#00ff00"`; un botón es `"adelante"`, o `("macro", 17)` y
`("atajo de teclado", "ctrl+c")` para las dos funciones que llevan parámetro.

Los campos que **no** se escriben tiran `CampoNoEscribible` con el motivo
medido —el clic izquierdo no se remapea porque un mouse sin clic izquierdo no
se arregla desde ninguna interfaz; los ocho colores de indicador no tienen
Etapa 2 porque ningún cliente oficial los movió nunca— y no un `KeyError`.

**Pero lo que hace que esto no sea una segunda copia es el test.**
`test_el_despachador_y_el_cli_dan_lo_mismo` corre los dos caminos contra el
mismo mouse falso y compara el bloque que sale, en **dieciséis casos** que
cubren los cinco comandos escribibles. Salió 16/16 a la primera. Si alguien
toca uno y no el otro, se pone rojo: es la misma idea que la caracterización de
quince corridas que verificó la migración del CLI, pero permanente.

### Y apareció el arreglo bueno de la idempotencia

Escribiendo el despachador quedó claro que el `ValueError` de esa mañana
—negarse a adivinar si una escritura era idempotente en cmd 8 y cmd 9— era un
parche: la respuesta correcta se podía calcular.

`sesion.referencia_idempotente(cmd, leido)` devuelve lo que un codificador da
**cuando no cambia nada**: `retraducir_botones()` para cmd 8, `escribir_macro()`
para cmd 9, el bloque leído para el resto. Comparar contra eso acierta en los
cinco comandos, así que `aplicar()` volvió a inferirlo solo y quien llama puede
decirlo igual si lo sabe.

> **Primero negarse a adivinar, después adivinar bien.** El parche de la mañana
> no fue tiempo perdido: convirtió un error silencioso en uno ruidoso, y eso
> fue lo que dejó ver dónde estaba la respuesta.

### Un fixture que mentía

El test nuevo destapó que `_MouseFalso` **guardaba los bytes del bus tal cual**.
Un mouse real no hace eso: en cmd 8 y cmd 9 el formato de escritura no es el de
lectura, así que al releer devuelve el bloque transformado de vuelta. El falso
mostraba un cambio donde no lo había.

Las dos inversas se verificaron antes de codificarlas: `retraducir_botones` es
de **orden 3** —aplicarla dos veces más deshace— y el checksum interno del
macro se da vuelta solo. Y el bloque de macro del fixture eran 108 ceros, o sea
un macro inválido que `escribir_macro()` *normalizaba* en vez de devolver igual;
ahora es un macro de verdad, armado con el codificador para que no se
desactualice.

### Los macros, modelados (G-02)

`modelo.macros_de(estado, nombres)` devuelve `Macro` con id, nombre local, modo,
**qué hace ese modo**, repeticiones, eventos, el texto en el formato que
`eventos_desde_texto()` acepta —así lo que se muestra se puede reescribir sin
traducir— y las advertencias medidas: que un macro de un evento no se
reproduce, y que dejar algo sin cerrar traba la tecla y obliga a desacoplar el
dongle. Un macro que el mouse no contestó se devuelve igual, dicho: esconderlo
haría creer que no existe.

### Lo que el mouse avisa solo (G-03), sin inventarle nombres

La batería no se pide: llega en reportes espontáneos del Report ID 3 cada 2-4 s,
y hasta hoy solo los miraba `backend.py`, o sea el puente. Ahora
`sesion.novedad_de()` los decodifica y `sesion.escuchar_novedades()` los
reenvía.

**Con una decisión epistémica que conviene respetar: `Novedad` no tiene un
campo `cargando`.** El byte de estado que acompaña al nivel solo se vio
valiendo 1, y el `2` ("desconocido") sale del bundle; qué significa cada valor
**no está medido**. Se expone crudo hasta que alguien mida el mouse enchufado y
desenchufado, y el test se pone rojo si aparece un `cargando`.

De paso, el otro tipo de novedad resultó más útil de lo que parecía: cuando el
usuario cicla el dpi con el botón del mouse, llega un aviso. Una interfaz que
muestre el nivel activo tiene que escucharlo o va a quedar mostrando un valor
viejo — que es, dicho sea de paso, la misma verificación independiente que
cerró `Current_Dpi_level_flag`.

### El nodo sin permiso (G-05)

El mensaje ya era bueno. Lo que faltaba era poder distinguirlo **sin parsear el
texto**: `hidraw.FaltaLaReglaDeUdev` sigue siendo un `PermissionError` —nada de
lo que ya lo capturaba deja de andar— y trae `.comando` y `.path` como datos,
para que una ventana ofrezca el arreglo como un botón.

### Estado

68 salvaguardas en verde, y el CLI sigue mandando **exactamente los mismos
bytes** en las quince corridas de la caracterización. Lo único abierto de la
lista de la auditoría es G-04, que no es código: es cómo convive `asyncio` con
el reactor gráfico, y se decide junto con el toolkit.

## El perfil declarativo, y de quién son los 47 modelos

### La pregunta, contestada con el bundle

¿Los modelos de `store.mouseNum` son todos de Attack Shark? **No.** Las rutas
del bundle enrutan a **tres marcas** —`/ATTACKSHARK/` (84 rutas),
`/MAMBASNAKE/` (14) e `/INX/` (5)—: es software OEM compartido, que es
exactamente lo que hacía sospechar que los protocolos se parecieran entre
marcas.

Y de paso, dos conteos que no coincidían. Son **47**: lo dice el bundle y lo
dice `protocol.MOUSE_NUM`. `protocolo.md` decía 43 y yo había dicho 46 — el
documento quedó corregido con la fecha del recuento.

De los 47, **solo 14 tienen ruta con marca explícita**; los otros 33 caen en
páginas genéricas y no se les puede atribuir marca con lo que hay. Anotarlos
como "Attack Shark" porque el repo se llama así sería justo el error que este
proyecto viene evitando.

### El perfil, y la distinción que importa

`driver/src/asbridge/dispositivos.py` separa dos cosas que es fácil mezclar:

* el **catálogo** dice qué modelos existen. Sale del bundle, o sea está
  **LEÍDO**: 47 entradas, una sola confirmada contra hardware;
* el **perfil** dice cómo se le habla a uno. Hay **uno**, el del X8 Pro, y está
  MEDIDO.

**Saber que un modelo existe no es saber hablarle.** Un `perfil_de()` de
cualquier otro no devuelve algo parecido: levanta `ModeloDesconocido` diciendo
qué modelo es, de qué marca si se sabe, y que para agregarlo hace falta la
captura de su driver oficial —no adivinar offsets parecidos—.

El perfil no cambia cómo se habla con el mouse: **junta en un lugar lo que
estaba disperso** entre `estructuras.py`, `protocol.py` e `hidraw.py` —los
tamaños de bloque, los dieciocho slots, la permutación de los slots 4, 5 y 6,
los ocho niveles de dpi, los rangos—, para que se lea de una sentada qué habría
que medir para agregar un modelo.

Y `test_el_perfil_no_miente` compara **cada campo** con la constante de la que
salió. Un perfil que dice 56 donde el código usa otra cosa es peor que no
tenerlo: manda a buscar al lugar equivocado.

> El test tiene además una línea que se pone roja si `PERFILES` crece: si
> alguien agrega un modelo, tiene que sacarla a mano. Copiar el perfil del X8
> Pro y cambiarle el nombre es exactamente lo que no puede pasar en silencio.

### Y una baranda que no existía

Escribiendo esto quedó a la vista algo que nadie había notado: **el código le
hablaba a cualquier mouse que contestara**, asumiendo que era un X8 Pro. Todo
lo medido es de ese modelo; escribirle a otro con estos offsets es mandarle
bytes que nadie verificó.

El `device_id` no se puede pedir —llega solo, en el Report ID 3—, así que la
primera oportunidad de notarlo es la primera novedad. `Hardware` ahora la mira:
si el modelo no es uno que tenemos medido, emite `modelo_detectado` con lo que
sea que dijo ser y un `problema` que lo explica. Dos pruebas nuevas en
`driver/tests/interfaz.py`, una por cada rama.

No bloquea: avisa. Bloquear obligaría a esperar una novedad que puede tardar
4 s, y con el mouse dormido no llega nunca.

## El byte de estado de batería: 3 es cargando, y por cable a la PC el mouse se calla

La corrida más barata que quedaba abierta, y salió con dos hallazgos: el que se
buscaba y uno que no.

### La corrida

`driver/scripts/sondear.py --escuchar`, que abre el nodo en solo lectura y ya imprime
el byte: no hubo que escribir código ni mandarle nada al mouse. Condición
física: el mouse en movimiento continuo —quieto se pierde la mitad de los
latidos— y sin tocar botones.

**Primera corrida, 120 s.** Base sin cable, después el cable a un puerto USB de
la PC, después afuera, y al final un cargador externo:

```
[  0.47s] 73% (estado 1)     base, sin cable
[ 44.51s] 72% (estado 1)     último latido antes del hueco
          ‹ 32 s de silencio ›   el cable, enchufado a la PC
[ 76.92s] 75% (estado 1)     cable afuera; cargó 3 puntos en el hueco
[108.95s] 72% (estado 1)
[111.09s] 72% (estado 3)     el cargador externo
[118.96s] 72% (estado 3)
```

**Segunda corrida, 60 s**, arrancando con el cargador puesto, para medir la
vuelta: sin ella el `3` quedaba atado a un solo evento.

```
[  0.84s] 71% (estado 3)     cargador puesto
[ 26.69s] 75% (estado 1)     lo saca:      3 -> 1
[ 40.69s] 75% (estado 1)
[ 42.70s] 75% (estado 3)     lo vuelve a poner: 1 -> 3
[ 58.72s] 75% (estado 3)
```

### Lo que quedó MEDIDO

**`estado 3` es cargando, `estado 1` es a batería.** Cuatro transiciones entre
las dos corridas, cada una siguiendo al cargador, con el enlace vivo de los dos
lados —el nivel se seguía leyendo— y **el LED morado de carga confirmándolo por
fuera del protocolo**, que es la clase de verificación que este proyecto
prefiere: no depende de nuestro código ni del del fabricante.

El `2` del bundle (`BATTERY_UNKNOWN`) **sigue sin aparecer nunca** en el
hardware, y el `0` tampoco.

### El hallazgo que no se buscaba

**Con el mouse enchufado por cable a la PC no llega ni un latido por el
dongle**: 32 s sin un solo Report ID 3, entre dos tramos que latían cada
2,00 s. Y sí estuvo cargando en ese hueco —volvió con 75% contra los 72% de
antes—, así que no es que el mouse se apagara: dejó de hablar por radio.

Por eso el primer tramo de la prueba no mostró nada, y por eso el cargador
externo era la forma de medir la carga: alimenta sin llevarse el canal.

Esto convierte en MEDIDO el consejo que `hardware.md` daba por prudencia
—trabajar siempre con el cable desenchufado— y le agrega una consecuencia para
la interfaz: **el dongle sigue en el bus y el puente no ve ninguna
desconexión**, simplemente no llegan novedades. Una UI que muestre batería
tiene que distinguir "no llegan novedades" de "la batería es la de hace un
rato". Que el mouse *conmute a modo cable* es la explicación razonable, pero lo
medido es el silencio: la enumeración de `1d57:2126` no se miró en esta corrida.

### Dos cosas menores, anotadas para no volver a medirlas

- **El latido cayó cada 2,00 s clavados**, las dos corridas enteras. No
  corrige nada: `medir-hibernacion.py` ya había medido las dos cadencias
  —2,00 s despierto, 4,00 s tras ~32,8 s de quietud— y esto es una
  confirmación independiente de la primera, con el mouse en movimiento. Sí se
  vieron dos huecos de ~4 s justo al manipular el cargador; si fue un latido
  perdido por radio o la otra cadencia, esta corrida no lo distingue.
- **El porcentaje tiene varios puntos de ruido.** 73, 72, 75, 74, 72, 71, 75 en
  cuatro minutos, y +3 puntos en 32 s de carga, que es demasiado rápido para
  ser la carga real. Por qué, no se sabe; lo que importa es no mostrar esos
  saltos como si fueran la batería moviéndose.

### Lo que se cambió

`protocol.py` tiene ahora `BATTERY_DISCHARGING = 1` y `BATTERY_CHARGING = 3`
con su procedencia al lado, y el `2` marcado como "del bundle, jamás
observado". `sesion.Novedad` gana un campo `cargando`, que da `True` con 3,
`False` con 1 y **`None` con cualquier otro valor**: decir `False` ahí sería
afirmar algo que nadie vio. El byte crudo se sigue exponiendo.

Y **la baranda de `driver/tests/salvaguardas.py` se dio vuelta a propósito**:
antes se ponía roja si `Novedad` tenía un campo `cargando`, porque habría sido
inventado. Ahora exige lo contrario —que 3 y 1 se lean— y sigue cuidando el
límite: un valor sin medir tiene que dar `None`.

### Lo que sigue abierto

Qué manda el mouse **con la batería llena**: si hay un cuarto valor para
"cargado", no se vio. Es una corrida de horas, no de minutos.

## Con el mouse rápido no se podía configurar nada, y la ventana se colgaba

Lo reportó el usuario: **con el polling rate en 2k, 4k u 8k no se puede modificar
ningún parámetro desde la aplicación, el programa se cuelga, y el mouse queda
inutilizable.** Y propuso la salida: que no lea todo el tiempo todos los datos,
o que baje una vez, lea, y cachee.

**No es un problema, son tres**, y las tres se reprodujeron sin tocar el
hardware —contra un mouse falso que respeta lo medido: arriba de 1000 Hz las
lecturas cortas llegan y las largas no—.

### Las tres fallas

| | Qué pasaba | De dónde salía |
| --- | --- | --- |
| **no se podía escribir** | `poner_tasa()` mandaba **una** trama y se rendía. El paso 0 de la Etapa 3 baja la tasa para poder respaldar, así que una sola pérdida de radio salía como `no-pude-bajar-la-tasa` y el campo no se escribía | el enlace pierde pedidos de verdad (95% con el mouse en movimiento, 50% quieto) y **el dongle acusa `0xC1` sin que el mouse aplique** (MEDIDO, dos veces seguidas a 2000 Hz). `driver/scripts/cambiar-rate.py` ya insistía releyendo, que es el camino MEDIDO; la biblioteca no |
| **el mouse quedaba inutilizable** | **dos escrituras de rate por campo**: el paso 0 baja y el `finally` devuelve. Tres cambios eran seis reconfiguraciones de la radio | está MEDIDO adónde lleva eso: la página oficial mandó seis tramas de rate en tres segundos —por clics encolados— y **el mouse dejó de mover el puntero** hasta que se lo sacó del modo dongle. La ventana tenía un camino directo a ese estado |
| **se colgaba** | **dos lecturas completas por campo** —el respaldo del paso 1 y la relectura del paso 6—, y leer el mouse entero tarda minutos. La pantalla se bloquea a propósito mientras escribe | la Etapa 3 está pensada para una corrida de terminal que escribe un campo y se va. Para una ventana donde alguien mueve un deslizador, no |

La reproducción, contra el mouse falso a 8000 Hz:

```
todo sale bien:                 motivo=cambio-lo-pedido     rate_escrito=2  lecturas=20
se pierde 1 escritura de rate:  motivo=no-pude-bajar-la-tasa rate_escrito=1  lecturas=3
tres cambios seguidos:                                       rate_escrito=6  lecturas=60
```

### El perfil completo sirve de testigo, y ahora está medido para cuatro comandos

Para releer barato hacía falta saber si algo más se había movido sin releer
todo. `evidencia.md` decía que el perfil completo embebe a los demás bloques,
pero lo tenía MEDIDO para **dos** comandos: rate y botones.

Se verificó sobre los **139 respaldos versionados**, que son mediciones contra
el hardware ya hechas y guardadas. Pares consecutivos con alguna diferencia:

```
pares con alguna diferencia ..................... 95
cambió solo dpi     -> el perfil acompañó ....... 28 de 28
cambió solo luz     -> el perfil acompañó ....... 19 de 19
cambió solo rate    -> el perfil acompañó .........2 de 2
cambió solo botones -> el perfil acompañó ....... 17 de 17
el perfil se movió solo (falso positivo) ......... 0
cambió algo y el perfil no acompañó .............. 0
```

**Lo que esto NO cubre**: los macros. Viven en `estado["macros"]`, se leen con
su id, y ningún par los movió sin mover además otra cosa: no hay medición que
diga que el perfil los refleje. El macro que se escribe sí se relee; los otros
no se miran, y eso se dice.

La verificación **es una prueba** (`test_el_perfil_acompaña_a_todo_cambio`) y
corre en cada tanda: si alguien agrega un respaldo que la contradiga, se pone
roja y la relectura acotada deja de estar justificada. No es un número copiado
a un comentario.

### Lo que se cambió

- **`sesion.poner_tasa()` insiste**, releyendo entre intento e intento y
  cortando apenas entra —lo mismo que `cambiar-rate.py`—, y **no manda nada si
  la tasa ya está puesta**. Con el enlace sano el mouse recibe una sola trama;
  el bucle existe porque el enlace pierde, no para repetir lo aplicado.
- **`sesion.Configuracion`**: la tasa se baja **una vez por ráfaga** y el estado
  se lee **una vez**. Cada escritura arranca con el respaldo que ya está.
- **`sesion.aplicar()` acepta `respaldo=`** —un estado ya leído, que se usa en
  lugar de tomar uno— y **`relectura=`**, que elige el alcance del paso 6.
- **La relectura acotada** mira el bloque escrito y el perfil. `Veredicto` gana
  `no_releidos` y la explicación **nombra lo que no se miró**, salvo cuando no
  se movió nada: ahí el perfil alcanza como testigo y avisar sería gastar una
  alarma.
- **La tasa deja de escribirse por la Etapa 3.** Es el bug que
  `SIGUIENTE-SESION.md` tenía anotado como abierto: el `finally` del paso 0
  restauraba justo lo que se acababa de pedir y el veredicto decía que había
  salido bien. Ahora va por el camino de un solo comando, como
  `cambiar-rate.py`, **con el respaldo completo igual** —dentro de la sesión el
  mouse ya está a 1000 Hz, así que el respaldo sí se puede tomar, que es lo
  único que a la herramienta de terminal le faltaba—.
- **La ventana lee bajando la tasa.** Hasta hoy, "leer el mouse" a 8000 Hz
  salía siempre incompleto y lo único que la ventana podía hacer era decirlo.
- **Y lo dice**: `CartelDeTasaPrestada` muestra que el mouse está a 1000 Hz
  prestado, de cuánto, y ofrece devolverlo. Vuelve solo al cerrar la ventana o
  tras 90 s sin cambios.

### Lo que NO se aflojó

El respaldo completo sigue siendo obligatorio antes de escribir —un respaldo
incompleto no se cachea, porque sería peor que no tener ninguno—; la relectura
y el veredicto siguen ahí; y la tasa vuelve.

Lo que **sí** cambia y hay que saberlo: el respaldo que hace de red puede ser
de hace minutos y no de hace segundos. Los dos caminos por los que el mouse se
mueve sin que lo movamos nosotros están cubiertos: el firmware, que escribe
`Current_Dpi_level_flag` al ciclar el dpi con el botón y lo avisa por el Report
ID 3 (`Configuracion.invalidar()`), y otro cliente oficial, que no puede correr
al mismo tiempo porque el nodo es exclusivo.

### Lo que falta, y es lo único que falta

**Nada de esto se probó contra el hardware.** Todo lo de arriba corre contra
mouses falsos y contra los respaldos versionados. Las tres corridas que lo
cierran están en `SIGUIENTE-SESION.md`, y las corre el usuario.

### De yapa, un bug que iba a reventar la ventana

`paneles/parametros.py` usaba `QHBoxLayout` sin importarlo, en el camino de dos
columnas. Con la ventana a 950 px o más, `resizeEvent` tiraba `NameError` por
el medio de un slot de Qt. Estaba en el árbol de trabajo, sin commitear.

## Cómo comprobar si el firmware acepta cambiar los colores de DPI

Quedó registrada la posibilidad de comprobar empíricamente si el firmware del
mouse permite modificar los colores del LED de cada nivel de DPI, y cómo se
debería encarar una prueba así.

### Fuzzing ciego vs. Mutación quirúrgica controlada

El "fuzzing" estricto —mandar bytes aleatorios o tramas con variaciones no
estructuradas al canal de configuración— **no es aconsejable ni necesario**:
1. **Riesgo físico innecesario**: una trama con longitud o campos arbitrarios
   podría escribir fuera del búfer de configuración en la flash/EEPROM del
   microcontrolador y corromper el firmware (bricking).
2. **La estructura ya se conoce byte a byte**: no hay nada que "adivinar". El
   bloque de cmd 4 mide 54 bytes de payload, los offsets de los 8 campos RGB
   (`Dpi_level_1..8_indication_flag`, 3 bytes cada uno) están identificados, y la
   fórmula del checksum interno (`co()`, suma de `datos[1:fin]`) está verificada
   en 61 tramas sin excepción.

Por ende, en vez de fuzzing ciego, lo que corresponde metodológicamente es una
**mutación quirúrgica controlada**:

1. **Lectura de base**: Tomar el bloque real de cmd 4 leído del mouse (donde el
   nivel 1 viene con `ff 00 00`, rojo).
2. **Mutación puntual**: Cambiar únicamente esos 3 bytes a un color claramente
   diferenciable (por ejemplo, `#800080` violeta o `#0000ff` azul).
3. **Recálculo**: Recalcular el checksum interno y el checksum de trama con la
   aritmética ya probada.
4. **Escritura y triple comprobación**:
   - **Acuse del dongle**: verificar si devuelve `0xC1`.
   - **Relectura del bloque**: comprobar si el comando 4 devuelve los bytes
     modificados o si el mouse los descartó y restauró el valor por defecto.
   - **Verificación en el hardware**: conmutar al nivel 1 con el botón físico o
     escribiendo `Current_Dpi_level_flag`. Si el LED físico parpadea en el nuevo
     color (violeta/azul), **queda demostrado que el firmware acepta colores
     personalizados**. Si parpadea en rojo a pesar del acuse, el firmware tiene
     la paleta cableada en su ROM interna y los bytes del bloque son solo un
     reflejo estático.

### La alternativa con Etapa 2: parchear el soft nativo en la VM

La otra opción —que preservaría la regla estricta del proyecto de no enviar
tramas que un cliente oficial no haya enviado antes— es desensamblar
`CMS_13_Page` en el instalador de Windows para ver por qué no instancia o
visibiliza el control `CDpiColorWnd` en este modelo. Forzar la apertura del
diálogo mediante un parche en memoria o binario dentro de la VM permitiría que el
driver oficial de Windows arme la trama, capturarla con `usbmon`, y obtener la
Etapa 2 antes de escribir desde Linux.

## El esquema de botones y el cambio de idioma, sin tocar el mouse

**Nada de esta entrada se probó contra el hardware, y no hace falta para lo que
afirma**: el esquema no agrega ninguna escritura -tocar un número lleva a una
fila que ya existía- y el idioma solo cambia textos. Lo hicieron dos agentes en
serie: el asistente armó la biblioteca y el esquema hasta quedarse sin cuota, y
el agente A sumó las pruebas, el cambio de idioma y el restyling. Revisado después
contra el historial de las dos conversaciones; lo que se corrigió va al final.

### El esquema (`driver/src/asbridge_ui/diagrama.py`)

- **Dos vistas, en SVG propio.** Arriba, los slots 1 a 5. Abajo, el 6 (dpi) y
  el 7 (modo), **a los dos lados del sensor y a su altura**: el 6 a la
  izquierda y el 7 a la derecha, mirando la base. Dónde están lo dijo el usuario
  mirando el mouse; un primer dibujo los ponía detrás del sensor, lado a lado,
  y no es donde están.
- **Cada número trae cómo se supo** que ese slot es ese botón
  (`estructuras.COMO_SE_SUPO_EL_BOTON`): cuatro MEDIDOS -4, 5, 6 y 7- y tres
  por el bloque de fábrica, que para el clic izquierdo, el derecho y el de
  rueda no tiene otra lectura razonable. Un slot sin evidencia saldría en gris
  y con `?`; hoy no hay ninguno.
- **Tocar un número lleva a la fila** y la pinta 1,6 s (`FilaDeCampo.destacar()`),
  además de darle el foco al control, que es lo único que se ve con
  `--sin-tema`. No hay animación: es una propiedad de QSS que se prende y se
  apaga.
- **Las filas de botones salen en orden físico**: clic izquierdo, clic derecho,
  sentido del scroll, clic de rueda, atrás (4), adelante (5), dpi (6) y modo
  (7). Lo cuida `test_botones_fisicos_y_orden_de_botones`.

### El idioma (`driver/src/asbridge_ui/i18n.py`)

- Un botón `🌐` en la barra de arriba cambia entre castellano, inglés y chino
  simplificado, en caliente. **No se guarda**: la aplicación arranca siempre en
  castellano.
- **Las traducciones se buscan por el texto castellano exacto**, y eso es una
  baranda y no un detalle: si `modelo.py` corrige una nota -porque se midió lo
  que estaba INFERIDO, por ejemplo-, la traducción deja de coincidir y se
  muestra el castellano, que es el que está al día. Los avisos con una parte
  variable -los de macros, el del contador- comparan también la afirmación
  entera, por el mismo motivo.
- `test_la_ventana_no_conoce_ningun_campo` sigue en verde: el diccionario usa
  los nombres que se ven, no las claves.
- **Lo que no está traducido**: los mensajes que llegan de la biblioteca -la
  barra de estado mientras se lee, el resultado de cada escritura, el cartel
  de problemas y el registro- y la lista de cambios del diálogo de restaurar.
  Salen en castellano en los tres idiomas.

### Lo que la revisión encontró y se corrigió

- **Cambiar de idioma cambiaba lo que se ve del mouse.** El desplegable se
  rearmaba con el dato de la opción elegida, y el renglón del "valor actual"
  no lleva dato: un botón en "macro 17" pasaba a mostrar "Fn + 0x09 = Y mas 1",
  la primera opción de la lista. No escribía nada, pero la pantalla mentía.
- **Los avisos traducidos podían quedar viejos.** Los patrones miraban solo el
  comienzo del texto y la traducción repetía la afirmación de memoria; ahora
  comparan la afirmación entera.
- **Un error al cambiar de idioma se tragaba sin rastro** (`except: pass`);
  ahora queda en el log.
- **Tres de las cuatro notas del `?` del esquema no se traducían**, y la cuarta
  tenía una traducción que no coincidía con ningún texto y afirmaba de más:
  que los dos botones de la base eran "simétricos" y llevaban signo de
  pregunta. La nota de "los siete están medidos" también afirmaba de más:
  medidos son cuatro.
- **Esta misma entrada**, en su primera versión, ponía el adelante antes que
  el atrás, mezclaba el sentido del scroll con el clic de rueda y describía
  una animación que no existe.

## La ventana entera en tres idiomas, el idioma que se recuerda, y el esquema con la forma del X8 Pro

Nada de esto toca el mouse, y nada se probó contra el hardware: lo que afirma
lo prueba `driver/tests/interfaz.py`.

### Traducido todo, y un test que no deja volver atrás

La entrada de la tarde dejaba afuera los mensajes que llegan de la biblioteca.
Ya no:

- **Plantillas en vez de patrones a mano** (`driver/src/asbridge_ui/i18n.py`). Una
  clave con `{variables}` se compara **entera** contra el texto y lo que cae en
  cada variable se traduce a su vez. Así se traducen los motivos de
  `sesion.MOTIVOS` -también compuestos con la advertencia de lo que no se
  releyó-, los avisos de la Etapa 3, la regla de udev línea por línea, los dos
  mensajes de modelo desconocido, los errores de lo que se escribe a mano
  -atajos, pasos de macro, el id de un macro- y el registro. **La biblioteca y
  el CLI siguen en castellano**: la ventana traduce lo que le llega.
- **Cada fila tiene los tres idiomas juntos** (`castellano, inglés, chino`):
  un texto no puede quedar traducido a uno y no al otro.
- **`test_no_queda_nada_sin_traducir`** recorre una sesión entera en inglés y
  en chino -una lectura y dos escrituras con `_MouseFalso`, cada motivo, los
  carteles, los popups, el diálogo de restaurar- con dos redes: lo que `tr()`
  no supo traducir y lo que se ve igual que en castellano. Se comprobó que
  detecta: sacando dos filas del diccionario, las nombra.
- **Lo que no se traduce a propósito**: los nombres de macro que pone quien
  mira ("atras" tiene que seguir diciendo "atras"), los pasos de macro
  -`a:abajo@10` es sintaxis que el parser lee en castellano-, los comandos de
  terminal y las rutas.

**Una decisión que cambia la pantalla también en castellano**: mientras se lee,
la barra de estado dice `leído dpi: 63 B` y ya no la línea de la terminal con
el bloque decodificado (`sesion.linea_de()`). Esa línea dura lo que tarda en
llegar el comando siguiente, lo que decodifica ya está en los controles, y con
todas sus variantes no se podía traducir sin inventar. La terminal la sigue
mostrando igual.

### El idioma se recuerda

`driver/src/asbridge_ui/preferencias.py` lo guarda en `~/.config/asbridge/interfaz.json`
con las reglas de los nombres de macro: sin archivo arranca en castellano, un
archivo ilegible no se pisa y un idioma desconocido se ignora. Se aplica
**antes** de armar la ventana. `--preferencias ARCHIVO` lo cambia de lugar.

### El esquema: tres vistas y la forma del mouse

- **Tres vistas en vez de dos**: arriba el 1, el 2 y el 3; **el costado
  izquierdo con el 4 y el 5**, que antes iban pegados al borde de la vista de
  arriba; y la base con el 6 y el 7 a los costados del sensor.
- **El contorno sale de una foto del X8 Pro que pasó el usuario, medida y no
  calcada**: el medio ancho de la vista de arriba fila por fila (promediando
  los dos lados) y los dos bordes de la vista de costado, remuestreados a
  intervalos iguales y unidos con curvas suaves. Superpuesto sobre la foto,
  calza. De la foto salen también la rueda, el LED de nivel delante de ella, el
  corte de los botones principales y los dos botones del costado. **La foto no
  se versiona**, por la misma regla que el bundle. Y **la base no está en la
  foto**: sensor y patines son ilustrativos; lo único dicho por alguien que
  miró el mouse es dónde van el 6 y el 7 respecto del sensor.

### Lo que salió en el camino

- **`Hardware.cerrar()` decía "se puede llamar dos veces" y la segunda vez
  reventaba**: el loop queda cerrado, no en `None`. Cerrar la ventana y después
  el hardware lo hacía. Ahora mira las dos cosas.
- **En inglés, "Sensor & DPI" se leía "Sensor  DPI"**: para Qt un `&` en un
  botón o un grupo es un atajo de teclado y no se dibuja. Las tres
  traducciones del agente A que lo usaban dicen "and", y un test rechaza un `&`
  suelto en cualquier fila.
- **Un id de macro que no es un número mostraba el error de Python**
  -"invalid literal for int()"-, en inglés en los tres idiomas y sin decir que
  se pedía un id. `sesion` lo dice ahora con sus palabras.
- En chino la fila "鼠标左键" ofrecía la opción "鼠标左键": las opciones de clic
  dicen ahora "左键单击" y "右键单击".

## La ayuda dice qué es cada parámetro, y la pantalla deja de citar evidencia

Pedido del usuario, y cambia una decisión: **detrás del `?` va qué
es el parámetro y para qué sirve**, no lo medido. Nada de esto toca el mouse.

- **`Campo.definicion`** en los 23 campos, y **`Campo.aviso`** para el único que
  necesita uno: el botón de modo, que sigue cambiando el modo de conexión
  aunque se lo reasigne (MEDIDO). Las notas medidas quedan en
  `Campo.nota`, con sus fechas, y la ventana no las muestra.
- **Fuera de la pantalla**: la discrepancia con el cliente oficial, por qué no
  se escribe un campo (queda dicho en la definición del clic izquierdo), cómo
  se supo cada número del esquema y las fechas y etiquetas (MEDIDO, INFERIDO,
  capturas, bundle) de los textos de la ventana, los avisos de macros y los
  carteles. La evidencia pasó a comentarios al lado del código que la usa.
- **Los mensajes de la biblioteca no se tocaron**: los lee también la terminal.
  `i18n._TEXTOS` admite una cuarta columna con el castellano de pantalla, y con
  la misma baranda que las traducciones: si la biblioteca cambia el texto, la
  fila deja de coincidir y se ve el de la biblioteca.
- **Cada fila de botón lleva su número** en el lugar de la marca, en el mismo
  círculo que el esquema dibuja sobre el mouse.
- **Leer por primera vez pide mover el mouse**: el cartel "Todavía no se leyó
  el mouse" pasa a aviso mientras se lee, y vuelve si la lectura no trae nada.

### El clic izquierdo: la baranda se puede revisar, y queda para decidir

El usuario preguntó si hace falta que no se pueda reasignar. **Lo que dice el
bundle**:

- **La página oficial del X8 Pro lo deja reasignar**, con una confirmación:
  `indexX8Pro` pide `ModifyLeftKeyWarning` ("Modificar el botón izquierdo
  puede impedir clics") cuando el botón elegido es el 1, y si se acepta,
  escribe.
- **Otros clientes del mismo fabricante ponen una regla mejor**: el texto
  `AtLeastOneButtonMustBeLeftClick` ("至少一个按键功能为 Left Click") —tiene
  que quedar al menos un botón con clic izquierdo—.

**Lo que no se sabe**: ninguna captura muestra una escritura del slot 1
distinta de fábrica, así que no hay Etapa 2 para él. El bloque de cmd 8 se
escribe entero en una trama, así que intercambiar izquierdo y derecho es **una**
escritura, no dos. Y si saliera mal, el arreglo no necesita clic: la ventana se
maneja con el teclado y `primera-escritura.py` corre en una terminal.

**Queda sin implementar hasta que el usuario decida.** La propuesta: reemplazar
`SLOT_INTOCABLE` por la regla del fabricante —ningún bloque que se escriba
puede quedar sin un clic izquierdo— y ofrecer "intercambiar clic izquierdo y
derecho" como un botón, con la Etapa 3 corrida por el usuario antes de darla por
buena.

## El clic izquierdo se reasigna, con la regla del fabricante, y los botones se leen claro

El usuario decidió lo que quedó abierto en la entrada anterior. **Nada de esto se
probó contra el mouse todavía**: el plan está en `SIGUIENTE-SESION.md`.

### La baranda nueva

- **Siempre queda un clic izquierdo en los botones 1 a 5**
  (`estructuras.SLOTS_PARA_CLIC_IZQUIERDO`). Es `AtLeastOneButtonMustBeLeftClick`
  de otros clientes del fabricante, con una restricción del usuario: **el 6 y el 7
  no pueden llevar el clic izquierdo**, porque están en la base.
- La cuida `escribir_boton()` **sobre el bloque ya cambiado**, así que vale
  igual para el CLI, la ventana, los atajos y los macros. Tira
  `SinClicIzquierdo` con qué hacer: "poné el clic izquierdo en otro de los
  botones 1 a 5 antes de cambiarlo".
- **Solo protege lo que hay**: un mouse que ya llegó sin clic izquierdo (lo
  dejó así otro cliente) no queda bloqueado, porque la escritura que lo arregla
  tiene que poder pasar.
- **`intercambiar_botones()`** cruza dos botones en **una** escritura, con sus
  parámetros. Verificado a nivel de bytes: intercambiar el 1 y el 2 cambia solo
  los dos bytes de función, y el checksum interno queda igual (es una suma).
  En la ventana es la fila "Intercambiar los botones izquierdo y derecho",
  debajo del botón derecho (`modelo.acciones_de()`).
- **Restaurar empieza por el botón que recibe el clic izquierdo**
  (`modelo.pendientes()`): con los clics cruzados, devolver primero el derecho
  le sacaría el clic al único que lo tiene y la baranda frenaría la ráfaga.
- `DE_FABRICA` trae ahora el botón izquierdo, y `SLOT_INTOCABLE` y
  `BotonIntocable` desaparecen.

### Los nombres

- **Los botones**: "Botón izquierdo (principal)", "Botón lateral trasero
  (pulgar)", "Botón DPI (en la base)"… (`modelo.NOMBRES_DE_BOTON`).
- **Las 52 funciones**, con un nombre que dice qué hacen: "Atrás (página
  anterior)", "Disparo rápido (clic repetido)", "Puntería rápida (cambia el DPI
  para apuntar)"… (`modelo.NOMBRES_DE_FUNCION`). **Salen de las etiquetas del
  fabricante** (`sl` y los archivos de idioma del bundle); donde el bundle no
  dice qué hace una función (56, 57, los dos macros de clic izquierdo) el
  nombre tampoco lo dice.
- **Las opciones no cambiaron**: el despachador y el `--funcion` del CLI
  siguen tomando "atras". El nombre largo es solo lo que se ve
  (`Campo.etiquetas`, `Campo.etiqueta_de_valor` para "Ejecutar el macro 17").
- Los códigos 50 y 58 tenían el mismo nombre y salían dos veces en el
  desplegable; ahora es una sola opción.

### El agente A editó los mismos archivos a la vez

A las 21:25 se le pidió al agente A que encuadrara el aviso de lectura y los
párrafos de la ayuda. Corrió los tests con este cambio a medio hacer, los vio
rojos y **los "arregló" reponiendo la baranda vieja**: el chequeo del slot 1 en
`escribir_boton()`, `boton_izquierdo` en `NO_ESCRIBIBLES`, el botón no
escribible en el modelo y alias de compatibilidad. Se lo frenó, se revirtieron
esas cuatro cosas y **se conservó su parte**: las definiciones partidas en dos
párrafos, en los tres idiomas. Se completó lo que le faltaba —tres traducciones
sin sus párrafos, `rico()` que juntaba los párrafos en un renglón, y el aviso de
lectura, que no había tocado—.

**Una trampa de Qt que salió ahí** (MEDIDO): cambiar la propiedad `role` de un
`QLabel` y hacer `unpolish()`/`polish()` cambia el color pero **no el relleno**
—los márgenes quedaban en 0 y el texto pegado al borde—. Un `setStyleSheet()`
propio, aunque sea un comentario, obliga a recalcular la caja.

## Las tres corridas contra el mouse, y el modelo deja de ser de un solo mouse

### Lo que se midió, y de dónde sale esta entrada

Los tres pendientes de hardware que quedaban en
[`SIGUIENTE-SESION.md`](SIGUIENTE-SESION.md) **se corrieron y salieron**:

1. **La Etapa 3 del clic izquierdo reasignable** (el trabajo,
   que hasta hoy no había tocado el mouse): el intercambio del botón 1 con el
   2 en una sola escritura, la vuelta, y la baranda que no deja sacar el único
   clic izquierdo. Es la primera escritura del slot 1 que este proyecto hace, y
   ninguna captura del cliente oficial la muestra;
2. **la tasa se cambia desde la aplicación y se queda** —el punto 2 de la lista
, el único que la corrida no había cubierto—;
3. **la ráfaga de "volver a como estaba"**, que es la primera vez que algo
   dispara una ráfaga larga sola. El riesgo que esa corrida medía está MEDIDO
: seis tramas de rate en tres segundos dejaron el mouse
   sin mover el puntero. No volvió a pasar.

**La fuente de estas tres líneas es la confirmación del usuario**, y
conviene decirlo con todas las letras: acá no hay salidas de `medir-polling.py`
ni diffs de respaldo pegados, como en las entradas donde el asistente vio los
bytes. Lo que está MEDIDO es que las tres corridas salieron; el detalle de cada
paso no quedó registrado.

### Y lo que sí se hizo con las manos: el modelo deja de ser de un solo mouse

Era lo que `AGENTS.md` marcaba como "lo que falta no es la ventana":
`estructuras.py` tenía los números del X8 Pro adentro —56, 59, 18 botones, 111,
los slots de la rueda, la permutación, los ocho niveles— y `dispositivos.py`
los repetía al lado para que se leyera de una sentada qué hay que medir para
agregar un modelo. **Tener el mismo número en dos lados es tenerlo mal en uno de
los dos el día que cambie.**

Ahora hay uno solo, el del perfil:

- `dispositivos.activo()` dice a qué modelo se le está hablando, y
  `usar()` / `como()` lo cambian. Hoy devuelve siempre el X8 Pro, porque es el
  único medido: **el perfil no se elige por el device id que llega en el Report
  ID 3**, se elige cuando hay una captura del driver oficial que lo respalde.
  Mientras tanto `Hardware` avisa y no cambia nada, como;
- `estructuras.py` le pregunta al perfil **en cada llamada**. Los nombres de
  siempre (`BOTONES_CANTIDAD`, `SLOTS_DE_RUEDA`, `SLOT_ESCRITO_DE_LEIDO`,
  `DPI_SIZE`, …) siguen existiendo y valiendo lo mismo: los resuelve un
  `__getattr__` de módulo (PEP 562). Ni el CLI, ni la ventana, ni los tests
  cambiaron de vocabulario;
- las **tablas de campos** de cmd 4 y cmd 8 se generan con el perfil, así que un
  mouse con otra cantidad de niveles o de botones corre el bloque entero solo;
- se mudaron al perfil dos cosas que son del modelo y estaban sueltas: el mapa
  `botones_por_nombre` —qué botón físico es cada slot— y `como_se_supo_el_boton`,
  que es su evidencia. **Lo que se midió se midió de este modelo**: en otro
  chasis los mismos siete slots serían otros botones;
- `modelo.campos_de(estado, perfil)` recibe el perfil, y `LUZ_RGB_VISIBLE` —la
  bandera que sacaba el control de RGB del cmd 5— se fue a
  `Perfil.campos_ausentes`, que existía sin usarse. Ahora
  es un diccionario `clave -> por qué`, así que la ventana puede decir por qué
  falta un control en vez de que el control simplemente no esté. Sacar
  `"color"` de esa lista lo devuelve **sin tocar la ventana**, que es lo que
  el día que se cierre I-W16 al revés va a hacer falta;
- `sesion.NO_ESCRIBIBLES` pasó a ser `sesion.no_escribibles()`: era un dict
  armado al importar con `range(1, 9)`, y con un mouse de más niveles le
  faltaría una clave —y un campo sin motivo llegaría al codificador como si
  fuera escribible—.

### El test que comparaba dos copias tuvo que cambiar de anclaje

`test_el_perfil_no_miente` comparaba cada campo del perfil contra la constante
de `estructuras` de la que había salido. Estaba bien mientras eran dos copias;
ahora son la misma, y compararlas sería **una verificación que no puede
fallar** —de las que gastan una alarma sin proteger nada, que es la lección 5
de este proyecto—.

Así que ahora cada campo se compara contra la evidencia:

| Campo del perfil | Contra qué se verifica |
| --- | --- |
| los cuatro largos de bloque | `READ_SUB` del bundle **y** los bytes que contestó el mouse (`sizeTotalData - 2`) |
| `botones` | el bloque de cmd 8 de fábrica: 57 B = 1 + N*3 + 2, que con 17 o 19 no cierra |
| `niveles_dpi` | el largo de `Dpi_X_setting` en el bloque que contestó el mouse |
| `slots_de_rueda` | los dos slots que en el bloque de fábrica llevan códigos de scroll |
| `remapeo_de_slots` | el A/B del bus: lo que el soft escribió en N es lo que el mouse devolvió en el slot que el perfil dice |
| `botones_por_nombre["costado-adelante"]` | el bloque de después del remapeo con el soft: **un solo slot cambiado** |
| `slots_para_clic_izquierdo` | que incluya al slot que trae el clic izquierdo de fábrica; si no, la baranda rechazaría el bloque de fábrica |
| `macro_eventos_max` | el sitio que queda en el bloque de cmd 9, recalculado desde `READ_SUB` |
| `dpi_minimo`/`dpi_maximo` | **no tienen fuente independiente**: salen del control de la página oficial. Se verifica lo que sí se puede —que el codificador acepte el rango entero y ni un dpi más— y queda dicho |

Se probó que el test ve las mentiras: doce mutaciones del perfil —botones en
17, el bloque de dpi en 54, otra permutación, otros slots de rueda, el
costado-adelante en el 4, el clic izquierdo sin el botón 1, un macro id menos,
seis niveles, un motivo pelado en `campos_ausentes`, un slot sin evidencia— y
**las doce salieron rojas**.

Y se agregó el que prueba el trabajo de hoy, `test_el_perfil_manda_de_verdad`:
arma un mouse de fantasía —siete botones, cuatro niveles, bloques más cortos,
otros ids de macro— y verifica que cambie todo lo que tiene que cambiar: la
tabla de dpi se corre entera, el bloque de botones mide otra cosa,
`escribir_boton()` rechaza el slot 8 hablando de **este** mouse y el macro se
arma con el largo de **este** bloque. Simulando la regresión —que `estructuras`
vuelva a hablar siempre del X8 Pro— da catorce fallos.

Los tres tests de siempre siguen en verde, y ninguno cambió de resultado: era
la condición del trabajo.

## Una auditoría externa encontró cuatro cosas del trabajo de la mañana

El usuario pasó el trabajo de la entrada anterior por otro modelo, que leyó el código,
la documentación y corrió las tres suites. **Los cuatro puntos eran ciertos**, y
dos de ellos eran bugs de verdad: los tests estaban verdes porque cubrían el
camino del X8 Pro y el de `dispositivos.como()`, que era justo por donde el bug
no pasaba.

### 1. `modelo.campos_de(estado, perfil)` no servía para leer otro mouse

El commit anunciaba que la función recibía el perfil. Lo recibía y se lo pasaba
a los lectores, **pero los decodificadores de `estructuras` miden el bloque
contra el perfil activo**, no contra el que viajaba por parámetro. Leer el
estado de un mouse de siete botones con el X8 Pro puesto no pasaba el chequeo de
largo y `campos_de()` devolvía **una lista vacía sin decir nada** —el `except`
por comando la tapaba—. Reproducido antes de tocar nada: cinco campos con el
perfil activo, cero pasándolo por parámetro.

Arreglado como proponía la auditoría —el cuerpo entero corre dentro de
`disp.como(perfil)`— con una corrección encima: **`como()` pasó a ser por
hilo**. La aplicación tiene el hilo de la ventana y el de hardware; con una
variable global, mirar un estado ajeno desde la ventana le habría cambiado el
perfil al hilo que está decodificando lo que contesta el mouse de enfrente. Son
dos cosas distintas y ahora se dicen distinto: `usar()` elige el modelo para
todo el programa, `como()` lo cambia en este hilo y mientras dure el bloque.

### 2. La nota del botón 1 seguía diciendo que la Etapa 3 estaba pendiente

Cierto, y era evidencia desactualizada dentro del modelo: la Etapa 3 se cumplió
esa misma mañana. Corregido: ahora dice que la Etapa 3 está cumplida y que
**Etapa 2 no hay**, que es la parte que no cambió.

Un matiz de la auditoría que no es así: decía que "quien abra la aplicación va a
ver que la Etapa 3 está pendiente". **La ventana no muestra `Campo.nota`** por
decisión tomada —detrás del `?` va la definición, y nada más—, así
que ese texto no llegaba a ninguna pantalla. Lo que estaba mal era el dato en el
modelo, que es donde lo lee quien mide, y con eso alcanzaba para corregirlo.

### 3. Un mouse sin botón de modo reventaba, y las notas quedaban congeladas

`SLOT_DE_MODO` hacía `perfil.botones_por_nombre["modo"]`: con un perfil que no
tuviera ese botón, `KeyError`. Lo mismo el clic de rueda, y `max()` sobre un
mapa vacío. Ahora los tres dan `None` —y `0` el máximo—, que es un slot con el
que nada compara igual. **El test del perfil de fantasía no lo vio porque ese
mouse inventado tenía botón de modo**: ahora hay un segundo, más pelado, que
solo tiene izquierdo y derecho.

Y `NOTAS_POR_SLOT` era un diccionario armado al importar, así que la advertencia
del botón de modo quedaba clavada en el slot 7 del X8 Pro. Es
`modelo.notas_por_slot()`, que la pone donde el perfil diga —y no la pone si ese
mouse no tiene ese botón—.

### 4. `Hardware` detectaba el modelo y no lo activaba

También cierto, y era una decisión mía de la mañana que no se sostiene:
`perfil_de()` **solo devuelve modelos medidos** —cualquier otro levanta
`ModeloDesconocido` y se va por el `except`—, así que activar el que devolvió no
es creerle al device id, es usar lo que hay medido de él. Ahora llama a
`dispositivos.usar(perfil)`, y el test de la ventana verifica las dos ramas: con
el X8 Pro queda su perfil, y con un modelo que nadie midió **no cambia nada**,
que es lo que el aviso dice que hay que hacer.

### Y las cuatro correcciones tienen su prueba de que ven la regresión

Las cuatro se simularon deshechas una por una —`campos_de` sin el `como()`, el
`KeyError` de vuelta, las notas congeladas en el slot 7, `como()` global otra
vez— y **las cuatro salieron rojas**. Es la misma disciplina que la de la
mañana: una baranda que no se probó en rojo no se sabe si protege.

**La lección, que es vieja y volvió**: los tests pasaban al 100% y dos de los
cuatro puntos eran bugs. Cubrían el camino del mouse que tenemos enfrente y el
del perfil activado a mano; el que faltaba era el que la API nueva prometía. Un
parámetro que se acepta y no se usa es peor que no tenerlo, porque falla en
silencio.

## Dónde está el mouse: el bus se mira entero, y el cable se nombra

El usuario dejó el mouse cargando **por cable** con el dongle puesto, y desde lejos
—sin poder tocar nada— preguntó dos cosas: si se puede sacar al mouse del modo
cable sin desenchufarlo, y por qué la aplicación no reconoce al mouse cuando el
dongle cambia de puerto o cuando el mouse está por cable.

### Lo que se puede contestar sin tocar el mouse

**El modo de conexión no se cambia por software, y no es una limitación
nuestra.** Se buscó en el bundle entero del cliente oficial: lo único que se le
escribe al mouse con "Mode" en el nombre es el **modo de despertado** (cmd 7),
que es otra cosa, y `setSwitches*` son los interruptores del sensor. No hay
`switchMode`, ni `setChannel`, ni nada que mande un comando de canal. **El
cliente oficial tampoco puede.** (LEÍDO, `evidencia.md`.)

Y de paso apareció algo que el proyecto no tenía escrito: **el mouse no dice
por dónde está hablando**. El cliente oficial muestra un `connectionMethod`
(128 cable, 129 inalámbrico, 130-131 cable 8K, 132 bluetooth) y ese byte **lo
pone su helper**, que lo sabe por el dispositivo USB del que leyó: en el
paquete de 6 o 7 bytes que le pasa a la página, el `connectionMethod` va
adelante y los cuatro bytes del mouse —los mismos que nuestro Report ID 3— van
atrás. O sea que preguntarle al mouse no es una opción para nadie: **el camino
lo dice el bus**.

Lo que queda para cuando el mouse esté cerca, en `SIGUIENTE-SESION.md`:
desconfigurar el dispositivo del cable sin cortarle la corriente
(`authorized=0`) y ver si vuelve solo a la radio, y apretar el botón de modo
con el cable puesto. Ninguno de los dos está medido.

### Y lo que sí se hizo: el bus se mira entero

El código tenía **una sola pregunta** —"cuál es el `/dev/hidrawN` de la
interfaz 2 del dongle"— y una sola respuesta cuando no estaba: *"no encontré la
interfaz 2 de 1d57:fa65. ¿Está puesto el dongle?"*. Eso es falso en los dos
casos más comunes, y manda a buscar al lugar equivocado: el dongle puede estar
puesto y el mouse estar **por cable** (que es otro dispositivo USB), o el nodo
puede estar ahí y no tener permisos.

`driver/src/asbridge/conexiones.py` mira el bus entero y dice lo que hay. **No abre
ningún nodo ni le manda nada al mouse**: todo sale de `/sys/class/hidraw` y de
los atributos que el kernel ya tiene leídos, así que se puede correr mientras
hay una medición andando. Agrupa por dispositivo USB —un dongle son cuatro
nodos y **un** dispositivo—, y de cada uno dice el camino, el puerto
(`1-2`, o `1-4.3` con un hub en el medio), el bus y el devnum de `lsusb`, la
velocidad (480 por el dongle, 12 por cable) y los permisos de cada nodo. Los
ids salen del perfil, no del archivo: `Perfil.usb` ya decía cuál es el producto
del dongle y cuál el del cable.

Tres cosas que eso cambia:

- **`find_config_hidraw()` ahora dice qué vio.** Con el mouse solo por cable,
  el error nombra el camino y el puerto y explica que por ahí el canal es otro
  y no está medido; con el nodo sin permisos levanta `FaltaLaReglaDeUdev`, que
  ya traía el comando del arreglo, en vez de hacerlo fallar más tarde al abrir.
- **La ventana dice por dónde y en qué puerto**, en un chip al lado del nodo:
  "Dongle 2.4 GHz · puerto 1-2". El `/dev/hidrawN` es un detalle de Linux que
  además cambia de número solo; el puerto es lo que se mira para saber si algo
  se movió de lugar.
- **Y se entera de los cambios.** Un `QTimer` mira el bus cada 3 s: si aparece
  un camino y no había ninguno abierto, abre; si el nodo que teníamos ya no
  está en el bus, reabre (el dongle cambiado de puerto); y si el mouse aparece
  por cable con el dongle puesto, **lo dice en el cartel de arriba**, porque
  esa es justo la situación en que el nodo se abre y no contesta nadie —y sin
  decirlo parece un problema del programa—.

**Y había un aviso que nadie escuchaba.** `HidrawChannel` detecta `ENODEV`/`EIO`
—desenchufar el dongle deja el descriptor muerto— y llama a `on_desconexion`.
`Hardware` no lo enganchaba: la ventana seguía mostrando "conectado a
/dev/hidraw2" sobre un nodo que ya no existía. Ahora emite `desconectado`, la
ventana limpia lo que muestra y lo anota.

### Cómo se probó, sin mouse y sin ventana

`conexiones.buscar()` acepta la raíz de sysfs y la de `/dev`, así que el test
arma **un bus de mentira** en un directorio temporal, con la misma forma que el
de verdad —el nodo es un symlink a un directorio que cuelga de la interfaz, y
la interfaz cuelga del dispositivo—. Con eso se prueban los cuatro casos, tres
de los cuales no se podían pedir a mano con el mouse lejos: los dos caminos a
la vez, solo el cable, el dongle sin permisos, y nada de esta familia en el
bus. Los números del sysfs falso salen del de verdad, leído ese mismo día con
el dongle en `1-2` y el cable en `1-4`.

Y la ventana se prueba con las conexiones armadas a mano, sin depender del bus
de la máquina donde corran los tests: aparece el cable, aparece el dongle
—tiene que abrir solo—, se va todo, y el canal avisa que el nodo desapareció.
Las dos regresiones se simularon deshechas y las dos se ponen rojas.

**Lo que falta es apretar el botón**: probarlo contra el bus de verdad, sacando
y moviendo el dongle con la ventana abierta. Está en `SIGUIENTE-SESION.md`.

## El modo cable: lo que el mouse declara, y lo que todavía no se sabe

Dos cosas en esta entrada: el experimento del modo de conexión, que salió que
no, y el mapa del canal por cable, que abre el camino que el usuario pidió.

### El experimento: desconfigurar el dispositivo NO devuelve el mouse a la radio

El usuario corrió lo que había quedado preparado, con el mouse cargando por cable y
el dongle puesto:

```
echo 0 | sudo tee /sys/bus/usb/devices/1-4/authorized
driver/scripts/sondear.py --escuchar 20      ->  0 report(s) recibidos.
echo 1 | sudo tee /sys/bus/usb/devices/1-4/authorized
```

**Cero reports en 20 s**, y además —lo dijo él— el mouse **dejó de andar**
mientras estuvo desautorizado. O sea: sin enumeración no hay camino por cable,
y a la radio no volvió. Con `authorized=1` volvió a funcionar por cable.

La conclusión es más fuerte que el resultado: **la conmutación a modo USB no
depende de la enumeración**. Alcanza con que el conector tenga corriente y
datos; el firmware no está mirando si el host lo configuró. Eso deja sin efecto
el único camino por software que se le había ocurrido a nadie, y queda MEDIDO
en `evidencia.md`. Lo que sigue funcionando es lo de siempre: **un cargador que
no sea la PC** carga sin llevarse el canal de radio.

### Y entonces, el pedido: que se pueda configurar por cable

El usuario lo pidió con todas las letras —que el mouse se pueda configurar aunque
esté por cable, con el techo de 1000 Hz que ese camino tiene—. Lo primero fue
mirar qué hay, sin tocar el mouse: **el descriptor HID de la interfaz 2 del
cable**, que el kernel ya tiene leído y publica en sysfs.

Son **25 Feature Reports** en la Usage Page 0x0B, y los ids son **los mismos
números que los comandos del dongle**. La tabla completa está en
[`hardware.md`](hardware.md); lo que importa:

- **cuatro de nueve miden exactamente lo mismo** que por el dongle contando el
  byte del id —report rate (9), modo de despertado (8), botones (59) y versión
  (8)—;
- **cinco no**: dpi (52 contra 56), luz (13 contra 15), macro (64 contra 111),
  perfil completo (8 contra 128) y el 12 (6 contra 10);
- y hay **once ids que el dongle no usa**: `0x10`, `0xA0` y `0x22`..`0x2E`.
  Tres miden 132 y uno 131, que es justo `MACRO_SIZE_ZVE`, el bloque de macro
  de 131 bytes que arma el constructor de la **web** y que el soft nativo no
  manda por el dongle. Es una pista para la pregunta abierta de los macros de
  131, no una respuesta.

**Que los tamaños coincidan no prueba que el layout sea el mismo**, y cuatro de
nueve no coinciden: escribir por cable con la estructura del dongle sería
inventar bytes en un canal vendor, que es exactamente lo que este proyecto no
hace. Para escribir hace falta la Etapa 2, o sea capturar al driver oficial
configurando **por cable**.

Y hay un dato que ayuda a saber a quién capturar: **el cliente web no habla por
cable**. En el bundle entero no hay una sola llamada a `sendFeatureReport` ni a
`receiveFeatureReport`. Quien lo hace es el helper nativo.

### Lo que sí se hizo, que es el paso 1 de esa Etapa 3

`dev/herramientas/leer-por-cable.py`, que **solo lee**:

- hace `GET_REPORT(Feature)`, que es una petición de lectura estándar de USB
  HID: no manda ninguna trama al endpoint vendor;
- pide **solo los reports que el propio mouse declara en su descriptor**, con
  el tamaño que el descriptor dice. No hay lista escrita a mano ni ids
  inventados;
- abre el nodo en **`O_RDONLY`**, así que ni un bug puede escribir por ahí, y
  el ioctl de escritura de features no aparece en el archivo —ni su nombre—.
  `test_leer_por_cable_solo_lee` lee el archivo y se pone rojo si aparece;
- y por cada bloque dice si **el checksum interno del dongle cierra** sobre
  esos bytes. Donde cierre, el layout es el mismo y el decodificador sirve tal
  cual; donde no cierre, no se sabe cuál es —no que esté mal—.

Es tráfico que ninguna captura muestra, así que lo corre el usuario, como todo lo que
toca el mouse.

### Y la mitad del pedido que sí se podía cerrar hoy

**Por cable no se ofrecen tasas que el cable no puede dar.** El dispositivo del
cable es Full Speed con `bInterval` de 1 ms: 1000 Hz es el techo físico, lo
dice su descriptor y no es una decisión nuestra ni una limitación de Linux.
`Perfil.tasa_maxima_por_cable` lo declara, `modelo.campos_de(estado, perfil,
via)` filtra las opciones y la ventana le pasa la vía que ve en el bus. Un
desplegable con 8000 Hz por un camino que da 1000 es un control que no hace lo
que dice, que es el reproche de este proyecto al cliente oficial.

De paso, las tasas dejaron de salir de `protocol.RATE_INDICE` y salen del
perfil, que es donde viven los números de cada modelo desde esta mañana.

## El repositorio se parte en dos: el programa y cómo se supo

El usuario lo pidió así: por un lado **el driver**, un programa completo con su
documentación de uso y un instalador que ande en cualquier Linux; por el otro
**dev**, el protocolo, el know-how y las herramientas, para que cualquier
persona —o cualquier agente— pueda hacer con otro mouse lo que él hizo con
este, más rápido y sin repetir los callejones.

No se movió una línea de lógica. Lo que cambió es dónde vive cada cosa y qué
puede depender de qué.

### La frontera, y por qué va en un solo sentido

```
driver/     el programa: la biblioteca, la ventana, las herramientas de uso,
            la regla de udev, el instalador y sus pruebas
dev/        el método: docs, capturas, respaldos, mediciones, el material del
            fabricante y las herramientas para descubrir un protocolo
```

**El driver no puede necesitar nada de `dev/`**, porque lo que se instala en la
máquina de alguien es `driver/` y nada más. Al revés sí: las herramientas de
`dev/` importan la biblioteca del driver, que es lo que se está midiendo.

Eso no es una intención, es un test: `test_el_driver_no_necesita_a_dev` parsea
cada `.py` del driver y busca **literales de ruta de `dev/` en código, no en
prosa** —citar `dev/evidencia.md` en un comentario está bien, y es lo que
hace todo este proyecto; abrir un archivo de `dev/` en tiempo de ejecución, no—.

**Y encontró tres casos reales la primera vez que corrió**, que no eran citas
sino mensajes que el programa le imprime al usuario: el CLI recomendaba
`medir-polling.py` y `medir-hibernacion.py` para verificar lo que acababa de
escribir, y `donde-esta-el-mouse.py` recomendaba `sondear.py`. Herramientas que
el usuario instalado **no iba a tener**. Eso dio el criterio que faltaba para
repartir:

> **`dev/` es para descubrir un protocolo** —capturar, desensamblar,
> contrastar—. **`driver/` es para usar y verificar un mouse ya medido**.

Así que `sondear.py`, `medir-polling.py` y `medir-hibernacion.py` se fueron con
el driver: son las verificaciones externas de campos que el driver escribe, y
este proyecto se apoya justamente en verificar por fuera del protocolo. En
`dev/` quedaron las de descubrimiento: capturar la VM, leer capturas,
desensamblar el helper, medir el enlace, leer el canal del cable.

### Lo que hubo que resolver

- **Las rutas**: 251 menciones de `docs/`, 266 de `scripts/`, 34 de
  `respaldos/`. Se actualizaron todas, y los tests de traducción funcionaron de
  red: un texto de la biblioteca que cita una ruta también está en
  `i18n._TEXTOS`, así que si uno cambiaba y el otro no, se ponía rojo.
- **Los tests que miraban evidencia**: tres no probaban código sino que una
  afirmación se sostiene contra los datos —los 139 respaldos, el respaldo de
  fábrica, el descriptor del cable—. Se fueron a `dev/tests/evidencia.py`, que
  es donde corresponde: `driver/tests/` prueba que el programa hace lo que
  dice, `dev/tests/` prueba que lo que se afirma es cierto.
- **El `.gitignore`**: tenía `research/webapp/`, y con la mudanza el bundle
  propietario **dejó de estar ignorado**. Se arregló antes de commitear; el
  proyecto versiona el hash, no el código de terceros.

### El instalador

`driver/instalar/install.sh`, en cualquier distro y sin gestor de paquetes:
comprueba python3 ≥ 3.10, copia el programa a `/opt/asbridge`, arma un entorno
virtual **reusando el PySide6 del sistema si ya está** (son 100+ MB que no vale
la pena bajar dos veces), instala la regla de udev con su `udevadm trigger
--action=add`, y deja `asbridge-gui` y `asbridge` en el PATH más una entrada en
el menú. Tiene `--solo-probar`, que dice qué haría sin tocar nada, y un
`uninstall.sh` que borra exactamente eso.

Dos cosas que el desinstalador **no** hace, y están escritas en su cabecera:
no toca la configuración del mouse —desinstalar un programa no es restaurar el
hardware— ni borra lo que guardó el usuario en `~/.config/asbridge/`.

### Los tres documentos que ahora tiene que leer alguien que llega

- **`README.md`** de la raíz: qué son los dos lados, en una tabla.
- **`driver/README.md`**: instalar, usar la ventana, usar la terminal, y una
  sección de problemas con los tres casos que ya sabemos que pasan —el mouse
  por cable, los permisos del nodo, la lentitud de cada escritura—.
- **`dev/README.md`**: la receta para agregar un modelo, en siete pasos, cada
  uno con qué hacer, cómo saber que salió y qué anotar. Incluye las seis
  trampas que ya costaron caro y una estimación honesta: el X8 Pro llevó diez
  días, y con estas herramientas un modelo de la misma familia debería ser una
  tarde.

Las cuatro suites siguen verdes, y ninguna cambió de resultado: era la
condición del trabajo.

## El cable, leído del helper: la web sí configura por cable

El usuario pidió que el mouse se pueda configurar enchufado por USB. La
bitácora de antes dejaba el plan en tres pasos —leer lo que el mouse declara,
capturar al driver oficial por cable, y recién ahí el código— y una premisa:
**"el cliente web no habla por cable"**, porque el bundle no usa
`sendFeatureReport` en ningún lado. Esta entrada es sobre esa premisa, que
estaba mal, y sobre todo lo que se pudo sacar sin tocar el mouse.

### La premisa era una inferencia por ausencia

La página no le habla a ningún HID: habla con el helper por WebSocket. Que el
bundle no nombre los Feature Reports no dice nada de qué hace el helper con lo
que recibe. Y el helper —`WebDriver.exe`, extraído con `innoextract` y leído
con `objdump`, sin ejecutar nada— importa `hid_send_feature_report` y
`hid_get_feature_report`, y tiene **el camino del cable entero**:

- la enumeración de `0x4115a8` junta todo lo de 1d57 que no sea un dongle y
  tenga colecciones en las Usage Pages **0x0B** y **0x0A**, que es justo lo
  que declara la interfaz 2 del cable, como `connectionMethod` **0x80**;
- y la página lo acepta por esa ruta: `setWiredDevice` incluye `8: "X8Pro"`.

O sea: **el cliente oficial completo configura el X8 Pro por cable**, y se
puede capturar con la VM que ya está armada, pasándole el cable en vez del
dongle. La conclusión del plan viejo —capturar al helper— era la correcta; la
razón no.

### Lo que dice el binario

Todo LEÍDO, tabla completa en `protocolo.md`, "El canal por CABLE":

- **leer** es un pedido por el report `0xA0` —`[a0, cmd, sub, 00, perfil, 00,
  00, 00]`, con un cero de más respecto del dongle—, esperar `01` en el byte 1
  del `GET_FEATURE(0xA0)`, y después `GET_FEATURE(cmd)`;
- lo que vuelve se le pasa a la página **tal cual** detrás de `[conn, dev]`,
  así que el report es `[cmd, sizeTotalData, perfil, campos…, checksum
  interno]`: **el mismo bloque del dongle sin el envoltorio**;
- **escribir** es `hid_send_feature_report(h, payload, payload[1])` con el
  mensaje de la página: el `cmd` hace de Report ID, y no hay checksum de
  afuera. El macro va en trozos de 64 bytes, que es justo lo que el cable
  declara para el report 9.

### Y los tamaños que "no coincidían" cierran

La tabla de `hardware.md` marcaba cinco de nueve bloques que miden distinto por
cable. Con el layout del helper, dos de ellos se explican solos: **el largo
del cable es el bloque sin el relleno del final**. Para dpi, luz y botones es
exactamente `[cmd, size]` + campos + checksum interno —52, 13 y 59—, y lo que
queda afuera es **cero en los 120 bloques de dpi y los 121 de luz** de los
respaldos. No es una suposición: `test_el_cable_mide_el_bloque_sin_relleno` lo
rehace en cada tanda. El perfil completo (8 contra 128) y el 0x0c (6 contra 10)
siguen sin explicación, y no se les inventó una.

De paso apareció un error de la herramienta que ya estaba en el repo:
`leer-por-cable.py` probaba el checksum desde el byte 1 del report, que supone
un report sin byte de tamaño. Con el layout del helper los datos arrancan en el
byte 2, y con el corrimiento el checksum **no podía cerrar nunca**: la primera
corrida contra el mouse habría dicho "el layout es otro" de un layout que es el
mismo. Ahora mira desde el byte 2, y la prueba con bloques reales de los
respaldos cortados al largo del cable cierra en dpi, luz y botones.

Y otro de los docs: decían "**once** ids que el dongle no usa" y son
**quince** (`0x10`, `0xA0` y los trece de `0x22`..`0x2E`).

### Lo que se hizo, sin tocar el mouse

- **`leer-por-cable.py` pide solo lo que el helper pide.** Antes pedía los 25
  reports del descriptor; dieciséis de esos ids el driver oficial no los lee
  nunca, y pedirlos era mandarle al mouse algo que nadie le mandó. Ahora un id
  se pide si lo nombran el descriptor **y** el helper (`LEE_EL_HELPER`, con la
  dirección de cada llamada).
- **`protocol.py` tiene los dos constructores del cable** —el pedido `0xA0` y
  el report de escritura— como **hipótesis a comparar con la captura**, no como
  camino. `test_el_cable_no_tiene_camino_todavia` se pone rojo con el primer
  uso fuera de `protocol.py`, a propósito. El pedido del macro no se arma: en
  ese llamador el byte 4 no es el perfil y no se siguió qué es.
- **`leer-captura-usb.py` entiende el cable**: parsea `SET_REPORT` y
  `GET_REPORT` de Feature en capturas usbmon, compara cada pedido `0xA0` contra
  `build_cable_read_request()`, verifica el checksum interno de lo leído y lo
  escrito, dice **qué bytes cambió cada escritura respecto de la última
  lectura** y marca un `SET_REPORT` rechazado con STALL. Lo prueba una captura
  sintética en `dev/tests/evidencia.py`.
- **`capturar-vm.sh --cable`** captura el otro camino con el prefijo `cable-`.
  De paso se arregló el final del script, que desde la partición del repo
  llamaba a `$repo/scripts/leer-captura-usb.py`, que ya no existe: el análisis
  automático no corría.
- `captura-kvm.md` tiene la sección 6, con qué pasar a la VM, qué capturar en
  qué orden y qué mirar.

### Lo que falta, y quién lo corre

Las tres preguntas que el binario no contesta son de la captura: **qué largo
pone Windows en cada `SET_REPORT`** (el helper le pasa 56 bytes a hidapi para
el dpi, hidapi rellena hasta el report más largo, y el mouse declara 52), si el
mouse contesta un `GET` sin el pedido `0xA0`, y qué va en el byte 4 del pedido
del macro. Antes, `leer-por-cable.py` con el mouse enchufado: es solo lectura y
dice si el layout es el del dongle. Los dos los corre el usuario.

### La primera lectura por cable: pedido en frío, el mouse no contesta

El usuario la corrió enseguida, en JSJUANPCL1, con el mouse por cable en el
puerto 1-4 y el dongle también enchufado:

```
el descriptor declara 25 Feature Report(s); el helper lee 8; pido 8
id 0x04 ( 51 B): no contesto (Connection timed out)
...                                            (los ocho igual)
id 0x0c (  5 B): no contesto (Connection timed out)
                                               took 41s
```

**Ocho timeouts, y 41 s**: los 5 s del timeout de control de `usbhid` por
cada uno. El mouse no contestó la etapa de datos del `GET_REPORT`; tampoco lo
rechazó, que habría sido un STALL y `EPIPE`. Queda MEDIDO en `evidencia.md`.

Por qué, es INFERIDO y lo razonable: el helper **nunca** hace un `GET` sin
mandar antes el pedido por el report `0xA0`, y eso es justo lo que la
herramienta no manda —a propósito: es un `SET_REPORT`—. La consecuencia es de
orden: **por cable no hay respaldo hasta la captura**, porque el único
camino para leer pasa por mandar el pedido, y el pedido se manda recién cuando
la captura lo muestre en el cable byte a byte.

Dos arreglos que salieron de mirar el resultado:

- **El json se guardó con `"features": {}`**, que no distingue "no contestó"
  de "no se pidió", y sin decir en qué máquina. La herramienta ahora guarda el
  error de cada report y el `hostname`; el json de esta corrida se completó a
  mano con la salida de la terminal, y lo dice en su `nota`.
- **La VM `JSJUANPC1W` tiene el cable en su definición**, pedido por el
  usuario, con `startupPolicy='optional'` para que siga arrancando sin el
  cable enchufado. El dongle quedó también: con el cable puesto el mouse no
  habla por radio, así que no debería aparecer en la página.

## Las capturas del cable: la Etapa 2 pasa, y el rate es el otro nibble

El usuario pasó el cable a la VM y corrió las seis capturas de
`captura-kvm.md`, sección 6 —abrir, rate 500 y 1000, LOD 2 y 1, macros—
**con el soft nativo**. Los comandos que le armé decían `--cable web`, y así
salieron los archivos y así las leí yo, hasta que él lo aclaró: "cuando entré
a la VM abrí el soft nomás". Ahora se llaman `cable-soft-*`. Las notas
quedaron en "nose", así que cada `.txt` tiene una línea `analisis:` con lo que
muestra el bus, marcada como tal.

### La etiqueta la puso el comando

Vale anotarlo porque el bus lo decía y no lo miré: el bloque de botones que se
escribió lleva la rueda en `0a, 09`, que es el orden del **soft** —la página
escribe `09, 0a` y deja el scroll invertido—, y el lector de capturas lo
imprimía en cada línea ("rueda como el soft nativo"). El byte de rate `0x73`,
con los dos nibbles distintos, tampoco es de la web, que por el dongle los
escribe iguales.

Lo que se cayó con la corrección fue todo lo que suponía **al helper en el
bus**: "el helper le pasa 56 a hidapi y en el cable va 52", "el helper no
reintenta, así que reintenta algo debajo de él". El helper nunca estuvo en
estas capturas. Lo que quedó es más fuerte que antes en otro sentido: los
pedidos que transcribí del helper los mandó, byte a byte, un programa que no
comparte código con él.

### Lo que confirmaron

- **El pedido de lectura es el del binario**: `a0 06 09 00 01 …`, `a0 04 38 …`
  y `a0 05 0f …` salen idénticos a `build_cable_read_request()`, y el
  `GET(0xA0)` vuelve `a0 01`. Con la primera lectura de la noche —ocho
  timeouts sin el pedido— queda claro para qué está.
- **El `SET_REPORT` lleva el largo que declara el mouse**: 52 para el dpi, no
  los 56 del bloque del dongle. Era la pregunta que el binario no contestaba,
  y es `build_cable_write_report()` tal cual.
- **La Etapa 2 pasa**: desde lo que devolvió el mouse, nuestros codificadores
  dan byte a byte el LOD a 2 mm y la vuelta, el nivel 1 del dpi a 500 y la
  vuelta, el costado-adelante a macro 17 y la vuelta, y el macro 17 en sus
  tres modos, rearmado de sus dos trozos de 64. Lo fija `test_etapa2_cable`,
  y se probó que el test se pone rojo si el report sale de 56 o si la tasa va
  al nibble equivocado.

### Lo que no se esperaba

**El rate por cable es el nibble bajo.** El soft leyó `0x74` y, para 500 Hz,
escribió `0x73`: el bajo de 4 a 3 y el alto quieto en 7, que es la tasa
inalámbrica de 8000. Nuestro codificador del dongle habría escrito `0x34`
—radio a 500, cable intacto—, o sea otra cosa que la pedida. Es la Etapa 2
haciendo su trabajo: `protocol.py` tenía anotado desde hace días "el nibble
bajo es INFERIDO: sería la tasa por cable", y ahora está visto escribir. Hay
un codificador aparte, `escribir_report_rate_por_cable()`. Lo que falta es el
efecto: `medir-polling.py` por cable después de escribirlo.

**El mouse a veces rechaza un `SET_REPORT` con STALL.** Seis de diecinueve,
y los seis se repitieron idénticos ~205 ms después y pasaron. Quién
reintenta —el soft, Windows o QEMU— no se sabe; el canal nuestro va a tener
que hacer lo mismo. El lector de capturas contaba
esos STALL como problemas; ahora distingue el rechazo reintentado y aceptado
del rechazo que nadie repitió.

Y un falso "checksum mal" del lector: leía cada trozo del macro como si fuera
el bloque. Ahora los junta, y el bloque rearmado es el de 111 de siempre.

### Lo que el soft no leyó, y cómo quedó el mouse

**Por cable, el soft lee solo rate, dpi y luz al abrirse**, y no escribe
nada. Botones, macro, perfil completo y versión no aparecen en ninguna
captura, así que sus pedidos siguen solo LEÍDOS del helper, y el del macro ni
eso. Yo había recomendado "capturar al soft abriendo por cable" como la salida
limpia, y el agente A la repitió: **era la captura que ya teníamos**. El usuario
eligió usar los pedidos LEÍDOS, que la regla del proyecto permite.

Lo que el soft leyó al abrir —dpi 1300/2400/3400/5600/8100/40000 en `Pu()`,
ripple y snapping OFF, hibernación 13 min, respuesta 4— lo tomé por un estado
pisado. **Es la configuración del usuario**, y pasa a ser el estado base de
`AGENTS.md`. De las capturas quedó solo el macro 17 en modo 2, que no tiene
botón asignado.

## El canal por cable: la misma cara que el dongle, otro protocolo adentro

El usuario preguntó si hacía falta tanto trámite: "¿no son iguales o similares
a las órdenes por el dongle?". Lo son. **El bloque es el mismo**, byte a
byte —eso es lo que dijo la Etapa 2—, y lo único distinto es el sobre: Feature
Reports en vez del Output Report 4, un pedido `0xA0` antes de cada lectura,
el largo del descriptor en cada escritura, y el STALL que se repite. Así que el
canal nuevo, `driver/src/asbridge/cable.py`, tiene los mismos `leer` y
`escribir` que `Device`, y la sesión, la Etapa 3 y la ventana siguen siendo
las mismas.

Lo que sí pide el camino, y está dicho en un solo lugar de la sesión
(`via_de`, `a_leer_de`, `lee_macros`):

- **la tasa es el otro nibble.** Por cable, leer el alto daba 8000 Hz, y la
  sesión habría "prestado la tasa" escribiendo la de la radio para poder leer
  un mouse que por cable nunca pasa de 1000. Ahora el nibble lo elige el
  camino, y la mutación solo dice cuántos Hz;
- **el macro se queda afuera.** Su pedido de lectura por cable no se conoce, y
  sin relectura no hay Etapa 3: por cable ni se lee ni se escribe, y la
  sesión corta antes de leer nada con un motivo propio, `macro-por-cable`. El
  "no contestó" que habría salido solo mandaba a buscar un problema de enlace;
- **los pedidos de versión, botones y perfil completo son LEÍDOS del helper.**
  El soft no los mandó nunca en el bus. El usuario eligió usarlos; si el mouse
  no los atiende, el respaldo sale incompleto y la baranda de siempre no deja
  escribir;
- **por cable se relee todo.** La relectura barata —el bloque escrito y el
  perfil de testigo— se apoya en algo medido por el dongle. Por cable no hace
  falta: no hay radio que pierda pedidos;
- **si están los dos, manda el cable**, porque con el cable puesto el dongle
  se calla. La ventana se cambia de camino sola cuando se enchufa o se saca el
  cable. El CLI y el puente siguen solo por el dongle, y `find_config_hidraw()`
  se niega a darles el nodo del cable: sería mandarle Output Reports del dongle
  a un endpoint que espera Feature Reports.

`test_el_cable_no_tiene_camino_todavia` decía "cuando la Etapa 2 del cable
esté hecha, este test se pone rojo con el primer uso, a propósito: es el
momento de revisarlo, no de borrarlo". Se puso rojo, y se revisó: lo que
cuidaba —que nada le hablara al cable sin respaldo— pasó a ser que **le hable
uno solo**, `cable.py` (`test_el_cable_solo_pasa_por_su_canal`).

`test_canal_por_cable` corre el canal y la sesión contra un mouse de Feature
Reports de mentira, y compara lo que sale con lo que mandó el soft en el bus.
Se comprobó que se pone rojo en cinco casos: la tasa al nibble del dongle, el
STALL sin repetir, el report de 56 en vez de 52, el macro sin cortar y la
solo lectura que escribe. El de la ventana se puso rojo con la lógica vieja
del bus, que avisaba "por el dongle no contesta" aun con el cable abierto.

**Nada de esto corrió contra el mouse todavía.** Lo que sigue es del usuario:
un respaldo por cable, y el LOD de ida y vuelta desde la ventana
(`SIGUIENTE-SESION.md`, paso 4).

### Lo primero contra el mouse

El usuario corrió el respaldo por cable y la tasa desde la ventana:

- **los seis bloques contestaron**, incluidos los tres cuyo pedido solo
  estaba LEÍDO del helper. Versión y botones salen byte a byte iguales que por
  el dongle; el perfil completo trae sus 126 bytes aunque el descriptor del
  cable declare 8, igual que el dpi devuelve 56 declarando 52;
- **la tasa por cable es el nibble bajo, ahora por fuera del protocolo**: la
  ventana escribió `06 09 01 73 8c …` —el mismo `SET` del soft— y
  `medir-polling.py` dio 2000 µs de mediana. Era lo único del cable que
  seguía siendo "la lectura razonable".

Lo que no corrió todavía es la Etapa 3 entera de un campo por cable —con su
relectura completa y su veredicto—, porque la tasa va por otro camino. Es el
LOD de ida y vuelta.

Y apareció una diferencia que no se explica sola: la luz del respaldo dice
hibernación 12 y respuesta 8, y la del soft al abrir la noche anterior, 13 y
4. No hubo escrituras nuestras por cable en el medio. Antes de tocar el
estado base se le pregunta al usuario de dónde salió.

### El LOD no entró, y la tasa sí

La segunda corrida: el LOD a 2 mm y la respuesta a 4 desde la ventana, por
cable. Las dos escrituras salieron bien armadas —el LOD, byte a byte el `SET`
del soft— y el mouse las aceptó sin STALL. La relectura completa las mostró
sin cambiar, y la ventana volvió sola a 1 mm y a 8.

La diferencia con la tasa, que sí entró, estaba en el código y no en el
mouse: `poner_tasa` relee **1 s después** de escribir, y `aplicar` relee
**enseguida**. Mirando los tiempos de las seis capturas, el soft nunca le
manda nada al mouse antes de ~200 ms de haber escrito, y no relee nunca
después de escribir; el helper hace `Sleep(500)`. Eso estaba LEÍDO y anotado
en `protocol.py` desde el principio, y al escribir el canal copié los tiempos
de la **lectura**, que estaban medidos, y me salteé el de la escritura, que
solo estaba leído.

La misma corrida dejó otra pista: al abrir, un `GET(6)` devolvió el bloque de
la **versión**. El mouse parece tener un solo buffer para todos los reports, y
el "listo" del pedido `0xA0` puede ser el del pedido anterior. La baranda del
canal —el bloque tiene que ser del comando pedido— lo atajó y la segunda
pasada lo leyó bien; ahora el canal lo vuelve a pedir en el momento.

Con eso, la lectura razonable es que un pedido que llega a los milisegundos
pisa la escritura antes de que el mouse la aplique. Es INFERIDO. El canal ahora
respira 500 ms después de escribir y ~120 ms entre pedidos, como el soft, y lo
que lo confirma es volver a correr el LOD.

Y la luz quedó aclarada a medias: la hibernación en 12 es del usuario, y la
respuesta la quiere en 4. Quién la puso en 8, no se sabe.

### Con el respiro, entra

Tercera corrida, con los 500 ms después de escribir: el LOD a 2 mm se quedó
después de la relectura completa, y la vuelta a 1 mm también. Es la primera
Etapa 3 entera por cable, y la misma escritura que en la corrida anterior no
se veía: lo único que cambió fue la espera. Queda medida la causa; el
mecanismo —el buffer compartido— sigue inferido.

La respuesta no se escribió en esta corrida, así que el mouse la sigue
teniendo en 8. Y quedó a la vista un hueco que por el dongle no existía: por
cable no se escucha el Report ID 3, así que la ventana no se entera si el
nivel de dpi cambia con el botón. Hay que releer a mano.

### El botón de dpi, por cable

El usuario lo confirmó: puso el nivel 2 con el botón y la ventana lo mostró
recién al releer. Antes de proponer un sondeo en segundo plano, se miró el
descriptor del cable en sysfs —sin tocar el mouse— y **declara un Input
Report 3 de 4 bytes** en la Usage Page de notificaciones de la interfaz 2: el
mismo número y largo que el aviso del dongle. Nadie lo escuchaba por cable.
Ahora el canal lo escucha, como `HidrawChannel`; si el mouse no lo manda, no
se pierde nada y el sondeo sigue siendo la salida.

### Los botones por cable, y la ventana que miraba la tasa de la radio

El usuario reasignó el clic derecho por cable y lo devolvió: tres escrituras
de cmd 8, cada una releída, y el bloque ajeno del rate al abrir se volvió a
pedir solo, que es el arreglo de la corrida anterior funcionando.

Al revisar lo que faltaba apareció un bug de la misma familia que el de la
tasa prestada: **varios lugares de la ventana leían el estado sin el camino**
y por cable veían 8000 Hz, la tasa de la radio. "Volver a como estaba"
anotaba 8000 y habría intentado escribirla por cable —el codificador del cable
la rechaza, así que la escritura fallaba—, y el diagnóstico de una lectura
incompleta decía "bajá la tasa a 1000" con el mouse ya en 1000. Se arregló en
la raíz: el estado leído por cable dice `"via": "cable"`, y `campos_de` y
`tasa_de` lo toman cuando nadie les pasa el camino. El test nuevo se puso rojo
con la versión anterior.

Y los mensajes de "mové el mouse" dejaron de explicar la radio: por el dongle
dicen "movelo mientras tanto: así lee más rápido", y por cable no piden nada,
porque no hay nada que mover. El test del cartel dependía del bus de la
máquina —con el mouse de verdad enchufado por cable veía el otro texto— y
ahora fija el suyo.

### Lo que faltaba, corrido

El usuario corrió lo que quedaba y contestó lo abierto:

- **el botón de dpi por cable avisa**: con la ventana abierta, apareció el
  aviso con el nivel. El Report ID 3 que declara el descriptor del cable
  llega. Como por cable releer el dpi tarda un segundo, ahora se relee solo al
  llegar el aviso, y el aviso se va cuando el estado trae el nivel nuevo —no
  con cualquier estado: uno con el nivel viejo no lo tapa—. Por el dongle,
  donde releer cuesta minutos, sigue pidiendo que relean;
- **la respuesta a 4 se quedó**: la luz se escribe por cable;
- **los tres interruptores, ida y vuelta**. Lo lindo de esta corrida es que
  el log solo alcanza para verificarla: cada escritura se arma desde la
  relectura de la anterior, así que en sus bytes se ve que la anterior entró;
- **el botón de modo no le gana al cable**: con el cable en la PC, manda el
  USB aunque el botón diga 2.4 GHz;
- sobre los macros dijo "para mí funcionan con dongle y con cable"; queda
  por aclarar si es que se ejecutan con el cable puesto o que se escriben.

El bloque ajeno volvió a aparecer —los botones devolvieron el dpi— y el canal
lo volvió a pedir solo.

### El macro por cable: el mismo bloque, y el id que faltaba

El usuario aclaró lo de los macros con una regla: **lo que por cable viaja
byte a byte igual que por el dongle hereda lo medido del dongle**. Para el
macro vale: el bloque de 111 es el que ya se escribe y se verifica por el
dongle, y los dos trozos de 64 son los que mandó el soft por cable.

Lo que no alcanzaba con eso era **leerlo**: sin el macro leído no hay de dónde
partir para cambiarle el modo, ni cómo verificar la escritura. El pedido
estaba en el helper con un byte sin seguir —`[ebx+0x8]`, en `0x40fbcb`—. Se
extrajo el helper del instalador que estaba en `~/Descargas` y se siguió: la
misma función tiene los dos caminos, y por el dongle pone esa variable en el
byte 5 de la trama de lectura, donde está medido que va el id del macro. Por
cable la pone en el byte 4 del pedido `0xA0`, donde los demás llevan el
perfil. `a0 09 83 00 <id> 00 00 00`: LEÍDO.

Con eso el canal lee el macro con su id y lo escribe en dos trozos, y si un
trozo no entra, manda la secuencia entera de nuevo, como por el dongle. La
pestaña de macros por cable deja de salir vacía. Falta que el mouse conteste
ese pedido: es el primero del macro que se le manda por cable.

### El macro contestó, y la ventana se cayó

El primer pedido del macro por cable —el que salió de seguir `[ebx+0x8]`— lo
contestó el mouse: el 17, en modo 2, con sus diez eventos. Pero la ventana se
cayó al mostrarlo, por dos cosas que no eran del cable:

- **por cable el bloque viene de 131**: `sizeTotalData` 0x83, que es lo que
  pide el helper, con los 111 bytes del dongle adentro —el checksum interno
  en su lugar, al revés como por el dongle— y 20 ceros detrás. El
  decodificador buscaba el checksum al final y decía "CHECKSUM INTERNO MAL".
  El canal ahora lo presenta como el de 111, **solo si lo que sobra es
  cero**, con la misma regla que ya tenía para no cortar datos al escribir;
- **el panel de macros no sabía mostrar un macro sin contador**. El
  decodificador devuelve `repeticiones=None` en los modos 1 y 2 a propósito
  —ahí el byte no es un contador— y el panel hacía `max(None, 1)`. Nunca se
  había leído un macro en modo 2 con la ventana: el 17 quedó así por las
  capturas del soft. El test nuevo reproduce el mismo `TypeError`.

Con eso arreglado, el usuario grabó el macro 17 por cable desde la ventana: los
dos trozos salieron byte a byte los del soft para el modo 2, y el mouse los
aceptó. Lo que se grabó era lo mismo que el macro ya tenía, así que la
relectura no puede decir si la escritura entró: queda medido el camino, no el
efecto. El usuario lo dio por cerrado.


## Una relectura podrida se reescribió sola, y el cmd 5 quedó roto

Corriendo por cable las escrituras que faltaban —dpi por nivel, nivel en uso,
reposo, hibernación y rueda— el dpi, el nivel y la rueda salieron bien, ida y
vuelta. La luz no: **el mouse quedó con cuatro campos que nadie pidió.**

El log tiene las tres escrituras de reposo, y la tercera es la que rompió:

```
escribiendo reposo: 05 0f 01 00 03 c8 00 ff 00 02 02 01 ce   (0.5 -> 1 min)
escribiendo reposo: 05 0f 01 00 03 c8 00 ff 00 02 02 01 ce   (la misma, repetida)
escribiendo reposo: 05 0f 01 74 8b 00 00 00 00 01 00 01 00   (la vuelta a 0.5)
```

La relectura de después devuelve **exactamente esos bytes**, así que el mouse
los guardó:

| | antes | después |
| --- | --- | --- |
| reposo | 0.5 min | 0.5 min ✅ |
| hibernación | 12 min | **128 min** |
| respuesta | 4 | **0** |
| modo / velocidad | 0 / 3 | **7 / 139** |
| color | `#00ff00` | `#000000` |

**El campo que se pidió entró bien.** Los otros cinco viajan en los mismos 13
bytes, y ahí está todo: `escribir_reposo_ligero()` toca `closeTime`, recalcula
el checksum y **copia el resto del bloque que leyó**. Esa vez leyó basura.

Reproducido con el decodificador del propio proyecto, sin el mouse:

```
escribir_reposo_ligero(01748b00000000010001000000, minutos=0.5)
  -> 01 74 8b 00 00 00 00 01 00 01 00 00 00      los bytes del log, clavados
```

**Por qué no lo agarró nada.** Tres redes fallaron a la vez:

- el checksum se recalcula **después** de meter la basura, así que el bloque
  sale internamente válido (es la suma de los índices 1 a 8: da `cd` para el
  bloque bueno y `00` para el podrido, y los dos cierran);
- por cable `checksum_ok` está fijo en `True` (`cable.py`), porque el que hay
  en el dongle es el del envoltorio y por cable no hay envoltorio;
- **el chequeo de rango ya existía** —`parametros_de_luz()["en_rango"]`, el
  `[!] FUERA DE RANGO` que imprime un respaldo— pero corría al **mostrar**, no
  antes de escribir.

Y el remate: `sesion.aplicar()` devolvió **`ok=True`**. La ventana mostró
verde mientras escribía basura. Es exactamente el reproche que este proyecto
le hace al cliente oficial —leer un bloque y reescribirlo cambiado—, y esta
vez fue nuestro.

Poco antes, en la hibernación, el log trae `iluminacion: volvió el bloque de
0x06, lo pido de nuevo (1/3)`: el buffer único del cable, ya conocido. Que la
lectura mala venga de ahí es **INFERIDO** —`_frame()` rechaza un report cuyo
byte 0 no sea el comando, así que no es el mismo caso— y queda abierto de
dónde salieron esos bytes.

### La baranda que faltaba, y por qué mira la salida

`estructuras.fuera_de_rango(cmd, datos)`, consultada en `sesion.aplicar()`
entre el paso 3 y el paso 4: un bloque con valores que el mouse no puede tener
no sale al bus.

**Juzga lo que se va a escribir, no lo que se leyó**, y la diferencia importa:
si mirara la lectura, un mouse que ya quedó mal no se podría arreglar —cada
campo suelto arrastra los otros y todas las escrituras quedarían rechazadas—.
Mirando la salida, un bloque bueno entero entra aunque el mouse esté podrido,
que es justo lo que hace falta para restaurarlo. Cubre además al codificador,
no solo a la lectura.

Solo sabe de cmd 5, y **lo dice**: `CMDS_CON_RANGO`. Inventarle rangos a cmd 4
o cmd 8 sin una captura que mueva esos campos sería lo de siempre —amplificar
una inferencia—, y un `None` que significara "está bien" sin tener con qué
juzgarlo es peor que no chequear.

`test_no_se_escribe_un_bloque_imposible` (`salvaguardas.py`) es una regresión
con los bytes de verdad, y verificado que se pone rojo sin la guarda: sin ella
el caso da `ok=True` y escribe.

### Y la herramienta que faltaba: volver atrás

Había `respaldar.py` y no había con qué volver. `driver/scripts/restaurar-bloque.py`
escribe un bloque entero desde un respaldo, por la Etapa 3, por dongle o por
cable. No acepta bytes tipeados —salen de un respaldo y de ningún otro lado—,
pasa el bloque por la misma baranda antes de mandarlo (un respaldo tomado
después del problema se rechaza solo), y **solo hace cmd 4 y cmd 5**: en cmd 8
y cmd 9 el formato de lectura no es el de escritura, y la tasa va por
`cambiar-rate.py`.

### Una cosa medida, de yapa

**Por cable el LED es morado fijo y no sigue el color del nivel de dpi**
(MEDIDO, el usuario). Por el dongle el color del LED es el testigo
independiente del nivel en uso; **por cable no sirve**, y ahí la verificación
es la relectura o el botón de ciclo de dpi.

### De dónde salieron los bytes: el canal por cable corrompe lecturas (MEDIDO)

La entrada de arriba dejó abierto de dónde venía el bloque podrido, y lo daba
por INFERIDO. **Se cerró, y con un testigo que no admite discusión: el bloque
de versión de firmware.**

En el diff entre los dos respaldos del incidente aparece esto:

```
version de firmware: 080083010100 -> 08740b010100
```

**La versión de firmware no se puede escribir.** No hay comando que la toque,
no la escribió nadie, y no puede cambiar. Que dos lecturas del mismo mouse den
valores distintos prueba que **una de las dos lecturas vino mal**, y no hay
ninguna otra explicación disponible.

Contra los 125 respaldos versionados que tienen el bloque: **124 dicen
`080083010100`** y uno solo dice otra cosa —`cable-despues-de-A.json`, el del
incidente—.

Y las dos corrupciones tienen **la misma firma**, en los mismos dos bytes:

```
cmd 11 (versión)      XOR  00 74 88 00 00 00
cmd  5 (iluminación)  XOR  00 74 88 c8 00 ff 00 00 02 00 cd 00 00
                               ^^ ^^
```

Byte 1 y byte 2, idénticos en los dos bloques. No es ruido de radio —por cable
no hay radio— ni el buffer ajeno que ya conocíamos: ahí el byte 0 trae el
comando de otro y `_frame()` lo rechaza. Acá el byte 0 está bien y el bloque
pasa entero.

**Lo que esto cambia:**

- la baranda de rango es necesaria pero **no alcanza**. Agarró este caso
  porque la basura cayó fuera de rango; una corrupción que caiga adentro pasa
  igual;
- **el bloque de versión es un canario gratis.** Es constante por definición,
  se lee en todo respaldo completo, y comparar dos lecturas suyas dentro de una
  misma sesión no cuesta nada y no depende de hardcodear el valor de ningún
  modelo;
- queda por saber **qué** mete esos dos bytes, y la explicación fácil ya se
  descartó. El candidato natural era el Input Report 3 —el canal por cable
  empezó a escucharlo dos días antes, y es el único código nuevo en ese
  camino—, pero **no cierra**: una notificación es `[deviceId, tipo, x, y]`
  con el tipo en 0x40, 0x41 o 0x10, y acá el byte 1 es 0x74 en los dos
  bloques. Si fuera el aviso pisando el buffer, el byte 2 tendría que ser el
  mismo en los dos, y no lo es (`8b` contra `0b`).

Lo único que los dos casos sostienen es que el byte 2 quedó XOR 0x88, y el
byte 1 pasó de 0x00 a 0x74 —que con los dos valores buenos en cero no
distingue un XOR de una sobreescritura—. **Con dos muestras eso es una
regularidad, no una regla**: hace falta una tercera corrupción para decir algo.
Lo que sí se puede hacer sin esperarla es **detectarla**, con el canario de
arriba.

### Era el buffer de cmd 6, y el checksum interno ya lo detectaba

El agente A, mirando los mismos respaldos, encontró lo que faltaba, y se verificó:
**los bytes que se filtran son el payload entero de cmd 6.**

```
cmd 6 (report rate)     01 74 8b 00 00 00 00
cmd 5 podrido           01 74 8b 00 00 00 00 | 01 00 01 00 00 00
cmd 5, otra lectura     01 74 8b 00 00 00 00 | 00 00 00 00 00 00
```

Los primeros siete bytes son cmd 6 clavado, y lo que sigue es relleno —o, en
el bloque del incidente, los cuatro bytes que nuestro codificador puso encima—.
El "XOR 0x88" de la entrada anterior era un artefacto de mirar solo dos bytes:
queda corregido.

**Lo que no cierra es el bloque de versión.** Cmd 6 es `01 74 8b 00 00 00`; la
versión corrupta es `08 74 0b 01 01 00`, con el byte 2 en `0b` y no en `8b`, y
los bytes 3 a 5 con sus valores buenos. No es el mismo sangrado, y queda
abierto.

**Y el detector estaba a la vista desde el principio: el checksum interno.**

```
cmd 5, checksum interno      guardado / calculado
  respaldo sano               0x01cd / 0x01cd   cierra
  el del incidente            0x0100 / 0x0100   cierra  <- lo recalculó nuestro codificador
  el sangrado, tal como llega 0x0000 / 0x00ff   NO CIERRA
```

La línea del medio es la que explica por qué esto pasó desapercibido: el
checksum sirve **en la lectura**, antes de que un codificador lo toque.
Después de recalcularlo ya no detecta nada.

Cruzado contra los 125 respaldos versionados: en cmd 4, 5 y 8 el checksum
interno cierra en **375 de 375** bloques, y falla en el único que se sabe
corrompido. Cero falsos positivos sobre toda la evidencia que hay.

**Las dos barandas que entraron, y por qué son dos:**

| | cmd 4 | cmd 5 | cmd 8 | cmd 9 | cmd 6 / 10 / 11 |
| --- | --- | --- | --- | --- | --- |
| checksum interno | sí | sí | sí | invertido | no tienen |
| canario | — | — | — | — | cmd 11 |

- `Cable._por_que_no_sirve()` rechaza el bloque leído si el byte 0 trae otro
  comando **o si el checksum interno no cierra**, lo vuelve a pedir hasta tres
  veces y, si insiste, **devuelve None en vez del bloque**: mejor que la Etapa
  3 corte por "no contestó" a que un codificador reciba datos de otro bloque.
  Cmd 9 queda afuera a propósito —su checksum vuelve invertido y su largo es
  variable—;
- `sesion.juzgar()` gana el veredicto **`lectura-corrompida`**: si cambió un
  bloque de `CMDS_INMUTABLES` —hoy la versión de firmware, que no tiene
  comando de escritura— una de las dos lecturas vino mal y no hay nada que
  comparar. Va **antes** que la rama idempotente. Cmd 11 no tiene checksum
  interno, así que es la única forma de detectarlo.

El canario no es una hipótesis: cuando esto pasó de verdad, el veredicto fue
`cambio-de-mas` —que manda a buscar qué otra cosa se escribió, y no se había
escrito nada—. Con el canario apagado, el test nuevo reproduce ese mismo
`cambio-de-mas`.

**Lo que esto le saca a la baranda de rango**: deja de ser el detector y pasa a
ser el respaldo. El checksum es genérico y cubre los tres bloques
estructurados; el rango solo sabe de cmd 5, y ahora eso ya no es el hueco que
parecía.

### El perfil completo, de testigo a testigo cruzado

Quedaba un agujero: **cmd 10 no tiene checksum interno** y es el testigo de
toda escritura por el camino de la relectura acotada. Una lectura suya
sangrada no la notaba nadie, y el veredicto del paso 6 se habría armado sobre
bytes de otro bloque.

Lo que lo cubre ya estaba en `evidencia.md` desde el primer respaldo por
cable —"lo que embebe coincide con los bloques leídos en la misma corrida"—
pero se miraba, no se cruzaba. Ahora se cruza. Los offsets salieron de los
**126 respaldos versionados** que tienen los cinco bloques:

| | en el perfil | en el bloque | largo | coincide |
| --- | --- | --- | --- | --- |
| cmd 6 rate | 1 | 1 | 2 | 126/126 |
| cmd 4 dpi | 3 | 1 | 47 | 126/126 |
| cmd 5 luz | 53 | 1 | 8 | 125/126 |
| cmd 8 botones | 62 | 0 | 55 | 126/126 |

El único que discrepa es `cable-restaurado.json`, la lectura sangrada. Y cada
tramo toma entre 3 y 14 valores distintos entre respaldos, así que la
coincidencia no es de bytes fijos: `test_el_perfil_embebe_donde_dice` exige
las dos cosas.

**Una trampa que casi entra en la tabla**: la primera versión ponía cmd 6 en
`perfil[14:18] == bloque[3:7]`, que es lo que encuentra un buscador de
subcadena más larga. Son cuatro ceros. Coincidían siempre y no verificaban
nada. Por eso el test exige que el tramo **se mueva**.

**Y de paso confirmó que el mouse nunca estuvo roto**: en
`cable-restaurado.json` el perfil trae la luz buena —`00 03 c8 00 ff 00 01
02`— y el bloque suelto trae el sangrado. Las dos copias estaban ahí desde el
principio; lo que faltaba era compararlas.

### Dos defectos que la baranda destapó al entrar

Ninguno de los dos se buscaba, y los dos eran reales:

- **`_escribir_tasa()` dejaba el caché contradiciéndose.** Es el camino de un
  solo comando, y refrescaba el bloque de rate **sin el perfil**. Como el
  mouse mueve el perfil con la tasa (MEDIDO, 2/2 en los respaldos), el caché
  quedaba con la tasa nueva y, adentro del perfil, la vieja. Era el único
  camino de escritura que no releía el perfil: `aplicar()` ya lo hacía. Ahora
  `_refrescar()` se lleva el perfil cuando el bloque es uno de los que embebe;
- **el mouse de mentira de los tests tenía un perfil de relleno** —125 ceros
  por cable, tres bytes por el dongle— así que no embebía nada. Pasaban
  pruebas sobre un mouse que no existe. Ahora los dos lo rehacen desde sus
  bloques, y después de cada escritura, que es lo que hace el de verdad.

Y el test de evidencia `el perfil acompaña a todo cambio` se puso rojo solo:
comparando `cable-restaurado.json` con su vecino decía "cambió la luz y el
perfil no acompañó", que es justo el agujero que esa prueba busca y ahí era
falso. Ahora descarta los respaldos que se contradicen y **dice cuáles**: un
respaldo con una lectura sangrada no es evidencia de nada.

### Cada cuánto sangra el canal por cable (MEDIDO)

Dos corridas de `medir-sangrado.py`, 240 pedidos cada una, solo lectura:

| | pedidos | rechazados | |
| --- | --- | --- | --- |
| sin pausa | 240 | 6 | 2.5% |
| con 0.5 s entre tandas | 240 | 3 | 1.2% |

**Lo que dice, y lo que no:**

- **el sangrado es frecuente**: entre 1 y 2.5% de los pedidos devuelven otro
  bloque. No es una rareza;
- **los reintentos lo tapan entero**: ningún bloque se perdió después de
  reintentar, en 480 pedidos. Con ~2% por intento, tres intentos fallan una vez
  cada cien mil, así que `PEDIDOS_POR_BLOQUE_AJENO = 3` sobra;
- **los nueve los agarró el filtro del byte 0**, el que ya existía. La variante
  silenciosa —byte 0 bien, contenido de otro bloque, que es la que rompió el
  cmd 5— **no apareció ni una vez en 480 pedidos**. Por la regla de tres, eso
  la acota por debajo de ~0.6% con 95% de confianza, y nada más: no se midió su
  frecuencia, se midió que es más rara que la visible;
- **la pausa NO se puede decir que ayude.** 6 contra 3 con n=240 tiene
  intervalos que se pisan de sobra. Parece menos y no alcanza para afirmarlo;
- el canario de versión no vio nada en 80 lecturas del bloque de versión.

**Decisión: no se tocan los tiempos del canal.** La medición se pidió para
decidir eso con datos, y los datos dicen que no hace falta: los reintentos
funcionan, no se pierde nada, y cambiar unos tiempos elegidos a ojo por otros
elegidos a ojo sobre una diferencia de 6 contra 3 sería la corazonada que la
medición venía a evitar.

**Y una hipótesis que la herramienta no podía ni plantear.** Al mirar los
nueve se veía tentador decir "siempre vuelve el bloque del pedido anterior",
pero el medidor contaba **qué volvió** y no **de qué pedido**, y con eso
cualquier bloque que vuelva es "el anterior" de alguno: la afirmación no era
falsable. Ahora el canal guarda el par —`pidiendo X: volvió el bloque de Y`— y
`medir-sangrado.py` compara contra el orden fijo de pedidos y dice si encaja o
si rompe. Queda para la próxima corrida.

### El sangrado es siempre el bloque anterior (MEDIDO), y eso cierra el hueco

La corrida con el medidor arreglado —el que guarda **de qué pedido** vino lo
que volvió— contesta la hipótesis:

```
  6 bloque(s) rechazado(s) (2.5% de los pedidos):
      3  pidiendo perfil completo:      volvio el bloque de 0x0b (version)
      2  pidiendo version de firmware:  volvio el bloque de 0x06 (rate)
      1  pidiendo report rate:          volvio el bloque de 0x08 (botones)

  de los que dicen que volvio: 6 son el bloque del pedido ANTERIOR y 0 no.
```

Seis de seis. Con el orden de pedidos fijo, cada uno es exactamente el
anterior. **El mouse sirve lo último que tenía cuando todavía no armó lo
nuevo.**

Y encaja con el incidente: en `A_LEER`, **cmd 6 se lee justo antes de cmd 5**,
así que el payload de cmd 6 que apareció dentro del bloque de luz era el
bloque anterior. Las dos variantes —con el byte 0 ajeno y con el byte 0 bien—
son el mismo fenómeno; lo único que cambia es si el id viene con el payload.

**Lo que eso permite: un detector que no necesita checksum.** El canal recuerda
lo último que sirvió y lo reconoce si vuelve, truncado o con ceros según cuánto
se pida —las dos formas salen del mismo mecanismo: el buffer tiene el bloque
anterior y un `GET` de N bytes devuelve N bytes de ese buffer—. Es **lo único
que cubre a cmd 6, 10 y 11**, que no tienen checksum interno y hasta ahora se
quedaban sin red.

Verificado contra los 146 respaldos, comparando **todos** los pares de bloques
distintos: los únicos casos donde un bloque parece otro son los dos respaldos
del incidente, y ahí es consecuencia del sangrado, no un falso positivo. En los
144 sanos, ninguno. El piso de cuatro bytes en común está puesto porque todos
los bloques de configuración arrancan con el mismo `profileId`.

Con esto los cuatro filtros cubren los siete comandos:

| | cmd 4 | cmd 5 | cmd 6 | cmd 8 | cmd 9 | cmd 10 | cmd 11 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| byte 0 ajeno | sí | sí | sí | sí | sí | sí | sí |
| checksum interno | sí | sí | — | sí | — | — | — |
| bloque anterior | sí | sí | sí | sí | sí | sí | sí |
| cruce con el perfil | sí | sí | sí | sí | — | sí | — |

### El reposo y la hibernación por cable, limpios (MEDIDO)

Son los dos campos que se habían corrompido, y los únicos de la luz que
quedaban sin Etapa 3 por cable. Corridos de nuevo, ahora con los cuatro
filtros puestos, ida y vuelta cada uno:

```
escribiendo hibernacion: 05 0f 01 00 03 18 00 ff 00 01 02 01 1d   (12 -> 1)
escribiendo hibernacion: 05 0f 01 00 03 c8 00 ff 00 01 02 01 cd   (1 -> 12)
escribiendo reposo:      05 0f 01 00 03 c8 00 ff 00 02 02 01 ce   (0.5 -> 1)
escribiendo reposo:      05 0f 01 00 03 c8 00 ff 00 01 02 01 cd   (1 -> 0.5)
```

Los cuatro bloques bien formados, cada uno armado desde una relectura sana
—se ve en los bytes: el de reposo lleva la hibernación en `c8`, que es la que
la escritura anterior dejó—. El respaldo de después no tiene **ninguna
diferencia** contra el de antes.

Ninguna baranda saltó: ni bloque imposible, ni lectura que se contradiga. Es
la corrida que la vez pasada terminó con el cmd 5 roto.

**Por cable la hibernación no se puede verificar a simple vista**, y no se
pidió: el mouse está alimentado, así que los temporizadores de reposo no
disparan y `medir-hibernacion.py` no diría nada. Por este camino el testigo es
la relectura; el físico es del dongle.

### Una séptima confirmación del bloque anterior, de regalo

Al abrir la ventana apareció esto:

```
version de firmware: volvio el bloque de 0x06, lo pido de nuevo (1/3)
```

Parecía un contraejemplo: en `A_LEER` la versión va **primera** y el rate
segundo, así que el rate sería el *siguiente*, no el anterior. Pero
`Configuracion.preparar()` lee la tasa **antes** de que `leer_estado`
empiece, para decidir si hay que bajarla. La secuencia real fue rate → versión,
y lo que volvió fue el rate: **el bloque anterior**, otra vez.

Vale como recordatorio de método: "el anterior" es el anterior en el bus, no
en la lista que uno está mirando.

### Dos agujeros que aparecieron al cerrar lo que quedaba de A

El dpi por nivel, el nivel en uso y la rueda corrieron bien por cable, ida y
vuelta, con los cuatro filtros puestos. Los dos problemas fueron otros.

**1. El sangrado conserva el byte 0, y el filtro comparaba desde el 0.**

El respaldo previo salió con el bloque de rate sangrado:

```
pedido cmd 6, volvio :  01 00 83 01 01 00 00
el bloque anterior   :  08 00 83 01 01 00        (la version)
byte 0               :  01 vs 08   <- difieren
desde el byte 1      :  00 83 01 01 00  ==  00 83 01 01 00
```

O sea: **el byte 0 del bloque pedido se conserva y el resto viene del
anterior**. `_es_el_bloque_anterior()` comparaba desde el byte 0 y ese caso se
le escapaba entero, porque el rate empieza con `01` (su `profileId`) y la
versión con `08`. Ahora compara **desde el byte 1**, y no afloja nada: ese
byte es el mismo `profileId` en casi todos los bloques, así que nunca sirvió
para distinguir. Cero falsos positivos en los 147 respaldos sanos, y detecta
los tres que se saben corrompidos.

Y el incidente original encaja en la misma forma: cmd 5 y cmd 6 tienen los dos
`profileId` 01, así que "conservó el byte 0" y "copió todo" eran
indistinguibles ahí. Una sola regla cubre los dos.

**2. `respaldar.py` guardaba un respaldo corrompido en silencio.**

Ese respaldo quedó como línea de base, y el diff contra el siguiente dijo:

```
report rate: 01008301010000 -> 01748b00000000
```

**La tasa no se había tocado.** Lo que había cambiado era que la primera
lectura vino mal. `sesion.incoherencias()` lo detecta —el perfil dice `74 8b` y
el bloque suelto `00 83`— pero `respaldar.py` no la corría. Ahora la corre al
guardar **y antes de un `--comparar`**: un diff contra un respaldo sangrado
inventa cambios que nadie hizo, que es la peor clase de alarma falsa que este
proyecto puede dar.

### Y un control de la ventana que hacía más de lo que decía

La vuelta del macro 17 al modo 2 se deshizo sola:

```
escribiendo macro_modo:          09 40 11 00 02 ...   <- modo 2, la vuelta
escribiendo macro_repeticiones:  09 40 11 00 00 ...   <- lo devolvio a 0
```

Escribir el contador **implica el modo 0**, porque ese byte solo es un contador
ahí —está documentado en `sesion.preparar_mutacion` y el CLI lo pide explícito
con `--modo 0 --repeticiones N`—. Pero en la ventana eso quedaba detrás de un
botón que dice "Aplicar" al lado de "Repeticiones", sin decir que mueve el
modo. Es exactamente el reproche que este proyecto le hace al cliente oficial.

El control ya se deshabilitaba fuera del modo 0; ahora además **se niega a
escribir** si el macro no está en modo 0, y dice por qué. La diferencia importa
porque quien lo habilita es una relectura, y una relectura puede venir vieja.

**Lo que sí quedó MEDIDO**: el macro por cable se escribe de verdad. El modo
pasó de 2 a 0 y la relectura lo devolvió cambiado, que es lo que la corrida
anterior no había podido mostrar —había escrito el mismo contenido que ya
tenía—. La mutación real de cmd 9 por cable está.

### Configurar por cable: cerrado

Con el macro 17 devuelto al modo 2, el respaldo contra la línea de base dice
**sin diferencias** y no trae ningún aviso de incoherencia. Por cable ya
corrieron, todos con Etapa 3 y con los cuatro filtros puestos:

la tasa, el LOD, los botones, la respuesta, los tres interruptores del sensor,
el dpi de cada nivel, el nivel en uso, la rueda, el reposo, la hibernación, y
la **mutación real del macro**.

El usuario confirmó que apretó "Aplicar" cada vez que cambió el modo, así que
el modo que volvía a 0 queda explicado del todo: era ese botón, y no hay una
segunda ruta que buscar.

### La detección de bus, contra el bus de verdad (MEDIDO)

`conexiones.py` estaba probado en sintético y nunca contra el hardware. Las
tres situaciones, con la ventana abierta y sin leer el mouse:

```
INFO  asbridge.hidraw: abierto /dev/hidraw2 (lectura/escritura)
WARNING asbridge.hidraw: el dispositivo desaparecio: [Errno 5] E/S     <- dongle fuera
INFO  asbridge.hidraw: abierto /dev/hidraw2 (lectura/escritura)        <- otro puerto, sola
INFO  asbridge.cable:  abierto /dev/hidraw7, por cable                 <- prioriza el cable
```

- **desenchufar el dongle**: la ventana se entera y lo dice;
- **cambiarlo de puerto en caliente**: se reconecta sola, sin reiniciar;
- **enchufar el cable con el dongle puesto**: pasa al cable.

El usuario confirmó que **en las tres el mouse quedó bien reconocido** en
pantalla —el chip de la barra con su camino y su puerto—. El log muestra la
reapertura; que el puerto mostrado fuera el nuevo es su observación, que es el
testigo que corresponde: la ventana es lo que se está probando.

Con esto la lista B queda cerrada.

### Un macro de tres eventos SÍ corre: la paridad no era la regla (MEDIDO)

La pregunta abierta era por qué un macro de **un** evento no se reproduce y
uno de dos sí. La hipótesis a mano era la paridad: los impares no corren.

Se escribió el macro 17 con tres eventos —`a:dir0@10, a:dir1@10, a:dir1@10`,
elegido así **a propósito**: termina con todo suelto, y el propio aviso de
`modelo.advertencias_de()` confirma que no deja nada apretado antes de
escribirlo—, se le asignó el botón del costado-adelante, y con el foco en un
editor:

```
aaaaaaaaaaaaaaaaaaaaaaaaaaa    <- mientras se mantiene apretado el boton
```

**Corre.** Tres eventos, número impar, y se reproduce sin problema, en modo 2
(repite mientras se mantiene). Así que **la paridad no es la regla** y el
misterio del macro de un solo evento sigue abierto, pero ahora se sabe que no
es eso.

Todo volvió al estado base en la misma tanda: el botón a "adelante" y el macro
a sus diez eventos. **El comando de vuelta se verificó antes de correrlo**,
sin tocar el mouse: el texto de los diez eventos reencodea al bloque exacto que
el mouse tenía, byte por byte.

Dos cosas de método que quedaron a la vista:

- `respaldar.py` **no baja la tasa sola**, y a 8000 Hz el respaldo no completa
  —el macro no llegó, y el propio mensaje del script dijo qué hacer—. Bajar a
  1000 una vez para toda la tanda es mejor que dejar que cada
  `primera-escritura.py` baje y suba: seis reconfiguraciones de radio contra
  una;
- la tasa se devolvió **al final**, después de todas las escrituras. Subirla en
  el medio deja a las que siguen sin poder releer, que es el paso 1 de la
  Etapa 3.

### Y el cartel de la tasa prestada tiene un segundo camino

Lo pidió el usuario en la misma sesión: el cartel ofrecía **una sola** salida
—"devolver la tasa ahora"— así que quien se sienta a configurar a 1000 Hz y
quiere **quedarse** ahí tenía que dejar que la sesión le devolviera los 8000 y
bajarlos de nuevo con `cambiar-rate.py`. Dos reconfiguraciones de radio para
terminar donde ya estaba.

Ahora hay un botón **"Quedarme en 1000 Hz"** al lado. Lo que hace es cancelar
la deuda: **no le escribe nada al mouse**, porque el mouse ya está a esa tasa,
y mandar una trama para poner la que ya está sería reconfigurar la radio de
gusto. Apaga también el reloj de gracia, que si no la devolvería solo a los
90 s y desharía lo que se acaba de elegir.

No es el botón primario, a propósito: lo que la sesión promete es devolverla, y
eso tiene que seguir siendo lo que salta a la vista.

### El modo 1 no hace lo que dice su nombre (MEDIDO)

El bundle lo llama `StopOnAnyKey`, "cualquier tecla para detener", y así estaba
el nombre en `MACRO_MODOS`. Con el macro de tres eventos asignado a un botón,
cuatro corridas, las cuatro iguales:

- se dispara al apretar y **sigue después de soltar**, indefinidamente;
- **una tecla del teclado NO lo detiene**: se escribe esa tecla y el macro
  sigue saliendo entremedio;
- **lo detiene apretar cualquier otro botón del mouse**.

Así que el nombre del fabricante describe algo que el firmware no hace. El
mostrado pasa a ser **"otro botón del mouse lo detiene"**, y el suyo queda
donde corresponde: en el comentario de `MACRO_MODOS`, como evidencia de lo que
dice el bundle, no de lo que hace el mouse.

Con esto **los tres modos están verificados apretando el botón**, que es lo que
faltaba: `modelo.MODO_SIN_MEDIR` queda en `None` y el aviso de "este modo
todavía no se probó" no sale nunca. El camino se deja armado, porque vuelve a
hacer falta en cuanto aparezca un modelo con el cuarto modo que el bundle lista
(`StopOnCurrentKey`) y el X8 Pro no tiene.

Es la lección de siempre, otra vez: **los nombres del fabricante no son
evidencia de lo que hace el firmware.** Ya había pasado con `LightBrightness` y
`breathingSpeed`, que parecían dos parámetros y son los nibbles de un
temporizador.

### La primera instalación de verdad, y estaba rota

Nunca se había corrido `install.sh` en serio: `--solo-probar` salía limpio y
con eso alcanzaba. La primera instalación real murió a la mitad:

```
Instalando la regla de udev
install: no se puede efectuar `stat' sobre '.../driver/udev/70-attackshark-x8pro.rules'
```

Al mover lo del X8 Pro a su carpeta por modelo, la regla quedó en
`driver/attackshark-x8pro/udev/` y el instalador tenía **dos** caminos hacia
ella: el de copiarla al prefijo, que se actualizó, y el de instalarla en
`/etc/udev/rules.d`, que no.

**Y el ensayo no podía agarrarlo**, que es lo peor del asunto: la línea rota
estaba adentro del `if` de instalar en serio, así que `--solo-probar` nunca la
tocaba. Un ensayo que no puede fallar por un archivo que no está da confianza
falsa, y eso es exactamente lo que dio.

Quedó arreglado por partida triple:

- el camino, en una sola variable (`ORIGEN_REGLA`) en vez de escrito dos veces;
- **la comprobación de que todo lo que se copia existe corre antes de copiar
  nada y también en `--solo-probar`**, así que ahora el ensayo sí puede fallar;
- `test_el_instalador_apunta_a_archivos_que_existen` saca las rutas del script
  y comprueba que existan, sin correr nada. Verificado poniendo el camino viejo
  de nuevo: se pone rojo con el mensaje exacto.

La instalación fallida dejó `/opt/asbridge` a medias —el programa copiado, sin
regla ni lanzadores—; volver a correr el instalador lo completa.

### La instalación, de punta a punta

```
Instalando la regla de udev
  instalada y aplicada
Dejando los lanzadores
  asbridge-gui y asbridge en /usr/local/bin
Listo.
```

Y la desinstalación: saca `/opt/asbridge`, los dos lanzadores, la entrada del
menú, el icono y la regla de udev, y deja lo que guardó el usuario en
`~/.config/asbridge/`. Las dos completaron.

**Lo que no se vio**: `asbridge-gui` corriendo **desde la instalación**. Los
lanzadores se crearon y se borraron, pero entre una cosa y la otra no se abrió
la ventana desde `/opt`, así que que el `venv` y los imports funcionen desde
ahí sigue sin verificarse. Es lo único de esta prueba que quedó abierto, y se
cierra instalando y abriendo la ventana una vez.


## Cada modelo, dentro de `models/`, y dos auditorías más

### La mudanza, y cuatro rutas que ya estaban rotas

`dev/attackshark-x8pro/` pasó a `dev/models/attackshark-x8pro/`, y lo mismo en
`driver/`. Lo pidió el usuario: con una carpeta por mouse colgando de cada lado,
cada modelo nuevo agregaba un directorio a la raíz de `dev/` y de `driver/`.

Al ajustar las rutas aparecieron cuatro que **ya estaban mal**, ninguna por
esta mudanza:

- `capturar-vm.sh` guardaba en `dev/docs/capturas-w`, que desde la mudanza
  anterior no es donde están las capturas. El `mkdir -p` lo tapaba: la próxima
  captura habría quedado lejos de las demás, sin aviso.
- **el botón "Aplicar: pkexec" de la ventana no aparecía nunca.** La ventana
  resuelve el comando contra la carpeta del driver, y el comando nombra
  `driver/scripts/...`: buscaba `driver/driver/scripts/instalar-udev.sh`. Viene
  de la separación entre `driver/` y `dev/`.
- instalado, ese mismo script buscaba la regla en
  `/opt/asbridge/attackshark-x8pro/udev/` e `install.sh` la dejaba en
  `/opt/asbridge/udev/`. Ahora `install.sh` copia `models/` con la forma del
  repo, y el script la encuentra en los dos lados.
- cuatro enlaces a `metodo.md` que apuntaban adentro de la carpeta del modelo.

Las tres primeras tienen prueba, verificada poniendo cada ruta rota de nuevo:
las tres se ponen rojas. Es la lección de "La primera instalación de verdad,
y estaba rota" otra vez: **un camino que se resuelve en dos lugares se
actualiza en uno**.

### Las auditorías del agente A (v3.0) y del agente B, contra el código

**Cierto, y el proyecto no lo tenía al día** —arreglado—:

- `AGENTS.md` decía dos corridas de `medir-sangrado.py` y 480 pedidos; fueron
  **tres, y 720** (la tercera es la del medidor que guarda de qué pedido vino
  cada bloque). Lo traía el agente A.
- `evidencia.md`: la fila "a 8000 Hz el canal no es utilizable, ni siquiera
  para leer" decía más de lo que su evidencia sostiene —pasan las escrituras y
  los tres comandos cortos— y la sección de límites mandaba a Windows para
  bajar la tasa, que desde "Las cuatro tasas funcionan desde Linux" no hace
  falta. Lo marcó el agente B.
- `evidencia.md`, punto 7 de INFERIDO: cerrado en el texto pero sin la marca
  que llevan los cerrados. Lo marcó el agente B. Y el **punto 17**, mismo tipo de
  desfase y que no marcó ninguna, seguía pidiendo la prueba del macro de tres
  eventos, que ya se había corrido; `SIGUIENTE-SESION.md` también.
- `dev/README.md` contaba 139 respaldos; hoy son 154. Ahora no da número.
- Que el soft nativo no le habilita el diálogo de colores de nivel a este
  mouse: el agente A lo dice y ya estaba comprobado. Nada que arreglar.

**Ya resuelto**: el N-04 del agente B —el mensaje de `--mode full` sin comandos
ofrecía luz y botones, que el CLI no acepta—. `cli.py` lo valida antes que el
backend desde la pasada anterior. **Casi se reabre**: en la primera lectura se
miró solo el mensaje de `backend.py` y se lo dio por abierto. El mensaje existe
en dos capas a propósito, y hay que mirar la que ve quien corre el comando.

**Falso, y no se aplica**:

- El agente A, G2-02: "espaciar a 500 ms reduce los reintentos a cero". La medición
  dio 6 contra 3 en 240 pedidos, dentro del ruido, y por eso **no se tocan los
  tiempos** ("Cada cuánto sangra el canal por cable"). Es el hallazgo que más
  daño haría aplicado.
- El agente A: los estados del dongle, cambiados —`0xC0` "ocupado", `0xC2` "payload
  corrupto", `0xC3` "NAK de radio"—. Son aceptado, sin respuesta y ocupado
  (`device.py`).
- El agente A: las cuatro barandas con `fuera_de_rango()` en lugar de
  `_es_el_bloque_anterior()`, que es la única que cubre cmd 6, 10 y 11.
- El agente A: que la pausa después de escribir "evita pisar la memoria no volátil
  durante el flasheo". Es el `Sleep(500)` del helper, y el mecanismo sigue
  INFERIDO (punto 20 de `evidencia.md`).
- El agente A, G2-03: que ante una lectura corrompida la ventana solo dice "error
  de relectura". Muestra el veredicto entero.
- El agente A: los números —65 y 30 pruebas (son 89 y 57), 13 capturas (19), 32
  campos (23), la tabla de líneas por archivo, `preferencias.json` (es
  `interfaz.json`) y un test con otro nombre—.
- El agente B cita `AUDITORIA.md` y "el informe vivo", que se retiraron hace rato.

**Aceptado sin hacer**: G2-01 —rangos para cmd 4 y 8 en `fuera_de_rango()`—
es a propósito y `CMDS_CON_RANGO` lo dice; además cmd 4 y 8 tienen checksum
interno en la lectura, que es lo que cierra el caso del incidente. G2-04
—Flatpak o AppImage— es una opinión de empaquetado, no un hallazgo.

Con esto contestado, los dos informes se borraron del repositorio.

## La nota de retomar, archivada entera

`SIGUIENTE-SESION.md` había crecido hasta 75 KB y casi todo era historia:
secciones tachadas como HECHO, planes ya cumplidos y el porqué de cada
decisión de la interfaz. Como es lo primero que se lee al retomar, cada sesión
pagaba esa historia entera. Se reescribió corta —solo el estado y lo que
queda— y lo que tenía va acá, **tal cual estaba**, con los encabezados bajados
un nivel. Parte de eso (las lecciones, la decisión del SVG, la auditoría de la
ventana) no estaba en ninguna otra entrada.

**Dos cosas ya estaban desactualizadas al archivarla**, y se dejan como
estaban porque las entradas no se editan:

- "Cómo quedó el mouse" daba hibernación 10, respuesta 8 y ripple y snapping
  ON. El estado base vigente es el de `AGENTS.md` (§5).
- "Lo técnico, cerrado" pedía correr la instalación y la desinstalación de
  verdad. Se corrieron: ver "La instalación, de punta a punta". Lo único que
  quedó abierto de eso es abrir la ventana desde `/opt`.

### Lo primero al retomar: el sangrado del canal por cable

El 2026-09-20 se descubrió que **el canal por cable devuelve, a veces, el
buffer de otro bloque con el byte 0 bien puesto**. Pedido cmd 5, volvió el
payload entero de cmd 6 relleno con ceros; pasó el único filtro que había, un
codificador le cambió su byte y le **recalculó el checksum**, y salió al
mouse. El cmd 5 quedó con hibernación 128 min y respuesta 0, y `aplicar()`
devolvió `ok=True`. Está entero en [`bitacora.md`](bitacora.md).

**El mouse quedó restaurado** (`cable-relectura.json`, sin diferencias contra
el estado base) y entraron tres barandas —el checksum interno en la lectura,
el canario de la versión y el cruce del perfil— más la composición de
mutaciones y `restaurar-bloque.py`. Todo eso es código y está hecho.

**La medición se hizo, y cerró el tema.** Tres corridas de 240 pedidos:
el sangrado es del 1 al 2.5% de los pedidos, los reintentos lo tapan entero
—ningún bloque perdido en 720 pedidos— y **de los seis atribuidos, los seis
eran el bloque del pedido anterior**. De ahí salió el cuarto filtro, que es el
único que cubre cmd 6, 10 y 11. **Los tiempos del canal no se tocan**: con ~2%
por intento, tres intentos fallan una vez cada cien mil, y la diferencia entre
correr con pausa y sin pausa (3 contra 6) está dentro del ruido.

La herramienta queda, por si hace falta volver a medirla:

```bash
dev/herramientas/medir-sangrado.py --vueltas 40
#   - solo lee; no hace falta mover el mouse, pero conviene no usarlo
#   - el mouse tiene que estar por CABLE
dev/herramientas/medir-sangrado.py --vueltas 40 --pausa 0.5
#   - la misma, espaciada: dice si el sangrado depende de qué tan seguido
#     se pide, que es lo que decidiría tocar los tiempos del canal
```

**Y una que quedó abierta sin poder cerrarse**: la corrupción del bloque de
**versión** (`08 00 83 01 01 00` → `08 74 0b 01 01 00`) **no** es el sangrado
de cmd 6 —los bytes 3 a 5 conservaron sus valores buenos y el byte 2 es `0b`,
no `8b`—. Hay una sola muestra, así que no hay con qué cerrarlo. El canario la
detecta, que es lo que importa; si `medir-sangrado.py` la hace aparecer otra
vez, ahí habrá con qué.

---

### Contra el hardware no queda nada pendiente

**Las cinco corridas que este documento pedía están hechas.** Lo que sigue
abajo se deja como el porqué de cada una, tachado donde corresponde.

**La sesión de configuración.** En la corrida en que se midió el
botón de modo, el log de `./asbridge-gui` muestra **siete escrituras seguidas**
—tres de `nivel_activo`, dos de `ripple`, dos de `boton_modo`—, las siete con
su `0xC1`, con **una sola** bajada de tasa al abrir y **una sola** devolución al
cerrar. Son los puntos 1 y 3 de la lista de abajo.

**Las tres que faltaban**, corridas y confirmadas:

1. **la Etapa 3 del clic izquierdo reasignable** —el intercambio del 1 con el
   2, la vuelta, y la baranda que no deja sacar el último clic izquierdo—, que
   es la primera escritura del slot 1 que sale de este proyecto;
2. **la tasa se cambia desde la aplicación y se queda** (el punto 2);
3. **la ráfaga de "volver a como estaba"** no trabó el puntero (el punto 4).

De esas tres **no quedaron salidas ni diffs registrados**: lo que está MEDIDO
es que salieron. Está anotado así en [`evidencia.md`](evidencia.md) y en la
bitácora, para que nadie lo lea como si el asistente hubiera
visto los bytes.

---

### Configurar el mouse por cable: qué falta, en orden

**El usuario lo pidió**, y ahora se sabe cómo lo hace el cliente oficial —está
**LEÍDO** del helper, `protocolo.md`, "El canal por CABLE"— pero no está medido.
Lo que se sabe hoy:

- por cable el mouse es **otro dispositivo USB** (`1d57:2126`) y su canal de
  configuración son Feature Reports en la Usage Page 0x0B, con ids que son los
  mismos números que los comandos del dongle (LEÍDO del descriptor,
  [`hardware.md`](hardware.md));
- **la web sí configura por cable, a través de su helper** (LEÍDO: lo que
  después se capturó por cable fue el soft nativo, no la web). Esto corrige lo
  que decía este documento ("el cliente web no habla por cable", porque el
  bundle no usa `sendFeatureReport`): la página no le habla a ningún HID, y el
  helper tiene el camino entero —enumera el cable como `connectionMethod`
  0x80, y la página acepta al X8 Pro por esa ruta—;
- **el report es el mismo bloque del dongle sin el envoltorio**: `[cmd,
  sizeTotalData, perfil, campos…, checksum interno]`, sin el `04 L 00` ni el
  checksum de afuera. Leer es un `SET_FEATURE` de pedido por el report `0xA0`
  y después un `GET_FEATURE` del bloque; escribir, un `SET_FEATURE` del
  bloque;
- y **los largos que declara el cable son el bloque sin el relleno del
  final** —dpi 52 en vez de 56, luz 13 en vez de 15—: lo que queda afuera es
  cero en los 120 bloques de dpi y los 121 de luz de los respaldos (MEDIDO
  sobre los respaldos, `test_el_cable_mide_el_bloque_sin_relleno`). Los
  "cuatro de nueve que miden distinto" eran eso, en dpi y luz; el perfil
  completo y el 0x0c siguen sin cerrar.

Los pasos, y ninguno se puede saltear:

**1. ~~Leer lo que el mouse devuelve sin pedírselo~~ — hecho, y no contesta
(MEDIDO).** `leer-por-cable.py` pidió en frío los ocho reports que lee el
helper y **los ocho dieron timeout**: 41 s, los 5 s del timeout de control de
`usbhid` cada uno, sin que el mouse contestara la etapa de datos (no fue un
STALL). Está en `dev/models/attackshark-x8pro/respaldos/cable-primera-lectura.json`. Lo razonable es
que falte el pedido por el report `0xA0`, que el helper manda siempre antes;
pero mandarlo es un `SET_REPORT`, y por eso primero va la captura, que lo
muestra en el cable. **O sea que por cable no hay respaldo hasta el paso 2.**

**2. ~~Capturar al cliente oficial configurando por cable~~ — hecho, y la
Etapa 2 pasa (MEDIDO).** Seis capturas (`capturas-w/cable-soft-*.pcap`):
abrir, rate 500 y 1000, LOD 2 y 1, macros. **Son del soft nativo, no de la
web**: se llamaron `cable-web-*` porque así decía el comando que armó el
asistente, y el usuario abrió el soft. Lo que dijeron está en `protocolo.md`,
"Lo que dijo la captura", y en `test_etapa2_cable`:

- el pedido `0xA0` es el de `build_cable_read_request()` y cada `SET_REPORT`
  lleva el largo que declara el mouse, que es `build_cable_write_report()`;
- desde lo que devolvió el mouse, **nuestros codificadores dan byte a byte lo
  que escribió el soft**: LOD, nivel de dpi, botón, macro en sus tres modos;
- **el rate por cable es el nibble bajo**, no el alto: hay un codificador
  aparte (`escribir_report_rate_por_cable`), porque el del dongle habría
  movido la tasa inalámbrica;
- el mouse a veces rechaza un `SET_REPORT` con STALL y el mismo `SET`,
  repetido ~205 ms después, pasa. El canal tiene que reintentar así.

**Lo que el soft no leyó por cable**: botones, macro, perfil completo,
versión y 0x0c. **Al abrirse lee solo rate, dpi y luz, y no escribe nada**
(`cable-soft-abrir`), así que capturarlo abriendo ya no tiene nada que dar.
Esos pedidos de lectura siguen solo LEÍDOS del helper, y el del macro ni eso
(su byte 4 no se siguió).

**Y cómo quedó el mouse**: como el usuario lo tenía, salvo el **macro 17 en
modo 2**, que no tiene botón asignado. Lo que el soft leyó al abrir —dpi
1300/2400/3400/5600/8100/40000 en `Pu()`, ripple y snapping OFF, hibernación
13 min, respuesta 4— **es la configuración que el usuario eligió**, no algo
que haya pisado un cliente: ahora es el estado base de `AGENTS.md`. Todo lo
demás que se escribió en las capturas volvió a donde estaba.

**3. ~~El código~~ — hecho (2026-09-18), sin correr contra el mouse.**
`driver/src/asbridge/cable.py`, con la misma interfaz que `Device` para que
la sesión y la ventana no se enteren del camino:

- `leer(cmd)`: el pedido `0xA0`, el `GET(0xA0)` hasta `a0 01`, y el
  `GET(cmd)` con el largo del helper, con los tiempos del soft en el bus
  (~320 y ~110 ms); los datos arrancan en el byte 2, como `Frame.data`, y se
  exige el bloque entero;
- `escribir(bloque)`: un `SET_REPORT` con `build_cable_write_report()` y el
  largo del descriptor, reintentando **el mismo** `SET` si vuelve con `EPIPE`;
- ~~el macro ni se lee ni se escribe por cable~~ — así salió el canal, y
  cambió el mismo día: el macro se lee con su id y se escribe en dos trozos
  (ver más abajo). La baranda quedó genérica: un camino que no lea el macro
  no lo escribe (`macro-sin-relectura`);
- sin acuse `0xC1`: lo que dice que el mouse aplicó es la relectura, que por
  cable es **completa**;
- la tasa por cable es el nibble bajo, y la sesión **no presta la tasa**.

Lo prueban `test_canal_por_cable` (contra un mouse de Feature Reports de
mentira, byte a byte contra `cable-soft-*.pcap`, y se pone rojo si la tasa va
al nibble del dongle, si no se repite el STALL, si el report sale de 56, si
el macro pasa o si la solo lectura escribe) y `test_la_ventana_abre_el_cable`.

**4. Correrlo contra el mouse — a medias (2026-09-18).**

- ~~el respaldo por cable~~: **los seis bloques contestaron**, incluidos los
  tres pedidos LEÍDOS del helper (`dev/models/attackshark-x8pro/respaldos/cable-primer-respaldo.json`);
- ~~la tasa a 500 y de vuelta~~: el `SET` salió byte a byte el del soft, y
  `medir-polling.py` dio 500 Hz. MEDIDO;
- **el LOD a 2 mm y la respuesta a 4 no se vieron en la relectura.** Las dos
  escrituras salieron como tenían que salir —el LOD, byte a byte el `SET` del
  soft— y el mouse las aceptó, pero la relectura completa las mostró sin
  cambiar y la ventana volvió a 1 mm y a 8. Lo que distingue a la tasa, que sí
  entró: `poner_tasa` relee **1 s después** de escribir, y `aplicar` relee
  **enseguida**. El helper hace `Sleep(500)` después de cada escritura (LEÍDO)
  y el soft nunca manda nada antes de ~200 ms (MEDIDO en las seis capturas),
  y yo no lo había copiado. La lectura razonable —INFERIDA— es que el pedido
  de relectura, llegando a los milisegundos, pisa la escritura antes de que el
  mouse la aplique: ya se vio que el mouse tiene un solo buffer, porque un
  `GET(6)` devolvió el bloque de la versión. **Arreglado en el canal**: 500
  ms después de cada escritura, ~120 entre pedidos como el soft, y el bloque
  de otro comando se vuelve a pedir. **Corrido y confirmado (2026-09-18)**:
  con el respiro, el LOD a 2 mm se quedó y la vuelta a 1 mm también, cada
  uno con su relectura completa. Es la primera Etapa 3 entera por cable;
- ~~los botones~~: el clic derecho a otra función y de vuelta, desde la
  ventana (MEDIDO, 2026-09-18);
- ~~la respuesta~~: a 4, y se quedó. Es la primera escritura de la luz por
  cable, que no tiene captura del soft (MEDIDO);
- ~~los interruptores~~: ripple, snapping y motion sync, encendidos y
  apagados. Cada escritura sale armada desde la relectura de la anterior, y
  en los bytes del log se ve que la anterior había entrado (MEDIDO);
- ~~sin correr por cable: el dpi de cada nivel, el nivel en uso, el reposo, la
  hibernación y la rueda~~ **corridos** (2026-09-20), ida y vuelta cada uno,
  con los cuatro filtros del sangrado puestos y sin una sola diferencia contra
  la línea de base;
- **"Volver a como estaba" y el diagnóstico de una lectura incompleta** leían
  la tasa de la radio por cable (8000 Hz): el primero habría intentado
  escribirla, y el segundo decía "bajá la tasa". Arreglado haciendo que el
  estado diga su camino (`"via"`), que `modelo.campos_de` y `sesion.tasa_de`
  toman cuando nadie se lo pasa;
- **la luz**: el usuario quiere hibernación **12** y respuesta **4**
  (2026-09-18). El mouse tiene la respuesta en **8**, y no se sabe quién la
  puso: el soft había leído 4 la noche anterior. En la corrida del LOD la
  respuesta no se escribió (no está en el log), así que sigue en 8. Ponerla
  en 4 por cable es también la primera escritura de la luz por ese camino;
- **por cable la ventana no se enteraba sola** del botón de dpi (MEDIDO: el
  nivel 2 apareció recién con "Leer el mouse"). **El descriptor del cable
  declara el mismo Input Report 3** que usa el dongle para ese aviso —4
  bytes, Usage Page 0x0A de la interfaz 2, LEÍDO de sysfs— y no lo escuchaba
  nadie. Ahora el canal lo escucha. **Falta ver si el mouse lo manda por
  cable**: con la ventana abierta por cable, apretar el botón de dpi. Si el
  nivel cambia solo, es MEDIDO; si no, la salida es releer el bloque de dpi
  cada pocos segundos, que por cable es barato. **Probado: llega** —la
  ventana mostró el aviso con el nivel—, y ahora por cable el dpi se relee
  solo al recibirlo y el aviso se va cuando llega el nivel nuevo;
- **el macro por cable, armado (2026-09-18), sin correr.** El usuario lo
  planteó así: "hay que considerar como medido lo que funciona en el dongle
  si es que es lo mismo que se transmite por cable. Los bytes". El bloque que
  se escribe es el mismo del dongle, verificado ahí, y va en los dos trozos
  que el soft mandó por cable. Lo que faltaba era **leerlo**, para partir de
  algo y para releer: se siguió `[ebx+8]` en el helper y es el id del macro,
  la misma variable que el camino del dongle pone donde va el id
  (`protocolo.md`, "Leer"). Pedido: `a0 09 83 00 <id> 00 00 00`, LEÍDO. Con
  eso el macro por cable tiene su Etapa 3 entera. **Y el mouse lo contesta**
  (MEDIDO, `cable-macro-17.json`): el 17 en modo 2 con sus diez eventos. Por
  cable el bloque viene de 131 —el de 111 más 20 ceros—, y el canal lo
  presenta como el de 111. **Escribirlo**: el mouse aceptó los dos trozos
  —los del soft para el modo 2—, pero lo escrito era lo que ya tenía, así
  que la relectura no distingue si entró. El usuario lo dio por cerrado
  (2026-09-18). ~~Un cambio real de macro por cable queda sin correr~~
  **corrido** (2026-09-20): el modo del 17 pasó de 2 a 0 y la relectura lo
  devolvió cambiado;

Para el macro, con el mouse por cable:

```bash
driver/scripts/respaldar.py --macro-id 17 -o dev/models/attackshark-x8pro/respaldos/cable-macro-17.json
#   - la linea "macro 17" tiene que traer su bloque: es el primer pedido del
#     macro por cable, y esta LEIDO, no visto en el bus
driver/asbridge-gui
#   - pestaña Macros: el 17 tiene que aparecer (esta en modo 2)
#   - cambiarle el modo a 0 y de vuelta a 2: cada cambio se relee
```

Los comandos, para lo que falta, con el mouse enchufado por cable y el dongle
puesto o no (da igual: manda el cable):

```bash
driver/scripts/respaldar.py -o dev/models/attackshark-x8pro/respaldos/cable-primer-respaldo.json
#   - rate, dpi y luz tienen que contestar: son los pedidos vistos en el bus
#   - version, botones y perfil completo son los LEIDOS del helper: si alguno
#     no contesta, lo dice, y por cable no se escribe hasta mirarlo
driver/asbridge-gui
#   - el chip de arriba: "Cable USB · puerto 1-4"
#   - Releer, y despues UN cambio de ida y vuelta: el LOD a 2 mm y a 1 mm
#     (es el primero que el soft escribio por cable, y el que tiene su
#     SET_REPORT byte a byte en test_etapa2_cable)
#   - y la respuesta a 4, que es la preferencia del usuario
#   - despues la tasa a 500 Hz y medir: driver/scripts/medir-polling.py tiene
#     que dar ~2000 us por cable; y de vuelta a 1000
```

La tasa es la única de las dos que se verifica por fuera del protocolo: que el
mouse aplique el nibble bajo como su tasa por cable es la lectura razonable, y
`medir-polling.py` la cierra.

**La decisión del respaldo, tomada (2026-09-18)**: el método pide los siete
comandos y los macros, y por cable, con pedidos vistos en el bus, se leen
tres (rate, dpi, luz). La salida del soft ya se probó y no da más, así que el
usuario eligió **aceptar para botones, perfil, versión y 0x0c los pedidos
LEÍDOS del helper**, que la regla de `AGENTS.md` permite ("levantadas
literalmente del binario del helper"). Un pedido así que el mouse no conteste
no rompe nada: no hay respuesta y el respaldo queda incompleto. **El macro,
por cable, no se lee** hasta ver su pedido, y por eso por cable no se escribe.

Lo que ya está hecho de este pedido: **por cable no se ofrecen tasas que el
cable no puede dar** (el dispositivo es Full Speed, `bInterval` 1 ms, así que
el techo son 1000 Hz). `modelo.campos_de(estado, perfil, via)` filtra las
opciones, y la ventana le pasa la vía que ve en el bus.

---

### Lo primero cuando el mouse vuelva a estar cerca

**Tres corridas cortas**, las tres contra el hardware, y ninguna bloquea nada.
Salieron de la sesión en que el mouse quedó cargando por cable con el dongle
puesto, con el mouse fuera de alcance.

**1. ¿Se puede sacar al mouse del modo cable sin tocarlo?** Con el cable
enchufado a la PC el mouse conmuta a USB y deja de hablar por el dongle
(MEDIDO). **No hay ningún comando de canal**: se buscó en el bundle y el
cliente oficial tampoco lo tiene (LEÍDO, `evidencia.md`). Lo que
queda por probar es si desconfigurar el dispositivo USB **sin cortarle la
corriente** lo devuelve a la radio:

```bash
driver/scripts/donde-esta-el-mouse.py            # el puerto del cable; acá salió 1-4
echo 0 | sudo tee /sys/bus/usb/devices/1-4/authorized
driver/scripts/sondear.py --escuchar 20          # ¿vuelven los latidos del Report ID 3?
#   - si vuelven: el mouse volvió a 2.4 GHz y **sigue cargando** (el puerto
#     sigue dando VBUS), que sería lo mejor de los dos lados
#   - si no vuelven en 20 s: no alcanza con desconfigurarlo
echo 1 | sudo tee /sys/bus/usb/devices/1-4/authorized   # deshacer, siempre
```

**CORRIDO, y salió que no**: 0 reports en 20 s, y además el mouse
**dejó de andar** —sin enumeración no hay camino por cable, y a la radio no
volvió—. Con `authorized=1` volvió a funcionar por cable. O sea que la
conmutación a modo USB no depende de la enumeración: alcanza con que el
conector tenga corriente y datos. Queda en `evidencia.md` como MEDIDO.

**2. ~~El botón de modo con el cable puesto~~ — contestado (2026-09-18).**
Con el cable enchufado a la PC **el mouse prioriza el USB aunque el botón de
modo esté en 2.4 GHz** (MEDIDO por el usuario). Con la PC como cargador no
hay forma de usar la radio.

**3. Que la ventana se entere de los cambios del bus.** Está probado entero
contra un bus de mentira, pero no contra el de verdad:

```bash
driver/asbridge-gui   # con el dongle puesto: el chip de arriba tiene que decir
                      # "Dongle 2.4 GHz · puerto 1-2"
#   - sacar el dongle: tiene que decir que el mouse se fue del bus
#   - ponerlo en OTRO puerto: tiene que reconocerlo solo, con el puerto nuevo,
#     y volver a abrirlo sin cerrar la ventana
#   - enchufar el mouse por cable con el dongle puesto: el cartel tiene que
#     avisar que por cable no contesta
```

---

### Y entonces, qué sigue

**Nada de lo que queda bloquea nada**, y ninguno es una corrida de hardware que
haya que hacer antes de seguir usando la aplicación.

1. **Lo que falta es captura, no código.** `dpi_ON_OFF_flag`, los ocho colores
   de indicador, `Dpi_indication_type` y `lightMode` son constantes en las 76
   escrituras capturadas: sin una captura que los mueva no hay Etapa 2, y
   escribirlos sería inventar bytes. Se consiguen moviendo esos controles en el
   soft nativo con usbmon corriendo (`captura-kvm.md`).
2. **Las corridas cortas de la tabla del final** —el modo 1 del macro, por qué
   un macro de un evento no corre, qué manda el byte de batería con la batería
   llena—. Son de minutos salvo la última, y las corre el usuario.
3. **Un segundo modelo.** El modelo ya no es de un solo mouse (punto 4 de la
   lista de la interfaz, hecho), así que agregar uno es llenar un
   `dispositivos.Perfil`. Pero **hace falta la captura de su driver oficial**:
   copiar el del X8 Pro y cambiarle el nombre es exactamente lo que
   `test_el_perfil_no_miente` se pone rojo para impedir.

---

### ~~Lo primero que hay que correr contra el hardware~~ HECHO

**Configurar con el mouse a 2k/4k/8k estaba roto de tres maneras distintas, y
las tres quedaron arregladas —pero contra mouses falsos.** El detalle está en
[`bitacora.md`](bitacora.md). Lo que falta es apretar el botón, y son tres
corridas cortas:

```bash
# 1. el caso reportado: con el mouse arriba, cambiar un parámetro desde la app
driver/scripts/cambiar-rate.py --valor 8000
./asbridge-gui
#    - "leer el mouse" tiene que traer los siete, no cinco
#    - el cartel tiene que decir "a 1000 Hz, prestado, vuelve a 8000"
#    - mover el dpi del nivel 1 y ver que entra, sin que la ventana se cuelgue
#    - cerrar la ventana
driver/scripts/medir-polling.py --segundos 10        # tiene que haber vuelto a 8000

# 2. que la tasa se pueda cambiar DESDE la app y se quede
./asbridge-gui                                 # poner la tasa en 4000 y cerrar
driver/scripts/medir-polling.py --segundos 10        # tiene que decir 4000, no 8000

# 3. que una ráfaga no deje el puntero trabado
./asbridge-gui        # con el mouse a 8000: cambiar cuatro campos seguidos
#    El riesgo que esto mide está MEDIDO: seis tramas de rate en
#    tres segundos dejaron el mouse sin mover el puntero. Ahora la ráfaga
#    entera cuesta **una** bajada y **una** devolución, así que no debería
#    pasar; si pasa, desacoplar el dongle y anotarlo.
```

**Mientras tanto el estado base sigue siendo 8000 Hz**, y ya no hace falta
bajarlo a mano para usar la aplicación: lo hace sola, lo dice, y lo devuelve.

#### 4. Y lo nuevo: la ráfaga de restaurar

La ventana tiene dos botones que escriben **muchos campos de una** —"volver a
como estaba" y "valores seguros"—. El mecanismo no es nuevo (son las mismas
escrituras de siempre, una por campo, y la sesión presta la tasa una sola vez),
pero **es la primera vez que algo dispara una ráfaga larga solo**, y el riesgo
que eso mide está MEDIDO:, seis tramas de rate en tres segundos
dejaron el mouse sin mover el puntero.

```bash
./asbridge-gui
#    - "leer el mouse"
#    - mover tres o cuatro campos a mano (dpi, LOD, ripple, la rueda)
#    - "volver a como estaba": el diálogo tiene que listar EXACTAMENTE esos
#      campos y ninguno más, y la tasa —si figura— tiene que ir última
#    - aplicar, moviendo el mouse mientras corre
#    - al terminar, la pantalla tiene que mostrar los valores de antes
driver/scripts/respaldar.py          # y el respaldo tiene que coincidir con el de antes
```

Si el puntero se traba, desacoplar el dongle y anotarlo: sería el mismo
problema y querría decir que la ráfaga necesita una pausa entre
escrituras.

**Y una que no se puede probar sin querer perder el estado base**: "valores
seguros" deja la tasa en 1000 Hz y el dpi del nivel 1 en 1200, así que después
hay que volver a dejar el mouse como dice `AGENTS.md`. No corre sola: el
diálogo pide confirmar y dice qué va a cambiar.

---

### ~~Lo primero que hay que correr: el clic izquierdo reasignado~~ HECHO

**El usuario lo pidió, está hecho y la Etapa 3 se cumplió**: el botón 1
se remapea, siempre que quede un clic izquierdo en los botones 1 a 5 (el 6 y el
7 no pueden llevarlo), y hay un botón que intercambia el 1 y el 2 en una sola
escritura. Sigue sin haber **Etapa 2**: ninguna captura del cliente oficial
muestra una escritura del slot 1, y eso no lo arregla ninguna corrida nuestra.

Lo de abajo es lo que se corrió, y queda como referencia:

```bash
./asbridge-gui
#   1. "Leer el mouse"
#   2. "Intercambiar" (fila abajo del botón derecho): el diálogo no pregunta,
#      escribe. Verificación externa: el botón IZQUIERDO físico tiene que abrir
#      el menú contextual y el DERECHO tiene que seleccionar.
#   3. "Intercambiar" otra vez: vuelve a como estaba. Probar los dos botones.
#   4. En el botón 1 elegir "Clic derecho": la ventana tiene que avisar que es
#      el único con clic izquierdo, y el mouse no tiene que cambiar.
driver/scripts/respaldar.py          # y el respaldo tiene que coincidir con el de antes
```

**Si el paso 2 deja el mouse sin clic**, no hace falta un clic para volver:
la ventana se maneja con Tab y Espacio, y desde una terminal
`driver/scripts/primera-escritura.py --comando botones --boton izquierdo --funcion
"clic izquierdo"` lo devuelve (con el derecho en clic izquierdo, la baranda lo
deja).

---

### El diagrama de botones: hecho

**Está hecho**: `driver/src/asbridge_ui/diagrama.py`, el orden físico de las filas y,
de yapa, el cambio de idioma (`driver/src/asbridge_ui/i18n.py`). Lo de abajo era el
plan y queda como el porqué de cada decisión; lo que se hizo, cómo se revisó y
qué quedó afuera está en la entrada de
[`bitacora.md`](bitacora.md). No hay nada que correr contra el mouse: el
esquema no agrega ninguna escritura.

**El idioma quedó completo esa misma noche**: la ventana entera en inglés y en
chino, el idioma se guarda, y `test_no_queda_nada_sin_traducir` se pone rojo si
aparece un texto sin traducir. **Un mensaje nuevo lleva su fila en
`i18n._TEXTOS`**, con los tres idiomas. Y el esquema pasó a tres vistas, con el
contorno medido de una foto del X8 Pro (bitácora, noche).

#### 1. El dibujo es nuestro, en SVG, y no se copia el del fabricante

Se investigó si servía la imagen del cliente oficial. **No hay ningún SVG de
mouse** en los 216 archivos del bundle: los únicos son `icomoon.svg` (una
fuente de iconos) y `vue.svg`. Todo el material gráfico de mouses son **PNG**,
uno por modelo. El que usaría el X8 Pro es `/assets/X8-BD26mML1.png` (275 KB),
que importa `X8-Bzci-KXG.js` —un chunk de 50 bytes cuyo contenido completo es
esa ruta— y consume `indexX8Pro-D0yEPypd.js`, que es `KeySetX8Pro`: lo pinta en
un `div.mouse-show` de `position:relative; width:200px; height:322px` con los
botones encima. Es la imagen del **X8 a secas**, reutilizada para el Pro.

Tres razones para no usarla, en orden de peso:

1. **`dev/research/README.md` ya dijo que no.** "De cada cosa se guarda **la
   huella, no el material**: son binarios y bundles propietarios". Por eso los
   4,2 MB del bundle no están versionados y sí `webapp.sha256`. El PNG cae en
   esa categoría. Bajarlo en tiempo de ejecución sortearía la regla y además
   ataría el dibujo de la app al sitio del que el proyecto se independiza; los
   nombres llevan hash de build, así que el 200 de hoy es 404 con el próximo.
2. **Las coordenadas de los botones no vienen con la imagen.** La página las
   pone con CSS scoped (`data-v-18197897`), en un `.css` que este proyecto
   nunca bajó: el manifiesto son 216 `.js`. Habría que medirlas a ojo igual.
3. **No alcanza para lo que esta app ofrece.** `buttonTableDataX8Pro` del
   bundle tiene **cinco** entradas —izquierdo, derecho, rueda, adelante,
   atrás—. Nuestro modelo nombra **siete** más los dos slots de rueda: el
   diagrama oficial no tiene dónde poner el botón de **dpi** ni el de **modo**.

Se puede mirar el PNG como referencia de proporciones sin copiarlo ni
distribuirlo, igual que se lee el bundle para el protocolo sin versionarlo.

**Cómo tiene que ser el SVG**: inline en el código, `currentColor` para que
siga el tema claro/oscuro, y **sin una lista de botones escrita a mano**. Los
números y los nombres salen de `estructuras.BOTONES_POR_NOMBRE` como sale todo
lo demás: un mouse con otros slots dibuja los suyos. Lo único que el dibujo
aporta es **dónde cae cada número**, que es geometría y no protocolo.

#### 2. Clickeable, desplegable, y los controles debajo

- un botón despliega y repliega el esquema;
- al tocar un número, la fila de ese botón queda a la vista;
- los controles de botones se corren **abajo** del esquema, no al costado.

#### 3. Y el orden de las filas de botones cambia

Hoy salen alfabéticas (`sorted(BOTONES_POR_NOMBRE.items())`): costado-adelante,
costado-atras, derecho, dpi, izquierdo, modo, rueda. Ese orden no es de nadie.
El nuevo es **el físico**, decidido:

| # | fila | slot |
| --- | --- | --- |
| 1 | clic izquierdo | 1 |
| 2 | clic derecho | 2 |
| 3 | sentido del scroll (derecho o invertido) | 17 y 18 |
| 4 | clic de rueda | 3 |
| 5 | botón atrás | 4 |
| 6 | botón adelante | 5 |
| 7 | botón dpi | 6 |
| 8 | botón modo | 7 |

Es casi el orden de slot, con el **sentido del scroll metido antes del clic de
rueda**: las dos cosas son la rueda y el sentido se mira primero. Ojo que el
campo del sentido no es un slot remapeable —son los slots 17 y 18, que no se
remapean— así que el orden no puede salir del número de slot solo.

#### 4. Qué botón es cada slot: CERRADO

Un diagrama que pone un número sobre un botón **afirma** que ese número es ese
botón, así que había que cerrar cuál era cuál antes de dibujar: si no, sería
amplificar una inferencia a hecho, el error que este proyecto ya nombró como el
que más veces estuvo cerca de costar caro. **Quedó cerrado.**

Cómo está cada uno hoy:

| slot | botón | estado |
| --- | --- | --- |
| 1, 2, 3 | izquierdo, derecho, clic de rueda | **fuerte**: es lo que dice el bloque de fábrica y no hay otra lectura razonable |
| 4 | costado-atrás | **MEDIDO**: remapeado a "reproducir / pausar", apretado —pausó la música— y devuelto a "atrás" |
| 5 | costado-adelante | **MEDIDO**: se remapeó con el soft y cambió ese slot y solo ese |
| 6 | dpi | **MEDIDO** por otro camino: al ciclarlo, el firmware escribe `Current_Dpi_level_flag` y el LED cambia de color |
| 7 | modo | **MEDIDO**: ver el punto 5 |
| 17, 18 | sentido del scroll | **MEDIDO**: se gira la rueda y se ve |

**No falta ninguno: quedaron todos cerrados.** El diagrama se
puede dibujar sin inventar ninguna posición. Los tres primeros no se apretaron
—no hace falta: el clic izquierdo, el derecho y el de rueda son lo que dice el
bloque de fábrica y no tienen lectura alternativa, y el izquierdo además no se
remapea por baranda—.

El método que cerró los dos últimos queda anotado porque sirve para cualquier
mouse nuevo: **remapear el slot a "reproducir / pausar" (código 24), apretar el
botón, y devolverlo**. Son dos escrituras, la verificación la hace el
reproductor del sistema y no deja nada trabado.

**La verificación es barata y no escribe nada**: `driver/scripts/sondear.py
--escuchar`, apretando un botón por vez y mirando qué llega. El del dpi ya está
resuelto por otro camino —al ciclarlo, el firmware escribe
`Current_Dpi_level_flag` y el LED cambia de color, MEDIDO—. Para
los del costado alcanza con remapear uno a algo reconocible y apretarlo.

Ya no queda nada que correr antes de dibujar. La regla igual se mantiene para
el día que aparezca otro mouse: si un slot no se puede confirmar, **el diagrama
lo dice** —ese número va en gris o con un signo de pregunta—, no se dibuja como
si estuviera medido.

#### 5. El botón de modo: RESUELTO

Se investigó el 15 en el bundle y se **midió** el 16 contra el mouse. Quedó en
`evidencia.md`; el resumen:

**MEDIDO.** Desde la aplicación se remapeó el slot 7 a `18 00 00`
—código 24, "reproducir / pausar"— y después se apretó el botón del mouse para
pasarlo a **modo USB**. Pasaron **las dos cosas juntas**: la música se pausó y
el mouse se desconectó del dongle.

Deja dos hechos, y el segundo es el que importa:

1. **El slot 7 es ese botón físico**, el de modo de conexión. Era el más flojo
   de los siete —salía de la asignación de fábrica y nunca se había apretado—
   y ahora está medido con verificación externa: el que contó fue el
   reproductor del sistema, no nuestro decodificador.
2. **El cambio de canal no es la función del slot.** Es del firmware, y sigue
   pasando con cualquier función encima. Por eso el código 60 (`FUN_MODE_KEY`)
   que trae de fábrica es, en la práctica, "no mandes nada extra".

**Lo que sigue sin medirse**: cuántos modos cicla y en qué orden, y si el
código 60 hace algo además de callar.

**Y una consecuencia para la interfaz, que hay que resolver al hacer el
diagrama**: remapear ese botón **no desactiva el cambio de modo**, así que cada
vez que alguien cambie de canal va a disparar además la función que le haya
puesto. Con "reproducir / pausar" es una molestia; con un macro largo o un
atajo destructivo es otra cosa. La fila de ese botón tiene que decirlo —hoy no
lo dice— y es material para su `?`.

**Y para probarlo, una advertencia de método**: apretar ese botón **corta la
corrida**, porque el mouse se va del dongle. No sirve `--escuchar` para
identificarlo —si cambia de canal no puede avisarlo por ese canal— y no
conviene apretarlo con nada más andando. La señal de que se apretó es que se
corta el latido de batería de cada 2 s.


---

### La interfaz está hecha

**`./asbridge-gui` levanta la aplicación.** Los cinco pasos del plan de abajo
están cumplidos, y el plan se deja tal cual porque explica **por qué** cada
pieza es como es.

```
driver/src/asbridge_ui/__main__.py          el punto de entrada (--nodo, --sin-tema, --nombres)
driver/src/asbridge_ui/ventana.py           la ventana: seis señales a seis lugares
driver/src/asbridge_ui/controles.py         la fábrica de controles, por propiedades del Campo
driver/src/asbridge_ui/paneles/parametros.py  los campos, agrupados por comando
driver/src/asbridge_ui/paneles/macros.py    macros, advertencias y el grabador en vivo
driver/src/asbridge_ui/teclado.py           de una tecla de Qt al nombre de un evento
driver/src/asbridge_ui/estilo.py            el tema, opcional
asbridge-gui                         el lanzador
```

Y tres cosas que entraron a la **biblioteca** porque la ventana las necesitaba
y el lugar correcto no era la ventana:

| Qué | Por qué ahí |
| --- | --- |
| `sesion.CLAVES_DE_MACRO` (`macro_modo`, `macro_repeticiones`, `macro_eventos`) en `preparar_mutacion()` | escribirle a un macro vivía **solo** dentro del CLI. `test_el_despachador_y_el_cli_dan_lo_mismo` ahora corre también los tres, así que siguen sin poder divergir |
| `sesion.FaltaElParametro`, con `.que` y `.ejemplo` | el desplegable de botones tiene que poder pedir el id del macro **sin saber que existe un código 18**. Sigue siendo `ValueError`: a quien ya lo atrapaba no le cambió nada |
| `modelo.advertencias_de()` pública | las advertencias hacen falta sobre la lista que se está **editando**, que todavía no es ningún `Macro`. Avisar después de escribir llega tarde |

Tres barandas nuevas, todas en `driver/tests/interfaz.py`:

* **la ventana no puede nombrar un campo.** El test parsea el árbol de
  `driver/src/asbridge_ui/` y falla si aparece una clave de `campos_de()` como literal
  o una comparación de `clave` contra un literal. Se verificó al revés: con un
  `if campo.clave == "lod"` puesto a propósito, se pone rojo;
* **lo que se construye tiene que verse.** Entró después de que la pantalla
  saliera en blanco con las 32 filas armadas adentro: el panel decidía qué
  grupos mostrar preguntando `isVisible()`, que es falso mientras la ventana no
  se mostró, así que los escondía todos;
* **mientras escribe, la pantalla se bloquea**, y se desbloquea pase lo que
  pase (`escritura_lista` o `problema`).

Lo que **no** se puede probar así es que la ventana se vea bien: eso lo mira
quien la usa.

#### La auditoría, y el bug que destapó

El agente A revisó la ventana recién hecha. De sus cuatro puntos, **tres eran
reales** y el cuarto estaba mal diagnosticado pero tapaba dos problemas de
verdad. Los cuatro quedaron arreglados con su test y con su control negativo.

| Qué | Arreglo |
| --- | --- |
| Si el hilo de hardware no está, `_pedir()` dejaba la corrutina colgada y `ocupado` no volvía nunca: **la ventana quedaba muerta**. Y tras `cerrar()` el loop no es `None` sino **cerrado**, así que `run_coroutine_threadsafe` tiraba `RuntimeError` por el medio de un slot de Qt | `_pedir()` devuelve si entró, cierra la corrutina si no, y `escribir()` suelta la pantalla |
| Una escritura que falla **antes** de la relectura no trae estado nuevo, y el control se quedaba mostrando lo que se pidió | `revertir()` en los dos paneles, disparado cuando la escritura termina sin traer estado |
| El deslizador del dpi tenía 39.900 posiciones y ofrecía 1623, que el mouse guarda como 1600 | `Campo.paso`, que **no es presentación**: es lo que el mouse puede guardar |
| El teclado numérico. Qt **no tiene** `Key_Numpad5` —el pad son las mismas teclas con `KeypadModifier`—, así que no se descartaba: se grababa como la fila de arriba, que es otro usage. Y el `+` y el `*` sí se perdían, en silencio | el grabador mira el modificador, y **avisa** cuando una tecla no entra |

**Y buscando la granularidad apareció uno peor, que no estaba en la
auditoría**: `respuesta` se **mostraba** como el número del slider (4..50) y se
**escribía** como el byte (2..25). Escribir el 8 que la pantalla acababa de
mostrar dejaba el mouse en 16, y la mitad de arriba del rango publicado ni
siquiera se podía escribir.

**Es exactamente el reproche que este proyecto le hace a la página oficial**
—"no puede releer su propio estado sin corromperlo"— y estaba en nuestro
código. No lo veía nadie porque el test de paridad compara
el despachador contra el CLI, y el CLI tiene la misma convención: los dos
coincidían en estar mal respecto del modelo.

La baranda que faltaba es `test_leer_y_reescribir_no_mueve_nada`, en
`salvaguardas.py`: para **cada** campo escribible, escribir lo que
`campos_de()` muestra tiene que dar el bloque idempotente byte a byte, y los
dos extremos del rango publicado tienen que ser escribibles. Mira desde el
único lado que importa, que es el valor que se ve.

#### Y de revisar los arreglos salieron dos cosas más

**Una restauración de más.** Sobre el arreglo de la pantalla que queda
mostrando lo que se pidió quedaron **dos** mecanismos en paralelo: uno colgado
de `ocupado(False)` y otro de `al_terminar_escritura()`. Hacen lo mismo, pero
no cubren lo mismo: una escritura que revienta **antes** de `sesion.aplicar()`
—un id de macro que no es un número alcanza— no emite `escritura_lista`
**nunca**, así que el segundo no corre y el control queda mostrando "macro"
para un botón que sigue en "adelante". Se comprobó en los dos sentidos y quedó
uno solo, el del `finally`, con `test_una_escritura_que_revienta_antes_tambien
_restaura`.

**Y un test que pasaba por el motivo equivocado.**
`test_un_respaldo_incompleto_no_escribe` esperaba 8 s por una operación que
tarda **15,0 s MEDIDOS**: la espera se vencía en todas las corridas, el
resultado quedaba en `None` y el `if` que comprobaba el motivo **no llegaba a
correr nunca**. El verde era cierto pero a medias, y venía de antes de la
ventana.

Lo destapó agregarle a `_correr_hasta()` un aviso por stderr cuando la espera
se vence. Vale la pena conservarlo: **la mayoría de los llamados ignoran el
valor de retorno**, así que sin el aviso una espera vencida se convierte en un
fallo más abajo que habla de otra cosa —o, como acá, en una comprobación que
se saltea en silencio—.

---

### Lo que había quedado listo

El backend estaba cerrado y las decisiones tomadas (abajo, "El plan de la
interfaz"):

* los dos codificadores que faltaban —atajo de teclado y eventos de macro—
  quedaron **MEDIDOS** contra el hardware;
* la tasa dejó de ser algo que uno tiene que recordar: el paso 0 la mide, la
  baja si hace falta y la devuelve, diciéndolo;
* `primera-escritura.py` delega la Etapa 3 entera en `sesion.aplicar()`, y eso
  destapó un bug de veredicto en la biblioteca que la app habría heredado;
* entraron las cuatro cosas que la auditoría pedía para la interfaz (G-01, 02,
  03, 05), el **puente entre asyncio y Qt** (G-04) y el **perfil declarativo**.

Todo está en [`bitacora.md`](bitacora.md) (tarde y cierres 1 a 5).

**Lo único pendiente contra el hardware no bloquea nada**: el modo 1 del macro
(cuatro corridas) y un macro de tres eventos para saber si la regla es la
paridad. Están al final, en "Lo que quedó abierto".

**El byte de estado de batería se cerró**: `3` es cargando y `1`
es a batería, medido con un cargador externo en cuatro transiciones y con el
LED morado de testigo. `sesion.Novedad` tiene ahora un campo `cargando` —que da
`None` para cualquier valor sin medir— y la baranda de `salvaguardas.py` se dio
vuelta a propósito. De paso salió un dato que **la interfaz tiene que tener en
cuenta**: con el mouse enchufado por cable a la PC no llega ni un latido por el
dongle, y el dongle sigue en el bus, así que no hay ninguna desconexión que
mostrar; simplemente dejan de llegar novedades. Ver `bitacora.md`.

---

### Cómo quedó el mouse

```
8000 Hz · reposo 0.5 min · hibernación 10 min · respuesta 8
LOD 1 mm · ripple ON · angle snapping ON · motion sync ON
dpi nivel 1 = 1600 (Pu) · nivel 1 en uso
costado-adelante = adelante · rueda 0a,09 · scroll derecho
macro 0x11 cargado (los cinco botones, 10 eventos de 10 ms), modo 0 x1,
sin botón asignado
```

**Y los 8000 Hz son el estado base**, decidido. La consecuencia
práctica es que **toda escritura pasa por bajar la tasa un momento**: el
respaldo completo de los siete comandos no sale arriba de 1000 Hz, y el paso 1
de la Etapa 3 lo exige. La herramienta lo hace sola y la devuelve al terminar.

Verificado a las 16:33 **desde los respaldos**, sin volver a
leer el hardware: `dev/models/attackshark-x8pro/respaldos/despues-de-escribir-macro-20260914T163256.json`
(macro 17, modo 0 x1, los diez eventos) y
`dev/models/attackshark-x8pro/respaldos/despues-de-escribir-botones-20260914T163311.json` (slot 5 =
`adelante`). Los macros viven en `estado["macros"]`, no en
`estado["comandos"]`.

> **Una trampa del formato de respaldo**: el `despues-de-escribir-*` de una
> corrida que bajó la tasa registra **1000 Hz**, porque se toma antes
> del `finally` que devuelve la tasa. El mouse queda en 8000 y el JSON dice
> otra cosa — y es justo el archivo que uno mira para saber cómo quedó. Para
> la tasa real, `driver/scripts/cambiar-rate.py` sin `--valor`, que solo mira.

### Lo que está cerrado

**El modelo de datos**: los siete comandos que el mouse contesta están
decodificados, y los cinco de `p.WRITABLE` se escriben desde Linux con la
Etapa 3 cumplida contra el hardware.

| Comando | Campos con codificador | Verificación externa |
| --- | --- | --- |
| rate (6) | la tasa | `medir-polling.py` |
| dpi (4) | los ocho niveles, LOD, ripple, angle snapping, motion sync, **nivel en uso** | LOD a simple vista; el nivel en uso, por el color del LED **y** por el byte que el firmware escribe al ciclar con el botón |
| luz (5) | color, reposo corto, hibernación, respuesta | el latido para; el escalón se mueve |
| botones (8) | los 18 slots y el orden de la rueda | se aprieta el botón |
| macros (9) | el disparo: modo y contador | se aprieta el botón; modos 0 y 2 medidos |

Cmd 7 (modo de despertado) **no se puede leer**, así que no tiene Etapa 3
posible: esa empieza releyendo.

#### Las tres barandas de "lo leído no se devuelve tal cual"

Es el patrón más importante que dejó la semana, y hay que respetarlo al
escribir el codificador de cualquier campo nuevo:

| comando | qué pasa si se devuelve el bloque leído |
| --- | --- |
| cmd 8 | los slots 4, 5 y 6 vienen permutados: rota tres botones |
| cmd 9 | el checksum interno viene invertido (`0c 6d` al escribir, `6d 0c` al leer) |
| cmd 4 | la página lo lee cruzado y lo reescribe mal (I-W24) |

Por eso codificador y decodificador son funciones distintas, y no un `memcpy`
con nombre.

---

### Los comandos de parámetros están cerrados

La última Etapa 3 pendiente **se cumplió**: el nivel de dpi en
uso, escrito 1 → 2 y 5 → 1 desde Linux, con el LED tomando el color del nivel
pedido en las dos. Y de yapa salió la verificación más independiente que tiene
el proyecto: al ciclar el dpi con el botón del mouse, **el firmware escribe el
mismo byte que nosotros y solo ese**, así que el campo quedó confirmado en las
dos direcciones sin pasar por software de terceros. Está en `bitacora.md`.

~~**Lo único barato que queda es el modo 1 del macro**~~ **CERRADO**
(2026-09-20, cuatro corridas iguales). Y salió con una corrección: el nombre
del fabricante —"cualquier tecla para detener", `StopOnAnyKey`— **no describe
lo que hace**. Lo medido es que se dispara al apretar, **sigue después de
soltar**, una tecla del teclado **no** lo detiene —se escribe esa tecla y el
macro sigue saliendo entremedio— y lo detiene **cualquier otro botón del
mouse**. Con eso los tres modos están verificados apretando el botón.

No bloquea nada: se puede hacer cuando caiga. Lo que sigue es la aplicación.

---

### La Etapa 3 de los dos codificadores: CUMPLIDA

El atajo de teclado y los eventos de macro se verificaron apretando el botón.
El detalle está en [`bitacora.md`](bitacora.md); acá va lo que hay que
recordar al grabar un macro.

**Los dos codificadores andan.** El primer macro que este mouse ejecutó armado
por nosotros —`clic-rueda:dir0@10, clic-rueda:dir1@10`— es uno que ninguna
captura contiene, y el atajo `ctrl+c` (slot `11 01 06`, tampoco capturado)
copia en un editor y manda SIGINT en una terminal.

**Y salieron tres cosas que nadie buscaba:**

| | |
| --- | --- |
| **`dir0` aprieta, `dir1` suelta** | MEDIDO. El punto 16 de `evidencia.md` queda cerrado, y la inferencia era correcta |
| **Un macro de un solo evento no se reproduce** | El mouse lo guarda —la relectura lo devuelve con su checksum bien— y al apretar el botón no pasa nada. Con dos sale, **y con tres también** (MEDIDO 2026-09-20), así que **la paridad no era la regla**. Por qué el de uno no corre sigue sin saberse |
| **El firmware no suelta nada al terminar el macro** | Lo que el macro deja apretado queda apretado, y **apretar la tecla física no la despega**: hay que desacoplar el dongle |

#### La advertencia que el proyecto tenía escrita y era falsa

La escribimos esa misma mañana, en `d0d3f5e`, junto con los codificadores:
*"si una `a` queda pegada, se despega apretando la tecla en el teclado"*. **No.** Con la tecla trabada el sistema ya la tiene por
apretada, así que la pulsación real no genera un carácter nuevo: la letra deja
de escribirse, y el propio remedio deja de estar disponible. El síntoma es
inconfundible —se escribe sin esa letra— y la salida es **desacoplar el
dongle**.

De ahí las dos barandas nuevas, que **avisan sin prohibir** (los dos macros
que las disparan son exactamente los experimentos que cerraron la dirección):

* `estructuras.eventos_sin_cerrar()` dice qué usages quedan apretados;
* `MACRO_EVENTOS_MIN_QUE_CORRE = 2` marca el macro que no se va a reproducir;
* `primera-escritura.advertencias_de_eventos()` las imprime en el **paso 3,
  antes del prompt de confirmación**, con el remedio real.

#### Y una lección de método, que es nueva

**Un experimento anotado en los docs es una hipótesis, no un procedimiento.**
El que este archivo proponía para cerrar la dirección —"un macro de un solo
evento `dir0` sobre una tecla"— estuvo tres días escrito como "se cierra
barato" y no cerraba nada: apilaba sin saberlo una segunda variable que
ninguna captura había tocado, **una tecla de teclado dentro de un macro**. Los
diez eventos de la única captura son los cinco botones del mouse (241..245).

Cuando un experimento diseñado no contesta, la primera sospecha no es el
hardware: es que mide dos cosas.

---

### 8 kHz en Linux: qué falta de verdad

**Usar el mouse a 8 kHz ya funciona**: `medir-polling.py` midió 8004 Hz con el
91.2% de los intervalos en 125 us, y el dongle declara `bInterval = 1`
(125 us) en High Speed. Lo que no funciona es **configurarlo** a esa tasa, y
quedó claro qué parte:

| | a 8 kHz |
| --- | --- |
| escrituras | **funcionan** — el driver oficial bajó el rate con el mouse a 7825 Hz y recibió `0xC0` + `0xC1` |
| lecturas cortas (versión, rate, luz) | funcionan — 3 de 3 corridas |
| lecturas largas (dpi, botones, macro, perfil) | **fallan** — el respaldo no se completa nunca |

Así que el problema real es que **subir a 8 kHz desde Linux es una trampa**: el
paso 1 de la Etapa 3 exige un respaldo completo de los siete comandos, y a esa
tasa no sale, así que para volver hay que ir a la VM. No es que el mouse no
pueda: es que la baranda no sabe que este caso es distinto.

#### Lo que ya está: las siete tasas

`estructuras.escribir_report_rate()` las escribe todas —125, 250, 500, 1000,
2000, 4000 y 8000— con Etapa 2 contra las catorce escrituras del bus, y
`report_rate_de()` las lee. Es lo que la aplicación va a usar; el CLI ya las
ofrecía, pero la aritmética estaba suelta dentro de la herramienta.

Con una baranda nueva: el codificador **respeta el nibble bajo**, así que si el
mouse quedó con uno raro —la página escribió `0x01`— el byte que
sale no lo mandó nunca un cliente oficial. No se prohíbe, se avisa antes de
confirmar (`rate_byte_en_el_bus()`).

#### La frontera está MEDIDA, y es 1000 Hz

El experimento se corrió y contestó en el primer escalón: **a
2000 Hz el respaldo completo ya no sale** (botones, macro y perfil completo sin
respuesta). No hace falta probar 4000: la zona utilizable para configurar
termina en 1000.

**Lo que sigue sin probarse es quieto contra movido**, y ahora sale barato:
ya no hace falta ir a 8 kHz, alcanza con 2000. Está medido que el mouse no
manda nada cuando está quieto, así que a tasas altas la instrucción de siempre
—"mové el mouse"— puede ser justo lo que satura el aire:

```bash
driver/scripts/cambiar-rate.py --valor 2000
driver/scripts/respaldar.py            # moviendo el mouse, como siempre
driver/scripts/respaldar.py            # sin tocarlo: ¿salen más de los siete?
driver/scripts/cambiar-rate.py --valor 1000
```

La vuelta está garantizada en los dos casos, porque `cambiar-rate.py` no
depende del respaldo completo. Si con el mouse quieto salen los siete, cambia
una instrucción que hoy se aplica por igual a todas las tasas.

#### Configurar con el mouse a una tasa alta: resuelto

`primera-escritura.py` baja a 1000 Hz solo, corre la Etapa 3
entera con su respaldo completo y devuelve la tasa original al terminar —en el
`finally`, así que vale también si la escritura falló—.

No se intenta respaldar a 8 kHz y no se descarta el respaldo: las dos serían
peores. A esa tasa ni siquiera se puede **armar** la escritura de dpi, porque
el codificador parte del bloque leído y ese bloque son 54 bytes, de los que se
caen. Falta probarlo contra el hardware: es lo primero que conviene correr.

```bash
driver/scripts/cambiar-rate.py --valor 8000
driver/scripts/primera-escritura.py --comando dpi --nivel 1 --valor 1600
driver/scripts/medir-polling.py --segundos 10     # tiene que haber vuelto a 8000
```

#### Cambiar de tasa: resuelto

`cambiar-rate.py --valor N` cambia la tasa **en las dos direcciones**, medido
con las cuatro —1000 → 2000 → 4000 → 8000 y la vuelta—, cada una
en el primer intento y verificada con `medir-polling.py` (a 8000: 126 us de
mediana, 68.9% de los intervalos en 125 us).

Lo que fallaba no era el hardware ni el canal: la trama iba empaquetada dos
veces y el mouse recibía un bloque de dpi de catorce bytes. Ver `bitacora.md`.

#### El camino de vuelta: hecho

`driver/scripts/cambiar-rate.py`. Lee cmd 6, lo guarda en `dev/models/attackshark-x8pro/respaldos/`,
muestra la trama, pide confirmación por terminal, escribe y relee. No pide el
respaldo de los siete bloques —que es lo que no se puede a esa tasa— y el campo
que toca queda respaldado igual, leído un segundo antes.

Y las herramientas dejaron de colgarse: se abandona la tanda tras tres fallos
seguidos, el bloque de rate hace de semáforo (si dice más de 1000 Hz, no se
intenta una segunda pasada) y un Ctrl-C sale con una línea en vez de treinta de
traceback.

---

### Por qué una aplicación propia, y con qué base

El objetivo no es ser un puente: es una aplicación propia. Lo que se aprendió
esta semana es el argumento, y también el plan.

#### Por qué, en hechos medidos

La página oficial **lee sus propios bytes con una regla distinta de la que usa
para escribirlos**:

| Campo | Escribe | Lee | Consecuencia |
| --- | --- | --- | --- |
| dpi (I-W10) | `Pu()`, lineal | tabla dispersa 3311 | muestra 1350 donde escribió 1600 |
| report rate | los dos nibbles iguales | el byte entero como índice | escribió `0x01`, que no es ninguno de los siete |
| interruptores (I-W24) | `lod<<4\|ripple` | byte entero `=== 1`, cruzado | **no puede mostrar el estado real** |
| botones (cmd 8) | soft y web, **al revés uno del otro** en la rueda | ninguno de los dos lee | la web deja el scroll invertido, MEDIDO |

Y quedó medido lo que eso significa en una sola conexión: con el
usuario tocando **un** botón, la página leyó tres bloques, escribió cinco, y
los tres que leyó los escribió cambiados. No es que nos falte información: es
que ser un puente nos ata a un cliente que está mal.

A eso se suma lo que **no expone**: el `Level1SleepTimer` está en un div con
`display:none`, así que el reposo corto no se toca desde la web en este modelo.

#### Lo que ya está listo para servir de base

- `driver/src/asbridge/estructuras.py` — decodifica **por lo que el firmware recibe,
  no por lo que la página muestra**, y tiene los doce codificadores, cada uno
  verificado contra tramas reales del driver oficial y con su test. Los dos
  últimos son: el **atajo de teclado** (con la tabla de 111
  usages HID del bundle, los cuatro modificadores atestiguados y el texto
  `ctrl+shift+s` en las dos direcciones) y los **eventos de macro**
  (`escribir_eventos_macro()` sobre un bloque leído, `armar_macro()` desde
  cero para un id que el mouse todavía no tiene).
- `driver/src/asbridge/nombres.py` — los **nombres de los macros**, que el mouse no
  guarda: el bloque de 111 bytes no tiene campo de nombre. Viven en
  `~/.config/asbridge/macros.json` y los edita
  `driver/scripts/nombres-de-macro.py`, que no toca el mouse.
- `driver/src/asbridge/sesion.py` — **la capa de la aplicación, completa**. Lee el
  estado entero (`leer_estado`), lo compara (`diferencias`), juzga cómo salió
  una escritura (`juzgar`), maneja la tasa (`tasa_actual`, `poner_tasa`) y
  **corre la Etapa 3 entera** (`aplicar`, que baja y devuelve la tasa sola).
  Desde además traduce `(clave, valor)` en qué escribir
  (`preparar_mutacion`) y decodifica lo que el mouse avisa solo
  (`novedad_de`, `escuchar_novedades`). No imprime y no decide políticas:
  avisa por callbacks con clave estable.
- `driver/src/asbridge/modelo.py` — los **23 campos con nombre propio**
  (`campos_de`, `por_clave`) y los **macros** (`macros_de`), con sus
  advertencias medidas. Es de acá que la ventana se construye sola.
- `driver/src/asbridge/dispositivos.py` — el **catálogo** de los 47 modelos que
  conoce el bundle (LEÍDO, de tres marcas) y el **perfil** del único que
  sabemos manejar (MEDIDO). Saber que un modelo existe no es saber hablarle.
- `driver/src/asbridge_ui/hardware.py` — el **puente entre `asyncio` y Qt**: un hilo
  dedicado que expone el mouse por señales. Nada de ese módulo toca widgets.

#### Lo que le falta, en orden

1. ~~La capa de escritura~~ **hecha.** `sesion.aplicar()` corre
   la Etapa 3 entera sin terminal —tasa, respaldo completo, lectura,
   codificación por callback, confirmación, escritura, relectura y veredicto,
   con la tasa devuelta en el `finally`— y `test_el_orquestador_aborta_donde_debe`
   prueba los seis casos sin hardware, tres de ellos barandas.

   ~~Queda una deuda anotada: `primera-escritura.py` mantiene su propia
   coreografía.~~ **Cerrada.** `primera-escritura.py` delega la
   Etapa 3 entera en `sesion.aplicar()` y conserva lo suyo: qué bytes pide el
   usuario (`codificar`) y cómo se cuenta lo que pasó. Sigue valiendo la regla:
   **las decisiones viven en la biblioteca; lo propio del CLI es cómo se
   cuentan**.

   Se hizo cuando la duplicación empezó a costar —ese mismo día el permiso de
   tasa se escribió dos veces, una de cada lado— y destapó **un bug de la
   biblioteca**: `aplicar()` infería la idempotencia comparando `datos ==
   leido`, que en cmd 8 y cmd 9 da lo contrario de la verdad. Le habría dado
   `no-cambio-nada` a una escritura idempotente de botones o de macro que salió
   perfecta. Ver `bitacora.md` (cierre 2).

   Y primero se puso la red que faltaba: `main()` acepta un `device`, así que
   la Etapa 3 entera corre contra `_MouseFalso`
   (`test_la_herramienta_de_punta_a_punta`, cinco casos, cinco mutaciones
   detectadas), más una caracterización de quince corridas que quedó en
   **15 de 15 con las mismas escrituras al mouse**.
2. ~~Un modelo de estado con nombres propios~~ **hecho.**
   `driver/src/asbridge/modelo.py` devuelve **23 campos** con clave estable, nombre en
   castellano, valor, unidad, rango u opciones, si se puede escribir, y la
   advertencia medida cuando la hay. Ningún nombre del fabricante queda a la
   vista, y `test_modelo_con_nombres_propios` lo fija —junto con que el clic
   izquierdo no se ofrezca, que los colores de indicador no figuren como
   escribibles y que un mouse leído a medias dé los campos que sí se leyeron—.
3. ~~Las dos cosas que le faltan para igualar al soft~~ **hechas**, las dos
   con Etapa 2 contra el bus (ver
   [`paridad-con-el-soft.md`](paridad-con-el-soft.md) y la bitácora):
   * el **codificador de eventos de macro**: `escribir_eventos_macro()` y
     `armar_macro()`, con los diez eventos del macro capturado devolviendo el
     bloque de 111 bytes **idéntico** al del soft nativo. En el CLI,
     `--comando macro --eventos "clic-izquierdo:abajo@10, ..."`;
   * el **atajo de teclado** (código 17): `escribir_atajo()` y
     `atajo_desde_texto()`, verificados contra los dos bloques del bus
     (`11 08 07`, `11 0a 16`) y contra las veinte entradas del bundle. En el
     CLI, `--funcion "atajo de teclado" --atajo ctrl+c`, con `--listar-teclas`;
   * y los **nombres de macro** del lado de la aplicación:
     `driver/src/asbridge/nombres.py` más `driver/scripts/nombres-de-macro.py`.

   **La Etapa 3 de los dos quedó CUMPLIDA esa misma tarde** (ver sección
   arriba y la bitácora tarde).
4. **Y lo que sigue es la interfaz.** Grabar un macro apretando teclas en vivo es
   parte de la interfaz, no del protocolo: el codificador ya está.

#### Lo primero de la interfaz: hecho

Las cuatro cosas que la auditoría marcó como "lo que la interfaz tendría que
reimplementar" ya están en la biblioteca, cada una con su test:

| | Qué hay ahora |
| --- | --- |
| **G-01** | `sesion.preparar_mutacion(clave, valor)` → `Mutacion(cmd, codificar)`, listo para pasarle a `aplicar()`. Las claves son las de `modelo.campos_de()`, así que la interfaz usa el mismo identificador para mostrar y para escribir. Traduce lo que hay que traducir —el LOD entra en **milímetros**, el color como `"#00ff00"`, un botón como `"adelante"` o `("macro", 17)`— y los campos que no se escriben tiran `CampoNoEscribible` **con el motivo medido**, no un `KeyError` |
| **G-02** | `modelo.macros_de(estado, nombres)` → una lista de `Macro` con id, nombre local, modo, qué hace ese modo, repeticiones, eventos, el texto reescribible y las **advertencias medidas** (que un macro de un evento no corre; que dejar algo sin cerrar traba la tecla y hay que desacoplar el dongle) |
| **G-03** | `sesion.novedad_de(datos)` y `sesion.escuchar_novedades(device, cb)`: la batería y el cambio de nivel de dpi que el mouse avisa solo por el Report ID 3 |
| **G-05** | `hidraw.FaltaLaReglaDeUdev`, que **sigue siendo un `PermissionError`** y trae `.comando` y `.path` como datos, para que una ventana ofrezca el arreglo sin parsear texto |

**Lo que impide que G-01 se convierta en una segunda copia** es
`test_el_despachador_y_el_cli_dan_lo_mismo`: corre los dos caminos —el
despachador y el CLI— contra el mismo mouse falso y compara el bloque que sale,
en dieciséis casos que cubren los cinco comandos. Si alguien toca uno y no el
otro, se pone rojo.

Y una decisión epistémica que conviene respetar: **`Novedad` no tiene un campo
`cargando`**. El byte de estado que acompaña al nivel de batería solo se vio
valiendo 1, y el `2` ("desconocido") sale del bundle; qué significa cada valor
no está medido. Se expone crudo hasta que alguien mida el mouse enchufado y
desenchufado. El test lo fija.

#### El plan de la interfaz

**Las decisiones ya están tomadas.** No hace falta volver a discutirlas al
empezar; sí hace falta respetarlas, porque cada una tiene un motivo detrás.

| Decisión | Por qué |
| --- | --- |
| **PySide6 (Qt 6)** | Lo pidió el usuario. Ya está instalado (6.11.2), es estable en Linux y no mete una capa intermedia |
| **Hilo dedicado, no `qasync`** | `qasync` no está instalado y no hace falta: el hilo no agrega dependencia y **aísla de verdad** —el hilo de la ventana nunca toca el dispositivo, así que ninguna espera del protocolo puede trabarla ni por error—. Ya está hecho y probado: `asbridge_ui/hardware.py` |
| **Data-driven: la ventana se construye desde `modelo.campos_de()`** | No conocer ningún campo por nombre es lo que hace que la ventana no haya que reescribirla el día que el modelo deje de ser mono-mouse |
| **Sin prompts de confirmación** | El consentimiento es el click. Lo que se conserva es el **registro**: la trama va al log igual que el CLI la imprime |
| **La ventana no decide nada del protocolo** | Qué bytes se escriben lo dice `sesion.preparar_mutacion()`, que es el mismo camino que usa el CLI, con un test que compara los dos |

#### Lo que ya está construido, y anda

```
driver/src/asbridge_ui/hardware.py     el puente asyncio <-> Qt, por señales
driver/tests/interfaz.py               once pruebas, sin ventana y sin mouse
```

`Hardware` expone: `estado`, `progreso`, `novedad`, `escritura_lista`,
`problema(mensaje, comando)`, `conectado`, `modelo_detectado`. Y acepta
`device=` para probarlo sin hardware, igual que `primera-escritura.py`.

Dos barandas que ya tiene y conviene no aflojar:

* **`cerrar()` espera a lo que esté en vuelo.** El camino multi-trama de cmd 9
  manda dos tramas con 1.008 s en el medio; cortar ahí deja medio bloque de
  macro en el mouse. Si no termina en `ESPERA_AL_CERRAR`, corta **y lo dice**;
* **avisa si el mouse no es el modelo medido.** El `device_id` llega solo en el
  Report ID 3, y todo lo que hay está medido contra un X8 Pro.

#### Los pasos, en orden

**1. La ventana de parámetros, autoconstruida.** Recorrer `modelo.campos_de()`
y dibujar un control por campo según lo que el `Campo` ya trae: `opciones` →
un desplegable, `minimo`/`maximo` → un deslizador, un booleano → un interruptor,
`unidad` al lado. **Sin un solo `if clave == "lod"`**: si aparece un `if` por
nombre de campo, la ventana dejó de ser data-driven.

   * los campos con `escribible=False` se muestran igual, en gris, con el
     motivo de `sesion.no_escribibles()` en el tooltip;
   * `campo.nota` y `campo.difiere_del_cliente_oficial` son la razón de ser del
     proyecto: cuando el cliente oficial mostraría otra cosa, **eso se
     muestra**, no se esconde;
   * al mover un control: `hardware.escribir(campo.clave, valor)`. Nada más.

**2. La barra de estado.** Conectar `progreso` a un label y `problema` a un
cartel con botón: si `comando` no está vacío —hoy solo la regla de udev— el
botón lo ofrece. Y el indicador de batería desde `novedad`.

   > Una escritura tarda **varios segundos** —respaldo completo, escritura,
   > relectura—. Sin esto la ventana parece colgada. Los avisos ya vienen
   > traducidos por `_legible()`.

**3. El panel de macros**, desde `modelo.macros_de(estado, nombres)`. Mostrar
las `advertencias` **antes** de que el usuario apriete el botón, no después:
son las dos cosas medidas (que un macro de un evento no corre, y
que dejar algo sin cerrar traba la tecla y obliga a desacoplar el dongle).
Grabar apretando teclas en vivo es de acá, no del protocolo: el codificador ya
está.

**4. ~~Y recién ahí, lo que falta para multi-mouse de verdad~~ HECHO.** Era
lo último de esta lista: la ventana ya nacía lista y el que
seguía siendo mono-mouse era el **modelo**, con los números del X8 Pro escritos
adentro (`DPI_SIZE = 56`, `BOTONES_SIZE = 59`, `BOTONES_CANTIDAD = 18`,
`MACRO_SIZE = 111`, `modelo.LUZ_RGB_VISIBLE` y los offsets fijos de
`estructuras.py`).

Ahora hay un solo lugar, el perfil:

- `dispositivos.activo()` dice a qué modelo se le habla. `usar()` lo elige para
  todo el programa —lo llama `Hardware` cuando el mouse dice qué modelo es y
  `perfil_de()` devuelve un perfil, o sea **solo con un modelo medido**; con uno
  que nadie midió avisa y no cambia nada— y `como()` lo cambia **solo en el hilo
  que lo llama**, para leer un estado ajeno o para una prueba. **Sigue habiendo
  un solo perfil medido**;
- `estructuras.py` le pregunta al perfil **en cada llamada**, y los nombres de
  siempre los resuelve un `__getattr__` de módulo, así que nadie cambió de
  vocabulario. Las tablas de campos de cmd 4 y cmd 8 se **generan** con el
  perfil;
- se mudaron además `botones_por_nombre` y `como_se_supo_el_boton`: qué botón
  es cada slot, y su evidencia, son de este modelo;
- `modelo.campos_de(estado, perfil)` recibe el perfil, y `LUZ_RGB_VISIBLE` se
  fue a `Perfil.campos_ausentes` —un `clave -> por qué`—. Sacar `"color"` de
  esa lista devuelve el control **sin tocar la ventana**, y
  `test_el_rgb_que_no_enciende_nada_no_se_ofrece` lo verifica ahora en las dos
  direcciones de verdad: la rama "el RGB enciende" **se ejecuta**, con un
  perfil que no lo lista;
- `sesion.NO_ESCRIBIBLES` pasó a ser `sesion.no_escribibles()`, porque se
  armaba al importar con un `range(1, 9)`.

**Y el test que los comparaba cambió de anclaje**, que era la parte delicada:
`test_el_perfil_no_miente` comparaba el perfil contra las constantes que ahora
salen de él —una verificación que no puede fallar—, así que ahora compara cada
campo contra la evidencia (las capturas, el bus y `READ_SUB` del bundle), y lo
que no tiene fuente independiente lo dice. `test_el_perfil_manda_de_verdad`
arma un mouse de fantasía y verifica que cambie lo que tiene que cambiar. El
detalle está en la bitácora.

Lo que **no** se hizo, a propósito: agregar un segundo perfil. Para eso hace
falta la captura del driver oficial de ese modelo, no adivinar offsets
parecidos.

#### Lo que NO hay que hacer

* **Un `if` por nombre de campo en la ventana.** Es lo único que la vuelve
  mono-mouse otra vez.
* **Reimplementar el mapeo de escritura.** Existe `preparar_mutacion()` y hay
  un test que lo compara contra el CLI: si la ventana arma bloques por su
  cuenta, ese test deja de proteger nada.
* **Llamar a `asbridge` desde el hilo de la ventana.** Todo va por `Hardware`.
* **Copiar el perfil del X8 Pro para otro modelo.** El test se pone rojo a
  propósito. Para agregar uno hace falta la captura de su driver oficial.
* **Esconder lo que el cliente oficial muestra distinto.** Es el argumento
  entero del proyecto. Desde no está debajo del control sino
  detrás del `?` de la fila y en su tooltip —que es donde entra sin tapar los
  controles—, y hay dos tests que exigen que **toda** nota medida y **toda**
  discrepancia salgan por los dos lados. Moverlo de lugar se puede; dejar de
  decirlo, no.

#### Cómo verificar cada paso, sin mouse

`driver/tests/interfaz.py` corre contra `_MouseFalso` y sin abrir ninguna ventana
(`QCoreApplication`, no `QApplication`). Un paso nuevo se prueba ahí antes de
tocar el hardware. Lo que **no** se puede probar así es que la ventana se vea
bien: eso lo mira quien la usa.

#### Lo que la aplicación NO debe heredar

- Ninguna de las lecturas equivocadas de la tabla de arriba.
- **Reescribir el estado al conectarse.** La página lo hace, y está medido.
- **Los nombres del fabricante.** `SensitivityX` no es sensibilidad,
  `closeTime` no es la hibernación y `LightBrightness` no es el brillo —es
  medio tiempo de hibernación—. El módulo los traduce; la aplicación debería
  mostrar los traducidos, como ya se hizo con `--lod` en milímetros y con los
  botones por nombre.

---

### Lo técnico, cerrado

**Al 2026-09-20 no queda nada técnico que dependa del código.** Lo que se cerró
en esta sesión, con su evidencia en [`bitacora.md`](bitacora.md):

| | |
| --- | --- |
| el sangrado del canal por cable | MEDIDO (1–2.5%), **cuatro filtros** y la decisión de no tocar los tiempos |
| configurar por cable | todos los campos con Etapa 3, incluida la mutación real del macro |
| la detección de bus | las tres situaciones, contra el bus de verdad |
| el macro de 3 eventos | corre: **la paridad no era la regla** |
| el modo 1 del macro | lo detiene **otro botón del mouse**, no una tecla: el nombre del fabricante miente |
| los tres modos de macro | verificados apretando el botón; `MODO_SIN_MEDIR` quedó en `None` |
| el instalador | estaba roto y el ensayo no podía saberlo; arreglado y con test |

Queda para quien retome, y **nada de esto bloquea**:

1. **correr la instalación de verdad y la desinstalación** —lo único que el
   proyecto todavía no ejercitó de punta a punta—;
2. **el byte de batería llena**: necesita cargar el mouse con algo que **no**
   sea la PC, porque con el cable puesto el dongle se calla;
3. **si el firmware suelta los botones del mouse** al terminar un macro. Lo
   medido es con teclas. La prueba crea a propósito un botón trabado y el
   único escape es desacoplar el dongle: es la menos valiosa y la más molesta;
4. **las capturas de VM**, que son lo que falta para los colores de nivel,
   `dpi_ON_OFF_flag`, `Dpi_indication_type`, `lightMode`, los macros de 131 de
   la web y el byte de rate `0x01`. No falta código: falta captura.

Y dos misterios que quedaron sin cerrar porque no hay con qué: **la corrupción
del bloque de versión** (una sola muestra, y no es el sangrado de cmd 6) y
**por qué un macro de un solo evento no corre** —ahora se sabe que no es la
paridad—.

---

### Lo que quedó abierto

**Ninguno bloquea la interfaz.** Los tres primeros son corridas cortas contra
el hardware, y las corre el usuario.

| Qué | Cómo se cierra |
| --- | --- |
| **Qué manda el byte de estado con la batería llena** | El `1` (a batería) y el `3` (cargando) quedaron MEDIDOS; si hay un cuarto valor para "cargado", no se vio. Es una corrida de horas, no de minutos, y no bloquea nada: `cargando` ya da `None` para todo lo que no se midió |
| ~~**El modo 1 del macro**, sin apretar~~ | **CERRADO** (2026-09-20, cuatro corridas): lo detiene **otro botón del mouse**, no una tecla. El nombre del fabricante (`StopOnAnyKey`) no describe lo que hace |
| **Por qué un macro de un evento no corre** | MEDIDO que no corre, y con dos y con tres sí; la regla no. **No es la paridad**: el de tres eventos corrió (2026-09-20). Sin otra prueba a mano que la cierre |
| **Si el firmware tampoco suelta los botones del mouse** | Lo medido es con teclas. El alcance a los cinco usages de botón queda inferido |
| **Los colores de nivel de dpi** | **Sin camino de escritura hoy.** El campo admite RGB libre y el LED lo usa (MEDIDO), pero **ningún cliente oficial lo escribe**: la web no puede —su serializador acepta los ocho colores y ninguna llamada se los pasa— y el soft, aunque tiene el diálogo compilado, no le habilita el control a este mouse (comprobado). Sin captura no hay Etapa 2. Quedan dos vías posibles: 1) desensamblar/forzar el diálogo en el soft oficial de Windows en VM para capturar una trama genuina; o 2) un experimento de mutación quirúrgica controlada (cambiar los 3 bytes de un solo nivel con checksum recalculado y verificar si el parpadeo cambia). Ver `bitacora.md` |
| **Escribir** `dpi_ON_OFF_flag`, `Dpi_indication_type` o `lightMode` | **Constantes en las 76 escrituras capturadas**: no falta código, falta captura. Se consiguen moviendo esos controles en el soft nativo con usbmon corriendo |
| Si la página manda macros de **131 bytes** donde el soft manda 111 | Capturando la web mientras asigna un macro. Hay que pagar el peaje: abrir la página pisa dpi, ripple, luz y rueda |
| Qué frecuencia deja el byte de rate `0x01` | Un viaje a la VM, y puede dejar el mouse en 8 kHz |
| La rama de tiempos largos del macro (>127 ms) | **Decodificada y ahora también escribible, pero INFERIDA** del bundle. Se cierra por dos caminos: grabando un macro con un retardo largo desde el soft y capturando, o escribiéndolo nosotros y mirando si el retardo sale (arriba, punto 3) |
| ~~**Escribir la tasa por la Etapa 3 se deshace solo**~~ | **CERRADO.** Se tomó la segunda de las dos salidas que este punto proponía: la tasa se escribe siempre por el camino de un solo comando, ahora también desde la aplicación (`sesion.Configuracion._escribir_tasa`), y la tasa prestada que la sesión tuviera anotada se cancela **antes** de tocar nada. El respaldo completo se sigue exigiendo, porque dentro de la sesión el mouse ya está a 1000 Hz y sí se puede tomar. `Ventana.tasa_que_se_pisa` se fue con el bug |
| Modo de despertado (cmd 7) | **No se puede leer**, así que no hay Etapa 3 posible |
| El valor absoluto del corte del LOD | El protocolo de la escalera está en `bitacora.md` |
| Cuál de las dos fórmulas es el dpi real del sensor (I-W11) | Necesita medir desplazamiento físico |
| `responseTime` como debounce | INFERIDO del nombre del control, sin medición barata |

---

### Las lecciones que se acumularon, y siguen valiendo

1. **La documentación heredada del proyecto no es evidencia.** Dijo que botones
   y macros no tenían capturas: botones tenía quince bloques en el bus.
2. **Y menos si es una promesa de verificación** ("visible a simple vista (el
   LED)", sobre un mouse que no tiene esa luz).
3. **Una medición sin su condición no es una corrección.** El "~4 s" de
   `hidraw.py` era cierto: describía el mouse quieto.
4. **Si una prueba deja el mouse en un estado que hay que revertir, el paso de
   vuelta se escribe antes de correrla.**
5. **Una herramienta que anuncia una alarma falsa y después la emite igual es
   peor que una que no avisa.** En un proyecto cuya única red son las barandas,
   gastar una alarma es caro.
6. **Leer y escribir no son la misma estructura.** Tres veces en una semana, en
   tres comandos distintos, y ninguna estaba documentada.
7. **Antes de escribir un codificador, mirar si el driver oficial movió ese
   campo alguna vez.** Si es constante en todas las capturas, no falta código:
   falta captura.
8. **Los nombres del fabricante hacen ver campos donde hay uno solo.**
   `LightBrightness` y `breathingSpeed` parecían dos parámetros sin escribir y
   son los nibbles del tiempo de hibernación.
9. **Si un campo se puede mover desde el hardware, esa es la mejor
   verificación que hay.** Dejar que el firmware lo escriba y leerlo nosotros
   no depende de nuestro código ni del del fabricante. Apareció de casualidad
   con el botón de ciclo de dpi; conviene buscarla a propósito.

---

## El proyecto pasa a llamarse LinShark

No toca el mouse: es un cambio de nombre. Va acá por lo que falló en el camino.

- Los paquetes `asbridge` y `asbridge_ui` pasan a `linshark` y `linshark_ui`;
  los lanzadores, a `linshark` y `linshark-gui`; lo instalado, a
  `/opt/linshark`; el título de la ventana y el menú dicen **LinShark**, y ya
  no el nombre de un modelo. Antes de elegirlo se buscó: no hay otro proyecto
  de Linux con ese nombre, ni un paquete `linshark` en PyPI.
- Lo que **no** cambió: la regla de udev y `models/attackshark-x8pro/`, que son
  de un modelo; esta bitácora y `capturas-w/`, que son registro. Por eso acá
  arriba sigue diciendo `asbridge`.
- Las carpetas de quien lo usa (`~/.config/asbridge/`,
  `~/.local/state/asbridge/`) **se mudan, no se empiezan de nuevo**: un
  respaldo no se vuelve a sacar. `lugares` las renombra la primera vez que se
  piden; si ya estaban las dos, no toca ninguna.
- `install.sh` saca la instalación vieja. El prefijo lo lee del lanzador viejo,
  que lo lleva escrito, y antes de borrar comprueba que adentro esté
  `src/asbridge`.

**Lo que falló**: la primera corrida de los tests después de agregar la
mudanza **mudó las carpetas de verdad**. `primera-escritura.py` pide la
carpeta de respaldos al importarse, y `salvaguardas.py` lo importa. No se
perdió nada —es un `rename`, y se comprobó que estaban los dos archivos de
configuración, `al-abrir.json` y los 24 respaldos—, pero una prueba no puede
tocar el HOME de quien la corre. Desde entonces los cuatro archivos de tests
arrancan con `XDG_CONFIG_HOME` y `XDG_STATE_HOME` en una carpeta temporal, y
se comprobó que después de las cuatro corridas las carpetas `asbridge` seguían
en su lugar.

**Aparte**: la prueba de interfaz "quedarse con la tasa prestada" falla a
veces (`volver pide []`). Pasa lo mismo sobre el commit de antes del cambio de
nombre (3 de 4 corridas), así que no viene de acá. Queda abierta.

---

## "Quedarse con la tasa" le ganaba a la lectura

Sigue a "El proyecto pasa a llamarse LinShark", que dejó abierta la prueba
intermitente. **No era la prueba: era la ventana.**

`Hardware.quedarse_con_la_tasa()` cambiaba la sesión **desde el hilo de la
ventana**, y `_leer_estado()` no tomaba el candado. La prueba aprieta
"quedarse" apenas aparece el cartel, y el cartel aparece al bajar la tasa,
antes de que termine la lectura. Una traza de los estados que llegan a la
ventana lo mostró: en la corrida que falla, el **primero** llega sin
`tasa_bajada_desde`, y la ventana lo anota como la lectura de al abrir con
1000 Hz como tasa del dueño. "Volver a como estaba" ya no tenía los 8000. Le
podía pasar a cualquiera que apretara el botón justo cuando termina la lectura.

El arreglo: la lectura toma el candado, como las escrituras y la devolución de
la tasa, y "quedarse" va por el hilo del hardware bajo el mismo candado.
Emite el estado antes que la tasa, así cuando el cartel se va la ventana ya
sabe. Cuánto se debía llega por la señal `tasa_elegida`. Con la traza: 12 de
12, contra 1 de cada 2 antes. La suite de interfaz entera, tres de tres.

---

## Un byte de tasa que no se entiende dejaba a la ventana afuera

La ventana abría el dongle y a los dos segundos decía "el mouse no contesto la
lectura del comando que se iba a escribir". Ni había una escritura en juego ni
el mouse se había callado.

**Lo que se midió**, todo por el dongle:

```
sondear.py --leer 6      04 06 c0 01 00 cb                              aceptado, a 0.01 s
                         04 0e 00 06 09 01 02 fd 00 00 00 00 01 21      la respuesta, a 0.71 s
cambiar-rate.py          byte 0x02  (respaldos/rate-20261004T175826.json)
medir-polling.py 15 s    76066 muestras, mediana 126 us: 7944 Hz
```

El bloque es `01 02 fd 00 00 00 00`: **nibble alto 0**, que no es ninguno de los
siete índices, con el complemento bien puesto (`0xFF ^ 0x02 = 0xfd`). No es un
sangrado —eso trae un complemento que no cierra, ver "Dos agujeros que
aparecieron al cerrar lo que quedaba de A"—: es lo que el mouse tenía guardado,
leído tres veces igual.

**Por qué se veía como un mouse mudo.** `report_rate_de()` devuelve `None` para
un índice que no conoce, `tasa_actual()` devuelve `None` también cuando el mouse
no contesta, y `Configuracion.preparar()` trataba los dos igual, con el motivo
`no-contesto`, cuyo texto es el del paso 2 de la Etapa 3. La primera lectura de
este incidente —"el mouse está dormido o en otro modo", deducida de que el
fallo llegaba en dos segundos— fue del asistente y estaba mal: es la trampa de
siempre, culpar al enlace antes de mirar la trama.

**Quién escribió `0x02` no se sabe.** El codificador del dongle no puede:
pone siempre el nibble alto entre 1 y 7. Es de la misma familia que el `0x01`
que la página oficial escribió en `web-rueda-orden-web.pcap` —el índice como
byte entero—, y hasta ahí llega lo que se puede decir.

**Y no cierra qué frecuencia deja un índice 0.** El mouse reportaba a 8000 Hz
con `0x02`, pero 8000 era ya la tasa de su dueño en la última lectura guardada,
dos días antes. "Índice 0 es 8000" y "índice 0 no se aplica y queda la que
había" dan lo mismo con lo que hay.

**La salida, a mano:**

```
cambiar-rate.py --valor 8000
  04 0e 00 06 09 01 72 8d 00 00 00 00 01 21
  intento 1/4: 0xC1, quedó en byte 0x02
  intento 2/4: 0xC1, quedó en 8000 Hz (byte 0x72)
medir-polling.py 10 s    48954 muestras, mediana 126 us: 7944 Hz
```

`0x72` no está en `RATE_BYTES_EN_EL_BUS` —sale de respetar el nibble bajo, que
valía 2— y el mouse lo aceptó. El primer intento es otro caso del dongle
acusando `0xC1` sin que el mouse aplique.

Después la ventana leyó el mouse entero, prestando la tasa como siempre. Esa
lectura contra la de dos días antes difiere **solo** en el nibble bajo del rate
(`0x44` -> `0x42`, y lo mismo embebido en el perfil): dpi, luz y botones,
iguales byte a byte. Lo que haya escrito el `0x02` no tocó nada más.

**Lo que cambió en el programa.**

- `preparar()` separa los dos casos: `sin-tasa` si el mouse no contesta ni el
  bloque corto, y ya no `no-contesto`.
- Una tasa ilegible **se arregla y se sigue leyendo** (`Configuracion.
  _arreglar_la_tasa()`): un mouse con un byte raro no puede dejar al programa
  afuera. Es el camino de un solo comando —escribir, releer, insistir— con el
  bloque de `estructuras.arreglar_report_rate()`, que **no** respeta el nibble
  bajo: sale siempre un byte de `RATE_BYTES_EN_EL_BUS`. Por el dongle es
  `0x44`, o sea la escritura de rate del driver oficial byte a byte; por cable
  se conserva el nibble alto si es un índice (`0x70` -> `0x74`).
- **Queda en 1000 Hz y no vuelve**, porque no hay una tasa anterior que
  devolver. Se dice en pantalla (`AVISO_TASA_ARREGLADA`, con el byte que había)
  y el bloque que se pisó viaja en el estado (`tasa_arreglada_desde`), así que
  queda en `al-abrir.json`.
- No arregla una lectura cuyo complemento no cierra —eso es una lectura mala, no
  un byte guardado— ni nada si quien llama no dio el permiso entero. En esos
  casos, y si la escritura no entra, el motivo es `tasa-ilegible`.

Lo cuida `test_una_tasa_ilegible_no_deja_al_programa_afuera`, con los bytes de
este incidente.

**Lo que NO está medido**: el arreglo automático contra el hardware. Sus dos
mitades sí —la trama de `0x44` es la del driver oficial y se escribió muchas
veces; escribir la tasa encima de un bloque con `0x02` es lo que hizo
`cambiar-rate.py` acá arriba— pero las dos juntas corrieron solo contra el
mouse de mentira. Para medirlo haría falta dejar el mouse otra vez con un byte
ilegible, y eso es escribir un byte que ninguna captura muestra.

**El CLI no cambió**: `primera-escritura.py` con una tasa ilegible sigue de
largo y falla en el respaldo si el mouse está rápido. Ahí la salida sigue
siendo `cambiar-rate.py`.

**Aparte**: `sondear.py` rotula las tramas corridas un byte. Mostró el acuse
`0xC0` como "report rate sub=192" y la respuesta de cmd 6 como "cmd 14 sub=0".
Queda abierto.
