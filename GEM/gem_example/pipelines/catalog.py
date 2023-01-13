from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from eogrow.core.pipeline import Pipeline
from eogrow.types import ExecKwargs, PatchList
from eogrow.utils.validators import field_validator, parse_data_collection
from eolearn.core import EONode, EOWorkflow, OverwritePermission, SaveTask, linearly_connect_tasks
from sentinelhub import DataCollection, SentinelHubCatalog

from ..tasks.data_availability import LoadOrCreateEOPatch, QueryCatalogAPI


class CatalogPipeline(Pipeline):
    class Schema(Pipeline.Schema):
        input_folder_key: str = Field(
            description="The storage manager key pointing to the EOPatches with data availability.py info."
        )
        start_time: str = Field(description="The starting time from which onwards we are interested in the data.")
        data_collection: DataCollection = Field(
            description=(
                "Data collection from which data will be downloaded. See `utils.validators.parse_data_collection` for"
                " more info on input options."
            )
        )
        catalog_fields: List[str] = Field(
            default=["id", "properties.datetime", "properties.eo:cloud_cover"],
            description="List of fields requested from the Catalog API",
        )
        _validate_data_collection = field_validator("data_collection", parse_data_collection, pre=True)
        catalog_filter: Optional[str] = Field(description="Filter passed to the Catalog API request.")

        @validator("catalog_fields")
        def _check_catalog_fields(cls, catalog_fields: List[str]) -> List[str]:
            assert (
                "properties.datetime" in catalog_fields
            ), "The list for catalog_fields must include 'properties.datetime'"
            return catalog_fields

    config: Schema

    def build_workflow(self) -> EOWorkflow:
        catalog = SentinelHubCatalog(config=self.sh_config)
        eopatches_folder = self.storage.get_folder(self.config.input_folder_key)
        load_or_create = LoadOrCreateEOPatch(eopatches_folder=eopatches_folder)

        query_catalog_task = QueryCatalogAPI(
            catalog=catalog,
            data_collection=self.config.data_collection,
            catalog_fields=self.config.catalog_fields,
            catalog_filter=self.config.catalog_filter,
            start_time=self.config.start_time,
        )

        save_task = SaveTask(
            path=self.storage.get_folder(self.config.input_folder_key),
            filesystem=self.storage.filesystem,
            overwrite_permission=OverwritePermission.OVERWRITE_PATCH,
        )

        return EOWorkflow(linearly_connect_tasks(load_or_create, query_catalog_task, save_task))

    def get_execution_arguments(self, workflow: EOWorkflow, patch_list: PatchList) -> ExecKwargs:
        """Prepares execution arguments for each eopatch from a list of patches

        :param workflow: A workflow for which arguments will be prepared
        """
        exec_kwargs = {}
        nodes = workflow.get_nodes()
        for name, bbox in patch_list:
            patch_args: Dict[EONode, Dict[str, Any]] = {}

            for node in nodes:
                if isinstance(node.task, LoadOrCreateEOPatch):
                    patch_args[node] = dict(eop_name=name, bbox=bbox, filesystem=self.storage.filesystem)
                if isinstance(node.task, SaveTask):
                    patch_args[node] = dict(eopatch_folder=name)

            exec_kwargs[name] = patch_args
        return exec_kwargs
