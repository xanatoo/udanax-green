#!/bin/sh
# Prepare Pyxi's writable runtime state. Never modify the Nix-store sample.
set -eu

if [ "$#" -ne 3 ]; then
    echo 'usage: prepare-pyxi-state.sh STATE-DIR BACKEND SAMPLE-ENF' >&2
    exit 2
fi
state=$1
backend=$2
sample=$3

directory="$state/be"
database="$directory/enf.enf"
mkdir -p "$directory"
if [ ! -e "$directory/backend" ]; then
    ln -s "$backend" "$directory/backend"
fi

# Refuse to chmod through a symlink: it might point into the immutable Nix store.
if [ -L "$database" ]; then
    echo "Pyxi: $database is a symlink; expected a private writable database copy" >&2
    exit 1
fi
if [ ! -e "$database" ]; then
    cp "$sample" "$database"
fi
# `cp` copies the Nix store file's read-only mode, so we must set owner-write
# even for an older state directory created by a previous launcher version.
if ! chmod u+w "$database"; then
    echo "Pyxi: cannot make database writable: $database" >&2
    exit 1
fi
if [ ! -w "$database" ]; then
    echo "Pyxi: database remains unwritable: $database" >&2
    exit 1
fi
