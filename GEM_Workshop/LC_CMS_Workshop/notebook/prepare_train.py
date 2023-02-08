import logging
from functools import partial
from typing import Any, List, Tuple

import fs
import geopandas
import numpy as np
from eogrow.core.pipeline import Pipeline
from eogrow.core.storage import FS
from eolearn.core import EOTask, EOPatch
from eolearn.core import LoadTask, SaveTask, EOWorkflow, OverwritePermission, FeatureType, linearly_connect_tasks, parallelize
from eolearn.core.utils.fs import pickle_fs
from eolearn.core.utils.fs import unpickle_fs
from eolearn.geometry.transformations import VectorToRasterTask
from pydantic import Field

LOGGER = logging.getLogger()


class LoadTrainingPolygonsForEOPatch(EOTask):
    """
    This task allows the load the training polygons for the EOPatch based on the training for the AOI
    """

    def __init__(self, raster_feature: Tuple[FeatureType, str], train_polygons_filepath: str, pickeld_fs: bytes):
        self.raster_feature = raster_feature
        self.train_polygons_filepath = train_polygons_filepath
        self.pickled_fs = pickeld_fs

    def execute(self, eopatch: EOPatch):
        """Execute EOPatch
            - Transform input geometry to match the DB
            - Query DB for the vector data
            - Filter to create train & val geometries based on the feat ids given
        """
        # transform to WGS84 CRS
        # fetch from database & rename `geom` column to `geometry` so that it can be used as EOLearn Vector feature
        LOGGER.info(f"Loading training polygons from file => {self.train_polygons_filepath}")
        # save the resulting features
        filesystem = unpickle_fs(self.pickled_fs)
        eopatch[self.raster_feature] = geopandas.read_file(filesystem.openbin(self.train_polygons_filepath))
        return eopatch


class PrepareTrainingDataPipeline(Pipeline):
    """
    Sample pipeline which prepares the training data
    """

    class Schema(Pipeline.Schema):
        input_folder_key: str = Field(description='The storage manager key pointing to the EOPatch for the AOI.')
        output_folder_key: str = Field(description='The storage manager key pointing to the input folder containing EOPatch Data.')
        # plots_folder_key: str = Field(description='The storage manager key pointing to the folder where plots/charts need to be stored.')
        dataset_folder_key: str = Field(
            description='The storage manager key pointing to the folder where prepared dataset should be stored.')
        no_data_value: int = Field(default=255, description='No data value for the resulting raster features')
        training_feature: Tuple[FeatureType, str] = Field(description="Name of the training features")
        compress_level: int = Field(default=1, description='Compression level of the stored output features')

    config: Schema

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._input_directory = self.storage.get_folder(self.config.input_folder_key, full_path=True)
        self._output_directory = self.storage.get_folder(self.config.output_folder_key, full_path=True)
        self.dataset_dir = self.storage.get_folder(self.config.dataset_folder_key)
        self.input_bands = self.config.training_feature  # FeatureType.DATA, 'BANDS'
        self.reference_data = FeatureType.MASK_TIMELESS, 'TRAINING_LABELS'
        self.train_polygons_file = fs.path.join(self.dataset_dir, 'training_polygons.gpkg')

    def build_workflow(self):
        """
        We always need to override this function.
        Create a workflow with following steps :
        - Load the sampling data
        - Rasterize labels [#train & #test]
        - Save the crafted Data & Labels into a numpy file
        """
        # fetch the data for entire AOI
        load_features_task = LoadTask(path=self._input_directory, config=self.sh_config, lazy_loading=True)

        # Load vector data from database per eopatch
        vector_labels_feature = FeatureType.VECTOR_TIMELESS, 'TRAIN_LABELS'
        load_vector_data_task = LoadTrainingPolygonsForEOPatch(raster_feature=vector_labels_feature,
                                                               train_polygons_filepath=self.train_polygons_file,
                                                               pickeld_fs=pickle_fs(self.storage.filesystem))

        # Rasterize the labels
        vector_to_raster_task = VectorToRasterTask(vector_input=vector_labels_feature,
                                                   raster_feature=self.reference_data,
                                                   values_column='lcms_type',
                                                   raster_shape=self.input_bands,
                                                   no_data_value=self.config.no_data_value)

        # Save resulting EO Patches
        save_task = SaveTask(path=self._output_directory,
                             features=[FeatureType.DATA, FeatureType.MASK_TIMELESS, FeatureType.BBOX, FeatureType.TIMESTAMP],
                             overwrite_permission=OverwritePermission.OVERWRITE_FEATURES,
                             config=self.sh_config,
                             compress_level=self.config.compress_level)
        return EOWorkflow(linearly_connect_tasks(load_features_task, load_vector_data_task, vector_to_raster_task, save_task))

    def run_procedure(self) -> Tuple[List[str], List[str]]:
        """
        Function that is called when running this pipeline
        """
        # run the workflow
        finished, failed = super().run_procedure()
        self.consolidate_training_data_from_eopatches()
        return finished, failed

    def consolidate_training_data_from_eopatches(self):
        """
        This task allows consolidating the training data from all the EoPatches into a single file
        """
        eopatch_paths = [f'{self._output_directory}/{name}' for name in self.patch_list]
        # load the data from eo-patches
        results_tuple = parallelize(
            partial(self.craft_input_features_from_eopatch, self.config.training_feature,
                    self.reference_data), eopatch_paths, workers=None)
        train_data = []
        train_labels = []
        for i_train_data, i_train_labels in results_tuple:
            train_data.append(i_train_data)
            train_labels.append(i_train_labels)

        with self.storage.filesystem.openbin(fs.path.join(self.dataset_dir, 'training_features.npy'), mode='w') as f:
            np.save(f, np.vstack(train_data), allow_pickle=True)
        with self.storage.filesystem.openbin(fs.path.join(self.dataset_dir, 'training_labels.npy'), mode='w') as f:
            np.save(f, np.hstack(train_labels), allow_pickle=True)

    @staticmethod
    def craft_input_features_from_eopatch(input_data_feature, train_label_feature, eopatch_path):
        """
        This function crafts the input featurs from the EOPatch tile
        """
        eopatch = EOPatch.load(path=eopatch_path, lazy_loading=True)
        # prepare training data
        t, w, h, c = eopatch[input_data_feature].shape
        data_reshaped = np.moveaxis(eopatch[input_data_feature], 0, -2).reshape((w * h, t * c))
        labels_reshaped = eopatch[train_label_feature].reshape((h * w))
        inds_with_labels = np.isin(labels_reshaped, 255, invert=True)
        i_train_data, i_train_labels = data_reshaped[inds_with_labels], labels_reshaped[inds_with_labels]
        return i_train_data, i_train_labels