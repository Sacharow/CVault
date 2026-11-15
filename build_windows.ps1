$ErrorActionPreference = "Stop"

if (-not (Get-Command flet -ErrorAction SilentlyContinue)) {
    throw "Flet is not installed. Run: py -m pip install -r requirements.txt"
}

flet pack main.py --name CVault --icon assets\icon.ico --add-data assets:assets -y
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& (Join-Path $PSScriptRoot "sign_windows.ps1")
