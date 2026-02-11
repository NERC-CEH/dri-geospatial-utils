import argparse


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI."""
    parser = argparse.ArgumentParser()

    # Example parser entry. Delete before use
    parser.add_argument(
        "--input_path",
        help="help string"
    )

    return parser


def main() -> None:
    """Entrypoint to the script."""
    parser = build_parser()
    args = parser.parse_args()

    run(*args)


def run(*args, **kwargs) -> None:
    """The main run function."""

    print("Finished")


if __name__ == "__main__":
    main()
