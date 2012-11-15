#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Given a list of manifest, print a dictionary mapping them
to their hash values.
"""

import hashlib
import optparse
import os
import sys


def main():
  # Parses arguments
  parser = optparse.OptionParser(usage='%prog [options]')
  parser.add_option('-n', '--manifest_name', action='append', default=[],
                    help='The name of a manifest to send to swarm. This may '
                    'be given multiple times to send multiple manifests.')
  parser.add_option('--manifest_directory', default='',
                    help='The directory to find the manifest files in. '
                    'Defaults to %default')
  (options, args) = parser.parse_args()

  manifests = options.manifest_name

  # Treat all arguments as 'test:test_filter'.
  for arg in args:
    # The buildbot might have put multiple test:test_filter pairs in a single
    # argument so split them up and add them separately.
    tests = arg.split()
    for test in tests:
      test_name = test.split(':', 1)[0] if ':' in test else test
      manifests.append(test_name + '.isolated')

  # Get the file hash values and output the pair.
  for filepath in manifests:
    test_name = os.path.basename(filepath).split('.')[0]
    full_filepath = os.path.join(options.manifest_directory, filepath)

    if not os.path.exists(full_filepath):
      print 'The manifest, %s, doesn\'t exist' % full_filepath
      continue

    sha1_hash = hashlib.sha1(open(full_filepath, 'rb').read()).hexdigest()
    print test_name + ' ' + sha1_hash

    # TODO(csharp): Remove once the isolate tracked dependencies are inputs
    # for the isolated files.
    print ('Delete %s to ensure it is regenerated by the next build.' %
           full_filepath)
    os.remove(full_filepath)


if __name__ == '__main__':
  sys.exit(main())
