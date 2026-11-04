#!/usr/bin/env python3
"""
Detecta automaticamente qual mouse Attack Shark está conectado.
Retorna o tipo de driver necessário: 'linshark' (LXDDZ/Beken) ou 'x11-ultra' (Nordic).
"""

import subprocess
import sys
import re
from typing import Optional, Dict

# Mapeamento de USB IDs para drivers
MOUSES_CONHECIDOS = {
    # Nordic (X8 Ultimate, X11 Ultra, X11 Carbon)
    '3554:f517': {
        'nome': 'Attack Shark X8 Ultimate / X11 Ultra (dongle)',
        'driver': 'x11-ultra',
        'chipset': 'Nordic 54L15'
    },
    '3554:f515': {
        'nome': 'Attack Shark X8 Ultimate / X11 Ultra (cabo)',
        'driver': 'x11-ultra',
        'chipset': 'Nordic 54L15'
    },

    # LXDDZ/Beken (X8 Pro, X3 Pro, MambaSnake, INX)
    '1d57:fa65': {
        'nome': 'Attack Shark X8 Pro (dongle)',
        'driver': 'linshark',
        'chipset': 'LXDDZ/Beken'
    },
    '1d57:2126': {
        'nome': 'Attack Shark X8 Pro (cabo)',
        'driver': 'linshark',
        'chipset': 'LXDDZ/Beken'
    },
    '1d57:fa55': {
        'nome': 'Attack Shark X11 (antigo, dongle)',
        'driver': 'linshark',
        'chipset': 'LXDDZ/Beken'
    },
    '1d57:fa60': {
        'nome': 'Attack Shark X11 (antigo, cabo)',
        'driver': 'linshark',
        'chipset': 'LXDDZ/Beken'
    },
}


def executar_lsusb() -> str:
    """Executa lsusb e retorna a saída."""
    try:
        resultado = subprocess.run(['lsusb'], capture_output=True, text=True, check=True)
        return resultado.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar lsusb: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Comando 'lsusb' não encontrado. Instale o pacote 'usbutils'.", file=sys.stderr)
        sys.exit(1)


def detectar_attack_shark(lsusb_output: str) -> Optional[Dict[str, str]]:
    """
    Detecta se há um mouse Attack Shark conectado.
    Retorna dict com info do mouse ou None se não encontrar.
    """
    # Procura por "ATTACK SHARK" ou pelos USB IDs conhecidos
    linhas = lsusb_output.split('\n')

    for linha in linhas:
        # Tenta match direto com "ATTACK SHARK" ou "Compx"
        if 'ATTACK SHARK' in linha or 'Compx' in linha:
            # Extrai USB ID (formato: 1234:5678)
            match = re.search(r'ID\s+([0-9a-f]{4}:[0-9a-f]{4})', linha, re.IGNORECASE)
            if match:
                usb_id = match.group(1).lower()

                # Verifica se é um ID conhecido
                if usb_id in MOUSES_CONHECIDOS:
                    info = MOUSES_CONHECIDOS[usb_id].copy()
                    info['usb_id'] = usb_id
                    info['linha_lsusb'] = linha.strip()
                    return info
                else:
                    # Attack Shark encontrado mas USB ID desconhecido
                    return {
                        'nome': 'Attack Shark (modelo desconhecido)',
                        'driver': 'desconhecido',
                        'chipset': 'Desconhecido',
                        'usb_id': usb_id,
                        'linha_lsusb': linha.strip()
                    }

        # Tenta match pelos USB IDs conhecidos mesmo sem o nome
        for usb_id, info in MOUSES_CONHECIDOS.items():
            if usb_id in linha.lower():
                resultado = info.copy()
                resultado['usb_id'] = usb_id
                resultado['linha_lsusb'] = linha.strip()
                return resultado

    return None


def main():
    """Função principal."""
    print("🔍 Detectando mouse Attack Shark...\n")

    lsusb_output = executar_lsusb()
    mouse = detectar_attack_shark(lsusb_output)

    if not mouse:
        print("❌ Nenhum mouse Attack Shark detectado.")
        print("\n💡 Certifique-se de que o mouse está:")
        print("   - Conectado via dongle 2.4GHz OU cabo USB")
        print("   - Ligado (se wireless)")
        print("   - Reconhecido pelo sistema (rode 'lsusb' para verificar)")
        sys.exit(1)

    print(f"✅ Mouse detectado: {mouse['nome']}")
    print(f"   USB ID: {mouse['usb_id']}")
    print(f"   Chipset: {mouse['chipset']}")
    print(f"   Driver: {mouse['driver']}")
    print(f"\n   lsusb: {mouse['linha_lsusb']}")

    if mouse['driver'] == 'desconhecido':
        print("\n⚠️  MODELO DESCONHECIDO")
        print("   Este mouse não está na lista de modelos suportados.")
        print("   Você pode ajudar adicionando suporte!")
        print("   Veja: docs/adicionar-modelo.md")
        sys.exit(2)

    # Retorna o nome do driver (para scripts)
    print(f"\n→ {mouse['driver']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
