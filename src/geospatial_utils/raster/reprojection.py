from pathlib import Path

from osgeo import gdal, osr


def reproject_raster(input_path: str | Path, output_path: str | Path, epsg_code: int) -> None:
    """
    Reproject a raster to the provided output EPSG Code

    Args:
        input_path: Path to the raster to be reprojected
        output_path: Path to save the reprojected raster to
        epsg_code: EPSG code representing the output spatial reference to project the raster to,

    """
    input_ds = gdal.Open(input_path)
    input_srs = input_ds.GetSpatialRef()

    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(epsg_code)

    creation_options = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "ZLEVEL=9"]

    warp_options = gdal.WarpOptions(dstSRS=output_srs, srcSRS=input_srs, creationOptions=creation_options)

    gdal.Warp(str(output_path), input_ds, options=warp_options)
