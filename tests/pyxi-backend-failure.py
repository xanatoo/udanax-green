#!/usr/bin/env python3
"""Pyxi must report the backend log, rather than a bare BrokenPipeError."""
import os
from pathlib import Path
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit('usage: pyxi-backend-failure.py PATH-TO-FALSE')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'pyxi'))
import x88

with tempfile.TemporaryDirectory() as temporary:
    previous = os.getcwd()
    try:
        os.chdir(temporary)
        Path('backenderror').write_text('intentional backend failure\n')
        stream = x88.PipeStream(sys.argv[1])
        stream.process.wait(timeout=5)
        # Pyxi changes directories after starting the backend. Its error
        # reporting must still find the log in the backend work directory.
        other = Path(temporary) / 'gui'
        other.mkdir()
        os.chdir(other)
        try:
            stream.write('35~')
        except x88.XuError as exc:
            message = str(exc)
            assert 'intentional backend failure' in message, message
            assert str(Path(temporary) / 'backenderror') in message, message
            assert 'Backend directory: %s' % temporary in message, message
        else:
            raise AssertionError('backend failure was not reported')
        stream.close()
    finally:
        os.chdir(previous)
print('Pyxi backend failure diagnostics: passed')
