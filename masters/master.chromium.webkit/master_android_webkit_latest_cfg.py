# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from main import main_config
from main.factory import remote_run_factory

import main_site_config

ActiveMain = main_site_config.ChromiumWebkit

defaults = {}

helper = main_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_main=ActiveMain,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)


################################################################################
## Release
################################################################################

defaults['category'] = 'layout'

#
# Android Rel Builder
#
B('Android Builder', 'f_android_rel', scheduler='global_scheduler')
F('f_android_rel', m_remote_run('chromium'))

B('WebKit Android (Nexus4)', 'f_webkit_android_tests')
F('f_webkit_android_tests', m_remote_run('chromium'))

def Update(_config, _active_main, c):
  return helper.Update(c)
