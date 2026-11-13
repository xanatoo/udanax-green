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
