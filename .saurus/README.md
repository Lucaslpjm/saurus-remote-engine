# Saurus Remote Engine — kit de customização do RustDesk 1.4.9

Este pacote transforma um fork **fixado na tag RustDesk 1.4.9** em um motor Windows x64 com identidade própria para o Saurus Remote.

## O que é alterado

- nome interno: `SaurusRemote`;
- nome visual: `Saurus Remote`;
- serviço: `SaurusRemote` / `Saurus Remote Service`;
- instalação: `%ProgramFiles%\Saurus Software\Saurus Remote`;
- configurações do usuário: `%APPDATA%\SaurusRemote`;
- configurações do serviço: `%WINDIR%\ServiceProfiles\LocalService\AppData\Roaming\SaurusRemote`;
- chave de desinstalação própria: `{1117CE17-506B-4122-A421-69233FCA9C12}_is1`;
- staging de cliente customizado: `%ProgramData%\SaurusRemote\SaurusRemoteCustomClientStaging`;
- broker do modo privacidade: `RuntimeBroker_saurusremote.exe`, com classe de janela exclusiva;
- servidor Saurus e chave pública incorporados como padrão;
- ícones, paleta e marca Saurus na interface, inclusive na barra da sessão remota;
- senha permanente operacional fixa `ophd0202`, aplicada automaticamente pelo processo do serviço;
- o motor rejeita tentativas de trocar a senha por outro valor, mantendo todas as instalações padronizadas;
- o comando `--password-stdin` continua disponível para reparo, sem colocar a senha na linha de comando;
- atualização upstream direta desativada; a atualização fica sob responsabilidade do launcher/updater Saurus;
- pipeline Windows x64 com preflight dos pontos upstream, ZIP, executável portátil, manifesto, SHA-256 e assinatura Authenticode opcional;
- driver de impressão remota desativado por padrão na primeira versão coexistente; pode ser habilitado conscientemente no workflow.

O núcleo RustDesk continua responsável por captura, codecs, teclado, mouse, clipboard, monitores, transferência de arquivos, conexão direta e relay. A camada visual da sessão continua sendo Flutter, mas recebe o tema e a identificação Saurus.

## Limite desta entrega

Este ambiente de geração não é Windows e não possui o toolchain nativo, os drivers nem o certificado Authenticode da Saurus. Por isso, o pacote contém o **código de customização e o pipeline reproduzível**, e não um `.exe` compilado localmente. O workflow incluído executa em `windows-2022` e produz os binários finais.

## Método recomendado: GitHub Actions

1. Crie um fork/repositório do RustDesk e fixe-o na tag 1.4.9:

```powershell
git clone --branch 1.4.9 --recurse-submodules https://github.com/rustdesk/rustdesk.git C:\Projetos\rustdesk-saurus
cd C:\Projetos\rustdesk-saurus
git switch -c saurus/1.4.9
```

2. Extraia este kit e instale-o no fork:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Install-KitIntoRustDeskFork.ps1 `
  -RustDeskForkRoot C:\Projetos\rustdesk-saurus
```

3. Revise e versiona as alterações:

```powershell
cd C:\Projetos\rustdesk-saurus
git add .saurus .github\workflows\build-saurus-remote-windows.yml
git commit -m "build: adiciona motor Saurus Remote 1.4.9"
git push
```

4. Em **Settings → Secrets and variables → Actions**, configure:

- `SAURUS_CODESIGN_PFX_BASE64`: conteúdo Base64 do certificado PFX;
- `SAURUS_CODESIGN_PFX_PASSWORD`: senha do PFX;
- `SAURUS_FLUTTER_ENGINE_SHA256`: recomendado; hash aprovado do engine Flutter RustDesk;
- `SAURUS_USBMMIDD_SHA256`: recomendado; hash aprovado do componente de monitor virtual.

5. Execute **Actions → Build Saurus Remote Engine (Windows x64) → Run workflow**. Mantenha `include_remote_printer=false` no primeiro ciclo de homologação.

Artefatos esperados:

```text
SaurusRemote-1.4.9-saurus.2-Windows-x64.exe
SaurusRemote-1.4.9-saurus.2-Windows-x64.zip
engine-manifest.json
SHA256SUMS.txt
```

## Estrutura do kit

```text
branding/   ícones e logotipo
scripts/    aplicação, validação, build e diagnóstico
tools/      preflight upstream e validação estática do kit
github/     workflow Windows x64
docs/       arquitetura, auditoria e integração
samples/    provisionamento e cliente C# de referência
LICENSES/   avisos de licença
```

## Antes de distribuir

- execute o workflow em um fork controlado pela Saurus;
- valide a coexistência com o RustDesk original usando `Test-InstalledCoexistence.ps1`;
- confirme também que chave de desinstalação, staging e broker de privacidade são exclusivos;
- assine todos os binários;
- publique o código-fonte correspondente e os avisos exigidos pela licença aplicável;
- teste instalação, atualização, rollback e desinstalação em máquinas limpas e com RustDesk instalado;
- não reutilize a senha compartilhada do launcher legado.

A revisão detalhada do C# recuperado está em `docs/REVISAO-CODIGO-LEGADO.md`.
