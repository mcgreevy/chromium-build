# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/git',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'webrtc',
]


def RunSteps(api):
  api.gclient.set_config('webrtc')

  # Make sure the checkout contains all deps for all platforms.
  for os in ['linux', 'android', 'mac', 'ios', 'win', 'unix']:
    api.gclient.c.target_os.add(os)

  step_result = api.python(
        'check roll status',
        api.package_repo_resource('scripts', 'tools', 'pycurl.py'),
        args=['https://webrtc-roll-cr-rev-status.appspot.com/status'],
        stdout=api.raw_io.output_text(),
        step_test_data=lambda: api.raw_io.test_api.stream_output(
            '1', stream='stdout')
  )
  step_result.presentation.logs['stdout'] = step_result.stdout.splitlines()
  if step_result.stdout.strip() != '1':
    step_result.presentation.step_text = 'Rolling deactivated'
    return
  else:
    step_result.presentation.step_text = 'Rolling activated'

  api.webrtc.checkout()
  api.gclient.runhooks()

  with api.context(cwd=api.path['checkout']):
    # Enforce a clean state, and discard any local commits from previous runs.
    api.git('checkout', '-f', 'main')
    api.git('pull', 'origin', 'main')
    api.git('clean', '-ffd')

    # Run the roll script. It will take care of branch creation, modifying DEPS,
    # uploading etc. It will also delete any previous roll branch.
    api.python(
        'autoroll DEPS',
        api.path['checkout'].join('tools_webrtc', 'autoroller', 'roll_deps.py'),
        ['--clean', '--verbose'],
    )


def GenTests(api):
  yield (
      api.test('rolling_activated') +
      api.properties.generic(mainname='client.webrtc.fyi',
                             buildername='Auto-roll - WebRTC DEPS')
  )
  yield (api.test('rolling_deactivated') +
      api.properties.generic(mainname='client.webrtc.fyi',
                             buildername='Auto-roll - WebRTC DEPS') +
      api.override_step_data('check roll status',
                             api.raw_io.stream_output('0', stream='stdout'))
  )
