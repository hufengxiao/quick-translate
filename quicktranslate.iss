; Quick Translate Inno Setup Script
; Build: iscc quicktranslate.iss

#define MyAppName "Quick Translate"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "Quick Translate"
#define MyAppURL "https://github.com/hufengxiao/quick-translate"
#define MyAppExeName "QuickTranslate.exe"

[Setup]
AppId={{B2C3D4E5-F6A7-8901-2345-678901234567}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\QuickTranslate
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=QuickTranslate-{#MyAppVersion}-Setup
SetupIconFile=data\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; ── Custom installer appearance ──
WizardImageFile=data\installer\wizard.bmp
WizardSmallImageFile=data\installer\small.bmp
SetupLogging=yes
DisableWelcomePage=no
WizardSizePercent=100

; ── Brand colors (match app accent #0A84FF) ──
BackColor=$0A84FF
BackColor2=$1C1C1E
WindowVisible=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Start with Windows"; GroupDescription: "Startup:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "data\installer\wizard.bmp"; DestDir: "{app}\installer"; Flags: ignoreversion skipifsourcedoesntexist
Source: "data\installer\small.bmp"; DestDir: "{app}\installer"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Start with Windows
Root: HKCU; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "QuickTranslate"; ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Kill process on uninstall
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM {#MyAppExeName}"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\installer"

[Code]
// Kill running instance before install/upgrade
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssInstall then
  begin
    Exec('taskkill', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

// Custom welcome page text
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption :=
    'Quick Translate will be installed to the following folder:' + #13#10#13#10 +
    'Features:' + #13#10 +
    '  ' + Chr(8226) + ' Instant word lookup with MDX dictionary' + #13#10 +
    '  ' + Chr(8226) + ' AI-powered translation (GPT, Claude, ...)' + #13#10 +
    '  ' + Chr(8226) + ' Vocabulary book with Anki export' + #13#10 +
    '  ' + Chr(8226) + ' Spell correction and fuzzy search' + #13#10 +
    '  ' + Chr(8226) + ' Clipboard monitoring auto-translate' + #13#10#13#10 +
    'Click Next to continue.';
end;

// Custom finished page text
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedLabel.Caption :=
      'Quick Translate has been installed successfully.' + #13#10#13#10 +
      'Press ' + Chr(8220) + 'Alt+M' + Chr(8221) + ' to open the translation window, ' +
      'or right-click the system tray icon for options.';
  end;
end;
