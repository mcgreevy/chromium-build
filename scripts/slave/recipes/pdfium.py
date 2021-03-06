# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'depot_tools/bot_update',
  'depot_tools/depot_tools',
  'depot_tools/gclient',
  'file',
  'goma',
  'depot_tools/gsutil',
  'recipe_engine/context',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/platform',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/shutil',
  'recipe_engine/step',
  'recipe_engine/time',
]

from recipe_engine.recipe_api import Property

# DM_JSON is the file that gathers results for ingestion into Gold.
DM_JSON = 'dm.json'

# GS_BUCKET is the GS bucket to hold Gold Results.
GS_BUCKET = 'skia-pdfium-gm'

# Number of times the upload routine will retry to upload Gold results.
UPLOAD_ATTEMPTS = 5

PROPERTIES = {
  'skia': Property(default=False, kind=bool),
  'xfa': Property(default=False, kind=bool),
  'memory_tool': Property(default=None, kind=str),
  'v8': Property(default=True, kind=bool),
  'target_cpu': Property(default=None, kind=str),
  'clang': Property(default=False, kind=bool),
  'rel': Property(default=False, kind=bool),
  'skip_test': Property(default=False, kind=bool),
  'target_os': Property(default=None, kind=str),
}

def _CheckoutSteps(api, target_os):
  # Checkout pdfium and its dependencies (specified in DEPS) using gclient.
  api.gclient.set_config('pdfium')
  if target_os:
    api.gclient.c.target_os = {target_os}
  api.gclient.c.got_revision_mapping['pdfium'] = 'got_revision'
  update_step = api.bot_update.ensure_checkout()

  api.gclient.runhooks()
  return update_step.presentation.properties['got_revision']

def _OutPath(memory_tool, skia, xfa, v8, clang, rel):
  out_dir = 'release' if rel else 'debug'
  if skia:
    out_dir += "_skia"
  if xfa:
    out_dir += "_xfa"
  if v8:
    out_dir += "_v8"
  if clang:
    out_dir += "_clang"
  if memory_tool == 'asan':
    out_dir += "_asan"
  return out_dir


# _GNGenBuilds calls 'gn gen' and returns a dictionary of
# the used build configuration to be used by Gold.
def _GNGenBuilds(api, memory_tool, skia, xfa, v8, target_cpu, clang, rel,
                 target_os, out_dir):
  api.goma.ensure_goma()
  gn_bool = {True: 'true', False: 'false'}
  # Generate build files by GN.
  checkout = api.path['checkout']
  gn_cmd = api.depot_tools.gn_py_path

  # Prepare the arguments to pass in.
  args = [
      'is_debug=%s' % gn_bool[not rel],
      'is_component_build=false',
      'pdf_enable_v8=%s' % gn_bool[v8],
      'pdf_enable_xfa=%s' % gn_bool[xfa],
      'pdf_use_skia=%s' % gn_bool[skia],
      'pdf_is_standalone=true',
      'use_goma=true',
      'goma_dir="%s"' % api.goma.goma_dir,
  ]
  if api.platform.is_win and not memory_tool:
    args.append('symbol_level=1')
  if api.platform.is_linux:
    args.append('use_sysroot=false')
  if clang:
    args.append('is_clang=true')
  if memory_tool == 'asan':
    args.append('is_asan=true is_lsan=true')
  if target_os:
    args.append('target_os="%s"' % target_os)
  if target_cpu == 'x86':
    args.append('target_cpu="x86"')

  with api.context(cwd=checkout):
    api.python('gn gen', gn_cmd,
               ['--root=' + str(checkout), 'gen', '//out/' + out_dir,
                '--args=' + ' '.join(args)])

  # convert the arguments to key values pairs for gold usage.
  return gold_build_config(args)

def _BuildSteps(api, clang, out_dir):
  debug_path = api.path['checkout'].join('out', out_dir)
  ninja_cmd = ['ninja', '-C', debug_path,
               '-j', api.goma.recommended_goma_jobs, 'pdfium_all']

  api.goma.build_with_goma(
      name='compile with ninja',
      ninja_command=ninja_cmd,
      ninja_log_outdir=debug_path,
      ninja_log_compiler='clang' if clang else 'unknown')

# _RunTests runs the tests and uploads the results to Gold.
def _RunTests(api, memory_tool, v8, out_dir, build_config, revision):
  env = {}
  if memory_tool == 'asan':
    options = ['detect_leaks=1',
               'allocator_may_return_null=1',
               'symbolize=1',
               'external_symbolizer_path='
               'third_party/llvm-build/Release+Asserts/bin/llvm-symbolizer']
    env.update({'ASAN_OPTIONS': ' '.join(options)})

  unittests_path = str(api.path['checkout'].join('out', out_dir,
                                                 'pdfium_unittests'))
  if api.platform.is_win:
    unittests_path += '.exe'
  with api.context(cwd=api.path['checkout'], env=env):
    api.step('unittests', [unittests_path])

  embeddertests_path = str(api.path['checkout'].join('out', out_dir,
                                                     'pdfium_embeddertests'))
  if api.platform.is_win:
    embeddertests_path += '.exe'
  with api.context(cwd=api.path['checkout'], env=env):
    api.step('embeddertests', [embeddertests_path])

  script_args = ['--build-dir', api.path.join('out', out_dir)]

  if v8:
    javascript_path = str(api.path['checkout'].join('testing', 'tools',
                                                    'run_javascript_tests.py'))
    with api.context(cwd=api.path['checkout'], env=env):
      api.python('javascript tests', javascript_path, script_args)

  pixel_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                   'run_pixel_tests.py'))
  with api.context(cwd=api.path['checkout'], env=env):
    api.python('pixel tests', pixel_tests_path, script_args)

  # Add the arguments needed to upload the resulting images.
  gold_output_dir = api.path['checkout'].join('out', out_dir, 'gold_output')
  gold_props, gold_key = get_gold_params(api, build_config, revision)
  script_args.extend([
    '--gold_properties', gold_props,
    '--gold_key', gold_key,
    '--gold_output_dir', gold_output_dir,
  ])

  ignore_hashes_file = get_gold_ignore_hashes(api, out_dir)
  if ignore_hashes_file:
    script_args.extend(['--gold_ignore_hashes',
                        ignore_hashes_file]) # pragma: no cover

  corpus_tests_path = str(api.path['checkout'].join('testing', 'tools',
                                                    'run_corpus_tests.py'))
  with api.context(cwd=api.path['checkout'], env=env):
    api.python('corpus tests', corpus_tests_path, script_args)
  upload_dm_results(api, gold_output_dir, revision)


def RunSteps(api, memory_tool, skia, xfa, v8, target_cpu, clang, rel, skip_test,
             target_os):
  revision = _CheckoutSteps(api, target_os)

  out_dir = _OutPath(memory_tool, skia, xfa, v8, clang, rel)

  build_config = _GNGenBuilds(api, memory_tool, skia, xfa, v8,
                              target_cpu, clang, rel, target_os, out_dir)

  _BuildSteps(api, clang, out_dir)

  if skip_test:
    return

  _RunTests(api, memory_tool, v8, out_dir, build_config, revision)

def get_gold_params(api, build_config, revision):
  """Get the parameters to be passed to the testing call to
  generate the dm.json file expected by Gold and to upload
  the generated images. Returns:
      (properties_str, key_str)
  These strings can be passed directly into run_corpus_tests.py.
  """
  builder_name = api.m.properties['buildername'].strip()
  props = [
    'gitHash', revision,
    'master', api.m.properties['mastername'],
    'builder', builder_name,
    'build_number', str(api.m.properties['buildnumber'])
  ]

  # Add the trybot information if this is a trybot run.
  issue = str(api.m.properties.get('issue', ''))
  patchset = str(api.m.properties.get('patchset', ''))
  if api.m.properties.get('patch_storage', '') == 'gerrit':
    issue = str(api.m.properties['patch_issue'])
    patchset = str(api.m.properties['patch_set'])
  if issue and patchset:
    props.extend([
      'issue', issue,
      'patchset', patchset,
      'patch_storage', api.m.properties.get('patch_storage', 'rietveld')
    ])

  # Add the os from the builder name to the set of unique identifers.
  keys = build_config.copy()
  keys["os"] = builder_name.split("_")[0]

  return " ".join(props), dict_to_str(keys)

def dict_to_str(props):
  """Returns the given dictionary as a string of space
     separated key/value pairs sorted by keys.
  """
  ret = []
  for k in sorted(props.keys()):
    ret += [k,props[k]]
  return " ".join(ret)

def gold_build_config(args):
  """ Extracts key value pairs from the arguments handed to 'gn gen'
      and returns them as a dictionary. Since these are used as
      parameters in Gold we strip common prefixes and disregard
      some arguments. i.e. 'use_goma' since we don't care about how
      a binary was built.  Only arguments that follow the
      'key=value' pattern are considered.
  """
  black_list = ["use_goma", "goma_dir", "use_sysroot", "is_component_build"]
  strip_prefixes = ["is_", "pdf_enable_", "pdf_use_", "pdf_"]
  build_config = {}
  for arg in args:
    # Catch multiple k/v pairs separated by spaces.
    parts = arg.split()
    for p in parts:
      kv = [x.strip() for x in p.split("=")]
      if len(kv) == 2:
        k,v = kv
        if k not in black_list:
          for prefix in strip_prefixes:
            if k.startswith(prefix):
              k = k[len(prefix):]
              break
          build_config[k] = v
  return build_config

def get_gold_ignore_hashes(api, out_dir):
  """Downloads a list of MD5 hashes from Gold and
  writes them to a file. That file is then used by the
  test runner in the pdfium repository to ignore already
  known hashes.
  """
  host_hashes_file = api.path['checkout'].join('out',
                                               out_dir,
                                               'ignore_hashes.txt')
  try:
    with api.context(cwd=api.path['checkout']):
      api.m.python.inline(
        'get uninteresting hashes',
        program="""
        import contextlib
        import math
        import socket
        import sys
        import time
        import urllib2

        HASHES_URL = 'https://pdfium-gold.skia.org/_/hashes'
        RETRIES = 5
        TIMEOUT = 60
        WAIT_BASE = 15

        socket.setdefaulttimeout(TIMEOUT)
        for retry in range(RETRIES):
          try:
            with contextlib.closing(
                urllib2.urlopen(HASHES_URL, timeout=TIMEOUT)) as w:
              hashes = w.read()
              with open(sys.argv[1], 'w') as f:
                f.write(hashes)
                break
          except Exception as e:
            print 'Failed to get uninteresting hashes from %s:' % HASHES_URL
            print e
            if retry == RETRIES:
              raise
            waittime = WAIT_BASE * math.pow(2, retry)
            print 'Retry in %d seconds.' % waittime
            time.sleep(waittime)
        """,
        args=[host_hashes_file],
        infra_step=True)
  except api.step.StepFailure:
    # Swallow the exception. The step will still show up as
    # failed, but processing will continue.
    pass

  if api.path.exists(host_hashes_file):
    return host_hashes_file
  return None

def upload_dm_results(api, results_dir, revision):
  """ Uploads results of the tests to Gold.
  This assumes that results_dir contains a JSON file
  and a set of PNGs.
  Adapted from:
  https://skia.googlesource.com/skia/+/master/infra/bots/recipes/upload_dm_results.py
  """
  builder_name = api.m.properties['buildername'].strip()

  # Upload the images.
  img_glob = results_dir.join("*.png")
  files_to_upload = api.file.glob(
      'find images',
      img_glob,
      test_data=[api.path['start_dir'].join('someimage.png')],
      infra_step=True)

  if len(files_to_upload) > 0:
    gs_cp(api, 'images', img_glob, 'dm-images-v1', multithreaded=True)

  # Upload the JSON summary and verbose.log.
  sec_str = str(int(api.time.time()))
  now = api.time.utcnow()
  summary_dest_path = '/'.join([
      'dm-json-v1',
      str(now.year ).zfill(4),
      str(now.month).zfill(2),
      str(now.day  ).zfill(2),
      str(now.hour ).zfill(2),
      revision,
      builder_name,
      sec_str])

  # Trybot results are further siloed by issue/patchset.
  issue = str(api.m.properties.get('issue', ''))
  patchset = str(api.m.properties.get('patchset', ''))
  if api.m.properties.get('patch_storage', '') == 'gerrit':
    issue = str(api.m.properties['patch_issue'])
    patchset = str(api.m.properties['patch_set'])
  if issue and patchset:
    summary_dest_path = '/'.join((
        'trybot', summary_dest_path, issue, patchset))

  summary_dest_path = '/'.join([summary_dest_path, DM_JSON])
  local_dmjson = results_dir.join(DM_JSON)
  gs_cp(api, 'JSON', local_dmjson, summary_dest_path,
        extra_args=['-z', 'json,log'])

def gs_cp(api, name, src, dst, multithreaded=False, extra_args=None):
  """
  Copy the src to dst in Google storage.
  """
  name = 'upload %s' % name
  for i in xrange(UPLOAD_ATTEMPTS):
    try:
      args = extra_args if extra_args else []
      full_dest = 'gs://%s/%s' % (GS_BUCKET, dst)
      api.gsutil(['cp'] + args + [src, full_dest],
                 name=name, multithreaded=multithreaded)
      break
    except api.step.StepFailure: # pragma: no cover
      if i == UPLOAD_ATTEMPTS - 1:
        raise

def GenTests(api):
  yield (
      api.test('win') +
      api.platform('win', 64) +
      api.properties(mastername="client.pdfium",
                     buildername='windows',
                     buildnumber='1234',
                     bot_id="test_slave")
  )
  yield (
      api.test('linux') +
      api.platform('linux', 64) +
      api.properties(mastername="client.pdfium",
                     buildername='linux',
                     buildnumber='1234',
                     bot_id="test_slave")
  )
  yield (
      api.test('mac') +
      api.platform('mac', 64) +
      api.properties(mastername="client.pdfium",
                     buildername='mac',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('win_no_v8') +
      api.platform('win', 64) +
      api.properties(v8=False,
                     mastername="client.pdfium",
                     buildername='windows_no_v8',
                     buildnumber='1234',
                     bot_id="test_slave")
  )
  yield (
      api.test('linux_no_v8') +
      api.platform('linux', 64) +
      api.properties(v8=False,
                     mastername="client.pdfium",
                     buildername='linux_no_v8',
                     buildnumber='1234',
                     bot_id="test_slave")
  )
  yield (
      api.test('mac_no_v8') +
      api.platform('mac', 64) +
      api.properties(v8=False,
                     mastername="client.pdfium",
                     buildername='mac_no_v8',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('win_skia') +
      api.platform('win', 64) +
      api.properties(skia=True,
                     xfa=True,
                     skip_test=True,
                     mastername="client.pdfium",
                     buildername='windows_skia',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('win_xfa_32') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     target_cpu='x86',
                     mastername="client.pdfium",
                     buildername='windows_xfa_32',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('win_xfa') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     mastername="client.pdfium",
                     buildername='windows_xfa',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('win_xfa_rel') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     rel=True,
                     mastername="client.pdfium",
                     buildername='windows_xfa_rel',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('win_xfa_clang_32') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     clang=True,
                     target_cpu='x86',
                     mastername="client.pdfium",
                     buildername='windows_xfa_clang_32',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('win_xfa_clang') +
      api.platform('win', 64) +
      api.properties(xfa=True,
                     clang=True,
                     mastername="client.pdfium",
                     buildername='windows_xfa_clang',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('linux_skia') +
      api.platform('linux', 64) +
      api.properties(skia=True,
                     xfa=True,
                     skip_test=True,
                     mastername="client.pdfium",
                     buildername='linux_skia',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('linux_xfa') +
      api.platform('linux', 64) +
      api.properties(xfa=True,
                     mastername="client.pdfium",
                     buildername='linux_xfa',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('linux_xfa_rel') +
      api.platform('linux', 64) +
      api.properties(xfa=True,
                     rel=True,
                     mastername="client.pdfium",
                     buildername='linux_xfa_rel',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('mac_skia') +
      api.platform('mac', 64) +
      api.properties(skia=True,
                     xfa=True,
                     skip_test=True,
                     mastername="client.pdfium",
                     buildername='mac_skia',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('mac_xfa') +
      api.platform('mac', 64) +
      api.properties(xfa=True,
                     mastername="client.pdfium",
                     buildername='mac_xfa',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('mac_xfa_rel') +
      api.platform('mac', 64) +
      api.properties(xfa=True,
                     rel=True,
                     mastername="client.pdfium",
                     buildername='mac_xfa_rel',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('linux_asan_lsan') +
      api.platform('linux', 64) +
      api.properties(memory_tool='asan',
                     mastername="client.pdfium",
                     buildername='linux_asan_lsan',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
      api.test('linux_xfa_asan_lsan') +
      api.platform('linux', 64) +
      api.properties(xfa=True,
                     memory_tool='asan',
                     mastername="client.pdfium",
                     buildername='linux_xfa_asan_lsan',
                     buildnumber='1234',
                     bot_id="test_slave")
  )

  yield (
       api.test('try-linux_xfa_asan_lsan') +
       api.platform('linux', 64) +
       api.properties.tryserver(xfa=True,
                                memory_tool='asan',
                                mastername='tryserver.client.pdfium',
                                buildnumber='1234',
                                buildername='linux_xfa_asan_lsan')
  )

  yield (
       api.test('try-linux-gerrit_xfa_asan_lsan') +
       api.platform('linux', 64) +
       api.properties.tryserver(xfa=True,
                                memory_tool='asan',
                                mastername='tryserver.client.pdfium',
                                buildnumber='1234',
                                buildername='linux_xfa_asan_lsan',
                                patch_issue='1234',
                                patch_set=5,
                                patch_storage='gerrit')
  )

  yield (
      api.test('android') +
      api.platform('linux', 64) +
      api.properties(mastername='client.pdfium',
                     buildername='android',
                     bot_id='test_slave',
                     target_os='android',
                     buildnumber='1234',
                     skip_test=True)
  )

  yield (
    api.test('success-download-hashes-file') +
    api.platform('linux', 64) +
    api.properties(v8=False,
                   mastername='client.pdfium',
                   buildername='android',
                   bot_id='test_slave',
                   target_os='android',
                   buildnumber='1234') +
    api.path.exists(
      api.path['checkout'].join('out', 'debug', 'ignore_hashes.txt')
    )
  )

  yield (
    api.test('fail-download-hashes-file') +
    api.platform('linux', 64) +
    api.properties(mastername='client.pdfium',
                   buildername='android',
                   bot_id='test_slave',
                   target_os='android',
                   buildnumber='1234') +
    api.step_data(
          'get uninteresting hashes', retcode=1)
  )
