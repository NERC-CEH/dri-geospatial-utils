
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

## Using the command line

Once the geospatial repo has been installed, this list of available commandline based tools can be viewed using the following command:

```commandline
python -m geospatial_utils --help
```

To run a specific tool (e.g. convert to cog), the name of the tool is appended onto the command. For example, the following command will display the help for the `convert_to_cog` command:


```commandline
python -m geospatial_utils convert_to_cog --help
```

### Developing tools for the command line

Command line based geospatial tools can be found in geospatial_utils/tools. Within this folder is `template.py` which provides a foundation structure for the commandline tool. The structure of the template has been designed to make it simple to create and register new geospatial cli based scripts. It is important to retain the `COMMAND` and `DESCRIPTION` constants, alongside the pre-defined contents of the `main()` and `run_from_cli` functions. The `run_from_cli` function in particular is hard coded as the CLI entrypoint when registering the function with the CLI. The contents of `run_from_cli` and the subsequent `run` function can be modified freely (including the `run` function name and declaration).


To register the new script to be accessible on the command line, import the whole module (e.g. `from geospatial_utils.tools import convert_to_cog`) into `geospatial_utils.tools.cli.main` and add it as a new entry within the `MODULES` list at the top of the file. This will automatically ensure it is included as an entry within the overall CLI parser. 