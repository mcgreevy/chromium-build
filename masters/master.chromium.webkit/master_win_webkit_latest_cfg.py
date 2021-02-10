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

defaults['category'] = 'layout'

################################################################################
## Release
################################################################################

# Archive location
rel_archive = main_config.GetGSUtilUrl('chromium-build-transfer',
                                         'WebKit Win Builder')

#
# Win Rel Builder
#
B('WebKit Win Builder', 'f_webkit_win_rel',
  scheduler='global_scheduler', builddir='webkit-win-latest-rel',
  auto_reboot=True)
F('f_webkit_win_rel', m_remote_run('chromium'))

#
# Win Rel WebKit testers
#
B('WebKit Win7', 'f_webkit_rel_tests')
B('WebKit Win10', 'f_webkit_rel_tests')
F('f_webkit_rel_tests', m_remote_run('chromium'))

#
# Win x64 Rel Builder (note: currently no x64 testers)
#
B('WebKit Win x64 Builder', 'f_webkit_win_rel_x64',
  scheduler='global_scheduler', builddir='webkit-win-latest-rel-x64',
  auto_reboot=True)
F('f_webkit_win_rel_x64', m_remote_run('chromium'))


################################################################################
## Debug
################################################################################

#
# Win Dbg Builder
#
B('WebKit Win Builder (dbg)', 'f_webkit_win_dbg', scheduler='global_scheduler',
  builddir='webkit-win-latest-dbg', auto_reboot=True)
F('f_webkit_win_dbg', m_remote_run('chromium'))

#
# Win Dbg WebKit testers
#
B('WebKit Win7 (dbg)', 'f_webkit_dbg_tests')
F('f_webkit_dbg_tests', m_remote_run('chromium'))

#
# Win x64 Dbg Builder (note: currently no x64 testers)
#
B('WebKit Win x64 Builder (dbg)', 'f_webkit_win_dbg_x64',
  scheduler='global_scheduler', builddir='webkit-win-latest-dbg-x64',
  auto_reboot=True)
F('f_webkit_win_dbg_x64', m_remote_run('chromium'))

def Update(_config, _active_main, c):
  return helper.Update(c)
