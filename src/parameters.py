"""
Parameter parsing for Py3DTiles conversion tool.

Handles command-line arguments for both Galaxy tool and standalone use.
"""

import argparse
from pathlib import Path
from typing import Optional


class Parameters:
    """
    Parameters for LAS/LAZ to 3D Tiles conversion.
    
    Attributes:
        input_path: Path to input LAS or LAZ file
        output_dir: Directory where tiles will be written
        extra_fields: Optional comma-separated list of extra fields to include
        srs_out: Output CRS EPSG code (default: "4978" for ECEF)
        overwrite: If True, clear output directory before conversion
    """
    
    def __init__(
        self,
        input_path: Path,
        output_dir: Path,
        extra_fields: Optional[str] = None,
        srs_out: Optional[str] = "4978",
        overwrite: bool = False,
    ):
        self.input_path = input_path
        self.output_dir = output_dir
        self.extra_fields = extra_fields
        self.srs_out = srs_out
        self.overwrite = overwrite
    
    @classmethod
    def from_args(cls, args=None):
        """Parse command-line arguments and return Parameters instance."""
        parser = argparse.ArgumentParser(
            description="Convert LAS/LAZ point clouds to Cesium 3D Tiles format",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        
        parser.add_argument(
            "--input",
            "--dataset-path",
            type=Path,
            required=True,
            dest="input_path",
            help="Input LAS or LAZ point cloud file",
        )
        
        parser.add_argument(
            "--output-dir",
            type=Path,
            required=True,
            dest="output_dir",
            help="Output directory for 3D tiles",
        )
        
        parser.add_argument(
            "--extra-fields",
            type=str,
            default=None,
            dest="extra_fields",
            help="Comma-separated list of extra fields to include (e.g., 'PredInstance' for segmentation)",
        )
        
        parser.add_argument(
            "--srs-out",
            type=str,
            default="4978",
            dest="srs_out",
            help="Output CRS EPSG code (default: 4978 for ECEF). Set to empty string to preserve original CRS.",
        )
        
        parser.add_argument(
            "--overwrite",
            action="store_true",
            default=False,
            help="Overwrite existing output directory if it exists",
        )
        
        parsed = parser.parse_args(args)
        
        # Convert empty string to None for srs_out
        srs_out = parsed.srs_out if parsed.srs_out else None
        
        return cls(
            input_path=parsed.input_path,
            output_dir=parsed.output_dir,
            extra_fields=parsed.extra_fields,
            srs_out=srs_out,
            overwrite=parsed.overwrite,
        )
    
    def __repr__(self):
        return (
            f"Parameters("
            f"input_path={self.input_path}, "
            f"output_dir={self.output_dir}, "
            f"extra_fields={self.extra_fields}, "
            f"srs_out={self.srs_out}, "
            f"overwrite={self.overwrite})"
        )

