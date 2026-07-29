# Saurus Remote 1.4.9 - UX Refresh 3.1.2

Este pacote foi montado a partir do repositório informado e contém o projeto completo, os scripts de customização já existentes e o novo ajuste de interface.

## Por que existe o Preparar-Projeto.ps1

O arquivo ZIP exportado pelo GitHub não traz o conteúdo do submódulo `libs/hbb_common`. Sem ele, o preflight e a compilação falham. O preparador clona a branch correta com `--recurse-submodules` e aplica os arquivos desta versão por cima do clone.

## Preparação recomendada

1. Extraia este ZIP, por exemplo, em:

```text
C:\SaurusRemote-Package
```

2. Abra o PowerShell nessa pasta e execute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Preparar-Projeto.ps1
```

O projeto pronto será criado em:

```text
C:\SaurusRemote
```

Para recriar a pasta do zero:

```powershell
.\Preparar-Projeto.ps1 -ForceReclone
```

3. Valide a estrutura:

```powershell
cd C:\SaurusRemote
.\Verificar-Projeto.ps1
```

## Publicação e compilação

Abra `C:\SaurusRemote` no GitHub Desktop, faça commit das alterações e envie para a branch:

```text
saurus/1.4.9
```

No GitHub:

```text
Actions
→ Build Saurus Remote Engine (Windows x64)
→ Run workflow
```

Use:

```text
Build label: saurus.3.1.2
Impressão remota: false
```

## Ajustes incluídos

- janela inicial maior e limitada à área útil do monitor;
- Dashboard responsivo para telas pequenas e grandes;
- dispositivo e conexão na faixa superior;
- histórico em largura total na parte inferior;
- remoção do diagnóstico rápido e das informações de rede duplicadas;
- tela própria de diagnóstico com serviço, ID, servidor, porta, DNS, disponibilidade, versão e relatório copiável;
- escala adaptada como padrão somente quando o usuário ainda não possui preferência salva;
- som desativado como padrão somente quando o usuário ainda não possui preferência salva;
- correção da navegação do menu Diagnóstico;
- cancelamento de builds obsoletos com o mesmo identificador;
- checkout raso;
- cache apenas das dependências pub, sem cachear o SDK Flutter modificado;
- validação sintética, verificação estática e formatação dos arquivos alterados antes do build nativo.

## Observação

A customização visual é aplicada no runner do GitHub Actions depois do script `Apply-SaurusCustomization.ps1`. Isso preserva o código upstream e mantém a aplicação idempotente.
