"""Convert one or more rasters to a COG formatted raster, in EPSG 3857."""

import argparse
import logging
from pathlib import Path
from types import SimpleNamespace

from geospatial_utils.raster.reprojection import reproject_raster

logger = logging.getLogger(__name__)

COMMAND = "reproject_raster"
DESCRIPTION = "Reproject a single raster into a different EPSG."

DEFAULT_EPSG_CODE = 3857


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--raster_path", type=Path, required=True, help="Path to the raster to be converted")
    parser.add_argument("--output_path", type=Path, required=True, help="Path to the save the reprojected raster to.")
    parser.add_argument("--epsg_code", type=int, required=True, help="EPSG code to reproject the raster to.")

    return parser


def main() -> None:
    """Entrypoint to the script."""

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run_from_cli(args)


def run_from_cli(args: SimpleNamespace) -> None:
    """The entrypoint when running from the centralised CLI."""
    # Call the main run function
    run(raster_path=args.raster_path, output_path=args.output_path, epsg_code=args.epsg_code)


def run(raster_path: str | Path, output_path: str | Path, epsg_code: int) -> None:
    """The main run function."""
    logging.info(f"Reprojecting raster to EPSG {epsg_code}")

    reproject_raster(input_path=raster_path, output_path=output_path, output_epsg_code=epsg_code)

    logging.info("Finished")


if __name__ == "__main__":
    main()
