from pathlib import Path

from osgeo import ogr, osr

from geospatial_utils.vector.constants import SHAPEFILE_DRIVER
from geospatial_utils.vector.types import Field


def create_vector_dataset(
    output_path: str | Path,
    layer_name: str | Path,
    srs: osr.SpatialReference,
    fields: list[Field] = [],
    driver_name: str = SHAPEFILE_DRIVER,
    geom_type: ogr.Geometry = ogr.wkbPolygon,
) -> None:
    """Creates an empty gdal.Dataset with a single layer, ready for features to be added.

    Args:
        output_path: The path to create the empty vector dataset.
        layer_name: The name of the layer create. For single layer vector file formats (geojson, shapefile), this should
            should be the filename without the extension. For example if the file is called "test.shapefile", the layer
            name will be "test"
        srs: The spatial reference to use for the output dataset.
        fields: A list of Field objects, each containing the name and the ogr.OFT field type to assign to the field.
        driver_name: Name of the driver to use to create the vector dataset. Defaults to SHAPEFILE_DRIVER.
        geom_type: Type of geometry that will be saved to the vector dataset. Defaults to ogr.wkbPolygon.

    Returns:
        Opened gdal.Dataset and ogr.Layer objects.

    """
    output_driver = ogr.GetDriverByName(driver_name)
    output_ds = output_driver.CreateDataSource(output_path)
    output_layer = output_ds.CreateLayer(layer_name, srs=srs, geom_type=geom_type)

    for field in fields:
        field_definition = ogr.FieldDefn(field.name, field.type)
        output_layer.CreateField(field_definition)

    return output_ds, output_layer


def write_feature_to_output_layer(
    output_layer: ogr.Layer,
    output_geometry: ogr.Geometry | None = None,
    feature_to_copy: ogr.Feature | None = None,
    fields_to_transfer: list[str] = [],
) -> None:
    """Write an ogr.Geometry object to a new feature in a layer, transferring any field values if required.

    Args:
        output_layer: The layer to write the feature to.
        output_geometry: The geometry to write to the output feature. If it's not provided, then the geometry from
            the feature to copy will be used.
        feature_to_copy: Optional ogr.Feature to transfer geometry and / or field values from to the new output feature.
        fields_to_transfer: List of names of the fields from the feature to copy to transfer to the output feature.

    Raises:
        ValueError: No output geometry or feature to copy has been provided.

    """
    output_feature = ogr.Feature(output_layer.GetLayerDefn())

    if not output_geometry:
        if not feature_to_copy:
            raise ValueError("An output geometry must be provided if no feature to copy is available,")

        # Use the geometry from the provided feature to copy
        output_geometry = feature_to_copy.geometry()

    if output_geometry:
        output_feature.SetGeometry(output_geometry)

    if feature_to_copy and fields_to_transfer:
        for field_name in fields_to_transfer:
            field_value = feature_to_copy.GetField(field_name)
            output_feature.SetField(field_name, field_value)

            output_layer.CreateFeature(output_feature)
