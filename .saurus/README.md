# Saurus Remote 1.4.9-saurus.3.1.1 — kit de produção e instalador

Este pacote transforma o RustDesk 1.4.9 no **Saurus Remote** e gera três formatos no GitHub Actions:

- `SaurusRemote-<versão>-Setup.exe`: instalador definitivo recomendado;
- `SaurusRemote-<versão>-Windows-x64.exe`: executável portátil;
- `SaurusRemote-<versão>-Windows-x64.zip`: motor e dependências separados.

## Correções desta versão

0. **Correção de build:** o padrão da escala desktop agora altera a linha real `keys::OPTION_VIEW_STYLE` do `hbb_common` 1.4.9, evitando o falso negativo da compilação.
1. **Escala adaptável** passa a ser o padrão no núcleo, no arquivo de preferências e nos pares já salvos durante a atualização.
2. **Desativar som** passa a iniciar ativo em novas sessões e também é migrado para os pares já existentes.
3. A senha operacional **`ophd0202`** é aplicada no início normal, no modo portátil, no serviço e no servidor.
4. O instalador repete a aplicação da senha por `stdin`, valida o retorno e registra log em `%ProgramData%\Saurus Software\Saurus Remote\install-config.log`.
5. O launcher instalado e o portátil recebem manifesto `requireAdministrator`; o motor permanece `asInvoker/default` para suportar serviço, servidor e tray.
6. O instalador registra o serviço `SaurusRemote`, configura início automático e recuperação após falhas, permite acesso na tela de logon, cria regra de firewall, atalhos e desinstalação limpa.

## Identidade isolada

- executável: `SaurusRemote.exe`;
- serviço: `SaurusRemote` / `Saurus Remote Service`;
- instalação: `%ProgramFiles%\Saurus Software\Saurus Remote`;
- configuração do usuário: `%APPDATA%\SaurusRemote`;
- configuração do serviço: `%WINDIR%\ServiceProfiles\LocalService\AppData\Roaming\SaurusRemote`;
- chave de desinstalação: `{1117CE17-506B-4122-A421-69233FCA9C12}_is1`;
- servidor: `20.195.216.23:443`;
- senha permanente: `ophd0202`.

O RustDesk original pode permanecer instalado: serviço, executável, diretórios, registro, IPC e recursos são separados.

## Aplicar no repositório já existente

```powershell
$Kit = "C:\Users\Lucas\Documents\projetos\SaurusRemote-Kit\SaurusRemote-RustDesk-1.4.9-saurus.3.1.1-ProductionSetupKit"
$Repositorio = "C:\Users\Lucas\Documents\projetos\saurus-remote-engine"

powershell -ExecutionPolicy Bypass `
  -File "$Kit\scripts\Install-KitIntoRustDeskFork.ps1" `
  -RustDeskForkRoot $Repositorio `
  -Force

Set-Location $Repositorio
git add .saurus .github/workflows/build-saurus-remote-windows.yml
git commit -m "fix: instala serviço, senha, escala e elevação administrativa"
git push origin "saurus/1.4.9"
```

No GitHub, execute uma compilação nova com:

```text
Branch: saurus/1.4.9
Identificador: saurus.3.1.1
Impressão remota: false
```

## Artefato recomendado

Para instalar em máquinas de teste, use:

```text
SaurusRemote-1.4.9-saurus.3.1.1-Setup.exe
```

O setup:

- copia o produto para Program Files;
- registra e inicia o serviço;
- aplica a senha real no motor;
- ativa somente senha permanente;
- permite acesso na tela de logon;
- configura escala adaptável e áudio desativado por padrão;
- migra essas preferências em conexões já salvas;
- aplica elevação administrativa ao abrir a interface;
- cria atalhos e desinstalador.

## Validação após instalar

```powershell
Get-Service SaurusRemote
Get-CimInstance Win32_Service -Filter "Name='SaurusRemote'" |
  Select-Object Name, State, StartMode, PathName

& "$env:ProgramFiles\Saurus Software\Saurus Remote\SaurusRemote.exe" --get-id
Get-Content "$env:ProgramData\Saurus Software\Saurus Remote\install-config.log" -Tail 100
```

Teste de outro computador com a senha `ophd0202`, reinicie a máquina controlada e repita o acesso na tela de logon/UAC.

## Estrutura

```text
branding/   identidade visual
installer/  Inno Setup, manifesto ADM e configuração pós-instalação
github/     workflow Windows x64
scripts/    aplicação e validação do fork
tools/      validação estática
docs/       arquitetura, build, segurança e homologação
samples/    integrações auxiliares
```

## Observações

- Os atalhos abrem `SaurusRemoteLauncher.exe`, que solicita confirmação do UAC e inicia o motor elevado. O serviço usa diretamente `SaurusRemote.exe`, sem forçar UAC nos subprocessos internos de servidor e tray.
- O instalador sem certificado funcionará, mas exibirá “Fornecedor desconhecido”.
- Para produção, configure assinatura Authenticode no GitHub Actions.
- A senha compartilhada é uma decisão operacional da Saurus e fica recuperável no código/binário; controle a distribuição.
- Esta entrega gera o instalador no Windows runner; a homologação funcional continua obrigatória.
