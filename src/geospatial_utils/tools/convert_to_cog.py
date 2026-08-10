"""Convert one or more rasters to a COG formatted raster, in EPSG 3857."""

import argparse
import logging
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from osgeo import gdal, osr

from geospatial_utils.raster.colour_raster import apply_colour_relief, create_legend
from geospatial_utils.raster.io import DEFAULT_CREATION_OPTIONS
from geospatial_utils.raster.raster_boundary import raster_boundary
from geospatial_utils.raster.reprojection import reproject_raster
from geospatial_utils.vector.vector_dataset import VectorDataset

logger = logging.getLogger(__name__)

COMMAND = "convert_to_cog"
DESCRIPTION = "Convert raster(s) to COG format, reprojected into EPSG 3857."

DEFAULT_EPSG_CODE = 3857


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
        "--colourmap_path",
        required=False,
        default=None,
        type=Path,
        help=("Provide file path to a defined colour ramp text file."),
    )
    parser.add_argument(
        "--create-boundary", action="store_true", help="If provided the boundary for the raster will be created"
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


def main() -> None:
    """Entrypoint to the script."""

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run_from_cli(args)


def run_from_cli(args: SimpleNamespace) -> None:
    """The entrypoint when running from the centralised CLI.

    Runs convert_to_cog, extracting out the relevant variables from the cli args object.

    """
    run(
        output_dir=args.output_dir,
        colourmap_path=args.colourmap_path,
        raster_path=args.raster_path,
        raster_dir=args.raster_dir,
        create_boundary=args.create_boundary,
    )


def run(
    output_dir: str | Path,
    colourmap_path: str | Path,
    raster_path: str | Path = None,
    raster_dir: str | Path = None,
    create_boundary: bool = False,
) -> None:
    """The main convert to cog function

    Checks whether to process a single raster or iterate over all .tif files within the provided directory
    Args:
        output_dir: The directory where the converted raster files will be saved to.
        colourmap_path: Path to the template colour ramp file, which will be modified to fit to the raster(s) being
            converted.
        raster_path: Path to a single raster to be converted. If this is not provided, then the raster_dir parameter
            must be provided.
        raster_dir: Path to a directory of raster files to be converted. If this is not provided, then the raster_path
            parameter must be provided.
        create_boundary: Flag. If provided, the boundary geojson file will also be generated.

    """
    # create the output diectory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        if raster_path is not None:
            convert_single_raster_to_cog(
                raster_path=raster_path, temp_dir=temp_dir, output_dir=output_dir, colourmap_path=colourmap_path
            )

        else:
            # Ensure the raster directory is a Path object
            raster_dir = Path(raster_dir)
            for raster_path in raster_path.glob("*.tif"):
                logger.info(f"Converting raster {raster_path.stem} to COG")
                convert_single_raster_to_cog(
                    raster_path=raster_path, temp_dir=temp_dir, output_dir=output_dir, colourmap_path=colourmap_path
                )

    logger.info("Finished")


def convert_single_raster_to_cog(
    raster_path: str | Path,
    temp_dir: str,
    output_dir: str | Path,
    colourmap_path: str | Path,
    create_boundary: bool = False,
) -> None:
    """Converts a single raster to a COG formatted raster.

    Firstly the raster will be reprojected into EPSG 3857, then the colour ramp will be modified to fit the
    min - max range of the raster, before being applied. The resulting RGBA raster will then be converted into
    a COG formatted raster and saved to the output directory.

    Args:
        raster_path: Path to the raster to be converted.
        temp_dir: Temporary working directory, used to save the intermediary outputs such as the reprojected and
            colourised rasters.
        output_dir: Path to the location where the final converted raster will be saved to.
        colourmap_path: Path to the template .txt colourmap file which will be customised for the current raster being
            processed.
        create_boundary: Flag. If provided, the boundary geojson file will also be generated.

    """

    # Ensure the raster path and temp directory are pathlib.Path object to make file manipulation easier
    raster_path = Path(raster_path)
    temp_dir = Path(temp_dir)

    logger.info("Reprojecting to EPSG 3857")
    # Note that the reprojected greyscale raster is saved to the main output directory
    reprojected_path = temp_dir.joinpath(f"{raster_path.stem}_3857.tif")
    reprojected_path = reproject_raster(
        input_path=raster_path, output_path=reprojected_path, output_epsg_code=DEFAULT_EPSG_CODE
    )

    logger.info("Converting reprojected raster to COG")
    output_greyscale_cog_path = output_dir.joinpath(f"{reprojected_path.stem}_cog.tif")
    convert_to_cog(reprojected_path, output_greyscale_cog_path)

    if colourmap_path:
        logger.info("Applying colour relief")
        colourised_path = temp_dir.joinpath(f"{reprojected_path.stem}_colourised.tif")
        apply_colour_relief(raster_path=reprojected_path, colourmap_path=colourmap_path, output_path=colourised_path)

        logger.info("Creating the legend.")
        legend_output_path = output_dir.joinpath(f"{raster_path.stem}_legend.json")
        create_legend(colourmap_path=colourmap_path, legend_path=legend_output_path)

        logger.info("Converting colour raster to COG")
        output_cog_path = output_dir.joinpath(f"{colourised_path.stem}_cog.tif")
        convert_to_cog(colourised_path, output_cog_path)

    if create_boundary:
        logger.info("Creating initial boundary geometry")
        boundary_3857_path = temp_dir.joinpath(f"{colourised_path.stem}_boundary.geojson")
        raster_boundary(raster_path=output_cog_path, output_path=boundary_3857_path)

        logger.info("Reprojecting boundary to WGS84")
        # Reproject the boundary to EPSG 4326 (WSG84) before saving to the final output directory
        boundary_4326_path = output_dir.joinpath(f"{raster_path.stem}_boundary_4326.geojson")
        boundary_ds = VectorDataset(boundary_3857_path)
        boundary_ds.reproject_layer(output_path=boundary_4326_path, target_epsg=4326, swap_xy=True)

    logger.info(f"Finished converting: {str(raster_path)}")


def reproject_to_epsg_3857(raster_path: str | Path, output_path: str | Path, input_epsg: int = 27700) -> None:
    """
    Reprojects the input raster into EPSG 3857

    This function takes an input raster and writes a reprojected raster to the output path. https://gdal.org/en/stable/api/python/utilities.html
    # for info on how to run the function osgeo.gdal.Warp(destNameOrDestDS, srcDSOrSrcDSTab, **kwargs)

    Args:
        raster_path: _description_
        output_path: _description_
        input_epsg: _description_. Defaults to 27700.
    """

    # open raster and get the spatial reference
    ds = gdal.Open(raster_path)
    ds_srs = ds.GetSpatialRef()

    # import the EPSG and put it in the container.
    # if the EPSG isn't picked up, require user input.
    if ds_srs is None:
        ds_srs = osr.SpatialReference()
        ds_srs.ImportFromEPSG(input_epsg)

    # get spatial reference from gdal - one to reproject to
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(3857)

    # reprojection options using gdal warp, save as an object to call later
    # https://gdal.org/en/stable/api/python/utilities.html for info on how to run the gdal.Warp function.
    options = gdal.WarpOptions(
        srcSRS=ds_srs, dstSRS=target_srs.ExportToWkt(), format="GTiff", creationOptions=DEFAULT_CREATION_OPTIONS
    )

    # Set the config options
    gdal.SetConfigOption("GTIFF_SRS_SOURCE", "EPSG")

    # run the reprojection
    gdal.Warp(output_path, ds, options=options)


def convert_to_cog(raster_path: str | Path, output_path: str | Path) -> None:
    """Converts the input raster to its COG formatted equivalent.

    Args:
        raster_path: Path to the raster to be converted
        output_path: Path to write the converted raster to.

    """
    translate_options = gdal.TranslateOptions(
        format="COG",
        creationOptions=["COMPRESS=DEFLATE", "PREDICTOR=2", "OVERVIEWS=IGNORE_EXISTING", "OVERVIEW_COUNT=10"],
    )
    gdal.Translate(output_path, raster_path, options=translate_options)


if __name__ == "__main__":
    main()
