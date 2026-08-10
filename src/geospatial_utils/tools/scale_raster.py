"""Combine multiple nodata values within a raster into a single nodata value."""

import argparse
import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from osgeo import gdal
from tqdm import tqdm

from geospatial_utils.raster.io import create_raster_dataset_from_template
from geospatial_utils.raster.raster_dataset import RasterDataset

logger = logging.getLogger(__name__)

COMMAND = "scale_raster"
DESCRIPTION = "Apply a multiplier value to a raster"

DEFAULT_EPSG_CODE = 3857


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    # Example parser entry. Delete before use
    parser.add_argument("--raster_path", type=Path, help="Path to the raster to be converted")
    parser.add_argument("--output_path", type=Path, help="Path to save the modified raster to")
    parser.add_argument("--multiplier", type=float, help="Value to scale the ")

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
    run(raster_path=args.raster_path, output_path=args.output_path, multiplier=args.multiplier)


def run(raster_path: str | Path, output_path: str | Path, multiplier: float) -> None:
    """The main run function."""
    logger.info(f"Scaling raster by {multiplier}")
    scale_raster(
        raster_path=raster_path,
        output_path=output_path,
        multiplier=multiplier,
    )

    logger.info("Finished")


def scale_raster(raster_path: str | Path, output_path: str | Path, multiplier: float) -> None:
    """Scale raster values.

    Args:
        raster_path: Input raster file.
        output_path: Output binary mask raster.
        multiplier: Value to multiply non-nodata values by

    """
    raster_dataset = RasterDataset(raster_path)

    output_dataset = create_raster_dataset_from_template(
        output_path,
        template_raster_path=raster_path,
        num_bands=raster_dataset.ds.RasterCount,
        output_dtype=gdal.GDT_Float32,
    )

    for band_index in range(1, raster_dataset.ds.RasterCount + 1):
        raster_band = raster_dataset.ds.GetRasterBand(band_index)
        nodata_value = raster_band.GetNoDataValue()

        output_band = output_dataset.GetRasterBand(band_index)
        if nodata_value:
            output_band.SetNoDataValue(nodata_value)

        for x_offset, y_offset, x_size, y_size in tqdm(raster_dataset.block_iterator()):
            array = raster_band.ReadAsArray(x_offset, y_offset, x_size, y_size)
            array = array.astype(np.float32)

            output_arr = np.array(array)
            if nodata_value:
                nodata_mask = array == nodata_value
                output_arr[nodata_mask] = np.nan

            output_arr = output_arr * multiplier

            output_band.WriteArray(output_arr, xoff=x_offset, yoff=y_offset)
