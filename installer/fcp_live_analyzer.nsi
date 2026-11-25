; FCP Live Analyzer 2.0 - NSIS installer
; Build: "C:\Program Files (x86)\NSIS\makensis.exe" installer\fcp_live_analyzer.nsi
; Requires dist\FCP_Live_Analyzer (PyInstaller one-folder build).

Unicode true
!include "MUI2.nsh"
!include "x64.nsh"

!define APPNAME "FCP Live Analyzer"
!define APPVER "2.0.0"
!define COMPANY "Tiago Lima Bicalho Cruz"
!define EXENAME "FCP_Live_Analyzer.exe"
!define SRCDIR "..\dist\FCP_Live_Analyzer"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\FCPLiveAnalyzer"

Name "${APPNAME} ${APPVER}"
OutFile "..\dist\FCP_Live_Analyzer_${APPVER}_Setup.exe"
InstallDir "$PROGRAMFILES64\${APPNAME}"
InstallDirRegKey HKLM "Software\FCPLiveAnalyzer" "InstallDir"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
BrandingText "${APPNAME} ${APPVER}"

VIProductVersion "2.0.0.0"
VIAddVersionKey "ProductName" "${APPNAME}"
VIAddVersionKey "ProductVersion" "${APPVER}"
VIAddVersionKey "FileVersion" "${APPVER}"
VIAddVersionKey "CompanyName" "${COMPANY}"
VIAddVersionKey "LegalCopyright" "Copyright 2025-2026 ${COMPANY}. Apache License 2.0"
VIAddVersionKey "FileDescription" "${APPNAME} installer"

!define MUI_ICON "..\assets\logo_fcp.ico"
!define MUI_UNICON "..\assets\logo_fcp.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${EXENAME}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "PortugueseBR"

LangString SecApp ${LANG_ENGLISH} "FCP Live Analyzer (required)"
LangString SecApp ${LANG_PORTUGUESEBR} "FCP Live Analyzer (obrigatório)"
LangString SecDesk ${LANG_ENGLISH} "Desktop shortcut"
LangString SecDesk ${LANG_PORTUGUESEBR} "Atalho na área de trabalho"
LangString ManEN ${LANG_ENGLISH} "Manual (English)"
LangString ManEN ${LANG_PORTUGUESEBR} "Manual (inglês)"
LangString ManPT ${LANG_ENGLISH} "Manual (Portuguese)"
LangString ManPT ${LANG_PORTUGUESEBR} "Manual (português)"
LangString Uninst ${LANG_ENGLISH} "Uninstall"
LangString Uninst ${LANG_PORTUGUESEBR} "Desinstalar"

Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "FCP Live Analyzer requires 64-bit Windows."
    Abort
  ${EndIf}
  SetRegView 64
  !insertmacro MUI_LANGDLL_DISPLAY
FunctionEnd

Section "!$(SecApp)" SEC_APP
  SectionIn RO
  SetOutPath "$INSTDIR"
  ; remove files of a previous version before copying
  RMDir /r "$INSTDIR\_internal"
  File /r "${SRCDIR}\*.*"
  File "..\LICENSE"
  File "..\NOTICE"
  File "..\CHANGELOG.md"
  WriteRegStr HKLM "Software\FCPLiveAnalyzer" "InstallDir" "$INSTDIR"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\${APPNAME}"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\${EXENAME}" "" "$INSTDIR\${EXENAME}" 0
  CreateShortCut "$SMPROGRAMS\${APPNAME}\$(ManEN).lnk" "$INSTDIR\_internal\docs\Manual_FCP_Live_Analyzer_EN.pdf"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\$(ManPT).lnk" "$INSTDIR\_internal\docs\Manual_FCP_Live_Analyzer_pt-BR.pdf"
  CreateShortCut "$SMPROGRAMS\${APPNAME}\$(Uninst).lnk" "$INSTDIR\Uninstall.exe"

  WriteRegStr HKLM "${UNINSTKEY}" "DisplayName" "${APPNAME} ${APPVER}"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayVersion" "${APPVER}"
  WriteRegStr HKLM "${UNINSTKEY}" "Publisher" "${COMPANY}"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\${EXENAME}"
  WriteRegStr HKLM "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTKEY}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "${UNINSTKEY}" "URLInfoAbout" "https://github.com/tiagolbc/FCPLiveAnalyzer"
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoRepair" 1
SectionEnd

Section "$(SecDesk)" SEC_DESK
  CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${EXENAME}" "" "$INSTDIR\${EXENAME}" 0
SectionEnd

Section "Uninstall"
  SetRegView 64
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APPNAME}"
  RMDir /r "$INSTDIR\_internal"
  Delete "$INSTDIR\${EXENAME}"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\NOTICE"
  Delete "$INSTDIR\CHANGELOG.md"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  DeleteRegKey HKLM "${UNINSTKEY}"
  DeleteRegKey HKLM "Software\FCPLiveAnalyzer"
  ; user settings and exports (Documents) are kept
SectionEnd
