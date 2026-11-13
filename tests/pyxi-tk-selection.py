#!/usr/bin/env python3
"""Regression: selecting link ends must accept Tk 8.6 Tcl_Obj text indices.

Run under a real X server (Xvfb is sufficient). No backend needed: these
menu callbacks only construct the source/target virtual spans.
"""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import select
import subprocess
import sys
import time
import tkinter as tk
from _tkinter import Tcl_Obj

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "pyxi"))
loader = importlib.machinery.SourceFileLoader("udanax_pyxi_gui", str(root / "pyxi" / "pyxi"))
spec = importlib.util.spec_from_loader(loader.name, loader)
pyxi = importlib.util.module_from_spec(spec)
loader.exec_module(pyxi)
import x88

def spawn_xvfb(executable):
    """Start a private X server without relying on a fixed display number."""
    read_fd, write_fd = os.pipe()
    try:
        server = subprocess.Popen(
            [executable, "-displayfd", str(write_fd), "-screen", "0",
             "1024x768x24", "-nolisten", "tcp"],
            pass_fds=(write_fd,), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    finally:
        os.close(write_fd)
    try:
        if not select.select([read_fd], [], [], 10)[0]:
            raise RuntimeError("Xvfb did not allocate a display in 10 seconds")
        with os.fdopen(read_fd) as stream:
            read_fd = None
            number = stream.readline().strip()
        if not number or not number.isdecimal():
            raise RuntimeError("Xvfb returned an invalid display: %r" % number)
        return server, ":" + number
    except Exception:
        server.terminate()
        server.wait(timeout=5)
        raise
    finally:
        if read_fd is not None:
            os.close(read_fd)


xserver = None
if len(sys.argv) == 2:
    xserver, os.environ["DISPLAY"] = spawn_xvfb(sys.argv[1])

try:
    for attempt in range(30):
        try:
            window = tk.Tk()
            break
        except tk.TclError:
            if not xserver or attempt == 29:
                raise
            time.sleep(0.1)
    window.withdraw()
    pyxi.clipboard = pyxi.Clipboard(None)
    browser = pyxi.Browser(window, None)

    # The address is an editable Xanadu tumbler, while the formerly blank
    # adjacent field is a buffered-edit counter, not another text input.
    assert isinstance(browser.loc_entry, tk.Entry)
    assert isinstance(browser.edit_label, tk.Label)
    assert browser.edit_label.cget("text") == "Pending: 0"
    assert browser.edit_label.pack_info()["side"] == "right"

    # Typography and parallel layout belong in View, document operations in
    # Document, and the structured quick reference in Help.
    assert browser.view_menu.index("Parallel View / Compare (Alt+P)") is not None
    assert browser.view_menu.index("Proportional Font") is not None
    assert browser.view_menu.index("Monospaced Font") is not None
    assert browser.view_menu.index("Paragraph Spacing") is not None
    assert browser.doc_menu.index("Browse Linked Documents...") is not None
    assert browser.help_menu.index("Controls and Shortcuts...") is not None
    assert all("Parallel View" not in browser.doc_menu.entrycget(i, "label")
               for i in range(browser.doc_menu.index("end") + 1)
               if browser.doc_menu.type(i) != "separator")

    # The help is a formatted, scrollable, read-only document, not a long
    # message-box paragraph. Verify that its headings and key styles exist.
    helpbox = pyxi.ControlsHelpBox(browser)
    helptext = helpbox.help_text
    assert helptext.cget("state") == tk.DISABLED
    assert helptext.cget("yscrollcommand")
    assert "Navigation" in helptext.get("1.0", "end")
    assert "Documents and comparison" in helptext.get("1.0", "end")
    assert "section" in helptext.tag_names()
    assert "key" in helptext.tag_names()
    helpbox.destroy()

    text = browser.doc_text
    text.docid = x88.Address("1.1.0.1.0.1")
    # A freshly created browser is read-only until a document is opened.
    assert text.cget("state") == tk.DISABLED
    text.configure(state=tk.NORMAL)
    text.insert("1.0", "\n".join(["line %d" % i for i in range(1, 9)]))
    text.configure(state=tk.DISABLED)
    text.tag_add("sel", "7.1", "7.5")
    native_indices = text.tag_ranges("sel")
    assert len(native_indices) == 2, native_indices
    assert isinstance(native_indices[0], Tcl_Obj), type(native_indices[0])
    assert text.selind() == ("7.1", "7.5"), text.selind()
    assert text.position(native_indices[0]) == text.position("7.1")
    assert text.index(native_indices[0]) == "7.1"
    assert text.selvspan().span.start == x88.Address(1, text.position("7.1") + 1)

    # The exact menu actions from the user traceback, including menu insertion.
    browser.cb_addsource()
    browser.cb_addtarget()
    assert len(browser.sourceends) == 1, browser.sourceends
    assert len(browser.targetends) == 1, browser.targetends
    assert browser.sourceends[0] == browser.targetends[0]
    assert browser.sourceends[0].docid == text.docid
    browser.cb_clear()
    assert not browser.sourceends and not browser.targetends
finally:
    if "window" in locals():
        window.destroy()
    if xserver:
        xserver.terminate()
        xserver.wait(timeout=5)
print("Pyxi Tk source/target selection: passed")
