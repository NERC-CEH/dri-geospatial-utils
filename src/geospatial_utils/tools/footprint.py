import argparse
import logging
from osgeo import gdal
from pathlib import Path
import subprocess
from shapely.geometry import shape, mapping
import shapely
import json
import numpy as np
from geospatial_utils.raster.raster_dataset import RasterDataset
from geospatial_utils.vector.io import (
    create_vector_dataset,
    create_raster_dataset_from_template,
    write_feature_to_output_layer,
)
from geospatial_utils.vector.vector_dataset import VectorDataset

"""logger = logging.getLogger(__name__)

COMMAND = "convert_to_cog"
DESCRIPTION = "Convert raster(s) to COG format, reprojected into EPSG 3857."

def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    Adds the command line arguments to the parser for the convert_to_cog CLI tool.

    Args:
        parser: Empty ArgumentParser object

    Returns:
        ArgumentParser object with arguments added.

    
    parser.add_argument(
        "--output_dir",
        required=True,
        type=Path,
        help=(
            "Directory to save the converted raster(s) to. Each raster will be saved using the original filename, "
            "with the suffix of `_{epsg_code}_colourised_cog`"
        ),
    )
    parser.add_argument(
        "--epsg_code",
        required=False,
        type=int,
        help=f"The EPSG code to reproject converted data to. Defaults to {DEFAULT_EPSG_CODE}",
    )

    parser.add_argument(
        "--colourmap_path", required=True, type=Path, help=("Provide file path to a defined colour ramp text file.")
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--raster_path", type=Path, help="Path to the raster to be converted")
    input_group.add_argument(
        "--raster_dir",
        type=Path,
        help=(
            "Path to the directory containing rasters to be converted. All .tif files found within this directory "
            "will be processed."
        ),
    )

    return parser
"""

raster_path = Path("/home/amber-barr/LIDAR_data/output/NT12SW_50CM_DSM_PHASE3_3857_colourised_cogified.tif")
output_dir = Path("/home/amber-barr/LIDAR_data/output/footprints")
simplified_dir = Path("/home/amber-barr/LIDAR_data/output/footprints/simplfiied")
binary_file = Path("/home/amber-barr/LIDAR_data/Tweed_SEPA/NT12SW_binary.tif")
polygonised_path = Path("/home/amber-barr/LIDAR_data/Tweed_SEPA/NT12SW_polygonised.tif")

output_dir.mkdir(parents=True, exist_ok=True)
simplified_dir.mkdir(parents=True, exist_ok=True)


# extension tasks: turn into CLI script
# try and write some tests
# check for any other values apart from 0 and 1 in the binary file
def main(raster_path, output_dir):
    binary_path = output_dir / "binary.tif"
    polygonised_path = output_dir / "polygonised.shp"
    dissolved_path = output_dir / "dissolved.shp"
    simplified_path = output_dir / "boundary.shp"

    mask_array(raster_path, binary_path)
    polygonise(binary_path, polygonised_path)
    dissolve_polygons(polygonised_path, dissolved_path)
    simplify_and_buffer(dissolved_path, simplified_path)

    print("finished")


# Create a binary mask array using nodata and valid data pixels.
def mask_array(raster_path, binary_file):
    raster_dataset = RasterDataset(raster_path)

    # create new dataset to write the mask array to. Use create raster dataset from template in main. Get the first abnd
    # set the nodata value to 0.
    new_dataset = create_raster_dataset_from_template(binary_file)

    for x_offset, y_offset, x_size, y_size in raster_dataset.block_iterator():
        raster_band = raster_dataset.ds.GetRasterBand(1)
        array = raster_band.ReadAsArray(x_offset, y_offset, x_size, y_size)

        # binary mask
        # find no data value and turn that to 0 and data to 1
        no_data = raster_band.GetNoDataValue()

        if no_data is None:
            no_data = 0

        mask = array == no_data

        array[mask] = 0
        array[~mask] = 1
    # add write array


# polygonise the mask array raster band into a polygon.
def polygonise(binary_file, polygonsied_path):
    binary_ds = RasterDataset(binary_file)
    binary_band = binary_ds.ds.GetRasterBand(1)

    output_ds, output_layer = create_vector_dataset(
        output_path=polygonsied_path, layer_name="NT12SW_binary_poly", srs=binary_ds.srs
    )

    gdal.Polygonize(binary_band, binary_band, output_layer, -1)

    output_ds = None


# Dissolve into one polygon
def dissolve_polygons(polygonised_path, dissolved_output_path):
    subprocess.run(
        [
            "ogr2ogr",
            "-f",
            "GPKG",
            dissolved_output_path,
            polygonised_path,
            "-dialect",
            "SQLite",
            "-sql",
            "SELECT ST_Union(geometry) FROM binary_poly",
        ],
        check=True,
    )


# Simplify polygon to reduce vertices
def simplify_and_buffer(dissolved):
    dissolved_vector = VectorDataset(dissolved)

    output_ds, output_layer = create_vector_dataset(
        output_path="/home/amber-barr/LIDAR_data/Tweed_SEPA/NT12SW_boundary.shp",
        layer_name="NT12SW_boundary",
        srs=dissolved_vector.srs,
    )
    # compare to test code
    for feature in dissolved_vector.layer:
        geometry = feature.GetGeometryRef()
        simplified = geometry.Simplify(1)
        buffered = simplified.Buffer(1)

        if buffered.IsEmpty():
            continue

        write_feature_to_output_layer(
            output_layer=output_layer,
            output_geometry=buffered,
            feature_to_copy=feature,
        )

        output_ds.SyncToDisk()


if __name__ == "__main__":
    main(raster_path)
