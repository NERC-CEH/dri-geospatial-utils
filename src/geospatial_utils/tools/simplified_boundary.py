"Create an simplified and buffered boundary of one or more rasters"

import argparse
import logging
from osgeo import gdal, ogr
from pathlib import Path
import geopandas as gpd
import pathlib
from types import SimpleNamespace
import os

from geospatial_utils.raster.raster_dataset import RasterDataset
from geospatial_utils.vector.io import (
    create_vector_dataset,
    write_feature_to_output_layer,
)
from geospatial_utils.raster.io import create_raster_dataset_from_template
from geospatial_utils.vector.vector_dataset import VectorDataset
from geospatial_utils.vector.types import Field

logger = logging.getLogger(__name__)

COMMAND = "get_raster_footprint"
DESCRIPTION = "Gets the footprint of a raster with simplified and buffered edges."


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Adds the command line arguments to the parser for the convert_to_cog CLI tool.

    Args:
        parser: Empty ArgumentParser object

    Returns:
        ArgumentParser object with arguments added.

    """
    parser.add_argument(
        "--output_dir",
        required=True,
        type=Path,
        help=(
            "Directory to save the boundary vector file to. Each raster will be saved using the original filename, "
            "with the suffix of {boundary}"
        ),
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--raster_path", type=Path, help="Path to the raster needing a boundary generated")
    input_group.add_argument(
        "--raster_dir",
        type=Path,
        help=(
            "Path to the directory containing rasters needing boundary generated. All .tif files found within this "
            "directory will be processed."
        ),
    )

    return parser


def main() -> None:
    """Entrypoint to the script."""

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run_from_cli(args)


def run_from_cli(args: SimpleNamespace) -> None:
    """The entrypoint when running from the centralised CLI."""
    # Call the main run function
    run(
        raster_path=args.raster_path,
        raster_dir=args.raster_dir,
        output_dir=args.output_dir,
    )


def run(
    output_dir: str | Path, raster_path: str | Path = None, raster_dir: str | Path = None
) -> None:
    # create the output directory if it doesn't already exist
    output_dir.mkdir(parents=True, exist_ok=True)

    if raster_path is not None:
        raster_to_footprint(raster_path=raster_path, output_dir=output_dir)

    else:
        raster_dir = Path(raster_path)

        for raster_path in raster_dir.rglob("*.csv"):
            logger.info(f"Converting {raster_path.name} to geojson")

            raster_to_footprint(raster_path=raster_path, output_dir=output_dir)

    print("finished")


# extension tasks: turn into CLI script
# try and write some tests
# check for any other values apart from 0 and 1 in the binary file
def raster_to_footprint(raster_path, output_dir):
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
def mask_array(raster_path, output_path):
    print("starting pipeline")
    raster_dataset = RasterDataset(raster_path)

    # create new dataset to write the mask array to. Use create raster dataset from template in main. Get the first abnd
    # set the nodata value to 0.
    output_dataset = create_raster_dataset_from_template(
        output_path, template_raster_path=raster_path, num_bands=1, output_dtype=gdal.GDT_Byte
    )

    output_band = output_dataset.GetRasterBand(1)
    output_band.SetNoDataValue(0)

    raster_band = raster_dataset.ds.GetRasterBand(1)

    for x_offset, y_offset, x_size, y_size in raster_dataset.block_iterator():
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
        output_band.WriteArray(array, xoff=x_offset, yoff=y_offset)

# polygonise the mask array raster band into a polygon.
def polygonise(binary_file, polygonsied_path):
    print("polygonising")
    binary_ds = RasterDataset(binary_file)
    binary_band = binary_ds.ds.GetRasterBand(1)

    output_ds, output_layer = create_vector_dataset(
        output_path=polygonsied_path, layer_name=Path(polygonsied_path).stem, srs=binary_ds.srs
    )

    gdal.Polygonize(binary_band, binary_band, output_layer, -1)

    print("polygonised")

# Dissolve into one polygon create empty geometry collection then add to it
def dissolve_polygons(polygonised_path, dissolved_output_path):

    # open shapefile and get layer
    ds = ogr.Open(polygonised_path)
    layer = ds.GetLayer()

    # create empty multipolygon
    multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)

    # iterate over features in layer
    for feature in layer:
        geometry = feature.geometry()
        geometry_type = geometry.GetGeometryName()

        if geometry_type == 'MULTIPOLYGON':
            for subgeom in geometry:
                multipolygon.AddGeometry(subgeom)

        elif geometry_type == 'POLYGON':
            multipolygon.AddGeometry(geometry)

        else:
            continue
    #unaryunion

    print()

    # create output dataset
    output_ds, output_layer = create_vector_dataset(
    output_path=dissolved_output_path, layer_name=Path(dissolved_path).stem, srs=layer.GetSpatialRef(), geom_type=ogr.wkbMultiPolygon
    )

    # Write features to file
    write_feature_to_output_layer(
    output_layer=output_layer,
    output_geometry=merged,
    feature_to_copy=feature,
    )

# Simplify polygon to reduce vertices
def simplify_and_buffer(input_path, output_path):
    print("simplifying")
    dissolved_vector = VectorDataset(input_path)

    output_ds, output_layer = create_vector_dataset(
        output_path=output_path,
        layer_name=output_path.stem,
        srs=dissolved_vector.srs,
    )
    # compare to test code
    for feature in dissolved_vector.layer:
        geometry = feature.GetGeometryRef()
        simplified = geometry.Simplify(1)
        buffered = simplified.Buffer(1)

        if buffered.IsEmpty():
            print("buffered.IsEmpty()")
            continue

        write_feature_to_output_layer(
            output_layer=output_layer,
            output_geometry=buffered,
            feature_to_copy=feature,
        )

        output_ds.SyncToDisk()
        output_ds = None
    print("simplified")
    # template_ds = ogr.Open(input_path)
    # template_layer = template_ds.GetLayer()
    # output_srs = template_ds.GetSpatialRef()

    # output_ds, output_layer = create_vector_dataset(
    #         output_path=output_path,
    #         layer_name="test",
    #         srs=output_srs,
    #         fields=[Field(field.name, field.type) for field in template_layer.schema],
    # )

    # for feature in template_layer:
    #     write_feature_to_output_layer(
    #         output_layer=output_layer,
    #         output_geometry=feature.geometry(),
    #         feature_to_copy=feature,
    #         fields_to_transfer=[],
    #     )

    #    output_ds.SyncToDisk()


if __name__ == "__main__":
    main()
