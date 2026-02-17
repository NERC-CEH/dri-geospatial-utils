import logging
import sys

from geospatial_utils.tools.cli.main import construct_parser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main(argv: list[str]) -> None:
    parser = construct_parser()
    args = parser.parse_args(argv)
    args.run()


if __name__ == "__main__":
    main(sys.argv[1:])
