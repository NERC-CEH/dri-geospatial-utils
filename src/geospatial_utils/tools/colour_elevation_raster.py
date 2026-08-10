"""Apply a colourmap to an elevation raster, combining it with hillshading"""

import argparse
import logging
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from geospatial_utils.raster.colour_raster import apply_colour_relief, apply_hillshade, create_legend

logger = logging.getLogger(__name__)

COMMAND = "colour_elevation_raster"
DESCRIPTION = "Apply a colourmap to an elevation raster, combining it with hillshading"

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

    with tempfile.TemporaryDirectory() as temp_directory:
        temp_dir = Path(temp_directory)

        logger.info("Creating initial coloured raster")
        coloured_raster_path = temp_dir.joinpath(f"{raster_path.stem}_coloured.tif")
        apply_colour_relief(raster_path=raster_path, colourmap_path=colourmap_path, output_path=coloured_raster_path)

        logger.info("Creating hillshade raster")
        hillshade_raster_path = temp_dir.joinpath(f"{raster_path.stem}_hillshade.tif")
        apply_hillshade(raster_path=raster_path, output_path=hillshade_raster_path)

        logger.info("Combining coloured and hillshade rasters")
        subprocess.run(
            [
                "gdal",
                "raster",
                "blend",
                "--opacity",
                "50",
                str(coloured_raster_path),
                str(hillshade_raster_path),
                str(output_path),
                "--operator",
                "hsv-value",
                "--overwrite",
                "--co",
                "TILED=YES",
                "--co",
                "COMPRESS=DEFLATE",
                "--co",
                "PREDICTOR=2",
                "--co",
                "ZLEVEL=9",
            ],
            check=True,
        )

        logger.info("Creating legend")
        create_legend(
            colourmap_path=colourmap_path, legend_path=output_path.parent.joinpath(f"{output_path.stem}_legend.json")
        )

    logger.info("Finished")


if __name__ == "__main__":
    main()
