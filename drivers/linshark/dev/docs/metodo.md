# El método: cómo escribir en el dispositivo sin inutilizarlo

Este documento es **la norma, no el registro**. Lo ejecutado está en
`bitacora.md`; lo que se sabe y cómo se sabe, en `evidencia.md`; el protocolo, en
`protocolo.md`.

Es transversal a cualquier modelo. Los ejemplos concretos proceden del Attack
Shark X8 Pro, el primer modelo medido, y se indica cuando un valor es suyo y no
una propiedad general.

Sustituye a `fase2.md`, que era el plan para habilitar las escrituras y quedó
cumplido para los cinco comandos de `p.WRITABLE`. Lo que sigue vigente de aquel
plan es esto.

---

## La regla de fondo

**Nunca se envía al dispositivo una secuencia de bytes que el driver oficial no
le haya enviado antes, verificada byte a byte.**

De ahí se deriva todo lo demás. El dispositivo no responde «comando inválido»:
no responde, y un opcode inventado puede corresponder a una rutina del gestor de
arranque e inutilizarlo. No hay *fuzzing* sobre el *endpoint* vendor, y no lo
habrá.

Corolario que costó una sesión aprender, y que volvió a manifestarse después:
**un error de formato es indistinguible de un problema de enlace**. Antes de
culpar a la radio, conviene contrastar la trama contra el binario.

Existe una comprobación barata que no se empleó cuando hacía falta:
**contrastar la trama que se emite ahora contra la de una corrida que sí
funcionó**. Aquel día una herramienta enviaba la trama empaquetada dos veces —el
dispositivo recibía un bloque de DPI de catorce bytes y lo descartaba, mientras
el dongle acusaba `0xC1`— y se invirtieron cuatro horas buscando explicaciones en
el firmware. Comparar sus bytes con los de la escritura que había funcionado tres
horas antes lo mostraba en un minuto.

---

## Las cuatro etapas

Ninguna etapa se omite, y las tres primeras no escriben un solo byte en el
dispositivo.

### Etapa 0 — Poder volver atrás

Un respaldo reciente y **completo** —todos los comandos legibles, más los macros
a los que apuntan los slots de botón— antes de cualquier escritura. Lo toma
`primera-escritura.py` en su paso 1 y aborta si resulta incompleto: un respaldo
al que le falta un bloque no es una red de seguridad.

### Etapa 1 — Capturar lo que emite el driver oficial

Con el dongle asignado a la VM y `usbmon` en el anfitrión (`captura-kvm.md`). Se
captura **accionando el control que interesa**, y conviene anotar qué se accionó
y cuándo: una captura sin su condición vale la mitad.

### Etapa 2 — Igualdad byte a byte, todavía sin escribir

El codificador propio debe reproducir **exactamente** lo que emitió el driver
oficial. Hay dos formas, y la segunda es más sólida:

1. **Contra una trama capturada:** partiendo del bloque que devolvió el
   dispositivo, el codificador produce byte a byte lo que el driver escribió.
2. **Convirtiendo una escritura real en otra:** dos escrituras del driver que
   difieren únicamente en el campo de interés —más el checksum—, y el codificador
   propio pasa de una a la otra **en ambas direcciones**. No exige dar por bueno
   ningún constructor del bundle.

La segunda es la que respalda el reposo corto (cmd 5) y el nivel de DPI activo
(cmd 4), y conviene buscarla siempre que haya capturas suficientes.

**Si un campo es constante en todas las capturas, no existe Etapa 2 posible.** No
falta codificador: falta captura. Hoy es el caso de `dpi_ON_OFF_flag`, los ocho
colores de indicador, `Dpi_indication_type` y `lightMode`.

### Etapa 3 — La primera escritura, diseñada para no cambiar nada

**Se escribe el valor que el dispositivo ya tiene.** Si el formato es correcto, lo
acepta y nada cambia; si es incorrecto, lo ignora y tampoco. En ambos casos el
dispositivo queda como estaba, y lo que se aprende —observando el acuse `0xC1`—
es si el *framing* sirve. Es la única forma de probar una escritura sin arriesgar
el hardware.

Después, y solo después, un cambio real: pequeño, reversible y con la vuelta
atrás **redactada antes de ejecutarlo**. Y al terminar, releer todo y comparar
contra el respaldo: no únicamente el campo modificado, sino todos los comandos,
byte a byte.

Dos trampas ya manifestadas:

* **Una escritura idempotente no siempre consiste en devolver el bloque leído.**
  En cmd 8 los slots 4, 5 y 6 se remapean entre escritura y lectura; en cmd 9 el
  checksum interno vuelve invertido. Devolver el bloque en crudo rota tres
  botones o emite un bloque mal formado. Por eso codificador y decodificador son
  funciones distintas.
* **Una escritura idempotente que no modifica un byte es un éxito, no un
  fallo.**

### Etapa 4 — El resto, por riesgo creciente

Un campo por corrida. El ciclo es **cambio pequeño → verificación → vuelta
atrás**, y dos campos simultáneos rompen la segunda parte: si algo resulta
anómalo, no se sabe cuál de los dos lo causó.

---

## Qué cuenta como verificación

El acuse `0xC1` y la relectura confirman que **el dispositivo ha almacenado** los
bytes. No confirman que produzcan efecto alguno. Una verificación **externa** es
la que no pasa por el protocolo:

| Campo | Cómo se verifica |
| :--- | :--- |
| tasa de sondeo | `medir-polling.py` cronometra el kernel |
| hibernación y reposo corto | el latido del dispositivo cesa, y el escalón se desplaza |
| botones y macros | se acciona el botón |
| distancia de despegue | se eleva el mouse a altura constante |
| nivel de DPI activo | el LED de nivel cambia de color, **y el firmware escribe el mismo byte al ciclar con el botón** |
| DPI | la plataforma oficial muestra un número (distinto, pero es un lector independiente) |
| los cuatro registros del sensor, color | **nada externo** |

**Existe una quinta vía, la más independiente de todas: dejar que el propio
dispositivo escriba.** Si un campo puede modificarse desde el hardware —el botón
de ciclo de DPI modifica `Current_Dpi_level_flag`— se acciona ahí, sin ningún
cliente conectado, y se lee el bloque. Si el firmware toca el mismo byte que se
escribe desde el proyecto, y solo ese, el significado del campo queda confirmado
sin depender del código propio ni del de szslxd-tech. Se descubrió por
casualidad, y conviene buscarla deliberadamente.

Las cuatro comprobables a simple vista son la distancia de despegue, los dos
órdenes de la rueda y el nivel de DPI activo. El color del cmd 5 **no enciende
nada en el X8 Pro**, y prometer una verificación inexistente es peor que no
ofrecer ninguna.

---

## Las siete llaves del modo `full`

Las verifica `driver/tests/salvaguardas.py`. Si alguna se modifica, la prueba
falla deliberadamente.

1. `--permitir-escritura CMD`, repetible: `--mode full` por sí solo es un
   **error**, no un permiso amplio.
2. Lista blanca de opcodes (`p.OPCODES_VALIDOS`): únicamente `0x00` y `0xA0`.
3. Lista blanca de comandos (`p.WRITABLE`), subconjunto **estricto** de lo
   legible.
4. Simulación por **defecto**: compone la trama, la muestra y no la emite.
5. Confirmación por terminal la primera vez que una sesión escribe realmente. Sin
   terminal interactiva no se escribe.
6. El nodo debe ser el del dongle, y la batería estar por encima del 50 %.
7. Una prueba por cada una, incluida una que comprueba que **con todo en su sitio
   sí escribe**: una salvaguarda que nunca deja pasar nada es indistinguible de
   una rota.

Y dos techos más restrictivos que `WRITABLE`, deliberadamente:

* **El CLI del puente** (`linshark --permitir-escritura`) solo admite tasa y DPI.
  A través del puente quien escribe es la plataforma oficial, y su bloque de
  botones invierte el desplazamiento.
* **El backend no sabe emitir bloques multitrama** y no va a saber:
  `backend.SIN_CAMINO_EN_EL_BACKEND` nombra la prohibición de cmd 9 para que no
  se confunda con «no ha superado la Etapa 2».

---

## Qué no se hace nunca

- Emitir un comando ausente de la lista blanca, aunque figure en el binario. El
  comando `0x0C` sigue sin identificar: no se toca.
- Inventar un `sizeTotalData`, o proceder por tanteo.
- Escribir con el cable conectado, o con la batería baja.
- Escribir dos comandos consecutivos sin verificar el primero.
- Continuar tras una señal de alarma bajo la hipótesis de que «quizá haya sido el
  enlace».
- **Configurar con el dispositivo por encima de 1000 Hz.** El respaldo completo
  no se completa —MEDIDO a 2000 Hz y a 8000 Hz— y el paso 1 de la Etapa 3 lo
  exige. Las escrituras **sí** llegan a cualquier tasa, de modo que la salida es
  reducirla primero: `driver/scripts/cambiar-rate.py --valor 1000`, que toca un
  único comando y respalda el campo que modifica leyéndolo un segundo antes.

---

## Señales de alarma: detenerse y no insistir

Ante cualquiera de estas se interrumpe la sesión de escritura, se desconecta y
reconecta el dongle, y se relee el estado completo antes de continuar:

- El dispositivo deja de responder lecturas que antes respondía.
- Un campo no modificado aparece alterado.
- El dispositivo se desconecta y reconecta por sí solo.
- Aparece un opcode de estado desconocido (distinto de `0xC0`, `0xC2` y `0xC3`).
- Dos escrituras idempotentes consecutivas producen resultados distintos.

Y la regla de fondo: **ante la duda, no se emite.** Un día más sin poder cambiar
el DPI desde Linux no es un problema. Un dispositivo inutilizado sí.

---

## Reparto de tareas

**Los comandos que interactúan con el dispositivo los ejecuta el usuario.** Vale
para escrituras, lecturas y mediciones. El motivo no es el permiso sino la
medición: si el mouse se usa mientras hay una corrida en marcha, la medición se
contamina sin que nadie lo advierta.

El asistente prepara el comando exacto **con su condición física** —mover el
mouse, no tocarlo durante N minutos, elevarlo unos 2 mm— y espera la salida. Y
ejecuta por su cuenta lo que no toca el dispositivo: pruebas, capturas ya
grabadas, bundle, código y documentación.

---

## Al añadir algo al protocolo

**Citar la fuente en el código**: el archivo y la función del bundle, o el
desplazamiento del desensamblado. Todo `protocol.py` está redactado así.

Y clasificar la afirmación en `evidencia.md`: **MEDIDO** (contra el hardware o el
binario, con salida reproducible), **LEÍDO** (consta en el bundle o en el
desensamblado, sin comprobación contra el aparato) o **INFERIDO** (deducido, y
puede ser falso). Una inferencia amplificada a hecho es el error que más veces ha
estado cerca de costar caro en este proyecto.
