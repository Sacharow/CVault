@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Brak podanego slowa.
    exit /b 1
)

set "word=%~1"

for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes('%word%'))"`) do set "x=%%A"

echo %x%