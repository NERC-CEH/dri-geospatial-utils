from pathlib import Path

import numpy as np
from osgeo import gdal

from tests.testing_utils.exceptions import ComparisonError


def compare_raster_files(expected_raster_path: str | Path, actual_raster_path: str | Path) -> None:
    """
    Compare two raster files.

    Args:
        expected_raster_path: The path to the raster containing the expected data
        actual_raster_path: The path to the raster to compare against the expected raster.

    Raises:
        ComparisonError: The number of bands differ betwwen expected and actual rasters

    """
    expected_ds = gdal.Open(expected_raster_path)
    actual_ds = gdal.Open(actual_raster_path)

    if expected_ds.RasterCount != actual_ds.RasterCount:
        raise ComparisonError(
            f"The raster: {actual_raster_path} has {actual_ds.RasterCount} bands instead of the expected: "
            f"{expected_ds.RasterCount}."
        )


def compare_raster_bands(expected_raster_ds: gdal.Dataset, actual_raster_ds: gdal.Dataset, band_index: int) -> None:
    """
    Compare two raster bands.

    For a specific band index, check the nodata values and data match that expected

    Args:
        expected_raster_ds: Opened gdal.Dataset containing the expected raster data.
        actual_raster_ds: Opened gdal.Dataset containing the raster data to compare against that expected
        band_index: Index of the band to read (count starts at one).

    Raises:
        ComparisonError: No data values do not match.
        ComparisonError: Band contents do not match.

    """
    expected_band = expected_raster_ds.GetRasterBand(band_index)
    actual_band = actual_raster_ds.GetRasterBand(band_index)

    expected_nodata = expected_band.GetNoDataValue()
    actual_nodata = actual_band.GetNoDataValue()

    if expected_nodata != actual_nodata:
        raise ComparisonError(
            f"The nodata value for band {band_index} is `{actual_nodata} instead of the expected `{expected_nodata}`."
        )

    expected_arr = expected_band.ReadAsArray()
    actual_arr = actual_band.ReadAsArray()

    if not np.isclose(expected_arr, actual_arr):
        raise ComparisonError(f"The data for raster band {band_index} does not that expected.")
