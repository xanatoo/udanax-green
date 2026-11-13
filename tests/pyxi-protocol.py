#!/usr/bin/env python3
"""Run the Python 3 FeBe client against the real, piped Udanax backend."""
import os
from pathlib import Path
import shutil
import sys
import tempfile

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'pyxi'))
import x88

backend, database = map(lambda p: str(Path(p).resolve()), sys.argv[1:3])
with tempfile.TemporaryDirectory(prefix='udanax-pyxi-') as tmp:
    shutil.copyfile(database, os.path.join(tmp, 'enf.enf'))
    current = os.getcwd()
    try:
        os.chdir(tmp)
        session = x88.pipeconnect(backend)
        try:
            address = x88.Address('1.1.0.1.0.1')
            opened = session.open_document(address, x88.READ_ONLY, x88.CONFLICT_COPY)
            spans = session.retrieve_vspanset(opened)
            assert spans, 'Sample document has no spans'
            text_span = next(v.span for v in spans if v.span.start[0] == 1)
            data = session.retrieve_contents(x88.SpecSet(x88.VSpec(opened, [text_span])))
            assert data and 'Welcome to Pyxi' in ''.join(data), repr(data)[:200]
            session.close_document(opened)
        finally:
            session.quit()
    finally:
        os.chdir(current)
print('Pyxi protocol client: sample document opened and retrieved')
