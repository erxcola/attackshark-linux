# El software nativo de escritorio

`ATTACK SHARK X8 SOFT.exe` (sha256 `b54043ca…`) es **un producto distinto**, no
el servicio auxiliar del navegador. Se analiza porque escribe con el mismo molde
HID —`capturas-w/soft-todo.txt`: 46 escrituras, las 46 reproducidas byte a byte
por `build_write_frame()`—, pero su superficie de comandos **no es la misma**.

Se extrae sin ejecutar nada:

```bash
dev/herramientas/extraer-soft.sh ~/Descargas/"ATTACK SHARK X8 SOFT.exe"
```

Es un instalador **Inno Setup 6.1.0**, igual que `WebDriverSetup.exe`, de modo
que se abre con `innoextract` (descompresión pura). 591 archivos.

## Composición

| Ruta | Contenido |
| :--- | :--- |
| `app/AttackShark.exe` | 1,7 MB, DuiLib. Las clases se denominan `CMS_<N>_Page`, `CMS_<N>_Macro`… (RTTI legible) |
| `app/hiddriver_<N>.dll` | 18 controladores, uno por modelo, más `hiddriver_4k_1.dll` |
| `app/res/skins/ms_<N>/` | 18 temas, uno por modelo. **Solo imágenes**, sin XML |
| `app/res/*.xml` | la interfaz, compartida entre modelos (`main.xml`, `DpiColorDialog.xml`, `macromenu.xml`…). Las **pantallas por modelo se componen en código**, no en XML: no existe un XML por `ms_<N>` |
| `app/res/lan/*.xml` | 13 idiomas. **`EN.xml` es el inventario completo de opciones** |

**El X8 Pro es el modelo 13.** No se deduce del binario, sino de lo que el propio
software escribió en el disco de Windows: el macro grabado manualmente con este
dispositivo quedó en `ms_13/macro.data`. Los directorios `ms_<N>` no incluyen el
nombre del modelo, y el VID/PID no aparece en texto plano en los
`hiddriver_<N>.dll`, que además son genéricos: exportan `Hid_Read`, `Hid_Write`,
`Set_VIDPID` y poco más.

## El selector de color de DPI

`app/res/DpiColorDialog.xml` es una ventana emergente de 250×200 con una
`ColorPalette` continua, campos **R / G / B numéricos** de tres dígitos —es
decir, un color arbitrario de 24 bits, no una lista— y dieciséis valores
predefinidos denominados `mouse_dpi_color_1..16`.

**Y la página del X8 Pro lo instancia.** La vtable de `CDpiColorWnd`
(`0x4ef7d4`) se referencia desde 36 puntos de `.text` en **18 pares regulares**,
y hay 18 modelos. Por RTTI, los constructores de `CMS_12_Page`, `CMS_13_Page` y
`CMS_14_Page` están en `0x435444`, `0x440164` y `0x44b444`; el par `0x44249f` /
`0x442a96` cae dentro del rango de la 13, y los otros dos pares dentro del suyo.
Un par por clase, en orden.

**Pero el control no aparece en la interfaz.** Se buscó, y el software no habilita
esa opción para este modelo. Lo que el binario demuestra es que la clase de esa
página **contiene** el código que construye el diálogo, no que sea alcanzable
desde la interfaz: las dieciocho páginas son copias de la misma clase —los pares
de instanciación están espaciados de forma idéntica— y en dieciocho copias el
código está presente aunque el control no se cree.

De modo que **no existe hoy ningún cliente oficial que escriba los ocho colores**,
y sin captura no hay Etapa 2. Ver `bitacora.md`.

## Opciones presentes en el software nativo y ausentes en la web del X8 Pro

Extraídas de `app/res/lan/EN.xml`:

- **Iluminación completa**: `Light Settings`, `Lightning`, `Breathing`, `Color
  Breathing`, `Rainbow Wave`, `Breathing DPI`, `Brightness:`, `Color:`,
  `Speed:`. La página del X8 Pro **no expone ninguna**: allí el bloque cmd 5
  viaja como portador de la distancia de despegue y del tiempo de respuesta (ver
  `indexX8Pro-BTVvPdTw.js`).
- **Perfiles a bordo**: `Add / Edit / Delete / Rename / Reset / Import / Export
  Profile`, `Profile +`, `Profile -`, `Profile Cycle`.
- **Energía**: `Power Management`, `Power Saving`, `Sleep Time:`, `Deep Sleep
  Time:`.
- **`Easy Aim`**, **`E-sports`**, `Angle Snap`, `Motion Sync`, `Ripple Control`.
- **`Lift Of Distance`** con `1 MM` / `2 MM`.
- Acciones de botón que la web no ofrece: `DPI Cycle`, `DPI +`, `DPI -`, `Double
  Click`, `Button Off`, `Custom Key Combination`, y toda la familia
  `Browser …` / `Media` / `Calculator`.

## El comando 0x0c

El software nativo emite un comando que la web nunca emitió:

    04 0f 00 0c 0a 01 fe 01 fe 00 00 00 00 02 27

`INFERIDO #5` afirmaba que `0x0c` con `sizeTotalData = 0x0a` figuraba «en las
tablas del binario pero sin invocación conocida desde la interfaz gráfica». Ya no
es así. El bloque consta de dos pares valor + complemento (`01 fe`, `01 fe`), el
mismo lenguaje del byte de tasa de sondeo y del cmd 7.

**Qué opción lo desencadena sigue sin determinarse.** Es una de las de la lista
anterior, y se averigua capturándolas una por una.

## La rueda

La restauración de fábrica del **WebDriver invierte el sentido de
desplazamiento**; la del software nativo lo deja correcto (observado contra el
hardware). Ambas aplicaciones escriben de forma distinta en algún campo. Las dos
restauraciones están capturadas (`web-todo.pcap`, `soft-todo.pcap`): un diff
debería identificar el campo.

### Diferencias entre ambas restauraciones de fábrica

El bloque de DPI que escribe cada una:

    web  reset:  01 01 11 3f 00 20 17 2f 3f 6f 9f 8f …
    soft reset:  01 01 01 3f 20 00 17 2f 3f 6f 9f 8f …
                       ^^    ^^ ^^

Los valores de DPI son idénticos. Difieren en dos aspectos:

**1. Dónde sitúan el `0x20`.** Con las etiquetas actuales de `estructuras.py`, la
web lo escribe en `DPI_Y_Double_Flag` y el software nativo en
`DPI_X_Double_Flag`. El respaldo posterior (`despues-de-los-resets.json`, tomado
con el software nativo como último en escribir) muestra el dispositivo con `20`
en el campo X. Ese `0x20` es el bit 5 = nivel 6, y es lo que hace que el nivel 6
valga 20000 × 2 = 40000, que es lo que muestra la interfaz. O una de las dos
aplicaciones lo escribe en el campo equivocado, o las etiquetas del proyecto
están desplazadas.

**2. El byte denominado `SensitivityY`:** la web escribe `0x11` y el software
nativo `0x01`. Difieren únicamente en el bit 4 (`0x10`).

Observado contra el hardware: la restauración de la **web invierte** el sentido
de desplazamiento, y la del **software nativo lo deja correcto**. El bit 4 de ese
byte es el único candidato restante una vez explicado el `0x20` como indicador de
duplicación de DPI.

**No está confirmado**: es una inferencia a partir de dos observaciones, no una
prueba. Se confirma en un paso: aplicar la restauración de la web (rueda
invertida), leer con `respaldar.py` y comprobar si el byte quedó en `0x11`.

Conviene tener presente que ese byte transporta además otros indicadores: en la
tanda de la web tomó los valores `00`, `01`, `10` y `11` mientras se accionaban
corrección de ángulo, sincronización de movimiento y control de fluctuación, de
modo que es un byte de bits y no un campo aislado.

---

## Los archivos que almacena en disco

Extraídos de una copia de su carpeta de datos. Constituyen una **tercera fuente**,
independiente del *bundle* web y del bus.

    CONFIG.ini          [SETTING] lanId=7, Feedback=0, Startup=0
    ms_1 .. ms_18/      una carpeta por modelo
      pro.data          el perfil; 18 archivos distintos, no una plantilla
      macro.data        el macro, únicamente donde existe alguno

### `macro.data` — decodificado por completo

    0x00..0x1f   nombre, UTF-16LE, 16 caracteres
    0x20..0x33   veinte bytes a cero
    0x34..0x37   número de eventos, dword LE
    0x38..       eventos de 16 bytes cada uno:
                   +0        00
                   +1        usage id
                   +2        dirección: 1 = pulsar, 2 = liberar
                   +3        00
                   +4..7     retardo en ms, dword LE
                   +8..15    cero

El archivo ocupa 3096 B fijos, es decir, capacidad para 190 eventos.

**Los usage id no son los códigos de `FUNCIONES_DE_BOTON`**: son usages HID de
teclado (A=4, B=5, …) y cinco códigos propios para los botones del mouse,
241..245. Un macro grabado manualmente accionando los cinco botones quedó
registrado como `f1 f3 f5 f4 f2` con retardos de 10 ms, que se interpreta como
izquierdo, rueda, atrás, adelante y derecho: exactamente el orden en que se
accionaron. Eso confirma la tabla del *bundle* desde un archivo del software
nativo de Windows.

### `pro.data` — útil para la tabla, inservible como estado

609 244 B, de los cuales **280 no son cero**. Los datos están dispersos en
regiones, y los botones son registros de 10 bytes:

    [índice, código, 00 00 00 00 00 00, 0x32, 0x02]

Los códigos coinciden con los de `FUNCIONES_DE_BOTON`, que es lo valioso: la
tabla queda validada desde una tercera fuente.

**Pero no describe este dispositivo.** El `pro.data` del directorio que el
software modificó durante la prueba contiene 17 registros —no 18— con ciclo de
perfil, inclinación de rueda a izquierda y derecha, y nueve entradas de «función
bloqueada» (código 0, no 1 = apagado). El X8 Pro tiene botón de modo, ciclo de
DPI y rueda arriba/abajo. **No es una permutación: son contenidos distintos.** De
modo que no sirve para deducir la asignación de este modelo, y conviene no
emplearlo como fuente de estado.
