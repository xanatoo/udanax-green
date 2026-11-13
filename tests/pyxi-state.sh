#!/bin/sh
# Regression for read-only database copies from the Nix store and prior runs.
set -eu
root=$(mktemp -d)
trap 'rm -rf "$root"' EXIT HUP INT TERM
sample="$root/sample.enf"
state="$root/state"
backend="$root/backend"
printf 'original data\n' > "$sample"
chmod 0444 "$sample"
: > "$backend"
prepare="scripts/prepare-pyxi-state.sh"

sh "$prepare" "$state" "$backend" "$sample"
database="$state/be/enf.enf"
cmp "$sample" "$database"
[ -L "$state/be/backend" ]
# test the mode bits rather than -w, which returns true for root.
[ "$(stat -c %A "$database" | cut -c3)" = w ]
[ "$(stat -c %A "$sample" | cut -c3)" = - ]

# Never overwrite a database with user edits.
printf 'user edit\n' >> "$database"
sh "$prepare" "$state" "$backend" "$sample"
grep -q '^user edit$' "$database"

# Repair databases that an older Pyxi launcher copied read-only.
chmod 0444 "$database"
sh "$prepare" "$state" "$backend" "$sample"
[ "$(stat -c %A "$database" | cut -c3)" = w ]
grep -q '^user edit$' "$database"

# A database symlink must not make us chmod the Nix store's sample.
rm "$database"
ln -s "$sample" "$database"
if sh "$prepare" "$state" "$backend" "$sample" > "$root/output" 2>&1; then
    echo 'expected refusal of symlinked database' >&2
    exit 1
fi
[ "$(stat -c %A "$sample" | cut -c3)" = - ]

echo 'Pyxi writable state: passed'
