#!/usr/bin/env python3
"""
F-list bulk image uploader.

Opens a normal browser window, lets you log in to F-list yourself, and then
does the "Choose file -> Add Image" routine for every picture in a folder,
one at a time, so you don't have to.

Your password never passes through this program: you type it into the real
F-list website in the browser window, exactly as you normally would.

Run it with no arguments for the point-and-click window, or see
`python flist_uploader.py --help` for the command-line version.
"""

import argparse
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# F-list's rules, from the Images section of the character edit page.
# ---------------------------------------------------------------------------
MAX_IMAGES = 50                 # "Images (Limit: 50)"
MAX_BYTES = 2_000_000           # "less than 2.0MB"
MAX_PIXELS = 4000               # "smaller than 4000 px in width and/or height"
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".gif"}

START_URL = "https://www.f-list.net/"
PROFILE_DIR = Path.home() / ".flist-uploader-browser"   # keeps you logged in between runs
PAUSE_BETWEEN_UPLOADS = 0.5     # seconds; be gentle with the site
UPLOAD_TIMEOUT = 90             # seconds to wait for one upload to finish
ADD_BUTTON_TEXT = re.compile(r"^\s*add\s+image\s*$", re.I)


# ---------------------------------------------------------------------------
# Picking and checking files
# ---------------------------------------------------------------------------
def _natural_key(path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", path.name)]


def image_problem(path):
    """Return why F-list would reject this file, or None if it looks fine."""
    if path.suffix.lower() not in ALLOWED_EXTS:
        return "not a png/jpg/gif"
    size = path.stat().st_size
    if size >= MAX_BYTES:
        return f"too big ({size / 1_000_000:.1f} MB, must be under 2.0 MB)"
    try:
        from PIL import Image
    except ImportError:
        return None  # can't check dimensions without Pillow; let F-list decide
    try:
        with Image.open(path) as im:
            w, h = im.size
    except Exception:
        return "couldn't be opened as an image"
    if w >= MAX_PIXELS or h >= MAX_PIXELS:
        return f"too large ({w}x{h} px, must be under {MAX_PIXELS} px)"
    return None


def scan_folder(folder, limit=None):
    """Return (files_to_upload, [(file, reason), ...skipped]) in filename order."""
    folder = Path(folder)
    candidates = sorted((p for p in folder.iterdir()
                         if p.is_file() and p.suffix.lower() in ALLOWED_EXTS),
                        key=_natural_key)
    good, skipped = [], []
    for p in candidates:
        reason = image_problem(p)
        if reason:
            skipped.append((p, reason))
        else:
            good.append(p)
    cap = MAX_IMAGES if limit is None else max(0, min(limit, MAX_IMAGES))
    return good[:cap], skipped


# ---------------------------------------------------------------------------
# Driving the browser
# ---------------------------------------------------------------------------
class Stopped(Exception):
    pass


def launch_browser(pw, log):
    """Use the user's own Chrome or Edge if present, else Playwright's Chromium."""
    errors = []
    for channel in ("chrome", "msedge", None):
        profile = PROFILE_DIR / (channel or "chromium")
        try:
            ctx = pw.chromium.launch_persistent_context(
                str(profile), headless=False, channel=channel, no_viewport=True)
            log(f"Opened {'Google Chrome' if channel == 'chrome' else 'Microsoft Edge' if channel == 'msedge' else 'Chromium'}.")
            return ctx
        except Exception as e:
            errors.append(e)
    log("No Chrome or Edge found, downloading a browser for Playwright (one time only)...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=False)
    return pw.chromium.launch_persistent_context(
        str(PROFILE_DIR / "chromium"), headless=False, no_viewport=True)


def find_upload_controls(page):
    """Locate the image file input and its Add Image button, fresh, on any frame.

    Called before every upload because the controls move down the page (and
    may be recreated) each time an image is added.
    """
    for frame in page.frames:
        try:
            buttons = frame.get_by_role("button", name=ADD_BUTTON_TEXT)
            if buttons.count() == 0:
                buttons = frame.locator("input[value='Add Image' i], button:has-text('Add Image')")
            if buttons.count() == 0:
                continue
            button = buttons.last
            file_input = button.locator("xpath=ancestor::form[1]//input[@type='file']")
            if file_input.count() == 0:
                file_input = button.locator("xpath=preceding::input[@type='file'][1]")
            if file_input.count() == 0:
                continue
            return frame, file_input.last, button
        except Exception:
            continue  # frame navigated away mid-check
    return None


# F-list pops up "Image added successfully." after each upload. Old copies of
# the message are tagged before each click so only a fresh one counts.
_SUCCESS_MSG_JS = """(mark) => {
  const r = document.evaluate("//*[contains(text(), 'added successfully')]",
                              document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
  let fresh = 0;
  for (let i = 0; i < r.snapshotLength; i++) {
    const el = r.snapshotItem(i);
    if (mark) el.dataset.fluSeen = '1';
    else if (!el.dataset.fluSeen) fresh++;
  }
  return fresh;
}"""


def success_message_shown(page, mark_old=False):
    fresh = 0
    for frame in page.frames:
        try:
            fresh += frame.evaluate(_SUCCESS_MSG_JS, mark_old)
        except Exception:
            pass
    return fresh > 0


def count_page_images(page):
    """Number of pictures on the page; goes up when a new upload appears."""
    total = 0
    for frame in page.frames:
        try:
            total += frame.locator("img").count()
        except Exception:
            pass
    return total


def run_upload(files, log, wait_for_user, stop_event, start_url=START_URL, browser_factory=None):
    """Upload `files` one at a time. Returns (uploaded, failed) lists."""
    from playwright.sync_api import sync_playwright

    uploaded, failed = [], []

    def check_stop():
        if stop_event.is_set():
            raise Stopped()

    with sync_playwright() as pw:
        ctx = (browser_factory or launch_browser)(pw, log)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            dialogs = []

            def on_dialog(d):
                dialogs.append(d.message)
                try:
                    d.accept()
                except Exception:
                    pass

            # Every file upload the page sends, so we know when F-list has answered.
            uploads = []

            def on_response(r):
                try:
                    if r.request.method == "POST" and "multipart/form-data" in (
                            r.request.headers.get("content-type") or ""):
                        uploads.append(r)
                except Exception:
                    pass

            ctx.on("response", on_response)
            ctx.on("page", lambda p: p.on("dialog", on_dialog))
            page.on("dialog", on_dialog)
            page.goto(start_url)

            # Let the user log in and open the right page.
            while True:
                wait_for_user(
                    "In the browser window: log in to F-list, open your character's "
                    "EDIT page, and make sure the Images section with the "
                    "'Add Image' button is showing. Then press Continue.")
                check_stop()
                page = ctx.pages[-1]  # whichever tab they ended up in
                page.on("dialog", on_dialog)
                if find_upload_controls(page):
                    break
                # Maybe the Images section is just collapsed.
                try:
                    page.get_by_text(re.compile(r"Images\s*\(Limit", re.I)).first.click(timeout=2000)
                    page.wait_for_timeout(1000)
                    if find_upload_controls(page):
                        break
                except Exception:
                    pass
                log("Couldn't find the 'Add Image' button on that page. "
                    "Make sure you're on the character edit page with Images open.")

            consecutive_failures = 0
            for i, path in enumerate(files, 1):
                check_stop()
                log(f"[{i}/{len(files)}] Uploading {path.name} ...")
                controls = find_upload_controls(page)
                if not controls:
                    page.wait_for_timeout(3000)
                    controls = find_upload_controls(page)
                if not controls:
                    log("  Lost track of the 'Add Image' button, stopping here.")
                    failed.append(path)
                    break
                frame, file_input, button = controls
                before = count_page_images(page)
                success_message_shown(page, mark_old=True)
                dialogs.clear()
                uploads.clear()

                file_input.set_input_files(str(path))
                button.scroll_into_view_if_needed()
                button.click()

                result = wait_for_upload(page, before, dialogs, uploads, stop_event)
                if result == "ok":
                    log("  Done.")
                    uploaded.append(path)
                    consecutive_failures = 0
                elif result == "probably":
                    log("  Sent (couldn't double-check it appeared, but no error was shown).")
                    uploaded.append(path)
                    consecutive_failures = 0
                else:
                    log(f"  Failed: {result}")
                    failed.append(path)
                    consecutive_failures += 1
                    if consecutive_failures >= 2:
                        log("Two uploads in a row failed, stopping so nothing gets stuck. "
                            "You may have hit the 50-image limit.")
                        break
                if i < len(files):
                    time.sleep(PAUSE_BETWEEN_UPLOADS)
        except Stopped:
            log("Stopped.")
        finally:
            wait_for_user("Finished. Have a look at your profile in the browser, "
                          "then press Continue to close it.", final=True)
            try:
                ctx.close()
            except Exception:
                pass
    return uploaded, failed


def _dialog_error(dialogs):
    msg = " / ".join(dialogs)
    if re.search(r"error|fail|invalid|too (big|large)|limit|exceed", msg, re.I):
        return f"F-list said: {msg}"
    return None


def _response_error(response):
    """F-list's reply to the upload, if it says something went wrong."""
    if response.status >= 400:
        return f"F-list answered with error {response.status}"
    try:
        import json
        data = json.loads(response.text())
    except Exception:
        return None
    if isinstance(data, dict) and data.get("error"):
        return f"F-list said: {data['error']}"
    return None


def wait_for_upload(page, before, dialogs, uploads, stop_event):
    """Wait until F-list has answered the upload, an error appears, or we time out."""
    deadline = time.time() + UPLOAD_TIMEOUT
    cleared_since = replied_at = None
    while time.time() < deadline:
        if stop_event.is_set():
            raise Stopped()
        try:
            page.wait_for_load_state("load", timeout=5000)
        except Exception:
            pass
        if dialogs and _dialog_error(dialogs):
            return _dialog_error(dialogs)
        if success_message_shown(page):
            return "ok"
        if uploads:
            # F-list has replied. Give the page a moment to show the new picture,
            # its success message, or an error popup before moving on.
            error = _response_error(uploads[-1])
            if error:
                return error
            replied_at = replied_at or time.time()
            if time.time() - replied_at > 2:
                return "ok"
        if count_page_images(page) > before:
            return "ok"
        # No thumbnail to count? Fall back to "the file box emptied out".
        controls = find_upload_controls(page)
        if controls:
            try:
                emptied = controls[1].evaluate("el => !el.files || el.files.length === 0")
            except Exception:
                emptied = False
            if emptied:
                cleared_since = cleared_since or time.time()
                if time.time() - cleared_since > 3:
                    return "probably"
            else:
                cleared_since = None
        page.wait_for_timeout(200)
    return "timed out waiting for F-list"


# ---------------------------------------------------------------------------
# Point-and-click window
# ---------------------------------------------------------------------------
def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext

    root = tk.Tk()
    root.title("F-list Image Uploader")
    root.geometry("640x520")

    folder_var = tk.StringVar()
    mode_var = tk.StringVar(value="all")
    count_var = tk.IntVar(value=MAX_IMAGES)
    summary_var = tk.StringVar(value="Choose a folder of pictures to start.")
    prompt_var = tk.StringVar()

    events = queue.Queue()
    continue_event = threading.Event()
    stop_event = threading.Event()

    pad = {"padx": 10, "pady": 4}

    row = tk.Frame(root)
    row.pack(fill="x", **pad)
    tk.Label(row, text="Pictures folder:").pack(side="left")
    tk.Entry(row, textvariable=folder_var).pack(side="left", fill="x", expand=True, padx=6)

    def browse():
        d = filedialog.askdirectory(title="Choose the folder with your pictures")
        if d:
            folder_var.set(d)
            refresh_summary()

    tk.Button(row, text="Browse...", command=browse).pack(side="left")

    row = tk.Frame(root)
    row.pack(fill="x", **pad)
    tk.Radiobutton(row, text=f"Upload all of them (up to {MAX_IMAGES})", variable=mode_var,
                   value="all", command=lambda: refresh_summary()).pack(anchor="w")
    sub = tk.Frame(row)
    sub.pack(anchor="w")
    tk.Radiobutton(sub, text="Upload only the first", variable=mode_var,
                   value="some", command=lambda: refresh_summary()).pack(side="left")
    tk.Spinbox(sub, from_=1, to=MAX_IMAGES, width=5, textvariable=count_var,
               command=lambda: refresh_summary()).pack(side="left")
    tk.Label(sub, text="pictures").pack(side="left")

    tk.Label(root, textvariable=summary_var, anchor="w", justify="left",
             wraplength=600).pack(fill="x", **pad)

    buttons = tk.Frame(root)
    buttons.pack(fill="x", **pad)
    go_btn = tk.Button(buttons, text="Go", width=10)
    go_btn.pack(side="left")
    cont_btn = tk.Button(buttons, text="Continue", width=10, state="disabled")
    cont_btn.pack(side="left", padx=6)
    stop_btn = tk.Button(buttons, text="Stop", width=10, state="disabled")
    stop_btn.pack(side="left")

    tk.Label(root, textvariable=prompt_var, fg="#a33", anchor="w", justify="left",
             wraplength=600, font=("TkDefaultFont", 10, "bold")).pack(fill="x", **pad)

    log_box = scrolledtext.ScrolledText(root, height=14, state="disabled")
    log_box.pack(fill="both", expand=True, **pad)

    def write_log(text):
        log_box.configure(state="normal")
        log_box.insert("end", text + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    def chosen_limit():
        if mode_var.get() == "all":
            return None
        try:
            return int(count_var.get())
        except (tk.TclError, ValueError):
            return MAX_IMAGES

    def refresh_summary():
        folder = Path(folder_var.get())
        if not folder.is_dir():
            summary_var.set("Choose a folder of pictures to start.")
            return None
        files, skipped = scan_folder(folder, chosen_limit())
        text = f"{len(files)} picture(s) will be uploaded."
        if skipped:
            text += f" {len(skipped)} will be skipped because F-list would refuse them (details in the log when you press Go)."
        summary_var.set(text)
        return files, skipped

    def go():
        scanned = refresh_summary()
        if not scanned:
            messagebox.showinfo("F-list Image Uploader", "Please choose a folder first.")
            return
        files, skipped = scanned
        for p, reason in skipped:
            write_log(f"Skipping {p.name}: {reason}")
        if not files:
            messagebox.showinfo("F-list Image Uploader", "There are no pictures to upload in that folder.")
            return
        go_btn.configure(state="disabled")
        stop_btn.configure(state="normal")
        continue_event.clear()
        stop_event.clear()

        def log(msg):
            events.put(("log", msg))

        def wait_for_user(msg, final=False):
            continue_event.clear()
            events.put(("prompt", msg))
            continue_event.wait()
            events.put(("prompt", ""))

        def worker():
            try:
                up, bad = run_upload(files, log, wait_for_user, stop_event)
                log(f"All done: {len(up)} uploaded, {len(bad)} failed.")
                for p in bad:
                    log(f"  Not uploaded: {p.name}")
            except Exception as e:
                log(f"Something went wrong: {e}")
            events.put(("done", None))

        threading.Thread(target=worker, daemon=True).start()

    def do_continue():
        cont_btn.configure(state="disabled")
        continue_event.set()

    def do_stop():
        stop_event.set()
        continue_event.set()
        stop_btn.configure(state="disabled")

    go_btn.configure(command=go)
    cont_btn.configure(command=do_continue)
    stop_btn.configure(command=do_stop)

    def pump():
        try:
            while True:
                kind, payload = events.get_nowait()
                if kind == "log":
                    write_log(payload)
                elif kind == "prompt":
                    prompt_var.set(payload)
                    cont_btn.configure(state="normal" if payload else "disabled")
                elif kind == "done":
                    go_btn.configure(state="normal")
                    stop_btn.configure(state="disabled")
                    cont_btn.configure(state="disabled")
                    prompt_var.set("")
        except queue.Empty:
            pass
        root.after(150, pump)

    pump()
    root.mainloop()


# ---------------------------------------------------------------------------
# Command-line version
# ---------------------------------------------------------------------------
def run_cli(args):
    files, skipped = scan_folder(args.folder, args.count)
    for p, reason in skipped:
        print(f"Skipping {p.name}: {reason}")
    if not files:
        print("No pictures to upload.")
        return
    print(f"{len(files)} picture(s) will be uploaded.")

    def wait_for_user(msg, final=False):
        input(f"\n{msg}\n(press Enter here to continue) ")

    up, bad = run_upload(files, print, wait_for_user, threading.Event(), start_url=args.url)
    print(f"\nAll done: {len(up)} uploaded, {len(bad)} failed.")
    for p in bad:
        print(f"  Not uploaded: {p.name}")


def main():
    parser = argparse.ArgumentParser(description="Upload a folder of pictures to an F-list character.")
    parser.add_argument("folder", nargs="?", help="folder of pictures (omit to open the window)")
    parser.add_argument("--count", type=int, help=f"only upload the first N pictures (max {MAX_IMAGES})")
    parser.add_argument("--url", default=START_URL, help="page to open first")
    args = parser.parse_args()
    if args.folder:
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()
