<p align="center"><img src="../driver/instalar/LinShark.svg" width="96" alt=""></p>

# Ingeniería inversa del protocolo, e incorporación de modelos nuevos

Este subsistema no contiene el programa: documenta **cómo se supo lo que el
programa sabe**, y provee el instrumental para repetirlo con otro modelo. El
programa está en [`../driver/`](../driver/README.md).

El material existente procede de un Attack Shark X8 Pro, pero el método no es
propio de ese modelo: el fabricante (LXDDZ / Beken) produce el software de
**47 modelos** de al menos tres marcas —Attack Shark, MambaSnake e INX— con el
mismo bundle y el mismo servicio auxiliar. Si un modelo se configura desde esa
misma plataforma web, buena parte de lo aquí descrito le resulta aplicable
directamente.

**Esfuerzo.** El X8 Pro requirió diez días de trabajo, la mitad de ellos
consumidos en obstáculos hoy resueltos: localizar el nodo correcto, comprender
el *framing*, descubrir que el enlace pierde peticiones y escribir el
decodificador. Un modelo de la misma familia no parte de cero —el método, las
herramientas y la biblioteca ya existen—, pero la captura, la decodificación y
la verificación de cada campo siguen siendo suyas. Los tiempos que acompañan a
cada paso son orientativos.

**Todos los comandos de este archivo se corren desde la raíz del
repositorio.**

---

## Las reglas que pesan aquí

Las reglas del proyecto están en un solo lugar,
[`AGENTS.md` §1](../AGENTS.md#1-reglas-que-no-se-negocian). Para este trabajo
pesan sobre todo tres:

**1. No se envía al dispositivo ningún byte que no se haya observado antes.** Ni
para probar, ni de forma exploratoria. Cada trama que este proyecto escribe
procede de una captura del cliente oficial o del binario del servicio auxiliar, y
lo declara en el código junto a su fuente. Un opcode inventado puede
corresponder a una rutina del gestor de arranque e inutilizar el dispositivo, y
no existe forma de distinguirlos desde fuera.

**2. Leer tiene un coste; escribir tiene consecuencias.** Leer un bloque que el
dispositivo declara no puede romper nada. Escribir sí, y por eso toda escritura
atraviesa las cuatro etapas de [`dev/docs/metodo.md`](docs/metodo.md), que en una
línea son: poder volver atrás, capturar al cliente oficial, reproducir sus bytes
**sin escribir**, y solo entonces escribir un único campo y releer.

**3. La documentación heredada no es evidencia.** Una afirmación de los
documentos del proyecto puede no haberse verificado nunca: se cruza contra el
código, las capturas o los respaldos antes de apoyarse en ella. La de este
proyecto afirmaba que botones y macros carecían de capturas; botones tenía
quince bloques en el bus.

El resto —las siete llaves del modo `full`, el canal de solo lectura, el filtro
de `Origin`— está explicado en `metodo.md`.

---

## Mapa del subsistema

| Ubicación | Contenido |
| :--- | :--- |
| [`dev/docs/metodo.md`](docs/metodo.md) | **Punto de partida.** Las cuatro etapas, las salvaguardas, las señales de alarma y el reparto de tareas |
| [`dev/models/attackshark-x8pro/docs/protocolo.md`](models/attackshark-x8pro/docs/protocolo.md) | El protocolo completo del X8 Pro, con la cita de origen de cada campo |
| [`dev/models/attackshark-x8pro/docs/evidencia.md`](models/attackshark-x8pro/docs/evidencia.md) | Qué está **MEDIDO**, qué **LEÍDO** y qué **INFERIDO**. La clasificación es el núcleo del proyecto |
| [`dev/models/attackshark-x8pro/docs/bitacora.md`](models/attackshark-x8pro/docs/bitacora.md) | Todo lo ensayado contra el hardware, **incluido lo que no funcionó** |
| [`dev/models/attackshark-x8pro/docs/hardware.md`](models/attackshark-x8pro/docs/hardware.md) | Los descriptores USB/HID, por dongle y por cable |
| [`dev/models/attackshark-x8pro/docs/captura-kvm.md`](models/attackshark-x8pro/docs/captura-kvm.md) | Cómo capturar al driver oficial con una VM de Windows y `usbmon` |
| [`dev/models/attackshark-x8pro/docs/paridad-con-el-soft.md`](models/attackshark-x8pro/docs/paridad-con-el-soft.md) | Qué hace el software nativo que el proyecto también hace, y cómo se verificó |
| `dev/herramientas/` | Instrumental de medición, captura y contraste (detalle abajo). Transversal: sirve para cualquier modelo |
| [`dev/research/`](research/README.md) | El material del fabricante: **huellas, no archivos**. `bajar-webapp.sh` lo descarga. Transversal: el bundle es común a los 47 modelos |
| `dev/models/attackshark-x8pro/respaldos/` | Las lecturas del dispositivo, versionadas. Son evidencia, no copias de seguridad |
| `dev/models/attackshark-x8pro/mediciones/` | Las corridas de hibernación, sondeo y fiabilidad del enlace |
| `dev/tests/evidencia.py` | Comprueba que las afirmaciones se sostienen contra esos datos |

Lo perteneciente a **un modelo concreto** reside en `dev/models/<modelo>/`, con
su propio `docs/`, `respaldos/` y `mediciones/`. `dev/herramientas/` y
`dev/research/` no conocen ningún modelo en particular. Dos piezas sí: hoy
`dev/tests/evidencia.py` apunta a `dev/models/attackshark-x8pro/respaldos/` e
`dev/herramientas/indexar-bitacora.py` a la bitácora del X8 Pro; con un segundo
modelo habrá que generalizarlas o darle a cada uno las suyas.

Las herramientas, y el subsistema al que pertenece cada una:

```bash
# --- dev/: descubrir un protocolo ---
dev/herramientas/leer-por-cable.py                  # el canal del cable, solo lectura
dev/herramientas/medir-enlace.py --segundos 45      # cuántas peticiones pierde la radio
dev/herramientas/medir-sangrado.py --vueltas 40     # con qué frecuencia el cable devuelve otro bloque
sudo dev/herramientas/preparar-captura-vm.sh        # usbmon en el anfitrión, una sola vez
sudo dev/herramientas/capturar-vm.sh web luz-rojo   # capturar al cliente oficial
dev/herramientas/leer-captura-usb.py dev/models/attackshark-x8pro/docs/capturas-w/*.pcap
dev/herramientas/extraer-soft.sh                    # extraer el instalador oficial
dev/herramientas/extraer-helper.sh                  # y el servicio auxiliar, para desensamblarlo
dev/herramientas/indexar-bitacora.py                # tras añadir una entrada

# --- driver/: los instrumentos ya verificados, que aquí se usan para medir ---
driver/scripts/donde-esta-el-mouse.py               # camino de conexión y puerto
driver/scripts/sondear.py --escuchar 20             # escuchar sin escribir
driver/scripts/respaldar.py                         # el respaldo, previo a toda escritura
driver/scripts/primera-escritura.py ...             # la Etapa 3, un campo por corrida
driver/scripts/medir-polling.py --segundos 15       # la tasa real, por el kernel
driver/scripts/medir-hibernacion.py --minutos 6     # cuándo entra en hibernación
```

La frontera es esa: **`dev/` sirve para descubrir un protocolo y `driver/` para
usar y verificar un modelo ya medido.** Y opera en un único sentido —las
herramientas de aquí importan la biblioteca del driver, y el driver no necesita
nada de aquí para funcionar—, condición que fija
`driver/tests/salvaguardas.py::test_el_driver_no_necesita_a_dev`.

Que el procedimiento de abajo corra scripts de `driver/scripts/` no contradice
esa frontera: la Etapa 3 de un modelo nuevo se hace **con los instrumentos que
ya están verificados**, no con unos nuevos. Correrlos contra un modelo en
estudio no lo da por integrado; lo integrado es lo que pasa la lista del final
del procedimiento.

---

## Procedimiento para incorporar un modelo

Cada paso indica **qué hacer**, **cómo comprobar que ha salido bien** y **qué
anotar**. Los que interactúan con el dispositivo los ejecuta una persona, no un
agente: no es una cuestión de permisos, sino de medición, que se contamina si
alguien usa el mouse durante una corrida.

### 1. Identificar el dispositivo (unos minutos, sin riesgo)

```bash
driver/scripts/donde-esta-el-mouse.py      # camino de conexión y puerto
lsusb -d <vendor>: -v                      # el descriptor completo
```

De aquí deben obtenerse: **identificadores de vendedor y producto del dongle**,
los **del cable** si existe, **cuál es la interfaz de configuración** —la que
declara una colección vendor, no las de teclado y mouse— y el **Report ID** con
el tamaño de su reporte. En el X8 Pro: `1d57:fa65`, interfaz 2, Report ID 4, 63
bytes.

El descriptor se lee sin tocar el dispositivo:

```bash
cat /sys/class/hidraw/hidrawN/device/report_descriptor | xxd
```

Si el modelo tiene cable, su descriptor también: por cable el X8 Pro declara
Feature Reports en lugar del Output Report del dongle (ver el paso 6).

→ Anotarlo en `dev/models/<modelo>/docs/hardware.md` y en un
`dispositivos.Perfil` nuevo.

### 2. Obtener el material del fabricante (del orden de una hora, sin riesgo)

El cliente oficial es la única fuente legítima de bytes. Dos piezas:

```bash
dev/research/bajar-webapp.sh            # el bundle de la web, con verificación de huellas
dev/herramientas/extraer-soft.sh        # el instalador de Windows
dev/herramientas/extraer-helper.sh      # el servicio auxiliar, para leerlo con objdump
```

Del **bundle** se extraen los nombres de los campos, las tablas de funciones de
botón, los rangos de los controles y el catálogo de modelos (`store.mouseNum`).
Del **servicio auxiliar** se extrae el *framing*: cómo se compone la trama que
viaja al dispositivo.

Se conserva **la huella, no el material**: son binarios propietarios. Ver
[`dev/research/README.md`](research/README.md).

→ Si el modelo figura en `store.mouseNum`, su `device id` ya es conocido.

### 3. Capturar al driver oficial (del orden de media jornada, sin riesgo para el dispositivo)

Esta es la Etapa 1, y no admite atajos: **sin captura no hay protocolo**. Se
realiza con una VM de Windows que reciba el dongle por *passthrough* USB,
capturando desde el anfitrión con `usbmon`:

```bash
sudo dev/herramientas/preparar-captura-vm.sh          # una sola vez
sudo dev/herramientas/capturar-vm.sh soft dpi-1600    # y accionar ESE control en la VM
```

Regla fundamental de las capturas: **un control por captura**, y el nombre del
archivo indica cuál. Una captura en la que se han tocado cinco parámetros no
permite aislar bytes.

→ Las capturas van a `dev/models/<modelo>/docs/capturas-w/` con un `.txt`
adjunto que indique qué se accionó, cuándo y en qué orden.

### 4. Decodificar, sin escribir nada (Etapa 2)

```bash
dev/herramientas/leer-captura-usb.py dev/models/<modelo>/docs/capturas-w/captura.pcap
```

El trabajo consiste en localizar los bloques, dividirlos en campos y
**recodificarlos** hasta que el resultado coincida **byte por byte** con lo que
emitió el driver oficial. Mientras eso no se cumpla, no se escribe nada.

Dos aspectos que en el X8 Pro resultaron costosos y conviene abordar desde el
principio:

- **el checksum**: aquí son dos, uno de trama y otro interno a la estructura, y
  el interno se calcula sobre un rango que no es evidente;
- **leer y escribir no comparten estructura**: hubo tres comandos en los que el
  dispositivo devuelve los campos en un orden distinto del que acepta.
  Devolverle literalmente lo que se le leyó rota tres botones.

→ Cada campo nuevo se anota en `dev/models/<modelo>/docs/protocolo.md` **con la
cita de su origen** (archivo y función del bundle, o desplazamiento del
desensamblado) y se clasifica en `dev/models/<modelo>/docs/evidencia.md` como
MEDIDO, LEÍDO o INFERIDO.

### 5. La primera escritura (Etapa 3; aquí sí hay riesgo)

El orden importa, y está diseñado para que **nada cambie**:

1. **respaldo completo** del dispositivo (`driver/scripts/respaldar.py`);
2. escribir **un único campo**, con el valor que ya tiene: una escritura
   idempotente. Si algo se ha entendido mal, se detecta sin haber modificado
   nada;
3. **releer y comparar.** Lo que haya cambiado debe ser exactamente lo escrito, y
   nada más;
4. solo entonces, un valor distinto, y **verificado fuera del protocolo**: el LED
   que cambia de color, el puntero que se comporta de otro modo, el cronómetro
   del kernel (`driver/scripts/medir-polling.py`). El decodificador propio no
   puede ser el único testigo de sí mismo.

`driver/scripts/primera-escritura.py` ejecuta los cuatro pasos, con confirmación
por terminal.

→ A la bitácora: qué se escribió, qué se releyó y qué se observó físicamente.

### 6. El cable, si el modelo lo tiene

El cable es otro transporte, no otro protocolo: en el X8 Pro los bloques son los
mismos, sin el envoltorio del dongle, pero viajan como Feature Reports, con un
pedido previo, un largo propio y tiempos propios (`AGENTS.md` §7). La regla del
proyecto es que **lo que viaja por cable byte a byte igual que por el dongle
hereda lo medido por el dongle, y el transporte se mide aparte**. En un modelo
nuevo eso significa medir su transporte, no darlo por igual al del X8 Pro.

Con el X8 Pro, medir el transporte fue:

- el descriptor del cable, en `hardware.md`;
- leerlo entero por cable, sin escribir (`dev/herramientas/leer-por-cable.py`);
- la Etapa 2 del cable: los codificadores contra el `SET_REPORT` capturado al
  cliente oficial escribiendo por cable (`test_etapa2_cable`, que hoy usa las
  capturas del X8 Pro);
- cuánto sangra el búfer por cable (`dev/herramientas/medir-sangrado.py`);
- escrituras de ida y vuelta por cable, releídas.

**Mientras eso no esté hecho, el perfil lleva `producto_cable=None`.** Con eso
`conexiones.py` no reconoce el cable como camino, y el programa le habla al
modelo solo por el dongle.

→ A `hardware.md`, a `evidencia.md` y a la bitácora, como cualquier otra
medición.

### 7. Declarar el perfil, y dejar que las pruebas corrijan

`driver/src/linshark/dispositivos.py` es el mecanismo —la clase `Perfil`, el
registro, `activo()`/`usar()`/`como()`— y no conoce ningún modelo en particular.
Los valores de **cada** modelo van en su propio archivo, dentro de
`driver/src/linshark/perfiles/`. Los campos obligatorios, con los valores del
X8 Pro como referencia de forma, no de contenido:

```python
# driver/src/linshark/perfiles/tu_modelo.py
from .. import protocol as p
from ..dispositivos import Perfil, Usb

TU_MODELO = Perfil(
    device_id=..., nombre="...", marca="...",
    usb=Usb(vendor=..., producto_dongle=..., producto_cable=None,   # paso 6
            interfaz=..., report_id=..., report_size=...),
    bloques={...},                  # el largo que declara cada comando
    escribibles=frozenset({...}),   # los que pasaron la Etapa 2 en ESTE modelo
    botones=18, slots_para_clic_izquierdo=(1, 2, 3, 4, 5),
    slots_de_rueda=(17, 18), remapeo_de_slots={...},
    botones_por_nombre={...}, como_se_supo_el_boton={...},
    niveles_dpi=8, dpi_minimo=100, dpi_maximo=40000,
    tasas=(125, ..., 8000),
    macro_eventos_max=50, macro_id_min=1, macro_id_max=255,
)
```

Opcionales: `tasa_maxima_por_cable` (1000 si no se declara),
`campos_ausentes` (los controles que en este chasis no harían nada, con su
motivo) y `perfil_embebe` (dónde el perfil completo embebe a cada bloque, que es
lo que habilita el cruce entre copias). `driver/src/linshark/perfiles/x8pro.py`
tiene cada uno con la cita de dónde salió.

Y se añade al registro en `driver/src/linshark/__init__.py`, junto a donde se
registra `X8_PRO`:

```python
from .perfiles.tu_modelo import TU_MODELO as _TU_MODELO
_dispositivos.registrar(_TU_MODELO)
```

Con eso, `estructuras.py` codifica y decodifica para **ese** modelo sin
modificar una línea: consulta el perfil en cada llamada.

Dos pruebas corregirán el trabajo, y existen para eso:

- `driver/tests/salvaguardas.py::test_el_perfil_no_miente` contrasta **cada
  campo contra la evidencia** —las capturas, los bloques del bus, `READ_SUB` del
  bundle—, no contra otra copia del mismo número. **Hoy lo hace solo con el
  X8 Pro** (`perfil_de(p.DEVICE_X8_PRO)`): un modelo nuevo tiene que sumarle
  sus comparaciones, contra sus propias capturas, o su perfil pasa sin que
  nadie lo mire;
- ese mismo archivo contiene una línea que **falla en cuanto aparece un perfil
  nuevo**. Debe retirarse manualmente, y esa fricción es deliberada: copiar el
  perfil del X8 Pro cambiándole el nombre es exactamente lo que no puede ocurrir
  en silencio.

### 8. Documentar lo que se sabe, y lo que no

- **`dev/models/<modelo>/docs/evidencia.md`**: la afirmación y cómo verificarla.
  MEDIDO es que alguien lo ha observado; LEÍDO es que lo declara el bundle;
  INFERIDO es que lo parece. **Amplificar una inferencia a hecho es el error que
  más veces ha estado cerca de costar caro en este proyecto.**
- **`dev/models/<modelo>/docs/bitacora.md`**: una entrada por sesión, con lo que
  no funcionó, y después `dev/herramientas/indexar-bitacora.py`.
- Las entradas **no se editan**: cuando una medición se corrige, la corrección se
  añade como entrada nueva que cita a la anterior.

### La incorporación está hecha cuando…

> - **`dev/models/<modelo>/`** tiene `docs/` —`hardware.md`, `protocolo.md`,
>   `evidencia.md`, `bitacora.md` y `capturas-w/` con sus `.txt`— y
>   `respaldos/`;
> - **`driver/src/linshark/perfiles/<modelo>.py`** existe y está registrado en
>   `linshark/__init__.py`;
> - **`driver/models/<modelo>/udev/`** tiene su regla. Hoy
>   `driver/instalar/install.sh`, `driver/instalar/uninstall.sh` y
>   `driver/scripts/instalar-udev.sh` nombran la regla del X8 Pro, y
>   `test_el_instalador_apunta_a_archivos_que_existen` busca una sola: el
>   segundo modelo obliga a generalizarlos. Sin la regla, el modelo existe en
>   el código y nadie puede hablarle sin root;
> - **`test_el_perfil_no_miente`** tiene sus comparaciones, y la línea que falla
>   ante un perfil nuevo se retiró;
> - **`dev/tests/evidencia.py`** e **`indexar-bitacora.py`** saben de su carpeta;
> - **el cable** está medido (paso 6), o el perfil dice `producto_cable=None`;
> - **la tabla de modelos del `README.md`** de la raíz tiene su fila;
> - **las cuatro tandas de pruebas pasan** (`AGENTS.md` §11).

---

## Obstáculos conocidos

1. **Un error de formato es indistinguible de un problema de enlace.** El
   dispositivo no responde «comando inválido»: no responde, y el dongle emite el
   mismo NAK que cuando se pierde el paquete por radio. Antes de culpar al
   enlace, conviene contrastar la trama contra el binario.
2. **El enlace de 2.4 GHz pierde peticiones de forma medible**: 95 % de éxito con
   el mouse en movimiento, 50 % en reposo. Toda prueba necesita reintentos, y
   conviene mover el mouse mientras se ejecuta.
3. **A tasas de sondeo altas el canal de configuración no responde.** Por encima
   de 1000 Hz los bloques largos no llegan, y una lectura que insiste puede dejar
   el dispositivo sin desplazar el puntero durante unos segundos.
4. **Abrir un cliente oficial obliga a revisar después.** La web reescribe todo
   lo que lee; el software nativo pisa el DPI, la corrección de ángulo y el
   tiempo de respuesta.
5. **Si un campo puede modificarse desde el propio hardware, esa es la mejor
   verificación disponible.** Dejar que el firmware lo escriba y leerlo después
   no depende del código propio ni del código del fabricante.

---

## Cuestiones abiertas en el modelo medido

El detalle, con el procedimiento de cierre de cada una, está en
[`dev/models/attackshark-x8pro/docs/SIGUIENTE-SESION.md`](models/attackshark-x8pro/docs/SIGUIENTE-SESION.md).
Las principales:

- **cuatro campos sin captura** (`dpi_ON_OFF_flag`, los colores de indicador,
  `Dpi_indication_type` y `lightMode`): son constantes en las 76 escrituras
  capturadas. No falta código, falta captura;
- **un segundo perfil**: el catálogo declara 47 modelos y hay **uno** medido.

---

## Pruebas de este subsistema

```bash
python3 dev/tests/evidencia.py
```

Comprueba que las afirmaciones se sostienen contra los respaldos y los
descriptores. Las del programa están en `driver/tests/`.
