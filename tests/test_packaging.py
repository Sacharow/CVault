import json
import os
import tempfile
import unittest

import main


class PackagingStorageTests(unittest.TestCase):
    def test_windows_uses_roaming_app_data(self):
        storage_directory = main.get_storage_directory(
            is_frozen=True,
            platform="win32",
            environ={"APPDATA": r"C:\Users\Tester\AppData\Roaming"},
            home=r"C:\Users\Tester",
        )
        self.assertEqual(
            storage_directory,
            os.path.join(r"C:\Users\Tester\AppData\Roaming", "CVault"),
        )

    def test_linux_respects_xdg_data_home(self):
        storage_directory = main.get_storage_directory(
            is_frozen=True,
            platform="linux",
            environ={"XDG_DATA_HOME": "/home/tester/.local/share"},
            home="/home/tester",
        )
        self.assertEqual(storage_directory, "/home/tester/.local/share/CVault")

    def test_linux_defaults_to_local_share(self):
        storage_directory = main.get_storage_directory(
            is_frozen=True,
            platform="linux",
            environ={},
            home="/home/tester",
        )
        self.assertEqual(storage_directory, "/home/tester/.local/share/CVault")

    def test_packaged_build_copies_legacy_files_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            project_directory = os.path.join(directory, "project")
            dist_directory = os.path.join(project_directory, "dist")
            storage_directory = os.path.join(directory, "user-data", "CVault")
            os.makedirs(dist_directory)
            legacy_data = [{"site": "example.test", "password": "sample"}]
            with open(os.path.join(project_directory, "data.json"), "w", encoding="utf-8") as file:
                json.dump(legacy_data, file)
            with open(os.path.join(project_directory, "settings.json"), "w", encoding="utf-8") as file:
                json.dump({"theme": "dark"}, file)

            main.migrate_packaged_storage(
                storage_directory,
                executable_path=os.path.join(dist_directory, "CVault.exe"),
                is_frozen=True,
            )

            migrated_data_path = os.path.join(storage_directory, "data.json")
            migrated_settings_path = os.path.join(storage_directory, "settings.json")
            with open(migrated_data_path, "r", encoding="utf-8") as file:
                self.assertEqual(json.load(file), legacy_data)
            with open(migrated_settings_path, "r", encoding="utf-8") as file:
                self.assertEqual(json.load(file), {"theme": "dark"})
            self.assertTrue(os.path.exists(os.path.join(project_directory, "data.json")))

            with open(migrated_data_path, "w", encoding="utf-8") as file:
                json.dump([], file)
            main.migrate_packaged_storage(
                storage_directory,
                executable_path=os.path.join(dist_directory, "CVault.exe"),
                is_frozen=True,
            )
            with open(migrated_data_path, "r", encoding="utf-8") as file:
                self.assertEqual(json.load(file), [])

    def test_linux_build_in_dist_subdirectory_copies_project_files(self):
        with tempfile.TemporaryDirectory() as directory:
            project_directory = os.path.join(directory, "project")
            executable_directory = os.path.join(project_directory, "dist", "linux")
            storage_directory = os.path.join(directory, "user-data", "CVault")
            os.makedirs(executable_directory)
            legacy_data = [{"site": "example.test", "password": "sample"}]
            with open(os.path.join(project_directory, "data.json"), "w", encoding="utf-8") as file:
                json.dump(legacy_data, file)

            main.migrate_packaged_storage(
                storage_directory,
                executable_path=os.path.join(executable_directory, "CVault"),
                is_frozen=True,
            )

            with open(os.path.join(storage_directory, "data.json"), "r", encoding="utf-8") as file:
                self.assertEqual(json.load(file), legacy_data)

    def test_source_run_does_not_migrate_packaged_files(self):
        with tempfile.TemporaryDirectory() as directory:
            main.migrate_packaged_storage(directory, is_frozen=False)
            self.assertEqual(os.listdir(directory), [])


if __name__ == "__main__":
    unittest.main()
