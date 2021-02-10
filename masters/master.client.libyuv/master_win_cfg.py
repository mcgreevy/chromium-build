# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from main.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='libyuv_windows_scheduler',
                            branch='main',
                            treeStableTimer=0,
                            builderNames=[
          'Win32 Debug',
          'Win32 Release',
          'Win64 Debug',
          'Win64 Release',
          'Win32 Debug (Clang)',
          'Win32 Release (Clang)',
          'Win64 Debug (Clang)',
          'Win64 Release (Clang)',
      ]),
  ])

  specs = [
    {'name': 'Win32 Debug', 'subordinatebuilddir': 'win'},
    {'name': 'Win32 Release', 'subordinatebuilddir': 'win'},
    {'name': 'Win64 Debug', 'subordinatebuilddir': 'win'},
    {'name': 'Win64 Release', 'subordinatebuilddir': 'win'},
    {'name': 'Win32 Debug (Clang)', 'subordinatebuilddir': 'win_clang'},
    {'name': 'Win32 Release (Clang)', 'subordinatebuilddir': 'win_clang'},
    {'name': 'Win64 Debug (Clang)', 'subordinatebuilddir': 'win_clang'},
    {'name': 'Win64 Release (Clang)', 'subordinatebuilddir': 'win_clang'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('libyuv/libyuv'),
        'notify_on_missing': True,
        'category': 'win',
        'subordinatebuilddir': spec['subordinatebuilddir'],
      } for spec in specs
  ])
