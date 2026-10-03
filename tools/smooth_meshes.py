#!/usr/bin/env python3
"""Smooth the shading of an add-on's mesh parts (poly_mesh), cubes untouched.

    tools/smooth_meshes.py <add-on .mcaddon/.mcpack/.zip or folder>
                           [--out build/smooth_meshes] [--angle 80] [--patch N]

Bedrock models are boxes ("cubes") and, in some add-ons, free-form meshes
("poly_mesh" in a bone): a list of positions shared between polygons, and
a normal for every polygon corner. The classic renderer shades with
exactly those normals, and most exporters write each polygon's own flat
normal, so a rounded mesh renders with a crease along
every edge even though its polygons share their vertices. Resource packs
cannot change the shaders, so the only fix is in the model file. (Models
whose normals are already smooth but which show creases only in Vibrant
Visuals are a different problem, in the renderer; this does not fix them.)

This tool rewrites the normals of every poly_mesh: each corner gets the
average of the normals of the polygons that share its vertex (weighted by
polygon area), so the surface shades smoothly across the shared edges.
Edges sharper than --angle degrees (default 80) stay sharp, so the caps
of a cylinder or a real corner keep their edge while curved surfaces lose
their facets; --angle 180 smooths everything that shares a vertex. Cubes
are left exactly as they are - they are meant to have edges.

The result is a separate resource pack to place ABOVE the add-on, holding
only the geometry files that contain meshes, with the same paths and
geometry identifiers so they replace the add-on's own. The add-on itself
is not modified. Like the add-on, the output is for personal use.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def load_json(data: bytes):
    text = data.decode("utf-8-sig")
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return json.loads(text)


def read_addon(path: Path) -> dict[str, bytes]:
    if path.is_dir():
        return {p.relative_to(path).as_posix(): p.read_bytes() for p in path.rglob("*") if p.is_file()}
    with zipfile.ZipFile(path) as z:
        return {i.filename: z.read(i) for i in z.infolist() if not i.is_dir()}


# --------------------------------------------------------------------------
# Normals
# --------------------------------------------------------------------------

def corners(mesh: dict) -> list[list[tuple[int, int, int]]]:
    """Polygons as lists of (position, normal, uv) indices, whichever of the
    two layouts the mesh uses."""
    polys = mesh.get("polys")
    if isinstance(polys, list):
        return [[tuple(int(i) for i in c) for c in poly] for poly in polys]
    # "tri_list" / "quad_list": positions, normals and uvs run in step.
    size = 3 if polys == "tri_list" else 4
    n = len(mesh.get("positions", []))
    return [[(i, i, i) for i in range(start, start + size)] for start in range(0, n - size + 1, size)]


def shared_positions(positions: np.ndarray) -> np.ndarray:
    """Index of the first position equal to each one. Meshes in list layout
    repeat a vertex for every polygon; equal coordinates are one vertex."""
    keys = np.round(positions, 4)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return first[inverse.reshape(-1)]


def smooth(mesh: dict, max_angle: float) -> tuple[dict, int]:
    """New mesh with smoothed corner normals; also how many corners changed."""
    positions = np.asarray(mesh.get("positions", []), np.float64).reshape(-1, 3)
    old_normals = np.asarray(mesh.get("normals", []), np.float64).reshape(-1, 3)
    polys = corners(mesh)
    if not len(positions) or not polys:
        return mesh, 0
    vertex = shared_positions(positions)

    # Face normals from the geometry (Newell's method copes with quads that
    # are not quite flat) and areas, for weighting.
    face_n = np.zeros((len(polys), 3))
    for f, poly in enumerate(polys):
        pts = positions[[c[0] for c in poly]]
        nxt = np.roll(pts, -1, axis=0)
        face_n[f] = 0.5 * np.array([
            np.sum((pts[:, 1] - nxt[:, 1]) * (pts[:, 2] + nxt[:, 2])),
            np.sum((pts[:, 2] - nxt[:, 2]) * (pts[:, 0] + nxt[:, 0])),
            np.sum((pts[:, 0] - nxt[:, 0]) * (pts[:, 1] + nxt[:, 1]))])
    area = np.linalg.norm(face_n, axis=1)
    unit = face_n / np.maximum(area, 1e-12)[:, None]

    # Match the file's own conventions (winding, mirrored axes): compare the
    # computed face normals with the normals the file gives each polygon.
    given = np.zeros_like(unit)
    for f, poly in enumerate(polys):
        idx = [c[1] for c in poly if 0 <= c[1] < len(old_normals)]
        if idx:
            given[f] = old_normals[idx].sum(axis=0)
    signs = np.ones(3)
    if np.abs(given).sum() > 0:
        corr = (unit * given).sum(axis=0)
        signs = np.where(corr < 0, -1.0, 1.0)
        # Axis-wise agreement can be ambiguous on flat meshes; fall back to
        # overall agreement.
        if np.all(np.abs(corr) < 1e-9):
            signs[:] = 1.0 if (unit * given).sum() >= 0 else -1.0
    unit *= signs
    face_n *= signs
    degenerate = area < 1e-12

    # Corner normals: polygons around the same vertex whose faces are within
    # max_angle of this one.
    by_vertex: dict[int, list[int]] = {}
    for f, poly in enumerate(polys):
        for c in poly:
            by_vertex.setdefault(int(vertex[c[0]]), []).append(f)
    cos_limit = np.cos(np.radians(max_angle))
    new_normals: list[tuple[float, float, float]] = []
    lookup: dict[tuple[float, float, float], int] = {}
    new_polys = []
    changed = 0
    for f, poly in enumerate(polys):
        out = []
        for p, n, t in poly:
            if degenerate[f]:
                vec = old_normals[n] if 0 <= n < len(old_normals) else np.array([0.0, 1.0, 0.0])
            else:
                around = [g for g in set(by_vertex[int(vertex[p])])
                          if not degenerate[g] and unit[g] @ unit[f] >= cos_limit]
                vec = face_n[around].sum(axis=0)
                if np.linalg.norm(vec) < 1e-12:
                    vec = unit[f]
            vec = vec / max(np.linalg.norm(vec), 1e-12)
            key = tuple(float(round(v, 5)) for v in vec)
            if key not in lookup:
                lookup[key] = len(new_normals)
                new_normals.append(key)
            if 0 <= n < len(old_normals) and np.dot(old_normals[n] / max(np.linalg.norm(old_normals[n]), 1e-12), vec) < 0.9999:
                changed += 1
            out.append([p, lookup[key], t])
        new_polys.append(out)

    new = dict(mesh)
    new["normals"] = [list(v) for v in new_normals]
    if isinstance(mesh.get("polys"), list):
        new["polys"] = new_polys
    else:
        # List layout: one normal per listed corner, in order.
        flat = [new_normals[c[1]] for poly in new_polys for c in poly]
        new["normals"] = [list(v) for v in flat]
    return new, changed


# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("addon", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "build/smooth_meshes")
    parser.add_argument("--angle", type=float, default=80.0,
                        help="edges sharper than this many degrees stay sharp (180: none)")
    parser.add_argument("--patch", type=int, default=0, help="patch number of the pack version")
    args = parser.parse_args()

    files = read_addon(args.addon)
    roots = []
    for name, data in files.items():
        if name.endswith("manifest.json"):
            try:
                manifest = load_json(data)
            except ValueError:
                continue
            if any(m.get("type") == "resources" for m in manifest.get("modules", [])):
                roots.append((name[: -len("manifest.json")], manifest["header"].get("name", "add-on")))
    if not roots:
        print(f"{args.addon}: no resource pack found")
        return 1
    if args.out.exists():
        shutil.rmtree(args.out)

    written = 0
    for root, _ in roots:
        for name, data in sorted(files.items()):
            if not (name.startswith(root) and name.endswith(".json") and b"poly_mesh" in data):
                continue
            try:
                doc = load_json(data)
            except ValueError:
                print(f"{name}: not valid JSON - skipped")
                continue
            meshes = changed = 0
            geos = list(doc.get("minecraft:geometry", []))
            geos += [g for k, g in doc.items() if k.startswith("geometry.") and isinstance(g, dict)]
            for geo in geos:
                for bone in geo.get("bones", []):
                    if isinstance(bone.get("poly_mesh"), dict):
                        bone["poly_mesh"], n = smooth(bone["poly_mesh"], args.angle)
                        meshes += 1
                        changed += n
            if not meshes:
                continue
            dest = args.out / name[len(root):]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                            encoding="utf-8")
            written += 1
            print(f"{name[len(root):]}: {meshes} meshes, {changed} corner normals smoothed")

    if not written:
        print("no poly_mesh parts in this add-on - nothing to smooth (box models already "
              "shade as intended)")
        return 0
    name = " / ".join(n for _, n in roots)
    seed = uuid.uuid5(uuid.NAMESPACE_URL, "vyse-smooth-meshes:" + name)
    version = [1, 0, args.patch]
    manifest = {
        "format_version": 2,
        "header": {
            "name": f"VYSE Smooth - {name}",
            "description": "Smooth shading for this add-on's mesh parts (cubes unchanged). "
                           "Place above the add-on. Personal use only.",
            "uuid": str(uuid.uuid5(seed, "header")),
            "version": version,
            "min_engine_version": [1, 21, 0],
        },
        "modules": [{"type": "resources", "uuid": str(uuid.uuid5(seed, "module")),
                     "version": version}],
    }
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    shutil.copy2(ROOT / "bedrock/pack_icon.png", args.out / "pack_icon.png")
    print(f"{args.out}: {manifest['header']['name']}, {written} geometry files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
