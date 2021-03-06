# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process


DEPS = [
    'chromium_tests',
    'filter',
    'recipe_engine/json',
    'recipe_engine/platform',
    'recipe_engine/properties',
    'recipe_engine/raw_io',
]


def RunSteps(api):
  api.chromium_tests.trybot_steps()
  assert api.chromium_tests.is_precommit_mode()


def GenTests(api):
  yield (
      api.test('basic') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data(
          'read test spec (chromium.linux.json)',
          api.json.output({
              'Linux Tests': {
                  'gtest_tests': ['base_unittests'],
              },
          })
      ) +
      api.filter.suppress_analyze()
  )

  yield (
      api.test('analyze_compile_mode') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_clobber_rel_ng')
  )

  yield (
      api.test('no_compile') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng')
  )

  yield (
      api.test('no_compile_no_source') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('OWNERS')
      )
  )

  yield (
      api.test('blink_linux') +
      api.properties.tryserver(
          mastername='tryserver.chromium.linux',
          buildername='linux_chromium_rel_ng') +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('third_party/WebKit/foo.cc')
      )
  )

  yield (
      api.test('blink_mac') +
      api.platform.name('mac') +
      api.properties.tryserver(
          mastername='tryserver.chromium.mac',
          buildername='mac_chromium_rel_ng') +
      api.override_step_data(
          'git diff to analyze patch',
          api.raw_io.stream_output('third_party/WebKit/foo.cc')
      )
  )

  layout_tests_config = {
      'Linux Tests': {
          'isolated_scripts': [{
              'isolate_name': 'webkit_layout_tests_exparchive',
              'merge': {
                  'args': [
                      '--verbose',
                      '--results-json-override-with-build-property',
                      'build_number',
                      'buildnumber',
                      '--results-json-override-with-build-property',
                      'builder_name',
                      'buildername',
                      '--results-json-override-with-build-property',
                      'chromium_revision',
                      'got_revision_cp',
                  ],
                  'script':
                      ('//third_party/WebKit/Tools/Scripts/'
                       'merge-layout-test-results'),
              },
              'name': 'webkit_layout_tests',
              'results_handler': 'layout tests',
              'swarming': {
                  'can_use_on_swarming_builders': True,
                  'dimension_sets': [{'os': 'Ubuntu-14.04'}],
                  'shards': 1,
              }
          }],
      },
  }

  # We want to make sure that while we trigger webkit_layout_tests when analyze
  # finds a dependency for webkit_layout_tests_exparchive, we don't also
  # trigger webkit_layout_tests a second time by adding manually it in the
  # recipe code.  We test this by first checking that the recipe-added
  # webkit_layout_tests is suppressed in the presence of a config (see
  # supresses_swarming_layout_tests_via_src_side_config), then testing that
  # webkit_layout_tests is re-added if analyze finds a dependency (see
  # add_swarming_layout_tests_via_src_side_config).
  yield (
    api.test('supresses_swarming_layout_tests_via_src_side_config') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='linux_chromium_rel_ng',
        swarm_hashes = {
            'webkit_layout_tests_exparchive':
            '[dummy hash for webkit_layout_tests_exparchive]'}
    ) +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output(layout_tests_config)
    ) +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
            'third_party/WebKit/Source/core/dom/Element.cpp\n')
    ) +
    api.post_process(
        post_process.DoesNotRun, 'webkit_layout_tests (with patch)') +
    api.post_process(post_process.DropExpectation)
  )


  # See comment for supresses_swarming_layout_tests_via_src_side_config.
  yield (
    api.test('add_swarming_layout_tests_via_src_side_config') +
    api.properties.tryserver(
        mastername='tryserver.chromium.linux',
        buildername='linux_chromium_rel_ng',
        swarm_hashes = {
            'webkit_layout_tests_exparchive':
            '[dummy hash for webkit_layout_tests_exparchive]'}
    ) +
    api.platform.name('linux') +
    api.override_step_data(
        'read test spec (chromium.linux.json)',
        api.json.output(layout_tests_config)
    ) +
    api.override_step_data(
      'analyze',
      api.json.output({'status': 'Found dependency',
                       'test_targets': ['webkit_layout_tests_exparchive'],
                       'compile_targets': ['webkit_layout_tests_exparchive']})
    ) +
    api.override_step_data(
        'git diff to analyze patch',
        api.raw_io.stream_output(
            'third_party/WebKit/Source/core/dom/Element.cpp\n')
    ) +
    api.post_process(
        post_process.MustRun, 'webkit_layout_tests (with patch)') +
    api.post_process(post_process.DropExpectation)
  )
