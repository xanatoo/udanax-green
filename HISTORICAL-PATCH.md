# 2005–2007 modified Udanax Green tree

The supplied `udanax-patch.tar.gz` is a partial replacement source tree, not a
unified diff. Its SHA-256 is:

`a705b1fa72c4711574baf5fbe744590f60fe47f89a31e654c0197256446b5032`

The unmodified tarball **contents** were committed on branch
`historical/roger-gregory-2007`, based on `d33c663` (the original extracted
1999 distribution), not on the NixOS port. That import includes temporary
editor files, experimental scripts and all other files in the archive to
preserve its historical evidence. No authorship or historical commit dates
were invented; this is a present-day archival import.

Relative to `d33c663`, the archive changes 37 files, with 324 added and 183
removed lines (line-based Git diff, including new files). For source files
(`*.c`, `*.h`, `*.py`, `*.s`, `*.sh`, and the `pyxi` script), 32 files account
for 319 added and 180 removed lines. These are changed lines, **not** net
new SLOC or a semantic SLOC count. Of 37 files, 28 are modified tracked
files and 9 are newly supplied. Binary editor swap files are included in the
archive branch; Git's line count does not account for their binary contents.

The `port/roger-gregory-selected` branch is based on the already-portable
master, and incorporates only individually reviewed frontend corrections:

- TCP sockets need one `(hostname, port)` tuple argument.
- Shared-span results need a tuple as the single `append` argument.
- Python 2 `long` string formatting should remove an `L` only if present.
- The Pyxi shebang is made conventional; the debug server host is `localhost`
  rather than a historical machine name.

The backend memory reclamation changes that disable consistency checks, the
altered byte-masking behavior, changed persistent disk structures, and the
experimental CGI scripts have **not** been merged. Other declaration tweaks
were deferred pending dedicated tests or are redundant with modern compiler
fixes. The original Pyxi frontend still requires Python 2 compatibility work;
these changes are not a functional frontend test.

Compare with:

```sh
git diff d33c663..historical/roger-gregory-2007
git log --graph --oneline --all --decorate
```

## Further review: free-disk index deletion

The 2007 tree changes `if (oldptr = 0)` to `if (oldptr == 0)` in
`multiloaf.c`. This is a real assignment-in-conditional bug, but the routine
still unlinks only the ordered table node; the hash table retains a node
referencing freed memory. The curated port uses a separately written
replacement that removes both nodes and frees the shared entry once, with
`tests/freedisk.c` providing a focused regression test. No wholesale disk
persistence edits from the historical tree were imported.
