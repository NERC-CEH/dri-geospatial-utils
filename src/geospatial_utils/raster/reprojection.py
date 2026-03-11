import logging
from pathlib import Path

from osgeo import gdal, osr
from geospatial_utils.raster.raster_dataset import RasterDataset

logger = logging.getLogger(__name__)


def reproject_raster(
    input_path: str | Path, output_path: str | Path, output_epsg_code: int, input_epsg_code: int = None
) -> Path:
    """
    Reproject a raster to the provided output EPSG Code

    Args:
        input_path: Path to the raster to be reprojected
        output_path: Path to save the reprojected raster to
        epsg_code: EPSG code representing the output spatial reference to project the raster to,

    """
    input_ds = RasterDataset(input_path)
    input_srs = input_ds.srs

    if input_srs is None:
        if input_epsg_code is None:
            raise ValueError("Please provide an input epsg code for the input raster.")

        # Construct the input spatial reference using the input_epsg_code parameter
        input_srs = osr.SpatialReference()
        input_srs.ImportFromEPSG(input_epsg_code)

    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(output_epsg_code)

    if input_srs.IsSame(output_srs):
        logger.warning(f"The raster is already projected to EPSG: {output_epsg_code}")
        return input_path

    pixel_width = input_ds.geotransform.x_res
    pixel_height = input_ds.geotransform.y_res

    creation_options = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "ZLEVEL=9"]

    warp_options = gdal.WarpOptions(
        dstSRS=output_srs,
        srcSRS=input_srs,
        xRes=pixel_width,
        yRes=abs(pixel_height),
        resampleAlg="bilinear",
        creationOptions=creation_options,
    )

    gdal.Warp(str(output_path), input_ds, options=warp_options)

    return output_path
