#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Source file for main_utils testcases."""


import unittest

import test_env  # pylint: disable=W0611,W0403

from buildbot.buildsubordinate import BuildSubordinate
from buildbot.process.properties import Properties
from main import main_utils
from main.autoreboot_buildsubordinate import AutoRebootBuildSubordinate

def remove_subordinate(subordinates, name):
  for i, s in enumerate(subordinates):
    if s.name == name:
      del(subordinates[i])
      break
  else:
    assert False, 'subordinate %s does not exist' % name


class MainUtilsTest(unittest.TestCase):

  def testPartition(self):
    partitions = main_utils.Partition([(1, 'a'),
                                         (2, 'b'),
                                         (3, 'c'),
                                         ], 2)
    self.assertEquals([['a', 'b'], ['c']], partitions)

  def testAutoSetupSubordinates(self):
    def B(name, subordinatenames, auto_reboot):
      return {
        'name': name,
        'subordinatenames': subordinatenames,
        'auto_reboot' : auto_reboot,
      }
    builders = [
      # Bot sharing two subordinates.
      B('B1', ['S1', 'S2'], True),
      B('B2', ['S3', 'S4'], False),
      # Subordinate sharing two bots.
      B('B3', ['S5'], True),
      B('B4', ['S5'], False),
      # Subordinate sharing two bots (inverse auto-reboot).
      B('B5', ['S6'], False),
      B('B6', ['S6'], True),
      # Two builders heterogeneously sharing one subordinate.
      B('B7', ['S7'], True),
      B('B8', ['S7', 'S8'], False),
    ]
    subordinates = dict(
      (subordinate.subordinatename, subordinate)
      for subordinate in main_utils.AutoSetupSubordinates(builders, 'pwd')
    )
    self.assertTrue(isinstance(subordinates['S1'], AutoRebootBuildSubordinate))
    self.assertTrue(isinstance(subordinates['S2'], AutoRebootBuildSubordinate))
    self.assertFalse(isinstance(subordinates['S3'], AutoRebootBuildSubordinate))
    self.assertFalse(isinstance(subordinates['S4'], AutoRebootBuildSubordinate))
    self.assertTrue(isinstance(subordinates['S5'], AutoRebootBuildSubordinate))
    self.assertTrue(isinstance(subordinates['S6'], AutoRebootBuildSubordinate))
    self.assertTrue(isinstance(subordinates['S7'], AutoRebootBuildSubordinate))
    self.assertFalse(isinstance(subordinates['S8'], AutoRebootBuildSubordinate))


class MockBuilder(object):
  def __init__(self, name):
    self.name = name

class MockSubordinate(object):
  def __init__(self, name, properties):
    self.properties = Properties()
    self.properties.update(properties, "BuildSubordinate")
    self.properties.setProperty("subordinatename", name, "BuildSubordinate")

class MockSubordinateBuilder(object):
  def __init__(self, name, properties):
    self.name = name
    self.subordinate = MockSubordinate(name, properties)

class PreferredBuilderNextSubordinateFuncTest(unittest.TestCase):
  def testNextSubordinate(self):
    builder1 = MockBuilder('builder1')
    builder2 = MockBuilder('builder2')
    builder3 = MockBuilder('builder3')

    subordinates = [
        MockSubordinateBuilder('subordinate1', {'preferred_builder': 'builder1'}),
        MockSubordinateBuilder('subordinate2', {'preferred_builder': 'builder2'}),
        MockSubordinateBuilder('subordinate3', {'preferred_builder': 'builder3'}),
    ]

    f = main_utils.PreferredBuilderNextSubordinateFunc()
    self.assertEqual('subordinate1', f(builder1, subordinates).name)
    self.assertEqual('subordinate2', f(builder2, subordinates).name)
    self.assertEqual('subordinate3', f(builder3, subordinates).name)

    remove_subordinate(subordinates, 'subordinate3')

    # When there is no subordinate that matches preferred_builder,
    # any subordinate builder might be chosen.
    self.assertTrue(f(builder3, subordinates).name in ['subordinate1', 'subordinate2'])

  def testNextSubordinateEmpty(self):
    builder = MockBuilder('builder')
    subordinates = []

    f = main_utils.PreferredBuilderNextSubordinateFunc()

    self.assertIsNone(f(builder, subordinates))

  def testNextSubordinateNG(self):
    builder1 = MockBuilder('builder1')
    builder2 = MockBuilder('builder2')
    builder3 = MockBuilder('builder3')

    subordinates = [
        MockSubordinateBuilder('s1', {'preferred_builder': 'builder1'}),
        MockSubordinateBuilder('s2', {'preferred_builder': 'builder2'}),
        MockSubordinateBuilder('s3', {'preferred_builder': 'builder3'}),
        MockSubordinateBuilder('s4', {'preferred_builder': 'builder1'}),
        MockSubordinateBuilder('s5', {'preferred_builder': 'builder2'}),
        MockSubordinateBuilder('s6', {'preferred_builder': 'builder3'}),
        # Fall-over pool with no preference.
        MockSubordinateBuilder('s7', {'preferred_builder': None}),
        MockSubordinateBuilder('s8', {'preferred_builder': None}),
    ]

    def f(builder, subordinates):
      # Call original method for code coverage only.
      main_utils.PreferredBuilderNextSubordinateFuncNG()(builder, subordinates)

      # Mock random.choice on function return for determinism and to check the
      # full choice range.
      mocked_func = main_utils.PreferredBuilderNextSubordinateFuncNG(choice=list)
      return set([s.name for s in mocked_func(builder, subordinates)])

    self.assertEqual(set(['s1', 's4']), f(builder1, subordinates))
    self.assertEqual(set(['s2', 's5']), f(builder2, subordinates))
    self.assertEqual(set(['s3', 's6']), f(builder3, subordinates))

    remove_subordinate(subordinates, 's3')

    # There's still a preferred subordinate left.
    self.assertEqual(set(['s6']), f(builder3, subordinates))

    remove_subordinate(subordinates, 's6')

    # No preferred subordinate. Subordinate will be choosen from fall-over pool (i.e.
    # subordinates with no preference).
    self.assertEqual(set(['s7', 's8']), f(builder3, subordinates))

    # We could also test the case where two subordinate sets are equal (e.g.
    # removing now 7 and 8), but that'd require making the most_common
    # method deterministic.

    remove_subordinate(subordinates, 's1')
    remove_subordinate(subordinates, 's7')
    remove_subordinate(subordinates, 's8')

    # Now only subordinates preferring builder2 have most capacity.
    self.assertEqual(set(['s2', 's5']), f(builder3, subordinates))

  def testNextSubordinateEmptyNG(self):
    builder = MockBuilder('builder')
    subordinates = []

    f = main_utils.PreferredBuilderNextSubordinateFuncNG(choice=list)

    self.assertIsNone(f(builder, subordinates))

if __name__ == '__main__':
  unittest.main()
