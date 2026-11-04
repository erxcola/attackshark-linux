# 🧪 Testando o Repositório Antes de Publicar

## Teste 1: Detector de Mouse

```bash
cd ~/attackshark-linux
python3 scripts/detectar-mouse.py
```

**Esperado:**
```
✅ Mouse detectado: Attack Shark X8 Ultimate / X11 Ultra (dongle)
   USB ID: 3554:f517
   Chipset: Nordic 54L15
   Driver: x11-ultra
```

## Teste 2: Driver X11-Ultra (Probe)

```bash
cd ~/attackshark-linux/drivers/x11-ultra
python3 probe.py
```

**Esperado:**
```
handshake OK  cid=124 mid=4 type=5 (wireless 8k)
online flag=0  paired addr=d5:27:df
```

Se os flash reads falharem ("no response"), **é normal** — mova o mouse para acordá-lo.

## Teste 3: Instalação Completa

⚠️ **ATENÇÃO:** Isso vai instalar tudo no sistema. Teste em VM ou tenha backup.

```bash
cd ~/attackshark-linux
./install.sh
```

**Esperado:**
1. Detecta o mouse automaticamente
2. Instala dependências (Qt6, cmake, etc) — **requer senha sudo**
3. Compila o driver x11-ultra
4. Instala regras udev
5. Cria atalho no menu

**Após instalação:**
```bash
# Testar GUI
~/.local/bin/attackshark-ultra

# Ou
attackshark-ultra  # (se ~/.local/bin estiver no PATH)
```

## Teste 4: Funcionalidades da GUI

1. **Abrir a GUI** (atalho ou comando)
2. **Conectar ao mouse** (deve detectar automaticamente)
3. **Aba Sensor:**
   - Mudar DPI de um gear
   - Aplicar → deve piscar o LED confirmando
4. **Aba Lighting:**
   - Mudar cor de um LED
   - Aplicar → LED muda de cor
5. **Polling Rate:**
   - Mudar de 1000Hz para 2000Hz
   - Aplicar → confirmar com `evhz` ou similar

## Teste 5: Estrutura do Repositório

```bash
cd ~/attackshark-linux
tree -L 2 -I '__pycache__|*.pyc|build'
```

**Esperado:**
```
.
├── CONTRIBUTING.md
├── docs/
│   └── modelos-suportados.md
├── drivers/
│   ├── linshark/
│   └── x11-ultra/
├── examples/
├── install.sh
├── LICENSE
├── PUBLICAR.md
├── README.md
├── scripts/
│   └── detectar-mouse.py
└── TESTAR.md
```

## Teste 6: Git e Commits

```bash
cd ~/attackshark-linux
git log --oneline
git status
```

**Esperado:**
- Pelo menos 2 commits
- `git status` limpo (nada para commitar)
- Branch `main` ativa

## Teste 7: Validação de Links

```bash
cd ~/attackshark-linux
grep -r "SEU-USUARIO" README.md CONTRIBUTING.md || echo "OK: Nenhum placeholder encontrado"
```

**Esperado antes de publicar:**
- `OK: Nenhum placeholder encontrado`

Se encontrar `SEU-USUARIO`, substitua:
```bash
sed -i 's/SEU-USUARIO/seu-usuario-github/g' README.md CONTRIBUTING.md
```

## Teste 8: README Renderização

Copie o conteúdo do `README.md` e cole em:
https://dillinger.io/

Verifique se:
- ✅ Badges renderizam
- ✅ Tabelas estão alinhadas
- ✅ Links funcionam (internos podem ficar quebrados no preview)
- ✅ Formatação está correta

## Checklist Final Antes de Publicar

- [ ] Detector funciona e identifica seu mouse
- [ ] Probe conecta ao mouse sem erros
- [ ] Instalação completa sem erros
- [ ] GUI abre e conecta
- [ ] Mudança de DPI funciona
- [ ] Mudança de LED funciona (se aplicável)
- [ ] Estrutura de diretórios correta
- [ ] Git log limpo
- [ ] Placeholders substituídos
- [ ] README renderiza bem

---

## 🆘 Problemas Comuns

### Detector não encontra o mouse

```bash
lsusb | grep -i attack
```

Se aparecer algo, anote o USB ID e adicione em `scripts/detectar-mouse.py`.

### Probe falha no handshake

- Mova o mouse (pode estar dormindo)
- Reconecte o dongle/cabo
- Tente como root: `sudo python3 probe.py`

### Instalação falha nas dependências

Instale manualmente:
```bash
# Nobara/Fedora
sudo dnf install cmake gcc-c++ qt6-qtbase-devel libudev-devel python3-pip

# Ubuntu/Debian
sudo apt install cmake g++ qt6-base-dev libudev-dev python3-pip

# Arch
sudo pacman -S cmake gcc qt6-base libudev python-pip
```

### GUI não abre

```bash
# Verificar se foi instalado
ls -la ~/.local/bin/attackshark-ultra

# Testar direto da build
cd ~/attackshark-linux/drivers/x11-ultra/app
./build/attackshark-ultra
```

---

**Tudo funcionando?** Prossiga para `PUBLICAR.md`! 🚀
