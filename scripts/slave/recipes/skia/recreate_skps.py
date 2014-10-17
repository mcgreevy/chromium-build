# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Recipe for the Skia RecreateSKPs Bot."""


from common.skia import global_constants


DEPS = [
  'gclient',
  'path',
  'python',
  'raw_io',
  'step',
]


def GenSteps(api):
  # Check out Chrome.
  gclient_cfg = api.gclient.make_config()
  src = gclient_cfg.solutions.add()
  src.name = 'src'
  src.url = 'https://chromium.googlesource.com/chromium/src.git'
  skia = gclient_cfg.solutions.add()
  skia.name = 'skia'
  skia.url = global_constants.SKIA_REPO
  gclient_cfg.got_revision_mapping['skia'] = 'got_revision'
  api.gclient.checkout(gclient_config=gclient_cfg)
  api.gclient.runhooks()

  # Build Chrome.
  api.step('Build Chrome',
           ['ninja', '-C', 'out/Debug', 'chrome'],
           cwd=api.path['checkout'])

  # Capture the SKPs.
  api.step('Recreate SKPs',
           ['python', api.path['build'].join('scripts', 'slave', 'skia',
                                             'recreate_skps.py'),
            api.path['checkout'],
            api.path['checkout'].join('out', 'Debug', 'chrome'),
           ],
           cwd=api.path['slave_build'].join('skia'),
  )

def GenTests(api):
  yield (
    api.test('RecreateSKPs')
  )
