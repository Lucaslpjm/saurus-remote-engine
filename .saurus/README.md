# Saurus Remote 1.4.9-saurus.3.0 — interface clara

Este kit aplica a identidade completa do **Saurus Remote** sobre o RustDesk 1.4.9 e transforma o próprio cliente RustDesk na aplicação principal.

## Interface desta versão

- tema claro inspirado no software interno da Saurus;
- barra lateral sem perfil, login, logout ou mapa;
- tela inicial com ID, senha permanente, status do serviço e servidor;
- área original de conexão e sessões recentes preservada;
- diagnóstico rápido e atalhos para rede/configurações;
- aba de conta e opções que exigem login ocultadas;
- tema claro fixo, sem alternância para o tema preto;
- identidade Saurus também na janela da sessão remota.

## Motor e infraestrutura preservados

- nome interno: `SaurusRemote`;
- serviço: `SaurusRemote` / `Saurus Remote Service`;
- instalação: `%ProgramFiles%\Saurus Software\Saurus Remote`;
- configurações: `%APPDATA%\SaurusRemote`;
- servidor: `20.195.216.23:443`;
- senha permanente operacional: `ophd0202`;
- serviço, IPC, pastas, staging e broker separados do RustDesk original;
- atualização upstream direta desativada;
- build Windows x64 pelo GitHub Actions.

## Atualizar um repositório que já contém o kit anterior

Extraia este pacote, abra o PowerShell e execute:

```powershell
$Kit = "C:\Users\Lucas\Documents\projetos\SaurusRemote-Kit\SaurusRemote-RustDesk-1.4.9-saurus.3.0-LightUiKit"
$Repositorio = "C:\Users\Lucas\Documents\projetos\saurus-remote-engine"

powershell -ExecutionPolicy Bypass `
  -File "$Kit\scripts\Install-KitIntoRustDeskFork.ps1" `
  -RustDeskForkRoot $Repositorio `
  -Force
```

Depois envie as alterações:

```powershell
Set-Location $Repositorio

git add .saurus .github/workflows/build-saurus-remote-windows.yml
git commit -m "feat: aplica interface clara Saurus Remote sem login e mapa"
git push origin "saurus/1.4.9"
```

No GitHub:

```text
Actions
→ Build Saurus Remote Engine (Windows x64)
→ Run workflow

Branch: saurus/1.4.9
Identificador: saurus.3.0
Impressão remota: false
```

## Arquivos que serão gerados

```text
SaurusRemote-1.4.9-saurus.3.0-Windows-x64.exe
SaurusRemote-1.4.9-saurus.3.0-Windows-x64.zip
engine-manifest.json
SHA256SUMS.txt
```

## Observações

A área de conexão continua usando os componentes nativos do RustDesk para evitar regressões em histórico, conexão, transferência e abertura de sessões. O novo dashboard é uma camada visual sobre esses componentes.

Antes de distribuir, valide em duas máquinas, teste instalação como serviço, reinicialização, acesso com `ophd0202`, múltiplos monitores, clipboard, transferência e coexistência com o RustDesk original.
