#!/usr/bin/env python3
"""Compile every program in shaders/ with glslangValidator.

OptiFine / Iris hand each shader stage to the driver after resolving
`#include` and prepending a block of standard macros.  This script does the
same thing so the pack can be checked without launching Minecraft, then maps
any reported line number back to the file the line actually came from.

Usage:
    tools/validate_shaders.py [--glslang PATH] [--shaders DIR] [--variant NAME]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

INCLUDE_RE = re.compile(r'^\s*#\s*include\s+"([^"]+)"\s*$')
# `const int colortex0Format = RGBA16F;` and friends are directives, not GLSL -
# OptiFine and Iris read them out of the source and drop them before the driver
# ever sees them, so the validator has to do the same.
BUFFER_FORMAT_RE = re.compile(r'^\s*const\s+int\s+\w+Format\s*=\s*\w+\s*;')
VERSION_RE = re.compile(r'^\s*#\s*version\b')
STAGE_BY_SUFFIX = {".vsh": "vert", ".gsh": "geom", ".fsh": "frag"}

# Macros OptiFine/Iris inject after the #version line of every stage.
BASE_MACROS = [
    "#define MC_VERSION 12104",
    "#define MC_GL_VERSION 460",
    "#define MC_GLSL_VERSION 460",
    "#define MC_OS_LINUX",
    "#define MC_GL_VENDOR_NVIDIA",
    "#define MC_GL_RENDERER_GEFORCE",
    "#define MC_RENDER_QUALITY 1.0",
    "#define MC_SHADOW_QUALITY 1.0",
    "#define MC_HAND_DEPTH 0.125",
    "#define MC_RENDER_STAGE_NONE 0",
    "#define MC_RENDER_STAGE_SKY 1",
    "#define MC_RENDER_STAGE_SUNSET 2",
    "#define MC_RENDER_STAGE_CUSTOM_SKY 3",
    "#define MC_RENDER_STAGE_SUN 4",
    "#define MC_RENDER_STAGE_MOON 5",
    "#define MC_RENDER_STAGE_STARS 6",
    "#define MC_RENDER_STAGE_VOID 7",
    "#define MC_RENDER_STAGE_TERRAIN_SOLID 8",
    "#define MC_RENDER_STAGE_TERRAIN_CUTOUT_MIPPED 9",
    "#define MC_RENDER_STAGE_TERRAIN_CUTOUT 10",
    "#define MC_RENDER_STAGE_ENTITIES 11",
    "#define MC_RENDER_STAGE_BLOCK_ENTITIES 12",
    "#define MC_RENDER_STAGE_DESTROY 13",
    "#define MC_RENDER_STAGE_OUTLINE 14",
    "#define MC_RENDER_STAGE_DEBUG 15",
    "#define MC_RENDER_STAGE_HAND_SOLID 16",
    "#define MC_RENDER_STAGE_TERRAIN_TRANSLUCENT 17",
    "#define MC_RENDER_STAGE_TRIPWIRE 18",
    "#define MC_RENDER_STAGE_PARTICLES 19",
    "#define MC_RENDER_STAGE_CLOUDS 20",
    "#define MC_RENDER_STAGE_RAIN_SNOW 21",
    "#define MC_RENDER_STAGE_WORLD_BORDER 22",
    "#define MC_RENDER_STAGE_HAND_TRANSLUCENT 23",
]

# Each variant re-compiles the whole pack with a different resource-pack /
# option combination so conditionally compiled branches get covered too.
VARIANTS = {
    "default": [],
    "labpbr": ["#define MC_NORMAL_MAP", "#define MC_SPECULAR_MAP",
               "#define MC_TEXTURE_FORMAT_LAB_PBR", "#define MC_TEXTURE_FORMAT_LAB_PBR_1_3"],
    "legacy": ["#undef MC_VERSION", "#define MC_VERSION 11605"],
    # 1.16 era: no render stage macros, so the fallback branches get exercised.
    "no_render_stages": ["#undef MC_VERSION", "#define MC_VERSION 11605"]
                        + [f"#undef {m.split()[1]}" for m in BASE_MACROS
                           if m.startswith("#define MC_RENDER_STAGE_")],
}


class Flattener:
    """Inlines #include directives and remembers where each line came from."""

    def __init__(self, root: Path):
        self.root = root
        self.lines: list[str] = []
        self.origin: list[tuple[Path, int]] = []

    def emit(self, text: str, source: Path, line_no: int) -> None:
        self.lines.append(text)
        self.origin.append((source, line_no))

    def resolve(self, target: str, includer: Path) -> Path:
        if target.startswith("/"):
            return self.root / target.lstrip("/")
        return includer.parent / target

    def expand(self, path: Path, stack: tuple[Path, ...] = ()) -> None:
        if path in stack:
            chain = " -> ".join(p.name for p in stack + (path,))
            raise RuntimeError(f"circular #include: {chain}")
        if not path.is_file():
            raise FileNotFoundError(path)
        for index, raw in enumerate(path.read_text().splitlines(), start=1):
            match = INCLUDE_RE.match(raw)
            if match:
                self.expand(self.resolve(match.group(1), path), stack + (path,))
            elif BUFFER_FORMAT_RE.match(raw):
                self.emit(f"// stripped directive: {raw.strip()}", path, index)
            else:
                self.emit(raw, path, index)


def flatten(entry: Path, root: Path, macros: list[str]) -> Flattener:
    flat = Flattener(root)
    body = Flattener(root)
    body.expand(entry)

    # The #version directive has to stay first; macros go directly after it.
    start = 0
    for i, line in enumerate(body.lines):
        if VERSION_RE.match(line):
            flat.emit(line, *body.origin[i])
            start = i + 1
            break
    else:
        raise RuntimeError(f"{entry} has no #version directive")

    for macro in BASE_MACROS + macros:
        flat.emit(macro, entry, 0)
    for i in range(start, len(body.lines)):
        flat.emit(body.lines[i], *body.origin[i])
    return flat


ERROR_LINE_RE = re.compile(r"^(ERROR|WARNING):\s*\d+:(\d+):(.*)$")


def remap(message: str, flat: Flattener, root: Path) -> str:
    out = []
    for line in message.splitlines():
        match = ERROR_LINE_RE.match(line)
        if not match:
            out.append(line)
            continue
        kind, lineno, rest = match.group(1), int(match.group(2)), match.group(3)
        if 1 <= lineno <= len(flat.origin):
            src, src_line = flat.origin[lineno - 1]
            try:
                shown = src.relative_to(root.parent)
            except ValueError:
                shown = src
            out.append(f"{kind}: {shown}:{src_line}:{rest}")
        else:
            out.append(line)
    return "\n".join(out)


def find_glslang(explicit: str | None) -> str:
    if explicit:
        return explicit
    for candidate in ("glslangValidator", "./glslang/bin/glslangValidator"):
        try:
            subprocess.run([candidate, "--version"], capture_output=True, check=True)
            return candidate
        except (OSError, subprocess.CalledProcessError):
            continue
    raise SystemExit("glslangValidator not found; pass --glslang PATH")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glslang")
    parser.add_argument("--shaders", default="java/shaders")
    parser.add_argument("--variant", action="append")
    args = parser.parse_args()

    root = Path(args.shaders).resolve()
    glslang = find_glslang(args.glslang)
    variants = args.variant or list(VARIANTS)

    programs = sorted(
        p for p in root.iterdir()
        if p.is_file() and p.suffix in STAGE_BY_SUFFIX
    )
    if not programs:
        raise SystemExit(f"no shader programs found in {root}")

    failures = 0
    checked = 0
    with tempfile.TemporaryDirectory() as tmp:
        for variant in variants:
            if variant not in VARIANTS:
                raise SystemExit(f"unknown variant '{variant}'")
            for program in programs:
                stage = STAGE_BY_SUFFIX[program.suffix]
                flat = flatten(program, root, VARIANTS[variant])
                staged = Path(tmp) / f"{variant}_{program.name}.{stage}"
                staged.write_text("\n".join(flat.lines) + "\n")
                result = subprocess.run(
                    [glslang, str(staged)], capture_output=True, text=True
                )
                checked += 1
                if result.returncode != 0:
                    failures += 1
                    print(f"\n=== FAIL [{variant}] {program.name} ===")
                    print(remap(result.stdout + result.stderr, flat, root))

    print(f"\n{checked - failures}/{checked} stage compilations passed "
          f"({len(programs)} stages x {len(variants)} variants)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
