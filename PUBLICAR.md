# 📤 Como Publicar no GitHub

## Passo 1: Criar Repositório no GitHub

1. Acesse https://github.com/new
2. Nome do repositório: `attackshark-linux`
3. Descrição: **Drivers nativos Linux para mouses Attack Shark - Suporte completo a X8 Pro/Ultimate, X11 Ultra com detecção automática**
4. ✅ **Public** (repositório público)
5. ❌ **NÃO** marque "Add README" (já temos)
6. ❌ **NÃO** adicione .gitignore ou LICENSE (já temos)
7. Clique em **Create repository**

## Passo 2: Conectar Repositório Local

Na página que abrir, copie os comandos e execute:

```bash
cd ~/attackshark-linux

# Se ainda não configurou seu GitHub:
git config user.name "Seu Nome"
git config user.email "seu-email@exemplo.com"

# Adicionar remote (SUBSTITUA pelo seu usuário)
git remote add origin https://github.com/SEU-USUARIO/attackshark-linux.git

# Push inicial
git push -u origin main
```

## Passo 3: Atualizar Links no README

Edite o `README.md` e substitua todos os `SEU-USUARIO` pelo seu nome de usuário do GitHub:

```bash
sed -i 's/SEU-USUARIO/seu-usuario-github/g' README.md CONTRIBUTING.md
git add README.md CONTRIBUTING.md
git commit -m "docs: atualiza links do repositório"
git push
```

## Passo 4: Configurar GitHub (opcional mas recomendado)

### Topics (tags de pesquisa)

No GitHub, vá em **About** (roda dentada) e adicione topics:
```
attackshark, gaming-mouse, linux, linux-driver, usb, nobara, fedora, arch, ubuntu, qt6, python, dpi, rgb, polling-rate
```

### Releases

Para criar a primeira release:

```bash
git tag -a v1.0.0 -m "Primeira release pública

- Suporte a X8 Pro, X8 Ultimate, X11 Ultra
- Detecção automática de modelo
- Instalador unificado
- Drivers LinShark e X11-Ultra integrados
- Documentação completa em PT-BR"

git push origin v1.0.0
```

No GitHub:
1. Vá em **Releases** → **Create a new release**
2. Selecione a tag `v1.0.0`
3. Título: **v1.0.0 - Primeira Release Pública**
4. Descrição: copie do changelog
5. Publique!

### GitHub Actions (CI/CD - opcional)

Crie `.github/workflows/test.yml`:

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt || true
      - name: Run detector
        run: python3 scripts/detectar-mouse.py || true
```

## Passo 5: Divulgar

### Reddit
- r/linux_gaming
- r/linux
- r/Fedora (ou sua distro)

Exemplo de post:
```
[OC] AttackShark-Linux: Drivers nativos para mouses Attack Shark

Criei um repositório unificado com suporte completo para mouses Attack Shark 
(X8 Pro/Ultimate, X11 Ultra) no Linux. Detecta automaticamente o modelo e 
instala o driver correto.

Features: DPI até 60k, polling 8000Hz, RGB, macros, GUI Qt6, tudo sem 
precisar do software Windows.

Testado em Nobara/Fedora. Link: https://github.com/seu-usuario/attackshark-linux

Contribuições bem-vindas!
```

### Discord/Telegram
- Grupos de Linux gaming
- Comunidades de periféricos

### YouTube (opcional)
- Vídeo tutorial de instalação
- Showcase das features

## Passo 6: Manutenção

### Issues
Responda issues e ajude a comunidade!

### Pull Requests
Revise PRs de contribuidores.

### Updates
Quando os drivers upstream (LinShark, x11-ultra) atualizarem:

```bash
cd /tmp
git clone https://github.com/JSjuan/LinShark.git
git clone https://github.com/MontyMcK/attack-shark-x11-ultra-linux.git

cd ~/attackshark-linux
rm -rf drivers/linshark drivers/x11-ultra
cp -r /tmp/LinShark drivers/linshark
cp -r /tmp/attack-shark-x11-ultra-linux drivers/x11-ultra

git add drivers/
git commit -m "chore: atualiza drivers upstream"
git push
```

---

## ✅ Checklist Final

- [ ] Repositório público criado
- [ ] Push feito com sucesso
- [ ] Links atualizados (SEU-USUARIO → seu username)
- [ ] Topics configurados
- [ ] Release v1.0.0 criada
- [ ] Testado em máquina limpa
- [ ] Divulgado em 2+ comunidades

---

**Boa sorte com o projeto!** 🦈🐧

Se precisar de ajuda, abra uma issue no próprio repositório.
