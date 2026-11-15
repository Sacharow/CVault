# CVault

CVault is a small Flet desktop application.

> **Security warning:** This checked-in version stores passwords using Base64 with an optional seed. Base64 is reversible and is not encryption. Do not use this build to protect real credentials.

## Install build dependencies

Install Python 3.10 or later, then run from the project directory:

```shell
python -m pip install -r requirements.txt
```

## Build for Windows

Run this in PowerShell on Windows:

```powershell
.\build_windows.ps1
```

The standalone executable is created at `dist\CVault.exe`. The script signs it using a local self-signed development certificate stored in your current Windows user certificate store. To sign an existing build again, run `.\sign_windows.ps1`.

This self-signed certificate is not trusted by other PCs and may not bypass Windows Smart App Control. Do not install it as a trusted root certificate to work around that protection. A trusted publisher identity requires a certificate from a recognized code-signing authority.

Keep the output folder available while building/running. Start the executable from `dist` once before moving it: if `data.json` or `settings.json` exists in the project directory, CVault copies it to the per-user storage location without deleting or overwriting the original.

## Build for Linux

Build on Linux (or inside WSL) rather than trying to cross-compile from Windows:

```shell
chmod +x build_linux.sh
./build_linux.sh
```

The executable is created at `dist/CVault`. Run it from `dist` once before moving it to allow existing project data and settings to be copied to the per-user storage location. Linux builds do not include a desktop icon yet.

## Data locations

Development runs keep `data.json` and `settings.json` in the project folder. Packaged Windows builds store them in `%APPDATA%\CVault`; Linux builds use `$XDG_DATA_HOME/CVault` or `~/.local/share/CVault`. Existing files in the executable directory (or its parent when the executable is in `dist`) are copied only if the corresponding per-user file does not exist.

Windows and Linux builds are platform-specific. Build each target on its native OS; on Windows, WSL can be used to produce the Linux build.
