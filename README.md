# Py3DTiles Conversion Tool

Convert LAS/LAZ point clouds to Cesium 3D Tiles format with support for custom attributes.

## Overview

This tool wraps [py3dtiles](https://gitlab.com/py3dtiles/py3dtiles) to provide a simple, standardized interface for converting point cloud data into web-ready 3D Tiles. Unlike other conversion tools (e.g., gocesiumtiler), py3dtiles supports custom point attributes, which is essential for visualizing segmentation results and other specialized data.

**Key features:**
- Automatic CRS detection and ECEF transformation for proper Cesium visualization
- Support for custom point attributes (e.g., segmentation IDs)
- Automatic LAZ decompression
- Post-processing to fix tileset URI issues
- Designed for both Galaxy workflows and standalone use

## Installation

### Option 1: Conda Environment (Recommended for Galaxy)

```bash
cd tools/tool_py3dtiles
conda env create -f environment.yml
conda activate py3dtiles_env
```

### Option 2: pip (For local runner)

```bash
pip install py3dtiles>=11.0.0 laspy[lazrs,laszip]>=2.5 pyproj>=3.6
```

## Usage

### Standalone Command Line

```bash
python src/run.py \
  --input /path/to/pointcloud.laz \
  --output-dir /path/to/output \
  --extra-fields PredInstance \
  --srs-out 4978
```

### Parameters

- `--input` / `--dataset-path`: Input LAS or LAZ file (required)
- `--output-dir`: Output directory for 3D tiles (required)
- `--extra-fields`: Comma-separated list of extra attributes to include (e.g., "PredInstance")
- `--srs-out`: Output CRS EPSG code (default: "4978" for ECEF). Set to empty string to preserve original CRS
- `--overwrite`: Clear output directory before conversion

### Galaxy Tool

The tool is available as a Galaxy tool at `galaxy/tools/py3dtiles.xml`. It will:

1. Create a conda environment with py3dtiles and dependencies
2. Run the conversion with selected parameters
3. Output tileset.json and tile files

## Integration with Local Runner

The runner (`runner/workflow.py`) imports the converter module directly:

```python
from converter import convert_las_to_3dtiles

# In workflow
convert_las_to_3dtiles(
    input_path=tiles_input,
    output_dir=tiles_dir,
    extra_fields="PredInstance",
    srs_out="4978",
    overwrite=False,
)
```

This ensures both Galaxy and the local runner use identical conversion logic.

## How It Works

### 1. Input Validation
- Validates file exists and is LAS/LAZ format
- Automatically decompresses LAZ to LAS if needed (py3dtiles works better with uncompressed LAS)

### 2. CRS Detection
```python
las_obj = laspy.read(input_path)
crs = las_obj.header.parse_crs()
has_crs = bool(crs)
```

### 3. Coordinate Transformation
If CRS metadata is present, transforms to ECEF (EPSG:4978):
```bash
py3dtiles convert --srs_out 4978 --pyproj-always-xy --out output/ input.las
```

Without CRS metadata, preserves original coordinates (assumes local/relative system).

### 4. Custom Attributes
Includes extra fields in tiles for specialized visualization:
```bash
py3dtiles convert --extra-fields PredInstance --out output/ input.las
```

### 5. Post-Processing
Automatically fixes URI issues in tileset structure:
- Rewrites child tileset URIs if they're under `points/` subfolder
- Normalizes redundant `points/points/` prefixes in sub-tilesets

## Output

The tool generates a complete 3D Tileset directory structure:

```
output/
├── tileset.json          # Main tileset metadata
├── tiles_log.txt         # Conversion log
└── points/               # Tile files
    ├── r0.pnts
    ├── r1.pnts
    ├── tileset.1.json
    └── ...
```

### tileset.json

The main metadata file that describes the tile structure. This is what Cesium loads to display the point cloud.

### PNTS files

Binary 3D Tiles in point cloud format, organized in an octree structure for efficient LOD rendering.

## Coordinate Systems

### ECEF (EPSG:4978) - Default
- Earth-Centered, Earth-Fixed coordinate system
- Required for proper Cesium camera controls
- Prevents issues with large UTM coordinates causing incorrect camera rotation
- Used when input file has CRS metadata

### Original CRS - Fallback
- Used when input file has no CRS metadata
- Assumes coordinates are already in suitable local/relative system

## Why Py3DTiles?

While gocesiumtiler is faster, we use py3dtiles because:

1. **Custom Attributes**: Supports extra dimensional attributes (essential for segmentation visualization)
2. **Bug Fixes**: Includes fixes for specific coordinate transformation issues
3. **Python Integration**: Better integration with Python-based workflows
4. **Maintained**: Active development with recent improvements

## Technical Details

### CRS Transformation
Uses pyproj with `--pyproj-always-xy` flag to ensure consistent axis order (East, North) regardless of CRS definition.

### Performance
- Processes ~1M points/second (varies by hardware)
- Scales well to large datasets (100M+ points)
- Memory usage proportional to point count

### Compatibility
- Python 3.10+
- Works on Linux, macOS, Windows
- No GPU required

## Troubleshooting

### "py3dtiles not found"
Ensure py3dtiles is installed and the executable is in PATH:
```bash
which py3dtiles  # Should show path to executable
pip list | grep py3dtiles  # Should show version 11.0.0+
```

### "Failed to uncompress LAZ"
Install laspy with compression support:
```bash
pip install laspy[lazrs,laszip]
```

### "CRS transformation failed"
Check that pyproj is installed and can find PROJ data:
```bash
python -c "import pyproj; print(pyproj.datadir.get_data_dir())"
```

### Tileset loads in Cesium but camera is weird
If the point cloud has a CRS but camera rotates incorrectly, ensure `srs_out` is set to "4978" (ECEF).

## Development

### Module Structure
```
tools/tool_py3dtiles/
├── src/
│   ├── converter.py    # Core conversion logic
│   ├── parameters.py   # Argument parsing
│   └── run.py         # Main entry point
├── environment.yml    # Conda environment
└── README.md         # This file
```

### Testing
```bash
# Standalone test
python src/run.py --input test.laz --output-dir ./test_output

# Check output
ls -la test_output/
cat test_output/tiles_log.txt
```

## References

- [Py3DTiles GitLab](https://gitlab.com/py3dtiles/py3dtiles)
- [Cesium 3D Tiles Specification](https://github.com/CesiumGS/3d-tiles)
- [LAS Specification](https://www.asprs.org/divisions-committees/lidar-division/laser-las-file-format-exchange-activities)

## License

Developed by the 3D Trees Project. Py3dtiles is developed by the py3dtiles community.

## Support

For issues specific to this tool wrapper, open an issue in the 3D Trees repository.
For py3dtiles issues, see the [py3dtiles issue tracker](https://gitlab.com/py3dtiles/py3dtiles/-/issues).

