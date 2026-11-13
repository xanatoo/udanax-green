#!/bin/sh
# Run Green's original standalone backend against disposable databases.
set -eu
backend=${1:?usage: backend-smoke.sh /path/to/xumain /path/to/sample.enf}
sample=${2:?sample enfilade required}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
cd "$work"

# Empty input must not spin forever; it must close the new database.
timeout 10 "$backend" </dev/null >empty.out 2>empty.err
[ -s enf.enf ] || { echo 'EOF startup did not create a database' >&2; exit 1; }
[ ! -s empty.err ] || { cat empty.err >&2; exit 1; }

# Create a document, close the database, and retrieve its span after restart.
rm -f enf.enf
printf '11\n16\n' | timeout 10 "$backend" >created.out 2>created.err
grep -q 'new document: 0.0.1' created.out
printf '14\n0.0.1\n16\n' | timeout 10 "$backend" >created-reopen.out 2>created-reopen.err
grep -q 'docvspan is:' created-reopen.out
grep -q 'Good Bye.' created-reopen.out
[ ! -s created-reopen.err ] || { cat created-reopen.err >&2; exit 1; }

# Read an existing database and confirm its contents remain readable.
cp "$sample" enf.enf
printf '14\n1.1.0.1\n16\n' | timeout 10 "$backend" >read.out 2>read.err
grep -q 'docvspan is:' read.out
fgrep -q 'Good Bye.' read.out
[ -s enf.enf ]
[ ! -s read.err ] || { cat read.err >&2; exit 1; }

# A second process must be able to read the same document span.
printf '14\n1.1.0.1\n16\n' | timeout 10 "$backend" >restart.out 2>restart.err
grep -q 'Good Bye.' restart.out
sed -n '/docvspan is:/,/request?/p' read.out >first-span
sed -n '/docvspan is:/,/request?/p' restart.out >second-span
cmp first-span second-span
[ ! -s restart.err ] || { cat restart.err >&2; exit 1; }
echo 'Udanax Green backend startup/reopen smoke test passed'
