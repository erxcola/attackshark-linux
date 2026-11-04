# Cómo contribuir

Las aportaciones son bienvenidas, y la más valiosa no es código: es **evidencia**.
La infraestructura ya es multimodelo; lo que falta de cada dispositivo es la
captura de cómo lo configura su driver oficial.

Al enviar una contribución se entiende que se aporta bajo la licencia del
proyecto, **GPL-2.0-or-later**, y que quien la envía tiene derecho a hacerlo.

No hay proceso de ramas ni plantilla de propuesta. Lo que decide si una
aportación entra es el criterio de aceptación de
[`dev/README.md`](dev/README.md) y que pasen las cuatro tandas de pruebas.

---

## Antes de escribir código

Leer, en este orden (es la lista para quien llega de afuera; la de quien retoma
una medición está en `AGENTS.md` §3):

1. [`dev/docs/metodo.md`](dev/docs/metodo.md) — las cuatro etapas y las
   salvaguardas. Es la norma del proyecto, no una sugerencia.
2. [`dev/README.md`](dev/README.md) — el procedimiento completo para incorporar
   un modelo.
3. [`AGENTS.md`](AGENTS.md) — las reglas del proyecto (§1) y el estado actual,
   condensado.

## Las reglas que no se negocian

Son las mismas para personas y agentes, y existen porque el software escribe en
la memoria no volátil de un dispositivo físico que puede quedar inservible.
Están en un solo lugar, [`AGENTS.md` §1](AGENTS.md#1-reglas-que-no-se-negocian),
para que no haya dos versiones que diverjan. Las que más suelen sorprender:

- **Ningún byte que no se haya observado antes**, ni para probar: cada trama
  sale de una captura del driver oficial o del desensamblado de su binario, con
  la fuente citada en el código.
- **Toda escritura pasa por las cuatro etapas** de
  [`metodo.md`](dev/docs/metodo.md), la última contra el hardware.
- **Las escrituras, lecturas y mediciones contra el mouse las corre quien lo
  tiene sobre la mesa.** Una propuesta trae el comando exacto y su condición
  física (mover el mouse, no tocarlo durante N minutos); no se asume que alguien
  más lo va a correr a ciegas.
- **La bitácora no se edita** y **el material del fabricante no se
  redistribuye**.

## Antes de enviar

```bash
python3 driver/tests/salvaguardas.py
python3 driver/tests/simula_pagina.py
QT_QPA_PLATFORM=offscreen python3 driver/tests/interfaz.py
python3 dev/tests/evidencia.py
```

Las cuatro tandas se ejecutan **sin el dispositivo físico** y deben pasar. Si una
salvaguarda estorba, la vía no es desactivarla: es explicar en la propuesta qué
impide y por qué.

Un mensaje nuevo en la interfaz necesita su fila en `linshark_ui/i18n.py`, o
`test_no_queda_nada_sin_traducir` fallará.

## Aportar un modelo nuevo

El camino está en [`dev/README.md`](dev/README.md), con el criterio de aceptación
de cada paso. Hace falta el dispositivo, una VM de Windows con el software del
fabricante y tiempo: el X8 Pro llevó diez días, la mitad en obstáculos que ya
están resueltos.

**Antes de copiar `x8pro.py`:** `driver/tests/salvaguardas.py` tiene una línea
que falla deliberadamente en cuanto aparece un perfil nuevo, y hay que retirarla
a mano. Esa fricción es intencionada: copiar el perfil existente cambiándole el
nombre es exactamente lo que no puede ocurrir en silencio. Y
`test_el_perfil_no_miente` hoy contrasta solo los campos del X8 Pro contra sus
capturas; un modelo nuevo le suma las comparaciones contra las suyas.

Qué tiene que traer una contribución de modelo completa —de las capturas a la
regla de `udev` y la fila del `README.md`— está en un solo lugar:
[«La incorporación está hecha cuando…»](dev/README.md#la-incorporación-está-hecha-cuando),
al final del procedimiento. La entrada de bitácora lleva lo que se escribió, lo
que se releyó y **lo que se observó físicamente**, incluido lo que no funcionó.

## Aportaciones que no necesitan hardware

- **Traducciones.** La interfaz se traduce por el texto castellano exacto en
  `driver/src/linshark_ui/i18n.py`. Los README de la raíz y de `driver/`
  tienen su versión en inglés y en chino: cada una dice en su primera línea el
  sha256 del castellano que tradujo, y una prueba avisa cuando el castellano
  cambió desde entonces. Un idioma nuevo es un archivo más y una entrada en
  `TRADUCCIONES_DEL_README` (`driver/tests/salvaguardas.py`). `dev/`,
  `AGENTS.md` y este archivo no se traducen, a propósito: son procedimiento y
  evidencia, y quien aporta un modelo lee el original.
- **Empaquetado** para distribuciones.
- **Revisión de la evidencia.** Si una afirmación de
  [`evidencia.md`](dev/models/attackshark-x8pro/docs/evidencia.md) está
  clasificada como MEDIDO y no lo está, es un error que interesa conocer. Vale
  como contribución por sí solo.

## Incidencias

Al informar de un problema, conviene incluir la salida de:

```bash
driver/scripts/donde-esta-el-mouse.py
```

que indica el modelo, el camino de conexión, el puerto y los permisos, y **no
toca el dispositivo**. Si el problema aparece al escribir, adjuntar también el
contenido de la pestaña **Registro** de la aplicación.
