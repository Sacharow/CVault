import json
import os
import subprocess
import platform
from datetime import datetime
import flet as ft

DATA_FILE = "data.json"

# --- Helper Functions ---
def get_os_type():
    system = platform.system()
    if "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ or "android" in platform.platform().lower():
        return "android"
    if system == "Windows":
        return "windows"
    if system == "Linux":
        return "linux"
    return "other"

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_entry(source: str, password: str):
    """Encrypt the password using the existing cipher scripts and store it in data.json with id and date."""
    os_type = get_os_type()
    if os_type == "windows":
        # cipher.bat expects the plain password as the first argument
        cmd = ["cipher.bat", password]
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    else:
        # Linux / Android uses cipher.sh
        cmd = ["bash", "cipher.sh", password]
        result = subprocess.run(cmd, capture_output=True, text=True)
    encrypted = result.stdout.strip()
    # Load, append, and write back
    data = load_data()
    existing_ids = [item["id"] for item in data if isinstance(item, dict) and isinstance(item.get("id"), int)]
    next_id = (max(existing_ids) + 1) if existing_ids else (len(data) + 1)
    current_date = datetime.now().strftime("%Y-%m-%d")

    data.append({
        "id": next_id,
        "site": source.strip(),
        "encrypted_password": encrypted,
        "date": current_date
    })
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def delete_entry(identifier):
    """Delete an entry by its ID or site name."""
    data = load_data()
    data = [item for item in data if item.get("id") != identifier and item.get("site") != identifier]
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
# --- UI Builders ---
def build_list_view(page: ft.Page):
    items = load_data()
    cards = []
    for item in items:
        date_str = item.get("date") or ""
        if " " in date_str:
            date_str = date_str.split()[0]
        src = item.get("site") or item.get("source") or "Nieznane źródło"
        pwd = item.get("encrypted_password") or item.get("password") or "(brak hasła)"

        card_content = []
        if date_str:
            card_content.append(
                ft.Text(date_str, size=11, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER)
            )

        card_content.extend([
            ft.Text(src, weight=ft.FontWeight.BOLD, size=18,
                    text_align=ft.TextAlign.CENTER),
            ft.Button(
                content=ft.Text(pwd, text_align=ft.TextAlign.CENTER, size=16),
                width=200,
                style=ft.ButtonStyle(padding=0),
                action=ft.CopyToClipboard(pwd),
            ),
        ])

        cards.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        card_content,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=6,
                    ),
                    padding=10,
                ),
                width=230,
                elevation=4,
                margin=ft.Margin(5, 5, 5, 5),
            )
        )
    return ft.GridView(
        expand=True,
        max_extent=250,
        spacing=10,
        controls=cards if cards else [ft.Text("Brak wpisów w data.json")],
    )

def build_add_view(page: ft.Page):
    src_field = ft.TextField(label="Source", hint_text="np. example.com")
    pwd_field = ft.TextField(label="Hasło", hint_text="Wpisz hasło")
    status = ft.Text("", color="green")
    def on_save(e):
        src = src_field.value.strip()
        pwd = pwd_field.value.strip()
        if not src or not pwd:
            status.value = "Proszę podać oba pola."
            status.color = "red"
            page.update()
            return
        save_entry(src, pwd)
        status.value = "Zapisano!"
        status.color = "green"
        src_field.value = ""
        pwd_field.value = ""
        page.update()
    save_btn = ft.Button(content=ft.Text("Zapisz"), on_click=on_save)
    return ft.Column([
        ft.Text("Dodaj nowy wpis", size=20, weight=ft.FontWeight.BOLD),
        src_field,
        pwd_field,
        save_btn,
        status,
    ], spacing=10, width=300)

# --- Main Application ---
def main(page: ft.Page):
    page.title = "CVault"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.icon = "icon.ico"
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Container that will host either list or add view
    container = ft.Column()

    def show_list(e):
        container.controls = [build_list_view(page)]
        page.update()

    def show_add(e):
        container.controls = [build_add_view(page)]
        page.update()

    # Navigation bar
    nav = ft.Row([
    ft.Button(content=ft.Text("Lista"), on_click=show_list),
    ft.Button(content=ft.Text("Dodaj"), on_click=show_add),
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

    # Initial view
    container.controls = [build_list_view(page)]

    page.add(nav, ft.Divider(), container)

ft.run(main, assets_dir="assets")
