"""Create a simplified and buffered boundary of one or more rasters."""

import argparse
import logging
from pathlib import Path
from types import SimpleNamespace

from osgeo import gdal, ogr

from geospatial_utils.raster.io import create_raster_dataset_from_template
from geospatial_utils.raster.raster_dataset import RasterDataset
from geospatial_utils.vector.io import (
    create_vector_dataset,
    write_feature_to_output_layer,
)
from geospatial_utils.vector.vector_dataset import VectorDataset

logger = logging.getLogger(__name__)

COMMAND = "get_simplified_boundary"
DESCRIPTION = "Gets the boundary of a raster with simplified and buffered edges."


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
        help=("Directory containing raster files (.tif) to process. All matching rasters will be processed."),
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


def run(output_dir: Path, raster_path: Path = None, raster_dir: Path = None) -> None:
    """Generate simplified boundaries for one or more rasters.

    Determines whether to process a single raster or all rasters in a directory.

    Args:
        output_dir: Directory where output boundary files will be written.
        raster_path: Optional path to a single raster file.
        raster_dir: Optional directory containing raster files (.tif).

    Raises:
        ValueError: If neither raster_path nor raster_dir is provided.
    """

    output_dir.mkdir(parents=True, exist_ok=True)

    if raster_path is not None:
        raster_to_footprint(raster_path=raster_path, output_dir=output_dir)

    elif raster_dir is not None:
        for raster_file in raster_dir.rglob("*.tif"):
            logger.info(f"Processing {raster_file.name}")
            raster_to_footprint(raster_path=raster_file, output_dir=output_dir)

    else:
        raise ValueError("Either raster_path or raster_dir must be provided.")

    print("finished")


def raster_to_footprint(raster_path: Path, output_dir: Path) -> None:
    """Generate a simplified and buffered footprint for a raster.

    Pipeline:
      1. Create binary mask raster
      2. Polygonize mask
      3. Simplify and buffer geometry

    Args:
        raster_path: Path to the input raster.
        output_dir: Directory for intermediate and final outputs.
    """

    binary_path = output_dir / "binary.tif"
    polygonised_path = output_dir / "polygonised.shp"
    simplified_path = output_dir / "boundary.shp"

    mask_array(raster_path, binary_path)
    polygonise(binary_path, polygonised_path)

    # geom = dissolve_polygons(polygonised_path)
    simplify_and_buffer(polygonised_path, simplified_path)
    print("finished")


def mask_array(raster_path: Path, output_path: Path) -> None:
    """Create a binary raster mask distinguishing data and NoData pixels.

    Valid pixels are set to 1 and NoData pixels are set to 0.

    Args:
        raster_path: Input raster file.
        output_path: Output binary mask raster.
    """

    print("starting pipeline")

    raster_dataset = RasterDataset(raster_path)

    # Use create raster dataset from template. Get the first band set the nodata value to 0.
    output_dataset = create_raster_dataset_from_template(
        output_path, template_raster_path=raster_path, num_bands=1, output_dtype=gdal.GDT_Byte
    )

    output_band = output_dataset.GetRasterBand(1)
    output_band.SetNoDataValue(0)

    raster_band = raster_dataset.ds.GetRasterBand(1)

    for x_offset, y_offset, x_size, y_size in raster_dataset.block_iterator():
        array = raster_band.ReadAsArray(x_offset, y_offset, x_size, y_size)

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
def polygonise(binary_file: Path, polygonsied_path: Path) -> None:
    """Convert a binary raster mask into vector polygons.

    Args:
        binary_file: Path to the binary raster file.
        polygonised_path: Output path for the polygonized shapefile.
    """

    print("polygonising")

    binary_ds = RasterDataset(binary_file)
    binary_band = binary_ds.ds.GetRasterBand(1)

    output_ds, output_layer = create_vector_dataset(
        output_path=polygonsied_path, layer_name=Path(polygonsied_path).stem, srs=binary_ds.srs
    )

    gdal.Polygonize(binary_band, binary_band, output_layer, -1)

    print("polygonised")


# Dissolve into one polygon create empty geometry collection then add to it
def dissolve_polygons(polygonised_path: Path) -> ogr.Geometry:
    """Dissolve all polygons in a vector dataset into a single geometry.

    Args:
        polygonised_path: Path to a polygon shapefile.

    Returns:
        ogr.Geometry: A dissolved multipolygon geometry.
    """

    print("dissolving...")
    # open shapefile and get layer
    ds = ogr.Open(polygonised_path)
    layer = ds.GetLayer()

    # create empty multipolygon
    multipolygon = ogr.Geometry(ogr.wkbMultiPolygon)

    # iterate over features in layer
    for feature in layer:
        geometry = feature.geometry()

        if geometry is None:
            continue

        if not geometry.IsValid():
            geometry = geometry.MakeValid()

        geometry_type = geometry.GetGeometryName()

        if geometry_type == "MULTIPOLYGON":
            multipolygon.AddGeometry(geometry.Clone())

        elif geometry_type == "POLYGON":
            multipolygon.AddGeometry(geometry.Clone())

        else:
            continue

    dissolved_geometry = multipolygon.UnaryUnion()

    return dissolved_geometry


def simplify_and_buffer(input_path: Path, output_path: Path) -> None:
    """Simplify and buffer a dissolved polygon geometry.

    Args:
        input_path: Path to the input polygon dataset.
        output_path: Path to the output simplified shapefile.
    """

    print("simplifying")

    input_ds = VectorDataset(input_path)

    geom = dissolve_polygons(input_path)

    print(geom.GetGeometryName())
    print(geom.GetArea())

    simplified = geom.Simplify(1)
    buffered = simplified.Buffer(1)

    output_ds, output_layer = create_vector_dataset(
        output_path=output_path, layer_name="simplified", srs=input_ds.srs, geom_type=ogr.wkbMultiPolygon
    )

    write_feature_to_output_layer(
        output_layer=output_layer,
        output_geometry=buffered,
        feature_to_copy=None,
    )

    print("simplified")


if __name__ == "__main__":
    main()
