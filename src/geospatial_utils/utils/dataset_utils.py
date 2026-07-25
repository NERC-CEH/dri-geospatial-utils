from abc import ABC, abstractmethod
from pathlib import Path

from osgeo import gdal, osr


class DatasetABC(ABC):
    def __init__(self, ds: str | Path | gdal.Dataset) -> None:
        if isinstance(ds, str | Path):
            self.open_dataset(ds)
        elif isinstance(ds, gdal.Dataset):
            self.ds = ds
        else:
            raise ValueError(f"{ds} is not a valid dataset.")

        self.srs = self.get_srs()

    @abstractmethod
    def open_dataset(self, file_path: str | Path | gdal.Dataset) -> gdal.Dataset:
        pass

    @abstractmethod
    def get_srs(self) -> osr.SpatialReference:
        pass

    @property
    def epsg_code(self) -> str:
        """Returns the EPSG code from the raster."""
        epsg_code = self.srs.GetAuthorityCode(None)

        # Where the dataset has a valid epsg code (i.e. not None), convert it to its numeric format
        if epsg_code is not None:
            epsg_code = int(epsg_code)

        return epsg_code
