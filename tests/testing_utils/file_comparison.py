from pathlib import Path

import numpy as np
from osgeo import gdal, ogr

from geospatial_utils.vector.vector_dataset import VectorDataset
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
    expected_ds = VectorDataset(expected_vector_path)
    actual_ds = VectorDataset(actual_vector_path)

    if expected_ds.fields != actual_ds.fields:
        raise ComparisonError("The field definitions between actual and expected data do not match.")

    if not expected_ds.srs.IsSame(actual_ds.srs):
        raise ComparisonError("The spatial reference does not match that expected.")

    compare_vector_layers(expected_ds.layer, actual_ds.layer)


def compare_vector_layers(expected_layer: ogr.Layer, actual_layer: ogr.Layer) -> None:
    field_names = [field.name for field in expected_layer.schema]

    for expected_feature, actual_feature in zip(expected_layer, actual_layer):
        expected_geometry = expected_feature.geometry()
        actual_geometry = actual_feature.geometry()

        # Due to potential rounding errors etc, it's possible that the geometries may differ very slightly. Therefore
        # construct a geometry out the difference betwee
        difference = expected_geometry.Difference(actual_geometry)
        if difference.Area() > 0.001:
            raise ComparisonError(f"The geometry for feature {expected_feature.GetFID()} does not match that expected.")

        for field_name in field_names:
            expected_field = expected_feature.GetField(field_name)
            acutal_field = actual_feature.GetField(field_name)

            if expected_field != acutal_field:
                raise ComparisonError(
                    f"The value for the field {field_name} for feature {expected_feature.GetFID()} does not match that "
                    "expected."
                )
