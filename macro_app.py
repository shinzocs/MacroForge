import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import json
import os
import sys
import ctypes

# ── High-resolution sleep for Windows ────────────────────────────────────────
# Sets Windows timer resolution to 1ms so time.sleep() is accurate.
try:
    ctypes.windll.winmm.timeBeginPeriod(1)
except Exception:
    pass

def precise_sleep(seconds: float, stop_event=None):
    if seconds <= 0:
        return
    deadline = time.perf_counter() + seconds
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return
        if stop_event and stop_event.is_set():
            return
        time.sleep(min(remaining, 0.001))

try:
    from pynput import keyboard as kb, mouse as ms
    from pynput.keyboard import Key, Controller as KbController
    from pynput.mouse import Button, Controller as MsController
except ImportError:
    os.system(f"{sys.executable} -m pip install pynput")
    from pynput import keyboard as kb, mouse as ms
    from pynput.keyboard import Key, Controller as KbController
    from pynput.mouse import Button, Controller as MsController

keyboard_ctrl = KbController()
mouse_ctrl    = MsController()

# ── Persist save to AppData (writable without admin rights) ──────────────────
def _app_dir():
    # When installed, save to %APPDATA%\MacroForge so no admin is needed
    appdata = os.environ.get("APPDATA")
    if appdata:
        save_dir = os.path.join(appdata, "MacroForge")
        os.makedirs(save_dir, exist_ok=True)
        return save_dir
    # Fallback: next to the script/exe
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

SAVE_PATH = os.path.join(_app_dir(), "macros.json")

# ── Theme ─────────────────────────────────────────────────────────────────────
DARK_BG  = "#0f0f13"
PANEL_BG = "#16161e"
CARD_BG  = "#1e1e2a"
ACCENT   = "#7c6af7"
ACCENT2  = "#a78bfa"
SUCCESS  = "#4ade80"
DANGER   = "#f87171"
WARN     = "#fbbf24"
TEXT     = "#e2e2f0"
SUBTEXT  = "#8888aa"
BORDER   = "#2a2a3d"
HOVER    = "#252535"
GRP_CLR  = "#fbbf24"

FONT_TITLE = ("Courier New", 18, "bold")
FONT_HEAD  = ("Courier New", 11, "bold")
FONT_MONO  = ("Courier New", 10)
FONT_SMALL = ("Courier New", 9)
FONT_BTN   = ("Courier New", 10, "bold")

SPECIAL_KEYS = {
    "space": Key.space, "enter": Key.enter, "tab": Key.tab,
    "shift": Key.shift, "ctrl": Key.ctrl, "alt": Key.alt,
    "backspace": Key.backspace, "delete": Key.delete,
    "esc": Key.esc, "up": Key.up, "down": Key.down,
    "left": Key.left, "right": Key.right,
    **{f"f{i}": getattr(Key, f"f{i}") for i in range(1, 13)},
}

def parse_key(key_str):
    k = key_str.strip().lower()
    return SPECIAL_KEYS.get(k, k[0] if k else 'z')


# ── Data model ────────────────────────────────────────────────────────────────
class Step:
    def __init__(self, step_type="key", key="z", delay=0.05, repeat=1,
                 mouse_btn="left", x=None, y=None):
        self.step_type = step_type
        self.key       = key
        self.delay     = delay
        self.repeat    = repeat
        self.mouse_btn = mouse_btn
        self.x         = x
        self.y         = y

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        s = cls()
        s.__dict__.update(d)
        return s


class Macro:
    def __init__(self, name="New Macro"):
        self.name       = name
        self.steps      = []
        self.loop       = False
        self.loop_delay = 0.0

    def to_dict(self):
        return {"name": self.name,
                "loop": self.loop, "loop_delay": self.loop_delay,
                "steps": [s.to_dict() for s in self.steps]}

    @classmethod
    def from_dict(cls, d):
        m = cls(d.get("name", "Macro"))
        m.loop       = d.get("loop", False)
        m.loop_delay = d.get("loop_delay", 0.0)
        m.steps      = [Step.from_dict(s) for s in d.get("steps", [])]
        return m


class Group:
    def __init__(self, name="New Group"):
        self.name   = name
        self.macros = []
        self.open   = True

    def to_dict(self):
        return {"name": self.name, "open": self.open,
                "macros": [m.to_dict() for m in self.macros]}

    @classmethod
    def from_dict(cls, d):
        g = cls(d.get("name", "Group"))
        g.open   = d.get("open", True)
        g.macros = [Macro.from_dict(m) for m in d.get("macros", [])]
        return g


# ── App ───────────────────────────────────────────────────────────────────────
class MacroApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MACROFORGE")
        self.geometry("1020x700")
        self.minsize(820, 580)
        self.configure(bg=DARK_BG)

        # Icon
        try:
            base = getattr(sys, '_MEIPASS', _app_dir())
            ip = os.path.join(base, "icon.png")
            if os.path.exists(ip):
                self._icon_img = tk.PhotoImage(file=ip)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

        self.groups    = []
        self.sel_group = None
        self.sel_macro = None
        self.running   = {}
        self.hotkey_listener = None
        self._loading   = False
        self._capturing = False
        self._tree_items = []
        self.global_hotkey = ""   # single hotkey that runs the selected macro

        self._build_ui()
        self._load()
        self._refresh_sidebar()
        self._start_hotkey_listener()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================================
    #  UI BUILD
    # =========================================================================

    def _build_ui(self):
        bar = tk.Frame(self, bg=PANEL_BG, height=54)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text="⬡ MACROFORGE", font=FONT_TITLE,
                 bg=PANEL_BG, fg=ACCENT2).pack(side="left", padx=18, pady=10)
        tk.Label(bar, text="windows automation toolkit",
                 font=FONT_SMALL, bg=PANEL_BG, fg=SUBTEXT).pack(side="left")
        sf = tk.Frame(bar, bg=PANEL_BG)
        sf.pack(side="right", padx=16)
        self.status_dot = tk.Label(sf, text="●", font=("Courier New", 13),
                                   bg=PANEL_BG, fg=SUBTEXT)
        self.status_dot.pack(side="left")
        self.status_lbl = tk.Label(sf, text="IDLE", font=FONT_SMALL,
                                   bg=PANEL_BG, fg=SUBTEXT)
        self.status_lbl.pack(side="left", padx=4)

        # Global hotkey in title bar
        tk.Label(bar, text="HOTKEY", font=FONT_SMALL,
                 bg=PANEL_BG, fg=SUBTEXT).pack(side="right", padx=(0, 4))
        self._btn(bar, "✕", self._clear_hotkey, DANGER, small=True).pack(side="right", padx=(0, 6))
        self.hotkey_var = tk.StringVar(value="click to bind")
        self.hotkey_btn = tk.Button(
            bar, textvariable=self.hotkey_var, font=FONT_MONO,
            bg=CARD_BG, fg=SUBTEXT, activebackground=HOVER,
            activeforeground=ACCENT2, relief="flat", bd=0,
            padx=10, pady=4, cursor="hand2", width=10,
            command=self._start_hotkey_capture
        )
        self.hotkey_btn.pack(side="right", padx=(0, 4))

        body = tk.Frame(self, bg=DARK_BG)
        body.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        sb = tk.Frame(body, bg=PANEL_BG, width=230)
        sb.pack(side="left", fill="y", padx=(0, 8))
        sb.pack_propagate(False)
        self._build_sidebar(sb)

        ed = tk.Frame(body, bg=DARK_BG)
        ed.pack(side="left", fill="both", expand=True)
        self._build_editor(ed)

    # ── SIDEBAR ──────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        top = tk.Frame(parent, bg=PANEL_BG)
        top.pack(fill="x", padx=8, pady=(10, 4))
        tk.Label(top, text="GROUPS & MACROS", font=FONT_HEAD,
                 bg=PANEL_BG, fg=ACCENT).pack(side="left")

        btn_row = tk.Frame(parent, bg=PANEL_BG)
        btn_row.pack(fill="x", padx=8, pady=(0, 6))
        self._btn(btn_row, "+ GROUP", self._new_group, GRP_CLR, small=True).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "+ MACRO", self._new_macro, ACCENT,  small=True).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "✕ DEL",  self._delete_selected, DANGER, small=True).pack(side="left")

        tf = tk.Frame(parent, bg=PANEL_BG)
        tf.pack(fill="both", expand=True, padx=6)

        sb_scroll = tk.Scrollbar(tf, bg=PANEL_BG, troughcolor=CARD_BG, highlightthickness=0)
        sb_scroll.pack(side="right", fill="y")

        self.tree = tk.Listbox(
            tf, bg=CARD_BG, fg=TEXT, font=FONT_MONO,
            selectbackground=ACCENT, selectforeground="white",
            activestyle="none", relief="flat", bd=0,
            highlightthickness=0, yscrollcommand=sb_scroll.set
        )
        self.tree.pack(fill="both", expand=True)
        sb_scroll.config(command=self.tree.yview)
        self.tree.bind("<<ListboxSelect>>", self._on_tree_select)
        self.tree.bind("<Double-Button-1>",  self._on_tree_double)

        bot = tk.Frame(parent, bg=PANEL_BG)
        bot.pack(fill="x", padx=8, pady=8)
        self._btn(bot, "💾 SAVE ALL", self._save, WARN).pack(fill="x", pady=2)

    # ── EDITOR ───────────────────────────────────────────────────────────────

    def _build_editor(self, parent):
        self.placeholder = tk.Frame(parent, bg=DARK_BG)
        self.placeholder.pack(fill="both", expand=True)
        tk.Label(self.placeholder, text="⬡", font=("Courier New", 48),
                 bg=DARK_BG, fg=BORDER).pack(expand=True)
        tk.Label(self.placeholder, text="select or create a macro",
                 font=FONT_SMALL, bg=DARK_BG, fg=SUBTEXT).pack()

        self.editor = tk.Frame(parent, bg=DARK_BG)

        # meta
        meta = tk.Frame(self.editor, bg=PANEL_BG)
        meta.pack(fill="x", pady=(0, 6))
        meta.columnconfigure(1, weight=1)

        tk.Label(meta, text="NAME", font=FONT_SMALL, bg=PANEL_BG, fg=SUBTEXT
                 ).grid(row=0, column=0, padx=(12, 4), pady=8, sticky="w")
        self.name_var = tk.StringVar()
        tk.Entry(meta, textvariable=self.name_var, font=FONT_MONO,
                 bg=CARD_BG, fg=TEXT, insertbackground=ACCENT2,
                 relief="flat", bd=4).grid(row=0, column=1, padx=(4, 12), pady=8, sticky="ew")
        self.name_var.trace_add("write", lambda *_: self._sync_name())

        lr = tk.Frame(meta, bg=PANEL_BG)
        lr.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")

        self.loop_var = tk.BooleanVar()
        tk.Checkbutton(lr, text="Loop macro", variable=self.loop_var,
                       bg=PANEL_BG, fg=TEXT, selectcolor=CARD_BG,
                       activebackground=PANEL_BG, font=FONT_SMALL,
                       command=self._sync_loop).pack(side="left")
        tk.Label(lr, text="  loop delay (s):", font=FONT_SMALL,
                 bg=PANEL_BG, fg=SUBTEXT).pack(side="left")
        self.loop_delay_var = tk.StringVar(value="0.0")
        tk.Entry(lr, textvariable=self.loop_delay_var, font=FONT_MONO,
                 bg=CARD_BG, fg=TEXT, insertbackground=ACCENT2,
                 relief="flat", bd=4, width=6).pack(side="left", padx=6)
        self.loop_delay_var.trace_add("write", lambda *_: self._sync_loop())

        # steps header
        sh = tk.Frame(self.editor, bg=DARK_BG)
        sh.pack(fill="x", pady=(0, 4))
        tk.Label(sh, text="SEQUENCE STEPS", font=FONT_HEAD,
                 bg=DARK_BG, fg=ACCENT).pack(side="left")
        af = tk.Frame(sh, bg=DARK_BG)
        af.pack(side="right")
        self._btn(af, "+ KEY",   self._add_key_step,   ACCENT,  small=True).pack(side="left", padx=4)
        self._btn(af, "+ CLICK", self._add_click_step, ACCENT2, small=True).pack(side="left")

        # steps canvas — both scrollbars
        sc_wrap = tk.Frame(self.editor, bg=DARK_BG)
        sc_wrap.pack(fill="both", expand=True)

        self.steps_vscroll = tk.Scrollbar(sc_wrap, orient="vertical",
                                           bg=PANEL_BG, troughcolor=CARD_BG,
                                           highlightthickness=0)
        self.steps_vscroll.pack(side="right", fill="y")

        self.steps_hscroll = tk.Scrollbar(sc_wrap, orient="horizontal",
                                           bg=PANEL_BG, troughcolor=CARD_BG,
                                           highlightthickness=0)
        self.steps_hscroll.pack(side="bottom", fill="x")

        self.steps_canvas = tk.Canvas(sc_wrap, bg=DARK_BG, highlightthickness=0,
                                       yscrollcommand=self.steps_vscroll.set,
                                       xscrollcommand=self.steps_hscroll.set)
        self.steps_canvas.pack(fill="both", expand=True)
        self.steps_vscroll.config(command=self.steps_canvas.yview)
        self.steps_hscroll.config(command=self.steps_canvas.xview)

        self.steps_inner = tk.Frame(self.steps_canvas, bg=DARK_BG)
        self._steps_win  = self.steps_canvas.create_window(
            (0, 0), window=self.steps_inner, anchor="nw")

        self.steps_inner.bind("<Configure>", self._on_steps_cfg)

        # single run bar
        rb = tk.Frame(self.editor, bg=PANEL_BG, height=50)
        rb.pack(fill="x", pady=(6, 0))
        rb.pack_propagate(False)
        self._btn(rb, "▶  RUN MACRO", self._run_selected,  SUCCESS).pack(side="left", padx=12, pady=8)
        self._btn(rb, "■  STOP",      self._stop_selected, DANGER ).pack(side="left", padx=4,  pady=8)
        tk.Label(rb, text="or press the assigned hotkey from any window",
                 font=FONT_SMALL, bg=PANEL_BG, fg=SUBTEXT).pack(side="left", padx=10)

    # =========================================================================
    #  SIDEBAR TREE
    # =========================================================================

    def _refresh_sidebar(self):
        self.tree.delete(0, "end")
        self._tree_items = []
        for gi, g in enumerate(self.groups):
            arrow = "▼" if g.open else "▶"
            self.tree.insert("end", f"{arrow} 📁 {g.name}")
            self._tree_items.append(("group", gi, None))
            self.tree.itemconfig("end", fg=GRP_CLR)
            if g.open:
                for mi, m in enumerate(g.macros):
                    self.tree.insert("end", f"    ⚡ {m.name}")
                    self._tree_items.append(("macro", gi, mi))
        self._restore_selection()

    def _restore_selection(self):
        if self.sel_group is None:
            return
        for i, (kind, gi, mi) in enumerate(self._tree_items):
            if kind == "macro" and gi == self.sel_group and mi == self.sel_macro:
                self.tree.selection_set(i); self.tree.see(i); return
            if kind == "group" and gi == self.sel_group and self.sel_macro is None:
                self.tree.selection_set(i); self.tree.see(i); return

    def _on_tree_select(self, event=None):
        sel = self.tree.curselection()
        if not sel:
            return
        kind, gi, mi = self._tree_items[sel[0]]
        if kind == "macro":
            self.sel_group = gi
            self.sel_macro = mi
            self._load_editor(self.groups[gi].macros[mi])
        else:
            self.sel_group = gi
            self.sel_macro = None
            self._hide_editor()

    def _on_tree_double(self, event=None):
        sel = self.tree.curselection()
        if not sel:
            return
        kind, gi, _ = self._tree_items[sel[0]]
        if kind == "group":
            self.groups[gi].open = not self.groups[gi].open
            self._refresh_sidebar()

    # =========================================================================
    #  CRUD
    # =========================================================================

    def _new_group(self):
        name = simpledialog.askstring("New Group", "Group name:",
                                       initialvalue="My Game", parent=self)
        if not name:
            return
        self.groups.append(Group(name))
        self.sel_group = len(self.groups) - 1
        self.sel_macro = None
        self._refresh_sidebar()
        self._hide_editor()

    def _new_macro(self):
        if not self.groups:
            messagebox.showinfo("No Group", "Create a group first!", parent=self)
            return
        gi = self.sel_group if self.sel_group is not None else 0
        m  = Macro(f"Macro {len(self.groups[gi].macros) + 1}")
        self.groups[gi].macros.append(m)
        self.sel_group = gi
        self.sel_macro = len(self.groups[gi].macros) - 1
        self._refresh_sidebar()
        self._load_editor(m)

    def _delete_selected(self):
        if self.sel_group is None:
            return
        if self.sel_macro is not None:
            self._stop_by_key((self.sel_group, self.sel_macro))
            self.groups[self.sel_group].macros.pop(self.sel_macro)
            self.sel_macro = None
            self._hide_editor()
        else:
            for mi in range(len(self.groups[self.sel_group].macros)):
                self._stop_by_key((self.sel_group, mi))
            self.groups.pop(self.sel_group)
            self.sel_group = None
            self._hide_editor()
        self._refresh_sidebar()

    # =========================================================================
    #  EDITOR LOAD / SYNC
    # =========================================================================

    def _load_editor(self, macro):
        self.placeholder.pack_forget()
        self.editor.pack(fill="both", expand=True)
        self._loading = True
        self.name_var.set(macro.name)
        self.loop_var.set(macro.loop)
        self.loop_delay_var.set(str(macro.loop_delay))
        self._loading = False
        self._rebuild_steps(macro)

    def _hide_editor(self):
        self.editor.pack_forget()
        self.placeholder.pack(fill="both", expand=True)

    def _current_macro(self):
        if self.sel_group is None or self.sel_macro is None:
            return None
        return self.groups[self.sel_group].macros[self.sel_macro]

    def _sync_name(self):
        if self._loading: return
        m = self._current_macro()
        if not m: return
        m.name = self.name_var.get()
        self._refresh_sidebar()

    def _start_hotkey_capture(self):
        self.hotkey_var.set("[ press key... ]")
        self.hotkey_btn.config(fg=WARN, bg=HOVER)
        self._capturing = True

        def on_press(key):
            if not self._capturing:
                return False
            try:
                k = key.char.lower() if hasattr(key, 'char') and key.char \
                    else key.name.lower()
            except:
                return False
            self._capturing = False
            self.global_hotkey = k
            self.after(0, lambda: self._finish_hotkey_capture(k))
            return False

        capture_listener = kb.Listener(on_press=on_press)
        capture_listener.daemon = True
        capture_listener.start()

    def _finish_hotkey_capture(self, key_name):
        self.hotkey_var.set(key_name)
        self.hotkey_btn.config(fg=ACCENT2, bg=CARD_BG)
        self._restart_hotkey_listener()
        self._save()

    def _clear_hotkey(self):
        self.global_hotkey = ""
        self.hotkey_var.set("click to bind")
        self.hotkey_btn.config(fg=SUBTEXT, bg=CARD_BG)
        self._restart_hotkey_listener()

    def _sync_loop(self):
        if self._loading: return
        m = self._current_macro()
        if not m: return
        m.loop = self.loop_var.get()
        try:    m.loop_delay = float(self.loop_delay_var.get())
        except: pass

    # =========================================================================
    #  STEPS
    # =========================================================================

    def _on_steps_cfg(self, e=None):
        self.steps_canvas.configure(scrollregion=self.steps_canvas.bbox("all"))

    def _rebuild_steps(self, macro):
        for w in self.steps_inner.winfo_children():
            w.destroy()
        if not macro.steps:
            tk.Label(self.steps_inner,
                     text="no steps yet — use + KEY or + CLICK above",
                     font=FONT_SMALL, bg=DARK_BG, fg=SUBTEXT).pack(pady=20)
            return
        for i, step in enumerate(macro.steps):
            self._build_step_row(i, step, macro)

    def _build_step_row(self, i, step, macro):
        color = ACCENT if step.step_type == "key" else ACCENT2
        tag   = "[KEY]" if step.step_type == "key" else "[CLK]"

        row = tk.Frame(self.steps_inner, bg=CARD_BG, pady=4)
        row.pack(anchor="w", pady=3, padx=2)

        tk.Label(row, text=f"  {i+1:02d}  {tag}", font=FONT_MONO,
                 bg=CARD_BG, fg=color, width=10).pack(side="left")

        fields = tk.Frame(row, bg=CARD_BG)
        fields.pack(side="left", padx=8)

        if step.step_type == "key":
            tk.Label(fields, text="key:", font=FONT_SMALL,
                     bg=CARD_BG, fg=SUBTEXT).pack(side="left")
            kv = tk.StringVar(value=step.key)
            tk.Entry(fields, textvariable=kv, font=FONT_MONO, bg=DARK_BG, fg=TEXT,
                     insertbackground=ACCENT2, relief="flat", bd=3,
                     width=8).pack(side="left", padx=4)
            kv.trace_add("write", lambda *_, v=kv, s=step: self._upd(s, "key", v.get()))
        else:
            tk.Label(fields, text="btn:", font=FONT_SMALL,
                     bg=CARD_BG, fg=SUBTEXT).pack(side="left")
            bv = tk.StringVar(value=step.mouse_btn)
            ttk.Combobox(fields, textvariable=bv, values=["left","right","middle"],
                         font=FONT_SMALL, width=7,
                         state="readonly").pack(side="left", padx=4)
            bv.trace_add("write", lambda *_, v=bv, s=step: self._upd(s, "mouse_btn", v.get()))

            for lbl, attr in [("x:", "x"), ("y:", "y")]:
                tk.Label(fields, text=lbl, font=FONT_SMALL,
                         bg=CARD_BG, fg=SUBTEXT).pack(side="left")
                val = "" if getattr(step, attr) is None else str(getattr(step, attr))
                ev  = tk.StringVar(value=val)
                tk.Entry(fields, textvariable=ev, font=FONT_MONO, bg=DARK_BG, fg=TEXT,
                         insertbackground=ACCENT2, relief="flat", bd=3,
                         width=6).pack(side="left", padx=2)
                ev.trace_add("write",
                             lambda *_, v=ev, s=step, a=attr: self._upd(s, a, v.get()))

            self._btn(fields, "📍 pick",
                      lambda s=step, m=macro: self._pick_coords(s, m),
                      WARN, small=True).pack(side="left", padx=4)

        tk.Label(fields, text="delay(s):", font=FONT_SMALL,
                 bg=CARD_BG, fg=SUBTEXT).pack(side="left")
        dv = tk.StringVar(value=str(step.delay))
        tk.Entry(fields, textvariable=dv, font=FONT_MONO, bg=DARK_BG, fg=TEXT,
                 insertbackground=ACCENT2, relief="flat", bd=3,
                 width=6).pack(side="left", padx=2)
        dv.trace_add("write", lambda *_, v=dv, s=step: self._upd(s, "delay", v.get()))

        tk.Label(fields, text="×", font=FONT_SMALL,
                 bg=CARD_BG, fg=SUBTEXT).pack(side="left")
        rv = tk.StringVar(value=str(step.repeat))
        tk.Entry(fields, textvariable=rv, font=FONT_MONO, bg=DARK_BG, fg=TEXT,
                 insertbackground=ACCENT2, relief="flat", bd=3,
                 width=5).pack(side="left", padx=2)
        rv.trace_add("write", lambda *_, v=rv, s=step: self._upd(s, "repeat", v.get()))

        ctrl = tk.Frame(row, bg=CARD_BG)
        ctrl.pack(side="left", padx=8)
        if i > 0:
            self._btn(ctrl, "▲",
                      lambda i=i, m=macro: self._move_step(i, -1, m),
                      SUBTEXT, small=True).pack(side="left")
        if i < len(macro.steps) - 1:
            self._btn(ctrl, "▼",
                      lambda i=i, m=macro: self._move_step(i, 1, m),
                      SUBTEXT, small=True).pack(side="left")
        self._btn(ctrl, "✕",
                  lambda i=i, m=macro: self._remove_step(i, m),
                  DANGER, small=True).pack(side="left", padx=(4, 0))

    def _upd(self, step, field, value):
        if field == "delay":
            try:    step.delay = float(value)
            except: pass
        elif field == "repeat":
            try:    step.repeat = max(1, int(value))
            except: pass
        elif field in ("x", "y"):
            try:    setattr(step, field, int(value) if value.strip() else None)
            except: pass
        else:
            setattr(step, field, value)

    def _add_key_step(self):
        m = self._current_macro()
        if not m: return
        m.steps.append(Step("key", "z", 0.05, 1))
        self._rebuild_steps(m)

    def _add_click_step(self):
        m = self._current_macro()
        if not m: return
        m.steps.append(Step("click", "left", 0.05, 1))
        self._rebuild_steps(m)

    def _remove_step(self, i, macro):
        macro.steps.pop(i)
        self._rebuild_steps(macro)

    def _move_step(self, i, d, macro):
        j = i + d
        macro.steps[i], macro.steps[j] = macro.steps[j], macro.steps[i]
        self._rebuild_steps(macro)

    def _pick_coords(self, step, macro):
        win = tk.Toplevel(self, bg=PANEL_BG)
        win.title("Pick Coordinates")
        win.geometry("320x160")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        tk.Label(win, text="Move your mouse to the target\nlocation and wait...",
                 font=FONT_MONO, bg=PANEL_BG, fg=TEXT, justify="center").pack(pady=16)
        cl = tk.Label(win, text="3", font=("Courier New", 36, "bold"),
                      bg=PANEL_BG, fg=ACCENT2)
        cl.pack()
        def cd(n):
            if n == 0:
                step.x, step.y = mouse_ctrl.position
                win.destroy()
                self._rebuild_steps(macro)
            else:
                cl.config(text=str(n))
                win.after(1000, lambda: cd(n - 1))
        cd(3)

    # =========================================================================
    #  MACRO EXECUTION  — Run button now respects loop flag correctly
    # =========================================================================

    def _run_macro(self, gi, mi):
        key   = (gi, mi)
        if key in self.running:
            return
        macro = self.groups[gi].macros[mi]
        stop  = threading.Event()
        self.running[key] = stop
        self.after(0, self._set_status, f"RUNNING: {macro.name}", SUCCESS)

        def worker():
            try:
                while not stop.is_set():
                    step_start = time.perf_counter()
                    for step in macro.steps:
                        if stop.is_set(): break
                        for _ in range(step.repeat):
                            if stop.is_set(): break
                            t0 = time.perf_counter()
                            if step.step_type == "key":
                                k = parse_key(step.key)
                                keyboard_ctrl.press(k)
                                keyboard_ctrl.release(k)
                            else:
                                btn = {"left":   Button.left,
                                       "right":  Button.right,
                                       "middle": Button.middle
                                       }.get(step.mouse_btn, Button.left)
                                if step.x is not None and step.y is not None:
                                    mouse_ctrl.position = (step.x, step.y)
                                mouse_ctrl.click(btn)
                            # Subtract time spent executing so delay is wall-clock accurate
                            elapsed = time.perf_counter() - t0
                            adjusted = max(0.0, step.delay - elapsed)
                            precise_sleep(adjusted, stop)
                    # after one full pass — only loop if flag is set
                    if not macro.loop:
                        break
                    if stop.is_set(): break
                    loop_elapsed = time.perf_counter() - step_start
                    precise_sleep(max(0.0, macro.loop_delay - loop_elapsed), stop)
            finally:
                self.running.pop(key, None)
                self.after(0, self._set_status, "IDLE", SUBTEXT)

        threading.Thread(target=worker, daemon=True).start()

    def _stop_by_key(self, key):
        ev = self.running.pop(key, None)
        if ev: ev.set()

    def _run_selected(self):
        if self.sel_group is None or self.sel_macro is None:
            return
        key = (self.sel_group, self.sel_macro)
        if key in self.running:
            self._stop_by_key(key)   # toggle off if already running
        else:
            self._run_macro(self.sel_group, self.sel_macro)

    def _stop_selected(self):
        if self.sel_group is None or self.sel_macro is None:
            return
        self._stop_by_key((self.sel_group, self.sel_macro))
        self._set_status("IDLE", SUBTEXT)

    # =========================================================================
    #  HOTKEY LISTENER
    # =========================================================================

    def _start_hotkey_listener(self):
        if self.hotkey_listener:
            try: self.hotkey_listener.stop()
            except: pass

        def on_press(key):
            if not self.global_hotkey:
                return
            try:
                k = key.char.lower() if hasattr(key, 'char') and key.char \
                    else key.name.lower()
            except: return
            if k == self.global_hotkey:
                if self.sel_group is None or self.sel_macro is None:
                    return
                rkey = (self.sel_group, self.sel_macro)
                if rkey in self.running:
                    self._stop_by_key(rkey)
                    self.after(0, self._set_status, "IDLE", SUBTEXT)
                else:
                    self._run_macro(self.sel_group, self.sel_macro)

        self.hotkey_listener = kb.Listener(on_press=on_press)
        self.hotkey_listener.daemon = True
        self.hotkey_listener.start()

    def _restart_hotkey_listener(self):
        self._start_hotkey_listener()

    # =========================================================================
    #  SAVE / LOAD
    # =========================================================================

    def _save(self):
        data = {
            "global_hotkey": self.global_hotkey,
            "groups": [g.to_dict() for g in self.groups]
        }
        try:
            with open(SAVE_PATH, "w") as f:
                json.dump(data, f, indent=2)
            self._set_status("SAVED ✓", SUCCESS)
            self.after(2000, self._set_status, "IDLE", SUBTEXT)
        except Exception as e:
            messagebox.showerror("Save Error", str(e), parent=self)

    def _load(self):
        if not os.path.exists(SAVE_PATH):
            return
        try:
            with open(SAVE_PATH) as f:
                data = json.load(f)
            # Support both old list format and new dict format
            if isinstance(data, list):
                self.groups = [Group.from_dict(d) for d in data]
            else:
                self.global_hotkey = data.get("global_hotkey", "")
                self.groups = [Group.from_dict(d) for d in data.get("groups", [])]
            # Update hotkey button display
            if self.global_hotkey:
                self.hotkey_var.set(self.global_hotkey)
                self.hotkey_btn.config(fg=ACCENT2, bg=CARD_BG)
        except Exception as e:
            print(f"Load error: {e}")

    def _on_close(self):
        self._save()   # auto-save on exit
        self.destroy()

    # =========================================================================
    #  HELPERS
    # =========================================================================

    def _btn(self, parent, text, cmd, color, small=False):
        f = FONT_SMALL if small else FONT_BTN
        p = (6, 3)    if small else (10, 5)
        b = tk.Button(parent, text=text, command=cmd, font=f,
                      bg=CARD_BG, fg=color, activebackground=HOVER,
                      activeforeground=color, relief="flat", bd=0,
                      padx=p[0], pady=p[1], cursor="hand2")
        b.bind("<Enter>", lambda e: b.config(bg=HOVER))
        b.bind("<Leave>", lambda e: b.config(bg=CARD_BG))
        return b

    def _set_status(self, text, color=SUBTEXT):
        self.status_lbl.config(text=text, fg=color)
        self.status_dot.config(fg=color)


if __name__ == "__main__":
    app = MacroApp()
    app.mainloop()
