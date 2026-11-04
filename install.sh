#!/bin/bash
set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}"
cat << "EOF"
   ___  __  __             __   ________ __               __
  / _ |/ /_/ /____ ______/ /__/ __/ /  / /__ ______ ___ / /__
 / __ / __/ __/ _  / __/  '_/_\ \/ _  / _  / __/ _  / // / _ \
/_/ |_\__/\__/\_,_/\__/_/\_\/___/_//_/_//_/\__/\_,_/\__/_//_/
                Linux Driver Unificado
EOF
echo -e "${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/attackshark-linux"
BIN_DIR="$HOME/.local/bin"

echo -e "${GREEN}🦈 AttackShark-Linux Instalador${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# 1. Verificar Python
echo -e "${BLUE}[1/7]${NC} Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo -e "${RED}❌ Python 3.10+ necessário (encontrado: $PYTHON_VERSION)${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION"
echo

# 2. Detectar mouse
echo -e "${BLUE}[2/7]${NC} Detectando mouse Attack Shark..."
chmod +x "$SCRIPT_DIR/scripts/detectar-mouse.py"

DETECT_OUTPUT=$("$SCRIPT_DIR/scripts/detectar-mouse.py" 2>&1)
DETECT_EXIT=$?

echo "$DETECT_OUTPUT" | head -n -1  # Mostra tudo exceto última linha (que é o nome do driver)

if [ $DETECT_EXIT -eq 1 ]; then
    echo -e "${RED}Instalação cancelada.${NC}"
    exit 1
elif [ $DETECT_EXIT -eq 2 ]; then
    echo -e "${YELLOW}Modelo não suportado ainda.${NC}"
    echo "Deseja continuar mesmo assim? (pode não funcionar) [s/N]"
    read -r resposta
    if [[ ! "$resposta" =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

DRIVER=$(echo "$DETECT_OUTPUT" | tail -n 1 | sed 's/^→ *//')  # Remove seta e espaços
echo
echo -e "${GREEN}Driver selecionado: ${DRIVER}${NC}"
echo

# 3. Instalar dependências
echo -e "${BLUE}[3/7]${NC} Instalando dependências..."

# Detectar package manager
if command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    INSTALL_CMD="sudo dnf install -y"
    PACKAGES="cmake gcc-c++ qt6-qtbase-devel libudev-devel python3-pip ImageMagick git"
elif command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
    INSTALL_CMD="sudo apt install -y"
    PACKAGES="cmake g++ qt6-base-dev libudev-dev python3-pip imagemagick git"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    INSTALL_CMD="sudo pacman -S --needed --noconfirm"
    PACKAGES="cmake gcc qt6-base libudev python-pip imagemagick git"
else
    echo -e "${YELLOW}⚠️  Package manager não detectado automaticamente${NC}"
    echo "Instale manualmente: cmake, g++/gcc, Qt6, libudev-dev, python3-pip, imagemagick, git"
    echo "Continuar? [s/N]"
    read -r resposta
    if [[ ! "$resposta" =~ ^[Ss]$ ]]; then
        exit 1
    fi
    SKIP_DEPS=true
fi

if [ "$SKIP_DEPS" != "true" ]; then
    echo "Detectado: $PKG_MANAGER"
    echo "Executando: $INSTALL_CMD $PACKAGES"
    echo
    $INSTALL_CMD $PACKAGES || {
        echo -e "${YELLOW}⚠️  Alguns pacotes podem ter falhado. Continuando...${NC}"
    }
fi

# Instalar PySide6 via pip
echo "Instalando PySide6..."
python3 -m pip install --user PySide6 || {
    echo -e "${YELLOW}⚠️  Falha ao instalar PySide6. A GUI pode não funcionar.${NC}"
}

echo

# 4. Copiar arquivos para ~/.local/share
echo -e "${BLUE}[4/7]${NC} Copiando arquivos..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Copia o driver específico e arquivos comuns
if [ "$DRIVER" = "x11-ultra" ]; then
    echo "Copiando driver X11-Ultra..."
    cp -r "$SCRIPT_DIR/drivers/x11-ultra"/* "$INSTALL_DIR/" 2>/dev/null || true
    # Remove subdiretórios vazios do git
    find "$INSTALL_DIR" -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
elif [ "$DRIVER" = "linshark" ]; then
    echo "Copiando driver LinShark..."
    cp -r "$SCRIPT_DIR/drivers/linshark"/* "$INSTALL_DIR/" 2>/dev/null || true
    find "$INSTALL_DIR" -name ".git" -type d -exec rm -rf {} + 2>/dev/null || true
else
    echo -e "${RED}❌ Driver desconhecido: $DRIVER${NC}"
    exit 1
fi

# Copia scripts comuns
cp -r "$SCRIPT_DIR/scripts" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/README.md" "$INSTALL_DIR/"

echo -e "${GREEN}✓${NC} Arquivos instalados em $INSTALL_DIR"
echo

# 5. Instalar regras udev
echo -e "${BLUE}[5/7]${NC} Instalando regras udev..."

if [ "$DRIVER" = "x11-ultra" ]; then
    UDEV_RULE="$INSTALL_DIR/udev/70-attack-shark-x11-ultra.rules"
elif [ "$DRIVER" = "linshark" ]; then
    UDEV_RULE="$INSTALL_DIR/models/attackshark-x8pro/udev/70-linshark-x8pro.rules"
fi

if [ -f "$UDEV_RULE" ]; then
    sudo cp "$UDEV_RULE" /etc/udev/rules.d/
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    echo -e "${GREEN}✓${NC} Regras udev instaladas (acesso sem root)"
else
    echo -e "${YELLOW}⚠️  Regra udev não encontrada em: $UDEV_RULE${NC}"
    echo "Você precisará de sudo/root para usar o driver."
fi

echo

# 6. Compilar (se necessário)
echo -e "${BLUE}[6/7]${NC} Compilando driver..."

if [ "$DRIVER" = "x11-ultra" ]; then
    cd "$INSTALL_DIR/app"

    # Gera ícones
    if [ -f "../packaging/make-icons.sh" ]; then
        bash ../packaging/make-icons.sh ../packaging/logo.png 2>/dev/null || true
    fi

    # Compila
    cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$HOME/.local" 2>&1 | grep -v "CMake Warning" || true
    cmake --build build -j$(nproc) 2>&1 | grep -v "CMake Warning" || true
    cmake --install build 2>&1 | grep -v "CMake Warning" || true

    echo -e "${GREEN}✓${NC} GUI compilada: $BIN_DIR/attackshark-ultra"

elif [ "$DRIVER" = "linshark" ]; then
    # LinShark é Python puro, só precisa criar symlinks
    if [ -f "$INSTALL_DIR/driver/linshark-gui" ]; then
        ln -sf "$INSTALL_DIR/driver/linshark-gui" "$BIN_DIR/attackshark-gui"
        ln -sf "$INSTALL_DIR/driver/linshark" "$BIN_DIR/attackshark-cli"
        chmod +x "$INSTALL_DIR/driver/linshark-gui"
        chmod +x "$INSTALL_DIR/driver/linshark"
        echo -e "${GREEN}✓${NC} Symlinks criados"
    fi
fi

echo

# 7. Criar atalho desktop
echo -e "${BLUE}[7/7]${NC} Criando atalho no menu..."

DESKTOP_FILE="$HOME/.local/share/applications/attackshark-linux.desktop"
mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Attack Shark Configurator
Comment=Configure seu mouse Attack Shark
Exec=$BIN_DIR/attackshark-ultra
Icon=attackshark
Terminal=false
Categories=Utility;HardwareSettings;
Keywords=mouse;gaming;attackshark;dpi;rgb;
EOF

echo -e "${GREEN}✓${NC} Atalho criado"
echo

# Sucesso!
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Instalação completa!${NC}"
echo
echo "Como usar:"
echo -e "  ${BLUE}→${NC} GUI:  attackshark-ultra (ou busque 'Attack Shark' no menu)"
echo -e "  ${BLUE}→${NC} CLI:  cd $INSTALL_DIR && python3 probe.py"
echo
echo "Arquivos instalados em:"
echo "  $INSTALL_DIR"
echo
echo -e "${YELLOW}⚠️  Desconecte e reconecte o mouse para aplicar as permissões udev${NC}"
echo
echo "Documentação: https://github.com/SEU-USUARIO/attackshark-linux"
echo
