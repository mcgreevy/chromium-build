# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for building and running tests for Libyuv stand-alone.
"""

from recipe_engine.types import freeze

DEPS = [
  'chromium',
  'chromium_android',
  'depot_tools/bot_update',
  'depot_tools/gclient',
  'depot_tools/tryserver',
  'libyuv',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/step',
]


def RunSteps(api):
  libyuv = api.libyuv
  libyuv.apply_bot_config(libyuv.BUILDERS, libyuv.RECIPE_CONFIGS)

  libyuv.checkout()
  if libyuv.should_build:
    api.chromium.ensure_goma()
  api.chromium.runhooks()

  if libyuv.should_build:
    api.chromium.run_gn(use_goma=True)
    api.chromium.compile(use_goma_module=True)
    if libyuv.should_upload_build:
      libyuv.package_build()

  if libyuv.should_download_build:
    libyuv.extract_build()

  if libyuv.should_test:
    libyuv.runtests()

  libyuv.maybe_trigger()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())


def GenTests(api):
  builders = api.libyuv.BUILDERS

  def generate_builder(mainname, buildername, revision, suffix=None):
    suffix = suffix or ''
    bot_config = builders[mainname]['builders'][buildername]
    bot_type = bot_config.get('bot_type', 'builder_tester')

    chromium_kwargs = bot_config.get('chromium_config_kwargs', {})
    test = (
      api.test('%s_%s%s' % (_sanitize_nonalpha(mainname),
                            _sanitize_nonalpha(buildername), suffix)) +
      api.properties(mainname=mainname,
                     buildername=buildername,
                     bot_id='bot_id',
                     BUILD_CONFIG=chromium_kwargs['BUILD_CONFIG']) +
      api.platform(bot_config['testing']['platform'],
                   chromium_kwargs.get('TARGET_BITS', 64))
    )

    if bot_config.get('parent_buildername'):
      test += api.properties(
          parent_buildername=bot_config['parent_buildername'])

    if revision:
      test += api.properties(revision=revision)
    if bot_type == 'tester':
      test += api.properties(parent_got_revision=revision)

    if mainname.startswith('tryserver'):
      test += api.properties(issue='123456789', patchset='1',
                             rietveld='https://rietveld.example.com')
    test += api.properties(buildnumber=1337)
    return test

  for mainname, main_config in builders.iteritems():
    for buildername in main_config['builders'].keys():
      yield generate_builder(mainname, buildername, revision='deadbeef')

  # Forced builds (not specifying any revision) and test failures.
  mainname = 'client.libyuv'
  yield generate_builder(mainname, 'Linux64 Debug', revision=None,
                         suffix='_forced')
  yield generate_builder(mainname, 'Android Debug', revision=None,
                         suffix='_forced')
  yield generate_builder(mainname, 'Android Tester ARM32 Debug (Nexus 5X)',
                         revision=None, suffix='_forced_invalid')

  yield generate_builder('tryserver.libyuv', 'linux', revision=None,
                         suffix='_forced')
