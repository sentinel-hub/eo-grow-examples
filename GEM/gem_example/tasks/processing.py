import geopandas as gpd
import numpy as np
import pandas as pd

from eogrow.utils.types import Feature
from eolearn.core import EOPatch, EOTask


class AddValidDataMaskTask(EOTask):
    def __init__(
        self,
        input_feature: Feature,
        output_feature: Feature,
        invalid_data_value: float = -1.0,
    ):
        self.input_feature = self.parse_feature(input_feature)
        self.output_feature = self.parse_feature(output_feature)
        self.invalid_data_value = invalid_data_value

    def execute(self, eopatch: EOPatch) -> EOPatch:
        """Extracts valid data mask from input data feature"""
        eopatch[self.output_feature] = np.array(eopatch[self.input_feature] != self.invalid_data_value, dtype=bool)

        return eopatch


class ExtractNominalWaterTask(EOTask):
    def __init__(self, input_feature: Feature, output_feature: Feature, water_class_value: int):
        self.input_feature = self.parse_feature(input_feature)
        self.output_feature = self.parse_feature(output_feature)
        self.water_class_values = water_class_value

    def execute(self, eopatch: EOPatch) -> EOPatch:
        """Extract mask corresponding to water"""
        eopatch[self.output_feature] = np.array(eopatch[self.input_feature] == self.water_class_values, dtype=bool)
        return eopatch


class ExtractWaterPixelsTask(EOTask):
    def __init__(self, input_feature: Feature, output_feature: Feature, threshold: float):
        self.input_feature = self.parse_feature(input_feature)
        self.output_feature = self.parse_feature(output_feature)
        self.threshold = threshold

    def execute(self, eopatch: EOPatch) -> EOPatch:
        eopatch[self.output_feature] = np.array(eopatch[self.input_feature] > self.threshold, dtype=bool)
        return eopatch


class ExtractValidPixelsTask(EOTask):
    def __init__(self, input_feature: Feature, masking_feature: Feature, output_feature: Feature):
        self.input_feature = self.parse_feature(input_feature)
        self.masking_feature = self.parse_feature(masking_feature)
        self.output_feature = self.parse_feature(output_feature)

    def execute(self, eopatch: EOPatch) -> EOPatch:
        input_feature = eopatch[self.input_feature]
        if len(input_feature.shape) == 3:
            input_feature = np.repeat(input_feature[np.newaxis, ...], len(eopatch.timestamp), axis=0)

        eopatch[self.output_feature] = np.sum(input_feature & eopatch[self.masking_feature], axis=(1, 2))
        return eopatch


class ComputeFractionTask(EOTask):
    def __init__(
        self,
        water_feature: Feature,
        water_nominal_feature: Feature,
        output_feature: Feature,
    ):
        self.water_feature = self.parse_feature(water_feature)
        self.water_nominal_feature = self.parse_feature(water_nominal_feature)
        self.output_feature = self.parse_feature(output_feature)

    def execute(self, eopatch) -> EOPatch:
        gdf = gpd.GeoDataFrame()
        gdf["water_valid_pixels"] = eopatch[self.water_feature].squeeze()
        gdf["nominal_water_valid_pixels"] = eopatch[self.water_nominal_feature].squeeze()
        gdf["TIMESTAMP"] = pd.to_datetime(eopatch.timestamp)
        gdf["geometry"] = eopatch.bbox.geometry
        gdf = gdf.set_crs(eopatch.bbox.crs.epsg)

        eopatch[self.output_feature] = gdf

        return eopatch
