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
    text = browser.doc_text
    text.docid = x88.Address("1.1.0.1.0.1")
    text.insert("1.0", "\n".join(["line %d" % i for i in range(1, 9)]))
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
