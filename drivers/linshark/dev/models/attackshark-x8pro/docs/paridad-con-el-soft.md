# Paridad con el software nativo de Windows

Dos preguntas concretas: **¿pueden asignarse los botones con las mismas opciones
que ofrece el programa de la VM?** y **¿pueden configurarse macros con las mismas
opciones?**

Ambas se responden sin tocar el dispositivo, cruzando tres fuentes ya presentes
en el repositorio: `app/res/lan/EN.xml` del instalador de Windows —su inventario
completo de textos de interfaz—, las tablas de códigos del *bundle* de la web, y
lo que el proyecto tiene decodificado del bus.

**Estado:** las dos piezas que faltaban están escritas y con su Etapa 2
cumplida —el **atajo de teclado** y el **codificador de eventos de macro**—, de
modo que la paridad de botones y macros es completa.

---

## Botones: paridad completa

El software nativo ofrece las familias siguientes, y **la tabla de 54 códigos
las cubre todas**:

| Opción del software nativo | Código en este proyecto |
| :--- | :--- |
| Left / Right / Middle Click, Forward, Backward | 2, 3, 4, 6, 5 |
| Double Click, Fire Button | 7, 8 |
| DPI, DPI Cycle, DPI +, DPI − | 16, 13, 14, 15 |
| Multimedia: Media Player, Play/Pause, Prev, Next, Stop, Mute, Vol ± | 21, 24, 22, 23, 25, 26, 27, 28 |
| Browser: Home, Favorites, Forward, Backward, Stop, Refresh, Search | 37, 31, 32, 33, 34, 36, 38 |
| Button Off | 1 |
| Macro | 18 (más `--macro-id`) |
| **Key** (tecla con Ctrl/Shift/Alt/Win) | 17 (más `--atajo ctrl+c`) |

El proyecto dispone además de funciones que el software nativo no muestra en su
lista de botones: ciclo de tasa de sondeo (40), ciclo de modo LED (41),
indicación de batería (43), ciclo de perfil (52-54), triple clic (55) y tecla Fn
(39).

### El atajo de teclado

El código 17 admite **dos parámetros**: los modificadores en `p1` —un byte de
bits— y el **usage HID** de la tecla en `p2`. El software nativo los compone
mediante su diálogo «Key»: se seleccionan Ctrl/Shift/Alt/Win y una tecla de la
lista.

Se escribe así, y la limitación de «no hay interfaz» pasó a ser una salvaguarda
de «sin tecla no se escribe»:

```bash
driver/scripts/primera-escritura.py --comando botones --boton costado-adelante \
    --funcion "atajo de teclado" --atajo ctrl+c
driver/scripts/primera-escritura.py --comando botones --listar-teclas
```

**Etapa 2 cumplida contra dos fuentes.** `soft-todo.pcap` contiene dos escrituras
consecutivas de cmd 8 que modifican un único slot cada una —`11 08 07` (Win+D) y
`11 0a 16` (Win+Shift+S)— y el codificador reproduce ambas byte a byte. Además,
las **veinte** entradas con código 17 de la tabla `sl` del *bundle* se componen a
partir de su texto (`ctrl+c` → `(1, 6)`, `alt+f4` → `(4, 61)`): veinte
coincidencias independientes sobre los cuatro bits del byte de modificadores, que
son los del estándar HID.

Dos elementos quedaron deliberadamente fuera:

* **los cuatro modificadores derechos** (`0x10`..`0x80`): el estándar los define,
  pero no aparecen en ninguna de las veinte entradas, ni en ningún bloque
  capturado, ni en el diálogo del software nativo, que ofrece cuatro. Se rechazan
  con ese motivo explícito en el mensaje;
* **el slot vacío `11 00 00`** —el `FUN_SHORTCUT` del *bundle*—, que el
  dispositivo acusa igualmente y deja el botón inerte. Es la misma carencia que
  el macro con identificador 0, y se cierra del mismo modo: `--atajo` es
  obligatorio.

---

## Macros: disparo y grabación

El software nativo dispone de un gestor de macros con las opciones siguientes:

| Opción | Estado en este proyecto |
| :--- | :--- |
| **Loop Times** (reproducir N veces) | **sí** — modo 0 con contador, MEDIDO accionando el botón |
| **Any Key Press To Stop Playing** | **sí** — modo 1 (escrito y releído; falta accionarlo) |
| **Press And Hold, Release Stop** | **sí** — modo 2, MEDIDO accionando el botón |
| Asignar el macro a un botón | **sí** — `--funcion macro --macro-id N` |
| Lista de eventos (Key / Action / Delay en ms) | **sí** — `--eventos`, con Etapa 2 contra el bus |
| Insertar evento de mouse, tecla o retardo; borrar, limpiar | **sí**, transmitiendo la lista completa |
| Grabación en vivo (Recording / Stop) | **sí** — la aplicación dispone de panel de macros con grabador |
| Record Delay, Min Delay, Default Delay | **no**, y son propios de su interfaz: el bloque solo transporta el tiempo de cada evento |
| Nombre del macro | **no viaja al dispositivo**: lo almacena la aplicación (ver más abajo) |

### El formato, decodificado

El bloque de un macro ocupa **111 bytes** y su estructura está decodificada y
verificada contra el bus (cuatro escrituras del software nativo, reproducidas
byte a byte):

* cabecera: identificador, modo de disparo, contador de repeticiones y **número
  de pares de bytes**;
* a continuación los eventos: **2 bytes cada uno** —`[tiempo | bit de dirección,
  usageId]`, con el tiempo en milisegundos— o **4 bytes** si el tiempo supera los
  127 ms, con un par adicional `[centenas, 3]`;
* y el checksum interno en *big-endian* al escribir, invertido al leer.

De ahí se deriva el límite: **50 eventos por macro** (100 bytes disponibles), o
25 si todos emplean tiempo largo.

Los usage IDs de los botones del mouse están confirmados por partida doble —el
*bundle* los declara 241..245 y un macro grabado manualmente con el software
nativo los almacena igual—, y los de las teclas son los usages HID estándar, los
mismos que requiere el atajo de teclado.

**Grabar un macro consiste, por tanto, en escribir esa lista**, y el codificador
existe:

```bash
driver/scripts/primera-escritura.py --comando macro --macro-id 17 \
    --eventos "clic-izquierdo:abajo@10, clic-izquierdo:arriba@10"
```

Con la Etapa 2 más económica que le quedaba al proyecto: los diez eventos del
macro capturado, entregados al codificador, devuelven **el bloque de 111 bytes
idéntico** al que el software nativo escribió en el dispositivo, checksum interno
incluido, y las dos tramas que viajan al dongle resultan iguales a las de
`soft-macro-asignado.pcap`.

El límite de 50 eventos **se valida contra el espacio disponible, no contra el
byte**: el contador de pares admite hasta 255 y los 100 bytes de espacio no, de
modo que excederlo llenaría el bloque y sobrescribiría el checksum. Qué hace el
dispositivo con un bloque más largo sigue sin medirse, y averiguarlo
sobrescribiendo su propio checksum no es el procedimiento adecuado.

### El nombre del macro no reside en el dispositivo

Los 111 bytes no incluyen campo de nombre, y el software nativo almacena los
suyos en un archivo propio (`ms_13/macro.data`, en el disco de Windows). Los
nombres son, por tanto, responsabilidad del cliente: **la aplicación los almacena
por su cuenta**, y si alguien configura el dispositivo con el software nativo y
después con esta aplicación, los nombres no se transfieren.

Está resuelto: `driver/src/linshark/nombres.py` los guarda en
`~/.config/linshark/macros.json` y `driver/scripts/nombres-de-macro.py` los edita
sin tocar el dispositivo. `primera-escritura.py --comando macro` los muestra,
para evitar escribir en el macro equivocado. Dos detalles que son salvaguardas y
no adornos: un archivo ilegible se interpreta como vacío **y así se comunica**
—sin nombres la aplicación funciona igual—, y en ese caso no se sobrescribe,
porque eso destruiría su contenido sin que nadie lo advirtiera.

---

## Qué falta para la paridad completa

Nada en cuanto a paridad de datos. Los tres puntos que quedaban abiertos —el
codificador de eventos, el atajo de teclado y los nombres del lado de la
aplicación— están cerrados, y con ellos los tres que dependían del hardware:

1. **La Etapa 3 de ambos codificadores:** cumplida contra el hardware. El atajo
   llega al sistema como pulsaciones reales —copia en un editor y emite SIGINT en
   una terminal— y el macro se reproduce con su secuencia en orden.
2. **La inferencia sobre `dir0`/`dir1`, cerrada:** que `dir0` pulsa y `dir1`
   libera quedó **MEDIDO**, donde antes era un alias INFERIDO.
3. **Grabación en vivo:** la aplicación dispone de panel de macros con grabador.

Nada de esto requirió capturas nuevas: era código, y la evidencia ya estaba en el
repositorio.
