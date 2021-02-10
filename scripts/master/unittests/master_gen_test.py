#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for scripts/main/main_gen.py."""

import os
import tempfile
import unittest


# This adjusts sys.path, so it must be imported before the other modules.
import test_env  # pylint: disable=W0403

from main import main_gen


SAMPLE_WATERFALL_PYL = """\
{
  "main_base_class": "_FakeMainBase",
  "main_port": 20999,
  "main_port_alt": 40999,
  "bot_port": 30999,
  "templates": ["templates"],

  "builders": {
    "Test Linux": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "scheduler": "test_repo",
      "bot_pools": ["main"],
      "botbuilddir": "test"
    },
    "Test Linux Timeouts": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "scheduler": "test_repo",
      "bot_pools": ["main"],
      "botbuilddir": "test",
      "builder_timeout_s": 7200,
      "no_output_timeout_s": 3600,
    },
    "Test Linux Remote Run": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "scheduler": "test_repo",
      "bot_pools": ["main"],
      "botbuilddir": "test",
      "use_remote_run": True,
    },
    "Test Linux Nightly": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_nightly_recipe",
      "scheduler": "nightly",
      "bot_pools": ["main"],
      "botbuilddir": "test",
      "category": "0nightly"
    }
  },

  "schedulers": {
    "nightly": {
      "type": "cron",
      "hour": 4,
      "minute": 15,
    },
    "test_repo": {
      "type": "git_poller",
      "git_repo_url": "https://chromium.googlesource.com/test/test.git",
    },
  },

  "bot_pools": {
    "main": {
      "bot_data": {
        "bits": 64,
        "os":  "linux",
        "version": "precise"
      },
      "bots": ["vm9999-m1"],
    },
  },
}
"""


SAMPLE_TRYSERVER_PYL = """\
{
  "main_base_class": "_FakeMainBase",
  "main_port": 20999,
  "main_port_alt": 40999,
  "bot_port": 30999,
  "buildbucket_bucket": "fake_bucket",
  "service_account_file": "fake_service_account",
  "templates": ["templates"],

  "builders": {
    "Test Linux": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "scheduler": None,
      "bot_pools": ["main"],
      "botbuilddir": "test"
    }
  },

  "schedulers": {},

  "bot_pools": {
    "main": {
      "bot_data": {
        "bits": 64,
        "os":  "linux",
        "version": "precise"
      },
      "bots": ["vm{9998..9999}-m1"],
    },
  },
}
"""

# This class fakes the base class from main_site_config.py.
class _FakeMainBase(object):
  in_production = False
  is_production_host = False


# This class fakes the actual main class in main_site_config.py.
class _FakeMain(_FakeMainBase):
  project_name = 'test'
  main_port = '20999'
  subordinate_port = '30999'
  main_port_alt = '40999'
  buildbot_url = 'https://build.chromium.org/p/test'
  buildbucket_bucket = None
  service_account_file = None


class PopulateBuildmainConfigTest(unittest.TestCase):
  def verify_timeouts(self, builder, expected_builder_timeout=None,
                      expected_no_output_timeout=2400):
    steps = builder['factory'].steps
    self.assertEqual(1, len(steps))
    step_dict = steps[0][1]
    self.assertEqual(step_dict['maxTime'], expected_builder_timeout)
    self.assertEqual(step_dict['timeout'], expected_no_output_timeout)

  def test_waterfall(self):
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(SAMPLE_WATERFALL_PYL)
      fp.close()

      c = {}
      main_gen.PopulateBuildmainConfig(c, fp.name, _FakeMain)
      c['builders'] = sorted(c['builders'])

      self.assertEqual(len(c['builders']), 4)
      self.assertEqual(c['builders'][0]['name'], 'Test Linux')
      self.verify_timeouts(c['builders'][0])

      self.assertEqual(c['builders'][1]['name'], 'Test Linux Timeouts')
      self.verify_timeouts(c['builders'][1], 7200, 3600)

      self.assertEqual(c['builders'][2]['name'], 'Test Linux Remote Run')
      self.verify_timeouts(c['builders'][2])

      self.assertEqual(len(c['change_source']), 1)
      self.assertEqual(len(c['schedulers']), 2)
    finally:
      os.remove(fp.name)

  def test_tryservers(self):
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(SAMPLE_TRYSERVER_PYL)
      fp.close()

      c = {}
      main_gen.PopulateBuildmainConfig(c, fp.name, _FakeMain)

      self.assertEqual(len(c['builders']), 1)
      self.assertEqual(c['builders'][0]['name'], 'Test Linux')
      self.assertEqual(set(s.subordinatename for s in c['subordinates']),
                       set(['vm9998-m1', 'vm9999-m1']))

      self.assertEqual(len(c['change_source']), 0)
      self.assertEqual(len(c['schedulers']), 0)
    finally:
      os.remove(fp.name)


# TODO: Remove this code once all of the builders.pyl formats have
# been upgraded to the new nomenclature.

OLD_TRYSERVER_PYL = """\
{
  "main_base_class": "_FakeMainBase",
  "main_port": 20999,
  "main_port_alt": 40999,
  "subordinate_port": 30999,
  "buildbucket_bucket": "fake_bucket",
  "service_account_file": "fake_service_account",
  "templates": ["templates"],

  "builders": {
    "Test Linux": {
      "properties": {
        "config": "Release"
      },
      "recipe": "test_recipe",
      "scheduler": None,
      "subordinate_pools": ["main"],
      "subordinatebuilddir": "test"
    }
  },

  "schedulers": {},

  "subordinate_pools": {
    "main": {
      "subordinate_data": {
        "bits": 64,
        "os":  "linux",
        "version": "precise"
      },
      "subordinates": ["vm9999-m1"],
    },
  },
}
"""

class OldNomenclature(unittest.TestCase):
  def test_old_nomenclature(self):
    try:
      fp = tempfile.NamedTemporaryFile(delete=False)
      fp.write(OLD_TRYSERVER_PYL)
      fp.close()

      c = {}
      main_gen.PopulateBuildmainConfig(c, fp.name, _FakeMain)

      self.assertEqual(len(c['builders']), 1)
      self.assertEqual(c['builders'][0]['name'], 'Test Linux')

      self.assertEqual(len(c['change_source']), 0)
      self.assertEqual(len(c['schedulers']), 0)
    finally:
      os.remove(fp.name)


if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()
