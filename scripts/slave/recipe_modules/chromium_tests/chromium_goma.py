# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from . import steps

SPEC = {
 'builders': {
   'Chromium Linux Goma Staging': {
     'chromium_config': 'chromium',
     'chromium_apply_config': ['goma_staging', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'compile_targets': [ 'chromium_builder_tests' ],
     'tests': steps.GOMA_TESTS,
     'goma_staging': True,
     'testing': {
       'platform': 'linux',
     },
   },
   'Chromium Mac Goma Staging': {
     'chromium_config': 'chromium',
     'chromium_apply_config': ['goma_staging', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'compile_targets': [ 'chromium_builder_tests' ],
     'tests': steps.GOMA_TESTS,
     'goma_staging': True,
     'testing': {
       'platform': 'mac',
     },
   },
   'CrWinGomaStaging': {
     'chromium_config': 'chromium',
     'chromium_apply_config': ['goma_staging', 'clobber', 'mb'],
     'gclient_config': 'chromium',
     'chromium_config_kwargs': {
       'BUILD_CONFIG': 'Release',
       'TARGET_BITS': 64,
     },
     'compile_targets': [ 'chromium_builder_tests' ],
     'tests': steps.GOMA_TESTS,
     'goma_staging': True,
     'testing': {
       'platform': 'win',
     },
   },
 },
}
