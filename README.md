<div align="center">

# ⬡ MACROFORGE

**A lightweight, open-source macro & automation toolkit for Windows.**

Create keyboard macros, mouse click sequences, and timed automation scripts — organized by game or category, triggered by a single global hotkey.

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-1.0.0-purple)

</div>

---

## ✨ Features

- **Global hotkey** — one key triggers whichever macro is currently selected
- **Groups & folders** — organize macros by game, category, or use case
- **Key press macros** — send any key with custom delay and repeat count
- **Mouse click automation** — left, right, or middle click at specific coordinates
- **Sequence steps** — chain multiple actions in order with individual timing
- **Loop mode** — repeat a macro indefinitely with a configurable loop delay
- **High-accuracy timing** — uses Windows 1ms timer resolution for precise delays
- **Auto-save** — macros save automatically on exit and reload on next launch
- **Coordinate picker** — 3-second countdown to capture any screen position
- **Standalone .exe** — no Python required for end users after building

---

## 🚀 Getting Started

### Option A — Run from source (requires Python)

1. Install [Python 3.8+](https://python.org)
2. Install the dependency:
   ```
   pip install pynput
   ```
3. Run the app:
   ```
   python macro_app.py
   ```

### Option B — Build a standalone .exe (recommended)

1. Install [Python 3.8+](https://python.org)
2. Double-click **`build_exe.bat`**
3. Your `MACROFORGE.exe` will appear in the `dist/` folder
4. Move the `.exe` anywhere — it runs with no dependencies

---

## 🎮 How to Use

### 1. Set your global hotkey
Click the **HOTKEY** button in the top-right of the title bar, then press any key (e.g. `F8`). This key will toggle the currently selected macro on/off from any window.

### 2. Create a group
Click **+ GROUP** in the sidebar and name it (e.g. "Roblox", "My Game"). Groups keep your macros organized by game or category.

### 3. Create a macro
Select a group, then click **+ MACRO**. Give it a name.

### 4. Add steps

**Key steps** (`+ KEY`)
- `key` — the key to press. Single letters (`z`, `x`), or special keys (see table below)
- `delay(s)` — how long to wait after pressing (wall-clock accurate)
- `×` — how many times to press before moving to the next step

**Click steps** (`+ CLICK`)
- `btn` — `left`, `right`, or `middle`
- `x` / `y` — screen coordinates (leave blank to click at current cursor position)
- Click **📍 pick** for a 3-second countdown to capture your cursor position
- `delay(s)` / `×` — same as key steps

### 5. Configure looping
Check **Loop macro** to repeat the sequence continuously. Set a **loop delay** (seconds between full repetitions).

### 6. Run it
- Click **▶ RUN MACRO** in the editor, or
- Press your global hotkey from any window — including your game
- Press again (or click **■ STOP**) to stop

---

## ⌨️ Special Key Names

| Key | Value to type |
|-----|--------------|
| Spacebar | `space` |
| Enter | `enter` |
| Tab | `tab` |
| Escape | `esc` |
| Backspace | `backspace` |
| Delete | `delete` |
| Shift | `shift` |
| Ctrl | `ctrl` |
| Alt | `alt` |
| Arrow keys | `up` `down` `left` `right` |
| Function keys | `f1` through `f12` |
| Letters / numbers | just type them: `z`, `1`, `a` |

---

## 📁 File Structure

```
MACROFORGE/
├── macro_app.py      # Main application
├── build_exe.bat     # One-click EXE builder
├── icon.ico          # App icon (for EXE)
├── icon.png          # App icon (for window)
├── macros.json       # Auto-generated save file (created on first run)
└── README.md         # This file
```

---

## 🛠️ Building from Source

Requirements:
- Python 3.8+
- `pynput` — input simulation
- `pyinstaller` — for building the `.exe`

```bash
pip install pynput pyinstaller
python -m PyInstaller --onefile --windowed --name MACROFORGE \
  --icon=icon.ico \
  --add-data "icon.png;." \
  --hidden-import pynput.keyboard._win32 \
  --hidden-import pynput.mouse._win32 \
  macro_app.py
```

---

## ⚠️ Disclaimer

MACROFORGE is intended for **personal, educational, and accessibility use only**. The user is solely responsible for ensuring their use of this software complies with the terms of service of any games, applications, or platforms they use it with. The author assumes no liability for any consequences resulting from misuse.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Pull requests are welcome! If you find a bug or have a feature idea, open an issue.

---

<div align="center">
Made with ⬡ and Python
</div>
