from pathlib import Path

from osgeo import gdal, ogr, osr

from geospatial_utils.vector.io import create_vector_dataset, write_feature_to_output_layer
from geospatial_utils.vector.types import Field


class VectorDataset:
    def __init__(self, ds: str | Path | gdal.Dataset, layer_name: str = None):
        if isinstance(ds, str | Path):
            self.open_dataset(ds)
        elif isinstance(ds, gdal.Dataset):
            self.ds = ds
        else:
            raise ValueError(f"{ds} is not a valid vector dataset.")

        self.layer = self.get_layer()
        self.srs = self.layer.GetSpatialRef()

    @property
    def fields(self) -> list[Field]:
        fields = [Field(field.name, field.type) for field in self.layer.schema]
        return fields

    @property
    def field_names(self) -> list[str]:
        return [field.name for field in self.layer.schema]

    def open_dataset(self, file_path: str | Path) -> None:
        if not Path(file_path).exists():
            raise IOError(f"The dataset; {file_path} does not exist")

        self.ds = ogr.Open(str(file_path))

    def get_layer(self, layer_name: str = None) -> ogr.Layer:
        if layer_name:
            return self.ds.GetLayer(layer_name)

        return self.ds.GetLayer()

    def reproject_layer(
        self,
        output_path: str | Path,
        target_epsg: int | None = None,
        target_srs: osr.SpatialReference | None = None,
        swap_xy: bool = False,
    ) -> None:
        """Reprojects the opened vector dataset into a new spatial reference system, saving to a new file.

        Args:
            output_path: Path to save the reprojected dataset to.
            target_epsg: EPSG code to reproject to. If this isn't used, then target_srs must be provided.
            target_srs: osr.SpatialReference object to use to reproject the dataset to. If this isn't used then 
                target_epsg must be provided.
            swap_xy: Whether to swap the xy coordinate order. This is sometimes required when converting between WGS84
                and other coordinate systems. Defaults to False.

        Raises:
            ValueError: Neither the target_epsg or target_srs variables have values.

        """
        if target_srs is None and target_epsg is None:
            raise ValueError("Either a target_epsg or a target_srs should be provided.")

        if target_epsg and target_srs is None:
            target_srs = osr.SpatialReference()
            target_srs.ImportFromEPSG(target_epsg)

        coord_transform = osr.CoordinateTransformation(self.srs, target_srs)

        # Create output vector dataset with the same format (e.g shapefile) and geometry type as the source dataset
        output_ds, output_layer = create_vector_dataset(
            output_path=output_path,
            layer_name="test",
            srs=target_srs,
            fields=self.fields,
            driver_name=self.ds.GetDriver().ShortName,
            geom_type=self.layer.GetGeomType(),
        )

        for feature in self.layer:
            geometry = feature.GetGeometryRef()
            geometry.Transform(coord_transform)

            if swap_xy:
                geometry.SwapXY()

            write_feature_to_output_layer(
                output_layer=output_layer,
                output_geometry=feature.geometry(),
                feature_to_copy=feature,
                fields_to_transfer=self.field_names,
            )

            output_ds.SyncToDisk()

        # Ensure the output dataset is properly closed by deleting it
        del output_ds, output_layer
