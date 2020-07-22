# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from main.factory import annotator_factory
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


m_annotator = annotator_factory.AnnotatorFactory()


def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_android_scheduler',
                            branch='main',
                            treeStableTimer=30,
                            builderNames=[
          'Android32 (M Nexus5X)(dbg)',
          'Android32 (M Nexus5X)',
          'Android64 (M Nexus5X)(dbg)',
          'Android64 (M Nexus5X)',
          'Android32 Builder x86',
          'Android32 Builder x86 (dbg)',
          'Android32 Builder MIPS (dbg)',
          'Android32 Clang (dbg)',
          'Android64 Builder x64 (dbg)',
          'Android32 (more configs)',
      ]),
  ])

  # 'subordinatebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple subordinate machines.
  specs = [
    {'name': 'Android32 (M Nexus5X)(dbg)', 'subordinatebuilddir': 'android_arm32'},
    {'name': 'Android32 (M Nexus5X)', 'subordinatebuilddir': 'android_arm32'},
    {'name': 'Android64 (M Nexus5X)(dbg)', 'subordinatebuilddir': 'android_arm64'},
    {'name': 'Android64 (M Nexus5X)', 'subordinatebuilddir': 'android_arm64'},
    {'name': 'Android32 Builder x86', 'subordinatebuilddir': 'android_x86'},
    {'name': 'Android32 Builder x86 (dbg)', 'subordinatebuilddir': 'android_x86'},
    {'name': 'Android32 Builder MIPS (dbg)', 'subordinatebuilddir': 'android_mips'},
    {'name': 'Android32 Clang (dbg)', 'subordinatebuilddir': 'android_clang'},
    {'name': 'Android64 Builder x64 (dbg)', 'subordinatebuilddir': 'android_x64'},
    {
      'name': 'Android32 (more configs)',
      'recipe': 'webrtc/more_configs',
      'subordinatebuilddir': 'android',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(spec['recipe'])
                   if 'recipe' in spec
                   else m_remote_run('webrtc/standalone'),
        'notify_on_missing': True,
        'category': 'android',
        'subordinatebuilddir': spec.get('subordinatebuilddir', 'android'),
      } for spec in specs
  ])
