# Build por GitHub Actions

Este é o método recomendado porque replica o ambiente Windows x64 do projeto upstream e evita divergências locais.

## Pré-requisitos

- fork na tag 1.4.9 com submódulos;
- GitHub Actions habilitado;
- kit copiado para `.saurus`;
- workflow em `.github/workflows/build-saurus-remote-windows.yml`;
- certificado de assinatura para distribuição.

## Toolchain fixado

```text
Rust 1.75
LLVM 15.0.6
Flutter 3.24.5
vcpkg 120deac3062162151622ca4860575a33844ba10b
Windows runner windows-2022
```

## Secrets

O PFX deve ser convertido para Base64:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes('C:\certificados\saurus-code-signing.pfx')) |
  Set-Content C:\certificados\pfx-base64.txt
```

Cadastre o conteúdo como `SAURUS_CODESIGN_PFX_BASE64` e a senha como `SAURUS_CODESIGN_PFX_PASSWORD`.

Na primeira execução controlada, o workflow registra os hashes do engine Flutter e do usbmmidd no manifesto/log. Após validação interna, fixe-os nos secrets `SAURUS_FLUTTER_ENGINE_SHA256` e `SAURUS_USBMMIDD_SHA256` para builds seguintes.

## Opção de impressão remota

O input `include_remote_printer` fica desativado por padrão. O pacote de driver upstream mantém nomes próprios do ecossistema RustDesk e deve ser homologado separadamente antes de ser incluído em uma versão que precise coexistir com outra instalação. Acesso remoto, clipboard, arquivos, múltiplos monitores e o restante do motor não dependem desse driver.

## Saída

O workflow gera uma pasta funcional compactada e um executável portátil autoextraível. Ambos contêm o mesmo motor customizado. O ZIP é melhor para integração com o instalador Saurus; o portátil é útil para testes manuais.

## Validação de release

- confira `SHA256SUMS.txt`;
- verifique a assinatura de todas as DLLs e EXEs;
- confira `engine-manifest.json`;
- instale em VM limpa;
- instale em VM com RustDesk original;
- confirme os serviços `SaurusRemote` e `RustDesk` simultaneamente;
- confirme chaves de desinstalação, pastas de staging e brokers de privacidade distintos;
- abra uma sessão e valide título, ícone, barra remota e menus;
- teste atualização e rollback.
