# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'depot_tools/gclient',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'v8',
]

def RunSteps(api):
  api.gclient.set_config('v8')
  api.bot_update.ensure_checkout(no_shallow=True)

  step_result = api.python(
      'check roll status',
      api.package_repo_resource('scripts', 'tools', 'runit.py'),
      [api.package_repo_resource('scripts', 'tools', 'pycurl.py'),
       'https://v8-roll.appspot.com/status'],
      stdout=api.raw_io.output_text(),
      step_test_data=lambda: api.raw_io.test_api.stream_output(
          '1', stream='stdout')
    )
  step_result.presentation.logs['stdout'] = step_result.stdout.splitlines()
  if step_result.stdout.strip() != '1':
    step_result.presentation.step_text = "Pushing deactivated"
    return
  else:
    step_result.presentation.step_text = "Pushing activated"

  with api.context(cwd=api.path['checkout']):
    api.python(
        'push candidate',
        api.path['checkout'].join(
            'tools', 'release', 'auto_push.py'),
        ['--author', 'v8-autoroll@chromium.org',
         '--reviewer', 'v8-autoroll@chromium.org',
         '--push',
         '--work-dir', api.path['start_dir'].join('workdir')],
      )


def GenTests(api):
  yield api.test('standard') + api.properties.generic(
      mainname='client.v8.fyi')
  yield (api.test('rolling_deactivated') +
      api.properties.generic(mainname='client.v8.fyi') +
      api.override_step_data(
          'check roll status', api.raw_io.stream_output('0', stream='stdout'))
    )

