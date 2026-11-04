# Siguiente sesión — estado

Qué hacer al retomar. **Leer esto después de `AGENTS.md` y antes de tocar
nada.** Acá va solo el estado y lo que queda. Lo que ya pasó está en
[`bitacora.md`](bitacora.md), que se lee **por su índice**: la entrada que
toque, no el archivo entero.

La versión larga de esta nota —los planes cumplidos, el porqué de cada decisión
de la interfaz, la decisión de dibujar el esquema en SVG propio— quedó
archivada tal cual en la bitácora, en "La nota de retomar, archivada entera".

**Directriz vigente**: los comandos que tocan el mouse los corre el usuario, no el
asistente. Vale para escrituras, **lecturas** y mediciones. El asistente
prepara el comando con su condición física y espera la salida.

---

## El cambio de nombre a LinShark, hecho

Hecho el 2026-09-23: paquetes, lanzadores, instalación, ventana y carpetas del
usuario. Qué cambió, qué no, y lo que falló en el camino: la entrada "El
proyecto pasa a llamarse LinShark" de la bitácora.

## Después de una prueba

El mouse vuelve a como estaba antes: `AGENTS.md`, §5, "Después de una prueba".
El repositorio no guarda la configuración de ningún mouse; lo que el programa
anota vive en `~/.local/state/linshark/`.

> **Una trampa del formato de respaldo**: el `despues-de-escribir-*` de una
> corrida que bajó la tasa registra **1000 Hz**, porque se toma antes del
> `finally` que la devuelve. Para la tasa real,
> `driver/scripts/cambiar-rate.py` sin `--valor`, que solo mira.

---

## Lo que queda

**No queda nada técnico que dependa del código, y nada de esto bloquea.**

### Contra el hardware (lo corre el usuario)

| Qué | Cómo se cierra |
| --- | --- |
| La ventana **desde la instalación** | La instalación y la desinstalación ya corrieron de punta a punta; lo que no se vio es `linshark-gui` abriendo desde `/opt`, o sea el `venv` y los imports instalados. Instalar y abrir la ventana una vez |
| El byte de estado con la **batería llena** | `1` (a batería) y `3` (cargando) están MEDIDOS. Un valor para "cargado" no se vio. Hace falta cargar con algo que **no** sea la PC, porque con el cable puesto el dongle se calla. Es de horas |
| Si el firmware **suelta los botones del mouse** al terminar un macro | Lo medido es con teclas; el alcance a los botones queda INFERIDO. La prueba traba un botón a propósito y la única salida es desacoplar el dongle: la menos valiosa y la más molesta |
| La rama de **tiempos largos del macro** (>127 ms) | Decodificada y escribible, pero INFERIDA del bundle (`Qve`). Se cierra escribiendo un macro con un retardo largo y mirando si sale, o capturando al soft grabando uno |
| El **botón de modo** | MEDIDO que el slot 7 es ese botón y que cambiar de canal no depende de su función. Falta cuántos modos cicla, en qué orden, y si el código 60 hace algo además de callar |

### Falta captura, no código

Se consiguen con la VM y usbmon (`captura-kvm.md`). Sin captura no hay Etapa 2,
y escribirlos sería inventar bytes.

- `dpi_ON_OFF_flag`, `Dpi_indication_type`, `lightMode`: constantes en las 76
  escrituras capturadas.
- **Los colores de nivel de dpi.** El LED los usa (MEDIDO), pero ningún cliente
  oficial los escribe: la web no puede y el soft no le habilita el diálogo a
  este mouse. Las vías que se consideraron están en la bitácora.
- Si la página manda macros de **131 bytes** donde el soft manda 111. Hay que
  pagar el peaje: abrir la página pisa dpi, ripple, luz y rueda.
- Qué frecuencia deja el byte de rate `0x01`. Puede dejar el mouse en 8 kHz.
  Con `0x02` el mouse reportó a 8000 Hz, pero ya estaba en 8000: no lo cierra
  (bitácora, "Un byte de tasa que no se entiende dejaba a la ventana afuera").

### Sin camino barato

- **Cmd 7** (modo de despertado): no se puede leer, así que no hay Etapa 3.
- El valor absoluto del corte del **LOD**: el protocolo de la escalera está en
  la bitácora.
- Cuál de las dos fórmulas es el **dpi real del sensor** (I-W11): hace falta
  medir desplazamiento físico.
- `responseTime` como debounce: INFERIDO del nombre del control.

### Dos misterios sin con qué cerrarlos

- **La corrupción del bloque de versión** (`08 00 83 01 01 00` →
  `08 74 0b 01 01 00`): una sola muestra, y no es el sangrado de cmd 6. El
  canario la detecta, que es lo que importa.
- **Por qué un macro de un solo evento no corre.** Con dos y con tres sí, así
  que no es la paridad.

### Un segundo modelo

Llenar un `dispositivos.Perfil` y sus carpetas en `models/`, **con la captura de
su driver oficial**. Copiar el del X8 Pro y cambiarle el nombre es lo que
`test_el_perfil_no_miente` se pone rojo para impedir. Receta en
[`dev/README.md`](../../../README.md).

---

## Las lecciones que se acumularon, y siguen valiendo

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
   no depende de nuestro código ni del del fabricante.
10. **Un experimento anotado en los docs es una hipótesis, no un
    procedimiento.** Cuando un experimento diseñado no contesta, la primera
    sospecha no es el hardware: es que mide dos cosas.
