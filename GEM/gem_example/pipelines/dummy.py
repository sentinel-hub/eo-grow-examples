"""Implements a pipeline to construct features for training/prediction."""
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from pydantic import Field
import time
from eolearn.core import (
    EONode,
    EOWorkflow,
    LoadTask,
    EOTask
)

from eogrow.core.pipeline import Pipeline

LOGGER = logging.getLogger(__name__)


class DummyTask(EOTask):
    def execute(self, eopatch): 
        time.sleep(60*5)
        print("I am finished.")
        return eopatch
    
class DummyPipeline(Pipeline):
    """A pipeline to calculate and prepare features for ML"""

    class Schema(Pipeline.Schema):
        input_folder_key: str = Field(
            description="The storage manager key pointing to the input folder for the features pipeline."
        )

    config: Schema

    def build_workflow(self) -> EOWorkflow:
        """
        Creates a workflow:
        1. Loads and prepares a 'bands_feature' and 'valid_data_feature'
        2. Temporally regularizes bands and NDIs
        3. Calculates NDIs based on 'bands_feature'
        4. Applies post-processing, which prepares all output features
        5. Saves all relevant features (specified in _get_output_features)
        """
        preparation_node = self.get_data_preparation_node()
        dummy_task_node = EONode(DummyTask(), inputs=[preparation_node])
        return EOWorkflow.from_endnodes(dummy_task_node)

    def get_data_preparation_node(self) -> EONode:
        """Nodes that load, filter, and prepare a feature containing all bands

        :return: A node with preparation tasks and feature for masking invalid data
        """
        load_task = LoadTask(
            self.storage.get_folder(self.config.input_folder_key),
            filesystem=self.storage.filesystem,
            lazy_loading=True,
        )
        end_node = EONode(load_task)
        return end_node