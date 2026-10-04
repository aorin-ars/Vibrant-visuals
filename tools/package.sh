#!/usr/bin/env bash
# Build the distributable packs.
#
#   tools/package.sh [--vanilla <bedrock-samples>/resource_pack]
#
#   build/VYSE-Vibrant-Visuals-<ver>.mcpack   Bedrock  -> open it, or drop in
#                                             com.mojang/resource_packs/
#   build/VYSE-Vibrant-Visuals-PBR-<ver>.mcpack Bedrock  -> optional PBR add-on:
#                                             block relief, glow, shine; only
#                                             with --vanilla, since it is made
#                                             from the vanilla textures
#                                             (personal use only)
#   build/VYSE-Weather-Sync-<ver>.mcpack      Bedrock  -> optional behavior pack:
#                                             restores the rainy sky after
#                                             rejoining a world while it rains
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

# Bedrock refuses to re-import a pack whose uuid and version it already has:
# it keeps the installed copy and says nothing useful, so a rebuilt pack with
# an unchanged version silently never reaches the game. The build therefore
# stamps the patch number with the commit count, which rises with every
# commit. The repository copy keeps its hand-set major.minor.
stage="build/stage/bedrock"
rm -rf build/stage
mkdir -p build/stage
cp -r bedrock "$stage"
patch="$(git rev-list --count HEAD 2>/dev/null || echo 0)"
python3 - "$stage/manifest.json" "$patch" <<'EOF'
import json, sys
path, patch = sys.argv[1], int(sys.argv[2])
manifest = json.load(open(path, encoding="utf-8"))
for entry in [manifest["header"]] + manifest["modules"]:
    entry["version"] = entry["version"][:2] + [patch]
open(path, "w", encoding="utf-8").write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print("pack version", ".".join(map(str, manifest["header"]["version"])))
EOF

# Bedrock: manifest.json has to sit at the archive root, so zip from inside.
bedrock="build/VYSE-Vibrant-Visuals-${version}.mcpack"
rm -f "$bedrock"
(cd "$stage" && zip -r -q "../../../$bedrock" . -x '.*')
rm -rf build/stage
echo "$bedrock"

if [[ -n "$vanilla" ]]; then
  python3 tools/build_pbr.py --vanilla "$vanilla" --out build/pbr --patch "$patch" >/dev/null
  python3 tools/check_bedrock.py build/pbr
  pbr="build/VYSE-Vibrant-Visuals-PBR-${version}.mcpack"
  rm -f "$pbr"
  (cd build/pbr && zip -r -q "../../$pbr" . -x '.*')
  echo "$pbr"
fi

# Behavior pack: resends rain after rejoining a rainy world (the game shows
# a clear sky until the weather changes). Same patch stamping as above.
sync_stage="build/stage/weather_sync"
rm -rf "$sync_stage" && mkdir -p build/stage && cp -r weather_sync "$sync_stage"
python3 - "$sync_stage/manifest.json" "$patch" <<'PYEOF'
import json, sys
path, patch = sys.argv[1], int(sys.argv[2])
manifest = json.load(open(path, encoding="utf-8"))
for entry in [manifest["header"]] + manifest["modules"]:
    entry["version"] = entry["version"][:2] + [patch]
open(path, "w", encoding="utf-8").write(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
PYEOF
sync="build/VYSE-Weather-Sync-${version}.mcpack"
rm -f "$sync"
(cd "$sync_stage" && zip -r -q "../../../$sync" . -x '.*')
rm -rf build/stage
echo "$sync"

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
