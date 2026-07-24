"""Convert one or more rasters to a COG formatted raster, in EPSG 3857."""

import argparse
import logging
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from osgeo import gdal

from geospatial_utils.raster.raster_dataset import RasterDataset

logger = logging.getLogger(__name__)

COMMAND = "merge_rasters"
DESCRIPTION = "Merge two or more rasters together"


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    # Example parser entry. Delete before use
    parser.add_argument("--raster_paths", type=Path, nargs="+", help="Paths to the raster to be merged")
    parser.add_argument("--output_path", type=Path, help="Path to save the merged raster to")

    return parser


def main() -> None:
    """Entrypoint to the script"""

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run_from_cli(args)


def run_from_cli(args: SimpleNamespace) -> None:
    """The entrypoint when running from the centralised CLI."""
    # Call the main run function
    run(raster_paths=args.raster_paths, output_path=args.output_path)


def run(raster_paths: list[str | Path], output_path: str | Path) -> None:
    """The main run function."""
    logging.info("Checking input rasters")
    check_for_consistent_srs(raster_paths=raster_paths)

    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info("Building VRT")
        vrt_path = os.path.join(temp_dir, "merged.vrt")
        gdal.BuildVRT(vrt_path, [str(raster_path) for raster_path in raster_paths])

        logger.info("Converting to single raster")
        creation_options = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "ZLEVEL=9"]
        gdal.Warp(output_path, vrt_path, creationOptions=creation_options)

    logger.info("Finished")


def check_for_consistent_srs(raster_paths: list[Path | str]) -> None:
    epsg_code = None
    for raster in raster_paths:
        raster_ds = RasterDataset(raster)
        if epsg_code is None:
            epsg_code = raster_ds.epsg_code
            continue
        if epsg_code != raster_ds.epsg_code:
            raise ValueError("The epsg code is inconsistent between the provided rasters to be merged.")


def merge_rasters(raster_paths: list[Path | str]) -> None:
    pass


if __name__ == "__main__":
    main()
