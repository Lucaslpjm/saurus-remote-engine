# Changelog

## 1.4.9-saurus.2 — senha operacional padronizada

- define `ophd0202` como senha permanente obrigatória em todas as instalações;
- reaplica a senha na inicialização do serviço e do servidor;
- rejeita tentativas de gravar uma senha permanente diferente;
- mantém `--password-stdin` para reparo sem exposição no CommandLine;
- atualiza cliente C#, scripts, manifestos e validações para a política fixa.

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
