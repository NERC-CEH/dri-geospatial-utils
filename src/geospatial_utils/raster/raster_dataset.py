from pathlib import Path
from typing import NamedTuple

from osgeo import gdal


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


class RasterDataset:
    def __init__(self, ds: str | Path | gdal.Dataset):
        if isinstance(ds, str | Path):
            self.open_dataset(ds)
        elif isinstance(ds, gdal.Dataset):
            self.ds = ds
        else:
            raise ValueError(f"{ds} is not a valid raster dataset.")

        self.srs = self.ds.GetSpatialRef()

        self.geotransform = GeoTransform(*self.ds.GetGeoTransform())

    def open_dataset(self, file_path: str | Path) -> None:
        """Open the raster as a gdal.Dataset and store it as self.ds.

        Args:
            file_path: Path to the raster to be opened.

        Raises:
            IOError: The raster file doesn't exist.

        """
        if not Path(file_path).exists():
            raise IOError(f"The dataset; {file_path} does not exist")

        self.ds = gdal.Open(str(file_path))

    @property
    def epsg_code(self) -> str:
        """Returns the EPSG code from the raster."""
        return self.srs.GetAuthorityCode(None)

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
