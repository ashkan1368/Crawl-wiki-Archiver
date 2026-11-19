; ============================================================================
; Inno Setup Installer Script for WikIran Archive (Windows 11)
; Builds a single self-contained Windows Installer: WikIranArchive_Setup.exe
; Steps for the user:
;   1. Double-click WikIranArchive_Setup.exe
;   2. Choose Storage / Installation Path & Click Install
;   3. Desktop shortcut ("WikIran Archive") is created automatically
;   4. WikIran Archive launches immediately
; ============================================================================

#define MyAppName "WikIran Archive"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "WikIran Research Archive"
#define MyAppExeName "WikIranArchive.exe"

[Setup]
AppId={{8D4F9B2A-5C1E-47A9-9E3B-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\WikIranArchive
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=no
OutputDir=installer_output
OutputBaseFilename=WikIranArchive_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Dirs]
Name: "{app}\data"
Name: "{app}\exports"
Name: "{app}\backups"
Name: "{app}\logs"

[Files]
Source: "..\dist\WikIranArchive\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\WikIranArchive\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\OPERATOR_MANUAL_EN.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\OPERATOR_MANUAL_FA.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
