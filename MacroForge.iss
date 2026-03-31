[Setup]
AppName=MacroForge
AppVersion=1.0.0
AppPublisher=MacroForge Contributors
AppPublisherURL=https://github.com/shinzocs/MacroForge
AppSupportURL=https://github.com/shinzocs/MacroForge/issues
AppUpdatesURL=https://github.com/shinzocs/MacroForge/releases
DefaultDirName={autopf}\MacroForge
DefaultGroupName=MacroForge
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=MacroForge_Setup_v1.0.0
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\MACROFORGE.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\MACROFORGE.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico";            DestDir: "{app}"; Flags: ignoreversion
Source: "icon.png";            DestDir: "{app}"; Flags: ignoreversion
Source: "README.md";           DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE";             DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md";        DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MacroForge";            Filename: "{app}\MACROFORGE.exe"
Name: "{group}\Uninstall MacroForge";  Filename: "{uninstallexe}"
Name: "{autodesktop}\MacroForge";      Filename: "{app}\MACROFORGE.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MACROFORGE.exe"; Description: "{cm:LaunchProgram,MacroForge}"; Flags: nowait postinstall skipifsilent
