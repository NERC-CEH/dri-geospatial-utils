from pathlib import Path

from geospatial_utils.raster.raster_dataset import RasterDataset


class TestRasterDataset:
    def test_convert_pixel_coord_to_native_srs(self, input_dir: Path) -> None:
        """
        Check the calculation to convert from pixel coordinates of the upper left hand corner to native srs is correct.
        """
        input_path = input_dir.joinpath("raster", "test_raster_3857.tif")

        expected_x = -312709
        expected_y = 7171879

        raster_ds = RasterDataset(input_path)

        actual_x, actual_y = raster_ds.convert_pixel_coord_to_native_srs(104, 289)

        assert int(actual_x) == expected_x
        assert int(actual_y) == expected_y

    def test_convert_native_srs_to_pixel_coordinates(self, input_dir: Path) -> None:
        """Check the calculation to convert from native srs coordinates to the corresponding pixel x/y are correct."""
        input_path = input_dir.joinpath("raster", "test_raster_3857.tif")

        expected_x = 104
        expected_y = 289

        raster_ds = RasterDataset(input_path)

        actual_x, actual_y = raster_ds.convert_native_srs_to_pixel_coord(x_coord=-312709, y_coord=7171879)

        assert actual_x == expected_x
        assert actual_y == expected_y
