from pathlib import Path

from geospatial_utils.vector.vector_dataset import VectorDataset
from tests.testing_utils.file_comparison import compare_vector_files


class TestReprojectVector:
    def test_reproject_vector(self, input_dir: Path, output_dir: Path, working_dir: Path) -> None:
        """Check a vector dataset is reprojected correctly."""
        input_path = input_dir.joinpath("vector", "test_vector_4326.geojson")
        expected_path = output_dir.joinpath("vector", "reprojection", "test_vector_3857.geojson")

        output_path = working_dir.joinpath("test.geojson")

        input_ds = VectorDataset(input_path)
        input_ds.reproject_layer(target_epsg=3857, output_path=output_path)

        compare_vector_files(expected_vector_path=expected_path, actual_vector_path=output_path)
