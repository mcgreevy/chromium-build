# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
]


def RunSteps(api):
  api.chromium.list_perf_tests(
      'sample-browser',
      4,
      'device-id')


def GenTests(api):
  yield api.test('basic')
