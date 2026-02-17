"""Convert one or more rasters to a COG formatted raster, in EPSG 3857."""

import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

COMMAND = "convert_to_cog"
DESCRIPTION = "Convert raster(s) to COG format, reprojected into EPSG 3857."

DEFAULT_EPSG_CODE = 3857


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    # Example parser entry. Delete before use
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--raster_path", type=Path, help="Path to the raster to be converted")
    input_group.add_argument(
        "--raster_dir",
        type=Path,
        help=(
            "Path to the directory containing rasters to be converted. All .tif files found within this directory "
            "will be processed."
        ),
    )

    parser.add_argument(
        "--output_dir",
        required=True,
        type=Path,
        help=(
            "Directory to save the converted raster(s) to. Each raster will be saved using the original filename, "
            "with the suffix of `_{epsg_code}_colourised_cog`"
        ),
    )
    parser.add_argument(
        "--epsg_code",
        required=False,
        type=int,
        help=f"The EPSG code to reproject converted data to. Defaults to {DEFAULT_EPSG_CODE}",
    )

    return parser


def main() -> None:
    """Entrypoint to the script."""

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run(*args)


def run(*args, **kwargs) -> None:
    """The main run function."""
    logging.info("Converting to COG")

    logging.info("Finished")


if __name__ == "__main__":
    main()
