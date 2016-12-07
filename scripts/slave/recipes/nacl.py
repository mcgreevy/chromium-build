# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'goma',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
  'trigger',
]

# Maps from triggering builder to triggered builder;
# key builder triggers value builder.
trigger_map = {
    # client.nacl builders
    'precise_64-newlib-arm_qemu-pnacl-dbg':
      'oneiric_32-newlib-arm_hw-pnacl-panda-dbg',
    'precise_64-newlib-arm_qemu-pnacl-opt':
      'oneiric_32-newlib-arm_hw-pnacl-panda-opt',
    'precise_64-newlib-arm_qemu-pnacl-buildonly-spec':
      'oneiric_32-newlib-arm_hw-pnacl-panda-spec',
    # tryserver.nacl builders
    'nacl-arm_opt_panda':
      'nacl-arm_hw_opt_panda',
    'nacl-arm_perf_panda':
      'nacl-arm_hw_perf_panda',
}

def _CheckoutSteps(api):
  api.gclient.set_config('nacl')
  result = api.bot_update.ensure_checkout()

  # HACK(iannucci): bot_update.ensure_checkout should return an actual meaninful
  # object with actual meaningful semantics.
  got_revision = result.presentation.properties['got_revision']
  api.gclient.runhooks()
  return got_revision

def _AnnotatedStepsSteps(api, got_revision):
  # Default environemnt; required by all builders.
  env = {
      'BUILDBOT_MASTERNAME': api.properties['mastername'],
      'BUILDBOT_BUILDERNAME': api.properties['buildername'],
      'BUILDBOT_REVISION': api.properties['revision'],
      'BUILDBOT_GOT_REVISION': got_revision,
      'RUNTEST': api.package_repo_resource('scripts', 'slave', 'runtest.py'),
      'BUILDBOT_SLAVE_TYPE': api.properties['slavetype'],
  }
  # Set up env for the triggered builders.
  if api.properties['buildername'] in trigger_map.values():
    env.update({
        'BUILDBOT_TRIGGERED_BY_BUILDERNAME':
          api.properties['parent_buildername'],
        'BUILDBOT_TRIGGERED_BY_BUILDNUMBER':
          api.properties['parent_buildnumber'],
        'BUILDBOT_TRIGGERED_BY_SLAVENAME':
          api.properties['parent_slavename'],
    })
  goma_dir = api.goma.ensure_goma()
  if goma_dir:
    env.update({
        'GOMA_DIR': goma_dir,
        'NOCONTROL_GOMA': '1',
    })
  api.goma.start()
  exit_status = -1
  try:
    api.python('annotated steps',
               api.path['checkout'].join('buildbot', 'buildbot_selector.py'),
               allow_subannotations=True,
               cwd = api.path['checkout'],
               env = env)
    exit_status = 0
  except api.step.StepFailure as e:
    exit_status = e.retcode
    raise e
  finally:
    api.goma.stop(ninja_log_exit_status=exit_status)

def _TriggerTestsSteps(api):
  if api.properties['buildername'] in trigger_map:
    api.trigger(
        {'builder_name': trigger_map[api.properties['buildername']],
         'properties': {'parent_slavename': api.properties['slavename']}})

def RunSteps(api):
  got_revision = _CheckoutSteps(api)
  _AnnotatedStepsSteps(api, got_revision)
  _TriggerTestsSteps(api)

def GenTests(api):
  yield (
    api.test('linux_triggering') +
    api.platform('linux', 64) +
    api.properties(
      mastername = 'client.nacl',
      buildername = 'precise_64-newlib-arm_qemu-pnacl-dbg',
      revision = 'abcd',
      slavename = 'TestSlave',
      buildnumber = 1234,
      slavetype = 'BuilderTester',
    ))

  yield (
    api.test('linux_triggering_failed') +
    api.platform('linux', 64) +
    api.properties(
      mastername = 'client.nacl',
      buildername = 'precise_64-newlib-arm_qemu-pnacl-dbg',
      revision = 'abcd',
      slavename = 'TestSlave',
      buildnumber = 1234,
      slavetype = 'BuilderTester',
    ) + api.step_data('annotated steps', retcode=1))

  yield (
    api.test('linux_triggered') +
    api.platform('linux', 32) +
    api.properties(
      mastername = 'client.nacl',
      buildername = 'oneiric_32-newlib-arm_hw-pnacl-panda-dbg',
      revision = 'abcd',
      slavename='TestSlave',
      buildnumber = 5678,
      parent_slavename = 'TestSlave',
      parent_buildername = 'precise_64-newlib-arm_qemu-pnacl-dbg',
      parent_buildnumber = 1,
      slavetype = 'BuilderTester',
    ))
