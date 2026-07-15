; Inno Setup script for KobeFinance Terminal
; Compile:  iscc /DAppVersion=0.1.0 packaging\installer.iss
; Consumes the PyInstaller one-folder output at dist\KobeFinanceTerminal\

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define AppName "KobeFinance Terminal"
#define AppPublisher "KobePay Tech"
#define AppExeName "KobeFinanceTerminal.exe"

[Setup]
AppId={{4B0C2A1E-7E1D-4F3A-9C2B-KOBEFIN00001}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\KobeFinance Terminal
DefaultGroupName=KobeFinance Terminal
DisableProgramGroupPage=yes
OutputDir=dist\installer
OutputBaseFilename=KobeFinanceTerminal-{#AppVersion}-windows-x64-setup
SetupIconFile={#SourcePath}kobefinance.ico
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\KobeFinanceTerminal\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\KobeFinance Terminal"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall KobeFinance Terminal"; Filename: "{uninstallexe}"
Name: "{autodesktop}\KobeFinance Terminal"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,KobeFinance Terminal}"; Flags: nowait postinstall skipifsilent
