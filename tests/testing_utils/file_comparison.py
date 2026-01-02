from pathlib import Path

import numpy as np
from osgeo import gdal, ogr

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


def compare_vector_files(expected_vector_path: str | Path, actual_vector_path: str | Path) -> None:
    """
    Compare two vector files (e.g. geojson or shapefile).

    Args:
        expected_vector_path: The path to the vector file containing the expected features and field values.
        actual_vector_path: The path to the vector file containing data to compare against the expected output.

    """
    expected_ds = ogr.Open(str(expected_vector_path))
    actual_ds = ogr.Open(str(actual_vector_path))

    compare_vector_features(expected_ds=expected_ds, actual_ds=actual_ds)


def compare_vector_features(expected_ds: gdal.Dataset, actual_ds: gdal.Dataset) -> None:
    """
    Compare individual vector features.
    For every feature within the first layer of the actual dataset, check the geometry and field values match those
    of the expected vector dataset.

    Args:
        expected_ds: Opened gdal.Dataset instance of the expected vector data to compare against.
        actual_ds: Opened gdal.Dataset instance of the vector data to compare against that expected.

    Raises:
        ComparisonError: The feature geometry does not match.
        ComparisonError: The field value does not match for a feature.

    """
    actual_layer = actual_ds.GetLayer()
    expected_layer = expected_ds.GetLayer()

    for expected_feature in expected_layer:
        expected_feature_id = expected_feature.GetFID()
        actual_feature = actual_layer.GetFeature(expected_feature_id)

        if not expected_feature.geometry().Equals(actual_feature.geometry()):
            raise ComparisonError(f"The geometry for feature {expected_feature_id} does not match that expected.")

        for field in expected_layer.schema:
            expected_field = expected_feature.GetField(field.name)
            actual_field = actual_feature.GetField(field.name)

            if expected_field != actual_field:
                raise ComparisonError(
                    f"The value for field {field.name} has a value of {actual_field} instead of {expected_field}."
                )
