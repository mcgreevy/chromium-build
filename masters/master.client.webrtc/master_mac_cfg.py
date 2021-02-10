# Copyright (c) 2012 The Chromium Authors. All rights reserved.
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
      SingleBranchScheduler(name='webrtc_mac_scheduler',
                            branch='main',
                            treeStableTimer=30,
                            builderNames=[
          'Mac64 Debug',
          'Mac64 Release',
          'Mac64 Release [large tests]',
          'Mac Asan',
          'iOS32 Debug',
          'iOS32 Release',
          'iOS64 Debug',
          'iOS64 Release',
          'iOS32 Sim Debug (iOS 9.0)',
          'iOS64 Sim Debug (iOS 9.0)',
          'iOS64 Sim Debug (iOS 10.0)',
          'iOS API Framework Builder',
      ]),
  ])

  # 'subordinatebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple subordinate machines.
  specs = [
    {'name': 'Mac64 Debug', 'subordinatebuilddir': 'mac64'},
    {'name': 'Mac64 Release', 'subordinatebuilddir': 'mac64'},
    {
      'name': 'Mac64 Release [large tests]',
      'category': 'compile|baremetal',
      'subordinatebuilddir': 'mac_baremetal',
    },
    {'name': 'Mac Asan', 'subordinatebuilddir': 'mac_asan'},
    {
      'name': 'iOS32 Debug',
      'subordinatebuilddir': 'mac32',
      'recipe': 'webrtc/ios',
    },
    {
      'name': 'iOS32 Release',
      'subordinatebuilddir': 'mac32',
      'recipe': 'webrtc/ios',
    },
    {
      'name': 'iOS64 Debug',
      'subordinatebuilddir': 'mac64',
      'recipe': 'webrtc/ios',
    },
    {
      'name': 'iOS64 Release',
      'subordinatebuilddir': 'mac64',
      'recipe': 'webrtc/ios',
    },
    {
      'name': 'iOS32 Sim Debug (iOS 9.0)',
      'subordinatebuilddir': 'mac32',
      'recipe': 'webrtc/ios',
    },
    {
      'name': 'iOS64 Sim Debug (iOS 9.0)',
      'subordinatebuilddir': 'mac64',
      'recipe': 'webrtc/ios',
    },
    {
      'name': 'iOS64 Sim Debug (iOS 10.0)',
      'subordinatebuilddir': 'mac64',
      'recipe': 'webrtc/ios',
    },
    {
      'name': 'iOS API Framework Builder',
      'subordinatebuilddir': 'mac64',
      'recipe': 'webrtc/ios_api_framework',
    },
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        # remote_run is not working for the webrtc/ios recipe: crbug.com/637666.
        'factory': m_annotator.BaseFactory(spec['recipe'])
                   if 'recipe' in spec and spec['recipe'] == 'webrtc/ios'
                   else m_remote_run(spec.get('recipe', 'webrtc/standalone')),
        'notify_on_missing': True,
        'category': spec.get('category', 'compile|testers'),
        'subordinatebuilddir': spec['subordinatebuilddir'],
      } for spec in specs
  ])
