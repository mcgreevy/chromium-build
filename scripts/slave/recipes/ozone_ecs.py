# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.types import freeze

DEPS = [
  'depot_tools/bot_update',
  'chromium',
  'depot_tools/gclient',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'depot_tools/tryserver',
]

OZONE_TESTS = freeze([
    # Linux tests.
    'base_unittests',
    # 'browser_tests', Not sensible.
    'cacheinvalidation_unittests',
    'cc_unittests',
    'components_unittests',
    'content_browsertests',
    'content_unittests',
    'crypto_unittests',
    # 'dbus_unittests', Not sensible; use_dbus==0.
    'device_unittests',
    # 'google_apis_unittests', Not sensible.
    'gpu_unittests',
    # 'interactive_ui_tests', Not sensible.
    'ipc_tests',
    # 'jingle_unittests', Later.
    'media_unittests',
    'net_unittests',
    'ozone_unittests',
    'ppapi_unittests',
    # 'printing_unittests', Not sensible.
    'sandbox_linux_unittests',
    'sql_unittests',
    'ui_base_unittests',
    # 'unit_tests',  Not sensible.
    'url_unittests',
    # 'sync_integration_tests', Not specified in bug.
    # 'chromium_swarm_tests', Not specified in bug.
] + [
    'aura_unittests',
    'compositor_unittests',
    'events_unittests',
    'gfx_unittests',
    'ui_touch_selection_unittests',
])

tests_that_do_not_compile = freeze([
])

tests_that_do_not_pass = freeze([
])

dbus_tests = freeze([
    'dbus_unittests',
])

def RunSteps(api):

  api.chromium.set_config('chromium', BUILD_CONFIG='Debug')
  api.gclient.set_config('chromium', BUILD_CONFIG='Debug')

  api.bot_update.ensure_checkout()

  api.chromium.c.gyp_env.GYP_DEFINES['embedded'] = 1

  api.chromium.runhooks()
  api.chromium.compile(['content_shell'], name='compile content_shell')

  try:
    api.python('check ecs deps', api.path['checkout'].join('tools',
      'check_ecs_deps', 'check_ecs_deps.py'),
      cwd=api.chromium.c.build_dir.join(api.chromium.c.build_config_fs))
  except api.step.StepFailure:
    pass

  tests_to_compile = list(set(OZONE_TESTS) - set(tests_that_do_not_compile))
  tests_to_compile.sort()
  api.chromium.compile(tests_to_compile, name='compile tests')

  tests_to_run = list(set(tests_to_compile) - set(tests_that_do_not_pass))
  #TODO(martiniss) convert loop
  for x in sorted(tests_to_run):
    api.chromium.runtest(x, xvfb=False, spawn_dbus=(x in dbus_tests))

  # Compile the failing targets.
  #TODO(martiniss) convert loop
  for x in sorted(set(OZONE_TESTS) &
                  set(tests_that_do_not_compile)): # pragma: no cover
    try:
      api.chromium.compile([x], name='experimentally compile %s' % x)
    except api.step.StepFailure:
      pass

  # Run the failing tests.
  tests_to_try = list(set(tests_to_compile) & set(tests_that_do_not_pass))
  #TODO(martiniss) convert loop
  for x in sorted(tests_to_try): # pragma: no cover
    try:
      api.chromium.runtest(x, xvfb=False, name='experimentally run %s' % x)
    except api.step.StepFailure:
      pass

def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.scheduled(mastername="chromium.fyi",
                               buildername='linux_ecs_ozone',
                               slavename="test_slave")
  )

  yield (
      api.test('trybot') +
      api.properties.tryserver(mastername="chromium.fyi",
                               buildername='linux_ecs_ozone',
                               slavename="test_slave")
  )

  yield (
    api.test('check_ecs_deps_fail') +
    api.properties.scheduled(mastername="chromium.fyi",
                            buildername='linux_ecs_ozone',
                            slavename="test_slave") +
    api.step_data('check ecs deps', retcode=1)
  )
