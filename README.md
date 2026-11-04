# 🦈 AttackShark-Linux

**Drivers nativos Linux para mouses Attack Shark** — Suporte completo para toda a linha Attack Shark (X8 Pro, X8 Ultimate, X11 Ultra e mais) sem precisar do software oficial Windows/macOS.

[![License: GPL-2.0+](https://img.shields.io/badge/License-GPL%202.0+-blue.svg)](LICENSE)
[![Nobara](https://img.shields.io/badge/Testado%20em-Nobara%20Linux-blueviolet)](https://nobaraproject.org/)

**Português** | **[English](README.en.md)**

---

## 🎯 O que é?

Projeto unificado que detecta automaticamente qual mouse Attack Shark você tem conectado e instala o driver correto:

- **LinShark** (para modelos LXDDZ/Beken): X8 Pro, MambaSnake, INX
- **X11-Ultra** (para modelos Nordic): X8 Ultimate, X11 Ultra, X11 Carbon

Você **não precisa saber** qual chipset seu mouse usa — o instalador detecta tudo automaticamente.

---

## ✨ Funcionalidades

### 🖱️ Configuração Completa do Mouse

✅ **DPI:** 50 a 60.000 (ajuste fino de 50 em 50)  
✅ **Polling Rate:** 125Hz até **8000Hz** (125/250/500/1K/2K/4K/8K)  
✅ **RGB/LED:** Cores por gear, efeitos (breathing, always-on), brightness  
✅ **Bateria:** Nível de carga e status de carregamento  
✅ **Sensor:** Lift-off distance, angle snapping, ripple control, motion sync  
✅ **Botões:** Remapeamento, macros, debounce (4-50ms)  
✅ **Energia:** Sleep timer, hibernação

### 🎨 Interface

- **GUI moderna** (Qt6/PySide6) com tema dark/light
- **CLI completo** para automação e scripts
- **Detecção automática** de conexão (2.4GHz dongle ou cabo USB)
- **Backup/restore** de configurações
- **Sem root** (após instalar regras udev)

---

## 🚀 Instalação Rápida

```bash
git clone https://github.com/erxcola/attackshark-linux.git
cd attackshark-linux
./install.sh
```

O script vai:
1. ✅ Detectar automaticamente seu mouse
2. ✅ Instalar dependências (Qt6, Python 3.10+)
3. ✅ Compilar o driver correto
4. ✅ Configurar regras udev (acesso sem root)
5. ✅ Adicionar atalho no menu de aplicativos

Depois da instalação:
```bash
attackshark-gui    # Abrir interface gráfica
# ou
attackshark-cli    # Usar linha de comando
```

---

## 📦 Modelos Suportados

### ✅ Totalmente Testados

| Modelo | Chipset | USB ID (dongle / cabo) | Status |
|--------|---------|------------------------|--------|
| **X8 Ultimate** | Nordic 54L15 | `3554:f517` / `3554:f515` | ✅ Testado |
| **X11 Ultra** | Nordic 54L15 | `3554:f517` / `3554:f515` | ✅ Testado |
| **X8 Pro** | LXDDZ/Beken | `1d57:fa65` / `1d57:2126` | ✅ Testado |

### 🔶 Compatíveis (não testados)

Outros 46+ modelos do catálogo Attack Shark/MambaSnake/INX que usam o mesmo protocolo LXDDZ/Beken:
- X3 Pro, X8 SE, X8 Plus, G3, X11 SE
- MambaSnake M2/M3/M5
- INX X3/X5

**Seu modelo não está na lista?** Veja [Como Adicionar um Modelo](docs/adicionar-modelo.md).

---

## 🛠️ Requisitos

### Sistema
- **Linux** com `udev` e `hidraw` (qualquer distro moderna)
- **Python 3.10+**
- **Qt6** (para GUI) ou **PySide6** (instalado automaticamente se necessário)

### Testado em
- ✅ Nobara Linux (Fedora-based)
- ✅ Arch Linux / Manjaro
- ✅ Ubuntu 22.04+ / Debian 12+
- ⚠️ Outras distros: deve funcionar, mas não testado

---

## 📖 Documentação

- **[Guia de Instalação](docs/instalacao.md)** — Instalação detalhada e troubleshooting
- **[Modelos Suportados](docs/modelos-suportados.md)** — Lista completa + como adicionar seu modelo
- **[Uso da CLI](docs/cli.md)** — Comandos e automação
- **[Uso da GUI](docs/gui.md)** — Tutorial da interface gráfica
- **[Protocolo USB](docs/protocolo.md)** — Documentação técnica de engenharia reversa
- **[Contribuir](docs/contribuir.md)** — Como ajudar o projeto

---

## 🤝 Contribuindo

Contribuições são muito bem-vindas! Veja [CONTRIBUTING.md](CONTRIBUTING.md).

### Como você pode ajudar:
- 🐛 Reportar bugs e problemas
- 📝 Melhorar documentação e traduções
- 🔬 Adicionar suporte a novos modelos (veja [docs/adicionar-modelo.md](docs/adicionar-modelo.md))
- 💻 Melhorar o código e adicionar features
- ⭐ Dar uma estrela no projeto!

---

## ⚠️ Aviso Legal

**Projeto independente e não oficial.** Não afiliado com:
- Guangzhou Junxingcheng Electronic Technology
- Attack Shark, MambaSnake, INX (marcas comerciais)
- LXDDZ, Beken, Nordic Semiconductor

O protocolo foi documentado via **engenharia reversa para fins de interoperabilidade** (uso legítimo segundo diretivas de interoperabilidade da UE e fair use nos EUA).

Este software escreve na memória não volátil do dispositivo. **Use por sua conta e risco.** Não nos responsabilizamos por danos ao hardware.

### Salvaguardas implementadas:
✅ Backup automático antes de qualquer escrita  
✅ Verificação de checksum e validação de range  
✅ Apenas comandos extraídos do driver oficial (sem fuzzing)  
✅ Relectura e comparação pós-escrita  

---

## 📜 Licença

**GPL-2.0-or-later** — GNU General Public License v2.0 ou posterior

Você pode usar, estudar, modificar e redistribuir este software. Trabalhos derivados devem usar a mesma licença.

Dependências (PySide6, Qt6, websockets, evdev) são BSD-3-Clause ou LGPL/GPL compatíveis.

---

## 🙏 Créditos

Baseado em:
- **[LinShark](https://github.com/JSjuan/LinShark)** (JSjuan) — Driver para X8 Pro e protocolo LXDDZ/Beken
- **[attack-shark-x11-ultra-linux](https://github.com/MontyMcK/attack-shark-x11-ultra-linux)** (MontyMcK) — Driver para X11 Ultra

Agradecimentos especiais a todos os contributors que fizeram engenharia reversa dos protocolos USB.

**[Ver créditos completos →](CREDITS.md)**

---

## 💬 Suporte

- 🐛 **Issues:** [GitHub Issues](https://github.com/erxcola/attackshark-linux/issues)
- 💬 **Discussões:** [GitHub Discussions](https://github.com/erxcola/attackshark-linux/discussions)
- 📧 **Email:** [Seu email]

---

**Made with ❤️ for the Linux gaming community**

Se este projeto te ajudou, considere dar uma ⭐!
