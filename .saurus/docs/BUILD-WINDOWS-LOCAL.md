# Build local no Windows

O build local é indicado para desenvolvimento. Para release, prefira o workflow.

É necessário preparar manualmente o toolchain equivalente ao workflow oficial: Visual Studio/Windows SDK, Rust, LLVM, Flutter com engine customizado, Python e vcpkg. O ambiente precisa ter `VCPKG_ROOT` definido.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Build-SaurusRemote.ps1 `
  -SourceRoot C:\Projetos\rustdesk-saurus `
  -ApplyCustomization `
  -BuildLabel saurus.dev1
```

Para assinar com certificado instalado no Windows:

```powershell
.\scripts\Build-SaurusRemote.ps1 `
  -SourceRoot C:\Projetos\rustdesk-saurus `
  -BuildLabel saurus.2 `
  -SigningCertificateThumbprint 'THUMBPRINT_SEM_ESPACOS'
```

O script valida a customização, compila, renomeia o executável, gera manifesto, ZIP, portátil e SHA-256. Componentes externos usados pelo build devem ser aprovados e fixados internamente antes de uma release.
