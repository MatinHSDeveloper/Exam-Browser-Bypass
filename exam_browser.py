"""
Text Expander + Browser Launcher (FIXED)
"""

import tkinter as tk
import threading
import time
import os
import webview
from pynput import keyboard
from pynput.keyboard import Key, Controller

try:
    import pystray
    from pystray import MenuItem as item
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

# ─── GLOBAL ─────────────────────────────────────────────
saved_text = ""
buffer = ""
clipboard_win_open = False
browser_open = False
webview_window = None
tray_icon = None
controller = Controller()
browser_created = False

root = None   # ✅ FIX مهم

TRIGGER_TYPE = "type"
TRIGGER_OPEN = "open"
TRIGGER_CLOSE = "sik"

# ─── TRAY ───────────────────────────────────────────────
def make_combined_icon(b_on: bool, c_on: bool):
    img = Image.new("RGBA", (64, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 4, 28, 28], fill="#2ecc71" if b_on else "#e74c3c")
    draw.ellipse([36, 4, 62, 28], fill="#2ecc71" if c_on else "#e74c3c")
    return img

def update_tray():
    if TRAY_AVAILABLE and tray_icon:
        tray_icon.icon = make_combined_icon(browser_open, bool(saved_text))

def start_tray():
    global tray_icon
    if not TRAY_AVAILABLE:
        return
    tray_icon = pystray.Icon(
        "TextExpander",
        make_combined_icon(False, False),
        "Text Expander"
    )
    tray_icon.run()

# ─── BROWSER ────────────────────────────────────────────
class BrowserWindow:
    def __init__(self):
        self.window = None

    def start(self):
        global browser_open, browser_created

        if browser_created:
            return

        browser_created = True
        browser_open = True
        update_tray()

        navigation_js = """
        var toolbar = document.createElement('div');
        toolbar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 50px;
            background: #2d2d2d;
            display: flex;
            align-items: center;
            padding: 0 10px;
            gap: 8px;
            z-index: 999999;
            font-family: Arial;
        `;

        var backBtn = document.createElement('button');
        backBtn.innerHTML = '◀';
        backBtn.onclick = () => window.history.back();

        var forwardBtn = document.createElement('button');
        forwardBtn.innerHTML = '▶';
        forwardBtn.onclick = () => window.history.forward();

        var homeBtn = document.createElement('button');
        homeBtn.innerHTML = '🏠';
        homeBtn.onclick = () => window.location.href = 'https://www.google.com';

        var refreshBtn = document.createElement('button');
        refreshBtn.innerHTML = '🔄';
        refreshBtn.onclick = () => window.location.reload();

        var urlBar = document.createElement('input');
        urlBar.style.flex = "1";
        urlBar.onkeypress = (e) => {
            if (e.key === 'Enter') {
                let url = urlBar.value;
                if (!url.startsWith('http'))
                    url = 'https://www.google.com/search?q=' + encodeURIComponent(url);
                window.location.href = url;
            }
        };

        setInterval(() => urlBar.value = window.location.href, 500);

        toolbar.appendChild(backBtn);
        toolbar.appendChild(forwardBtn);
        toolbar.appendChild(homeBtn);
        toolbar.appendChild(refreshBtn);
        toolbar.appendChild(urlBar);

        document.body.prepend(toolbar);
        document.body.style.marginTop = "50px";
        """

        self.window = webview.create_window(
            "Browser",
            "https://www.google.com",
            width=1300,
            height=800
        )

        def on_loaded():
            self.window.evaluate_js(navigation_js)

        def on_closed():
            global browser_open, browser_created
            browser_open = False
            browser_created = False
            update_tray()

        self.window.events.loaded += on_loaded
        self.window.events.closed += on_closed

        # ❌ NO threading, MUST run here
        webview.start()

    def close(self):
        if self.window:
            try:
                self.window.destroy()
            except:
                pass

browser_instance = None

def get_browser():
    global browser_instance
    if browser_instance is None:
        browser_instance = BrowserWindow()
    return browser_instance

# ─── FIX اصلی اینجاست ────────────────────────────────
def open_browser_window():
    if not browser_open:
        browser = get_browser()
        root.after(0, browser.start)   # ✅ FIX

def close_browser_window():
    global browser_open, browser_created
    browser = get_browser()
    browser.close()
    browser_open = False
    browser_created = False
    update_tray()

# ─── KEYBOARD EXPANDER ────────────────────────────────
def erase_word(word):
    time.sleep(0.05)
    for _ in range(len(word)):
        controller.press(Key.backspace)
        controller.release(Key.backspace)

def type_saved_text():
    if not saved_text:
        return
    erase_word(TRIGGER_TYPE)
    time.sleep(0.05)
    for c in saved_text:
        if c == "\n":
            controller.press(Key.enter)
            controller.release(Key.enter)
        else:
            controller.type(c)

def on_press(key):
    global buffer
    try:
        ch = key.char
    except:
        buffer = ""
        return

    buffer += ch
    buffer = buffer[-20:]

    if buffer.endswith(TRIGGER_TYPE):
        buffer = ""
        threading.Thread(target=type_saved_text, daemon=True).start()

    elif buffer.endswith(TRIGGER_OPEN):
        buffer = ""
        root.after(0, open_browser_window)

    elif buffer.endswith(TRIGGER_CLOSE):
        buffer = ""
        root.after(0, close_browser_window)

# ─── SAVE WINDOW ───────────────────────────────────────
def open_save_window():
    global clipboard_win_open, saved_text
    if clipboard_win_open:
        return
    clipboard_win_open = True

    win = tk.Toplevel(root)
    win.title("Clipboard")
    win.geometry("520x340")

    text = tk.Text(win)
    text.pack(fill="both", expand=True)

    if saved_text:
        text.insert("1.0", saved_text)

    def save():
        global saved_text
        saved_text = text.get("1.0", tk.END)
        win.destroy()

    tk.Button(win, text="Save", command=save).pack()

# ─── HOTKEY ───────────────────────────────────────────
def start_hotkey():
    keyboard.GlobalHotKeys({
        "<ctrl>+<alt>+v": lambda: root.after(0, open_save_window)
    }).start()

# ─── MAIN ─────────────────────────────────────────────
if __name__ == "__main__":
    kb = keyboard.Listener(on_press=on_press)
    kb.start()

    threading.Thread(target=start_hotkey, daemon=True).start()

    if TRAY_AVAILABLE:
        threading.Thread(target=start_tray, daemon=True).start()

    # ✅ MAIN ROOT
    root = tk.Tk()
    root.title("Text Expander")
    root.geometry("400x200")

    tk.Label(root,
        text="Active\n\nopen → browser\nsik → close\nCtrl+Alt+V → clipboard"
    ).pack(expand=True)

    root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

    root.mainloop()