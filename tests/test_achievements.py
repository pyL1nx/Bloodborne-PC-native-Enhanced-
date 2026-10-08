# SPDX-License-Identifier: GPL-2.0-or-later
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT

sys.path.insert(0, str(ROOT / "launcher"))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib
Adw.init()

from bbport_achievements import (
    AchievementBox,
    InotifyWatcher,
    get_achievement_paths,
    load_achievements,
)


class AchievementsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.tmp.name)
        self.fake_home = self.temp_path / "home"
        self.fake_home.mkdir()
        self.data_dir = self.temp_path / "data"
        self.data_dir.mkdir()
        self.ach_file = self.data_dir / "achievements.json"

        self._orig_home = os.environ.get("HOME")
        self._orig_bb_data = os.environ.get("BB_DATA_DIR")
        os.environ["HOME"] = str(self.fake_home)
        os.environ["BB_DATA_DIR"] = str(self.data_dir)

    def tearDown(self):
        if self._orig_home is not None:
            os.environ["HOME"] = self._orig_home
        else:
            os.environ.pop("HOME", None)
        if self._orig_bb_data is not None:
            os.environ["BB_DATA_DIR"] = self._orig_bb_data
        else:
            os.environ.pop("BB_DATA_DIR", None)
        self.tmp.cleanup()

    def test_paths_and_empty_load(self):
        paths = get_achievement_paths()
        self.assertIn(self.ach_file, paths)
        self.assertEqual(load_achievements(), {})

    def test_live_inotify_unlock_and_tracking(self):
        self.ach_file.write_text("[]")
        box = AchievementBox()
        try:
            self.assertIn("0 / 40", box._counter_label.get_label())
            self.assertFalse(box._trophy_widgets[21]["is_unlocked"])

            notified = []
            box._notify_trophy_unlocked = lambda trophy: notified.append(trophy)

            # Atomic rename write simulating runtime_services.c
            tmp = self.data_dir / ".achievements.json.tmp"
            tmp.write_text(
                '[{"id": 21, "name": "Shadow of Yharnam", "unlocked_at": "2026-10-08T17:27:08+0530"}]'
            )
            os.replace(str(tmp), str(self.ach_file))

            ctx = GLib.MainContext.default()
            ctx.iteration(False)
            time.sleep(0.08)
            ctx.iteration(False)

            self.assertIn("1 / 40", box._counter_label.get_label())
            self.assertTrue(box._trophy_widgets[21]["is_unlocked"])
            self.assertEqual(len(notified), 1)
            self.assertEqual(notified[0]["id"], 21)
            self.assertEqual(notified[0]["name"], "Shadow of Yharnam")
        finally:
            box.destroy_watcher()

    def test_fallback_poll_check(self):
        self.ach_file.write_text("[]")
        box = AchievementBox()
        try:
            # Stop inotify to test poll check in isolation
            box._watcher.stop()
            box._watcher = None

            tmp = self.data_dir / ".achievements.json.tmp"
            tmp.write_text(
                '[{"id": 18, "name": "Cleric Beast", "unlocked_at": "2026-10-08T17:35:00+0530"}]'
            )
            os.replace(str(tmp), str(self.ach_file))

            box._poll_check()
            ctx = GLib.MainContext.default()
            time.sleep(0.08)
            ctx.iteration(False)

            self.assertIn("1 / 40", box._counter_label.get_label())
            self.assertTrue(box._trophy_widgets[18]["is_unlocked"])
        finally:
            box.destroy_watcher()


if __name__ == "__main__":
    unittest.main()
