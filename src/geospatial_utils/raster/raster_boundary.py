import subprocess
from pathlib import Path


def extract_raster_boundary(raster_path: str | Path, output_path: str | Path) -> None:
    """
    Extract the boundary of all areas within a raster that do not contain no data.
    This can be used to produce a more accurate outline of a raster in comparison to the general bounding box.

    Args:
        raster_path: Path to the raster to extract the boundary from
        output_path: Path to save the boundary geojson file to. This should include the filename and geojson extension.
            for example `~/raster_data/boundary.geojson`

    """
    subprocess.run(
        ["gdal", "raster", "footprint", "--no-location-field", str(raster_path), str(output_path)], check=True
    )
