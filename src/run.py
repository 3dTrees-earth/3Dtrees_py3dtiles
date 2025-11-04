#!/usr/bin/env python
"""
Py3DTiles Conversion Tool - Main Entry Point

Converts LAS/LAZ point clouds to Cesium 3D Tiles format.
Designed for use in Galaxy workflows and standalone execution.
"""

import logging
import sys
from pathlib import Path

from parameters import Parameters
from converter import convert_las_to_3dtiles


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the conversion tool."""
    try:
        # Parse command-line arguments
        params = Parameters.from_args()
        logger.info(f"Starting conversion with parameters: {params}")
        
        # Validate input file exists
        if not params.input_path.exists():
            logger.error(f"Input file not found: {params.input_path}")
            sys.exit(1)
        
        # Validate input file format
        if params.input_path.suffix.lower() not in ['.las', '.laz']:
            logger.error(f"Input file must be LAS or LAZ format, got: {params.input_path.suffix}")
            sys.exit(1)
        
        # Run conversion
        logger.info(f"Converting {params.input_path} to 3D Tiles...")
        tileset_json = convert_las_to_3dtiles(
            input_path=params.input_path,
            output_dir=params.output_dir,
            extra_fields=params.extra_fields,
            srs_out=params.srs_out,
            overwrite=params.overwrite,
        )
        
        logger.info(f"Conversion completed successfully!")
        logger.info(f"Tileset written to: {tileset_json}")
        logger.info(f"Output directory: {params.output_dir}")
        
        # List output files for verification
        output_files = list(params.output_dir.rglob("*"))
        logger.info(f"Generated {len(output_files)} files in output directory")
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

