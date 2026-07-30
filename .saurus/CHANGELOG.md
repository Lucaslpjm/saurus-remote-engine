# Changelog Saurus Remote

## 3.1.2 - 2026-07-29

- Aumenta a janela inicial e mantém o encaixe na área útil do monitor.
- Reorganiza o Dashboard em dispositivo/conexão no topo e histórico em largura total abaixo.
- Remove diagnóstico rápido e informações de rede duplicadas do Dashboard.
- Cria diagnóstico funcional com testes de serviço, ID, motor, servidor/porta, DNS, disponibilidade e versão.
- Define escala adaptada e áudio desativado somente quando ainda não há preferência salva pelo usuário.
- Separa os modos de conexão e histórico da `ConnectionPage` sem duplicar controladores globais.
- Otimiza o workflow com concorrência, checkout raso, cache somente de dependências pub, validação e formatação.

## 1.4.9-saurus.3.1.0 — instalador definitivo e correções operacionais

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
