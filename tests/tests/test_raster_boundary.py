from pathlib import Path

from geospatial_utils.raster.raster_boundary import extract_raster_boundary
from tests.testing_utils.file_comparison import compare_vector_files


class TestRasterBoundary:
    def test_raster_boundary(self, input_dir: Path, output_dir: Path, working_dir: Path) -> None:
        """Check the raster boundary is produced correctly."""
        input_path = input_dir.joinpath("test_raster_3857.tif")
        output_path = working_dir.joinpath("footprint.geojson")

        expected_path = output_dir.joinpath("raster", "raster_boundary", "footprint.geojson")

        extract_raster_boundary(input_path, output_path)

        compare_vector_files(expected_vector_path=expected_path, actual_vector_path=output_path)
