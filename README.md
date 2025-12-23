
[![tests badge](https://github.com/NERC-CEH/python-template/actions/workflows/pipeline.yml/badge.svg)](https://github.com/NERC-CEH/python-template/actions)
[![docs badge](https://github.com/NERC-CEH/python-template/actions/workflows/deploy-docs.yml/badge.svg)](https://nerc-ceh.github.io/python-template/)

[Read the docs!](https://nerc-ceh.github.io/python-template)

# Geospatial Utils

A collection of geospatial utility functions and scripts.


## Getting Started

### Virtual environment setup

Due to the need to use GDAL, the conda is used for the virtual environment. Instructions for installing conda can be
found here https://github.com/conda-forge/miniforge?tab=readme-ov-file#unix-like-platforms-macos-linux--wsl

#### Creating the conda environment

To create the initial conda environment:

```commandline
conda env create -n gis_utils --file environment.yml
```

#### Activating the conda environment

To activate the environment run:

```commandline
conda activate gis_utils
```

#### Installing geospatial_utils

Activate the conda environment (`conda activate gis_utils`)

To install the geospatial utils package and any non-conda dependencies for software development purposes use the 
following command. This installs an editable version of the repository and the development specific dependencies.


```commandline
pip install -e .[dev]
```

For all other use cases:


```commandline
pip install .
```

#### Updating the environment

To update the environment run

```commandline
conda env update -n gis_utils --file environment.yml
```

### Linting

Linting uses ruff using the config in pyproject.toml

```
ruff check --fix
```

### Formatting

Formatting uses ruff using the config in pyproject.toml which follows the default black settings.

```
ruff format .
```


### Pre commit hooks

The linting, formatting and type checking can be called as a pre-commit hook. Run below to set them up.

```
pre-commit install
```

If you need to ignore the hook for a particular commit then use the `--no-verify` flag.

## Run the Tests

To run the tests, ensure the localstack docker container is running, and the virtual environment is activated. Then run:

```commandline
pytest
```
