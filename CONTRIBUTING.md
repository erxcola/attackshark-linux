# 🤝 Contribuindo para AttackShark-Linux

Obrigado por considerar contribuir! Este projeto existe graças à comunidade Linux gaming. 🎮🐧

---

## 📋 Como Contribuir

### 1. 🐛 Reportar Bugs

Abra uma [issue](../../issues/new) incluindo:

- **Modelo do mouse** e USB ID (`lsusb | grep -i attack`)
- **Distribuição Linux** e versão (ex: Nobara 40, Ubuntu 24.04)
- **Versão do Python** (`python3 --version`)
- **Driver usado** (linshark ou x11-ultra)
- **O que aconteceu** vs **o que esperava**
- **Logs completos:**
  ```bash
  python3 probe.py 2>&1 | tee bug-report.log
  ```

### 2. ✨ Sugerir Features

Abra uma [discussion](../../discussions/new?category=ideas) explicando:

- **O que** você gostaria de adicionar
- **Por que** seria útil
- **Como** você imagina que funcionaria

### 3. 📝 Melhorar Documentação

Contribuições de documentação são **muito** valiadas:

- Corrigir typos, traduzir para outros idiomas
- Adicionar screenshots/GIFs da GUI
- Melhorar guias de troubleshooting
- Documentar novos modelos

### 4. 💻 Contribuir Código

#### Setup de Desenvolvimento

```bash
git clone https://github.com/SEU-USUARIO/attackshark-linux.git
cd attackshark-linux

# Instalar em modo dev (sem copiar para ~/.local)
./install.sh --dev

# Rodar testes (se disponíveis)
python3 -m pytest tests/
```

#### Workflow

1. **Fork** o repositório
2. **Crie um branch:**
   ```bash
   git checkout -b feature/minha-feature
   # ou
   git checkout -b fix/bug-tal
   ```

3. **Faça suas mudanças:**
   - Siga o [código de estilo](#código-de-estilo)
   - Adicione testes se possível
   - Documente mudanças no código

4. **Commit:**
   ```bash
   git add .
   git commit -m "feat: adiciona suporte ao modelo X"
   # ou
   git commit -m "fix: corrige detecção de bateria"
   ```

   Use [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` nova funcionalidade
   - `fix:` correção de bug
   - `docs:` documentação
   - `refactor:` refatoração sem mudar comportamento
   - `test:` adicionar/corrigir testes
   - `chore:` tarefas de build, deps, etc

5. **Push e PR:**
   ```bash
   git push origin feature/minha-feature
   ```
   
   Abra um Pull Request descrevendo:
   - O que mudou
   - Por que mudou
   - Como testar

---

## 🔬 Adicionar Suporte a Novo Modelo

### Pré-requisitos

- **O mouse físico** em mãos
- **Máquina Windows** (VM serve) com software oficial
- **Wireshark ou similar** para capturar USB
- **Tempo:** 2-10 dias dependendo da complexidade

### Processo

1. **Capture o protocolo:**
   ```bash
   # No Linux
   sudo wireshark
   # Filtre por: usb.idVendor == 0x3554 (seu vendor ID)
   ```

   No Windows, use [USBPcap](https://desowin.org/usbpcap/).

2. **Documente descobertas:**
   - Estrutura de pacotes
   - Comandos de leitura/escrita
   - Offsets de configuração
   
   Veja exemplo: `drivers/x11-ultra/PROTOCOL.md`

3. **Crie um perfil:**
   ```python
   # drivers/linshark/driver/src/linshark/perfiles/seu_modelo.py
   
   from ..dispositivos import Perfil
   
   PERFIL_SEU_MODELO = Perfil(
       nome="Attack Shark Seu Modelo",
       usb_ids=["1234:5678"],  # Dongle e cabo
       # ... configurações
   )
   ```

4. **Teste exaustivamente:**
   - Leitura/escrita de DPI
   - Mudança de polling rate
   - RGB/LED (se aplicável)
   - Bateria
   - Todos os botões

5. **Documente:**
   - Modelo no `docs/modelos-suportados.md`
   - README do driver
   - Evidências em `dev/models/seu-modelo/`

6. **Submeta PR** com:
   - Capturas USB (`.pcap`)
   - Documentação do protocolo
   - Código do perfil
   - Logs de teste

---

## 📐 Código de Estilo

### Python

- **PEP 8** (use `black` ou `ruff`)
- Type hints onde possível
- Docstrings em português (ou inglês se preferir)

```python
def ler_dpi(device: HIDDevice) -> int:
    """
    Lê o valor atual de DPI do mouse.
    
    Args:
        device: Dispositivo HID conectado
        
    Returns:
        Valor de DPI (50-60000)
        
    Raises:
        DeviceError: Se a leitura falhar
    """
    ...
```

### Bash

- `set -e` no topo de scripts
- Validar inputs
- Mensagens de erro claras

### C++ (GUI Qt6)

- Seguir convenções Qt
- `camelCase` para métodos
- Comentários em inglês (opcional)

---

## ✅ Checklist Antes do PR

- [ ] Código segue o estilo do projeto
- [ ] Comentários explicam **por que**, não **o que**
- [ ] Documentação atualizada (README, docs/)
- [ ] Testado em hardware real
- [ ] Commits seguem Conventional Commits
- [ ] PR tem descrição clara

---

## 🎖️ Créditos de Contribuidores

Todos os contributors aparecem em:
- [README.md](README.md) (seção Créditos)
- GitHub Contributors automático
- Release notes

---

## 🆘 Dúvidas?

- **Discussões:** [GitHub Discussions](../../discussions)
- **Chat:** (adicionar Discord/Matrix se houver)
- **Email:** (seu email)

---

## 📜 Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob **GPL-2.0-or-later**, a mesma licença do projeto.

Código de terceiros (LinShark, x11-ultra) mantém suas licenças originais (GPL-2.0+).

---

**Obrigado por ajudar a melhorar o suporte Attack Shark no Linux!** 🦈🐧
