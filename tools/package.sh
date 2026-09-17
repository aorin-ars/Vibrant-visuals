#!/usr/bin/env bash
# Build both distributable packs.
#
#   build/VibrantVisuals-<ver>.mcpack        Bedrock  -> open it, or drop in
#                                            com.mojang/resource_packs/
#   build/VibrantVisuals-Check-<ver>.mcpack  Bedrock  -> diagnostic; turns the
#                                            world magenta iff deferred
#                                            rendering is actually running
#   build/VibrantVisuals-Java-<ver>.zip      Java     -> .minecraft/shaderpacks/
set -euo pipefail

cd "$(dirname "$0")/.."

version="$(git describe --tags --always --dirty 2>/dev/null || echo dev)"
mkdir -p build

# Bedrock: manifest.json has to sit at the archive root, so zip from inside.
bedrock="build/VibrantVisuals-${version}.mcpack"
rm -f "$bedrock"
(cd bedrock && zip -r -q "../$bedrock" . -x '.*')
echo "$bedrock"

# Diagnostic: answers "is deferred rendering even running?" - see diagnostic/README.md
check="build/VibrantVisuals-Check-${version}.mcpack"
rm -f "$check"
(cd diagnostic && zip -r -q "../$check" . -x '.*' -x 'README.md')
echo "$check"

# Java: shaders/ has to sit at the archive root.
java="build/VibrantVisuals-Java-${version}.zip"
rm -f "$java"
(cd java && zip -r -q "../$java" shaders)
zip -q -j "$java" LICENSE
echo "$java"
