"""Updater checks use synthetic releases; no game files or network required."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_backend as updater


def sha(data):
    return hashlib.sha256(data).hexdigest()


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tekken-updater-test-")
        self.root = Path(self.temp.name)
        (self.root / "VERSION").write_text("0.1.3\n", encoding="utf-8")
        (self.root / "game.toml").write_text("game", encoding="utf-8")
        (self.root / "disc").mkdir()
        (self.root / "disc" / "owned.cue").write_text("personal disc", encoding="utf-8")
        (self.root / "build-release" / "mods").mkdir(parents=True)
        (self.root / "build-release" / "mods" / "player-mod.txt").write_text("keep", encoding="utf-8")
        (self.root / "build-release" / "Tekken_3_Recompiled.exe").write_bytes(b"old game")
        (self.root / ".setup").mkdir()
        (self.root / ".setup" / "ready.json").write_text("old ready", encoding="utf-8")
        self.patchers = [
            patch.object(updater, "ROOT", self.root),
            patch.object(updater, "STATE", self.root / ".setup"),
            patch.object(updater, "STATUS", self.root / ".setup" / "update-status.json"),
            patch.object(updater, "SETTINGS", self.root / ".setup" / "updates.json"),
        ]
        for item in self.patchers:
            item.start()

    def tearDown(self):
        for item in reversed(self.patchers):
            item.stop()
        self.temp.cleanup()

    def release_fixture(self, files=None):
        files = files or {"VERSION": b"0.1.4\n", "src/new.txt": b"new source"}
        package = self.root / "source.zip"
        with zipfile.ZipFile(package, "w") as zipped:
            for name, data in files.items():
                zipped.writestr(name, data)
        manifest = self.root / "source-manifest.json"
        manifest.write_text(json.dumps({"release": "v0.1.4", "files": [
            {"path": name, "size": len(data), "sha256": sha(data)} for name, data in files.items()
        ]}), encoding="utf-8")
        def asset(name):
            return {"name": name, "digest": "sha256:" + "a" * 64, "size": 123,
                    "browser_download_url": "https://github.com/tekken3-linux/releases/download/v0.1.4/" + name}
        release = {"tag_name": "v0.1.4", "name": "Patch 0.1.4", "body": "Fixed things",
                   "html_url": "https://github.com/tekken3-linux/releases/tag/v0.1.4",
                   "draft": False, "prerelease": True,
                   "assets": [asset("Tekken3Recompiled-v0.1.4-Easy-Setup.zip"), asset("RELEASE-MANIFEST.json")]}
        def fake_download(spec, target, label):
            shutil.copy2(manifest if spec["name"] == "RELEASE-MANIFEST.json" else package, target)
            return target
        return release, fake_download

    def test_prerelease_selected_and_patch_zip_ignored(self):
        release, _ = self.release_fixture()
        release["assets"].append({"name": "Tekken3Recompiled-v0.1.4-Setup-Fix.zip"})
        selected = updater.select_release([release], "0.1.3")
        self.assertEqual(selected[0]["tag_name"], "v0.1.4")
        self.assertEqual(selected[1]["name"], "Tekken3Recompiled-v0.1.4-Easy-Setup.zip")
        self.assertIsNone(updater.select_release([release], "0.1.4"))

    def test_install_preserves_disc_and_mod_and_rebuilds(self):
        release, fake_download = self.release_fixture()
        with patch.object(updater, "releases", return_value=[release]), \
             patch.object(updater, "download", side_effect=fake_download), \
             patch.object(updater, "rebuild") as rebuild:
            updater.install("v0.1.4", 0, restart=False)
        rebuild.assert_called_once()
        self.assertEqual((self.root / "VERSION").read_text(), "0.1.4\n")
        self.assertEqual((self.root / "src" / "new.txt").read_bytes(), b"new source")
        self.assertEqual((self.root / "disc" / "owned.cue").read_text(), "personal disc")
        self.assertEqual((self.root / "build-release" / "mods" / "player-mod.txt").read_text(), "keep")
        self.assertEqual(updater.load_json(self.root / ".setup" / "current-patch.json")["version"], "v0.1.4")

    def test_failed_rebuild_restores_previous_install(self):
        release, fake_download = self.release_fixture()
        def fail_rebuild():
            (self.root / "build-release" / "Tekken_3_Recompiled.exe").write_bytes(b"broken")
            (self.root / "build-release" / "mods" / "player-mod.txt").write_text("broken")
            raise updater.UpdateError("build failed")
        with patch.object(updater, "releases", return_value=[release]), \
             patch.object(updater, "download", side_effect=fake_download), \
             patch.object(updater, "rebuild", side_effect=fail_rebuild):
            with self.assertRaises(updater.UpdateError):
                updater.install("v0.1.4", 0, restart=False)
        self.assertEqual((self.root / "VERSION").read_text(), "0.1.3\n")
        self.assertFalse((self.root / "src" / "new.txt").exists())
        self.assertEqual((self.root / "build-release" / "Tekken_3_Recompiled.exe").read_bytes(), b"old game")
        self.assertEqual((self.root / "build-release" / "mods" / "player-mod.txt").read_text(), "keep")
        self.assertEqual((self.root / ".setup" / "ready.json").read_text(), "old ready")

    def test_archive_rejects_traversal_and_bad_hash(self):
        for name in ("../outside", "C:/outside", "safe/../../outside", "safe\\outside", "CON.txt"):
            with self.subTest(name=name), self.assertRaises(updater.UpdateError):
                updater.safe_name(name)
        package = self.root / "bad.zip"
        with zipfile.ZipFile(package, "w") as zipped:
            zipped.writestr("VERSION", b"wrong")
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"release": "v0.1.4", "files": [
            {"path": "VERSION", "size": 5, "sha256": "a" * 64}]}), encoding="utf-8")
        with self.assertRaises(updater.UpdateError):
            updater.stage_archive(package, manifest, self.root / "stage", "v0.1.4")


if __name__ == "__main__":
    unittest.main()
