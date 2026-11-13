# NixOS port status

This repository contains an original Udanax Green source release. The
Nix integration builds the **three C backend executables** without a network
connection during compilation. It does **not** make the 1980s frontend or
the entire interactive demonstration work on modern Linux.

```sh
nix build
nix flake check
nix develop
make -C green/be_source CC=cc CFLAGS="$UDANAX_CFLAGS" LFLAGS= all
```

The package installs `udanax-xumain`, `udanax-backend`, and
`udanax-backenddaemon` along with the demo data under
`share/udanax-green/`. The backend works with local `enf.enf` files, so run
it from a writable working directory; the Nix store is read-only.

## Compatibility edits

The original source is unchanged in its import commit. Follow-up edits
address diagnostics that modern GCC treats as errors:

- Move legacy `static` forward declarations to file scope.
- Restore the original pointer return type of `taskalloc` at its callsite.
- Correct a missing `goodblock` declaration.
- Replace a macro invocation on a cast expression (non-lvalue) with the
  existing `getrightbro` routine.
- Make extern declarations of shared counters agree across translation
  units (64-bit `long` versus 32-bit `int`).

The compile flags retain C89 implicit declarations and `-fcommon`; many
other old-style declarations and pointer/integer conversions remain.

## Validation limits

The C backend has been compiled with modern GCC on x86_64 Linux, but the
machine used for this port has no Nix installation, so `nix build` and
`nix flake check` have **not** been executed. A non-interactive `xumain`
invocation enters an input loop on EOF; do not treat it as a passing
functional test. The original code also makes assumptions about pointer
sizes, data layouts, and file formats. Interactive frontend, database
correctness, and cross-architecture operation remain **unverified**.

## Historical 2007 disk allocator fix

The historical branch corrected `if (oldptr = 0)` in the free-disk ordered
index deletion. Further review showed that the same function left the hash
index node behind while freeing the entry shared by both indexes. Rather than
apply the one-character patch alone, the current port removes **both** index
nodes before freeing their shared entry. `tests/freedisk.c` tests deletion
from multi-entry lists; it runs during the Nix package check phase. The test
has passed under AddressSanitizer on x86_64 Linux, but it is not a persistent
database round-trip test. The original allocator has other unverified paths,
including `changefreediskstructures`. Hash bucket computation now uses
unsigned wide arithmetic to avoid signed integer overflow; the hash table is
process-local and is not part of the on-disk representation.

## Modern compiler and runtime fixes (November 2026)

The backend now compiles with GCC `-Werror=format-security` without disabling
Nix's format-string hardening.  The `test.c` debug messages use `fputs`
instead of passing an arbitrary message as a format string.

Further compatibility repairs include standard declarations for libc routines,
correct `sbrk()` failure checks, a pointer-returning allocator declaration for
the frontend protocol, a 64-bit-safe tumbler byte comparison, byte-pointer
arithmetic for disk offsets, proper `fd_set` usage for the daemon's `select`,
and corrected `.backendrc` numeric parsing.

The flake check phase runs `tests/freedisk.c` and `tests/rcfile.c`.
Both tests pass under GCC and AddressSanitizer/UndefinedBehaviorSanitizer
outside Nix.  **No full database persistence round trip or Nix build has been
verified in the assistant environment.**  Other original-code warnings remain,
including K&R implicit returns and pointer-format diagnostic issues.  Treat
runtime correctness and serialized database compatibility as unverified.

## Standalone backend smoke tests

The flake's `checkPhase` now exercises `xumain` with disposable databases,
not just allocator/parser unit tests. The new `tests/backend-smoke.sh` checks
that:

- EOF on an empty input script exits without spinning and creates `enf.enf`;
- a newly created document can be retrieved after closing and reopening;
- the shipped `sample.enf` opens and a document-span query succeeds;
- the document-span response remains the same after a second process starts.

The original `xumain` loop previously retried indefinitely on EOF; it now
closes the database and exits cleanly. Explicit request `16` still quits.

**Caution:** Opening and closing `sample.enf` changes bytes in the database,
even without user-visible edits. The test deliberately compares decoded query
results rather than requiring an identical file checksum. The reason for the
on-disk rewrites, long-term serialization compatibility, and the full
interactive demonstration are still unverified. The smoke tests do not prove
that all document contents or links survive a restart.

## Text insertion and retrieval across restarts

`tests/text-persistence.sh` now runs the standalone protocol against a
throwaway database, creates document `0.0.1`, inserts `hello Green` at
virtual address `1`, closes the process, retrieves its 12-byte span in a
new process, and checks that a second restart returns identical output.
This test is included in the flake's check phase. It does not exercise
transclusion, link following, concurrent access, or document versioning.

The original standalone parser also had an `fprintf("%c")` without its
corresponding character argument on the error path. That is corrected,
and `getnum` now avoids passing EOF to `ungetc`.

**Known failing operation:** In a disposable newly created document,
request `13` (create new version of `0.0.1`) aborted in
`docreatenewversion` after `doopen` failed. This is not marked as a
passing regression test and needs separate investigation before versioning
can be claimed functional. The first insertion emitted an internal
`levelpush` diagnostic on stderr, even though subsequent text reads worked.

**Sample database rewrites:** A controlled open/quit of the original
`sample.enf` changed its SHA-256, and repeated open/quit cycles continued
to change it. This is reproducible but its cause has not yet been identified.
Always test against a copy of the sample database.


## Pyxi graphical frontend (Python 3 / Tk)

The original 1999 Pyxi frontend has been converted to Python 3 while keeping
its menus, document editor and Tk widgets. Run with `nix run .#pyxi` or build
with `nix build .#pyxi`. This launcher prepares a writable copy of the sample
database in `${XDG_STATE_HOME:-$HOME/.local/state}/udanax-green/be/enf.enf`
and starts the backend through pipes. The original sample in the Nix store is
never modified. Changes to the local database persist between launches.

Use `nix develop` for a Python interpreter with Tkinter support, and invoke
`python3 pyxi/test.py` for its historical mocked-protocol test suite.
`tests/pyxi-protocol.py` also checks that the ported client can open and
retrieve the introduction from the real backend's sample database.

The graphical application has been launched under Xvfb and has not shown a
Python traceback during startup, but interactive GUI editing, link editing and
version creation are **not yet verified**. Historical backend version creation
still has a known failure. Full `nix flake check` also needs a local NixOS run.
