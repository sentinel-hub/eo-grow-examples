import os
from typing import Any, Dict, List, Tuple

import pandas as pd
from pydantic import Field

from eogrow.core.pipeline import Pipeline
from eogrow.utils.fs import LocalFile
from eogrow.utils.types import Feature
from eolearn.core import EONode, EOWorkflow, FeatureType, LoadTask, OverwritePermission, SaveTask

from ..tasks.aggregation import ExtractOutputTask
from ..tasks.processing import (
    AddValidDataMaskTask,
    ComputeFractionTask,
    ExtractNominalWaterTask,
    ExtractValidPixelsTask,
    ExtractWaterPixelsTask,
)


class NDWIFractionsPipeline(Pipeline):
    class Schema(Pipeline.Schema):
        input_folder_key: str = Field("Key to input eopatches with NDWI features.")
        output_folder_key: str = Field("Key to output folder where dataframes will be saved.")
        input_water_feature: Feature = Field("Name of feature in EOPatch holding water feature.")
        input_nominal_water_feature: Feature = Field("Name of feature in EOPatch holding the nominal water feature.")
        water_class_value: int = Field("Value of water class in the nominal water feature.")
        water_threshold: float = Field("Threshold value for the water index.")
        invalid_data_value: float = Field("Value for invalid data in water feature.")
        output_feature: Feature = Field("Name of feature in EOPatch to write dataframes to.")
        output_filename: str = Field("Name of geopackage filename with aggregated water fraction data.")
        geopackage_folder_key: str = Field("Name of storage manager key pointing to the geopackage folder.")

    config: Schema

    def build_workflow(self) -> EOWorkflow:
        valid_data_feature = (FeatureType.MASK, "VALID_DATA")
        nominal_water_feature = (FeatureType.MASK_TIMELESS, "NOMINAL_WATER")
        water_feature = (FeatureType.DATA, "NDWI_WATER")
        water_mask_feature = (FeatureType.SCALAR, "NDWI_WATER_MASK")
        nominal_water_mask_feature = (FeatureType.SCALAR, "NOMINAL_WATER_MASK")

        load_task = LoadTask(
            path=self.storage.get_folder(self.config.input_folder_key),
            filesystem=self.storage.filesystem,
            features=[
                self.config.input_water_feature,
                self.config.input_nominal_water_feature,
                FeatureType.BBOX,
                FeatureType.TIMESTAMP,
            ],
        )

        load_node = EONode(load_task)

        valid_mask_task = AddValidDataMaskTask(
            input_feature=self.config.input_water_feature,
            output_feature=valid_data_feature,
            invalid_data_value=self.config.invalid_data_value,
        )

        valid_mask_node = EONode(valid_mask_task, inputs=[load_node])

        extract_nominal_water_task = ExtractNominalWaterTask(
            input_feature=self.config.input_nominal_water_feature,
            output_feature=nominal_water_feature,
            water_class_value=self.config.water_class_value,
        )

        extract_nominal_water_node = EONode(extract_nominal_water_task, inputs=[valid_mask_node])

        nominal_water_mask_task = ExtractValidPixelsTask(
            input_feature=nominal_water_feature,
            masking_feature=valid_data_feature,
            output_feature=nominal_water_mask_feature,
        )

        nominal_water_mask_node = EONode(nominal_water_mask_task, inputs=[extract_nominal_water_node])

        extract_water_task = ExtractWaterPixelsTask(
            input_feature=self.config.input_water_feature,
            output_feature=water_feature,
            threshold=self.config.water_threshold,
        )

        extract_water_node = EONode(extract_water_task, inputs=[nominal_water_mask_node])

        water_mask_task = ExtractValidPixelsTask(
            input_feature=water_feature,
            masking_feature=valid_data_feature,
            output_feature=water_mask_feature,
        )

        water_mask_node = EONode(water_mask_task, inputs=[extract_water_node])

        extract_dataframe = ComputeFractionTask(
            water_feature=water_mask_feature,
            water_nominal_feature=nominal_water_mask_feature,
            output_feature=self.config.output_feature,
        )

        extract_dataframe_node = EONode(extract_dataframe, inputs=[water_mask_node])

        extract_task = ExtractOutputTask(
            name="extract_output",
            feature=self.config.output_feature,
        )

        extract_node = EONode(extract_task, inputs=[extract_dataframe_node])

        save_task = SaveTask(
            path=self.storage.get_folder(self.config.output_folder_key),
            filesystem=self.storage.filesystem,
            features=[self.config.output_feature],
            overwrite_permission=OverwritePermission.OVERWRITE_FEATURES,
        )

        save_node = EONode(save_task, inputs=[extract_dataframe_node])

        workflow = EOWorkflow.from_endnodes(extract_node, save_node)

        return workflow

    def run_procedure(self) -> Tuple[List[str], List[str]]:
        dataframes = []
        finished_total, failed_total = [], []

        workflow = self.build_workflow()
        exec_args = self.get_execution_arguments(workflow)

        finished, failed, execution_results = self.run_execution(workflow, exec_args)
        output = "extract_output"

        dataframes += [results.outputs[output] for results in execution_results if output in results.outputs]
        finished_total += [f"{finished_}" for finished_ in finished]
        failed_total += [f"{failed_}" for failed_ in failed]

        dataframe = pd.concat(dataframes)
        crses = dataframe.epsg.unique()

        output_path = self.storage.get_folder(self.config.geopackage_folder_key)
        output_filepath = os.path.join(output_path, self.config.output_filename)
        with LocalFile(output_filepath, mode="w", filesystem=self.storage.filesystem) as out_file:
            for crs in crses:
                gdf = dataframe[dataframe.epsg == crs].copy()
                gdf = gdf.set_crs(epsg=crs, allow_override=True)
                gdf.to_file(out_file.path, driver="GPKG", encoding="utf-8", layer=f"Grid EPSG:{crs}")

        return finished, failed

    def get_execution_arguments(self, workflow: EOWorkflow) -> List[Dict[EONode, Dict[str, object]]]:
        """Prepares execution arguments for each eopatch from a list of patches

        :param workflow: A workflow for which arguments will be prepared
        """
        bbox_list = self.eopatch_manager.get_bboxes(eopatch_list=self.patch_list)

        exec_args = []
        nodes = workflow.get_nodes()
        for name, bbox in zip(self.patch_list, bbox_list):
            single_exec_dict: Dict[EONode, Dict[str, Any]] = {}

            for node in nodes:
                if isinstance(node.task, (SaveTask, LoadTask, ExtractOutputTask)):
                    single_exec_dict[node] = dict(eopatch_folder=name)

            exec_args.append(single_exec_dict)
        return exec_args
