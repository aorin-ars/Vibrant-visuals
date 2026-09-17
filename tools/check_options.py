#!/usr/bin/env python3
"""Cross-check the options system.

An option that is listed on a screen but never defined in GLSL, or defined but
never given a label, fails silently in game - the screen just shows a raw
identifier or drops the entry. This walks the three places an option has to
appear and reports anything that only shows up in some of them.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SHADERS = Path("java/shaders")

DEFINE_RE = re.compile(r'^\s*#define\s+([A-Za-z_]\w*)\b(.*)$')
CONST_RE = re.compile(r'^\s*const\s+\w+\s+([A-Za-z_]\w*)\s*=\s*[^;]+;\s*(//\s*\[.*\])?')
VALUE_LIST_RE = re.compile(r'//\s*\[([^\]]*)\]')

# Listed on a screen but supplied by the loader rather than by the pack.
BUILTIN_OPTIONS = {"ambientOcclusionLevel", "sunPathRotation", "shadowMapResolution",
                   "shadowDistance", "entityShadowDistanceMul"}


def collect_glsl_options() -> tuple[dict[str, list[str]], set[str]]:
    """Returns {option: [values]} for value options, and the set of toggles."""
    values: dict[str, list[str]] = {}
    toggles: set[str] = set()

    for path in sorted(SHADERS.rglob("*")):
        if path.suffix not in {".glsl", ".vsh", ".fsh", ".gsh"}:
            continue
        for line in path.read_text().splitlines():
            const = CONST_RE.match(line)
            if const:
                listed = VALUE_LIST_RE.search(line)
                if listed:
                    values[const.group(1)] = listed.group(1).split()
                continue

            define = DEFINE_RE.match(line)
            if not define:
                continue
            name, rest = define.group(1), define.group(2)
            listed = VALUE_LIST_RE.search(rest)
            if listed:
                values[name] = listed.group(1).split()
            elif not rest.strip() or rest.strip().startswith("//"):
                toggles.add(name)

    return values, toggles


def collect_properties_options() -> tuple[set[str], set[str], dict[str, set[str]]]:
    text = (SHADERS / "shaders.properties").read_text()
    text = re.sub(r"\\\s*\n", " ", text)          # join continuation lines

    screens: set[str] = set()
    sliders: set[str] = set()
    profiles: dict[str, set[str]] = {}

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, rhs = line.partition("=")
        key, rhs = key.strip(), rhs.strip()

        if key == "screen" or key.startswith("screen."):
            screens |= {t for t in rhs.split()
                        if not t.startswith("[") and not t.startswith("<")}
        elif key == "sliders":
            sliders |= set(rhs.split())
        elif key.startswith("profile."):
            profiles[key[len("profile."):]] = {
                t.lstrip("!").split(":")[0] for t in rhs.split()
            }

    return screens, sliders, profiles


def collect_lang(path: Path) -> tuple[set[str], set[tuple[str, str]]]:
    labels: set[str] = set()
    values: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("option.") and ".comment" not in line:
            labels.add(line.split("=", 1)[0][len("option."):])
        elif line.startswith("value."):
            key = line.split("=", 1)[0][len("value."):]
            name, _, value = key.rpartition(".")
            values.add((name, value))
    return labels, values


def check_properties_files() -> list[str]:
    """Both loaders read these with java.util.Properties semantics."""
    problems = []
    for path in sorted(SHADERS.glob("*.properties")):
        joined = re.sub(r"\\\s*\n\s*", " ", path.read_text())
        keys: list[str] = []
        for line in joined.splitlines():
            line = line.strip()
            if not line or line[0] in "#!":
                continue
            if "=" not in line:
                problems.append(f"{path.name}: line without '=': {line[:60]}")
                continue
            keys.append(line.split("=", 1)[0].strip())
        for key in sorted({k for k in keys if keys.count(k) > 1}):
            problems.append(f"{path.name}: duplicate key {key}")
    return problems


def main() -> int:
    glsl_values, glsl_toggles = collect_glsl_options()
    defined = set(glsl_values) | glsl_toggles | BUILTIN_OPTIONS
    screens, sliders, profiles = collect_properties_options()

    problems: list[str] = check_properties_files()

    for name in sorted(screens - defined):
        problems.append(f"on a screen but never defined in GLSL: {name}")
    for name in sorted(sliders - defined):
        problems.append(f"listed as a slider but never defined: {name}")
    for name in sorted(sliders - screens):
        problems.append(f"listed as a slider but on no screen: {name}")
    for profile, options in sorted(profiles.items()):
        for name in sorted(options - defined):
            problems.append(f"profile {profile} sets an undefined option: {name}")

    for name in sorted(glsl_values):
        if name in screens and name not in sliders:
            problems.append(f"value option not declared as a slider: {name}")

    for lang in sorted((SHADERS / "lang").glob("*.lang")):
        labels, value_labels = collect_lang(lang)
        for name in sorted(screens - labels):
            problems.append(f"{lang.name}: no label for {name}")
        for name in sorted(labels - screens):
            problems.append(f"{lang.name}: label for an option on no screen: {name}")
        # An option is an enumeration if any of its values was given a name.
        # Numeric options - sample counts, step counts - read fine as numbers,
        # but a partly labelled enumeration shows raw indices for the rest.
        labelled = {name for name, _ in value_labels}
        for name in sorted(labelled & set(glsl_values)):
            for value in glsl_values[name]:
                if (name, value) not in value_labels:
                    problems.append(f"{lang.name}: no label for {name} = {value}")

    if problems:
        print("\n".join(f"  {p}" for p in problems))
        print(f"\n{len(problems)} problem(s)")
        return 1

    print(f"options consistent: {len(screens)} on screens, "
          f"{len(sliders)} sliders, {len(profiles)} profiles, "
          f"{len(list((SHADERS / 'lang').glob('*.lang')))} languages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
