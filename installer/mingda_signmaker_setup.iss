; MINGDA SignMaker Inno Setup installer.
; Compile with Inno Setup 6 ISCC.exe.

#ifndef MyAppVersion
#define MyAppVersion "0.0.0"
#endif

#ifndef MyAppVersionInfo
#define MyAppVersionInfo "0.0.0.0"
#endif

#define MyAppName "MINGDA SignMaker"
#define MyAppPublisher "Shenzhen Mingda Technology Co.,Ltd."
#define MyAppExeName "MINGDA SignMaker.exe"
#define MyAppURL "https://www.mingda3d.com/"
#define MyAppDescription "LED Sign Letter 3D Printing Slicer"
#define MyAppId "{{7E58B770-04B6-4F42-B3A0-A7E17D39DF77}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=MINGDA-SignMaker-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\resources\logos\MINGDA_logo.ico

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes

VersionInfoVersion={#MyAppVersionInfo}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
VersionInfoProductName={#MyAppName}
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "associatesmp"; Description: "Associate .smp project files with {#MyAppName}"; GroupDescription: "File associations:"; Flags: unchecked
Name: "associatedxf"; Description: "Associate .dxf files with {#MyAppName}"; GroupDescription: "File associations:"; Flags: unchecked
Name: "associatesvg"; Description: "Associate .svg files with {#MyAppName}"; GroupDescription: "File associations:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKA; Subkey: "Software\Classes\.smp"; ValueType: string; ValueName: ""; ValueData: "MINGDA.SignMaker.smp"; Flags: uninsdeletevalue; Tasks: associatesmp
Root: HKA; Subkey: "Software\Classes\MINGDA.SignMaker.smp"; ValueType: string; ValueName: ""; ValueData: "MINGDA SignMaker Project"; Flags: uninsdeletekey; Tasks: associatesmp
Root: HKA; Subkey: "Software\Classes\MINGDA.SignMaker.smp\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associatesmp
Root: HKA; Subkey: "Software\Classes\MINGDA.SignMaker.smp\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associatesmp

Root: HKA; Subkey: "Software\Classes\.dxf"; ValueType: string; ValueName: ""; ValueData: "MINGDA.SignMaker.dxf"; Flags: uninsdeletevalue; Tasks: associatedxf
Root: HKA; Subkey: "Software\Classes\MINGDA.SignMaker.dxf"; ValueType: string; ValueName: ""; ValueData: "DXF Drawing File"; Flags: uninsdeletekey; Tasks: associatedxf
Root: HKA; Subkey: "Software\Classes\MINGDA.SignMaker.dxf\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associatedxf
Root: HKA; Subkey: "Software\Classes\MINGDA.SignMaker.dxf\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associatedxf

Root: HKA; Subkey: "Software\Classes\.svg"; ValueType: string; ValueName: ""; ValueData: "MINGDA.SignMaker.svg"; Flags: uninsdeletevalue; Tasks: associatesvg
Root: HKA; Subkey: "Software\Classes\MINGDA.SignMaker.svg"; ValueType: string; ValueName: ""; ValueData: "SVG Vector File"; Flags: uninsdeletekey; Tasks: associatesvg
Root: HKA; Subkey: "Software\Classes\MINGDA.SignMaker.svg\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: associatesvg
Root: HKA; Subkey: "Software\Classes\MINGDA.SignMaker.svg\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: associatesvg

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
