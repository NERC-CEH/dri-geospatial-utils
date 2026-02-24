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

logger = logging.getLogger(__name__)

COMMAND = "convert_to_cog"
DESCRIPTION = "Convert raster(s) to COG format, reprojected into EPSG 3857."

DEFAULT_EPSG_CODE = 3857


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    # Example parser entry. Delete before use
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
        colourmap_path=args.colourmap_path,
    )


def run(raster_path: str | Path, raster_dir: str | Path, output_dir: str | Path, colourmap_path: str | Path) -> None:
    """The main run function."""
    logging.info("Converting to COG")

    # create the output diectory if it doesn't already exist
    os.makedirs(output_dir, exist_ok=True)

    # delete the temp folder if it already exists and make it again to clear it.
    with tempfile.TemporaryDirectory() as temp_dir:
        raster_paths = [os.path.join(raster_dir, "NT12NE_50CM_DSM_PHASE3.tif")]

        for raster_path in raster_paths:
            # reproject
            basename, ext = os.path.splitext(os.path.basename(raster_path))
            # writing the output file name to give the function an output path to write to.
            reprojected_path = os.path.join(temp_dir, f"{basename}_3857.tif")

            print("reprojecting...")

            reproject(raster_path, reprojected_path)

            # build colour ramp

            basename, ext = os.path.splitext(os.path.basename(reprojected_path))
            output_colour_ramp_path = os.path.join(output_dir, f"{basename}_colourramp.txt")

            print("building colour ramp")

            colour_ramp(reprojected_path, colourmap_path, output_colour_ramp_path)

            # apply relief to raster using colour ramp

            basename, ext = os.path.splitext(os.path.basename(reprojected_path))
            colourised_path = os.path.join(temp_dir, f"{basename}_colourised.tif")

            print("applying colour relief")

            apply_relief(reprojected_path, output_colour_ramp_path, colourised_path)

            # create legend

            legend_output_path = os.path.join(output_dir, f"{basename}_legend.json")
            create_legend(output_colour_ramp_path, legend_output_path)

            basename, ext = os.path.splitext(os.path.basename(colourised_path))
            cogified_path = os.path.join(output_dir, f"{basename}_cogified.tif")

            print("cogifyiing...")

            cogification(colourised_path, cogified_path)

            print("finished...")

    logging.info("Finished")


# --------------
# REPROJECT RASTER
# --------------


def reproject(raster_path: str | Path, output_path: str | Path, input_epsg: int = 27700) -> None:
    # open raster and get the spatial reference
    ds = gdal.Open(raster_path)
    ds_srs = ds.GetSpatialRef()

    # if the spatial reference is None - data may be old and formatted differently, hard code the epsg.
    # import the EPSG and put it in the container.
    # if the EPSG isn't picked up, require user input.

    if ds_srs is None:
        ds_srs = osr.SpatialReference()
        ds_srs.ImportFromEPSG(input_epsg)

    # get spatial reference from gdal - one to reproject to
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(3857)

    # compression set up (can be from QGIS advanced high comopression export)
    creation_options = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "ZLEVEL=9"]

    # reprojection options using gdal warp, save as an object to call later
    options = gdal.WarpOptions(
        srcSRS=ds_srs, dstSRS=target_srs.ExportToWkt(), format="GTiff", creationOptions=creation_options
    )

    # run the reprojection
    # https://gdal.org/en/stable/api/python/utilities.html
    # osgeo.gdal.Warp(destNameOrDestDS, srcDSOrSrcDSTab, **kwargs)
    gdal.SetConfigOption("GTIFF_SRS_SOURCE", "EPSG")
    # where the output goes first, the opened dataset
    gdal.Warp(output_path, ds, options=options)

    print("finish")


# ---------------
# BUILD COLOUR RAMP FILE
# ---------------


# create the values to apply the colour ramp to. input the raster and path to colour template.
# Output path to colour ramp.txt
# build colour ramp
def colour_ramp(
    input_raster_path: str | Path, colourmap_template_path: str | Path, output_colour_ramp_path: str | Path
) -> None:
    ds = gdal.Open(input_raster_path)
    band = ds.GetRasterBand(1)

    # get min and max of the raster to classify for colourisation.
    min_value, max_value = band.ComputeRasterMinMax(approx_ok=True)

    # open the navia template file which has the rgb for the colours
    # store the contents as a variable to call later and close the file.
    with open(colourmap_template_path) as colourmap_file:
        colourmap_data = colourmap_file.readlines()

    # calculate the interval from the raster value range e.g a break point
    # will be at every 20 (colour_interval)
    colour_interval = (max_value - min_value) / (len(colourmap_data) - 1)

    # create the values for the entire range to assign the colours to
    interval_values = np.around(np.arange(min_value, max_value, colour_interval), 0)

    # store the output data with values from the colour ramp template and
    # and the interval values.
    # keep the first line from the template which has the no data value.
    output_colourmap_data = [colourmap_data[0].strip()]

    # loop through each file simultaneously bug ignoring the no data value
    # row in the template file so the colours match the intervals.
    for row, interval_value in zip(colourmap_data[1:], interval_values):
        _, red, green, blue = row.strip().split(" ")

        # create a new row of joined data to append to output data. Add the interval
        # value to the rgb value from the template into one new row.
        new_row = " ".join([str(np.around(interval_value, 2)), red, green, blue])
        output_colourmap_data.append(new_row)

    # write the file to an output path.
    with open(output_colour_ramp_path, "w") as colourmap_file:
        colourmap_file.write("\n".join(output_colourmap_data))

    print()


# ------------
# APPLY COLOUR RELIEF
# ------------


# apply colour relief to the reprojected raster, output is a temp colour tiff, using the output from
# building the colour ramp
def apply_relief(reprojected_path: str | Path, colour_ramp_path: str | Path, colourised_path: str | Path) -> None:
    creation_options = ["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=2", "ZLEVEL=9"]
    gdal.DEMProcessing(
        destName=colourised_path,
        srcDS=gdal.Open(reprojected_path),
        colorFilename=colour_ramp_path,
        processing="color-relief",
        creationOptions=creation_options,
    )

    # store values from the colourmap generated where rgb values are from the Navia template
    # and values are from the range of values in the raster.


# -----------
# CREATE LEGEND
# -----------


def create_legend(colourmap_path: str | Path, legend_path: str | Path) -> None:
    # create a space to store the r,g b values
    legends = []

    with open(colourmap_path) as fin:
        colour_ramp = fin.readlines()

        for row in colour_ramp[1:]:
            # say what the values are
            value, r, g, b = row.strip().split(" ")

            # store the value in legends
            legends.append({"value": float(value), "colour": [int(r), int(g), int(b)]})
    with open(legend_path, "w") as fout:
        json.dump(legends, fout, indent=2)


# ----------
# CONVERT TO COG
# ----------


def cogification(colourised_path: str | Path, cogified_path: str | Path) -> None:
    translate_options = gdal.TranslateOptions(
        format="COG",
        creationOptions=["COMPRESS=DEFLATE", "PREDICTOR=2", "OVERVIEWS=IGNORE_EXISTING", "OVERVIEW_COUNT=10"],
    )
    gdal.Translate(cogified_path, colourised_path, options=translate_options)


if __name__ == "__main__":
    main()
