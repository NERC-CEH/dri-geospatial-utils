from pathlib import Path

from osgeo import gdal, ogr, osr

from geospatial_utils.vector.io import create_vector_dataset, write_feature_to_output_layer
from geospatial_utils.vector.types import Field
from tests.testing_utils.file_comparison import compare_vector_files


class TestCreateVectorDataset:
    def test_create_vector_dataset(self, working_dir: Path) -> None:
        """Check a new vector dataset is created correctly."""
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(3857)

        expected_fields = [("id", 0), ("name", 4)]

        ds, layer = create_vector_dataset(
            output_path=working_dir.joinpath("test.shp"),
            layer_name="test",
            srs=srs,
            fields=[Field("id", ogr.OFTInteger), Field("name", ogr.OFTString)],
        )

        assert isinstance(ds, gdal.Dataset)
        assert isinstance(layer, ogr.Layer)
        assert [(field.name, field.type) for field in layer.schema] == expected_fields


class TestWriteFeatureToOutputLayer:
    def test_write_feature_to_output_layer(self, input_dir: Path, output_dir: Path, working_dir: Path) -> None:
        """Check vector features are written to file correctly."""
        template_vector_path = input_dir.joinpath("vector", "test_vector_4326.geojson")

        template_ds = ogr.Open(template_vector_path)
        template_layer = template_ds.GetLayer()

        output_srs = template_layer.GetSpatialRef()

        output_path = working_dir.joinpath("test.shp")

        output_ds, output_layer = create_vector_dataset(
            output_path=output_path,
            layer_name="test",
            srs=output_srs,
            fields=[Field(field.name, field.type) for field in template_layer.schema],
        )

        for feature in template_layer:
            write_feature_to_output_layer(
                output_layer=output_layer,
                output_geometry=feature.geometry(),
                feature_to_copy=feature,
                fields_to_transfer=[field.name for field in template_layer.schema],
            )

        output_ds.SyncToDisk()

        compare_vector_files(expected_vector_path=template_vector_path, actual_vector_path=output_path)
