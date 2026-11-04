# 📋 Modelos Suportados

## ✅ Modelos Testados e Funcionais

### Série Nordic (X8 Ultimate, X11 Ultra)

Usa o driver **x11-ultra** (protocolo Nordic 54L15).

| Modelo | USB ID (dongle) | USB ID (cabo) | Polling Max | Status |
|--------|----------------|---------------|-------------|--------|
| **X8 Ultimate** | `3554:f517` | `3554:f515` | 8000 Hz | ✅ Testado |
| **X11 Ultra** | `3554:f517` | `3554:f515` | 8000 Hz | ✅ Testado |
| **X11 Ultra Carbon** | `3554:f517` | `3554:f515` | 8000 Hz | ✅ Testado |

**Características:**
- Polling: 125/250/500/1K/2K/4K/**8K Hz**
- DPI: 50 até 60.000 (PAW3395 / PAW3950)
- LED por gear (cores RGB)
- Battery reporting
- Sensor: LOD, angle snapping, ripple control, motion sync

### Série LXDDZ/Beken (X8 Pro, X3 Pro)

Usa o driver **LinShark** (protocolo LXDDZ/Beken).

| Modelo | USB ID (dongle) | USB ID (cabo) | Polling Max | Status |
|--------|----------------|---------------|-------------|--------|
| **X8 Pro** | `1d57:fa65` | `1d57:2126` | 8000 Hz | ✅ Testado |
| **X11 (antigo)** | `1d57:fa55` | `1d57:fa60` | 1000 Hz | 🔶 Compatível |

**Características:**
- Polling: 125/250/500/1K/2K/4K/**8K Hz** (wireless), 1K Hz (cabo)
- DPI: 100 até 40.000 (steps de 50)
- LED por gear (sem RGB no X8 Pro)
- Macros e remapeamento de 18 botões
- Sleep timers

---

## 🔶 Modelos Compatíveis (Não Testados)

Estes modelos **devem funcionar** pois usam o mesmo protocolo LXDDZ/Beken, mas **não foram testados ainda**.

### Attack Shark
- X3 Pro
- X8 SE
- X8 Plus
- G3
- X11 SE
- K85 (teclado)
- K86 (teclado)

### MambaSnake
- M2
- M3
- M5

### INX
- X3
- X5

Se você tem um desses modelos, **teste e reporte** os resultados! Veja [Como Contribuir](../CONTRIBUTING.md).

---

## ❓ Modelo Não Listado?

### Como verificar se seu mouse é compatível:

1. **Conecte o mouse** (dongle ou cabo)

2. **Rode o detector:**
   ```bash
   python3 scripts/detectar-mouse.py
   ```

3. **Se aparecer "ATTACK SHARK" no lsusb:**
   - ✅ Há grandes chances de funcionar!
   - 📝 Abra uma [issue](https://github.com/SEU-USUARIO/attackshark-linux/issues) reportando:
     - Modelo exato
     - USB ID (formato `1234:5678`)
     - Qual software oficial você usa no Windows (web ou app)

4. **Se não funcionar:**
   - Seu mouse pode usar um protocolo diferente
   - Veja [Como Adicionar Suporte](adicionar-modelo.md)

---

## 🔬 Como Adicionar um Modelo

Veja o guia completo: **[docs/adicionar-modelo.md](adicionar-modelo.md)**

**TL;DR:**
1. Capture tráfego USB do driver oficial no Windows
2. Documente o protocolo
3. Crie um perfil para o modelo
4. Teste e submeta um PR

Contribuições são muito bem-vindas! 🙏

---

## 📊 Chipsets Conhecidos

### Nordic nRF54L15 / nRF52840
- **Modelos:** X8 Ultimate, X11 Ultra
- **USB Vendor:** `3554` (Compx)
- **Polling:** Até 8000 Hz
- **Driver:** x11-ultra

### LXDDZ / Beken BK52820
- **Modelos:** X8 Pro, X8 SE, X11 antigo
- **USB Vendor:** `1d57`
- **Polling:** Até 8000 Hz (wireless), 1000 Hz (cabo)
- **Driver:** linshark

### PixArt Sensors
- **PAW3950** (X8 Ultimate): até 42.000 DPI
- **PAW3395** (X8 Pro/X11 Ultra): até 40.000 DPI
- **PAW3370** (X8 antigo): até 19.000 DPI

---

## 🆘 Troubleshooting

### Mouse não é detectado

```bash
lsusb | grep -i "attack\|shark\|compx\|1d57\|3554"
```

Se aparecer algo, anote o USB ID e abra uma issue.

### Mouse detectado mas driver não funciona

1. **Tente os dois drivers:**
   ```bash
   # Tente X11-Ultra
   cd ~/attackshark-linux/drivers/x11-ultra
   python3 probe.py
   
   # Tente LinShark
   cd ~/attackshark-linux/drivers/linshark
   ./driver/linshark-gui
   ```

2. **Capture logs e reporte:**
   ```bash
   python3 probe.py 2>&1 | tee mouse-debug.log
   ```

3. **Abra uma issue** com o log anexado.

---

**Voltar para:** [README Principal](../README.md) | [Documentação](README.md)
