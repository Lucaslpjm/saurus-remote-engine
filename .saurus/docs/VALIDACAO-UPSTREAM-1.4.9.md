# Validação dos pontos upstream — RustDesk 1.4.9

O kit não aplica substituições genéricas. Antes do patch, `tools/check_upstream_149.py` exige que cada ponto esperado exista na quantidade correta. O script PowerShell também interrompe a execução quando um padrão não corresponde ao fonte fixado.

Pontos verificados:

- versão `1.4.9` no pacote principal;
- nome interno usado pelas configurações;
- implementação dos comandos de senha e atualização;
- título usado no despacho para a janela Flutter;
- caminho de instalação, serviço e chave Inno Setup do Windows;
- staging de cliente customizado e limpeza de atualizações temporárias;
- broker e nomes de janela do modo privacidade;
- metadados do runner Windows;
- funções FFI que fornecem o nome visual ao Flutter;
- tema e barra da sessão remota;
- declaração de assets no `pubspec.yaml`.

## Resultado que ainda precisa ocorrer em Windows

A validação estática deste kit não substitui o build. O artefato final só deve ser aprovado depois que o workflow `windows-2022` concluir:

1. customização;
2. verificação pós-patch;
3. geração da ponte Flutter/Rust;
4. compilação Rust/Flutter;
5. empacotamento;
6. assinatura;
7. testes em VM limpa e em VM com RustDesk original.

Qualquer atualização do upstream deve começar por um novo inventário desses pontos; não use `-AllowDifferentUpstreamVersion` em release de produção sem revisar os diffs.
