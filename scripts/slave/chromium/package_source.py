#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A tool to package a checkout's source and upload it to Google Storage."""


import fnmatch
import json
import os
import re
import Queue
import shlex
import shutil
import sys
import threading
from time import strftime

from common import chromium_utils
from slave import slave_utils


FILENAME = 'chromium-src.tar.bz2'
GSBASE = 'gs://chromium-browser-csindex'
GSACL = 'public-read'
CONCURRENT_TASKS = 4
UNIT_INDEXER = './clang_indexer/bin/external_corpus_compilation_indexer'


def CreateJSONCompileCommands():
  with open('compile_commands.json', 'wb') as json_commands_file:
    json_commands_file.write('[\n')
    for root, _, filenames in os.walk('src/out'):
      for filename in fnmatch.filter(filenames, '*.json-command'):
        shutil.copyfileobj(open(os.path.join(root, filename), 'rb'),
                           json_commands_file)
    # Seek backwards 2 bytes to delete ",\n" from the last entry.
    json_commands_file.seek(-2, 1)
    json_commands_file.write('\n]\n')
    json_commands_file.close()


class IndexResult:
  def __init__(self):
    self.success = True

  def __nonzero__(self):
    return self.success

  def fail(self):
    self.success = False


def GenerateIndex():
  CreateJSONCompileCommands()

  with open('compile_commands.json', 'rb') as json_commands_file:
    json_commands = json.load(json_commands_file)

  if not os.path.exists(UNIT_INDEXER):
    raise Exception('ERROR: compilation indexer not found, exiting')

  # Get the absolute path of the indexer as we later execut it in the directory
  # in which the original compilation was executed.
  indexer = os.path.abspath(UNIT_INDEXER)

  queue = Queue.Queue()

  result = IndexResult()

  def _Worker():
    while True:
      directory, command = queue.get()

      # Use str(command) as shlex does not support unicode.
      run = [indexer, '--gid=', '--uid=', '--loas_pwd_fallback_in_corp',
             '--'] + shlex.split(str(command))
      try:
        # Ignore the result code - indexing success is monitored on a higher
        # level.
        chromium_utils.RunCommand(run, cwd=directory)
      except OSError, e:
        print >> sys.stderr, 'Failed to run %s: %s' % (run, e)
        result.fail()
      finally:
        queue.task_done()

  for entry in json_commands:
    queue.put((entry['directory'], entry['command']))

  for _ in range(CONCURRENT_TASKS):
    t = threading.Thread(target=_Worker)
    t.daemon = True
    t.start()

  queue.join()
  return result


def DeleteIfExists(filename):
  """Deletes the file (relative to GSBASE), if it exists."""
  (status, output) = slave_utils.GSUtilListBucket(GSBASE)
  if status != 0:
    raise Exception('ERROR: failed to get list of GSBASE, exiting' % GSBASE)

  regex = re.compile('\s*\d+\s+([-:\w]+)\s+%s/%s\n' % (GSBASE, filename))
  if not regex.search(output):
    return

  status = slave_utils.GSUtilDeleteFile('%s/%s' % (GSBASE, filename))
  if status != 0:
    raise Exception('ERROR: GSUtilDeleteFile error %d. "%s"' % (
        status, '%s/%s' % (GSBASE, filename)))


def main():
  if not os.path.exists('src'):
    raise Exception('ERROR: no src directory to package, exiting')

  completed_hour = strftime('%H')
  completed_filename = '%s.%s' % (FILENAME, completed_hour)
  partial_filename = '%s.partial' % completed_filename

  chromium_utils.RunCommand(['rm', '-f', partial_filename])
  if os.path.exists(partial_filename):
    raise Exception('ERROR: %s cannot be removed, exiting' % partial_filename)

  indexing_successful = GenerateIndex()

  find_command = ['find', 'src/', 'tools/', 'o3d/', '-type', 'f',
                  '(', '-regex', '^src/out/.*index$', '-o',
                  '!', '-regex', '^src/out/.*', ')', '-a',
                  '!', '-regex', r'.*\.svn.*']

  if chromium_utils.RunCommand(find_command,
                               pipes=[['tar', '-T-', '-cjvf',
                                       partial_filename]]) != 0:
    raise Exception('ERROR: failed to create %s, exiting' % partial_filename)

  DeleteIfExists(completed_filename)
  DeleteIfExists(partial_filename)

  status = slave_utils.GSUtilCopyFile(partial_filename, GSBASE, gs_acl=GSACL)
  if status != 0:
    raise Exception('ERROR: GSUtilCopyFile error %d. "%s" -> "%s"' % (
        status, partial_filename, GSBASE))

  status = slave_utils.GSUtilMoveFile('%s/%s' % (GSBASE, partial_filename),
                                      '%s/%s' % (GSBASE, completed_filename))
  if status != 0:
    raise Exception('ERROR: GSUtilMoveFile error %d. "%s" -> "%s"' % (
        status, '%s/%s' % (GSBASE, partial_filename),
        '%s/%s' % (GSBASE, completed_filename)))

  (status, output) = slave_utils.GSUtilListBucket(GSBASE)
  if status != 0:
    raise Exception('ERROR: failed to get list of GSBASE, exiting' % GSBASE)

  regex = re.compile('\s*\d+\s+([-:\w]+)\s+%s/%s\n' % (GSBASE,
                                                       completed_filename))
  match_data = regex.search(output)
  modified_time = None
  if match_data:
    modified_time = match_data.group(1)
  if not modified_time:
    raise Exception('ERROR: could not get modified_time, exiting')
  print 'Last modified time: %s' % modified_time

  if not indexing_successful:
    return 1

  return 0


if '__main__' == __name__:
  sys.exit(main())
