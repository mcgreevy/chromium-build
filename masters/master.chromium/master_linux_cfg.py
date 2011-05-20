# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = '4linux'

#
# Main release scheduler for src/
#
S('linux_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel builder
#
T('linux_rel_trigger')

#
# Linux Rel Builder
#
B('Linux Builder x64', 'rel', 'compile', 'linux_rel')
F('rel', linux().ChromiumFactory(
    slave_type='NASBuilder',
    options=['--compiler=goma', 'app_unittests', 'browser_tests',
             'googleurl_unittests', 'gpu_unittests', 'ipc_tests',
             'media_unittests', 'memory_test', 'page_cycler_tests',
             'printing_unittests', 'remoting_unittests',
             'startup_tests', 'sync_unit_tests', 'ui_tests', 'unit_tests',
             'url_fetch_test', 'base_unittests', 'net_unittests',
             'gfx_unittests', 'safe_browsing_tests', 'sync_integration_tests',
             'crypto_unittests'],
    factory_properties={'trigger': 'linux_rel_trigger'}))

#
# Linux Rel testers
#
B('Linux Tests x64', 'rel_unit', 'testers', 'linux_rel_trigger',
  auto_reboot=True)
F('rel_unit', linux().ChromiumFactory(
    slave_type='NASTester',
    tests=['check_deps', 'googleurl', 'media', 'printing', 'remoting', 'ui',
           'browser_tests', 'unit', 'gpu', 'base', 'net', 'safe_browsing',
           'crypto'],
    factory_properties={'generate_gtest_json': True}))

B('Linux Sync', 'rel_sync', 'testers', 'linux_rel_trigger', auto_reboot=True)
F('rel_sync', linux().ChromiumFactory(
    slave_type='NASTester',
    tests=['sync_integration'],
    factory_properties={'generate_gtest_json': True}))


################################################################################
## Debug
################################################################################

#
# Main debug scheduler for src/
#
S('linux_dbg', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builders
#
T('linux_dbg_trigger')
T('linux_dbg_cmp_trigger')

#
# Linux Dbg Builder
#
B('Linux Builder (dbg)', 'dbg', 'compile', 'linux_dbg')
F('dbg', linux().ChromiumFactory(
    slave_type='NASBuilder',
    target='Debug',
    options=['--compiler=goma', 'app_unittests', 'browser_tests',
             'googleurl_unittests', 'gpu_unittests', 'interactive_ui_tests',
             'ipc_tests', 'media_unittests',
             'nacl_ui_tests', 'nacl_sandbox_tests',
             'printing_unittests', 'remoting_unittests', 'sync_unit_tests',
             'ui_tests', 'unit_tests',
             'base_unittests', 'net_unittests', 'crypto_unittests',
             'gfx_unittests', 'plugin_tests', 'safe_browsing_tests'],
    factory_properties={'trigger': 'linux_dbg_trigger',
                        'gclient_env': {'GYP_DEFINES':'target_arch=ia32'},}))

#
# Linux Dbg Unit testers
#

B('Linux Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'linux_dbg_trigger',
  auto_reboot=True)
F('dbg_unit_1', linux().ChromiumFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['check_deps', 'net', 'browser_tests'],
    factory_properties={'generate_gtest_json': True}))

B('Linux Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'linux_dbg_trigger',
  auto_reboot=True)
F('dbg_unit_2', linux().ChromiumFactory(
    slave_type='NASTester',
    target='Debug',
    tests=['unit', 'nacl_ui', 'nacl_integration', 'nacl_sandbox',
           'gpu', 'interactive_ui',
           'ui', 'plugin', 'googleurl', 'media', 'printing', 'remoting',
           'base', 'safe_browsing', 'crypto'],
    factory_properties={'generate_gtest_json': True}))

#
# Linux Dbg Component Builder
#
B('Linux Builder (dbg)(cmp)', 'dbg_cmp', 'compile', 'linux_dbg')
F('dbg_cmp', linux().ChromiumFactory(
    slave_type='NASBuilder',
    target='Debug',
    options=['--build-tool=make'],
    factory_properties={
        'gclient_env': {'GYP_DEFINES':'component=shared_library'},
        'trigger': 'linux_dbg_cmp_trigger'}))

#
# Linux Dbg Component Unit testers
#

B('Linux Tests (dbg)(cmp)', 'dbg_cmp_unit', 'testers',
  'linux_dbg_cmp_trigger', auto_reboot=True)
F('dbg_cmp_unit', linux().ChromiumFactory(
    target='Debug',
    slave_type='NASTester',
    tests=['base', 'browser_tests', 'check_deps', 'googleurl', 'media', 'net',
           'printing', 'remoting', 'sizes', 'test_shell', 'ui', 'unit',
           'crypto'],
    factory_properties={'generate_gtest_json': True}))

#
# Linux Dbg Clang bot
#

B('Linux Clang (dbg)', 'dbg_linux_clang', 'compile', 'linux_dbg')
F('dbg_linux_clang', linux().ChromiumFactory(
    target='Debug',
    options=['--build-tool=make', '--compiler=clang'],
    tests=['base', 'gfx', 'unit', 'crypto'],
    factory_properties={
        'gclient_env': {
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1 fastbuild=1'
    }}))


def Update(config, active_master, c):
  return helper.Update(c)
