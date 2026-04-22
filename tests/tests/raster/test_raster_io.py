from pathlib import Path

from osgeo import gdal

from geospatial_utils.raster.io import create_raster_dataset_from_template


class TestCreateRasterDatasetFromTemplate:
    def test_create_raster_dataset_from_template(self, input_dir: Path, working_dir: Path) -> None:
        template_raster_path = input_dir.joinpath("raster", "test_raster_3857.tif")
        output_path = working_dir.joinpath("new_raster.tif")

        new_ds = create_raster_dataset_from_template(output_path=output_path, template_raster_path=template_raster_path)

        # Check the spatial reference, geotransform, number of bands, x and y size all match that of the template raster
        template_ds = gdal.Open(template_raster_path)

        assert template_ds.GetSpatialRef().IsSame(new_ds.GetSpatialRef())
        assert template_ds.GetGeoTransform() == new_ds.GetGeoTransform()

        assert template_ds.RasterCount == new_ds.RasterCount
        assert template_ds.RasterXSize == new_ds.RasterXSize
        assert template_ds.RasterYSize == new_ds.RasterYSize
