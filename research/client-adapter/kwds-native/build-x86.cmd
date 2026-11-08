@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86
if errorlevel 1 exit /b 10

rem KWDS_ISOLATED_X86_BUILD_V1
rem Build in a new directory outside OneDrive.
rem Existing repository binaries are never overwritten.
set "OUT_BASE=%USERPROFILE%\KWDS-Build-Staging"

if not exist "%OUT_BASE%" mkdir "%OUT_BASE%"
if errorlevel 1 exit /b 40

set "OUT_DIR=%OUT_BASE%\issue4-%RANDOM%-%RANDOM%"

if exist "%OUT_DIR%" exit /b 41

mkdir "%OUT_DIR%"
if errorlevel 1 exit /b 42

cd /d "%OUT_DIR%"
if errorlevel 1 exit /b 43

echo [INFO] Isolated build output: %OUT_DIR%

rem Override with the location of the x86 vcpkg installed prefix if needed.
if not defined KWDS_DETOURS_X86 set "KWDS_DETOURS_X86=%USERPROFILE%\OneDrive\Documents\project map\kwds-external-references\kwds-build-lab-v2\vcpkg_installed\x86-windows"
if not exist "%KWDS_DETOURS_X86%\include\detours\detours.h" exit /b 11
if not exist "%KWDS_DETOURS_X86%\lib\detours.lib" exit /b 12

cl /nologo /LD /MD /EHsc /std:c++17 /W4 /I"%KWDS_DETOURS_X86%\include\detours" "%~dp0kwds-adapter-router-v2.cpp" /link /OUT:"%OUT_DIR%\kwds-adapter.dll" /IMPLIB:"%OUT_DIR%\kwds-adapter.lib" /PDB:"%OUT_DIR%\kwds-adapter.pdb" /DEF:"%~dp0kwds-adapter.def" /LIBPATH:"%KWDS_DETOURS_X86%\lib" detours.lib ws2_32.lib Psapi.lib

if errorlevel 1 exit /b 20

echo.
echo === REQUIRED DETOURS EXPORT ===
dumpbin /nologo /exports "%OUT_DIR%\kwds-adapter.dll"
if errorlevel 1 exit /b 30

echo.
echo [PASS] KWDS native adapter build completed.
exit /b 0
