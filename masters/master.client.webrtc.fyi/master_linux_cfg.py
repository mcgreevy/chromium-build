# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Periodic
from buildbot.schedulers.basic import SingleBranchScheduler

from main.factory import annotator_factory
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


m_annotator = annotator_factory.AnnotatorFactory()


def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_linux_scheduler',
                            branch='main',
                            treeStableTimer=0,
                            builderNames=[
                                'Linux (swarming)',
                                'Linux32 Debug (ARM)',
                                'Linux64 GCC',
      ]),
      # Run WebRTC DEPS roller every 3 hours.
      Periodic(
          name='webrtc_deps',
          periodicBuildTimer=3*60*60,
          branch=None,
          builderNames=['Auto-roll - WebRTC DEPS'],
      ),
  ])

  specs = [
    {'name': 'Linux (swarming)', 'subordinatebuilddir': 'linux_swarming'},
    {'name': 'Linux32 Debug (ARM)', 'subordinatebuilddir': 'linux_arm'},
    {'name': 'Linux64 GCC', 'subordinatebuilddir': 'linux_gcc'},
    {
      'name': 'Auto-roll - WebRTC DEPS',
      'recipe': 'webrtc/auto_roll_webrtc_deps',
      'subordinatebuilddir': 'linux_autoroll',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(spec['recipe'])
                   if 'recipe' in spec
                   else m_remote_run('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'linux',
        'subordinatebuilddir': spec['subordinatebuilddir'],
        'auto_reboot': False,
      } for spec in specs
  ])
