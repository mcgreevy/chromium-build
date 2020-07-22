#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Execute buildsteps on the subordinate.

This is the buildrunner, a script designed to run builds on the subordinate. It works
by mocking out the structures of a Buildbot main, then running a subordinate under
that 'fake' main. There are several benefits to this approach, the main one
being that build code can be changed and reloaded without a main restart.

Usage is detailed with -h.
"""

# pylint: disable=C0323

import optparse
import re
import os
import sys
import time

# Bootstrap PYTHONPATH from runit
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
import common.env
common.env.Install()

from common import main_cfg_utils
from common import chromium_utils
from subordinate import builder_utils
from subordinate import runbuild_utils

REVISION_RE = re.compile(r'[0-9a-f]{5,40}|[1-9][0-9]{0,8}')


def get_args():
  """Process command-line arguments."""

  prog_desc = 'Executes a Buildbot build locally, without a main.'
  usage = '%prog [options] <main directory> [builder or subordinate hostname]'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--list-mains', action='store_true',
                    help='list mains in search path')
  parser.add_option('--main-dir', help='specify a main directory '
                    'instead of a mainname')
  parser.add_option('--list-builders', help='list all available builders for '
                    'this main', action='store_true')
  parser.add_option('-s', '--subordinatehost', metavar='subordinatehost',
                    help='specify a subordinatehost to operate as')
  parser.add_option('-b', '--builder', metavar='builder',
                    help='string specified is a builder name')
  parser.add_option('--list-steps', action='store_true',
                    help='list steps in factory, but don\'t execute them')
  parser.add_option('--show-commands', action='store_true',
                    help='when listing steps, also show the generated output'
                         ' command. Also enables --list-steps and '
                         '--override-brdostep.')
  parser.add_option('--override-brdostep', action='store_true',
                    help='process all steps, even those with '
                         'brDoStepIf=False or None.')
  parser.add_option('--stepfilter', help='only run steps that match the '
                    'stepfilter regex')
  parser.add_option('--stepreject', help='reject any steps that match the '
                    'stepfilter regex')
  parser.add_option('--logfile', default='build_runner.log',
                    help='log build runner output to file (use - for stdout). '
                    'default: %default')
  parser.add_option('--hide-header', help='don\'t log environment information'
                    ' to logfile', action='store_true')
  parser.add_option('--subordinate-dir', help='location of the subordinate dir',
                    default=None)
  parser.add_option('--svn-rev', help='revision to check out, default: '
                    'LKGR')
  parser.add_option('--main-cfg', default='main.cfg',
                    help='filename of the main config. default: %default')
  parser.add_option('--builderpath',
                    help='directory to build results in. default: safe '
                    'transformation of builder name')
  parser.add_option('--build-properties', action='callback',
                    callback=chromium_utils.convert_json, type='string',
                    nargs=1, default={},
                    help='build properties in JSON format')
  parser.add_option('--factory-properties', action='callback',
                    callback=chromium_utils.convert_json, type='string',
                    nargs=1, default={},
                    help='factory properties in JSON format')
  parser.add_option('--output-build-properties', action='store_true',
                    help='output JSON-encoded build properties extracted from'
                    ' the build')
  parser.add_option('--output-factory-properties', action='store_true',
                    help='output JSON-encoded build properties extracted from'
                    'the build factory')
  parser.add_option('--annotate', action='store_true',
                    help='format output to work with the Buildbot annotator')
  parser.add_option('--test-config', action='store_true',
                    help='Attempt to parse all builders and steps without '
                    'executing them. Returns 0 on success.')
  parser.add_option('--fail-fast', action='store_true',
                    help='Exit on first step error instead of continuing.')

  return parser.parse_args()


def args_ok(inoptions, pos_args):
  """Verify arguments are correct and prepare args dictionary."""

  if inoptions.factory_properties:
    for key in inoptions.factory_properties:
      setattr(inoptions, key, inoptions.factory_properties[key])

  if inoptions.list_mains:
    return True

  if inoptions.build_properties and not inoptions.main_dir:
    if inoptions.build_properties['mainname']:
      inoptions.mainname = inoptions.build_properties['mainname']
    else:
      print >>sys.stderr, 'Error: build properties did not specify a ',
      print >>sys.stderr, 'mainname.'
      return False
  else:
    if not (inoptions.main_dir or pos_args):
      print >>sys.stderr, 'Error: you must provide a mainname or ',
      print >>sys.stderr, 'directory.'
      return False
    else:
      if not inoptions.main_dir:
        inoptions.mainname = pos_args.pop(0)

  inoptions.step_regex = None
  inoptions.stepreject_regex = None
  if inoptions.stepfilter:
    if inoptions.stepreject:
      print >>sys.stderr, ('Error: can\'t specify both stepfilter and '
                           'stepreject at the same time.')
      return False

    try:
      inoptions.step_regex = re.compile(inoptions.stepfilter)
    except re.error as e:
      print >>sys.stderr, 'Error compiling stepfilter regex \'%s\': %s' % (
          inoptions.stepfilter, e)
      return False
  if inoptions.stepreject:
    if inoptions.stepfilter:
      print >>sys.stderr, ('Error: can\'t specify both stepfilter and '
                           'stepreject at the same time.')
      return False
    try:
      inoptions.stepreject_regex = re.compile(inoptions.stepreject)
    except re.error as e:
      print >>sys.stderr, 'Error compiling stepreject regex \'%s\': %s' % (
          inoptions.stepreject, e)
      return False

  if inoptions.list_builders:
    return True

  if inoptions.show_commands:
    inoptions.override_brdostep = True
    inoptions.list_steps = True

  if inoptions.test_config:
    inoptions.spec = {}
    inoptions.revision = 12345
    inoptions.build_properties['got_revision'] = 12345
    inoptions.build_properties['revision'] = 12345
    return True

  if inoptions.build_properties and not (inoptions.subordinatehost or
                                         inoptions.builder):
    if inoptions.build_properties['buildername']:
      inoptions.builder = inoptions.build_properties['buildername']
    else:
      print >>sys.stderr, 'Error: build properties did not specify a '
      print >>sys.stderr, 'buildername.'
      return False
  else:
    if not (pos_args or inoptions.subordinatehost or inoptions.builder):
      print >>sys.stderr, 'Error: you must provide a builder or subordinate hostname.'
      return False

  # buildbot expects a list here, not a comma-delimited string
  if 'blamelist' in inoptions.build_properties:
    inoptions.build_properties['blamelist'] = (
        inoptions.build_properties['blamelist'].split(','))

  inoptions.spec = {}
  if inoptions.builder:
    inoptions.spec['builder'] = inoptions.builder
  elif inoptions.subordinatehost:
    inoptions.spec['hostname'] = inoptions.subordinatehost
  else:
    inoptions.spec['either'] = pos_args.pop(0)

  if inoptions.logfile == '-' or inoptions.annotate:
    inoptions.log = sys.stdout
  else:
    try:
      inoptions.log = open(inoptions.logfile, 'w')
    except IOError as err:
      errno, strerror = err
      print >>sys.stderr, 'Error %d opening logfile %s: %s' % (
          inoptions.logfile, errno, strerror)
      return False
    print >>sys.stderr, 'Writing to logfile', inoptions.logfile

  inoptions.revision = None
  if inoptions.build_properties and not inoptions.svn_rev:
    if inoptions.build_properties.get('revision'):
      inoptions.revision = inoptions.build_properties['revision']

    # got_revision will supersede revision if present.
    if inoptions.build_properties.get('got_revision'):
      inoptions.revision = inoptions.build_properties['got_revision']

    if not inoptions.revision:
      print >>sys.stderr, ('Error: build properties did not specify '
                           'valid revision.')
      return False

    if not REVISION_RE.match(inoptions.revision):
      print >>sys.stderr, 'Error: revision must be hash-like or revision-like.'
      return False

    print >>sys.stderr, 'using revision: %s' % inoptions.revision
    inoptions.build_properties['revision'] = '%s' % inoptions.revision
  else:
    if inoptions.svn_rev:
      try:
        inoptions.revision = int(inoptions.svn_rev)
      except ValueError:
        inoptions.revision = None

      if not inoptions.revision or inoptions.revision < 1:
        print >>sys.stderr, 'Error: svn rev must be a non-negative integer.'
        return False

      if not inoptions.annotate:
        print >>sys.stderr, 'using revision: %d' % inoptions.revision
    else:  # nothing specified on command line, let's check LKGR
      inoptions.revision, errmsg = chromium_utils.GetLKGR()
      if not inoptions.revision:
        print >>sys.stderr, errmsg
        return False
      if not inoptions.annotate:
        print >>sys.stderr, 'using LKGR: %d' % inoptions.revision

  return True


def execute(options):
  if options.list_mains:
    mainpairs = main_cfg_utils.GetMains()
    main_cfg_utils.PrettyPrintMains(mainpairs)
    return 0

  if options.main_dir:
    config = main_cfg_utils.LoadConfig(options.main_dir, options.main_cfg)
  else:
    path = main_cfg_utils.ChooseMain(options.mainname)
    if not path:
      return 2

    config = main_cfg_utils.LoadConfig(path, config_file=options.main_cfg)

  if not config:
    return 2

  mainname = config['BuildmainConfig']['properties']['mainname']
  builders = config['BuildmainConfig']['builders']
  options.build_properties.update(config['BuildmainConfig'].get(
      'properties', {}))

  if options.list_builders:
    main_cfg_utils.PrettyPrintBuilders(builders, mainname)
    return 0

  if options.test_config:
    for builder in builders:
      # We need to provide a subordinatename, so just pick the first one
      # the builder has.
      builder['subordinatename'] = builder['subordinatenames'][0]
      execute_builder(builder, mainname, options)
    return 0

  my_builder = main_cfg_utils.ChooseBuilder(builders, options.spec)
  return execute_builder(my_builder, mainname, options)

def execute_builder(my_builder, mainname, options):
  if options.spec and 'hostname' in options.spec:
    subordinatename = options.spec['hostname']
  elif (options.spec and 'either' in options.spec) and (
      options.spec['either'] != my_builder['name']):
    subordinatename = options.spec['either']
  else:
    subordinatename = my_builder['subordinatename']

  if not my_builder:
    return 2

  buildsetup = options.build_properties
  if 'revision' not in buildsetup:
    buildsetup['revision'] = '%s' % options.revision
  if 'branch' not in buildsetup:
    buildsetup['branch'] = 'src'

  steplist, build = builder_utils.MockBuild(my_builder, buildsetup, mainname,
      subordinatename, basepath=options.builderpath,
      build_properties=options.build_properties,
      subordinatedir=options.subordinate_dir)

  if options.output_build_properties:
    print
    print 'build properties:'
    print runbuild_utils.PropertiesToJSON(build.getProperties())

  if options.output_factory_properties:
    print
    print 'factory properties:'
    print runbuild_utils.PropertiesToJSON(my_builder['factory'].properties)

  if options.output_build_properties or options.output_factory_properties:
    return 0

  commands = builder_utils.GetCommands(steplist)
  if options.test_config:
    return 0

  if options.override_brdostep:
    for command in commands:
      command['doStep'] = True

  filtered_commands = runbuild_utils.FilterCommands(commands,
                                                    options.step_regex,
                                                    options.stepreject_regex)

  if options.list_steps:
    print
    print 'listing steps in %s/%s:' % (mainname, my_builder['name'])
    print
    for skip, cmd in filtered_commands:
      if 'command' not in cmd:
        print '-', cmd['name'], '[skipped] (custom step type: %s)' % (
            cmd['stepclass'])
      elif skip:
        print '-', cmd['name'], '[skipped]'
      elif skip is None:
        print '-', cmd['name'], '[skipped] (not under buildrunner)'
      else:
        print '*', cmd['name'],
        if options.show_commands:
          print '(in %s): %s' % (cmd['quoted_workdir'], cmd['quoted_command'])
        print
    return 0

  # Only execute commands that can be executed.
  filtered_commands = [(s, c) for s, c in filtered_commands if 'command' in c]

  if not options.annotate:
    print >>sys.stderr, 'using %s builder \'%s\'' % (mainname,
        my_builder['name'])

  start_time = time.clock()
  commands_executed, err = runbuild_utils.Execute(filtered_commands,
      options.annotate, options.log, fail_fast=options.fail_fast)
  end_time = time.clock()

  if err:
    print >>sys.stderr, ('error occurred in previous step, aborting! (%0.2fs'
                         ' since start).' % (end_time - start_time))
    return 2

  if not options.annotate:
    print >>sys.stderr, '%d commands completed (%0.2fs).' % (
        commands_executed, end_time - start_time)
  else:
    if commands_executed < 1:
      print '0 commands executed.'
  return 0


def main():
  opts, args = get_args()
  if not args_ok(opts, args):
    print
    print 'run with --help for usage info'
    return 1

  retcode = execute(opts)

  if retcode == 0:
    if not (opts.annotate or opts.list_mains or opts.list_builders
            or opts.list_steps or opts.test_config):
      print >>sys.stderr, 'build completed successfully'
  else:
    if not opts.annotate:
      print >>sys.stderr, 'build error encountered! aborting build'

  return retcode


if __name__ == '__main__':
  sys.exit(main())
