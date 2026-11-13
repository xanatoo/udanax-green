#!/usr/bin/env python3
"""Pyxi must report the backend log, rather than a bare BrokenPipeError."""
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'pyxi'))
import x88

with tempfile.TemporaryDirectory() as temporary:
    previous = os.getcwd()
    try:
        os.chdir(temporary)
        Path('backenderror').write_text('intentional backend failure\n')
        stream = x88.PipeStream('/bin/false')
        stream.process.wait(timeout=5)
        try:
            stream.write('35~')
        except x88.XuError as exc:
            message = str(exc)
            assert 'intentional backend failure' in message, message
            assert temporary in message, message
        else:
            raise AssertionError('backend failure was not reported')
        stream.close()
    finally:
        os.chdir(previous)
print('Pyxi backend failure diagnostics: passed')
