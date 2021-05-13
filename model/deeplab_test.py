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

"""Tests for deeplab."""

import os

import numpy as np
import tensorflow as tf

from google.protobuf import text_format
from deeplab2 import common
from deeplab2 import config_pb2
from deeplab2.data import dataset
from deeplab2.model import deeplab
# resources dependency

_CONFIG_PATH = 'deeplab2/configs/example'


def _read_proto_file(filename, proto):
  filename = filename  # OSS: removed internal filename loading.
  with tf.io.gfile.GFile(filename, 'r') as proto_file:
    return text_format.ParseLines(proto_file, proto)


def _create_model_from_test_proto(file_name):
  proto_filename = os.path.join(_CONFIG_PATH, file_name)
  config = _read_proto_file(proto_filename, config_pb2.ExperimentOptions())
  return deeplab.DeepLab(config,
                         dataset.CITYSCAPES_PANOPTIC_INFORMATION
                         ), config


class DeeplabTest(tf.test.TestCase):

  def test_deeplab_with_deeplabv3(self):
    model, experiment_options = _create_model_from_test_proto(
        'example_cityscapes_deeplabv3.textproto')
    train_crop_size = tuple(
        experiment_options.train_dataset_options.crop_size)
    input_tensor = tf.random.uniform(
        shape=(2, train_crop_size[0], train_crop_size[1], 3))
    expected_semantic_shape = [
        2, train_crop_size[0], train_crop_size[1],
        experiment_options.model_options.deeplab_v3.num_classes]
    resulting_dict = model(input_tensor)
    self.assertListEqual(
        resulting_dict[common.TARGET_SEMANTIC_LOGITS_KEY].shape.as_list(),
        expected_semantic_shape)
    num_params = np.sum(
        [np.prod(v.get_shape().as_list()) for v in model.trainable_weights])
    self.assertEqual(num_params, 39638355)

  def test_deeplab_with_deeplabv3plus(self):
    model, experiment_options = _create_model_from_test_proto(
        'example_cityscapes_deeplabv3plus.textproto')
    train_crop_size = tuple(
        experiment_options.train_dataset_options.crop_size)
    input_tensor = tf.random.uniform(
        shape=(2, train_crop_size[0], train_crop_size[1], 3))
    expected_semantic_shape = [
        2, train_crop_size[0], train_crop_size[1],
        experiment_options.model_options.deeplab_v3_plus.num_classes]
    resulting_dict = model(input_tensor)
    self.assertListEqual(
        resulting_dict[common.TARGET_SEMANTIC_LOGITS_KEY].shape.as_list(),
        expected_semantic_shape)
    num_params = np.sum(
        [np.prod(v.get_shape().as_list()) for v in model.trainable_weights])
    self.assertEqual(num_params, 39210947)

  def test_deeplab_with_deeplabv3_mv3l(self):
    model, experiment_options = _create_model_from_test_proto(
        'example_cityscapes_deeplabv3_mv3l.textproto')
    train_crop_size = tuple(
        experiment_options.train_dataset_options.crop_size)
    input_tensor = tf.random.uniform(
        shape=(2, train_crop_size[0], train_crop_size[1], 3))
    expected_semantic_shape = [
        2, train_crop_size[0], train_crop_size[1],
        experiment_options.model_options.deeplab_v3.num_classes]
    resulting_dict = model(input_tensor)
    self.assertListEqual(
        resulting_dict[common.TARGET_SEMANTIC_LOGITS_KEY].shape.as_list(),
        expected_semantic_shape)
    num_params = np.sum(
        [np.prod(v.get_shape().as_list()) for v in model.trainable_weights])
    self.assertEqual(num_params, 11024963)

  def test_deeplab_with_panoptic_deeplab(self):
    model, experiment_options = _create_model_from_test_proto(
        'example_cityscapes_panoptic_deeplab.textproto')
    train_crop_size = tuple(
        experiment_options.train_dataset_options.crop_size)
    input_tensor = tf.random.uniform(
        shape=(2, train_crop_size[0], train_crop_size[1], 3))
    expected_semantic_shape = [
        2, train_crop_size[0], train_crop_size[1],
        experiment_options.model_options.panoptic_deeplab.semantic_head.
        output_channels]
    expected_instance_center_shape = [
        2, train_crop_size[0], train_crop_size[1]]
    expected_instance_regression_shape = [
        2, train_crop_size[0], train_crop_size[1], 2]
    resulting_dict = model(input_tensor)
    self.assertListEqual(
        resulting_dict[common.TARGET_SEMANTIC_LOGITS_KEY].shape.as_list(),
        expected_semantic_shape)
    self.assertListEqual(
        resulting_dict[common.TARGET_INSTANCE_SCORES_KEY].shape.as_list(),
        expected_instance_center_shape)
    self.assertListEqual(
        resulting_dict[common.TARGET_CENTER_HEATMAP_KEY].shape.as_list(),
        expected_instance_center_shape)
    self.assertListEqual(
        resulting_dict[common.TARGET_OFFSET_MAP_KEY].shape.as_list(),
        expected_instance_regression_shape)
    num_params = np.sum(
        [np.prod(v.get_shape().as_list()) for v in model.trainable_weights])
    self.assertEqual(num_params, 54973702)

  def test_deeplab_with_panoptic_deeplab_mv3l(self):
    model, experiment_options = _create_model_from_test_proto(
        'example_cityscapes_panoptic_deeplab_mv3l.textproto')
    train_crop_size = tuple(
        experiment_options.train_dataset_options.crop_size)
    input_tensor = tf.random.uniform(
        shape=(2, train_crop_size[0], train_crop_size[1], 3))
    expected_semantic_shape = [
        2, train_crop_size[0], train_crop_size[1],
        experiment_options.model_options.panoptic_deeplab.semantic_head.
        output_channels]
    expected_instance_center_shape = [
        2, train_crop_size[0], train_crop_size[1]]
    expected_instance_regression_shape = [
        2, train_crop_size[0], train_crop_size[1], 2]
    resulting_dict = model(input_tensor)
    self.assertListEqual(
        resulting_dict[common.TARGET_SEMANTIC_LOGITS_KEY].shape.as_list(),
        expected_semantic_shape)
    self.assertListEqual(
        resulting_dict[common.TARGET_INSTANCE_SCORES_KEY].shape.as_list(),
        expected_instance_center_shape)
    self.assertListEqual(
        resulting_dict[common.TARGET_CENTER_HEATMAP_KEY].shape.as_list(),
        expected_instance_center_shape)
    self.assertListEqual(
        resulting_dict[common.TARGET_OFFSET_MAP_KEY].shape.as_list(),
        expected_instance_regression_shape)
    num_params = np.sum(
        [np.prod(v.get_shape().as_list()) for v in model.trainable_weights])
    self.assertEqual(num_params, 18226550)

  def test_deeplab_errors(self):
    proto_filename = os.path.join(
        _CONFIG_PATH, 'example_cityscapes_panoptic_deeplab.textproto')
    experiment_options = _read_proto_file(proto_filename,
                                          config_pb2.ExperimentOptions())

    with self.subTest('ResNet error.'):
      with self.assertRaises(ValueError):
        experiment_options.model_options.backbone.name = 'not_a_resnet_backbone'
        _ = deeplab.DeepLab(experiment_options,
                            dataset.CITYSCAPES_PANOPTIC_INFORMATION)

    with self.subTest('Encoder family error.'):
      with self.assertRaises(ValueError):
        experiment_options.model_options.backbone.name = 'not_a_backbone'
        _ = deeplab.DeepLab(experiment_options,
                            dataset.CITYSCAPES_PANOPTIC_INFORMATION)

  def test_deeplab_set_pooling(self):
    model, _ = _create_model_from_test_proto(
        'example_cityscapes_panoptic_deeplab.textproto')
    pool_size = (10, 10)
    model.set_pool_size(pool_size)

    self.assertTupleEqual(
        model._decoder._semantic_decoder._aspp._aspp_pool._pool_size, pool_size)
    self.assertTupleEqual(
        model._decoder._instance_decoder._aspp._aspp_pool._pool_size, pool_size)

  def test_deeplab_reset_pooling(self):
    model, _ = _create_model_from_test_proto(
        'example_cityscapes_panoptic_deeplab.textproto')
    model.reset_pooling_layer()
    pool_size = (None, None)
    self.assertTupleEqual(
        model._decoder._semantic_decoder._aspp._aspp_pool._pool_size, pool_size)
    self.assertTupleEqual(
        model._decoder._instance_decoder._aspp._aspp_pool._pool_size, pool_size)


if __name__ == '__main__':
  tf.test.main()