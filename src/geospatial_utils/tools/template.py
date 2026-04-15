"""Convert one or more rasters to a COG formatted raster, in EPSG 3857."""

import argparse
import logging
from pathlib import Path
from types import SimpleNamespace

logger = logging.getLogger(__name__)

COMMAND = "convert_to_cog"
DESCRIPTION = "Convert raster(s) to COG format, reprojected into EPSG 3857."

DEFAULT_EPSG_CODE = 3857


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    # Example parser entry. Delete before use
    parser.add_argument("--raster_path", type=Path, help="Path to the raster to be converted")

    return parser


def main() -> None:
    """Entrypoint to the script. This is standardised to make registering the script with the core CLI easy
    DO NOT MODIFY
    """

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run_from_cli(args)


def run_from_cli(args: SimpleNamespace) -> None:
    """The entrypoint when running from the centralised CLI.

    The function definition must not change (i.e the `def run from cli(args: SimpleNamespace)):`, the contents of
    this function can be freely modified.

    However, it is advisable to put all core logic in subsequent functions, as this allows running from both the CLI
    and calling the main `run` function directly from anywhere else in the codebase if needed.

    """
    # Call the main run function
    run(raster_path=args.raster_path, raster_dir=args.raster_dir, output_dir=args.output_dir)


def run(raster_path: str | Path, raster_dir: str | Path, output_dir: str | Path) -> None:
    """The main run function."""
    logging.info("Converting to COG")

    logging.info("Finished")


if __name__ == "__main__":
    main()
