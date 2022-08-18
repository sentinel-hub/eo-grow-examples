"""Tasks used in download pipeline."""
import copy

import numpy as np

from eolearn.core import EOPatch, EOTask, FeatureType, deep_eq
from sentinelhub import BBox


class SpatialGridJoinTask(EOTask):
    """Spatially joins EOPatches, which bounding boxes form a regular grid, into a single EOPatch.

    TODO: this task could eventually be moved to eo-learn, here are potential extensions:
    - support overlap and how data is merged on overlap
      * some joining with overlap functionality is already implemented in sgbd.tasks.prediction.BuildingPredictionTask
    - missing bboxes and no_data_value
    """

    def __init__(self, rows, columns):
        self.rows = rows
        self.columns = columns

    def _get_grid_indices_and_joined_bbox(self, eopatches):
        """Provides a list of index pairs, one for each EOPatch. A pair of indices signifies where in the grid an
        EOPatch is located. Indices are counted from the lower left corner.

        Besides that this method also provides a final joined bbox.
        """
        bboxes = [eopatch.bbox for eopatch in eopatches]

        coords_x = set()
        coords_y = set()
        for bbox in bboxes:
            x0, y0, x1, y1 = list(bbox)
            coords_x.add(x0)
            coords_x.add(x1)
            coords_y.add(y0)
            coords_y.add(y1)

        coord_x_to_index = {value: index for index, value in enumerate(sorted(coords_x))}
        if len(coord_x_to_index) != self.columns + 1:
            raise ValueError("BBoxes don't form a regular grid in x dimension")
        coord_y_to_index = {value: index for index, value in enumerate(sorted(coords_y))}
        if len(coord_y_to_index) != self.rows + 1:
            raise ValueError("BBoxes don't form a regular grid in y dimension")

        grid_indices = []
        for bbox in bboxes:
            x0, y0, x1, y1 = list(bbox)

            index_x = coord_x_to_index[x0]
            if coord_x_to_index[x1] != index_x + 1:
                raise ValueError("Grid seems to have irregular coordinates in x dimension")

            index_y = coord_y_to_index[y0]
            if coord_y_to_index[y1] != index_y + 1:
                raise ValueError("Grid seems to have irregular coordinates in y dimension")

            grid_indices.append((index_x, index_y))

        unique_crs = bboxes[0].crs
        if not all(bbox.crs is unique_crs for bbox in bboxes[1:]):
            raise ValueError("Bounding boxes should have the same CRS")

        joined_bbox = BBox(
            (
                min(coord_x_to_index),
                min(coord_y_to_index),
                max(coord_x_to_index),
                max(coord_y_to_index),
            ),
            unique_crs,
        )

        return grid_indices, joined_bbox

    def _join_spatial_data(self, spatial_arrays, grid_indices):
        """Spatially joins arrays according to the grid indices."""
        array_shape = spatial_arrays[0].shape
        if not all(array.shape == array_shape for array in spatial_arrays):
            raise NotImplementedError("Arrays of a spatial feature from each EOPatch should be the same shapes")

        array_dtype = spatial_arrays[0].dtype
        if not all(array.dtype == array_dtype for array in spatial_arrays):
            raise ValueError("Arrays of a spatial feature from each EOPatch should be the same dtype")

        if len(array_shape) == 4:
            height, width = array_shape[1], array_shape[2]
            joined_shape = (
                array_shape[0],
                self.rows * height,
                self.columns * width,
                array_shape[3],
            )
        else:
            height, width = array_shape[0], array_shape[1]
            joined_shape = self.rows * height, self.columns * width, array_shape[2]

        joined_array = np.empty(joined_shape, dtype=array_dtype)

        for array, (index_x, index_y) in zip(spatial_arrays, grid_indices):
            index_y = self.rows - 1 - index_y
            slice_x = slice(index_x * width, (index_x + 1) * width)
            slice_y = slice(index_y * height, (index_y + 1) * height)
            joined_array[..., slice_y, slice_x, :] = array

        return joined_array

    def execute(self, *eopatches):
        if len(eopatches) != self.rows * self.columns:
            raise ValueError(f"Expected exactly {self.rows} * {self.columns} EOPatches but {len(eopatches)} received")

        if len(eopatches) == 1:
            return copy.copy(eopatches[0])

        grid_indices, joined_bbox = self._get_grid_indices_and_joined_bbox(eopatches)

        joined_eopatch = EOPatch(bbox=joined_bbox)

        expected_features = eopatches[0].get_features()
        if not all(eopatch.get_features() == expected_features for eopatch in eopatches[1:]):
            raise ValueError("EOPatches should have the same features")

        for feature_type, feature_names in eopatches[0].get_features().items():
            if feature_type is FeatureType.BBOX:
                continue

            if feature_type.is_spatial():
                if feature_type.is_vector():
                    raise NotImplementedError("Joining spatial vector features is not yet implemented")

                for feature_name in feature_names:
                    feature = feature_type, feature_name
                    spatial_data = [eopatch[feature] for eopatch in eopatches]
                    joined_eopatch[feature] = self._join_spatial_data(spatial_data, grid_indices)

            else:
                expected_values = eopatches[0][feature_type]

                if not all(deep_eq(eopatch[feature_type], expected_values) for eopatch in eopatches):
                    raise ValueError(
                        f"EOPatches should have the same features and values of non-spatial type {feature_type}"
                    )

                joined_eopatch[feature_type] = expected_values

        return joined_eopatch
