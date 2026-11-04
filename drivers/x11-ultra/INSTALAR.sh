#!/bin/bash
set -e

echo "🔧 Configurando Attack Shark X8 Ultimate no Linux..."
echo

# 1. Instalar regras udev
echo "📋 Instalando regras udev..."
sudo cp udev/70-attack-shark-x11-ultra.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "✅ Regras udev instaladas"
echo

# 2. Verificar dependências
echo "📦 Verificando dependências..."
deps_missing=0

if ! command -v cmake &> /dev/null; then
    echo "❌ cmake não encontrado"
    deps_missing=1
fi

if ! command -v g++ &> /dev/null; then
    echo "❌ g++ não encontrado"
    deps_missing=1
fi

if ! ldconfig -p | grep -q libQt6Widgets; then
    echo "❌ Qt6 Widgets não encontrado"
    deps_missing=1
fi

if [ $deps_missing -eq 1 ]; then
    echo
    echo "📥 Instalando dependências faltantes..."
    sudo dnf install -y cmake gcc-c++ qt6-qtbase-devel libudev-devel ImageMagick
    echo "✅ Dependências instaladas"
fi
echo

# 3. Compilar GUI
echo "🔨 Compilando GUI..."
cd app
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$HOME/.local
cmake --build build -j$(nproc)
echo "✅ GUI compilada"
echo

# 4. Instalar
echo "📦 Instalando em ~/.local..."
cmake --install build
echo "✅ Instalado em ~/.local/bin/attackshark-ultra"
echo

# 5. Testar
echo "🧪 Testando conexão com o mouse..."
cd ..
python3 probe.py
echo

echo "✅ Instalação completa!"
echo
echo "Para usar:"
echo "  - CLI:  cd /tmp/attack-shark-x11-ultra-linux && python3 probe.py"
echo "  - GUI:  ~/.local/bin/attackshark-ultra"
echo "        (ou busque 'Attack Shark' no lançador de aplicativos)"
