#!/usr/bin/env bash
# Build a .zip that can be dropped straight into .minecraft/shaderpacks.
set -euo pipefail

cd "$(dirname "$0")/.."

name="VibrantVisuals"
version="$(git describe --tags --always --dirty 2>/dev/null || echo dev)"
out="build/${name}-${version}.zip"

mkdir -p build
rm -f "$out"

# Only shaders/ belongs in the pack; the repository's own tooling does not.
zip -r -q "$out" shaders LICENSE README.md

echo "$out"
