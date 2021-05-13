# coding=utf-8
# Copyright 2021 The Deeplab2 Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Visualizes and stores results of a panoptic-deeplab model."""
import os.path
from typing import Any, Dict, List, Text

import numpy as np
import tensorflow as tf

from deeplab2 import common
from deeplab2.data import dataset
from deeplab2.trainer import vis_utils

# The format of the labels.
_IMAGE_FORMAT = '%06d_image'
_CENTER_LABEL_FORMAT = '%06d_center_label'
_OFFSET_LABEL_FORMAT = '%06d_offset_label'
_PANOPTIC_LABEL_FORMAT = '%06d_panoptic_label'
_SEMANTIC_LABEL_FORMAT = '%06d_semantic_label'

# The format of the predictions.
_INSTANCE_PREDICTION_FORMAT = '%06d_instance_prediction'
_CENTER_HEATMAP_PREDICTION_FORMAT = '%06d_center_prediction'
_OFFSET_PREDICTION_RGB_FORMAT = '%06d_offset_prediction_rgb'
_PANOPTIC_PREDICTION_FORMAT = '%06d_panoptic_prediction'
_SEMANTIC_PREDICTION_FORMAT = '%06d_semantic_prediction'

# The format of others.
_ANALYSIS_FORMAT = '%06d_semantic_error'

# Conversion from train id to eval id.
_CITYSCAPES_TRAIN_ID_TO_EVAL_ID = (
    7, 8, 11, 12, 13, 17, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 31, 32, 33, 0
)


def _crop_like(tensor_to_crop: np.ndarray,
               crop_to_tensor: np.ndarray) -> np.ndarray:
  h, w = crop_to_tensor.shape[:2]
  return tensor_to_crop[:h, :w, ...]


def _convert_cityscapes_train_id_to_eval_id(
    prediction: np.ndarray) -> np.ndarray:
  """Converts the predicted label for evaluation.

  There are cases where the training labels are not equal to the evaluation
  labels. This function is used to perform the conversion so that we could
  evaluate the results on the evaluation server.

  Args:
    prediction: Semantic segmentation prediction.

  Returns:
    Semantic segmentation prediction whose labels have been changed.
  """
  length = np.maximum(256, len(_CITYSCAPES_TRAIN_ID_TO_EVAL_ID))
  to_eval_id_map = np.zeros((length), dtype=prediction.dtype)
  cityscapes_ids = np.asarray(
      _CITYSCAPES_TRAIN_ID_TO_EVAL_ID, dtype=prediction.dtype)
  to_eval_id_map[:len(_CITYSCAPES_TRAIN_ID_TO_EVAL_ID)] = cityscapes_ids
  return to_eval_id_map[prediction]


def _get_fg_mask(label_map: np.ndarray, thing_list: List[int]) -> np.ndarray:
  fg_mask = np.zeros_like(label_map, np.bool)
  for class_id in np.unique(label_map):
    if class_id in thing_list:
      fg_mask = np.logical_or(fg_mask, np.equal(label_map, class_id))
  fg_mask = np.expand_dims(fg_mask, axis=2)
  return fg_mask.astype(np.int)


def store_raw_predictions(predictions: Dict[str, Any],
                          image_filename: tf.Tensor,
                          dataset_info: dataset.DatasetDescriptor,
                          save_dir: Text,
                          sequence: tf.Tensor,
                          raw_panoptic_format='two_channel_png',
                          convert_to_eval=True):
  """Stores raw predictions to the specified path.

  Raw predictions are saved in the specified path with the specified
  `raw_panoptic_format`. For the `raw_panoptic_format`, we currently
  support `two_channel_png`, `three_channel_png` and `two_channel_numpy_array`.
  Note that `two_channel_png` and `three_channel_png` could not encode large
  values of semantic label and instance ID due to limited PNG channel size. In
  such a case, use `raw_panoptic_format` = `two_channel_numpy_array` to save
  the raw predictions as two channel numpy array (i.e., first channel encodes
  the semantic class and the second channel the instance ID).

  Args:
    predictions: A dctionary with string keys and any content. Tensors under
      common.TARGET_SEMANTIC_KEY and common.TARGET_PANOPTIC_KEY will be stored.
    image_filename: A tf.Tensor containing the image filename.
    dataset_info: A dataset.DatasetDescriptor specifying the dataset.
    save_dir: A path to the folder to write the output to.
    sequence: A tf.Tensor describing the sequence that the image belongs to.
    raw_panoptic_format: A string specifying what format the panoptic output
      should be stored. Supports:
      - 'two_channel_png': The popular format, also supported by the official
        COCO panoptic API (https://github.com/cocodataset/panopticapi), where
        the saved PNG image contains R-channel for semantic labels and
        G-channel for instance IDs.
      - 'three_channel_png': A simple extension of the 'two_channel_png' format,
        and is adopted in some video panoptic segmentation datasets (for
        example, KITTI-STEP and MOTChallenge-STEP), where the saved PNG image
        contains R-channel for semantic labels, G-channel for the values of
        (instance ID // 256), and B-channel for (instance ID % 256).
      - 'two_channel_numpy_array': A more flexible format (unconstrained by the
        PNG channel size), where the panoptic predictions are saved as a numpy
        array in the two channel format (i.e., first channel encodes the
        semantic class and the second channel the instance ID).
    convert_to_eval: A flag specyfing whether semantic class IDs should be
      converted to cityscapes eval IDs. This is usefulfor the official test
      sever evaluation.

  Raises:
    ValueError: An error occurs when semantic label or instance ID is larger
      than the values supported by the 'two_channel_png' or 'three_channel_png'
      format. Or, if the raw_panoptic_format is not supported.
    ValueError: If convert_to_eval is True, but the dataset is not supported.
  """
  # Note: predictions[key] contains a tuple of length 1.
  predictions = {key: predictions[key][0] for key in predictions}
  predictions = vis_utils.squeeze_batch_dim_and_convert_to_numpy(predictions)
  image_filename = image_filename.numpy().decode('utf-8')
  image_filename = os.path.splitext(image_filename)[0]

  # Store raw semantic prediction.
  semantic_prediction = predictions[common.TARGET_SEMANTIC_KEY]
  if convert_to_eval:
    if 'cityscapes' in dataset_info.dataset_name:
      semantic_prediction = _convert_cityscapes_train_id_to_eval_id(
          semantic_prediction)
    else:
      raise ValueError(
          'Unsupported dataset %s for converting semantic class IDs.' %
          dataset_info.dataset_name)
  output_folder = os.path.join(save_dir, 'raw_semantic')
  if dataset_info.is_video_dataset:
    sequence = sequence.numpy().decode('utf-8')
    output_folder = os.path.join(output_folder, sequence)
    tf.io.gfile.makedirs(output_folder)
  vis_utils.save_annotation(
      semantic_prediction,
      output_folder,
      image_filename,
      add_colormap=False)

  if common.TARGET_PANOPTIC_KEY in predictions:
    # Save the predicted panoptic annotations in two-channel format, where the
    # R-channel stores the semantic label while the G-channel stores the
    # instance label.
    panoptic_prediction = predictions[common.TARGET_PANOPTIC_KEY]
    panoptic_outputs = np.zeros(
        (panoptic_prediction.shape[0], panoptic_prediction.shape[1], 3),
        dtype=panoptic_prediction.dtype)
    predicted_semantic_labels = (
        panoptic_prediction // dataset_info.panoptic_label_divisor)
    if convert_to_eval:
      predicted_semantic_labels = _convert_cityscapes_train_id_to_eval_id(
          predicted_semantic_labels)
    predicted_instance_labels = predictions[
        common.TARGET_PANOPTIC_KEY] % dataset_info.panoptic_label_divisor

    output_folder = os.path.join(save_dir, 'raw_panoptic')
    if dataset_info.is_video_dataset:
      output_folder = os.path.join(output_folder, sequence)
      tf.io.gfile.makedirs(output_folder)
    if raw_panoptic_format == 'two_channel_png':
      if np.max(predicted_semantic_labels) > 255:
        raise ValueError('Overflow: Semantic IDs greater 255 are not supported '
                         'for images of 8-bit. Please save output as numpy '
                         'arrays instead.')
      if np.max(predicted_instance_labels) > 255:
        raise ValueError(
            'Overflow: Instance IDs greater 255 could not be encoded by '
            'G channel. Please save output as numpy arrays instead.')
      panoptic_outputs[:, :, 0] = predicted_semantic_labels
      panoptic_outputs[:, :, 1] = predicted_instance_labels
      vis_utils.save_annotation(panoptic_outputs,
                                output_folder,
                                image_filename,
                                add_colormap=False)
    elif raw_panoptic_format == 'three_channel_png':
      if np.max(predicted_semantic_labels) > 255:
        raise ValueError('Overflow: Semantic IDs greater 255 are not supported '
                         'for images of 8-bit. Please save output as numpy '
                         'arrays instead.')
      if np.max(predicted_instance_labels) > 65535:
        raise ValueError(
            'Overflow: Instance IDs greater 65535 could not be encoded by '
            'G and B channels. Please save output as numpy arrays instead.')
      panoptic_outputs[:, :, 0] = predicted_semantic_labels
      panoptic_outputs[:, :, 1] = predicted_instance_labels // 256
      panoptic_outputs[:, :, 2] = predicted_instance_labels % 256
      vis_utils.save_annotation(panoptic_outputs,
                                output_folder,
                                image_filename,
                                add_colormap=False)
    elif raw_panoptic_format == 'two_channel_numpy_array':
      panoptic_outputs[:, :, 0] = predicted_semantic_labels
      panoptic_outputs[:, :, 1] = predicted_instance_labels
      with tf.io.gfile.GFile(
          os.path.join(output_folder, image_filename + '.npy'), 'w') as f:
        np.save(f, panoptic_outputs)
    else:
      raise ValueError(
          'Unknown raw_panoptic_format %s.' % raw_panoptic_format)


def store_predictions(predictions: Dict[str, Any], inputs: Dict[str, Any],
                      image_id: int, dataset_info: dataset.DatasetDescriptor,
                      save_dir: Text):
  """Saves predictions and labels to the specified path."""
  predictions = {key: predictions[key][0] for key in predictions}
  predictions = vis_utils.squeeze_batch_dim_and_convert_to_numpy(predictions)
  inputs = {key: inputs[key][0] for key in inputs}
  del inputs[common.IMAGE_NAME]
  inputs = vis_utils.squeeze_batch_dim_and_convert_to_numpy(inputs)

  thing_list = dataset_info.class_has_instances_list
  label_divisor = dataset_info.panoptic_label_divisor
  colormap_name = dataset_info.colormap

  # 1. Save image.
  vis_utils.save_annotation(
      inputs[common.IMAGE],
      save_dir,
      _IMAGE_FORMAT % image_id,
      add_colormap=False)

  # 2. Save semantic predictions and semantic labels.
  vis_utils.save_annotation(
      predictions[common.TARGET_SEMANTIC_KEY],
      save_dir,
      _SEMANTIC_PREDICTION_FORMAT % image_id,
      add_colormap=True,
      colormap_name=colormap_name)
  vis_utils.save_annotation(
      inputs[common.GT_SEMANTIC_RAW],
      save_dir,
      _SEMANTIC_LABEL_FORMAT % image_id,
      add_colormap=True,
      colormap_name=colormap_name)

  if common.TARGET_PANOPTIC_KEY in predictions:
    # 3. Save center heatmap.
    vis_utils.save_annotation(
        vis_utils.overlay_heatmap_on_image(
            predictions[common.TARGET_CENTER_HEATMAP_KEY],
            inputs[common.IMAGE]),
        save_dir,
        _CENTER_HEATMAP_PREDICTION_FORMAT % image_id,
        add_colormap=False)
    vis_utils.save_annotation(
        vis_utils.overlay_heatmap_on_image(
            inputs[common.GT_INSTANCE_CENTER_KEY],
            inputs[common.IMAGE]),
        save_dir,
        _CENTER_LABEL_FORMAT % image_id,
        add_colormap=False)

    # 4. Save center offsets.
    center_offset_prediction = _crop_like(
        predictions[common.TARGET_OFFSET_MAP_KEY],
        predictions[common.TARGET_SEMANTIC_KEY])
    center_offset_prediction_rgb = vis_utils.flow_to_color(
        center_offset_prediction)
    semantic_prediction = predictions[common.TARGET_SEMANTIC_KEY]
    pred_fg_mask = _get_fg_mask(semantic_prediction, thing_list)
    center_offset_prediction_rgb = (
        center_offset_prediction_rgb * pred_fg_mask)
    vis_utils.save_annotation(
        center_offset_prediction_rgb,
        save_dir,
        _OFFSET_PREDICTION_RGB_FORMAT % image_id,
        add_colormap=False)

    center_offset_label = inputs[common.GT_INSTANCE_REGRESSION_KEY]
    center_offset_label_rgb = vis_utils.flow_to_color(center_offset_label)
    gt_fg_mask = _get_fg_mask(inputs[common.GT_SEMANTIC_KEY], thing_list)
    vis_utils.save_annotation(
        center_offset_label_rgb * gt_fg_mask,
        save_dir,
        _OFFSET_LABEL_FORMAT % image_id,
        add_colormap=False)

    # 5. Save instance map.
    vis_utils.save_annotation(
        vis_utils.create_rgb_from_instance_map(
            predictions[common.TARGET_INSTANCE_KEY]),
        save_dir,
        _INSTANCE_PREDICTION_FORMAT % image_id,
        add_colormap=False)

    # 6. Save panoptic segmentation.
    vis_utils.save_parsing_result(
        predictions[common.TARGET_PANOPTIC_KEY],
        label_divisor=label_divisor,
        thing_list=thing_list,
        save_dir=save_dir,
        filename=_PANOPTIC_PREDICTION_FORMAT % image_id,
        colormap_name=colormap_name)
    vis_utils.save_parsing_result(
        parsing_result=inputs[common.GT_PANOPTIC_RAW],
        label_divisor=label_divisor,
        thing_list=thing_list,
        save_dir=save_dir,
        filename=_PANOPTIC_LABEL_FORMAT % image_id,
        colormap_name=colormap_name)

  # 7. Save error of semantic prediction.
  label = inputs[common.GT_SEMANTIC_RAW].astype(np.uint8)
  error_prediction = (
      (predictions[common.TARGET_SEMANTIC_KEY] != label) &
      (label != dataset_info.ignore_label)).astype(np.uint8) * 255
  vis_utils.save_annotation(
      error_prediction,
      save_dir,
      _ANALYSIS_FORMAT % (image_id),
      add_colormap=False)