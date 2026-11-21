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
Name: "installpython"; Description: "Check & automatically install Python 3.11.9 + required packages if missing on this PC"; GroupDescription: "System Prerequisites:"

[Dirs]
Name: "{app}\data"
Name: "{app}\exports"
Name: "{app}\backups"
Name: "{app}\logs"

[Files]
Source: "..\dist\WikIranArchive\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\WikIranArchive\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\OPERATOR_MANUAL_EN.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\OPERATOR_MANUAL_FA.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ""$py = Get-Command python.exe -ErrorAction SilentlyContinue; if (-not $py -or $py.Source -like '*WindowsApps*') { $tmp = Join-Path $env:TEMP 'python-3.11.9-amd64.exe'; try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', $tmp); Start-Process $tmp -ArgumentList '/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1' -Wait; Remove-Item $tmp -Force -ErrorAction SilentlyContinue } catch {} }; $py2 = Get-Command python.exe -ErrorAction SilentlyContinue; if ($py2 -and $py2.Source -notlike '*WindowsApps*') { Start-Process $py2.Source -ArgumentList '-m pip install --quiet -r ""{app}\requirements.txt""' -WindowStyle Hidden -Wait }"""; StatusMsg: "Checking PC prerequisites and installing Python 3.11 + packages if needed..."; Flags: runhidden waituntilterminated; Tasks: installpython
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

