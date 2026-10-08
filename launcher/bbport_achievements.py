# SPDX-License-Identifier: GPL-2.0-or-later
"""Achievement tracking panel for the Bloodborne launcher (GTK4 / libadwaita).

Watches ~/.local/share/bbport/achievements.json via Linux inotify (zero CPU while idle).
Renders the PS5 Platinum Trophy circle with a dynamic PlayStation Blue progress arc,
along with an interactive achievements browser with real-time unlock tracking.
"""

import ctypes
import ctypes.util
import fcntl
import json
import math
import os
import struct
import subprocess
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk, Gdk, Pango  # noqa: E402
from bbport_i18n import tr

# ---------------------------------------------------------------------------
# Bloodborne CUSA03173: all 40 trophies (base game + The Old Hunters DLC)
# ---------------------------------------------------------------------------
TROPHY_LIST = [
    {"id": 0,  "name": "Bloodborne",                          "grade": "platinum", "desc": "All trophies unlocked"},
    {"id": 1,  "name": "Hunter's Essence",                    "grade": "gold",     "desc": "Acquire all hunter weapons"},
    {"id": 2,  "name": "Hunter's Craft",                      "grade": "silver",   "desc": "Acquire all special hunter tools"},
    {"id": 3,  "name": "Weapon Master",                       "grade": "silver",   "desc": "Acquire a weapon of the highest level"},
    {"id": 4,  "name": "Blood Gem Master",                    "grade": "silver",   "desc": "Acquire an extremely precious blood gem"},
    {"id": 5,  "name": "Rune Master",                         "grade": "silver",   "desc": "Acquire an extremely precious Caryll Rune"},
    {"id": 6,  "name": "Yharnam Sunrise",                     "grade": "gold",     "desc": "You lived through the hunt, and saw another morning"},
    {"id": 7,  "name": "Honoring Wishes",                     "grade": "gold",     "desc": "Captivated by the moon presence, you pledge to watch over the hunter's dream"},
    {"id": 8,  "name": "Childhood's Beginning",               "grade": "gold",     "desc": "You became an infant Great One, lifting humanity into its next childhood"},
    {"id": 9,  "name": "Cainhurst",                           "grade": "silver",   "desc": "Gain entry to Cainhurst, the lost and ruined castle"},
    {"id": 10, "name": "The Choir",                           "grade": "silver",   "desc": "Gain entry to the realm of the Choir, the high stratum of the Healing Church"},
    {"id": 11, "name": "The Source of the Dream",             "grade": "silver",   "desc": "Discover the abandoned old workshop, the source of the hunter's dream"},
    {"id": 12, "name": "Nightmare Lecture Building",           "grade": "silver",   "desc": "Gain entry into the Byrgenwerth lecture building, drifted into the realm of nightmare"},
    {"id": 13, "name": "Nightmare of Mensis",                 "grade": "silver",   "desc": "Gain entry into the Mensis nightmare, home of the school of Mensis"},
    {"id": 14, "name": "Father Gascoigne",                    "grade": "bronze",   "desc": "Defeat the beast that once was Father Gascoigne"},
    {"id": 15, "name": "Vicar Amelia",                        "grade": "bronze",   "desc": "Defeat the beast that once was Vicar Amelia"},
    {"id": 16, "name": "Shadow of Yharnam",                   "grade": "bronze",   "desc": "Defeat the Shadow of Yharnam"},
    {"id": 17, "name": "Rom, the Vacuous Spider",             "grade": "bronze",   "desc": "Defeat Great One: Rom, the Vacuous Spider"},
    {"id": 18, "name": "The One Reborn",                      "grade": "bronze",   "desc": "Defeat The One Reborn"},
    {"id": 19, "name": "Micolash, Host of the Nightmare",     "grade": "bronze",   "desc": "Defeat Micolash, Host of the Nightmare"},
    {"id": 20, "name": "Mergo's Wet Nurse",                   "grade": "bronze",   "desc": "Defeat Great One: Mergo's Wet Nurse"},
    {"id": 21, "name": "Cleric Beast",                        "grade": "bronze",   "desc": "Defeat Cleric Beast"},
    {"id": 22, "name": "Blood-starved Beast",                 "grade": "bronze",   "desc": "Defeat Blood-starved Beast"},
    {"id": 23, "name": "The Witch of Hemwick",                "grade": "bronze",   "desc": "Defeat the Witch of Hemwick"},
    {"id": 24, "name": "Darkbeast Paarl",                     "grade": "bronze",   "desc": "Defeat Darkbeast Paarl"},
    {"id": 25, "name": "Amygdala",                            "grade": "bronze",   "desc": "Defeat Great One: Amygdala"},
    {"id": 26, "name": "Martyr Logarius",                     "grade": "bronze",   "desc": "Defeat Martyr Logarius"},
    {"id": 27, "name": "Celestial Emissary",                  "grade": "bronze",   "desc": "Defeat Great One: Celestial Emissary"},
    {"id": 28, "name": "Ebrietas, Daughter of the Cosmos",    "grade": "bronze",   "desc": "Defeat Great One: Ebrietas, Daughter of the Cosmos"},
    {"id": 29, "name": "Chalice of Pthumeru",                 "grade": "silver",   "desc": "Acquire the Chalice of Pthumeru that seals the catacombs under Yharnam"},
    {"id": 30, "name": "Chalice of Ailing Loran",             "grade": "silver",   "desc": "Acquire the Chalice of Ailing Loran that seals the land devoured by the sands"},
    {"id": 31, "name": "Chalice of Isz",                      "grade": "silver",   "desc": "Acquire the Great Chalice of Isz that seals the tomb of the cosmic kin"},
    {"id": 32, "name": "Yharnam, Pthumerian Queen",           "grade": "gold",     "desc": "Defeat Yharnam, Blood Queen of the Old Labyrinth"},
    {"id": 33, "name": "Hunter's Dream",                      "grade": "bronze",   "desc": "Gain access to the Hunter's Dream"},
    {"id": 34, "name": "Ludwig, the Holy Blade",              "grade": "silver",   "desc": "Defeat the beast that was once Ludwig, the Holy Blade"},
    {"id": 35, "name": "Laurence, the First Vicar",           "grade": "silver",   "desc": "Defeat the beast that was once Laurence, the First Vicar"},
    {"id": 36, "name": "Living Failures",                     "grade": "bronze",   "desc": "Defeat the failures who failed to become Great Ones"},
    {"id": 37, "name": "Lady Maria of the Astral Clocktower", "grade": "silver",   "desc": "Defeat Lady Maria of the Astral Clocktower"},
    {"id": 38, "name": "Orphan of Kos",                       "grade": "gold",     "desc": "Defeat Great One: Orphan of Kos"},
    {"id": 39, "name": "The Old Hunters",                     "grade": "gold",     "desc": "Acquire all Old Hunter weapons"},
]
TOTAL_TROPHIES = len(TROPHY_LIST)

GRADE_ICONS = {
    "platinum": "🏆",
    "gold":     "🥇",
    "silver":   "🥈",
    "bronze":   "🥉",
}

GRADE_COLORS = {
    "platinum": "#38bdf8",
    "gold":     "#fbbf24",
    "silver":   "#cbd5e1",
    "bronze":   "#fb923c",
}

# ---------------------------------------------------------------------------
# Linux inotify via ctypes — zero CPU file watcher
# ---------------------------------------------------------------------------
IN_MODIFY = 0x00000002
IN_ATTRIB = 0x00000004
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_NONBLOCK = getattr(os, "O_NONBLOCK", 0o4000)
IN_CLOEXEC = getattr(os, "O_CLOEXEC", 0o2000000)

_libc_name = ctypes.util.find_library("c")
_libc = ctypes.CDLL(_libc_name, use_errno=True) if _libc_name else None


class InotifyWatcher:
    """Watches achievement files and directories for writes via Linux inotify with GLib main loop integration."""

    def __init__(self, paths, callback):
        if isinstance(paths, (str, Path)):
            self.paths = [Path(paths)]
        else:
            self.paths = [Path(p) for p in paths]
        self.callback = callback
        self.inotify_fd = -1
        self.watch_fds = {}  # watch_fd -> watch_dir
        self.source_id = None

        if _libc is None:
            return

        if hasattr(_libc, "inotify_init1"):
            self.inotify_fd = _libc.inotify_init1(IN_NONBLOCK | IN_CLOEXEC)
            if self.inotify_fd < 0:
                self.inotify_fd = _libc.inotify_init1(0)
        if self.inotify_fd < 0 and hasattr(_libc, "inotify_init"):
            self.inotify_fd = _libc.inotify_init()

        if self.inotify_fd < 0:
            return

        try:
            flags = fcntl.fcntl(self.inotify_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.inotify_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        except Exception:
            pass

        mask = IN_CLOSE_WRITE | IN_MODIFY | IN_CREATE | IN_MOVED_TO | IN_ATTRIB | IN_DELETE
        watched_dirs = set()
        for p in self.paths:
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                watch_dir = str(p.parent.resolve())
            except Exception:
                watch_dir = str(p.parent)
            if watch_dir not in watched_dirs:
                wfd = _libc.inotify_add_watch(self.inotify_fd, watch_dir.encode(), mask)
                if wfd >= 0:
                    self.watch_fds[wfd] = watch_dir
                    watched_dirs.add(watch_dir)

        channel = GLib.IOChannel.unix_new(self.inotify_fd)
        channel.set_encoding(None)
        channel.set_buffered(False)
        self.source_id = GLib.io_add_watch(
            channel,
            GLib.PRIORITY_DEFAULT,
            GLib.IOCondition.IN | GLib.IOCondition.HUP | GLib.IOCondition.ERR,
            self._on_readable,
        )

    def _on_readable(self, _channel, condition):
        if condition & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
            return False

        targets = {p.name.encode() for p in self.paths}
        fired = False

        while True:
            try:
                data = os.read(self.inotify_fd, 4096)
                if not data:
                    break
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break

            offset = 0
            while offset + 16 <= len(data):
                _wd, _mask, _cookie, name_len = struct.unpack_from("iIII", data, offset)
                offset += 16
                if name_len > 0:
                    name = data[offset:offset + name_len].rstrip(b"\x00")
                    offset += name_len
                    if name in targets:
                        fired = True
                else:
                    fired = True

        if fired:
            self.callback()
        return True

    def stop(self):
        if self.source_id is not None:
            try:
                GLib.source_remove(self.source_id)
            except Exception:
                pass
            self.source_id = None
        if self.inotify_fd >= 0:
            if _libc is not None and hasattr(_libc, "inotify_rm_watch"):
                for wfd in list(self.watch_fds.keys()):
                    try:
                        _libc.inotify_rm_watch(self.inotify_fd, wfd)
                    except Exception:
                        pass
            try:
                os.close(self.inotify_fd)
            except Exception:
                pass
            self.inotify_fd = -1
        self.watch_fds.clear()


# ---------------------------------------------------------------------------
# Achievement data loader
# ---------------------------------------------------------------------------

def get_achievement_paths():
    """Returns all paths to achievements.json (standard location and BB_DATA_DIR)."""
    paths = []
    seen = set()

    # 1. BB_DATA_DIR if specified
    data_dir = os.environ.get("BB_DATA_DIR")
    if data_dir:
        p = (Path(data_dir) / "achievements.json").expanduser()
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if rp not in seen:
            seen.add(rp)
            paths.append(p)

    # 2. Standard location: ~/.local/share/bbport/achievements.json
    home = os.environ.get("HOME", "/tmp")
    p = Path(home) / ".local" / "share" / "bbport" / "achievements.json"
    try:
        rp = p.resolve()
    except Exception:
        rp = p
    if rp not in seen:
        seen.add(rp)
        paths.append(p)

    return paths


def achievements_path():
    """Returns the primary existing achievements.json path or default."""
    for p in get_achievement_paths():
        if p.is_file():
            return p
    paths = get_achievement_paths()
    return paths[0] if paths else Path.home() / ".local" / "share" / "bbport" / "achievements.json"


def load_achievements():
    """Returns {trophy_id: unlock_timestamp_str, ...} merged across all achievement paths."""
    unlocked = {}
    for path in get_achievement_paths():
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict):
                        tid = entry.get("id")
                        ts = entry.get("unlocked_at", "")
                        if tid is not None:
                            try:
                                itid = int(tid)
                                if itid not in unlocked or (ts and not unlocked[itid]):
                                    unlocked[itid] = ts
                            except (ValueError, TypeError):
                                pass
        except (OSError, ValueError):
            continue
    return unlocked


def format_timestamp(ts_str):
    if not ts_str:
        return ""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime("%b %d, %Y  %H:%M")
    except (ValueError, TypeError):
        return ts_str


# ---------------------------------------------------------------------------
# PS5 Platinum Trophy & Dynamic Blue Progress Circle SVG Generator
# ---------------------------------------------------------------------------

def render_ps5_trophy_svg(fraction, _unlocked, _total):
    """Generates a tall, black-and-white SVG trophy icon inside a progress ring."""
    r = 60
    cx, cy = 80, 110
    circ = 2 * math.pi * r
    clamped = max(0.0, min(1.0, fraction))
    offset = circ * (1.0 - clamped)

    # Active progress arc (white/silver)
    if clamped > 0.001:
        arc_svg = (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#bw-arc)" stroke-width="8" '
            f'stroke-dasharray="{circ:.2f} {circ:.2f}" stroke-dashoffset="{offset:.2f}" '
            f'stroke-linecap="round" transform="rotate(-90 {cx} {cy})"/>'
        )
    else:
        arc_svg = ""

    # Glowing ring if 100% completed
    plat_crown = (
        f'<circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="none" stroke="#d0d0d0" stroke-width="1.5" opacity="0.6"/>'
        if clamped >= 0.999 else ""
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="220" viewBox="0 0 160 220">
  <defs>
    <!-- Black & white metallic gradient -->
    <linearGradient id="bw-metal" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff"/>
      <stop offset="25%" stop-color="#d4d4d4"/>
      <stop offset="65%" stop-color="#737373"/>
      <stop offset="100%" stop-color="#3a3a3a"/>
    </linearGradient>
    <!-- White/silver progress ring -->
    <linearGradient id="bw-arc" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#e0e0e0"/>
      <stop offset="45%" stop-color="#a0a0a0"/>
      <stop offset="100%" stop-color="#606060"/>
    </linearGradient>
    <!-- Soft radial glow (neutral) -->
    <radialGradient id="bw-glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="rgba(180, 180, 180, 0.22)"/>
      <stop offset="70%" stop-color="rgba(120, 120, 120, 0.05)"/>
      <stop offset="100%" stop-color="rgba(0, 0, 0, 0)"/>
    </radialGradient>
  </defs>

  <!-- Background Track & Glow -->
  <circle cx="{cx}" cy="{cy}" r="74" fill="url(#bw-glow)"/>
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(255, 255, 255, 0.08)" stroke-width="7"/>

  <!-- Active Progress Arc -->
  {arc_svg}
  {plat_crown}

  <!-- Inner Circle Hub -->
  <circle cx="{cx}" cy="{cy}" r="49" fill="#0d0d0d" stroke="rgba(255, 255, 255, 0.12)" stroke-width="1.5"/>

  <!-- Trophy Cup (taller, black & white) -->
  <g transform="translate({cx}, {cy - 2}) scale(1.15)">
    <!-- Curved cup handles -->
    <path d="M-18,-14 C-25,-14 -25,4 -16,8 L-14,4 C-21,1 -20,-10 -15,-10 Z" fill="url(#bw-metal)"/>
    <path d="M18,-14 C25,-14 25,4 16,8 L14,4 C21,1 20,-10 15,-10 Z" fill="url(#bw-metal)"/>

    <!-- Cup Body -->
    <path d="M-16,-18 L16,-18 L13,6 C11,14 -11,14 -13,6 Z" fill="url(#bw-metal)"/>

    <!-- Cup Rim & Opening -->
    <ellipse cx="0" cy="-18" rx="16" ry="3.5" fill="#e8e8e8"/>
    <ellipse cx="0" cy="-18" rx="13.5" ry="2.5" fill="#555555"/>

    <!-- Center Shine (monochrome) -->
    <path d="M-7,-16 L-2,-16 L-2,12 C-5,11 -6.5,8 -7,4 Z" fill="#ffffff" opacity="0.45"/>
    <path d="M2,-16 L7,-16 L6.5,4 C6,8 5,11 2,12 Z" fill="#2a2a2a" opacity="0.35"/>

    <!-- Stem -->
    <path d="M-3.5,12 L3.5,12 L4.5,19 L-4.5,19 Z" fill="url(#bw-metal)"/>

    <!-- Pedestal Base -->
    <path d="M-9,19 L9,19 L10,23 L-10,23 Z" fill="url(#bw-metal)"/>
    <path d="M-14,23 L14,23 L15,27 L-15,27 Z" fill="url(#bw-metal)"/>
    <line x1="-14" y1="27" x2="14" y2="27" stroke="#1a1a1a" stroke-width="1"/>

    <!-- Star emblem -->
    <polygon points="0,-6 1.8,-1.5 6.5,-1.5 2.8,1.2 4.2,5.5 0,3 -4.2,5.5 -2.8,1.2 -6.5,-1.5 -1.8,-1.5" fill="#ffffff" opacity="0.8"/>
  </g>
</svg>"""
    return svg


# ---------------------------------------------------------------------------
# CSS Styling for Achievements Rectangle Box
# ---------------------------------------------------------------------------

ACHIEVEMENT_CSS = """
.achievement-rectangle-box {
    background: linear-gradient(135deg, alpha(@card_bg_color, 0.95), alpha(@window_bg_color, 0.98));
    border: 1px solid alpha(#0070d1, 0.35);
    border-radius: 16px;
    padding: 16px;
    margin: 4px 0 16px 0;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.trophy-left-col {
    min-width: 175px;
    padding-right: 14px;
}

.trophy-percent-badge {
    font-size: 20px;
    font-weight: 800;
    color: #38bdf8;
    letter-spacing: 0.5px;
}

.trophy-count-label {
    font-size: 13px;
    font-weight: 600;
    color: alpha(@window_fg_color, 0.85);
}

.trophy-tier-pills {
    font-size: 11px;
    color: alpha(@window_fg_color, 0.7);
    background: alpha(@window_fg_color, 0.06);
    border-radius: 12px;
    padding: 3px 10px;
    margin-top: 4px;
}

.trophy-right-col {
    padding-left: 8px;
}

.trophy-header-title {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.3px;
}

.trophy-header-sub {
    font-size: 12px;
    color: alpha(@window_fg_color, 0.6);
}

.trophy-filter-btn {
    font-size: 11px;
    padding: 3px 10px;
    min-height: 26px;
}

.trophy-card {
    background: alpha(@window_fg_color, 0.04);
    border-radius: 8px;
    padding: 8px 12px;
    border: 1px solid transparent;
    transition: all 160ms ease;
}

.trophy-card:hover {
    background: alpha(@window_fg_color, 0.08);
}

.trophy-card-unlocked {
    background: alpha(#0070d1, 0.12);
    border: 1px solid alpha(#0070d1, 0.35);
}

.trophy-card-unlocked:hover {
    background: alpha(#0070d1, 0.18);
}

.trophy-card-locked {
    opacity: 0.7;
}

.trophy-card-name {
    font-weight: 600;
    font-size: 13px;
}

.trophy-card-unlocked .trophy-card-name {
    color: @window_fg_color;
}

.trophy-card-locked .trophy-card-name {
    color: alpha(@window_fg_color, 0.6);
}

.trophy-card-sub {
    font-size: 11px;
    color: alpha(@window_fg_color, 0.55);
}

.trophy-card-status-unlocked {
    font-size: 11px;
    font-weight: 600;
    color: #4ade80;
}

.trophy-card-status-locked {
    font-size: 12px;
    color: alpha(@window_fg_color, 0.4);
}
"""

_css_loaded = False


def _ensure_css():
    global _css_loaded
    if _css_loaded:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(ACHIEVEMENT_CSS.encode())
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    _css_loaded = True


# ---------------------------------------------------------------------------
# AchievementBox Widget — The Top Rectangle Box
# ---------------------------------------------------------------------------

class AchievementBox(Gtk.Box):
    """The Top Achievements Rectangle Box:

    - Left Side: Circle with PS5 Platinum trophy icon and PlayStation Blue progress fill.
    - Right Side: Interactive achievements list showing locked vs unlocked trophies.
    """

    def __init__(self, toast_overlay=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        _ensure_css()
        self.add_css_class("achievement-rectangle-box")

        self._toast_overlay = toast_overlay
        self._filter = "all"  # "all", "unlocked", "locked"
        self._trophy_widgets = {}  # tid -> (card, name_lbl, sub_lbl, status_lbl, is_unlocked)
        self._known_unlocked = None
        self._refresh_timeout_id = None
        self._poll_timer_id = None

        self._build_ui()
        self._refresh()

        # inotify file watcher (instant, 0% CPU while idle)
        self._watcher = InotifyWatcher(get_achievement_paths(), self._on_file_changed)

        # File snapshots and fallback polling timer (never miss an update)
        self._file_snapshots = self._snapshot_files()
        self._poll_timer_id = GLib.timeout_add_seconds(1, self._poll_check)

    def _build_ui(self):
        # ── LEFT SIDE: PS5 Platinum Circle & Progress ──
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        left_box.add_css_class("trophy-left-col")
        left_box.set_valign(Gtk.Align.CENTER)
        left_box.set_halign(Gtk.Align.CENTER)

        # The Circle Picture (dynamic SVG)
        self._trophy_picture = Gtk.Picture()
        self._trophy_picture.set_can_shrink(False)
        self._trophy_picture.set_size_request(140, 140)
        left_box.append(self._trophy_picture)

        # Percentage label
        self._percent_label = Gtk.Label(label="0%")
        self._percent_label.add_css_class("trophy-percent-badge")
        left_box.append(self._percent_label)

        # Unlocked / Total text
        self._counter_label = Gtk.Label(label="0 / 40 Unlocked")
        self._counter_label.add_css_class("trophy-count-label")
        left_box.append(self._counter_label)

        # Tier breakdown pills
        self._tier_label = Gtk.Label(label="🏆 0   🥇 0   🥈 0   🥉 0")
        self._tier_label.add_css_class("trophy-tier-pills")
        left_box.append(self._tier_label)

        self.append(left_box)

        # Vertical Divider
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.append(sep)

        # ── RIGHT SIDE: Achievements Browser ──
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        right_box.add_css_class("trophy-right-col")
        right_box.set_hexpand(True)

        # Top row: title & filter buttons
        header_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        title_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        main_title = Gtk.Label(label=tr("Трофеи Bloodborne"), xalign=0)
        main_title.add_css_class("trophy-header-title")
        title_col.append(main_title)

        self._status_summary = Gtk.Label(label="0 Unlocked · 40 Locked", xalign=0)
        self._status_summary.add_css_class("trophy-header-sub")
        title_col.append(self._status_summary)
        header_row.append(title_col)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_row.append(spacer)

        # Filter Segmented Group
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        filter_box.add_css_class("linked")

        self._btn_all = Gtk.Button(label=tr("Все"))
        self._btn_all.add_css_class("trophy-filter-btn")
        self._btn_all.add_css_class("suggested-action")
        self._btn_all.connect("clicked", lambda _b: self._set_filter("all"))
        filter_box.append(self._btn_all)

        self._btn_unlocked = Gtk.Button(label=tr("Открыто"))
        self._btn_unlocked.add_css_class("trophy-filter-btn")
        self._btn_unlocked.connect("clicked", lambda _b: self._set_filter("unlocked"))
        filter_box.append(self._btn_unlocked)

        self._btn_locked = Gtk.Button(label=tr("Закрыто"))
        self._btn_locked.add_css_class("trophy-filter-btn")
        self._btn_locked.connect("clicked", lambda _b: self._set_filter("locked"))
        filter_box.append(self._btn_locked)

        header_row.append(filter_box)
        right_box.append(header_row)

        # Scrollable list of achievements
        self._cards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroller = Gtk.ScrolledWindow(
            vexpand=True,
            hexpand=True,
            min_content_height=180,
            max_content_height=225,
            child=self._cards_box,
        )
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        right_box.append(scroller)

        self.append(right_box)

        # Populate trophy cards
        self._build_trophy_cards()

    def _build_trophy_cards(self):
        for trophy in TROPHY_LIST:
            tid = trophy["id"]
            grade = trophy["grade"]
            name = trophy["name"]
            desc = trophy.get("desc", "")

            card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            card.add_css_class("trophy-card")

            # Grade Icon
            grade_icon = Gtk.Label(label=GRADE_ICONS.get(grade, "🏅"))
            grade_icon.set_valign(Gtk.Align.CENTER)
            card.append(grade_icon)

            # Details column
            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            text_box.set_hexpand(True)

            name_lbl = Gtk.Label(label=name, xalign=0, ellipsize=Pango.EllipsizeMode.END)
            name_lbl.add_css_class("trophy-card-name")
            text_box.append(name_lbl)

            sub_lbl = Gtk.Label(label=desc, xalign=0, ellipsize=Pango.EllipsizeMode.END)
            sub_lbl.add_css_class("trophy-card-sub")
            text_box.append(sub_lbl)

            card.append(text_box)

            # Status column
            status_lbl = Gtk.Label(label="🔒", xalign=1)
            status_lbl.set_valign(Gtk.Align.CENTER)
            card.append(status_lbl)

            self._cards_box.append(card)
            self._trophy_widgets[tid] = {
                "card": card,
                "name_lbl": name_lbl,
                "sub_lbl": sub_lbl,
                "status_lbl": status_lbl,
                "is_unlocked": False,
            }

    def _set_filter(self, mode):
        self._filter = mode
        # Update button classes
        self._btn_all.remove_css_class("suggested-action")
        self._btn_unlocked.remove_css_class("suggested-action")
        self._btn_locked.remove_css_class("suggested-action")

        if mode == "all":
            self._btn_all.add_css_class("suggested-action")
        elif mode == "unlocked":
            self._btn_unlocked.add_css_class("suggested-action")
        elif mode == "locked":
            self._btn_locked.add_css_class("suggested-action")

        self._apply_filter()

    def _apply_filter(self):
        for _tid, info in self._trophy_widgets.items():
            unlocked = info["is_unlocked"]
            if self._filter == "all":
                info["card"].set_visible(True)
            elif self._filter == "unlocked":
                info["card"].set_visible(unlocked)
            elif self._filter == "locked":
                info["card"].set_visible(not unlocked)

    def _snapshot_files(self):
        snapshots = {}
        for p in get_achievement_paths():
            try:
                st = p.stat()
                snapshots[str(p)] = (st.st_mtime_ns, st.st_size)
            except OSError:
                snapshots[str(p)] = None
        return snapshots

    def _poll_check(self):
        curr = self._snapshot_files()
        if curr != self._file_snapshots:
            self._file_snapshots = curr
            self._on_file_changed()
        return True

    def _on_file_changed(self):
        if self._refresh_timeout_id is None:
            self._refresh_timeout_id = GLib.timeout_add(50, self._deferred_refresh)

    def _deferred_refresh(self):
        self._refresh_timeout_id = None
        self._file_snapshots = self._snapshot_files()
        self._refresh()
        return False

    def _notify_trophy_unlocked(self, trophy):
        name = trophy.get("name", "")
        grade = trophy.get("grade", "bronze")
        desc = trophy.get("desc", "")
        grade_icon = GRADE_ICONS.get(grade, "🏆")

        # 1. In-app toast notification in launcher
        toast_parent = self._toast_overlay or self.get_ancestor(Adw.ToastOverlay)
        if toast_parent and hasattr(toast_parent, "add_toast"):
            try:
                toast_title = f"{grade_icon} {tr('Трофей разблокирован!')}: {name}"
                toast = Adw.Toast(title=toast_title, timeout=6)
                toast_parent.add_toast(toast)
            except Exception:
                pass

        # 2. Desktop notification via notify-send so user sees it in-game
        try:
            notif_title = f"{grade_icon} Bloodborne: {tr('Трофей разблокирован!')}"
            notif_body = f"{name}\n{desc}" if desc else name
            subprocess.Popen(
                ["notify-send", "-a", "Bloodborne", "-u", "normal", notif_title, notif_body],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    def _refresh(self):
        """Re-reads achievements.json and updates the circular progress and cards."""
        unlocked = load_achievements()
        count = len(unlocked)
        fraction = count / TOTAL_TROPHIES if TOTAL_TROPHIES else 0.0

        current_unlocked_ids = set(unlocked.keys())

        # Check for newly unlocked trophies if not the initial startup
        if self._known_unlocked is not None:
            newly_unlocked = current_unlocked_ids - self._known_unlocked
            for tid in sorted(newly_unlocked):
                trophy = next((t for t in TROPHY_LIST if t["id"] == tid), None)
                if trophy:
                    self._notify_trophy_unlocked(trophy)

        self._known_unlocked = current_unlocked_ids

        # Update Circle graphic (SVG -> Gdk.Texture)
        svg_code = render_ps5_trophy_svg(fraction, count, TOTAL_TROPHIES)
        b = GLib.Bytes.new(svg_code.encode("utf-8"))
        try:
            texture = Gdk.Texture.new_from_bytes(b)
            self._trophy_picture.set_paintable(texture)
        except Exception:
            pass

        # Update Left column counters
        percent = int(fraction * 100)
        self._percent_label.set_label(f"{percent}%")
        self._counter_label.set_label(f"{count} / {TOTAL_TROPHIES} " + tr("Открыто"))

        # Tier breakdown
        tiers = {"platinum": 0, "gold": 0, "silver": 0, "bronze": 0}
        for trophy in TROPHY_LIST:
            if trophy["id"] in unlocked:
                tiers[trophy["grade"]] += 1

        self._tier_label.set_label(
            f"🏆 {tiers['platinum']}   🥇 {tiers['gold']}   🥈 {tiers['silver']}   🥉 {tiers['bronze']}"
        )

        # Update Right column header
        locked_count = TOTAL_TROPHIES - count
        self._status_summary.set_label(
            f"{count} " + tr("Открыто") + f" · {locked_count} " + tr("Закрыто")
        )
        self._btn_all.set_label(tr("Все") + f" ({TOTAL_TROPHIES})")
        self._btn_unlocked.set_label(tr("Открыто") + f" ({count})")
        self._btn_locked.set_label(tr("Закрыто") + f" ({locked_count})")

        # Update individual trophy cards
        for trophy in TROPHY_LIST:
            tid = trophy["id"]
            info = self._trophy_widgets[tid]
            card = info["card"]
            status_lbl = info["status_lbl"]
            sub_lbl = info["sub_lbl"]

            card.remove_css_class("trophy-card-unlocked")
            card.remove_css_class("trophy-card-locked")
            status_lbl.remove_css_class("trophy-card-status-unlocked")
            status_lbl.remove_css_class("trophy-card-status-locked")

            ts = unlocked.get(tid)
            if ts is not None:
                info["is_unlocked"] = True
                card.add_css_class("trophy-card-unlocked")
                status_lbl.add_css_class("trophy-card-status-unlocked")
                status_lbl.set_label("✓ " + tr("Открыто"))
                date_str = format_timestamp(ts)
                sub_lbl.set_label(f"{trophy.get('desc', '')} · {date_str}" if date_str else trophy.get("desc", ""))
            else:
                info["is_unlocked"] = False
                card.add_css_class("trophy-card-locked")
                status_lbl.add_css_class("trophy-card-status-locked")
                status_lbl.set_label("🔒")
                sub_lbl.set_label(trophy.get("desc", ""))

        self._apply_filter()

    def destroy_watcher(self):
        if hasattr(self, "_watcher") and self._watcher is not None:
            self._watcher.stop()
            self._watcher = None
        if hasattr(self, "_poll_timer_id") and self._poll_timer_id is not None:
            try:
                GLib.source_remove(self._poll_timer_id)
            except Exception:
                pass
            self._poll_timer_id = None
        if hasattr(self, "_refresh_timeout_id") and self._refresh_timeout_id is not None:
            try:
                GLib.source_remove(self._refresh_timeout_id)
            except Exception:
                pass
            self._refresh_timeout_id = None


# Backward compatibility alias
AchievementPanel = AchievementBox
