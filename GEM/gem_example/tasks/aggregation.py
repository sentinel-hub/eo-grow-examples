from typing import Any

import geopandas as gpd

from eogrow.utils.types import Feature
from eolearn.core import EOPatch, OutputTask


class ExtractOutputTask(OutputTask):
    """Output task to"""

    def __init__(self, *args: Any, feature: Feature, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.feature = self.parse_feature(feature)

    def execute(self, eopatch: EOPatch, *, eopatch_folder: str) -> gpd.GeoDataFrame:
        gdf = eopatch[self.feature]
        gdf["eopatch"] = eopatch_folder
        gdf["epsg"] = eopatch.bbox.crs.epsg
        return gdf
