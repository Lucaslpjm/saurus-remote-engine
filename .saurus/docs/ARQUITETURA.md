# Arquitetura recomendada

## Componentes

```text
SaurusRemote.Launcher.exe       interface, histórico e conexão
SaurusRemote.ElevatedHelper.exe operações administrativas mínimas
SaurusRemote.exe                cliente/motor RustDesk customizado
SaurusRemoteUpdater.exe         atualização atômica e rollback
SaurusRemoteDiagnostics.exe     coleta sanitizada de diagnóstico
SaurusRemote (serviço)          host de acesso não assistido
```

O launcher deve executar como `asInvoker`. Instalação, alteração de serviço e atualização devem passar por um helper pequeno, assinado, com comandos limitados. A sessão remota é aberta pelo `SaurusRemote.exe`, cuja interface Flutter já recebe a identidade visual Saurus.

## Isolamento

| Recurso | Saurus Remote | RustDesk original |
|---|---|---|
| Serviço | `SaurusRemote` | `RustDesk` |
| Processo | `SaurusRemote.exe` | `rustdesk.exe` |
| Instalação | `Saurus Software\Saurus Remote` | `RustDesk` |
| Configuração | `%APPDATA%\SaurusRemote` | `%APPDATA%\RustDesk` |
| Configuração do serviço | `...\Roaming\SaurusRemote` | `...\Roaming\RustDesk` |
| URI | `saurusremote://` | `rustdesk://` |
| Chave Inno Setup | `{1117CE17-506B-4122-A421-69233FCA9C12}_is1` | `{54E86BC2-6C85-41F3-A9EB-1A94AC9B1F93}_is1` |
| Staging público | `SaurusRemote\SaurusRemoteCustomClientStaging` | `RustDesk\RustDeskCustomClientStaging` |
| Broker privacidade | `RuntimeBroker_saurusremote.exe` | `RuntimeBroker_rustdesk.exe` |

A coexistência é requisito: reparar ou remover o Saurus Remote nunca pode parar, apagar, reconfigurar ou desinstalar o RustDesk original. A identidade precisa ser separada também nos recursos menos visíveis, como registro de desinstalação, staging de atualização e janela auxiliar do modo privacidade.

## Estados do launcher

```text
Ausente → Instalando → Serviço iniciando → Configurando
→ Validando ID/Relay → Pronto → Conectando → Em sessão
```

Cada transição deve ter timeout, cancelamento, log estruturado, código de erro e rollback. Esperas fixas não devem representar sucesso.

## Credencial de acesso

- gere uma senha aleatória individual por instalação;
- envie ao motor por stdin usando `--password-stdin`;
- proteja a cópia local com DPAPI (`CurrentUser` ou `LocalMachine`, conforme o modelo);
- não grave a senha em logs, linha de comando, arquivo TOML ou histórico;
- permita rotação sem reinstalar o motor;
- em ambiente de suporte, considere aprovação interativa ou credencial temporária como padrão.

## Atualização

O motor desativa `--update` upstream. O updater Saurus deve:

1. baixar um manifesto assinado;
2. validar versão, arquitetura, SHA-256 e assinatura Authenticode;
3. parar apenas `SaurusRemote`;
4. trocar arquivos de forma atômica;
5. reiniciar e executar health check;
6. restaurar a versão anterior em caso de falha.

## Diagnóstico

O diagnóstico deve separar:

- integridade do pacote e assinatura;
- identidade/caminho do serviço;
- versão do launcher e do motor;
- obtenção do ID;
- DNS e TCP do servidor;
- relay e eventual fallback;
- logs recentes sanitizados;
- presença independente do RustDesk original.
