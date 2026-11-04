> **Documento historico: la copia tal como salio de Windows.**
> Se conserva sin tocar como artefacto de la captura y **no se actualiza**.
> Lo vigente esta en [`../protocolo.md`](../protocolo.md) y [`../evidencia.md`](../evidencia.md);
> si dicen cosas distintas, valen esos. La version que se mantenia al dia en
> `docs/reporteWsoft.md` se retiro, absorbida por esos dos.

# Etapa W — soft nativo Windows vs WebDriver

Etapa: W  
Máquina: AUT01  
Dongle: VID `1D57` / PID `FA65` · USBPcap `\\.\USBPcap1` · device address 2 · EP OUT `0x03`  
Proceso: **AttackShark** (soft oficial Windows, no el WebDriver del navegador)

Nota del operador: en soft se eligieron **valores de rate/DPI deliberadamente distintos o iguales** a los de la pasada web. Las diferencias de bytes de valor/checksum son esperables; lo que importa es el **framing** (Report ID, length, cmd/sub, endpoint).

---

## Capturas

| Artefacto | Contenido |
|-----------|-----------|
| `w2soft-rate.pcap` | Soft: cambio report rate |
| `w2soft-dpi.pcap` | Soft: cambio DPI / perfiles |
| `w2soft-rate-outs.txt` / `w2soft-dpi-outs.txt` | Extracción tshark Interrupt OUT + `usbhid.data` |
| Referencia web | `w2-rate.pcap`, `w2-dpi.pcap`, `reporteW.md` |

Filtro tshark (igual que Etapa W web):

```text
usb.transfer_type == 0x01 && usb.endpoint_address.direction == 0 && usbhid.data
```

---

## Resultado: soft y web usan el mismo molde HID

### Report rate

| Origen | HID Interrupt OUT (`usbhid.data`) |
|--------|-----------------------------------|
| **Soft** | `04 0e 00 06 09 01 34 cb 00 00 00 00 01 21 00 00 00 00 00 00` |
| **Web** | `04 0e 00 06 09 01 44 bb 00 00 00 00 01 21 00 00 00 00 00 00` |

Igual en soft y web:

- Report ID `04`
- Length LE `0e 00` (14)
- Cmd/sub `06 09`
- EP OUT `0x03`
- Un solo Interrupt OUT por acción

Difiere (esperado: otro valor de rate elegido):

- Byte de valor + checksum: soft `01 34 cb…` vs web `01 44 bb…`

### DPI / perfiles

| Origen | Prefijo del OUT (resto del body distinto por valores) |
|--------|--------------------------------------------------------|
| **Soft** | `04 3d 00 04 38 01 01 01 3f 20 00 17 2f 3f 6f 9f 8f …` |
| **Web** | `04 3d 00 04 38 01 01 11 3f 00 00 13 27 35 5e 87 f3 …` |

Igual en soft y web:

- Report ID `04`
- Length LE `3d 00` (61)
- Cmd/sub `04 38`
- EP OUT `0x03`
- Un solo Interrupt OUT por acción

Difiere (esperado: otros DPI/perfiles):

- Payload interno y checksum; soft empieza `…01 01 01 3f 20…`, web `…01 01 11 3f 00…`

---

## Conclusión

1. El **soft nativo Windows** escribe al dongle con el **mismo framing** que el WebDriver oficial vía helper: `Report ID 04` + `uint16 LE length` + body (`06 09` rate / `04 38` DPI).
2. No hay indicios, en estas dos acciones, de otro Report ID, otro endpoint, o un protocolo paralelo distinto al de la web.
3. Los bytes de valor/checksum cambian con el setting elegido; **no** se exige igualdad byte-a-byte con la captura web si el operador no usó el mismo rate/DPI.
4. Para builders Linux MEDIDO: reutilizar el molde de `reporteW.md`; validar con frames soft+web del mismo setting cuando se quiera igualdad de valor.

---

## Relación con hallazgos previos

| Hallazgo | Soft vs web |
|----------|-------------|
| Frame write ≠ prefix read `0c a0` | Confirmado también en soft |
| Rate `06 09` / DPI `04 38` | Mismos cmd/sub en soft |
| Un OUT por acción | Igual en soft |

Ver también: [reporteW.md](reporteW.md) (pasada WebDriver).
