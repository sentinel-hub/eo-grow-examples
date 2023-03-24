import datetime as dt
import os
from datetime import datetime
from typing import Any, List, Optional, Tuple

from pydantic import Field

from eogrow.pipelines.download import BaseDownloadPipeline, CommonDownloadFields, SessionLoaderType
from eogrow.types import ExecKwargs, PatchList
from eogrow.utils.types import Feature, FeatureSpec, Path
from eolearn.core import EONode, EOPatch, EOWorkflow, FeatureType
from eolearn.io import SentinelHubEvalscriptTask
from sentinelhub import MimeType, MosaickingOrder, read_data


def calculate_time_period(
    existing_timestamps: List[datetime], availability_timestamps: List[datetime]
) -> Tuple[datetime, datetime]:
    """Calculate first timestamp that is available, but does not yet exist"""

    if existing_timestamps:
        max_existing_ts = max(existing_timestamps).replace(tzinfo=None)
    else:
        max_existing_ts = datetime.min.replace(tzinfo=None)

    new_timestamps = [ts for ts in availability_timestamps if ts.replace(tzinfo=None) > max_existing_ts]

    if new_timestamps:
        return min(new_timestamps), max(new_timestamps)
    raise ValueError("No new timestamps.")


class IncrementalDownloadPipeline(BaseDownloadPipeline):
    class Schema(BaseDownloadPipeline.Schema, CommonDownloadFields):
        features: List[Feature] = Field(description="Features to construct from the evalscript")
        evalscript_path: Path
        catalog_folder_key: str = Field(
            description="The storage manager key pointing to the EOPatches with data availability info."
        )
        time_difference: Optional[float] = Field(
            description="Time difference in minutes between consecutive time frames"
        )

        mosaicking_order: Optional[MosaickingOrder] = Field(
            description="The mosaicking order used by Sentinel Hub service. Default is mostRecent"
        )

    config: Schema

    def _get_output_features(self) -> List[FeatureSpec]:
        features: List[FeatureSpec] = [FeatureType.BBOX, FeatureType.TIMESTAMP]
        features.extend(self.config.features)
        return features

    def _get_download_node(self, session_loader: SessionLoaderType) -> EONode:
        evalscript = read_data(self.config.evalscript_path, data_format=MimeType.TXT)
        time_diff = None if self.config.time_difference is None else dt.timedelta(minutes=self.config.time_difference)

        download_task = SentinelHubEvalscriptTask(
            features=self.config.features,
            evalscript=evalscript,
            data_collection=self.config.data_collection,
            resolution=self.config.resolution,
            size=self.config.size,
            maxcc=self.config.maxcc,
            time_difference=time_diff,
            max_threads=self.config.threads_per_worker,
            config=self.sh_config,
            mosaicking_order=self.config.mosaicking_order,
            downsampling=self.config.resampling_type,
            upsampling=self.config.resampling_type,
            session_loader=session_loader,
        )
        return EONode(download_task)

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.time_periods = {}

    def _get_time_period(self, eopatch_name: str) -> Tuple[datetime, datetime]:
        fs = self.storage.filesystem
        existing_folder = self.storage.get_folder(self.config.output_folder_key)
        catalog_folder = self.storage.get_folder(self.config.catalog_folder_key)
        existing_eop_path = os.path.join(existing_folder, eopatch_name)
        catalog_eop_path = os.path.join(catalog_folder, eopatch_name)
        catalog_ts = EOPatch.load(catalog_eop_path, filesystem=fs).timestamp

        existing_ts = []
        if fs.exists(existing_eop_path):
            existing_ts = EOPatch.load(existing_eop_path, filesystem=self.storage.filesystem).timestamp

        return calculate_time_period(existing_ts, catalog_ts)

    def filter_patch_list(self, patch_list: PatchList) -> PatchList:
        """EOPatches are filtered according to existence of specified output features"""
        filtered_patch_list: PatchList = []
        for name, bbox in patch_list:
            try:
                time_period = self._get_time_period(name)
                self.time_periods[name] = time_period
                filtered_patch_list.append((name, bbox))
            except ValueError:
                continue
        return filtered_patch_list

    def get_execution_arguments(self, workflow: EOWorkflow, patch_list: PatchList) -> ExecKwargs:
        """Adds required bbox and time_interval parameters for input task to the base execution arguments

        :param workflow: EOWorkflow used to download images
        """
        exec_args = super().get_execution_arguments(workflow, patch_list)

        download_node = workflow.get_node_with_uid(self.download_node_uid)

        if download_node is None:
            return exec_args

        for name, bbox in patch_list:
            exec_args[name][download_node] = {"bbox": bbox, "time_interval": self.time_periods[name]}

        return exec_args
