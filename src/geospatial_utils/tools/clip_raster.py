"""Clip a raster using a vector mask."""

import argparse
import logging
import tempfile
from pathlib import Path
from types import SimpleNamespace

from osgeo import gdal

from geospatial_utils.raster.io import DEFAULT_CREATION_OPTIONS
from geospatial_utils.raster.raster_dataset import RasterDataset
from geospatial_utils.vector.vector_dataset import VectorDataset

logger = logging.getLogger(__name__)

COMMAND = "clip_raster"
DESCRIPTION = "Clip a raster to a boundary geometry"


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Adds the command line arguments to the parser for the convert_to_cog CLI tool.

    Args:
        parser: Empty ArgumentParser object

    Returns:
        ArgumentParser object with arguments added.

    """
    parser.add_argument("--raster_path", type=Path, help="Paths to the raster to be clipped.")
    parser.add_argument(
        "--clip_boundary_path",
        type=Path,
        help="Path to the vector dataset containing the boundary to clip the raster to.",
    )
    parser.add_argument("--output_path", type=Path, help="Path to save the clipped raster to.")

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
    run(raster_path=args.raster_path, clip_boundary_path=args.clip_boundary_path, output_path=args.output_path)


def run(raster_path: str | Path, clip_boundary_path: str | Path, output_path: str | Path) -> None:
    """The main run function."""
    with tempfile.TemporaryDirectory() as temp_dir:
        reprojected_path = reproject_clip_boundary(
            clip_boundary_path=clip_boundary_path, raster_path=raster_path, output_dir=temp_dir
        )

        clip_raster(raster_path=raster_path, clip_boundary_path=reprojected_path, output_path=output_path)

    logger.info("Finished")


def reproject_clip_boundary(
    clip_boundary_path: str | Path, raster_path: str | Path, output_dir: str | Path
) -> str | Path:
    """
    Reproject the clipping boundary to the same projection as the raster to be clipped. If no reprojection is required
    the path of the clip boundary dataset will be returned without modification.

    Args:
        clip_boundary_path: Path to the vector file used to clip the raster. It is expected this will be contain
        a single feature within a single layer.
        raster_path: Path to the raster to be clipped.
        output_dir: Directory to write the clipped raster to.

    Raises:
        ValueError: The raster has no coordinate system that could be detected by GDAL
        ValueError: The clip boundary vector has no coordinate system that could be detected by GDAL

    Returns:
        Path to the reprojected clip boundary vector dataset.

    """
    raster_ds = RasterDataset(raster_path)
    clip_ds = VectorDataset(clip_boundary_path)

    if raster_ds.epsg_code is None:
        raise ValueError(f"No projection system could be found for {raster_path}")

    if clip_ds.epsg_code is None:
        raise ValueError(f"No projection system could be found for {clip_boundary_path}")

    if clip_ds.epsg_code != raster_ds.epsg_code:
        logger.info(f"Reprojecting the clip boundary to EPSG:{raster_ds.epsg_code}")
        reprojected_path = Path(output_dir).joinpath(f"{Path(clip_boundary_path).stem}.geojson")
        clip_ds.reproject_layer(output_path=reprojected_path, target_epsg=raster_ds.epsg_code)
        return reprojected_path

    return clip_boundary_path


def clip_raster(raster_path: str | Path, clip_boundary_path: str | Path, output_path: str | Path) -> None:
    """
    Clip the raster using the boundary vector dataset.

    Args:
        raster_path: Path to the raster to be clipped
        clip_boundary_path: Path to the vector dataset containing the geometry to clip the raster to.
        output_path: Path to save the clipped raster to.

    """
    raster_ds = RasterDataset(raster_path)

    gdal.Warp(
        output_path,
        raster_ds.ds,
        cutlineDSName=clip_boundary_path,
        cropToCutline=True,
        creationOptions=DEFAULT_CREATION_OPTIONS,
    )


if __name__ == "__main__":
    main()
