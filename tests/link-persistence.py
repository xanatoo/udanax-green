#!/usr/bin/env python3
"""Create a jump link on a disposable copy of sample.enf and reopen it."""
import os
from pathlib import Path
import shutil
import sys
import tempfile

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'pyxi'))
import x88

backend, sample = map(lambda p: str(Path(p).resolve()), sys.argv[1:3])
source = x88.Address('1.1.0.1.0.1')
target = x88.Address('1.1.0.1.0.3')
sources = x88.SpecSet(x88.VSpec(source, [
    x88.Span(x88.Address(1, 200), x88.Offset(0, 4))]))
targets = x88.SpecSet(x88.VSpec(target, [
    x88.Span(x88.Address(1, 20), x88.Offset(0, 4))]))
with tempfile.TemporaryDirectory(prefix='udanax-link-') as tmp:
    shutil.copyfile(sample, os.path.join(tmp, 'enf.enf'))
    cwd = os.getcwd()
    try:
        os.chdir(tmp)
        session = x88.pipeconnect(backend)
        try:
            session.open_document(source, x88.READ_WRITE, x88.CONFLICT_COPY)
            created = session.create_link(source, sources, targets,
                                          x88.SpecSet(x88.JUMP_TYPE))
            assert created in session.find_links(sources)
            assert session.follow_link(created, x88.LINK_TARGET) == targets
            session.close_document(source)
        finally:
            session.quit()

        session = x88.pipeconnect(backend)
        try:
            session.open_document(source, x88.READ_ONLY, x88.CONFLICT_COPY)
            assert created in session.find_links(sources), 'link lost on restart'
            assert session.follow_link(created, x88.LINK_TARGET) == targets
            session.close_document(source)
        finally:
            session.quit()
    finally:
        os.chdir(cwd)
print('Udanax link create/find/follow/reopen: passed')
