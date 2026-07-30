## 1.4.9-saurus.3.2.3

- Consolida a UX final em um unico pipeline idempotente.
- Migra o titulo legado "Conectar e acessar sessoes recentes" antes da validacao final.
- Mantem a validacao estrutural da UX responsiva existente.
- Impede falso negativo causado por texto residual em codigo nao renderizado.
- Exige os textos finais: Este dispositivo, Conectar a outro dispositivo e Historico e sessoes recentes.
- Mantem verificacao de UTF-8 e bloqueio de mojibake.
## 1.4.9-saurus.3.2.1.4

- Normaliza validate_kit.py para UTF-8 com LF e remove CR tratado como trailing whitespace pelo Git.
- Mantem a resolucao do workflow real em .github/workflows.
- Protege o validador com regra eol=lf em .gitattributes.
## 1.4.9-saurus.3.2.1.1

- Restaura a UX responsiva e o diagnostico aprovados anteriormente.
- Remove do dashboard os blocos antigos de diagnostico rapido e configuracoes de rede.
- Limpa a saida Flutter antes de cada compilacao para impedir binario antigo no Setup.
- Substitui a configuracao pos-instalacao por fluxo headless, sem abrir a interface.
- Adiciona watchdog de 120 segundos para impedir travamento permanente do instalador.
- Reconstroi o preflight por template completo e elimina insercao fragil dentro de param().
- Atualiza o servico existente com sc config, evitando estado marcado para exclusao.
- Analisa todos os scripts PowerShell e contratos do workflow antes do commit.

## 1.4.9-saurus.3.1.4.2

- Corrige a validacao do AppId em arquivos com quebra de linha CRLF.
- Normaliza CRLF, LF e CR antes das expressoes regulares do preflight.
- Endurece o teste para impedir regressao no runner Windows.

## 1.4.9-saurus.3.1.4.1

- Corrige o AppId do Inno Setup usando escape literal de chave GUID.
- Mantem os campos binarios de versao no formato numerico aceito pelo Windows.
- Adiciona compilacao real de preflight do instalador antes do build principal.
- Reaproveita o mesmo preflight no build local e reforca a validacao estatica do kit.

## 1.4.9-saurus.3.1.4

- Corrige o AppId do Inno Setup usando escape literal de chave GUID.
- Mantem os campos binarios de versao no formato numerico aceito pelo Windows.
- Adiciona compilacao real de preflight do instalador antes do build principal.
- Reaproveita o mesmo preflight no build local e reforca a validacao estatica do kit.

## 1.4.9-saurus.3.1.3

- Corrige VersionInfoProductVersion do Inno Setup para o formato numerico aceito pelo recurso de versao do Windows.
- Mantem a versao completa Saurus em AppVersion e VersionInfoProductTextVersion.

## 1.4.9-saurus.3.1.2

- Corrige a aplicação da senha fixa no início normal/portátil sem depender da formatação exata de core_main.rs.
- Localiza start_server(false, no_server) de forma tolerante a alterações anteriores e mantém a operação idempotente.

# Changelog

## 1.4.9-saurus.3.1.1 — correção do padrão de escala no upstream

- corrige o contrato de busca da escala desktop em `UserDefaultConfig::get`;
- troca a linha real `keys::OPTION_VIEW_STYLE` por substituição literal segura;
- adiciona validação preflight contra o `hbb_common` usado pelo RustDesk 1.4.9;
- impede o retorno do regex incorreto que procurava uma chave textual `"view_style"`.

## 1.4.9-saurus.3.1.1 — instalador definitivo e correções operacionais

- adiciona `SaurusRemote-<versão>-Setup.exe` construído com Inno Setup;
- instala em `%ProgramFiles%\Saurus Software\Saurus Remote`;
- registra e inicia o serviço `SaurusRemote`;
- configura início automático e ações de recuperação do serviço;
- aplica a senha `ophd0202` no fluxo normal, portátil, serviço e servidor;
- reaplica e valida a senha por `--password-stdin` durante a instalação e novamente depois do reinício do serviço;
- define `verification-method=use-permanent-password` e `approve-mode=password`;
- habilita acesso na tela de logon;
- define escala `adaptive` no núcleo e no arquivo default;
- define `disable_audio='Y'` e o valor padrão de `PeerConfig` como verdadeiro;
- migra `view_style='adaptive'` e `disable_audio=true` nos pares já salvos de todos os perfis encontrados;
- incorpora manifesto `requireAdministrator` no motor e no portátil;
- cria regra de firewall, atalhos e desinstalação do serviço;
- preserva ID e configurações em atualização;
- adiciona log de instalação em `%ProgramData%\Saurus Software\Saurus Remote`.

## 1.4.9-saurus.3.0.1

- corrige aplicação idempotente do patch Flutter 3.24.5;
- remove cache do SDK Flutter modificado.

## 1.4.9-saurus.3.0

- interface clara Saurus;
- remove login, conta e mapa;
- mantém dashboard, conexões, histórico, diagnóstico e configurações.

## 1.4.9-saurus.2.3

- corrige CRLF no `pubspec.yaml`.

## 1.4.9-saurus.2.2

- corrige a constante de servidor dentro de `lazy_static!`.

## 1.4.9-saurus.2.1

- corrige parser PowerShell na inserção C++.
## saurus.3.2.1.6

- Corrige de forma abrangente todas as referencias a `$home` no PowerShell embutido no workflow.
- Substitui a variavel reservada por `$desktopHomeContent` sem depender do formato exato da linha.
- Adiciona validacao para impedir nova colisao com a variavel automatica `$HOME`.
## saurus.3.2.1.7

- Corrige a falha 1639 do sc.exe ao criar o servico com caminho, conta e nome contendo espacos.
- Substitui sc.exe create/config pelos metodos Win32_Service.Create e Win32_Service.Change.
- Mantem o servico na conta NT AUTHORITY\LocalService com senha vazia para a conta interna.
- Adiciona verificacao do PathName, StartName e StartMode depois da configuracao.
- Rotaciona o log de instalacao para separar tentativas antigas da execucao atual.
- Mantem instalacao headless, watchdog, preferencias adaptativas e audio desativado.
## saurus.3.2.2.1

- Repara a corrupcao UTF-8/CP850 da interface e impede novo empacotamento com textos mojibake.
- Trata linhas vazias durante a verificacao de codificacao, evitando ParameterBindingValidationException no PowerShell 5.1.
- Remove a elevacao obrigatoria do executavel principal, mantendo elevacao somente no setup e no servico.
- Abre o aplicativo como o usuario original ao concluir o instalador.
- Reforca o servidor 20.195.216.23:443 e a chave publica em toda inicializacao.
- Grava SaurusRemote2.toml nos perfis de usuario e LocalService durante a instalacao.
- Exige que o servico permaneca estavel antes de concluir o setup.
## saurus.3.2.2.2

- Alinha o validate_kit.py com a mensagem real do configurador headless V4.
- Remove o falso negativo na validacao das preferencias adaptativas, audio desativado e servidor Saurus.
- Mantem o build bloqueado caso o configurador e o validador voltem a divergir.
