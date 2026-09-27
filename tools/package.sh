#!/usr/bin/env bash
# Build the distributable packs.
#
#   tools/package.sh [--vanilla <bedrock-samples>/resource_pack]
#
#   build/VibrantUnbound-<ver>.mcpack         Bedrock  -> open it, or drop in
#                                             com.mojang/resource_packs/
#   build/VibrantUnbound-Relief-<ver>.mcpack  Bedrock  -> optional block relief
#                                             add-on; only with --vanilla, since
#                                             it is made from the vanilla
#                                             textures (personal use only)
#   build/VibrantVisuals-Check-<ver>.mcpack   Bedrock  -> diagnostic; turns the
#                                             world magenta iff deferred
#                                             rendering is actually running
#   build/VibrantVisuals-Java-<ver>.zip       Java     -> .minecraft/shaderpacks/
set -euo pipefail

cd "$(dirname "$0")/.."

vanilla=""
if [[ "${1:-}" == "--vanilla" ]]; then
  vanilla="${2:?--vanilla needs a path}"
fi

version="$(git describe --tags --always --dirty 2>/dev/null || echo dev)"
mkdir -p build

python3 tools/check_bedrock.py bedrock ${vanilla:+--vanilla "$vanilla"}
python3 tools/check_bedrock.py diagnostic >/dev/null

# Bedrock: manifest.json has to sit at the archive root, so zip from inside.
bedrock="build/VibrantUnbound-${version}.mcpack"
rm -f "$bedrock"
(cd bedrock && zip -r -q "../$bedrock" . -x '.*')
echo "$bedrock"

if [[ -n "$vanilla" ]]; then
  python3 tools/build_pbr.py --vanilla "$vanilla" --out build/pbr >/dev/null
  python3 tools/check_bedrock.py build/pbr
  relief="build/VibrantUnbound-Relief-${version}.mcpack"
  rm -f "$relief"
  (cd build/pbr && zip -r -q "../../$relief" . -x '.*')
  echo "$relief"
fi

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
