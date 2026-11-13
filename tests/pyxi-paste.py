#!/usr/bin/env python3
"""Tk regression: X11 paste must obey read-only mode and reach the backend.

Uses a private copy of sample.enf and a real C backend, with an optional Xvfb.
"""
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
loader = importlib.machinery.SourceFileLoader('udanax_pyxi_paste', str(rootdir / 'pyxi' / 'pyxi'))
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
                                   '1024x768x24', '-nolisten', 'tcp'],
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
    with tempfile.TemporaryDirectory(prefix='udanax-pyxi-paste-') as tmp:
        shutil.copyfile(sample, Path(tmp) / 'enf.enf')
        cwd = os.getcwd()
        os.chdir(tmp)
        session = None
        window = None
        try:
            session = x88.pipeconnect(backend)
            for attempt in range(40):
                try:
                    window = tk.Tk()
                    break
                except tk.TclError:
                    if not server or attempt == 39:
                        raise
                    time.sleep(.1)
            window.geometry('850x650')
            pyxi.clipboard = pyxi.Clipboard(session)
            browser = pyxi.Browser(window, session)
            browser.pack(fill=tk.BOTH, expand=True)
            source = tk.Text(window, height=1)
            source.pack()
            source.insert('1.0', 'PRIMARY PASTE')
            window.update()

            rootid = x88.Address('1.1.0.1.0.1')
            browser.goto(rootid)
            window.update()
            doc = browser.doc_text
            original = doc.get('1.0', 'end-1c')
            assert 'Welcome to Pyxi' in original[:100], original[:100]
            assert doc.cget('state') == tk.DISABLED

            # Tk exports a Text selection as the X11 PRIMARY selection.
            source.tag_add('sel', '1.0', '1.13')
            window.update()
            assert doc.selection_get(selection='PRIMARY') == 'PRIMARY PASTE'
            doc.event_generate('<ButtonRelease-2>', x=30, y=30)
            doc.event_generate('<<Paste>>')
            doc.event_generate('<<Clear>>')
            doc.event_generate('<<Cut>>')
            window.update()
            assert doc.get('1.0', 'end-1c') == original
            assert doc.cget('state') == tk.DISABLED

            # Editing enables the widget; both clipboard and PRIMARY pastes
            # must go through the C server, not a Tk-only text insertion.
            newid = session.create_document()
            session.open_document(newid, x88.READ_WRITE, x88.CONFLICT_COPY)
            session.insert(newid, x88.Address(1, 1), [' '])
            session.close_document(newid)
            browser.goto(newid, editable=1)
            window.update()
            assert doc.cget('state') == tk.NORMAL
            assert doc.get('1.0', 'end-1c') == ' '

            window.clipboard_clear()
            window.clipboard_append('clipboard text')
            doc.event_generate('<<Paste>>')
            browser.finishedit()
            assert 'clipboard text' in doc.get('1.0', 'end-1c')

            # PRIMARY paste is located by click position, and likewise must
            # be stored in the backend. Put the insertion point at the end.
            doc.see('end')
            window.update()
            bbox = doc.bbox('end-1c')
            assert bbox is not None
            x, y, width, height = bbox
            # The source window still owns the PRIMARY selection.
            assert doc.selection_get(selection='PRIMARY') == 'PRIMARY PASTE'
            doc.event_generate('<ButtonRelease-2>', x=x + max(1, width - 1),
                               y=y + max(1, height // 2))
            browser.finishedit()
            expected = doc.get('1.0', 'end-1c')
            assert 'PRIMARY PASTE' in expected, expected
            browser.reload()
            assert doc.cget('state') == tk.NORMAL
            assert doc.get('1.0', 'end-1c') == expected, 'pasted text not saved'

            browser.closedoc()
            browser.goto(rootid)
            assert doc.cget('state') == tk.DISABLED
            assert doc.get('1.0', 'end-1c') == original
        finally:
            if window is not None:
                window.destroy()
            if session is not None:
                try:
                    session.quit()
                except (OSError, x88.XuError):
                    pass
            os.chdir(cwd)
finally:
    if server:
        server.terminate()
        server.wait(timeout=5)
print('Pyxi read-only and backend-synchronized paste: passed')
