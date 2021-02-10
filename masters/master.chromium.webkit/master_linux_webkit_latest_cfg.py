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

#
# Linux Rel Builder/Tester
#

B('WebKit Linux Trusty', 'f_webkit_linux_rel', scheduler='global_scheduler')
F('f_webkit_linux_rel', m_remote_run('chromium'))

B('WebKit Linux Trusty ASAN', 'f_webkit_linux_rel_asan',
    scheduler='global_scheduler', auto_reboot=True)
F('f_webkit_linux_rel_asan', m_remote_run('chromium'))

B('WebKit Linux Trusty MSAN', 'f_webkit_linux_rel_msan',
    scheduler='global_scheduler', auto_reboot=True)
F('f_webkit_linux_rel_msan', m_remote_run('chromium'))

B('WebKit Linux Trusty Leak', 'f_webkit_linux_leak_rel',
    scheduler='global_scheduler', category='layout')
F('f_webkit_linux_leak_rel', m_remote_run('chromium'))


################################################################################
## Debug
################################################################################

#
# Linux Dbg Webkit builders/testers
#

B('WebKit Linux Trusty (dbg)', 'f_webkit_dbg_tests',
    scheduler='global_scheduler', auto_reboot=True)
F('f_webkit_dbg_tests', m_remote_run('chromium'))


def Update(_config, _active_main, c):
  return helper.Update(c)
