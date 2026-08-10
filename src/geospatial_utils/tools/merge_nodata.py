"""Combine multiple nodata values within a raster into a single nodata value."""

import argparse
import logging
from pathlib import Path
from types import SimpleNamespace

from tqdm import tqdm

from geospatial_utils.raster.io import create_raster_dataset_from_template
from geospatial_utils.raster.raster_dataset import RasterDataset

logger = logging.getLogger(__name__)

COMMAND = "merge_nodata"
DESCRIPTION = "Convert raster(s) to COG format, reprojected into EPSG 3857."

DEFAULT_EPSG_CODE = 3857


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    # Example parser entry. Delete before use
    parser.add_argument("--raster_path", type=Path, help="Path to the raster to be converted")
    parser.add_argument("--output_path", type=Path, help="Path to save the modified raster to")
    parser.add_argument(
        "--extra_nodata", type=float, nargs="+", help="Extra nodata values to convert to a single nodata value"
    )
    parser.add_argument("--output_nodata", type=float, help="The value to use for nodata in the output raster")

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
    run(
        raster_path=args.raster_path,
        output_path=args.output_path,
        extra_nodata_values=args.extra_nodata,
        output_nodata=args.output_nodata,
    )


def run(
    raster_path: str | Path, output_path: str | Path, extra_nodata_values: list[float], output_nodata: float
) -> None:
    """The main run function."""
    logger.info("Merging nodata values")
    merge_nodata_values(
        raster_path=raster_path,
        output_path=output_path,
        extra_nodata_values=extra_nodata_values,
        output_nodata=output_nodata,
    )
    logger.info("Finished")


def merge_nodata_values(
    raster_path: str | Path, output_path: str | Path, extra_nodata_values: list[float], output_nodata: float
) -> None:
    """Merge nodata values.

    Args:
        raster_path: Input raster file.
        output_path: Output binary mask raster.
    """
    raster_dataset = RasterDataset(raster_path)

    output_dataset = create_raster_dataset_from_template(
        output_path,
        template_raster_path=raster_path,
        num_bands=raster_dataset.ds.RasterCount,
    )

    for band_index in range(1, raster_dataset.ds.RasterCount + 1):
        output_band = output_dataset.GetRasterBand(band_index)
        output_band.SetNoDataValue(output_nodata)
        raster_band = raster_dataset.ds.GetRasterBand(band_index)

        existing_no_data = raster_band.GetNoDataValue()
        if existing_no_data is not None:
            nodata_values = [existing_no_data] + extra_nodata_values
        else:
            nodata_values = extra_nodata_values

        for x_offset, y_offset, x_size, y_size in tqdm(raster_dataset.block_iterator()):
            array = raster_band.ReadAsArray(x_offset, y_offset, x_size, y_size)

            for nodata_value in nodata_values:
                array[array == nodata_value] = output_nodata

            output_band.WriteArray(array, xoff=x_offset, yoff=y_offset)
