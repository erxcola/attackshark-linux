# 🦈 AttackShark-Linux

**Native Linux drivers for Attack Shark mice** — Complete support for the entire Attack Shark lineup (X8 Pro, X8 Ultimate, X11 Ultra and more) without needing the official Windows/macOS software.

[![License: GPL-2.0+](https://img.shields.io/badge/License-GPL%202.0+-blue.svg)](LICENSE)
[![Tested on Nobara](https://img.shields.io/badge/Tested%20on-Nobara%20Linux-blueviolet)](https://nobaraproject.org/)

**[Português](README.md)** | **English**

---

## 🎯 What is it?

Unified project that automatically detects which Attack Shark mouse you have connected and installs the correct driver:

- **LinShark** (for LXDDZ/Beken models): X8 Pro, MambaSnake, INX
- **X11-Ultra** (for Nordic models): X8 Ultimate, X11 Ultra, X11 Carbon

You **don't need to know** which chipset your mouse uses — the installer detects everything automatically.

---

## ✨ Features

### 🖱️ Complete Mouse Configuration

✅ **DPI:** 50 to 60,000 (50-step increments)  
✅ **Polling Rate:** 125Hz up to **8000Hz** (125/250/500/1K/2K/4K/8K)  
✅ **RGB/LED:** Per-gear colors, effects (breathing, always-on), brightness  
✅ **Battery:** Charge level and charging status  
✅ **Sensor:** Lift-off distance, angle snapping, ripple control, motion sync  
✅ **Buttons:** Remapping, macros, debounce (4-50ms)  
✅ **Power:** Sleep timer, hibernation

### 🎨 Interface

- **Modern GUI** (Qt6/PySide6) with dark/light themes
- **Complete CLI** for automation and scripts
- **Auto-detection** of connection (2.4GHz dongle or USB cable)
- **Backup/restore** of settings
- **No root required** (after installing udev rules)

---

## 🚀 Quick Install

```bash
git clone https://github.com/erxcola/attackshark-linux.git
cd attackshark-linux
./install.sh
```

The script will:
1. ✅ Automatically detect your mouse
2. ✅ Install dependencies (Qt6, Python 3.10+)
3. ✅ Compile the correct driver
4. ✅ Configure udev rules (no-root access)
5. ✅ Add shortcut to application menu

After installation:
```bash
attackshark-ultra    # Open GUI
# or
attackshark-cli      # Use command line
```

---

## 📦 Supported Models

### ✅ Fully Tested

| Model | Chipset | USB ID (dongle / cable) | Status |
|-------|---------|------------------------|--------|
| **X8 Ultimate** | Nordic 54L15 | `3554:f517` / `3554:f515` | ✅ Tested |
| **X11 Ultra** | Nordic 54L15 | `3554:f517` / `3554:f515` | ✅ Tested |
| **X8 Pro** | LXDDZ/Beken | `1d57:fa65` / `1d57:2126` | ✅ Tested |

### 🔶 Compatible (untested)

46+ other models from Attack Shark/MambaSnake/INX catalog using the same LXDDZ/Beken protocol:
- X3 Pro, X8 SE, X8 Plus, G3, X11 SE
- MambaSnake M2/M3/M5
- INX X3/X5

**Your model not listed?** See [How to Add a Model](docs/adicionar-modelo.md).

---

## 🛠️ Requirements

### System
- **Linux** with `udev` and `hidraw` (any modern distro)
- **Python 3.10+**
- **Qt6** (for GUI) or **PySide6** (auto-installed if needed)

### Tested on
- ✅ Nobara Linux (Fedora-based)
- ✅ Arch Linux / Manjaro
- ✅ Ubuntu 22.04+ / Debian 12+
- ⚠️ Other distros: should work but untested

---

## 📖 Documentation

- **[Installation Guide](docs/instalacao.md)** — Detailed install and troubleshooting (PT-BR)
- **[Supported Models](docs/modelos-suportados.md)** — Complete list + how to add yours (PT-BR)
- **[CLI Usage](docs/cli.md)** — Commands and automation (PT-BR)
- **[GUI Tutorial](docs/gui.md)** — Interface guide (PT-BR)
- **[USB Protocol](docs/protocolo.md)** — Technical reverse engineering docs (PT-BR)
- **[Contributing](CONTRIBUTING.md)** — How to help the project (PT-BR)

---

## 🤝 Contributing

Contributions are very welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

### How you can help:
- 🐛 Report bugs and issues
- 📝 Improve documentation and translations
- 🔬 Add support for new models (see [docs/adicionar-modelo.md](docs/adicionar-modelo.md))
- 💻 Improve code and add features
- ⭐ Give the project a star!

---

## ⚠️ Legal Notice

**Independent and unofficial project.** Not affiliated with:
- Guangzhou Junxingcheng Electronic Technology
- Attack Shark, MambaSnake, INX (trademarks)
- LXDDZ, Beken, Nordic Semiconductor

The protocol was documented via **reverse engineering for interoperability purposes** (legitimate use under EU interoperability directives and US fair use).

This software writes to the device's non-volatile memory. **Use at your own risk.** We are not responsible for hardware damage.

### Implemented safeguards:
✅ Automatic backup before any write  
✅ Checksum verification and range validation  
✅ Only commands extracted from official driver (no fuzzing)  
✅ Post-write re-read and comparison  

---

## 📜 License

**GPL-2.0-or-later** — GNU General Public License v2.0 or later

You can use, study, modify and redistribute this software. Derivative works must use the same license.

Dependencies (PySide6, Qt6, websockets, evdev) are BSD-3-Clause or LGPL/GPL compatible.

---

## 🙏 Credits

Based on:
- **[LinShark](https://github.com/JSjuan/LinShark)** (JSjuan) — Driver for X8 Pro and LXDDZ/Beken protocol
- **[attack-shark-x11-ultra-linux](https://github.com/MontyMcK/attack-shark-x11-ultra-linux)** (MontyMcK) — Driver for X11 Ultra

Special thanks to all contributors who reverse-engineered the USB protocols.

**[Full credits →](CREDITS.md)**

---

## 💬 Support

- 🐛 **Issues:** [GitHub Issues](https://github.com/erxcola/attackshark-linux/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/erxcola/attackshark-linux/discussions)

---

**Made with ❤️ for the Linux gaming community**

If this project helped you, consider giving it a ⭐!
