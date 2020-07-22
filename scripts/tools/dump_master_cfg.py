#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Dumps main config as JSON.

Uses main_cfg_utils.LoadConfig, which should be called at most once
in the same process. That's why this is a separate utility.
"""

import argparse
import json
import os
import subprocess
import sys

SCRIPTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir))
if not SCRIPTS_DIR in sys.path:
  sys.path.insert(0, SCRIPTS_DIR)

from common import env

env.Install()

from common import main_cfg_utils
from main.factory.build_factory import BuildFactory

SELF = sys.argv[0]


class BuildbotJSONEncoder(json.JSONEncoder):
  def default(self, obj):  # pylint: disable=E0202
    if isinstance(obj, BuildFactory):
      return {'repr': repr(obj), 'properties': obj.properties.asDict()}

    return repr(obj)


def _dump_main((name, path)):
  data = subprocess.check_output(
      [sys.executable, SELF, path, '-'])
  try:
    return (name, json.loads(data))
  except Exception as e:
    return (name, e)


def dump_all_mains(glob):
  # Selective imports. We do this here b/c "dump_main_cfg" is part of
  # a lot of production paths, and we don't want random import/pathing errors
  # to break that.
  import fnmatch
  import multiprocessing

  import config_bootstrap
  from subordinate import bootstrap

  # Homogenize main names: remove "main." from glob if present. We'll do the
  # same with main names.
  def strip_prefix(v, pfx):
    if v.startswith(pfx):
      v = v[len(pfx):]
    return v
  glob = strip_prefix(glob, 'main.')

  bootstrap.ImportMainConfigs(include_internal=True)
  all_mains = {
      strip_prefix(os.path.basename(mc.local_config_path), 'main.'): mc
      for mc in config_bootstrap.Main.get_all_mains()}

  pool = multiprocessing.Pool(multiprocessing.cpu_count())
  m = dict(pool.map(_dump_main, (
      (k, v.local_config_path) for k, v in sorted(all_mains.items())
      if fnmatch.fnmatch(k, glob))))
  pool.close()
  pool.join()

  for k, v in sorted(m.items()):
    if isinstance(v, Exception):
      print >>sys.stderr, 'Failed to load JSON from %s: %s' % (k, v)
      m[k] = None

  return m


def main(argv):
  parser = argparse.ArgumentParser()
  parser.add_argument('-m', '--multi', action='store_true',
      help='If specified, produce multi-main format and interpret the '
           '"main" argument as a glob expression of mains to match.')
  parser.add_argument('main',
      help='The path of the main to dump. If "*" is provided, produce a '
           'multi-main-format output list of all main configs.')
  parser.add_argument('output', type=argparse.FileType('w'), default=sys.stdout)

  args = parser.parse_args(argv)

  if args.multi:
    data = dump_all_mains(args.main)
  else:
    data = main_cfg_utils.LoadConfig(args.main)['BuildmainConfig']

  json.dump(data,
            args.output,
            cls=BuildbotJSONEncoder,
            indent=4,
            sort_keys=True)
  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
