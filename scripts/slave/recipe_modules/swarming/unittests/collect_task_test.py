#!/usr/bin/env python
# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import shutil
import sys
import tempfile
import unittest


THIS_DIR = os.path.dirname(__file__)

sys.path.insert(
    0, os.path.abspath(os.path.join(THIS_DIR, '..', '..', '..', 'unittests')))
import test_env

RESOURCES_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'resources'))
sys.path.insert(0, RESOURCES_DIR)
import collect_task

from testing_support import auto_stub


class CollectTaskTest(auto_stub.TestCase):

  def setUp(self):
    super(CollectTaskTest, self).setUp()

    self.subprocess_calls = []
    def mocked_subprocess_call(args):
      self.subprocess_calls.append(args)
      return 0
    self.mock(
        collect_task.subprocess,
        'call',
        mocked_subprocess_call)

    self.temp_dir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.temp_dir)
    super(CollectTaskTest, self).tearDown()

  def test_basic(self):
    collect_cmd = [
      'swarming.py',
      'positional0',
      '--swarming-arg0', '0',
      '--swarming-arg1', '1',
      'positional1',
    ]
    build_props_json = os.path.join(self.temp_dir, 'build_properties.json')
    task_output_dir = os.path.join(self.temp_dir, 'task_output_dir')
    os.makedirs(task_output_dir)
    output_json = os.path.join(self.temp_dir, 'output.json')
    exit_code = collect_task.collect_task(
        collect_cmd, 'merge.py', build_props_json, None, task_output_dir,
        output_json)
    self.assertEqual(0, exit_code)

    # Should append correct --task-output-dir to args after '--'.
    self.assertEqual(
        [
            [
                'swarming.py',
                'positional0',
                '--swarming-arg0', '0',
                '--swarming-arg1', '1',
                'positional1',
                '--task-output-dir',
                task_output_dir,
            ],
            [
                sys.executable,
                'merge.py',
                '--build-properties', build_props_json,
                '-o', output_json,
            ]
        ],
        self.subprocess_calls)

  def test_task_output_dir_handling(self):
    collect_cmd = [
      'swarming.py',
      'positional0',
      '--swarming-arg0', '0',
      '--swarming-arg1', '1',
      'positional1',
    ]
    merge_script = os.path.join(
        RESOURCES_DIR, 'standard_isolated_script_merge.py')
    task_output_dir = os.path.join(self.temp_dir, 'task_output_dir')
    os.makedirs(task_output_dir)
    summary_json = os.path.join(task_output_dir, 'summary.json')
    with open(summary_json, 'w') as f:
      f.write('{}')

    shard0_output_dir = os.path.join(task_output_dir, '0')
    os.makedirs(shard0_output_dir)
    shard0_output_json = os.path.join(shard0_output_dir, 'output.json')
    with open(shard0_output_json, 'w') as f:
      f.write('{}')

    build_props_json = os.path.join(self.temp_dir, 'build_properties.json')
    output_json = os.path.join(self.temp_dir, 'output.json')
    exit_code = collect_task.collect_task(
        collect_cmd, merge_script, build_props_json, None, task_output_dir,
        output_json)

    self.assertEquals(0, exit_code)
    self.assertEquals(
        [
          [
            'swarming.py',
            'positional0',
            '--swarming-arg0', '0',
            '--swarming-arg1', '1',
            'positional1',
            '--task-output-dir', task_output_dir,
          ],
          [
            sys.executable,
            merge_script,
            '--build-properties', build_props_json,
            '--summary-json', summary_json,
            '-o', output_json,
            shard0_output_json
          ],
        ],
        self.subprocess_calls)

  def test_custom_merge(self):
    collect_cmd = [
      'swarming.py',
      'positional0',
      '--swarming-arg0', '0',
      '--swarming-arg1', '1',
      'positional1',
    ]
    merge_script = os.path.join(self.temp_dir, 'fake_custom_merge.py')
    task_output_dir = os.path.join(self.temp_dir, 'task_output_dir')
    os.makedirs(task_output_dir)

    build_props_json = os.path.join(self.temp_dir, 'build_properties.json')
    output_json = os.path.join(self.temp_dir, 'output.json')
    exit_code = collect_task.collect_task(
        collect_cmd, merge_script, build_props_json, None, task_output_dir,
        output_json)

    self.assertEquals(0, exit_code)
    self.assertEquals(
        [
          [
            'swarming.py',
            'positional0',
            '--swarming-arg0', '0',
            '--swarming-arg1', '1',
            'positional1',
            '--task-output-dir', task_output_dir,
          ],
          [
            sys.executable,
            merge_script,
            '--build-properties', build_props_json,
            '-o', output_json
          ],
        ],
        self.subprocess_calls)

  def test_custom_merge_with_args(self):
    collect_cmd = [
      'swarming.py',
      'positional0',
      '--swarming-arg0', '0',
      '--swarming-arg1', '1',
      'positional1',
    ]
    merge_script = os.path.join(self.temp_dir, 'fake_custom_merge.py')
    task_output_dir = os.path.join(self.temp_dir, 'task_output_dir')
    os.makedirs(task_output_dir)

    build_props = json.dumps({
      'sample_build_property': 'sample_value'
    })
    merge_args = json.dumps([
      '--merge-arg0', 'merge-arg0-value',
    ])

    output_json = os.path.join(self.temp_dir, 'output.json')
    exit_code = collect_task.collect_task(
        collect_cmd, merge_script, build_props, merge_args,
        task_output_dir, output_json)

    self.assertEquals(0, exit_code)
    self.assertEquals(
        [
          [
            'swarming.py',
            'positional0',
            '--swarming-arg0', '0',
            '--swarming-arg1', '1',
            'positional1',
            '--task-output-dir', task_output_dir,
          ],
          [
            sys.executable,
            merge_script,
            '--build-properties', build_props,
            '--merge-arg0', 'merge-arg0-value',
            '-o', output_json
          ],
        ],
        self.subprocess_calls)


if __name__ == '__main__':
  unittest.main()
