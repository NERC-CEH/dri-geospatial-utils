"""Generate the boundary geometry for one or more rasters."""

import argparse
import logging
from pathlib import Path
from types import SimpleNamespace

from geospatial_utils.raster.raster_boundary import raster_boundary

logger = logging.getLogger(__name__)

COMMAND = "raster_boundary"
DESCRIPTION = "Extract the boundary geometry for a raster."


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Adds the command line arguments to the parser for the convert_to_cog CLI tool.

    Args:
        parser: Empty ArgumentParser object

    Returns:
        ArgumentParser object with arguments added.

    """
    parser.add_argument("--raster_path", type=Path, help="Path to the raster to extract the boundary from")

    parser.add_argument(
        "--output_path",
        required=True,
        type=Path,
        help=("Path to save the generated geojson file to."),
    )

    return parser


def main() -> None:
    """Entrypoint to the script."""

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run_from_cli(args)


def run_from_cli(args: SimpleNamespace) -> None:
    """Run raster_boundary from the commandline."""
    # Call the main run function
    run(
        raster_path=args.raster_path,
        output_path=args.output_path,
    )


def run(
    raster_path: Path,
    output_path: Path,
) -> None:
    """Generates simplified boundaries for one or more rasters.

    Determines whether to process a single raster or all rasters in a directory.

    Args:
        raster_path: Path to the raster to create the boundary from.
        output_path: Location of the geojson file to create.

    Raises:
        ValueError: If neither raster_path nor raster_dir is provided.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    raster_boundary(raster_path=raster_path, output_path=output_path)

    logger.info("Finished")


if __name__ == "__main__":
    main()
