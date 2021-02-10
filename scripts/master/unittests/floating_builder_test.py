#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Source file for floating builder testcases."""

import calendar
import datetime
import itertools
import os
import time
import unittest

import test_env  # pylint: disable=W0611,W0403

import mock

from main import floating_builder as fb


def _to_timestamp(dt):
  # Calculate the offset between local timezone and UTC.
  current_time = time.mktime(dt.timetuple())
  offset = (datetime.datetime.fromtimestamp(current_time) -
            datetime.datetime.utcfromtimestamp(current_time))

  return calendar.timegm((dt - offset).timetuple())


class _FakeSubordinateStatus(object):
  def __init__(self, name):
    self.name = name
    self.connect_times = []
    self.last_message_received = None

  def lastMessageReceived(self):
    return self.last_message_received


class _FakeSubordinate(object):
  def __init__(self, subordinatename):
    self.subordinatename = subordinatename
    self.subordinate_status = None
    self.offline = False

  def _set_last_seen(self, now, **kwargs):
    td = datetime.timedelta(**kwargs)
    self.subordinate_status = _FakeSubordinateStatus(self.subordinatename)
    self.subordinate_status.last_message_received = _to_timestamp(now + td)

  def __str__(self):
    return self.subordinatename


class _FakeBuilder(object):

  def __init__(self, name, subordinates):
    self.name = name
    self._all_subordinates = subordinates

    self.botmain = mock.MagicMock()
    self.builder_status = mock.MagicMock()
    self.builder_status.getSubordinates.side_effect = lambda: [
        s.subordinate_status for s in self._all_subordinates
        if s.subordinate_status]

    self._online_subordinates = ()
    self._busy_subordinates = ()

  def __repr__(self):
    return self.name

  @property
  def subordinates(self):
    return [_FakeSubordinateBuilder(s, self)
            for s in self._all_subordinates
            if s.subordinatename in self._online_subordinates]

  @property
  def subordinatebuilders(self):
    """Returns the list of subordinatebuilders that would be handed to
    NextSubordinateFunc.

    This is the set of subordinates that are available for scheduling. We derive
    this by returning all subordinates that are both online and not busy.
    """
    return self._get_subordinate_builders(lambda s:
      s.subordinatename in self._online_subordinates and
      s.subordinatename not in self._busy_subordinates)

  def _get_subordinate_builders(self, fn):
    return [_FakeSubordinateBuilder(subordinate, self)
            for subordinate in self._all_subordinates
            if fn(subordinate)]

  def set_online_subordinates(self, *subordinatenames):
    self._online_subordinates = set(subordinatenames)

  def set_busy_subordinates(self, *subordinatenames):
    self._busy_subordinates = set(subordinatenames)


class _FakeSubordinateBuilder(object):

  def __init__(self, subordinate, builder):
    self.subordinate = subordinate
    self.builder = builder

  def __repr__(self):
    return '{%s/%s}' % (self.builder.name, self.subordinate.subordinatename)


class FloatingBuilderTest(unittest.TestCase):

  def setUp(self):
    self._mocks = (
      mock.patch('main.floating_builder._get_now'),
      mock.patch('main.floating_builder.PokeBuilderTimer.reset'),
    )
    for patcher in self._mocks:
      patcher.start()

    # Mock current date/time.
    self.now = datetime.datetime(2016, 1, 1, 8, 0, 0) # 1/1/2016 @8:00
    fb._get_now.side_effect = lambda: self.now

    # Mock PokeBuilderTimer to record when the poke builder was set, but not
    # actually schedule any reactor magic.
    self.poke_delta = None
    def record_poke_delta(delta):
      self.poke_delta = delta
    fb.PokeBuilderTimer.reset.side_effect = record_poke_delta

    self._subordinates = dict((s, _FakeSubordinate(s)) for s in (
        'primary-a', 'primary-b', 'floating-a', 'floating-b',
    ))

    self.builder = _FakeBuilder(
        'Test Builder',
        [s[1] for s in sorted(self._subordinates.iteritems())],
    )

  def tearDown(self):
    for patcher in reversed(self._mocks):
      patcher.stop()

  def testJustStartedNoPrimariesOnlineWaits(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSubordinateFunc(datetime.timedelta(seconds=10))

    self.builder.set_online_subordinates('floating-a', 'floating-b')

    nsb = fnsf(self.builder, self.builder.subordinatebuilders)
    self.assertIsNone(nsb)
    self.assertEqual(self.poke_delta, datetime.timedelta(seconds=10))

    self.now += datetime.timedelta(seconds=11)
    nsb = fnsf(self.builder, self.builder.subordinatebuilders)
    self.assertIsNotNone(nsb)
    self.assertEqual(nsb.subordinate.subordinatename, 'floating-a')

  def testPrimaryBuilderIsSelectedWhenAvailable(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSubordinateFunc(datetime.timedelta(seconds=10))

    self.builder.set_online_subordinates('primary-a', 'floating-a', 'floating-b')

    nsb = fnsf(self.builder, self.builder.subordinatebuilders)
    self.assertIsNotNone(nsb)
    self.assertEqual(nsb.subordinate.subordinatename, 'primary-a')

  def testPrimaryBuilderIsSelectedWhenOneIsAvailableAndOneIsBusy(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a', 'primary-b')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSubordinateFunc(datetime.timedelta(seconds=10))

    self.builder.set_online_subordinates('primary-a', 'primary-b', 'floating-a',
                                   'floating-b')
    self.builder.set_busy_subordinates('primary-a')

    nsb = fnsf(self.builder, self.builder.subordinatebuilders)
    self.assertIsNotNone(nsb)
    self.assertEqual(nsb.subordinate.subordinatename, 'primary-b')

  def testNoBuilderIsSelectedWhenPrimariesAreOfflineWithinGrace(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a', 'primary-b')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSubordinateFunc(datetime.timedelta(seconds=10))

    self.now += datetime.timedelta(seconds=30)
    self.builder.set_online_subordinates('floating-a')
    self._subordinates['primary-b']._set_last_seen(self.now, seconds=-1)

    nsb = fnsf(self.builder, self.builder.subordinatebuilders)
    self.assertIsNone(nsb)
    self.assertEqual(self.poke_delta, datetime.timedelta(seconds=9))

  def testFloatingBuilderIsSelectedWhenPrimariesAreOfflineForAWhile(self):
    fs = fb.FloatingSet()
    fs.AddPrimary('primary-a', 'primary-b')
    fs.AddFloating('floating-a', 'floating-b')
    fnsf = fs.NextSubordinateFunc(datetime.timedelta(seconds=10))

    self.now += datetime.timedelta(seconds=30)
    self.builder.set_online_subordinates('floating-a')

    nsb = fnsf(self.builder, self.builder.subordinatebuilders)
    self.assertIsNotNone(nsb)
    self.assertEqual(nsb.subordinate.subordinatename, 'floating-a')


if __name__ == '__main__':
  unittest.main()
