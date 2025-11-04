"""
Py3DTiles Converter Module

Converts LAS/LAZ point clouds to Cesium 3D Tiles format using py3dtiles.
Handles CRS detection, coordinate transformation, and post-processing.

Extracted from runner/workflow.py for reuse in both Galaxy tool and local runner.
"""

import json
import subprocess
import sys
from pathlib import Path
from shutil import which
from typing import Any, Dict, Optional

import laspy


def uncompress_laz_to_las(laz_path: Path) -> Path:
    """
    Uncompress a LAZ file to LAS format.
    
    Returns path to the uncompressed LAS file.
    """
    las_path = laz_path.with_suffix('.las')
    
    # If LAS already exists and is newer than LAZ, no need to uncompress
    if las_path.exists():
        try:
            if las_path.stat().st_mtime >= laz_path.stat().st_mtime:
                return las_path
        except Exception:
            pass
    
    # Uncompress using laspy
    try:
        las = laspy.read(laz_path)
        las.write(str(las_path))
        return las_path
    except Exception as e:
        raise RuntimeError(f"Failed to uncompress {laz_path.name} to LAS: {e}")


def resolve_py3dtiles_executable() -> Path:
    """
    Find the py3dtiles executable in the current environment.
    
    Looks first in the same directory as the Python interpreter,
    then falls back to PATH search.
    """
    py3dtiles_exe = Path(sys.executable).with_name("py3dtiles")
    if py3dtiles_exe.exists():
        return py3dtiles_exe
    found = which("py3dtiles")
    if not found:
        raise RuntimeError("py3dtiles not found in venv or PATH")
    return Path(found)


def rewrite_child_tileset_uris_if_needed(tiles_dir: Path) -> bool:
    """
    Fix child tileset URIs in the main tileset.json if py3dtiles wrote them under points/.

    Some py3dtiles versions generate auxiliary tileset files (e.g., tileset.1.json)
    inside a 'points/' subfolder, while the main tileset.json may reference them as
    'tileset.N.json' (without the folder). This function rewrites those URIs to
    'points/tileset.N.json' when the corresponding file exists under tiles_dir/points/.

    Returns True when the file was modified, False otherwise.
    """
    main_tileset = tiles_dir / "tileset.json"
    points_dir = tiles_dir / "points"
    if not main_tileset.exists():
        return False
    try:
        with main_tileset.open("r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
    except Exception:
        return False

    modified: bool = False

    def maybe_fix_uri(obj: Dict[str, Any]) -> None:
        nonlocal modified
        if not isinstance(obj, dict):
            return
        uri_val = obj.get("uri")
        if isinstance(uri_val, str):
            # Only fix bare tileset.N.json (no path). Leave other URIs untouched.
            if uri_val.startswith("tileset.") and uri_val.endswith(".json") and "/" not in uri_val:
                candidate = points_dir / uri_val
                try:
                    if candidate.exists() and candidate.is_file():
                        obj["uri"] = f"points/{uri_val}"
                        modified = True
                except Exception:
                    # Best-effort; ignore FS errors
                    pass

    def walk(node: Dict[str, Any]) -> None:
        if not isinstance(node, dict):
            return
        content = node.get("content")
        if isinstance(content, dict):
            maybe_fix_uri(content)
        contents = node.get("contents")
        if isinstance(contents, list):
            for c in contents:
                if isinstance(c, dict):
                    maybe_fix_uri(c)
        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                if isinstance(child, dict):
                    walk(child)

    try:
        walk(data.get("root", {}))
    except Exception:
        # Do not block workflow on traversal issues
        return False

    if modified:
        try:
            with main_tileset.open("w", encoding="utf-8") as f:
                # Keep compact single-line JSON similar to generator output
                json.dump(data, f, separators=(",", ":"))
        except Exception:
            return False
    return modified


def normalize_sub_tileset_uris_in_points(tiles_dir: Path) -> int:
    """
    Normalize URIs inside sub-tileset JSONs located under tiles_dir/points.

    Some generated sub-tileset files (stored under the 'points/' folder) may
    incorrectly prefix their content URIs with 'points/'. Because those JSON
    files already live inside 'points/', such URIs resolve to 'points/points/...'
    at runtime and fail to load. This function strips that redundant prefix when
    the targeted file exists relative to the sub-tileset location.

    Returns the number of files modified.
    """
    points_dir = tiles_dir / "points"
    if not points_dir.exists() or not points_dir.is_dir():
        return 0

    def fix_uris_in_data(data: Dict[str, Any]) -> bool:
        modified_local = False

        def maybe_fix(obj: Dict[str, Any]) -> None:
            nonlocal modified_local
            if not isinstance(obj, dict):
                return
            uri_val = obj.get("uri")
            if isinstance(uri_val, str) and uri_val.startswith("points/"):
                trimmed = uri_val[len("points/") :]
                candidate = points_dir / trimmed
                try:
                    if candidate.exists() and candidate.is_file():
                        obj["uri"] = trimmed
                        modified_local = True
                except Exception:
                    pass

        def walk(node: Dict[str, Any]) -> None:
            if not isinstance(node, dict):
                return
            content = node.get("content")
            if isinstance(content, dict):
                maybe_fix(content)
            contents = node.get("contents")
            if isinstance(contents, list):
                for c in contents:
                    if isinstance(c, dict):
                        maybe_fix(c)
            children = node.get("children")
            if isinstance(children, list):
                for child in children:
                    if isinstance(child, dict):
                        walk(child)

        try:
            walk(data.get("root", {}))
        except Exception:
            return False
        return modified_local

    modified_count = 0
    for ts_file in points_dir.glob("tileset.*.json"):
        try:
            with ts_file.open("r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
        except Exception:
            continue
        if fix_uris_in_data(data):
            try:
                with ts_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f, separators=(",", ":"))
                modified_count += 1
            except Exception:
                # If we can't write, skip but do not fail the workflow
                pass
    return modified_count


def convert_las_to_3dtiles(
    input_path: Path,
    output_dir: Path,
    extra_fields: Optional[str] = None,
    srs_out: Optional[str] = "4978",
    overwrite: bool = False,
) -> Path:
    """
    Convert LAS/LAZ point cloud to Cesium 3D Tiles format.
    
    Args:
        input_path: Path to input LAS or LAZ file
        output_dir: Directory where tiles will be written
        extra_fields: Comma-separated list of extra fields to include (e.g., "PredInstance")
        srs_out: Output CRS EPSG code (default: "4978" for ECEF, None to preserve original)
        overwrite: If True, clear output directory before conversion
        
    Returns:
        Path to the generated tileset.json file
        
    Raises:
        RuntimeError: If conversion fails or py3dtiles is not found
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear output directory if overwrite requested
    if overwrite:
        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure we have an uncompressed LAS file (py3dtiles works better with LAS than LAZ)
    tiles_input = input_path
    if input_path.suffix.lower() == '.laz':
        try:
            tiles_input = uncompress_laz_to_las(input_path)
        except Exception:
            # If uncompression fails, try using the LAZ file directly
            tiles_input = input_path
    
    # Detect CRS from input file
    has_crs = False
    try:
        las_obj = laspy.read(tiles_input)
        try:
            crs = las_obj.header.parse_crs()
            has_crs = bool(crs)
        except Exception:
            pass
    except Exception:
        pass
    
    # Find py3dtiles executable
    py3dtiles_exe = resolve_py3dtiles_executable()
    
    # Build py3dtiles command
    cmd = [
        str(py3dtiles_exe),
        "convert",
        "--out",
        str(output_dir),
    ]
    
    # Transform to ECEF only if file has CRS metadata
    if has_crs and srs_out:
        # Transform to ECEF (EPSG:4978) for proper Cesium camera controls.
        # Even without a basemap, Cesium's 3D scene and camera rotation require ECEF coordinates
        # to work correctly. Without this, large UTM coordinates (~500k, ~5M) cause the camera
        # to rotate around Earth's center instead of the point cloud center.
        cmd += ["--srs_out", srs_out]
        cmd += ["--pyproj-always-xy"]  # Ensure axis order is always X,Y (East,North)
    # If file has no CRS: keep original coordinates without transformation.
    # This assumes coordinates are already in local/relative system suitable for visualization.
    
    # Add extra fields if specified
    if extra_fields:
        cmd += ["--extra-fields", extra_fields]
    
    # Add input file as final argument
    cmd.append(str(tiles_input))
    
    # Run py3dtiles conversion
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Write log file
    log_file = output_dir / "tiles_log.txt"
    log_file.write_text(proc.stdout)
    
    # Check for errors
    if proc.returncode != 0:
        raise RuntimeError(f"tiles conversion (py3dtiles) failed with exit code {proc.returncode}; see tiles_log.txt")
    
    tileset_json = output_dir / "tileset.json"
    if not tileset_json.exists():
        raise RuntimeError("tiles conversion did not produce tileset.json")
    
    # Post-process: fix potential URI issues in tileset structure
    try:
        modified_main = rewrite_child_tileset_uris_if_needed(output_dir)
        normalized_count = normalize_sub_tileset_uris_in_points(output_dir)
    except Exception:
        # URI fixes are best-effort; don't fail the conversion if they don't work
        pass
    
    return tileset_json

