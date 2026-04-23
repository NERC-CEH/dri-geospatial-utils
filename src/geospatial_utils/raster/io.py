from pathlib import Path

from osgeo import gdal

from geospatial_utils.raster.raster_dataset import RasterDataset

DEFAULT_CREATION_OPTIONS = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "ZLEVEL=9"]


def create_raster_dataset_from_template(
    output_path: str | Path,
    template_raster_path: str | Path,
    num_bands: int | None = None,
    output_dtype: int | None = None,
) -> gdal.Dataset:
    """
    Create a new empty raster (.tif) file on disk, using a template raster to provide the spatial reference,
    geotransform, size, data type and number of bands. Note that the number of bands and data type can be overwritten
    manually if required.

    The nodata value will need setting on writing to the new dataset on a per-band basis.

    Args:
        output_path: Path the new raster should be saved to.
        template_raster_path: Path to the raster file used as a template for the new raster.
        num_bands: The number of bands the new raster should contain. If not provided this will be copied from the
            template raster. Defaults to None.
        output_dtype: Integer representation of the gdal datatype to create the new output raster with. If not provided
            this will be copied from the template raster. Defaults to None.

    Returns:
        gdal.Dataset instance of the new raster dataset.

    """
    template_ds = RasterDataset(template_raster_path)

    # The number of bands in the output and the data type to use are variables that may need to be modified from
    # the template raster (e.g. if creating a single band boolean mask from an RGBA raster)
    if num_bands is None:
        num_bands = template_ds.ds.RasterCount

    if output_dtype is None:
        first_band = template_ds.ds.GetRasterBand(1)
        output_dtype = first_band.DataType

    driver = gdal.GetDriverByName("GTiff")

    new_ds = driver.Create(
        output_path,
        xsize=template_ds.ds.RasterXSize,
        ysize=template_ds.ds.RasterYSize,
        eType=output_dtype,
        options=DEFAULT_CREATION_OPTIONS,
    )

    # Assign the coordinate reference system an d
    new_ds.SetProjection(template_ds.srs.ExportToWkt())
    new_ds.SetGeoTransform(template_ds.ds.GetGeoTransform())

    return new_ds
