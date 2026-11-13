#!/usr/bin/env python3
"""Tk regression: Edit menu toggle must allow persistent keyboard typing.

Use real Tk key events and a real backend; calling Browser.insertchar()
would miss modifier-state handling and disabled-Text-widget regressions.
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
loader = importlib.machinery.SourceFileLoader('udanax_pyxi_typing',
                                            str(rootdir / 'pyxi' / 'pyxi'))
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
    with tempfile.TemporaryDirectory(prefix='udanax-pyxi-typing-') as tmp:
        shutil.copyfile(sample, Path(tmp) / 'enf.enf')
        cwd = os.getcwd()
        os.chdir(tmp)
        window = None
        session = None
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

            docid = session.create_document()
            session.open_document(docid, x88.READ_WRITE, x88.CONFLICT_COPY)
            session.insert(docid, x88.Address(1, 1), ['seed'])
            session.close_document(docid)
            browser.goto(docid)
            window.update()
            text = browser.doc_text
            menu = browser.edit_menu
            assert str(menu.cget('tearoff')) == '0'
            assert menu.entrycget(browser.enable_edit_menu_index, 'label') == 'Enable Editing'
            assert menu.entrycget(browser.mark_menu_index, 'label') == 'Mark'
            assert menu.entrycget(browser.transclude_menu_index, 'label') == 'Transclude'
            assert menu.entrycget(browser.move_menu_index, 'label') == 'Move'
            assert text.cget('state') == tk.DISABLED

            # Read-only text must reject typing, even with Num Lock set.
            text.focus_set()
            text.mark_set('insert', 'end-1c')
            text.event_generate('<KeyPress-x>', state=0x10)
            window.update()
            assert text.get('1.0', 'end-1c') == 'seed'

            # Invoke the actual menu item instead of setting browser.editable.
            menu.invoke(browser.enable_edit_menu_index)
            window.update()
            assert browser.editable and browser.edit_var.get()
            assert text.cget('state') == tk.NORMAL
            assert menu.entrycget(browser.mark_menu_index, 'state') == tk.DISABLED

            text.focus_set()
            text.mark_set('insert', 'end-1c')
            expected = 'seed'
            # NumLock/LockMask previously bypassed Pyxi's edit buffer. Tk
            # would insert these locally, but a reload would lose the text.
            for keysym, state in [('a', 0), ('b', 0x10), ('c', 0x2)]:
                before = text.get('1.0', 'end-1c')
                text.event_generate('<KeyPress-%s>' % keysym, state=state)
                window.update()
                after = text.get('1.0', 'end-1c')
                assert len(after) == len(before) + 1, (keysym, state, before, after)
                assert browser.editstate == pyxi.INSERTING, (keysym, state)
                expected = after
            browser.finishedit()
            browser.reload()
            assert text.cget('state') == tk.NORMAL
            assert text.get('1.0', 'end-1c') == expected, 'typed text lost after reload'

            # Selection and marked source should update the correct menu
            # entries regardless of the platform's tear-off default.
            text.tag_add('sel', '1.0', '1.2')
            browser.updateeditmenu()
            assert menu.entrycget(browser.mark_menu_index, 'state') == tk.NORMAL
            menu.invoke(browser.mark_menu_index)
            assert pyxi.clipboard.marked()
            assert menu.entrycget(browser.transclude_menu_index, 'state') == tk.NORMAL

            # Toggling editing off and back on keeps keyboard entry working.
            menu.invoke(browser.enable_edit_menu_index)
            window.update()
            assert not browser.editable and text.cget('state') == tk.DISABLED
            text.tag_remove('sel', '1.0', 'end')
            text.event_generate('<KeyPress-z>')
            window.update()
            assert text.get('1.0', 'end-1c') == expected
            menu.invoke(browser.enable_edit_menu_index)
            window.update()
            assert browser.editable and text.cget('state') == tk.NORMAL
            text.focus_set()
            text.mark_set('insert', 'end-1c')
            text.event_generate('<KeyPress-d>', state=0x10)
            window.update()
            assert browser.editstate == pyxi.INSERTING
            expected = text.get('1.0', 'end-1c')
            browser.finishedit()
            browser.reload()
            assert text.get('1.0', 'end-1c') == expected

            browser.closedoc()
            session.quit()
            session = x88.pipeconnect(backend)
            session.open_document(docid, x88.READ_ONLY, x88.CONFLICT_COPY)
            content = session.retrieve_contents(x88.SpecSet(x88.VSpec(docid, [
                x88.Span(x88.Address(1, 1), x88.Offset(0, len(expected)))])))
            assert ''.join(content) == expected, 'typed text lost after backend restart'
            session.close_document(docid)
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
    if server is not None:
        server.terminate()
        server.wait(timeout=5)
print('Pyxi edit toggle and keyboard typing: passed')
