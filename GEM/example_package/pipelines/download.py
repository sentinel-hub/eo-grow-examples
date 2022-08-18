"""A module with download pipeline."""
import itertools as it
from typing import List, Optional

import numpy as np
from eogrow.core.pipeline import Pipeline
from eogrow.core.schemas import BaseSchema
from pydantic import Field
from sentinelhub import Band, DataCollection, Unit

from eolearn.core import EONode, EOWorkflow, FeatureType, OverwritePermission, SaveTask
from eolearn.features import LinearFunctionTask
from eolearn.io import SentinelHubInputTask
from ..tasks.download import SpatialGridJoinTask


class GridSchema(BaseSchema):
    """A sub-schema defining a grid."""

    rows: int = Field(1, description="Number of rows in which each tile will be split for download.")
    columns: int = Field(1, description="Number of rows in which each tile will be split for download.")


class BandSchema(BaseSchema):
    """A sub-schema defining data collection band."""

    name: str
    unit: Unit
    output_type: str


class GemGHSLDownloadPipeline(Pipeline):
    class Schema(Pipeline.Schema):
        output_folder_key: str = Field(
            description="Storage manager key pointing to the path where downloaded EOPatches will be saved."
        )
        byoc_collection_id: str = Field(description="An ID of BYOC collection")
        byoc_url: Optional[str] = Field(description="Base url to use to fetch BYOC collection")
        resolution: int = Field(description="Resolution of downloaded data in meters")
        bands: Optional[List[BandSchema]] = Field(description="Bands to download")

        download_grid: GridSchema = Field(
            description=(
                "This parameter is used in case a bounding box from AOI grid is too "
                "large to download data from Sentinel Hub service. It splits a "
                "bounding box into a grid of smaller bounding boxes, downloads data "
                "for each one, and joins data afterward."
            )
        )

        data_feature: str = Field(description="A name of the data feature that will be saved")

        rescale_factor: Optional[float] = Field(description="Factor to rescale bands with")
        compress_level: int = Field(0, description="Level of compression used in saving EOPatches")
        threads_per_worker: Optional[int] = Field(
            10,
            description=(
                "Maximum number of parallel threads used during download by each worker. If set to None "
                "it will use 5 * N threads, where N is the number of processors on the machine"
            ),
        )

        processing_args: Optional[dict] = Field(
            description="Processing parameters for the aux_request_args of the SentinelHubRequests",
            default={"downsampling": "BILINEAR", "upsampling": "BILINEAR"},
        )

    def run_procedure(self):
        """Procedure which downloads satellite data."""
        workflow = self.build_workflow()

        exec_args = self.get_execution_arguments(workflow)
        exec_args = self.add_time_interval_args(workflow, exec_args)

        finished, failed, _ = self.run_execution(workflow, exec_args)
        return finished, failed

    def build_workflow(self):
        """Builds the workflow."""
        bands_feature = FeatureType.DATA, self.config.data_feature
        download_nodes = self._get_download_nodes(bands_feature)

        join_task = SpatialGridJoinTask(
            rows=self.config.download_grid.rows,
            columns=self.config.download_grid.columns,
        )
        join_node = EONode(join_task, download_nodes)

        rescale_node = None
        if self.config.rescale_factor:
            rescale_bands = LinearFunctionTask(bands_feature, slope=self.config.rescale_factor)
            rescale_node = EONode(rescale_bands, [join_node])

        save_task = SaveTask(
            self.storage.get_folder(self.config.output_folder_key, full_path=True),
            compress_level=1,
            overwrite_permission=OverwritePermission.OVERWRITE_FEATURES,
            config=self.sh_config,
        )
        save_node = EONode(save_task, [rescale_node or join_node])

        return EOWorkflow.from_endnodes(save_node)

    def _get_download_nodes(self, bands_feature):
        """Provides a list of download tasks."""
        data_collection = DataCollection.define_byoc(
            self.config.byoc_collection_id,
            service_url=self.config.byoc_url,
            bands=[
                Band(
                    name=b.name,
                    units=(b.unit,),
                    output_types=(np.typeDict[b.output_type],),
                )
                for b in self.config.bands
            ],
        )

        download_nodes = []
        sh_config = self.sh_config
        if self.config.byoc_url:
            sh_config.sh_base_url = self.config.byoc_url
        for row in range(self.config.download_grid.rows):
            for column in range(self.config.download_grid.columns):
                task = SentinelHubInputTask(
                    bands_feature=bands_feature,
                    resolution=self.config.resolution,
                    data_collection=data_collection,
                    max_threads=self.config.threads_per_worker,
                    single_scene=True,
                    aux_request_args={"processing": self.config.processing_args},
                    config=sh_config,
                )
                download_nodes.append(EONode(task, [], f"Download {row}_{column} chunk from grid"))

        return download_nodes

    def add_time_interval_args(self, workflow, args_list):
        """Adds time interval."""
        input_nodes = []
        for node in workflow.get_nodes():
            if isinstance(node.task, SentinelHubInputTask):
                input_nodes.append(node)

        bbox_list = self.eopatch_manager.get_bboxes(eopatch_list=self.patch_list)

        for index, (_, bbox) in enumerate(zip(self.patch_list, bbox_list)):
            bbox_grid = bbox.get_partition(
                num_x=self.config.download_grid.columns,
                num_y=self.config.download_grid.rows,
            )

            for sub_bbox, input_node in zip(it.chain.from_iterable(bbox_grid), input_nodes):
                args_list[index][input_node] = {
                    "bbox": sub_bbox,
                    "time_interval": (
                        "2017-01-01",
                        "2020-01-01",
                    ), 
                }

        return args_list
