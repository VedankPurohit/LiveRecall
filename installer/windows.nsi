; LiveRecall Windows Installer Script
; Built with NSIS (Nullsoft Scriptable Install System)
; https://nsis.sourceforge.io/
;
; To build: makensis /DVERSION=0.1.2 /DEXE_PATH=dist\LiveRecall.exe /DOUTFILE=dist\LiveRecall-Setup.exe windows.nsi

;--------------------------------
; Includes

!include "MUI2.nsh"
!include "FileFunc.nsh"

;--------------------------------
; General Configuration

!ifndef VERSION
    !define VERSION "0.1.0"
!endif

!ifndef EXE_PATH
    !define EXE_PATH "..\dist\LiveRecall.exe"
!endif

!ifndef OUTFILE
    !define OUTFILE "..\dist\LiveRecall-${VERSION}-Windows-Setup.exe"
!endif

Name "LiveRecall"
OutFile "${OUTFILE}"
InstallDir "$PROGRAMFILES\LiveRecall"
InstallDirRegKey HKLM "Software\LiveRecall" "InstallDir"
RequestExecutionLevel admin

; Version information
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "LiveRecall"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "FileDescription" "LiveRecall Installer"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "LiveRecall"

;--------------------------------
; Interface Settings

!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\icon.ico"
!define MUI_UNICON "..\assets\icon.ico"

; Welcome page settings
!define MUI_WELCOMEPAGE_TITLE "Welcome to LiveRecall Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of LiveRecall.$\r$\n$\r$\nLiveRecall captures your screen periodically and lets you search through your visual history using natural language.$\r$\n$\r$\nClick Next to continue."

; Finish page settings
!define MUI_FINISHPAGE_RUN "$INSTDIR\LiveRecall.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch LiveRecall"
!define MUI_FINISHPAGE_SHOWREADME ""
!define MUI_FINISHPAGE_SHOWREADME_NOTCHECKED

;--------------------------------
; Pages

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Languages

!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Installer Section

Section "Install" SecInstall
    SetOutPath $INSTDIR

    ; Install main executable
    File "${EXE_PATH}"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\LiveRecall"
    CreateShortCut "$SMPROGRAMS\LiveRecall\LiveRecall.lnk" "$INSTDIR\LiveRecall.exe" "" "$INSTDIR\LiveRecall.exe" 0
    CreateShortCut "$SMPROGRAMS\LiveRecall\Uninstall LiveRecall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0

    ; Optional: Create Desktop shortcut
    CreateShortCut "$DESKTOP\LiveRecall.lnk" "$INSTDIR\LiveRecall.exe" "" "$INSTDIR\LiveRecall.exe" 0

    ; Write registry keys for uninstall
    WriteRegStr HKLM "Software\LiveRecall" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\LiveRecall" "Version" "${VERSION}"

    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LiveRecall" "DisplayName" "LiveRecall"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LiveRecall" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LiveRecall" "Publisher" "LiveRecall"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LiveRecall" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LiveRecall" "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LiveRecall" "DisplayIcon" "$\"$INSTDIR\LiveRecall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LiveRecall" "InstallLocation" "$INSTDIR"

    ; Get installed size
    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LiveRecall" "EstimatedSize" "$0"

SectionEnd

;--------------------------------
; Uninstaller Section

Section "Uninstall"
    ; Remove files
    Delete "$INSTDIR\LiveRecall.exe"
    Delete "$INSTDIR\Uninstall.exe"

    ; Remove Start Menu shortcuts
    Delete "$SMPROGRAMS\LiveRecall\LiveRecall.lnk"
    Delete "$SMPROGRAMS\LiveRecall\Uninstall LiveRecall.lnk"
    RMDir "$SMPROGRAMS\LiveRecall"

    ; Remove Desktop shortcut
    Delete "$DESKTOP\LiveRecall.lnk"

    ; Remove installation directory (only if empty)
    RMDir "$INSTDIR"

    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\LiveRecall"
    DeleteRegKey HKLM "Software\LiveRecall"

    ; Remove auto-start entry (if exists)
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "LiveRecall"

SectionEnd

;--------------------------------
; Functions

Function .onInit
    ; Check if already installed
    ReadRegStr $0 HKLM "Software\LiveRecall" "InstallDir"
    StrCmp $0 "" done

    MessageBox MB_OKCANCEL|MB_ICONINFORMATION "LiveRecall is already installed.$\r$\n$\r$\nClick OK to uninstall the previous version, or Cancel to abort." IDOK uninstall
    Abort

uninstall:
    ; Run uninstaller silently
    ExecWait '$0\Uninstall.exe /S _?=$0'
    Delete "$0\Uninstall.exe"
    RMDir "$0"

done:
FunctionEnd
