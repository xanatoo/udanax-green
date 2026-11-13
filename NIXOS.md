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

The C backend has been compiled with modern GCC on x86_64 Linux. The
assistant environment lacks Nix, but `nix build` and `nix flake check` were
reported to work on NixOS before this latest change. `xumain` now handles EOF.
The original code still makes assumptions about pointer sizes, data layouts,
and file formats. Full database correctness and cross-architecture operation
remain **unverified**.

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
outside Nix.  Focused allocator, text-persistence, and link-persistence tests have since
been added, but no complete database validation has been performed. Other
original-code warnings remain, including K&R implicit returns and
pointer-format diagnostic issues.

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
The launcher sets owner-write permission on the copied sample and repairs
read-only copies left by older launcher versions without replacing their
contents. Database symlinks are rejected to avoid chmodding a Nix store path.
If the database belongs to another user, repair its ownership separately.

Use `nix develop` for a Python interpreter with Tkinter support, and invoke
`python3 pyxi/test.py` for its historical mocked-protocol test suite.
`tests/pyxi-protocol.py` also checks that the ported client can open and
retrieve the introduction from the real backend's sample database.

The graphical frontend launches under Xvfb. Subsequent tests cover real Tk
link clicking, source/target selection, linked-document discovery, and backend
link creation on the original sample database. Full interactive editing is
not covered. Historical backend version creation still has a known failure.

## Flake applications

The flake exposes named apps with `meta.description` strings:

| Command | Purpose |
| --- | --- |
| `nix run` or `nix run .#pyxi` | Graphical Pyxi browser/editor (default app) |
| `nix run .#xumain` | Interactive protocol console (creates/opens `./enf.enf`) |
| `nix run .#backend` | Pipe-protocol backend, for frontend integration |
| `nix run .#backenddaemon` | Historical network backend daemon, for advanced use |

`xumain` operates in the current directory, which must be writable.
The two low-level backend apps do not provide a user interface on their own;
they require the corresponding client and protocol setup. Pyxi is the
recommended interactive entry point and keeps its database under XDG state.

## Pyxi backend failures

Pyxi's pipe client now reports the actual backend exit status and the contents
of `backenderror` when the backend exits unexpectedly, rather than only a
Python `BrokenPipeError`. The backend writes that log in its working directory,
normally `${XDG_STATE_HOME:-$HOME/.local/state}/udanax-green/be`. Pyxi changes
its working directory after spawning the backend, so its diagnostic helper
retains the original backend working directory; otherwise it would miss the
log and show only the signal number.

If the GUI fails while opening the startup document, test against **a fresh
copy of the sample database** without deleting your current database:

```sh
XDG_STATE_HOME="$(mktemp -d)" nix run .#pyxi
```

This discriminates a database-state problem from a reproducible backend or
frontend problem. Do not delete or overwrite an existing `enf.enf` merely
because Pyxi has exited. The backend still requires further 64-bit and database
compatibility work.

The flake also uses `stdenv.hostPlatform.system` instead of the deprecated
`pkgs.system` attribute.


## Isolating Pyxi database crashes

The normal `nix run .#pyxi` stores its database in
`$XDG_STATE_HOME/udanax-green/be/enf.enf` (default
`~/.local/state/udanax-green/be/enf.enf`). The backend may exit with
SIGABRT, leaving Pyxi reporting a broken pipe. This does not by itself
identify whether the error is caused by the database, allocator, or protocol.

Run `nix run .#pyxi-clean` to use a **separate persistent database** in
`$XDG_STATE_HOME/udanax-green-clean` without touching the original.
This is a diagnostic launch, not a repair of the original state. Do not
copy or delete the failing database without a backup. The backend diagnostic
file is `be/backenderror` under the selected state directory. A custom
state directory can also be selected with `UDANAX_GREEN_STATE_DIR=/path`.

## Investigating SIGABRT on an existing database

The backend's reported exit status `-6` is SIGABRT, not a Python transport
failure. On the normal Pyxi launcher, inspect the log **before running again**
(it is overwritten each time the backend starts):

```sh
cat "${XDG_STATE_HOME:-$HOME/.local/state}/udanax-green/be/backenderror"
```

`nix run .#pyxi-clean` uses a separate, persistent sample database and is a
safe control test. If it works while the normal app crashes, preserve the
original `enf.enf` for debugging. Neither an abort signal nor the presence of
`backenderror` alone proves that the database is corrupted. The GUI regression
suite checks log collection even when the GUI changes its working directory.

## Read-only sample database and Tk selection fixes

The sample database shipped in the Nix store is mode `0444`. Older Pyxi
launchers copied it directly into the persistent state directory without
adding write permission, so opening a document caused `initenffile: Permission
denied` and a `SIGABRT`/broken pipe. The launcher now uses
`scripts/prepare-pyxi-state.sh` to make its *private copy* owner-writable,
including copies left by earlier versions. It never overwrites existing data
and refuses database symlinks. Run `nix run .#pyxi` after updating; there is
no need to delete or reset the old database.

On modern Python/Tk, `Text.tag_ranges("sel")` returns `_tkinter.Tcl_Obj`
indices rather than strings. The original `XuText.position()` rejected those
objects, producing `TypeError: 7.193 is not an index, position, or address`
when using **Link → Add Source End** or **Add Target End**. Pyxi now accepts
Tk index objects and normalizes selection ranges to strings. The flake check
runs `tests/pyxi-tk-selection.py` on a private Xvfb server to exercise both
link-menu callbacks using actual Tk selection indices. This validates adding
link ends to the menu, not creating and following a complete backend link.

## Link navigation and discovering documents

Pyxi's original link navigation uses **Alt + left-click** on a source or
target link end. In read-only mode, this port also allows an **ordinary
left-click**. Source ends are blue and underlined; target ends have a shaded
background. Right-click an end to inspect its link and jump to individual
ends. While editing, ordinary clicks still position the caret or select
text, and Alt-click follows the link. The Link menu's **Create Link** command
now requires both a source and a target end. A new jump link can be
created, found, followed, and reopened on a disposable copy of `sample.enf` (see `tests/link-persistence.py`). Link creation in a
fresh, empty database currently fails and needs separate backend debugging.

**Document → Browse Linked Documents...** opens a navigable listing rooted at
the current document. It discovers documents through the backend's native
`find_links` and `follow_link` calls in **both directions**, shows brief text
excerpts, and can inspect a selected document or explore up to 100 connected
documents. Double-click (or **Open Selected**) to open an entry in the main
browser. The sample database's introduction has links to Declaration of
Independence documents. The address field above the editor also permits
opening known document IDs directly.

**This is not a full database enumeration.** Green's FeBe API has
`find_documents` *containing a specified content span*, but no documented
operation to list all document IDs. Documents that are not reachable by
links from the starting document may not appear. The browser does not parse
or modify the enfilade format directly; the historical backend itself can
rewrite database bookkeeping on otherwise read-only opens. Keep backups of
valuable databases.

`tests/pyxi-linked-documents.py` uses the real C backend with the shipped
sample database, Tk under Xvfb, ordinary link-click navigation, editable
text-click behavior, connected-document discovery, and opening a document
from the new browser. The test runs against a **temporary copied database**.

### Pyxi clipboard behavior

When **Enable Editing** is off, Pyxi's Tk text widget is truly disabled,
including X11 middle-button PRIMARY selection paste, Ctrl+V/Shift+Insert,
and Tk's other built-in mutation shortcuts. You can still select/copy text
and follow links. Pyxi briefly enables the widget internally when loading a
document, then restores the editing state.

When editing is on, Ctrl+V/Shift+Insert and middle-click paste are routed
through the Udanax backend in bounded chunks. Since the historical wire
protocol is Latin-1, pasting text outside that character set is rejected.
Tk's native Cut, Clear, Undo and Redo bindings are intercepted rather than
allowing them to silently desynchronize the GUI from the backend.

`tests/pyxi-paste.py` uses a private database copy and real Tk/Xvfb to
check that read-only paste makes no changes and editable paste survives a
document reload.

## Pyxi fonts, parallel Compare, and hidden controls

Document text defaults are now slightly larger: 16-pixel proportional Times
(previously 14) and 14-pixel monospaced Courier (previously 12). The
**View** menu contains the font-family and paragraph-spacing choices.
The toolbar's compact font is unchanged.

**View → Parallel View / Compare (Alt+P)** opens a second document pane.
The two panes share the existing window width and resize together; opening
Parallel View does not enlarge the window automatically.
Enter another document address in that pane, leave both panes in read-only
mode, then click **Compare** in the middle. This invokes Green's
`compare_versions` protocol request, coloring *shared underlying text spans*
and drawing correspondence lines between them; it is not a line-based diff.
Use Alt+P or the menu again to close the second pane. The sample Declaration
documents `1.1.0.1.0.3` and `1.1.0.1.0.3.1` have shared spans and are a
reproducible test case. A backend limitation noted in Pyxi's original code
means results may be wrong when a document contains multiple virtual copies
of the same span. The flake now exercises this view under Tk/Xvfb against the
actual backend (`tests/pyxi-compare.py`).

**Help → Controls and Shortcuts...** gives a reminder inside the app:

- **Alt+P:** toggle side-by-side parallel view; Compare is active only when
  both panes contain read-only documents.
- **Alt+Left / Alt+Right:** document history back/forward.
- **Alt+Q:** quit Pyxi.
- **Enter in the address field:** open the entered document address.
- **Left-click a highlighted link end in read-only mode:** follow its link.
  **Alt+left-click:** follow even while editing. **Right-click:** link
  properties and available endpoints.
- **Edit → Mark / Transclude / Move:** selection-based cross-document text
  sharing; the destination document must be editable.
- **Link → Add Source End / Add Target End / Create Link:** create links by
  selecting endpoint spans in documents. **Document → Browse Linked
  Documents...** explores graph-connected documents, not every document in
  the database.

The toolbar now separates the menu row (Document, Edit, Link, View, Help)
from the navigation row. The top address entry is a hierarchical Xanadu
document identifier (*tumbler*), not a version counter: related versions can
have distinct, nested addresses. The adjacent **Pending: 0** label is not
an editable field; it shows buffered insert/delete characters waiting to be
sent to the backend, turning green for inserts and red for deletions. It is
visible even when no edits are pending.

The help window now has section headings, bold shortcut names, aligned
explanations, and a scrollable read-only text area. It can also be reached
from the new **Help** menu. Font and layout options are now in **View**;
document creation/import/export and the linked-document browser remain in
**Document**.

New windows opened from Pyxi retain the parallel-view feature. The compare
layout now uses integer Tk width values and a compact center button, and
closing the parallel view also clears any active comparison highlights.

### Transcluding marked text in Pyxi

To reuse text without copying its underlying Xanadu content:

1. Open the **source** document. Select a non-empty passage and choose
   **Edit → Mark**. The marked passage is highlighted.
2. Navigate to the **destination** document (or another Pyxi window).
   The mark is kept even when the original document is closed or editing is
   toggled, although its highlight only appears while viewing the source.
3. Enable editing in the destination, place the insertion cursor, and choose
   **Edit → Transclude**. The mark is cleared after a successful transclusion.

Marking and transclusion use Green's `vcopy` protocol operation, which shares
underlying content; this is *not* a plain-text copy. **Move** requires its
editable source document to remain open. If no text is marked, invoking
Transclude now displays an actionable explanation instead of throwing a Tk
callback traceback. Edits to a marked source invalidate the mark. Pyxi flushes
pending destination text before transcluding so backend addresses stay aligned.

`tests/pyxi-transclude.py` exercises the workflow using a disposable copy of
`sample.enf`, real Tk widgets under Xvfb, and the original C backend. It tests
both navigation and editing-mode transitions, comparison of shared spans,
flushing buffered destination typing, and persistence after a backend restart.
The test is part of the flake's package check phase.

### Edit-menu portability and keyboard input

The Edit menu now explicitly disables Tk's historical tear-off item and
records the **Mark**, **Transclude**, and **Move** entry indices when creating
them. Previously, `updateeditmenu()` assumed a tear-off entry occupied index
zero. On Tk builds without that entry, the menu states were applied to the
wrong actions, and `tests/pyxi-transclude.py` failed while testing the
Transclude entry. The test now refers to the named entry indices.

`Browser.eh_key()` also treats X11 Caps Lock (`LockMask`) and Num Lock
(`Mod2Mask`) as non-editing modifiers. Previously, those states bypassed
Pyxi's backend-synchronized insertion buffer: Tk could show new characters
locally, but a reload would discard them. Ordinary typing and typing with
these locks active now take the same edit-buffer path. This does not enable
editing in read-only mode.

`tests/pyxi-typing.py` exercises the actual Enable Editing menu toggle and
Tk key events against the C backend under Xvfb. It verifies read-only
protection, plain/NumLock/CapsLock typing, edit-menu states, toggling edit
mode off and on, and persistence across reloads and backend restart. The
flake check phase runs this test alongside the Transclude and paste tests.
