#ifndef SourceRoot
  #error SourceRoot must be supplied by ISCC /DSourceRoot=...
#endif
#ifndef OutputDir
  #error OutputDir must be supplied by ISCC /DOutputDir=...
#endif
#ifndef ProductVersion
  #define ProductVersion "1.4.9-saurus.3.1.0"
#endif
#ifndef InstallerRoot
  #error InstallerRoot must be supplied by ISCC /DInstallerRoot=...
#endif
#ifndef BrandingRoot
  #error BrandingRoot must be supplied by ISCC /DBrandingRoot=...
#endif

#define AppGuid "{1117CE17-506B-4122-A421-69233FCA9C12}"
#define AppName "Saurus Remote"
#define AppPublisher "Saurus Software"
#define AppExeName "SaurusRemote.exe"

[Setup]
AppId={#AppGuid}
AppName={#AppName}
AppVersion={#ProductVersion}
AppVerName={#AppName} {#ProductVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Saurus Software\Saurus Remote
DefaultGroupName=Saurus Remote
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir={#OutputDir}
OutputBaseFilename=SaurusRemote-{#ProductVersion}-Setup
SetupIconFile={#BrandingRoot}\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
SetupLogging=yes
MinVersion=10.0.17763
VersionInfoVersion=1.4.9.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Instalador do Saurus Remote
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#ProductVersion}

[Files]
Source: "{#SourceRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#InstallerRoot}\Configure-SaurusRemote.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "{#InstallerRoot}\Uninstall-SaurusRemote.ps1"; DestDir: "{app}\tools"; Flags: ignoreversion
Source: "{#InstallerRoot}\SaurusRemote_default.toml"; DestDir: "{app}\defaults"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Saurus Remote"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\Saurus Remote"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir o Saurus Remote"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\tools\Uninstall-SaurusRemote.ps1"" -InstallDir ""{app}"""; Flags: runhidden waituntilterminated; RunOnceId: "SaurusRemoteRemoveService"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\sc.exe'), 'stop SaurusRemote', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM SaurusRemote.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  PowerShellExe: String;
  ConfigureScript: String;
  Parameters: String;
begin
  if CurStep <> ssPostInstall then
    Exit;

  PowerShellExe := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  ConfigureScript := ExpandConstant('{app}\tools\Configure-SaurusRemote.ps1');
  Parameters := '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
    ConfigureScript + '" -InstallDir "' + ExpandConstant('{app}') + '"';

  WizardForm.StatusLabel.Caption := 'Configurando serviço, senha e preferências do Saurus Remote...';
  if not Exec(PowerShellExe, Parameters, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    RaiseException('Não foi possível iniciar a configuração final do Saurus Remote.');
  if ResultCode <> 0 then
    RaiseException(Format('A configuração final do Saurus Remote falhou (código %d). Consulte o log em %%ProgramData%%\Saurus Software\Saurus Remote\install-config.log.', [ResultCode]));
end;
