; Inno Setup script. Build from api/ after PyInstaller:
;   iscc /DAppVersion=0.1.0 desktop\installer\heal_tool.iss
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{7B0C5B6E-4F0B-4C57-9B52-3C1D2A9E6A11}
AppName=HEAL Tool
AppVersion={#AppVersion}
AppPublisher=HEALstrata
DefaultDirName={autopf}\HEALTool
DefaultGroupName=HEAL Tool
; Per-user install by default so no admin rights are needed.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\dist
OutputBaseFilename=HEALTool-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\HEALTool.exe
WizardStyle=modern

[Files]
Source: "..\..\dist\HEALTool\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\HEAL Tool"; Filename: "{app}\HEALTool.exe"
Name: "{autodesktop}\HEAL Tool"; Filename: "{app}\HEALTool.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; \
  StatusMsg: "Installing Microsoft WebView2 Runtime..."; Check: BootstrapperReady
Filename: "{app}\HEALTool.exe"; Description: "Launch HEAL Tool"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2Guid = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function WebView2Installed: Boolean;
var
  Version: String;
begin
  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + WebView2Guid, 'pv', Version) or
     RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\' + WebView2Guid, 'pv', Version)) and
    (Version <> '') and (Version <> '0.0.0.0');
end;

function BootstrapperReady: Boolean;
begin
  Result := (not WebView2Installed) and FileExists(ExpandConstant('{tmp}\MicrosoftEdgeWebview2Setup.exe'));
end;

// Windows 10/11 normally ship WebView2; fetch Microsoft's bootstrapper only when missing.
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssInstall) and (not WebView2Installed) then
  begin
    try
      DownloadTemporaryFile('https://go.microsoft.com/fwlink/p/?LinkId=2124703',
        'MicrosoftEdgeWebview2Setup.exe', '', nil);
    except
      MsgBox('Could not download the Microsoft WebView2 Runtime. HEAL Tool may not start ' +
        'until it is installed from https://developer.microsoft.com/microsoft-edge/webview2/',
        mbInformation, MB_OK);
    end;
  end;
end;
