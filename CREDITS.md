# 🙏 Créditos e Agradecimentos

AttackShark-Linux é um projeto unificado baseado no trabalho de engenharia reversa de vários desenvolvedores da comunidade Linux. Este projeto **não seria possível** sem o trabalho árduo dos criadores originais.

---

## 🔬 Projetos Base

### LinShark
**Autor:** [JSjuan](https://github.com/JSjuan)  
**Repositório:** https://github.com/JSjuan/LinShark  
**Licença:** GPL-2.0-or-later  

**Contribuição:**
- Driver completo para protocolo LXDDZ/Beken (Attack Shark X8 Pro)
- Documentação detalhada de engenharia reversa
- Metodologia de análise de protocolo USB
- Interface PySide6 completa
- Sistema de perfis multimodelo
- Arquitetura de testes e salvaguardas

**Modelos suportados:**
- Attack Shark X8 Pro (`1d57:fa65` / `1d57:2126`)
- Outros modelos LXDDZ/Beken (MambaSnake, INX)

**Destaques técnicos:**
- Classificação epistemológica (MEDIDO/LEÍDO/INFERIDO)
- Sistema de backup e verificação em 4 etapas
- Proibição de fuzzing para segurança do hardware
- Documentação completa do protocolo

---

### attack-shark-x11-ultra-linux
**Autor:** [MontyMcK](https://github.com/MontyMcK)  
**Repositório:** https://github.com/MontyMcK/attack-shark-x11-ultra-linux  
**Licença:** Não especificada (engenharia reversa para interoperabilidade)  

**Contribuição:**
- Driver para protocolo Nordic (Attack Shark X11 Ultra)
- Documentação completa do protocolo USB (`PROTOCOL.md`)
- Interface Qt6 nativa
- Suporte a polling rates até 8000Hz (2K/4K/8K)
- Sistema de retry para reads via radio
- Probe script para diagnóstico

**Modelos suportados:**
- Attack Shark X11 Ultra (`3554:f517` / `3554:f515`)
- Attack Shark X8 Ultimate (mesmo protocolo)
- Attack Shark X11 Ultra Carbon

**Destaques técnicos:**
- Descoberta de 2 USB IDs diferentes (dongle vs cabo)
- Codec de DPI com round-trip completo
- Identificação de branch duplo no polling rate byte
- Correção de inconsistências no JS vendor

---

## 🔧 AttackShark-Linux (Este Projeto)

**Autor:** [erxcola](https://github.com/erxcola)  
**Repositório:** https://github.com/erxcola/attackshark-linux  
**Licença:** GPL-2.0-or-later  

**Contribuições originais:**
- Unificação dos dois drivers (LinShark + X11-Ultra)
- Sistema de detecção automática de modelo via USB ID
- Instalador universal para todas as distros Linux
- Documentação completa em PT-BR e inglês
- Scripts de setup e configuração
- Estrutura de repositório organizada
- Integração e testes

---

## 📚 Outras Contribuições

### OpenMouse Project
**Repositório:** https://github.com/OpenMouse-Project/mouse-protocol  
**Contribuição:** Notas de protocolo do X8 Pro (Issue #171)

### Comunidade Linux Gaming
Agradecimentos especiais a todos que:
- Testaram os drivers
- Reportaram bugs
- Contribuíram com documentação
- Compartilharam conhecimento sobre engenharia reversa

---

## 🎖️ Metodologia de Engenharia Reversa

A engenharia reversa realizada pelos criadores originais seguiu práticas éticas:

1. **Propósito legítimo:** Interoperabilidade (uso de hardware legalmente adquirido em Linux)
2. **Sem redistribuição de código proprietário**
3. **Documentação de protocolo via observação comportamental**
4. **Salvaguardas contra danos ao hardware**
5. **Classificação clara de evidências** (medido vs inferido)

Isso está em conformidade com:
- Diretivas de interoperabilidade da União Europeia
- Fair use nos Estados Unidos
- Diretrizes de engenharia reversa para compatibilidade

---

## 🔗 Links dos Projetos Originais

| Projeto | Autor | Link |
|---------|-------|------|
| **LinShark** | JSjuan | https://github.com/JSjuan/LinShark |
| **attack-shark-x11-ultra-linux** | MontyMcK | https://github.com/MontyMcK/attack-shark-x11-ultra-linux |
| **AttackShark-Linux** (este) | erxcola | https://github.com/erxcola/attackshark-linux |

---

## 📜 Declaração de Não Afiliação

Este projeto é **independente e não oficial**. Não possui afiliação, patrocínio ou endosso de:

- Guangzhou Junxingcheng Electronic Technology Co., Ltd
- Attack Shark (marca comercial)
- MambaSnake (marca comercial)
- INX (marca comercial)
- LXDDZ
- Beken Corporation
- Nordic Semiconductor
- PixArt Imaging Inc.

As marcas comerciais pertencem a seus respectivos proprietários e são mencionadas apenas para identificar os dispositivos compatíveis.

---

## 💝 Como Contribuir

Se este projeto te ajudou, você pode:

1. ⭐ **Dar uma estrela** nos 3 repositórios:
   - https://github.com/JSjuan/LinShark
   - https://github.com/MontyMcK/attack-shark-x11-ultra-linux
   - https://github.com/erxcola/attackshark-linux

2. 📝 **Contribuir** com código, documentação ou testes

3. 🐛 **Reportar bugs** e ajudar outros usuários

4. 📣 **Compartilhar** o projeto na comunidade Linux

---

## 🏆 Agradecimento Especial

Um **obrigado especial** a JSjuan e MontyMcK pela paciência e dedicação em documentar esses protocolos USB complexos. Sem o trabalho de vocês, este projeto unificado não existiria.

**Vocês são heróis da comunidade open source!** 🦸‍♂️🦸‍♀️

---

**Última atualização:** 2026-11-04
