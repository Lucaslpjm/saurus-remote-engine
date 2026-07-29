# Changelog

## 1.4.9-saurus.3.0 — interface clara sem login e sem mapa

- nova tela principal clara inspirada no design system Saurus;
- sem perfil de usuário, login, logout ou mapa;
- painel funcional com ID, senha, status, diagnóstico e conexões recentes;
- tema claro fixo;
- aba de conta e opções dependentes de login ocultadas;
- mantém senha operacional `ophd0202`, servidor Saurus e isolamento do RustDesk original.

## 1.4.9-saurus.2.3 — correção de CRLF no `pubspec.yaml`

- Corrige o falso negativo na alteração da descrição Flutter em runners Windows.
- Substitui o regex ancorado por uma troca literal validada pelo preflight da tag 1.4.9.
- Funciona com arquivos em LF ou CRLF sem alterar a estrutura YAML.
- Mantém as correções anteriores de parser PowerShell e indentação do `lazy_static!`.

## 1.4.9-saurus.2.2 — correção da constante de servidor no `lazy_static`

- Corrige o patch de `PROD_RENDEZVOUS_SERVER` no `libs/hbb_common/src/config.rs`.
- Preserva os quatro espaços de indentação exigidos pelo bloco `lazy_static!`.
- Substitui o regex frágil por troca literal validada contra a estrutura da tag 1.4.9.
- Mantém a correção anterior do parser PowerShell na inserção C++.

## 1.4.9-saurus.2.1 — correção do parser PowerShell

- corrigido o escape das aspas na linha que insere `app_name = L"Saurus Remote";` em `flutter/windows/runner/main.cpp`;
- eliminado o `ParserError` que ocorria antes da aplicação das customizações;
- adicionada validação de regressão para impedir que o escape inválido volte ao kit.

## 1.4.9-saurus.1 — kit inicial

- isolamento de nome interno, serviço, instalação, configuração e IPC;
- servidor e chave Saurus como padrão;
- tema e ícones Saurus;
- marca Saurus na barra da sessão remota;
- metadados Windows próprios;
- `--password-stdin` para provisionamento sem segredo na linha de comando;
- remoção de senha universal embutida;
- desativação da atualização upstream direta;
- workflow Windows x64 baseado nas versões fixadas pelo build oficial 1.4.9;
- assinatura Authenticode opcional;
- manifesto e checksums do pacote;
- scripts de diagnóstico e coexistência;
- relatório de auditoria do launcher decompilado.

## 1.4.9-saurus.1 — endurecimento de coexistência

- chave Inno Setup exclusiva para impedir herança do `InstallLocation` do RustDesk;
- staging público de cliente customizado isolado;
- limpeza de temporários limitada ao prefixo do Saurus Remote;
- broker e janelas do modo privacidade renomeados;
- preflight automático dos pontos de patch do upstream 1.4.9;
- impressão remota desativada por padrão no workflow;
- compatibilidade do cliente de referência corrigida para .NET Framework 4.7.2.
