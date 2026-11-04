# LinShark — instrucciones para agentes

Configurador de ratones **LXDDZ / Beken** (los de szslxd-tech.com: Attack Shark,
MambaSnake, INX) para Linux, sin el cliente oficial. El catálogo declara 47
modelos; hay **uno medido**, el Attack Shark X8 Pro. Nada del código conoce un
modelo por nombre: todo sale de `dispositivos.activo()`.

La aplicación existe y funciona: `./driver/linshark-gui`. Se arma sola desde
`modelo.campos_de()` (un control por campo), tiene panel de macros con grabador,
ofrece la regla de udev como botón, y `driver/tests/interfaz.py` la prueba entera
sin mouse ni ventana (`QT_QPA_PLATFORM=offscreen`).

**Qué es este archivo.** Las reglas del proyecto (§1), que valen igual para
personas y agentes, y después el estado que no hay que redescubrir: hallazgos
medidos y decisiones tomadas, cada una con su test. Las reglas son **solo las
del §1**; de §2 en adelante nada es norma, aunque esté en negrita.
`CONTRIBUTING.md` remite acá en vez de repetirlas. Si otro documento dice algo
distinto sobre una regla, manda este; sobre un hecho, mandan el código, los
tests y `evidencia.md`.

**Alcance de un agente, de un vistazo:**

- **Solo, sin preguntar:** leer y editar código, tests y documentación; correr
  los tests y todo lo que no toca el mouse (§11, primer bloque).
- **Lo prepara el agente y lo corre el usuario:** todo lo que le habla al
  mouse —lee, escribe o mide— (§11, segundo bloque), y lo que pide `sudo`.
- **Solo si lo pide el usuario:** aflojar una baranda (§1.4).
- **La puerta:** las cuatro tandas de tests del §11 pasan antes de dar algo por
  terminado.

**Secciones:** [§1 Reglas](#1-reglas-que-no-se-negocian) ·
[§2 Estructura](#2-estructura) · [§3 Qué leer](#3-leer-antes-de-tocar-nada) ·
[§4 Barandas de lectura](#4-las-cuatro-barandas-de-lectura) ·
[§5 Protocolo](#5-estado-del-protocolo) ·
[§6 La tasa](#6-la-tasa-que-es-el-caso-especial) ·
[§7 El cable](#7-el-canal-por-cable) · [§8 Conexión](#8-conexión) ·
[§9 Trampas](#9-trampas-que-ya-costaron-caro) ·
[§10 La aplicación](#10-la-aplicación-decisiones-tomadas) ·
[§11 Comandos](#11-comandos)

---

## 1. Reglas que no se negocian

1. **No hay fuzzing sobre el endpoint vendor.** Solo se emiten secuencias
   levantadas literalmente del bundle de la web o del binario del helper. Un
   opcode inventado puede caer en un comando de bootloader.
2. **Los comandos que tocan el mouse los corre el usuario, no el asistente.**
   Escrituras, lecturas y mediciones. El motivo es la medición, no el permiso: si
   alguien usa el mouse durante una corrida, se ensucia. El asistente prepara el
   comando exacto **con su condición física** (mover el mouse, no tocarlo N
   minutos, levantarlo ~2 mm) y espera la salida. Corre por su cuenta lo que no
   toca el dispositivo: tests, capturas grabadas, bundle, código, documentación.
3. **Al agregar algo al protocolo, citar la fuente en el código** (archivo y
   función del bundle, u offset del desensamblado) y clasificar la afirmación en
   `evidencia.md` como **MEDIDO**, **LEÍDO** o **INFERIDO**. Amplificar una
   inferencia a hecho es el error que más veces estuvo cerca de costar caro acá.
4. **Las barandas no se aflojan sin que lo pida el usuario.** El canal de solo
   lectura en `listen`, las siete llaves del modo `full`, la verificación del nodo
   en `--hidraw`, el filtro de `Origin` y la ausencia de opciones para mandar
   bytes crudos salen de hallazgos de auditoría. Las verifica
   `driver/tests/salvaguardas.py`.
5. **La documentación heredada no es evidencia.** Cruzar contra el código o los
   respaldos antes de amplificar una afirmación de los docs.
6. **Las entradas de la bitácora no se editan.** Una medición que se corrige se
   corrige en una entrada nueva que cita a la anterior.
7. **No se redistribuye material del fabricante.** Del bundle y del helper se
   guardan huellas criptográficas, nunca los archivos, y no se copia su código:
   se reproduce el *comportamiento* —el formato de los datos y la
   correspondencia entre bytes y valores—, que es lo que pide la
   interoperabilidad. Una captura del navegador guardada «with content» (`.har`)
   trae el bundle entero: se versiona lo extraído, no el `.har` (`.gitignore`).
8. **Toda escritura atraviesa las cuatro etapas** de `dev/docs/metodo.md`:
   respaldo íntegro, captura del driver oficial, reproducción byte a byte sin
   emitir nada, y solo entonces un único campo con relectura y comparación.

## 2. Estructura

```
driver/   el programa: biblioteca, ventana, CLI, regla de udev, instalador.
dev/      cómo se supo: método, protocolo, evidencia, capturas, herramientas.
```

- **La frontera va en un solo sentido**: `dev/` importa la biblioteca del driver;
  el driver **no puede necesitar nada de `dev/` en runtime**
  (`test_el_driver_no_necesita_a_dev`). Citar un doc de `dev/` en un comentario
  está bien; abrir un archivo de `dev/` en runtime, no.
- **Lo de un modelo va en `models/<modelo>/`**, de los dos lados
  (`dev/models/attackshark-x8pro/`, `driver/models/attackshark-x8pro/`). Lo
  general queda en `dev/` y `driver/` a secas. El instalador copia
  `driver/models/` entero y con la misma forma, porque `instalar-udev.sh` busca la
  regla relativa a sí mismo.
- En el código: `dispositivos.py` es el mecanismo (`Perfil`, registro, `activo()`)
  y no sabe de ningún mouse; el perfil del X8 Pro vive en
  `driver/src/linshark/perfiles/x8pro.py` y `linshark/__init__.py` lo registra.
  `estructuras.py` pide los offsets al perfil **en cada llamada**, y un
  `__getattr__` de módulo resuelve los nombres de siempre (`BOTONES_CANTIDAD`,
  `SLOTS_DE_RUEDA`, `DPI_SIZE`…).
- **Agregar un modelo** = un `dispositivos.Perfil` en `perfiles/`, sus carpetas en
  `models/`, y **la captura de su driver oficial**. `test_el_perfil_no_miente`
  compara cada campo contra la evidencia **solo del X8 Pro**: un modelo nuevo le
  suma sus comparaciones; `test_el_perfil_manda_de_verdad` arma un
  mouse ficticio para verificar que el perfil realmente manda. Receta completa en
  `dev/README.md`.
- **`dev/` es para descubrir un protocolo; `driver/` para usar y verificar un
  modelo ya medido.**
- **Los README de la raíz y de `driver/` tienen traducción** al inglés y al
  chino (`README.en.md`, `README.zh-CN.md`). El castellano es el original, y
  cada traducción dice en su primera línea el sha256 del castellano que
  tradujo. **Quien cambia un README en castellano actualiza sus dos
  traducciones y después la marca**: `test_las_traducciones_no_quedaron_atrasadas`
  se pone rojo si no. Los rótulos de la ventana se toman de `i18n._TEXTOS`, que
  es lo que la ventana muestra. `dev/`, este archivo y `CONTRIBUTING.md` **no se
  traducen, a propósito**: son procedimiento y evidencia, y una traducción
  atrasada ahí es alguien escribiéndole al mouse con una Etapa 2 mal entendida.

## 3. Leer antes de tocar nada

El método siempre; lo demás, según lo que se vaya a tocar. (La lista para quien
aporta un modelo sin haber estado en las sesiones está en `CONTRIBUTING.md`.)

1. `dev/docs/metodo.md` — las cuatro etapas, las barandas, las señales de alarma.
2. `dev/models/attackshark-x8pro/docs/SIGUIENTE-SESION.md` — qué queda abierto y las lecciones.
3. `dev/models/attackshark-x8pro/docs/evidencia.md` — qué se sabe y cómo.
4. `dev/models/attackshark-x8pro/docs/protocolo.md` — el protocolo, con citas.
5. `dev/models/attackshark-x8pro/docs/hardware.md` — descriptores USB/HID.

**La bitácora no se lee entera**: pasa los 400 KB. Se lee su índice (el
principio del archivo, que regenera `indexar-bitacora.py`) y la entrada que
toque: lo probado contra el hardware, **incluido lo que falló**. Antes de
tocar un comando o una baranda, buscar en ella su nombre.

## 4. Las cuatro barandas de lectura

El mouse tiene **un solo buffer para todos los reports**: por cable un `GET`
puede devolver el pedido anterior **con el byte 0 bien puesto** (pasó el
2026-09-20: cmd 5 devolvió el payload de cmd 6, un codificador le recalculó el
checksum y se lo mandó al mouse). **Ningún bloque tiene las cuatro barandas, y
entre las cuatro no queda ninguno afuera** (tabla por comando en `bitacora.md`):

| Baranda | Dónde | Cubre |
| :--- | :--- | :--- |
| checksum interno | `Cable._por_que_no_sirve()` | cmd 4, 5, 8 — cierra en 375/375 bloques de 125 respaldos. Cmd 9 queda afuera: vuelve invertido |
| canario | `sesion.juzgar()` | si cambió un bloque de `CMDS_INMUTABLES` (versión de firmware) → `lectura-corrompida`, no se juzga la escritura |
| cruce | `sesion.incoherencias()` | el perfil completo embebe rate, dpi, luz y botones (`Perfil.perfil_embebe`): dos copias que tienen que coincidir. `aplicar()` lo exige en el respaldo previo y en la relectura |
| bloque anterior | `Cable._es_el_bloque_anterior()` | lo único que cubre **cmd 6, 10 y 11**. MEDIDO 6 de 6 en 240 pedidos; 0 falsos positivos en 146 respaldos |

- **Sangrado MEDIDO: 1 a 2.5% de los pedidos** (`medir-sangrado.py`, tres corridas
  de 240). Los reintentos lo tapan entero (0 bloques perdidos en 720 pedidos):
  **los tiempos del canal no se tocan**.
- **El checksum sirve en la LECTURA, no después**: los codificadores lo
  recalculan, así que un bloque podrido que llegó a la escritura sale válido. Por
  eso el incidente no se vio.
- **Un bloque imposible no sale al bus.** Los codificadores de un campo tocan su
  byte y **copian el resto del bloque leído**. `estructuras.fuera_de_rango()`
  juzga **el bloque que se va a escribir** —no el leído, para que un mouse mal
  configurado se pueda arreglar— y `sesion.aplicar()` corta antes de confirmar.
  Solo sabe de cmd 5 y lo dice (`CMDS_CON_RANGO`). Volver atrás un bloque entero:
  `restaurar-bloque.py`.

## 5. Estado del protocolo

Los siete comandos que el mouse contesta están decodificados. Los **cinco** de
`p.WRITABLE` se escriben con Etapa 3 cumplida contra el hardware:

| Comando | Qué escribe | Verificación externa |
| :--- | :--- | :--- |
| rate (6) | la tasa de reporte | `medir-polling.py` cronometra el kernel |
| dpi (4) | ocho niveles, cuatro interruptores del sensor, nivel en uso | LOD a ojo; el nivel en uso, por el color del LED (MEDIDO) |
| luz (5) | color, reposo, hibernación, respuesta | el latido para, el escalón se mueve |
| botones (8) | los 18 slots y el orden de la rueda | se aprieta el botón |
| macros (9) | el disparo: modo y contador | se aprieta el botón y el macro corre |

Más **dos campos**, también con Etapa 3: el **atajo de teclado** de un botón
(código 17, modificadores en `p1`, usage HID en `p2`) y la **lista de eventos** de
un macro. El **cmd 7 (modo de despertado) no se puede leer**, así que no hay
Etapa 3 posible.

**Falta captura, no código**: `dpi_ON_OFF_flag`, los ocho colores de indicador,
`Dpi_indication_type` y `lightMode` son constantes en las 76 escrituras
capturadas. Escribirlos sería inventar bytes.

**El propio mouse sirve de lector independiente**: al ciclar el dpi con su botón,
el firmware escribe `Current_Dpi_level_flag` —el mismo byte que escribimos, y solo
ese—. Cuando un campo se pueda mover desde el hardware, usar ese camino.

**Los nombres de macro los guarda la aplicación** (`driver/src/linshark/nombres.py`):
el mouse no tiene campo de nombre.

### Al grabar un macro (MEDIDO)

- `dir0` aprieta y `dir1` suelta.
- **Un macro de un solo evento no se reproduce.** Se guarda y se relee bien; al
  apretar el botón no pasa nada. Con dos sale. Por qué, no se sabe.
- **El firmware no suelta nada al terminar**, y una tecla trabada no se despega
  apretándola: hay que desacoplar el dongle. El CLI avisa antes de confirmar.

### Después de una prueba

El mouse vuelve a como estaba antes de la prueba. **El repositorio no guarda la
configuración de ningún mouse**: eso vive en la máquina de quien lo usa
(`linshark.lugares`), no al lado del código (`test_lo_del_mouse_no_va_al_lado_del_codigo`):

- `~/.local/state/linshark/al-abrir.json`: la primera lectura de cada apertura
  de la ventana, con el formato de un respaldo. Se reemplaza en cada apertura.
  Con la tasa prestada, el bloque de rate dice 1000 y `tasa_bajada_desde` dice
  a cuánto estaba;
- `~/.local/state/linshark/respaldos/`: el respaldo que toma cada escritura del
  CLI antes de escribir.

**Los tests corren con `XDG_CONFIG_HOME` y `XDG_STATE_HOME` en una carpeta
temporal**: ninguna prueba escribe en el HOME de quien la corre.

Para volver, *volver a como estaba* en la ventana, o bloque por bloque con
`restaurar-bloque.py --respaldo`; para confirmar, `respaldar.py --comparar`.

## 6. La tasa, que es el caso especial

- **Arriba de 1000 Hz no se puede LEER el mouse entero** (MEDIDO a 2000 y 8000
  Hz): el respaldo no se completa y el paso 1 de la Etapa 3 lo exige. Las
  escrituras sí pasan a cualquier tasa.
- **La tasa no se escribe por la Etapa 3**, ni desde el CLI ni desde la app:
  verificaría el cambio con la herramienta que el cambio acaba de romper. Va por
  el camino de un solo comando —`cambiar-rate.py`, `Configuracion._escribir_tasa()`—
  que **insiste releyendo**, porque el dongle acusa `0xC1` sin que el mouse aplique
  (MEDIDO).
- **Las cuatro tasas se cambian desde Linux en las dos direcciones** (MEDIDO: 1000
  → 2000 → 4000 → 8000 y la vuelta, cada una al primer intento, verificadas con
  `medir-polling.py`).
- **Configurar pasa por bajar la tasa un momento**, por dos caminos:
  - **el CLI** (`primera-escritura.py`): el paso 0 la baja, el `finally` la
    devuelve, por corrida;
  - **la aplicación** (`sesion.Configuracion`): la baja **una vez**, lee el mouse
    **una vez**, y la devuelve al cerrar la ventana o tras 90 s sin cambios.
    **Lo dice en pantalla**, con un botón para devolverla ya. Es, con el
    arreglo de una tasa ilegible, lo único que la app cambia sin que se lo
    pidan, y por eso no se calla.
  - Antes esto estaba roto: bajaba y subía la tasa **por cada campo** (seis
    reconfiguraciones de radio para tres cambios, MEDIDO que puede dejar el mouse
    sin mover el puntero) y releía el mouse **dos veces por campo**. Probado
    contra el hardware: una ráfaga de siete escrituras con una sola bajada.

- **Una tasa que no se entiende no deja al programa afuera.** MEDIDO que
  pasa: el mouse devolvió `01 02 fd 00 00 00 00` —nibble alto 0— reportando a
  8000 Hz, y la ventana no leía nada. `Configuracion.preparar()` la deja en
  1000 Hz y sigue leyendo; **lo dice en pantalla** y guarda el bloque pisado en
  el estado (`tasa_arreglada_desde`). No vuelve: no hay tasa anterior que
  devolver.
  - El bloque sale de `estructuras.arreglar_report_rate()`, que **no respeta el
    nibble bajo**: da siempre un byte de `RATE_BYTES_EN_EL_BUS` (`0x44` por el
    dongle, la escritura del driver oficial byte a byte).
  - No toca una lectura cuyo complemento no cierra: eso es una lectura mala, no
    un byte guardado.
  - **El arreglo corrió solo contra el mouse de mentira**
    (`test_una_tasa_ilegible_no_deja_al_programa_afuera`). Del incidente se
    salió a mano con `cambiar-rate.py`, que sigue siendo la salida del CLI.

## 7. El canal por cable

`driver/src/linshark/cable.py`, con la misma interfaz que el `Device` del dongle, y
es el único que le habla al cable (`test_el_cable_solo_pasa_por_su_canal`). Por
cable el mouse declara **25 Feature Reports** (Usage Page 0x0B) con los mismos
números que los comandos del dongle: **el mismo bloque sin el envoltorio**. Leer =
pedido por el report `0xA0` + `GET_FEATURE` (sin el pedido no contesta); escribir =
`SET_FEATURE` con el largo que declara el mouse. `test_etapa2_cable` pasa byte a
byte en LOD, nivel de dpi, botón y macro.

**Lo que viaja por cable byte a byte igual que por el dongle hereda lo MEDIDO del
dongle** (regla del usuario, 2026-09-18). Lo que se mide aparte es el transporte
—pedido, largo, tiempos—, y cada escritura se sigue verificando releyendo.

Particularidades:
- **la tasa es el nibble bajo** y nunca se presta: por cable no pasa de 1000, así
  que no hay nada que bajar. La ventana ofrece solo las tasas del cable;
- **el macro se lee con su id** en el byte 4 del pedido y se escribe en dos trozos
  de 64;
- **después de escribir, 500 ms sin mandar nada** (el `Sleep(500)` del helper).
  Antes de eso el LOD no se veía en la relectura;
- **por cable se relee todo**, no el bloque escrito y el perfil: no hay radio que
  pierda pedidos;
- **escucha el Input Report 3** y al llegar un aviso relee solo dpi y perfil;
- **con el cable enchufado a la PC manda el cable**, aunque el botón de modo diga
  2.4 GHz, y el dongle se calla (MEDIDO). `conexiones.buscar()` pone el cable
  primero; `find_config_hidraw()` se niega a devolver el nodo del cable, y el CLI
  y el puente siguen hablando solo por el dongle;
- el mouse **a veces rechaza un `SET_REPORT` con STALL**; repetirlo pasa.

Por cable ya corrieron, ida y vuelta y sin una sola diferencia contra la
lectura previa: LOD, botones, respuesta, los tres interruptores, el dpi de cada nivel, el
nivel en uso, la rueda, el reposo, la hibernación, y la mutación real del macro
(modo del 17 de 2 a 0, relectura cambiada). **No queda nada sin correr por cable.**

## 8. Conexión

`linshark.conexiones` mira el bus entero —sin abrir ningún nodo ni mandarle nada
al mouse— y dice **por qué camino** está (dongle o cable), **en qué puerto** y con
qué permisos. De ahí salen el chip de la barra, un error que dice qué se vio en vez
de preguntar "¿está puesto el dongle?", y un vigilante que mira el bus cada 3 s: si
el dongle aparece lo abre, si cambió de puerto lo reabre, y si el mouse está por
cable lo avisa. Probado contra el bus de verdad (MEDIDO).

**El modo de conexión no se cambia por software**: en el bundle no hay ningún
comando de canal, así que el cliente oficial tampoco puede (LEÍDO). El mouse
tampoco dice por dónde habla: el `connectionMethod` lo pone el helper, que lo sabe
por el dispositivo USB del que leyó. Desconfigurar el dispositivo del cable desde
Linux **no lo devuelve a la radio** (MEDIDO). Lo que sirve es un cargador que no sea
la PC.

## 9. Trampas que ya costaron caro

- **Un error de formato se ve igual que un problema de enlace.** El mouse no
  contesta "comando inválido": no contesta, y el dongle manda el mismo NAK que
  cuando se pierde el paquete. Antes de culpar al enlace, revisar la trama contra
  el binario.
- **El enlace 2.4 GHz pierde pedidos de verdad**: 95% de éxito con el mouse en
  movimiento, 50% quieto. Toda prueba necesita reintentos, y conviene mover el
  mouse mientras corre.
- **Abrir cualquiera de los dos clientes oficiales pisa configuración.** La web
  reescribe todo lo que lee y deja el scroll invertido; el soft nativo pisa el dpi,
  el angle snapping y el tiempo de respuesta (MEDIDO). Después hay que revisar.
- **El dpi tiene dos lecturas.** La página lo **lee** con la tabla del 3311 y lo
  **escribe** con `Pu()`: para los mismos bytes muestra 1350 donde escribimos 1600.
  Cuál es el dpi real del sensor **no se sabe** (el nombre comercial PAW3395 es
  INFERIDO: sale del marketing, no de una lectura).

## 10. La aplicación: decisiones tomadas

No revertir sin motivo; cada una tiene su test.

- **No lee el mouse al arrancar.** Abre el nodo —para la batería y el cartel de
  udev— y espera. Leer lo pide quien mira, con el botón. Y una vez leído, el
  respaldo queda cacheado: cada escritura relee **el bloque escrito y el perfil
  completo**, que hace de testigo (MEDIDO sobre 139 respaldos, 95 pares con
  diferencias, 0 contraejemplos). Cuando con eso no alcanza para decir "y nada
  más", el veredicto **nombra lo que no se miró**. El caché se tira cuando el mouse
  cambia solo (Report ID 3).
- **Una fila es una fila**: la marca (color del LED del nivel, número del botón),
  el nombre, el control y un **`?`**. Detrás del `?` va qué es el parámetro y para
  qué sirve (`Campo.definicion`); el botón de modo lleva además su aviso
  (`Campo.aviso`). **La ventana no muestra la evidencia**: lo medido (`Campo.nota`,
  `dispositivos.Perfil`) queda en el modelo y en `dev/docs/`. Lo cuidan
  `test_la_ayuda_dice_que_es_cada_parametro` y `test_modelo_con_nombres_propios`.
- **Dos campos no se ofrecen, por el mismo motivo**: un control que mueve bytes y
  no cambia nada es el reproche que este proyecto le hace al cliente oficial.
  - el **color del indicador** de cada nivel es la marca de la fila de su nivel
    (`Campo.color`), y solo de los niveles cargados;
  - el **RGB del cmd 5 no sale**: se escribe, el mouse acusa `0xC1`, la relectura
    lo devuelve cambiado y el chasis no prende nada (MEDIDO). No cierra I-W16 —que
    sean inertes no está probado, todo se vio con `lightMode: 0`— así que
    `preparar_mutacion("color", …)` y el `--color` del CLI siguen andando: esto
    saca el control, no la capacidad. Vive en `Perfil.campos_ausentes`
    (`clave -> por qué`); sacarlo de esa lista devuelve el control **sin tocar la
    ventana**.
- **El clic izquierdo se reasigna**, con la regla del fabricante: siempre queda uno
  en los botones 1 a 5, y el 6 y el 7 (en la base) no pueden llevarlo
  (`Perfil.slots_para_clic_izquierdo`, `SinClicIzquierdo`). La ventana ofrece
  intercambiar el 1 y el 2 en una escritura. Etapa 3 cumplida; **Etapa 2 no hay**,
  ninguna captura muestra al cliente oficial escribiendo el slot 1.
- **Dos botones restauran, y ninguno toca los macros** (un macro es trabajo de
  quien lo grabó): *volver a como estaba* (la **primera** lectura de esta sesión,
  guardada una sola vez, y también en `~/.local/state/linshark/al-abrir.json`;
  la tasa es la de su dueño y no la prestada, `modelo.como_esta()`) y *valores seguros* (`modelo.SEGUROS` = `DE_FABRICA` con la
  tasa en 1000 Hz). Restaurar **no es un comando del protocolo**: son las
  escrituras que ya sabemos hacer, **solo las que hacen falta**
  (`modelo.pendientes()`), con la tasa **última** de la ráfaga. Antes, un diálogo
  dice qué campos van a cambiar y de qué a qué, y nombra los bloques que el mouse
  no contestó.
- **`DE_FABRICA` tiene dos fuentes independientes** que coinciden byte por byte: el
  dpi sale de `M()` del chunk `dpiX8Pro-CVtR2JhM.js`; el resto de
  `respaldos/linea-base-antes-de-escribir.json` (este mouse antes de que el
  proyecto le escribiera nada). Lo cuida `test_la_tabla_de_fabrica_sale_del_respaldo`.
  **La tasa "segura" son 1000 Hz y NO es la de fábrica** (500): 1000 es el techo
  desde el que el mouse todavía se puede leer entero.
- **La rueda no cambia los desplegables** (un `QComboBox` se come la rueda del
  scroll, y acá eso es una escritura al mouse). Los deslizadores y los numeritos sí
  la aceptan: ahí el valor se ve cambiar y no se escribe hasta soltar.
- **La función de un botón se elige escribiendo o por grupo** (son más de
  cincuenta): al abrir el desplegable sale un buscador sin tildes ni mayúsculas,
  con los grupos al costado (`controles.SelectorAgrupado`). Los grupos **no son del
  protocolo**: son `modelo.GRUPOS_DE_FUNCION`, por código, y llegan como
  `Campo.grupos`, así que la ventana sigue sin conocer ningún campo por nombre; un
  código sin grupo cae en "Otras". Las flechas **abren el buscador** en vez de
  elegir la opción de al lado. Lo cuida `test_las_funciones_se_buscan_y_se_agrupan`.
- **Tres idiomas** (castellano, inglés, chino), botón `🌐`, elección en
  `~/.config/linshark/interfaz.json`. Se traduce **por el texto castellano exacto**
  (`linshark_ui/i18n.py`): si una nota cambia en `modelo.py`, la traducción deja de
  coincidir y se ve el castellano, en vez de repetir en otro idioma algo que ya no
  es cierto. **Un mensaje nuevo lleva su fila en `i18n._TEXTOS`**
  (`test_no_queda_nada_sin_traducir`). Una fila puede traer una cuarta columna con
  el castellano **de pantalla**: en la terminal "MEDIDO a 2000 y a 8000" es la cita
  que importa, en la ventana sobra. La biblioteca y el CLI siguen en castellano.
- **Una unidad difiere a propósito**: `preparar_mutacion("respuesta", N)` toma el
  número que se ve (4..50, de a 2), como `campos_de()`; el `--respuesta` del CLI
  toma el **byte**, que viaja a la mitad. Lo cuida
  `test_leer_y_reescribir_no_mueve_nada`: **escribir lo que `campos_de()` muestra no
  puede mover ningún campo**.

La biblioteca tiene todo lo que la interfaz necesita: `sesion.aplicar()` corre la
Etapa 3 entera sin terminal, `modelo.campos_de()` da los 23 campos con nombre
propio, `modelo.macros_de()` los macros con sus advertencias,
`sesion.preparar_mutacion()` traduce `(clave, valor)` en lo que hay que escribir, y
`sesion.escuchar_novedades()` trae la batería y el cambio de nivel de dpi.

Requiere la regla de udev, que el instalador pone sola; a mano,
`sudo driver/scripts/instalar-udev.sh` (ya corre `udevadm trigger --action=add`;
con `change` los permisos del nodo vivo no se reaplican).

## 11. Comandos

**No tocan el mouse** — los corre el agente:

```bash
python3 driver/tests/salvaguardas.py                     # las barandas y el protocolo
python3 driver/tests/interfaz.py                         # la interfaz, sin mouse ni ventana
python3 driver/tests/simula_pagina.py                    # la web nos acepta
python3 dev/tests/evidencia.py                           # las afirmaciones, contra los respaldos

driver/scripts/donde-esta-el-mouse.py                    # por dónde y en qué puerto; solo mira sysfs
driver/instalar/install.sh --solo-probar                 # qué haría el instalador
dev/herramientas/leer-captura-usb.py dev/models/attackshark-x8pro/docs/capturas-w/*.pcap
dev/herramientas/indexar-bitacora.py                     # tras agregar una entrada
```

**Le hablan al mouse, o piden `sudo`** — el agente los prepara, con su condición
física, y los corre el usuario:

```bash
sudo driver/instalar/install.sh                          # instalar
sudo driver/instalar/uninstall.sh

./driver/linshark-gui                                    # la aplicación; --sin-tema usa el del escritorio

driver/scripts/sondear.py --escuchar 20                  # escuchar, sin escribir
driver/scripts/sondear.py --pedir 9 --macro-id 17        # el macro se lee con su id
driver/scripts/respaldar.py                              # respaldo, antes de escribir
driver/scripts/cambiar-rate.py --valor 1000              # solo la tasa; sin respaldo completo
driver/scripts/restaurar-bloque.py --respaldo X.json --comando luz [--solo-probar]
driver/scripts/nombres-de-macro.py --poner 17 "copiar y pegar"
driver/scripts/medir-polling.py --segundos 15            # tasa real
driver/scripts/medir-hibernacion.py --minutos 6          # cuándo se duerme (no escribe)

# Etapa 3: respaldo, confirmación, escritura, relectura y diff. Un campo por corrida.
# Con el mouse arriba de 1000 Hz no hay nada que agregar: baja y vuelve solo.
driver/scripts/primera-escritura.py --comando dpi --nivel 1 --valor 1600
driver/scripts/primera-escritura.py --comando dpi --nivel-activo 2 | --lod 2
driver/scripts/primera-escritura.py --comando luz --hibernacion 1 | --reposo 1
driver/scripts/primera-escritura.py --comando botones --listar-funciones | --listar-teclas
driver/scripts/primera-escritura.py --comando botones --boton costado-adelante --funcion adelante
driver/scripts/primera-escritura.py --comando botones --boton costado-adelante \
    --funcion "atajo de teclado" --atajo ctrl+c          # p1 = modificadores, p2 = usage
driver/scripts/primera-escritura.py --comando macro --macro-id 17 \
    --eventos "a:abajo@10, a:arriba@10"                  # GRABA la lista de eventos

dev/herramientas/leer-por-cable.py                       # el canal del CABLE, solo lectura
dev/herramientas/medir-enlace.py --segundos 45           # fiabilidad del enlace (dongle)
dev/herramientas/medir-sangrado.py --vueltas 40          # cada cuánto sangra el buffer (cable)
sudo dev/herramientas/preparar-captura-vm.sh             # una vez: usbmon en el host
sudo dev/herramientas/capturar-vm.sh web luz-rojo        # medir al driver oficial

./driver/linshark --backend hidraw --mode read           # el puente, contra la web
```

Para medir al driver oficial, una VM de Windows toma el dongle por USB
passthrough y se captura desde el host con usbmon:
`dev/models/attackshark-x8pro/docs/captura-kvm.md`.
