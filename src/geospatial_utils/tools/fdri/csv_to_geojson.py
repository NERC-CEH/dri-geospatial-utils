"""Script to convert csv metadata into geojson format"""

import argparse
import logging
import os
from pathlib import Path
from types import SimpleNamespace

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)

COMMAND = "obs_fdri_to_geojson"
DESCRIPTION = "Convert gauging csv files into geojson to store metadata."

# create a mapping to create consistant column names in all fdri observatory csv files.
POSSIBLE_NAME_KEY = {
    "Start_date": ["start_Date", "Data Start", "data_start", "Data_start", "start_date", "oldest_survey", "TUBE_START"],
    "End_date": ["Data End", "Data_end", "newest_survey", "end_date", "TUBE_END_D"],
    "Site_ID": ["AWS_ID", "Site ID", "Station_number", "SiteID", "TUBE_ID"],
    "Altitude": ["altitude", "Altitude_m", "ALTITUDE"],
    "Name": ["AWS_name", "Site Name", "SiteName", "AWS_Name", "SITE_NAME"],
    "Latitude": ["lat", "latitude", "LATITUDE"],
    "Longitude": ["lon", "longitude", "LONGITUDE"],
    "Instrument": ["instrument"],
}


def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--output_geojson_dir",
        required=True,
        type=Path,
        help=("directory to store all geoson files containing metadata."),
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input_csv_path", type=Path, help="Path to the csv to be converted")
    input_group.add_argument(
        "--input_csv_dir",
        type=Path,
        help=(
            "Path to the directory containing csvs to be converted. All .csv files found within this directory "
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
    """The entrypoint when running from the centralised CLI."""
    # Call the main run function
    run(
        input_csv_path=args.input_csv_path,
        input_csv_dir=args.input_csv_dir,
        output_geojson_dir=args.output_geojson_dir,
    )


def run(output_geojson_dir: str | Path, input_csv_path: str | Path = None, input_csv_dir: str | Path = None) -> None:
    # create the output directory if it doesn't already exist
    os.makedirs(output_geojson_dir, exist_ok=True)

    if input_csv_path is not None:
        csv_to_geojson(input_csv_path=input_csv_path, output_geojson_dir=output_geojson_dir)

    else:
        input_csv_dir = Path(input_csv_dir)

        for input_csv_path in input_csv_dir.rglob("*.csv"):
            logger.info(f"Converting {input_csv_path.name} to geojson")

            csv_to_geojson(input_csv_path=input_csv_path, output_geojson_dir=output_geojson_dir)

    print("finished")


def csv_to_geojson(input_csv_path: str | Path, output_geojson_dir: str | Path) -> None:
    """takes the metadata in csv format and creates a geojson file

    inputs: a directory with multiple csvs to process or an individual metadata.csv

    outputs: metadata.geojson

    """
    # open the csv file
    df = pd.read_csv(input_csv_path, encoding="utf-8-sig")

    # normalise columns first
    df.columns = df.columns.str.strip()

    # create an empty dictionary to store standardised column headers.
    resolved_columns = {}

    # check for each alias name and store the corresponding standard name.
    for standard_name, aliases in POSSIBLE_NAME_KEY.items():
        for alias in aliases:
            if alias in df.columns:
                resolved_columns[alias] = standard_name
                break

    # rename the column headers to the newly matched ones.
    df = df.rename(columns=resolved_columns)

    # keep columns that have been mapped
    cols_to_keep = list(set(df.columns).intersection(POSSIBLE_NAME_KEY.keys()))

    # convert start and end dates to consistent format
    if "Start_date" in df.columns:
        df["Start_date"] = pd.to_datetime(df["Start_date"], errors="coerce")

        mask = df["Start_date"].isna()
        df.loc[mask, "Start_date"] = pd.to_datetime(
            df.loc[mask, "Start_date"].astype(str), format="%Y%m%d", errors="coerce"
        )

        df["Start_date"] = df["Start_date"].dt.strftime("%Y-%m-%d")

    if "End_date" in df.columns:
        df["End_date"] = pd.to_datetime(df["End_date"], errors="coerce")

        mask = df["End_date"].isna()
        df.loc[mask, "End_date"] = pd.to_datetime(
            df.loc[mask, "End_date"].astype(str), format="%Y%m%d", errors="coerce"
        )

        df["End_date"] = df["End_date"].dt.strftime("%Y-%m-%d")

    # convert to geodataframe
    geo_df = gpd.GeoDataFrame(
        df[cols_to_keep], geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]), crs="EPSG:4326"
    )

    output_geojson_path = output_geojson_dir / f"{input_csv_path.stem}.geojson"

    geo_df.to_file(output_geojson_path, driver="GeoJSON")

    print("finished")


if __name__ == "__main__":
    main()
