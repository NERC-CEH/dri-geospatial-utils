# N.B. The Python versions in the builder and prod images must match.
# Make sure to update *both* FROM lines when making changes!

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Disable Python downloads, because we want to use the system interpreter
# across both images.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0

RUN apt update && apt install -y --no-install-recommends git

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=src/mypackage/__init__.py,target=src/mypackage/__init__.py \
    uv sync --locked --no-install-project --no-dev

COPY pyproject.toml uv.lock /app/
# COPY .git /app/.git
COPY src /app/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.12-slim-bookworm AS prod

# Copy the application from the builder
COPY --from=builder --chown=app:app /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH" VIRTUAL_ENV="/app/.venv"

# Unset entrypoint from parent image
ENTRYPOINT []

CMD ["python", "-m", "mypackage"]
