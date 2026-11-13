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
