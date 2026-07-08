"""Generate the boundary geometry for one or more rasters."""

import argparse
import logging
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from osgeo import gdal, ogr
from tqdm import tqdm

from geospatial_utils.raster.io import create_raster_dataset_from_template
from geospatial_utils.raster.raster_dataset import RasterDataset
from geospatial_utils.vector.io import (
    create_vector_dataset,
    write_feature_to_output_layer,
)
from geospatial_utils.vector.vector_dataset import VectorDataset

logger = logging.getLogger(__name__)

COMMAND = "raster_boundary"
DESCRIPTION = "Extract the boundary geometry for a raster."

SIMPLIFICATION_DISTANCE = 1
BUFFER_DISTANCE = 1


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Adds the command line arguments to the parser for the convert_to_cog CLI tool.

    Args:
        parser: Empty ArgumentParser object

    Returns:
        ArgumentParser object with arguments added.

    """
    parser.add_argument("--raster_path", type=Path, help="Path to the raster to extract the boundary from")

    parser.add_argument(
        "--output_path",
        required=True,
        type=Path,
        help=("Path to save the generated geojson file to."),
    )

    return parser


def main() -> None:
    """Entrypoint to the script."""

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run_from_cli(args)


def run_from_cli(args: SimpleNamespace) -> None:
    """Run raster_boundary from the commandline."""
    # Call the main run function
    run(
        raster_path=args.raster_path,
        output_path=args.output_path,
    )


def run(
    raster_path: Path,
    output_path: Path,
) -> None:
    """Generates simplified boundaries for one or more rasters.

    Determines whether to process a single raster or all rasters in a directory.

    Args:
        raster_path: Path to the raster to create the boundary from.
        output_path: Location of the geojson file to create.

    Raises:
        ValueError: If neither raster_path nor raster_dir is provided.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    raster_footprint(raster_path=raster_path, output_path=output_path)

    logger.info("Finished")


def raster_footprint(raster_path: Path, output_path: Path) -> None:
    """Generate a simplified and buffered footprint for a raster.

    Pipeline:
      1. Create binary mask raster
      2. Polygonize mask
      3. Simplify and buffer geometry

    Args:
        raster_path: Path to the input raster.
        output_dir: Directory for intermediate and final outputs.
    """

    # Only projected coordinate systems are supported at this time in order to ensure the buffer and simplification
    # distances are sensible.
    raster_ds = RasterDataset(raster_path)
    if raster_ds.srs.IsGeographic():
        raise ValueError("The provided raster is not in a projected coordinate system. Please reproject first.")

    with tempfile.TemporaryDirectory(suffix="raster_boundary") as temp_dir:
        logger.info("Creating binary mask")
        masked_raster_path = os.path.join(temp_dir, "masked_raster.tif")
        create_binary_mask(raster_path=raster_path, output_path=masked_raster_path)

        logger.info("Converting boolean mask to vector")
        vectorised_mask_path = os.path.join(temp_dir, "vectorised_mask.shp")
        polygonise(raster_path=masked_raster_path, output_path=vectorised_mask_path)

        logger.info("Creating final boundary geometry")
        simplify_boundary(input_path=vectorised_mask_path, output_path=output_path)

    logger.info("Finished")


def create_binary_mask(raster_path: Path, output_path: Path) -> None:
    """Create a binary raster mask distinguishing data and NoData pixels.

    Valid pixels are set to 1 and NoData pixels are set to 0.

    Args:
        raster_path: Input raster file.
        output_path: Output binary mask raster.
    """
    raster_dataset = RasterDataset(raster_path)

    # Use create raster dataset from template. Get the first band set the nodata value to 0.
    output_dataset = create_raster_dataset_from_template(
        output_path, template_raster_path=raster_path, num_bands=1, output_dtype=gdal.GDT_Byte
    )
    output_band = output_dataset.GetRasterBand(1)
    output_band.SetNoDataValue(0)

    band_index = 1
    if raster_dataset.is_rgb:
        band_index = 4
    raster_band = raster_dataset.ds.GetRasterBand(band_index)

    no_data = raster_band.GetNoDataValue()

    for x_offset, y_offset, x_size, y_size in tqdm(raster_dataset.block_iterator()):
        array = raster_band.ReadAsArray(x_offset, y_offset, x_size, y_size)

        # find no data value and turn that to 0 and data to 1
        if no_data is None:
            no_data = 0

        mask = array == no_data

        array[mask] = 0
        array[~mask] = 1

        # add write array
        output_band.WriteArray(array, xoff=x_offset, yoff=y_offset)


def polygonise(raster_path: Path, output_path: Path) -> None:
    """Convert a binary raster mask into vector polygons.

    Args:
        raster_path: Path to the binary raster file.
        output_path: Output path for the polygonized shapefile.
    """
    binary_ds = RasterDataset(raster_path)
    binary_band = binary_ds.ds.GetRasterBand(1)

    output_ds, output_layer = create_vector_dataset(
        output_path=output_path, layer_name=Path(output_path).name, srs=binary_ds.srs
    )

    gdal.Polygonize(binary_band, binary_band, output_layer, -1)


def simplify_boundary(input_path: Path, output_path: Path) -> None:
    """Simplify the vectorised boolean mask.

    Combine all polygons within the vector layer into a single multipolygon, before reducing the complexity of the
    final geometry by first simplifying to a 1m threshold, before buffering the final geometry by 1m to ensure the
    entire raster is encompassed by the boundary.

    Args:
        input_path: Path to the input polygon dataset.
        output_path: Path to the output simplified geojson.

    """

    dissolved_geom = dissolve_layer(input_path)

    input_ds = VectorDataset(input_path)

    simplified = dissolved_geom.Simplify(SIMPLIFICATION_DISTANCE)
    buffered = simplified.Buffer(BUFFER_DISTANCE)

    output_ds, output_layer = create_vector_dataset(
        output_path=output_path,
        layer_name=output_path.name,
        srs=input_ds.srs,
        driver_name="GeoJSON",
    )

    write_feature_to_output_layer(
        output_layer=output_layer,
        output_geometry=buffered,
        feature_to_copy=None,
    )


def dissolve_layer(input_path: Path) -> ogr.Geometry:
    """Dissolve all polygons in the vector layer into a single multipolygon.

    This assumes a single layer vector dataset. It iterates over each feature within the layer, adding any polygons
    to a single multipolygon, before applying a unnary union to remove any overlaps.

    Args:
        input_path: Path to the vector dataset to dissolve.

    Returns:
        ogr.Geometry: A dissolved multipolygon geometry.
    """
    input_ds = VectorDataset(input_path)

    multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)

    for feature in input_ds.layer:
        geometry = feature.geometry()

        if geometry is None:
            continue

        if not geometry.IsValid():
            geometry = geometry.MakeValid()

        geometry_type = geometry.GetGeometryName()

        if geometry_type == "MULTIPOLYGON":
            for sub_geom in geometry:
                multipolygon.AddGeometry(sub_geom)

        if geometry_type == "POLYGON":
            multipolygon.AddGeometry(geometry)

    dissolved_geometry = multipolygon.UnaryUnion()

    return dissolved_geometry


if __name__ == "__main__":
    main()
