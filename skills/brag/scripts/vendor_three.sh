#!/bin/bash
# Vendor three.js locally as a classic script (window.THREE), so a render page needs no network and no module loader.
#   vendor_three.sh <project-dir>        writes <project-dir>/vendor/three.classic.js
# Pinned to 0.170.0 (published 2024-10-31, well past the two-week cooling-off for a new release). Needs node and npm.
# Change the pin only to a version at least two weeks old, and say so in plan.md.
set -euo pipefail
DIR="${1:?project dir}"
VER="0.170.0"
TMP="$(mktemp -d)"
npm install --prefix "$TMP" "three@$VER" --no-audit --no-fund --silent
mkdir -p "$DIR/vendor"
{
  printf '(function(){var exports={};var module={exports:exports};\n'
  cat "$TMP/node_modules/three/build/three.cjs"
  printf '\n;window.THREE=module.exports;})();\n'
} > "$DIR/vendor/three.classic.js"
echo "vendored three@$VER -> $DIR/vendor/three.classic.js ($(wc -c < "$DIR/vendor/three.classic.js") bytes)"
