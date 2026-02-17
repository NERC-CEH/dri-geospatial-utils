"""Convert one or more rasters to a COG formatted raster, in EPSG 3857."""

import argparse

COMMAND = "convert_to_cog"
DESCRIPTION = "Convert raster(s) to COG format, reprojected into EPSG 3857."

def add_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    # Example parser entry. Delete before use
    parser.add_argument("--input_path", help="help string")

    return parser


def main() -> None:
    """Entrypoint to the script."""

    parser = argparse.ArgumentParser(prog=COMMAND, description=DESCRIPTION)

    parser = add_arguments(parser)
    args = parser.parse_args()

    run(*args)


def run(*args, **kwargs) -> None:
    """The main run function."""

    print("Finished")


if __name__ == "__main__":
    main()
