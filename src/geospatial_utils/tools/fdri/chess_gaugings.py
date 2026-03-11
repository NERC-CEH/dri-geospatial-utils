"""Parse Chess gaugings data into metadata geojson and timeseries csv"""

import argparse
import logging
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import geojson
import pandas as pd
from pyproj import Transformer

logger = logging.getLogger(__name__)

COMMAND = "create_chess_gauging_metadata"
DESCRIPTION = "Convert gauging csv files into geojson to store metadata."


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--gauging_input_path",
        required=True,
        type=Path,
        help=("Path to the gauging file and metadata"),
    )

    parser.add_argument(
        "--output_dir",
        required=True,
        type=Path,
        help=(
            "Path to store all geoson files containing metadata. Each file which contain metadata for each station in"
            "the gauging input file."
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
        gauging_input_path=args.gauging_input_path,
        output_path=args.output_dir,
    )


gauging_input_path = Path("/home/amber-barr/temp/Chess Gaugings.csv")

output_path = Path("/home/amber-barr/temp/chess_gaugings.geojson")


# open the csv of gaugings summaries and store contents as gaugings to close the file
def run(
    gauging_input_path: Path,
) -> None:
    with open(gauging_input_path) as input_file:
        gaugings = input_file.readlines()

    # store each section of the summary into station_chunk until it reaches the next entry and store
    # that into processed_gaugings.

    station_chunk = {}
    processed_gaugings = []

    # loop through each row in the gauging summary, taking the first entry for the key and second for the value
    # ignoring empty entries.

    is_data = False
    for row in gaugings:
        # strip the /n from each row and split by commas.
        row_parts = row.strip().split(",")
        # extract the key
        row_key = row_parts[0]
        # join everything except first column, removing empty entries, join into a string
        row_value = ",".join([item for item in row_parts[1:] if item])

        # if new station name appears, save previous station and reset.
        if row_key == "Station name" and station_chunk:
            # create df
            if station_chunk.get("data_rows"):
                df = pd.DataFrame(columns=station_chunk["data_rows"][0], data=station_chunk["data_rows"][1:])
                station_chunk["df"] = df

            processed_gaugings.append(station_chunk)
            station_chunk = {row_key: row_value}
            is_data = False
            continue

        # if the row contains "", parse dates
        if "Period of record" in row_key:
            row_key, row_value = row_key.split(":", 1)
            start_date, end_date = row_value.strip().split("to")
            # start_date_strp = datetime.strptime(start_date.strip(), "%d/%m/%Y %H:%M:%S")
            # end_date_strp = datetime.strptime(end_date.strip(), "%d/%m/%Y %H:%M:%S")
            row_value = (start_date, end_date)

        # if row contains "", create column headers and an empty list for data rows.
        # switch is_data flag to True
        if "Time stamp" in row_key:
            row_key = "column_headers"
            row_value = row_parts
            station_chunk["data_rows"] = []
            is_data = True

        # append row to data_rows
        if is_data:
            # we're on a data line!
            station_chunk["data_rows"].append(row_parts)

        # if flag is false, store key/value in station dictionary.
        if not is_data:
            station_chunk[row_key] = row_value

    # build geojson features
    metadata_features = []

    transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)

    # create geojson feature of the point location, using Easting and Northing from the summary.
    for gauging in processed_gaugings:
        lon, lat = transformer.transform(float(gauging["Easting"]), float(gauging["Northing"]))
        geometry = geojson.Point((lon, lat))

        # prepare properties
        meta_properties = {
            "station_name": gauging.get("Station name"),
            "name": gauging.get("Station name", "").capitalize(),
            "station_number": gauging.get("Station number"),
            "easting": float(gauging["Easting"]),
            "northing": float(gauging["Northing"]),
            "start_date": datetime(gauging["start_date"]),
            "end_date": datetime(gauging["end_date"]),
        }

        feature = geojson.Feature(geometry=geometry, properties=meta_properties)
        metadata_features.append(feature)

    # write to file.
    with open(str(output_path), "w") as fout:
        feature_collection = geojson.FeatureCollection(metadata_features)
        geojson.dump(feature_collection, fout)

    # points to temp
    output_directory = output_path.parent

    # write the timeseries to csv
    for station in processed_gaugings:
        station_id = station["Station number"]
        station_outpath = output_directory.joinpath(f"{station_id}.csv")

        # write dataframe out to file
        station_df = station.get("df")
        if station_df is not None:
            station_df.to_csv(station_outpath, header=True, index=False)


if __name__ == "__main__":
    main()
