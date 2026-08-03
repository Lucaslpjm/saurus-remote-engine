# Instalador definitivo do Saurus Remote

## Objetivo

O arquivo portátil continua disponível, mas o artefato recomendado é o `Setup.exe`. Ele resolve as diferenças entre executar uma cópia portátil e manter acesso não assistido após reinicialização, tela de logon e UAC.

## Sequência de instalação

1. O setup solicita privilégios administrativos.
2. Para a versão anterior e encerra a interface.
3. Copia o motor e todas as dependências para Program Files.
4. Registra o serviço `SaurusRemote` como `LocalSystem`, com início automático e recuperação em falhas.
5. Define as opções de autenticação e tela de logon.
6. Grava as preferências operacionais; o próprio motor reforça `ophd0202` no início normal, serviço e servidor.
7. Bloqueia alterações para outra senha.
8. Grava preferências de escala adaptável e som desativado e migra pares já salvos.
9. Cria regra de firewall e reinicia o serviço.
10. Reinicia o serviço e confirma que `--server` permanece ativo na sessão interativa antes de concluir o setup.

## Atualização

A instalação sobre uma versão anterior para o serviço, substitui os binários e registra novamente o serviço sem apagar `%APPDATA%\SaurusRemote`. O ID e o histórico devem ser preservados.

## Desinstalação

O desinstalador remove serviço, processos e regra de firewall. As configurações e o ID não são apagados automaticamente, para permitir reinstalação e recuperação. Uma rotina de remoção total pode ser adicionada posteriormente.

## Log

```text
%ProgramData%\Saurus Software\Saurus Remote\install-config.log
```

Esse arquivo deve ser solicitado quando instalação, senha, serviço ou ID não forem concluídos.

## Elevação administrativa

O `SaurusRemoteLauncher.exe` instalado e o portátil recebem manifesto `requireAdministrator`. Os atalhos e a abertura pós-instalação usam esse launcher, portanto o Windows exibe o UAC antes da interface. O motor `SaurusRemote.exe` permanece `asInvoker/default`, pois o mesmo binário executa os modos internos `--service`, `--server` e `--tray`; aplicar elevação obrigatória diretamente nele impede a criação correta desses subprocessos na sessão do usuário.
