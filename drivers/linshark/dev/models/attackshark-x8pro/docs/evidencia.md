# Qué se sabe, y cómo se sabe

Este documento existe para que alguien que no participó del trabajo pueda
revisarlo **sin tener que confiar en nada**. Cada afirmación del proyecto está
clasificada por cómo se sabe, y con cómo volver a verificarla.

Es el documento de evidencia, no un informe de auditoría: no registra hallazgos
de nadie, registra el estado epistémico de lo que el proyecto afirma. El método
de trabajo está en [`metodo.md`](../../../docs/metodo.md), el protocolo en
[`protocolo.md`](protocolo.md) y lo que se probó contra el hardware —incluido
lo que no funcionó— en [`bitacora.md`](bitacora.md).

El trabajo se hizo sobre una VivoBook con CachyOS, Hyprland y un Attack Shark
X8 Pro conectado por su dongle de 2.4 GHz.

---

## 1. Qué es esto y por qué existe

El X8 Pro se configura con un "web driver" en <https://szslxd-tech.com/#/>.
Esa web **no usa WebHID**: es solo la interfaz, y todo el acceso al mouse lo
hace un demonio nativo que escucha en `ws://localhost:10086`, del que solo
existen builds para Windows y macOS. Este proyecto empezó reemplazando ese
demonio y hoy apunta a una aplicación propia, por una razón medida: **el
cliente oficial no puede releer su propio estado sin corromperlo** (ver I-W24
en la tabla de MEDIDO).

**Estado.** Las lecturas funcionan de punta a punta: los siete
comandos que el mouse contesta están decodificados. Las escrituras están
habilitadas para los **cinco** comandos de `p.WRITABLE` —rate (6), dpi y los
interruptores del sensor (4), los temporizadores y el color (5), botones (8) y
macros (9)— detrás de las siete barandas de [`metodo.md`](../../../docs/metodo.md), y los
cinco tienen la Etapa 3 cumplida contra el hardware.

**Dos campos entraron con la Etapa 2 cumplida y la 3 pendiente**:
el atajo de teclado de un botón (código 17) y la lista de eventos de un macro.
Etapa 2 quiere decir que el bloque que armamos es byte a byte el que el driver
oficial mandó al bus; que el mouse los ejecute no está medido todavía, y se
mide apretando el botón.

Por el puente solo se exponen rate y dpi; el resto se opera con
`driver/scripts/primera-escritura.py`, que habla con `device.py` directo. Es una
baranda, no un desfase: por el puente quien escribe es la página oficial.

Lo que queda sin codificador **no es trabajo de código, es falta de captura**:
`dpi_ON_OFF_flag`, los ocho colores de indicador, `Dpi_indication_type` y
`lightMode` son constantes en las 76 escrituras capturadas de cmd 4 y cmd 5.

---

## 2. Clasificacion de las afirmaciones

Tres niveles:

- **[MEDIDO]** — comprobado contra el hardware o el binario, con salida
  concreta. Deberia poder reproducirse.
- **[LEIDO]** — transcripcion directa de codigo de terceros (el bundle JS o
  el desensamblado). Verificable releyendo la fuente, pero es lectura de
  codigo, no ejecucion.
- **[INFERIDO]** — razonamiento sobre lo anterior, sin confirmacion directa.
  **Es donde hay que mirar con mas atencion.**

### Lo que esta MEDIDO

| Afirmacion | Como verificarlo |
| ---------- | ---------------- |
| La web necesita un helper en `ws://localhost:10086`; no hay build de Linux | `grep -r "10086" dev/research/webapp/app.js`; la vista `webHid` redirige a `myapp://WebDriver` y ofrece `.exe` y `.pkg` |
| Brave abre `ws://localhost` desde una pagina HTTPS sin flags | `./linshark` y abrir la web; log en `bitacora.md` |
| El canal de configuracion es la interfaz 2 del dongle, `Report ID 4`, 63 bytes | `hardware.md`; `driver/scripts/sondear.py` lo encuentra recorriendo sysfs |
| El mouse manda notificaciones solo por `Report ID 3` | `driver/scripts/sondear.py --escuchar 20` y apretar el boton de DPI |
| La trama lleva checksum = suma de todos los bytes anteriores, **incluido el Report ID** | `python3 -c "from linshark.protocol import build_read_frame; ..."` — reproduce byte por byte el paquete del binario |
| Se leen del mouse: version, report rate, dpi, iluminacion, botones, perfil | `driver/scripts/sondear.py --pedir 11 --pedir 6 --pedir 4 --pedir 5 --pedir 8 --pedir 10` |
| El enlace 2.4 GHz pierde pedidos: 95% con el mouse en movimiento, 50% quieto | `dev/herramientas/medir-enlace.py --segundos 45` |
| La tasa de reporte real, y que se puede cambiar desde Linux | `driver/scripts/medir-polling.py --segundos 15`, que lee `/dev/input/eventN` y no habla el protocolo. Midio 8004, 1001 y 500 Hz en los tres estados por los que paso el mouse |
| El byte de report rate: el **nibble alto** es el indice de frecuencia, `125 * 2^(n-1)` | Barrida anotada de los siete valores con el soft oficial (`capturas-w/soft-rates-anotados.txt`), la barrida independiente de la web en `web-todo.pcap`, y la escritura desde Linux de 1000 a 500 Hz con el efecto medido |
| La trama con la que Linux bajo el rate a 500 Hz **ya la habia mandado el driver oficial** | `capturas-w/w2soft-rate-outs.txt`, capturada: `040e0006090134cb000000000121`. Es byte a byte la que se escribio. No se dedujo del mapeo de nibbles: ya estaba en el bus, que es la forma fuerte de cumplir la regla del proyecto |
| Una escritura desde Linux cambia lo que tiene que cambiar, y nada mas | `dev/models/attackshark-x8pro/respaldos/antes-de-escribir-rate-20260908T190938.json` contra su `despues-`: dos bytes distintos en todo el mouse, los mismos dos en report rate y en perfil completo, que lo embebe |
| **El perfil completo (cmd 10) acompaña a todo cambio de dpi, luz, tasa y botones** | Verificado sobre los **139 respaldos versionados**, comparando pares consecutivos: 95 pares con alguna diferencia; cambio solo dpi 28/28, solo luz 19/19, solo rate 2/2, solo botones 17/17; **0** falsos positivos (el perfil solo) y **0** falsos negativos (algo se movio y el perfil no). Es la base de la relectura acotada del paso 6, y lo rehace `test_el_perfil_acompaña_a_todo_cambio` en cada tanda. **No cubre los macros**: viven en `estado["macros"]` y ningun par los movio aislados, asi que no hay medicion sobre ellos |
| A 8000 Hz **no se puede leer el mouse entero**: el respaldo de los siete comandos no se completa | Tres corridas de `driver/scripts/respaldar.py` con el mouse a 8 kHz: 3/7, 5/7 y 3/7 comandos. El dongle contesta `0xC3` ocupado y el mouse puede quedarse sin responder unos segundos. Pasaron siempre los tres comandos cortos -version, rate, iluminacion- y fallaron los largos; **las escrituras si pasan** (fila "A 8 kHz el mouse SI acepta escrituras", mas abajo). Ver `bitacora.md` |
| El soft oficial reescribe el perfil entero aunque se toque un solo control | `capturas-w/soft-rate-8000-a-1000.pcap`: cinco Interrupt OUT seguidos (`0x0c`, dpi, luz, rate, botones), las cinco identicas a `build_write_frame()`. El puente **no** replica eso: manda solo el comando permitido |
| La pagina oficial **lee** el dpi del X8 Pro con la tabla dispersa del 3311 y lo **escribe** con la formula lineal `Pu()` | Leido del bundle: `getSensorType()` mapea `X8Pro: "3311"` y `parseDpiSettings()` llama a `convertBytesToDpi3311()`; para escribir hay seis usos de `Pu(`. Y visto en vivo: con los bytes `1f 2f 3f 6f 9f 8f` la pantalla mostro 1350/2000/2700/4750/6800/24400 (la tabla) y la pagina, al conectarse, los reescribio como `1a 27 35 5e 87 e7`, que es `Pu()` de esos mismos seis. La aplicacion del fabricante se contradice sola |
| El layout de la estructura de dpi | Tres anclas sobre la misma captura: los ocho colores de nivel dan los defaults del bundle, `dpi_ON_OFF_flag` da 63, y los `Dpi_X_setting` decodificados dan los seis DPI de arriba. `python3 driver/tests/salvaguardas.py` |
| El framing de ESCRITURA, byte a byte | `bitacora.md`: la trama que el driver oficial le escribe al mouse para el report rate es `04 0e 00 06 09 01 44 bb 00 00 00 00 01 21`, y `build_write_frame()` la reproduce **identica**. Confirmado por dos capturas independientes (web y soft nativo) |
| El bloque de dpi que escribe el soft oficial es el mismo que leemos por hidraw | `01 01 01 3f 20 00 17 2f 3f 6f 9f 8f`, identico en la captura de Windows y en la lectura de `driver/scripts/sondear.py` |
| El checksum interno de las estructuras: es la suma de `datos[1:fin_de_campos]`, o sea sin el `profileId` y sin la cola | `estructuras.checksum_interno()`. Verificado contra **61 tramas** de dpi e iluminacion de las capturas del driver oficial, web y soft, con valores distintos: las 61 traen exactamente esa suma. Hasta la funcion sumaba el bloque entero y no daba ese numero en ningun caso |
| El codificador de escritura de dpi reproduce lo que hace el driver oficial | Dos formas, las dos en `driver/tests/salvaguardas.py`: reescribirle a cada uno de los seis niveles el valor que ya tiene reproduce el bloque byte a byte (incluido el nivel 6, que usa la otra rama de `Pu()`), y el cambio de 4750 a 4800 que hizo la pagina en `web-todo.pcap` se reproduce identico a partir del bloque anterior |
| El latido espontáneo (Report ID 3) tiene dos cadencias metronómicas | `driver/scripts/medir-hibernacion.py`: 2.00 s con el mouse recién usado (±0.01 s) y 4.00 s tras ~32.8 s de quietud ininterrumpida. El payload despierto es constante (`03 08 40 01 56`) |
| La hibernación **detiene el latido espontáneo** y el corte sigue `30 s + N·60 s` | Palanca de 10× en `mediciones/`: N=1 cortó en [88.0, 92.0] s (predicho 90); N=10 en [628.9, 632.9] s (predicho 630, corrida de 960 s anclada). Descarta el modelo paralelo (600 s) y el N·90. Lo medido es que **el latido para**; que la radio se apague del todo es la lectura natural, no una medición |
| El byte 7 de cmd 5 **gobierna el escalon del latido**: con 0.5 min el salto de 2.00 a 4.00 s cae en (32.75, 36.75) s de quietud y con 1.0 min en (63.55, 67.55) | Dos corridas ancladas, `mediciones/…T215337` y `…T215919`. Y con el reposo en 1, el corte se fue a [119.8, 123.8] s: los timers estan **anidados** (`T_reposo + N·60`), sin preambulo fijo |
| **El LOD cambia la altura de corte del sensor** | A/B **a altura constante**: con el LOD en 2 mm se levanto el mouse hasta ~2 mm y seguia rastreando; **sin bajarlo**, se bajo el ajuste a 1 mm y dejo de moverse. El ajuste fue la unica variable, asi que el efecto es del campo y no de la altura. Las escrituras, con `0xC1` y relectura, movieron solo `SensitivityX` y el checksum. **Lo que queda fuera**: los ~2 mm son a ojo, no con galga, asi que esta medido el **efecto del campo**, no el valor absoluto del corte de cada ajuste |
| Los cuatro interruptores de sensor de cmd 4 se movieron en el bus | **10 pares distintos** de (SensitivityX, SensitivityY) entre las capturas, con los cuatro bits en los dos estados, y **tres transiciones que difieren solo en esos dos bytes**. `escribir_parametros_sensor()` las reproduce byte a byte en las dos direcciones (`test_escribir_parametros_sensor`) |
| El byte 7 de cmd 5 es un campo propio, toma 1, 2 y 12 en el bus, y se mueve aparte de la hibernacion | `soft-todo.pcap`: el soft nativo lo llevo 1 → 12 → 1 mientras la hibernacion de los nibbles iba 10 → 25 → 10 por separado. `escribir_reposo_ligero()` convierte una trama real del driver en la otra byte a byte, en las dos direcciones (`test_escribir_reposo_ligero`). Que ese campo sea el reposo ligero es LEIDO del bundle (`hibernateTime = sleepTime/2`); que sea el termino de 30 s del corte es INFERIDO, ver la inferencia 10 |
| Los bytes de color RGB de cmd 5 se escriben y se releen sin encender nada visible | Escritura ida y vuelta (verde ↔ azul) con acuse `0xC1` y relectura exitosa, sin ningun LED visible. **Que sean inertes NO esta probado** (I-W16, abierto): todo lo observado fue con `lightMode: 0`, y no se zanja sin escribir ese campo, que es el ambiguo de I-W14 |
| El layout de cmd 8 (botones): `profileId` + **18 slots de 3 bytes** + checksum | El constructor `_fe()` de `app.js` escribe `[8, 59, profileId]` y despues tripletas; el mouse devuelve 57 B = 1 + 18·3 + 2, que es `sizeTotalData - 2`. Con 17 o 19 slots no cierra. El checksum interno, calculado desde la tabla, cae exactamente en `[55:57]` en los **44 respaldos** y en los **15 bloques del bus**. `test_botones` |
| **La notificacion de cambio de dpi son 3 bytes, no 4 — y por eso nunca la decodificamos** | `driver/scripts/sondear.py --escuchar 20` ciclando el dpi con su boton: llegaron `08 10 02` y `08 10 03`, de **3 bytes de cuerpo**, contra los 4 de la presencia (`08 40 01 34`) en la misma corrida. `sondear.py` no recorta nada: imprime el cuerpo tal cual, y el cuerpo es `data[1:5]`, o sea que el Input Report entero son 4 bytes contra los 5 de la presencia. **El `00` final que `protocol.py` tenia documentado (`08 10 03 00`) era LEIDO del bundle** -donde el helper reenvia 6 bytes al navegador- y nunca se habia mirado el reporte crudo. Consecuencia: `sesion.novedad_de()` y `backend._on_estado_mouse()` arrancan los dos con `if len(datos) < 4: return`, asi que **tiran todas las notificaciones de dpi**. El aviso "el mouse cambio de nivel, relee" y el tirado del cache que `AGENTS.md` da por hechos **no funcionaron nunca** contra el hardware. Los tests no lo agarraron porque alimentan `08100300`, la forma del bundle: el decodificador y su test se escribieron desde la misma lectura y coincidian en estar mal. **Son dos notificaciones de una sola corrida**: falta repetirlo para darlo por cerrado |
| **El slot 4 es el boton fisico del costado-atras** | con el mismo metodo que cerro el slot 7: se lo remapeo a `18 00 00` (codigo 24, "reproducir / pausar"), se lo apreto -**la musica se pauso**- y se lo devolvio a `05 00 00` ("atras"). Verificacion externa: el que conto fue el reproductor del sistema. La trama ademas confirma el remapeo de escritura una vez mas: el `18` salio en la **posicion 5** del bloque, que es donde `SLOT_ESCRITO_DE_LEIDO` manda el slot leido 4. Con esto **los siete slots quedan cerrados**: 5, 6 y 7 medidos apretando, 4 medido aca, 17 y 18 girando la rueda, y 1-2-3 por el bloque de fabrica, que para el clic izquierdo, el derecho y el de rueda no tiene lectura alternativa |
| **El slot 7 es el boton fisico de modo de conexion, y ese boton hace DOS cosas a la vez** | desde la aplicacion: se remapeo el slot 7 a `18 00 00` (codigo 24, "reproducir / pausar") y despues se apreto el boton del mouse para pasarlo a **modo USB**. Pasaron las dos cosas juntas: **la musica se pauso** y **el mouse se desconecto** del dongle. La verificacion es externa -el que conto fue el reproductor del sistema, no nuestro decodificador- y ademas no hay otro camino por el que ese byte pudiera haber pausado nada. Deja dos hechos: (1) el slot 7 **es** ese boton, que hasta aca era el mas flojo de los siete -salia de la asignacion de fabrica y nunca se habia apretado-; (2) el cambio de canal **no es la funcion del slot**: es del firmware y sigue pasando con cualquier funcion encima. Por eso el codigo 60 (`FUN_MODE_KEY`) de fabrica es, en la practica, "no mandes nada extra". **Lo que NO esta medido**: cuantos modos cicla, en que orden, ni si el codigo 60 hace algo ademas de callar |
| Las siete funciones que el mouse trae asignadas de fabrica | Decodificadas con la tabla `Rve` del bundle: clic izquierdo, derecho, rueda, atras, adelante, ciclo de dpi y tecla de modo, mas nueve slots apagados y los dos de la rueda. Si la estructura se corriera un byte, ninguna daria |
| **Los dos clientes oficiales escriben los slots 17 y 18 de la rueda al reves uno del otro** | sobre el bus: 13 bloques del soft nativo con `slot 17 = 0x0a, slot 18 = 0x09` y 3 de la pagina web con `0x09, 0x0a`, sin una sola excepcion y con los otros 16 slots iguales. Los dos son **escrituras**, asi que la comparacion es directa. El bloque con el que la web cierra su captura -con el usuario devolviendo todo a fabrica- queda distinto del de fabrica **exactamente en esos dos bytes**. **Los dos ordenes quedaron MEDIDOS, girando la rueda**: con `0a, 09` el scroll anda derecho y con `09, 0a` -que es lo que la pagina escribe con solo abrirla y guardar- queda invertido. No son bytes inertes: la pagina rompe la rueda al conectarse |
| **Ningun cliente oficial lee los botones del mouse** | Los 15 bloques de cmd 8 que hay en `capturas-w/` van en direccion OUT; cero en IN. Y no es que falten lecturas: `web-arranque-dpi-y-rate.pcap` trae la respuesta del mouse para luz y para dpi al conectarse la pagina, y ahi no aparece ningun bloque de botones. Los dos clientes escriben este comando desde su propio estado guardado y nunca lo releen |
| **El soft nativo tambien pisa el dpi al tocar cualquier control** | se abrio el soft solo para remapear un boton y el nivel 1 de dpi volvio de **1600** -escrito desde Linux- a **1200**, el de fabrica. Es I-W12 con el otro cliente, y la consecuencia medida de que el soft reescriba el perfil entero |
| **Al abrirse, el soft nativo pisa tres campos, no uno: el dpi, el angle snapping y el tiempo de respuesta** | `respaldos/antes-de-escribir-dpi-20260912T190235.json` contra `respaldos/antes-de-escribir-rate-20260913T134004.json`, sin ninguna escritura del proyecto entre los dos y con una visita al soft en el medio: el nivel 1 de dpi `1f -> 17` (1600 -> 1200), `SensitivityY` `1 -> 17` (angle snapping OFF -> ON) y `direction` `18 -> 8` (tiempo de respuesta). El reposo y el color quedaron igual: no es un restablecer. Tambien cambio `Current_Dpi_level_flag` `5 -> 1`, que **no se le atribuye al soft**: el nivel en uso se mueve con el boton del mouse. Bitacora, "De paso: el soft nativo piso tres campos, no uno" |
| **Con la rueda en `0a, 09` el scroll anda derecho** | girandola. Es la segunda verificacion a simple vista del proyecto despues del LOD. Y esos dos slots **no se remapean**: el soft escribe `0a, 09` y el mouse devuelve `0a, 09`; si se intercambiaran se leeria `09, 0a` |
| **Los slots 4, 5 y 6 de cmd 8 se remapean entre escritura y lectura** | A/B directo, misma sesion: escritura capturada (`0d 05 06`) a las 17:21:05 y lectura (`05 06 0d`) a las 17:22:58, con los otros quince slots identicos. `escrito[4]->leido[6]`, `escrito[5]->leido[4]`, `escrito[6]->leido[5]`. `test_botones` lo fija byte a byte |
| Los usage IDs de los botones del mouse dentro de un macro | `app.js` los declara 241..245 (`LeftMouseButton`, `RightClick`, `MouseWheelClick`, `MouseForward`, `MouseBack`) y un macro grabado a mano con el soft nativo los guarda como `f1 f3 f5 f4 f2`, que se lee izquierdo, rueda, atras, adelante, derecho: el orden en que se apretaron. Dos fuentes independientes, bundle web y archivo del soft de Windows |
| La tabla de funciones de boton se valida desde una **tercera** fuente | Los `pro.data` del soft nativo guardan registros de 10 bytes `[indice, codigo, 0*6, 0x32, 0x02]` cuyos codigos son los mismos de `FUNCIONES_DE_BOTON`: clic izquierdo, derecho, rueda, adelante, atras, ciclo de perfil, tilt. Ni el bundle ni el bus |
| El acuse `0xC1` no se pierde durante las pausas de reintento/ocupado | `_dormir_salvo_evento()` en `device.py` (fix N-H04), asegurado con pruebas de regresión en `driver/tests/salvaguardas.py` |
| **Al mouse le llegan macros de 111 bytes, no de 131** | sobre el bus: `soft-macro-asignado.pcap` trae cuatro escrituras de cmd 9 y las cuatro miden 111, en el layout de la familia de `Qve`. El chunk del X8 Pro importa `Zve` (131), pero quien escribio fue el **soft nativo**, que no es el bundle: que la pagina mande 131 sigue LEIDO y sin capturar. El bloque va **partido en dos tramas** (59 + 52, con el numero de bloque donde iria el opcode) y `build_write_blocks()` -transcripcion del desensamblado que nunca se habia podido contrastar- reproduce las cuatro identicas |
| **El byte `[3]` del bloque de macro es el modo de disparo, y toma 0, 1 y 2** | cuatro escrituras del soft con el mismo macro y el mismo boton en las que **lo unico que cambio fue ese byte** (0 → 1 → 2 → 0), con el checksum interno acompanando. Cual valor es cual sale del bundle y no del orden en que se toco la UI: los cuatro constructores hacen `n===0 ? setUint8(7,a) : setUint8(7,1)`, o sea que el modo 0 es el unico que usa el contador de repeticiones, y es el unico de los tres con campo numerico en la UI |
| El tiempo de los eventos de macro va en **milisegundos** | El `.macro` del soft guarda retardos de 10 ms (dword LE) y en el bus el byte es `0x0a`. Con la formula de `Zve` -decimas de segundo- 10 ms viajaria como 1. Un solo valor, pero separa las dos ramas |
| **La pagina oficial reescribe TODO lo que leyo, y CAMBIADO** | `web-rueda-orden-web.pcap`, con el usuario tocando **un** boton. La pagina leyo tres bloques y escribio cinco, y los tres que leyo los escribio distintos: cmd 4 con `SensitivityX 0x01 -> 0x00` (**ripple ON -> OFF**) y los dos `Double_Flag` intercambiados (`20 00 -> 00 20`, que mueve el nivel 6); cmd 5 con reposo 0.5 -> 1 min, respuesta 18 -> 8 y el color de verde a azul; cmd 6 con el byte de rate `0x44` (1000 Hz) -> `0x01`. Cmd 7 y cmd 8 los escribio **sin haberlos leido nunca**, el de botones con la rueda invertida |
| **Y para los interruptores el usuario no puede enterarse** | En la misma captura, la UI de la pagina mostraria "ripple ON" **antes y despues** de apagarlo, porque lee `SensitivityY === 1` en vez del bit que escribe. Es I-W24 y la inferencia 13, las dos con captura |
| El byte de report rate puede tomar valores fuera de la familia observada | En la misma captura la pagina escribio `0x01`, indice 0, que no esta en `RATE_HZ` (los siete observados son `0x14`..`0x74` del soft y `0x11`..`0x77` de la web). **Que frecuencia deja no se sabe**: poco despues el mouse midio 8000 Hz, pero entre medio hubo un "restaurar valores por defecto" y los dos eventos no se pueden separar con lo que hay |
| **El mouse guarda y devuelve un byte de rate con el nibble alto en 0**, y sigue andando | 2026-10-04, por el dongle: cmd 6 devolvio `01 02 fd 00 00 00 00` tres veces (`sondear.py --leer 6` y dos `cambiar-rate.py`), con el complemento bien puesto, y `medir-polling.py` dio 7944 Hz de mediana sobre 76066 muestras. **No dice que frecuencia deja un indice 0**: 8000 ya era la tasa del mouse en la lectura guardada de dos dias antes. Quien escribio el `0x02`, no se sabe. Bitacora, "Un byte de tasa que no se entiende dejaba a la ventana afuera" |
| **Sobre un byte de rate ilegible se puede escribir una tasa, y el mouse la aplica** | Misma sesion: `cambiar-rate.py --valor 8000` mando `04 0e 00 06 09 01 72 8d 00 00 00 00 01 21`; el primer intento volvio con `0xC1` y la relectura en `0x02`, el segundo quedo en `0x72`, y el cronometro dio 7944 Hz. `0x72` no esta en ninguna captura del driver oficial. Despues la ventana leyo el mouse entero, y contra la lectura de dos dias antes difiere **solo** en el nibble bajo del rate |
| **La lectura de cmd 9 lleva el id del macro en el byte 5, no el perfil** | con el perfil el mouse devuelve `01` y 108 bytes de `0xff`; con el id `0x11` devuelve el bloque entero. Sale de `sendMacroDataCommand(macroId)` del bundle y quedo comprobado contra el hardware. Descarta ademas que el bloque vuelva vacio por falta de macro: la lectura anterior se hizo con el macro **asignado a un boton** y volvio igual |
| **El bloque de macro leido es el de escritura, con el checksum interno invertido** | los 111 bytes coinciden byte a byte con lo que el soft nativo escribe, salvo los dos ultimos -`0c 6d` al escribir, `6d 0c` al leer-. La suma es la misma. Es una rareza de cmd 9: cmd 4, cmd 5 y cmd 8 devuelven el suyo en el mismo orden en que se escribe, que es lo que hace posible comparar una lectura contra una escritura en `test_etapa2_ida_y_vuelta` y `test_etapa2_botones` |
| **El camino multi-bloque funciona contra el hardware** | dos escrituras de cmd 9 desde Linux, partidas en 59 + 52. El dongle acuso `0xC1` **despues de la segunda trama** en las dos, que es el modelo que salia de `soft-macro-asignado.pcap`; si hubiera acusado despues de la primera, el modelo estaba mal. Primera vez que el proyecto manda un bloque partido |
| **Las tres escrituras del dia son las del driver oficial, byte a byte** | los hex que imprimio el CLI coinciden **identicos** con las constantes que `driver/tests/salvaguardas.py` levanto de las capturas del soft nativo -`MACRO_OFICIAL[0]`, `BOTONES_OFICIAL_MACRO` y `MACRO_OFICIAL[2]`-. No una trama equivalente: la **misma** trama |
| **La escritura idempotente de cmd 9 no mueve un byte, y el bloque que se manda no es el que se leyo** | `SIN DIFERENCIAS` en los siete bloques y en el macro, con el bloque enviado difiriendo del leido en los dos bytes del checksum (`6d 0c` -> `0c 6d`). La baranda de cmd 9 queda probada contra el hardware y no solo contra la captura |
| **El modo de disparo del macro se escribe** | `--modo 2` sobre el macro 17; la relectura lo devuelve en modo 2 y el diff del paso 6 tiene **una sola linea**, el byte `[3]` con su checksum (`0c6d` -> `0c6f`). **Lo que esta medido aca es que el mouse lo guardo**; que el modo 2 *haga* "mantener apretado" se midio apretando el boton esa noche, en la fila de abajo |
| **La permutacion de slots de cmd 8, por segunda vez** | se escribio `12 00 11` en el slot **escrito 6** y el mouse lo devolvio en el **leido 5**, sin mover ninguno de los otros diecisiete. Segunda confirmacion contra el hardware de `SLOT_ESCRITO_DE_LEIDO` |
| **El modo 2 del macro es "mantener apretado"** | con el macro 17 en modo 2 asignado al costado-adelante, manteniendo el boton apretado el macro se repitio **ocho veces seguidas** y al soltarlo se corto. Es verificacion **externa**: el macro incluye un clic de rueda y en X11 eso pega la seleccion primaria, asi que cada vuelta dejo una copia del texto y el conteo lo hizo el sistema operativo, no nuestro decodificador. Con esto la Etapa 3 de cmd 9 queda cumplida. **No** esta medida la duracion -la estimacion fue a ojo y no cierra con los ~100 ms por vuelta que dan diez eventos de 10 ms-, |
| **El `0xC1` es del dongle y no dice nada del mouse** | el dongle acuso **veinte tramas mal armadas** -un bloque de dpi de 14 bytes, tamaño que no existe- sin protestar una sola vez, y el firmware las descarto todas. Le alcanza con que la trama cierre: Report ID, largo coherente y checksum bueno. Lo unico que dice que el mouse aplico algo es la relectura, que es el paso 6 de la Etapa 3 |
| **A 8 kHz el mouse SI acepta escrituras: lo que falla son las lecturas largas** | midiendo `soft-rate-8000-a-1000.pcap` entera. La tasa en el bus, sobre los huecos entre reportes de movimiento: **7825 Hz antes** de la escritura del rate y **1000 Hz despues** (huecos de 1000 us clavados), o sea que la captura muestra el cambio en vivo con el mouse de verdad a 8 kHz. Y la escritura recibio sus dos acuses, `0xC0` y `0xC1`, igual que las otras cuatro de esa captura. Encaja con la tabla: a 8 kHz pasan los tres comandos cortos y fallan los largos. Una lectura trae el bloque entero **desde** el mouse, que es la direccion que carga el trafico de movimiento; una escritura va en la otra y solo vuelve un acuse de seis bytes |
| **El mouse no manda nada cuando esta quieto** | Misma captura: 34 silencios de mas de 50 ms que suman **19.9 s de 34.0 s**, el 58% del tiempo. Cuando manda, manda a su tasa nominal. El trafico de radio existe solo mientras el mouse se mueve, asi que la instruccion "move el mouse" -medida y cierta a 1000 Hz- puede ser contraproducente a 8 kHz. Nunca se probo leer a 8 kHz con el mouse quieto |
| **El driver oficial no lee nada para reconfigurar** | Misma captura: cinco escrituras, cero lecturas, una por segundo (1.01 s entre tramas, la misma pausa que usa para los macros). Escribe su estado completo desde su base de datos local. Por eso no le molesta que a 8 kHz las lecturas fallen: no las hace |
| **El driver oficial escribe `Current_Dpi_level_flag` con seis valores** | sobre las 53 escrituras de cmd 4 que hay en `capturas-w/`: toma 1, 2, 3, 4, 5 y 6, que es toda la barrida de los niveles encendidos. Y hay **86 pares que difieren solo en ese byte y en el checksum interno**, varios dentro de la misma captura y con segundos de diferencia -`soft-todo.pcap` manda nivel 3 a t+862.96 y nivel 1 a t+865.24-. `escribir_nivel_activo()` convierte una en la otra en las dos direcciones (`test_escribir_nivel_activo`). **Etapa 3 cumplida**: escrito 1 -> 2 y 5 -> 1 desde Linux, con el LED tomando el color del nivel pedido en las dos |
| **Los ocho colores de indicador son de verdad los colores del LED de nivel** | mirando el mouse: con `Current_Dpi_level_flag` en 2 el indicador se puso **verde** (`00ff00` en el bloque), con 5 estaba **turquesa** (`00ffff`) y con 1 volvio a **rojo** (`ff0000`). Tres niveles, tres colores, los tres como dice el bloque. Hasta ese dia la tabla estaba **LEIDA** -los valores coincidian con los defaults del bundle-; ahora esta medida en tres de los ocho puntos. Es el unico LED que prende en este modelo |
| **El firmware escribe `Current_Dpi_level_flag` por su cuenta, y es el mismo byte** | entre dos corridas, con el mouse solo y ningun cliente conectado, se ciclo el dpi con el boton y el respaldo siguiente leyo el campo en 5 -coincidiendo con el turquesa que se veia-. Comparando los dos respaldos, el firmware movio **ese campo y solo ese** (mas su checksum). Es la primera vez que el proyecto verifica un campo dejando que **el mouse lo escriba** y leyendolo nosotros, en vez de al reves: el firmware es ahi un lector y escritor independiente de todo nuestro codigo y del de szslxd-tech |
| **El boton de ciclo de dpi hace lo que la tabla de funciones dice** | Mismo experimento: el slot leido 6 tiene la funcion `0d`, que en la tabla de 61 funciones del bundle es "ciclo de dpi", y apretarlo movio el nivel. Un punto mas de esa tabla, confirmado contra el hardware |
| **Cuatro campos de configuracion son constantes en TODAS las capturas** | mismo recuento: `dpi_ON_OFF_flag` = `0x3f`, los ocho `Dpi_level_N_indication_flag` con sus colores por defecto y `Dpi_indication_type` = 2 en las 53 escrituras de cmd 4; `lightMode` = 0 en las 23 de cmd 5. Ningun cliente oficial los movio nunca delante de una captura, asi que **no hay Etapa 2 posible** y no tienen codificador. No es que falte codigo: falta captura. Para los colores se sabe ademas **por que**: la web no puede tocarlos -su serializador acepta un array de ocho colores y ninguna llamada se lo pasa- y el que si puede es el soft nativo, ver la fila de LEIDO |
| **Y el modo 0 es "reproducir N veces", con el A/B mas limpio del proyecto** | con el macro ya en modo 0 y todavia asignado al mismo boton, manteniendolo apretado salio **una sola copia y paro**, contra las ocho en bucle del modo 2 minutos antes. Misma accion fisica, mismo macro, mismo boton: la unica variable fue el byte `[3]`. La condicion no depende de la memoria de nadie -la prueba cae por fuerza en la ventana entre las dos corridas de la vuelta atras, 17:11:43 y 17:12:02, la unica en que el macro estuvo asignado **y** en modo 0-. El modo **1** sigue sin verificacion externa |
| **La lista de eventos de un macro se arma byte a byte como la del bus** | Etapa 2 sin hardware: dandole al codificador los diez eventos del macro capturado -los cinco botones, apretados y soltados, 10 ms cada uno- sale el bloque de 111 bytes **identico** al que el soft nativo le escribio al mouse, con su checksum interno, y las dos tramas que van al dongle salen identicas a las cuatro escrituras de `soft-macro-asignado.pcap`. Y al reves: devolverle los eventos que `parametros_de_macro()` leyo reproduce el bloque tal cual, que es la escritura idempotente. **Y la Etapa 3 se cumplio**, apretando el boton: ver las filas de abajo. `test_etapa2_eventos_de_macro` |
| **El atajo de teclado se escribe como lo escribe el soft nativo** | Etapa 2 sin hardware: `soft-todo.pcap` tiene dos escrituras consecutivas de cmd 8 que cambian **un solo slot** cada una -`17 00 00` -> `11 08 07` (Win+D) y `02 00 00` -> `11 0a 16` (Win+Shift+S)-, y aplicarle nuestro codificador al bloque anterior da el siguiente byte a byte, checksum interno incluido. Ademas las **veinte** entradas con codigo 17 de la tabla `sl` del bundle se reproducen desde su texto (`ctrl+c` -> `(1, 6)`, `alt+f4` -> `(4, 61)`, `win+shift+s` -> `(10, 22)`). **Y la Etapa 3 se cumplio**, apretando el boton: ver las filas de abajo. `test_etapa2_atajo` |
| **El codificador de eventos de macro se ejecuta en el mouse — Etapa 3** | se escribio desde Linux `clic-rueda:dir0@10, clic-rueda:dir1@10` —un macro de dos eventos que **ninguna captura contiene**— con el macro 17 asignado al costado-adelante y en modo 0, y al apretar el boton el mouse **pego la seleccion primaria una vez por apretada**. Verificacion externa: el pegado lo hace X11 al recibir el clic de rueda, no nuestro decodificador. Y despues con una tecla: `a:dir0@10, a:dir1@10` escribio una `a`, tanto en un editor como en una terminal, con otra cosa en el portapapeles —o sea que era una tecla y no un pegado— |
| **Una tecla de teclado dentro de un macro se codifica como dice el bundle** | Mismo dia, y hacia falta medirlo aparte: los diez eventos de la unica captura de macro son los **cinco botones del mouse** (241..245), asi que el usage 4 para la `a` salia solo del bundle. Al separarlo del resto de las variables, la tecla sale. Los dos espacios de usage de `MACRO_USAGE_BOTONES` y la tabla de teclas conviven en un macro como el bundle dice |
| **`dir0` aprieta y `dir1` suelta** | se escribio `a:dir0@10, b:dir0@10` —los dos eventos en la misma direccion, ninguno de cierre— y al apretar el boton salio `abbbbbbbb...`. Que salgan caracteres dice que `dir0` aprieta; que queden apretadas, que `dir1` es lo unico que suelta. Cierra el punto 16 de las inferencias, que resulto correcto |
| **Un macro de UN SOLO evento no se reproduce** | probado en las dos direcciones (`a:dir0@10` y `a:dir1@10`), con el macro asignado y en modo 0: el mouse **guarda** el bloque —la relectura lo devuelve con su checksum bien— y al apretar el boton no pasa nada. Con dos eventos sale. **La causa no se sabe**: lo medido es el umbral entre uno y dos, no la regla. Es ademas lo que invalido el experimento que `evidencia.md` proponia para cerrar la direccion, que era justamente de un evento |
| **El firmware no suelta nada al terminar el macro** | Misma corrida: la `a` y la `b` quedaron apretadas despues de que el macro terminara. Y el remedio no es el obvio: **apretar la tecla en el teclado fisico no la despega** —el sistema ya la tiene por apretada, asi que la pulsacion real no genera un caracter nuevo— y hubo que **desacoplar el dongle**. De aca sale `eventos_sin_cerrar()` y que su aviso salga **antes** de confirmar la escritura |
| **El atajo de teclado llega al sistema como teclas de verdad — Etapa 3** | con el slot `11 01 06` (ctrl+c) escrito desde Linux en el costado-adelante, apretar el boton copia en un editor **y** manda SIGINT en una terminal. Las dos cosas a la vez descartan que sea un pegado o que lo interprete una sola aplicacion. Es la primera combinacion escrita que **no** esta en ninguna captura: las dos del bus son `11 08 07` y `11 0a 16` |
| **El byte de estado de bateria: `3` es cargando y `1` es a bateria** | dos corridas de `driver/scripts/sondear.py --escuchar` poniendo y sacando un cargador externo: cuatro transiciones, cada una siguiendo al cargador, con el enlace vivo de los dos lados —el nivel se seguia leyendo— y **el LED morado de carga** confirmandolo por fuera del protocolo. El `2` del bundle (`BATTERY_UNKNOWN`) **no aparecio nunca**, ni el `0`, asi que `sesion.Novedad.cargando` da None para cualquier valor que no sea 1 o 3. Que manda con la bateria llena tampoco se midio: es una corrida de horas |
| **El clic izquierdo se reasigna — Etapa 3** | y es la primera escritura del slot 1 que sale de este proyecto: se intercambiaron los botones 1 y 2 en una sola escritura, se volvieron a intercambiar, y la baranda `SinClicIzquierdo` no dejo quitar el unico clic izquierdo. Verificacion externa: el boton fisico. **La fuente es la confirmacion de quien corrio las tres pruebas** de `SIGUIENTE-SESION.md`; en esta entrada no hay bytes ni salidas pegadas, a diferencia de las de arriba |
| **La tasa se cambia desde la aplicacion y se queda** | se puso la tasa desde la ventana, se cerro, y el mouse quedo en la tasa nueva —no en la que la sesion habia prestado—. Es el punto 2 de la lista, el unico que la corrida no habia cubierto. Misma fuente que la fila anterior |
| **Una rafaga larga disparada sola no traba el puntero** | con "volver a como estaba": varios campos cambiados a mano y devueltos en una rafaga, con **una** bajada de tasa y **una** devolucion. El riesgo estaba MEDIDO al reves —seis tramas de rate en tres segundos dejaron el mouse sin mover el puntero— y no volvio a pasar. Misma fuente |
| **Desconfigurar el dispositivo USB del cable NO devuelve el mouse a 2.4 GHz** | con el mouse cargando por cable y el dongle puesto, `echo 0 > /sys/bus/usb/devices/1-4/authorized` -que desconfigura el dispositivo sin cortarle la corriente, el puerto sigue dando VBUS- y `driver/scripts/sondear.py --escuchar 20` devolvio **0 reports**. Y ademas **el mouse dejo de andar**: sin enumeracion no hay camino por cable, y a la radio no volvio. Con `authorized=1` volvio a funcionar por cable. O sea que la conmutacion a modo USB **no depende de la enumeracion**: alcanza con que el conector tenga corriente y datos. Volver a 2.4 GHz sin tocar el mouse no tiene camino conocido |
| **Con el mouse enchufado por cable a la PC no llega ni un latido por el dongle** | Misma corrida: 32 s sin un solo Report ID 3, entre dos tramos que latian cada 2,00 s. Y cargo en el hueco —volvio con 75% contra 72%—, asi que el mouse no se apago: dejo de hablar por radio. Es la medicion del consejo que `hardware.md` daba por prudencia, y tiene consecuencia para la interfaz: **el dongle sigue en el bus y no hay ninguna desconexion que mostrar**, simplemente dejan de llegar novedades. Que *conmute a modo cable* es la lectura razonable; lo medido es el silencio |
| **Por cable, el mouse no contesta un `GET_REPORT(Feature)` pedido en frio** | `dev/herramientas/leer-por-cable.py` en JSJUANPCL1, mouse por cable en el puerto 1-4: los ocho reports que el helper lee (4, 5, 6, 8, 9, 10, 11 y 12) dieron `ETIMEDOUT`, y la corrida tardo 41 s, o sea los 5 s del timeout de control de `usbhid` cada uno. El mouse **no contesto la etapa de datos**; no la rechazo, que seria un STALL y `EPIPE`. Queda en `dev/models/attackshark-x8pro/respaldos/cable-primera-lectura.json`. **Por que no contesta es INFERIDO**: el helper nunca hace un `GET` sin mandar antes el pedido por el report `0xA0` (LEIDO, `0x40e380`), y eso es lo que falto. Lo confirma la captura |
| **Por cable se lee y se escribe como dice el helper, y nuestros codificadores dan lo que escribio el soft nativo** | Seis capturas del soft nativo configurando por cable (`capturas-w/cable-soft-*.pcap`, JSJUANPCL1 con la VM JSJUANPC1W; se llamaron `cable-web-*` por el comando, y el usuario aclaro que abrio el soft. Lo confirma el bus: la rueda escrita en `0a, 09` y el rate `0x73` con los nibbles distintos son del soft). Que el helper y el soft, dos programas sin codigo en comun, armen el mismo pedido es lo que vuelve fuerte al LEIDO. El pedido `0xA0` sale identico a `build_cable_read_request()` para rate, dpi y luz, y el `GET(0xA0)` vuelve `a0 01`. **Etapa 2 cumplida** desde lo que devolvio el mouse: LOD 2 mm y vuelta, dpi nivel 1 a 500 y vuelta, el costado-adelante a macro 17 y vuelta, y el macro 17 en los tres modos, todo byte a byte (`test_etapa2_cable`). Cada `SET_REPORT` lleva el largo que el mouse declara (52 el dpi), y cada `GET` pide el del helper (56) y el mouse devuelve el bloque entero con su relleno |
| **Por cable, el soft mueve el nibble BAJO del byte de rate** | `cable-soft-rate-500.pcap` y `cable-soft-rate-1000.pcap`: leyo `0x74`, escribio `0x73` para 500 Hz y `0x74` para 1000, con el alto en 7 (8000 por radio). El codificador del dongle habria escrito `0x34`. Y **el efecto tambien esta medido**: ver la fila de abajo |
| **Por cable, el nibble bajo es la tasa del cable** | 2026-09-18, JSJUANPCL1, el mouse enchufado en 1-4: la ventana escribio `06 09 01 73 8c 00 00 00 00` -byte a byte el `SET` del soft para 500 Hz- y `medir-polling.py` por cable dio **2000 us de mediana, 500 Hz** (4982 muestras, 45% en 2000 us y el 99% entre 1750 y 2250). Es verificacion por fuera del protocolo: el cronometro del kernel, no una relectura. La vuelta a 1000 (`...74 8b...`) el mouse la acepto; no se midio con el cronometro |
| **Por cable, el mouse acepta una escritura que la relectura inmediata no muestra** | 2026-09-18, desde la ventana: el LOD a 2 mm (`04 38 01 10 …`, byte a byte el `SET` del soft) y la respuesta a 4 (`05 0f 01 00 03 c8 00 ff 00 01 02 01 cd`) volvieron aceptados, y la relectura completa, que salio a los pocos milisegundos, los mostro sin cambiar. La tasa, releida 1 s despues, si se vio. Por que, esta INFERIDO: ver abajo |
| **Por cable, con 500 ms de respiro despues de escribir, la escritura se ve en la relectura** | 2026-09-18, desde la ventana, la misma escritura que antes no se veia: el LOD a 2 mm (`04 38 01 10 … 0f d1`) se quedo tras la relectura completa, y la vuelta a 1 mm (`04 38 01 00 … 0f c1`) tambien. Es la primera Etapa 3 entera por cable. Lo unico que cambio entre las dos corridas fue la espera |
| **Por cable se lee el macro, con el pedido LEIDO del helper** | 2026-09-18, `respaldar.py --macro-id 17` por cable (`dev/models/attackshark-x8pro/respaldos/cable-macro-17.json`): con `a0 09 83 00 11 00 00 00` el mouse devolvio el macro 17 -modo 2, sus diez eventos, que es como lo dejo el soft-. **Por cable viene con `sizeTotalData` 0x83**: los 111 bytes del bloque del dongle, con su checksum interno en su lugar y al reves como por el dongle (`6f 0c`), y despues 20 ceros de relleno. El canal lo presenta como el de 111 solo si lo que sobra es cero |
| **Por cable, el mouse acepta el macro en los dos trozos** | 2026-09-18, desde la ventana: el macro 17 en modo 2 con sus diez eventos, dos `SET_FEATURE(9)` de 64 **byte a byte los del soft para el modo 2** (`cable-soft-macros.pcap`), aceptados. **Era lo mismo que el macro ya tenia**, asi que la relectura no puede decir si entro: lo medido es el camino, no el efecto. Un cambio real de macro por cable -otro modo, otros eventos- no se corrio |
| **Por cable se reasigna un boton** | 2026-09-18, desde la ventana: el clic derecho a la funcion 7, a la `0x27` y de vuelta a 3, tres escrituras de cmd 8 (59 B, en el formato de escritura, como las del soft por cable), cada una aceptada y releida; el usuario vio el cambio y la vuelta en la ventana. En la misma corrida, el `GET` ajeno del rate se volvio a pedir solo |
| **Por cable, el mouse manda el Report ID 3 del boton de dpi** | 2026-09-18, con la ventana abierta por cable: el usuario apreto el boton de dpi y la ventana mostro el aviso con el nivel al que cambio. El descriptor del cable lo declaraba (4 bytes, Usage Page 0x0A); ahora esta visto llegar |
| **Por cable se escribe la luz** | 2026-09-18: la respuesta a 4 desde la ventana, y se quedo. No hay captura del soft escribiendo la luz por cable: es el bloque del dongle cortado al largo del descriptor (13), y la relectura lo confirma |
| **Por cable se escriben los tres interruptores** | 2026-09-18, desde la ventana: ripple, angle snapping y motion sync, encendidos y apagados, seis escrituras de cmd 4. Cada una sale armada **desde la relectura de la anterior**, y en sus bytes 3 y 4 se ve que la anterior habia entrado (`01 01` → `01 11` → `01 10` → `00 10` → `00 00` → `00 01`) |
| **Con el cable enchufado a la PC, manda el cable aunque el boton de modo diga 2.4 GHz** | 2026-09-18, el usuario: con el cable puesto, el mouse prioriza la conexion USB aunque el boton de modo este en dongle |
| **Por cable, un `GET` puede devolver el bloque de otro comando** | La misma corrida, al abrir: el `GET(6)` del rate volvio con el bloque de la version (`0x0b`), que era el pedido anterior. El canal lo rechazo por no ser del comando pedido. Volvio a pasar dos veces mas -el rate con la version, los botones con el dpi- y el canal lo volvio a pedir solo |
| **Por cable contestan los pedidos de lectura LEIDOS del helper: version, botones y perfil completo** | `respaldar.py` por cable (`dev/models/attackshark-x8pro/respaldos/cable-primer-respaldo.json`): los seis bloques del respaldo, con el pedido `0xA0` de `build_cable_read_request()`. Version (`080083010100`) y botones (57 B) salen **byte a byte iguales** que por el dongle en `despues-de-escribir-botones-20260914T163311.json`; el perfil completo trae 126 B como por el dongle -aunque el descriptor del cable declare 8- y difiere solo en los bytes que embeben rate, dpi y luz, que cambiaron desde entonces. Lo que embebe coincide con los bloques leidos en la misma corrida: la luz, por ejemplo, va como `03 c8 00 ff 00 01 04` en los dos |
| **Por cable, el mouse rechaza a veces un `SET_REPORT`, y repetirlo funciona** | En las mismas capturas: 6 de 19 pedidos volvieron con STALL (`EPIPE`), y los seis se repitieron identicos entre 201 y 209 ms despues y pasaron. Quien reintenta -el soft, Windows o QEMU- no se sabe; lo medido es el bus |
| **El canal por cable sangra: un `GET` devuelve el bloque ANTERIOR** | 2026-09-20, `medir-sangrado.py`, tres corridas de 240 pedidos: **1 a 2.5%** de los pedidos devuelven otro bloque. Con los pares registrados (pedido + lo que volvio), **6 de 6 eran el bloque del pedido anterior** y ninguno otra cosa. Los reintentos lo tapan entero: **ningun bloque perdido en 720 pedidos** |
| **El sangrado conserva el byte 0 del bloque pedido** | La misma sesion: pedido cmd 6 volvio `01 00 83 01 01 00 00` -el `01` del rate con el payload de la version detras-. Y el incidente de cmd 5 tiene la misma forma: `01 74 8b 00 00 00 00` + ceros, con el `01` propio. Por eso el detector compara **desde el byte 1** |
| **Una lectura sangrada puede pasar el filtro del byte 0** | 2026-09-20: pedido cmd 5 volvio el payload entero de cmd 6 **con el byte 0 en `0x05`**. Paso el unico filtro que habia, un codificador le cambio su byte y le **recalculo el checksum**, y salio al mouse: el cmd 5 quedo con hibernacion 128 min y respuesta 0, y `aplicar()` devolvio `ok=True`. El checksum interno del bloque leido era lo unico que no cerraba |
| **El checksum interno distingue un bloque bueno de uno sangrado** | Sobre los **125 respaldos versionados**: en cmd 4, 5 y 8 cierra en **375 de 375** bloques y falla **solo** en el corrompido. Cero falsos positivos sobre toda la evidencia que hay |
| **El perfil completo embebe a rate, dpi, luz y botones en offsets fijos** | Sobre los **126 respaldos** con los cinco bloques: `rate perfil[1:3]`, `dpi perfil[3:50]`, `luz perfil[53:61]`, `botones perfil[62:117]`, cada uno igual en los 126 y tomando entre 3 y 14 valores distintos. El unico que discrepa es la lectura sangrada. Es lo que cubre a cmd 10, que no tiene checksum interno |
| **Por cable se configura TODO, con Etapa 3** | 2026-09-20: dpi de cada nivel, nivel en uso, rueda, reposo e hibernacion, ida y vuelta cada uno, y el mouse termino **sin una sola diferencia** contra la linea de base. Se suman a la tasa, el LOD, los botones, la respuesta y los tres interruptores, ya medidos el 2026-09-18 |
| **Por cable, una mutacion real del macro entra** | 2026-09-20: el modo del macro 17 paso de 2 a 0 y la relectura lo devolvio cambiado. La corrida anterior (2026-09-18) no habia podido mostrarlo porque escribio el mismo contenido que el macro ya tenia |
| **La ventana se entera de los cambios de bus** | 2026-09-20, con la ventana abierta: desenchufar el dongle (`el dispositivo desaparecio`), enchufarlo en **otro puerto** (se reabrio sola, sin reiniciar) y enchufar el cable con el dongle puesto (paso al cable). El usuario confirmo que en las tres quedo bien reconocido en pantalla |
| **Un macro de TRES eventos si se reproduce** | 2026-09-20: `a:dir0@10, a:dir1@10, a:dir1@10` asignado al costado-adelante, con el foco en un editor, salieron las `a` mientras se mantuvo apretado. Tres es impar, asi que **la paridad no es la regla** del macro de un solo evento, que sigue sin explicacion |
| **El modo 1 del macro lo detiene otro boton del MOUSE, no una tecla** | 2026-09-20, cuatro corridas iguales: se dispara al apretar y **sigue despues de soltar**; una tecla del teclado **no** lo detiene -se escribe esa tecla y el macro sigue saliendo entremedio-; lo detiene apretar cualquier otro boton del mouse. El bundle lo llama `StopOnAnyKey`, asi que **el nombre del fabricante no describe lo que hace el firmware** |
| **Por cable el LED es morado fijo** | 2026-09-20, el usuario: no sigue el color del nivel de dpi. Por el dongle el color del LED **si** es el testigo independiente del nivel en uso; por cable no sirve, y ahi la verificacion es la relectura o el boton de ciclo de dpi |

### Lo que esta LEIDO

| Afirmacion | Fuente |
| ---------- | ------ |
| Formato de los mensajes WebSocket en los dos sentidos | `dev/research/webapp/app.js`, store de Pinia. Citas en `protocolo.md` |
| La tabla de `sub` por comando | Desensamblado, 8 sitios de `hid_write` con `push 0xc` |
| El byte 5 es el numero de perfil y va 1-based | `mov al,[ebp+0x8]; inc al` en los sitios de lectura |
| `rateRadio`: 1=125Hz … 7=8000Hz | `dev/research/webapp/chunks/indexX8Pro-*.js`, opciones del radio |
| **La pagina del X8 Pro deja remapear el boton 1**, con una confirmacion | `dev/research/webapp/chunks/indexX8Pro-*.js`: cuando el boton elegido es el 1 pide `ModifyLeftKeyWarning` ("Modificar el botón izquierdo puede impedir clics", `es-*.js`) y, si se acepta, escribe. Ninguna captura muestra esa escritura, asi que **el remapeo del slot 1 no tiene Etapa 2**; la Etapa 3 si, (ver la tabla de arriba) |
| **Otros clientes del fabricante exigen que quede un clic izquierdo** | `dev/research/webapp/chunks/zh-*.js`: `AtLeastOneButtonMustBeLeftClick: "至少一个按键功能为“Left Click”!"`. Es la regla que el proyecto adopta, limitada a los botones 1 a 5; vive en `dispositivos.Perfil.slots_para_clic_izquierdo`, porque en que botones se puede usar comodo un clic depende del chasis |
| **Por cable el mouse declara 25 Feature Reports, con los numeros de los comandos** | Descriptor HID de la interfaz 2 de `1d57:2126`, leido de sysfs (`hardware.md`, y los bytes en `dev/tests/evidencia.py`). Usage Page 0x0B, ids `0x04`..`0x2E`. **Cuatro de nueve miden lo mismo que por el dongle** (rate, modo de despertado, botones, version) y cinco no (dpi, luz, macro, perfil, el 12), y hay quince ids que el dongle no usa —tres de 132 y uno de 131, que es el tamaño del macro que arma la **web**—. Que los tamaños coincidan no prueba que el layout sea el mismo: **para escribir por cable falta la Etapa 2**, o sea capturar al driver oficial hablando por ese camino. Dpi y luz miden distinto por el relleno: ver la inferencia 19 |
| **La web configura el X8 Pro por cable, a traves del helper** | `WebDriver.exe`: la enumeracion de `0x4115a8` junta lo de 1d57 que no sea un dongle y tenga colecciones en las Usage Pages 0x0B y 0x0A —las del cable— como `connectionMethod` 0x80; `app.js`: `setWiredDevice` incluye `8: "X8Pro"`. **Corrige** lo que decian `SIGUIENTE-SESION.md` y la bitacora ("el cliente web no habla por cable", porque el bundle no usa `sendFeatureReport`): era una inferencia por ausencia, y la pagina no le habla a ningun HID |
| **Por cable, leer es un pedido por el report `0xA0` y despues el bloque; escribir, el bloque como Feature Report** | `WebDriver.exe`: `0x40e380` manda `[a0, cmd, sub, 00, perfil, 00, 00, 00]` y espera `01` en el byte 1 del `GET_FEATURE(0xA0)`; cada llamador hace `GET_FEATURE(cmd, sub)` y le pasa el buffer tal cual a la pagina (`0x412730`); la rama 0x80 de `0x40cf10` escribe con `hid_send_feature_report(h, payload, payload[1])`. O sea que el report es `[cmd, sizeTotalData, perfil, campos..., checksum interno]`. Tabla de llamadores en `protocolo.md`, "El canal por CABLE". **Lo que no dice**: que largo pone Windows en el cable |
| **El modo de conexion no viaja en el paquete del mouse** | El cliente oficial tiene `connectionMethod` (128 cable, 129 inalambrico, 130-131 cable 8K, 132 bluetooth) y **lo pone su helper**: en el paquete de 6 o 7 bytes que le pasa a la pagina, ese byte va **adelante** y los cuatro del mouse (`deviceId`, `0x40`/`0x41`, estado y nivel de bateria) van atras. El propio bundle lo confirma por descarte: valida `n[0] >= 128 && n[0] <= 133` y ademas exige que el byte de tipo sea 64 o 65, que es el nuestro. O sea que **por donde esta conectado el mouse se sabe por el bus USB, no preguntandole al mouse** — que es lo que hace `linshark.conexiones` |
| **Ningun cliente oficial cambia el canal de conexion por software** | Se busco en el bundle entero: lo unico con "Mode" que se le escribe al mouse es el **modo de despertado** (cmd 7, `sendWakeupModeReadCommand`), que es otra cosa, y `setSwitches*` son los interruptores del sensor. No hay `switchMode`, `setChannel` ni nada que mande un comando de canal. Con el cable enchufado el mouse conmuta solo, y **volver a 2.4 GHz no tiene camino conocido por software**, ni para el cliente oficial |
| Los nombres de las funciones de boton que ve quien elige | Etiquetas `label` de la tabla `sl` de `app.js` y sus traducciones en `es-*.js`, `en-*.js` y `zh-*.js`; lo que hace cada una entre parentesis sale de esas etiquetas y de `Rve`. En 56, 57, 50 y 58 el bundle no dice que hacen, y los nombres (`modelo.NOMBRES_DE_FUNCION`) no lo inventan |
| `Level1SleepTimer` (0.5..30 min) y `SleepTimer` (1..60 min) | `chunks/indexX8Pro-BTVvPdTw.js`: el primero oculto (`display: none`), serializado en byte 7 (`closeTime * 2`); el segundo en nibbles altos de bytes 2 y 3 |
| `KeyResponseTime` (4..50, **unidad INFERIDA**, ver inferencia 11) viaja en byte 8 dividido por 2 | `chunks/indexX8Pro-BTVvPdTw.js`: slider `responseTime`, guardado en campo `direction` |
| Interruptores de sensor en cmd 4: LOD, ripple, snapping, sync | `chunks/indexX8Pro-BTVvPdTw.js`: `SensitivityX = (lod<<4)\|ripple` y `SensitivityY = (snapping<<4)\|sync`. Los nombres salen del template: el radio de `sensitivityX`, bajo el header `SilentHeight`, declara `value:0 → "1 MM"` y `value:1 → "2 MM"` |
| **La pagina oficial lee mal esos cuatro campos en el X8 Pro** | `app.js`: el modelo cae en la rama `else`, que hace `straightLine = sensitivityX === 1` y `ripple = sensitivityY === 1` — compara el byte **entero** contra 1, con los campos **cruzados**, y nunca lee de vuelta el LOD ni el motion sync. Con el bloque de fabrica (`01 01`) muestra "angle snapping ON" y el byte dice OFF. Tercer caso del mismo patron, despues del dpi (I-W10) y del nibble de rate |
| El algoritmo de DPI del sensor 3311 | `convertBytesToDpi3311()` en `app.js`, transcripto en `driver/src/linshark/dpi.py` |
| El helper antepone `[connectionMethod, 0x01]` a las notificaciones | Cadenas de formato del binario, una por metodo de conexion: `"8301%02x%02x%02x%02x%02x"` en VA `0x60ac0c`, usada en `0x410a89`. La del bluetooth (`"8401%02x%02x%02x%02x"`) tiene un `%02x` menos, que es justo la variante de 6 bytes que la pagina solo acepta para 0x84 |
| El paquete de desconexion es `[connectionMethod, 0x00, deviceId]` | `"8300%02x"` y sus cinco hermanas (VA `0x60aa7c`), usadas en `0x40c06c` con el campo `[esi+0x418]` del dispositivo |
| El byte que llamamos `sub` es el largo del bloque | En `app.js` los constructores lo escriben como `e.sizeTotalData` y calculan `const t = e.sizeTotalData + 5`. Los objetos `gw` (luz) y `Qt` (dpi) traen `fixed: 5 / sizeTotalData: 15` y `fixed: 4 / sizeTotalData: 56`, que son los mismos valores que la tabla sacada del binario (`0x0F` y `0x38`) |
| La tabla de funciones de boton, codigo por codigo | `app.js`: `Rve` (codigo -> nombre, 0..58, exportada como `ag` y usada por el chunk del X8 Pro con `ae[q(codigo)]`, donde `q = e => parseInt(e)`) y `sl` (nombre -> tripleta `[codigo, p1, p2]`, 61 funciones). Transcripta en `estructuras.FUNCIONES_DE_BOTON`. **El codigo 60 (`FUN_MODE_KEY`), que el mouse trae de fabrica en el slot 7, esta en `sl` y NO en `Rve`** |
| Que `p1`/`p2` son modificadores y usage HID en los atajos | `sl`: `FUN_SHOW_DESKTOP:[17,8,7]`, `FUN_SCREEN_CAPTURE:[17,10,22]`, `FUN_MACRO:[18,0,id]`. **Y ademas capturado**: `soft-todo.pcap` trae bloques con `11 08 07` y `11 0a 16`, que son esas dos entradas byte a byte |
| **La tabla de teclas: 111 usages HID** | `_w()` en `app.js` declara `keyMap`, con 124 entradas: 111 teclas (`KeyA:{usageId:4}` … `F24:{usageId:115}`), los ocho modificadores en 224..231 y los cinco botones del mouse en 241..245. Son los usages estandar de la pagina 0x07 de HID. Transcripta en `estructuras.TECLAS_HID` -con nombres propios, porque los del bundle son los `event.code` del navegador- y fijada contra la cita literal en `test_teclas_del_bundle`: nuestra tabla cubre **exactamente** esos usages, ni uno mas ni uno menos |
| **El byte de modificadores es el estandar HID, bits 0..3** | Las veinte entradas con codigo 17 de `sl` son atajos conocidos de Windows y **las veinte cierran** con `ctrl=1, shift=2, alt=4, win=8` mas la tabla de usages: `FUN_COPY:[17,1,6]` es Ctrl+C, `FUN_CLOSE_WINDOWS:[17,4,61]` Alt+F4, `FUN_BROWSER_FAVORITES:[17,3,18]` Ctrl+Shift+O, `FUN_SCREEN_CAPTURE:[17,10,22]` Win+Shift+S. Veinte coincidencias independientes sobre cuatro bits. **Los cuatro modificadores derechos del estandar (0x10..0x80) no aparecen en ninguna**, ni en el bus, ni en el dialogo del soft -que ofrece cuatro-, asi que el codificador los rechaza |

| La pagina web armaria macros de **131** bytes donde el soft manda 111 | El chunk del X8 Pro importa `Zve` (`ah as Fe`), que arma 131, y no importa ningun otro constructor. **No esta capturado**: si de verdad le manda 131 al mouse, es el cuarto desacuerdo entre los dos clientes oficiales. Se ve capturando la web mientras asigna un macro |

| **El soft nativo tiene un selector de color de dpi, y la pagina del X8 Pro lo instancia** | `app/res/DpiColorDialog.xml` es un popup de 250x200 con una `ColorPalette` continua, campos **R/G/B numericos** -color arbitrario de 24 bits, no una lista- y dieciseis presets `mouse_dpi_color_1..16`. Que le aparezca a **este** modelo sale del binario: la vtable de `CDpiColorWnd` (`0x4ef7d4`) se referencia desde 36 lugares en **18 pares**, hay 18 modelos, y por RTTI los constructores de las paginas 12, 13 y 14 caen en `0x435444`, `0x440164` y `0x44b444`, con un par dentro del rango de cada una -el de la 13 es `0x44249f`/`0x442a96`-. El X8 Pro es el modelo 13: el soft guardo el macro de este mouse en `ms_13/macro.data`. **PERO el control no aparece en la interfaz**: se lo busco y el soft no le habilita esa opcion para este mouse. Lo que el binario prueba es que la clase de esa pagina **contiene** el codigo que construye el dialogo, no que sea alcanzable; las dieciocho paginas son copias de la misma clase, con los pares de instanciacion espaciados identico. Asi que **no hay hoy ningun cliente oficial que escriba esos bytes**, y sin captura no hay Etapa 2 |

| **El pedido de lectura del macro por cable lleva el id del macro en el byte 4** | `WebDriver.exe`, funcion `0x40f780`: por el dongle pone `[ebx+0x8]` en el byte 5 de `04 0c a0 09 6f ..` (`0x40f81c`) -donde el id esta MEDIDO-, y por cable pasa esa misma variable a `0x40e380` como el byte 4 (`0x40fbcb`). El `GET_FEATURE(9)` pide 131 (`0x40fc07`). Seguido el 2026-09-18; no se vio en el bus |

### Lo que esta INFERIDO — revisar con atencion

(La numeracion se mantiene aunque algun punto se haya cerrado, porque los dos
informes de auditoria citan estos numeros.)

1. ~~**El `connectionMethod` que declaramos (`0x83`).**~~ **CERRADO, ahora
   MEDIDO** por la captura del WebSocket del helper oficial en Windows
   (`bitacora.md`): el paquete de presencia real es
   `83 01 03 08 40 01 64`, o sea que el helper anuncia efectivamente `0x83`.
   Lo que sigue abajo queda como registro de por que se dudaba.

   *(texto original)* Sigue INFERIDO. El valor
   lo elige el usuario con `--conn`. La respuesta de version del mouse trae
   `08 00 83 01 05 00`, con `0x83` en la tercera posicion, y por un rato eso
   se anoto como "el hardware lo dice". **No lo dice**: el `0x83` del prefijo
   lo pusimos nosotros, y el del payload es un campo del firmware que no
   sabemos que significa. Lo unico MEDIDO es que coinciden. Es el mismo tipo
   de falsa confirmacion que el de los DPI (ver seccion 3).

2. ~~Que el helper antepone `[connectionMethod, 0x01]` a las notificaciones.~~
   **PROMOVIDO A [LEIDO].** Estan las cadenas de formato en el binario, una
   por metodo de conexion (`"8301%02x%02x%02x%02x%02x"` en VA `0x60ac0c`,
   usada en `0x410a89`), y la del bluetooth tiene un `%02x` menos, que explica
   por si sola la variante de 6 bytes. Ver la tabla de LEIDO.

3. ~~**Que el helper reenvia `[conn, deviceId, cmd, sub, ...datos]` en las
   respuestas.**~~ **CERRADO, ahora MEDIDO** por la misma captura: la respuesta
   real de version es `83 08 0b 08 08 00 83 01 05 00 00 b5`, o sea
   `[conn, deviceId]` + la trama del mouse desde el byte 3 **incluido su
   checksum**. Ver el hallazgo sobre el largo en `metodo.md`.

   *(texto original)* Parcialmente respaldado: las cadenas `"84%02x0B08%02x%02x"` y
   `"84%02x0C0A%02x%02x%02x%02x"` muestran ese orden exacto, pero son del
   camino de **bluetooth**. Que el camino del dongle arme igual es lo que
   sigue INFERIDO, aunque ahora con bastante mas apoyo.

4. **La tabla de adaptadores** (`ADAPTADORES` en `backend.py`). Hoy solo
   tiene el report rate, justificado contra el handler de la pagina. **Es
   muy probable que falten mas**, y solo se van a ver al tocar pantallas que
   todavia no se probaron.

5. **El comando `0x0c` (sub `0x0a`).** Ya no es un desconocido total: el soft
   nativo lo manda y quedo capturado
   (`04 0f 00 0c 0a 01 fe 01 fe 00 00 00 00 02 27`), o sea que `0x0a` es un
   `sizeTotalData` de 10 y el bloque son dos pares valor+complemento
   (`01 fe`, `01 fe`), el mismo idioma del byte de report rate y de cmd 7. La
   web nunca lo manda. **Que opcion lo dispara sigue sin saberse**, y se
   averigua capturando una por una las opciones que el soft tiene de mas. Ver
   `soft-nativo.md`.

5b. ~~**`Dpi_Y_setting`**, dentro de la estructura de dpi.~~ **CERRADO.**
   No venia todo en cero: trae un `01` en el indice 5, que es
   justo el byte alto que hace falta para que el nivel 6 de 40000 (rama de
   `/100`, con el bit 5 puesto en `DPI_X_Double_Flag`). Si el campo empezara un
   byte antes o despues, ese `01` caeria en el nivel 5 o en el 7 y los seis
   valores no darian lo que muestra la pagina oficial. `CAMPOS_SIN_CONFIRMAR`
   quedo vacio.

6. **El grupo de cadenas `"%02x%02x<CMD>F0"`** (VA `0x60ab94` y vecinas,
   usadas en `0x40e755`, `0x40ed98`, `0x412b0c`, entre otras). Hay una por
   cada uno de los ocho comandos de lectura (`04 05 06 08 09 0A 0B 0C`), se
   formatean con dos argumentos, y **no se sabe que son**. No se les asigno
   ningun significado ni se usan en el codigo: quedan anotadas como pista
   para la fase 2.

7. ~~**El nibble bajo del byte de report rate.**~~ **CERRADO, ahora MEDIDO**
   (2026-09-18), por lo que sigue. El alto quedo MEDIDO. Del
   bajo, **quedo medido quien lo mueve**: el soft nativo, por cable, escribe
   `0x73` para 500 Hz y `0x74` para 1000, con el alto quieto
   (`cable-soft-rate-*.pcap`). Por el dongle el mismo soft lo deja siempre en
   4 y la web lo pisa con el mismo valor que el inalambrico. **CERRADO,
   MEDIDO (2026-09-18)**: el mouse aplica el bajo como su tasa por cable,
   `medir-polling.py` dio 500 Hz con `0x73` escrito (tabla de MEDIDO). El
   puente lo **respeta**: al escribir por el dongle cambia solo el nibble
   alto.

8b. **Cual de las dos formulas corresponde al dpi que hace el sensor.** La
   pagina lee con la tabla y escribe con `Pu()`, y para los mismos bytes las
   dos dan numeros distintos (1350 contra 1600 en el nivel 1; 24400 contra
   40000 en el 6). A favor de la lineal: el X8 Pro se vende como 40000 dpi,
   `M()` del chunk pone `dpi6 = 4e4` al restaurar, y al subir de a 50 desde la
   UI los bytes se mueven de a uno. A favor de la tabla: es lo que se ve en
   pantalla. **Se decide midiendo el desplazamiento real del sensor**, y el
   nivel 6 es donde mas separadas estan las hipotesis (64%).

8. **Si al mouse le da igual como se codifique un mismo dpi.** `Pu()` tiene
   dos ramas y hay valores que salen por las dos: 2000 dpi es `0x27` con el bit
   de rama apagado, y tambien `0x13` con el bit puesto. **El driver oficial usa
   las dos** (`web-todo.pcap`: paso el nivel 1 de 1000 a 2000 encendiendo el
   bit, sin tocar el byte). La UI las muestra igual. Lo que **no** se sabe es
   si el firmware usa ese flag solo como etiqueta o para su propio calculo; si
   fuera lo segundo, dos codificaciones "equivalentes" podrian no mover el
   sensor igual. No se puede decidir desde las capturas. El puente escribe
   siempre la rama que dice `Pu()`.

9. **El nivel seleccionado.** Al cambiar un nivel de dpi, el driver oficial
   mueve ademas `Current_Dpi_level_flag` al nivel tocado. El puente no lo hace
   -cambiar cuanto vale un nivel y cambiar en cual esta el mouse son dos cosas
   distintas- pero eso significa que para dpi **no hay igualdad byte a byte con
   el oficial**, salvo cuando el nivel seleccionado ya coincidia. Es una
   decision, no un hallazgo, y esta anotada aca para que no se lea como lo otro.

10. ~~**El termino constante de 30 s de reposo ligero.**~~ **CERRADO, ahora
    MEDIDO**. Se escribio `--reposo 1.0` (byte 7 = 2) y el escalon
    del latido paso de 32.75 s a 63.55 s de quietud: el byte se duplico y el
    escalon se duplico. Y con el reposo ya en 1, bajar la hibernacion a 1 dio un
    corte en [119.8, 123.8] s, que es el modelo **anidado** (60+60=120) y no el
    de preambulo fijo (30+60=90). Los dos terminos de `corte = T_reposo + N*60`
    quedan verificados moviendolos por separado.

11. **`responseTime` como debounce de botones.** Inferencia basada en el nombre
    `"KeyResponseTime"` y rango 4..50 ms de la UI web. No medible directamente
    por software hidraw.

12. **Inercia total de luces en el chasis.** Confirmada en `lightMode: 0`; queda
    inferido si en otros modos de iluminacion encenderia algun indicador interno.

13. ~~**Que la pagina oficial corrompa los interruptores de sensor al escribir
    un dpi.**~~ **CERRADA, ahora MEDIDA** con
    `capturas-w/web-rueda-orden-web.pcap`. Ver la fila nueva en la tabla
    de MEDIDO: el mouse contesto `SensitivityX = 0x01` y tres segundos despues
    la pagina escribio `0x00`, sin que el usuario tocara ese control.

14. ~~**Que los slots 4, 5 y 6 de cmd 8 no se lean en el orden en que se
    escriben.**~~ **CERRADA, ahora MEDIDO** con un A/B directo:
    `capturas-w/soft-boton4-vuelve-adelante.pcap` tiene la escritura del
    soft a las 17:21:05 con `0d 05 06` en los slots 4-6, y
    `dev/models/attackshark-x8pro/respaldos/20260910-172258.json` la lectura de las 17:22:58 con `05 06 0d`.
    Misma sesion, los otros quince slots identicos, la permutacion se cumple en
    los tres. Lo de abajo queda como registro de como se llego.

    *(texto original)* Que los slots 4, 5 y 6 de cmd 8 no se lean en el orden en
    que se escriben. El soft nativo cerro su captura 16:16 devolviendo
    el mouse a fabrica, y ese bloque lleva `0d 05 06` en los slots 4-6. El
    respaldo de las **16:51 del mismo dia** lee `05 06 0d`: los tres valores
    estan, corridos un lugar. Los 44 respaldos leen siempre lo mismo, incluidos
    los posteriores a la captura. No es una rotacion global: 1, 2 y 3 coinciden.

    **El experimento se hizo** (`dev/models/attackshark-x8pro/respaldos/20260910-161848.json`):
    se remapeo con el soft nativo el boton fisico del costado-adelante a
    "reproducir / pausar" y se leyo desde Linux, sin escribir un byte. Cambio
    **un solo slot, el 5** -de `06` a `18`-, mas el checksum y su reflejo en el
    perfil. Como el soft escribe "adelante" en **su** slot 6, el par
    `escrito 6 -> leido 5` queda confirmado por un boton que se puede apretar,
    sin depender de ninguna tabla:

        escrito 4 (ciclo de dpi) -> leido 6
        escrito 5 (atras)        -> leido 4
        escrito 6 (adelante)     -> leido 5   <- confirmado con el boton fisico

    **Sigue sin ser un A/B directo**: falta la trama de escritura de esa sesion,
    que no se capturo, asi que lo que hay es la escritura del 08 mas esta
    lectura. Pero la alternativa -que no haya remapeo- exige que el soft creyera
    que el costado-adelante es su slot 5, donde el mismo escribe `05` = atras.
    Para cerrarla del todo: repetir el remapeo **con usbmon corriendo**.

    Importo antes de que cmd 8 entrara en `WRITABLE`:
    devolverle al mouse el bloque que se le leyo, tal cual, **le rota tres
    botones**. Fue la primera vez que el proyecto encontro un motivo para no
    tratar una relectura como idempotente, que es con lo que empieza cada
    Etapa 3 —y aparecio la segunda, el checksum invertido de
    cmd 9—. `retraducir_botones()` es la escritura idempotente de este
    comando: devuelve un bloque **distinto** del leido y deja al mouse igual.

15. **La rama larga de los eventos de macro.** Arriba de 127 ms el evento ocupa
    cuatro bytes: el par normal lleva el resto de dividir por 100 y detras va
    `[centenas, 3]`. Sale de `Qve` en `app.js`, que es el constructor del
    layout de 111 bytes -el que le llega a este mouse-, y **ninguna captura lo
    muestra**: en la unica que hay, los diez eventos son de 10 ms.

    Se decodifica igual, y por un motivo concreto: sin eso
    un macro con un solo evento de 250 ms se leia como **dos** eventos, el
    segundo con "usage 3", y eso entra al respaldo. El `3` sirve de marcador
    porque no colisiona con los usage de teclado HID -que empiezan en 4- ni con
    los cinco de los botones del mouse (241..245). `describir()` marca esos
    tiempos con `?` y aclara que salen del bundle.

    Dos matices que quedan adentro de la inferencia: **el byte 8 cuenta pares
    de bytes, no eventos** (`e.length+s`), y **el bit 0 lo fuerza el bundle**
    en tres de los cuatro casos mientras el soft nativo no lo pone nunca, asi
    que un macro escrito por la pagina puede leerse 1 ms corrido. Se cierra
    grabando un macro con un retardo largo desde el soft nativo y capturando.

    **Y tambien se escribe, con una decision anotada**: el
    codificador usa la estructura de cuatro bytes del bundle (INFERIDA) pero
    **no fuerza el bit 0** (que es lo MEDIDO del soft, aunque solo en eventos
    cortos). La consecuencia es concreta y a favor: pedir 350 ms escribe 350,
    mientras el codificador del bundle escribiria 351. No es un hallazgo, es
    una eleccion entre dos clientes que no coinciden, y se eligio el que tiene
    su escritura de macro capturada. `primera-escritura.py` avisa antes de
    confirmar cuando algun evento cae en esta rama.

16. ~~**Cual de los dos bits de direccion es apretar y cual soltar.**~~
    **CERRADO, ahora MEDIDO: `dir0` aprieta y `dir1` suelta.**
    La inferencia resulto correcta.

    Se midio escribiendo `a:dir0@10, b:dir0@10` —los dos eventos en la misma
    direccion, **ninguno de cierre**— con el macro asignado al costado-adelante
    y en modo 0. Al apretar el boton salio `abbbbbbbb...`: la `a` y despues la
    `b`, en el orden en que se escribieron, y la ultima repitiendo. Que salgan
    caracteres dice que `dir0` aprieta; que queden apretadas dice que `dir1` es
    lo unico que suelta.

    **El experimento que este documento proponia no servia, y eso es parte del
    hallazgo.** Decia: "un macro de un solo evento `dir0` sobre una tecla". Se
    corrio, en las dos direcciones, y **no paso nada en ninguna** —ver el punto
    17—, asi que no distinguia. Apilaba sin saberlo una segunda variable que
    ninguna captura habia tocado: una **tecla de teclado** dentro de un macro.
    Los diez eventos de la unica captura son los cinco botones del mouse
    (241..245); el usage 4 sale del bundle. Recien al separar las dos
    variables —primero un par de `clic-rueda`, que es usage atestiguado, y
    despues un par de `a`— la tecla quedo MEDIDA tambien.

    *(texto original)* Cada evento de macro lleva el bit 7 del primer byte
    como direccion, y el proyecto lo muestra como `dir0`/`dir1` desde que lo
    decodifica, a proposito. Lo que hay: el `.macro` del soft guarda una
    direccion por evento (`1 = abajo, 2 = arriba`, ver
    [`soft-nativo.md`](soft-nativo.md)) y el macro del bus manda cada boton dos
    veces, primero **sin** el bit y despues con el, en el orden en que se
    apretaron. De ahi que `dir0` sea "abajo", que es razonable -un boton se
    aprieta antes de soltarse- pero nadie leyo las direcciones de ese archivo
    una por una.

17. **Por que un macro de UN SOLO evento no se reproduce.** Lo MEDIDO es el
    hecho, no la causa: con un evento —probado en las dos
    direcciones, `a:dir0@10` y `a:dir1@10`, con el macro asignado y en modo 0—
    el mouse **guarda** el bloque (la relectura lo devuelve con su checksum
    bien) y al apretar el boton no pasa nada. Con **dos** eventos sale, tanto
    del mismo usage (`a:dir0@10, a:dir1@10`) como de dos distintos
    (`a:dir0@10, b:dir0@10`).

    Lo que no se sabe es la regla: puede ser que el firmware itere de a pares,
    que descarte los macros de largo impar, o cualquier otra cosa. Lo unico
    medido es el umbral entre uno y dos. `MACRO_EVENTOS_MIN_QUE_CORRE` vale 2
    y `primera-escritura.py` avisa antes de confirmar, sin prohibir.

    **La prueba de tres eventos se corrio (2026-09-20) y corre** (tabla de
    MEDIDO): la regla **no es la paridad**. Por que uno solo no corre sigue
    abierto, y no hay a mano otra prueba que lo cierre.

18. **El firmware no suelta nada al terminar el macro** — MEDIDO en la misma
    corrida que el punto 16: la `a` y la `b` quedaron
    apretadas despues de que el macro terminara. Lo que esto tiene de
    inferido es **el alcance**: no se sabe si vale para los cinco botones del
    mouse igual que para las teclas, porque el macro que lo mostro era de
    teclas.

    La consecuencia es operativa y cara: con una tecla trabada, **apretarla en
    el teclado fisico no la despega** —el sistema ya la tiene por apretada, asi
    que la pulsacion real no genera un caracter nuevo— y hubo que **desacoplar
    el dongle**. Por eso `eventos_sin_cerrar()` existe y el aviso sale
    **antes** de confirmar la escritura, no en el consejo posterior.

19. ~~**Que por cable el report sea el bloque del dongle cortado al largo que
    declara el mouse.**~~ **CERRADO, ahora MEDIDO**: en las capturas del cable
    cada `SET_REPORT` lleva exactamente ese largo -52 el dpi, 9 el rate, 59
    los botones- y `build_cable_write_report()` reproduce las escrituras del
    soft byte a byte (tabla de MEDIDO). Lo que queda de esta inferencia es
    el perfil completo (8 por cable, 128 por el dongle) y el 0x0c (6 contra
    10), que el soft no leyo por cable y **siguen sin explicacion**. El
    perfil completo, al menos, contesta por cable con sus 126 bytes (tabla
    de MEDIDO).

20. **Por que la escritura por cable no se vio en la relectura.**
    **La causa es la espera, MEDIDO**: la misma escritura del LOD no se veia
    releyendo a los milisegundos y se vio con 500 ms de respiro (tabla de
    MEDIDO). Lo que sigue INFERIDO es **el mecanismo**. Lo MEDIDO de la primera
    corrida es que el LOD y la respuesta se aceptaron y la relectura inmediata
    no los mostro, y que la tasa, releida 1 s despues, si. La explicacion que se
    tomo es que **un pedido que llega a los milisegundos de una escritura la
    pisa antes de que el mouse la aplique**, por un buffer compartido. Se
    apoya en tres cosas y en ninguna medicion directa: el `Sleep(500)` del
    helper despues de escribir (LEIDO), que el soft nunca manda nada antes de
    ~200 ms de haber escrito (MEDIDO en las capturas), y el `GET(6)` que
    devolvio el bloque de la version (MEDIDO). **Otras explicaciones siguen
    abiertas** -que la escritura se aplique y la lectura por cable devuelva
    otra copia, por ejemplo-. La cierra volver a escribir el LOD con el
    respiro de 500 ms: si ahora la relectura lo muestra, es esto; si no, es
    otra cosa, y el LOD a 2 mm se puede comprobar ademas a simple vista,
    levantando el mouse. **Se corrio y la relectura lo mostro**, asi que la
    otra explicacion -que la escritura se aplicara y la lectura devolviera
    otra copia- queda descartada para este caso: sin la espera, la relectura
    mostraba 1 mm; con ella, 2.

---

## 3. Errores que se cometieron y como se detectaron

Util para un auditor: marca donde el razonamiento fue fragil.

| Error | Como se detecto |
| ----- | --------------- |
| Regla de udev con `ATTRS{}` de dos padres distintos, mas archivo `99-` (tarde para `uaccess`) | `udevadm test`: la regla se leia pero no aparecia en ninguna decision |
| Timeout de reintento (1.4 s) **menor** que el NAK del dongle (2.10 s), lo que hacia que cada reintento cayera encima del pedido anterior y el dongle respondiera `0xC3` ocupado | Aparecieron `06 c3` en el log, que no estaban antes |
| Mandar 0 en el byte de perfil. Falla **en silencio**: el mouse ignora el comando y el sintoma es identico a una perdida de radio | Comparando los templates del binario: en esos comandos el byte 5 venia de un registro, no era constante |
| Decodificar DPI como `(valor+1)*50`. Daba 1200/2400/3200/5600/8000, parecido a los defaults, y eso hizo de falsa confirmacion | Las notificaciones de escritorio de la pagina decian 2000/2700/4750/6800. **Anotado: esta fila envejecio al reves.** `(valor+1)*50` es la rama de `/50` de `Pu()`, o sea que era **correcta**, y 1200/2400/3200/5600/8000 son los valores que hoy estan MEDIDOS. Lo que fallo fue la correccion: se la reemplazo por la tabla del 3311 apoyandose en unas notificaciones que nunca se pudieron reconciliar. Dos falsas confirmaciones seguidas, una en cada direccion |
| Forzar `0x40` en las notificaciones, tirando las de cambio de DPI | La pagina mostraba siempre el nivel 1 aunque el LED cambiara |
| Fuga de canales: `start()` abria otro `/dev/hidraw` sin cerrar el anterior al reconectar | Cada notificacion aparecia dos veces en el log |
| Afirmar que el X8 Pro no estaba en la cadena de cambio de DPI de la pagina | La expresion regular se cortaba en el primer parentesis; si estaba |
| Dar por cerrado que el `0x83` de la respuesta de version confirmaba el connectionMethod. Razonamiento circular: ese prefijo lo poniamos nosotros | Las dos auditorias lo marcaron en paralelo (I-01 y H-13). este documento lo tenia bien como INFERIDO; era la bitacora la que se habia adelantado |
| `driver/scripts/instalar-udev.sh` corria `udevadm trigger` sin `--action=add`, justo la trampa que el propio proyecto documenta en tres archivos | Auditoria de codigo (H-01). El script terminaba con exito aparente y dejaba al usuario sin permisos |
| Dos opciones de las sondas (`--crudo` y `--leer CMD SUB`) permitian mandar bytes arbitrarios al endpoint vendor, o sea justo lo que la regla del proyecto prohibe | Auditoria de codigo (H-04 / I-06 / I-07). Se sacaron |
| El canal se abria `O_RDWR` incluso en modo `listen`: la garantia de "no le escribe nada" dependia solo de un `if` | Auditoria de codigo (H-03). Ahora en `listen` se abre `O_RDONLY` |
| `CMD_WAKEUP` no estaba en `READ_SUB` y `build_read_frame()` levantaba `KeyError` sin capturar, que se llevaba puesta la conexion WebSocket entera | Auditoria de codigo (H-02 / I-05) |
| Descartar la tabla del 3311 para leer, creyendo que la pagina mostraba los valores lineales | **Nunca los mostro.** Se vio abriendo la web con los bytes delante: muestra los de la tabla. La evidencia buena del commit que la descarto era sobre la ESCRITURA, y se extendio a la lectura sin mirar la pantalla. Tercera vez que el dpi engania, y las tres por lo mismo: contrastar contra datos que no separan las alternativas |
| `_adaptar_report_rate()` tomaba el nibble **bajo**. Andaba de casualidad: la web escribe los dos nibbles iguales y el mouse estuvo en `0x44` todas las pruebas. Con cualquier otro estado le decia 1000 Hz a la pagina, siempre | La barrida anotada con el soft, que mueve un solo nibble y separa las dos hipotesis |
| En `leer()`, el futuro donde se deja la respuesta se registraba y se borraba **dentro de cada intento**: durante las pausas de reintento no quedaba nadie esperando, y una respuesta que llegara ahi se descartaba mientras el pedido moria por timeout | Aparecio al fallar los respaldos a 8000 Hz. Otra vez el primer patron de abajo: **se ve identico a "el enlace perdio el pedido"**, y el pedido volvia |
| Afirmar, con dos corridas, que la frontera de los fallos a 8 kHz era el limite del bloque de 64 bytes | La tercera corrida la desmintio: fallaron tambien dos comandos que entran en un bloque solo |
| Afirmar que `hidraw.py` estaba mal al decir ~4 s e imponer 2.00 s ignorando que la medición se hizo con el mouse en uso (I-W20) | Corridas de quietud: a los ~32 s el latido salta metronómicamente a 4.00 s. Las dos afirmaciones eran verdaderas en estados distintos |
| Prometer en `metodo.md` que la luz era "visible a simple vista" sin verificar en el hardware físico (I-W15) | Tras escribir exitosamente el color con acuse `0xC1`, el chasis X8 Pro no encendió ninguna luz visible |
| Mostrar "respuesta 9" en `describir()` cuando la UI oficial muestra 18 (I-W22) | El byte viaja dividido por 2 respecto a los ms de la web; mismo error que el nibble de rate |
| Justificar el rango de `responseTime` con la fórmula `Math.floor(2+23*v/100)` (I-W22) | Dicha fórmula pertenecía en realidad al control `Level1SleepTimer` |
| Perder el acuse `0xC1` en `Device.escribir()` durante pausas de `asyncio.sleep()` (N-H04) | Al llegar el acuse en la pausa, el bucle hacía `continue` y la siguiente vuelta lo borraba con `clear()` antes de evaluarlo. Corregido con `_dormir_salvo_evento()` |
| Tratar a "LOD / parámetros" como un comando bloqueado sin capturas (I-W17) | Eran tres comandos distintos (rate, sensor cmd 4, luz/reposo cmd 5) ya capturados en el repositorio |
| No revisar `soft-nativo.md` antes de teorizar sobre la anomalía de los 90 s de hibernación | Los dos temporizadores (`Sleep Time` y `Deep Sleep Time`) ya estaban identificados en el volcado XML del software nativo |
| Anunciar en el paso 3 que el paso 6 iba a contar una escritura idempotente como fallo, y después contarla | Corriendo el CLI. Una herramienta que predice su propia alarma falsa y la emite igual es peor que una que no avisa: en un proyecto cuya única red son las barandas, gastar una alarma es caro |
| Listar como cambio del mouse una asimetría entre los dos respaldos de una escritura: al asignar un macro aparece solo en el posterior, y al desasignarlo solo en el previo | Corriendo el CLI, las dos veces(12:36 y 17:12). El arreglo de la primera no cubría la segunda. Ahora los dos respaldos se leen con la misma lista de macros |
| Leer cada par de bytes de un macro como un evento, cuando arriba de 127 ms el evento ocupa cuatro | Leyendo `Qve` entero en el bundle. Un macro con un solo evento de 250 ms se veía como dos, el segundo con "usage 3", y eso entra al respaldo |
| Creer que `LightBrightness` y `breathingSpeed` eran campos sin escribir | Contando valores en las capturas: sus "cinco" y "tres" valores distintos son los nibbles del tiempo de hibernación, que ya tenía codificador. Heredar los nombres del fabricante hace ver campos donde hay uno solo |
| Dar por buena una afirmación de la documentación del propio proyecto | `SIGUIENTE-SESION.md` decía que botones y macros no tenían capturas; botones tenía **quince bloques en el bus**. Aparecieron buscando el bloque por contenido en vez de por un layout de trama supuesto |


Dos patrones que se repiten y conviene tener presentes al auditar:

- **Errores de formato disfrazados de problemas de enlace.** El mouse no
  contesta "comando invalido": simplemente no contesta, y el dongle emite el
  mismo NAK que cuando se pierde el paquete.
- **Falsas confirmaciones.** Mas de una vez un resultado "parecia razonable"
  y se acepto sin contrastarlo contra una fuente independiente.

---

## 4. Riesgos

**El riesgo real del proyecto es dejar el mouse ladrillo** mandando bytes al
endpoint vendor y cayendo en un comando de bootloader o de actualizacion de
firmware.

Mitigaciones vigentes:

- Regla del proyecto: **solo se mandan secuencias levantadas literalmente del
  bundle de la web o del binario del helper. Nunca fuzzing.**
- El modo por defecto es `listen`, y ahi el `/dev/hidraw` se abre
  **`O_RDONLY`**: que no salga un byte lo sostiene el kernel, no un `if`.
- El modo `full` existe, pero **no habilita nada por si solo**: `--mode full`
  a secas es un error. Hay que nombrar cada comando con `--permitir-escritura`
  y solo se aceptan los de `WRITABLE` (`rate`, `dpi`, `luz`, `botones` y
  `macro`), que son los que pasaron la Etapa 2. El default es **simulacro**:
  arma la trama y no la manda. La primera escritura real de cada
  sesion pide confirmacion por terminal, y no se escribe con la bateria por
  debajo del 50%. (Nota: en el CLI de `linshark`, `ESCRIBIBLES` expone solo
  `rate` y `dpi`, y hay un test que exige que sea un subconjunto **estricto**;
  `luz`, `botones` y `macro` se operan con `driver/scripts/primera-escritura.py`).
- **Con `full` y `--permitir-escritura dpi`, abrir la pagina oficial le
  reescribe el dpi al mouse sin que nadie toque un control**: la pagina lee con
  una formula y escribe con otra, y "normaliza" el estado al conectarse. Se lo
  vio en vivo, y en `read` quedo bloqueado seis veces seguidas.
  La confirmacion de la primera escritura es lo unico que se interpone.
- **Macros (cmd 9) esta en `WRITABLE` pero el backend lo rechaza igual**, y no
  por falta de Etapa 2: el backend no sabe mandar un bloque partido en varias
  tramas. La prohibicion esta nombrada en `backend.SIN_CAMINO_EN_EL_BACKEND`,
  no delegada a que el armador de tramas se queje por el largo, que dejaria
  pasar un macro corto. **El techo del backend es mas bajo que `WRITABLE`**, y
  hay dos techos mas abajo todavia: `cli.ESCRIBIBLES` y lo que
  `primera-escritura.py` acepta por corrida.
- **El camino de macros es el unico multi-bloque, y tiene una ventana de ~1 s
  en la que el mouse tiene medio bloque.** Un reintento reenvia la secuencia
  entera y nunca el ultimo trozo suelto; el `0xC0` de la primera trama **no es
  un acuse**, el `0xC1` llega despues de la ultima. La pausa entre trozos es la
  del soft nativo (1.008 s, MEDIDA), no el `Sleep(200)` del helper de la web:
  nadie fue mas rapido que un segundo en el bus, asi que no hay medida del
  minimo.
- **La funcion "macro" de un boton lleva el id en `p2`, y escribirla con cero
  deja el boton muerto sin que se note**: el mouse acusa `0xC1` igual porque 18
  es un codigo valido. `escribir_boton()` y el CLI exigen `--macro-id` (N-W19).
- Antes de una escritura real hace falta un respaldo **completo** de los siete
  comandos. `driver/scripts/primera-escritura.py` aborta si falta alguno: un respaldo
  incompleto no sirve como linea de base. Y cuando se escribe un macro, el
  respaldo lo incluye **aunque ningun boton lo apunte**: un macro puede existir
  huerfano -asi esta el `0x11`- y entonces no hay de donde
  deducir su id.
- `build_read_frame()` es el unico camino que arma tramas, y levanta
  `ComandoSinSub` si el comando no tiene `sub` documentado.
- Las sondas de `scripts/` no tienen forma de mandar bytes arbitrarios.
- `--hidraw` verifica contra sysfs que el nodo forzado sea la interfaz 2 del
  **dongle**: el nodo equivalente del mouse por cable existe, se abre sin
  quejarse y habla Feature Reports.
- El servidor solo acepta conexiones cuyo `Origin` sea el del fabricante.
  Escuchar en localhost no es privado: cualquier pagina abierta en otra
  pestana puede abrir `ws://localhost` sin pedir CORS.

`driver/tests/salvaguardas.py` verifica todo eso sin hardware, para que no se caiga
sin que nadie se entere.

Que deberia revisar un auditor:

- Que ningun camino de codigo pueda escribir en modo `listen`.
- Que `build_read_frame()` siga sin aceptar comandos sin `sub` conocido, y que
  nadie haya agregado entradas a `READ_SUB` sin citar de donde salieron.
- Que `WRITABLE` no haya crecido sin que el comando nuevo pase la Etapa 2, y
  que las siete barandas de escritura sigan en pie. `driver/tests/salvaguardas.py` las
  verifica (H-08), y esta escrito para ponerse rojo a proposito si se aflojan.
- Que la regla de udev siga dando acceso **solo a la interfaz 2**. Las
  interfaces 0, 1 y 3 son teclado/mouse/multimedia, y darles acceso de
  usuario permitiria a cualquier proceso leer las pulsaciones de las teclas
  de macro.

---

## 5. Alcance y limites

- Probado **solo** con el dongle de 2.4 GHz (`1d57:fa65`). El modo cable
  (`1d57:2126`) usa un canal distinto —Feature Reports en vez de Output
  Report— y **el codigo no sirve tal cual**.
- Probado solo con un X8 Pro (`deviceId 8`). La web soporta 43 modelos.
- **Las capturas vienen de DOS mouses distintos, y hay que saber cual mira
  cada una.** Se ve en el bloque de version, que parte la evidencia en dos
  grupos limpios:

  | Origen | Bloque de version (cmd 11) | chk |
  | ------ | -------------------------- | --- |
  | **AUT01**, PC fisica con Windows (Etapa W): `w1-from-har.jsonl`, `w2-*.pcap`, `w2soft-*.pcap` | `08 00 83 01 05 00` | `b5` |
  | **VM de Windows** con el dongle por passthrough: `web-*.pcap`, `soft-*.pcap` | `08 00 83 01 01 00` | `b1` |
  | Los **27 respaldos** por hidraw desde Linux | `08 00 83 01 01 00` | `b1` |

  Las dos tramas son reales: el checksum acompana en las dos. Y el argumento
  que cierra el asunto es que **la VM usa el mismo dongle fisico que Linux**,
  pasado por USB passthrough, asi que VM y Linux miran necesariamente el mismo
  mouse — y coinciden. AUT01 tenia el suyo.

  Consecuencia practica, y es la que importa al auditar: **la Etapa W (AUT01)
  vale como framing, no como valores de esta unidad.** El framing esta
  confirmado aparte contra este mouse, asi que ninguna conclusion de forma se
  cae. Lo que no se puede hacer es tomar un valor de AUT01 como estado de este
  mouse. La Etapa 2 no lo hace: se valido contra `soft-todo.pcap` y
  `web-todo.pcap`, los dos de la VM, partiendo de un respaldo real.

  Sigue sin saberse **que campo es ese byte**. Y las dos trazas de
  `bitacora.md` que muestran `05` como lectura de Linux no
  concuerdan con ningun respaldo: quedan marcadas como sospechosas.
- Probado solo en Brave. Deberia andar en cualquier Chromium.
- Un solo mouse, una sola sesion: no hay evidencia de que los `sub` o los
  offsets sean estables entre versiones de firmware.
- **A 8000 Hz no se puede LEER el mouse entero desde Linux** (las escrituras si pasan: ver la fila de MEDIDO). El canal
  de configuracion compite con el trafico de movimiento y el dongle contesta
  `0xC3` ocupado. Medido con tres corridas, y no se arregla con reintentos: hay
  que bajar la tasa antes de configurar. Eso se hace desde Linux:
  `driver/scripts/cambiar-rate.py` toca un solo comando y cambia las cuatro
  tasas en las dos direcciones (MEDIDO, `bitacora.md`, "Las cuatro tasas
  funcionan desde Linux"), y `primera-escritura.py` y la aplicacion bajan y
  vuelven solas.

---

## 6. Como empezar a auditar

```bash
# 1. Las pruebas que no tocan hardware
python3 driver/tests/simula_pagina.py     # la web nos acepta como helper
python3 driver/tests/salvaguardas.py      # las barandas siguen puestas

# 2. Escuchar el mouse sin escribirle nada
driver/scripts/sondear.py --escuchar 20
driver/scripts/medir-hibernacion.py --minutos 6   # escucha O_RDONLY el latido Report ID 3

# 3. Leer valores reales (mover el mouse mientras corre)
driver/scripts/sondear.py --pedir 11 --pedir 6 --pedir 4
driver/scripts/respaldar.py               # los siete comandos, a dev/models/attackshark-x8pro/respaldos/<fecha>.json

# 3b. El camino de escritura: el paso 4 pide confirmacion por terminal
driver/scripts/primera-escritura.py --comando rate                  # idempotente
driver/scripts/primera-escritura.py --comando luz --hibernacion 10  # mueve el corte
driver/scripts/primera-escritura.py --comando dpi --nivel-activo 2  # el LED cambia
driver/scripts/primera-escritura.py --comando macro --macro-id 17   # las dos tramas


# 4. Reproducir el analisis del binario
#    (el sha del instalador se verifica solo; los strings de formato del
#     helper salen con: strings -a -t x app/WebDriver.exe | grep '%02x')
dev/herramientas/extraer-helper.sh ~/Descargas/WebDriverSetup.exe /tmp/helper

# 5. Punta a punta, con la web
./linshark --backend hidraw --mode read --record traza.jsonl
```

`driver/tests/simula_pagina.py` merece atencion especial: es una transcripcion de la
logica real del store de la pagina (handler de presencia, `setDevice`,
`selectDevice`), con los chequeos raros incluidos. Si esta mal transcripto,
valida algo que no es. Contrastarlo contra `dev/research/webapp/app.js`.
