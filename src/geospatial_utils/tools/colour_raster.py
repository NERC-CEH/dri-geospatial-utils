"""Convert one or more rasters to a COG formatted raster, in EPSG 3857."""

import argparse
import logging
from pathlib import Path
from types import SimpleNamespace

from geospatial_utils.raster.colour_raster import apply_colour_relief, create_legend

logger = logging.getLogger(__name__)

COMMAND = "colour_raster"
DESCRIPTION = "Apply a colourmap to a raster"

DEFAULT_EPSG_CODE = 3857


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--raster_path", type=Path, help="Path to the raster to be coloured")
    parser.add_argument("--output_path", type=Path, help="Path to save the output raster to.")
    parser.add_argument("--colourmap_path", type=Path, help="Path to the colourmap to apply to be converted")

    return parser


def main() -> None:
    """Entrypoint to the script. This is standardised to make registering the script with the core CLI easy."""

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
    run(raster_path=args.raster_path, output_path=args.output_path, colourmap_path=args.colourmap_path)


def run(raster_path: str | Path, output_path: str | Path, colourmap_path: str | Path) -> None:
    """The main run function."""
    output_path = Path(output_path)

    logger.info("Applying colourmap")
    apply_colour_relief(raster_path=raster_path, colourmap_path=colourmap_path, output_path=output_path)

    logger.info("Creating legend")
    create_legend(
        colourmap_path=colourmap_path, legend_path=output_path.parent.joinpath(f"{output_path.stem}_legend.json")
    )

    logger.info("Finished")


if __name__ == "__main__":
    main()
