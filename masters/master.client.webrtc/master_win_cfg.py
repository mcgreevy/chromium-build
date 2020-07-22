# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from main.factory import remote_run_factory

import main_site_config
ActiveMain = main_site_config.WebRTC


def m_remote_run(recipe, **kwargs):
  return remote_run_factory.RemoteRunFactory(
      active_main=ActiveMain,
      repository='https://chromium.googlesource.com/chromium/tools/build.git',
      recipe=recipe,
      factory_properties={'path_config': 'kitchen'},
      **kwargs)


def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_windows_scheduler',
                            branch='main',
                            treeStableTimer=30,
                            builderNames=[
          'Win32 Debug',
          'Win32 Release',
          'Win64 Debug',
          'Win64 Release',
          'Win32 Release [large tests]',
          'Win32 Debug (Clang)',
          'Win32 Release (Clang)',
          'Win64 Debug (Clang)',
          'Win64 Release (Clang)',
          'Win32 ASan',
      ]),
  ])

  # 'subordinatebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple subordinate machines.
  specs = [
    {'name': 'Win32 Debug'},
    {'name': 'Win32 Release'},
    {'name': 'Win64 Debug'},
    {'name': 'Win64 Release'},
    {
      'name': 'Win32 Release [large tests]',
      'category': 'compile|baremetal|windows',
      'subordinatebuilddir': 'win_baremetal',
    },
    {'name': 'Win32 Debug (Clang)', 'subordinatebuilddir': 'win_clang'},
    {'name': 'Win32 Release (Clang)', 'subordinatebuilddir': 'win_clang'},
    {'name': 'Win64 Debug (Clang)', 'subordinatebuilddir': 'win_clang'},
    {'name': 'Win64 Release (Clang)', 'subordinatebuilddir': 'win_clang'},
    {'name': 'Win32 ASan', 'subordinatebuilddir': 'win_asan'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        # TODO(sergiyb): Remove the timeout below after all bots have synched
        # past Blink merge commit.
        'factory': m_remote_run('webrtc/standalone', timeout=3600),
        'notify_on_missing': True,
        'category': spec.get('category', 'compile|testers|windows'),
        'subordinatebuilddir': spec.get('subordinatebuilddir', 'win'),
      } for spec in specs
  ])
