"""Convert one or more rasters to a COG formatted raster, in EPSG 3857."""

import argparse
import json
import logging
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from osgeo import gdal, osr

from geospatial_utils.raster.io import DEFAULT_CREATION_OPTIONS
from geospatial_utils.raster.reprojection import reproject_raster

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
    )


def run(
    output_dir: str | Path,
    colourmap_path: str | Path,
    raster_path: str | Path = None,
    raster_dir: str | Path = None,
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

    """
    logging.info("Converting to COG")

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

    logging.info("Finished")


def convert_single_raster_to_cog(
    raster_path: str | Path, temp_dir: str, output_dir: str | Path, colourmap_path: str | Path
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

    """

    # Ensure the raster path and temp directory are pathlib.Path object to make file manipulation easier
    raster_path = Path(raster_path)
    temp_dir = Path(temp_dir)

    logger.info("Reprojecting to EPSG 3857")
    # Note that the reprojected greyscale raster is saved to the main output directory
    reprojected_path = output_dir.joinpath(f"{raster_path.stem}_3857.tif")
    reprojected_path = reproject_raster(
        input_path=raster_path, output_path=reprojected_path, output_epsg_code=DEFAULT_EPSG_CODE
    )

    logger.info("Building colour ramp")
    output_colour_ramp_path = output_dir.joinpath(f"{raster_path.stem}_colourramp.txt")
    colour_ramp(reprojected_path, colourmap_path, output_colour_ramp_path)

    logger.info("Applying colour relief")
    colourised_path = temp_dir.joinpath(f"{reprojected_path.stem}_colourised.tif")
    apply_colour_relief(reprojected_path, output_colour_ramp_path, colourised_path)

    logger.info("Creating the legend.")
    legend_output_path = output_dir.joinpath(f"{raster_path.stem}_legend.json")
    create_legend(output_colour_ramp_path, legend_output_path)

    logger.info("Converting to COG")
    output_path = output_dir.joinpath(f"{colourised_path.stem}_cog.tif")
    convert_to_cog(colourised_path, output_path)

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


def colour_ramp(
    input_raster_path: str | Path,
    colourmap_template_path: str | Path,
    output_colour_ramp_path: str | Path,
) -> None:
    """Create the colour ramp

    Using an existing template colour ramp file to provide the colours, create a new colour ramp text file
    with the colours applied at equidistant intervals from the minimum to maximum range of the input raster.

    The template colour ramp text file should have the following format:
    - The first row corresponds to the nodata value with a rgb colour of (0, 0, 0). This will be used as the nodata
      colour when the colour ramp is applied to the raster.
    - Each row following this will have the raster value corresponding to the minimum bound for the colour, and the
      red, green, blue and alpha values for that colour. Note that alpha should always be 0

    For example, for a raster with a nodata value of -9999, a min-max range from 10-40 and three colours within the
    template colour ramp (e.g. blue, green, and yellow), the contents of the colour map would look something like this:

    ```
    -9999 0 0 0 0
    10 0 0 255 0
    20 0 255 0 0
    30 255 255 0 0
    ```

    Args:
        input_raster_path: Path to the raster file to fit the template colour ramp to.
        colourmap_template_path: Text file containing the colour ramp to modify to work with the input raster.
        output_colour_ramp_path: Location to save the customised colour ramp to. It is expected this should not already
            exist.

    Raises:
        ValueError: No nodata value could be found within the raster.

    """
    # Open input raster and get the nodata value from the elevation band.
    ds = gdal.Open(input_raster_path)
    band = ds.GetRasterBand(1)
    nodata_value = band.GetNoDataValue()

    # raise a ValueError if no NoData value is present in the raster.
    if nodata_value is None:
        raise ValueError(f"NoData value not found in {input_raster_path}")

    # get min and max of the raster to classify for colourisation.
    min_value, max_value = band.ComputeRasterMinMax(approx_ok=True)

    # open the navia template file which has the rgb for the colours
    # store the contents as a variable to call later and close the file.
    with open(colourmap_template_path) as colourmap_file:
        colourmap_data = colourmap_file.readlines()

    # calculate the evenly spaced intervals from the raster value range using linspace.
    # minus one because one entry in the no data row.
    interval_values = np.linspace(min_value, max_value, len(colourmap_data) - 1)

    # Round the interval values down to the nearest 2dp to make the legend entries easier to read.
    # By rounding down before the colour ramp is applied, it ensures that the legend corresponds
    # accurately to the colourised raster.
    interval_values = np.trunc((interval_values * 100)) / 100

    # Construct the nodata row. This will be hardcoded to black
    no_data_row = f"{nodata_value} 0 0 0 0"

    output_colourmap_data = [no_data_row]

    # loop through each row simultaneously but ignoring the no data value
    # row in the template file so the colours match the intervals.
    for row, interval_value in zip(colourmap_data[1:], interval_values):
        # Split into value, and colour code. The colour code will either be rgb or rgba
        _, colour_code = row.strip().split(" ", 1)

        # create a new row of joined data to append to output data. Add the interval
        # value to the rgb value from the template into one new row.
        new_rows = f"{interval_value} {colour_code}"
        output_colourmap_data.append(new_rows)

    # write the file to an output path.
    with open(output_colour_ramp_path, "w") as colourmap_file:
        colourmap_file.write("\n".join(output_colourmap_data))


def apply_colour_relief(
    input_raster_path: str | Path, colour_ramp_path: str | Path, colourised_path: str | Path
) -> None:
    """Applies the modified colour ramp text file to the raster.

    Args:
        input_raster_path: Path to the single band raster to be colourised.
        colour_ramp_path: Path to the .txt file containing the colour ramp information, modified to fit the input
        raster's min - max bounds and nodata value.
        colourised_path: Path to write the output, RGBA formatted colourised raster to.

    Raises:
        ValueError: No nodata value could be found for the input raster.

    """

    # Open input raster and get the nodata value from the elevation band.
    ds = gdal.Open(input_raster_path)
    band = ds.GetRasterBand(1)
    nodata_value = band.GetNoDataValue()

    # raise a ValueError if no NoData value is present in the raster.
    if nodata_value is None:
        raise ValueError(f"NoData value not found in {input_raster_path}")

    # Apply the color ramp, creating a RGBA raster.
    creation_options = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "ZLEVEL=9"]
    gdal.DEMProcessing(
        destName=colourised_path,
        srcDS=gdal.Open(input_raster_path),
        colorFilename=colour_ramp_path,
        processing="color-relief",
        creationOptions=creation_options,
    )


def create_legend(colourmap_path: str | Path, legend_path: str | Path) -> None:
    """Creates a json file containing the legend information for the colourised raster.

    This takes the .txt colourmap file, modified to the min-max bounds for the raster being processed, and creates
    a json dictionary of the colours and corresponding values.

    The output format is as follows:

    [
        {
            "value": float (minimum raster value for the bound)
            "colour": [red, green, blue] (0-255 values for red, green and blue respectively)
        }
    ]

    """
    # create a space to store the r,g b values
    legends = []

    with open(colourmap_path) as fin:
        colour_ramp = fin.readlines()

        for row in colour_ramp[1:]:
            # Each row is represented as a space separated list, with "value red green blue" and an optional "alpha"
            # value. In order to accomodate both formats, split the row into it's individual components, then extract
            # out the first 4 as the alpha value isn't needed for the legend.
            row_components = row.strip().split(" ")
            value, r, g, b = row_components[:4]

            legends.append({"value": float(value), "colour": [int(r), int(g), int(b)]})

    with open(legend_path, "w") as fout:
        json.dump(legends, fout, indent=2)


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
