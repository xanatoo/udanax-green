#!/usr/bin/env python3
"""Integration: real Tk link navigation and linked document discovery on sample.enf."""
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
loader = importlib.machinery.SourceFileLoader('udanax_pyxi_gui_links', str(rootdir / 'pyxi' / 'pyxi'))
spec = importlib.util.spec_from_loader(loader.name, loader)
pyxi = importlib.util.module_from_spec(spec)
loader.exec_module(pyxi)
import x88
import docbrowser

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

def click_tag(text, tag, bind='<Button-1>'):
    # Scroll the first link into view and simulate the pointer moving onto it.
    # Tk dispatches tag bindings based on 'current', which tracks the pointer.
    indices = text.tag_ranges(tag)
    assert indices, 'missing %s tag' % tag
    index = str(indices[0])
    text.see(index)
    text.update()
    bbox = text.bbox(index)
    assert bbox is not None, (tag, index)
    x, y, w, h = bbox
    x += max(1, min(2, w // 2))
    y += max(1, h // 2)
    text.event_generate('<Motion>', x=x, y=y)
    text.update()
    assert tag in text.tag_names('current'), (tag, text.tag_names('current'), index)
    text.event_generate(bind, x=x, y=y)
    text.update()

try:
    with tempfile.TemporaryDirectory(prefix='udanax-pyxi-links-') as tmp:
        shutil.copyfile(sample, Path(tmp) / 'enf.enf')
        cwd = os.getcwd()
        os.chdir(tmp)
        session = None
        window = None
        try:
            session = x88.pipeconnect(backend)
            rootid = x88.Address('1.1.0.1.0.1')
            session.open_document(rootid, x88.READ_ONLY, x88.CONFLICT_COPY)
            title, linked = docbrowser.inspect_document(session, rootid, already_open=True)
            assert 'Welcome to Pyxi' in title, title
            assert str(x88.Address('1.1.0.1.0.3')) in set(map(str, linked)), linked
            session.close_document(rootid)

            for attempt in range(40):
                try:
                    window = tk.Tk()
                    break
                except tk.TclError:
                    if not server or attempt == 39:
                        raise
                    time.sleep(.1)
            window.geometry('900x700')
            pyxi.clipboard = pyxi.Clipboard(session)
            browser = pyxi.Browser(window, session)
            browser.pack(fill=tk.BOTH, expand=True)
            window.update()
            browser.goto(rootid)
            window.update()

            # Editing mode still permits ordinary selection instead of
            # navigating when the pointer is on a link end.
            browser.editable = True
            click_tag(browser.doc_text, 'source')
            assert browser.docid == rootid, 'editing click navigated unexpectedly'
            # Alt-click is still available in editing mode.
            click_tag(browser.doc_text, 'source', '<Alt-Button-1>')
            assert browser.docid != rootid, 'Alt-click did not navigate'
            browser.goto(rootid)
            browser.editable = False

            # A plain click on a linked source navigates in read-only mode.
            click_tag(browser.doc_text, 'source')
            assert browser.docid != rootid, 'plain-click did not navigate'
            assert str(browser.docid) in set(map(str, linked)), browser.docid

            # The new browser lists the root and discovers its linked documents.
            browser.goto(rootid)
            explorer = pyxi.LinkedDocumentWindow(browser)
            window.update()
            assert len(explorer.docs) >= 4, explorer.docs
            explorer.explore_connected()
            assert len(explorer.docs) >= 4
            explorer.listbox.selection_clear(0, tk.END)
            target_idx = explorer.entries.index(str(linked[0]))
            explorer.listbox.selection_set(target_idx)
            explorer.open_selected()
            assert browser.docid == linked[0]
            explorer.destroy()
            browser.closedoc()
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
print('Pyxi linked-document browser and click navigation: passed')
