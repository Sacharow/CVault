import base64
import json
import ntpath
import os
import posixpath
import shutil
import sys
from datetime import datetime
import flet as ft

def get_storage_directory(is_frozen=None, platform=None, environ=None, home=None):
    is_frozen = getattr(sys, "frozen", False) if is_frozen is None else is_frozen
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = os.path.expanduser("~") if home is None else home

    if not is_frozen:
        return os.path.dirname(os.path.abspath(__file__))
    path_module = ntpath if platform == "win32" else posixpath if platform.startswith("linux") else os.path
    if platform == "win32":
        base_directory = environ.get("APPDATA") or path_module.join(home, "AppData", "Roaming")
    else:
        base_directory = environ.get("XDG_DATA_HOME") or path_module.join(home, ".local", "share")
    return path_module.join(base_directory, "CVault")


def migrate_packaged_storage(data_directory, executable_path=None, is_frozen=None):
    is_frozen = getattr(sys, "frozen", False) if is_frozen is None else is_frozen
    if not is_frozen:
        return

    executable_path = sys.executable if executable_path is None else executable_path
    executable_directory = os.path.dirname(os.path.abspath(executable_path))
    legacy_directories = [executable_directory]
    parent_directory = os.path.dirname(executable_directory)
    if os.path.basename(executable_directory).lower() == "dist":
        legacy_directories.append(os.path.dirname(executable_directory))
    elif os.path.basename(parent_directory).lower() == "dist":
        legacy_directories.extend([parent_directory, os.path.dirname(parent_directory)])

    os.makedirs(data_directory, exist_ok=True)
    for filename in ("data.json", "settings.json"):
        destination = os.path.join(data_directory, filename)
        if os.path.exists(destination):
            continue
        for legacy_directory in legacy_directories:
            source = os.path.join(legacy_directory, filename)
            if (
                os.path.isfile(source)
                and os.path.normcase(os.path.abspath(source)) != os.path.normcase(os.path.abspath(destination))
            ):
                shutil.copy2(source, destination)
                break


DATA_DIRECTORY = get_storage_directory()
os.makedirs(DATA_DIRECTORY, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIRECTORY, "data.json")
SETTINGS_FILE = os.path.join(DATA_DIRECTORY, "settings.json")
if getattr(sys, "frozen", False):
    migrate_packaged_storage(DATA_DIRECTORY)
DEFAULT_SETTINGS = {"language": "en", "theme": "dark", "seed": ""}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        settings = DEFAULT_SETTINGS.copy()
        save_settings(settings)
        return settings

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        stored_settings = json.load(f)
    if not isinstance(stored_settings, dict):
        raise ValueError(f"{SETTINGS_FILE} must contain a JSON object")

    settings = {
        key: stored_settings.get(key, default)
        for key, default in DEFAULT_SETTINGS.items()
    }
    if settings["language"] not in ("en", "pl"):
        settings["language"] = DEFAULT_SETTINGS["language"]
    if settings["theme"] not in ("dark", "light"):
        settings["theme"] = DEFAULT_SETTINGS["theme"]
    if not isinstance(settings["seed"], str):
        settings["seed"] = DEFAULT_SETTINGS["seed"]
    if settings != stored_settings:
        save_settings(settings)
    return settings

def get_theme_colors(settings):
    is_dark = settings["theme"] == "dark"
    return {
        "page": "#0B0F19" if is_dark else "#F1F5F9",
        "panel": "#1E293B" if is_dark else "#FFFFFF",
        "field": "#0F172A" if is_dark else "#F8FAFC",
        "border": "#334155" if is_dark else "#CBD5E1",
        "text": "white" if is_dark else "#0F172A",
        "muted": "#94A3B8" if is_dark else "#475569",
        "subtle": "#475569" if is_dark else "#94A3B8",
        "strong": "#E2E8F0" if is_dark else "#1E293B",
    }

def translate(settings, english, polish):
    return polish if settings["language"] == "pl" else english

# --- Helper Functions ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def open_dialog(page: ft.Page, dialog: ft.AlertDialog):
    open_fn = getattr(page, "open", None)
    if callable(open_fn):
        open_fn(dialog)
    else:
        if dialog not in page.overlay:
            page.overlay.append(dialog)
        dialog.open = True
        page.update()

def close_dialog(page: ft.Page, dialog: ft.AlertDialog):
    close_fn = getattr(page, "close", None)
    if callable(close_fn):
        close_fn(dialog)
    else:
        dialog.open = False
        page.update()

def save_entry(source: str, password: str, seed: str = ""):
    """Encode the password, wrapped with the configured seed, and store it in data.json."""
    fused_password = f"{seed}{password}{seed}"
    encrypted = base64.b64encode(fused_password.encode("utf-8")).decode("ascii")
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

def delete_entry(identifier=None, target_id=None, site=None):
    """Delete an entry by its ID or site name."""
    data = load_data()
    t_id = target_id if target_id is not None else (identifier if isinstance(identifier, int) else None)
    t_site = site if site is not None else (identifier if isinstance(identifier, str) else None)

    if t_id is not None:
        data = [item for item in data if item.get("id") != t_id]
    elif t_site is not None:
        data = [item for item in data if item.get("site") != t_site]

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- UI Builders ---
def build_list_view(page: ft.Page, on_refresh=None, settings=None):
    settings = settings or DEFAULT_SETTINGS
    colors = get_theme_colors(settings)
    items = load_data()

    def make_delete_handler(target_id, target_site):
        def show_confirm_dialog(e):
            def on_confirm(ce):
                close_dialog(page, dialog)
                delete_entry(target_id=target_id, site=target_site)
                if on_refresh:
                    on_refresh()
                else:
                    refresh_data()

            def on_cancel(ce):
                close_dialog(page, dialog)

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    [
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#EF4444", size=24),
                        ft.Text(translate(settings, "Confirm deletion", "Potwierdź usunięcie"), size=18, weight=ft.FontWeight.BOLD),
                    ],
                    spacing=8,
                ),
                content=ft.Text(
                    translate(
                        settings,
                        f"Are you sure you want to delete the entry for '{target_site}'? This cannot be undone.",
                        f"Czy na pewno chcesz usunąć wpis dla '{target_site}'? Ta operacja jest nieodwracalna.",
                    ),
                    size=14,
                    color=colors["strong"],
                ),
                actions=[
                    ft.Column(
                        [
                            ft.Button(
                                content=ft.Row(
                                    [
                                        ft.Icon(ft.Icons.DELETE_OUTLINE_ROUNDED, size=16, color="white"),
                                        ft.Text(translate(settings, "Delete entry", "Usuń wpis"), color="white", weight=ft.FontWeight.BOLD),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    spacing=6,
                                ),
                                style=ft.ButtonStyle(
                                    bgcolor="#DC2626",
                                    padding=ft.Padding(16, 12, 16, 12),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                width=260,
                                on_click=on_confirm,
                            ),
                            ft.Button(
                                content=ft.Row(
                                    [
                                        ft.Text(translate(settings, "Cancel", "Anuluj"), color=colors["muted"]),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                                style=ft.ButtonStyle(
                                    bgcolor=colors["panel"],
                                    padding=ft.Padding(16, 12, 16, 12),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                width=260,
                                on_click=on_cancel,
                            ),
                        ],
                        spacing=10,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.CENTER,
                shape=ft.RoundedRectangleBorder(radius=14),
                bgcolor=colors["field"],
            )
            open_dialog(page, dialog)

        return show_confirm_dialog

    def render_card(item):
        item_id = item.get("id")
        date_str = item.get("date") or ""
        if " " in date_str:
            date_str = date_str.split()[0]
        src = item.get("site") or item.get("source") or translate(settings, "Unknown source", "Nieznane źródło")
        pwd = item.get("encrypted_password") or item.get("password") or translate(settings, "(no password)", "(brak hasła)")
        initial = src[0].upper() if src else "?"

        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        src,
                                        size=15,
                                        weight=ft.FontWeight.BOLD,
                                        color=colors["text"],
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Row(
                                        [
                                            ft.Icon(ft.Icons.CALENDAR_TODAY, size=10, color="#64748B"),
                                            ft.Text(date_str, size=11, color=colors["muted"]),
                                        ],
                                        spacing=4,
                                    ) if date_str else ft.Container(),
                                ],
                                spacing=2,
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                                icon_color="#EF4444",
                                icon_size=18,
                                tooltip=translate(settings, "Delete entry", "Usuń wpis"),
                                on_click=make_delete_handler(item_id, src),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=1, color=colors["border"]),
                    ft.Container(
                        content=ft.Button(
                            content=ft.Row(
                                [
                                    ft.Icon(ft.Icons.KEY_ROUNDED, size=16, color="#818CF8"),
                                    ft.Text(
                                        pwd,
                                        size=16,
                                        color=colors["strong"],
                                        font_family="monospace",
                                        weight=ft.FontWeight.W_500,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        expand=True,
                                    ),
                                    ft.Icon(ft.Icons.COPY_ROUNDED, size=16, color=colors["muted"]),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            style=ft.ButtonStyle(
                                bgcolor=colors["field"],
                                padding=ft.Padding(12, 40, 12, 40),
                                shape=ft.RoundedRectangleBorder(radius=8),
                            ),
                            action=ft.CopyToClipboard(pwd),
                            tooltip=translate(settings, "Copy encrypted password", "Kopiuj zaszyfrowane hasło"),
                        ),
                        border=ft.Border(
                            top=ft.BorderSide(1, colors["border"]),
                            bottom=ft.BorderSide(1, colors["border"]),
                            left=ft.BorderSide(1, colors["border"]),
                            right=ft.BorderSide(1, colors["border"]),
                        ),
                        border_radius=8,
                    ),
                ],
                spacing=10,
            ),
            bgcolor=colors["panel"],
            padding=14,
            border_radius=12,
            border=ft.Border(
                top=ft.BorderSide(1, colors["border"]),
                bottom=ft.BorderSide(1, colors["border"]),
                left=ft.BorderSide(1, colors["border"]),
                right=ft.BorderSide(1, colors["border"]),
            ),
            width=220,
        )

    grid = ft.GridView(
        expand=True,
        max_extent=200,
        spacing=12,
        run_spacing=12,
    )

    count_badge = ft.Text("", size=12, color=colors["muted"], weight=ft.FontWeight.W_500)

    def get_filtered_and_sorted_items():
        query = (search_field.value or "").strip().lower()
        filtered = []
        for it in items:
            s = (it.get("site") or it.get("source") or "").lower()
            d = (it.get("date") or "").lower()
            if not query or query in s or query in d:
                filtered.append(it)

        sort_mode = sort_dropdown.value
        if sort_mode == "source_asc":
            filtered.sort(key=lambda x: (x.get("site") or x.get("source") or "").lower())
        elif sort_mode == "source_desc":
            filtered.sort(key=lambda x: (x.get("site") or x.get("source") or "").lower(), reverse=True)
        elif sort_mode == "date_desc":
            filtered.sort(key=lambda x: x.get("date") or "", reverse=True)
        elif sort_mode == "date_asc":
            filtered.sort(key=lambda x: x.get("date") or "")
        return filtered

    def update_view(e=None):
        filtered = get_filtered_and_sorted_items()
        count_badge.value = translate(
            settings,
            f"Found: {len(filtered)} of {len(items)}",
            f"Znaleziono: {len(filtered)} z {len(items)}",
        )
        if not filtered:
            msg = translate(settings, "No entries in the database", "Brak wpisów w bazie danych") if not items else translate(
                settings,
                "No search results found",
                "Brak wyników pasujących do wyszukiwania",
            )
            icon = ft.Icons.LOCK_OPEN_ROUNDED if not items else ft.Icons.SEARCH_OFF_ROUNDED
            grid.controls = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(icon, size=44, color=colors["subtle"]),
                            ft.Text(msg, size=15, color=colors["muted"], weight=ft.FontWeight.W_500),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    padding=40,
                    alignment=ft.Alignment(0, 0),
                )
            ]
        else:
            grid.controls = [render_card(it) for it in filtered]
        page.update()

    def refresh_data():
        nonlocal items
        items = load_data()
        update_view()

    search_field = ft.TextField(
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        hint_text=translate(settings, "Search sites or dates...", "Szukaj strony lub daty..."),
        expand=True,
        dense=True,
        border_radius=10,
        bgcolor=colors["panel"],
        border_color=colors["border"],
        focused_border_color="#6366F1",
        on_change=update_view,
    )

    sort_dropdown = ft.Dropdown(
        options=[
            ft.dropdown.Option(key="source_asc", text=translate(settings, "Source (A-Z)", "Źródło (A-Z)")),
            ft.dropdown.Option(key="source_desc", text=translate(settings, "Source (Z-A)", "Źródło (Z-A)")),
            ft.dropdown.Option(key="date_desc", text=translate(settings, "Date (Newest)", "Data (Najnowsze)")),
            ft.dropdown.Option(key="date_asc", text=translate(settings, "Date (Oldest)", "Data (Najstarsze)")),
        ],
        value="source_asc",
        width=200,
        dense=True,
        border_radius=10,
        bgcolor=colors["panel"],
        border_color=colors["border"],
        focused_border_color="#6366F1",
        on_select=update_view,
    )
    setattr(sort_dropdown, "on_change", update_view)

    controls_bar = ft.Row(
        [
            search_field,
            sort_dropdown,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=10,
    )

    top_section = ft.Column(
        [
            controls_bar,
            ft.Row([count_badge], alignment=ft.MainAxisAlignment.END),
        ],
        spacing=6,
    )

    update_view()

    return ft.Column(
        [
            top_section,
            grid,
        ],
        expand=True,
        spacing=8,
    )

def build_add_view(page: ft.Page, settings=None):
    settings = settings or DEFAULT_SETTINGS
    colors = get_theme_colors(settings or DEFAULT_SETTINGS)
    src_field = ft.TextField(
        label=translate(settings, "Website / Service", "Strona / Serwis"),
        hint_text=translate(settings, "e.g. example.com", "np. example.com"),
        prefix_icon=ft.Icons.LANGUAGE_ROUNDED,
        border_radius=10,
        bgcolor=colors["field"],
        border_color=colors["border"],
        focused_border_color="#6366F1",
    )
    pwd_field = ft.TextField(
        label=translate(settings, "Password", "Hasło"),
        hint_text=translate(settings, "Enter a password to encrypt", "Wpisz hasło do zaszyfrowania"),
        prefix_icon=ft.Icons.LOCK_ROUNDED,
        border_radius=10,
        bgcolor=colors["field"],
        border_color=colors["border"],
        focused_border_color="#6366F1",
    )
    status = ft.Text("", size=13, text_align=ft.TextAlign.CENTER)

    def on_save(e):
        src = src_field.value.strip()
        pwd = pwd_field.value.strip()
        if not src or not pwd:
            status.value = translate(settings, "⚠️ Please fill in both fields.", "⚠️ Proszę podać oba pola.")
            status.color = "#EF4444"
            page.update()
            return
        save_entry(src, pwd, settings["seed"])
        status.value = translate(settings, "✓ Saved successfully!", "✓ Zapisano pomyślnie!")
        status.color = "#10B981"
        src_field.value = ""
        pwd_field.value = ""
        page.update()

    save_btn = ft.Button(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.LOCK_OUTLINE_ROUNDED, color="white", size=18),
                ft.Text(translate(settings, "Encrypt and Save", "Zaszyfruj i Zapisz"), color="white", size=15, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        ),
        style=ft.ButtonStyle(
            bgcolor="#4F46E5",
            padding=ft.Padding(18, 14, 18, 14),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
        width=340,
        on_click=on_save,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.LOCK_RESET_ROUNDED, color="#818CF8", size=32),
                    bgcolor="#312E81",
                    padding=14,
                    border_radius=25,
                ),
                ft.Text(
                    translate(settings, "Add a new entry", "Dodaj nowy wpis"),
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=colors["text"],
                ),
                ft.Text(
                    translate(
                        settings,
                        "Your password will be encrypted and secured in CVault",
                        "Hasło zostanie automatycznie zaszyfrowane i zabezpieczone w CVault",
                    ),
                    size=12,
                    color=colors["muted"],
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Divider(height=10, color=colors["border"]),
                src_field,
                pwd_field,
                save_btn,
                status,
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=340,
        ),
        bgcolor=colors["panel"],
        padding=28,
        border_radius=16,
        border=ft.Border(
            top=ft.BorderSide(1, colors["border"]),
            bottom=ft.BorderSide(1, colors["border"]),
            left=ft.BorderSide(1, colors["border"]),
            right=ft.BorderSide(1, colors["border"]),
        ),
        alignment=ft.Alignment(0, 0),
        margin=ft.Margin(0, 20, 0, 0),
    )

def build_settings_view(page: ft.Page, settings, on_change):
    colors = get_theme_colors(settings)

    language_dropdown = ft.Dropdown(
        label=translate(settings, "Language", "Język"),
        options=[
            ft.dropdown.Option(key="en", text="English"),
            ft.dropdown.Option(key="pl", text="Polski"),
        ],
        value=settings["language"],
        border_radius=10,
        bgcolor=colors["field"],
        border_color=colors["border"],
        focused_border_color="#6366F1",
        on_select=lambda e: on_change("language", e.control.value),
    )
    theme_dropdown = ft.Dropdown(
        label=translate(settings, "Theme", "Motyw"),
        options=[
            ft.dropdown.Option(key="dark", text="Dark"),
            ft.dropdown.Option(key="light", text="Light"),
        ],
        value=settings["theme"],
        border_radius=10,
        bgcolor=colors["field"],
        border_color=colors["border"],
        focused_border_color="#6366F1",
        on_select=lambda e: on_change("theme", e.control.value),
    )
    seed_field = ft.TextField(
        label="Seed",
        hint_text=translate(settings, "Optional", "Opcjonalnie"),
        value=settings["seed"],
        prefix_icon=ft.Icons.KEY_ROUNDED,
        border_radius=10,
        bgcolor=colors["field"],
        border_color=colors["border"],
        focused_border_color="#6366F1",
        on_change=lambda e: on_change("seed", e.control.value),
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Icon(ft.Icons.SETTINGS_ROUNDED, color="#818CF8", size=32),
                    bgcolor="#312E81",
                    padding=14,
                    border_radius=25,
                ),
                ft.Text(
                    translate(settings, "Settings", "Ustawienia"),
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=colors["text"],
                ),
                ft.Text(
                    translate(settings, "Customize your app preferences", "Dostosuj preferencje aplikacji"),
                    size=12,
                    color=colors["muted"],
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Divider(height=10, color=colors["border"]),
                language_dropdown,
                theme_dropdown,
                seed_field,
                ft.Text(
                    translate(
                        settings,
                        "Changing this seed changes the password output. Use the same seed on every device for matching results. This does not add cryptographic security.",
                        "Zmiana ziarna zmienia wynik hasła. Aby uzyskać taki sam wynik na każdym urządzeniu, ustaw na nich to samo ziarno. Nie zwiększa to bezpieczeństwa kryptograficznego.",
                    ),
                    size=11,
                    color=colors["muted"],
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=340,
        ),
        bgcolor=colors["panel"],
        padding=28,
        border_radius=16,
        border=ft.Border(
            top=ft.BorderSide(1, colors["border"]),
            bottom=ft.BorderSide(1, colors["border"]),
            left=ft.BorderSide(1, colors["border"]),
            right=ft.BorderSide(1, colors["border"]),
        ),
        alignment=ft.Alignment(0, 0),
        margin=ft.Margin(0, 20, 0, 0),
    )

# --- Main Application ---
def main(page: ft.Page):
    settings = load_settings()
    colors = get_theme_colors(settings)
    page.title = "CVault"
    page.theme_mode = ft.ThemeMode.LIGHT if settings["theme"] == "light" else ft.ThemeMode.DARK
    page.bgcolor = colors["page"]
    page.padding = 24
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
    if os.path.exists(icon_path):
        page.window.icon = icon_path

    page.window.width = 880
    page.window.height = 720
    page.window.min_width = 520
    page.window.min_height = 550

    active_tab = "list"
    container = ft.Column(expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    nav_container = ft.Container()
    header_title = ft.Text("CVault", size=22, weight=ft.FontWeight.BOLD, color=colors["text"])
    header_subtitle = ft.Text(
        translate(
            settings,
            "Local, encrypted vault for your credentials",
            "Lokalny, szyfrowany sejf na Twoje poświadczenia",
        ),
        size=12,
        color=colors["muted"],
    )
    header_divider = ft.Divider(height=1, color=colors["border"])

    def update_setting(key, value):
        nonlocal colors
        if key == "seed":
            value = value or ""
        settings[key] = value
        save_settings(settings)
        if key in ("theme", "language"):
            colors = get_theme_colors(settings)
            if key == "theme":
                page.theme_mode = ft.ThemeMode.LIGHT if value == "light" else ft.ThemeMode.DARK
                page.bgcolor = colors["page"]
            header_title.color = colors["text"]
            header_subtitle.value = translate(
                settings,
                "Local, encrypted vault for your credentials",
                "Lokalny, szyfrowany sejf na Twoje poświadczenia",
            )
            header_subtitle.color = colors["muted"]
            header_divider.color = colors["border"]
            update_navigation()
            if active_tab == "settings":
                container.controls = [build_settings_view(page, settings, update_setting)]
            elif active_tab == "list":
                container.controls = [build_list_view(page, on_refresh=show_list, settings=settings)]
            else:
                container.controls = [build_add_view(page, settings=settings)]
            page.update()

    def update_navigation():
        nav_container.content = ft.Row(
            [
                ft.Button(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.VIEW_QUILT_ROUNDED, size=16, color="white" if active_tab == "list" else colors["muted"]),
                            ft.Text(
                                translate(settings, "Password Vault", "Katalog haseł"),
                                color="white" if active_tab == "list" else colors["muted"],
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=8,
                    ),
                    style=ft.ButtonStyle(
                        bgcolor="#4F46E5" if active_tab == "list" else colors["panel"],
                        padding=ft.Padding(16, 10, 16, 10),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=show_list,
                ),
                ft.Button(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED, size=16, color="white" if active_tab == "add" else colors["muted"]),
                            ft.Text(
                                translate(settings, "Add Entry", "Dodaj wpis"),
                                color="white" if active_tab == "add" else colors["muted"],
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=8,
                    ),
                    style=ft.ButtonStyle(
                        bgcolor="#4F46E5" if active_tab == "add" else colors["panel"],
                        padding=ft.Padding(16, 10, 16, 10),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=show_add,
                ),
                ft.Button(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SETTINGS_ROUNDED, size=16, color="white" if active_tab == "settings" else colors["muted"]),
                            ft.Text(
                                translate(settings, "Settings", "Ustawienia"),
                                color="white" if active_tab == "settings" else colors["muted"],
                                weight=ft.FontWeight.W_600,
                            ),
                        ],
                        spacing=8,
                    ),
                    style=ft.ButtonStyle(
                        bgcolor="#4F46E5" if active_tab == "settings" else colors["panel"],
                        padding=ft.Padding(16, 10, 16, 10),
                        shape=ft.RoundedRectangleBorder(radius=8),
                    ),
                    on_click=show_settings,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10,
        )

    def show_list(e=None):
        nonlocal active_tab
        active_tab = "list"
        update_navigation()
        container.controls = [build_list_view(page, on_refresh=show_list, settings=settings)]
        page.update()

    def show_add(e=None):
        nonlocal active_tab
        active_tab = "add"
        update_navigation()
        container.controls = [build_add_view(page, settings=settings)]
        page.update()

    def show_settings(e=None):
        nonlocal active_tab
        active_tab = "settings"
        update_navigation()
        container.controls = [build_settings_view(page, settings, update_setting)]
        page.update()

    header = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.Icons.SHIELD_ROUNDED, color="#818CF8", size=26),
                            bgcolor="#312E81",
                            padding=10,
                            border_radius=12,
                        ),
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        header_title,
                                        ft.Container(
                                            content=ft.Text("v1.4", size=10, color="#818CF8", weight=ft.FontWeight.BOLD),
                                            bgcolor="#1E1B4B",
                                            padding=ft.Padding(6, 2, 6, 2),
                                            border_radius=6,
                                        ),
                                    ],
                                    spacing=8,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                header_subtitle,
                            ],
                            spacing=2,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                nav_container,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding(4, 0, 4, 12),
    )

    update_navigation()
    container.controls = [build_list_view(page, on_refresh=show_list, settings=settings)]

    page.add(
        header,
        header_divider,
        ft.Container(height=8),
        container,
    )

if __name__ == "__main__":
    ft.run(main, assets_dir=os.path.join(os.path.dirname(__file__), "assets"))
