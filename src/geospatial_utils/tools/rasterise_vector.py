"""Convert a vector layer to a colourised raster."""

import argparse
import json
import logging
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from osgeo import gdal, ogr
from tqdm import tqdm

from geospatial_utils.raster.colour_raster import apply_colour_relief
from geospatial_utils.raster.io import DEFAULT_CREATION_OPTIONS
from geospatial_utils.vector.io import create_vector_dataset, get_driver_name
from geospatial_utils.vector.types import Field
from geospatial_utils.vector.vector_dataset import VectorDataset

logger = logging.getLogger(__name__)

COMMAND = "rasterize_vector"
DESCRIPTION = "Convert a vector layer to a GeoTIFF, applying colour using a provided legend"

VALUE_FIELD = "value"


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--vector_path", type=Path, help="Path to the vector to be rasterised")
    parser.add_argument("--output_path", type=Path, help="Path to the output raster")
    parser.add_argument(
        "--colour_mapping_path", type=Path, help="Path to the json file mapping field values to colours in rgb"
    )
    parser.add_argument(
        "--legend_field",
        type=str,
        help="Name of the field in the layers attributes containing values to use for colours",
    )
    parser.add_argument(
        "--resolution",
        type=float,
        help=(
            "Resolution to use for creating the output the raster dataset. This should be in the same units as the "
            "vector CRS"
        ),
    )
    parser.add_argument("--layer_name", type=str, required=False, help="Name of the layer to read")

    return parser


def main() -> None:
    """Entrypoint to the script. This is standardised to make registering the script with the core CLI easy."""

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run_from_cli(args)


def run_from_cli(args: SimpleNamespace) -> None:
    """The entrypoint when running from the centralised CLI.

    The function definition must not change (i.e the `def run from cli(args: SimpleNamespace)):`, the contents of
    this function can be freely modified.

    However, it is advisable to put all core logic in subsequent functions, as this allows running from both the CLI
    and calling the main `run` function directly from anywhere else in the codebase if needed.

    """
    # Call the main run function
    run(
        vector_path=args.vector_path,
        output_path=args.output_path,
        colour_mapping_path=args.colour_mapping_path,
        legend_field=args.legend_field,
        resolution=args.resolution,
        layer_name=args.layer_name,
    )


def run(
    vector_path: str | Path,
    output_path: str | Path,
    colour_mapping_path: str | Path,
    legend_field: str,
    resolution: float,
    layer_name: str | None = None,
) -> None:
    """The main run function."""
    logger.info("Rasterizing vector")
    vector_ds = VectorDataset(vector_path, layer_name=layer_name)

    if legend_field not in vector_ds.field_names:
        raise ValueError(f"The required field: {legend_field} could not be found in the vector file: {vector_path}")

    with open(colour_mapping_path) as colour_mapping_file:
        colour_mapping = json.load(colour_mapping_file)

    field_mapping = {field_value: index + 1 for (index, field_value) in enumerate(list(colour_mapping.keys()))}

    with tempfile.TemporaryDirectory(suffix="rasterize_vector") as temp_dir:
        logger.info("Creating temporary vector dataset")
        # Apply the field mapping so each field-colour combination has a unique value to burn into the raster
        temp_vector_path = os.path.join(temp_dir, "temp_layer.shp")
        output_ds, output_layer = create_vector_dataset(
            output_path=temp_vector_path,
            layer_name="temp_layer",
            srs=vector_ds.srs,
            fields=[Field(VALUE_FIELD, ogr.OFTInteger)],
            driver_name=get_driver_name(temp_vector_path),
            geom_type=vector_ds.layer.GetGeomType(),
        )

        for feature in tqdm(vector_ds.layer, total=vector_ds.layer.GetFeatureCount()):
            field_value = feature.GetField(legend_field)
            index_value = field_mapping.get(field_value)

            if not index_value:
                logger.debug(f"Skipping feature ID: {feature.GetFID()}, no value for field: {legend_field}")
                continue

            output_feature = ogr.Feature(output_layer.GetLayerDefn())
            output_feature.SetGeometry(feature.geometry())
            output_feature.SetField(VALUE_FIELD, index_value)

            output_layer.CreateFeature(output_feature)
            output_ds.SyncToDisk()

        # Rasterisation
        logger.info("Rasterizing temporary vector dataset")
        rasterized_path = os.path.join(temp_dir, "rasterised.tif")

        rasterize_options = gdal.RasterizeOptions(
            creationOptions=DEFAULT_CREATION_OPTIONS,
            attribute=VALUE_FIELD,
            xRes=resolution,
            yRes=resolution,
            noData=-9999,
            targetAlignedPixels=True,
        )

        gdal.Rasterize(rasterized_path, temp_vector_path, options=rasterize_options)

        # Construct the colourmap
        logger.info("Applying colour")
        colourmap_path = os.path.join(temp_dir, "colourmap.txt")
        colourmap = []
        for field_value, index_value in field_mapping.items():
            colour_entry = colour_mapping.get(field_value)
            colour_string = ",".join([str(item) for item in colour_entry])
            colourmap.append(f"{index_value},{colour_string}\n")

        with open(colourmap_path, "w") as colourmap_file:
            colourmap_file.writelines(colourmap)

        # Apply colouring to the rasterized vector
        apply_colour_relief(raster_path=rasterized_path, colourmap_path=colourmap_path, output_path=output_path)

    logger.info("Finished")


if __name__ == "__main__":
    main()
