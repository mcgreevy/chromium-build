# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class ChromiumTestApi(recipe_test_api.RecipeTestApi):
  def gen_tests_for_builders(self, builder_dict):
    # TODO: crbug.com/354674. Figure out where to put "simulation"
    # tests. Is this really the right place?

    def _sanitize_nonalpha(text):
      return ''.join(c if c.isalnum() else '_' for c in text)

    for mastername in builder_dict:
      for buildername in builder_dict[mastername]['builders']:
        if 'mac' in buildername or 'Mac' in buildername:
          platform_name = 'mac'
        elif 'win' in buildername or 'Win' in buildername:
          platform_name = 'win'
        else:
          platform_name = 'linux'
        test = (
            self.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                      _sanitize_nonalpha(buildername))) +
            self.m.platform.name(platform_name)
        )
        if mastername.startswith('tryserver'):
          test += self.m.properties.tryserver(buildername=buildername,
                                              mastername=mastername)
        else:
          test += self.m.properties.generic(buildername=buildername,
                                            mastername=mastername)

        yield test

  # The following data was generated by running 'gyp_chromium
  # --analyzer' with input JSON files corresponding to changes
  # affecting these targets.
  @property
  def analyze_builds_nothing(self):
    return self.m.json.output({
        'status': 'No dependencies',
        'compile_targets': [],
        'test_targets': [],
        })
