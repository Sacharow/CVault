import os
import platform
import subprocess
import json

def get_os_type():
    system = platform.system()
    
    # Sprawdzanie czy to Android (Android bazuje na Linuksie)
    if "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ or "android" in platform.platform().lower():
        return "android"
    elif system == "Windows":
        return "windows"
    elif system == "Linux":
        return "linux"
    else:
        return "other"

os_type = get_os_type()
print(f"Wykryty system: {os_type}")

word_to_cipher = "example_word"

# Wybór odpowiedniego skryptu zależnie od systemu
if os_type == "windows":
    # Na Windowsie uruchamiamy cipher.bat przez cmd.exe
    cmd = ["cipher.bat", word_to_cipher]
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
else:
    # Na Linuxie i Androidzie (np. w Termux) uruchamiamy cipher.sh przez bash
    cmd = ["bash", "cipher.sh", word_to_cipher]
    result = subprocess.run(cmd, capture_output=True, text=True)

output = result.stdout
print(output)

# Zapis do pliku
data = {
    "detected_os": os_type,
    "last_run": output.strip()
}
with open("data.json", "w") as f:
    json.dump(data, f, indent=4)