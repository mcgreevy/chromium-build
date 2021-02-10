#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Starts run_subordinate and verify if it starts successfully.
"""

import mock
import os
import re
import runpy
import subprocess
import sys
import unittest


RUN_SLAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.append(RUN_SLAVE_PATH)

import run_subordinate

# import twisted to mock run()
_, tw_ver = run_subordinate.GetThirdPartyVersions(None)
sys.path.append(os.path.join(RUN_SLAVE_PATH, 'third_party', tw_ver))
import twisted.scripts.twistd


class ExitInvoked(Exception):
  # Raises when a mocked sys.exit() is invoked.
  # With mocking sys.exit() with this exception, the execution flow doesn't
  # continue after sys.exit(), but interrupted and the control is passed back to
  # a unit test.
  pass


def _GetCallArgumentFromMock(mock_call, position, keyword=None):
  args, kwargs = mock_call.call_args
  return kwargs[keyword] if keyword and keyword in kwargs else args[position]


class RunSubordinateTest(unittest.TestCase):
  @mock.patch('subprocess.call')
  @mock.patch('subprocess.Popen')
  @mock.patch('sys.exit', mock.Mock(side_effect=ExitInvoked))
  def test_run_subordinate_restart_after_gclient_sync(self, popen_call,
                                                subprocess_call):
    """Tests if run_subordinate restarts itself after gclient sync."""
    with self.assertRaises(ExitInvoked):
      runpy.run_module("run_subordinate", run_name="__main__", alter_sys=True)

    # verify that gclient sync has been executed
    self.assertTrue(subprocess_call.called)
    call_cmd_args = _GetCallArgumentFromMock(subprocess_call, 0, 'args')
    self.assertEqual(call_cmd_args[0], run_subordinate.GetGClientPath())
    self.assertEqual(call_cmd_args[1], 'sync')

    # verify that run_subordinate was re-executed by Popen() with --no-gclient-sync
    run_subordinate_py_path = re.sub(
        r'pyc$', 'py', os.path.abspath(run_subordinate.__file__))

    popen_cmd_args = _GetCallArgumentFromMock(popen_call, 0, 'args')

    # run_subordinate.py should be placed either at the beinning of the args
    # after the path python executable
    # : i.e., python run_subordinate.py --foo, or run_subordinate.py --foo
    self.assertIn(run_subordinate_py_path, popen_cmd_args[:2])
    self.assertIn('--no-gclient-sync', popen_cmd_args[1:])

  @mock.patch('subprocess.call')
  @mock.patch('subprocess.check_call')
  @mock.patch('subprocess.check_output')
  @mock.patch('twisted.scripts.twistd.run')
  @mock.patch('sys.argv', [run_subordinate.__file__, '--no-gclient-sync'])
  def test_run_subordinate_with_no_gclient_sync(self, twistd_run,
                                          subprocess_check_output,
                                          subprocess_check_call,
                                          subprocess_call):
    """Tests if twistd.run() gets invoked when --no-gclient-sync is given."""
    os.environ['TESTING_MASTER'] = 'Main1'
    os.environ['TESTING_SLAVE'] = 'Subordinate1'
    runpy.run_module("run_subordinate", run_name="__main__", alter_sys=True)

    gclient_path = run_subordinate.GetGClientPath()
    for mock_call in (subprocess_call, subprocess_check_call,
                      subprocess_check_output):
      if mock_call.called:
        cmd_args = _GetCallArgumentFromMock(mock_call, 0, 'args')

        # verify that gclient with sync option has not been called within
        # run_subordinate.
        if gclient_path == cmd_args[0]:
          self.assertNotEqual(cmd_args[1], 'sync')

    self.assertTrue(twistd_run.called)


if __name__ == '__main__':
  unittest.main()
