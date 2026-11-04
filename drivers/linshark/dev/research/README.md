# Material de referencia del fabricante

Material de terceros que respalda lo documentado en `docs/`. De cada pieza se
conserva **la huella, no el material**: se trata de binarios y *bundles*
propietarios. El manifiesto de hashes basta para que una auditoría descargue lo
mismo y compruebe que las citas de `docs/` proceden de esos bytes exactos.

El material es **común a los 47 modelos** del catálogo del fabricante: la misma
aplicación web y el mismo servicio auxiliar sirven a todos, de modo que este
directorio no pertenece a ningún modelo en particular.

## `webapp/`

El *bundle* de <https://szslxd-tech.com>.

**No se versiona en el repositorio**: es código propietario de un tercero, igual
que el servicio auxiliar de Windows. Lo que sí está versionado es
`webapp.sha256`, con la huella de los 216 archivos consultados.

Para descargarlo y verificarlo:

```bash
dev/research/bajar-webapp.sh   # descarga a dev/research/webapp/ y ejecuta sha256sum -c
```

Contenido resultante:

- `app.js` — el *bundle* principal (1,5 MB), copia local de
  `assets/index-CHmxtNQf.js`. Contiene el almacén de Pinia, donde reside todo el
  protocolo del lado de la aplicación web. Es el archivo que citan
  `docs/evidencia.md`, `docs/protocolo.md`, `dpi.py` y `estructuras.py`.
- `chunks/` — los 211 fragmentos de carga diferida. Los relevantes para el X8 Pro
  son `indexX8Pro-*.js` y `dpiX8Pro-*.js`; cada modelo tiene los suyos.
- Los cuatro archivos sueltos en `webapp/` son copias de los más citados, por
  comodidad.

Todo procede de `https://szslxd-tech.com/assets/<nombre>`. Los nombres incorporan
la huella de compilación de Vite, de modo que **una versión nueva del sitio no
sobrescribe a la anterior: cambia de nombre**. Si `bajar-webapp.sh` falla con un
404 o con una huella distinta, el sitio ha publicado una compilación nueva y las
citas de `docs/` deben releerse contra ella, en lugar de actualizar el manifiesto
sin más.

## El servicio auxiliar de Windows

**No se versiona en el repositorio**: es software propietario y ocupa 4,7 MB. Se
descarga de <https://szslxd-tech.com/downloads/WebDriverSetup.exe>, enlace
presente en la propia plataforma, en la pantalla de descarga del controlador.

Huellas de lo analizado:

```
ec2e171e593f6219af1fca7bc8101bf6967347c0d34855d7bee69acaf6d3c4da  WebDriverSetup.exe
0eea3fef04f796332cdf0e07b7c14a8bc0bf427480839db668ea82096e60f1dc  app/WebDriver.exe
4f119fe8bb9d3382013632e94f61b4841e724e8c2ebc11146abcea7013bc75d8  app/hidapi.dll
```

## El software nativo de Windows

`ATTACK SHARK X8 SOFT.exe` es **un producto distinto** (DuiLib más
`hiddriver_*.dll`), no el servicio auxiliar del navegador. Se analiza igualmente
porque escribe con el mismo molde HID, pero sus capturas se etiquetan `soft-` y
no se mezclan con las `web-`.

Tampoco se versiona. Huella de la versión analizada:

```
b54043ca726adf5d4aed061283472845efded61a3aef0fca8e7d983a05f3af66  ATTACK SHARK X8 SOFT.exe
```

## Reproducir la extracción

```bash
dev/herramientas/extraer-helper.sh ~/Descargas/WebDriverSetup.exe /tmp/helper
```

Ese script **no ejecuta nada de Windows**: `innoextract` se limita a descomprimir
el blob LZMA del instalador Inno Setup, y `objdump` solo lee. Los
desplazamientos citados en `docs/protocolo.md` corresponden al `WebDriver.exe` de
la huella indicada arriba.
