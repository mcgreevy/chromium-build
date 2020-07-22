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
      SingleBranchScheduler(name='webrtc_mac_scheduler',
                            branch='main',
                            treeStableTimer=0,
                            builderNames=[
                                'Mac (swarming)',
                            ]),
  ])

  specs = [
    {'name': 'Mac (swarming)', 'subordinatebuilddir': 'mac_swarming'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_remote_run(spec.get('recipe', 'webrtc/standalone')),
        'notify_on_missing': True,
        'category': 'mac',
        'subordinatebuilddir': spec['subordinatebuilddir'],
      } for spec in specs
  ])
