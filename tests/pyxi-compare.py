#!/usr/bin/env python3
"""Exercise the historical parallel Compare view under Tk and the C server."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import tempfile
import time
import tkinter as tk

rootdir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(rootdir / 'pyxi'))
loader = importlib.machinery.SourceFileLoader('udanax_pyxi_compare', str(rootdir / 'pyxi' / 'pyxi'))
spec = importlib.util.spec_from_loader(loader.name, loader)
pyxi = importlib.util.module_from_spec(spec)
loader.exec_module(pyxi)
import x88

backend, sample = (str(Path(value).resolve()) for value in sys.argv[1:3])
xvfb = str(Path(sys.argv[3]).resolve()) if len(sys.argv) > 3 else None
server = None
if xvfb:
    r, w = os.pipe()
    try:
        server = subprocess.Popen([xvfb, '-displayfd', str(w), '-screen', '0',
                                   '1100x750x24', '-nolisten', 'tcp'],
                                  pass_fds=(w,), stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
    finally:
        os.close(w)
    try:
        assert select.select([r], [], [], 10)[0], 'Xvfb launch timeout'
        display = os.read(r, 128).decode().strip()
        assert display.isdecimal(), repr(display)
        os.environ['DISPLAY'] = ':' + display
    finally:
        os.close(r)

try:
    with tempfile.TemporaryDirectory(prefix='udanax-pyxi-compare-') as tmp:
        shutil.copyfile(sample, Path(tmp) / 'enf.enf')
        originaldir = os.getcwd()
        os.chdir(tmp)
        session = None
        root = None
        win = None
        try:
            session = x88.pipeconnect(backend)
            for attempt in range(40):
                try:
                    root = tk.Tk()
                    break
                except tk.TclError:
                    if not server or attempt == 39:
                        raise
                    time.sleep(.1)
            root.withdraw()
            pyxi.windows = {}
            pyxi.clipboard = pyxi.Clipboard(session)
            win = pyxi.TwoBrowserWindow(session)
            win.geometry('950x680')
            win.browser.goto(x88.Address('1.1.0.1.0.3'))
            win.update()

            # The document text, including both font modes, is larger than
            # the original 1999 defaults. Toolbar font is unchanged.
            assert '-16-' in pyxi.PROPFONT, pyxi.PROPFONT
            assert '-14-' in pyxi.MONOFONT, pyxi.MONOFONT
            assert win.browser.doc_text.cget('font') == pyxi.PROPFONT
            win.browser.font_var.set(pyxi.MONOFONT)
            win.browser.cb_font()
            assert win.browser.doc_text.cget('font') == pyxi.MONOFONT
            win.browser.font_var.set(pyxi.PROPFONT)
            win.browser.cb_font()

            # Invoke the menu option, not an internal toggler.
            menu = win.browser.doc_menu
            index = menu.index('Parallel View / Compare (Alt+P)')
            assert index is not None
            menu.invoke(index)
            win.update()
            assert win.browser2 is not None
            assert win.compare_btn.cget('state') == tk.DISABLED
            assert int(win.browser.doc_text.cget('width')) > 0
            assert int(win.browser2.doc_text.cget('width')) > 0
            assert win.compare_btn.winfo_width() < 200, 'Compare button takes over the layout'

            # Distinct but related Declaration documents from the sample store.
            win.browser2.goto(x88.Address('1.1.0.1.0.3.1'))
            win.update()
            assert win.compare_btn.cget('state') == tk.NORMAL
            win.compare_btn.invoke()
            win.update()
            assert win.comparing, 'Compare was not enabled'
            assert isinstance(win.sharedspans, list)
            assert len(win.sharedspans) > 0, 'sample versions should share content'
            assert len(win.translines) == len(win.sharedspans)

            # The menu can collapse the view even while comparing; reopening
            # must not retain stale bindings/tags or a dead second pane.
            menu.invoke(index)
            win.update()
            assert win.browser2 is None
            assert not win.comparing
            assert 'left-0' not in win.browser.doc_text.tag_names()
            menu.invoke(index)
            win.update()
            assert win.browser2 is not None
            assert win.compare_btn.cget('state') == tk.DISABLED
            win.eh_parallel(None)
            win.update()
            assert win.browser2 is None
        finally:
            if win is not None:
                try:
                    win.browser.closedoc()
                except (OSError, x88.XuError):
                    pass
                win.destroy()
            if root is not None:
                root.destroy()
            if session is not None:
                try:
                    session.quit()
                except (OSError, x88.XuError):
                    pass
            os.chdir(originaldir)
finally:
    if server is not None:
        server.terminate()
        server.wait(timeout=5)
print('Pyxi parallel Compare view and larger fonts: passed')
