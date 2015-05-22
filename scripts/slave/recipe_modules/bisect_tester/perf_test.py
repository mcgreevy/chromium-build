# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import time

from . import parse_metric


def run_perf_test(api, test_config):
  """Runs the command N times and parses a metric from the output."""
  limit = time.time() + test_config['timeout_seconds']
  values = []
  metric = test_config['metric'].split('/')
  output_for_all_runs = ''
  retcodes = []
  for i in range(test_config['repeat_count']):
    if time.time() < limit:
      command_name = "Performance Test %d/%d" % (i + 1,
                                                 test_config['repeat_count'])
      if api.m.platform.is_linux:
        os.environ['CHROME_DEVEL_SANDBOX'] = api.m.path.join(
            '/opt', 'chromium', 'chrome_sandbox')
      out, err, retcode = _run_command(api, test_config['command'], command_name)
      if out is None and err is None:
        # dummy value when running test TODO: replace with a mock
        values.append(0)
        retcodes.append(retcode)
      else:  # pragma: no cover
        valid_value, value = parse_metric.parse_metric(out, err, metric)
        output_for_all_runs += out
        retcodes.append(retcode)
        if valid_value:
          values.extend(value)
    else:  # pragma: no cover
      break
  return values, output_for_all_runs, retcodes


def truncate_and_aggregate(api, values, truncate_percent):
  truncate_proportion = truncate_percent / 100.0
  mean = api.m.math_utils.truncated_mean(values, truncate_proportion)
  std_err = api.m.math_utils.standard_error(values)
  return {'mean': mean, 'std_err': std_err, 'values': values}


def _run_command(api, command, command_name):

  # TODO(robertocn): Reevaluate this approach when adding support for non-perf
  # tests and non-linux platforms.
  if api.m.platform.is_linux and 'xvfb' not in command:
    command = 'xvfb-run -a ' + command
  command_parts = command.split()
  stdout = api.m.raw_io.output()
  stderr = api.m.raw_io.output()
  try:
    step_result = api.m.step(
        command_name,
        command_parts,
        stdout=stdout,
        stderr=stderr)
  except api.m.step.StepFailure as sf:
    return sf.result.stdout, sf.result.stderr, sf.result.retcode
  return step_result.stdout, step_result.stderr, step_result.retcode
