import base64
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import main
from vault_crypto import decrypt_text, derive_keys


class FakePage:
    def __init__(self):
        from types import SimpleNamespace

        self.window = SimpleNamespace()
        self.controls = []
        self.overlay = []

    def add(self, *controls):
        self.controls.extend(controls)

    def clean(self):
        self.controls.clear()

    def update(self):
        pass


class VaultEncryptionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings_path = main.SETTINGS_FILE
        self.data_path = main.DATA_FILE
        self.vault_context = main._VAULT_CONTEXT
        main._VAULT_CONTEXT = None
        main.SETTINGS_FILE = os.path.join(self.directory.name, "settings.json")
        main.DATA_FILE = os.path.join(self.directory.name, "data.json")

    def tearDown(self):
        main.SETTINGS_FILE = self.settings_path
        main.DATA_FILE = self.data_path
        main._VAULT_CONTEXT = self.vault_context
        self.directory.cleanup()

    def test_correct_password_opens_the_vault_ui(self):
        with (
            patch.object(main, "is_settings_encrypted", return_value=True),
            patch.object(
                main,
                "load_settings",
                return_value=(main.DEFAULT_SETTINGS.copy(), b"s" * 16, b"k" * 32, b"d" * 32),
            ),
            patch.object(main, "load_data", return_value=[]),
        ):
            page = FakePage()
            main.main(page)
            icon_path = os.path.join(os.path.dirname(main.__file__), "assets", "icon.ico")
            self.assertEqual(page.window.icon, icon_path)
            lock_controls = page.controls[0].content.controls
            lock_controls[2].value = "correct horse battery"
            lock_controls[4].on_click(None)

        self.assertIsNotNone(main._VAULT_CONTEXT)
        self.assertEqual(len(page.controls), 4)
        self.assertEqual(page.window.icon, icon_path)

    def test_forgot_password_reset_erases_local_files_and_returns_to_setup(self):
        with open(main.SETTINGS_FILE, "w", encoding="utf-8") as file:
            json.dump({"format": main.SETTINGS_FORMAT}, file)
        with open(main.DATA_FILE, "w", encoding="utf-8") as file:
            json.dump({"format": main.DATA_FORMAT, "entries": ["encrypted"]}, file)

        page = FakePage()
        main.main(page)
        page.controls[0].content.controls[5].on_click(None)
        confirmation = page.overlay[0]
        confirmation.actions[1].on_click(None)

        self.assertFalse(os.path.exists(main.SETTINGS_FILE))
        self.assertFalse(os.path.exists(main.DATA_FILE))
        self.assertEqual(page.controls[0].content.controls[0].value, "Create master password")
        self.assertIsNone(main._VAULT_CONTEXT)

    def test_settings_are_encrypted_and_require_the_master_password(self):
        settings = {"language": "pl", "theme": "light", "seed": "private-seed"}
        salt, settings_key, _ = derive_keys("correct horse battery staple")
        main.save_settings(settings, salt, settings_key)

        with open(main.SETTINGS_FILE, "r", encoding="utf-8") as file:
            envelope = json.load(file)
        self.assertEqual(envelope["format"], main.SETTINGS_FORMAT)
        self.assertNotIn("private-seed", json.dumps(envelope))
        self.assertEqual(
            main.load_settings("correct horse battery staple")[0],
            settings,
        )
        with self.assertRaisesRegex(ValueError, "Incorrect master password"):
            main.load_settings("a different master password")

    def test_data_save_migrates_legacy_entries_and_encrypts_records(self):
        old_password = base64.b64encode(b"seedsecretseed").decode("ascii")
        with open(main.DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(
                [{"id": 1, "site": "private.example", "encrypted_password": old_password}],
                file,
            )
        _, _, data_key = derive_keys("correct horse battery staple")

        main.save_data(main.load_data(data_key), data_key, seed="seed")

        with open(main.DATA_FILE, "r", encoding="utf-8") as file:
            envelope = json.load(file)
        self.assertEqual(envelope["format"], main.DATA_FORMAT)
        self.assertNotIn("private.example", json.dumps(envelope))
        migrated_entry = main.load_data(data_key)[0]
        self.assertEqual(migrated_entry["password_format"], 1)
        self.assertEqual(
            decrypt_text(migrated_entry["encrypted_password"], data_key),
            "seedsecretseed",
        )

    def test_new_password_ciphertext_remains_base64(self):
        _, _, data_key = derive_keys("correct horse battery staple")

        main.save_entry("example.test", "secret", "seed", data_key)

        entry = main.load_data(data_key)[0]
        encoded_password = entry["encrypted_password"]
        self.assertTrue(base64.b64decode(encoded_password, validate=True))
        self.assertEqual(decrypt_text(encoded_password, data_key), "seedsecretseed")

    def test_modified_encrypted_entry_is_rejected(self):
        _, _, data_key = derive_keys("correct horse battery staple")
        main.save_data(
            [{"id": 1, "site": "private.example", "encrypted_password": "value", "password_format": 1}],
            data_key,
        )
        with open(main.DATA_FILE, "r", encoding="utf-8") as file:
            envelope = json.load(file)
        encrypted = bytearray(base64.b64decode(envelope["entries"][0]))
        encrypted[-1] ^= 1
        envelope["entries"][0] = base64.b64encode(encrypted).decode("ascii")
        with open(main.DATA_FILE, "w", encoding="utf-8") as file:
            json.dump(envelope, file)

        with self.assertRaisesRegex(ValueError, "Incorrect master password"):
            main.load_data(data_key)


if __name__ == "__main__":
    unittest.main()
