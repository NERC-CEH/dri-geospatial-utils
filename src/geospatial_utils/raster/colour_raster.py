import json
from pathlib import Path

import numpy as np
from osgeo import gdal
from tqdm import tqdm

from geospatial_utils.raster.io import DEFAULT_CREATION_OPTIONS
from geospatial_utils.raster.raster_dataset import RasterDataset


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


def apply_colour_relief(raster_path: str | Path, colourmap_path: str | Path, output_path: str | Path) -> None:
    """Applies the modified colour ramp text file to the raster.

    Args:
        raster_path: Path to the single band raster to be colourised.
        colour_ramp_path: Path to the .txt file containing the colour ramp information
        output_path: Path to write the output, RGBA formatted colourised raster to.

    Raises:
        ValueError: No nodata value could be found for the input raster.

    """
    ds = gdal.Open(raster_path)
    band = ds.GetRasterBand(1)
    nodata_value = band.GetNoDataValue()

    if nodata_value is None:
        raise ValueError(f"NoData value not found in {raster_path}")

    creation_options = DEFAULT_CREATION_OPTIONS
    gdal.DEMProcessing(
        destName=str(output_path),
        srcDS=gdal.Open(raster_path),
        colorFilename=colourmap_path,
        processing="color-relief",
        creationOptions=creation_options,
        addAlpha=True,
    )

    # # Ensure the nodata value for each band is 0
    # colour_ds = RasterDataset(output_path)
    # for band_index in range(1, colour_ds.ds.RasterCount + 1):
    #     band = colour_ds.ds.GetRasterBand(band_index)
    #     band.SetNoDataValue(0)

    add_alpha_mask(greyscale_raster_path=raster_path, colour_raster_path=output_path)


def add_alpha_mask(greyscale_raster_path: Path, colour_raster_path: Path) -> None:
    """Use the original greyscale raster to calculate the areas of nodata before applying them to the colour raster.

    Note that it is assumed that the greyscale and colour raster are identical and will align perfectly

    Args:
        greyscale_raster_path: Path to the original greyscale raster
        colour_raster_path: Path to the coloured raster path for the same raster
    """
    greyscale_ds = RasterDataset(greyscale_raster_path)

    colour_ds = gdal.Open(colour_raster_path, gdal.GA_Update)

    greyscale_band = greyscale_ds.ds.GetRasterBand(1)
    alpha_band = colour_ds.GetRasterBand(4)

    no_data = greyscale_band.GetNoDataValue()
    if no_data is None:
        raise ValueError("Unable to apply alpha mask to colour raster. Greyscale input has no nodata value.")

    for x_offset, y_offset, x_size, y_size in tqdm(greyscale_ds.block_iterator()):
        greyscale_arr = greyscale_band.ReadAsArray(x_offset, y_offset, x_size, y_size)
        alpah_arr = alpha_band.ReadAsArray(x_offset, y_offset, x_size, y_size)

        nodata_mask = np.logical_or(greyscale_arr == no_data, np.isnan(greyscale_arr))

        alpah_arr[nodata_mask] = 0

        # add write array
        alpha_band.WriteArray(alpah_arr, xoff=x_offset, yoff=y_offset)


def create_legend(colourmap_path: str | Path, legend_path: str | Path) -> None:
    """Creates a json file containing the legend information for the colourised raster.

    This takes the .txt colourmap file, modified to the min-max bounds for the raster being processed, and creates
    a json dictionary of the colours and corresponding values.

    The output format is as follows:

    {
        "type": "range",
        "values": [
            {
                "value": float (minimum raster value for the bound)
                "colour": [red, green, blue] (0-255 values for red, green and blue respectively)
            }
        ]
    }

    """
    legend_values = []

    with open(colourmap_path) as colourmap_file:
        colour_ramp = colourmap_file.readlines()

        min_entry = None
        for current_row in colour_ramp:
            row_components = current_row.strip().split(" ")
            value, r, g, b = row_components[:4]

            max_entry = {"value": float(value), "colour": [int(r), int(g), int(b)]}

            if min_entry is None:
                min_entry = max_entry
                continue

            legend_values.append({"min": min_entry, "max": max_entry})
            min_entry = max_entry

    legend = {"type": "range", "values": legend_values}

    with open(legend_path, "w") as legend_file:
        json.dump(legend, legend_file, indent=2)


def apply_hillshade(raster_path: str | Path, output_path: str | Path) -> None:
    """Applies the modified colour ramp text file to the raster.

    Args:
        raster_path: Path to the single band raster to be colourised.
        colour_ramp_path: Path to the .txt file containing the colour ramp information
        output_path: Path to write the output, RGBA formatted colourised raster to.

    Raises:
        ValueError: No nodata value could be found for the input raster.

    """

    creation_options = DEFAULT_CREATION_OPTIONS
    gdal.DEMProcessing(
        destName=output_path,
        srcDS=gdal.Open(raster_path),
        processing="hillshade",
        creationOptions=creation_options,
    )
