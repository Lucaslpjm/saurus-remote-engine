# Revisão do launcher C# recuperado

## Escopo efetivamente recebido

Os conjuntos denominados “Saurus Instalador” e “Saurus Remote” são equivalentes: mesmo `.csproj`, manifesto, `Form1`, `Program`, recursos e metadados. Portanto, o material recuperado representa um único launcher WinForms; não há, nos anexos, uma implementação distinta de instalador.

## Problemas críticos

### 1. Conflito destrutivo com RustDesk original

O código aponta para `C:\Program Files\RustDesk\rustdesk.exe`, usa o serviço `rustdesk`, compartilha as pastas `%APPDATA%\RustDesk` e `LocalService\...\RustDesk`, encerra todos os processos `rustdesk`, remove o serviço, apaga a pasta do produto e remove os TOMLs. A rotina também exclui atalhos do RustDesk.

Consequência: em uma máquina com RustDesk original, “reparar conexão” pode danificar ou substituir a instalação independente.

Correção: usar somente `SaurusRemote`, validar o caminho registrado no serviço e nunca operar sobre recursos com identidade RustDesk.

### 2. Senha permanente universal no executável

Uma única senha é constante, aplicada a todas as máquinas, exibida na tela e copiada para o clipboard. Quem obtiver o binário ou a senha de uma estação pode tentar utilizá-la em outras.

Correção: senha individual, aleatória, rotacionável, protegida por DPAPI e enviada por stdin; ou acesso interativo/temporário.

### 3. Download sem validação de integridade

O launcher baixa um executável por HTTPS e o executa elevado, mas não valida SHA-256, assinatura Authenticode, versão ou publisher. O arquivo também é reutilizado indefinidamente se já existir no cache.

Correção: manifesto assinado, hash fixado, validação de assinatura e download atômico em arquivo temporário.

### 4. Resultado administrativo ignorado

`ExecutarCmdAdminAsync` não captura código de saída, stdout ou stderr. Cancelar o UAC, falhar um `sc`, `net`, `rmdir` ou instalador pode ser tratado como se tivesse funcionado.

Correção: helper elevado com protocolo estruturado, retorno obrigatório e verificação pós-condição.

### 5. Falsos positivos de conectividade

A validação aceita como sucesso situações como:

- existir um ID numérico;
- qualquer linha do `netstat` contendo o IP;
- log antigo contendo termos genéricos;
- no modo público, apenas obter um ID.

Isso não prova que o serviço correto está registrado nem que uma sessão poderá usar ID/relay.

Correção: health check do serviço pelo caminho, configuração efetiva, obtenção de ID, conectividade do rendezvous e teste de relay com erro classificado.

### 6. Injeção por argumento de conexão

O ID remoto remove espaços, mas não é limitado estritamente a dígitos antes de ser concatenado a `--connect`. Um valor malformado pode introduzir argumentos adicionais no motor.

Correção: aceitar somente o formato permitido pelo RustDesk e usar uma API de argumentos, nunca uma string concatenada sem validação.

## Problemas de alta prioridade

- `WaitForExit(5000)` não trata timeout nem encerra o processo; a leitura posterior pode bloquear;
- buffers stdout/stderr são lidos somente depois da espera, com risco de deadlock;
- `async` dentro de `Invoke((Action)...)` vira `async void`, perdendo propagação de erro;
- configuração é sobrescrita diretamente em duas identidades RustDesk e pode ser regravada pelo serviço;
- `Task.Delay` fixo é usado para inferir instalação, IPC e inicialização;
- o ID é cacheado sem vínculo com versão, servidor ou configuração;
- exceções são silenciadas em diversos pontos;
- histórico e preferências são arquivos texto sem proteção, locking ou escrita atômica;
- logs podem registrar argumentos sensíveis;
- o aplicativo inteiro exige administrador, apesar de a maior parte da UI não precisar;
- não há mutex de instância nem trava de manutenção;
- não há verificação de compatibilidade entre launcher e motor;
- o botão de reparo executa uma reinstalação destrutiva em vez de reparar o componente identificado.

## Problemas de projeto e interface

- toda a aplicação está concentrada em uma classe `Form1`;
- interface criada manualmente com coordenadas fixas, sem responsividade e DPI adequado;
- projeto marca `Prefer32Bit=True`, enquanto instala um motor descrito como 64 bits;
- metadados do assembly são genéricos (`Remote`, versão 1.0.0.0), mas a UI informa v5.0;
- manifesto força administrador e deixa DPI, long paths e Common Controls desabilitados;
- `GetHicon()` não libera o handle nativo;
- imagem carregada com `Image.FromStream` é mantida após o stream ser descartado;
- configuração `chave=valor` usa `Split('=')` sem limite;
- não há testes automatizados nem separação entre UI, rede, serviço, atualização e persistência.

## Refatoração recomendada do C#

```text
Saurus.Remote.App
Saurus.Remote.Application
Saurus.Remote.Engine
Saurus.Remote.Infrastructure
Saurus.Remote.ElevatedHelper
Saurus.Remote.Updater
Saurus.Remote.Tests
```

Começar pelo isolamento do motor e pelo runner de processos. Depois migrar o launcher para .NET moderno, manter a UI como `asInvoker`, criar um helper elevado mínimo e implementar diagnóstico por estados. A reconstrução do launcher deve ocorrer somente depois de o binário customizado ser compilado e testado, pois caminhos, serviço e CLI passam a ser contratos estáveis.
