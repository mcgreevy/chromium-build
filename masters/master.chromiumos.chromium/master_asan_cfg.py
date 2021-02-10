# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from main import main_config
from main.factory import annotator_factory, chromeos_factory

from buildbot.schedulers.basic import SingleBranchScheduler as Scheduler

def Builder(factory_obj, board):
  config = '%s-tot-asan-informational' % (board,)
  builder = {
      'name': config,
      'builddir': config,
      'category': '4chromeos asan',
      'factory': chromeos_factory.ChromiteRecipeFactory(
          factory_obj, 'cros/cbuildbot'),
      'gatekeeper': 'crosasantest',
      'scheduler': 'chromium_src_asan',
      'notify_on_missing': True,
      'properties': {
          'cbb_config': config,
      },
  }
  return builder


def Update(_config, active_main, c):
  factory_obj = annotator_factory.AnnotatorFactory(
      active_main=active_main)

  builders = [
      Builder(factory_obj, 'amd64-generic'),
  ]

  c['schedulers'] += [
      Scheduler(name='chromium_src_asan',
                branch='main',
                treeStableTimer=60,
                builderNames=[b['name'] for b in builders],
      ),
  ]
  c['builders'] += builders
