from pathlib import Path

from geospatial_utils.raster.reprojection import reproject_raster
from tests.testing_utils.file_comparison import compare_raster_files


class TestReprojectRaster:
    def test_reproject_raster_3857_to_4326(self, input_dir: Path, output_dir: Path, working_dir: Path) -> None:
        """Test projection is successful between a raster in EPSG 3857 and WGS84 (EPSG 4326)."""
        input_path = input_dir.joinpath("test_raster_3857.tif")
        expected_path = output_dir.joinpath("raster", "reprojection", "test_raster_4326.tif")

        actual_path = working_dir.joinpath("test_raster_4326.tif")

        reproject_raster(input_path=input_path, output_path=actual_path, epsg_code=4326)

        compare_raster_files(expected_raster_path=expected_path, actual_raster_path=actual_path)
