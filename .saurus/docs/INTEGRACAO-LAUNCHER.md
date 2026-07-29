# Integração do launcher com o motor customizado

## Contrato do motor

```text
Executável instalado: C:\Program Files\Saurus Software\Saurus Remote\SaurusRemote.exe
Serviço: SaurusRemote
Nome visual: Saurus Remote Service
Configuração do usuário: %APPDATA%\SaurusRemote
Configuração do serviço: %WINDIR%\ServiceProfiles\LocalService\AppData\Roaming\SaurusRemote
```

Comandos relevantes:

```text
SaurusRemote.exe --silent-install
SaurusRemote.exe --get-id
SaurusRemote.exe --password-stdin
SaurusRemote.exe --connect <ID>
SaurusRemote.exe --uninstall
```

## Regras obrigatórias

1. Nunca procurar, parar ou apagar o serviço `RustDesk`.
2. Nunca usar `C:\Program Files\RustDesk`.
3. Validar que `Win32_Service.PathName` aponta para o executável Saurus esperado.
4. Validar o ID remoto com uma expressão restritiva antes de iniciar a sessão.
5. Não incluir senha em `Arguments`, logs, histórico ou mensagens de erro.
6. Usar timeout e `CancellationToken` em todas as operações.
7. Confirmar a pós-condição de cada comando: serviço, arquivo, versão, ID e configuração.
8. Verificar hash e Authenticode antes de instalar ou atualizar.

## Elevação

O launcher deve usar `asInvoker`. Para instalar/atualizar:

```text
Launcher → helper elevado assinado → operação autorizada → JSON de resultado
```

O helper deve aceitar apenas comandos conhecidos (`install`, `repair`, `update`, `uninstall`, `set-password`) e não uma linha arbitrária de `cmd.exe`.

## Senha

O exemplo `samples/SaurusRemoteEngineClient.cs` mostra como escrever a senha no stdin do motor. Quando o launcher não estiver elevado, delegue essa operação ao helper. A senha deve ser gerada por CSPRNG e guardada com DPAPI.

## Sessão

Ao conectar, o launcher deve executar `SaurusRemote.exe --connect <ID>`. Como o frontend Flutter foi customizado, a janela aberta continuará exibindo Saurus Remote, e não o layout/identidade padrão do RustDesk.

## Diagnóstico de coexistência

Depois da instalação, execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Test-InstalledCoexistence.ps1
```

O teste falha se o serviço não existir, apontar para uma pasta RustDesk, compartilhar o mesmo binário, herdar o mesmo `InstallLocation`, usar a chave de desinstalação errada ou não localizar o executável Saurus. Ele também registra staging e processos auxiliares dos dois produtos para diagnóstico.
