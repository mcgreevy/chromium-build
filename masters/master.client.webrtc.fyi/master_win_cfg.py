# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from main.factory import remote_run_factory

import main_site_config
ActiveMain = main_site_config.WebRTCFYI


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
                            treeStableTimer=0,
                            builderNames=[
                                'Win (swarming)',
                                'Win64 Debug (Win8)',
                                'Win64 Debug (Win10)',
                            ]),
  ])

  specs = [
    {
      'name': 'Win (swarming)',
      'subordinatebuilddir': 'win_swarming',
    },
    {
      'name': 'Win64 Debug (Win8)',
      'subordinatebuilddir': 'win',
    },
    {
      'name': 'Win64 Debug (Win10)',
      'subordinatebuilddir': 'win',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'win',
        'subordinatebuilddir': spec['subordinatebuilddir'],
      } for spec in specs
  ])
