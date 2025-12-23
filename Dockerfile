FROM condaforge/miniforge3:25.11.0-0

RUN apt update && apt install -y --no-install-recommends git

WORKDIR /app

COPY pyproject.toml environment.yml /app/
COPY src /app/src

RUN conda env update -n base --file environment.yml

RUN pip install -e .[dev]

ENV PATH=/opt/conda/envs/gis_utils/bin:$PATH
ENV CONDA_DEFAULT_ENV=gis_utils
