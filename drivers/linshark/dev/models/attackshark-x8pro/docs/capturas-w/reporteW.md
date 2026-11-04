> **Documento historico: la copia tal como salio de Windows.**
> Se conserva sin tocar como artefacto de la captura y **no se actualiza**.
> Lo vigente esta en [`../protocolo.md`](../protocolo.md) y [`../evidencia.md`](../evidencia.md);
> si dicen cosas distintas, valen esos. La version que se mantenia al dia en
> `docs/reporteW.md` se retiro, absorbida por esos dos.

# Reporte Etapa W — Capturas desde Windows

**Proyecto:** LinuxAttackSharkX8pro  
**Etapa:** W  
**PC:** AUT01 (Windows)  
**Artefactos:** `<descargas>\`  
**Objetivo (fase2.md):** medir el helper oficial para cerrar inferencias y obtener tramas HID de escritura **MEDIDAS**, sin inventar bytes.

---

## Resumen ejecutivo

| Captura | Resultado | Archivo principal |
| -------- | --------- | ----------------- |
| **W1** WebSocket (`ws://localhost:10086`) | OK — 85 frames (15 tx / 70 rx) | `w1.har` → `w1-from-har.jsonl` |
| **W2** USB report rate | OK — 1 Interrupt OUT al dongle | `w2-rate.pcap` |
| **W2** USB DPI | OK — 1 Interrupt OUT al dongle | `w2-dpi.pcap` |

**Dongle:** `VID_1D57` / `PID_FA65`, device address 2, endpoint **OUT 0x03**, Report ID **0x04**.

**Conclusión:** Etapa W cumplida para rate y DPI. Fase 2 puede anclar escrituras a estas tramas (igualdad byte a byte).

---

## Entorno

- Helper: `WebDriver.exe` en `:10086` (Chrome conectado).
- Web: `https://szslxd-tech.com/#/` (X8 Pro).
- Herramientas: Wireshark 4.6.8, Npcap 1.84, USBPcap 1.5.4.0 (en esta carpeta).
- USBPcap requirió **reinicio** para exponer `\\.\USBPcap1`.
- W1: hook de Console falló (F5 borra el hook); se usó Plan B — Network → WS → HAR.

---

## W1 — WebSocket

### Método
Chrome DevTools → Network → WS → Preserve log → Save all as HAR with content → `w1.har`.

### Cierres de evidencia

#### connectionMethod = 0x83 (antes INFERIDO #1)
Presencia helper (**RX**): `83010308400164` = `[0x83, 0x01, 0x03, 0x08, 0x40, 0x01, 0x64]`.

#### Respuestas dongle (antes INFERIDO #3)
TX lecturas: `f083080b00` / `f083080600` / `f083080500` / `f083080400`  
= `[0xF0, conn, deviceId=0x08, cmd, sub]`

RX ejemplo versión: `83080b0808008301050000b5…`  
= `[conn, deviceId, cmd, sub, …payload]`

#### Escrituras WS (página → helper)
| Tipo | Hex (inicio) |
| ---- | ------------ |
| Report rate | `830806090133cc00000000000000000000` |
| DPI/perfil | `83080438…` (varias) |

Escrituras WS: `[conn, deviceId, cmd, sub, …]` **sin** `0xF0`.

---

## W2 — USB (USBPcap)

### W2-rate
`w2-rate.pcap` — única Interrupt OUT:

```
04 0e 00 06 09 01 44 bb 00 00 00 00 01 21 00 … (64 bytes)
```

| Bytes | Lectura |
| ----- | ------- |
| `04` | Report ID |
| `0e 00` | length LE = 14 |
| `06` / `09` | cmd / sub report rate |
| `01 44 bb` | valor + checksum aparente |

W1 tenía `01 33 cc` (otro rate). Mismo cmd/sub.

### W2-dpi
`w2-dpi.pcap` — única Interrupt OUT:

```
04 3d 00 04 38 01 01 11 3f 00 00 13 27 35 5e 87 f3 … (64 bytes)
```

| Bytes | Lectura |
| ----- | ------- |
| `04` | Report ID |
| `3d 00` | length LE = 61 |
| `04 38` | cmd/sub (alineado a W1 `83080438…`) |
| resto | DPI/perfil |

---

## Patrón HID de escritura (MEDIDO)

1. Página → helper: lecturas `[0xF0,conn,dev,cmd,sub]`; escrituras `[conn,dev,cmd,sub,…]`.
2. Helper → mouse: Interrupt OUT, Report ID `0x04`, luego `uint16` LE longitud, luego cuerpo.
3. Las escrituras medidas **no** usan el prefijo de lectura `0c a0`.

**Regla Fase 2:** reproducir capturas byte a byte antes de habilitar escrituras en Linux.

---

## Inventario

Primarios: `w1.har`, `w1-from-har.jsonl`, `w2-rate.pcap`, `w2-dpi.pcap`, `W1-RESULTADO.txt`, `W2-RESULTADO-rate.txt`, `W2-RESULTADO-dpi.txt`, `reporteW.md`.

---

## Limitaciones

- USB solo rate + DPI (faltan LOD/RGB/botones/macros si se quieren).
- Soft nativo **ATTACK SHARK X8 SOFT** no capturado (otro stack).
- Etapa 0 (respaldo) sigue siendo prerequisito antes de escribir desde Linux.

---

## Opinión: ¿medir también el software nativo de Windows?

**Sí como vía secundaria, no como reemplazo.**

El camino **web + WebDriver** es el que el puente Linux debe emular: ya está medido para rate/DPI.

El **X8 SOFT** (DuiLib + `hiddriver_*.dll`) es otro producto. Puede servir para sacar más comandos rápido, pero hay que etiquetar capturas `SOFT-` vs `WEB-` y comparar: si coinciden byte a byte, una sola tabla; si no, dos dialectos y no mezclarlos en el puente.

Orden sugerido: (1) archivar esto en el repo y Etapa 0 + igualdad byte a byte en Linux; (2) opcionalmente capturar SOFT después para LOD/RGB/macros.
