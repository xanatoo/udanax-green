#!/bin/sh
# Exercise the original command protocol with a disposable real database.
set -eu
backend=${1:?usage: text-persistence.sh /path/to/xumain}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
cd "$work"

# Create document 0.0.1, insert text at v-address 1 and close cleanly.
printf '11\n0\nhello Green\n\n0.0.1\n1\n16\n' |
  timeout 10 "$backend" >insert.out 2>insert.err
grep -q 'new document: 0.0.1' insert.out
grep -q 'Good Bye.' insert.out
[ -s enf.enf ]

# Retrieval uses a vspec for the new document and an explicit vspan.
# The request is made in a separate process so it must read from disk.
printf '5\ny\nn\n0.0.1\ny\n1\n12\nn\nn\n16\n' |
  timeout 10 "$backend" >read.out 2>read.err
grep -q 'hello Green' read.out
grep -q 'vstuff is:' read.out
grep -q 'Good Bye.' read.out

# Reopen again to ensure the first read did not damage the database.
printf '5\ny\nn\n0.0.1\ny\n1\n12\nn\nn\n16\n' |
  timeout 10 "$backend" >repeat.out 2>repeat.err
cmp read.out repeat.out
[ ! -s read.err ] && [ ! -s repeat.err ] || {
  cat read.err repeat.err >&2; exit 1;
}
echo 'Udanax Green text insert/retrieve/restart passed'
