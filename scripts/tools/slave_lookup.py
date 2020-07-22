#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Simple utility script to read subordinate names and output their information."""


import argparse
import json
import os
import sys

# Install infra environment.
SCRIPTS_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.pardir))
sys.path.insert(0, SCRIPTS_ROOT)
from common import env
env.Install()

from common import chromium_utils


def main(args):
  parser = argparse.ArgumentParser()
  parser.add_argument('-i', '--input', metavar='PATH',
      type=argparse.FileType('r'), default=None,
      help='Read subordinate names from this file (use - for STDIN).')
  parser.add_argument('subordinate_names', nargs='*',
      help='Individual names of subordinates. Leave blank to read from STDIN.')
  opts = parser.parse_args(args)

  subordinate_names = set(opts.subordinate_names)
  if not subordinate_names and not opts.input:
    opts.input = sys.stdin
  if opts.input:
    subordinate_names.update(s.strip() for s in opts.input.read().split())
    opts.input.close()

  subordinates = {}
  for path in chromium_utils.ListMainsWithSubordinates():
    for subordinate in chromium_utils.GetSubordinatesFromMainPath(path):
      hostname = subordinate.get('hostname')
      if hostname in subordinate_names:
        subordinates[hostname] = subordinate

  json.dump(subordinates, sys.stdout, indent=1, sort_keys=True)


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
