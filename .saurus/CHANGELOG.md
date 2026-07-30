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
