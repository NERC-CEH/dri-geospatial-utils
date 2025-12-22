import shutil
from pathlib import Path

import pytest


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).parents[0].joinpath("data")


@pytest.fixture
def input_dir(data_dir: Path) -> Path:
    return data_dir.joinpath("inputs")


@pytest.fixture
def output_dir(data_dir: Path) -> Path:
    return data_dir.joinpath("outputs")


@pytest.fixture
def working_dir(data_dir: Path) -> Path:
    working_dir = data_dir.joinpath("temp")

    if working_dir.exists():
        shutil.rmtree(working_dir)

    working_dir.mkdir(exist_ok=True)

    # Run the test logic
    yield working_dir

    # Cleanup the working directory
    shutil.rmtree(working_dir)
