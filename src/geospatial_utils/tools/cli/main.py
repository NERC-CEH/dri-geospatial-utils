import argparse

from geospatial_utils.tools import (
    clip_raster,
    colour_elevation_raster,
    colour_raster,
    convert_to_cog,
    merge_nodata,
    merge_rasters,
    raster_boundary,
    rasterise_vector,
    reproject_raster,
    scale_raster,
)
from geospatial_utils.tools.fdri import csv_to_geojson

MODULES = [
    convert_to_cog,
    reproject_raster,
    csv_to_geojson,
    raster_boundary,
    merge_rasters,
    scale_raster,
    clip_raster,
    merge_nodata,
    colour_raster,
    colour_elevation_raster,
    rasterise_vector,
]


def construct_parser() -> argparse.Parser:
    parser = argparse.ArgumentParser(prog="Geospatial Utilities")

    subparser = parser.add_subparsers(title="subcommands")
    # Add scripts to the main parser
    for module in MODULES:
        add_module_parser(subparser, module)

    return parser


def add_module_parser(subparser: argparse.ArgumentParser, module: callable) -> argparse.ArgumentParser:
    module_parser = subparser.add_parser(name=module.COMMAND, help=module.DESCRIPTION)
    module.add_arguments(module_parser)
    module_parser.set_defaults(func=module.run_from_cli)

    return module_parser


if __name__ == "__main__":
    construct_parser()
