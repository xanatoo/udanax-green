#!/usr/bin/env python3
"""Test marking, transcluding and editing-mode transitions in real Tk/backend.

Runs with a disposable sample.enf. Source marks must survive navigating to a
new document or toggling edit mode, but modifying the marked source invalidates
its mark. Transclusion must persist after closing and reopening the database.
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
loader = importlib.machinery.SourceFileLoader('udanax_pyxi_transclude',
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
    with tempfile.TemporaryDirectory(prefix='udanax-pyxi-transclude-') as tmp:
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
            window.update()

            # A callback must not pass None to x88.SpecSet when no text was marked.
            errors = []
            original_error = pyxi.tktrans.error
            pyxi.tktrans.error = lambda _parent, message, title: errors.append((title, message))
            try:
                source = x88.Address('1.1.0.1.0.1')
                browser.goto(source)
                browser.cb_vcopy()
                assert errors and errors[-1][0] == 'No Marked Text', errors
                errors.clear()
            finally:
                pyxi.tktrans.error = original_error

            # Mark a source in a read-only browser and navigate away from it.
            text = browser.doc_text
            text.tag_add('sel', '1.0', '1.0 + 17c')
            chosen = text.get('sel.first', 'sel.last')
            assert chosen == ' \nWelcome to Pyxi', repr(chosen)
            browser.cb_mark()
            assert pyxi.clipboard.marked()
            assert pyxi.clipboard.markdata == chosen
            assert text.tag_ranges('clip')

            # Seed a new document: Green's backend dislikes completely empty ones.
            target = session.create_document()
            session.open_document(target, x88.READ_WRITE, x88.CONFLICT_COPY)
            session.insert(target, x88.Address(1, 1), ['X'])
            session.close_document(target)
            browser.goto(target, editable=1)
            assert pyxi.clipboard.marked(), 'navigation lost the marked source'
            assert pyxi.clipboard.marktext is None
            assert browser.edit_menu.entrycget(browser.transclude_menu_index, 'state') == tk.NORMAL
            assert browser.edit_menu.entrycget(browser.move_menu_index, 'state') == tk.DISABLED
            assert text.cget('state') == tk.NORMAL
            assert not text.tag_ranges('clip'), 'source highlight leaked to destination'

            browser.doc_text.setcur('end-1c')
            browser.cb_vcopy()
            expected = 'X' + chosen
            assert text.get('1.0', 'end-1c') == expected
            assert not pyxi.clipboard.marked(), 'successful transclusion retained the mark'
            browser.reload()
            assert text.get('1.0', 'end-1c') == expected

            # Version identity, not just a duplicated string: both passages share
            # the same Xanadu content, as reported by compare_versions.
            source_spec = x88.SpecSet(x88.VSpec(source, [
                x88.Span(x88.Address(1, 1), x88.Offset(0, len(chosen)))]))
            target_spec = x88.SpecSet(x88.VSpec(target, [
                x88.Span(x88.Address(1, 2), x88.Offset(0, len(chosen)))]))
            session.open_document(source, x88.READ_ONLY, x88.CONFLICT_COPY)
            try:
                shared = session.compare_versions(source_spec, target_spec)
                assert shared, 'transcluded text did not share Xanadu content'
            finally:
                session.close_document(source)

            # Pending destination typing must be flushed before the backend
            # processes a transclusion at the new cursor address.
            browser.goto(source)
            text.tag_add('sel', '1.0', '1.0 + 4c')
            browser.cb_mark()
            browser.goto(target, editable=1)
            text.tag_remove('sel', '1.0', 'end')
            text.setcur('end-1c')
            browser.insertchar('Y')
            assert pyxi.clipboard.marked(), 'typing in destination discarded source mark'
            browser.cb_vcopy()
            expected += 'Y' + chosen[:4]
            assert text.get('1.0', 'end-1c') == expected
            browser.reload()
            assert text.get('1.0', 'end-1c') == expected

            # A read-only mark also survives enabling editing in the SAME doc.
            browser.goto(source)
            text.tag_add('sel', '1.0', '1.5')
            browser.cb_mark()
            assert pyxi.clipboard.marked()
            browser.edit_var.set(1)
            browser.cb_editable()
            assert text.cget('state') == tk.NORMAL, 'editing toggle left Tk disabled'
            assert pyxi.clipboard.marked(), 'editing toggle discarded the mark'
            assert pyxi.clipboard.marktext is text, 'source highlight not restored'
            assert text.tag_ranges('clip')
            assert browser.edit_menu.entrycget(browser.transclude_menu_index, 'state') == tk.NORMAL

            # Edits to the marked source must invalidate its span.
            text.setcur('end-1c')
            browser.insertchar('Z')
            assert not pyxi.clipboard.marked(), 'source edit kept a stale mark'
            browser.finishedit()
            browser.closedoc()

            session.quit()
            session = x88.pipeconnect(backend)
            session.open_document(target, x88.READ_ONLY, x88.CONFLICT_COPY)
            full_spec = x88.SpecSet(x88.VSpec(target, [
                x88.Span(x88.Address(1, 1), x88.Offset(0, len(expected)))]))
            assert ''.join(session.retrieve_contents(full_spec)) == expected
            session.close_document(target)
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
print('Pyxi marked-text transclusion, restart and edit transitions: passed')
