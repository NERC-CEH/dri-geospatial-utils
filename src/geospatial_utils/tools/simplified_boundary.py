"""Create a simplified and buffered boundary of one or more rasters."""

import argparse
import logging
from pathlib import Path
from types import SimpleNamespace

from geospatial_utils.raster.boundary_simplification import extract_raster_boundary

logger = logging.getLogger(__name__)

COMMAND = "get_simplified_boundary"
DESCRIPTION = "Gets the boundary of a raster with simplified and buffered edges."


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Adds the command line arguments to the parser for the convert_to_cog CLI tool.

    Args:
        parser: Empty ArgumentParser object

    Returns:
        ArgumentParser object with arguments added.

    """
    parser.add_argument(
        "--output_dir",
        required=True,
        type=Path,
        help=(
            "Directory to save the boundary vector file to. Each raster will be saved using the original filename, "
            "with the suffix of {boundary}"
        ),
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--raster_path", type=Path, help="Path to the raster needing a boundary generated")
    input_group.add_argument(
        "--raster_dir",
        type=Path,
        help=("Directory containing raster files (.tif) to process. All matching rasters will be processed."),
    )

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
    run(
        raster_path=args.raster_path,
        raster_dir=args.raster_dir,
        output_dir=args.output_dir,
    )


def run(output_dir: Path, raster_path: Path = None, raster_dir: Path = None) -> None:
    """Generate simplified boundaries for one or more rasters.

    This wraps `extract_raster_boundary` and preserves the previous CLI behaviour.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if raster_path is not None:
        extract_raster_boundary(raster_path, output_dir.joinpath("footprint.geojson"), output_epsg_code=3857)

    elif raster_dir is not None:
        for raster_file in Path(raster_dir).rglob("*.tif"):
            logging.info(f"Processing {raster_file.name}")
            extract_raster_boundary(
                raster_file, output_dir.joinpath(f"{raster_file.stem}_footprint.geojson"), output_epsg_code=3857
            )

    else:
        raise ValueError("Either raster_path or raster_dir must be provided.")

    logging.info("Finished")


if __name__ == "__main__":
    main()
