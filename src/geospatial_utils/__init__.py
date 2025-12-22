import autosemver
from osgeo import gdal

try:
    __version__ = autosemver.packaging.get_current_version(project_name="geospatial_utils")
except Exception:
    __version__ = "0.0.0"

gdal.UseExceptions()
