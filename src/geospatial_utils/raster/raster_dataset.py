from pathlib import Path
from typing import NamedTuple

from osgeo import gdal, osr

from geospatial_utils.utils.dataset_utils import DatasetABC


class GeoTransform(NamedTuple):
    ul_x: float
    x_res: float
    x_rot: float
    ul_y: float
    y_rot: float
    y_res: float


class Point(NamedTuple):
    x: float
    y: float


class RasterDataset(DatasetABC):
    def __init__(self, ds: str | Path | gdal.Dataset):
        super().__init__(ds)

        self.geotransform = GeoTransform(*self.ds.GetGeoTransform())

    def open_dataset(self, file_path: str | Path) -> None:
        """Open the raster as a gdal.Dataset and store it as self.ds.

        Args:
            file_path: Path to the raster to be opened.

        Raises:
            IOError: The raster file doesn't exist.

        """
        if not Path(file_path).exists() and not str(file_path).startswith("/vsicurl"):
            raise IOError(f"The dataset; {file_path} does not exist")

        self.ds = gdal.Open(str(file_path))

    def get_srs(self) -> osr.SpatialReference:
        return self.ds.GetSpatialRef()

    @property
    def is_rgb(self) -> bool:
        """Performs a primitive check to see if the raster is likely to be an RGB or RGBA dataset."""
        return self.ds.RasterCount in (3, 4)

    def convert_pixel_coord_to_native_srs(self, pixel_x: int, pixel_y: int) -> Point:
        """Converts a pixel coordinate to its corresponding native srs x/y coordinate of the upper left hand corner.

        Args:
            pixel_x: Pixel x coordinate.
            pixel_y: Pixel y coordinate

        Returns:
            Point object containing the xy coordinates.

        """
        # Taken from https://gdal.org/en/stable/user/raster_data_model.html#affine-geotransform
        x_coord = self.geotransform.ul_x + pixel_x * self.geotransform.x_res + pixel_y * self.geotransform.x_rot
        y_coord = self.geotransform.ul_y + pixel_x * self.geotransform.y_rot + pixel_y * self.geotransform.y_res

        return Point(x=x_coord, y=y_coord)

    def convert_native_srs_to_pixel_coord(self, x_coord: float, y_coord: float) -> tuple[int, int]:
        """Convert a native srs x/y coordinate pair to the corresponding pixel coordinate.

        Args:
            x_coord: X coordinate in the native srs for the raster.
            y_coord: Y coordinate in the native srs for the raster.

        Returns:
            Pixel coordinates rounded to the nearest integer.

        """
        x_pixel = (
            x_coord
            - self.geotransform.ul_x
            - self.geotransform.x_rot / self.geotransform.y_res * (y_coord - self.geotransform.ul_y)
        ) / (self.geotransform.x_res - self.geotransform.x_rot * self.geotransform.y_rot / self.geotransform.y_res)

        y_pixel = (y_coord - self.geotransform.ul_y - x_coord * self.geotransform.y_rot) / self.geotransform.y_res
        return int(round(x_pixel, 0)), int(round(y_pixel, 0))

    def block_iterator(self) -> tuple(int, int, int, int):
        raster_band = self.ds.GetRasterBand(1)
        block_x_size, block_y_size = raster_band.GetBlockSize()

        # work out offsets
        for x_offset in range(0, self.ds.RasterXSize, block_x_size):
            for y_offset in range(0, self.ds.RasterYSize, block_y_size):
                x_size = block_x_size
                y_size = block_y_size

                # The row and column indices refer to the bottom left pixel. Calculate the maximum row and column being
                # read aren't going to be beyond the size of the raster, and adjust the x and y sizes accordingly

                if x_offset + block_x_size > self.ds.RasterXSize:
                    x_size = self.ds.RasterXSize - x_offset

                if y_offset + block_y_size > self.ds.RasterYSize:
                    y_size = self.ds.RasterYSize - y_offset

                yield x_offset, y_offset, x_size, y_size
