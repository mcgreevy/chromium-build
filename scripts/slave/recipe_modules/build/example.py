# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'build',
]

def RunSteps(api):
  assert api.build.subordinate_utils_args

  with api.build.gsutil_py_env():
    api.build.python(
        'runtest',
        api.build.package_repo_resource('scripts', 'subordinate', 'runtest.py'))


def GenTests(api):
  yield api.test('basic')
