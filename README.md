# CVault

CVault is a small Flet desktop application.

There are two types of executable files in the dist folder, one for simpler but less secure storage of vault entries, and one for more secure storage.

Addionally, CVault supports both Windows and Linux.

While simpler storage is easier to use, it is less secure. The more secure storage uses a master password to encrypt the vault entries and settings.

## Security of CVault-Secure

CVault protects the settings (including the seed) and vault entries with AES-GCM. A master password is processed with Argon2id; derived keys are kept in memory only while the app is running. Encrypted values remain Base64-encoded for display and copying.

On first launch, create a master password with at least 8 characters. Existing plaintext settings are encrypted during setup. Existing data.json entries remain readable and are encrypted the next time vault data is saved (for example, when adding or deleting an entry). Keep a backup before upgrading. The master password cannot be recovered, so losing it makes the encrypted settings and vault data inaccessible.

If you forget the master password, use Forgot password? Erase vault data on the unlock screen. After confirmation, CVault deletes its local settings and vault files and lets you create a new vault. This is irreversible; backups and copies outside CVault's storage are not affected.

## Important Note

Do not use both CVault and CVault-Secure, the encryption methods are not compatible. Mixing them may cause different password to generate.

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
