# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import base64
import collections
import json


def perform_bisect(api, **flags):  # pragma: no cover
  try:
      bisect_config = api.m.properties.get('bisect_config')
      assert isinstance(bisect_config, collections.Mapping)
      bisector = api.create_bisector(bisect_config, **flags)
      with api.m.step.nest('Gathering reference values'):
        _gather_reference_range(api, bisector)
      if (not bisector.failed and bisector.check_improvement_direction() and
          bisector.check_initial_confidence()):
        if bisector.check_reach_adjacent_revision(bisector.good_rev):
          # Only show this step if bisect has reached adjacent revisions.
          with api.m.step.nest(str('Check bisect finished on revision ' +
                                   bisector.good_rev.revision_string())):
            if bisector.check_bisect_finished(bisector.good_rev):
              bisector.bisect_over = True
        if not bisector.bisect_over:
          _bisect_main_loop(bisector)
      else:
        bisector.bisect_over = True
      bisector.print_result_debug_info()
      bisector.post_result(halt_on_failure=True)
  except api.m.step.StepFailure:
      if api.m.chromium.c.TARGET_PLATFORM == 'android':
        api.m.chromium_android.device_status_check()
        connected_devices = api.m.chromium_android.devices()
        tested_devices = api.m.bisect_tester.devices_tested
        available_devices = [device for device in connected_devices
                             if device not in tested_devices]
        if available_devices:
          serial_number = available_devices[0]
          api.m.bisect_tester.device_to_test = serial_number
          api.m.bisect_tester.devices_tested.append(serial_number)
          perform_bisect(api,**flags)
        else:
          raise
      else:
        raise


def _gather_reference_range(api, bisector):  # pragma: no cover
  bisector.good_rev.start_job()
  bisector.bad_rev.start_job()
  bisector.wait_for_all([bisector.good_rev, bisector.bad_rev])
  if bisector.good_rev.failed:
    bisector.surface_result('REF_RANGE_FAIL')
    api.m.halt('Testing the "good" revision failed')
    bisector.failed = True
  elif bisector.bad_rev.failed:
    bisector.surface_result('REF_RANGE_FAIL')
    api.m.halt('Testing the "bad" revision failed')
    bisector.failed = True
    api.m.halt('Testing the "good" revision failed')
  else:
    bisector.compute_relative_change()


def _bisect_main_loop(bisector):  # pragma: no cover
  """This is the main bisect loop.

  It gets an evenly distributed number of revisions in the candidate range,
  then it starts them in parallel and waits for them to finish.
  """
  while not bisector.bisect_over:
    revision_to_check = bisector.get_revision_to_eval()
    if not revision_to_check:
      bisector.bisect_over = True
      break

    with bisector.api.m.step.nest(str('Working on revision ' +
                                      revision_to_check.revision_string())):
      bisector.post_result(halt_on_failure=False)
      revision_to_check.start_job()
      bisector.wait_for(revision_to_check)

    if bisector.check_reach_adjacent_revision(revision_to_check):
      # Only show this step if bisect has reached adjacent revisions.
      with bisector.api.m.step.nest(
          str('Check bisect finished on revision ' +
              revision_to_check.revision_string())):
        if bisector.check_bisect_finished(revision_to_check):
            bisector.bisect_over = True
