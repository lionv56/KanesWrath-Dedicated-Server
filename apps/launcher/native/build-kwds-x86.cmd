@echo off
setlocal

call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86
if errorlevel 1 exit /b 10

rem KWDS_ISOLATED_LAUNCHER_BUILD_V1
rem Keep compiler output outside the repository.

set "OUT_BASE=%USERPROFILE%\KWDS-Build-Staging"

if not exist "%OUT_BASE%" mkdir "%OUT_BASE%"
if errorlevel 1 exit /b 40

set "OUT_DIR=%OUT_BASE%\launcher-%RANDOM%-%RANDOM%"

if exist "%OUT_DIR%" exit /b 41

mkdir "%OUT_DIR%"
if errorlevel 1 exit /b 42

cd /d "%OUT_DIR%"
if errorlevel 1 exit /b 43

echo [INFO] Launcher build directory: %OUT_DIR%

rem Override with the location of the x86 vcpkg installed prefix if needed.
if not defined KWDS_DETOURS_X86 set "KWDS_DETOURS_X86=%USERPROFILE%\OneDrive\Documents\project map\kwds-external-references\kwds-build-lab-v2\vcpkg_installed\x86-windows"
if not exist "%KWDS_DETOURS_X86%\include\detours\detours.h" exit /b 11
if not exist "%KWDS_DETOURS_X86%\lib\detours.lib" exit /b 12

cl /nologo /MD /EHsc /std:c++17 /W4 /DUNICODE /D_UNICODE /Fe:"%OUT_DIR%\kwds-client-launcher.exe" /I"%KWDS_DETOURS_X86%\include\detours" "%~dp0kwds-client-launcher.cpp" /link /SUBSYSTEM:CONSOLE /LIBPATH:"%KWDS_DETOURS_X86%\lib" detours.lib

if errorlevel 1 exit /b 20
if not exist "%OUT_DIR%\kwds-client-launcher.exe" exit /b 21

echo [PASS] X86 launcher compiled.
exit /b 0
