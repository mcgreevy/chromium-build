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
      SingleBranchScheduler(name='webrtc_android_scheduler',
                            branch='main',
                            treeStableTimer=0,
                            builderNames=[
          'Android Archive',
          'Android (swarming)',
          'Android ASan (swarming)',
      ]),
  ])

  specs = [
    {'name': 'Android Archive', 'recipe': 'webrtc/android_archive'},
    {'name': 'Android (swarming)'},
    {'name': 'Android ASan (swarming)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run(spec.get('recipe', 'webrtc/standalone')),
        'notify_on_missing': True,
        'category': 'android',
        'subordinatebuilddir': spec.get('subordinatebuilddir', 'android'),
      } for spec in specs
  ])
