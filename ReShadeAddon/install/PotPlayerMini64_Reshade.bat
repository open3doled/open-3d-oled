REM @echo off
cd /d "%~dp0"  REM Change to the directory of the batch file
start "" ".\inject64.exe" "PotPlayerMini64.exe"
start "" "PotPlayerMini64.exe"