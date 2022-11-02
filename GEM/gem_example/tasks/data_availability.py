from datetime import datetime
from typing import List

from eolearn.core import EOPatch, EOTask, LoadTask
from eolearn.core.utils.fs import join_path
from sentinelhub import BBox, DataCollection, SentinelHubCatalog, parse_time


class QueryCatalogAPI(EOTask):
    def __init__(
        self,
        catalog: SentinelHubCatalog,
        data_collection: DataCollection,
        catalog_fields: List[str],
        catalog_filter: str,
        start_time: str,
    ):
        self.catalog = catalog
        self.data_collection = data_collection
        self.catalog_fields = catalog_fields
        self.catalog_filter = catalog_filter
        self.start_time = start_time

    def execute(self, eopatch: EOPatch):
        time_interval_start = eopatch[-1] if eopatch.timestamp else self.start_time

        time_interval_end = datetime.now()
        time_interval = (time_interval_start, time_interval_end)
        search_iterator = self.catalog.search(
            self.data_collection,
            bbox=eopatch.bbox,
            time=time_interval,
            filter=self.catalog_filter,
            fields={
                "include": self.catalog_fields,
                "exclude": [],
            },
        )
        results = list(search_iterator)
        timestamps = [parse_time(result["properties"]["datetime"]) for result in results]
        eopatch.timestamp.extend(timestamps)
        raw_results = eopatch.meta_info.get("RAW_RESULTS", [])
        raw_results.extend(results)
        eopatch.meta_info["RAW_RESULTS"] = raw_results
        return eopatch


class LoadOrCreateEOPatch(EOTask):
    def __init__(self, eopatches_folder: str):
        self.eopatches_folder = eopatches_folder

    def execute(self, eop_name: str, bbox: BBox, filesystem):
        if filesystem.exists(join_path(self.eopatches_folder, eop_name)):
            return LoadTask(path=self.eopatches_folder, filesystem=filesystem).execute(eopatch_folder=eop_name)
        return EOPatch(bbox=bbox)
